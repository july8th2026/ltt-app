"""V3 (`asv-nhac`, 25/09) — nhac nen KHACH TU TAI LEN: tai len + am luong + lap.

Xem `docs/superpowers/plans/2026-09-25-asv-full-tu-viral.md` hang `V3` (muc 3,
3.2) va hang `V3` cua bang nghiem thu (muc 5). Loi giai tham khao:
`D:/Viral/resources/app-src/xu_ly_video.py:51,1091-1093,1170-1212`.

⛔ **Mot tien de trong brief KHONG khop kien truc cua ta — ghi ro thay vi lang
   le bo qua.** Viral co mot tham so `goc_vol` (am luong tieng GOC giu lai o
   muc thap khi de len giong dub) va coi `goc_vol<=0.001` la "video cam". San
   pham nay KHONG overlay tieng goc — no THAY THE hoan toan bang giong dub
   (`nen` = ban demucs da bo `vocals`, `cac_lo` = giong dub tu `am_master`), nen
   KHONG co truong `goc_vol` nao trong `am_thanh` de kiem "≤0,001". Ca "video
   cam" duoi day duoc dien lai bang `nen`/`cac_lo` THAT SU im lang — phep kiem
   gan nhat voi tinh huong Viral mo ta ma kien truc nay co the co.

## Vi sao mot phep chuan hoa khong chung minh duoc tep ra dung (luat #4/#1)

Moi phep kiem tren TEP RA THAT deu chay `am_master.tron_cuoi` bang ffmpeg
THAT — khuon `test_2171`/`test_479`: mot chuoi loc dung khong chung minh duoc
gi, chi mot lan chay that tren mot nguon xac dinh moi tra loi duoc.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.fixtures.asv_media import require_ffmpeg

TONG = 6.0


# ══════════════════════════════════════════════════════════════════════════
#  Fixture — WAV tong hop, xac dinh (khuon test_2171._stems / test_479._ff)
# ══════════════════════════════════════════════════════════════════════════

def _ffmpeg_wav(t: Path, ten: str, *, lavfi: str, af: str | None = None) -> str:
    require_ffmpeg()
    from platform_core import media

    f = str(t / f"{ten}.wav")
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", lavfi]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", f]
    subprocess.run(cmd, check=True, capture_output=True)
    return f


def _im_lang(t: Path, ten: str, dur: float) -> str:
    return _ffmpeg_wav(t, ten, lavfi=f"anullsrc=r=44100:cl=stereo:d={dur}")


def _tieng(t: Path, ten: str, *, hz: float, dur: float, loud: bool = False) -> str:
    # `loud=True` -> gan full-scale, khuon test_2171 (`_stems(loud=True)`):
    # can no de phep kiem KHONG CLIP co gi de kiem.
    return _ffmpeg_wav(t, ten, lavfi=f"sine=frequency={hz}:duration={dur}",
                       af=("volume=21dB" if loud else None))


def _dinh_that(duong: str) -> float:
    from apps.auto_scan_video import tach_tieng
    return tach_tieng.do_am_luong(duong)["dinh_that"]


@pytest.fixture(scope="module")
def nen_lo(tmp_path_factory):
    """`nen` + MOT lo tieng dub — nguyen lieu 'binh thuong'."""
    from apps.auto_scan_video import am_master

    t = tmp_path_factory.mktemp("v3nl")
    nen = _tieng(t, "nen", hz=150, dur=TONG)
    doan = _tieng(t, "d0", hz=1000, dur=1.5)
    lo = am_master.tron_lo([doan], [2000], [1.0], str(t / "lo.wav"), tong_giay=TONG)
    return t, nen, lo


@pytest.fixture(scope="module")
def nen_lo_im_lang(tmp_path_factory):
    """`nen` + lo HOAN TOAN im lang — dien lai ca "video cam" (xem canh bao
    tien de dau tep: kien truc nay khong co truong `goc_vol` de mo phong y het
    Viral, day la phep tuong duong GAN NHAT ma no co)."""
    from apps.auto_scan_video import am_master

    t = tmp_path_factory.mktemp("v3im")
    nen = _im_lang(t, "nen", TONG)
    doan = _im_lang(t, "d0", 1.5)
    lo = am_master.tron_lo([doan], [2000], [1.0], str(t / "lo.wav"), tong_giay=TONG)
    return t, nen, lo


#: ⚠️ **Khoa kho GIA phai chua mot chu KHONG-hex (25/09/2026).**
#:
#:    Ban dau hai khoa nay la `"a"*32` va `"b"*32` — va `tools/scan_source_secrets.py`
#:    bao chung la bi mat, vi luat `bare_32_char_hex` la `[0-9a-f]{32}` tron va `a`/`b`
#:    DEU la chu so hex. Gate do o buoc quet bi mat.
#:
#: ⛔ Dung "lam cho im" bang cach mien tru tep nay khoi may quet: mot ngoai le se song
#:    mai va che mot bi mat THAT sau nay. Thay vao do dat ten khoa co chu `z` (khong
#:    phai hex) va TU NOI RA no la khoa gia — nguoi sau doc la hieu, va may quet khong
#:    con gi de nham.
def _ho_so(khoa="asv/oA/rA/timing_align/khoagia_nhac_nen_KHONG_bi_mat_z1.mp3",
           *, am_luong_nen=None, lap=None) -> dict:
    nhac_nen = {"khoa": khoa}
    if am_luong_nen is not None:
        nhac_nen["am_luong_nen"] = am_luong_nen
    if lap is not None:
        nhac_nen["lap"] = lap
    return {"nhac_nen": nhac_nen}


# ══════════════════════════════════════════════════════════════════════════
#  1. Ho so `am_thanh.nhac_nen` — duyet o cua (① ho so THUA)
# ══════════════════════════════════════════════════════════════════════════

def test_KHONG_tai_nhac_thi_ho_so_VANG_MAT():
    """Luat #1/#2 cua brief: khach khong tai nhac -> `nhac_nen` vang mat, KHONG
    phai `{"am_luong_nen": 0.25, ...}` day du."""
    from apps.auto_scan_video import am_thanh

    assert am_thanh.MAC_DINH["nhac_nen"] is None
    assert am_thanh.chuan_hoa({})["nhac_nen"] is None
    assert am_thanh.tu_cai_dat(None)["nhac_nen"] is None
    assert am_thanh.tu_form("") is None
    assert am_thanh.tu_form("{}") is None


def test_ho_so_CHI_co_nhac_nen_khac_MAC_DINH_nen_KHONG_gop_ve_None():
    import json

    from apps.auto_scan_video import am_thanh

    ra = am_thanh.tu_form(json.dumps(_ho_so()))
    assert ra is not None
    assert ra["nhac_nen"]["khoa"] == _ho_so()["nhac_nen"]["khoa"]
    assert ra["nhac_nen"]["am_luong_nen"] == am_thanh.NHAC_NEN_AM_LUONG_MAC_DINH
    assert ra["nhac_nen"]["lap"] is True


def test_ho_so_nhac_nen_hop_le_DIEN_DAY_DU_va_LUY_DANG():
    from apps.auto_scan_video import am_thanh

    ra = am_thanh.chuan_hoa_nhac_nen({"khoa": "asv/oA/rA/s/aaaa.mp3"})
    assert ra == {"khoa": "asv/oA/rA/s/aaaa.mp3",
                  "am_luong_nen": am_thanh.NHAC_NEN_AM_LUONG_MAC_DINH, "lap": True}
    assert am_thanh.chuan_hoa_nhac_nen(ra) == ra


@pytest.mark.parametrize("xau", [
    {"khoa": ""}, {"khoa": "../etc/passwd"}, {"khoa": "http://x/y.mp3"},
    {"khoa": "/etc/passwd"}, {"khoa": "a.mp3", "am_luong_nen": -0.1},
    {"khoa": "a.mp3", "am_luong_nen": 2.01}, {"khoa": "a.mp3", "am_luong_nen": "to"},
    {"khoa": "a.mp3", "am_luong_nen": True}, {"khoa": "a.mp3", "lap": 1},
    {"khoa": "a.mp3", "la": 1}, "khong phai dict", [1, 2],
])
def test_ho_so_nhac_nen_XAU_bi_TU_CHOI(xau):
    from apps.auto_scan_video import am_thanh

    with pytest.raises(am_thanh.AmThanhLoi):
        am_thanh.chuan_hoa_nhac_nen(xau)
    if isinstance(xau, dict):
        with pytest.raises(am_thanh.AmThanhLoi):
            am_thanh.chuan_hoa({"nhac_nen": xau})


def test_am_luong_nen_DUNG_LAI_mien_gain_cua_tach_tieng():
    from apps.auto_scan_video import am_thanh, tach_tieng

    assert am_thanh.NHAC_NEN_AM_LUONG_NHO_NHAT == tach_tieng.GAIN_NHO_NHAT
    assert am_thanh.NHAC_NEN_AM_LUONG_LON_NHAT == tach_tieng.GAIN_LON_NHAT


def test_cho_giao_dien_phoi_them_mien_nhac_nen():
    from apps.auto_scan_video import am_thanh

    gd = am_thanh.cho_giao_dien()
    assert gd["nhac_nen_am_luong_mac_dinh"] == am_thanh.NHAC_NEN_AM_LUONG_MAC_DINH
    assert gd["nhac_nen_am_luong_min"] == am_thanh.NHAC_NEN_AM_LUONG_NHO_NHAT
    assert gd["nhac_nen_am_luong_max"] == am_thanh.NHAC_NEN_AM_LUONG_LON_NHAT


# ══════════════════════════════════════════════════════════════════════════
#  2. `bieu_thuc_tron` — ho so va chi so PHAI khop nhau; mac dinh GIU DUNG chuoi
# ══════════════════════════════════════════════════════════════════════════

def test_bieu_thuc_tron_TU_CHOI_khi_ho_so_va_chi_so_LECH_NHAU():
    from apps.auto_scan_video import am_master

    with pytest.raises(am_master.MasterError):
        am_master.bieu_thuc_tron(2, tong_giay=TONG, nhac_nen_idx=2)
    with pytest.raises(am_master.MasterError):
        am_master.bieu_thuc_tron(2, am=_ho_so(), tong_giay=TONG)


def test_bieu_thuc_tron_MAC_DINH_khong_nhac_GIU_DUNG_chuoi_CU():
    """⛔ Khong regress byte cua ho so mac dinh (khong nhac nen) — chinh phep
    kiem `test_ho_so_MAC_DINH_ra_DUNG_chuoi_truoc_pha_23` cua `test_479` da
    xac nhan gian tiep; o day chot them dang KHONG co `nhac_nen_idx`."""
    from apps.auto_scan_video import am_master

    cu = am_master.bieu_thuc_tron(2, tong_giay=TONG)
    moi = am_master.bieu_thuc_tron(2, tong_giay=TONG, nhac_nen_idx=None)
    assert cu == moi
    assert "nhacnen" not in cu and "nenx" not in cu


def test_bieu_thuc_tron_CO_nhac_them_DUNG_cac_nhan_moi():
    from apps.auto_scan_video import am_master

    loc = am_master.bieu_thuc_tron(2, am=_ho_so(am_luong_nen=0.4), tong_giay=TONG,
                                   nhac_nen_idx=2)
    assert "[2:a]volume=0.4,apad," in loc
    assert "[nen][nhacnen]amix=inputs=2:normalize=0:dropout_transition=0[nenx];" in loc
    # Nhanh KHONG ducking phai tron tu `[nenx]`, khong phai `[nen]` truc tiep.
    assert "[nenx][t1]amix=inputs=2:normalize=0:dropout_transition=0[tron];" in loc


# ══════════════════════════════════════════════════════════════════════════
#  3. Van tay — ② PHIEN_BAN_MASTER da tang, ③ van tay doi theo khoa/am luong
# ══════════════════════════════════════════════════════════════════════════

def test_PHIEN_BAN_MASTER_da_len_bac_V3():
    from apps.auto_scan_video import am_master

    assert am_master.PHIEN_BAN_MASTER >= 6


def test_van_tay_master_DOI_khi_KHOA_hoac_AM_LUONG_NEN_doi():
    from apps.auto_scan_video import am_master

    kw = dict(van_tay_nen="n", van_tay_ke_hoach="k", phien_ban_ffmpeg_="f")
    goc = am_master.van_tay_master(**kw)
    voi_nhac = am_master.van_tay_master(**kw, am_thanh=_ho_so())
    assert voi_nhac != goc

    khac_khoa = am_master.van_tay_master(
        **kw, am_thanh=_ho_so("asv/oA/rA/s/khoagia_nhac_khac_KHONG_bi_mat_z2.mp3"))
    assert khac_khoa != voi_nhac

    khac_am_luong = am_master.van_tay_master(**kw, am_thanh=_ho_so(am_luong_nen=0.8))
    assert khac_am_luong != voi_nhac

    khac_lap = am_master.van_tay_master(**kw, am_thanh=_ho_so(lap=False))
    assert khac_lap != voi_nhac


# ══════════════════════════════════════════════════════════════════════════
#  4. Tep ra THAT (ffmpeg that) — luat #1 cua brief, KHONG tin chuoi loc
# ══════════════════════════════════════════════════════════════════════════

def test_KHAC_am_luong_nen_RA_KHAC_BYTE_ffmpeg_THAT(nen_lo, tmp_path_factory):
    """④ Phep kiem chong 'thanh keo khong lam gi' (`asv/am_thanh.js` da canh
    bao dung bay nay; `test_2171` da chot cung luat cho gain lop). Hai luot
    CHAY THAT tren CUNG nguon, KHAC dung `am_luong_nen`, phai ra hai tep KHAC
    NHAU o cap byte."""
    from apps.auto_scan_video import am_master

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3gain")
    nhac = _tieng(tn, "nhac", hz=440, dur=TONG)

    a = am_master.tron_cuoi(nen, [lo], str(tn / "a.wav"), tong_giay=TONG,
                            am=_ho_so(am_luong_nen=0.25), nhac_nen_duong=nhac)
    b = am_master.tron_cuoi(nen, [lo], str(tn / "b.wav"), tong_giay=TONG,
                            am=_ho_so(am_luong_nen=1.4), nhac_nen_duong=nhac)
    assert Path(a).read_bytes() != Path(b).read_bytes()

    # Va TAT nhac hoan toan (ho so vang mat) phai khac ca hai tep tren.
    c = am_master.tron_cuoi(nen, [lo], str(tn / "c.wav"), tong_giay=TONG, am=None)
    assert Path(c).read_bytes() != Path(a).read_bytes()
    assert Path(c).read_bytes() != Path(b).read_bytes()


def test_tron_cuoi_TU_CHOI_khi_duong_va_ho_so_LECH_NHAU(nen_lo, tmp_path_factory):
    from apps.auto_scan_video import am_master

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3lech")
    nhac = _tieng(tn, "nhac", hz=440, dur=TONG)
    with pytest.raises(am_master.MasterError):
        am_master.tron_cuoi(nen, [lo], str(tn / "x.wav"), tong_giay=TONG,
                            am=None, nhac_nen_duong=nhac)          # co duong, khong ho so
    with pytest.raises(am_master.MasterError):
        am_master.tron_cuoi(nen, [lo], str(tn / "y.wav"), tong_giay=TONG,
                            am=_ho_so(), nhac_nen_duong=None)        # co ho so, khong duong


# ── ⑤⑥ Bon ca do dai (luat #5 cua brief) ────────────────────────────────────

def test_VIDEO_CAM_ban_ra_dai_DUNG_video_va_nhac_van_nghe_duoc(
        nen_lo_im_lang, tmp_path_factory):
    """⑤ Ca 'video cam' (xem canh bao tien de dau tep): `nen`/loi hoan toan im
    lang, chi con nhac nen. Ban ra phai dai DUNG `tong_giay` (bay `apad`,
    Viral `xu_ly_video.py:1197-1212`) va nhac phai con NGHE DUOC (khong bi mot
    nhanh `amix` nao bo mat)."""
    from apps.auto_scan_video import am_master, hop_dong_v4

    t, nen, lo = nen_lo_im_lang
    tn = tmp_path_factory.mktemp("v3cam")
    nhac = _tieng(tn, "nhac", hz=440, dur=TONG, loud=True)
    ra = str(tn / "cam.wav")
    am_master.tron_cuoi(nen, [lo], ra, tong_giay=TONG,
                        am=_ho_so(am_luong_nen=1.0), nhac_nen_duong=nhac)
    kq = am_master.kiem_ban_ra(ra, mong_doi_giay=TONG,
                               dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S)
    assert abs(kq["lech_giay"]) <= hop_dong_v4.DUNG_SAI_DO_DAI_S
    assert kq["dinh_that"] > -60, "nhac nen bi mat trong ca video cam"


def test_NHAC_NGAN_hon_video_VOI_lap_van_DAI_DUNG(nen_lo, tmp_path_factory):
    """⑥ Nhac 2 s, video 6 s, `lap=True` (mac dinh) -> nhac duoc LAP cho du
    (Viral `xu_ly_video.py:1091-1093`), ban ra van dai dung `tong_giay`."""
    from apps.auto_scan_video import am_master, hop_dong_v4

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3ngan_lap")
    nhac = _tieng(tn, "nhac", hz=440, dur=2.0)
    ra = str(tn / "ra.wav")
    am_master.tron_cuoi(nen, [lo], ra, tong_giay=TONG,
                        am=_ho_so(lap=True), nhac_nen_duong=nhac)
    kq = am_master.kiem_ban_ra(ra, mong_doi_giay=TONG,
                               dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S)
    assert abs(kq["lech_giay"]) <= hop_dong_v4.DUNG_SAI_DO_DAI_S


def test_NHAC_NGAN_hon_video_TAT_lap_van_DAI_DUNG_nho_apad(nen_lo, tmp_path_factory):
    """⑥ Cung nhac ngan nhung `lap=False` — KHONG co `-stream_loop`, chi con
    `apad` giu do dai (bay Viral `xu_ly_video.py:1197-1212`: thieu no thi
    nhanh nhac ket thuc som va ban ra bi cat theo nhac)."""
    from apps.auto_scan_video import am_master, hop_dong_v4

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3ngan_khong_lap")
    nhac = _tieng(tn, "nhac", hz=440, dur=2.0)
    ra = str(tn / "ra.wav")
    am_master.tron_cuoi(nen, [lo], ra, tong_giay=TONG,
                        am=_ho_so(lap=False), nhac_nen_duong=nhac)
    kq = am_master.kiem_ban_ra(ra, mong_doi_giay=TONG,
                               dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S)
    assert abs(kq["lech_giay"]) <= hop_dong_v4.DUNG_SAI_DO_DAI_S


def test_NHAC_DAI_hon_video_bi_CAT_vua_khit(nen_lo, tmp_path_factory):
    """⑥ Nhac 20 s, video 6 s -> ban ra van dai dung `tong_giay`, khong keo dai
    theo nhac (`-t tong_giay` tren dau ra chot do dai, khong phu thuoc co lap
    hay khong)."""
    from apps.auto_scan_video import am_master, hop_dong_v4

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3dai")
    nhac = _tieng(tn, "nhac", hz=440, dur=20.0)
    ra = str(tn / "ra.wav")
    am_master.tron_cuoi(nen, [lo], ra, tong_giay=TONG,
                        am=_ho_so(lap=False), nhac_nen_duong=nhac)
    kq = am_master.kiem_ban_ra(ra, mong_doi_giay=TONG,
                               dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S)
    assert abs(kq["lech_giay"]) <= hop_dong_v4.DUNG_SAI_DO_DAI_S


# ── ⑦ Khong clip ────────────────────────────────────────────────────────────

def test_GAIN_CAO_khong_vuot_DINH_THAT(nen_lo, tmp_path_factory):
    """⑦ Nguon gan full-scale + `am_luong_nen` o TRAN TREN
    (`NHAC_NEN_AM_LUONG_LON_NHAT` = 2,0) se lam `amix normalize=0` cong ra mot
    tin hieu vuot xa 0 dBFS truoc `loudnorm`. Do DINH THAT tren tep RA THAT
    (`han_dinh`/`ghim_tran_phoi` da chay ben trong `tron_cuoi`) — khong tin
    chuoi loc — va no phai o duoi (hoac sat) `DINH_THAT_DB`."""
    from apps.auto_scan_video import am_master, am_thanh, tach_tieng

    t, nen, lo = nen_lo
    tn = tmp_path_factory.mktemp("v3clip")
    nhac = _tieng(tn, "nhac", hz=440, dur=TONG, loud=True)
    ra = str(tn / "nong.wav")
    am_master.tron_cuoi(
        nen, [lo], ra, tong_giay=TONG,
        am=_ho_so(am_luong_nen=am_thanh.NHAC_NEN_AM_LUONG_LON_NHAT),
        nhac_nen_duong=nhac)
    dinh = _dinh_that(ra)
    # Dung sai 0,3 dB — khuon `test_2171` (sai so do cua `loudnorm` mot luot),
    # khong phai mot nguong long tay.
    assert dinh <= tach_tieng.DINH_THAT_DB + 0.3, (
        f"dinh that {dinh} dB vuot tran {tach_tieng.DINH_THAT_DB} dB — co the CLIP")


# ══════════════════════════════════════════════════════════════════════════
#  5. `assets.py` — ⑧ tran kich thuoc + quyen so huu (DUNG LAI, khong viet moi)
# ══════════════════════════════════════════════════════════════════════════

def test_tran_nhac_nen_byte_LAY_TU_chinh_sach_NEN_TANG():
    """⛔ Khong tu dat mot con so thu hai — `tran_nhac_nen_byte()` phai bang
    dung `CLOUDFLARE_BODY_LIMIT` (khuon `features.tran_logo_byte()`)."""
    from apps.auto_scan_video import assets
    from platform_core.storage import CLOUDFLARE_BODY_LIMIT

    assert assets.tran_nhac_nen_byte() == CLOUDFLARE_BODY_LIMIT == 100 * 1024 * 1024


def test_KIND_AUDIO_da_co_san_khong_can_mot_loai_artifact_moi():
    from apps.auto_scan_video.tables import KIND_AUDIO, KINDS

    assert KIND_AUDIO in KINDS


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'asv_v3.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


@pytest.fixture()
def kho(tmp_path):
    from platform_core.storage import LocalStorage, set_storage

    k = LocalStorage(str(tmp_path / "kho"))
    set_storage(k)
    yield k
    set_storage(None)


def test_NHAC_NEN_DA_PROMOTE_chi_CHU_SO_HUU_moi_doc_duoc(db, kho, tmp_path):
    """⑧ Duong `assets` da co san kiem quyen so huu (`asset_cua`) + kiem noi
    dung `kind="audio"` (`kiem_hop_le`, KHONG can mot `kind` moi — xem test o
    tren) — day la phep kiem chot LAI hai nang luc do CHO CHINH tinh huong
    nhac nen khach tai len, khong viet duong thu hai."""
    from tests.conftest import bao_dam_user

    from apps.auto_scan_video import assets

    bao_dam_user(db, "chu"); bao_dam_user(db, "nguoi_khac")
    db.commit()

    nhac = _tieng(tmp_path, "nhac_upload", hz=300, dur=1.0)
    staging = assets.khoa_staging(owner_id="chu", run_id="run1", stage="nhac_nen",
                                  van_tay="a" * 32, duoi="wav")
    with open(nhac, "rb") as f:
        kho.put(staging, f, content_type="audio/wav")

    hang = assets.promote_va_ghi(db, kho, owner_id="chu", run_id="run1",
                                 stage="nhac_nen", van_tay="a" * 32, kind="audio",
                                 duoi="wav", staging_key=staging)
    db.commit()

    # Chu so huu doc duoc.
    assert assets.asset_cua(db, hang.storage_key, "chu").id == hang.id
    # Nguoi khac — KHONG.
    with pytest.raises(assets.AssetError):
        assets.asset_cua(db, hang.storage_key, "nguoi_khac")
