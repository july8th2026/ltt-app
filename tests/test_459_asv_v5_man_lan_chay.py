"""Pha V5 R4 — man LAN CHAY o ba trang thai, voi du lieu THAT trong man hinh.

## Vi sao tep nay ton tai, va vi sao no khong can may B

`V5_UX_AUDIT.md` xep `R4` la *"chay lai audit tren man tien do/ket qua sau khi
co mot luot chay that"*, va no bi coi la **chan boi may B** suot may gio.

⛔ Do la mot phep suy sai, va no ton thoi gian that. `R4` la mot bai audit
   **GIAO DIEN**. Mot bai audit giao dien can **du lieu that trong man hinh**,
   khong can mot **mach chay that**. Gop hai thu lam mot la tu chan minh bang
   mot dieu kien khong lien quan.

⇒ Tep nay gieo ba lan chay o ba trang thai roi doi chieu man hinh. No **khong**
  cham `nghiem_thu_hien_hanh.json` — ghi de tep do la ghi de bang chung nghiem
  thu cua san pham, mot viec thuoc quyet dinh cua chu du an.

## Ba khiem khuyet tep nay chot lai, ca ba do `R4` tim ra

1. Tieu de noi **"Dang long tieng"** cho mot lan chay **da hong**.
2. Dong ho **khong bao gio hien** o SQLite (nhanh nuot `TypeError`).
3. `elapsed 621s` — mot con so, khong phai mot khoang thoi gian doc duoc.
"""
from __future__ import annotations

import datetime as dt

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong


def _gieo(db, owner_id, ma, trang_thai, so_xong, *, loi="", ket_qua=False,
          phut_truoc=8):
    """Mot lan chay o mot trang thai cu the. Khong chay mach nao."""
    from apps.auto_scan_video import pipeline, tables as T

    bay_gio = dt.datetime.now(dt.timezone.utc)
    ten = list(pipeline.TEN_GIAI_DOAN)
    r = T.AsvRun(id=ma, owner_id=owner_id, status=trang_thai,
                 source_key="v/nguon.mp4",
                 settings={"preset": "smart_localize", "timing_mode": "natural",
                           "giong_id": "Minh Đức"},
                 credit_held=140, credit_actual=118, error=loi,
                 created_at=bay_gio - dt.timedelta(minutes=phut_truoc))
    if trang_thai in ("done", "error", "cancelled"):
        r.finished_at = bay_gio
    db.add(r)
    for i, t in enumerate(ten):
        if i < so_xong:
            tt = T.STAGE_SUCCEEDED
        elif i == so_xong:
            tt = "failed_terminal" if trang_thai == "error" else "running"
        else:
            tt = T.STAGE_PENDING
        st = T.AsvStage(run_id=ma, owner_id=owner_id, stage=t, status=tt,
                        attempt=1, error=(loi if tt == "failed_terminal" else ""),
                        started_at=bay_gio - dt.timedelta(minutes=phut_truoc - i))
        # 🔴 Ban giao la `IMAGE_FINISH` (b4 25/09): `render` giao ban trung gian.
        if ket_qua and t == pipeline.IMAGE_FINISH and tt == T.STAGE_SUCCEEDED:
            st.outputs = {"khoa_asset": [f"v/{ma}-ra.mp4"]}
            db.add(T.AsvAsset(owner_id=owner_id, run_id=ma, created_by_stage=t,
                              kind="video", storage_key=f"v/{ma}-ra.mp4",
                              size=1024))
        db.add(st)
    db.commit()
    return r


@pytest.fixture()
def ba_lan_chay(moi_truong):
    """Ba lan chay cua NGUOI A: dang chay · da xong · hong."""
    import platform_core.db as dbmod
    from apps.auto_scan_video import pipeline
    from platform_core.models import User

    app, a, csrf_a, b, csrf_b = moi_truong
    db = next(dbmod.get_session())
    u = db.query(User).filter(User.email == "asv-a@example.com").first()
    n = len(pipeline.TEN_GIAI_DOAN)
    _gieo(db, u.id, "r4-chay", "running", 5)
    _gieo(db, u.id, "r4-xong", "done", n, ket_qua=True, phut_truoc=14)
    _gieo(db, u.id, "r4-hong", "error", 5, loi="content_process: khong hoan tat")
    db.close()
    return a, b


# ══════════════════════════════════════════════════════════════════════════════
#  A. Tieu de phai khop TRANG THAI
# ══════════════════════════════════════════════════════════════════════════════

def test_lan_chay_HONG_khong_duoc_noi_dang_chay(ba_lan_chay):
    """🔴 Khiem khuyet `R4` tim ra.

    Ban dau template chi phan biet `done` voi "moi thu con lai", nen mot lan chay
    **da hong** van doi tieu de *"Dang long tieng"* — khach doc mot dong noi viec
    dang chay ngay ben tren mot khung do noi viec da dung.

    ⚠️ No **chi lo ra khi co du lieu that o trang thai do**. Moi phep kiem truoc
       do cua V5 deu di qua duong xanh, nen khong bai nao cham toi nhanh nay.
    """
    a, _b = ba_lan_chay
    van = a.get("/auto-scan-video/run/r4-hong").text
    assert "Đang lồng tiếng" not in van, "lan chay hong ma tieu de noi dang chay"


def test_moi_trang_thai_co_mot_tieu_de_RIENG(ba_lan_chay):
    a, _b = ba_lan_chay
    tieu_de = {}
    for ma in ("r4-chay", "r4-xong", "r4-hong"):
        van = a.get(f"/auto-scan-video/run/{ma}").text
        i = van.index('id="asv-ct"')
        tieu_de[ma] = van[i:i + 200]
    assert len({t.strip() for t in tieu_de.values()}) == 3, (
        "hai trang thai dung chung mot tieu de")


# ══════════════════════════════════════════════════════════════════════════════
#  B. Dong ho — nhanh nuot loi da lam no VO HINH o moi noi ta nhin
# ══════════════════════════════════════════════════════════════════════════════

def test_dong_ho_HIEN_tren_SQLite(ba_lan_chay):
    """🔴 Cot khai `DateTime(timezone=True)`, nhung **SQLite khong luu mui gio**.

    `_now()` ghi UTC; SQLite doc ra naive. Ban dau `_tien_do_khach` bat
    `TypeError` roi tra `None` — nen dong ho **khong bao gio hien** o dev lan
    trong bo test, va chi production (PostgreSQL) moi co.

    ⛔ Do la kieu lech te nhat: **dung o cho khong ai soi, sai o moi cho ta
       nhin**. Mot loi nhu the co the song rat lau.
    """
    a, _b = ba_lan_chay
    van = a.get("/auto-scan-video/run/r4-chay").text
    assert "asv-dong-ho" in van
    i = van.index("asv-dong-ho")
    doan = van[i:i + 300]
    assert "%" in doan
    assert "giây" in doan or "seconds" in doan, (
        "dong ho khong hien thoi gian da chay")


def test_thoi_gian_dai_hien_theo_PHUT_khong_phai_giay_tho(ba_lan_chay):
    """`621s` la mot con so, khong phai mot khoang thoi gian doc duoc. Mot lan
    chay muoi phut bat khach tu chia."""
    a, _b = ba_lan_chay
    van = a.get("/auto-scan-video/run/r4-chay").text
    i = van.index("asv-dong-ho")
    doan = van[i:i + 300]
    assert "phút" in doan or "minute" in doan, (
        "thoi gian dai van hien bang giay tho")


# ══════════════════════════════════════════════════════════════════════════════
#  C. Moi trang thai bay dung thu no can — va KHONG bay thu no khong co
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_lan_chay_XONG_moi_co_doi_chieu_nguon_ket_qua(ba_lan_chay):
    a, _b = ba_lan_chay
    assert "asv-doi-chieu" in a.get("/auto-scan-video/run/r4-xong").text
    for ma in ("r4-chay", "r4-hong"):
        assert "asv-doi-chieu" not in a.get(f"/auto-scan-video/run/{ma}").text, (
            f"{ma} bay khung doi chieu ma chua co ket qua")


def test_chi_lan_chay_HONG_moi_co_khoi_loi_bon_cau(ba_lan_chay):
    a, _b = ba_lan_chay
    van = a.get("/auto-scan-video/run/r4-hong").text
    assert 'class="asv-loi"' in van
    # ⭐ Dong "khong tinh them credit" la dong ngan khach doan hau qua tien bac
    #    cua mot nut — va ho se doan ve phia khong dam bam.
    assert "credit" in van
    for ma in ("r4-chay", "r4-xong"):
        assert 'class="asv-loi"' not in a.get(f"/auto-scan-video/run/{ma}").text


def test_chi_lan_chay_DANG_CHAY_moi_hoi_lai_bang_htmx(ba_lan_chay):
    """⛔ Mot trang da xong ma van hoi lai moi 3 giay la mot vong lap vo ich chay
    mai — va no nhan len theo so tab khach de mo."""
    a, _b = ba_lan_chay
    assert "hx-trigger" in a.get("/auto-scan-video/run/r4-chay").text
    for ma in ("r4-xong", "r4-hong"):
        assert "hx-trigger" not in a.get(f"/auto-scan-video/run/{ma}").text


def test_nguoi_khac_khong_xem_duoc_ba_lan_chay_nay(ba_lan_chay):
    a, b = ba_lan_chay
    for ma in ("r4-chay", "r4-xong", "r4-hong"):
        assert b.get(f"/auto-scan-video/run/{ma}",
                     follow_redirects=False).status_code == 404
