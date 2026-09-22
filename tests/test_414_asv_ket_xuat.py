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


def _ban_cat(**kw) -> dict:
    """Cung ban dung, nhung khai preset CAT (ma hoa lai)."""
    from apps.auto_scan_video import che_do_render as cdr

    ban = _ban(**kw)
    ban["hinh"].update({"cach_render": cdr.CAT_MA_HOA_LAI, "bo_ma_hoa": "libx264",
                        "khoang_giu": [[0.0, 2.0]]})
    return ban


def _lenh(ban, **kw):
    n = len(ban["tieng"]["lop"])
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="/t/v.mp4", duong_master="/t/n.wav",
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


def test_co_shortest_o_preset_CAT_de_tieng_tran_khong_keo_dai_video():
    """`-shortest` cua `replace_audio`: khong co no, mot doan tieng tran qua cuoi
    se keo dai tep ra bang mot khung hinh dong bang.

    🔴 **Chot nay tung la vo dieu kien, va no lam hong preset GIU HINH.**
       asv-final R-02: o duong `-c:v copy`, `-shortest` vut bo cac goi hinh cuoi
       khi luong hinh nguon dai hon luong tieng — do tren phim khach that, mat
       2 khung, MD5 luong hinh khac nguon, QC T3 hong. Chot duoc **thu hep** ve
       dung preset can no: `test_2014` giu dau kia.
    """
    from apps.auto_scan_video import che_do_render as cdr

    assert "-shortest" in _lenh(_ban_cat())
    assert "-shortest" not in _lenh(_ban()), (
        f"preset giu hinh ({cdr.SAO_CHEP}) khong duoc mang -shortest — no cat "
        f"khung hinh cuoi va pha loi hua 'khong mot diem anh nao doi'")


def test_preset_GIU_HINH_khong_bao_gio_ma_hoa_lai():
    """⛔ D-ASV-03: preset giu hinh **sao chep** luong hinh. Khong giai ma, khong
    ma hoa, khong mat mat the he, khong ton mot suat GPU nao.

    🔴 **Chot nay tung la "KHONG BAO GIO ma hoa lai hinh" — khong dieu kien.**
       Pha 17 lam no thanh sai: preset CAT **buoc phai** ma hoa lai, vi cat bang
       stream copy chi cat duoc tai keyframe va do that cho GOP 8,333 giay — tuc
       diem cat bi day di toi 8,3 giay so voi ban phoi am.

    ⭐ Nen menh de duoc **thu hep chu khong bo**: no van la mot loi hua, chi la
       mot loi hua cua MOT preset. Bo han no di se de preset giu hinh troi vao
       ma hoa lai ma khong ai thay.
    """
    from apps.auto_scan_video import che_do_render as cdr

    cmd = _lenh(_ban())          # mac dinh: SAO_CHEP
    assert "copy" in cmd
    for bo in cdr.THAM_SO:
        assert bo not in cmd, f"preset giu hinh dang ma hoa bang {bo}"
    assert "-filter_complex" not in cmd


def test_cach_render_KHONG_HOP_LE_bi_tu_choi():
    """Mot ban dung khai mot cach render khong co that phai hong o day, khong
    phai o giua mot luot ffmpeg da chiem suat."""
    ban = _ban()
    ban["hinh"]["cach_render"] = "phep_thuat"
    with pytest.raises(ket_xuat.KetXuatError):
        _lenh(ban)


def test_preset_CAT_ma_hoa_lai_va_KHONG_dung_copy():
    """Va chieu nguoc lai: preset cat khong duoc am tham dung `copy`."""
    from apps.auto_scan_video import che_do_render as cdr

    ban = _ban()
    ban["hinh"]["cach_render"] = cdr.CAT_MA_HOA_LAI
    ban["hinh"]["bo_ma_hoa"] = "libx264"
    ban["hinh"]["khoang_giu"] = [[0.0, 5.0], [10.0, 20.0]]
    cmd = _lenh(ban)
    assert "libx264" in cmd
    assert "-filter_complex" in cmd
    # Khoang duoc giu phai xuat hien DUNG THU TU trong bieu thuc cat-noi.
    loc = cmd[cmd.index("-filter_complex") + 1]
    assert loc.index("start=0.000000") < loc.index("start=10.000000")
    assert "concat=n=2" in loc
    assert "copy" not in cmd


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


# 🔴 **Bon phep kiem tron tieng da chuyen sang `test_442`** cung voi ham ma
#    chung canh giu. Pha 17 go `_loc_am` khoi trinh render: pha 16 da dung mot
#    ban phoi hoan chinh, va giu ca hai la chuan hoa am luong hai lan.
#
# ⭐ Chung KHONG bi xoa. Moi bai hoc trong so do da tra gia mot lan
#    (`normalize=0`, `all=1`, `aformat` tung dau vao, `dual_mono`), va chung di
#    theo doi tuong chung bao ve chu khong theo tep chung tinh co nam trong.


def test_so_tep_lech_so_lop_bi_TU_CHOI():
    """Lech thu tu/so luong khong lam ffmpeg hong — no chi dat sai cau vao sai
    cho. Mot loi im lang phai bi bat o day."""
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat.dung_lenh(_ban(so_lop=2), ffmpeg_bin="ffmpeg",
                           duong_video="/t/v.mp4", duong_master="/t/n.wav",
                           duong_lop=["/t/s0.wav"], duong_ra="/t/o.mp4")


def test_khong_lop_tieng_nao_van_ra_lenh_hop_le():
    """Moi doan bi cat o TIMING la mot ket cuc hop le, khong phai mot loi."""
    cmd = _lenh(_ban(so_lop=0))
    # ⚠️ Tu pha 17 tieng LUON den tu ban phoi (`-map 1:a:0`), ke ca khi con lop
    #    nao. `-filter_complex` chi con xuat hien o preset CAT (cat-noi hinh).
    assert "1:a:0" in cmd
    assert "-filter_complex" not in cmd


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


def test_renderer_KHONG_TU_GIANH_GPU_ma_chi_dung_suat_da_duoc_cap():
    """🔴 **Chot nay tung cam ca `gpu_env`, va lenh cam do chinh la B24-01.**

    Cau chu cu: *"`-c:v copy` khong cham bo ma hoa. Xin mot suat GPU la giu mot
    thu khan hiem de khong dung toi."* Dung — cho preset `preserve`. Preset
    `smart_localize` **buoc phai ma hoa lai** (cat bang stream copy chi cat duoc
    tai keyframe; do that cho GOP 8,333 giay), nen tu pha 12 tro di menh de do
    het dung, va khong ai quay lai doc lai chot nay.

    ⛔ Hau qua: `gpu_env` bi cam, nen ffmpeg khong bao gio duoc ghim vao card
       duoc cap, nen bo ma hoa phan cung khong bao gio duoc dung — mot chot da
       **bao ve chinh khiem khuyet no duoc viet ra de tranh**.

    ⭐ Dieu can bao ve khong phai "dung cham GPU", ma la **khong TU GIANH**:
       nen tang cap card qua `ctx.gpu_uuid`, va handler chi duoc dung cai da
       duoc cap. Hai handler tu do card roi tu quyet la kich ban OOM ma
       `gpu_lease` sinh ra de chan — va `gpu_env` la thu THI HANH viec do, chu
       khong pha no.
    """
    # Tu giu cho, tu liet card, tu do bo ma hoa cua may: tat ca deu la tu quyet.
    tu_gianh = ("gpu_lease", "list_gpus", "detect_gpu_encoder", "gpu_arbiter")
    for mod in (ket_xuat, giai_doan_ket_xuat):
        assert _vi_pham(inspect.getsource(mod), tu_gianh) == [], (
            f"{mod.__name__} tu gianh GPU thay vi dung suat nen tang cap")


def test_renderer_GHIM_ffmpeg_vao_dung_card_duoc_cap():
    """Mat con lai cua chot tren: duoc cap card ma khong ghim thi van la dam nhau.

    `JobContext.gpu_env` ton tai dung cho viec nay va docstring cua no ke ten
    ffmpeg. Mot lan render duoc cap card **1** ma chay `h264_nvenc` tren card
    **0** thi nen tang giu cho mot dang con thuc te mot neo.
    """
    van = inspect.getsource(giai_doan_ket_xuat)
    assert "gpu_env()" in van, (
        "RENDER khong ghim tien trinh ffmpeg vao card duoc cap")


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
                             duong_master=str(nen),
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
                             duong_master=str(nen), duong_lop=[], duong_ra=str(ra))
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
