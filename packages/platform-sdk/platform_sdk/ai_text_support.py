from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def normalize_word_key(value: str | None) -> str:
    return (value or '').strip().lower()


def normalize_word_list(values) -> list[str]:
    if isinstance(values, str):
        candidates = values.replace('，', ',').split(',')
    elif isinstance(values, (list, tuple, set)):
        candidates = list(values)
    elif values in (None, ''):
        candidates = []
    else:
        candidates = [values]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text_value = str(item or '').strip()
        key = normalize_word_key(text_value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(text_value)
    return normalized


def parse_client_epoch_ms(value) -> datetime | None:
    if value in (None, '', 0):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def load_json_data(data_dir: str, filename: str, default):
    path = os.path.join(data_dir, filename)
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception:
        return default
