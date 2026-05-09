from __future__ import annotations

import argparse
import sys

from bot import find_entry, get_config, load_or_create_entries, render_entry_message


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Применить шаблон сообщения к слову из english-pronunciation.md."
    )
    parser.add_argument("word", help="Английское слово из словаря, например access.")
    args = parser.parse_args()

    config = get_config()
    entries = load_or_create_entries(config.pronunciation_file)
    entry = find_entry(entries, args.word)
    if entry is None:
        print(f"Слово не найдено: {args.word}", file=sys.stderr)
        return 1

    print(render_entry_message(entry, config.template_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
