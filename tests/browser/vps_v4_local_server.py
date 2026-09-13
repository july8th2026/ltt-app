"""Local-only browser fixture. Never imports credentials or uses production DB.

Run this explicitly, then tests/browser/vps_v4_admin.js via Playwright CLI.
Session bootstrap endpoints exist only in this fixture, never in server/app.py.
"""
from pathlib import Path
import os
import secrets
import sys
import tempfile


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    # Remove inherited deployment configuration before any platform imports.
    for name in list(os.environ):
        if name.startswith(("LTT_", "TURNSTILE_")):
            os.environ.pop(name)
    directory = Path(tempfile.mkdtemp(prefix="ltt-vps-v4-browser-"))
    os.environ.update({
        "LTT_ENV": "development", "LTT_VPS": "1", "LTT_VPS_ROLLOUT": "allowlist",
        "LTT_DATABASE_URL": f"sqlite:///{(directory / 'browser-test.db').as_posix()}",
        "LTT_DATA_DIR": str(directory / "data"),
        "LTT_LOGS_DIR": str(directory / "logs"),
        "LTT_SECRETS_DIR": str(directory / "no-production-secrets"),
        "LTT_TEMP_VIDEO_DIR": str(directory / "videos"),
        "LTT_SESSION_SECRET": secrets.token_urlsafe(32),
    })
    from platform_core import db as dbmod, users
    from platform_core.models import User
    from apps.vps.tables import VpsInfrastructureProfile
    from server.app import create_app
    from fastapi import HTTPException, Request
    from fastapi.responses import RedirectResponse
    import uvicorn

    dbmod.reset_engine()
    app = create_app()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    db = next(gen)
    identities = {}
    for kind in ("admin", "customer", "outsider"):
        user = users.tao_nguoi_dung(
            db, email=f"vps-{kind}@test.invalid", password=secrets.token_urlsafe(24),
            is_verified=True)
        if kind == "admin":
            user.role = "admin"
        identities[kind] = user.id
    db.add(VpsInfrastructureProfile(
        id="local-ovh-profile", slug="ovh-local-test", region="sgp",
        name="OVH-SGP-PROD — LOCAL TEST", status="STANDBY",
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH",
        network_config={"gateway_credential_ref": "LTT_OVH_GATEWAY",
                        "mapping_strategy": "ovh_gwnat"}))
    db.commit()
    gen.close()
    os.environ["LTT_VPS_USER_IDS"] = identities["customer"]

    @app.get("/_vps_v4_test/session/{kind}", include_in_schema=False)
    def bootstrap(request: Request, kind: str):
        if kind not in identities:
            raise HTTPException(status_code=404)
        gen = dbmod.get_session()
        db = next(gen)
        try:
            sid = users.tao_phien(db, db.get(User, identities[kind]))
            db.commit()
        finally:
            gen.close()
        request.session.clear()
        request.session["sid"] = sid
        return RedirectResponse("/", status_code=303)

    print(f"LOCAL TEST DATA ONLY: {directory}", flush=True)
    uvicorn.run(app, host="127.0.0.2", port=8100, access_log=False)


if __name__ == "__main__":
    main()
