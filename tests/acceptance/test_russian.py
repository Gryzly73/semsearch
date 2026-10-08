"""T2 acceptance: Russian text is tokenized and normalized.

DO NOT EDIT: protected by the harness.
"""

from minisearch.tokenize import tokenize


def test_cyrillic_tokens_are_not_dropped():
    assert tokenize("Чёрные дыры") != []


def test_inflected_forms_share_a_token():
    assert set(tokenize("хлеба")) & set(tokenize("хлеб"))
    assert set(tokenize("водой")) & set(tokenize("воды"))


def test_yo_equals_ye():
    assert tokenize("свёкла") == tokenize("свекла")


def test_english_unchanged():
    assert tokenize("Hello, World 42!") == ["hello", "world", "42"]
