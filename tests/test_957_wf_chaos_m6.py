"""LTT WORKFLOW V2 · Đợt 3D — bộ chaos: `M6` 10/10 điểm giết → cùng kết quả.

Ngưỡng `M6` (`02 §M`): *"10/10 diem giet -> cung ket qua"*. Nó không hỏi
*"có khôi phục được không"* mà hỏi **"khôi phục có ra CÙNG một kết quả không"** —
câu thứ hai khó hơn hẳn, vì một hệ có thể khôi phục được mà vẫn thu tiền hai
lần, hoặc bỏ sót một bước.

🔴 Vì sao ngưỡng này có thật ở kho này: worker restart **13,6 lần/ngày**
   (`01 §A.6`). Một lượt chạy dài **sẽ** bị cắt ngang, không phải *có thể*.

## Mô hình giết ở đây

Đợt 3 chưa có scheduler, nên thứ đo được là **tầng bền vững**: kịch bản một run
gồm 9 bước, mỗi bước `commit()` riêng. "Giết ở bước k" = chạy 1..k, `rollback`
phần chưa commit, rồi **phát lại toàn bộ kịch bản từ đầu** — đúng thứ một worker
mới làm khi nhặt lại một run dở.

⭐ Bất biến phải giữ: trạng thái cuối, chi phí thật, và giữ chỗ — **giống hệt
   nhau ở cả 10 lượt** (9 điểm giết + 1 lượt không giết).

⛔ Và bài này bắt được đúng thứ khó thấy nhất: **phát lại không được cộng tiền
   lần nữa.** Bảng chỉ-thêm khiến sai lầm ấy dễ mắc — hàng cũ vẫn nằm đó.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf8.db').as_posix()}")
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


def _tao_run(db):
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Chaos")
    db.commit()
    v = dinh_nghia.xuat_ban(
        db, wf.id,
        {"schema_version": 1,
         "nodes": [{"id": "n0", "type": "llm.chat", "params": {}},
                   {"id": "n1", "type": "text.join", "params": {}}],
         "edges": []},
        created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual",
                         estimated_max=100)
    r.hold_id = "hold-chaos"
    db.commit()
    return r


def _kich_ban(db, run_id):
    """9 bước của một lượt chạy. Mỗi bước là một `commit()` riêng.

    Phát lại **toàn bộ** danh sách này phải luỹ đẳng: bước đã qua bị máy trạng
    thái từ chối (ghi `is_valid=False`, con trỏ đứng yên), bước chưa qua chạy.
    """
    from platform_core.workflow import may_trang_thai as mts

    return [
        lambda: mts.chuyen_run(db, run_id, sang="QUEUED"),
        lambda: mts.chuyen_run(db, run_id, sang="RUNNING"),
        lambda: mts.chuyen_node(db, run_id, "n0", sang="READY", mo_ta="r"),
        lambda: mts.chuyen_node(db, run_id, "n0", sang="QUEUED", mo_ta="q"),
        lambda: mts.chuyen_node(db, run_id, "n0", sang="RUNNING", mo_ta="run"),
        lambda: mts.chuyen_node(db, run_id, "n0", sang="SUCCEEDED",
                                mo_ta="xong", cost_credit=30),
        lambda: mts.chuyen_node(db, run_id, "n1", sang="READY", mo_ta="r"),
        lambda: mts.chuyen_node(db, run_id, "n1", sang="QUEUED", mo_ta="q"),
        lambda: mts.chuyen_node(db, run_id, "n1", sang="RUNNING", mo_ta="run"),
    ]


def _ket_thuc(db, run_id):
    from platform_core.workflow import may_trang_thai as mts

    mts.chuyen_node(db, run_id, "n1", sang="SUCCEEDED", mo_ta="xong",
                    cost_credit=12)
    mts.chuyen_run(db, run_id, sang="SUCCEEDED")
    db.commit()


def _chay_het(db, run_id):
    for buoc in _kich_ban(db, run_id):
        buoc()
        db.commit()
    _ket_thuc(db, run_id)


def _anh_chup_ket_qua(db, run_id) -> dict:
    """Thứ PHẢI giống nhau ở mọi điểm giết."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ket_so, may_trang_thai as mts

    run = db.get(WorkflowRun, run_id)
    db.refresh(run)
    return {
        "status": run.status,
        "actual_cost": run.actual_cost,
        "hold_id": run.hold_id,
        "da_ket_so": ket_so.da_ket_so(db, run_id),
        "n0": mts.trang_thai_node(db, run_id, "n0"),
        "n1": mts.trang_thai_node(db, run_id, "n1"),
    }


# ── M6 ────────────────────────────────────────────────────────────────────────

def test_M6_muoi_diem_giet_deu_cho_CUNG_MOT_ket_qua(db):
    """🔴 `M6`: 10/10 điểm giết → cùng kết quả."""
    goc = _tao_run(db)
    _chay_het(db, goc.id)
    chuan = _anh_chup_ket_qua(db, goc.id)

    lech = []
    for k in range(1, 10):
        r = _tao_run(db)
        buoc = _kich_ban(db, r.id)
        for i in range(k):                       # chay toi buoc k
            buoc[i]()
            db.commit()
        db.rollback()                            # <- "tien trinh chet"

        for buoc_moi in _kich_ban(db, r.id):     # worker moi PHAT LAI tu dau
            buoc_moi()
            db.commit()
        _ket_thuc(db, r.id)

        ra = _anh_chup_ket_qua(db, r.id)
        if ra != chuan:
            lech.append((k, ra))

    assert lech == [], f"ket qua lech o cac diem giet: {lech}\nchuan={chuan}"


def test_M6_phat_lai_KHONG_cong_tien_lan_nua(db):
    """⛔ Thứ khó thấy nhất: bảng CHỈ-THÊM khiến cộng đôi rất dễ mắc.

    Hàng cũ vẫn nằm đó sau khi phát lại, nên một phép tính "tổng mọi hàng" sẽ
    ra gấp đôi. Chỉ đếm hàng **hợp lệ** mới đúng — và bước đã qua khi phát lại
    bị máy trạng thái từ chối, nên nó ghi `is_valid=False`.
    """
    r = _tao_run(db)
    _chay_het(db, r.id)
    mot_lan = _anh_chup_ket_qua(db, r.id)["actual_cost"]

    r2 = _tao_run(db)
    _chay_het(db, r2.id)
    for buoc in _kich_ban(db, r2.id):            # phat lai LAN NUA sau khi xong
        buoc()
        db.commit()

    assert _anh_chup_ket_qua(db, r2.id)["actual_cost"] == mot_lan == 42


def test_M6_BO_DON_NEN_goi_lai_ket_so_khong_doi_gi(db):
    """⛔ Đường mà bản chaos đầu tiên của tôi BỎ SÓT.

    Đối chứng cho thấy: làm `ket_so` mất tính luỹ đẳng thì bộ chaos vẫn **xanh**
    — vì đường phát lại không bao giờ gọi `ket_so` lần hai (`chuyen_run` tới
    trạng thái kết thúc đã bị từ chối trước đó).

    Nhưng **bộ dọn nền thì có gọi** — đó chính là kiến trúc cũ mà `M10` sinh ra
    để thay, và nó vẫn còn đó trong lúc chuyển tiếp. Nên đường ấy phải được đo.
    """
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ket_so

    r = _tao_run(db)
    _chay_het(db, r.id)
    truoc = _anh_chup_ket_qua(db, r.id)
    row = db.get(WorkflowRun, r.id)
    dau_truoc = (row.ket_so_luc, row.ly_do_ket_so)

    for _ in range(3):                    # bo don nen quet ba luot
        assert ket_so.ket_so(db, r.id, ly_do="bo don nen") is False
        db.commit()

    db.refresh(row)
    # ⚠️ `_anh_chup_ket_qua` mot minh KHONG DU: no chi giu `da_ket_so` la mot
    #    bool, nen mot lan ket so chay lai tu dau van cho ra anh chup Y HET.
    #    Doi chung da chi ra dieu do — go tinh luy dang ma bai nay van xanh.
    #    `ket_so_luc` moi la thu doi khi ket so chay lai.
    assert _anh_chup_ket_qua(db, r.id) == truoc
    assert (row.ket_so_luc, row.ly_do_ket_so) == dau_truoc, (
        "dau ket so bi ghi de => `ket_so` da chay lai tu dau")


def test_M6_phat_lai_khong_lam_run_da_ket_thuc_song_lai(db):
    r = _tao_run(db)
    _chay_het(db, r.id)
    for buoc in _kich_ban(db, r.id):
        buoc()
        db.commit()

    ra = _anh_chup_ket_qua(db, r.id)
    assert ra["status"] == "SUCCEEDED" and ra["hold_id"] == ""


def test_M6_dau_vet_cua_lan_giet_KHONG_bi_xoa(db):
    """⭐ Phát lại không được **xoá lịch sử** — nó phải THÊM vào lịch sử.

    Đây là chỗ mô hình C trả công: sau một lần giết, ta đọc được cả đường đi
    thật lẫn những bước bị từ chối lúc phát lại. Một khối JSON sửa tại chỗ thì
    lần phát lại **ghi đè** mất dấu vết của lần chết.
    """
    from platform_core.models import NodeRunSnapshot

    r = _tao_run(db)
    buoc = _kich_ban(db, r.id)
    for i in range(7):
        buoc[i]()
        db.commit()
    db.rollback()
    for buoc_moi in _kich_ban(db, r.id):
        buoc_moi()
        db.commit()
    _ket_thuc(db, r.id)

    rows = db.query(NodeRunSnapshot).filter_by(run_id=r.id).all()
    assert any(s.is_valid for s in rows), "phai con duong di that"
    assert any(not s.is_valid for s in rows), (
        "phai con dau vet cua nhung buoc bi tu choi luc phat lai")
