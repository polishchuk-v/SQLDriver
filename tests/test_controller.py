# Тести шару управління застосунку «SQL-консоль» (без графічного інтерфейсу)

import os
import tempfile
import unittest

from sql_driver import ConnectionError, QueryError
from sql_console.controller import ConsoleController


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "shop.db")
        self.controller = ConsoleController.create(os.path.join(self._tmp.name, "journal.db"))

    def tearDown(self):
        self.controller.close_database()
        self._tmp.cleanup()

    def test_requires_open_database(self):
        self.assertFalse(self.controller.is_open)
        self.assertEqual(self.controller.tables(), [])
        with self.assertRaises(QueryError):
            self.controller.execute("SELECT 1")

    def test_open_execute_and_tables(self):
        self.controller.open_database(self.db)
        self.assertEqual(self.controller.database_name, "shop.db")
        self.controller.execute("CREATE TABLE goods (name TEXT)")
        report = self.controller.execute("INSERT INTO goods VALUES ('a')")
        self.assertFalse(report.is_selection)
        self.assertEqual(report.rowcount, 1)
        self.assertTrue(self.controller.has_unsaved_changes)
        self.controller.commit()
        self.assertFalse(self.controller.has_unsaved_changes)
        self.assertEqual(self.controller.tables(), ["goods"])
        report = self.controller.preview_table("goods")
        self.assertEqual((report.columns, report.rows), (("name",), [("a",)]))

    def test_large_result_is_truncated(self):
        self.controller.open_database(self.db)
        report = self.controller.execute(
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 1500) "
            "SELECT x FROM n")
        self.assertEqual((report.total_rows, len(report.rows), report.truncated),
                         (1500, 1000, True))

    def test_dangerous_statements(self):
        self.assertTrue(self.controller.needs_confirmation("  delete from t"))
        self.assertTrue(self.controller.needs_confirmation("DROP TABLE t"))
        self.assertFalse(self.controller.needs_confirmation("SELECT 'DELETE'"))
        self.assertFalse(self.controller.needs_confirmation("SELECT 'незакрито"))

    def test_journal_rows_are_localized(self):
        self.controller.open_database(self.db)
        with self.assertRaises(QueryError):
            self.controller.execute("SELECT * FROM nope")
        row = self.controller.journal_rows()[0]
        self.assertEqual(row[4], "помилка")
        self.assertNotIn(None, row)

    def test_failed_open_keeps_previous_database(self):
        self.controller.open_database(self.db)
        with self.assertRaises(ConnectionError):
            self.controller.open_database(self._tmp.name)       # папка, а не файл
        self.assertEqual(self.controller.database_name, "shop.db")


if __name__ == "__main__":
    unittest.main()
