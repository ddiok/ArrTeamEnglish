# ArrTeamEnglish

Telegram-бот для заполнения файла `english-pronunciation.md`.

## Настройка

1. Добавьте токен BotFather и ключ OpenAI в `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:your_real_token
OPENAI_API_KEY=sk-proj-your_real_openai_key
OPENAI_MODEL=gpt-5-mini
```

2. Запустите бота:

```powershell
python bot.py
```

## Автозапуск Windows

Запустите PowerShell от имени администратора, затем выполните:

```powershell
cd C:\Users\WORK\Documents\Codex\ArrTeamEnglish
.\install_task_scheduler.ps1
```

Задача называется `ArrTeamEnglishBot`. Она запускает бота при входе в Windows и пишет логи в `logs/`.

Чтобы удалить задачу:

```powershell
.\uninstall_task_scheduler.ps1
```

## Поведение

Отправьте боту одно английское слово.

- Если слово уже есть в `english-pronunciation.md`, бот отправит все сохраненные значения одним сообщением: одно значение на строку, без названий полей.
- Если слова еще нет, бот попросит OpenAI заполнить произношение, перевод, ударение, множественное число и частые фразы, затем сохранит новую запись `wordN` и отправит значения.

Если `OPENAI_API_KEY` отсутствует или запрос к OpenAI не сработает, бот создаст локальную заготовку с полями `TODO`.
