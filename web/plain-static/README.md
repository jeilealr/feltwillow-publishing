# Plain static renderer

**State: spec_only.** Nothing to install, import, build or deploy.

- **Planned:** `render.py` (Python standard library only, no lockfile); output is a static site artifact.
- **Input:** render-input bundle only (`FELTWILLOW_WEB_BUNDLE`). **Output:** a new directory (`FELTWILLOW_WEB_OUTPUT`).
- **Gates:** WEB-P01…P16, PS-1…PS-4 (escaping, safe-HTML boundary, byte-identical double render, isolation).
- **Proposed** as the first primary renderer on the zero-cost profile (proposal, not a decision).
- The commands appear here only after they have been run and tested.
