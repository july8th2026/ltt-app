"""HM-5 — đường ống chạy **trọn vẹn trên máy giả lập**, không cần pod.

## Mệnh đề trung tâm

Nếu `jobs.handle` không đi hết được một lượt với `MayGiaLap`, thì HM-6 (GUI) vẫn
phải chờ pod, và cả kế hoạch "giả lập trước" mất ý nghĩa. Phép kiểm đầu tiên ở
đây chính là phép kiểm chứng minh kế hoạch ấy đứng vững.

## ⛔ Và một ranh giới ngược lại, quan trọng hơn

Máy giả lập **không được** tự động thay máy thật khi thiếu cấu hình. Một job của
người dùng thật chạy trên máy giả lập sẽ "thành công" và trả về một tệp **không
phải video**: job XONG, credit đã trừ, người dùng tải về một tệp hỏng. Thất bại
im lặng ở phía có lợi — kiểu tệ nhất.

⇒ `MayGiaLap` chỉ được tiêm **tường minh** qua `_client`, từ phép kiểm.

## G2 — không kiểm lại WanGP

Không phép kiểm nào ở đây nói về **chất lượng video**. WanGP đã có bộ test của
nó; kiểm lại là nhân đôi công và nhân đôi chỗ sai. Ở đây chỉ kiểm **mối nối**:
khoá hợp đồng, đường tiền, đường lỗi, đường huỷ.
"""
from __future__ import annotations

import ast
import inspect
import io

import pytest

from apps.lttvideo import jobs
from apps.lttvideo.cong.giao_uoc import LoiMay
from apps.lttvideo.cong.may_gia_lap import MayGiaLap


class KhoGia:
    def __init__(self, co_san: dict[str, bytes] | None = None):
        self.da_luu: dict[str, bytes] = {}
        self._co_san = dict(co_san or {})

    def put(self, khoa, luong, content_type="application/octet-stream"):
        self.da_luu[khoa] = luong.read()
        return khoa

    def open(self, khoa):
        return io.BytesIO(self._co_san.get(khoa, b"ANH"))

    def exists(self, khoa):
        return khoa in self.da_luu


def _tham_so(**kw):
    ra = {"prompt": "mot dong song luc hoang hon", "duration_s": 5,
          "nguoi_dung_id": "42"}
    ra.update(kw)
    return ra


# ══════════════════════════════════════════════════════════════════════════
#  1. Mot luot TRON VEN, khong pod, khong GPU
# ══════════════════════════════════════════════════════════════════════════

def test_mot_luot_chu_thanh_video_chay_HET_tren_may_gia_lap():
    """🔑 Phép kiểm chứng minh kế hoạch "giả lập trước" đứng vững."""
    kho = KhoGia()
    ra = jobs.handle(_tham_so(), _client=MayGiaLap(), _kho=kho, _dieu_phoi=None)
    assert ra["video_keys"], "job xong ma khong co khoa video nao"
    assert kho.da_luu, "khong co tep nao vao kho"


def test_mot_luot_ANH_thanh_video_chay_HET_tren_may_gia_lap():
    kho = KhoGia(co_san={"lttvideo/42/vao/a.png": b"PNGDATA"})
    ra = jobs.handle(
        _tham_so(tac_vu="anh_thanh_video", media_key="lttvideo/42/vao/a.png"),
        _client=MayGiaLap(), _kho=kho, _dieu_phoi=None)
    assert ra["video_keys"]


def test_khoa_ket_qua_phai_tan_cung_bang_keys():
    """⛔ `server/routes/jobs.py:_artifacts()` chỉ nhặt khoá tận cùng `_key` /
    `_keys`. Tên khác nghĩa là job XONG, video nằm trong kho, và người dùng
    **không tải được** — một thất bại không có dấu hiệu nào ở phía máy chủ.
    """
    ra = jobs.handle(_tham_so(), _client=MayGiaLap(), _kho=KhoGia(),
                     _dieu_phoi=None)
    assert any(k.endswith(("_key", "_keys")) for k in ra), (
        f"khong khoa nao tan cung `_key`/`_keys`: {sorted(ra)}")


# ══════════════════════════════════════════════════════════════════════════
#  2. Ranh gioi: KHONG duoc lui ve may gia lap
# ══════════════════════════════════════════════════════════════════════════

def test_thieu_cau_hinh_thi_NEM_chu_khong_lui_ve_may_gia_lap(monkeypatch):
    """🔴 Thất bại im lặng **về phía có lợi** — kiểu tệ nhất.

    Một job thật chạy trên máy giả lập sẽ "thành công" và trả về một tệp không
    phải video: job XONG, credit đã trừ, người dùng tải về một tệp hỏng. Không
    lỗi ở đâu cả.
    """
    monkeypatch.delenv("LTTV_WANGP_URL", raising=False)
    with pytest.raises(jobs.LoiJob):
        jobs.handle(_tham_so(), _kho=KhoGia(), _dieu_phoi=None)


def test_MA_SAN_PHAM_khong_nhac_toi_MayGiaLap():
    """Đối chứng cho phép kiểm trên, đo ở tầng **mã** chứ không tầng hành vi:
    nếu `jobs.py` import máy giả lập thì một đường lui có thể mọc lại sau."""
    cay = ast.parse(inspect.getsource(jobs))
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom):
            assert "may_gia_lap" not in (n.module or ""), (
                "ma san pham import may gia lap — mot duong lui im lang")
        for ten in getattr(n, "names", []) or []:
            assert getattr(ten, "name", "") != "MayGiaLap"


# ══════════════════════════════════════════════════════════════════════════
#  3. Duong loi va duong huy — hai ket cuc KHAC NHAU ve tien
# ══════════════════════════════════════════════════════════════════════════

class _MayHong(MayGiaLap):
    def ket_qua(self, ma_viec):
        return {"tep": [], "loi": ["CUDA out of memory"], "huy": False}


class _MayHuy(MayGiaLap):
    def ket_qua(self, ma_viec):
        return {"tep": [], "loi": [], "huy": True}


class _MayNem(MayGiaLap):
    def gui_viec(self, settings):
        raise LoiMay("GET /submit: ConnectionResetError")


def test_job_HONG_thi_nem_LoiJob_kem_ly_do():
    with pytest.raises(jobs.LoiJob) as e:
        jobs.handle(_tham_so(), _client=_MayHong(), _kho=KhoGia(),
                    _dieu_phoi=None)
    assert "CUDA out of memory" in str(e.value), (
        "khong noi ly do — nguoi dung se thu lai dung cach vua hong")


def test_job_HUY_KHAC_job_hong():
    """Huỷ là một kết cục **bình thường**. Nền tảng đã hoàn credit ở
    `POST /jobs/{id}/cancel`; ném thêm một lỗi ở đây là một báo động giả."""
    ra = jobs.handle(_tham_so(), _client=_MayHuy(), _kho=KhoGia(),
                     _dieu_phoi=None)
    assert ra["trang_thai"] == "da_huy"
    assert ra["video_keys"] == []


def test_may_NEM_thi_job_hong_NGAY_chu_khong_treo():
    """Một `LoiMay` lọt ra ngoài không được bắt nghĩa là worker treo tới hết
    hạn thay vì hỏng ngay — và credit chỉ được hoàn khi job vào `JOB_ERROR`."""
    with pytest.raises((jobs.LoiJob, LoiMay)):
        jobs.handle(_tham_so(), _client=_MayNem(), _kho=KhoGia(),
                    _dieu_phoi=None)


def test_KHONG_co_duong_hoan_credit_rieng_trong_duong_ong():
    """⛔ `platform_core/job_runner.py` đã hoàn credit khi job vào `JOB_ERROR`.
    Thêm một đường hoàn thứ hai ở app là **hoàn hai lần** — và bánh cóc giữ cả
    hai đầu vì mỗi đầu nhìn riêng đều trông đúng.

    📌 Đọc **AST**, không quét chữ: `jobs.py` có chú thích giải thích rằng
       `job_runner` lo việc hoàn tiền, và một bộ dò quét văn bản sẽ báo động
       trên chính đoạn giải thích ấy — chuyện đã xảy ra **năm lần** ở kho này
       trong một ngày.
    """
    cay = ast.parse(inspect.getsource(jobs))
    goi = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            ten = getattr(f, "attr", None) or getattr(f, "id", None)
            if ten:
                goi.add(ten)
        if isinstance(n, ast.ImportFrom):
            goi |= {a.name for a in n.names}
    for cam in ("hoan_credit", "refund", "hoan_tien", "credit"):
        assert cam not in goi, f"duong ong tu hoan credit: goi {cam!r}"


# ══════════════════════════════════════════════════════════════════════════
#  4. Hai hang so trung ten DA duoc tach
# ══════════════════════════════════════════════════════════════════════════

def test_hai_tran_CHO_khong_con_trung_ten():
    """🔴 `CHO_TOI_DA_S` từng tồn tại ở **hai** tệp với **hai** giá trị và
    **hai** nghĩa: `dieu_phoi` = 900,0 (chờ MÁY khởi động), `jobs` = 3600,0
    (chờ VIỆC xong). Và `routes.py` nói với người dùng con số của cái kia.

    ⭐ Một tên dùng cho hai nghĩa không sai ở đâu cả cho tới lúc có người đọc
      một chỗ rồi suy về chỗ kia — và ở đây "chỗ kia" là câu ta nói với người
      dùng về thời gian chờ.
    """
    from apps.lttvideo import dieu_phoi

    assert hasattr(dieu_phoi, "CHO_MAY_SAN_SANG_S")
    assert hasattr(jobs, "CHO_VIEC_XONG_S")
    assert not hasattr(dieu_phoi, "CHO_TOI_DA_S")
    assert not hasattr(jobs, "CHO_TOI_DA_S")
    assert dieu_phoi.CHO_MAY_SAN_SANG_S < jobs.CHO_VIEC_XONG_S, (
        "cho MAY khoi dong phai ngan hon cho VIEC xong")



# ══════════════════════════════════════════════════════════════════════════
#  5. G2 — khong kiem lai WanGP
# ══════════════════════════════════════════════════════════════════════════

def test_duong_ong_KHONG_giai_ma_video():
    """⭐ Ràng buộc G2 (*"không viết phép kiểm nào kiểm lại hành vi của WanGP"*)
    được làm cho **cưỡng chế được** thay vì chỉ là một dòng trong tài liệu.

    Đo bằng một proxy chắc chắn: đường ống không được import thư viện giải mã
    video. Nếu nó giải mã thì nó đang đo **chất lượng đầu ra của WanGP** — việc
    của WanGP, không phải của ta — và mỗi phép kiểm như thế là một phép kiểm sẽ
    đỏ vì thượng nguồn đổi, chứ không vì ta sai.

    🔴 Bản đầu của phép kiểm này quét **danh sách từ cấm trong chính nó**, nên
       nó tự làm mình đỏ. Đó là lần thứ **năm** trong một ngày một bộ dò quét
       văn bản ở kho này báo động trên chính đoạn giải thích nó.
    """
    cay = ast.parse(inspect.getsource(jobs))
    nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            nhap |= {a.name.split(".")[0] for a in n.names}
        if isinstance(n, ast.ImportFrom) and n.module:
            nhap.add(n.module.split(".")[0])
    for thu_vien in ("cv2", "av", "imageio", "moviepy", "ffmpeg", "torch"):
        assert thu_vien not in nhap, (
            f"duong ong import {thu_vien!r} — no dang giai ma video, tuc dang "
            "do chat luong dau ra cua WanGP")
