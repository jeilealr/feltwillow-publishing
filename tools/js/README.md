# JavaScript canonicalization parity (cj1.mjs)

`cj1.mjs` is Agent B's independent JavaScript implementation of **feltwillow-canonical-json-v1** within the safe
domain (own strict parser, duplicate-key rejection, NFC/unassigned/surrogate checks, keys sorted by UTF-16
code units). Standard library only; offline. Copied unchanged from `work/agent-B/tools/cj1.mjs`.

Two modes:

```sh
node tools/js/cj1.mjs tests/fixtures/golden/expected.json          # 24 golden cases; exit 1 on any mismatch
node tools/js/cj1.mjs --digest publishing/examples/*.json          # record + payload digests as JSON
```

The runner does both and compares the digests with Python:

```sh
PYTHONPATH=src python -m feltwillow_publish.check --all --node "$(command -v node)" --report results/check_results.json
```

## Node version (OPEN / PROOF REQUIRED)

Parity was run with the Node binary bundled with the VS Code server on LUMI (v24.21.0, Unicode 17.0),
**unpinned** and not installed by us. Before acceptance, re-run with a pinned Node in the publishing repo:

1. Choose an even-major LTS (for example the version Astro requires, Node >= 22.12) and record it in
   `.nvmrc` / `.node-version` (not created here: no Node toolchain is part of the scaffold yet).
2. Run the two commands above; both must exit 0 and the runner's `js_parity` group must pass.
3. Record the exact `node --version` and `process.versions.unicode` in `VALIDATION.md`.

Unicode-version note: the safe domain rejects code points that are unassigned in Python's Unicode database
(15.0 in Python 3.12), so a newer Node Unicode version cannot change an NFC verdict for accepted input.
