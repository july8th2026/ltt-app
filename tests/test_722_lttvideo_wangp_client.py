"""Client gọi WanGP trên C-CLOUD — **client mỏng**, không phải engine abstraction.

Kiểm bằng hàm HTTP tiêm vào, nên chạy được **không cần GPU** (`BLOCKED_BY_C1`
không chặn phần này).
"""
from __future__ import annotations

import pytest

from apps.lttvideo import wangp_client as wc


class GoiGia:
    """Hàm HTTP giả — ghi lại mọi lượt gọi để phép kiểm soi được."""

    def __init__(self, dap: dict | None = None):
        self.dap = dap or {}
        self.da_goi: list[tuple[str, str, dict | None]] = []

    def __call__(self, method: str, duong: str, than=None, timeout: float = 30.0):
        self.da_goi.append((method, duong, than))
        for mau, gia_tri in self.dap.items():
            if mau in duong:
                if isinstance(gia_tri, Exception):
                    raise gia_tri
                return gia_tri
        return {}


def _client(dap=None):
    g = GoiGia(dap)
    return wc.WanGPClient(goc="https://c-cloud.test", khoa="KHOA", goi=g), g


def test_health_hoi_dung_duong_va_khong_gui_than():
    c, g = _client({"/health": {"ok": True, "wangp_sha": "abc"}})
    assert c.health()["ok"] is True
    method, duong, than = g.da_goi[0]
    assert method == "GET" and duong.endswith("/health") and than is None


def test_submit_gui_tham_so_va_nhan_ve_job_id():
    c, g = _client({"/submit": {"job_id": "J1"}})
    jid = c.submit({"prompt": "x", "model_type": "t2v_2_2"})
    assert jid == "J1"
    _, _, than = g.da_goi[0]
    assert than["settings"]["prompt"] == "x"


def test_submit_KHONG_tu_them_tham_so_nao():
    """⛔ Client mỏng: nó chuyển tiếp, không chuẩn hoá.

    WanGP đã có `apply_media_flag_defaults` và `apply_video_length_duration`.
    Chuẩn hoá lần hai ở đây là dựng bản sao thứ hai của sự thật.
    """
    c, g = _client({"/submit": {"job_id": "J"}})
    vao = {"prompt": "x", "model_type": "t2v_2_2", "video_length": "5s"}
    c.submit(dict(vao))
    _, _, than = g.da_goi[0]
    assert than["settings"] == vao, "client không được thêm/bớt khoá nào"


def test_progress_tra_ve_nguyen_van_su_kien_cua_wangp():
    c, _ = _client({"/progress": {"phase": "denoising", "current_step": 7,
                                  "total_steps": 20}})
    p = c.progress("J1")
    assert p["current_step"] == 7 and p["total_steps"] == 20


def test_cancel_goi_dung_job():
    c, g = _client({"/cancel": {"cancelled": True}})
    assert c.cancel("J9")["cancelled"] is True
    assert "J9" in g.da_goi[0][1]


def test_result_nhan_dien_luot_bi_HUY_khac_voi_luot_HONG():
    """WanGP trả huỷ bằng `success=False` + một mục lỗi huỷ — không phải lỗi thật."""
    c, _ = _client({"/result": {"success": False,
                                "errors": ["Generation was cancelled"]}})
    kq = c.result("J1")
    assert kq.da_huy is True
    assert kq.thanh_cong is False


def test_result_hong_that_thi_KHONG_bi_coi_la_huy():
    c, _ = _client({"/result": {"success": False, "errors": ["CUDA out of memory"]}})
    kq = c.result("J1")
    assert kq.da_huy is False


def test_result_thanh_cong_tra_danh_sach_tep():
    c, _ = _client({"/result": {"success": True,
                                "generated_files": ["/data/out/a.mp4"]}})
    kq = c.result("J1")
    assert kq.thanh_cong is True and kq.tep == ["/data/out/a.mp4"]


def test_khoa_endpoint_di_theo_moi_lenh_goi():
    c, g = _client({"/health": {}})
    c.health()
    assert c.khoa == "KHOA"


def test_loi_mang_duoc_boc_thanh_loi_CUA_APP():
    """Người gọi không phải biết `urllib` — và không được nuốt lỗi."""
    c, _ = _client({"/health": TimeoutError("het gio")})
    with pytest.raises(wc.LoiWanGP):
        c.health()


def test_client_KHONG_biet_gi_ve_credit_hay_nguoi_dung():
    """Ranh giới: client là vận chuyển, không mang nghiệp vụ.

    ⭐ Đọc **AST**, không quét chuỗi. Một bộ dò quét văn bản sẽ báo động trên
       chính đoạn chú thích giải thích ranh giới này — tức nó **trừng phạt việc
       giải thích**, và cách chữa duy nhất là xoá lời giải thích đi. Nên nó phải
       hỏi *"mã có DÙNG khái niệm đó không"*, chứ không hỏi *"tệp có NHẮC tới
       nó không"*.
    """
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(wc))
    ten_dung: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Name):
            ten_dung.add(n.id.lower())
        elif isinstance(n, ast.Attribute):
            ten_dung.add(n.attr.lower())
        elif isinstance(n, ast.arg):
            ten_dung.add(n.arg.lower())
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ten_dung.add(n.name.lower())
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            ten_dung.update((a.name or "").lower() for a in n.names)
            if isinstance(n, ast.ImportFrom):
                ten_dung.add((n.module or "").lower())

    for cam in ("credit", "user_id", "nguoi_dung", "storage", "billing"):
        assert not any(cam in t for t in ten_dung), (
            f"client dùng khái niệm {cam!r} — nó là vận chuyển, không phải nghiệp vụ"
        )
