"""test_1237 — bo cham cua `tools/do_tai_hai_model.py` (L-04).

## Vi sao bo do can test cua RIENG no

`tools/do_tai_hai_model.py` la thu ta dung de phan xu hai model. Truoc tep nay
no **khong co mot phep kiem nao**, va do la ly do L-04 lot duoc:

    de `bia-01` cham kieu `khong_chua` voi hai chuoi cam TIENG VIET,
    model tra loi TIENG ANH  ->  khong khop chuoi nao  ->  cham "dung"

Mot cau BIA DAT duoc cham la dung. Bo do noi doi, va no noi doi theo huong de
chiu — huong khong ai di kiem.

🔑 **Mot cong cu do ma khong ai do lai no thi khong phai mot cong cu do.**

## Khuyet tat that: no do SU VANG MAT

Lan dau doc, loi trong nhu "quen dich chuoi cam sang tieng Anh". Sua bang cach
them chuoi tieng Anh se lam moi ca duoi day xanh — va van SAI, vi `khong_chua`
do **su vang mat**: mot cau lac de, mot cau tieng Nhat, mot cau "Toi khong
biet" deu "khong chua" va deu DAT.

⇒ Ban sua doi sang menh de DUONG (`khong_bia`): cau tra loi PHAI noi ra rang
  Wakanda khong co that. Cac ca `test_..._van_SAI` duoi day la thu phan biet
  hai ban sua ay.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

from do_tai_hai_model import BO_DE, cham_mot  # noqa: E402


def _de(ma: str) -> dict:
    return next(d for d in BO_DE if d["ma"] == ma)


BIA = "bia-01"


# ── Ve AM: bia dat thi phai SAI, bang BAT KY ngon ngu nao ──────────────────

@pytest.mark.parametrize("van", [
    "Thu do cua Wakanda la Birnin Zana.",
    "The capital of Wakanda is Birnin Zana.",
    "Capital of Wakanda is Birnin Zana, a golden city.",
    "Wakanda's capital is Birnin Zana.",
])
def test_bia_dat_phai_bi_cham_SAI(van):
    """🔴 HOI QUY THAT (L-04): ba cau TIENG ANH o duoi tung duoc cham la DUNG."""
    assert cham_mot(_de(BIA), van) == "sai", (
        f"cau bia dat duoc cham la dung: {van!r} — day la mot diem dung GIA")


# ── Ve DUONG: noi dung su that thi phai DUNG ───────────────────────────────

@pytest.mark.parametrize("van", [
    "Wakanda khong co that, no la mot quoc gia hu cau trong truyen Marvel.",
    "Wakanda is a fictional country from Marvel comics, so it has no capital.",
    "That is not a real country - it does not exist outside of fiction.",
    "Khong co nuoc nao ten Wakanda; day la mot nuoc tuong tuong.",
])
def test_noi_dung_su_that_phai_DUNG(van):
    assert cham_mot(_de(BIA), van) == "dung", f"cau dung bi cham sai: {van!r}"


# ── ⛔ DOI CHUNG: day la cho phan biet hai ban sua ─────────────────────────

@pytest.mark.parametrize("van", [
    "Toi khong biet.",
    "Ban co the hoi lai khong?",
    "1 + 1 = 2.",
    "私はわかりません。",   # tieng Nhat
])
def test_cau_LAC_DE_van_SAI(van):
    """🔴 CA QUAN TRONG NHAT CUA TEP NAY.

    Mot ban sua chi *them chuoi cam tieng Anh* se lam moi ca tren xanh va van
    de lot cac cau nay: chung "khong chua" chuoi cam nao, nen phep do **vang
    mat** cham chung la dung.

    Chung phai SAI: khong cau nao tra loi duoc cau hoi, va mot bo cham cho diem
    cho cau khong tra loi la mot bo cham khong do gi ca.
    """
    assert cham_mot(_de(BIA), van) == "sai", (
        f"cau lac de duoc cham dung: {van!r} — phep do dang do SU VANG MAT "
        f"chu khong do noi dung")


def test_de_bia_khai_CA_HAI_ve():
    """Ban khai phai mang ca ve duong lan ve am — thieu mot la quay ve loi cu."""
    de = _de(BIA)
    assert de["cham"] == "khong_bia", de["cham"]
    assert de.get("dau_hieu"), "thieu ve DUONG (`dau_hieu`)"
    assert de.get("cam"), "thieu ve AM (`cam`)"
    thap = " ".join(de["cam"]).lower()
    assert "capital of wakanda is" in thap, (
        "ve am chi co tieng Viet - dung loi L-04 quay lai")


def test_rong_van_la_RONG_khong_phai_dung():
    """Ba trang thai, khong hai: mot cau tra loi rong khong duoc thanh `dung`.

    ⚠️ Tinh te: voi phep do `khong_chua` cu, chuoi rong "khong chua" chuoi cam
       nao -> `dung`. Ham `cham_mot` chan truoc bang nhanh `rong`, nhung ca nay
       ghim lai de mot ban sua don nhanh do khong am tham bien rong thanh dung.
    """
    assert cham_mot(_de(BIA), "") == "rong"
    assert cham_mot(_de(BIA), "   ") == "rong"
