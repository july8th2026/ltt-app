"""ISSUE L — duong het-gio phai giet cay tien trinh con TRUOC khi `os._exit`.

🔴 VI SAO — lo hong nay VO HINH voi co che lease

`_het_gio` thoat bang `os._exit`, va docstring cu cua no noi *"o day khong con gi
dang don — trang thai da ben vung"*. Trang thai CSDL thi ben vung that. Nhung
engine la `subprocess.Popen`, KHONG phai con `multiprocessing`, nen no khong chet
theo worker — no thanh MO COI va VAN GIU CARD.

Va `gpu_lease.reclaim_orphans` co luat "job da ket thuc => rac, thu hoi NGAY,
khong cho nhip dap". Nen chuoi that la:

    _het_gio danh dau job failed -> os._exit -> con VAN chay, VAN giu card
      -> reclaim_orphans thay "job da ket thuc" -> xoa lease NGAY
      -> he thong tin card TRONG -> nhan job moi -> tranh VRAM voi mo coi

⭐ Do dung la cuoc dua ma `UniqueConstraint` cua `GpuLease` sinh ra de chan.
Tien trinh mo coi tai lap dung ca ay, va VO HINH voi lease vi no khong phai job.

Quan sat that 26/09/2026: mot `realesrgan-ncnn-vulkan.exe` mo coi (cha da chet)
giu GPU 100 % trong khi he thong coi card la ranh.

⚠️ Cac phep kiem duoi day KHONG chay `taskkill` that — chung chan `subprocess.run`
   va soi ARGV. Chay that se giet chinh tien trinh pytest.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="duong giet cay tien trinh con la dac thu Windows")


def _bat_taskkill(monkeypatch):
    """Chan `subprocess.run` trong `job_runner`, tra ve danh sach argv da goi."""
    from platform_core import job_runner

    da_goi: list = []

    class _KetQua:
        returncode = 0
        stdout = b""
        stderr = b""

    def _gia(args, **kwargs):
        da_goi.append((list(args), kwargs))
        return _KetQua()

    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", _gia)
    assert job_runner is not None
    return da_goi


def test_giet_cay_con_nham_PID_CUA_CHINH_TA(monkeypatch):
    """Pham vi phai la con chau CUA TA — khong bao gio la tien trinh nguoi khac.

    Ngan hoi quy: neu ai do doi sang mot pid khac (vd doc tu bien, tu cau hinh),
    duong het-gio se giet tien trinh cua phien/dich vu khac. Luat "chi giet thu
    minh khoi dong" o day duoc OS thi hanh, khong phai do ta nho.
    """
    from platform_core import job_runner

    da_goi = _bat_taskkill(monkeypatch)
    job_runner._giet_cay_tien_trinh_con("job-abc-123")

    assert len(da_goi) == 1, "phai goi taskkill dung mot lan"
    argv, kwargs = da_goi[0]
    assert argv[0] == "taskkill"
    assert "/T" in argv, "thieu /T => chi giet con truc tiep, bo sot chau"
    assert "/F" in argv, "thieu /F => tien trinh treo se khong chet"
    assert str(os.getpid()) in argv, (
        "taskkill PHAI nham pid cua chinh tien trinh nay; nham pid khac la giet "
        "tien trinh cua phien/dich vu khac")
    assert kwargs.get("timeout"), "phai co timeout — duong het-gio khong duoc treo them"


def test_giet_cay_con_KHONG_BAO_GIO_nem(monkeypatch):
    """Duong het-gio ma nem thi mat luon cua thoat.

    `os._exit` nam ngay sau lenh nay; mot exception o day se noi len `finally`
    va co the chan mat no.
    """
    from platform_core import job_runner

    def _no(args, **kwargs):
        raise OSError("taskkill khong ton tai")

    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", _no)
    job_runner._giet_cay_tien_trinh_con("job-abc-123")     # phai IM LANG di qua


def test_het_gio_GIET_CON_TRUOC_roi_moi_exit(monkeypatch):
    """Thu tu la ban chat: `_exit` truoc thi con mo coi ngay do.

    Ngan hoi quy: doi cho hai lenh nay cho nhau se khien ban va nay vo dung ma
    moi phep kiem khac van xanh.
    """
    from platform_core import job_runner

    thu_tu: list = []

    monkeypatch.setattr(job_runner, "_giet_cay_tien_trinh_con",
                        lambda job_id: thu_tu.append("giet_con"))

    def _gia_exit(ma):
        thu_tu.append(f"exit:{ma}")
        raise SystemExit(ma)          # de thoat ham, KHONG giet pytest

    monkeypatch.setattr(os, "_exit", _gia_exit)

    def _khong_co_db(*a, **k):
        raise RuntimeError("khong co CSDL trong phep kiem nay")

    monkeypatch.setattr(job_runner, "_one_session", _khong_co_db)

    with pytest.raises(SystemExit):
        job_runner._het_gio("job-abc-123", "upscalevideo.render", 7200)

    assert thu_tu == ["giet_con", "exit:3"], (
        f"thu tu sai: {thu_tu}. Phai giet cay con TRUOC khi `os._exit`, neu "
        f"khong engine se song sot va giu card trong khi lease da bi thu hoi.")


def test_tran_giay_ngan_co_chu_y():
    """Cho lau o duong thoat khan la doi mot tien trinh treo lay hai."""
    from platform_core import job_runner

    assert 0 < job_runner._GIAY_GIET_CAY_CON <= 30, (
        "tran giay cho taskkill phai NGAN: day la duong thoat khan, cho lau o "
        "day la mat luon cua thoat")
