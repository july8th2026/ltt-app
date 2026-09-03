"""Auto Scan Video — AUDIO_PREPARE: tach giong khoi nen, tron, chuan am luong.

Giai doan GPU dau tien. Tren may nay `torch` la ban **CPU-only**
(`2.11.0+cpu`, `cuda False`), nen phep tach that chay tren CPU — do 4,3 giay cho
mot doan 3 giay stereo. Du de smoke that; **khong** du de do VRAM (xem
`TestChoBangChungNgoai`).
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import pytest

from tests import rao_chan_nang

from tests.fixtures.asv_media import require_ffmpeg


def _wav_stereo(dich: Path, *, giay: float = 2.0, hz: int = 440,
                tan_so: int = 44100) -> Path:
    from platform_core import media
    require_ffmpeg()
    dich.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency={hz}:duration={giay}",
         "-ac", "2", "-ar", str(tan_so), "-c:a", "pcm_s16le", str(dich)],
        check=True, capture_output=True)
    return dich


# ══════════════════════════════════════════════════════════════════════════════
#  Doc/ghi WAV — duong da bo `torchaudio.save`
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_ghi_wav_khong_dung_torchaudio(tmp_path):
    """🔴 Ban di san tiem mot ban va vao `torchaudio.save` de doi sang
    `soundfile`, vi `torchaudio >= 2.10` doi `torchcodec` ma DLL hong tren
    Windows (`Cut_only ver2/nerf_engine/stages/audio.py:8`).

    Ban va do **khong chay duoc o day**: `soundfile` khong duoc cai. Do that:

        torchaudio 2.11.0+cpu
        torchaudio.save -> ImportError: TorchCodec is required
        soundfile      -> KHONG CAI

    ⭐ Nen ta khong tiem ban va nao ca — doc/ghi WAV bang module `wave` cua thu
       vien chuan. Bo mot phu thuoc, mot ban va toan cuc, va ca mot lop hong chi
       xuat hien tren Windows.
    """
    import numpy as np

    from apps.auto_scan_video.demucs_runner import doc_wav, ghi_wav

    nguon = _wav_stereo(tmp_path / "a.wav")
    mang, tan_so = doc_wav(str(nguon))
    assert mang.shape[0] == 2 and tan_so == 44100
    # Nguong 0,01 chu khong phai 0,1: `sine` cua ffmpeg ra khoang -21 dBFS
    # (bien do ~0,088 — khop voi phep do loudnorm -21,75 LUFS o duoi). Phep kiem
    # nay hoi "co tin hieu that khong", khong hoi "to bao nhieu"; dat nguong
    # theo mot con so doan la bien no thanh phep kiem thu hai ma khong ai dinh.
    assert np.abs(mang).max() > 0.01, "doc ra toan so 0"

    ra = tmp_path / "ra.wav"
    ghi_wav(str(ra), mang, tan_so)
    lai, tan_so2 = doc_wav(str(ra))
    assert tan_so2 == tan_so and lai.shape == mang.shape
    assert np.abs(lai - mang).max() < 0.01, "ghi roi doc lai bi lech nhieu"


def test_ghi_wav_KEP_bien_do_thay_vi_cuon_vong(tmp_path):
    """Mot mau vuot [-1, 1] doi thang sang int16 se **cuon vong** — mot dinh am
    to bien thanh mot tieng no. Kep thi no chi bi cat ngon, nghe duoc."""
    import numpy as np

    from apps.auto_scan_video.demucs_runner import doc_wav, ghi_wav

    qua = np.array([[2.0, -2.0, 0.5]], dtype="float32")
    ghi_wav(str(tmp_path / "kep.wav"), qua, 44100)
    lai, _ = doc_wav(str(tmp_path / "kep.wav"))
    assert lai[0][0] > 0.9, "mau duong vuot nguong da cuon vong thanh so am"
    assert lai[0][1] < -0.9, "mau am vuot nguong da cuon vong"


# ══════════════════════════════════════════════════════════════════════════════
#  Rut ban day du — KHAC ban 16 kHz cua pha 08
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_cho_TACH_khac_ban_cho_ASR(tmp_path):
    """Hai ban tieng cho hai muc dich, va do khong phai trung lap.

    Dua ban 16 kHz mono cua pha 08 vao demucs la sai hai huong cung luc: mat
    toan bo dai tren 8 kHz (Nyquist) — tuc phan lon thong tin phep tach dua vao
    — va mat anh stereo ma htdemucs dung de phan biet nguon.
    """
    from apps.auto_scan_video import nhap_media, tach_tieng
    from tests.fixtures.asv_media import tiny_mp4

    nguon = tiny_mp4(tmp_path / "v.mp4")

    asr = nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "asr.wav"))
    day_du = tach_tieng.rut_ban_day_du(str(nguon), str(tmp_path / "dd.wav"))

    tt_asr = nhap_media.soi(asr)
    tt_dd = nhap_media.soi(day_du)

    assert tt_asr["tan_so"] == 16000 and tt_asr["so_kenh"] == 1
    assert tt_dd["tan_so"] == 44100 and tt_dd["so_kenh"] == 2
    assert tt_asr["tan_so"] != tt_dd["tan_so"], "hai ban phai khac nhau"


# ══════════════════════════════════════════════════════════════════════════════
#  Tach nguon — smoke THAT
# ══════════════════════════════════════════════════════════════════════════════

@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_tach_nguon_ra_du_BON_stem(tmp_path):
    """Smoke that voi demucs that. Checkpoint da nam trong cache torch hub.

    Do tren may nay: 3 giay stereo -> 4,3 giay tren CPU.
    """
    from apps.auto_scan_video import tach_tieng

    nguon = _wav_stereo(tmp_path / "a.wav", giay=1.0)
    ket_qua = tach_tieng.tach_nguon(str(nguon), str(tmp_path / "stem"))

    assert set(ket_qua["nguon"]) == {"drums", "bass", "other", "vocals"}
    for ten, duong in ket_qua["duong"].items():
        assert Path(duong).exists() and Path(duong).stat().st_size > 0, ten
    assert ket_qua["thiet_bi"] in ("cpu", "cuda")


def test_stem_giu_lai_dung_chinh_sach_da_khai(tmp_path):
    """Muc 4 — chinh sach stem phai la mot ban khai, khong phai mot y dinh."""
    from apps.auto_scan_video import tach_tieng

    assert tach_tieng.STEM_GIU == ("drums", "bass", "other")
    assert tach_tieng.STEM_BO == ("vocals",)
    assert set(tach_tieng.STEM_GIU) & set(tach_tieng.STEM_BO) == set()


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_tron_nen_ra_dung_dinh_dang_va_am_luong(tmp_path):
    from apps.auto_scan_video import nhap_media, tach_tieng

    nguon = _wav_stereo(tmp_path / "a.wav", giay=1.0)
    ket_qua = tach_tieng.tach_nguon(str(nguon), str(tmp_path / "stem"))
    nen = tach_tieng.tron_nen(ket_qua["duong"], str(tmp_path / "bed.wav"))

    tt = nhap_media.soi(nen)
    assert tt["tan_so"] == tach_tieng.TAN_SO_TACH
    assert tt["so_kenh"] == tach_tieng.SO_KENH_TACH
    assert tt["thoi_luong"] == pytest.approx(1.0, abs=0.15)


def test_tron_nen_KHONG_co_stem_thi_nem(tmp_path):
    from apps.auto_scan_video import nhap_media, tach_tieng

    with pytest.raises(nhap_media.MediaError):
        tach_tieng.tron_nen({}, str(tmp_path / "bed.wav"))


def test_do_am_luong_cat_dung_khoi_JSON(tmp_path):
    """🔴 Loi da co that o day, va no doi thong bao chi sai cho.

    `loudnorm` in khoi JSON ra stderr **giua chung**, roi ffmpeg in tiep dong
    tong ket (`[out#0/null ...]`, `size=N/A ...`) sau no. Ban dau ham nay lay tu
    `{` **den het chuoi**, nen `json.loads` luon vo — va thong bao "khong do
    duoc am luong" chi vao ffmpeg trong khi loi nam trong chinh ham nay.
    """
    from apps.auto_scan_video import tach_tieng

    nguon = _wav_stereo(tmp_path / "a.wav", giay=1.0)
    am = tach_tieng.do_am_luong(str(nguon))
    assert isinstance(am["lufs"], float) and am["lufs"] < 0
    assert isinstance(am["dinh_that"], float)


# ══════════════════════════════════════════════════════════════════════════════
#  I11 / O6 — card do NEN TANG cap
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_truong_GPU_duoc_truyen_XUONG_tien_trinh_con(tmp_path, monkeypatch):
    """Yeu cau kiem chung cua pha: "Verify assigned GPU env in subprocess test".

    Do bang cach dat mot bien danh dau vao `gpu_env` roi doc lai no **tu ben
    trong** tien trinh con. Neu moi truong khong duoc truyen xuong, tien trinh
    con se khong thay bien do.
    """
    import json
    import os
    import sys

    ma = ("import os, json; "
          "print(json.dumps({'thay': os.environ.get('ASV_DANH_DAU', '')}))")
    moi_truong = dict(os.environ)
    moi_truong["ASV_DANH_DAU"] = "card-7"

    from apps.auto_scan_video.tach_tieng import _chay_kem_moi_truong

    r = _chay_kem_moi_truong([sys.executable, "-c", ma], timeout=60,
                             hoi_huy=None, moi_truong=moi_truong)
    assert r.returncode == 0
    assert json.loads(r.stdout.decode())["thay"] == "card-7", (
        "moi truong GPU KHONG toi duoc tien trinh con")


def test_tach_nguon_truyen_gpu_env_cua_JobContext(tmp_path, monkeypatch):
    """Chuoi day du: `JobContext.gpu_env()` -> `tach_nguon` -> tien trinh con.

    Chan `_chay_kem_moi_truong` de bat lay moi truong that su duoc dung, thay vi
    tin rang no da duoc truyen.
    """
    import subprocess as sp

    from apps.auto_scan_video import tach_tieng

    bat = {}

    def gia(cmd, *, timeout, hoi_huy, moi_truong):
        bat["moi_truong"] = moi_truong
        return sp.CompletedProcess(cmd, 0, b'{"nguon":[],"duong":{},"tan_so":44100,'
                                           b'"thiet_bi":"cpu"}', b"")

    monkeypatch.setattr(tach_tieng, "_chay_kem_moi_truong", gia)
    tach_tieng.tach_nguon("a.wav", str(tmp_path / "s"),
                          gpu_env={"CUDA_VISIBLE_DEVICES": "GPU-abc", "PATH": "x"})

    assert bat["moi_truong"]["CUDA_VISIBLE_DEVICES"] == "GPU-abc", (
        "card da cap khong toi duoc tien trinh con")


def test_KHONG_tep_nao_cua_auto_scan_tu_chon_card():
    """I11 — chot lai o day vi pha nay la pha dau tien co the vi pham that.

    Guard AST o `test_401` quet ca ba app; phep kiem nay goi thang no de mot lan
    hong hien ra trong bao cao cua chinh pha 09.
    """
    from tests.test_401_asv_ranh_gioi_va_artifact import (_CAM_GPU,
                                                          _tep_auto_scan,
                                                          _vi_pham)

    xau = []
    for tep in _tep_auto_scan():
        con = _vi_pham(tep.read_text(encoding="utf-8", errors="replace"), _CAM_GPU)
        if con:
            xau.append(f"{tep.name}: {con}")
    assert not xau, xau


# ══════════════════════════════════════════════════════════════════════════════
#  Van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_theo_nguon_model_va_cong_cu():
    from apps.auto_scan_video import tach_tieng

    goc = tach_tieng.van_tay_tach(checksum_nguon="aaa", phien_ban_ffmpeg_="8.0")
    assert goc != tach_tieng.van_tay_tach(checksum_nguon="bbb",
                                          phien_ban_ffmpeg_="8.0")
    assert goc != tach_tieng.van_tay_tach(checksum_nguon="aaa",
                                          phien_ban_ffmpeg_="7.1")


def test_van_tay_doi_khi_CHINH_SACH_STEM_doi(monkeypatch):
    """Doi stem giu lai = doi ban nen. Cache cu phai vo hieu (O13)."""
    from apps.auto_scan_video import tach_tieng

    truoc = tach_tieng.van_tay_tach(checksum_nguon="aaa", phien_ban_ffmpeg_="8.0")
    monkeypatch.setattr(tach_tieng, "STEM_GIU", ("drums", "bass"))
    assert tach_tieng.van_tay_tach(checksum_nguon="aaa",
                                   phien_ban_ffmpeg_="8.0") != truoc


def test_van_tay_doi_khi_MODEL_doi(monkeypatch):
    from apps.auto_scan_video import tach_tieng

    truoc = tach_tieng.van_tay_tach(checksum_nguon="aaa", phien_ban_ffmpeg_="8.0")
    monkeypatch.setattr(tach_tieng, "MODEL_TACH", "mdx_extra")
    assert tach_tieng.van_tay_tach(checksum_nguon="aaa",
                                   phien_ban_ffmpeg_="8.0") != truoc


# ══════════════════════════════════════════════════════════════════════════════
#  Cong thoat
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_ban_nen_la_artifact_chinh_tac_da_kiem(tmp_path, monkeypatch):
    """Chay that qua hang doi: `media_prepare` roi `audio_prepare`.

    Cuoi cung phai co mot ban nen ben vung, kiem duoc, dung dinh dang, dung thoi
    luong — va **khong** co ban `vocals` nao duoc luu.
    """
    import platform_core.db as dbmod
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.storage import LocalStorage, set_storage
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p9.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)
    try:
        from apps.auto_scan_video import assets, features, nhap_media, tach_tieng

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()

        for _ in range(8):
            job = jobs.claim(db, worker_id="w", capabilities={"api", "ffmpeg", "gpu", "voice"})
            if job is None:
                break
            db.commit()
            ctx = JobContext(job.id); ctx.job_type = job.job_type
            try:
                jobs.complete(db, job, jobs.resolve_handler(job.job_type)(
                    dict(job.params), ctx) or {})
            except Exception as exc:      # noqa: BLE001
                jobs.fail(db, job, str(exc), retry=False)
            db.commit()
        db.expire_all()

        s = features.giai_doan_theo_ten(db, run.id, "audio_prepare")
        assert s.status == "succeeded", f"audio_prepare: {s.status} {s.error}"

        khoa_ra = (s.outputs or {}).get("khoa_asset") or []
        assert len(khoa_ra) == 1, "chi mot ban nen duoc luu"
        a = assets.asset_cua(db, khoa_ra[0], "uA")
        assert a.kind == "audio"
        assert assets.kiem_toan_ven(db, kho, a) == "ok"

        tt = nhap_media.soi(kho.local_path(a.storage_key))
        assert tt["tan_so"] == tach_tieng.TAN_SO_TACH
        assert tt["so_kenh"] == tach_tieng.SO_KENH_TACH

        # ⛔ Giong goc cua khach KHONG duoc luu lai o dau ca.
        from sqlalchemy import select
        from apps.auto_scan_video.tables import AsvAsset
        moi_khoa = [r.storage_key for r in db.execute(select(AsvAsset)).scalars()]
        assert not any("vocal" in k.lower() for k in moi_khoa), (
            "giong goc cua khach bi luu lai")

        # Lineage: ban nen tro ve artifact cua `media_prepare`.
        truoc = features.giai_doan_theo_ten(db, run.id, "media_prepare")
        assert set((truoc.outputs or {}).get("khoa_asset") or []).issubset(
            set(a.parent_keys))
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  Cho bang chung ngoai
# ══════════════════════════════════════════════════════════════════════════════

class TestChoBangChungNgoai:
    """Nhung thu may nay KHONG do duoc, ghi ra thay vi lam ngo.

    ⛔ Prompt 09 doi: "mocked external-model path otherwise must remain pending
       external evidence". Day la cho ghi dieu do.
    """

    def test_torch_o_may_nay_la_ban_CPU(self):
        """Nen khong do duoc VRAM that (RISK-05-01 van mo).

        `asv_gpu.gpu_vram_mb` van la **uoc luong**. Luat cua kho la "CHUA DO THI
        KHONG CHAY", va phep do do can mot may co card + ban torch CUDA.
        """
        import torch
        assert not torch.cuda.is_available(), (
            "May nay da co CUDA — hay DO VRAM that cua demucs va cap nhat "
            "`apps/asv_gpu/manifest.py:gpu_vram_mb`, roi xoa phep kiem nay.")


# ══════════════════════════════════════════════════════════════════════════════
#  Tran luong torch — cho ma ngan sach cua gate khong voi toi
# ══════════════════════════════════════════════════════════════════════════════

def test_demucs_runner_CHAN_so_luong_torch():
    """🔴 Nguyen nhan gan nhat cua mot lan may chet, do duoc trong hop den 03/09.

    Muoi hai tien trinh `demucs_runner` chay trong 4 phut 12 giay, moi cai dinh
    **462-984% CPU** — moi tien trinh mot minh doi 5 den 10 loi logic. Luc
    16:51:09 CPU cham 100%, RAM trong tut tu 17,7 xuong 14,1 GB, va may khong
    ghi them dong nao nua.

    🔑 Day la cho ma `-n 6` **khong voi toi duoc**: no dem WORKER PYTEST, khong
       dem thu moi worker sinh ra. Sau worker, moi worker mot demucs, moi demucs
       muoi luong = 60 luong tren 10 loi. Mot tien trinh chau khong xin khoa,
       khong khai bao, va khong nam trong bat cu phep tinh nao cua gate.
    """
    import torch

    from apps.auto_scan_video import demucs_runner

    assert demucs_runner.LUONG_TORCH <= 4, (
        "tran luong torch phai NHO - mot lan tach nguon la viec nen, khong gap")

    cu = torch.get_num_threads()
    try:
        n = demucs_runner._dat_tran_luong(torch)
        assert n == demucs_runner.LUONG_TORCH
        assert torch.get_num_threads() == demucs_runner.LUONG_TORCH, (
            "goi ham ma so luong khong doi - `set_num_threads` khong an")
    finally:
        torch.set_num_threads(cu)


def test_tran_luong_duoc_dat_TRUOC_khi_nap_model():
    """⛔ `torch.set_num_threads` sau khi mot phep tinh da bat dau thi khong con
    tac dung len phep tinh do.

    Chot bang AST: trong `main`, loi goi `_dat_tran_luong` phai dung TRUOC
    `get_model` va `apply_model`.
    """
    import ast

    from apps.auto_scan_video import demucs_runner

    cay = ast.parse(Path(demucs_runner.__file__).read_text(encoding="utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "main"][0]

    dong = {}
    for n in ast.walk(ham):
        if isinstance(n, ast.Call):
            ten = (n.func.id if isinstance(n.func, ast.Name)
                   else getattr(n.func, "attr", ""))
            if ten in ("_dat_tran_luong", "get_model", "apply_model"):
                dong.setdefault(ten, n.lineno)

    assert "_dat_tran_luong" in dong, "`main` khong dat tran luong"
    for sau in ("get_model", "apply_model"):
        if sau in dong:
            assert dong["_dat_tran_luong"] < dong[sau], (
                f"dat tran luong SAU `{sau}` thi khong con tac dung")
