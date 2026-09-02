"""Pha 19 muc 3 — engine da rut so voi ban di san, va cho lech nao la CO Y.

## Vi sao khong so sanh TEP RA

Cach hien nhien la chay ca hai ban tren cung dau vao roi so byte. No khong lam
duoc, va ly do dang biet: ban di san **khong chay duoc o day**. `mix_stems` doi
mot thu muc stem cua demucs; `replace_audio` doi mot video da qua xfade concat;
ca hai nam trong mot chuoi co trang thai rieng. Dung mot khuon do de chay chung
la viet lai ban di san — luc do ta so ban minh viet voi ban minh viet.

⇒ So **QUYET DINH**, khong so byte. Moi dong duoi day ghi mot lua chon cua ban
  di san, gia tri ta giu hay doi, va **vi sao**. Doi mot gia tri o day ma khong
  doi bang nay la lam hai tai lieu noi hai dieu khac nhau.

⭐ Bang nay khong phai tai lieu. No la ma chay: neu ai do doi mot hang so trong
   engine, phep kiem tuong ung do va nguoi do phai viet ra ly do — dung thu ma
   mot chu thich khong bao gio ep duoc.
"""
from __future__ import annotations

import inspect

from apps.auto_scan_video import ket_xuat, tach_tieng, thoi_gian

# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tach nguon + tron nen  <-  Cut_only/nerf_engine/stages/audio.py
# ══════════════════════════════════════════════════════════════════════════════

def test_giu_amix_normalize_0_cua_ban_di_san():
    """`audio.py:110` dung `amix=...:normalize=0`. Ta giu nguyen, va no la mot
    quyet dinh chu khong phai mot chi tiet: mac dinh `normalize=1` chia bien do
    cho so dau vao, nen am luong phu thuoc vao **so stem tim thay**."""
    ma = inspect.getsource(tach_tieng.tron_nen)
    assert "normalize=0" in ma


def test_LECH_CO_Y_6_ban_nen_giu_44k1_cua_htdemucs_chu_khong_48k():
    """⭐ Chinh phep kiem nay tim ra mot cho lech CHUA AI GHI.

    Ban dau no viet `assert TAN_SO_TACH == 48000` theo `audio.py:113`, va do —
    ta dung **44 100**. Lan theo thi ly do da nam san o `tach_tieng.py:58`:
    *"44,1 kHz stereo la dang model duoc huan luyen tren"*. htdemucs chay o
    44,1 kHz.

    ⇒ Ban di san lay mau lai **truoc** khi tach (hoac ep stem ve 48k luc tron);
      ta giu nguyen tan so goc cua model va lay mau lai **mot lan duy nhat, o
      RENDER** (`ket_xuat._loc_am` dat `aformat` cho moi dau vao). Cung mot so
      lan lay mau lai, nhung cua ta xay ra sau khi model da lam viec xong.

    ⚠️ Cho lech nay ton tai tu pha 09 va khong o bang nao ca. No khong gay hai —
       nhung mot cho lech khong ai ghi la mot cho lech se bi "sua" nham o luot
       sau, boi mot nguoi doc `audio.py` va tuong ta chep sai.
    """
    assert tach_tieng.TAN_SO_TACH == 44100
    assert tach_tieng.SO_KENH_TACH == 2
    # Va RENDER phai dua no ve 48k — neu khong, hai tan so gap nhau o `amix`.
    assert ket_xuat.ban_dung.TAN_SO_RA == 48000
    assert "aformat=sample_rates=" in inspect.getsource(ket_xuat._loc_am)


def test_LECH_CO_Y_1_khong_phoi_lai_tung_stem():
    """Ban di san cho moi stem mot `volume=<gain>` rieng (`audio.py:107`).

    ⛔ Ta KHONG lam vay, va do la mot khac biet **san pham**: ban di san dang
       lam mot ban phoi sang tao. MVP nay hua *giu lai nhac nen va tieng dong*,
       nen no phai giu nguyen tuong quan giua cac nhac cu ma tac gia da dung.
       Mot he so `drums_gain=0.7` la ta tu quyet dinh ban nhac cua khach nen
       nghe the nao.
    """
    ma = inspect.getsource(tach_tieng.tron_nen)
    assert "volume=" not in ma, (
        "dang phoi lai tung stem — doi tuong quan nhac cu cua tac gia")


def test_LECH_CO_Y_2_loudnorm_ngay_trong_cung_luot_ffmpeg():
    """Ban di san tron roi de viec chuan hoa cho mot buoc sau.

    Ta gop `loudnorm` vao cung mot lan chay: it hon mot vong giai ma/ma hoa, va
    it hon mot tep tam co the thanh rac khi worker chet giua chung.
    """
    ma = inspect.getsource(tach_tieng.tron_nen)
    assert "loudnorm" in ma
    assert ma.count("_chay(") == 1, "da tach thanh hai luot ffmpeg"


def test_stem_GIU_LAI_dung_ba_cai():
    """`vocals` bi bo — do la ca muc dich cua giai doan.

    ⚠️ Chot bang TAP HOP. Them mot stem ma quen cap nhat cho nay se lam do, va
       do la dieu ta muon: doi tap stem la doi thu khach nghe thay.
    """
    assert set(tach_tieng.STEM_GIU) == {"drums", "bass", "other"}
    assert "vocals" not in tach_tieng.STEM_GIU


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Render  <-  Cut_only/.../ffmpeg_edit_cutonly.py + DUNGVIDEO/assemble.py
# ══════════════════════════════════════════════════════════════════════════════

#: `replace_audio` (`ffmpeg_edit_cutonly.py:323`) va `_audio_encode_args`
#: (`assemble.py:199`). Da chot o `test_414::PARITY_DI_SAN`; o day chot phan
#: **hang so**, de mot lan doi chinh sach khong lot qua bang cach doi hang so
#: thay vi doi lenh.
def test_giu_chinh_sach_ma_hoa_cua_ban_di_san():
    assert ket_xuat.ban_dung.CODEC_TIENG == "aac"        # replace_audio
    assert ket_xuat.ban_dung.BITRATE_TIENG == "192k"     # replace_audio
    assert ket_xuat.ban_dung.TAN_SO_RA == 48000          # assemble.py:201
    assert ket_xuat.ban_dung.SO_KENH_RA == 2             # assemble.py:202
    assert ket_xuat.ban_dung.CHE_DO_HINH == "copy"       # replace_audio


def test_LECH_CO_Y_3_tron_NHIEU_LOP_theo_moc_thoi_gian():
    """Khong ban di san nao lam viec nay.

    `replace_audio` nhan **mot** tep tieng da tron san. Ta co N lop phai dat vao
    N moc khac nhau, moi lop co the co he so tang toc rieng. Do la phan moi cua
    pha 15, va no khong co ban doi chieu.
    """
    ma = inspect.getsource(ket_xuat._loc_am)
    assert "adelay" in ma and "amix" in ma


def test_LECH_CO_Y_4_loudnorm_tren_BAN_TRON_CUOI():
    """⭐ Lech nay khong den tu mot lua chon thiet ke — no den tu mot PHEP DO.

    Ban dau ta khong chuan hoa ban tron cuoi, giong ban di san. Cong QC cua pha
    18 do duoc **-12,58 LUFS** so voi dich -14 ± 1: nhac nen da chuan hoa cong
    them N lop tieng thi to hon ca hai. Ban di san khong gap loi nay vi no thay
    the tieng chu khong **cong them** tieng.
    """
    ma = inspect.getsource(ket_xuat._loc_am)
    assert "loudnorm" in ma
    assert "dual_mono=true" in ma, (
        "thieu `dual_mono` — mot lop mono da noi rong thanh stereo se bi do to "
        "hon thuc te 3 dB")
    assert ket_xuat.LUFS_DICH_RA == tach_tieng.LUFS_DICH, (
        "dich am luong cua ban ra lech voi dich cua nhac nen — hai con so cho "
        "cung mot muc chuan la hai con so se lech nhau")


def test_PHIEN_BAN_KET_XUAT_da_nang_khi_doi_cach_dung_lenh():
    """Doi bo loc ma khong nang phien ban thi moi lan chay lai dung tep cu."""
    assert ket_xuat.PHIEN_BAN_KET_XUAT >= 2


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Thoi gian  <-  SoniTranslate + Subdub (khong o trong kho)
# ══════════════════════════════════════════════════════════════════════════════

def test_nguong_MUON_deu_ghi_ro_nguon():
    """Hai nguong muon tu du an cong dong, mot nguong tu ta.

    ⚠️ Kho nay co luat: **muon nguong thi phai do lai**. Hai so dau chua duoc do
       lai tren du lieu that (RISK-13-*), va viec do duoc ghi trong ADR-003 chu
       khong bi giau. Phep kiem nay chi chot rang chung khong bi doi lang le.
    """
    assert thoi_gian.TY_LE_MUON_KHOANG_LANG == 0.7      # SoniTranslate
    assert thoi_gian.TRAN_TANG_TOC == 1.15              # Subdub
    assert thoi_gian.TRAN_CHONG_LAN_MS == 200           # SoniTranslate


def test_LECH_CO_Y_5_tran_troi_la_CUA_TA():
    """⭐ Khong du an tham chieu nao co tran nay.

    Subdub tich luy no khong gioi han. Tren mot video noi don, no tang don dieu
    toi khi tieng roi hinh ca chuc giay. Ta can tran vi D-ASV-03 sao chep luong
    hinh — tong thoi luong la mot con so co dinh, khong gian ra duoc.
    """
    assert thoi_gian.TRAN_TROI_SO_DOAN == 3


def test_bang_parity_nay_KHONG_RONG():
    """Chot chinh bang parity: mot bang chi con muc `assert True` van xanh."""
    import pathlib

    ma = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert ma.count("def test_") >= 12
    assert ma.count("LECH_CO_Y") >= 6, "so cho lech co y da giam — da go mat?"
