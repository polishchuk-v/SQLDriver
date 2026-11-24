# Шар інтерфейсу: драйвери-творці з'єднань (патерн Factory Method)

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Callable

from . import messages
from .connection import Connection, LoggingConnection, SQLiteConnection
from .exceptions import ConnectionError
from .gateway import DatabaseGateway, SqliteGateway
from .journal import QueryLogger

MEMORY_DATABASE = ":memory:"
GatewayFactory = Callable[[], DatabaseGateway]


class Driver(ABC):
    # Абстрактний творець: спільний алгоритм підключення

    def connect(self, path: Any) -> Connection:
        return self.create_connection(self.check_path(path))

    @staticmethod
    def check_path(path: Any) -> str:
        if isinstance(path, os.PathLike):
            path = os.fspath(path)
        if not isinstance(path, str):
            raise ConnectionError(messages.BAD_PATH_TYPE)
        if not path.strip():
            raise ConnectionError(messages.EMPTY_PATH)
        if path == MEMORY_DATABASE:
            return path
        if os.path.isdir(path):
            raise ConnectionError(messages.PATH_IS_FOLDER.format(path))
        folder = os.path.dirname(os.path.abspath(path))
        if not os.path.isdir(folder):
            raise ConnectionError(messages.FOLDER_NOT_FOUND.format(folder))
        return path

    @abstractmethod
    def create_connection(self, path: str) -> Connection:
        """Фабричний метод: конкретний клас з'єднання визначає підклас."""


class SQLiteDriver(Driver):
    """Створює звичайні з'єднання SQLiteConnection.

    Клас шлюзу передається ззовні (принцип DIP), тому в тестах замість
    SqliteGateway можна підставити іншу реалізацію DatabaseGateway.
    """

    def __init__(self, gateway_factory: GatewayFactory = SqliteGateway) -> None:
        self._gateway_factory = gateway_factory

    def create_connection(self, path: str) -> Connection:
        return SQLiteConnection(self._open_gateway(path))

    def _open_gateway(self, path: str) -> DatabaseGateway:
        gateway = self._gateway_factory()
        gateway.open(path)
        return gateway


class LoggingSQLiteDriver(SQLiteDriver):
    # Створює з'єднання LoggingConnection, що пишуть журнал у службову БД

    def __init__(self, logger: QueryLogger,
                 gateway_factory: GatewayFactory = SqliteGateway) -> None:
        super().__init__(gateway_factory)
        self.logger = logger

    def create_connection(self, path: str) -> Connection:
        gateway = self._open_gateway(path)
        try:
            session = self.logger.open_session(path)
        except Exception:
            gateway.close()
            raise
        return LoggingConnection(gateway, session)
