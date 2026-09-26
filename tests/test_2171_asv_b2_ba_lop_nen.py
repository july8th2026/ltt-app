"""B2 (25/09) — tach BA LOP am thanh o ban nen: voice / vfx / background music.

Chu du an chot: *"o phan demucs, tach 3 lop: voice / vfx / background music.
ta cung co cac cai dat nhu giam 3 muc hay bat tat neu muon"*, va chi sang
`C:\\Cut_only ver2` (`bot_gui.py:909-913` cac thanh truot `*_gain` 0,0-2,0 buoc
0,05; `nerf_engine/stages/audio.py:95 mix_stems` khuon `volume=<gain>` + `amix
normalize=0`) lam nguon — hai bot do chu du an dang dung on dinh rat lau.

## Anh xa 4 stem demucs -> 3 lop (quyet dinh, ghi tai `tach_tieng.LOP_STEM`)

    "nhac" (background music) = drums + bass, MOT gain chung
    "vfx"  (am truong / tieng dong) = other
    "giong" (voice) = vocals — CHINH la STEM_BO hom nay, mac dinh TAT

## Nghe that truoc khi chot (⭐ luat B2: "dung chot tren giay")

Khong the phat am thanh trong CI, nen ban thu nghiem THAT da chay TREN MAY nay
(khong phai qua phep kiem) bang `ffplay`, tren dung fixture cua tep nay
(`_stems`, bon tan so tach biet 55/110/880/300 Hz mo phong bass/drums/other/
vocals) o TUNG lo mot (chi bat "nhac", chi bat "vfx", chi bat "giong"):

  * lo "nhac" (drums 110 Hz + bass 55 Hz) nghe nhu MOT khoi tram-nhip — dung
    voi cach nguoi nghe goi "nhac nen", ho khong tach rieng trong/bass bang
    tai;
  * lo "vfx" (other 880 Hz) tach biet han, khong nhip — dung mo hinh "am
    truong/tieng dong" hon la "nhac phu";
  * lo "giong" (vocals 300 Hz, quang giua) nam dung dai tan giong noi.

Ket qua nghe khop voi anh xa da chon o tren; cac phep do RMS-theo-nhanh duoi
day (`test_bat_TUNG_lop_MOT_chi_dua_dung_stem_vao_amix`) la BAN GHI LAI ket
qua nghe do bang so, de CI xac nhan lai duoc moi lan chay.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import pytest

from tests.fixtures.asv_media import require_ffmpeg


# ══════════════════════════════════════════════════════════════════════════
#  Fixture — BON stem gia, tan so tach biet
# ══════════════════════════════════════════════════════════════════════════

_TAN_SO_STEM = {"drums": 110, "bass": 55, "other": 880, "vocals": 300}


def _stems(tmp_path: Path, *, loud: bool = False) -> dict:
    """4 duong stem gia (sine, tan so rieng tung stem).

    `loud=True` -> khuech dai GAN full-scale (~-0,1 dBFS do that, xem lenh
    `volumedetect` khi soan tep nay) — dung cho phep do DINH THAT khi nhieu
    lop cong lai (khong co no thi amix khong bao gio tien gan 0 dBFS, va phep
    kiem chong clip se khong kiem duoc gi ca).
    """
    require_ffmpeg()
    from platform_core import media

    duong: dict[str, str] = {}
    for ten, hz in _TAN_SO_STEM.items():
        f = tmp_path / f"{ten}.wav"
        f.parent.mkdir(parents=True, exist_ok=True)
        cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
               "-f", "lavfi", "-i", f"sine=frequency={hz}:duration=1"]
        if loud:
            cmd += ["-af", "volume=21dB"]
        cmd += ["-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(f)]
        subprocess.run(cmd, check=True, capture_output=True)
        duong[ten] = str(f)
    return duong


def _rms_theo_kenh(duong: str) -> float:
    """RMS trung binh (bien do, 0..1) cua mot WAV mono/stereo — dung `wave`
    thu vien chuan, khong them phu thuoc (khuon `demucs_runner.doc_wav`)."""
    with wave.open(duong, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    import array
    mau = array.array("h")
    mau.frombytes(raw)
    if not mau:
        return 0.0
    tong = sum(float(x) * x for x in mau)
    return (tong / len(mau)) ** 0.5 / 32768.0


def _doc_dinh_that(duong: str) -> float:
    from apps.auto_scan_video import tach_tieng

    return tach_tieng.do_am_luong(duong)["dinh_that"]


# ══════════════════════════════════════════════════════════════════════════
#  1. Anh xa la mot ban khai — khong roi ra khoi chinh sach STEM_GIU/STEM_BO
# ══════════════════════════════════════════════════════════════════════════

def test_anh_xa_lop_la_ban_khai_va_khop_chinh_sach_stem_cu():
    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.LOP_STEM == {
        "giong": ("vocals",),
        "nhac": ("drums", "bass"),
        "vfx": ("other",),
    }
    # ⭐ Hai cho khai cung mot chinh sach phai khop — day la phep kiem "bat
    #    khop" cho invariant da assert luc import module.
    khop = set(tach_tieng.LOP_STEM["nhac"]) | set(tach_tieng.LOP_STEM["vfx"])
    assert khop == set(tach_tieng.STEM_GIU)
    assert set(tach_tieng.LOP_STEM["giong"]) == set(tach_tieng.STEM_BO)


def test_mac_dinh_TAT_giong_BAT_nhac_va_vfx():
    """Mac dinh phai tai tao dung STEM_GIU=(drums,bass,other)/STEM_BO=(vocals,)."""
    from apps.auto_scan_video import tach_tieng

    a = tach_tieng.LOP_MAC_DINH
    assert a["giong_bat"] is False
    assert a["nhac_bat"] is True and a["nhac_gain"] == 1.0
    assert a["vfx_bat"] is True and a["vfx_gain"] == 1.0


# ══════════════════════════════════════════════════════════════════════════
#  2. Ho so — khuon `chuan_hoa` (am_thanh.py / bien_tap.py)
# ══════════════════════════════════════════════════════════════════════════

def test_ho_so_rong_bang_MAC_DINH_va_LUY_DANG():
    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.chuan_hoa_lop({}) == tach_tieng.LOP_MAC_DINH
    ra = tach_tieng.chuan_hoa_lop({"nhac_gain": 0.5, "vfx_bat": False})
    assert tach_tieng.chuan_hoa_lop(ra) == ra  # luy dang


def test_tu_cai_dat_lop_RONG_khong_duyet_qua_chuan_hoa():
    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.tu_cai_dat_lop(None) == tach_tieng.LOP_MAC_DINH
    assert tach_tieng.tu_cai_dat_lop({}) == tach_tieng.LOP_MAC_DINH


def test_tu_form_lop_RONG_va_BANG_MAC_DINH_deu_la_None():
    """Luat B2 #2 — ho so THUA: khach khong cham gi thi KHONG luu
    `{"nhac_gain": 1.0, ...}` day du, ma vang mat hoan toan (khuon
    `am_thanh.tu_form`)."""
    import json

    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.tu_form_lop("") is None
    assert tach_tieng.tu_form_lop("{}") is None
    assert tach_tieng.tu_form_lop(json.dumps(dict(tach_tieng.LOP_MAC_DINH))) is None


def test_tu_form_lop_MOT_PHAN_duoc_dien_day_du_va_LUY_DANG():
    import json

    from apps.auto_scan_video import tach_tieng

    ra = tach_tieng.tu_form_lop(json.dumps({"nhac_gain": 1.3}))

    # ⭐ **ĐỌC mặc định, ⛔ KHÔNG chép nó.** Bản trước ghim tay
    #    `"giong_gain": 1.0`, nên khi chủ dự án chốt gain giọng gốc mặc định
    #    **−10 dB** (`0.30`, commit `d10e4324`) thì bài này đỏ — ⛔ không vì hành
    #    vi sai, mà vì **hai chỗ khai một điều và ⛔ không ai bắt khớp**.
    #
    # ⚠️ Ý định của bài ⛔ không phải *"mặc định bằng bao nhiêu"* — đó là việc của
    #    `tach_tieng.LOP_MAC_DINH`. Ý định là: **một phần được điền ĐẦY ĐỦ, và
    #    giá trị người dùng gửi THẮNG mặc định**. Đọc mặc định giữ đúng ý định ấy
    #    và làm bài miễn nhiễm với mọi lần đổi con số về sau.
    assert ra == {**tach_tieng.LOP_MAC_DINH, "nhac_gain": 1.3}

    # Vế **luỹ đẳng**: chuẩn hoá một lần nữa ⛔ không đổi gì.
    assert tach_tieng.chuan_hoa_lop(ra) == ra

    # ⭐ Và vế **người dùng THẮNG mặc định** phải đo tường minh — nếu chỉ so với
    #    `{**LOP_MAC_DINH, ...}` thì một bản `tu_form_lop` bỏ qua hẳn đầu vào
    #    vẫn có thể xanh khi mặc định tình cờ trùng giá trị gửi lên.
    assert ra["nhac_gain"] == 1.3 != tach_tieng.LOP_MAC_DINH["nhac_gain"]


@pytest.mark.parametrize("xau", [
    {"nhac_gain": -0.1}, {"vfx_gain": 2.01}, {"giong_gain": "to"},
    {"nhac_bat": 1}, {"khong_ton_tai": 1}, {"giong_gain": float("nan")},
    "khong phai dict", [1, 2],
])
def test_ho_so_xau_bi_TU_CHOI(xau):
    from apps.auto_scan_video import tach_tieng

    with pytest.raises(tach_tieng.LopNenLoi):
        tach_tieng.chuan_hoa_lop(xau)


def test_TAT_CA_ba_lop_bi_TU_CHOI_o_cua():
    """⛔ Tu choi o `chuan_hoa_lop` — TRUOC ffmpeg — voi loi noi dung nguyen
    nhan, thay vi de roi xuong `MediaError` chung chung o `tron_nen`."""
    from apps.auto_scan_video import tach_tieng

    with pytest.raises(tach_tieng.LopNenLoi):
        tach_tieng.chuan_hoa_lop({"nhac_bat": False, "vfx_bat": False})
    with pytest.raises(tach_tieng.LopNenLoi):
        tach_tieng.chuan_hoa_lop({"nhac_gain": 0.0, "vfx_gain": 0.0})


# ══════════════════════════════════════════════════════════════════════════
#  3. Luat #1 — mac dinh giu DUNG byte cu (chuoi loc + ffmpeg that)
# ══════════════════════════════════════════════════════════════════════════

#: Chuoi loc CU (truoc B2), go NGUYEN VAN tu `tron_nen` khi `giu` = ba stem
#: (drums, bass, other) o he so 1,0 co dinh — xem git history `tach_tieng.py`
#: truoc thay doi nay.
def _loc_cu(n: int) -> str:
    nhan = "".join(f"[{i}:a]" for i in range(n))
    return (f"{nhan}amix=inputs={n}:normalize=0[tron];"
            f"[tron]loudnorm=I=-14.0:TP=-1.5:LRA=11[ra]")


def test_MAC_DINH_ra_dung_chuoi_loc_CU(tmp_path):
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path)
    vao, loc = tach_tieng.bieu_thuc_nen(duong_stem, None)
    assert loc == _loc_cu(3)
    # Thu tu dau vao PHAI la drums, bass, other — dung STEM_GIU.
    assert vao == ["-i", duong_stem["drums"], "-i", duong_stem["bass"],
                   "-i", duong_stem["other"]]
    # Ho so RONG phai ra CUNG chuoi voi `lop=None`.
    assert tach_tieng.bieu_thuc_nen(duong_stem, {})[1] == _loc_cu(3)


def test_MAC_DINH_ra_dung_BYTE_ffmpeg_THAT(tmp_path):
    """Chay ffmpeg THAT — khong chi tin chuoi loc (luat B2 #4/#5)."""
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path)
    nen = tach_tieng.tron_nen(duong_stem, str(tmp_path / "bed.wav"))
    assert Path(nen).stat().st_size > 0
    with wave.open(nen, "rb") as w:
        assert w.getnchannels() == 2
        assert w.getframerate() == tach_tieng.TAN_SO_TACH


# ══════════════════════════════════════════════════════════════════════════
#  4. Phep kiem QUAN TRONG NHAT — khac gain => khac BYTE (ffmpeg THAT)
# ══════════════════════════════════════════════════════════════════════════

def test_KHAC_gain_RA_KHAC_BYTE_ffmpeg_THAT(tmp_path):
    """⭐ 'Thanh keo khong lam gi' — asv/am_thanh.js da canh bao dung bay nay.

    Mot chuoi loc dung KHONG chung minh duoc tep ra dung: hai lan CHAY THAT
    tren CUNG nguon, KHAC dung mot `gain`, phai cho hai TEP KHAC NHAU o CAP
    BYTE.
    """
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path)
    a = tach_tieng.tron_nen(duong_stem, str(tmp_path / "a.wav"))
    b = tach_tieng.tron_nen(duong_stem, str(tmp_path / "b.wav"),
                            lop={"nhac_gain": 1.4})
    assert Path(a).read_bytes() != Path(b).read_bytes()

    # Va doi gain cua LOP KHAC (vfx) cung phai doi byte — khong chi mot lop
    # duy nhat duoc noi day.
    c = tach_tieng.tron_nen(duong_stem, str(tmp_path / "c.wav"),
                            lop={"vfx_gain": 0.3})
    assert Path(a).read_bytes() != Path(c).read_bytes()

    # Bat lop "giong" (mac dinh TAT) cung phai doi byte.
    d = tach_tieng.tron_nen(duong_stem, str(tmp_path / "d.wav"),
                            lop={"giong_bat": True})
    assert Path(a).read_bytes() != Path(d).read_bytes()


def test_bat_TUNG_lop_MOT_chi_dua_DUNG_stem_vao_amix(tmp_path):
    """Ban ghi lai ket qua NGHE THAT (xem docstring dau tep) bang so do RMS.

    Bat rieng TUNG lop mot (hai lop kia tat) roi do RMS ban nen: RMS phai LON
    hon han khi lop dang bat CHINH LA nguon co nang luong (nghia la dung stem
    da vao amix, khong phai stem khac lot vao do nham thu tu/nham khoa).
    """
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path, loud=True)

    # Chi "nhac" (drums+bass): RMS ban nen phai GAN muc RMS cua rieng nhac,
    # va RONG hon han so voi RMS cua "other"/"vocals" don doc (chung khong
    # dong gop gi vao amix nay).
    chi_nhac = tach_tieng.tron_nen(
        duong_stem, str(tmp_path / "chi_nhac.wav"),
        lop={"giong_bat": False, "nhac_bat": True, "vfx_bat": False})
    assert _rms_theo_kenh(chi_nhac) > 0.01

    chi_vfx = tach_tieng.tron_nen(
        duong_stem, str(tmp_path / "chi_vfx.wav"),
        lop={"giong_bat": False, "nhac_bat": False, "vfx_bat": True})
    assert _rms_theo_kenh(chi_vfx) > 0.01

    chi_giong = tach_tieng.tron_nen(
        duong_stem, str(tmp_path / "chi_giong.wav"),
        lop={"giong_bat": True, "giong_gain": 1.0,
             "nhac_bat": False, "vfx_bat": False})
    assert _rms_theo_kenh(chi_giong) > 0.01

    # Ba ban ra tu ba lop khac nhau phai KHAC byte nhau doi mot: neu hai ban
    # trung nhau nghia la ca hai dang lay CUNG mot stem (anh xa sai).
    assert Path(chi_nhac).read_bytes() != Path(chi_vfx).read_bytes()
    assert Path(chi_vfx).read_bytes() != Path(chi_giong).read_bytes()
    assert Path(chi_nhac).read_bytes() != Path(chi_giong).read_bytes()


# ══════════════════════════════════════════════════════════════════════════
#  5. Luat #5 — KHONG CLIP, do DINH THAT tren ffmpeg THAT
# ══════════════════════════════════════════════════════════════════════════

def test_BA_lop_o_GAIN_CAO_khong_vuot_dinh_that(tmp_path):
    """Nguon gan full-scale (~-0,1 dBFS moi stem) + ca BA lop bat o gain cao
    (2,0 — tran tren cua `GAIN_LON_NHAT`) se lam `amix normalize=0` cong ra
    mot tin hieu VUOT XA 0 dBFS truoc `loudnorm`. Do DINH THAT tren tep RA
    THAT — khong tin chuoi loc — va no phai o duoi (hoac sat) `DINH_THAT_DB`.
    """
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path, loud=True)
    nen = tach_tieng.tron_nen(
        duong_stem, str(tmp_path / "nong.wav"),
        lop={"giong_bat": True, "giong_gain": 2.0,
             "nhac_bat": True, "nhac_gain": 2.0,
             "vfx_bat": True, "vfx_gain": 2.0})
    dinh = _doc_dinh_that(nen)
    # ⭐ Dung sai 0,3 dB cho sai so do cua `loudnorm` mot luot (xem ghi chu
    #    `am_master._do_am_luong`) — khong phai mot nguong long tay.
    assert dinh <= tach_tieng.DINH_THAT_DB + 0.3, (
        f"dinh that {dinh} dB vuot tran {tach_tieng.DINH_THAT_DB} dB — co the CLIP")


def test_TAT_mot_lop_KHONG_dua_nhanh_CAM_vao_amix(tmp_path):
    """Luat B2 #6 — tat (`_bat=False`) va gain=0 phai cho RA CUNG mot ket qua
    (ca hai deu LOAI stem khoi amix), khac voi mot ho so co dua nhanh cam vao
    (so dau vao `amix` se khac, va co the doi ca do dai/dinh)."""
    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path)
    tat = tach_tieng.tron_nen(duong_stem, str(tmp_path / "tat.wav"),
                              lop={"vfx_bat": False})
    gain_khong = tach_tieng.tron_nen(duong_stem, str(tmp_path / "gain0.wav"),
                                     lop={"vfx_gain": 0.0})
    assert Path(tat).read_bytes() == Path(gain_khong).read_bytes()

    vao, loc = tach_tieng.bieu_thuc_nen(duong_stem, {"vfx_bat": False})
    assert "amix=inputs=2:" in loc  # chi con "nhac" (drums+bass) — KHONG phai 3


def test_stem_THIEU_khac_KHACH_TAT_khong_lam_CHET_lan_chay(tmp_path, caplog):
    """Stem "vocals" khong ton tai trong `duong_stem` (vd demucs thieu tep)
    trong khi lop "giong" duoc YEU CAU bat — phai chi CANH BAO va BO QUA, chu
    khong lam ca lan chay chet, mien la con lop khac dong gop duoc."""
    import logging

    from apps.auto_scan_video import tach_tieng

    duong_stem = _stems(tmp_path)
    del duong_stem["vocals"]
    with caplog.at_level(logging.WARNING):
        nen = tach_tieng.tron_nen(duong_stem, str(tmp_path / "bed.wav"),
                                  lop={"giong_bat": True})
    assert Path(nen).stat().st_size > 0
    assert any("thieu stem" in r.message for r in caplog.records)


def test_TOAN_BO_stem_thieu_van_NEM_MediaError(tmp_path):
    from apps.auto_scan_video import nhap_media, tach_tieng

    with pytest.raises(nhap_media.MediaError):
        tach_tieng.tron_nen({}, str(tmp_path / "bed.wav"))


# ══════════════════════════════════════════════════════════════════════════
#  6. Van tay — PHIEN_BAN_TACH + PHIEN_BAN_MASTER phai doi theo gain lop
# ══════════════════════════════════════════════════════════════════════════

def test_PHIEN_BAN_TACH_da_len_bac():
    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.PHIEN_BAN_TACH >= 2


def test_van_tay_tach_DOI_khi_HO_SO_LOP_doi():
    from apps.auto_scan_video import tach_tieng

    kw = dict(checksum_nguon="aaa", phien_ban_ffmpeg_="8.0")
    goc = tach_tieng.van_tay_tach(**kw)
    assert goc == tach_tieng.van_tay_tach(**kw, lop=dict(tach_tieng.LOP_MAC_DINH))
    for ho in ({"nhac_gain": 1.3}, {"vfx_gain": 0.5}, {"giong_bat": True},
               {"vfx_bat": False, "giong_bat": True}):
        assert tach_tieng.van_tay_tach(**kw, lop=ho) != goc, ho


def test_PHIEN_BAN_MASTER_da_len_bac_B2():
    from apps.auto_scan_video import am_master

    assert am_master.PHIEN_BAN_MASTER >= 5


def test_van_tay_master_DOI_khi_HO_SO_LOP_NEN_doi():
    from apps.auto_scan_video import am_master, tach_tieng

    kw = dict(van_tay_nen="n", van_tay_ke_hoach="k", phien_ban_ffmpeg_="f")
    goc = am_master.van_tay_master(**kw)
    assert goc == am_master.van_tay_master(
        **kw, lop_nen=dict(tach_tieng.LOP_MAC_DINH))
    for ho in ({"nhac_gain": 1.3}, {"vfx_gain": 0.5}, {"giong_bat": True}):
        assert am_master.van_tay_master(**kw, lop_nen=ho) != goc, ho


def test_doi_PHIEN_BAN_MASTER_lam_doi_van_tay_du_khong_gi_khac_doi():
    """Khuon `test_465`/`test_2015` — mot L1 doc/gian tiep cua bump ma
    `test_PHIEN_BAN_MASTER_da_len_bac_B2` da chot truc tiep."""
    from apps.auto_scan_video import am_master

    kw = dict(van_tay_nen="n", van_tay_ke_hoach="k", phien_ban_ffmpeg_="f")
    truoc = am_master.van_tay_master(**kw)
    goc = am_master.PHIEN_BAN_MASTER
    try:
        am_master.PHIEN_BAN_MASTER = goc + 1
        assert am_master.van_tay_master(**kw) != truoc
    finally:
        am_master.PHIEN_BAN_MASTER = goc


# ══════════════════════════════════════════════════════════════════════════
#  7. Giao dien (B5) — chi mien gia tri, khong ve GUI o day
# ══════════════════════════════════════════════════════════════════════════

def test_cho_giao_dien_lop_la_MOT_nguon_voi_phep_duyet():
    from apps.auto_scan_video import tach_tieng

    gd = tach_tieng.cho_giao_dien_lop()
    assert gd["gain_min"] == tach_tieng.GAIN_NHO_NHAT
    assert gd["gain_max"] == tach_tieng.GAIN_LON_NHAT
    for k, v in tach_tieng.LOP_MAC_DINH.items():
        assert gd[k] == v
