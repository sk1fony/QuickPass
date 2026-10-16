"""English and Russian interface strings; the preference contains no vault data."""

import argparse
import json
import os
from pathlib import Path
import sys

LANGUAGE = "en"

EN = {
    "Подпись должна быть не длиннее 120 символов": "Labels must be 120 characters or shorter",
    "Для ввода мастер-пароля открой обычный терминал": "Open a terminal to enter your master password",
    "Новый мастер-пароль: ": "New master password: ",
    "Для мастер-пароля нужно минимум 16 символов": "Your master password needs at least 16 characters",
    "Повтори мастер-пароль: ": "Confirm master password: ",
    "Пароли не совпадают": "Passwords do not match",
    "Мастер-пароль: ": "Master password: ",
    "Хранилище не найдено: {path}": "Vault not found: {path}",
    "Придумай мастер-пароль от 16 символов": "Create a master password with at least 16 characters",
    "Хранилище создано": "Vault created",
    "История хранится локально. Команда b создаёт зашифрованную копию": "History is stored locally. Use b to make an encrypted backup",
    "Записей пока нет": "No entries yet",
    "Ничего не найдено": "No matches",
    "Дата": "Date",
    "Подпись": "Label",
    "без подписи": "no label",
    "Без подписи": "No label",
    "Показано {shown} из {total}": "Showing {shown} of {total}",
    "Скопировано. Буфер обмена не очищается автоматически": "Copied. The clipboard is not cleared automatically",
    "Номер": "Number",
    "Открыть запись": "Open entry",
    "/текст": "/text",
    "Поиск": "Search",
    "Показать все": "Show all",
    "Назад": "Back",
    "Скопировать": "Copy",
    "Изменить подпись": "Rename",
    "Удалить пароль": "Delete password",
    "Пароль: {password}": "Password: {password}",
    "Подпись: ": "Label: ",
    "Подпись изменена": "Label updated",
    "Удалить эту запись?": "Delete this entry?",
    "Удалить": "Delete",
    "Отмена": "Cancel",
    "Пароль удалён из истории": "Password deleted from history",
    "Удаление отменено": "Deletion cancelled",
    "Ошибка: {error}": "Error: {error}",
    "Введи номер записи или /текст для поиска": "Enter an entry number or /text to search",
    "Включено": "Enabled",
    "Выключено": "Disabled",
    "Включить": "Enable",
    "Выключить": "Disable",
    "Оставить как есть": "Keep current value",
    "Длина: {length}": "Length: {length}",
    "Длина должна быть от {minimum} до {maximum}": "Length must be between {minimum} and {maximum}",
    "Спецсимволы": "Symbols",
    "Исключить похожие Il1O0o": "Exclude similar characters Il1O0o",
    "Настройки действуют до закрытия программы": "These settings apply until you close QuickPass",
    "Открой QuickPass в терминале. Для генерации без меню есть команда gen": "Open QuickPass in a terminal. Use gen to generate a password without the menu",
    "Записей: {count}": "Entries: {count}",
    "Создать пароль": "Create password",
    "История": "History",
    "Копировать последний": "Copy last password",
    "Настройки": "Settings",
    "Резервная копия": "Back up vault",
    "Восстановить историю": "Restore vault",
    "Изменить мастер-пароль": "Change master password",
    "Путь к хранилищу": "Vault location",
    "Язык": "Language",
    "Выход": "Quit",
    "Подпись, например почта или архив": "Label, for example email or archive",
    "Пропустить": "Skip",
    "Сохранён в истории под номером {number}": "Saved to history as entry {number}",
    "В этом сеансе ещё нет нового пароля. Старые записи доступны через h": "No password created in this session. Open h to find saved entries",
    "Куда сохранить копию, включая имя файла": "Backup destination, including the file name",
    "Копия сохранена: {path}": "Backup saved: {path}",
    "Для открытия нужен текущий мастер-пароль": "Use your current master password to open this backup",
    "Путь к резервной копии": "Backup file path",
    "Копия заменит текущую историю. Сначала будет сохранена старая версия": "This will replace your current history. A copy of the current vault will be saved first",
    "Продолжить": "Continue",
    "Мастер-пароль резервной копии: ": "Backup master password: ",
    "История восстановлена": "Vault restored",
    "Предыдущая версия: {path}": "Previous version: {path}",
    "Мастер-пароль изменён. Старые резервные копии используют прежний пароль": "Master password changed. Existing backups still use the previous password",
    "Выбери команду из меню": "Choose a command from the menu",
    "Длина должна быть целым числом": "Length must be a whole number",
    "Генератор паролей с зашифрованной историей": "Password generator with encrypted history",
    "путь к хранилищу вместо стандартного": "use this vault file instead of the default location",
    "язык интерфейса": "interface language",
    "показать справку": "show this help message and exit",
    "сгенерировать пароль": "generate a password",
    "подпись в истории": "entry label",
    "только буквы и цифры": "use letters and digits only",
    "исключить Il1O0o": "exclude Il1O0o",
    "вывести без сохранения и без мастер-пароля": "print without saving or asking for a master password",
    "также скопировать в буфер обмена": "also copy to the clipboard",
    "список записей без показа паролей": "list entries without revealing passwords",
    "показать все записи": "show all entries",
    "показать сохранённый пароль по номеру": "show a saved password by entry number",
    "изменить подпись записи": "change an entry label",
    "удалить запись из истории": "delete a saved entry",
    "удалить без повторного подтверждения": "delete without asking for confirmation",
    "показать путь к хранилищу": "show the vault location",
    "сменить мастер-пароль": "change the master password",
    "сохранить зашифрованную копию": "save an encrypted backup",
    "восстановить зашифрованную копию": "restore an encrypted backup",
    "заменить существующую историю, сохранив её копию": "replace the current vault after saving a copy",
    "--label требует сохранения. Убери --no-save или --label": "--label requires saving. Remove --no-save or --label",
    "Она зашифрована тем же мастер-паролем. Содержимое не проверялось расшифровкой": "The backup uses the same master password. Its contents have not been verified by decryption",
    "Хранилище уже существует. Для замены нужен --replace": "A vault already exists. Use --replace to replace it",
    "История восстановлена: {path}": "Vault restored: {path}",
    "Закрыто": "Closed",
    "Не установлена cryptography. Запусти файл Start для своей ОС или выполни python -m pip install -r requirements.txt": "cryptography is not installed. Run the Start file for your OS or run python -m pip install -r requirements.txt",
    "Хранилище больше 64 МБ. Файл не изменён": "The vault exceeds 64 MB. The file has not been changed",
    "Повреждена структура хранилища": "Invalid vault structure",
    "Повреждена запись в хранилище": "Invalid vault entry",
    "Повреждена подпись записи": "Invalid entry label",
    "Это не хранилище QuickPass или файл повреждён": "This is not a QuickPass vault, or the file is damaged",
    "Неверный мастер-пароль или повреждён файл. Хранилище не изменено": "Wrong master password or damaged file. The vault has not been changed",
    "Повреждено содержимое хранилища": "Invalid vault contents",
    "Это хранилище уже открыто в другом окне QuickPass": "This vault is already open in another QuickPass window",
    "Хранилище уже существует. Оно не изменено": "The vault already exists. It has not been changed",
    "Хранилище достигло ограничения в 64 МБ": "The vault has reached its 64 MB limit",
    "Записи с таким номером нет": "No entry with this number",
    "Для копии выбери другой файл": "Choose a different file for the backup",
    "Это уже выбранное хранилище": "This file is already the selected vault",
    "Не найден PowerShell для доступа к буферу обмена": "PowerShell could not be found for clipboard access",
    "Нет доступа к буферу обмена. Пароль можно скопировать из терминала": "Clipboard access is unavailable. Copy the password from the terminal",
    "Не удалось скопировать пароль в буфер обмена": "Could not copy the password to the clipboard",
    "QuickPass нужен Python 3.10 или новее: https://www.python.org/downloads/": "QuickPass requires Python 3.10 or newer: https://www.python.org/downloads/",
    "Не удалось запустить QuickPass: {error}": "Could not start QuickPass: {error}",
    "Не удалось сохранить язык: {error}": "Could not save the language preference: {error}",
    "Выбери 1 или 2": "Choose 1 or 2",
}


def t(message, **values):
    template = EN.get(message, message) if LANGUAGE == "en" else message
    return template.format(**values) if values else template


def set_language(language):
    global LANGUAGE
    if language not in ("en", "ru"):
        raise ValueError("Language must be en or ru")
    LANGUAGE = language


def settings_path():
    from vault import default_path
    custom = os.environ.get("QUICKPASS_SETTINGS")
    return Path(custom).expanduser().resolve() if custom else default_path().parent / "settings.json"


def saved_language():
    try:
        with settings_path().open(encoding="utf-8") as source:
            settings = json.loads(source.read(4096))
        value = settings.get("language")
        return value if value in ("en", "ru") else None
    except (OSError, ValueError, AttributeError):
        return None


def save_language(language):
    from vault import atomic_write
    atomic_write(settings_path(), json.dumps({"language": language}).encode("utf-8"))


def choose_language():
    from terminal import menu, title
    title("Language / Язык")
    menu(("1", "English"), ("2", "Русский"), ("Enter", "English"))
    while True:
        choice = input("> ").strip().lower()
        if choice in ("", "1", "en", "english"):
            value = "en"
            break
        if choice in ("2", "ru", "русский"):
            value = "ru"
            break
        print(t("Выбери 1 или 2"))
    set_language(value)
    save_language(value)
    return value


def configure(language=None, *, interactive=False):
    selected = language or os.environ.get("QUICKPASS_LANG")
    if selected not in ("en", "ru"):
        selected = saved_language()
    set_language(selected or "en")
    if selected is None and interactive and sys.stdin.isatty() and sys.stdout.isatty():
        choose_language()
    return LANGUAGE


def initialize(argv):
    flags = argparse.ArgumentParser(add_help=False)
    flags.add_argument("--lang", choices=("en", "ru"))
    flags.add_argument("--vault")
    known, remaining = flags.parse_known_args(argv)
    quiet = any(value in remaining for value in ("--no-save", "--help", "-h", "--version"))
    quiet = quiet or bool(remaining and remaining[0] in ("path", "backup"))
    return configure(known.lang, interactive=not quiet)
