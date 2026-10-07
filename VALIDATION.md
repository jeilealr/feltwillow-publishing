# Validation of the publishing scaffold (contract revision H2)

Run by Agent G1 on LUMI, last on 2026-10-07 after the fixes for Agent F's review (B1, M1, M2, M5, M6, m2, m3,
m4) and the owner decisions L-27, L-28 (reading text authored in publishing) and L-29 (measurement provenance,
lossless audio, ffprobe for video). Full machine-readable result: `results/check_results.json` (copied from
the clean-checkout run below). Nothing was committed, imported, uploaded or deployed.

## Environment

| Item | Value |
|---|---|
| Python | 3.12.9 (unicodedata 15.0.0), isolated venv `/scratch/project_465002727/jelealro/tmp/venv-blueprint` |
| Python packages | PyYAML 6.0.3, jsonschema 4.26.0 (referencing 0.37.0) |
| Node (JS parity only) | v24.21.0, Unicode 17.0: the VS Code server's bundled binary `~/.vscode-server/cli/servers/Stable-07f806f999227108933c2e30515b26eecc1fda74/server/node` (the one Agent B used). **Unpinned, not installed by us; OPEN / PROOF REQUIRED: re-run with a pinned Node (tools/js/README.md).** |

## Clean-checkout run (no production repository, HOME-independent)

The scaffold was copied to a throw-away directory and run with an empty environment (`env -i`, `HOME=/nonexistent`,
`PATH=/usr/bin:/bin`, no `FELTWILLOW_*` variables). No code or fixture reads the production checkout, the v2 package or
`work/agent-*`. Vendored inputs: synthetic PNGs (`tests/fixtures/packages/SOURCES.json` records the b880c23
paths and digests they stand in for), the five carried v2 example YAMLs (`tests/fixtures/v2-carried/source/`,
`SOURCES.sha256`), and read-only copies of G3's selection example and `CONTRACT.lock` (`tests/fixtures/compat/`,
refreshed 2026-10-07 after G3's L-26 regeneration).

```sh
C=/scratch/project_465002727/jelealro/tmp/g1_clean; rm -rf $C; mkdir -p $C
cp -a package/publishing-scaffold $C/feltwillow-publishing; cd $C/feltwillow-publishing
PY=/scratch/project_465002727/jelealro/tmp/venv-blueprint/bin/python
NODE=~/.vscode-server/cli/servers/Stable-07f806f999227108933c2e30515b26eecc1fda74/server/node
E="env -i PATH=/usr/bin:/bin HOME=/nonexistent PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src"
$E $PY tools/build_schemas.py          # wrote 20 H2 schemas and record-types.json
$E $PY tools/build_examples.py         # examples: 24 + web bundles; record negatives: 153 (57 H2, 30 v2-port/F, 18 L-28/L-29); raw: 1; imports: 27; scenarios: 9; podcast negatives: 23
$E $PY tools/build_error_codes.py      # error codes: 442 families: 27
diff -r <scaffold>/publishing publishing && diff -r <scaffold>/tests tests    # regeneration byte-identical
$E $PY -m feltwillow_publish.check --all --tmp $C/check-tmp --node $NODE --report $C/check_results.json
# 555/555 passed; success: True; exit 0
```

## Counts (555 counted cases, all passing)

| Group | Result | What it covers |
|---|---|---|
| schemas_check_schema | 36/36 | 20 H2 schemas (incl. reading-edition.v1) + 16 v2 schemas, Draft 2020-12 meta-check |
| positive_examples | 37/37 | 24 examples (incl. the Lion-and-Mouse reading edition, EXAMPLE ONLY), 2 render-input manifests, 2 web-bundle payloads, 2 strict-zero ops fixtures, synthetic package handoff + allocation, 5 carried v2 examples (catalog, collection, rights-review, show, story) |
| negative_records | 153/153 | 48 from Agent B (adjusted to L-28: Lion handoff assets are the two illustrations) + 57 H2 + 30 v2-port / Agent F (fv01-fv07, fv09, v2p01-v2p21, rc08) + 18 L-28/L-29 (hr01-hr03, re01-re09, ms01-ms06); 3 are positive patch cases |
| negative_raw | 1/1 | fv08: 5000-digit integer -> CJ_INT_RANGE (m4) |
| v2_semantics_ported | 35/35 | the v2 checker's 35 self-test mutations on the H2 successor kinds (`tests/v2_selftests.py`) |
| golden_python | 24/24 | canonical-json golden cases |
| negative_imports | 27/27 | m01-m27 (m26 member prefix collision F-I01; m27 no expected digest F-I02); each rejected, nothing archived |
| import_scenarios | 9/9 | sc01-sc06 + sc07 archive store corrupt (M2), sc08 corrupt prior receipt (F-I04), sc09 lock held (F-I03) |
| positive_import | 1/1 | synthetic Lion h0001 accepted with an out-of-band digest; tar at `FELTWILLOW_MASTER_ROOT/handoffs/<sha256>.tar` |
| import_roots | 8/8 | environment roots (refusals write a receipt when the state root is usable), test-only no-digest switch (receipt marked example), every negative import left exactly one receipt |
| web_* (6 groups) | 51/51 | payload 2+22, render-input 2+9, completeness 5, synthetic site artifact 11 |
| podcast | 60/60 | Agent D's suite |
| leak_scan | 44/44 | E's 36 + L36-L43 (F-L01..F-L05 and invalid JSON) |
| strict_zero | 28/28 | E's 26 + owner inventory + fixture validity |
| ci_lint | 24/24 | E's suite |
| state_roots | 10/10 | `STATE_ROOT_UNSET`/`STATE_ROOT_UNSAFE` |
| handoff_index_scan | 3/3 | IC-E4 |
| error_catalogue | 2/2 | all 257 distinct observed codes catalogued; no deprecated code emitted |
| js_parity | 2/2 | Node: 24 golden cases; 27 record digests identical to Python |

Informational, not counted (`info_g3_compat`): G3's `CONTRACT.lock` (0.2.0-h2) validates as contract-lock.v1, but
L-28/L-29 changed common.v2, production-handoff.v1, release.v2 and handoff-selection.v1 and added reading-edition.v1,
so 4 of its 35 pinned digests now differ and the new schema is not pinned. **G3 must regenerate the lock.** G3's
selection example still has the `reading` component; `tools/build_examples.py` adapts it (`l28_selection`) for the
scaffold's example until G3 updates it.

Agent F's adversarial script (`work/agent-F/adversarial/adversarial_f.py`), re-run against the updated scaffold:
17 of 18 cases defended. The remaining "GAP" (F-I03) is a scripting artifact: the script expects an exception, but
the importer now returns a rejected receipt with `IMPORT_LOCKED` (covered by sc09). F-I01 and F-I04 are refused in
F's script with `EXPECTED_DIGEST_REQUIRED` first (it supplies no digest); m26 and sc08 exercise them with a digest.

## Intentional differences from the agents' original results

- D's `n05-float-duration` expects `CJ_FLOAT` (canonical domain checked before the schema).
- B's `i03` expects the H2 locator `handoffs/<sha256>.tar`; the old layout is `i04`.
- B's `m09`/`m13`/`m14` adapted to the small synthetic package (since L-28 it has no reading-text file: 3 members).
- Imports now require an operator-supplied expected digest (M1); test packages pass the real archive digest.
- Codes restored to v2 spelling: `PLAN_EXPIRY_ORDER`, `DUPLICATE_ACTION`, `UNSUPPORTED_OPERATION`,
  `DUPLICATE_SITE_EDITION` (first-build names are listed as `deprecated` in error-codes.json).
- See `DEPRECATED_V2_RULES.md` for ported, adapted and retired v2 rules.

## Not tested (OPEN / PROOF REQUIRED)

Real exporter output (G3 tests it in its own change set); real WAV/FLAC/MP3/MP4 sniffing; multi-GB archives,
disk-full, network-filesystem locking, stale-lock recovery; renderers, Ghost, hosts and podcast providers; CI on
real runners; restore drill; release freezer, approval-validity engine, plan/apply and CLI (not implemented); JS
parity with a pinned Node (the 5000-digit integer case is tested in Python only); web-bundle.v2 in JavaScript.
The leak scan stays heuristic.
