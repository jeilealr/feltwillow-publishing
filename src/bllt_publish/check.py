"""One offline runner for every scaffold check (contract revision H2, PROPOSED CONTRACT).

    PYTHONPATH=src python -m bllt_publish.check --all --report results/check_results.json \
        [--tmp DIR] [--node PATH_TO_NODE]

Suites (tests/test_*.py): contracts, imports, web, podcast, ops. Plus two runner-level checks:
  error_catalogue  every code observed in any suite result is listed in publishing/contracts/error-codes.json
  js_parity        only with --node: tools/js/cj1.mjs on the golden cases and on every example record,
                   compared byte-for-byte (digest) with the Python implementation
Needs only this checkout (no production repository, no credentials, no network except the podcast probe
tests' local 127.0.0.1 server). Writes only --report and throw-away files under --tmp (default
build/check-tmp inside this checkout, git-ignored). Exit 0 when every case passes.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITES = ("contracts", "imports", "web", "podcast", "ops")
CODE_RE = re.compile(r"^([A-Z][A-Z0-9]*(?:[_-][A-Z0-9]+)+)(?::|$)")


def _codes_in(value, out: set):
    if isinstance(value, str):
        m = CODE_RE.match(value)
        if m:
            out.add(m.group(1))
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in ("expect", "expected", "got", "errors", "code", "codes", "findings", "problems", "outcome"):
                _codes_in(v, out)
            elif isinstance(v, (dict, list)):
                _codes_in(v, out)
    elif isinstance(value, list):
        for v in value:
            _codes_in(v, out)


def catalogue_check(results) -> list[dict]:
    cat = json.loads((ROOT / "publishing" / "contracts" / "error-codes.json").read_text(encoding="utf-8"))
    known = {c["code"] for c in cat["codes"]}
    patterns = [re.compile(p["regex"]) for p in cat.get("patterns", [])]
    seen: set = set()
    _codes_in(results, seen)
    seen -= {"VALID"}
    missing = sorted(c for c in seen if c not in known and not any(p.match(c) for p in patterns))
    deprecated = sorted(c["code"] for c in cat["codes"] if c["status"] == "deprecated" and c["code"] in seen)
    return [{"case": f"{len(seen)} distinct codes observed in suite results are catalogued", "pass": not missing,
             "got": missing, "observed": len(seen), "catalogued": len(known)},
            {"case": "no deprecated code is emitted any more", "pass": not deprecated, "got": deprecated}]


def js_parity(node: str, tmp: Path) -> list[dict]:
    from .contracts import cj1
    out = []
    golden = ROOT / "tests" / "fixtures" / "golden" / "expected.json"
    p = subprocess.run([node, str(ROOT / "tools" / "js" / "cj1.mjs"), str(golden)], capture_output=True, timeout=120)
    try:
        rep = json.loads(p.stdout)
        out.append({"case": f"golden cases in JavaScript ({rep['runtime']}, Unicode {rep['unicode']})",
                    "pass": p.returncode == 0 and rep["mismatches"] == 0,
                    "got": {"cases": rep["cases"], "mismatches": rep["mismatches"]}})
    except ValueError:
        out.append({"case": "golden cases in JavaScript", "pass": False, "got": p.stderr.decode()[:300]})
    files = sorted((ROOT / "publishing" / "examples").glob("*.json")) + sorted(
        (ROOT / "publishing" / "examples" / "web" / "manifests").glob("*.json"))
    files.append(ROOT / "publishing" / "examples" / "web" / "render-input" / "site-set-0002" / "data" / "web-bundle.json")
    p = subprocess.run([node, str(ROOT / "tools" / "js" / "cj1.mjs"), "--digest", *map(str, files)],
                       capture_output=True, timeout=120)
    js = json.loads(p.stdout)["digests"]
    bad = []
    for f in files:
        v = cj1.loads_strict(f.read_bytes())
        py = {"record": cj1.digest(v), "payload": cj1.digest(v["payload"]) if "payload" in v else None}
        if js.get(str(f)) != py:
            bad.append({"file": f.name, "python": py, "node": js.get(str(f))})
    out.append({"case": f"record digests Python == JavaScript for {len(files)} example records", "pass": not bad, "got": bad})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the offline scaffold checks.")
    ap.add_argument("--all", action="store_true", help="run every suite (default when no --suite is given)")
    ap.add_argument("--suite", action="append", choices=SUITES)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--tmp", type=Path, default=ROOT / "build" / "check-tmp")
    ap.add_argument("--node", help="Node.js binary for the JavaScript canonicalization parity check")
    a = ap.parse_args(argv)
    suites = SUITES if a.all or not a.suite else tuple(a.suite)
    sys.path.insert(0, str(ROOT / "tests"))
    sys.dont_write_bytecode = True
    if a.tmp.exists():
        shutil.rmtree(a.tmp)
    a.tmp.mkdir(parents=True)
    results = {}
    for s in suites:
        mod = importlib.import_module("test_" + s)
        for group, cases in mod.run({"tmp": a.tmp, "root": ROOT}).items():
            results[group] = cases
    if a.all or not a.suite:
        results["error_catalogue"] = catalogue_check(results)
    if a.node:
        results["js_parity"] = js_parity(a.node, a.tmp)
    shutil.rmtree(a.tmp, ignore_errors=True)
    counted = {g: cs for g, cs in results.items() if not g.startswith("info_")}  # info_* groups are not pass/fail
    summary = {g: f"{sum(c['pass'] for c in cs)}/{len(cs)}" for g, cs in counted.items()}
    total = sum(len(cs) for cs in counted.values())
    passed = sum(c["pass"] for cs in counted.values() for c in cs)
    report = {"tool": "bllt_publish.check", "contract_revision": "H2 (PROPOSED CONTRACT)",
              "summary": summary, "totals": {"cases": total, "passed": passed}, "success": passed == total,
              "js_parity_run": bool(a.node),
              "environment": {"python": platform.python_version(), "unicodedata": unicodedata.unidata_version,
                              "jsonschema": importlib.metadata.version("jsonschema"),
                              "pyyaml": importlib.metadata.version("PyYAML")},
              "results": results}
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    print(f"{passed}/{total} passed; success: {report['success']}")
    for g, cs in counted.items():
        for c in cs:
            if not c["pass"]:
                print("FAIL", g, json.dumps(c, ensure_ascii=False)[:400])
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
