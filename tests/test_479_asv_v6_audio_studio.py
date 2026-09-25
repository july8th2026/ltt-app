"""ASV V6 pha 23 — Audio Studio: muc nen, ha nen theo loi, fade; MOT thanh muc.

🔴 **Vi sao chi MOT thanh muc.** Ban phoi ket thuc bang `loudnorm` ve -14 LUFS,
   nen "giong +3 / nen -3" va "giong 0 / nen -6" ra cung mot tep (SNR 69,7 dB),
   con doi TI LE thi khac han (9,4 dB). Mot thanh "muc giong" canh thanh nen se
   la mot thanh keo khong lam gi. `test_giao_dien_chi_co_MOT_thanh_keo_am_thanh`
   giu quyet dinh do.

⭐ Moi dieu khien duoc kiem tren **tep ra that** cua `am_master.tron_cuoi` (ffmpeg
   that, `loudnorm` hai luot that): nen va loi dat o hai DAI TAN tach nhau, nen
   loc thong thap doc duoc rieng muc nen ngay trong ban phoi da tron.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from apps.auto_scan_video import am_master, am_thanh, cai_dat
from tests import test_423_asv_giao_dien as _mt

GOC = Path(__file__).resolve().parents[1]
moi_truong = _mt.moi_truong


# ══ 1. Ho so: duyet o cua ═══════════════════════════════════════════════════

def test_rong_va_bang_MAC_DINH_deu_la_None():
    """⛔ Ho so mac dinh KHONG duoc ghi (`cai_dat.KHOA_THUA`)."""
    assert am_thanh.tu_form("") is None
    assert am_thanh.tu_form("{}") is None
    assert am_thanh.tu_form(json.dumps({"nen_db": am_master.NEN_GIAM_DB})) is None


def test_ho_so_mot_phan_duoc_dien_day_du_va_LUY_DANG():
    ra = am_thanh.tu_form('{"nen_db": -12, "fade_ra": 1.5}')
    assert ra == {"nen_db": -12.0, "giam_theo_loi": False, "fade_vao": 0.0,
                  "fade_ra": 1.5, "nhac_nen": None}
    assert am_thanh.chuan_hoa(ra) == ra


def test_mac_dinh_la_CHINH_hang_so_cua_am_master():
    """Hai cho khai cung mot con so la hai cho se lech nhau."""
    assert am_thanh.MAC_DINH["nen_db"] is am_master.NEN_GIAM_DB


@pytest.mark.parametrize("xau", [
    '{"nen_db": 3}', '{"nen_db": -30}', '{"nen_db": "to"}', '{"nen_db": true}',
    '{"fade_vao": 6}', '{"fade_ra": -1}', '{"giam_theo_loi": 1}',
    '{"muc_giong": 3}', '{"nen_db": null, "giam_theo_loi": true}',
    '[1, 2]', '{khong phai json', '{"nen_db": NaN}',
])
def test_ho_so_xau_bi_TU_CHOI(xau):
    with pytest.raises(am_thanh.AmThanhLoi):
        am_thanh.tu_form(xau)


def test_cai_dat_LUU_thua_va_DOC_day():
    assert "am_thanh" in cai_dat.KHOA_THUA
    ho = {"nen_db": None, "giam_theo_loi": False, "fade_vao": 0.0, "fade_ra": 0.0}
    luu = cai_dat.chuan_hoa({"am_thanh": ho})
    assert luu["am_thanh"] == ho
    assert "am_thanh" not in cai_dat.chuan_hoa({})
    assert cai_dat.tu_ho_so(luu).am_thanh == ho
    assert cai_dat.tu_ho_so({}).am_thanh is None


# ══ 2. Chuoi loc ════════════════════════════════════════════════════════════

#: Chuoi tron TRUOC pha 23, go NGUYEN VAN (n = 3). Ho so mac dinh phai ra dung no:
#: doi no la doi ban ra cua moi lan chay khong chinh gi.
CHUOI_TRUOC_PHA_23 = (
    "[0:a]volume=-6.0dB,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[nen];"
    "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[t1];"
    "[2:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[t2];"
    "[nen][t1][t2]amix=inputs=3:normalize=0:dropout_transition=0[tron];")


def test_ho_so_MAC_DINH_ra_DUNG_chuoi_truoc_pha_23():
    assert am_master.bieu_thuc_tron(3, tong_giay=30) == CHUOI_TRUOC_PHA_23
    assert am_master.bieu_thuc_tron(3, am=dict(am_thanh.MAC_DINH),
                                    tong_giay=30) == CHUOI_TRUOC_PHA_23


def test_van_tay_ban_phoi_DOI_theo_ho_so_am_thanh():
    kw = dict(van_tay_nen="n", van_tay_ke_hoach="k",
              phien_ban_ffmpeg_="f")
    mac = am_master.van_tay_master(**kw)
    assert mac == am_master.van_tay_master(**kw, am_thanh=dict(am_thanh.MAC_DINH))
    for ho in ({"nen_db": -12.0}, {"giam_theo_loi": True}, {"fade_vao": 1.0},
               {"nen_db": None}):
        assert am_master.van_tay_master(**kw, am_thanh=ho) != mac, ho


def test_fade_bi_CAT_theo_do_dai_ban_phoi():
    assert am_master.fade_ap_dung({"fade_vao": 5.0, "fade_ra": 1.0}, 6.0) == (2.0, 1.0)
    assert am_master.fade_ap_dung(None, 60.0) == (0.0, 0.0)


# ══ 3. Tep ra THAT ══════════════════════════════════════════════════════════

TONG = 12.0
MOC_CAU = (2000, 5000, 8000)      # ba cau 1,5 s
DUOI_LOI = (5.3, 1.0)             # giua cau 2
GIUA_CAU = (3.8, 1.0)             # khong ai noi


def _ff(*a):
    from platform_core import media
    r = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-y", "-loglevel", "error", *a],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode()[-400:]


def _rms(duong, cua, *, loc):
    from platform_core import media
    r = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-ss", str(cua[0]), "-t",
                        str(cua[1]), "-i", duong, "-af", f"{loc},astats=metadata=0",
                        "-f", "null", "-"], capture_output=True, text=True)
    return float([d for d in r.stderr.splitlines() if "RMS level dB" in d][-1]
                 .split(":")[-1].replace("-inf", "-200"))


NEN_BANG = "lowpass=f=200,lowpass=f=200"     # nen: nhieu hong < 200 Hz
LOI_BANG = "highpass=f=700,highpass=f=700"   # loi: am 1 kHz


@pytest.fixture(scope="module")
def nguyen_lieu(tmp_path_factory):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    t = tmp_path_factory.mktemp("am23")
    nen = str(t / "nen.wav")
    # ⚠️ `seed` CO DINH: khong co no moi luot la mot tin hieu nen khac, va hai
    #    phep kiem duoi day tung do chap chon (nguong dat theo MOT luot do).
    _ff("-f", "lavfi", "-i", f"anoisesrc=c=pink:a=0.3:d={TONG}:seed=4", "-af", NEN_BANG,
        "-ar", "44100", "-ac", "2", nen)
    doan = []
    for i in range(3):
        d = str(t / f"d{i}.wav")
        _ff("-f", "lavfi", "-i", "sine=f=1000:d=1.5", "-af", "tremolo=f=5:d=0.6,volume=-9dB",
            "-ar", "44100", "-ac", "1", d)
        doan.append(d)
    lo = am_master.tron_lo(doan, list(MOC_CAU), [1.0] * 3, str(t / "lo.wav"), tong_giay=TONG)
    return t, nen, lo


def _tron(nguyen_lieu, ten, am):
    t, nen, lo = nguyen_lieu
    ra = str(t / f"{ten}.wav")
    am_master.tron_cuoi(nen, [lo], ra, tong_giay=TONG, am=am)
    am_master.kiem_ban_ra(ra, mong_doi_giay=TONG, dung_sai_giay=0.1)
    return ra


def test_NEN_THAP_hon_thi_nen_giua_hai_cau_NHO_hon_so_voi_loi(nguyen_lieu):
    """Muc nen la TI LE nen/loi: sau `loudnorm` phai doc bang hieu nen - loi."""
    def ti_le(ra):
        return _rms(ra, GIUA_CAU, loc=NEN_BANG) - _rms(ra, DUOI_LOI, loc=LOI_BANG)
    mac = ti_le(_tron(nguyen_lieu, "mac", None))
    thap = ti_le(_tron(nguyen_lieu, "thap", {"nen_db": -18}))
    # Do tren 8 seed nhieu nen: 12,85-13,52 dB cho 12 dB yeu cau — `loudnorm` nen
    # them mot chut. Nguong bao ca dai do, khong chinh theo mot luot.
    assert 10.5 <= mac - thap <= 14.5, (mac, thap)


def test_TAT_nen_thi_giua_hai_cau_la_IM_LANG(nguyen_lieu):
    ra = _tron(nguyen_lieu, "tat", {"nen_db": None})
    assert _rms(ra, GIUA_CAU, loc="anull") < -60
    assert _rms(ra, DUOI_LOI, loc=LOI_BANG) > -40, "tat nen ma mat ca loi"


def test_HA_THEO_LOI_ha_nen_DUOI_loi_va_GIU_nen_giua_hai_cau(nguyen_lieu):
    """🔑 Doi chung la chinh ban phoi co dinh CUNG NGUON: bat ha theo loi thi nen
       duoi loi thap them it nhat 5 dB so voi ban do.
    """
    def chenh(ra):
        return _rms(ra, GIUA_CAU, loc=NEN_BANG) - _rms(ra, DUOI_LOI, loc=NEN_BANG)
    co_dinh = chenh(_tron(nguyen_lieu, "co_dinh", {"nen_db": -6}))
    theo_loi = chenh(_tron(nguyen_lieu, "theo_loi", {"nen_db": -6, "giam_theo_loi": True}))
    # ⚠️ Ban CO DINH cung khong phang: `loudnorm` tu nen nen duoi loi 0,7-2,7 dB
    #    (do tren 8 seed, luon duong). Nen phep kiem so HIEU voi ban co dinh
    #    cung nguon: 6,5-8,0 dB tren 8 seed.
    assert co_dinh < 3.5, co_dinh
    assert theo_loi - co_dinh >= 5.0, (co_dinh, theo_loi)


def test_FADE_vao_va_ra_co_tren_tep_ra(nguyen_lieu):
    ra = _tron(nguyen_lieu, "fade", {"fade_vao": 3.0, "fade_ra": 3.0})
    mac = _tron(nguyen_lieu, "mac2", None)
    for cua in ((0.0, 0.8), (TONG - 0.8, 0.8)):
        assert _rms(ra, cua, loc=NEN_BANG) < _rms(mac, cua, loc=NEN_BANG) - 6, cua


# ══ 4. Cua HTTP + giao dien ═════════════════════════════════════════════════

def _nop(client, csrf, tmp_path, am):
    from tests.fixtures.asv_media import tiny_mp4
    from tests.test_475_asv_v6_voice_binding import _mau

    tep = tiny_mp4(tmp_path / "a.mp4", duration_s=1.0)
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao", data={
            "csrf_token": csrf, "che_do": "fit_original",
            "che_do_giong": "USER_SELECTED", "giong_id": _mau(), "am_thanh": am},
            files={"video": ("a.mp4", f, "video/mp4")})


def _run_moi_nhat():
    import platform_core.db as dbmod
    from sqlalchemy import func, select

    from apps.auto_scan_video.tables import AsvRun

    db = next(dbmod.get_session())
    try:
        n = db.execute(select(func.count()).select_from(AsvRun)).scalar_one()
        r = db.execute(select(AsvRun).order_by(AsvRun.created_at.desc())).scalars().first()
        return n, dict(r.settings or {}) if r else {}
    finally:
        db.close()


def test_HTTP_ho_so_xau_TU_CHOI_truoc_khi_tao_lan_chay(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    truoc, _ = _run_moi_nhat()
    r = _nop(a, csrf, tmp_path, '{"nen_db": 9}')
    assert r.status_code == 400, r.status_code
    assert "Mức nhạc nền phải từ" in r.text
    assert _run_moi_nhat()[0] == truoc


def test_HTTP_ho_so_hop_le_duoc_LUU_va_mac_dinh_thi_KHONG(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, '{"nen_db": -15, "giam_theo_loi": true}')
    assert r.status_code == 200, r.text[:300]
    assert _run_moi_nhat()[1]["am_thanh"]["nen_db"] == -15.0
    r = _nop(a, csrf, tmp_path, "")
    assert r.status_code == 200
    assert "am_thanh" not in _run_moi_nhat()[1]


def test_giao_dien_chi_co_MOT_thanh_keo_am_thanh():
    """🔴 Mot thanh "muc giong" canh thanh nen la mot tinh nang GIA sau `loudnorm`."""
    van = (GOC / "apps/auto_scan_video/templates/asv_trang_chinh.html").read_text(encoding="utf-8")
    dau = van.index('id="asv-nhom-am-thanh"')
    khoi = van[dau:van.index('name="am_thanh"', dau)]
    assert khoi.count('type="range"') == 1
    js = (GOC / "server/static/asv/am_thanh.js").read_text(encoding="utf-8")
    assert "muc_giong" not in js and "giong_db" not in js
