#!/usr/bin/env python3
"""One local virtual environment per OS; install dependencies only when needed."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

import i18n
from i18n import t


def main():
    if sys.version_info < (3, 10):
        print(t("QuickPass нужен Python 3.10 или новее: https://www.python.org/downloads/"))
        return 1
    root = Path(__file__).resolve().parent
    script = root / "quickpass.py"
    arguments = sys.argv[1:]
    if "gen" in arguments and "--no-save" in arguments:
        return subprocess.call([sys.executable, str(script), *arguments], cwd=root)
    language = i18n.initialize(arguments)
    system = {"win32": "win", "darwin": "mac"}.get(sys.platform, "linux")
    directory = root / f".venv-{system}"
    python = directory / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(directory)
    requirements = root / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = directory / ".requirements-hash"
    ready = stamp.is_file() and stamp.read_text(encoding="ascii") == digest
    if ready:
        result = subprocess.run(
            [str(python), "-c", "import cryptography"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        ready = result.returncode == 0
    if not ready:
        result = subprocess.run([
            str(python), "-m", "pip", "install", "--index-url", "https://pypi.org/simple",
            "--quiet", "--disable-pip-version-check", "-r", str(requirements),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Dependency installation failed")
        stamp.write_text(digest, encoding="ascii")
    environment = dict(os.environ, QUICKPASS_LANG=language)
    return subprocess.call([str(python), str(script), *arguments], cwd=root, env=environment)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n" + t("Закрыто"))
        sys.exit(130)
    except EOFError:
        sys.exit(0)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(t("Не удалось запустить QuickPass: {error}", error=exc), file=sys.stderr)
        sys.exit(1)
