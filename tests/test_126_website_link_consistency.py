"""WEB-002: App/Support/Legal/Commerce links share one current contract."""
from __future__ import annotations

import json
from pathlib import Path

from server.templating import PUBLIC_LINKS


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_public_links_match_wordpress_content_contract():
    contract = json.loads((ROOT / "docs/lttstudios-website/wordpress-content-contract.json")
                          .read_text(encoding="utf-8"))
    assert PUBLIC_LINKS == contract["marketing"]
    assert contract["control_plane"] == {
        "catalog": "https://app.lttstudios.com/",
        "login": "https://app.lttstudios.com/login",
        "register": "https://app.lttstudios.com/register",
        "commerce": "https://app.lttstudios.com/nap",
    }


def test_default_legal_links_use_live_pretty_urls_and_callbacks_stay_legacy():
    # ⛔ BO 26/08 — vong lap doc `config.example.json` va `data/config.json`.
    #
    #    `config.example.json` DA XOA o `9bb8f85` (Q108): no la khuon cau hinh
    #    CUA APP socialbot (Meta App ID, Sheet ID, ten cot, chong spam), khong
    #    phai cau hinh nen tang. `data/config.json` la du lieu van hanh, bi
    #    gitignore — mot ban clone moi khong co no, nen mot phep kiem doc no
    #    xanh hay do tuy vao may chay.
    #
    #    Nam khang dinh trong vong lap do noi ve `tiktok_redirect_uri` va
    #    `meta_redirect_uri` — hai truong cua mot san pham khong con ban.
    #
    # ⭐ Phan CON LAI cua phep kiem van dung nguyen gia tri: no chot rang lien
    #    ket phap ly cua WEBSITE khai o mot cho. Do la thu khong di cung
    #    socialbot.
    route_map = json.loads((ROOT / "docs/lttstudios-website/route-map.json")
                           .read_text(encoding="utf-8"))
    callbacks = {rule["production"] for rule in route_map["rules"]
                 if rule["disposition"] == "oauth_callback"}
    assert callbacks == {"/legal/callback.html", "/auth/fb-callback.html"}


def test_all_base_shells_render_the_shared_product_legal_footer():
    partial = (ROOT / "server/templates/_platform_footer.html").read_text(encoding="utf-8")
    assert "Credit &amp; thanh toán" in partial
    assert "public_links.privacy" in partial and "public_links.terms" in partial
    for name in ("base.html", "base_public.html", "base_plain.html"):
        body = (ROOT / "server/templates" / name).read_text(encoding="utf-8")
        assert '{% include "_platform_footer.html" %}' in body
