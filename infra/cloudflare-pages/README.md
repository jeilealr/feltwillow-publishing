# Cloudflare Pages: spec-only hosting option

**Not configured.** Planned use:
- A **Direct Upload** project (it cannot later switch to Git integration) on the `*.pages.dev` subdomain.
- Upload of a checked site artifact, either by dashboard (≤1,000 files) or Wrangler (≤20,000 files);
  25 MiB per file.
- No Functions, `_worker.js`, KV/R2/D1 or Access under the zero-cost profile; preflight `ZC_*`.
- Preview deployments are public by default; keep comparison previews local.
- The upload token is owner-held, scoped to Pages, outside Git. Rotation follows the security runbook.
- Rollback: redeploy the kept previous artifact. Dashboard rollback for Direct Upload projects is unproven.
