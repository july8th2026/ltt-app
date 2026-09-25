"""asv v4-be-mat-de-xuat — nối `do_vung.de_xuat()` vào sản phẩm qua HTTP.

## Câu hỏi thật: bề mặt HTTP mới có tôn trọng ĐÚNG hợp đồng của `do_vung` không?

`do_vung.de_xuat()` tự nó đã đúng (`test_4301`) nhưng ⛔ KHÔNG ai gọi nó ngoài
chính tệp và test của nó — xem docstring đầu `do_vung.py`. Bài này KHÔNG đo lại
độ chính xác của bộ dò (đã đo ở `test_4301` + `L_DO_VUNG.md`); nó đo **đường ống
mới**: `POST /auto-scan-video/tai-len/{id}/de-xuat-vung`.

## Ba điều phải đúng, và mỗi điều là MỘT bài dưới đây

1. Route chỉ đọc được lượt tải lên CỦA NGƯỜI GỌI (I6 — không phải IDOR mới).
2. `do_vung.de_xuat()` không bao giờ ném — kể cả tệp không đọc được, route vẫn
   trả 200 kèm `trang_thai="khong_do_duoc"` (⛔ không phải 500), đúng BẤT BIẾN 1
   của `do_vung.py`: *"không đọc được" ≠ "không có gì"*.
3. Hình dạng `do_vung.de_xuat()` trả về TƯƠNG THÍCH với `vung_che.chuan_hoa_mot`
   một khi khách "nhận" (gắn `loai`) — đây chính là khớp nối mà lần này phải
   dựng: một đề xuất không đi qua được cửa kiểm của `vung_che` thì tính năng
   "nhận" ở giao diện sẽ luôn bị máy chủ từ chối ở bước tạo lần chạy.
"""
from __future__ import annotations

import base64
import hashlib
import re
import subprocess

import pytest

from apps.auto_scan_video import do_vung, vung_che
from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

GOC = "/auto-scan-video/tai-len"


def _md5(b: bytes) -> str:
    return base64.b64encode(hashlib.md5(b).digest()).decode()


def _tai_len_mot_phan(c, csrf: str, ten: str, kieu: str, than: bytes) -> str:
    """Tải một tệp NHỎ (một phần duy nhất) qua đường bền vững -> `upload_id` READY."""
    mo_ta = c.post(GOC, data={"csrf_token": csrf, "ten_tep": ten, "kieu": kieu,
                              "co": str(len(than))}).json()
    uid = mo_ta["upload_id"]
    assert mo_ta["so_phan"] == 1, "clip test phai nam trong MOT phan (< CO_PHAN)"
    ve = c.post(f"{GOC}/{uid}/phan/1/ve",
               data={"csrf_token": csrf, "md5": _md5(than)}).json()
    r = c.put(ve["url"], content=than, headers=ve["headers"])
    assert r.status_code == 204, r.text[:300]
    xong = c.post(f"{GOC}/{uid}/xong", data={"csrf_token": csrf})
    assert xong.status_code == 200 and xong.json()["xong"] is True, xong.text[:300]
    return uid


def _mp4_khong_doc_duoc() -> bytes:
    """Đủ chữ ký `ftyp` để `upload_sessions.confirm` nhận, ⛔ nhưng KHÔNG phải
    một khung hình nào cv2 mở được — đúng ca "KHÔNG đọc được"."""
    return (b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
            + b"\x00" * 4000)


@pytest.fixture(scope="module")
def clip_that(tmp_path_factory) -> bytes:
    """Clip THẬT rất nhỏ — chỉ để chứng minh `do_vung` ĐỌC ĐƯỢC khung hình qua
    đường ống mới, ⛔ không đo độ chính xác (đã đo ở `test_4301`)."""
    ra = tmp_path_factory.mktemp("de_xuat_http") / "nho.mp4"
    kq = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc2=size=160x90:rate=8:duration=2",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "28", str(ra)],
        capture_output=True, text=True, timeout=60, errors="replace")
    assert kq.returncode == 0, (kq.stderr or "")[-1500:]
    return ra.read_bytes()


# ══════════════════════════════════════════════════════════════════════════════
#  1. Chủ sở hữu — I6, cùng khuôn `test_423`
# ══════════════════════════════════════════════════════════════════════════════

def test_nguoi_khac_khong_doc_duoc_luot_tai_cua_ban(moi_truong):
    _app, a, csrf_a, b, csrf_b = moi_truong
    uid = _tai_len_mot_phan(a, csrf_a, "a.mp4", "video/mp4", _mp4_khong_doc_duoc())
    r = b.post(f"{GOC}/{uid}/de-xuat-vung", data={"csrf_token": csrf_b})
    assert r.status_code == 404, r.text[:300]


def test_luot_tai_khong_ton_tai_tra_404(moi_truong):
    _app, a, csrf_a, _b, _cb = moi_truong
    r = a.post(f"{GOC}/khong-ton-tai/de-xuat-vung", data={"csrf_token": csrf_a})
    assert r.status_code == 404, r.text[:300]


def test_thieu_csrf_bi_tu_choi(moi_truong):
    _app, a, csrf_a, _b, _cb = moi_truong
    uid = _tai_len_mot_phan(a, csrf_a, "a.mp4", "video/mp4", _mp4_khong_doc_duoc())
    r = a.post(f"{GOC}/{uid}/de-xuat-vung", data={"csrf_token": "sai"})
    assert r.status_code == 400, r.text[:300]


# ══════════════════════════════════════════════════════════════════════════════
#  2. BẤT BIẾN 1 qua HTTP: "không đọc được" -> 200 + trang_thai riêng, KHÔNG 500
# ══════════════════════════════════════════════════════════════════════════════

def test_video_khong_doc_duoc_tra_200_khong_do_duoc(moi_truong):
    _app, a, csrf, _b, _cb = moi_truong
    uid = _tai_len_mot_phan(a, csrf, "hong.mp4", "video/mp4", _mp4_khong_doc_duoc())
    r = a.post(f"{GOC}/{uid}/de-xuat-vung", data={"csrf_token": csrf})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["trang_thai"] == do_vung.TRANG_THAI_KHONG_DO_DUOC
    assert d["vung"] == []
    assert d["ly_do"], "BAT BIEN 1: 'khong doc duoc' phai co ly do — khong im lang"


# ══════════════════════════════════════════════════════════════════════════════
#  3. Đường ống THẬT: tệp thật -> `do_vung` chạy qua chính đường tải lên bền vững
# ══════════════════════════════════════════════════════════════════════════════

def test_video_that_di_qua_duong_ong_va_co_bang_chung_da_quet(moi_truong, clip_that):
    """`so_khung > 0` LÀ bằng chứng chạy thật (docstring `do_vung.KetQua`) —
    ⛔ không đoán, đo TRỰC TIẾP hai khoá `logo_tinh`/`dai_chu`."""
    _app, a, csrf, _b, _cb = moi_truong
    uid = _tai_len_mot_phan(a, csrf, "that.mp4", "video/mp4", clip_that)
    r = a.post(f"{GOC}/{uid}/de-xuat-vung", data={"csrf_token": csrf})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["trang_thai"] in (do_vung.TRANG_THAI_CO, do_vung.TRANG_THAI_KHONG_CO)
    assert d["so_khung"].get(do_vung.NGUON_LOGO, 0) > 0
    assert d["so_khung"].get(do_vung.NGUON_DAI, 0) > 0
    for hop in d["vung"]:
        assert hop["nguon"] in (do_vung.NGUON_LOGO, do_vung.NGUON_DAI)


def test_tranh_json_hong_khong_lam_sap_route(moi_truong, clip_that):
    """`tranh` là JSON máy tự tạo phía trình duyệt — một lượt gõ dở KHÔNG được
    làm hỏng cả yêu cầu, chỉ coi như chưa vẽ gì."""
    _app, a, csrf, _b, _cb = moi_truong
    uid = _tai_len_mot_phan(a, csrf, "that2.mp4", "video/mp4", clip_that)
    r = a.post(f"{GOC}/{uid}/de-xuat-vung",
              data={"csrf_token": csrf, "tranh": "{khong phai json"})
    assert r.status_code == 200, r.text[:300]


# ══════════════════════════════════════════════════════════════════════════════
#  4. 🔴 Khớp nối thật: hình dạng `do_vung` PHẢI qua được cửa `vung_che`
# ══════════════════════════════════════════════════════════════════════════════
#
#  Đây là bài quan trọng nhất của tệp: nó KHÔNG phụ thuộc bộ dò có bắt trúng
#  gì hay không (dễ giòn theo môi trường ffmpeg/CI) — nó khẳng định một điều
#  tĩnh, luôn đúng: MỌI hộp `do_vung` có thể trả về (đúng hình dạng docstring
#  `de_xuat()`) đều được `vung_che.chuan_hoa_mot` NHẬN một khi khách "nhận" nó
#  (gắn thêm khoá `loai`) — đúng luồng "đề xuất -> khách bấm nhận -> vung_che
#  THẬT" mà `do_vung.py` mục 3 mô tả.

@pytest.mark.parametrize("nguon,loai_nhan", [
    (do_vung.NGUON_LOGO, vung_che.LOAI_LAM_MO),
    (do_vung.NGUON_DAI, vung_che.LOAI_DIEN_NEN),
])
def test_hop_de_xuat_QUA_DUOC_cua_kiem_vung_che_sau_khi_nhan(nguon, loai_nhan):
    hop_de_xuat = {"x0": 0.12, "y0": 0.04, "x1": 0.34, "y1": 0.16,
                   "nguon": nguon, "goc": "tl"}
    # ⭐ Đúng thao tác giao diện làm khi khách bấm "Nhận": thêm `loai`, giữ
    #    nguyên bốn toạ độ — `asv/de_xuat.js:themVungDeXuat`.
    da_nhan = vung_che.chuan_hoa_mot({**hop_de_xuat, "loai": loai_nhan})
    assert da_nhan["loai"] == loai_nhan
    assert (da_nhan["x0"], da_nhan["y0"], da_nhan["x1"], da_nhan["y1"]) == (
        0.12, 0.04, 0.34, 0.16)


def test_danh_sach_de_xuat_rong_van_la_ho_so_THUA():
    """`vung_che.chuan_hoa([])` phải rỗng — hồ sơ THƯA khi khách không dùng
    tính năng này (điều kiện 4 trong brief). Không có gì đặc biệt để ghi."""
    assert vung_che.chuan_hoa([]) == []
