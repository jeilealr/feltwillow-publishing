# Ghost theme and publication adapter

**State: spec_only.** No theme build, no adapter, no Ghost site, no credentials.

Choosing this module means a recurring hosting cost (Ghost(Pro) Publisher or higher, because Starter has no
custom themes or Admin API; or a self-hosted server), so there is no zero-cost profile.

Before enabling:
- Pass GH-1 (routing proofs R1–R5) and GH-2…GH-10.
- Members, Portal, comments and newsletters stay disabled.
- The adapter never sends the `newsletter` parameter.
- Remote dashboard edits stop updates with `GHOST_REMOTE_EDIT_CONFLICT`. Resolve each by adopting the edit
  upstream or by an explicit discard decision. Updates never silently overwrite.
