# Тести журналювання у службовій БД (ФВ-10)

import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import sql_driver
from sql_driver import QueryError, QueryLogger


class JournalTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "data.db")
        self.journal = os.path.join(self._tmp.name, "journal.db")

    def tearDown(self):
        self._tmp.cleanup()

    def rows(self, sql):
        conn = sqlite3.connect(self.journal)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_schema_has_six_tables(self):
        QueryLogger(self.journal)
        names = {r[0] for r in self.rows("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(names, {"database_files", "connections", "transactions", "queries",
                                 "query_parameters", "error_records"})

    def test_queries_parameters_errors_and_transactions(self):
        with sql_driver.connect(self.db, log_path=self.journal) as conn:
            cur = conn.cursor()
            cur.execute("CREATE TABLE t (a TEXT)")
            cur.execute("INSERT INTO t VALUES (?)", ("x",))
            with self.assertRaises(QueryError):
                cur.execute("SELECT * FROM nope")
            conn.commit()

        self.assertEqual(self.rows("SELECT query_type, status FROM queries ORDER BY id"),
                         [("DDL", "SUCCESS"), ("DML", "SUCCESS"), ("SELECT", "ERROR")])
        self.assertEqual(self.rows("SELECT position, value_text, value_type FROM query_parameters"),
                         [("1", "x", "str")])
        self.assertEqual(self.rows("SELECT error_type FROM error_records"), [("QueryError",)])
        self.assertEqual(self.rows("SELECT outcome FROM transactions"), [("COMMIT",)])
        self.assertEqual(self.rows("SELECT count(*) FROM queries WHERE transaction_id IS NOT NULL"),
                         [(2,)])
        self.assertEqual(self.rows("SELECT status FROM connections"), [("CLOSED",)])

    def test_rollback_on_close_and_recent_queries(self):
        conn = sql_driver.connect(self.db, log_path=self.journal)
        conn.cursor().execute("CREATE TABLE t (a)")
        conn.cursor().execute("INSERT INTO t VALUES (1)")
        conn.close()
        self.assertEqual(self.rows("SELECT outcome FROM transactions"), [("ROLLBACK",)])
        recent = QueryLogger(self.journal).recent_queries(1)
        self.assertEqual(recent[0][2], "INSERT INTO t VALUES (1)")
        self.assertEqual(recent[0][1], "data.db")

    def test_journal_failure_does_not_break_query(self):
        conn = sql_driver.connect(self.db, log_path=self.journal)
        logger = conn._journal._logger
        with mock.patch.object(logger, "run", side_effect=QueryError("збій")), \
                self.assertLogs("sql_driver", level="WARNING"):
            result = conn.cursor().execute("SELECT 1").fetchone()
        self.assertEqual(result, (1,))
        conn.close()


if __name__ == "__main__":
    unittest.main()
