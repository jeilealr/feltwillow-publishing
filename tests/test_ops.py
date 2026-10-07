"""Operations suites (Agent E's test_e.py integrated for H2) plus the new H2 checks: storage roots
(STATE_ROOT_*), the handoff-index private-field scan (IC-E4) and strict-zero on the owner's declared
inventory. Synthetic bundles only, under ctx.tmp.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import struct
import zlib
from pathlib import Path

from feltwillow_publish.contracts import validate as V
from feltwillow_publish.ops import ci_lint, handoff_index_scan, leak_scan, state_roots, strict_zero
from support import EXAMPLES, FIX, case as mkcase

OPS = FIX / "ops"
POLICY = json.loads((OPS / "scan-policy.example.json").read_text())


def png(text_chunk: bool = False) -> bytes:
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    if text_chunk:
        out += chunk(b"tEXt", b"parameters\0prompt: lion, model: x")
    return out + chunk(b"IDAT", zlib.compress(b"\0\0\0\0")) + chunk(b"IEND", b"")


def jpeg_exif() -> bytes:
    seg = b"Exif\0\0" + b"MM\0*" + b"\0" * 8
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(seg) + 2) + seg + b"\xff\xd9"


def mp3_with(frame: str) -> bytes:
    body = b"\0" + b"x" * 8
    fr = frame.encode() + struct.pack(">I", len(body)) + b"\0\0" + body
    size = len(fr)
    syn = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x03\x00\x00" + syn + fr + b"\xff\xfb\x90\x00" + b"\0" * 32


CLEAN_HTML = (b"<!doctype html><html lang=\"en\"><head><title>The Lion and the Mouse</title></head><body>"
              b"<p>A small mouse helps a lion.</p><a href=\"https://open.spotify.com/show/REAL-ID-CAPTURED\">Listen</a>"
              b"<img src=\"../../media/illus.png\" alt=\"A mouse\"></body></html>\n")


def build(root: Path, files: dict[str, bytes], extra_decl: dict | None = None, skip_decl=()) -> dict:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    decl = []
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        os.chmod(p, 0o644)
        if rel not in skip_decl:
            decl.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                         "media_type": "text/html" if rel.endswith(".html") else "application/octet-stream",
                         "source": None})
    for rel, d in (extra_decl or {}).items():
        decl.append({"path": rel, **d})
    return {"kind": "public-bundle-manifest", "schema_version": 1, "example": True, "bundle_id": "t",
            "files": decl}


def scan(root: Path, manifest: dict, policy=None) -> set[str]:
    return {f["code"] for f in leak_scan.Scan(root, manifest, policy or POLICY).run()}


def leak_cases(tmp: Path) -> list[dict]:
    base = {"en/stories/the-lion-and-the-mouse/index.html": CLEAN_HTML, "media/illus.png": png()}
    cases = []

    def case(name, expect, files=None, mutate=None, policy=None, post=None):
        root = tmp / name
        fs = dict(base)
        fs.update(files or {})
        man = build(root, fs)
        if mutate:
            mutate(man)
        if post:
            post(root)
        got = scan(root, man, policy)
        ok = (got == set()) if expect is None else (expect in got)
        cases.append({"case": name, "expect": expect or "clean", "got": sorted(got), "pass": ok})

    html = lambda s: {"en/x/index.html": s.encode()}  # noqa: E731
    case("L00-clean", None)
    case("L01-google-key", "PUBLIC_SECRET_PATTERN", html("<script>const k='AIza" + "A" * 35 + "'</script>"))
    case("L02-openai-key", "PUBLIC_SECRET_PATTERN", html("<p>sk-proj-" + "a" * 30 + "</p>"))
    case("L03-private-key", "PUBLIC_SECRET_PATTERN", html("-----BEGIN OPENSSH PRIVATE KEY-----"))
    case("L04-machine-path", "PUBLIC_MACHINE_PATH",
         html("<img src=\"/scratch/project_465002727/jelealro/x.png\" alt=\"\">"))
    case("L05-mac-path", "PUBLIC_MACHINE_PATH", html("<!-- /Users/owner/Feltwillow/masters/a.wav -->"))
    case("L06-production-path", "PUBLIC_PRODUCTION_PATH",
         html("<p>character/characters/lion_and_mouse_v5/interactions/keyframes/s01.png</p>"))
    case("L07-private-field-json", "PUBLIC_PRIVATE_FIELD",
         {"data/story.json": b"{\"title\": \"x\", \"generation_provenance\": []}"})
    case("L08-placeholder", "PUBLIC_PLACEHOLDER", html("<p>EXAMPLE ONLY: no story</p>"))
    case("L09-email", "PUBLIC_EMAIL_NOT_ALLOWLISTED", html("<p>owner.private@example.org</p>"))
    case("L10-signed-url", "PUBLIC_SIGNED_URL",
         html("<a href=\"https://open.spotify.com/a.mp3?X-Amz-Signature=abc&X-Amz-Expires=60\">x</a>"))
    case("L11-url-credentials", "PUBLIC_URL_CREDENTIALS", html("<a href=\"https://u:p@open.spotify.com/\">x</a>"))
    case("L12-private-address", "PUBLIC_PRIVATE_ADDRESS", html("<a href=\"http://192.168.1.10/x\">x</a>"))
    case("L13-host-not-allowed", "PUBLIC_URL_HOST_NOT_ALLOWED",
         html("<script src=\"https://tracker.example.com/t.js\"></script>"))
    case("L14-png-text-chunk", "PUBLIC_MEDIA_METADATA", {"media/illus.png": png(text_chunk=True)})
    case("L15-jpeg-exif", "PUBLIC_MEDIA_METADATA", {"media/a.jpg": jpeg_exif()})
    case("L16-id3-private-frame", "PUBLIC_MEDIA_METADATA", {"media/a.mp3": mp3_with("PRIV")})
    case("L17-id3-allowed-frame", None, {"media/a.mp3": mp3_with("TIT2")})
    case("L18-elf-binary", "PUBLIC_EXECUTABLE_CONTENT", {"media/a.webp": b"\x7fELF" + b"\0" * 60})
    case("L19-env-file", "PUBLIC_FORBIDDEN_FILE", {".env.production": b"X=1\n"})
    case("L20-serverless", "PUBLIC_FORBIDDEN_FILE", {"functions/api.js": b"export default {}\n"})
    case("L21-wav-master", "PUBLIC_FORBIDDEN_FILE", {"media/master.wav": b"RIFF\0\0\0\0WAVE"})
    case("L22-undeclared-file", "BUNDLE_UNDECLARED_FILE",
         post=lambda r: (r / "extra.html").write_bytes(b"<p>x</p>"))
    case("L23-missing-file", "BUNDLE_MISSING_FILE",
         mutate=lambda m: m["files"].append({"path": "gone.html", "sha256": "0" * 64, "bytes": 1,
                                              "media_type": "text/html", "source": None}))
    case("L24-hash-mismatch", "BUNDLE_HASH_MISMATCH",
         post=lambda r: (r / "media/illus.png").write_bytes(png() + b"\0"))
    case("L25-symlink", "PUBLIC_LINK_FORBIDDEN",
         post=lambda r: os.symlink("/etc/hostname", r / "media/link.png"))
    case("L26-executable-mode", "PUBLIC_EXECUTABLE_MODE",
         post=lambda r: os.chmod(r / "media/illus.png", 0o755))
    case("L27-denylist-term", "PUBLIC_DENYLIST_TERM", html("<p>voice Kore-private-label</p>"),
         policy={**POLICY, "deny_terms": ["kore-private-label"]})
    case("L28-example-outside-test", "EXAMPLE_RECORD", policy={**POLICY, "test_mode": False})
    case("L29-secret-in-binary-strings", "PUBLIC_SECRET_PATTERN",
         {"media/illus.png": png() + b"hf_" + b"a" * 34})
    case("L30-http-not-https", "PUBLIC_URL_NOT_HTTPS", html("<a href=\"http://open.spotify.com/x\">x</a>"))
    case("L31-git-dir", "PUBLIC_FORBIDDEN_FILE", {".git/config": b"[core]\n"})
    case("L32-github-token", "PUBLIC_SECRET_PATTERN", html("<p>ghp_" + "A" * 36 + "</p>"))
    secret = "AIza" + "Q" * 35
    r35 = tmp / "L35"
    man35 = build(r35, {**base, "en/y/index.html": ("<p>" + secret + "</p>").encode()})
    found = leak_scan.Scan(r35, man35, POLICY).run()
    cases.append({"case": "L35-report-never-contains-secret", "expect": "redacted",
                  "got": sorted({f["code"] for f in found}),
                  "pass": bool(found) and secret not in json.dumps(found) and "Q" * 10 not in json.dumps(found)})
    case("L33-prefixed-record-name", "PUBLIC_FORBIDDEN_FILE", {"data/production-handoff.lion.json": b"{}"})
    case("L34-import-receipt-name", "PUBLIC_FORBIDDEN_FILE", {"data/import-receipt.x.json": b"{}"})
    # H2 (M5): Agent F's bypasses F-L01..F-L04, plus invalid JSON
    fake_key = "AIza" + "B" * 35
    utf16 = f"credits: voice key {fake_key} contact owner.private@example.org\n".encode("utf-16")
    case("L36-utf16-text-flagged (F-L01)", "PUBLIC_TEXT_NOT_UTF8", {"credits.txt": utf16})
    case("L37-utf16-secret-still-found (F-L01)", "PUBLIC_SECRET_PATTERN", {"credits.txt": utf16})
    case("L38-production-keyframe-path (F-L02)", "PUBLIC_PRODUCTION_PATH",
         html('<img src="/media/a.png" data-src="stories/lion_and_mouse_v5/keyframes/s01_r03.png">'))
    case("L39-json-escaped-private-key (F-L03)", "PUBLIC_PRIVATE_FIELD", {"data/data.json": b'{"voice\\u005fid": "Kore", "title": "x"}'})
    mp4 = (b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00\x00\x00\x30udta\x00\x00\x00\x28\xa9cmt"
           + b"owner.private@example.org mix v3 final")
    case("L40-mp4-udta-metadata (F-L04)", "PUBLIC_MEDIA_METADATA", {"media/abc.mp4": mp4})
    case("L41-email-in-binary-strings (F-L04)", "PUBLIC_EMAIL_NOT_ALLOWLISTED", {"media/abc.mp4": mp4})
    case("L42-invalid-json", "PUBLIC_JSON_INVALID", {"data/broken.json": b'{"title": '})
    case("L43-entity-encoded-email (F-L05)", "PUBLIC_EMAIL_NOT_ALLOWLISTED",
         html("<p>contact: jei&#46;leal&#46;r&#64;gmail&#46;com</p>"), policy={**POLICY, "allowed_emails": []})
    return cases


def ci_cases(tmp: Path) -> list[dict]:
    wfdir = FIX / "workflows"
    offline = (wfdir / "offline-checks.yml").read_text()
    deploy = (wfdir / "deploy-website.yml").read_text()
    cases = []

    def case(name, expect, text, fname="offline-checks.yml", allow=True):
        p = tmp / name / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        codes = {x.split(":")[0] for x in ci_lint.lint(p, allow)}
        ok = (not codes) if expect is None else (expect in codes)
        cases.append({"case": name, "expect": expect or "clean", "got": sorted(codes), "pass": ok})

    case("C00-offline-checks-example", None, offline)
    case("C01-deploy-example", None, deploy, "deploy-website.yml")
    case("C02-placeholder-pins-refused-outside-test", "CI-R10_PLACEHOLDER_PIN", offline, allow=False)
    case("C03-pull-request-target", "CI-R1_FORBIDDEN_TRIGGER", offline.replace("pull_request:", "pull_request_target:"))
    case("C04-workflow-run-chain", "CI-R1_FORBIDDEN_TRIGGER",
         offline.replace("on:\n", "on:\n  workflow_run:\n    workflows: [x]\n"))
    case("C05-repository-dispatch", "CI-R1_FORBIDDEN_TRIGGER",
         offline.replace("on:\n", "on:\n  repository_dispatch:\n    types: [handoff]\n"))
    case("C06-deploy-on-push", "CI-R2_DEPLOY_NOT_MANUAL_ONLY",
         deploy.replace("on:\n", "on:\n  push:\n    branches: [main]\n"), "deploy-website.yml")
    case("C07-deploy-without-plan-digest", "CI-R2_DEPLOY_WITHOUT_PLAN_DIGEST",
         deploy.replace("plan_sha256:\n        description", "other:\n        description"), "deploy-website.yml")
    case("C08-write-all", "CI-R3_TOP_LEVEL_PERMISSIONS_NOT_READ_ONLY",
         offline.replace("permissions:\n  contents: read", "permissions: write-all"))
    case("C09-no-permissions", "CI-R3_TOP_LEVEL_PERMISSIONS_MISSING",
         offline.replace("permissions:\n  contents: read\n", ""))
    case("C10-no-concurrency", "CI-R4_CONCURRENCY_MISSING",
         offline.replace("concurrency:\n  group: offline-checks-${{ github.ref }}\n  cancel-in-progress: true\n", ""))
    case("C11-secret-in-check", "CI-R5_SECRET_IN_NON_DEPLOY_WORKFLOW",
         offline + "        env:\n          T: ${{ secrets.FELTWILLOW_PAGES_DEPLOY_TOKEN }}\n")
    case("C12-gemini-key", "CI-R6_PRODUCTION_CREDENTIAL_OR_COUPLING", offline + "# GEMINI_API_KEY\n")
    case("C13-production-checkout", "CI-R6_PRODUCTION_CREDENTIAL_OR_COUPLING",
         offline + "      - run: git clone git@github.com:jeilealr/feltwillow-production.git\n")
    case("C14-import-in-ci", "CI-R7_IMPORT_IN_CI", offline + "      - run: python -m feltwillow_publish import x.tar\n")
    case("C15-apply-in-check", "CI-R7_DEPLOY_COMMAND_IN_NON_DEPLOY_WORKFLOW",
         offline + "      - run: npx wrangler pages deploy dist\n")
    case("C16-self-hosted", "CI-R8_RUNNER_NOT_STANDARD_HOSTED", offline.replace("ubuntu-24.04", "self-hosted"))
    case("C17-no-timeout", "CI-R9_TIMEOUT_MISSING_OR_LARGE", offline.replace("    timeout-minutes: 15\n", ""))
    case("C18-unpinned-action", "CI-R10_ACTION_NOT_SHA_PINNED",
         offline.replace("actions/checkout@0000000000000000000000000000000000000000", "actions/checkout@v4"))
    case("C19-checkout-persists", "CI-R11_CHECKOUT_PERSISTS_CREDENTIALS",
         offline.replace("persist-credentials: false", "persist-credentials: true"))
    case("C20-cross-repo-artifact", "CI-R12_CROSS_REPO_ARTIFACT",
         offline + "      - uses: actions/download-artifact@0000000000000000000000000000000000000000\n"
                   "        with:\n          repository: jeilealr/feltwillow-production\n"
                   "          digest-mismatch: error\n")
    case("C21-artifact-digest-not-enforced", "CI-R12_ARTIFACT_DIGEST_NOT_ENFORCED",
         offline + "      - uses: actions/download-artifact@0000000000000000000000000000000000000000\n")
    case("C22-expression-injection", "CI-R13_EXPRESSION_IN_RUN",
         offline + "      - run: echo ${{ github.event.pull_request.title }}\n")
    case("C23-job-write-permission", "CI-R3_WRITE_PERMISSION_IN_NON_DEPLOY",
         offline.replace("    timeout-minutes: 15\n", "    timeout-minutes: 15\n    permissions:\n      contents: write\n"))
    return cases


def zero_cases() -> list[dict]:
    proj = json.loads((OPS / "project.zero_cost.example.json").read_text())
    inv = json.loads((OPS / "service-inventory.strict-zero.example.json").read_text())
    today = dt.date(2026, 10, 7)  # H2: owner storage evidence is dated 2026-10-07
    cases = []

    def case(name, expect, pmut=None, imut=None, today_=today):
        p, i = copy.deepcopy(proj), copy.deepcopy(inv)
        if pmut:
            pmut(p)
        if imut:
            imut(i)
        errs, _ = strict_zero.check(p, i, today_, 180)
        codes = {e.split(":")[0] for e in errs}
        ok = (not errs) if expect is None else (expect in codes)
        cases.append({"case": name, "expect": expect or "pass", "got": sorted(codes), "pass": ok})

    def svc(**kw):
        return lambda i: i["services"].append({"state": "enabled", "billing": {},
                                               "evidence": {"checked_at": "2026-10-06", "source": "x"}, **kw})

    def setsvc(idx, path, val):
        def f(i):
            d = i["services"][idx]
            for k in path[:-1]:
                d = d[k]
            d[path[-1]] = val
        return f

    case("Z00-strict-zero-example-passes", None)
    case("Z01-ghost-module", "ZERO_PROFILE_FORBIDDEN_CAPABILITY", pmut=lambda p: p["modules"].update(ghost="enabled"))
    case("Z02-commerce", "ZERO_PROFILE_FORBIDDEN_CAPABILITY", pmut=lambda p: p.update(commerce="enabled"))
    case("Z03-newsletter", "ZERO_PROFILE_FORBIDDEN_CAPABILITY", pmut=lambda p: p.update(newsletter="enabled"))
    case("Z04-independent-rss", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         pmut=lambda p: p.update(podcast_authority="independent"))
    case("Z05-custom-domain-origin", "ZERO_PROFILE_ORIGIN_NOT_PROVIDER_SUBDOMAIN",
         pmut=lambda p: p["website"].update(origin="https://feltwillow-example.com"))
    case("Z06-serverless-functions", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="website-serverless-functions", provider="cloudflare-workers", plan="free"))
    case("Z07-object-storage", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="website-object-storage", provider="cloudflare-r2", plan="free-allowance"))
    case("Z08-ghost-pro", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="website-managed-cms", provider="ghost-pro", plan="publisher"))
    case("Z09-vercel-hobby", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="website-static-host", provider="vercel", plan="hobby"))
    case("Z10-unknown-provider-fails-closed", "UNKNOWN_CAPABILITY_OR_PROVIDER",
         imut=svc(capability="website-static-host", provider="new-free-host", plan="free"))
    case("Z11-unknown-capability-fails-closed", "UNKNOWN_CAPABILITY_OR_PROVIDER",
         imut=svc(capability="ai-chatbot", provider="x", plan="free"))
    case("Z12-tts-in-publishing", "PUBLISHING_HOLDS_PRODUCTION_CAPABILITY",
         imut=svc(capability="tts-api", provider="gemini", plan="paid"))
    case("Z13-actions-payment-method", "ZERO_PROFILE_HARD_LIMIT_NOT_PROVEN",
         imut=setsvc(3, ["billing", "payment_method_on_file"], True))
    case("Z14-actions-larger-runner", "ZERO_PROFILE_FORBIDDEN_CAPABILITY", imut=setsvc(3, ["plan"], "larger"))
    case("Z15-auto-recharge", "ZERO_PROFILE_OVERAGE_ENABLED",
         imut=svc(capability="website-static-host", provider="netlify", plan="free",
                  billing={"payment_method_on_file": False, "auto_recharge": True}))
    case("Z16-stale-evidence", "COST_EVIDENCE_STALE", today_=dt.date(2027, 6, 1))
    case("Z17-missing-evidence", "COST_EVIDENCE_MISSING", imut=setsvc(0, ["evidence"], {}))
    case("Z18-github-pro-plan", "ZERO_PROFILE_FORBIDDEN_CAPABILITY", imut=setsvc(2, ["plan"], "pro"))
    case("Z19-two-hosts", "ZERO_PROFILE_MULTIPLE_HOSTS",
         imut=svc(capability="website-static-host", provider="netlify", plan="free",
                  billing={"payment_method_on_file": False, "auto_recharge": False}))
    case("Z20-host-undeclared", "ZERO_PROFILE_HOST_UNDECLARED", imut=setsvc(0, ["state"], "disabled"))
    case("Z21-profile-mismatch", "PROFILE_MISMATCH", imut=lambda i: i.update(profile="standard"))
    case("Z22-third-party-analytics", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="website-analytics-third-party", provider="any", plan="free"))
    case("Z23-paid-podcast-subscriptions", "ZERO_PROFILE_FORBIDDEN_CAPABILITY",
         imut=svc(capability="podcast-paid-subscriptions", provider="spotify-for-creators", plan="any"))
    case("Z24-standard-profile-allows-ghost-pro", None,
         pmut=lambda p: p.update(profile_option="astro"),
         imut=lambda i: (i.update(profile="standard"),
                         svc(capability="website-managed-cms", provider="ghost-pro", plan="publisher")(i)))
    case("Z25-tts-refused-even-in-standard", "PUBLISHING_HOLDS_PRODUCTION_CAPABILITY",
         pmut=lambda p: p.update(profile_option="astro"),
         imut=lambda i: (i.update(profile="standard"), svc(capability="tts-api", provider="gemini", plan="paid")(i)))
    return cases




def roots_cases(tmp: Path) -> list[dict]:
    out = []
    gitrepo = tmp / "repo"
    (gitrepo / ".git").mkdir(parents=True)
    od = tmp / "Library" / "CloudStorage" / "OneDrive-Personal"
    od.mkdir(parents=True)
    plain = tmp / "owner-disk" / "Feltwillow-master"
    plain.mkdir(parents=True)
    lax = {"lumi_prefixes": ()}

    def c(name, env, var, expect, **kw):
        try:
            state_roots.check_root(var, env, **kw)
            got = "ok"
        except state_roots.StateRootError as exc:
            got = exc.code
        out.append(mkcase(name, got == expect, expect=expect, got=got))
    c("unset", {}, "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSET")
    c("empty", {"FELTWILLOW_MASTER_ROOT": ""}, "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSET")
    c("relative", {"FELTWILLOW_MASTER_ROOT": "masters"}, "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSAFE")
    c("inside a git work tree", {"FELTWILLOW_PUBLISH_STATE_ROOT": str(gitrepo / "state")}, "FELTWILLOW_PUBLISH_STATE_ROOT", "STATE_ROOT_UNSAFE", **lax)
    c("inside a OneDrive folder (name)", {"FELTWILLOW_MASTER_ROOT": str(od / "Feltwillow")}, "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSAFE", **lax)
    c("inside configured OneDrive dir", {"FELTWILLOW_MASTER_ROOT": str(plain), "FELTWILLOW_ONEDRIVE_DIR": str(plain.parent)},
      "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSAFE", **lax)
    c("on LUMI scratch", {"FELTWILLOW_HANDOFF_INBOX": "/scratch/project_465002727/inbox"}, "FELTWILLOW_HANDOFF_INBOX", "STATE_ROOT_UNSAFE")
    c("on LUMI project storage", {"FELTWILLOW_MASTER_ROOT": "/projappl/project_465002727/m"}, "FELTWILLOW_MASTER_ROOT", "STATE_ROOT_UNSAFE")
    c("plain owner disk accepted", {"FELTWILLOW_MASTER_ROOT": str(plain)}, "FELTWILLOW_MASTER_ROOT", "ok", **lax)
    c("macOS-style path accepted", {"FELTWILLOW_MASTER_ROOT": "/Users/owner/Feltwillow-master"}, "FELTWILLOW_MASTER_ROOT", "ok")
    return out


def index_cases() -> list[dict]:
    clean = handoff_index_scan.scan(FIX / "handoff-index" / "clean")
    leaky = {f["code"] for f in handoff_index_scan.scan(FIX / "handoff-index" / "leaky")}
    return [mkcase("clean index", not clean, expect="clean", got=[f["code"] for f in clean]),
            mkcase("private field in index", "HANDOFF_INDEX_PRIVATE_FIELD" in leaky, expect="HANDOFF_INDEX_PRIVATE_FIELD", got=sorted(leaky)),
            mkcase("tar in index", "HANDOFF_INDEX_FORBIDDEN_FILE" in leaky, expect="HANDOFF_INDEX_FORBIDDEN_FILE", got=sorted(leaky))]


def owner_cases() -> list[dict]:
    proj = json.loads((EXAMPLES / "project.v2.example.json").read_text())
    inv = json.loads((EXAMPLES / "service-inventory.v1.example.json").read_text())
    errs, info = strict_zero.check(proj, inv, dt.date(2026, 10, 7), 180)
    zp = json.loads((OPS / "project.zero_cost.example.json").read_text())
    zi = json.loads((OPS / "service-inventory.strict-zero.example.json").read_text())
    v = V.validate(zp) + V.validate(zi)
    return [mkcase("owner project + inventory (standard profile) pass; OneDrive and HDD declared as owner infra",
                   not errs and sum("OWNER_INFRA_COST_DECLARED" in i for i in info) == 2, got={"errors": errs, "info": info}),
            mkcase("strict-zero fixtures are valid project.v2 / service-inventory.v1 records", not v, got=v)]


def run(ctx):
    tmp = ctx["tmp"] / "ops"
    tmp.mkdir(parents=True)
    try:
        lc = leak_cases(tmp / "leak")
        cc = ci_cases(tmp / "ci")
        rc = roots_cases(tmp / "roots")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"leak_scan": lc, "strict_zero": zero_cases() + owner_cases(), "ci_lint": cc,
            "state_roots": rc, "handoff_index_scan": index_cases()}
