# -*- coding: utf-8 -*-
"""Gan credential cho node + bat `core.http` — plan wf-v2 P5c/T2, T4, T5.

## Dieu phep kiem nay giu

🔴 **`core.http` bi KHOA tu 24/09 vi mot ly do cu the**: cho duy nhat mot
   workflow cat duoc header `Authorization` la `params` cua node, tuc BEN
   TRONG `workflow_version` — mot ban ghi duoc NHAN BAN khi khach "Save as" va
   duoc tra nguyen ven cho trinh soan thao. Mo khoa node ma khong co kho
   credential la moi khach dan token vao mot ban ghi xuat/clone duoc.

Nen bon tinh chat:

1. `credential_ref` cua node `core.*` **di duoc qua bo bien dich** (truoc day
   `_node_loi` ghi cung `""` — mot o luon rong thi khong ai gan duoc gi).
2. Publish **tu choi** ref khong thuoc chu workflow, ref da thu hoi, ref sai
   kieu. Chan o PUBLISH, khong phai luc chay.
3. Bi mat **khong bao gio** xuat hien trong output/loi cua node, ke ca khi
   dich tra loi 401 va ke ca trong `headers` tra ve.
4. Mo-dun `nut_loi/http.py` **duoc import** trong `__init__.py` — mot mo-dun
   dang ky ma khong ai import la mo-dun chet.

## Doi chung

`test_doi_chung_may_chu_that_su_nhan_duoc_header` chung minh header CO di ra
day thuc su. Khong co no, moi phep "bi mat khong lo" xanh ca khi node khong
gui gi.
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from platform_core.workflow import bien_dich, nut_loi
from platform_core.workflow.nut_loi import http as nut_http

BI_MAT = "sk-TOKEN-CUA-KHACH-KHONG-DUOC-LO-77"


@pytest.fixture()
def db(tmp_path):
    import platform_core.models  # noqa: F401
    from platform_core.db import Base

    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'gan.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    phien = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield phien
    finally:
        phien.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _khoa(monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-" + "z" * 32)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)


class _Tay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):                                   # noqa: N802
        self.server.da_nhan.append(
            {"uy_quyen": self.headers.get("Authorization", ""),
             "khoa_api": self.headers.get("X-Api-Key", "")})
        than = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(self.server.ma_tra)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        # ⚠️ Mot dich thu dich co the DOI LAI bi mat trong header phan hoi.
        self.send_header("X-Echo-Auth", self.headers.get("Authorization", ""))
        self.end_headers()
        self.wfile.write(than)

    def log_message(self, *_a):                         # im lang
        return


@pytest.fixture()
def may_chu():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Tay)
    srv.da_nhan = []
    srv.ma_tra = 200
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


def _url(srv) -> str:
    return f"http://127.0.0.1:{srv.server_address[1]}/x"


def _mo_cong(monkeypatch):
    """May chu gia song o 127.0.0.1 — bo gac chan dia chi do, DUNG nhu no phai.

    ⛔ Khong vo hieu bo gac: thay CHINH SACH cua node bang
    `an_toan_mang.CHINH_SACH_NOI_BO` (da co san cho dung viec nay). Bo gac van
    chay, van la MOT ban, chi la no duoc hoi mot cau khac.
    """
    import platform_core.an_toan_mang as an_toan_mang

    monkeypatch.setattr(nut_http, "CHINH_SACH_NODE",
                        an_toan_mang.CHINH_SACH_NOI_BO)


# ── 1. `credential_ref` di qua bo bien dich ─────────────────────────────────

def _draft(**node):
    n = {"id": "n1", "type": "core.http",
         "params": {"url": "https://vi.du/api"}}
    n.update(node)
    return {"pages": [{"id": "p1", "nodes": [n], "edges": []}]}


def test_credential_ref_KHONG_bi_bo_di_khi_bien_dich():
    ct = bien_dich.cau_truc(_draft(credential_ref="cred-1"))
    assert ct.nodes[0]["credential_ref"] == "cred-1"


def test_node_khong_nhan_credential_ma_bi_gan_ref_thi_BI_TU_CHOI():
    """`core.set` khong goi ra ngoai; mot ref o do la mot hieu nham."""
    draft = {"pages": [{"id": "p1", "edges": [], "nodes": [
        {"id": "n1", "type": "core.set",
         "params": {"bien": {"x": "1"}}, "credential_ref": "cred-1"}]}]}
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.cau_truc(draft)
    assert e.value.ma == "credential_khong_ho_tro"


# ── 2. Publish kiem ref that (spec §9.1) ────────────────────────────────────

def _bo_doi(db):
    """Mot workflow + mot draft cua `u1`, tra `(workflow_id, cred)`."""
    from platform_core import credential
    from platform_core.models import Workflow, WorkflowDraft

    wf = Workflow(id="wf1", owner_id="u1", name="t")
    db.add(wf)
    db.add(WorkflowDraft(workflow_id="wf1", document=_draft(
        credential_ref="se-thay")))
    c = credential.tao(db, owner_id="u1", kieu="bearer", nha_cung_cap="http",
                       ten="Token", bi_mat=BI_MAT)
    db.flush()
    return wf, c


def _publish(db, ref: str):
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import dinh_nghia

    draft = db.get(WorkflowDraft, "wf1")
    draft.document = _draft(credential_ref=ref)
    return dinh_nghia.xuat_ban_draft(db, "wf1", created_by="u1")


def test_doi_chung_ref_HOP_LE_thi_publish_QUA(db):
    _wf, c = _bo_doi(db)
    v = _publish(db, c.id)
    assert v.graph["nodes"][0]["credential_ref"] == c.id


def test_publish_tu_choi_ref_CUA_NGUOI_KHAC(db):
    from platform_core import credential

    _bo_doi(db)
    la = credential.tao(db, owner_id="u2", kieu="bearer", ten="cua u2",
                        bi_mat="x")
    db.flush()
    with pytest.raises(bien_dich.LoiBienDich) as e:
        _publish(db, la.id)
    assert e.value.ma == "credential_khong_hop_le"


def test_publish_tu_choi_ref_DA_THU_HOI(db):
    from platform_core import credential

    _wf, c = _bo_doi(db)
    credential.thu_hoi(db, c.id, owner_id="u1")
    db.flush()
    with pytest.raises(bien_dich.LoiBienDich) as e:
        _publish(db, c.id)
    assert e.value.ma == "credential_khong_hop_le"


def test_publish_tu_choi_ref_SAI_KIEU(db):
    from platform_core import credential

    _bo_doi(db)
    sai = credential.tao(db, owner_id="u1", kieu="oauth2", ten="google",
                         bi_mat={"access_token": "a"})
    db.flush()
    with pytest.raises(bien_dich.LoiBienDich) as e:
        _publish(db, sai.id)
    assert e.value.ma == "credential_khong_hop_le"


# ── 3. Tiem + che bi mat o `core.http` ──────────────────────────────────────

class _Run:
    id = "run-1"
    owner_id = "u1"


def _chay(db, srv, ref: str = "", **params):
    node = {"id": "n1", "type": "core.http", "credential_ref": ref,
            "params": {"url": _url(srv), **params}}
    return nut_http.chay_http(db, _Run(), node, moi_truong={})


def test_doi_chung_may_chu_that_su_nhan_duoc_header(db, may_chu, monkeypatch):
    """⛔ Khong co phep nay, moi phep 'bi mat khong lo' xanh vi khong gui gi."""
    from platform_core import credential

    _mo_cong(monkeypatch)
    c = credential.tao(db, owner_id="u1", kieu="bearer", ten="t",
                       bi_mat=BI_MAT)
    db.flush()
    ket = _chay(db, may_chu, ref=c.id)
    assert ket.sang != "FAILED", ket.error
    assert may_chu.da_nhan[0]["uy_quyen"] == f"Bearer {BI_MAT}"


def test_bi_mat_KHONG_nam_trong_output_cua_node(db, may_chu, monkeypatch):
    from platform_core import credential

    _mo_cong(monkeypatch)
    c = credential.tao(db, owner_id="u1", kieu="bearer", ten="t",
                       bi_mat=BI_MAT)
    db.flush()
    ket = _chay(db, may_chu, ref=c.id)
    assert BI_MAT not in json.dumps(ket.output, default=str)


def test_bi_mat_KHONG_nam_trong_loi_khi_dich_tra_401(db, may_chu, monkeypatch):
    from platform_core import credential

    _mo_cong(monkeypatch)
    may_chu.ma_tra = 401
    c = credential.tao(db, owner_id="u1", kieu="bearer", ten="t",
                       bi_mat=BI_MAT)
    db.flush()
    ket = _chay(db, may_chu, ref=c.id)
    assert ket.sang == "FAILED"
    assert BI_MAT not in str(ket.error)


def test_kieu_api_key_di_vao_header_do_meta_khai(db, may_chu, monkeypatch):
    from platform_core import credential

    _mo_cong(monkeypatch)
    c = credential.tao(db, owner_id="u1", kieu="api_key", ten="t",
                       bi_mat=BI_MAT, meta={"ten_header": "X-Api-Key"})
    db.flush()
    _chay(db, may_chu, ref=c.id)
    assert may_chu.da_nhan[0]["khoa_api"] == BI_MAT
    assert may_chu.da_nhan[0]["uy_quyen"] == ""


def test_ref_da_thu_hoi_thi_node_FAILED_co_MA(db, may_chu, monkeypatch):
    from platform_core import credential

    _mo_cong(monkeypatch)
    c = credential.tao(db, owner_id="u1", kieu="bearer", ten="t",
                       bi_mat=BI_MAT)
    db.flush()
    credential.thu_hoi(db, c.id, owner_id="u1")
    db.flush()
    ket = _chay(db, may_chu, ref=c.id)
    assert ket.sang == "FAILED"
    assert "credential_bi_thu_hoi" in str(ket.error)
    assert may_chu.da_nhan == []          # chua gui gi ca


# ── 4. Node da duoc BAT ─────────────────────────────────────────────────────

def test_http_khong_con_nam_trong_CHUA_BAT():
    """⛔ Ly do khoa da het: kho credential ton tai tu T1.

    `test_1789` doi moi mo-dun co `dang_ky` phai duoc import HOAC khai trong
    `CHUA_BAT`. Giu ten o ca hai cho la de mot node DA BAT tiep tuc mang mot
    ly do khoa khong con dung — phep kiem doi chung cua chinh `test_1789` bat
    dieu do, va day la phia con lai cua no.
    """
    from tests.test_1789_wf_node_khai_toolspec import CHUA_BAT

    assert "http" not in CHUA_BAT


def test_core_http_khai_nhan_ba_kieu_credential():
    nd = nut_loi.tat_ca()["core.http"]
    assert set(nd.credential) == {"api_key", "bearer", "basic"}
    assert "credential" in nd.quyen


def test_core_http_publish_duoc():
    """Dieu kien ra cua phase: FLOW A voi HTTP THAT — publish duoc moi chay."""
    assert nut_loi.tat_ca()["core.http"].publish_duoc is True
