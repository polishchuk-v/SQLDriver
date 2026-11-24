# Точка входу застосунку

from __future__ import annotations

import logging
import sys
import tkinter as tk

from sql_driver import DriverError

from . import config, dialogs
from .controller import ConsoleController
from .main_window import MainWindow

UNEXPECTED = ("Сталася непередбачена помилка, але програма продовжує роботу.\n"
              "Подробиці записано до файлу:\n{0}")


def _setup_logging() -> None:
    config.APP_FOLDER.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(config.ERROR_LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler])


def main() -> int:
    try:
        _setup_logging()
        controller = ConsoleController.create()   # корінь композиції
    except (OSError, DriverError) as exc:
        text = getattr(exc, "message", None) or "Не вдалося підготувати папку програми."
        root = tk.Tk()
        root.withdraw()
        dialogs.show_error(root, config.APP_TITLE, f"{text}\n{config.APP_FOLDER}")
        return 1

    root = tk.Tk()

    def report_unexpected(exc_type, exc, tb) -> None:
        logging.getLogger(config.APP_TITLE).error("Непередбачена помилка",
                                                  exc_info=(exc_type, exc, tb))
        dialogs.show_error(root, config.APP_TITLE, UNEXPECTED.format(config.ERROR_LOG_PATH))

    root.report_callback_exception = report_unexpected
    MainWindow(root, controller)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
