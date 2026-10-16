#!/usr/bin/env python3
"""QuickPass terminal interface and command-line commands."""

import argparse
from dataclasses import dataclass
import getpass
from pathlib import Path
import sys
import unicodedata

from clipboard import ClipboardError, copy
import i18n
from i18n import t
from passwords import DEFAULT_LENGTH, MAX_LENGTH, MIN_LENGTH, generate
from terminal import confirm, error, menu, optional, style, success, title
from vault import Vault, VaultError, backup, locked, resolve_path, restore

VERSION = "1.0"


@dataclass
class Options:
    length: int = DEFAULT_LENGTH
    symbols: bool = True
    exclude_similar: bool = False


def clean(text):
    return "".join(c for c in text if not unicodedata.category(c).startswith("C"))


def label(text):
    text = clean(text).strip()
    if len(text) > 120:
        raise VaultError(t("Подпись должна быть не длиннее 120 символов"))
    return text


def secret(prompt):
    if not sys.stdin.isatty():
        raise VaultError(t("Для ввода мастер-пароля открой обычный терминал"))
    return getpass.getpass(prompt)


def new_master():
    value = secret(t("Новый мастер-пароль: "))
    if len(value) < 16:
        raise VaultError(t("Для мастер-пароля нужно минимум 16 символов"))
    if value != secret(t("Повтори мастер-пароль: ")):
        raise VaultError(t("Пароли не совпадают"))
    return value


def unlock(path, *, create=False):
    if path.exists():
        return Vault.open(path, secret(t("Мастер-пароль: ")))
    if not create:
        raise VaultError(t("Хранилище не найдено: {path}", path=path))
    print(t("Придумай мастер-пароль от 16 символов"))
    store = Vault.create(path, new_master())
    success(t("Хранилище создано"))
    print(style(t("История хранится локально. Команда b создаёт зашифрованную копию"), "dim"))
    return store


def make_password(store, options, title=""):
    password = generate(
        options.length, symbols=options.symbols, exclude_similar=options.exclude_similar,
    )
    # Display only after the encrypted write has succeeded.
    number = store.add(password, label(title))
    return password, number


def print_history(store, query="", limit=20):
    query = query.casefold()
    items = [
        (number, entry) for number, entry in enumerate(store.entries, 1)
        if query in entry.get("label", "").casefold() or query in entry["time"].casefold()
    ]
    visible = items if limit is None else items[-limit:]
    if not visible:
        print(t("Записей пока нет" if not query else "Ничего не найдено"))
        return
    print(style(f"\n{'#':>5}  {t('Дата'):<25}  {t('Подпись')}", "cyan"))
    for number, entry in reversed(visible):
        timestamp = clean(entry["time"]).replace("T", " ")[:25]
        entry_label = clean(entry.get("label", "")) or t("без подписи")
        if len(entry_label) > 56:
            entry_label = entry_label[:53] + "..."
        print(f"{number:>5}  {timestamp:<25}  {entry_label}")
    print(style(t("Показано {shown} из {total}", shown=len(visible), total=len(items)), "dim"))


def copy_password(password):
    copy(password)
    success(t("Скопировано. Буфер обмена не очищается автоматически"))


def delete_entry(store, number, *, yes=False):
    entry = store.get(number)
    if not yes:
        print(clean(entry.get("label", "")) or t("Без подписи"))
        if not confirm(t("Удалить эту запись?"), delete=True):
            print(t("Удаление отменено"))
            return False
    store.delete(number)
    success(t("Пароль удалён из истории"))
    return True


def history_menu(store):
    query, limit, deleted = "", 20, False
    while True:
        print_history(store, query, limit)
        print()
        menu(
            (t("Номер"), t("Открыть запись")),
            (t("/текст"), t("Поиск")),
            ("a", t("Показать все")),
            ("Enter", t("Назад")),
        )
        command = input("> ").strip()
        if not command:
            return deleted
        if command == "a":
            limit = None
        elif command.startswith("/"):
            query = command[1:].strip()
        elif command.isdigit():
            try:
                number = int(command)
                entry = store.get(number)
                title(clean(entry.get("label", "")) or t("Без подписи"))
                print(t("Пароль: {password}", password=clean(entry["password"])))
                menu(
                    ("c", t("Скопировать")),
                    ("r", t("Изменить подпись")),
                    ("d", t("Удалить пароль")),
                    ("Enter", t("Назад")),
                )
                action = input("> ").strip().lower()
                if action == "c":
                    copy_password(entry["password"])
                elif action == "r":
                    store.rename(number, label(input(t("Подпись: "))))
                    success(t("Подпись изменена"))
                elif action == "d":
                    deleted = delete_entry(store, number) or deleted
            except (VaultError, ClipboardError, OSError) as exc:
                error(exc)
        else:
            print(t("Введи номер записи или /текст для поиска"))


def toggle(prompt, current):
    print(f"\n{prompt}: {t('Включено' if current else 'Выключено')}")
    menu(("y", t("Включить")), ("n", t("Выключить")), ("Enter", t("Оставить как есть")))
    while True:
        value = input("> ").strip().lower()
        if value in ("y", "n", ""):
            return current if not value else value == "y"


def settings(options):
    print(t("Длина: {length}", length=options.length))
    menu(("Enter", t("Оставить как есть")))
    value = input("> ").strip()
    if value:
        if not value.isdigit() or not MIN_LENGTH <= int(value) <= MAX_LENGTH:
            raise VaultError(t("Длина должна быть от {minimum} до {maximum}", minimum=MIN_LENGTH, maximum=MAX_LENGTH))
        options.length = int(value)
    options.symbols = toggle(t("Спецсимволы"), options.symbols)
    options.exclude_similar = toggle(t("Исключить похожие Il1O0o"), options.exclude_similar)
    success(t("Настройки действуют до закрытия программы"))


def input_path(prompt):
    value = optional(prompt, cancel=True).strip().strip('"').strip("'")
    return Path(value).expanduser().resolve() if value else None


def main_menu(store, options):
    print()
    print(style(t("Записей: {count}", count=len(store.entries)), "dim"))
    print(style(t("Длина: {length}", length=options.length), "dim"))
    menu(
        ("Enter", t("Создать пароль")),
        ("h", t("История")),
        ("c", t("Копировать последний")),
        ("s", t("Настройки")),
        ("b", t("Резервная копия")),
        ("r", t("Восстановить историю")),
        ("m", t("Изменить мастер-пароль")),
        ("p", t("Путь к хранилищу")),
        ("l", t("Язык")),
        ("q", t("Выход")),
    )


def interactive(path):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise VaultError(t("Открой QuickPass в терминале. Для генерации без меню есть команда gen"))
    title(f"QuickPass {VERSION}")
    store = unlock(path, create=True)
    options = Options()
    last = None
    while True:
        main_menu(store, options)
        command = input("> ").strip().lower()
        try:
            if command in ("q", "quit", "exit"):
                return
            if command in ("", "n"):
                entry_label = optional(t("Подпись, например почта или архив"))
                password, number = make_password(store, options, entry_label)
                last = number
                print("\n" + style(t("Пароль: {password}", password=password), "green"))
                success(t("Сохранён в истории под номером {number}", number=number))
            elif command == "h":
                if history_menu(store):
                    # Deletion renumbers entries, so a cached number must not be reused.
                    last = None
            elif command == "c":
                if last is None:
                    print(t("В этом сеансе ещё нет нового пароля. Старые записи доступны через h"))
                else:
                    copy_password(store.get(last)["password"])
            elif command == "s":
                settings(options)
            elif command == "l":
                i18n.choose_language()
            elif command == "p":
                print(path)
                print(t("История хранится локально. Команда b создаёт зашифрованную копию"))
            elif command == "b":
                destination = input_path(t("Куда сохранить копию, включая имя файла"))
                if destination is not None:
                    success(t("Копия сохранена: {path}", path=backup(path, destination)))
                    print(t("Для открытия нужен текущий мастер-пароль"))
            elif command == "r":
                source = input_path(t("Путь к резервной копии"))
                if source is not None:
                    if confirm(t("Копия заменит текущую историю. Сначала будет сохранена старая версия")):
                        master = secret(t("Мастер-пароль резервной копии: "))
                        previous = restore(source, path, master, replace=True)
                        store = Vault.open(path, master)
                        del master
                        last = None
                        success(t("История восстановлена"))
                        if previous:
                            print(t("Предыдущая версия: {path}", path=previous))
            elif command == "m":
                store.change_master(new_master())
                success(t("Мастер-пароль изменён. Старые резервные копии используют прежний пароль"))
            else:
                print(t("Выбери команду из меню"))
        except (VaultError, ClipboardError, OSError) as exc:
            error(exc)


def length_value(value):
    try:
        length = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(t("Длина должна быть целым числом")) from exc
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise argparse.ArgumentTypeError(t("Длина должна быть от {minimum} до {maximum}", minimum=MIN_LENGTH, maximum=MAX_LENGTH))
    return length


def parser():
    root = argparse.ArgumentParser(description=t("Генератор паролей с зашифрованной историей"), add_help=False)
    root.add_argument("-h", "--help", action="help", help=t("показать справку"))
    root.add_argument("--version", action="version", version=f"QuickPass {VERSION}")
    root.add_argument("--lang", choices=("en", "ru"), help=t("язык интерфейса"))
    root.add_argument("--vault", metavar="FILE", help=t("путь к хранилищу вместо стандартного"))
    commands = root.add_subparsers(dest="command", metavar="COMMAND")
    gen = commands.add_parser("gen", help=t("сгенерировать пароль"))
    gen.add_argument("-l", "--length", type=length_value, default=DEFAULT_LENGTH, metavar="N")
    gen.add_argument("--label", default="", metavar="TEXT", help=t("подпись в истории"))
    gen.add_argument("--no-symbols", action="store_true", help=t("только буквы и цифры"))
    gen.add_argument("--exclude-similar", action="store_true", help=t("исключить Il1O0o"))
    gen.add_argument("--no-save", action="store_true", help=t("вывести без сохранения и без мастер-пароля"))
    gen.add_argument("--copy", action="store_true", help=t("также скопировать в буфер обмена"))
    history = commands.add_parser("history", help=t("список записей без показа паролей"))
    history.add_argument("--search", default="", metavar="TEXT")
    history.add_argument("--all", action="store_true", help=t("показать все записи"))
    show = commands.add_parser("show", help=t("показать сохранённый пароль по номеру"))
    show.add_argument("number", type=int)
    show.add_argument("--copy", action="store_true")
    rename = commands.add_parser("rename", help=t("изменить подпись записи"))
    rename.add_argument("number", type=int)
    rename.add_argument("label")
    delete = commands.add_parser("delete", help=t("удалить запись из истории"))
    delete.add_argument("number", type=int)
    delete.add_argument("--yes", action="store_true", help=t("удалить без повторного подтверждения"))
    commands.add_parser("path", help=t("показать путь к хранилищу"))
    commands.add_parser("master", help=t("сменить мастер-пароль"))
    copy_cmd = commands.add_parser("backup", help=t("сохранить зашифрованную копию"))
    copy_cmd.add_argument("destination", metavar="FILE")
    restore_cmd = commands.add_parser("restore", help=t("восстановить зашифрованную копию"))
    restore_cmd.add_argument("source", metavar="FILE")
    restore_cmd.add_argument("--replace", action="store_true", help=t("заменить существующую историю, сохранив её копию"))
    return root


def run(args):
    path = resolve_path(args.vault)
    if args.command == "path":
        print(path)
        return
    if args.command == "gen" and args.no_save:
        if args.label:
            raise VaultError(t("--label требует сохранения. Убери --no-save или --label"))
        password = generate(args.length, symbols=not args.no_symbols, exclude_similar=args.exclude_similar)
        print(password)
        if args.copy:
            copy_password(password)
        return
    with locked(path):
        if args.command is None:
            interactive(path)
        elif args.command == "backup":
            success(t("Копия сохранена: {path}", path=backup(path, args.destination)))
            print(t("Она зашифрована тем же мастер-паролем. Содержимое не проверялось расшифровкой"))
        elif args.command == "restore":
            if path.exists() and not args.replace:
                raise VaultError(t("Хранилище уже существует. Для замены нужен --replace"))
            master = secret(t("Мастер-пароль резервной копии: "))
            previous = restore(args.source, path, master, replace=args.replace)
            del master
            success(t("История восстановлена: {path}", path=path))
            if previous:
                print(t("Предыдущая версия: {path}", path=previous))
        else:
            store = unlock(path, create=args.command == "gen")
            if args.command == "gen":
                options = Options(args.length, not args.no_symbols, args.exclude_similar)
                password, number = make_password(store, options, args.label)
                print(password)
                print(t("Сохранён в истории под номером {number}", number=number), file=sys.stderr)
                if args.copy:
                    copy_password(password)
            elif args.command == "history":
                print_history(store, args.search, None if args.all else 20)
            elif args.command == "show":
                password = store.get(args.number)["password"]
                print(clean(password))
                if args.copy:
                    copy_password(password)
            elif args.command == "rename":
                store.rename(args.number, label(args.label))
                success(t("Подпись изменена"))
            elif args.command == "delete":
                delete_entry(store, args.number, yes=args.yes)
            elif args.command == "master":
                store.change_master(new_master())
                success(t("Мастер-пароль изменён. Старые резервные копии используют прежний пароль"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        i18n.initialize(argv)
        args = parser().parse_args(argv)
        run(args)
        return 0
    except (VaultError, ClipboardError, OSError, ValueError) as exc:
        print(style(t("Ошибка: {error}", error=exc), "red") if sys.stderr.isatty() else t("Ошибка: {error}", error=exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n" + t("Закрыто"), file=sys.stderr)
        return 130
    except EOFError:
        print("\n" + t("Закрыто"), file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
