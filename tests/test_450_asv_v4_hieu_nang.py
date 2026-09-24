"""Pha 24 — HIEU NANG VA TAI: do that tren may nay, roi moi noi cai gi nhanh.

## Cau hoi cua pha nay khong phai "no co nhanh khong"

Ma la: **mot lan chay co lam may bao hoa khong, va cho nao.** May nay dang phuc
vu khach that (`C:\\LTTPlatform`), nen mot giai doan an het CPU trong ba muoi
giay khong phai mot con so trong bang — no la ba muoi giay khach cua ung dung
khac cho lau hon.

⇒ Moi con so o day la **CPU/RAM/VRAM TOAN MAY**, khong phai cua rieng tien trinh,
  va bao cao ghi lai tai nen do duoc luc bat dau de doc duoc phan chenh.

## Hai nua, giong pha 22 va vi cung mot ly do

    A. LUOT DO THAT  — nang, mac dinh KHONG chay, ghi ra bao cao may doc duoc
    B. DOC BAO CAO   — nhe, chay moi luot gate, doi chieu so do voi khai bao
                       HOM NAY (`gpu_vram_mb`, tran lap lai, bo ma hoa)

⭐ Nua B la thu bien mot bang so thanh mot **chot**: `asv_gpu` khai 2.200 MB VRAM
   cho `audio_prepare`; neu phep do noi 3.000 thi khai bao do sai, va mot con so
   sai trong `gpu_vram_mb` khong hong to — no chi xep job vao mot card khong du
   cho roi OOM giua chung.

⛔ Luot do KHONG ghi vao cay lam viec (xem `test_448`): duong ra lay tu bien
   `LTT_ASV_PERF_RA`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e as fx
from tests.fixtures import do_tai
from tests.test_423_asv_giao_dien import moi_truong  # noqa: F401

import apps.ltt_voice.tables  # noqa: E402,F401  isort:skip

#: 🔴 **Tep nay CUON, no khong dong bang — va cai ten cu da noi nguoc lai.**
#:
#:    No tung ten la `24_hieu_nang.json`, nghe nhu "bang chung cua pha 24".
#:    Thuc te moi luot nghiem thu deu GHI DE len no, va dieu do la CO Y: pha 28
#:    da sinh lai no vi bang chung ghi truoc mot commit cham vao duong chay thi
#:    khong con mo ta ban dang xet.
#:
#: ⛔ Hai su that do khong the cung dung duoi mot cai ten. Bao cao pha 24 trich
#:    so tu tep nay; sau pha 29 nhung so do khong con o trong no nua — lien ket
#:    van song, noi dung van dung, chi la no khong con la thu bao cao 24 mo ta.
#:    Doi ten de cai ten thoi hua mot dieu ma tep khong giu.
BAO_CAO = (Path(__file__).resolve().parents[1]
           / "docs" / "auto_scan_video_v4" / "evidence"
           / "hieu_nang_hien_hanh.json")
BIEN_RA = "LTT_ASV_PERF_RA"
SCHEMA = "asv.v4.hieu_nang.1"
NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}

#: Tran CPU toan may cho tai DUY TRI cua mot lan chay don le, tinh bang %.
#:
#: 🔑 **Do tren TRUNG BINH cua giai doan, khong tren dinh.** Mot mau 0,5 giay o
#:    97% luc ffmpeg khoi dong la mot dinh; thu lam dich vu khac tren may cham
#:    lai la giu muc do trong nhieu giay lien. Do duoc o pha 24: `transcribe`
#:    cham 96,9% o **mot** mau trong khi trung binh ca giai doan la 39,8% — goi
#:    do la "bao hoa" thi phep kiem se do mot cai gai, khong do mot van de.
#:
#: ⛔ Va con so nay duoc chot TRUOC khi nhin ket qua. Chinh sua no sau khi thay
#:    so do la tu chinh thuoc do cho vua voi vat.
#:
#: ⚠️ CHUA phai mot chinh sach da duoc chu du an duyet — no la nguong pha 24 dat
#:    ra de co mot cai chot, va bao cao noi ro do la nguong tu dat.
TRAN_CPU_MOT_LUOT = 90.0

#: So giay mot giai doan duoc phep O TREN tran truoc khi goi la bao hoa.
#:
#: ⭐ Khong phai 0: mot lan khoi dong tien trinh con luon co mot dinh ngan, va
#:    mot nguong 0 se bien moi lan chay ffmpeg thanh mot vi pham.
GIAY_TREN_TRAN_TOI_DA = 3.0

#: RAM trong thap nhat cho phep (MiB). Duoi muc nay may bat dau swap, va swap
#: tren mot may dang phuc vu khach la thu nguoi dung CAM THAY duoc.
SAN_RAM_TRONG_MB = 4096.0


def _cap_gpu_nhu_worker_that(db, job_type: str, job_id: str):
    """Giu mot card DUNG cach `job_runner._giu_gpu` giu, hoac `None`.

    ⛔ Doc nhu cau tu chinh `job_runner._vram_can` chu khong go lai con so: mot
       ban sao cua ban khai la mot ban sao se lech, va luc do bo do se noi rang
       san pham dung trong khi no chi dung so cua bo do.
    """
    from platform_core import gpu_lease
    from platform_core.job_runner import _vram_can

    can = _vram_can(job_type)
    if can <= 0:
        return None

    # 🔴 **Cap card cho mot tien trinh KHONG THE dung card la lam ban do bot
    #    trung thanh, khong phai them.**
    #
    #    Cay nay chay `torch+cpu` (V4-R05). Cap lease cho `asv_gpu.*` o day thi
    #    `ctx.gpu_uuid` co gia tri, `demucs_runner` tin rang no co card, roi
    #    khong thay CUDA dau va nem `ThieuCard: "Nen tang da cap card nhung tien
    #    trinh tach khong thay GPU"` — mot phan loai HOAN TOAN DUNG cho mot tinh
    #    huong ma bo do vua tu bia ra.
    #
    # ⇒ Hoi chinh thu quyet dinh: torch cua cay NAY co thay card khong. Tren
    #   venv san pham (`torch 2.11.0+cu128`) dieu kien nay dat va lease duoc cap
    #   nhu worker that; o cay dev thi khong, va bo do noi that ve dieu do thay
    #   vi gia vo.
    #
    # ⚠️ `asv_media.render` KHONG di qua torch — no chay ffmpeg, va `h264_nvenc`
    #    dung duoc ngay ca khi torch la ban CPU. Nen no van duoc cap.
    if not _torch_thay_card() and not job_type.startswith("asv_media."):
        return None
    try:
        return gpu_lease.acquire(db, worker_id="w-do", job_id=job_id,
                                 need_mb=can)
    except Exception:                       # noqa: BLE001
        return None


def _torch_thay_card() -> bool:
    """Trinh thong dich DANG CHAY co thay GPU khong. Do, khong khai."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:                       # noqa: BLE001
        return False


def _nha_gpu(db, lease) -> None:
    from platform_core import gpu_lease
    try:
        gpu_lease.release(db, lease)
    except Exception:                       # noqa: BLE001
        pass


def _chay_hang_doi_co_do(db, bo_do, *, nang_luc=NANG_LUC, toi_da=200) -> list[dict]:
    """Worker that, va danh dau moc tung giai doan cho bo do.

    ⭐ Moc dat quanh **loi goi handler**, khong quanh ca vong lap: thoi gian nhat
       job va ghi CSDL khong phai thoi gian cua giai doan, va gop chung vao se
       lam moi giai doan trong dat hon thuc te.
    """
    from platform_core import jobs as jobq
    from platform_core.job_runner import JobContext

    nhat_ky: list[dict] = []
    for _ in range(toi_da):
        job = jobq.claim(db, worker_id="w-do", capabilities=nang_luc)
        if job is None:
            break
        db.commit()
        handler = jobq.resolve_handler(job.job_type)
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        # 🔴 **Worker gia nay tung bo qua buoc cap GPU, va do la mot khoang
        #    trong lam chinh no khong the do duoc thu no dinh do.**
        #
        #    `job_runner._giu_gpu` doc `gpu_vram_mb` cua app roi giu mot card
        #    truoc khi goi handler. Bo qua no thi `ctx.gpu_uuid` luon rong o
        #    day — nen mot cau hoi nhu "lan chay co dung bo ma hoa phan cung
        #    khong" chi do duoc chinh cai khoang trong nay, chu khong do san
        #    pham. Cung lop loi ma pha 24 goi la "phep do mo ta bo do".
        lease = _cap_gpu_nhu_worker_that(db, job.job_type, job.id)
        if lease is not None:
            ctx.gpu_uuid = lease.gpu_uuid
        ten = job.job_type.split(".")[-1]
        t0 = time.time()
        loi = ""
        bo_do.bat_dau(ten)
        try:
            jobq.complete(db, job, handler(dict(job.params), ctx) or {})
        except Exception as exc:            # noqa: BLE001
            loi = f"{type(exc).__name__}: {exc}"
            jobq.fail(db, job, str(exc), retry=False)
        finally:
            bo_do.ket_thuc(ten)
            if lease is not None:
                _nha_gpu(db, lease)
        db.commit()
        nhat_ky.append({"giai_doan": ten, "giay": round(time.time() - t0, 2),
                        "loi": loi})
    db.expire_all()
    return nhat_ky


def _ban_dung_cua(db, run) -> dict:
    """Ban dung da luu — de doc ra BO MA HOA that su duoc chon."""
    from platform_core.storage import get_storage

    from apps.auto_scan_video import features, pipeline

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.COMPOSE)
    khoa = next((k for k in ((gd.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if gd else ""
    if not khoa:
        return {}
    with get_storage().open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_DO_TAI_hai_preset(moi_truong, tmp_path, monkeypatch):
    """Chay that hai preset, lay mau tai nguyen, dem cong viec lap lai."""
    _app, a, csrf_a, _b, _cb = moi_truong
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")

    import platform_core.db as dbmod
    from apps.auto_scan_video import hop_dong_v4, pipeline
    from apps.auto_scan_video.tables import AsvRun

    if not fx.co_sapi():
        pytest.skip("khong co SAPI de dung ban nguon co tieng noi that")

    su_that = fx.nguon_hoi_thoai(tmp_path / "nguon")
    fx.dat_cua_model(monkeypatch, su_that=su_that)
    fx.dat_cua_giong(monkeypatch, tmp_path / "tieng")

    luot = []
    for nhan, preset in (("giu_hinh", hop_dong_v4.PRESET_GIU_HINH),
                         ("cat_thong_minh", hop_dong_v4.PRESET_CAT_THONG_MINH)):
        du_lieu = {"csrf_token": csrf_a, "che_do": "fit_original",
                   "preset": preset,
                   "che_do_giong": hop_dong_v4.CHE_DO_GIONG_TU_CHON,
                   "giong_id": "Minh Đức"}

        db = next(dbmod.get_session())
        try:
            bo_dem = do_tai.gan_bo_dem(monkeypatch, do_tai.BoDem())
            # 🔴 **Bo do mo TRUOC khi nop form.**
            #
            #    Luot do dau tien cua pha nay chup tai nen NGAY SAU khi form da
            #    tai video len — va lan tai len do tu no chay `ffprobe`, kiem
            #    chinh sach, ghi vao kho. Ket qua: "nen 83,2%" trong khi may
            #    thuc su rat yen, va moi con so sau do doc lech theo.
            #
            # ⭐ Mot phep do tinh tai nen SAU khi minh da bat dau lam viec thi no
            #    dang do chinh minh va goi do la nen.
            with do_tai.BoDo() as bo_do:
                bo_do.bat_dau("tai_len")
                with open(su_that.duong, "rb") as f:
                    r = a.post("/auto-scan-video/tao", data=du_lieu,
                               files={"video": ("n.mp4", f, "video/mp4")})
                bo_do.ket_thuc("tai_len")
                assert r.status_code == 200 and "/run/" in str(r.url), r.text[:300]
                run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
                nhat_ky = _chay_hang_doi_co_do(db, bo_do)
            run = db.get(AsvRun, run_id)
            db.refresh(run)
            ban = _ban_dung_cua(db, run)
            luot.append({
                "nhan": nhan, "preset": preset,
                "trang_thai": run.status,
                "giai_doan": bo_do.theo_giai_doan(tran_cpu=TRAN_CPU_MOT_LUOT),
                "tong": bo_do.tong(),
                "nhat_ky": nhat_ky,
                "lap_lai": bo_dem.sang_dict(),
                "lap_lai_chi_tiet": {k: v[:24] for k, v in bo_dem.chi_tiet.items()},
                "bo_ma_hoa": str((ban.get("hinh") or {}).get("bo_ma_hoa") or ""),
                "cach_render": str((ban.get("hinh") or {}).get("cach_render") or ""),
            })
        finally:
            db.close()

    from platform_core import media

    bao_cao = {
        "schema": SCHEMA,
        "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may": _may(),
        "bo_ma_hoa_may_co": media.detect_gpu_encoder(),
        "nguong": {"tran_cpu_mot_luot": TRAN_CPU_MOT_LUOT,
                   "giay_tren_tran_toi_da": GIAY_TREN_TRAN_TOI_DA,
                   "san_ram_trong_mb": SAN_RAM_TRONG_MB},
        "nguon": {"thoi_luong": su_that.thoi_luong,
                  "so_canh": len(su_that.canh), "so_loi": len(su_that.loi)},
        "khai_bao_vram": _khai_vram(),
        "luot": luot,
    }
    duong = Path(os.environ.get(BIEN_RA) or (tmp_path / "hieu_nang_hien_hanh.json"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(
        json.dumps(fx.sach_de_cong_bo(bao_cao), ensure_ascii=False,
                   indent=2), encoding="utf-8")

    for l in luot:
        assert l["trang_thai"] == "done", (l["nhan"], l["nhat_ky"])
        assert [g["ten"] for g in l["giai_doan"] if g["ten"] != "advance"], l["nhan"]
    assert len(pipeline.CHUOI) == 12


def _may() -> dict:
    import platform

    import psutil

    from platform_core import media

    try:
        import torch
        mo_ta = f"{torch.__version__} cuda={torch.cuda.is_available()}"
    except Exception:                       # noqa: BLE001
        mo_ta = ""
    return {"os": platform.platform(), "python": platform.python_version(),
            "loi_vat_ly": psutil.cpu_count(logical=False),
            "loi_logic": psutil.cpu_count(logical=True),
            "ram_gib": round(psutil.virtual_memory().total / 2 ** 30, 1),
            "ffmpeg": media.ffmpeg_bin().rsplit("\\", 1)[-1], "torch": mo_ta}


def _khai_vram() -> dict:
    """`gpu_vram_mb` cac app ASV dang khai — de doi chieu voi dinh do duoc."""
    from platform_core.registry import discover

    ra = {}
    for it in discover():
        if it.error or not str(it.manifest.slug).startswith("asv"):
            continue
        for jt in it.manifest.job_types:
            v = it.manifest.vram_for(jt)
            if v:
                ra[jt] = v
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  B. DOC BAO CAO
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def bc() -> dict:
    if not BAO_CAO.exists():
        pytest.fail(f"chua co bao cao hieu nang {BAO_CAO}")
    return json.loads(BAO_CAO.read_text(encoding="utf-8"))


def test_bao_cao_du_hai_preset_va_dung_luoc_do(bc):
    from apps.auto_scan_video import hop_dong_v4

    assert bc["schema"] == SCHEMA
    assert {l["preset"] for l in bc["luot"]} == set(hop_dong_v4.PRESET)


def test_KHONG_giai_doan_nao_dat_may_vao_bao_hoa(bc):
    """⛔ Cong thoat cua pha 24: khong giai doan nao lam may bao hoa **ma khong
    duoc ghi lai**. Vuot tran thi phai co ten trong bao cao, khong duoc im."""
    tran = float(bc["nguong"]["tran_cpu_mot_luot"])
    lau = float(bc["nguong"]["giay_tren_tran_toi_da"])

    # Tai DUY TRI: trung binh ca giai doan.
    duy_tri = [(l["nhan"], g["ten"], g["cpu_tb"])
               for l in bc["luot"] for g in l["giai_doan"] if g["cpu_tb"] > tran]
    assert not duy_tri, f"tai duy tri vuot {tran}%: {duy_tri}"

    # Va khong duoc NAM tren tran lau: mot dinh thi duoc, mot cao nguyen thi khong.
    cao_nguyen = [(l["nhan"], g["ten"], g["cpu_tren_tran_giay"])
                  for l in bc["luot"] for g in l["giai_doan"]
                  if float(g.get("cpu_tren_tran_giay") or 0) > lau]
    assert not cao_nguyen, f"o tren {tran}% qua {lau}s: {cao_nguyen}"


def test_RAM_trong_khong_tut_xuong_duoi_san(bc):
    san = float(bc["nguong"]["san_ram_trong_mb"])
    thap = [(l["nhan"], l["tong"]["ram_trong_thap_nhat_mb"]) for l in bc["luot"]
            if l["tong"]["ram_trong_thap_nhat_mb"] < san]
    assert not thap, f"RAM trong tut duoi {san} MiB: {thap}"


def test_VRAM_dinh_KHONG_vuot_con_so_app_dang_khai(bc):
    """🔑 Bien mot bang so thanh mot chot.

    `gpu_vram_mb` la **san de nen tang xep cho**. Khai thieu thi job bi xep vao
    card khong du trong roi OOM giua chung; khai thua thi no cho lau hon can.
    Phep kiem nay doi chieu dinh do duoc voi con so dang khai HOM NAY.
    """
    khai = bc.get("khai_bao_vram") or {}
    assert khai, "bao cao khong ghi khai bao VRAM nao"

    # ⛔ **Tren mot cay `torch+cpu` phep kiem nay do RONG, va no phai NOI RA.**
    #
    #    V4-R05: trinh thong dich cua cay nay la `torch 2.11.0+cpu`, nen demucs
    #    va ASR deu chay tren CPU va VRAM gan nhu khong nhuc nhich. Khi do moi
    #    khai bao — 2.200 hay 1 MiB — deu "dat", va mot phep kiem luon dat la
    #    mot phep kiem khong do gi.
    #
    # ⭐ Bo qua CO LY DO thay vi de no xanh: mot phep kiem xanh rong lam nguoi
    #    doc tin rang con so da duoc doi chieu. Do dung la cai bay pha 23 vua
    #    dinh voi hai phep kiem cache.
    if "cuda=True" not in str(bc.get("may", {}).get("torch") or ""):
        pytest.skip("cay nay la torch+cpu (V4-R05) — VRAM khong nhuc nhich, "
                    "phep doi chieu nay khong do duoc gi o day")
    for l in bc["luot"]:
        for g in l["giai_doan"]:
            jt = f"asv_gpu.{g['ten']}"
            if jt not in khai:
                continue
            dinh = max(g.get("vram_dinh_mb") or [0])
            nen = max((bc["luot"][0]["tong"]["nen"].get("vram_mb_nen") or [0]))
            assert dinh - nen <= khai[jt], (
                f"{jt}: dinh do duoc {dinh} MiB (nen {nen}) vuot khai {khai[jt]}")


def test_bao_cao_ghi_ro_BO_MA_HOA_that_su_duoc_dung(bc):
    """⚠️ Khong khang dinh no phai la NVENC — chi doi bao cao NOI RA no la gi.

    Pha 17 do NVENC nhanh 1,68 lan va ha CPU may tu 61% xuong 41%. Neu duong
    chay that van chon `libx264` thi phep do do khong ap dung cho san pham, va
    dieu do phai nhin thay duoc trong bao cao chu khong nam trong mot cau van.
    """
    from apps.auto_scan_video import che_do_render as cdr, hop_dong_v4

    theo = {l["preset"]: l for l in bc["luot"]}
    cat = theo[hop_dong_v4.PRESET_CAT_THONG_MINH]
    assert cat["cach_render"] == cdr.CAT_MA_HOA_LAI
    assert cat["bo_ma_hoa"] in cdr.THAM_SO, cat["bo_ma_hoa"]
    # Preset giu hinh sao chep luong hinh, nen no khong chon bo ma hoa nao.
    assert theo[hop_dong_v4.PRESET_GIU_HINH]["bo_ma_hoa"] == ""


def test_may_va_tai_NEN_duoc_ghi_lai(bc):
    """Mot con so hieu nang khong kem tai nen la mot con so khong doc duoc."""
    for khoa in ("os", "loi_vat_ly", "ram_gib", "torch"):
        assert bc["may"].get(khoa) not in (None, ""), khoa
    for l in bc["luot"]:
        nen = l["tong"]["nen"]
        assert "cpu_nen" in nen and "ram_trong_mb_nen" in nen, l["nhan"]


# ══════════════════════════════════════════════════════════════════════════════
#  DEMUCS + ASR CHAY CUNG LUC — phep do ma `pipeline.CHUOI` dat hang
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 `pipeline.CHUOI` giu `audio_prepare` va `transcribe` tren **cung mot ten tai
#    nguyen** (`tach_nguon_cuc_bo`), nen chung khong bao gio chay dong thoi. Chu
#    thich o do noi thang ly do va noi thang cai gi se go duoc no:
#
#      "Dung MOT phep do de tach suat: chay `asv_gpu.audio_prepare` va
#       `asv_gpu.transcribe` dong thoi tren mot may dang phuc vu khach, do CPU
#       toan may + RAM trong + VRAM moi card. Neu dinh CPU < 70% va RAM trong
#       > 8 GiB thi tach ten tai nguyen ra, va thong luong tang ~1,3 lan."
#
# ⛔ Nguong 70% / 8 GiB duoc VIET RA TRUOC phep do, boi mot pha khac. Day la lan
#    chay no — khong phai lan chinh no cho vua ket qua.

#: Nguong tach suat, chep nguyen tu `pipeline.CHUOI`.
DINH_CPU_DE_TACH_SUAT = 70.0
RAM_TRONG_DE_TACH_SUAT_GIB = 8.0

BAO_CAO_SUAT = (Path(__file__).resolve().parents[1]
                / "docs" / "auto_scan_video_v4" / "evidence"
                / "suat_gpu_hien_hanh.json")
BIEN_RA_SUAT = "LTT_ASV_SUAT_RA"


def _rut_tieng(nguon: str, dich: Path, *, tan_so: int, so_kenh: int) -> str:
    """Rut ban tieng dung DANG ma tung engine doi.

    ⛔ Hai engine doi hai dang khac nhau, va do khong phai chi tiet: demucs
       **tu choi** mot tep 16 kHz — `tach_theo_khoi` nem "tan so tep 16000 khac
       tan so model 44100, phep ghim luoi phan doan se sai". Do la mot phep chot
       dung (pha 13 dat luoi phan doan theo tan so model), va no cung la ly do
       `media_prepare` sinh HAI ban tieng chu khong mot.
    """
    import subprocess

    from platform_core import media

    subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(nguon), "-vn", "-ac", str(so_kenh),
                    "-ar", str(tan_so), "-c:a", "pcm_s16le", str(dich)], check=True)
    return str(dich)


def _chay_demucs(duong_wav: str) -> float:
    from apps.auto_scan_video import tach_tieng

    t0 = time.time()
    import tempfile
    with tempfile.TemporaryDirectory(prefix="do-demucs-") as tam:
        tach_tieng.tach_nguon(duong_wav, tam)
    return round(time.time() - t0, 2)


def _chay_asr(duong_wav: str) -> float:
    from apps.auto_scan_video import giai_doan_chep_loi

    t0 = time.time()
    giai_doan_chep_loi.chep_loi(duong_wav)
    return round(time.time() - t0, 2)


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_DO_SUAT_demucs_va_asr(tmp_path, monkeypatch):
    """Ba lan do: demucs mot minh, ASR mot minh, va hai cai cung luc."""
    import threading

    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")

    if not fx.co_sapi():
        pytest.skip("khong co SAPI de dung ban nguon co tieng noi that")
    su_that = fx.nguon_hoi_thoai(tmp_path / "nguon")
    from apps.auto_scan_video import tach_tieng

    wav_asr = _rut_tieng(su_that.duong, tmp_path / "asr16k.wav",
                         tan_so=16000, so_kenh=1)
    wav_tach = _rut_tieng(su_that.duong, tmp_path / "tach44k.wav",
                          tan_so=tach_tieng.TAN_SO_TACH,
                          so_kenh=tach_tieng.SO_KENH_TACH)
    duong_cua = {"demucs": wav_tach, "asr": wav_asr}

    ket: dict = {}

    def do_mot(ten, ham, wav):
        with do_tai.BoDo() as bd:
            bd.bat_dau(ten)
            giay = ham(wav)
            bd.ket_thuc(ten)
        ket[ten] = {"giay": giay,
                    **{k: v for k, v in bd.tong().items() if k != "nen"},
                    "nen": bd.tong()["nen"]}

    do_mot("demucs_mot_minh", _chay_demucs, wav_tach)
    do_mot("asr_mot_minh", _chay_asr, wav_asr)

    # ── Cung luc ────────────────────────────────────────────────────────────
    thoi = {}
    with do_tai.BoDo() as bd:
        bd.bat_dau("cung_luc")
        luong = [threading.Thread(target=lambda: thoi.update(
                     {"demucs": _chay_demucs(wav_tach)})),
                 threading.Thread(target=lambda: thoi.update(
                     {"asr": _chay_asr(wav_asr)}))]
        t0 = time.time()
        for t in luong:
            t.start()
        for t in luong:
            t.join()
        tuong = round(time.time() - t0, 2)
        bd.ket_thuc("cung_luc")
    ket["cung_luc"] = {"giay_tuong": tuong, "giay_tung_cai": dict(thoi),
                       **{k: v for k, v in bd.tong().items() if k != "nen"},
                       "nen": bd.tong()["nen"]}

    lan_luot = ket["demucs_mot_minh"]["giay"] + ket["asr_mot_minh"]["giay"]
    ram_trong_gib = ket["cung_luc"]["ram_trong_thap_nhat_mb"] / 1024.0
    dat = (ket["cung_luc"]["cpu_dinh"] < DINH_CPU_DE_TACH_SUAT
           and ram_trong_gib > RAM_TRONG_DE_TACH_SUAT_GIB)

    bao_cao = {
        "schema": "asv.v4.suat_gpu.1",
        "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may": _may(),
        "nguon_giay": su_that.thoi_luong,
        "nguong_tach_suat": {"dinh_cpu": DINH_CPU_DE_TACH_SUAT,
                             "ram_trong_gib": RAM_TRONG_DE_TACH_SUAT_GIB},
        "do": ket,
        "lan_luot_giay": round(lan_luot, 2),
        "thong_luong_tang": round(lan_luot / max(0.01, tuong), 2),
        "dat_nguong_tach_suat": bool(dat),
        # ⛔ Cai phep do nay KHONG tra loi duoc, va no phai duoc ghi canh ket qua:
        #    cay nay chay `torch+cpu` (V4-R05), nen day la phep do CPU/RAM. Cau
        #    hoi VRAM khi hai model cung nam tren mot card van chua co cau tra loi.
        "chua_do_duoc": ("VRAM khi hai model cung tren mot card — cay nay la "
                         "torch+cpu (V4-R05), nen ca hai deu chay tren CPU"),
    }
    duong = Path(os.environ.get(BIEN_RA_SUAT) or (tmp_path / "suat_gpu_hien_hanh.json"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(
        json.dumps(fx.sach_de_cong_bo(bao_cao), ensure_ascii=False,
                   indent=2), encoding="utf-8")

    assert ket["cung_luc"]["giay_tuong"] > 0
    assert set(thoi) == {"demucs", "asr"}, thoi


def test_bao_cao_SUAT_ket_luan_khop_voi_so_do(bc):
    """⛔ Ket luan "tach duoc suat" phai suy TU so do, khong duoc gõ tay.

    Phep kiem nay tinh lai chinh phep so sanh do tu cac con so trong bao cao. Mot
    bao cao ket luan mot dang va do duoc mot neo la mot bao cao khong doc duoc.
    """
    if not BAO_CAO_SUAT.exists():
        pytest.skip("chua co bao cao suat GPU")
    b = json.loads(BAO_CAO_SUAT.read_text(encoding="utf-8"))
    ng = b["nguong_tach_suat"]
    cl = b["do"]["cung_luc"]
    tinh_lai = (cl["cpu_dinh"] < ng["dinh_cpu"]
                and cl["ram_trong_thap_nhat_mb"] / 1024.0 > ng["ram_trong_gib"])
    assert bool(b["dat_nguong_tach_suat"]) == tinh_lai, (
        f"bao cao ket luan {b['dat_nguong_tach_suat']} nhung so do cho "
        f"{tinh_lai}: cpu_dinh={cl['cpu_dinh']} "
        f"ram_trong={cl['ram_trong_thap_nhat_mb']}")
    assert b.get("chua_do_duoc"), "bao cao khong noi ra thu no KHONG do duoc"


# ══════════════════════════════════════════════════════════════════════════════
#  Hai chot rut ra tu so do
# ══════════════════════════════════════════════════════════════════════════════

# ⭐ **Nhan `xfail(strict=True)` da duoc GO o pha 27.** Ly do cu con dung tung
#    chu ve nguyen nhan, va no da duoc sua o BA cho: `asv_media` khai
#    `gpu_vram_mb` cho `asv_media.render` (500 MiB, do that: mot phien nvenc
#    1080p chiem dinh 228 MiB); quyet dinh bo ma hoa chuyen tu COMPOSE (mot job
#    khong bao gio giu lease toi luc render) sang RENDER; va ffmpeg duoc ghim
#    vao card duoc cap bang `ctx.gpu_env()`.
#    Do duoc tren luot chay that: `bo_ma_hoa_may_co h264_nvenc`, va lan chay
#    `cat_thong_minh` ghi `bo_ma_hoa: h264_nvenc`.
def test_preset_CAT_dung_bo_ma_hoa_PHAN_CUNG_khi_may_co(bc):
    """🔴 May co `h264_nvenc` (do duoc), pha 17 do NVENC nhanh 1,68 lan va ha
    CPU may tu 61% xuong 41% — va duong chay that van ma hoa bang CPU.

    ⭐ Cung hinh dang voi B22-01 (VLM dung xong khong ai goi) va B23-01 (cache
      dung xong khong bao gio trung): mot nang luc da do, da chung minh, va
      **khong noi vao mach**.
    """
    from apps.auto_scan_video import che_do_render as cdr, hop_dong_v4

    if bc.get("bo_ma_hoa_may_co") in ("", None, cdr.LUI_VE):
        pytest.skip("may nay khong co bo ma hoa phan cung de doi chieu")
    cat = next(l for l in bc["luot"]
               if l["preset"] == hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert cat["bo_ma_hoa"] == bc["bo_ma_hoa_may_co"], (
        f"may co {bc['bo_ma_hoa_may_co']} nhung lan chay dung "
        f"{cat['bo_ma_hoa']}")


def test_SUAT_GPU_van_phai_dung_CHUNG_cho_toi_khi_co_phep_do_moi(bc):
    """🔑 Mot quyet dinh dua tren so do, va mot chot giu no khoi bi doi ngam.

    `pipeline.CHUOI` viet san dieu kien tach suat: dinh CPU < 70% VA RAM trong
    > 8 GiB khi demucs va ASR chay cung luc. Pha 24 chay phep do do:

        demucs mot minh   20,74 s   dinh 49,0%   RAM trong thap nhat 11,2 GiB
        ASR mot minh      42,79 s   dinh 46,5%   RAM trong thap nhat  9,6 GiB
        cung luc          42,43 s   dinh 78,6%   RAM trong thap nhat  9,1 GiB

    Thong luong tang **1,5 lan** (63,53 s lan luot -> 42,43 s cung luc) — dung
    huong du doan. Nhung **dinh CPU 78,6% > 70%**, nen dieu kien KHONG dat, va
    hai giai doan phai tiep tuc dung chung mot suat.

    ⛔ Chot nay do rang chung VAN chung. Ai tach chung ra thi phai kem mot phep
       do moi — khong phai mot lan doi y.
    """
    from apps.auto_scan_video import pipeline

    theo = {g.ten: g for g in pipeline.CHUOI}
    am, chep = theo["audio_prepare"], theo["transcribe"]
    assert am.tai_nguyen and am.tai_nguyen == chep.tai_nguyen, (
        "audio_prepare va transcribe khong con dung chung mot ten tai nguyen — "
        "neu do la co y thi phai kem phep do moi thay cho "
        "evidence/suat_gpu_hien_hanh.json")
    assert am.tai_nguyen_suat == chep.tai_nguyen_suat == 1


# ══════════════════════════════════════════════════════════════════════════════
#  ASR tren CUDA — mon no pha 22 giao lai, do o day
# ══════════════════════════════════════════════════════════════════════════════

BAO_CAO_ASR = (Path(__file__).resolve().parents[1]
               / "docs" / "auto_scan_video_v4" / "evidence"
               / "asr_cuda_hien_hanh.json")
BIEN_RA_ASR = "LTT_ASV_ASR_RA"


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_DO_ASR_tren_CUDA(tmp_path, monkeypatch):
    """Tach BA buoc: hoi card, nap model, chay suy dien — moi buoc mot con so.

    🔴 Pha 22 ghi "hon bay phut khong ket qua, khong loi" va giao lai cho pha 24.
       Phep do o day tach ba buoc ra, va cau tra loi hoan toan khac: duong CUDA
       **khong treo**, no **nem ngay** — chi la nem o buoc ma khong ai bat.
    """
    from apps.auto_scan_video import giai_doan_chep_loi

    if not fx.co_sapi():
        pytest.skip("khong co SAPI de dung ban nguon co tieng noi that")
    su_that = fx.nguon_hoi_thoai(tmp_path / "nguon")
    wav = _rut_tieng(su_that.duong, tmp_path / "asr16k.wav",
                     tan_so=16000, so_kenh=1)

    try:
        import ctranslate2
    except Exception:                       # noqa: BLE001
        pytest.skip("khong co ctranslate2")
    if not ctranslate2.get_cuda_device_count():
        pytest.skip("may nay khong co card CUDA de do")

    from faster_whisper import WhisperModel

    ra = {"ct2": ctranslate2.__version__,
          "so_card": ctranslate2.get_cuda_device_count(),
          "model": giai_doan_chep_loi.MODEL_ASR, "buoc": {}}

    for ten, thiet_bi, tinh in (("cpu", "cpu", "int8"),
                                ("cuda", "cuda", "float16")):
        muc = {}
        t0 = time.time()
        try:
            m = WhisperModel(ra["model"], device=thiet_bi, compute_type=tinh)
            muc["giay_nap"] = round(time.time() - t0, 2)
        except Exception as loi:            # noqa: BLE001
            muc["giay_nap"] = round(time.time() - t0, 2)
            muc["loi_nap"] = f"{type(loi).__name__}: {loi}"
            ra["buoc"][ten] = muc
            continue
        t0 = time.time()
        try:
            doan, tt = m.transcribe(wav, vad_filter=True, beam_size=5)
            doan = list(doan)
            muc["giay_chay"] = round(time.time() - t0, 2)
            muc["so_doan"] = len(doan)
            muc["ngon_ngu"] = getattr(tt, "language", "")
        except Exception as loi:            # noqa: BLE001
            muc["giay_chay"] = round(time.time() - t0, 2)
            muc["loi_chay"] = f"{type(loi).__name__}: {loi}"
        ra["buoc"][ten] = muc

    ra["san_sang_sidecar"] = bool(os.environ.get("LTT_WHISPERX_PYTHON", "").strip())
    ra["ghi_luc"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ra["may"] = _may()
    duong = Path(os.environ.get(BIEN_RA_ASR) or (tmp_path / "asr_cuda_hien_hanh.json"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(
        json.dumps(fx.sach_de_cong_bo(ra), ensure_ascii=False, indent=2),
        encoding="utf-8")

    assert "cpu" in ra["buoc"] and "cuda" in ra["buoc"]


def test_bao_cao_ASR_CUDA_noi_ro_no_HONG_o_dau(bc):
    """⛔ Mot mon no duoc dong lai thi phai dong bang mot cau tra loi, khong bang
    mot cau "da xem xet".

    Bao cao phai chi ra duong CPU chay duoc, va neu duong CUDA hong thi hong o
    BUOC nao kem thong bao loi — do la thu bien mot trieu chung thanh mot viec
    sua duoc.
    """
    if not BAO_CAO_ASR.exists():
        pytest.skip("chua co bao cao ASR/CUDA")
    b = json.loads(BAO_CAO_ASR.read_text(encoding="utf-8"))
    cpu = b["buoc"].get("cpu") or {}
    assert cpu.get("so_doan", 0) > 0, f"duong CPU khong chep duoc loi nao: {cpu}"
    cuda = b["buoc"].get("cuda") or {}
    if "loi_chay" in cuda or "loi_nap" in cuda:
        assert (cuda.get("loi_chay") or cuda.get("loi_nap")).strip(), cuda
    else:
        assert cuda.get("so_doan", 0) > 0, cuda
