from __future__ import annotations

from bot import (
    audio_link,
    get_config,
    get_or_create_word_audio,
    load_or_create_entries,
    save_entries,
)


def main() -> int:
    config = get_config()
    entries = load_or_create_entries(config.pronunciation_file)

    changed = False
    for entry in entries:
        word = entry.values.get("word", "").strip()
        if not word:
            continue
        audio_path = get_or_create_word_audio(config, word)
        link = audio_link(config, audio_path)
        if entry.values.get("link") != link:
            entry.values["link"] = link
            changed = True
            print(f"{word}: {link}")

    if changed:
        save_entries(config.pronunciation_file, entries)
    else:
        print("Все link уже актуальны.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
