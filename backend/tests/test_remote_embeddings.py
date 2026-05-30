import json

import httpx
import pytest

from app.services.text_embeddings import EmbeddingConfig, EmbeddingProviderError, EmbeddingService


def _build_service(handler, *, embed_dim: int = 512) -> EmbeddingService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    config = EmbeddingConfig(
        endpoint="https://embedding.example.test",
        api_key="test-key",
        model_id="jinaai/jina-embeddings-v5-omni-small-retrieval",
        embed_dim=embed_dim,
        timeout=5.0,
    )
    return EmbeddingService(config, client=client)


def test_embed_query_calls_remote_query_task() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [{"object": "embedding", "embedding": [0.1] * 512, "index": 0}],
            },
        )

    service = _build_service(handler)

    result = service.embed_query(content=[{"type": "text", "text": "test"}])

    assert len(result) == 512
    assert result[0] == 0.1
    assert requests[0].url == "https://embedding.example.test/v1/embeddings"
    assert requests[0].headers["authorization"] == "Bearer test-key"
    payload = json.loads(requests[0].content)
    assert payload["task_type"] == "retrieval.query"
    assert payload["dimensions"] == 512
    assert payload["input"] == ["test"]


def test_embed_item_calls_remote_passage_task() -> None:
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.read())
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.2] * 512}]},
        )

    service = _build_service(handler)

    service.embed_item(title="Title", content=[{"type": "text", "text": "Body"}])

    assert b'"input":["Title\\n\\nBody"]' in bodies[0]
    assert b'"task_type":"retrieval.passage"' in bodies[0]


def test_embed_item_sends_multimodal_content_blocks() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.read()))
        return httpx.Response(200, json={"data": [{"embedding": [0.3] * 512}]})

    service = _build_service(handler)

    service.embed_item(
        title="Product",
        content=[
            {"type": "text", "text": "Waterproof boot"},
            {"type": "image_url", "url": "https://example.com/boot.png"},
        ],
    )

    assert bodies[0]["input"] == [
        {
            "content": [
                {"type": "text", "value": "Product"},
                {"type": "text", "value": "Waterproof boot"},
                {"type": "image", "format": "url", "value": "https://example.com/boot.png"},
            ]
        }
    ]


def test_embed_query_raises_when_remote_dimension_is_wrong() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"embedding": [0.1] * 128}]})

    service = _build_service(handler, embed_dim=512)

    with pytest.raises(ValueError, match="expected 512, got 128"):
        service.embed_query(content=[{"type": "text", "text": "test"}])


def test_missing_api_key_raises_provider_error() -> None:
    config = EmbeddingConfig(
        endpoint="https://embedding.example.test",
        api_key="",
        model_id="jinaai/jina-embeddings-v5-omni-small-retrieval",
        embed_dim=512,
        timeout=5.0,
    )
    service = EmbeddingService(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))))

    with pytest.raises(EmbeddingProviderError, match="RAG_EMBEDDING_API_KEY"):
        service.embed_query(content=[{"type": "text", "text": "test"}])


def test_remote_error_raises_provider_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key."}})

    service = _build_service(handler)

    with pytest.raises(EmbeddingProviderError, match="Remote embedding request failed: 401"):
        service.embed_query(content=[{"type": "text", "text": "test"}])
