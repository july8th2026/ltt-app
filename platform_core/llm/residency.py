"""residency.py — MÁY TRẠNG THÁI chia RTX 3090 giữa LTT-3.8 và model ảnh. (D01 B)

⭐ HÀM THUẦN, và đó là toàn bộ lý do tệp này tồn tại riêng: không CSDL, không
   HTTP, không đọc đồng hồ, không `sleep`. Thời gian và trạng thái đi VÀO bằng
   tham số (`bay_gio`, `TrangThai`, `QuanSat`), quyết định đi RA bằng giá trị
   trả về (`TrangThai` mới + các lệnh phải phát). Mọi tác dụng phụ — đọc lease,
   đọc hàng job, gọi gateway máy B, ghi dòng `gpu_residency` — nằm ở người gọi
   (Task 5.3 admission, Task 5.5 trọng tài).

   Nhờ vậy luật chia card kiểm được **không cần GPU, không cần máy B, không cần
   CSDL**: `tests/test_1216_residency_thuan.py` chạy nó qua mọi cặp
   trạng thái × quan sát trong vài giây.

⛔ LUẬT SÁNG LẬP CỦA CHƯƠNG TRÌNH (L-9, D01 B): **không lượt nào bị giết để đổi
   cư trú** — cả lượt LLM lẫn lượt vẽ. Vì llama.cpp không preempt được và ComfyUI
   cũng không, "đổi cư trú" chỉ có một cách đúng: **drain**. Máy này encode luật
   ấy bằng hai thứ cơ học chứ không bằng lời văn:

   1. `CHUYEN_HOP_LE` — bảng chuyển. `_sang()` là cửa DUY NHẤT đổi trạng thái và
      nó ném với mọi cặp ngoài bảng. Nên `LLM → NHA_LLM` (nhả model khi chưa
      drain) hay `ANH → NAP_LLM` (nạp lại khi lượt vẽ còn chạy) không phải là
      "một nhánh code cần cẩn thận" — chúng **không biểu đạt được**.
   2. Ba bất biến ở tầng LỆNH, vì lệnh mới là thứ giết việc:
      · `nha_llm` chỉ phát khi `da_drain_xong(qs)` — 0 lease LLM **và** gateway
        báo 0 in-flight (không đo được ⇒ coi như chưa drain);
      · `nap_llm` và `free_comfy` chỉ phát khi `dang_ve_anh(qs)` là False.
        Nạp 16 GB trọng số lên card đang vẽ, hay dọn VRAM của ComfyUI đang vẽ,
        là giết lượt vẽ bằng OOM.

📐 Các con số ĐÃ ĐO (12/09/2026, `docs/ltt_llm_dual/10_BENCHMARK_P3.md`) — đừng
   thay bằng phỏng đoán, và đừng đo lại ở đây:

   · `t_nap_llm_s = 16,3` (§G4, nạp LTT-3.8 từ kho ấm). Bản plan đầu đoán 45,0 —
     gấp 2,8 lần thật, và sai số ấy đẩy về phía **ngần ngại đổi cư trú**, tức
     3090 nằm sai chỗ lâu hơn cần.
   · **MỘT con số phủ cả kho ấm và kho lạnh** (§G5): kho lạnh chỉ đắt hơn 7–11 %
     (≈16,9 s cho 3.8), vì nút thắt của việc nạp không phải đọc tệp mà là đẩy
     trọng số lên GPU + cấp phát ngữ cảnh — hai thứ không đổi giữa ấm và lạnh.
     Cận trên 17 s phủ cả hai. Nên ở đây **không cần hai tham số**, và một tham
     số thứ hai sẽ là một nút không ai biết đặt bao nhiêu.
   · Và kho lạnh gần như không xảy ra: hồ sơ mới đặt `ttl: 0` + `preload`, hai
     model nằm thường trú, còn trọng tài chỉ tháo/nạp LTT-3.8 và lần nạp lại
     luôn cách lần trước vài phút — thừa sức còn trong standby cache 24,8 GB.
   · `t_anh_uoc_s = 110` — đo 92–110 s/ảnh (`docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md`,
     `CHIA_GPU_HAI_MODEL.md`). Lấy đầu **xấu** của dải: con số này dùng để đoán
     "vẽ thêm một ảnh nữa có làm người chờ LLM chết vì hết trần chờ không", và
     đoán thấp ở đó thì người chờ chết thật.

⚠️ `free_comfy` KHÔNG phải chỉ `POST /free` (L-14 §3, spec §0): ComfyUI ấm giữ
   **223,5 MiB** ngữ cảnh CUDA thường trú và `/free` **không** nhả nó — chỉ dừng
   dịch vụ mới nhả. Biên của LTT-3.8 ở `-c 221184` là **445 MiB** khi ComfyUI
   chưa nạp, nên 223,5 MiB không phải chuyện tối ưu, nó là **ràng buộc cứng**:
   người thực thi lệnh này (Task 5.4/5.5) phải dừng hẳn dịch vụ LTTComfyUI trong
   cửa sổ LLM. Tên lệnh giữ theo plan để Task 5.4 khớp chuỗi; nghĩa của nó là
   *"làm cho VRAM 3090 sạch"*, không phải *"gọi đúng endpoint /free"*.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

# ── Trạng thái của nhóm GPU ───────────────────────────────────────────────────
#
# Chuỗi ổn định: chúng vào cột `gpu_residency.trang_thai`, vào `/ops/jobs-metrics`
# và vào log. Đổi một giá trị ở đây là đổi dữ liệu đang nằm trong CSDL.
LLM, XA_LLM, NHA_LLM, ANH, TRA_ANH, NAP_LLM, LOI_NAP = (
    "llm", "xa_llm", "nha_llm", "anh", "tra_anh", "nap_llm", "loi_nap")

#: Thứ tự = thứ tự một chu trình bình thường đi qua. Dùng để duyệt trong phép kiểm.
TRANG_THAI: tuple[str, ...] = (LLM, XA_LLM, NHA_LLM, ANH, TRA_ANH, NAP_LLM, LOI_NAP)

# ── Lệnh gửi ra ngoài ─────────────────────────────────────────────────────────
#
# Máy thuần KHÔNG gọi gì; nó trả về TÊN việc phải làm. Cả ba đều **idempotent**
# theo thiết kế, vì người gọi có thể phát lại chúng nhiều lượt bước liền nhau khi
# máy B còn chưa xong (xem nhánh `NHA_LLM`).
NHA_LLM_LENH, NAP_LLM_LENH, FREE_COMFY_LENH = "nha_llm", "nap_llm", "free_comfy"

#: Trạng thái → những trạng thái nó được phép sang. "Ở lại" không phải một chuyển,
#: nên không trạng thái nào tự lặp trong bảng này.
#:
#: ⭐ Đọc bảng này bằng những gì nó KHÔNG chứa — đó là chỗ luật sống:
#:
#:   · `LLM → NHA_LLM`, `LLM → ANH`   nhả model / vẽ mà chưa drain lượt LLM;
#:   · `XA_LLM → ANH`                 vẽ trước khi máy B xác nhận model đã rời card;
#:   · `ANH → NAP_LLM`                nạp lại khi lượt vẽ còn đang chạy;
#:   · `TRA_ANH → LLM`                khai "LLM đang cư trú" mà chưa nạp gì.
#:
#: Bốn dòng đó là bốn cách giết việc đang chạy, và không cái nào biểu đạt được.
CHUYEN_HOP_LE: dict[str, frozenset[str]] = {
    LLM: frozenset({XA_LLM}),
    # Về `LLM` là đường HUỶ BỎ: job ảnh rút khỏi hàng giữa lúc drain thì không có
    # gì phải đổi nữa, và quay lại không tốn một lần nạp 16,3 s.
    XA_LLM: frozenset({NHA_LLM, LLM}),
    NHA_LLM: frozenset({ANH}),
    ANH: frozenset({TRA_ANH}),
    TRA_ANH: frozenset({NAP_LLM}),
    NAP_LLM: frozenset({LLM, LOI_NAP}),
    LOI_NAP: frozenset({NAP_LLM}),
}


# ── Câu hỏi duy nhất admission đặt ra cho máy này ─────────────────────────────
#
# Nền tảng chỉ biết **vai trò**, không biết tên app (`test_147` layering): app khai
# `AdmissionModel(..., residency_group="rtx3090", vai_tro=...)` qua `ToolSpec`.
MAC_DINH, THEO_LO = "mac_dinh", "theo_lo"
VAI_TRO: tuple[str, ...] = (MAC_DINH, THEO_LO)

#: Vai trò → những trạng thái nhóm MỞ cửa admission cho nó. Một bảng chứ không
#: một biểu thức `or`, vì đây là nơi duy nhất trả lời "ai được nhận lượt mới", và
#: bất biến cốt tuỷ của D01 B đọc thẳng ra được từ nó: **không trạng thái nào có
#: mặt ở cả hai dòng** ⇒ hai model không bao giờ cùng nhận lượt trên một card.
TRANG_THAI_MO: dict[str, frozenset[str]] = {
    MAC_DINH: frozenset({LLM}),
    THEO_LO: frozenset({ANH}),
}


def mo_cho(ten: str, vai_tro: str) -> bool:
    """Admission của thành viên có vai trò này đang mở không (luật 0 của `luat_nhan`)?

    Hai kiểu đầu vào "lạ" được xử KHÁC nhau, và lý do nằm ở hậu quả:

    · **trạng thái lạ ⇒ đóng.** Fail-closed, và cái lạ ấy vẫn có người báo động:
      `buoc_thuan` ném khi gặp nó, nên trọng tài sẽ kêu. Admission chỉ cần đừng
      mở cửa cho một cư trú mà không ai biết là cư trú gì.
    · **vai trò lạ ⇒ NÉM.** Một `vai_tro` gõ sai trong manifest (`"theolo"`) mà
      trả về False sẽ làm app đó không bao giờ được nhận lượt — một app chết âm
      thầm, và loại hỏng đó đắt hơn nhiều một ngoại lệ ở cửa.
    """
    if vai_tro not in TRANG_THAI_MO:
        raise ValueError(f"vai tro la: {vai_tro!r}")
    return ten in TRANG_THAI_MO[vai_tro]


@dataclass(frozen=True)
class TrangThai:
    """Toàn bộ trạng thái BỀN của nhóm — đúng bốn trường, khớp bảng `gpu_residency`.

    Mọi thứ khác mà máy cần biết là **quan sát** (`QuanSat`), tức thứ đọc lại
    được từ sự thật (lease, hàng job, máy B). Giữ trạng thái bền tối thiểu là
    cách duy nhất để một tiến trình chết giữa cửa sổ không để lại một bộ đếm sai.
    """

    ten: str = LLM
    #: Vào `ten` hiện tại từ lúc nào (giây, cùng gốc với `bay_gio`).
    tu_luc: float = 0.0
    #: Cửa sổ ảnh mở lúc nào. Chỉ có nghĩa từ `ANH` trở đi.
    cua_so_bat_dau: float = 0.0
    lan_nap_loi: int = 0


@dataclass(frozen=True)
class ThamSoResidency:
    """Tham số cấu hình. Mọi con số ở đây ĐO ĐƯỢC hoặc do chủ dự án chốt (D01).

    Người gọi dựng một thể hiện từ cấu hình; máy không đọc `os.environ`.
    """

    #: Trần trên của một cửa sổ ảnh (D01, tham số khởi đầu của chủ dự án).
    cua_so_anh_toi_da: int = 4
    cua_so_anh_s: float = 480.0
    #: ĐÃ ĐO 12/09 §G4: nạp LTT-3.8 (16,46 GB) từ kho ấm. §G5 cho cận trên 17 s
    #: phủ luôn kho lạnh (+11 %) ⇒ một con số là đủ. Xem docstring module.
    t_nap_llm_s: float = 16.3
    #: Đầu XẤU của dải đo 92–110 s/ảnh: con số này quyết "vẽ thêm một ảnh nữa có
    #: làm người chờ LLM chết không", và đoán thấp ở đó là để họ chết thật.
    t_anh_uoc_s: float = 110.0
    bien_s: float = 30.0
    #: VRAM 3090 phải xuống dưới mức này mới nạp LTT-3.8 (fail-closed ở máy B nữa).
    vram_sach_mib: int = 2500
    lui_nap_loi_s: float = 30.0


@dataclass(frozen=True)
class QuanSat:
    """Sự thật đọc được ở một thời điểm. **Không trường nào có mặc định** — trừ
    `nap_ket_qua` — vì mỗi trường là một câu hỏi người gọi phải trả lời; một mặc
    định ở đây là một câu trả lời bịa ra cho câu chưa hỏi.

    `None` ở ba trường của máy B nghĩa là **không hỏi được**, và máy luôn xử
    `None` theo hướng KHÔNG hành động (fail-closed) — không phải theo hướng 0.
    """

    #: Lease sống của thành viên `mac_dinh` (LTT-3.8 trên 3090).
    lease_llm: int
    #: Lease sống của thành viên `theo_lo` (model ảnh trên 3090).
    lease_anh: int
    #: Job `theo_lo` đang `queued`.
    job_anh_cho: int
    #: Job `theo_lo` đã được NHẬN kể từ `TrangThai.cua_so_bat_dau`. Đếm từ bảng
    #: `jobs`, không phải một bộ đếm ghi tay (xem docstring `models.GpuResidency`).
    anh_bat_dau_trong_cua_so: int
    #: Người chờ LTT-3.8: waiter của cửa tương tác + job `mac_dinh` đang `queued`.
    nguoi_cho_llm: int
    #: Giây còn lại tới hạn chót SỚM NHẤT của người chờ LLM. `None` = không ai chờ
    #: hoặc không ai có hạn chót.
    han_chot_llm_s: float | None
    #: Sổ slot của gateway máy B cho `qwen38-api`. `None` = không hỏi được máy B.
    gateway_inflight_llm: int | None
    #: llama-swap có đang giữ hồ sơ `qwen38-api` không. `None` = không hỏi được.
    llm_da_nap: bool | None
    #: VRAM đang dùng trên UUID 3090. `None` = không đọc được.
    vram_3090_mib: int | None
    #: Kết quả lượt nạp do lệnh `nap_llm` GẦN NHẤT khởi động: `""` (đang chạy hoặc
    #: chưa có) | `"ok"` | `"loi"`.
    #:
    #: ⚠️ Máy B phải đặt lại `""` khi nhận một lệnh `nap_llm` mới. Giữ `"loi"` cũ
    #: thì máy quay vòng `LOI_NAP → NAP_LLM → LOI_NAP` và thời gian lùi chạm trần
    #: vì một con số cũ. Ghim ở
    #: `test_1216::test_nap_ket_qua_cu_lam_phong_lui_dan_nen_may_b_phai_dat_lai`.
    nap_ket_qua: str = ""


# ── Ba vị từ: mỗi cái là một cái PHANH, nên mỗi cái là một hàm có tên ────────
#
# Tách ra khỏi thân `buoc_thuan` có hai lý do, cả hai đều thực dụng: người đọc
# thấy được luật mà không phải giải mã một biểu thức `and/or` dài, và phép kiểm
# ĐỐI CHỨNG có thứ để gỡ — `monkeypatch` một trong hai hàm dưới đây rồi chạy lại
# phép quét vét cạn là cách chứng minh phép kiểm THẬT SỰ bắt được việc gỡ phanh.

def da_drain_xong(qs: QuanSat) -> bool:
    """Lượt LLM đã chạy hết chưa? Hỏi HAI sổ, và `None` là "chưa".

    Sổ lease của máy A một mình không đủ: một lượt có thể đã nhả lease mà kết nối
    tới llama-server còn sống (hoặc ngược lại — một lease mồ côi). Nhả model khi
    gateway còn in-flight là **giết một lượt của khách đang chạy**, đúng thứ
    `GET /unload` cũ đã làm và là lý do trọng tài cũ bị gỡ (D01, L-9).
    """
    return qs.lease_llm == 0 and qs.gateway_inflight_llm == 0


def dang_ve_anh(qs: QuanSat) -> bool:
    """Có lượt vẽ nào đang chạy không. Phanh của chiều NGƯỢC lại: nạp 16 GB lên
    card đang vẽ, hay dọn VRAM của ComfyUI đang vẽ, giết lượt vẽ bằng OOM."""
    return qs.lease_anh > 0


def lui_nap_s(tt: TrangThai, ts: ThamSoResidency) -> float:
    """Thời gian lùi trước lần nạp lại tiếp theo: gấp đôi, chặn trần ở ×16.

    Trần có mặt để một máy B đang hỏng không bị gọi nạp mỗi 30 s mãi mãi, mà cũng
    không bị lùi thành hàng giờ — 480 s là mức mà một lượt sửa tay kịp xen vào.
    """
    return ts.lui_nap_loi_s * min(2 ** max(tt.lan_nap_loi - 1, 0), 16)


def _sang(tt: TrangThai, ten: str, bay_gio: float, **dat) -> TrangThai:
    """Cửa DUY NHẤT đổi trạng thái. Ném nếu cặp chuyển không có trong bảng.

    Vì sao ném chứ không trả về `tt`: một chuyển ngoài bảng không phải một điều
    kiện chưa thoả, nó là một **lỗi lập trình** — và lỗi loại đó ở đây có nghĩa
    là máy vừa suýt giết một lượt của khách. Im lặng ở lại sẽ biến nó thành một
    nhóm GPU treo mà không ai biết vì sao.
    """
    if ten not in CHUYEN_HOP_LE[tt.ten]:
        raise ValueError(f"chuyen bat hop le: {tt.ten!r} -> {ten!r}")
    return replace(tt, ten=ten, tu_luc=bay_gio, **dat)


def _dong_cua_so(tt: TrangThai, qs: QuanSat, ts: ThamSoResidency,
                 bay_gio: float) -> bool:
    """Đã tới lúc đóng cửa sổ ảnh chưa (spec §12, D01 B)?

    Bốn vế, theo đúng thứ tự này, và thứ tự là một phần của luật:

    1. **Hết việc ảnh** ⇒ đóng ngay, kể cả khi không ai chờ LLM: giữ card cho một
       hàng rỗng là giữ không.
    2. **Không ai chờ LLM** ⇒ KHÔNG đóng, dù đã quá trần 4 ảnh / 480 s. Trần của
       D01 là trần **trên**, không phải một hạn phải dừng; dừng xe khi không ai
       đợi bến là bỏ không một card (work-conserving).
    3. Có người chờ ⇒ hết trần số ảnh, hoặc hết trần thời gian.
    4. Có người chờ ⇒ **vẽ thêm một ảnh nữa sẽ đẩy người chờ lâu nhất quá hạn
       chót của cửa họ**: `hạn_chót − t_nap_llm − t_anh_uoc − biên ≤ 0`.

    Vế 4 là chỗ spec giải xung đột giữa hai tham số: một ảnh mất 92–110 s nên trần
    4 ảnh (≈6–7 phút) DÀI HƠN trần chờ stream 300 s của D-06. Không có vế này thì
    cửa sổ vẫn "đúng luật D01" trong khi người chờ chết vì hết trần chờ.
    """
    if qs.job_anh_cho == 0 and not dang_ve_anh(qs):
        return True
    if qs.nguoi_cho_llm == 0:
        return False
    if qs.anh_bat_dau_trong_cua_so >= ts.cua_so_anh_toi_da:
        return True
    if bay_gio - tt.cua_so_bat_dau >= ts.cua_so_anh_s:
        return True
    if qs.han_chot_llm_s is not None and (
            qs.han_chot_llm_s - ts.t_nap_llm_s - ts.t_anh_uoc_s - ts.bien_s) <= 0:
        return True
    return False


def buoc_thuan(tt: TrangThai, qs: QuanSat, ts: ThamSoResidency,
               bay_gio: float) -> tuple[TrangThai, tuple[str, ...]]:
    """MỘT bước của máy: trạng thái + quan sát + giờ ⇒ trạng thái mới + lệnh.

    Người gọi lặp nó (vòng bảo trì worker, ~2 s một lượt) và thực thi các lệnh trả
    về. Mọi lệnh đều idempotent, vì "đã xong chưa" chỉ biết được ở lượt sau qua
    quan sát — nên máy phát lại lệnh cho tới khi quan sát đổi.

    Trả `(tt, ())` nghĩa là **chưa tới lúc**, và đó là câu trả lời đúng ở phần lớn
    lượt bước. Trạng thái chỉ đổi qua `_sang`, nên không nhánh nào dưới đây có thể
    nhảy một bước không có trong `CHUYEN_HOP_LE`.
    """
    t = tt.ten
    if t == LLM:
        # Chỉ một điều kiện rời `LLM`: có job ảnh đang xếp hàng. Không đọc VRAM,
        # không đoán — hàng job là thứ nói có việc cho model ảnh hay không.
        if qs.job_anh_cho > 0:
            return _sang(tt, XA_LLM, bay_gio), ()
        return tt, ()

    if t == XA_LLM:
        # Admission của LTT-3.8 đã đóng (luật 0, Task 5.3); lượt đang chạy chạy
        # tới hết. Ở đây máy chỉ CHỜ — và chờ là toàn bộ nội dung của L-9.
        if qs.job_anh_cho == 0 and not dang_ve_anh(qs):
            return _sang(tt, LLM, bay_gio), ()      # job ảnh rút ⇒ huỷ việc đổi
        if da_drain_xong(qs):
            return _sang(tt, NHA_LLM, bay_gio), (NHA_LLM_LENH,)
        return tt, ()

    if t == NHA_LLM:
        # Không tin lệnh đã gửi: chỉ đi tiếp khi máy B NÓI model không còn nạp.
        # `None` (không hỏi được) ⇒ ở lại, vì mở cửa sổ ảnh khi LTT-3.8 vẫn nằm
        # trên card là cách chắc chắn nhất để OOM cả hai bên.
        if qs.llm_da_nap is False:
            return _sang(tt, ANH, bay_gio, cua_so_bat_dau=bay_gio), ()
        if da_drain_xong(qs):
            return tt, (NHA_LLM_LENH,)              # lặp lệnh, nó idempotent
        return tt, ()

    if t == ANH:
        if _dong_cua_so(tt, qs, ts, bay_gio):
            return _sang(tt, TRA_ANH, bay_gio), ()
        return tt, ()

    if t == TRA_ANH:
        # Admission của ảnh đã đóng; lượt vẽ đang chạy chạy tới hết (L-9 chiều
        # ngược). Không phát lệnh nào trong lúc đó — kể cả `free_comfy`.
        if dang_ve_anh(qs):
            return tt, ()
        if qs.vram_3090_mib is not None and qs.vram_3090_mib <= ts.vram_sach_mib:
            return _sang(tt, NAP_LLM, bay_gio), (NAP_LLM_LENH,)
        # VRAM còn bẩn, hoặc không đọc được ⇒ dọn rồi đo lại lượt sau. ⚠️ "dọn" ở
        # đây là DỪNG dịch vụ LTTComfyUI, không phải `POST /free`: 223,5 MiB ngữ
        # cảnh CUDA của ComfyUI không nhả theo `/free`, và biên của LTT-3.8 chỉ
        # 445 MiB (L-14 §3).
        return tt, (FREE_COMFY_LENH,)

    if t == NAP_LLM:
        if qs.nap_ket_qua == "ok" and qs.llm_da_nap:
            return _sang(tt, LLM, bay_gio, lan_nap_loi=0), ()
        if qs.nap_ket_qua == "loi":
            return _sang(tt, LOI_NAP, bay_gio, lan_nap_loi=tt.lan_nap_loi + 1), ()
        return tt, ()

    if t == LOI_NAP:
        # ⭐ Vế `dang_ve_anh` là một chỗ SIẾT so với bản phác trong plan. Lý do:
        #    lệnh `nap_llm` phát từ đây không đi qua nhánh kiểm VRAM của `TRA_ANH`,
        #    nên nếu một lượt vẽ mới đã kịp bắt đầu (lease ảnh sống) thì bản phác
        #    sẽ nạp 16 GB lên một card đang vẽ. Máy B có chốt fail-closed cho ca
        #    đó, nhưng quyền quyết nghiệp vụ ở máy A (TD-D10) — nên phanh phải có
        #    ở đây, không phải chỉ ở bên kia dây.
        #    Không siết thêm bằng VRAM: từ `LOI_NAP` không ai phát `free_comfy`,
        #    nên một điều kiện VRAM ở đây sẽ thành ngõ cụt vĩnh viễn.
        if dang_ve_anh(qs):
            return tt, ()
        if bay_gio - tt.tu_luc >= lui_nap_s(tt, ts):
            return _sang(tt, NAP_LLM, bay_gio), (NAP_LLM_LENH,)
        return tt, ()

    raise ValueError(f"trang thai la: {t!r}")
