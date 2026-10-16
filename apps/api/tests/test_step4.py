"""Projects, settings, usage dashboard and server administration."""

import pytest
from fastapi.testclient import TestClient

from vortex_api.main import create_app

from .conftest import make_settings, parse_events

PASSWORD = "senha-forte-123"


def signup(client, email, name="X"):
    client.cookies.clear()
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["user"]


@pytest.fixture
def server(tmp_path):
    with TestClient(create_app(make_settings(tmp_path, local_mode=False))) as c:
        yield c


def chat(client, conv_id, text):
    r = client.post(f"/api/conversations/{conv_id}/chat", json={"content": text})
    assert r.status_code == 200, r.text
    return parse_events(r.text)


# ---------------------------------------------------------------- projects


def test_project_lifecycle(client):
    p = client.post(
        "/api/projects",
        json={
            "name": "Jogo UE5 - Rio de Janeiro",
            "instructions": "Use Unreal Engine 5.",
            "color": "pink",
        },
    ).json()
    assert p["conversation_count"] == 0

    conv = client.post("/api/conversations", json={"project_id": p["id"]}).json()
    assert conv["project_id"] == p["id"]
    chat(client, conv["id"], "oi")
    client.post("/api/conversations", json={})  # outside the project

    listed = client.get("/api/projects").json()["data"]
    assert [x["name"] for x in listed] == ["Jogo UE5 - Rio de Janeiro"]
    assert listed[0]["conversation_count"] == 1

    detail = client.get(f"/api/projects/{p['id']}").json()
    assert [c["id"] for c in detail["conversations"]] == [conv["id"]]
    only = client.get("/api/conversations", params={"project_id": p["id"]}).json()["data"]
    assert [c["id"] for c in only] == [conv["id"]]

    renamed = client.patch(f"/api/projects/{p['id']}", json={"name": "Jogo UE5"}).json()
    assert renamed["name"] == "Jogo UE5"

    # deleting a project keeps its conversations
    assert client.delete(f"/api/projects/{p['id']}").status_code == 204
    assert client.get(f"/api/conversations/{conv['id']}").json()["project_id"] is None


def test_project_validation_and_moving(client):
    assert client.post("/api/projects", json={"name": ""}).status_code == 422
    assert client.post("/api/projects", json={"name": "x", "color": "neon"}).status_code == 422
    assert client.post("/api/conversations", json={"project_id": "nope"}).status_code == 404

    p = client.post("/api/projects", json={"name": "P"}).json()
    conv = client.post("/api/conversations", json={}).json()
    moved = client.patch(f"/api/conversations/{conv['id']}", json={"project_id": p["id"]}).json()
    assert moved["project_id"] == p["id"]
    out = client.patch(f"/api/conversations/{conv['id']}", json={"project_id": ""}).json()
    assert out["project_id"] is None


def test_projects_are_private(server):
    signup(server, "ana@example.com")
    p = server.post("/api/projects", json={"name": "Segredo"}).json()
    signup(server, "bia@example.com")
    assert server.get("/api/projects").json()["data"] == []
    assert server.get(f"/api/projects/{p['id']}").status_code == 404
    assert server.post("/api/conversations", json={"project_id": p["id"]}).status_code == 404


def test_project_and_user_instructions_reach_the_model(tmp_path):
    seen = {}

    app = create_app(make_settings(tmp_path))
    with TestClient(app) as c:
        backend = app.state.gateway.backends["ollama"]
        original = backend.stream_chat

        def spy(payload):
            seen.update(payload)
            return original(payload)

        backend.stream_chat = spy
        c.patch(
            "/api/settings",
            json={
                "custom_instructions": "Me chame de Capitão.",
                "temperature": 0.2,
                "max_tokens": 300,
            },
        )
        p = c.post(
            "/api/projects", json={"name": "Marketing", "instructions": "Tom informal."}
        ).json()
        conv = c.post("/api/conversations", json={"project_id": p["id"]}).json()
        chat(c, conv["id"], "oi")

    system = seen["messages"][0]["content"]
    assert "Me chame de Capitão." in system
    assert 'projeto "Marketing"' in system and "Tom informal." in system
    assert seen["temperature"] == 0.2 and seen["max_tokens"] == 300


# ---------------------------------------------------------------- settings


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json()
    assert s["temperature"] is None and s["memory_enabled"] is True
    assert {t["id"] for t in s["tools"]} >= {"web_search", "image_generation", "code"}

    s = client.patch(
        "/api/settings",
        json={"default_model": "vortex-v0.2.1", "temperature": 0.5, "tools": {"web_search": False}},
    ).json()
    assert s["default_model"] == "vortex-v0.2.1" and s["temperature"] == 0.5
    assert next(t for t in s["tools"] if t["id"] == "web_search")["enabled"] is False

    s = client.patch("/api/settings", json={"temperature": None}).json()
    assert s["temperature"] is None and s["default_model"] == "vortex-v0.2.1"  # untouched

    assert client.patch("/api/settings", json={"temperature": 3}).status_code == 422
    assert client.patch("/api/settings", json={"default_model": "nope"}).status_code == 404
    assert client.patch("/api/settings", json={"default_model": "vortex-embed"}).status_code == 400
    assert client.patch("/api/settings", json={"tools": {"hack": True}}).status_code == 400


def test_export_and_delete_all(client):
    conv = client.post("/api/conversations", json={}).json()
    chat(client, conv["id"], "guarde isso")
    r = client.get("/api/settings/export")
    assert r.headers["content-disposition"].startswith("attachment")
    data = r.json()
    assert data["conversations"][0]["messages"][0]["content"] == "guarde isso"

    assert client.delete("/api/conversations").json() == {"deleted": 1}
    assert client.get("/api/conversations").json()["data"] == []


def test_profile_password_and_account_deletion(server):
    signup(server, "ana@example.com", "Ana")
    assert (
        server.patch("/api/auth/me", json={"name": "Ana Paula"}).json()["user"]["name"]
        == "Ana Paula"
    )

    bad = server.post(
        "/api/auth/password", json={"current_password": "errada", "new_password": "nova-senha-1"}
    )
    assert bad.status_code == 400
    ok = server.post(
        "/api/auth/password", json={"current_password": PASSWORD, "new_password": "nova-senha-1"}
    )
    assert ok.status_code == 204
    server.cookies.clear()
    login = server.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "nova-senha-1"}
    )
    assert login.status_code == 200

    server.post("/api/conversations", json={})
    assert server.request("DELETE", "/api/auth/me", json={"password": "errada"}).status_code == 400
    assert (
        server.request("DELETE", "/api/auth/me", json={"password": "nova-senha-1"}).status_code
        == 204
    )
    server.cookies.clear()
    gone = server.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "nova-senha-1"}
    )
    assert gone.status_code == 401


# ---------------------------------------------------------------- admin


def test_first_account_is_admin_and_controls_signups(server):
    admin = signup(server, "dono@example.com", "Dono")
    assert admin["is_admin"] is True
    assert server.get("/api/admin/server").json()["users"] == 1

    member = signup(server, "ana@example.com", "Ana")
    assert member["is_admin"] is False
    assert server.get("/api/admin/users").status_code == 403
    assert server.get("/api/usage", params={"scope": "server"}).status_code == 403

    server.cookies.clear()
    server.post("/api/auth/login", json={"email": "dono@example.com", "password": PASSWORD})
    users = server.get("/api/admin/users").json()["data"]
    assert [u["email"] for u in users] == ["dono@example.com", "ana@example.com"]

    assert server.patch("/api/admin/server", json={"allow_registration": False}).json() == {
        "allow_registration": False
    }
    server.cookies.clear()
    assert server.get("/api/auth/config").json()["allow_registration"] is False
    closed = server.post(
        "/api/auth/register", json={"email": "eve@example.com", "password": PASSWORD}
    )
    assert closed.status_code == 403


def test_admin_cannot_remove_last_admin_or_self(server):
    admin = signup(server, "dono@example.com")
    ana = signup(server, "ana@example.com")
    server.cookies.clear()
    server.post("/api/auth/login", json={"email": "dono@example.com", "password": PASSWORD})

    assert (
        server.patch(f"/api/admin/users/{admin['id']}", json={"is_admin": False}).status_code == 409
    )
    assert server.delete(f"/api/admin/users/{admin['id']}").status_code == 400
    # the only admin can't delete their own account while others depend on the server
    sole = server.request("DELETE", "/api/auth/me", json={"password": PASSWORD})
    assert sole.status_code == 409

    assert server.patch(f"/api/admin/users/{ana['id']}", json={"is_admin": True}).json()["is_admin"]
    assert server.delete(f"/api/admin/users/{ana['id']}").status_code == 204
    assert len(server.get("/api/admin/users").json()["data"]) == 1


# ---------------------------------------------------------------- usage


def test_usage_is_per_user_with_history(server):
    signup(server, "ana@example.com")
    conv = server.post("/api/conversations", json={}).json()
    chat(server, conv["id"], "oi")
    chat(server, conv["id"], "tudo bem?")
    mine = server.get("/api/usage").json()
    assert mine["requests"] == 2

    hist = server.get("/api/usage/history", params={"days": 7}).json()
    assert len(hist["days"]) == 7
    assert hist["days"][-1]["requests"] == 2
    assert hist["models"][0]["model"] == "vortex-v0.2.1"

    signup(server, "bia@example.com")
    assert server.get("/api/usage").json()["requests"] == 0


def test_system_stats(client):
    s = client.get("/api/system").json()
    assert s["cpu"]["cores"] >= 1
    assert 0 < s["memory"]["total_gb"]
    assert isinstance(s["gpus"], list)
