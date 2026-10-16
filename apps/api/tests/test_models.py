def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "version": "0.2.1"}


def test_api_health_reports_backends(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["local_mode"] is True
    assert body["backends"]["ollama"]["ok"] is True


def test_list_models_openai_shape(client):
    body = client.get("/v1/models").json()
    assert body["object"] == "list"
    ids = {m["id"] for m in body["data"]}
    assert {"vortex-v0.2.1", "vortex-embed"} <= ids
    model = next(m for m in body["data"] if m["id"] == "vortex-v0.2.1")
    assert model == {
        "id": "vortex-v0.2.1",
        "object": "model",
        "created": model["created"],
        "owned_by": "vortex",
    }
    assert model["created"] > 0


def test_get_model(client):
    assert client.get("/v1/models/vortex-v0.2.1").json()["id"] == "vortex-v0.2.1"


def test_get_unknown_model_is_openai_error(client):
    r = client.get("/v1/models/gpt-4")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "model_not_found"


def test_api_models_has_ui_metadata(client):
    data = client.get("/api/models").json()["data"]
    vortex = next(m for m in data if m["id"] == "vortex-v0.2.1")
    assert vortex["display_name"] == "Vortex v0.2.1"
    assert vortex["badge"] == "PRÓPRIO"
    assert vortex["description"] == "Nosso modelo exclusivo. Rápido, inteligente e versátil."
    assert vortex["default"] is True
