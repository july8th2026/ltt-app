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
   thứ **không tự hồi** (`api_pool._ung_vien` chỉ tự hồi `COOLDOWN`).

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
import pathlib

import pytest

from platform_core.llm.luong_vlm import KhongMoDuocLuong

GOC = pathlib.Path(__file__).resolve().parents[1]
LUONG_VLM = GOC / "platform_core" / "llm" / "luong_vlm.py"


def _ham_mo() -> ast.FunctionDef:
    cay = ast.parse(LUONG_VLM.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "mo")


def _nhanh_504() -> ast.If:
    """Nhánh `if r.status_code == 504:` trong `mo()`."""
    for n in ast.walk(_ham_mo()):
        if not isinstance(n, ast.If):
            continue
        for so in ast.walk(n.test):
            if isinstance(so, ast.Constant) and so.value == 504:
                return n
    pytest.fail("khong tim thay nhanh `status_code == 504` trong luong_vlm.mo()")


def test_co_nhanh_504_rieng():
    assert _nhanh_504() is not None


def test_nhanh_504_KHONG_danh_dau_loi():
    """🔴 Bất biến trung tâm: hết giờ không được phạt khoá.

    Đọc bằng AST chứ không dựng CSDL — thứ ta chốt là **hình dạng mã**, và một
    phép kiểm hành vi ở đây sẽ đòi cả `api_pool`, `api_keys`, một CSDL và một
    khoá thật, để trả lời đúng câu hỏi mà bốn dòng AST trả lời chắc chắn hơn.
    """
    than = ast.dump(ast.Module(body=_nhanh_504().body, type_ignores=[]))
    assert "danh_dau_loi" not in than, (
        "nhanh 504 CO goi danh_dau_loi -> 5 lan het gio la khoa vao "
        "APIKEY_ERROR, va trang thai do KHONG tu hoi")


def test_nhanh_504_KHONG_dat_ban_True():
    """`ban=True` hứa *"30 giây nữa thử lại là được"* — hết giờ không hứa được thế.

    Một yêu cầu hết giờ vì nó quá lớn sẽ hết giờ y hệt ở lần sau; gắn `ban` vào
    đây là dựng một vòng thử lại vô ích. Đúng cái bẫy mà chú thích nhánh 413
    ngay bên trên đã cảnh báo (*"retry vô ích → bão"*).
    """
    for kw in [k for n in ast.walk(_nhanh_504())
               if isinstance(n, ast.Call) for k in n.keywords]:
        if kw.arg == "ban":
            assert not (isinstance(kw.value, ast.Constant) and kw.value.value is True), \
                "nhanh 504 dat ban=True -> bao thu lai"


def test_nhanh_504_dat_het_gio_True():
    co = [k for n in ast.walk(_nhanh_504()) if isinstance(n, ast.Call)
          for k in n.keywords
          if k.arg == "het_gio" and isinstance(k.value, ast.Constant)
          and k.value.value is True]
    assert co, "nhanh 504 khong danh dau het_gio -> ben goi khong phan biet duoc"


def test_nhanh_504_dung_TRUOC_nhanh_500():
    """⛔ Thứ tự quyết định tất cả: `504 >= 500`.

    Đặt sau thì nhánh `>= 500` nuốt mất và nhánh 504 **chết im lặng** — không
    lỗi, không cảnh báo, chỉ là khoá lại bị phạt như cũ. Cùng lớp bẫy với thứ
    tự `except` của `TimeoutException`/`HTTPError` ở `upstream.py`.
    """
    van = LUONG_VLM.read_text(encoding="utf-8")
    i504 = van.find("r.status_code == 504")
    i500 = van.find("r.status_code >= 500")
    assert 0 < i504 < i500, (
        "nhanh `>= 500` dung TRUOC nhanh 504 -> nhanh 504 khong bao gio chay")


def test_413_va_429_khong_bi_anh_huong():
    """Bản vá này **không được** chạm hai cửa vốn đã đúng."""
    van = LUONG_VLM.read_text(encoding="utf-8")
    i413 = van.find("r.status_code == 413")
    i429 = van.find("r.status_code == 429")
    i504 = van.find("r.status_code == 504")
    assert 0 < i429 < i413 < i504 < van.find("r.status_code >= 500")


def test_co_flag_het_gio_tren_ngoai_le():
    e = KhongMoDuocLuong("het gio", het_gio=True)
    assert e.het_gio is True and e.ban is False and e.qua_dai is False


def test_mac_dinh_het_gio_la_False():
    """Thêm một cờ mà mặc định `True` sẽ lặng lẽ đổi nghĩa mọi nhánh cũ."""
    e = KhongMoDuocLuong("gi do")
    assert e.het_gio is False


def test_moi_nhanh_KhongMoDuocLuong_deu_duoc_HOAN_tien():
    """💰 Vế tiền — và nó đúng ở tầng dưới, không phải ở tệp này.

    `runtime_noi_bo/luong.py` gọi `hoan()` **trước** khi phân loại `e.ban`, nên
    mọi nhánh `KhongMoDuocLuong` (kể cả `het_gio` mới) đều hoàn đủ. Chốt lại ở
    đây vì một bản vá tương lai rất dễ chuyển `hoan()` xuống *sau* một nhánh
    `if`, và lúc đó khách sẽ bị thu tiền cho một lượt hết giờ.
    """
    cay = ast.parse((GOC / "platform_core" / "runtime_noi_bo"
                     / "luong.py").read_text(encoding="utf-8"))
    for xu in ast.walk(cay):
        if not isinstance(xu, ast.ExceptHandler) or xu.type is None:
            continue
        if "KhongMoDuocLuong" not in ast.dump(xu.type):
            continue
        # `hoan(...)` phải là lệnh đầu tiên, trước mọi `if`.
        dau = xu.body[0]
        assert isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Call), \
            "lenh dau cua nhanh khong phai mot loi goi"
        assert "hoan" in ast.dump(dau.value.func), (
            "hoan() khong con la lenh DAU TIEN -> mot nhanh loi moi se quen hoan tien")
        return
    pytest.fail("khong tim thay `except KhongMoDuocLuong` trong runtime_noi_bo/luong.py")
