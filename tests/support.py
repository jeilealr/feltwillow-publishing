"""Shared helpers for the scaffold test suites (run by `python -m feltwillow_publish.check`)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "publishing" / "examples"


def load_fixture(path: Path):
    def pairs(ps):
        out = {}
        for k, v in ps:
            if k in out:
                raise ValueError("duplicate key in fixture " + k)
            out[k] = v
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def _pointer(doc, path):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]
    parent = doc
    for p in parts[:-1]:
        parent = parent[int(p)] if isinstance(parent, list) else parent[p]
    return parent, parts[-1]


def apply_patch(doc, ops):
    """Minimal JSON-patch (add/replace/remove) used by the negative fixtures."""
    doc = copy.deepcopy(doc)
    for op in ops:
        parent, key = _pointer(doc, op["path"])
        if isinstance(parent, list):
            if op["op"] == "add":
                parent.insert(len(parent) if key == "-" else int(key), op["value"])
            elif op["op"] == "replace":
                parent[int(key)] = op["value"]
            else:
                del parent[int(key)]
        else:
            if op["op"] == "remove":
                del parent[key]
            elif op["op"] == "replace" and key not in parent:
                raise KeyError(op["path"])
            else:
                parent[key] = op["value"]
    return doc


def case(name, ok, expect=None, got=None, **extra):
    out = {"case": name, "pass": bool(ok)}
    if expect is not None:
        out["expect"] = expect
    if got is not None:
        out["got"] = got
    out.update(extra)
    return out
