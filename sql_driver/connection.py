# Шар інтерфейсу: з'єднання з БД (продукти патерну Factory Method)

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from . import messages
from .cursor import Cursor
from .exceptions import ConnectionError
from .executor import ConnectionJournal, QueryExecutor, QueryFilter, QueryJournal
from .gateway import DatabaseGateway


class Connection(ABC):
    """Інтерфейс з'єднання за PEP 249: cursor(), commit(), rollback(), close().

    На відміну від sqlite3, вихід із блоку with не лише фіксує або скасовує
    транзакцію, а й закриває з'єднання.
    """

    @abstractmethod
    def cursor(self) -> Cursor: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def closed(self) -> bool: ...

    @property
    @abstractmethod
    def in_transaction(self) -> bool: ...

    def ensure_open(self) -> None:
        # Перевіряє, що з'єднання відкрите (використовується також курсором)
        if self.closed:
            raise ConnectionError(messages.CONNECTION_CLOSED)

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            if not self.closed:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            self.close()


class SQLiteConnection(Connection):
    # З'єднання з файлом SQLite. Містить QueryExecutor і створені курсори

    def __init__(self, gateway: DatabaseGateway, journal: Optional[QueryJournal] = None,
                 filters: Optional[Sequence[QueryFilter]] = None) -> None:
        self._gateway = gateway
        self._executor = QueryExecutor(gateway, journal, filters)
        self._cursors: List[Cursor] = []
        self._closed = False

    def cursor(self) -> Cursor:
        # Фабричний метод курсора, налаштованого на QueryExecutor з'єднання
        self.ensure_open()
        cursor = Cursor(self, self._executor)
        self._cursors = [c for c in self._cursors if not c.closed]
        self._cursors.append(cursor)
        return cursor

    def commit(self) -> None:
        self.ensure_open()
        self._gateway.commit()

    def rollback(self) -> None:
        self.ensure_open()
        self._gateway.rollback()

    def close(self) -> None:
        # Закриває курсори та з'єднання. Незбережені зміни скасовуються
        if self._closed:
            return
        for cursor in self._cursors:
            cursor.close()
        self._cursors.clear()
        self._closed = True
        self._gateway.close()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def in_transaction(self) -> bool:
        return not self._closed and self._gateway.in_transaction


class LoggingConnection(SQLiteConnection):
    # З'єднання, що записує запити й транзакції до службової БД (ФВ-10)

    def __init__(self, gateway: DatabaseGateway, journal: ConnectionJournal,
                 filters: Optional[Sequence[QueryFilter]] = None) -> None:
        super().__init__(gateway, journal, filters)
        self._journal = journal

    def commit(self) -> None:
        super().commit()
        self._journal.end_transaction("COMMIT")

    def rollback(self) -> None:
        super().rollback()
        self._journal.end_transaction("ROLLBACK")

    def close(self) -> None:
        if self.closed:
            return
        had_changes = self.in_transaction
        try:
            super().close()
        finally:
            if had_changes:
                self._journal.end_transaction("ROLLBACK")
            self._journal.close()
