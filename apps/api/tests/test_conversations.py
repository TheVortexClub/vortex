from .conftest import parse_events


def new_conv(client, **body):
    r = client.post("/api/conversations", json=body)
    assert r.status_code == 201
    return r.json()


def send(client, conv_id, **body):
    r = client.post(f"/api/conversations/{conv_id}/chat", json=body)
    assert r.status_code == 200, r.text
    return parse_events(r.text)


def test_chat_streams_and_persists(client):
    conv = new_conv(client)
    events = send(client, conv["id"], content="Olá Vortex")
    names = [e for e, _ in events]
    assert names[0] == "meta" and names[-1] == "done"
    assert set(names[1:-1]) == {"delta"}

    meta = events[0][1]
    assert meta["user_message"]["content"] == "Olá Vortex"
    assert meta["completion_id"].startswith("chatcmpl-vx")
    assert meta["conversation"]["title"] == "Olá Vortex"  # first message names the chat

    text = "".join(d["content"] for e, d in events if e == "delta")
    done = events[-1][1]
    assert done["status"] == "ok"
    assert done["message"]["content"] == text
    assert "Você disse: Olá Vortex" in text

    saved = client.get(f"/api/conversations/{conv['id']}").json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["model"] == "vortex-v0.2.1"


def test_history_is_sent_to_the_model(client):
    conv = new_conv(client)
    send(client, conv["id"], content="primeira")
    events = send(client, conv["id"], content="segunda")
    assert "Você disse: segunda" in events[-1][1]["message"]["content"]
    msgs = client.get(f"/api/conversations/{conv['id']}").json()["messages"]
    assert [m["content"] for m in msgs if m["role"] == "user"] == ["primeira", "segunda"]


def test_regenerate_replaces_last_answer(client):
    conv = new_conv(client)
    first = send(client, conv["id"], content="oi")[-1][1]["message"]
    again = send(client, conv["id"], regenerate=True)
    assert again[0][1]["user_message"] is None
    msgs = client.get(f"/api/conversations/{conv['id']}").json()["messages"]
    assert len(msgs) == 2
    assert msgs[1]["id"] != first["id"]


def test_edit_truncates_and_resends(client):
    conv = new_conv(client)
    send(client, conv["id"], content="um")
    user_two = send(client, conv["id"], content="dois")[0][1]["user_message"]
    send(client, conv["id"], content="três")

    events = send(client, conv["id"], content="DOIS editado", edit_message_id=user_two["id"])
    assert events[0][1]["user_message"]["id"] == user_two["id"]
    msgs = client.get(f"/api/conversations/{conv['id']}").json()["messages"]
    assert [m["content"] for m in msgs if m["role"] == "user"] == ["um", "DOIS editado"]
    assert len(msgs) == 4


def test_mode_and_model_are_saved(client):
    conv = new_conv(client, mode="programar")
    assert conv["mode"] == "programar"
    events = send(client, conv["id"], content="x", model="vortex", mode="planejar", think=True)
    assert events[0][1]["conversation"]["mode"] == "planejar"
    assert events[0][1]["conversation"]["model"] == "vortex"
    assert events[0][1]["model"] == "vortex-v0.2.1"


def test_chat_validation(client):
    conv = new_conv(client)
    url = f"/api/conversations/{conv['id']}/chat"
    assert client.post(url, json={"content": "   "}).status_code == 400
    assert client.post(url, json={"regenerate": True}).status_code == 400
    assert client.post(url, json={"content": "x", "model": "nope"}).status_code == 404
    assert client.post("/api/conversations/nope/chat", json={"content": "x"}).status_code == 404
    assert client.post("/api/conversations", json={"mode": "hackear"}).status_code == 422


def test_list_search_pin_rename_delete(client):
    a = new_conv(client)
    send(client, a["id"], content="receita de pão de queijo")
    b = new_conv(client, title="Planejamento")

    def ids():
        return [c["id"] for c in client.get("/api/conversations").json()["data"]]

    assert ids() == [b["id"], a["id"]]  # most recent first
    client.patch(f"/api/conversations/{a['id']}", json={"pinned": True})
    assert ids() == [a["id"], b["id"]]  # pinned first

    found = client.get("/api/conversations", params={"q": "queijo"}).json()["data"]
    assert [c["id"] for c in found] == [a["id"]]
    assert client.get("/api/conversations", params={"q": "100%"}).json()["data"] == []

    r = client.patch(f"/api/conversations/{a['id']}", json={"title": "Pão de queijo"})
    assert r.json()["title"] == "Pão de queijo"

    assert client.delete(f"/api/conversations/{a['id']}").status_code == 204
    assert client.get(f"/api/conversations/{a['id']}").status_code == 404


def test_branch_feedback_export(client):
    conv = new_conv(client)
    send(client, conv["id"], content="um")
    answer = send(client, conv["id"], content="dois")[-1][1]["message"]
    first_answer = client.get(f"/api/conversations/{conv['id']}").json()["messages"][1]

    branch = client.post(
        f"/api/conversations/{conv['id']}/branch", json={"message_id": first_answer["id"]}
    ).json()
    branched = client.get(f"/api/conversations/{branch['id']}").json()["messages"]
    assert [m["content"] for m in branched if m["role"] == "user"] == ["um"]

    liked = client.patch(f"/api/messages/{answer['id']}", json={"feedback": 1}).json()
    assert liked["feedback"] == 1
    assert client.patch(f"/api/messages/{answer['id']}", json={"feedback": 5}).status_code == 422

    md = client.get(f"/api/conversations/{conv['id']}/export")
    assert md.headers["content-type"].startswith("text/markdown")
    assert "**Você:**" in md.text and "dois" in md.text


def test_cancel_saves_partial_answer(client):
    """Stop button: the cancel endpoint ends the stream and the partial answer is kept."""
    import asyncio
    import time as _time

    from vortex_api.backends.mock import MockBackend

    app = client.app
    backend = MockBackend(delay=0.01)
    app.state.gateway.backends["ollama"] = backend
    conv = new_conv(client)

    async def cancel_soon():
        for _ in range(200):
            await asyncio.sleep(0.01)
            active = list(app.state.generations._active)
            if active:
                await asyncio.sleep(0.05)
                app.state.generations.cancel(active[0])
                return

    client.portal.start_task_soon(cancel_soon)
    started = _time.perf_counter()
    events = send(client, conv["id"], content="palavra " * 200)
    assert _time.perf_counter() - started < 3
    done = events[-1][1]
    assert done["status"] == "cancelled"
    assert done["message"]["status"] == "cancelled"
    assert 0 < len(done["message"]["content"]) < len("palavra " * 200)
