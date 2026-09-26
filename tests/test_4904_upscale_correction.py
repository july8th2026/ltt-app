"""Khoa cac sua sai H32 cho upscalevideo (ISSUE A,C,D,E,F,G,H,I,J).

Nguon: docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md (tep:dong cho tung claim).
Moi ham la MOT bat bien; docstring noi RO neu ai lam hong thi hong CAI GI.
Khong cham GPU/ffmpeg that: moi subprocess deu bi monkeypatch.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _tree(relative: str) -> ast.Module:
    return ast.parse(_read(relative), filename=relative)


# ---------------------------------------------------------------------------
# A. Hop dong encoder (ISSUE I) — bat bien producer -> consumer
# ---------------------------------------------------------------------------

def _khong_co_hevc_phan_cung(monkeypatch) -> None:
    """Gia lap may KHONG co `hevc_nvenc` chay duoc, va chan moi phep do that.

    `jobs.co_hevc_phan_cung` cache theo tien trinh, nen phai xoa cache TRUOC va
    ep ca `media._test_encoder` nem AssertionError neu bi goi — de test khong bao
    gio sinh mot tien trinh ffmpeg nao (may nay dang chay job khach tren GPU)."""
    from apps.upscalevideo import jobs
    from platform_core import media

    def _khong_duoc_do(*a, **k):
        raise AssertionError("test khong duoc goi _test_encoder that")
    monkeypatch.setattr(media, "_test_encoder", _khong_duoc_do)
    monkeypatch.setattr(jobs, "_hevc_phan_cung", False)


def _co_hevc_phan_cung(monkeypatch) -> None:
    from apps.upscalevideo import jobs
    from platform_core import media

    def _khong_duoc_do(*a, **k):
        raise AssertionError("test khong duoc goi _test_encoder that")
    monkeypatch.setattr(media, "_test_encoder", _khong_duoc_do)
    monkeypatch.setattr(jobs, "_hevc_phan_cung", True)


def test_resolve_encoder_luon_tra_ten_ma_venc_args_hieu(monkeypatch):
    """Voi MOI Codec x MOI gia tri detect_gpu_encoder() co the tra, ten ma
    jobs._resolve_encoder tra ve phai duoc ff._venc_args hieu KHONG nem loi
    (hoac chinh no NEM `CodecKhongPhucVuDuoc` — mot tu choi RO RANG khong pha
    bat bien nay). Day dung la bat bien bi vi pham o ISSUE I (QSV/AMF roi am
    tham ve libx264 ma _resolve_encoder tung khai la no "ho tro")."""
    from apps.upscalevideo import ff, jobs
    from platform_core import media
    from apps.upscalevideo.schemas import Codec

    for co_hevc in (False, True):
        (_co_hevc_phan_cung if co_hevc else _khong_co_hevc_phan_cung)(monkeypatch)
        for gpu_return in ("", "h264_nvenc", "h264_qsv", "h264_amf"):
            monkeypatch.setattr(media, "detect_gpu_encoder", lambda _v=gpu_return: _v)
            for codec in Codec:
                try:
                    encoder = jobs._resolve_encoder(codec)
                except jobs.CodecKhongPhucVuDuoc:
                    continue
                ff._venc_args(encoder)  # khong duoc nem


def test_co_hevc_phan_cung_DO_hevc_nvenc_chu_khong_suy_tu_h264(monkeypatch):
    """FIX 1. `jobs.co_hevc_phan_cung()` phai DO `hevc_nvenc` bang
    `media._test_encoder("hevc_nvenc")`, ⛔ khong duoc suy ra tu
    `detect_gpu_encoder()` (ham do CHI thu `h264_nvenc`/`h264_qsv`/`h264_amf` —
    khong mot `hevc_*` nao, xem `platform_core/media.py`).

    Bang chung phep kiem nay bat duoc hoi quy: ta dat `detect_gpu_encoder` tra
    `h264_nvenc` (tuc suy luan cu se noi "co HEVC") NHUNG cho `_test_encoder`
    tra False cho `hevc_nvenc` — mot ban suy-tu-h264 se tra True o day."""
    from apps.upscalevideo import jobs
    from platform_core import media

    monkeypatch.setattr(media, "detect_gpu_encoder", lambda: "h264_nvenc")
    da_do: list[str] = []

    def _do_gia(enc):
        da_do.append(enc)
        return False
    monkeypatch.setattr(media, "_test_encoder", _do_gia)
    monkeypatch.setattr(jobs, "_hevc_phan_cung", None)      # xoa cache

    assert jobs.co_hevc_phan_cung() is False
    assert "hevc_nvenc" in da_do, da_do

    # Cache theo tien trinh: lan hai KHONG duoc do lai (mot encode thu la mot
    # tien trinh ffmpeg; day la may production).
    assert jobs.co_hevc_phan_cung() is False
    assert da_do == ["hevc_nvenc"]


def test_venc_args_nem_valueerror_cho_encoder_la():
    """`ff._venc_args` phai NEM cho encoder no khong biet — roi am tham ve
    libx264 (khong nem gi ca) chinh la thu lam hop dong codec noi doi (ISSUE I)."""
    from apps.upscalevideo import ff

    for encoder_la in ("h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf", "hevc_vaapi"):
        with pytest.raises(ValueError):
            ff._venc_args(encoder_la)


def test_venc_args_dung_ho_codec_cho_moi_ten_duoc_chap_nhan():
    """`-c:v` phat ra tu `_venc_args` phai dung HO codec (h264/hevc) theo
    `quality_gate.HO_CODEC` cho moi ten ma `_resolve_encoder` co the tra —
    lech o day nghia la khach xin HEVC nhan H.264 ma khong ai biet (ISSUE J)."""
    from apps.upscalevideo import ff
    from apps.upscalevideo.quality_gate import HO_CODEC

    ten_hop_le = ("h264_nvenc", "hevc_nvenc", "libx264", "libx265")
    ho_mong_doi = {"h264_nvenc": "h264", "hevc_nvenc": "hevc",
                   "libx264": "h264", "libx265": "hevc"}
    for ten in ten_hop_le:
        args = ff._venc_args(ten)
        i = args.index("-c:v")
        assert args[i + 1] == ten
        assert HO_CODEC[ten] == ho_mong_doi[ten]


# ---------------------------------------------------------------------------
# B. Ngu nghia HEVC (ISSUE J)
# ---------------------------------------------------------------------------

def test_hevc_co_phan_cung_thi_dung_hevc_nvenc(monkeypatch):
    """FIX 1 nhanh (2): co `hevc_nvenc` chay duoc -> phai dung no, khong tut ve
    CPU. `detect_gpu_encoder` tra "" (tuc dong h264 khong co NVENC) KHONG duoc
    chan duong HEVC phan cung: hai phep do doc lap."""
    from apps.upscalevideo import ff, jobs
    from platform_core import media
    from apps.upscalevideo.schemas import Codec

    _co_hevc_phan_cung(monkeypatch)
    monkeypatch.setattr(media, "detect_gpu_encoder", lambda: "")

    encoder = jobs._resolve_encoder(Codec.hevc)
    assert encoder == "hevc_nvenc"
    args = ff._venc_args(encoder)
    assert args[args.index("-c:v") + 1] == "hevc_nvenc"


@pytest.mark.parametrize("gpu_return", ["", "h264_nvenc", "h264_qsv", "h264_amf"])
def test_hevc_khong_phan_cung_phai_NEM_khong_duoc_libx265_cung_khong_duoc_h264(
        monkeypatch, gpu_return):
    """⭐ FIX 1 (BLOCKER). Xin HEVC + khong co HEVC phan cung -> `_resolve_encoder`
    PHAI nem `CodecKhongPhucVuDuoc`, voi mot cau noi ro khach phai lam gi.

    Hai duong lui deu bi khoa o day, va ca hai deu TUNG duoc cai vao:
    - tra `"libx264"` (ban dau) = giao H.264 ma khai HEVC (ISSUE J, mandate §17);
    - tra `"libx265"` (ban sua dau) = `-preset medium` 2160p hang GIO CPU, roi
      `job_runner` `os._exit(3)` o `RUNTIME_LIMIT_S` bo qua `finally` => ro thu
      muc tam co GB + engine/ffmpeg mo coi giu GPU (ISSUE L).
    Chay phep kiem nay tren ma TRUOC khi sua: no do o `pytest.raises` vi ham tra
    ve "libx265" chu khong nem gi."""
    from apps.upscalevideo import jobs
    from platform_core import media
    from apps.upscalevideo.schemas import Codec

    _khong_co_hevc_phan_cung(monkeypatch)
    monkeypatch.setattr(media, "detect_gpu_encoder", lambda: gpu_return)

    with pytest.raises(jobs.CodecKhongPhucVuDuoc) as e:
        jobs._resolve_encoder(Codec.hevc)

    loi = str(e.value).lower()
    assert "hevc" in loi or "h.265" in loi
    assert "h.264" in loi or "h264" in loi          # phai NOI khach chon gi


def test_h264_giu_nguyen_hanh_vi_nvenc_hoac_libx264(monkeypatch):
    """FIX 1 nhanh (4): H.264 KHONG doi — NVENC neu co, khong thi `libx264`.
    ⛔ Va duong H.264 khong duoc goi phep do HEVC (`_test_encoder` o day se nem
    neu bi goi): mot job H.264 khong phai tra gia cho mot encode thu HEVC."""
    from apps.upscalevideo import jobs
    from platform_core import media
    from apps.upscalevideo.schemas import Codec

    _khong_co_hevc_phan_cung(monkeypatch)
    monkeypatch.setattr(jobs, "_hevc_phan_cung", None)   # chua do -> se nem neu goi

    monkeypatch.setattr(media, "detect_gpu_encoder", lambda: "h264_nvenc")
    assert jobs._resolve_encoder(Codec.h264) == "h264_nvenc"
    for gpu_return in ("", "h264_qsv", "h264_amf"):
        monkeypatch.setattr(media, "detect_gpu_encoder", lambda _v=gpu_return: _v)
        assert jobs._resolve_encoder(Codec.h264) == "libx264"


def test_libx265_van_duoc_ff_ho_tro_cho_duong_ngoai_tuyen():
    """FIX 1 nhanh (5): `_resolve_encoder` khong con dinh tuyen job khach vao
    `libx265`, NHUNG `ff._venc_args` phai VAN hieu no — no chay that (do
    26/09) va duong benchmark/ngoai tuyen co quyen xin no."""
    from apps.upscalevideo import ff
    from apps.upscalevideo.quality_gate import HO_CODEC

    args = ff._venc_args("libx265")
    assert args[args.index("-c:v") + 1] == "libx265"
    assert HO_CODEC["libx265"] == "hevc"


def test_qsv_amf_bi_bo_khoi_schemas_va_ho_codec():
    """QSV/AMF: `ffmpeg -encoders` LIET KE ca bon, ca bon CHET luc chay tren may
    nay (do 26/09) => `schemas` khong duoc con `ENCODER_QSV`/`ENCODER_AMD` (khong
    caller nao trong kho), va `HO_CODEC` khong duoc liet ke chung nhu the app co
    the sinh ra chung. Mot ban LIET KE nang luc khong phai mot phep DO nang luc."""
    from apps.upscalevideo import schemas
    from apps.upscalevideo.quality_gate import HO_CODEC

    assert not hasattr(schemas, "ENCODER_QSV")
    assert not hasattr(schemas, "ENCODER_AMD")
    for ten in HO_CODEC:
        assert "_qsv" not in ten and "_amf" not in ten, ten


def test_ho_codec_khong_co_lo_hong_cho_moi_gia_tri_resolve_encoder_co_the_tra():
    """`quality_gate.HO_CODEC` phai anh xa MOI gia tri ma `_resolve_encoder` co
    the tra ve toi mot ho codec — thieu mot lo la cong chat luong (ISSUE H, muc
    4) khong nhan ra sai lech va im lang bo qua no."""
    from apps.upscalevideo.schemas import ENCODER, ENCODER_CPU
    from apps.upscalevideo.quality_gate import HO_CODEC

    gia_tri_co_the = set(ENCODER.values()) | set(ENCODER_CPU.values())
    for ten in gia_tri_co_the:
        assert HO_CODEC.get(ten) is not None, ten


# ---------------------------------------------------------------------------
# C. Su that dong thoi GPU (ISSUE A)
# ---------------------------------------------------------------------------

def test_gpu_lease_unique_constraint_khoa_dong_thoi_ve_mot():
    """`GpuLease.__table_args__` phai co `UniqueConstraint` tren DUNG
    ("host","gpu_uuid") — day la thu duy nhat lam dong thoi GPU that = 1
    (ISSUE A). Ai bo rang buoc nay thi PHAI bo luon moi loi khai "N job dong
    thoi" o manifest/docs — khong the giu ca hai."""
    from sqlalchemy import UniqueConstraint
    from platform_core.models import GpuLease

    unique_constraints = [c for c in GpuLease.__table_args__
                          if isinstance(c, UniqueConstraint)]
    assert len(unique_constraints) == 1
    columns = {col.name for col in unique_constraints[0].columns}
    assert columns == {"host", "gpu_uuid"}


# Cac chuoi noi dong thoi gia (ISSUE A) da bi CURRENT_TRUTH.md ghi nhan la
# LOI KHAI SAI trong 9 vi tri o docs/UPSCALE_V2/ (bao cao kiem toan CU, chua
# duoc sua/luu tru — chinh CURRENT_TRUTH.md liet ke tung tep:dong). Quet lai
# nguyen 9 cho do o day se do lai dung cai da duoc ghi nhan la SAI ma khong
# ai so huu de sua trong pham vi mot tep test — thay vao do, khoa noi RUI RO
# THAT: ai do sua `manifest.py` (nguon dang song) hoac xoa phan "SAI/⛔" khoi
# `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` (ban ghi sua sai chinh
# thuc) ma van giu con so dong thoi gia.
_MAU_DONG_THOI_GIA = [
    re.compile(r"4\s*→\s*12"), re.compile(r"4->12"),
    re.compile(r"\b(8|10|12)\s+concurrent"),
    re.compile(r"tripling"), re.compile(r"3x throughput"),
]
_DAU_HIEU_DA_DEBUNK = ("⛔", "sai", "false", "issue a", "bản cũ", "not 12")


def _vi_pham_theo_doan(text: str) -> list[str]:
    """Chia `text` thanh cac DOAN theo heading Markdown `## ` (khong co heading
    nao -> ca tep la mot doan). Mot dong khop mau dong-thoi-gia CHI la vi pham
    neu CA DOAN chua no khong mang dau hieu debunk nao — vi mot cau trich dan
    dai (nhu o CURRENT_TRUTH.md) co the bi xuong dong giua chung khi Markdown
    ngat dong, nen dau hieu debunk (vd. tieu de "## ISSUE A ... SAI") thuong
    dung truoc do vai dong chu khong nam chung dong voi tu khoa bi trich."""
    lines = text.splitlines()
    chi_so_heading = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not chi_so_heading:
        doan_list = [(0, len(lines))]
    else:
        doan_list = []
        if chi_so_heading[0] > 0:
            doan_list.append((0, chi_so_heading[0]))
        bien = chi_so_heading + [len(lines)]
        for start, end in zip(chi_so_heading, bien[1:], strict=True):
            doan_list.append((start, end))

    vi_pham = []
    for start, end in doan_list:
        doan_text = "\n".join(lines[start:end]).lower()
        if any(dh in doan_text for dh in _DAU_HIEU_DA_DEBUNK):
            continue
        for ln in lines[start:end]:
            if any(m.search(ln) for m in _MAU_DONG_THOI_GIA):
                vi_pham.append(ln)
    return vi_pham


def test_doc_truth_gate_manifest_va_ban_sua_khong_khai_dong_thoi_gia():
    """Cong chan chan LOI KHAI dong thoi GPU gia (ISSUE A) o hai noi CON SONG:
    `apps/upscalevideo/manifest.py` (nguon dang duoc doc de tinh gpu_vram_mb)
    va `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` (ban ghi sua sai
    chinh thuc). Quy tac (don gian, xem `_vi_pham_theo_doan`): chia tep thanh
    doan theo heading `## `; mot khop voi 1-trong-5 mau dong thoi gia chi la
    vi pham neu CA DOAN chua no khong co dau hieu da debunk (⛔/SAI/false/
    ISSUE A/Ban cu/"not 12", khong phan biet hoa-thuong) o BAT KY dau trong
    doan — khong chi cung mot dong (trich dan dai co the xuong dong giua tu
    khoa va dau hieu debunk nam o cau dan phia truoc).

    ⚠️ Pham vi CO Y khong bao gom `docs/UPSCALE_V2/*.md` (bao cao kiem toan
    CU): CURRENT_TRUTH.md da liet ke 9 vi tri sai trong do la LOI KHAI CU
    chua duoc don/luu tru, khong phai mot regression tu ban sua nay — quet
    lai chung o day se do FAIL vinh vien cho toi khi ai do don docs, khong
    lien quan gi den viec khoa ban sua H32.6. Da chay va xac nhan XANH tren
    cay hien tai voi pham vi nay (26/09)."""
    for rel in ("apps/upscalevideo/manifest.py",
               "docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md"):
        vi_pham = _vi_pham_theo_doan(_read(rel))
        assert not vi_pham, f"{rel}: {vi_pham}"


# ---------------------------------------------------------------------------
# D. Quality gate (ISSUE H)
# ---------------------------------------------------------------------------

_TU_CAM = frozenset({"pil", "image", "psnr", "ssim", "vmaf", "libvmaf"})
_TACH_TU = re.compile(r"[^A-Za-z0-9]+")


def _tu_cam_trong(muc: str) -> str | None:
    """Tra TU CAM dau tien trong `muc`, hoac None.

    ⭐ FIX 7. Khong dung `in` (substring) va cung khong dung `\\b` cua regex:
    - `in` do oan tren `compile`/`compiled`/`pile`/`pipeline` (chua "pil");
    - `\\b` BO SOT `psnr_score`, vi `_` la ky tu tu (word char) nen khong co bien
      tu giua `psnr` va `_score` — da do that o luot dau, 26/09.
    Nay: CAT `muc` thanh token theo moi ky tu khong-chu-khong-so (ke ca `_` va
    `.`), roi so SANH BANG voi tap tu cam. Chinh xac ca hai chieu."""
    for tu in _TACH_TU.split(muc):
        if tu and tu.lower() in _TU_CAM:
            return tu
    return None


def _dinh_danh_va_chuoi(tree: ast.Module) -> list[str]:
    """Moi TEN DINH DANH + moi CHUOI khong-phai-docstring trong `tree`.

    ⭐ FIX 7. Ban truoc quet bang `"pil" not in source.lower()` — mot phep kiem
    SUBSTRING tho. No se do oan tren bat ky `compile`, `compiled`, `pile`,
    `pillar`… ma khong ai lien quan den PIL, tuc mot bai min cho nguoi sua sau.
    Nay: doc AST, lay dung TEN (import / Name / Attribute / arg / def / class) va
    cac chuoi hang, roi so khop bang TOKEN (`_tu_cam_trong`). Docstring bi loai vi
    module docstring CO QUYEN nhac psnr/ssim/vmaf de giai thich loi cu (ISSUE H).
    """
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and node.body:
            dau = node.body[0]
            if (isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Constant)
                    and isinstance(dau.value.value, str)):
                docstring_ids.add(id(dau.value))

    ten: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            ten += [a.name for a in node.names] + [a.asname or "" for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            ten.append(node.module or "")
            ten += [a.name for a in node.names]
        elif isinstance(node, ast.Name):
            ten.append(node.id)
        elif isinstance(node, ast.Attribute):
            ten.append(node.attr)
        elif isinstance(node, ast.arg):
            ten.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ten.append(node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            ten.append(node.arg)
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstring_ids):
            ten.append(node.value)
    return [t for t in ten if t]


def test_quality_gate_khong_con_psnr_ssim_vmaf_pil_trong_ma_thuc_thi():
    """`quality_gate.py` KHONG duoc dung PIL/Image/psnr/ssim/vmaf trong ma THUC
    THI (ISSUE H). Kiem bang AST + bien tu, khong bang `in` tho — xem
    `_dinh_danh_va_chuoi`. Docstring module duoc phep nhac chung."""
    tree = _tree("apps/upscalevideo/quality_gate.py")
    for muc in _dinh_danh_va_chuoi(tree):
        khop = _tu_cam_trong(muc)
        assert khop is None, f"{muc!r} chua tu cam {khop!r}"


def test_phep_kiem_tu_cam_khong_do_oan_va_khong_bo_sot():
    """Doi-chung HAI CHIEU cho FIX 7 — khong co no thi "phep kiem da chinh xac"
    chi la mot cau noi:

    - phai IM voi `compile`/`compiled`/`pile`/`pipeline`/`compilation` (phep kiem
      SUBSTRING cu do o day);
    - phai DO voi `PIL`, `Image`, `psnr_score`, `obj.vmaf`, `"libvmaf"`
      (phep kiem `\\b` regex BO SOT `psnr_score`, vi `_` la word char)."""
    an_toan = ("import functools\nx = compile('1', '<s>', 'eval')\n"
               "pile = 1\np = 'pipeline'\ncompiled_re = 2\ns = 'compilation'\n")
    for muc in _dinh_danh_va_chuoi(ast.parse(an_toan)):
        assert _tu_cam_trong(muc) is None, muc

    for xau in ("from PIL import Image\n", "y = psnr_score\n",
                "z = obj.vmaf\n", "w = 'libvmaf'\n", "v = ssim_map(a)\n",
                "u = '-lavfi psnr'\n"):
        assert any(_tu_cam_trong(m) for m in _dinh_danh_va_chuoi(ast.parse(xau))), xau


def test_kiem_tra_dau_ra_tep_khong_ton_tai():
    """Duong dan khong ton tai -> `ok=False` va `loi` khac rong — khong duoc
    de mot ngoai le tho thoat ra (cong tu sap khong duoc lam do mot job tot,
    nhung o day chinh no la ca hu hong that)."""
    from apps.upscalevideo.quality_gate import kiem_tra_dau_ra

    ket = kiem_tra_dau_ra("/khong/ton/tai/dau_ra.mp4", target_h=1080, src_w=1920, src_h=1080,
                          expect_encoder="libx264", expect_audio=False,
                          expect_duration_s=10.0)
    assert ket["ok"] is False
    assert ket["loi"]


def test_kiem_tra_dau_ra_tep_qua_nho_khong_goi_ffprobe(tmp_path, monkeypatch):
    """Tep < `MIN_BYTES` (10 KB) -> `ok=False`, ly do nhac kich thuoc, VA
    KHONG BAO GIO goi `ff.probe_video` — ham phai tra som truoc buoc do
    (kiem bang cach lam `probe_video` nem neu bi goi)."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    def _khong_duoc_goi(*a, **k):
        raise AssertionError("khong duoc goi ffprobe cho tep qua nho")
    monkeypatch.setattr(ff, "probe_video", _khong_duoc_goi)

    tep = tmp_path / "qua_nho.mp4"
    tep.write_bytes(b"x" * 100)
    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=False,
                             expect_duration_s=10.0)
    assert ket["ok"] is False
    assert any("100" in loi or "B" in loi for loi in ket["loi"])


def test_kiem_tra_dau_ra_bat_lech_codec_khi_hevc_roi_ve_h264(tmp_path, monkeypatch):
    """Runtime catch cho ISSUE J: xin `expect_encoder="libx265"` (HEVC) nhung
    dau ra that la `h264` -> phai co trong `loi` (khong phai canh_bao) — day
    la luoi cuoi cung khi encoder that sai voi hop dong."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    def _probe_gia(*a, **k):
        return {"w": 1920, "h": 1080, "duration": 10.0, "vcodec": "h264",
               "has_audio": True, "fps": 30.0, "fps_str": "30/1",
               "nb_frames": 300, "is_vfr": False, "rotation": 0}
    monkeypatch.setattr(ff, "probe_video", _probe_gia)

    tep = tmp_path / "dau_ra.mp4"
    tep.write_bytes(b"x" * 20000)
    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx265", expect_audio=True,
                             expect_duration_s=10.0)
    assert ket["ok"] is False
    assert any("codec" in loi.lower() for loi in ket["loi"])


def test_kiem_tra_dau_ra_thieu_audio_chi_la_canh_bao_khong_danh_do(tmp_path, monkeypatch):
    """Codec dung nhung khach doi tieng ma dau ra khong co -> `ok=True`,
    `canh_bao` khac rong. Mot lech MEM khong duoc lam do mot job cua khach
    (khac voi lech codec — do la loi that o test tren)."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    def _probe_gia(*a, **k):
        return {"w": 1920, "h": 1080, "duration": 10.0, "vcodec": "h264",
               "has_audio": False, "fps": 30.0, "fps_str": "30/1",
               "nb_frames": 300, "is_vfr": False, "rotation": 0}
    monkeypatch.setattr(ff, "probe_video", _probe_gia)

    tep = tmp_path / "dau_ra.mp4"
    tep.write_bytes(b"x" * 20000)
    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=True,
                             expect_duration_s=10.0)
    assert ket["ok"] is True
    assert ket["canh_bao"]


def _probe_gia_factory(**ghi_de):
    goc = {"w": 1920, "h": 1080, "duration": 10.0, "vcodec": "h264",
           "has_audio": True, "fps": 30.0, "fps_str": "30/1",
           "nb_frames": 300, "is_vfr": False, "rotation": 0}
    goc.update(ghi_de)

    def _probe(*a, **k):
        return dict(goc)
    return _probe


def test_cong_KHONG_nhan_expect_w_expect_h_nua():
    """⭐ FIX 2. Chu ky `kiem_tra_dau_ra` khong duoc con `expect_w`/`expect_h`.

    Do KHONG phai chuyen dat ten: `jobs.handle` lay hai so do tu
    `ff.encode_full`/`concat_and_mux`, ma hai ham ay `probe_video(out_path)` —
    tuc cong so tep voi CHINH NO va KHONG BAO GIO do duoc (ISSUE M con mo trong
    khi ma khai la dong). Cach duy nhat de bat bien nay khong tai dien la lam
    cho cong KHONG THE nhan mot so do tu dau ra: no phai nhan `target_h` (khach
    xin) + `src_w`/`src_h` (probe NGUON)."""
    import inspect
    from apps.upscalevideo.quality_gate import kiem_tra_dau_ra

    tham_so = set(inspect.signature(kiem_tra_dau_ra).parameters)
    assert "expect_w" not in tham_so and "expect_h" not in tham_so
    assert {"target_h", "src_w", "src_h"} <= tham_so


def test_cong_DO_khi_chieu_cao_khac_target_h(tmp_path, monkeypatch):
    """FIX 2: hua 2160p ma dau ra 1080p -> `loi`. Tren ma TRUOC khi sua phep
    kiem nay khong the do duoc: caller truyen `expect_h` = chinh chieu cao vua
    probe tu dau ra, nen hai ve luon bang nhau."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    monkeypatch.setattr(ff, "probe_video", _probe_gia_factory(w=1920, h=1080))
    tep = tmp_path / "dau_ra.mp4"; tep.write_bytes(b"x" * 20000)

    ket = qg.kiem_tra_dau_ra(str(tep), target_h=2160, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=True,
                             expect_duration_s=10.0)
    assert ket["ok"] is False
    assert any("cao" in loi for loi in ket["loi"]), ket["loi"]


def test_cong_DO_khi_ti_le_khung_bi_pha(tmp_path, monkeypatch):
    """FIX 2: nguon 16:9 hua o 1080p phai cho ~1920 px rong; dau ra 1440 px
    (4:3) la ti le da bi pha -> `loi`."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    monkeypatch.setattr(ff, "probe_video", _probe_gia_factory(w=1440, h=1080))
    tep = tmp_path / "dau_ra.mp4"; tep.write_bytes(b"x" * 20000)

    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=True,
                             expect_duration_s=10.0)
    assert ket["ok"] is False
    assert any("tỉ lệ" in loi for loi in ket["loi"]), ket["loi"]


@pytest.mark.parametrize("rong_that", [1918, 1919, 1920, 1921, 1922])
def test_cong_XANH_trong_dung_sai_2px_cua_scale_am_2(tmp_path, monkeypatch, rong_that):
    """FIX 2, mat con lai: `scale=-2:H` lam tron chieu rong ve so CHAN (yeu cau
    cua yuv420p), nen doi khop CHINH XAC se danh do nhung job hoan toan dung.
    Nguon 1920x1080 o 1080p hua ~1920 px; 1918..1922 phai XANH.

    ⚠️ Day la mat DOI LAP cua hai phep kiem tren: mot phep kiem chi co ich khi no
    do dung cho SAI va khong do cho ca DUNG."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    monkeypatch.setattr(ff, "probe_video",
                        _probe_gia_factory(w=rong_that, h=1080))
    tep = tmp_path / "dau_ra.mp4"; tep.write_bytes(b"x" * 20000)

    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=True,
                             expect_duration_s=10.0)
    assert ket["ok"] is True, ket["loi"]
    assert qg.DUNG_SAI_KHUNG_PX == 2


def test_cong_bo_qua_phep_thoi_luong_khi_caller_khai_khong_doan_duoc(tmp_path,
                                                                     monkeypatch):
    """`expect_duration_s <= 0` = caller noi "khong du doan duoc" -> cong BO QUA
    phep thoi luong (khong canh bao, khong doan). Doi lap voi viec im lang so
    voi mot con so sai (FIX 5)."""
    from apps.upscalevideo import ff
    from apps.upscalevideo import quality_gate as qg

    monkeypatch.setattr(ff, "probe_video", _probe_gia_factory(duration=265.0))
    tep = tmp_path / "dau_ra.mp4"; tep.write_bytes(b"x" * 20000)

    ket = qg.kiem_tra_dau_ra(str(tep), target_h=1080, src_w=1920, src_h=1080,
                             expect_encoder="libx264", expect_audio=True,
                             expect_duration_s=0.0)
    assert ket["ok"] is True
    assert not ket["canh_bao"], ket["canh_bao"]
    assert "lech_thoi_luong_s" not in ket["do"]


def test_bat_cong_ton_trong_bien_moi_truong_va_mac_dinh_bat(monkeypatch):
    """`bat_cong()` phai tra False khi `LTT_UPSCALE_TECH_GATE=0`, va True
    khi bien khong duoc dat (mac dinh BAT — day la luoi duy nhat, tat am
    tham la mat luoi ma khong ai biet)."""
    from apps.upscalevideo import quality_gate as qg

    monkeypatch.setenv("LTT_UPSCALE_TECH_GATE", "0")
    assert qg.bat_cong() is False

    monkeypatch.delenv("LTT_UPSCALE_TECH_GATE", raising=False)
    assert qg.bat_cong() is True


# ---------------------------------------------------------------------------
# E. Checkpoint KHONG phai resume (ISSUE G)
# ---------------------------------------------------------------------------

def _ten_ham_goi(tree: ast.AST) -> list[str]:
    ten = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            ten.append(node.func.attr)
    return ten


def test_jobs_khong_he_goi_duong_doc_checkpoint():
    """`load_checkpoint`/`get_job_checkpoints` KHONG duoc co caller nao trong
    `jobs.py` (parse bang ast) — do la bat bien "khong co duong resume that"
    (ISSUE G). Ai them mot duong doc o day ma CHUA co dau tay (tham so +
    model + phien ban pipeline) thi se giao nham video cu cho khach."""
    goi = _ten_ham_goi(_tree("apps/upscalevideo/jobs.py"))
    assert "load_checkpoint" not in goi
    assert "get_job_checkpoints" not in goi


def test_jobs_co_goi_cleanup_don_rac_checkpoint():
    """`jobs.py` PHAI goi `checkpoint.cleanup_job_checkpoints` (ast) — day la
    vet sua ro ri: ban cu khai ham nay nhung khong ai goi, so tien do cua moi
    job xong/loi/sap nam lai vinh vien (ISSUE G)."""
    goi = _ten_ham_goi(_tree("apps/upscalevideo/jobs.py"))
    assert "cleanup_job_checkpoints" in goi


def test_jobs_co_goi_SWEEPER_don_so_cu_that(monkeypatch):
    """⭐ FIX 3. `don_so_cu` phai co CALLER THAT. Truoc 26/09 no khong co mot
    caller nao trong ca kho, trong khi `jobs.py` VA `checkpoint.py` deu chu thich
    rang no la thu "hot phan `finally` bo sot" — tuc tai dien chinh khuyet diem
    ISSUE G (`cleanup_job_checkpoints` khong caller) lui mot ham, CONG mot loi
    khai sai. Kiem bang ast: `jobs.py` phai goi `don_so_cu_mot_lan`."""
    goi = _ten_ham_goi(_tree("apps/upscalevideo/jobs.py"))
    assert "don_so_cu_mot_lan" in goi, goi


def test_don_so_cu_mot_lan_chay_DUNG_MOT_LAN_moi_tien_trinh(monkeypatch):
    """FIX 3: sweeper khong duoc them do tre do duoc vao MOI job -> `_mot_lan`
    goi `don_so_cu` o lan dau va KHONG goi nua o cac lan sau."""
    from apps.upscalevideo import checkpoint as cp

    dem: list[int] = []
    monkeypatch.setattr(cp, "don_so_cu", lambda ttl_ngay=cp.TTL_NGAY:
                        (dem.append(1), 7)[1])
    monkeypatch.setattr(cp, "_DA_DON_TRONG_TIEN_TRINH", False)

    assert cp.don_so_cu_mot_lan() == 7
    assert cp.don_so_cu_mot_lan() == 0
    assert cp.don_so_cu_mot_lan() == 0
    assert len(dem) == 1


def test_don_so_cu_mot_lan_KHONG_BAO_GIO_nem_vao_job(monkeypatch):
    """FIX 3: sweeper nem = mot job tot bi do vi viec don rac. Phai nuot."""
    from apps.upscalevideo import checkpoint as cp

    def _no(ttl_ngay=cp.TTL_NGAY):
        raise OSError("o dia bien mat")
    monkeypatch.setattr(cp, "don_so_cu", _no)
    monkeypatch.setattr(cp, "_DA_DON_TRONG_TIEN_TRINH", False)

    assert cp.don_so_cu_mot_lan() == 0


def test_don_so_cu_xoa_dung_thu_muc_qua_han_giu_thu_muc_moi(tmp_path, monkeypatch):
    """`don_so_cu()`: hai thu muc job, mot cu hon TTL (mtime lui qua han) mot
    moi -> chi thu muc CU bi xoa, thu muc MOI con nguyen. Day la ham hot rac
    duy nhat cho ro ri "so tien do o lai vinh vien khi worker bi `os._exit`
    luc het gio cung" (ISSUE G/L)."""
    import time as time_mod
    from apps.upscalevideo import checkpoint as cp

    monkeypatch.setenv("LTT_UPSCALE_TEMP", str(tmp_path))

    cu_dir = tmp_path / "job-cu"; cu_dir.mkdir()
    cu_file = cu_dir / "probe_completed.json"
    cu_file.write_text("{}", encoding="utf-8")
    han_cu = time_mod.time() - (cp.TTL_NGAY + 1) * 86400
    os.utime(cu_file, (han_cu, han_cu))

    moi_dir = tmp_path / "job-moi"; moi_dir.mkdir()
    (moi_dir / "probe_completed.json").write_text("{}", encoding="utf-8")

    da_xoa = cp.don_so_cu()

    assert da_xoa == 1
    assert not cu_dir.exists()
    assert moi_dir.exists()


# ---------------------------------------------------------------------------
# F. Warmup (ISSUE D/E/F)
# ---------------------------------------------------------------------------

def test_warmup_model_truyen_g_va_env_giong_job_that(monkeypatch):
    """`_warmup_model` PHAI truyen `-g <gpu_index>` VA `env=` cho subprocess
    con — warmup khong ghim card thi tren may co iGPU Intel co the ham nong
    SAI CARD (ISSUE E), vo ich va con lam ban card khac."""
    from apps.upscalevideo import engine

    bat: dict = {}

    def _fake_run(args, **kwargs):
        bat["args"] = args
        bat["kwargs"] = kwargs
        return None
    monkeypatch.setattr(engine.subprocess, "run", _fake_run)

    engine._warmup_model("realesr-general-x4v3", gpu_index=3, env={"X": "1"})

    args = bat["args"]
    assert any(args[i:i + 2] == ["-g", "3"] for i in range(len(args) - 1))
    assert bat["kwargs"]["env"] == {"X": "1"}


def test_engine_khong_import_numpy_cv2():
    """`engine.py` KHONG duoc import numpy hay cv2 (ast Import/ImportFrom) —
    hai dependency nay chi tung ton tai de tao MOT anh xam 512x512 cho
    warmup, va `_tiny_png` (stdlib thuan struct+zlib) da lam duoc viec do
    (ISSUE F, rac dependency)."""
    tree = _tree("apps/upscalevideo/engine.py")
    modun_cam = {"numpy", "cv2"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in modun_cam, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert node.module.split(".")[0] not in modun_cam, node.module


def test_engine_khong_con_bien_model_cache_chet():
    """`engine.py` KHONG duoc con bien module-level `_model_cache` (dict chet:
    ban cu khai roi khong doc khong ghi o dau ca — ISSUE D). Kiem bang ast
    thay vi chuoi de comment nhac ten no khong lam test rot sai."""
    tree = _tree("apps/upscalevideo/engine.py")
    ten_gan = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ten_gan.add(target.id)
    assert "_model_cache" not in ten_gan


def test_engine_khoa_cache_ham_nong_la_ten_model_tran_khong_phai_fstring_tile():
    """Chon phuong an RE: gia PHU HOP hanh vi (goi duong warmup that) can mock
    ca `model_available`+`_warmup_model`+subprocess — nang hon can thiet cho
    mot bat bien tinh. Thay vao do doc AST: buoc gan duy nhat vao
    `_model_warmup_cache[...]` phai dung mot `ast.Name` tran (bien model) lam
    khoa, KHONG phai JoinedStr (f-string) chua "tile" — khoa kieu
    `f"{model}_tile{tune.tile}_j{tune.threads}"` cua ban cu gan nhu KHONG BAO
    GIO trung vi tile/threads doi theo VRAM song moi job (ISSUE D)."""
    tree = _tree("apps/upscalevideo/engine.py")
    gan_vao_cache = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "_model_warmup_cache"):
            gan_vao_cache.append(node.targets[0].slice)

    assert gan_vao_cache, "khong tim thay gan nao vao _model_warmup_cache[...]"
    for khoa in gan_vao_cache:
        assert isinstance(khoa, ast.Name), ast.dump(khoa)
        assert not isinstance(khoa, ast.JoinedStr)


# ---------------------------------------------------------------------------
# G. Hang so autotune (ISSUE C)
# ---------------------------------------------------------------------------

def test_autotune_fast_est_alloc_1000_khi_budget_du(monkeypatch):
    """Khoa `est_alloc_mb == 1000` cho Fast khi budget rong rai — ban cu co
    HAI chu thich noi "750 MB" cach dung mot dong "1000" ma no dung (ISSUE C).
    So dung hom nay: 848 MB dinh do duoc + 152 MB an toan = 1000."""
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset

    monkeypatch.setattr(autotune, "query_vram", lambda gpu_uuid="": (16311, 16311))
    ket = autotune.pick(Preset.fast, 1024, 576, reserve_mb=0)

    assert ket.est_alloc_mb == 1000
    assert ket.threads == "4:4:4"


def test_autotune_fast_tut_ve_du_phong_khi_budget_thap(monkeypatch):
    """Budget < 1000 MB -> Fast phai tut ve `tile=200, threads="2:2:2",
    est_alloc_mb=500` — duong an toan khi GPU dang chat, khong duoc nhan
    job roi khai can it hon that (ISSUE C)."""
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset

    monkeypatch.setattr(autotune, "query_vram", lambda gpu_uuid="": (16311, 500))
    ket = autotune.pick(Preset.fast, 1024, 576, reserve_mb=0)

    assert ket.tile == 200
    assert ket.threads == "2:2:2"
    assert ket.est_alloc_mb == 500


def test_autotune_quality_khong_bao_gio_khai_can_nhieu_hon_budget(monkeypatch):
    """Bat bien (khong phai mot gia tri don le): tai MOI san dai Quality,
    `est_alloc_mb` tra ve KHONG duoc VUOT budget dua vao. Ban cu nhan job o
    budget 5000 roi khai can 5095 — vuot chinh san cua no 95 MB. Sau sua, moi
    san (5095/7025/9314/10524=FAST_ALLOC+SAFETY) phai tu-nhat-quan:
    est_alloc_mb(budget=san) <= san."""
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset

    # San lay tu nguon `autotune.pick` (nhanh Quality, 26/09):
    #   >= FAST_ALLOC(10024)+SAFETY(500) = 10524 -> est 10024
    #   >= 9314 -> est 9314 | >= 7025 -> est 7025 | >= 5095 -> est 5095
    for san in (10524, 9314, 7025, 5095):
        monkeypatch.setattr(autotune, "query_vram",
                            lambda gpu_uuid="", _f=san: (16311, _f))
        ket = autotune.pick(Preset.quality, 1024, 576, reserve_mb=0)
        assert ket.est_alloc_mb <= san, (san, ket.est_alloc_mb)


@pytest.mark.parametrize("preset_ten", ["fast", "quality"])
@pytest.mark.parametrize("budget", [0, 1, 499, 500, 999, 1000, 3512, 3513,
                                    5094, 5095, 7024, 7025, 9313, 9314,
                                    10523, 10524, 16311])
def test_autotune_MOI_DAI_ke_ca_dai_DAY_noi_that_ve_budget(monkeypatch, budget,
                                                           preset_ten):
    """⭐ FIX 6. Bat bien dung cho MOI dai cua CA HAI preset, khong chi bon dai
    tren cua Quality: hoac `est_alloc_mb <= budget_mb`, hoac ket qua phai khai
    `budget_du_cho_est is False`.

    Ban truoc dat mot san cho bon dai tren nhung de HAI dai khong san:
    - Quality `else: tile, est = 256, 3513` — budget 0 van khai can 3513;
    - Fast `if budget < est_alloc: ... est_alloc = 500` — budget 0 van khai 500.
    Va phep kiem mang ten "MOI san dai" chi chay qua bon san tren, tuc TEN cua no
    rong hon PHAM VI cua no. Danh sach budget o day di qua ca hai ben cua TUNG
    nguong (san-1, san) nen khong con dai nao khong bi cham toi.

    Chay tren ma truoc khi sua: `budget=0` (ca hai preset) do o `assert` duoi."""
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset

    monkeypatch.setattr(autotune, "query_vram",
                        lambda gpu_uuid="", _f=budget: (16311, _f))
    ket = autotune.pick(Preset(preset_ten), 1024, 576, reserve_mb=0)

    assert ket.budget_mb == budget
    assert ket.est_alloc_mb > 0                    # luon la mot luong CAN that
    if ket.budget_du_cho_est:
        assert ket.est_alloc_mb <= budget, (budget, ket.est_alloc_mb)
    else:
        # Noi that: `est` la luong CAN, budget khong dai tho noi. KHONG duoc
        # "sua" bang cach ha est xuong bang budget.
        assert ket.est_alloc_mb > budget, (budget, ket.est_alloc_mb)


@pytest.mark.parametrize("preset_ten,est_day", [("fast", 500), ("quality", 3513)])
def test_autotune_dai_DAY_giu_nguyen_luong_CAN_va_bao_thieu(monkeypatch,
                                                            preset_ten, est_day):
    """FIX 6, mat doi lap: o budget 0, dai DAY phai VAN khai dung luong no CAN
    (`est_day`) va dat `budget_du_cho_est=False` — chu khong ha `est` xuong 0 de
    "thoa man" bat bien. Hai trang thai ("du budget" / "thieu budget") phai phan
    biet duoc; gop chung vao mot con so `est` la mat kha nang phan biet."""
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset

    monkeypatch.setattr(autotune, "query_vram", lambda gpu_uuid="": (16311, 0))
    ket = autotune.pick(Preset(preset_ten), 1024, 576, reserve_mb=0)

    assert ket.est_alloc_mb == est_day
    assert ket.budget_du_cho_est is False


# ---------------------------------------------------------------------------
# H. `jobs.handle` chay THAT (moi subprocess bi thay) — FIX 2/4/5
# ---------------------------------------------------------------------------

class _CtxGia:
    """`JobContext` toi thieu: du cho `_gpu_runtime` (khong gpu_uuid -> khong
    goi `platform_core.gpu`), `ctx.progress`, `ctx.is_cancelled`, `ctx.job_id`."""

    def __init__(self, job_id: str = "job-thu"):
        self.job_id = job_id
        self.gpu_uuid = ""
        self.moc: list = []

    def progress(self, pct, msg=""):
        self.moc.append((pct, msg))

    def is_cancelled(self):
        return False


def _chay_handle(monkeypatch, tmp_path, *, preview: bool, co_audio: bool,
                 thoi_luong_nguon: float = 265.0, n_frames: int = 240,
                 encode_nem: bool = False, target_h: int = 1080):
    """Chay `jobs.handle` voi MOI subprocess bi thay (KHONG ffmpeg, KHONG GPU).

    Tra `(ket_qua, ngoai_le, gate_kwargs, so_dir)`. `gate_kwargs` la dung nhung
    ky vong `jobs` truyen cho cong ky thuat — do la thu FIX 2 va FIX 5 noi ve."""
    from apps.upscalevideo import autotune, checkpoint, cost, engine, ff, jobs
    from apps.upscalevideo import quality_gate as qg
    from apps.upscalevideo.schemas import TuneResult
    import platform_core.storage as storage_mod

    so_goc = tmp_path / "so"
    monkeypatch.setenv("LTT_UPSCALE_TEMP", str(so_goc))
    nguon = tmp_path / "nguon.mp4"
    nguon.write_bytes(b"\0" * 4096)

    class _Storage:
        def __init__(self):
            self.da_put: dict = {}

        def exists(self, key):
            return False

        def open(self, key):
            return open(nguon, "rb")

        def put(self, key, stream, content_type=None):
            self.da_put[key] = len(stream.read())

    monkeypatch.setattr(storage_mod, "get_storage", _Storage)
    monkeypatch.setattr(engine, "check_engine", lambda: True)
    monkeypatch.setattr(engine, "run_upscale", lambda *a, **k: "done")
    monkeypatch.setattr(jobs, "_resolve_encoder", lambda codec: "libx264")
    monkeypatch.setattr(jobs, "_dam_bao_giu_cho", lambda *a, **k: None)
    monkeypatch.setattr(cost, "uoc_luong_credit", lambda *a, **k: 5)
    monkeypatch.setattr(ff, "probe_video", _probe_gia_factory(
        w=1920, h=1080, duration=thoi_luong_nguon, has_audio=co_audio,
        fps=30.0, fps_str="30/1", nb_frames=int(30 * thoi_luong_nguon)))
    monkeypatch.setattr(ff, "extract_frames", lambda *a, **k: n_frames)
    monkeypatch.setattr(autotune, "pick", lambda *a, **k: TuneResult(
        model="realesr-general-x4v3", tile=256, threads="4:4:4",
        est_alloc_mb=1000, free_mb=16000, budget_mb=13000, fast_path=True))

    def _encode(frames_dir, src_for_audio, out_path, *a, **k):
        if encode_nem:
            raise RuntimeError("encode hong co y")
        with open(out_path, "wb") as fh:
            fh.write(b"x" * 20000)
        return 1920, target_h
    monkeypatch.setattr(ff, "encode_full", _encode)

    gate_kwargs: dict = {}

    def _gate(out_local, **kwargs):
        gate_kwargs.update(kwargs)
        return {"ok": True, "loi": [], "canh_bao": [], "do": {"bytes": 20000}}
    monkeypatch.setattr(qg, "kiem_tra_dau_ra", _gate)
    monkeypatch.setattr(qg, "bat_cong", lambda: True)
    monkeypatch.setattr(checkpoint, "_DA_DON_TRONG_TIEN_TRINH", False)

    ctx = _CtxGia()
    params = {"video_key": "vao/x.mp4", "owner_id": "u1", "preset": "fast",
              "codec": "h264", "target_height": target_h, "preview": preview}
    ket = ngoai_le = None
    try:
        ket = jobs.handle(params, ctx)
    except Exception as e:  # noqa: BLE001 — chinh la thu ta muon soi
        ngoai_le = e
    return ket, ngoai_le, gate_kwargs, so_goc / ctx.job_id


def test_handle_truyen_LOI_HUA_cho_cong_khong_phai_so_do_tu_dau_ra(
        tmp_path, monkeypatch):
    """FIX 2 ve phia caller: `jobs.handle` phai truyen `target_h` + khung NGUON,
    KHONG truyen `expect_w`/`expect_h` lay tu `encode_full` (= probe cua chinh
    dau ra). Ma truoc khi sua truyen `expect_w=ow, expect_h=oh` -> phep kiem nay
    do ngay o `assert "expect_w" not in`."""
    _ket, ngoai_le, gate_kwargs, _so = _chay_handle(
        monkeypatch, tmp_path, preview=False, co_audio=True, target_h=1440)

    assert ngoai_le is None, ngoai_le
    assert "expect_w" not in gate_kwargs and "expect_h" not in gate_kwargs
    assert gate_kwargs["target_h"] == 1440
    assert (gate_kwargs["src_w"], gate_kwargs["src_h"]) == (1920, 1080)


def test_preview_co_tieng_KHONG_sinh_ky_vong_thoi_luong_8s(tmp_path, monkeypatch):
    """FIX 5. Preview cat KHUNG (8 s) nhung `encode_full` map audio NGUYEN VEN
    (`-map 1:a:0 -c:a copy`, khong `-t` tren input audio, khong `-shortest`), nen
    thoi luong CONTAINER = luong dai nhat = ~265 s. Ban sua dau truyen
    `expect_duration_s=eff_dur` = 8.0 -> lech 257 s > dung sai ~1 s -> MOI preview
    co tieng deu mang mot `quality_warning` gia.

    Phep kiem do lai dung con so bi sai: `expect_duration_s` phai ~265, KHONG
    duoc la 8. Chay tren ma truoc khi sua: gia tri nhan duoc la 8.0 -> do."""
    _ket, ngoai_le, gate_kwargs, _so = _chay_handle(
        monkeypatch, tmp_path, preview=True, co_audio=True,
        thoi_luong_nguon=265.0, n_frames=240)          # 240 khung @30fps = 8 s

    assert ngoai_le is None, ngoai_le
    assert gate_kwargs["expect_duration_s"] != pytest.approx(8.0)
    assert gate_kwargs["expect_duration_s"] == pytest.approx(265.0)


def test_preview_KHONG_tieng_thi_ky_vong_dung_do_dai_khung(tmp_path, monkeypatch):
    """FIX 5, mat doi lap: khong co audio de keo dai container thi ky vong phai
    la do dai phan VIDEO (`n_frames / fps_out` = 240/30 = 8 s) — khong duoc lay
    thoi luong nguon. Neu chi "bo qua phep kiem cho preview" thi mat con nay
    cung mat, va cong het nhin thay mot preview bi cat sai."""
    _ket, ngoai_le, gate_kwargs, _so = _chay_handle(
        monkeypatch, tmp_path, preview=True, co_audio=False,
        thoi_luong_nguon=265.0, n_frames=240)

    assert ngoai_le is None, ngoai_le
    assert gate_kwargs["expect_duration_s"] == pytest.approx(8.0)


def test_thoi_luong_hua_la_MAX_cua_video_va_audio():
    """FIX 5, don vi: `_thoi_luong_hua` phai la chinh ngu nghia mux — `max(video,
    audio)` khi co audio, `video` khi khong, va `0.0` (= "khong du doan duoc")
    khi thieu du lieu, de cong BO QUA thay vi doan."""
    from apps.upscalevideo.jobs import _thoi_luong_hua

    assert _thoi_luong_hua(240, "30/1", True, 265.0) == pytest.approx(265.0)
    assert _thoi_luong_hua(240, "30/1", False, 265.0) == pytest.approx(8.0)
    assert _thoi_luong_hua(7950, "30/1", True, 265.0) == pytest.approx(265.0)
    assert _thoi_luong_hua(0, "30/1", True, 265.0) == 0.0
    assert _thoi_luong_hua(240, "0/1", True, 265.0) == 0.0


def test_job_THANH_CONG_thi_so_tien_do_bi_XOA(tmp_path, monkeypatch):
    """FIX 4, nua thu nhat: job tot thi khong ai can biet no da di qua chang nao
    -> `finally` xoa so."""
    ket, ngoai_le, _gk, so_dir = _chay_handle(
        monkeypatch, tmp_path, preview=False, co_audio=True)

    assert ngoai_le is None, ngoai_le
    assert ket and ket["video_key"]
    assert not so_dir.exists()


def test_job_LOI_thi_so_tien_do_PHAI_CON(tmp_path, monkeypatch):
    """FIX 4. `checkpoint.py` ton tai de nguoi van hanh soi duoc "job chet o chang
    nao", nhung `finally` cu `rmtree` so tren MOI duong ke ca duong ngoai le —
    tu huy dung luc can dung nhat. Nay: job nem -> so CON LAI, va con dung dong
    chang cuoi da di qua (`frame_extraction_completed`).

    Chay tren ma truoc khi sua: `so_dir.exists()` la False -> do."""
    ket, ngoai_le, _gk, so_dir = _chay_handle(
        monkeypatch, tmp_path, preview=False, co_audio=True, encode_nem=True)

    assert ket is None and ngoai_le is not None
    assert so_dir.is_dir(), f"so bi xoa tren duong loi: {so_dir}"
    ten_chang = {p.stem for p in so_dir.glob("*.json")}
    assert "frame_extraction_completed" in ten_chang, ten_chang
