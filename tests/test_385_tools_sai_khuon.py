"""Cửa Anthropic phải TỪ CHỐI `tools` sai khuôn, không im lặng bỏ qua.

## Đo thật 01/09 qua Cloudflare

Gửi `tools` khuôn **OpenAI** (`{"type":"function","function":{…}}`) vào cửa
Anthropic `/api/v1/messages`:

    HTTP 200
    "Xin loi, hien tai toi khong co tool nao de truy van kho hang..."

Khách gõ sai hình dạng nhận một câu trả lời **hợp lý mà sai**, không phải một
lỗi. Và đó là nhầm lẫn dễ mắc nhất ở cửa này: hai giao thức, hai khuôn tool,
**cùng một tên trường `tools`**.

⛔ Nó cũng lệch chuẩn với chính khu API này, nơi lỗi gọi đúng tên scope thiếu
   (`missing_scope: usage:read`), nói *"A quote token is required"*, và đính
   `retry: never`. Anthropic thật trả `400` cho tool schema sai; ta khai tương
   thích giao thức đó thì phải trả lời như nó.

## ⭐ Vì sao CHỈ báo lỗi khi KHÔNG mục nào dùng được

Hỗn hợp hợp lệ + rác vẫn đi tiếp như cũ. Biến nó thành `400` là một **hồi quy
cho client đang chạy**, và cái giá lớn hơn cái lợi — ta đang sửa một *câu trả
lời sai im lặng*, không phải siết hợp đồng.
"""
from __future__ import annotations

import pytest

from server.api import tool_dich

ANTHROPIC = {"name": "tra_ton_kho", "description": "Tra ton kho",
             "input_schema": {"type": "object",
                              "properties": {"ma_hang": {"type": "string"}}}}
OPENAI = {"type": "function", "function": {
    "name": "tra_ton_kho", "description": "Tra ton kho",
    "parameters": {"type": "object",
                   "properties": {"ma_hang": {"type": "string"}}}}}


class TestKhongKhaiThiKhongSao:
    @pytest.mark.parametrize("tools", [None, [], "", 0, {}])
    def test_khong_khai_tool_KHONG_phai_loi(self, tools):
        assert tool_dich.vi_sao_khong_dung_duoc(tools) is None


class TestKhuonDungThiQua:
    def test_khuon_anthropic_qua(self):
        assert tool_dich.vi_sao_khong_dung_duoc([ANTHROPIC]) is None
        assert tool_dich.sang_openai_tools([ANTHROPIC])

    def test_HON_HOP_hop_le_va_rac_VAN_QUA(self):
        """Không siết hợp đồng — chỉ chống câu trả lời sai im lặng."""
        assert tool_dich.vi_sao_khong_dung_duoc([ANTHROPIC, OPENAI]) is None
        assert tool_dich.vi_sao_khong_dung_duoc([ANTHROPIC, {"rac": 1}]) is None


class TestKhuonSaiThiNOI_RA:
    def test_khuon_RESPONSES_phang_PHAI_qua(self):
        """🔴 KHUÔN CODEX GỬI. Từ chối nó = client không dùng được lượt nào.

        OpenAI Responses API khai tool **phẳng** — `type` + `name` +
        `parameters`, không lồng dưới `function`, không `input_schema`. Cửa
        `/api/v1/responses` của ta nói đúng giao thức đó.

        ⛔ Đo thật 01/09 bằng Codex CLI 0.145.0 trỏ vào production:

            ERROR: 400 "khong muc nao trong `tools` dung duoc: moi muc phai co
                        `name` va `input_schema`."

        Codex **luôn** khai `shell`/`apply_patch`, nên đây không phải "mất tool"
        mà là **client chết hẳn**.

        ⭐ Vì sao không phép kiểm nào bắt được: chốt này được viết cho nhầm lẫn ở
           cửa **Anthropic**, rồi đặt trong `_cua` — hàm phục vụ **cả hai** cửa.
           `test_385`, phép kiểm HTTP mới ở `test_272`, và canary production đều
           thử `/messages`. Chỉ một **client thật** mới đi qua `/responses` kèm
           tool. Đây chính là điều `test_290` đã ghi: *API trả 200 ≠ client chạy được*.
        """
        responses_style = {"type": "function", "name": "shell",
                           "description": "Runs a shell command",
                           "parameters": {"type": "object",
                                          "properties": {"command": {"type": "array"}}}}
        assert tool_dich.vi_sao_khong_dung_duoc([responses_style]) is None
        ra = tool_dich.sang_openai_tools([responses_style])
        assert ra and ra[0]["function"]["name"] == "shell"
        assert ra[0]["function"]["parameters"]["properties"] == {
            "command": {"type": "array"}}, "mat schema => model goi tool sai tham so"

    def test_khuon_RESPONSES_thieu_parameters_van_qua(self):
        """Tool không tham số là hợp lệ; thiếu `parameters` không phải lỗi."""
        assert tool_dich.vi_sao_khong_dung_duoc(
            [{"type": "function", "name": "khong_tham_so"}]) is None

    def test_khuon_OpenAI_bi_tu_choi(self):
        vi = tool_dich.vi_sao_khong_dung_duoc([OPENAI])
        assert vi is not None, (
            "khuon OpenAI bi BO QUA IM LANG -- khach nhan 200 + 'toi khong co "
            "tool nao', mot cau tra loi hop ly ma sai")

    def test_thong_diep_CHI_RA_khuon_dung(self):
        """Một lỗi không nói cách làm đúng chỉ đổi một bí ẩn lấy một bí ẩn khác."""
        vi = tool_dich.vi_sao_khong_dung_duoc([OPENAI])
        assert "input_schema" in vi, "phai goi ten truong dung"
        assert "OpenAI" in vi, "phai noi ra khach dang dung khuon nao"
        assert "chat/completions" in vi, "phai chi cho cua nhan khuon OpenAI"

    @pytest.mark.parametrize("rac", [
        [{"khong_co_name": 1}],
        [{"name": ""}],
        ["mot chuoi"],
        [123],
    ])
    def test_moi_loai_rac_deu_bi_noi_ra(self, rac):
        assert tool_dich.vi_sao_khong_dung_duoc(rac) is not None


class TestToolMayChuCuaAnthropicVanBoQuaIM:
    """`{"type": "web_search_…"}` không có `input_schema` — ta không chạy được.

    ⚠️ Đây KHÁC với rác: nó là tool hợp lệ của Anthropic mà ta cố ý không hỗ trợ.
       Bỏ qua im lặng ở đây là **có chủ ý** và đã ghi trong `sang_openai_tools`;
       biến nó thành 400 sẽ chặn một request mà phần còn lại vẫn phục vụ được.
    """

    def test_chi_co_tool_may_chu_thi_VAN_bao(self):
        # Không mục nào dùng được ⇒ vẫn phải nói, nếu không khách lại nhận
        # "tôi không có tool nào" mà không hiểu vì sao.
        assert tool_dich.vi_sao_khong_dung_duoc(
            [{"type": "web_search_20250305", "name": "web_search"}]) is not None

    def test_tool_may_chu_DI_KEM_tool_thuong_thi_qua(self):
        assert tool_dich.vi_sao_khong_dung_duoc(
            [ANTHROPIC, {"type": "web_search_20250305", "name": "web_search"}]) is None
