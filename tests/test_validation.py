# Тести попередньої перевірки запиту: сканер, SqlValidator, ParameterBinder (ФВ-5)

import unittest

from sql_driver import QueryError
from sql_driver.executor.filters import ParameterBinder, SqlValidator
from sql_driver.executor.query import Query
from sql_driver.executor.scanner import scan


class ScannerTest(unittest.TestCase):
    def test_counts_statements_ignoring_trailing_semicolon(self):
        self.assertEqual(scan("SELECT 1;").statements, 1)
        self.assertEqual(scan("SELECT 1; SELECT 2").statements, 2)

    def test_ignores_markers_inside_strings_and_comments(self):
        result = scan("SELECT ';?', \"a;b\" -- ? ;\n/* :x ; */ FROM t WHERE a = ?")
        self.assertEqual((result.statements, result.positional, result.named), (1, 1, frozenset()))

    def test_detects_marker_styles(self):
        self.assertEqual(scan("SELECT ?, ?").positional, 2)
        self.assertEqual(scan("SELECT ?3, ?1").numbered, 3)
        self.assertEqual(scan("SELECT :a, @b, $c").named, {"a", "b", "c"})

    def test_keyword_of_first_statement(self):
        self.assertEqual(scan("  /* c */ delete FROM t").keyword, "DELETE")

    def test_unclosed_quote_and_comment(self):
        for sql in ("SELECT 'abc", "SELECT 1 /* x", 'SELECT "a', "SELECT [a"):
            with self.subTest(sql=sql), self.assertRaises(QueryError):
                scan(sql)

    def test_doubled_quote_is_escape(self):
        self.assertEqual(scan("SELECT 'it''s; ok'").statements, 1)


class SqlValidatorTest(unittest.TestCase):
    def setUp(self):
        self.validator = SqlValidator()

    def test_rejects_empty_and_non_string(self):
        for sql in ("", "   ", "-- лише коментар", None, 42):
            with self.subTest(sql=sql), self.assertRaises(QueryError):
                self.validator.process(Query(sql))

    def test_rejects_several_statements(self):
        with self.assertRaises(QueryError) as ctx:
            self.validator.process(Query("SELECT 1; DROP TABLE t"))
        self.assertIn("одну", ctx.exception.message)

    def test_classifies_query(self):
        cases = {"SELECT 1": "SELECT", "insert into t values (1)": "DML",
                 "CREATE TABLE t (a)": "DDL", "COMMIT": "TCL", "PRAGMA user_version": "OTHER"}
        for sql, kind in cases.items():
            with self.subTest(sql=sql):
                self.assertEqual(self.validator.process(Query(sql)).kind, kind)


class ParameterBinderTest(unittest.TestCase):
    def bind(self, sql, params):
        return ParameterBinder().process(SqlValidator().process(Query(sql, params)))

    def test_positional_ok(self):
        self.assertEqual(self.bind("SELECT ?, ?", [1, "a"]).params, (1, "a"))
        self.assertEqual(self.bind("SELECT 1", None).params, ())

    def test_count_mismatch(self):
        with self.assertRaises(QueryError) as ctx:
            self.bind("SELECT ?, ?", (1,))
        self.assertIn("(1)", ctx.exception.message)

    def test_named_ok_and_missing(self):
        self.assertEqual(self.bind("SELECT :a", {"a": 1, "b": 2}).params, {"a": 1, "b": 2})
        with self.assertRaises(QueryError):
            self.bind("SELECT :a, :b", {"a": 1})

    def test_wrong_container(self):
        for sql, params in (("SELECT ?", "1"), ("SELECT ?", 5),
                            ("SELECT :a", [1]), ("SELECT ?", {"a": 1}), ("SELECT ?, ?1", (1, 2))):
            with self.subTest(sql=sql, params=params), self.assertRaises(QueryError):
                self.bind(sql, params)

    def test_unsupported_value_type(self):
        with self.assertRaises(QueryError):
            self.bind("SELECT ?", ([1, 2],))


if __name__ == "__main__":
    unittest.main()
