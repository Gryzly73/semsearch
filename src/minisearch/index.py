"""In-memory vector index with cosine search."""

from .corpus import Document
from .embed import Embedder


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class Index:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self.docs: list[Document] = []
        self.vectors: list[list[float]] = []

    def add(self, doc: Document) -> None:
        self.docs.append(doc)
        self.vectors.append(self.embedder.embed(doc.text))

    def add_many(self, docs: list[Document]) -> None:
        for doc in docs:
            self.add(doc)

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        """Return the top-k documents by cosine similarity (vectors are unit length)."""
        q = self.embedder.embed(query)
        scored = [(doc, _dot(q, vec)) for doc, vec in zip(self.docs, self.vectors, strict=True)]
        scored.sort(key=lambda pair: (-pair[1], pair[0].id))
        return [(d, s) for d, s in scored[:k] if s > 0.0]
