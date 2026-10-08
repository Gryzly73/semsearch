from minisearch import Document, HashingEmbedder, Index
from minisearch.tokenize import tokenize


def test_tokenize_english():
    assert tokenize("Hello, World 42!") == ["hello", "world", "42"]


def test_embedding_is_unit_length():
    vec = HashingEmbedder().embed("sourdough bread starter")
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-9


def test_empty_text_gives_zero_vector():
    assert sum(HashingEmbedder().embed("")) == 0.0


def test_search_ranks_relevant_doc_first():
    index = Index(HashingEmbedder())
    index.add(Document("a", "bread and flour and water"))
    index.add(Document("b", "black holes and gravity"))
    hits = index.search("flour for bread", k=2)
    assert hits[0][0].id == "a"
