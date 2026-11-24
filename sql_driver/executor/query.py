# Формати даних, якими обмінюються фільтри конвеєра

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Optional, Tuple

# Типи інструкцій для журналу та інтерфейсу.
KIND_SELECT = "SELECT"
KIND_DML = "DML"
KIND_DDL = "DDL"
KIND_TCL = "TCL"
KIND_OTHER = "OTHER"

_KINDS = {
    KIND_SELECT: {"SELECT", "WITH", "VALUES", "EXPLAIN"},
    KIND_DML: {"INSERT", "UPDATE", "DELETE", "REPLACE"},
    KIND_DDL: {"CREATE", "DROP", "ALTER"},
    KIND_TCL: {"BEGIN", "COMMIT", "ROLLBACK", "END", "SAVEPOINT", "RELEASE"},
}


def classify(keyword: str) -> str:
    # Визначає тип інструкції за першим ключовим словом
    for kind, words in _KINDS.items():
        if keyword in words:
            return kind
    return KIND_OTHER


@dataclass(frozen=True)
class Query:
    # SQL-запит, що проходить через фільтри SqlValidator і ParameterBinder

    sql: Any
    params: Any = None
    keyword: str = ""
    kind: str = ""
    positional: int = 0                     # кількість маркерів «?»
    numbered: int = 0                       # найбільший номер маркера «?N»
    named: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class QueryResult:
    # Результат, який отримує Cursor від фільтра ResultMapper

    rows: list
    columns: Tuple[str, ...]
    description: Optional[tuple]
    rowcount: int
    lastrowid: Optional[int]
    kind: str
