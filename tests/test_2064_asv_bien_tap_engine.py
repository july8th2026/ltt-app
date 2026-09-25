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
                                  hinh_hoc, ket_xuat, nhap_media, phu_de, qc,
                                  vung_che)

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


def test_toc_do_1_25_hinh_tieng_phu_de_cung_roi_vao_3_2s_va_QC_dat(tmp_path):
    """Doan loi `s1` dat tai 4,0 s truc bien tap. Ban ra 1,25x: phai o 3,2 s — ca
    chop sang cua hinh LAN tieng bip cua ban phoi (A/V lech <= 1 khung)."""
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
    # 🔴 **`phu_de` van luu trong ban dung GD1 (gd2-diem-anh), nhung GD1 KHONG
    #    con DOT no vao hinh** — `ket_xuat.dung_lenh` khong con nhan `duong_ass`.
    #    `ho_so.su_kien` van can cho phep kiem T15/`bt.moc_ban_ra` o duoi (chung
    #    doc `ban["hinh"]["phu_de"]`, khong quan tam ai dot no).
    ban = ban_dung.dung(
        khoa_video="v", khoa_nen="n", khoa_master="m", ke_hoach=ke_hoach,
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "s1"}]}, phien_ban_ffmpeg="8",
        tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
        khoang_giu=[(0.0, 8.0)], preset="smart_localize", rong_khung=640,
        cao_khung=360, phu_de=pd, bien_tap={"toc_do": 1.25})
    ra = tmp_path / "ra.mp4"
    cmd = ket_xuat.dung_lenh(ban, ffmpeg_bin="ffmpeg", duong_video=str(video),
                             duong_master=str(master), duong_lop=[str(master)],
                             duong_ra=str(ra), bo_ma_hoa="libx264", tien_do=False)
    _chay(cmd)

    tt = ket_xuat.kiem_tep_ra(str(ra), ban, soi=nhap_media.soi)
    assert tt["thoi_luong"] == pytest.approx(6.4, abs=0.1)

    t_hinh, t_tieng = _moc_sang(ra), _moc_tieng(ra)
    assert t_hinh == pytest.approx(3.2, abs=0.05), t_hinh
    assert t_tieng == pytest.approx(3.2, abs=0.05), t_tieng
    assert abs(t_hinh - t_tieng) <= 0.04, (t_hinh, t_tieng)

    bc = qc.kiem(tt_ra=tt, tt_nguon=nhap_media.soi(str(video)),
                 am_luong={"lufs": -14.0, "dinh_that": -2.0}, ke_hoach=ke_hoach,
                 ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "s1"}]},
                 ban_dung_lop=ban["tieng"]["lop"], che_do_render=cdr.CAT_MA_HOA_LAI,
                 thoi_luong_mong_doi=bt.moc_ban_ra(8.0, ban["hinh"]["bien_tap"]),
                 ban_hinh=ban["hinh"])
    trang = {m["ma"]: m["trang_thai"] for m in bc["muc"]}
    for ma in ("T1", "T2", "T7", "T11", "T15", "T16"):
        assert trang[ma] == qc.DAT, (ma, [m for m in bc["muc"] if m["ma"] == ma])
