# feltwillow-publishing (scaffold, contract revision H2)

**Status: PROPOSED CONTRACT. No contract is released and no module is enabled.** This is the private
repository `jeilealr/feltwillow-publishing` (branch `main`; the owner does all git), started from the
Blueprint v3 scaffold (2026-10-07).

This is the one canonical home of the H2 contracts and code: Agent B's handoff contract (draft H1), Agents
C/D/E's schemas and tools, and the lead's DECISIONS_H2.

## Two repositories, one boundary

- Production (`jeilealr/feltwillow-production`) makes stories and exports a **handoff package** (a tar;
  `production/export_handoff.py`, proposed in the production change set) against a pinned contract
  (`production/contracts/CONTRACT.lock`).
- Publishing (this repository) owns the contracts, imports handoffs, freezes releases, builds public
  bundles and plans publication. Neither repository imports the other's code; no submodules; this
  repository never needs a production checkout (proved by the clean-checkout run in `VALIDATION.md`).

## What runs today

One command, offline (plus a local 127.0.0.1 server for the podcast probe tests):

```sh
python -m venv .venv && .venv/bin/pip install -r requirements/blueprint-check.txt
PYTHONPATH=src .venv/bin/python -m feltwillow_publish.check --all --report results/check_results.json
# optional JavaScript canonicalization parity:  --node "$(command -v node)"   (see tools/js/README.md)
```

Regenerate the contract artifacts (deterministic; the committed files are the source of truth):

```sh
PYTHONPATH=src python tools/build_schemas.py      # publishing/contracts/schemas/*.v2+ and record-types.json
PYTHONPATH=src python tools/build_examples.py     # publishing/examples/ and tests/fixtures/ (needs PyYAML)
python tools/build_error_codes.py                 # publishing/contracts/error-codes.json
```

**Planned, not executable:** the `feltwillow-publish` CLI (`validate`, `import-handoff`, `freeze`, `prepare`,
`preview`, `plan`, `apply`, `reconcile`, `status`, `rollback`). No console script is installed.

## Module states

`spec_only` = specification only; `implemented` = code exists here and its tests ran; `enabled` = allowed
to act on real state (requires an owner `configuration` approval). **Nothing is `enabled`.**

| Module | Path | State | Notes |
|---|---|---|---|
| contracts (cj1 canonicalization, validation) | `src/feltwillow_publish/contracts/` | implemented | 20 H2 schemas + 16 v2 schemas carried forward |
| imports (reference importer) | `src/feltwillow_publish/imports/` | implemented | tested on synthetic packages only; agents never run a real import |
| web contract checks | `src/feltwillow_publish/web/` | implemented | payload, render-input, completeness, synthetic site artifact |
| podcast tools | `src/feltwillow_publish/podcast/` | implemented | validator, safe feed parser, diff, reconcile, probe; independent-RSS builder is an INACTIVE reference |
| ops: leak_scan, strict_zero, ci_lint, handoff_index_scan, state_roots | `src/feltwillow_publish/ops/` | implemented | declaration checks; no provider dashboard observed |
| website: plain-static, astro, ghost-theme, shared | `web/` | spec_only | READMEs only |
| hosting: cloudflare-pages, netlify, ghost | `infra/` | spec_only | no accounts, tokens or DNS |
| releases/freeze, bundles, plans/apply, adapters, CLI | — | spec_only | not in this scaffold |
| CI workflows | `tests/fixtures/workflows/` | spec_only | linted examples only; no `.github/workflows/` |

## Layout

```text
README.md  CLAUDE.md  VALIDATION.md  DEPRECATED_V2_RULES.md  pyproject.toml  .gitignore  requirements/blueprint-check.txt
publishing/contracts/schemas/        all H2 schemas (*.v2/new) + v2 *.v1 schemas (byte copies)
publishing/contracts/record-types.json   current version per kind; superseded v1 kinds
publishing/contracts/error-codes.json    merged catalogue (442 codes in 27 families, incl. planned and deprecated)
publishing/examples/                 positive examples (example: true) incl. web/render-input bundles
src/feltwillow_publish/{contracts,imports,web,podcast,ops}/  code;  src/feltwillow_publish/check.py  runner
tests/test_*.py  tests/support.py  tests/podcast_fixtures.py
tests/fixtures/  negative/{records,imports}, scenarios, golden, packages (synthetic PNGs), podcast,
                 feeds, ops, handoff-index, workflows, compat (G3's selection example and CONTRACT.lock)
tools/build_*.py  tools/js/cj1.mjs (+README)   web/  infra/   results/check_results.json
```

## Storage roots (DECISIONS_H2 s.2)

| Variable | Holds | Refused (`STATE_ROOT_UNSET` / `STATE_ROOT_UNSAFE`) when |
|---|---|---|
| `FELTWILLOW_HANDOFF_INBOX` | incoming handoff tars before import | unset (for import), relative, inside Git, inside OneDrive, on LUMI storage |
| `FELTWILLOW_MASTER_ROOT` | immutable archived tars `handoffs/<sha256>.tar`, masters, final mixes, DaVinci archives | same |
| `FELTWILLOW_PUBLISH_STATE_ROOT` | import receipts, plans/receipts, locks, feed observations, private evidence | same |

Owner storage (2026-10-07): Mac working copy outside OneDrive; copies to **Microsoft 365 Personal OneDrive
(1 TB plan, 187 GB used)** and a **1 TB external drive**, never deleting at the destination. OneDrive is a
sync copy, not history. Recorded in `publishing/examples/service-inventory.v1.example.json` as owner
infrastructure (declared, not counted as a service fee).

## Owner decisions reflected in examples

- Repository private, branch `main`, owner does all git (CLAUDE.md).
- First podcast host **Spotify** (`project.v2` `podcast_authority: spotify`; Spotify module still `spec_only`).
- Public contact e-mail `jei.leal.r@gmail.com` (`project.v2`), `public_contact_acknowledged: true` (L-27: the
  owner supplied it knowing it becomes public in the RSS feed).
- AI-voice disclosure (L-27, Apple guideline 1.11): `project.v2` `ai_disclosure` = {"text": "All voices in this
  podcast are AI-generated.", "spoken": true}. `project.v2` has a single text field, so the rest of the owner's
  wording is recorded here (and in `tools/build_examples.py` `AI_DISCLOSURE_NOTE`): spoken at the start of every
  episode, EN "This story is told with AI-generated voices." / ES "Esta historia se cuenta con voces generadas por
  inteligencia artificial." / DE "Diese Geschichte wird mit KI-generierten Stimmen erzählt."; show description in
  all languages (translated) "All voices in this podcast are AI-generated."; last line of every episode
  description "The voices in this episode are AI-generated.". **ES/DE wording needs a native-speaker check before
  use.** A per-language disclosure field would be a future `project` schema version (not added, to keep the H2
  schemas stable for G3's CONTRACT.lock).
- Launch languages **en first, then es and de** (`story-allocation` `planned_languages`; web examples are en only).
- **L-28 (OD-14): the reading-edition text is authored in publishing.** Production hands over the script / line
  list (source files) and media only; the handoff has an `images` component instead of `reading`. Publishing writes
  `reading-edition.v1` records (example: `publishing/examples/reading-edition.v1.lion-and-mouse.example.json`, EXAMPLE
  ONLY) and each release with a website channel pins one (`READING_EDITION_MISSING` otherwise).
- **L-29 (OD-24): audio masters are WAV/FLAC** (MP3/M4A refused in handoffs: `HANDOFF_AUDIO_NOT_LOSSLESS`;
  publishing derives delivery MP3s); every measured asset records `measurement: {tool, version}`
  (`feltwillow-stdlib` or `ffprobe`); video must be measured by ffprobe. The exporter refuses video without ffprobe
  (`MEASUREMENT_TOOL_UNAVAILABLE`, catalogued as planned until G3 implements it).
- Not decided, therefore absent: website module and host, ffprobe for MP3/MP4 measurement (L-24).
