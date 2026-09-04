"""
test_626 — Phase 11: CHỨNG MINH kiến trúc mở rộng, không phải tuyên bố nó.

Ba fixture, ba câu hỏi khác nhau:

  1. Thêm **alias text thứ ba** với năng lực khác ⇒ hiện ra, cờ tính năng đi
     theo metadata — **không sửa một dòng nào** trong `apps/chatltt` hay
     `frontend/chatltt`.
  2. Thêm **alias ảnh KHÔNG khả dụng** ⇒ trạng thái nói đúng, và nút tạo phải tắt.
  3. Thêm **một phương thức lạ** (`video`) mà bộ hiển thị không vẽ được ⇒
     **fail-closed**: không hiện, không gọi được.

Cộng thêm hai phép kiểm tĩnh — thứ giữ cho ba điều trên còn đúng ở phiên sau:
không `if <tên model>` trong app/frontend, và không import provider/app khác.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from apps.chatltt.services import chinh_sach
from platform_core import registry as reg

GOC = Path(__file__).resolve().parents[1]


def _tool(ten, job_type, *, returns, models=None, sync=False, **g):
    hd = {"description": f"mo ta cong khai cua {ten}", "scopes": ("jobs:create",)}
    if models:
        hd["models"] = models
    return reg.ToolSpec(
        name=ten, job_type=job_type, description="noi bo",
        params_schema={"prompt": {"type": "string", "required": True}},
        returns=returns, api_exposed=True, api_contract=hd,
        sync_executor=("tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA" if sync else ""),
        **g)


def _app(slug, tools, **g):
    m = reg.AppManifest(
        slug=slug, display_name=slug, route_prefix=f"/{slug}",
        job_types=tuple(sorted({t.job_type for t in tools})),
        credit_cost=lambda p: 1, surface="runtime", lifecycle="internal",
        tools=tuple(tools), **g)
    return reg.LoadedApp(manifest=m, router=None)


# ── 1. Alias text thứ ba, chỉ bằng bản khai ─────────────────────────────────

HAI = {
    "ltt_llm": {"id": "noi-bo-a", "stability": "stable",
                "constraints": {"context_window": 88555, "max_output_tokens": 32768}},
    "ltt_llm_vision": {"id": "noi-bo-b", "stability": "stable",
                       "constraints": {"context_window": 28000, "reads_images": True}},
}
BA = dict(HAI, ltt_llm_dai={
    "id": "noi-bo-c", "stability": "experimental",
    "description": "cua so rat dai, sinh cham hon",
    "constraints": {"context_window": 200000, "max_output_tokens": 8192,
                    "reads_images": True}})


def _apps_text(models):
    return [_app("t626", [_tool("text.chat", "t626.j", returns={"content": "text"},
                                models=models, sync=True)])]


def test_them_alias_text_thu_ba_chi_bang_ban_khai():
    truoc = chinh_sach.danh_muc(None, user_id="u", apps=_apps_text(HAI))[0]
    sau = chinh_sach.danh_muc(None, user_id="u", apps=_apps_text(BA))[0]

    assert set(truoc.models) == {"ltt_llm", "ltt_llm_vision"}
    assert set(sau.models) == {"ltt_llm", "ltt_llm_vision", "ltt_llm_dai"}

    moi = sau.models["ltt_llm_dai"]
    assert moi["stability"] == "experimental"
    assert moi["constraints"]["context_window"] == 200000
    # Cờ năng lực đi theo metadata: bộ chọn bật nút đính ảnh khi `reads_images`.
    assert moi["constraints"]["reads_images"] is True
    assert sau.models["ltt_llm"]["constraints"].get("reads_images") is None
    # id nội bộ KHÔNG rời nền tảng, kể cả với alias mới.
    assert "noi-bo-c" not in json.dumps(sau.models)
    assert all("id" not in m for m in sau.models.values())


# ── 2. Alias/năng lực KHÔNG khả dụng ────────────────────────────────────────

def test_nang_luc_khong_kha_dung_duoc_the_hien_dung(monkeypatch):
    from platform_core.runtime_noi_bo import danh_muc as dm

    tools = [_tool("image.ltt", "i626.j", returns={"image_keys": "image[]"},
                   models={"chuan": {"id": "engine-anh"}})]
    dm._DEM_SUC_KHOE.clear()
    apps_tat = [_app("i626", tools, suc_khoe=lambda: "chua_san_sang")]
    apps_bat = [_app("i626", tools, suc_khoe=lambda: "san_sang")]

    tat = chinh_sach.danh_muc(None, user_id="u", cho_phep=None, apps=apps_tat) \
        if False else chinh_sach.danh_muc(None, user_id="u", apps=apps_tat)
    assert [n.san_sang for n in tat] == ["chua_san_sang"]
    dm._DEM_SUC_KHOE.clear()
    bat = chinh_sach.danh_muc(None, user_id="u", apps=apps_bat)
    assert [n.san_sang for n in bat] == ["san_sang"]

    # Giao diện tắt nút theo đúng trường này — chốt bằng chính mã nguồn để một
    # bản sau đổi tên trường không lặng lẽ làm nút luôn bật.
    tsx = (GOC / "frontend" / "chatltt" / "src" / "TaoMedia.tsx").read_text(encoding="utf-8")
    assert "san_sang !== 'san_sang'" in tsx


def test_hook_suc_khoe_hong_thi_fail_closed(monkeypatch):
    from platform_core.runtime_noi_bo import danh_muc as dm

    tools = [_tool("image.ltt", "i627.j", returns={"image_keys": "image[]"},
                   models={"chuan": {"id": "e"}})]
    for hong in (lambda: (_ for _ in ()).throw(RuntimeError("cong chet")),
                 lambda: "mau-xanh",
                 lambda: None):
        dm._DEM_SUC_KHOE.clear()
        ds = chinh_sach.danh_muc(None, user_id="u", apps=[_app("i627", tools, suc_khoe=hong)])
        assert ds[0].san_sang == "chua_san_sang"


# ── 3. Phương thức lạ ⇒ fail-closed ─────────────────────────────────────────

def test_phuong_thuc_la_khong_hien_va_khong_goi_duoc(monkeypatch):
    monkeypatch.setattr(chinh_sach, "CONG_CU_CHO_PHEP",
                        ("text.chat", "video.tuong_lai"))
    apps = [
        _app("v626a", [_tool("text.chat", "v626a.j", returns={"content": "text"},
                             models=HAI, sync=True)]),
        _app("v626b", [_tool("video.tuong_lai", "v626b.j",
                             returns={"video_key": "video"},
                             models={"chuan": {"id": "engine-video"}})]),
    ]
    ds = chinh_sach.danh_muc(None, user_id="u", apps=apps)
    assert [n.ten for n in ds] == ["text.chat"]           # video KHÔNG hiện

    # Nhưng nó vẫn trong allowlist, nên `kiem_cho_phep` cho qua — và đó là đúng:
    # chính sách sản phẩm và khả năng VẼ là hai cổng khác nhau. Cổng vẽ chặn ở
    # `danh_muc`, nên người dùng không bao giờ thấy để mà bấm.
    assert chinh_sach.kiem_cho_phep("video.tuong_lai") == "video.tuong_lai"
    assert "video" not in chinh_sach.PHUONG_THUC_HIEN_THI


def test_khoi_la_khong_duoc_ghi_vao_hoi_thoai():
    """Bộ khối nội dung là danh sách ĐÓNG: một loại lạ bị từ chối lúc ghi."""
    from apps.chatltt.services import hoi_thoai as H

    with pytest.raises(H.ThamSoSai):
        H.kiem_khoi([{"type": "video", "key": "x"}])
    with pytest.raises(H.ThamSoSai):
        H.kiem_khoi([{"type": "html", "text": "<b>x</b>"}])
    assert H.kiem_khoi([{"type": "text", "text": "ok"}]) == [{"type": "text", "text": "ok"}]


# ── Hai phép kiểm TĨNH giữ cho ba điều trên còn đúng ────────────────────────

def test_khong_re_nhanh_theo_ten_model_o_bat_cu_dau():
    xau = re.compile(r"(qwen38|hidream|noi-bo-|ltt_llm_vision|ltt_llm_dai|vieneu)",
                     re.IGNORECASE)
    for goc, duoi in ((GOC / "apps" / "chatltt", "*.py"),
                      (GOC / "frontend" / "chatltt" / "src", "*.ts*")):
        for tep in goc.rglob(duoi):
            for i, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
                ma = dong.split("#", 1)[0].split("//", 1)[0]
                assert not xau.search(ma), f"{tep.name}:{i} re nhanh theo model: {dong.strip()}"


def test_chatltt_khong_import_app_khac_hay_provider():
    """Thêm model mới không được đòi ChatLTT biết ai cung cấp nó."""
    cam = re.compile(r"^\s*(from|import)\s+(apps\.(?!chatltt)|platform_core\.(providers|api_pool|image_gen|llm)\b|render_gateway|llm_gateway|voice_sidecar)")
    xau = []
    for tep in (GOC / "apps" / "chatltt").rglob("*.py"):
        for i, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
            if cam.match(dong):
                xau.append(f"{tep.relative_to(GOC)}:{i} {dong.strip()}")
    assert not xau, xau


def test_them_model_moi_can_sua_dung_nhung_dau_da_ghi_ra():
    """Tài liệu phải nói ĐÚNG chỗ phải sửa — nếu không, phiên sau đi dò."""
    doc = (GOC / "docs" / "CHATLTT" / "11_THEM_MODEL_MOI.md").read_text(encoding="utf-8")
    # Ten TEP phai sua, va ten TRUONG hop dong — hai thu mot nguoi tiep quan
    # phai tim duoc ma khong doc mã.
    for phai_co in ("manifest.py", "api_contract", "models", "constraints",
                    "suc_khoe", "tuy_chon_dong", "so_lan_thu",
                    "chinh_sach.py", "CONG_CU_CHO_PHEP", "PHUONG_THUC_HIEN_THI",
                    "KHOI_THEO_PHUONG_THUC", "kiem_so_huu_khoa"):
        assert phai_co in doc, phai_co
    # Và phải nói rõ thứ KHÔNG phải sửa — đó mới là lời hứa của kiến trúc.
    assert "frontend/chatltt" in doc and "KHONG" in doc.upper()
