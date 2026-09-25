"""Auto Scan Video V7 — may trang thai phai TU CHOI mot lan giao hang RONG (N-57).

## Ca that dang duoc khep o day

Lan `asv-g17` chay mot luot E2E that 49 phut tren phim khach: 12/12 giai doan
bao `SUCCEEDED`, QC bao `dat == True`, ma `render.outputs.khoa_asset` **RONG**
— khong mot tep nao duoc giao. May trang thai (`apps/auto_scan_video/jobs.py`,
`_advance`) van ket luan `RUN_DONE`.

**Nua TIEN da khep o `test_432`** (`CHI_THU_KHI_GIAO_DUOC` + `co_hien_vat_giao_duoc`):
khong hien vat thi thu 0, nha hold. Bai nay khep **nua may trang thai** — cho
mac dinh cua no la `RUN_DONE`, va khong gi ep no doc lai cau hoi "co hien vat
khong" truoc khi chot.

## Cau hoi bat buoc da tra loi TRUOC khi sua (⛔ khong doan)

Co che do san pham nao hop le ma dau ra KHONG co `.mp4` khong (vd: chi xuat
`.srt`, hoac mot preset chi ra am thanh)? — **KHONG.**

    * `pipeline.CHUOI` la MOT chuoi CO DINH (pipeline.py:145) — `RENDER` luon
      la mot giai doan bat buoc, khong co nhanh preset nao bo qua no.
    * `features.khoa_ket_qua` (features.py:1020) chi loc `.mp4` trong
      `render.outputs.khoa_asset`; `features.khoa_phu_de` (features.py:1034)
      doc lai chinh docstring cua no rang mot `.srt` khong kem `.mp4` la
      "dung hinh dang mot o chet" — luu vinh vien nhung khong ai tai ve duoc,
      vi man hinh khach chi co nut tai `.mp4` (`routes.tai_ket_qua`,
      routes.py:561, 404 khi `khoa_ket_qua` rong).

⇒ Khong co che do nao ma "khong .mp4" la hop le. Ep `error` khi khong co hien
  vat KHONG lam hong mot san pham dung — day la dieu kien DU cho MOI ban giao.

## Luat cho loi giai (⛔ khong tu viet lai)

`jobs._advance` phai goi thang `features.co_hien_vat_giao_duoc(db, run)` —
KHONG tu doc `outputs["khoa_asset"]` o day. Hai cau tra loi ("co hien vat de
thu tien" va "co hien vat de giao hang") phai la MOT phep tinh, khong phai
hai ban doc co the troi nhau.

Nhanh `giao_hang_rong` moi phai o CANH nhanh `hong` da co (mot giai doan
FAILED_TERMINAL), khong duoc GOP lam mot: mot run `error` vi mot giai doan
hong (loi co the cua du lieu khach) khac han mot run `error` vi giao hang
rong (khiem khuyet cua TA, chuoi da chay het). Nguoi doc `run.error` phai
phan biet duoc hai ca — do la ho loi "hai trang thai gop thanh mot gia tri"
da ghi trong so tay du an.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import features, jobs, pipeline
from apps.auto_scan_video.tables import (RUN_DONE, RUN_ERROR, RUN_RUNNING,
                                         STAGE_FAILED_TERMINAL,
                                         STAGE_SUCCEEDED, AsvRun, AsvStage)

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """SQLite tam, cung khuon voi `tests/test_454`."""
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _run_da_chay_het(db, *, owner="u1", khoa_asset=None) -> AsvRun:
    """Mot lan chay 12/12 giai doan `succeeded` — dung hinh ca that `asv-g17`.

    `khoa_asset=None` tai hien dung ca that: `render` SUCCEEDED nhung
    `outputs.khoa_asset` rong (khong truong `khoa_asset` nao ca). Truyen mot
    danh sach de mo phong lan giao hang co hien vat (doi chung).
    """
    run = AsvRun(owner_id=owner, source_key="asv/u1/nguon/x.mp4",
                 settings={}, credit_held=0, status=RUN_RUNNING)
    db.add(run)
    db.flush()
    for g in pipeline.CHUOI:
        outputs = None
        # 🔴 Hien vat giao duoc nam o `IMAGE_FINISH` (b4 hai giai doan, 25/09):
        #    `render` giao mot ban TRUNG GIAN — chua qua phep cat cua giai doan 2 —
        #    nen `features.khoa_ket_qua` doc `IMAGE_FINISH`. Gieo o `render` lam
        #    bai di duong "khong co hien vat" vi mot ly do KHAC han.
        if g.ten == pipeline.IMAGE_FINISH:
            outputs = ({"khoa_asset": list(khoa_asset)} if khoa_asset is not None
                      else {"dat": True})
        db.add(AsvStage(run_id=run.id, owner_id=owner, stage=g.ten,
                        status=STAGE_SUCCEEDED, fingerprint="", outputs=outputs))
    db.flush()
    return run


def _advance(db, run):
    return jobs._advance(db, run_id=run.id, owner_id=run.owner_id)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tai hien dung ca that: 12/12 SUCCEEDED + khoa_asset rong -> error
# ══════════════════════════════════════════════════════════════════════════════

def test_12_tren_12_succeeded_ma_khoa_asset_rong_thi_KHONG_duoc_done(db):
    """Dung hinh ca `asv-g17`: het chuoi, QC da gac (khong con khiem khuyet
    BIET duoc), ma khong co `.mp4` nao trong outputs cua `render`."""
    run = _run_da_chay_het(db, khoa_asset=[])

    assert len({s.status for s in features.cac_giai_doan(db, run)}) == 1
    assert all(s.status == STAGE_SUCCEEDED for s in features.cac_giai_doan(db, run))

    kq = _advance(db, run)

    assert kq["status"] == RUN_ERROR, (
        "12/12 giai doan SUCCEEDED nhung khong hien vat -> phai la error, "
        "khong duoc `done` (N-57)")
    assert run.status == RUN_ERROR
    assert not features.khoa_ket_qua(db, run), "khong duoc co khoa de tai ve"


def test_khong_co_truong_khoa_asset_nao_cung_bi_tu_choi(db):
    """Bien the khac cua RONG: `render` SUCCEEDED nhung `outputs` khong he co
    khoa `khoa_asset` (khong phai danh sach rong ma la thieu han truong)."""
    run = _run_da_chay_het(db, khoa_asset=None)
    kq = _advance(db, run)
    assert kq["status"] == RUN_ERROR


def test_error_noi_that_vi_sao_va_mang_tien_to_phan_biet_duoc(db):
    """`run.error` phai doc duoc: chuoi da chay het, QC da gac, ma khong hien
    vat -- va phai mang mot tien to RIENG voi nhanh `hong` (xem §3)."""
    run = _run_da_chay_het(db, khoa_asset=[])
    _advance(db, run)

    assert "giao_hang_rong" in run.error
    assert "khoa_asset" in run.error or ".mp4" in run.error


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Doi chung BAT BUOC: du hien vat thi VAN done qua chinh cong moi
# ══════════════════════════════════════════════════════════════════════════════

def test_du_hien_vat_thi_van_DONE_qua_dung_cong_moi(db):
    """Neu thieu bai nay, bai §1 chi chung minh cong chan duoc MOI THU — khong
    chung minh no phan biet duoc ban giao THAT voi ban giao rong."""
    run = _run_da_chay_het(
        db, khoa_asset=["asv/u1/run/long-tieng.mp4"])

    kq = _advance(db, run)

    assert kq["status"] == RUN_DONE, run.error
    assert run.status == RUN_DONE
    assert features.khoa_ket_qua(db, run).endswith(".mp4")


def test_nhieu_tep_trong_khoa_asset_ma_khong_co_mp4_van_bi_tu_choi(db):
    """⚠️ `khoa_ket_qua` loc rieng `.mp4` (docstring `features.py:1020`): mot
    danh sach KHONG rong nhung chi mang `.srt` van la mot ban giao rong o
    man hinh khach — `routes.tai_ket_qua` phuc vu `.mp4`, khong phuc vu `.srt`.
    """
    run = _run_da_chay_het(db, khoa_asset=["asv/u1/run/phu-de.srt"])
    kq = _advance(db, run)
    assert kq["status"] == RUN_ERROR, (
        "danh sach khoa_asset khong rong nhung khong co .mp4 -- van la "
        "khong hien vat de giao (khoa_ket_qua chi loc .mp4)")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Phan biet voi nhanh `hong` da co — khong duoc gop mot gia tri
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_HONG_van_di_nhanh_cu_khong_lan_voi_giao_hang_rong(db):
    """Mot giai doan FAILED_TERMINAL phai tiep tuc di nhanh `hong` (loi CO THE
    la du lieu khach) -- KHONG duoc trung tien to voi `giao_hang_rong` (khiem
    khuyet cua TA). Hai nhanh phai o CANH nhau, khong GOP lam mot."""
    run = AsvRun(owner_id="u1", source_key="asv/u1/nguon/x.mp4",
                settings={}, credit_held=0, status=RUN_RUNNING)
    db.add(run)
    db.flush()
    for i, g in enumerate(pipeline.CHUOI):
        if i == 0:
            db.add(AsvStage(run_id=run.id, owner_id="u1", stage=g.ten,
                            status=STAGE_FAILED_TERMINAL, fingerprint="",
                            error="tep nguon hong"))
        else:
            db.add(AsvStage(run_id=run.id, owner_id="u1", stage=g.ten,
                            status=STAGE_SUCCEEDED, fingerprint=""))
    db.flush()

    kq = _advance(db, run)

    assert kq["status"] == RUN_ERROR
    assert "giao_hang_rong" not in run.error, (
        "giai doan HONG khong duoc mang tien to cua nhanh giao-hang-rong")
    assert run.error.startswith(pipeline.CHUOI[0].ten + ":")


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Dung lai `co_hien_vat_giao_duoc` -- khong tu viet ban doc thu hai
# ══════════════════════════════════════════════════════════════════════════════

def test_jobs_KHONG_tu_doc_khoa_asset_ma_uy_quyen_cho_features(db):
    """🔑 Doc AST cua `jobs.py`: nhanh giao-hang-rong phai GOI
    `features.co_hien_vat_giao_duoc`, va tep nay ⛔ khong duoc tu import/doc
    `khoa_asset` truc tiep tu `outputs`. Mot ban doc thu hai ve "the nao la
    mot ban giao" la mot ban khai co the troi khoi ban dau (features.py:534).
    """
    cay = ast.parse((GOC / "apps" / "auto_scan_video" / "jobs.py")
                    .read_text(encoding="utf-8"))
    ten_goi = {n.func.attr for n in ast.walk(cay)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "co_hien_vat_giao_duoc" in ten_goi, (
        "_advance phai goi features.co_hien_vat_giao_duoc, khong tu doc lai")

    nguon = (GOC / "apps" / "auto_scan_video" / "jobs.py").read_text(encoding="utf-8")
    assert '"khoa_asset"' not in nguon and "'khoa_asset'" not in nguon, (
        "jobs.py khong duoc tu doc khoa 'khoa_asset' -- do la viec cua "
        "features.khoa_ket_qua/khoa_phu_de")


def test_ca_hai_cau_tra_loi_la_MOT_phep_tinh_tien_va_giao_hang(db):
    """`co_hien_vat_giao_duoc` (dung de THU TIEN, test_432) va cong moi trong
    `_advance` (dung de CHOT TRANG THAI) phai dong y voi nhau tren CUNG mot
    run: khong hien vat thi ca hai deu noi "khong"."""
    run = _run_da_chay_het(db, khoa_asset=[])
    assert features.co_hien_vat_giao_duoc(db, run) is False

    kq = _advance(db, run)
    assert kq["status"] == RUN_ERROR
    # Sau khi chot, cau tra loi cua ham thu tien van phai khop voi trang thai
    # vua chot -- khong chuong nhau.
    assert features.co_hien_vat_giao_duoc(db, run) is False
