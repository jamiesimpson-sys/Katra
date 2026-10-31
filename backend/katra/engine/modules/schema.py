"""The module format: a workflow (sections, questions, coverage rules, report templates) as data.

See docs/MODULES.md for the authoring guide. Unknown keys are rejected so typos fail loudly.
"""

import enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG = r"^[a-z][a-z0-9_]*$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Priority(enum.StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Question(Strict):
    id: str = Field(pattern=SLUG, max_length=100)
    text: str = Field(min_length=1)
    follow_up_hints: list[str] = []
    related_document_types: list[str] = []
    priority: Priority = Priority.MEDIUM


class Section(Strict):
    id: str = Field(pattern=SLUG, max_length=100)
    name: str = Field(min_length=1)
    description: str = ""
    questions: list[Question] = Field(min_length=1)


class DocumentType(Strict):
    id: str = Field(pattern=SLUG, max_length=100)
    name: str = Field(min_length=1)


class CoverageThresholds(Strict):
    """Share of questions at each priority that must be answered for a section to be complete."""

    high_priority_answered: float = Field(default=1.0, ge=0.0, le=1.0)
    medium_priority_answered: float = Field(default=0.5, ge=0.0, le=1.0)
    low_priority_answered: float = Field(default=0.0, ge=0.0, le=1.0)


class CoverageOverride(Strict):
    high_priority_answered: float | None = Field(default=None, ge=0.0, le=1.0)
    medium_priority_answered: float | None = Field(default=None, ge=0.0, le=1.0)
    low_priority_answered: float | None = Field(default=None, ge=0.0, le=1.0)


class CoverageRules(Strict):
    # Only verified (owner-approved) answers count. Other rules can be added later.
    question_answered_when: Literal["approved_item"] = "approved_item"
    section_complete_when: CoverageThresholds = CoverageThresholds()
    overrides: dict[str, CoverageOverride] = {}

    def thresholds_for(self, section_id: str) -> CoverageThresholds:
        override = self.overrides.get(section_id)
        if override is None:
            return self.section_complete_when
        return self.section_complete_when.model_copy(update=override.model_dump(exclude_none=True))


class Output(Strict):
    id: str = Field(pattern=SLUG, max_length=100)
    name: str = Field(min_length=1)
    format: Literal["markdown"] = "markdown"
    template: str = Field(min_length=1)


class Module(Strict):
    id: str = Field(pattern=SLUG, max_length=100)
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    description: str = ""
    # Who gets interviewed (labels shown in the UI; the app role is always "owner").
    roles: list[str] = Field(min_length=1)
    session_length_minutes: int = Field(ge=5, le=120)
    target_sessions: int = Field(ge=1, le=50)
    sections: list[Section] = Field(min_length=1)
    document_types: list[DocumentType] = []
    coverage_rules: CoverageRules = CoverageRules()
    outputs: list[Output] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_references(self) -> "Module":
        _require_unique("section id", [s.id for s in self.sections])
        _require_unique("question id", [q.id for s in self.sections for q in s.questions])
        _require_unique("document type id", [d.id for d in self.document_types])
        _require_unique("output id", [o.id for o in self.outputs])

        doc_types = {d.id for d in self.document_types}
        for section in self.sections:
            for q in section.questions:
                unknown = set(q.related_document_types) - doc_types
                if unknown:
                    raise ValueError(
                        f"question {q.id!r} refers to undefined document types "
                        f"{sorted(unknown)}; add them to document_types"
                    )
        unknown_sections = set(self.coverage_rules.overrides) - {s.id for s in self.sections}
        if unknown_sections:
            raise ValueError(
                f"coverage_rules.overrides refers to unknown sections {sorted(unknown_sections)}"
            )
        return self

    # Convenience lookups -------------------------------------------------------------

    def questions(self) -> list[tuple[Section, Question]]:
        return [(s, q) for s in self.sections for q in s.questions]

    def question(self, question_id: str) -> Question | None:
        return next((q for _, q in self.questions() if q.id == question_id), None)

    def section(self, section_id: str) -> Section | None:
        return next((s for s in self.sections if s.id == section_id), None)

    def output(self, output_id: str) -> Output | None:
        return next((o for o in self.outputs if o.id == output_id), None)


def _require_unique(what: str, values: list[str]) -> None:
    dupes = sorted({v for v in values if values.count(v) > 1})
    if dupes:
        raise ValueError(f"duplicate {what}: {', '.join(dupes)}")
