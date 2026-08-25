"""
test_273_ma_luot — mã giữ chỗ/quyết toán phải LƯU ĐƯỢC. (H38, sau sự cố 23/08)

🔴 LỖI THẬT, VÀ NÓ CHẠY SẠCH QUA TOÀN BỘ BỘ TEST.

   `credit_entries.job_id` là `VARCHAR(36)`. **SQLite không ép độ dài,
   PostgreSQL thì có.** Bộ test chạy trên SQLite, bản thật chạy trên PostgreSQL.
   Kết quả: hai cửa thu tiền đi qua 739 test xanh, qua `gate` 13/13, qua cả một
   lần deploy — rồi trả `500` ở **lượt gọi thật đầu tiên**:

       stream:<32 hex>    39 ky tu
       chat:<uuid4 36 ky tu>  41 ky tu
       -> psycopg.errors.StringDataRightTruncation

   Bài học không phải "đếm ký tự cẩn thận hơn". Nó là: **một ràng buộc chỉ tồn
   tại ở production là một ràng buộc chưa được test.** File này kéo ràng buộc đó
   về chỗ đo được, không cần dựng PostgreSQL.

⭐ VÀ NÓ ĐO THEO CỘT, KHÔNG THEO CON SỐ GÕ TAY. Ngày ai đó nới cột lên 64, test
   này đi theo. Gõ `36` vào đây là tạo ra một sự thật thứ hai.
"""
from __future__ import annotations

import pytest

from platform_core.llm.thanh_toan import ma_luot


def _tran() -> int:
    from platform_core.models import CreditEntry

    return int(CreditEntry.__table__.c.job_id.type.length)


# ── 1. Vừa cột, mọi lúc ─────────────────────────────────────────────────────

@pytest.mark.parametrize("nguon", ["st", "ch", "a", "abc", "x1"])
def test_ma_luon_vua_cot(nguon):
    for _ in range(200):                    # uuid ngau nhien — quet nhieu lan
        ma = ma_luot(nguon)
        assert len(ma) <= _tran(), f"{ma!r} dai {len(ma)} > {_tran()}"


def test_ma_khong_trung_nhau():
    """Trùng mã nghĩa là **quyết toán nhầm lượt của người khác**."""
    assert len({ma_luot("st") for _ in range(2000)}) == 2000


def test_ma_mang_dau_nguon_de_lan_ra_tu_so_tien():
    """Một dòng `credit_entries` không nói được nó từ cửa nào thì đối soát tiền
    thành việc đoán."""
    assert ma_luot("st").startswith("st:")
    assert ma_luot("ch").startswith("ch:")


# ── 2. Nguồn quá dài bị chặn NGAY, không cắt lặng lẽ ────────────────────────

@pytest.mark.parametrize("xau", ["stream", "chat", "", "  ", "a-b", "ab:", "quá"])
def test_nguon_sai_bi_chan(xau):
    """⛔ Cắt lặng lẽ sẽ làm hai nguồn khác nhau đụng mã nhau."""
    with pytest.raises(ValueError):
        ma_luot(xau)


# ── 3. Hai cửa thật dùng đúng hàm này ───────────────────────────────────────

def test_hai_cua_KHONG_tu_ghep_chuoi():
    """Chốt chống tái phát: chỉ cần một chỗ quay lại `f"stream:{uuid4().hex}"`
    là lỗi sống lại, và nó chỉ hiện ra trên production."""
    import pathlib

    goc = pathlib.Path(__file__).resolve().parent.parent
    for ten in ("server/api/streaming.py", "server/api/chat.py"):
        ma = (goc / ten).read_text(encoding="utf-8")
        assert "ma_luot(" in ma, f"{ten} khong dung ma_luot"
        assert 'request_id = f"' not in ma, (
            f"{ten} tu ghep request_id — dung `thanh_toan.ma_luot`")


def test_tran_doc_tu_MODEL_khong_go_tay():
    """Ngày ai đó nới cột, hàm đi theo. Gõ tay `36` là tạo một sự thật thứ hai."""
    from platform_core.llm import thanh_toan

    assert thanh_toan._tran_ma() == _tran()


# ── 4. Ca thật: mã dài ĐÚNG LÀ thứ PostgreSQL từ chối ───────────────────────

def test_dung_lai_hai_ma_da_lam_no_production():
    """Hai hình dạng này lấy từ log lỗi ngày 23/08 — độ dài giữ nguyên, phần
    ngẫu nhiên thay bằng ký tự lặp: một chuỗi hex 32 ký tự trong mã nguồn
    trông y hệt một khoá API, và máy quét bí mật của gate bắt đúng như vậy."""
    for cu in ("stream:" + "a" * 32, "chat:" + "b" * 36):
        assert len(cu) > _tran(), (
            f"{cu!r} dai {len(cu)} — neu no vua thi test nay het y nghia, "
            "kiem lai cot")
