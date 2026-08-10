from __future__ import annotations

from typing import Any

from mnamer.exceptions import MnamerException
from mnamer.metadata import Metadata, MetadataEpisode, MetadataMovie

SMART_MATCH_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_MODEL: Any = None
_MODEL_INITIALIZED = False


class SmartMatchUnavailable(MnamerException):
    """Raised when the optional smart-match model cannot be loaded."""


def _load_model() -> Any:
    global _MODEL, _MODEL_INITIALIZED
    if _MODEL_INITIALIZED:
        return _MODEL
    try:
        from sentence_transformers import (  # type: ignore[import-not-found]
            SentenceTransformer,  # type: ignore[import-not-found]
        )
    except ImportError as error:
        raise SmartMatchUnavailable(
            "smart matching requires the optional dependency; install "
            'mnamer with `pip install "mnamer[smart-match]"`'
        ) from error
    try:
        _MODEL = SentenceTransformer(SMART_MATCH_MODEL)
    except Exception as error:
        raise SmartMatchUnavailable(
            f"smart matching model '{SMART_MATCH_MODEL}' could not be loaded"
        ) from error
    _MODEL_INITIALIZED = True
    return _MODEL


def _title(metadata: Metadata) -> str | None:
    if isinstance(metadata, MetadataMovie):
        return metadata.name
    if isinstance(metadata, MetadataEpisode):
        return metadata.series
    return None


def _similarity(first: Any, second: Any) -> float:
    return sum(
        float(left) * float(right) for left, right in zip(first, second, strict=True)
    )


def rank_matches(query: Metadata, matches: list[Metadata]) -> list[Metadata]:
    """Rerank movie or episode matches by semantic title similarity."""
    query_title = _title(query)
    scorable = [
        (index, metadata, _title(metadata))
        for index, metadata in enumerate(matches)
        if _title(metadata)
    ]
    if not query_title or len(scorable) < 2:
        return matches

    model = _load_model()
    titles = [query_title, *(title for _, _, title in scorable)]
    try:
        embeddings = model.encode(titles, normalize_embeddings=True)
        query_embedding = embeddings[0]
        ranked = [
            (
                _similarity(query_embedding, embeddings[position + 1]),
                index,
                metadata,
            )
            for position, (index, metadata, _) in enumerate(scorable)
        ]
        ranked.sort(
            key=lambda result: result[0],
            reverse=True,
        )
    except Exception as error:
        raise SmartMatchUnavailable(
            "smart matching failed while encoding titles"
        ) from error

    ranked_matches = [metadata for _, _, metadata in ranked]
    ranked_indexes = {index for _, index, _ in ranked}
    return ranked_matches + [
        metadata
        for index, metadata in enumerate(matches)
        if index not in ranked_indexes
    ]
