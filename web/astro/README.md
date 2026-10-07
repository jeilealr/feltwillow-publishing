# Astro renderer

**State: spec_only.** No `package.json` or lockfile exists, so nothing is installed.

When implemented:
- Node ≥ 22.12.0, even major only (check Astro's current requirements and pin at implementation time).
- `package-lock.json` is the only lockfile, installed with `npm ci`.
- `output: 'static'`, no adapter, `trailingSlash: 'always'`, `build.format: 'directory'`.
- No content collections; one typed loader of `data/web-bundle.json`.
- No `astro:assets` processing of bundle media (media must stay byte-identical).
- Gates: WEB-P01…P16, AST-1…AST-4.
