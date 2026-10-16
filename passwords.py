"""Password generation without third-party dependencies."""

import secrets
import string

from i18n import t

DEFAULT_LENGTH = 15
MIN_LENGTH = 12
MAX_LENGTH = 128
SYMBOLS = "!@#$%&*+-_=?"
SIMILAR = frozenset("Il1O0o")


def generate(length=DEFAULT_LENGTH, *, symbols=True, exclude_similar=False):
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise ValueError(t("Длина должна быть от {minimum} до {maximum}", minimum=MIN_LENGTH, maximum=MAX_LENGTH))
    groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    if symbols:
        groups.append(SYMBOLS)
    if exclude_similar:
        groups = ["".join(c for c in group if c not in SIMILAR) for group in groups]
    alphabet = "".join(groups)
    # Rejection sampling keeps all passwords meeting the policy equally likely.
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(c in group for c in password) for group in groups):
            return password
