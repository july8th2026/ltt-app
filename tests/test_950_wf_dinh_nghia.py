"""LTT WORKFLOW V2 · Đợt 2.1 — định nghĩa workflow: draft · version · hash.

Dải test **950–999** cấp cho LTT WORKFLOW V2. Đo ngày 2026-09-08, không đọc
bảng cấp phát (bảng chép tay trôi; xem `CLAUDE.md` mục "hỏi máy chủ"):

    400-454  ASV          500-504  (5 tep)     600-637  CHATLTT
    800-849  (50 tep)     900-906  Mobile V1   907+     TRONG

`700–799` để trống dù chưa dùng — đang cấp cho LTT VIDEO AI. `505–599` bỏ qua
vì kề `500–504`, dễ nhập nhằng.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.1`.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf.db').as_posix()}")
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


def _do_thi(*, gia_tri: str = "xin chao", vi_tri=(10, 20), nhan: str = "Node A"):
    """Một đồ thị hai node tối thiểu, tham số hoá phần trình bày."""
    return {
        "schema_version": 1,
        "nodes": [
            {"id": "n1", "type": "llm.chat", "type_version": 1,
             "params": {"prompt": gia_tri},
             "position": {"x": vi_tri[0], "y": vi_tri[1]},
             "label": nhan, "_ui": {"mau": "xanh"}},
            {"id": "n2", "type": "text.join", "type_version": 1,
             "params": {"sep": " "},
             "position": {"x": 200, "y": 20}, "label": "Node B"},
        ],
        "edges": [
            {"id": "e1", "source_node": "n1", "source_port": "out",
             "target_node": "n2", "target_port": "in", "kind": "DATA"},
        ],
    }


# ── Hash đồ thị ───────────────────────────────────────────────────────────────

def test_LOAI_TRU_KHOI_HASH_duoc_khai_TUONG_MINH():
    """⛔ Không khai ⇒ `position` lọt vào hash ⇒ kéo node sang phải sinh version mới.

    Bài học Kestra (`07+08 §1.4`). Phép kiểm này **mạnh hơn thứ nó đo**: nó ghim
    một tập hợp mà mã có thể lặng lẽ thu hẹp, và thu hẹp thì gate đỏ.
    """
    from platform_core.workflow.dinh_nghia import LOAI_TRU_KHOI_HASH

    assert LOAI_TRU_KHOI_HASH >= {
        "position", "label", "summary", "_ui", "created_at", "updated_at"}


def test_bam_do_thi_BO_QUA_truong_trinh_bay():
    """Kéo một node sang chỗ khác, đổi nhãn ⇒ **cùng** hash."""
    from platform_core.workflow.dinh_nghia import bam_do_thi

    a = bam_do_thi(_do_thi(vi_tri=(10, 20), nhan="Node A"))
    b = bam_do_thi(_do_thi(vi_tri=(999, 888), nhan="Ten khac han"))
    assert a == b


def test_bam_do_thi_DOI_khi_noi_dung_doi():
    from platform_core.workflow.dinh_nghia import bam_do_thi

    assert bam_do_thi(_do_thi(gia_tri="xin chao")) != bam_do_thi(
        _do_thi(gia_tri="chao nhe"))


def test_bam_do_thi_KHONG_phu_thuoc_thu_tu_node():
    """Canvas trả node theo thứ tự dựng; thứ tự ấy không phải nội dung."""
    from platform_core.workflow.dinh_nghia import bam_do_thi

    xuoi = _do_thi()
    nguoc = _do_thi()
    nguoc["nodes"] = list(reversed(nguoc["nodes"]))
    assert bam_do_thi(xuoi) == bam_do_thi(nguoc)


def test_bam_do_thi_la_64_ky_tu_hex():
    from platform_core.workflow.dinh_nghia import bam_do_thi

    h = bam_do_thi(_do_thi())
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


# ── Xuất bản ──────────────────────────────────────────────────────────────────

def test_xuat_ban_hai_lan_cung_noi_dung_tra_ve_CUNG_version(db):
    """⭐ `UNIQUE (workflow_id, graph_hash)` — bằng ràng buộc, không bằng mã cẩn thận."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()

    v1 = dinh_nghia.xuat_ban(db, wf.id, _do_thi(), created_by="u1")
    db.commit()
    v2 = dinh_nghia.xuat_ban(db, wf.id, _do_thi(vi_tri=(777, 666)), created_by="u1")
    db.commit()

    assert v2.id == v1.id, "cung noi dung (chi khac vi tri) phai tra ve version cu"
    assert v2.seq == 1


def test_xuat_ban_noi_dung_khac_thi_tang_seq(db):
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v1 = dinh_nghia.xuat_ban(db, wf.id, _do_thi(gia_tri="mot"), created_by="u1")
    db.commit()
    v2 = dinh_nghia.xuat_ban(db, wf.id, _do_thi(gia_tri="hai"), created_by="u1")
    db.commit()

    assert (v1.seq, v2.seq) == (1, 2)
    assert v1.id != v2.id


def test_xuat_ban_dong_bang_estimated_max_cung_do_thi(db):
    """Trần chi phí đóng băng **cùng** graph — không tính lại lúc chạy."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, _do_thi(), created_by="u1",
                            estimated_max=250)
    db.commit()
    assert v.estimated_max == 250


def test_hai_workflow_khac_nhau_cung_noi_dung_van_ra_hai_version(db):
    """Ràng buộc là (workflow_id, graph_hash) — không phải hash toàn cục."""
    from platform_core.workflow import dinh_nghia

    a = dinh_nghia.tao_workflow(db, owner_id="u1", name="A")
    b = dinh_nghia.tao_workflow(db, owner_id="u2", name="B")
    db.commit()
    va = dinh_nghia.xuat_ban(db, a.id, _do_thi(), created_by="u1")
    vb = dinh_nghia.xuat_ban(db, b.id, _do_thi(), created_by="u2")
    db.commit()
    assert va.id != vb.id and va.graph_hash == vb.graph_hash


# ── Chỉ mục dẫn xuất ──────────────────────────────────────────────────────────

def test_xuat_ban_sinh_chi_muc_node_va_edge(db):
    """"Tool X đang được dùng ở đâu?" phải trả lời bằng SQL, không quét jsonb."""
    from platform_core.models import WorkflowVersionEdge, WorkflowVersionNode
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, _do_thi(), created_by="u1")
    db.commit()

    nodes = db.query(WorkflowVersionNode).filter_by(version_id=v.id).all()
    edges = db.query(WorkflowVersionEdge).filter_by(version_id=v.id).all()
    assert {n.node_type for n in nodes} == {"llm.chat", "text.join"}
    assert [e.kind for e in edges] == ["DATA"]


# ── Draft: khoá lạc quan ──────────────────────────────────────────────────────

def test_luu_draft_tang_revision(db):
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    d1 = dinh_nghia.luu_draft(db, wf.id, document={"pages": []}, revision=0)
    db.commit()
    assert d1.revision == 1


def test_luu_draft_revision_cu_bi_TU_CHOI(db):
    """Hai tab cùng sửa: tab đến sau phải nhận 409, không được ghi đè âm thầm."""
    from platform_core.workflow import dinh_nghia
    from platform_core.workflow.dinh_nghia import XungDotRevision

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    dinh_nghia.luu_draft(db, wf.id, document={"pages": ["a"]}, revision=0)
    db.commit()

    with pytest.raises(XungDotRevision):
        dinh_nghia.luu_draft(db, wf.id, document={"pages": ["b"]}, revision=0)


def test_bam_do_thi_PHU_THUOC_thu_tu_CANH(db=None):
    """⛔ Đảo thứ tự cạnh PHẢI đổi hash — ngược hẳn với `nodes`.

    Phiên ASV chỉ ra rằng luật *"`sort_keys` không sắp phần tử list nên phải
    `sorted()`"* thiếu một vế, và vế thiếu mới là vế nguy hiểm:

        thu tu list co anh huong DAU RA khong?
          KHONG  -> sorted()  tranh van tay gia (lam lai viec thua)
          CO     -> sorted() la LOI:  hai cau hinh cho ra HAI ket qua khac nhau
                    dung CHUNG mot van tay  =>  phuc vu lai mot ket qua SAI

    Ở đây `25_26 §7` khai cổng `multiple: True` — **một cổng nhận nhiều cạnh**.
    Không có trường thứ tự tường minh nào trên cạnh, nên **thứ tự mảng `edges`
    là thứ duy nhất mang được thứ tự nối vào** một node kiểu `text.join`. Sắp
    nó đi là quyết định lặng lẽ rằng thứ tự ấy không tồn tại.

    ⚠️ `nodes` thì ngược lại: thứ tự mảng là ngẫu nhiên của giao diện (thứ tự
    người dựng), không ảnh hưởng đầu ra — nên nó vẫn được sắp.

    ⇒ Khi phân vân, **giữ thứ tự** là phía an toàn: hỏng thành "làm lại việc
    thừa" thay vì "phục vụ lại kết quả sai".
    """
    from platform_core.workflow.dinh_nghia import bam_do_thi

    goc = {
        "schema_version": 1,
        "nodes": [{"id": "a", "type": "src", "params": {}},
                  {"id": "b", "type": "src", "params": {}},
                  {"id": "j", "type": "text.join", "params": {}}],
        "edges": [
            {"id": "e1", "source_node": "a", "source_port": "out",
             "target_node": "j", "target_port": "vao", "kind": "DATA"},
            {"id": "e2", "source_node": "b", "source_port": "out",
             "target_node": "j", "target_port": "vao", "kind": "DATA"},
        ],
    }
    dao = {**goc, "edges": list(reversed(goc["edges"]))}

    assert bam_do_thi(goc) != bam_do_thi(dao), (
        "dao thu tu canh vao cung mot cong `multiple` doi thu tu noi -> "
        "doi dau ra -> BAT BUOC doi hash")
