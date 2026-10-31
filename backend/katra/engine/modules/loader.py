"""Loads every *.yaml / *.json file in the modules directory into a registry.

Adding a workflow means adding a file; no code changes. Any invalid module stops startup
with an error naming the file and the field.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from katra.config import get_settings
from katra.engine.modules.schema import Module
from katra.engine.modules.templates import check_templates

MODULE_SUFFIXES = {".yaml", ".yml", ".json"}


class ModuleLoadError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("Invalid module file(s):\n  " + "\n  ".join(errors))


def _format_validation_error(path: Path, err: ValidationError) -> list[str]:
    out = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"]) or "(top level)"
        out.append(f"{path.name}: {loc}: {e['msg']}")
    return out


def _parse(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)


def load_module(path: Path) -> Module:
    try:
        data = _parse(path)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ModuleLoadError([f"{path.name}: not valid {path.suffix[1:].upper()}: {e}"]) from e
    if not isinstance(data, dict):
        raise ModuleLoadError([f"{path.name}: expected a mapping at the top level"])
    try:
        module = Module.model_validate(data)
    except ValidationError as e:
        raise ModuleLoadError(_format_validation_error(path, e)) from e
    errors = [f"{path.name}: {msg}" for msg in check_templates(module)]
    if module.id != path.stem:
        errors.append(f"{path.name}: id {module.id!r} must match the file name {path.stem!r}")
    if errors:
        raise ModuleLoadError(errors)
    return module


class ModuleRegistry:
    def __init__(self, modules: dict[str, Module]) -> None:
        self._modules = modules

    @classmethod
    def from_directory(cls, directory: Path) -> "ModuleRegistry":
        if not directory.is_dir():
            raise ModuleLoadError([f"modules directory not found: {directory}"])
        modules: dict[str, Module] = {}
        errors: list[str] = []
        for path in sorted(directory.iterdir()):
            if path.suffix not in MODULE_SUFFIXES or path.name.startswith("."):
                continue
            try:
                module = load_module(path)
            except ModuleLoadError as e:
                errors.extend(e.errors)
                continue
            modules[module.id] = module
        if errors:
            raise ModuleLoadError(errors)
        return cls(modules)

    def get(self, module_id: str) -> Module | None:
        return self._modules.get(module_id)

    def all(self) -> list[Module]:
        return sorted(self._modules.values(), key=lambda m: m.name)


@lru_cache
def get_registry() -> ModuleRegistry:
    return ModuleRegistry.from_directory(Path(get_settings().modules_dir))
