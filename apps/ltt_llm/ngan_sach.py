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
#  SỐ GÕ TAY — mọi thứ dưới đây tính ra từ chúng
# ══════════════════════════════════════════════════════════════════════════

#: Id model nội bộ **mặc định** — model mọi bí danh cũ đã di trú về (D02).
#: Mọi hàm theo-model nhận `model_id`; hằng cấp module nào còn phải là **một**
#: con số (bộ cài client, `LTT_LLM_MAX_INPUT_TOKENS` của máy B…) lấy của model này.
MODEL_MAC_DINH = "qwen38-api"

#: 🔑 CỬA SỔ ENGINE THEO **ID MODEL NỘI BỘ** — hai model, hai card, hai con số.
#:
#: Khoá là id của máy B, không phải bí danh công khai (bí danh không bao giờ rời
#: máy A — INV-015). Đây là **số ĐO**, đo từ `-c` của llama-server ở đúng cấu
#: hình sẽ triển khai, không phải số mong muốn:
#:
#:   * `qwen38-api` (RTX 3090) **221_184** — `docs/ltt_llm_dual/10_BENCHMARK_P3.md`
#:     §G1b, chốt ở `DECISION_LOG.md` L-14. Mốc **cao nhất còn sạch** ở `-ub` mặc
#:     định với `-np 3` + mmproj trên GPU: VRAM 24.131 MiB, `Shared` 568 (nằm
#:     trong dải sàn 526–568 ⇒ **không tràn**), biên 445 MiB. Bước lên 229.376 là
#:     `Shared` đã vượt sàn ~140 MiB. 262.144 (điều `constraints.md` viết ban đầu)
#:     **không vừa card** cùng mmproj — đo được ~25,2 GB.
#:   * `qwen35-api` (RTX 5060 Ti) **262_144** — §G3: VRAM 13.423 MiB, `Shared`
#:     354 (không tràn), biên 2.888 MiB ngay ở **4** slot. Card này không bị ràng
#:     buộc như 3090; 262.144 là ngữ cảnh đầy đủ của model.
#:
#: ⛔ Đổi `-c` của một hồ sơ bên B thì đổi đúng khoá của nó ở đây — và **chỉ**
#:    khoá đó. Một con số dùng cho hai model là một con số sai cho ít nhất một
#:    trong hai (khuyết tật F-02).
#:
#: ⚠️ VÀ MỘT CẢNH BÁO CHO NGƯỜI SỬA TIẾP: đổi số ở đây **không đủ** để máy B đổi
#:    theo. `llm_gateway/deploy/deploy.ps1` ghi đè `LTT_LLM_MAX_INPUT_TOKENS`
#:    bằng số gõ tay, và nó chép `llama-swap.yaml` mà **không** restart
#:    `LTTLlamaSwap`. Thứ tự deploy nằm ở §7 của
#:    `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md` và nó **không hoán vị được**.
#:    `test_334` chốt các bản sao đó.
CUA_SO_THEO_MODEL = {
    "qwen38-api": 221_184,
    "qwen35-api": 262_144,
}

#: Cửa sổ ngữ cảnh của model **mặc định** — bí danh của một ô trong bảng trên.
#: ⛔ ĐỪNG gõ một con số vào đây: hai nơi khai cùng một điều là hai nơi lệch nhau.
#:
#: 📈 03/09: 131.072 → 204.800, kèm KV cache `q8_0` → `q4_0` (bắt buộc: `q8_0`
#:    ở 204.800 không vừa card 24 GB). 12/09: 204.800 → **221.184** (L-14, §G1b) —
#:    cùng lúc `qwen38-vision` biến mất, vì hồ sơ mới mang mmproj trên GPU nên
#:    **một hồ sơ text+vision duy nhất** là đủ.
#:
#: 🔴 `CUA_SO_MODEL_VISION` ĐÃ ĐƯỢC GỠ Ở ĐÂY (dual-model 2.6) — và nó đáng được
#:    ghi lại, vì sự tồn tại của nó từng là một lời hứa sai. Trước 01/09 hai
#:    alias `ltt_llm`/`ltt_llm_vision` dùng **chung** một con số công bố, nên
#:    `/api/v1/models` nói vision có *"same 89K usable input context"* trong khi
#:    máy B chặn nó ở 65.536 (đo thật: `413 {"tran":65536,"thay":71281}`). Cách
#:    chữa hồi ấy là **thêm một cửa sổ thứ hai**; cách chữa bây giờ là **xoá cả
#:    hồ sơ**: `qwen38-api` tự nạp mmproj nên không còn model vision riêng để nói
#:    sai về. Nguồn lỗi `ConnectionReset` do llama-swap đổi hồ sơ giữa chừng cũng
#:    biến mất cùng nó (L-14 hệ quả 4).
CUA_SO_MODEL = CUA_SO_THEO_MODEL[MODEL_MAC_DINH]

#: Cửa sổ **hẹp nhất** trong các model đang bán. Mọi chỗ phải kẹp một con số mà
#: **chưa biết model** dùng cái này chứ không dùng cái rộng nhất: kẹp rộng hơn
#: cửa sổ thật của model đang chạy là để model tự cắt ngữ cảnh — thứ hỏng không
#: sạch và rất khó truy.
CUA_SO_HEP_NHAT = min(CUA_SO_THEO_MODEL.values())

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

#: Trần đầu vào thật sự dùng được **của model mặc định**: chừa đủ chỗ cho một
#: câu trả lời dài nhất. Đây là số máy B phải khai ở `LTT_LLM_MAX_INPUT_TOKENS`.
#: ⛔ Một con số, nên nó chỉ đúng cho MỘT model. Đường theo-model là
#:    `tran_vao_cua(model_id)` — cùng công thức, khác cửa sổ.
TOKEN_VAO_TRAN = CUA_SO_MODEL - TOKEN_RA_TRAN - LE           # 186_368

#: Số byte JSON cho mỗi token khi hội thoại đi trên dây. Đo 30/08 trên thân
#: request thật của Codex (kể cả dấu ngoặc, escape và định nghĩa tool).
BYTE_MOI_TOKEN_JSON = 4.5

#: Trần thân request **tối thiểu** phải cho phép, để `TOKEN_VAO_TRAN` không bị
#: chặn bởi kích thước byte trước khi ai kịp đếm token.
#:
#: ⛔ ĐÂY LÀ MỘT LỖI ĐÃ XẢY RA: trần body 256 KB của nền tảng chặn hội thoại dài
#:    ở khoảng 64.000 token — gần bằng 65.000 nên suốt buổi ta tưởng đang chạm
#:    trần của máy B. Hai trần không liên quan gì nhau mà cái nhỏ hơn thắng.
#:
#: ⭐ TÍNH THEO MODEL **RỘNG NHẤT**, không theo model mặc định: trần body là một
#:    con số của cả cửa `/api/v1`, và một request `ltt-3.5` hợp lệ ở trần token
#:    của NÓ phải lọt qua. Lấy theo model mặc định (hẹp hơn) là dựng lại đúng
#:    lỗi "hai trần không biết nhau" cho model kia.
BODY_BYTES_TOI_THIEU = int(
    (max(CUA_SO_THEO_MODEL.values()) - TOKEN_RA_TRAN - LE)
    * BYTE_MOI_TOKEN_JSON)                                        # ~999 KB

#: Cửa sổ **công bố** cho client agentic (Codex, Claude Code) để chúng nén hội
#: thoại **trước** khi chạm trần. Chừa 8% cho lệch tokenizer: client đếm token
#: bằng bộ đếm của nó, model đếm bằng bộ của Qwen, hai số không bao giờ khớp.
CONG_BO_CHO_CLIENT = int(TOKEN_VAO_TRAN * 0.92)                   # 171_458


# ── Ngân sách THEO MODEL ───────────────────────────────────────────────────
#
# ⭐ Hai model, hai cửa sổ, nên **hai bộ số** — và đó là toàn bộ bài học của
#    khuyết tật F-02: một con số dùng cho hai model là một con số sai cho ít
#    nhất một trong hai.
#
# ⛔ Công thức phải GIỐNG HỆT đường text ở trên (chừa `TOKEN_RA_TRAN` cho câu
#    trả lời dài nhất, chừa `LE` cho sai số ước, rồi bớt 8 % lệch tokenizer).
#    Nếu một model được một công thức "nới tay" riêng thì con số công bố của hai
#    model không còn mang **cùng một lời hứa**, và khách không có cách nào biết
#    lời hứa nào áp cho model nào.
#
# 🔑 Bảng cửa sổ (`CUA_SO_THEO_MODEL`) nằm ở đầu tệp, cùng chỗ với các số gõ tay
#    khác — vì từ 2.6 nó CHÍNH LÀ số gõ tay, còn `CUA_SO_MODEL` là bí danh của
#    một ô trong nó. Trước 2.6 thứ tự ngược lại, và đó là lý do một con số của
#    model text rò sang model kia.


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
       Hai model hôm nay đều rộng nên cả hai trả số dương; nhánh 0 vẫn phải sống.
       Nó viết ra vì `qwen38-vision` (`-c 65536`, đã gỡ ở 2.6) có cửa sổ công bố
       28.262 — **hẹp hơn một lượt sinh dài nhất** — nên không ngưỡng nén nào giữ
       được lời hứa, kể cả ngưỡng bằng 1. Model nào hẹp như thế quay lại thì
       nhánh này là câu trả lời sẵn có, không phải một lỗi phải sửa lần nữa.

    ⭐ Con số 0 là một câu trả lời, không phải một lỗi: nó nói *"model này không
       phải model để chạy một phiên agent dài"*. Bộ cài đọc 0 thì **bỏ hẳn**
       trường ngưỡng nén thay vì ghi một con số bịa vào tệp cấu hình của khách —
       và đó đúng là khác biệt giữa "khách biết mình đang ở đâu" và "khách tin
       một lời hứa ta không giữ được".
    """
    con = cong_bo_cua(model_id) - TOKEN_RA_TRAN
    return con if con > 0 else 0


#: Ngưỡng nén của model **mặc định** — con số hai bộ cài chép sang máy khách.
NEN_CHO_CLIENT = nen_cua(MODEL_MAC_DINH)


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
#:
#: 📈 12/09: 1 → **3** (L-14, §G1b). ⛔ **3, KHÔNG PHẢI 4** — và lý do khác nhau
#:    ở hai card, nên đừng đọc con số này là "giới hạn phần cứng":
#:
#:      * `qwen38-api` / 3090: 4 slot ở ngữ cảnh đã chốt **tràn** sang RAM chủ.
#:        3 là trần thật. Mọi chỗ plan/spec viết "C4" đọc lại là **C3**.
#:      * `qwen35-api` / 5060 Ti: §G3 đo 262.144 × **4** slot vừa thoải mái (VRAM
#:        13.423 MiB, biên 2.888 MiB). 3 ở đây là **lựa chọn** của chủ dự án cho
#:        nhất quán hai card (12/09: *"cứ để 3 cho nhất quán 2 card"*), không phải
#:        giới hạn. Muốn nâng 3.5 lên 4 thì chỉ cần đổi một con số —
#:        `admission_theo_model` khai số suất theo TỪNG model, hai card không
#:        buộc bằng nhau.
SO_SLOT_MAY_B = 3

#: Tên cũ, giữ làm **bí danh** (cùng một số, không phải số thứ hai) cho mã và
#: phép kiểm đang đọc nó.
DONG_THOI_MAY_B = SO_SLOT_MAY_B

#: Pool KV **theo model** khi `-kvu`: chính là cửa sổ engine của từng hồ sơ.
#: Nền tảng nhận nó qua `ToolSpec.admission_theo_model` (không import app).
POOL_KV = dict(CUA_SO_THEO_MODEL)

#: Tên cũ, giữ làm **bí danh** cho model mặc định (một số, không phải số thứ hai).
POOL_KV_MAY_B = CUA_SO_MODEL

# ── Sức chứa THEO MODEL (dual-model 2.3 nối dây, 2.6 chốt số ĐO) ─────────────
#
# 🔑 Hai model công khai chạy trên **hai card khác nhau** của máy B, nên mỗi cái
#    có pool KV riêng. Bản khai admission ở `manifest.py` đọc đúng ba hằng dưới
#    đây — **đừng gõ số vào manifest** (test_1201 chốt điều đó).

#: Số slot song song cho MỖI model. Bí danh của `SO_SLOT_MAY_B`.
SO_SLOT = SO_SLOT_MAY_B

#: Ngân sách KV của `ltt-3.8` (3090) và `ltt-3.5` (5060 Ti).
POOL_38 = POOL_KV["qwen38-api"]
POOL_35 = POOL_KV["qwen35-api"]

#: Tên tài nguyên admission của từng model. Chúng phải **khác nhau**: hai card
#: khác nhau thì một suất giành trên card này không nói gì về card kia, và gộp
#: tên là biến hai hàng đợi thành một cách âm thầm.
TAI_NGUYEN_38 = "ltt_38_3090"
TAI_NGUYEN_35 = "ltt_35_5060"

#: Nhóm cư trú GPU của `ltt-3.8` (trọng tài residency, Task 5.x). `ltt-3.5` nằm
#: trên card riêng nên không tranh cư trú với ai.
NHOM_CU_TRU_38 = "rtx3090"


def tran_theo_ngu_canh(token_vao_uoc: int, model_id: str | None = None) -> int:
    """Trần token ra **thật sự dùng được**, biết ngữ cảnh còn bao nhiêu.

    Vào và ra chia nhau cùng một cửa sổ. Một lượt có 100.000 token vào mà xin
    32.768 token ra thì tổng vượt cửa sổ, và thứ hỏng ở đó **không phải một lỗi
    sạch** — model cắt bớt ngữ cảnh hoặc thượng nguồn từ chối, cả hai đều khó truy.

    ⛔ Trả về ít nhất 1: một lượt hết chỗ phải hỏng ở **chốt token VÀO** với
       thông điệp đúng, chứ không biến thành `max_tokens=0`.

    ⭐ `model_id=None` ⇒ **cửa sổ HẸP NHẤT**, không phải cửa sổ của model mặc
       định và tuyệt đối không phải cửa sổ rộng nhất. Bên gọi không nêu model là
       bên gọi không biết mình đang ở model nào; con số duy nhất an toàn khi
       không biết là con số đúng cho cả hai. Trước 2.6 chỗ này dùng
       `CUA_SO_MODEL` **vô điều kiện** và nó chỉ đúng nhờ một bất biến ở nơi
       khác (`tran_vao_cua` đã trừ sẵn `TOKEN_RA_TRAN`) — loại "đúng nhờ hằng số
       bên cạnh", mất đi mà không có gì kêu.
    """
    cua_so = (CUA_SO_HEP_NHAT if model_id is None
              else CUA_SO_THEO_MODEL[model_id])
    con_lai = cua_so - int(token_vao_uoc or 0) - LE
    return max(1, min(TOKEN_RA_TRAN, con_lai))


# ══════════════════════════════════════════════════════════════════════════
#  SỐ ĐO THEO MODEL — đo ở đúng cấu hình sẽ triển khai (G4, 12/09)
# ══════════════════════════════════════════════════════════════════════════
#
# ⛔ Bốn hằng dưới đây là **số đo**, nguồn `docs/ltt_llm_dual/10_BENCHMARK_P3.md`
#    §G4. Chúng ở đây chứ không ở chỗ dùng, vì mỗi cái đã có sẵn một bản sao gõ
#    tay ở nơi khác và đó chính là lớp lỗi tệp này sinh ra để dẹp.

#: Prefill tok/s theo **độ dài prompt**, từng model — đo ở cấu hình L-14 + L-16.
#: Đây là đường cong, không phải một con số: 3.8 tụt từ 1.239 xuống 646 tok/s
#: giữa 6,7K và 163K, nên "prefill bao lâu" không suy ra được từ một điểm.
DUONG_PREFILL_TOK_S = {
    "qwen38-api": ((786, 977.0), (6_700, 1_239.0), (32_600, 1_132.0),
                   (98_000, 842.0), (163_000, 646.0)),
    "qwen35-api": ((786, 1_765.0), (6_700, 2_238.0), (32_600, 2_059.0),
                   (98_000, 1_630.0), (163_000, 1_350.0)),
}

#: Token ngữ cảnh một ảnh 1024×768 ăn. Đo bằng **hiệu** `n_prompt_tokens` giữa
#: cùng một câu hỏi có ảnh và không ảnh (17 → 787), nên phần chữ triệt tiêu.
#: Giống nhau ở cả hai model. ⛔ Không ước bằng công thức patch: mỗi bản mmproj
#: băm ảnh một kiểu, và con số này **đi thẳng vào hoá đơn**.
TOKEN_MOI_ANH = 770

#: Thời gian nạp model từ **kho ấm** (tệp vừa đọc ở lượt trước), giây.
#: ⚠️ Máy trạng thái residency (Task 5.2) đang giả định 45,0 — gấp 2,8 lần thực
#:    tế, tức trọng tài ngần ngại đổi cư trú và 3090 nằm sai chỗ lâu hơn cần.
#:    Task 5.2 phải **đọc hằng này**, không gõ lại một con số thứ hai.
NAP_KHO_AM_S = {"qwen38-api": 16.3, "qwen35-api": 12.1}

#: ⭐ THỜI GIAN CHẶN TỐI ĐA TA TUYÊN BỐ LÀ CHẤP NHẬN ĐƯỢC, giây.
#:
#: Đây là một **tuyên bố**, không phải một phép đo — và nó phải nói ra như vậy.
#: Con số lấy từ `LTT_LLM_CHO_WHALE_S` mặc định của
#: `platform_core/llm/tham_so_da_luot.py`: kho này đã tuyên bố 30 s là mức lâu
#: nhất một lượt tương tác bị bắt nhường. Dùng lại chính nó thay vì đẻ ra một
#: ngưỡng thứ hai cho cùng một câu hỏi.
WHALE_CHAN_TOI_DA_S = 30.0


def thoi_gian_prefill_s(model_id: str, token_vao: int) -> float:
    """Prefill của `token_vao` token trên `model_id` mất bao nhiêu giây.

    Nội suy tuyến tính giữa các điểm đo; ngoài dải thì kẹp về điểm đầu/cuối
    (⛔ **không** ngoại suy — đường cong này không có dạng hàm nào được đo).
    """
    diem = DUONG_PREFILL_TOK_S[model_id]
    n = max(1, int(token_vao))
    if n <= diem[0][0]:
        toc = diem[0][1]
    elif n >= diem[-1][0]:
        toc = diem[-1][1]
    else:
        toc = diem[-1][1]
        for (a, ra), (b, rb) in zip(diem, diem[1:], strict=False):
            if a <= n <= b:
                toc = ra + (n - a) * (rb - ra) / (b - a)
                break
    return n / toc


def _nguong_whale(model_id: str) -> int:
    """Độ dài prompt dài nhất còn prefill **trong** `WHALE_CHAN_TOI_DA_S`.

    ⭐ DẪN XUẤT, KHÔNG CHÉP. Bước 512 = `-ub` mặc định của llama-server (§G1b) —
       đơn vị prefill thật sự tiến theo, nên làm tròn xuống bội của 512 là làm
       tròn xuống một mốc **có nghĩa cơ học**, không phải cho tròn mắt.
    """
    n = 512
    while thoi_gian_prefill_s(model_id, n + 512) <= WHALE_CHAN_TOI_DA_S:
        n += 512
    return n


#: 🔑 NGƯỠNG "CÁ VOI" — từ độ dài nào thì một lượt đủ làm nghèo slot người khác.
#:
#: ⛔ PHẢI KHÁC NHAU THEO MODEL, VÀ ĐÂY LÀ PHÉP ĐO NÓI THẾ, không phải sở thích:
#:    một lượt 163K token chặn prefill **257 s trên 3.8** nhưng chỉ **125 s trên
#:    3.5** (§G4). Chép một con số từ model này sang model kia là tuyên bố hai
#:    card có cùng đường cong — và bảng §G4 bác bỏ điều đó ở **mọi** độ dài.
#:
#: ⭐ CÁCH DẪN XUẤT (tái hiện được bằng `_nguong_whale` ngay trên):
#:      1. Tuyên bố mức chặn không chấp nhận được: **30 s** (`WHALE_CHAN_TOI_DA_S`,
#:         chính là `LTT_LLM_CHO_WHALE_S` kho này đã dùng).
#:      2. Giải `token / prefill_tok_s(token) = 30` trên đường cong ĐO của TỪNG
#:         model (nội suy tuyến tính giữa các điểm), làm tròn xuống bội 512.
#:      3. Kết quả: `qwen38-api` **33.792** (29,99 s) · `qwen35-api` **56.832**
#:         (29,91 s). Bước tiếp theo của mỗi cái đã vượt 30 s.
#:
#: 🔴 SỐ NÀY KHÔNG PHẢI SỐ TRONG PLAN, VÀ ĐÓ LÀ CÓ CHỦ Ý. Plan ghi tạm
#:    `16_384 / 32_768`; đường cong đo cho hai con số đó **13,7 s** và **15,9 s**
#:    — tức chúng gắn cờ "cá voi" cho những lượt chặn chưa tới một nửa ngưỡng ta
#:    tuyên bố. Chúng không sai về hướng (3.5 phải cao hơn 3.8), chúng chỉ không
#:    **dẫn xuất từ** cái gì cả. Tỉ lệ đúng theo đo là 1,68× chứ không phải 2×.
NGUONG_WHALE = {m: _nguong_whale(m) for m in DUONG_PREFILL_TOK_S}
