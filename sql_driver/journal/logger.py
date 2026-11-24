"""Шар даних: журналювання запитів у службовій БД (ФВ-10).

QueryLogger відповідає за службову БД і може спільно використовуватися
кількома з'єднаннями (агрегація). Для кожного з'єднання він створює
JournalSession, яка пам'ятає ідентифікатори з'єднання та транзакції.
Кожен запис виконується через окреме коротке з'єднання з журналом, тому
журнал не блокує файл і його можна читати паралельно.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

from .. import config, messages
from ..exceptions import ConnectionError, DriverError
from ..executor import ConnectionJournal, Query, QueryResult
from ..executor.query import KIND_OTHER, KIND_TCL
from ..gateway import DatabaseGateway, SqliteGateway

_log = logging.getLogger(config.LOGGER_NAME)
_SCHEMA = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")

_RECENT_SQL = """
SELECT q.executed_at, f.name, q.sql_text, q.query_type, q.status,
       q.rows_affected, ROUND(q.duration_ms, 2), e.message
FROM queries q
JOIN connections c ON c.id = q.connection_id
JOIN database_files f ON f.id = c.database_id
LEFT JOIN error_records e ON e.query_id = q.id
ORDER BY q.id DESC
LIMIT ?
"""


def _now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="milliseconds")


class QueryLogger:
    """Службова БД журналу: створення схеми, сеанси з'єднань, читання записів."""

    def __init__(self, journal_path: str,
                 gateway_factory: Callable[[], DatabaseGateway] = SqliteGateway) -> None:
        self.path = str(journal_path)
        self._gateway_factory = gateway_factory
        folder = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            raise ConnectionError(messages.JOURNAL_FOLDER_FAILED.format(folder), str(exc)) from exc
        self.run(lambda gw: gw.executescript(_SCHEMA))

    def run(self, action: Callable[[DatabaseGateway], Any]) -> Any:
        """Виконує дію в окремому з'єднанні з журналом і фіксує зміни."""
        gateway = self._gateway_factory()
        gateway.open(self.path)
        try:
            result = action(gateway)
            gateway.commit()
            return result
        finally:
            gateway.close()

    def open_session(self, database_path: str) -> "JournalSession":
        full_path = database_path if database_path == ":memory:" else os.path.abspath(database_path)

        def register(gw: DatabaseGateway) -> int:
            gw.execute("INSERT OR IGNORE INTO database_files (name, file_path, created_at) "
                       "VALUES (?, ?, ?)", (os.path.basename(full_path), full_path, _now()))
            database_id = gw.execute("SELECT id FROM database_files WHERE file_path = ?",
                                     (full_path,)).rows[0][0]
            return gw.execute("INSERT INTO connections (database_id, opened_at, status) "
                              "VALUES (?, ?, 'OPEN')", (database_id, _now())).lastrowid

        return JournalSession(self, self.run(register))

    def recent_queries(self, limit: int = 200) -> List[tuple]:
        """Останні записи журналу: час, БД, SQL, тип, статус, рядки, мс, помилка."""
        return self.run(lambda gw: gw.execute(_RECENT_SQL, (limit,)).rows)


class JournalSession(ConnectionJournal):
    """Журнал одного з'єднання. Помилки журналу не переривають роботу драйвера."""

    def __init__(self, logger: QueryLogger, connection_id: int) -> None:
        self._logger = logger
        self.connection_id = connection_id
        self._transaction_id: Optional[int] = None

    def log_query(self, query: Query, result: Optional[QueryResult],
                  error: Optional[DriverError], duration_ms: float,
                  in_transaction: bool) -> None:
        def write(gw: DatabaseGateway) -> None:
            if in_transaction and self._transaction_id is None:
                self._transaction_id = gw.execute(
                    "INSERT INTO transactions (connection_id, started_at, outcome) "
                    "VALUES (?, ?, 'OPEN')", (self.connection_id, _now())).lastrowid
            sql_text = query.sql if isinstance(query.sql, str) else repr(query.sql)
            query_id = gw.execute(
                "INSERT INTO queries (connection_id, transaction_id, sql_text, query_type, "
                "executed_at, duration_ms, rows_affected, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.connection_id, self._transaction_id, sql_text, query.kind or KIND_OTHER,
                 _now(), round(duration_ms, 3), result.rowcount if result else None,
                 "ERROR" if error else "SUCCESS")).lastrowid
            for position, value in _parameters(query.params):
                gw.execute("INSERT INTO query_parameters (query_id, position, value_text, "
                           "value_type) VALUES (?, ?, ?, ?)",
                           (query_id, position, _as_text(value), type(value).__name__))
            if error:
                gw.execute("INSERT INTO error_records (query_id, error_type, message, "
                           "occurred_at) VALUES (?, ?, ?, ?)",
                           (query_id, type(error).__name__, error.message, _now()))

        self._safe(write)
        # Транзакцію могли завершити SQL-командою COMMIT / ROLLBACK.
        if query.kind == KIND_TCL and not in_transaction and error is None:
            self.end_transaction("ROLLBACK" if query.keyword == "ROLLBACK" else "COMMIT")

    def end_transaction(self, outcome: str) -> None:
        if self._transaction_id is None:
            return
        tx_id, self._transaction_id = self._transaction_id, None
        self._safe(lambda gw: gw.execute(
            "UPDATE transactions SET ended_at = ?, outcome = ? WHERE id = ?",
            (_now(), outcome, tx_id)))

    def close(self) -> None:
        self._safe(lambda gw: gw.execute(
            "UPDATE connections SET closed_at = ?, status = 'CLOSED' WHERE id = ?",
            (_now(), self.connection_id)))

    def _safe(self, action: Callable[[DatabaseGateway], Any]) -> None:
        try:
            self._logger.run(action)
        except DriverError as exc:
            _log.warning(messages.JOURNAL_FAILED, exc.message)


def _parameters(params: Any) -> list:
    if isinstance(params, dict):
        return list(params.items())
    if isinstance(params, tuple):
        return [(str(i), v) for i, v in enumerate(params, start=1)]
    return []


def _as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} байт>"
    return str(value)[:config.JOURNAL_VALUE_MAX_LENGTH]
