"""Nối khoảng cách hai tầng biểu thức ở cổng publish node app/tool (plan
`docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md` §P-B, làn wfb5).

## Khoảng cách ĐÃ ĐO (không suy diễn)

- **Ngôn ngữ §6 đầy đủ** (`platform_core/workflow/bieu_thuc.py`,
  `ham_bieu_thuc.py` — 49 hàm, 7 namespace `loop/nodes/params/run/trigger/
  vars/workflow`) được node LÕI (`core.*`) dùng thẳng qua
  `bien_dich.trich_tham_chieu` (không giới hạn hình dạng theo §6, chỉ cần
  `ast.parse` được).
- **Cổng publish của node app/tool** (`bien_dich._doi`, chạy trong
  `cau_truc()`/`_node()`) trước làn wfb5 chỉ nhận ĐÚNG một hình dạng:
  `{{ nodes.<id>.output.<cổng> }}` — MỘT đoạn duy nhất sau `.output.`, qua
  regex `_THAM_CHIEU`/`la_tham_chieu`. Bằng chứng thật: `test_4190` (FLOW G
  lượt 2, model thật) — `app.video.generate` nhận
  `"{{ nodes.fetch_sheet.output.json.prompt }}"` (đường dẫn LỒNG sau
  `.output.json`) và bị từ chối `bieu_thuc_chua_ho_tro`.

## Bản vá (wfb5)

`_doi` (xem `platform_core/workflow/bien_dich.py`) nay hỏi bộ duyệt HÌNH
DẠNG của chính ngôn ngữ §6 (`ngon_ngu.kiem`, tức
`chinh_sach.kiem_ngon_ngu(cs=chinh_sach.chinh_sach_day_du(ham=BANG_HAM))`)
thay vì tự nới một regex thứ hai — MỘT nguồn luật cho câu hỏi "biểu thức nào
hợp lệ", node lõi và node app/tool cùng hỏi một chỗ (khác chỗ đã hỏi trước
đây).

⛔ **KHÔNG đổi** cổng an ninh tổ tiên (`_tham_chieu_trong`/`trich_tham_chieu`,
`bien_dich()`'s vòng kiểm `to_tien`/`cong_ra_cua`) — nó vẫn là NGUỒN DUY NHẤT
trả lời "node nào là tổ tiên node nào" / "cổng ra có tồn tại", tách biệt khỏi
`_doi` từ trước, không sửa gì ở đây. Các phép kiểm dưới đây CHỦ Ý gọi
`bien_dich.bien_dich()` (cổng THẬT, đủ cả hai tầng), không chỉ gọi `_doi`
riêng — để chứng minh khoảng cách đã nối mà không hạ thấp cổng an ninh kia.

## ⚠️ CHƯA đóng — biên rõ, đọc `bien_dich._doi.__doc__`

Cổng publish rộng ra không kéo theo cầu nối job LÚC CHẠY
(`cau_noi.giai_tham_so`) hay báo giá tham chiếu đơn — cả hai vẫn dùng
`la_tham_chieu` (một regex một-đoạn, không đổi ở làn này) để đọc GIÁ TRỊ
thật. Một `params` publish được với `{{ nodes.a.output.b.c }}` sẽ KHÔNG được
`giai_tham_so` thay giá trị lúc job chạy thật (nó trả nguyên văn chuỗi
`{{ }}` vì `la_tham_chieu` không khớp) — đây là một khoảng cách MỚI, được
flag riêng (xem báo cáo phiên wfb5), KHÔNG đóng trong tệp này.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich
from platform_core.workflow.cong_cu import CongCu


def _cc(ten, returns):
    """⚠️ `returns` là tập cổng ra THẬT — cùng lý do ghi ở `test_1714`."""
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=1, params_schema={},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=lambda p: 1, returns=dict(returns))


CC = {
    "http.fetch": _cc("http.fetch", {"json": "object"}),
    "video.generate": _cc("video.generate", {"video_key": "text"}),
}


def _doc(nodes, edges):
    return {"version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]}


def _node(nid, tool, params=None):
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": params or {}}}


def _canh(eid, a, b, sp="out", tp="in", kind="DATA"):
    return {"id": eid, "source_node": a, "target_node": b,
            "source_port": sp, "target_port": tp, "kind": kind}


# ── 1. Truy cập LỒNG sau .output.<cổng> — ca thật của FLOW G ────────────────

def test_tham_chieu_long_sau_output_duoc_publish():
    """`{{ nodes.a.output.json.prompt }}` — ĐÚNG hình dạng model FLOW G sinh
    ra (`test_4190`). Trước wfb5: `bieu_thuc_chua_ho_tro`. Nay: qua."""
    doc = _doc(
        [_node("fetch_sheet", "http.fetch"),
         _node("create_video", "video.generate",
               {"prompt": "{{ nodes.fetch_sheet.output.json.prompt }}"})],
        [_canh("e1", "fetch_sheet", "create_video", "json", "prompt")])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    cv = next(n for n in g["nodes"] if n["id"] == "create_video")
    assert cv["params"]["prompt"] == \
        "{{ nodes.fetch_sheet.output.json.prompt }}"


def test_to_tien_van_rut_duoc_dung_qua_bieu_thuc_long():
    """Yêu cầu #3 của brief: cấu trúc đồ thị (ai là tổ tiên ai) VẪN đọc được
    xuyên qua một biểu thức §6 lồng — không đoán, đo bằng `cau_truc()`."""
    doc = _doc(
        [_node("fetch_sheet", "http.fetch"),
         _node("create_video", "video.generate",
               {"prompt": "{{ nodes.fetch_sheet.output.json.prompt }}"})],
        [_canh("e1", "fetch_sheet", "create_video", "json", "prompt")])
    ct = bien_dich.cau_truc(doc, cong_cu=CC)
    assert ct.to_tien["create_video"] == {"fetch_sheet"}
    # Tham chiếu lồng vẫn bị TRÍCH ra đúng — cổng an ninh tổ tiên không mù.
    refs = bien_dich._tham_chieu_trong(
        {"prompt": "{{ nodes.fetch_sheet.output.json.prompt }}"})
    assert refs == {bien_dich.ThamChieu("fetch_sheet", "json", "output")}


def test_da_tang_long_van_publish_duoc():
    """`nodes.a.output.b.c.d[0].e` — lồng NHIỀU tầng (subscript + attribute),
    không riêng hai tầng như ca FLOW G."""
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ nodes.a.output.json.b.c[0].d }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    assert g["thu_tu"] == ["a", "b"]


# ── 2. Quyết định "biểu thức §6 có hàm" (bullet #1 của brief) ───────────────
#
# ⭐ QUYẾT ĐỊNH: `_doi` uỷ quyền TOÀN BỘ câu hỏi hình dạng cho `ngon_ngu.kiem`
#   (ngôn ngữ §6 đầy đủ, bảng hàm THẬT `ham_bieu_thuc.BANG_HAM`) — không tự
#   dựng một tập con "chỉ nodes.*, không hàm". Lý do (xem `_doi.__doc__` và
#   `_bieu_thuc_s6_hop_le.__doc__`): (a) node LÕI đã lỏng hơn `ngon_ngu.kiem`
#   từ trước (nhận MỌI `ast.parse` được, không danh sách trắng nút); (b) một
#   tập con tự chọn là một BẢNG THỨ HAI sẽ trôi khỏi §6 đúng như bài học
#   "hai chỗ khai một điều"; (c) khoảng cách CHẠY THẬT (`giai_tham_so`) đã hở
#   kể từ ca lồng-đơn-giản ở trên, cho phép thêm hàm không mở thêm rủi ro mới
#   trên đường tiền — `_doi` vẫn chỉ là cổng HÌNH DẠNG, không phải cổng chạy.

def test_bieu_thuc_co_ham_duoc_publish_theo_quyet_dinh_uy_quyen_s6():
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ upper(nodes.a.output.json.prompt) }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    b = next(n for n in g["nodes"] if n["id"] == "b")
    assert b["params"]["prompt"] == \
        "{{ upper(nodes.a.output.json.prompt) }}"


def test_cong_params_nhan_dong_bo_voi_bien_dich_that_cho_ca_bieu_thuc_co_ham():
    """`cong_params_nhan` (cửa gợi ý) không được nói dối cổng thật."""
    assert bien_dich.cong_params_nhan(
        "upper(nodes.a.output.json.prompt)") is True
    assert bien_dich.cong_params_nhan("round(1.5, 0)") is True


# ── 3. Vẫn từ chối: chuỗi RÁC (tên không thuộc namespace §6.2) ──────────────

def test_bieu_thuc_rac_van_bi_tu_choi():
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ khong_ton_tai.bay_bay }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "bieu_thuc_chua_ho_tro"
    assert e.value.node_id == "b"
    assert bien_dich.cong_params_nhan("khong_ton_tai.bay_bay") is False


def test_bieu_thuc_khong_phan_tich_duoc_van_bi_tu_choi():
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate", {"prompt": "{{ nodes.a.output.x + }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "bieu_thuc_chua_ho_tro"


# ── 4. Vẫn từ chối: tham chiếu tới node KHÔNG TỒN TẠI ───────────────────────
#
# ⭐ `_doi` (hình dạng) không biết đồ thị — cổng chặn ca này là cổng tổ tiên
#   `bien_dich()`, xảy ra SAU `cau_truc()`. Phép kiểm dưới chứng minh biểu
#   thức LỒNG mới không lách được cổng đó, dù đã lách được `_doi`.

def test_tham_chieu_node_khong_ton_tai_van_bi_tu_choi_du_da_qua_doi():
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ nodes.ma_khong_co.output.json.prompt }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    # Hình dạng qua được _doi (không phải rác) — chứng minh cổng SAU mới là
    # cổng thật sự chặn.
    assert bien_dich.cong_params_nhan(
        "nodes.ma_khong_co.output.json.prompt") is True
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_node_khong_ton_tai"
    assert "ma_khong_co" in str(e.value)


def test_tham_chieu_khong_phai_to_tien_van_bi_tu_choi_qua_bieu_thuc_long():
    """`a`, `b` SONG SONG (không cạnh a->b) — `b` đọc lồng vào `a` vẫn sai."""
    doc = _doc(
        [_node("a", "http.fetch"), _node("root", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ nodes.a.output.json.prompt }}"})],
        [_canh("e1", "root", "a", "json", "in"),
         _canh("e2", "root", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"
    assert e.value.node_id == "b"


def test_cong_ra_khong_ton_tai_van_bi_tu_choi_qua_bieu_thuc_long():
    """`fetch_sheet` không có cổng `json_sai` — cổng RA phải khớp `returns`
    thật của tool, kể cả khi đường dẫn SAU cổng đó lồng sâu."""
    doc = _doc(
        [_node("fetch_sheet", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ nodes.fetch_sheet.output.json_sai.prompt }}"})],
        [_canh("e1", "fetch_sheet", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "cong_khong_ton_tai"


def test_tu_tham_chieu_van_bi_tu_choi_qua_bieu_thuc_long():
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "{{ nodes.b.output.json.prompt }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"
    assert e.value.node_id == "b"


# ── 5. Tiêm lỗi: nới LỎNG QUÁ TAY thì bài nào lộ ────────────────────────────
#
# ⭐ Brief đòi rõ: "nếu ai đó nới lỏng quá tay thì bài nào đỏ". Ba ca dưới đây
#   khoá lại ĐÚNG ba ranh giới còn lại sau bản vá — nếu một bản sửa sau này
#   thay `_bieu_thuc_s6_hop_le` bằng `lambda *_: True` (nới mù quáng, bỏ qua
#   bộ duyệt §6 thật) hoặc bỏ yêu cầu "trọn chuỗi MỘT khối `{{ }}`", các phép
#   dưới đây đỏ ngay.

def test_noi_suy_nhieu_doan_trong_mot_chuoi_van_bi_tu_choi():
    """`noi_suy.py` (nội suy nhiều đoạn trong MỘT chuỗi) CHƯA có — một chuỗi
    có chữ bao quanh `{{ }}` vẫn phải bị từ chối, không được vô tình nhận vì
    bộ duyệt §6 mới rộng hơn."""
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"prompt": "Vẽ: {{ nodes.a.output.json.prompt }} nhé"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "bieu_thuc_chua_ho_tro"
    assert bien_dich.cong_params_nhan(
        "nodes.a.output.json.prompt") is True, (
        "chinh doan {{ }} do, tach rieng, PHAI qua — de loai tru ca "
        "_bieu_thuc_s6_hop_le tu choi nham")


def test_tham_chieu_nodes_co_doan_dong_van_bi_tu_choi():
    """`nodes[params.ten_node]` — chỉ số ĐỘNG vào `nodes`. Cấm ở CẢ HAI lớp
    (`chinh_sach.DAY_DU.goc_phai_tinh="nodes"` lẫn
    `trich_tham_chieu`/`_goc_la_nodes`) — cùng một luật, hai cửa cùng khoá."""
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate",
               {"ten_node": "a",
                "prompt": "{{ nodes[params.ten_node].output.json }}"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "bieu_thuc_chua_ho_tro"
    assert bien_dich._bieu_thuc_s6_hop_le(
        "nodes[params.ten_node].output.json") is False


def test_gia_tri_khong_chua_hai_ngoac_van_giu_nguyen_khong_phai_bieu_thuc():
    """Về đối chứng chốt lại `_CU`: `"item.title"` (chuỗi trần, không bọc
    `{{ }}`, như lượt 1 FLOW G) không bao giờ đi vào nhánh biểu thức — cổng
    mới không vô tình bắt các chuỗi trần thường ngày."""
    doc = _doc(
        [_node("a", "http.fetch"),
         _node("b", "video.generate", {"prompt": "item.title"})],
        [_canh("e1", "a", "b", "json", "prompt")])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    b = next(n for n in g["nodes"] if n["id"] == "b")
    assert b["params"]["prompt"] == "item.title"
