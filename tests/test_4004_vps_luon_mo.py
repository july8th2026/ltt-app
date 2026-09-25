"""VPS luôn mở: khách không có nút tắt, và host reboot không làm khách mất máy.

🔴 Đo 25/09/2026: host Proxmox khởi động lại lúc ~22:04 hôm trước. `startall` bật
   lại VM 100–107 + 199 (đều có `onboot=1`) nhưng **VM 204 và 208 thì không** —
   máy khách không có `onboot`. Chúng nằm tắt **17,4 giờ**, trong khi khách vẫn
   bị tính tiền, và không một tín hiệu nào nói ra điều đó.

   Chủ dự án bấm "Kết nối lại" console và thấy một lỗi chung; Proxmox ghi
   `vncproxy Failed to run` — console hỏng vì **máy không chạy**, nhưng giao diện
   không nói vậy nên nó đẩy người đọc đi tìm lỗi ở console.

Chủ dự án chốt 25/09: **VPS luôn mở.** Khách chỉ được *khởi động lại*, không có
trạng thái "đã tắt" để rơi vào. Quyết định đó xoá luôn xung đột "hệ thống tự bật
lại chống ý khách" — vì không còn ý muốn tắt nào của khách để chống.
"""
import pathlib


def test_may_moi_co_onboot():
    """Gốc của cả sự cố: thiếu `onboot` thì host reboot = khách mất máy."""
    from types import SimpleNamespace

    from apps.vps import jobs

    cfg = jobs._cau_hinh_may_trong(
        SimpleNamespace(id="3ca8c925", plan_id="vps-nho", dia_them_gb=0),
        SimpleNamespace(vcpu=1, ram_mb=2048, disk_gb=40),
        SimpleNamespace(ho="windows"), "local:iso/x.iso")
    assert str(cfg.get("onboot")) == "1"


def test_khach_KHONG_con_route_tat():
    """⛔ Không còn đường nào để khách đưa máy vào trạng thái tắt."""
    nguon = pathlib.Path("apps/vps/routes.py").read_text(encoding="utf-8")
    assert '"/{instance_id}/tat"' not in nguon
    assert '"/{instance_id}/tat-cung"' not in nguon


def test_van_con_duong_CUU_HO():
    """Bỏ nút tắt ⛔ không được lấy mất đường cứu hộ khi máy treo."""
    nguon = pathlib.Path("apps/vps/routes.py").read_text(encoding="utf-8")
    assert '"/{instance_id}/khoi-dong-lai"' in nguon
    assert '"/{instance_id}/khoi-dong-lai-cung"' in nguon


def test_he_thong_VAN_tat_duoc_may():
    """⚠️ Bỏ nút của KHÁCH ⛔ không phải bỏ khả năng của HỆ THỐNG: treo máy hết
    hạn, cách ly khi lạm dụng, và xoá máy đều cần tắt."""
    from apps.vps.services import dieu_khien

    assert "tat" in dieu_khien.LENH
    assert "tat_cung" in dieu_khien.LENH


def test_dieu_khoan_khai_may_chay_lien_tuc():
    from apps.vps import dieu_khoan  # noqa: F401
    from tests.test_298_vps_dieu_khoan import _render

    vi = _render("/vps/dieu-khoan")
    thap = vi.lower()
    assert "liên tục" in thap or "luôn chạy" in thap
    assert "tạm dừng tính phí" in thap or "không tạm dừng" in thap
