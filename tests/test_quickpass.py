from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import secrets
import string
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import clipboard
import bootstrap
import i18n
import quickpass
import terminal
from passwords import SIMILAR, SYMBOLS, generate
import vault
from vault import Vault, VaultError, backup, locked, restore

ROOT = Path(__file__).resolve().parents[1]
MASTER = "test-only master phrase 2026"
OTHER_MASTER = "another test-only master phrase"
TEST_PASSWORD = "test-only password value"


class PasswordTests(unittest.TestCase):
    def test_password_policy_and_optional_groups(self):
        for length in (12, 15, 32, 128):
            for _ in range(20):
                value = generate(length)
                self.assertEqual(len(value), length)
                for group in (string.ascii_lowercase, string.ascii_uppercase, string.digits, SYMBOLS):
                    self.assertTrue(set(value) & set(group))
                simple = generate(length, symbols=False, exclude_similar=True)
                self.assertTrue(set(simple) <= set(string.ascii_letters + string.digits))
                self.assertFalse(set(simple) & SIMILAR)

    def test_invalid_lengths_are_rejected(self):
        for length in (-1, 0, 11, 129):
            with self.assertRaises(ValueError):
                generate(length)

    def test_no_save_runs_without_site_packages_and_leaves_no_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "absent" / "vault.bin"
            result = subprocess.run([
                sys.executable, "-S", str(ROOT / "quickpass.py"), "--vault", str(path),
                "gen", "--no-save", "--length", "24",
            ], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(result.stdout.strip()), 24)
            self.assertFalse(path.parent.exists())


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "vault.bin"
        self.store = Vault.create(self.path, MASTER)

    def test_encrypted_round_trip_and_metadata(self):
        number = self.store.add(TEST_PASSWORD, "почта")
        raw = self.path.read_bytes()
        self.assertNotIn(TEST_PASSWORD.encode(), raw)
        self.assertNotIn("почта".encode(), raw)
        reopened = Vault.open(self.path, MASTER)
        self.assertEqual(reopened.get(number)["password"], TEST_PASSWORD)
        self.assertEqual(reopened.get(number)["label"], "почта")
        reopened.rename(number, "рабочая почта")
        self.assertEqual(Vault.open(self.path, MASTER).get(number)["label"], "рабочая почта")
        if os.name != "nt":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_wrong_password_and_modified_ciphertext_do_not_change_original(self):
        self.store.add(TEST_PASSWORD)
        original = self.path.read_bytes()
        with self.assertRaises(VaultError):
            Vault.open(self.path, OTHER_MASTER)
        modified = Path(self.directory.name) / "modified.bin"
        data = bytearray(original)
        data[-1] ^= 1
        modified.write_bytes(data)
        with self.assertRaises(VaultError):
            Vault.open(modified, MASTER)
        self.assertEqual(self.path.read_bytes(), original)

    def test_original_v1_file_remains_readable_after_editing(self):
        entries = [{"time": "2026-10-15T12:00:00+03:00", "password": TEST_PASSWORD}]
        nonce = secrets.token_bytes(12)
        raw = vault.MAGIC + self.store.salt + nonce + AESGCM(self.store.key).encrypt(
            nonce, json.dumps(entries).encode(), vault.MAGIC,
        )
        self.path.write_bytes(raw)
        migrated = Vault.open(self.path, MASTER)
        self.assertEqual(migrated.get(1).get("label", ""), "")
        migrated.add("second test-only value", "архив")
        reopened = Vault.open(self.path, MASTER)
        self.assertEqual(reopened.get(1)["password"], TEST_PASSWORD)
        self.assertEqual(reopened.get(2)["label"], "архив")
        # The old reader expects a list with time/password fields, not a new envelope.
        offset = len(vault.MAGIC)
        data = self.path.read_bytes()
        old_reader = json.loads(AESGCM(self.store.key).decrypt(
            data[offset + 16:offset + 28], data[offset + 28:], vault.MAGIC,
        ))
        self.assertEqual(old_reader[1]["password"], "second test-only value")

    def test_creation_never_overwrites_a_file(self):
        before = self.path.read_bytes()
        with self.assertRaises(VaultError):
            Vault.create(self.path, OTHER_MASTER)
        self.assertEqual(before, self.path.read_bytes())

    def test_failed_save_is_not_shown_or_added_to_history(self):
        before = self.path.read_bytes()
        output, errors = io.StringIO(), io.StringIO()
        with patch("quickpass.secret", return_value=MASTER), patch(
            "vault.atomic_write", side_effect=OSError("test write failure")
        ), redirect_stdout(output), redirect_stderr(errors):
            code = quickpass.main(["--vault", str(self.path), "gen", "--label", "архив"])
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(Vault.open(self.path, MASTER).entries, [])

    def test_history_does_not_generate_a_password_or_expose_values(self):
        self.store.add(TEST_PASSWORD, "почта")
        before = self.path.read_bytes()
        output = io.StringIO()
        with patch("quickpass.secret", return_value=MASTER), patch(
            "quickpass.generate", side_effect=AssertionError("history must not generate")
        ), redirect_stdout(output):
            code = quickpass.main(["--vault", str(self.path), "history", "--search", "почта"])
        self.assertEqual(code, 0)
        self.assertIn("почта", output.getvalue())
        self.assertNotIn(TEST_PASSWORD, output.getvalue())
        self.assertEqual(self.path.read_bytes(), before)

    def test_backup_is_encrypted_and_will_not_overwrite_existing_files(self):
        self.store.add(TEST_PASSWORD)
        destination = Path(self.directory.name) / "backup.bin"
        backup(self.path, destination)
        self.assertEqual(destination.read_bytes(), self.path.read_bytes())
        with self.assertRaises(FileExistsError):
            backup(self.path, destination)
        self.assertEqual(Vault.open(destination, MASTER).get(1)["password"], TEST_PASSWORD)

    def test_restore_checks_password_and_preserves_previous_vault(self):
        self.store.add(TEST_PASSWORD, "old")
        original = self.path.read_bytes()
        source = Path(self.directory.name) / "source.bin"
        other = Vault.create(source, OTHER_MASTER)
        other.add("restored test-only value", "new")
        with self.assertRaises(VaultError):
            restore(source, self.path, MASTER, replace=True)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.before-restore-*")), [])
        with self.assertRaises(VaultError):
            restore(source, self.path, OTHER_MASTER)
        previous = restore(source, self.path, OTHER_MASTER, replace=True)
        self.assertEqual(previous.read_bytes(), original)
        self.assertEqual(Vault.open(self.path, OTHER_MASTER).get(1)["label"], "new")

    def test_master_rotation_and_failed_rotation(self):
        self.store.add(TEST_PASSWORD)
        old_key, old_data = self.store.key, self.path.read_bytes()
        with patch("vault.atomic_write", side_effect=OSError("test write failure")):
            with self.assertRaises(OSError):
                self.store.change_master(OTHER_MASTER)
        self.assertEqual(self.store.key, old_key)
        self.assertEqual(self.path.read_bytes(), old_data)
        self.store.change_master(OTHER_MASTER)
        with self.assertRaises(VaultError):
            Vault.open(self.path, MASTER)
        self.assertEqual(Vault.open(self.path, OTHER_MASTER).get(1)["password"], TEST_PASSWORD)

    def test_os_lock_is_released_after_process_is_terminated(self):
        script = (
            "import sys,time; from pathlib import Path; from vault import locked; "
            "context = locked(Path(sys.argv[1])); context.__enter__(); "
            "print('locked', flush=True); time.sleep(30)"
        )
        child = subprocess.Popen([
            sys.executable, "-u", "-c", script, str(self.path),
        ], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            with self.assertRaises(VaultError):
                with locked(self.path):
                    self.fail("two processes entered the same vault")
        finally:
            child.terminate()
            child.communicate(timeout=10)
        with locked(self.path):
            self.assertTrue(self.path.exists())

    def test_deleting_an_entry_persists_and_preserves_the_other_passwords(self):
        self.store.add("first test-only value", "first")
        self.store.add("remove this test-only value", "middle")
        self.store.add("last test-only value", "last")
        self.store.delete(2)
        reopened = Vault.open(self.path, MASTER)
        self.assertEqual([e["label"] for e in reopened.entries], ["first", "last"])
        self.assertEqual(reopened.get(2)["password"], "last test-only value")

    def test_cancelled_or_failed_deletion_preserves_the_vault(self):
        self.store.add(TEST_PASSWORD, "keep")
        original = self.path.read_bytes()
        with patch("quickpass.confirm", return_value=False), redirect_stdout(io.StringIO()):
            self.assertFalse(quickpass.delete_entry(self.store, 1))
        with patch("vault.atomic_write", side_effect=OSError("test write failure")):
            with self.assertRaises(OSError):
                self.store.delete(1)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.get(1)["password"], TEST_PASSWORD)
        with self.assertRaises(VaultError):
            self.store.delete(0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_delete_resets_copy_last_in_the_main_menu(self):
        def remove_entry(store):
            store.delete(1)
            return True
        output = io.StringIO()
        with patch("quickpass.unlock", return_value=self.store), patch(
            "quickpass.sys.stdin.isatty", return_value=True
        ), patch("quickpass.sys.stdout.isatty", return_value=True), patch(
            "builtins.input", side_effect=["", "demo", "h", "c", "q"]
        ), patch("quickpass.history_menu", side_effect=remove_entry), patch(
            "quickpass.copy_password"
        ) as copied, redirect_stdout(output):
            # redirect_stdout changes the stream; give the replacement TTY semantics.
            with patch.object(output, "isatty", return_value=True):
                quickpass.interactive(self.path)
        copied.assert_not_called()
        self.assertEqual(self.store.entries, [])


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.preference = Path(self.directory.name) / "settings.json"
        self.environment = patch.dict(os.environ, {
            "QUICKPASS_SETTINGS": str(self.preference), "QUICKPASS_LANG": "", "NO_COLOR": "1",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        previous = i18n.LANGUAGE
        self.addCleanup(i18n.set_language, previous)
        i18n.set_language("en")

    def choose(self, response):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(output, "isatty", return_value=True), patch(
            "i18n.sys.stdin.isatty", return_value=True
        ), patch("builtins.input", return_value=response):
            result = i18n.configure(interactive=True)
        return result, output.getvalue()

    def test_enter_selects_english_once_and_saves_the_preference(self):
        selected, output = self.choose("")
        self.assertEqual(selected, "en")
        self.assertIn("English", output)
        self.assertEqual(json.loads(self.preference.read_text()), {"language": "en"})
        with patch("builtins.input", side_effect=AssertionError("must not ask twice")):
            self.assertEqual(i18n.configure(interactive=True), "en")

    def test_russian_choice_translates_menus_and_storage_errors(self):
        self.assertEqual(self.choose("2")[0], "ru")
        output = io.StringIO()
        with redirect_stdout(output):
            quickpass.main_menu(type("Store", (), {"entries": []})(), quickpass.Options())
        self.assertIn("Создать пароль", output.getvalue())
        self.assertNotIn("Create password", output.getvalue())
        with self.assertRaisesRegex(VaultError, "Записи с таким номером нет"):
            Vault(self.preference, [], b"", b"").get(1)

    def test_redirected_output_has_no_ansi_codes_and_actions_use_separate_lines(self):
        output = io.StringIO()
        with redirect_stdout(output):
            terminal.menu(("Enter", "Create password"), ("h", "History"))
        self.assertNotIn("\033[", output.getvalue())
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("Create password", lines[0])
        self.assertIn("History", lines[1])

    def test_bootstrap_keeps_successful_dependency_installation_quiet(self):
        root = Path(self.directory.name)
        (root / "requirements.txt").write_text("cryptography>=50.0.2,<51\n")
        def create_env(directory):
            python = directory / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            python.parent.mkdir(parents=True)
            python.touch()
        output, errors = io.StringIO(), io.StringIO()
        with patch("bootstrap.__file__", str(root / "bootstrap.py")), patch(
            "bootstrap.sys.argv", ["bootstrap.py", "--lang", "en"]
        ), patch("bootstrap.venv.EnvBuilder") as builder, patch(
            "bootstrap.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "installer output", "")
        ) as install, patch("bootstrap.subprocess.call", return_value=0) as child, redirect_stdout(output), redirect_stderr(errors):
            builder.return_value.create.side_effect = create_env
            self.assertEqual(bootstrap.main(), 0)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "")
        self.assertTrue(install.call_args.kwargs["capture_output"])
        self.assertEqual(child.call_args.kwargs["env"]["QUICKPASS_LANG"], "en")


class ClipboardTests(unittest.TestCase):
    def test_password_is_passed_through_stdin_not_argv(self):
        with patch("clipboard.sys.platform", "darwin"), patch("clipboard.subprocess.run") as run:
            clipboard.copy(TEST_PASSWORD)
        self.assertEqual(run.call_args.args[0], ["pbcopy"])
        self.assertEqual(run.call_args.kwargs["input"], TEST_PASSWORD.encode())

    def test_copy_failure_has_a_readable_error(self):
        with patch("clipboard.sys.platform", "darwin"), patch(
            "clipboard.subprocess.run", side_effect=FileNotFoundError,
        ):
            with self.assertRaises(clipboard.ClipboardError):
                clipboard.copy(TEST_PASSWORD)


if __name__ == "__main__":
    unittest.main()
