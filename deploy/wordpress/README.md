# WordPress production integration

> **DEFERRED 2026-08-04 (Q60):** source is ready but the plugin has **not**
> been uploaded or activated on production. Reopen only with an authenticated
> `wp-admin` session or a WordPress Application Password stored outside the
> repository. This backlog does not block the control-plane release gate.

`lttstudios.com` is WordPress-owned (Q59). Install the folder
`lttstudios-integration/` as a normal plugin or copy it to `wp-content/mu-plugins/`
and activate it. Do not upload `docs/lttstudios-website/` over `public_html`.

Rollback: deactivate/remove only this plugin. It creates no table, option, post
or user data. The two OAuth callback `.html` files are deliberately untouched.

After activation run:

```powershell
python tools\audit_public_web.py
```

The command must report zero failures before WEB-003 can be accepted.

> **Quy trình đầy đủ để giao cho máy làm web: `KICH_HOAT.md`** (cùng thư mục).
> Có sẵn prompt dán được, kèm baseline đã đo 2026-08-06: **30 FAIL** trước khi
> kích hoạt (29 alias 404 + WordPress login còn lộ ở trang chủ).

## Reopen checklist (`DEFERRED-WP-001`)

1. Back up the WordPress files and database.
2. Package `lttstudios-integration/` as a ZIP and upload/activate it. The source
   folder here is authoritative; any package under `C:\Temp` is disposable.
3. Run `python tools\audit_public_web.py` and require zero failures.
4. Verify desktop and mobile in Playwright: redirects, CTA, layout overflow,
   console errors and failed network requests.
5. Verify that both OAuth callback `.html` URLs are unchanged.

If rollback is needed, deactivate and remove only this plugin, then rerun the
crawler. Never place WordPress credentials in this repository or chat logs.
