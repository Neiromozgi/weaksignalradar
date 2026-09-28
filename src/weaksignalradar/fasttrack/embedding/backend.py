"""Embedding backends: frozen E5 profile with swappable runtime encoder."""

from __future__ import annotations

import hashlib
import math
import os
from abc import ABC, abstractmethod

from ..config.embedding_profile import E5_SMALL_V1, EmbeddingProfile


class EmbeddingUnavailableError(RuntimeError):
    """Frozen embedding runtime could not be loaded."""


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector dimension mismatch")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return max(-1.0, min(1.0, dot))


class EmbeddingBackend(ABC):
    profile: EmbeddingProfile

    @property
    def backend_name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicTestBackend(EmbeddingBackend):
    """Reproducible 384-d vectors for unit tests (not the HF model)."""

    profile = E5_SMALL_V1

    def encode(self, texts: list[str]) -> list[list[float]]:
        dim = self.profile.vector_dimension
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vec = []
            for i in range(dim):
                b = digest[i % len(digest)]
                vec.append((b / 127.5) - 1.0)
            out.append(_l2_normalize(vec))
        return out


class SentenceTransformerBackend(EmbeddingBackend):
    profile = E5_SMALL_V1

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        self._model = SentenceTransformer(
            self.profile.embedding_model_id,
            revision=self.profile.embedding_model_revision,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [list(map(float, row)) for row in vectors]


def embedding_runtime_status() -> str:
    mode = os.environ.get("WSR_EMBEDDING_BACKEND", "auto").strip().lower()
    if mode in {"test", "deterministic", "test_deterministic"}:
        return "TEST_DETERMINISTIC"
    if mode == "disabled":
        return "DISABLED"
    try:
        import sentence_transformers  # noqa: F401

        return "AVAILABLE"
    except ImportError:
        return "EMBEDDING_UNAVAILABLE"


def get_embedding_backend(*, allow_none: bool = False) -> EmbeddingBackend | None:
    mode = os.environ.get("WSR_EMBEDDING_BACKEND", "auto").strip().lower()
    if mode in {"test", "deterministic", "test_deterministic"}:
        return DeterministicTestBackend()
    if mode == "disabled":
        if allow_none:
            return None
        raise EmbeddingUnavailableError("WSR_EMBEDDING_BACKEND=disabled")
    try:
        return SentenceTransformerBackend()
    except Exception as exc:
        if allow_none:
            return None
        raise EmbeddingUnavailableError(str(exc)) from exc


def encode_single(backend: EmbeddingBackend | None, text: str | None) -> list[float] | None:
    if backend is None or text is None or not text.strip():
        return None
    return backend.encode([text])[0]
