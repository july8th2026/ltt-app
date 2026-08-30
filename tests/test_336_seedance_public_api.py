"""test_336 — `video.generate` (Seedance) ra Public API. (API Expansion V2, Phase 03)

Ba tính chất neo ở đây, và cả ba đều là **tiền hoặc bảo mật**:

  1. **Ràng buộc theo model phải tới được khách TRƯỚC khi họ gọi.** Nếu không,
     họ đoán, họ sai, và họ trả tiền để bị từ chối.
  2. **Tổ hợp sai bị chặn TRƯỚC quote/hold/dispatch.** Ba tool video trước đã
     dính Q84 — báo giá đã ký vẫn quyết toán cao hơn. Ở đây chưa mở nên chưa có
     ai để làm hỏng; luật phải đúng ngay từ đầu.
  3. **Id nhà cung cấp không rò.** Alias tồn tại để đổi nhà cung cấp không thành
     thay đổi phá vỡ tương thích; rò id thật là mất luôn lớp đệm đó.
"""
from __future__ import annotations

import json

import pytest

from platform_core.public_api.catalog import build_catalog, build_models
from platform_core.public_api.config import load_public_api_config

TOOL = "video.generate"


def _catalog():
    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": TOOL})
    return build_catalog(cfg)


def _tool():
    return next(t for t in _catalog() if t.name == TOOL)


# ── 1. Hợp đồng sinh ra, không gõ tay ────────────────────────────────────────

def test_hop_dong_SINH_tu_models_py_khong_chep():
    """Đổi `MODELS` thì hợp đồng đổi theo. Chép tay là hai bản sẽ lệch."""
    from apps.taovideo import models as m

    hoat_dong = {k for k, v in m.MODELS.items() if v.get("active")}
    cong_bo = {x.name for x in build_models(_catalog())}
    assert cong_bo == hoat_dong, (
        "danh sach model cong bo phai bang danh sach model dang bat trong "
        "models.py — neu lech thi mot trong hai da bi go tay")


def test_moi_model_mang_rang_buoc_CUA_RIENG_NO():
    """Đây là cả lý do tồn tại của việc này.

    `seedance-2.0` nhận `1080p`/`4k`; hai model kia thì không. Publish một tập
    hợp nhất sẽ nói dối về hai model sau.
    """
    theo_ten = {x.name: x.to_public_dict()["constraints"]
                for x in build_models(_catalog())}
    assert "4k" in theo_ten["seedance-2.0"]["resolutions"]
    assert "4k" not in theo_ten["seedance-2.0-mini"]["resolutions"]
    for rb in theo_ten.values():
        assert rb["resolutions"] and rb["durations"] and rb["aspect_ratios"]


def test_KHONG_ro_id_nha_cung_cap_hay_dia_chi_ha_tang():
    van = json.dumps(_tool().to_public_dict(), ensure_ascii=False)
    van += json.dumps([x.to_public_dict() for x in build_models(_catalog())],
                      ensure_ascii=False)
    for xau in ("dreamina", "provider_model_id", "endpoint", "ep-2026",
                "byteplus", "modelark"):
        assert xau.lower() not in van.lower(), f"ro ra ngoai: {xau}"


# ── 2. Tổ hợp sai bị chặn TRƯỚC khi tiền chuyển ─────────────────────────────

def test_to_hop_SAI_theo_model_bi_tu_choi():
    from platform_core.public_api import invocation
    from platform_core.public_api.errors import ApiError

    with pytest.raises(ApiError) as e:
        invocation.validate_public_input(_tool(), {
            "prompt": "x", "model": "seedance-2.0-mini", "resolution": "4k"})
    # ⛔  chi la "400 invalid_request" — thong diep that o
    #    . Doc nham cho lam phep kiem do trong khi ma DA dung.
    tin = str(getattr(e.value, "detail", "")).lower()
    assert "seedance-2.0-mini" in tin and "4k" in tin
    assert "480p" in tin, "loi phai NOI RA gia tri nao duoc chap nhan"


def test_to_hop_DUNG_di_qua():
    from platform_core.public_api import invocation

    sach = invocation.validate_public_input(_tool(), {
        "prompt": "x", "model": "seedance-2.0", "resolution": "4k",
        "duration": 5, "aspect_ratio": "16:9"})
    assert sach["resolution"] == "4k"


def test_kiem_chay_TRUOC_price():
    """⛔ Bất biến quan trọng nhất của tệp này.

    Ba tool video trước đã dính Q84: giá theo con số **khách khai**, worker đo
    lại rồi nâng giữ chỗ ⇒ một báo giá đã ký vẫn quyết toán cao hơn. Luật rút
    ra: mọi phép kiểm ảnh hưởng tới giá phải chạy **trước** khi tiền chuyển.
    """
    import inspect

    from server.api import jobs as api_jobs

    ma = inspect.getsource(api_jobs)
    for than in ma.split("def ")[1:]:
        if "validate_public_input" not in than or "price" not in than:
            continue
        assert than.index("validate_public_input") < than.index("price"), (
            "price() chay truoc validate_public_input — mot to hop sai se duoc "
            "bao gia va giu cho truoc khi bi tu choi")


# ── 3. Tham chiếu chưa chứng minh ownership thì HOÃN, không mở ──────────────

def test_bon_duong_tham_chieu_chua_an_toan_duoc_HOAN_CO_GHI():
    """Hoãn ≠ bỏ qua kiểm. Một ref mở mà chưa kiểm ownership là đường để khách
    A đọc tệp của khách B."""
    thuoc_tinh = set(_tool().to_public_dict()["input_schema"]["properties"])
    for hoan in ("image_keys", "video_key", "audio_key", "refs"):
        assert hoan not in thuoc_tinh, f"{hoan} lot ra hop dong cong khai"
    assert "prompt" in thuoc_tinh and "model" in thuoc_tinh
