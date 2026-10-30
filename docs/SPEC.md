# Katra — Prototype Spec for Claude Code

Oct 30, 2026 · Jamie

Build a working prototype of Katra's diligence-ready module. An owner uploads documents and is interviewed by AI from a question bank. They verify the captured answers, and the system generates a sourced diligence report plus a Q&A assistant. Hand this whole doc to Claude Code as the starting brief.

## Goal and scope

The prototype proves that one modular workflow can run end to end on a shared core engine. It is for demos to brokers, buyers and owners, not for production.

**In scope:**

- One workflow module: Diligence-ready (owner preparing to sell)
- A module format that lets new workflows be added as config files, with no code changes
- Text interview first; voice as a stretch goal
- Document upload and ingestion (PDF, DOCX, TXT, CSV)
- Answer verification by the owner
- A generated diligence report with sources
- A Q&A assistant over verified knowledge
- Phase 1 security basics

**Out of scope:** billing, multi-tenant admin, email ingestion, on-prem deployment, mobile apps and integrations.

## Users and roles

- **Owner (interviewee):** takes interviews, uploads files, verifies answers
- **Admin (Jamie or a broker):** creates a project, picks a module, invites the owner, views the report
- **Viewer (buyer):** read-only access to the approved report and the Q&A assistant

## Core user flow

1. The admin creates a project and selects the Diligence-ready module.
2. The owner logs in and uploads documents: financials, contracts, customer lists and SOPs.
3. The system ingests and indexes the documents.
4. The owner starts interview sessions of about 15 minutes each. The AI asks questions from the module's question bank, adapts follow-ups to the answers, and draws on the uploaded documents to probe gaps and contradictions.
5. After each session, the AI turns transcripts into discrete knowledge items: a claim, its topic, and its source (a transcript quote and any linked documents).
6. The owner reviews each item: approve, edit or reject. Only approved items count as verified.
7. A coverage dashboard shows progress by topic and highlights gaps.
8. The admin generates the diligence report: verified answers by section, the source behind each, and an open-gaps list.
9. A viewer queries the Q&A assistant, which answers only from verified items, cites sources, and says when it doesn't know.

## Module format

Each workflow is a YAML or JSON file in a modules folder. Adding a module means adding a file. A module defines:

- `id`, `name` and `description`
- `roles`: who gets interviewed
- `sections`: topics such as Customers, Pricing, Suppliers, Staff, Operations, Financials, Legal and Risks
- `questions` per section: the base question, follow-up hints, related document types, and priority
- `session_length_minutes` and `target_sessions`
- `outputs`: report template(s), as Markdown templates with placeholders
- `coverage_rules`: what counts as a section being complete

Include a complete `diligence_ready.yaml` with 40–60 realistic questions across the sections. Add a minimal second module (for example `resignation.yaml`) to prove the format generalizes.

## Suggested tech stack

These are suggestions. Claude Code can propose alternatives.

- **Backend:** Python with FastAPI
- **Frontend:** Next.js or a simple React app
- **Database:** PostgreSQL with the pgvector extension for embeddings
- **LLM:** a provider abstraction layer so the model can be swapped, including a local model later. Default to the Claude API.
- **Document parsing:** a standard library for PDF and DOCX extraction
- **Voice (stretch):** browser speech-to-text and text-to-speech, or a provider abstraction
- **Packaging:** Docker Compose so the whole stack runs locally with one command

## Data model (starting point)

- `Project`: id, name, module\_id, status, created\_at
- `User`: id, email, role, project access
- `Document`: id, project\_id, filename, type, extracted text, chunks with embeddings
- `Session`: id, project\_id, user\_id, transcript, started\_at, ended\_at
- `KnowledgeItem`: id, project\_id, section, question\_id, claim text, transcript quote, linked document chunks, status (draft, approved, edited, rejected), verified\_by, verified\_at
- `Report`: id, project\_id, template, generated content, generated\_at
- `AuditLog`: id, user\_id, action, target, timestamp

## Key AI behaviours

- **Interviewer:** asks one question at a time, in plain language, with follow-ups when answers are vague. It references uploaded documents ("Your contract with X mentions a change-of-control clause. How has that been handled?"). It tracks which questions are covered.
- **Extractor:** turns transcripts into atomic knowledge items, each tied to an exact quote.
- **Contradiction check:** flags conflicts between answers, or between answers and documents, for the owner to resolve.
- **Report writer:** uses only approved items, never invents content, and marks gaps explicitly.
- **Q&A assistant:** uses retrieval over approved items and linked documents, always cites sources, and declines when unsupported.

**Hard rule:** the system must never fabricate an answer on the owner's behalf. Every claim in a report traces back to the owner's own words and verification.

## Security baseline (Phase 1)

- Data isolated per project, with authorization checks on every request
- Encryption at rest (database and file storage) and HTTPS in transit
- Role-based access: owner, admin, viewer
- An audit log of views, edits, approvals, report generation and Q&A queries
- Configurable retention and a project-level delete-everything function
- No customer data used for model training; use provider settings that ensure this
- Portable architecture: containerized, with LLM and storage behind interfaces, so private cloud or on-prem deployment is possible in Phase 2
- Secrets in environment variables, never in code

## Build milestones

1. Project skeleton, Docker Compose, auth and roles, database schema
2. Module loader and the `diligence_ready.yaml` question bank
3. Document upload, parsing, chunking and embeddings
4. Text interview UI and interviewer agent with coverage tracking
5. Knowledge extraction and the verification UI
6. Coverage dashboard and contradiction flags
7. Report generation (Markdown and PDF export)
8. Q&A assistant with citations
9. Audit log, retention and delete controls
10. Stretch: voice interviews; second module demo

## Demo scenario

Seed a fictional company: a 25-person managed IT services firm whose owner is preparing to sell. Include sample documents (a P&L summary, two customer contracts, a supplier agreement and an SOP), a short pre-recorded interview, and a generated report. This makes demos to brokers repeatable.

## Success criteria

- A new owner can complete upload, at least one interview session and verification without help
- The report covers every module section, with sources on every claim and gaps listed
- The Q&A assistant answers correctly from verified items and refuses unsupported questions
- A second module runs by adding only a config file
- The whole stack starts locally with one command

## How to use this with Claude Code

- Start a new repo, paste or attach this spec, and ask Claude Code to propose an architecture and plan before writing code.
- Build one milestone at a time, and review and run the code after each.
- Ask Claude Code to write tests for the module loader, extraction and authorization checks.
- Keep a `CLAUDE.md` file in the repo with the hard rules: no fabricated answers, cite sources, keep security basics.
