"""Contract suites: schema meta-check, positive examples, negative record fixtures, canonical golden cases."""
from __future__ import annotations

import hashlib
import json

from jsonschema import Draft202012Validator

from bllt_publish.contracts import cj1
from bllt_publish.contracts import validate as V
from support import EXAMPLES, FIX, ROOT, apply_patch, case, load_fixture
from v2_selftests import run_v2_selftests


def positive_files():
    files = sorted(EXAMPLES.glob("*.json")) + sorted((EXAMPLES / "web" / "manifests").glob("*.json"))
    files += sorted((FIX / "ops").glob("*.example.json"))
    files += [FIX / "packages" / "lion-h0001-synthetic" / "handoff.json", FIX / "packages" / "story-allocation.lion-and-mouse.json"]
    files += sorted((FIX / "v2-carried").glob("*.example.json"))
    files += sorted((EXAMPLES / "web" / "render-input").glob("*/data/web-bundle.json"))
    return [f for f in files if f.name != "scan-policy.example.json"]


def run(ctx):
    res = {"schemas_check_schema": [], "positive_examples": [], "negative_records": [], "golden_python": []}
    for p in V.schema_files():
        try:
            Draft202012Validator.check_schema(cj1.loads_strict(p.read_bytes()))
            res["schemas_check_schema"].append(case(p.name, True))
        except Exception as exc:  # report, never crash the suite
            res["schemas_check_schema"].append(case(p.name, False, got=str(exc)[:200]))
    for p in positive_files():
        errs = V.validate(cj1.loads_strict(p.read_bytes()))
        res["positive_examples"].append(case(str(p.relative_to(ROOT)), not errs, expect="valid", got=errs))
    for p in sorted((FIX / "negative" / "records").glob("*.json")):
        fx = load_fixture(p)
        base = cj1.loads_strict((ROOT / fx["base"]).read_bytes())
        got = V.codes(V.validate(apply_patch(base, fx["patch"])))
        ok = (got == []) if fx["expect"] == "VALID" else fx["expect"] in got
        res["negative_records"].append(case(p.stem, ok, expect=fx["expect"], got=got, rule=fx.get("rule")))
    res["negative_raw"] = []
    for p in sorted((FIX / "negative" / "raw").glob("*.json")):
        fx = load_fixture(p)
        try:
            cj1.loads_strict(fx["raw_text"].encode("utf-8"))
            got = "accepted"
        except cj1.CanonicalError as e:
            got = e.code
        res["negative_raw"].append(case(p.stem, got == fx["expect"], expect=fx["expect"], got=got))
    res["v2_semantics_ported"] = run_v2_selftests()
    exp = json.loads((FIX / "golden" / "expected.json").read_text(encoding="utf-8"))
    for c in exp["cases"]:
        raw = (FIX / "golden" / c["file"]).read_bytes()
        try:
            out = cj1.canonical_bytes(cj1.loads_strict(raw))
            good = c["expect"] == "ok" and out.hex() == c["canonical_utf8_hex"]
            got = "ok " + hashlib.sha256(out).hexdigest()[:16]
        except cj1.CanonicalError as e:
            good = c["expect"] == "reject" and e.code == c["code"]
            got = e.code
        res["golden_python"].append(case(c["id"], good, expect=c.get("code") or "ok", got=got))
    # informational (not counted): compatibility with Agent G3's production change set
    lock = cj1.loads_strict((FIX / "compat" / "g3-CONTRACT.lock.json").read_bytes())
    ours = {f"schemas/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest() for p in V.schema_files()}
    differ = [f["path"] for f in lock["files"] if ours.get(f["path"]) != f["sha256"]]
    res["info_g3_compat"] = [
        case("G3 example CONTRACT.lock validated as contract-lock.v1 (H2)", True, got=V.codes(V.validate(lock)),
             note="G3's lock regenerated for H2 (0.2.0-h2, with canonicalization), refreshed by the lead 2026-10-07"),
        case("G3 lock pins vs the H2 schema files shipped here", True, got={"pinned": len(lock["files"]), "digest_differs": differ},
             note="G3's lock pins exactly the H2 schema files shipped here"),
    ]
    return res
