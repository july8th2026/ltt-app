# -*- coding: utf-8 -*-
"""FLOW A voi HTTP **THAT** tren PostgreSQL that — dieu kien ra cua P5 (§18.5).

## Khac gi `test_1787` (FLOW A cua P3)?

P3 chay FLOW A voi **http-mock**: mot tool registry gia, khong he ra mang
(`test_1787._app`). Do la dung voi P3 — no dang do NHANH RE, khong do HTTP.

Tep nay do phan P3 co y khong do:

- node **`core.http` that** trong do thi, chay het vong dong co, mo mot socket
  toi mot may chu HTTP **that** (cuc bo, cong 0);
- header `Authorization` den tu **kho credential**, khong tu `params` —
  tuc bi mat KHONG nam trong `workflow_version`;
- bi mat khong xuat hien trong `node_run_snapshot`, mot bang CHI-THEM (khong
  sua duoc, nen mot bi mat lot vao do la lot **vinh vien**);
- nhanh `false` van SKIPPED va **khong gui request nao** — phep dem cua may
  chu gia la thu chung minh dieu do, khong phai mot lap luan.

⚠️ PostgreSQL that, khong SQLite: `test_1720` da ghi lai ca `started_at` naive
   tren SQLite / aware tren PostgreSQL nem `TypeError` o production. Tep nay
   them mot ho nua vao cung nhom — `credential.dung_lan_cuoi` di vao cung phep
   so gio do.

Chay qua `python tools/chay_test_pg.py -q tests/test_2923_flow_a_http_that_pg.py`
(tep nay nam trong `TEP_PG`).
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest
import sqlalchemy as sa

import platform_core.an_toan_mang as an_toan_mang
from platform_core.workflow.nut_loi import http as nut_http
from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoa advisory rieng cho tep nay — cung ly do `test_1787._KHOA_LOCK_KEY`.
_KHOA_LOCK_KEY = 172012002923

BI_MAT = "sk-FLOW-A-TOKEN-CUA-KHACH-4242"


class _Tay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):                                   # noqa: N802
        self.server.da_nhan.append(self.headers.get("Authorization", ""))
        than = json.dumps({"diem": 42}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        # Mot dich co the DOI LAI bi mat trong header phan hoi.
        self.send_header("X-Echo", self.headers.get("Authorization", ""))
        self.end_headers()
        self.wfile.write(than)

    def log_message(self, *_a):
        return


@pytest.fixture()
def may_chu():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Tay)
    srv.da_nhan = []
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.fixture(autouse=True)
def _chinh_sach(monkeypatch):
    """May chu gia song o 127.0.0.1 — bo gac chan dia chi do, DUNG nhu no phai.

    ⛔ Khong vo hieu bo gac: doi CHINH SACH sang `CHINH_SACH_NOI_BO` (co san
    cho dung viec nay). Bo gac van chay va van la MOT ban duy nhat.
    """
    monkeypatch.setattr(nut_http, "CHINH_SACH_NODE",
                        an_toan_mang.CHINH_SACH_NOI_BO)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-flow-a-" + "q" * 32)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"),
                      {"k": _KHOA_LOCK_KEY})
    try:
        dbmod.Base.metadata.drop_all(dbmod.get_engine())
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield dbmod
    finally:
        dbmod.reset_engine()
        khoa_conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"),
                          {"k": _KHOA_LOCK_KEY})
        khoa_conn.close()
        khoa_engine.dispose()


@pytest.fixture()
def db(pg):
    from platform_core import credit
    from tests.conftest import bao_dam_user

    s = next(pg.get_session())
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 10_000, note="test")
    s.commit()
    try:
        yield s
    finally:
        s.close()


_DEM = {"n": 0}


def _core(nid: str, loai: str, *, credential_ref: str = "", **params) -> dict:
    n = {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
         "params": params}
    if credential_ref:
        n["credential_ref"] = credential_ref
    return n


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


def _publish(db, nodes, edges=()):
    from platform_core.workflow import dinh_nghia

    _DEM["n"] += 1
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"flowa{_DEM['n']}")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                 "edges": list(edges)}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu={})
    w.published_version_id = v.id
    db.commit()
    return w


def _chay(db, w):
    from platform_core.workflow import tao_run

    _DEM["n"] += 1
    run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                             trigger_kind="manual",
                             idempotency_key=f"flowa{_DEM['n']}")
    db.commit()
    return run


def _vong(db, run, lan=4):
    from platform_core.workflow import dong_co

    tt = ""
    for _ in range(lan):
        tt = dong_co.xu_ly_run(db, run.id, cong_cu={})
        db.commit()
    return tt


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt

    return mtt.trang_thai_node(db, run.id, nid)


def _cred(db):
    from platform_core import credential

    c = credential.tao(db, owner_id="u1", kieu="bearer", nha_cung_cap="http",
                       ten="Token FLOW A", bi_mat=BI_MAT)
    db.commit()
    return c


def _do_thi(srv, cred_id: str, nguong: int):
    return ([_core("s", "set", bien={"diem": "10"}),
             _core("i", "if", dieu_kien=f"vars.diem > {nguong}"),
             _core("h", "http", credential_ref=cred_id,
                   url=f"http://127.0.0.1:{srv.server_address[1]}/api"),
             _core("dung", "stop", trang_thai="SUCCEEDED", ly_do="diem thap")],
            [_canh("s", "i"),
             _canh("i", "h", kind="CONTROL", condition="true"),
             _canh("i", "dung", kind="CONTROL", condition="false")])


# ── FLOW A voi HTTP THAT ────────────────────────────────────────────────────

def test_FLOW_A_nhanh_true_goi_HTTP_THAT_va_SUCCEEDED(db, may_chu):
    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=1)
    run = _chay(db, _publish(db, nodes, edges))
    _vong(db, run)
    assert _tt(db, run, "h") == "SUCCEEDED", _tt(db, run, "h")
    assert _tt(db, run, "dung") == "SKIPPED"
    # ⭐ Doi chung: may chu gia THAT SU nhan duoc mot request, va header uy
    #    quyen la thu kho credential phat ra — khong phai mot chuoi trong graph.
    assert may_chu.da_nhan == [f"Bearer {BI_MAT}"]


def test_FLOW_A_nhanh_false_KHONG_gui_request_nao(db, may_chu):
    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=99)
    run = _chay(db, _publish(db, nodes, edges))
    _vong(db, run)
    assert _tt(db, run, "h") == "SKIPPED"
    assert may_chu.da_nhan == []


def test_bi_mat_KHONG_nam_trong_workflow_version(db, may_chu):
    """🔴 Ly do `core.http` bi khoa tu 24/09, do thang bang mot cau SQL.

    `workflow_version` duoc NHAN BAN khi khach "Save as" va tra nguyen ven cho
    trinh soan thao. Bi mat o do la bi mat da ro.
    """
    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=1)
    w = _publish(db, nodes, edges)
    tho = db.execute(sa.text(
        "SELECT graph::text FROM workflow_version WHERE workflow_id = :w"),
        {"w": w.id}).scalar_one()
    assert BI_MAT not in tho
    # Doi chung: ref CO nam trong graph — neu khong, phep tren xanh vi graph
    # khong he mang credential nao.
    assert c.id in tho


def test_bi_mat_KHONG_nam_trong_node_run_snapshot(db, may_chu):
    """`node_run_snapshot` la bang CHI-THEM: mot bi mat lot vao la lot VINH VIEN."""
    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=1)
    run = _chay(db, _publish(db, nodes, edges))
    _vong(db, run)
    hang = db.execute(sa.text(
        "SELECT COALESCE(output_ref::text, '') || COALESCE(error, '') "
        "FROM node_run_snapshot WHERE run_id = :r"), {"r": run.id}).all()
    assert hang, "khong co anh chup nao — phep kiem nay dang khong do gi"
    for (tho,) in hang:
        assert BI_MAT not in tho


def test_header_doi_lai_bi_mat_van_bi_CHE(db, may_chu):
    """May chu gia doi lai `Authorization` trong header `X-Echo` cua phan hoi.

    ⛔ Che theo TEN mot minh khong bat duoc ca nay (`x-echo` khong nam trong
       `HEADER_PHAI_CHE`), nen phai che ca theo GIA TRI.
    """
    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=1)
    run = _chay(db, _publish(db, nodes, edges))
    _vong(db, run)
    tho = db.execute(sa.text(
        "SELECT output_ref::text FROM node_run_snapshot "
        "WHERE run_id = :r AND node_id = 'h'"), {"r": run.id}).scalars().all()
    assert tho, "node http chua co anh chup"
    # ⚠️ PostgreSQL tra `jsonb::text` voi ky tu ngoai ASCII da thoat
    #    (`«`), nen so chuoi THO voi `DA_CHE` luon sai. Phan tich JSON roi
    #    hoi — mot phep kiem so nham lop ma hoa la mot phep kiem do nham thu.
    x_echo = [json.loads(t).get("headers", {}).get("x-echo", "")
              for t in tho if json.loads(t)]
    assert any(nut_http.DA_CHE in e for e in x_echo), x_echo
    assert all(BI_MAT not in e for e in x_echo), x_echo


def test_credential_ghi_nhan_da_DUNG_o_dung_run(db, may_chu):
    """Nhat ky credential tra loi *'khoa nay bi dung o dau'* — cau hoi luc su co."""
    from platform_core.models import CredentialNhatKy

    c = _cred(db)
    nodes, edges = _do_thi(may_chu, c.id, nguong=1)
    run = _chay(db, _publish(db, nodes, edges))
    _vong(db, run)
    dung = db.query(CredentialNhatKy).filter(
        CredentialNhatKy.credential_id == c.id,
        CredentialNhatKy.hanh_dong == "dung").all()
    assert [(h.run_id, h.node_id) for h in dung] == [(run.id, "h")]
