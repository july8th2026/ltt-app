"""LTT WORKFLOW V2 · Đợt 3.1 — bốn hệ con còn lại, và CỜ bật/tắt.

`23_24 §6` khai **tám** hệ con. Bốn cái đã có (`snapshot` · `waitpoint` ·
`finally` · kho dữ liệu `foreach`). Bốn cái ở đây:

    enqueue   run moi -> hang doi              thay `_prepare_run`
    dequeue   ⭐ LOC THEO SUC CHUA TRUOC KHI CHON   thay `jobs.claim` (sua)
    attempt   submit job · nhan ket qua · thu lai   thay `_sync_children`
    ttl       het han run · waitpoint · artifact    thay cho rai rac

🔴 `27_29 §28` đặt tên Đợt 3 là *"Scheduler mới, **chạy sau cờ**"*. Cờ không
   phải một tuỳ chọn tiện nghi — nó là điều kiện để thứ này tồn tại cạnh đường
   cũ mà không ai phải chọn giữa hai đường trong lúc chưa đo được cái nào tốt
   hơn.

⛔ Ràng buộc của `3.1` (`G23`): **không I/O ngoài trong transaction**. Đây là
   lỗi LTT đang mắc mà chính `job_runner` đã cấm cho handler —
   `verifier.verify()` gọi model **bên trong** transaction, nên một lần model
   treo là một transaction treo, và một transaction treo giữ khoá hàng.
"""
from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timedelta, timezone

import pytest


def _bay_gio():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wfb.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def wf(db):
    from platform_core.workflow import dinh_nghia

    w = dinh_nghia.tao_workflow(db, owner_id="u1", name="DP")
    db.commit()
    v = dinh_nghia.xuat_ban(
        db, w.id,
        {"schema_version": 1,
         "nodes": [{"id": "n0", "type": "llm.chat", "params": {}}],
         "edges": []},
        created_by="u1")
    db.commit()
    return w, v


# ── CỜ ────────────────────────────────────────────────────────────────────────

def test_co_MAC_DINH_TAT(monkeypatch):
    """⛔ Mặc định TẮT. Một scheduler mới bật sẵn là một lần đổi đường chạy
    mà không ai bấm nút."""
    from platform_core.workflow import dieu_phoi

    monkeypatch.delenv(dieu_phoi.BIEN_CO, raising=False)
    assert dieu_phoi.dang_bat() is False


def test_co_bat_duoc_bang_bien_moi_truong(monkeypatch):
    from platform_core.workflow import dieu_phoi

    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    assert dieu_phoi.dang_bat() is True


def test_gia_tri_LA_bi_coi_la_TAT(monkeypatch):
    """`"0"`, `"false"`, `"khong"`, rác — tất cả là TẮT.

    Fail-closed: một giá trị không hiểu được nghĩa là người đặt nó không chắc
    họ đang bật cái gì.
    """
    from platform_core.workflow import dieu_phoi

    for gt in ("0", "false", "no", "", "  ", "bat_di"):
        monkeypatch.setenv(dieu_phoi.BIEN_CO, gt)
        assert dieu_phoi.dang_bat() is False, gt


def test_vong_dieu_phoi_KHONG_LAM_GI_khi_co_tat(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.delenv(dieu_phoi.BIEN_CO, raising=False)
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()

    assert dieu_phoi.mot_vong(db) == {"bo_qua": "co tat"}
    db.refresh(r)
    assert r.status == "queued", "co tat ma run van bi day di la sai"


# ── `enqueue` ────────────────────────────────────────────────────────────────

def test_enqueue_dua_run_moi_vao_hang_doi(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()

    assert dieu_phoi.enqueue(db, r.id) is True
    db.commit()
    db.refresh(r)
    assert r.status == "QUEUED"


def test_enqueue_LUY_DANG(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    dieu_phoi.enqueue(db, r.id)
    db.commit()

    assert dieu_phoi.enqueue(db, r.id) is False, "lan hai khong duoc lam gi"


# ── `dequeue` — ⭐ lọc sức chứa TRƯỚC khi chọn ───────────────────────────────

def test_dequeue_lay_run_dang_QUEUED(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    dieu_phoi.enqueue(db, r.id)
    db.commit()

    assert [x.id for x in dieu_phoi.dequeue(db)] == [r.id]


def test_dequeue_KHONG_lay_run_da_ket_thuc(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING", "SUCCEEDED"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    db.commit()

    assert dieu_phoi.dequeue(db) == []


def test_dequeue_BO_QUA_run_dang_cho_waitpoint_CHUA_mo(db, wf, monkeypatch):
    """⭐ Đây là *"lọc theo sức chứa TRƯỚC khi chọn"* ở tầng run.

    Nhặt một run rồi phát hiện nó đang chờ là **đúng khiếm khuyết** mà `F2` đo
    được ở tầng job: 92,2 % lượt nhặt kết thúc bằng "hoãn". Mỗi lượt nhặt-rồi-
    nhả tốn một vòng truy vấn và một khoảng chờ khách nhìn thấy.
    """
    from platform_core.workflow import cho_doi, dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING", "WAITING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    wp = cho_doi.tao_waitpoint(db, run_id=r.id, owner_id="u1", kind="JOB")
    cho_doi.chan_node(db, run_id=r.id, node_id="n0", waitpoint_id=wp.id)
    db.commit()

    assert dieu_phoi.dequeue(db) == [], "run dang cho thi dung nhat len"


def test_dequeue_LAY_LAI_ngay_khi_waitpoint_MO(db, wf, monkeypatch):
    from platform_core.workflow import cho_doi, dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING", "WAITING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    wp = cho_doi.tao_waitpoint(db, run_id=r.id, owner_id="u1", kind="BARRIER",
                               required_successes=1)
    cho_doi.chan_node(db, run_id=r.id, node_id="n0", waitpoint_id=wp.id)
    db.commit()
    assert dieu_phoi.dequeue(db) == []

    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    db.commit()
    assert [x.id for x in dieu_phoi.dequeue(db)] == [r.id]


def test_dequeue_ton_trong_gioi_han(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    for _ in range(9):
        r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual")
        db.commit()
        dieu_phoi.enqueue(db, r.id)
    db.commit()

    assert len(dieu_phoi.dequeue(db, gioi_han=4)) == 4


# ── `attempt` ────────────────────────────────────────────────────────────────

def test_attempt_dem_LUOT_THU_theo_node(db, wf, monkeypatch):
    """`attempt_number` phải tăng theo node, không theo run.

    Một run có node A thử ba lần và node B thử một lần; một bộ đếm chung nói
    "lượt thứ 4" cho B — và `cost_credit` ghi theo attempt sẽ vào sai chỗ.
    """
    from platform_core.workflow import dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    db.commit()

    assert dieu_phoi.attempt(db, r.id, "n0") == 1
    db.commit()
    assert dieu_phoi.attempt(db, r.id, "n0") == 2
    db.commit()
    assert dieu_phoi.attempt(db, r.id, "n1") == 1, "node khac phai dem RIENG"


# ── `ttl` ────────────────────────────────────────────────────────────────────

def test_ttl_dong_run_qua_han(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    r.hold_id = "h1"
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    r.started_at = _bay_gio() - timedelta(hours=48)
    db.commit()

    assert dieu_phoi.ttl(db)["run"] == 1
    db.commit()
    db.refresh(r)
    assert r.status == "TIMED_OUT"


def test_ttl_dong_run_qua_han_thi_KET_SO_luon(db, wf, monkeypatch):
    """⭐ `TIMED_OUT` cũng là trạng thái kết thúc ⇒ `finally` phải chạy.

    Đây đúng là hình dạng của `M10`: đường `SUCCEEDED` có người kết sổ, còn
    `TIMED_OUT` rơi vào bộ dọn nền và giữ chỗ nằm lại.
    """
    from platform_core.workflow import dieu_phoi, ket_so, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    r.hold_id = "h1"
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    r.started_at = _bay_gio() - timedelta(hours=48)
    db.commit()
    dieu_phoi.ttl(db)
    db.commit()
    db.refresh(r)

    assert r.hold_id == "" and ket_so.da_ket_so(db, r.id) is True


def test_ttl_KHONG_dong_run_con_trong_han(db, wf, monkeypatch):
    from platform_core.workflow import dieu_phoi, may_trang_thai, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    for s in ("VALIDATING", "QUEUED", "RUNNING"):
        may_trang_thai.chuyen_run(db, r.id, sang=s)
    db.commit()

    assert dieu_phoi.ttl(db)["run"] == 0


def test_ttl_dem_ca_waitpoint_va_artifact(db, wf, monkeypatch):
    from platform_core.workflow import artifact, cho_doi, dieu_phoi, thi_hanh

    w, v = wf
    monkeypatch.setenv(dieu_phoi.BIEN_CO, "1")
    r = thi_hanh.tao_run(db, workflow_id=w.id, version_id=v.id, owner_id="u1",
                         trigger_kind="manual")
    db.commit()
    wp = cho_doi.tao_waitpoint(db, run_id=r.id, owner_id="u1", kind="DELAY",
                               due_at=_bay_gio() - timedelta(hours=1))
    a = artifact.ghi_danh(db, owner_id="u1", backend="local", key="cu",
                          kind="image", ttl_class="EPHEMERAL")
    a.expires_at = _bay_gio() - timedelta(days=1)
    db.commit()

    ra = dieu_phoi.ttl(db)
    db.commit()
    assert ra["waitpoint"] == 1 and ra["artifact"] == 1
    db.refresh(wp)
    assert wp.status == "EXPIRED"


# ── 🔴 `G23`: KHÔNG I/O ngoài trong transaction — kiểm TĨNH ─────────────────

def test_G23_mo_dun_dieu_phoi_KHONG_import_thu_gi_goi_ra_NGOAI():
    """🔴 Lỗi LTT đang mắc mà chính `job_runner` đã cấm cho handler.

    `verifier.verify()` gọi model **bên trong** transaction ⇒ một lần model treo
    là một transaction treo, và một transaction treo **giữ khoá hàng**. Ở quy mô
    một suất `llm_remote` thì đó là cả hàng đợi đứng.

    Kiểm **tĩnh** (đọc AST) chứ không kiểm lúc chạy: một phép kiểm lúc chạy chỉ
    bắt được đường mà bài kiểm đi qua, còn cấm ở tầng import thì bắt **mọi**
    đường — kể cả đường chưa ai viết.
    """
    cam = {"requests", "httpx", "urllib", "urllib3", "subprocess", "socket",
           "aiohttp", "smtplib", "ftplib", "telnetlib"}
    tep = (pathlib.Path(__file__).resolve().parent.parent
           / "platform_core" / "workflow" / "dieu_phoi.py")
    cay = ast.parse(tep.read_text(encoding="utf-8"))

    thay = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            thay |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            thay.add(n.module.split(".")[0])

    assert not (thay & cam), (
        f"`dieu_phoi` import thu goi ra ngoai: {sorted(thay & cam)} — "
        "I/O ngoai KHONG duoc nam trong transaction (`G23`)")


def test_doi_chung_bo_do_G23_bat_duoc_mau_xau(tmp_path):
    """Đối chứng: bộ dò phải thật sự bắt được, không chỉ "không thấy gì"."""
    xau = tmp_path / "xau.py"
    xau.write_text("import requests\ndef f(): pass\n", encoding="utf-8")
    cay = ast.parse(xau.read_text(encoding="utf-8"))
    thay = {a.name.split(".")[0]
            for n in ast.walk(cay) if isinstance(n, ast.Import)
            for a in n.names}
    assert "requests" in thay
