# GoLuto marketing site

Static landing page for **https://goluto.de**.

Preview locally:

```bash
cd website
python3 -m http.server 4173
```

Then open http://127.0.0.1:4173

## Deploy on Render (Static Site)

1. Push this repo.
2. Render → **New** → **Static Site** → same GitHub repo (`GoLuto-backend`).
3. Settings:
   - **Root Directory:** `website`
   - **Build Command:** *(leave empty)*
   - **Publish Directory:** `.`
4. After deploy, **Settings → Custom Domains** → add `goluto.de`.
5. At GoDaddy DNS add:

| Type | Name | Value |
|------|------|--------|
| A or ALIAS | `@` | follow Render’s root-domain instructions |
| CNAME | `www` | optional; or forward `www` to `goluto.de` in GoDaddy |

Hobby includes 2 custom domains. `api.goluto.de` already uses one, so prefer attaching only `goluto.de` here and forwarding `www` at GoDaddy.

Fill in your name and address on `impressum.html` before going public (required in Germany).
