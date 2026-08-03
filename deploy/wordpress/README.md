# WordPress production integration

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
