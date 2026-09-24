"""Compiler draft v3 → ltt.workflow/3 (spec §4.1–4.3)."""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich
from platform_core.workflow.cong_cu import CongCu


def _cc(ten, gia=5, returns=None):
    # ⚠️ `returns` KHÔNG còn để trống được: nó là tập cổng ra thật của tool, và
    #    validator §6.2 kiểm `nodes.<id>.output.<cổng>` bằng chính tập này. Một
    #    `CongCu` giả không khai `returns` là một node KHÔNG có cổng ra nào —
    #    mọi tham chiếu tới nó phải đỏ, và đó là hành vi đúng.
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2, params_schema={},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=lambda p, g=gia: g,
                  returns=dict(returns or {"text": "text"}))


CC = {"image.generate": _cc("image.generate",
                            returns={"image_keys": "image[]", "prompt": "text"}),
      "text.chat": _cc("text.chat", 1)}


def _doc(pages):
    return {"version": 3, "pages": pages}


def _node(nid, tool, params=None):
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": params or {}}}


def _canh(eid, a, b, sp="out", tp="in", kind="DATA"):
    return {"id": eid, "source_node": a, "target_node": b,
            "source_port": sp, "target_port": tp, "kind": kind}


def test_gop_moi_trang_va_doi_node_cu_sang_app():
    doc = _doc([
        {"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
        {"id": "p2", "nodes": [_node("b", "image.generate")], "edges": []},
    ])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    assert g["schema"] == "ltt.workflow/3"
    assert {n["id"]: n["type"] for n in g["nodes"]} == {
        "a": "app.text.chat", "b": "app.image.generate"}
    assert all(n["type_version"] == 2 and n["thi_hanh"] == "job"
               for n in g["nodes"])
    assert g["settings"] == {"max_concurrency": 4, "timeout_s": 21600}


def test_tham_chieu_cu_doi_sang_bieu_thuc():
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"),
        _node("b", "image.generate", {"prompt": "$a.text", "count": 2})],
        "edges": [_canh("e1", "a", "b", "text", "prompt")]}])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    b = next(n for n in g["nodes"] if n["id"] == "b")
    assert b["params"] == {"prompt": "{{ nodes.a.output.text }}", "count": 2}
    assert bien_dich.la_tham_chieu(b["params"]["prompt"]) == ("a", "text")
    assert g["thu_tu"] == ["a", "b"]


@pytest.mark.parametrize("pages,ma", [
    ([{"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
      {"id": "p2", "nodes": [_node("a", "text.chat")], "edges": []}], "id_trung"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
      {"id": "p2", "nodes": [_node("b", "text.chat")],
       "edges": [_canh("e", "a", "b")]}], "canh_khac_trang"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat"), _node("b", "text.chat")],
       "edges": [_canh("e1", "a", "b"), _canh("e2", "b", "a")]}], "chu_trinh"),
    ([{"id": "p1", "nodes": [_node("a", "khong.co")], "edges": []}],
     "node_khong_ton_tai"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat",
                                   {"x": "Xin {{ trigger.body }}"})],
       "edges": []}], "bieu_thuc_chua_ho_tro"),
    ([{"id": "p1", "nodes": [_node("a" * 65, "text.chat")], "edges": []}],
     "id_khong_hop_le"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat")],
       "edges": [_canh("e", "a", "a", kind="MAGIC")]}], "canh_khong_hop_le"),
])
def test_tu_choi_co_ma(pages, ma):
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(_doc(pages), cong_cu=CC)
    assert e.value.ma == ma


def test_do_thi_rong_bi_tu_choi():
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(_doc([{"id": "p1", "nodes": [], "edges": []}]),
                            cong_cu=CC)
    assert e.value.ma == "do_thi_rong"


def test_tham_chieu_toi_node_khong_phai_to_tien():
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"), _node("b", "text.chat", {"q": "$a.text"})],
        "edges": []}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"


def test_tat_ca_tra_ve_text_chat_tu_registry_that():
    """Bảo vệ adapter khỏi trôi so với registry thật — không mock.

    `text.chat` sống ở app `ltt_llm` (`apps/ltt_llm/manifest.py`); nếu tên
    tool, job_type hay app_slug đổi mà adapter `cong_cu.tat_ca()` không theo
    kịp, phép này đỏ trước khi compiler dùng dữ liệu sai lặng lẽ.
    """
    from platform_core.workflow import cong_cu

    ra = cong_cu.tat_ca()
    assert "text.chat" in ra
    assert ra["text.chat"].app_slug == "ltt_llm"


# ── Task 7 (P2): validator tham chiếu TỔ TIÊN + cổng tồn tại (spec §6.2) ─────
#
# 🔑 Chặn ở PUBLISH. Lúc chạy thì run đã tạo, tiền đã giữ chỗ — từ chối khi ấy
#    là từ chối sau khi đã hứa.
#
# ⭐ Tra nguồn (plan §6.2): n8n và Activepieces **không** chặn ở publish.
#    - Activepieces: `flowStructureUtil.findPathToStep` (tập tổ tiên) chỉ được
#      gọi từ `packages/web/src/app/builder/data-selector/index.tsx` và
#      `flow-canvas/utils/flow-canvas-utils.ts` — tức là một GỢI Ý của giao
#      diện, không có bản sao nào trên đường publish của server.
#    - n8n: `getParentNodes` (`packages/workflow/src/common/get-parent-nodes.ts`)
#      chỉ được `workflow-data-proxy.ts` dùng LÚC CHẠY.
#    ⇒ Điều học được không phải "cách chặn" mà "cách TÍNH tập tổ tiên", và một
#      chi tiết: `findPathToStep` lọc bỏ chính bước đích
#      (`.filter((step) => step.name !== targetStepName)`) — **một node không
#      phải tổ tiên của chính nó**. Đó là nguồn cho quyết định tự-tham-chiếu.


def test_doi_chung_tham_chieu_to_tien_van_publish_duoc():
    """VẾ ĐỐI CHỨNG — thiếu nó thì một bản vá từ chối TẤT CẢ cũng xanh.

    `a -> b -> c`; `c` đọc output của `a` (tổ tiên GIÁN TIẾP, không có cạnh
    trực tiếp). Đây là ca Canvas dùng nhiều nhất, và nó **phải qua**.
    """
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"),
        _node("b", "text.chat", {"q": "$a.text"}),
        _node("c", "image.generate", {"prompt": "$a.text", "n": "$b.text"})],
        "edges": [_canh("e1", "a", "b"), _canh("e2", "b", "c")]}])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    assert g["thu_tu"] == ["a", "b", "c"]
    c = next(n for n in g["nodes"] if n["id"] == "c")
    assert c["params"] == {"prompt": "{{ nodes.a.output.text }}",
                           "n": "{{ nodes.b.output.text }}"}


def test_tham_chieu_node_sau_trong_thu_tu_bi_tu_choi():
    """Hai nhánh SONG SONG: `a->b`, `a->c`. `c` đọc `b` — `b` không là tổ tiên."""
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"), _node("b", "text.chat"),
        _node("c", "text.chat", {"q": "$b.text"})],
        "edges": [_canh("e1", "a", "b"), _canh("e2", "a", "c")]}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"
    assert e.value.node_id == "c"
    # Thông điệp phải nói rõ NODE nào và CỔNG nào — người dùng đang nhìn Canvas.
    assert "b" in str(e.value) and "text" in str(e.value)


def test_tham_chieu_node_khong_ton_tai_bi_tu_choi():
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat", {"q": "$khongcoai.text"})], "edges": []}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_node_khong_ton_tai"
    assert "khongcoai" in str(e.value)


def test_tham_chieu_cong_khong_ton_tai_bi_tu_choi():
    """⭐ Ca DỄ QUÊN: node có thật, là tổ tiên thật, nhưng cổng thì không có."""
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"),
        _node("b", "text.chat", {"q": "$a.khong_co_cong_nay"})],
        "edges": [_canh("e1", "a", "b")]}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "cong_khong_ton_tai"
    assert e.value.node_id == "b"
    # Nói cả cổng sai LẪN các cổng có thật — nếu không, người dùng phải đoán.
    assert "khong_co_cong_nay" in str(e.value) and "text" in str(e.value)


def test_tu_tham_chieu_bi_tu_choi():
    """QUYẾT ĐỊNH: một node KHÔNG phải tổ tiên của chính nó ⇒ từ chối.

    Lý do đo được, không phải quy ước: lúc động cơ tính `params` của `a`, node
    `a` chưa chạy nên `nodes.a.output` **chưa tồn tại**. Và đồ thị là DAG nên
    `a` không bao giờ vào được `to_tien[a]` — cho qua sẽ là một lời hứa mà
    runtime chắc chắn không giữ được. Trùng với Activepieces (`findPathToStep`
    lọc bỏ chính bước đích).
    """
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat", {"q": "$a.text"})], "edges": []}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"
    assert e.value.node_id == "a"
    assert "CHINH NO" in str(e.value)


def test_to_tien_TRONG_THAN_foreach__cau_tra_loi_cua_Task_5():
    """Cái chuông tác giả treo sẵn: *"ngày P3 mở `core.*`, nó đỏ, và người mở
    phải quay lại đây quyết định tổ tiên trong thân vòng lặp nghĩa là gì."*

    ## Câu trả lời

    **Luật tổ tiên §6.2 KHÔNG đổi.** Nó nói về đồ thị đã biên dịch, và thân vòng
    lặp là một đoạn của chính đồ thị ấy: node thân đọc được node thân đứng
    trước nó vì node ấy **là** tổ tiên theo `graph.thu_tu`. Không có luật thứ hai.

    **Thứ Task 5 thêm là GIÁ TRỊ, không phải QUAN HỆ.** Trong thân, một tham
    chiếu `nodes.<x>.output` trả giá trị của **vòng đang chạy**
    (`nut_loi/vong_lap._mt_than` phủ ảnh chụp CSDL bằng output của vòng ấy), và
    `loop.item/index/total` tồn tại. Ngoài thân, cùng tham chiếu ấy trả giá trị
    của **vòng CUỐI** — vì `node_run` khoá theo `(run_id, node_id)` nên chỉ một
    trạng thái sống sót. ⛔ Muốn cả tập thì đọc `foreach_end.output.results`.

    **Ranh giới đã khai:** thân chỉ nhận node `inline`; thân có node job bị từ
    chối lúc publish (`than_foreach_co_node_job`) — xem `test_1784`.
    """
    from platform_core.workflow import nut_loi
    so = nut_loi.tat_ca()
    assert "core.foreach" in so and "core.foreach_end" in so

    doc = _doc([{"id": "p1", "nodes": [
        {"id": "f", "type": "core.foreach",
         "params": {"items": "[1]", "max_items": 5}},
        {"id": "x", "type": "core.transform", "params": {"gia_tri": "loop.item"}},
        {"id": "y", "type": "core.transform",
         "params": {"gia_tri": "nodes.x.output.gia_tri"}},
        {"id": "fe", "type": "core.foreach_end", "params": {"foreach": "f"}}],
        "edges": [
            {"id": "e1", "source_node": "f", "target_node": "x"},
            {"id": "e2", "source_node": "x", "target_node": "y"},
            {"id": "e3", "source_node": "y", "target_node": "fe"}]}])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    assert [n["thi_hanh"] for n in g["nodes"]] == ["inline"] * 4

    # ⛔ Và luật tổ tiên vẫn CẮN trong thân: `x` đọc `y` là đọc ngược.
    doc["pages"][0]["nodes"][1]["params"]["gia_tri"] = "nodes.y.output.gia_tri"
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"


# ── Bộ TRÍCH tham chiếu, đo riêng ────────────────────────────────────────────
#
# ⚠️ Vì sao đo riêng: `_doi` hôm nay CHỈ cho qua chuỗi `{{ nodes.a.output.b }}`
#    nguyên vẹn, nên qua `bien_dich()` không chạm tới được biểu thức ghép. Bộ
#    trích thì phải đúng TRƯỚC ngày Task 2 mở cú pháp — nếu nó bỏ sót một tham
#    chiếu nằm trong biểu thức ghép, cổng mở đúng vào hôm cú pháp mở ra.

TC = bien_dich.ThamChieu


@pytest.mark.parametrize("bt,mong", [
    ("nodes.a.output.text", [TC("a", "text", "output")]),
    ("nodes.a.output.text + nodes.b.output.q",
     [TC("a", "text", "output"), TC("b", "q", "output")]),
    ('nodes.a.output["text"]', [TC("a", "text", "output")]),
    ('nodes["a"].output.text', [TC("a", "text", "output")]),
    # Điều hướng SÂU trong một cổng: cổng vẫn là `text`.
    ("nodes.a.output.text.mot.hai", [TC("a", "text", "output")]),
    ("nodes.a.output.items[0]", [TC("a", "items", "output")]),
    ("nodes.a.status", [TC("a", "", "status")]),
    ("nodes.a.error", [TC("a", "", "error")]),
    ("len(nodes.a.output.text) if nodes.b.status == 'SUCCEEDED' else 0",
     [TC("a", "text", "output"), TC("b", "", "status")]),
    # Namespace khác: không phải việc của bộ trích này.
    ("trigger.body.x + workflow.input.y + vars.z + loop.item", []),
    ("1 + 2", []),
])
def test_trich_tham_chieu(bt, mong):
    assert sorted(bien_dich.trich_tham_chieu(bt)) == sorted(mong)


@pytest.mark.parametrize("bt,ma", [
    ("nodes", "tham_chieu_khong_hop_le"),
    ("nodes.a", "tham_chieu_khong_hop_le"),
    ("nodes.a.output", "tham_chieu_khong_hop_le"),      # thiếu tên cổng
    ("nodes.a.params.x", "tham_chieu_khong_hop_le"),    # không phải output
    ("nodes.a._an.x", "tham_chieu_khong_hop_le"),
    ("nodes[ten_bien].output.x", "tham_chieu_dong"),    # id động
    ("nodes.a.output[i]", "tham_chieu_dong"),           # cổng động
    ("nodes.a.output.x +", "bieu_thuc_chua_ho_tro"),    # không phân tích được
])
def test_trich_tham_chieu_that_bai_dong_cua(bt, ma):
    """⛔ FAIL-CLOSED: thứ bộ trích không đọc nổi phải bị TỪ CHỐI, không bỏ qua.

    Bỏ qua một biểu thức khó đọc nghĩa là nó đi thẳng qua cổng tổ tiên — đúng
    hạng khiếm khuyết `canh.truyen` đã ghi: *"nuốt lỗi rồi trả True là mở cổng
    khi bộ gác ngã"*.
    """
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.trich_tham_chieu(bt)
    assert e.value.ma == ma


@pytest.mark.parametrize("chuoi,mong", [
    ("{{ nodes.a.output.text }}", ["nodes.a.output.text"]),
    ("Xin chao {{ a }} va {{ b }}!", ["a", "b"]),
    ("khong co gi", []),
    # `\\{{` la chu thuong (spec §6.1) — khong phai mot bieu thuc.
    (r"\{{ nodes.a.output.text }}", []),
    (r"\{{ giu nguyen }} nhung {{ nodes.a.output.text }} thi khong",
     ["nodes.a.output.text"]),
])
def test_doan_bieu_thuc(chuoi, mong):
    assert list(bien_dich.doan_bieu_thuc(chuoi)) == mong


def test_doan_bieu_thuc_khong_dong_ngoac_bi_tu_choi():
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.doan_bieu_thuc("{{ nodes.a.output.text")
    assert e.value.ma == "bieu_thuc_chua_ho_tro"
