"""Text -> tokens."""

import re

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase the text and split it into alphanumeric tokens."""
    return _TOKEN.findall(text.lower())
