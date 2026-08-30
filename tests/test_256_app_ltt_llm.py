"""
test_256_app_ltt_llm — app `ltt_llm` và hợp đồng công khai của nó. (H38, mảnh E)

Năm tính chất neo ở đây:

  1. **Alias ≠ id nội bộ.** Bản đầu tôi đặt trùng hệt, và `test_212` bắt được:
     alias tồn tại để *"a vendor change is not a breaking change"*. Trùng hệt là
     xoá lớp đệm.
  2. **Khách KHÔNG gọi được id nội bộ.** Nếu gọi được, tích hợp sẽ ghim vào nó.
  3. **`credit_cost` là TRẦN, ước CAO.** Giữ thiếu thì khách tiêu quá số dư.
  4. **Không cascade sang đám mây.** Đây là hàng bán ra ngoài: khách trả tiền cho
     `ltt_llm` mà nhận Gemini là bán sai hàng (D-010).
  5. **Kiểm tham số TRƯỚC khi tiền chuyển** — cùng câu mà `server/api/jobs.py`
     đã viết: *"a typo must never reach the ledger"*.
"""
from __future__ import annotations

import pytest

from apps.ltt_llm import features
from apps.ltt_llm.manifest import CUA_SO_NGU_CANH, MANIFEST, MAX_TOKENS_TRAN


def test_cua_so_ngu_canh_khop_moc_benchmark_131k():
    """Mốc đã đo phải được gắn vào hợp đồng app, không chỉ ghi trong nhật ký.

    🔴 NHƯNG MÔ TẢ CÔNG KHAI KHÔNG ĐƯỢC NÓI CON SỐ NÀY (sửa 30/08).

       131.072 là cửa sổ của **engine**. Thứ khách thật sự nhét vào được là
       `CONG_BO_CHO_CLIENT` (88.555) — thấp hơn vì phải chừa chỗ cho câu trả lời
       dài nhất và cho sai số của phép ước token.

       Bản cũ của phép kiểm này **bắt buộc** mô tả phải chứa `"131K"`, tức nó
       canh cho đúng lời hứa sai: khách đọc 131K, nhét 120K token, ăn **413**.
       Và `"64K"` cho bản vision thì không khớp con số nào cả.

    ⇒ Hằng vẫn phải bằng mốc đã đo; mô tả thì phải nói con số **khách dùng
      được**, và phải **sinh ra** từ hằng chứ không gõ tay.
    """
    from apps.ltt_llm.ngan_sach import CONG_BO_CHO_CLIENT

    assert CUA_SO_NGU_CANH == 131_072
    models = MANIFEST.tools[0].api_contract["models"]
    cua_so = f"{round(CONG_BO_CHO_CLIENT / 1000)}K"
    for ten in ("ltt_llm", "ltt_llm_vision"):
        mo_ta = models[ten]["description"]
        assert cua_so in mo_ta, (ten, mo_ta)
        assert "131K" not in mo_ta, (
            f"`{ten}` van hua cua so cua ENGINE chu khong phai cua so khach "
            f"dung duoc: {mo_ta}")


# ── 1. Bản khai ──────────────────────────────────────────────────────────────

def test_manifest_hop_le_va_dung_ba_cong():
    from platform_core.registry import discover
    it = {a.manifest.slug: a for a in discover()}["ltt_llm"]
    assert it.error == "", it.error
    m = it.manifest
    # Ba cổng độc lập của Q92 — quên một cái thì thiếu tính năng, không lộ hàng.
    assert m.surface == "customer", "Public API chi nhan surface='customer'"
    assert m.lifecycle in ("released", "development")
    assert m.tools[0].api_exposed is True
    # `public` la co cua catalog WEB, KHAC `api_exposed`. Dung tron.
    assert m.public is False


def test_tool_len_duoc_catalog_cong_khai():
    from platform_core.public_api.catalog import build_catalog, build_models
    from platform_core.public_api.config import load_public_api_config
    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    cat = build_catalog(cfg)
    assert "text.chat" in [t.name for t in cat]
    assert {m.name for m in build_models(cat)} >= {"ltt_llm", "ltt_llm_vision"}


def test_khong_bat_co_thi_khong_len_catalog():
    """Fail-closed (Q92): bật `LTT_PUBLIC_API` một mình KHÔNG mở tool nào."""
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    cfg = load_public_api_config({"LTT_PUBLIC_API": "1"})   # TOOLS rong
    assert "text.chat" not in [t.name for t in build_catalog(cfg)]


# ── 2. Alias là lớp đệm, không phải bí danh trang trí ────────────────────────

def test_alias_khac_id_noi_bo():
    for alias, noi_bo in features.ALIAS_SANG_ID.items():
        assert alias != noi_bo, (
            f"alias {alias!r} trung id noi bo -> lop dem bien mat, va "
            "test_no_vendor_model_id_reaches_a_customer_surface se do")


def test_khach_KHONG_goi_duoc_id_noi_bo():
    """Gọi được id nội bộ thì tích hợp sẽ ghim vào nó, và alias hết tác dụng."""
    for noi_bo in features.ALIAS_SANG_ID.values():
        with pytest.raises(features.ThamSoSai):
            features.kiem_tham_so({"messages": [{"role": "user", "content": "x"}],
                                   "model": noi_bo})


def test_manifest_khai_alias_dang_dict_co_id():
    """`test_212` doc `spec.get("id")` — dang chuoi tran lam no no."""
    models = MANIFEST.tools[0].api_contract["models"]
    for alias, spec in models.items():
        assert isinstance(spec, dict) and spec.get("id")
        assert features.ALIAS_SANG_ID[alias] == spec["id"], \
            "manifest va features phai khai CUNG mot anh xa"


# ── 3. Giá là TRẦN, ước CAO ──────────────────────────────────────────────────

def test_credit_cost_luon_it_nhat_1():
    assert MANIFEST.credit_cost({"messages": [{"role": "user", "content": "hi"}],
                                 "max_tokens": 1}) >= 1


def test_credit_cost_tang_theo_max_tokens():
    ngan = MANIFEST.credit_cost({"messages": [{"role": "user", "content": "hi"}],
                                 "max_tokens": 100})
    dai = MANIFEST.credit_cost({"messages": [{"role": "user", "content": "hi"}],
                                "max_tokens": 16_000})
    assert dai > ngan


def test_credit_cost_khong_bao_gio_THAP_hon_chi_phi_that():
    """Bất biến quan trọng nhất của phần giữ chỗ.

    Quét mọi kết cục thật: sinh từ 0 tới `max_tokens`, cache từ 0 tới toàn bộ."""
    from platform_core.llm import gia_token
    from platform_core.llm.cong_vlm import SuDung

    params = {"messages": [{"role": "user", "content": "x" * 8000}],
              "max_tokens": 2000}
    tran_credit = MANIFEST.credit_cost(params)

    # 8.000 ky tu -> uoc ~3.200 token vao. Token vao THAT co the it hon.
    for vao_that in (100, 1_600, 3_200):
        for ra_that in (0, 500, 2_000):
            that = gia_token.tinh(SuDung(token_vao=vao_that, token_ra=ra_that,
                                         dang_tin=True))
            assert that.tong_credit_lam_tron_len <= tran_credit


# ── 4. Không cascade sang đám mây ────────────────────────────────────────────

def test_chi_dung_model_nha_KHONG_cascade():
    """⛔ D-010: khách trả tiền cho `ltt_llm` mà nhận Gemini là bán sai hàng."""
    assert features.THU_TU_PROVIDER == ("ltt_llm",)
    assert "gemini" not in features.THU_TU_PROVIDER


# ── 5. Kiểm tham số trước khi tiền chuyển ────────────────────────────────────

@pytest.mark.parametrize("xau", [
    {},
    {"messages": []},
    {"messages": "khong phai list"},
    {"messages": [{"content": "thieu role"}]},
    {"messages": [{"role": "user", "content": "x"}], "model": "khong-co"},
    {"messages": [{"role": "user", "content": "x"}], "max_tokens": 0},
    {"messages": [{"role": "user", "content": "x"}], "max_tokens": MAX_TOKENS_TRAN + 1},
    {"messages": [{"role": "user", "content": "x"}], "temperature": 9},
    {"messages": [{"role": "user", "content": "x"}], "tools": "khong phai list"},
    {"messages": [{"role": "user", "content": "x"}], "reasoning_effort": "cuc_cao"},
])
def test_tham_so_sai_bi_chan(xau):
    with pytest.raises(features.ThamSoSai):
        features.kiem_tham_so(xau)


def test_tham_so_dung_duoc_chuan_hoa():
    sach = features.kiem_tham_so({"messages": [{"role": "user", "content": "x"}]})
    assert sach["model"] == features.MODEL_MAC_DINH
    assert sach["max_tokens"] > 0
    # Truong khong khai thi KHONG duoc tu dien vao - de thuong nguon dung mac dinh.
    assert "temperature" not in sach and "tools" not in sach


# ── 6. Kết quả mang theo usage để tính tiền ─────────────────────────────────

def test_ket_qua_bao_usage_cho_costing():
    """`public_api/costing.py`: *"A per-job token figure appears here only when a
    handler reports one in its result"*. Khong bao thi khong quy duoc token ve job."""
    kq = features.KetQua(noi_dung="x", suy_nghi="", tool_calls=(),
                         finish_reason="stop", model="ltt_llm",
                         token_vao=10, token_ra=5, token_vao_cache=3, do_duoc=True)
    u = kq.as_result()["usage"]
    assert u["prompt_tokens"] == 10 and u["completion_tokens"] == 5
    assert u["cached_prompt_tokens"] == 3 and u["measured"] is True


# ── 7. Gia THAT, khong phai tran da giu ─────────────────────────────────────

def _kq(vao=0, ra=0, cache=0, do_duoc=True):
    return features.KetQua(noi_dung="x", suy_nghi="", tool_calls=(),
                           finish_reason="stop", model="ltt_llm",
                           token_vao=vao, token_ra=ra, token_vao_cache=cache,
                           do_duoc=do_duoc)


def test_handler_PHAI_bao_credit_cost():
    """🔴 LOI TIEN THAT neu thieu.

    `job_runner._quyet_toan_credit` lay gia cuoi tu `result["credit_cost"]`;
    handler khong bao thi no dung dung PHAN DA GIU. Ma phan da giu la TRAN uoc
    cao — xin max_tokens=4096 ma model chi sinh 200 token thi khach van tra du
    4096. Im lang, va sai ve phia khach."""
    r = _kq(vao=2_000, ra=200).as_result()
    assert "credit_cost" in r, "thieu khoa nay = khach bi thu tron phan da giu"
    assert isinstance(r["credit_cost"], int)


def test_gia_that_RE_HON_tran_khi_sinh_it():
    """Day la ca canh ma bug tren gay thiet hai lon nhat."""
    params = {"messages": [{"role": "user", "content": "x" * 5000}],
              "max_tokens": 8000}
    tran = MANIFEST.credit_cost(params)
    that = _kq(vao=2_000, ra=200).gia_that_credit()
    assert that < tran, f"sinh it ma van thu tran ({that} vs {tran})"


def test_gia_that_KHONG_BAO_GIO_vuot_tran():
    """Bat bien: `credit.quyet_toan` da kep o phan da giu, nhung neu gia that
    thuong xuyen vuot tran thi cong thuc uoc tran dang sai."""
    from platform_core.llm import gia_token
    params = {"messages": [{"role": "user", "content": "x" * 8000}],
              "max_tokens": 2000}
    tran = MANIFEST.credit_cost(params)
    for vao in (100, 1_600, 3_200):
        for ra in (0, 500, 2_000):
            assert _kq(vao=vao, ra=ra).gia_that_credit() <= tran


def test_khong_do_duoc_thi_thu_0_chu_KHONG_thu_tran():
    """⛔ Thu tien ma khong co bang chung con te hon mat mot it tien.
    Cung luat voi `thanh_toan.quyet_toan_hoac_hoan`."""
    assert _kq(vao=9_999, ra=9_999, do_duoc=False).gia_that_credit() == 0
    assert _kq(vao=9_999, ra=9_999, do_duoc=False).as_result()["credit_cost"] == 0


def test_cache_lam_gia_that_re_hon():
    khong = _kq(vao=100_000, ra=1_000).gia_that_credit()
    co = _kq(vao=100_000, ra=1_000, cache=90_000).gia_that_credit()
    assert co < khong


# ── 8. Cua JOB phai nhan duoc DUNG vi du trang tai lieu in ra ───────────────

def test_cua_job_nhan_duoc_vi_du_cua_chinh_no():
    """🔴 LOI THAT, im lang tu luc dung app nay toi 23/08.

    `messages` khai `"json"`, ma `json` phoi ra cong khai la `object`, roi
    `invocation._validate_value` doi mot `dict`. `messages` la mot LIST. Ket qua:
    `POST /api/v1/jobs` voi `tool: text.chat` **tu choi moi input hop le** — ke
    ca dung vi du ma trang tai lieu in ra. Khong loi nao bao, vi khong ai thu.

    Goc re: bang kieu cua ToolSpec khong co cach nao noi "mot MANG JSON". Da
    them `json[]` (2026-08-23), chu KHONG noi long `object` cho nhan ca list —
    noi long se lam yeu bo kiem cua MOI tool khac de chieu mot tool."""
    from platform_core.public_api import examples
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.invocation import validate_public_input

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    tool = [t for t in build_catalog(cfg) if t.name == "text.chat"][0]
    validate_public_input(tool, examples.example_input(tool))    # khong duoc nem


def test_messages_phoi_ra_la_MANG_khong_phai_object():
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    tool = [t for t in build_catalog(cfg) if t.name == "text.chat"][0]
    assert tool.input_schema["properties"]["messages"]["type"] == "array"
    assert tool.input_schema["properties"]["tools"]["type"] == "array"


def test_moi_vi_du_khai_trong_manifest_deu_qua_duoc_bo_kiem():
    """Quet ca tool, khong chi `messages`: mot vi du khong chay duoc con te hon
    khong co vi du, vi nguoi doc tin no va mat mot buoi chieu."""
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.invocation import validate_public_input

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    tool = [t for t in build_catalog(cfg) if t.name == "text.chat"][0]
    day_du = {ten: spec["examples"][0]
              for ten, spec in tool.input_schema["properties"].items()
              if spec.get("examples")}
    validate_public_input(tool, day_du)
