"""Rendering module output templates (Markdown + Jinja2, sandboxed).

Templates can only use the placeholders in `sample_context` below. Unknown placeholders
are errors (StrictUndefined), so a template typo is caught when the module loads.
"""

from typing import Any

from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

from katra.engine.modules.schema import Module, Output

_env = SandboxedEnvironment(
    undefined=StrictUndefined,
    autoescape=False,  # output is Markdown; it is escaped when rendered to HTML
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render_output(output: Output, context: dict[str, Any]) -> str:
    return _env.from_string(output.template).render(**context)


def sample_context(module: Module) -> dict[str, Any]:
    """The full set of placeholders a report template may use, filled with sample values."""
    sections = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "complete": False,
            "narrative": "Sample narrative citing an approved answer [K1].",
            "items": [
                {
                    "ref": "K1",
                    "claim": "Sample claim.",
                    "quote": "sample quote",
                    "question": s.questions[0].text,
                    "session_date": "2026-01-01",
                    "documents": ["contract.pdf p.2"],
                }
            ],
            "gaps": [{"question_id": s.questions[0].id, "text": s.questions[0].text}],
            "flags": [{"explanation": "Sample contradiction."}],
        }
        for s in module.sections
    ]
    return {
        "project": {"name": "Sample Co"},
        "module": {"id": module.id, "name": module.name, "version": module.version},
        "generated_at": "2026-01-01 12:00 UTC",
        "coverage": {"percent": 50, "answered": 1, "total": 2},
        "sections": sections,
        "gaps": [g for s in sections for g in s["gaps"]],
        "sources": [{"ref": "K1", "label": "Owner interview, 2026-01-01"}],
    }


def check_templates(module: Module) -> list[str]:
    """Render every output with the sample context. Returns error messages (empty if fine)."""
    errors = []
    ctx = sample_context(module)
    for output in module.outputs:
        try:
            render_output(output, ctx)
        except TemplateError as e:
            errors.append(f"outputs.{output.id}.template: {e}")
    return errors
