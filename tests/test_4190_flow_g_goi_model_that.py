"""FLOW G — lượt gọi model THẬT đầu tiên qua máy B (plan wf-v2 P-B, làn wfb4).

`tests/test_2935_flow_g.py` chỉ tiêm **dữ liệu vàng** (`_do_thi_vang`) — chưa
bao giờ chạm `ltt-3.5` thật. Tệp này đóng đúng khoảng trống đó bằng **một**
lượt gọi thật, đã chạy 25/09/2026 qua `platform_core.agent.ke_hoach_v3.soan_draft`
KHÔNG `llm_call` (tức đi đúng đường `planner.goi_model` → `admission` →
`dieu_phoi.goi` → máy B), câu `CAU` dưới đây, model `ltt-3.5`
(`Qwen3.5-9B-Q6_K`, 5060 Ti — rẻ nhất trong hai model nội bộ, đúng
`canonical.MODEL_NOI_BO_MAC_DINH`). 53,25 s, 6 632 token vào / 2 990 token ra.

## Lượt gọi thật đó KHÔNG biên dịch được — và đây là ĐÚNG hai lý do, đo được

`_TAI_LIEU_THAT_25_09` dưới đây là **nguyên văn** `document` model trả về
(qua `chuan_hoa`, JSON đông cứng — không phải dữ liệu vàng tôi soạn). Cho nó
đi qua ĐÚNG `bien_dich.bien_dich()`: nó bị từ chối ngay ở node đầu tiên bằng
`node_khong_ton_tai` cho `"type": "core.http@1"`.

Lý do KHÔNG phải model kém: `core.http` (bỏ hậu tố) nằm đúng trong danh mục
publish_duoc mà prompt đưa cho nó. Lý do là **prompt cũ có hai lỗ**, cả hai
đều lộ ra ở lượt gọi thật này, KHÔNG lộ ra ở test dữ liệu vàng (dữ liệu vàng
do người viết, không mắc lỗi mà chỉ model mới mắc):

1. Dòng danh mục cũ viết dính `type@type_version` (`- core.http@1 (job): ...`)
   — model chép NGUYÊN chuỗi hiển thị đó vào trường `type` của **cả 8 node**,
   thay vì tách `type`/`type_version`. Bài học "ví dụ trong lời nhắc là mệnh
   lệnh ngầm" (memory `vi-du-trong-loi-nhac-la-menh-lenh-ngam.md`): model học
   HÌNH THỨC hiển thị, không học lược đồ JSON.
2. Mẫu JSON cũ liệt `"kind"` như một khoá rỗng, KHÔNG bao giờ nói giá trị hợp
   lệ (`bien_dich._KIND = {"DATA","CONTROL","ERROR"}`). Model đoán `"json"`
   cho cả 7 cạnh — hợp lý về ngữ nghĩa (nó đang tả ĐỊNH DẠNG dữ liệu) nhưng
   sai Ô cần điền.

`platform_core/agent/ke_hoach_v3.py::build_prompt` đã sửa CẢ HAI (danh mục
viết `type=... type_version=... kind=...` tách rời; thêm khối
`[QUY_UOC_KIND]` liệt đúng 3 giá trị; `[DAU_RA]` nói thẳng "không được nối
`@version` vào `type`"). Tệp này khoá lại bằng máy, không bằng lời hứa.

## Sau khi sửa ĐÚNG HAI CHỖ ĐÓ — không sửa gì khác — draft THẬT biên dịch được

`test_sua_dung_hai_loi_prompt_thi_draft_THAT_bien_dich_duoc` áp CHÍNH XÁC hai
phép sửa mà prompt mới đòi hỏi (bỏ hậu tố `@\\d+` khỏi `type`, đổi `kind` từ
`"json"` sang `"DATA"`) lên `_TAI_LIEU_THAT_25_09` — KHÔNG sửa node nào khác,
KHÔNG thêm/bớt cạnh, KHÔNG gọi lại model. Chứng minh: cổng biên dịch và
registry node phía nền tảng vốn đã nhận được hình dạng model thật sinh ra
(fetch → transform → filter → foreach → video → foreach_end → human →
output) — chỉ prompt (đã sửa) từng cản nó.

## ⛔ Vẫn CHƯA có node Sheets/cron thật — không phải chỗ tệp này chốt

Model thật KHÔNG dùng `piece.google_sheets.find_rows` — nó không nằm trong
danh mục gửi cho model, vì `platform_core/workflow/nut.py::tu_piece()` khoá
CỨNG `publish_duoc=False` cho MỌI node `piece.*` (bình luận tại chỗ: cổng
publish `cau_noi.nop_job` còn từ chối `piece.*` bằng `LoiTienTo`, chờ "plan
08" mở đường runner Node riêng). Model tự bù bằng `core.http` — một cách giải
hợp lý cho hôm nay, không phải bằng chứng Sheets đã dùng được. FLOW G day đủ
6/6 theo đúng tinh thần §18.5 (bấm nút, Sheets thật, không phải HTTP tay) vẫn
CHƯA đạt — việc đó thuộc P-C (kết nối `pollingHelper`), không phải P-B.
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


#: Nguyên văn `document` (`ke_hoach_v3.chuan_hoa`) của lượt gọi THẬT 25/09/2026
#: qua `ltt-3.5`. KHÔNG được sửa tay — đây là bằng chứng, không phải fixture.
_TAI_LIEU_THAT_25_09 = {
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


def test_lot_goi_that_NGUYEN_VAN_bi_tu_choi_dung_ma_da_do(cc):
    """Đóng băng lý do thật, bằng máy — không phải lời kể lại."""
    with pytest.raises(bien_dich.LoiBienDich) as exc:
        bien_dich.bien_dich(copy.deepcopy(_TAI_LIEU_THAT_25_09), cong_cu=cc)
    assert exc.value.ma == "node_khong_ton_tai"
    assert exc.value.node_id == "fetch_sheet"


def test_sua_dung_hai_loi_prompt_thi_draft_THAT_bien_dich_duoc(cc):
    """Sửa ĐÚNG hai điểm prompt mới đòi hỏi — không sửa gì khác — thì qua cổng."""
    doc = copy.deepcopy(_TAI_LIEU_THAT_25_09)
    for n in doc["pages"][0]["nodes"]:
        n["type"] = re.sub(r"@\d+$", "", n["type"])
    for e in doc["pages"][0]["edges"]:
        assert e["kind"] == "json"          # đúng lỗi thật, trước khi sửa
        e["kind"] = "DATA"

    graph = bien_dich.bien_dich(doc, cong_cu=cc)
    assert graph["thu_tu"][0] == "fetch_sheet"
    assert graph["thu_tu"][-1] == "output_result"
    loai = {n["type"] for n in graph["nodes"]}
    # Tính chất FLOW G đo được HÔM NAY: filter + foreach + video + human có
    # thật trong đồ thị thật model sinh ra — ⛔ không chốt bằng "dùng node tên
    # X", chốt bằng VIỆC (có bước lọc, có vòng lặp, có sinh video, có cửa
    # người duyệt).
    assert {"core.filter", "core.foreach", "core.foreach_end",
            "app.video.generate", "core.human"} <= loai

    bg = bao_gia.bao_gia_do_thi(graph, cong_cu=cc)
    assert bg.toi_da > 0 and bg.uoc_tinh > 0


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
    """Vì sao model thật không (và không thể) dùng node Sheets hôm nay."""
    dinh_nghia = nut.tat_ca(cong_cu=cc)
    assert "piece.google_sheets.find_rows" in dinh_nghia
    assert dinh_nghia["piece.google_sheets.find_rows"].publish_duoc is False
    muc_types = {m["type"] for m in ke_hoach_v3.danh_muc(cong_cu=cc)}
    assert "piece.google_sheets.find_rows" not in muc_types
