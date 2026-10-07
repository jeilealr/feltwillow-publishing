"""The v2 checker's 35 self-test mutations (baseline v2 tools/validate_blueprint.py `self_tests`), applied to
the H2 successor of each kind (release.v2, project.v2, web-bundle.v2, approval.v2, publish-plan.v2) or to
the carried v1 kind (rights-review). Each mutation must still be rejected, and the two valid cases accepted."""
from __future__ import annotations

import copy

import yaml

from feltwillow_publish.contracts import cj1
from feltwillow_publish.contracts import validate as V
from feltwillow_publish.contracts.yaml_strict import load_yaml
from support import ROOT, case


def run_v2_selftests():
    def ld(rel):
        return cj1.loads_strict((ROOT / rel).read_bytes())
    r = ld("publishing/examples/release.v2.lion-and-mouse.draft.example.json")
    p = ld("publishing/examples/project.v2.example.json")
    w = ld("publishing/examples/web/render-input/site-set-0002/data/web-bundle.json")
    a = ld("publishing/examples/approval.v2.rejected.example.json")
    plan = ld("publishing/examples/publish-plan.v2.website-preview.example.json")
    rights = ld("tests/fixtures/v2-carried/rights-review.example.json")
    out = []

    def chk(name, passed, got=None):
        out.append(case(name, passed, got=got))

    def ch(orig, fn):
        d = copy.deepcopy(orig)
        fn(d)
        return d

    def rejected(name, rec):
        errs = V.codes(V.validate(rec))
        chk(name, bool(errs), errs)
    chk("01 valid draft example", not V.validate(r), V.validate(r))
    chk("02 safe inactive project requires no credentials", not V.validate(p), V.validate(p))
    rejected("03 unknown field rejected", ch(r, lambda d: d.update({"surprise": True})))
    rejected("04 unsupported schema version rejected", ch(r, lambda d: d.update({"schema_version": 3})))
    rejected("05 release identity mismatch rejected", ch(r, lambda d: d.update({"release_id": "wrong"})))
    rejected("06 reversed age range rejected", ch(r, lambda d: d["content"].update({"age_min": 8, "age_max": 3})))
    rejected("07 path traversal rejected (rights.record_path; v2 sources[] became handoffs)",
             ch(r, lambda d: d["rights"].update({"record_path": "../secrets"})))
    rejected("08 empty path segment rejected", ch(r, lambda d: d["rights"].update({"record_path": "publishing//file.yaml"})))
    rejected("09 missing image reference rejected", ch(r, lambda d: d["content"]["blocks"].append(
        {"type": "image", "asset_id": "absent", "alt": "An illustration", "caption": None})))
    rejected("10 native audio without asset rejected", ch(r, lambda d: d["channels"]["website"].update({"player": "native_audio"})))
    rejected("11 Spotify player without episode rejected", ch(r, lambda d: d["channels"]["website"].update({"player": "spotify_embed"})))
    rejected("12 spec-only module cannot be selected", ch(p, lambda d: d["website"].update({"primary": "astro", "origin": "https://example.invalid"})))
    rejected("13 two enabled websites rejected", ch(p, lambda d: d["modules"].update({"astro": "enabled", "ghost": "enabled"})))
    rejected("14 two feed authorities rejected", ch(p, lambda d: d["modules"].update({"spotify_hosted": "enabled", "independent_rss": "enabled"})))
    rejected("15 unselected feed authority rejected", ch(p, lambda d: (d.update({"podcast_authority": "undecided"}),
                                                                      d["modules"].update({"spotify_hosted": "enabled"}))))
    rejected("16 zero-cost commerce activation rejected", ch(p, lambda d: d.update({"profile_option": "zero_cost", "commerce": "enabled"})))
    rejected("17 approval cannot pass failed check", ch(a, lambda d: d.update({"decision": "approved"})))
    rejected("18 private field in public bundle rejected", ch(w, lambda d: d.update({"api_key": "dummy-nonsecret"})))
    rejected("19 duplicate public page rejected", ch(w, lambda d: d["stories"].append(copy.deepcopy(d["stories"][0]))))
    rejected("20 language path disagreement rejected", ch(w, lambda d: d["stories"][0].update({"language": "de"})))
    rejected("21 public player mismatch rejected", ch(w, lambda d: d["stories"][0]["listening"]["player"].update({"type": "native_audio"})))
    rejected("22 URL with embedded credential rejected", ch(w, lambda d: d.update({"origin": "https://user:secret@example.invalid"})))
    chk("23 example cannot satisfy declarative readiness", "EXAMPLE_RECORD" in V.readiness_errors(r, "podcast"))
    chk("24 missing selected delivery assets detected", any(x.startswith("MISSING_ASSET") for x in V.readiness_errors(r, "podcast")))
    chk("25 pending rights detected", "RIGHTS_NOT_CLEARED" in V.readiness_errors(r, "podcast"))
    chk("26 canonical map ordering stable", cj1.digest({"a": 1, "b": 2}) == cj1.digest({"b": 2, "a": 1}))
    chk("27 content mutation changes digest", cj1.digest(r) != cj1.digest(ch(r, lambda d: d["content"].update({"title": "changed"}))))
    for name, fn in [("28 duplicate YAML keys rejected", lambda: load_yaml("a: 1\na: 2\n")),
                     ("29 duplicate JSON keys rejected", lambda: cj1.loads_strict(b'{"a":1,"a":2}')),
                     ("30 nonfinite canonical number rejected", lambda: cj1.canonical_bytes({"x": float("nan")})),
                     ("31 unsafe YAML tag rejected", lambda: load_yaml('!!python/object/apply:os.system ["echo forbidden"]'))]:
        try:
            fn()
            passed = False
        except (ValueError, yaml.YAMLError):
            passed = True
        chk(name, passed)
    rejected("32 unreviewed rights cannot be marked cleared", ch(rights, lambda d: d.update({"status": "cleared"})))
    rejected("33 unrequested newsletter send rejected", ch(plan, lambda d: d.update({"newsletter_send": True})))
    rejected("34 invalid plan time interval rejected", ch(plan, lambda d: d.update({"expires_at": d["created_at"]})))
    rejected("35 empty production plan rejected", ch(plan, lambda d: d.update({"environment": "production", "actions": []})))
    return out
