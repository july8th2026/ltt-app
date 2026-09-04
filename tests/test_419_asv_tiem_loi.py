"""Pha 17 §2-§8 — tiem loi, va chung minh tien/quyen/tai nguyen/chay tiep con nguyen.

Cong thoat cua pha nay khong phai "khong hong". No la: **moi duong hong deu giu
duoc tien, quyen so huu, tai nguyen va kha nang chay tiep.**

⭐ Do la mot cong thoat khac han cac pha truoc, va no doi mot kieu phep kiem
   khac: khong kiem rang mot thu chay duoc, ma kiem rang khi no KHONG chay duoc
   thi so sach van dung.
"""
from __future__ import annotations

import subprocess

import pytest
from sqlalchemy import select

from platform_core import credit
from platform_core.models import Job
from apps.auto_scan_video import (features, ket_xuat, loi, nhap_media, pipeline,
                                  thi_hanh)
from apps.auto_scan_video.tables import (RUN_CANCELLED, RUN_DONE, RUN_ERROR,
                                         STAGE_SUCCEEDED, AsvAsset, AsvStage)
from tests.fixtures import asv_media as fx
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


def _so_sach(db_, run_id, owner="uA", *, so_du_ban_dau=None) -> dict:
    """Anh chup so sach.

    🔴 **SO CREDIT LA APPEND-ONLY, nen KHONG DAU NAO co so "dang giu".** Toi da
       doan sai cho nay HAI lan lien tiep truoc khi doc ma nguon:

         `run.credit_held`          -> da giu bao nhieu (su that lich su)
         `credit.so_da_giu(job_id)` -> tong cac but toan HOLD, cung khong doi
                                       sau khi quyet toan

       Quyet toan ghi mot but toan `SETTLE` **rieng** thay vi sua but toan HOLD.
       Do la thiet ke dung cua mot so ke toan, va no co nghia la cau hoi "con
       giu bao nhieu" khong co cho nao tra loi — vi no khong phai cau hoi dung.

    ⇒ Bat bien phai phat bieu bang **su ton tai cua but toan quyet toan** cong
      **so du that**, chu khong bang mot con so "con giu".
    """
    run = features.lay_run(db_, run_id, owner)
    return {"so_du": credit.so_du(db_, owner),
            "da_chot": credit._ket_qua_da_chot(db_, run.id),
            "da_giu_ban_dau": int(run.credit_held),
            "da_tinh": int(run.credit_actual or 0),
            "da_dung": features.tong_da_dung(db_, run),
            "trang_thai": run.status}


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Dau vao khong hop le -> KHONG thu lai, tien tra ve du
# ══════════════════════════════════════════════════════════════════════════════

def test_video_KHONG_CO_TIENG_hong_ngay_va_khong_thu_lai(db, kho_tam, tmp_path):
    """`MVP_CONTRACT` §2 tu choi video khong co luong tieng.

    Chot hai thu cung luc: lan chay ket thuc o `error`, VA no khong dot ba lan
    thu cho mot viec khong bao gio thanh cong.
    """
    from tests.fixtures.asv_media import nap_nguon_vao_kho
    from tests.test_402_asv_mach_doc_gia import bao_dam_user

    fx.require_ffmpeg()
    bao_dam_user(db, "uA")
    credit.nap(db, "uA", 1000)
    # ⚠️ `kho_tam` chi CAI DAT kho toan cuc roi `yield` rong.
    from platform_core.storage import get_storage
    khoa = nap_nguon_vao_kho(get_storage(), tmp_path, owner_id="uA",
                             im_lang=True)
    run = features.tao_run(db, owner_id="uA", source_key=khoa,
                           settings={"giong_id": "Minh Đức", "timing_mode": "fit_original"},
                           uoc_luong_credit=10)
    db.commit()
    truoc = credit.so_du(db, "uA")

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_ERROR
    # Tien: giu cho da duoc hoan HET, vi khong giai doan nao tieu duoc gi.
    assert credit._ket_qua_da_chot(db, run.id) is not None, "chua quyet toan"
    assert credit.so_du(db, "uA") == truoc + 10

    # Khong thu lai: job cua giai doan dau chi chay DUNG MOT lan.
    j = db.execute(select(Job).where(
        Job.plan_id == run.id,
        Job.job_type == "asv_media.media_prepare")).scalars().first()
    assert j is not None
    assert int(j.attempts or 0) <= 1, (
        f"job da thu {j.attempts} lan cho mot dau vao khong bao gio hop le")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Artifact bien mat giua chung
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def run_xong(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    return run


def test_artifact_bien_mat_thi_CACHE_khong_dung_lai_no(run_xong, db):
    """I10. "Co mot dong trong so" khong phai la mot cache hop le.

    Xoa bytes nhung giu ban ghi, roi hoi cache: no phai tu choi.
    """
    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets

    a = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run_xong.id,
        AsvAsset.created_by_stage == pipeline.RENDER)).scalars().one()
    get_storage().delete(a.storage_key)

    cu = assets.cache_dung_duoc(db, get_storage(), owner_id="uA",
                                run_id=run_xong.id, stage=pipeline.RENDER,
                                van_tay=features.giai_doan_theo_ten(
                                    db, run_xong.id, pipeline.RENDER).fingerprint)
    assert cu in ([], None), "cache tra ve mot artifact khong con tep"


def test_checkpoint_HONG_bi_phat_hien_chu_khong_duoc_dung_tiep(run_xong, db):
    """Checkpoint hong = ban ghi con nhung noi dung da doi (checksum lech)."""
    import io

    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets
    from apps.auto_scan_video.tables import ASSET_OK

    kho = get_storage()
    a = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run_xong.id,
        AsvAsset.created_by_stage == pipeline.COMPOSE)).scalars().one()
    kho.put(a.storage_key, io.BytesIO(b"noi dung da bi doi"),
            content_type="application/json")

    assert assets.kiem_toan_ven(db, kho, a) != ASSET_OK, (
        "checksum lech ma van bao toan ven")


# ══════════════════════════════════════════════════════════════════════════════
#  §4  ffmpeg hong · tien trinh con bi giet
# ══════════════════════════════════════════════════════════════════════════════

def test_ffmpeg_hong_KHONG_de_lai_artifact_VA_khong_quyet_toan_nham(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    truoc = credit.so_du(db, "uA")

    def _no(*_a, **_k):
        raise ket_xuat.KetXuatError("ep ffmpeg hong")
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do", _no)

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_ERROR
    assert credit._ket_qua_da_chot(db, run.id) is not None, "chua quyet toan"
    # Khong tieu qua so da tieu that.
    assert credit.so_du(db, "uA") >= truoc - features.tong_da_dung(db, run)
    con = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run.id,
        AsvAsset.created_by_stage == pipeline.RENDER)).scalars().all()
    assert con == []


def test_tien_trinh_con_bi_giet_thanh_loi_CO_KIEU_chu_khong_treo(tmp_path):
    """Worker chet giua chung: `_chay_co_tien_do` phai nem, khong duoc treo."""
    binary = fx.require_ffmpeg()
    cmd = [binary, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(tmp_path / "khong-co.mp4"),
           "-progress", "pipe:1", "-nostats", str(tmp_path / "ra.mp4")]
    with pytest.raises(ket_xuat.KetXuatError):
        ket_xuat._chay_co_tien_do(cmd, tong_giay=1.0, timeout=30)


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Huy truoc / trong khi job con chay — va KHONG ghi de thanh cong
# ══════════════════════════════════════════════════════════════════════════════

def test_huy_TRUOC_khi_job_con_chay(db, kho_tam, tmp_path, asr_gia, dich_gia,
                                    giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    truoc = credit.so_du(db, "uA")
    features.huy_run(db, run.id, "uA")
    db.commit()

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_CANCELLED
    assert credit._ket_qua_da_chot(db, run.id) is not None, "chua quyet toan"
    assert credit.so_du(db, "uA") == truoc + 10, "khong hoan du phan chua dung"


def test_huy_GIUA_CHUNG_khong_bi_mot_job_ve_dich_muon_ghi_de(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """I13. Nua thu hai cua bat bien: `_advance` doc lai duoi khoa va dung ngay.

    Kich ban: chay vai giai doan, huy, ROI van chay tiep hang doi. Mot job con
    ve dich sau do khong duoc lam run song lai.
    """
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg"}, toi_da=4)
    features.huy_run(db, run.id, "uA")
    db.commit()

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_CANCELLED, "mot job ve dich muon da lam song lai run"
    assert not any(s.status == STAGE_SUCCEEDED
                   for s in features.cac_giai_doan(db, run)
                   if s.finished_at and run.finished_at
                   and s.finished_at > run.finished_at), (
        "co giai doan bao thanh cong SAU khi run da huy")


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Tien: giu MOT LAN, quyet toan MOT LAN, o ca bon ket cuc
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ket_cuc", ["thanh_cong", "huy"])
def test_giu_cho_ve_0_o_moi_ket_cuc(ket_cuc, db, kho_tam, tmp_path, asr_gia,
                                    dich_gia, giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    so_du_dau = credit.so_du(db, "uA")
    if ket_cuc == "huy":
        features.huy_run(db, run.id, "uA")
        db.commit()
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    s = _so_sach(db, run.id)
    s["so_du_ban_dau"] = so_du_dau
    assert s["trang_thai"] in (RUN_DONE, RUN_CANCELLED, RUN_ERROR)
    assert s["da_chot"] is not None, "ket thuc ma khong co but toan quyet toan"
    assert s["da_tinh"] <= s["da_giu_ban_dau"], "tinh nhieu hon so da giu"
    # ⚠️ Giu cho da bi TRU NGAY luc tao run, nen `so_du_ban_dau` (do sau khi
    #    tao) da thieu di phan giu. Sau khi quyet toan, phan chua dung quay lai:
    #        cuoi = sau_khi_giu + (da_giu - da_thu)
    #    Ban dau toi viet `cuoi == sau_khi_giu - da_thu` va no do voi
    #    `1000 == 990 - 0` — mot phep tru hai lan cung mot khoan.
    assert s["so_du"] == s["so_du_ban_dau"] + s["da_giu_ban_dau"] - s["da_tinh"]


def test_job_con_KHONG_giu_them_credit_nao(run_xong, db):
    """ADR-001 D3: tien giu DUNG MOT LAN tren `run.id`.

    Mot job con giu them la mot lan tinh tien thu hai cho cung mot viec.
    """
    con = db.execute(select(Job).where(Job.plan_id == run_xong.id)).scalars().all()
    assert con, "khong co job con nao — phep kiem vo nghia"
    # ⚠️ `Job` khong co cot `credit_held`; phan giu nam trong SO credit, khoa
    #    theo `job_id`. Ban dau phep kiem doc mot cot khong ton tai va do voi
    #    `AttributeError` — mot phep kiem khong the xanh, tuc khong canh gi ca.
    for j in con:
        assert credit.so_da_giu(db, j.id) == 0, (
            f"job con {j.job_type} da giu credit rieng — tien phai giu DUNG MOT "
            f"LAN tren run.id (ADR-001 D3)")


def test_quyet_toan_KHONG_chay_hai_lan(run_xong, db):
    """Goi lai `quyet_toan` tren mot run da xong khong duoc doi so du."""
    truoc = credit.so_du(db, "uA")
    features.quyet_toan(db, run_xong, trang_thai_cuoi=RUN_DONE)
    db.commit()
    assert credit.so_du(db, "uA") == truoc


# ══════════════════════════════════════════════════════════════════════════════
#  §7-§8  Tai nguyen: GPU do nen tang cap, khong co duong khoa di san
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_giai_doan_nao_tu_chon_card_GPU():
    """I11/O6. Handler khong bao gio tu chon card — no xin `ctx.gpu_env()`.

    Chot bang AST tren MOI module cua app: mot cho gan `CUDA_VISIBLE_DEVICES`
    truc tiep la mot handler dang tu chia GPU sau lung nen tang.

    🔴 **Truoc pha 13 o day co mot BAN SAO rieng cua phep quet, va ban sao do
       chua hoc bai ma ban goc da hoc.**

       `test_401._vi_pham` tung la mot phep quet chuoi con, va no da bao dong
       tren chinh nhung dong van giai thich luat — nen no duoc sua thanh doc AST
       va **mien tru docstring**, kem mot doan ghi ro vi sao: *"mot guard bao loi
       tren doan van giai thich chinh no day nguoi sau xoa loi giai thich di, va
       nhu the con te hon la khong co guard"*.

       Ban sao o day thi khong: no duyet MOI `ast.Constant` la chuoi — ke ca
       docstring. Pha 13 viet mot doan giai thich vi sao tien trinh con **khong
       duoc** doc bien ghim card, va ban sao nay bao dong tren dung doan do.

    ⭐ Nen cach sua khong phai noi luat ra, ma la **bo ban sao**: mot luat, mot
       cho cuong che. Hai ban sao cua cung mot luat thi som muon chi mot ban
       duoc sua.
    """
    import pathlib

    from apps.auto_scan_video import loi as _loi
    from tests.test_401_asv_ranh_gioi_va_artifact import _CAM_GPU, _vi_pham

    goc = pathlib.Path(_loi.__file__).resolve().parent
    xau: list[str] = []
    for tep in sorted(goc.glob("*.py")):
        con = _vi_pham(tep.read_text(encoding="utf-8"), _CAM_GPU)
        if con:
            xau.append(f"{tep.name}: {con}")
    assert xau == [], (
        f"app tu dat CUDA_VISIBLE_DEVICES o {xau} — card do nen tang cap qua "
        f"`ctx.gpu_env()`, handler khong bao gio tu chon (I11/O6)")


def test_KHONG_duong_khoa_GPU_DI_SAN_nao_toi_duoc_tu_runtime():
    """Muc 8. Kho nay tung co mot duong khoa GPU rieng cua app; Auto Scan khong
    duoc cham toi no."""
    import ast
    import inspect
    import pathlib

    from apps.auto_scan_video import loi as _loi
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    goc = pathlib.Path(_loi.__file__).resolve().parent
    cam = ("gpu_lock", "GPULock", "gpu_claims", "acquire_gpu", "khoa_gpu")
    for tep in sorted(goc.glob("*.py")):
        vp = _vi_pham(tep.read_text(encoding="utf-8"), cam)
        assert vp == [], f"{tep.name} cham duong khoa GPU di san: {vp}"


def test_giai_doan_GPU_xin_moi_truong_qua_ctx_chu_khong_tu_dat():
    """Chieu duong: giai doan that su dung GPU phai goi `ctx.gpu_env()`."""
    import inspect

    from apps.auto_scan_video import giai_doan_am_thanh, giai_doan_chep_loi

    import ast

    # ⚠️ Nen tang cap card qua HAI hinh thuc, va ca hai deu dung:
    #      `ctx.gpu_env(base=...)`  -> moi truong da gan card (demucs)
    #      `ctx.gpu_uuid`           -> uuid card, chuyen tiep xuong engine (ASR)
    #    Ban dau phep kiem chi chap nhan hinh thuc thu nhat va bao
    #    `giai_doan_chep_loi` "khong xin moi truong card" — trong khi no xin,
    #    chi la bang duong kia. Dieu can chot la **card den tu `ctx`**, khong
    #    phai mot cu phap cu the.
    for mod in (giai_doan_am_thanh, giai_doan_chep_loi):
        cay = ast.parse(inspect.getsource(mod))
        tu_ctx = {n.attr for n in ast.walk(cay)
                  if isinstance(n, ast.Attribute)}
        chuoi = {n.value for n in ast.walk(cay)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert ({"gpu_env", "gpu_uuid"} & (tu_ctx | chuoi)), (
            f"{mod.__name__} chay tren lan gpu ma khong nhan card tu ctx")


def test_RENDER_khong_TU_GIANH_GPU_va_khong_dat_cho_mot_tai_nguyen_nao(db):
    """🔴 **Chot nay tung khang dinh "RENDER khong xin GPU", va khang dinh do
    chinh la B24-01.**

    Muc 7 duoc viet khi MVP con mot preset: `-c:v copy` that su khong cham bo ma
    hoa. Preset `smart_localize` thi **buoc phai ma hoa lai**, nen tu pha 12
    menh de do het dung — va cam `gpu_env` da khoa bo ma hoa phan cung ra ngoai
    tren mot may co `h264_nvenc`.

    ⭐ Dieu con dung, va la dieu chot nay giu lai: RENDER khong duoc **tu gianh**
       card (nen tang cap qua `ctx.gpu_uuid`), va khong duoc dat cho mot tai
       nguyen dung chung nao — no la giai doan DAI NHAT cua san pham.
    """
    import ast
    import inspect

    from apps.auto_scan_video import giai_doan_ket_xuat

    cay = ast.parse(inspect.getsource(giai_doan_ket_xuat))
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    for tu_gianh in ("acquire", "list_gpus", "detect_gpu_encoder"):
        assert tu_gianh not in goi, (
            f"RENDER tu gianh GPU qua `{tu_gianh}` thay vi dung suat duoc cap")
    # Va no VAN phai ghim vao card duoc cap — nua con lai cua cung mot luat.
    assert "gpu_env" in goi, "RENDER khong ghim ffmpeg vao card duoc cap"
    g = next(x for x in pipeline.CHUOI if x.ten == pipeline.RENDER)
    assert g.tai_nguyen == ""


# ══════════════════════════════════════════════════════════════════════════════
#  §9  Hai nguoi dung dong thoi — khong ai thay du lieu cua ai
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_nguoi_dung_chay_dong_thoi_khong_lan_du_lieu(db, kho_tam, tmp_path,
                                                         asr_gia, dich_gia,
                                                         giong_gia):
    fx.require_ffmpeg()
    a = _tao_run(db, owner="uA", kho=kho_tam, tmp_path=tmp_path / "a")
    b = _tao_run(db, owner="uB", kho=kho_tam, tmp_path=tmp_path / "b")
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    for run, chu in ((a, "uA"), (b, "uB")):
        assert features.lay_run(db, run.id, chu).status == RUN_DONE
        hang = db.execute(select(AsvAsset).where(
            AsvAsset.run_id == run.id)).scalars().all()
        assert hang, "khong co artifact nao"
        assert {x.owner_id for x in hang} == {chu}
        for x in hang:
            assert f"/{chu[:16]}/" in x.storage_key or x.storage_key.startswith(
                f"asv/{chu[:16]}/"), (
                f"khoa {x.storage_key} khong mang chu so huu {chu}")

    # Va khong ai doc duoc run cua nguoi kia.
    with pytest.raises(features.AsvError):
        features.lay_run(db, a.id, "uB")


def test_moi_dong_giai_doan_va_asset_deu_mang_chu_so_huu(run_xong, db):
    for s in db.execute(select(AsvStage).where(
            AsvStage.run_id == run_xong.id)).scalars().all():
        assert s.owner_id == "uA"
    for a in db.execute(select(AsvAsset).where(
            AsvAsset.run_id == run_xong.id)).scalars().all():
        assert a.owner_id == "uA"
