# Тести, що перевіряють дотримання принципів SOLID через підстановку реалізацій

import os
import tempfile
import unittest

from sql_driver import (DatabaseGateway, LoggingSQLiteDriver, QueryError, QueryFilter,
                        QueryJournal, QueryLogger, SQLiteConnection, SQLiteDriver, SqliteGateway)
from sql_driver.executor import QueryExecutor, default_filters
from sql_driver.gateway import RawResult
from sql_console.controller import ConsoleController


class FakeGateway(DatabaseGateway):
    # Шлюз-замінник без СУБД: повертає заздалегідь задані рядки

    def __init__(self):
        self.opened = None
        self.calls = []
        self.closed = False

    def open(self, path):
        self.opened = path

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return RawResult([(1, "a")], (("id",), ("name",)), -1, None)

    def executescript(self, script):
        self.calls.append((script, None))

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True

    @property
    def in_transaction(self):
        return False


class CountingFilter(QueryFilter):
    """Додатковий фільтр: рахує запити й передає дані далі без змін."""

    def __init__(self):
        self.count = 0

    def process(self, data):
        self.count += 1
        return data


class MemoryJournal(QueryJournal):
    """Мінімальний журнал, що реалізує лише log_query() (ISP)."""

    def __init__(self):
        self.records = []

    def log_query(self, query, result, error, duration_ms, in_transaction):
        self.records.append((query.kind, error is None))


class SolidTest(unittest.TestCase):
    def test_dip_driver_works_with_any_gateway(self):
        conn = SQLiteDriver(gateway_factory=FakeGateway).connect(":memory:")
        cur = conn.cursor().execute("SELECT id, name FROM t WHERE id = ?", (1,))
        self.assertEqual(cur.fetchall(), [(1, "a")])
        self.assertEqual(cur.columns, ("id", "name"))
        gateway = conn._gateway
        self.assertEqual(gateway.calls, [("SELECT id, name FROM t WHERE id = ?", (1,))])
        conn.close()
        self.assertTrue(gateway.closed)

    def test_ocp_new_filter_without_changing_executor(self):
        gateway = SqliteGateway()
        gateway.open(":memory:")
        counter = CountingFilter()
        conn = SQLiteConnection(gateway, filters=[counter] + default_filters(gateway))
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.execute("SELECT 2")
        self.assertEqual(counter.count, 2)
        conn.close()

    def test_isp_minimal_journal_is_enough_for_executor(self):
        journal = MemoryJournal()
        gateway = SqliteGateway()
        gateway.open(":memory:")
        executor = QueryExecutor(gateway, journal)
        executor.execute("SELECT 1")
        with self.assertRaises(QueryError):
            executor.execute("")
        self.assertEqual(journal.records, [("SELECT", True), ("", False)])
        gateway.close()

    def test_lsp_logging_connection_substitutes_base(self):
        def scenario(conn):
            cur = conn.cursor()
            cur.execute("CREATE TABLE t (a INTEGER)")
            cur.executemany("INSERT INTO t VALUES (?)", [(1,), (2,)])
            conn.commit()
            result = cur.execute("SELECT sum(a) FROM t").fetchone()
            conn.close()
            return result

        with tempfile.TemporaryDirectory() as tmp:
            plain = SQLiteDriver().connect(os.path.join(tmp, "a.db"))
            logged = LoggingSQLiteDriver(QueryLogger(os.path.join(tmp, "j.db"))).connect(
                os.path.join(tmp, "b.db"))
            self.assertEqual(scenario(plain), scenario(logged))

    def test_dip_controller_accepts_injected_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = QueryLogger(os.path.join(tmp, "j.db"))
            controller = ConsoleController(SQLiteDriver(gateway_factory=FakeGateway), logger)
            controller.open_database(":memory:")
            self.assertEqual(controller.execute("SELECT * FROM t").rows, [(1, "a")])
            controller.close_database()


if __name__ == "__main__":
    unittest.main()
