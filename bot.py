from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
DEFAULT_PRONUNCIATION_FILE = BASE_DIR / "english-pronunciation.md"
DEFAULT_TEMPLATE_FILE = BASE_DIR / "message-templates.md"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "marin"
DEFAULT_AUDIO_CACHE_DIR = BASE_DIR / "audio-cache"

FIELDS = [
    "word",
    "many",
    "pron_uk",
    "pron_us",
    "stress",
    "pron_uk_many",
    "pron_us_many",
    "stress_many",
    "ru",
    "ru_other",
    "used_phrase",
]

WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'-]*$")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class Entry:
    key: str
    values: dict[str, str]


@dataclass
class Config:
    telegram_token: str
    pronunciation_file: Path
    template_file: Path
    audio_cache_dir: Path
    openai_api_key: str
    openai_model: str
    tts_model: str
    tts_voice: str


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def get_config() -> Config:
    env = {**load_env(ENV_FILE), **os.environ}
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN пустой. Добавьте токен BotFather в .env.")

    file_name = env.get("PRONUNCIATION_FILE", str(DEFAULT_PRONUNCIATION_FILE)).strip()
    pronunciation_file = Path(file_name)
    if not pronunciation_file.is_absolute():
        pronunciation_file = BASE_DIR / pronunciation_file

    template_file_name = env.get("MESSAGE_TEMPLATE_FILE", str(DEFAULT_TEMPLATE_FILE)).strip()
    template_file = Path(template_file_name)
    if not template_file.is_absolute():
        template_file = BASE_DIR / template_file

    audio_cache_name = env.get("AUDIO_CACHE_DIR", str(DEFAULT_AUDIO_CACHE_DIR)).strip()
    audio_cache_dir = Path(audio_cache_name)
    if not audio_cache_dir.is_absolute():
        audio_cache_dir = BASE_DIR / audio_cache_dir

    return Config(
        telegram_token=token,
        pronunciation_file=pronunciation_file,
        template_file=template_file,
        audio_cache_dir=audio_cache_dir,
        openai_api_key=env.get("OPENAI_API_KEY", "").strip(),
        openai_model=env.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL,
        tts_model=env.get("OPENAI_TTS_MODEL", DEFAULT_TTS_MODEL).strip() or DEFAULT_TTS_MODEL,
        tts_voice=env.get("OPENAI_TTS_VOICE", DEFAULT_TTS_VOICE).strip() or DEFAULT_TTS_VOICE,
    )


def extract_yaml_block(markdown: str) -> str:
    match = re.search(r"```yaml\s*(.*?)\s*```", markdown, flags=re.DOTALL)
    return match.group(1) if match else ""


def parse_entries(markdown: str) -> list[Entry]:
    block = extract_yaml_block(markdown)
    entries: list[Entry] = []
    current: Entry | None = None

    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        key_match = re.match(r"^(word\d+):\s*$", line)
        if key_match:
            current = Entry(key=key_match.group(1), values={})
            entries.append(current)
            continue

        field_match = re.match(r"^\s{2}([a-z_]+):\s*(.*)$", line)
        if field_match and current is not None:
            current.values[field_match.group(1)] = field_match.group(2).strip()

    return entries


def parse_templates(markdown: str) -> dict[str, str]:
    block = extract_yaml_block(markdown)
    templates: dict[str, str] = {}
    lines = block.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        match = re.match(r"^([a-z_]+):\s*\|\s*$", line)
        if not match:
            index += 1
            continue

        template_name = match.group(1)
        index += 1
        value_lines: list[str] = []
        while index < len(lines):
            value_line = lines[index].rstrip()
            if re.match(r"^[a-z_]+:\s*\|\s*$", value_line):
                break
            if value_line.startswith("  "):
                value_lines.append(value_line[2:])
            elif not value_line:
                value_lines.append("")
            else:
                break
            index += 1
        templates[template_name] = "\n".join(value_lines).strip("\n")

    return templates


def load_templates(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return parse_templates(path.read_text(encoding="utf-8"))


def render_markdown(entries: list[Entry]) -> str:
    lines = ["# English Pronunciation", "", "```yaml"]
    for entry in entries:
        lines.append(f"{entry.key}:")
        for field in FIELDS:
            lines.append(f"  {field}: {entry.values.get(field, '')}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def normalize_word(text: str) -> str:
    return text.strip().lower()


def make_plural(word: str) -> str:
    lower = word.lower()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return f"{word}es"
    if lower.endswith("y") and len(word) > 1 and lower[-2] not in "aeiou":
        return f"{word[:-1]}ies"
    if lower.endswith("fe"):
        return f"{word[:-2]}ves"
    if lower.endswith("f"):
        return f"{word[:-1]}ves"
    return f"{word}s"


def stress_placeholder(word: str) -> str:
    return word.upper()


def create_entry(word: str, key: str) -> Entry:
    many = make_plural(word)
    return Entry(
        key=key,
        values={
            "word": word,
            "many": many,
            "pron_uk": "TODO",
            "pron_us": "TODO",
            "stress": stress_placeholder(word),
            "pron_uk_many": "TODO",
            "pron_us_many": "TODO",
            "stress_many": stress_placeholder(many),
            "ru": "TODO",
            "ru_other": "TODO",
            "used_phrase": "TODO",
        },
    )


def openai_json_request(api_key: str, model: str, word: str) -> dict[str, str]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": FIELDS,
        "properties": {field: {"type": "string"} for field in FIELDS},
    }
    prompt = (
        "Create a dictionary entry for one English noun. Return only schema fields. "
        "Use IPA slashes for pron_uk, pron_us, pron_uk_many, pron_us_many. "
        "Use classic British pronunciation for pron_uk and common American pronunciation for pron_us. "
        "Use stress in a simple learner format like MEN-u, with stressed syllables uppercase. "
        "For ru, give one most common Russian translation, one word if possible. "
        "For ru_other, give other possible Russian meanings separated by commas. "
        "For used_phrase, give three common English phrases with the word separated by commas. "
        "If the word is usually uncountable, still provide the common plural form if it exists; "
        "otherwise repeat the word in many and plural pronunciation fields.\n\n"
        f"Word: {word}"
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are an expert English phonetics and English-Russian dictionary assistant. "
                    "Be concise and accurate."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "pronunciation_entry",
                "schema": schema,
                "strict": True,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error: {exc.code} {details}") from exc

    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    text = content["text"]
                    break
            if text:
                break
    if not text:
        raise RuntimeError("OpenAI API returned no text output.")

    values = json.loads(text)
    return {field: str(values.get(field, "")).strip() for field in FIELDS}


def safe_audio_file_name(word: str) -> str:
    safe_word = re.sub(r"[^A-Za-z0-9_-]+", "_", word).strip("_")
    return f"{safe_word or 'word'}.mp3"


def openai_speech_request(api_key: str, model: str, voice: str, word: str) -> bytes:
    payload = {
        "model": model,
        "voice": voice,
        "input": word,
        "instructions": (
            "Pronounce only this single English word in clear General American English. "
            "Do not add any other words."
        ),
        "response_format": "mp3",
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI TTS API error: {exc.code} {details}") from exc


def get_or_create_word_audio(config: Config, word: str) -> Path:
    config.audio_cache_dir.mkdir(parents=True, exist_ok=True)
    audio_path = config.audio_cache_dir / safe_audio_file_name(word)
    if audio_path.exists() and audio_path.stat().st_size > 0:
        return audio_path
    if not config.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY пустой, аудио произношение не создано.")

    audio = openai_speech_request(
        config.openai_api_key,
        config.tts_model,
        config.tts_voice,
        word,
    )
    audio_path.write_bytes(audio)
    return audio_path


def create_entry_with_openai(word: str, key: str, api_key: str, model: str) -> Entry:
    values = openai_json_request(api_key, model, word)
    values["word"] = normalize_word(values.get("word") or word)
    if values["word"] != normalize_word(word):
        values["word"] = word
    for field in FIELDS:
        values.setdefault(field, "")
    return Entry(key=key, values=values)


def find_entry(entries: list[Entry], word: str) -> Entry | None:
    normalized = normalize_word(word)
    for entry in entries:
        if normalize_word(entry.values.get("word", "")) == normalized:
            return entry
    return None


def next_key(entries: list[Entry]) -> str:
    max_number = 0
    for entry in entries:
        match = re.match(r"word(\d+)$", entry.key)
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"word{max_number + 1}"


def load_or_create_entries(path: Path) -> list[Entry]:
    if not path.exists():
        path.write_text(render_markdown([]), encoding="utf-8")
    return parse_entries(path.read_text(encoding="utf-8"))


def upsert_word(
    path: Path,
    word: str,
    openai_api_key: str = "",
    openai_model: str = DEFAULT_OPENAI_MODEL,
) -> tuple[Entry, bool]:
    entries = load_or_create_entries(path)
    existing = find_entry(entries, word)
    if existing:
        return existing, False

    key = next_key(entries)
    if openai_api_key:
        entry = create_entry_with_openai(word, key, openai_api_key, openai_model)
    else:
        entry = create_entry(word, key)
    entries.append(entry)
    path.write_text(render_markdown(entries), encoding="utf-8")
    return entry, True


def format_entry(entry: Entry, template: str | None = None) -> str:
    if not template:
        return "\n".join(entry.values.get(field, "") for field in FIELDS)
    return template.format_map({field: entry.values.get(field, "") for field in FIELDS})


def render_entry_message(entry: Entry, template_file: Path = DEFAULT_TEMPLATE_FILE) -> str:
    templates = load_templates(template_file)
    return format_entry(entry, templates.get("word_card"))


class TelegramBot:
    def __init__(self, config: Config) -> None:
        self.api_base = f"https://api.telegram.org/bot{config.telegram_token}"
        self.config = config

    def request(self, method: str, params: dict[str, object] | None = None) -> dict:
        data = None
        if params is not None:
            data = urllib.parse.urlencode(params).encode("utf-8")

        with urllib.request.urlopen(f"{self.api_base}/{method}", data=data, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not payload.get("ok"):
            description = payload.get("description", "Telegram API request failed")
            raise RuntimeError(description)

        return payload

    def send_message(self, chat_id: int, text: str) -> None:
        self.request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
        )

    def multipart_request(self, method: str, fields: dict[str, object], files: dict[str, Path]) -> dict:
        boundary = f"----ArrTeamEnglish{int(time.time() * 1000)}"
        chunks: list[bytes] = []

        for name, value in fields.items():
            chunks.append(f"--{boundary}\r\n".encode("utf-8"))
            chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            chunks.append(str(value).encode("utf-8"))
            chunks.append(b"\r\n")

        for name, path in files.items():
            filename = path.name
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            chunks.append(f"--{boundary}\r\n".encode("utf-8"))
            chunks.append(
                (
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8")
            )
            chunks.append(path.read_bytes())
            chunks.append(b"\r\n")

        chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(chunks)
        request = urllib.request.Request(
            f"{self.api_base}/{method}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok"):
            description = payload.get("description", "Telegram API request failed")
            raise RuntimeError(description)
        return payload

    def send_audio(self, chat_id: int, audio_path: Path, title: str) -> None:
        self.multipart_request(
            "sendAudio",
            {
                "chat_id": chat_id,
                "title": title,
            },
            {"audio": audio_path},
        )

    def get_updates(self, offset: int | None) -> list[dict]:
        params: dict[str, object] = {"timeout": 50}
        if offset is not None:
            params["offset"] = offset
        return self.request("getUpdates", params).get("result", [])

    def handle_text(self, chat_id: int, text: str) -> None:
        word = normalize_word(text)
        if word in {"/start", "/help"}:
            self.send_message(
                chat_id,
                (
                    "Привет! Напиши одно английское слово, а я добавлю его в словарь "
                    "или покажу уже сохраненную карточку. После карточки пришлю AI-аудио "
                    "с американским произношением."
                ),
            )
            return

        if not WORD_RE.match(word):
            self.send_message(chat_id, "Пришли одно английское слово без пробелов.")
            return

        try:
            entry, _created = upsert_word(
                self.config.pronunciation_file,
                word,
                self.config.openai_api_key,
                self.config.openai_model,
            )
        except Exception as exc:
            print(f"Не удалось заполнить слово через OpenAI ({word}): {exc}")
            entry, _created = upsert_word(self.config.pronunciation_file, word)
        self.send_message(chat_id, render_entry_message(entry, self.config.template_file))
        try:
            audio_word = entry.values.get("word", word)
            audio_path = get_or_create_word_audio(self.config, audio_word)
            self.send_audio(chat_id, audio_path, audio_word)
        except Exception as exc:
            print(f"Не удалось отправить аудио произношение ({word}): {exc}")

    def run(self) -> None:
        print("Telegram-бот запущен. Нажмите Ctrl+C, чтобы остановить.")
        offset: int | None = None

        while True:
            try:
                for update in self.get_updates(offset):
                    offset = update["update_id"] + 1
                    message = update.get("message") or update.get("edited_message") or {}
                    text = message.get("text")
                    chat = message.get("chat") or {}
                    chat_id = chat.get("id")
                    if isinstance(chat_id, int) and isinstance(text, str):
                        self.handle_text(chat_id, text)
            except KeyboardInterrupt:
                print("Остановлено.")
                return
            except Exception as exc:
                print(f"Ошибка: {exc}")
                time.sleep(5)


def main() -> None:
    config = get_config()
    TelegramBot(config).run()


if __name__ == "__main__":
    main()
