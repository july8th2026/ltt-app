"""Bánh cóc chỉ được **chặn** vì tệp git ĐANG THEO DÕI, ⛔ không vì tệp rác của ai.

## Ca thật 26/09/2026

`deploy.ps1` — một tệp **chưa theo dõi** (`?? deploy.ps1`), scratch của làn
upscalevideo, có một dấu gạch dài `—` trong chú thích dòng 1 — **chặn commit của MỌI
phiên**, kể cả các phiên ⛔ không liên quan gì tới nó.

Đây là lần thứ **ba** trong một ngày một thứ ⛔ không thuộc kho chặn cả kho:

| Thứ | Chặn gì |
|---|---|
| `LTTGateBaseline68cde0/` (worktree trong kho) | bánh cóc `ruff` đếm **gấp đôi** |
| `apps/upscalevideo/jobs.py` một chuỗi chưa bọc `_()` | `check_i18n` |
| `deploy.ps1` chưa theo dõi | `check_ascii_cau_hinh` |

⇒ Cả ba cùng một hình: **phép đo nói về "kho này" nhưng đếm thứ nằm trên ĐĨA.**

## Luật đúng: chặn theo tệp ĐÃ THEO DÕI, cảnh báo cho phần còn lại

`git ls-files` là tập "cái gì thuộc kho này" — và nó gồm cả tệp **đang staged**, nên
một tệp mới tôi sắp commit **vẫn bị chặn** (đúng: đó là lúc phải bắt).

⚠️ Nhưng ⛔ không được **im lặng** với tệp chưa theo dõi: một `.ps1` có ký tự ngoài
   ASCII sẽ vỡ khi **ai đó chạy nó**, dù nó chưa vào kho. Nên nó vẫn được in ra, chỉ
   là ⛔ không làm đỏ. Bỏ hẳn phần cảnh báo là đổi một báo động giả thành một điểm mù.

⭐ Và chiều hỏng là chiều **rẻ**: một tệp rơi khỏi phạm vi thì nó chỉ **không được
   kiểm** (bỏ sót, im lặng, cần một cửa khác bắt). Còn báo động giả thì làm người ta
   **TẮT cổng** — đắt hơn nhiều.
"""
from __future__ import annotations

import subprocess

from tools import check_ascii_cau_hinh as kt


def _da_theo_doi() -> set[str]:
    ra = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                        cwd=str(kt.GOC), timeout=90)
    return {d.strip().replace("\\", "/") for d in ra.stdout.splitlines() if d.strip()}


def test_tap_CHAN_chi_gom_tep_da_theo_doi():
    theo_doi = _da_theo_doi()
    for p in kt.can_soi_chan():
        rel = p.relative_to(kt.GOC).as_posix()
        assert rel in theo_doi, (
            f"{rel} KHONG duoc git theo doi — mot tep rac khong duoc chan ca kho")


def test_tep_chua_theo_doi_van_duoc_NEU_RA_chu_khong_bi_bo_qua():
    """⛔ Im lặng với nó là đổi một báo động giả thành một điểm mù."""
    chan = {p.as_posix() for p in kt.can_soi_chan()}
    tat_ca = {p.as_posix() for p in kt.can_soi()}
    assert chan <= tat_ca, "tap chan phai la con cua tap soi"


def test_van_chan_duoc_tep_DA_THEO_DOI(tmp_path, monkeypatch):
    """Đừng nới thành "không chặn gì": một `.ps1` đã commit có ký tự lạ phải đỏ."""
    (tmp_path / "setup").mkdir()
    xau = tmp_path / "setup" / "co_dau.ps1"
    xau.write_bytes("# Deploy — em dash\n".encode())
    monkeypatch.setattr(kt, "GOC", tmp_path)
    monkeypatch.setattr(kt, "_da_theo_doi_git",
                        lambda: {"setup/co_dau.ps1"})
    assert [p.name for p in kt.can_soi_chan()] == ["co_dau.ps1"]


def test_git_khong_chay_duoc_thi_CHAN_TAT_CA_chu_khong_cho_qua(tmp_path, monkeypatch):
    """⛔ `git` im thì ⛔ không được biến thành "không tệp nào thuộc kho".

    Đó là fail-open: một lỗi công cụ sẽ **tắt** bánh cóc, im lặng. Chưa biết thì
    kiểm hết — thà báo động giả còn hơn tắt cổng mà không ai hay.
    """
    (tmp_path / "setup").mkdir()
    (tmp_path / "setup" / "a.ps1").write_bytes(b"# ascii only\n")
    monkeypatch.setattr(kt, "GOC", tmp_path)
    monkeypatch.setattr(kt, "_da_theo_doi_git", lambda: None)
    assert [p.name for p in kt.can_soi_chan()] == ["a.ps1"]
