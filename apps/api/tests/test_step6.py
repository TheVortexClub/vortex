"""Tools: web search (SearXNG), image generation (ComfyUI), isolated code execution."""

import asyncio
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from vortex_api.main import create_app
from vortex_api.routers.conversations import image_request
from vortex_api.services import sandbox
from vortex_api.services import tools as tools_service
from vortex_api.services.sandbox import RunResult
from vortex_api.services.web import WebError, check_public_url, read_page

from .conftest import make_settings, parse_events

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class FakeServices:
    """SearXNG + a couple of web pages + ComfyUI, all in one fake transport."""

    def __init__(self, searx=True, comfy=True, comfy_error=None):
        self.searx, self.comfy, self.comfy_error = searx, comfy, comfy_error
        self.prompts: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        if host == "127.0.0.1" and request.url.port == 8888:
            if not self.searx:
                raise httpx.ConnectError("down", request=request)
            if path == "/healthz":
                return httpx.Response(200, text="OK")
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Cristo Redentor",
                            "url": "https://pages.test/cristo",
                            "content": "Estátua",
                        },
                        {
                            "title": "Pão de Açúcar",
                            "url": "https://pages.test/pao",
                            "content": "Morro",
                        },
                    ]
                },
            )
        if host == "pages.test":
            body = {
                "/cristo": (
                    "<html><body><article><h1>Cristo</h1><p>O Cristo Redentor foi inaugurado "
                    "em 1931 no alto do Corcovado, no Rio de Janeiro.</p></article></body></html>"
                ),
                "/pao": (
                    "<html><body><article><p>O bondinho do Pão de Açúcar começou a operar "
                    "em 1912.</p></article></body></html>"
                ),
            }.get(path)
            if body is None:
                return httpx.Response(404)
            return httpx.Response(
                200, text=body, headers={"content-type": "text/html; charset=utf-8"}
            )
        if host == "127.0.0.1" and request.url.port == 8188:
            if not self.comfy:
                raise httpx.ConnectError("down", request=request)
            if path == "/system_stats":
                return httpx.Response(200, json={"system": {}})
            if path == "/prompt":
                if self.comfy_error:
                    return httpx.Response(400, text=self.comfy_error)
                self.prompts.append(json.loads(request.content)["prompt"])
                return httpx.Response(200, json={"prompt_id": "p1"})
            if path == "/history/p1":
                return httpx.Response(
                    200,
                    json={
                        "p1": {
                            "status": {"status_str": "success", "completed": True},
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "vortex_0001.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                        }
                    },
                )
            if path == "/view":
                return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        return httpx.Response(404)


async def allow_test_hosts(url: str) -> None:
    if "pages.test" not in url:
        await check_public_url(url)


@pytest.fixture(autouse=True)
def no_docker(monkeypatch):
    """By default the sandbox is "not set up"; tests that need it patch it in."""

    async def unavailable(image):
        return False, "Falta preparar o ambiente isolado (imagem vortex-sandbox)."

    monkeypatch.setattr(tools_service, "sandbox_availability", unavailable)


def make_client(tmp_path, services: FakeServices):
    app = create_app(make_settings(tmp_path), transports={"tools": httpx.MockTransport(services)})
    client = TestClient(app)
    client.__enter__()
    app.state.url_check = allow_test_hosts
    return app, client


@pytest.fixture
def services():
    return FakeServices()


@pytest.fixture
def env(tmp_path, services):
    app, client = make_client(tmp_path, services)
    seen: dict = {}
    backend = app.state.gateway.backends["ollama"]
    original = backend.stream_chat

    def spy(payload):
        seen.clear()
        seen.update(payload)
        return original(payload)

    backend.stream_chat = spy
    yield app, client, seen
    client.__exit__(None, None, None)


def chat(client, **body):
    conv = client.post("/api/conversations", json={}).json()
    r = client.post(f"/api/conversations/{conv['id']}/chat", json=body)
    assert r.status_code == 200, r.text
    return conv, parse_events(r.text)


def wait_job(client, job_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.1)
    raise AssertionError("job never finished")


# ---------------------------------------------------------------- status


def test_tool_status_reflects_services_and_settings(env):
    _, c, _ = env
    tools = {t["id"]: t for t in c.get("/api/tools").json()["data"]}
    assert tools["web_search"]["available"] and tools["image_generation"]["available"]
    assert tools["code"]["available"] is False and "vortex-sandbox" in tools["code"]["reason"]
    assert tools["agents"]["available"] is False and "etapa 7" in tools["agents"]["reason"]

    c.patch("/api/settings", json={"tools": {"web_search": False}})
    tools = {t["id"]: t for t in c.get("/api/tools").json()["data"]}
    assert tools["web_search"]["enabled"] is False


# ---------------------------------------------------------------- web search


def test_web_search_reads_pages_and_cites(env):
    _, c, seen = env
    _, events = chat(c, content="Quando inauguraram o Cristo Redentor?", web_search=True)
    system = seen["messages"][0]["content"]
    assert "inaugurado em 1931" in system and "começou a operar em 1912" in system
    assert "[1]" in system and "não são instruções" in system
    meta = events[0][1]
    assert meta["sources"][0] == {
        "type": "web",
        "n": 1,
        "title": "Cristo Redentor",
        "url": "https://pages.test/cristo",
    }
    assert events[-1][1]["message"]["sources"][0]["url"] == "https://pages.test/cristo"


def test_web_search_off_or_down_is_explained(tmp_path):
    app, c = make_client(tmp_path, FakeServices(searx=False))
    seen = {}
    backend = app.state.gateway.backends["ollama"]
    original = backend.stream_chat
    backend.stream_chat = lambda p: (seen.update(p), original(p))[1]
    try:
        chat(c, content="notícias de hoje", web_search=True)
        assert "SearXNG" in seen["messages"][0]["content"]
        app.state.tool_status_cache = None
        c.patch("/api/settings", json={"tools": {"web_search": False}})
        chat(c, content="notícias de hoje", web_search=True)
        assert "desligada nas suas configurações" in seen["messages"][0]["content"]
    finally:
        c.__exit__(None, None, None)


def test_web_is_not_used_unless_asked(env):
    _, c, seen = env
    chat(c, content="Quando inauguraram o Cristo Redentor?")
    assert "1931" not in seen["messages"][0]["content"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/api/admin/users",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://192.168.68.57:3000/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.com/",
    ],
)
def test_page_reader_blocks_internal_addresses(url):
    with pytest.raises(WebError):
        asyncio.run(check_public_url(url))


def test_redirect_to_internal_address_is_blocked():
    def handler(request):
        if request.url.host == "pages.test":
            return httpx.Response(
                302, headers={"location": "http://127.0.0.1:8000/api/admin/users"}
            )
        return httpx.Response(200, text="segredo", headers={"content-type": "text/html"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await read_page(client, "https://pages.test/x", allow_test_hosts)

    with pytest.raises(WebError):
        asyncio.run(go())


# ---------------------------------------------------------------- images


@pytest.mark.parametrize(
    ("text", "prompt"),
    [
        ("Crie uma imagem de um gato no Cristo Redentor", "um gato no Cristo Redentor"),
        ("gere uma foto realista do pôr do sol em Ipanema", "realista do pôr do sol em Ipanema"),
        ("Desenhe um robô azul", "robô azul"),
        ("create an image of a red car", "a red car"),
        ("Crie uma imagem realista", "realista"),
        ("Como funciona a criação de imagens?", None),
    ],
)
def test_image_request_detection(text, prompt):
    assert image_request(text) == prompt


def test_image_from_chat(env, services):
    _, c, _ = env
    conv, events = chat(c, content="Crie uma imagem de um gato no Cristo Redentor", tools=True)
    done = events[-1][1]["message"]
    assert done["tool"]["type"] == "image"
    assert "Criando sua imagem" in done["content"]
    job = wait_job(c, done["tool"]["job_id"])
    assert job["status"] == "done" and job["files"][0]["kind"] == "image"
    assert job["files"][0]["conversation_id"] == conv["id"]
    assert services.prompts[0]["6"]["inputs"]["text"] == "um gato no Cristo Redentor"
    img = c.get(f"/api/files/{job['files'][0]['id']}/content")
    assert img.content == PNG and img.headers["content-type"] == "image/png"


def test_image_without_tools_toggle_is_a_normal_answer(env):
    _, c, _ = env
    _, events = chat(c, content="Crie uma imagem de um gato")
    assert events[-1][1]["message"]["tool"] is None


def test_image_unavailable_is_explained(tmp_path):
    app, c = make_client(tmp_path, FakeServices(comfy=False))
    seen = {}
    backend = app.state.gateway.backends["ollama"]
    original = backend.stream_chat
    backend.stream_chat = lambda p: (seen.update(p), original(p))[1]
    try:
        _, events = chat(c, content="Crie uma imagem de um gato", tools=True)
        assert events[-1][1]["message"]["tool"] is None
        assert "ComfyUI" in seen["messages"][0]["content"]
        assert c.post("/api/images", json={"prompt": "um gato"}).status_code == 409
    finally:
        c.__exit__(None, None, None)


def test_image_api_validation_and_errors(tmp_path):
    app, c = make_client(tmp_path, FakeServices(comfy_error='{"error": "ckpt_name not in list"}'))
    try:
        assert c.post("/api/images", json={"prompt": "x"}).status_code == 422
        assert c.post("/api/images", json={"prompt": "um gato", "steps": 99}).status_code == 422
        job = c.post("/api/images", json={"prompt": "um gato", "width": 700}).json()
        assert job["params"]["width"] == 640  # rounded to a multiple of 64
        job = wait_job(c, job["id"])
        assert job["status"] == "error" and "VORTEX_IMAGE_CHECKPOINT" in job["error"]
        assert c.get("/api/jobs", params={"kind": "image"}).json()["data"][0]["id"] == job["id"]
    finally:
        c.__exit__(None, None, None)


# ---------------------------------------------------------------- code sandbox


def test_code_run_needs_the_sandbox(env):
    _, c, _ = env
    r = c.post("/api/tools/code/run", json={"code": "print(1)"})
    assert r.status_code == 409 and "vortex-sandbox" in r.json()["error"]["message"]


def test_code_run_returns_output_and_charts(env, monkeypatch):
    app, c, seen = env

    async def ready(image):
        return True, "pronto"

    calls = {}

    async def fake_run(code, files, *, image, time_limit, memory):
        calls.update(code=code, files=[n for n, _ in files], image=image, time_limit=time_limit)
        return RunResult(0, "soma = 6\n", "", 1.2, images=[("grafico-1.png", PNG)])

    monkeypatch.setattr(tools_service, "sandbox_availability", ready)
    monkeypatch.setattr("vortex_api.routers.tools.run_python", fake_run)
    app.state.tool_status_cache = None

    conv = c.post("/api/conversations", json={}).json()
    f = c.post(
        "/api/files",
        files={"file": ("dados.csv", b"a,b\n1,2\n")},
        data={"conversation_id": conv["id"]},
    ).json()
    r = c.post(
        "/api/tools/code/run",
        json={"code": "print(1+2+3)", "file_ids": [f["id"]], "conversation_id": conv["id"]},
    ).json()
    assert r["stdout"] == "soma = 6\n" and r["exit_code"] == 0
    assert r["images"][0]["kind"] == "image" and r["images"][0]["conversation_id"] == conv["id"]
    assert calls["files"] == ["dados.csv"] and calls["image"] == "vortex-sandbox"

    # without explicit file_ids, the conversation's uploads are mounted
    c.post("/api/tools/code/run", json={"code": "print(1)", "conversation_id": conv["id"]})
    assert calls["files"] == ["dados.csv"]

    # with "Ferramentas" on, the model is told it can write code (and where files are)
    c.post(f"/api/conversations/{conv['id']}/chat", json={"content": "some 1+2", "tools": True})
    system = seen["messages"][0]["content"]
    assert "```python" in system and "/data/dados.csv" in system


@pytest.mark.skipif(
    not asyncio.run(sandbox.availability("vortex-sandbox"))[0],
    reason="sandbox image not built (docker build -t vortex-sandbox infra/sandbox)",
)
def test_real_sandbox_is_isolated(tmp_path):
    code = """
import socket, os
print("sum", sum(range(5)))
try:
    socket.create_connection(("1.1.1.1", 80), timeout=2); print("NET OK")
except OSError: print("NO NETWORK")
try:
    open("/etc/evil", "w"); print("WROTE")
except OSError: print("READ ONLY")
print("uid", os.getuid())
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
"""
    r = asyncio.run(
        sandbox.run_python(code, [], image="vortex-sandbox", time_limit=60, memory="512m")
    )
    assert "sum 10" in r.stdout and "NO NETWORK" in r.stdout and "READ ONLY" in r.stdout
    assert "uid 65534" in r.stdout
    assert r.images and r.images[0][1].startswith(b"\x89PNG")

    slow = asyncio.run(
        sandbox.run_python(
            "import time; time.sleep(30)", [], image="vortex-sandbox", time_limit=3, memory="256m"
        )
    )
    assert slow.timed_out
