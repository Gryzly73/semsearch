"""Embedders turn text into fixed-size vectors."""

import math
from typing import Protocol

from .tokenize import tokenize


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Bag-of-words embedder using the hashing trick. No network, no model files."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            vec[hash(token) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]
