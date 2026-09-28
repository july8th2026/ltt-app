"""tests/test_5509_upload_zip_entry_accounting.py — không entry nào biến mất.

⭐ Bất biến rút từ bài học "setpts" của một phiên khác: một khẳng định chỉ về
HÌNH THỨC (ví dụ "extract xong không lỗi") có thể xanh trên một đồ thị hỏng —
một tên không ai sinh ra, một tên bị sinh hai lần — miễn THỨ TỰ không đổi.
Thuốc là một bất biến CẤU TRÚC: mọi entry trong zip phải có ĐÚNG MỘT kết cục
được ghi lại — hoặc trở thành một `ZipEntry` chấp nhận được (import), hoặc bị
liệt vào danh sách bỏ qua KÈM LÝ DO. Không entry nào được biến mất im lặng
giữa hai trạng thái đó.

Bản gốc của `iter_safe_entries` (trước bài này) dùng `continue` cho entry có
đuôi không phải ảnh — đúng dạng lỗi "biến mất im lặng": entry đó không xuất
hiện trong kết quả trả về VÀ không có ghi chú nào là nó đã bị loại. Bài dưới
tiêm đúng ba loại lỗi (đuôi lạ, tệp rỗng, tên trùng) để chứng minh cả ba đều
được ghi nhận, không cái nào rơi mất.
"""
from __future__ import annotations

import io
import zipfile

import pytest


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _plan(zip_bytes):
    from apps.prompt_ai_ommi.services import upload_zip
    return list(upload_zip.iter_safe_entries(zip_bytes))


def test_every_entry_gets_exactly_one_recorded_outcome():
    payload = _zip_bytes({
        "anh_hop_le.png": b"\x89PNG" + b"\x00" * 40,
        "anh_hop_le.png__copy": b"ban chua ro dinh dang",  # sai duoi -> skip
        "anh_hop_le_2.png": b"\x89PNG" + b"\x01" * 40,
    })
    entries = _plan(payload)
    # Zip nay co 3 entry file (khong thu muc). Bat bien: MOI entry co mat
    # trong ket qua — khong entry nao bien mat.
    assert len(entries) == 3

    accepted = [e for e in entries if e.skip_reason is None]
    skipped = [e for e in entries if e.skip_reason is not None]
    assert len(accepted) + len(skipped) == 3
    # Entry sai duoi phai nam trong skipped, KEM ly do khac rong.
    wrong_ext = [e for e in skipped if e.name == "anh_hop_le.png__copy"]
    assert len(wrong_ext) == 1
    assert (wrong_ext[0].skip_reason or "").strip() != ""


def test_injected_wrong_extension_entry_is_recorded_not_vanished():
    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 10,
        "ghi_chu.txt": b"day khong phai anh",
    })
    entries = _plan(payload)
    assert len(entries) == 2
    by_name = {e.name: e for e in entries}
    assert by_name["ok.png"].skip_reason is None
    assert by_name["ghi_chu.txt"].skip_reason is not None
    assert by_name["ghi_chu.txt"].skip_reason.strip() != ""


def test_injected_zero_byte_entry_is_recorded_not_vanished():
    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 10,
        "rong.png": b"",
    })
    entries = _plan(payload)
    assert len(entries) == 2
    by_name = {e.name: e for e in entries}
    assert by_name["ok.png"].skip_reason is None
    assert by_name["rong.png"].skip_reason is not None


def test_injected_duplicate_name_entry_is_recorded_not_vanished():
    """Hai entry cùng tên sau chuẩn hoá — zipfile cho phép, một số bộ giải nén
    xử lý khác nhau (mơ hồ zip cổ điển). Entry TRÙNG THỨ HAI phải bị bỏ qua
    kèm lý do, không được âm thầm ghi đè hay biến mất.
    """
    from apps.prompt_ai_ommi.services import upload_zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("nhan_vat.png", b"\x89PNG" + b"\x00" * 10)
        zf.writestr("nhan_vat.png", b"\x89PNG" + b"\x01" * 10)
    entries = list(upload_zip.iter_safe_entries(buf.getvalue()))
    assert len(entries) == 2
    accepted = [e for e in entries if e.skip_reason is None]
    skipped = [e for e in entries if e.skip_reason is not None]
    assert len(accepted) == 1
    assert len(skipped) == 1
    assert skipped[0].skip_reason.strip() != ""


def test_zip_with_only_valid_images_has_zero_skips_and_accounts_for_all():
    payload = _zip_bytes({"a.png": b"\x89PNG" + b"\x00" * 10,
                          "b.jpg": b"\xff\xd8\xff" + b"\x00" * 10})
    entries = _plan(payload)
    assert len(entries) == 2
    assert all(e.skip_reason is None for e in entries)
