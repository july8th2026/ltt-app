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
   nó; `tests/test_334_ngan_sach_ltt_llm.py` **đối chiếu** hai bên và đỏ khi lệch.
"""
from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════════
#  BA CON SỐ GÕ TAY — mọi thứ dưới đây tính ra từ chúng
# ══════════════════════════════════════════════════════════════════════════

#: Cửa sổ ngữ cảnh của model, **đo từ `-c` của llama-server** trên máy B
#: (`llama-swap.yaml`, hồ sơ `qwen38-api`). Vào và ra **dùng chung** con số này.
#: ⛔ Đây là số ĐO, không phải số mong muốn. Đổi `-c` bên B thì đổi ở đây.
#:
#: 📈 03/09: 131.072 → 204.800, kèm KV cache `q8_0` → `q4_0` (bắt buộc: `q8_0`
#:    ở 204.800 không vừa card 24 GB). Bằng chứng đầy đủ ở
#:    `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md`. Ba số quan trọng nhất:
#:
#:      * **VRAM đỉnh 21.979 MiB** ở hồ sơ 200K, so với **22.017 MiB** ở hồ sơ
#:        131K cũ — rộng gấp rưỡi mà tốn ÍT hơn. Đây không phải phép màu: KV
#:        `q4_0` ở 204.800 nhỏ hơn KV `q8_0` ở 131.072.
#:      * **Chạy thật tới 179.902 token vào**, đọc lại đúng mốc đầu và mốc cuối.
#:        Trần dẫn xuất dưới đây là 169.984 ⇒ trần nằm **bên trong** vùng đã
#:        chứng minh, không phải ở mép nó.
#:      * Prefill **không** chậm hơn ở mọi mốc chung (50K/100K/130K), và
#:        kim-trong-đống-cỏ ở 130K đọc đúng **10/10** ở năm độ sâu.
#:
#: ⚠️ VÀ MỘT CẢNH BÁO CHO NGƯỜI SỬA TIẾP: đổi số này **không đủ** để máy B đổi
#:    theo. `llm_gateway/deploy/deploy.ps1` ghi đè `LTT_LLM_MAX_INPUT_TOKENS`
#:    bằng số gõ tay, và nó chép `llama-swap.yaml` mà **không** restart
#:    `LTTLlamaSwap`. Thứ tự deploy nằm ở §7 của tài liệu trên và nó **không
#:    hoán vị được**. `test_334` chốt hai bản sao đó.
CUA_SO_MODEL = 204_800

#: Cửa sổ ngữ cảnh của model **VISION** — `qwen38-vision` nạp với `-c 65536`
#: (`llama-swap.yaml` trên máy B, và `llm_gateway/catalog.py:max_context`).
#:
#: 🔴 SỐ NÀY TỪNG KHÔNG TỒN TẠI, VÀ SỰ VẮNG MẶT CỦA NÓ LÀ MỘT LỜI HỨA SAI.
#:
#:    Trước 01/09 cả hai alias `ltt_llm` và `ltt_llm_vision` dùng **chung** một
#:    con số công bố, dẫn xuất từ `CUA_SO_MODEL` (131.072). Nên `/api/v1/models`
#:    nói với khách rằng vision có *"same 89K usable input context"* — trong khi
#:    máy B chặn nó ở **65.536**. Đo thật 01/09, cùng một thân request:
#:
#:        ltt_llm_vision -> 413 {"tran":65536,"thay":71281}
#:        ltt_llm        -> 200 (input_tokens that = 52.810)
#:
#:    ⭐ Điều đáng nhớ: `_cua_so_noi_voi_khach()` ở `manifest.py` được viết ngày
#:       30/08 để giết **đúng lớp lỗi này** ("trước 30/08 chỗ này gõ tay 131K, và
#:       đó là một lời hứa sai"). Nó giết được ở alias text và sống sót nguyên vẹn
#:       ở alias vision — vì bản vá sửa *con số*, còn khuyết tật thật là **một con
#:       số cho hai model khác nhau**.
#:
#: ⛔ Đây là số ĐO, không phải số mong muốn. Đổi `-c` của `qwen38-vision` bên B
#:    thì đổi ở đây. `test_334` buộc hai đầu lại.
CUA_SO_MODEL_VISION = 131_072

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
TOKEN_VAO_TRAN = CUA_SO_MODEL - TOKEN_RA_TRAN - LE           # 169_984

#: Số byte JSON cho mỗi token khi hội thoại đi trên dây. Đo 30/08 trên thân
#: request thật của Codex (kể cả dấu ngoặc, escape và định nghĩa tool).
BYTE_MOI_TOKEN_JSON = 4.5

#: Trần thân request **tối thiểu** phải cho phép, để `TOKEN_VAO_TRAN` không bị
#: chặn bởi kích thước byte trước khi ai kịp đếm token.
#:
#: ⛔ ĐÂY LÀ MỘT LỖI ĐÃ XẢY RA: trần body 256 KB của nền tảng chặn hội thoại dài
#:    ở khoảng 64.000 token — gần bằng 65.000 nên suốt buổi ta tưởng đang chạm
#:    trần của máy B. Hai trần không liên quan gì nhau mà cái nhỏ hơn thắng.
BODY_BYTES_TOI_THIEU = int(TOKEN_VAO_TRAN * BYTE_MOI_TOKEN_JSON)   # ~747 KB

#: Cửa sổ **công bố** cho client agentic (Codex, Claude Code) để chúng nén hội
#: thoại **trước** khi chạm trần. Chừa 8% cho lệch tokenizer: client đếm token
#: bằng bộ đếm của nó, model đếm bằng bộ của Qwen, hai số không bao giờ khớp.
CONG_BO_CHO_CLIENT = int(TOKEN_VAO_TRAN * 0.92)                   # 156_385


# ── Ngân sách THEO MODEL ───────────────────────────────────────────────────
#
# ⭐ Hai model, hai cửa sổ, nên **hai bộ số** — và đó là toàn bộ bài học của
#    khuyết tật F-02: một con số dùng cho hai model là một con số sai cho ít
#    nhất một trong hai.
#
# ⛔ Công thức phải GIỐNG HỆT đường text ở trên (chừa `TOKEN_RA_TRAN` cho câu
#    trả lời dài nhất, chừa `LE` cho sai số ước, rồi bớt 8 % lệch tokenizer).
#    Nếu vision được một công thức "nới tay" riêng thì con số công bố của hai
#    model không còn mang **cùng một lời hứa**, và khách không có cách nào biết
#    lời hứa nào áp cho model nào.

#: Cửa sổ engine theo **id model nội bộ**. Khoá là id của máy B, không phải
#: bí danh công khai — bí danh không bao giờ được rời máy A (INV-015).
CUA_SO_THEO_MODEL = {
    "qwen38-api": CUA_SO_MODEL,
    "qwen38-vision": CUA_SO_MODEL_VISION,
}


def tran_vao_cua(model_id: str) -> int:
    """Trần đầu vào thật sự dùng được của **một** model.

    Ném `KeyError` với thông điệp nói rõ tên hợp lệ — im lặng trả một số mặc
    định là cách chắc chắn nhất để lời hứa sai quay lại.
    """
    if model_id not in CUA_SO_THEO_MODEL:
        raise KeyError(f"model khong biet: {model_id!r}; "
                       f"phai la mot trong {sorted(CUA_SO_THEO_MODEL)}")
    return CUA_SO_THEO_MODEL[model_id] - TOKEN_RA_TRAN - LE


def cong_bo_cua(model_id: str) -> int:
    """Con số ngữ cảnh **công bố cho client** của một model."""
    return int(tran_vao_cua(model_id) * 0.92)


#: Ngưỡng client **phải nén** hội thoại, tính từ cửa sổ công bố.
#:
#: 🔴 VÌ SAO KHÔNG PHẢI MỘT TỈ LỆ. Trước 03/09 cả hai bộ cài đều gõ `× 0,8`, và
#:    tỉ lệ ấy **không đo cái cần đo**. Thứ phải vừa không phải "80 % cửa sổ" mà
#:    là *khoảng trống còn lại sau ngưỡng nén*: client kiểm ngưỡng **giữa hai
#:    lượt**, nên lượt kế tiếp vẫn được phép lớn thêm trọn một lượt nữa trước
#:    khi nó có cơ hội nén lần sau.
#:
#: ⛔ VÀ ĐÂY LÀ LỖI ĐÃ XẢY RA TRÊN PRODUCTION, không phải lo xa. Một lượt
#:    `POST /api/v1/responses` ăn `413` với **101.938** token vào trên trần
#:    96.256. Với `× 0,8` thì ngưỡng nén là 70.844 và khoảng trống tới trần chỉ
#:    còn **25.412** — nhỏ hơn một lượt sinh dài nhất mà chính ta cho phép
#:    (`TOKEN_RA_TRAN` = 32.768). Cấu hình ấy **không thể** giữ lời hứa "nén
#:    trước khi chạm trần"; nó chỉ đúng chừng nào không ai trả lời dài.
#:
#: ⭐ Nên quy tắc là: **chừa trọn một lượt sinh dài nhất** giữa ngưỡng nén và
#:    cửa sổ công bố. Kết quả có một tính chất đáng chú ý: ở hồ sơ ngữ cảnh rộng
#:    nó xấp xỉ đúng 0,8 cũ — con số cũ không sai vì bịa, nó sai vì **được chọn ở
#:    một cửa sổ rộng rồi mang sang một cửa sổ hẹp** mà không ai tính lại.
def nen_cua(model_id: str) -> int:
    """Ngưỡng nén hội thoại **công bố cho client** của một model.

    ⛔ TRẢ **0** KHI KHÔNG ĐỊNH NGHĨA ĐƯỢC, chứ không kẹp về một số trông hợp lệ.
       `qwen38-vision` chạy `-c 65536` và vẫn chịu chung `TOKEN_RA_TRAN` 32.768,
       nên cửa sổ công bố của nó (28.262) **hẹp hơn một lượt sinh dài nhất**:
       không có ngưỡng nén nào giữ được lời hứa, kể cả ngưỡng bằng 1.

    ⭐ Con số 0 là một câu trả lời, không phải một lỗi: nó nói *"model này không
       phải model để chạy một phiên agent dài"*. Bộ cài đọc 0 thì **bỏ hẳn**
       trường ngưỡng nén thay vì ghi một con số bịa vào tệp cấu hình của khách —
       và đó đúng là khác biệt giữa "khách biết mình đang ở đâu" và "khách tin
       một lời hứa ta không giữ được".
    """
    con = cong_bo_cua(model_id) - TOKEN_RA_TRAN
    return con if con > 0 else 0


#: Ngưỡng nén của model text — con số hai bộ cài chép sang máy khách.
NEN_CHO_CLIENT = nen_cua("qwen38-api")


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
    # 🔴 KỊCH TRẦN, CÓ CHỦ Ý — và con số 8.192 trước đó là một lỗi ĐO ĐƯỢC.
    #
    #    Lần đầu tôi đặt 8.192 với lý do "đặt kịch trần bắt khách phải có số dư
    #    gấp bốn lần nhu cầu thật". **Lý do đó sai, và phép đo bác bỏ nó**: giá
    #    ra là 400 credit/1M token, nên giữ trước cho 32.768 token chỉ là
    #    **13,1 credit** — 1% số dư của một tài khoản thường. Không có "ví mỏng
    #    bị từ chối oan" nào cả.
    #
    # ⛔ CÁI GIÁ CỦA VIỆC ĐẶT THẤP THÌ ĐO ĐƯỢC VÀ ĐẮT: 30/08, một lượt Codex viết
    #    ba tệp Python dừng ở **đúng 8.192 token** (`STREAM XONG … token_ra=8192`,
    #    138 giây). Phản hồi cụt ⇒ Codex không dùng được ⇒ **không tệp nào được
    #    tạo**, và khách chỉ thấy "chạy 2 phút rồi không có gì". Đúng lớp lỗi của
    #    trần 1.024 cũ, chỉ dịch lên một nấc.
    #
    # ⭐ NÊN LUẬT LÀ: cửa stream KHÔNG có trần ẩn nào dưới trần đã công bố. Model
    #    tự dừng khi trả lời xong; credit giữ trước rồi **hoàn** về token thật
    #    sinh ra; và `tran_theo_ngu_canh()` vẫn tự siết theo ngữ cảnh còn lại.
    #    Bất kỳ số nào nhỏ hơn `TOKEN_RA_TRAN` đều chỉ là một chỗ để cụt lần sau.
    "stream": TOKEN_RA_TRAN,
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

#: Số slot song song của `llama-server` trên máy B (`--parallel`). **MỘT nguồn**:
#: manifest `admission_slots`, env gateway `LTT_LLM_MAX_DONG_THOI` và cờ
#: `--parallel` trong `llm_gateway/deploy/llama-swap.yaml` đều phải bằng số này
#: (`tests/test_1201`, `tests/test_334`).
#:
#: 🔴 LÝ DO CŨ "1 vì speculative decoding chỉ tối ưu một luồng; `--parallel 2`
#:    thấp ~20%" ĐÃ ĐO LẠI VÀ KHÔNG ĐÚNG TRÊN 3090 (multijob M-1, 11/09): con số
#:    −20% đo trên RTX 5090; trên máy B `-np 4 -kvu` giữ C1 60–63 tok/s và gấp
#:    đôi C4. Xem `docs/multijob/00_BASELINE.md`.
#:
#: ⛔ Đổi số này KHÔNG an toàn một mình: `-kvu` + nhiều slot mà thiếu admission
#:    ngân sách KV thì một lần tràn pool giết MỌI slot (llama.cpp b10689,
#:    `server-context.cpp:3661-3708`). Ngân sách nằm ở `POOL_KV_MAY_B` bên dưới.
SO_SLOT_MAY_B = 1

#: Tên cũ, giữ làm **bí danh** (cùng một số, không phải số thứ hai) cho mã và
#: phép kiểm đang đọc nó.
DONG_THOI_MAY_B = SO_SLOT_MAY_B

#: Pool KV dùng chung giữa các slot khi `-kvu`: chính là cửa sổ engine. Nền tảng
#: nhận nó qua `ToolSpec.admission_token_pool` (không import app).
POOL_KV_MAY_B = CUA_SO_MODEL


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
