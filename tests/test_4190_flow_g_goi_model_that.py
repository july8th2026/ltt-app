"""FLOW G — HAI lượt gọi model THẬT qua máy B (plan wf-v2 P-B, làn wfb4).

`tests/test_2935_flow_g.py` chỉ tiêm **dữ liệu vàng** (`_do_thi_vang`) — chưa
bao giờ chạm `ltt-3.5` thật. Tệp này đóng khoảng trống đó bằng **hai** lượt
gọi thật (25/09/2026), cả hai qua `platform_core.agent.ke_hoach_v3.soan_draft`
KHÔNG `llm_call` (đúng đường `planner.goi_model` → `admission` →
`dieu_phoi.goi` → máy B), CÙNG câu `CAU`, CÙNG model `ltt-3.5`
(`Qwen3.5-9B-Q6_K`, 5060 Ti — rẻ nhất trong hai model nội bộ, đúng
`canonical.MODEL_NOI_BO_MAC_DINH`).

## LƯỢT 1 (trước khi sửa prompt) — 53,25 s, 6 632 vào / 2 990 ra

`_LOT1_25_09` là nguyên văn `document` model trả về. Bị `bien_dich.bien_dich()`
từ chối ngay node đầu (`node_khong_ton_tai` cho `"type": "core.http@1"`).
Không phải model kém — `core.http` (bỏ hậu tố) nằm đúng trong danh mục
publish_duoc. Hai lỗ THẬT trong `build_prompt()` cũ:

1. Danh mục cũ viết dính `type@type_version` (`- core.http@1 (job): ...`) —
   model chép NGUYÊN chuỗi hiển thị vào trường `type` của **cả 8 node**. Bài
   học "ví dụ trong lời nhắc là mệnh lệnh ngầm": model học HÌNH THỨC hiển
   thị, không học lược đồ JSON.
2. Mẫu JSON cũ liệt `"kind"` như một khoá rỗng, KHÔNG nói giá trị hợp lệ
   (`bien_dich._KIND = {"DATA","CONTROL","ERROR"}`). Model đoán `"json"` cho
   cả 7 cạnh.

Sửa `build_prompt()` (danh mục tách `type=`/`type_version=`/`kind=`; thêm
`[QUY_UOC_KIND]`; `[DAU_RA]` cấm nối `@version` vào `type`).

## LƯỢT 2 (SAU khi sửa, cùng câu, cùng model) — 40,00 s, 6 919 vào / 2 746 ra

⭐ Gọi lại đúng như điều phối viên yêu cầu — KHÔNG kiểm bản vá trên draft lượt
1 đã đông băng (đó là một **bản đại diện**, không phải model thật). `_LOT2_25_09`
là nguyên văn document của lượt này.

**Hai lỗi cũ ĐÃ HẾT, đo trực tiếp trên máy, không suy diễn**: không node nào
có hậu tố `@version` trong `type`; `kind` chỉ dùng `DATA`/`CONTROL` (model
còn tự phân biệt đúng: cạnh nhánh `true` của `core.if` được gắn `CONTROL`,
các cạnh còn lại `DATA` — đúng ngữ nghĩa `_KIND`, không phải khớp ngẫu nhiên).

**NHƯNG draft lượt 2 VẪN không biên dịch được — vì một lý do KHÁC, không liên
quan tới bản vá**: `create_video` dùng `"{{ nodes.fetch_sheet.output.json.prompt }}"`
— `_THAM_CHIEU` (regex `^\\{\\{\\s*nodes\\.ID\\.output\\.CONG\\s*\\}\\}$`,
xem `platform_core/workflow/bien_dich.py`) CHỈ nhận đúng MỘT đoạn sau
`.output.`; đường dẫn lồng `.output.json.prompt` không khớp ⇒ `_doi()` ném
`bieu_thuc_chua_ho_tro`. Đoạn regex này KHÔNG nằm trong lượt sửa vừa rồi —
nó có từ trước, và lượt 1 không chạm tới nó vì các tham số lượt 1 dùng chuỗi
trần (`"item.title"`, không bọc `{{ }}`) nên `_doi()` không xét nhánh này.
Lượt 2 mới thật sự thử cú pháp `{{ nodes... }}` mà `[DAU_RA]` yêu cầu — và lộ
ra giới hạn CHƯA TỪNG ĐO của cổng biên dịch: nó không hỗ trợ truy cập lồng
sau `output.<cong>`.

## ⚠️ Lượt 2 KHÔNG còn `core.filter`/`core.foreach` — CHƯA rõ có phải do bản vá

Lượt 2 chỉ có 6 node (`core.http`, `core.if`, `app.video.generate`,
`core.human`, `core.output`, `core.stop`) — xử một hàng đơn bằng nhánh điều
kiện, KHÔNG lọc-rồi-lặp nhiều hàng như lượt 1. `build_prompt()` không đổi gì
về hướng dẫn lọc/lặp (chỉ đổi cách hiển thị danh mục + thêm khối kind), và
`core.filter`/`core.foreach` vẫn nằm nguyên trong danh mục gửi cho model
(`test_danh_muc_van_co_filter_va_foreach`). ⛔ KHÔNG đủ căn cứ để nói bản vá
"làm tụt" kiến trúc filter+foreach — cũng KHÔNG đủ căn cứ để nói nó KHÔNG
liên quan. **N=1 mỗi phía, không so sánh được.** Đây là đúng thứ so tay cảnh
báo (`vi-du-trong-loi-nhac-la-menh-lenh-ngam.md`: sửa lời nhắc phải đo lại CẢ
TẬP) — và đúng lý do KHÔNG gọi lượt 3 ở đây: cần nhiều mẫu mỗi phía để tách
tín hiệu khỏi nhiễu lấy mẫu của chính model, không phải vá thêm một câu nữa
rồi đoán tiếp. Việc đó cần chủ trì, không phải một lượt vá đơn lẻ.

## ⛔ Sheets/cron thật — vẫn KHÔNG phải chỗ tệp này chốt

`piece.google_sheets.find_rows` có trong registry nhưng `publish_duoc=False`
cứng (`nut.py::tu_piece()`, chờ "plan 08"/P-C mở runner Node cho `piece.*`).
Cả hai lượt đều không dùng — không nằm trong danh mục gửi cho model. FLOW G
đủ 6/6 với Sheets THẬT vẫn CHƯA đạt.
"""
from __future__ import annotations

import copy
import re

import pytest

from platform_core.agent import ke_hoach_v3
from platform_core.workflow import bao_gia, bien_dich, cong_cu, nut

CAU = "Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"


@pytest.fixture(scope="module")
def cc():
    return cong_cu.tat_ca()


#: Nguyên văn `document` (`ke_hoach_v3.chuan_hoa`) LƯỢT 1 — TRƯỚC khi sửa
#: `build_prompt()`. KHÔNG sửa tay — bằng chứng, không phải fixture.
_LOT1_25_09 = {
    "version": 3,
    "pages": [{
        "id": "p1", "name": "Trang 1",
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "nodes": [
            {"id": "fetch_sheet", "type": "core.http@1", "type_version": 1,
             "position": {"x": 0, "y": 0}, "label": "",
             "params": {"url": "https://api.example.com/sheet/daily_ready",
                        "than": "", "cach": "GET"},
             "credential_ref": "", "settings": {}},
            {"id": "parse_data", "type": "core.transform@1", "type_version": 1,
             "position": {"x": 280, "y": 0}, "label": "",
             "params": {"gia_tri": "JSON.parse(fetch_sheet.than)"},
             "credential_ref": "", "settings": {}},
            {"id": "filter_ready", "type": "core.filter@1", "type_version": 1,
             "position": {"x": 560, "y": 0}, "label": "",
             "params": {"items": "parse_data.gia_tri",
                        "dieu_kien": "item.status == 'READY'"},
             "credential_ref": "", "settings": {}},
            {"id": "loop_videos", "type": "core.foreach@1", "type_version": 1,
             "position": {"x": 840, "y": 0}, "label": "",
             "params": {"items": "filter_ready.results", "max_items": 100,
                        "parallelism": 4},
             "credential_ref": "", "settings": {}},
            {"id": "generate_video", "type": "app.video.generate@1",
             "type_version": 1, "position": {"x": 1120, "y": 0}, "label": "",
             "params": {"prompt": "item.title", "model": "seedance-v1"},
             "credential_ref": "", "settings": {}},
            {"id": "collect_results", "type": "core.foreach_end@1",
             "type_version": 1, "position": {"x": 1400, "y": 0}, "label": "",
             "params": {"foreach": "loop_videos"},
             "credential_ref": "", "settings": {}},
            {"id": "human_review", "type": "core.human@1", "type_version": 1,
             "position": {"x": 0, "y": 160}, "label": "",
             "params": {"cau_hoi": "Xác nhận video đã tạo"},
             "credential_ref": "", "settings": {}},
            {"id": "output_result", "type": "core.output@1", "type_version": 1,
             "position": {"x": 280, "y": 160}, "label": "",
             "params": {"ten": "video_keys",
                        "gia_tri": "collect_results.results"},
             "credential_ref": "", "settings": {}},
        ],
        "edges": [
            {"id": "e1", "source_node": "fetch_sheet", "target_node": "parse_data",
             "source_port": "than", "target_port": "gia_tri", "kind": "json",
             "condition": ""},
            {"id": "e2", "source_node": "parse_data", "target_node": "filter_ready",
             "source_port": "gia_tri", "target_port": "items", "kind": "json",
             "condition": ""},
            {"id": "e3", "source_node": "filter_ready", "target_node": "loop_videos",
             "source_port": "results", "target_port": "items", "kind": "json",
             "condition": ""},
            {"id": "e4", "source_node": "loop_videos", "target_node": "generate_video",
             "source_port": "results", "target_port": "in", "kind": "json",
             "condition": ""},
            {"id": "e5", "source_node": "generate_video",
             "target_node": "collect_results", "source_port": "video_key",
             "target_port": "in", "kind": "json", "condition": ""},
            {"id": "e6", "source_node": "collect_results",
             "target_node": "human_review", "source_port": "results",
             "target_port": "in", "kind": "json", "condition": ""},
            {"id": "e7", "source_node": "human_review",
             "target_node": "output_result", "source_port": "du_lieu",
             "target_port": "gia_tri", "kind": "json", "condition": ""},
        ],
    }],
}

#: Nguyên văn `document` LƯỢT 2 — SAU khi sửa `build_prompt()`, gọi lại thật,
#: cùng câu `CAU`, cùng model. KHÔNG sửa tay.
_LOT2_25_09 = {
    "version": 3,
    "pages": [{
        "id": "p1", "name": "Trang 1",
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "nodes": [
            {"id": "fetch_sheet", "type": "core.http", "type_version": 1,
             "position": {"x": 0, "y": 0}, "label": "",
             "params": {"url": "https://sheets.example.com/morning_task",
                        "cach": "GET"},
             "credential_ref": "", "settings": {}},
            {"id": "check_ready", "type": "core.if", "type_version": 1,
             "position": {"x": 280, "y": 0}, "label": "",
             "params": {"dieu_kien":
                        "{{ nodes.fetch_sheet.output.json.status === 'READY' }}"},
             "credential_ref": "", "settings": {}},
            {"id": "create_video", "type": "app.video.generate",
             "type_version": 1, "position": {"x": 560, "y": 0}, "label": "",
             "params": {"prompt": "{{ nodes.fetch_sheet.output.json.prompt }}",
                        "model": "seedance-pro", "duration": 10,
                        "generate_audio": True},
             "credential_ref": "", "settings": {}},
            {"id": "wait_human", "type": "core.human", "type_version": 1,
             "position": {"x": 840, "y": 0}, "label": "",
             "params": {"cau_hoi": "Bạn đã duyệt video này chưa? (Duyệt để tiếp tục)"},
             "credential_ref": "", "settings": {}},
            {"id": "finalize", "type": "core.output", "type_version": 1,
             "position": {"x": 1120, "y": 0}, "label": "",
             "params": {"ten": "video_result",
                        "gia_tri": "{{ nodes.create_video.output.video_key }}"},
             "credential_ref": "", "settings": {}},
            {"id": "finish", "type": "core.stop", "type_version": 1,
             "position": {"x": 1400, "y": 0}, "label": "",
             "params": {"trang_thai": "SUCCEEDED"},
             "credential_ref": "", "settings": {}},
        ],
        "edges": [
            {"id": "e1", "source_node": "fetch_sheet", "target_node": "check_ready",
             "source_port": "json", "target_port": "in", "kind": "DATA",
             "condition": ""},
            {"id": "e2", "source_node": "check_ready", "target_node": "create_video",
             "source_port": "true", "target_port": "in", "kind": "CONTROL",
             "condition": ""},
            {"id": "e3", "source_node": "create_video", "target_node": "wait_human",
             "source_port": "video_key", "target_port": "in", "kind": "DATA",
             "condition": ""},
            {"id": "e4", "source_node": "wait_human", "target_node": "finalize",
             "source_port": "du_lieu", "target_port": "in", "kind": "DATA",
             "condition": ""},
            {"id": "e5", "source_node": "finalize", "target_node": "finish",
             "source_port": "gia_tri", "target_port": "in", "kind": "DATA",
             "condition": ""},
        ],
    }],
}


# ── LƯỢT 1 ────────────────────────────────────────────────────────────────

def test_lot1_NGUYEN_VAN_bi_tu_choi_dung_ma_da_do(cc):
    """Đóng băng lý do thật của lượt 1 — không phải lời kể lại."""
    with pytest.raises(bien_dich.LoiBienDich) as exc:
        bien_dich.bien_dich(copy.deepcopy(_LOT1_25_09), cong_cu=cc)
    assert exc.value.ma == "node_khong_ton_tai"
    assert exc.value.node_id == "fetch_sheet"


def test_lot1_sua_dung_hai_loi_thi_bien_dich_duoc(cc):
    """Sửa ĐÚNG hai điểm prompt mới đòi hỏi lên draft lượt 1 (không gọi lại
    model) — chứng minh cổng biên dịch vốn nhận được hình dạng model sinh
    ra; chỉ prompt (khi đó) cản nó."""
    doc = copy.deepcopy(_LOT1_25_09)
    for n in doc["pages"][0]["nodes"]:
        n["type"] = re.sub(r"@\d+$", "", n["type"])
    for e in doc["pages"][0]["edges"]:
        assert e["kind"] == "json"          # đúng lỗi thật, trước khi sửa
        e["kind"] = "DATA"

    graph = bien_dich.bien_dich(doc, cong_cu=cc)
    assert graph["thu_tu"][0] == "fetch_sheet"
    assert graph["thu_tu"][-1] == "output_result"
    loai = {n["type"] for n in graph["nodes"]}
    assert {"core.filter", "core.foreach", "core.foreach_end",
            "app.video.generate", "core.human"} <= loai

    bg = bao_gia.bao_gia_do_thi(graph, cong_cu=cc)
    assert bg.toi_da > 0 and bg.uoc_tinh > 0


# ── LƯỢT 2 (gọi lại thật SAU khi sửa prompt) ────────────────────────────────

def test_lot2_khong_con_hau_to_type_khong_con_kind_la(cc):
    """Đo trực tiếp trên lượt gọi thật thứ hai — không suy diễn từ lượt 1.

    ⭐ Đây là câu trả lời cho "bản vá có đúng không": ĐÚNG, hai lỗi cũ hết
    thật trên một lượt gọi model SỐNG, không phải trên draft đã đông băng.
    """
    for n in _LOT2_25_09["pages"][0]["nodes"]:
        assert not re.search(r"@\d+$", n["type"]), n
    for e in _LOT2_25_09["pages"][0]["edges"]:
        assert e["kind"] in {"DATA", "CONTROL", "ERROR"}, e
    # Model tự phân biệt CONTROL (nhánh `if`) với DATA (mọi cạnh còn lại) —
    # không phải khớp ngẫu nhiên với 1 trong 3 giá trị.
    kinds = {e["source_node"]: e["kind"] for e in _LOT2_25_09["pages"][0]["edges"]}
    assert kinds["check_ready"] == "CONTROL"


def test_lot2_van_KHONG_bien_dich_duoc_NHUNG_ly_do_khac_va_khong_lien_quan_ban_va(cc):
    """Lượt 2 vẫn đỏ — vì một giới hạn cổng biên dịch CÓ TRƯỚC bản vá, không
    do bản vá gây ra (bản vá không chạm quy tắc biểu thức `{{ }}`)."""
    with pytest.raises(bien_dich.LoiBienDich) as exc:
        bien_dich.bien_dich(copy.deepcopy(_LOT2_25_09), cong_cu=cc)
    assert exc.value.ma == "bieu_thuc_chua_ho_tro"
    assert exc.value.node_id == "create_video"

    # ⭐ Chỉ ra ĐÚNG giới hạn, bằng chính hàm compiler dùng để phán quyết
    # (`la_tham_chieu`, regex `_THAM_CHIEU`) — không suy diễn qua vá cả tài
    # liệu. `_THAM_CHIEU` chỉ nhận ĐÚNG MỘT đoạn sau `.output.`:
    bieu_thuc_model_viet = "{{ nodes.fetch_sheet.output.json.prompt }}"
    bieu_thuc_don_doan = "{{ nodes.fetch_sheet.output.json }}"
    assert bien_dich.la_tham_chieu(bieu_thuc_model_viet) is None, (
        "duong dan long sau .output. khong duoc _THAM_CHIEU chap nhan")
    assert bien_dich.la_tham_chieu(bieu_thuc_don_doan) == ("fetch_sheet", "json")
    # Giới hạn này CÓ TRƯỚC bản vá — `_THAM_CHIEU`/`la_tham_chieu` không nằm
    # trong đoạn `build_prompt()` vừa sửa. Lượt 1 không lộ ra giới hạn này vì
    # tham số lượt 1 là chuỗi trần (`"item.title"`), không bọc `{{ }}`, nên
    # `_doi()` chưa từng xét nhánh kiểm tra tham chiếu ở lượt đó.


def test_lot2_khong_dung_filter_foreach_thuc_te_khong_suy_dien(cc):
    """Sự kiện tĩnh, đo trực tiếp trên `document` lượt 2 — không cần biên
    dịch để biết model không chọn kiến trúc lọc+lặp lần này."""
    loai = {n["type"] for n in _LOT2_25_09["pages"][0]["nodes"]}
    assert not ({"core.filter", "core.foreach"} & loai)
    assert {"app.video.generate", "core.human"} <= loai


def test_danh_muc_van_co_filter_va_foreach(cc):
    """Bản vá KHÔNG rút filter/foreach khỏi danh mục gửi cho model — nếu lượt
    2 không dùng chúng thì đó là lựa chọn của model, không phải một cửa đã bị
    khoá bởi bản vá."""
    muc_types = {m["type"] for m in ke_hoach_v3.danh_muc(cong_cu=cc)}
    assert {"core.filter", "core.foreach"} <= muc_types


def test_prompt_moi_khong_con_dinh_type_va_co_liet_ke_kind(cc):
    """Khoá lại BẢN VÁ, không chỉ khoá lại BẰNG CHỨNG lỗi cũ."""
    muc = ke_hoach_v3.danh_muc(cong_cu=cc)
    prompt = ke_hoach_v3.build_prompt(CAU, muc=muc, ngan_sach_credit=200)
    assert "[QUY_UOC_KIND]" in prompt
    assert "DATA" in prompt and "CONTROL" in prompt and "ERROR" in prompt
    # Dòng danh mục PHẢI tách `type=` và `type_version=` — không còn `type@version`.
    for dong in prompt.splitlines():
        if dong.startswith("- type="):
            assert "@" not in dong.split(":", 1)[0]


def test_sheets_van_KHONG_publish_duoc_ly_do_that(cc):
    """Vì sao cả hai lượt gọi thật đều không (và không thể) dùng node Sheets."""
    dinh_nghia = nut.tat_ca(cong_cu=cc)
    assert "piece.google_sheets.find_rows" in dinh_nghia
    assert dinh_nghia["piece.google_sheets.find_rows"].publish_duoc is False
    muc_types = {m["type"] for m in ke_hoach_v3.danh_muc(cong_cu=cc)}
    assert "piece.google_sheets.find_rows" not in muc_types
