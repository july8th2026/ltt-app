"""Tran thoi gian phai DU cho so luot goi o tran so canh.

## 🔴 Vi sao bai nay ton tai

Chia lo **nhan so luot goi len**: 20 canh tu 1 luot thanh `ceil(20/5) = 4` luot. Mot
tran von vua du co the thanh khong du — va `prompt_canh` da ghi dung hau qua vao
manifest cua no: *"chet o tran nghia la khach DA TRA ma khong nhan gi"*.

⭐ Khuon lay tu `tests/test_1105` cua `prompt_canh` — bai da tra tien cho bai hoc nay.
   Hai con so (`max_runtime_s` va `MAX_SCENES`) song o hai tep khac nhau, nen ⛔ khong
   ai bat khop chung tru mot phep kiem.
"""
from __future__ import annotations

import inspect

from apps.prompt_ai_ommi.manifest import MANIFEST
from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo

JOB = "prompt_ai_ommi.generate"


def test_manifest_KHAI_tran_thoi_gian_cho_job_nay():
    assert JOB in (MANIFEST.max_runtime_s or {}), (
        "khong khai `max_runtime_s` thi job an mac dinh nen tang, va chia lo vua "
        "nhan so luot goi len 4 lan — mot tran von vua du co the thanh khong du")


def test_tran_DU_cho_so_luot_goi_o_tran_so_canh():
    can = chia_lo.so_luot_goi(MAX_SCENES) * chia_lo.NGAN_SACH_MOI_LUOT_S
    co = MANIFEST.max_runtime_s[JOB]
    assert co >= can, (
        f"{MAX_SCENES} canh = {chia_lo.so_luot_goi(MAX_SCENES)} luot goi x "
        f"{chia_lo.NGAN_SACH_MOI_LUOT_S}s = {can}s can, ma tran chi {co}s. "
        f"Chet o tran nghia la khach DA TRA ma khong nhan gi.")


def test_manifest_SUY_tu_chia_lo_chu_KHONG_go_lai_so():
    """⛔ Mot so go tay se troi khoi `LO_CANH` ngay lan dau ai doi `LO_CANH`.

    ⭐ Cung ly le voi `prompt_canh.manifest` **nhap** `TRAN_SO_CANH` thay vi go `500`.
    """
    from apps.prompt_ai_ommi import manifest
    src = inspect.getsource(manifest)
    assert "chia_lo" in src, (
        "`manifest` phai NHAP tu `chia_lo` (`so_luot_goi` / `NGAN_SACH_MOI_LUOT_S`) "
        "chu khong go lai con so")


def test_DOI_CHUNG_doi_LO_CANH_thi_tran_di_THEO(monkeypatch):
    """Tiem: lam lo NHO di => can NHIEU luot hon => nhu cau thoi gian TANG.

    ⭐ Khong co ve nay thi `test_tran_DU...` co the dang xanh vi mot tran go tay
       rong rai, chu ⛔ khong vi no thuc su di theo `chia_lo`.
    """
    goc = chia_lo.LO_CANH
    can_goc = chia_lo.so_luot_goi(MAX_SCENES) * chia_lo.NGAN_SACH_MOI_LUOT_S
    monkeypatch.setattr(chia_lo, "LO_CANH", 2)
    can_nho = chia_lo.so_luot_goi(MAX_SCENES) * chia_lo.NGAN_SACH_MOI_LUOT_S
    assert can_nho > can_goc, (
        f"lo {goc} -> 2 ma nhu cau thoi gian khong tang ({can_goc} -> {can_nho}): "
        f"`so_luot_goi` khong phu thuoc `LO_CANH` nhu ta tuong")
