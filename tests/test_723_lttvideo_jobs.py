"""Handler job của `lttvideo` — dán nối, không thêm abstraction.

⛔ Chạy được **không cần GPU**: client WanGP và kho lưu trữ đều tiêm vào được.
   Đây là phần mock; biên thật kiểm ở Phase E (`BLOCKED_BY_C1`).
"""
from __future__ import annotations

import io

import pytest

from apps.lttvideo import jobs, wangp_client as wc


class ClientGia:
    def __init__(self, *, tep=("/data/Wan2GP/outputs/2026-09-06_seed1_"
                               "A large orange octopus, blending in.mp4"),
                 thanh_cong=True, loi=()):
        self.tep = list(tep)
        self._thanh_cong = thanh_cong
        self._loi = list(loi)
        self.da_submit: dict | None = None
        self.da_cleanup = False

    def submit(self, settings):
        self.da_submit = settings
        return "JOB1"

    def progress(self, job_id):
        return {"phase": "denoising", "current_step": 20, "total_steps": 20}

    def result(self, job_id):
        return wc.KetQua(thanh_cong=self._thanh_cong, tep=self.tep, loi=self._loi)

    def cleanup(self, job_id):
        self.da_cleanup = True
        return {}

    def tai_ve(self, duong):
        return io.BytesIO(b"MP4DATA")


class KhoGia:
    def __init__(self):
        self.da_luu: dict[str, bytes] = {}

    def put(self, key, stream, content_type=""):
        self.da_luu[key] = stream.read()
        return type("SF", (), {"key": key, "size": len(self.da_luu[key])})()

    def exists(self, key):
        return key in self.da_luu


def _chay(params=None, client=None, kho=None):
    return jobs.handle(
        params or {"prompt": "một dòng sông", "duration_s": 5, "nguoi_dung_id": 42},
        ctx=None,
        _client=client or ClientGia(),
        _kho=kho or KhoGia(),
    )


def test_job_gui_tham_so_tu_HO_SO_da_duyet():
    c = ClientGia()
    _chay(client=c)
    assert c.da_submit["model_type"] == "t2v_2_2"
    assert c.da_submit["flow_shift"] == 12, "tham số hồ sơ phải đi kèm"
    assert c.da_submit["prompt"] == "một dòng sông"


def test_ten_tep_R2_KHONG_chua_prompt_cua_nguoi_dung():
    """🔴 Bẫy đo được ở P01: WanGP đặt tên tệp bằng nguyên văn prompt.

    Dùng lại tên đó làm khoá đối tượng vừa hỏng khoá vừa **rò rỉ prompt**.
    """
    kho = KhoGia()
    _chay(kho=kho)
    khoa = next(iter(kho.da_luu))
    assert "octopus" not in khoa.lower()
    assert "blending" not in khoa.lower()
    assert khoa.endswith(".mp4")


def test_khoa_R2_mang_id_nguoi_dung_de_soi_duoc_so_huu():
    kho = KhoGia()
    _chay(params={"prompt": "x", "duration_s": 5, "nguoi_dung_id": 77}, kho=kho)
    assert "77" in next(iter(kho.da_luu))


def test_job_CHUA_xong_cho_toi_khi_tep_nam_trong_kho():
    """Kiến trúc §4: job không `done` tới khi output đã ở kho của LTT."""
    kho = KhoGia()
    ra = _chay(kho=kho)
    assert ra["trang_thai"] == "xong"
    assert kho.exists(ra["video_keys"][0])


def test_wangp_hong_thi_job_hong_va_KHONG_luu_gi():
    kho = KhoGia()
    with pytest.raises(jobs.LoiJob):
        _chay(client=ClientGia(thanh_cong=False, loi=["CUDA out of memory"]), kho=kho)
    assert not kho.da_luu


def test_bi_HUY_thi_KHAC_bi_hong():
    c = ClientGia(thanh_cong=False, loi=["Generation was cancelled"], tep=())
    ra = _chay(client=c)
    assert ra["trang_thai"] == "da_huy"


def test_don_rac_tren_c_cloud_sau_khi_keo_ve():
    c = ClientGia()
    _chay(client=c)
    assert c.da_cleanup is True, "không dọn là để rác trên máy tính tiền"


def test_khong_co_prompt_thi_tu_choi_TRUOC_khi_cham_GPU():
    with pytest.raises(jobs.LoiJob):
        _chay(params={"prompt": "  ", "duration_s": 5, "nguoi_dung_id": 1})


def test_khoa_ket_qua_PHAI_hop_khuon_ma_nen_tang_nhat_duoc():
    """`_artifacts()` của nền tảng chỉ nhặt khoá tên `*_key` / `*_keys`.

    ⛔ Đặt tên khác thì job vẫn **XONG**, tệp vẫn nằm trong R2, và người dùng
       **không tải được** — một thất bại không để lại dấu hiệu nào ở phía máy
       chủ. Chốt ở đây để tên khoá không trôi trở lại.
    """
    import ast
    import pathlib

    ma = (pathlib.Path(__file__).parent.parent / "apps" / "lttvideo" / "jobs.py"
          ).read_text(encoding="utf-8")
    cay = ast.parse(ma)
    khoa: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    khoa.add(k.value)
    assert "video_keys" in khoa, "kết quả không mang khoá tên `*_keys`"
    assert "tep" not in khoa, "tên `tep` quay lại — nền tảng sẽ không nhặt được"
