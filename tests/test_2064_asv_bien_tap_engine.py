"""asv-final lan `bien-tap` — ENGINE THAT: do tren tep ra, khong tin chuoi loc.

Moi bai render mot nguon tong hop nho (640x360, vai giay) qua CHINH ham san pham
(`che_do_render.loc_cat_noi` / `ket_xuat.dung_lenh`), roi do tren tep ra:

  · khung/ti le/phong/cat — tep ra FFV1 (khong mat mat, `PHA11 §4`) so TUNG DIEM
    ANH voi mot phep bien doi doc lap tren nguon: PSNR `inf` = dung cho, dung co;
    va so voi nguon/khung khac: PSNR huu han = khac biet NHIN THAY duoc;
  · toc do — `dung_lenh` that (libx264 + AAC): chop sang o hinh va tieng bip o ban
    phoi, cung dat tai giay 4,0 truc bien tap, phai cung roi vao 3,2 s ban ra; va
    `qc.kiem` tren tep ra: T2/T7/T11/T15/T16 DAT.

⭐ ffmpeg KHONG phai phep kiem nang (`rao_chan_nang`: "no la cong cu, chay vai tram
   mili giay"), nen bai nay KHONG sau rao — no chay trong gate.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, bien_tap as bt, che_do_render as cdr,
                                  giai_doan_hinh_anh as gdha, hinh_hoc,
                                  ket_xuat, nhap_media, phu_de, qc, vung_che)

W, H = 640, 360


def _chay(cmd, timeout=180):
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True,
                       timeout=timeout, errors="replace")
    assert r.returncode == 0, (r.stderr or "")[-1500:]
    return r


@pytest.fixture(scope="module")
def nguon(tmp_path_factory):
    thu = tmp_path_factory.mktemp("bt_nguon")
    p = thu / "nguon.mkv"
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", f"testsrc2=size={W}x{H}:rate=25:duration=2",
           "-c:v", "ffv1", "-level", "3", p])
    return p


def _render(nguon, ra, *, bien_tap=None, vung=()):
    loc = cdr.loc_cat_noi([(0.0, 2.0)], vung=vung, bien_tap=bien_tap,
                          rong_nguon=W, cao_nguon=H)
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", nguon,
           "-filter_complex", loc, "-map", "[ra]", "-c:v", "ffv1", "-level", "3",
           ra])
    return ra


def _doc_lap(nguon, ra, vf):
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", nguon,
           "-vf", vf, "-c:v", "ffv1", "-level", "3", ra])
    return ra


def _kich(p):
    r = _chay(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height", "-of", "csv=p=0", p])
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def _psnr(a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b),
                        "-lavfi", "psnr", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace", timeout=120)
    m = re.search(r"average:(inf|[0-9.]+)", r.stderr or "")
    assert m, (r.stderr or "")[-800:]
    return float("inf") if m.group(1) == "inf" else float(m.group(1))


# ══ 1. Khung: dung CHO, dung CO, va KHAC nguon ══════════════════════════════

@pytest.mark.parametrize("ten,ho_so,vf_doc_lap", [
    ("ti_le_9_16_cat", {"khung": {"ti_le": "9:16", "cach": "cat"}},
     "crop=202:360:218:0,setsar=1"),
    ("ti_le_1_1_tam_trai", {"khung": {"ti_le": "1:1", "cach": "cat", "tam_x": 0.0}},
     "crop=360:360:0:0,setsar=1"),
    ("cat_khung", {"cat_khung": {"x0": 0.25, "y0": 0.0, "x1": 0.75, "y1": 1.0}},
     "crop=320:360:160:0,setsar=1"),
    ("zoom_2x", {"zoom": {"he_so": 2.0}},
     "crop=320:180:160:90,scale=640:360:flags=lanczos,setsar=1"),
])
def test_khung_ra_TRUNG_phep_doc_lap_va_KHAC_nguon(nguon, tmp_path, ten, ho_so,
                                                   vf_doc_lap):
    ho_so = bt.chuan_hoa(ho_so)
    ra = _render(nguon, tmp_path / f"{ten}.mkv", bien_tap=ho_so)
    assert _kich(ra) == hinh_hoc.khung_bien_tap(W, H, ho_so)["ra"]
    doc_lap = _doc_lap(nguon, tmp_path / f"{ten}_dl.mkv", vf_doc_lap)
    assert _psnr(ra, doc_lap) == float("inf"), "khung ra khong trung phep doc lap"
    if _kich(ra) == (W, H):          # cung co thi so voi nguon: phai KHAC
        assert _psnr(ra, nguon) < 40


def test_nen_mo_khung_doc_hinh_giua_trung_nguon_thu_nho(nguon, tmp_path):
    ho_so = bt.chuan_hoa({"khung": {"ti_le": "9:16", "cach": "nen_mo"}})
    hh = hinh_hoc.khung_bien_tap(W, H, ho_so)
    ra = _render(nguon, tmp_path / "nen_mo.mkv", bien_tap=ho_so)
    assert _kich(ra) == hh["ra"] == (360, 640)
    (fw, fh), (px, py) = hh["khung"]["hinh"], hh["khung"]["vi_tri"]
    giua = _doc_lap(ra, tmp_path / "giua.mkv", f"crop={fw}:{fh}:{px}:{py}")
    nho = _doc_lap(nguon, tmp_path / "nho.mkv", f"scale={fw}:{fh},setsar=1")
    assert _psnr(giua, nho) == float("inf"), "hinh giua khung khong phai nguon thu nho"
    # Dai tren KHONG den: nen la chinh video lam mo, khong phai vien den.
    tren = _doc_lap(ra, tmp_path / "tren.mkv", f"crop={fw}:{py}:0:0,signalstats")
    r = _chay(["ffmpeg", "-hide_banner", "-i", tren, "-vf",
               "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
               "-f", "null", "-"])
    yavg = [float(x) for x in re.findall(r"YAVG=([0-9.]+)", r.stderr)]
    assert yavg and min(yavg) > 20, yavg


def test_L3_vung_che_NGOAI_cua_so_cat_khong_de_lai_vet(nguon, tmp_path):
    """`vung_che` L3: bien doi hinh lam hop ra ngoai khung thi LOAI, khong KEP.

    Vung che ap TRUOC khung (toa do nguon), nen mot vung o mep trai (0-20%) bi cat
    mat hoan toan khi giu 30-100%: ban ra co vung == ban ra khong vung, TUNG diem
    anh. Doi chung: vung nam TRONG cua so thi ban ra phai khac.
    """
    ho_so = bt.chuan_hoa({"cat_khung": {"x0": 0.3, "y0": 0.0, "x1": 1.0, "y1": 1.0}})

    def vung(x0, x1):
        return vung_che.chuan_hoa([{"x0": x0, "y0": 0.1, "x1": x1, "y1": 0.9,
                                    "loai": "lam_mo"}])
    khong = _render(nguon, tmp_path / "khong.mkv", bien_tap=ho_so)
    ngoai = _render(nguon, tmp_path / "ngoai.mkv", bien_tap=ho_so, vung=vung(0.0, 0.2))
    trong = _render(nguon, tmp_path / "trong.mkv", bien_tap=ho_so, vung=vung(0.5, 0.7))
    assert _psnr(ngoai, khong) == float("inf"), "vung ngoai cua so van de vet"
    assert _psnr(trong, khong) < 60, "doi chung: vung trong cua so phai che"


# ══ 2. Toc do: dong bo hinh/tieng + QC tren dung_lenh THAT ══════════════════

def _moc_sang(p):
    r = _chay(["ffmpeg", "-hide_banner", "-i", p, "-vf",
               "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
               "-f", "null", "-"])
    moc = re.findall(r"pts_time:([0-9.]+)", r.stderr)
    yavg = re.findall(r"YAVG=([0-9.]+)", r.stderr)
    for t, y in zip(moc, yavg, strict=False):
        if float(y) > 100:
            return float(t)
    raise AssertionError("khong thay chop sang")


def _moc_tieng(p, tan_so=8000):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(p),
                        "-map", "0:a:0", "-ac", "1", "-ar", str(tan_so), "-f", "s16le",
                        "-"], capture_output=True, timeout=120)
    assert r.returncode == 0
    import array
    a = array.array("h")
    a.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    for i, x in enumerate(a):
        if abs(x) > 3000:
            return i / tan_so
    raise AssertionError("khong thay tieng bip")


def test_toc_do_1_25_QUA_CA_HAI_GIAI_DOAN__hinh_tieng_phu_de_cung_roi_vao_3_2s(
        tmp_path):
    """🔴 **Bai nay chay CA HAI giai doan, va do la yeu cau cua B6 (27/09).**

    Truoc B6, `toc_do` ap o GD1 nen bai nay dung MOT lenh (`ket_xuat`) la du. Nay
    toc do ap o CUOI GD2, nen mot bai chi chay GD1 se **⛔ khong do gi ca**: no se
    xanh mai mai tren mot tep ⛔ chua doi toc do.

    Chuoi do:
      1. GD1 (`ket_xuat.dung_lenh`) — nguon 8 s / 25 fps ⇒ ban ra **8 s**, ⛔ khong
         doi moc. Chop sang van o **4,0 s**.
      2. GD2 (`giai_doan_hinh_anh.dung_lenh`, `toc_do = 1,25`) ⇒ ban giao **6,4 s**,
         chop sang o **3,2 s**, tieng bip o **3,2 s**, A/V lech <= 1 khung.

    ⭐ Buoc 1 la phep do QUAN TRONG NHAT o day: no chung minh GD1 **⛔ khong** doi
       moc thoi gian. Thieu no thi mot phep chia sot lai o GD1 se lam ban giao dai
       5,12 s (8 / 1,25 / 1,25) va ta chi biet "sai o dau do".
    """
    video = tmp_path / "v.mp4"
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "color=c=black:s=640x360:r=25:d=8,drawbox=x=0:y=0:w=640:h=360:"
           "color=white:t=fill:enable='between(t,4,4.4)'",
           "-c:v", "libx264", "-g", "250", video])
    master = tmp_path / "m.wav"
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "aevalsrc='if(between(t,4,4.4),0.5*sin(2*PI*1000*t),0)':s=48000:d=8",
           "-ac", "2", master])
    ke_hoach = {"doan": [{"ma": "s1", "dai_ms": 400, "dat_tai_ms": 4000,
                          "he_so_toc": 1.0, "ngan_sach_ms": 400, "troi_sau_ms": 0}],
                "ban_do": {"giu": [[0.0, 8.0]], "thoi_luong_nguon": 8.0}}
    su_kien = [{"start": 4.0, "end": 7.9, "text": "Xin chao", "display_text": "Xin chao",
                "line_count": 1, "scene_id": "s1", "index": 0}]
    pd = dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
              su_kien=su_kien)
    # 🔴 **`bien_tap` ⛔ KHONG con truyen vao ban dung GD1 (B6).** `ban_dung.dung`
    #    NEM neu bi truyen — GD1 ⛔ khong thuc thi phep bien tap nao, va GD2 doc
    #    `cai_dat.doc(run)` thang. `ho_so.su_kien` van luu o day cho T15.
    ban = ban_dung.dung(
        khoa_video="v", khoa_nen="n", khoa_master="m", ke_hoach=ke_hoach,
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "s1"}]}, phien_ban_ffmpeg="8",
        tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
        khoang_giu=[(0.0, 8.0)], preset="smart_localize", rong_khung=640,
        cao_khung=360, phu_de=pd)
    assert ban["ra"]["thoi_luong_giay"] == pytest.approx(8.0), (
        "ban dung GD1 hua mot do dai KHAC do dai nguon ⇒ con mot phep chia cho "
        "`toc_do` sot lai o GD1")

    # ── Giai doan 1: ⛔ KHONG doi moc thoi gian ──────────────────────────────
    gd1 = tmp_path / "gd1.mp4"
    _chay(ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video=str(video),
        duong_master=str(master), duong_lop=[str(master)],
        duong_ra=str(gd1), bo_ma_hoa="libx264", tien_do=False))
    tt1 = nhap_media.soi(str(gd1))
    assert float(tt1["thoi_luong"]) == pytest.approx(8.0, abs=0.1), tt1
    assert _moc_sang(gd1) == pytest.approx(4.0, abs=0.05), (
        "GD1 da doi moc thoi gian — chop sang phai VAN o 4,0 s")

    # ── Giai doan 2: cat (⛔ khong cat gi o day) roi DOI TOC DO o duoi chuoi ──
    ra = tmp_path / "ra.mp4"
    _chay(gdha.dung_lenh(
        str(gd1), str(ra), khoang=[(0.0, 8.0)], bo_ma_hoa="libx264",
        ffmpeg_bin="ffmpeg", thoi_luong_ra=8.0, tien_do=False,
        bien_tap={"toc_do": 1.25}, rong_nguon=640, cao_nguon=360,
        # ⭐ GD2 tu soi tep vao cua chinh no; o day ta khai dung con so ma
        #    `nhap_media.nhip_that(tt1)` se tra — 25 fps.
        fps_vao=nhap_media.nhip_that(tt1)))

    tt = nhap_media.soi(str(ra))
    assert float(tt["thoi_luong"]) == pytest.approx(6.4, abs=0.1), tt

    t_hinh, t_tieng = _moc_sang(ra), _moc_tieng(ra)
    assert t_hinh == pytest.approx(3.2, abs=0.05), t_hinh
    assert t_tieng == pytest.approx(3.2, abs=0.05), t_tieng
    assert abs(t_hinh - t_tieng) <= 0.04, (t_hinh, t_tieng)

    # ── T17: tep ra phai HOP CHUAN — ⛔ khong moc nao trung ──────────────────
    #
    # 🔴 **⛔ Khong phep kiem nao canh dieu nay truoc 27/09, va do la vi sao T17
    #    do tren BA luot chay that ma bo test van xanh.**
    #
    #    `setpts=PTS/toc` nen moc cua tung khung. Neu ⛔ khong ai khai NHIP RA
    #    (`-r` = nhip vao x toc) thi nhieu khung roi vao CUNG mot moc: do duoc
    #    **40** moc trung tren fixture nay (25 fps) va **269** tren mot luot 30 fps.
    #
    # ⚠️ Va khang dinh TROI o tren ⛔ KHONG bat duoc no: `passthrough` cho troi
    #    15,9 ms — **duoi** nguong 40 ms — nen bai nay van xanh voi 40 moc trung.
    #    Do dung ho `pham vi phep do hep hon loi tuyen bo`.
    #
    # ⭐ Dem bang chinh cach T17 dem: giai ma ca tep va bat dong loi cua muxer.
    _gm = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "error", "-i", str(ra), "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    _trung = [d for d in (_gm.stderr or "").splitlines() if "monotonic" in d]
    assert not _trung, (
        f"{len(_trung)} moc thoi gian TRUNG trong tep ra — `setpts` da nen moc ma "
        f"⛔ khong ai khai nhip ra (`-r`). Vi du: {_trung[0][:120]}")

    # ── QC: `toc_do` den tu CAI DAT, ⛔ khong tu artifact GD1 (B6) ───────────
    #
    # ⭐ `giai_doan_qc` ghep `bien_tap` tu `cai_dat.doc(run)` vao `ban_hinh` truoc
    #    khi goi `qc.kiem`. O day ta lam dung dieu do bang tay, vi bai nay ⛔
    #    khong co `run`.
    hinh_qc = {**ban["hinh"], "bien_tap": {"toc_do": 1.25}}
    bc = qc.kiem(tt_ra=tt, tt_nguon=nhap_media.soi(str(video)),
                 am_luong={"lufs": -14.0, "dinh_that": -2.0}, ke_hoach=ke_hoach,
                 ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "s1"}]},
                 ban_dung_lop=ban["tieng"]["lop"], che_do_render=cdr.CAT_MA_HOA_LAI,
                 thoi_luong_mong_doi=bt.moc_ban_ra(8.0, {"toc_do": 1.25}),
                 ban_hinh=hinh_qc)
    trang = {m["ma"]: m["trang_thai"] for m in bc["muc"]}
    for ma in ("T1", "T2", "T7", "T11", "T15", "T16"):
        assert trang[ma] == qc.DAT, (ma, [m for m in bc["muc"] if m["ma"] == ma])

def test_CAT_VA_DOI_TOC_cung_luc__ban_do_cat_roi_toc_do__moc_roi_DUNG(tmp_path):
    """🔴 **Ca ma bai tren ⛔ KHONG phu: ban do cat KHAC dong nhat.**

    `test_toc_do_1_25_QUA_CA_HAI_GIAI_DOAN` giu `[0, 8)` — tuc ban do cat la phep
    DONG NHAT, nen no ⛔ khong the phat hien mot phep hop thanh sai giua *cat* va
    *doi toc*. Day chinh la cho con bug truoc B6 se cat vao: hai phep doi truc
    xep sai thu tu thi chi lo ra khi CA HAI deu khac dong nhat.

    So do (nguon 12 s / 25 fps, chop sang o 9,0-9,4 s, giu `[0,4)` + `[8,12)`):

        sau cat, truc NGUON : chop o 4,0 + (9,0 - 8,0) = **5,0 s**, dai 8,0 s
        toc 1,25            : chop o 5,0 / 1,25 = **4,0 s**, dai 6,4 s

    ⭐ Do 27/09: ca hai lech **+0,0 ms**, 0 loi DTS, dai dung 8,000 va 6,400.
    """
    gd1 = tmp_path / "gd1.mp4"
    _chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", "color=c=black:s=320x180:r=25:d=12,drawbox=x=0:y=0:w=320:h=180:"
           "color=white:t=fill:enable='between(t,9,9.4)'",
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=12",
           "-c:v", "libx264", "-g", "250", "-c:a", "aac", "-shortest", gd1])
    tt1 = nhap_media.soi(str(gd1))
    assert _moc_sang(gd1) == pytest.approx(9.0, abs=0.05)

    khoang = [(0.0, 4.0), (8.0, 12.0)]
    dai_sau_cat = sum(k - b for b, k in khoang)          # 8,0 s truc NGUON

    # ⚠️ `ho_so` chu ⛔ khong `bt`: `bt` la ten module `bien_tap` da import o dau
    #    tep, va mot bien vong lap cung ten se CHE no (ruff F402).
    for ho_so, dai_mong, chop_mong in ((None, 8.0, 5.0),
                                       ({"toc_do": 1.25}, 6.4, 4.0)):
        ra = tmp_path / ("ra_%s.mp4" % (ho_so or {}).get("toc_do", 1))
        _chay(gdha.dung_lenh(
            str(gd1), str(ra), khoang=khoang, bo_ma_hoa="libx264",
            ffmpeg_bin="ffmpeg", thoi_luong_ra=dai_sau_cat, tien_do=False,
            bien_tap=ho_so, rong_nguon=320, cao_nguon=180,
            fps_vao=nhap_media.nhip_that(tt1)))
        tt = nhap_media.soi(str(ra))
        assert float(tt["thoi_luong"]) == pytest.approx(dai_mong, abs=0.1), (ho_so, tt)
        # ⭐ Khang dinh THAT SU dang do: noi dung roi dung CHO, ⛔ khong chi dung
        #    DO DAI. Mot tep dai dung ma noi dung lech la thu khach nhin thay.
        assert _moc_sang(ra) == pytest.approx(chop_mong, abs=0.05), (ho_so, ra)
        _gm = subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-i", str(ra), "-f", "null",
             "-"], capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        _trung = [d for d in (_gm.stderr or "").splitlines() if "monotonic" in d]
        assert not _trung, (ho_so, len(_trung), _trung[0][:120])
