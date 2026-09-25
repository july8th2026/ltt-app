"""Làn `wfk` — vá tiếp Lỗi 1 (`data.tool`), lần thứ hai trong MỘT lần.

`test_4250` chốt hình dạng **cấp NODE** (`data.tool`/`data.params`). Playwright
THẬT (`tests/browser/wf_v2_pa_4180_canvas_bam_that.js`, chạy qua
`tests/browser/wf_v2_pa_4180_run.ps1` trên máy chủ thử cổng 8199, KHÔNG mock)
đỏ ở bước A3 "Soạn bằng AI" — `TypeError: Cannot read properties of undefined
(reading 'trim')` tại `CanvasShell.tsx::soanBangAI` (`state.document.goal.trim()`).

Nguyên nhân: `ke_hoach_v3.chuan_hoa()` trả `document` chỉ có
`{version, pages}` — thiếu `goal`/`active_page_id`/`budget_max_credit` mà
`CanvasDocument`/`CanvasDocumentV3` (`workflowApi.ts`) cần ở **CẤP TÀI LIỆU**.
`CanvasShell.tsx::soanBangAI` ghi thẳng
`dispatch({type:'replace', document: fromV3(kq.document)})` — `fromV3()`
(cùng tệp) chỉ spread nguyên `canvas` rồi đổi `version`/`pages`, nên field nào
tài liệu gốc không có thì tài liệu sau cũng không có, `undefined`.

## Gốc bệnh: hình dạng khai HAI CHỖ, không ai bắt khớp

`CanvasDocument`/`CanvasDocumentV3` (TypeScript, `workflowApi.ts`) và
`ke_hoach_v3.chuan_hoa()` (Python) — đúng khuôn đã có tên trong sổ tay kho:
*"hai chỗ khai một điều, không ai bắt khớp"* (`tests/test_968_canvas_v3_khop_may_chu.py`
đã đóng một trường hợp khác của CÙNG khuôn, ở cấp TRANG — đọc `CanvasPage`,
gọi thật `di_tru_m1._trang_v3`, so khoá). Tệp này làm ĐÚNG kỹ thuật đó ở cấp
TÀI LIỆU, cho `ke_hoach_v3.chuan_hoa()`.

⛔ KHÔNG chốt bằng cách liệt kê ba tên trường vào một hằng số ở đây — một
   hằng số thứ ba chỉ là chỗ thứ ba để trôi (y hệt cảnh báo ở đầu `test_968`).
   Cả hai vế đọc từ NGUỒN THẬT: TS đọc bằng regex trên khai báo kiểu, Python
   gọi thật `chuan_hoa()`. Thêm một trường bên TS thì bài này tự đỏ, không
   cần sửa tay.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from platform_core.agent import ke_hoach_v3

GOC = pathlib.Path(__file__).resolve().parent.parent
TS = GOC / "frontend" / "agent-canvas" / "src" / "workflowApi.ts"


def _truong_tai_lieu_typescript() -> set[str]:
    """Trường CẤP TRÊN của `CanvasDocument`, đọc từ khai báo kiểu trong TS.

    ⭐ Đọc `CanvasDocument` (khoá thật client render), KHÔNG phải
       `CanvasDocumentV3` (khoá `Omit<CanvasDocument,...> & {...}` — cùng
       tập trường, nhưng cú pháp `Omit<>` khó regex hơn và không cần thiết:
       `CanvasDocumentV3` không thêm/bớt trường nào so với `CanvasDocument`,
       chỉ đổi kiểu của `version`/`pages`).
    ⛔ Không đọc `pages` — đó là một MẢNG kiểu `CanvasPage[]`, không mở ngoặc
       `{...}` nên regex một-dòng-một-trường vẫn bắt đúng tên `pages`, nhưng
       nội dung BÊN TRONG mỗi trang đã có `test_968` chốt riêng.
    """
    noi_dung = TS.read_text(encoding="utf-8")
    m = re.search(r"export type CanvasDocument = \{(.*?)\n\}", noi_dung, re.S)
    if m is None:
        pytest.fail("khong tim thay `export type CanvasDocument` trong workflowApi.ts")
    return set(re.findall(r"^\s*([a-z_][a-zA-Z0-9_]*)\s*:", m.group(1), re.M))


@pytest.fixture(scope="module")
def can() -> set[str]:
    assert TS.exists(), f"khong thay {TS} -- nguon frontend duoc git theo doi"
    return _truong_tai_lieu_typescript()


def test_phep_doc_TS_khong_rong(can):
    """Đối chứng cho chính phép kiểm (y hệt `test_968::test_phep_kiem_nay_doc_duoc_ca_HAI_bo`)
    -- regex hụt thì `can` rỗng và bài dưới xanh giả."""
    assert can == {"version", "goal", "budget_max_credit", "active_page_id", "pages"}


def test_chuan_hoa_sinh_DU_khoa_cap_tai_lieu_ma_canvas_doc_thang(can):
    """🔑 Mệnh đề trung tâm. Gọi THẬT `chuan_hoa()`, so khoá đầu ra với đúng
    khoá TS khai -- không phải một danh sách chép tay."""
    doc = ke_hoach_v3.chuan_hoa(
        {"nodes": [{"id": "a", "type": "core.stop", "params": {}}], "edges": []},
        goal="muc tieu that", budget_max_credit=200)
    thieu = sorted(can - set(doc))
    assert not thieu, (
        f"chuan_hoa() thieu khoa cap tai lieu ma CanvasDocument doi: {thieu}\n"
        f"  TS doi        : {sorted(can)}\n"
        f"  chuan_hoa() co : {sorted(doc)}")


def test_khong_truong_nao_None_sau_khi_JSON_hoa(can):
    """⚠️ `None` (Python) -> `null` (JSON) -> `.trim()` trên `null` NÉM CÙNG
    kiểu lỗi với `undefined` -- thiếu khoá và khoá mang `None` là HAI hình
    dạng của CÙNG một lỗ, bài này chặn cả hai."""
    doc = ke_hoach_v3.chuan_hoa(
        {"nodes": [{"id": "a", "type": "core.stop", "params": {}}], "edges": []},
        goal="", budget_max_credit=0)
    rong = sorted(k for k in can if k in doc and doc[k] is None)
    assert not rong, f"khoa mang None (se thanh null/undefined o JS): {rong}"


def test_goal_va_ngan_sach_duoc_GIU_nguyen_khong_bi_doan():
    """Vòng lặp thật: người dùng gõ `goal`, bấm "Soạn bằng AI" -- tài liệu trả
    về phải ECHO đúng `goal`/ngân sách đã gửi, không phải một giá trị đoán
    hay rỗng cứng. Mất `goal` ở đây là mất chữ người dùng vừa gõ trên UI."""
    doc = ke_hoach_v3.chuan_hoa(
        {"nodes": [{"id": "a", "type": "core.stop", "params": {}}], "edges": []},
        goal="Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt",
        budget_max_credit=250)
    assert doc["goal"] == "Đọc Sheet mỗi sáng, lấy READY, tạo video, chờ tôi duyệt"
    assert doc["budget_max_credit"] == 250


def test_active_page_id_khop_id_trang_that_khong_lam_updateActive_im_lang():
    """`editorState.ts::updateActive()` so KHỚP TUYỆT ĐỐI `page.id ===
    document.active_page_id` (không có lối lui `?? pages[0]`, xem chú thích
    đầu `wf_v2_pa_4180_canvas_bam_that.js`) -- lệch một chữ thì MỌI thao tác
    thêm/sửa node qua UI sau `/soan` im lặng không làm gì, không lỗi console."""
    doc = ke_hoach_v3.chuan_hoa(
        {"nodes": [{"id": "a", "type": "core.stop", "params": {}}], "edges": []},
        goal="x", budget_max_credit=1)
    assert doc["active_page_id"] == doc["pages"][0]["id"]


def test_chuan_hoa_khong_tham_so_moi_van_chay_duoc_tuong_thich_nguoc():
    """`chuan_hoa(raw)` không kèm `goal=`/`budget_max_credit=` (test_2930,
    test_4190, test_4250 gọi kiểu này) phải còn chạy được -- tham số mới có
    mặc định, không phải bắt buộc."""
    doc = ke_hoach_v3.chuan_hoa(
        {"nodes": [{"id": "a", "type": "core.stop", "params": {}}], "edges": []})
    assert doc["goal"] == ""
    assert doc["budget_max_credit"] == 0
