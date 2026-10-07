#!/usr/bin/env python3
"""Write the contract revision H2 examples (publishing/examples/) and test fixtures (tests/fixtures/).

PROPOSED CONTRACT. Deterministic; offline; reads nothing outside this scaffold (no production checkout, no
`git show`: Agent B's IC 8). Writes only publishing/examples/ and tests/fixtures/ (feeds, golden and
workflows are vendored files and are not rewritten here).

Value sources
  REPO evidence (measured by Agent B from production commit b880c23, recorded here as constants): source-file
    and keyframe sha256/bytes/dimensions, licensing register digest, six dirty paths observed at Stage 0.
    Paths that no longer exist after the owner's 2026-10-06 cleanup are cited only as b880c23 provenance;
    current/future production paths use the v5 location (DECISIONS_H2 s.0).
  OWNER decisions (OWNER_DECISIONS.md + lead message 2026-10-07): first podcast host Spotify; public contact
    e-mail; launch languages en, then es and de; storage = Microsoft 365 Personal OneDrive (1 TB plan,
    187 GB used) plus a 1 TB external drive.
  Everything else is synthetic, confined to records with "example": true and labelled EXAMPLE ONLY.
    No master, approval, provider ID or URL is invented.
Usage: python tools/build_examples.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from bllt_publish.contracts import cj1  # noqa: E402
from bllt_publish.podcast import podcast as P  # noqa: E402
import podcast_fixtures as PF  # noqa: E402

EX = ROOT / "publishing" / "examples"
FX = ROOT / "tests" / "fixtures"
COMMIT = "b880c230c6de419c809e879c422972c4122c9917"
SHA_X = "ab" * 32


def synth(label: str) -> str:
    """Deterministic synthetic digest for example-only values (clearly not a real file)."""
    return hashlib.sha256(("EXAMPLE ONLY " + label).encode()).hexdigest()


def write(path: Path, value, check=True):
    if check:
        cj1.check_domain(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def png(w: int, h: int, rgb) -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


AI_SHOW_TEXT = "All voices in this podcast are AI-generated."  # owner decision 2026-10-07 (EN)
AI_DISCLOSURE_NOTE = {  # owner decision 2026-10-07; ES/DE need a native-speaker check before use
    "spoken_intro": {"en": "This story is told with AI-generated voices.",
                     "es": "Esta historia se cuenta con voces generadas por inteligencia artificial.",
                     "de": "Diese Geschichte wird mit KI-generierten Stimmen erzählt."},
    "show_description": "All voices in this podcast are AI-generated.",
    "episode_description_last_line": "The voices in this episode are AI-generated.",
}
CONTRACT_PKG = {"name": "bllt-contracts", "version": "0.2.0-h2", "archive_sha256": synth("contract package 0.2.0-h2")}
PUBLISHING_COMMIT = synth("bllt-publishing commit")[:40]
NO_MEASURE = {"width_px": None, "height_px": None, "duration_ms": None, "sample_rate_hz": None,
              "channels": None, "frame_rate": None}

# ---------------------------------------------------------------- REPO evidence (Agent B, b880c23)
SOURCE_FILES = [
    {"source_id": "dialogue-v4", "purpose": "dialogue", "repo_role": "production",
     "path": "stories/lion_and_mouse_v4/dialogue_coverage.json", "commit": COMMIT,
     "sha256": "595e4b9669ef88f458c4feb59bfb364d64f54366450bb0b8d0a02e1a524737f8", "bytes": 77164},
    {"source_id": "prompt-manifest-v4", "purpose": "prompt-manifest", "repo_role": "production",
     "path": "stories/lion_and_mouse_v4/prompt_manifest.json", "commit": COMMIT,
     "sha256": "2734b6f0032c2d3f0c8aa2a744d4a742707e0cf8ca2c70b358af840e2eed7cf3", "bytes": 3240572},
    {"source_id": "runtime-inputs-v5", "purpose": "runtime", "repo_role": "production",
     "path": "stories/lion_and_mouse_v5/runtime_inputs.json", "commit": COMMIT,
     "sha256": "cc69c1c47c67978168cd35d51aae33c8bf172a7bb5737a5263a2cab79f251fbb", "bytes": 23342},
]
KF = "character/characters/lion_and_mouse_v5/interactions/keyframes/"
KEYFRAMES = [  # asset_id, file name, sha256, bytes, width, height (PNG IHDR), synthetic fixture colour
    ("illus-s01-explores-start", "s01_explores_start_r01.png",
     "2bf719f4756214ce7a804c4c9ad85587edaf54c43cd73a5f9e2f6c6ae36a3872", 4329316, 1920, 1080, (196, 160, 90)),
    ("illus-s01-acorn-start", "s01_acorn_start_r01.png",
     "eb2761b3be520496be21265fb6680e12998cf755c19387dec149ad2b1ceaa10f", 4327468, 1920, 1080, (120, 90, 40)),
]
LICENSING_MD_SHA = "95178ac1f052c4dccadcacf0af2aaa3cbc74b42fac7806e390abfe1a03a8f568"
DIRTY_AT_STAGE0 = ["CLAUDE.md", "production/export_runtime.py", "stories/lion_and_mouse_v5/story.yaml",
                   "stories/ugly_duckling_v1/prompt_manifest.json", "stories/ugly_duckling_v1/runtime_inputs.json",
                   "stories/ugly_duckling_v1/story.yaml"]
READING_TEXT = (b'{"kind":"reading-blocks","example":true,"note":"EXAMPLE ONLY: synthetic stand-in. The owner-approved '
                b'Lion-and-Mouse reading edition has not been supplied.","blocks":[{"type":"paragraph","text":"EXAMPLE '
                b'ONLY: the approved reading edition replaces this paragraph."},{"type":"image","asset_id":"illus-s01-'
                b'explores-start","alt":"EXAMPLE ONLY: alt text to be written and reviewed.","caption":null}]}')


def asset_from_keyframe(kf, synthetic=False):
    aid, name, sha, size, w, h, rgb = kf
    if synthetic:
        data = png(w, h, rgb)
        sha, size = hashlib.sha256(data).hexdigest(), len(data)
        origin = {"store": "owner-master-store", "ref": "SYNTHETIC-FIXTURE/" + name, "commit": None}
        note = (f"SYNTHETIC FIXTURE: solid-colour {w}x{h} PNG standing in for b880c23:{KF}{name} "
                f"(sha256 {kf[2][:12]}...) so tests build without the production checkout.")
    else:
        origin = {"store": "production-git", "ref": KF + name, "commit": COMMIT}
        note = ("EXAMPLE ONLY: a real tracked v5 video keyframe used to exercise the contract; "
                "NOT an owner-selected reading illustration.")
    return {"asset_id": aid, "role": "illustration", "media_type": "image/png", "bytes": size, "sha256": sha,
            "transport": "embedded", "package_path": f"files/{aid}/{name}",
            "measured": {**NO_MEASURE, "width_px": w, "height_px": h}, "derived_from": [],
            "origin": origin, "selection_note": note}


def record_head(kind, version):
    return {"kind": kind, "schema_version": version, "example": True, "canonicalization": "bllt-canonical-json-v1"}


def build_b_examples():
    out = {}
    out["alloc_lion"] = {**record_head("story-allocation", 1), "story_id": "lion-and-mouse", "status": "allocated",
                         "allocated_at": "2026-10-06T00:00:00Z", "allocated_by": "EXAMPLE-OWNER",
                         "working_title": "The Lion and the Mouse", "production_slugs": ["lion_and_mouse_v5"],
                         "planned_languages": ["en", "es", "de"]}  # owner: en first, then es and de
    out["alloc_fix"] = {**record_head("story-allocation", 1), "story_id": "fixture-second-story", "status": "allocated",
                        "allocated_at": "2026-10-06T00:00:00Z", "allocated_by": "EXAMPLE-OWNER",
                        "working_title": "EXAMPLE ONLY: synthetic second story",
                        "production_slugs": ["fixture_second_story_v1"], "planned_languages": ["en"]}
    reading = {"asset_id": "reading-text-en", "role": "reading-text",
               "media_type": "application/vnd.bllt.reading-blocks+json", "bytes": len(READING_TEXT),
               "sha256": hashlib.sha256(READING_TEXT).hexdigest(), "transport": "embedded",
               "package_path": "files/reading-text-en/reading-text.json", "measured": dict(NO_MEASURE),
               "derived_from": [], "origin": {"store": "owner-master-store", "ref": "EXAMPLE-ONLY/reading-text.example.json", "commit": None},
               "selection_note": "EXAMPLE ONLY: synthetic stand-in; the approved reading edition has not been supplied."}

    def lion_handoff(synthetic):
        return {
            **record_head("production-handoff", 1), "contract_package": CONTRACT_PKG,
            "envelope": {"created_at": "2026-10-06T18:00:00Z", "operator": "EXAMPLE-OPERATOR",
                         "exporter": {"tool": "production/export_handoff.py (PROPOSED)", "tool_version": "0.1.0",
                                      "repository": "jeilealr/big_lessons_little_tales", "commit": COMMIT,
                                      "tool_dirty": False},
                         "transport": "self-contained-tar"},
            "payload": {
                "handoff_id": "lion-and-mouse.en.h0001", "story_id": "lion-and-mouse", "language": "en",
                "handoff_revision": 1, "purpose": "initial", "supersedes": None, "reason": None,
                "story_allocation_sha256": cj1.digest(out["alloc_lion"]),
                "production_slugs": ["lion_and_mouse_v5"],
                "source_repositories": [{"repo_role": "production", "repository": "jeilealr/big_lessons_little_tales",
                                         "branch": "working-cloud-branch", "commit": COMMIT,
                                         "worktree": {"state": "dirty", "dirty_paths": DIRTY_AT_STAGE0}}],
                "source_files": copy.deepcopy(SOURCE_FILES),
                "assets": [copy.deepcopy(reading)] + [asset_from_keyframe(k, synthetic) for k in KEYFRAMES],
                "components": {"reading": {"text_asset": "reading-text-en",
                                           "illustration_assets": [k[0] for k in KEYFRAMES], "cover_asset": None},
                               "audio": None, "video": None},
                "editorial_selection": {"selected_by": "EXAMPLE-OWNER", "selected_at": "2026-10-06T17:00:00Z",
                                        "statement": "EXAMPLE ONLY: no owner selection of final Lion-and-Mouse assets has been made.",
                                        "evidence": []},
                "rights_evidence": [{"component": "images", "evidence": {"ref": "docs/licensing.md", "sha256": LICENSING_MD_SHA},
                                     "note": "EXAMPLE ONLY: b880c23 licensing register; image-tool terms still to verify; not a clearance."}],
                "generation_provenance": [],
            },
        }
    out["lion"] = lion_handoff(False)
    out["lion_synthetic"] = lion_handoff(True)

    def synth_asset(asset_id, role, mt, name, measured, derived=()):
        return {"asset_id": asset_id, "role": role, "media_type": mt, "bytes": 1000, "sha256": synth(asset_id),
                "transport": "embedded", "package_path": f"files/{asset_id}/{name}",
                "measured": {**NO_MEASURE, **measured}, "derived_from": list(derived),
                "origin": {"store": "owner-master-store", "ref": "EXAMPLE-ONLY/" + name, "commit": None},
                "selection_note": "EXAMPLE ONLY: synthetic digest, no file exists."}
    fix_commit = "1" * 40
    out["fix"] = {
        **record_head("production-handoff", 1), "contract_package": CONTRACT_PKG,
        "envelope": {"created_at": "2026-10-08T09:30:00Z", "operator": "EXAMPLE-OPERATOR",
                     "exporter": {"tool": "production/export_handoff.py (PROPOSED)", "tool_version": "0.1.0",
                                  "repository": "jeilealr/big_lessons_little_tales", "commit": fix_commit, "tool_dirty": False},
                     "transport": "self-contained-tar"},
        "payload": {
            "handoff_id": "fixture-second-story.en.h0002", "story_id": "fixture-second-story", "language": "en",
            "handoff_revision": 2, "purpose": "correction",
            "supersedes": {"handoff_id": "fixture-second-story.en.h0001", "payload_sha256": synth("fixture h0001 payload")},
            "reason": "EXAMPLE ONLY: narrator mispronunciation in scene 3 re-recorded; reading text unchanged.",
            "story_allocation_sha256": cj1.digest(out["alloc_fix"]), "production_slugs": ["fixture_second_story_v1"],
            "source_repositories": [{"repo_role": "production", "repository": "jeilealr/big_lessons_little_tales",
                                     "branch": "working-cloud-branch", "commit": fix_commit,
                                     "worktree": {"state": "clean", "dirty_paths": []}}],
            "source_files": [{"source_id": "script-en", "purpose": "script", "repo_role": "production",
                              "path": "stories/fixture_second_story_v1/dialogue_coverage.json", "commit": fix_commit,
                              "sha256": synth("fixture script"), "bytes": 5000}],
            "assets": [
                synth_asset("reading-text-en", "reading-text", "application/vnd.bllt.reading-blocks+json", "reading-text.json", {},
                            derived=[{"sha256": synth("fixture script"), "asset_id": None, "relation": "text-adaptation"}]),
                synth_asset("transcript-en", "spoken-transcript", "text/plain", "transcript.txt", {}),
                synth_asset("audio-master-en", "audio-master", "audio/wav", "master.wav",
                            {"duration_ms": 412500, "sample_rate_hz": 48000, "channels": 2},
                            derived=[{"sha256": synth("davinci lossless export"), "asset_id": None, "relation": "export"}]),
                synth_asset("audio-delivery-en", "audio-delivery", "audio/mpeg", "episode.mp3",
                            {"duration_ms": 412526, "sample_rate_hz": 44100, "channels": 2},
                            derived=[{"sha256": synth("audio-master-en"), "asset_id": "audio-master-en", "relation": "transcode"}]),
                synth_asset("illus-01", "illustration", "image/png", "illus-01.png", {"width_px": 1920, "height_px": 1080}),
                synth_asset("cover-en", "cover-art", "image/png", "cover.png", {"width_px": 3000, "height_px": 3000}),
            ],
            "components": {"reading": {"text_asset": "reading-text-en", "illustration_assets": ["illus-01"], "cover_asset": "cover-en"},
                           "audio": {"master_asset": "audio-master-en", "delivery_asset": "audio-delivery-en",
                                     "transcript_asset": "transcript-en"}, "video": None},
            "editorial_selection": {"selected_by": "EXAMPLE-OWNER", "selected_at": "2026-10-08T09:00:00Z",
                                    "statement": "EXAMPLE ONLY: owner selected the corrected final mix; video not part of this handoff.",
                                    "evidence": [{"ref": "EXAMPLE-ONLY/selection-notes.md", "sha256": None}]},
            "rights_evidence": [{"component": "voices", "evidence": {"ref": "EXAMPLE-ONLY/voice-terms-check.md", "sha256": None},
                                 "note": "EXAMPLE ONLY."}],
            "generation_provenance": [{"asset_id": "audio-master-en", "tools": ["EXAMPLE ONLY: tool list from production sidecars"],
                                       "evidence": {"ref": "EXAMPLE-ONLY/timing.json", "sha256": None}}],
        },
    }
    lion = out["lion"]
    archive_sha = synth("lion h0001 archive (not built for real)")
    out["lion_pin"] = {"handoff_id": "lion-and-mouse.en.h0001", "payload_sha256": cj1.digest(lion["payload"]),
                       "archive_sha256": archive_sha}
    kf1 = lion["payload"]["assets"][1]
    out["release"] = {
        **record_head("release", 2),
        "release_id": "lion-and-mouse.en.r0001", "story_id": "lion-and-mouse", "language": "en", "revision": 1,
        "lifecycle": "draft", "supersedes": None, "handoffs": [out["lion_pin"]],
        "content": {"title": "The Lion and the Mouse", "slug": "the-lion-and-the-mouse",
                    "summary": "EXAMPLE ONLY: replace with the owner-approved public description.",
                    "age_min": 3, "age_max": 7, "moral": "EXAMPLE ONLY: replace with the approved moral.",
                    "reading_text_asset": "reading-text-en", "spoken_transcript_asset": None,
                    "reading_divergence": "not-applicable",
                    "blocks": [{"type": "paragraph", "text": "EXAMPLE ONLY: the approved reading edition has not been supplied."},
                               {"type": "image", "asset_id": "illus-s01-explores-start", "alt": "EXAMPLE ONLY: alt text pending review.", "caption": None}]},
        "assets": [
            {"asset_id": "reading-text-en", "role": "reading-text",
             "origin": {"kind": "handoff", "handoff_id": "lion-and-mouse.en.h0001", "handoff_asset_id": "reading-text-en"},
             "sha256": hashlib.sha256(READING_TEXT).hexdigest(), "bytes": len(READING_TEXT),
             "media_type": "application/vnd.bllt.reading-blocks+json",
             "width": None, "height": None, "duration_ms": None, "selection": "pending", "derived_from_sha256": None},
            {"asset_id": "illus-s01-explores-start", "role": "image",
             "origin": {"kind": "handoff", "handoff_id": "lion-and-mouse.en.h0001", "handoff_asset_id": "illus-s01-explores-start"},
             "sha256": kf1["sha256"], "bytes": kf1["bytes"], "media_type": "image/png", "width": 1920, "height": 1080,
             "duration_ms": None, "selection": "pending", "derived_from_sha256": None}],
        "channels": {"website": {"requested": True, "player": "none", "audio_asset": None, "cover_asset": None,
                                 "podcast_episode_id": None, "youtube_edition_id": None},
                     "podcast": {"requested": True, "show_id": "bllt-en", "episode_id": "lion-and-mouse.en",
                                 "episode_type": "full", "audio_asset": None, "artwork_asset": None,
                                 "chapters_asset": None, "explicit": False},
                     "youtube": {"requested": False, "video_asset": None, "thumbnail_asset": None, "made_for_kids": True}},
        "rights": {"status": "pending", "record_path": "publishing/rights/lion-and-mouse/en/review-0001.yaml", "record_sha256": None},
        "emergency_override": None, "frozen_with": None,
    }
    out["release_pin"] = {"release_id": "lion-and-mouse.en.r0001", "release_sha256": cj1.digest(out["release"])}
    out["approval"] = {**record_head("approval", 2), "approval_id": "example-approval-0001",
                       "stage": "channel-readiness", "subject_type": "release", "subject_id": "lion-and-mouse.en.r0001",
                       "subject_sha256": out["release_pin"]["release_sha256"], "scope": "podcast", "decision": "rejected",
                       "revokes": None, "depends_on": [], "reviewed_by": "EXAMPLE-REVIEWER",
                       "reviewed_at": "2026-10-06T19:00:00Z", "reason": "EXAMPLE ONLY: release is a draft without audio.",
                       "checks": [{"name": "final-audio", "result": "fail",
                                   "evidence": "EXAMPLE ONLY: no selected audio master in handoff h0001."}]}
    out["approval_audio"] = {**record_head("approval", 2), "approval_id": "example-approval-0002",
                             "stage": "editorial-rights", "subject_type": "release", "subject_id": "lion-and-mouse.en.r0001",
                             "subject_sha256": out["release_pin"]["release_sha256"],
                             "scope": "rights_review.podcast_audio", "decision": "rejected", "revokes": None,
                             "depends_on": [], "reviewed_by": "EXAMPLE-REVIEWER", "reviewed_at": "2026-10-06T19:10:00Z",
                             "reason": "EXAMPLE ONLY: podcast-audio rights review cannot pass yet.",
                             "checks": [{"name": "gemini-terms-answer", "result": "fail",
                                         "evidence": "EXAMPLE ONLY: the Gemini Age Requirements question is drafted but not sent (REPO b880c23:docs/google_gemini_terms_question.md)."},
                                        {"name": "mix-music-and-effects", "result": "fail",
                                         "evidence": "EXAMPLE ONLY: no final DaVinci mix exists yet; music/effects sources unknown."}]}
    out["import_receipt"] = {
        **record_head("import-receipt", 1), "receipt_id": "imp-20261006T180500Z-0a1b2c3d", "outcome": "accepted",
        "errors": [], "handoff_id": "lion-and-mouse.en.h0001", "archive": {"sha256": archive_sha, "bytes": 8673280},
        "expected_archive_sha256": archive_sha, "expected_digest_source": "operator-out-of-band",
        "record_sha256": cj1.digest(lion), "payload_sha256": out["lion_pin"]["payload_sha256"],
        "schema_version_seen": 1, "supersedes": None, "consumer_supports": [1], "duplicate_of": None,
        "archival_locator": f"handoffs/{archive_sha}.tar", "promoted": True,
        "staged_at": "2026-10-06T18:05:00Z", "finished_at": "2026-10-06T18:05:09Z", "operator": "EXAMPLE-OPERATOR",
        "importer": {"tool": "bllt_publish.imports.importer (reference)", "tool_version": "0.2.0-h2", "publishing_commit": None},
        "authorizes_publication": False}
    return out


# ---------------------------------------------------------------- C: render-input bundles (web-bundle.v2)
WEB_IMAGES_SPEC = {
    "illus-s01-explores-start": ("lion", (16, 9, (196, 160, 90))),
    "cover-lion-and-mouse": ("lion", (9, 9, (120, 90, 40))),
    "illus-fixture-01": ("second", (16, 9, (90, 140, 200))),
}


def build_web(b):
    lion_rel = b["release_pin"]
    second_rel = {"release_id": "fixture-second-story.en.r0001", "release_sha256": synth("release fixture-second-story.en.r0001")}
    rel_of = {"lion": lion_rel, "second": second_rel}
    images = {k: (rel_of[r]["release_id"], png(*spec)) for k, (r, spec) in WEB_IMAGES_SPEC.items()}

    def media_entry(asset_id):
        release_id, data = images[asset_id]
        sha = hashlib.sha256(data).hexdigest()
        w, h = struct.unpack(">II", data[16:24])
        return {"path": f"media/{sha}.png", "sha256": sha, "bytes": len(data), "media_type": "image/png",
                "width": w, "height": h, "duration_ms": None, "source": {"release_id": release_id, "asset_id": asset_id}}
    lion = {"story_id": "lion-and-mouse", "language": "en", "release": lion_rel,
            "path": "/en/stories/the-lion-and-the-mouse/", "title": "The Lion and the Mouse",
            "summary": "EXAMPLE ONLY: replace with the owner-approved public description.",
            "moral": "EXAMPLE ONLY: replace with the approved moral.", "age_min": 3, "age_max": 7,
            "published_at": None, "updated_at": None,
            "cover": {"asset_id": "cover-lion-and-mouse", "alt": "EXAMPLE ONLY: cover alt text pending review."},
            "blocks": [{"type": "heading", "level": 2, "text": "EXAMPLE ONLY: part one"},
                       {"type": "paragraph", "text": "EXAMPLE ONLY: the approved reading edition has not been supplied."},
                       {"type": "image", "asset_id": "illus-s01-explores-start", "alt": "EXAMPLE ONLY: alt text pending review.", "caption": None},
                       {"type": "quote", "speaker": "EXAMPLE Mouse", "text": "EXAMPLE ONLY: a line of dialogue."}],
            "reading_divergence": "not-applicable", "transcript": None,
            "listening": {"duration_ms": None, "player": {"type": "none"}, "links": []}, "video": None}
    second = {"story_id": "fixture-second-story", "language": "en", "release": second_rel,
              "path": "/en/stories/fixture-second-story/", "title": "EXAMPLE ONLY: synthetic second story",
              "summary": "EXAMPLE ONLY: synthetic fixture used to prove complete site-sets.", "moral": "EXAMPLE ONLY.",
              "age_min": 3, "age_max": 8, "published_at": None, "updated_at": None, "cover": None,
              "blocks": [{"type": "paragraph", "text": "EXAMPLE ONLY: first paragraph."},
                         {"type": "image", "asset_id": "illus-fixture-01", "alt": "EXAMPLE ONLY: fixture alt text.",
                          "caption": "EXAMPLE ONLY: caption."},
                         {"type": "paragraph", "text": "EXAMPLE ONLY: paragraph after the illustration."}],
              "reading_divergence": "identical", "transcript": None,
              "listening": {"duration_ms": None, "player": {"type": "none"}, "links": []}, "video": None}
    pages = [{"page_id": "about", "language": "en", "path": "/en/about/", "title": "EXAMPLE ONLY: About",
              "blocks": [{"type": "paragraph", "text": "EXAMPLE ONLY: owner-approved about text pending."}]},
             {"page_id": "privacy", "language": None, "path": "/privacy/", "title": "EXAMPLE ONLY: Privacy",
              "blocks": [{"type": "paragraph", "text": "EXAMPLE ONLY: approved privacy text pending."}]}]
    manifests = {}
    for name, stories in (("site-set-0001", [lion]), ("site-set-0002", [lion, second])):
        site_set_id = "example-" + name
        media_ids = sorted({x["asset_id"] for s in stories for x in s["blocks"] if x["type"] == "image"}
                           | {s["cover"]["asset_id"] for s in stories if s["cover"]})
        payload = {**record_head("web-bundle", 2),
                   "site_set": {"site_set_id": site_set_id, "sha256": synth("site-set " + site_set_id)},
                   "origin": None, "brand": {"name": "Big Lessons, Little Tales"}, "default_language": "en",
                   "trailing_slash": "always",
                   # owner launch order: en first; es and de follow in later site-sets
                   "languages": [{"language": "en", "label": "English", "path": "/en/"}],
                   "pages": pages, "stories": stories, "redirects": [],
                   "media": {m: media_entry(m) for m in media_ids}}
        root = EX / "web" / "render-input" / name
        if root.exists():
            shutil.rmtree(root)
        (root / "data").mkdir(parents=True)
        (root / "media").mkdir()
        body = cj1.canonical_bytes(payload)
        (root / "data" / "web-bundle.json").write_bytes(body)
        files = [{"path": "data/web-bundle.json", "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                  "media_type": "application/json", "source": None}]
        for aid, m in payload["media"].items():
            (root / m["path"]).write_bytes(images[aid][1])
            files.append({"path": m["path"], "sha256": m["sha256"], "bytes": m["bytes"], "media_type": m["media_type"],
                          "source": m["source"]})
        manifest = {**record_head("public-bundle-manifest", 1), "bundle_id": f"example-web-input-{name}",
                    "bundle_type": "web", "manifest_visibility": "internal",
                    "inputs": {"releases": sorted((s["release"] for s in stories), key=lambda r: r["release_id"]),
                               "site_set": payload["site_set"], "public_record_sha256": cj1.digest(payload),
                               "renderer": None, "contract_package": CONTRACT_PKG},
                    "files": sorted(files, key=lambda f: f["path"])}
        write(EX / "web" / "manifests" / f"render-input.{name}.json", manifest)
        manifests[name] = manifest
    return manifests


# ---------------------------------------------------------------- H2 lead records
def build_h2(b, manifests):
    out = {}
    out["service_inventory"] = {
        **record_head("service-inventory", 1), "profile": "standard",
        "services": [
            {"capability": "podcast-host", "provider": "spotify-for-creators", "plan": "free", "state": "planned",
             "billing": {"auto_recharge": False},
             "evidence": {"checked_at": "2026-10-06", "source": "Owner decision 2026-10-07: Spotify is the first podcast host; free plan per Agent D's register (D-00)."}},
            {"capability": "source-hosting", "provider": "github", "plan": "free", "state": "enabled",
             "billing": {"payment_method_on_file": None},
             "evidence": {"checked_at": "2026-10-06", "source": "jeilealr/bllt-publishing exists (private, owner decision); plan not observed by agents."}},
            {"capability": "backup-cloud-storage", "provider": "onedrive", "plan": "microsoft-365-personal", "state": "enabled",
             "billing": {"auto_recharge": None},
             "evidence": {"checked_at": "2026-10-07", "source": "Owner statement 2026-10-07: Microsoft 365 Personal, 1 TB plan, 187 GB used."}},
            {"capability": "backup-local-disk", "provider": "owner-external-hdd", "plan": "owned-1tb", "state": "enabled",
             "billing": {},
             "evidence": {"checked_at": "2026-10-07", "source": "Owner statement 2026-10-07: 1 TB external drive."}},
            {"capability": "website-static-host", "provider": "cloudflare-pages", "plan": "free", "state": "disabled"},
        ]}
    out["project"] = {
        **record_head("project", 2), "project_id": "big-lessons-little-tales", "profile_option": "undecided",
        "website": {"primary": "none", "origin": None, "locale_prefixes": True},
        "modules": {"astro": "spec_only", "ghost": "spec_only", "plain_static": "spec_only",
                    "spotify_hosted": "spec_only", "independent_rss": "spec_only", "youtube": "spec_only"},
        "podcast_authority": "spotify",  # owner decision 2026-10-07
        "safety": {"production_enabled": False, "allow_remote_writes": False},
        "newsletter": "disabled", "commerce": "disabled",
        # Owner decision 2026-10-07 (L-27): show-level wording, spoken at the start of every episode.
        # project.v2 has one text field; the episode-description line and the ES/DE spoken lines (which need
        # a native-speaker check) are recorded in AI_DISCLOSURE_NOTE / README, not in the record.
        "ai_disclosure": {"text": AI_SHOW_TEXT, "spoken": True},
        "public_contact_email": "jei.leal.r@gmail.com",  # owner decision 2026-10-07
        "public_contact_acknowledged": True,  # L-27: owner supplied it knowing it becomes public in the feed
        "service_inventory": {"path": "publishing/service-inventory.json", "sha256": cj1.digest(out["service_inventory"])},
    }
    pins = {"publishing_commit": PUBLISHING_COMMIT, "contract_version": CONTRACT_PKG["version"],
            "contract_package": CONTRACT_PKG, "handoff_package_digests": [b["lion_pin"]]}
    out["site_set"] = {**record_head("site-set", 2), "site_set_id": "example-site-set-0001", "lifecycle": "draft",
                       "renderer": "plain_static", "entries": [b["release_pin"]], "remove_paths": [], **pins}
    m1 = manifests["site-set-0001"]
    out["plan_web"] = {
        **record_head("publish-plan", 2), "plan_id": "example-plan-web-0001",
        "created_at": "2026-10-07T10:00:00Z", "expires_at": "2026-10-07T11:00:00Z",
        "environment": "preview", "destination": "website", **pins,
        "project_sha256": cj1.digest(out["project"]),
        "site_set": {"site_set_id": "example-site-set-0001", "sha256": cj1.digest(out["site_set"])},
        "registry_sha256": synth("provider registry"), "releases": [b["release_pin"]],
        "check_reports": {"leak_scan": {"report_sha256": synth("leak_scan report"),
                                        "bundle_manifest_sha256": cj1.digest(m1), "clean": True},
                          "strict_zero": None},
        "actions": [{"action_id": "deploy-preview", "target": "static-site", "operation": "deploy",
                     "subject_id": "example-site-set-0001",
                     "artifact": {"sha256": synth("site artifact tar"), "bytes": 40960}}],
        "newsletter_send": False,
        "auxiliary_inputs": [{"record_kind": "public-bundle-manifest", "path": "build/bundles/example-web-input-site-set-0001.json",
                              "sha256": cj1.digest(m1)}]}
    ep_prepared = PF.ep()
    out["plan_podcast"] = {
        **record_head("publish-plan", 2), "plan_id": "example-plan-podcast-0001",
        "created_at": "2026-10-07T10:00:00Z", "expires_at": "2026-10-08T10:00:00Z",
        "environment": "production", "destination": "podcast", **pins,
        "project_sha256": cj1.digest(out["project"]), "site_set": None,
        "registry_sha256": synth("provider registry"), "releases": [b["release_pin"]],
        "check_reports": {"leak_scan": None, "strict_zero": {"report_sha256": synth("strict_zero report"), "pass": True}},
        "actions": [{"action_id": "upload-episode", "target": "spotify", "operation": "manual-upload",
                     "subject_id": "lion-and-mouse.en",
                     "artifact": {"sha256": ep_prepared["submitted_audio"]["sha256"], "bytes": ep_prepared["submitted_audio"]["bytes"]}},
                    {"action_id": "observe-feed", "target": "spotify", "operation": "observe_feed",
                     "subject_id": "example-show-en", "artifact": None}],
        "newsletter_send": False,
        "auxiliary_inputs": [{"record_kind": "episode-publication", "path": "publishing/episodes/example-show-en/lion-and-mouse.en.json",
                              "sha256": cj1.digest(ep_prepared)}]}
    out["receipt_pending"] = {
        **record_head("publish-receipt", 2), "plan_id": "example-plan-podcast-0001",
        "plan_sha256": cj1.digest(out["plan_podcast"]), "action_id": "upload-episode", "operation": "manual-upload",
        "result": "manual_pending", "observed_at": "2026-10-07T10:05:00Z", "external_id": None, "external_url": None,
        "observation_id": None, "submitted_sha256": None, "evidence": None, "conflict": None}
    out["receipt_conflict"] = {
        **record_head("publish-receipt", 2), "plan_id": "example-plan-ghost-0001", "plan_sha256": synth("ghost plan"),
        "action_id": "update-story-post", "operation": "update-draft", "result": "conflict",
        "observed_at": "2026-10-07T10:06:00Z", "external_id": None, "external_url": None, "observation_id": None,
        "submitted_sha256": None, "evidence": {"ref": "EXAMPLE-ONLY/ghost-readback.json", "sha256": synth("ghost readback")},
        "conflict": {"code": "GHOST_REMOTE_EDIT_CONFLICT",
                     "detail": "EXAMPLE ONLY: updated_at and read-back digest differ from the last write; operator must adopt or discard."}}
    out["media_delivery"] = {
        **record_head("media-delivery", 2),
        "records": [{"asset_sha256": PF.SHA_B, "provider": "spotify", "url": "https://media.example.invalid/ep1-a.mp3",
                     "observed_sha256": None, "observed_bytes": 6600000, "duration_ms": 412500,
                     "observed_at": "2026-10-06T19:00:00Z", "access": "public", "review": "pending"}]}
    return out


# ---------------------------------------------------------------- negative record fixtures
def rec(code, base, patch, description, rule="H1 (Agent B)"):
    return {"fixture": "negative-record", "expect": code, "base": base, "patch": patch, "description": description, "rule": rule}


def imp(code, mutations, description, options=None):
    return {"fixture": "negative-import", "expect": code, "base_package": "lion-h0001-synthetic",
            "mutations": mutations, "options": options or {}, "description": description}


def rep(path, value):
    return {"op": "replace", "path": path, "value": value}


def add(path, value):
    return {"op": "add", "path": path, "value": value}


def rem(path):
    return {"op": "remove", "path": path}


E = "publishing/examples/"
H_LION = E + "production-handoff.lion-and-mouse.example.json"
H_FIX = E + "production-handoff.fixture-second-story.example.json"
REL = E + "release.v2.lion-and-mouse.draft.example.json"
APP = E + "approval.v2.rejected.example.json"
APP_A = E + "approval.v2.podcast-audio-rights-review.example.json"
REC = E + "import-receipt.accepted.example.json"
MAN = E + "public-bundle-manifest.web.example.json"
LOCK = E + "contract-lock.example.json"
ALLOC = E + "story-allocation.lion-and-mouse.example.json"
PLAN_W = E + "publish-plan.v2.website-preview.example.json"
PLAN_P = E + "publish-plan.v2.podcast-spotify.example.json"
RCPT = E + "publish-receipt.v2.manual-pending.example.json"
RCPT_C = E + "publish-receipt.v2.ghost-conflict.example.json"
MD = E + "media-delivery.v2.example.json"
SS = E + "site-set.v2.example.json"
PJ = E + "project.v2.example.json"
SI = E + "service-inventory.v1.example.json"
SEL = E + "handoff-selection.v1.lion-and-mouse.example.json"
V2C = "tests/fixtures/v2-carried/"
CAT, STORY, SHOW, COLL, RR = (V2C + k + ".example.json" for k in ("catalog", "story", "show", "collection", "rights-review"))
WEB = E + "web/render-input/site-set-0002/data/web-bundle.json"
V2 = "v2 rule ported (B1, Agent F)"
V1_ASSET = {"asset_id": "coll-master", "role": "audio-master", "store": "masters", "path": "masters/coll.wav",
            "sha256": "cd" * 32, "bytes": 1, "media_type": "audio/wav", "width": None, "height": None,
            "duration_seconds": None, "selection": "pending", "derived_from_sha256": None}
ITEM = {"episode_id": "lion-and-mouse.en", "release_id": "lion-and-mouse.en.r0001", "release_sha256": "ab" * 32, "order": 1}
PNG1 = "files/illus-s01-explores-start/s01_explores_start_r01.png"
TXT = "files/reading-text-en/reading-text.json"
PASS_CHECK = {"name": "x", "result": "pass", "evidence": "EXAMPLE ONLY"}

B_RECORD_CASES = {
    "h01-unknown-top-level-field": rec("SCHEMA_VIOLATION", H_LION, [add("/surprise", True)], "Unknown fields are errors."),
    "h02-unsupported-schema-version": rec("CONTRACT_VERSION_UNSUPPORTED", H_LION, [rep("/schema_version", 2)], "Consumer supports production-handoff v1 only."),
    "h03-handoff-id-mismatch": rec("HANDOFF_ID_MISMATCH", H_LION, [rep("/payload/handoff_id", "lion-and-mouse.en.h0002")], "handoff_id = <story>.<lang>.h<revision>."),
    "h04-correction-without-supersedes": rec("SUPERSEDES_REQUIRED", H_FIX, [rep("/payload/supersedes", None)], "Revision > 1 names what it supersedes."),
    "h05-initial-with-supersedes": rec("SUPERSEDES_UNEXPECTED", H_LION, [rep("/payload/supersedes", {"handoff_id": "lion-and-mouse.en.h0001", "payload_sha256": SHA_X})], "A first handoff supersedes nothing."),
    "h06-duplicate-asset-id": rec("DUPLICATE_ASSET_ID", H_LION, [rep("/payload/assets/2/asset_id", "illus-s01-explores-start"), rep("/payload/assets/2/package_path", "files/illus-s01-explores-start/s01_acorn_start_r01.png")], "Asset IDs are unique."),
    "h07-component-unknown-asset": rec("UNKNOWN_ASSET", H_LION, [add("/payload/components/reading/illustration_assets/-", "illus-missing")], "Components reference declared assets only."),
    "h08-component-wrong-role": rec("WRONG_ASSET_ROLE", H_LION, [rep("/payload/components/reading/cover_asset", "illus-s01-acorn-start"), rep("/payload/components/reading/illustration_assets", ["illus-s01-explores-start"])], "An illustration is not cover art."),
    "h09-media-type-role-mismatch": rec("MEDIA_TYPE_ROLE_MISMATCH", H_LION, [rep("/payload/assets/1/media_type", "audio/wav")], "An illustration is an image."),
    "h10-missing-image-measurement": rec("MISSING_MEASUREMENT", H_LION, [rep("/payload/assets/1/measured/width_px", None)], "Images need measured dimensions."),
    "h11-package-path-mismatch": rec("PACKAGE_PATH_MISMATCH", H_LION, [rep("/payload/assets/1/package_path", "files/illus-s01-acorn-start/x.png")], "Package folder = asset_id."),
    "h12-source-path-traversal": rec("UNSAFE_PATH", H_LION, [rep("/payload/source_files/0/path", "../secrets/key.txt")], "No traversal in provenance paths."),
    "h13-selected-source-dirty": rec("SELECTED_SOURCE_DIRTY", H_LION, [rep("/payload/source_files/2/path", "stories/lion_and_mouse_v5/story.yaml")], "A dirty selected source is rejected."),
    "h14-float-duration": rec("CJ_FLOAT", H_FIX, [rep("/payload/assets/2/measured/duration_ms", 412500.0)], "No floats in the canonical domain."),
    "h15-publication-approval-smuggled": rec("SCHEMA_VIOLATION", H_LION, [add("/payload/publication_approved", True)], "A handoff carries no publication approval."),
    "h16-parent-hash-mismatch": rec("PARENT_HASH_MISMATCH", H_FIX, [rep("/payload/assets/3/derived_from/0/sha256", SHA_X)], "Parent digest matches the parent asset."),
    "h17-derivation-self-cycle": rec("DERIVATION_CYCLE", H_FIX, [rep("/payload/assets/2/derived_from", [{"sha256": "8f" + "0" * 62, "asset_id": "audio-delivery-en", "relation": "other"}]), rep("/payload/assets/3/sha256", "8f" + "0" * 62)], "Master derived from its own derivative."),
    "h18-referenced-media": rec("REFERENCED_MEDIA_NOT_SUPPORTED", H_LION, [rep("/payload/assets/1/transport", "referenced"), rep("/payload/assets/1/package_path", None)], "Only embedded media."),
    "h19-no-components": rec("NO_COMPONENTS", H_LION, [rep("/payload/components/reading", None)], "At least one component."),
    "h20-revocation-with-assets": rec("REVOCATION_WITH_ASSETS", H_FIX, [rep("/payload/purpose", "revocation")], "A revocation carries no assets."),
    "h21-created-before-selected": rec("TIMESTAMP_ORDER", H_LION, [rep("/envelope/created_at", "2026-10-06T16:00:00Z")], "Export cannot precede selection."),
    "h22-nfd-text": rec("CJ_NOT_NFC", H_LION, [rep("/payload/editorial_selection/statement", "Café selection")], "Strings are NFC."),
    "h23-url-as-private-ref": rec("REMOTE_REFERENCE_FORBIDDEN", H_LION, [rep("/payload/rights_evidence/0/evidence/ref", "https://drive.example.invalid/contract.pdf")], "Private refs are never URLs."),
    "h24-local-time": rec("SCHEMA_VIOLATION", H_LION, [rep("/envelope/created_at", "2026-10-06T21:00:00+03:00")], "UTC with Z."),
    "h25-exporter-dirty": rec("EXPORTER_DIRTY", H_LION, [rep("/envelope/exporter/tool_dirty", True)], "Exporter runs from committed code."),
    "h26-unreferenced-asset": rec("UNREFERENCED_ASSET", H_LION, [rep("/payload/components/reading/illustration_assets", ["illus-s01-explores-start"])], "No stray assets."),
    "h27-large-integer": rec("CJ_INT_RANGE", H_LION, [rep("/payload/assets/1/bytes", 9007199254740993)], "Integers within +-(2^53-1)."),
    "h28-correction-without-reason": rec("REASON_REQUIRED", H_FIX, [rep("/payload/reason", None)], "Corrections state a reason."),
    "r01-frozen-without-handoff": rec("FROZEN_WITHOUT_HANDOFF", REL, [rep("/lifecycle", "frozen"), rep("/handoffs", []), rep("/assets", []), rep("/content/reading_text_asset", None), rep("/content/blocks", [{"type": "paragraph", "text": "x"}]), rep("/frozen_with", {"publishing_commit": "2" * 40, "tool_version": "0.1.0", "contract_package": {"name": "bllt-contracts", "version": "0.1.0", "archive_sha256": SHA_X}})], "Frozen release cites its handoffs."),
    "r02-release-id-mismatch": rec("RELEASE_ID_MISMATCH", REL, [rep("/release_id", "lion-and-mouse.en.r0002")], "release_id agrees with revision."),
    "r03-unlisted-handoff": rec("UNLISTED_HANDOFF", REL, [rep("/assets/1/origin/handoff_id", "lion-and-mouse.en.h0009")], "Origins resolve through pinned handoffs."),
    "r04-v1-schema-version": rec("CONTRACT_VERSION_UNSUPPORTED", REL, [rep("/schema_version", 1)], "v1 releases are migrated explicitly."),
    "r05-float-age": rec("CJ_FLOAT", REL, [rep("/content/age_min", 3.0)], "No floats."),
    "a01-approved-with-failed-check": rec("INVALID_POSITIVE_APPROVAL", APP, [rep("/decision", "approved"), add("/depends_on/-", {"approval_id": "ed-1", "approval_sha256": SHA_X})], "A failed check cannot be approved."),
    "a02-revoked-without-target": rec("REVOCATION_TARGET_MISSING", APP, [rep("/decision", "revoked")], "Revocation names its target."),
    "a03-readiness-without-chain": rec("APPROVAL_CHAIN_MISSING", APP, [rep("/decision", "approved"), rep("/checks/0/result", "pass")], "Readiness depends on editorial-rights."),
    "a04-deployment-on-release": rec("STAGE_SUBJECT_MISMATCH", APP, [rep("/stage", "deployment")], "Deployment binds a plan/site-set/project."),
    "a05-old-approval-v1": rec("CONTRACT_VERSION_UNSUPPORTED", APP, [rep("/schema_version", 1)], "v1 approvals are not accepted."),
    "i01-accepted-with-errors": rec("RECEIPT_OUTCOME_INCONSISTENT", REC, [rep("/errors", ["HASH_MISMATCH"])], "Accepted receipts have no errors."),
    "i02-receipt-authorizes-publication": rec("SCHEMA_VIOLATION", REC, [rep("/authorizes_publication", True)], "A receipt is never an approval."),
    "i03-locator-mismatch": rec("ARCHIVAL_LOCATOR_MISMATCH", REC, [rep("/archival_locator", "handoffs/" + SHA_X + ".tar")], "Locator is handoffs/<archive sha256>.tar.", rule="H2 s.2 layout"),
    "p01-public-env-file": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "assets/.env.production", "sha256": SHA_X, "bytes": 10, "media_type": "text/plain", "source": None})], "No secrets files."),
    "p02-public-serverless-entry": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "functions/api.js", "sha256": SHA_X, "bytes": 10, "media_type": "application/javascript", "source": None})], "No serverless entry points."),
    "p03-public-handoff-json": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "data/handoff.json", "sha256": SHA_X, "bytes": 10, "media_type": "application/json", "source": None})], "No private records."),
    "p04-public-path-traversal": rec("UNSAFE_PATH", MAN, [rep("/files/0/path", "../index.html")], "No traversal."),
    "l01-lock-duplicate-path": rec("DUPLICATE_LOCK_PATH", LOCK, [add("/files/-", {"path": "schemas/common.v2.schema.json", "sha256": SHA_X})], "One digest per file."),
    "l02-lock-missing-emitted-schema": rec("LOCK_MISSING_EMITTED_SCHEMA", LOCK, [rep("/producer_emits/production-handoff", 2)], "Emitted version must be pinned."),
    "s01-allocation-bad-id": rec("SCHEMA_VIOLATION", ALLOC, [rep("/story_id", "Lion_and_Mouse_v5")], "Story IDs are slugs."),
}

H2 = "H2 (DECISIONS_H2)"
H2_RECORD_CASES = {
    "c01-missing-canonicalization": rec("SCHEMA_VIOLATION", REL, [rem("/canonicalization")], "Every H2 record carries the canonicalization constant (s.3).", H2),
    "c02-wrong-canonicalization": rec("SCHEMA_VIOLATION", ALLOC, [rep("/canonicalization", "jcs-rfc8785")], "JCS migration rejected for now (s.3).", H2),
    "c03-common-v2-email-pattern": rec("SCHEMA_VIOLATION", PJ, [rep("/public_contact_email", "not-an-address")], "common.v2 email.", H2),
    "ap01-podcast-audio-review-missing-checks": rec("RIGHTS_REVIEW_EVIDENCE_MISSING", APP_A, [rep("/decision", "approved"), rep("/checks", [PASS_CHECK])], "rights_review.podcast_audio needs gemini-terms-answer and mix-music-and-effects (IC-D7).", H2),
    "ap02-podcast-audio-review-wrong-stage": rec("STAGE_SUBJECT_MISMATCH", APP_A, [rep("/stage", "channel-readiness")], "The scope belongs to the editorial-rights stage.", H2),
    "ap03-unknown-scope": rec("SCHEMA_VIOLATION", APP_A, [rep("/scope", "rights_review.audiobook")], "Audiobook scopes deferred to backlog (s.7).", H2),
    "pm01-renderer-old-spelling": rec("SCHEMA_VIOLATION", MAN, [rep("/inputs/renderer", {"name": "plain-static", "version": "0.0.1"})], "Module ids astro/ghost/plain_static (IC-C3).", H2),
    "pm02-renderer-ghost-theme": rec("SCHEMA_VIOLATION", MAN, [rep("/inputs/renderer", {"name": "ghost-theme", "version": "0.0.1"})], "ghost-theme is a folder name, not a module id.", H2),
    "p05-public-import-receipt-name": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "data/import-receipt.x.json", "sha256": SHA_X, "bytes": 10, "media_type": "application/json", "source": None})], "E's wider name rule (IC-E5): B's rule missed this.", H2),
    "p06-public-release-record-name": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "data/release.v2.lion.json", "sha256": SHA_X, "bytes": 10, "media_type": "application/json", "source": None})], "E's wider name rule (IC-E5).", H2),
    "p07-public-source-map": rec("PUBLIC_FORBIDDEN_FILE", MAN, [add("/files/-", {"path": "assets/site.js.map", "sha256": SHA_X, "bytes": 10, "media_type": "application/json", "source": None})], "E's wider name rule (IC-E5).", H2),
    "i04-old-archive-layout": rec("SCHEMA_VIOLATION", REC, [rep("/archival_locator", "handoffs/lion-and-mouse/en/lion-and-mouse.en.h0001." + SHA_X + ".tar")], "Archive layout moved to BLLT_MASTER_ROOT/handoffs/<sha256>.tar (s.2).", H2),
    "pl01-website-plan-touches-podcast": rec("WEBSITE_PLAN_TOUCHES_PODCAST", PLAN_W, [add("/auxiliary_inputs/-", {"record_kind": "episode-publication", "path": "publishing/episodes/x.json", "sha256": SHA_X})], "IC-D12: a website plan may not change podcast records.", H2),
    "pl02-deploy-without-leak-scan": rec("LEAK_SCAN_REPORT_REQUIRED", PLAN_W, [rep("/check_reports/leak_scan", None)], "IC-E2: plan pins a clean leak_scan report.", H2),
    "pl03-production-without-strict-zero": rec("STRICT_ZERO_REPORT_REQUIRED", PLAN_W, [rep("/environment", "production")], "IC-E2: production plans pin a strict_zero report.", H2),
    "pl04-contract-version-pin-mismatch": rec("CONTRACT_VERSION_PIN_MISMATCH", PLAN_W, [rep("/contract_version", "0.1.0")], "IC-A2 pins agree.", H2),
    "pl05-v1-source-commit": rec("SCHEMA_VIOLATION", PLAN_W, [add("/source_commit", "b880c230c6de419c809e879c422972c4122c9917")], "v1 source_commit replaced by publishing_commit (IC-A2).", H2),
    "pl06-operation-target-mismatch": rec("UNSUPPORTED_OPERATION", PLAN_W, [rep("/actions/0/operation", "manual_audio_replace")], "Manual operations only on their targets (IC-D4).", H2),
    "pl07-deploy-without-artifact": rec("ARTIFACT_REQUIRED", PLAN_W, [rep("/actions/0/artifact", None)], "Uploads name a content-addressed artifact (IC-D4).", H2),
    "pl08-spotify-action-in-website-plan": rec("ACTION_DESTINATION_MISMATCH", PLAN_W, [add("/actions/-", {"action_id": "obs", "target": "spotify", "operation": "observe_feed", "subject_id": "s", "artifact": None})], "Explicit destination (IC-D4).", H2),
    "pl09-ghost-input-without-ghost-action": rec("GHOST_INPUT_WITHOUT_GHOST_ACTION", PLAN_W, [add("/auxiliary_inputs/-", {"record_kind": "ghost-routes", "path": "build/ghost/routes.yaml", "sha256": SHA_X})], "Ghost artifacts pinned only for Ghost actions (IC-C4).", H2),
    "pl10-duplicate-handoff-pin": rec("DUPLICATE_HANDOFF_PIN", PLAN_P, [add("/handoff_package_digests/-", {"handoff_id": "lion-and-mouse.en.h0001", "payload_sha256": SHA_X, "archive_sha256": SHA_X})], "One pin per handoff.", H2),
    "pl11-observe-feed-with-artifact": rec("ARTIFACT_UNEXPECTED", PLAN_P, [rep("/actions/1/artifact", {"sha256": SHA_X, "bytes": 1})], "Observation uploads nothing.", H2),
    "pl12-newsletter-send": rec("SCHEMA_VIOLATION", PLAN_W, [rep("/newsletter_send", True)], "Plans never send newsletters (v2 rule kept).", H2),
    "rc01-conflict-without-detail": rec("CONFLICT_INCONSISTENT", RCPT_C, [rep("/conflict", None)], "conflict result carries its code (IC-B4).", H2),
    "rc02-succeeded-without-evidence": rec("RECEIPT_EVIDENCE_REQUIRED", RCPT, [rep("/result", "succeeded"), rep("/submitted_sha256", PF.SHA_B)], "Success needs a private evidence reference (IC-D5).", H2),
    "rc03-evidence-free-text": rec("SCHEMA_VIOLATION", RCPT, [rep("/evidence", "uploaded it, looked fine")], "Evidence is a private_ref, not free text (IC-D5).", H2),
    "rc04-observe-without-observation-id": rec("OBSERVATION_ID_REQUIRED", RCPT, [rep("/operation", "observe_feed"), rep("/action_id", "observe-feed"), rep("/result", "succeeded"), rep("/evidence", {"ref": "EXAMPLE-ONLY/feed.xml", "sha256": SHA_X})], "Feed observations link their observation_id.", H2),
    "rc05-v1-manual-pending-spelling": rec("SCHEMA_VIOLATION", RCPT, [rep("/result", "manual-pending")], "Status spelling manual_pending (s.3).", H2),
    "rc06-pending-with-outcome": rec("MANUAL_PENDING_WITH_OUTCOME", RCPT, [rep("/external_id", "x")], "manual_pending is written before the owner acts.", H2),
    "rc07-upload-without-submitted-sha": rec("SUBMITTED_SHA256_REQUIRED", RCPT, [rep("/result", "succeeded"), rep("/evidence", {"ref": "EXAMPLE-ONLY/upload.png", "sha256": SHA_X})], "Submitted file digest kept (IC-D5).", H2),
    "md01-float-duration": rec("CJ_FLOAT", MD, [rep("/records/0/duration_ms", 412.5)], "Integer duration_ms (IC-B2).", H2),
    "md02-v1-duration-seconds": rec("SCHEMA_VIOLATION", MD, [add("/records/0/duration_seconds", 412)], "duration_seconds removed (IC-B2).", H2),
    "md03-duplicate-url": rec("DUPLICATE_DELIVERY_URL", MD, [add("/records/-", {"asset_sha256": SHA_X, "provider": "spotify", "url": "https://media.example.invalid/ep1-a.mp3", "observed_sha256": None, "observed_bytes": 1, "duration_ms": None, "observed_at": "2026-10-06T19:00:00Z", "access": "public", "review": "pending"})], "One delivery record per URL.", H2),
    "ss01-renderer-old-spelling": rec("SCHEMA_VIOLATION", SS, [rep("/renderer", "plain-static")], "Module ids (IC-C3).", H2),
    "ss02-v1-source-commit": rec("SCHEMA_VIOLATION", SS, [add("/source_commit", "b880c230c6de419c809e879c422972c4122c9917")], "Same pins as publish-plan (IC-A2).", H2),
    "ss03-duplicate-story": rec("DUPLICATE_SITE_EDITION", SS, [add("/entries/-", {"release_id": "lion-and-mouse.en.r0002", "release_sha256": SHA_X})], "One release per story-language.", H2),
    "ss04-pin-mismatch": rec("CONTRACT_VERSION_PIN_MISMATCH", SS, [rep("/contract_version", "9.9.9")], "Pins agree.", H2),
    "pj01-source-branch": rec("SCHEMA_VIOLATION", PJ, [add("/source_branch", "main")], "project.source_branch removed (L-08).", H2),
    "pj02-podcast-enabled-without-disclosure": rec("AI_DISCLOSURE_REQUIRED", PJ, [rep("/modules/spotify_hosted", "enabled"), rep("/ai_disclosure", None)], "Apple guideline 1.11 disclosure (IC-D6).", H2),
    "pj03-podcast-enabled-without-acknowledged-contact": rec("PUBLIC_CONTACT_REQUIRED", PJ, [rep("/modules/spotify_hosted", "enabled"), rep("/public_contact_acknowledged", False), rep("/ai_disclosure", {"text": "EXAMPLE ONLY: narrated with synthetic voices.", "spoken": True})], "Public contact must be acknowledged (IC-D6).", H2),
    "pj04-acknowledged-without-email": rec("PUBLIC_CONTACT_ACK_WITHOUT_EMAIL", PJ, [rep("/public_contact_email", None), rep("/public_contact_acknowledged", True)], "Acknowledgement needs an address.", H2),
    "pj05-zero-cost-without-inventory": rec("SERVICE_INVENTORY_REQUIRED", PJ, [rep("/profile_option", "zero_cost"), rep("/service_inventory", None)], "IC-E3.", H2),
    "pj06-v1-owner-email-field": rec("SCHEMA_VIOLATION", PJ, [add("/owner_email", "owner@example.invalid")], "owner_email replaced by public_contact_email (IC-D6).", H2),
    "pj07-primary-module-spec-only": rec("PRIMARY_MODULE_SPEC_ONLY", PJ, [rep("/website/primary", "plain_static")], "A primary site needs at least an implemented module.", H2),
    "si01-duplicate-service": rec("DUPLICATE_SERVICE", SI, [add("/services/-", {"capability": "podcast-host", "provider": "spotify-for-creators", "plan": "free", "state": "disabled"})], "(capability, provider) unique (E-05).", H2),
    "dp00-leading-dot-dirty-path-accepted": rec("VALID", H_LION, [add("/payload/source_repositories/0/worktree/dirty_paths/-", ".claude/settings.local.json")], "L-21: leading-dot dirty paths are recordable (positive patch case).", H2),
    "dp01-dirty-path-parent-segment": rec("UNSAFE_PATH", H_LION, [add("/payload/source_repositories/0/worktree/dirty_paths/-", "stories/../x")], "L-21: '..' still forbidden.", H2),
    "dp02-dirty-path-empty-segment": rec("UNSAFE_PATH", H_LION, [add("/payload/source_repositories/0/worktree/dirty_paths/-", "a//b")], "L-21: empty segments forbidden.", H2),
    "sp01-selection-source-purpose-accepted": rec("VALID", H_LION, [rep("/payload/source_files/0/purpose", "selection")], "L-23: source purpose selection (positive patch case).", H2),
    "hs01-missing-master-bad-slot": rec("SELECTION_SLOT_INVALID", SEL, [rep("/missing_masters/0/slot", "cover")], "L-23: missing_masters names a real slot.", H2),
    "hs02-filled-and-declared-missing": rec("SELECTION_MISSING_CONTRADICTION", SEL, [rep("/components/reading/cover_asset", "illus-s01-acorn-end")], "L-23: a slot cannot be filled and declared missing.", H2),
    "hs03-glob-path": rec("SCHEMA_VIOLATION", SEL, [rep("/assets/0/path", "character/characters/lion_and_mouse_v5/interactions/keyframes/*.png")], "L-23: no globs, name every file.", H2),
    "hs04-revision-purpose-mismatch": rec("PURPOSE_REVISION_MISMATCH", SEL, [rep("/handoff_revision", 2)], "L-23: revision 1 <=> initial <=> supersedes null.", H2),
    "hs05-canonicalization-not-allowed": rec("SCHEMA_VIOLATION", SEL, [add("/canonicalization", "bllt-canonical-json-v1")], "L-23: YAML selection is pinned by blob digest, not canonical JSON.", H2),
    "hs06-unknown-component-asset": rec("UNKNOWN_ASSET", SEL, [add("/components/reading/illustration_assets/-", "illus-missing")], "L-23: components reference selected assets.", H2),
    "si02-bad-state": rec("SCHEMA_VIOLATION", SI, [rep("/services/0/state", "trial")], "state is disabled/planned/enabled.", H2),
}

V2_PORT_CASES = {
    # Agent F adversarial cases F-V01..F-V09 (F-V08 is a raw-bytes case in negative/raw/)
    "fv01-three-websites-enabled": rec("MULTIPLE_WEBSITES", PJ, [rep("/modules/astro", "enabled"), rep("/modules/ghost", "enabled"), rep("/modules/plain_static", "enabled"), rep("/website/primary", "astro"), rep("/website/origin", "https://bllt.example.invalid")], "F-V01 (v2 I06).", V2),
    "fv02-two-feed-authorities": rec("MULTIPLE_FEED_AUTHORITIES", PJ, [rep("/modules/spotify_hosted", "enabled"), rep("/modules/independent_rss", "enabled")], "F-V02 (v2 I07).", V2),
    "fv03-enabled-feed-not-authority": rec("FEED_MODULE_NOT_ENABLED", PJ, [rep("/modules/independent_rss", "enabled")], "F-V03: authority spotify, only independent_rss enabled (adapted rule).", V2),
    "fv04-production-without-remote-writes": rec("PRODUCTION_WRITE_SWITCH_CONFLICT", PJ, [rep("/safety/production_enabled", True)], "F-V04.", V2),
    "fv05-rights-cleared-one-component": rec("INCOMPLETE_RIGHTS_CLEARANCE", RR, [rep("/example", False), rep("/status", "cleared"), rep("/checks", [{"component": "underlying-story", "decision": "cleared", "evidence": "x", "reviewed_by": "R", "reviewed_at": "2026-10-06T00:00:00Z"}])], "F-V05.", V2),
    "fv06-catalog-duplicate-story": rec("DUPLICATE_CATALOG_OR_EDITION", CAT, [add("/stories/-", {"story_id": "lion-and-mouse", "record_path": "publishing/stories/lion-and-mouse.yaml"})], "F-V06 (v2 I01).", V2),
    "fv07-native-audio-without-asset": rec("NATIVE_AUDIO_REFERENCE_MISSING", REL, [rep("/channels/website/player", "native_audio")], "F-V07.", V2),
    "fv09-registry-two-listed-show-pages": rec("DUPLICATE_PROVIDER_MAPPING", E + "provider-registry.v2.example.json", [add("/records/-", {"record_id": "reg-sp-show-2", "destination": "spotify", "entity_type": "show", "entity_id": "example-show-en", "url_kind": "show-page", "external_url": "https://open.example.invalid/show/x2", "external_id": None, "status": "listed", "observed_at": "2026-10-06T19:00:00Z", "receipt_id": None, "supersedes_record_id": None, "note": "EXAMPLE ONLY"})], "F-V09 / m3: one active listed row per (entity_type, entity_id, destination, url_kind).", V2),
    # remaining ported v2 rules, one fixture each
    "v2p01-primary-not-selected": rec("PRIMARY_NOT_SELECTED", PJ, [rep("/modules/plain_static", "enabled")], "Enabled website without website.primary.", V2),
    "v2p02-primary-module-not-enabled": rec("MODULE_NOT_ENABLED", PJ, [rep("/modules/astro", "implemented"), rep("/website/primary", "astro"), rep("/website/origin", "https://bllt.example.invalid")], "Primary must be enabled (v2: spec-only module cannot be selected).", V2),
    "v2p03-missing-origin": rec("MISSING_ORIGIN", PJ, [rep("/modules/plain_static", "enabled"), rep("/website/primary", "plain_static")], "Primary site needs an origin.", V2),
    "v2p04-feed-authority-not-selected": rec("FEED_AUTHORITY_NOT_SELECTED", PJ, [rep("/podcast_authority", "undecided"), rep("/modules/spotify_hosted", "enabled")], "Enabled feed module without an authority.", V2),
    "v2p05-zero-cost-commerce": rec("ZERO_PROFILE_FORBIDDEN_CAPABILITY", PJ, [rep("/profile_option", "zero_cost"), rep("/commerce", "enabled")], "Zero-cost profile refuses commerce.", V2),
    "v2p06-story-duplicate-edition": rec("DUPLICATE_CATALOG_OR_EDITION", STORY, [add("/editions/-", {"language": "en", "draft_path": "publishing/content/lion-and-mouse/en/draft2.yaml"})], "One edition per language.", V2),
    "v2p07-duplicate-rights-component": rec("DUPLICATE_RIGHTS_COMPONENT", RR, [add("/checks/-", {"component": "voices", "decision": "pending", "evidence": "x", "reviewed_by": None, "reviewed_at": None})], "One check per rights component.", V2),
    "v2p08-collection-duplicate-asset": rec("DUPLICATE_COLLECTION_ASSET", COLL, [rep("/assets", [V1_ASSET, V1_ASSET])], "Collection asset ids unique.", V2),
    "v2p09-collection-master-missing": rec("COLLECTION_MASTER_REFERENCE_MISSING", COLL, [rep("/master_asset_id", "absent-master")], "Master must be a collection asset.", V2),
    "v2p10-collection-order-invalid": rec("COLLECTION_ORDER_INVALID", COLL, [rep("/items", [dict(ITEM, order=2)])], "Order is 1..n.", V2),
    "v2p11-collection-duplicate-episode": rec("DUPLICATE_COLLECTION_EPISODE", COLL, [rep("/items", [ITEM, dict(ITEM, order=2)])], "One item per episode.", V2),
    "v2p12-spotify-player-without-episode": rec("SPOTIFY_EPISODE_REFERENCE_MISSING", REL, [rep("/channels/website/player", "spotify_embed")], "Spotify embed needs the episode reference.", V2),
    "v2p13-channel-unknown-asset": rec("UNKNOWN_ASSET", REL, [rep("/channels/podcast/audio_asset", "absent-audio")], "Channel assets resolve in the release.", V2),
    "v2p14-channel-wrong-role": rec("WRONG_ASSET_ROLE", REL, [rep("/channels/podcast/artwork_asset", "illus-s01-explores-start")], "Podcast artwork must be a podcast-cover asset.", V2),
    "v2p15-plan-expiry-order": rec("PLAN_EXPIRY_ORDER", PLAN_W, [rep("/expires_at", "2026-10-07T10:00:00Z")], "expires_at after created_at.", V2),
    "v2p16-duplicate-action": rec("DUPLICATE_ACTION", PLAN_P, [rep("/actions/1/action_id", "upload-episode")], "Action ids unique.", V2),
    "v2p17-empty-production-plan": rec("EMPTY_PRODUCTION_PLAN", PLAN_P, [rep("/actions", [])], "A production plan does something.", V2),
    "v2p18-duplicate-removal": rec("SCHEMA_VIOLATION", SS, [rep("/remove_paths", ["/en/stories/old/", "/en/stories/old/"])], "v2 DUPLICATE_REMOVAL: site-set.v2 enforces it in the schema (uniqueItems), so SCHEMA_VIOLATION fires first; the semantic check stays as defence in depth.", V2),
    "v2p19-unsafe-removal-path": rec("UNSAFE_REMOVAL_PATH", SS, [rep("/remove_paths", ["/en/stories/../x/"])], "No traversal in removals.", V2),
    "v2p20-url-with-credentials": rec("UNSAFE_URL", SHOW, [rep("/hosting/website_url", "https://user:secret@example.invalid/")], "URLs carry no credentials.", V2),
    "v2p21-wrong-embed-host": rec("WRONG_EMBED_HOST", WEB, [rep("/example", False), rep("/stories/0/listening/player", {"type": "spotify_embed", "embed_url": "https://evil.example.invalid/embed", "fallback_url": "https://open.spotify.com/show/x"}), rep("/stories/0/listening/duration_ms", 1000)], "Spotify embeds come from open.spotify.com (real records).", V2),
    "rc08-accepted-without-out-of-band-digest": rec("RECEIPT_DIGEST_SOURCE_REQUIRED", REC, [rep("/example", False), rep("/expected_archive_sha256", None), rep("/expected_digest_source", "not-provided")], "M1: an accepted real import needs an operator-supplied digest.", H2),
}
RAW_CASES = {
    "fv08-5000-digit-integer": {"fixture": "negative-raw", "expect": "CJ_INT_RANGE", "raw_text": '{"a":' + "9" * 5000 + "}",
                                "description": "F-V08 / m4: oversized integers report CJ_INT_RANGE (not CJ_SYNTAX)."},
}

IMPORT_CASES = {
    "m01-traversal-member": imp("ARCHIVE_UNSAFE_PATH", [{"op": "add_file", "name": "../evil.txt", "data": "x"}], "Member escaping the staging root."),
    "m02-absolute-member": imp("ARCHIVE_UNSAFE_PATH", [{"op": "add_file", "name": "/tmp/evil.txt", "data": "x"}], "Absolute member name."),
    "m03-symlink-member": imp("ARCHIVE_LINK_FORBIDDEN", [{"op": "add_symlink", "name": "files/reading-text-en/link", "target": "/etc/passwd"}], "Symlink member."),
    "m04-hardlink-member": imp("ARCHIVE_LINK_FORBIDDEN", [{"op": "add_hardlink", "name": "files/reading-text-en/hl", "target": "handoff.json"}], "Hard link member."),
    "m05-fifo-member": imp("ARCHIVE_SPECIAL_FILE", [{"op": "add_special", "name": "files/reading-text-en/pipe", "type": "fifo"}], "FIFO member."),
    "m06-device-member": imp("ARCHIVE_SPECIAL_FILE", [{"op": "add_special", "name": "files/reading-text-en/dev", "type": "chr"}], "Character device member."),
    "m07-gzip-archive": imp("ARCHIVE_FORMAT_UNSUPPORTED", [{"op": "compress", "with": "gzip"}], "Compressed archives refused."),
    "m08-not-a-tar": imp("ARCHIVE_MALFORMED", [{"op": "garbage", "bytes": 4096}], "Random bytes."),
    "m09-truncated-tar": imp("ARCHIVE_MALFORMED", [{"op": "truncate_mid_last_member"}], "Archive cut in the middle of a member (H2: offset computed, synthetic package is small)."),
    "m10-missing-bytes": imp("MISSING_BYTES", [{"op": "remove_file", "name": PNG1}], "Declared asset absent."),
    "m11-extra-file": imp("UNEXPECTED_FILE", [{"op": "add_file", "name": "files/reading-text-en/notes.txt", "data": "extra"}], "Undeclared file."),
    "m12-modified-bytes": imp("HASH_MISMATCH", [{"op": "replace_file", "name": TXT, "data": "{\"kind\":\"reading-blocks\",\"blocks\":[]}"}], "Bytes differ from digest."),
    "m13-too-many-members": imp("ARCHIVE_TOO_MANY_MEMBERS", [], "Member count above limit.", {"limits": {"max_members": 3}}),
    "m14-expansion-limit": imp("ARCHIVE_SIZE_LIMIT", [], "Declared sizes above the configured total.", {"limits": {"max_total_bytes": 5000}}),
    "m15-duplicate-member": imp("ARCHIVE_DUPLICATE_MEMBER", [{"op": "duplicate_member", "name": TXT}], "Same member twice."),
    "m16-case-collision": imp("ARCHIVE_CASE_COLLISION", [{"op": "add_file", "name": "files/reading-text-en/Reading-Text.json", "data": "x"}], "Case-insensitive collision."),
    "m17-script-disguised-as-png": imp("MEDIA_TYPE_MISMATCH", [{"op": "replace_asset_bytes", "asset_index": 1, "data": "#!/bin/sh\necho executed\n"}], "PNG whose bytes are a script."),
    "m18-handoff-json-missing": imp("HANDOFF_RECORD_MISSING", [{"op": "remove_file", "name": "handoff.json"}], "No handoff record."),
    "m19-out-of-band-digest-mismatch": imp("ARCHIVE_DIGEST_MISMATCH", [], "Operator digest differs.", {"expected_archive_sha256": SHA_X}),
    "m20-unsupported-version-in-package": imp("CONTRACT_VERSION_UNSUPPORTED", [{"op": "patch_handoff", "patch": [rep("/schema_version", 2)]}], "Producer newer than consumer."),
    "m21-measurement-mismatch": imp("MEASUREMENT_MISMATCH", [{"op": "patch_handoff", "patch": [rep("/payload/assets/1/measured/width_px", 1280)]}], "Width differs from PNG header."),
    "m22-example-into-production-state": imp("EXAMPLE_RECORD", [], "example:true cannot enter real state.", {"allow_example": False}),
    "m23-story-not-allocated": imp("STORY_NOT_ALLOCATED", [], "Story without allocation.", {"allocations": {}}),
    "m24-duplicate-json-key": imp("CJ_DUPLICATE_KEY", [{"op": "raw_handoff_suffix_dup"}], "Repeated key."),
    "m26-member-prefix-collision": imp("ARCHIVE_MEMBER_PREFIX_COLLISION", [{"op": "add_file", "name": "files/zz", "data": "x"}, {"op": "add_file", "name": "files/zz/y.txt", "data": "y"}], "F-I01 / m2: a regular member used as a directory."),
    "m27-no-expected-digest": imp("EXPECTED_DIGEST_REQUIRED", [], "F-I02 / M1: no out-of-band expected digest supplied.", {"no_expected_digest": True}),
    "m25-unsafe-name-backslash": imp("ARCHIVE_UNSAFE_PATH", [{"op": "add_file", "name": "files\\..\\evil", "data": "x"}], "Backslash path."),
}

SCENARIOS = {
    "sc01-reimport-identical": {"fixture": "import-scenario", "description": "Retry (also re-exported with a new created_at) = one logical handoff.",
                                "steps": [{"mutations": [], "expect_outcome": "accepted"}, {"mutations": [], "expect_outcome": "duplicate-identical"},
                                          {"mutations": [{"op": "patch_handoff", "patch": [rep("/envelope/created_at", "2026-10-06T20:00:00Z")]}], "expect_outcome": "duplicate-identical"}]},
    "sc02-revision-conflict": {"fixture": "import-scenario", "description": "Same handoff_id, different payload.",
                               "steps": [{"mutations": [], "expect_outcome": "accepted"},
                                         {"mutations": [{"op": "patch_handoff", "patch": [rep("/payload/editorial_selection/statement", "EXAMPLE ONLY: changed selection.")]}], "expect_outcome": "rejected", "expect": "HANDOFF_REVISION_CONFLICT"}]},
    "sc03-supersedes-unknown": {"fixture": "import-scenario", "description": "A correction supersedes an accepted handoff.",
                                "steps": [{"mutations": [{"op": "make_correction", "revision": 2, "parent_payload": SHA_X}], "expect_outcome": "rejected", "expect": "SUPERSEDES_UNKNOWN"}]},
    "sc04-correction-then-fork": {"fixture": "import-scenario", "description": "h0002 supersedes h0001; h0003 superseding h0001 is a fork.",
                                  "steps": [{"mutations": [], "expect_outcome": "accepted"},
                                            {"mutations": [{"op": "make_correction", "revision": 2, "parent_payload": "@step0"}], "expect_outcome": "accepted"},
                                            {"mutations": [{"op": "make_correction", "revision": 3, "parent_payload": "@step0"}], "expect_outcome": "rejected", "expect": "HANDOFF_FORK"}]},
    "sc05-interrupted-then-retry": {"fixture": "import-scenario", "description": "Crash after archival copy: one accepted receipt, one archive file in BLLT_MASTER_ROOT/handoffs/.",
                                    "steps": [{"mutations": [], "crash_after": "archive", "expect_outcome": "crash"}, {"mutations": [], "expect_outcome": "accepted"},
                                              {"mutations": [], "expect_outcome": "duplicate-identical"}],
                                    "expect_final": {"accepted_receipts": 1, "archive_files": 1}},
    "sc07-archive-store-corrupt": {"fixture": "import-scenario", "description": "M2: different bytes already sit at BLLT_MASTER_ROOT/handoffs/<sha256>.tar; the import is refused and nothing is overwritten.",
                                   "steps": [{"mutations": [], "options": {"preseed_corrupt_archive": True}, "expect_outcome": "rejected", "expect": "ARCHIVE_STORE_CORRUPT"}],
                                   "expect_final": {"accepted_receipts": 0, "archive_files": 1}},
    "sc08-corrupt-prior-receipt": {"fixture": "import-scenario", "description": "F-I04 / m2: an unreadable earlier receipt stops the import with IMPORT_STATE_CORRUPT and a new receipt.",
                                   "steps": [{"mutations": [], "options": {"preseed_corrupt_receipt": True}, "expect_outcome": "rejected", "expect": "IMPORT_STATE_CORRUPT"}],
                                   "expect_final": {"accepted_receipts": 0, "archive_files": 0}},
    "sc09-lock-held": {"fixture": "import-scenario", "description": "F-I03 / m2: a held import.lock refuses with IMPORT_LOCKED and still writes a receipt.",
                       "steps": [{"mutations": [], "options": {"preseed_lock": True}, "expect_outcome": "rejected", "expect": "IMPORT_LOCKED"}],
                       "expect_final": {"accepted_receipts": 0, "archive_files": 0}},
    "sc06-interrupted-during-staging": {"fixture": "import-scenario", "description": "Crash after staging: nothing promoted, stale staging swept.",
                                        "steps": [{"mutations": [], "crash_after": "staging", "expect_outcome": "crash"}, {"mutations": [], "expect_outcome": "accepted"}],
                                        "expect_final": {"accepted_receipts": 1, "archive_files": 1, "staging_left": 0}},
}


def main():
    for old in (FX / "v2-carried").glob("*.json"):
        old.unlink()
    for d in (EX, FX / "negative", FX / "scenarios", FX / "packages", FX / "podcast", FX / "ops", FX / "handoff-index"):
        if d.exists() and d != EX:
            shutil.rmtree(d)
    for old in EX.glob("*.json"):
        old.unlink()
    b = build_b_examples()
    write(EX / "package-src" / "reading-text.example.json", json.loads(READING_TEXT), check=False)
    (EX / "package-src" / "reading-text.example.json").write_bytes(READING_TEXT)
    write(EX / "story-allocation.lion-and-mouse.example.json", b["alloc_lion"])
    write(EX / "story-allocation.fixture-second-story.example.json", b["alloc_fix"])
    write(EX / "production-handoff.lion-and-mouse.example.json", b["lion"])
    write(EX / "production-handoff.fixture-second-story.example.json", b["fix"])
    write(EX / "release.v2.lion-and-mouse.draft.example.json", b["release"])
    write(EX / "approval.v2.rejected.example.json", b["approval"])
    write(EX / "approval.v2.podcast-audio-rights-review.example.json", b["approval_audio"])
    write(EX / "import-receipt.accepted.example.json", b["import_receipt"])
    manifests = build_web(b)
    m1 = manifests["site-set-0001"]
    pub = copy.deepcopy(m1)
    pub["bundle_id"] = "example-web-site-artifact-0001"
    pub["inputs"]["renderer"] = {"name": "plain_static", "version": "0.0.0-spec-only"}
    pub["files"] = [{"path": "en/stories/the-lion-and-the-mouse/index.html", "sha256": synth("index.html"), "bytes": 4000,
                     "media_type": "text/html", "source": None}] + [f for f in m1["files"] if f["path"].startswith("media/")]
    write(EX / "public-bundle-manifest.web.example.json", pub)
    h2 = build_h2(b, manifests)
    names = {"service_inventory": "service-inventory.v1.example.json", "project": "project.v2.example.json",
             "site_set": "site-set.v2.example.json", "plan_web": "publish-plan.v2.website-preview.example.json",
             "plan_podcast": "publish-plan.v2.podcast-spotify.example.json",
             "receipt_pending": "publish-receipt.v2.manual-pending.example.json",
             "receipt_conflict": "publish-receipt.v2.ghost-conflict.example.json",
             "media_delivery": "media-delivery.v2.example.json"}
    for k, n in names.items():
        write(EX / n, h2[k])
    # handoff-selection.v1 (L-23): G3's example YAML, vendored unchanged in tests/fixtures/compat/
    from bllt_publish.contracts.yaml_strict import load_yaml
    sel = load_yaml((FX / "compat" / "g3-handoff_selection.example.yaml").read_text(encoding="utf-8"))
    write(EX / "handoff-selection.v1.lion-and-mouse.example.json", sel)
    # podcast examples (Agent D)
    write(EX / "episode-publication.v2.spotify-prepared.example.json", PF.ep())
    write(EX / "episode-publication.v2.spotify-published.example.json", PF.ep(**PF.PUBLISHED))
    write(EX / "provider-registry.v2.example.json", PF.REG_OK)
    obs = P.observe_feed((FX / "feeds" / "f01_initial.xml").read_bytes(), show_id="example-show-en",
                         feed_url="https://feeds.example.invalid/x.xml", fetched_at="2026-10-06T19:00:00Z",
                         observation_id="obs-20261006T190000Z-00000000", example=True)
    write(EX / "feed-observation.v1.example.json", obs)
    # contract lock over the H2 schemas actually shipped
    schema_dir = ROOT / "publishing" / "contracts" / "schemas"
    lock = {**record_head("contract-lock", 1),
            "package": {"name": "bllt-contracts", "version": CONTRACT_PKG["version"], "archive_sha256": CONTRACT_PKG["archive_sha256"],
                        "source_repository": "jeilealr/bllt-publishing", "source_commit": None, "released_at": "2026-10-07T00:00:00Z"},
            "files": [{"path": f"schemas/{p.name}", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(schema_dir.glob("*.schema.json"))],
            "producer_emits": {"production-handoff": 1}}
    write(EX / "contract-lock.example.json", lock)
    # ---- fixtures
    # v2 kinds carried forward: vendored v2 examples (tests/fixtures/v2-carried/source/, SOURCES.sha256) as JSON
    from bllt_publish.contracts.yaml_strict import load_yaml
    for k in ("catalog", "story", "show", "collection", "rights-review"):
        src = FX / "v2-carried" / "source" / f"{k}.example.yaml"
        write(FX / "v2-carried" / f"{k}.example.json", load_yaml(src.read_text(encoding="utf-8")))
    for name, case in {**B_RECORD_CASES, **H2_RECORD_CASES, **V2_PORT_CASES}.items():
        write(FX / "negative" / "records" / f"{name}.json", case, check=False)
    for name, case in RAW_CASES.items():
        write(FX / "negative" / "raw" / f"{name}.json", case, check=False)
    for name, case in IMPORT_CASES.items():
        write(FX / "negative" / "imports" / f"{name}.json", case, check=False)
    for name, case in SCENARIOS.items():
        write(FX / "scenarios" / f"{name}.json", case, check=False)
    pkg = FX / "packages" / "lion-h0001-synthetic"
    write(pkg / "handoff.json", b["lion_synthetic"])
    (pkg / "files" / "reading-text-en").mkdir(parents=True)
    (pkg / "files" / "reading-text-en" / "reading-text.json").write_bytes(READING_TEXT)
    sources = []
    for k in KEYFRAMES:
        a = asset_from_keyframe(k, synthetic=True)
        data = png(k[4], k[5], k[6])
        (pkg / a["package_path"]).parent.mkdir(parents=True)
        (pkg / a["package_path"]).write_bytes(data)
        sources.append({"package_path": a["package_path"], "synthetic_sha256": a["sha256"], "synthetic_bytes": a["bytes"],
                        "stands_in_for": f"b880c23:{KF}{k[1]}", "source_sha256": k[2], "source_bytes": k[3],
                        "source_dimensions": [k[4], k[5]], "evidence": "REPO, measured by Agent B with git show (read-only)"})
    write(FX / "packages" / "SOURCES.json", {"note": "Synthetic PNGs replace production bytes (Agent B IC 8). "
                                                     "Same file names and dimensions; different bytes and digests.",
                                             "files": sources}, check=False)
    write(FX / "packages" / "story-allocation.lion-and-mouse.json", b["alloc_lion"])
    for name, (rec_, codes_) in PF.NEGATIVE.items():
        write(FX / "podcast" / "negative" / f"{name}.json", {"expected": codes_, "record": rec_}, check=False)
    for name, (prev, new, codes_) in PF.SUCCESSION.items():
        write(FX / "podcast" / "negative" / f"{name}.json", {"expected": codes_, "previous": PF.ep(**prev), "new": PF.ep(**new)}, check=False)
    # ops (Agent E) with owner storage decision; project fixture converted to project.v2
    inv = {**record_head("service-inventory", 1), "profile": "strict-zero", "services": [
        {"capability": "website-static-host", "provider": "cloudflare-pages", "plan": "free", "state": "enabled",
         "billing": {"payment_method_on_file": None, "auto_recharge": False},
         "evidence": {"checked_at": "2026-10-06", "source": "https://developers.cloudflare.com/pages/functions/pricing/"}},
        {"capability": "podcast-host", "provider": "spotify-for-creators", "plan": "free", "state": "enabled",
         "billing": {"auto_recharge": False}, "evidence": {"checked_at": "2026-10-06", "source": "Agent D register D-00 (Spotify for Creators, free hosting)"}},
        {"capability": "source-hosting", "provider": "github", "plan": "free", "state": "enabled",
         "billing": {"payment_method_on_file": False},
         "evidence": {"checked_at": "2026-10-06", "source": "https://docs.github.com/en/get-started/learning-about-github/githubs-plans"}},
        {"capability": "ci-hosted-runner", "provider": "github-actions", "plan": "standard", "state": "planned",
         "billing": {"payment_method_on_file": False, "overage_allowed": False},
         "evidence": {"checked_at": "2026-10-06", "source": "https://docs.github.com/en/billing/concepts/product-billing/github-actions"}},
        {"capability": "backup-cloud-storage", "provider": "onedrive", "plan": "microsoft-365-personal", "state": "enabled",
         "billing": {"auto_recharge": None}, "evidence": {"checked_at": "2026-10-07", "source": "Owner statement 2026-10-07: Microsoft 365 Personal, 1 TB plan, 187 GB used."}},
        {"capability": "backup-local-disk", "provider": "owner-external-hdd", "plan": "owned-1tb", "state": "enabled",
         "billing": {}, "evidence": {"checked_at": "2026-10-07", "source": "Owner statement 2026-10-07: 1 TB external drive."}},
        {"capability": "newsletter", "provider": "none", "plan": "none", "state": "disabled"}]}
    write(FX / "ops" / "service-inventory.strict-zero.example.json", inv)
    proj = {**h2["project"], "profile_option": "zero_cost",
            "website": {"primary": "plain_static", "origin": "https://bllt-example.pages.dev", "locale_prefixes": True},
            "modules": {"astro": "spec_only", "ghost": "spec_only", "plain_static": "enabled", "spotify_hosted": "enabled",
                        "independent_rss": "spec_only", "youtube": "spec_only"},
            "ai_disclosure": {"text": AI_SHOW_TEXT, "spoken": True},
            "public_contact_acknowledged": True,
            "service_inventory": {"path": "tests/fixtures/ops/service-inventory.strict-zero.example.json", "sha256": cj1.digest(inv)}}
    write(FX / "ops" / "project.zero_cost.example.json", proj)
    write(FX / "ops" / "scan-policy.example.json", {
        "allowed_url_hosts": ["open.spotify.com", "creators.spotify.com", "www.youtube-nocookie.com", "www.youtube.com", "bllt-example.pages.dev"],
        "allowed_emails": ["jei.leal.r@gmail.com"], "deny_terms": [], "allow_placeholders": False, "test_mode": True,
        "allowed_id3_frames": ["TIT2", "TPE1", "TALB", "TRCK", "TDRC", "TCON", "APIC", "TLEN", "TCOP"]}, check=False)
    lion_index = {"handoff_id": "lion-and-mouse.en.h0001", "story_id": "lion-and-mouse", "language": "en",
                  "payload_sha256": b["lion_pin"]["payload_sha256"], "archive_sha256": b["lion_pin"]["archive_sha256"],
                  "contract_version": CONTRACT_PKG["version"], "receipt_id": "imp-20261006T180500Z-0a1b2c3d", "example": True}
    write(FX / "handoff-index" / "clean" / "lion-and-mouse" / "en" / "lion-and-mouse.en.h0001.json", lion_index, check=False)
    write(FX / "handoff-index" / "leaky" / "lion-and-mouse" / "en" / "lion-and-mouse.en.h0001.json",
          {**lion_index, "rights_evidence": [{"component": "voices", "evidence": {"ref": "x", "sha256": None}}],
           "operator": "EXAMPLE-OPERATOR"}, check=False)
    (FX / "handoff-index" / "leaky" / "lion-and-mouse" / "en" / "lion-and-mouse.en.h0001.tar").write_bytes(b"\0" * 512)
    print("examples:", len(list(EX.glob("*.json"))), "+ web bundles; record negatives:",
          len(B_RECORD_CASES) + len(H2_RECORD_CASES) + len(V2_PORT_CASES),
          f"({len(H2_RECORD_CASES)} H2, {len(V2_PORT_CASES)} v2-port/F); raw: {len(RAW_CASES)}; imports:", len(IMPORT_CASES),
          "scenarios:", len(SCENARIOS), "podcast negatives:", len(PF.NEGATIVE) + len(PF.SUCCESSION))


if __name__ == "__main__":
    main()
