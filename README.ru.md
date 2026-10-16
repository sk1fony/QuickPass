# QuickPass

[English](README.md)

Генератор паролей на Windows, macOS и Linux 

## Запуск

Установи [Python 3.10+](https://www.python.org/downloads/), скачай проект и распакуй

| Система | Запуск |
|---|---|
| Windows | Открой `Start_Windows.bat` |
| macOS | Выполни `bash Start_macOS.command` |
| Linux | Выполни `python3 bootstrap.py` |

## Команды

```bash
python bootstrap.py gen --label "почта"
python bootstrap.py history
python bootstrap.py show 1 --copy
python bootstrap.py backup "quickpass-backup.bin"
```

На macOS и Linux используй `python3`. Полный список команд доступен через `python bootstrap.py --help`

## Сохранённые пароли

История остаётся на устройстве, где ты её создал, и сама не синхронизируется. Команда `b` сохраняет зашифрованную копию, `r` восстанавливает её на другом устройстве. Путь к хранилищу можно посмотреть через `p`

Хранилище зашифровано AES-256-GCM, ключ выводится из мастер-пароля через scrypt. Если забыть мастер-пароль, восстановить историю не получится

Буфер обмена не очищается автоматически

[MIT](LICENSE)
