"""ASV final (lan fix-qc-am) — R-02: preset GIU HINH phai giao DU luong hinh.

🔴 **Vi sao bo kiem cu khong bat duoc.** T3 co tu pha 02 va `test_448` chay ca
   chuoi tren mot clip `lavfi`, nhung clip do duoc dung bang `testsrc` +
   `sine` **cung do dai**, nen luong tieng luon >= luong hinh va `-shortest`
   khong co gi de cat. Con `test_444`/`test_473` chi truyen hai CHUOI bam gia
   vao `qc.kiem` — chung kiem *cau lenh so sanh*, khong kiem *phep sao chep*.
   `qc.bam_luong_hinh` chua he duoc goi tren mot tep that trong ca bo kiem.

⇒ Dieu kien no lo ra la: **luong HINH cua nguon dai hon luong TIENG** — hinh
  dang binh thuong cua phim that (do tren bon phim khach: mot trong bon). Bai
  kiem nay dung dung hinh dang do.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, che_do_render as cdr,  # noqa: E402
                                  ket_xuat, qc)
from tests.fixtures import asv_media as fx  # noqa: E402

#: 🔑 **Dieu kien lam `-shortest` cat luong hinh, do 23/09 tren phim khach:**
#:    luong hinh cua NGUON ket thuc SAU ban phoi. No khong hiem — no la hinh
#:    dang mac dinh, vi `am_master.tron_cuoi` cat ban phoi bang
#:    `-t {tong_giay:.3f}`: mot video 106,833333 s cho ra ban phoi 106,833 s,
#:    tuc ngan hon **0,33 mili giay**, va the la du.
#:
#: ⭐ Nen clip o day dai 91 khung / 30 fps = 3,033333 s: lam tron ba chu so
#:    thap phan cho 3,033 — dung mot buoc voi duong san pham.
DAI_HINH_S = 91 / 30.0
DAI_TIENG_S = 2.6


def _nguon(dest: Path) -> Path:
    """MP4 h264 (co khung B, nhu phim that) voi luong hinh DAI HON luong tieng."""
    ff = fx.require_ffmpeg()
    subprocess.run(
        [ff, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=s=320x240:r=30:d={DAI_HINH_S}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={DAI_TIENG_S}",
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(dest)],
        check=True, capture_output=True)
    return dest


def _master(dest: Path, *, giay: float = DAI_HINH_S) -> Path:
    """Ban phoi dung khuon `am_master.tron_cuoi`: `-t` lam tron BA chu so."""
    ff = fx.require_ffmpeg()
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", f"{giay:.3f}", "-c:a", "pcm_s16le", str(dest)],
                   check=True, capture_output=True)
    return dest


def _ban(cach: str) -> dict:
    ban = {
        "schema": ban_dung.SCHEMA_BAN_DUNG,
        "phien_ban": ban_dung.PHIEN_BAN_BAN_DUNG,
        "hinh": {"khoa": "v", "che_do": "copy", "cach_render": cach},
        "tieng": {"nen": {"khoa": "n"}, "lop": [],
                  "tan_so": ban_dung.TAN_SO_RA, "so_kenh": ban_dung.SO_KENH_RA},
        "ra": {"container": "mp4", "codec_tieng": ban_dung.CODEC_TIENG,
               "bitrate_tieng": ban_dung.BITRATE_TIENG, "faststart": True,
               "thoi_luong_giay": DAI_HINH_S},
        "cong_cu": {"ffmpeg": "x"},
    }
    if cach == cdr.CAT_MA_HOA_LAI:
        ban["hinh"].update({"bo_ma_hoa": "libx264", "rong_khung": 320,
                            "cao_khung": 240,
                            "khoang_giu": [[0.0, DAI_HINH_S]],
                            # 🔴 gd2-diem-anh: preset CAT ma GD1 KHONG co vung
                            # /toc_do thi REMUX (khong con `-shortest`, xem
                            # `ket_xuat.dung_lenh`). `-shortest` chi con y
                            # nghia khi GD1 THAT SU ma hoa lai — gia lap dieu
                            # do bang mot `toc_do` khac 1.
                            "bien_tap": {"toc_do": 1.1}})
    return ban


def _lenh(cach: str, nguon: Path, master: Path, ra: Path) -> list[str]:
    return ket_xuat.dung_lenh(
        _ban(cach), ffmpeg_bin=fx.require_ffmpeg(), duong_video=str(nguon),
        duong_master=str(master), duong_lop=[], duong_ra=str(ra), tien_do=False)


def _so_khung(duong: Path) -> int:
    from platform_core import media

    r = subprocess.run([media.ffprobe_bin(), "-v", "error", "-select_streams", "v:0",
                        "-count_packets", "-show_entries", "stream=nb_read_packets",
                        "-of", "json", str(duong)], capture_output=True, check=True)
    g = json.loads(r.stdout.decode("utf-8", "replace"))
    return int(g["streams"][0]["nb_read_packets"])


# ── Chinh sach trong cau lenh ─────────────────────────────────────────────────

def test_duong_SAO_CHEP_khong_mang_shortest():
    """⛔ `-shortest` o duong `-c:v copy` chi co the cat hinh, khong the cuu gi."""
    cmd = _lenh(cdr.SAO_CHEP, Path("v.mp4"), Path("m.wav"), Path("o.mp4"))
    assert "-shortest" not in cmd


def test_duong_CAT_VAN_mang_shortest():
    """Chot duoc THU HEP chu khong bo: o duong ma hoa lai no van lam viec cu."""
    cmd = _lenh(cdr.CAT_MA_HOA_LAI, Path("v.mp4"), Path("m.wav"), Path("o.mp4"))
    assert "-shortest" in cmd


# ── ffmpeg that: luong hinh giong nguon TUNG BIT ──────────────────────────────

def test_ban_ra_giu_DU_khung_va_bam_bang_nguon(tmp_path):
    """T3 tren tep THAT, khong phai tren hai chuoi bam gia."""
    nguon = _nguon(tmp_path / "nguon.mp4")
    ra = tmp_path / "ra.mp4"
    subprocess.run(_lenh(cdr.SAO_CHEP, nguon, _master(tmp_path / "m.wav"), ra),
                   check=True, capture_output=True)

    assert _so_khung(ra) == _so_khung(nguon), "render sao chep lam mat khung hinh"
    assert qc.bam_luong_hinh(str(ra)) == qc.bam_luong_hinh(str(nguon))


def test_TIEM_LAI_shortest_thi_bam_KHAC_nguon(tmp_path):
    """Doi chung: khong co no, bai tren xanh ca khi loi quay lai.

    ⭐ Day la ban sao dung cua khiem khuyet R-02: cung cau lenh, chi them lai
       mot co. Neu mot ngay nao do `-shortest` quay ve duong sao chep, bai nay
       la thu noi *cai gi* dang xay ra chu khong chi *co gi do khac*.
    """
    nguon = _nguon(tmp_path / "nguon.mp4")
    ra = tmp_path / "ra_shortest.mp4"
    cmd = _lenh(cdr.SAO_CHEP, nguon, _master(tmp_path / "m.wav"), ra)
    subprocess.run(cmd[:-1] + ["-shortest", cmd[-1]], check=True,
                   capture_output=True)

    assert _so_khung(ra) < _so_khung(nguon)
    assert qc.bam_luong_hinh(str(ra)) != qc.bam_luong_hinh(str(nguon))


def test_QC_doc_hai_ban_bam_that_va_ket_luan_T3(tmp_path):
    """Khep vong: tu tep that -> `bam_luong_hinh` -> `qc.kiem` -> T3 `dat`."""
    nguon = _nguon(tmp_path / "nguon.mp4")
    ra = tmp_path / "ra.mp4"
    subprocess.run(_lenh(cdr.SAO_CHEP, nguon, _master(tmp_path / "m.wav"), ra),
                   check=True, capture_output=True)

    bc = qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": DAI_HINH_S},
                 tt_nguon={"thoi_luong": DAI_HINH_S}, am_luong={},
                 ke_hoach={"doan": []}, ban_ke_tieng={"doan": []},
                 bam_ra=qc.bam_luong_hinh(str(ra)),
                 bam_nguon=qc.bam_luong_hinh(str(nguon)),
                 che_do_render=cdr.SAO_CHEP, thoi_luong_mong_doi=DAI_HINH_S)
    t3 = next(m for m in bc["muc"] if m["ma"] == "T3")
    assert t3["trang_thai"] == qc.DAT, t3
