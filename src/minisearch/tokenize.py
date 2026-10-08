"""Text -> tokens (English + Russian)."""

import re

_TOKEN = re.compile(r"[a-zа-яё0-9]+")
_STOP = frozenset(
    "как что для при из за на в во с со и а о об по к от до не ли же бы у но или это есть".split()
)
_SUFFIXES = sorted(
    (
        "ами ями ого его ому ему ыми ими ией ах ях ов ев ой ей ом ем ам ям ую юю ая яя ое ее "
        "ые ие ых их ым им ть ет ит ют ут ат ят ешь ишь ется ится ла ло ли на ны ни ну ню "
        "а я о е ы и у ю ь й"
    ).split(),
    key=len,
    reverse=True,
)


def stem(token: str) -> str:
    """Very small suffix stripper for Russian; other tokens are returned unchanged."""
    if not token or not ("а" <= token[0] <= "я"):
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase, fold ё to е, split, drop Russian stopwords, stem Russian tokens."""
    tokens = _TOKEN.findall(text.lower().replace("ё", "е"))
    return [stem(t) for t in tokens if t not in _STOP]
