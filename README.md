# ArrTeamEnglish

Telegram bot for filling `english-pronunciation.md`.

## Setup

1. Add the BotFather token to `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:your_real_token
OPENAI_API_KEY=sk-proj-your_real_openai_key
OPENAI_MODEL=gpt-5-mini
```

2. Run the bot:

```powershell
python bot.py
```

## Behavior

Send one English word to the bot.

- If the word already exists in `english-pronunciation.md`, the bot sends all saved values as one message, one value per line, without field names.
- If the word does not exist, the bot asks OpenAI to fill pronunciation, translation, stress, plural, and common phrases, then saves a new `wordN` entry and sends the values.

If `OPENAI_API_KEY` is missing or the OpenAI request fails, the bot falls back to a local placeholder entry with `TODO` fields.
