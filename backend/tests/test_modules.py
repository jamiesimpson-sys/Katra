"""Module format tests: shipped modules, malformed files, drop-in modules and pinning."""

import re
import shutil
from pathlib import Path

import pytest
import yaml

from katra.config import get_settings
from katra.engine.modules import ModuleLoadError, ModuleRegistry, load_module
from katra.engine.modules.templates import render_output, sample_context

REPO = Path(__file__).resolve().parents[2]
MODULES_DIR = REPO / "modules"
SHIPPED = sorted(p for p in MODULES_DIR.iterdir() if p.suffix in {".yaml", ".yml", ".json"})


# --- Shipped modules ---------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_every_shipped_module_loads_and_renders(path):
    module = load_module(path)
    assert module.id == path.stem
    for section in module.sections:
        assert any(q.priority == "high" for q in section.questions), section.id
    for output in module.outputs:
        rendered = render_output(output, sample_context(module))
        for section in module.sections:
            assert section.name in rendered


def test_registry_loads_all_shipped_modules():
    registry = ModuleRegistry.from_directory(MODULES_DIR)
    assert {m.id for m in registry.all()} == {p.stem for p in SHIPPED}


def test_diligence_ready_question_bank():
    m = load_module(MODULES_DIR / "diligence_ready.yaml")
    assert [s.name for s in m.sections] == [
        "Customers", "Pricing", "Suppliers", "Staff",
        "Operations", "Financials", "Legal", "Risks",
    ]  # fmt: skip
    assert 40 <= len(m.questions()) <= 60
    assert m.session_length_minutes == 15
    assert m.coverage_rules.thresholds_for("legal").medium_priority_answered == 1.0
    assert m.coverage_rules.thresholds_for("customers").medium_priority_answered == 0.5


def test_no_module_or_question_ids_in_application_code():
    """Modules are data: application code must not special-case any module or question."""
    ids: set[str] = set()
    for path in SHIPPED:
        m = load_module(path)
        ids |= {m.id} | {s.id for s in m.sections} | {q.id for _, q in m.questions()}
    # Section ids like "legal" are ordinary words; only flag the distinctive ones.
    ids = {i for i in ids if "_" in i}
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, ids)) + r")\b")
    sources = [*(REPO / "backend/katra").rglob("*.py"), *(REPO / "frontend/src").rglob("*.ts*")]
    hits = [
        f"{p.relative_to(REPO)}: {m.group(0)}"
        for p in sources
        for m in pattern.finditer(p.read_text())
    ]
    assert not hits, hits


# --- Malformed modules -------------------------------------------------------------


def _base() -> dict:
    return yaml.safe_load((MODULES_DIR / "resignation.yaml").read_text())


def _write(tmp_path: Path, data, name: str = "resignation") -> Path:
    path = tmp_path / f"{name}.yaml"
    path.write_text(data if isinstance(data, str) else yaml.safe_dump(data))
    return path


def _mutate(fn):
    data = _base()
    fn(data)
    return data


MALFORMED = {
    "missing field": (_mutate(lambda d: d.pop("sections")), "sections: Field required"),
    "typo in key": (
        _mutate(lambda d: d["sections"][0]["questions"][0].update(priorty="high")),
        "sections.0.questions.0.priorty: Extra inputs are not permitted",
    ),
    "bad priority": (
        _mutate(lambda d: d["sections"][0]["questions"][0].update(priority="urgent")),
        "sections.0.questions.0.priority",
    ),
    "duplicate question id": (
        _mutate(lambda d: d["sections"][1]["questions"][0].update(id="resp_weekly")),
        "duplicate question id: resp_weekly",
    ),
    "duplicate section id": (
        _mutate(lambda d: d["sections"][1].update(id="responsibilities")),
        "duplicate section id: responsibilities",
    ),
    "undefined document type": (
        _mutate(lambda d: d["sections"][0]["questions"][0].update(related_document_types=["nda"])),
        "undefined document types ['nda']",
    ),
    "override for unknown section": (
        _mutate(lambda d: d.update(coverage_rules={"overrides": {"nope": {}}})),
        "unknown sections ['nope']",
    ),
    "unknown template placeholder": (
        _mutate(lambda d: d["outputs"][0].update(template="{{ project.title }}")),
        "outputs.handover_note.template",
    ),
    "template syntax error": (
        _mutate(lambda d: d["outputs"][0].update(template="{% for x in sections %}")),
        "outputs.handover_note.template",
    ),
    "empty sections": (_mutate(lambda d: d.update(sections=[])), "sections: List should have"),
    "bad id format": (_mutate(lambda d: d["sections"][0].update(id="Has Spaces")), "sections.0.id"),
    "invalid yaml": ("id: [unclosed", "not valid YAML"),
    "not a mapping": ("- just\n- a list\n", "expected a mapping"),
}


@pytest.mark.parametrize("case", MALFORMED.keys())
def test_malformed_module_fails_with_file_and_field(tmp_path, case):
    data, expected = MALFORMED[case]
    path = _write(tmp_path, data)
    with pytest.raises(ModuleLoadError) as exc:
        load_module(path)
    message = str(exc.value)
    assert "resignation.yaml" in message
    assert expected in message, message


def test_id_must_match_file_name(tmp_path):
    path = _write(tmp_path, _base(), name="other_name")
    with pytest.raises(ModuleLoadError, match="must match the file name"):
        load_module(path)


def test_registry_reports_every_bad_file(tmp_path):
    _write(tmp_path, "id: [", name="a_broken")
    _write(tmp_path, _mutate(lambda d: d.pop("outputs")), name="resignation")
    with pytest.raises(ModuleLoadError) as exc:
        ModuleRegistry.from_directory(tmp_path)
    assert {e.split(":")[0] for e in exc.value.errors} == {"a_broken.yaml", "resignation.yaml"}


def test_json_modules_are_supported(tmp_path):
    import json

    data = _mutate(lambda d: d.update(id="json_module"))
    (tmp_path / "json_module.json").write_text(json.dumps(data))
    assert ModuleRegistry.from_directory(tmp_path).get("json_module") is not None


# --- Drop-in modules and pinning, through the API ----------------------------------


@pytest.fixture
def modules_dir(tmp_path, monkeypatch):
    """A writable copy of the modules folder, used by the app for this test."""
    from katra.engine.modules import get_registry

    target = tmp_path / "modules"
    shutil.copytree(MODULES_DIR, target)
    monkeypatch.setenv("KATRA_MODULES_DIR", str(target))
    get_settings.cache_clear()
    get_registry.cache_clear()
    yield target
    get_settings.cache_clear()
    get_registry.cache_clear()


def _reload_registry():
    from katra.engine.modules import get_registry

    get_registry.cache_clear()


def test_new_module_is_usable_by_adding_a_file(modules_dir, world):
    data = _mutate(lambda d: d.update(id="exit_interview", name="Exit interview"))
    _write(modules_dir, data, name="exit_interview")
    _reload_registry()

    admin = world.clients["admin"]
    listed = {m["id"] for m in admin.get("/api/modules").json()}
    assert "exit_interview" in listed

    r = admin.post("/api/projects", json={"name": "Leaver", "module_id": "exit_interview"})
    assert r.status_code == 201
    module = admin.get(f"/api/projects/{r.json()['id']}/module").json()
    assert module["name"] == "Exit interview"
    assert [s["id"] for s in module["sections"]] == [s["id"] for s in _base()["sections"]]


def test_projects_keep_the_module_version_they_started_with(modules_dir, world):
    admin = world.clients["admin"]
    pid = admin.post("/api/projects", json={"name": "P", "module_id": "resignation"}).json()["id"]

    data = _mutate(lambda d: d.update(version=2, name="Handover v2"))
    data["sections"] = data["sections"][:1]
    _write(modules_dir, data)
    _reload_registry()

    pinned = admin.get(f"/api/projects/{pid}/module").json()
    assert pinned["version"] == 1 and len(pinned["sections"]) == 4
    new_pid = admin.post("/api/projects", json={"name": "Q", "module_id": "resignation"}).json()
    assert new_pid["module_version"] == 2


def test_unknown_module_is_rejected(world):
    r = world.clients["admin"].post("/api/projects", json={"name": "X", "module_id": "nope"})
    assert r.status_code == 422


def test_module_catalogue_is_staff_only(world):
    assert world.clients["admin"].get("/api/modules").status_code == 200
    assert world.clients["admin"].get("/api/modules/diligence_ready").status_code == 200
    assert world.clients["admin"].get("/api/modules/nope").status_code == 404
    assert world.clients["owner"].get("/api/modules").status_code == 403
    assert world.clients["anonymous"].get("/api/modules").status_code == 401


def test_pre_m2_projects_fall_back_to_the_module_file(world):
    """world's projects were created without a snapshot, like projects made before M2."""
    r = world.clients["owner"].get(f"/api/projects/{world.project_a.id}/module")
    assert r.status_code == 200
    assert r.json()["id"] == "diligence_ready"
