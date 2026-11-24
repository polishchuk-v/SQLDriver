# Шар управління застосунку: сеанс роботи з однією БД через SQL Driver

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sql_driver import Connection, Driver, LoggingSQLiteDriver, QueryError, QueryLogger
from sql_driver.executor import scan

from . import config

_STATUS = {"SUCCESS": "успішно", "ERROR": "помилка"}
_SCHEMA_KEYWORDS = {"CREATE", "DROP", "ALTER", "ROLLBACK"}

NOT_OPEN = "Спочатку відкрийте або створіть базу даних."

_TABLES_SQL = ("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') "
               "AND name NOT LIKE 'sqlite_%' ORDER BY name")


@dataclass(frozen=True)
class ExecutionReport:

    columns: Tuple[str, ...]
    rows: List[tuple]
    total_rows: int
    rowcount: int

    @property
    def is_selection(self) -> bool:
        return bool(self.columns)

    @property
    def truncated(self) -> bool:
        return self.total_rows > len(self.rows)


class ConsoleController:
    def __init__(self, driver: Driver, logger: QueryLogger) -> None:
        self.logger = logger
        self._driver = driver
        self._connection: Optional[Connection] = None
        self.path: Optional[str] = None

    @classmethod
    def create(cls, journal_path: str = str(config.JOURNAL_PATH)) -> "ConsoleController":
        """Збирає контролер зі стандартних компонентів: журнал і драйвер із журналюванням."""
        logger = QueryLogger(journal_path)
        return cls(LoggingSQLiteDriver(logger), logger)

    # --- стан ----------------------------------------------------------------
    @property
    def is_open(self) -> bool:
        return self._connection is not None

    @property
    def has_unsaved_changes(self) -> bool:
        return self._connection is not None and self._connection.in_transaction

    @property
    def database_name(self) -> str:
        return os.path.basename(self.path) if self.path else ""

    # --- з'єднання -----------------------------------------------------------
    def open_database(self, path: str) -> None:
        connection = self._driver.connect(path)
        self.close_database()
        self._connection, self.path = connection, path

    def close_database(self) -> None:
        if self._connection is not None:
            connection, self._connection, self.path = self._connection, None, None
            connection.close()

    # --- запити --------------------------------------------------------------
    def execute(self, sql: str) -> ExecutionReport:
        cursor = self._require().cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchmany(config.MAX_DISPLAY_ROWS) if cursor.columns else []
            total = cursor.rowcount if cursor.columns else 0
            return ExecutionReport(cursor.columns, rows, total, cursor.rowcount)
        finally:
            cursor.close()

    def preview_table(self, table: str) -> ExecutionReport:
        name = table.replace('"', '""')
        return self.execute(f'SELECT * FROM "{name}"')

    def tables(self) -> List[str]:
        if not self.is_open:
            return []
        return [row[0] for row in self.execute(_TABLES_SQL).rows]

    def commit(self) -> None:
        self._require().commit()

    def rollback(self) -> None:
        self._require().rollback()

    def journal_rows(self) -> List[tuple]:
        rows = []
        for row in self.logger.recent_queries(config.JOURNAL_LIMIT):
            row = list(row)
            row[4] = _STATUS.get(row[4], row[4])
            rows.append(tuple("" if value is None else value for value in row))
        return rows

    @staticmethod
    def changes_schema(sql: str) -> bool:
        try:
            return scan(sql).keyword in _SCHEMA_KEYWORDS
        except QueryError:
            return False

    @staticmethod
    def needs_confirmation(sql: str) -> bool:
        try:
            return scan(sql).keyword in config.DANGEROUS_KEYWORDS
        except QueryError:
            return False

    def _require(self) -> Connection:
        if self._connection is None:
            raise QueryError(NOT_OPEN)
        return self._connection

