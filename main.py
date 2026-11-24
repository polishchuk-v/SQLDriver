import importlib.util
import sys

if sys.version_info < (3, 8):
    sys.exit("Потрібен Python 3.8 або новіший, а запущено " + sys.version.split()[0] + ".\n"
             "У PyCharm: File → Settings → Project → Python Interpreter.")
if importlib.util.find_spec("tkinter") is None:
    sys.exit("У цьому інтерпретаторі Python немає модуля tkinter.\n"
             "Windows: перевстановіть Python з python.org і позначте «tcl/tk and IDLE».\n"
             "Linux: sudo apt install python3-tk")

from sql_console.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
