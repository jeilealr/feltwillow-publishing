"""Offline validator for contract revision H2 records (PROPOSED CONTRACT).

Order of checks for every record (each step stops on failure; semantic checks report all codes found):
  1. canonical domain        (cj1.check_domain)            -> CJ_* codes
  2. version negotiation     (kind + schema_version)       -> UNKNOWN_RECORD_KIND, CONTRACT_VERSION_UNSUPPORTED
  3. path-safety pre-pass    (path-like fields)             -> UNSAFE_PATH, REMOTE_REFERENCE_FORBIDDEN
  4. JSON Schema 2020-12     (local registry, no retrieval) -> SCHEMA_VIOLATION
  5. semantic rules          (cross-field)                  -> specific codes (catalogue: error-codes.json)

Origin: Agent B's h1_contracts.py (handoff-contract draft H1), merged with Agent D's podcast semantics and
the lead's H2 rules. No network, no subprocess, no writes. Schemas load from publishing/contracts/schemas/.
Every result is a list of "CODE: context" strings; [] means valid.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from . import cj1

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "publishing" / "contracts" / "schemas"

# Consumer support table (version negotiation). A kind absent here is unknown.
SUPPORTED = {
    "production-handoff": {1}, "release": {2}, "approval": {2}, "import-receipt": {1},
    "public-bundle-manifest": {1}, "contract-lock": {1}, "story-allocation": {1},
    "web-bundle": {2}, "episode-publication": {2}, "provider-registry": {2}, "feed-observation": {1},
    "publish-plan": {2}, "publish-receipt": {2}, "media-delivery": {2}, "site-set": {2}, "project": {2},
    "service-inventory": {1}, "handoff-selection": {1}, "reading-edition": {1},
    # carried forward unchanged from the v2 package
    "catalog": {1}, "collection": {1}, "rights-review": {1}, "show": {1}, "story": {1},
}

ROLE_MEDIA = {
    "reading-text": {"application/vnd.feltwillow.reading-blocks+json"}, "spoken-transcript": {"text/plain"},
    "audio-master": {"audio/wav", "audio/flac"}, "audio-delivery": {"audio/mpeg", "audio/mp4"},
    "illustration": {"image/png", "image/jpeg", "image/webp"}, "cover-art": {"image/png", "image/jpeg"},
    "video-master": {"video/mp4", "video/quicktime"}, "video-delivery": {"video/mp4"},
    "thumbnail": {"image/png", "image/jpeg"}, "captions": {"text/vtt"}, "chapters": {"application/json"},
}
REQUIRED_MEASURES = {
    "illustration": ("width_px", "height_px"), "cover-art": ("width_px", "height_px"),
    "thumbnail": ("width_px", "height_px"),
    "audio-master": ("duration_ms", "sample_rate_hz", "channels"),
    "audio-delivery": ("duration_ms", "sample_rate_hz", "channels"),
    "video-master": ("duration_ms", "width_px", "height_px", "frame_rate"),
    "video-delivery": ("duration_ms", "width_px", "height_px", "frame_rate"),
}
COMPONENT_ROLES = {
    ("images", "illustration_assets"): {"illustration"}, ("images", "cover_asset"): {"cover-art"},  # L-28
    ("audio", "master_asset"): {"audio-master"},
    ("audio", "transcript_asset"): {"spoken-transcript"},
    ("video", "master_asset"): {"video-master"}, ("video", "captions_asset"): {"captions"},
    ("video", "thumbnail_asset"): {"thumbnail"},
}
PATH_KEYS = {"path", "package_path", "dirty_paths", "record_path", "draft_path", "artifact_path"}
URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://|^//|^[A-Za-z]:\\")


def _load_registry():
    schemas, resources = {}, []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        raw = path.read_bytes()
        data = cj1.loads_strict(raw)
        Draft202012Validator.check_schema(data)
        resources.append((data["$id"], Resource.from_contents(data)))
        props = data.get("properties", {})
        if "kind" in props:
            schemas[(props["kind"]["const"], props["schema_version"]["const"])] = data
    return schemas, Registry().with_resources(resources)


SCHEMAS, REGISTRY = _load_registry()


def schema_files():
    return sorted(SCHEMA_DIR.glob("*.schema.json"))


def codes(errors) -> list[str]:
    return sorted({e.split(":")[0] for e in errors})


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _walk(value, trail=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield trail + (k,), v
            yield from _walk(v, trail + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield trail + (i,), v
            yield from _walk(v, trail + (i,))


def unsafe_relpath(p: str) -> bool:
    if not p or p.startswith("/") or "\\" in p or "\x00" in p or URL_RE.match(p):
        return True
    return any(seg in ("", ".", "..") for seg in p.split("/"))


def prepass(data) -> list[str]:
    errs = []
    for trail, value in _walk(data):
        key = next((t for t in reversed(trail) if isinstance(t, str)), "")
        if key in PATH_KEYS and isinstance(value, str) and unsafe_relpath(value):
            # web-bundle "path" values are public URL routes (/en/...), not filesystem paths (v2 rule kept)
            if not (data.get("kind") == "web-bundle" and key == "path"):
                errs.append("UNSAFE_PATH: " + ".".join(map(str, trail)))
        if key == "ref" and isinstance(value, str) and (URL_RE.match(value) or value.startswith("/")):
            errs.append("REMOTE_REFERENCE_FORBIDDEN: " + ".".join(map(str, trail)))
    return errs


def schema_errors(data) -> list[str]:
    schema = SCHEMAS[(data["kind"], data["schema_version"])]
    v = Draft202012Validator(schema, registry=REGISTRY, format_checker=FormatChecker())
    errs = sorted(v.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    return ["SCHEMA_VIOLATION: " + ".".join(map(str, e.absolute_path)) + ": " + e.message[:200] for e in errs]


def validate(data) -> list[str]:
    """Return a list of 'CODE: context' strings; empty means structurally and semantically valid."""
    try:
        cj1.check_domain(data)
    except cj1.CanonicalError as exc:
        return [exc.code + ": " + str(exc)]
    if not isinstance(data, dict) or data.get("kind") not in SUPPORTED:
        return ["UNKNOWN_RECORD_KIND"]
    if data.get("schema_version") not in SUPPORTED[data["kind"]]:
        return [f"CONTRACT_VERSION_UNSUPPORTED: {data['kind']} schema_version={data.get('schema_version')!r} "
                f"supported={sorted(SUPPORTED[data['kind']])}"]
    pre = prepass(data)
    if pre:
        return pre
    errs = schema_errors(data)
    if errs:
        return errs
    fn = SEMANTIC.get(data["kind"])
    return url_errors(data) + (fn(data) if fn else [])


URL_KEYS = ("url", "origin", "external_url")


def url_errors(data) -> list[str]:
    """v2 rule UNSAFE_URL: every URL-valued field is https with a host and no credentials. Feed observations
    record raw observed values and are exempt (their problems list reports non-https enclosures)."""
    if data["kind"] == "feed-observation":
        return []
    e = []
    for trail, value in _walk(data):
        key = trail[-1] if isinstance(trail[-1], str) else ""
        if (key in URL_KEYS or key.endswith("_url")) and isinstance(value, str) and not value.startswith("/media/"):
            try:
                parts = urlsplit(value)
                bad = parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            except ValueError:
                bad = True
            if bad:
                e.append("UNSAFE_URL: " + ".".join(map(str, trail)))
    return e


# ---------------------------------------------------------------- B: production-handoff
def sem_handoff(d) -> list[str]:
    e = []
    p = d["payload"]
    if p["handoff_id"] != f"{p['story_id']}.{p['language']}.h{p['handoff_revision']:04d}":
        e.append("HANDOFF_ID_MISMATCH")
    if p["handoff_revision"] == 1:
        if p["supersedes"] is not None:
            e.append("SUPERSEDES_UNEXPECTED")
        if p["purpose"] != "initial":
            e.append("PURPOSE_REVISION_MISMATCH")
    else:
        if p["supersedes"] is None:
            e.append("SUPERSEDES_REQUIRED")
        elif not p["supersedes"]["handoff_id"].startswith(f"{p['story_id']}.{p['language']}.h"):
            e.append("SUPERSEDES_OTHER_EDITION")
        elif int(p["supersedes"]["handoff_id"][-4:]) >= p["handoff_revision"]:
            e.append("SUPERSEDES_NOT_EARLIER")
        if p["purpose"] == "initial":
            e.append("PURPOSE_REVISION_MISMATCH")
        if not p["reason"]:
            e.append("REASON_REQUIRED")
    by_id = {}
    for a in p["assets"]:
        if a["asset_id"] in by_id:
            e.append("DUPLICATE_ASSET_ID: " + a["asset_id"])
        by_id[a["asset_id"]] = a
    paths = [a["package_path"] for a in p["assets"] if a["package_path"]]
    if len(paths) != len(set(paths)) or len({x.lower() for x in paths}) != len(paths):
        e.append("DUPLICATE_PACKAGE_PATH")
    for a in p["assets"]:
        aid = a["asset_id"]
        if a["media_type"] not in ROLE_MEDIA[a["role"]]:
            e.append(f"MEDIA_TYPE_ROLE_MISMATCH: {aid}")
        # L-29: lossless audio only; measured media carry tool provenance; video measured by ffprobe
        if a["media_type"] in ("audio/mpeg", "audio/mp4"):
            e.append(f"HANDOFF_AUDIO_NOT_LOSSLESS: {aid}")
        if a["media_type"].split("/")[0] in ("image", "audio", "video") and a["measurement"] is None:
            e.append(f"MEASUREMENT_PROVENANCE_MISSING: {aid}")
        if (a["media_type"].startswith("video/") and a["measurement"] is not None
                and a["measurement"]["tool"] != "ffprobe"):
            e.append(f"VIDEO_MEASUREMENT_REQUIRES_FFPROBE: {aid}")
        for m in REQUIRED_MEASURES.get(a["role"], ()):
            if a["measured"][m] is None:
                e.append(f"MISSING_MEASUREMENT: {aid}.{m}")
        if a["transport"] == "referenced":
            e.append(f"REFERENCED_MEDIA_NOT_SUPPORTED: {aid}")
        elif a["package_path"] is None:
            e.append(f"PACKAGE_PATH_MISSING: {aid}")
        elif a["package_path"].split("/")[1] != aid:
            e.append(f"PACKAGE_PATH_MISMATCH: {aid}")
        if (a["origin"]["store"] == "production-git") != (a["origin"]["commit"] is not None):
            e.append(f"ORIGIN_COMMIT_INCONSISTENT: {aid}")
        if a["origin"]["store"] == "production-git" and unsafe_relpath(a["origin"]["ref"]):
            e.append(f"UNSAFE_PATH: {aid}.origin.ref")
        for parent in a["derived_from"]:
            if parent["sha256"] == a["sha256"]:
                e.append(f"DERIVATION_CYCLE: {aid}")
            if parent["asset_id"] is not None and parent["asset_id"] not in by_id:
                e.append(f"UNKNOWN_PARENT_ASSET: {aid}")
            elif parent["asset_id"] is not None and by_id[parent["asset_id"]]["sha256"] != parent["sha256"]:
                e.append(f"PARENT_HASH_MISMATCH: {aid} -> {parent['asset_id']}")
    graph = {a["asset_id"]: [x["asset_id"] for x in a["derived_from"] if x["asset_id"] in by_id] for a in p["assets"]}
    state = {}

    def dfs(n):
        state[n] = 1
        for m in graph[n]:
            if state.get(m) == 1 or (state.get(m) is None and dfs(m)):
                return True
        state[n] = 2
        return False
    if any(state.get(n) is None and dfs(n) for n in graph):
        e.append("DERIVATION_CYCLE")
    comps = p["components"]
    if p["purpose"] == "revocation":
        if any(comps.values()) or p["assets"]:
            e.append("REVOCATION_WITH_ASSETS")
    elif not any(comps.values()):
        e.append("NO_COMPONENTS")
    used = set()
    for (comp, field), roles in COMPONENT_ROLES.items():
        c = comps.get(comp)
        if not c:
            continue
        for aid in (c[field] if isinstance(c[field], list) else [c[field]]):
            if aid is None:
                continue
            used.add(aid)
            if aid not in by_id:
                e.append(f"UNKNOWN_ASSET: {comp}.{field}={aid}")
            elif by_id[aid]["role"] not in roles:
                e.append(f"WRONG_ASSET_ROLE: {comp}.{field}={aid}")
    unused = set(by_id) - used
    if unused:
        e.append("UNREFERENCED_ASSET: " + ",".join(sorted(unused)))
    repo = p["source_repositories"][0]
    dirty = set(repo["worktree"]["dirty_paths"])
    if (repo["worktree"]["state"] == "clean") != (not dirty):
        e.append("WORKTREE_STATE_INCONSISTENT")
    for s in p["source_files"]:
        if s["commit"] != repo["commit"]:
            e.append(f"SOURCE_COMMIT_MISMATCH: {s['source_id']}")
        if s["path"] in dirty:
            e.append(f"SELECTED_SOURCE_DIRTY: {s['path']}")
    for a in p["assets"]:
        if a["origin"]["store"] == "production-git":
            if a["origin"]["commit"] != repo["commit"]:
                e.append(f"SOURCE_COMMIT_MISMATCH: {a['asset_id']}")
            if a["origin"]["ref"] in dirty:
                e.append(f"SELECTED_SOURCE_DIRTY: {a['origin']['ref']}")
    if d["envelope"]["exporter"]["tool_dirty"]:
        e.append("EXPORTER_DIRTY")
    if len({s["source_id"] for s in p["source_files"]}) != len(p["source_files"]):
        e.append("DUPLICATE_SOURCE_ID")
    for g in p["generation_provenance"]:
        if g["asset_id"] not in by_id:
            e.append("UNKNOWN_ASSET: generation_provenance." + g["asset_id"])
    if _ts(d["envelope"]["created_at"]) < _ts(p["editorial_selection"]["selected_at"]):
        e.append("TIMESTAMP_ORDER")
    return e


# ---------------------------------------------------------------- B: release, approval, receipt, manifest, lock
def sem_release(d) -> list[str]:
    e = []
    if d["release_id"] != f"{d['story_id']}.{d['language']}.r{d['revision']:04d}":
        e.append("RELEASE_ID_MISMATCH")
    c = d["content"]
    if c["age_min"] > c["age_max"]:
        e.append("AGE_RANGE_REVERSED")
    if (d["revision"] == 1) != (d["supersedes"] is None):
        e.append("SUPERSEDES_INCONSISTENT")
    listed = {h["handoff_id"] for h in d["handoffs"]}
    assets = {}
    for a in d["assets"]:
        if a["asset_id"] in assets:
            e.append("DUPLICATE_ASSET_ID")
        assets[a["asset_id"]] = a
        o = a["origin"]
        if o["kind"] == "handoff":
            if o["handoff_id"] is None or o["handoff_asset_id"] is None:
                e.append("ORIGIN_INCOMPLETE: " + a["asset_id"])
            elif o["handoff_id"] not in listed:
                e.append("UNLISTED_HANDOFF: " + a["asset_id"])
        elif a["derived_from_sha256"] is None:
            e.append("DERIVATIVE_WITHOUT_PARENT: " + a["asset_id"])
        if a["role"] in ("image", "podcast-cover") and (not a["width"] or not a["height"]):
            e.append("MISSING_IMAGE_DIMENSIONS")
        if a["role"] in ("audio-master", "podcast-audio", "video-master") and not a["duration_ms"]:
            e.append("MISSING_MEDIA_DURATION")
    # L-28: the reading text is a publishing-authored reading-edition record, pinned per release
    ed = c["reading_edition"]
    if ed is not None and not ed["edition_id"].startswith(f"{d['story_id']}.{d['language']}.e"):
        e.append("READING_EDITION_MISMATCH")
    if d["channels"]["website"]["requested"] and ed is None:
        e.append("READING_EDITION_MISSING")
    for field, roles in (("spoken_transcript_asset", ("transcript",)),):
        aid = c[field]
        if aid is not None and (aid not in assets or assets[aid]["role"] not in roles):
            e.append("UNKNOWN_ASSET: content." + field)
    for b in c["blocks"]:
        if b["type"] == "image" and (b["asset_id"] not in assets or assets[b["asset_id"]]["role"] not in ("image", "podcast-cover")):
            e.append("UNKNOWN_ASSET: block " + b["asset_id"])
    # v2 channel rules (ported, B1)
    def asset_ref(value, roles, where):
        if value is not None:
            if value not in assets:
                e.append(f"UNKNOWN_ASSET: channels.{where}={value}")
            elif assets[value]["role"] not in roles:
                e.append(f"WRONG_ASSET_ROLE: channels.{where}={value}")
    w, pc, y = (d["channels"][k] for k in ("website", "podcast", "youtube"))
    asset_ref(w["audio_asset"], ("podcast-audio",), "website.audio_asset")
    asset_ref(w["cover_asset"], ("image", "podcast-cover"), "website.cover_asset")
    asset_ref(pc["audio_asset"], ("podcast-audio",), "podcast.audio_asset")
    asset_ref(pc["artwork_asset"], ("podcast-cover",), "podcast.artwork_asset")
    asset_ref(pc["chapters_asset"], ("chapters",), "podcast.chapters_asset")
    asset_ref(y["video_asset"], ("video-master",), "youtube.video_asset")
    asset_ref(y["thumbnail_asset"], ("image",), "youtube.thumbnail_asset")
    if w["player"] == "native_audio" and w["audio_asset"] is None:
        e.append("NATIVE_AUDIO_REFERENCE_MISSING")
    if w["player"] == "spotify_embed" and not w["podcast_episode_id"]:
        e.append("SPOTIFY_EPISODE_REFERENCE_MISSING")
    if d["lifecycle"] == "frozen":
        if not d["handoffs"]:
            e.append("FROZEN_WITHOUT_HANDOFF")
        if d["frozen_with"] is None:
            e.append("FROZEN_WITHOUT_TOOLING_PROVENANCE")
    elif d["frozen_with"] is not None:
        e.append("DRAFT_WITH_FREEZE_PROVENANCE")
    o = d["emergency_override"]
    if o and o["backport"] == "backported" and o["backport_handoff"] is None:
        e.append("BACKPORT_REFERENCE_MISSING")
    return e


STAGE_RULES = {
    "editorial-rights": ({"release"}, {"edition", "rights_review.podcast_audio"}),
    "channel-readiness": ({"release"}, {"website", "podcast", "youtube"}),
    "deployment": ({"publish-plan", "site-set", "project"}, {"website", "podcast", "youtube", "configuration"}),
}
PODCAST_AUDIO_REVIEW_CHECKS = ("gemini-terms-answer", "mix-music-and-effects")


def sem_approval(d) -> list[str]:
    e = []
    subjects, scopes = STAGE_RULES[d["stage"]]
    if d["subject_type"] not in subjects or d["scope"] not in scopes:
        e.append("STAGE_SUBJECT_MISMATCH")
    names = [c["name"] for c in d["checks"]]
    if len(names) != len(set(names)):
        e.append("DUPLICATE_APPROVAL_CHECK")
    if d["decision"] == "approved":
        if not names or any(c["result"] == "fail" for c in d["checks"]):
            e.append("INVALID_POSITIVE_APPROVAL")
        if d["revokes"] is not None:
            e.append("REVOCATION_TARGET_UNEXPECTED")
        if d["stage"] in ("channel-readiness", "deployment") and not d["depends_on"]:
            e.append("APPROVAL_CHAIN_MISSING")
        if d["scope"] == "rights_review.podcast_audio":
            missing = [n for n in PODCAST_AUDIO_REVIEW_CHECKS if n not in names]
            if missing:
                e.append("RIGHTS_REVIEW_EVIDENCE_MISSING: " + ",".join(missing))
    elif d["decision"] == "revoked":
        if d["revokes"] is None:
            e.append("REVOCATION_TARGET_MISSING")
        if not d["reason"]:
            e.append("REASON_REQUIRED")
    elif d["revokes"] is not None:
        e.append("REVOCATION_TARGET_UNEXPECTED")
    if d["approval_id"] in {x["approval_id"] for x in d["depends_on"]}:
        e.append("APPROVAL_SELF_DEPENDENCY")
    return e


def sem_receipt(d) -> list[str]:
    e = []
    if d["outcome"] == "accepted" and not d["example"] and d["expected_digest_source"] != "operator-out-of-band":
        e.append("RECEIPT_DIGEST_SOURCE_REQUIRED")  # M1: acceptance needs a trusted out-of-band digest
    o = d["outcome"]
    if o == "accepted" and (d["errors"] or not d["promoted"] or d["archival_locator"] is None
                            or d["payload_sha256"] is None or d["duplicate_of"] is not None):
        e.append("RECEIPT_OUTCOME_INCONSISTENT")
    if o == "rejected" and (not d["errors"] or d["promoted"] or d["duplicate_of"] is not None):
        e.append("RECEIPT_OUTCOME_INCONSISTENT")
    if o == "duplicate-identical" and (d["duplicate_of"] is None or d["promoted"] or d["errors"]):
        e.append("RECEIPT_OUTCOME_INCONSISTENT")
    if (d["expected_digest_source"] == "operator-out-of-band") != (d["expected_archive_sha256"] is not None):
        e.append("DIGEST_SOURCE_INCONSISTENT")
    elif d["expected_archive_sha256"] is not None and d["expected_archive_sha256"] != d["archive"]["sha256"] and o != "rejected":
        e.append("ARCHIVE_DIGEST_MISMATCH")
    if _ts(d["finished_at"]) < _ts(d["staged_at"]):
        e.append("TIMESTAMP_ORDER")
    if d["archival_locator"] and d["archival_locator"] != f"handoffs/{d['archive']['sha256']}.tar":
        e.append("ARCHIVAL_LOCATOR_MISMATCH")
    return e


def sem_public_manifest(d) -> list[str]:
    from ..ops.leak_scan import FORBIDDEN_NAME  # E's wider rule replaces B's PUBLIC_FORBIDDEN (IC-E5)
    e = []
    paths = [f["path"] for f in d["files"]]
    if len(paths) != len(set(paths)) or len({p.lower() for p in paths}) != len(paths):
        e.append("DUPLICATE_PUBLIC_PATH")
    for p in paths:
        if FORBIDDEN_NAME.search(p):
            e.append("PUBLIC_FORBIDDEN_FILE: " + p)
    if d["bundle_type"] == "web" and d["inputs"]["site_set"] is None:
        e.append("WEB_BUNDLE_WITHOUT_SITE_SET")
    return e


def sem_lock(d) -> list[str]:
    paths = [f["path"] for f in d["files"]]
    e = []
    if len(paths) != len(set(paths)):
        e.append("DUPLICATE_LOCK_PATH")
    if f"schemas/production-handoff.v{d['producer_emits']['production-handoff']}.schema.json" not in paths:
        e.append("LOCK_MISSING_EMITTED_SCHEMA")
    return e


# ---------------------------------------------------------------- lead: H2 new versions
def _pins(d) -> list[str]:
    e = []
    if d["contract_version"] != d["contract_package"]["version"]:
        e.append("CONTRACT_VERSION_PIN_MISMATCH")
    ids = [h["handoff_id"] for h in d["handoff_package_digests"]]
    if len(ids) != len(set(ids)):
        e.append("DUPLICATE_HANDOFF_PIN")
    return e


TARGET_DESTINATION = {"static-site": "website", "ghost": "website", "spotify": "podcast",
                      "independent-rss": "podcast", "apple": "directory", "amazon": "directory",
                      "pocket_casts": "directory", "youtube": "youtube"}
TARGET_OPERATIONS = {
    "static-site": {"deploy", "withdraw", "manual_redirect"},
    "ghost": {"create-draft", "update-draft", "publish", "withdraw", "deploy"},
    "spotify": {"manual-upload", "publish", "manual_metadata_edit", "manual_audio_replace", "observe_feed",
                "manual_redirect", "withdraw"},
    "independent-rss": {"deploy", "manual_audio_replace", "observe_feed", "manual_redirect", "withdraw"},
    "apple": {"manual-submit", "manual_metadata_edit", "withdraw"},
    "amazon": {"manual-submit", "manual_metadata_edit", "withdraw"},
    "pocket_casts": {"manual-submit", "withdraw"},
    "youtube": {"manual-upload", "manual_metadata_edit", "withdraw"},
}
ARTIFACT_REQUIRED_OPS = {"deploy", "manual-upload", "manual_audio_replace", "create-draft", "update-draft"}
ARTIFACT_FORBIDDEN_OPS = {"observe_feed", "manual-submit", "manual_redirect"}
PODCAST_RECORD_KINDS = {"show", "episode-publication", "feed-observation", "media-delivery"}
GHOST_AUX = {"ghost-theme", "ghost-routes", "ghost-redirects", "ghost-post-payload"}


def sem_plan(d) -> list[str]:
    e = _pins(d)
    if _ts(d["expires_at"]) <= _ts(d["created_at"]):
        e.append("PLAN_EXPIRY_ORDER")  # v2 code (was TIMESTAMP_ORDER in the first H2 build)
    ids = [a["action_id"] for a in d["actions"]]
    if len(ids) != len(set(ids)):
        e.append("DUPLICATE_ACTION")  # v2 code (was DUPLICATE_ACTION_ID)
    if d["environment"] == "production" and not d["actions"]:
        e.append("EMPTY_PRODUCTION_PLAN")  # v2 rule
    rel = [r["release_id"] for r in d["releases"]]
    if len(rel) != len(set(rel)):
        e.append("DUPLICATE_RELEASE_PIN")
    for a in d["actions"]:
        tag = a["action_id"]
        if TARGET_DESTINATION[a["target"]] != d["destination"]:
            e.append(f"ACTION_DESTINATION_MISMATCH: {tag}")
        if a["operation"] not in TARGET_OPERATIONS[a["target"]]:
            e.append(f"UNSUPPORTED_OPERATION: {tag} {a['target']}/{a['operation']}")  # v2 code
        if a["operation"] in ARTIFACT_REQUIRED_OPS and a["artifact"] is None:
            e.append(f"ARTIFACT_REQUIRED: {tag}")
        if a["operation"] in ARTIFACT_FORBIDDEN_OPS and a["artifact"] is not None:
            e.append(f"ARTIFACT_UNEXPECTED: {tag}")
    aux = {x["record_kind"] for x in d["auxiliary_inputs"]}
    if d["destination"] == "website" and aux & PODCAST_RECORD_KINDS:
        e.append("WEBSITE_PLAN_TOUCHES_PODCAST: " + ",".join(sorted(aux & PODCAST_RECORD_KINDS)))  # IC-D12
    if aux & GHOST_AUX and not any(a["target"] == "ghost" for a in d["actions"]):
        e.append("GHOST_INPUT_WITHOUT_GHOST_ACTION")
    uploads_web = any(a["target"] in ("static-site", "ghost") and a["operation"] in ("deploy", "publish")
                      for a in d["actions"])
    if uploads_web and d["check_reports"]["leak_scan"] is None:
        e.append("LEAK_SCAN_REPORT_REQUIRED")
    if d["environment"] == "production" and d["actions"] and d["check_reports"]["strict_zero"] is None:
        e.append("STRICT_ZERO_REPORT_REQUIRED")
    if d["destination"] == "website" and uploads_web and d["site_set"] is None:
        e.append("WEB_PLAN_WITHOUT_SITE_SET")
    return e


def sem_publish_receipt(d) -> list[str]:
    e = []
    if (d["result"] == "conflict") != (d["conflict"] is not None):
        e.append("CONFLICT_INCONSISTENT")
    if d["result"] == "succeeded" and d["evidence"] is None:
        e.append("RECEIPT_EVIDENCE_REQUIRED")
    if d["result"] == "manual_pending" and any(d[k] is not None for k in ("external_id", "external_url", "observation_id")):
        e.append("MANUAL_PENDING_WITH_OUTCOME")
    if d["result"] == "succeeded" and d["operation"] == "observe_feed" and d["observation_id"] is None:
        e.append("OBSERVATION_ID_REQUIRED")
    if d["result"] == "succeeded" and d["operation"] in ("manual-upload", "manual_audio_replace") and d["submitted_sha256"] is None:
        e.append("SUBMITTED_SHA256_REQUIRED")
    return e


def sem_media_delivery(d) -> list[str]:
    urls = [r["url"] for r in d["records"]]
    return ["DUPLICATE_DELIVERY_URL"] if len(urls) != len(set(urls)) else []


def sem_site_set(d) -> list[str]:
    e = _pins(d)
    ids = [r["release_id"] for r in d["entries"]]
    keys = [r.rsplit(".r", 1)[0] for r in ids]
    if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
        e.append("DUPLICATE_SITE_EDITION")  # v2 code
    if len(d["remove_paths"]) != len(set(d["remove_paths"])):
        e.append("DUPLICATE_REMOVAL")
    if any(".." in x.split("/") or "//" in x or "?" in x or "#" in x for x in d["remove_paths"]):
        e.append("UNSAFE_REMOVAL_PATH")
    if d["lifecycle"] == "frozen" and not d["entries"] and not d["remove_paths"]:
        e.append("SITE_SET_EMPTY")
    return e


def sem_project(d) -> list[str]:
    e = []
    podcast_on = "enabled" in (d["modules"]["spotify_hosted"], d["modules"]["independent_rss"])
    if d["public_contact_acknowledged"] and d["public_contact_email"] is None:
        e.append("PUBLIC_CONTACT_ACK_WITHOUT_EMAIL")
    if podcast_on and (d["public_contact_email"] is None or not d["public_contact_acknowledged"]):
        e.append("PUBLIC_CONTACT_REQUIRED")
    if podcast_on and d["ai_disclosure"] is None:
        e.append("AI_DISCLOSURE_REQUIRED")  # Apple Podcasts guideline 1.11 (Agent D)
    if d["profile_option"] == "zero_cost" and d["service_inventory"] is None:
        e.append("SERVICE_INVENTORY_REQUIRED")
    modules, primary = d["modules"], d["website"]["primary"]
    if primary != "none" and modules[primary] == "spec_only":
        e.append("PRIMARY_MODULE_SPEC_ONLY")
    # v2 project rules (ported, B1)
    enabled_web = [x for x in ("astro", "ghost", "plain_static") if modules[x] == "enabled"]
    if len(enabled_web) > 1:
        e.append("MULTIPLE_WEBSITES")
    if primary == "none" and enabled_web:
        e.append("PRIMARY_NOT_SELECTED")
    if primary != "none" and modules[primary] != "enabled":
        e.append("MODULE_NOT_ENABLED: " + primary)
    if primary != "none" and not d["website"]["origin"]:
        e.append("MISSING_ORIGIN")
    if modules["spotify_hosted"] == modules["independent_rss"] == "enabled":
        e.append("MULTIPLE_FEED_AUTHORITIES")
    chosen = {"spotify": "spotify_hosted", "independent": "independent_rss"}.get(d["podcast_authority"])
    enabled_feed = [m for m in ("spotify_hosted", "independent_rss") if modules[m] == "enabled"]
    # Adapted (DEPRECATED_V2_RULES.md): H2 lets the owner record the decided authority before its module is
    # enabled; an ENABLED feed module must be the chosen authority's module.
    if chosen and enabled_feed and chosen not in enabled_feed:
        e.append("FEED_MODULE_NOT_ENABLED")
    if not chosen and enabled_feed:
        e.append("FEED_AUTHORITY_NOT_SELECTED")
    if d["profile_option"] == "zero_cost" and (modules["ghost"] == "enabled" or d["newsletter"] == "enabled"
                                               or d["commerce"] == "enabled" or d["podcast_authority"] == "independent"):
        e.append("ZERO_PROFILE_FORBIDDEN_CAPABILITY")
    if d["safety"]["production_enabled"] and not d["safety"]["allow_remote_writes"]:
        e.append("PRODUCTION_WRITE_SWITCH_CONFLICT")
    return e


# ---------------------------------------------------------------- v2 kinds carried forward (B1)
def sem_catalog_or_story(d) -> list[str]:
    values = [x["story_id"] for x in d["stories"]] if d["kind"] == "catalog" else [x["language"] for x in d["editions"]]
    return ["DUPLICATE_CATALOG_OR_EDITION"] if len(values) != len(set(values)) else []


RIGHTS_COMPONENTS_REQUIRED = {"underlying-story", "adaptation", "translation", "voices", "images", "music",
                              "sound-effects", "video", "compute-resources"}


def sem_rights_review(d) -> list[str]:
    e = []
    names = [c["component"] for c in d["checks"]]
    if len(names) != len(set(names)):
        e.append("DUPLICATE_RIGHTS_COMPONENT")
    if d["status"] == "cleared" and (set(names) != RIGHTS_COMPONENTS_REQUIRED or any(
            c["decision"] not in ("cleared", "not-applicable") or not c["reviewed_by"] or not c["reviewed_at"]
            for c in d["checks"])):
        e.append("INCOMPLETE_RIGHTS_CLEARANCE")
    return e


def sem_collection(d) -> list[str]:
    e = []
    own = [x["asset_id"] for x in d["assets"]]
    if len(own) != len(set(own)):
        e.append("DUPLICATE_COLLECTION_ASSET")
    if d["master_asset_id"] is not None and d["master_asset_id"] not in own:
        e.append("COLLECTION_MASTER_REFERENCE_MISSING")
    order = [x["order"] for x in d["items"]]
    if sorted(order) != list(range(1, len(order) + 1)):
        e.append("COLLECTION_ORDER_INVALID")
    if len({x["episode_id"] for x in d["items"]}) != len(d["items"]):
        e.append("DUPLICATE_COLLECTION_EPISODE")
    return e


def readiness_errors(release, channel) -> list[str]:
    """v2 declarative_readiness_errors, ported to release.v2. Only checks declarations: an empty result is
    NOT permission to publish (approvals and live checks still apply)."""
    errors = validate(release)
    if errors or release.get("kind") != "release":
        return errors or ["NOT_A_RELEASE"]
    if release["example"]:
        errors.append("EXAMPLE_RECORD")
    if release["lifecycle"] != "frozen":
        errors.append("RELEASE_NOT_FROZEN")
    if release["rights"]["status"] != "cleared":
        errors.append("RIGHTS_NOT_CLEARED")
    if release["rights"]["record_sha256"] is None:
        errors.append("RIGHTS_RECORD_HASH_MISSING")
    if not release["handoffs"]:
        errors.append("SOURCE_HASH_MISSING")  # v2 sources[] are pinned handoffs in H2
    if not release["channels"][channel]["requested"]:
        errors.append("CHANNEL_NOT_REQUESTED")
    if channel == "website" and release["content"]["reading_edition"] is None:
        errors.append("READING_EDITION_MISSING")
    required = {"website": ["cover_asset"], "podcast": ["audio_asset", "artwork_asset"],
                "youtube": ["video_asset", "thumbnail_asset"]}[channel]
    assets = {x["asset_id"]: x for x in release["assets"]}
    for field in required:
        aid = release["channels"][channel][field]
        if aid not in assets:
            errors.append("MISSING_ASSET: " + field)
        elif assets[aid]["selection"] != "approved":
            errors.append("UNAPPROVED_ASSET: " + field)
    if channel == "podcast":
        pc = release["channels"]["podcast"]
        if not pc["show_id"] or not pc["episode_id"]:
            errors.append("PODCAST_ID_MISSING")
        cover = assets.get(pc["artwork_asset"])
        if cover and (cover["width"] != cover["height"] or not (1400 <= (cover["width"] or 0) <= 3000)):
            errors.append("PODCAST_COVER_DIMENSIONS")
    return errors


def sem_reading_edition(d) -> list[str]:
    """reading-edition.v1 (L-28)."""
    e = []
    if d["edition_id"] != f"{d['story_id']}.{d['language']}.e{d['revision']:04d}":
        e.append("READING_EDITION_ID_MISMATCH")
    if (d["revision"] == 1) != (d["supersedes"] is None):
        e.append("SUPERSEDES_INCONSISTENT")
    if d["source_script"]["handoff_id"].rsplit(".h", 1)[0] != f"{d['story_id']}.{d['language']}":
        e.append("READING_SOURCE_OTHER_EDITION")
    ills = {}
    for i in d["illustrations"]:
        if i["asset_id"] in ills:
            e.append("DUPLICATE_ASSET_ID: " + i["asset_id"])
        ills[i["asset_id"]] = i
    used = set()
    for b in d["blocks"]:
        if b["type"] == "image":
            used.add(b["asset_id"])
            if b["asset_id"] not in ills:
                e.append("UNKNOWN_ASSET: block " + b["asset_id"])
    if set(ills) - used:
        e.append("UNREFERENCED_ASSET: " + ",".join(sorted(set(ills) - used)))
    if not any(b["type"] in ("paragraph", "quote") for b in d["blocks"]):
        e.append("READING_EDITION_WITHOUT_TEXT")
    return e


def sem_service_inventory(d) -> list[str]:
    keys = [(s["capability"], s["provider"]) for s in d["services"]]
    return ["DUPLICATE_SERVICE"] if len(keys) != len(set(keys)) else []


SELECTION_SLOTS = {"images": {"illustration_assets", "cover_asset"},
                   "audio": {"master_asset", "transcript_asset"},
                   "video": {"master_asset", "captions_asset", "thumbnail_asset"}}


def sem_selection(d) -> list[str]:
    """handoff-selection.v1 (L-23). Mirrors the static rules of production/export_handoff.py (G3); the
    exporter additionally checks Git state, bytes and the allocation, which need the production checkout."""
    e = []
    rev, purpose, sup = d["handoff_revision"], d["purpose"], d["supersedes"]
    if (rev == 1) != (sup is None) or (rev == 1) != (purpose == "initial"):
        e.append("PURPOSE_REVISION_MISMATCH")
    if purpose != "initial" and not d["reason"]:
        e.append("REASON_REQUIRED")
    assets = {}
    for a in d["assets"] or []:
        if a["asset_id"] in assets:
            e.append("DUPLICATE_ASSET_ID: " + a["asset_id"])
        assets[a["asset_id"]] = a
        if a["media_type"] not in ROLE_MEDIA[a["role"]]:
            e.append("MEDIA_TYPE_ROLE_MISMATCH: " + a["asset_id"])
    sids = [s["source_id"] for s in d["source_files"] or []]
    if len(sids) != len(set(sids)):
        e.append("DUPLICATE_SOURCE_ID")
    missing = set()
    for m in d["missing_masters"] or []:
        if m["slot"] not in SELECTION_SLOTS[m["component"]]:
            e.append(f"SELECTION_SLOT_INVALID: {m['component']}.{m['slot']}")
        missing.add((m["component"], m["slot"]))
    for (comp, field), roles in COMPONENT_ROLES.items():
        c = d["components"].get(comp)
        if not c:
            continue
        vals = c[field] if isinstance(c[field], list) else [c[field]]
        if (comp, field) in missing and any(v is not None for v in vals):
            e.append(f"SELECTION_MISSING_CONTRADICTION: {comp}.{field}")
        for v in vals:
            if v is None:
                continue
            if v not in assets:
                e.append(f"UNKNOWN_ASSET: {comp}.{field}={v}")
            elif assets[v]["role"] not in roles:
                e.append(f"WRONG_ASSET_ROLE: {comp}.{field}={v}")
    return e


def _sem_web(d):
    from ..web.contract import web_semantics
    return web_semantics(d)


def _sem_podcast(d):
    from ..podcast.podcast import podcast_semantics
    return podcast_semantics(d)


SEMANTIC = {"production-handoff": sem_handoff, "release": sem_release, "approval": sem_approval,
            "import-receipt": sem_receipt, "public-bundle-manifest": sem_public_manifest,
            "contract-lock": sem_lock, "story-allocation": lambda d: [],
            "publish-plan": sem_plan, "publish-receipt": sem_publish_receipt,
            "media-delivery": sem_media_delivery, "site-set": sem_site_set, "project": sem_project,
            "service-inventory": sem_service_inventory,
            "catalog": sem_catalog_or_story, "story": sem_catalog_or_story, "rights-review": sem_rights_review,
            "collection": sem_collection, "handoff-selection": sem_selection, "web-bundle": _sem_web,
            "reading-edition": sem_reading_edition,
            "episode-publication": _sem_podcast, "provider-registry": _sem_podcast,
            "feed-observation": _sem_podcast}


def payload_digest(handoff) -> str:
    return cj1.digest(handoff["payload"])
