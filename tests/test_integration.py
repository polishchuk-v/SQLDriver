# Інтеграційні тести на тестовій БД «Інтернет-магазин» (tests/data/test_shop.db)

import sqlite3

import sql_driver
from sql_driver import QueryError
from sql_console.controller import ConsoleController
from tests.fixtures import TestDatabaseCase


class QueriesTest(TestDatabaseCase):
    def test_select_with_join_and_parameters(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor().execute(
                "SELECT g.name FROM goods g JOIN categories c ON c.id = g.category_id "
                "WHERE c.name = ? AND g.price < ? ORDER BY g.price", ("Аксесуари", 1000))
            self.assertEqual(cur.fetchall(), [("Чохол O'Neil для смартфона",),
                                              ("Миша Logitech M185",)])

    def test_aggregate_and_view(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT customer, total FROM order_totals ORDER BY order_id")
            self.assertEqual(cur.fetchall(), [("Іваненко Олена", 34097.0),
                                              ("Коваль Максим", 17898.0),
                                              ("Іваненко Олена", 19998.0)])
            cur.execute("SELECT count(*), sum(stock) FROM goods")
            self.assertEqual(cur.fetchone(), (7, 149))

    def test_named_parameters_and_quote_in_value(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor().execute("SELECT id FROM goods WHERE name = :name",
                                        {"name": "Чохол O'Neil для смартфона"})
            self.assertEqual(cur.fetchone(), (7,))

    def test_injection_attempt_returns_nothing(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor().execute("SELECT * FROM customers WHERE email = ?",
                                        ("x' OR '1'='1",))
            self.assertEqual(cur.fetchall(), [])

    def test_executemany_rowcount(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor().executemany(
                "UPDATE goods SET stock = stock + ? WHERE id = ?", [(1, 1), (1, 2), (1, 99)])
            self.assertEqual(cur.rowcount, 2)


class IntegrityTest(TestDatabaseCase):
    def assert_rejected(self, sql, params, fragment):
        with sql_driver.connect(self.db) as conn:
            with self.assertRaises(QueryError) as ctx:
                conn.cursor().execute(sql, params)
            self.assertIn(fragment, ctx.exception.message)

    def test_restrict_delete_of_referenced_rows(self):
        self.assert_rejected("DELETE FROM categories WHERE id = ?", (1,), "зовнішній ключ")
        self.assert_rejected("DELETE FROM customers WHERE id = ?", (1,), "зовнішній ключ")

    def test_unreferenced_row_can_be_deleted(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor().execute("DELETE FROM categories WHERE id = ?", (4,))
            self.assertEqual(cur.rowcount, 1)

    def test_cascade_delete_of_order_items(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM orders WHERE id = ?", (1,))
            cur.execute("SELECT count(*) FROM order_items WHERE order_id = 1")
            self.assertEqual(cur.fetchone(), (0,))

    def test_check_unique_not_null_constraints(self):
        self.assert_rejected("UPDATE goods SET price = ? WHERE id = 1", (0,), "умові перевірки")
        self.assert_rejected("INSERT INTO orders (customer_id, created_at, status) "
                             "VALUES (1, '2026-11-02', ?)", ("LOST",), "умові перевірки")
        self.assert_rejected("INSERT INTO customers (name, email) VALUES (?, ?)",
                             ("Тест", "koval@example.com"), "унікальним")
        self.assert_rejected("INSERT INTO goods (category_id, price) VALUES (1, 10)", None,
                             "не може бути порожнім")

    def test_insert_with_missing_foreign_key(self):
        self.assert_rejected("INSERT INTO order_items VALUES (?, ?, ?, ?)", (2, 99, 1, 10.0),
                             "зовнішній ключ")


class TransactionsTest(TestDatabaseCase):
    def stock(self, goods_id):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT stock FROM goods WHERE id = ?", (goods_id,)).fetchone()[0]
        finally:
            conn.close()

    def test_rollback_restores_data(self):
        conn = sql_driver.connect(self.db)
        conn.cursor().execute("UPDATE goods SET stock = 0 WHERE id = 1")
        conn.rollback()
        conn.close()
        self.assertEqual(self.stock(1), 7)

    def test_commit_persists_and_journal_records_transaction(self):
        with sql_driver.connect(self.db, log_path=self.journal) as conn:
            conn.cursor().execute("UPDATE goods SET stock = stock - 1 WHERE id = ?", (1,))
        self.assertEqual(self.stock(1), 6)
        journal = sqlite3.connect(self.journal)
        try:
            self.assertEqual(journal.execute("SELECT outcome FROM transactions").fetchall(),
                             [("COMMIT",)])
            self.assertEqual(journal.execute("SELECT value_text FROM query_parameters").fetchall(),
                             [("1",)])
        finally:
            journal.close()


class ControllerOnTestDatabaseTest(TestDatabaseCase):
    def test_tables_preview_and_dangerous_statements(self):
        controller = ConsoleController.create(self.journal)
        controller.open_database(self.db)
        self.assertEqual(controller.tables(), ["categories", "customers", "goods", "order_items",
                                               "order_totals", "orders"])
        report = controller.preview_table("order_totals")
        self.assertEqual(report.columns, ("order_id", "customer", "status", "total"))
        self.assertEqual(report.total_rows, 3)
        self.assertTrue(controller.needs_confirmation("DELETE FROM orders"))
        controller.execute("DELETE FROM orders WHERE id = 2")
        self.assertTrue(controller.has_unsaved_changes)
        controller.rollback()
        self.assertEqual(controller.execute("SELECT count(*) FROM orders").rows, [(3,)])
        controller.close_database()
