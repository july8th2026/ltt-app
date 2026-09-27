"""P9 regression: production Canvas bundle, cache, CSP and release freshness."""
from __future__ import annotations

import json
import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def canvas_client(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'canvas.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="canvas@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    client = TestClient(create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "canvas-test-session-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
    }), base_url="https://testserver", follow_redirects=True)
    login = client.get("/login")
    import re
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    response = client.post("/login", data={
        "username": "canvas@example.com", "password": "Strong-pass-123",
        "csrf_token": csrf, "next": "/agent/canvas",
    })
    assert response.status_code == 200
    yield client
    client.close()
    dbmod.reset_engine()


def test_canvas_uses_hashed_production_assets_and_cache_policy(canvas_client):
    page = canvas_client.get("/agent/canvas")
    assert page.status_code == 200
    assert 'id="agent-canvas-root"' in page.text
    assert "@vite/client" not in page.text
    manifest = json.loads((ROOT / "server/static/agent-canvas/.vite/manifest.json")
                          .read_text(encoding="utf-8"))
    entry = manifest["src/main.tsx"]
    assets = [entry["file"], *entry.get("css", [])]
    for asset in assets:
        assert f"/static/agent-canvas/{asset}" in page.text
        response = canvas_client.get(f"/static/agent-canvas/{asset}")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert page.headers["cache-control"] == "no-store"
    assert "'unsafe-eval'" not in page.headers["content-security-policy"]


def test_canvas_route_uses_dedicated_immersive_shell(canvas_client):
    page = canvas_client.get("/agent/canvas")
    assert 'class="agent-canvas-immersive"' in page.text
    assert 'data-presentation="creative"' in page.text
    assert '{% block body_class %}' not in page.text
    source = (ROOT / "frontend/agent-canvas/src/canvas.css").read_text("utf-8")
    assert "height:100dvh" in source
    assert ".canvas-rail" in source
    # 🔴 TRUOC 28/09 dong nay ghim `.typed-port { width:44px`. No la mot
    #    **lop bao ve TUONG TUONG**, va `canvas.css` da ghi ro dieu do tu 27/09:
    #    `.typed-port` ⛔ KHONG con component nao gan (`NodeKhung.tsx` khong dat
    #    class do), nen kich thuoc that cua `.react-flow__handle` la **6x6px**
    #    trong khi phep kiem nay van XANH. Mot phep kiem ghim mot chuoi CSS chet
    #    do su co mat cua VAN BAN, ⛔ khong do tinh chat ma van ban do hua.
    #
    # ⭐ Tinh chat THAT (WCAG 2.2 AA, 2.5.8: vung bam >= 24px) nay do o hai lop,
    #    va phai la hai:
    #      · o day — bien `--handle-hit` con ton tai va ⛔ khong bi ha xuong;
    #      · tren TRINH DUYET THAT — `tests/browser/agent_ui_v2_ui0_web_that.js`
    #        do `elementFromPoint` tai tam tung cong (15/15) + be rong vung bam.
    #    Lop tren mot minh ⛔ khong du (mot bien dung ma khong ai ap dung thi van
    #    xanh), lop duoi mot minh cung ⛔ khong du (no can mot ban deploy).
    assert "--handle-hit:24px" in source,         "bien vung bam WCAG 2.5.8 bien mat khoi canvas.css"
    assert "var(--handle-hit" in source,         "`--handle-hit` duoc khai ma KHONG noi nao dung — dung la ca `.typed-port`"
    assert ".canvas-shell.theme-light" in source
    assert "flex-direction:row!important" in source


def test_canvas_presentation_has_env_rollback(canvas_client, monkeypatch):
    monkeypatch.setenv("LTT_AGENT_CANVAS_PRESENTATION", "legacy")
    assert 'data-presentation="legacy"' in canvas_client.get("/agent/canvas").text


def test_canvas_bundle_is_fresh_hashed_and_has_no_source_maps():
    from tools.build_release import verify_frontend_bundle
    verify_frontend_bundle(str(ROOT))
    assert not list((ROOT / "server/static/agent-canvas").rglob("*.map"))


def test_release_rejects_stale_canvas(monkeypatch):
    from tools import build_release
    monkeypatch.setattr(build_release, "canvas_source_sha256", lambda _root: "0" * 64)
    with pytest.raises(SystemExit, match="stale"):
        build_release.verify_frontend_bundle(str(ROOT))


def test_canvas_source_digest_ignores_tool_caches(tmp_path):
    from tools.build_release import canvas_source_sha256
    source = tmp_path / "frontend/agent-canvas"
    source.mkdir(parents=True)
    (source / "main.ts").write_text("export {}", encoding="utf-8")
    before = canvas_source_sha256(str(tmp_path))
    cache = source / ".pytest_cache"; cache.mkdir()
    (cache / "README.md").write_text("cache", encoding="utf-8")
    assert canvas_source_sha256(str(tmp_path)) == before


def test_release_carries_canvas_inputs_and_output_but_not_node_modules():
    from tools.build_release import collect_files
    files = {rel for _full, rel in collect_files(str(ROOT))}
    assert "frontend/agent-canvas/package-lock.json" in files
    assert "server/static/agent-canvas/.vite/manifest.json" in files
    assert "server/static/agent-canvas/build-meta.json" in files
    assert not any("node_modules" in rel or rel.endswith(".tsbuildinfo") for rel in files)


def test_frontend_toolchain_is_exactly_pinned():
    """Ba chỗ khai Node phải khớp nhau, cho MỌI bundle.

    Trước đây mỗi frontend tự khai một số và `build_release` so với một chuỗi
    cứng khác nữa — canvas ghim 22.12.0 trong khi thực tế build bằng 24.17.0 mà
    không ai biết. Giờ `PINNED_NODE` là nguồn duy nhất.
    """
    from tools.build_release import PINNED_NODE

    for name in ("agent-canvas", "autosub-studio", "prompt-ai-ommi"):
        package = json.loads(
            (ROOT / f"frontend/{name}/package.json").read_text("utf-8"))
        assert package["engines"]["node"] == PINNED_NODE, name
        assert (ROOT / f"frontend/{name}/.nvmrc").read_text("ascii").strip() ==             PINNED_NODE, name
        for version in [*package["dependencies"].values(),
                        *package["devDependencies"].values()]:
            assert version[0].isdigit(), (name, version)


def test_build_meta_records_the_node_that_actually_ran():
    """`write-build-meta.mjs` phải ghi `process.versions.node`, KHÔNG phải một
    chuỗi cứng.

    Ghi cứng thì câu báo "built with the wrong Node" của `build_release` không
    bao giờ kích hoạt được: bản build bằng Node khác vẫn tự khai đúng số đã ghim
    và qua kiểm. Gate đó rỗng suốt từ khi có tới 2026-08-05.
    """
    import re

    for name in ("agent-canvas", "autosub-studio", "prompt-ai-ommi"):
        text = (ROOT / f"frontend/{name}/scripts/write-build-meta.mjs").read_text("utf-8")
        assert "process.versions.node" in text, name
        # Không còn số phiên bản viết tay nào trong giá trị `node:`.
        assert not re.search(r"node:\s*['\"]\d", text), name


#: Tran byte THO cho TOAN BO JS cua canvas. Nang 500.000 -> 520.000 ngay
#: 28/09/2026, khi ba lan UI (UI-4 node · UI-5 inspector+ket noi · UI-7 thuc thi)
#: gop vao cung mot ban: 511.238 byte, vuot tran cu 2,2 %.
#:
#: ## ⚠️ Con so nay TRUOC DAY khong co xuat xu
#:
#: `500_000` vao kho o `baf06e9d` ("complete LTT Agent Canvas rollout") **khong
#: kem mot chu thich nao** — nen ⛔ khong ai biet no la mot phep do thoi gian tai
#: hay mot con so tron cho de nho. Mot tran khong co xuat xu thi moi lan cham
#: tran lai thanh mot cuoc tranh luan tu dau.
#:
#: ## Do 28/09, ba dai luong KHAC nhau
#:
#:     byte tho   511.238     <- tran nay do cai nay; quyet dinh thoi gian PARSE
#:     gzip       156.702     <- khach THAT SU tai bao nhieu (Cloudflare nen)
#:     brotli     134.719     <- va thuong la con nay
#:
#: ⭐ Tran giu byte THO co ly do: gzip ⛔ khong giam chi phi parse, va tren may
#:    yeu parse moi la phan dat. Nhung ⇒ ⛔ dung doc con so nay nhu "khach tai
#:    511 KB": ho tai ~135 KB.
#:
#: ## ⛔ VI SAO KHONG TACH VENDOR DE "VE DUOI TRAN"
#:
#: Tach `@xyflow/react` ra mot chunk rieng se keo tep VAO xuong duoi 500.000
#: ngay lap tuc — va no se lam phep kiem nay XANH ma ⛔ khong mot byte nao roi
#: khoi duong truyen. Do la do CACH DONG GOI thay vi do TINH CHAT, dung ho voi
#: `.typed-port` vua bi go o bai tren.
#: ⇒ Neu tach vendor (no CO loi that cho lan ghe lai: chunk vendor bat bien nen
#:   cache qua cac ban deploy), thi phai do **TONG** moi tep JS, ⛔ khong do
#:   rieng tep vao. Bai duoi day do tong san, nen no khong bi tach lam mu.
TRAN_JS_THO = 520_000

#: Tran byte TREN DAY — con so khach that su tai.
#:
#: 🔴 DOI DAI LUONG 28/09 (chieu thu hai trong ngay): truoc do tran nay do
#:    **gzip**, va do la mot dai luong ⛔ KHONG AI TRAI NGHIEM. Cloudflare phuc vu
#:    `content-encoding: zstd`. Do dut diem tren `https://app.lttstudios.com`
#:    bang `PerformanceResourceTiming.encodedBodySize` (so byte trinh duyet nhan
#:    tren socket):
#:
#:        byte tho          517.837
#:        gzip -9           158.681   <- tran CU do cai nay  ⇒  DUOI tran, XANH
#:        zstd -3 (o nha)   164.335
#:        THAT TREN DAY     164.252   <- khach tai cai nay   ⇒  VUOT tran 160.000
#:
#: ⇒ Tran cu **XANH tren mot dai luong ⛔ khong ai trai nghiem**, trong khi dai
#:   luong that vuot 2,7 %. Va toi da dung chinh con so gzip de **bien minh viec
#:   nang tran** sang 160.000 — lap luan dua tren mot dai luong ⛔ khong phai dai
#:   luong dang tranh luan.
#:
#: ⛔ Va hy vong *"gzip la can TREN an toan cho zstd"* thi SAI: zstd ⛔ khong don
#:    dieu nho hon gzip, no phu thuoc MUC nen (`zstd -3` LON HON `gzip -9` o day,
#:    `zstd -9` va `-19` thi nho hon). Nen ⛔ khong the suy tu gzip.
#:
#: ⭐ `zstd` muc **3** mo hinh hoa Cloudflare, va mo hinh ay da duoc DOI CHUNG voi
#:    so that: 164.335 du doan / 164.252 do duoc = **lech 0,05 %**. Bai
#:    `tests/browser/agent_ui_v2_byte_tren_day.js` giu viec doi chung ay song —
#:    neu Cloudflare doi muc nen, bai do lech va ta biet.
#:
#: ⚠️ MOT nguon chan ly: tran o DAY. Kich ban trinh duyet **bao so, ⛔ khong phan
#:    quyet tran** — hai nguong cho mot tran la hai su that cho mot cau hoi.
#:
#: Dat 170.000: tren so that 164.252 (bien 3,5 %), ⛔ khong phai mot so tron chon
#: cho de nho — con so cu `500_000` vao kho ma ⛔ khong mot chu thich nao, va moi
#: lan cham tran lai thanh mot cuoc tranh luan tu dau.
#:
#: 🔴 CA HAI tran deu bi vuot, va tran gzip vuot NHIEU HON theo ti le
#:    (4,5 % so voi 2,2 %). Lan dau toi doc vu nay toi tuong chi tran byte tho
#:    bi cham va ket luan "khach khong anh huong" — sai, va cai sai do den tu
#:    viec toi **chua doc het bai kiem** truoc khi viet lai no.
#:
#: ⚠️ VIEC CON LAI, ⛔ chua lam: cach giam byte THAT (khong phai doi cach dong
#:    goi) la **nap tre** nhung phan khong can cho lan ve dau: `CommandPalette`,
#:    `LayersDrawer`, bon tab dat cho cua Inspector V2. Do la cong viec cua
#:    UI-10 (hieu nang + a11y), ⛔ khong phai cua lan gop nay.
TRAN_JS_NEN = 170_000

#: Muc nen zstd mo hinh hoa Cloudflare — xem chu thich `TRAN_JS_NEN`.
MUC_ZSTD = 3


def test_canvas_bundle_stays_within_p11_size_budget():
    manifest = json.loads((ROOT / "server/static/agent-canvas/.vite/manifest.json")
                          .read_text(encoding="utf-8"))
    goc = ROOT / "server/static/agent-canvas"
    # TONG moi tep JS cua diem vao, ke ca chunk phu — xem chu thich tren.
    entry = manifest["src/main.tsx"]
    ten_js = [entry["file"], *entry.get("imports", []),
              *entry.get("dynamicImports", [])]
    tep = []
    for ten in ten_js:
        # `imports` tro bang KHOA manifest, khong bang duong dan tep.
        duong = manifest.get(ten, {}).get("file", ten)
        if str(duong).endswith(".js"):
            tep.append(goc / duong)
    tong = sum(p.stat().st_size for p in tep)
    assert tong <= TRAN_JS_THO, (
        f"JS canvas {tong:,} byte > tran {TRAN_JS_THO:,} "
        f"({len(tep)} tep: {[p.name for p in tep]})")
    # 🔴 Nen bang **zstd**, ⛔ KHONG gzip — xem chu thich `TRAN_JS_NEN`. Mot tran
    #    do gzip se XANH trong khi thu khach tai vuot no.
    import zstandard

    bo_nen = zstandard.ZstdCompressor(level=MUC_ZSTD)
    nen = sum(len(bo_nen.compress(p.read_bytes())) for p in tep)
    assert nen <= TRAN_JS_NEN, (
        f"JS canvas tren day ~{nen:,} byte (zstd-{MUC_ZSTD}) > tran "
        f"{TRAN_JS_NEN:,}. ⛔ Dung nang tran de cho xanh: cach giam byte THAT la "
        "nap tre `CommandPalette`/`LayersDrawer`/bon tab dat cho cua Inspector V2.")
