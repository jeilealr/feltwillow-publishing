#!/usr/bin/env python3
"""Content-level leakage scan of a built public bundle (Agent E; integrated as bllt_publish.ops.leak_scan, H2).

Complements Agent B's PUBLIC_FORBIDDEN_FILE check (file *names* in a public-bundle-manifest) with checks
of file *contents* and of the directory that will actually be uploaded.

    python -m bllt_publish.ops.leak_scan <bundle_dir> --manifest <public-bundle-manifest.json>
        [--policy <scan-policy.json>] [--report <out.json>]

Standard library only. Offline: no network, no subprocess, reads only <bundle_dir>, the manifest and the
policy; writes only --report. Never prints a matched secret: findings carry a redacted preview.

Heuristic by nature: a clean result means "none of the listed patterns matched", not "nothing private is
present". The owner's private denylist (voice IDs, private e-mail, machine names) is supplied at run time
from the private state store and is never committed (see E-05 section 3).
Exit codes: 0 clean, 1 findings, 2 usage/IO error.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import os
import re
import stat
import struct
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

TEXT_TYPES = {"text/html", "text/css", "application/javascript", "application/json", "application/xml",
              "text/plain", "text/vtt", "image/svg+xml", "application/rss+xml", "application/manifest+json"}
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".xml", ".txt", ".vtt", ".srt", ".svg",
                 ".rss", ".webmanifest", ".md"}

# File-name rules (superset of Agent B's PUBLIC_FORBIDDEN regex; kept in sync by an interface request).
FORBIDDEN_NAME = re.compile(
    r"(^|/)(\.git|\.github|\.env[^/]*|\.ssh|\.aws|\.config|functions|_worker\.js|_routes\.json|node_modules"
    r"|__pycache__|\.DS_Store|Thumbs\.db|\.npmrc|\.netrc|\.htpasswd|id_rsa[^/]*|id_ed25519[^/]*)(/|$)"
    r"|\.(ya?ml|py|pyc|sh|bash|tar|zip|7z|gz|wav|flac|aif|aiff|mov|drp|drt|dra|log|pem|key|p12|pfx|sqlite|db"
    r"|bak|orig|swp|map)$"
    r"|(^|/)[^/]*(handoff|receipt|approval|manifest|publish-plan|provider-registry|rights-review|contract-lock"
    r"|story-allocation|service-inventory|release\.v\d)[^/]*\.json$", re.I)

SECRET_PATTERNS = [
    ("google-api-key", re.compile(rb"AIza[0-9A-Za-z_\-]{35}")),
    ("openai-key", re.compile(rb"sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,}")),
    ("huggingface-token", re.compile(rb"hf_[A-Za-z0-9]{30,}")),
    ("github-token", re.compile(rb"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}")),
    ("aws-access-key", re.compile(rb"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("private-key-block", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("slack-token", re.compile(rb"xox[abprs]-[0-9A-Za-z\-]{10,}")),
    ("elevenlabs-key", re.compile(rb"\bsk_[0-9a-f]{40,}\b")),
    ("cloudflare-token-assignment", re.compile(rb"(?i)(?:CLOUDFLARE|CF)_API_TOKEN\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}")),
    ("generic-secret-assignment", re.compile(
        rb"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[\"']?\s*[=:]\s*[\"'][^\"'\s]{12,}[\"']")),
    ("jwt", re.compile(rb"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
]
MACHINE_PATH = re.compile(
    rb"(?:file://|(?<![A-Za-z0-9_.])/(?:scratch|pfs|project|users|home|Users|Volumes|private/var|var/folders|tmp|mnt)/"
    rb"|\b[A-Za-z]:\\\\?(?:Users|Documents)|~/(?:\.config|Library|Desktop|Documents))")
# Production-repository provenance paths (REPO b880c23 layout): stories/<slug>/..., character/..., work/...
PRODUCTION_PATH = re.compile(
    rb"(?<![A-Za-z0-9_/.-])(?:stories/[a-z0-9_]+/(?:story\.ya?ml|dialogue_coverage\.json|prompt_manifest\.json"
    rb"|runtime_inputs\.json|voices?\.ya?ml)|character/(?:characters|locations)/|work/stories/|voice/(?:cast|narrators)/"
    rb"|lumi/[a-z_]+\.(?:sh|py)|bllt/paths\.py"
    # H2 (M5): any production story folder (slugs contain '_', public slugs never do), character/ and work/
    rb"|stories/[a-z0-9]+_[a-z0-9_]*/|character/|work/)")
# private JSON keys checked on parsed JSON (H2, M5): escapes such as "voice\u005fid" cannot hide a key
PRIVATE_KEYS = {"origin", "rights_evidence", "generation_provenance", "editorial_selection", "private_ref",
                "dirty_paths", "source_files", "voice_id", "voice_ids", "handoff_id", "receipt_id",
                "archival_locator", "expected_archive_sha256", "operator", "approved_by", "reviewer",
                "subject_sha256", "worktree_state", "customer", "subscriber", "billing"}
TEXT_BOMS = [(b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")]
MP4_CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"udta", b"meta", b"ilst"}
PRIVATE_FIELD = re.compile(
    rb"[\"'](?:origin|rights_evidence|generation_provenance|editorial_selection|private_ref|dirty_paths|"
    rb"source_files|voice_id|voice_ids|handoff_id|receipt_id|archival_locator|expected_archive_sha256|"
    rb"operator|approved_by|reviewer|subject_sha256|worktree_state|customer|subscriber|billing)[\"']\s*:")
PLACEHOLDER = re.compile(rb"(?i)EXAMPLE ONLY|example\.invalid|lorem ipsum|\bTODO\b|\bFIXME\b|\"example\"\s*:\s*true"
                         rb"|PLACEHOLDER|\bTBD\b")
EMAIL = re.compile(rb"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL = re.compile(rb"(?i)\b(?:https?|ftp|wss?)://[^\s\"'<>()\\]+")
SIGNED_QUERY = re.compile(r"(?i)(?:^|[?&])(?:x-amz-signature|x-amz-credential|signature|sig|se|sv|token|"
                          r"access_token|auth|key|apikey|api_key|expires|x-goog-signature)=")
EXEC_MAGIC = [(b"\x7fELF", "elf"), (b"MZ", "pe"), (b"\xcf\xfa\xed\xfe", "mach-o"), (b"\xca\xfe\xba\xbe", "mach-o-fat"),
              (b"#!", "shebang")]
MAX_SCAN_BYTES = 256 * 1024 * 1024


def redact(b: bytes) -> str:
    s = b.decode("utf-8", "replace")
    return (s[:4] + "…" if len(s) > 4 else s) + f" ({len(s)} chars)"


class Scan:
    def __init__(self, root: Path, manifest: dict, policy: dict):
        self.root, self.manifest, self.policy = root, manifest, policy
        self.findings: list[dict] = []
        self.allowed_hosts = {h.lower() for h in policy.get("allowed_url_hosts", [])}
        self.allowed_emails = {e.lower() for e in policy.get("allowed_emails", [])}
        self.deny_terms = [t for t in policy.get("deny_terms", []) if t]
        self.allow_placeholders = bool(policy.get("allow_placeholders", False))

    def add(self, code: str, path: str, detail: str = "", line: int | None = None):
        f = {"code": code, "path": path}
        if line is not None:
            f["line"] = line
        if detail:
            f["detail"] = detail
        self.findings.append(f)

    # 1. inventory: the uploaded directory must equal the manifest exactly
    def inventory(self) -> dict[str, dict]:
        declared = {f["path"]: f for f in self.manifest.get("files", [])}
        on_disk: dict[str, Path] = {}
        for dirpath, dirnames, filenames in os.walk(self.root, followlinks=False):
            for name in dirnames + filenames:
                p = Path(dirpath) / name
                rel = p.relative_to(self.root).as_posix()
                st = os.lstat(p)
                if stat.S_ISLNK(st.st_mode):
                    self.add("PUBLIC_LINK_FORBIDDEN", rel)
                    continue
                if name in dirnames:
                    if FORBIDDEN_NAME.search(rel + "/"):
                        self.add("PUBLIC_FORBIDDEN_FILE", rel + "/")
                    continue
                if not stat.S_ISREG(st.st_mode):
                    self.add("PUBLIC_SPECIAL_FILE", rel)
                    continue
                if st.st_mode & 0o111:
                    self.add("PUBLIC_EXECUTABLE_MODE", rel)
                if unicodedata.normalize("NFC", rel) != rel or not rel.isascii():
                    self.add("PUBLIC_NONASCII_PATH", rel)
                on_disk[rel] = p
        for rel in sorted(set(on_disk) - set(declared)):
            self.add("BUNDLE_UNDECLARED_FILE", rel)
        for rel in sorted(set(declared) - set(on_disk)):
            self.add("BUNDLE_MISSING_FILE", rel)
        for rel in sorted(set(declared) | set(on_disk)):
            if FORBIDDEN_NAME.search(rel):
                self.add("PUBLIC_FORBIDDEN_FILE", rel)
        return {rel: {"path": on_disk[rel], "decl": declared.get(rel)} for rel in on_disk}

    def check_file(self, rel: str, path: Path, decl: dict | None):
        size = path.stat().st_size
        if size > MAX_SCAN_BYTES:
            self.add("PUBLIC_FILE_TOO_LARGE_TO_SCAN", rel, str(size))
            return
        data = path.read_bytes()
        if decl is not None:
            if decl.get("bytes") != len(data):
                self.add("BUNDLE_SIZE_MISMATCH", rel)
            if decl.get("sha256") != hashlib.sha256(data).hexdigest():
                self.add("BUNDLE_HASH_MISMATCH", rel)
        for magic, kind in EXEC_MAGIC:
            if data.startswith(magic):
                self.add("PUBLIC_EXECUTABLE_CONTENT", rel, kind)
                break
        media_type = (decl or {}).get("media_type", "")
        is_text = media_type in TEXT_TYPES or Path(rel).suffix.lower() in TEXT_SUFFIXES
        if is_text:
            decoded = self.text_bytes(rel, data)
            self.scan_bytes(rel, decoded, text=True)
            if rel.lower().endswith(".json") or media_type == "application/json":
                self.json_keys(rel, decoded)
        else:
            self.media_metadata(rel, data)
            self.scan_bytes(rel, b"\n".join(re.findall(rb"[\x20-\x7e]{8,}", data)), text=False)

    def text_bytes(self, rel: str, data: bytes) -> bytes:
        """Public text must be plain UTF-8 without BOM (H2, M5). Other encodings are flagged AND decoded,
        so the content checks still see what a browser would show."""
        for bom, codec in TEXT_BOMS:
            if data.startswith(bom):
                self.add("PUBLIC_TEXT_NOT_UTF8", rel, codec + " BOM")
                try:
                    return data.decode(codec).encode("utf-8")
                except UnicodeDecodeError:
                    return data
        try:
            data.decode("utf-8")
            return data
        except UnicodeDecodeError:
            self.add("PUBLIC_TEXT_NOT_UTF8", rel, "invalid UTF-8")
            for codec in ("utf-16-le", "utf-16-be", "latin-1"):
                try:
                    return data.decode(codec).encode("utf-8")
                except UnicodeDecodeError:
                    continue
            return data

    def json_keys(self, rel: str, data: bytes):
        keys: list[str] = []

        def hook(pairs):
            keys.extend(k for k, _ in pairs)
            return dict(pairs)
        try:
            json.loads(data.decode("utf-8"), object_pairs_hook=hook)
        except (ValueError, UnicodeDecodeError):
            self.add("PUBLIC_JSON_INVALID", rel)
            return
        reported = set()
        for k in keys:
            if k in PRIVATE_KEYS and k not in reported:
                reported.add(k)
                self.add("PUBLIC_PRIVATE_FIELD", rel, k + " (parsed JSON key)")

    def scan_bytes(self, rel: str, data: bytes, text: bool):
        def line_of(pos: int) -> int | None:
            return data.count(b"\n", 0, pos) + 1 if text else None

        for name, rx in SECRET_PATTERNS:
            for m in rx.finditer(data):
                self.add("PUBLIC_SECRET_PATTERN", rel, f"{name}: {redact(m.group(0))}", line_of(m.start()))
        for m in MACHINE_PATH.finditer(data):
            self.add("PUBLIC_MACHINE_PATH", rel, redact(m.group(0)), line_of(m.start()))
        for m in PRODUCTION_PATH.finditer(data):
            self.add("PUBLIC_PRODUCTION_PATH", rel, m.group(0).decode("ascii", "replace"), line_of(m.start()))
        if text:
            for m in PRIVATE_FIELD.finditer(data):
                self.add("PUBLIC_PRIVATE_FIELD", rel, m.group(0).decode("ascii", "replace").strip('"\': '),
                         line_of(m.start()))
            if not self.allow_placeholders:
                for m in PLACEHOLDER.finditer(data):
                    self.add("PUBLIC_PLACEHOLDER", rel, m.group(0).decode("utf-8", "replace"), line_of(m.start()))
            for m in URL.finditer(data):
                self.check_url(rel, m.group(0).decode("utf-8", "replace"), line_of(m.start()))
        if text and rel.lower().endswith((".html", ".htm", ".xml", ".svg")):
            unescaped = html.unescape(data.decode("utf-8", "replace")).encode("utf-8")
            if unescaped != data:  # entity-encoded addresses (F-L05): check the decoded text too
                for m in EMAIL.finditer(unescaped):
                    if m.group(0) not in data and m.group(0).decode("ascii", "replace").lower() not in self.allowed_emails:
                        self.add("PUBLIC_EMAIL_NOT_ALLOWLISTED", rel, redact(m.group(0)) + " (entity-encoded)")
        for m in EMAIL.finditer(data):  # text AND printable strings of binaries (H2, M5)
            if m.group(0).decode("ascii", "replace").lower() not in self.allowed_emails:
                self.add("PUBLIC_EMAIL_NOT_ALLOWLISTED", rel, redact(m.group(0)), line_of(m.start()))
        lowered = data.lower()
        for i, term in enumerate(self.deny_terms):
            if term.lower().encode("utf-8") in lowered:
                self.add("PUBLIC_DENYLIST_TERM", rel, f"policy deny_terms[{i}]")

    def check_url(self, rel: str, url: str, line: int | None):
        try:
            parts = urlsplit(url)
            host = (parts.hostname or "").lower()
        except ValueError:
            self.add("PUBLIC_URL_UNPARSEABLE", rel, url[:60], line)
            return
        if parts.username or parts.password:
            self.add("PUBLIC_URL_CREDENTIALS", rel, host, line)
        if parts.query and SIGNED_QUERY.search(parts.query):
            self.add("PUBLIC_SIGNED_URL", rel, host, line)
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                self.add("PUBLIC_PRIVATE_ADDRESS", rel, host, line)
        except ValueError:
            if host in ("localhost",) or host.endswith((".local", ".internal", ".lan", ".localhost")):
                self.add("PUBLIC_PRIVATE_ADDRESS", rel, host, line)
        if parts.scheme.lower() != "https" and host not in ("www.w3.org",):
            self.add("PUBLIC_URL_NOT_HTTPS", rel, host, line)
        if host and not any(host == h or host.endswith("." + h) for h in self.allowed_hosts):
            self.add("PUBLIC_URL_HOST_NOT_ALLOWED", rel, host, line)

    def media_metadata(self, rel: str, data: bytes):
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            pos = 8
            while pos + 8 <= len(data):
                length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
                if ctype in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
                    self.add("PUBLIC_MEDIA_METADATA", rel, "png:" + ctype.decode())
                if ctype == b"IEND":
                    break
                pos += 12 + length
        elif data.startswith(b"\xff\xd8"):
            pos = 2
            while pos + 4 <= len(data) and data[pos] == 0xFF:
                marker = data[pos + 1]
                if marker in (0xD9, 0xDA):
                    break
                seglen = struct.unpack(">H", data[pos + 2:pos + 4])[0]
                seg = data[pos + 4:pos + 2 + seglen]
                if marker == 0xE1 and (seg.startswith(b"Exif") or seg.startswith(b"http://ns.adobe.com/xap")):
                    self.add("PUBLIC_MEDIA_METADATA", rel, "jpeg:" + ("exif" if seg.startswith(b"Exif") else "xmp"))
                if marker == 0xFE:
                    self.add("PUBLIC_MEDIA_METADATA", rel, "jpeg:comment")
                pos += 2 + seglen
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            pos = 12
            while pos + 8 <= len(data):
                ctype, length = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
                if ctype in (b"EXIF", b"XMP "):
                    self.add("PUBLIC_MEDIA_METADATA", rel, "webp:" + ctype.decode().strip())
                pos += 8 + length + (length & 1)
        elif data[4:8] == b"ftyp":
            self.mp4_boxes(rel, data, 0, len(data), 0)
        elif data.startswith(b"ID3") and len(data) >= 10:
            allowed = set(self.policy.get("allowed_id3_frames", ["TIT2", "TPE1", "TALB", "TRCK", "TYER", "TDRC",
                                                                  "TCON", "APIC", "TLEN", "TCOP"]))
            ver = data[3]
            size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
            pos, end = 10, min(10 + size, len(data))
            while pos + 10 <= end and data[pos:pos + 4].strip(b"\0"):
                fid = data[pos:pos + 4].decode("latin-1")
                fsz = struct.unpack(">I", data[pos + 4:pos + 8])[0]
                if ver == 4:
                    fsz = (data[pos + 4] << 21) | (data[pos + 5] << 14) | (data[pos + 6] << 7) | data[pos + 7]
                if fid not in allowed:
                    self.add("PUBLIC_MEDIA_METADATA", rel, "id3:" + fid)
                pos += 10 + fsz

    def mp4_boxes(self, rel: str, data: bytes, start: int, end: int, depth: int):
        """Walk ISO-BMFF boxes; flag user-data / iTunes metadata (udta, meta, ilst, (c)xxx atoms) (H2, M5)."""
        pos = start
        while pos + 8 <= end and depth < 8:
            size, typ = struct.unpack(">I4s", data[pos:pos + 8])
            header = 8
            if size == 1 and pos + 16 <= end:
                size, header = struct.unpack(">Q", data[pos + 8:pos + 16])[0], 16
            elif size == 0:
                size = end - pos
            if size < header:
                break
            box_end = min(pos + size, end)
            if typ in (b"udta", b"meta", b"ilst") or typ[:1] == b"\xa9":
                self.add("PUBLIC_MEDIA_METADATA", rel, "mp4:" + typ.decode("latin-1"))
            if typ in MP4_CONTAINERS:
                inner = pos + header + (4 if typ == b"meta" else 0)
                self.mp4_boxes(rel, data, inner, box_end, depth + 1)
            pos = box_end

    def run(self) -> list[dict]:
        if self.manifest.get("kind") != "public-bundle-manifest":
            self.add("BUNDLE_MANIFEST_INVALID", "<manifest>", "kind")
        if self.manifest.get("example") is True and not self.policy.get("test_mode"):
            self.add("EXAMPLE_RECORD", "<manifest>")
        files = self.inventory()
        for rel in sorted(files):
            self.check_file(rel, files[rel]["path"], files[rel]["decl"])
        return self.findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle_dir")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--policy")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    try:
        root = Path(a.bundle_dir)
        if root.is_symlink() or not root.is_dir():
            print("bundle_dir must be a real directory", file=sys.stderr)
            return 2
        manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
        policy = json.loads(Path(a.policy).read_text(encoding="utf-8")) if a.policy else {}
    except (OSError, ValueError) as exc:
        print(f"usage/IO error: {type(exc).__name__}", file=sys.stderr)
        return 2
    findings = Scan(root, manifest, policy).run()
    report = {"tool": "leak_scan", "version": "0.1.0-e1", "bundle_id": manifest.get("bundle_id"),
              "clean": not findings, "finding_count": len(findings), "findings": findings,
              "note": "heuristic scan; clean means no listed pattern matched"}
    out = json.dumps(report, indent=1, ensure_ascii=True)
    if a.report:
        Path(a.report).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
