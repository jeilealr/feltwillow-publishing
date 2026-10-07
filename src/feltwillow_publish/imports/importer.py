"""Reference import protocol for production handoff packages (contract revision H2).

PROPOSED CONTRACT. Reference implementation (Agent B's h1_import.py) moved into feltwillow_publish.imports and
changed for DECISIONS_H2 s.2: archives go to FELTWILLOW_MASTER_ROOT, operational state to FELTWILLOW_PUBLISH_STATE_ROOT.
Status: implemented and tested offline only. Agents never run an import against real state (L-09); the
owner/operator does. No network access of any kind; package content is treated as data only.

Layout (both roots owner-controlled, outside Git, outside OneDrive sync, not on LUMI scratch; checked by
feltwillow_publish.ops.state_roots before a real import):
  $FELTWILLOW_PUBLISH_STATE_ROOT/import.lock                 single-importer lock (O_EXCL)
  $FELTWILLOW_PUBLISH_STATE_ROOT/staging/<random>/           disposable extraction area
  $FELTWILLOW_PUBLISH_STATE_ROOT/receipts/<receipt_id>.json  append-only receipts (the commit point)
  $FELTWILLOW_MASTER_ROOT/handoffs/<archive_sha256>.tar      immutable archived package (0444)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import struct
import tarfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import cj1
from ..contracts import validate as h1_contracts

CONSUMER_SUPPORTS = sorted(h1_contracts.SUPPORTED["production-handoff"])
TOOL = {"tool": "feltwillow_publish.imports.importer (reference)", "tool_version": "0.2.0-h2", "publishing_commit": None}
DEFAULT_LIMITS = {
    "max_archive_bytes": 64 * 2**30,
    "max_members": 10000,
    "max_member_bytes": 32 * 2**30,
    "max_total_bytes": 64 * 2**30,
    "max_handoff_json_bytes": 8 * 2**20,
    "max_name_length": 200,
}
MEMBER_RE = re.compile(r"^(handoff\.json|files|files/[a-z0-9]+(?:-[a-z0-9]+)*|files/[a-z0-9]+(?:-[a-z0-9]+)*/[A-Za-z0-9][A-Za-z0-9_.-]{0,127})$")
COMPRESSED_MAGIC = {b"\x1f\x8b": "gzip", b"BZh": "bzip2", b"\xfd7zXZ\x00": "xz", b"\x28\xb5\x2f\xfd": "zstd",
                    b"PK\x03\x04": "zip", b"7z\xbc\xaf\x27\x1c": "7z"}


class ImportReject(Exception):
    def __init__(self, codes):
        super().__init__(", ".join(codes))
        self.codes = list(codes)


class SimulatedCrash(Exception):
    """Test hook: abort between two protocol steps as a power cut would."""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha_file(path: Path):
    h, n = hashlib.sha256(), 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def sniff_ok(media_type: str, data_head: bytes, full_path: Path) -> bool:
    h = data_head
    if media_type == "image/png":
        return h[:8] == b"\x89PNG\r\n\x1a\n"
    if media_type == "image/jpeg":
        return h[:3] == b"\xff\xd8\xff"
    if media_type == "image/webp":
        return h[:4] == b"RIFF" and h[8:12] == b"WEBP"
    if media_type == "audio/wav":
        return h[:4] == b"RIFF" and h[8:12] == b"WAVE"
    if media_type == "audio/flac":
        return h[:4] == b"fLaC"
    if media_type == "audio/mpeg":
        return h[:3] == b"ID3" or (len(h) > 1 and h[0] == 0xFF and (h[1] & 0xE0) == 0xE0)
    if media_type in ("audio/mp4", "video/mp4", "video/quicktime"):
        return h[4:8] in (b"ftyp", b"moov", b"wide", b"mdat")
    if media_type in ("text/plain", "text/vtt", "application/json", "application/vnd.feltwillow.reading-blocks+json"):
        data = full_path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        if "\x00" in text or not unicodedata.is_normalized("NFC", text):
            return False
        if media_type == "text/vtt":
            return text.startswith("WEBVTT")
        if media_type.endswith("json"):
            try:
                return isinstance(cj1.loads_strict(data), dict)
            except cj1.CanonicalError:
                return False
        return True
    return False


def png_dimensions(head: bytes):
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        return struct.unpack(">II", head[16:24])
    return None


def inspect_members(tar: tarfile.TarFile, archive_bytes: int, limits) -> list:
    """Structural checks on every member BEFORE anything is written."""
    errs, seen, folded, total, count = [], set(), set(), 0, 0
    members = []
    try:
        for m in tar:
            count += 1
            if count > limits["max_members"]:
                raise ImportReject(["ARCHIVE_TOO_MANY_MEMBERS"])
            members.append(m)
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ImportReject(["ARCHIVE_MALFORMED"]) from exc
    if not members:
        raise ImportReject(["ARCHIVE_MALFORMED"])
    for m in members:
        name = m.name
        if (len(name) > limits["max_name_length"] or not MEMBER_RE.match(name)
                or not unicodedata.is_normalized("NFC", name)):
            errs.append("ARCHIVE_UNSAFE_PATH")
        if m.issym() or m.islnk():
            errs.append("ARCHIVE_LINK_FORBIDDEN")
        elif m.ischr() or m.isblk() or m.isfifo() or m.issparse() or not (m.isreg() or m.isdir()):
            errs.append("ARCHIVE_SPECIAL_FILE")
        if m.isdir() and name not in ("files",) and name.count("/") != 1:
            errs.append("ARCHIVE_UNSAFE_PATH")
        if name in seen:
            errs.append("ARCHIVE_DUPLICATE_MEMBER")
        elif name.casefold() in folded:
            errs.append("ARCHIVE_CASE_COLLISION")
        seen.add(name)
        folded.add(name.casefold())
        if m.isreg():
            if m.size > limits["max_member_bytes"]:
                errs.append("ARCHIVE_SIZE_LIMIT")
            total += m.size
    if total > limits["max_total_bytes"] or total > archive_bytes:
        errs.append("ARCHIVE_SIZE_LIMIT")
    regular = {m.name for m in members if m.isreg()}
    for name in seen:  # a regular member used as a directory of another member (F-I01)
        parts = name.split("/")
        if any("/".join(parts[:i]) in regular for i in range(1, len(parts))):
            errs.append("ARCHIVE_MEMBER_PREFIX_COLLISION")
    if errs:
        raise ImportReject(sorted(set(errs)))
    return members


def stage(tar, members, staging: Path):
    """Write regular files with O_EXCL|O_NOFOLLOW; never trust archive modes/owners/links."""
    for m in members:
        if m.isdir():
            continue
        dest = staging / m.name
        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not dest.parent.resolve().is_relative_to(staging.resolve()):
            raise ImportReject(["ARCHIVE_UNSAFE_PATH"])
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        written = 0
        try:
            src = tar.extractfile(m)
            with os.fdopen(fd, "wb") as out:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > m.size:
                        raise ImportReject(["ARCHIVE_SIZE_LIMIT"])
                    out.write(chunk)
        except (tarfile.TarError, EOFError, OSError) as exc:
            raise ImportReject(["ARCHIVE_MALFORMED"]) from exc
        if written != m.size:
            raise ImportReject(["ARCHIVE_MALFORMED"])


def _receipts(state_root: Path):
    out = []
    for p in sorted((state_root / "receipts").glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError, OSError):
            raise ImportReject(["IMPORT_STATE_CORRUPT"]) from None
        if not isinstance(r, dict) or r.get("kind") != "import-receipt" or not isinstance(r.get("outcome"), str):
            raise ImportReject(["IMPORT_STATE_CORRUPT"])
        out.append(r)
    return out


def _write_atomic(path: Path, data: bytes, mode=0o444):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp-" + secrets.token_hex(4))
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def import_archive(archive: Path, state_root: Path, master_root: Path, *, operator: str, allocations: dict,
                   expected_archive_sha256: str | None = None, limits: dict | None = None,
                   allow_example: bool = False, crash_after: str | None = None,
                   require_expected_digest: bool = True) -> dict:
    """Import one package. `require_expected_digest=False` is a TEST-ONLY switch: such a receipt is marked
    example:true, because an accepted real import needs an operator-supplied out-of-band digest (M1)."""
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    state_root.mkdir(parents=True, exist_ok=True)
    receipt = _new_receipt(operator, expected_archive_sha256)
    if not require_expected_digest:
        receipt["example"] = True
    lock = state_root / "import.lock"
    try:
        lock_fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return reject_without_import(state_root, ["IMPORT_LOCKED"], archive, receipt)
    staging_ref = [None]  # set by _import_locked once the private staging copy exists
    crashed = False
    try:
        return _import_locked(archive, state_root, master_root, receipt, limits, allocations,
                              expected_archive_sha256, allow_example, crash_after, require_expected_digest,
                              staging_ref)
    except SimulatedCrash:
        crashed = True
        raise
    finally:
        staging = staging_ref[0]
        if staging is not None and not crashed:
            shutil.rmtree(staging.parent, ignore_errors=True)
        os.close(lock_fd)
        os.unlink(lock)


def _new_receipt(operator, expected_archive_sha256):
    staged_at = _now()
    return {"kind": "import-receipt", "schema_version": 1, "example": False, "canonicalization": cj1.ALGORITHM_ID,
               "receipt_id": "imp-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4),
               "outcome": "rejected", "errors": [], "handoff_id": None,
               "archive": {"sha256": "0" * 64, "bytes": 1},
               "expected_archive_sha256": expected_archive_sha256,
               "expected_digest_source": "operator-out-of-band" if expected_archive_sha256 else "not-provided",
               "record_sha256": None, "payload_sha256": None, "schema_version_seen": None, "supersedes": None,
               "consumer_supports": CONSUMER_SUPPORTS, "duplicate_of": None, "archival_locator": None,
               "promoted": False, "staged_at": staged_at, "finished_at": staged_at, "operator": operator,
               "importer": TOOL, "authorizes_publication": False}


def _hash_file(path: Path, limit: int):
    try:
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            return None
        return _sha_file(path)
    except OSError:
        return None


def reject_without_import(state_root: Path, codes, archive: Path | None, receipt: dict) -> dict:
    """Record a refusal that happened before the protocol could start (lock held, unsafe roots)."""
    got = _hash_file(Path(archive), DEFAULT_LIMITS["max_archive_bytes"]) if archive is not None else None
    if got:
        receipt["archive"] = {"sha256": got[0], "bytes": max(got[1], 1)}
    receipt.update(errors=sorted(set(codes)), outcome="rejected", promoted=False, archival_locator=None)
    _persist(state_root, receipt)
    return receipt


def _import_locked(archive, state_root, master_root, receipt, limits, allocations, expected_archive_sha256,
                   allow_example, crash_after, require_expected_digest, staging_ref):
    staging = None
    try:
        # Sweep stale staging left by an interrupted earlier run (we hold the lock).
        shutil.rmtree(state_root / "staging", ignore_errors=True)
        st = os.lstat(archive)
        if not stat.S_ISREG(st.st_mode):
            raise ImportReject(["ARCHIVE_MALFORMED"])
        if st.st_size > limits["max_archive_bytes"]:
            raise ImportReject(["ARCHIVE_SIZE_LIMIT"])
        # Copy once into staging while hashing; every later step reads only this private copy,
        # so a source file changed during the import cannot differ from what was hashed.
        staging = state_root / "staging" / secrets.token_hex(8)
        staging.mkdir(parents=True, mode=0o700)
        staging_ref[0] = staging
        held = staging.parent / (staging.name + ".archive")
        h, size = hashlib.sha256(), 0
        with open(archive, "rb") as src, open(held, "xb") as dst:
            for chunk in iter(lambda: src.read(1 << 20), b""):
                size += len(chunk)
                if size > limits["max_archive_bytes"]:
                    raise ImportReject(["ARCHIVE_SIZE_LIMIT"])
                h.update(chunk)
                dst.write(chunk)
        sha = h.hexdigest()
        archive = held
        receipt["archive"] = {"sha256": sha, "bytes": max(size, 1)}
        if expected_archive_sha256 is None and require_expected_digest:
            raise ImportReject(["EXPECTED_DIGEST_REQUIRED"])  # M1: trust boundary (ch21)
        if expected_archive_sha256 and expected_archive_sha256 != sha:
            raise ImportReject(["ARCHIVE_DIGEST_MISMATCH"])
        with open(archive, "rb") as f:
            head = f.read(512)
        for magic, _name in COMPRESSED_MAGIC.items():
            if head.startswith(magic):
                raise ImportReject(["ARCHIVE_FORMAT_UNSUPPORTED"])
        if len(head) < 512 or head[257:262] != b"ustar":
            raise ImportReject(["ARCHIVE_MALFORMED"])
        try:
            tar = tarfile.open(archive, mode="r:")
        except (tarfile.TarError, OSError) as exc:
            raise ImportReject(["ARCHIVE_MALFORMED"]) from exc
        with tar:
            members = inspect_members(tar, size, limits)
            names = {m.name for m in members if m.isreg()}
            if "handoff.json" not in names:
                raise ImportReject(["HANDOFF_RECORD_MISSING"])
            if next(m for m in members if m.name == "handoff.json").size > limits["max_handoff_json_bytes"]:
                raise ImportReject(["ARCHIVE_SIZE_LIMIT"])
            stage(tar, members, staging)
        if crash_after == "staging":
            raise SimulatedCrash()
        raw = (staging / "handoff.json").read_bytes()
        try:
            record = cj1.loads_strict(raw)
        except cj1.CanonicalError as exc:
            raise ImportReject([exc.code]) from None
        if isinstance(record, dict):
            receipt["schema_version_seen"] = record.get("schema_version") if isinstance(record.get("schema_version"), int) else None
        errs = h1_contracts.validate(record)
        if errs:
            raise ImportReject(sorted({e.split(":")[0] for e in errs}))
        p = record["payload"]
        receipt["handoff_id"] = p["handoff_id"]
        receipt["record_sha256"] = cj1.digest(record)
        receipt["payload_sha256"] = payload = cj1.digest(p)
        receipt["supersedes"] = p["supersedes"]
        codes = []
        if record["example"] and not allow_example:
            codes.append("EXAMPLE_RECORD")
        if allocations.get(p["story_id"]) != p["story_allocation_sha256"]:
            codes.append("STORY_NOT_ALLOCATED")
        declared = {a["package_path"]: a for a in p["assets"]}
        actual = {n for n in names if n != "handoff.json"}
        if declared.keys() - actual:
            codes.append("MISSING_BYTES")
        if actual - declared.keys():
            codes.append("UNEXPECTED_FILE")
        for path in sorted(declared.keys() & actual):
            a = declared[path]
            fsha, fbytes = _sha_file(staging / path)
            if fbytes != a["bytes"]:
                codes.append("SIZE_MISMATCH")
            if fsha != a["sha256"]:
                codes.append("HASH_MISMATCH")
                continue
            with open(staging / path, "rb") as f:
                fhead = f.read(64)
            if not sniff_ok(a["media_type"], fhead, staging / path):
                codes.append("MEDIA_TYPE_MISMATCH")
            dims = png_dimensions(fhead) if a["media_type"] == "image/png" else None
            if dims and dims != (a["measured"]["width_px"], a["measured"]["height_px"]):
                codes.append("MEASUREMENT_MISMATCH")
        if codes:
            raise ImportReject(sorted(set(codes)))
        # Reconciliation against durable receipts.
        accepted = [r for r in _receipts(state_root) if r["outcome"] == "accepted"]
        same = [r for r in accepted if r["handoff_id"] == p["handoff_id"]]
        if same:
            if same[0]["payload_sha256"] == payload:
                receipt.update(outcome="duplicate-identical", duplicate_of=same[0]["receipt_id"])
                _persist(state_root, receipt)
                return receipt
            raise ImportReject(["HANDOFF_REVISION_CONFLICT"])
        if p["supersedes"] is not None:
            parent = [r for r in accepted if r["handoff_id"] == p["supersedes"]["handoff_id"]
                      and r["payload_sha256"] == p["supersedes"]["payload_sha256"]]
            if not parent:
                raise ImportReject(["SUPERSEDES_UNKNOWN"])
            if any(r["supersedes"] == p["supersedes"] for r in accepted):
                raise ImportReject(["HANDOFF_FORK"])
        # Immutable archival copy (content-addressed; an identical earlier copy is reused).
        rel = f"handoffs/{sha}.tar"  # relative to FELTWILLOW_MASTER_ROOT (DECISIONS_H2 s.2)
        dest = master_root / rel
        if dest.exists():
            if _sha_file(dest)[0] != sha:
                raise ImportReject(["ARCHIVE_STORE_CORRUPT"])
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name("." + dest.name + ".tmp-" + secrets.token_hex(4))
            shutil.copyfile(archive, tmp)
            with open(tmp, "rb") as f:
                os.fsync(f.fileno())
            os.chmod(tmp, 0o444)
            os.replace(tmp, dest)
        if crash_after == "archive":
            raise SimulatedCrash()
        receipt.update(outcome="accepted", archival_locator=rel, promoted=True)
        _persist(state_root, receipt)
        return receipt
    except ImportReject as rej:
        receipt.update(errors=rej.codes, outcome="rejected", promoted=False, archival_locator=None)
        _persist(state_root, receipt)
        return receipt
    except OSError:
        # I/O failure inside the protocol (disk full, permission): nothing promoted; record it if possible.
        receipt.update(errors=["IMPORT_IO_ERROR"], outcome="rejected", promoted=False, archival_locator=None)
        _persist(state_root, receipt)
        return receipt


def _persist(state_root: Path, receipt: dict):
    """Write the receipt: the commit point of an import attempt (append-only, atomic)."""
    receipt["finished_at"] = _now()
    errs = h1_contracts.validate(receipt)
    if errs:
        raise RuntimeError("receipt self-check failed: " + "; ".join(errs))
    _write_atomic(state_root / "receipts" / (receipt["receipt_id"] + ".json"),
                  (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def import_from_environment(archive: Path, *, operator: str, allocations: dict, env=None,
                            root_check: dict | None = None, **kw) -> dict:
    """Operator entry point (planned CLI `feltwillow-publish import`): resolve and check the three roots first.

    Refuses with ImportReject(["STATE_ROOT_UNSET"|"STATE_ROOT_UNSAFE", ...]) before touching anything, and
    with ARCHIVE_OUTSIDE_INBOX when the package is not inside FELTWILLOW_HANDOFF_INBOX. Never run by agents (L-09).
    """
    from ..ops import state_roots
    roots, errors = state_roots.check_all(env, **(root_check or {}))
    codes = sorted({e.split(":")[0] for e in errors})
    real = Path(os.path.realpath(archive))
    if not errors and roots["FELTWILLOW_HANDOFF_INBOX"] not in real.parents:
        codes = ["ARCHIVE_OUTSIDE_INBOX"]
    if codes:
        state = roots.get("FELTWILLOW_PUBLISH_STATE_ROOT")
        if state is not None:  # the state root itself is usable: the refusal leaves a receipt (m2)
            state.mkdir(parents=True, exist_ok=True)
            reject_without_import(state, codes, real, _new_receipt(operator, kw.get("expected_archive_sha256")))
        raise ImportReject(codes)
    return import_archive(real, roots["FELTWILLOW_PUBLISH_STATE_ROOT"], roots["FELTWILLOW_MASTER_ROOT"],
                          operator=operator, allocations=allocations, **kw)
