"""`core.wait` (webhook · event) và `core.human` — chờ TÍN HIỆU, không chờ đồng hồ.

Spec §5.7 (`WEBHOOK` · `EVENT` · `HUMAN`), §8.3 (route resume), §8.4 (nguồn sự
kiện trong phạm vi: **chỉ** `workflow.run.finished`).

## Nguồn — tra trước, không tự suy

- `activepieces#3798` *"Create Approval Link ⇒ Wait for Approval doesn't work
  when there's a step in between"*: định danh điểm chờ phải mang đủ ngữ cảnh.
  Ta lấy khoá từ `khoa_idem.khoa_cho` (đường thi hành), nên bài đó không tái
  diễn — và `test_human_TRONG_foreach_moi_vong_mot_nguoi_duyet` đo điều đó.
- `activepieces#14388` *"Support multiple pauses within a single step run"* —
  cùng họ.
- `activepieces#15626` *"Subflow INTERNAL_ERROR fails the waiting parent
  instantly, then BullMQ retries the same run 8 min later and its Return
  Response is dropped"*: mở một điểm chờ ĐÃ ĐÓNG phải là một **câu trả lời**
  (409), không phải một 200 nói dối. `test_gui_lai_vao_diem_cho_DA_DONG`.
- Flowise/Langflow HumanInput: resume bằng **API** + **hết hạn thì định
  tuyến**. Mặc định `reject` (spec §5.7) — ⛔ không `approve`.

## ⛔ Tệp này KHÔNG phủ

Bộ phát sự kiện **cross-workflow** của `trigger.event` (§8.4) — đó là T8. Ở đây
`core.wait mode=event` được hỏi **lười** trong `tiep_mot`, và phép kiểm nói
thẳng ra rằng nó quét `workflow_event` chứ không đi qua một con trỏ bền.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

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


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


@pytest.fixture()
def lam(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 100_000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"w{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"wk{dem['n']}")
        db.commit()
        return run
    return _lam


def _tt(db, run, nid, vong=()):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid, vong)


def _ra(db, run, nid, vong=()):
    from platform_core.workflow import thi_hanh
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid, vong)
    return dict(anh.output_ref or {}) if anh else {}


def _dong_ho(monkeypatch, giay: int) -> None:
    from platform_core.workflow import danh_thuc, dong_co, han_cho, noi_lai
    from platform_core.workflow.nut_loi import cho

    lech = timedelta(seconds=giay)

    def _moi():
        return datetime.now(timezone.utc).replace(tzinfo=None) + lech

    for mod in (cho, danh_thuc, dong_co, han_cho, noi_lai):
        monkeypatch.setattr(mod, "_bay_gio", _moi)


# ── `core.wait mode=webhook` ────────────────────────────────────────────────

def test_wait_webhook_phat_URL_va_token_MOT_LAN(db, lam):
    from platform_core.models import Waitpoint
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("w", "wait", mode="webhook")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "WAITING"
    ra = _ra(db, run, "w")
    wp = db.query(Waitpoint).filter_by(run_id=run.id, kind="WEBHOOK").one()
    assert ra["url"] == f"/hooks/wp/{wp.id}" and ra["token"]
    # ⛔ CSDL chỉ giữ bản BĂM. Token thô đọc lại được là một chìa khoá đã rò.
    assert wp.token_hash == noi_lai.bam_token(ra["token"])
    assert ra["token"] not in (wp.token_hash, wp.idempotency_key)


def test_wait_webhook_mo_bang_token_thi_chay_tiep(db, lam):
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("w", "wait", mode="webhook"),
               _core("s", "set", bien={"xong": "1"})],
              [_canh("w", "s")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    ra = _ra(db, run, "w")
    wp_id = ra["url"].rsplit("/", 1)[-1]

    assert noi_lai.mo_bang_token(db, wp_id, token="sai") is noi_lai.TOKEN_SAI
    assert noi_lai.mo_bang_token(db, wp_id, token=ra["token"],
                                 du_lieu={"than": {"ok": 1}}) is noi_lai.DA_MO
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "SUCCEEDED" and _tt(db, run, "s") == "SUCCEEDED"
    assert _ra(db, run, "w")["than"] == {"ok": 1}


def test_gui_lai_vao_diem_cho_DA_DONG(db, lam):
    """`activepieces#15626`: một lượt "thành công" cho một điểm chờ đã đóng là
    một câu nói dối — và nó che mất việc tín hiệu thật đã bị bỏ."""
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("w", "wait", mode="webhook")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    ra = _ra(db, run, "w")
    wp_id = ra["url"].rsplit("/", 1)[-1]
    assert noi_lai.mo_bang_token(db, wp_id, token=ra["token"]) is noi_lai.DA_MO
    assert noi_lai.mo_bang_token(db, wp_id,
                                 token=ra["token"]) is noi_lai.DA_DONG


def test_wait_HET_HAN_thi_FAIL_theo_mac_dinh(db, lam, monkeypatch):
    """Spec §5.7: *"`core.wait` mặc định `fail`"* — ⛔ không "coi như xong"."""
    from platform_core.workflow import dong_co

    run = lam([_core("w", "wait", mode="webhook", timeout_s=30)], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "WAITING"
    _dong_ho(monkeypatch, 31)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "FAILED"


# ── `core.wait mode=event` ─────────────────────────────────────────────────

def test_wait_event_khop_BO_LOC_thi_chay_tiep(db, lam):
    from platform_core.workflow import dong_co, su_kien

    run = lam([_core("w", "wait", mode="event",
                     loc="event.status == 'SUCCEEDED'")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "WAITING"

    # Sự kiện của một run KHÁC, KHÔNG khớp ⇒ vẫn chờ.
    khac = lam([_core("s", "set", bien={"a": "1"})], [])
    su_kien.ghi(db, khac.id, "WorkflowFailed", du_lieu={"status": "FAILED"})
    db.flush()
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "WAITING", "doi chung: bo loc phai loai duoc"

    su_kien.ghi(db, khac.id, "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    db.flush()
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "SUCCEEDED"
    assert _ra(db, run, "w")["event"]["run_id"] == khac.id


def test_wait_event_KHONG_nghe_su_kien_CUA_CHINH_MINH(db, lam):
    """⛔ Một run nghe chính nó là một vòng: `WorkflowStarted` của nó đã nằm
    trong bảng trước khi điểm chờ mở, và một `WorkflowCompleted` của nó thì
    không bao giờ tới khi nó đang chờ."""
    from platform_core.workflow import dong_co, su_kien

    run = lam([_core("w", "wait", mode="event")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    su_kien.ghi(db, run.id, "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    db.flush()
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "WAITING"


def test_wait_event_bo_loc_HONG_thi_FAILED_chu_khong_treo(db, lam):
    from platform_core.workflow import dong_co, su_kien

    run = lam([_core("w", "wait", mode="event", loc="event.khong_co_ham()")],
              [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    khac = lam([_core("s", "set", bien={"a": "1"})], [])
    su_kien.ghi(db, khac.id, "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    db.flush()
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "w") == "FAILED"


# ── `core.human` ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("quyet_dinh,chay,bo", [("approve", "a", "r"),
                                                ("reject", "r", "a")])
def test_human_hai_nhanh_deu_di_dung_duong(db, lam, quyet_dinh, chay, bo):
    """FLOW E: *"approve đi tiếp / reject đi nhánh khác"*."""
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("h", "human", cau_hoi="Duyet khong?"),
               _core("a", "set", bien={"da_duyet": "1"}),
               _core("r", "set", bien={"da_tu_choi": "1"})],
              [_canh("h", "a", kind="CONTROL", condition="approve"),
               _canh("h", "r", kind="CONTROL", condition="reject")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    ra = _ra(db, run, "h")
    wp_id = ra["url"].rsplit("/", 1)[-1]
    assert noi_lai.mo_bang_token(
        db, wp_id, token=ra["token"],
        du_lieu={"than": {"quyet_dinh": quyet_dinh}}) is noi_lai.DA_MO
    for _ in range(3):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, chay) == "SUCCEEDED"
    assert _tt(db, run, bo) == "SKIPPED"


def test_human_THIEU_quyet_dinh_bi_tu_choi_KHONG_mac_dinh_approve(db, lam):
    """⛔ Không có mặc định. Một workflow duyệt-trước-khi-đăng mà tự duyệt khi
    người gửi không nói gì là đúng thứ `core.human` sinh ra để chặn."""
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("h", "human")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    ra = _ra(db, run, "h")
    wp_id = ra["url"].rsplit("/", 1)[-1]
    assert noi_lai.mo_bang_token(db, wp_id, token=ra["token"],
                                 du_lieu={"than": {}}) is noi_lai.DU_LIEU_SAI
    assert noi_lai.mo_bang_token(
        db, wp_id, token=ra["token"],
        du_lieu={"than": {"quyet_dinh": "co le"}}) is noi_lai.DU_LIEU_SAI
    assert _tt(db, run, "h") == "WAITING"


def test_human_HET_HAN_mac_dinh_la_REJECT(db, lam, monkeypatch):
    """Spec §5.7: *"`core.human` mặc định `reject`"* — và FLOW E đòi
    *"hết hạn ⇒ reject"*."""
    from platform_core.workflow import dong_co

    run = lam([_core("h", "human", timeout_s=60),
               _core("a", "set", bien={"da_duyet": "1"}),
               _core("r", "set", bien={"da_tu_choi": "1"})],
              [_canh("h", "a", kind="CONTROL", condition="approve"),
               _canh("h", "r", kind="CONTROL", condition="reject")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    _dong_ho(monkeypatch, 61)
    for _ in range(3):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "h") == "SUCCEEDED"
    assert _ra(db, run, "h")["quyet_dinh"] == "reject"
    assert _tt(db, run, "r") == "SUCCEEDED" and _tt(db, run, "a") == "SKIPPED"


# ── 🔴 Hai vòng `foreach` KHÔNG đụng nhau ──────────────────────────────────

def test_human_TRONG_foreach_moi_vong_mot_nguoi_duyet(db, lam):
    """⭐ `activepieces#3798` / `000015`: mỗi vòng phải có điểm duyệt RIÊNG.

    Đối chứng nằm ngay trong phép: mở điểm chờ của vòng 0 **không** được làm
    vòng 1 đi tiếp. Với khoá trần, vòng 1 sẽ thấy hàng `COMPLETED` của vòng 0
    và bỏ qua lần duyệt của chính nó.
    """
    from platform_core.models import Waitpoint
    from platform_core.workflow import dong_co, noi_lai

    run = lam([_core("f", "foreach", items="[1, 2]", max_items=5,
                     parallelism=2),
               _core("h", "human"),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "h"), _canh("h", "fe")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)

    wps = db.query(Waitpoint).filter_by(run_id=run.id, kind="HUMAN").all()
    assert len(wps) == 2, [w.idempotency_key for w in wps]
    assert _tt(db, run, "h", (("f", 0),)) == "WAITING"
    assert _tt(db, run, "h", (("f", 1),)) == "WAITING"

    # Duyệt ĐÚNG MỘT vòng…
    ra0 = _ra(db, run, "h", (("f", 0),))
    assert noi_lai.mo_bang_token(
        db, ra0["url"].rsplit("/", 1)[-1], token=ra0["token"],
        du_lieu={"than": {"quyet_dinh": "approve"}}) is noi_lai.DA_MO
    for _ in range(3):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)

    # …vòng kia VẪN phải chờ. Đây là câu trả lời cho "hai vòng có đụng nhau".
    assert _tt(db, run, "h", (("f", 0),)) == "SUCCEEDED"
    assert _tt(db, run, "h", (("f", 1),)) == "WAITING"
    assert run.status != "SUCCEEDED"

    ra1 = _ra(db, run, "h", (("f", 1),))
    assert ra1["token"] != ra0["token"], "hai vong phai co HAI token khac nhau"
    assert noi_lai.mo_bang_token(
        db, ra1["url"].rsplit("/", 1)[-1], token=ra1["token"],
        du_lieu={"than": {"quyet_dinh": "approve"}}) is noi_lai.DA_MO
    for _ in range(4):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert run.status == "SUCCEEDED"
