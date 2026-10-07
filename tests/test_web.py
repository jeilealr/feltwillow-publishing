"""Website contract suites (Agent C's self-test of check_web_contract.py, integrated for H2).

Payload (WB_*), render-input bundle (RI_*), site-set completeness (SC_*) and a SYNTHETIC site artifact
(SA_*; no renderer exists). Temporary trees live under ctx.tmp and are removed afterwards.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil

from feltwillow_publish.web.contract import (PAYLOAD_PATH, check_completeness, check_payload, check_render_input,
                                       check_site_artifact, route_file, routes_of)
from support import EXAMPLES

def _mut(fn):
    def apply(p):
        q = copy.deepcopy(p)
        fn(q)
        return q
    return apply


def payload_negatives():
    def s0(q):
        return q["stories"][0]
    return [
        ("unknown block type", _mut(lambda q: s0(q)["blocks"].append({"type": "video", "text": "x"})), "WB_SCHEMA"),
        ("private field leaks into story", _mut(lambda q: s0(q).__setitem__("voice_id", "x")), "WB_SCHEMA"),
        ("float duration", _mut(lambda q: s0(q)["listening"].__setitem__("duration_ms", 1.5)), "WB_CANONICAL_DOMAIN"),
        ("http (not https) youtube url", _mut(lambda q: s0(q).__setitem__("video", {"youtube_url": "http://example.invalid/v"})), "WB_SCHEMA"),
        ("javascript: url in link", _mut(lambda q: s0(q)["listening"]["links"].append({"service": "other", "label": "x", "url": "javascript:alert(1)"})), "WB_SCHEMA"),
        ("empty alt text", _mut(lambda q: s0(q)["blocks"][2].__setitem__("alt", "")), "WB_SCHEMA"),
        ("story path in other language", _mut(lambda q: s0(q).__setitem__("path", "/de/stories/the-lion-and-the-mouse/")), "WB_STORY_PATH_LANGUAGE_MISMATCH"),
        ("duplicate route", _mut(lambda q: q["stories"][1].__setitem__("path", q["stories"][0]["path"])), "WB_ROUTE_DUPLICATE"),
        ("image block references missing media", _mut(lambda q: s0(q)["blocks"][2].__setitem__("asset_id", "illus-missing")), "WB_MEDIA_UNRESOLVED"),
        ("unused media (nonselected asset)", _mut(lambda q: q["media"].__setitem__("illus-extra", dict(q["media"]["illus-fixture-01"], source={"release_id": "fixture-second-story.en.r0001", "asset_id": "illus-extra"}))), "WB_MEDIA_UNUSED"),
        ("media path not content-addressed", _mut(lambda q: q["media"]["illus-fixture-01"].__setitem__("path", "media/" + "0" * 64 + ".png")), "WB_MEDIA_PATH_NOT_CONTENT_ADDRESSED"),
        ("spotify embed without measured duration", _mut(lambda q: s0(q)["listening"].__setitem__("player", {"type": "spotify_embed", "embed_url": "https://example.invalid/embed", "fallback_url": "https://example.invalid/show"})), "WB_DURATION_REQUIRED"),
        ("spotify embed without fallback link", _mut(lambda q: s0(q)["listening"].__setitem__("player", {"type": "spotify_embed", "embed_url": "https://example.invalid/embed"})), "WB_SCHEMA"),
        ("audio but divergence not-applicable", _mut(lambda q: s0(q)["listening"]["links"].append({"service": "spotify", "label": "Listen", "url": "https://example.invalid/ep"})), "WB_DIVERGENCE_INCONSISTENT"),
        ("adapted reading text with audio but no transcript", _mut(lambda q: (s0(q).__setitem__("reading_divergence", "intentional-adaptation"), s0(q)["listening"]["links"].append({"service": "spotify", "label": "Listen", "url": "https://example.invalid/ep"}))), "WB_TRANSCRIPT_REQUIRED"),
        ("age range inverted", _mut(lambda q: s0(q).__setitem__("age_min", 9)), "WB_AGE_RANGE"),
        ("release of another story", _mut(lambda q: s0(q)["release"].__setitem__("release_id", "fixture-second-story.en.r0001")), "WB_RELEASE_MISMATCH"),
        ("redirect to missing route", _mut(lambda q: q["redirects"].append({"from": "/en/stories/old-name/", "to": "/en/stories/nowhere/", "status": 301})), "WB_REDIRECT_TARGET_MISSING"),
        ("redirect shadows live route", _mut(lambda q: q["redirects"].append({"from": "/en/about/", "to": "/en/", "status": 301})), "WB_REDIRECT_SHADOWS_ROUTE"),
        ("default language not offered", _mut(lambda q: q.__setitem__("default_language", "de")), "WB_DEFAULT_LANGUAGE_UNKNOWN"),
        ("origin is http", _mut(lambda q: q.__setitem__("origin", "http://example.invalid")), "WB_SCHEMA"),
        ("trailing slash policy changed", _mut(lambda q: q.__setitem__("trailing_slash", "never")), "WB_SCHEMA"),
    ]


def _write_artifact(root: Path, payload, mutate=None):
    """Synthetic renderer output used only to exercise the artifact checks (not a website)."""
    if root.exists():
        shutil.rmtree(root)
    pages = {}
    for r in routes_of(payload):
        pages[route_file(r)] = (f'<!doctype html><html lang="{payload["default_language"]}"><head><meta charset="utf-8">'
                                f"<title>fixture</title></head><body><main><h1>fixture</h1></main></body></html>")
    for s in payload["stories"]:
        imgs = "".join(f'<img src="/{payload["media"][b["asset_id"]]["path"]}" alt="{b["alt"]}">'
                       for b in s["blocks"] if b["type"] == "image")
        pages[route_file(s["path"])] = (f'<!doctype html><html lang="{s["language"]}"><head><meta charset="utf-8">'
                                        f"<title>fixture</title></head><body><main><h1>fixture</h1>{imgs}</main></body></html>")
    pages["404.html"] = '<!doctype html><html lang="en"><body><main><h1>Not found</h1></main></body></html>'
    files = {k: v.encode() for k, v in pages.items()}
    files["assets/site.css"] = b"body{font-family:system-ui}"
    for m in payload["media"].values():
        files[m["path"]] = (EXAMPLES / "web" / "render-input" / "site-set-0002" / m["path"]).read_bytes()
    if mutate:
        mutate(files)
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return files


def _artifact_manifest(files, in_manifest):
    mt = {"html": "text/html", "css": "text/css", "png": "image/png", "webp": "image/webp", "js": "application/javascript"}
    out = copy.deepcopy(in_manifest)
    out["bundle_id"] = "example-web-site-artifact"
    out["inputs"]["renderer"] = {"name": "plain_static", "version": "0.0.0-fixture"}
    out["files"] = [{"path": rel, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d),
                     "media_type": mt.get(rel.rsplit(".", 1)[-1], "text/plain"), "source": None}
                    for rel, d in sorted(files.items())]
    return out


def self_test(TMP):
    res = {"payload_positive": [], "payload_negative": [], "render_input_positive": [],
           "render_input_negative": [], "completeness": [], "site_artifact": []}
    ex = EXAMPLES / "web"
    bundles = {}
    for name in ("site-set-0001", "site-set-0002"):
        man = json.loads((ex / "manifests" / f"render-input.{name}.json").read_text())
        errs, payload = check_render_input(man, ex / "render-input" / name)
        bundles[name] = (man, payload)
        res["render_input_positive"].append({"case": name, "errors": errs, "pass": errs == []})
        if payload is not None:
            pe = check_payload(payload)
            res["payload_positive"].append({"case": name, "errors": pe, "pass": pe == []})
    man2, p2 = bundles["site-set-0002"]
    for label, fn, code in payload_negatives():
        errs = check_payload(fn(p2))
        res["payload_negative"].append({"case": label, "expected": code, "errors": errs,
                                        "pass": any(x.startswith(code) for x in errs)})
    # render-input negatives on temp copies
    TMP.mkdir(parents=True, exist_ok=True)
    src = ex / "render-input" / "site-set-0002"
    a_media = next(f["path"] for f in man2["files"] if f["path"].startswith("media/"))

    def ri_case(label, code, tree_fn=None, man_fn=None):
        root = TMP / "ri"
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(src, root, symlinks=True)
        m = copy.deepcopy(man2)
        if tree_fn:
            tree_fn(root)
        if man_fn:
            man_fn(m)
        errs, _ = check_render_input(m, root)
        res["render_input_negative"].append({"case": label, "expected": code, "errors": errs,
                                             "pass": any(x.startswith(code) for x in errs)})

    ri_case("extra unlisted file (e.g. leaked notes)", "RI_UNLISTED_FILE", tree_fn=lambda r: (r / "notes.txt").write_text("x"))
    ri_case("missing media bytes", "RI_MISSING_FILE", tree_fn=lambda r: (r / a_media).unlink())
    ri_case("media bytes changed", "RI_FILE_DIGEST_MISMATCH", tree_fn=lambda r: (r / a_media).write_bytes(b"\x89PNG\r\n\x1a\nchanged"))
    ri_case("escaping symlink", "RI_TREE_SYMLINK", tree_fn=lambda r: os.symlink("/etc/hostname", r / "media" / "link.png"))
    ri_case("renderer already set", "RI_RENDERER_MUST_BE_NULL",
            man_fn=lambda m: m["inputs"].__setitem__("renderer", {"name": "astro", "version": "0.0.0"}))
    ri_case("payload digest not pinned", "RI_PUBLIC_RECORD_DIGEST_MISMATCH",
            man_fn=lambda m: m["inputs"].__setitem__("public_record_sha256", "0" * 64))
    ri_case("release list differs from payload", "RI_RELEASES_MISMATCH",
            man_fn=lambda m: m["inputs"].__setitem__("releases", m["inputs"]["releases"][:1]))
    ri_case("forbidden function file listed (B rule)", "RI_PUBLIC_FORBIDDEN_FILE",
            man_fn=lambda m: m["files"].append({"path": "functions/api.js", "sha256": "0" * 64, "bytes": 1,
                                                "media_type": "application/javascript", "source": None}))
    ri_case("payload rewritten non-canonically", "RI_PAYLOAD_NOT_CANONICAL",
            tree_fn=lambda r: (r / PAYLOAD_PATH).write_text(json.dumps(p2, indent=1)),
            man_fn=lambda m: [f.update(sha256=hashlib.sha256(json.dumps(p2, indent=1).encode()).hexdigest(),
                                       bytes=len(json.dumps(p2, indent=1).encode()))
                              for f in m["files"] if f["path"] == PAYLOAD_PATH])
    # completeness
    p1 = bundles["site-set-0001"][1]
    cases = [
        ("first -> second story keeps the first", p1, p2, (), None),
        ("second site-set drops the first story", p2, _mut(lambda q: q["stories"].pop(0))(p2), (), "SC_STORY_DROPPED"),
        ("explicit withdrawal via remove_paths", p2, _mut(lambda q: (q["stories"].pop(0), q["media"].pop("cover-lion-and-mouse"),
                                                                    q["media"].pop("illus-s01-explores-start")))(p2),
         ("/en/stories/the-lion-and-the-mouse/",), None),
        ("slug change without redirect", p2, _mut(lambda q: q["stories"][0].__setitem__("path", "/en/stories/lion-and-mouse/"))(p2), (), "SC_PATH_CHANGED_WITHOUT_REDIRECT"),
        ("slug change with redirect", p2, _mut(lambda q: (q["stories"][0].__setitem__("path", "/en/stories/lion-and-mouse/"),
                                                         q["redirects"].append({"from": "/en/stories/the-lion-and-the-mouse/", "to": "/en/stories/lion-and-mouse/", "status": 301})))(p2), (), None),
    ]
    for label, prev, new, removed, code in cases:
        errs = check_completeness(prev, new, removed)
        if code is None:
            errs += check_payload(new)
        ok = errs == [] if code is None else any(x.startswith(code) for x in errs)
        res["completeness"].append({"case": label, "expected": code or "pass", "errors": errs, "pass": ok})
    # site artifact
    art_cases = [
        ("synthetic complete artifact", None, None),
        ("missing 404 page", lambda f: f.pop("404.html"), "SA_404_MISSING"),
        ("story route missing", lambda f: f.pop("en/stories/fixture-second-story/index.html"), "SA_ROUTE_MISSING"),
        ("renderer re-encoded media", lambda f: f.__setitem__("media/" + "1" * 64 + ".webp", b"RIFFxxxxWEBP"), "SA_MEDIA_NOT_FROM_INPUT"),
        ("functions dir shipped", lambda f: f.__setitem__("functions/api.js", b"export default 1"), "SA_PUBLIC_FORBIDDEN_FILE"),
        ("local path leaked", lambda f: f.__setitem__("en/about/index.html", b'<html lang="en"><main><h1>x</h1>/scratch/project/x</main></html>'), "SA_LOCAL_PATH_OR_SECRET_PATTERN"),
        ("autoplay audio", lambda f: f.__setitem__("en/stories/fixture-second-story/index.html",
                                                   f["en/stories/fixture-second-story/index.html"].replace(b"</main>", b'<audio autoplay src="/x.mp3"></audio></main>')), "SA_AUTOPLAY"),
        ("illustration missing from story page", lambda f: f.__setitem__("en/stories/the-lion-and-the-mouse/index.html",
                                                            b'<html lang="en"><main><h1>x</h1></main></html>'), "SA_ILLUSTRATION_ORDER"),
        ("img without alt", lambda f: f.__setitem__("en/stories/fixture-second-story/index.html",
                                                    f["en/stories/fixture-second-story/index.html"].replace(b' alt="EXAMPLE ONLY: fixture alt text."', b"")), "SA_IMG_WITHOUT_ALT"),
        ("eager third-party iframe", lambda f: f.__setitem__("en/stories/fixture-second-story/index.html",
                                                             f["en/stories/fixture-second-story/index.html"].replace(b"</main>", b'<iframe src="https://example.invalid/embed"></iframe></main>')), "SA_EAGER_IFRAME"),
        ("wrong html lang", lambda f: f.__setitem__("en/stories/fixture-second-story/index.html",
                                                    f["en/stories/fixture-second-story/index.html"].replace(b'lang="en"', b'lang="de"')), "SA_HTML_LANG_MISMATCH"),
    ]
    for label, mutate, code in art_cases:
        root = TMP / "artifact"
        files = _write_artifact(root, p2, mutate)
        am = _artifact_manifest(files, man2)
        errs = check_site_artifact(am, root, man2, p2)
        ok = errs == [] if code is None else any(x.startswith(code) for x in errs)
        res["site_artifact"].append({"case": label, "expected": code or "pass", "errors": errs, "pass": ok})
    shutil.rmtree(TMP, ignore_errors=True)
    return {"web_" + k: v for k, v in res.items()}


def run(ctx):
    return self_test(ctx["tmp"] / "web")


