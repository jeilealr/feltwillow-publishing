# v2 checker rules in H2: ported, adapted, retired

Source: `semantic_errors`, `declarative_readiness_errors` and `self_tests` in the v2 package's
`tools/validate_blueprint.py` (baseline copy, SHA-256 manifest verified). Agent F's review (B1) found that the
first H2 build dropped many of these rules. They were ported on 2026-10-07; this file lists every rule's status.
Fixture ids refer to `tests/fixtures/negative/{records,raw}/`; `v2_semantics_ported` is the test group that
re-runs v2's 35 self-test mutations on the H2 successor kinds (all 35 pass).

## Ported with the v2 code (implemented, one fixture each)

| v2 code | Kind (H2) | Fixture |
|---|---|---|
| MULTIPLE_WEBSITES | project.v2 | fv01 |
| PRIMARY_NOT_SELECTED | project.v2 | v2p01 |
| MODULE_NOT_ENABLED | project.v2 | v2p02 (plus `PRIMARY_MODULE_SPEC_ONLY`, L-25) |
| MISSING_ORIGIN | project.v2 | v2p03 |
| MULTIPLE_FEED_AUTHORITIES | project.v2 | fv02 |
| FEED_AUTHORITY_NOT_SELECTED | project.v2 | v2p04 |
| ZERO_PROFILE_FORBIDDEN_CAPABILITY | project.v2 (and strict_zero) | v2p05 |
| PRODUCTION_WRITE_SWITCH_CONFLICT | project.v2 | fv04 |
| DUPLICATE_CATALOG_OR_EDITION | catalog.v1, story.v1 (carried) | fv06, v2p06 |
| DUPLICATE_RIGHTS_COMPONENT | rights-review.v1 (carried) | v2p07 |
| INCOMPLETE_RIGHTS_CLEARANCE | rights-review.v1 (carried) | fv05 |
| DUPLICATE_COLLECTION_ASSET, COLLECTION_MASTER_REFERENCE_MISSING, COLLECTION_ORDER_INVALID, DUPLICATE_COLLECTION_EPISODE | collection.v1 (carried) | v2p08..v2p11 |
| NATIVE_AUDIO_REFERENCE_MISSING | release.v2 | fv07 |
| SPOTIFY_EPISODE_REFERENCE_MISSING | release.v2 | v2p12 |
| UNKNOWN_ASSET / WRONG_ASSET_ROLE for channel assets | release.v2 | v2p13, v2p14 |
| RELEASE_ID_MISMATCH, AGE_RANGE_REVERSED, DUPLICATE_ASSET_ID, MISSING_IMAGE_DIMENSIONS, MISSING_MEDIA_DURATION | release.v2 | already in H1 (r02 ...) |
| DUPLICATE_APPROVAL_CHECK, INVALID_POSITIVE_APPROVAL | approval.v2 | already in H1 (a01) |
| DUPLICATE_PROVIDER_MAPPING | provider-registry.v2 | fv09 (adapted key, below) |
| DUPLICATE_SITE_EDITION | site-set.v2 | ss03 (replaces first-build `SITE_SET_DUPLICATE_STORY`) |
| UNSAFE_REMOVAL_PATH | site-set.v2 | v2p19 |
| PLAN_EXPIRY_ORDER | publish-plan.v2 | v2p15 (replaces first-build `TIMESTAMP_ORDER` for plans) |
| DUPLICATE_ACTION | publish-plan.v2 | v2p16 (replaces `DUPLICATE_ACTION_ID`) |
| UNSUPPORTED_OPERATION | publish-plan.v2 | pl06 (replaces `OPERATION_TARGET_MISMATCH`; H2 target/operation table) |
| EMPTY_PRODUCTION_PLAN | publish-plan.v2 | v2p17 |
| UNSAFE_URL | every kind except feed-observation | v2p20 |
| UNSAFE_PATH | prepass (+ `draft_path`, `artifact_path`) | h12, p04, v2 mutation 07/08 |
| WRONG_EMBED_HOST | web-bundle.v2 (real records only) | v2p21 |
| Readiness: NOT_A_RELEASE, EXAMPLE_RECORD, RELEASE_NOT_FROZEN, RIGHTS_NOT_CLEARED, RIGHTS_RECORD_HASH_MISSING, SOURCE_HASH_MISSING, CHANNEL_NOT_REQUESTED, MISSING_ASSET, UNAPPROVED_ASSET, PODCAST_ID_MISSING, PODCAST_COVER_DIMENSIONS | `validate.readiness_errors(release.v2, channel)` | v2 mutations 23-25 |

## Adapted (rule kept, condition changed for H2)

| v2 rule | H2 behaviour | Why |
|---|---|---|
| FEED_MODULE_NOT_ENABLED: the chosen authority's module must be `enabled` | fires only when a feed module IS enabled and it is not the chosen authority's (fixture fv03) | The owner decided Spotify as first host (2026-10-07) while every module stays `spec_only`; `podcast_authority` now records a decision before activation. Enabling the wrong module is still refused. |
| DUPLICATE_PROVIDER_MAPPING on (entity_type, entity_id, destination) | on (entity_type, entity_id, destination, url_kind), active `listed` rows only | provider-registry.v2 records one row per URL kind (show page, RSS, embed ...) and keeps superseded history (Agent D, m3). |
| SOURCE_HASH_MISSING (sources[] without sha256) | release has no pinned handoffs | v2 `sources[]` became pinned handoff package digests (release.v2, IC-A1). |
| v2 mutations 07/08 (path in `sources[0].path`) | applied to `rights.record_path` | release.v2 has no `sources[]`. |
| v2 mutations 18-22 (web-bundle.v1) | applied to web-bundle.v2 | Agent C's successor schema. |
| DUPLICATE_REMOVAL | site-set.v2 schema (`uniqueItems`) rejects first with SCHEMA_VIOLATION (fixture v2p18); the semantic check stays as defence in depth | H2 schema is stricter. |

## Retired (replaced; listed as `deprecated` in error-codes.json)

| v2 code | Replaced by | Why |
|---|---|---|
| NON_JSON_VALUE | CJ_* (H1 safe domain) | floats and big integers are now outside the canonical domain |
| SCHEMA | SCHEMA_VIOLATION | renamed prefix |
| PUBLIC_LANGUAGE_PATH_MISMATCH | WB_STORY_PATH_LANGUAGE_MISMATCH | web-bundle.v2 (Agent C) |
| PUBLIC_IMAGE_MISSING | WB_MEDIA_UNRESOLVED | web-bundle.v2 media map replaces per-story `images` |
| PUBLIC_PLAYER_URL_MISMATCH | WB_SCHEMA | player is a `oneOf` (none / spotify_embed / native_audio) |
| DUPLICATE_PUBLIC_PAGE | WB_ROUTE_DUPLICATE, WB_STORY_LANGUAGE_DUPLICATE | web-bundle.v2 |

## Known limits of the carried kinds (OPEN)

- `collection.v1` assets use v2's `common.v1` asset with float `duration_seconds`; a non-null float is outside
  the H2 canonical domain (`CJ_FLOAT`). A `collection.v2` with integer `duration_ms` is needed before any
  collection carries media (backlog; audiobook/book scopes are deferred, DECISIONS_H2 s.7).
- `show.v1` still has `owner_email`; the public contact address now lives in `project.v2`
  (`public_contact_email`). A `show.v2` should drop it when shows are implemented.

## Removed by owner decisions L-28 / L-29 (2026-10-07; H2 unreleased, amended in place)

| Removed | Replacement | Fixtures |
|---|---|---|
| handoff component `reading` (`text_asset`, illustrations, cover) and role `reading-text` | component `images` (illustrations, cover); reading text = publishing `reading-edition.v1` | hr01, hr02, hr03 |
| release `content.reading_text_asset` and release asset role `reading-text` | `content.reading_edition` pin; `READING_EDITION_MISSING` when the website channel is requested | re01, re02 |
| handoff role `audio-delivery` and `audio.delivery_asset` (MP3/M4A) | WAV/FLAC master only; publishing derives delivery MP3s; `HANDOFF_AUDIO_NOT_LOSSLESS` | ms04, ms05 |
| measurement without provenance | `measurement: {tool: feltwillow-stdlib or ffprobe, version}`; `MEASUREMENT_PROVENANCE_MISSING`; video needs ffprobe (`VIDEO_MEASUREMENT_REQUIRES_FFPROBE`) | ms01, ms02, ms03 (positive), ms06 |
