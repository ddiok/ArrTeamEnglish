from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError

from bot import get_config, load_or_create_entries, save_entries


CYRILLIC_FIELDS = [
    "pron_uk_ru",
    "pron_us_ru",
    "pron_uk_many_ru",
    "pron_us_many_ru",
]


def openai_cyrillic_request(
    api_key: str,
    model: str,
    values: dict[str, str],
) -> dict[str, str]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": CYRILLIC_FIELDS,
        "properties": {field: {"type": "string"} for field in CYRILLIC_FIELDS},
    }
    prompt = (
        "Fill approximate English pronunciation using Russian Cyrillic letters for a Russian-speaking learner. "
        "Return each value wrapped in slashes. Mark the stressed syllable with uppercase Cyrillic letters. "
        "Keep it concise and readable, not academic. Use the IPA and stress hints below.\n\n"
        f"word: {values.get('word', '')}\n"
        f"many: {values.get('many', '')}\n"
        f"pron_uk: {values.get('pron_uk', '')}\n"
        f"pron_us: {values.get('pron_us', '')}\n"
        f"stress: {values.get('stress', '')}\n"
        f"pron_uk_many: {values.get('pron_uk_many', '')}\n"
        f"pron_us_many: {values.get('pron_us_many', '')}\n"
        f"stress_many: {values.get('stress_many', '')}"
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are an English pronunciation assistant for Russian speakers. "
                    "Be practical and consistent."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cyrillic_pronunciation",
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

    result = json.loads(text)
    return {field: str(result.get(field, "")).strip() for field in CYRILLIC_FIELDS}


def main() -> int:
    config = get_config()
    if not config.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY пустой.")

    entries = load_or_create_entries(config.pronunciation_file)
    changed = False

    for entry in entries:
        if all(entry.values.get(field) for field in CYRILLIC_FIELDS):
            continue
        values = openai_cyrillic_request(config.openai_api_key, config.openai_model, entry.values)
        entry.values.update(values)
        changed = True
        print(f"{entry.values.get('word', '')}: {values}")

    if changed:
        save_entries(config.pronunciation_file, entries)
    else:
        print("Все русскобуквенные произношения уже заполнены.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
