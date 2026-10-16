"""The real backend adapter against a fake OpenAI-compatible server (no model needed)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from vortex_api.main import create_app

from .conftest import make_settings, parse_sse


class FakeUpstream:
    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.mode == "down":
            raise httpx.ConnectError("connection refused", request=request)
        if self.mode == "error":
            return httpx.Response(500, text="model 'x' not found")
        body = json.loads(request.content) if request.content else {}
        self.requests.append({"path": request.url.path, "body": body})

        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "qwen2.5:7b-instruct-q4_K_M"}]})
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "model": body["model"],
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                },
            )
        if body.get("stream"):
            chunks = [
                {"id": "up", "choices": [{"index": 0, "delta": {"role": "assistant"}}]},
                {"id": "up", "choices": [{"index": 0, "delta": {"content": "Oi"}}]},
                {"id": "up", "choices": [{"index": 0, "delta": {"content": "!"}}]},
                {"id": "up", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                {"id": "up", "choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 2}},
            ]
            sse = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
            sse = ": keep-alive\n\n" + sse + "data: [DONE]\n\n"
            return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
        return httpx.Response(
            200,
            json={
                "id": "upstream-id",
                "object": "chat.completion",
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Oi!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 2, "total_tokens": 11},
            },
        )


@pytest.fixture
def upstream():
    return FakeUpstream()


@pytest.fixture
def client(tmp_path, upstream):
    app = create_app(
        make_settings(tmp_path, mock_backend=False),
        transports={"ollama": httpx.MockTransport(upstream)},
    )
    with TestClient(app) as c:
        yield c


def test_payload_is_rewritten_for_upstream(client, upstream):
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "vortex",
            "messages": [
                {"role": "developer", "content": "Responda em uma linha."},
                {"role": "user", "content": "Oi"},
            ],
            "max_completion_tokens": 50,
        },
    )
    assert r.status_code == 200
    assert r.json()["model"] == "vortex-v0.2.1"
    assert r.json()["id"].startswith("chatcmpl-vx")

    sent = upstream.requests[-1]["body"]
    assert sent["model"] == "vortex:0.2.1"
    assert sent["max_tokens"] == 50 and "max_completion_tokens" not in sent
    assert sent["temperature"] == 0.7  # registry default
    system = sent["messages"][0]
    assert system["role"] == "system"
    assert system["content"].startswith("Você é o Vortex")
    assert system["content"].endswith("Responda em uma linha.")
    assert [m["role"] for m in sent["messages"]] == ["system", "user"]


def test_client_values_override_defaults(client, upstream):
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "x"}], "temperature": 0.1, "seed": 7},
    )
    sent = upstream.requests[-1]["body"]
    assert sent["temperature"] == 0.1
    assert sent["seed"] == 7


def test_streaming_through_adapter(client, upstream):
    r = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "x"}], "stream": True},
    )
    events = parse_sse(r.text)
    assert events[-1] == "[DONE]"
    chunks = events[:-1]
    assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks) == "Oi!"
    assert all(c["model"] == "vortex-v0.2.1" for c in chunks)
    assert all(c["id"] == r.headers["x-vortex-completion-id"] for c in chunks)
    assert upstream.requests[-1]["body"]["stream_options"] == {"include_usage": True}

    usage = client.get("/api/usage").json()
    assert usage["prompt_tokens"] == 9 and usage["completion_tokens"] == 2


def test_embeddings_through_adapter(client, upstream):
    r = client.post("/v1/embeddings", json={"input": "olá"})
    assert r.json()["model"] == "vortex-embed"
    assert upstream.requests[-1]["body"]["model"] == "nomic-embed-text"


def test_health_through_adapter(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["backends"]["ollama"]["upstream_models"] == ["qwen2.5:7b-instruct-q4_K_M"]


@pytest.mark.parametrize(("mode", "status"), [("down", 503), ("error", 502)])
@pytest.mark.parametrize("stream", [False, True])
def test_backend_failures_become_http_errors(tmp_path, mode, status, stream):
    app = create_app(
        make_settings(tmp_path, mock_backend=False),
        transports={"ollama": httpx.MockTransport(FakeUpstream(mode))},
    )
    with TestClient(app) as c:
        r = c.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "x"}], "stream": stream},
        )
        assert r.status_code == status
        assert r.json()["error"]["code"] == "backend_error"
        assert c.get("/api/health").json()["status"] == "degraded"
