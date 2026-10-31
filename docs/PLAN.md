# Katra Prototype — Architecture & Development Plan

Status: **approved** (decisions recorded in §10). M1 complete; see `docs/milestones/`.
Source brief: [`docs/SPEC.md`](./SPEC.md)

This document proposes the architecture, key design decisions, data model and a
milestone-by-milestone build plan for the Diligence-ready prototype. Each
milestone ends with something runnable, a set of tests, and a review point.

---

## 1. Guiding principles

1. **Never fabricate on the owner's behalf.** Every claim that reaches a report
   or a Q&A answer must trace to an exact owner quote and an owner approval.
   This is enforced in *code* (validators that reject unsupported output), not
   only in prompts.
2. **Deterministic orchestration, LLM for language.** Code decides *what*
   happens (which question is next, what counts as covered, which items go in a
   report, what the gaps are). The LLM decides *how to say it* and does
   extraction/judgement inside a narrow structured contract.
3. **Modules are data.** Everything workflow-specific (sections, questions,
   coverage rules, report templates) lives in a module file. No module ids
   appear in application code.
4. **Everything behind an interface:** LLM, embeddings, file storage, document
   parsers. This keeps the private-cloud / on-prem path open for Phase 2.
5. **Demo-reliable.** A fake LLM provider and seeded demo data let the whole
   flow run offline and deterministically, for tests and for broker demos.

---

## 2. Proposed stack

| Concern | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | As suggested; strong typing for module schema and LLM structured output |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Standard, works well with pgvector |
| Database | PostgreSQL 16 + `pgvector` | One store for relational data and vectors |
| Background jobs | Postgres-backed job table + a `worker` process (same image) | Ingestion, extraction, contradiction checks and reports run async without adding Redis/Celery |
| Frontend | React + TypeScript (Vite SPA), TanStack Query, Tailwind | Backend owns all logic and auth, so SSR adds nothing; simpler than Next.js. Easy to swap later |
| LLM | `LLMProvider` interface; `AnthropicProvider` default, `FakeProvider` for tests/offline | Model per task set by env var (fast model for interviewing, stronger model for extraction/reports) |
| Embeddings | `EmbeddingProvider` interface; default local model via `fastembed` (ONNX, e.g. `bge-small-en`, 384-d) | Claude has no embeddings endpoint; a local model keeps document text in-container and supports the on-prem story. Voyage AI is a drop-in alternative |
| Document parsing | `pypdf` (PDF), `python-docx` (DOCX), stdlib `csv`, plain text | Standard, pure-Python. Scanned PDFs (OCR) are out of scope |
| Report export | Jinja2 Markdown templates → HTML (`markdown-it-py`) → PDF (WeasyPrint) | Templates stay in modules; PDF needs no headless browser |
| Edge / TLS | Caddy reverse proxy with its internal CA | HTTPS locally with no config; one origin for SPA and API |
| Packaging | Docker Compose: `caddy`, `web`, `api`, `worker`, `db` | `docker compose up` starts everything |
| Tests | pytest (+ a real Postgres via Compose), Vitest for the frontend, Playwright for one end-to-end smoke test | |

---

## 3. System architecture

```
 Browser (Owner / Admin / Viewer)
        │  HTTPS
        ▼
 ┌──────────────┐   /        ┌──────────────────────────┐
 │    Caddy     ├──────────► │  web  (React SPA, static)│
 │  (TLS, proxy)│            └──────────────────────────┘
 │              │   /api     ┌──────────────────────────────────────────────┐
 │              ├──────────► │  api  (FastAPI)                               │
 └──────────────┘            │  ├─ auth & RBAC deps  (every project route)   │
                             │  ├─ routers: projects, documents, interviews, │
                             │  │   knowledge, coverage, reports, qa, audit  │
                             │  ├─ services (domain logic)                   │
                             │  └─ core engine ───────────────┐             │
                             └────────────┬───────────────────┼─────────────┘
                                          │ enqueue jobs      │
                             ┌────────────▼───────────┐       │
                             │ worker (same codebase) │       │
                             │  ingest · extract ·    │       │
                             │  contradictions ·      │       │
                             │  report · retention    │       │
                             └────────────┬───────────┘       │
                                          │                   │
          ┌───────────────────────────────┼───────────────────┼───────────┐
          │ Interfaces                    │                   │           │
          │  LLMProvider ──► Anthropic API (or Fake / local later)        │
          │  EmbeddingProvider ──► local fastembed (or Voyage)            │
          │  BlobStorage ──► encrypted local volume (or S3/MinIO later)   │
          │  ModuleRegistry ──► /modules/*.yaml                           │
          └───────────────────────────────┬───────────────────────────────┘
                                          ▼
                             PostgreSQL 16 + pgvector
```

### Backend layout

```
backend/
  katra/
    main.py                 # FastAPI app factory
    config.py               # pydantic-settings; all secrets from env
    db/                     # engine, session, base, alembic migrations
    models/                 # SQLAlchemy models
    schemas/                # Pydantic request/response models
    auth/                   # password hashing, sessions, invites, RBAC deps
    api/                    # routers (thin; call services)
    services/               # projects, documents, interviews, knowledge, reports, qa, audit, retention
    engine/                 # the shared core engine (module-agnostic)
      modules/              # module schema + loader + registry
      interview/            # planner (deterministic) + interviewer agent
      extraction/           # extractor + quote validator
      contradictions/
      reporting/            # assembler, writer, citation validator, exporters
      qa/                   # retriever, answerer, citation validator
      retrieval.py          # shared vector search, always project-scoped
    providers/
      llm/                  # base.py, anthropic.py, fake.py
      embeddings/           # base.py, fastembed.py, fake.py
      storage/              # base.py, encrypted_local.py
      parsers/              # pdf, docx, txt, csv
    jobs/                   # job queue + worker entrypoint + handlers
    prompts/                # versioned prompt templates (text files)
  tests/
modules/
  diligence_ready.yaml
  resignation.yaml
frontend/
  src/ (pages: admin, owner, viewer; components; api client)
seed/
  demo_company/ (documents, scripted interview, seed script)
docker-compose.yml
Caddyfile
CLAUDE.md
```

---

## 4. Module format

Modules are YAML files in `modules/`, validated on startup against a Pydantic
schema (a malformed module fails loudly, with the file and field in the error).
Projects store `module_id` **and** `module_version`, so editing a module never
silently changes an in-flight project.

```yaml
id: diligence_ready
version: 1
name: Diligence-ready
description: Prepare an owner-operated business for sale and buyer diligence.
roles: [owner]                      # who gets interviewed
session_length_minutes: 15
target_sessions: 6

sections:
  - id: customers
    name: Customers
    description: Concentration, contracts, churn and relationships.
    questions:
      - id: cust_top10
        text: Who are your ten largest customers, and what share of revenue does each represent?
        follow_up_hints:
          - Ask whether any single customer is above 15% of revenue.
          - Ask how long each relationship has lasted.
        related_document_types: [customer_list, financials]
        priority: high                # high | medium | low
      # ...

coverage_rules:
  question_answered_when: approved_item   # at least one approved knowledge item
  section_complete_when:
    high_priority_answered: 1.0           # share of high-priority questions answered
    medium_priority_answered: 0.5
  # optional per-section overrides
  overrides:
    legal: { high_priority_answered: 1.0, medium_priority_answered: 1.0 }

document_types:                    # labels the owner can tag uploads with
  - { id: financials, name: Financial statements }
  - { id: customer_contract, name: Customer contract }
  - { id: customer_list, name: Customer list }
  - { id: supplier_agreement, name: Supplier agreement }
  - { id: sop, name: Standard operating procedure }

outputs:
  - id: diligence_report
    name: Diligence report
    template: |
      # {{ project.name }} — Diligence Report
      Generated {{ generated_at }} · {{ coverage.percent }}% coverage
      {% for section in sections %}
      ## {{ section.name }}
      {{ section.narrative }}
      {% for gap in section.gaps %}- **Open gap:** {{ gap.text }}
      {% endfor %}{% endfor %}
      ## Sources
      {% for s in sources %}[{{ s.ref }}] {{ s.label }}
      {% endfor %}
```

Templates are sandboxed Jinja2 (`SandboxedEnvironment`) with a fixed set of
placeholders documented in the schema. `diligence_ready.yaml` will have 40–60
questions across Customers, Pricing, Suppliers, Staff, Operations, Financials,
Legal and Risks. `resignation.yaml` (key-person knowledge capture before an
employee leaves) will be small but complete, and is loaded by the same tests
to prove the format generalizes.

---

## 5. Data model

Changes from the spec's starting point are marked **(Δ)** with the reason.

| Table | Key fields | Notes |
|---|---|---|
| `users` | id, email, password_hash, display_name, created_at | |
| `project_members` **(Δ)** | project_id, user_id, role (`admin`/`owner`/`viewer`) | Role is per project, not per user: a broker can be admin on one project and viewer on another |
| `invites` **(Δ)** | id, project_id, email, role, token_hash, expires_at, accepted_at | Admin invites owner/viewer. The prototype shows the invite link in the UI; no email is sent |
| `auth_sessions` | id, user_id, token_hash, expires_at | httpOnly secure cookie |
| `projects` | id, name, module_id, module_version, status, retention_days, created_at | |
| `documents` | id, project_id, filename, mime, doc_type, blob_key, sha256, status, extracted_text, uploaded_by, created_at | `status`: uploaded → parsing → indexed / failed |
| `document_chunks` | id, document_id, project_id, ordinal, text, page, embedding `vector(384)` | `project_id` is denormalized so every vector query filters on it |
| `interview_sessions` | id, project_id, user_id, status, started_at, ended_at, current_question_id | Named to avoid clashing with auth sessions |
| `session_turns` **(Δ)** | id, session_id, ordinal, speaker (`interviewer`/`owner`), text, question_id, referenced_chunk_ids, created_at | The transcript is stored as turns so quotes point at an exact turn |
| `question_coverage` **(Δ)** | project_id, question_id, status (`unasked`/`asked`/`partial`/`answered`), last_session_id | Interview-time coverage. "Verified" coverage comes from approved items |
| `knowledge_items` | id, project_id, section_id, question_id, claim, original_claim, quote, turn_id, quote_start, quote_end, status (`draft`/`approved`/`edited`/`rejected`), verified_by, verified_at, embedding | `edited` = owner rewrote the claim and approved it, so it counts as verified (see open question 2) |
| `knowledge_item_chunks` | knowledge_item_id, chunk_id | Linked document evidence |
| `contradiction_flags` **(Δ)** | id, project_id, item_id, other_item_id \| chunk_id, explanation, status (`open`/`resolved`/`dismissed`), resolution_note | |
| `reports` | id, project_id, output_id, content_md, citations_json, coverage_snapshot, generated_by, generated_at | Immutable; regenerating creates a new row |
| `qa_messages` **(Δ)** | id, project_id, user_id, question, answer, citations_json, refused, created_at | |
| `audit_log` | id, project_id, user_id, action, target_type, target_id, metadata, ip, created_at | Append-only; holds ids and actions, not content |
| `jobs` **(Δ)** | id, type, payload, status, attempts, run_after, error | Claimed with `FOR UPDATE SKIP LOCKED` |
| `project_keys` **(Δ)** | project_id, wrapped_dek | Per-project data key for blob encryption; destroying it crypto-shreds the files |

---

## 6. Core engine and AI behaviours

### 6.1 Ingestion (job)
Upload → stream to encrypted blob storage → `parse` (parser chosen by mime) →
normalize text and keep page numbers → chunk (~800 tokens, ~100 overlap,
paragraph-aware; CSV chunked by row groups with the header repeated) → embed →
`indexed`. Per-file and per-project size limits, mime sniffing, and duplicate
detection by sha256.

### 6.2 Interviewer
Split into two parts:

- **Planner (deterministic code).** Picks the next target question by
  priority, by coverage status, by rotating sections so one session isn't all
  financials, and by whether relevant documents exist. Tracks the 15-minute
  budget. When time is up, it tells the agent to wrap up.
- **Interviewer agent (LLM).** Given the target question, follow-up hints,
  the last few turns, a compact coverage summary and the top-k retrieved
  chunks for this question (filtered by `related_document_types`), it returns
  structured output:
  ```json
  { "action": "follow_up" | "next_question" | "wrap_up",
    "utterance": "Your contract with Northwind mentions a change-of-control clause. How has that been handled?",
    "answer_quality": "clear" | "vague" | "off_topic" | "declined",
    "covered_question_ids": ["legal_coc"],
    "referenced_chunk_ids": ["…"] }
  ```
  The planner validates that `covered_question_ids` exist in the module, caps
  follow-ups per question (for example 2), and updates `question_coverage`.
  Responses stream to the UI. The module and document context sit in a cached
  prompt prefix to keep latency and cost down.

### 6.3 Extractor (job, on session end)
Input: the owner turns with turn ids, the questions asked, and the referenced
chunks. Output: atomic items `{section_id, question_id, claim, quote, turn_id,
chunk_ids}`.
**Quote validator (code):** `quote` must appear in the text of `turn_id`
(after whitespace and quote normalization), and that turn must be an *owner*
turn. Items that fail are dropped and logged. Claims are never made from
interviewer turns. Items are created as `draft`.

### 6.4 Contradiction check (job, after extraction and after each edit)
For each new or edited item: vector-search similar items and chunks in the same
project, then ask the LLM to classify each pair as `consistent`,
`contradicts` or `unrelated`, with a one-line explanation. `contradicts` opens a
flag. Flags show next to items in the verification UI and on the dashboard.
The owner resolves a flag by editing, rejecting or dismissing with a note.

### 6.5 Report writer (job)
1. **Assemble (code):** load the approved/edited items grouped by section;
   compute gaps from `coverage_rules` (unanswered high/medium questions, open
   contradiction flags). The LLM never decides what is a gap.
2. **Write (LLM):** for each section, turn *only* those items into short
   prose. Every sentence must carry one or more `[K<id>]` citations.
3. **Validate (code):** reject the section if any sentence has no citation, or
   if it cites an id that wasn't supplied. After one retry, fall back to a
   deterministic bullet list of the approved claims verbatim. A report can
   therefore always be produced without trusting the model.
4. **Render:** module Jinja2 template → Markdown → HTML → PDF. Sources list
   each claim with its owner quote, session date and linked document/page.

### 6.6 Q&A assistant
Retrieve over **approved items only** (plus the chunks linked to them), scoped
to the project. If the best similarity is below a threshold, refuse without
calling the LLM. Otherwise the LLM answers with `[K<id>]` citations or
returns `insufficient`. Citations are validated as in the report writer; an
answer with invalid citations becomes a refusal. Every query and answer is
logged (`qa_messages` and `audit_log`).

### 6.7 Prompts and evaluation
Prompts live as versioned files in `katra/prompts/`; the version is stored with
each output. A small golden set (from the demo company) covers extraction
precision, quote validity, contradiction detection and Q&A refusal. It runs
against the real model on demand (`make eval`). CI uses `FakeProvider`.

---

## 7. Security baseline (Phase 1)

| Requirement | Implementation |
|---|---|
| Per-project isolation and authz on every request | Each project-scoped route depends on `require_project_role(*roles)`, which loads membership and returns a `ProjectContext`. Services and repositories take that context, never a bare `project_id`. A **route-inventory test** fails if any route under `/api/projects/{id}` lacks the dependency, and a parametrized **role × endpoint matrix test** checks allow/deny, including cross-project access attempts |
| Role-based access | admin: manage project, invites, generate reports, view everything · owner: upload, interview, verify · viewer: approved reports and Q&A only (no raw documents, transcripts or draft items) |
| Encryption in transit | Caddy TLS on all traffic; secure, httpOnly, SameSite=Lax cookies; HSTS; CSRF token on mutating requests |
| Encryption at rest | Files: AES-256-GCM with a per-project data key, wrapped by a master key from env. Database: run on an encrypted volume (documented in the deployment notes). Column-level encryption of transcripts is deferred because it breaks search; this is noted as a known limitation |
| Audit log | Written by a service helper called from routes for views, edits, approvals, report generation, Q&A queries, logins, invites and deletes. Append-only at the DB level (app role has no UPDATE/DELETE on `audit_log`). Visible to admins |
| Retention and delete-everything | `projects.retention_days` with a daily worker job that purges expired projects. Admin "Delete project" requires typing the project name, then deletes rows, blobs and the project key (crypto-shred), and keeps a minimal audit tombstone |
| No training on customer data | Anthropic commercial API terms (no training on API data by default). Document how to request zero data retention. Local embeddings mean no document text goes to an embeddings vendor |
| Portability | Everything containerized; LLM, embeddings, storage and parsers behind interfaces |
| Secrets | `.env` (git-ignored) with `.env.example`; `pydantic-settings`; startup fails if a required secret is missing; no secrets in logs |
| Also | Argon2id password hashing, login rate limiting, upload size/type limits, sandboxed Jinja2, LLM output treated as untrusted (rendered as escaped Markdown) |

---

## 8. Milestones

Each milestone ends with: code merged on the branch, tests green,
`docker compose up` working, and a short demo note in `docs/milestones/`.
**Review gate after every milestone** before the next starts.

The order follows the spec, with two deliberate changes:
**audit-log plumbing moves into M1** (so every later feature logs from day one,
and M9 only adds retention/delete and the audit viewer), and **demo seed data
grows with each milestone** rather than arriving at the end.

### M0 — Plan and repo conventions *(this PR)*
- `docs/SPEC.md`, `docs/PLAN.md`, `CLAUDE.md` with the hard rules
- **Done when:** plan reviewed; open questions (§10) answered

### M1 — Skeleton, Compose, auth and roles, schema
- Compose services: `caddy`, `web`, `api`, `worker`, `db` (pgvector image); `make up`, `make test`
- FastAPI app factory, settings, health endpoint; Alembic with the **full schema** from §5
- Auth: login/logout, session cookies, invite creation and acceptance, CLI to create the first admin
- RBAC dependency, `ProjectContext`, audit helper and table
- Provider interfaces and fakes (LLM, embeddings, storage) stubbed
- Frontend shell: login, project list, role-aware navigation
- **Tests:** auth flows, role × endpoint matrix, route-inventory test, cross-project denial
- **Done when:** an admin creates a project and invites an owner and a viewer, each logs in and sees only what their role allows, over HTTPS, from one command

### M2 — Module loader and question banks
- Pydantic module schema, loader, registry, version pinning on projects
- Full `diligence_ready.yaml` (40–60 questions, 8 sections) and minimal `resignation.yaml`
- Module picker in the create-project flow; read-only question bank view
- **Tests:** valid modules load; each kind of malformed module fails with a clear error; duplicate ids rejected; templates render with sample context; both modules pass the same suite
- **Done when:** dropping a new YAML file into `modules/` makes it selectable with no code change

### M3 — Document upload, parsing, chunking, embeddings
- Upload API and UI (drag-drop, doc-type tagging, status badges); encrypted blob storage
- Job queue and worker; parsers for PDF, DOCX, TXT and CSV; chunker; local embeddings; project-scoped retriever
- Seed: demo company documents (P&L summary, two customer contracts, supplier agreement, SOP)
- **Tests:** each parser on fixtures; chunk boundaries; retrieval never crosses projects; blobs on disk are not plaintext
- **Done when:** the demo documents upload, index, and return sensible top-k chunks for sample questions

### M4 — Text interview and interviewer agent
- Planner, interviewer agent, session lifecycle (start / pause / resume / end), timer
- Chat UI with streaming responses, a "documents referenced" panel, and end-session
- `AnthropicProvider` implemented (streaming, structured output, prompt caching, retries)
- **Tests:** planner selection and coverage transitions (deterministic, no LLM); agent contract with `FakeProvider`; follow-up cap; time budget
- **Done when:** an owner completes a 15-minute session with sensible questions that reference the uploaded documents, and coverage updates

### M5 — Knowledge extraction and verification UI
- Extraction job on session end; quote validator; draft items
- Verification UI: item cards with claim, highlighted quote in transcript context, linked docs; approve / edit / reject; bulk approve per section
- Seed: scripted demo interview transcript
- **Tests:** quote validator (exact, normalized, wrong-turn, interviewer-turn cases); extraction with fake output, including invalid items being dropped; only the owner can verify; every verification is audited
- **Done when:** an owner turns a session into verified items without help

### M6 — Coverage dashboard and contradiction flags
- Coverage computed from module rules: per question, per section, overall; gap list
- Dashboard: section progress bars, unanswered high-priority questions, open flags; "next session will focus on…" preview
- Contradiction job and resolution UI
- Seed: one planted contradiction (for example, contract term in a document vs the owner's answer)
- **Tests:** coverage rules incl. overrides; flag lifecycle; the planner prioritizes gaps
- **Done when:** the dashboard matches hand-calculated coverage for the demo, and the planted contradiction is flagged

### M7 — Report generation (Markdown and PDF)
- Assembler, writer, citation validator, deterministic fallback, renderer, PDF export
- Report page for admin/viewer; report history; download MD/PDF
- **Tests:** a report covers every section; every sentence cites an approved item; uncited LLM output is rejected and the fallback is used; gaps match coverage; rejected/draft items never appear
- **Done when:** the demo company produces a sourced report with a gaps list

### M8 — Q&A assistant with citations
- Retriever over approved items, threshold refusal, answerer, citation validation
- Viewer chat UI with clickable citations (claim → quote → document)
- **Tests:** answers cite only approved items; unsupported questions are refused; draft/rejected content is never retrievable; viewer cannot reach raw documents
- **Done when:** on a 20-question demo script, every answerable question is answered with correct citations and every unanswerable one is refused

### M9 — Audit viewer, retention and delete controls
- Audit log viewer (admin, filterable); retention setting; purge job; delete-everything with crypto-shred
- Security pass: headers, rate limits, dependency scan, secret scan
- **Tests:** a full delete leaves no rows, blobs or keys for the project; the retention job purges correctly; the audit table rejects update/delete
- **Done when:** the security checklist in §7 is demonstrably met

### M10 — Stretch: voice and the second-module demo
- Voice: browser Web Speech API for speech-to-text and speech synthesis behind a frontend `VoiceAdapter`; transcripts flow through the same turn pipeline (Chrome/Edge first)
- Second module: run a full `resignation` project end to end with no code change
- Playwright end-to-end smoke test for the main demo path
- **Done when:** all success criteria in the spec pass

---

## 9. Testing strategy

- **Unit:** module loader, planner, coverage rules, quote and citation validators, parsers, chunker
- **Integration:** API against a real Postgres via Compose; `FakeProvider` for LLM and embeddings
- **Authorization:** route inventory + role × endpoint × project matrix (required by the spec)
- **AI evals:** a golden set against the real model, run on demand, not in CI
- **E2E:** one Playwright run of the demo path (M10)

---

## 10. Decisions

Agreed at the plan review (all recommendations accepted):

1. **Frontend:** Vite React SPA, not Next.js.
2. **"Edited" status:** owner-edited items count as verified. The original claim and quote are kept, and the report shows the edited text.
3. **Viewer document access:** buyers see the claim and quote only, not the raw source documents.
4. **Embeddings:** local `fastembed` by default (Voyage AI stays a drop-in option).
5. **Invites:** the invite link is shown once in the admin UI; no email is sent.
6. **Report generation:** admins only.
7. **Model and data terms:** still open. An Anthropic API key is needed from M4. Zero data retention is to be requested before demos that use real owner data. Until then everything runs on the `fake` providers.

Decisions made during the build:

- **Who can create projects:** a `users.is_staff` flag (Jamie, brokers). Project roles stay per project in `project_members`. The first staff user is created from `.env` on first start, or with `python -m katra.cli create-admin`.
- **Services:** the SPA is served by the same Caddy container that terminates TLS (`web`), so Compose runs four services: `web`, `api`, `worker` and `db`.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Interview feels robotic or repetitive | Planner rotates sections; LLM handles phrasing; tune on the demo transcript in M4 |
| Extraction misses or merges claims | Owner verification is the backstop; golden-set eval; "add item from quote" in the verification UI |
| LLM output slips past the no-fabrication rule | Code validators for quotes and citations, plus a deterministic report fallback |
| Live-demo latency or API outage | Streaming, prompt caching, `FakeProvider` offline demo mode with seeded data |
| Scanned PDFs yield no text | Detect empty extraction and tell the user; OCR is Phase 2 |
| Scope creep from the stretch goals | Voice and polish wait until M1–M9 pass review |
