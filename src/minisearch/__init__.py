"""minisearch: a tiny search library (hashing embedder + cosine similarity)."""

from .corpus import Document, load_jsonl
from .embed import HashingEmbedder
from .index import Index

__all__ = ["Document", "HashingEmbedder", "Index", "load_jsonl"]
