# Фільтри конвеєра QueryExecutor (патерн Pipe-Filter)

"""
Кожен фільтр виконує одну операцію й нічого не знає про інші фільтри:
F1 SqlValidator → F2 ParameterBinder → F3 StatementRunner → F4 ResultMapper.
Помилка в будь-якому фільтрі перериває конвеєр винятком QueryError.
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from .. import messages
from ..exceptions import QueryError
from ..gateway import DatabaseGateway, RawResult
from .query import KIND_SELECT, Query, QueryResult, classify
from .scanner import scan

_ALLOWED_VALUE_TYPES = (type(None), int, float, str, bytes, bytearray, memoryview)


class QueryFilter(ABC):
    # Спільний інтерфейс фільтра: отримує дані, повертає перетворені дані

    @abstractmethod
    def process(self, data: Any) -> Any: ...


class SqlValidator(QueryFilter):
    # F1: запит є рядком, не порожній, містить одну інструкцію; визначає тип

    def process(self, query: Query) -> Query:
        if not isinstance(query.sql, str):
            raise QueryError(messages.SQL_NOT_STRING)
        result = scan(query.sql)
        if result.statements == 0:
            raise QueryError(messages.SQL_EMPTY)
        if result.statements > 1:
            raise QueryError(messages.SQL_MULTIPLE.format(result.statements))
        return dataclasses.replace(
            query,
            keyword=result.keyword,
            kind=classify(result.keyword),
            positional=result.positional,
            numbered=result.numbered,
            named=result.named,
        )


class ParameterBinder(QueryFilter):
    # F2: кількість і типи значень відповідають маркерам; значення окремо від SQL

    def process(self, query: Query) -> Query:
        params = query.params if query.params is not None else ()
        if isinstance(params, Mapping):
            bound = self._bind_mapping(query, params)
        elif isinstance(params, Sequence) and not isinstance(params, (str, bytes)):
            bound = self._bind_sequence(query, tuple(params))
        else:
            raise QueryError(messages.PARAMS_BAD_CONTAINER)
        return dataclasses.replace(query, params=bound)

    def _bind_sequence(self, query: Query, values: tuple) -> tuple:
        if query.named:
            raise QueryError(messages.PARAMS_NEED_MAPPING)
        if query.positional and query.numbered:
            raise QueryError(messages.PARAMS_MIXED)
        expected = query.numbered or query.positional
        if len(values) != expected:
            raise QueryError(messages.PARAMS_COUNT.format(len(values), expected))
        for index, value in enumerate(values, start=1):
            self._check_type(f"№{index}", value)
        return values

    def _bind_mapping(self, query: Query, values: Mapping) -> dict:
        if query.positional or query.numbered:
            raise QueryError(messages.PARAMS_NEED_SEQUENCE)
        missing = sorted(query.named - set(values))
        if missing:
            raise QueryError(messages.PARAMS_MISSING.format(", ".join(":" + m for m in missing)))
        for name in query.named:
            self._check_type(name, values[name])
        return dict(values)

    @staticmethod
    def _check_type(name: str, value: Any) -> None:
        if not isinstance(value, _ALLOWED_VALUE_TYPES):
            raise QueryError(messages.PARAMS_BAD_TYPE.format(name, type(value).__name__))


class StatementRunner(QueryFilter):
    # F3: передає перевірений запит до СУБД через DatabaseGateway

    def __init__(self, gateway: DatabaseGateway) -> None:
        self._gateway = gateway

    def process(self, query: Query) -> RawResult:
        raw = self._gateway.execute(query.sql, query.params)
        return dataclasses.replace(raw, kind=query.kind)


class ResultMapper(QueryFilter):
    # F4: перетворює сирий результат на QueryResult для курсора

    def process(self, raw: RawResult) -> QueryResult:
        rows = [tuple(row) for row in raw.rows]
        columns = tuple(item[0] for item in raw.description) if raw.description else ()
        # sqlite3 повертає rowcount = -1 для SELECT; PEP 249 дозволяє вказати кількість рядків.
        rowcount = len(rows) if raw.description or raw.kind == KIND_SELECT else raw.rowcount
        return QueryResult(rows, columns, raw.description, rowcount, raw.lastrowid, raw.kind)
