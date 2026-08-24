"""`POST /api/v1/messages` phải phục vụ **cả** request không streaming.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — MỘT CỬA ĐÓNG, TÌM RA 24/08 KHI CẮM CLAUDE DESKTOP.

   Route này từng từ chối thẳng mọi request thiếu `stream: true`, với lý do nghe
   rất hợp lý: *"nhận rồi trả một cục là nói dối client đang chờ SSE"*.

   Lý do đó đúng cho một client **đã xin** streaming — và sai với hợp đồng
   Anthropic Messages, thứ **cho phép cả hai**.

⛔ HẬU QUẢ ĐO ĐƯỢC: Claude Desktop **thăm dò model** bằng một request KHÔNG
   streaming. Ta trả 400, ứng dụng kết luận *"Gateway rejected model ltt_llm"*
   và **chặn luôn ô chat** — không phải một cảnh báo trang trí, mà là một cửa
   đóng. Triệu chứng khách nhìn thấy (*"model không khả dụng"*) **không hề chỉ
   về phía nguyên nhân**.

⭐ BÀI HỌC RỘNG HƠN MỘT LỖI: một dòng `if` giữ cho hợp đồng "sạch" đã làm cả một
   ứng dụng khách không dùng được. Khi ta **hẹp hơn** hợp đồng ta tuyên bố nói,
   thứ vỡ không phải phép thử của ta — mà là client của khách.
"""
from __future__ import annotations

import importlib
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def st():
    return importlib.import_module("server.api.streaming")


class _SuDung:
    def __init__(self, vao=11, ra=7):
        self.token_vao, self.token_ra = vao, ra


class _Kq:
    def __init__(self, finish="stop", noi="144"):
        self.noi_dung = noi
        self.finish_reason = finish
        self.su_dung = _SuDung()


# ── Hình dạng phản hồi, theo tài liệu chính thức ───────────────────────────

#: Trường bắt buộc của một `message` Anthropic. Thiếu một cái là client tự dựng
#: một giá trị mặc định — và nó đoán, chứ không báo lỗi.
TRUONG_BAT_BUOC = ("id", "type", "role", "model", "content",
                   "stop_reason", "stop_sequence", "usage")


def test_du_moi_truong_bat_buoc(st):
    d = st._dang_anthropic(_Kq(), "ltt_llm", "ms-abc")
    thieu = [t for t in TRUONG_BAT_BUOC if t not in d]
    assert not thieu, f"thieu truong bat buoc: {thieu}"
    assert d["type"] == "message" and d["role"] == "assistant"
    assert d["content"] == [{"type": "text", "text": "144"}]
    assert d["usage"] == {"input_tokens": 11, "output_tokens": 7}


def test_stop_details_PHAI_CO_MAT_va_bang_None(st):
    """Tài liệu: `stop_details` chỉ được điền khi `stop_reason == "refusal"`.

    Nhưng client đọc nó **vô điều kiện** — thiếu khoá và có khoá `null` là hai
    chuyện khác nhau với một bộ giải mã chặt.
    """
    d = st._dang_anthropic(_Kq(), "ltt_llm", "ms-abc")
    assert "stop_details" in d
    assert d["stop_details"] is None


@pytest.mark.parametrize("openai_style,anthropic_style", [
    ("stop", "end_turn"),
    ("length", "max_tokens"),
    ("tool_calls", "tool_use"),
    ("content_filter", "refusal"),
    ("", "end_turn"),               # khong biet -> mac dinh an toan
    (None, "end_turn"),
])
def test_anh_xa_ly_do_dung(st, openai_style, anthropic_style):
    """🔴 Máy B nói giao thức OpenAI; hợp đồng Anthropic khai một tập KHÁC HẲN.

    Bản đầu truyền thẳng `finish_reason`, tức đưa chữ `stop` của OpenAI vào một
    trường client đọc theo bảng Anthropic. Client **không vỡ ngay** — nó chỉ
    không nhận ra giá trị, rồi xử lý sai ở chỗ quan trọng nhất: `length` (bị cắt
    vì hết token) trông y hệt một câu trả lời hoàn chỉnh, nên client không biết
    mà xin tiếp.
    """
    d = st._dang_anthropic(_Kq(finish=openai_style), "ltt_llm", "ms-x")
    assert d["stop_reason"] == anthropic_style


def test_model_tra_ve_la_ALIAS_khong_phai_id_noi_bo(st):
    """Khách không bao giờ được nhìn thấy `qwen38-*` (cùng luật với test_212)."""
    d = st._dang_anthropic(_Kq(), "ltt_llm", "ms-x")
    assert d["model"] == "ltt_llm"
    assert "qwen" not in str(d).lower()


def test_che_do_thu_cung_dung_hinh_dang(st):
    """Chế độ thử phải trả **đúng hình dạng**, nếu không nó chứng minh sai thứ.

    Một sandbox trả hình dạng khác là một sandbox dạy khách trông đợi sai.
    """
    d = st._thu_mot_cuc("ltt_llm")
    thieu = [t for t in TRUONG_BAT_BUOC if t not in d]
    assert not thieu, f"che do thu thieu truong: {thieu}"
    assert "stop_details" in d
    assert d["usage"] == {"input_tokens": 0, "output_tokens": 0}


# ── Route không còn từ chối request không-stream ───────────────────────────

def test_ma_nguon_KHONG_con_tu_choi_request_khong_stream(st):
    """Chốt bằng mã nguồn: câu từ chối cũ phải biến mất khỏi đường `/messages`.

    Đây là một chốt **thô** có chủ ý — nó không dựng cả app lên, chỉ chắc rằng
    lối thoát cũ không lặng lẽ quay lại trong một lần sửa sau.
    """
    ma = pathlib.Path(st.__file__).read_text(encoding="utf-8")
    assert "This endpoint streams: send" not in ma, (
        "cau tu choi cu da quay lai - Claude Desktop se lai bi chan o o chat")
    assert "_mot_cuc(" in ma


def test_khong_stream_van_kep_max_tokens(st):
    """Không stream ⇒ không byte nào chảy cho tới khi xong ⇒ đồng hồ 100 giây của
    Cloudflare **có hiệu lực**, khác hẳn đường streaming.

    Nên trần phải là trần của đường **đồng bộ**, không phải trần streaming.
    """
    ma = pathlib.Path(st.__file__).read_text(encoding="utf-8")
    assert "_tran_max_tokens" in ma, (
        "duong khong-stream phai kep theo tran cua duong dong bo")
