"""
config.py — mọi tham số vận hành đọc từ biến môi trường, không hằng số nằm rải rác.

⛔ Không dùng `Path(__file__).parents[n]` để neo đường dẫn: đếm sai cấp thư mục
   ngay khi file đổi chỗ, và hỏng lặng lẽ (`AGENTS.md`).

⛔ FAIL-CLOSED như Q92: `LTT_LLM_MODELS` mặc định **rỗng**. Bật cờ một mình
   **không** mở model nào. Đây không phải sự cẩn thận thừa — Public API đã chốt
   nguyên tắc này và nó đã cứu một lần deploy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(ten: str, mac_dinh: int) -> int:
    try:
        return int((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return mac_dinh


def _float(ten: str, mac_dinh: float) -> float:
    try:
        return float((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return mac_dinh


def _danh_sach(ten: str) -> tuple[str, ...]:
    """Đọc danh sách phân tách bằng dấu phẩy. Rỗng → tuple rỗng (fail-closed)."""
    tho = (os.environ.get(ten) or "").strip()
    if not tho:
        return ()
    return tuple(x.strip() for x in tho.split(",") if x.strip())


@dataclass(frozen=True)
class Config:
    # ── Thượng nguồn: llama-swap ─────────────────────────────────────────────
    #: llama-swap nghe loopback. KHÔNG bao giờ trỏ ra LAN.
    upstream_url: str

    # ── Cổng VLM ─────────────────────────────────────────────────────────────
    host: str
    port: int
    token: str

    # ── Danh mục ─────────────────────────────────────────────────────────────
    #: Tên model được phép phục vụ. **Rỗng = không mở gì cả** (Q92 fail-closed).
    models_mo: tuple[str, ...]

    # ── Ngân sách ────────────────────────────────────────────────────────────
    #: Trần token đầu vào public API.
    #:
    #: ⛔ ĐỪNG GÕ LẠI CON SỐ VÀO CHÚ THÍCH NÀY. Giá trị mặc định nằm ở
    #:    `from_env()` bên dưới và nó là **bản sao dẫn xuất** của
    #:    `apps/ltt_llm/ngan_sach.py::TOKEN_VAO_TRAN`; muốn biết số hôm nay thì
    #:    đọc ở đó, hoặc hỏi máy B bằng `GET /health` → `tran.input_tokens`.
    #:
    #: 🔴 CHỖ NÀY TỪNG GHI *"Engine có cửa sổ 131.072; public giữ 65.000 theo
    #:    Q116"*. Cả ba mệnh đề đều đã hết đúng: engine lên 204.800 ngày 03/09,
    #:    trần public thành số **dẫn xuất** chứ không còn gõ tay, và Q116 đã bị
    #:    Q120 thay (`tests/test_604_q120_tran_ngu_canh_mot_nguon.py`).
    #:
    #: ⭐ Nó sai **không phải vì người viết cẩu thả** — nó đúng vào ngày viết rồi
    #:    hết đúng, y như chú thích `qwen38-ops` ở `catalog.py`. Một chú thích
    #:    chép lại giá trị sẽ trôi mỗi lần giá trị đổi; một chú thích chỉ *tên
    #:    nguồn* thì không bao giờ trôi. Đó là lý do đoạn trên nói tên chứ không
    #:    nói số.
    max_input_tokens: int
    #: Trần token sinh ra mỗi yêu cầu.
    max_output_tokens: int
    #: Trần số ảnh mỗi yêu cầu. Mỗi ảnh nuốt hàng nghìn token ngữ cảnh.
    max_images: int
    #: Trần byte của một ảnh gửi kèm (base64 đã giải mã).
    max_image_bytes: int

    # ── Thời gian ────────────────────────────────────────────────────────────
    #: Chờ llama-swap nạp model. Nạp một GGUF 15 GiB từ page cache mất vài giây,
    #: từ đĩa lạnh lâu hơn. llama-swap có `healthCheckTimeout` riêng của nó.
    upstream_timeout_s: float
    #: Chờ token đầu tiên khi ngữ cảnh dài. Ở 200K, prefill có thể mất VÀI PHÚT
    #: (cộng đồng đo prefill ~1.000 tok/s ở đầu vào 100k). Đừng đặt thấp.
    stream_timeout_s: float

    # ── Trọng tài GPU ────────────────────────────────────────────────────────
    #: Ngưỡng RAM trống tối thiểu. LẤY TỪ SỰ CỐ THẬT của dự án video máy B:
    #: còn ~23 GB thì VRAM bị đẩy lên 98 %, còn ~4 GB thì Windows sập (19/08).
    #: Là LƯỢNG TUYỆT ĐỐI, không phải tỉ lệ — tỉ lệ đổi nghĩa mỗi lần nâng RAM.
    ram_trong_toi_thieu_gb: float
    #: Bật trọng tài. Tắt (0) chỉ dùng khi test trên máy không có GPU.
    trong_tai_bat: bool

    # ── Ngưỡng "card đã sạch" cho lệnh residency (5.4b) ──────────────────────
    #: VRAM đang dùng trên 3090 phải **xuống dưới** mức này thì `POST
    #: /v1/residency/nap` mới nạp; trên nó ⇒ 409 kèm số đo.
    #:
    #: Nền đo được: desktop 1.515–1.612 MiB · ComfyUI thường trú 6.211–16.620 MiB.
    #: 2.500 nằm gọn giữa hai vùng.
    #:
    #: ⛔ MỘT NGƯỠNG, HAI ĐẦU DÂY. Máy A khai cùng con số ở
    #:    `platform_core/llm/residency.ThamSoResidency.vram_sach_mib`, và
    #:    `tests/test_1218_gateway_residency.py` chốt hai bên bằng nhau: lệch
    #:    nhau thì máy A phát lệnh nạp mà máy B từ chối, mãi mãi, im lặng.
    #:
    #: ⚠️ `comfy_url`/`don_dep_bat` ĐÃ ĐI CÙNG `don_dep.py` (5.4b): cổng LLM
    #:    không còn đường nào chạm ComfyUI — việc ấy là của trọng tài residency ở
    #:    máy A qua `POST /v1/nha_comfy` của cổng render (D01 B, TD-D10).
    vram_sach_mb: int

    # ── Hàng rào của riêng cổng (V9) ─────────────────────────────────────────
    #: Số lượt được chạy CÙNG LÚC. `llama-server` chạy `--parallel 1`, nên nhiều
    #: hơn 1 chỉ thành kết nối treo và một hàng đợi vô hình trong llama.cpp.
    #: Hàng đợi thật phải sống ở admission plane, có trạng thái/fairness/hủy;
    #: gateway này chỉ cho đúng một lượt chạm vào engine.
    max_dong_thoi: int
    #: Trần lượt mỗi phút. 0 = tắt. Chốt phụ — đồng thời mới là chốt chính.
    rpm: int

    # ── Nhịp tim SSE ─────────────────────────────────────────────────────────
    #: Chèn một dòng chú thích SSE mỗi khi luồng lặng quá số giây này. 0 = tắt.
    #:
    #: 🔴 KHÔNG TẮT KHI CÓ CODEX HAY CLAUDE CODE CẮM VÀO. Cả hai bỏ luồng sau
    #:    **300 giây im lặng**, mà `llama-server` không phát gì trong lúc prefill
    #:    — và prompt hệ thống của một CLI agent là ~22.000 token. Xem `nhip_tim`.
    nhip_tim_giay: float

    # ── Sổ theo model (Dual-model 4.2) ───────────────────────────────────────
    #
    # ⛔ BA TRƯỜNG DƯỚI ĐÂY CÓ MẶC ĐỊNH, ĐỪNG BỎ MẶC ĐỊNH ĐI. Không phải vì tiện:
    #    `Config` được dựng bằng tay ở nhiều bộ test (`Config(**mac_dinh)`), và
    #    một trường bắt buộc mới làm mọi bộ đó vỡ cùng lúc vì một lý do không liên
    #    quan đến thứ chúng đo.

    #: Trần đồng thời **riêng cho từng model**, ghi đè `max_dong_thoi`.
    #: `LTT_LLM_MAX_DONG_THOI__<model>`. Trống = mọi model dùng số chung.
    #:
    #: ⭐ Tồn tại vì hai card **không buộc bằng nhau**: §G3 đo 5060 Ti thừa sức 4
    #:    slot ở ngữ cảnh đầy, còn 3090 chỉ vừa 3 (L-14). Hôm nay chủ dự án chọn
    #:    3 cho cả hai "cho nhất quán", nên map này thường **rỗng** — nó là chỗ
    #:    đổi một con số khi muốn, không phải một con số thứ hai.
    dong_thoi_rieng: dict = field(default_factory=dict)

    #: Bể KV **theo model**, tính bằng token. `LTT_LLM_TOKEN_POOL` (chung) và
    #: `LTT_LLM_TOKEN_POOL__<model>` (riêng) ghi đè; mặc định **dẫn xuất từ
    #: `catalog.HO_SO[*].max_context`**.
    #:
    #: 🔴 DẪN XUẤT, KHÔNG GÕ. Với `-kvu` thì bể KV **chính là** `-c` của hồ sơ, và
    #:    `catalog` đã khai `-c` (và `test_334` đã buộc nó khớp `llama-swap.yaml`).
    #:    Gõ một con số thứ hai vào đây là mở lại đúng cái khe đã nói sai năm lần
    #:    ở dự án này — và lần này nó sai theo chiều nguy hiểm: bể của 3090 nhỏ
    #:    hơn bể của 5060 Ti **40.960 token**, nên một con số chung sẽ để 3090
    #:    nhận quá tay, KV cạn, và llama.cpp huỷ **mọi** slot.
    token_pool_rieng: dict = field(default_factory=dict)

    #: Sàn VRAM trống theo model, MiB: `LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__<model>`.
    #: Dưới sàn ⇒ **429 bận**, không nhận lượt mới (không giết lượt đang chạy).
    #:
    #: ⭐ MẶC ĐỊNH **600** CHO `qwen35-api` — CHỦ DỰ ÁN QUYẾT dải, xem
    #:    `docs/ltt_llm_dual/DECISION_LOG.md` **L-18** (dải được phép 600–700).
    #:    ⛔ Đừng chép lý lẽ của con số sang đây; đọc L-18. Ghi lại ở hai chỗ là
    #:       đúng cơ chế đã nói sai năm lần trong dự án này.
    #:
    #:    🔴 VÀ CON SỐ ĐÚNG LÀ SỐ **LÚC BẬN**, KHÔNG PHẢI SỐ LÚC RẢNH. Đo lại
    #:    12/09 trên chính 5060 Ti, đúng cấu hình đã chốt (§G6):
    #:
    #:        nạp xong, rảnh    15.309 / 16.311 MiB   → trống **1.002**
    #:        đỉnh C1           15.425                → trống   886
    #:        đỉnh ảnh + C3     15.555                → trống   **756**
    #:
    #:    Cửa này chạy **trước mọi lượt**, kể cả lượt thứ ba lúc hai lượt kia đang
    #:    chạy — tức nó đọc **756**, không đọc 1.002. Một sàn 700 chỉ cách đỉnh
    #:    đó **56 MiB**: một lát cắt nhỉnh hơn một chút là một **429 giả**, và khách
    #:    không phân biệt được "bận thật" với "thước đo quá sát".
    #:
    #:    ⇒ **600** — vẫn trong dải chủ dự án cho phép, để lại **156 MiB** trước khi
    #:    cổng đóng. Nó vẫn bắt được điều nó sinh ra để bắt (một tiến trình lạ
    #:    ăn card) mà không tự bắn vào chân ở tải đỉnh bình thường.
    #:
    #: ⚠️ Cửa này chỉ gây **429 bận**, không bao giờ giết một lượt đang chạy —
    #:    nên đặt cao thì mất một ít thông lượng, đặt thấp thì trả bằng OOM. Đó là
    #:    lý do dải này được chọn rộng tay. Nhưng "cao" phải cao so với **đỉnh**,
    #:    không phải so với lúc rảnh — xem §G6 ở trên. Điều còn phải theo dõi: §G3b ghi một phiên
    #:    RDP đang vẽ từng chiếm ~193 MiB, tức dải dư 300 MiB hẹp lại khi chủ dự án
    #:    điều khiển máy B trực tiếp. Thấy `ban_vram` tăng mà card vẫn rảnh thì đó
    #:    là chỗ phải đo, không phải chỗ để tự hạ sàn.
    #:
    #: ⛔ `qwen38-api` KHÔNG có sàn ở đây. Không phải bỏ quên: cuộc tranh trên
    #:    3090 do **trọng tài residency ở máy A** phân xử (D01 B), và chốt VRAM
    #:    của nó là `vram_sach_mb` ở trên, áp một lần tại `POST
    #:    /v1/residency/nap`. Thêm một cái sàn thứ hai cho cùng một card là hai
    #:    chốt nói hai thứ khác nhau về một trạng thái.
    vram_trong_toi_thieu_mb: dict = field(default_factory=dict)

    @staticmethod
    def from_env() -> "Config":
        return Config(
            upstream_url=(os.environ.get("LTT_LLM_UPSTREAM_URL")
                          or "http://127.0.0.1:8280").rstrip("/"),
            host=os.environ.get("LTT_LLM_HOST") or "127.0.0.1",
            port=_int("LTT_LLM_PORT", 8299),
            token=(os.environ.get("LTT_LLM_TOKEN") or "").strip(),
            models_mo=_danh_sach("LTT_LLM_MODELS"),
            # 🔴 NGUỒN CHÂN LÝ là `apps/ltt_llm/ngan_sach.py::TOKEN_VAO_TRAN`
            #    (= CUA_SO_MODEL − TOKEN_RA_TRAN − LE = 221184 − 32768 − 2048).
            #    Kho này deploy sang máy B nên **không import được** từ đó; số ở
            #    đây là bản sao, và hai phép kiểm đỏ ngay khi hai bên lệch:
            #    `tests/test_334_ngan_sach_ltt_llm.py` và
            #    `tests/test_250_llm_gateway.py`.
            #
            # ⛔ CHÚ THÍCH NÀY TỪNG GHI `tests/test_312`, VÀ ĐÓ LÀ MỘT LỜI HỨA
            #    TRỎ NHẦM CHỖ. `tests/test_312_vps_khoa_dich_vu.py` là khoá dịch
            #    vụ VPS — hai phiên từng cấp trùng số hiệu ấy
            #    (`docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md` §559 đã ghi nhận,
            #    nhưng bản vá lúc đó chỉ sửa tài liệu, bỏ quên chú thích này).
            #
            # ⭐ Nên từ nay **viện dẫn bằng TÊN TỆP, không bằng số hiệu**: số
            #    hiệu test là thứ hai phiên có thể cùng cấp phát, tên tệp thì
            #    không. `tests/test_980_vien_dan_phep_kiem.py` cưỡng chế điều này.
            #    ⛔ 65.000 cũ là con số gõ tay không dẫn xuất từ đâu, và nó đã
            #       khiến ta phí 25% cửa sổ model suốt nhiều ngày.
            max_input_tokens=_int("LTT_LLM_MAX_INPUT_TOKENS", 186_368),
            max_output_tokens=_int("LTT_LLM_MAX_OUTPUT_TOKENS", 32_768),
            max_images=_int("LTT_LLM_MAX_IMAGES", 4),
            max_image_bytes=_int("LTT_LLM_MAX_IMAGE_BYTES", 12 * 1024 * 1024),
            upstream_timeout_s=_float("LTT_LLM_UPSTREAM_TIMEOUT_S", 600.0),
            stream_timeout_s=_float("LTT_LLM_STREAM_TIMEOUT_S", 900.0),
            ram_trong_toi_thieu_gb=_float("LTT_LLM_RAM_TRONG_GB", 48.0),
            trong_tai_bat=(os.environ.get("LTT_LLM_TRONG_TAI") or "1").strip() != "0",
            vram_sach_mb=_int("LTT_LLM_VRAM_SACH_MB", 2500),
            # 📈 12/09: 1 -> 3, khop `ngan_sach.SO_SLOT_MAY_B` (L-14 §G1b).
            #    ⛔ `deploy.ps1` VAN ghim 1 vao gateway.env cho toi Task 4.1, va
            #       do la co y: llama-swap con chay `--parallel 1` cho toi khi
            #       Task 3.3 thay yaml. Mac dinh nay chi co hieu luc khi
            #       gateway.env khong khai - `tests/test_1201` doi chieu no.
            max_dong_thoi=_int("LTT_LLM_MAX_DONG_THOI", 3),
            rpm=_int("LTT_LLM_RPM", 120),
            nhip_tim_giay=_float("LTT_LLM_NHIP_TIM_S", 15.0),
            dong_thoi_rieng=_theo_model("LTT_LLM_MAX_DONG_THOI__"),
            token_pool_rieng=_pool_theo_model(),
            vram_trong_toi_thieu_mb=_san_vram(),
        )


def _theo_model(tien_to: str) -> dict:
    """Mọi biến `<tien_to><model>` thành `{model: int}`.

    ⛔ TÊN MODEL LẤY TỪ CHÍNH BIẾN MÔI TRƯỜNG, không từ một danh sách cứng: một
       hồ sơ mới thêm vào `catalog` phải cấu hình được **ngay**, không phải sau
       khi ai đó nhớ ra còn một danh sách nữa cần sửa.
    """
    ra: dict = {}
    for ten, gt in os.environ.items():
        model = _duoi_ten_model(ten, tien_to)
        if model is None:
            continue
        try:
            so = int((gt or "").strip())
        except ValueError:
            continue
        if so > 0:
            ra[model] = so
    return ra


def _duoi_ten_model(ten_bien: str, tien_to: str) -> "str | None":
    """Phần đuôi `<model>` của `<tien_to><model>`, đã hạ về chữ thường.

    🔴 WINDOWS **VIẾT HOA** TÊN BIẾN MÔI TRƯỜNG. `os.environ` trên Windows không
       phân biệt hoa thường và trả khoá đã viết hoa, nên
       `LTT_LLM_TOKEN_POOL__qwen35-api` đọc ra thành `..._POOL__QWEN35-API` —
       khớp tiền tố vẫn đúng, nhưng tên model thì **không** khớp `catalog`, và
       hậu quả là một ghi đè cấu hình **im lặng không có tác dụng**.

    ⚠️ Đây không phải giả thuyết: bộ kiểm của chính Task 4.2 đỏ vì nó, trên đúng
       hệ điều hành mà máy B chạy. Id model trong kho này đều chữ thường, nên hạ
       về chữ thường là phép đối chiếu đúng ở cả hai phía.
    """
    if not ten_bien.upper().startswith(tien_to.upper()):
        return None
    duoi = ten_bien[len(tien_to):].strip().lower()
    return duoi or None


def _pool_theo_model() -> dict:
    """Bể KV theo model: **dẫn xuất** từ `catalog`, rồi mới cho env ghi đè.

    Thứ tự: `catalog.HO_SO[*].max_context` (số `-c` thật của hồ sơ, đã bị
    `test_334` buộc khớp `llama-swap.yaml`) → `LTT_LLM_TOKEN_POOL` (chung, cho
    **mọi** model) → `LTT_LLM_TOKEN_POOL__<model>` (riêng).

    ⭐ Ghi đè chung đứng TRƯỚC ghi đè riêng, nên một lần "hạ tạm cả hai bể" vẫn
       giữ được một ngoại lệ cho một model. Nếu đảo lại thì biến chung sẽ xoá
       biến riêng một cách vô hình.
    """
    from .catalog import HO_SO

    ra = {m.ten: int(m.max_context) for m in HO_SO}
    chung = _int("LTT_LLM_TOKEN_POOL", 0)
    if chung > 0:
        ra = {ten: chung for ten in ra}
    ra.update(_theo_model("LTT_LLM_TOKEN_POOL__"))
    return ra


def _san_vram() -> dict:
    """Sàn VRAM trống theo model. Mặc định: chỉ `qwen35-api` (5060 Ti) có sàn.

    ⚠️ `...__<model>=0` **tắt** sàn của model ấy — và đó là một lựa chọn vận hành
       hợp lệ (máy không có `nvidia-smi`, hoặc đang chẩn đoán), nên nó phải nói
       được. `_theo_model` bỏ số 0, nên chỗ này đọc trực tiếp.
    """
    # 600 = dai chu du an cho phep la 600-700 (L-18). Chon 600 chu khong
    # phai 700 vi phep do DINH: xem khoi chu thich cua `vram_trong_toi_thieu_mb`.
    ra = {"qwen35-api": 600}
    tien_to = "LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__"
    for ten, gt in os.environ.items():
        model = _duoi_ten_model(ten, tien_to)
        if model is None:
            continue
        try:
            so = int((gt or "").strip())
        except ValueError:
            continue
        ra[model] = max(0, so)
    return ra
