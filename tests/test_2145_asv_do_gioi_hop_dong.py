"""ASV final — hop dong cua bo do `gioi` + cong cu `do_gioi_giong` (khong nap model).

Chot BA thu ma mot lan sua vo y de lam truot, va ca ba deu truot IM LANG:

  ① ban ghim cua weights (repo/revision/sha256/so byte) — doi mot ky tu la doi
     ca ket qua do, ma khong co gi bao;
  ② thu tu lop cua checkpoint (`0 = male`) — dao no thi moi so van "hop ly";
  ③ kich ban do — mot kich ban co chu so se duoc `chuan_hoa` doc tran, va cot
     "tu/phut" cua bang xep hang het nghia.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from apps.asv_gpu.do_luong import gioi
from apps.asv_gpu.do_luong._ecapa_gioi import ban_ghim
from apps.asv_gpu.do_luong._ecapa_gioi.ecapa_gioi import LOP
from tools import do_gioi_giong as cc

VENDOR = pathlib.Path(ban_ghim.__file__).resolve().parent


def test_ban_ghim_la_ban_da_xac_minh():
    """Ban ghim 23/09/2026. Doi cac hang so nay = doi model, phai co doan do moi."""
    assert ban_ghim.REPO == "JaesungHuh/voice-gender-classifier"
    assert ban_ghim.REVISION == "db1222153bd60337e900be22add7af180452adc0"
    assert ban_ghim.SHA256 == (
        "2d8e0be1fdf159d60d5087416e6f6277c5e30ce9e33a61c767a9a409e6c503c5")
    assert ban_ghim.SO_BYTE == 61_907_512
    assert ban_ghim.C == 1024
    # Phien ban di vao ket qua: no phai MANG ban ghim, khong phai mot so tay.
    assert ban_ghim.REVISION[:12] in gioi.PHIEN_BAN
    assert ban_ghim.SHA256[:12] in gioi.PHIEN_BAN


def test_thu_tu_lop_khong_duoc_dao():
    """`0 = male` la mot phan cua TRONG SO da cong bo, khong phai quy uoc cua ta."""
    assert LOP == ("male", "female")


def test_giay_phep_di_kem_ma_nhung():
    """MIT bat buoc giu nguyen van ban giay phep + ghi cong khi phan phoi lai."""
    lic = (VENDOR / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in lic
    assert "Copyright (c) 2024 jaesunghuh" in lic
    notice = (VENDOR / "NOTICE").read_text(encoding="utf-8")
    # NOTICE phai dan ca commit upstream lan ban ghim — do la thu lam cho no
    # kiem tra duoc thay vi chi de doc.
    assert "49bcbecfd929ba5a043bde645fdff1a375eb79c7" in notice
    assert ban_ghim.SHA256 in notice
    assert "TaoRuijie/ECAPA-TDNN" in notice


def test_kich_ban_khong_co_so_hay_viet_tat():
    """Kich ban do phai la thu hai giong doc RA GIONG NHAU ve do dai chu.

    `text_pipeline.chuan_hoa` doc tran chu so va viet tat, nen mot kich ban co
    "2024" se dai ngan khac nhau tuy khuon chuan hoa — va cot "tu/phut" trong
    bang xep hang la mot phep chia cho so tu cua kich ban.
    """
    for ma, (lan, chu) in cc.KICH_BAN.items():
        assert lan in ("vi", "en"), ma
        assert not re.search(r"\d", chu), f"{ma} co chu so"
        assert "(" not in chu and "http" not in chu, ma
        assert 55 <= len(chu.split()) <= 130, (ma, len(chu.split()))


def test_gioi_khai_doc_dung_xuat_xu():
    """Nhan KHAI (thu dang bi kiem), khong phai nhan DO."""
    assert cc.gioi_khai("harry_male_adventure.wav", "Aaron — nam, phiêu lưu") == "nam"
    assert cc.gioi_khai("bella_nu.wav", "Clara — nữ, thuyết minh") == "nu"
    assert cc.gioi_khai("hoathinh_female.wav", "Lulu — nữ, hoạt hình") == "nu"
    assert cc.gioi_khai("bietdoi_girl.wav", "Nova — nữ, hoạt hình") == "nu"
    assert cc.gioi_khai("ht3d_men.wav", "Victor — nam, kể chuyện") == "nam"
    # Robin: xuat xu KHAI `male` — day dung la dong ma phep do phai doi chat.
    assert cc.gioi_khai("khanh_male_entertainment.wav",
                        "Robin — giải trí, biến hoá giọng") == "nam"
    # Ten tep cu khong mang dau hieu nao -> lay tu ten hien thi da duyet.
    assert cc.gioi_khai("Huong_KT.wav", "Diễm Chi — nữ, kể chuyện ngôn tình") == "nu"


#: ⛔ Dieu kien la MOT: co `manifest.json` trong kho clip goc hay khong.
#:    Ban cu con ve thanh `not cc.KHO_GIONG_CHUNG.is_file() and ...`, nhung
#:    `KHO_GIONG_CHUNG` la mot THU MUC, nen `.is_file()` cua no khong bao gio
#:    dung — nua dau la mot nhan chet, va no lam nguoi doc tuong co hai duong
#:    thoa man hang rao nay. Cung mot cach hoi voi `test_2144`.
@pytest.mark.skipif(not (cc.KHO_GIONG_CHUNG / "manifest.json").is_file(),
                    reason="khong co kho clip goc tren may nay")
def test_viec_sinh_phu_het_45_giong():
    """20 preset (tap hieu chinh CO NHAN) + 25 giong kho chung, khong sot."""
    viec = cc._viec_sinh()
    preset = [v for v in viec if v["loai"] == "preset"]
    chung = {v["public_id"] for v in viec if v["loai"] == "chung"}
    assert len(preset) == 20
    assert len(chung) == 25
    # Moi preset PHAI co nhan giới — neu khong thi tap hieu chinh rong cho no.
    assert all(v["gioi_nhan"] in ("nam", "nu") for v in preset)
    # Giong `en` doc HAI kich ban (xep hang can hon mot ban), `vi` doc mot.
    en = [v for v in viec if v["loai"] == "chung" and v["ngon_ngu"] == "en"]
    vi = [v for v in viec if v["loai"] == "chung" and v["ngon_ngu"] == "vi"]
    assert len(en) == 34 and len(vi) == 8
    assert len({v["ma"] for v in viec}) == len(viec)


def test_khong_co_venv_thi_khong_kha_dung(tmp_path, monkeypatch):
    """Thieu qc-venv ⇒ `KhongKhaDung`, KHONG lui ve mot heuristic tu che."""
    monkeypatch.setenv("LTT_QC_PYTHON", str(tmp_path / "khong-co.exe"))
    with pytest.raises(gioi.venv.KhongKhaDung):
        gioi.do_gioi([{"ma": "x", "tep": str(tmp_path / "x.wav")}])
