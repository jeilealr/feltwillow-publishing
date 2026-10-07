"""Import suites (reference importer, Agent B's protocol with the H2 storage layout).

Packages are built from tests/fixtures/packages/lion-h0001-synthetic/ (synthetic PNGs; no production
checkout, no `git show`). State and master roots are throw-away directories under ctx.tmp.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

from feltwillow_publish.contracts import cj1
from feltwillow_publish.imports import importer as I
from support import FIX, apply_patch, case, load_fixture

PKG = FIX / "packages" / "lion-h0001-synthetic"


def base_package():
    handoff = cj1.loads_strict((PKG / "handoff.json").read_bytes())
    files = {}
    for a in handoff["payload"]["assets"]:
        data = (PKG / a["package_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == a["sha256"], a["asset_id"]
        files[a["package_path"]] = data
    return handoff, files


def _info(name, size=0, type_=tarfile.REGTYPE):
    ti = tarfile.TarInfo(name)
    ti.size, ti.type, ti.mtime, ti.mode, ti.uid, ti.gid = size, type_, 0, 0o644, 0, 0
    ti.uname = ti.gname = ""
    return ti


def build_package(dest: Path, mutations, step_payloads=None):
    handoff, files = base_package()
    extra, post, raw_dup = [], [], False
    for m in mutations:
        op = m["op"]
        if op == "patch_handoff":
            handoff = apply_patch(handoff, m["patch"])
        elif op == "make_correction":
            parent = m["parent_payload"]
            if parent.startswith("@step"):
                parent = step_payloads[int(parent[5:])]
            p = handoff["payload"]
            rev = m["revision"]
            p.update(handoff_revision=rev, handoff_id=f"{p['story_id']}.{p['language']}.h{rev:04d}", purpose="correction",
                     reason=f"EXAMPLE ONLY: correction test revision {rev}.",
                     supersedes={"handoff_id": f"{p['story_id']}.{p['language']}.h0001", "payload_sha256": parent})
        elif op == "remove_file":
            if m["name"] == "handoff.json":
                extra.append(("omit_handoff",))
            files.pop(m["name"], None)
        elif op == "replace_file":
            files[m["name"]] = m["data"].encode()
        elif op == "replace_asset_bytes":
            a = handoff["payload"]["assets"][m["asset_index"]]
            data = m["data"].encode()
            files[a["package_path"]] = data
            a["sha256"], a["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
        elif op in ("add_file", "add_symlink", "add_hardlink", "add_special", "duplicate_member"):
            extra.append((op, m))
        elif op in ("compress", "truncate_mid_last_member", "garbage"):
            post.append(m)
        elif op == "raw_handoff_suffix_dup":
            raw_dup = True
        else:
            raise ValueError(op)
    body = json.dumps(handoff, indent=2, ensure_ascii=False).encode("utf-8")
    if raw_dup:
        body = b'{"kind": "production-handoff",' + body[1:]
    buf = io.BytesIO()
    last_member = None
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        if ("omit_handoff",) not in extra:
            tar.addfile(_info("handoff.json", len(body)), io.BytesIO(body))
        for name in sorted(files):
            last_member = (buf.tell(), len(files[name]))
            tar.addfile(_info(name, len(files[name])), io.BytesIO(files[name]))
        for item in extra:
            if item[0] == "omit_handoff":
                continue
            op, m = item
            if op == "add_file":
                d = m["data"].encode()
                tar.addfile(_info(m["name"], len(d)), io.BytesIO(d))
            elif op == "add_symlink":
                ti = _info(m["name"], 0, tarfile.SYMTYPE); ti.linkname = m["target"]; tar.addfile(ti)
            elif op == "add_hardlink":
                ti = _info(m["name"], 0, tarfile.LNKTYPE); ti.linkname = m["target"]; tar.addfile(ti)
            elif op == "add_special":
                tar.addfile(_info(m["name"], 0, tarfile.FIFOTYPE if m["type"] == "fifo" else tarfile.CHRTYPE))
            elif op == "duplicate_member":
                d = files[m["name"]]
                tar.addfile(_info(m["name"], len(d)), io.BytesIO(d))
    data = buf.getvalue()
    for m in post:
        if m["op"] == "compress":
            data = gzip.compress(data, mtime=0)
        elif m["op"] == "truncate_mid_last_member":
            start, size = last_member  # header offset of the last regular member, its data size
            data = data[: start + 512 + size // 2]  # PAX/ustar header block(s) precede the data; cut inside it
        elif m["op"] == "garbage":
            data = hashlib.sha256(b"garbage").digest() * (m["bytes"] // 32)
    dest.write_bytes(data)
    return handoff


def allocations_default():
    alloc = cj1.loads_strict((FIX / "packages" / "story-allocation.lion-and-mouse.json").read_bytes())
    return {"lion-and-mouse": cj1.digest(alloc)}


def run_import(tmp: Path, name, mutations, options, roots=None, step_payloads=None, crash_after=None):
    arc = tmp / f"{name}.tar"
    handoff = build_package(arc, mutations, step_payloads)
    state, master = roots or (tmp / f"state-{name}", tmp / f"master-{name}")
    actual = hashlib.sha256(arc.read_bytes()).hexdigest()
    # The operator's out-of-band digest (M1): the real archive digest unless the fixture overrides or omits it.
    expected = None if options.get("no_expected_digest") else options.get("expected_archive_sha256", actual)
    if options.get("preseed_corrupt_archive"):
        (master / "handoffs").mkdir(parents=True, exist_ok=True)
        (master / "handoffs" / f"{actual}.tar").write_bytes(b"different bytes at the content address")
    if options.get("preseed_corrupt_receipt"):
        (state / "receipts").mkdir(parents=True, exist_ok=True)
        (state / "receipts" / "imp-00000000T000000Z-00000000.json").write_text("{not json")
    if options.get("preseed_lock"):
        state.mkdir(parents=True, exist_ok=True)
        (state / "import.lock").write_text("")
    receipt = I.import_archive(arc, state, master, operator="TEST-OPERATOR",
                               allocations=options.get("allocations", allocations_default()),
                               expected_archive_sha256=expected,
                               limits=options.get("limits"), allow_example=options.get("allow_example", True),
                               crash_after=crash_after)
    return receipt, handoff


def _archives(master: Path):
    return list((master / "handoffs").glob("*.tar")) if (master / "handoffs").exists() else []


def run(ctx):
    tmp = ctx["tmp"] / "imports"
    tmp.mkdir(parents=True)
    res = {"negative_imports": [], "import_scenarios": [], "positive_import": [], "import_roots": []}
    for p in sorted((FIX / "negative" / "imports").glob("*.json")):
        fx = load_fixture(p)
        receipt, _ = run_import(tmp, p.stem, fx["mutations"], fx["options"])
        archived = _archives(tmp / f"master-{p.stem}")
        ok = receipt["outcome"] == "rejected" and fx["expect"] in receipt["errors"] and not receipt["promoted"] and not archived
        res["negative_imports"].append(case(p.stem, ok, expect=fx["expect"], got=receipt["errors"], archived_files=len(archived)))
    for p in sorted((FIX / "scenarios").glob("*.json")):
        fx = load_fixture(p)
        roots = (tmp / f"state-{p.stem}", tmp / f"master-{p.stem}")
        payloads, steps, ok = [], [], True
        for i, st in enumerate(fx["steps"]):
            try:
                receipt, handoff = run_import(tmp, f"{p.stem}-{i}", st["mutations"], st.get("options", {}), roots=roots,
                                              step_payloads=payloads, crash_after=st.get("crash_after"))
                outcome, codes = receipt["outcome"], receipt["errors"]
            except I.SimulatedCrash:
                outcome, codes, handoff = "crash", [], None
            payloads.append(cj1.digest(handoff["payload"]) if handoff else None)
            good = outcome == st["expect_outcome"] and (st.get("expect") is None or st["expect"] in codes)
            ok &= good
            steps.append({"step": i, "outcome": outcome, "errors": codes, "pass": good})
        final = {}
        if "expect_final" in fx:
            receipts = []
            for x in (roots[0] / "receipts").glob("*.json"):
                try:
                    receipts.append(json.loads(x.read_text()))
                except ValueError:
                    pass  # the deliberately corrupt fixture receipt
            final = {"accepted_receipts": sum(r["outcome"] == "accepted" for r in receipts),
                     "archive_files": len(_archives(roots[1])),
                     "staging_left": len(list((roots[0] / "staging").glob("*"))) if (roots[0] / "staging").exists() else 0}
            for k, v in fx["expect_final"].items():
                ok &= final[k] == v
        res["import_scenarios"].append(case(p.stem, ok, got=steps, final=final))
    receipt, _ = run_import(tmp, "positive-lion", [], {})
    arc = _archives(tmp / "master-positive-lion")
    ok = (receipt["outcome"] == "accepted" and receipt["archival_locator"] == f"handoffs/{receipt['archive']['sha256']}.tar"
          and len(arc) == 1 and arc[0].name == receipt["archive"]["sha256"] + ".tar"
          and (tmp / "state-positive-lion" / "receipts").is_dir() and not (tmp / "state-positive-lion" / "archive").exists())
    res["positive_import"].append(case("lion-h0001-synthetic accepted; tar in MASTER_ROOT/handoffs/<sha256>.tar; receipt in STATE_ROOT",
                                       ok, got={"outcome": receipt["outcome"], "errors": receipt["errors"],
                                                "archival_locator": receipt["archival_locator"],
                                                "archive_bytes": receipt["archive"]["bytes"]}))
    # environment-root entry point (DECISIONS_H2 s.2)
    arc_path = tmp / "env-inbox" / "lion.tar"
    arc_path.parent.mkdir()
    build_package(arc_path, [])
    lax = {"lumi_prefixes": ()}  # the test tree lives on LUMI scratch; that rule is tested in test_ops

    digest = hashlib.sha256(arc_path.read_bytes()).hexdigest()

    def env_case(name, env, expect, root_check=None, receipt_expected=None):
        state = Path(env["FELTWILLOW_PUBLISH_STATE_ROOT"]) if env.get("FELTWILLOW_PUBLISH_STATE_ROOT", "").startswith("/") else None
        before = len(list((state / "receipts").glob("*.json"))) if state and (state / "receipts").exists() else 0
        try:
            r = I.import_from_environment(arc_path, operator="TEST-OPERATOR", allocations=allocations_default(),
                                          env=env, root_check=root_check, allow_example=True,
                                          expected_archive_sha256=digest)
            got = [r["outcome"]]
        except I.ImportReject as rej:
            got = rej.codes
        after = len(list((state / "receipts").glob("*.json"))) if state and (state / "receipts").exists() else 0
        ok = expect in got and (receipt_expected is None or (after - before == 1) == receipt_expected)
        res["import_roots"].append(case(name, ok, expect=expect, got=got, receipt_written=after - before))
    good = {"FELTWILLOW_HANDOFF_INBOX": str(arc_path.parent), "FELTWILLOW_MASTER_ROOT": str(tmp / "env-master"),
            "FELTWILLOW_PUBLISH_STATE_ROOT": str(tmp / "env-state")}
    env_case("inbox unset (state root usable: rejection receipt written)",
             {k: v for k, v in good.items() if k != "FELTWILLOW_HANDOFF_INBOX"}, "STATE_ROOT_UNSET", lax, True)
    env_case("master root unset", {k: v for k, v in good.items() if k != "FELTWILLOW_MASTER_ROOT"}, "STATE_ROOT_UNSET", lax)
    env_case("state root on LUMI scratch (default rules)", good, "STATE_ROOT_UNSAFE")
    env_case("state root relative", {**good, "FELTWILLOW_PUBLISH_STATE_ROOT": "state"}, "STATE_ROOT_UNSAFE", lax)
    env_case("archive outside inbox (receipt written)", {**good, "FELTWILLOW_HANDOFF_INBOX": str(tmp / "other-inbox")},
             "ARCHIVE_OUTSIDE_INBOX", lax, True)
    env_case("safe roots accept", good, "accepted", lax, True)
    # M1 test-only switch: no digest accepted only as an example:true receipt (never a real acceptance)
    arc2 = tmp / "test-mode.tar"
    build_package(arc2, [])
    r = I.import_archive(arc2, tmp / "state-test-mode", tmp / "master-test-mode", operator="TEST-OPERATOR",
                         allocations=allocations_default(), allow_example=True, require_expected_digest=False)
    res["import_roots"].append(case("test-only switch: no digest -> accepted receipt marked example:true", r["outcome"] == "accepted"
                                    and r["example"] is True and r["expected_digest_source"] == "not-provided",
                                    got={"outcome": r["outcome"], "example": r["example"]}))
    # every negative import must have left exactly one rejection receipt (m2)
    missing = [p.stem for p in sorted((FIX / "negative" / "imports").glob("*.json"))
               if len(list((tmp / f"state-{p.stem}" / "receipts").glob("*.json"))) != 1]
    res["import_roots"].append(case("every negative import wrote exactly one rejection receipt", not missing, got=missing))
    return res
