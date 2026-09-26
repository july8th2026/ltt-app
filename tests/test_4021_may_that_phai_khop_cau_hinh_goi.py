"""Máy thật phải có đúng CPU/RAM mà **gói** hứa — và khi không, phải có gì đó báo.

## Lỗ hở này mở ra đúng lúc bảng giá đổi

`jobs._cau_hinh_may_trong` đặt `cores`/`memory` **một lần duy nhất, lúc tạo
máy**. ⛔ Không đường nào đọc lại chúng về sau.

Ngày 26/09/2026 gói Nhỏ đổi 1 vCPU/2 GB → 2 vCPU/4 GB. Từ giây đó:

* `cost.PLANS` nói máy `vps-nho` có 2 vCPU / 4 GB;
* Proxmox vẫn chạy nó với 1 vCPU / 2 GB;
* `billing` thu tiền theo **gói**, tức theo con số ở vế thứ nhất.

⇒ Khách trả tiền cho thứ họ ⛔ không nhận, và ⛔ **không cửa nào** trong hệ nói
  ra điều đó. Đây đúng khuôn *"hai chỗ khai cùng một điều mà không ai bắt khớp"*
  — cơ học (Proxmox) thắng giao ước (catalog), và im lặng.

## Vì sao phép đo TÁCH khỏi phép sửa

Đổi `cores`/`memory` của QEMU đòi tắt máy rồi bật lại. Một vòng bảo trì tự khởi
động lại máy khách là một **sự cố**, ⛔ không phải một lần sửa. Nên:

* `bao_tri.lech_cau_hinh_goi` chỉ **đo**;
* `tools/vps_ap_cau_hinh_goi.py` **sửa**, và chỉ khi có người bấm.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from apps.vps import bao_tri
from apps.vps.cost import lay_plan


def _ham_cong_cu(ten: str):
    """Cây AST của một hàm trong `tools/vps_ap_cau_hinh_goi.py`.

    Đọc NGUỒN chứ không import: công cụ nạp `app.env` của production khi chạy,
    và một phép kiểm ⛔ không được chạm vào đó.
    """
    cay = ast.parse(Path("tools/vps_ap_cau_hinh_goi.py").read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


def test_lech_thi_noi_ro_LECH_CHIEU_NAO():
    """⛔ Đừng trả `True/False`: lệch xuống là khách nhận thiếu thứ đã trả tiền,
    lệch lên là ta cho không. Hai chuyện khác nhau, hai cách xử khác nhau."""
    lech = bao_tri.lech_cau_hinh_goi(lay_plan("vps-nho"),
                                     {"cores": 1, "memory": 2048})
    assert lech == {"cores": (1, 2), "memory": (2048, 4096)}


def test_khop_thi_RONG():
    p = lay_plan("vps-nho")
    assert bao_tri.lech_cau_hinh_goi(
        p, {"cores": p.vcpu, "memory": p.ram_mb}) == {}


def test_KHONG_DO_DUOC_khong_duoc_tinh_la_LECH():
    """🔴 `0` ở đây nghĩa là *không đọc được*, ⛔ không phải *máy có 0 vCPU*.

    Gộp hai trạng thái ấy thì mỗi lần Proxmox im lặng sẽ thành một báo động
    giả — và báo động giả làm người ta TẮT cổng.
    """
    p = lay_plan("vps-nho")
    assert bao_tri.lech_cau_hinh_goi(p, {}) == {}
    assert bao_tri.lech_cau_hinh_goi(p, {"cores": 0, "memory": 0}) == {}
    # Đọc được MỘT vế thì vẫn phải kết luận về vế ấy.
    assert bao_tri.lech_cau_hinh_goi(p, {"cores": 1, "memory": 0}) == {
        "cores": (1, p.vcpu)}


def test_goi_khong_ton_tai_thi_KHONG_ket_luan():
    assert bao_tri.lech_cau_hinh_goi(None, {"cores": 1, "memory": 512}) == {}


def test_vong_bao_tri_KHONG_duoc_tu_khoi_dong_lai_may_khach():
    """Phép đo ⛔ không được kéo theo phép sửa.

    Chốt bằng TÍNH CHẤT: thân hàm ⛔ không được gọi bất cứ thứ gì dừng/bật máy.
    """
    cay = ast.parse(inspect.getsource(bao_tri.lech_cau_hinh_goi))
    ten_goi = {getattr(n.func, "attr", "") or getattr(n.func, "id", "")
               for n in ast.walk(cay) if isinstance(n, ast.Call)}
    cam = {"stop", "start", "bat", "tat_mem", "tat_cung", "dat_cau_hinh",
           "thi_hanh", "_goi"}
    assert not (ten_goi & cam), f"phep DO lai di SUA: {ten_goi & cam}"


def test_cong_cu_sua_ton_tai_va_MAC_DINH_chi_soi():
    """Một công cụ tắt máy khách mà mặc định là "làm luôn" thì sớm muộn có người
    chạy nó để xem thử."""
    nguon = Path("tools/vps_ap_cau_hinh_goi.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    co = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
          and getattr(n.func, "attr", "") == "add_argument"
          and any(getattr(a, "value", None) == "--ap" for a in n.args)]
    assert co, "cong cu khong con co --ap"
    assert all(kw.value.value == "store_true"
               for c in co for kw in c.keywords if kw.arg == "action"), (
        "--ap phai la co, khong duoc mac dinh bat")


def test_doc_lai_SAU_KHI_dat_chu_khong_tin_ma_200():
    """200 chỉ nói Proxmox đã **nhận**. Thứ ta cần biết là nó đã **giữ**."""
    ham = _ham_cong_cu("ap_cho_mot_may")
    goi = [getattr(n.func, "id", "") or getattr(n.func, "attr", "")
           for n in ast.walk(ham) if isinstance(n, ast.Call)]
    assert goi.count("doc_cau_hinh") >= 2, (
        "phai doc lai cau hinh SAU khi dat, khong chi doc truoc")
    assert goi.count("doc_dang_chay") >= 2, (
        "phai doc lai TIEN TRINH DANG CHAY sau khi bat — xem test duoi")


def test_PHAI_do_ca_TIEN_TRINH_DANG_CHAY_chu_khong_chi_so_cau_hinh():
    """🔴 Bẫy đã bắt tôi ngày 26/09/2026.

    Công cụ đọc `GET .../config` rồi in **"khớp"**, trong khi hai máy khách vẫn
    đang chạy 1 vCPU / 2 GB: cấu hình đã đổi, nhưng QEMU **chốt CPU/RAM lúc
    tiến trình khởi động** và hai máy đã chạy liên tục 25 giờ.

    ⭐ *Thứ tôi đang hỏi có SẴN ở chỗ tôi đang đứng không?* Câu hỏi là **khách
       đang được cấp bao nhiêu**; `config` trả lời một câu KHÁC (*"lần boot sau
       sẽ là bao nhiêu"*). Hai câu chỉ trùng khi ⛔ không ai sửa gì từ lần bật.
    """
    nguon = Path("tools/vps_ap_cau_hinh_goi.py").read_text(encoding="utf-8")
    assert "def doc_dang_chay(" in nguon, (
        "khong con duong doc tien trinh dang chay")
    assert "status/current" in nguon or "trang_thai_vm" in nguon, (
        "doc_dang_chay phai hoi trang thai HIEN TAI cua VM")
    ham = _ham_cong_cu("main")
    goi = {getattr(n.func, "id", "") or getattr(n.func, "attr", "")
           for n in ast.walk(ham) if isinstance(n, ast.Call)}
    assert {"doc_cau_hinh", "doc_dang_chay"} <= goi, (
        "bao cao phai doi chieu CA HAI nguon, khong chon mot")


def test_KHONG_duoc_dung_reboot_de_ap_CPU_RAM():
    """`reboot` khởi động lại **guest** trong cùng tiến trình QEMU cũ ⇒ máy boot
    lại mà vẫn giữ nguyên CPU/RAM cũ, và mọi thứ trông như đã xong."""
    nguon = Path("tools/vps_ap_cau_hinh_goi.py").read_text(encoding="utf-8")
    ham = _ham_cong_cu("ap_cho_mot_may")
    duong = [n.value for n in ast.walk(ham)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("status/reboot" in d for d in duong), (
        "reboot KHONG doi duoc CPU/RAM — phai stop roi start")
    assert any("status/stop" in d for d in duong) and            any("status/start" in d for d in duong), nguon[:0] or "thieu stop/start"
