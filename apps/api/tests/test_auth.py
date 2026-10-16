import pytest
from fastapi.testclient import TestClient

from vortex_api.main import create_app

from .conftest import make_settings

ALICE = {"email": "Alice@Example.com", "password": "senha-forte-1", "name": "Alice"}


@pytest.fixture
def server(tmp_path):
    """Multi-user server mode (accounts on), like the notebook serving everyone."""
    with TestClient(create_app(make_settings(tmp_path, local_mode=False))) as c:
        yield c


def test_local_mode_needs_no_login(client):
    me = client.get("/api/auth/me").json()
    assert me["local_mode"] is True
    assert me["user"]["email"] == "local@vortex.local"
    assert client.post("/api/auth/register", json=ALICE).status_code == 400


def test_server_mode_requires_login(server):
    assert server.get("/api/auth/me").status_code == 401
    assert server.get("/api/conversations").status_code == 401
    assert server.get("/v1/models").status_code == 401
    assert server.get("/api/auth/config").json() == {
        "local_mode": False,
        "allow_registration": True,
    }
    assert server.get("/health").status_code == 200


def test_register_login_logout(server):
    r = server.post("/api/auth/register", json=ALICE)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "alice@example.com"
    assert "vortex_session" in r.cookies
    assert server.get("/api/auth/me").json()["user"]["name"] == "Alice"

    assert server.post("/api/auth/logout").status_code == 204
    server.cookies.clear()
    assert server.get("/api/auth/me").status_code == 401

    bad = server.post("/api/auth/login", json={**ALICE, "password": "errada123"})
    assert bad.status_code == 401
    ok = server.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": ALICE["password"]}
    )
    assert ok.status_code == 200
    assert server.get("/api/auth/me").status_code == 200


def test_bearer_token_for_api_clients(server):
    token = server.post("/api/auth/register", json=ALICE).json()["access_token"]
    server.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}
    assert server.get("/v1/models", headers=headers).status_code == 200
    assert server.get("/v1/models", headers={"Authorization": "Bearer nope"}).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {**ALICE, "email": "not-an-email"},
        {**ALICE, "password": "curta"},
    ],
)
def test_registration_validation(server, body):
    assert server.post("/api/auth/register", json=body).status_code == 422


def test_duplicate_email(server):
    server.post("/api/auth/register", json=ALICE)
    assert server.post("/api/auth/register", json=ALICE).status_code == 409


def test_users_only_see_their_own_conversations(server):
    server.post("/api/auth/register", json=ALICE)
    conv = server.post("/api/conversations", json={"title": "Segredo da Alice"}).json()

    server.cookies.clear()
    server.post("/api/auth/register", json={**ALICE, "email": "bob@example.com"})
    assert server.get("/api/conversations").json()["data"] == []
    assert server.get(f"/api/conversations/{conv['id']}").status_code == 404
    assert server.delete(f"/api/conversations/{conv['id']}").status_code == 404


def test_registration_can_be_closed(tmp_path):
    settings = make_settings(tmp_path, local_mode=False, allow_registration=False)
    with TestClient(create_app(settings)) as c:
        # the first account is always allowed: it becomes the server admin
        first = c.post("/api/auth/register", json=ALICE)
        assert first.status_code == 201 and first.json()["user"]["is_admin"] is True
        c.cookies.clear()
        bob = {**ALICE, "email": "bob@example.com"}
        assert c.post("/api/auth/register", json=bob).status_code == 403


def test_secret_is_persisted(tmp_path):
    create_app(make_settings(tmp_path))
    secret = (tmp_path / ".secret_key").read_text()
    assert len(secret) > 40
    create_app(make_settings(tmp_path))
    assert (tmp_path / ".secret_key").read_text() == secret
