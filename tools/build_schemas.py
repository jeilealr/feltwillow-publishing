#!/usr/bin/env python3
"""Write the contract revision H2 JSON Schemas into publishing/contracts/schemas/.

PROPOSED CONTRACT (contract revision H2 = Agent B's draft H1 + Agents C/D/E schemas + the lead's
DECISIONS_H2). The generated *.schema.json files are the contract artifacts; this script only keeps them
consistent. v2 `*.v1.schema.json` files sit next to them as byte copies of the v2 package (carried forward
unchanged; superseded kinds stay resolvable for `$ref` and for explicit migration).

Local `$id`s under https://feltwillow.example.invalid/ (never resolved over a network). Offline, stdlib only.
Usage: python tools/build_schemas.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publishing" / "contracts" / "schemas"
BASE = "https://feltwillow.example.invalid/schemas/"
D2020 = "https://json-schema.org/draft/2020-12/schema"
C = BASE + "common.v2.json#/$defs/"
C1 = BASE + "common.v1.json#/$defs/"
MAX_SAFE = 2**53 - 1
REVISION = "Contract revision H2 (PROPOSED CONTRACT; not released)."
LANGS = "en|de|es|fr|ru|uk"
SLUG = "[a-z0-9]+(?:-[a-z0-9]+)*"


def ref(name, common=C):
    return {"$ref": common + name}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def obj(props: dict, required=None, **extra):
    out = {"type": "object", "additionalProperties": False, "properties": props,
           "required": list(props) if required is None else required}
    out.update(extra)
    return out


def arr(items, **extra):
    out = {"type": "array", "items": items}
    out.update(extra)
    return out


def text(max_len=2000):
    return {"type": "string", "minLength": 1, "maxLength": max_len}


def string(max_len, min_len=1, pattern=None):
    s = {"type": "string", "minLength": min_len, "maxLength": max_len}
    if pattern:
        s["pattern"] = pattern
    return s


def record(name, version, title, props: dict, description):
    """Every H2 record kind carries kind, schema_version, example and the canonicalization constant
    (DECISIONS_H2 s.3: every digest-pinned record carries it; in H2 every new record kind can be pinned)."""
    head = {"kind": {"const": name}, "schema_version": {"const": version}, "example": {"type": "boolean"},
            "canonicalization": ref("canonicalization")}
    head.update(props)
    return {"$schema": D2020, "$id": f"{BASE}{name}.v{version}.json", "title": title,
            "description": description + " " + REVISION, **obj(head)}


# L-28: no reading-text in handoffs (reading editions are authored in publishing);
# L-29: no lossy audio-delivery in handoffs (publishing derives delivery MP3s from the WAV/FLAC master).
ROLE_ENUM = ["spoken-transcript", "audio-master", "illustration",
             "cover-art", "video-master", "video-delivery", "thumbnail", "captions", "chapters"]
MEDIA_ENUM = ["application/vnd.feltwillow.reading-blocks+json", "text/plain", "audio/wav", "audio/flac",
              "audio/mpeg", "audio/mp4", "image/png", "image/jpeg", "image/webp", "video/mp4",
              "video/quicktime", "text/vtt", "application/json"]
RIGHTS_COMPONENTS = ["underlying-story", "adaptation", "translation", "voices", "images", "music",
                     "sound-effects", "video", "compute-resources"]
HTTPS_PATTERN = r"^https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[^\s\"'<>\\]*)?$"

# ------------------------------------------------------------------------------------------ common.v2
COMMON = {
    "$schema": D2020, "$id": BASE + "common.v2.json",
    "title": "Feltwillow shared definitions v2 (H2)",
    "description": "Shared definitions for contract revision H2. common.v1 stays unchanged for v1 records. "
                   "H2 adds https_url, episode_id, observation_id (IC-D10), canonicalization, module_id, "
                   "handoff_package_digest, email, date and dirty_path (L-21). " + REVISION,
    "$defs": {
        "id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 64},
        "language": {"enum": ["en", "de", "es", "fr", "ru", "uk"]},
        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "git_commit": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
        "utc_timestamp": {"type": "string", "format": "date-time",
                          "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
        "date": {"type": "string", "format": "date", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
        "safe_count": {"type": "integer", "minimum": 0, "maximum": MAX_SAFE},
        "positive_count": {"type": "integer", "minimum": 1, "maximum": MAX_SAFE},
        "relpath": {"type": "string", "maxLength": 512,
                    "pattern": "^(?!/)(?!.*//)(?!(?:.*/)?\\.{1,2}(?:/|$))[A-Za-z0-9_@+-][A-Za-z0-9_.@+/-]*$"},
        "dirty_path": {"type": "string", "maxLength": 512,
                       "pattern": "^(?!/)(?!.*//)(?!(?:.*/)?\\.{1,2}(?:/|$))[A-Za-z0-9_.@+-][A-Za-z0-9_.@+/-]*$",
                       "description": "L-21: recorded unrelated dirty path; like relpath but leading-dot segments "
                                      "(.gitignore, .claude/...) allowed; '.', '..', absolute and backslash forbidden."},
        "package_path": {"type": "string", "pattern": "^files/[a-z0-9]+(?:-[a-z0-9]+)*/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"},
        "handoff_id": {"type": "string",
                       "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*\\.(?:en|de|es|fr|ru|uk)\\.h[0-9]{4}$"},
        "release_id": {"type": "string",
                       "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*\\.(?:en|de|es|fr|ru|uk)\\.r[0-9]{4}$"},
        "episode_id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*\\.(?:en|de|es|fr|ru|uk)$"},
        "observation_id": {"type": "string", "pattern": "^obs-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$"},
        "https_url": {"type": "string", "minLength": 9, "maxLength": 2048, "pattern": HTTPS_PATTERN},
        "email": {"type": "string", "maxLength": 254,
                  "pattern": "^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\\.[A-Za-z0-9-]+)*\\.[A-Za-z]{2,}$"},
        "person": {"type": "string", "minLength": 1, "maxLength": 128},
        "text": text(),
        "error_code": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
        "semver": {"type": "string",
                   "pattern": "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$"},
        "canonicalization": {"const": "feltwillow-canonical-json-v1",
                             "description": "v2 canonical-json-v1 bytes within the H1 safe domain (normative)."},
        "module_id": {"enum": ["astro", "ghost", "plain_static"],
                      "description": "IC-C3: one spelling in every record; folders web/astro, web/ghost-theme, web/plain-static."},
        "role": {"enum": ROLE_ENUM},
        "media_type": {"enum": MEDIA_ENUM},
        "rights_component": {"enum": RIGHTS_COMPONENTS},
        "private_ref": obj({
            "ref": {"type": "string", "minLength": 1, "maxLength": 512,
                    "description": "Opaque PRIVATE locator (production-relative path, owner-store label). "
                                   "Provenance only: never a permission to read a production checkout, never a URL."},
            "sha256": nullable(ref("sha256")),
        }),
        "contract_package": obj({
            "name": {"const": "feltwillow-contracts"},
            "version": ref("semver"),
            "archive_sha256": ref("sha256"),
        }),
        "handoff_ref": obj({"handoff_id": ref("handoff_id"), "payload_sha256": ref("sha256")}),
        "reading_edition_id": {"type": "string",
                               "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*\\.(?:en|de|es|fr|ru|uk)\\.e[0-9]{4}$"},
        "reading_edition_pin": obj({"edition_id": {"$ref": "#/$defs/reading_edition_id"}, "edition_sha256": {"$ref": "#/$defs/sha256"}}),
        "measurement": obj({"tool": {"enum": ["feltwillow-stdlib", "ffprobe"]},
                            "version": {"type": "string", "minLength": 1, "maxLength": 64}},
                           description="L-29: tool that measured the asset bytes and its version."),
        "handoff_package_digest": obj({"handoff_id": ref("handoff_id"), "payload_sha256": ref("sha256"),
                                       "archive_sha256": ref("sha256")}),
        "release_pin": obj({"release_id": ref("release_id"), "release_sha256": ref("sha256")}),
        "approval_ref": obj({"approval_id": ref("id"), "approval_sha256": ref("sha256")}),
        "frame_rate": obj({"numerator": ref("positive_count"), "denominator": ref("positive_count")}),
    },
}

# ------------------------------------------------------------------------------------------ B (H1, adopted)
MEASURED = obj({
    "width_px": nullable(ref("positive_count")), "height_px": nullable(ref("positive_count")),
    "duration_ms": nullable(ref("positive_count")), "sample_rate_hz": nullable(ref("positive_count")),
    "channels": nullable({"type": "integer", "minimum": 1, "maximum": 64}),
    "frame_rate": nullable(ref("frame_rate")),
}, description="Measured by the exporter from the bytes. Integers only.")

HANDOFF_ASSET = obj({
    "asset_id": ref("id"), "role": ref("role"), "media_type": ref("media_type"),
    "bytes": ref("positive_count"), "sha256": ref("sha256"),
    "transport": {"enum": ["embedded", "referenced"]},
    "package_path": nullable(ref("package_path")), "measured": MEASURED,
    "measurement": nullable(ref("measurement")),
    "derived_from": arr(obj({
        "sha256": ref("sha256"), "asset_id": nullable(ref("id")),
        "relation": {"enum": ["export", "mixdown", "transcode", "resize", "crop", "loudness-normalize",
                              "caption-timing", "text-adaptation", "other"]},
    }), maxItems=16),
    "origin": obj({
        "store": {"enum": ["production-git", "owner-master-store", "production-work"]},
        "ref": {"type": "string", "minLength": 1, "maxLength": 512},
        "commit": nullable(ref("git_commit")),
    }),
    "selection_note": nullable(text(500)),
})

SOURCE_PURPOSES = ["script", "dialogue", "reading-adaptation", "transcript-source", "runtime",
                   "prompt-manifest", "voices", "timing", "rights-index", "selection", "other"]  # selection: L-23
SOURCE_FILE = obj({
    "source_id": ref("id"),
    "purpose": {"enum": SOURCE_PURPOSES},
    "repo_role": {"const": "production"}, "path": ref("relpath"), "commit": ref("git_commit"),
    "sha256": ref("sha256"), "bytes": ref("positive_count"),
})

HANDOFF = record("production-handoff", 1, "Production handoff v1", {
    "contract_package": ref("contract_package"),
    "envelope": obj({
        "created_at": ref("utc_timestamp"), "operator": ref("person"),
        "exporter": obj({
            "tool": {"type": "string", "minLength": 1, "maxLength": 128}, "tool_version": ref("semver"),
            "repository": {"const": "jeilealr/feltwillow-production"}, "commit": ref("git_commit"),
            "tool_dirty": {"type": "boolean"},
        }),
        "transport": {"const": "self-contained-tar"},
    }, description="Facts about this export run. Excluded from payload_sha256."),
    "payload": obj({
        "handoff_id": ref("handoff_id"), "story_id": ref("id"), "language": ref("language"),
        "handoff_revision": {"type": "integer", "minimum": 1, "maximum": 9999},
        "purpose": {"enum": ["initial", "correction", "revocation"]},
        "supersedes": nullable(ref("handoff_ref")), "reason": nullable(text(1000)),
        "story_allocation_sha256": ref("sha256"),
        "production_slugs": arr({"type": "string", "pattern": "^[a-z0-9_]+$", "maxLength": 64},
                                minItems=1, uniqueItems=True),
        "source_repositories": arr(obj({
            "repo_role": {"const": "production"},
            "repository": {"const": "jeilealr/feltwillow-production"},
            "branch": {"type": "string", "minLength": 1, "maxLength": 128}, "commit": ref("git_commit"),
            "worktree": obj({"state": {"enum": ["clean", "dirty"]},
                             "dirty_paths": arr(ref("dirty_path"), uniqueItems=True, maxItems=10000)}),
        }), minItems=1, maxItems=1),
        "source_files": arr(SOURCE_FILE, maxItems=1000),
        "assets": arr(HANDOFF_ASSET, maxItems=5000),
        "components": obj({
            # L-28: `images` replaces the reading component (illustrations and cover only; no reading text)
            "images": nullable(obj({"illustration_assets": arr(ref("id"), uniqueItems=True, maxItems=500),
                                    "cover_asset": nullable(ref("id"))})),
            "audio": nullable(obj({"master_asset": ref("id"), "transcript_asset": nullable(ref("id"))})),
            "video": nullable(obj({"master_asset": ref("id"), "captions_asset": nullable(ref("id")),
                                   "thumbnail_asset": nullable(ref("id"))})),
        }),
        "editorial_selection": obj({
            "selected_by": ref("person"), "selected_at": ref("utc_timestamp"), "statement": text(1000),
            "evidence": arr(ref("private_ref"), maxItems=100),
        }, description="Production-side selection (approval stage 0). NOT publication approval."),
        "rights_evidence": arr(obj({"component": ref("rights_component"), "evidence": ref("private_ref"),
                                    "note": nullable(text(500))}), maxItems=200),
        "generation_provenance": arr(obj({
            "asset_id": ref("id"),
            "tools": arr({"type": "string", "minLength": 1, "maxLength": 128}, minItems=1, maxItems=20),
            "evidence": nullable(ref("private_ref")),
        }), maxItems=5000),
    }),
}, "Private, self-contained selection of final content from the production repository. Importable "
   "without production code. Never a publication approval.")

RELEASE_ASSET = obj({
    "asset_id": ref("id"),
    "role": {"enum": ["image", "podcast-cover", "audio-master", "podcast-audio", "video-master",
                      "transcript", "chapters", "captions"]},
    "origin": obj({"kind": {"enum": ["handoff", "publishing-derivative"]},
                   "handoff_id": nullable(ref("handoff_id")), "handoff_asset_id": nullable(ref("id"))}),
    "sha256": ref("sha256"), "bytes": ref("positive_count"), "media_type": ref("media_type"),
    "width": nullable(ref("positive_count")), "height": nullable(ref("positive_count")),
    "duration_ms": nullable(ref("positive_count")),
    "selection": {"enum": ["pending", "approved", "rejected"]},
    "derived_from_sha256": nullable(ref("sha256")),
})

RELEASE = record("release", 2, "Publishing release v2", {
    "release_id": ref("release_id"), "story_id": ref("id"), "language": ref("language"),
    "revision": {"type": "integer", "minimum": 1, "maximum": 9999},
    "lifecycle": {"enum": ["draft", "frozen"]},
    "supersedes": nullable(ref("release_pin")),
    "handoffs": arr(ref("handoff_package_digest"), maxItems=20),
    "content": obj({
        "title": text(200), "slug": ref("id"), "summary": text(1000),
        "age_min": {"type": "integer", "minimum": 0, "maximum": 18},
        "age_max": {"type": "integer", "minimum": 0, "maximum": 18},
        "moral": text(500),
        "reading_edition": nullable(ref("reading_edition_pin")),  # L-28: authored in publishing
        "spoken_transcript_asset": nullable(ref("id")),
        "reading_divergence": {"enum": ["identical", "intentional-adaptation", "not-applicable"]},
        "blocks": arr(ref("block", C1)),
    }),
    "assets": arr(RELEASE_ASSET),
    "channels": {"$ref": BASE + "release.v1.json#/properties/channels"},
    "rights": {"$ref": BASE + "release.v1.json#/properties/rights"},
    "emergency_override": nullable(obj({
        "reason": text(1000), "authored_by": ref("person"), "authored_at": ref("utc_timestamp"),
        "backport": {"enum": ["pending", "backported", "waived-by-owner"]},
        "backport_handoff": nullable(ref("handoff_ref")),
    })),
    "frozen_with": nullable(obj({"publishing_commit": ref("git_commit"), "tool_version": ref("semver"),
                                 "contract_package": ref("contract_package")})),
}, "Immutable publication edition (asset roots: package/masters/publishing; production paths are provenance "
   "only, via referenced handoffs). Approvals are separate records.")

APPROVAL = record("approval", 2, "Approval v2", {
    "approval_id": ref("id"),
    "stage": {"enum": ["editorial-rights", "channel-readiness", "deployment"]},
    "subject_type": {"enum": ["release", "site-set", "project", "publish-plan"]},
    "subject_id": {"type": "string", "minLength": 1, "maxLength": 128},
    "subject_sha256": ref("sha256"),
    "scope": {"enum": ["edition", "rights_review.podcast_audio", "website", "podcast", "youtube", "configuration"]},
    "decision": {"enum": ["approved", "rejected", "revoked"]},
    "revokes": nullable(ref("approval_ref")),
    "depends_on": arr(ref("approval_ref"), uniqueItems=True, maxItems=200),
    "reviewed_by": ref("person"), "reviewed_at": ref("utc_timestamp"), "reason": nullable(text(1000)),
    "checks": arr(obj({"name": text(100), "result": {"enum": ["pass", "fail", "not_applicable"]},
                       "evidence": text(1000)}), maxItems=100),
}, "Decision bound to one subject digest, one stage and one scope. H2 adds scope rights_review.podcast_audio "
   "(IC-D7): an approved podcast-audio rights review must carry the checks gemini-terms-answer and "
   "mix-music-and-effects (not_applicable allowed with evidence).")

IMPORT_RECEIPT = record("import-receipt", 1, "Import receipt v1", {
    "receipt_id": {"type": "string", "pattern": "^imp-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$"},
    "outcome": {"enum": ["accepted", "duplicate-identical", "rejected"]},
    "errors": arr(ref("error_code"), uniqueItems=True, maxItems=200),
    "handoff_id": nullable(ref("handoff_id")),
    "archive": obj({"sha256": ref("sha256"), "bytes": ref("positive_count")}),
    "expected_archive_sha256": nullable(ref("sha256")),
    "expected_digest_source": {"enum": ["operator-out-of-band", "not-provided"]},
    "record_sha256": nullable(ref("sha256")), "payload_sha256": nullable(ref("sha256")),
    "schema_version_seen": nullable({"type": "integer", "minimum": 0, "maximum": 1000}),
    "supersedes": nullable(ref("handoff_ref")),
    "consumer_supports": arr({"type": "integer", "minimum": 1}, minItems=1, uniqueItems=True),
    "duplicate_of": nullable({"type": "string", "pattern": "^imp-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$"}),
    "archival_locator": nullable({"type": "string", "pattern": "^handoffs/[a-f0-9]{64}\\.tar$",
                                  "description": "Relative to FELTWILLOW_MASTER_ROOT (DECISIONS_H2 s.2)."}),
    "promoted": {"type": "boolean"},
    "staged_at": ref("utc_timestamp"), "finished_at": ref("utc_timestamp"), "operator": ref("person"),
    "importer": obj({"tool": {"type": "string", "minLength": 1, "maxLength": 128}, "tool_version": ref("semver"),
                     "publishing_commit": nullable(ref("git_commit"))}),
    "authorizes_publication": {"const": False},
}, "Durable, append-only observation of one import attempt, stored in FELTWILLOW_PUBLISH_STATE_ROOT/receipts/. "
   "The archived tar lives at FELTWILLOW_MASTER_ROOT/handoffs/<archive sha256>.tar. Never an approval.")

PUBLIC_MANIFEST = record("public-bundle-manifest", 1, "Public output bundle manifest v1", {
    "bundle_id": ref("id"),
    "bundle_type": {"enum": ["web", "podcast-package", "youtube-package"]},
    "manifest_visibility": {"const": "internal"},
    "inputs": obj({
        "releases": arr(ref("release_pin"), minItems=1),
        "site_set": nullable(obj({"site_set_id": ref("id"), "sha256": ref("sha256")})),
        "public_record_sha256": nullable(ref("sha256")),
        "renderer": nullable(obj({"name": ref("module_id"), "version": ref("semver")}),
                             ) | {"description": "null = render-input bundle (IC-C2); set = site artifact."},
        "contract_package": ref("contract_package"),
    }),
    "files": arr(obj({
        "path": {"type": "string", "maxLength": 512,
                 "pattern": "^(?!/)(?!.*//)(?!(?:.*/)?\\.{1,2}(?:/|$))[A-Za-z0-9_-][A-Za-z0-9_./-]*$"},
        "sha256": ref("sha256"), "bytes": ref("positive_count"),
        "media_type": {"enum": ["text/html", "text/css", "application/javascript", "application/json",
                                "application/xml", "application/rss+xml", "image/png", "image/jpeg",
                                "image/webp", "image/svg+xml", "audio/mpeg", "audio/mp4", "video/mp4",
                                "text/vtt", "text/plain", "font/woff2"]},
        "source": nullable(obj({"release_id": ref("release_id"), "asset_id": ref("id")})),
    }), minItems=1, maxItems=100000),
}, "Internal manifest of an allowlisted public projection. The listed files are public; this manifest is not.")

CONTRACT_LOCK = record("contract-lock", 1, "Contract lock v1", {
    "package": obj({
        "name": {"const": "feltwillow-contracts"}, "version": ref("semver"), "archive_sha256": ref("sha256"),
        "source_repository": {"const": "jeilealr/feltwillow-publishing"},
        "source_commit": nullable(ref("git_commit")), "released_at": ref("utc_timestamp"),
    }),
    "files": arr(obj({"path": ref("relpath"), "sha256": ref("sha256")}), minItems=1),
    "producer_emits": obj({"production-handoff": {"type": "integer", "minimum": 1}}),
}, "Pinned copy of a released contract package (production/contracts/CONTRACT.lock).")

ALLOCATION = record("story-allocation", 1, "Story ID allocation v1", {
    "story_id": ref("id"), "status": {"enum": ["allocated", "retired"]},
    "allocated_at": ref("utc_timestamp"), "allocated_by": ref("person"), "working_title": text(200),
    "production_slugs": arr({"type": "string", "pattern": "^[a-z0-9_]+$", "maxLength": 64}, minItems=1, uniqueItems=True),
    "planned_languages": arr(ref("language"), minItems=1, uniqueItems=True),
}, "Publishing-side assignment of a stable story ID, issued before the first handoff.")

# ------------------------------------------------------------------------------------------ L-28: reading-edition.v1
READING_EDITION = record("reading-edition", 1, "Reading edition v1", {
    "edition_id": ref("reading_edition_id"), "story_id": ref("id"), "language": ref("language"),
    "revision": {"type": "integer", "minimum": 1, "maximum": 9999},
    "lifecycle": {"enum": ["draft", "frozen"]},
    "supersedes": nullable(ref("reading_edition_pin")),
    "title": text(200),
    "source_script": obj({"handoff_id": ref("handoff_id"), "handoff_payload_sha256": ref("sha256"),
                          "source_id": ref("id"), "sha256": ref("sha256")},
                         description="The handoff script / line-list source file this edition was written from."),
    "illustrations": arr(obj({"asset_id": ref("id"), "handoff_id": ref("handoff_id"),
                              "handoff_asset_id": ref("id"), "sha256": ref("sha256")}), maxItems=500),
    "blocks": arr(ref("block", C1), minItems=1, maxItems=2000),
    "provenance": obj({"authored_in": {"const": "publishing"}, "authored_by": ref("person"),
                       "authored_at": ref("utc_timestamp"), "tools": arr(text(128), maxItems=20),
                       "note": nullable(text(1000))}),
}, "Reading text of one story-language, authored in the publishing repository (L-28). Ordered blocks: "
   "text (paragraph/heading/quote) and illustrations (image block: handoff asset ref + alt text). Pins the "
   "handoff script/line-list digest it was written from. Approvals are separate records.")

# ------------------------------------------------------------------------------------------ L-23: handoff-selection.v1
SEL_EVIDENCE = {"oneOf": [obj({"repo_path": ref("relpath")}), ref("private_ref")]}
SLOT_IDS = lambda: nullable(ref("id"))  # noqa: E731
HANDOFF_SELECTION = {
    "$schema": D2020, "$id": BASE + "handoff-selection.v1.json", "title": "Handoff selection v1",
    "description": "Production-authored, publishing-released selection file stories/<slug>/handoff_selection.yaml "
                   "read by production/export_handoff.py (Agent G3; L-23). YAML authored and pinned by its Git blob "
                   "digest as a source file of purpose `selection`, so it carries no canonicalization constant. "
                   "Every file is named explicitly (no globs, no 'latest'). " + REVISION,
    **obj({
        "kind": {"const": "handoff-selection"}, "schema_version": {"const": 1}, "example": {"type": "boolean"},
        "story_id": ref("id"), "language": ref("language"),
        "handoff_revision": {"type": "integer", "minimum": 1, "maximum": 9999},
        "purpose": {"enum": ["initial", "correction", "revocation"]},
        "supersedes": nullable(ref("handoff_ref")), "reason": nullable(text(1000)),
        "production_slugs": arr({"type": "string", "pattern": "^[a-z0-9_]+$", "maxLength": 64}, minItems=1, uniqueItems=True),
        "editorial_selection": obj({"selected_by": ref("person"), "selected_at": ref("utc_timestamp"),
                                    "statement": text(1000), "evidence": arr(SEL_EVIDENCE, maxItems=100)}),
        "source_files": nullable(arr(obj({"source_id": ref("id"), "purpose": {"enum": SOURCE_PURPOSES},
                                          "path": ref("relpath")}), maxItems=1000)),
        "assets": nullable(arr(obj({
            "asset_id": ref("id"), "role": ref("role"), "media_type": ref("media_type"),
            "store": {"enum": ["production-git", "production-work", "owner-master-store"]},
            "path": ref("relpath"),
            "package_name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"},
            "derived_from": nullable(arr(obj({"sha256": ref("sha256"), "asset_id": nullable(ref("id")),
                                              "relation": {"enum": ["export", "mixdown", "transcode", "resize", "crop",
                                                                    "loudness-normalize", "caption-timing",
                                                                    "text-adaptation", "other"]}}), maxItems=16)),
            "selection_note": nullable(text(500)),
        }, required=["asset_id", "role", "media_type", "store", "path"]), maxItems=5000)),
        "components": obj({
            "images": nullable(obj({"illustration_assets": arr(ref("id"), uniqueItems=True, maxItems=500),
                                    "cover_asset": SLOT_IDS()})),
            "audio": nullable(obj({"master_asset": SLOT_IDS(), "transcript_asset": SLOT_IDS()})),
            "video": nullable(obj({"master_asset": SLOT_IDS(), "captions_asset": SLOT_IDS(), "thumbnail_asset": SLOT_IDS()})),
        }),
        "missing_masters": nullable(arr(obj({"component": {"enum": ["images", "audio", "video"]},
                                             "slot": {"type": "string", "pattern": "^[a-z_]+$", "maxLength": 64},
                                             "status": ref("id"), "note": text(1000)}), maxItems=50)),
        "rights_evidence": nullable(arr(obj({"component": ref("rights_component"), "evidence": SEL_EVIDENCE,
                                             "note": nullable(text(500))}), maxItems=200)),
        "generation_provenance": nullable(arr(obj({"asset_id": ref("id"),
                                                   "tools": arr({"type": "string", "minLength": 1, "maxLength": 128}, minItems=1, maxItems=20),
                                                   "evidence": nullable(SEL_EVIDENCE)}), maxItems=5000)),
    }),
}

# ------------------------------------------------------------------------------------------ C: web-bundle.v2
HTTPS_URL = ref("https_url")
ORIGIN = string(253, pattern=r"^https://[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]{1,5})?$")
ROUTE = string(200, pattern=r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)*$")
STORY_PATH = string(200, pattern=rf"^/(?:{LANGS})/stories/{SLUG}/$")
PAGE_PATH = string(64, pattern=rf"^/(?:(?:{LANGS})/)?(?:about|contact|privacy|legal)/$")
MEDIA_PATH = string(80, pattern=r"^media/[a-f0-9]{64}\.(?:webp|png|jpg|mp3|m4a|vtt)$")
TRANSCRIPT_BLOCK = {"oneOf": [
    obj({"type": {"const": "paragraph"}, "text": string(4000)}),
    obj({"type": {"const": "heading"}, "level": {"enum": [2, 3]}, "text": string(300)}),
    obj({"type": {"const": "quote"}, "speaker": string(120), "text": string(4000)}),
]}
PLAYER = {"oneOf": [
    obj({"type": {"const": "none"}}),
    obj({"type": {"const": "spotify_embed"}, "embed_url": HTTPS_URL, "fallback_url": HTTPS_URL}),
    obj({"type": {"const": "native_audio"}, "asset_id": ref("id")}),
]}
WEB_STORY = obj({
    "story_id": ref("id"), "language": ref("language"), "release": ref("release_pin"), "path": STORY_PATH,
    "title": string(200), "summary": string(1000), "moral": string(500),
    "age_min": {"type": "integer", "minimum": 0, "maximum": 18},
    "age_max": {"type": "integer", "minimum": 0, "maximum": 18},
    "published_at": nullable(ref("utc_timestamp")), "updated_at": nullable(ref("utc_timestamp")),
    "cover": nullable(obj({"asset_id": ref("id"), "alt": string(500)})),
    "blocks": {"type": "array", "minItems": 1, "maxItems": 2000, "items": ref("block", C1)},
    "reading_divergence": {"enum": ["identical", "intentional-adaptation", "not-applicable"]},
    "transcript": nullable(obj({"source": {"const": "spoken-transcript"},
                                "blocks": {"type": "array", "minItems": 1, "maxItems": 4000, "items": TRANSCRIPT_BLOCK}})),
    "listening": obj({
        "duration_ms": nullable(ref("positive_count")), "player": PLAYER,
        "links": {"type": "array", "maxItems": 12, "items": obj({
            "service": {"enum": ["spotify", "apple-podcasts", "amazon-music", "pocket-casts", "youtube", "rss", "other"]},
            "label": string(80), "url": HTTPS_URL})},
    }),
    "video": nullable(obj({"youtube_url": HTTPS_URL})),
})
WEB_PAGE = obj({
    "page_id": {"enum": ["about", "contact", "privacy", "legal"]}, "language": nullable(ref("language")),
    "path": PAGE_PATH, "title": string(200),
    "blocks": {"type": "array", "minItems": 1, "maxItems": 500, "items": ref("block", C1)},
})
WEB_MEDIA = obj({
    "path": MEDIA_PATH, "sha256": ref("sha256"), "bytes": ref("positive_count"),
    "media_type": {"enum": ["image/webp", "image/png", "image/jpeg", "audio/mpeg", "audio/mp4", "text/vtt"]},
    "width": nullable(ref("positive_count")), "height": nullable(ref("positive_count")),
    "duration_ms": nullable(ref("positive_count")),
    "source": obj({"release_id": ref("release_id"), "asset_id": ref("id")}),
})
WEB_BUNDLE = record("web-bundle", 2, "Public web payload v2", {
    "site_set": obj({"site_set_id": ref("id"), "sha256": ref("sha256")}),
    "origin": nullable(ORIGIN), "brand": obj({"name": string(200)}),
    "default_language": ref("language"), "trailing_slash": {"const": "always"},
    "languages": {"type": "array", "minItems": 1, "maxItems": 6, "items": obj({
        "language": ref("language"), "label": string(64), "path": string(4, pattern=rf"^/(?:{LANGS})/$")})},
    "pages": {"type": "array", "maxItems": 50, "items": WEB_PAGE},
    "stories": {"type": "array", "maxItems": 2000, "items": WEB_STORY},
    "redirects": {"type": "array", "maxItems": 2000, "items": obj({"from": ROUTE, "to": ROUTE, "status": {"enum": [301, 308]}})},
    "media": {"type": "object", "maxProperties": 20000, "propertyNames": ref("id"), "additionalProperties": WEB_MEDIA},
}, "The single public data file (data/web-bundle.json) of a render-input bundle (Agent C, IC-C1). Every "
   "renderer (astro, ghost, plain_static) reads only this file plus the media it lists; media are named "
   "media/<sha256>.<ext>.")

# ------------------------------------------------------------------------------------------ D
GUID = {"type": "string", "minLength": 1, "maxLength": 512}
REC_ID = {"type": "string", "pattern": "^reg-[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 96}
EPISODE = record("episode-publication", 2, "Episode publication v2", {
    "show_id": ref("id"), "episode_id": ref("episode_id"),
    "record_revision": {"type": "integer", "minimum": 1, "maximum": 9999},
    "supersedes": nullable(obj({"record_revision": {"type": "integer", "minimum": 1, "maximum": 9998},
                                "record_sha256": ref("sha256")})),
    "change": {"enum": ["prepared", "first-publication", "metadata-correction", "audio-replacement",
                        "artwork-change", "host-migration", "withdrawal", "observation-refresh"]},
    "release_id": ref("release_id"), "release_sha256": ref("sha256"),
    "authority": {"enum": ["spotify", "independent"]},
    "state": {"enum": ["prepared", "published", "withdrawn"]},
    "episode_type": {"enum": ["full", "trailer", "bonus"]},
    "guid": nullable(GUID), "guid_is_permalink": nullable({"type": "boolean"}),
    "guid_source": nullable({"enum": ["observed-from-host-feed", "generated-before-release", "retained-from-previous-host"]}),
    "first_published_at": nullable(ref("utc_timestamp")),
    "first_pubdate_raw": nullable({"type": "string", "minLength": 1, "maxLength": 64}),
    "submitted_audio": obj({"asset_id": ref("id"), "sha256": ref("sha256"), "bytes": ref("positive_count"),
                            "media_type": {"enum": ["audio/mpeg", "audio/mp4", "audio/wav"]},
                            "duration_ms": ref("positive_count")}),
    "observed_enclosure": nullable(obj({
        "url": HTTPS_URL, "declared_length_bytes": ref("safe_count"),
        "declared_type": {"type": "string", "minLength": 1, "maxLength": 128},
        "delivered_sha256": nullable(ref("sha256")), "delivered_bytes": nullable(ref("positive_count")),
        "head_ok": nullable({"type": "boolean"}), "range_ok": nullable({"type": "boolean"}),
    })),
    "evidence": nullable(obj({"observation_id": ref("observation_id"), "observation_sha256": ref("sha256")})),
    "observed_at": nullable(ref("utc_timestamp")),
}, "Persistent identity of one logical podcast episode in one show (Agent D, IC-D1): integer duration_ms; "
   "GUID/first date null only while prepared; guid_source; append-only revisions; observed enclosure kept "
   "apart from the submitted file.")

URL_KINDS = ["show-page", "episode-page", "rss-feed", "enclosure", "embed", "creator-profile", "video-page",
             "playlist-page", "website-page"]
REGISTRY = record("provider-registry", 2, "Provider registry v2", {
    "records": {"type": "array", "maxItems": 5000, "items": obj({
        "record_id": REC_ID,
        "destination": {"enum": ["spotify", "apple", "amazon", "pocket_casts", "youtube", "independent-rss", "ghost", "website"]},
        "entity_type": {"enum": ["show", "episode", "video", "website-story", "collection"]},
        "entity_id": {"type": "string", "minLength": 1, "maxLength": 96},
        "url_kind": nullable({"enum": URL_KINDS}),
        "external_url": nullable(HTTPS_URL),
        "external_id": nullable({"type": "string", "minLength": 1, "maxLength": 256}),
        "status": {"enum": ["not_submitted", "submitted", "verification_needed", "listed", "blocked", "superseded", "withdrawn"]},
        "observed_at": ref("utc_timestamp"),
        "receipt_id": nullable({"type": "string", "minLength": 1, "maxLength": 128}),
        "supersedes_record_id": nullable(REC_ID),
        "note": nullable({"type": "string", "minLength": 1, "maxLength": 500}),
    })},
}, "Sanitized public provider mappings with a required url_kind per URL (Agent D, IC-D2). Values are "
   "observed, never constructed. No e-mail addresses, owner account IDs, tokens or verification codes.")

FEED_ITEM = obj({
    "guid": nullable({"type": "string", "maxLength": 2048}), "guid_is_permalink": {"type": "boolean"},
    "guid_permalink_attr_present": {"type": "boolean"},
    "title": nullable({"type": "string", "maxLength": 2000}),
    "pubdate_raw": nullable({"type": "string", "maxLength": 128}), "pubdate_utc": nullable(ref("utc_timestamp")),
    "enclosure": nullable(obj({"url": {"type": "string", "maxLength": 2048},
                               "length": nullable({"type": "string", "maxLength": 32}),
                               "type": nullable({"type": "string", "maxLength": 128})})),
    "itunes_duration_raw": nullable({"type": "string", "maxLength": 32}),
    "itunes_episode_type": nullable({"type": "string", "maxLength": 32}),
})
FEED_OBS = record("feed-observation", 1, "Feed observation v1", {
    "observation_id": ref("observation_id"), "show_id": ref("id"), "feed_url": HTTPS_URL,
    "fetched_at": ref("utc_timestamp"),
    "fetch": nullable(obj({"final_url": HTTPS_URL, "http_status": {"type": "integer", "minimum": 100, "maximum": 599},
                           "redirect_chain": {"type": "array", "maxItems": 10, "items": obj({
                               "status": {"type": "integer", "minimum": 300, "maximum": 399}, "location": HTTPS_URL})}})),
    "feed_sha256": ref("sha256"), "feed_bytes": ref("positive_count"),
    "channel": obj({"title": nullable({"type": "string", "maxLength": 2000}),
                    "language": nullable({"type": "string", "maxLength": 32}),
                    "itunes_email_present": {"type": "boolean"},
                    "itunes_new_feed_url": nullable({"type": "string", "maxLength": 2048}),
                    "itunes_block": nullable({"type": "string", "maxLength": 16}),
                    "item_count": ref("safe_count")}),
    "items": {"type": "array", "maxItems": 10000, "items": FEED_ITEM},
    "problems": {"type": "array", "uniqueItems": True, "maxItems": 500, "items": ref("error_code")},
}, "Read-only observation of one RSS feed document (Agent D, IC-D3). Stores only the presence, never the "
   "value, of itunes:email. Raw feed bytes stay in FELTWILLOW_PUBLISH_STATE_ROOT, addressed by sha256.")

# ------------------------------------------------------------------------------------------ lead (H2 new versions)
PINS = {
    "publishing_commit": ref("git_commit"), "contract_version": ref("semver"),
    "contract_package": ref("contract_package"),
    "handoff_package_digests": arr(ref("handoff_package_digest"), maxItems=500),
}
TARGETS = ["static-site", "ghost", "spotify", "independent-rss", "apple", "amazon", "pocket_casts", "youtube"]
OPERATIONS = ["create-draft", "update-draft", "publish", "manual-upload", "manual-submit", "deploy", "withdraw",
              "manual_audio_replace", "manual_metadata_edit", "observe_feed", "manual_redirect"]
AUX_KINDS = ["show", "episode-publication", "media-delivery", "rights-review", "feed-observation",
             "provider-registry", "service-inventory", "web-bundle", "public-bundle-manifest",
             "ghost-theme", "ghost-routes", "ghost-redirects", "ghost-post-payload"]

PLAN = record("publish-plan", 2, "Publish plan v2", {
    "plan_id": ref("id"), "created_at": ref("utc_timestamp"), "expires_at": ref("utc_timestamp"),
    "environment": {"enum": ["preview", "production"]},
    "destination": {"enum": ["website", "podcast", "directory", "youtube"]},
    **PINS,
    "project_sha256": ref("sha256"),
    "site_set": nullable(obj({"site_set_id": ref("id"), "sha256": ref("sha256")})),
    "registry_sha256": ref("sha256"),
    "releases": arr(ref("release_pin"), maxItems=2000),
    "check_reports": obj({
        "leak_scan": nullable(obj({"report_sha256": ref("sha256"), "bundle_manifest_sha256": ref("sha256"),
                                   "clean": {"const": True}})),
        "strict_zero": nullable(obj({"report_sha256": ref("sha256"), "pass": {"const": True}})),
    }, description="IC-E2: digests of clean leak_scan and strict_zero reports; apply re-runs leak_scan on the exact upload directory."),
    "actions": arr(obj({
        "action_id": ref("id"), "target": {"enum": TARGETS}, "operation": {"enum": OPERATIONS},
        "subject_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "artifact": nullable(obj({"sha256": ref("sha256"), "bytes": ref("positive_count")},
                                 description="Content-addressed artifact (IC-D4); located by digest in the build or state store.")),
    }), maxItems=1000),
    "newsletter_send": {"const": False},
    "auxiliary_inputs": arr(obj({"record_kind": {"enum": AUX_KINDS}, "path": ref("relpath"), "sha256": ref("sha256")}),
                            maxItems=1000),
}, "Pinned, expiring plan (IC-A2, IC-B5, IC-C4, IC-D4, IC-E2): replaces v1's single source_commit with "
   "publishing_commit + contract pins + handoff package digests; explicit destination; manual operations; "
   "Ghost deployment artifacts as auxiliary inputs.")

RECEIPT = record("publish-receipt", 2, "Publish receipt v2", {
    "plan_id": ref("id"), "plan_sha256": ref("sha256"), "action_id": ref("id"),
    "operation": {"enum": OPERATIONS},
    "result": {"enum": ["manual_pending", "succeeded", "failed", "unknown", "conflict"]},
    "observed_at": ref("utc_timestamp"),
    "external_id": nullable({"type": "string", "minLength": 1, "maxLength": 256}),
    "external_url": nullable(HTTPS_URL),
    "observation_id": nullable(ref("observation_id")),
    "submitted_sha256": nullable(ref("sha256")),
    "evidence": nullable(ref("private_ref")),
    "conflict": nullable(obj({"code": ref("error_code"), "detail": text(1000)})),
}, "Append-only record of one plan action (IC-B4, IC-C4, IC-D5). Written as manual_pending before the owner "
   "acts; conflict records the Ghost remote-edit stop; evidence is a private reference, never free text.")

MEDIA_DELIVERY = record("media-delivery", 2, "Media delivery v2", {
    "records": arr(obj({
        "asset_sha256": ref("sha256"), "provider": ref("id"), "url": HTTPS_URL,
        "observed_sha256": nullable(ref("sha256")), "observed_bytes": ref("positive_count"),
        "duration_ms": nullable(ref("positive_count")),
        "observed_at": ref("utc_timestamp"), "access": {"enum": ["public", "private"]},
        "review": {"enum": ["pending", "pass", "fail"]},
    }), maxItems=10000),
}, "Observed delivery of a media file by a provider (IC-B2: integer duration_ms replaces float seconds).")

SITE_SET = record("site-set", 2, "Site set v2", {
    "site_set_id": ref("id"), "lifecycle": {"enum": ["draft", "frozen"]}, "renderer": ref("module_id"),
    "entries": arr(ref("release_pin"), maxItems=2000),
    "remove_paths": arr(string(200, pattern=r"^/"), uniqueItems=True, maxItems=2000),
    **PINS,
}, "Complete list of story-language releases on the website (IC-A2): same pins as publish-plan v2.")

MODULE_STATE = {"enum": ["spec_only", "implemented", "enabled"]}
PROJECT = record("project", 2, "Project v2", {
    "project_id": ref("id"),
    "profile_option": {"enum": ["undecided", "astro", "ghost", "zero_cost"]},
    "website": obj({"primary": {"enum": ["none", "astro", "ghost", "plain_static"]},
                    "origin": nullable(HTTPS_URL), "locale_prefixes": {"const": True}}),
    "modules": obj({k: MODULE_STATE for k in ("astro", "ghost", "plain_static", "spotify_hosted", "independent_rss", "youtube")}),
    "podcast_authority": {"enum": ["undecided", "spotify", "independent"]},
    "safety": obj({"production_enabled": {"type": "boolean"}, "allow_remote_writes": {"type": "boolean"}}),
    "newsletter": {"enum": ["disabled", "planned", "enabled"]},
    "commerce": {"enum": ["disabled", "planned", "enabled"]},
    "ai_disclosure": nullable(obj({"text": text(1000), "spoken": {"type": "boolean"}},
                                  description="Show-level synthetic-voice disclosure (Apple guideline 1.11).")),
    "public_contact_email": nullable(ref("email")),
    "public_contact_acknowledged": {"type": "boolean",
                                    "description": "True only when the owner has acknowledged that this address becomes public (RSS feed)."},
    "service_inventory": nullable(obj({"path": ref("relpath"), "sha256": ref("sha256")})),
}, "Sole active configuration (IC-A8, IC-D6, IC-E3): no source_branch (branch policy is documentation); "
   "ai_disclosure; public contact e-mail with explicit acknowledgement; pinned service-inventory reference.")

SERVICE_INVENTORY = record("service-inventory", 1, "Service inventory v1", {
    "profile": {"enum": ["strict-zero", "standard"]},
    "services": arr(obj({
        "capability": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 64},
        "provider": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 64},
        "plan": {"type": "string", "pattern": "^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", "maxLength": 64},
        "state": {"enum": ["disabled", "planned", "enabled"]},
        "billing": obj({"payment_method_on_file": nullable({"type": "boolean"}),
                        "auto_recharge": nullable({"type": "boolean"}),
                        "overage_allowed": nullable({"type": "boolean"})}, required=[]),
        "evidence": obj({"checked_at": ref("date"), "source": text(500)}),
    }, required=["capability", "provider", "plan", "state"]), maxItems=200),
}, "Declared external services and their cost class (Agent E, IC-E3); checked fail-closed by "
   "feltwillow_publish.ops.strict_zero. A pass checks declarations, not provider dashboards.")

H2 = {
    "common.v2.schema.json": COMMON,
    "production-handoff.v1.schema.json": HANDOFF, "release.v2.schema.json": RELEASE,
    "approval.v2.schema.json": APPROVAL, "import-receipt.v1.schema.json": IMPORT_RECEIPT,
    "public-bundle-manifest.v1.schema.json": PUBLIC_MANIFEST, "contract-lock.v1.schema.json": CONTRACT_LOCK,
    "story-allocation.v1.schema.json": ALLOCATION, "web-bundle.v2.schema.json": WEB_BUNDLE,
    "episode-publication.v2.schema.json": EPISODE, "provider-registry.v2.schema.json": REGISTRY,
    "feed-observation.v1.schema.json": FEED_OBS, "publish-plan.v2.schema.json": PLAN,
    "publish-receipt.v2.schema.json": RECEIPT, "media-delivery.v2.schema.json": MEDIA_DELIVERY,
    "site-set.v2.schema.json": SITE_SET, "project.v2.schema.json": PROJECT,
    "service-inventory.v1.schema.json": SERVICE_INVENTORY,
    "handoff-selection.v1.schema.json": HANDOFF_SELECTION,
    "reading-edition.v1.schema.json": READING_EDITION,
}
# v2 package kinds carried forward unchanged (still current in H2) vs superseded by an H2 version.
V1_CURRENT = ["catalog", "collection", "rights-review", "show", "story"]
V1_SUPERSEDED = {"approval": 2, "release": 2, "web-bundle": 2, "episode-publication": 2, "provider-registry": 2,
                 "publish-plan": 2, "publish-receipt": 2, "media-delivery": 2, "site-set": 2, "project": 2}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, schema in H2.items():
        (OUT / name).write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    current = {k: f"schemas/{k}.v1.schema.json" for k in V1_CURRENT}
    for name, schema in H2.items():
        if name.startswith("common."):
            continue
        kind = schema["properties"]["kind"]["const"]
        current[kind] = "schemas/" + name
    rt = {"schema_version": 2, "contract_revision": "H2 (PROPOSED CONTRACT)",
          "canonicalization": "feltwillow-canonical-json-v1",
          "current": dict(sorted(current.items())),
          "shared": ["schemas/common.v1.schema.json", "schemas/common.v2.schema.json"],
          "superseded_v1": {k: {"schema": f"schemas/{k}.v1.schema.json", "successor_version": v}
                            for k, v in sorted(V1_SUPERSEDED.items())},
          "note": "v1 schema files are byte copies of the v2 blueprint package. Superseded v1 kinds are kept "
                  "for $ref resolution and explicit migration; the H2 validator rejects them with "
                  "CONTRACT_VERSION_UNSUPPORTED."}
    (OUT.parent / "record-types.json").write_text(json.dumps(rt, indent=2) + "\n", encoding="utf-8")
    print("wrote", len(H2), "H2 schemas and record-types.json")


if __name__ == "__main__":
    main()
