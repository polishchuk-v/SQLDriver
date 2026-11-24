# Тести бібліотеки через публічний API: з'єднання, курсор, транзакції, помилки

import os
import tempfile
import unittest

import sql_driver
from sql_driver import (ConnectionError, LoggingConnection, LoggingSQLiteDriver, QueryError,
                        QueryLogger, SQLiteConnection, SQLiteDriver)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.db = os.path.join(self.dir, "test.db")

    def tearDown(self):
        self._tmp.cleanup()


class ConnectTest(TempDirTestCase):
    def test_facade_selects_connection_class(self):
        with sql_driver.connect(self.db) as conn:
            self.assertIsInstance(conn, SQLiteConnection)
            self.assertNotIsInstance(conn, LoggingConnection)
        with sql_driver.connect(self.db, log_path=os.path.join(self.dir, "j.db")) as conn:
            self.assertIsInstance(conn, LoggingConnection)

    def test_factory_method_in_subclasses(self):
        logger = QueryLogger(os.path.join(self.dir, "j.db"))
        self.assertIsInstance(SQLiteDriver().connect(self.db), SQLiteConnection)
        self.assertIsInstance(LoggingSQLiteDriver(logger).connect(self.db), LoggingConnection)

    def test_bad_paths(self):
        for path in ("", "   ", None, 5, self.dir, os.path.join(self.dir, "нема", "x.db")):
            with self.subTest(path=path), self.assertRaises(ConnectionError):
                sql_driver.connect(path)

    def test_not_a_database_file(self):
        with open(self.db, "w", encoding="utf-8") as f:
            f.write("це не база даних" * 100)
        with self.assertRaises(ConnectionError) as ctx:
            sql_driver.connect(self.db)
        self.assertIn("не є базою даних", ctx.exception.message)

    def test_memory_database(self):
        with sql_driver.connect(":memory:") as conn:
            self.assertEqual(conn.cursor().execute("SELECT 2 + 2").fetchone(), (4,))


class CursorTest(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.conn = sql_driver.connect(self.db)
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        self.cur.executemany("INSERT INTO t (name) VALUES (?)", [("a",), ("b",), ("c",)])

    def tearDown(self):
        self.conn.close()
        super().tearDown()

    def test_executemany_rowcount_and_lastrowid(self):
        self.assertEqual(self.cur.rowcount, 3)
        self.assertEqual(self.cur.lastrowid, 3)

    def test_fetch_methods(self):
        self.cur.execute("SELECT name FROM t ORDER BY id")
        self.assertEqual(self.cur.description[0][0], "name")
        self.assertEqual(self.cur.rowcount, 3)
        self.assertEqual(self.cur.fetchone(), ("a",))
        self.assertEqual(self.cur.fetchmany(1), [("b",)])
        self.assertEqual(self.cur.fetchall(), [("c",)])
        self.assertIsNone(self.cur.fetchone())

    def test_iteration_and_arraysize(self):
        self.cur.execute("SELECT id FROM t")
        self.cur.arraysize = 2
        self.assertEqual(len(self.cur.fetchmany()), 2)
        self.assertEqual(list(self.cur), [(3,)])

    def test_fetch_before_execute_and_bad_size(self):
        cur = self.conn.cursor()
        with self.assertRaises(QueryError):
            cur.fetchall()
        cur.execute("SELECT 1")
        for size in (0, -1, "2", True):
            with self.subTest(size=size), self.assertRaises(QueryError):
                cur.fetchmany(size)

    def test_errors_are_translated(self):
        cases = {"SELECT * FROM nope": "не знайдено",
                 "INSERT INTO t (name) VALUES ('a')": "унікальним",
                 "INSERT INTO t (id) VALUES (10)": "не може бути порожнім",
                 "SELEC 1": "Синтаксична"}
        for sql, text in cases.items():
            with self.subTest(sql=sql), self.assertRaises(QueryError) as ctx:
                self.cur.execute(sql)
            self.assertIn(text, ctx.exception.message)
            self.assertTrue(ctx.exception.detail)        # оригінал зберігається

    def test_injection_is_passed_as_value(self):
        self.cur.execute("SELECT count(*) FROM t WHERE name = ?", ("a' OR '1'='1",))
        self.assertEqual(self.cur.fetchone(), (0,))

    def test_closed_cursor_and_connection(self):
        self.cur.close()
        with self.assertRaises(QueryError):
            self.cur.execute("SELECT 1")
        cur = self.conn.cursor()
        self.conn.close()
        self.assertTrue(cur.closed)
        with self.assertRaises(ConnectionError):
            self.conn.cursor()
        with self.assertRaises(ConnectionError):
            self.conn.commit()
        self.conn.close()                                # повторне закриття безпечне


class TransactionTest(TempDirTestCase):
    def setUp(self):
        super().setUp()
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            cur.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, "
                        "parent_id INTEGER NOT NULL REFERENCES parent(id))")
            cur.execute("INSERT INTO parent VALUES (1)")
            cur.execute("INSERT INTO child VALUES (1, 1)")

    def count(self, table):
        with sql_driver.connect(self.db) as conn:
            return conn.cursor().execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def test_commit_and_rollback(self):
        conn = sql_driver.connect(self.db)
        cur = conn.cursor()
        cur.execute("INSERT INTO parent VALUES (2)")
        self.assertTrue(conn.in_transaction)
        conn.rollback()
        self.assertEqual(self.count("parent"), 1)
        cur.execute("INSERT INTO parent VALUES (3)")
        conn.commit()
        conn.close()
        self.assertEqual(self.count("parent"), 2)

    def test_close_discards_uncommitted_changes(self):
        conn = sql_driver.connect(self.db)
        conn.cursor().execute("INSERT INTO parent VALUES (5)")
        conn.close()
        self.assertEqual(self.count("parent"), 1)

    def test_with_block_rolls_back_on_error(self):
        with self.assertRaises(RuntimeError):
            with sql_driver.connect(self.db) as conn:
                conn.cursor().execute("INSERT INTO parent VALUES (7)")
                raise RuntimeError
        self.assertTrue(conn.closed)
        self.assertEqual(self.count("parent"), 1)

    def test_foreign_keys_enabled(self):
        with sql_driver.connect(self.db) as conn:
            cur = conn.cursor()
            with self.assertRaises(QueryError) as ctx:
                cur.execute("DELETE FROM parent WHERE id = 1")
            self.assertIn("зовнішній ключ", ctx.exception.message)
            with self.assertRaises(QueryError):
                cur.execute("INSERT INTO child VALUES (2, 99)")


if __name__ == "__main__":
    unittest.main()
