"""Pha 15 — trinh render.

Cong thoat cua pha nay la mot menh de rat cu the: **mot ban dung da luu, MOT
MINH, phai tai tao duoc mot tep media da kiem.** Moi phep kiem o day phuc vu
mot trong hai nua cua menh de do: *mot minh* (khong hoi thuong nguon) va *da
kiem* (khong promote mot thu chua ai soi).
"""
from __future__ import annotations

import ast
import inspect
import io
import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

from apps.auto_scan_video import (ban_dung, giai_doan_ket_xuat, ket_xuat,
                                  nhap_media, pipeline)
from tests.fixtures import asv_media as fx
from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham


def _ban(*, so_lop: int = 2, tong_giay: float = 2.0,
         he_so: float = 1.0) -> dict:
    lop = [{"ma": str(i + 1), "khoa": f"k{i}", "dat_tai_ms": i * 500,
            "he_so_toc": he_so} for i in range(so_lop)]
    return {
        "schema": ban_dung.SCHEMA_BAN_DUNG,
        "phien_ban": ban_dung.PHIEN_BAN_BAN_DUNG,
        "hinh": {"khoa": "v", "che_do": "copy"},
        "tieng": {"nen": {"khoa": "n"}, "lop": lop,
                  "tan_so": ban_dung.TAN_SO_RA, "so_kenh": ban_dung.SO_KENH_RA},
        "ra": {"container": "mp4", "codec_tieng": ban_dung.CODEC_TIENG,
               "bitrate_tieng": ban_dung.BITRATE_TIENG, "faststart": True,
               "thoi_luong_giay": tong_giay},
        "cong_cu": {"ffmpeg": "ffmpeg version test"},
    }


def _lenh(ban, **kw):
    n = len(ban["tieng"]["lop"])
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="/t/v.mp4", duong_nen="/t/n.wav",
        duong_lop=[f"/t/s{i}.wav" for i in range(n)], duong_ra="/t/o.mp4", **kw)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Parity — chinh sach thua ke tu ban render di san (muc 1, muc 2)
# ══════════════════════════════════════════════════════════════════════════════

#: Khuon `replace_audio` cua `Cut_only ver2/nerf_engine/stages/
#: ffmpeg_edit_cutonly.py:323`, cong chinh sach ma hoa tieng cua
#: `DUNGVIDEO-FULL/engine/assemble.py:199-207`.
#:
#: ⭐ Day la **khuon doi chieu** ma Prompt 15 muc 2 doi phai dung TRUOC khi rut
#:    ma. No khong so sanh tep ra (tep ra phu thuoc phien ban ffmpeg va khong
#:    tai lap duoc giua cac may) ma so sanh **quyet dinh**: doi mot trong nhung
#:    co nay la doi san pham, va phai la mot lan doi co y.
PARITY_DI_SAN = [
    ("-c:v", "copy"),        # khong bao gio ma hoa lai hinh (replace_audio)
    ("-c:a", "aac"),         # assemble.py:_audio_encode_args
    ("-b:a", "192k"),        # replace_audio
    ("-ar", "48000"),        # assemble.py:_audio_encode_args
    ("-ac", "2"),            # assemble.py:_audio_encode_args
    ("-movflags", "+faststart"),   # ca hai ban
]


def test_giu_dung_chinh_sach_ma_hoa_cua_ban_di_san():
    cmd = _lenh(_ban())
    for co, gt in PARITY_DI_SAN:
        assert co in cmd, f"mat co {co} so voi khuon di san"
        assert cmd[cmd.index(co) + 1] == gt, (
            f"{co} doi tu {gt!r} thanh {cmd[cmd.index(co) + 1]!r} — "
            f"lech khuon di san, phai la mot lan doi CO Y")


def test_co_shortest_de_tieng_tran_khong_keo_dai_video():
    """`-shortest` cua `replace_audio`: khong co no, mot doan tieng tran qua cuoi
    se keo dai tep ra bang mot khung hinh dong bang."""
    assert "-shortest" in _lenh(_ban())


def test_KHONG_BAO_GIO_ma_hoa_lai_hinh():
    ban = _ban()
    ban["hinh"]["che_do"] = "libx264"
    with pytest.raises(ket_xuat.KetXuatError):
        _lenh(ban)


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Lenh la HAM THUAN — dung duoc, kiem duoc, khong cham tep
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_bao_gio_shell_true():
    """⛔ Duong dan di vao argv. `shell=True` bien mot ten tep thanh mot cau lenh.

    ⚠️ Chot bang AST, **khong** bang `"shell=True" not in ma`. Ban dau co ca hai
       va nhanh quet chuoi do ngay — vi `ket_xuat.py` co mot dong tai lieu noi
       rang no khong dung `shell=True`. Do la lan thu TU trong dot xay nay mot
       danh sach dau hieu bat trung chinh tai lieu cua no.

    ⭐ Va bo nhanh quet chuoi khong lam guard yeu di: mot chuoi trong chu thich
       khong chay, con AST thay MOI cach truyen that — ke ca `shell=co` voi mot
       bien, ma quet chuoi khong bao gio thay.
    """
    for mod in (ket_xuat, giai_doan_ket_xuat):
        cay = ast.parse(inspect.getsource(mod))
        for nut in ast.walk(cay):
            if isinstance(nut, ast.keyword) and nut.arg == "shell":
                assert isinstance(nut.value, ast.Constant), (
                    f"{mod.__name__}: `shell=` nhan mot bieu thuc — khong doc "
                    f"tinh duoc, phai la hang so False")
                assert not nut.value.value, f"{mod.__name__} dung shell=True"


def test_atempo_CHI_ap_khi_he_so_lon_hon_1():
    assert "atempo" not in " ".join(_lenh(_ban(he_so=1.0)))
    assert "atempo=1.150000" in " ".join(_lenh(_ban(he_so=1.15)))


def test_adelay_dat_tre_cho_MOI_kenh():
    """Thieu `all=1` thi chi kenh dau bi tre — tieng lech hai ben tai."""
    loi = " ".join(_lenh(_ban()))
    assert "adelay=500:all=1" in loi


def test_amix_khong_chuan_hoa_bien_do():
    """`normalize=1` (mac dinh) chia bien do cho so dau vao ⇒ am luong cua ban
    long tieng phu thuoc vao SO CAU NOI. Khong ai yeu cau hanh vi do."""
    assert "normalize=0" in " ".join(_lenh(_ban()))


def test_moi_dau_vao_duoc_dat_dinh_dang_truoc_khi_tron():
    """Tieng TTS va nhac nen khong cung tan so; de `amix` tu chon la de no chon
    theo dau vao dau tien."""
    loi = " ".join(_lenh(_ban(so_lop=2)))
    assert loi.count("aformat=sample_rates=48000") == 3   # nen + 2 lop


def test_so_tep_lech_so_lop_bi_TU_CHOI():
    """Lech thu tu/so luong khong lam ffmpeg hong — no chi dat sai cau vao sai
    cho. Mot loi im lang phai bi bat o day."""
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.dung_lenh(_ban(so_lop=2), ffmpeg_bin="ffmpeg",
                           duong_video="/t/v.mp4", duong_nen="/t/n.wav",
                           duong_lop=["/t/s0.wav"], duong_ra="/t/o.mp4")


def test_khong_lop_tieng_nao_van_ra_lenh_hop_le():
    """Moi doan bi cat o TIMING la mot ket cuc hop le, khong phai mot loi."""
    cmd = _lenh(_ban(so_lop=0))
    assert "-filter_complex" not in cmd
    assert "1:a:0" in cmd


# ══════════════════════════════════════════════════════════════════════════════
#  §3  KHONG goi thuong nguon, KHONG xin GPU (muc 6, dieu cam)
# ══════════════════════════════════════════════════════════════════════════════

def test_renderer_KHONG_goi_chep_loi_model_hay_may_sinh_tieng():
    """⛔ Dieu cam cua Prompt 15, va no la thu lam cong thoat co nghia: mot lan
    render lai khong duoc keo theo mot lan goi model."""
    cam = ("dich_thuat", "giai_doan_noi_dung", "giong_noi", "giai_doan_giong",
           "ban_ghi", "giai_doan_chep_loi", "dieu_phoi", "sidecar_client")
    for mod in (ket_xuat, giai_doan_ket_xuat):
        assert _vi_pham(inspect.getsource(mod), cam) == [], (
            f"{mod.__name__} cham vao thuong nguon")


def test_renderer_KHONG_xin_GPU():
    """`-c:v copy` khong cham bo ma hoa. Xin mot suat GPU la giu mot thu khan
    hiem de khong dung toi (muc 6)."""
    for mod in (ket_xuat, giai_doan_ket_xuat):
        assert _vi_pham(inspect.getsource(mod), ("gpu_env", "gpu_lease")) == []


def test_RENDER_chay_o_lan_ffmpeg_va_khong_khai_tai_nguyen():
    g = next(x for x in pipeline.CHUOI if x.ten == pipeline.RENDER)
    assert g.app_slug == "asv_media", "RENDER phai o lan ffmpeg"
    assert g.tai_nguyen == "", "RENDER khong duoc dat cho mot tai nguyen nao"


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Ho so chan doan CHE truoc khi luu (muc 9)
# ══════════════════════════════════════════════════════════════════════════════

def test_ho_so_chan_doan_khong_lo_duong_dan():
    """Duong tam mang ten may va ten nguoi dung Windows. Mot ho so chan doan
    duoc doc boi nguoi khong phai chu tep do."""
    goc = r"C:\Users\NguoiThat\AppData\Local\Temp\asv-render-abc"
    cmd = ["ffmpeg", "-i", goc + r"\v.mp4", "-i", goc + r"\n.wav",
           "-c:v", "copy", goc + r"\ra.mp4"]
    ho_so = ket_xuat.ho_so_chan_doan(_ban(), cmd, goc_tam=goc,
                                     duoi_stderr="loi gi do")
    goi = json.dumps(ho_so, ensure_ascii=False)
    assert "NguoiThat" not in goi
    assert "AppData" not in goi
    # Van giu TEN TEP — do la thu lam ho so co ich.
    assert "v.mp4" in goi and "ra.mp4" in goi


def test_ho_so_chan_doan_cat_ngan_stderr():
    ho_so = ket_xuat.ho_so_chan_doan(_ban(), ["ffmpeg"], duoi_stderr="x" * 9000)
    assert len(ho_so["stderr"]) <= 2000


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Render THAT — smoke, va cac ket cuc hong (verification cua Prompt 15)
# ══════════════════════════════════════════════════════════════════════════════

def _tep_tieng(binary: str, dest: Path, giay: float, hz: int = 440) -> Path:
    subprocess.run([binary, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"sine=frequency={hz}:duration={giay}",
                    "-ar", "48000", "-ac", "2", str(dest)],
                   check=True, capture_output=True)
    return dest


def test_render_that_sinh_ra_tep_co_ca_hinh_va_tieng(tmp_path):
    binary = fx.require_ffmpeg()
    video = fx.tiny_mp4(tmp_path / "v.mp4", duration_s=2.0)
    nen = _tep_tieng(binary, tmp_path / "n.wav", 2.0, hz=220)
    s0 = _tep_tieng(binary, tmp_path / "s0.wav", 0.5)
    s1 = _tep_tieng(binary, tmp_path / "s1.wav", 0.5)
    ra = tmp_path / "ra.mp4"

    ban = _ban(so_lop=2, tong_giay=2.0)
    cmd = ket_xuat.dung_lenh(ban, ffmpeg_bin=binary, duong_video=str(video),
                             duong_nen=str(nen),
                             duong_lop=[str(s0), str(s1)], duong_ra=str(ra))
    ket_xuat._chay_co_tien_do(cmd, tong_giay=2.0, timeout=120)

    tt = ket_xuat.kiem_tep_ra(str(ra), ban, soi=nhap_media.soi)
    assert tt["co_video"] and tt["co_tieng"]
    assert tt["codec_video"] == "h264", "hinh da bi ma hoa lai"
    assert tt["codec_tieng"] == "aac"
    assert tt["tan_so"] == 48000 and tt["so_kenh"] == 2


def test_tien_do_duoc_bao_ra_trong_luc_render(tmp_path):
    binary = fx.require_ffmpeg()
    video = fx.tiny_mp4(tmp_path / "v.mp4", duration_s=3.0)
    nen = _tep_tieng(binary, tmp_path / "n.wav", 3.0)
    ra = tmp_path / "ra.mp4"
    ban = _ban(so_lop=0, tong_giay=3.0)
    cmd = ket_xuat.dung_lenh(ban, ffmpeg_bin=binary, duong_video=str(video),
                             duong_nen=str(nen), duong_lop=[], duong_ra=str(ra))
    thay: list[float] = []
    ket_xuat._chay_co_tien_do(cmd, tong_giay=3.0, timeout=120,
                              bao_tien_do=thay.append)
    assert thay, "khong nhan duoc mot moc tien do nao"
    assert max(thay) <= 100.0


def test_huy_giua_chung_thi_GIET_tien_trinh_va_khong_de_lai_ket_qua(tmp_path):
    """Huy la HOP TAC: giet tien trinh con roi nem, thay vi de mot lan render
    dai chay tiep sau khi khach da bam huy va da duoc hoan tien.

    ⭐ Va no phai huy duoc **ke ca khi ffmpeg khong in ra dong tien do nao** —
       do la cho ban cua `burn.py` khong lam duoc, vi no dua vao `on_progress`.
    """
    binary = fx.require_ffmpeg()
    ra = tmp_path / "ra.mp4"

    # ⭐ `-re` = doc dau vao dung THOI GIAN THUC, nen lenh nay chac chan chay
    #    30 giay bat ke may nhanh cham. Ban dau cho nay dung `-preset veryslow`
    #    tren mot video nho va phep kiem do: ffmpeg ma hoa xong truoc khi phep
    #    huy kip xen vao. Mot phep kiem ve dieu khien ma ket qua phu thuoc toc
    #    do CPU thi no dang do toc do CPU, khong do dieu khien.
    cmd = [binary, "-y", "-hide_banner", "-loglevel", "error", "-re",
           "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=30",
           "-c:v", "libx264", "-progress", "pipe:1", "-nostats", str(ra)]

    bat_dau = time.monotonic()
    with pytest.raises(nhap_media.DaHuy):
        ket_xuat._chay_co_tien_do(
            cmd, tong_giay=30.0, timeout=120,
            hoi_huy=lambda: time.monotonic() - bat_dau > 0.6)
    assert time.monotonic() - bat_dau < 30, "khong giet duoc tien trinh con"


def test_ffmpeg_that_bai_thi_nem_KetXuatError(tmp_path):
    binary = fx.require_ffmpeg()
    cmd = [binary, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(tmp_path / "khong-ton-tai.mp4"),
           "-progress", "pipe:1", "-nostats", str(tmp_path / "ra.mp4")]
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat._chay_co_tien_do(cmd, tong_giay=1.0, timeout=60)


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Kiem TRUOC khi promote (muc 8)
# ══════════════════════════════════════════════════════════════════════════════

def test_tep_rong_bi_TU_CHOI(tmp_path):
    p = tmp_path / "rong.mp4"
    p.write_bytes(b"")
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.kiem_tep_ra(str(p), _ban(), soi=nhap_media.soi)


def test_tep_khong_ton_tai_bi_TU_CHOI(tmp_path):
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.kiem_tep_ra(str(tmp_path / "khong.mp4"), _ban(),
                             soi=nhap_media.soi)


def test_thieu_luong_tieng_bi_TU_CHOI(tmp_path):
    """`ffmpeg tra ve 0` KHAC `co mot tep dung duoc`."""
    def _soi_gia(_d):
        return {"co_video": True, "co_tieng": False, "thoi_luong": 2.0,
                "co_byte": 100}
    p = tmp_path / "x.mp4"
    p.write_bytes(b"khong rong")
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.kiem_tep_ra(str(p), _ban(), soi=_soi_gia)


def test_thoi_luong_lech_qua_nguong_bi_TU_CHOI(tmp_path):
    """Mot ban long tieng dai sai la mot ban trong do tieng va hinh lech nhau —
    hong dung thu ma san pham nay ban."""
    def _soi_gia(_d):
        return {"co_video": True, "co_tieng": True, "thoi_luong": 9.0,
                "co_byte": 100}
    p = tmp_path / "x.mp4"
    p.write_bytes(b"khong rong")
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.kiem_tep_ra(str(p), _ban(tong_giay=2.0), soi=_soi_gia)


def test_lech_trong_nguong_thi_CHAP_NHAN(tmp_path):
    """Chieu nguoc lai: `-c:v copy` giu nguyen khung hinh nen sai so nho la
    binh thuong. Mot nguong qua chat se danh hong moi lan render that."""
    def _soi_gia(_d):
        return {"co_video": True, "co_tieng": True, "thoi_luong": 2.4,
                "co_byte": 100}
    p = tmp_path / "x.mp4"
    p.write_bytes(b"khong rong")
    ket_xuat.kiem_tep_ra(str(p), _ban(tong_giay=2.0), soi=_soi_gia)
