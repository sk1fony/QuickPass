# QuickPass

[Русский](README.ru.md)

A terminal password generator for Windows, macOS and Linux, with an encrypted history

[Download](https://github.com/sk1fony/QuickPass/releases/tag/v1.0)

## Run

Install [Python 3.10+](https://www.python.org/downloads/), download the project and unpack it

| System | Launch |
|---|---|
| Windows | Open `Start_Windows.bat` |
| macOS | Run `bash Start_macOS.command` |
| Linux | Run `python3 bootstrap.py` |

## Commands

```bash
python bootstrap.py gen --label "email"
python bootstrap.py history
python bootstrap.py show 1 --copy
python bootstrap.py backup "quickpass-backup.bin"
```

Use `python3` on macOS and Linux. Run `python bootstrap.py --help` for the full command list

## Your passwords

History stays on the device where you created it. It does not sync automatically. Use `b` to save an encrypted backup and `r` to restore it on another device. Press `p` to see the vault location

The vault uses AES-256-GCM with a key derived from your master password through scrypt. If you forget the master password, the history cannot be recovered

The clipboard is not cleared automatically

[MIT](LICENSE)
