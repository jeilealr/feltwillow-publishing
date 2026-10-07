"""Storage-root safety checks (DECISIONS_H2 s.2, IC-A4, IC-E1). PROPOSED CONTRACT; implemented, offline.

Three environment roots, each refused when unsafe:
  FELTWILLOW_HANDOFF_INBOX       incoming handoff tars before import (transient; required for `import`)
  FELTWILLOW_MASTER_ROOT         immutable archived handoff tars (handoffs/<sha256>.tar), masters, final mixes
  FELTWILLOW_PUBLISH_STATE_ROOT  import receipts, publish plans/receipts, locks, feed observations, private evidence

Codes: STATE_ROOT_UNSET (variable missing/empty) and STATE_ROOT_UNSAFE (relative path; inside a Git work
tree; inside the configured OneDrive sync folder; on LUMI scratch/project storage).
Reads only the environment and path metadata (os.stat); never writes. Standard library only.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_VARS = ("FELTWILLOW_HANDOFF_INBOX", "FELTWILLOW_MASTER_ROOT", "FELTWILLOW_PUBLISH_STATE_ROOT")
# LUMI shared file systems (scratch is purged; project/flash are not owner-controlled durable storage).
LUMI_PREFIXES = ("/scratch/", "/pfs/lustre", "/project/", "/projappl/", "/flash/", "/appl/lumi")
ONEDRIVE_VAR = "FELTWILLOW_ONEDRIVE_DIR"  # optional explicit OneDrive sync folder; name-based detection also applies


class StateRootError(Exception):
    def __init__(self, code: str, var: str, reason: str):
        super().__init__(f"{code}: {var}: {reason}")
        self.code, self.var, self.reason = code, var, reason


def _inside_git(p: Path) -> bool:
    for parent in [p, *p.parents]:
        try:
            if (parent / ".git").exists():
                return True
        except OSError:
            return False
    return False


def unsafe_reasons(path: str, *, onedrive_dir: str | None = None, lumi_prefixes=LUMI_PREFIXES) -> list[str]:
    """Return the reasons a root path is unsafe ([] = acceptable). Does not require the path to exist."""
    reasons = []
    p = Path(path)
    if not p.is_absolute():
        return ["relative path"]
    norm = os.path.normpath(str(p))
    resolved = Path(os.path.realpath(norm))
    for cand in {norm, str(resolved)}:
        if any((cand + "/").startswith(pref) for pref in lumi_prefixes):
            reasons.append("on LUMI shared storage")
            break
    parts = [x.lower() for x in resolved.parts]
    if any(x.startswith("onedrive") for x in parts):
        reasons.append("inside a OneDrive folder")
    if onedrive_dir:
        od = Path(os.path.realpath(onedrive_dir))
        if resolved == od or od in resolved.parents:
            reasons.append("inside the configured OneDrive sync folder")
    if _inside_git(resolved):
        reasons.append("inside a Git work tree")
    return sorted(set(reasons))


def check_root(var: str, env=None, **kw) -> Path:
    env = os.environ if env is None else env
    value = env.get(var, "")
    if not value:
        raise StateRootError("STATE_ROOT_UNSET", var, "not set")
    reasons = unsafe_reasons(value, onedrive_dir=env.get(ONEDRIVE_VAR) or None, **kw)
    if reasons:
        raise StateRootError("STATE_ROOT_UNSAFE", var, "; ".join(reasons))
    return Path(os.path.realpath(value))


def check_all(env=None, needed=ROOT_VARS, **kw) -> tuple[dict, list[str]]:
    """Return ({var: Path}, ["CODE: var: reason", ...])."""
    roots, errors = {}, []
    for var in needed:
        try:
            roots[var] = check_root(var, env, **kw)
        except StateRootError as exc:
            errors.append(str(exc))
    return roots, errors
