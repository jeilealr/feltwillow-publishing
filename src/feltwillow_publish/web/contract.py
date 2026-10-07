"""Offline checks for the shared website contract (Agent C; integrated for contract revision H2).

PROPOSED CONTRACT; renderer-independent:
  payload        data/web-bundle.json against web-bundle.v2 + semantic rules             WB_*
  render-input   public-bundle-manifest.v1 (unified validator) + render-input rules + bytes on disk   RI_*
  completeness   a later site-set keeps every story-language of the earlier one        SC_*
  site-artifact  a renderer's output tree against its input bundle                      SA_*
No network, no subprocess, no writes.
"""
from __future__ import annotations

import hashlib
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from ..contracts import cj1
from ..contracts import validate as contracts

PAYLOAD_PATH = "data/web-bundle.json"
MAGIC = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}
LEAK_RE = re.compile(rb"(/scratch/|/users/|/home/|file://|[A-Za-z]:\\\\|FELTWILLOW_[A-Z_]+=|\.env\b)")
ARTIFACT_ALLOWED_TOP = {"index.html", "404.html", "sitemap.xml", "robots.txt", "_redirects", "_headers",
                        "favicon.ico", "favicon.svg"}
ARTIFACT_ALLOWED_DIRS = ("assets/", "media/")


# ---------------------------------------------------------------- payload
def routes_of(p) -> list[str]:
    r = ["/"] + [l["path"] for l in p["languages"]] + [l["path"] + "stories/" for l in p["languages"]]
    return r + [pg["path"] for pg in p["pages"]] + [s["path"] for s in p["stories"]]


def check_payload(p) -> list[str]:
    try:
        cj1.check_domain(p)
    except cj1.CanonicalError as exc:
        return [f"WB_CANONICAL_DOMAIN: {exc}"]
    if not isinstance(p, dict) or p.get("kind") != "web-bundle" or p.get("schema_version") != 2:
        return ["WB_SCHEMA: kind/schema_version"]
    errs = sorted({"WB_SCHEMA: " + e.split(": ")[1] for e in contracts.schema_errors(p)})
    if errs:
        return errs
    return web_semantics(p)


def web_semantics(p) -> list[str]:
    """Cross-field rules of web-bundle.v2 (schema already valid)."""
    e: list[str] = []
    langs = [l["language"] for l in p["languages"]]
    if len(set(langs)) != len(langs):
        e.append("WB_LANGUAGE_DUPLICATE")
    for l in p["languages"]:
        if l["path"] != f"/{l['language']}/":
            e.append("WB_LANGUAGE_PATH_MISMATCH: " + l["path"])
    if p["default_language"] not in langs:
        e.append("WB_DEFAULT_LANGUAGE_UNKNOWN")
    routes = routes_of(p)
    dup = {r for r in routes if routes.count(r) > 1}
    if dup:
        e.append("WB_ROUTE_DUPLICATE: " + ",".join(sorted(dup)))
    keys = [(s["story_id"], s["language"]) for s in p["stories"]]
    if len(set(keys)) != len(keys):
        e.append("WB_STORY_LANGUAGE_DUPLICATE")
    media = p["media"]
    used: set[str] = set()
    for pg in p["pages"]:
        if pg["language"] is not None and pg["language"] not in langs:
            e.append("WB_PAGE_LANGUAGE_UNKNOWN: " + pg["path"])
        if pg["language"] is not None and not pg["path"].startswith(f"/{pg['language']}/"):
            e.append("WB_PAGE_PATH_LANGUAGE_MISMATCH: " + pg["path"])
        if pg["language"] is None and pg["path"].count("/") != 2:
            e.append("WB_PAGE_PATH_LANGUAGE_MISMATCH: " + pg["path"])
        for b in pg["blocks"]:
            if b["type"] == "image":
                used.add(b["asset_id"])
                if b["asset_id"] not in media or not media[b["asset_id"]]["media_type"].startswith("image/"):
                    e.append("WB_MEDIA_UNRESOLVED: " + b["asset_id"])
    for s in p["stories"]:
        sid = f"{s['story_id']}.{s['language']}"
        if s["language"] not in langs:
            e.append("WB_STORY_LANGUAGE_UNKNOWN: " + sid)
        if not s["path"].startswith(f"/{s['language']}/stories/"):
            e.append("WB_STORY_PATH_LANGUAGE_MISMATCH: " + sid)
        if not s["release"]["release_id"].startswith(f"{s['story_id']}.{s['language']}.r"):
            e.append("WB_RELEASE_MISMATCH: " + sid)
        if s["age_min"] > s["age_max"]:
            e.append("WB_AGE_RANGE: " + sid)
        refs = [b["asset_id"] for b in s["blocks"] if b["type"] == "image"]
        if s["cover"]:
            refs.append(s["cover"]["asset_id"])
        for a in refs:
            used.add(a)
            if a not in media or not media[a]["media_type"].startswith("image/"):
                e.append(f"WB_MEDIA_UNRESOLVED: {sid}:{a}")
            elif media[a]["width"] is None or media[a]["height"] is None:
                e.append(f"WB_IMAGE_DIMENSIONS_MISSING: {sid}:{a}")
        lis = s["listening"]
        has_audio = lis["player"]["type"] != "none" or any(l["service"] != "youtube" for l in lis["links"])
        if lis["player"]["type"] == "native_audio":
            a = lis["player"]["asset_id"]
            used.add(a)
            if a not in media or not media[a]["media_type"].startswith("audio/"):
                e.append(f"WB_MEDIA_UNRESOLVED: {sid}:{a}")
            elif media[a]["duration_ms"] != lis["duration_ms"]:
                e.append("WB_DURATION_MISMATCH: " + sid)
        if (lis["player"]["type"] == "spotify_embed" and not p["example"]
                and urlsplit(lis["player"]["embed_url"]).hostname != "open.spotify.com"):
            e.append("WRONG_EMBED_HOST: " + sid)  # v2 rule (examples use reserved hosts only)
        if lis["player"]["type"] != "none" and lis["duration_ms"] is None:
            e.append("WB_DURATION_REQUIRED: " + sid)
        if has_audio and s["reading_divergence"] == "not-applicable":
            e.append("WB_DIVERGENCE_INCONSISTENT: " + sid)
        if has_audio and s["reading_divergence"] == "intentional-adaptation" and s["transcript"] is None:
            e.append("WB_TRANSCRIPT_REQUIRED: " + sid)
        if s["published_at"] and s["updated_at"] and s["updated_at"] < s["published_at"]:
            e.append("WB_TIMESTAMP_ORDER: " + sid)
    for k, m in media.items():
        ext = m["path"].rsplit(".", 1)[1]
        want = {"image/webp": "webp", "image/png": "png", "image/jpeg": "jpg", "audio/mpeg": "mp3",
                "audio/mp4": "m4a", "text/vtt": "vtt"}[m["media_type"]]
        if m["path"] != f"media/{m['sha256']}.{want}" or ext != want:
            e.append("WB_MEDIA_PATH_NOT_CONTENT_ADDRESSED: " + k)
        if m["source"]["asset_id"] != k:
            e.append("WB_MEDIA_SOURCE_MISMATCH: " + k)
        if k not in used:
            e.append("WB_MEDIA_UNUSED: " + k)
    route_set = set(routes)
    froms = [r["from"] for r in p["redirects"]]
    if len(set(froms)) != len(froms):
        e.append("WB_REDIRECT_DUPLICATE")
    for r in p["redirects"]:
        if r["from"] in route_set:
            e.append("WB_REDIRECT_SHADOWS_ROUTE: " + r["from"])
        if r["to"] not in route_set:
            e.append("WB_REDIRECT_TARGET_MISSING: " + r["to"])
    return e


# ---------------------------------------------------------------- render-input bundle
def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_tree(root: Path) -> tuple[dict[str, Path], list[str]]:
    """Return regular files by relative path; report symlinks and special files."""
    files, errs = {}, []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                errs.append("TREE_SYMLINK: " + rel)
            elif name in filenames:
                if not full.is_file():
                    errs.append("TREE_SPECIAL_FILE: " + rel)
                else:
                    files[rel] = full
    return files, errs


def check_render_input(manifest, root: Path):
    """Return (errors, payload or None)."""
    e = ["RI_" + c for c in contracts.validate(manifest)]
    if e:
        return e, None
    if manifest["bundle_type"] != "web":
        e.append("RI_NOT_WEB_BUNDLE")
    if manifest["inputs"]["renderer"] is not None:
        e.append("RI_RENDERER_MUST_BE_NULL")
    listed = {f["path"]: f for f in manifest["files"]}
    if PAYLOAD_PATH not in listed or listed[PAYLOAD_PATH]["media_type"] != "application/json":
        return e + ["RI_PAYLOAD_MISSING"], None
    on_disk, terr = scan_tree(root)
    e += ["RI_" + t for t in terr]
    for rel in sorted(set(on_disk) - set(listed)):
        e.append("RI_UNLISTED_FILE: " + rel)
    for rel, f in listed.items():
        if rel not in on_disk:
            e.append("RI_MISSING_FILE: " + rel)
            continue
        data_len = on_disk[rel].stat().st_size
        if data_len != f["bytes"] or _sha(on_disk[rel]) != f["sha256"]:
            e.append("RI_FILE_DIGEST_MISMATCH: " + rel)
        magic = MAGIC.get(f["media_type"])
        if magic and not on_disk[rel].read_bytes()[: len(magic)] == magic:
            e.append("RI_MEDIA_TYPE_MISMATCH: " + rel)
    if PAYLOAD_PATH not in on_disk:
        return e, None
    raw = on_disk[PAYLOAD_PATH].read_bytes()
    try:
        payload = cj1.loads_strict(raw)
    except cj1.CanonicalError as exc:
        return e + [f"RI_PAYLOAD_PARSE: {exc}"], None
    if cj1.canonical_bytes(payload) != raw:
        e.append("RI_PAYLOAD_NOT_CANONICAL")
    e += check_payload(payload)
    if any(x.startswith("WB_SCHEMA") or x.startswith("WB_CANONICAL") for x in e):
        return e, None
    if manifest["inputs"]["public_record_sha256"] != cj1.digest(payload):
        e.append("RI_PUBLIC_RECORD_DIGEST_MISMATCH")
    if manifest["inputs"]["site_set"] != payload["site_set"]:
        e.append("RI_SITE_SET_MISMATCH")
    rel_in = {(r["release_id"], r["release_sha256"]) for r in manifest["inputs"]["releases"]}
    rel_pl = {(s["release"]["release_id"], s["release"]["release_sha256"]) for s in payload["stories"]}
    if rel_in != rel_pl:
        e.append("RI_RELEASES_MISMATCH")
    media_paths = {m["path"]: m for m in payload["media"].values()}
    for rel, f in listed.items():
        if rel == PAYLOAD_PATH:
            continue
        m = media_paths.get(rel)
        if m is None:
            e.append("RI_FILE_NOT_IN_PAYLOAD: " + rel)
        elif (m["sha256"], m["bytes"], m["media_type"], m["source"]) != (
                f["sha256"], f["bytes"], f["media_type"], f["source"]):
            e.append("RI_PAYLOAD_MANIFEST_DISAGREE: " + rel)
    for rel in media_paths:
        if rel not in listed:
            e.append("RI_PAYLOAD_MEDIA_NOT_LISTED: " + rel)
    return e, payload


# ---------------------------------------------------------------- site-set completeness
def check_completeness(prev, new, removed_paths=()) -> list[str]:
    e = []
    removed = set(removed_paths)
    new_by_key = {(s["story_id"], s["language"]): s for s in new["stories"]}
    redirects = {r["from"]: r["to"] for r in new["redirects"]}
    for s in prev["stories"]:
        key = (s["story_id"], s["language"])
        if key not in new_by_key:
            if s["path"] not in removed:
                e.append("SC_STORY_DROPPED: {}.{}".format(*key))
            continue
        if new_by_key[key]["path"] != s["path"] and redirects.get(s["path"]) != new_by_key[key]["path"]:
            e.append("SC_PATH_CHANGED_WITHOUT_REDIRECT: " + s["path"])
    for r in prev["redirects"]:
        if r["from"] not in redirects:
            e.append("SC_REDIRECT_DROPPED: " + r["from"])
    for l in prev["languages"]:
        if l["language"] not in {x["language"] for x in new["languages"]} and l["path"] not in removed:
            e.append("SC_LANGUAGE_DROPPED: " + l["language"])
    return e


# ---------------------------------------------------------------- site artifact
class _PageScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_lang, self.imgs, self.problems, self.has_main, self.has_h1 = None, [], [], False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "main":
            self.has_main = True
        if tag == "h1":
            self.has_h1 = True
        if tag in ("audio", "video") and "autoplay" in a:
            self.problems.append("SA_AUTOPLAY")
        if tag == "img":
            if a.get("alt") is None:
                self.problems.append("SA_IMG_WITHOUT_ALT")
            self.imgs.append(a.get("src") or "")
        if tag == "script" and a.get("src", "").startswith(("http:", "https:", "//")):
            self.problems.append("SA_REMOTE_SCRIPT")
        if tag == "iframe":
            self.problems.append("SA_EAGER_IFRAME")  # third-party embeds must be click-to-load


def route_file(route: str) -> str:
    return (route.lstrip("/") + "index.html") if route != "/" else "index.html"


def check_site_artifact(art_manifest, root: Path, in_manifest, payload) -> list[str]:
    e = ["SA_" + c for c in contracts.validate(art_manifest)]
    if e:
        return e
    if art_manifest["inputs"]["renderer"] is None:
        e.append("SA_RENDERER_REQUIRED")
    pin = {k: v for k, v in in_manifest["inputs"].items() if k != "renderer"}
    if {k: v for k, v in art_manifest["inputs"].items() if k != "renderer"} != pin:
        e.append("SA_INPUTS_DIFFER_FROM_RENDER_INPUT")
    listed = {f["path"]: f for f in art_manifest["files"]}
    on_disk, terr = scan_tree(root)
    e += ["SA_" + t for t in terr]
    if set(on_disk) != set(listed):
        e.append("SA_MANIFEST_TREE_DIFFER")
    for rel, f in listed.items():
        if rel in on_disk and (_sha(on_disk[rel]) != f["sha256"] or on_disk[rel].stat().st_size != f["bytes"]):
            e.append("SA_FILE_DIGEST_MISMATCH: " + rel)
        top_ok = rel in ARTIFACT_ALLOWED_TOP or rel.startswith(ARTIFACT_ALLOWED_DIRS) or rel.endswith("/index.html")
        if not top_ok:
            e.append("SA_UNEXPECTED_FILE: " + rel)
    if "404.html" not in listed:
        e.append("SA_404_MISSING")
    input_media = {f["path"]: f["sha256"] for f in in_manifest["files"] if f["path"].startswith("media/")}
    for rel, f in listed.items():
        if rel.startswith("media/") and input_media.get(rel) != f["sha256"]:
            e.append("SA_MEDIA_NOT_FROM_INPUT: " + rel)
    for rel in input_media:
        if rel not in listed:
            e.append("SA_INPUT_MEDIA_NOT_SHIPPED: " + rel)
    for r in routes_of(payload):
        if route_file(r) not in listed:
            e.append("SA_ROUTE_MISSING: " + r)
    for rel, path in on_disk.items():
        if rel.endswith((".html", ".xml", ".txt", ".css", ".js", "_redirects", "_headers")):
            if LEAK_RE.search(path.read_bytes()):
                e.append("SA_LOCAL_PATH_OR_SECRET_PATTERN: " + rel)
    media = payload["media"]
    for s in payload["stories"]:
        f = on_disk.get(route_file(s["path"]))
        if f is None:
            continue
        scan = _PageScan()
        scan.feed(f.read_text(encoding="utf-8"))
        e += [f"{p}: {s['path']}" for p in scan.problems]
        if scan.html_lang != s["language"]:
            e.append("SA_HTML_LANG_MISMATCH: " + s["path"])
        if not (scan.has_main and scan.has_h1):
            e.append("SA_LANDMARK_MISSING: " + s["path"])
        expected = [media[b["asset_id"]]["path"] for b in s["blocks"] if b["type"] == "image"]
        seen = [src.split("/media/", 1)[-1] for src in scan.imgs if "/media/" in src]
        seen = ["media/" + x for x in seen]
        cover = media[s["cover"]["asset_id"]]["path"] if s["cover"] else None
        if cover and seen and seen[0] == cover:
            seen = seen[1:]
        if seen != expected:
            e.append("SA_ILLUSTRATION_ORDER: " + s["path"])
    return e


