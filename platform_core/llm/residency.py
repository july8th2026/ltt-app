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

━━━ HAI NỬA TRONG MỘT TỆP (Task 5.5) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Từ Task 5.5 tệp này có **hai phần, phân cách bằng một dải kẻ**, và câu "hàm
thuần" ở trên vẫn đúng **từng chữ cho phần 1**:

  · **PHẦN 1 (tới `buoc_thuan`)** — luật. Không CSDL, không HTTP, không đồng hồ.
  · **PHẦN 2 (từ dải kẻ trở xuống)** — trọng tài: đọc lease/hàng job/máy B, ghi
    dòng `gpu_residency`, phát lệnh. `buoc()` **không** chứa một luật nào; nó
    dựng `QuanSat` rồi gọi `buoc_thuan` và thi hành thứ hàm ấy trả về.

Vì sao **một tệp** chứ không hai: mọi trường của `QuanSat` là một câu hỏi phần 2
phải trả lời, và hai tệp làm chúng trôi khỏi nhau trong im lặng — đúng loại hỏng
mà `QuanSat` (không trường nào có mặc định) sinh ra để chặn. Dải kẻ là ranh giới,
và phép kiểm `test_1219::test_phan_thuan_khong_cham_csdl_hay_mang` ghim nó.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger(__name__)

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
    # 13/09: them `NAP_LLM` — duong LUI. Xem `tran_vao_anh_hong` va L-07.
    NHA_LLM: frozenset({ANH, NAP_LLM}),
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
    #: Bao nhieu lan LIEN TIEP khong mo duoc cua so anh thi coi phia anh la
    #: KHONG DUNG DUOC, tra card cho LLM va ngung thu cho toi khi mo duoc.
    #:
    #: 🔴 VI SAO CAN: `NHA_LLM` truoc 13/09 chi co MOT duong ra (`ANH`), va loi
    #:    vao `ANH` doi `may_b.chay_comfy()` thanh cong. Ngay 13/09 cong render
    #:    may B chay ban cu thieu `/v1/nha_comfy` => 404 => khong bao gio vao
    #:    duoc `ANH`, ma cung khong co duong lui. Ket qua: LLM da roi card, anh
    #:    khong bao gio duoc ve, 3090 nam khong — `ltt-3.8` tra 429 suot 32 phut
    #:    (L-07). Mot trang thai vao duoc ma khong ra duoc la khuyet tat ve HINH
    #:    DANG, khong phai ve cau hinh: sua cau hinh lam su co AY het, khong lam
    #:    ngo cut ay het.
    tran_vao_anh_hong: int = 3
    #: Sau khi cham `tran_vao_anh_hong`, bao lau moi cho THU LAI mot lan.
    #:
    #: 🔴 VI SAO CAN (L-10, do 13/09): chi co `tran_vao_anh_hong` thi bo dem la
    #:    mot chieu. No duoc xoa o DUNG MOT cho — `chay_comfy()` thanh cong — ma
    #:    `chay_comfy()` lai nam sau chinh cai phanh dang chan. Do duoc: ComfyUI
    #:    hong 3 lan, roi BAT LAI BINH THUONG, nop job anh moi => trong tai dung
    #:    im o `llm` suot 120 s, job o `queued`, khong mot dong log. Phia anh bi
    #:    KHOA NGOAI cho toi khi ai do khoi dong lai worker. Ban va L-07 doi mot
    #:    ngo cut lay mot ngo cut khac, o phia ben kia.
    #:
    #: ⚖️ Vi sao THOI GIAN chu khong phai mot lan thu lai duy nhat: moi lan thu
    #:    ton mot chu trinh nha/nap do duoc **47 s** (46,7 s ngay 13/09), trong
    #:    do LLM roi card. Nhip 300 s giu gia ay o ~16 %, va gap doi (tran ×8 =
    #:    40 phut) de mot may B hong ca buoi khong bi tra gia ay mai.
    lui_anh_hong_s: float = 300.0


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
    #: So lan LIEN TIEP ben goi khong mo duoc cua so anh (khong bat lai duoc
    #: ComfyUI). Ben goi dem; may thuan chi DOC no nhu mot su that.
    #:
    #: ⭐ Vi sao no o `QuanSat` chu khong o `TrangThai`: no la thu doc lai duoc
    #:    tu the gioi (lenh vua roi co chay khong), khong phai trang thai BEN
    #:    cua nhom. Giu trang thai ben toi thieu la cach duy nhat de mot tien
    #:    trinh chet giua cua so khong de lai mot bo dem sai — cung ly do
    #:    `TrangThai` chi co bon truong.
    lan_vao_anh_hong: int = 0
    #: Luc lan hong GAN NHAT (cung dong ho voi `bay_gio`). 0 = chua hong lan nao.
    #: Di kem `lan_vao_anh_hong`: mot bo dem khong kem moc thoi gian thi khong
    #: the tu nhat di, va mot bo dem khong tu nhat di chinh la L-10.
    luc_anh_hong_cuoi: float = 0.0


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


def duoc_thu_anh(qs: QuanSat, ts: ThamSoResidency, bay_gio: float) -> bool:
    """Có được phép THỬ mở cửa sổ ảnh lúc này không.

    ⭐ MỘT vị từ, dùng ở HAI chỗ, và đó là toàn bộ nội dung của bản vá L-10:

        `LLM`      → `XA_LLM`   khi `duoc_thu_anh`  (nhả card để thử)
        `NHA_LLM`  → `NAP_LLM`  khi KHÔNG           (đường lui 2, trả card)

    🔴 Vì sao không được nới riêng vế ở `LLM`: ở `NHA_LLM`, đường lui 2 được
       kiểm **trước** nhánh vào `ANH`. Nới một mình vế `LLM` thì lượt thử lại sẽ
       nhả card rồi nạp lại ngay mà **không hề gọi `chay_comfy()`** — tốn trọn
       47 s để không hỏi được câu duy nhất cần hỏi. Hai chỗ phải đọc cùng một
       sự thật, nếu không "thử lại" chỉ là một vòng quay đắt tiền.

    Trả `True` khi chưa chạm trần, hoặc đã chạm trần nhưng đã lùi đủ lâu.

    ⚖️ `luc_anh_hong_cuoi = 0` (đếm nói đã hỏng, mà không biết hỏng lúc nào) cho
       ra `True` — CHỦ Ý. Hai trường ấy luôn được ghi cùng nhau ở `buoc()` nên
       lệch nhau là chuyện không nên xảy ra; nhưng nếu có, hướng hỏng an toàn là
       thử thừa một lượt 47 s (lần hỏng kế tiếp ghi lại mốc thật, tự sửa) chứ
       không phải khoá phía ảnh vô hạn — đúng cái L-10 vừa dạy.
    """
    if qs.lan_vao_anh_hong < ts.tran_vao_anh_hong:
        return True
    return bay_gio - qs.luc_anh_hong_cuoi >= lui_anh_s(qs, ts)


def lui_anh_s(qs: QuanSat, ts: ThamSoResidency) -> float:
    """Thời gian lùi trước lần thử mở cửa sổ ảnh tiếp theo: gấp đôi, trần ×8.

    Trần ×8 (40 phút) thấp hơn `lui_nap_s` có chủ ý: bên kia là LLM đã chết hẳn
    nên lùi lâu không mất gì thêm, còn bên này LLM vẫn đang phục vụ bình thường
    — cái đang chờ là hàng job ảnh, và một hàng job chờ quá 40 phút thì đằng nào
    cũng cần người, không cần máy thử tiếp.
    """
    du = max(qs.lan_vao_anh_hong - ts.tran_vao_anh_hong, 0)
    return ts.lui_anh_hong_s * min(2 ** du, 8)


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
        #
        # ⛔ VÀ MỘT PHANH: đừng nhả card khi phía ảnh đang KHÔNG DÙNG ĐƯỢC.
        #
        #    Không có vế này thì đường lui mới ở `NHA_LLM` biến thành một vòng
        #    quay: nhả → không mở được cửa sổ ảnh → lui về `LLM` → job ảnh vẫn
        #    xếp hàng → nhả lại → … Mỗi vòng tốn một lượt nạp 16,3 s và KHÔNG
        #    ai được phục vụ. Một đường lui không kèm phanh vào là đổi một ngõ
        #    cụt lấy một vòng lặp — hỏng theo kiểu khác, không phải hết hỏng.
        #    ⚠️ Nhưng phanh ấy phải TỰ NHẢ (L-10). Bản 13/09 viết thẳng
        #    `lan_vao_anh_hong < tran`, và vì bộ đếm chỉ được xoá sau một
        #    `chay_comfy()` thành công — thứ nằm sau chính cái phanh này — phía
        #    ảnh không bao giờ trở lại được, kể cả khi ComfyUI đã lành từ lâu.
        if qs.job_anh_cho > 0 and duoc_thu_anh(qs, ts, bay_gio):
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
        # 🔴 HAI ĐƯỜNG LUI, thêm 13/09 sau sự cố L-07. Trước đó `NHA_LLM` có
        #    ĐÚNG MỘT đường ra (`ANH`), và lối vào `ANH` đòi `chay_comfy()`
        #    thành công. Cổng render máy B chạy bản cũ ⇒ 404 ⇒ không bao giờ vào
        #    được, và không có gì để lui: LLM đã rời card, ảnh không bao giờ
        #    được vẽ, 3090 nằm không, `ltt-3.8` trả 429 suốt 32 phút.
        #
        # ⭐ Cả hai đều đi qua `NAP_LLM` chứ không nhảy thẳng về `LLM`: ở đây
        #    model ĐÃ rời card (khác hẳn `XA_LLM`, nơi nó còn nằm đó), nên "trả
        #    card cho LLM" bắt buộc là một lượt NẠP. Nhảy thẳng `LLM` là khai
        #    "LLM đang cư trú" trong khi card trống — đúng thứ bảng chuyển cấm
        #    ở `TRA_ANH → LLM`.

        # Đường lui 1 — HUỶ: việc ảnh rút hết trong lúc ta đang nhả.
        # Đối xứng với `XA_LLM`, nơi vế này đã có sẵn từ đầu. Thiếu nó ở đây là
        # toàn bộ chỗ bất đối xứng đã sinh ra L-07: huỷ job ảnh lúc 05:2x KHÔNG
        # gỡ được máy, vì đường huỷ chỉ tồn tại ở bước trước.
        if qs.job_anh_cho == 0 and not dang_ve_anh(qs):
            return _sang(tt, NAP_LLM, bay_gio), (NAP_LLM_LENH,)

        # Đường lui 2 — PHÍA ẢNH KHÔNG DÙNG ĐƯỢC: đã thử đủ nhiều lần mà không
        # mở nổi cửa sổ ảnh. Trả card cho LLM và để job ảnh xếp hàng chờ người
        # sửa. Một bên chạy được tốt hơn hẳn hai bên cùng chết.
        #
        # ⛔ Vẫn siết `dang_ve_anh` — cùng lý do như `LOI_NAP`: lệnh `nap_llm`
        #    phát từ đây không đi qua nhánh kiểm VRAM của `TRA_ANH`.
        #
        # ⭐ Đọc CÙNG vị từ với lối ra ở `LLM` (L-10): hết hạn lùi thì đây phải
        #    nhường đường cho nhánh vào `ANH` bên dưới, nếu không lượt thử lại
        #    quay đầu ngay tại đây và `chay_comfy()` không bao giờ được gọi.
        if not duoc_thu_anh(qs, ts, bay_gio) and not dang_ve_anh(qs):
            return _sang(tt, NAP_LLM, bay_gio), (NAP_LLM_LENH,)

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


# ═════════════════════════════════════════════════════════════════════════════
#  PHẦN 2 — TRỌNG TÀI (Task 5.5). Từ đây mới có CSDL, HTTP và đồng hồ.
# ═════════════════════════════════════════════════════════════════════════════
#
# ⛔ Không một LUẬT nào được viết dưới dải kẻ này. Thấy mình sắp viết `if` về
#    trạng thái ở đây thì `if` ấy thuộc `buoc_thuan` — nơi 40 ca của `test_1216`
#    nhìn thấy nó mà không cần CSDL, không cần máy B, không cần GPU.


#: Trạng thái dòng `gpu_residency` được TẠO ra ở lượt bước đầu tiên của một nhóm.
#:
#: 🔴 VÌ SAO `LLM` VÀ KHÔNG PHẢI MỘT TRẠNG THÁI "AN TOÀN HƠN". Ba sự thật khoá
#:    lựa chọn này lại, và chúng đến từ ba tầng khác nhau:
#:
#:    1. **Không có dòng ⇒ CẢ HAI cửa đóng** (luật 0 fail-closed, Task 5.3), và
#:       migration cố ý không gieo dòng nào. Nên trạng thái khởi tạo không phải
#:       một lựa chọn giữa "an toàn" và "liều": nó là lựa chọn giữa *bán hàng*
#:       và *không bán gì cả*. Báo cáo 5.3 §6.1 gọi đúng tên hậu quả: một máy B
#:       im lặng biến thành "LTT-3.8 ngừng bán", vì mọi lượt chờ hết ngân sách
#:       rồi 429.
#:    2. **`LLM` là cư trú mặc định của thiết kế** (D01 B: *"LTT-3.8 nóng mặc
#:       định"*), và llama-swap giữ hồ sơ ấy thường trú (`ttl: 0` + `preload`).
#:       Khai `LLM` ở lượt đầu là khai **hiện trạng**, không phải một mong muốn.
#:    3. **Tạo dòng KHÔNG phát lệnh nào.** Thứ nguy hiểm trên một card là lệnh
#:       `nap_llm`/`nha`/`free_comfy`, và cả ba chỉ phát từ các nhánh sau khi đã
#:       drain. Cấp một lease LLM lên card mà LTT-3.8 **đang** nằm sẵn là đúng
#:       hành vi của hôm qua, từng byte.
#:
#: ⚠️ Ứng viên còn lại — `XA_LLM` — mở cửa cho **không ai** và vẫn đi tiếp được
#:    cả hai đường, nên nó "an toàn hơn" theo nghĩa hẹp. Nhưng nó chỉ rời khỏi
#:    chỗ ấy qua `buoc_thuan`, và `buoc()` **không chuyển gì khi máy B câm** —
#:    tức máy B chết = cửa LTT-3.8 đóng vô hạn, đúng thảm hoạ ở (1). Chọn một
#:    trạng thái an toàn hơn ở đây là trả bằng chính thứ ta đang bảo vệ.
TRANG_THAI_KHOI_TAO = LLM

#: Trần số dòng `jobs` đọc về trong một lượt đếm. Mọi câu hỏi máy trạng thái đặt
#: cho hàng job là "> 0 chưa" hoặc "đã tới 4 chưa", nên một trần không đổi phán
#: quyết nào; nó chỉ chặn một lượt bước biến thành một phép quét toàn bảng khi
#: hàng đợi dồn.
TRAN_DEM_JOB = 200

#: Đệm (base_url, credential) của cổng LLM máy B trong bấy nhiêu giây. Trọng tài
#: chạy mỗi 2 s; hỏi `api_pool` mỗi lượt là ~43.000 lượt chọn khoá mỗi ngày cho
#: một câu trả lời đổi vài tháng một lần.
DEM_KHOA_S = 300.0

#: Tệp DANH TÍNH GPU của máy B — cùng tệp `llm_gateway/gpu_uuid.py` đọc (Task
#: 4.1). Đọc theo ĐƯỜNG DẪN, không `import llm_gateway`: gói ấy là của máy B và
#: không có mặt trong mọi bản cài (Task 6.1 §2 đo điều này cho `render_gateway`).
DUONG_DANH_TINH_GPU = (pathlib.Path(__file__).resolve().parents[2]
                       / "llm_gateway" / "deploy" / "gpu_may_b.json")

#: Vai của card mang nhóm cư trú trong tệp trên. Không phải tên app.
VAI_CARD_3090 = "ltt38"

#: Tên cửa ĐỒNG BỘ trong `llm_waiters.cua` — nhãn của nền tảng
#: (`server/api/{chat,streaming}.py` ghi nó), không phải của một app. Đây là tên
#: cửa DUY NHẤT trọng tài được phép biết; xem `_nguoi_cho_llm`.
CUA_DONG_BO = "sync"


class LoiMayB(Exception):
    """Không hỏi được máy B. Người gọi phải xử theo hướng KHÔNG hành động."""


# ── Cổng ra máy B ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TinMayB:
    """Bốn câu trả lời `QuanSat` cần từ máy B. `None` = **không đọc được**.

    ⛔ `None` không phải 0. `buoc_thuan` xử `None` theo hướng không hành động, và
       đó là toàn bộ giá trị của việc phân biệt hai thứ ở đây: một `0` bịa ra cho
       `inflight` là một lệnh `nha` phát lên một model đang sinh chữ cho khách.
    """

    llm_da_nap: bool | None
    inflight_llm: int | None
    vram_3090_mib: int | None
    nap_ket_qua: str = ""


class MayBResidency:
    """Các lệnh residency của máy B, theo hợp đồng Task 5.4 / 5.4a.

        GET  /v1/residency/trang_thai   (cổng LLM)    -> TinMayB
        POST /v1/residency/nha  {"model": …}          -> nhả model khỏi 3090
        POST /v1/residency/nap  {"model": …}          -> nạp lại LTT-3.8
        POST /v1/nha_comfy {"hanh_dong": "dung"}      -> dừng hẳn LTTComfyUI
        POST /v1/nha_comfy {"hanh_dong": "chay"}      -> bật lại LTTComfyUI

    ⭐ Lớp này là **cổng**, không phải chính sách: nó không biết trạng thái nào
       được phát lệnh nào. Nhờ vậy phép kiểm tiêm một máy B giả có đúng năm
       phương thức và chứng minh được cả chu trình mà không có máy B nào.

    ⚠️ Hai chiều của `nha_comfy` là MỘT cặp: cái dừng và cái bật lại. Thêm cái
       thứ nhất mà quên cái thứ hai là tắt vĩnh viễn phía ảnh.

    ⚠️ `nha`/`nap` trả **409** khi máy B từ chối (còn lượt đang chạy / VRAM chưa
       sạch) — đó là *"chưa tới lúc"*, **không** phải lỗi: cả ba lệnh idempotent
       và `buoc_thuan` phát lại ở lượt sau. `trang_thai()` và **hai lệnh ComfyUI**
       thì NÉM, vì cả ba trả lời câu "card có sạch/có sẵn sàng không" — một câu
       trả lời sai ở đó là một lần OOM hoặc một app ảnh chết câm.
    """

    def __init__(self, *, model_llm: str = "", gpu_uuid: str = "",
                 timeout_s: float = 10.0, timeout_comfy_s: float = 120.0,
                 goi_llm: Callable[..., Any] | None = None,
                 goi_render: Callable[..., Any] | None = None) -> None:
        self.model_llm = model_llm or _model_llm_mac_dinh()
        self.gpu_uuid = gpu_uuid or _uuid_card_3090()
        self.timeout_s = float(timeout_s)
        #: ⚠️ KHÔNG phải một hạn chờ thứ hai cạnh tranh với hạn của cổng render.
        #:    Cổng ấy tự chờ dịch vụ (`HAN_DOI_GIAY = 60 s`) rồi chờ VRAM tụt
        #:    (15 s) và **trả lời bằng số đo**; con số dưới đây chỉ là chốt chặn
        #:    của tầng vận chuyển, cố ý đặt cao hơn hẳn tổng ấy để phán quyết
        #:    luôn đến từ **thân trả lời**, không đến từ đồng hồ của máy A.
        self.timeout_comfy_s = float(timeout_comfy_s)
        self._goi_llm = goi_llm
        self._goi_render = goi_render

    # -- đọc ------------------------------------------------------------------
    def trang_thai(self) -> TinMayB:
        tin = self._llm("GET", "/v1/residency/trang_thai")
        if not isinstance(tin, dict):
            raise LoiMayB(f"trang_thai tra ve {type(tin).__name__}, khong phai dict")
        nap = tin.get("llm_da_nap")
        bay = tin.get("inflight")
        return TinMayB(
            llm_da_nap=bool(nap) if isinstance(nap, bool) else None,
            inflight_llm=(int(bay.get(self.model_llm, 0))
                          if isinstance(bay, dict) else None),
            vram_3090_mib=self._vram(tin.get("vram_mib")),
            nap_ket_qua=str(tin.get("nap_ket_qua") or ""),
        )

    # -- lệnh -----------------------------------------------------------------
    def nha(self) -> None:
        self._llm("POST", "/v1/residency/nha", {"model": self.model_llm},
                  cho_phep_409=True)

    def nap(self) -> None:
        self._llm("POST", "/v1/residency/nap", {"model": self.model_llm},
                  cho_phep_409=True)

    def free_comfy(self) -> None:
        """⚠️ Tên theo plan, NGHĨA theo L-14 §3 / R22: *làm cho VRAM 3090 sạch*.

        ComfyUI ấm giữ 223,5 MiB ngữ cảnh CUDA và `POST /free` **không** nhả nó,
        trong khi biên của LTT-3.8 ở `-c 221184` chỉ 445 MiB. Cổng render
        (Task 5.4a) **dừng hẳn dịch vụ LTTComfyUI** sau tên này; máy A không
        được tự đoán lại nghĩa ấy bằng một lệnh `/free` gọi thẳng.

        ⛔ THÀNH CÔNG IM LẶNG LÀ KẾT CỤC TỆ NHẤT. Cổng trả **503** kèm lý do khi
           nó không dừng được (nó phát hiện cả mã 1051 "còn dịch vụ phụ thuộc"),
           và nó xác minh bằng **VRAM đo lại** chứ không bằng lời của SCM. Nên
           non-200 — hoặc 200 mà `da_dung` không đúng — là "card CHƯA sạch", và
           ném ở đây là cách duy nhất để lượt bước không tưởng mình đã dọn xong.
           (Trạng thái vẫn ở `TRA_ANH`: `buoc_thuan` phát lệnh này **không kèm**
           một chuyển nào, nên một lần dừng hỏng tự nó đã không đổi gì.)
        """
        tra = self._render("POST", "/v1/nha_comfy", {"hanh_dong": "dung"})
        if not (isinstance(tra, dict) and tra.get("da_dung")):
            raise LoiMayB(f"nha_comfy(dung) khong xac nhan da dung: {tra!r}")

    def chay_comfy(self) -> None:
        """Bật LTTComfyUI trở lại — nửa còn lại của `free_comfy`.

        🔴 KHÔNG CÓ NỬA NÀY THÌ CHU TRÌNH LÀ MỘT CHIỀU: cửa sổ LLM mở ⇒ ComfyUI
           bị dừng ⇒ **không ai bật lại** ⇒ `BusyWatcher` báo card bận mãi và
           việc sinh ảnh không bao giờ trở lại. Tệ hơn hẳn bài toán D01 B sinh ra
           để giải.

        ⭐ Nó nằm ở chỗ máy trạng thái nói *"phía ảnh được cầm card từ đây"* —
           tức lối vào `ANH` — chứ không ở cuối cửa sổ LLM như một việc dọn dẹp.
           Khác biệt ấy quan trọng đúng lúc một lượt bước hỏng giữa chừng: đặt ở
           lối vào thì "chưa bật được" đồng nghĩa với "chưa vào `ANH`", nên cửa
           nhận job ảnh **chưa mở** — không có job nào được nhận vào một máy
           không có ComfyUI. Đặt ở cuối cửa sổ LLM thì hai điều ấy rời nhau.

        Idempotent: bật một dịch vụ đang chạy là một lượt xác nhận, không phải
        một lần khởi động lại (`dich_vu_comfy.chay_lai`).
        """
        tra = self._render("POST", "/v1/nha_comfy", {"hanh_dong": "chay"})
        if not (isinstance(tra, dict) and tra.get("dang_chay")):
            raise LoiMayB(f"nha_comfy(chay) khong xac nhan dang chay: {tra!r}")

    # -- đường dây ------------------------------------------------------------
    def _llm(self, method: str, path: str, than: dict | None = None,
             *, cho_phep_409: bool = False) -> Any:
        if self._goi_llm is not None:
            return self._goi_llm(method, path, than)
        return _goi_cong_llm(method, path, than, timeout_s=self.timeout_s,
                             cho_phep_409=cho_phep_409)

    def _render(self, method: str, path: str, than: dict | None = None) -> Any:
        if self._goi_render is not None:
            return self._goi_render(method, path, than)
        return _goi_cong_render(method, path, than, timeout_s=self.timeout_comfy_s)

    def _vram(self, bang: Any) -> int | None:
        """VRAM của **card mang nhóm cư trú**, tra theo UUID.

        ⛔ Không `max()` cả bảng: máy B có hai card, và LTT-3.5 giữ ~13 GB trên
           5060 Ti thường trực — lấy `max` là đọc VRAM của card không liên can
           rồi kết luận 3090 chưa sạch, tức không bao giờ nạp lại LTT-3.8. Đó
           đúng là khuyết tật Task 6.1 vừa gỡ khỏi `render_gateway/busy.py`.
        """
        if not isinstance(bang, dict) or not bang:
            return None
        if self.gpu_uuid and self.gpu_uuid in bang:
            return int(bang[self.gpu_uuid])
        if len(bang) == 1:
            return int(next(iter(bang.values())))
        log.error("khong biet UUID cua card 3090 (%d UUID trong bang, cau hinh "
                  "%r) => coi nhu KHONG DOC DUOC VRAM. Dat LTT_RESIDENCY_GPU_UUID "
                  "hoac de %s doc duoc.", len(bang), self.gpu_uuid,
                  DUONG_DANH_TINH_GPU.name)
        return None


def _model_llm_mac_dinh() -> str:
    """Id hồ sơ máy B của model cư trú 3090 — đọc, không gõ lại.

    `canonical.ALIAS_SANG_ID` là nơi bảng bí danh → id nội bộ đã sống; gõ
    `"qwen38-api"` ở đây là bản khai thứ hai của cùng một điều, và bản sao sẽ
    trôi đúng ngày đổi GGUF.
    """
    from platform_core.llm import canonical

    return canonical.ALIAS_SANG_ID[canonical.MODEL_MAC_DINH]


_UUID_3090: str | None = None


def _uuid_card_3090() -> str:
    """UUID card 3090: biến môi trường trước, rồi tệp danh tính của máy B.

    Rỗng nghĩa là *không biết* — và `_vram` xử "không biết" thành `None` chứ
    không thành một con số đoán.
    """
    global _UUID_3090
    if _UUID_3090 is not None:
        return _UUID_3090
    tu_env = (os.environ.get("LTT_RESIDENCY_GPU_UUID") or "").strip()
    if tu_env:
        _UUID_3090 = tu_env
        return _UUID_3090
    try:
        khai = json.loads(DUONG_DANH_TINH_GPU.read_bytes().decode("utf-8"))
        for card in khai:
            if str(card.get("vai") or "") == VAI_CARD_3090:
                _UUID_3090 = str(card.get("uuid") or "").strip()
                return _UUID_3090
    except Exception:  # noqa: BLE001 - thiếu tệp là chuyện bình thường ở máy A
        log.info("khong doc duoc %s; UUID 3090 phai den tu LTT_RESIDENCY_GPU_UUID",
                 DUONG_DANH_TINH_GPU, exc_info=True)
    _UUID_3090 = ""
    return _UUID_3090


_KHOA_DEM = threading.Lock()
_DEM_KHOA_LLM: tuple[float, str, str] | None = None


def _dia_chi_cong_llm() -> tuple[str, str]:
    """`(base_url, credential)` của cổng LLM máy B, đệm `DEM_KHOA_S` giây.

    ⛔ Khoá lấy qua `api_pool` như mọi provider khác — máy A không đọc bí mật từ
       biến môi trường (Q102). `base_url` của KHOÁ đi trước `base_url` của
       registry, cùng lý do đã ghi ở `dieu_phoi.goi`: registry đọc env, và env
       không có mặt trong một tiến trình chạy tay.
    """
    global _DEM_KHOA_LLM
    with _KHOA_DEM:
        dem = _DEM_KHOA_LLM
        if dem is not None and time.monotonic() - dem[0] < DEM_KHOA_S:
            return dem[1], dem[2]

    from platform_core import api_keys, api_pool, providers
    from platform_core.db import get_session
    from platform_core.llm import canonical
    from platform_core.models import APIKEY_CAT_CHAT

    pid = canonical.THU_TU_PROVIDER[0]
    gen = get_session()
    db = next(gen)
    try:
        key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                model=_model_llm_mac_dinh(), thu_tu_provider=[pid])
        cred = api_keys.lay_credential(db, key)
        base = ((getattr(key, "base_url", "") or "").strip()
                or (getattr(providers.get(pid), "base_url", "") or "").strip())
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    with _KHOA_DEM:
        _DEM_KHOA_LLM = (time.monotonic(), base, cred)
    return base, cred


def quen_dem_khoa() -> None:
    """Xoá đệm địa chỉ/khoá (phép kiểm và một lượt xoay khoá gọi hàm này)."""
    global _DEM_KHOA_LLM, _DEM_KHOA_RENDER, _UUID_3090
    with _KHOA_DEM:
        _DEM_KHOA_LLM = None
        _DEM_KHOA_RENDER = None
    _UUID_3090 = None


def _goi_cong_llm(method: str, path: str, than: dict | None, *, timeout_s: float,
                  cho_phep_409: bool) -> Any:
    import httpx

    base, cred = _dia_chi_cong_llm()
    if not base:
        raise LoiMayB("thieu base_url cong LLM may B (LTT_LLM_BASE_URL/khoa)")
    try:
        r = httpx.request(method, base.rstrip("/") + path,
                          headers={"Authorization": f"Bearer {cred}"} if cred else {},
                          json=than, timeout=timeout_s)
    except Exception as e:  # noqa: BLE001 - mạng hỏng là "không hỏi được"
        quen_dem_khoa()
        raise LoiMayB(f"{method} {path}: {type(e).__name__}") from e
    if r.status_code in (401, 403):
        quen_dem_khoa()                      # khoá vừa xoay ⇒ lượt sau lấy lại
    if cho_phep_409 and r.status_code == 409:
        log.info("may B tu choi %s (409) — chua toi luc, se phat lai", path)
        return {}
    if r.status_code >= 400:
        raise LoiMayB(f"{method} {path}: HTTP {r.status_code}")
    try:
        return r.json()
    except Exception as e:  # noqa: BLE001
        raise LoiMayB(f"{method} {path}: than khong phai JSON") from e


_DEM_KHOA_RENDER: tuple[float, str, str] | None = None


def _dia_chi_cong_render() -> tuple[str, str]:
    global _DEM_KHOA_RENDER
    with _KHOA_DEM:
        dem = _DEM_KHOA_RENDER
        if dem is not None and time.monotonic() - dem[0] < DEM_KHOA_S:
            return dem[1], dem[2]

    from platform_core import api_keys, api_pool, providers
    from platform_core.db import get_session
    from platform_core.image_gen.http_cong import PROVIDER
    from platform_core.models import APIKEY_CAT_IMAGE

    gen = get_session()
    db = next(gen)
    try:
        key = api_pool.chon_key(db, category=APIKEY_CAT_IMAGE,
                                thu_tu_provider=[PROVIDER])
        cred = api_keys.lay_credential(db, key)
        base = ((getattr(key, "base_url", "") or "").strip()
                or (getattr(providers.get(PROVIDER), "base_url", "") or "").strip())
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    with _KHOA_DEM:
        _DEM_KHOA_RENDER = (time.monotonic(), base, cred)
    return base, cred


def _goi_cong_render(method: str, path: str, than: dict | None, *,
                     timeout_s: float) -> Any:
    """Gọi một LỆNH RESIDENCY trên cổng render.

    ⛔ CỐ Ý KHÔNG ĐI QUA `image_gen.http_cong.goi_http`, dù đó là đường của mọi
       lượt vẽ. `goi_http` ghi telemetry `api_pool` cho từng lượt gọi, nên một
       **503 của lệnh dừng dịch vụ** sẽ bị đọc thành "khoá `ltt_image` hỏng":
       `danh_dau_loi` → cooldown → `disable` sau 5 lần, và model ảnh tự tắt vì
       một dịch vụ Windows không chịu dừng. Đó đúng là họ hàng của cạm bẫy D-005
       ghi thường trực ở `CLAUDE.md`, chỉ đổi chiều. Lệnh residency **không phải**
       một lượt dùng khoá; nó chỉ mượn khoá để xác thực.
    """
    import httpx

    base, cred = _dia_chi_cong_render()
    if not base:
        raise LoiMayB("thieu base_url cong render (LTT_RENDER_BASE_URL)")
    try:
        r = httpx.request(method, base.rstrip("/") + path,
                          headers={"Authorization": f"Bearer {cred}"} if cred else {},
                          json=than, timeout=timeout_s)
    except Exception as e:  # noqa: BLE001
        quen_dem_khoa()
        raise LoiMayB(f"{method} {path}: {type(e).__name__}") from e
    if r.status_code >= 400:
        # 503 mang theo lý do đọc được (`error.message`) — giữ nó trong ngoại lệ
        # để dòng log của trọng tài nói ra ai đang chặn, không chỉ nói "hỏng".
        raise LoiMayB(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
    try:
        return r.json()
    except Exception as loi:  # noqa: BLE001
        # ⛔ KHÔNG coi "200 mà thân không đọc được" là thành công. Cổng render
        #    trả bằng chứng (`da_dung` + VRAM đo lại) ở mọi đường ra; mất thân
        #    nghĩa là ta không có bằng chứng nào, và "tưởng đã dọn card" đúng là
        #    hỏng mà D01 B sinh ra để chặn. Mang theo `loi` vì ba nguyên nhân
        #    (proxy chèn HTML, thân rỗng, mã hoá lạ) cần ba việc sửa khác nhau.
        raise LoiMayB(f"{method} {path}: HTTP 200 nhung than khong phai JSON "
                      f"({loi!r}): {r.text[:200]!r}") from loi


# ── Bản khai của app: nhóm nào có những thành viên nào ───────────────────────

_BAN_DO_JOB: dict[str, dict[str, Any]] | None = None


def quen_ban_do_job() -> None:
    """Xoá đệm `{nhóm: {job_type: ToolSpec}}` (phép kiểm tiêm bản khai gọi nó)."""
    global _BAN_DO_JOB
    _BAN_DO_JOB = None


def thanh_vien(nhom: str) -> dict[str, str]:
    """`{vai_tro: tên tài nguyên}` của một nhóm GPU, đọc từ BẢN KHAI của app.

    ⛔ Dùng lại `admission._ban_do_cu_tru()` chứ không viết một bộ đọc thứ hai:
       cửa admission và trọng tài phải trả lời **cùng một câu** "tài nguyên nào
       thuộc nhóm nào, với vai gì". Hai bộ đọc là hai bản khai, và bản thứ hai sẽ
       trôi — đúng khuôn hỏng mà `nhom_cu_tru` đã ghi thành cảnh báo.
       `test_1219::test_trong_tai_doc_cung_ban_do_voi_admission` ghim tên hàm ấy,
       nên một lần đổi tên bên đó làm ĐỎ ở đây chứ không làm hỏng ở production.

    Hai tài nguyên khai cùng (nhóm, vai) ⇒ **ném**: đó là bản khai tự mâu thuẫn,
    và đoán bừa một trong hai là chọn nhầm card cho một nửa lưu lượng.
    """
    from platform_core.llm import admission

    ra: dict[str, str] = {}
    for ten, khai in admission._ban_do_cu_tru().items():
        for g, vai in khai:
            if g != nhom or not vai:
                continue
            cu = ra.setdefault(vai, ten)
            if cu != ten:
                raise ValueError(f"nhom {nhom!r} vai {vai!r} duoc khai cho hai "
                                 f"tai nguyen: {sorted((cu, ten))}")
    return ra


def cac_nhom() -> tuple[str, ...]:
    """Mọi nhóm cư trú app đang khai. Nền tảng **đọc**, không gõ tên nhóm.

    Hôm nay đúng một (`rtx3090`), và tên ấy nằm ở `apps/ltt_llm/ngan_sach.py` +
    ba manifest ảnh — không có một bản sao nào trong `platform_core`.
    """
    from platform_core.llm import admission

    ra = {g for khai in admission._ban_do_cu_tru().values() for g, _ in khai if g}
    return tuple(sorted(ra))


def _ban_do_job(nhom: str) -> dict[str, Any]:
    """`{job_type: ToolSpec}` của các tool có khai nhóm cư trú này.

    Lọc thô theo `job_type` để phép đếm chỉ đọc về những dòng job CÓ THỂ thuộc
    nhóm; vai trò thật của từng dòng vẫn giải theo `params["model"]` qua
    `registry.suc_chua_admission` — đúng hàm `job_runner` dùng để đòi lease, nên
    "cái ta đếm" và "cái sẽ xin lease" không thể lệch nhau.
    """
    global _BAN_DO_JOB
    if _BAN_DO_JOB is not None:
        return _BAN_DO_JOB.get(nhom, {})
    from platform_core.registry import discover

    ban_do: dict[str, dict[str, Any]] = {}
    try:
        for app in discover():
            if getattr(app, "error", None):
                continue
            for tool in getattr(app.manifest, "tools", ()) or ():
                jt = str(getattr(tool, "job_type", "") or "")
                if not jt:
                    continue
                for am in (getattr(tool, "admission_theo_model", {}) or {}).values():
                    g = str(getattr(am, "residency_group", "") or "").strip()
                    if g:
                        ban_do.setdefault(g, {})[jt] = tool
    except Exception:  # noqa: BLE001 - nói ra, đừng đệm một bản khai hỏng
        log.warning("khong doc duoc ban khai job cua nhom cu tru", exc_info=True)
        return {}
    _BAN_DO_JOB = ban_do
    return ban_do.get(nhom, {})


def _vai_cua_job(tool: Any, params: Any, nhom: str) -> str:
    from platform_core.registry import suc_chua_admission

    try:
        am = suc_chua_admission(tool, str((params or {}).get("model") or ""))
    except KeyError:
        return ""                      # bản khai không biết model này ⇒ không đếm
    if am is None or str(getattr(am, "residency_group", "") or "").strip() != nhom:
        return ""
    return str(getattr(am, "vai_tro", "") or "").strip()


# ── Khoá ─────────────────────────────────────────────────────────────────────

def _advisory(db: Any, khoa: str) -> None:
    """Khoá advisory của TRANSACTION hiện tại. SQLite bỏ qua (như `admission`)."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": khoa})


def _khoa(db: Any, nhom: str, tai_nguyen: dict[str, str]) -> None:
    """Giành `residency:<nhóm>` rồi hai khoá tài nguyên **theo thứ tự tên**.

    🔴 THỨ TỰ LÀ TOÀN BỘ NỘI DUNG CỦA HÀM NÀY. Cửa admission giành đúng một khoá
       (`llm-admission:<tài nguyên>`, `admission._khoa_resource`) rồi đọc dòng
       `gpu_residency` bên trong nó; trọng tài giành **cả hai** rồi ghi dòng ấy.
       Hai bên giành theo hai thứ tự khác nhau là một deadlock có thật giữa một
       lượt xin và một lượt lật cư trú. Một thứ tự cố định — và `sorted()` là
       cách duy nhất khiến nó không phụ thuộc vào thứ tự `dict` của bản khai.

    ⛔ Gọi `admission._khoa_resource` chứ không tự dựng chuỗi khoá: khoá phải
       TRÙNG từng ký tự với bên kia, và hai công thức là hai khoá khác nhau —
       tức không khoá gì cả, trong im lặng.
    """
    from platform_core.llm import admission

    _advisory(db, f"residency:{nhom}")
    for ten in sorted(tai_nguyen.values()):
        admission._khoa_resource(db, ten)


# ── Dòng `gpu_residency` ─────────────────────────────────────────────────────

def _aware(t: datetime | None) -> datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def _giay(t: datetime | None) -> float:
    d = _aware(t)
    return 0.0 if d is None else d.timestamp()


def _luc(giay: float) -> datetime | None:
    return None if not giay else datetime.fromtimestamp(giay, timezone.utc)


def _tu_dong(dong: Any) -> TrangThai:
    return TrangThai(ten=str(dong.trang_thai or ""), tu_luc=_giay(dong.tu_luc),
                     cua_so_bat_dau=_giay(dong.cua_so_bat_dau),
                     lan_nap_loi=int(dong.lan_nap_loi or 0))


def _doc_dong(db: Any, nhom: str, bay_gio: float) -> tuple[TrangThai, int]:
    """Đọc dòng, TẠO nếu chưa có. Trả `(trạng thái, phiên bản đã đọc)`.

    Bên gọi phải đang giữ khoá của `_khoa`.
    """
    from platform_core.models import GpuResidency

    dong = db.get(GpuResidency, nhom)
    if dong is None:
        dong = GpuResidency(nhom=nhom, trang_thai=TRANG_THAI_KHOI_TAO,
                            tu_luc=_luc(bay_gio) or datetime.now(timezone.utc),
                            cua_so_bat_dau=None, lan_nap_loi=0, phien_ban=0)
        db.add(dong)
        db.flush()
        log.warning("tao dong gpu_residency %r = %r (lan buoc dau tien cua nhom "
                    "nay). Truoc dong nay CA HAI cua admission dong.",
                    nhom, TRANG_THAI_KHOI_TAO)
    return _tu_dong(dong), int(dong.phien_ban or 0)


def _ghi_dong(db: Any, nhom: str, moi: TrangThai, phien_ban: int) -> bool:
    """Ghi kèm `phien_ban + 1`. `False` = một trọng tài khác đã ghi trước.

    Khoá lạc quan chứ không "đọc rồi gán": hai tiến trình worker chồng nhau (một
    lượt deploy) đọc cùng một dòng rồi cùng gán sẽ cùng thấy mình thắng, và
    **cùng phát lệnh** — hai lệnh `nha` cho một lần đổi cư trú. Kẻ thua ở đây
    không sửa gì và không phát gì; nó thử lại ở lượt sau với sự thật mới.
    """
    from sqlalchemy import update

    from platform_core.models import GpuResidency

    kq = db.execute(
        update(GpuResidency)
        .where(GpuResidency.nhom == nhom, GpuResidency.phien_ban == phien_ban)
        .values(trang_thai=moi.ten, tu_luc=_luc(moi.tu_luc),
                cua_so_bat_dau=_luc(moi.cua_so_bat_dau),
                lan_nap_loi=int(moi.lan_nap_loi), phien_ban=phien_ban + 1))
    return int(kq.rowcount or 0) == 1


# ── Quan sát ─────────────────────────────────────────────────────────────────

def _dem_lease(db: Any, resource: str) -> int:
    from sqlalchemy import func, select

    from platform_core.models import ExecutionLease

    if not resource:
        return 0
    return int(db.execute(select(func.count()).select_from(ExecutionLease)
                          .where(ExecutionLease.resource == resource)).scalar() or 0)


def _dem_job(db: Any, *, nhom: str, vai: str, trang_thai: str = "",
             tu_luc: datetime | None = None) -> int:
    """Đếm job của một VAI trong nhóm — theo bản khai, không theo tên app.

    ⛔ KHÔNG đếm theo cột `Job.admission_resource`. Cột ấy chỉ được ghi ở hai
       đường nộp có `registry.admission_luc_nop` (Public API, runtime nội bộ);
       ba app ảnh nộp job từ giao diện qua `job_submit.submit_with_credit` và để
       cột ấy **rỗng**. Còn `job_runner` thì đòi lease theo **bản khai của tool**
       chứ không theo cột. Đếm theo cột nghĩa là: job ảnh của giao diện bị cửa
       admission từ chối (vì nhóm đang ở `LLM`) trong khi trọng tài không thấy ai
       chờ nên không bao giờ mở cửa sổ ảnh — một bế tắc câm, và nó chỉ xảy ra với
       đúng đường mà khách thật đang đi.
    """
    from platform_core.models import Job

    ban_do = _ban_do_job(nhom)
    if not ban_do:
        return 0
    q = db.query(Job).filter(Job.job_type.in_(sorted(ban_do)))
    if trang_thai:
        q = q.filter(Job.status == trang_thai)
    if tu_luc is not None:
        q = q.filter(Job.admitted_at.isnot(None))
    n = 0
    for job in q.limit(TRAN_DEM_JOB).all():
        # So mốc thời gian TRONG PYTHON: SQLite trả naive, PostgreSQL trả aware,
        # và một phép so lẫn hai loại ở tầng SQL sai im lặng (`_aware`).
        if tu_luc is not None:
            luc = _aware(job.admitted_at)
            if luc is None or luc < tu_luc:
                continue
        if _vai_cua_job(ban_do[job.job_type], job.params, nhom) == vai:
            n += 1
    return n


def _nguoi_cho_llm(db: Any, resource: str, now: datetime) -> tuple[int, float | None]:
    """`(số người chờ còn sống, giây tới hạn chót SỚM NHẤT)` của cửa tương tác.

    ⭐ "Còn sống" theo đúng định nghĩa của phòng chờ (`phong_cho.HAN_NHIP_CHO_S`):
       một dòng mất nhịp là một tiến trình web đã chết, và đóng cửa sổ ảnh sớm vì
       một xác chết là nhường card cho không ai.

    Hạn chót = `created_at + trần chờ CỦA CỬA ẤY`. Hai trần, và chúng là **hai
    mặc định duy nhất tồn tại** trong mã chờ (`runtime_noi_bo/luong.py`): cửa
    đồng bộ 60 s (TD-7, `:426`), mọi cửa còn lại 300 s (D-06, `:537`, `:1042`).
    Một con số chung sẽ sai cho một nửa số người chờ — và sai về phía *"còn nhiều
    thời gian"* nghĩa là họ chết thật trong lúc ta vẽ thêm một ảnh.

    ⛔ PHÂN NHÁNH THEO ĐÚNG MỘT TÊN CỬA, VÀ TÊN ẤY LÀ CỦA NỀN TẢNG. `"sync"` do
       `server/api/{chat,streaming}.py` ghi; các cửa khác do **app** đặt tên
       (`apps/chatltt/chinh_sach.CUA`), và liệt kê chúng ở đây là đưa tên app vào
       `platform_core` — thứ `test_147` cấm và
       `test_1219::test_residency_khong_nhac_ten_app_trong_ma` bắt được.
       Rơi về trần stream cho cửa lạ không phải một phỏng đoán: đó là **mặc định
       của chính đường chờ** mà mọi cửa không-đồng-bộ đi qua.

    ⚠️ XẤP XỈ, và nói ra: bên gọi truyền được `han_s`/`tran_s` riêng, còn bảng
       `llm_waiters` **không lưu hạn chót**. Một cửa app tự đặt trần NGẮN hơn sẽ
       được ước là 300 s ⇒ cửa sổ ảnh đóng muộn hơn nó nên đóng. Cách sửa đúng
       là một cột hạn chót ghi lúc vào hàng (Task 6.3 sở hữu bảng ấy), không
       phải một bảng tên cửa ở đây.
    """
    from platform_core.llm import phong_cho, tham_so_da_luot
    from platform_core.models import LlmWaiter

    if not resource:
        return 0, None
    ts = tham_so_da_luot.doc()
    so = 0
    som_nhat: float | None = None
    for w in (db.query(LlmWaiter)
              .filter(LlmWaiter.resource == resource, LlmWaiter.trang_thai == "cho")
              .limit(TRAN_DEM_JOB).all()):
        nhip = _aware(w.heartbeat_at)
        if nhip is None or (now - nhip).total_seconds() > phong_cho.HAN_NHIP_CHO_S:
            continue
        so += 1
        tao = _aware(w.created_at) or now
        tran = (ts.cho_dong_bo_toi_da_s if str(w.cua or "") == CUA_DONG_BO
                else ts.cho_stream_toi_da_s)
        con = (tao - now).total_seconds() + tran
        som_nhat = con if som_nhat is None else min(som_nhat, con)
    return so, som_nhat


#: Số lần LIÊN TIẾP `chay_comfy()` hỏng, theo nhóm. **Trong tiến trình**, cố ý.
#:
#: ⭐ Vì sao không phải một cột CSDL: nó là một sự thật về *lượt gọi vừa rồi*,
#:    không phải trạng thái bền của nhóm. Một tiến trình chết rồi sống lại thì
#:    bộ đếm về 0 — và đó là hành vi ĐÚNG: khởi động lại worker là một lượt thử
#:    lại tự nhiên, đúng lúc người vận hành vừa đụng vào máy.
#:
#: ⚠️ Nhiều worker ⇒ mỗi worker một bộ đếm riêng, nên đường lui có thể tới muộn
#:    hơn `tran_vao_anh_hong` lượt. Chậm hơn, không sai — và đổi lại là không
#:    thêm một cột phải giữ đồng bộ giữa các tiến trình.
#: Giá trị là CẶP `(so_lan, luc_hong_cuoi)` — mốc thời gian đi kèm vì thiếu nó
#: thì bộ đếm chỉ tăng được mà không nhạt đi (L-10). Xem `duoc_thu_anh`.
_LAN_VAO_ANH_HONG: dict[str, tuple[int, float]] = {}


def _quan_sat(db: Any, *, nhom: str, tt: TrangThai, tai_nguyen: dict[str, str],
              tin: TinMayB, bay_gio: float) -> QuanSat:
    from platform_core.models import JOB_QUEUED

    now = datetime.fromtimestamp(bay_gio, timezone.utc)
    res_llm = tai_nguyen.get(MAC_DINH, "")
    res_anh = tai_nguyen.get(THEO_LO, "")
    cho, han = _nguoi_cho_llm(db, res_llm, now)
    cua_so = _luc(tt.cua_so_bat_dau)
    return QuanSat(
        lease_llm=_dem_lease(db, res_llm),
        lease_anh=_dem_lease(db, res_anh),
        job_anh_cho=_dem_job(db, nhom=nhom, vai=THEO_LO, trang_thai=JOB_QUEUED),
        anh_bat_dau_trong_cua_so=(
            _dem_job(db, nhom=nhom, vai=THEO_LO, tu_luc=cua_so)
            if cua_so is not None else 0),
        nguoi_cho_llm=cho + _dem_job(db, nhom=nhom, vai=MAC_DINH,
                                     trang_thai=JOB_QUEUED),
        han_chot_llm_s=han,
        gateway_inflight_llm=tin.inflight_llm,
        llm_da_nap=tin.llm_da_nap,
        vram_3090_mib=tin.vram_3090_mib,
        nap_ket_qua=tin.nap_ket_qua,
    )


# ── Một bước của trọng tài ───────────────────────────────────────────────────

_PHAT = {
    NHA_LLM_LENH: lambda may_b: may_b.nha(),
    NAP_LLM_LENH: lambda may_b: may_b.nap(),
    FREE_COMFY_LENH: lambda may_b: may_b.free_comfy(),
}


#: Bao lau moi nhac lai ĐẦY ĐỦ mot loi cu tru lap di lap lai (giay).
#:
#: 🔴 VI SAO CAN: `buoc()` chay MOI NHIP BAO TRI (2 giay, tren MOI worker).
#:    Khi may B khong cau hinh — may dev, CSDL test, hay may A truoc khi co khoa
#:    cong — dieu kien loi dung O MOI NHIP, va mot `exc_info=True` moi lan la mot
#:    traceback day du moi 2 giay tren moi tien trinh.
#:
#:    Do duoc 12/09: `check_multiproc` (3 worker) chay 9 job thumbnail chi xong 2
#:    trong cua so thoi gian — khong lease nao bi giu, khong advisory lock nao,
#:    moi ket noi idle. Vong lap worker khong bi KHOA, no bi LAM CHAM boi chinh
#:    dong log cua ta.
#:
#: ⛔ Day KHONG phai "giam on cho de nhin". Mot dong log lap 30 lan/phut vua
#:    lam cham vong lap vua chon moi dong khac — tuc no lam HONG ca hai viec ma
#:    log sinh ra de lam.
#:
#: ⭐ Cung khuon `admission.NHAC_LOI_CU_TRU_S` dang dung cho cung hang loi.
NHAC_TRACEBACK_S = 300.0

#: {nhom: thoi diem monotonic da nhac day du lan cuoi}
_da_nhac_tb: dict[str, float] = {}


def _nhac_mot_lan(nhom: str, bay_gio: float) -> bool:
    """Lan nay co duoc in traceback day du khong? (cua so `NHAC_TRACEBACK_S`)"""
    cu = _da_nhac_tb.get(nhom)
    if cu is not None and bay_gio - cu < NHAC_TRACEBACK_S:
        return False
    _da_nhac_tb[nhom] = bay_gio
    return True


def buoc(db: Any, *, nhom: str, may_b: MayBResidency | None = None,
         ts: ThamSoResidency | None = None,
         bay_gio: Callable[[], float] = time.time) -> TrangThai:
    """MỘT lượt trọng tài cho một nhóm GPU. Trả về trạng thái SAU lượt này.

    Ba giai đoạn, và thứ tự của chúng là ba quyết định riêng:

    1. **Dòng phải tồn tại — kể cả khi máy B câm.** Không có dòng ⇒ luật 0 đóng
       CẢ HAI cửa (Task 5.3), nên một trọng tài chỉ tạo dòng sau khi đọc được máy
       B sẽ biến một máy B im lặng thành "LTT-3.8 ngừng bán". Xem
       `TRANG_THAI_KHOI_TAO`.
    2. **Hỏi máy B NGOÀI khoá.** Giữ khoá `llm-admission:*` trong lúc chờ một
       lượt HTTP là bắt mọi lượt xin của khách xếp hàng sau máy B. Quan sát vì
       thế cũ hơn quyết định vài chục mili giây — và điều đó AN TOÀN ở đây vì
       mọi lệnh nguy hiểm chỉ phát từ trạng thái đã ĐÓNG cửa của bên kia:
       `nha` chỉ phát từ `XA_LLM` (không lượt LLM mới nào vào được nữa, nên
       `inflight` chỉ giảm), `nap`/`free_comfy` chỉ từ `TRA_ANH`/`LOI_NAP`
       (không lượt vẽ mới nào vào được nữa). Một quan sát cũ ở đây chỉ sai về
       phía *chờ thêm một lượt*.
       ⛔ `trang_thai` ném ⇒ **không chuyển gì, không phát gì**, chỉ một dòng
          cảnh báo. Một lần chuyển trên sự thật không biết là cách cả hai model
          cùng tin mình sở hữu card.
    3. **Quyết trong khoá, ghi bằng `phien_ban + 1`, rồi mới phát lệnh.** Kẻ
       thua khoá lạc quan không phát lệnh nào — nhờ vậy "đúng một lệnh `nha` cho
       một lần đổi cư trú" đúng cả khi hai worker cùng chạy vòng bảo trì.
    4. **Một lệnh đi TRƯỚC lời khai: bật lại ComfyUI ở lối vào `ANH`.** Mọi lệnh
       khác đi sau lời khai vì chúng chỉ *thi hành* một cư trú đã chốt; lệnh này
       là **điều kiện** của cư trú mới, nên nó phải thành công trước khi cửa nhận
       job ảnh mở. Xem `MayBResidency.chay_comfy`.

    ⚠️ Hàm này **commit** `db`: khoá advisory của transaction chỉ nhả ở commit,
       và giữ chúng qua một lượt HTTP phát lệnh là chặn cửa admission trong suốt
       lượt ấy.
    """
    ts = ts or ThamSoResidency()
    may_b = may_b if may_b is not None else MayBResidency()
    tai_nguyen = thanh_vien(nhom)

    _khoa(db, nhom, tai_nguyen)
    tt, _ = _doc_dong(db, nhom, bay_gio())
    db.commit()

    try:
        tin = may_b.trang_thai()
    except Exception as loi:  # noqa: BLE001 - fail-closed: KHÔNG chuyển, và nói ra
        # ⚠️ Traceback ĐẦY ĐỦ một lần rồi rút gọn — xem `NHAC_TRACEBACK_S`. Hướng
        #    xử lý không đổi: không chuyển trạng thái, không phát lệnh nào.
        if _nhac_mot_lan(nhom, bay_gio()):
            log.warning("khong hoi duoc may B ve cu tru %r => giu nguyen %r, khong "
                        "phat lenh nao (fail-closed)", nhom, tt.ten, exc_info=True)
        else:
            log.warning("khong hoi duoc may B ve cu tru %r (%s) => giu nguyen %r",
                        nhom, type(loi).__name__, tt.ten)
        return tt

    _khoa(db, nhom, tai_nguyen)
    t = bay_gio()
    tt, phien_ban = _doc_dong(db, nhom, t)
    qs = _quan_sat(db, nhom=nhom, tt=tt, tai_nguyen=tai_nguyen, tin=tin, bay_gio=t)
    _so_lan, _luc_hong = _LAN_VAO_ANH_HONG.get(nhom, (0, 0.0))
    qs = replace(qs, lan_vao_anh_hong=_so_lan, luc_anh_hong_cuoi=_luc_hong)
    moi, lenh = buoc_thuan(tt, qs, ts, t)

    if moi.ten == ANH and tt.ten != ANH:
        # 🔴 LỐI VÀO `ANH` = "phía ảnh được cầm card từ đây" ⇒ ComfyUI phải SỐNG
        #    trước khi cửa nhận job ảnh mở. `free_comfy` đã **dừng hẳn** dịch vụ
        #    (5.4a), nên không có bước này thì chu trình là một chiều: ComfyUI
        #    tắt vĩnh viễn, `BusyWatcher` báo card bận mãi, việc sinh ảnh không
        #    bao giờ trở lại.
        #
        # ⛔ Bật KHÔNG được ⇒ **không chuyển**. Ở lại `NHA_LLM` là trạng thái
        #    không mở cửa cho ai, nên không job ảnh nào bị nhận vào một máy
        #    không có ComfyUI; lượt sau thử lại (lệnh idempotent).
        #
        # ⚠️ Nhả khoá TRƯỚC lượt gọi: cổng render tự chờ dịch vụ tới 60 s, và giữ
        #    `llm-admission:*` suốt ngần ấy là bắt mọi lượt xin của khách xếp
        #    hàng sau một dịch vụ Windows. Sau khi bật xong, đọc lại dòng: trạng
        #    thái đổi trong lúc ấy (một trọng tài khác) ⇒ bỏ lượt này, tính lại ở
        #    lượt sau với sự thật mới.
        db.rollback()
        try:
            may_b.chay_comfy()
        except Exception:  # noqa: BLE001
            # 🔴 ĐẾM. Không đếm thì `tran_vao_anh_hong` là một tham số không ai
            #    đặt được, và `NHA_LLM` giữ nguyên ngõ cụt đã gây L-07: một cổng
            #    render cũ làm 3090 nằm không vô hạn, im lặng với mọi người trừ
            #    dòng log này.
            #
            # ⏱️ Và GHI GIỜ cùng lúc: `duoc_thu_anh` đo từ mốc này. Đếm mà không
            #    ghi giờ thì bộ đếm không nhạt đi được, và đó đúng là L-10.
            n = _LAN_VAO_ANH_HONG.get(nhom, (0, 0.0))[0] + 1
            _LAN_VAO_ANH_HONG[nhom] = (n, t)
            log.error("khong bat lai duoc ComfyUI (lan %d lien tiep) => KHONG vao "
                      "%s (cu tru %s van o %s); tu lan %d se TRA CARD cho LLM, "
                      "thu lai sau %.0fs",
                      n, ANH, nhom, tt.ten, ThamSoResidency().tran_vao_anh_hong,
                      lui_anh_s(replace(qs, lan_vao_anh_hong=n),
                                ThamSoResidency()),
                      exc_info=(n == 1))
            return tt
        # ⭐ Bật được ⇒ đặt lại về 0. Một bộ đếm chỉ tăng sẽ khoá phía ảnh vĩnh
        #    viễn sau ba lần trục trặc thoáng qua trong cả đời tiến trình.
        #
        # ⚠️ Đây KHÔNG còn là đường xoá duy nhất (L-10 đã chứng minh một đường
        #    xoá duy nhất nằm sau chính cái phanh là không xoá được bao giờ);
        #    `duoc_thu_anh` cho một lượt thử theo nhịp, và chính lượt ấy mới đưa
        #    dòng chạy tới được đây. Hai cái đi cùng nhau, thiếu một là hỏng.
        _LAN_VAO_ANH_HONG.pop(nhom, None)
        _khoa(db, nhom, tai_nguyen)
        lai, phien_ban = _doc_dong(db, nhom, bay_gio())
        if lai != tt:
            db.commit()
            return lai

    if moi != tt:
        if not _ghi_dong(db, nhom, moi, phien_ban):
            db.rollback()
            log.info("mat luot ghi cu tru %r (phien ban %d da cu) — khong phat "
                     "lenh, thu lai luot sau", nhom, phien_ban)
            return tt
        log.info("cu tru %s: %s -> %s%s", nhom, tt.ten, moi.ten,
                 f" (lenh {'+'.join(lenh)})" if lenh else "")
    db.commit()

    for ten_lenh in lenh:
        try:
            _PHAT[ten_lenh](may_b)
        except Exception:  # noqa: BLE001 - lệnh idempotent, lượt sau phát lại
            log.warning("lenh %r toi may B that bai (cu tru %s = %s); se phat lai",
                        ten_lenh, nhom, moi.ten, exc_info=True)
    return moi


def buoc_dinh_ky(may_b: MayBResidency | None = None) -> None:
    """Một lượt trọng tài cho MỌI nhóm cư trú app đang khai. KHÔNG BAO GIỜ NÉM.

    Đây là mặt tiếp xúc duy nhất của vòng bảo trì `job_runner` (chu kỳ 2 s), nên
    nó phải chịu được mọi thứ hỏng: một ngoại lệ ở đây sẽ cắt phần còn lại của
    lượt bảo trì (dọn dữ liệu, webhook, báo động) chứ không chỉ cắt trọng tài.

    ⚠️ Một `MayBResidency` cho mọi nhóm chỉ đúng vì hôm nay có **đúng một** nhóm.
       Ngày có nhóm thứ hai, id hồ sơ máy B phải đi theo nhóm — dòng cảnh báo
       dưới đây là chỗ ngày ấy sẽ tự nói ra.
    """
    from platform_core.db import get_session

    try:
        nhom_ds = cac_nhom()
    except Exception:  # noqa: BLE001
        log.warning("khong doc duoc danh sach nhom cu tru", exc_info=True)
        return
    if len(nhom_ds) > 1:
        log.warning("co %d nhom cu tru (%s) nhung chi mot cong may B duoc cau "
                    "hinh — id ho so phai di theo nhom", len(nhom_ds), nhom_ds)
    for nhom in nhom_ds:
        gen = get_session()
        db = next(gen)
        try:
            buoc(db, nhom=nhom, may_b=may_b)
        except Exception:  # noqa: BLE001
            log.exception("buoc trong tai cu tru %r that bai", nhom)
            try:
                db.rollback()
            except Exception as loi:  # noqa: BLE001
                # Ba nguyên nhân khác nhau (mất kết nối, phiên đã đóng, khoá) và
                # ba việc sửa khác nhau — nên in ra cái nào, đừng chỉ nói "hỏng".
                log.warning("khong rollback duoc sau khi buoc %r hong: %r",
                            nhom, loi)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
