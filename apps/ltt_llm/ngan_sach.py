"""Ngân sách của `ltt_llm` — **nguồn chân lý duy nhất** cho mọi con số.

    from apps.ltt_llm import ngan_sach
    ngan_sach.TOKEN_VAO_TRAN          # trần đầu vào
    ngan_sach.mac_dinh_cho("stream")  # token ra mặc định của MỘT CỬA

================================================================================
🔴 VÌ SAO TỆP NÀY TỒN TẠI

Ngày 30/08 một triệu chứng duy nhất — *"trả lời dài thì im lặng"* — bắt truy qua
**bốn tầng tham số ở bốn nơi khác nhau**, và thủ phạm hoá ra là cửa stream mượn
nhầm ngân sách 1.024 của cửa đồng bộ. Chú thích trong `features.py` khi ấy viết
*"Cửa stream và cửa job vẫn dùng mặc định 4.096"* — **tài liệu hứa một đằng, mã
làm một nẻo**, và triệu chứng là câu trả lời cụt ở đúng 1.024 token: không lỗi,
không cảnh báo, không ai biết.

Bảy chỗ chồng chéo đo được hôm đó ghi ở
`docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md`.

================================================================================
⭐ HAI LUẬT CỦA TỆP NÀY

**1. Chỉ BA con số được gõ tay.** Mọi thứ khác **tính ra** từ chúng. Sửa cửa sổ
   model là các trần dưới tự đúng theo — không còn chỗ để hai nơi lệch nhau.

**2. Mặc định phải MANG TÊN CỬA nó phục vụ.** Không có "token ra mặc định" chung
   chung; phải là `mac_dinh_cho("stream")`. Lỗi 30/08 **không xảy ra được** nếu
   tên bắt buộc nêu cửa.

⛔ Và một luật cho người sửa: **`platform_core` không được import tệp này.** App
   phụ thuộc nền tảng, không phải chiều ngược lại. Nền tảng giữ trần riêng của
   nó; `tests/test_312_ngan_sach_ltt_llm.py` **đối chiếu** hai bên và đỏ khi lệch.
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════
#  BA CON SỐ GÕ TAY — mọi thứ dưới đây tính ra từ chúng
# ══════════════════════════════════════════════════════════════════════════

#: Cửa sổ ngữ cảnh của model, **đo từ `-c` của llama-server** trên máy B
#: (`llama-swap.yaml`, hồ sơ `qwen38-api`). Vào và ra **dùng chung** con số này.
#: ⛔ Đây là số ĐO, không phải số mong muốn. Đổi `-c` bên B thì đổi ở đây.
CUA_SO_MODEL = 131_072

#: Trần token ra cứng cho một lượt. Khớp `LTT_LLM_MAX_OUTPUT_TOKENS` của máy B.
#: ⭐ Phải ≥ 32.000: Claude Code gửi `max_tokens: 32000` mặc định và khách gần
#:    như không đổi được — trần thấp hơn khiến Claude Code không dùng được (H38/L2).
TOKEN_RA_TRAN = 32_768

#: Biên cho khuôn chat, định nghĩa tool và sai số của phép **ước** token vào.
#: `uoc_token_vao` là ước chứ không phải đếm thật, nên phải chừa.
LE = 2_048


# ══════════════════════════════════════════════════════════════════════════
#  DẪN XUẤT — KHÔNG GÕ TAY BẤT KỲ SỐ NÀO DƯỚI ĐÂY
# ══════════════════════════════════════════════════════════════════════════

#: Trần đầu vào thật sự dùng được: chừa đủ chỗ cho một câu trả lời dài nhất.
#: Đây là số máy B phải khai ở `LTT_LLM_MAX_INPUT_TOKENS`.
TOKEN_VAO_TRAN = CUA_SO_MODEL - TOKEN_RA_TRAN - LE            # 96_256

#: Số byte JSON cho mỗi token khi hội thoại đi trên dây. Đo 30/08 trên thân
#: request thật của Codex (kể cả dấu ngoặc, escape và định nghĩa tool).
BYTE_MOI_TOKEN_JSON = 4.5

#: Trần thân request **tối thiểu** phải cho phép, để `TOKEN_VAO_TRAN` không bị
#: chặn bởi kích thước byte trước khi ai kịp đếm token.
#:
#: ⛔ ĐÂY LÀ MỘT LỖI ĐÃ XẢY RA: trần body 256 KB của nền tảng chặn hội thoại dài
#:    ở khoảng 64.000 token — gần bằng 65.000 nên suốt buổi ta tưởng đang chạm
#:    trần của máy B. Hai trần không liên quan gì nhau mà cái nhỏ hơn thắng.
BODY_BYTES_TOI_THIEU = int(TOKEN_VAO_TRAN * BYTE_MOI_TOKEN_JSON)   # ~433 KB

#: Cửa sổ **công bố** cho client agentic (Codex, Claude Code) để chúng nén hội
#: thoại **trước** khi chạm trần. Chừa 8% cho lệch tokenizer: client đếm token
#: bằng bộ đếm của nó, model đếm bằng bộ của Qwen, hai số không bao giờ khớp.
CONG_BO_CHO_CLIENT = int(TOKEN_VAO_TRAN * 0.92)                    # 88_555


# ══════════════════════════════════════════════════════════════════════════
#  MẶC ĐỊNH THEO CỬA — mỗi cửa một ngân sách, và tên phải nói ra cửa nào
# ══════════════════════════════════════════════════════════════════════════

#: ⛔ ĐỪNG gộp ba số này thành một "mặc định chung". Chúng khác nhau vì **ràng
#:    buộc của từng cửa khác nhau**, không phải vì ai đó tuỳ hứng:
#:
#:    * `sync`   — cửa trả JSON một cục, bị **trần 100 giây của Cloudflare**.
#:                 Sinh quá 1.024 token là gần chắc chắn 524 trước khi xong.
#:    * `stream` — byte chảy liên tục nên **không có đồng hồ đó**. 8.192 đủ cho
#:                 một tệp mã ~300 dòng; 4.096 vẫn cắt cụt lượt agentic viết tệp.
#:    * `job`    — chạy nền, cũng không có đồng hồ chờ byte đầu.
#:
#: ⭐ Rộng là AN TOÀN, không phải phóng tay: credit **giữ trước rồi hoàn** về
#:    token thật sinh ra, và model tự dừng khi trả lời xong. Con số này chỉ
#:    quyết định *chỗ để thở*, không quyết định tiền khách trả. Nhưng cũng đừng
#:    đặt kịch `TOKEN_RA_TRAN`: khoản giữ trước sẽ đòi số dư gấp bốn lần nhu cầu
#:    thật và một ví mỏng bị từ chối oan.
TOKEN_RA_MAC_DINH = {
    "sync": 1_024,
    "stream": 8_192,
    # ⛔ 4.096 CHỨ KHÔNG PHẢI 8.192, và đây là một ràng buộc chứ không phải quên
    #    đồng bộ: con số của cửa job là **giá trị `default` in trong hợp đồng công
    #    khai** (`input_schema.properties.max_tokens.default`) mà khách đọc được
    #    qua `/api/v1/tools`. Cửa job chưa từng dính lỗi 30/08 — lỗi đó chỉ ở cửa
    #    stream — nên không có lý do gì đổi thứ khách đang thấy. Muốn đổi thì đó
    #    là một thay đổi hợp đồng, phải cập nhật `tests/golden/` một cách có chủ ý.
    "job": 4_096,
}

CAC_CUA = tuple(TOKEN_RA_MAC_DINH)


def mac_dinh_cho(cua: str) -> int:
    """Token ra mặc định của **một cửa**, khi khách không tự khai giới hạn.

    ⛔ Ném `KeyError` với tên cửa sai thay vì lặng lẽ trả một số nào đó. Lỗi
       30/08 sống được chính vì một mặc định chung chung trả về số của cửa khác
       mà không ai phải nói mình đang ở cửa nào.
    """
    if cua not in TOKEN_RA_MAC_DINH:
        raise KeyError(f"cua khong hop le: {cua!r}; phai la mot trong {CAC_CUA}")
    return TOKEN_RA_MAC_DINH[cua]


# ══════════════════════════════════════════════════════════════════════════
#  PHÉP ƯỚC TOKEN — một nơi, hai kho cùng đọc
# ══════════════════════════════════════════════════════════════════════════

#: Tỉ lệ ước ký-tự-sang-token. **Phải khớp `llm_gateway/ngan_sach.py` của máy B**
#: — lệch nhau là tiền ta giữ trước lệch tiền B tính, và không có gì báo.
#: Nghiêng về ước CAO cho tiếng Việt có dấu.
KY_TU_MOI_TOKEN = 2.5


# ══════════════════════════════════════════════════════════════════════════
#  ĐỒNG THỜI — trần của ta phải biết trần của máy B
# ══════════════════════════════════════════════════════════════════════════

#: Số lượt máy B phục vụ **cùng lúc** (`LTT_LLM_MAX_DONG_THOI`).
#:
#: ⛔ 1 KHÔNG PHẢI dè dặt — nó là con số đúng: `llama-server` chạy `--parallel 1`
#:    vì speculative decoding chỉ tối ưu ở một luồng (lợi thế biến mất ở
#:    `--parallel 4`, và `--parallel 2` đo thấp hơn ~20%).
#:
#: ⚠️ Hệ quả bên ta: cho **nhiều** việc chạy song song hơn số này thì phần dôi ra
#:    chắc chắn ăn 429/503 — không phải lỗi của bên nào, là hai trần không biết
#:    nhau. Ai đặt trần đồng thời cho `text.chat` phải đọc con số này trước.
DONG_THOI_MAY_B = 1


def tran_theo_ngu_canh(token_vao_uoc: int) -> int:
    """Trần token ra **thật sự dùng được**, biết ngữ cảnh còn bao nhiêu.

    Vào và ra chia nhau cùng một cửa sổ. Một lượt có 100.000 token vào mà xin
    32.768 token ra thì tổng vượt cửa sổ, và thứ hỏng ở đó **không phải một lỗi
    sạch** — model cắt bớt ngữ cảnh hoặc thượng nguồn từ chối, cả hai đều khó truy.

    ⛔ Trả về ít nhất 1: một lượt hết chỗ phải hỏng ở **chốt token VÀO** với
       thông điệp đúng, chứ không biến thành `max_tokens=0`.
    """
    con_lai = CUA_SO_MODEL - int(token_vao_uoc or 0) - LE
    return max(1, min(TOKEN_RA_TRAN, con_lai))
