from pathlib import Path

import numpy as np
import pytest

from app.services.vectorlab.embeddings import EmbeddingConfig, EmbeddingService


class _StubLlama:
    def __init__(self, vector: np.ndarray) -> None:
        self._vector = vector

    def embed(self, _prompt: str):
        return self._vector


def _build_service(monkeypatch: pytest.MonkeyPatch, *, embed_dim: int, model_output_dim: int) -> EmbeddingService:
    model_output = np.arange(model_output_dim, dtype=np.float32)

    monkeypatch.setattr(
        EmbeddingService,
        "_ensure_model_file",
        lambda self, config: Path("/tmp/test-model.gguf"),
    )
    monkeypatch.setattr(
        EmbeddingService,
        "_load_model",
        lambda self, model_path, config: _StubLlama(model_output),
    )

    config = EmbeddingConfig(
        model_repo="repo",
        model_filename="model.gguf",
        model_dir=Path("/tmp"),
        embed_dim=embed_dim,
    )
    return EmbeddingService(config)


def test_embed_query_truncates_with_matryoshka_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=256, model_output_dim=768)

    result = service.embed_query(query="test")

    assert len(result) == 256
    np.testing.assert_array_equal(result, np.arange(256, dtype=np.float32))


def test_embed_query_raises_when_model_output_is_too_small(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=256, model_output_dim=128)

    with pytest.raises(ValueError, match="expected at least 256, got 128"):
        service.embed_query(query="test")

