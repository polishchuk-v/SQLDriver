# Шар даних: адаптер до стандартного модуля sqlite3 (патерн Adapter)

"""
SqliteGateway — єдине місце в пакеті, що імпортує sqlite3. Він приводить
інтерфейс sqlite3 до інтерфейсу DatabaseGateway та перетворює винятки
sqlite3.Error на власні винятки драйвера з українськими повідомленнями.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from . import config, messages
from .exceptions import ConnectionError, QueryError


@dataclass(frozen=True)
class RawResult:
    # Необроблений результат виконання інструкції

    rows: list
    description: Optional[tuple]
    rowcount: int
    lastrowid: Optional[int]
    kind: str = ""


class DatabaseGateway(ABC):
    # Абстракція доступу до СУБД, від якої залежать вищі шари

    @abstractmethod
    def open(self, path: str) -> None: ...

    @abstractmethod
    def execute(self, sql: str, params: Any = ()) -> RawResult: ...

    @abstractmethod
    def executescript(self, script: str) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def in_transaction(self) -> bool: ...


@contextmanager
def _translated(error_class: type, fallback: str = "") -> Iterator[None]:
    # Перетворює sqlite3.Error на виняток драйвера вказаного класу
    try:
        yield
    except sqlite3.Error as exc:
        original = str(exc)
        text = messages.translate_sqlite_message(original)
        if text == messages.SQLITE_GENERIC and fallback:
            text = fallback
        raise error_class(text, detail=original) from exc


class SqliteGateway(DatabaseGateway):
    # Реалізація DatabaseGateway на основі модуля sqlite3

    def __init__(self) -> None:
        self._conn: Optional[sqlite3.Connection] = None

    def open(self, path: str) -> None:
        with _translated(ConnectionError, messages.OPEN_FAILED):
            conn = sqlite3.connect(path, timeout=config.LOCK_TIMEOUT_SECONDS)
            try:
                # sqlite3 відкриває файл «ліниво», тому одразу читаємо схему:
                # так пошкоджений або чужий файл буде виявлено під час з'єднання.
                conn.execute("PRAGMA schema_version").fetchone()
                # НФВ-3: у SQLite перевірка зовнішніх ключів вимкнена за замовчуванням.
                conn.execute("PRAGMA foreign_keys = ON")
            except sqlite3.Error:
                conn.close()
                raise
        self._conn = conn

    def execute(self, sql: str, params: Any = ()) -> RawResult:
        conn = self._require()
        with _translated(QueryError):
            cursor = conn.execute(sql, params)
            try:
                rows = cursor.fetchall()
                return RawResult(rows, cursor.description, cursor.rowcount, cursor.lastrowid)
            finally:
                cursor.close()

    def executescript(self, script: str) -> None:
        with _translated(QueryError):
            self._require().executescript(script)

    def commit(self) -> None:
        with _translated(QueryError, messages.COMMIT_FAILED):
            self._require().commit()

    def rollback(self) -> None:
        with _translated(QueryError, messages.ROLLBACK_FAILED):
            self._require().rollback()

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except sqlite3.Error as exc:  # pragma: no cover — рідкісна ситуація
            raise ConnectionError(messages.translate_sqlite_message(str(exc)), str(exc)) from exc
        finally:
            self._conn = None

    @property
    def in_transaction(self) -> bool:
        return self._conn is not None and self._conn.in_transaction

    def _require(self) -> sqlite3.Connection:
        if self._conn is None:
            raise ConnectionError(messages.CONNECTION_CLOSED)
        return self._conn
