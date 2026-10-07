#!/usr/bin/env python3
"""Podcast reference code (Agent D; integrated into feltwillow_publish.podcast for contract revision H2).

PROPOSED CONTRACT. Implemented and tested offline only; no provider is called.

Offline helpers for the podcast runbooks:
  * validate()           schema + semantic checks for episode-publication.v2, provider-registry.v2,
                          feed-observation.v1 (schema checks via feltwillow_publish.contracts.validate)
  * observe_feed()       safe, read-only parse of a downloaded RSS document -> feed-observation record
  * diff_observations()  classify feed changes between two observations (identity-breaking vs expected)
  * check_succession()   episode identity must survive record revisions
  * build_feed()         reference generator for the INACTIVE independent-RSS module (serializer escaping)
  * probe_media()        HEAD + byte-range probe of one enclosure URL (used in tests only against localhost)

No provider API is called. No credentials are read. Network use is limited to probe_media(), which the
test suite points only at a local test server.
"""
from __future__ import annotations

import email.utils
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
CONTENT = "http://purl.org/rss/1.0/modules/content/"
MAX_FEED_BYTES = 20 * 1024 * 1024
PLACEHOLDER_HOST = re.compile(r"(^|\.)(invalid|example|test|localhost)$|(^|\.)example\.(com|org|net)$", re.I)


from ..contracts import validate as _v

PLACEHOLDER_HOST_NOTE = "examples must use reserved hosts only; real records must never use them"


def _host(url):
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _urls(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _urls(v)
    elif isinstance(value, list):
        for v in value:
            yield from _urls(v)
    elif isinstance(value, str) and value.startswith("https://"):
        yield value


def validate(record):
    """Agent D's interface: sorted list of error codes ([] = valid), via the unified H2 validator."""
    return _v.codes(_v.validate(record))


def podcast_semantics(record):
    """Semantic rules for episode-publication.v2, provider-registry.v2, feed-observation.v1 (Agent D)."""
    errors = set()
    # anti-fabrication: real records must not carry placeholder hosts; examples must carry ONLY placeholders
    for url in _urls(record):
        placeholder = bool(PLACEHOLDER_HOST.search(_host(url)))
        if record["example"] is False and placeholder:
            errors.add("PLACEHOLDER_URL_IN_REAL_RECORD")
        if record["example"] is True and not placeholder:
            errors.add("REAL_LOOKING_URL_IN_EXAMPLE")
    errors |= {"episode-publication": _sem_episode, "provider-registry": _sem_registry,
               "feed-observation": _sem_observation}[record["kind"]](record)
    return sorted(errors)


def _sem_episode(r):
    e = set()
    stem = r["release_id"].rsplit(".r", 1)[0]
    if stem != r["episode_id"]:
        e.add("EPISODE_RELEASE_MISMATCH")
    if r["state"] == "prepared":
        if r["change"] != "prepared":
            e.add("EPISODE_CHANGE_STATE_MISMATCH")
        if r["authority"] == "spotify" and any(r[k] is not None for k in ("guid", "first_published_at")):
            e.add("SPOTIFY_GUID_BEFORE_OBSERVATION")  # Spotify assigns it; never pre-fill a guess
    else:
        for k in ("guid", "guid_is_permalink", "guid_source", "first_published_at", "first_pubdate_raw",
                  "observed_enclosure", "evidence", "observed_at"):
            if r[k] is None:
                e.add("PUBLISHED_EPISODE_INCOMPLETE")
        if r["change"] == "prepared":
            e.add("EPISODE_CHANGE_STATE_MISMATCH")
    if r["authority"] == "spotify" and r["guid_source"] == "generated-before-release":
        e.add("GUID_SOURCE_AUTHORITY_MISMATCH")
    if r["authority"] == "independent" and r["state"] != "prepared" and r["guid_source"] == "observed-from-host-feed":
        e.add("GUID_SOURCE_AUTHORITY_MISMATCH")
    if (r["record_revision"] == 1) != (r["supersedes"] is None):
        e.add("EPISODE_SUPERSEDES_INCONSISTENT")
    if r["supersedes"] and r["supersedes"]["record_revision"] != r["record_revision"] - 1:
        e.add("EPISODE_SUPERSEDES_INCONSISTENT")
    if r["first_pubdate_raw"] is not None and r["first_published_at"] is not None:
        utc = rfc2822_to_utc(r["first_pubdate_raw"])
        if utc != r["first_published_at"]:
            e.add("PUBDATE_RAW_UTC_MISMATCH")
    return e


KIND_ENTITY = {
    "show-page": {"show"}, "creator-profile": {"show"}, "rss-feed": {"show"},
    "episode-page": {"episode"}, "enclosure": {"episode"}, "embed": {"show", "episode", "video"},
    "video-page": {"video"}, "playlist-page": {"show", "collection"}, "website-page": {"website-story", "collection"},
}
DEST_KINDS = {
    "spotify": {"show-page", "episode-page", "rss-feed", "enclosure", "embed", "creator-profile"},
    "independent-rss": {"rss-feed", "enclosure"},
    "apple": {"show-page", "episode-page"}, "amazon": {"show-page", "episode-page"},
    "pocket_casts": {"show-page", "episode-page"},
    "youtube": {"video-page", "playlist-page", "embed"},
    "ghost": {"website-page"}, "website": {"website-page"},
}


def _sem_registry(r):
    e, ids, url_kind = set(), set(), {}
    for rec in r["records"]:
        if rec["record_id"] in ids:
            e.add("DUPLICATE_RECORD_ID")
        ids.add(rec["record_id"])
        k, url = rec["url_kind"], rec["external_url"]
        if (k is None) != (url is None):
            e.add("URL_KIND_REQUIRED")
        if k is not None:
            if rec["entity_type"] not in KIND_ENTITY[k]:
                e.add("URL_KIND_ENTITY_MISMATCH")
            if k not in DEST_KINDS[rec["destination"]]:
                e.add("URL_KIND_DESTINATION_MISMATCH")
        if rec["status"] == "listed" and url is None:
            e.add("LISTED_WITHOUT_URL")
        if url is not None and rec["status"] != "superseded":
            prev = url_kind.setdefault(url, k)
            if prev != k:
                e.add("URL_KIND_CONFLICT")  # one URL recorded as two different kinds
    # v2 DUPLICATE_PROVIDER_MAPPING, refined for url_kind (m3): one active listed row per
    # (entity_type, entity_id, destination, url_kind)
    active = [(x["entity_type"], x["entity_id"], x["destination"], x["url_kind"]) for x in r["records"]
              if x["status"] == "listed"]
    if len(active) != len(set(active)):
        e.add("DUPLICATE_PROVIDER_MAPPING")
    for rec in r["records"]:
        if rec["supersedes_record_id"] is not None and rec["supersedes_record_id"] not in ids:
            e.add("SUPERSEDES_UNKNOWN_RECORD")
    return e


def _sem_observation(r):
    e = set()
    if r["channel"]["item_count"] != len(r["items"]):
        e.add("ITEM_COUNT_MISMATCH")
    return e


# ---------------------------------------------------------------- time
def rfc2822_to_utc(raw):
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None or dt.tzinfo is None:
        return None  # a pubDate without a zone is ambiguous; never guess
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_to_rfc2822(utc):
    dt = datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return email.utils.format_datetime(dt)  # e.g. 'Tue, 06 Oct 2026 18:00:00 +0000'


# ---------------------------------------------------------------- safe XML
class FeedRejected(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


_FORBIDDEN_MARKUP = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)


def safe_parse(data: bytes):
    """Parse untrusted feed bytes. DTDs/entities are refused before the parser sees them, so entity
    expansion and external entities cannot occur even with an older Expat (LUMI venv: expat 2.6.4)."""
    if len(data) > MAX_FEED_BYTES:
        raise FeedRejected("FEED_TOO_LARGE")
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if _FORBIDDEN_MARKUP.search(data):
        raise FeedRejected("FEED_DTD_FORBIDDEN")
    head = data[:200].decode("ascii", "replace")
    m = re.match(r"\s*<\?xml[^>]*encoding=[\"']([A-Za-z0-9._-]+)[\"']", head)
    if m and m.group(1).lower() not in ("utf-8", "utf8"):
        raise FeedRejected("FEED_ENCODING_UNSUPPORTED")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise FeedRejected("FEED_INVALID_UTF8")
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise FeedRejected("FEED_XML_MALFORMED")
    if root.tag != "rss" or root.find("channel") is None:
        raise FeedRejected("FEED_NOT_RSS")
    return root


def _text(el, path, ns=None):
    x = el.find(path, ns or {})
    if x is None or x.text is None:
        return None
    return x.text.strip()


def observe_feed(data: bytes, *, show_id, feed_url, fetched_at, observation_id, example, fetch=None):
    """Return a feed-observation.v1 record (raises FeedRejected for unsafe/unparseable input)."""
    root = safe_parse(data)
    ch = root.find("channel")
    ns = {"itunes": ITUNES}
    problems, items, seen_guid, seen_encl = set(), [], set(), set()
    for it in ch.findall("item"):
        g = it.find("guid")
        guid = g.text.strip() if g is not None and g.text else None
        attr = g.get("isPermaLink") if g is not None else None
        is_perma = (attr is None) or (attr.strip().lower() == "true")  # RSS 2.0: default true
        if guid is None:
            problems.add("ITEM_WITHOUT_GUID")
        elif guid in seen_guid:
            problems.add("DUPLICATE_GUID")
        seen_guid.add(guid)
        enc = it.find("enclosure")
        enclosure = None
        if enc is None:
            problems.add("ITEM_WITHOUT_ENCLOSURE")
        else:
            enclosure = {"url": enc.get("url", ""), "length": enc.get("length"), "type": enc.get("type")}
            if enclosure["url"] in seen_encl:
                problems.add("DUPLICATE_ENCLOSURE_URL")
            seen_encl.add(enclosure["url"])
            if not enclosure["length"] or not enclosure["length"].isdigit():
                problems.add("ENCLOSURE_LENGTH_INVALID")
            if not enclosure["type"]:
                problems.add("ENCLOSURE_TYPE_MISSING")
            if not enclosure["url"].startswith("https://"):
                problems.add("ENCLOSURE_NOT_HTTPS")
        raw = _text(it, "pubDate")
        utc = rfc2822_to_utc(raw) if raw else None
        if raw is None:
            problems.add("ITEM_WITHOUT_PUBDATE")
        elif utc is None:
            problems.add("PUBDATE_UNPARSEABLE")
        items.append({
            "guid": guid, "guid_is_permalink": is_perma, "guid_permalink_attr_present": attr is not None,
            "title": _text(it, "title"), "pubdate_raw": raw, "pubdate_utc": utc, "enclosure": enclosure,
            "itunes_duration_raw": _text(it, "itunes:duration", ns),
            "itunes_episode_type": _text(it, "itunes:episodeType", ns),
        })
    if ch.find("itunes:owner/itunes:email", ns) is None and ch.find("itunes:email", ns) is None:
        problems.add("FEED_EMAIL_ABSENT")  # directory ownership checks (e.g. Amazon) will fail
    for tag in ("title", "description", "language"):
        if _text(ch, tag) is None:
            problems.add(f"CHANNEL_{tag.upper()}_MISSING")
    if ch.find("itunes:explicit", ns) is None:
        problems.add("CHANNEL_EXPLICIT_MISSING")
    if ch.find("itunes:category", ns) is None:
        problems.add("CHANNEL_CATEGORY_MISSING")
    if ch.find("itunes:image", ns) is None and ch.find("image") is None:
        problems.add("CHANNEL_ARTWORK_MISSING")
    return {
        "kind": "feed-observation", "schema_version": 1, "example": example,
        "canonicalization": "feltwillow-canonical-json-v1", "observation_id": observation_id, "show_id": show_id,
        "feed_url": feed_url, "fetched_at": fetched_at, "fetch": fetch,
        "feed_sha256": hashlib.sha256(data).hexdigest(), "feed_bytes": len(data),
        "channel": {
            "title": _text(ch, "title"), "language": _text(ch, "language"),
            "itunes_email_present": "FEED_EMAIL_ABSENT" not in problems,
            "itunes_new_feed_url": _text(ch, "itunes:new-feed-url", ns),
            "itunes_block": _text(ch, "itunes:block", ns), "item_count": len(items),
        },
        "items": items, "problems": sorted(problems),
    }


# ---------------------------------------------------------------- feed change classification
BREAKING = {"ITEM_REMOVED", "SUSPECTED_GUID_REWRITE", "PUBDATE_CHANGED", "PERMALINK_FLAG_CHANGED",
            "FEED_BLOCKED", "FEED_EMAIL_REMOVED"}


def diff_observations(old, new):
    """Return a list of {event, guid, detail, breaking}. Order-insensitive; keyed on exact GUID text."""
    events = []
    o = {i["guid"]: i for i in old["items"] if i["guid"]}
    n = {i["guid"]: i for i in new["items"] if i["guid"]}
    removed = [g for g in o if g not in n]
    added = [g for g in n if g not in o]
    for g in removed:
        twin = next((a for a in added if (n[a]["title"] == o[g]["title"] and o[g]["title"])
                     or (n[a]["pubdate_utc"] == o[g]["pubdate_utc"] and o[g]["pubdate_utc"])), None)
        if twin:
            events.append({"event": "SUSPECTED_GUID_REWRITE", "guid": g, "detail": twin})
        else:
            events.append({"event": "ITEM_REMOVED", "guid": g, "detail": None})
    paired = {e["detail"] for e in events if e["event"] == "SUSPECTED_GUID_REWRITE"}
    for g in added:
        if g not in paired:
            events.append({"event": "ITEM_ADDED", "guid": g, "detail": None})
    for g in o.keys() & n.keys():
        a, b = o[g], n[g]
        if a["pubdate_utc"] != b["pubdate_utc"]:
            events.append({"event": "PUBDATE_CHANGED", "guid": g, "detail": f"{a['pubdate_utc']} -> {b['pubdate_utc']}"})
        if a["guid_is_permalink"] != b["guid_is_permalink"]:
            events.append({"event": "PERMALINK_FLAG_CHANGED", "guid": g, "detail": None})
        if a["title"] != b["title"]:
            events.append({"event": "TITLE_CHANGED", "guid": g, "detail": None})
        ae, be = a["enclosure"] or {}, b["enclosure"] or {}
        if ae.get("url") != be.get("url"):
            events.append({"event": "ENCLOSURE_URL_CHANGED", "guid": g, "detail": None})
        if ae.get("length") != be.get("length"):
            events.append({"event": "ENCLOSURE_LENGTH_CHANGED", "guid": g, "detail": None})
    oc, nc = old["channel"], new["channel"]
    if nc["itunes_new_feed_url"] and nc["itunes_new_feed_url"] != oc["itunes_new_feed_url"]:
        events.append({"event": "NEW_FEED_URL_ANNOUNCED", "guid": None, "detail": nc["itunes_new_feed_url"]})
    if (nc["itunes_block"] or "").lower() == "yes" and (oc["itunes_block"] or "").lower() != "yes":
        events.append({"event": "FEED_BLOCKED", "guid": None, "detail": None})
    if oc["itunes_email_present"] and not nc["itunes_email_present"]:
        events.append({"event": "FEED_EMAIL_REMOVED", "guid": None, "detail": None})
    for ev in events:
        ev["breaking"] = ev["event"] in BREAKING
    return sorted(events, key=lambda x: (x["event"], x["guid"] or ""))


def reconcile(episodes, observation):
    """Check every published episode-publication record against one observation of its show feed."""
    by_guid = {i["guid"]: i for i in observation["items"] if i["guid"]}
    out = []
    for ep in episodes:
        if ep["state"] != "published":
            continue
        item = by_guid.get(ep["guid"])
        if item is None:
            out.append((ep["episode_id"], "EPISODE_MISSING_FROM_FEED"))
            continue
        if item["pubdate_utc"] != ep["first_published_at"]:
            out.append((ep["episode_id"], "FIRST_PUBLISHED_AT_DRIFT"))
        if item["guid_is_permalink"] != ep["guid_is_permalink"]:
            out.append((ep["episode_id"], "PERMALINK_FLAG_DRIFT"))
        enc = item["enclosure"] or {}
        if ep["observed_enclosure"] and enc.get("url") != ep["observed_enclosure"]["url"]:
            out.append((ep["episode_id"], "ENCLOSURE_CHANGED_SINCE_RECORD"))
    return out


def check_succession(prev, new):
    """Identity rules across episode-publication record revisions (B H1-06 §6, v2 I08)."""
    e = set()
    if new["episode_id"] != prev["episode_id"] or new["show_id"] != prev["show_id"]:
        e.add("EPISODE_IDENTITY_CHANGED")
    if new["record_revision"] != prev["record_revision"] + 1:
        e.add("EPISODE_SUPERSEDES_INCONSISTENT")
    if prev["state"] != "prepared":
        for k in ("guid", "guid_is_permalink", "first_published_at"):
            if new[k] != prev[k]:
                e.add("EPISODE_IDENTITY_CHANGED")
    if prev["state"] == "withdrawn" and new["state"] == "published" and new["change"] != "first-publication":
        pass  # republication after withdrawal keeps identity; allowed only as an explicit decision
    if new["change"] == "audio-replacement" and new["submitted_audio"]["sha256"] == prev["submitted_audio"]["sha256"]:
        e.add("AUDIO_REPLACEMENT_WITHOUT_NEW_AUDIO")
    if new["change"] == "host-migration" and new["guid_source"] != "retained-from-previous-host":
        e.add("MIGRATION_GUID_NOT_RETAINED")
    return sorted(e)


# ---------------------------------------------------------------- independent RSS (INACTIVE reference)
def build_feed(show, episodes):
    """Serialize a podcast RSS document from approved show metadata and episode-publication records.
    Text is escaped by the serializer; nothing is concatenated. Only state=published episodes are emitted,
    newest first. Raises ValueError on identity problems instead of emitting a damaged feed."""
    ET.register_namespace("itunes", ITUNES)
    ET.register_namespace("content", CONTENT)
    rss = ET.Element("rss", {"version": "2.0"})
    ch = ET.SubElement(rss, "channel")
    for tag in ("title", "description", "language"):
        ET.SubElement(ch, tag).text = show[tag]
    ET.SubElement(ch, "link").text = show["website_url"]
    ET.SubElement(ch, f"{{{ITUNES}}}author").text = show["author"]
    ET.SubElement(ch, f"{{{ITUNES}}}image", {"href": show["artwork_url"]})
    cat = ET.SubElement(ch, f"{{{ITUNES}}}category", {"text": show["category"]})
    if show.get("subcategory"):
        ET.SubElement(cat, f"{{{ITUNES}}}category", {"text": show["subcategory"]})
    ET.SubElement(ch, f"{{{ITUNES}}}explicit").text = "true" if show["explicit"] else "false"
    ET.SubElement(ch, f"{{{ITUNES}}}type").text = show["show_type"]
    owner = ET.SubElement(ch, f"{{{ITUNES}}}owner")
    ET.SubElement(owner, f"{{{ITUNES}}}name").text = show["author"]
    ET.SubElement(owner, f"{{{ITUNES}}}email").text = show["public_contact_email"]
    if show.get("new_feed_url"):
        ET.SubElement(ch, f"{{{ITUNES}}}new-feed-url").text = show["new_feed_url"]
    guids, urls = set(), set()
    pub = [e for e in episodes if e["state"] == "published"]
    for ep in sorted(pub, key=lambda e: e["first_published_at"], reverse=True):
        if ep["guid"] in guids:
            raise ValueError("DUPLICATE_GUID")
        enc = ep["observed_enclosure"]
        if enc["url"] in urls:
            raise ValueError("DUPLICATE_ENCLOSURE_URL")
        guids.add(ep["guid"]); urls.add(enc["url"])
        meta = show["episodes"][ep["episode_id"]]
        it = ET.SubElement(ch, "item")
        ET.SubElement(it, "title").text = meta["title"]
        ET.SubElement(it, "description").text = meta["description"]
        ET.SubElement(it, "guid", {"isPermaLink": "true" if ep["guid_is_permalink"] else "false"}).text = ep["guid"]
        ET.SubElement(it, "pubDate").text = ep["first_pubdate_raw"] or utc_to_rfc2822(ep["first_published_at"])
        ET.SubElement(it, "enclosure", {"url": enc["url"], "length": str(enc["declared_length_bytes"]),
                                        "type": enc["declared_type"]})
        secs = ep["submitted_audio"]["duration_ms"] // 1000
        ET.SubElement(it, f"{{{ITUNES}}}duration").text = str(secs)
        ET.SubElement(it, f"{{{ITUNES}}}episodeType").text = ep["episode_type"]
        ET.SubElement(it, f"{{{ITUNES}}}explicit").text = "true" if show["explicit"] else "false"
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="utf-8", xml_declaration=False)


# ---------------------------------------------------------------- media delivery probe
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe_media(url, *, expected_bytes, expected_type, allowed_redirect_hosts=(), timeout=10, max_redirects=5):
    """HEAD + 'Range: bytes=0-1023' GET without credentials. Redirects are followed manually and only to
    allowed hosts. Returns (ok, findings, facts). Never downloads the whole file."""
    opener = urllib.request.build_opener(_NoRedirect)
    findings, facts, chain = [], {}, []
    current = url

    def call(method, extra=None):
        nonlocal current
        for _ in range(max_redirects + 1):
            req = urllib.request.Request(current, method=method, headers={"User-Agent": "feltwillow-probe/0.1", **(extra or {})})
            try:
                resp = opener.open(req, timeout=timeout)
                return resp
            except urllib.error.HTTPError as err:
                if err.code in (301, 302, 303, 307, 308) and err.headers.get("Location"):
                    nxt = urllib.parse.urljoin(current, err.headers["Location"])
                    if _host(nxt) not in allowed_redirect_hosts:
                        findings.append("REDIRECT_TO_UNAPPROVED_HOST")
                        return None
                    chain.append({"status": err.code, "location": nxt})
                    current = nxt
                    continue
                findings.append(f"HTTP_{err.code}")
                return None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                findings.append("UNREACHABLE")
                return None
        findings.append("TOO_MANY_REDIRECTS")
        return None

    head = call("HEAD")
    if head is not None:
        facts["head_status"] = head.status
        ctype = (head.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        clen = head.headers.get("Content-Length")
        facts.update(content_type=ctype, content_length=clen, accept_ranges=head.headers.get("Accept-Ranges"))
        if ctype != expected_type:
            findings.append("CONTENT_TYPE_MISMATCH")
        if clen is None or not clen.isdigit() or int(clen) != expected_bytes:
            findings.append("CONTENT_LENGTH_MISMATCH")
        head.close()
    rng = call("GET", {"Range": "bytes=0-1023"})
    if rng is not None:
        facts["range_status"] = rng.status
        body = rng.read(2048)
        rng.close()
        cr = rng.headers.get("Content-Range") or ""
        m = re.match(r"bytes 0-(\d+)/(\d+)$", cr)
        if rng.status != 206 or not m:
            findings.append("RANGE_NOT_SUPPORTED")
        else:
            if int(m.group(2)) != expected_bytes:
                findings.append("RANGE_TOTAL_MISMATCH")
            if len(body) != int(m.group(1)) + 1:
                findings.append("RANGE_BODY_LENGTH_MISMATCH")
    facts["redirect_chain"] = chain
    facts["final_url"] = current
    return (not findings), sorted(set(findings)), facts


if __name__ == "__main__":
    # CLI: observe a local feed file (no network). Usage: python -m feltwillow_publish.podcast.podcast observe FEED.xml SHOW_ID FEED_URL FETCHED_AT
    if len(sys.argv) == 6 and sys.argv[1] == "observe":
        data = Path(sys.argv[2]).read_bytes()
        stamp = sys.argv[5].replace("-", "").replace(":", "")
        obs_id = f"obs-{stamp[:15]}Z-{hashlib.sha256(data).hexdigest()[:8]}"
        rec = observe_feed(data, show_id=sys.argv[3], feed_url=sys.argv[4], fetched_at=sys.argv[5],
                           observation_id=obs_id, example=False)
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        print("validation:", validate(rec) or "ok", file=sys.stderr)
    else:
        print(__doc__)
