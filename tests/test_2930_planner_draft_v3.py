"""Agent Designer (spec §12.2): `planner` sinh **draft v3**, không còn Plan v1.

Phase gốc 11 / plan wf-v2 P8 Task 1.

⭐ NGUỒN (tra trước khi tự suy — luật §6.2 của plan MASTER):
   `n8n-io/n8n` `packages/@n8n/ai-workflow-builder.ee/src/tools/add-node.tool.ts`
   — bộ dựng workflow bằng AI của n8n **không** hỏi model một đồ thị hoàn chỉnh
   rồi tin nó. Nó cho model một công cụ có **lược đồ** (`nodeCreationSchema`),
   rồi mã **tất định** mới dựng node thật: `findNodeType(...)` ném
   `NodeTypeNotFoundError` khi loại node không có, và **vị trí do mã tính**
   (`calculateNodePosition`), không do model bịa. Hai điều đó là hai phép kiểm
   dưới đây.
"""
from __future__ import annotations

import json

import pytest

from platform_core.agent import ke_hoach_v3
from platform_core.workflow import nut
from platform_core.workflow.cong_cu import CongCu


def _cc(ten, gia=5, returns=None):
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2, params_schema={},
                  side_effect="external", idempotency_fields=("prompt",),
                  resource={"class": "api"},
                  tinh_gia=lambda p, g=gia: g,
                  returns=dict(returns or {"text": "text"}))


CC = {"text.chat": _cc("text.chat", 1),
      "image.generate": _cc("image.generate",
                            returns={"image_keys": "image[]"})}


def _ra_model(nodes, edges=()):
    return json.dumps({"nodes": list(nodes), "edges": list(edges)},
                      ensure_ascii=False)


# ── 1. Đầu ra là draft v3, KHÔNG phải Plan v1 ────────────────────────────────

def test_dau_ra_la_draft_v3_khong_con_steps_cua_plan_v1():
    doc = ke_hoach_v3.chuan_hoa(_ra_model([
        {"id": "a", "type": "app.text.chat", "params": {"prompt": "chào"}}]))
    assert doc["version"] == 3
    assert "steps" not in doc
    assert [t["id"] for t in doc["pages"]] == [ke_hoach_v3.TRANG_MAC_DINH]
    assert doc["pages"][0]["nodes"][0]["type"] == "app.text.chat"


def test_soan_draft_goi_model_MOT_lan_va_tra_ve_tai_lieu_v3():
    goi = []

    def gia_lap(prompt):
        goi.append(prompt)
        return _ra_model([{"id": "a", "type": "app.text.chat",
                           "params": {"prompt": "x"}}])

    kq = ke_hoach_v3.soan_draft(None, goal="viết một câu",
                                ngan_sach_credit=10, cong_cu=CC,
                                llm_call=gia_lap)
    assert len(goi) == 1
    assert kq["document"]["version"] == 3
    assert kq["hop_le"] is True and kq["loi"] == ()
    # Agent KHÔNG publish: nó trả tài liệu + báo giá, người dùng bấm publish.
    assert "graph" in kq and kq["graph"]["schema"] == "ltt.workflow/3"


# ── 2. Danh mục node + lược đồ tham số là đầu vào của prompt (§12.2) ─────────

def test_prompt_mang_danh_muc_node_va_luoc_do_tham_so():
    muc = ke_hoach_v3.danh_muc(cong_cu=CC)
    ten = {m["type"] for m in muc}
    assert "app.text.chat" in ten
    assert all({"type", "type_version", "tham_so"} <= set(m) for m in muc)
    prompt = ke_hoach_v3.build_prompt("mục tiêu", muc=muc, ngan_sach_credit=7)
    assert "app.text.chat" in prompt and "[NGAN_SACH] 7" in prompt
    assert "mục tiêu" in prompt


def test_danh_muc_chi_moi_node_PUBLISH_DUOC():
    """⛔ Không mời model kéo một node mà cổng publish sẽ từ chối."""
    muc = ke_hoach_v3.danh_muc(cong_cu=CC)
    dinh_nghia = nut.tat_ca(cong_cu=CC)
    for m in muc:
        assert dinh_nghia[m["type"]].publish_duoc, m["type"]


# ── 3. Đầu ra đi qua ĐÚNG validator publish (§12.2), không bản sao thứ hai ───

def test_tham_chieu_khong_phai_to_tien_bi_tu_choi_bang_MA_CUA_COMPILER():
    doc = ke_hoach_v3.chuan_hoa(_ra_model([
        {"id": "a", "type": "app.text.chat",
         "params": {"prompt": "{{ nodes.b.output.text }}"}},
        {"id": "b", "type": "app.text.chat", "params": {"prompt": "x"}}]))
    hop_le, loi = ke_hoach_v3.kiem(doc, cong_cu=CC)
    assert hop_le is False
    assert [l["ma"] for l in loi] == ["tham_chieu_khong_phai_to_tien"]


def test_loai_node_khong_co_that_bi_tu_choi():
    doc = ke_hoach_v3.chuan_hoa(_ra_model([
        {"id": "a", "type": "app.khong.he.co", "params": {}}]))
    hop_le, loi = ke_hoach_v3.kiem(doc, cong_cu=CC)
    assert hop_le is False and loi[0]["ma"] == "node_khong_ton_tai"


def test_soan_draft_tra_loi_thay_vi_nem_khi_model_bia_do_thi_sai():
    kq = ke_hoach_v3.soan_draft(
        None, goal="x", ngan_sach_credit=1, cong_cu=CC,
        llm_call=lambda _p: _ra_model(
            [{"id": "a", "type": "app.khong.he.co", "params": {}}]))
    assert kq["hop_le"] is False and kq["graph"] is None
    assert kq["loi"][0]["ma"] == "node_khong_ton_tai"


# ── 4. Vị trí do MÃ tính, không do model bịa (bài học n8n) ───────────────────

def test_vi_tri_do_ma_tinh_khong_lay_cua_model():
    doc = ke_hoach_v3.chuan_hoa(_ra_model([
        {"id": "a", "type": "app.text.chat", "params": {},
         "position": {"x": 999999, "y": -12345}},
        {"id": "b", "type": "app.text.chat", "params": {}}]))
    vi_tri = [n["position"] for n in doc["pages"][0]["nodes"]]
    assert vi_tri == [{"x": 0, "y": 0}, {"x": ke_hoach_v3.BUOC_X, "y": 0}]


# ── 5. Đầu ra model là DỮ LIỆU KHÔNG TIN ĐƯỢC ────────────────────────────────

@pytest.mark.parametrize("raw,ma", [
    ("khong phai json", "khong_doc_duoc"),
    ('{"nodes": "khong phai danh sach"}', "hinh_dang_sai"),
    ('{"nodes": [{"id": "A b", "type": "app.text.chat"}]}', "id_khong_hop_le"),
    ('{"nodes": [{"id": "a", "type": "app.text.chat"},'
     ' {"id": "a", "type": "app.text.chat"}]}', "id_trung"),
    ('{"nodes": []}', "do_thi_rong"),
])
def test_dau_ra_model_hong_bi_tu_choi_co_ma(raw, ma):
    with pytest.raises(ke_hoach_v3.LoiSoan) as e:
        ke_hoach_v3.chuan_hoa(raw)
    assert e.value.ma == ma


def test_qua_nhieu_node_bi_tu_choi():
    raw = _ra_model([{"id": f"n{i}", "type": "app.text.chat", "params": {}}
                     for i in range(ke_hoach_v3.MAX_NUT + 1)])
    with pytest.raises(ke_hoach_v3.LoiSoan) as e:
        ke_hoach_v3.chuan_hoa(raw)
    assert e.value.ma == "qua_nhieu_node"


def test_canh_duoc_chuan_hoa_ve_khoa_v3():
    doc = ke_hoach_v3.chuan_hoa(_ra_model(
        [{"id": "a", "type": "app.text.chat", "params": {}},
         {"id": "b", "type": "app.text.chat", "params": {}}],
        [{"source": "a", "target": "b", "source_port": "text",
          "target_port": "prompt"}]))
    e = doc["pages"][0]["edges"][0]
    assert e["source_node"] == "a" and e["target_node"] == "b"
    assert e["kind"] == "DATA" and e["id"]
