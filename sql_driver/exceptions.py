"""Ієрархія винятків драйвера (ФВ-9).

Усі помилки модуля sqlite3 перетворюються на ці класи в SqliteGateway,
тому прикладний код не залежить від sqlite3 і отримує повідомлення
українською мовою. Оригінальний текст СУБД зберігається в атрибуті detail
для журналу.
"""


class DriverError(Exception):
    # Базовий виняток

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class ConnectionError(DriverError):  # noqa: A001 — назва з вимоги ФВ-9
    """Помилка відкриття, використання або закриття з'єднання"""


class QueryError(DriverError):
    """Помилка перевірки або виконання SQL-запиту"""
