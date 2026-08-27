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


class _Kq:
    """Giả lập `apps.ltt_llm.features.KetQua` — **token phẳng**, không có `.su_dung`.

    ⚠️ Bản đầu của test này giả lập `KetQuaChat` của cổng (có `.su_dung`), vì mã
       lúc đó tự dựng `CongVlm`. Khi mã chuyển sang đường chung `features.chay`,
       kiểu trả về đổi — và test **đỏ đúng lúc nó phải đỏ**. Giữ nguyên hình dạng
       thật ở đây; một giả lập lệch kiểu là một test đo nhầm thế giới.
    """

    def __init__(self, finish="stop", noi="144"):
        self.noi_dung = noi
        self.finish_reason = finish
        self.token_vao, self.token_ra = 11, 7
        self.token_vao_cache = 0
        self.do_duoc = True


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
    # ⚠️ `tool_calls` KHONG nam o day nua. Bang anh xa van dich no thanh
    #    `tool_use`, nhung `_dang_anthropic` co them mot luoi: khong co khoi
    #    `tool_use` that thi ha ve `end_turn`. Hai hanh vi do duoc do rieng o
    #    `test_khong_khai_tool_use_khi_khong_co_khoi_tool_use` va
    #    `test_van_khai_tool_use_khi_THAT_SU_co_tool_calls` — gop vao day thi
    #    mot test se do hai thu va khong noi duoc thu nao hong.
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
    """Không stream ⇒ không byte nào chảy cho tới khi xong ⇒ đồng hồ 125 giây của
    Cloudflare **có hiệu lực**, khác hẳn đường streaming.

    Nên trần phải nhận cả input ước lượng của đường **đồng bộ**, không phải chỉ
    kẹp output theo một số cố định.
    """
    ma = pathlib.Path(st.__file__).read_text(encoding="utf-8")
    assert "_tran_max_tokens" in ma, (
        "duong khong-stream phai kep theo tran cua duong dong bo")
    assert "_tran_max_tokens(vao_uoc)" in ma, (
        "tran dong bo phai tinh ca thoi gian prefill cua input")


# ── `messages` gửi cho model KHÁC danh sách dùng để ước token ─────────────────
#
# 🔴 ĐO ĐƯỢC 25/08 TRÊN PRODUCTION. `_tin_nhan` được viết **chỉ để ước token**,
#    nên nó cố ý sinh phần tử **không có `role`**: prompt hệ thống thành
#    `{"content": …}`, và cả khối JSON của `tools` cũng bị nhét vào như một tin.
#
# ⛔ Bản đầu của `_mot_cuc` đem thẳng danh sách ấy đi gọi model. Hai hậu quả:
#    (1) request có `system`/`tools` → `ThamSoSai` → **500** cho khách;
#    (2) request không vỡ thì model nhận hội thoại **đã bị bóp méo** — và nó vẫn
#        trả lời, nên `8x7=56` vẫn đúng và lỗi không tự lộ ra.
#
# ⭐ Đó là phần đáng sợ hơn: một phép thử đúng đã che một ngữ cảnh sai.

def test_prompt_he_thong_phai_thanh_tin_co_ROLE(st):
    than = {"system": "ban la tro ly",
            "messages": [{"role": "user", "content": "chao"}]}
    tin = st._tin_that(than)
    assert all("role" in m for m in tin), f"con phan tu thieu role: {tin}"
    assert tin[0] == {"role": "system", "content": "ban la tro ly"}
    assert tin[1]["role"] == "user"


def test_system_dang_KHOI_cung_phai_ra_van_ban(st):
    """Anthropic cho phép `system` là danh sách khối `{type,text}`."""
    than = {"system": [{"type": "text", "text": "dong mot"},
                       {"type": "text", "text": "dong hai"}],
            "messages": [{"role": "user", "content": "chao"}]}
    tin = st._tin_that(than)
    assert tin[0]["role"] == "system"
    assert "dong mot" in tin[0]["content"] and "dong hai" in tin[0]["content"]


def test_dinh_nghia_TOOLS_khong_duoc_thanh_mot_luot_noi(st):
    """`tools` được cộng vào phần **ước token**, nhưng không phải một tin nhắn.

    Đưa nó vào hội thoại là bịa ra một lượt nói mà khách chưa hề gửi.
    """
    than = {"messages": [{"role": "user", "content": "chao"}],
            "tools": [{"name": "doc_tep", "description": "x" * 50}]}
    tin = st._tin_that(than)
    assert len(tin) == 1 and tin[0]["role"] == "user"
    assert "doc_tep" not in str(tin)
    # Nhưng ước token thì VẪN phải đếm nó, nếu không ta giữ thiếu tiền.
    assert "doc_tep" in str(st._tin_nhan(than))


def test_input_chuoi_tran_cua_responses_thanh_luot_NGUOI_DUNG(st):
    tin = st._tin_that({"input": "tinh giup 2+2"})
    assert tin == [{"role": "user", "content": "tinh giup 2+2"}]


def test_bo_qua_phan_tu_khong_co_role_thay_vi_de_no_vo_o_duoi(st):
    """Một phần tử rác từ client không được đi tiếp tới `kiem_tham_so`."""
    than = {"messages": [{"content": "khong co role"},
                         {"role": "user", "content": "co role"}]}
    tin = st._tin_that(than)
    assert tin == [{"role": "user", "content": "co role"}]


def test_ma_nguon_KHONG_con_dung_tin_uoc_de_goi_model(st):
    """Chốt thô: `_mot_cuc` phải gọi `_tin_that`, không phải biến `tin`."""
    ma = pathlib.Path(st.__file__).read_text(encoding="utf-8")
    than = ma.split("def _mot_cuc", 1)[1].split("\ndef ", 1)[0]
    assert "_tin_that(than)" in than, (
        "quay lai dung danh sach uoc token lam messages that -> 500 khi co "
        "`system`, va ngu canh bi bop meo khi khong 500")
    assert '"messages": tin' not in than, (
        "`tin` la danh sach UOC TOKEN (co phan tu khong co `role`) - khong duoc "
        "dung no lam messages that")
    # Va phai di qua bo dich sang giao thuc OpenAI, neu khong thi vong goi tool
    # (tool_use / tool_result) khong con nguyen.
    assert "sang_openai_messages" in than


# ── `tool_use` là một LỜI HỨA, không phải một nhãn ───────────────────────────

def test_khong_khai_tool_use_khi_khong_co_khoi_tool_use(st):
    """🔴 `stop_reason: "tool_use"` hứa rằng `content` có khối `tool_use`.

    Client đọc `stop_reason`, đi tìm khối đó để chạy tool. Không thấy thì nó
    **treo** — không báo lỗi, không thoát. Đó là kiểu hỏng tệ nhất.

    ⚠️ Hôm nay ta chưa dựng được khối đó (`_mot_cuc` không truyền `tools` lên
       model), nên đường đúng là hạ về `end_turn` chứ không phải hứa suông.
    """
    d = st._dang_anthropic(_Kq(finish="tool_calls"), "ltt_llm", "ms-x")
    assert d["stop_reason"] == "end_turn"
    assert all(k.get("type") != "tool_use" for k in d["content"])


def test_van_khai_tool_use_khi_THAT_SU_co_tool_calls(st):
    """Khi ta dựng được khối thật thì nhãn phải quay lại đúng.

    Test này là **chỗ bắt đầu** của đợt làm tool cho tử tế: nó đỏ cho tới khi
    `_dang_anthropic` biết dựng khối `tool_use`.
    """
    kq = _Kq(finish="tool_calls")
    kq.tool_calls = ({"id": "call_1", "type": "function",
                      "function": {"name": "doc_tep", "arguments": "{}"}},)
    d = st._dang_anthropic(kq, "ltt_llm", "ms-x")
    # Con no: chua dung khoi `tool_use`. Nhung nhan thi da dung.
    assert d["stop_reason"] == "tool_use"
