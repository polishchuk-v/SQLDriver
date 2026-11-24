# Модальні діалоги з українськими написами на кнопках.

""" Стандартний tkinter.messagebox показує кнопки мовою операційної системи
або англійською (Yes / No), що суперечить вимогам до інтерфейсу. Тому
діалоги підтвердження й повідомлення реалізовано окремо.
Клавіші: Enter — натиснути вибрану кнопку, Esc — відмова, Tab / Shift+Tab —
перехід між кнопками.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Sequence, Tuple

ICONS = {"error": "::tk::icons::error", "warning": "::tk::icons::warning",
         "info": "::tk::icons::information", "question": "::tk::icons::question"}

YES, NO, CANCEL, OK = "Так", "Ні", "Скасувати", "Гаразд"


class _Dialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, message: str, icon: str,
                 buttons: Sequence[Tuple[str, object]], default: int, escape_value: object):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        if parent.winfo_toplevel().winfo_viewable():
            self.transient(parent.winfo_toplevel())
        self.result = escape_value

        body = ttk.Frame(self, padding=(16, 16, 16, 8))
        body.pack(fill="both", expand=True)
        try:
            ttk.Label(body, image=ICONS[icon]).pack(side="left", anchor="n", padx=(0, 12))
        except tk.TclError:
            pass                                  # значок недоступний — не критично
        ttk.Label(body, text=message, wraplength=380, justify="left").pack(side="left")

        bar = ttk.Frame(self, padding=(16, 0, 16, 12))
        bar.pack(fill="x")
        widgets = []
        for text, value in buttons:
            button = ttk.Button(bar, text=text, command=lambda v=value: self._close(v))
            button.pack(side="right", padx=(6, 0))
            button.bind("<Return>", lambda e: (e.widget.invoke(), "break")[1])
            widgets.append(button)
        for button in reversed(widgets):          # порядок Tab — зліва направо
            button.lift()

        self.bind("<Escape>", lambda _e: self._close(escape_value))
        self.protocol("WM_DELETE_WINDOW", lambda: self._close(escape_value))
        self._center(parent)
        self.grab_set()
        self.focus_force()
        widgets[default].focus_set()

    def _center(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_reqwidth()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _close(self, value: object) -> None:
        self.result = value
        self.grab_release()
        self.destroy()

    def show(self) -> object:
        self.wait_window()
        return self.result


def ask_yes_no(parent: tk.Misc, title: str, message: str, default_yes: bool = False,
               icon: str = "question") -> bool:
    # Так / Ні. Esc означає «Ні»
    buttons = [(NO, False), (YES, True)]          # праворуч наліво: «Так» ліворуч від «Ні»
    return bool(_Dialog(parent, title, message, icon, buttons,
                        default=1 if default_yes else 0, escape_value=False).show())


def ask_yes_no_cancel(parent: tk.Misc, title: str, message: str) -> Optional[bool]:
    # Так / Ні / Скасувати. Esc означає (None)
    buttons = [(CANCEL, None), (NO, False), (YES, True)]
    return _Dialog(parent, title, message, "question", buttons, default=2,
                   escape_value=None).show()


def show_error(parent: tk.Misc, title: str, message: str) -> None:
    _Dialog(parent, title, message, "error", [(OK, None)], default=0, escape_value=None).show()


def show_info(parent: tk.Misc, title: str, message: str) -> None:
    _Dialog(parent, title, message, "info", [(OK, None)], default=0, escape_value=None).show()
