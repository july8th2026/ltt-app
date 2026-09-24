"""Barrier (`shouldReleaseBarrier` PORT) · `core.join` · `core.foreach`.

## 🔴 LUẬT SÀN: MỘT BARRIER ĐÃ NIÊM PHONG **LUÔN LUÔN** MỞ KHI HẾT TÍN HIỆU CHỜ

Nguồn — `activepieces/activepieces@17e2ac0b`,
`brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`:

    "Release is an **unconditional floor rule**: a sealed barrier releases once
     no signal is still `PENDING`. **No configuration can produce a hang**;
     `policy` only ever releases *sooner* — `requiredSuccesses` (K-of-N
     approvals) and `releaseOnFirstFailure` (veto)."

và hàm thật (`packages/core/execution/src/lib/flow-run/waitpoint/index.ts`):

    if (policy?.releaseOnFirstFailure && UNFAVOURABLE.some(s => countOf(s) > 0)) return true
    if (!isNil(policy?.requiredSuccesses) && countOf(SUCCEEDED) >= policy.requiredSuccesses) return true
    if (!sealed) return false
    return countOf({ counts, status: PENDING }) === 0

🔴 **`cho_doi.da_mo` của ta THIẾU đúng hai dòng cuối**, và chỗ thiếu ấy là một
**TREO THẬT**: với `required_successes = 2`, nếu cả ba nhánh đã báo về nhưng chỉ
một nhánh `SUCCEEDED`, hàm trả `False` **mãi mãi** — không còn tín hiệu nào sẽ
tới nữa. Run đứng tới hạn `TRAN_RUN` 20 giờ với tiền vẫn bị giữ.

Khác biệt thứ hai: tập "tín hiệu xấu" của họ có `NOT_DISPATCHED`, của ta thì
không — nên một nhánh **sẽ không bao giờ gửi gì** không kích hoạt được veto.

## Phép này KHÔNG phủ cái gì

Thân `foreach` ở đây chỉ gồm node **inline**. Thân có node job đi qua run con
(`body_workflow`, spec §5.9) — Task 7. Không chạy trên PostgreSQL thật (Task 8).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


# ── PORT `shouldReleaseBarrier`: hàm THUẦN, đo không cần CSDL ────────────────

def _dem(**kw) -> dict:
    return dict(kw)


def test_port_luat_san_barrier_niem_phong_het_PENDING_thi_MO():
    from platform_core.workflow.join import nen_mo_barrier
    assert nen_mo_barrier(sealed=True, dem=_dem(SUCCEEDED=2, FAILED=1))
    assert not nen_mo_barrier(sealed=True, dem=_dem(SUCCEEDED=2, PENDING=1))
    assert not nen_mo_barrier(sealed=False, dem=_dem(SUCCEEDED=2))


def test_port_KHONG_CAU_HINH_NAO_GAY_TREO():
    """⭐ Chính câu quyết định 000015 viết: *"No configuration can produce a hang"*.

    `required_successes = 2` mà chỉ 1 thành công, và **không còn tín hiệu nào
    đang chờ** ⇒ vẫn phải mở. Luật sàn đứng SAU policy, không bị policy nuốt.
    """
    from platform_core.workflow.join import nen_mo_barrier
    assert nen_mo_barrier(sealed=True, can_thanh_cong=2,
                          dem=_dem(SUCCEEDED=1, FAILED=2))


def test_port_policy_chi_mo_SOM_HON():
    from platform_core.workflow.join import nen_mo_barrier
    # N-of-M: đủ N là mở ngay, chưa cần niêm phong.
    assert nen_mo_barrier(sealed=False, can_thanh_cong=2,
                          dem=_dem(SUCCEEDED=2, PENDING=5))
    assert not nen_mo_barrier(sealed=False, can_thanh_cong=3,
                              dem=_dem(SUCCEEDED=2, PENDING=5))


@pytest.mark.parametrize("xau", ["FAILED", "CANCELLED", "NOT_DISPATCHED"])
def test_port_veto_tinh_ca_NOT_DISPATCHED(xau):
    """`UNFAVOURABLE_SIGNAL_STATUSES` của họ có `NOT_DISPATCHED`; của ta thì chưa.

    Một nhánh **sẽ không bao giờ gửi gì** là một nhánh đã hỏng theo đúng nghĩa
    veto quan tâm — coi nó là "đang chờ" là treo vĩnh viễn (`cho_doi._DA_XONG`
    đã nhận ra điều đó cho luật ALL, nhưng veto thì bỏ sót).
    """
    from platform_core.workflow.join import nen_mo_barrier
    assert nen_mo_barrier(sealed=False, mo_khi_hong_dau_tien=True,
                          dem={xau: 1, "PENDING": 9})


def test_port_khong_co_tin_hieu_nao_va_da_niem_phong_thi_MO():
    """Barrier rỗng đã niêm phong: không có gì để chờ ⇒ mở. (Ca biên của họ.)"""
    from platform_core.workflow.join import nen_mo_barrier
    assert nen_mo_barrier(sealed=True, dem={})


# ── Cùng luật, nhưng đi qua CSDL thật ───────────────────────────────────────

def _wp(db, **kw):
    from platform_core.workflow import cho_doi
    return cho_doi.tao_waitpoint(db, run_id="r1", owner_id="u1",
                                 kind="BARRIER", **kw)


def test_doi_chung_join_ALL_van_cho_khi_thieu_mot_nhanh(db):
    """Đối chứng: nếu phép này đỏ thì luật mới đang mở barrier quá sớm."""
    from platform_core.workflow import cho_doi, join
    wp = join.tao(db, run_id="r1", owner_id="u1", che_do="ALL", so_nhanh=3)
    for i in range(2):
        cho_doi.ghi_tin_hieu(db, wp.id, seq=i, status="SUCCEEDED")
    assert cho_doi.da_mo(db, wp.id) is False


def test_join_N_OF_M_khong_du_N_nhung_het_nhanh_thi_VAN_MO(db):
    """🔴 Đây là cái TREO. Ba nhánh đã báo, chỉ 1 thành công, `can=2`."""
    from platform_core.workflow import cho_doi, join
    wp = join.tao(db, run_id="r1", owner_id="u1", che_do="N_OF_M",
                  so_nhanh=3, can=2)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="FAILED")
    assert cho_doi.da_mo(db, wp.id) is False      # con mot nhanh chua bao
    cho_doi.ghi_tin_hieu(db, wp.id, seq=2, status="FAILED")
    assert cho_doi.da_mo(db, wp.id) is True       # het nhanh => MO, khong treo


def test_join_ANY_mo_ngay_khi_mot_nhanh_xong(db):
    from platform_core.workflow import cho_doi, join
    wp = join.tao(db, run_id="r1", owner_id="u1", che_do="ANY", so_nhanh=3)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    assert cho_doi.da_mo(db, wp.id) is True


def test_dem_tin_hieu_la_MOT_cau_gom_nhom(db):
    """⭐ 000015: *"one `GROUP BY status` replaces up to three round-trips"*.

    ⛔ Và không chỉ để nhanh: `da_mo` cũ nạp **mọi hàng** tín hiệu vào bộ nhớ.
       Với một barrier 10 000 nhánh (con số họ khai là có thật) đó là 10 000
       đối tượng ORM cho một câu trả lời `bool`.
    """
    from sqlalchemy import event
    from platform_core.workflow import cho_doi, join
    wp = join.tao(db, run_id="r1", owner_id="u1", che_do="ALL", so_nhanh=2)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    db.flush()
    cau: list[str] = []

    def _ghi(conn, cursor, stmt, params, ctx, many):
        if "waitpoint_signal" in stmt:
            cau.append(stmt)

    event.listen(db.get_bind(), "before_cursor_execute", _ghi)
    try:
        cho_doi.da_mo(db, wp.id)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", _ghi)
    assert len(cau) == 1, cau
    assert "count" in cau[0].lower() and "group by" in cau[0].lower()


# ── `core.foreach` / `core.foreach_end` / `core.join` ───────────────────────

def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


@pytest.fixture()
def lam(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 10000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"t{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"k{dem['n']}")
        return run
    return _lam


def _chay(db, run):
    from platform_core.workflow import dong_co
    return dong_co.xu_ly_run(db, run.id, cong_cu=CC)


def _ra(db, run, nid):
    from platform_core.workflow import thi_hanh
    return thi_hanh.anh_chup_hien_tai(db, run.id, nid).output_ref


def test_foreach_chay_het_moi_phan_tu_va_gom_dung_THU_TU(db, lam):
    run = lam([_core("f", "foreach", items="[10, 20, 30]", max_items=5),
               _core("x", "transform", gia_tri="loop.item * 2"),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "x"), _canh("x", "fe")])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "fe")["results"] == [20, 40, 60]
    assert _ra(db, run, "fe")["errors"] == []


def test_foreach_vuot_max_items_bi_tu_choi_TRUOC_khi_chay(db, lam):
    """`foreach.VuotTran`: *"Ném TRƯỚC khi chạy, không dừng giữa chừng."*"""
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    run = lam([_core("f", "foreach", items="[1, 2, 3]", max_items=2),
               _core("x", "transform", gia_tri="loop.item"),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "x"), _canh("x", "fe")])
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "f") == "FAILED"
    assert "vuot_max_items" in thi_hanh.anh_chup_hien_tai(db, run.id, "f").error


def test_foreach_loop_index_va_total_co_mat_trong_than(db, lam):
    run = lam([_core("f", "foreach", items='["a", "b"]', max_items=5),
               _core("x", "transform",
                     gia_tri='loop.item + ":" + to_string(loop.index) '
                             '+ "/" + to_string(loop.total)'),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "x"), _canh("x", "fe")])
    _chay(db, run)
    assert _ra(db, run, "fe")["results"] == ["a:0/2", "b:1/2"]


def test_loop_KHONG_TON_TAI_ngoai_than_foreach(db, lam):
    """`moi_truong_wf`: *"đọc `loop.item` ngoài thân ForEach phải báo **không có
    `loop`**, chứ không phải `loop` không có khoá `item`"*."""
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    run = lam([_core("x", "transform", gia_tri="loop.index")], [])
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "x") == "FAILED"
    loi = thi_hanh.anh_chup_hien_tai(db, run.id, "x").error
    assert "bieu_thuc_loi" in loi and "loop" in loi


@pytest.mark.parametrize("cach,tt_f,tt_fe", [
    ("skip", "SUCCEEDED", "SUCCEEDED"),
    ("collect", "SUCCEEDED", "SUCCEEDED"),
    # ⛔ `fail`: CHÍNH node `foreach` hỏng, và `foreach_end` SKIPPED theo luật
    #    lan truyền §5.5 — nó không "hỏng", nó **không còn đường nào tới**.
    ("fail", "FAILED", "SKIPPED"),
])
def test_on_item_error_ba_cach(db, lam, cach, tt_f, tt_fe):
    from platform_core.workflow import may_trang_thai as mtt
    run = lam([_core("f", "foreach", items="[1, 0, 3]", max_items=5,
                     on_item_error=cach),
               # Phần tử `0` ⇒ chia cho 0 ⇒ vòng đó hỏng. Hai phần tử kia ra
               # chính nó, nên `results` nói rõ vòng nào đã bị bỏ.
               _core("x", "transform",
                     gia_tri="loop.item / loop.item * loop.item"),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "x"), _canh("x", "fe")])
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "f") == tt_f
    assert mtt.trang_thai_node(db, run.id, "fe") == tt_fe
    if tt_fe == "SUCCEEDED":
        assert _ra(db, run, "fe")["results"] == [1, 3]
        assert len(_ra(db, run, "fe")["errors"]) == (1 if cach == "collect"
                                                     else 0)


def test_than_co_node_JOB_bi_tu_choi_luc_publish_voi_cau_ro(db, lam):
    """⛔ Từ chối, đừng chạy nửa vời. Thân có node job đi qua run con (§5.9,
    `body_workflow`) — Task 7. Nói thẳng ra thay vì treo lúc chạy."""
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich) as e:
        lam([_core("f", "foreach", items="[1]", max_items=5),
             {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
              "data": {"tool": "text.chat", "params": {}}},
             _core("fe", "foreach_end", foreach="f")],
            [_canh("f", "a"), _canh("a", "fe")])
    assert e.value.ma == "than_foreach_co_node_job"


def test_foreach_thieu_foreach_end_bi_tu_choi_luc_publish(db, lam):
    from platform_core.workflow.bao_gia import KhongBaoGiaDuoc
    with pytest.raises(KhongBaoGiaDuoc):
        lam([_core("f", "foreach", items="[1]", max_items=5)], [])


def test_wakeup_trong_than_foreach_khoa_theo_DUONG_THI_HANH(db, lam):
    """Task 1 nối vào Task 5: `thu_lai.hen` trong thân phải mang `(vòng, chỉ số)`.

    Ở đây đo phần đo được hôm nay: `nut_loi.foreach.ngu_canh_vong` trả đúng bộ
    `(tên vòng, chỉ số)` mà `danh_thuc.duong_thi_hanh` cần.
    """
    from platform_core.workflow import danh_thuc
    from platform_core.workflow.nut_loi import vong_lap
    g = {"nodes": [{"id": "f", "type": "core.foreach"},
                   {"id": "x", "type": "core.transform"},
                   {"id": "fe", "type": "core.foreach_end",
                    "params": {"foreach": "f"}}],
         "edges": [{"source_node": "f", "target_node": "x"},
                   {"source_node": "x", "target_node": "fe"}],
         "thu_tu": ["f", "x", "fe"]}
    assert vong_lap.than_cua(g) == {"f": ("fe", ("x",))}
    assert danh_thuc.duong_thi_hanh("x", vong=(("f", 2),)) == "f:2/x"


# ── core.join ───────────────────────────────────────────────────────────────

def test_join_node_ALL_cho_moi_nhanh(db, lam):
    from platform_core.workflow import may_trang_thai as mtt
    run = lam([_core("i", "if", dieu_kien="true"),
               _core("a", "transform", gia_tri="1"),
               _core("b", "transform", gia_tri="2"),
               _core("j", "join", che_do="ALL")],
              [_canh("i", "a", kind="CONTROL", condition="true"),
               _canh("i", "b", kind="CONTROL", condition="true"),
               _canh("a", "j"), _canh("b", "j")])
    assert _chay(db, run) == "SUCCEEDED"
    assert mtt.trang_thai_node(db, run.id, "j") == "SUCCEEDED"


def test_join_node_ANY_chay_ngay_khi_MOT_nhanh_toi(db, lam):
    """`ANY` hạ NGƯỠNG READY, và ngưỡng ấy sống ở `dong_co._lan_truyen`.

    Nhánh `false` của `if` chết hẳn; với `ALL` thì join SKIPPED theo. Với `ANY`
    một nhánh sống là đủ — và nhánh chết KHÔNG được kéo join đi theo nó.
    """
    from platform_core.workflow import may_trang_thai as mtt
    run = lam([_core("i", "if", dieu_kien="true"),
               _core("a", "transform", gia_tri="1"),
               _core("b", "transform", gia_tri="2"),
               _core("j", "join", che_do="ANY")],
              [_canh("i", "a", kind="CONTROL", condition="true"),
               _canh("i", "b", kind="CONTROL", condition="false"),
               _canh("a", "j"), _canh("b", "j")])
    assert _chay(db, run) == "SUCCEEDED"
    assert mtt.trang_thai_node(db, run.id, "b") == "SKIPPED"
    assert mtt.trang_thai_node(db, run.id, "j") == "SUCCEEDED"


def test_doi_chung_join_ALL_thi_nhanh_chet_KEO_join_di_theo(db, lam):
    """Đối chứng của phép trên: cùng đồ thị, đổi mỗi `che_do` ⇒ kết quả khác."""
    from platform_core.workflow import may_trang_thai as mtt
    run = lam([_core("i", "if", dieu_kien="true"),
               _core("a", "transform", gia_tri="1"),
               _core("b", "transform", gia_tri="2"),
               _core("j", "join", che_do="ALL")],
              [_canh("i", "a", kind="CONTROL", condition="true"),
               _canh("i", "b", kind="CONTROL", condition="false"),
               _canh("a", "j"), _canh("b", "j")])
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "j") == "SKIPPED"
