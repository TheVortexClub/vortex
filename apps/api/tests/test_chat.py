import pytest

from .conftest import parse_sse

HELLO = [{"role": "user", "content": "Olá"}]


def test_non_streaming_completion(client):
    r = client.post("/v1/chat/completions", json={"model": "vortex-v0.2.1", "messages": HELLO})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "vortex-v0.2.1"
    assert body["id"].startswith("chatcmpl-vx")
    assert "Você disse: Olá" in body["choices"][0]["message"]["content"]
    assert body["usage"]["total_tokens"] > 0


@pytest.mark.parametrize("model", [None, "vortex", "vortex-latest"])
def test_default_model_and_aliases(client, model):
    payload = {"messages": HELLO}
    if model:
        payload["model"] = model
    assert client.post("/v1/chat/completions", json=payload).json()["model"] == "vortex-v0.2.1"


def test_unknown_model(client):
    r = client.post("/v1/chat/completions", json={"model": "nope", "messages": HELLO})
    assert r.status_code == 404
    assert r.json()["error"]["param"] == "model"


def test_embedding_model_rejected_for_chat(client):
    r = client.post("/v1/chat/completions", json={"model": "vortex-embed", "messages": HELLO})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_model"


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": []},
        {"messages": [{"role": "robot", "content": "x"}]},
        {"messages": HELLO, "temperature": 5},
    ],
)
def test_validation(client, payload):
    assert client.post("/v1/chat/completions", json=payload).status_code == 422


def test_streaming_completion(client):
    r = client.post("/v1/chat/completions", json={"messages": HELLO, "stream": True})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    assert events[-1] == "[DONE]"
    chunks = events[:-1]
    completion_id = r.headers["x-vortex-completion-id"]
    assert all(c["id"] == completion_id and c["model"] == "vortex-v0.2.1" for c in chunks)
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert "Você disse: Olá" in text
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert not any("usage" in c for c in chunks), "usage only when include_usage is requested"


def test_streaming_include_usage(client):
    r = client.post(
        "/v1/chat/completions",
        json={"messages": HELLO, "stream": True, "stream_options": {"include_usage": True}},
    )
    usage_chunk = parse_sse(r.text)[-2]
    assert usage_chunk["choices"] == []
    assert usage_chunk["usage"]["completion_tokens"] > 0


def test_cancel_unknown_generation(client):
    r = client.post("/v1/chat/completions/chatcmpl-nope/cancel")
    assert r.status_code == 404


def test_embeddings(client):
    r = client.post("/v1/embeddings", json={"input": ["olá", "mundo"]})
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "vortex-embed"
    assert [d["index"] for d in body["data"]] == [0, 1]
    assert len(body["data"][0]["embedding"]) == 16


def test_chat_model_rejected_for_embeddings(client):
    r = client.post("/v1/embeddings", json={"model": "vortex-v0.2.1", "input": "x"})
    assert r.status_code == 400


def test_usage_is_recorded(client):
    client.post("/v1/chat/completions", json={"messages": HELLO})
    client.post("/v1/chat/completions", json={"messages": HELLO, "stream": True})
    usage = client.get("/api/usage").json()
    assert usage["requests"] == 2
    assert usage["completion_tokens"] > 0
    assert usage["plan"]["name"] == "Livre"
