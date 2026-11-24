# Спільні засоби тестів: робоча копія тестової БД у тимчасовій папці

import os
import shutil
import tempfile
import unittest

from tests.data.build_test_db import DB_PATH, build


class TestDatabaseCase(unittest.TestCase):
    """Базовий клас тестів, яким потрібна тестова БД «Інтернет-магазин».

    Перед кожним тестом файл tests/data/test_shop.db копіюється до тимчасової
    папки, тому тести не впливають один на одного й не змінюють еталонну БД.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DB_PATH):
            build()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "shop.db")
        self.journal = os.path.join(self._tmp.name, "journal.db")
        shutil.copyfile(DB_PATH, self.db)

    def tearDown(self):
        self._tmp.cleanup()
