#!/usr/bin/env python3
"""Write publishing/contracts/error-codes.json: the one merged error catalogue of contract revision H2
(DECISIONS_H2 s.4, IC-C5): Agent B's codes, C's WB_/RI_/SC_/SA_/ZC_ codes, D's podcast codes, E's codes,
STATE_ROOT_*, the lead's H2 codes and, for reference, the production exporter's codes (Agent G3).

Status per family: implemented = emitted by code in this scaffold (or G3's exporter) and exercised by
tests where the test map says so; proposed = specified in documents only (no code emits it yet).
`feltwillow_publish.check` fails when any code observed in a test result is missing here.
Usage: python tools/build_error_codes.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

W = lambda s: s.split()  # noqa: E731

FAMILIES = [
    ("canonical-domain", "B", "feltwillow_publish.contracts.cj1; tools/js/cj1.mjs", "implemented",
     "Input outside the canonical-json-v1 safe domain (feltwillow-canonical-json-v1).",
     W("CJ_INVALID_UTF8 CJ_BOM CJ_SYNTAX CJ_DUPLICATE_KEY CJ_KEY_NOT_ASCII CJ_FLOAT CJ_INT_RANGE CJ_LONE_SURROGATE "
       "CJ_UNASSIGNED_CODEPOINT CJ_NOT_NFC CJ_DEPTH")),
    ("negotiation-structure", "B", "feltwillow_publish.contracts.validate", "implemented",
     "Record kind/version negotiation, path pre-pass and JSON Schema validation.",
     W("UNKNOWN_RECORD_KIND CONTRACT_VERSION_UNSUPPORTED SCHEMA_VIOLATION UNSAFE_PATH REMOTE_REFERENCE_FORBIDDEN")),
    ("handoff-semantics", "B", "feltwillow_publish.contracts.validate.sem_handoff", "implemented",
     "production-handoff.v1 cross-field rules.",
     W("HANDOFF_ID_MISMATCH SUPERSEDES_REQUIRED SUPERSEDES_UNEXPECTED SUPERSEDES_OTHER_EDITION SUPERSEDES_NOT_EARLIER "
       "PURPOSE_REVISION_MISMATCH REASON_REQUIRED DUPLICATE_ASSET_ID DUPLICATE_PACKAGE_PATH MEDIA_TYPE_ROLE_MISMATCH "
       "MISSING_MEASUREMENT REFERENCED_MEDIA_NOT_SUPPORTED PACKAGE_PATH_MISSING PACKAGE_PATH_MISMATCH "
       "ORIGIN_COMMIT_INCONSISTENT DERIVATION_CYCLE UNKNOWN_PARENT_ASSET PARENT_HASH_MISMATCH REVOCATION_WITH_ASSETS "
       "NO_COMPONENTS UNKNOWN_ASSET WRONG_ASSET_ROLE UNREFERENCED_ASSET WORKTREE_STATE_INCONSISTENT "
       "SOURCE_COMMIT_MISMATCH SELECTED_SOURCE_DIRTY EXPORTER_DIRTY DUPLICATE_SOURCE_ID TIMESTAMP_ORDER")),
    ("release-approval-receipt-manifest-lock", "B", "feltwillow_publish.contracts.validate", "implemented",
     "release.v2, approval.v2, import-receipt.v1, public-bundle-manifest.v1, contract-lock.v1 rules.",
     W("RELEASE_ID_MISMATCH AGE_RANGE_REVERSED SUPERSEDES_INCONSISTENT ORIGIN_INCOMPLETE UNLISTED_HANDOFF "
       "DERIVATIVE_WITHOUT_PARENT MISSING_IMAGE_DIMENSIONS MISSING_MEDIA_DURATION FROZEN_WITHOUT_HANDOFF "
       "FROZEN_WITHOUT_TOOLING_PROVENANCE DRAFT_WITH_FREEZE_PROVENANCE BACKPORT_REFERENCE_MISSING STAGE_SUBJECT_MISMATCH "
       "DUPLICATE_APPROVAL_CHECK INVALID_POSITIVE_APPROVAL REVOCATION_TARGET_UNEXPECTED REVOCATION_TARGET_MISSING "
       "APPROVAL_CHAIN_MISSING APPROVAL_SELF_DEPENDENCY RECEIPT_OUTCOME_INCONSISTENT DIGEST_SOURCE_INCONSISTENT "
       "ARCHIVAL_LOCATOR_MISMATCH DUPLICATE_PUBLIC_PATH PUBLIC_FORBIDDEN_FILE WEB_BUNDLE_WITHOUT_SITE_SET "
       "DUPLICATE_LOCK_PATH LOCK_MISSING_EMITTED_SCHEMA")),
    ("import-protocol", "B (H2 storage layout: lead)", "feltwillow_publish.imports.importer", "implemented",
     "Reference import of a handoff tar; any code here means nothing was promoted.",
     W("IMPORT_LOCKED ARCHIVE_DIGEST_MISMATCH ARCHIVE_FORMAT_UNSUPPORTED ARCHIVE_MALFORMED ARCHIVE_UNSAFE_PATH "
       "ARCHIVE_LINK_FORBIDDEN ARCHIVE_SPECIAL_FILE ARCHIVE_DUPLICATE_MEMBER ARCHIVE_CASE_COLLISION "
       "ARCHIVE_TOO_MANY_MEMBERS ARCHIVE_SIZE_LIMIT HANDOFF_RECORD_MISSING EXAMPLE_RECORD STORY_NOT_ALLOCATED "
       "MISSING_BYTES UNEXPECTED_FILE SIZE_MISMATCH HASH_MISMATCH MEDIA_TYPE_MISMATCH MEASUREMENT_MISMATCH "
       "HANDOFF_REVISION_CONFLICT SUPERSEDES_UNKNOWN HANDOFF_FORK ARCHIVE_STORE_CORRUPT ARCHIVE_OUTSIDE_INBOX "
       "EXPECTED_DIGEST_REQUIRED ARCHIVE_MEMBER_PREFIX_COLLISION IMPORT_STATE_CORRUPT IMPORT_IO_ERROR")),
    ("storage-roots", "lead (IC-A4, IC-E1)", "feltwillow_publish.ops.state_roots", "implemented",
     "FELTWILLOW_HANDOFF_INBOX / FELTWILLOW_MASTER_ROOT / FELTWILLOW_PUBLISH_STATE_ROOT missing, or relative / inside Git / inside "
     "OneDrive / on LUMI shared storage.", W("STATE_ROOT_UNSET STATE_ROOT_UNSAFE")),
    ("h2-records", "lead (DECISIONS_H2 s.3)", "feltwillow_publish.contracts.validate", "implemented",
     "publish-plan.v2, publish-receipt.v2, media-delivery.v2, site-set.v2, project.v2, service-inventory.v1, "
     "approval scope rights_review.podcast_audio and handoff-selection.v1 rules.",
     W("CONTRACT_VERSION_PIN_MISMATCH DUPLICATE_HANDOFF_PIN DUPLICATE_RELEASE_PIN RECEIPT_DIGEST_SOURCE_REQUIRED "
       "ACTION_DESTINATION_MISMATCH ARTIFACT_REQUIRED ARTIFACT_UNEXPECTED "
       "WEBSITE_PLAN_TOUCHES_PODCAST GHOST_INPUT_WITHOUT_GHOST_ACTION LEAK_SCAN_REPORT_REQUIRED "
       "STRICT_ZERO_REPORT_REQUIRED WEB_PLAN_WITHOUT_SITE_SET CONFLICT_INCONSISTENT RECEIPT_EVIDENCE_REQUIRED "
       "MANUAL_PENDING_WITH_OUTCOME OBSERVATION_ID_REQUIRED SUBMITTED_SHA256_REQUIRED DUPLICATE_DELIVERY_URL "
       "SITE_SET_EMPTY PUBLIC_CONTACT_ACK_WITHOUT_EMAIL PUBLIC_CONTACT_REQUIRED "
       "AI_DISCLOSURE_REQUIRED SERVICE_INVENTORY_REQUIRED PRIMARY_MODULE_SPEC_ONLY DUPLICATE_SERVICE "
       "RIGHTS_REVIEW_EVIDENCE_MISSING SELECTION_SLOT_INVALID SELECTION_MISSING_CONTRADICTION")),
    ("v2-semantics-ported", "v2 checker (ported to H2 by G1 after Agent F's B1)", "feltwillow_publish.contracts.validate "
     "(+ podcast/web semantics)", "implemented",
     "v2 validate_blueprint.py semantic rules, kept with their v2 codes and adapted to H2 fields "
     "(see DEPRECATED_V2_RULES.md for adapted and retired rules).",
     W("MULTIPLE_WEBSITES PRIMARY_NOT_SELECTED MODULE_NOT_ENABLED MISSING_ORIGIN MULTIPLE_FEED_AUTHORITIES "
       "FEED_MODULE_NOT_ENABLED FEED_AUTHORITY_NOT_SELECTED ZERO_PROFILE_FORBIDDEN_CAPABILITY "
       "PRODUCTION_WRITE_SWITCH_CONFLICT DUPLICATE_CATALOG_OR_EDITION DUPLICATE_RIGHTS_COMPONENT "
       "INCOMPLETE_RIGHTS_CLEARANCE DUPLICATE_COLLECTION_ASSET COLLECTION_MASTER_REFERENCE_MISSING "
       "COLLECTION_ORDER_INVALID DUPLICATE_COLLECTION_EPISODE NATIVE_AUDIO_REFERENCE_MISSING "
       "SPOTIFY_EPISODE_REFERENCE_MISSING DUPLICATE_PROVIDER_MAPPING DUPLICATE_SITE_EDITION DUPLICATE_REMOVAL "
       "UNSAFE_REMOVAL_PATH PLAN_EXPIRY_ORDER DUPLICATE_ACTION UNSUPPORTED_OPERATION EMPTY_PRODUCTION_PLAN "
       "UNSAFE_URL WRONG_EMBED_HOST")),
    ("declarative-readiness", "v2 checker (ported)", "feltwillow_publish.contracts.validate.readiness_errors", "implemented",
     "Declaration-only readiness of a release.v2 for one channel; an empty result is NOT permission to publish.",
     W("NOT_A_RELEASE EXAMPLE_RECORD RELEASE_NOT_FROZEN RIGHTS_NOT_CLEARED RIGHTS_RECORD_HASH_MISSING "
       "SOURCE_HASH_MISSING CHANNEL_NOT_REQUESTED MISSING_ASSET UNAPPROVED_ASSET PODCAST_ID_MISSING "
       "PODCAST_COVER_DIMENSIONS")),
    ("v2-planned", "v2 ch15 / G2", "docs only", "planned",
     "Named in the v2/v3 chapters for planned components (release freezer, plan/apply, reconcile, retention, "
     "CLI guard); no code emits them yet.",
     W("MODULE_NOT_IMPLEMENTED APPROVAL_MISMATCH SOURCE_CHANGED DUPLICATE_EPISODE REGISTRY_CONFLICT "
       "UNKNOWN_REMOTE_RESULT SITE_REMOVAL_NOT_APPROVED RETENTION_REFERENCED_ASSET PRODUCTION_CREDENTIAL_PRESENT")),
    ("reading-edition", "lead (L-28, owner OD-14)", "feltwillow_publish.contracts.validate", "implemented",
     "Reading text is authored in publishing as reading-edition.v1; releases with a website channel pin one.",
     W("READING_EDITION_MISSING READING_EDITION_MISMATCH READING_EDITION_ID_MISMATCH READING_EDITION_WITHOUT_TEXT "
       "READING_SOURCE_OTHER_EDITION")),
    ("handoff-measurement", "lead (L-29, owner OD-24)", "feltwillow_publish.contracts.validate.sem_handoff", "implemented",
     "Per-asset measurement provenance; lossless audio only; video measured with ffprobe.",
     W("MEASUREMENT_PROVENANCE_MISSING VIDEO_MEASUREMENT_REQUIRES_FFPROBE HANDOFF_AUDIO_NOT_LOSSLESS")),
    ("web-payload", "C", "feltwillow_publish.web.contract", "implemented", "web-bundle.v2 payload rules.",
     W("WB_SCHEMA WB_CANONICAL_DOMAIN WB_LANGUAGE_DUPLICATE WB_LANGUAGE_PATH_MISMATCH WB_DEFAULT_LANGUAGE_UNKNOWN "
       "WB_ROUTE_DUPLICATE WB_STORY_LANGUAGE_DUPLICATE WB_PAGE_LANGUAGE_UNKNOWN WB_PAGE_PATH_LANGUAGE_MISMATCH "
       "WB_MEDIA_UNRESOLVED WB_STORY_LANGUAGE_UNKNOWN WB_STORY_PATH_LANGUAGE_MISMATCH WB_RELEASE_MISMATCH WB_AGE_RANGE "
       "WB_IMAGE_DIMENSIONS_MISSING WB_DURATION_MISMATCH WB_DURATION_REQUIRED WB_DIVERGENCE_INCONSISTENT "
       "WB_TRANSCRIPT_REQUIRED WB_TIMESTAMP_ORDER WB_MEDIA_PATH_NOT_CONTENT_ADDRESSED WB_MEDIA_SOURCE_MISMATCH "
       "WB_MEDIA_UNUSED WB_REDIRECT_DUPLICATE WB_REDIRECT_SHADOWS_ROUTE WB_REDIRECT_TARGET_MISSING")),
    ("web-render-input", "C", "feltwillow_publish.web.contract", "implemented",
     "Render-input bundle vs manifest and bytes; RI_<code> also wraps any validator code of the manifest.",
     W("RI_NOT_WEB_BUNDLE RI_RENDERER_MUST_BE_NULL RI_PAYLOAD_MISSING RI_TREE_SYMLINK RI_TREE_SPECIAL_FILE "
       "RI_UNLISTED_FILE RI_MISSING_FILE RI_FILE_DIGEST_MISMATCH RI_MEDIA_TYPE_MISMATCH RI_PAYLOAD_PARSE "
       "RI_PAYLOAD_NOT_CANONICAL RI_PUBLIC_RECORD_DIGEST_MISMATCH RI_SITE_SET_MISMATCH RI_RELEASES_MISMATCH "
       "RI_FILE_NOT_IN_PAYLOAD RI_PAYLOAD_MANIFEST_DISAGREE RI_PAYLOAD_MEDIA_NOT_LISTED")),
    ("web-completeness", "C", "feltwillow_publish.web.contract", "implemented", "A later site-set keeps earlier stories.",
     W("SC_STORY_DROPPED SC_PATH_CHANGED_WITHOUT_REDIRECT SC_REDIRECT_DROPPED SC_LANGUAGE_DROPPED")),
    ("web-site-artifact", "C", "feltwillow_publish.web.contract", "implemented",
     "Renderer output tree vs its input (tested on a synthetic tree only); SA_<code> wraps validator codes.",
     W("SA_RENDERER_REQUIRED SA_INPUTS_DIFFER_FROM_RENDER_INPUT SA_TREE_SYMLINK SA_TREE_SPECIAL_FILE "
       "SA_MANIFEST_TREE_DIFFER SA_FILE_DIGEST_MISMATCH SA_UNEXPECTED_FILE SA_404_MISSING SA_MEDIA_NOT_FROM_INPUT "
       "SA_INPUT_MEDIA_NOT_SHIPPED SA_ROUTE_MISSING SA_LOCAL_PATH_OR_SECRET_PATTERN SA_AUTOPLAY SA_IMG_WITHOUT_ALT "
       "SA_REMOTE_SCRIPT SA_EAGER_IFRAME SA_HTML_LANG_MISMATCH SA_LANDMARK_MISSING SA_ILLUSTRATION_ORDER")),
    ("web-proposed", "C", "docs (C-03, C-05)", "proposed",
     "Zero-cost preflight and Ghost adapter codes; no code emits them yet.",
     W("ZC_CUSTOM_ORIGIN_UNAPPROVED ZC_FILE_LIMIT ZC_HOST_UNAPPROVED ZC_METERED_SERVICE ZC_REMOTE_PREVIEW "
       "ZC_RENDERER_NOT_STATIC ZC_SERVER_CODE WEB_ORIGIN_REQUIRED_FOR_DEPLOY WB_GHOST_SLUG_COLLISION "
       "GHOST_REMOTE_EDIT_CONFLICT GHOST_MAPPED_POST_MISSING GHOST_THEME_DRIFT")),
    ("podcast-records", "D", "feltwillow_publish.podcast.podcast", "implemented",
     "episode-publication.v2 / provider-registry.v2 / feed-observation.v1 semantics and identity succession.",
     W("PLACEHOLDER_URL_IN_REAL_RECORD REAL_LOOKING_URL_IN_EXAMPLE EPISODE_RELEASE_MISMATCH "
       "EPISODE_CHANGE_STATE_MISMATCH SPOTIFY_GUID_BEFORE_OBSERVATION PUBLISHED_EPISODE_INCOMPLETE "
       "GUID_SOURCE_AUTHORITY_MISMATCH EPISODE_SUPERSEDES_INCONSISTENT PUBDATE_RAW_UTC_MISMATCH DUPLICATE_RECORD_ID "
       "URL_KIND_REQUIRED URL_KIND_ENTITY_MISMATCH URL_KIND_DESTINATION_MISMATCH LISTED_WITHOUT_URL URL_KIND_CONFLICT "
       "SUPERSEDES_UNKNOWN_RECORD ITEM_COUNT_MISMATCH EPISODE_IDENTITY_CHANGED AUDIO_REPLACEMENT_WITHOUT_NEW_AUDIO "
       "MIGRATION_GUID_NOT_RETAINED")),
    ("podcast-feed", "D", "feltwillow_publish.podcast.podcast", "implemented",
     "Safe feed parsing (refusals), observation problems, change events and reconcile findings.",
     W("FEED_TOO_LARGE FEED_DTD_FORBIDDEN FEED_ENCODING_UNSUPPORTED FEED_INVALID_UTF8 FEED_XML_MALFORMED FEED_NOT_RSS "
       "ITEM_WITHOUT_GUID DUPLICATE_GUID ITEM_WITHOUT_ENCLOSURE DUPLICATE_ENCLOSURE_URL ENCLOSURE_LENGTH_INVALID "
       "ENCLOSURE_TYPE_MISSING ENCLOSURE_NOT_HTTPS ITEM_WITHOUT_PUBDATE PUBDATE_UNPARSEABLE FEED_EMAIL_ABSENT "
       "CHANNEL_TITLE_MISSING CHANNEL_DESCRIPTION_MISSING CHANNEL_LANGUAGE_MISSING CHANNEL_EXPLICIT_MISSING "
       "CHANNEL_CATEGORY_MISSING CHANNEL_ARTWORK_MISSING ITEM_REMOVED ITEM_ADDED SUSPECTED_GUID_REWRITE "
       "PUBDATE_CHANGED PERMALINK_FLAG_CHANGED TITLE_CHANGED ENCLOSURE_URL_CHANGED ENCLOSURE_LENGTH_CHANGED "
       "NEW_FEED_URL_ANNOUNCED FEED_BLOCKED FEED_EMAIL_REMOVED EPISODE_MISSING_FROM_FEED FIRST_PUBLISHED_AT_DRIFT "
       "PERMALINK_FLAG_DRIFT ENCLOSURE_CHANGED_SINCE_RECORD")),
    ("podcast-probe", "D", "feltwillow_publish.podcast.podcast.probe_media", "implemented",
     "HEAD + byte-range probe findings (tests use a local 127.0.0.1 server only).",
     W("REDIRECT_TO_UNAPPROVED_HOST UNREACHABLE TOO_MANY_REDIRECTS CONTENT_TYPE_MISMATCH CONTENT_LENGTH_MISMATCH "
       "RANGE_NOT_SUPPORTED RANGE_TOTAL_MISMATCH RANGE_BODY_LENGTH_MISMATCH")),
    ("leak-scan", "E", "feltwillow_publish.ops.leak_scan", "implemented",
     "Content-level scan of the exact upload directory (heuristic; clean = no listed pattern matched).",
     W("BUNDLE_MANIFEST_INVALID BUNDLE_UNDECLARED_FILE BUNDLE_MISSING_FILE BUNDLE_SIZE_MISMATCH BUNDLE_HASH_MISMATCH "
       "PUBLIC_LINK_FORBIDDEN PUBLIC_SPECIAL_FILE PUBLIC_EXECUTABLE_MODE PUBLIC_NONASCII_PATH "
       "PUBLIC_FILE_TOO_LARGE_TO_SCAN PUBLIC_EXECUTABLE_CONTENT PUBLIC_SECRET_PATTERN PUBLIC_MACHINE_PATH "
       "PUBLIC_PRODUCTION_PATH PUBLIC_PRIVATE_FIELD PUBLIC_PLACEHOLDER PUBLIC_EMAIL_NOT_ALLOWLISTED "
       "PUBLIC_URL_UNPARSEABLE PUBLIC_URL_CREDENTIALS PUBLIC_SIGNED_URL PUBLIC_PRIVATE_ADDRESS PUBLIC_URL_NOT_HTTPS "
       "PUBLIC_URL_HOST_NOT_ALLOWED PUBLIC_MEDIA_METADATA PUBLIC_DENYLIST_TERM PUBLIC_TEXT_NOT_UTF8 PUBLIC_JSON_INVALID")),
    ("handoff-index-scan", "E (IC-E4)", "feltwillow_publish.ops.handoff_index_scan", "implemented",
     "Untrusted-CI scan of publishing/handoffs/**.",
     W("HANDOFF_INDEX_FORBIDDEN_FILE HANDOFF_INDEX_PRIVATE_FIELD HANDOFF_INDEX_SECRET HANDOFF_INDEX_MACHINE_PATH "
       "HANDOFF_INDEX_EMAIL")),
    ("strict-zero", "E", "feltwillow_publish.ops.strict_zero", "implemented",
     "Fail-closed declaration check of project + service-inventory (OWNER_INFRA_COST_DECLARED is informational).",
     W("SERVICE_INVENTORY_INVALID PROJECT_INVALID PROFILE_MISMATCH DUPLICATE_SERVICE SERVICE_STATE_INVALID "
       "PUBLISHING_HOLDS_PRODUCTION_CAPABILITY UNKNOWN_CAPABILITY_OR_PROVIDER COST_EVIDENCE_MISSING COST_EVIDENCE_STALE "
       "OWNER_INFRA_COST_DECLARED ZERO_PROFILE_FORBIDDEN_CAPABILITY ZERO_PROFILE_OVERAGE_ENABLED "
       "ZERO_PROFILE_HARD_LIMIT_NOT_PROVEN ZERO_PROFILE_ORIGIN_NOT_PROVIDER_SUBDOMAIN ZERO_PROFILE_HOST_UNDECLARED "
       "ZERO_PROFILE_MULTIPLE_HOSTS ZERO_PROFILE_PODCAST_HOST_UNDECLARED")),
    ("ci-lint", "E", "feltwillow_publish.ops.ci_lint", "implemented",
     "Workflow rules CI-R1..CI-R13 (codes keep E's hyphenated CI-Rn prefix).",
     W("CI_YAML_INVALID CI-R1_FORBIDDEN_TRIGGER CI-R2_DEPLOY_NOT_MANUAL_ONLY CI-R2_DEPLOY_WITHOUT_PLAN_DIGEST "
       "CI-R3_TOP_LEVEL_PERMISSIONS_MISSING CI-R3_TOP_LEVEL_PERMISSIONS_NOT_READ_ONLY CI-R3_WRITE_PERMISSION_IN_NON_DEPLOY "
       "CI-R3_WRITE_ALL CI-R4_CONCURRENCY_MISSING CI-R5_SECRET_IN_NON_DEPLOY_WORKFLOW "
       "CI-R6_PRODUCTION_CREDENTIAL_OR_COUPLING CI-R7_IMPORT_IN_CI CI-R7_DEPLOY_COMMAND_IN_NON_DEPLOY_WORKFLOW "
       "CI-R8_RUNNER_NOT_STANDARD_HOSTED CI-R9_TIMEOUT_MISSING_OR_LARGE CI-R10_ACTION_NOT_SHA_PINNED "
       "CI-R10_PLACEHOLDER_PIN CI-R11_CHECKOUT_PERSISTS_CREDENTIALS CI-R12_CROSS_REPO_ARTIFACT "
       "CI-R12_ARTIFACT_DIGEST_NOT_ENFORCED CI-R13_EXPRESSION_IN_RUN")),
    ("production-exporter", "G3 (production-change-set)", "production/export_handoff.py (production repo, proposed)",
     "implemented-in-production-change-set",
     "Exporter refusals; listed for one catalogue. Not emitted by this scaffold.",
     W("ALLOCATION_INVALID COMPONENT_INCOMPLETE CONTRACT_LOCK_INVALID CONTRACT_LOCK_MISMATCH CONTRACT_LOCK_MISSING "
       "CONTRACT_NOT_PINNED_IN_REPO CONTRACT_PIN_DIRTY CONTRACT_PIN_MISSING DIRTY_PATHS_TOO_MANY "
       "DIRTY_PATH_UNREPRESENTABLE EVIDENCE_REF_DIRTY EVIDENCE_REF_UNTRACKED GIT_FAILED LANGUAGE_NOT_PLANNED "
       "MEASUREMENT_UNSUPPORTED NOT_A_GIT_REPO NOT_A_REGULAR_FILE NOT_REPO_ROOT OUT_EXISTS "
       "OUT_INSIDE_REPO PACKAGE_NAME_INVALID PATH_OUTSIDE_REPO SCHEMA_CHECK_UNAVAILABLE SELECTED_FILE_MISSING "
       "SELECTED_SOURCE_UNTRACKED SELECTION_GLOB_FORBIDDEN SELECTION_INVALID SELECTION_MISSING SELECTION_OUTSIDE_REPO "
       "SLUG_NOT_ALLOCATED SOURCE_CHANGED_DURING_EXPORT SYMLINK_FORBIDDEN TEXT_ASSET_TOO_LARGE")),
    ("production-exporter-l29", "lead (L-29) for G3's exporter", "production/export_handoff.py (to be added by G3)",
     "planned", "Video selected but ffprobe not available: the exporter refuses video (owner OD-24).",
     W("MEASUREMENT_TOOL_UNAVAILABLE")),
    ("other-proposed", "B", "docs (H1-06)", "proposed", "Release-freezer rule specified, not implemented.",
     W("EMERGENCY_BACKPORT_PENDING")),
]

# Codes no longer emitted, kept so old reports stay interpretable.
DEPRECATED = {
    "MASTER_ROOT_UNSET": ("G3 exporter before L-26", "STATE_ROOT_UNSET", "G3's exporter now emits STATE_ROOT_UNSET/STATE_ROOT_UNSAFE (L-26)."),
    "DUPLICATE_ACTION_ID": ("first H2 build", "DUPLICATE_ACTION", "v2 code restored (Agent F B1)."),
    "OPERATION_TARGET_MISMATCH": ("first H2 build", "UNSUPPORTED_OPERATION", "v2 code restored (Agent F B1)."),
    "SITE_SET_DUPLICATE_STORY": ("first H2 build", "DUPLICATE_SITE_EDITION", "v2 code restored (Agent F B1)."),
    "NON_JSON_VALUE": ("v2 checker", "CJ_*", "H1 safe domain replaces v2's JSON-type check."),
    "SCHEMA": ("v2 checker", "SCHEMA_VIOLATION", "renamed prefix."),
    "PUBLIC_LANGUAGE_PATH_MISMATCH": ("v2 checker (web-bundle.v1)", "WB_STORY_PATH_LANGUAGE_MISMATCH", "web-bundle.v2 rules (Agent C)."),
    "PUBLIC_IMAGE_MISSING": ("v2 checker (web-bundle.v1)", "WB_MEDIA_UNRESOLVED", "web-bundle.v2 rules (Agent C)."),
    "PUBLIC_PLAYER_URL_MISMATCH": ("v2 checker (web-bundle.v1)", "WB_SCHEMA", "player is a oneOf in web-bundle.v2."),
    "DUPLICATE_PUBLIC_PAGE": ("v2 checker (web-bundle.v1)", "WB_ROUTE_DUPLICATE / WB_STORY_LANGUAGE_DUPLICATE", "web-bundle.v2 rules (Agent C)."),
}

PATTERNS = [
    {"regex": "^HTTP_[0-9]{3}$", "family": "podcast-probe", "source": "D", "status": "implemented",
     "meaning": "HTTP status returned by the probed media URL."},
    {"regex": "^RI_[A-Z0-9_]+$", "family": "web-render-input", "source": "C", "status": "implemented",
     "meaning": "RI_ + any validator code reported for the render-input manifest."},
    {"regex": "^SA_[A-Z0-9_]+$", "family": "web-site-artifact", "source": "C", "status": "implemented",
     "meaning": "SA_ + any validator code reported for the site-artifact manifest."},
]


def main():
    codes, seen = [], {}
    for fam, src, module, status, meaning, items in FAMILIES:
        for c in items:
            if c in seen:  # first family owns the code; later families list it as shared
                seen[c]["also_used_by"].append(fam)
                continue
            entry = {"code": c, "family": fam, "source": src, "module": module, "status": status,
                     "meaning": meaning, "also_used_by": []}
            seen[c] = entry
            codes.append(entry)
    for c, (src, repl, why) in DEPRECATED.items():
        assert c not in seen, c
        codes.append({"code": c, "family": "deprecated", "source": src, "module": None, "status": "deprecated",
                      "meaning": why, "replaced_by": repl, "also_used_by": []})
    out = {"catalogue": "Feltwillow error codes", "contract_revision": "H2 (PROPOSED CONTRACT)",
           "format": "Codes are reported as CODE or CODE: context; context never contains secrets.",
           "codes": sorted(codes, key=lambda e: e["code"]), "patterns": PATTERNS,
           "statuses": {"implemented": "emitted by code in this scaffold", "implemented-in-production-change-set":
                        "emitted by G3's exporter (production repo, proposed)", "planned": "named in docs; no code yet",
                        "proposed": "specified by an agent; no code yet", "deprecated": "no longer emitted; see replaced_by"}}
    p = ROOT / "publishing" / "contracts" / "error-codes.json"
    p.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("error codes:", len(codes), "families:", len(FAMILIES))


if __name__ == "__main__":
    main()
