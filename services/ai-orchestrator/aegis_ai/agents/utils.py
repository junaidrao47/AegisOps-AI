from __future__ import annotations

import re
from typing import Any, Iterable


def extract_text(payload: dict[str, Any], keys: Iterable[str]) -> str:
    parts: list[str] = []
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(_flatten_list(value))
        elif isinstance(value, dict):
            parts.extend(_flatten_list(value.values()))
    return "\n".join(part for part in parts if part)


def keyword_hits(text: str, patterns: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern)
    return hits


def _flatten_list(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, str):
            output.append(item)
        elif isinstance(item, (list, tuple)):
            output.extend(_flatten_list(item))
        elif isinstance(item, dict):
            output.extend(_flatten_list(item.values()))
        else:
            output.append(str(item))
    return output
