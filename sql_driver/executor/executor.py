# Шар управління: модуль виконання запитів QueryExecutor

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from ..exceptions import DriverError
from ..gateway import DatabaseGateway
from .filters import ParameterBinder, QueryFilter, ResultMapper, SqlValidator, StatementRunner
from .query import Query, QueryResult


class QueryJournal(ABC):
    # Абстракція журналу запитів, від якої залежить QueryExecutor (принцип DIP)

    @abstractmethod
    def log_query(self, query: Query, result: Optional[QueryResult],
                  error: Optional[DriverError], duration_ms: float,
                  in_transaction: bool) -> None: ...


class ConnectionJournal(QueryJournal):
    """Журнал з'єднання: запити, результати транзакцій і закриття.

    Від цієї абстракції залежить LoggingConnection; реалізація — journal.JournalSession.
    Інтерфейс розділено на два (принцип ISP): виконавцю запитів потрібна лише
    операція log_query().
    """

    @abstractmethod
    def end_transaction(self, outcome: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


def default_filters(gateway: DatabaseGateway) -> List[QueryFilter]:
    # Стандартний конвеєр F1–F4
    return [SqlValidator(), ParameterBinder(), StatementRunner(gateway), ResultMapper()]


class QueryExecutor:
    """Проводить запит через конвеєр фільтрів і за потреби журналює результат.

    Склад конвеєра можна передати ззовні (принцип OCP): новий етап оброблення
    додається новим класом-фільтром без змін QueryExecutor.
    """

    def __init__(self, gateway: DatabaseGateway, journal: Optional[QueryJournal] = None,
                 filters: Optional[Sequence[QueryFilter]] = None) -> None:
        self._gateway = gateway
        self._journal = journal
        self._filters: List[QueryFilter] = (list(filters) if filters is not None
                                            else default_filters(gateway))

    def execute(self, sql: Any, params: Any = None) -> QueryResult:
        data: Any = Query(sql, params)
        query = data
        started = time.perf_counter()
        try:
            for step in self._filters:
                data = step.process(data)
                if isinstance(data, Query):
                    query = data            # найповніша версія запиту для журналу
        except DriverError as error:
            self._log(query, None, error, started)
            raise
        self._log(query, data, None, started)
        return data

    def _log(self, query: Query, result: Optional[QueryResult],
             error: Optional[DriverError], started: float) -> None:
        if self._journal is None:
            return
        duration_ms = (time.perf_counter() - started) * 1000
        self._journal.log_query(query, result, error, duration_ms, self._gateway.in_transaction)
