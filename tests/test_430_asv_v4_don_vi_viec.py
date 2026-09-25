"""Auto Scan Video V4 — `AsvWorkItem`: the checkpoint below a stage.

ADR-V4-002 D-V4-10/11/12. Three claims are worth testing and one of them is worth
testing hard:

**§1 identity** — `UNIQUE(run_id, stage, item_key)` is the load-bearing constraint.
     Without it "has segment 47 been synthesized" has more than one answer.

**§2 billing** — a stage that owns items must **not** also write its own
     `credit_actual`. 🔴 It fails **silently**: the run still finishes, the video is
     still correct, the internal cost ledger (`tong_da_dung`) still balances. Only
     the number is wrong. ⚠️ **Updated 2026-09-25**: since flat pricing
     (`gia.tinh_credit`, `test_3900_asv_gia_phang.py`) this is no longer a surface
     where the *customer* can be charged twice — `quyet_toan` prices from measured
     source duration, not from `credit_actual`. It is still the only surface for
     double-counting our own **internal cost** tracking (`kiem_tran_chi` and the
     ops view read `tong_da_dung`, which still enforces this — see
     `test_quyet_toan_di_qua_cung_mot_cua` for what changed on the customer side).

**§3 not a queue** — the positive half of D-V4-11. `test_427` proves the forbidden
     columns are absent; here we prove nothing *reads* this table to pick work.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import features, pipeline
from apps.auto_scan_video.tables import (ITEM_SUCCEEDED, AsvRun, AsvStage,
                                         AsvWorkItem)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Temp SQLite, cung khuon voi `tests/test_400`."""
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _run(db, *, owner="u1", held=1000) -> AsvRun:
    run = AsvRun(owner_id=owner, source_key="asv/u1/nguon/x.mp4",
                 settings={}, credit_held=held)
    db.add(run); db.flush()
    for g in pipeline.CHUOI:
        db.add(AsvStage(run_id=run.id, owner_id=owner, stage=g.ten))
    db.flush()
    return run


def _item(db, run, stage, key, *, credit=0, status=ITEM_SUCCEEDED) -> AsvWorkItem:
    it = AsvWorkItem(run_id=run.id, owner_id=run.owner_id, stage=stage,
                     item_key=key, status=status, credit_actual=credit)
    db.add(it); db.flush()
    return it


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Danh tinh
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_dong_cho_cung_mot_don_vi_viec_bi_CSDL_tu_choi(db):
    """Rang buoc chiu luc cua ca thiet ke.

    ⛔ Khong co no, hai worker cung sinh tieng doan 47 tao hai dong, va "doan 47
       xong chua" co hai cau tra loi. Do chinh la ly do `AsvStage` co
       `UNIQUE(run_id, stage)` tu ADR-001 D2 — day la cung mot bai hoc, mot cap
       thap hon.
    """
    from sqlalchemy.exc import IntegrityError

    run = _run(db)
    _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-047")
    with pytest.raises(IntegrityError):
        _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-047")


def test_cung_item_key_o_HAI_giai_doan_khac_nhau_thi_HOP_LE(db):
    """`item_key` duy nhat trong pham vi `(run, stage)`, khong duy nhat toan cuc.

    ⭐ Canh nay co that va se den o pha 12/15: canh so 3 co the vua la mot don vi
       cua `scene_analyze` vua la mot don vi cua `voice_synthesis`. Ep chung duy
       nhat toan cuc se buoc moi giai doan tu them tien to vao khoa — mot quy uoc
       khong ai cuong che va se bi quen.
    """
    run = _run(db)
    _item(db, run, pipeline.VOICE_SYNTHESIS, "3")
    _item(db, run, pipeline.CONTENT_PROCESS, "3")
    assert len(features.cac_don_vi(db, run.id)) == 2


def test_hai_lan_chay_khac_nhau_dung_chung_item_key_thi_HOP_LE(db):
    run_a, run_b = _run(db), _run(db)
    _item(db, run_a, pipeline.VOICE_SYNTHESIS, "seg-001")
    _item(db, run_b, pipeline.VOICE_SYNTHESIS, "seg-001")
    assert len(features.cac_don_vi(db, run_a.id)) == 1
    assert len(features.cac_don_vi(db, run_b.id)) == 1


def test_chu_so_huu_nam_o_COT_chu_khong_chi_trong_duong_dan(db):
    """I6 — mot phep tra "cua ai" phai la mot dieu kien WHERE."""
    run = _run(db, owner="u1")
    _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-001")
    cot = {c.name for c in AsvWorkItem.__table__.columns}
    assert "owner_id" in cot
    assert AsvWorkItem.__table__.c.owner_id.nullable is False


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Tien — be mat tinh hai lan
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_KHONG_co_don_vi_van_tu_ghi_chi_phi_nhu_cu(db):
    """Tuong thich nguoc: mot lan chay tao truoc pha 05 khong co dong item nao."""
    run = _run(db)
    st = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    st.credit_actual = 40
    db.flush()
    assert features.tong_da_dung(db, run) == 40


def test_giai_doan_CO_don_vi_thi_tong_la_tong_cua_cac_don_vi(db):
    run = _run(db)
    for i, gia in enumerate([10, 20, 30]):
        _item(db, run, pipeline.VOICE_SYNTHESIS, f"seg-{i}", credit=gia)
    assert features.tong_da_dung(db, run) == 60


def test_tron_HAI_kieu_giai_doan_trong_MOT_lan_chay(db):
    """Canh that: mot vai giai doan chia don vi, so con lai thi khong."""
    run = _run(db)
    st = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    st.credit_actual = 5
    for i, gia in enumerate([7, 8]):
        _item(db, run, pipeline.VOICE_SYNTHESIS, f"seg-{i}", credit=gia)
    db.flush()
    assert features.tong_da_dung(db, run) == 5 + 15


def test_giai_doan_vua_co_don_vi_vua_tu_ghi_chi_phi_thi_NEM(db):
    """🔴 Phep kiem quan trong nhat trong tep nay.

    Day la be mat duy nhat trong V4 de thu tien khach hai lan cho mot viec, va
    no hong **im lang**: lan chay van xong, video van dung, so du van can. Chi
    co con so la sai.

    ⛔ Cho nay nem thay vi tin vao ky luat. `_kiem_khong_tinh_hai_lan` chay ngay
       trong `tong_da_dung`, tuc **moi** duong doc so tien deu di qua no —
       khong co duong vong.
    """
    run = _run(db)
    _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-0", credit=10)
    st = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    st.credit_actual = 10        # <- dong lam hong moi thu
    db.flush()

    with pytest.raises(features.TinhHaiLan, match="VOICE|voice_synthesis"):
        features.tong_da_dung(db, run)


def test_quyet_toan_di_qua_cung_mot_cua(db):
    """`quyet_toan` tinh tien khach theo GIA PHANG (do dai nguon do duoc), ⛔
    KHONG con doc `tong_da_dung`/`credit_actual` cap don vi hay giai doan nua.

    ⭐ **Cap nhat 25/09/2026 (gia phang, xem `features.quyet_toan` va
       `tests/test_3900_asv_gia_phang.py`).** Ban truoc phep kiem nay chot
       `quyet_toan` phai NEM `TinhHaiLan` khi mot giai doan vua co don vi viec
       vua tu ghi `credit_actual` cua chinh no (§2 cua tep nay) — dung luc
       `quyet_toan` con doc `tong_da_dung` de ra so tien khach tra, nen no
       "thua ke" chot chong-tinh-hai-lan cua ham do.

       Tu gia phang: so tien khach tra den tu `gia.tinh_credit(giay)` (do dai
       NGUON, khong lien quan `credit_actual`), nen mot loi ghi so cai cap
       don vi/giai doan ⛔ KHONG con lam sai so khach tra qua `quyet_toan`
       nua — no khong con la "cung mot cua" voi `tong_da_dung`. `TinhHaiLan`
       van song va van chot: gio la mot bat bien CHI PHI NOI BO cua rieng
       `tong_da_dung` (doc no truc tiep — xem
       `test_giai_doan_vua_co_don_vi_vua_tu_ghi_chi_phi_thi_NEM`), khong con
       nam tren duong quyet toan khach.

    Phep kiem nay gio chot dieu NGUOC lai: du co loi ghi hai lan o cap giai
    doan, `quyet_toan` van chay xong KHONG nem, va so tien khach (`run.
    credit_actual` sau khi quyet toan) KHONG lien quan gi toi con so bi ghi
    hai lan do (10 + 10 = 20) — fixture nay khong co hien vat giao duoc, nen
    luat `N-21` (khong giao duoc thi khong thu) nha toan bo hold, tra ve 0.
    """
    run = _run(db)
    _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-0", credit=10)
    st = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    st.credit_actual = 10
    db.flush()

    from apps.auto_scan_video.tables import RUN_DONE
    ra = features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)  # khong nem

    assert ra.credit_actual == 0, (
        "khong hien vat giao duoc phai nha toan bo hold (N-21), khong phai "
        "tong da bi ghi hai lan (20)")


def test_dung_lai_mot_don_vi_hop_le_ton_0_credit(db):
    """G5/G12 — thu lai mot don vi con van tay khop khong duoc tinh them tien.

    ⚠️ O day ta chot **phep cong**, khong chot chinh sach dung lai (do la pha 15).
       Diem can co bay gio: tong khong doi khi khong co don vi nao chay lai.
    """
    run = _run(db)
    _item(db, run, pipeline.VOICE_SYNTHESIS, "seg-0", credit=10)
    truoc = features.tong_da_dung(db, run)

    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS, "seg-0")
    it.attempt = int(it.attempt) + 1      # chay lai, khong ghi them chi phi
    db.flush()

    assert features.tong_da_dung(db, run) == truoc == 10


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Khong phai hang doi — nua KHANG DINH cua D-V4-11
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_module_ASV_nao_doc_bang_item_de_quyet_dinh_chay_gi_tiep(db):
    """`test_427` chung minh cac COT cua mot hang doi vang mat. Day la nua kia.

    ⛔ Mot bang co the khong co mot cot `claimed_by` nao ma van bi dung nhu mot
       hang doi, neu co ai do truy van no de chon viec. Nen phep kiem nay chot
       rang `jobs.py` — noi duy nhat phat viec — **khong nhac** toi bang item.

    ⭐ `jobs._nop_giai_doan_san_sang` phat theo GIAI DOAN, va do phai giu nguyen:
       mot don vi viec la mot checkpoint cua giai doan, khong phai mot thu duoc
       xep hang doc lap.
    """
    import ast
    from pathlib import Path

    nguon = Path(__file__).resolve().parent.parent / "apps" / "auto_scan_video" / "jobs.py"
    cay = ast.parse(nguon.read_text(encoding="utf-8"))
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}

    assert "AsvWorkItem" not in ten, (
        "`jobs.py` nhac toi bang don vi viec — no la noi phat viec, va viec chi "
        "duoc phat theo GIAI DOAN (ADR-V4-002 D-V4-11)")
    assert "cac_don_vi" not in ten


def test_bang_item_KHONG_co_cot_nao_cua_mot_hang_doi():
    """Chot lai o day tren BANG THAT (test_427 chot tren ma nguon `tables.py`).

    ⭐ Hai duong do khac nhau: `test_427` doc AST nen bat duoc ca mot cot bi
       comment lai nham; cho nay doc metadata cua SQLAlchemy nen bat duoc mot cot
       duoc them qua `__table_args__` hay mot mixin — thu ma doc AST cua mot tep
       khong thay.
    """
    cot = {c.name for c in AsvWorkItem.__table__.columns}
    cam = {"claimed_by", "worker_id", "locked_by", "lease_until",
           "visible_at", "available_at", "priority", "heartbeat_at"}
    assert cot & cam == set()
