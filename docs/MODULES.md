# Writing a module

A module is one workflow, such as preparing a business for sale or a key-person handover,
described in a single YAML or JSON file in `modules/`. Adding a workflow means adding a
file. No code changes are needed.

The file name must match the module's `id`, so `exit_interview.yaml` must contain
`id: exit_interview`. Unknown keys are rejected, so typos fail loudly. Copy
[`modules/resignation.yaml`](../modules/resignation.yaml) as a starting point.

## Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | lowercase letters, digits and `_`; matches the file name |
| `version` | yes | integer ≥ 1; bump it when you change questions |
| `name`, `description` | name yes | shown in the module picker |
| `roles` | yes | labels for who is interviewed (e.g. `[owner]`) |
| `session_length_minutes` | yes | 5–120 |
| `target_sessions` | yes | how many sessions a full run should take |
| `document_types` | no | `{id, name}` labels for uploads; questions refer to them |
| `sections` | yes | each has `id`, `name`, optional `description`, and at least one question |
| `sections[].questions` | yes | `id`, `text`, `priority` (`high`/`medium`/`low`, default medium), `follow_up_hints`, `related_document_types` |
| `coverage_rules` | no | when a section counts as complete (below) |
| `outputs` | yes | report templates: `id`, `name`, `template` (Markdown + Jinja2) |

Question and section ids must be unique across the module. They identify answers, so
don't reuse an id for a different question.

## Coverage rules

A question counts as answered when it has at least one owner-approved answer. A section
is complete when the share of answered questions at each priority meets its threshold:

```yaml
coverage_rules:
  section_complete_when:
    high_priority_answered: 1.0    # default 1.0
    medium_priority_answered: 0.5  # default 0.5
    low_priority_answered: 0.0     # default 0.0
  overrides:
    legal: { medium_priority_answered: 1.0 }   # per-section changes; other values inherited
```

## Report templates

Templates are Markdown with Jinja2 tags, rendered in a sandbox. Only these placeholders
exist. Anything else is an error when the module loads.

| Placeholder | Contents |
|---|---|
| `project.name` | project name |
| `module.id`, `module.name`, `module.version` | this module |
| `generated_at` | timestamp |
| `coverage.percent`, `coverage.answered`, `coverage.total` | overall coverage |
| `sections[]` | `id`, `name`, `description`, `complete`, `narrative` (cited prose), `items[]`, `gaps[]`, `flags[]` |
| `sections[].items[]` | `ref`, `claim`, `quote`, `question`, `session_date`, `documents[]` |
| `sections[].gaps[]` / `gaps[]` | `question_id`, `text` (unanswered questions) |
| `sections[].flags[]` | `explanation` (unresolved contradictions) |
| `sources[]` | `ref`, `label` |

The report writer fills `narrative` only from verified answers, and gaps are computed from
the coverage rules (see `CLAUDE.md`). Templates control layout, not content.

## Trying a module

- **Locally:** save the file in `modules/` and run `docker compose restart api`. If the file
  is invalid, the API refuses to start and its log names the file and field.
- **Tests:** `make test-backend` checks every file in `modules/` (it loads, ids are unique,
  templates render, and every section has a high-priority question).
- **Existing projects keep the version they were created with.** Editing a module only
  affects new projects.
