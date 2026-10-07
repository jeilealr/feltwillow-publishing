#!/usr/bin/env python3
"""Strict-zero configuration check (Agent E; integrated as bllt_publish.ops.strict_zero, H2).

    python -m bllt_publish.ops.strict_zero --project <project.json> --services <service-inventory.json>
        [--today YYYY-MM-DD] [--max-evidence-age-days 180] [--report out.json]

Validates a publishing `project` record (v2 project.v1 field set) together with a PROPOSED
`service-inventory` record (E-05 section 1). Fails closed: an unknown capability or provider is an error,
not a pass. Standard library only, offline, writes only --report.

It checks declarations. A passing result does not prove that a provider account has no payment method,
that a free plan still exists, or that nobody enabled a paid add-on in a dashboard: those are owner
observations recorded with a date (proof tasks PT-E10/PT-E11 in E-01).
Exit codes: 0 pass, 1 refused, 2 usage/IO error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# capability -> provider -> plan -> class
#   free             : no charge possible on that plan per the cited docs (still observe the account)
#   free-hard-limit  : free plan whose documented behaviour at the limit is to stop/pause, not to bill
#   refused          : billable, restricted for commercial use, or outside the strict-zero profile
#   owner-infra      : owner's own infrastructure cost (backup storage); declared, never hidden, not counted
CATALOGUE: dict[str, dict[str, dict[str, str]]] = {
    "website-static-host": {
        "cloudflare-pages": {"free": "free"},            # static asset requests free and unlimited [E-C1]
        "netlify": {"free": "free-hard-limit"},           # 300 credits/month, hard limit, no recharge [E-N1]
        "github-pages": {"free": "refused"},              # v2 [H1]: not for online business use
        "vercel": {"hobby": "refused"},                   # v2 [V1]: non-commercial only
    },
    "website-managed-cms": {"ghost-pro": {"*": "refused"}},
    "website-serverless-functions": {"*": {"*": "refused"}},
    "website-custom-domain": {"*": {"*": "refused"}},
    "website-object-storage": {"*": {"*": "refused"}},
    "website-analytics-third-party": {"*": {"*": "refused"}},
    "podcast-host": {"spotify-for-creators": {"free": "free"}, "*": {"*": "refused"}},
    "podcast-media-storage": {"*": {"*": "refused"}},
    "podcast-paid-subscriptions": {"*": {"*": "refused"}},
    "video-platform": {"youtube": {"free": "free"}},
    "newsletter": {"*": {"*": "refused"}},
    "payments": {"*": {"*": "refused"}},
    "memberships": {"*": {"*": "refused"}},
    "email-mailbox-custom-domain": {"*": {"*": "refused"}},
    "ci-hosted-runner": {"github-actions": {"standard": "free-hard-limit", "larger": "refused"}},
    "source-hosting": {"github": {"free": "free", "pro": "refused", "team": "refused"}},
    "backup-cloud-storage": {"onedrive": {"*": "owner-infra"}, "*": {"*": "owner-infra"}},
    "backup-local-disk": {"*": {"*": "owner-infra"}},
}
# Never allowed in a publishing service inventory, in any profile (owner prompt section 11):
PRODUCTION_ONLY = {"tts-api", "image-generation-api", "music-generation-api", "video-generation-compute",
                   "gpu-compute", "llm-api"}
PROVIDER_SUBDOMAIN = re.compile(r"^https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:pages\.dev|netlify\.app)/?$")


def lookup(cap: str, provider: str, plan: str) -> str | None:
    providers = CATALOGUE.get(cap)
    if providers is None:
        return None
    plans = providers.get(provider) or providers.get("*")
    if plans is None:
        return None
    return plans.get(plan) or plans.get("*")


def check(project: dict, inv: dict, today: dt.date, max_age: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    info: list[str] = []
    if inv.get("kind") != "service-inventory" or inv.get("schema_version") != 1:
        errors.append("SERVICE_INVENTORY_INVALID")
        return errors, info
    if project.get("kind") != "project":
        errors.append("PROJECT_INVALID")
        return errors, info
    zero = project.get("profile_option") == "zero_cost"
    if (inv.get("profile") == "strict-zero") != zero:
        errors.append("PROFILE_MISMATCH: project.profile_option vs service-inventory.profile")
    seen = set()
    enabled: dict[str, set[str]] = {}
    for i, s in enumerate(inv.get("services", [])):
        cap, prov, plan, state = s.get("capability"), s.get("provider"), s.get("plan"), s.get("state")
        tag = f"services[{i}] {cap}/{prov}/{plan}"
        if (cap, prov) in seen:
            errors.append("DUPLICATE_SERVICE: " + tag)
        seen.add((cap, prov))
        if state not in ("disabled", "planned", "enabled"):
            errors.append("SERVICE_STATE_INVALID: " + tag)
            continue
        if cap in PRODUCTION_ONLY:
            errors.append("PUBLISHING_HOLDS_PRODUCTION_CAPABILITY: " + tag)
            continue
        cls = lookup(cap, prov, plan)
        if cls is None:
            errors.append("UNKNOWN_CAPABILITY_OR_PROVIDER: " + tag)
            continue
        if state == "disabled":
            continue
        enabled.setdefault(cap, set()).add(prov)
        billing = s.get("billing") or {}
        ev = s.get("evidence") or {}
        if not ev.get("checked_at") or not ev.get("source"):
            errors.append("COST_EVIDENCE_MISSING: " + tag)
        else:
            try:
                age = (today - dt.date.fromisoformat(ev["checked_at"])).days
                if age > max_age or age < 0:
                    errors.append(f"COST_EVIDENCE_STALE: {tag} ({age} days)")
            except ValueError:
                errors.append("COST_EVIDENCE_MISSING: " + tag)
        if cls == "owner-infra":
            info.append("OWNER_INFRA_COST_DECLARED: " + tag)
            continue
        if not zero:
            continue
        if cls == "refused":
            errors.append("ZERO_PROFILE_FORBIDDEN_CAPABILITY: " + tag)
        if billing.get("auto_recharge") is True or billing.get("overage_allowed") is True:
            errors.append("ZERO_PROFILE_OVERAGE_ENABLED: " + tag)
        if cls == "free-hard-limit" and billing.get("payment_method_on_file") is not False:
            # GitHub: "If your account does not have a valid payment method on file, usage is blocked once you
            # use up your quota." [E-G9] With a payment method, the limit is no longer a hard stop.
            errors.append("ZERO_PROFILE_HARD_LIMIT_NOT_PROVEN: " + tag)
    if not zero:
        return errors, info
    # cross-checks against the v2 project record
    mods = project.get("modules", {})
    if mods.get("ghost") == "enabled":
        errors.append("ZERO_PROFILE_FORBIDDEN_CAPABILITY: modules.ghost")
    for k in ("newsletter", "commerce"):
        if project.get(k) == "enabled":
            errors.append("ZERO_PROFILE_FORBIDDEN_CAPABILITY: " + k)
    if project.get("podcast_authority") == "independent" or mods.get("independent_rss") == "enabled":
        errors.append("ZERO_PROFILE_FORBIDDEN_CAPABILITY: independent RSS needs separately hosted media")
    origin = (project.get("website") or {}).get("origin")
    if origin is not None and not PROVIDER_SUBDOMAIN.match(origin):
        errors.append("ZERO_PROFILE_ORIGIN_NOT_PROVIDER_SUBDOMAIN")
    primary = (project.get("website") or {}).get("primary", "none")
    if primary != "none" and "website-static-host" not in enabled:
        errors.append("ZERO_PROFILE_HOST_UNDECLARED")
    if len(enabled.get("website-static-host", ())) > 1:
        errors.append("ZERO_PROFILE_MULTIPLE_HOSTS")
    if mods.get("spotify_hosted") == "enabled" and "spotify-for-creators" not in enabled.get("podcast-host", ()):
        errors.append("ZERO_PROFILE_PODCAST_HOST_UNDECLARED")
    return errors, info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--services", required=True)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--max-evidence-age-days", type=int, default=180)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    try:
        project = json.loads(Path(a.project).read_text(encoding="utf-8"))
        inv = json.loads(Path(a.services).read_text(encoding="utf-8"))
        today = dt.date.fromisoformat(a.today)
    except (OSError, ValueError) as exc:
        print(f"usage/IO error: {type(exc).__name__}", file=sys.stderr)
        return 2
    errors, info = check(project, inv, today, a.max_evidence_age_days)
    rep = {"tool": "strict_zero", "version": "0.1.0-e1", "pass": not errors, "errors": errors, "info": info,
           "note": "declaration check only; provider dashboards must be observed separately"}
    out = json.dumps(rep, indent=1)
    if a.report:
        Path(a.report).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
