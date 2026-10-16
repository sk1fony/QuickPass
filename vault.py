"""The original QuickPass-v1 format, with atomic writes and OS file locks."""

from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import sys

from i18n import t
import tempfile

MAGIC = b"QuickPass-v1\0"
MAX_VAULT_SIZE = 64 * 1024 * 1024


class VaultError(Exception):
    pass


def crypto():
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError as exc:
        raise VaultError(
            t("Не установлена cryptography. Запусти файл Start для своей ОС "
            "или выполни python -m pip install -r requirements.txt")
        ) from exc
    return InvalidTag, AESGCM, Scrypt


def default_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path.home() / ".local/share"
    return base / ".QuickPass" / "vault.bin"


def resolve_path(value=None):
    value = value or os.environ.get("QUICKPASS_VAULT")
    return Path(value).expanduser().resolve() if value else default_path().resolve()


def derive(master, salt):
    _, _, Scrypt = crypto()
    return Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(master.encode("utf-8"))


def read_bytes(path):
    with Path(path).open("rb") as source:
        data = source.read(MAX_VAULT_SIZE + 1)
    if len(data) > MAX_VAULT_SIZE:
        raise VaultError(t("Хранилище больше 64 МБ. Файл не изменён"))
    return data


def validate_entries(entries):
    if not isinstance(entries, list):
        raise VaultError(t("Повреждена структура хранилища"))
    for entry in entries:
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(field), str) for field in ("time", "password")
        ):
            raise VaultError(t("Повреждена запись в хранилище"))
        if not isinstance(entry.get("label", ""), str):
            raise VaultError(t("Повреждена подпись записи"))
    return entries


def decode(data, master):
    InvalidTag, AESGCM, _ = crypto()
    if not data.startswith(MAGIC) or len(data) < len(MAGIC) + 44:
        raise VaultError(t("Это не хранилище QuickPass или файл повреждён"))
    offset = len(MAGIC)
    salt, nonce = data[offset:offset + 16], data[offset + 16:offset + 28]
    key = derive(master, salt)
    try:
        payload = AESGCM(key).decrypt(nonce, data[offset + 28:], MAGIC)
    except InvalidTag as exc:
        raise VaultError(t("Неверный мастер-пароль или повреждён файл. Хранилище не изменено")) from exc
    try:
        entries = validate_entries(json.loads(payload.decode("utf-8")))
    except (ValueError, UnicodeDecodeError) as exc:
        raise VaultError(t("Повреждено содержимое хранилища")) from exc
    return entries, salt, key


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".qp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def exclusive_write(path, data):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


@contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = path.with_name(path.name + ".lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    handle = os.fdopen(fd, "r+b")
    acquired = False
    try:
        if os.fstat(fd).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise VaultError(t("Это хранилище уже открыто в другом окне QuickPass")) from exc
        acquired = True
        yield
    finally:
        try:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            handle.close()
        # Keep the lock's inode: unlinking it can let two processes lock different files.


class Vault:
    def __init__(self, path, entries, salt, key):
        self.path = Path(path)
        self.entries = entries
        self.salt = salt
        self.key = key

    @classmethod
    def open(cls, path, master):
        return cls(path, *decode(read_bytes(path), master))

    @classmethod
    def create(cls, path, master):
        if len(master) < 16:
            raise VaultError(t("Для мастер-пароля нужно минимум 16 символов"))
        path = Path(path)
        if path.exists():
            raise VaultError(t("Хранилище уже существует. Оно не изменено"))
        salt = secrets.token_bytes(16)
        vault = cls(path, [], salt, derive(master, salt))
        # Creation must never replace an existing vault.
        exclusive_write(path, vault.encode([]))
        return vault

    def encode(self, entries, *, salt=None, key=None):
        _, AESGCM, _ = crypto()
        salt = self.salt if salt is None else salt
        key = self.key if key is None else key
        payload = json.dumps(entries, ensure_ascii=False).encode("utf-8")
        nonce = secrets.token_bytes(12)
        data = MAGIC + salt + nonce + AESGCM(key).encrypt(nonce, payload, MAGIC)
        if len(data) > MAX_VAULT_SIZE:
            raise VaultError(t("Хранилище достигло ограничения в 64 МБ"))
        return data

    def commit(self, entries):
        atomic_write(self.path, self.encode(entries))
        self.entries = entries

    def add(self, password, label=""):
        entry = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "password": password,
            "label": label,
        }
        self.commit([*self.entries, entry])
        return len(self.entries)

    def get(self, number):
        if not 1 <= number <= len(self.entries):
            raise VaultError(t("Записи с таким номером нет"))
        return self.entries[number - 1]

    def rename(self, number, label):
        self.get(number)
        entries = [dict(entry) for entry in self.entries]
        entries[number - 1]["label"] = label
        self.commit(entries)

    def delete(self, number):
        self.get(number)
        self.commit(self.entries[:number - 1] + self.entries[number:])

    def change_master(self, master):
        if len(master) < 16:
            raise VaultError(t("Для мастер-пароля нужно минимум 16 символов"))
        salt = secrets.token_bytes(16)
        key = derive(master, salt)
        atomic_write(self.path, self.encode(self.entries, salt=salt, key=key))
        self.salt, self.key = salt, key


def backup(path, destination):
    path, destination = Path(path).resolve(), Path(destination).expanduser().resolve()
    if destination in (path, path.with_name(path.name + ".lock")):
        raise VaultError(t("Для копии выбери другой файл"))
    data = read_bytes(path)
    if not data.startswith(MAGIC) or len(data) < len(MAGIC) + 44:
        raise VaultError(t("Это не хранилище QuickPass или файл повреждён"))
    return exclusive_write(destination, data)


def restore(source, destination, master, *, replace=False):
    source, destination = Path(source).expanduser().resolve(), Path(destination).resolve()
    if source == destination:
        raise VaultError(t("Это уже выбранное хранилище"))
    data = read_bytes(source)
    decode(data, master)
    previous = None
    if destination.exists():
        if not replace:
            raise VaultError(t("Хранилище уже существует. Для замены нужен --replace"))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        previous = destination.with_name(f"{destination.name}.before-restore-{stamp}.bin")
        exclusive_write(previous, read_bytes(destination))
    atomic_write(destination, data)
    return previous
