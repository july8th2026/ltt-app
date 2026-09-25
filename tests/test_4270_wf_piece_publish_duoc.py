"""`piece.*` mở được đường PUBLISH thật (lan wfp, plan 08, 25/09).

Trước bản vá này BA chỗ khoá node piece ở trạng thái "chưa hỗ trợ", và bật
MỘT mình không có tác dụng gì — phải nối cả ba:

1. `nut.tu_piece()` — `publish_duoc` cứng `False`.
2. `bien_dich._node()` — không có nhánh nào cho một `type` không khớp
   `TIEN_TO_LOI`/`"tool"`/`"app."`; mọi node piece rơi thẳng xuống
   `loai_node_chua_ho_tro`.
3. `dinh_nghia._kiem_credential()` — lọc bỏ MỌI `credential_ref` rỗng trước
   cả vòng lặp, nên một node piece khai `credential=("oauth2",)` mà không
   gắn ref nào đi lọt qua publish sạch sẽ (lộ ra lúc CHẠY, sau khi run đã
   giữ tiền).

Tệp này đo publish (biên dịch + báo giá + kiểm credential) — `cau_noi.nop_job`
(nộp job thật) nằm ở `test_4271_wf_piece_nop_job.py`.

⭐ Dùng catalog GIẢ (`monkeypatch.setattr(nut, "NGUON_PIECE", ...)`), không
   phải `connector_runner/catalog.json` thật: phép kiểm không được phụ thuộc
   `npm install` đã chạy hay chưa, và số `gia` phải KHÁC 0 để phân biệt được
   "tính đúng" với "âm thầm rơi về 0" — catalog thật hôm nay ghi `gia: 0` cho
   mọi piece (JS `xuat_catalog.js`, TODO giá thật, ngoài phạm vi lan này).
"""
from __future__ import annotations
# ruff: noqa: F811 -- fixture pytest duoc import co chu y.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

#: Giá cố định KHÁC 0 và khác mọi hằng "tình cờ đúng" (0, 1) hay dùng trong
#: mã nguồn — một con số phải ĐI TRỌN vẹn từ catalog giả tới `gia_tran` mới
#: khớp nó.
GIA_PIECE = 17

TEN_PIECE_THAT = "piece.demo.say_hi"
TEN_PIECE_NGOAI = "piece.demo.khong_co_that"


def _catalog_gia() -> list:
    return [{
        "type": TEN_PIECE_THAT, "type_version": 1,
        "title": "Demo noi xin chao", "description": "Piece gia cho test 4270",
        "icon": "D", "auth": ["oauth2"],
        "params": {"msg": {"type": "string", "required": True}},
        "returns": {"ok": "json"}, "gia": GIA_PIECE, "side_effect": "external",
    }]


@pytest.fixture()
def nguon_piece_gia(monkeypatch):
    """Gắn catalog giả — CHỈ MỘT piece, `TEN_PIECE_THAT`.

    ⚠️ Import `nut_loi` TRƯỚC khi monkeypatch: `nut.NGUON_PIECE` là MỘT biến
       toàn cục bị `nut_loi/connector.py` ghi đè làm hiệu ứng phụ Ở LẦN NHẬP
       ĐẦU TIÊN (`nut.NGUON_PIECE = _connector.doc_catalog`). Chạy phép này
       ĐƠN LẺ (không có phép nào khác nhập `nut_loi` trước) mà monkeypatch
       trước rồi mới gọi một hàm nhập `nut_loi` cục bộ (`nut.tat_ca()`) thì
       chính lần nhập đó GHI ĐÈ catalog giả bằng catalog THẬT — cùng bẫy
       `test_1755_wf_nut_ba_nguon.py::
       test_nguon_piece_MAC_DINH_rong_va_allowlist_CO_TRAN` đã ghim ("gọi
       trong một tiến trình sạch ra 0, chạy dưới pytest ra 7").
    """
    from platform_core.workflow import nut, nut_loi
    nut_loi.tat_ca()                      # ep lan nhap dau tien xay ra o day
    monkeypatch.setattr(nut, "NGUON_PIECE", _catalog_gia)
    return nut


def _wf_moi(db, ten="wf-piece"):
    from platform_core.workflow import dinh_nghia
    return dinh_nghia.tao_workflow(db, owner_id="u1", name=ten)


def _draft_mot_node(db, wf_id, *, loai=TEN_PIECE_THAT, credential_ref="",
                    params=None):
    from platform_core.workflow import dinh_nghia
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": loai, "position": {"x": 0, "y": 0},
         "params": dict(params or {"msg": "chao"}),
         "credential_ref": credential_ref},
    ], "edges": []}]}
    dinh_nghia.luu_draft(db, wf_id, document=doc, revision=0)


# ── 1. Publish được, và publish_duoc phản ánh đúng ba nguồn ─────────────────

def test_publish_duoc_BAT_cho_moi_piece_trong_catalog(nguon_piece_gia):
    """`nut.tu_piece()` không còn khoá cứng `False`."""
    from platform_core.workflow import nut
    nd = nut.tat_ca()[TEN_PIECE_THAT]
    assert nd.publish_duoc is True
    assert nd.job_type == nut.JOB_TYPE_PIECE


def test_node_piece_BIEN_DICH_duoc(db, nguon_piece_gia):
    """`bien_dich._node()` nay có nhánh cho piece — không còn
    `loai_node_chua_ho_tro` cho một node CÓ trong catalog."""
    from platform_core.workflow import bien_dich
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": TEN_PIECE_THAT, "position": {"x": 0, "y": 0},
         "params": {"msg": "chao"}, "credential_ref": ""},
    ], "edges": []}]}
    g = bien_dich.bien_dich(doc, cong_cu={})
    node = g["nodes"][0]
    assert node["type"] == TEN_PIECE_THAT
    assert node["thi_hanh"] == "job"
    assert node["params"] == {"msg": "chao"}


# ── 2. Ngoài allowlist vẫn bị từ chối ────────────────────────────────────────

def test_node_piece_NGOAI_allowlist_van_bi_tu_choi(db, nguon_piece_gia):
    """`TEN_PIECE_NGOAI` không có trong `_catalog_gia()` — phải NÉM, không
    được suy ra publish_duoc từ một tiền tố `"piece."` trông giống thật."""
    from platform_core.workflow import bien_dich
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": TEN_PIECE_NGOAI, "position": {"x": 0, "y": 0},
         "params": {}, "credential_ref": ""},
    ], "edges": []}]}
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu={})
    assert e.value.ma == "loai_node_chua_ho_tro"
    assert TEN_PIECE_NGOAI in str(e.value)


def test_TIEM_LOI_khop_TUYET_DOI_khong_phai_tien_to(db, nguon_piece_gia):
    """⭐ Tripwire: nếu ai đó nới `dinh_nghia_piece` từ so khớp TUYỆT ĐỐI
    (`muc["type"] == loai`) sang `loai.startswith(f"piece.demo.")` (nới theo
    PIECE thay vì theo ACTION), một action KHÔNG có trong catalog nhưng cùng
    tiền tố piece sẽ lọt qua. Bài này ghim đúng ranh giới đó."""
    from platform_core.workflow import nut
    # Cùng piece ("demo"), khác action — action nay KHONG co trong catalog.
    assert nut.dinh_nghia_piece("piece.demo.say_hi_v2") is None
    assert nut.dinh_nghia_piece(TEN_PIECE_THAT) is not None


# ── 3. Báo giá ra số ĐÚNG cho node piece, không phải 0 ──────────────────────

def test_bao_gia_ra_dung_gia_cua_piece_KHONG_PHAI_0(db, nguon_piece_gia):
    from platform_core.workflow import bao_gia, bien_dich
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": TEN_PIECE_THAT, "position": {"x": 0, "y": 0},
         "params": {"msg": "chao"}, "credential_ref": ""},
    ], "edges": []}]}
    g = bien_dich.bien_dich(doc, cong_cu={})
    gia = bao_gia.bao_gia_do_thi(g, cong_cu={})
    assert gia.toi_da == GIA_PIECE, (
        f"gia_tran phai la {GIA_PIECE} (tu NodeDefinition.gia), khong phai "
        f"0 hay mot con so khac: {gia.toi_da}")
    node = g["nodes"][0]
    assert node["gia_tran"] == GIA_PIECE


# ── 4. Thiếu credential vẫn bị từ chối, đúng mã lỗi cũ ──────────────────────

def test_thieu_credential_van_bi_tu_choi_dung_ma_loi_cu(db, nguon_piece_gia):
    """`TEN_PIECE_THAT` khai `auth=["oauth2"]` (credential BẮT BUỘC) — một
    draft không gắn `credential_ref` nào phải KHÔNG publish được, và mã lỗi
    phải là `credential_khong_hop_le` — CÙNG mã mà `_kiem_credential` đã
    dùng cho ca "ref không dùng được" (không phải một mã mới bịa ra)."""
    from platform_core.workflow import bien_dich, dinh_nghia
    wf = _wf_moi(db, "wf-thieu-cred")
    _draft_mot_node(db, wf.id, credential_ref="")
    with pytest.raises(bien_dich.LoiBienDich) as e:
        dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu={})
    assert e.value.ma == "credential_khong_hop_le"


def test_TIEM_LOI_bo_loc_ref_rong_som_thi_bai_tren_do(db, nguon_piece_gia):
    """⭐ Tripwire ngược: tái hiện ĐÚNG lỗi cũ (lọc `credential_ref` rỗng
    TRƯỚC vòng lặp) để chứng minh bài trên THẬT SỰ đo cửa credential, không
    phải xanh vì một lý do khác (vd node không biên dịch được)."""
    from platform_core.workflow import dinh_nghia

    wf = _wf_moi(db, "wf-tiem-loi-cred")
    _draft_mot_node(db, wf.id, credential_ref="")

    def _kiem_credential_long_leo(db_, workflow_id, graph):
        # Bản CŨ: loại bỏ moi node co credential_ref RONG truoc khi xet gi ca.
        refs = [n for n in (graph.get("nodes") or []) if n.get("credential_ref")]
        assert not refs  # khong con gi de kiem -- publish se troi qua

    import platform_core.workflow.dinh_nghia as dn_mod
    truoc = dn_mod._kiem_credential
    dn_mod._kiem_credential = _kiem_credential_long_leo
    try:
        v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu={})
        assert v is not None, "voi cua long leo, publish PHAI qua duoc"
    finally:
        dn_mod._kiem_credential = truoc


def test_co_credential_dung_kieu_thi_publish_qua(db, nguon_piece_gia):
    """Đối chứng thuận: gắn đúng một credential `oauth2` của đúng chủ thì
    publish phải QUA — bài trên không phải "mọi piece đều bị chặn cứng"."""
    from platform_core import credential as kho
    from platform_core.workflow import dinh_nghia

    wf = _wf_moi(db, "wf-co-cred")
    cred = kho.tao(db, owner_id="u1", kieu="oauth2", bi_mat="tok-demo")
    _draft_mot_node(db, wf.id, credential_ref=cred.id)
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu={})
    assert v.graph["nodes"][0]["credential_ref"] == cred.id
    assert v.estimated_max == GIA_PIECE
