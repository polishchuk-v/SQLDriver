# Шар інтерфейсу: курсор за специфікацією PEP 249
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Iterator, List, Optional

from . import config, messages
from .exceptions import QueryError
from .executor import QueryExecutor, QueryResult

if TYPE_CHECKING:
    from .connection import Connection


class Cursor:
    # Передає SQL-інструкції модулю QueryExecutor і видає рядки результату

    def __init__(self, connection: "Connection", executor: QueryExecutor) -> None:
        self._connection = connection
        self._executor = executor
        self._result: Optional[QueryResult] = None
        self._position = 0
        self._closed = False
        self.arraysize = config.DEFAULT_ARRAYSIZE

    # --- атрибути PEP 249 ----------------------------------------------------
    @property
    def connection(self) -> "Connection":
        return self._connection

    @property
    def description(self) -> Optional[tuple]:
        return self._result.description if self._result else None

    @property
    def rowcount(self) -> int:
        return self._result.rowcount if self._result else -1

    @property
    def lastrowid(self) -> Optional[int]:
        return self._result.lastrowid if self._result else None

    @property
    def columns(self) -> tuple:
        """Назви стовпців останньої вибірки (розширення PEP 249)."""
        return self._result.columns if self._result else ()

    @property
    def closed(self) -> bool:
        return self._closed

    # --- виконання -----------------------------------------------------------
    def execute(self, sql: str, params: Any = None) -> "Cursor":
        self._check_open()
        self._result, self._position = None, 0
        self._result = self._executor.execute(sql, params)
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Any]) -> "Cursor":
        self._check_open()
        if isinstance(seq_of_params, (str, bytes)) or not isinstance(seq_of_params, Iterable):
            raise QueryError(messages.PARAMS_SEQ_EMPTY)
        total = 0
        for params in seq_of_params:
            self.execute(sql, params)
            total += max(self.rowcount, 0)
        if self._result is not None:
            self._result = replace(self._result, rowcount=total)
        return self

    # --- вибірка -------------------------------------------------------------
    def fetchone(self) -> Optional[tuple]:
        rows = self._take(1)
        return rows[0] if rows else None

    def fetchmany(self, size: Optional[int] = None) -> List[tuple]:
        size = self.arraysize if size is None else size
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise QueryError(messages.BAD_FETCH_SIZE)
        return self._take(size)

    def fetchall(self) -> List[tuple]:
        return self._take(None)

    def close(self) -> None:
        self._closed = True
        self._result = None

    def __iter__(self) -> Iterator[tuple]:
        return iter(self.fetchone, None)

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # --- допоміжне -----------------------------------------------------------
    def _take(self, count: Optional[int]) -> List[tuple]:
        self._check_open()
        if self._result is None:
            raise QueryError(messages.NO_RESULT)
        rows = self._result.rows
        end = len(rows) if count is None else min(len(rows), self._position + count)
        chunk = rows[self._position:end]
        self._position = end
        return chunk

    def _check_open(self) -> None:
        self._connection.ensure_open()
        if self._closed:
            raise QueryError(messages.CURSOR_CLOSED)
