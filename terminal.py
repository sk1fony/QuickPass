"""Small ANSI helpers. Redirected output and NO_COLOR stay plain."""

import os
import sys

from i18n import t

WINDOWS_VT = None
COLORS = {"cyan": "36", "green": "32", "red": "31", "dim": "2", "bold": "1"}


def supports_color():
    global WINDOWS_VT
    if not sys.stdout.isatty() or "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    if os.name == "nt":
        if WINDOWS_VT is None:
            try:
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.GetStdHandle.argtypes = [wintypes.DWORD]
                kernel.GetStdHandle.restype = wintypes.HANDLE
                kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
                kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                handle = kernel.GetStdHandle(-11 & 0xFFFFFFFF)
                mode = wintypes.DWORD()
                WINDOWS_VT = bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and kernel.SetConsoleMode(handle, mode.value | 4))
            except (OSError, AttributeError):
                WINDOWS_VT = False
        return WINDOWS_VT
    return True


def style(text, color):
    return f"\033[{COLORS[color]}m{text}\033[0m" if supports_color() else str(text)


def title(text):
    print("\n" + style(text, "cyan"))


def menu(*items):
    for key, text in items:
        print(f"  {style(str(key).ljust(7), 'red' if key == 'd' else 'cyan')} {text}")


def success(text):
    print(style(text, "green"))


def error(exc):
    print(style(t("Ошибка: {error}", error=exc), "red"))


def optional(prompt, *, cancel=False):
    print(prompt)
    menu(("Enter", t("Отмена" if cancel else "Пропустить")))
    return input("> ")


def confirm(prompt, *, delete=False):
    print(prompt)
    menu(("y", t("Удалить" if delete else "Продолжить")), ("Enter", t("Отмена")))
    return input("> ").strip().lower() == "y"
