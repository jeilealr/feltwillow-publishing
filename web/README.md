# Optional website implementations

All web modules are **`spec_only`**. No renderer, `package.json`, lockfile, theme build or deployment exists.

Every renderer reads only the **render-input bundle**:
- `data/web-bundle.json` (web-bundle v2, PROPOSED);
- `media/<sha256>.<ext>`;
- an internal `public-bundle-manifest.v1` with `renderer: null`.

Renderers never read the production repository, `publishing/` records or private state. Exactly one module
may be `enabled`, and it must equal `website.primary`. `implemented` modules may build **local** comparison
previews only.

| Module | Folder | State | Specification |
|---|---|---|---|
| Plain static (stdlib Python) | [plain-static/](plain-static/README.md) | spec_only | website chapter: plain-static |
| Astro (static output, no adapter) | [astro/](astro/README.md) | spec_only | website chapter: Astro |
| Ghost theme + publication adapter | [ghost-theme/](ghost-theme/README.md) | spec_only | website chapter: Ghost |
| Shared tokens, UI strings, screenshot checklist | [shared/](shared/README.md) | spec_only | shared visitor contract |

Population gate:
1. Implement the module in its own folder with its own lockfile (if any).
2. Pass WEB-P01…P14 and the module gates on both shared fixtures.
3. Record `implemented` with the test-report digest.
4. Have the owner approve the configuration (deployment stage, scope `configuration`) before it becomes
   `enabled`.

Unchosen modules need no dependencies or secrets, and none owns the only copy of a story.
