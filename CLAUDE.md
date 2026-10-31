# Katra — notes for Claude Code

Katra is a prototype of the "Diligence-ready" workflow. An owner uploads documents, is
interviewed by AI from a module's question bank, verifies the extracted answers, and
the system produces a sourced diligence report and a Q&A assistant.

- Brief: `docs/SPEC.md`
- Architecture and milestones: `docs/PLAN.md`. Build one milestone at a time and stop for review after each.

## Hard rules

1. **Never fabricate an answer on the owner's behalf.** Every claim in a report or Q&A
   answer must trace to an exact owner quote (an owner turn, not an interviewer turn)
   and an owner approval. Enforce this in code with validators, not only in prompts.
2. **Always cite sources.** Report sentences and Q&A answers carry `[K<id>]` citations
   that are validated against approved items. If an answer is unsupported, refuse it;
   don't guess.
3. **Gaps are computed, not generated.** Coverage and gaps come from module
   `coverage_rules` in code.
4. **Keep the security basics.**
   - Every project-scoped route uses the RBAC dependency, and the route-inventory test must pass.
   - All queries, including vector search, are filtered by project.
   - Log views, edits, approvals, report generation and Q&A queries to `audit_log`.
   - Secrets come from environment variables only. Never commit them.
   - Customer data is never sent anywhere except through the provider interfaces.
5. **Modules are data.** No module ids or question ids in application code. A new
   workflow must work by adding a YAML file to `modules/`.
6. **The /admin browser stays read-only for anything that carries the hard rules.** Never make
   knowledge items, transcripts, reports or the audit log editable there, and never show secret
   columns (`katra/admin.py`).
7. **Interfaces for portability.** LLM, embeddings, storage and parsers are accessed
   through `katra/providers/*` only.

## Conventions

- Tests: write tests for the module loader, extraction, citation/quote validators and
  authorization checks alongside each feature. CI uses `FakeProvider`, never the real API.
- Do not put model identifiers in code comments or commit messages. Models are set by env vars.
