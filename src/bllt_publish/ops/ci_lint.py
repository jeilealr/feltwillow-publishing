#!/usr/bin/env python3
"""Offline lint of GitHub Actions workflow files (Agent E; integrated as bllt_publish.ops.ci_lint, H2).

    python -m bllt_publish.ops.ci_lint <workflow.yml>... [--allow-placeholder-pins] [--report out.json]

Encodes the CI rules CI-R1..CI-R12 of E-02 section 4. Requires PyYAML (already pinned for the blueprint
checks); parses with SafeLoader only; offline; writes only --report. It inspects declarations, it does not
prove GitHub's runtime behaviour (proof tasks PT-E04/PT-E05 in E-01).

Workflow classes, decided by file name:
  deploy-*.yml   explicitly approved deployment: workflow_dispatch only, plan digest input, concurrency,
                 the only class that may reference a non-GITHUB_TOKEN secret (and only after the owner moves
                 deployment off the local machine; initially no deploy workflow exists)
  anything else  untrusted/offline checks: read-only token, no secrets, no deploy/import/apply commands
Exit codes: 0 clean, 1 findings, 2 usage/IO error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

FORBIDDEN_TRIGGERS = {"pull_request_target", "workflow_run", "repository_dispatch"}
STANDARD_RUNNERS = {"ubuntu-latest", "ubuntu-24.04", "ubuntu-22.04"}
PIN = re.compile(r"^[^@\s]+@([0-9a-f]{40})$")
UNTRUSTED_EXPR = re.compile(r"\$\{\{\s*(github\.event\.|github\.head_ref|inputs\.|github\.event_name\b.*\|\|)")
PROD_CREDS = re.compile(r"(?i)GEMINI_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY|ELEVENLABS|HF_TOKEN|HUGGING_?FACE"
                        r"|LUMI|SLURM|sbatch|BLLT_REPO\b|big_lessons_little_tales")
SECRET_REF = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)")
DEPLOY_CMD = re.compile(r"(?i)\bbllt[-_]publish\s+(apply|rollback)\b|wrangler\s+pages\s+deploy|netlify\s+deploy")
IMPORT_CMD = re.compile(r"(?i)\bbllt[-_]publish\s+import\b|bllt_publish\.imports|h1_import\.py")
MAX_TIMEOUT = 30


def load(path: Path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader)


def triggers(wf: dict) -> dict:
    on = wf.get("on", wf.get(True))  # YAML 1.1 parses the key `on` as boolean True
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {k: None for k in on}
    return on or {}


def lint(path: Path, allow_placeholder: bool) -> list[str]:
    e: list[str] = []
    try:
        wf = load(path)
    except yaml.YAMLError:
        return ["CI_YAML_INVALID"]
    if not isinstance(wf, dict):
        return ["CI_YAML_INVALID"]
    deploy = path.name.startswith("deploy-")
    text = path.read_text(encoding="utf-8")
    trig = triggers(wf)
    for t in trig:
        if t in FORBIDDEN_TRIGGERS:
            e.append(f"CI-R1_FORBIDDEN_TRIGGER: {t}")
    if deploy and set(trig) != {"workflow_dispatch"}:
        e.append("CI-R2_DEPLOY_NOT_MANUAL_ONLY")
    if deploy:
        inputs = ((trig.get("workflow_dispatch") or {}).get("inputs") or {})
        if "plan_sha256" not in inputs:
            e.append("CI-R2_DEPLOY_WITHOUT_PLAN_DIGEST")
    perms = wf.get("permissions")
    if perms is None:
        e.append("CI-R3_TOP_LEVEL_PERMISSIONS_MISSING")
    elif perms not in ({}, "read-all") and not (isinstance(perms, dict) and set(perms.values()) <= {"read", "none"}):
        e.append("CI-R3_TOP_LEVEL_PERMISSIONS_NOT_READ_ONLY")
    if wf.get("concurrency") is None:
        e.append("CI-R4_CONCURRENCY_MISSING")
    for m in SECRET_REF.finditer(text):
        if m.group(1) != "GITHUB_TOKEN" and not deploy:
            e.append(f"CI-R5_SECRET_IN_NON_DEPLOY_WORKFLOW: {m.group(1)}")
    if PROD_CREDS.search(text):
        e.append("CI-R6_PRODUCTION_CREDENTIAL_OR_COUPLING")
    if IMPORT_CMD.search(text):
        e.append("CI-R7_IMPORT_IN_CI")
    if DEPLOY_CMD.search(text) and not deploy:
        e.append("CI-R7_DEPLOY_COMMAND_IN_NON_DEPLOY_WORKFLOW")
    for jname, job in (wf.get("jobs") or {}).items():
        if not isinstance(job, dict):
            e.append(f"CI_YAML_INVALID: job {jname}")
            continue
        runs_on = job.get("runs-on")
        labels = runs_on if isinstance(runs_on, list) else [runs_on]
        if not labels or any(lbl not in STANDARD_RUNNERS for lbl in labels):
            e.append(f"CI-R8_RUNNER_NOT_STANDARD_HOSTED: {jname}")
        to = job.get("timeout-minutes")
        if not isinstance(to, int) or to > MAX_TIMEOUT:
            e.append(f"CI-R9_TIMEOUT_MISSING_OR_LARGE: {jname}")
        jp = job.get("permissions")
        if isinstance(jp, dict) and "write" in jp.values() and not deploy:
            e.append(f"CI-R3_WRITE_PERMISSION_IN_NON_DEPLOY: {jname}")
        if jp == "write-all":
            e.append(f"CI-R3_WRITE_ALL: {jname}")
        for i, step in enumerate(job.get("steps") or []):
            uses = step.get("uses")
            if uses and not uses.startswith("./"):
                m = PIN.match(uses)
                if not m:
                    e.append(f"CI-R10_ACTION_NOT_SHA_PINNED: {jname}[{i}] {uses}")
                elif set(m.group(1)) == {"0"} and not allow_placeholder:
                    e.append(f"CI-R10_PLACEHOLDER_PIN: {jname}[{i}]")
                if uses.split("@")[0] == "actions/checkout":
                    if (step.get("with") or {}).get("persist-credentials") is not False:
                        e.append(f"CI-R11_CHECKOUT_PERSISTS_CREDENTIALS: {jname}[{i}]")
                if uses.split("@")[0] == "actions/download-artifact":
                    w = step.get("with") or {}
                    if "repository" in w or "github-token" in w:
                        e.append(f"CI-R12_CROSS_REPO_ARTIFACT: {jname}[{i}]")
                    if w.get("digest-mismatch") != "error":
                        e.append(f"CI-R12_ARTIFACT_DIGEST_NOT_ENFORCED: {jname}[{i}]")
            run = step.get("run") or ""
            if UNTRUSTED_EXPR.search(run):
                e.append(f"CI-R13_EXPRESSION_IN_RUN: {jname}[{i}]")
    return e


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--allow-placeholder-pins", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    res = {}
    try:
        for f in a.files:
            res[f] = lint(Path(f), a.allow_placeholder_pins)
    except OSError as exc:
        print(f"IO error: {type(exc).__name__}", file=sys.stderr)
        return 2
    ok = not any(res.values())
    out = json.dumps({"tool": "ci_lint", "version": "0.1.0-e1", "clean": ok, "results": res}, indent=1)
    if a.report:
        Path(a.report).write_text(out + "\n")
    else:
        print(out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
