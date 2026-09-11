"""ASV V6 pha 32 — huy HAI buoc, song sot qua luot hoi lai cua htmx.

🔴 Truoc pha 32 mot cu bam "Huy lan chay" la huy — va huy la trang thai CUOI:
   `huy_run` quyet toan ngay, `thu_lai` tu choi lan chay da ket thuc. Mot cu bam
   truot tay la mat mot lan chay da tra tien.

⭐ Hanh vi that (mo bang ban phim, song qua 2 luot hoi lai, chi buoc hai moi gui
   POST) duoc chung minh tren trinh duyet — `PHA32_UX_A11Y.md` §2, kem doi chung
   bo `hx-preserve` thi khung TU DONG sau 2 luot. Cac bai o day chot HINH DANG
   tren trang may chu dung that.
"""
from __future__ import annotations

import re

from tests import test_423_asv_giao_dien as _mt
from tests.test_475_asv_v6_voice_binding import _mau

moi_truong = _mt.moi_truong


def _tao_run(a, csrf, tmp_path):
    from tests.fixtures.asv_media import tiny_mp4

    tep = tiny_mp4(tmp_path / "a.mp4", duration_s=1.0)
    with open(tep, "rb") as f:
        r = a.post("/auto-scan-video/tao", data={
            "csrf_token": csrf, "che_do": "fit_original", "che_do_giong": "USER_SELECTED",
            "giong_id": _mau()}, files={"video": ("a.mp4", f, "video/mp4")})
    assert r.status_code == 200, r.status_code
    return str(r.url).rstrip("/").rsplit("/", 1)[-1], r.text


def _khoi_huy(van):
    m = re.search(r'<details[^>]*id="asv-huy"[^>]*>(.*?)</details>', van, re.S)
    assert m, "khong co khung huy hai buoc"
    return m.group(0), m.group(1)


def test_huy_la_HAI_buoc_nut_that_nam_TRONG_khung_xac_nhan(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    _id, van = _tao_run(a, csrf, tmp_path)
    ca, trong = _khoi_huy(van)
    tom = re.search(r"<summary[^>]*>(.*?)</summary>", trong, re.S).group(1)
    assert "Huỷ lần chạy" in tom and "<button" not in tom and "<form" not in tom
    form = re.search(r'<form[^>]*action="[^"]*/huy"[^>]*>.*?</form>', trong, re.S)
    assert form and 'type="submit"' in form.group(0)
    # ⛔ Khong duoc con mot nut huy MOT buoc nao ngoai khung.
    ngoai = van.replace(ca, "")
    assert not re.search(r'action="[^"]*/huy"', ngoai), "con mot duong huy mot buoc"


def test_khung_xac_nhan_NOI_RO_hau_qua(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    _id, van = _tao_run(a, csrf, tmp_path)
    _ca, trong = _khoi_huy(van)
    assert "dừng hẳn" in trong and "hoàn lại" in trong and "tạo lần chạy mới" in trong


def test_khung_xac_nhan_SONG_SOT_qua_luot_hoi_lai(moi_truong, tmp_path):
    """⚠️ Manh tien do bi htmx thay `outerHTML` 3 giay mot lan."""
    _app, a, csrf, _b, _cb = moi_truong
    run_id, van = _tao_run(a, csrf, tmp_path)
    assert 'hx-trigger="every 3s"' in van
    ca, _ = _khoi_huy(van)
    assert 'hx-preserve="true"' in ca
    manh = a.get(f"/auto-scan-video/run/{run_id}/tien-do").text
    assert 'hx-preserve="true"' in _khoi_huy(manh)[0], "manh hoi lai mat id/hx-preserve"


def test_huy_van_CHAY_qua_HTTP(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    run_id, _ = _tao_run(a, csrf, tmp_path)
    r = a.post(f"/auto-scan-video/run/{run_id}/huy", data={"csrf_token": csrf})
    assert r.status_code == 200
    assert 'id="asv-huy"' not in r.text, "lan chay da huy van hien khung huy"
