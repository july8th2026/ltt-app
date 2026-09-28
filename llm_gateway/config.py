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
    #
    # ⛔ ĐÃ GỠ `max_input_tokens` (phương án C bước 3, O-02). Trần vào là
    #    **theo model** và **dẫn xuất**: `vat_ly.tran_vao(-c, max_out, DEM_UOC)`,
    #    cùng công thức với `apps/ltt_llm/ngan_sach.tran_vao_cua(m)`. Env cũ
    #    `LTT_LLM_MAX_INPUT_TOKENS` ép một số cho CẢ HAI model — sai cho 3.5.
    #
    #: Trần token sinh ra mỗi yêu cầu (= `ngan_sach.TOKEN_RA_TRAN` của máy A;
    #: `deploy.ps1` ghi nó vào `gateway.env` bằng cách ĐỌC ngan_sach, không gõ).
    max_output_tokens: int
    #: Trần byte của một ảnh gửi kèm (base64 đã giải mã).
    #:
    #: ⛔ ĐÃ GỠ `max_images` (env `LTT_LLM_MAX_IMAGES`, 28/09/2026, quyết định C4
    #:    của chủ dự án). Lý do: con số 4 không có phép đo nào đứng sau, llama.cpp
    #:    KHÔNG có trần số ảnh, và trần thật luôn là NGỮ CẢNH. Chi phí ngữ cảnh
    #:    của một ảnh nay được TÍNH (`anh_token.token_anh`, đo 14/14 ô ngày
    #:    28/09) thay vì quy bằng một hằng phẳng, nên đếm ảnh không còn đo gì.
    #:    Rủi ro tồn dư (nhiều ảnh nhỏ ⇒ nhiều lượt mã hoá mmproj) ghi ở
    #:    `docs/superpowers/specs/2026-09-28-vision-plan-lock.md` §7.2.
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

    # ⛔ ĐÃ GỠ (phương án C bước 3): `max_dong_thoi`/`LTT_LLM_MAX_DONG_THOI[__m]`,
    #    `rpm`/`LTT_LLM_RPM` (O-03), `token_pool_rieng`/`LTT_LLM_TOKEN_POOL[__m]`.
    #    Số chuỗi và bể KV là `-np`/`-c` của **từng** hồ sơ, đọc thẳng từ
    #    `llama-swap.yaml` (`vat_ly`). Nhịp/tần suất/công bằng là việc của máy A.
    #    Biến cũ còn đặt trong `gateway.env` chỉ sinh một dòng cảnh báo lúc khởi
    #    động (`bien_da_go_con_dat`), không còn tác dụng.

    #: Biên ước token vào (`DEM_UOC`) — cùng số máy A cộng vào đặt chỗ và trừ ra
    #: khỏi trần vào. Nguồn chân lý là `apps/ltt_llm/ngan_sach.py`; `deploy.ps1`
    #: ghi `LTT_LLM_DEM_UOC` bằng cách ĐỌC nó, và `test_1223` đối chiếu mặc định.
    dem_uoc: int = 2_048                     # = DEM_UOC_MAC_DINH (duoi day)

    #: `{hồ sơ: VatLy}` đọc từ `llama-swap.yaml` (`vat_ly.tim_yaml`).
    #:
    #: ⭐ Mặc định **đọc tệp**, không phải dict rỗng: `Config(**...)` dựng tay ở
    #:    nhiều bộ test, và một rào vật lý rỗng là một cổng không mở model nào —
    #:    đúng lớp lỗi "xanh vì lý do sai".
    vat_ly: dict = field(default_factory=lambda: _vat_ly_mac_dinh()[1])
    #: Tệp yaml đã đọc — cho `/health`, để người trực biết cổng tin tệp nào.
    nguon_vat_ly: str = field(default_factory=lambda: _vat_ly_mac_dinh()[0])

    #: Sàn VRAM trống theo model, MiB: `LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__<model>`.
    #: Dưới sàn ⇒ **429 bận**, không nhận lượt mới (không giết lượt đang chạy).
    #:
    #: ⭐ MẶC ĐỊNH **TẮT (0)** CHO `qwen35-api` — xem L-21. Sàn 600 ở L-18 đã
    #:    tạo vòng tự khóa 42 phút trên production trong khi không có OOM.
    #:    Cơ chế vẫn tồn tại dưới dạng opt-in. Chỉ bật lại khi có bằng chứng OOM
    #:    và một ngưỡng được đo dưới đúng tải production; không suy từ VRAM rảnh.
    #:
    #: ⛔ `qwen38-api` KHÔNG có sàn ở đây. Không phải bỏ quên: cuộc tranh trên
    #:    3090 do **trọng tài residency ở máy A** phân xử (D01 B), và chốt VRAM
    #:    của nó là `vram_sach_mb` ở trên, áp một lần tại `POST
    #:    /v1/residency/nap`. Thêm một cái sàn thứ hai cho cùng một card là hai
    #:    chốt nói hai thứ khác nhau về một trạng thái.
    vram_trong_toi_thieu_mb: dict = field(default_factory=dict)

    @staticmethod
    def from_env() -> "Config":
        nguon, vat_ly = _vat_ly_mac_dinh()
        return Config(
            upstream_url=(os.environ.get("LTT_LLM_UPSTREAM_URL")
                          or "http://127.0.0.1:8280").rstrip("/"),
            host=os.environ.get("LTT_LLM_HOST") or "127.0.0.1",
            port=_int("LTT_LLM_PORT", 8299),
            token=(os.environ.get("LTT_LLM_TOKEN") or "").strip(),
            models_mo=_danh_sach("LTT_LLM_MODELS"),
            # 🔴 NGUỒN CHÂN LÝ là `apps/ltt_llm/ngan_sach.py::TOKEN_RA_TRAN`. Kho
            #    này deploy sang máy B nên **không import được** từ đó; mặc định ở
            #    đây là bản sao, `deploy.ps1` ghi giá trị ĐỌC từ ngan_sach vào
            #    `gateway.env`, và `tests/test_334_ngan_sach_ltt_llm.py` +
            #    `tests/test_1223_phuong_an_c_rao_vat_ly_b.py` đỏ khi lệch.
            max_output_tokens=_int("LTT_LLM_MAX_OUTPUT_TOKENS", 32_768),
            max_image_bytes=_int("LTT_LLM_MAX_IMAGE_BYTES", 12 * 1024 * 1024),
            upstream_timeout_s=_float("LTT_LLM_UPSTREAM_TIMEOUT_S", 600.0),
            stream_timeout_s=_float("LTT_LLM_STREAM_TIMEOUT_S", 900.0),
            ram_trong_toi_thieu_gb=_float("LTT_LLM_RAM_TRONG_GB", RAM_TRONG_GB_MAC_DINH),
            trong_tai_bat=(os.environ.get("LTT_LLM_TRONG_TAI") or "1").strip() != "0",
            vram_sach_mb=_int("LTT_LLM_VRAM_SACH_MB", 2500),
            nhip_tim_giay=_float("LTT_LLM_NHIP_TIM_S", 15.0),
            vram_trong_toi_thieu_mb=_san_vram(),
            dem_uoc=_int("LTT_LLM_DEM_UOC", DEM_UOC_MAC_DINH),
            vat_ly=vat_ly,
            nguon_vat_ly=nguon,
        )


#: Sàn RAM trống (GiB — `psutil.available / 1024**3`) của trọng tài cổng B. L-25
#: (18/09): 48 → 24. Cùng một ràng buộc với `--cache-ram` của `llama-swap.yaml`:
#: 2 × cache + sàn + biên ≤ RAM trống lúc cache rỗng (đo 85,0). `deploy.ps1` ghi
#: đè `gateway.env` bằng đúng số này mỗi lần deploy; `test_1293` đối chiếu cả ba.
#:
#: ⚠️ Sàn này chỉ **chặn lượt mới** — nó không xả cache. Và nó KHÔNG phải sàn của
#:    cổng render (`LTT_RENDER_RAM_TRONG_GB`, vẫn 48): hai cổng, hai phép tính.
RAM_TRONG_GB_MAC_DINH = 24.0

#: Bản sao của `DEM_UOC` máy A (`apps/ltt_llm/ngan_sach.py`, trước bước 2 tên
#: `LE`, ĐÃ THAY). `tests/test_1223_phuong_an_c_rao_vat_ly_b.py` đối chiếu nó VÀ mặc định
#: của trường `Config.dem_uoc`.
DEM_UOC_MAC_DINH = 2_048

#: Biến môi trường ĐÃ GỠ ở phương án C bước 3. Khớp theo TIỀN TỐ để bắt cả dạng
#: `__<model>`. Còn đặt ⇒ cảnh báo lúc khởi động (không còn tác dụng).
BIEN_DA_GO = ("LTT_LLM_MAX_INPUT_TOKENS", "LTT_LLM_MAX_DONG_THOI",
              "LTT_LLM_TOKEN_POOL", "LTT_LLM_RPM")


def bien_da_go_con_dat() -> list[str]:
    """Tên các biến đã gỡ nhưng vẫn còn trong môi trường tiến trình."""
    return sorted(ten for ten in os.environ
                  if any(ten.upper().startswith(g) for g in BIEN_DA_GO))


def _vat_ly_mac_dinh() -> tuple[str, dict]:
    """`(đường tệp, {hồ sơ: VatLy})` — ném `vat_ly.YamlHong` khi không dựng được."""
    from . import vat_ly as VL

    p = VL.tim_yaml()
    return str(p), VL.doc_tep(p)


def _duoi_ten_model(ten_bien: str, tien_to: str) -> "str | None":
    """Phần đuôi `<model>` của `<tien_to><model>`, đã hạ về chữ thường.

    🔴 WINDOWS **VIẾT HOA** TÊN BIẾN MÔI TRƯỜNG. `os.environ` trên Windows không
       phân biệt hoa thường và trả khoá đã viết hoa, nên
       `LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__qwen35-api` đọc ra thành `..._MB__QWEN35-API` —
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


def _san_vram() -> dict:
    """Sàn VRAM trống theo model. Mặc định: chỉ `qwen35-api` (5060 Ti) có sàn.

    ⚠️ `...__<model>=0` **tắt** sàn của model ấy — và đó là một lựa chọn vận hành
       hợp lệ (máy không có `nvidia-smi`, hoặc đang chẩn đoán), nên nó phải nói
       được. `_theo_model` bỏ số 0, nên chỗ này đọc trực tiếp.
    """
    # L-21: số đo production 15/09 bác sàn 600 (112 lần `ban_vram`, 0 lần đầy
    # suất, model mất phục vụ 42 phút, không có OOM). Giữ cơ chế opt-in qua env,
    # nhưng mặc định 0 để không dựng một lỗi giả từ VRAM WDDM dao động.
    ra = {"qwen35-api": 0}
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
