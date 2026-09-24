"""R-01 §4 — phep DO F0 tren giong goc: mat `gioi` cua `AUTO_MATCH`.

Ba mat cua catalog, va chi mot trong ba **do duoc**:

    gioi        do tren stem `vocals` (tep nay)
    vung        giong vung mien tieng Viet — mot phim tieng Trung khong noi gi
    phong_cach  nhan mo ta giong, khong phai nut van (`giong_mau`)

⇒ Nen `gioi` di duong DO, hai mat kia di duong HOI. Tep nay do duong do.

⛔ Khong nap demucs that o day: bai nay do `cao_do` tren WAV tong hop, va do
   duong di cua con so tu tien trinh con len `outputs` cua giai doan bang mot
   ban thay the. Mot phep kiem nap model that giua luot gate la thu
   `tests/rao_chan_nang.py` sinh ra de chan.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from apps.auto_scan_video import cao_do


def _wav(dest: Path, f0: float, *, giay: float = 2.5, tan_so: int = 44100,
         kenh: int = 2, im_lang_cuoi: float = 1.0) -> Path:
    """Mot nguyen am tong hop: co ban + hai hoa am, roi im lang.

    ⭐ Co hoa am chu khong phai sin thuan: mot sin thuan la tin hieu de nhat cho
       moi bo do cao do, va do de tren mot tin hieu de thi khong noi gi ve tieng
       noi. Doan im lang o cuoi de bai kiem cua NANG LUONG co viec that.
    """
    n = int(tan_so * giay)
    mau = []
    for i in range(n):
        t = i / tan_so
        v = sum(math.sin(2 * math.pi * f0 * k * t) / k for k in (1, 2, 3)) * 0.25
        mau.append(max(-1.0, min(1.0, v)))
    mau += [0.0] * int(tan_so * im_lang_cuoi)
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(kenh); w.setsampwidth(2); w.setframerate(tan_so)
        w.writeframes(b"".join(
            struct.pack("<" + "h" * kenh, *([int(v * 32767)] * kenh))
            for v in mau))
    return dest


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Phep do
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("f0", [105.0, 140.0, 200.0, 240.0])
def test_do_dung_F0_trong_khoang_tieng_noi(tmp_path, f0):
    do = cao_do.f0_trung_vi(_wav(tmp_path / "v.wav", f0))
    assert do == pytest.approx(f0, rel=0.03), f"do {do} cho nguon {f0}"


def test_gop_kenh_truoc_khi_do(tmp_path):
    """Stem cua demucs la stereo. Mot ban do tung kenh roi gop hai day so lai
    la lam hai lan cong viec cho cung mot cau tra loi."""
    a = cao_do.f0_trung_vi(_wav(tmp_path / "1.wav", 120.0, kenh=1))
    b = cao_do.f0_trung_vi(_wav(tmp_path / "2.wav", 120.0, kenh=2))
    assert a == pytest.approx(b, rel=0.02)


def test_im_lang_tra_ve_KHONG_DO_DUOC_chu_khong_phai_mot_con_so(tmp_path):
    """🔴 `detect_pitch_frequency` tra ve MOT con so cho MOI khung, ke ca khung
    im lang — va con so do la rac. Khong co cua nang luong thi trung vi do
    chinh rac, tuc mot lan chay se chon giong theo tieng on."""
    im = tmp_path / "im.wav"
    with wave.open(str(im), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(b"\x00" * 44100 * 4)
    assert cao_do.f0_trung_vi(im) == 0.0


def test_tep_khong_co_hoac_hong_KHONG_lam_hong_audio_prepare(tmp_path):
    """⚠️ Fail-soft co chu dinh: `audio_prepare` la giai doan dat nhat cua chuoi
    (72 giay demucs o luot that). Mot phep do khong chay duoc — thieu
    `torchaudio`, tep hong — khong duoc phep giet no."""
    assert cao_do.f0_trung_vi(tmp_path / "khong-co.wav") == 0.0
    hong = tmp_path / "hong.wav"
    hong.write_bytes(b"khong phai WAV")
    assert cao_do.f0_trung_vi(hong) == 0.0


def test_am_cao_hon_tieng_noi_nguoi_khong_ra_mot_con_so(tmp_path):
    """Tran tren la 400 Hz: mot am cao hon the khong phai giong nguoi lon."""
    assert cao_do.f0_trung_vi(_wav(tmp_path / "rat-cao.wav", 500.0)) == 0.0


def test_LOI_QUANG_TAM_duoc_khai_that_chu_khong_giau(tmp_path):
    """🔴 **Bai nay chot mot GIOI HAN, khong chot mot tinh nang.**

    Bo do la mot ho tu tuong quan; tren mot am KHONG PHAI TIENG NOI no co the
    bat vao mot chu ky boi. Do 23/09: mot sin 440 Hz + hoa am ra ~219 Hz, tuc
    roi thang vao khoang "nu". Viet no ra o day de khong ai doc `cao_do` roi
    tuong no la mot bo phan loai gioi tinh dung tren am thanh bat ky.

    ⭐ Cai chan no trong duong that la **dau vao**, khong phai phep do: thu di
       vao la stem `vocals` cua demucs, nen mot video khong co giong nguoi cho
       ra mot stem gan nhu im lang va cua nang luong tra `0.0`
       (`test_im_lang_tra_ve_KHONG_DO_DUOC...`).
    """
    do = cao_do.f0_trung_vi(_wav(tmp_path / "cao.wav", 440.0))
    assert do == pytest.approx(440.0 / 2, rel=0.05), (
        f"loi quang tam da doi hanh vi ({do} Hz) — doc lai ghi chu gioi han "
        "o `cao_do.py` truoc khi sua bai nay")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Nguong va VUNG XAM
# ══════════════════════════════════════════════════════════════════════════════

def test_vung_xam_KHONG_phan_dinh():
    """🔴 Khoang nam (~85–180 Hz) va nu (~165–255 Hz) **chong nhau**. Mot nguong
    don o giua se khai gioi sai cho dung nhung giong kho nhat, va hau qua la
    mot lan chay doc bang giong nguoc gioi ma khong ai bam nut nao.

    ⛔ `""` o day nghia la *khong rang buoc mat nay* — `rang_giong` doc dung the
       — chu khong phai "nam".
    """
    for hz in (cao_do.NGUONG_GIOI_HZ - cao_do.BIEN_XAM_HZ + 1,
               cao_do.NGUONG_GIOI_HZ,
               cao_do.NGUONG_GIOI_HZ + cao_do.BIEN_XAM_HZ - 1):
        assert cao_do.gioi_tu_f0(hz) == "", f"{hz} Hz bi phan dinh"


def test_ngoai_khoang_tieng_noi_nguoi_lon_thi_khong_khai():
    assert cao_do.gioi_tu_f0(cao_do.F0_THAP_HZ - 1) == ""
    assert cao_do.gioi_tu_f0(cao_do.F0_CAO_HZ + 1) == ""
    assert cao_do.gioi_tu_f0("khong phai so") == ""


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Duong di cua con so: tien trinh con -> `outputs` cua `audio_prepare`
# ══════════════════════════════════════════════════════════════════════════════

def test_runner_do_stem_vocals_chu_khong_phai_ban_NEN(tmp_path, monkeypatch):
    """⛔ `bed.wav` la nhac nen DA BO giong — do F0 tren no la do tieng dan.

    Va phep do phai nam o tien trinh con: `giai_doan_am_thanh` XOA `vocals`
    ngay khi tien trinh con ket thuc (no la giong goc cua khach), nen sau do
    khong con gi de do.
    """
    from apps.auto_scan_video import demucs_runner

    _wav(tmp_path / "vocals.wav", 115.0)
    _wav(tmp_path / "other.wav", 330.0)
    kq = {"duong": {"vocals": str(tmp_path / "vocals.wav"),
                    "other": str(tmp_path / "other.wav")}}
    f0, ly_do = demucs_runner._f0_cua_giong(kq)
    assert f0 == pytest.approx(115.0, rel=0.03)
    assert ly_do == "", ly_do


def test_runner_khong_co_stem_vocals_thi_KHONG_do():
    """⭐ `0.0` di kem LY DO: mot bao cao khong phan biet duoc "khong co giong"
    voi "khong do duoc" thi khong tra loi duoc cau nao ca."""
    from apps.auto_scan_video import demucs_runner

    for kq in ({"duong": {}}, {}):
        f0, ly_do = demucs_runner._f0_cua_giong(kq)
        assert f0 == 0.0
        assert "vocals" in ly_do, ly_do


def test_con_so_di_len_TOM_TAT_cua_giai_doan(monkeypatch, tmp_path):
    """Con so phai toi duoc `ho_so_noi_dung.f0_tu_giai_doan`, khong dung lai o
    stdout cua tien trinh con."""
    from apps.auto_scan_video import ho_so_noi_dung

    class _GD:
        outputs = {"f0_trung_vi": 118.5}

    class _Run:
        id = "r1"

    monkeypatch.setattr("apps.auto_scan_video.features.giai_doan_theo_ten",
                        lambda db, rid, ten: _GD())
    assert ho_so_noi_dung.f0_tu_giai_doan(None, _Run()) == 118.5


def test_giai_doan_khong_co_con_so_thi_ve_KHONG_do_duoc(monkeypatch):
    """Ban demucs gia lap cua bo test khong tra `f0_trung_vi`, va mot lan chay
    cu (truoc 23/09) cung khong co. Ca hai phai ra `0.0`, khong phai `None`."""
    from apps.auto_scan_video import ho_so_noi_dung

    class _Run:
        id = "r1"

    monkeypatch.setattr("apps.auto_scan_video.features.giai_doan_theo_ten",
                        lambda db, rid, ten: None)
    assert ho_so_noi_dung.f0_tu_giai_doan(None, _Run()) == 0.0
