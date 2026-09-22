"""test_986 — cửa STREAMING cũng phải thôi phạt khoá khi máy B hết giờ.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 MỘT BẢN VÁ NỬA VỜI, VÀ NỬA BỊ BỎ QUÊN LÀ NỬA HAY HỎNG NHẤT
═══════════════════════════════════════════════════════════════════════════

Phase 5 tách `504` (hết giờ) khỏi `502` (hỏng) ở cổng máy B, rồi dạy **cửa đồng
bộ** (`platform_core/llm/cong_vlm.py`) đọc 504 thành `AmbiguousProviderError` —
tức không `danh_dau_loi`, không cascade.

⛔ NHƯNG CỬA STREAMING ĐI ĐƯỜNG KHÁC HẲN. `platform_core/llm/luong_vlm.py` là
   một client riêng, và nó có nhánh riêng:

       if r.status_code >= 500:
           ...
           api_pool.danh_dau_loi(db, key, message=f"HTTP {r.status_code}")

   `504 >= 500`. Nên sau Phase 5, cửa đồng bộ được bảo vệ còn cửa streaming
   **vẫn phạt khoá y như cũ** — và sau 5 lần thì `key.status = APIKEY_ERROR`,
   thứ hồi đó **không tự hồi** (từ 19/09: có hạn rồi thử lại, nhưng lỗi kế tắt
   lại ngay; ERROR không hạn vẫn chờ admin — `test_1524`).

🔴 VÀ ĐÂY LÀ VẾ ĐÁNG NHỚ: **streaming là cửa hay hết giờ nhất.** Codex và Claude
   Code chỉ nói SSE; chúng là thứ gửi prompt 100–200K. Cửa đồng bộ thì bị
   Cloudflare cắt ở ~100 giây nên không ai gửi việc dài qua đó.

   ⇒ Bản vá Phase 5, nếu dừng ở `cong_vlm`, sẽ **trông như đã xong** trong khi
     nó chưa chạm tới con đường mà khuyết tật thật sự đi.

⭐ Bài học chung, và nó đã có tên trong bộ nhớ dự án: *"phạm vi phép đo hẹp hơn
   lời tuyên bố"*. Sửa một client rồi tuyên bố "đã sửa taxonomy lỗi" là đo một
   trục và kết luận cho cả hai.

═══════════════════════════════════════════════════════════════════════════
 MỘT RANH GIỚI CỐ Ý KHÔNG VƯỢT
═══════════════════════════════════════════════════════════════════════════

Khách vẫn nhận **503**, không phải 504. Đưa 504 ra tới khách đòi một **mã lỗi
mới trong hợp đồng Public API** (`CODE_*` + `_TITLES` + golden API + kiểm tương
thích + tài liệu) — một thay đổi bề mặt công khai để đổi lấy một sắc thái ngữ
nghĩa.

Ba thứ **thật sự** quan trọng đều đã đúng, và chúng đúng ở tầng dưới:

  * tiền  — `runtime_noi_bo/luong.py` gọi `hoan()` cho **mọi** nhánh
            `KhongMoDuocLuong`, nên khách được hoàn đủ khi hết giờ;
  * khoá  — không `danh_dau_loi` (tệp này chốt);
  * bão   — `ban=False`, nên không có vòng thử-lại-sau-30-giây cho một yêu cầu
            sẽ hết giờ y hệt ở lần sau.

⚠️ Ghi ra đây thay vì lặng lẽ bỏ qua: 503 cho một lượt hết giờ là **chưa chuẩn**,
   chỉ là cái giá của nó cao hơn cái lợi ở hệ nội bộ này. Ngày mở API ra ngoài
   thì đọc lại đoạn này.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

from platform_core.llm.luong_vlm import KhongMoDuocLuong

GOC = pathlib.Path(__file__).resolve().parents[1]
LUONG_VLM = GOC / "platform_core" / "llm" / "luong_vlm.py"


def test_typed_504_duoc_nhan_dien_bang_code_khong_bang_status():
    from llm_gateway.error_contract import make_error
    from platform_core.llm.model_failure import decode_gateway_failure

    body = json.dumps({"error": make_error("upstream_timeout", request_id="rid-timeout")}).encode()
    failure = decode_gateway_failure(504, {}, body)
    error = KhongMoDuocLuong(failure=failure)

    assert error.failure.is_timeout
    assert not error.failure.is_busy
    assert not error.failure.is_context_limit


def test_timeout_nam_trong_nhom_khong_phat_khoa():
    """Policy có tên thay cho phép dò source dễ xanh giả trước Task 6."""
    from platform_core.llm.model_failure import model_failure

    failure = model_failure("upstream_timeout", http_status=504)
    assert not failure.penalizes_key


def test_413_va_429_khong_bi_gop_nghia():
    from llm_gateway.error_contract import make_error
    from platform_core.llm.model_failure import decode_gateway_failure

    unknown_413 = decode_gateway_failure(413, {}, b'{"detail":"context window exceeded"}')
    busy_429 = decode_gateway_failure(
        429,
        {},
        json.dumps(
            {"error": make_error("concurrency_limited", request_id="rid-busy", retry_after_s=17)}
        ).encode(),
    )
    assert unknown_413.canonical_code == "upstream_unknown"
    assert not unknown_413.is_context_limit
    assert busy_429.is_busy
    assert busy_429.retry_after_s == 17


def test_khong_con_co_boolean_het_gio_tren_ngoai_le():
    """Task 13: nghĩa nằm ở `failure`; kwarg `het_gio=` đã gỡ."""
    with pytest.raises(TypeError):
        KhongMoDuocLuong("het gio", het_gio=True)  # type: ignore[call-arg]


def test_mac_dinh_la_unknown_khong_phai_het_gio():
    """Không có `failure` ⇒ fail-closed `upstream_unknown`, không đoán hết giờ."""
    e = KhongMoDuocLuong("gi do")
    assert e.failure.canonical_code == "upstream_unknown"
    assert not e.failure.is_timeout


def test_moi_nhanh_KhongMoDuocLuong_deu_duoc_HOAN_tien():
    """💰 Vế tiền — và nó đúng ở tầng dưới, không phải ở tệp này.

    `runtime_noi_bo/luong.py` gọi `hoan()` **trước** khi phân loại `e.ban`, nên
    mọi nhánh `KhongMoDuocLuong` (kể cả `het_gio` mới) đều hoàn đủ. Chốt lại ở
    đây vì một bản vá tương lai rất dễ chuyển `hoan()` xuống *sau* một nhánh
    `if`, và lúc đó khách sẽ bị thu tiền cho một lượt hết giờ.
    """
    cay = ast.parse(
        (GOC / "platform_core" / "runtime_noi_bo" / "luong.py").read_text(encoding="utf-8")
    )
    for xu in ast.walk(cay):
        if not isinstance(xu, ast.ExceptHandler) or xu.type is None:
            continue
        if "KhongMoDuocLuong" not in ast.dump(xu.type):
            continue
        # `hoan(...)` phải là lệnh đầu tiên, trước mọi `if` — TRỪ đúng một ngoại
        # lệ có tên (phương án C bước 1, 17/09/2026): nhánh `e.ban and not
        # hoan_khi_ban` GIỮ tiền vì lượt sắp xếp lại; `mo_co_xep_lai` hoàn ở mọi
        # đường ra (đo bằng hành vi: `test_600`/`test_1208` "429 MAI ⇒ hold, refund").
        than = list(xu.body)
        if (
            isinstance(than[0], ast.If)
            and "hoan_khi_ban" in ast.dump(than[0].test)
            and isinstance(than[0].body[-1], ast.Raise)
        ):
            than = than[1:]
        dau = than[0]
        assert isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Call), (
            "lenh dau cua nhanh khong phai mot loi goi"
        )
        assert "hoan" in ast.dump(dau.value.func), (
            "hoan() khong con la lenh DAU TIEN -> mot nhanh loi moi se quen hoan tien"
        )
        return
    pytest.fail("khong tim thay `except KhongMoDuocLuong` trong runtime_noi_bo/luong.py")
