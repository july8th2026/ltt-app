"""Bo canh /health/ready may B - N-05.

Khong goi mang that: tiem ham `doc` de mo phong ba tinh huong da xay ra that
(200 san sang, 503 thieu_card 23/09, khong noi duoc khi may B mat mang).
"""
from __future__ import annotations

from tools.canh_cong_may_b import kiem


def test_200_la_san_sang():
    kq = kiem("http://x/health/ready", doc=lambda u: (200, {"ok": True}))
    assert kq["ok"] is True and kq["http"] == 200


def test_503_thieu_card_la_bao_dong():
    kq = kiem("http://x/health/ready", doc=lambda u: (503, {"ok": False, "ly_do": "thieu_card"}))
    assert kq["ok"] is False and kq["ly_do"] == "thieu_card"


def test_khong_noi_duoc_cung_la_bao_dong():
    def hong(_u):
        raise OSError("khong noi duoc")
    kq = kiem("http://x/health/ready", doc=hong)
    assert kq["ok"] is False and "khong_noi_duoc" in kq["ly_do"]


def test_200_nhung_ok_false_van_la_bao_dong():
    """Doi chung: status HTTP dung ma than khong xac nhan `ok` thi van la loi."""
    kq = kiem("http://x/health/ready", doc=lambda u: (200, {"ok": False}))
    assert kq["ok"] is False
