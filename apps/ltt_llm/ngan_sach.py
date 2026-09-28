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

from dataclasses import dataclass

# ══════════════════════════════════════════════════════════════════════════
#  SỐ GÕ TAY — mọi thứ dưới đây tính ra từ chúng
# ══════════════════════════════════════════════════════════════════════════

#: Id model nội bộ **mặc định** — model mọi bí danh cũ đã di trú về (D02).
#: Mọi hàm theo-model nhận `model_id`; hằng cấp module nào còn phải là **một**
#: con số (bộ cài client, trần vào của bí danh lạ…) lấy của model này.
MODEL_MAC_DINH = "qwen38-api"

#: Trần token ra cứng cho một lượt. Khớp `LTT_LLM_MAX_OUTPUT_TOKENS` của máy B.
#: ⭐ Phải ≥ 32.000: Claude Code gửi `max_tokens: 32000` mặc định và khách gần
#:    như không đổi được — trần thấp hơn khiến Claude Code không dùng được (H38/L2).
TOKEN_RA_TRAN = 32_768

#: 🔑 ĐỆM ƯỚC — MỘT con số cho câu hỏi *"phép ước token vào lệch tối đa bao nhiêu"*.
#:
#: Chừa cho khuôn chat, định nghĩa tool và sai số của phép **ước** token vào
#: (`uoc_token_vao` là ước chứ không phải đếm thật). Dùng ở HAI chỗ và phải là
#: CÙNG một số ở cả hai, vì bất biến `vào ≤ tran_vao ⇒ đặt chỗ ≤ -c` dựa trên nó:
#:   * trần vào  `tran_vao_cua(m) = -c − TOKEN_RA_TRAN − DEM_UOC` (413 trước 200);
#:   * đặt chỗ   `vào + ra + DEM_UOC + ảnh × TOKEN_GIU_MOI_ANH` (`luat_nhan` luật 2).
#:
#: 🔴 PHƯƠNG ÁN C bước 2 (O-08, 17/09/2026): ĐÃ THAY hai tên cũ trả lời cùng câu
#:    hỏi — `LE` (ở đây, 30/08) và `dem_dat_truoc` (env `LTT_LLM_DEM_DAT_TRUOC`
#:    của `platform_core/llm/tham_so_da_luot.py`, 11/09, ĐÃ GỠ). Đổi một cái mà
#:    quên cái kia thì bất biến trên gãy IM LẶNG (`luat_cho` từng kẹp về pool).
DEM_UOC = 2_048

#: Token ĐẶT CHỖ cho mỗi ảnh (sổ KV, không phải hoá đơn).
#:
#: ⛔ KHÁC `TOKEN_MOI_ANH` (770 — xem hằng ấy). Đặt chỗ phải phủ ảnh LỚN NHẤT
#:    được phép; đặt chỗ thừa chỉ tốn suất, đặt thiếu là tràn `-kvu`.
#: 🔴 O-11 (17/09): thay env `LTT_LLM_TOKEN_MOI_ANH` (ĐÃ GỠ).
#:
#: ══════════════════════════════════════════════════════════════════════════
#: 🔴 ĐÃ ĐO 28/09/2026 — VÀ SỐ ĐO PHỦ ĐỊNH CHÍNH HẰNG NÀY
#:
#: Bản trước của chú thích này viết: *"Đặt chỗ phải phủ ảnh LỚN NHẤT được phép,
#: và **chưa ai đo ảnh ấy** — nên giữ 2.048 … **cho tới khi đo**."* Nay đã đo,
#: nên điều kiện tự đặt ra ấy đã tới hạn.
#:
#: Chi phí thật là một HÀM của kích thước, không phải một hằng. Đo bằng hiệu
#: `usage.prompt_tokens` trên CẢ HAI model production (`tools/do_token_anh.py`,
#: 14/14 ô khớp), và công thức chốt từ siêu dữ liệu GGUF của chính hai tệp
#: mmproj (`clip.projector_type = qwen3vl_merger`, `patch_size = 16`,
#: `spatial_merge_size = 2` ⇒ **1 token = 32×32 điểm ảnh**):
#:
#:      320×240   →     82        1920×1080 →  2.042   (≈ 2.048: hằng này được
#:      512×512   →    258        2048×2048 →  4.098    hiệu chuẩn cho 1080p,
#:      1024×768  →    770        3840×2160 →  4.082    và CHỈ đúng ở 1080p)
#:      1280×720  →    922
#:
#: ⇒ 2.048 sai **CẢ HAI CHIỀU**: thừa tới 136× ở ảnh 320×240, và 🔴 **THIẾU 2×**
#:   ở 2048×2048 — vốn đúng bằng cỡ tối đa client LTTCODE gửi
#:   (`plugins/llm-ltt/src/adapter.ts` `IMAGE_BUDGET.maxPixels = 2048²`).
#:   Thiếu là chiều nguy hiểm: `DatChoVuotPool` sinh ra để chặn đúng chiều ấy,
#:   và một lần tràn `-kvu` giết MỌI slot (llama.cpp b10689).
#:
#: ⇒ Hằng này **sẽ bị gỡ** ở Pha 3, thay bằng `Σ anh_token.token_anh(w, h)`.
#:   Giữ lại tới lúc đó vì gỡ nó đụng bốn tệp ở hai máy.
#:   Kế hoạch: `docs/superpowers/specs/2026-09-28-vision-plan-lock.md`.
#: ══════════════════════════════════════════════════════════════════════════
TOKEN_GIU_MOI_ANH = 2_048

#: Biên bể KV (token) A không cho đặt chỗ — `token_budget = -c − BIEN_POOL_TOKEN`.
#:
#: 🔴 17/09/2026 `KET_QUA_DO_17_09.md` (`da153d40`): trên b10883 tràn `-kvu` giết
#:    các luồng GIỮA CHỪNG, sau khi đã trả 200; draft MTP (`--spec-draft-n-max 2`)
#:    và sai số ước chiếm KV mà phép đặt chỗ không đếm. Đề xuất `-c − 8.192`.
#: ✅ CHỦ DỰ ÁN CHỐT 17/09/2026: `token_budget = -c − 8.192`, `-np 3` và `-c`
#:    giữ nguyên (3.8 ⇒ 212.992, 3.5 ⇒ 253.952). 18/09 (L-28) 3.5 lên `-np 4`
#:    ở cùng `-c` ⇒ ngân sách KV không đổi (`-kvu`: một bể chung mọi slot).
#: ⚠️ Hệ quả phải biết (`test_1229`): với LTTCODE gửi `max_tokens` 24.000 (chốt cùng
#:    ngày), ví dụ 15K+100K chạy / 110K chờ / 55K backfill KHÔNG đạt trên 3.8 —
#:    55K cần 81.048, hai lượt đang chạy giữ 167.096 ⇒ 248.144 > 212.992. Backfill
#:    ở ví dụ ấy chỉ có khi giữ chỗ đầu ra ≤ 12.282 token.
BIEN_POOL_TOKEN = 8_192


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
#: Giống nhau ở cả hai model.
#:
#: 🔴 ĐÍNH CHÍNH 28/09/2026 — HAI CÂU Ở ĐÂY SAI, VÀ CẢ HAI ĐỀU DẠY NGƯỜI SAU SAI:
#:
#: 1. *"con số này **đi thẳng vào hoá đơn**"* — **KHÔNG**. Hoá đơn đọc
#:    `usage.prompt_tokens` THẬT của llama-server (`llm_gateway/so_luot.py`,
#:    `platform_core/llm/cong_vlm.py`), và `prompt_tokens` **đã tính token ảnh**.
#:    Hằng này chỉ được `apps/auto_scan_video` dùng để **ước trước** (`test_436`).
#:    ⇒ Hoá đơn ảnh **vốn đã đúng theo độ phân giải**. Đừng "sửa" nó.
#:
#: 2. *"⛔ Không ước bằng công thức patch: mỗi bản mmproj băm ảnh một kiểu"* —
#:    đúng về nguyên tắc, sai về sự thật ở đây. Đọc siêu dữ liệu GGUF của **cả
#:    hai** mmproj: `clip.projector_type = 'qwen3vl_merger'`, `patch_size = 16`,
#:    `spatial_merge_size = 2` ⇒ công thức có thật và **giống nhau ở hai model**.
#:    Nó cho đúng 770 cho 1024×768 (= 32×24 + 2 dấu vision) và khớp **14/14** ô
#:    đo trên production. Xem `tools/do_token_anh.py`.
#:
#: ⇒ 770 **chỉ đúng cho 1024×768**. Đừng dùng nó như "chi phí một ảnh".
#:    Chi phí một ảnh bất kỳ: `anh_token.token_anh(w, h)`.
TOKEN_MOI_ANH = 770

#: 🔴 TRẦN ẢNH — cưỡng chế ở **cổng máy B**, công bố ở đây. Thêm 14/09/2026.
#:
#:    Đo 14/09 trên production: gửi **4** ảnh → 200; gửi **5** → 400. Tức trần
#:    có thật và đang chạy — nhưng **không chỗ nào công bố nó**. Khách chỉ biết
#:    khi đã đâm vào, và trước bản vá P0-2 cùng ngày thì thông điệp còn là
#:    *"yeu cau vuot tran cua cong"*, không nói trần nào hay bao nhiêu.
#:
#: ⛔ HAI SỐ NÀY LÀ **BẢN SAO** CỦA `llm_gateway/config.py` TRÊN MÁY B
#:    (`LTT_LLM_MAX_IMAGES`, `LTT_LLM_MAX_IMAGE_BYTES`). Máy A **không** cưỡng
#:    chế chúng — nó chỉ *đếm* ảnh để tính ngân sách KV (`luong.dem_anh`), còn
#:    người từ chối vẫn là cổng máy B. Giữ đúng một người cưỡng chế là có chủ ý:
#:    hai nơi cùng chặn là hai nơi sẽ lệch nhau.
#:
#: ⚠️ Nên bản sao này **phải có người canh**: `test_1259` đối chiếu nó với
#:    `llama-swap`/cổng máy B. Một con số chép sang mà không ai đối chiếu chính
#:    là cơ chế đã làm bảng ở kho này nói sai **năm lần**.
SO_ANH_TOI_DA = 4
ANH_BYTE_TOI_DA = 12 * 1024 * 1024

#: Thời gian nạp model từ **kho ấm** (tệp vừa đọc ở lượt trước), giây.
#: ⚠️ Máy trạng thái residency (Task 5.2) đang giả định 45,0 — gấp 2,8 lần thực
#:    tế, tức trọng tài ngần ngại đổi cư trú và 3090 nằm sai chỗ lâu hơn cần.
#:    Task 5.2 phải **đọc hằng này**, không gõ lại một con số thứ hai.
NAP_KHO_AM_S = {"qwen38-api": 16.3, "qwen35-api": 12.1}

#: ⭐ THỜI GIAN CHẶN TỐI ĐA TA TUYÊN BỐ LÀ CHẤP NHẬN ĐƯỢC, giây.
#:
#: Đây là một **tuyên bố**, không phải một phép đo — và nó phải nói ra như vậy:
#: *"prefill của một lượt được làm nghèo các lượt khác tối đa bao lâu"*. Ngưỡng
#: whale theo đường cong (`nguong_whale_theo_chan`) là ƯỚC cho mục tiêu này; số ĐANG
#: CHẠY là số chủ dự án chọn (`NGUONG_WHALE`, dưới).
#:
#: 🔴 KHÔNG còn buộc bằng `LTT_LLM_CHO_WHALE_S` (phương án C bước 2, 17/09). Giá
#:    trị 30 lấy từ đó lúc 12/09, nhưng đó là câu hỏi KHÁC ("whale đứng nhường lượt
#:    tương tác bao lâu", `luat_nhan` luật 5); buộc hai số bằng nhau là chặn đúng
#:    lần đổi số đo đề xuất dưới đây.
#:
#: ✅ CHỦ DỰ ÁN CHỐT 17/09/2026: mục tiêu **9 s** (trước đó 30 s).
#:    `KET_QUA_DO_17_09.md` (nhánh `phien/bench-may-b`, `da153d40`) đo được lượt
#:    đang decode tụt còn ~1,5–2 tok/s SUỐT prefill của lượt khác. Đường cong §G4
#:    ở 9 s cho 10.752 / 18.944 — chỉ là GHI CHÚ; ngưỡng đang chạy là số chủ dự
#:    án chọn tường minh 8.192 / 16.384 (`NGUONG_WHALE`).
WHALE_CHAN_TOI_DA_S = 9.0


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


def nguong_whale_theo_chan(model_id: str, chan_toi_da_s: float) -> int:
    """Độ dài prompt dài nhất còn prefill **trong** `chan_toi_da_s` giây trên `model_id`.

    `chan_toi_da_s` là MỤC TIÊU "một lượt prefill được làm nghèo lượt khác bao
    lâu" — một TUYÊN BỐ, truyền vào tường minh (phương án C bước 2). Hồ sơ dùng
    `WHALE_CHAN_TOI_DA_S`; đổi mục tiêu (vd 9 s theo `KET_QUA_DO_17_09.md`) là
    đổi MỘT dòng ấy, ngưỡng hai model tự dịch theo đường cong của từng model.

    ⭐ DẪN XUẤT, KHÔNG CHÉP. Bước 512 = `-ub` mặc định của llama-server (§G1b) —
       đơn vị prefill thật sự tiến theo, nên làm tròn xuống bội của 512 là làm
       tròn xuống một mốc **có nghĩa cơ học**, không phải cho tròn mắt.
    """
    n = 512
    while thoi_gian_prefill_s(model_id, n + 512) <= float(chan_toi_da_s):
        n += 512
    return n


#: 🔑 NGƯỠNG "CÁ VOI" — từ độ dài nào thì một lượt đủ làm nghèo slot người khác.
#:
#: ⛔ PHẢI KHÁC NHAU THEO MODEL, VÀ ĐÂY LÀ PHÉP ĐO NÓI THẾ, không phải sở thích:
#:    một lượt 163K token chặn prefill **257 s trên 3.8** nhưng chỉ **125 s trên
#:    3.5** (§G4). Chép một con số từ model này sang model kia là tuyên bố hai
#:    card có cùng đường cong — và bảng §G4 bác bỏ điều đó ở **mọi** độ dài.
#:
#: ✅ CHỦ DỰ ÁN CHỌN TƯỜNG MINH 17/09/2026 (DECISION_LOG L-23): **3.8 = 8.192**,
#:    **3.5 = 16.384** token prefill mới. Đây là số GÕ TAY CÓ CHỦ Ý — quyết định
#:    của chủ dự án, không phải kết quả đường cong. Trên đường cong §G4 hai số
#:    này prefill ~6,6 s (3.8) và ~7,6 s (3.5): đều DƯỚI mục tiêu
#:    `WHALE_CHAN_TOI_DA_S` (test_1214 buộc điều đó, không buộc bằng nhau).
#:
#: 📝 Ghi chú — ước theo đường cong (`nguong_whale_theo_chan`): giải
#:    `token / prefill_tok_s(token) = mục tiêu` trên đường cong ĐO của TỪNG model,
#:    làm tròn xuống bội 512 (`-ub`). Ở 9 s: 10.752 · 18.944 (KHÔNG dùng). Ở 30 s
#:    (12/09–17/09, chưa từng chạy trên đường thật): 33.792 · 56.832.
#:
#: 🔴 PHƯƠNG ÁN C bước 2 (O-06, 17/09/2026): TỪ NAY LÀ SỐ ĐANG CHẠY. Trước đó
#:    đường thật dùng một ngưỡng chung 16.384 (env `LTT_LLM_NGUONG_WHALE`, ĐÃ GỠ)
#:    và bảng này chỉ có phép kiểm đọc. Nay `HO_SO[m].nguong_whale` →
#:    `AdmissionModel.nguong_whale` → `tham_so_da_luot.luat_cho` gắn cờ cho MỌI
#:    cửa (stream, đồng bộ, job, nội bộ).
NGUONG_WHALE = {"qwen38-api": 8_192, "qwen35-api": 16_384}

#: 🔑 "MỘT PREFILL DÀI MỖI LÚC" (L-29, Task 17, 18/09/2026) — hệ số chậm khi prefill
#: CHỒNG lên luồng đang decode, đo C4 (`KET_QUA_C4_18_09.md` §2, prefill 32K có người
#: sinh ÷ một mình): 3.8 36,2/29,57 = 1,22 · 3.5 18,2/16,10 = 1,13. Lấy 1,25 phủ cả hai.
HE_SO_PREFILL_CHONG = 1.25


def toc_prefill_uoc(model_id: str) -> float:
    """Tốc độ prefill BẢO THỦ (tok/s) để A ước "lượt này còn prefill tới bao giờ".

    = điểm CHẬM NHẤT của đường cong đo `DUONG_PREFILL_TOK_S` ÷ `HE_SO_PREFILL_CHONG`
    (3.8 646/1,25 ≈ 517 · 3.5 1.350/1,25 = 1.080). Chỉ dùng khi A không có tín hiệu
    byte đầu (cửa đồng bộ/job, và lưới cho cửa stream). ⭐ Chậm hơn thật ⇒ hạn dài
    hơn thật ⇒ sai về phía whale kế chờ lâu hơn, không về phía hai prefill dài chồng.
    """
    return min(v for _, v in DUONG_PREFILL_TOK_S[model_id]) / HE_SO_PREFILL_CHONG


@dataclass(frozen=True)
class HoSoModel:
    """Hồ sơ nhận MỘT model — mọi con số admission của model ấy, một chỗ (phương án C).

    ⭐ Bản khai admission (`manifest.py` → `platform_core.registry.AdmissionModel`)
       đọc **chỉ** từ đây. Đổi `-c`/`-np` của engine (bước 4, số đo) là sửa đúng
       một dòng `HO_SO` + `llm_gateway/deploy/llama-swap.yaml`; `test_1229` đối
       chiếu hai bên.

    ⛔ `__post_init__` NÉM khi hồ sơ tự mâu thuẫn. Một hồ sơ sai phải đỏ ở lúc
       NẠP APP, không phải thành một lượt tràn KV lúc 3 giờ sáng.
    """

    model_id: str
    #: `-c` của hồ sơ trong `llama-swap.yaml`. Với `-kvu`: bể KV CHUNG mọi slot.
    engine_ctx: int
    #: `-np` của hồ sơ — số chuỗi engine chạy song song.
    np: int
    #: Trần số lượt A cho chạy đồng thời (chính sách, ≤ `np`).
    seq_cap: int
    #: Token bể KV A KHÔNG cho đặt chỗ — biên cho thứ engine dùng mà phép đặt chỗ
    #: không đếm (draft MTP, sai số ước). Đơn vị TOKEN, không phải tỉ lệ.
    #: `token_budget = engine_ctx − bien_pool_token`. Xem `BIEN_POOL_TOKEN`.
    bien_pool_token: int
    #: Đệm ước mỗi lượt — xem `DEM_UOC`.
    dem_uoc: int
    #: Token đặt chỗ mỗi ảnh — xem `TOKEN_GIU_MOI_ANH`.
    token_giu_moi_anh: int
    #: Token prefill MỚI từ mức này lượt là whale — `NGUONG_WHALE[model_id]`
    #: (số chủ dự án chọn 17/09, L-23).
    nguong_whale: int
    #: L-29: whale không vào engine khi lượt khác còn prefill (llama.cpp nhồi prompt
    #: theo thứ tự slot — lượt ngắn đang prefill chờ hết prefill dài). Mặc định BẬT.
    mot_prefill_dai: bool = True
    #: Tốc độ prefill bảo thủ cho hạn ước "còn prefill" — `toc_prefill_uoc(m)`.
    toc_prefill_uoc_tok_s: float = 0.0

    def __post_init__(self) -> None:
        if min(self.engine_ctx, self.np, self.seq_cap, self.dem_uoc,
               self.token_giu_moi_anh, self.nguong_whale) <= 0:
            raise ValueError(f"ho so {self.model_id}: moi so phai > 0: {self}")
        if self.seq_cap > self.np:
            raise ValueError(f"ho so {self.model_id}: seq_cap {self.seq_cap} > "
                             f"-np {self.np} — engine khong co chuoi thu {self.np + 1}")
        # ⛔ Biên phải NHỎ HƠN một lượt ra dài nhất: `tran_vao_cua` chừa trọn
        #    `TOKEN_RA_TRAN`, nên lượt vào dài nhất hợp lệ vẫn còn ≥ 1 token ra
        #    trong ngân sách (`tran_theo_ngu_canh` kẹp theo ngân sách). Biên lớn
        #    hơn thế thì lượt qua được 413 lại không bao giờ đặt chỗ vừa.
        if self.mot_prefill_dai and self.toc_prefill_uoc_tok_s <= 0:
            raise ValueError(f"ho so {self.model_id}: mot_prefill_dai can "
                             f"toc_prefill_uoc_tok_s > 0")
        if not 0 <= self.bien_pool_token < TOKEN_RA_TRAN:
            raise ValueError(f"ho so {self.model_id}: bien_pool_token "
                             f"{self.bien_pool_token} ngoai [0; {TOKEN_RA_TRAN})")

    @property
    def token_budget(self) -> int:
        """Pool KV A cho phép đặt chỗ: `engine_ctx − bien_pool_token`."""
        return self.engine_ctx - self.bien_pool_token


#: 🔑 HỒ SƠ THEO **ID MODEL NỘI BỘ** — hai model, hai card, hai hồ sơ.
#:
#: Khoá là id của máy B, không phải bí danh công khai (bí danh không bao giờ rời
#: máy A — INV-015). `engine_ctx`/`np` là **số ĐO** ở đúng cấu hình triển khai:
#:
#:   * `qwen38-api` (RTX 3090) `-c` **221_184** — `docs/ltt_llm_dual/10_BENCHMARK_P3.md`
#:     §G1b, chốt ở `DECISION_LOG.md` L-14. Mốc **cao nhất còn sạch** ở `-ub` mặc
#:     định với `-np 3` + mmproj trên GPU: VRAM 24.131 MiB, `Shared` 568 (nằm
#:     trong dải sàn 526–568 ⇒ **không tràn**), biên 445 MiB. Bước lên 229.376 là
#:     `Shared` đã vượt sàn ~140 MiB. 262.144 **không vừa card** cùng mmproj.
#:     `-np 3`, KHÔNG 4: 4 slot ở ngữ cảnh đã chốt **tràn** sang RAM chủ.
#:   * `qwen35-api` (RTX 5060 Ti) `-c` **262_144** — §G3: VRAM 13.423 MiB, `Shared`
#:     354, biên 2.888 MiB ngay ở **4** slot. `-np 3` (12/09) từng là **lựa chọn**
#:     cho nhất quán hai card, không phải giới hạn phần cứng.
#:     ✅ **`-np 4` từ C4 (18/09, `DECISION_LOG.md` L-28)** — đo lại trên production
#:     (`artifacts/bench_hang_cho/KET_QUA_C4_18_09.md`): shared +6 MiB (sạch), 0 rò,
#:     0 rỗng, lặng 1,22 s và prefill 32K không đổi, tổng 147,8 → 169,9 tok/s. Mỗi
#:     luồng khi ĐỦ 4 luồng = 57,5 % đơn luồng (dưới mục tiêu 60 %) — phiên chính
#:     chấp nhận vì chỉ xảy ra khi có người thứ tư; ở np3 người đó chờ ~20 s.
#:     3.8 giữ `-np 3`: np4 tràn ở 221.184, và ở 204.800 mỗi luồng còn 48 %.
#:
#: 🔴 LÝ DO CŨ "1 slot vì speculative decoding chỉ tối ưu một luồng" ĐÃ ĐO LẠI VÀ
#:    KHÔNG ĐÚNG TRÊN 3090 (multijob M-1, 11/09) — `docs/multijob/00_BASELINE.md`.
#:
#: ⛔ Đổi `-c`/`-np` của một hồ sơ bên B thì đổi đúng hồ sơ ấy ở đây — và **chỉ**
#:    hồ sơ đó (khuyết tật F-02). `-kvu` + nhiều slot mà thiếu ngân sách KV thì
#:    một lần tràn giết MỌI slot (llama.cpp b10689).
#:
#: 🔴 PHƯƠNG ÁN C bước 2 (O-12, 17/09/2026): ĐÃ THAY `CUA_SO_THEO_MODEL` gõ tay,
#:    `SO_SLOT_MAY_B` và các bí danh `DONG_THOI_MAY_B`, `POOL_KV_MAY_B`, `SO_SLOT`,
#:    `POOL_KV` (ĐÃ GỠ). Hỏi `HO_SO[m]`.
HO_SO = {
    "qwen38-api": HoSoModel(
        "qwen38-api", engine_ctx=221_184, np=3, seq_cap=3,
        bien_pool_token=BIEN_POOL_TOKEN, dem_uoc=DEM_UOC,
        token_giu_moi_anh=TOKEN_GIU_MOI_ANH,
        nguong_whale=NGUONG_WHALE["qwen38-api"],
        toc_prefill_uoc_tok_s=toc_prefill_uoc("qwen38-api")),
    "qwen35-api": HoSoModel(
        "qwen35-api", engine_ctx=262_144, np=4, seq_cap=4,
        bien_pool_token=BIEN_POOL_TOKEN, dem_uoc=DEM_UOC,
        token_giu_moi_anh=TOKEN_GIU_MOI_ANH,
        nguong_whale=NGUONG_WHALE["qwen35-api"],
        toc_prefill_uoc_tok_s=toc_prefill_uoc("qwen35-api")),
}

#: Cửa sổ engine theo model — DẪN XUẤT từ `HO_SO`, giữ tên vì rất nhiều nơi đọc.
#: ⛔ ĐỪNG gõ số vào đây: số nằm ở `HO_SO`.
CUA_SO_THEO_MODEL = {m: h.engine_ctx for m, h in HO_SO.items()}

#: Cửa sổ ngữ cảnh của model **mặc định** — một ô của bảng trên.
#:
#: 📈 03/09: 131.072 → 204.800, kèm KV cache `q8_0` → `q4_0`. 12/09: 204.800 →
#:    **221.184** (L-14, §G1b) — cùng lúc `qwen38-vision` biến mất, vì hồ sơ mới
#:    mang mmproj trên GPU nên **một hồ sơ text+vision duy nhất** là đủ.
#:
#: 🔴 `CUA_SO_MODEL_VISION` ĐÃ ĐƯỢC GỠ (dual-model 2.6): trước 01/09 hai alias
#:    dùng chung một con số công bố, nên `/api/v1/models` hứa vision *"same 89K"*
#:    trong khi máy B chặn ở 65.536 (`413 {"tran":65536,"thay":71281}`).
CUA_SO_MODEL = CUA_SO_THEO_MODEL[MODEL_MAC_DINH]

#: Cửa sổ **hẹp nhất** trong các model đang bán. Mọi chỗ phải kẹp một con số mà
#: **chưa biết model** dùng cái này chứ không dùng cái rộng nhất: kẹp rộng hơn
#: cửa sổ thật của model đang chạy là để model tự cắt ngữ cảnh — thứ hỏng không
#: sạch và rất khó truy.
CUA_SO_HEP_NHAT = min(CUA_SO_THEO_MODEL.values())

#: Ngân sách đặt chỗ **hẹp nhất** — cùng lý lẽ với `CUA_SO_HEP_NHAT`, cho phép kẹp
#: token ra khi chưa biết model (`tran_theo_ngu_canh(vao)`).
NGAN_SACH_HEP_NHAT = min(h.token_budget for h in HO_SO.values())


# ══════════════════════════════════════════════════════════════════════════
#  DẪN XUẤT — KHÔNG GÕ TAY BẤT KỲ SỐ NÀO DƯỚI ĐÂY
# ══════════════════════════════════════════════════════════════════════════

#: Trần đầu vào thật sự dùng được **của model mặc định**: chừa đủ chỗ cho một
#: câu trả lời dài nhất. Máy B KHÔNG khai số này: cổng tự tính `-c − max_out − DEM_UOC`
#: theo từng model từ `llama-swap.yaml` (phương án C bước 3).
#: ⛔ Một con số, nên nó chỉ đúng cho MỘT model. Đường theo-model là
#:    `tran_vao_cua(model_id)` — cùng công thức, khác cửa sổ.
TOKEN_VAO_TRAN = CUA_SO_MODEL - TOKEN_RA_TRAN - DEM_UOC      # 186_368

#: 🔑 HỆ SỐ ƯỚC TRÊN THẬT — trần tiền kiểm ở A (`tran_vao_cua`, `TOKEN_VAO_TRAN`)
#: tính trên TOKEN ƯỚC (`platform_core/llm/uoc_token.py`, cận trên có chứng
#: minh); nhưng con số ta công bố cho client phải đúng ở TOKEN THẬT — client
#: đếm bằng bộ đếm của nó, model tính tiền bằng token thật của Qwen. Hai đơn vị
#: khác nhau; hằng số này là tỉ lệ đo được để quy đổi cái trước sang cái sau.
#:
#: 📏 Đo: `uoc_token_vao(A, cận trên) / usage token thật`, 1.120 lượt production
#: (`C:\lttc0\logs\he_so_uoc_that.md`, 22/09/2026). median = 1,31 · max = 1,483.
#:
#: ✅ CHỦ DỰ ÁN CHỐT 22/09/2026 (quyết định (b)): k = **1,50**, BỎ biên `× 0,92`
#:    cũ ("chừa lệch tokenizer" — sai câu hỏi: số công bố không cần chừa lệch
#:    tokenizer, nó phải KHỚP token thật; cái cần chừa là khoảng cách ước↔thật
#:    ở cửa vào của A).
#:
#: 🔴 VÌ SAO LẤY MAX (1,483 → 1,5) CHỨ KHÔNG P99: k gần như HẰNG trong một
#:    phiên (cùng ngôn ngữ, cùng hình dạng nội dung suốt một phiên chat), nên
#:    1.120 lượt gộp lại chỉ tương đương cỡ mẫu HIỆU DỤNG ~28 phiên độc lập —
#:    một p99 trên cỡ mẫu nhỏ như vậy không đáng tin, một phiên lệch có thể
#:    chiếm cả phần đuôi. `max` đo được là biên cứng quan sát trên toàn bộ
#:    1.120 lượt; 1,50 nới thêm chút cho phiên chưa thấy.
HE_SO_UOC_TREN_THAT = 1.5

#: Cửa sổ **công bố** cho client agentic (Codex, Claude Code) để chúng nén hội
#: thoại **trước** khi chạm trần — tính theo TOKEN THẬT (`/ HE_SO_UOC_TREN_THAT`),
#: trong khi `TOKEN_VAO_TRAN` (tiền kiểm ở A) tính theo TOKEN ƯỚC.
CONG_BO_CHO_CLIENT = int(TOKEN_VAO_TRAN / HE_SO_UOC_TREN_THAT)    # 124_245


# ── Ngân sách THEO MODEL ───────────────────────────────────────────────────
#
# ⭐ Hai model, hai cửa sổ, nên **hai bộ số** — và đó là toàn bộ bài học của
#    khuyết tật F-02: một con số dùng cho hai model là một con số sai cho ít
#    nhất một trong hai.
#
# ⛔ Công thức phải GIỐNG HỆT đường text ở trên (chừa `TOKEN_RA_TRAN` cho câu
#    trả lời dài nhất, chừa `DEM_UOC` cho sai số ước, rồi chia `HE_SO_UOC_TREN_THAT`
#    để quy đổi token ƯỚC ở A sang token THẬT client thấy).
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
    h = HO_SO[model_id]
    return h.engine_ctx - TOKEN_RA_TRAN - h.dem_uoc


def cong_bo_cua(model_id: str) -> int:
    """Con số ngữ cảnh **công bố cho client** của một model — quy đổi trần
    tiền kiểm (token ƯỚC ở A) sang token THẬT bằng `HE_SO_UOC_TREN_THAT`."""
    return int(tran_vao_cua(model_id) / HE_SO_UOC_TREN_THAT)


#: Số byte JSON cho mỗi token THẬT (token do provider báo, đơn vị GIỐNG
#: `cong_bo_cua` — KHÔNG phải token ƯỚC của `tran_vao_cua`) khi hội thoại đi
#: trên dây. Đo 30/08 trên thân request thật của Codex: 4,5 (đơn vị token ước
#: khi đó — xem lịch sử git; đã lỗi thời).
#:
#: 🔴 25/09/2026 — HAI LẦN SỬA SỐ TRONG CÙNG MỘT NGÀY, VÀ CẢ HAI LẦN ĐẦU ĐỀU LÀ
#:    "ĐỌC THỨ ĐẠI DIỆN THAY VÌ ĐO THỨ THẬT". Ghi lại đủ cả hai lần sai để
#:    không ai lặp cùng lớp lỗi:
#:
#:    (1) Lần đầu soi ngược thân **1.150.067 B** ăn 413 ở trần 1.048.576 B,
#:        tưởng là ca sản xuất — đó là **phép dò tổng hợp của người báo lỗi**
#:        (`'x' * 1_150_000`, không phải hội thoại thật), và "227.328 token ⇒
#:        5,059 B/token" suy từ đó **bịa mẫu số** (một triệu ký tự `x` không
#:        nguyên âm ước ra ~1 token/ký tự theo chính `uoc_token._chu`, không
#:        phải 227.328). Chọn 6,0 từ số này đã bị RÚT LẠI.
#:
#:    (2) Lần hai đọc ảnh chụp thanh đo (model đoán nhầm `ltt-3.5`, tỉ lệ suy
#:        ra ≈10,64) — nhưng ảnh chụp là READ-OUT tại một khoảnh khắc bất kỳ,
#:        không phải bản ghi. Có bản ghi phiên thật (`session-0019f199`, giải
#:        nén cẩn thận: tệp là NHIỀU KHUNG zstd nối nhau, phải đọc bằng
#:        `stream_reader(..., read_across_frames=True)` chứ không chỉ khung
#:        đầu) mới xác nhận: **165 bước**, `usage` cuối trước 413 —
#:        `totalTokens = 80.823` (cacheRead 80.395, input 350), model
#:        **ltt-3.8** (không phải 3.5 — khách đã đổi model trước khi chụp ảnh;
#:        `80.823 / 0,65 ≈ 124.343 ≈ 124.245 = cong_bo_cua("qwen38-api")` xác
#:        nhận đúng model VÀ xác nhận mẫu số thanh `%` = cửa sổ công bố).
#:
#: ⭐ SỐ DÙNG ĐỂ CHỐT: thân request **vượt** 1.048.576 B (bất đẳng thức — trần
#:    cũ là 1 MiB, "vượt" chỉ nói lớn hơn, KHÔNG phải giá trị chính xác) trên
#:    **80.823** token thật (từ `usage`, không phải ước lượng) ⇒ tỉ lệ **SÀN**
#:    (canh dưới kép: cả tử số lẫn mẫu số đều là cận dưới của giá trị thật):
#:
#:        1.048.576 / 80.823 ≈ 12,97 byte/token
#:
#:    Phiên này có **190 sự kiện `tool/result`** và khối SUY NGHĨ luôn bật
#:    (`ltt-3.8` mặc định `medium`, xem `NGHI_MAC_DINH_THEO_MODEL`) — hai thứ
#:    mẫu tự dựng của lần sửa này (tài liệu tiếng Việt + mã nguồn, xây bằng
#:    `platform_core/llm/uoc_token.py`) không tái hiện được:
#:      * hội thoại vài khối văn bản LỚN — ước median ≈ 2,65 · p90 ≈ 3,05 B/token;
#:      * phiên nhiều lượt NHỎ xen tool_use/tool_result — tới 4,35 B/token.
#:    Ca thật (12,97+) cao gấp ~3–4 lần mọi mẫu tự dựng — KHÔNG được giải thích
#:    hết bằng dữ liệu đang có (nghi khối suy nghĩ + 190 tool_result mang byte
#:    không tương ứng token theo cùng tỉ lệ với văn xuôi thường; CHƯA XÁC NHẬN
#:    cơ chế chính xác). Nói thẳng khoảng trống này thay vì lấp bằng cảm tính.
#:
#: ✅ CHỌN 16,0 = 12,97 (SÀN đo trên `session-0019f199`) × ~1,23 biên.
#:    `test_4200_tran_body_du_byte_token.py` ghim tỉ lệ SÀN (12,97) và số CHỐT
#:    (16,0) để không ai hạ lại xuống dưới sự cố đã xảy ra mà không biết.
#:
#: ⛔ VẪN CHƯA TÍNH ẢNH. Ảnh gửi kèm là base64 (~1,37× byte gốc) và
#:    `ANH_BYTE_TOI_DA` = 12 MiB/ảnh, `SO_ANH_TOI_DA` = 4 ảnh — MỘT ảnh đơn đã
#:    vượt xa mọi trần thân tính từ hằng số này. Hằng số này chỉ chừa đủ cho
#:    HỘI THOẠI CHỮ; trần thân thật ở `platform_core/public_api/config.py`
#:    cộng thêm biên riêng cho việc đó (xem chú thích ở đó).
BYTE_MOI_TOKEN_JSON = 16.0

#: Trần thân request **tối thiểu** phải cho phép, để một client hoạt động
#: ĐÚNG TRONG cửa sổ **công bố** của nó (`cong_bo_cua`, đơn vị token THẬT —
#: đúng đơn vị của `BYTE_MOI_TOKEN_JSON` và của chính sự cố 25/09) không bị
#: chặn bởi kích thước byte trước khi ai kịp đếm token.
#:
#: ⛔ ĐÂY LÀ MỘT LỚP LỖI ĐÃ XẢY RA HAI LẦN. Lần 1 (30/08): trần body 256 KB của
#:    nền tảng chặn hội thoại dài ở khoảng 64.000 token — gần bằng 65.000 nên
#:    suốt buổi ta tưởng đang chạm trần của máy B. Lần 2 (25/09): trần 1 MiB
#:    (rồi 2 MiB) vẫn mỏng hơn một phiên `ltt-3.8`/`ltt-3.5` thật đang suy
#:    nghĩ + gọi nhiều `tool_result`. Cả hai lần, hai trần không liên quan gì
#:    nhau mà cái nhỏ hơn thắng.
#:
#: ⭐ DÙNG `cong_bo_cua`, KHÔNG DÙNG `CUA_SO_THEO_MODEL`/`tran_vao_cua`. Hai
#:    cái sau là ngân sách ƯỚC dùng cho tiền kiểm NỘI BỘ ở A; câu hỏi ở đây là
#:    "một client tuân thủ đúng lời hứa TA CÔNG BỐ có gửi lọt không" — và lời
#:    hứa đó, cùng mọi số đo thật ta có (`usage.totalTokens`, thanh đo %), đều
#:    ở đơn vị token THẬT. Nhân `BYTE_MOI_TOKEN_JSON` (đo ở đơn vị thật) với
#:    một ngân sách ƯỚC (lớn hơn thật ~1,3–1,5 lần) sẽ cho một con số "an
#:    toàn hơn cần" nhưng SAI ĐƠN VỊ — và khi tài liệu (chú thích, báo cáo)
#:    dẫn một phép tính ở đơn vị thật mà hằng số lại nhân nhầm đơn vị ước, đó
#:    chính là "hai chỗ khai một điều không ai bắt khớp" — lớp lỗi này đang cố
#:    dẹp, không phải lớp lỗi nên tạo thêm.
#:
#: ⭐ TÍNH THEO MODEL **RỘNG NHẤT**, không theo model mặc định: trần body là một
#:    con số của cả cửa `/api/v1`, và một request `ltt-3.5` hợp lệ ở trần công
#:    bố của NÓ phải lọt qua. Lấy theo model mặc định (hẹp hơn) là dựng lại
#:    đúng lỗi "hai trần không biết nhau" cho model kia.
BODY_BYTES_TOI_THIEU = int(
    max(cong_bo_cua(m) for m in CUA_SO_THEO_MODEL) * BYTE_MOI_TOKEN_JSON)


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
       Hai model hôm nay đều rộng nên cả hai trả số dương; nhánh 0 vẫn phải sống,
       và lý do là **hình dạng** chứ không phải danh sách model: hàm này là hàm
       của một **hiệu số**, không của một cái tên. Xoá một nhánh vì "hiện không
       ai chạm" là đổi một bất biến lấy một sự trùng hợp.
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
    # 🔴 NÂNG 4.096 → `TOKEN_RA_TRAN` ngày 14/09/2026, chủ dự án chốt.
    #
    #    Chú thích cũ ở đây giữ 4.096 với lý do: *"cửa job chưa từng dính lỗi
    #    30/08 — lỗi đó chỉ ở cửa stream — nên không có lý do gì đổi thứ khách
    #    đang thấy."* Lý lẽ ấy **bảo vệ hiện trạng chứ không bảo vệ khách**:
    #    "chưa dính" không phải "không dính được", và cơ chế gây ra lỗi 30/08
    #    (một trần ẩn **dưới** trần đã công bố, model bị cắt giữa chừng, khách
    #    thấy "chạy xong mà không có gì") **có đủ ở cửa job y hệt**.
    #
    #    Cái cửa job KHÔNG có là lý do để đặt thấp: nó chạy nền, không có đồng
    #    hồ 100 giây của Cloudflare như cửa `sync`. Nên 4.096 ở đây là tàn dư,
    #    không phải ràng buộc.
    #
    # ⭐ Nhà sản xuất khuyến nghị **32.768 token ra cho hầu hết truy vấn**
    #    (model card, mục Best Practices) — đúng bằng `TOKEN_RA_TRAN`.
    #
    # ⛔ Và nâng KHÔNG đội giá: credit giữ trước rồi **hoàn** theo token thật
    #    sinh ra. Giữ cho 32.768 token là **13,1 credit** (đo, ở giá 400
    #    credit/1M) — 1 % số dư một tài khoản thường. Đây đúng là phép tính đã
    #    bác bỏ nỗi lo "ví mỏng bị từ chối oan" khi sửa cửa stream.
    #
    # ⚠️ Đây LÀ một thay đổi hợp đồng (`input_schema...max_tokens.default` khách
    #    đọc qua `/api/v1/tools`), nên nó đi kèm `tests/golden/` sinh lại và một
    #    mục CHANGELOG — đúng như chú thích cũ đòi hỏi.
    "job": TOKEN_RA_TRAN,
}

# ══════════════════════════════════════════════════════════════════════════
#  SÀN token ra theo MỨC SUY NGHĨ — L-02, 13/09/2026
# ══════════════════════════════════════════════════════════════════════════
#
# 🔴 VÌ SAO CẦN SÀN, VÀ VÌ SAO NÓ THEO **MỨC SUY NGHĨ** CHỨ KHÔNG PHẢI MỘT SỐ.
#
#    Model nhà suy nghĩ trước khi trả lời. Suy nghĩ tiêu **chính** ngân sách
#    `max_tokens` của lượt đó. Đặt trần thấp thì model tiêu hết trần vào suy
#    nghĩ, bị cắt (`finish_reason=length`), và khách nhận `content` **rỗng** —
#    nhưng GPU đã chạy thật nên **vẫn tính tiền** (đo: `mcredit_du` +4).
#
# 📏 Đo 13/09 trên đường thật, `ltt-3.5`, câu hỏi một dòng, 3-5 lượt mỗi ô:
#
#      effort    token ra (đủ chỗ)   max_tokens sạch 5/5
#      none              4                   32
#      low             206                  300
#      medium          377                  600
#      xhigh           421                  600+
#
#    ⇒ Ba mức tiêu **khác nhau rõ rệt**, nên một sàn chung sẽ hoặc quá chặt với
#      `none` (từ chối oan) hoặc quá lỏng với `xhigh` (không chặn được gì).
#
# ⛔ SÀN NÀY KHÔNG PHẢI MỘT BẢO ĐẢM. Nó chặn *"trần thấp một cách hiển nhiên"*,
#    không chặn được mọi lượt rỗng: một câu hỏi **khó** tiêu nhiều token suy nghĩ
#    hơn hẳn câu một dòng dùng để đo. Nhà sản xuất khuyến nghị **32.768** token
#    ra cho hầu hết truy vấn — sàn ở đây chỉ là mức tối thiểu để lượt gọi có cơ
#    hội trả lời, không phải mức nên dùng.
#
# 🔴 ĐÃ GỠ 18/09/2026 (L-26): "đường thoát `reasoning_effort="none"` hạ sàn
#    xuống 64". `none` bị từ chối từ 14/09 (tắt suy nghĩ hỏng chất lượng: 2
#    token thay vì ~1.180), nên dòng `none` của bảng sàn là một lời hứa chết.
#    Hàng `none` trong bảng đo ngay trên giữ lại vì nó là SỐ ĐO lịch sử.
#
# 🔴 SÀN 3.5 = BUDGET SUY NGHĨ ENGINE + CHỖ TRẢ LỜI (L-26, chủ dự án 18/09).
#    3.5 chỉ có MỘT chế độ, suy nghĩ BẬT; effort khách gửi bị gỡ trước máy B
#    (`runtime_noi_bo.luong.chuan_hoa_suy_nghi`), nên suy nghĩ tiêu tới
#    `--reasoning-budget` của hồ sơ `qwen35-api` trong `llama-swap.yaml` ở MỌI
#    mức. Sàn thấp hơn budget + 512 là cho phép một lượt tiêu hết trần vào suy
#    nghĩ rồi trả `content` rỗng mà vẫn thu tiền (R-20 của phiên Serving v2:
#    "MTP trả rỗng" thực ra là hết `max_tokens`). `test_1430` đọc budget từ
#    yaml và chốt `san_token_ra("ltt-3.5", *) >= budget + 512`.
#
# ⭐ Cửa ĐỒNG BỘ `/chat/completions` (mặc định 1.024 token ra, trần thời gian
#    ~2.300) KHÔNG dùng sàn này cho 3.5: máy chủ tự đặt `reasoning_budget_tokens`
#    của lượt = `max_tokens − TOKEN_CHO_TRA_LOI` (kẹp ≤ budget engine) — xem
#    `budget_suy_nghi_dong_bo`, `san_token_ra_dong_bo`. Vẫn là "máy chủ quyết
#    budget" (L-26); chỉ budget KHÁCH gửi bị gỡ.
#: ⛔ SÀN THEO **MODEL × MỨC**, không phải một bảng chung — và lý do là một
#: phép đo, không phải sự cẩn thận:
#:
#:      cùng một câu hỏi một dòng, `max_tokens` = 1500
#:        ltt-3.5   none 4 · low 206 · medium 377 · xhigh 421
#:        ltt-3.8   none 4 · low  63 · medium  63 · xhigh  55
#:
#:    Hai model tiêu khác nhau **6 lần**. Một bảng chung sẽ lấy số của model
#:    tốn nhất và **phạt oan** model kia: `ltt-3.8` trả lời ĐÚNG ở
#:    `max_tokens=100` với `low`, mà một sàn 512 sẽ từ chối lượt hợp lệ ấy.
#:
#: ⛔ HAI QUY TẮC ĐẶT SÀN, và chúng KHÁC nhau có chủ ý:
#:
#:    model ĐÃ THẤY hỏng  -> sàn = đo được x ~2 (câu đo là câu MỘT DÒNG; câu khó
#:                           suy nghĩ nhiều hơn, nên biên là phần trả cho chênh
#:                           lệch ấy)
#:    model CHƯA thấy hỏng -> sàn = đúng số ĐO ĐƯỢC, làm tròn lên. KHÔNG nhân
#:                           biên.
#:
#: 🔴 Vì sao không nhân biên cho model chưa hỏng: biên ở đây không miễn phí, nó
#:    **từ chối lượt hợp lệ**. `ltt-3.8` sinh 63 token cho câu một dòng và trả
#:    lời ĐÚNG ở `max_tokens=100`; một sàn 256 "cho chắc" biến lượt ấy thành
#:    400. Đó đúng là hình dạng lỗi đã ghi: *một cái phanh đặt dưới nhu cầu
#:    thật còn tệ hơn không có phanh*. Biên chỉ được trả bằng lượt hợp lệ khi
#:    ta ĐÃ thấy thiệt hại nó ngăn.
_SAN_NHE = {"low": 64, "medium": 64, "xhigh": 64}

#: `--reasoning-budget` của hồ sơ `qwen35-api` trong `llm_gateway/deploy/
#: llama-swap.yaml`. Bản sao CÓ ĐỐI CHIẾU: `test_1430` đọc yaml và chốt sàn
#: dưới đây ≥ budget + `TOKEN_CHO_TRA_LOI` — đổi budget bên B mà quên ở đây thì đỏ.
BUDGET_SUY_NGHI_35 = 2_048
#: Chỗ tối thiểu cho câu trả lời sau khi suy nghĩ dùng hết budget (L-26).
TOKEN_CHO_TRA_LOI = 512
_SAN_35 = BUDGET_SUY_NGHI_35 + TOKEN_CHO_TRA_LOI

SAN_TOKEN_RA_THEO_NGHI = {
    # 3.5: một chế độ, suy nghĩ BẬT tới hết budget engine ⇒ một sàn cho mọi mức
    # (effort bị gỡ trước máy B). Số đo 13/09 cũ (low 512 / medium 1024) thấp
    # hơn budget 2.048 ⇒ lượt khó vẫn rỗng; thay bằng budget + chỗ trả lời.
    "ltt-3.5": {"low": _SAN_35, "medium": _SAN_35, "xhigh": _SAN_35},
    # Đo 13/09: 63 token ở MỌI mức, đúng ngay ở max_tokens=100 — chưa từng
    # thấy trả rỗng, nên lấy sàn "đo được", không nhân biên.
    "ltt-3.8": dict(_SAN_NHE),
}

#: Mức thực tế khi khách không khai `reasoning_effort` (Q131). Đây là thuộc
#: tính theo MODEL; 3.5 chỉ công bố thinking on/off, template v22.5 dùng medium
#: khi thinking bật.
#: ⭐ L-33 (chủ dự án chốt 19/09 tối): 3.8 mặc định `medium` trên TOÀN nền tảng
#:    (đảo mức mặc định của L-26; `xhigh` vẫn chọn được). Đo LTTCODE lượt lập
#:    plan: xhigh 94-99 s, medium 49-81 s, token ra ~1/2. Máy chủ CHÈN mức này
#:    khi request bỏ trống (`runtime_noi_bo.luong.chuan_hoa_suy_nghi`) — không
#:    còn dựa vào `--reasoning-effort xhigh` của máy B. Bản sao CÓ ĐỐI CHIẾU:
#:    `examples.CODEX_MODEL_REASONING` (catalog + luong đọc) — `test_1430` buộc bằng nhau.
NGHI_MAC_DINH_THEO_MODEL = {
    "ltt-3.8": "medium",
    "ltt-3.5": "medium",
}


def nghi_mac_dinh(model: str | None = None) -> str:
    """Mức dùng để tính admission khi request không gửi effort."""
    return NGHI_MAC_DINH_THEO_MODEL.get(str(model or ""), "xhigh")


def san_token_ra(model: str | None = None, muc_nghi: str | None = None) -> int:
    """Sàn `max_tokens` cho (model, mức suy nghĩ).

    ⛔ Không ném với model hay mức lạ: `features.kiem_tham_so` đã chặn cả hai
       enum trước khi tới đây, nên một `KeyError` ở đây chỉ có thể là lỗi nội
       bộ — và nó sẽ thành 500 cho một lượt lẽ ra chỉ cần 400.

    ⭐ Model chưa có trong bảng lấy `_SAN_NHE`: một model mới thêm vào **không**
       thừa hưởng hình phạt của model tốn nhất, cho tới khi ai đó đo nó.
    """
    bang = SAN_TOKEN_RA_THEO_NGHI.get(str(model or ""), _SAN_NHE)
    mac_dinh = nghi_mac_dinh(model)
    return bang.get(str(muc_nghi or mac_dinh), bang.get(mac_dinh, bang["xhigh"]))


#: Budget suy nghĩ ENGINE theo bí danh, cho model MỘT chế độ (effort bị gỡ nên
#: budget là núm duy nhất). Model có nấc (3.8) ở `BUDGET_SUY_NGHI_THEO_MUC`.
BUDGET_SUY_NGHI_ENGINE = {"ltt-3.5": BUDGET_SUY_NGHI_35}

#: `--reasoning-budget` của hồ sơ `qwen38-api` (`llama-swap.yaml`). Bản sao CÓ
#: ĐỐI CHIẾU: `test_1430` đọc yaml và chốt mức `xhigh` bằng số này.
BUDGET_SUY_NGHI_38 = 4_096

#: ⭐ L-32 (chủ dự án duyệt 19/09): NẤC EFFORT 3.8 THẬT = budget suy nghĩ MÁY CHỦ
#: đặt theo mức. Đo T1c (18-19/09, engine B, n=5): effort của template v22.5 chỉ
#: là MỘT câu ở đầu system prompt — độ dài suy nghĩ KHÔNG theo mức (median token
#: ra low/xhigh: 4.695/4.855 bài lát domino, 385/245 bài tàu hoả). Nên mỗi mức
#: mang thêm một trần suy nghĩ; câu effort của template vẫn gửi (định hướng).
#: `xhigh` = budget engine. Mức mặc định từ L-33 là `medium` (2.048).
BUDGET_SUY_NGHI_THEO_MUC = {
    "ltt-3.8": {"low": 1_024, "medium": 2_048, "xhigh": BUDGET_SUY_NGHI_38},
}
#: Suy nghĩ tối thiểu cửa đồng bộ còn chừa khi tự đặt budget — bằng chỗ trả
#: lời, nên sàn đồng bộ = 2 × `TOKEN_CHO_TRA_LOI` ≤ mặc định 1.024 của cửa.
SUY_NGHI_DONG_BO_TOI_THIEU = TOKEN_CHO_TRA_LOI


def budget_suy_nghi_dong_bo(model: str | None, max_tokens: int,
                            muc_nghi: str | None = None) -> int | None:
    """`reasoning_budget_tokens` MÁY CHỦ đặt cho một lượt cửa đồng bộ, hoặc None.

    Cửa đồng bộ bị kẹp `max_tokens` (thời gian ~90 s, `features.
    tran_token_ra_dong_bo` dẫn từ tốc độ decode đo) — thấp hơn budget engine +
    chỗ trả lời. Để suy nghĩ tiêu hết `max_tokens` là trả `content` rỗng mà vẫn
    thu tiền. Nên máy chủ chia: suy nghĩ = `max_tokens − TOKEN_CHO_TRA_LOI`, kẹp
    ≤ budget engine. llama.cpp nhận trường này MỖI request (91f6a6cf3
    `server-common.cpp:1366-1369`). None ⇒ model không có trong hai bảng.

    Model có nấc (3.8, L-32): trần = `BUDGET_SUY_NGHI_THEO_MUC[model][muc_nghi]`;
    `muc_nghi` là mức ĐÃ chuẩn hoá (`luong.chuan_hoa_suy_nghi`), None ⇒ mức mặc
    định của model. Model một chế độ (3.5): `muc_nghi` bị bỏ qua.

    🔴 Dùng ở MỌI cửa, không chỉ cửa đồng bộ (sự cố 18/09 22:45): `features.chay`
       tự gọi khi bên gọi không truyền (`/messages`/`/responses` không stream, job),
       cửa stream gọi qua `runtime_noi_bo.luong._dat_budget_may_chu`. Trần lớn
       ⇒ trả đúng budget engine, tức không đổi hành vi.
    ⚠️ `max_tokens` ≤ 512 ⇒ 0 = kết thúc suy nghĩ ngay (llama.cpp `--reasoning-budget`
       "0 for immediate end"): chỗ trả lời được ưu tiên hơn suy nghĩ.
    """
    ten = str(model or "")
    tran = BUDGET_SUY_NGHI_ENGINE.get(ten)
    if tran is None:
        bang = BUDGET_SUY_NGHI_THEO_MUC.get(ten)
        if bang is None:
            return None
        mac_dinh = nghi_mac_dinh(ten)
        tran = bang.get(str(muc_nghi or mac_dinh), bang[mac_dinh])
    return max(0, min(tran, int(max_tokens) - TOKEN_CHO_TRA_LOI))


def san_token_ra_dong_bo(model: str | None = None, muc_nghi: str | None = None) -> int:
    """Sàn `max_tokens` ở cửa ĐỒNG BỘ. Model một chế độ: đủ chỗ cho
    `SUY_NGHI_DONG_BO_TOI_THIEU` + `TOKEN_CHO_TRA_LOI` (budget do máy chủ đặt);
    model khác: đúng `san_token_ra`."""
    if str(model or "") in BUDGET_SUY_NGHI_ENGINE:
        return SUY_NGHI_DONG_BO_TOI_THIEU + TOKEN_CHO_TRA_LOI
    return san_token_ra(model, muc_nghi)


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

#: ⭐ Phép ước token vào (CẬN TRÊN có chứng minh, Task 7 18/09/2026) sống ở
#:    `platform_core/llm/uoc_token.py` — bản giống hệt từng byte của
#:    `llm_gateway/uoc_token.py` máy B (test_1470). `apps/ltt_llm/features.uoc_token_vao`
#:    là cửa duy nhất của app gọi nó.
#:
#: 🔴 ĐÃ GỠ `KY_TU_MOI_TOKEN = 2.5` (ký tự / 2,5): đo trên engine nó ước THIẾU code
#:    0,74× · chữ Trung 0,42× · hex 0,45× · emoji 0,16× (giữ chỗ nhỏ hơn thật ⇒ tràn
#:    KV giết luồng SAU 200) và THỪA văn xuôi Anh 2,25×.


# ══════════════════════════════════════════════════════════════════════════
#  SỨC CHỨA THEO MODEL — dẫn xuất từ `HO_SO`
# ══════════════════════════════════════════════════════════════════════════
#
# 🔑 Hai model công khai chạy trên **hai card khác nhau** của máy B, nên mỗi cái
#    có pool KV và số slot riêng. Bản khai admission ở `manifest.py` đọc `HO_SO`
#    — **đừng gõ số vào manifest** (test_1201 chốt điều đó).
#
# 🔴 ĐÃ GỠ 17/09/2026 (phương án C bước 2, O-12): `SO_SLOT_MAY_B` (một số cho
#    HAI card), bí danh `DONG_THOI_MAY_B`, `SO_SLOT`, `POOL_KV`, `POOL_KV_MAY_B`.
#    Số slot là `HO_SO[m].np` (engine) / `HO_SO[m].seq_cap` (chính sách A).

#: Ngân sách KV A cho phép đặt chỗ của `ltt-3.8` (3090) và `ltt-3.5` (5060 Ti).
POOL_38 = HO_SO["qwen38-api"].token_budget
POOL_35 = HO_SO["qwen35-api"].token_budget

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
    # 🔴 PHƯƠNG ÁN C bước 2: chỗ còn lại tính trên NGÂN SÁCH ĐẶT CHỖ
    #    (`token_budget` = `-c` − biên), không trên `-c` trần. Đặt chỗ của lượt là
    #    `vào + ra + đệm`; kẹp `ra` theo `-c` thì lượt vào dài nhất đặt chỗ VƯỢT
    #    ngân sách và `luat_cho` ném `DatChoVuotPool` — một 413 cho lượt đã qua
    #    trần vào. Kẹp theo ngân sách giữ bất biến `vào ≤ tran_vao ⇒ đặt chỗ ≤ pool`.
    ngan_sach = (NGAN_SACH_HEP_NHAT if model_id is None
                 else HO_SO[model_id].token_budget)
    dem = DEM_UOC if model_id is None else HO_SO[model_id].dem_uoc
    con_lai = ngan_sach - int(token_vao_uoc or 0) - dem
    return max(1, min(TOKEN_RA_TRAN, con_lai))
