# Лексичний розбір SQL-тексту для попередньої перевірки (ФВ-5).

""""
Сканер пропускає рядкові літерали, ідентифікатори в лапках і коментарі,
щоб символи «;», «?» та «:ім'я» всередині них не враховувалися.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

from .. import messages
from ..exceptions import QueryError

_QUOTES = "'\"`"
_NAME_PREFIXES = ":@$"


@dataclass(frozen=True)
class ScanResult:
    statements: int
    keyword: str
    positional: int
    numbered: int
    named: FrozenSet[str]


def _closing_quote(sql: str, start: int, quote: str) -> int:
    # Індекс закривальної лапки; подвоєна лапка всередині — це екранування
    i = start + 1
    while True:
        j = sql.find(quote, i)
        if j == -1:
            raise QueryError(messages.SQL_UNCLOSED_QUOTE.format(quote))
        if j + 1 < len(sql) and sql[j + 1] == quote:
            i = j + 2
            continue
        return j


def _read_word(sql: str, start: int) -> int:
    end = start
    while end < len(sql) and (sql[end].isalnum() or sql[end] == "_"):
        end += 1
    return end


def scan(sql: str) -> ScanResult:
    statements = positional = numbered = 0
    keyword = ""
    named = set()
    has_content = False
    i, n = 0, len(sql)

    while i < n:
        c = sql[i]
        if c in _QUOTES:
            i = _closing_quote(sql, i, c) + 1
            has_content = True
        elif c == "[":
            j = sql.find("]", i + 1)
            if j == -1:
                raise QueryError(messages.SQL_UNCLOSED_BRACKET)
            i, has_content = j + 1, True
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j == -1:
                raise QueryError(messages.SQL_UNCLOSED_COMMENT)
            i = j + 2
        elif c == ";":
            if has_content:
                statements += 1
                has_content = False
            i += 1
        elif c.isspace():
            i += 1
        elif c.isalpha() or c == "_":
            end = _read_word(sql, i)
            if not has_content and statements == 0:
                keyword = sql[i:end].upper()
            i, has_content = end, True
        elif c == "?":
            end = _read_word(sql, i + 1)
            digits = sql[i + 1:end]
            if digits.isdigit():
                numbered = max(numbered, int(digits))
            else:
                positional += 1
                end = i + 1
            i, has_content = end, True
        elif c in _NAME_PREFIXES and i + 1 < n and (sql[i + 1].isalpha() or sql[i + 1] == "_"):
            end = _read_word(sql, i + 1)
            named.add(sql[i + 1:end])
            i, has_content = end, True
        else:
            i, has_content = i + 1, True

    if has_content:
        statements += 1
    return ScanResult(statements, keyword, positional, numbered, frozenset(named))
