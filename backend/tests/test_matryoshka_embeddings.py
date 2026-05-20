from pathlib import Path

import numpy as np
import pytest

from app.services.text_embeddings import EmbeddingConfig, EmbeddingService


class _StubSentenceTransformer:
    def __init__(self, vector: np.ndarray) -> None:
        self._vector = vector
        self.calls = []

    def encode(self, texts, *, prompt_name: str, normalize_embeddings: bool, convert_to_numpy: bool):
        self.calls.append(
            {
                "texts": texts,
                "prompt_name": prompt_name,
                "normalize_embeddings": normalize_embeddings,
                "convert_to_numpy": convert_to_numpy,
            }
        )
        return self._vector


def _build_service(monkeypatch: pytest.MonkeyPatch, *, embed_dim: int, model_output_dim: int) -> EmbeddingService:
    model_output = np.arange(model_output_dim, dtype=np.float32).reshape(1, model_output_dim)

    monkeypatch.setattr(
        EmbeddingService,
        "_load_model",
        lambda self, config: _StubSentenceTransformer(model_output),
    )

    config = EmbeddingConfig(
        model_id="lightonai/DenseOn",
        model_dir=Path("/tmp"),
        embed_dim=embed_dim,
    )
    return EmbeddingService(config)


def test_embed_query_uses_denseon_query_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=768, model_output_dim=768)

    result = service.embed_query(query="test")

    assert len(result) == 768
    np.testing.assert_array_equal(result, np.arange(768, dtype=np.float32))
    assert service._model.calls == [
        {
            "texts": ["test"],
            "prompt_name": "query",
            "normalize_embeddings": True,
            "convert_to_numpy": True,
        }
    ]


def test_embed_document_uses_denseon_document_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=768, model_output_dim=768)

    service.embed_document(title="Title", text="Body")

    assert service._model.calls[0]["texts"] == ["Title\n\nBody"]
    assert service._model.calls[0]["prompt_name"] == "document"


def test_embed_query_raises_when_model_output_is_too_small(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=768, model_output_dim=128)

    with pytest.raises(ValueError, match="expected 768, got 128"):
        service.embed_query(query="test")
