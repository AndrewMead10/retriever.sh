from pathlib import Path

import numpy as np
import pytest
import torch

from app.services.siglip2_embeddings import Siglip2Config, Siglip2EmbeddingService


class _StubTokenizer:
    def __call__(self, text, return_tensors="pt", padding=False):
        assert return_tensors == "pt"
        assert text is not None
        return {"input_ids": torch.tensor([[1, 2, 3]])}


class _StubImageProcessor:
    def __call__(self, *, images=None, return_tensors="pt"):
        assert return_tensors == "pt"
        assert images is not None
        return {"pixel_values": torch.zeros((1, 3, 2, 2), dtype=torch.float32)}


class _StubModel:
    def to(self, device):
        return self

    def eval(self):
        return self

    def get_text_features(self, **kwargs):
        return torch.tensor([[3.0, 4.0, 0.0, 0.0]], dtype=torch.float32)

    def get_image_features(self, **kwargs):
        return torch.tensor([[0.0, 3.0, 4.0, 0.0]], dtype=torch.float32)


def _build_service(monkeypatch: pytest.MonkeyPatch, *, embed_dim: int) -> Siglip2EmbeddingService:
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.Siglip2Tokenizer.from_pretrained",
        lambda *args, **kwargs: _StubTokenizer(),
    )
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.Siglip2ImageProcessor.from_pretrained",
        lambda *args, **kwargs: _StubImageProcessor(),
    )
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.AutoModel.from_pretrained",
        lambda *args, **kwargs: _StubModel(),
    )

    config = Siglip2Config(
        model_id="google/siglip2-base-patch16-224",
        model_dir=Path("/tmp"),
        embed_dim=embed_dim,
    )
    return Siglip2EmbeddingService(config)


def test_embed_text_normalises_output(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=4)
    vector = service.embed_text(query="test query")

    assert len(vector) == 4
    np.testing.assert_allclose(vector, np.array([0.6, 0.8, 0.0, 0.0], dtype=np.float32))


def test_embed_image_normalises_output(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _build_service(monkeypatch, embed_dim=4)
    image_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x89\x1f\xa0"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    vector = service.embed_image(image_bytes=image_bytes)

    assert len(vector) == 4
    np.testing.assert_allclose(vector, np.array([0.0, 0.6, 0.8, 0.0], dtype=np.float32))


def test_raises_on_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="embedding dimension mismatch"):
        _build_service(monkeypatch, embed_dim=8)
