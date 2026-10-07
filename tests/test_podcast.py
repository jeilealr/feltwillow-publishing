"""Podcast suites (Agent D's check_d.py, integrated for H2): podcast examples, negative and succession
fixtures, hostile feeds, observation content, change classification, reconcile, the INACTIVE independent-RSS
reference builder, and the media-delivery probe against a local 127.0.0.1 server only.
"""
from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from feltwillow_publish.podcast import podcast as D
import podcast_fixtures as PF
from support import EXAMPLES, FIX

FEEDS = FIX / "feeds"


def run(ctx):
    results = {"cases": []}

    def case(name, ok, detail=None):
        results["cases"].append({"case": name, "pass": bool(ok), "got": detail})

    def obs(name, oid="obs-20261006T190000Z-00000000"):
        return D.observe_feed((FEEDS / name).read_bytes(), show_id="example-show-en",
                              feed_url="https://feeds.example.invalid/x.xml", fetched_at="2026-10-06T19:00:00Z",
                              observation_id=oid, example=True)


    # 1. examples (schemas are meta-checked by test_contracts)
    for p in sorted(EXAMPLES.glob("*.json")):
        if p.name.split(".")[0] in ("episode-publication", "provider-registry", "feed-observation"):
            errs = D.validate(json.loads(p.read_text()))
            case(f"example:{p.name}", errs == [], errs)

    # 2. negative records and succession fixtures
    for p in sorted((FIX / "podcast" / "negative").glob("*.json")):
        fx = json.loads(p.read_text())
        if "record" in fx:
            got = D.validate(fx["record"])
        else:
            assert D.validate(fx["previous"]) == [] and D.validate(fx["new"]) == [], p.name
            got = D.check_succession(fx["previous"], fx["new"])
        case(f"negative:{p.stem}", got == sorted(fx["expected"]), {"expected": fx["expected"], "got": got})

    # 3. safe parsing of hostile feeds
    for name, code in [("x01_billion_laughs.xml", "FEED_DTD_FORBIDDEN"), ("x02_xxe.xml", "FEED_DTD_FORBIDDEN"),
                       ("x03_latin1.xml", "FEED_ENCODING_UNSUPPORTED"), ("x04_malformed.xml", "FEED_XML_MALFORMED"),
                       ("x05_atom.xml", "FEED_NOT_RSS"), ("x06_lowercase_doctype.xml", "FEED_DTD_FORBIDDEN")]:
        try:
            obs(name)
            case(f"hostile:{name}", False, "accepted")
        except D.FeedRejected as e:
            case(f"hostile:{name}", e.code == code, e.code)

    # 4. observation content
    o1 = obs("f01_initial.xml")
    case("observe:f01 validates", D.validate(o1) == [], D.validate(o1))
    case("observe:f01 no problems", o1["problems"] == [], o1["problems"])
    ep2 = next(i for i in o1["items"] if i["guid"] == "https://www.example.invalid/ep2")
    case("observe:isPermaLink default true when attribute absent",
         ep2["guid_is_permalink"] is True and ep2["guid_permalink_attr_present"] is False)
    case("observe:+0200 pubDate normalized to UTC", ep2["pubdate_utc"] == "2026-10-13T16:00:00Z", ep2["pubdate_utc"])
    case("observe:entity-escaped title decoded", o1["items"][1]["title"] == "The Lion & the Mouse (EXAMPLE)")
    case("observe:email value not stored", "owner@example.invalid" not in json.dumps(o1))
    o6 = obs("f06_email_removed.xml")
    case("observe:missing itunes email flagged", "FEED_EMAIL_ABSENT" in o6["problems"], o6["problems"])
    o7 = obs("f07_duplicate_guid_and_enclosure.xml")
    case("observe:duplicate guid/enclosure flagged",
         {"DUPLICATE_GUID", "DUPLICATE_ENCLOSURE_URL"} <= set(o7["problems"]), o7["problems"])

    # 5. feed change classification
    def events(a, b):
        return [(e["event"], e["breaking"]) for e in D.diff_observations(a, b)]


    ev = events(o1, obs("f02_correction_and_new_episode.xml"))
    case("diff:correction + replacement + new episode are non-breaking",
         sorted(ev) == sorted([("ENCLOSURE_LENGTH_CHANGED", False), ("ENCLOSURE_URL_CHANGED", False),
                               ("ITEM_ADDED", False), ("TITLE_CHANGED", False)]), ev)
    ev = events(o1, obs("f03_guid_rewrite.xml"))
    case("diff:guid rewrite detected as breaking", ev == [("SUSPECTED_GUID_REWRITE", True)], ev)
    ev = events(o1, obs("f04_pubdate_reset.xml"))
    case("diff:pubdate reset is breaking", ev == [("PUBDATE_CHANGED", True)], ev)
    ev = events(o1, obs("f05_migration_announced.xml"))
    case("diff:new-feed-url announced", ev == [("NEW_FEED_URL_ANNOUNCED", False)], ev)
    ev = events(o1, o6)
    case("diff:email removed is breaking (directory verification)", ev == [("FEED_EMAIL_REMOVED", True)], ev)

    # 6. reconcile ledger vs observation
    published = PF.ep(**PF.PUBLISHED)
    case("reconcile:ledger matches f01", D.reconcile([published], o1) == [], D.reconcile([published], o1))
    r = D.reconcile([published], obs("f04_pubdate_reset.xml"))
    case("reconcile:date drift reported", r == [("lion-and-mouse.en", "FIRST_PUBLISHED_AT_DRIFT")], r)
    r = D.reconcile([published], obs("f02_correction_and_new_episode.xml"))
    case("reconcile:enclosure change reported", r == [("lion-and-mouse.en", "ENCLOSURE_CHANGED_SINCE_RECORD")], r)

    # 7. independent RSS generator round trip (INACTIVE module reference)
    show = {"title": 'EXAMPLE <Show> & "Friends"', "description": "Tales & morals <for> kids", "language": "en",
            "website_url": "https://www.example.invalid/", "author": "EXAMPLE Author",
            "artwork_url": "https://cdn.example.invalid/show.jpg", "category": "Kids & Family",
            "subcategory": "Stories for Kids", "explicit": False, "show_type": "episodic",
            "public_contact_email": "podcast@example.invalid",
            "episodes": {"lion-and-mouse.en": {"title": "Lion & Mouse — 🦁 <part 1>", "description": "a ]]> b"},
                         "second.en": {"title": "Second", "description": "x"}}}
    ep_b = PF.ep(**{**PF.PUBLISHED, "episode_id": "second.en", "release_id": "second.en.r0001",
                   "guid": "urn:uuid:00000000-0000-4000-8000-000000000002", "guid_source": "generated-before-release",
                   "authority": "independent", "first_published_at": "2026-10-13T16:00:00Z", "first_pubdate_raw": None,
                   "observed_enclosure": {**PF.PUBLISHED["observed_enclosure"], "url": "https://media.example.invalid/2.mp3"}})
    prepared = PF.ep(episode_id="third.en", release_id="third.en.r0001", authority="independent")
    xml = D.build_feed(show, [published, ep_b, prepared])
    og = D.observe_feed(xml, show_id="example-show-en", feed_url="https://feeds.example.invalid/x.xml",
                        fetched_at="2026-10-06T19:00:00Z", observation_id="obs-20261006T190000Z-11111111", example=True)
    case("build:round trip has no problems", og["problems"] == [], og["problems"])
    case("build:only published episodes emitted", og["channel"]["item_count"] == 2)
    case("build:special characters survive", og["items"][1]["title"] == "Lion & Mouse — 🦁 <part 1>"
         and og["channel"]["title"] == show["title"], og["items"][1]["title"])
    case("build:raw host pubDate retained verbatim", og["items"][1]["pubdate_raw"] == "Tue, 06 Oct 2026 18:00:00 GMT")
    case("build:ledger reconciles with generated feed", D.reconcile([published, ep_b], og) == [])
    try:
        D.build_feed(show, [published, {**published, "episode_id": "second.en"}])
        case("build:duplicate GUID refused", False)
    except ValueError as e:
        case("build:duplicate GUID refused", str(e) == "DUPLICATE_GUID", str(e))

    # 8. media-delivery probe against local servers
    BODY = hashlib.sha256(b"seed").digest() * 4096  # 131072 bytes of synthetic "audio"


    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _hdr(self, code, length, extra=None):
            self.send_response(code)
            ctype = "text/html" if self.path.startswith("/wrongtype") else "audio/mpeg"
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()

        def do_HEAD(self):
            if self.path.startswith("/redir"):
                self.send_response(301); self.send_header("Location", "http://unapproved.invalid/a.mp3"); self.end_headers(); return
            self._hdr(200, len(BODY), {"Accept-Ranges": "bytes"} if self.path.startswith("/ok") else None)

        def do_GET(self):
            if self.path.startswith("/redir"):
                self.send_response(301); self.send_header("Location", "http://unapproved.invalid/a.mp3"); self.end_headers(); return
            rng = self.headers.get("Range")
            if rng and not self.path.startswith("/norange"):
                a, b = rng.split("=")[1].split("-")
                chunk = BODY[int(a):int(b) + 1]
                self._hdr(206, len(chunk), {"Content-Range": f"bytes {a}-{int(a) + len(chunk) - 1}/{len(BODY)}"})
                self.wfile.write(chunk)
            else:
                self._hdr(200, len(BODY)); self.wfile.write(BODY)


    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    for path, exp in [("/ok.mp3", []), ("/norange.mp3", ["RANGE_NOT_SUPPORTED"]),
                      ("/wrongtype.mp3", ["CONTENT_TYPE_MISMATCH"]), ("/redir.mp3", ["REDIRECT_TO_UNAPPROVED_HOST"])]:
        ok, findings, facts = D.probe_media(base + path, expected_bytes=len(BODY), expected_type="audio/mpeg")
        case(f"probe:{path}", findings == exp, {"findings": findings, "facts": facts})
    ok, findings, _ = D.probe_media(base + "/ok.mp3", expected_bytes=len(BODY) + 1, expected_type="audio/mpeg")
    case("probe:length mismatch", findings == ["CONTENT_LENGTH_MISMATCH", "RANGE_TOTAL_MISMATCH"], findings)
    srv.shutdown()


    return {"podcast": results["cases"]}
