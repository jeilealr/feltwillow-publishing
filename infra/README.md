# Hosting option specifications

No infrastructure is provisioned: no accounts, projects, tokens, DNS or billing. Choosing a host does not
enable a website module or a podcast authority.

| Host | Folder | Use |
|---|---|---|
| Cloudflare Pages Free (Direct Upload) | [cloudflare-pages/](cloudflare-pages/README.md) | proposed default and strict-zero host |
| Netlify Free | [netlify/](netlify/README.md) | fallback; all team sites pause when credits run out |
| Ghost(Pro) or self-hosted Ghost | [ghost/](ghost/README.md) | only with the Ghost module; recurring cost |

Excluded as free business hosts: GitHub Pages (online-business restriction; the private repo would need a
paid plan) and Vercel Hobby (non-commercial only). Media and feed hosting: see the podcast runbooks
(`independent-media/`, owned by the podcast workstream).
