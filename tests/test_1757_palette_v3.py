"""Spec §13.1/§13.4 — MỘT đường palette, sinh từ registry, kèm luật nối dây."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    # Bang RIENG cua app (`apps/<slug>/tables.py`) — nap y het production
    # (`registry.load_app_tables`), khong go ten mot app cu the. Palette giai
    # `ToolSpec.tuy_chon_dong` nen no THAT SU doc bang cua app (vd
    # `voice_profile`); thieu chung thi route 500 va bai kiem noi doi ve
    # nguyen nhan.
    from platform_core import registry as _reg
    _reg.load_app_tables()
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="palette@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "palette-v3-test-session",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "palette@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
    yield client
    client.close(); dbmod.reset_engine()


def test_palette_can_dang_nhap(api):
    from fastapi.testclient import TestClient as TC
    khach = TC(api.app, base_url="https://testserver", follow_redirects=False)
    assert khach.get("/agent/api/v3/palette").status_code in (302, 303, 401, 403)
    khach.close()


def test_palette_nhom_theo_category_dung_thu_tu(api):
    from platform_core.workflow import nut
    body = api.get("/agent/api/v3/palette").json()
    assert body["phien_ban"] == 3
    ten_nhom = [n["category"] for n in body["nhom"]]
    assert ten_nhom == [c for c in nut.CATEGORY if c in ten_nhom]
    assert "TRIGGERS" in ten_nhom and "LTT_APPS" in ten_nhom


def test_moi_node_mang_du_thong_tin_the_palette(api):
    body = api.get("/agent/api/v3/palette").json()
    apps = next(n for n in body["nhom"] if n["category"] == "LTT_APPS")["nut"]
    nd = next(x for x in apps if x["type"] == "app.transcript.run")
    assert nd["type_version"] == 1 and nd["kind"] == "app"
    assert nd["title"] and nd["description"] and nd["app_name"]
    assert nd["gia"] == {"kieu": "theo_registry", "so": 0,
                         "job_type": "transcript.run"}
    assert nd["resource"]["class"] == "gpu"
    assert {"ten": "audio", "kieu": "audio", "bat_buoc": True,
            "nhieu": False} in nd["cong_vao"]
    assert {"ten": "transcript", "kieu": "json", "bat_buoc": True,
            "nhieu": False} in nd["cong_ra"]
    assert nd["tham_so"]["type"] == "object"
    assert nd["publish_duoc"] is True


def test_node_loi_chua_publish_duoc_thi_bao_ra_chu_khong_giau(api):
    """⭐ Nâng 24/09: nhóm TRIGGERS nay có thêm trigger POLLING của piece.

    Phase gốc 8 đưa `trigger.piece.google_sheets.new_spreadsheet` lên palette,
    và nó nằm ở **TRIGGERS** chứ không ở CONNECTORS — đúng chủ đích: một
    trigger là **điểm bắt đầu** đồ thị, đặt nó vào CONNECTORS thì người soạn
    tìm mọi trigger khác ở một chỗ và không thấy nó ở đó.

    ⛔ Hai chỗ bản cũ mong manh, sửa cả hai:
      - chốt **danh sách theo thứ tự** ⇒ vỡ khi thêm một mục;
      - đọc `trig[0]` ⇒ khẳng định về `publish_duoc` **trượt sang mục khác**
        khi thứ tự đổi, mà vẫn XANH. Nay chốt **theo tên**, không theo chỉ số.

    🔴 SỬA 25/09 (lan wfp, plan 08): `trigger.piece.*` đã publish_duoc được
       (xem `test_3503_wf_connector_catalog.py::
       test_node_piece_publish_duoc_tu_25_09_lan_wfp`) — chỉ `trigger.manual`
       (node LÕI thật, chưa có phần thi hành `inline`, khác hẳn piece) còn
       khoá. Bài này giờ chốt CẢ HAI trạng thái, mỗi cái đúng tên của nó,
       ⛔ không còn gộp chung một khẳng định `False` cho mọi phần tử.
    """
    body = api.get("/agent/api/v3/palette").json()
    trig = next(n for n in body["nhom"] if n["category"] == "TRIGGERS")["nut"]
    theo_ten = {x["type"]: x for x in trig}
    # ⭐ 25/09 (vong P-C): them 3 piece POLLING that (google-drive, gmail,
    #    notion) canh google-sheets — xem allowlist.json `palette`.
    assert set(theo_ten) == {
        "trigger.manual",
        "trigger.piece.google_sheets.new_spreadsheet",
        "trigger.piece.google_drive.new_file",
        "trigger.piece.google_drive.new_folder",
        "trigger.piece.google_drive.new_or_updated_file",
        "trigger.piece.gmail.gmail_new_email_received",
        "trigger.piece.notion.new_database_item",
    }
    # ⭐ 28/09/2026 (Q11): `trigger.manual` `False` -> `True`. Nay CA BAY trigger
    #    publish được, nên nhóm TRIGGERS ⛔ không còn một ví dụ `False` nào.
    for ten, x in theo_ten.items():
        assert x["publish_duoc"] is True, ten

    # 🔴 Mệnh đề *"node chưa publish được thì palette KHAI RA, ⛔ không giấu đi"*
    #    ĐÃ CHUYỂN sang `test_palette_KHAI_RA_node_chua_publish_duoc` ở dưới —
    #    đúng thứ tự tác giả bản 25/09 dặn: *chuyển trước khi xoá*.
    #
    # ⚠️ Vì sao phải chuyển: bản cũ lấy nhân chứng từ **registry thật**, và
    #    28/09/2026 ba node `ai.*` được mở (plan 10) ⇒ registry ⛔ không còn một
    #    node `False` nào, nên bài đỏ với thông điệp *"mất nhân chứng"*. Nó ⛔
    #    KHÔNG báo một lỗi sản phẩm: nó báo rằng **phép đo đã hết vật đo**.
    #
    # ⭐ Bài mới ⛔ không chờ kho có sẵn một node chưa mở — nó **tiêm** một node
    #    giả. Một bất biến phụ thuộc vào việc *"tình cờ còn ai đó chưa xong"* là
    #    một bất biến sẽ tự tắt đúng vào ngày mọi thứ xong.


def test_palette_KHAI_RA_node_chua_publish_duoc(api, monkeypatch):
    """**Node chưa publish được thì palette KHAI RA, ⛔ không giấu đi.**

    🔴 Vì sao bất biến này đáng một bài riêng: nếu palette **lọc** theo
       `publish_duoc`, người soạn tìm một bước họ cần và thấy nó ⛔ không tồn tại —
       ⛔ không thông điệp, ⛔ không lý do. Một cửa **khoá** còn nói được *"chưa
       mở"*; một cửa **bị xoá khỏi bản đồ** thì ⛔ không nói gì cả.

    ⭐ Node giả, ⛔ KHÔNG dùng nhân chứng thật trong registry. Bản 25/09 lấy nhân
       chứng thật và bài tự tắt ngày 28/09 khi ba node `ai.*` mở — tức phép đo hết
       **vật đo**, chứ ⛔ không phải sản phẩm hết lỗi. Một bất biến ⛔ không được
       phụ thuộc vào việc *"tình cờ còn ai đó chưa xong"*.

    ⚠️ Tiêm bằng `monkeypatch` vào bản sao registry, ⛔ KHÔNG gọi `dang_ky` thật:
       `dang_ky` ghi vào một dict cấp module, nên nó rỉ sang mọi bài chạy sau
       trong cùng tiến trình — và dưới `-n` thì rỉ sang một tập bài **khác nhau
       mỗi lượt**, tức một bài đỏ ⛔ không tái hiện được.
    """
    from platform_core.workflow import nut as _nut
    from platform_core.workflow.nut import NodeDefinition

    # ⚠️ Patch `platform_core.workflow.nut.tat_ca`, ⛔ KHÔNG `nut_loi.tat_ca`.
    #    Lần đầu tôi nhắm `nut_loi` và **vế đối chứng ở dưới đã bắt được** —
    #    `palette_v3` gọi `nut.tat_ca(cong_cu=...)` (ba nguồn: node lõi + piece +
    #    ToolSpec), còn `nut_loi.tat_ca` chỉ là MỘT trong ba nguồn ấy.
    #
    # ⭐ Đó đúng là việc của vế đối chứng: nếu ⛔ không có nó, bài này đã XANH với
    #    một phép tiêm ⛔ không tới được route — tức đo một cửa ⛔ không có xe.
    GIA = "core.node_gia_chua_mo"
    nd_gia = NodeDefinition(
        type=GIA, type_version=1, kind="control", category="FLOW",
        title="Node giả chưa mở", description="chỉ dùng trong test",
        icon="?", cong_vao=(), cong_ra=(),
        tham_so={"type": "object", "properties": {}, "required": [],
                 "additionalProperties": False},
        thi_hanh="inline", publish_duoc=False)

    that = _nut.tat_ca

    def co_ca_node_gia(*a, **k):
        ra = dict(that(*a, **k))
        ra[GIA] = nd_gia
        return ra

    monkeypatch.setattr(_nut, "tat_ca", co_ca_node_gia)

    body = api.get("/agent/api/v3/palette").json()
    moi_nut = {x["type"]: x for nhom in body["nhom"] for x in nhom["nut"]}

    # ⛔ Vế ĐỐI CHỨNG trước: nếu phép tiêm ⛔ không tới được route thì bài dưới
    #    xanh mà ⛔ không đo gì — đúng bẫy "fixture tự dựng tiền đề sản phẩm không
    #    có", chỉ là chiều ngược lại.
    assert GIA in moi_nut, (
        "phep tiem KHONG toi duoc route (palette doc registry qua mot duong khac?) "
        "⇒ bai nay chua do duoc gi. Kiem `palette_v3` lay `nut_loi.tat_ca` o dau.")
    assert moi_nut[GIA]["publish_duoc"] is False, (
        "palette bao node gia la publish duoc — no ⛔ khong doc `nd.publish_duoc`")


def test_khong_lo_job_type_noi_bo_cua_provider(api):
    # `gia.job_type` la lan cua NEN TANG, khong phai ten provider — nhung
    # `api_contract`, `sync_executor`, `admission_*` thi KHONG duoc ra ngoai.
    tho = api.get("/agent/api/v3/palette").text
    for cam in ("sync_executor", "api_contract", "admission_token_pool",
                "kiem_truoc", "tuy_chon_dong"):
        assert cam not in tho
    # 🔑 DOI CHUNG (fix round 1): sau bon dong `assert ... not in`, mot route
    #    tra `{}` cung XANH. Neo lai mot chuoi PHAI co mat — `x-ltt-dong` la
    #    marker trung lap thay cho ten co che noi bo, va `app.video.generate`
    #    (taovideo) co `depends_on` nen no phai xuat hien that.
    assert "x-ltt-dong" in tho and "app_property" in tho


def test_luat_noi_day_la_CUNG_mot_bang_voi_he_kieu(api):
    from platform_core.workflow import he_kieu
    body = api.get("/agent/api/v3/luat-noi-day").json()
    assert body == he_kieu.xuat_luat_noi_day()
    # 🔑 DOI CHUNG (fix round 1): `{} == {}` cung XANH. Bang luat phai co noi
    #    dung that thi phep so sanh moi noi duoc dieu gi.
    assert body["cap_noi_duoc"] and body["kieu"]
    # Palette nhung san cung bang => Canvas chi can MOT luot goi khi mo trang.
    assert api.get("/agent/api/v3/palette").json()["luat_noi_day"] == body


def test_palette_loc_theo_quyen_app_cua_nguoi_dung(api, monkeypatch):
    from platform_core import app_access
    monkeypatch.setattr(app_access, "muc_quyen",
                        lambda db, user, slug: app_access.ENABLED
                        if slug != "transcript" else "")
    apps = next(n for n in api.get("/agent/api/v3/palette").json()["nhom"]
                if n["category"] == "LTT_APPS")["nut"]
    assert "app.transcript.run" not in {x["type"] for x in apps}


# ─────────────────────────── Fix round 1 (Task 8) ───────────────────────────

#: Cong cu app CO TINH khai `customer_visible=False` — cua dong TAY vi chua
#: nghiem thu E2E (`apps/audio_pause/manifest.py:73-87`). Duong v2 loc chung o
#: `presentationAdapter.ts:65`; duong v3 phai loc o server.
KHONG_CHO_KHACH = ("app.audio_pause.run", "app.prompt_canh.run",
                   "app.video_assembly.run", "app.chatltt.trich_tep",
                   "app.chatltt.nghien_cuu")


def test_palette_khong_lo_cong_cu_customer_visible_false(api):
    body = api.get("/agent/api/v3/palette").json()
    co_mat = {x["type"] for n in body["nhom"] for x in n["nut"]}
    for ten in KHONG_CHO_KHACH:
        assert ten not in co_mat, f"{ten} customer_visible=False ma van len palette"
    # 🔑 DOI CHUNG: mot bo loc chan SACH cung lam bon dong tren xanh. Palette
    #    phai con dung nhung node that — 12 node app deu duoc ra mat.
    apps = {x["type"] for n in body["nhom"]
            if n["category"] == "LTT_APPS" for x in n["nut"]}
    assert len(apps) >= 10 and "app.transcript.run" in apps
    assert "app.speech.ltt" in apps


def _thamso(api, ten: str) -> dict:
    body = api.get("/agent/api/v3/palette").json()
    nd = next(x for n in body["nhom"] for x in n["nut"] if x["type"] == ten)
    return nd["tham_so"]["properties"]


def test_tuy_chon_dong_duoc_GIAI_chu_khong_ra_o_chu_tu_do(api):
    """GENERIC_GAP D10: `voice_id`/`preset` la enum THEO NGUOI DUNG.

    Khong goi `resolve_params_schema(db=, user_id=)` thi ca hai ra
    `{"type": "string", "maxLength": N}` — dung cai o chu tu do ma D10 sinh ra
    de dong (`docs/CHATLTT/reports/02_runtime_noi_bo.md:38`).
    """
    p = _thamso(api, "app.speech.ltt")
    # Kho DUNG CHUNG cua nen tang: luon co 20 giong, khong phu thuoc tai khoan.
    assert "enum" in p["preset"], f"preset van la o chu tu do: {p['preset']}"
    assert len(p["preset"]["enum"]) >= 1
    assert p["preset"]["x-ltt-nhan"]
    # Giong NHAN BAN cua chinh nguoi dung: tai khoan test chua nhan ban giong
    # nao ⇒ enum RONG. Phep kiem phan biet "enum rong" (co khoa, list rong)
    # voi "chuoi tu do" (khong co khoa `enum`) — day moi la cai khe D10 do.
    assert "enum" in p["voice_id"], f"voice_id van la o chu tu do: {p['voice_id']}"
    assert isinstance(p["voice_id"]["enum"], list)


def test_resource_chi_tra_khoa_phan_loai_khong_tra_so_lieu_ha_tang(api):
    """Sức chứa GPU khong phai thong tin cua khach dang nhap."""
    tho = api.get("/agent/api/v3/palette").text
    for cam in ("vram_min_mb", "slots", "est_duration_s"):
        assert cam not in tho, f"palette lo so lieu ha tang: {cam}"
    # 🔑 DOI CHUNG: bo SACH khoi `resource` cung lam ba dong tren xanh —
    #    `class` la khoa Canvas that su can de phan loai node.
    body = api.get("/agent/api/v3/palette").json()
    nd = next(x for n in body["nhom"] for x in n["nut"]
              if x["type"] == "app.transcript.run")
    assert nd["resource"] == {"class": "gpu"}


# ───────────── Fix round 2 (Task 8) — palette la CATALOGUE, khong phai giao dich ──

#: Tool DUY NHAT trong cay nay khai tham chieu dong (`apps/ltt_voice/manifest.py:359`)
#: — no la cho MOT app co the nem loi luc giai tuy chon.
_REF_HONG = "apps.ltt_voice.tham_chieu:tuy_chon_voice_id"
#: Chuoi NOI BO co y nhet vao thong bao loi: no ra toi trinh duyet = ro thong tin.
_RO = r"D:\LTTSTUDIOSAPP\secrets\kho_giong.py:42 (bien _speaker_embedding)"


@pytest.fixture()
def api_mot_app_hong(api, monkeypatch):
    """Callable `ToolSpec` dong cua MOT app nem loi; cac app khac nguyen ven."""
    from platform_core.agent import tools as _tools
    that = _tools.tai_tham_chieu

    def gia(ref):
        if ref == _REF_HONG:
            raise RuntimeError(f"CSDL giong sap: {_RO}")
        return that(ref)

    monkeypatch.setattr(_tools, "tai_tham_chieu", gia)
    return api


def test_mot_app_hong_khong_lam_sap_ca_palette(api_mot_app_hong):
    """Palette la CATALOGUE: mot muc hong khong duoc giet ca quyen sach."""
    r = api_mot_app_hong.get("/agent/api/v3/palette")
    assert r.status_code == 200, r.text[:400]
    co_mat = {x["type"] for n in r.json()["nhom"] for x in n["nut"]}
    assert "app.speech.ltt" in co_mat, "node hong bi giau thay vi bao ra"
    # 🔑 DOI CHUNG: mot ban va tra palette RONG cung "khong 500". Cac node khac
    #    phai con NGUYEN VEN thi phep kiem nay moi noi duoc dieu gi.
    assert "app.transcript.run" in co_mat and "trigger.manual" in co_mat
    assert len([t for t in co_mat if t.startswith("app.")]) >= 10


def test_node_hong_mang_dau_doc_duoc_tren_truong_bi_anh_huong(api_mot_app_hong):
    body = api_mot_app_hong.get("/agent/api/v3/palette").json()
    nd = next(x for n in body["nhom"] for x in n["nut"]
              if x["type"] == "app.speech.ltt")
    props = nd["tham_so"]["properties"]
    for truong in ("voice_id", "preset"):
        assert props[truong].get("x-ltt-loi"), f"{truong} thieu dau loi doc duoc"
    assert nd.get("x-ltt-loi"), "node thieu dau loi o muc node"
    # Truong khong dinh toi lua chon dong thi khong bi danh dau oan.
    assert "x-ltt-loi" not in props["text"]
    # Va luoc do TINH van con: form khong duoc rong di.
    assert props["text"]["type"] == "string" and props["language"]["enum"]


def test_node_khac_khong_bi_danh_dau_oan(api_mot_app_hong):
    body = api_mot_app_hong.get("/agent/api/v3/palette").json()
    for n in body["nhom"]:
        for x in n["nut"]:
            if x["type"] == "app.speech.ltt":
                continue
            assert "x-ltt-loi" not in x, f"{x['type']} bi danh dau oan"
            ban = [k for k, v in x["tham_so"]["properties"].items()
                   if "x-ltt-loi" in v]
            assert not ban, f"{x['type']} truong {ban} bi danh dau oan"


def test_dau_loi_la_MA_NGAN_chu_khong_phai_traceback(api_mot_app_hong):
    """Chi tiet loi thuoc ve log may chu, khong thuoc ve moi tai khoan dang nhap."""
    tho = api_mot_app_hong.get("/agent/api/v3/palette").text
    for cam in ("Traceback", "RuntimeError", "LTTSTUDIOSAPP", "kho_giong",
                "_speaker_embedding", "CSDL giong sap", "tham_chieu",
                "tuy_chon_voice_id"):
        assert cam not in tho, f"palette ro thong tin noi bo: {cam}"
