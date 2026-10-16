"""Model registry: maps public Vortex model ids to backends and upstream models.

Loaded from models/registry.yaml. Adding a model version is a config change only.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal

import yaml

from .errors import VortexError

ModelKind = Literal["chat", "embedding"]

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class RegistryError(Exception):
    pass


def expand_env(value: Any) -> Any:
    """Expand ${VAR} and ${VAR:-default} recursively. Unset or empty VAR uses the default."""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value


@dataclass
class BackendSpec:
    name: str
    type: str
    base_url: str = ""
    api_key: str = ""
    timeout: float | None = None
    # native backend: folder containing the `vortex` package, its checkpoints, and torch device
    path: str = ""
    checkpoint_dir: str = ""
    device: str = ""


@dataclass
class ModelSpec:
    id: str
    kind: ModelKind
    backend: str
    upstream_model: str
    display_name: str
    version: str = ""
    badge: str | None = None
    description: str = ""
    aliases: tuple[str, ...] = ()
    system_prompt: str | None = None
    context_window: int | None = None
    dimensions: int | None = None
    capabilities: tuple[str, ...] = ()
    defaults: dict[str, Any] = field(default_factory=dict)
    hidden: bool = False
    created: int = 0


def _to_timestamp(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = dt.date.fromisoformat(value)
    if isinstance(value, dt.date):
        return int(dt.datetime(value.year, value.month, value.day, tzinfo=dt.UTC).timestamp())
    raise RegistryError(f"Invalid 'released' value: {value!r}")


def _build(cls: type, data: dict[str, Any], what: str) -> Any:
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise RegistryError(f"{what}: unknown keys {sorted(unknown)}")
    try:
        return cls(**data)
    except TypeError as e:
        raise RegistryError(f"{what}: {e}") from e


class Registry:
    def __init__(
        self,
        backends: dict[str, BackendSpec],
        models: dict[str, ModelSpec],
        default_chat: str | None,
        default_embedding: str | None,
    ) -> None:
        self.backends = backends
        self.models = models
        self.defaults: dict[str, str | None] = {
            "chat": default_chat,
            "embedding": default_embedding,
        }
        self._aliases: dict[str, str] = {}
        for spec in models.values():
            for alias in spec.aliases:
                if alias in models or alias in self._aliases:
                    raise RegistryError(f"Alias '{alias}' is already used")
                self._aliases[alias] = spec.id
        for kind, model_id in self.defaults.items():
            if model_id and model_id not in models:
                raise RegistryError(f"default_{kind} '{model_id}' is not a registered model")

    @classmethod
    def load(cls, path: Path) -> Registry:
        if not path.exists():
            raise RegistryError(f"Registry file not found: {path}")
        raw = expand_env(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        base_dir = path.parent

        backends = {
            name: _build(BackendSpec, {"name": name, **(cfg or {})}, f"backend '{name}'")
            for name, cfg in (raw.get("backends") or {}).items()
        }
        for backend in backends.values():  # relative paths are relative to the registry file
            for attr in ("path", "checkpoint_dir"):
                value = getattr(backend, attr)
                if value and not Path(value).is_absolute():
                    setattr(backend, attr, str((base_dir / value).resolve()))

        models: dict[str, ModelSpec] = {}
        for entry in raw.get("models") or []:
            data = dict(entry)
            model_id = data.get("id", "<missing id>")
            prompt_file = data.pop("system_prompt_file", None)
            if prompt_file:
                prompt_path = base_dir / prompt_file
                if not prompt_path.exists():
                    raise RegistryError(f"model '{model_id}': prompt file not found: {prompt_path}")
                data["system_prompt"] = prompt_path.read_text(encoding="utf-8").strip()
            data["created"] = _to_timestamp(data.pop("released", None))
            data["aliases"] = tuple(data.get("aliases") or ())
            data["capabilities"] = tuple(data.get("capabilities") or ())
            spec = _build(ModelSpec, data, f"model '{model_id}'")
            if spec.kind not in ("chat", "embedding"):
                raise RegistryError(f"model '{spec.id}': kind must be 'chat' or 'embedding'")
            if spec.backend not in backends:
                raise RegistryError(f"model '{spec.id}': unknown backend '{spec.backend}'")
            if spec.id in models:
                raise RegistryError(f"Duplicate model id '{spec.id}'")
            models[spec.id] = spec

        return cls(backends, models, raw.get("default_chat"), raw.get("default_embedding"))

    def list(self, kind: ModelKind | None = None, include_hidden: bool = False) -> list[ModelSpec]:
        return [
            m
            for m in self.models.values()
            if (kind is None or m.kind == kind) and (include_hidden or not m.hidden)
        ]

    def resolve(self, name: str | None, kind: ModelKind) -> ModelSpec:
        """Find a model by id or alias; None means the default model for that kind."""
        model_id = name or self.defaults.get(kind)
        if not model_id:
            raise VortexError(400, f"No default {kind} model configured", code="model_not_found")
        model_id = self._aliases.get(model_id, model_id)
        spec = self.models.get(model_id)
        if spec is None:
            raise VortexError(
                404, f"The model '{name}' does not exist", code="model_not_found", param="model"
            )
        if spec.kind != kind:
            raise VortexError(
                400,
                f"The model '{spec.id}' is a {spec.kind} model and cannot be used for {kind}",
                code="invalid_model",
                param="model",
            )
        return spec

    def used_backends(self) -> set[str]:
        return {m.backend for m in self.models.values()}
