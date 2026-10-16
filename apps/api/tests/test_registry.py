import pytest

from vortex_api.errors import VortexError
from vortex_api.registry import Registry, RegistryError, expand_env

from .conftest import REGISTRY


def test_expand_env(monkeypatch):
    monkeypatch.setenv("VX_SET", "value")
    monkeypatch.setenv("VX_EMPTY", "")
    monkeypatch.delenv("VX_UNSET", raising=False)
    assert expand_env("${VX_SET:-d}") == "value"
    assert expand_env("${VX_EMPTY:-d}") == "d"
    assert expand_env("${VX_UNSET:-d}") == "d"
    assert expand_env("${VX_UNSET}") == ""
    assert expand_env({"a": ["x-${VX_SET}"]}) == {"a": ["x-value"]}


def test_env_overrides_upstream_model(monkeypatch):
    monkeypatch.setenv("VORTEX_CHAT_MODEL", "llama3.1:8b")
    assert Registry.load(REGISTRY).models["vortex-v0.2.1"].upstream_model == "llama3.1:8b"


def test_real_registry_loads_prompt():
    registry = Registry.load(REGISTRY)
    spec = registry.resolve(None, "chat")
    assert spec.id == "vortex-v0.2.1"
    assert "Vortex" in spec.system_prompt
    assert registry.resolve("vortex", "chat") is spec
    with pytest.raises(VortexError):
        registry.resolve("nope", "chat")


def _write(tmp_path, body: str):
    path = tmp_path / "registry.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_new_version_by_config_only(tmp_path):
    path = _write(
        tmp_path,
        """
default_chat: vortex-v0.3
backends:
  local: {type: openai_compat, base_url: http://x/v1}
models:
  - {id: vortex-v0.3, kind: chat, backend: local, upstream_model: ft, display_name: New}
  - {id: vortex-v0.2.1, kind: chat, backend: local, upstream_model: base, display_name: Old,
     hidden: true}
""",
    )
    registry = Registry.load(path)
    assert registry.resolve(None, "chat").id == "vortex-v0.3"
    assert [m.id for m in registry.list()] == ["vortex-v0.3"]
    assert registry.resolve("vortex-v0.2.1", "chat").hidden


@pytest.mark.parametrize(
    "models",
    [
        "- {id: a, kind: chat, backend: missing, upstream_model: u, display_name: A}",
        "- {id: a, kind: chat, backend: b, upstream_model: u, display_name: A, typo: 1}",
        "- {id: a, kind: image, backend: b, upstream_model: u, display_name: A}",
        "- {id: a, kind: chat, backend: b, upstream_model: u, display_name: A, "
        "system_prompt_file: nope.md}",
    ],
)
def test_invalid_registry(tmp_path, models):
    path = _write(tmp_path, f"backends:\n  b: {{type: openai_compat}}\nmodels:\n  {models}\n")
    with pytest.raises(RegistryError):
        Registry.load(path)
