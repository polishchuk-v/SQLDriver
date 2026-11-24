#SQL Driver — надбудова над sqlite3 за специфікацією PEP 249.

from __future__ import annotations

from typing import Any, Optional

from .connection import Connection, LoggingConnection, SQLiteConnection
from .cursor import Cursor
from .driver import Driver, LoggingSQLiteDriver, SQLiteDriver
from .exceptions import ConnectionError, DriverError, QueryError
from .executor import ConnectionJournal, QueryFilter, QueryJournal
from .gateway import DatabaseGateway, SqliteGateway
from .journal import QueryLogger

# Атрибути модуля, яких вимагає PEP 249.
apilevel = "2.0"
threadsafety = 1
paramstyle = "qmark"

__version__ = "1.0.0"


def connect(path: Any, log_path: Optional[str] = None) -> Connection:
    # Фасад: відкриває з'єднання; з log_path — із журналюванням запитів
    driver = LoggingSQLiteDriver(QueryLogger(log_path)) if log_path else SQLiteDriver()
    return driver.connect(path)


__all__ = [
    "connect", "Connection", "SQLiteConnection", "LoggingConnection", "Cursor",
    "Driver", "SQLiteDriver", "LoggingSQLiteDriver", "QueryLogger",
    "DatabaseGateway", "SqliteGateway", "QueryFilter", "QueryJournal", "ConnectionJournal",
    "DriverError", "ConnectionError", "QueryError",
    "apilevel", "threadsafety", "paramstyle",
]
