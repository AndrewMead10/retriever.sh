from __future__ import annotations

import io
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, Siglip2ImageProcessor, Siglip2Tokenizer


_TORCH_DTYPES = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}


@dataclass(frozen=True)
class Siglip2Config:
    model_id: str
    model_dir: Path
    embed_dim: int
    device: str = "cpu"
    dtype: str = "float32"
    hf_token: str | None = None


class Siglip2EmbeddingService:
    def __init__(self, config: Siglip2Config) -> None:
        self._config = config
        self._lock = threading.RLock()
        torch_dtype = _TORCH_DTYPES.get(config.dtype.lower())
        if torch_dtype is None:
            raise ValueError(f"Unsupported RAG_IMAGE_DTYPE: {config.dtype}")

        self._model = AutoModel.from_pretrained(
            config.model_id,
            token=config.hf_token,
            cache_dir=str(config.model_dir),
            torch_dtype=torch_dtype,
        )
        self._model_type = str(getattr(self._model.config, "model_type", "")).lower()
        if self._model_type != "siglip2":
            raise ValueError(
                "RAG_IMAGE_MODEL_ID must resolve to a SigLIP2 model "
                f"(got model_type='{self._model_type or 'unknown'}' for '{config.model_id}'). "
                "Use a SigLIP2 checkpoint such as 'google/siglip2-base-patch16-naflex'."
            )
        self._image_processor = Siglip2ImageProcessor.from_pretrained(
            config.model_id,
            token=config.hf_token,
            cache_dir=str(config.model_dir),
        )
        self._tokenizer = Siglip2Tokenizer.from_pretrained(
            config.model_id,
            token=config.hf_token,
            cache_dir=str(config.model_dir),
            use_fast=False,
        )
        self._device = torch.device(config.device)
        self._model.to(self._device)
        self._model.eval()

        self._actual_dim = self._detect_embedding_dim()
        if self._actual_dim != config.embed_dim:
            raise ValueError(
                f"SigLIP2 embedding dimension mismatch: expected {config.embed_dim}, got {self._actual_dim}"
            )

    @property
    def embedding_dim(self) -> int:
        return self._actual_dim

    def embed_text(self, *, query: str) -> Sequence[float]:
        if not query.strip():
            raise ValueError("Text query cannot be empty")
        with self._lock:
            model_inputs = self._tokenizer(
                [query],
                return_tensors="pt",
                padding="max_length",
                truncation=True,
            )
            return self._encode_text_inputs(model_inputs)

    def embed_image(self, *, image_bytes: bytes) -> Sequence[float]:
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb_image = image.convert("RGB")
        with self._lock:
            model_inputs = self._image_processor(images=[rgb_image], return_tensors="pt")
            return self._encode_image_inputs(model_inputs)

    def _detect_embedding_dim(self) -> int:
        with torch.inference_mode():
            model_inputs = self._tokenizer(
                ["dimension probe"],
                return_tensors="pt",
                padding="max_length",
                truncation=True,
            )
            embedding = self._encode_text_inputs(model_inputs)
            return len(embedding)

    def _encode_text_inputs(self, model_inputs: dict) -> Sequence[float]:
        with torch.inference_mode():
            tensors = {
                key: value.to(self._device)
                for key, value in model_inputs.items()
                if isinstance(value, torch.Tensor)
            }
            raw_features = self._model.get_text_features(**tensors)
            features = self._coerce_feature_tensor(raw_features)
            normalised = torch.nn.functional.normalize(features, p=2, dim=-1)
            vector = normalised[0].detach().to("cpu", dtype=torch.float32).numpy()
        return self._normalise_vector(vector)

    def _encode_image_inputs(self, model_inputs: dict) -> Sequence[float]:
        with torch.inference_mode():
            tensors = {
                key: value.to(self._device)
                for key, value in model_inputs.items()
                if isinstance(value, torch.Tensor)
            }
            self._coerce_pixel_values_shape(tensors)
            raw_features = self._model.get_image_features(**tensors)
            features = self._coerce_feature_tensor(raw_features)
            normalised = torch.nn.functional.normalize(features, p=2, dim=-1)
            vector = normalised[0].detach().to("cpu", dtype=torch.float32).numpy()
        return self._normalise_vector(vector)

    def _coerce_pixel_values_shape(self, tensors: dict[str, torch.Tensor]) -> None:
        pixel_values = tensors.get("pixel_values")
        if not isinstance(pixel_values, torch.Tensor):
            raise ValueError("Image processor did not return a pixel_values tensor")
        if pixel_values.ndim == 2:
            tensors["pixel_values"] = pixel_values.unsqueeze(0)
            return
        if pixel_values.ndim != 3:
            raise ValueError(
                "Expected SigLIP2 pixel_values to be 2D or 3D, "
                f"got shape {tuple(pixel_values.shape)}"
            )

    def _coerce_feature_tensor(self, raw_features: Any) -> torch.Tensor:
        if isinstance(raw_features, torch.Tensor):
            features = raw_features
        elif isinstance(raw_features, (tuple, list)) and raw_features and isinstance(raw_features[0], torch.Tensor):
            features = raw_features[0]
        else:
            pooler_output = getattr(raw_features, "pooler_output", None)
            if isinstance(pooler_output, torch.Tensor):
                features = pooler_output
            else:
                raise TypeError(
                    "SigLIP2 features must be a torch.Tensor or include pooler_output; "
                    f"got {type(raw_features).__name__}"
                )

        if features.ndim == 1:
            features = features.unsqueeze(0)
        if features.ndim != 2:
            raise ValueError(f"Expected 2D SigLIP2 feature tensor, got shape {tuple(features.shape)}")
        return features

    def _normalise_vector(self, vector: np.ndarray) -> Sequence[float]:
        expected_dim = getattr(self, "_actual_dim", vector.shape[0])
        if vector.shape[0] != expected_dim:
            raise ValueError(
                f"Unexpected embedding size from SigLIP2: expected {expected_dim}, got {vector.shape[0]}"
            )
        return vector.tolist()
