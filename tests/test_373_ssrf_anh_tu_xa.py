"""F14 — cổng phải TỪ CHỐI ảnh dạng URL từ xa. Chốt một biện pháp SSRF chưa ai chốt.

## Vì sao tệp này tồn tại

`llm_gateway/ngan_sach.py` **đã** từ chối URL từ xa và giải thích rõ vì sao. Rà
soát 01/09 thấy `grep url_tu_xa tests/` trả về **rỗng**: một biện pháp bảo mật
đang làm việc mà **không có phép kiểm nào**. Nó chỉ cách một lần refactor thiện
chí là biến mất, và biến mất **không tiếng động** — mọi phép kiểm khác vẫn xanh.

## Vì sao nó là SSRF thật, không phải một lo xa

Nếu cổng chuyển tiếp một `image_url` trỏ ra ngoài thì **máy B** là bên đi tải nó.
Khách gửi `http://127.0.0.1:8188/...` là bắt máy B gọi vào chính mạng nội bộ của
nó — và ComfyUI ở cổng 8188 **không có xác thực** (theo thiết kế: nó chỉ nghe
loopback). Tức lớp phòng thủ của ComfyUI chính là "không ai gọi được tới nó từ
bên ngoài", và một `image_url` chuyển tiếp phá đúng giả định đó.

🔴 **ĐÍNH CHÍNH 28/09/2026 — LỚP THỨ HAI ĐÃ MẤT, VÀ ĐÚNG NHƯ CHÚ THÍCH CŨ CẢNH BÁO.**

   Bản trước của đoạn này viết: *"Đo 22/08: `llama-server` hiện **cũng** từ chối
   URL http. Nhưng đó là một bảo đảm **đi mượn** — nó phụ thuộc hành vi của
   thượng nguồn và có thể đổi ở một bản nâng cấp mà không ai báo."*

   Câu cảnh báo ấy **đã thành sự thật**. Tra lại ở **đúng commit đang chạy**
   (`91f6a6cf3`, build b10883): `handle_media` ở `tools/server/server-common.cpp`
   (gọi từ ba chỗ dựng nội dung đa phương thức) **TẢI** mọi URL bắt đầu bằng
   `http` qua `common_remote_get_content()` — trần 10 MB, hết giờ 10 s, **không
   cờ bật/tắt, không danh sách trắng**. Chỉ `file://` mới bị chặn sau
   `--media-path`.

⇒ ⛔ **Phép kiểm này KHÔNG còn là lớp thứ hai. Nó là lớp DUY NHẤT.** Nếu
  `url_tu_xa` ở `llm_gateway/ngan_sach.py` bị gỡ, không còn thứ gì đứng giữa
  khách và `http://127.0.0.1:8188`. Đừng nới nó vì "llama-server chắc cũng chặn".

⚠️ Và bài học rộng hơn, đáng giá hơn chính con bọ: một câu **"đo 22/08"** nằm
   trong chú thích **không tự già đi**. Nó đọc y như một sự thật hiện tại suốt
   năm tuần sau khi hết đúng. Số đo trong chú thích phải mang **ngày** và mang
   **bản** — và một bảo đảm đi mượn thì phải được **đo lại sau mỗi lần nâng
   thượng nguồn** (`docs/ltt_llm_dual/RUNBOOK.md` §4b).

## Ba giao thức, ba hình dạng — phải chặn cả ba

Cổng phục vụ OpenAI Chat, OpenAI Responses và Anthropic Messages. Chặn hai trong
ba là **không chặn**: kẻ tấn công chỉ cần đổi cửa.
"""
from __future__ import annotations

import base64

import pytest

from llm_gateway.ngan_sach import VuotNganSach, do_yeu_cau, kiem_tra

TRAN = {"max_input_tokens": 96_256, "max_output_tokens": 32_768,
        "max_image_bytes": 20 * 1024 * 1024,
        "max_context": 131_072, "co_vision": True,
        # 28/09: mot ho so engine DA CAU HINH DUNG. Thieu hai so nay thi
        # `kiem_tra` nem `ThieuTranAnhEngine` cho MOI anh, ke ca anh `data:` hop
        # le - va luc do `TestVanNHAN_anh_data` se do vi mot ly do khong lien
        # quan gi toi SSRF. Chu de cua tep nay la SSRF, nen no phai mo phong mot
        # he DANG CHAY BINH THUONG, khong phai mot he cau hinh thieu.
        "token_anh_toi_thieu": 8, "token_anh_toi_da": 4096}

_ANH_THAT = "data:image/png;base64," + base64.b64encode(b"\x89PNG" * 40).decode()

#: Đích nguy hiểm THẬT trên máy B, không phải URL bịa. Xem docstring.
NOI_BO = (
    "http://127.0.0.1:8188/view?filename=x",       # ComfyUI, KHONG xac thuc
    "http://localhost:8188/history",
    "http://192.168.2.66:8299/health",             # chinh cong nay
    "http://169.254.169.254/latest/meta-data/",    # metadata dam may
    "http://[::1]:8188/",
    "file:///C:/ProgramData/LTTLlm/gateway.env",   # doc bi mat cua chinh no
)


def _chat(url):
    return {"messages": [{"role": "user", "content": [
        {"type": "text", "text": "cai gi day"},
        {"type": "image_url", "image_url": {"url": url}}]}]}


def _responses(url):
    return {"input": [{"role": "user", "content": [
        {"type": "input_text", "text": "cai gi day"},
        {"type": "input_image", "image_url": url}]}]}


def _anthropic_url(url):
    return {"messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "url", "url": url}}]}]}


KHUON = {"openai-chat": _chat, "openai-responses": _responses,
         "anthropic-messages": _anthropic_url}


class TestChanCaBaGiaoThuc:
    """Chặn hai trong ba là KHÔNG chặn — kẻ tấn công chỉ cần đổi cửa."""

    @pytest.mark.parametrize("ten", sorted(KHUON))
    @pytest.mark.parametrize("url", NOI_BO)
    def test_url_tu_xa_bi_TU_CHOI(self, ten, url):
        with pytest.raises(VuotNganSach) as e:
            kiem_tra(KHUON[ten](url), **TRAN)
        assert e.value.truong == "image_url", (
            f"{ten} + {url}: bi chan nhung vi mot ly do KHAC "
            f"({e.value.truong}) -- doi tran mot cai la lo hong mo lai")


class TestVanNHAN_anh_data:
    """Đối chứng: nếu chặn tất thì phép kiểm trên xanh mà tính năng đã chết."""

    @pytest.mark.parametrize("ten", sorted(KHUON))
    def test_anh_data_van_qua(self, ten):
        if ten == "anthropic-messages":
            than = {"messages": [{"role": "user", "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/png",
                            "data": base64.b64encode(b"\x89PNG" * 40).decode()}}]}]}
        else:
            than = KHUON[ten](_ANH_THAT)
        kiem_tra(than, **TRAN)      # khong duoc nem

    def test_do_yeu_cau_KHONG_dem_anh_data_la_url_tu_xa(self):
        assert do_yeu_cau(_chat(_ANH_THAT)).url_tu_xa == ()


class TestKhongDeLotQuaBangCACH_VIET_KHAC:
    """Một danh sách chặn theo chuỗi sẽ thủng ở đây. Luật đúng là *cho phép* `data:`."""

    @pytest.mark.parametrize("url", (
        "HTTP://127.0.0.1:8188/x",          # HOA
        "hTtPs://evil.example/x",           # hoa-thuong tron
        "  http://127.0.0.1:8188/x",        # khoang trang dau
        "//127.0.0.1:8188/x",               # thieu giao thuc
        "http:\\\\127.0.0.1:8188\\x",       # gach nguoc
        "datax:image/png;base64,AAAA",      # gan giong `data:`
        "data\t:image/png;base64,AAAA",     # ky tu trang chen giua
    ))
    def test_bien_the_van_bi_chan(self, url):
        with pytest.raises(VuotNganSach) as e:
            kiem_tra(_chat(url), **TRAN)
        assert e.value.truong == "image_url"


class TestThongDiepNoiDuocPHAI_LAM_GI:
    def test_loi_chi_ra_dang_duoc_chap_nhan(self):
        """Một lỗi bảo mật không nói cách làm đúng sẽ đẩy khách đi đoán."""
        with pytest.raises(VuotNganSach) as e:
            kiem_tra(_chat("http://127.0.0.1:8188/x"), **TRAN)
        assert "data:" in str(e.value)
