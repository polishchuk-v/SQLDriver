# Вікно довідки (F1)

import tkinter as tk
from tkinter import ttk

HELP_TEXT = """\
SQL-консоль — програма для роботи з базами даних SQLite через бібліотеку SQL Driver.

ПОРЯДОК РОБОТИ
1. Відкрийте наявну базу даних (Ctrl+O) або створіть нову (Ctrl+N).
2. Введіть SQL-інструкцію у вікні запиту. За один раз виконується одна інструкція.
3. Виконайте її клавішею F5 або Ctrl+Enter.
4. Результат вибірки з'явиться на вкладці «Результат».
5. Зміни даних (INSERT, UPDATE, DELETE) зберігаються лише після команди
   «Зберегти зміни» (Ctrl+S). Кнопка «Скасувати зміни» повертає дані до
   останнього збереження.
6. Подвійне клацання або Enter на назві таблиці показує її вміст.
7. На вкладці «Журнал запитів» видно всі виконані запити, їхній статус,
   тривалість і текст помилки.

КЛАВІШІ
F1 — довідка
F5, Ctrl+Enter — виконати запит
Ctrl+O — відкрити базу даних
Ctrl+N — створити базу даних
Ctrl+S — зберегти зміни
Enter — підтвердити дію або натиснути вибрану кнопку
Esc — закрити вікно довідки або завершити роботу з програмою
Tab, Shift+Tab — перейти до наступного або попереднього елемента

БЕЗПЕКА ДАНИХ
Перед виконанням DELETE і DROP програма просить підтвердження.
Під час виходу або відкриття іншої бази даних програма запропонує
зберегти незбережені зміни.
Перевірка зовнішніх ключів увімкнена: запис, на який посилаються інші
записи, видалити не вдасться.
"""


class HelpDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Довідка — SQL-консоль")
        self.geometry("640x560")
        self.transient(master)

        text = tk.Text(self, wrap="word", padx=12, pady=12, relief="flat")
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)

        close = ttk.Button(self, text="Закрити (Esc)", command=self.destroy)
        close.pack(pady=8)

        for key in ("<Escape>", "<Return>", "<F1>"):
            self.bind(key, lambda _e: self.destroy())
        self.grab_set()
        self.focus_force()
        close.focus_set()
