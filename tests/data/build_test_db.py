"""Створює тестову базу даних tests/data/test_shop.db зі schema.sql і seed.sql.

Запуск: python tests/data/build_test_db.py
Тести не змінюють цей файл: перед кожним тестом він копіюється до тимчасової папки.
"""

import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "test_shop.db")


def build(path: str = DB_PATH) -> str:
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    try:
        for name in ("schema.sql", "seed.sql"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
    return path


if __name__ == "__main__":
    print("Тестову базу даних створено:", build())
