import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sql_driver  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")

SCHEMA = [
    """CREATE TABLE categories (
        id    INTEGER PRIMARY KEY,
        name  TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE goods (
        id           INTEGER PRIMARY KEY,
        category_id  INTEGER NOT NULL REFERENCES categories(id),
        name         TEXT NOT NULL,
        price        REAL NOT NULL CHECK (price > 0),
        stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
    )""",
    """CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        customer    TEXT NOT NULL,
        created_at  TEXT NOT NULL
    )""",
    """CREATE TABLE order_items (
        order_id  INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        goods_id  INTEGER NOT NULL REFERENCES goods(id),
        quantity  INTEGER NOT NULL CHECK (quantity > 0),
        PRIMARY KEY (order_id, goods_id)
    )""",
]

CATEGORIES = [("Ноутбуки",), ("Смартфони",), ("Аксесуари",)]
GOODS = [
    (1, "Ноутбук Lenovo IdeaPad 5", 32999.0, 7),
    (1, "Ноутбук ASUS VivoBook 15", 24499.0, 12),
    (2, "Смартфон Samsung Galaxy A55", 15999.0, 20),
    (2, "Смартфон Motorola G84", 9999.0, 15),
    (3, "Миша Logitech M185", 549.0, 60),
    (3, "Навушники JBL Tune 520BT", 1899.0, 35),
]
ORDERS = [("Іваненко О. П.", "2026-10-28"), ("Коваль М. С.", "2026-10-30")]
ORDER_ITEMS = [(1, 1, 1), (1, 5, 2), (2, 3, 1), (2, 6, 1)]


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with sql_driver.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for statement in SCHEMA:
            cur.execute(statement)
        cur.executemany("INSERT INTO categories (name) VALUES (?)", CATEGORIES)
        cur.executemany("INSERT INTO goods (category_id, name, price, stock) "
                        "VALUES (?, ?, ?, ?)", GOODS)
        cur.executemany("INSERT INTO orders (customer, created_at) VALUES (?, ?)", ORDERS)
        cur.executemany("INSERT INTO order_items VALUES (?, ?, ?)", ORDER_ITEMS)
    print(f"Демонстраційну базу даних створено: {DB_PATH}")


if __name__ == "__main__":
    main()
