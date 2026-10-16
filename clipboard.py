"""Explicit clipboard access. Passwords go through stdin, never command arguments."""

import shutil
import subprocess
import sys

from i18n import t


class ClipboardError(Exception):
    pass


def copy(text):
    if sys.platform == "darwin":
        command = ["pbcopy"]
    elif sys.platform == "win32":
        program = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not program:
            raise ClipboardError(t("Не найден PowerShell для доступа к буферу обмена"))
        command = [
            program, "-NoProfile", "-NonInteractive", "-Command",
            "[Console]::InputEncoding = [Text.Encoding]::UTF8; "
            "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
        ]
    elif shutil.which("wl-copy"):
        command = ["wl-copy"]
    elif shutil.which("xclip"):
        command = ["xclip", "-selection", "clipboard"]
    else:
        raise ClipboardError(t("Нет доступа к буферу обмена. Пароль можно скопировать из терминала"))
    try:
        subprocess.run(
            command, input=text.encode("utf-8"), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ClipboardError(t("Не удалось скопировать пароль в буфер обмена")) from exc
