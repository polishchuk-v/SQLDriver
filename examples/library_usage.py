import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sql_driver  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")
JOURNAL_PATH = os.path.join(tempfile.gettempdir(), "sql_driver_example_journal.db")


def main() -> None:
    if not os.path.exists(DB_PATH):
        print("Спочатку створіть демонстраційну БД: python examples/create_demo_db.py")
        return

    with sql_driver.connect(DB_PATH, log_path=JOURNAL_PATH) as conn:
        cur = conn.cursor()

        print("Товари дешевші за 10 000 грн:")
        cur.execute("SELECT name, price FROM goods WHERE price < ? ORDER BY price", (10000,))
        for name, price in cur:
            print(f"  {name}: {price:.2f} грн")

        print("\nПеревірка запиту до виконання та помилки СУБД:")
        for sql, params in (("SELECT 1; DROP TABLE goods", None),
                            ("SELECT * FROM goods WHERE id = ?", ()),
                            ("SELECT * FROM suppliers", None),
                            ("DELETE FROM categories WHERE id = 1", None)):
            try:
                cur.execute(sql, params)
            except sql_driver.DriverError as error:
                print(f"  {sql!r}: {error.message}")

        conn.rollback()

    print("\nОстанні записи журналу:")
    for row in sql_driver.QueryLogger(JOURNAL_PATH).recent_queries(4):
        print(f"  {row[0]}  {row[4]:<7}  {row[2]}")


if __name__ == "__main__":
    main()
