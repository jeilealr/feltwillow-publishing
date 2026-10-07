#!/usr/bin/env python3
"""Podcast fixture definitions (from Agent D's make_fixtures_d.py; contract revision H2).

Every URL uses a reserved .invalid host and every record is example: true. Nothing here is a real Feltwillow show,
feed, GUID or URL. Used by tools/build_examples.py (writes the files) and tests/test_podcast.py (helpers).
H2 change: n05 now expects CJ_FLOAT (the unified validator checks the canonical domain before the schema).
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "tests" / "fixtures" / "feeds"
NEG = ROOT / "tests" / "fixtures" / "podcast" / "negative"
EX = ROOT / "publishing" / "examples"

HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" '
        'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">\n<channel>\n'
        '<title>EXAMPLE Show &amp; Friends</title><description>Synthetic fixture</description>'
        '<language>en</language><link>https://www.example.invalid/</link>'
        '<itunes:image href="https://cdn.example.invalid/show.jpg"/>'
        '<itunes:category text="Kids &amp; Family"/><itunes:explicit>false</itunes:explicit>'
        '{owner}{extra}\n')
OWNER = '<itunes:owner><itunes:name>EXAMPLE</itunes:name><itunes:email>owner@example.invalid</itunes:email></itunes:owner>'


def item(guid, title, pub, url, length, perma=None):
    attr = "" if perma is None else f' isPermaLink="{perma}"'
    return (f'<item><title>{title}</title><description>d</description><guid{attr}>{guid}</guid>'
            f'<pubDate>{pub}</pubDate><enclosure url="{url}" length="{length}" type="audio/mpeg"/>'
            f'<itunes:duration>412</itunes:duration><itunes:episodeType>full</itunes:episodeType></item>\n')


def feed(items, owner=OWNER, extra=""):
    return (HEAD.format(owner=owner, extra=extra) + "".join(items) + "</channel>\n</rss>\n").encode()


E1 = ("example-host-guid-0001", "The Lion &amp; the Mouse (EXAMPLE)", "Tue, 06 Oct 2026 18:00:00 GMT",
      "https://media.example.invalid/ep1-a.mp3", "6600000", "false")
E2 = ("https://www.example.invalid/ep2", "Second &quot;Story&quot; (EXAMPLE)", "Tue, 13 Oct 2026 18:00:00 +0200",
      "https://media.example.invalid/ep2.mp3", "5500000", None)  # no isPermaLink attr -> RSS default true
E3 = ("example-host-guid-0003", "Third (EXAMPLE)", "Tue, 20 Oct 2026 18:00:00 GMT",
      "https://media.example.invalid/ep3.mp3", "4400000", "false")

FEED_FILES = {
    "f01_initial.xml": feed([item(*E2), item(*E1)]),
    # corrected title + replacement audio under a NEW enclosure URL + new episode: all non-breaking
    "f02_correction_and_new_episode.xml": feed([
        item(*E3), item(*E2),
        item(E1[0], "The Lion and the Mouse (EXAMPLE, corrected)", E1[2],
             "https://media.example.invalid/ep1-b.mp3", "6612345", "false")]),
    # host rewrote episode 2's GUID: same title, different GUID -> identity-breaking
    "f03_guid_rewrite.xml": feed([item("https://www.example.invalid/ep2-new", *E2[1:]), item(*E1)]),
    # first publication date reset by an edit -> identity-breaking
    "f04_pubdate_reset.xml": feed([item(*E2), item(E1[0], E1[1], "Wed, 21 Oct 2026 09:00:00 GMT", *E1[3:])]),
    "f05_migration_announced.xml": feed([item(*E2), item(*E1)],
                                        extra="<itunes:new-feed-url>https://feeds.example.invalid/new.xml</itunes:new-feed-url>"),
    "f06_email_removed.xml": feed([item(*E2), item(*E1)], owner=""),
    "f07_duplicate_guid_and_enclosure.xml": feed([item(*E1), item(*E1)]),
    # hostile / malformed inputs
    "x01_billion_laughs.xml": (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
                               b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
                               b'<rss version="2.0"><channel><title>&lol2;</title></channel></rss>'),
    "x02_xxe.xml": (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                    b'<rss version="2.0"><channel><title>&x;</title></channel></rss>'),
    "x03_latin1.xml": '<?xml version="1.0" encoding="ISO-8859-1"?><rss version="2.0"><channel><title>caf\xe9</title></channel></rss>'.encode("latin-1"),
    "x04_malformed.xml": b'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>a & b</title></channel></rss>',
    "x05_atom.xml": b'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>x</title></feed>',
    "x06_lowercase_doctype.xml": b'<?xml version="1.0"?><!doctype rss><rss version="2.0"><channel/></rss>',
}

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def ep(**over):
    base = {
        "kind": "episode-publication", "schema_version": 2, "example": True,
        "canonicalization": "feltwillow-canonical-json-v1", "show_id": "example-show-en",
        "episode_id": "lion-and-mouse.en", "record_revision": 1, "supersedes": None, "change": "prepared",
        "release_id": "lion-and-mouse.en.r0001", "release_sha256": SHA_A, "authority": "spotify",
        "state": "prepared", "episode_type": "full", "guid": None, "guid_is_permalink": None,
        "guid_source": None, "first_published_at": None, "first_pubdate_raw": None,
        "submitted_audio": {"asset_id": "audio-delivery", "sha256": SHA_B, "bytes": 6600000,
                            "media_type": "audio/mpeg", "duration_ms": 412500},
        "observed_enclosure": None, "evidence": None, "observed_at": None,
    }
    base.update(over)
    return base


PUBLISHED = dict(
    record_revision=2, supersedes={"record_revision": 1, "record_sha256": SHA_C}, change="first-publication",
    state="published", guid="example-host-guid-0001", guid_is_permalink=False, guid_source="observed-from-host-feed",
    first_published_at="2026-10-06T18:00:00Z", first_pubdate_raw="Tue, 06 Oct 2026 18:00:00 GMT",
    observed_enclosure={"url": "https://media.example.invalid/ep1-a.mp3", "declared_length_bytes": 6600000,
                        "declared_type": "audio/mpeg", "delivered_sha256": None, "delivered_bytes": None,
                        "head_ok": None, "range_ok": None},
    evidence={"observation_id": "obs-20261006T190000Z-0a1b2c3d", "observation_sha256": SHA_C},
    observed_at="2026-10-06T19:00:00Z")


def registry(records):
    return {"kind": "provider-registry", "schema_version": 2, "example": True,
            "canonicalization": "feltwillow-canonical-json-v1", "records": records}


def reg(rid, dest, etype, eid, kind, url, status="listed", sup=None):
    return {"record_id": rid, "destination": dest, "entity_type": etype, "entity_id": eid, "url_kind": kind,
            "external_url": url, "external_id": None, "status": status, "observed_at": "2026-10-06T19:00:00Z",
            "receipt_id": None, "supersedes_record_id": sup, "note": "EXAMPLE ONLY"}


REG_OK = registry([
    reg("reg-sp-show", "spotify", "show", "example-show-en", "show-page", "https://open.example.invalid/show/x"),
    reg("reg-sp-profile", "spotify", "show", "example-show-en", "creator-profile", "https://creators.example.invalid/pod/x"),
    reg("reg-sp-rss", "spotify", "show", "example-show-en", "rss-feed", "https://feeds.example.invalid/x.xml"),
    reg("reg-sp-ep1", "spotify", "episode", "lion-and-mouse.en", "episode-page", "https://open.example.invalid/episode/y"),
    reg("reg-sp-enc1", "spotify", "episode", "lion-and-mouse.en", "enclosure", "https://media.example.invalid/ep1-a.mp3"),
    reg("reg-sp-embed1", "spotify", "episode", "lion-and-mouse.en", "embed", "https://open.example.invalid/embed/episode/y"),
    reg("reg-ap-show", "apple", "show", "example-show-en", "show-page", "https://podcasts.example.invalid/x/id0"),
    reg("reg-am-show", "amazon", "show", "example-show-en", None, None, status="verification_needed"),
    reg("reg-pc-show", "pocket_casts", "show", "example-show-en", None, None, status="not_submitted"),
    reg("reg-yt-v1", "youtube", "video", "lion-and-mouse.en", "video-page", "https://video.example.invalid/watch/z"),
])


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


NEGATIVE = {
    # name: (record, expected codes)
    "n01-placeholder-url-in-real-record": (ep(**PUBLISHED, example=False), ["PLACEHOLDER_URL_IN_REAL_RECORD"]),
    "n02-real-looking-url-in-example": (ep(**{**PUBLISHED, "observed_enclosure": {**PUBLISHED["observed_enclosure"],
                                         "url": "https://203.0.113.5/ep.mp3"}}),
                                        ["REAL_LOOKING_URL_IN_EXAMPLE"]),
    "n03-spotify-guid-guessed-before-observation": (ep(guid="lion-and-mouse-en-1"), ["SPOTIFY_GUID_BEFORE_OBSERVATION"]),
    "n04-published-without-evidence": (ep(**{**PUBLISHED, "evidence": None}), ["PUBLISHED_EPISODE_INCOMPLETE"]),
    "n05-float-duration": (ep(submitted_audio={**ep()["submitted_audio"], "duration_ms": 412.5}), ["CJ_FLOAT"]),
    "n06-spotify-generated-guid": (ep(**{**PUBLISHED, "guid_source": "generated-before-release"}),
                                   ["GUID_SOURCE_AUTHORITY_MISMATCH"]),
    "n07-release-other-episode": (ep(release_id="ugly-duckling.en.r0001"), ["EPISODE_RELEASE_MISMATCH"]),
    "n08-pubdate-raw-utc-mismatch": (ep(**{**PUBLISHED, "first_published_at": "2026-10-06T16:00:00Z"}),
                                     ["PUBDATE_RAW_UTC_MISMATCH"]),
    "n09-supersedes-on-revision-1": (ep(supersedes={"record_revision": 1, "record_sha256": SHA_C}),
                                     ["EPISODE_SUPERSEDES_INCONSISTENT"]),
    "n10-url-kind-conflict": (registry([
        reg("reg-a", "spotify", "show", "s", "show-page", "https://feeds.example.invalid/x.xml"),
        reg("reg-b", "spotify", "show", "s", "rss-feed", "https://feeds.example.invalid/x.xml")]), ["URL_KIND_CONFLICT"]),
    "n11-rss-feed-on-episode": (registry([reg("reg-a", "spotify", "episode", "e", "rss-feed",
                                              "https://feeds.example.invalid/x.xml")]), ["URL_KIND_ENTITY_MISMATCH"]),
    "n12-listed-without-url": (registry([reg("reg-a", "apple", "show", "s", None, None)]), ["LISTED_WITHOUT_URL"]),
    "n13-enclosure-for-apple": (registry([reg("reg-a", "apple", "episode", "e", "enclosure",
                                              "https://media.example.invalid/a.mp3")]), ["URL_KIND_DESTINATION_MISMATCH"]),
    "n14-supersedes-unknown": (registry([reg("reg-a", "apple", "show", "s", "show-page",
                                             "https://podcasts.example.invalid/a", sup="reg-zzz")]), ["SUPERSEDES_UNKNOWN_RECORD"]),
    "n15-http-url": (registry([reg("reg-a", "apple", "show", "s", "show-page", "http://podcasts.example.invalid/a")]),
                     ["SCHEMA_VIOLATION"]),
    "n16-email-field-smuggled": (registry([{**reg("reg-a", "apple", "show", "s", None, None, status="submitted"),
                                            "verification_email": "owner@example.invalid"}]), ["SCHEMA_VIOLATION"]),
}

SUCCESSION = {
    # name: (prev overrides, new overrides, expected codes)
    "s01-metadata-correction-keeps-identity": (PUBLISHED, {**PUBLISHED, "record_revision": 3,
        "supersedes": {"record_revision": 2, "record_sha256": SHA_C}, "change": "metadata-correction",
        "release_id": "lion-and-mouse.en.r0002"}, []),
    "s02-audio-replacement-keeps-guid-and-date": (PUBLISHED, {**PUBLISHED, "record_revision": 3,
        "supersedes": {"record_revision": 2, "record_sha256": SHA_C}, "change": "audio-replacement",
        "submitted_audio": {**ep()["submitted_audio"], "sha256": "d" * 64, "bytes": 6612345}}, []),
    "s03-guid-changed": (PUBLISHED, {**PUBLISHED, "record_revision": 3, "change": "metadata-correction",
        "supersedes": {"record_revision": 2, "record_sha256": SHA_C}, "guid": "example-host-guid-0001-v2"},
        ["EPISODE_IDENTITY_CHANGED"]),
    "s04-first-date-reset": (PUBLISHED, {**PUBLISHED, "record_revision": 3, "change": "audio-replacement",
        "supersedes": {"record_revision": 2, "record_sha256": SHA_C}, "first_published_at": "2026-10-21T09:00:00Z", "first_pubdate_raw": "Wed, 21 Oct 2026 09:00:00 GMT",
        "submitted_audio": {**ep()["submitted_audio"], "sha256": "d" * 64}}, ["EPISODE_IDENTITY_CHANGED"]),
    "s05-replacement-same-bytes": (PUBLISHED, {**PUBLISHED, "record_revision": 3, "change": "audio-replacement",
        "supersedes": {"record_revision": 2, "record_sha256": SHA_C}}, ["AUDIO_REPLACEMENT_WITHOUT_NEW_AUDIO"]),
    "s06-migration-new-guid": (PUBLISHED, {**PUBLISHED, "record_revision": 3, "change": "host-migration",
        "authority": "independent", "supersedes": {"record_revision": 2, "record_sha256": SHA_C},
        "guid_source": "generated-before-release", "guid": "urn:uuid:00000000-0000-4000-8000-000000000001"},
        ["EPISODE_IDENTITY_CHANGED", "MIGRATION_GUID_NOT_RETAINED"]),
    "s07-migration-retained": (PUBLISHED, {**PUBLISHED, "record_revision": 3, "change": "host-migration",
        "authority": "independent", "supersedes": {"record_revision": 2, "record_sha256": SHA_C},
        "guid_source": "retained-from-previous-host"}, []),
}

