from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from transformers.modeling_outputs import BaseModelOutputWithPooling

from app.services.siglip2_embeddings import Siglip2Config, Siglip2EmbeddingService


_SAMPLE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x89\x1f\xa0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class _StubTokenizer:
    def __call__(self, text, return_tensors="pt", padding=False):
        assert return_tensors == "pt"
        assert text is not None
        return {"input_ids": torch.tensor([[1, 2, 3]])}


class _StubSiglip2ImageProcessor:
    def __init__(self, *, return_unbatched: bool = False) -> None:
        self._return_unbatched = return_unbatched

    def __call__(self, *, images=None, return_tensors="pt"):
        assert return_tensors == "pt"
        assert images is not None
        if self._return_unbatched:
            return {
                "pixel_values": torch.zeros((256, 768), dtype=torch.float32),
                "pixel_attention_mask": torch.ones((256,), dtype=torch.int64),
                "spatial_shapes": torch.tensor([16, 16], dtype=torch.int64),
            }
        return {
            "pixel_values": torch.zeros((1, 256, 768), dtype=torch.float32),
            "pixel_attention_mask": torch.ones((1, 256), dtype=torch.int64),
            "spatial_shapes": torch.tensor([[16, 16]], dtype=torch.int64),
        }


class _StubModel:
    def __init__(self, *, model_type: str = "siglip2") -> None:
        self.config = SimpleNamespace(model_type=model_type)
        self.last_image_shape: tuple[int, ...] | None = None

    def to(self, device):
        return self

    def eval(self):
        return self

    def get_text_features(self, **kwargs):
        return BaseModelOutputWithPooling(
            last_hidden_state=torch.tensor(
                [[[3.0, 4.0, 0.0, 0.0], [3.0, 4.0, 0.0, 0.0]]],
                dtype=torch.float32,
            ),
            pooler_output=torch.tensor([[3.0, 4.0, 0.0, 0.0]], dtype=torch.float32),
        )

    def get_image_features(self, **kwargs):
        pixel_values = kwargs.get("pixel_values")
        if isinstance(pixel_values, torch.Tensor):
            self.last_image_shape = tuple(pixel_values.shape)
        return BaseModelOutputWithPooling(
            last_hidden_state=torch.tensor(
                [[[0.0, 3.0, 4.0, 0.0], [0.0, 3.0, 4.0, 0.0]]],
                dtype=torch.float32,
            ),
            pooler_output=torch.tensor([[0.0, 3.0, 4.0, 0.0]], dtype=torch.float32),
        )


def _build_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    embed_dim: int,
    return_unbatched_pixel_values: bool = False,
    model_type: str = "siglip2",
) -> Siglip2EmbeddingService:
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.AutoModel.from_pretrained",
        lambda *args, **kwargs: _StubModel(model_type=model_type),
    )
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.Siglip2Tokenizer.from_pretrained",
        lambda *args, **kwargs: _StubTokenizer(),
    )
    monkeypatch.setattr(
        "app.services.siglip2_embeddings.Siglip2ImageProcessor.from_pretrained",
        lambda *args, **kwargs: _StubSiglip2ImageProcessor(
            return_unbatched=return_unbatched_pixel_values
        ),
    )

    config = Siglip2Config(
        model_id="google/siglip2-base-patch16-naflex",
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
    vector = service.embed_image(image_bytes=_SAMPLE_PNG_BYTES)

    assert len(vector) == 4
    np.testing.assert_allclose(vector, np.array([0.0, 0.6, 0.8, 0.0], dtype=np.float32))
    assert service._model.last_image_shape == (1, 256, 768)


def test_embed_image_unsqueezes_unbatched_siglip2_pixel_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service(monkeypatch, embed_dim=4, return_unbatched_pixel_values=True)
    vector = service.embed_image(image_bytes=_SAMPLE_PNG_BYTES)

    assert len(vector) == 4
    np.testing.assert_allclose(vector, np.array([0.0, 0.6, 0.8, 0.0], dtype=np.float32))
    assert service._model.last_image_shape == (1, 256, 768)


def test_raises_on_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="embedding dimension mismatch"):
        _build_service(monkeypatch, embed_dim=8)


def test_raises_for_non_siglip2_model(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="must resolve to a SigLIP2 model"):
        _build_service(monkeypatch, embed_dim=4, model_type="siglip")
