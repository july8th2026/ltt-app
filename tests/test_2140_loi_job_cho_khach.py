"""
Lỗi job hiện cho KHÁCH không lộ tên lớp Python hay văn bản thô (22/09/2026).

`job_runner` lưu `Job.error = "TenLop: thông điệp"` — đó là chẩn đoán cho vận hành. Nhiều trang app in thẳng chuỗi đó:
khách thấy "LoiNguoiGoi: Video không tồn tại…", "RuntimeError: C:\\LTTPlatform\\…". `/api/v1` đã trả câu chung
(`server/api/jobs.py::_public_job`, Q76); web thì chưa.

Mệnh đề:
- `LoiNguoiGoi` (và lớp con) là câu app VIẾT CHO KHÁCH ⇒ khách thấy đúng câu đó, không tiền tố;
- mọi lỗi khác (hạ tầng, provider, bug) ⇒ câu chung — không bao giờ văn bản thô;
- vận hành vẫn thấy tên lớp con trong `Job.error`;
- bánh cóc: không route app nào đưa `job.error` thô cho khách (template/JS đọc dict của route).
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

GOC = Path(__file__).resolve().parents[1]


def _lop_con():
    from platform_core.jobs import LoiNguoiGoi

    class LoiGiongNoi(LoiNguoiGoi):
        pass
    return LoiGiongNoi


def test_mo_ta_loi_nguoi_goi_giu_ten_lop_con_cho_van_hanh():
    from platform_core import jobs
    assert jobs.mo_ta_loi(jobs.LoiNguoiGoi("Thiếu tệp.")) == "LoiNguoiGoi: Thiếu tệp."
    assert jobs.mo_ta_loi(_lop_con()("Giọng không thuộc tài khoản.")) == \
        "LoiNguoiGoi(LoiGiongNoi): Giọng không thuộc tài khoản."
    assert jobs.mo_ta_loi(RuntimeError("boom")) == "RuntimeError: boom"


def _job(error, status="error"):
    return SimpleNamespace(status=status, error=error)


@pytest.mark.parametrize("error, mong", [
    ("LoiNguoiGoi: Video không tồn tại hoặc đã bị gỡ.", "Video không tồn tại hoặc đã bị gỡ."),
    ("LoiNguoiGoi(LoiGiongNoi): Giọng không thuộc tài khoản.", "Giọng không thuộc tài khoản."),
    ("LoiNguoiGoi: dòng 1\ndòng 2", "dòng 1\ndòng 2"),
])
def test_loi_nguoi_goi_hien_dung_cau_cua_app(error, mong):
    from platform_core import jobs
    assert jobs.loi_cho_khach(_job(error)) == mong


@pytest.mark.parametrize("error", [
    "RuntimeError: C:\\LTTPlatform\\app\\x.py boom",
    "KeyError: 'muc'",
    "LoiGiongNoi: định dạng cũ trước bản sửa — không chứng minh được là lỗi người gọi",
    "Job vượt trần thời gian 7200 s",
    "",
    None,
])
def test_loi_khac_thanh_cau_chung(error):
    from platform_core import jobs
    assert jobs.loi_cho_khach(_job(error)) == jobs.LOI_CHUNG_KHACH


def test_job_chua_loi_thi_khong_co_cau():
    from platform_core import jobs
    assert jobs.loi_cho_khach(_job("LoiNguoiGoi: x", status="done")) == ""
    assert jobs.loi_cho_khach(None) == ""


def test_worker_ghi_loi_nguoi_goi_theo_mo_ta_loi():
    """`job_runner` dựng chuỗi lỗi qua ĐÚNG `jobs.mo_ta_loi` (một nguồn), không f-string riêng."""
    src = (GOC / "platform_core" / "job_runner.py").read_text(encoding="utf-8")
    assert "jobq.mo_ta_loi(exc)" in src
    assert 'f"{type(exc).__name__}: {exc}"' not in src


# ── Bánh cóc: không route app nào đưa lỗi thô cho khách ──────────────────────
#
# Template app KHÔNG nhận `Job` ORM: mọi trang (thumbnail, taoanh, taoclipngan, upscalevideo, autosubvideo) đọc
# dict mà route dựng (`_jobs_cua_toi`/`_jobs`), và JS đọc JSON từ route ⇒ chốt ở route là chốt ở mọi cửa hiển thị.

_ROUTE_THO = re.compile(r"""["']error["']\s*:\s*(?:j|job|row)\.error\b""")


def _vi_pham() -> list[str]:
    ra = []
    for p in sorted((GOC / "apps").glob("*/**/*.py")):
        for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _ROUTE_THO.search(dong):
                ra.append(f"{p.relative_to(GOC).as_posix()}:{i}")
    return ra


def test_khong_route_app_nao_dua_loi_job_tho():
    assert _vi_pham() == []


def test_bo_do_bat_duoc_mau_cu():
    """Đối chứng: bộ đo phải bắt được chính các dạng đã từng lộ (số 0 cần đối chứng)."""
    assert _ROUTE_THO.search('"progress_msg": j.progress_msg, "error": j.error,')
    assert _ROUTE_THO.search('"result": job.result or {}, "error": job.error or "",')
    assert _ROUTE_THO.search('"error": job.error if job.status == "error" else "",')
    assert _ROUTE_THO.search('"progress_msg": row.progress_msg, "error": row.error,')
    assert not _ROUTE_THO.search('"error": loi_cho_khach(j),')
