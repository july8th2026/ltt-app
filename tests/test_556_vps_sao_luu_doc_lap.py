"""VPS V2 Pha 06 — năng lực sao lưu: nói đúng cái mình có, và im khi chưa có.

Pha này **không** dựng được một lớp sao lưu độc lập: hạ tầng chưa có (kho `dir`
duy nhất trên node còn ~2,2 GiB, chưa có PBS). Thứ nó dựng được — và thứ đáng
dựng nhất khi hạ tầng còn thiếu — là **một hợp đồng nói đúng sự thật**.

Nên bộ test này chốt đúng một mệnh đề, ở nhiều mặt: *hệ thống không được nói nó
có thứ nó không có.* Ba biến thể của lời nói dối ấy:

* trả `True` cho `chong_hong_phan_cung` khi chỉ có ảnh chụp cùng pool;
* trả `False` cho `qua_han` khi **chưa từng** sao lưu lần nào;
* coi một tệp sao lưu tồn tại là bằng chứng dữ liệu khôi phục được.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import sao_luu_doc_lap as sl

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

_DU = {
    sl.KHOA_MAY_CHU: "https://pbs.noi-bo:8007",
    sl.KHOA_KHO: "vps-backup",
    sl.KHOA_NGUOI_DUNG: "ltt@pbs",
    sl.KHOA_MAT_KHAU: "bi-mat-that",
    sl.KHOA_VAN_TAY: "aa:bb:cc",
}


# ── 1. Chưa cấu hình ⇒ nói KHÔNG, và nói vì sao ─────────────────────────────

def test_chua_cau_hinh_thi_khong_co_sao_luu_doc_lap():
    nl = sl.nang_luc({})
    assert nl.sao_luu_doc_lap is False
    assert nl.anh_chup_cuc_bo is True


def test_tat_thi_PHAI_kem_ly_do():
    """Một tính năng bị tắt mà không nói vì sao là một ô xám vô nghĩa.

    Khách không biết đó là "chưa mở bán", "hỏng", hay "gói của bạn không có".
    """
    nl = sl.nang_luc({})
    assert nl.ly_do, "tat ma khong noi vi sao"
    assert "CUNG KHO" in nl.ly_do, "phai noi ro anh chup nam cung kho voi dia goc"


def test_anh_chup_CUNG_POOL_khong_tinh_la_chong_hong_phan_cung():
    """Mệnh đề trung tâm của cả pha.

    Theo `CORE/QUALITY_SCORECARD.md`: *"snapshot on same storage only ⇒ hardware
    backup/disaster protection ≤ 50 regardless of code quality"*. Trần đó là
    trần **thật**, và không dòng mã nào gỡ được nó.
    """
    assert sl.nang_luc({}).chong_hong_phan_cung is False


def test_thieu_MOT_bien_cung_la_chua_cau_hinh():
    """Nửa cấu hình tệ hơn không cấu hình: nó trông như đã xong."""
    for thieu in (sl.KHOA_MAY_CHU, sl.KHOA_KHO, sl.KHOA_NGUOI_DUNG):
        env = {k: v for k, v in _DU.items() if k != thieu}
        assert sl.nang_luc(env).sao_luu_doc_lap is False, thieu


def test_du_cau_hinh_thi_bao_CO():
    nl = sl.nang_luc(_DU)
    assert nl.sao_luu_doc_lap is True and nl.chong_hong_phan_cung is True
    assert "vps-backup" in nl.dich


# ── 2. Bí mật không được lọt ra ─────────────────────────────────────────────

def test_mat_khau_va_van_tay_KHONG_lot_vao_mo_ta():
    """`mo_ta_cau_hinh` là đường DUY NHẤT để in cấu hình ra ngoài."""
    ra = sl.mo_ta_cau_hinh(sl.doc_cau_hinh(_DU))
    text = repr(ra)
    assert "bi-mat-that" not in text and "aa:bb:cc" not in text


def test_repr_cua_cau_hinh_KHONG_chua_bi_mat():
    """`repr()` là thứ lọt vào traceback, log gỡ lỗi, và Sentry — im lặng."""
    cf = sl.doc_cau_hinh(_DU)
    assert "bi-mat-that" not in repr(cf) and "bi-mat-that" not in str(cf)


def test_danh_sach_truong_an_toan_la_danh_sach_CHO_PHEP():
    """Danh sách CẤM chỉ chặn được thứ nó biết tên.

    Trường bí mật tiếp theo sẽ là trường không ai nhớ thêm vào danh sách cấm.
    Nên hàm phải lọc theo danh sách **cho phép** — thêm một trường mới thì mặc
    định nó **không** ra ngoài.
    """
    assert "mat_khau" not in sl._TRUONG_AN_TOAN
    assert "van_tay" not in sl._TRUONG_AN_TOAN
    ra = sl.mo_ta_cau_hinh(sl.doc_cau_hinh(_DU))
    assert set(ra) == set(sl._TRUONG_AN_TOAN)


def test_nang_luc_KHONG_goi_mang(monkeypatch):
    """Trang máy của khách gọi hàm này mỗi lần mở.

    Một lần gọi ra ngoài ở đó biến một đích sao lưu chậm thành một trang chậm
    cho **mọi** khách — kể cả khách không dùng sao lưu.
    """
    import socket

    def _cam(*a, **kw):
        raise AssertionError("nang_luc() khong duoc goi mang")

    monkeypatch.setattr(socket, "create_connection", _cam)
    monkeypatch.setattr(socket.socket, "connect", _cam)
    assert sl.nang_luc(_DU).sao_luu_doc_lap is True


# ── 3. Độ tươi và xác minh ──────────────────────────────────────────────────

def test_chua_tung_sao_luu_tinh_la_QUA_HAN():
    """Trả `False` cho `None` là biến "chưa bao giờ chạy" thành "vẫn ổn".

    Đúng loại im lặng mà lớp này sinh ra để phá.
    """
    assert sl.qua_han(None, now=NOW) is True


def test_sao_luu_moi_thi_khong_qua_han():
    assert sl.qua_han(NOW - timedelta(hours=6), now=NOW) is False


def test_sao_luu_cu_hon_han_thi_qua_han():
    assert sl.qua_han(NOW - timedelta(days=5), now=NOW) is True


def test_moc_naive_khong_lam_no_vo():
    """Trộn `datetime` naive với aware là `TypeError` — và nó chỉ nổ trên MỘT engine."""
    tho = (NOW - timedelta(days=5)).replace(tzinfo=None)
    assert sl.qua_han(tho, now=NOW) is True


def test_TON_TAI_khong_phai_bang_chung_KHOI_PHUC_DUOC():
    """Một tệp sao lưu có mặt không nói gì về việc dữ liệu trong đó dùng được."""
    assert sl.da_xac_minh(None, NOW) is False


def test_xac_minh_CU_HON_ban_sao_luu_thi_khong_tinh():
    """Một lần xác minh cũ hơn nói về một **bản khác**.

    Đây là cách một hệ thống "có xác minh" vẫn giao ra dữ liệu hỏng: job xác
    minh chết từ tuần trước, job sao lưu vẫn chạy, và dấu tích xanh vẫn còn đó.
    """
    assert sl.da_xac_minh(NOW - timedelta(days=3), NOW) is False
    assert sl.da_xac_minh(NOW, NOW - timedelta(days=3)) is True


# ── 4. Hợp đồng phải khớp với những gì `services/sao_luu.py` thật sự làm ────

def test_lop_A_luon_co_vi_anh_chup_khong_can_cau_hinh_gi():
    """Ảnh chụp chạy được với đúng những gì `proxmox.py` đã có."""
    assert sl.nang_luc({}).anh_chup_cuc_bo is True


def test_khong_co_ham_nao_o_day_TAO_ra_mot_ban_sao_luu():
    """Pha này khai **năng lực**, không khai tính năng.

    Một hàm `chay_sao_luu()` ở đây mà không có đích thật sẽ hoặc là ném mỗi lượt,
    hoặc là ghi một trạng thái "đang chờ" trông y hệt một hệ đang chạy tốt. Cả
    hai đều tệ hơn việc không có nó.
    """
    ten = [x for x in dir(sl) if not x.startswith("_")]
    assert not [x for x in ten if x.startswith(("chay_", "tao_", "gui_"))], (
        f"tep nay khong duoc TAO ban sao luu nao: {ten}")


@pytest.mark.parametrize("dich", [
    "https://pbs.noi-bo:8007",          # Proxmox Backup Server
    "ssh://backup@nha-khac:22",         # một máy khác, qua rsync/borg
    "s3://ap-southeast-1.example",      # kho đối tượng
])
def test_hop_dong_KHONG_ghim_vao_mot_san_pham_sao_luu_nao(dich):
    """Hợp đồng là *"failure domain độc lập"*, không phải *"phải là PBS"*.

    `CORE/TARGET_ARCHITECTURE.md` §9 nói thẳng: đừng ghim cứng PBS nếu deployment
    chọn một công nghệ tương đương khác. Nên phép kiểm hỏi câu **hành vi** — ba
    kiểu đích rất khác nhau có được nhận như nhau không — chứ không đi tìm một
    câu chú thích trong mã nguồn. Một chú thích thì đổi lời văn là mất; một hành
    vi thì không.
    """
    env = dict(_DU)
    env[sl.KHOA_MAY_CHU] = dich
    assert sl.nang_luc(env).sao_luu_doc_lap is True
