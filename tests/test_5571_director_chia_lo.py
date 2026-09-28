"""Duong DIRECTOR sinh canh theo LO, mang lich su, va bao tien do o ranh lo.

## 🔴 Vi sao o `jobs.py` chu KHONG o `breakdown.py`

`breakdown()` chi duoc goi tu `routes/storyboard.py:349` — mot route dong bo. Duong
khach di, va duong Q-16 do (`scene_count=20` -> 19/20 canh), la:

    jobs.py::_handle_generate -> composer.director_prompt -> provider.generate_json
                              -> _normalize_result  (bu placeholder cho du so canh)

⭐ Cai "19/20" chinh la vong `while len(scenes) < requested` trong `_normalize_result`:
   no bu mot canh *"Canh chua duoc AI tao"*. Trung thuc, nhung do la mot canh khach
   tra tien ma khong nhan.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.project_schema import empty_project, prompt_job_params
from apps.prompt_ai_ommi.services import chia_lo


def _params(so_canh: int) -> dict:
    du_an = empty_project("Phim thu")
    du_an["brief"]["story"] = "Mot cau chuyen du dai de AI phan tich thanh nhieu canh."
    du_an["brief"]["scene_count"] = so_canh
    return prompt_job_params(du_an, operation="director", model="gemini-2.5-flash")


def _gia_lap(ghi: list[str], moi_lo: int | None = None):
    """`generate_json` gia: ghi lai loi nhac, tra DUNG so canh duoc yeu cau.

    `moi_lo` != None thi tra THIEU (mo phong provider tra thieu) de kiem rang mot lo
    thieu ⛔ khong lam cac lo sau lech chi so.
    """
    def goi(system: str, prompt: str, *, model: str = "", **_kw):
        ghi.append(prompt)
        import re
        m = re.search(r"(\d+)\s+scenes", prompt)
        n = int(m.group(1)) if m else 1
        n = moi_lo if moi_lo is not None else n
        return ({"summary": "goi canh", "anchors": {},
                 "scenes": [{"title": f"c{i}", "prompt": f"p{i}"} for i in range(n)]}, 123)
    return goi


def test_20_canh_di_qua_DUNG_so_lo_chu_khong_MOT_luot(monkeypatch):
    """Day la CA LY DO pha 6 ton tai."""
    from apps.prompt_ai_ommi import jobs
    ghi: list[str] = []
    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap(ghi))
    ra = jobs.handle(_params(20))
    assert len(ghi) == chia_lo.so_luot_goi(20), (
        f"{len(ghi)} luot goi, dung ra {chia_lo.so_luot_goi(20)} — MOT luot goi duy "
        f"nhat la trang thai TRUOC khi va")
    assert len(ra["prompt_package"]["scenes"]) == 20


def test_lo_thu_HAI_tro_di_MANG_lich_su_cua_lo_truoc(monkeypatch):
    """Thieu lich su thi chia lo doi mot loi (chat luong suy) lay mot loi khac
    (mat lien mach) — va bai nay la cho duy nhat bat duoc dieu do."""
    from apps.prompt_ai_ommi import jobs
    ghi: list[str] = []
    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap(ghi))
    jobs.handle(_params(20))
    assert "c0" not in ghi[0], "lo DAU khong the co lich su"
    assert "c0" in ghi[1] or "p0" in ghi[1], (
        "lo 2 phai thay canh cua lo 1 trong o `existing` cua `director_prompt`")


def test_tokens_used_CONG_DON_qua_cac_lo(monkeypatch):
    """`tokens_used` la *"job nay dung bao nhieu token"* — nen no phai la TONG.

    ⛔ Tra token cua MOT lo la khai thieu cho mot job goi nhieu luot.
    """
    from apps.prompt_ai_ommi import jobs
    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap([]))
    ra = jobs.handle(_params(20))
    assert ra["tokens_used"] == 123 * chia_lo.so_luot_goi(20)


def test_bo_dem_tien_do_TANG_va_ket_o_dung_tong(monkeypatch):
    from apps.prompt_ai_ommi import jobs
    moc: list[tuple[int, int]] = []

    class _Ctx:
        job_id = "job-gia"

        def progress(self, *_a, **_k):
            return None

        def progress_counter(self, da_xong, tong, **_k):
            moc.append((da_xong, tong))
            return True

    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap([]))
    jobs.handle(_params(20), _Ctx())
    assert len(moc) == chia_lo.so_luot_goi(20), moc
    assert moc[-1] == (20, 20), f"moc cuoi phai la (20, 20), dang la {moc[-1]}"
    assert [d for d, _ in moc] == sorted(d for d, _ in moc), "bo dem phai TANG"


def test_progress_counter_NEM_thi_jobs_KHONG_nuot(monkeypatch):
    """⛔ `_handle_generate` khong duoc bat `JobCancelled` roi chay tiep.

    Bat va nuot nghia la job ket thuc BINH THUONG sau khi khach bam Huy, va tien
    duoc quyet toan DAY DU cho mot luot chi giao mot phan.
    """
    from apps.prompt_ai_ommi import jobs
    from platform_core.job_runner import JobCancelled

    class _Ctx:
        job_id = "job-gia"

        def progress(self, *_a, **_k):
            return None

        def progress_counter(self, da_xong, tong, **_k):
            if da_xong >= 10:
                raise JobCancelled()
            return True

    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap([]))
    with pytest.raises(JobCancelled):
        jobs.handle(_params(20), _Ctx())


def test_MOT_canh_van_dung_MOT_lo(monkeypatch):
    from apps.prompt_ai_ommi import jobs
    ghi: list[str] = []
    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap(ghi))
    ra = jobs.handle(_params(1))
    assert len(ghi) == 1
    assert len(ra["prompt_package"]["scenes"]) == 1


def test_mot_lo_tra_THIEU_thi_van_du_TONG_so_canh(monkeypatch):
    """Bat bien cu cua `_normalize_result` phai song sot qua chia lo.

    ⭐ Voi mot lo tra 1 canh thay vi 5, tong van phai bang `scene_count` — phan
       thieu la placeholder *"Canh chua duoc AI tao"*, TRUNG THUC chu khong lap
       noi dung AI. Day dung la ca `19/20` da do.
    """
    from apps.prompt_ai_ommi import jobs
    monkeypatch.setattr(jobs.provider, "generate_json", _gia_lap([], moi_lo=1))
    ra = jobs.handle(_params(20))
    canh = ra["prompt_package"]["scenes"]
    assert len(canh) == 20, "tong so canh phai DUNG bang yeu cau"
    thieu = [c for c in canh if "chưa được AI tạo" in (c.get("summary") or "")]
    assert thieu, "phan bu phai la placeholder TRUNG THUC, khong phai noi dung lap"
