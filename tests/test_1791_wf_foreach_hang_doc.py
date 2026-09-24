"""`foreach` đọc bao nhiêu HÀNG mỗi vòng động cơ — hồi quy `O(N²/P)`.

🔴 SỐ ĐO CÓ THẬT (làn p3b, PostgreSQL thật —
   `docs/superpowers/reports/p3b-do-tai/report.md`)

| N | P | tổng hàng `foreach_muc` đọc | giây |
|---|---|---|---|
| 10 | 8 | 40 | 0,35 |
| 100 | 8 | 1 500 | 2,67 |
| 1000 | 8 | **127 000** | 31,67 |

Dự đoán `N²/P` = 125 000, đo được 127 000. Nguyên nhân:
`nut_loi/vong_lap.py::_muc_theo_chi_so` tải **toàn bảng** mỗi tick rồi bỏ
`xong` bằng Python. Trần `max_items ≤ 1000` hôm nay mất ~32 giây bookkeeping
**thuần** cho MỘT run.

## ⛔ VÌ SAO PHÉP NÀY ĐẾM **HÀNG**, KHÔNG ĐẾM **CÂU SQL**

Cũng từ báo cáo đó: số câu SQL mỗi tick **gần như không đổi theo N**
(226 → 409, ổn định qua cả ba mức). Một phép kiểm kiểu *"số truy vấn không
tăng ⇒ ổn"* sẽ kết luận **không có vấn đề** — và sai. Thứ suy biến là số **hàng
ORM nạp** mỗi tick, không phải số câu.

## Phép này chốt HÌNH DẠNG, không chốt một con số

Số hàng đọc mỗi tick phải **không tăng theo N**. Có đối chứng hai chiều:

  - tăng N mà **số tick** phải tăng (nếu không, phép đo không hề chạy thêm
    vòng nào và "không tăng" là vô nghĩa);
  - và cách CŨ phải **đỏ** — `test_doi_chung_cach_cu_doc_ca_bang`.

⚠️ **Phép này KHÔNG trả lời**: thời gian thật trên PostgreSQL (ở đây là SQLite,
   và thân dùng job giả hoàn tất đồng bộ), cũng không phủ nhiều run song song.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 1,
                          returns={"text": "text"})}


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str) -> dict:
    return {"id": f"{a}-{b}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA",
            "condition": ""}


@pytest.fixture()
def lam(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 5_000_000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"hd{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"hd{dem['n']}")
        return run
    return _lam


# ── ĐỐI CHỨNG: cách CŨ thật sự đọc cả bảng ──────────────────────────────────

def test_doi_chung_cach_cu_doc_ca_bang(db):
    """⛔ `filter_by(vong_id=…).all()` trả về **N** hàng kể cả khi N−1 đã xong.

    Đây là đối chứng của cả tệp: nếu phép này không còn chứng minh được hình
    dạng `O(N)` thì mọi phép "không tăng theo N" phía dưới là xanh giả.
    """
    from platform_core.models import ForeachMuc
    from platform_core.workflow import foreach

    vong = foreach.mo_vong(db, run_id="r1", node_id="f1",
                           muc=list(range(50)), max_items=100)
    for i in range(49):
        foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": i})
    ca_bang = db.query(ForeachMuc).filter_by(vong_id=vong.id).all()
    assert len(ca_bang) == 50, "cach cu doc CA BANG du chi con 1 phan tu"


def test_muc_chua_xong_chi_doc_dung_so_hang_xin(db):
    from platform_core.workflow import foreach

    vong = foreach.mo_vong(db, run_id="r2", node_id="f1",
                           muc=list(range(50)), max_items=100)
    assert len(foreach.muc_chua_xong(db, vong, gioi_han=4)) == 4
    # …và đi tiếp bằng KEYSET (`chi_so` cuối đã xem), không bằng OFFSET.
    lo2 = foreach.muc_chua_xong(db, vong, sau_chi_so=3, gioi_han=4)
    assert [i for i, _v in lo2] == [4, 5, 6, 7]
    # Phần tử ĐÃ XONG không bao giờ quay lại — đó là toàn bộ điểm của bản sửa.
    for i in range(10):
        foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": i})
    assert [i for i, _v in foreach.muc_chua_xong(db, vong, gioi_han=3)] \
        == [10, 11, 12]
    # Hết phần tử ⇒ rỗng, không ném.
    assert foreach.muc_chua_xong(db, vong, sau_chi_so=999, gioi_han=3) == []


# ── HÌNH DẠNG: hàng đọc mỗi tick KHÔNG tăng theo N ──────────────────────────

def _do(db, lam, monkeypatch, *, n: int, p: int) -> dict:
    """Chạy một `foreach` N phần tử, thân là node JOB, đếm hàng đọc mỗi tick."""
    from platform_core import jobs
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import Job
    from platform_core.workflow import dong_co, foreach, tao_run
    from platform_core.workflow.nut_loi import vong_lap

    so: dict = {"tick": 0, "moi_tick": []}
    that = foreach.muc_chua_xong

    def dem(db_, vong, **kw):
        ra = that(db_, vong, **kw)
        so["moi_tick"][-1] += len(ra)
        return ra

    monkeypatch.setattr(vong_lap._foreach, "muc_chua_xong", dem)

    run = lam([_core("f", "foreach", items=f"range({n})", max_items=n,
                     parallelism=p),
               {"id": "x", "type": "tool", "position": {"x": 0, "y": 0},
                "data": {"tool": "text.chat", "params": {}}},
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "x"), _canh("x", "fe")])

    for _ in range(n * 4):
        so["moi_tick"].append(0)
        so["tick"] += 1
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        cho = db.query(Job).filter(
            Job.plan_id == run.id, Job.origin == ORIGIN_WORKFLOW,
            Job.job_type != tao_run.DONG_CO_JOB, Job.status == "queued").all()
        if not cho:
            break
        for j in cho:
            jobs.complete(db, j, {"text": "x"})
    return {"tick": so["tick"], "max_hang": max(so["moi_tick"]),
            "tong": sum(so["moi_tick"]), "run": run}


def test_hang_doc_moi_tick_KHONG_tang_theo_N(db, lam, monkeypatch):
    """Hai cỡ, **cả hai lớn hơn `LO_DOC`** — nếu không thì trần quan sát được
    chỉ là chính N, và phép đo nói về N chứ không về hình dạng."""
    from platform_core.workflow.nut_loi.vong_lap import LO_DOC

    nho = _do(db, lam, monkeypatch, n=2 * LO_DOC, p=2)
    to = _do(db, lam, monkeypatch, n=4 * LO_DOC, p=2)

    # ĐỐI CHỨNG 1 — N lớn hơn PHẢI chạy nhiều tick hơn. Không có vế này thì
    # "hàng đọc không tăng" có thể chỉ vì phép đo không hề chạy thêm vòng nào.
    assert to["tick"] > nho["tick"], (nho["tick"], to["tick"])

    # HÌNH DẠNG 1 — hàng đọc NHIỀU NHẤT trong một tick là một HẰNG, không phải
    # một hàm của N. ⛔ Không chốt một con số cụ thể: chốt rằng hai cỡ bằng nhau.
    assert to["max_hang"] == nho["max_hang"], (nho["max_hang"], to["max_hang"])
    # …và hằng ấy là trần đọc, không phải N.
    assert to["max_hang"] <= LO_DOC + 2, to["max_hang"]

    # HÌNH DẠNG 2 — công TRUNG BÌNH mỗi tick. Cách cũ cho đúng **N** ở đây
    # (`127 000 / 127 ≈ 1000` trong báo cáo p3b), nên đây là chỗ `O(N²/P)` hiện
    # ra rõ nhất: N gấp đôi ⇒ trung bình gấp đôi.
    #
    # ⚠️ Không đòi BẰNG NHAU tuyệt đối: mấy tick cuối đọc ít hơn cả lô (còn ít
    #    phần tử hơn `LO_DOC`), nên trung bình nhích lên khi phần đuôi chiếm tỉ
    #    lệ nhỏ hơn. Ngưỡng 1,5 tách dứt khoát hai giả thuyết — hằng ⇒ ≈ 1,0 ·
    #    tuyến tính ⇒ ≈ 2,0 — mà không chốt một con số nào.
    tb_nho = nho["tong"] / nho["tick"]
    tb_to = to["tong"] / to["tick"]
    assert tb_to < tb_nho * 1.5, (tb_nho, tb_to)


def test_foreach_job_van_chay_dung_sau_khi_doi_cach_doc(db, lam, monkeypatch):
    """⛔ Nhanh hơn mà sai thì không phải nhanh hơn: N job, đúng N kết quả."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import thi_hanh

    kq = _do(db, lam, monkeypatch, n=7, p=3)
    run = db.get(WorkflowRun, kq["run"].id)
    assert run.status == "SUCCEEDED", run.status
    ra = thi_hanh.anh_chup_hien_tai(db, run.id, "fe").output_ref
    assert len(ra["results"]) == 7 and ra["errors"] == []
