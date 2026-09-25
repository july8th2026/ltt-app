"""`bao_gia._gia_node` phải tra ToolSpec bằng **khai báo**, ⛔ không bằng `[4:]`.

🔴 Lỗi thật, tái hiện 25/09:

    'ai.llm'[4:] == 'lm'   ⇒  KhongBaoGiaDuoc: khong co cong cu 'lm'

`ai.llm` **có** khai `ten_toolspec="text.chat"`, và `text.chat` **có** trong
registry. Nhưng `_gia_node` cắt cứng 4 ký tự đầu — một phép cắt chỉ đúng cho
tiền tố `app.`. ⇒ Publish bất kỳ đồ thị nào chứa `ai.llm`/`ai.extract`/
`ai.router` đều chết ở cổng báo giá.

⭐ `cau_noi.ten_cong_cu()` đã giải đúng bài này từ trước: `app.` thì cắt tiền
   tố, còn lại thì đọc `NodeDefinition.ten_toolspec`. Docstring của nó còn ghi
   rõ vì sao ⛔ không được tra ngược `job_type → tên tool` (ba `job_type` đang
   bị hai tool dùng chung — tra ngược sẽ im lặng chọn nhầm).
   ⇒ Bản vá **dùng lại** hàm ấy, ⛔ không viết cách giải thứ hai.

⚠️ Vì sao lỗi sống lâu: `test_1789` phủ `ten_cong_cu` và `nop_job` cho node
   `ai.*`, nhưng ⛔ không bài nào đưa node `ai.*` qua **đường báo giá**. Hai
   cửa cùng hỏi *"node này bọc tool nào"*, chỉ một cửa hỏi đúng cách.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bao_gia, nut_loi
from platform_core.workflow.bao_gia import KhongBaoGiaDuoc
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC

#: Mọi node lõi `thi_hanh="job"` có khai `ten_toolspec` — đọc CƠ HỌC từ
#: registry, ⛔ không gõ tay, để node AI thứ tư sinh ra cũng được phủ.
NODE_AI_JOB = sorted(
    nd.type for nd in nut_loi.tat_ca().values()
    if nd.thi_hanh == "job" and nd.ten_toolspec
    and not nd.type.startswith("app.")
)


def _node(loai: str) -> dict:
    return {"id": "n1", "type": loai, "thi_hanh": "job",
            "params": {"prompt": "xin chao"}}


def test_co_it_nhat_mot_node_ai_job_de_do():
    """⛔ Đối chứng cho chính phép quét: tập rỗng thì mọi bài dưới xanh rỗng."""
    assert NODE_AI_JOB, (
        "khong node loi nao co thi_hanh=job + ten_toolspec — phep quet nay "
        "dang do mot tap RONG, tuc no khong canh gi ca")


@pytest.mark.parametrize("loai", NODE_AI_JOB)
def test_node_ai_bao_gia_duoc_qua_ten_toolspec(loai):
    """🔴 Bài chính. Trước bản vá: `KhongBaoGiaDuoc ... cong cu 'lm'`."""
    nd = nut_loi.tat_ca()[loai]
    assert nd.ten_toolspec in CC, (
        f"{loai} khai ten_toolspec={nd.ten_toolspec!r} ma registry thu khong "
        "co — bai nay dang do sai thu")
    gia = bao_gia._gia_node(_node(loai), CC)
    assert isinstance(gia, int) and gia >= 0


def test_khong_dung_phep_cat_4_ky_tu_nua():
    """Chốt **tính chất**, ⛔ không chốt cách gõ: giá của `ai.llm` phải bằng
    giá của chính ToolSpec nó khai, ⛔ không phụ thuộc độ dài tiền tố."""
    nd = nut_loi.tat_ca()["ai.llm"]
    qua_node = bao_gia._gia_node(_node("ai.llm"), CC)
    qua_app = bao_gia._gia_node(_node("app." + str(nd.ten_toolspec)), CC)
    assert qua_node == qua_app


def test_node_KHONG_khai_ten_toolspec_VAN_bi_tu_choi():
    """⛔ Bản vá ⛔ không được nới thành *"cứ node lõi là bỏ qua báo giá"*.

    Một node `thi_hanh="job"` ngoài không gian `app.` mà ⛔ không khai
    `ten_toolspec` thì cầu nối job cũng ⛔ không biết nó bọc gì — báo giá phải
    từ chối, y như `ten_cong_cu()` ném `LoiTienTo`.
    """
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia._gia_node(_node("core.khong_he_ton_tai"), CC)


def test_duong_app_khong_doi_hanh_vi():
    """Hồi quy: ca thường (`app.<tool>`) phải y nguyên."""
    gia = bao_gia._gia_node(_node("app.text.chat"), CC)
    assert isinstance(gia, int) and gia >= 0
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia._gia_node(_node("app.khong_he_ton_tai"), CC)
