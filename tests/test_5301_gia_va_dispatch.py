"""M3 — giá của việc mới, dispatch của `jobs.handle`, và ba router được đăng ký.

Ba thứ này ⛔ không thể kiểm bằng cách đọc mã: một `operation` có giá mà
`handle` không nhận thì khách **bị trừ credit rồi job chết**; một router viết
xong mà không ai `import` thì endpoint ⛔ không tồn tại dù tệp có đủ mã.

⭐ `character_lock` KHÔNG có `story`, nên **thứ tự** trong `handle` là một phần
của hợp đồng: phép kiểm `story` phải nằm SAU nhánh dispatch. Đảo thứ tự là chặn
oan một việc hợp lệ — và bài `test_khoa_nhan_vat_khong_bi_chan_boi_phep_kiem_story`
dưới đây là thứ duy nhất bắt được điều đó.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi import jobs, manifest as mf
from apps.prompt_ai_ommi.project_schema import TOI_THIEU_KY_TU_BRIEF


# ── Giá ──────────────────────────────────────────────────────────────────────

def test_moi_operation_duoc_dispatch_deu_co_gia_duong():
    """Một `operation` mà `handle` nhận nhưng `_cost` không biết sẽ rơi về giá
    director — tức tính tiền theo số cảnh cho một việc không có cảnh nào."""
    for op in ("director", "storyboard", "iterate", "character_lock"):
        gia = mf._cost({"operation": op, "scene_count": 6})
        assert gia > 0, f"{op}: gia {gia}"


def test_khoa_nhan_vat_gia_khong_phu_thuoc_so_canh():
    """Sinh MỘT khối chữ cho nhân vật ⇒ số cảnh không liên quan.

    ⛔ Không có bài này thì `character_lock` âm thầm rơi về `_director_cost` và
    khách khoá một nhân vật bị tính tiền như dựng 20 cảnh.
    """
    gia = {mf._cost({"operation": "character_lock", "scene_count": n})
           for n in (1, 6, 20)}
    assert len(gia) == 1, f"gia doi theo so canh: {sorted(gia)}"


def test_iterate_re_hon_director_nhung_khong_mien_phi():
    """Sửa một kịch bản ĐÃ CÓ rẻ hơn dựng lại từ đầu — nhưng vẫn tốn."""
    for n in (1, 6, 20):
        p = {"scene_count": n}
        it = mf._cost({**p, "operation": "iterate"})
        dr = mf._cost({**p, "operation": "director"})
        assert 0 < it <= dr, f"scene_count={n}: iterate {it} vs director {dr}"
    # Doi chung: neu `_cost` tra HANG SO bat ke operation thi bai tren xanh oan.
    assert mf._cost({"operation": "director", "scene_count": 20}) != \
        mf._cost({"operation": "character_lock", "scene_count": 20})


# ── Dispatch ────────────────────────────────────────────────────────────────

def test_operation_la_khong_hop_le_thi_tu_choi():
    with pytest.raises(ValueError):
        jobs.handle({"operation": "khong-he-ton-tai", "story": "x" * 40})


def test_khoa_nhan_vat_khong_bi_chan_boi_phep_kiem_story(monkeypatch):
    """`character_lock` ⛔ không có `story` — phép kiểm story phải nằm SAU dispatch.

    Bài này KHÔNG gọi LLM: thay `chay_khoa_nhan_vat` bằng một hàm đánh dấu, nên
    nó đo đúng một thứ — **đường dispatch** — chứ không đo model.
    """
    goi = {}

    def gia_lap(params, ctx=None):
        goi["da_goi"] = True
        return {"ok": True}

    from apps.prompt_ai_ommi.services import nhan_vat as nv
    monkeypatch.setattr(nv, "chay_khoa_nhan_vat", gia_lap)
    ra = jobs.handle({"operation": "character_lock", "ten": "Ong Ngoai"})
    assert goi.get("da_goi") and ra == {"ok": True}


def test_iterate_duoc_dispatch_sang_service(monkeypatch):
    goi = {}

    def gia_lap(params, ctx=None):
        goi["da_goi"] = True
        return {"ok": "iterate"}

    from apps.prompt_ai_ommi.services import iterate as it
    monkeypatch.setattr(it, "chay_iterate", gia_lap)
    ra = jobs.handle({"operation": "iterate", "brief_id": "b1"})
    assert goi.get("da_goi") and ra == {"ok": "iterate"}


def test_director_van_doi_story_du_dai():
    """Đối chứng cho hai bài trên: phép kiểm `story` vẫn còn hiệu lực cho
    `director`. Không có ca này thì "dispatch chạy" có thể chỉ là "mọi phép kiểm
    đã bị xoá"."""
    with pytest.raises(ValueError):
        jobs.handle({"operation": "director",
                     "story": "x" * (TOI_THIEU_KY_TU_BRIEF - 1)})


# ── Router đã đăng ký ────────────────────────────────────────────────────────

@pytest.mark.parametrize("duong", [
    "/api/briefs", "/api/briefs/{bid}/preflight", "/api/briefs/{bid}/bundle",
    "/api/briefs/{bid}/generate", "/api/briefs/{bid}/iterations",
    "/api/characters", "/api/characters/{cid}/lock", "/api/backgrounds",
])
def test_router_moi_thuc_su_duoc_gan(duong):
    """Tệp router viết xong mà không ai `import` ⇒ endpoint KHÔNG tồn tại, dù mã
    đầy đủ và test của chính nó xanh. Đây là phép kiểm duy nhất bắt được."""
    from apps.prompt_ai_ommi.routes import router
    assert duong in {r.path for r in router.routes}
