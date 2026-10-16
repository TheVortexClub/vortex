"""The native backend that serves the from-scratch GPT, with a fake engine (no torch needed)."""

import time

import pytest

from vortex_api.backends.native import NativeBackend, to_history
from vortex_api.errors import BackendError
from vortex_api.registry import BackendSpec, Registry

from .conftest import REGISTRY, REPO_ROOT


class FakeEngine:
    def __init__(self):
        self.calls = []

    def stream(self, history, **kwargs):
        self.calls.append((history, kwargs))
        for piece in "Oi, eu sou o Vortex!":
            time.sleep(0.001)
            yield piece


def backend(engine=None, tmp="."):
    spec = BackendSpec(name="native", type="native", checkpoint_dir=str(tmp))
    return NativeBackend(spec, engine_factory=(lambda: engine) if engine else None)


def test_to_history_maps_roles_and_drops_system():
    msgs = [
        {"role": "system", "content": "ignored"},
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": "olá"},
        {"role": "user", "content": [{"type": "text", "text": "tudo bem?"}]},
    ]
    assert to_history(msgs) == [("user", "oi"), ("bot", "olá"), ("user", "tudo bem?")]


async def test_stream_and_generation_params():
    engine = FakeEngine()
    payload = {
        "model": "vortex-gpt",
        "messages": [{"role": "user", "content": "oi"}],
        "max_tokens": 50,
        "temperature": 0.3,
        "stream_options": {"include_usage": True},
    }
    chunks = [c async for c in backend(engine).stream_chat(payload)]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"])
    assert text == "Oi, eu sou o Vortex!"
    assert chunks[-1]["usage"]["completion_tokens"] == len(text)
    assert engine.calls[0] == ([("user", "oi")], {"max_new_tokens": 50, "temperature": 0.3})


async def test_non_streaming_chat():
    result = await backend(FakeEngine()).chat(
        {"model": "vortex-gpt", "messages": [{"role": "user", "content": "oi"}]}
    )
    assert result["choices"][0]["message"]["content"] == "Oi, eu sou o Vortex!"


async def test_requires_user_message_last():
    with pytest.raises(BackendError) as e:
        await backend(FakeEngine()).chat(
            {"model": "x", "messages": [{"role": "system", "content": "s"}]}
        )
    assert e.value.status_code == 400


async def test_untrained_model_is_clear_error(tmp_path):
    b = backend(tmp=tmp_path)
    assert (await b.health())["ok"] is False
    with pytest.raises(BackendError) as e:
        await b.chat({"model": "x", "messages": [{"role": "user", "content": "oi"}]})
    assert e.value.status_code == 503
    assert "train.py" in e.value.message


def test_registry_points_native_backend_at_repo():
    spec = Registry.load(REGISTRY).backends["native"]
    assert spec.path == str(REPO_ROOT.resolve())
    assert spec.checkpoint_dir == str((REPO_ROOT / "checkpoints").resolve())


def test_native_model_has_no_injected_system_prompt():
    model = Registry.load(REGISTRY).resolve("vortex-native", "chat")
    assert model.backend == "native"
    assert model.system_prompt is None
    assert model.badge == "PRÓPRIO"
