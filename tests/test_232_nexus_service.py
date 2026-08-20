"""Nexus N3.3b — agent tự chạy lại sau khi khởi động máy.

Quyết định: **Scheduled Task theo người dùng**, không phải Windows Service. Lý
do gắn với Q95 — bản cài chưa ký đã làm Windows cảnh báo rồi; thêm một lời xin
quyền admin nữa là dựng đúng màn hình mà kịch bản lừa đảo T1 cần khách bấm qua.

Cái được kiểm kỹ nhất ở đây là **trích dẫn đường dẫn**, vì đó là chỗ loại code
này hỏng và hỏng theo kiểu tệ nhất: máy người viết thường ở `C:\\Python`, máy
khách ở `C:\\Program Files\\...`, nên lỗi **chỉ xuất hiện trên máy khách** và
không bao giờ trên máy đã test.
"""
from __future__ import annotations

import pytest


def _runner(ma: int = 0, ra: str = ""):
    """Runner giả, ghi lại lệnh đã gọi."""
    goi = []

    def chay(argv):
        goi.append(argv)
        return ma, ra

    chay.goi = goi
    return chay


# ── Trích dẫn đường dẫn ──────────────────────────────────────────────────────

def test_duong_dan_co_DAU_CACH_duoc_boc_ngoac():
    """`C:\\Program Files\\...` là mặc định trên máy khách, không phải ngoại lệ."""
    from nexus_agent.service import lenh_chay

    lenh = lenh_chay(r"C:\Program Files\Python313\python.exe",
                     "https://app.lttstudios.com")
    assert '"C:\\Program Files\\Python313\\python.exe"' in lenh


def test_thu_muc_co_dau_cach_cung_duoc_boc():
    from nexus_agent.service import lenh_chay

    lenh = lenh_chay("py.exe", "https://x", r"C:\Program Data\LTT Nexus")
    assert '"C:\\Program Data\\LTT Nexus"' in lenh


def test_thu_muc_dat_TRUOC_lenh_con():
    """`--dir` là tham số của parser gốc. Đặt sau `run` thì argparse từ chối, và
    triệu chứng là task chạy rồi thoát ngay — trông như 'không chạy'."""
    from nexus_agent.service import lenh_chay

    lenh = lenh_chay("py.exe", "https://x", r"C:\data")
    assert lenh.index("--dir") < lenh.index("run")


def test_khong_co_thu_muc_thi_khong_them_co_dir():
    from nexus_agent.service import lenh_chay

    assert "--dir" not in lenh_chay("py.exe", "https://x")


# ── Không có chỗ để tiêm lệnh ────────────────────────────────────────────────

def test_tham_so_la_LIST_chu_khong_phai_chuoi():
    """List thì `subprocess` không đi qua shell, nên một đường dẫn chứa `&` hay
    `^` không thể biến thành lệnh khác. Đó là khác biệt giữa 'trích dẫn cẩn
    thận' và 'không có chỗ để tiêm'."""
    from nexus_agent.service import lenh_tao_task, lenh_xoa_task

    for lenh in (lenh_tao_task("bat cu gi"), lenh_xoa_task()):
        assert isinstance(lenh, list)
        assert all(isinstance(x, str) for x in lenh)


def test_duong_dan_hiem_van_o_nguyen_mot_tham_so():
    from nexus_agent.service import lenh_chay, lenh_tao_task

    hiem = r"C:\a & b\c^d\python.exe"
    argv = lenh_tao_task(lenh_chay(hiem, "https://x"))
    # Toan bo chuoi chay nam trong DUNG MOT phan tu, sau `/tr`.
    assert argv[argv.index("/tr") + 1].count(hiem) == 1


# ── Không xin quyền admin ────────────────────────────────────────────────────

def test_chay_ELEVATED_bang_token_nguoi_dung_Q99():
    """Q99: điều khiển không giám sát cần admin (V8: `--password` đòi admin).

    Đổi so với N3.3b: task giờ chạy `/rl HIGHEST` — token admin của CHÍNH người
    dùng, KHÔNG `/ru SYSTEM`. Hai điều được chốt ở đây:

    * `/rl HIGHEST` CÓ mặt → agent chạy đủ quyền để xoay mật khẩu RustDesk. Task
      Scheduler nâng quyền tự động, không hỏi UAC mỗi lần (chỉ lúc cài).
    * `/ru SYSTEM` VẮNG → giữ ngữ cảnh DPAPI của người dùng, để khoá thiết bị mã
      hoá lúc enroll vẫn đọc được lúc chạy. Đổi sang SYSTEM là một lỗi chỉ hiện
      trên máy thật (khoá không giải mã được).
    """
    from nexus_agent.service import lenh_tao_task

    argv = [x.upper() for x in lenh_tao_task("py.exe")]
    assert "/RL" in argv and "HIGHEST" in argv, "Q99: can /rl HIGHEST de xoay mat khau"
    assert "/RU" not in argv, "khong dung /ru SYSTEM — giu ngu canh DPAPI nguoi dung"
    assert "SYSTEM" not in argv


def test_chay_khi_dang_nhap_chu_khong_khi_khoi_dong():
    """`onstart` cần quyền admin; `onlogon` thì không. Đây là chỗ đánh đổi đã
    chọn: không vào được máy trước khi đăng nhập."""
    from nexus_agent.service import lenh_tao_task

    argv = lenh_tao_task("py.exe")
    assert argv[argv.index("/sc") + 1].lower() == "onlogon"


def test_cai_lai_ghi_de_chu_khong_bao_loi():
    """Không có `/f` thì cài lại trên máy đã có task sẽ hỏi Y/N — mà tiến trình
    cài không có ai để trả lời."""
    from nexus_agent.service import lenh_tao_task

    assert "/f" in lenh_tao_task("py.exe")


# ── Vòng đời ─────────────────────────────────────────────────────────────────

def test_cai_that_bai_thi_NEM_chu_khong_im_lang():
    from nexus_agent.service import ServiceError, cai

    with pytest.raises(ServiceError):
        cai("py.exe", "https://x", runner=_runner(ma=1, ra="Access is denied"))


def test_go_mot_thu_KHONG_ton_tai_khong_phai_loi():
    """Gỡ một thứ vốn không có là kết quả mong muốn. Ném ở đây làm đường gỡ cài
    đặt dừng giữa chừng và để lại máy ở trạng thái nửa vời."""
    from nexus_agent.service import go

    assert go(runner=_runner(ma=1, ra="ERROR: The system cannot find the file")) is False


def test_da_cai_doc_ma_thoat_chu_khong_doc_van_ban():
    """Văn bản của `schtasks` đổi theo ngôn ngữ Windows. Một máy chạy Windows
    tiếng Việt sẽ trả chuỗi khác, nên đọc văn bản là một lỗi chờ ngày xảy ra."""
    import inspect

    from nexus_agent import service

    src = inspect.getsource(service.da_cai)
    assert "ma == 0" in src
    assert "SUCCESS" not in src and "TaskName" not in src


def test_ngoai_Windows_thi_noi_thang_chu_khong_chay_bua(monkeypatch):
    from nexus_agent import service

    monkeypatch.setattr(service.sys, "platform", "linux")
    with pytest.raises(service.ServiceError):
        service.cai("py", "https://x")
