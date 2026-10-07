"""Private-field scan of the sanitized handoff index `publishing/handoffs/**` (IC-E4). PROPOSED; implemented.

Runs in the untrusted CI tier (no secrets, no network). The index may hold only sanitized import facts
(handoff_id, digests, contract version, receipt id); never tar files and never private handoff fields.

    python -m bllt_publish.ops.handoff_index_scan <publishing/handoffs> [--report out.json]
Exit codes: 0 clean, 1 findings, 2 usage/IO error. Standard library only; never prints a matched secret.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from . import leak_scan

ALLOWED_PRIVATE_LOOKING = {"handoff_id", "receipt_id"}  # identifiers, not private content
FIELD = re.compile(rb"[\"']([A-Za-z_]+)[\"']\s*:")
PRIVATE_KEYS = {"origin", "rights_evidence", "generation_provenance", "editorial_selection", "private_ref",
                "dirty_paths", "source_files", "voice_id", "voice_ids", "archival_locator",
                "expected_archive_sha256", "operator", "approved_by", "reviewer", "worktree", "worktree_state",
                "selection_note", "evidence", "envelope", "payload", "assets"}


def scan(root: Path) -> list[dict]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in sorted(filenames):
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or not name.endswith(".json"):
                out.append({"code": "HANDOFF_INDEX_FORBIDDEN_FILE", "path": rel})
                continue
            data = p.read_bytes()
            for m in FIELD.finditer(data):
                key = m.group(1).decode()
                if key in PRIVATE_KEYS and key not in ALLOWED_PRIVATE_LOOKING:
                    out.append({"code": "HANDOFF_INDEX_PRIVATE_FIELD", "path": rel, "detail": key})
            for label, rx in leak_scan.SECRET_PATTERNS:
                if rx.search(data):
                    out.append({"code": "HANDOFF_INDEX_SECRET", "path": rel, "detail": label})
            if leak_scan.MACHINE_PATH.search(data):
                out.append({"code": "HANDOFF_INDEX_MACHINE_PATH", "path": rel})
            if leak_scan.EMAIL.search(data):
                out.append({"code": "HANDOFF_INDEX_EMAIL", "path": rel})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index_dir")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    root = Path(a.index_dir)
    if not root.is_dir() or root.is_symlink():
        print("index_dir must be a real directory", file=sys.stderr)
        return 2
    f = scan(root)
    out = json.dumps({"tool": "handoff_index_scan", "clean": not f, "findings": f}, indent=1)
    if a.report:
        Path(a.report).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0 if not f else 1


if __name__ == "__main__":
    sys.exit(main())
