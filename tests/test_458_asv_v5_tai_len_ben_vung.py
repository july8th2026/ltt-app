"""Pha V5 R1 — duong tai len BEN VUNG co client that.

## Vi sao tep nay ton tai

`CURRENT_UI_AUDIT.md` §2 xep day la **P0-1**, muc dau bang:

    Route `cap_ve` va `platform_core.upload_sessions` DA song va da co nguoi goi
    that. ASV co route nhung **khong co client**. He qua: tran that cua san pham
    la 90 MB, khong phai 2 GiB.

Va `V5_UX_AUDIT.md` §3 do lai sau khi xay xong Studio: van chua noi. Tep nay la
nua con thieu — no chot rang **client ton tai** va **no lui dung cach khi khong
di duong ben vung duoc**.

## ⛔ Cai tep nay KHONG chung minh duoc

Tren may phat trien va trong bo test, kho la `LocalStorage`, va no **khong cap
presigned PUT** — `tao_ve_tai_len` tra `{"mode": "local"}`. Nen cu `PUT` that
len R2 **khong co duong nao chay o day**.

⇒ Nhung phep kiem duoi day chot: hop dong cua ve, duong LUI, va cac bat bien cua
  client doc duoc bang AST. Chung **khong** chot rang mot tep 500 MB len duoc R2.
  Dieu do can mot moi truong co R2 that, va no phai duoc noi ra chu khong duoc
  giau duoi mot bo phep kiem xanh.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

DUONG_JS = (Path(__file__).resolve().parents[1] / "server" / "static" / "asv.js")
DUONG_HTML = (Path(__file__).resolve().parents[1] / "apps" / "auto_scan_video"
              / "templates" / "asv_trang_chinh.html")


def _js() -> str:
    return DUONG_JS.read_bytes().decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  A. Client CO THAT — day la menh de ma P0-1 doi
# ══════════════════════════════════════════════════════════════════════════════

def test_client_CO_goi_duong_cap_ve():
    """🔴 Truoc R1, `asv.js` khong nhac toi `/ve` mot lan nao, va o `upload_id`
    khong co trong form. Route song, nhung khong ai voi toi.

    ⚠️ Chot theo **duong dan lay tu template** chu khong theo chuoi `"/ve"` go
       cung: route prefix do `MANIFEST` quyet, va mot ban go cung se im lang sai
       ngay khi prefix doi.
    """
    js = _js()
    assert "asv-ve" in js, "client khong doc o cau hinh cap ve"
    assert "data-url" in js, "client tu ghep duong thay vi doc tu template"
    html = DUONG_HTML.read_bytes().decode("utf-8")
    assert 'name="upload_id"' in html, "form thieu o upload_id"
    assert "/ve" in html, "template khong cung cap duong cap ve"


def test_form_van_co_o_upload_id_RONG_luc_dung_trang(moi_truong):
    """⛔ O nay chi duoc co gia tri khi cu PUT **da xong**. Dat som la noi doi
    voi `routes.tao`: no uu tien `upload_id` va se tao mot lan chay tro vao mot
    tep chua ton tai."""
    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video").text
    m = re.search(r'<input[^>]*name="upload_id"[^>]*>', van)
    assert m, "trang khong co o upload_id"
    assert 'value=""' in m.group(0), "o upload_id co san gia tri — khong duoc"


# ══════════════════════════════════════════════════════════════════════════════
#  B. Bat bien khong duoc mat — moi cai la mot cach hong THAT
# ══════════════════════════════════════════════════════════════════════════════

def test_client_TAT_o_chon_tep_truoc_khi_nop():
    """🔴 Bat bien dat nhat cua ca R1.

    `routes.tao` uu tien `upload_id` va tra ve **truoc khi** cham toi `video` —
    nhung trinh duyet thi **da gui ca than multipart roi**. Tuc tep di len HAI
    LAN, va lan thu hai dam thang vao dung cai tran 100 MB cua Cloudflare ma ta
    vua tranh.

    ⭐ Va phai `disabled`, khong duoc `value = ""`: o chon tep co `required`, nen
       mot o rong ma con `required` se chan ca form — hong theo kieu "bam nut
       khong co gi xay ra".
    """
    js = _js()
    assert "oTep.disabled = true" in js, (
        "client khong tat o chon tep — tep se di len hai lan")
    assert 'oTep.value = ""' not in js, (
        "dung `value=\"\"`: o co `required`, form se bi chan")


def test_client_LUI_ve_multipart_khi_khong_co_ve():
    """`{"mode":"local"}` la cau tra loi THAT cua `LocalStorage`, khong phai loi.
    Client phai lui ve duong multipart, khong duoc dung lai va bao loi."""
    js = _js()
    assert '"direct"' in js, "client khong phan biet duoc mode"
    assert "catch" in js, "khong co duong lui khi xin ve that bai"


def test_client_KHONG_xin_ve_cho_kieu_duong_ben_vung_TU_CHOI():
    """⚠️ `KIEU_VIDEO_HOP_LE` (mp4/quicktime/x-m4v) HEP HON `KIEU_VIDEO` cua
    duong multipart (them mkv/webm). O chon tep nhan ca bon.

    Khong loc o client thi khach chon mot tep `.mkv` se nhan mot loi **cap ve**
    kho hieu, thay vi lang le di duong multipart von chay tot cho no.
    """
    js = _js()
    assert "data-kieu-ben-vung" in js, "client khong loc kieu truoc khi xin ve"


def test_client_bao_TIEN_DO_bang_XHR_chu_khong_fetch():
    """`fetch` khong bao duoc tien do TAI LEN. Voi mot tep hang tram MB, khong
    co thanh tien do thi trang dung im vai phut va khach tuong may treo."""
    js = _js()
    assert "XMLHttpRequest" in js
    assert "upload.onprogress" in js


# ══════════════════════════════════════════════════════════════════════════════
#  C. Hop dong cua ve — o TANG DICH VU
# ══════════════════════════════════════════════════════════════════════════════

def test_ve_tra_ve_local_khi_kho_khong_cap_duoc_presigned(moi_truong):
    """Doi chung: tren `LocalStorage`, `/ve` tra `{"mode":"local"}` — mot cau
    tra loi THAT, va client lui ve multipart."""
    _app, a, csrf, _b, _cb = moi_truong
    r = a.post("/auto-scan-video/ve",
               data={"csrf_token": csrf, "ten_tep": "a.mp4",
                     "kieu": "video/mp4", "co": 1024})
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("mode") == "local"


def test_tran_ben_vung_LON_HON_tran_multipart():
    """🔑 Ca diem cua R1. Neu hai tran bang nhau thi duong ben vung khong go bo
    gi, va cong sua nay khong co ly do ton tai."""
    from apps.auto_scan_video import features, routes

    assert features.TRAN_BEN_VUNG > routes.TRAN_TAI_LEN
    assert features.TRAN_BEN_VUNG == 2 * 1024 * 1024 * 1024


def test_trang_noi_ca_HAI_tran_cho_client(moi_truong):
    """Client phai doc hai so nay tu template — go tay o JavaScript la tao mot
    ban thu hai se troi khi hang so doi."""
    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video").text
    assert 'data-tran-ben-vung="2048"' in van
    assert "data-kieu-ben-vung=" in van


# ══════════════════════════════════════════════════════════════════════════════
#  D. Duong cu KHONG duoc hong
# ══════════════════════════════════════════════════════════════════════════════

def test_duong_multipart_van_tao_duoc_lan_chay(moi_truong, tmp_path):
    """R1 them mot duong, khong thay mot duong. Tren `LocalStorage` — tuc trong
    ca bo test — duong multipart van la duong duy nhat chay duoc."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    r = _mt._tao_run_cho(a, csrf, tmp_path)
    assert r.status_code == 200, r.text[:300]
    assert "/run/" in r.url.path


@pytest.mark.parametrize("kieu", ["video/mp4", "video/quicktime"])
def test_kieu_duoc_ca_HAI_duong_chap_nhan(kieu):
    """Hai kieu nay phai di duoc ca hai duong — neu khong, mot khach co tep mp4
    se roi vao khe giua hai chinh sach."""
    from apps.auto_scan_video import features, routes

    assert kieu in routes.KIEU_VIDEO
    assert kieu in features.KIEU_VIDEO_HOP_LE
