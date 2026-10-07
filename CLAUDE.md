# Agent and developer rules for feltwillow-publishing

These rules bind every AI agent and every collaborator working in this repository.

## Git and authority

- **The owner does all git** (add, commit, push, pull, merge, branch, tag) unless the owner explicitly
  delegates a specific operation in writing for that session. Agents may run read-only git (`status`,
  `log`, `diff`, `show`).
- Default branch `main`. The repository is private.
- Agents **never** run `import`, `apply`, `rollback` or any command that writes to `FELTWILLOW_MASTER_ROOT` or
  `FELTWILLOW_PUBLISH_STATE_ROOT`, and never call a provider (Spotify, Apple, Amazon, Pocket Casts, YouTube,
  Cloudflare, Netlify, Ghost). The reference importer is exercised only by the test suite on throw-away
  directories.
- Agents never hold, request, read or print deploy tokens, API keys or account credentials. Production
  credentials (Gemini, OpenAI, ElevenLabs, Hugging Face, LUMI) never belong in this repository or its CI.
- Approvals are records made by the owner/reviewer. An agent never writes an approval with
  `decision: approved`, never sets `public_contact_acknowledged: true` on its own (only to record an owner decision), and never changes a module to `enabled`.

## Module states

`spec_only` (specification only), `implemented` (code exists here and its tests ran), `enabled` (may act on
real state; requires an owner approval of stage `deployment`, scope `configuration`). Exactly one website
module may be `enabled` and it must equal `website.primary`. Never describe a planned command as executable.

## Contracts

- Schemas in `publishing/contracts/schemas/` are the contract authority; production pins a released copy.
  Change them only through `tools/build_schemas.py`, bump the record version for any non-additive change,
  and regenerate examples and fixtures. Frozen digests are never recomputed.
- Every H2 record carries `"canonicalization": "feltwillow-canonical-json-v1"` (except `handoff-selection.v1`,
  which is YAML pinned by its Git blob digest). Integers only (no floats), within +-(2^53-1); strings NFC.
- Examples carry `"example": true` and `EXAMPLE ONLY` text; never invent provider IDs, URLs, prices,
  approvals or masters. Real records must not use `.invalid`/example hosts.

## Data boundaries

- Never commit tars, masters, final mixes, DaVinci projects, receipts, plans, feed observations or private
  evidence: they live in `FELTWILLOW_MASTER_ROOT` / `FELTWILLOW_PUBLISH_STATE_ROOT` (outside Git, outside OneDrive
  sync folders, never on LUMI scratch). `publishing/handoffs/` may hold only sanitized index entries.
- Reading-edition text is authored here (L-28) as `reading-edition.v1`; agents may draft it only as a record
  marked draft/example for the owner, never mark it frozen or approved.
- Public bundles pass `feltwillow_publish.ops.leak_scan` on the exact upload directory before any upload.
- Before finishing a change, run `PYTHONPATH=src python -m feltwillow_publish.check --all` and report the counts.
