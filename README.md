# SQL Driver

Курсовий проєкт «Проєкт програмної системи драйвера SQL-запитів до СУБД».

Проєкт складається з двох частин:

- **`sql_driver`** — бібліотека-надбудова над стандартним модулем `sqlite3` за специфікацією PEP 249. Вона перевіряє запит до виконання, видає повідомлення про помилки українською мовою, вмикає перевірку зовнішніх ключів і веде журнал запитів у службовій БД.
- **`sql_console`** — графічний застосунок «SQL-консоль» (tkinter), який працює з базами даних SQLite через бібліотеку `sql_driver`.

Сторонні бібліотеки не потрібні: використовується лише стандартна бібліотека Python.

## Вимоги

- Python 3.8 або новіший.
- Модуль tkinter. У Windows і macOS він входить до стандартного інсталятора Python (у Windows має бути позначено пункт «tcl/tk and IDLE», він увімкнений за замовчуванням). У Linux: `sudo apt install python3-tk`.

## Відкриття в PyCharm

1. Розпакуйте архів і відкрийте папку `SQLDriver` у PyCharm (**File → Open**).
2. Якщо PyCharm попросить вибрати інтерпретатор, вкажіть Python 3.8+ (**Configure Python Interpreter**). Встановлювати пакети не потрібно.
3. У списку конфігурацій запуску (праворуч угорі) вже є:
   - **SQL-консоль** — запуск застосунку;
   - **Тести** — усі модульні тести;
   - **Демо-БД** — повторне створення демонстраційної бази `examples/shop.db`;
   - **Тестова БД** — повторне створення тестової бази `tests/data/test_shop.db`;
   - **Приклад бібліотеки** — використання `sql_driver` без інтерфейсу.

### Якщо програма не запускається

- **Ліворуч від Run червоний хрестик або «No Python interpreter configured»** — інтерпретатор не вибрано: File → Settings → Project: SQLDriver → Python Interpreter → Add Interpreter → System Interpreter (або Virtualenv) → вибрати встановлений Python 3.8+.
- **«У цьому інтерпретаторі Python немає модуля tkinter»** — перевстановіть Python з python.org і позначте пункт «tcl/tk and IDLE».
- **Запуск main.py правою кнопкою миші** працює і без готових конфігурацій: `main.py` → Run 'main'.
- Якщо вікно програми з'явилося, але сталася помилка, подробиці записано у файл `~/.sql_console/errors.log`.

## Запуск з командного рядка

```bash
python main.py                         # застосунок «SQL-консоль»
python -m unittest discover -s tests   # тести
python examples/create_demo_db.py      # демонстраційна БД «Магазин»
python tests/data/build_test_db.py     # тестова БД для інтеграційних тестів
python examples/library_usage.py       # приклад використання бібліотеки
```

У застосунку відкрийте `examples/shop.db` (Ctrl+O) і виконайте, наприклад:

```sql
SELECT g.name, c.name AS category, g.price
FROM goods g JOIN categories c ON c.id = g.category_id
ORDER BY g.price DESC;
```

## Клавіші застосунку

| Клавіша | Дія |
|---|---|
| F1 | довідка |
| F5, Ctrl+Enter | виконати запит |
| Ctrl+O / Ctrl+N | відкрити / створити базу даних |
| Ctrl+S | зберегти зміни |
| Enter | підтвердити дію, натиснути вибрану кнопку, показати вибрану таблицю |
| Esc | закрити довідку або завершити роботу |
| Tab, Shift+Tab | перехід між елементами |

Журнал запитів і файл помилок зберігаються в папці `~/.sql_console/`.

## Використання бібліотеки

```python
import sql_driver

with sql_driver.connect("shop.db", log_path="journal.db") as conn:
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM goods WHERE price < ?", (10000,))
    for row in cur:
        print(row)
```

Вихід із блоку `with` фіксує зміни (або скасовує їх у разі винятку) і закриває з'єднання.

## Структура

```
SQLDriver/
├── main.py                    точка запуску застосунку
├── sql_driver/                бібліотека
│   ├── __init__.py            фасад connect() і атрибути PEP 249
│   ├── driver.py              Driver, SQLiteDriver, LoggingSQLiteDriver (Factory Method)
│   ├── connection.py          Connection, SQLiteConnection, LoggingConnection
│   ├── cursor.py              Cursor
│   ├── executor/              QueryExecutor і фільтри конвеєра (Pipe-Filter)
│   ├── gateway.py             SqliteGateway — адаптер до sqlite3 (Adapter)
│   ├── journal/               QueryLogger і схема службової БД
│   ├── exceptions.py          DriverError, ConnectionError, QueryError
│   ├── messages.py            тексти повідомлень і переклад помилок SQLite
│   └── config.py              налаштування
├── sql_console/               застосунок «SQL-консоль»
│   ├── controller.py          шар управління (без tkinter)
│   ├── main_window.py         головне вікно
│   ├── dialogs.py             діалоги підтвердження українською
│   ├── help_dialog.py         довідка (F1)
│   ├── app.py                 запуск і обробка непередбачених помилок
│   └── config.py              налаштування
├── examples/                  демонстраційна БД і приклад використання
└── tests/                     модульні та інтеграційні тести (unittest)
    ├── data/                  тестова БД: schema.sql, seed.sql, test_shop.db
    ├── fixtures.py            копія тестової БД у тимчасовій папці для кожного тесту
    ├── test_integration.py    сценарії на тестовій БД
    └── test_solid.py          перевірка SOLID через підстановку реалізацій
```

## Тестова база даних

`tests/data/test_shop.db` — база «Інтернет-магазин» (категорії, товари, клієнти, замовлення,
позиції замовлень і представлення `order_totals`) з обмеженнями PRIMARY KEY, FOREIGN KEY
(RESTRICT і CASCADE), UNIQUE, NOT NULL і CHECK. Схема — `tests/data/schema.sql`, дані —
`tests/data/seed.sql`. Перед кожним інтеграційним тестом файл копіюється до тимчасової папки,
тому еталонна БД не змінюється. Її також можна відкрити в «SQL-консолі» (Ctrl+O) для ручної
перевірки, наприклад: `DELETE FROM categories WHERE id = 1` — відхиляється зовнішнім ключем,
`DELETE FROM orders WHERE id = 1` — каскадно видаляє позиції замовлення.
