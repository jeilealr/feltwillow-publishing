<!-- Saved by the lead from Agent G1's hand-back, 2026-10-07. -->

## Agent G1 report: publishing scaffold integrator (contract revision H2)

I built the scaffold at `package/publishing-scaffold/`; the folder was empty when I resumed after the session limit, so everything here is new. In a clean-checkout run (no production checkout, empty environment, HOME unset) all **446 of 446** counted cases pass, including JavaScript parity with an unpinned Node. Nothing was committed, imported, uploaded or enabled, and nothing was written to the real `bllt-publishing` clone (still empty). Production HEAD is still `b880c23`.

### 1. Evidence
- **Sources read:** `COMMON.md`, `DECISIONS_H2.md` (including the new §8, L-20..L-24), `OWNER_DECISIONS.md`, `LEAD_NOTES.md`, `STAGE0_INVENTORY.md`, the REPORT.md of agents A–E, and all tools, schemas, examples and fixtures of B, C, D and E.
- **v2 package (REPO):** read-only. Its 16 v1 schemas are byte-copied into the scaffold.
- **Agent G3's change set (read-only):** `export_handoff.py` (selection format, key sets, error codes), `handoff_selection.example.yaml` and the example `CONTRACT.lock`. The last two are vendored unchanged in `tests/fixtures/compat/`.
- **REPO values:** the Lion-and-Mouse source-file and keyframe digests, sizes and dimensions are Agent B's `b880c23` measurements, recorded as constants. Paths removed by the owner's cleanup are cited only as `b880c23` provenance; current paths use the v5 location.
- **Owner decisions:** applied in the examples, as listed in §2.

### 2. Proposals (files written, all PROPOSED CONTRACT)
- **Top-level files:**
  - `README.md`: purpose, module-state table, layout, storage roots, and where each owner decision appears.
  - `CLAUDE.md`: owner does all git; agents never run import/apply/rollback or git writes, never hold tokens, never write approvals or set a module to `enabled`.
  - `pyproject.toml` (no console script; the CLI is labelled planned), `requirements/blueprint-check.txt` (PyYAML 6.0.3, jsonschema 4.26.0), `.gitignore`.
  - `VALIDATION.md` and `results/check_results.json`.
- **Contracts (`publishing/contracts/`):**
  - `schemas/`: 19 H2 schemas plus the 16 v2 v1 schemas, so 35 files.
  - `record-types.json` (current version per kind, superseded v1 kinds).
  - `error-codes.json`: 374 codes in 21 families, merging B, C, D, E, `STATE_ROOT_*`, the new H2 codes and G3's exporter codes for reference.
  - `README.md`.
- **Examples (`publishing/examples/`):** 23 records plus two render-input web bundles and their manifests. Owner decisions recorded there:
  - `project.v2`: `podcast_authority: spotify`; `public_contact_email: jei.leal.r@gmail.com` with `public_contact_acknowledged: false`; `ai_disclosure: null` because no wording is approved yet.
  - `story-allocation`: `planned_languages: [en, es, de]`; web examples are en only.
  - `service-inventory.v1`: Microsoft 365 Personal OneDrive (1 TB plan, 187 GB used) and a 1 TB external drive, declared as owner infrastructure; Spotify for Creators as `planned`.
- **Code (`src/bllt_publish/`):**
  - `contracts`: `cj1` and one unified `validate` with B's semantics, D's semantics, a hook to C's web rules, and the new H2 rules.
  - `imports/importer.py`: B's importer with the H2 storage layout, plus `import_from_environment` (the three root checks and `ARCHIVE_OUTSIDE_INBOX`).
  - `web/contract.py` (C), `podcast/podcast.py` (D).
  - `ops/`: E's `leak_scan`, `strict_zero` and `ci_lint`, plus new `state_roots.py` and `handoff_index_scan.py` (IC-E4).
  - `check.py`: the single runner, `python -m bllt_publish.check --all --report <file> [--node <path>]`.
- **Tests:**
  - Suites: `tests/test_{contracts,imports,web,podcast,ops}.py`, plus `support.py` and `podcast_fixtures.py`.
  - `tests/fixtures/`: 105 negative record fixtures (57 new for H2), 25 negative imports, 6 scenarios, golden cases, synthetic packages with a `SOURCES.json` digest record, podcast fixtures, feeds, ops, handoff-index and workflows.
- **Tools and READMEs:** `tools/build_{schemas,examples,error_codes}.py`; `tools/js/cj1.mjs` with a README on running parity under a pinned Node; C's `web/` and `infra/` READMEs, all `spec_only`.

**Module states:** `contracts`, `imports`, `web`, `podcast` and `ops` are `implemented` (code plus executed tests). Website renderers, hosting, releases, plans/apply, adapters, the CLI and CI workflows are `spec_only`. Nothing is `enabled`.

**DECISIONS_H2 applied:**
- Module ids `astro`/`ghost`/`plain_static` in every record.
- `common.v2` additions, plus `dirty_path` (L-21).
- Approval scope `rights_review.podcast_audio`: an approved review must carry the checks `gemini-terms-answer` and `mix-music-and-effects`.
- New versions `publish-plan.v2` (with the rule that a website plan may not touch podcast records, IC-D12), `publish-receipt.v2`, `media-delivery.v2`, `site-set.v2`, `project.v2`, `service-inventory.v1`.
- E's wider public file-name pattern replaces B's.
- `STATE_ROOT_UNSET`/`STATE_ROOT_UNSAFE` checks for the three roots; archives at `BLLT_MASTER_ROOT/handoffs/<sha256>.tar`.
- Canonicalization constant `bllt-canonical-json-v1` everywhere (L-20).
- Source purpose `selection` and the `handoff-selection.v1` schema; G3's example YAML validates against it (L-23).

**Choices I made that the lead should confirm:**
- **Canonicalization constant on all H2 kinds.** I put it on every H2 record kind, not only digest-pinned ones (`approval`, `import-receipt`, `story-allocation` and `contract-lock` now require it). `handoff-selection` is the exception, because it is YAML pinned by its Git blob digest.
- **Plan check reports.** The plan requires a `leak_scan` report digest for web deploy/publish actions, and a `strict_zero` report digest for any production plan.
- **`PRIMARY_MODULE_SPEC_ONLY`.** New `project.v2` rule: `website.primary` may not name a `spec_only` module.

**Decisions not fully applied:**
- **L-24 (ffprobe):** this is an owner decision. The scaffold does no MP3/MP4 measurement; the importer's PNG dimension check is the only measurement check.
- **G3 compatibility:** G3's example `CONTRACT.lock` fails `contract-lock.v1` under H2 only because it lacks the `canonicalization` field. Its 8 pinned digests are of B's H1 schemas, so all 8 differ from the H2 files. This is recorded as an uncounted `info_g3_compat` group in the results.
- **Code-name overlap:** G3's exporter emits `MASTER_ROOT_UNSET` where H2 uses `STATE_ROOT_UNSET`; the catalogue notes this.

### 3. Open questions for the owner
1. Do you acknowledge that `jei.leal.r@gmail.com` becomes public in the RSS feed and on the directories? I left the acknowledgement `false`.
2. What AI-disclosure wording should the show use, and is it also spoken in the audio? It is required before any podcast module is enabled.
3. Is ffprobe allowed for MP3/MP4/MOV measurement (L-24)?
4. Do you accept unpinned Node v24.21.0 as interim parity evidence, or should parity wait for a pinned-Node run?

### 4. Interface-change requests to the lead
- **IC-G1-1 (G3):** regenerate `CONTRACT.lock` from the H2 schemas with the `canonicalization` constant and version `0.2.0-h2`, and emit `canonicalization` in its handoff records.
- **IC-G1-2 (G3):** use `STATE_ROOT_UNSET`/`STATE_ROOT_UNSAFE` instead of `MASTER_ROOT_UNSET`, and record the selection file with source purpose `selection` instead of `other`.
- **IC-G1-3 (G2):** the docs should name the constant `bllt-canonical-json-v1`. Docs should also cover the `publish-receipt.v2` status spelling `manual_pending`, the new error codes (`error-codes.json` is the source), and the archive locator `handoffs/<sha256>.tar`.
- **IC-G1-4 (lead):** confirm the choices listed in §2.

### 5. Tests executed
Python is `/scratch/project_465002727/jelealro/tmp/venv-blueprint` (3.12.9). Node is `~/.vscode-server/cli/servers/Stable-07f806f999227108933c2e30515b26eecc1fda74/server/node` (v24.21.0, unpinned). Exact commands are in `VALIDATION.md`.

| Command | Result |
|---|---|
| `build_schemas.py`, `build_examples.py`, `build_error_codes.py` in the clean copy `/scratch/project_465002727/jelealro/tmp/g1_clean/` | regenerated output is byte-identical to the package (`diff -r` clean) |
| `env -i HOME=/nonexistent PYTHONPATH=src python -m bllt_publish.check --all --node … --report …` | **446/446, exit 0** |

The 446 cases break down as:
- **Contracts:** schemas 35/35, positive examples 29/29, negative records 105/105, Python golden cases 24/24.
- **Imports:** negative imports 25/25, scenarios 6/6, positive import 1/1, environment-root import 6/6.
- **Web:** 51/51.
- **Podcast:** 60/60.
- **Ops:** leak_scan 36/36, strict_zero 28/28, ci_lint 24/24, state_roots 10/10, handoff_index_scan 3/3.
- **Runner checks:** error catalogue covers all 214 observed codes (1/1); JS parity 2/2 (24 golden cases plus 26 record digests).

**Intentional result changes:**
- D's `n05` now expects `CJ_FLOAT`, because the unified validator checks the canonical domain before the schema.
- B's `i03` uses the new locator, and the old layout is the new negative `i04`.
- B's `m09` and `m14` were adapted because the synthetic package is about 27 KB instead of 8.7 MB.
- E's strict-zero test date is now 2026-10-07, matching the owner's storage evidence.

**Untested:**
- Real exporter output and real audio/video sniffing.
- Multi-GB archives and filesystem locking.
- Every provider, host, renderer and real CI run.
- The restore drill.
- The freezer, approval engine, plan/apply and CLI, which are not implemented.
- Parity under a pinned Node.

Temporary files are under `/scratch/project_465002727/jelealro/tmp/g1_*`; the clean copy is kept as evidence.

## Follow-up (L-27), 2026-10-07

L-27 is applied in the scaffold, and the full clean-checkout check still passes 446 of 446.

**What changed in the examples**
- **`project.v2` example:** `ai_disclosure` is now `{"text": "All voices in this podcast are AI-generated.", "spoken": true}` and `public_contact_acknowledged` is `true`.
- **Strict-zero ops fixture:** carries the same disclosure wording.
- **Two negative fixtures adjusted** so each still tests only its own rule: pj02 now removes the disclosure, and pj03 sets the acknowledgement back to `false`.

**Wording that has no field in `project.v2`.** The schema has only `text` and `spoken`, so the rest of the owner's wording is recorded outside the record, in `README.md` and in the `AI_DISCLOSURE_NOTE` constant in `tools/build_examples.py`:
- the spoken intro lines in EN, ES and DE;
- the show-description line;
- the last line of every episode description;
- the flag that the ES and DE wording needs a native-speaker check before use.

I did not change the schema, so G3's lock pins against the H2 schemas stay valid. A per-language disclosure field would need a later `project` schema version.

**Other files touched**
- `CLAUDE.md`: agents may set `public_contact_acknowledged: true` only to record an owner decision.
- `VALIDATION.md`: notes the re-run and the L-27 fixture changes.
- `results/check_results.json`: replaced with the new run.

**Verification**
- I regenerated everything with the build tools in a fresh copy at `/scratch/project_465002727/jelealro/tmp/g1_clean/`, run with an empty environment and `HOME=/nonexistent`. The regenerated output is byte-identical to the package.
- `python -m bllt_publish.check --all --node <VS Code Node v24.21.0, unpinned>` passed 446 of 446 and exited 0, including the 2 JavaScript parity cases.

I did not edit or re-read G3's files. The uncounted `info_g3_compat` result still compares against my older copy of G3's lock, taken before its L-26 regeneration, so it will keep showing the old mismatches until that copy is refreshed.

## Follow-up (Agent F findings), 2026-10-07

All of Agent F's findings in my scope are fixed: B1, M1, M2, M5, M6, m2, m3 and m4. The clean-checkout run now passes **535 of 535** cases (was 446), exit 0. It was run with `env -i` and `HOME=/nonexistent`, regeneration was byte-identical, and JS parity ran with the unpinned Node v24.21.0. Re-running F's own adversarial script gives 17 of 18 defended. The remaining "GAP" (F-I03) is an artifact of the script: it expects an exception, while the importer now returns a rejected receipt with `IMPORT_LOCKED` (covered by sc09).

No schema file changed, so G3's regenerated `CONTRACT.lock` (0.2.0-h2) still matches all 35 pinned digests. I only refreshed the read-only copies of G3's files in `tests/fixtures/compat/`.

**Codes renamed to their v2 spelling (docs that cite the old names need updating).** The old names stay in the catalogue as `deprecated` with `replaced_by`:

| Old (first H2 build) | Now |
|---|---|
| `TIMESTAMP_ORDER` (plans only) | `PLAN_EXPIRY_ORDER` |
| `DUPLICATE_ACTION_ID` | `DUPLICATE_ACTION` |
| `OPERATION_TARGET_MISMATCH` | `UNSUPPORTED_OPERATION` |
| `SITE_SET_DUPLICATE_STORY` | `DUPLICATE_SITE_EDITION` |

**B1, v2 rules ported**
- **Project rules** (project.v2):
  - `MULTIPLE_WEBSITES`, `PRIMARY_NOT_SELECTED`, `MODULE_NOT_ENABLED`, `MISSING_ORIGIN`
  - `MULTIPLE_FEED_AUTHORITIES`, `FEED_MODULE_NOT_ENABLED`, `FEED_AUTHORITY_NOT_SELECTED`
  - `ZERO_PROFILE_FORBIDDEN_CAPABILITY`, `PRODUCTION_WRITE_SWITCH_CONFLICT`
- **Carried v1 kinds:**
  - catalog and story: `DUPLICATE_CATALOG_OR_EDITION`
  - rights-review: `DUPLICATE_RIGHTS_COMPONENT`, `INCOMPLETE_RIGHTS_CLEARANCE`
  - collection: `DUPLICATE_COLLECTION_ASSET`, `COLLECTION_MASTER_REFERENCE_MISSING`, `COLLECTION_ORDER_INVALID`, `DUPLICATE_COLLECTION_EPISODE`
- **Release:** channel asset checks (`UNKNOWN_ASSET`/`WRONG_ASSET_ROLE`), `NATIVE_AUDIO_REFERENCE_MISSING`, `SPOTIFY_EPISODE_REFERENCE_MISSING`.
- **Provider registry:** `DUPLICATE_PROVIDER_MAPPING`.
- **Site-set:** `DUPLICATE_SITE_EDITION`, `DUPLICATE_REMOVAL`, `UNSAFE_REMOVAL_PATH`.
- **Plans:** `PLAN_EXPIRY_ORDER`, `DUPLICATE_ACTION`, `UNSUPPORTED_OPERATION`, `EMPTY_PRODUCTION_PLAN`.
- **Generic:** `UNSAFE_URL` on every kind except feed-observation.
- **Web:** `WRONG_EMBED_HOST` (real records only).
- **Readiness:** v2's readiness check is now `validate.readiness_errors()`, with `NOT_A_RELEASE`, `RELEASE_NOT_FROZEN`, `RIGHTS_NOT_CLEARED`, `RIGHTS_RECORD_HASH_MISSING`, `SOURCE_HASH_MISSING`, `CHANNEL_NOT_REQUESTED`, `MISSING_ASSET`, `UNAPPROVED_ASSET`, `PODCAST_ID_MISSING`, `PODCAST_COVER_DIMENSIONS`.
- **New test group `v2_semantics_ported` (35/35):** runs v2's 35 self-test mutations against the successor kinds; code in `tests/v2_selftests.py`.
- **New `DEPRECATED_V2_RULES.md`** lists every v2 rule as ported, adapted or retired. Two adaptations to flag:
  - `FEED_MODULE_NOT_ENABLED` now fires only when an enabled feed module is not the chosen authority's module. Under v2's strict form, the owner's "Spotify decided, module still spec_only" example would have failed.
  - `DUPLICATE_PROVIDER_MAPPING` keys on (entity_type, entity_id, destination, url_kind) for `listed` rows (m3).
- **Retired v2 codes:** `NON_JSON_VALUE`, `SCHEMA`, `PUBLIC_LANGUAGE_PATH_MISMATCH`, `PUBLIC_IMAGE_MISSING`, `PUBLIC_PLAYER_URL_MISMATCH`, `DUPLICATE_PUBLIC_PAGE`; each has a replacement code.
- **`DUPLICATE_REMOVAL` is shadowed by the site-set.v2 schema** (`uniqueItems`), so fixture v2p18 expects `SCHEMA_VIOLATION`.

**Bug found and fixed along the way:** web-bundle.v2 payloads failed the unified validator with `UNSAFE_PATH` on their route paths. They were never in the positive set. Route paths are now exempt, as in v2, and both payloads are positive examples.

**M1:**
- The importer requires an expected digest (`EXPECTED_DIGEST_REQUIRED`).
- The test-only switch `require_expected_digest=False` marks its receipt `example: true`.
- New receipt rule `RECEIPT_DIGEST_SOURCE_REQUIRED`: a non-example `accepted` receipt must have `expected_digest_source: operator-out-of-band`.

**M2:** scenario sc07 places different bytes at the archive's content address and expects `ARCHIVE_STORE_CORRUPT`; nothing is overwritten.

**m2, importer:**
- New `ARCHIVE_MEMBER_PREFIX_COLLISION` (F-I01) and `IMPORT_STATE_CORRUPT` (F-I04).
- `IMPORT_LOCKED` now returns a rejected receipt instead of raising.
- `STATE_ROOT_*` and `ARCHIVE_OUTSIDE_INBOX` refusals write a receipt when the state root is usable.
- New `IMPORT_IO_ERROR` for I/O failures inside the protocol.
- A test asserts that every negative import leaves exactly one receipt.

**m4:** integers longer than 16 digits now give `CJ_INT_RANGE`. This is tested in Python only, not added to the golden JS cases.

**M5, leak scan:**
- New `PUBLIC_TEXT_NOT_UTF8`: a BOM or non-UTF-8 text file is flagged, then decoded and scanned anyway.
- New `PUBLIC_JSON_INVALID`: `.json` files are parsed and their keys checked as data.
- The production-path rule is widened to production story folders (`stories/<slug>/` with an underscore in the slug), `character/` and `work/`.
- E-mail checks now also run on printable strings inside binary files.
- MP4 `udta`/`meta`/`ilst`/`©` atoms are parsed and reported as `PUBLIC_MEDIA_METADATA`.
- HTML-entity-encoded e-mail addresses are caught (F-L05).

**M6, catalogue:** `error-codes.json` now has 433 codes in 24 families, covering:
- The new families `v2-semantics-ported` and `declarative-readiness`.
- A `v2-planned` family (status `planned`): `MODULE_NOT_IMPLEMENTED`, `APPROVAL_MISMATCH`, `SOURCE_CHANGED`, `DUPLICATE_EPISODE`, `REGISTRY_CONFLICT`, `UNKNOWN_REMOTE_RESULT`, `SITE_REMOVAL_NOT_APPROVED`, `RETENTION_REFERENCED_ASSET`, `PRODUCTION_CREDENTIAL_PRESENT`.
- `MASTER_ROOT_UNSET` is now `deprecated`, replaced by `STATE_ROOT_UNSET` (L-26).
- The runner adds a check that no deprecated code is still emitted.

**Counts by group:**

| Group | Result |
|---|---|
| schemas_check_schema | 35/35 |
| positive_examples | 36/36 |
| negative_records | 135/135 |
| negative_raw | 1/1 |
| v2_semantics_ported | 35/35 |
| golden_python | 24/24 |
| negative_imports | 27/27 |
| import_scenarios | 9/9 |
| positive_import | 1/1 |
| import_roots | 8/8 |
| web (6 groups) | 51/51 |
| podcast | 60/60 |
| leak_scan | 44/44 |
| strict_zero | 28/28 |
| ci_lint | 24/24 |
| state_roots | 10/10 |
| handoff_index_scan | 3/3 |
| error_catalogue | 2/2 (249 distinct codes observed) |
| js_parity | 2/2 |

**New fixture and test ids, for the docs to cite:**
- **Record fixtures** (`tests/fixtures/negative/records/`):

  | Fixture | Expected code |
  |---|---|
  | fv01-three-websites-enabled | `MULTIPLE_WEBSITES` |
  | fv02-two-feed-authorities | `MULTIPLE_FEED_AUTHORITIES` |
  | fv03-enabled-feed-not-authority | `FEED_MODULE_NOT_ENABLED` |
  | fv04-production-without-remote-writes | `PRODUCTION_WRITE_SWITCH_CONFLICT` |
  | fv05-rights-cleared-one-component | `INCOMPLETE_RIGHTS_CLEARANCE` |
  | fv06-catalog-duplicate-story | `DUPLICATE_CATALOG_OR_EDITION` |
  | fv07-native-audio-without-asset | `NATIVE_AUDIO_REFERENCE_MISSING` |
  | fv09-registry-two-listed-show-pages | `DUPLICATE_PROVIDER_MAPPING` |
  | v2p01-primary-not-selected | `PRIMARY_NOT_SELECTED` |
  | v2p02-primary-module-not-enabled | `MODULE_NOT_ENABLED` |
  | v2p03-missing-origin | `MISSING_ORIGIN` |
  | v2p04-feed-authority-not-selected | `FEED_AUTHORITY_NOT_SELECTED` |
  | v2p05-zero-cost-commerce | `ZERO_PROFILE_FORBIDDEN_CAPABILITY` |
  | v2p06-story-duplicate-edition | `DUPLICATE_CATALOG_OR_EDITION` |
  | v2p07-duplicate-rights-component | `DUPLICATE_RIGHTS_COMPONENT` |
  | v2p08-collection-duplicate-asset | `DUPLICATE_COLLECTION_ASSET` |
  | v2p09-collection-master-missing | `COLLECTION_MASTER_REFERENCE_MISSING` |
  | v2p10-collection-order-invalid | `COLLECTION_ORDER_INVALID` |
  | v2p11-collection-duplicate-episode | `DUPLICATE_COLLECTION_EPISODE` |
  | v2p12-spotify-player-without-episode | `SPOTIFY_EPISODE_REFERENCE_MISSING` |
  | v2p13-channel-unknown-asset | `UNKNOWN_ASSET` |
  | v2p14-channel-wrong-role | `WRONG_ASSET_ROLE` |
  | v2p15-plan-expiry-order | `PLAN_EXPIRY_ORDER` |
  | v2p16-duplicate-action | `DUPLICATE_ACTION` |
  | v2p17-empty-production-plan | `EMPTY_PRODUCTION_PLAN` |
  | v2p18-duplicate-removal | `SCHEMA_VIOLATION` |
  | v2p19-unsafe-removal-path | `UNSAFE_REMOVAL_PATH` |
  | v2p20-url-with-credentials | `UNSAFE_URL` |
  | v2p21-wrong-embed-host | `WRONG_EMBED_HOST` |
  | rc08-accepted-without-out-of-band-digest | `RECEIPT_DIGEST_SOURCE_REQUIRED` |

  Two existing fixtures changed their expected code: pl06 now expects `UNSUPPORTED_OPERATION` and ss03 expects `DUPLICATE_SITE_EDITION`.
- **Raw fixture:** `negative/raw/fv08-5000-digit-integer` expects `CJ_INT_RANGE`.
- **Import fixtures:** m26-member-prefix-collision (`ARCHIVE_MEMBER_PREFIX_COLLISION`) and m27-no-expected-digest (`EXPECTED_DIGEST_REQUIRED`).
- **Scenarios:**
  - sc07-archive-store-corrupt: `ARCHIVE_STORE_CORRUPT`
  - sc08-corrupt-prior-receipt: `IMPORT_STATE_CORRUPT`
  - sc09-lock-held: `IMPORT_LOCKED`, with a receipt written
- **Leak cases:**

  | Case | Covers | Expected code |
  |---|---|---|
  | L36, L37 | F-L01 | `PUBLIC_TEXT_NOT_UTF8`, `PUBLIC_SECRET_PATTERN` |
  | L38 | F-L02 | `PUBLIC_PRODUCTION_PATH` |
  | L39 | F-L03 | `PUBLIC_PRIVATE_FIELD` |
  | L40, L41 | F-L04 | `PUBLIC_MEDIA_METADATA`, `PUBLIC_EMAIL_NOT_ALLOWLISTED` |
  | L42 | invalid JSON | `PUBLIC_JSON_INVALID` |
  | L43 | F-L05 | `PUBLIC_EMAIL_NOT_ALLOWLISTED` |
- **New import_roots cases:** refusal receipts for unset or unsafe roots, the test-only no-digest switch, and the one-receipt-per-negative-import check.

**Open, for the docs:** collection.v1 assets still carry float `duration_seconds`, which the canonical domain rejects when non-null, so a collection.v2 is needed before collections hold media. show.v1 still has `owner_email`. Both are recorded in `DEPRECATED_V2_RULES.md`. I updated `VALIDATION.md` (counts, the old G3-compat note, Agent F's rerun) and `results/check_results.json`; the five carried v2 examples are vendored with `SOURCES.sha256`.

Files are in `package/publishing-scaffold/`:
- `VALIDATION.md`
- `DEPRECATED_V2_RULES.md`
- `results/check_results.json`
- `publishing/contracts/error-codes.json`