# Налаштування застосунку

from pathlib import Path

APP_TITLE = "SQL-консоль"
APP_FOLDER = Path.home() / ".sql_console"
JOURNAL_PATH = APP_FOLDER / "journal.db"
ERROR_LOG_PATH = APP_FOLDER / "errors.log"

MAX_DISPLAY_ROWS = 1000      # скільки рядків результату показувати в таблиці
JOURNAL_LIMIT = 200          # скільки останніх записів журналу показувати
DANGEROUS_KEYWORDS = {"DELETE", "DROP"}   # інструкції, що потребують підтвердження

WINDOW_SIZE = "1100x700"
FONT = ("Segoe UI", 10)
EDITOR_FONT = ("Consolas", 11)
