# Шар інтерфейсу застосунку: головне вікно

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Sequence

from sql_driver import DriverError

from . import config
from .controller import ConsoleController, ExecutionReport
from . import dialogs
from .help_dialog import HelpDialog

JOURNAL_COLUMNS = ("Час", "База даних", "Запит", "Тип", "Статус", "Рядків", "мс", "Помилка")
JOURNAL_WIDTHS = (175, 110, 360, 70, 80, 60, 60, 360)
DB_TYPES = [("База даних SQLite", "*.db *.sqlite *.sqlite3"), ("Усі файли", "*.*")]


class MainWindow:
    def __init__(self, root: tk.Tk, controller: ConsoleController) -> None:
        self.root = root
        self.controller = controller
        root.title(config.APP_TITLE)
        root.geometry(config.WINDOW_SIZE)
        root.minsize(800, 500)
        root.option_add("*Font", config.FONT)
        self._build()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()
        self.editor.focus_set()

    # --- побудова інтерфейсу -------------------------------------------------
    def _build(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(6, 6, 6, 0))
        toolbar.pack(fill="x")
        self.buttons = {}
        for key, text, command in (
            ("open", "Відкрити БД (Ctrl+O)", self.open_database),
            ("create", "Створити БД (Ctrl+N)", self.create_database),
            ("run", "Виконати (F5)", self.run_query),
            ("commit", "Зберегти зміни (Ctrl+S)", self.commit),
            ("rollback", "Скасувати зміни", self.rollback),
            ("help", "Довідка (F1)", self.show_help),
        ):
            button = ttk.Button(toolbar, text=text, command=command)
            button.pack(side="left", padx=(0, 6))
            self.buttons[key] = button

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(body)
        ttk.Label(left, text="Таблиці").pack(anchor="w")
        self.tables = tk.Listbox(left, width=24, exportselection=False, activestyle="dotbox")
        self.tables.pack(fill="both", expand=True)
        body.add(left, weight=1)

        right = ttk.PanedWindow(body, orient="vertical")
        body.add(right, weight=5)

        editor_frame = ttk.Frame(right)
        ttk.Label(editor_frame, text="SQL-запит").pack(anchor="w")
        self.editor = tk.Text(editor_frame, height=8, undo=True, wrap="word",
                              font=config.EDITOR_FONT)
        self.editor.pack(fill="both", expand=True)
        right.add(editor_frame, weight=1)

        self.tabs = ttk.Notebook(right)
        self.result = self._make_tree(self.tabs)
        self.journal = self._make_tree(self.tabs)
        self.tabs.add(self.result.master, text="Результат")
        self.tabs.add(self.journal.master, text="Журнал запитів")
        self._set_columns(self.journal, JOURNAL_COLUMNS, JOURNAL_WIDTHS)
        right.add(self.tabs, weight=3)

        self.status = ttk.Label(self.root, padding=(8, 4), relief="sunken", anchor="w")
        self.status.pack(fill="x", side="bottom")

    @staticmethod
    def _make_tree(parent: tk.Misc) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, show="headings", selectmode="browse")
        vbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _bind_keys(self) -> None:
        r = self.root
        r.bind("<F1>", lambda _e: self.show_help())
        r.bind("<F5>", lambda _e: self.run_query())
        r.bind("<Control-Return>", lambda _e: self._break(self.run_query))
        # Ctrl+літера має працювати й в українській розкладці, тому клавіші
        # розпізнаються за кількома позначеннями (keysym).
        # У Windows код клавіші (virtual-key code) не залежить від розкладки.
        self._shortcuts, self._win_keycodes = {}, {}
        for keysyms, keycode, action in ((("o", "Cyrillic_shcha"), 79, self.open_database),
                                         (("n", "Cyrillic_te"), 78, self.create_database),
                                         (("s", "Ukrainian_i", "Cyrillic_yeru"), 83, self.commit)):
            self._win_keycodes[keycode] = action
            for keysym in keysyms:
                self._shortcuts[keysym.lower()] = action
        r.bind("<Control-Key>", self._on_control_key)
        self.editor.bind("<Control-Key>", self._on_control_key)
        r.bind("<Escape>", lambda _e: self.on_escape())
        # Enter натискає кнопку, на якій стоїть фокус (зокрема в стандартних діалогах)
        r.bind_class("TButton", "<Return>", self._invoke_focused_button)
        # Tab у полі запиту переводить фокус, а не вставляє табуляцію
        self.editor.bind("<Tab>", lambda e: self._focus(e.widget.tk_focusNext()))
        self.editor.bind("<Shift-Tab>", lambda e: self._focus(e.widget.tk_focusPrev()))
        self.editor.bind("<ISO_Left_Tab>", lambda e: self._focus(e.widget.tk_focusPrev()))
        self.editor.bind("<Control-Return>", lambda _e: self._break(self.run_query))
        self.tables.bind("<Double-Button-1>", lambda _e: self.preview_table())
        self.tables.bind("<Return>", lambda _e: self.preview_table())

    def _invoke_focused_button(self, event: tk.Event) -> str:
        widget = event.widget
        if isinstance(widget, str):        # кнопка стандартного діалогу Tcl/Tk
            self.root.tk.call(widget, "invoke")
        else:
            widget.invoke()
        return "break"

    def _on_control_key(self, event: tk.Event) -> str:
        action = self._shortcuts.get(event.keysym.lower())
        if action is None and sys.platform == "win32":
            action = self._win_keycodes.get(event.keycode)
        if action is None:
            return ""
        action()
        return "break"

    @staticmethod
    def _focus(widget: tk.Misc) -> str:
        widget.focus_set()
        return "break"

    @staticmethod
    def _break(action: Callable[[], None]) -> str:
        action()
        return "break"

    # --- дії користувача -----------------------------------------------------
    def open_database(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Відкрити базу даних",
                                          filetypes=DB_TYPES)
        if path:
            self._switch_database(path)

    def create_database(self) -> None:
        path = filedialog.asksaveasfilename(parent=self.root, title="Створити базу даних",
                                            defaultextension=".db", filetypes=DB_TYPES,
                                            confirmoverwrite=False)
        if not path:
            return
        if os.path.exists(path):
            dialogs.show_info(self.root, config.APP_TITLE,
                              "Файл уже існує, тому його буде відкрито.")
        self._switch_database(path)

    def _switch_database(self, path: str) -> None:
        if not self._resolve_unsaved_changes():
            return
        if self._attempt(lambda: self.controller.open_database(path)):
            self._clear_tree(self.result)
            self.refresh(f"Відкрито базу даних «{self.controller.database_name}».")

    def run_query(self) -> None:
        sql = self.editor.get("1.0", "end-1c")
        if self.controller.needs_confirmation(sql) and not dialogs.ask_yes_no(
                self.root, "Підтвердження", "Ця інструкція видаляє дані або таблиці.\n"
                                            "Ви дійсно бажаєте її виконати?", icon="warning"):
            self._set_status("Виконання скасовано.")
            return
        report = self._attempt(lambda: self.controller.execute(sql))
        if report:
            self._show_report(report, tables=self.controller.changes_schema(sql))

    def preview_table(self) -> None:
        selection = self.tables.curselection()
        if not selection:
            return
        name = self.tables.get(selection[0])
        report = self._attempt(lambda: self.controller.preview_table(name))
        if report:
            self._show_report(report, f"Таблиця «{name}»: ")

    def commit(self) -> None:
        if not self.controller.has_unsaved_changes:
            self._set_status("Незбережених змін немає.")
            return
        if self._attempt(self.controller.commit):
            self.refresh("Зміни збережено.", tables=False)

    def rollback(self) -> None:
        if not self.controller.has_unsaved_changes:
            self._set_status("Незбережених змін немає.")
            return
        if not dialogs.ask_yes_no(self.root, "Підтвердження",
                                  "Скасувати всі зміни після останнього збереження?",
                                  icon="warning"):
            return
        if self._attempt(self.controller.rollback):
            self.refresh("Зміни скасовано.")

    def show_help(self) -> None:
        HelpDialog(self.root)

    def on_escape(self) -> None:
        if dialogs.ask_yes_no(self.root, config.APP_TITLE, "Завершити роботу з програмою?"):
            self.on_close()

    def on_close(self) -> None:
        if self._resolve_unsaved_changes():
            self.controller.close_database()
            self.root.destroy()

    # --- допоміжне -----------------------------------------------------------
    def _resolve_unsaved_changes(self) -> bool:
        if not self.controller.has_unsaved_changes:
            return True
        answer = dialogs.ask_yes_no_cancel(
            self.root, "Незбережені зміни", "У базі даних є незбережені зміни. Зберегти їх?")
        if answer is None:
            return False
        action = self.controller.commit if answer else self.controller.rollback
        return self._attempt(action) is not False

    def _attempt(self, action: Callable):
        try:
            result = action()
        except DriverError as exc:
            self._set_status(exc.message, error=True)
            dialogs.show_error(self.root, "Помилка", exc.message)
            self._refresh_journal()
            return False
        return True if result is None else result

    def _show_report(self, report: ExecutionReport, prefix: str = "",
                     tables: bool = False) -> None:
        if report.is_selection:
            self._set_columns(self.result, report.columns, _widths(report))
            self._fill(self.result, report.rows)
            self.tabs.select(0)
            text = f"{prefix}отримано рядків: {report.total_rows}."
            if report.truncated:
                text += f" Показано перші {len(report.rows)}."
        else:
            text = "Інструкцію виконано."
            if report.rowcount >= 0:
                text += f" Змінено рядків: {report.rowcount}."
            if self.controller.has_unsaved_changes:
                text += " Щоб зберегти зміни, натисніть Ctrl+S."
        self.refresh(text[0].upper() + text[1:], tables=tables)

    def refresh(self, status: str = "", tables: bool = True) -> None:
        is_open = self.controller.is_open
        unsaved = self.controller.has_unsaved_changes
        name = self.controller.database_name
        self.root.title(f"{config.APP_TITLE} — {name}{' *' if unsaved else ''}"
                        if name else config.APP_TITLE)
        for key in ("run", "commit", "rollback"):
            self.buttons[key].state(["!disabled"] if is_open else ["disabled"])
        if tables:
            self._refresh_tables()
        self._refresh_journal()
        self._set_status(status or ("Готово до роботи." if is_open else
                                    "Відкрийте (Ctrl+O) або створіть (Ctrl+N) базу даних."))

    def _refresh_tables(self) -> None:
        selected = self.tables.curselection()
        self.tables.delete(0, "end")
        names = self._attempt(self.controller.tables) if self.controller.is_open else []
        for table in names or []:
            self.tables.insert("end", table)
        if selected and selected[0] < self.tables.size():
            self.tables.selection_set(selected[0])

    def _refresh_journal(self) -> None:
        try:
            rows = self.controller.journal_rows()
        except DriverError as exc:
            self._set_status(exc.message, error=True)
            return
        self._fill(self.journal, rows)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status.configure(text=text, foreground="#b00020" if error else "")

    @staticmethod
    def _set_columns(tree: ttk.Treeview, columns: Sequence[str], widths: Sequence[int]) -> None:
        ids = [f"c{i}" for i in range(len(columns))]
        tree.configure(columns=ids)
        for cid, title, width in zip(ids, columns, widths):
            tree.heading(cid, text=title, anchor="w")
            tree.column(cid, width=width, minwidth=40, stretch=False, anchor="w")

    @classmethod
    def _fill(cls, tree: ttk.Treeview, rows: Sequence[tuple]) -> None:
        cls._clear_tree(tree, keep_columns=True)
        for row in rows:
            tree.insert("", "end", values=[_display(v) for v in row])

    @staticmethod
    def _clear_tree(tree: ttk.Treeview, keep_columns: bool = False) -> None:
        tree.delete(*tree.get_children())
        if not keep_columns:
            tree.configure(columns=())


def _widths(report: ExecutionReport) -> list:
    widths = []
    for index, title in enumerate(report.columns):
        longest = max([len(title)] + [len(_display(r[index])) for r in report.rows[:50]])
        widths.append(min(max(60, longest * 8 + 16), 400))
    return widths


def _display(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return f"<{len(value)} байт>"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value).replace("\n", " ")
