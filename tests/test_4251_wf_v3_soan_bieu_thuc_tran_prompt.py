"""Làn `wfk` — Lỗi 2 (`docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md`,
brief làn wfk), cùng tệp `platform_core/agent/ke_hoach_v3.py` với Lỗi 1.

`tests/test_4190_flow_g_goi_model_that.py::_LOT2_25_09` (lượt gọi model
THẬT, đóng băng) có `check_ready` (`core.if`):

    "dieu_kien": "{{ nodes.fetch_sheet.output.json.status === 'READY' }}"

Hai lỗi CÙNG LÚC (xem `test_lot2_toan_van_van_KHONG_bien_dich_duoc_NHUNG_vi_
check_ready_khong_phai_create_video` trong tệp đó, đóng băng bằng chứng
KHÔNG sửa):

  1. bọc trong `{{ }}` — nhưng tham số kiểu `bieu_thuc`/`bang_bieu_thuc` của
     NODE LÕI (`bien_dich.KIEU_BIEU_THUC`, đọc ở `_node_loi`/`_tham_chieu_
     node_loi`) phải TRẦN, không ngoặc — khác tham số CHUỖI của node app/tool
     (đó mới dùng `{{ nodes... }}` để nội suy);
  2. `===` của JavaScript — ngôn ngữ §6 (`platform_core/workflow/chinh_sach.py`
     dòng ~1025: `ast.Eq: _bang`) chỉ có `==`/`!=`, phân tích bằng `ast.parse`
     (cú pháp Python) nên `===` là lỗi cú pháp thẳng, không phải một toán tử
     bị từ chối bằng thông điệp rõ ràng.

`build_prompt()` (bản trước bản vá này) không nói gì về quy ước tham số kiểu
`bieu_thuc` — danh mục chỉ in nguyên lược đồ JSON thô
(`"dieu_kien":{"type":"bieu_thuc"}`) mà không giải thích `"bieu_thuc"` nghĩa
là gì cho một model đọc tiếng Anh/Việt tự nhiên, không đọc mã nguồn compiler.

⛔ KHÔNG sửa `test_4190` — nó đóng băng NGUYÊN VĂN một lượt gọi model đã xảy
ra trong quá khứ (bằng chứng, không phải hành vi hiện tại của `build_prompt`).
"""
from __future__ import annotations

import pytest

from platform_core.agent import ke_hoach_v3
from platform_core.workflow import cong_cu


@pytest.fixture(scope="module")
def cc():
    return cong_cu.tat_ca()


@pytest.fixture(scope="module")
def muc(cc):
    return ke_hoach_v3.danh_muc(cong_cu=cc)


def test_danh_muc_core_if_co_tham_so_kieu_bieu_thuc(muc):
    """Cột chứng minh: hướng dẫn mới phải đứng trên lược đồ THẬT
    (`tham_so.properties.dieu_kien.type == "bieu_thuc"`), không đoán tên
    tham số `dieu_kien` -- xem `bien_dich.KIEU_BIEU_THUC`."""
    core_if = next(m for m in muc if m["type"] == "core.if")
    assert core_if["tham_so"]["properties"]["dieu_kien"]["type"] == "bieu_thuc"


def test_prompt_day_biet_tham_so_bieu_thuc_phai_tran_khong_boc_ngoac(muc):
    prompt = ke_hoach_v3.build_prompt("muc tieu", muc=muc, ngan_sach_credit=100)
    assert "[QUY_UOC_BIEU_THUC]" in prompt, (
        "prompt chua noi ve quy uoc tham so kieu bieu_thuc/bang_bieu_thuc")
    # Dong huong dan phai NEU RO tu "bieu_thuc" (nhan luoc do that) VA
    # canh bao khong boc {{ }} -- khong chi lap lai [DAU_RA] chung chung.
    khoi = prompt.split("[QUY_UOC_BIEU_THUC]", 1)[1].split("[MUC_TIEU]", 1)[0]
    assert "bieu_thuc" in khoi
    assert "{{" in khoi and "}}" in khoi


def test_prompt_neu_dich_danh_toan_tu_javascript_ba_dau_bang(muc):
    prompt = ke_hoach_v3.build_prompt("muc tieu", muc=muc, ngan_sach_credit=100)
    khoi = prompt.split("[QUY_UOC_BIEU_THUC]", 1)[1].split("[MUC_TIEU]", 1)[0]
    assert "===" in khoi, "phai NOI TEN toan tu JS sai de cam, khong im lang"
    assert "==" in khoi
