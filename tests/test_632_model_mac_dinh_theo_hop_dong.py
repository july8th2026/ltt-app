"""
test_632 — Model mặc định của ChatLTT phải là **`ltt_llm`**, và phải đúng vì
một lời khai chứ không vì thứ tự một dict. (H43 Phase 13)

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Giao diện chọn mặc định bằng
   `Object.keys(models)[0]` — phần tử đầu của một `dict`. Nó cho ra `ltt_llm`,
   đúng thứ ta muốn, nhưng đúng một cách **tình cờ**: đảo hai dòng trong
   `apps/ltt_llm/manifest.py` là mặc định lặng lẽ chuyển sang `ltt_llm_vision`.

⛔ Và hậu quả không nhỏ tương xứng với độ nhỏ của nguyên nhân. `ltt_llm_vision`
   có ngữ cảnh **28.262** token, `ltt_llm` có **88.555** — kém hơn ba lần. Mọi
   hội thoại dài của mọi khách sẽ chạm trần sớm gấp ba, và triệu chứng ("hội
   thoại vượt trần ngữ cảnh") không hề trỏ về nguyên nhân (thứ tự khai model).

⭐ Hợp đồng ĐÃ nói mặc định là gì: `input_schema.properties.model.default`.
   Việc phải làm không phải chọn hộ, mà là chuyển câu trả lời đã có tới nơi cần
   nó — và chốt để nó không trôi.
"""
from __future__ import annotations

import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "m.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _text_chat(db):
    from apps.chatltt.services import chinh_sach
    ds = chinh_sach.danh_muc(db, user_id="u-mac-dinh")
    for n in ds:
        if n.ten == "text.chat":
            return n
    pytest.fail("catalog ChatLTT khong con text.chat")


# ── 1. Mặc định là `ltt_llm`, và KHÔNG phải vision ──────────────────────────

def test_mac_dinh_cua_text_chat_la_ltt_llm(db):
    n = _text_chat(db)
    assert n.model_mac_dinh == "ltt_llm"
    assert n.model_mac_dinh != "ltt_llm_vision", (
        "vision co ngu canh 28K thay vi 89K — no khong bao gio duoc lam mac dinh "
        "cho chat, ke ca khi no duoc quang cao trong danh sach")


def test_mac_dinh_nam_trong_danh_sach_model_duoc_mo(db):
    """Một mặc định không có trong `models` là một ô chọn trống."""
    n = _text_chat(db)
    assert n.model_mac_dinh in n.models


# ── 2. Nó đến từ HỢP ĐỒNG, không từ thứ tự dict ─────────────────────────────

def test_khong_lay_phan_tu_dau_cua_dict(db, monkeypatch):
    """Đảo thứ tự khai thì mặc định **không** được đổi theo.

    Đây là toàn bộ lý do trường `model_mac_dinh` tồn tại. Nếu phép kiểm này
    xanh mà không có trường đó thì nó đang đo may mắn.
    """
    from platform_core.runtime_noi_bo import danh_muc as DM

    class _PT:
        description = "x"
        input_schema = {"properties": {"model": {"default": "ltt_llm"}}}

    # `models` đảo thứ tự: vision đứng TRƯỚC.
    dao = {"ltt_llm_vision": {}, "ltt_llm": {}}
    assert next(iter(dao)) == "ltt_llm_vision"          # tiền đề của phép kiểm
    assert DM._mac_dinh(_PT(), dao) == "ltt_llm"


def test_hop_dong_cam_thi_lui_ve_phan_tu_dau_chu_khong_tra_rong():
    """Lưới đỡ: một năng lực chưa khai `default` vẫn phải mở được ô chọn."""
    from platform_core.runtime_noi_bo import danh_muc as DM

    class _KhongKhai:
        input_schema = {"properties": {}}

    assert DM._mac_dinh(_KhongKhai(), {"a": {}, "b": {}}) == "a"
    assert DM._mac_dinh(_KhongKhai(), {}) == ""


def test_default_tro_toi_alias_khong_ton_tai_thi_khong_dung(db):
    """Một `default` sai chính tả không được biến ô chọn thành rỗng."""
    from platform_core.runtime_noi_bo import danh_muc as DM

    class _Sai:
        input_schema = {"properties": {"model": {"default": "ltt_llm_go_nham"}}}

    assert DM._mac_dinh(_Sai(), {"ltt_llm": {}, "ltt_llm_vision": {}}) == "ltt_llm"


# ── 3. Hai đầu dây phải khớp nhau ───────────────────────────────────────────

def test_manifest_khai_dung_ltt_llm_lam_default():
    """Nguồn của sự thật: chính `apps/ltt_llm/manifest.py`."""
    from apps.ltt_llm.manifest import MANIFEST

    for tool in MANIFEST.tools:
        if tool.name != "text.chat":
            continue
        # ⚠️ Khai o `params_schema`, KHONG o `api_contract`. `api_contract` la
        #    ban CHIEU cong khai va no duoc `project_tool` sinh ra TU day —
        #    nen doc `params_schema` la doc nguon, doc `api_contract` la doc
        #    mot ban sao co the vang mat truong nay.
        model = (tool.params_schema or {}).get("model") or {}
        assert model.get("default") == "ltt_llm", (
            "params_schema cua text.chat phai khai `ltt_llm` lam default")
        assert "ltt_llm_vision" in (model.get("values") or []), (
            "vision van phai duoc MO — no chi khong duoc lam mac dinh")
        return
    pytest.fail("khong tim thay tool text.chat trong manifest ltt_llm")


def test_route_danh_muc_tra_ve_truong_model_mac_dinh():
    """Trường có ở phép chiếu mà route không trả ra thì giao diện vẫn đoán mò."""
    nguon = (GOC / "apps" / "chatltt" / "routes" / "_p_trang.py").read_text(
        encoding="utf-8")
    assert '"model_mac_dinh"' in nguon


def test_giao_dien_uu_tien_model_mac_dinh_hon_thu_tu_dict():
    app_tsx = (GOC / "frontend" / "chatltt" / "src" / "App.tsx").read_text(
        encoding="utf-8")
    assert "model_mac_dinh" in app_tsx, (
        "App.tsx phai doc `model_mac_dinh`; `Object.keys(models)[0]` chi con la "
        "luoi do khi may chu cu chua co truong nay")
    i_moi = app_tsx.index("model_mac_dinh")
    i_cu = app_tsx.index("Object.keys(text?.models")
    assert i_moi < i_cu, "phai thu `model_mac_dinh` TRUOC roi moi lui ve thu tu dict"


def test_bundle_da_dung_lai_sau_khi_doi_App():
    """Sửa `App.tsx` mà quên `npm run build` thì người dùng nhận bản cũ.

    ⭐ Phép kiểm này đọc **bundle đã build**, không đọc mã nguồn — đó là thứ
       trình duyệt thật sự tải.
    """
    thu_muc = GOC / "server" / "static" / "chatltt" / "assets"
    js = sorted(thu_muc.glob("main-*.js"))
    assert js, "chua build bundle chatltt"
    noi_dung = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in js)
    assert "model_mac_dinh" in noi_dung, (
        "bundle chua co `model_mac_dinh` — chay `npm run build` trong frontend/chatltt")


def test_manifest_va_hop_dong_khong_lech_nhau(db):
    """Con số ngữ cảnh phải nói cùng một chuyện ở cả hai chỗ."""
    n = _text_chat(db)
    rang_buoc = (n.models.get("ltt_llm") or {}).get("constraints") or {}
    rb_vision = (n.models.get("ltt_llm_vision") or {}).get("constraints") or {}
    assert rang_buoc.get("context_window", 0) > rb_vision.get("context_window", 0), (
        "gia dinh cua phep kiem nay: `ltt_llm` co ngu canh LON hon vision. Neu "
        "dieu do doi thi ly do chon mac dinh cung phai duoc xem lai, "
        "khong chi doi con so.")
    assert json.dumps(n.hop_dong)  # hợp đồng phải serialise được cho giao diện
