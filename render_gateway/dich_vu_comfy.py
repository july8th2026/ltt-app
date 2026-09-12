"""
dich_vu_comfy.py — DỪNG và CHẠY LẠI dịch vụ `LTTComfyUI` bằng SCM của Windows.

🔴 VÌ SAO TỆP NÀY TỒN TẠI, VÀ VÌ SAO NÓ KHÔNG PHẢI `POST /free`.

   `POST /free {"unload_models": true, "free_memory": true}` nhả **trọng số** của
   ComfyUI. Nó **không** nhả **ngữ cảnh CUDA** của tiến trình — đo 12/09/2026
   (L-14 §3, `docs/ltt_llm_dual/DECISION_LOG.md`): một ComfyUI **ấm mà ngồi im**
   vẫn giữ **223,5 MiB** trên card, và chỉ **dừng hẳn tiến trình** mới trả lại.

   Con số ấy sẽ là chuyện vặt nếu biên còn rộng. Nó không rộng: LTT-3.8 ở cấu
   hình đã chốt (`-c 221184 -np 3`, mmproj trên GPU) chiếm 24.131/24.576 MiB —
   **biên 445 MiB**. 223,5 trên 445 là **một nửa biên**, tiêu cho một tiến trình
   không làm gì. ⇒ Trong cửa sổ LLM, ComfyUI phải **tắt**, không phải "đã `/free`".

⛔ VÀ ĐÂY KHÔNG PHẢI "GIẾT VIỆC ĐANG CHẠY" (L-9). Lệnh này chỉ thu hồi bộ nhớ
   **của chính ComfyUI**, và nó được phát bởi **trọng tài residency ở máy A**
   (Task 5.5) đúng ở trạng thái `TRA_ANH`, tức sau khi cửa nhận job ảnh đã đóng
   **và** không còn lượt vẽ nào chạy. Cổng render **không** tự quyết định —
   nó không được thêm một người quyết thứ hai (TD-D10).

⚠️ HAI CẠM BẪY ĐÃ ĐO TRÊN MÁY B, CẢ HAI ĐỀU LÀM "THÀNH CÔNG GIẢ":

   1. **Dịch vụ báo `Stopped` mà ComfyUI thật vẫn sống.**
      `E:\\AI\\venv\\Scripts\\python.exe` là một **stub 274 KB**; nó sinh ra
      `...\\Python312\\python.exe` mới là ComfyUI thật (giữ model + VRAM). Đo
      22/08: PID 8564 (3,8 MB) → PID 13912 (2.265 MB). Nếu chỉ giết tiến trình
      cha thì SCM nói "Stopped" trong khi card vẫn bị ôm.
      ⇒ Vì vậy hàm `dung()` **không tin SCM**: nó đọc lại VRAM của **đúng card
      3090** và **đòi thấy VRAM tụt**. Chính chú thích trong
      `render_gateway/deploy/cai_dat_dich_vu.ps1` đã dặn *"KHONG TIN, HAY DO"* —
      tệp này biến lời dặn ấy thành cơ chế.

   2. **`LTTRenderGateway` PHỤ THUỘC `LTTComfyUI`.**
      `cai_dat_dich_vu.ps1` đặt `DependOnService LTTComfyUI`. SCM **từ chối**
      dừng một dịch vụ còn dịch vụ phụ thuộc đang chạy: `ControlService` trả
      `ERROR_DEPENDENT_SERVICES_RUNNING` (**1051**). Nghĩa là cổng render — chính
      kẻ phát lệnh — là thứ chặn lệnh của mình.
      ⇒ `MA_PHU_THUOC` được nhận diện riêng và thông điệp lỗi **nói thẳng cách
      sửa**, vì một mã 1051 trần trụi trong log không tự giải thích được.
      Đường sửa nằm ở deploy, không ở đây: `nssm reset LTTRenderGateway
      DependOnService` (hoặc `sc config LTTRenderGateway depend= `).

⛔ IM LẶNG THÀNH CÔNG LÀ KẾT CỤC TỆ NHẤT. Một bước residency tưởng đã dọn card mà
   thật ra chưa dọn sẽ nạp 16 GB đè lên phần ComfyUI còn giữ, và **cả hai** cùng
   chậm trong khi mọi chốt vẫn xanh (P6, D-051). Nên mọi đường ra ở đây hoặc là
   *"đã dừng, VRAM đã tụt, đây là số"*, hoặc là **một lỗi có lý do đọc được**.

⭐ `sc.exe` chứ không `nssm.exe`: `sc.exe` luôn có trong `System32`, còn đường của
   `nssm.exe` là một giả định về bố cục máy B (`E:\\AI\\ltt_render\\scripts\\`).
   Cả hai đều gọi cùng một SCM nên hành vi giống nhau — kể cả lỗi 1051. Đổi công
   cụ được bằng `LTT_SC_EXE` mà không phải deploy lại mã.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger("render_gateway.dich_vu_comfy")

#: Tên dịch vụ ComfyUI trên máy B (`cai_dat_dich_vu.ps1`).
TEN_DICH_VU_MAC_DINH = "LTTComfyUI"

BIEN_TEN_DICH_VU = "LTT_COMFY_DICH_VU"
BIEN_CONG_CU = "LTT_SC_EXE"

#: Chờ tối đa bao lâu cho SCM chuyển xong trạng thái.
#: 60 s: `AppThrottle` của nssm là 5 s và ComfyUI phải nhả ~16 GB VRAM; dài hơn
#: hẳn mức thường (đo: vài giây) mà vẫn ngắn hơn trần chờ của người gọi.
HAN_DOI_GIAY = 60.0
NHIP_GIAY = 1.0

#: Hết giờ cho **một** lệnh `sc.exe`. SCM tự nó chỉ chờ ~30 s.
HET_GIO_LENH_S = 30.0

# ── Mã lỗi Win32 mà ta phải phân biệt ─────────────────────────────────────────
#
# ⚠️ `sc.exe` **không** trả mã Win32 qua exit code trong mọi vỏ: đo trên máy này,
#    `sc stop <khong-co>` in `[SC] OpenService FAILED 1060:` và thoát 1060 (bash
#    cắt còn 36). Nên ta đọc **cả hai**: chuỗi `FAILED <n>` trước, exit code sau.
MA_TU_CHOI = 5              # ERROR_ACCESS_DENIED
MA_PHU_THUOC = 1051         # ERROR_DEPENDENT_SERVICES_RUNNING
MA_KHONG_CO_DICH_VU = 1060  # ERROR_SERVICE_DOES_NOT_EXIST
MA_CHUA_CHAY = 1062         # ERROR_SERVICE_NOT_ACTIVE — dừng cái đã dừng: KHÔNG lỗi
MA_DANG_CHAY = 1056         # ERROR_SERVICE_ALREADY_RUNNING — chạy cái đã chạy: KHÔNG lỗi

# Trạng thái dịch vụ, theo số của SCM (`SERVICE_STATUS.dwCurrentState`).
DUNG, CHAY = "STOPPED", "RUNNING"
TEN_TRANG_THAI: dict[int, str] = {
    1: DUNG, 2: "START_PENDING", 3: "STOP_PENDING", 4: CHAY,
    5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED",
}


@dataclass(frozen=True)
class KetQuaLenh:
    """Kết quả thô của một lệnh `sc.exe`."""
    ma: int
    ra: str = ""


#: Chạy một lệnh. Tiêm được để test không đụng SCM thật.
ChayLenh = Callable[[list[str]], KetQuaLenh]


def ten_dich_vu(env: Optional[dict] = None) -> str:
    e = os.environ if env is None else env
    return (e.get(BIEN_TEN_DICH_VU) or "").strip() or TEN_DICH_VU_MAC_DINH


def _cong_cu() -> str:
    rieng = (os.environ.get(BIEN_CONG_CU) or "").strip()
    if rieng:
        return rieng
    return shutil.which("sc") or r"C:\Windows\System32\sc.exe"


def chay_that(doi_so: list[str]) -> KetQuaLenh:
    """Gọi `sc.exe` thật. Không ném — mọi hỏng hóc thành một `KetQuaLenh`."""
    try:
        r = subprocess.run([_cong_cu(), *doi_so], capture_output=True, text=True,
                           timeout=HET_GIO_LENH_S, encoding="utf-8",
                           errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("khong chay duoc sc.exe %s: %s", " ".join(doi_so), e)
        return KetQuaLenh(-1, f"{type(e).__name__}: {e}")
    return KetQuaLenh(int(getattr(r, "returncode", 1) or 0),
                      (r.stdout or "") + (r.stderr or ""))


_RE_FAILED = re.compile(r"FAILED\s+(\d+)")
#: `        STATE              : 4  RUNNING`
#: Chỉ nhận số **một chữ số** + tên trong bảng: dòng `TYPE : 30  WIN32` cùng hình
#: dạng nhưng không phải trạng thái, và đọc nhầm nó là đọc sai cả phép đo.
_RE_TRANG_THAI = re.compile(r":\s*([1-7])\s+([A-Z_]+)")


def ma_loi(kq: KetQuaLenh) -> int:
    """Mã Win32 của một lệnh hỏng. `0` = không thấy dấu hiệu hỏng."""
    m = _RE_FAILED.search(kq.ra or "")
    if m:
        return int(m.group(1))
    return kq.ma if kq.ma > 0 else 0


def _doc_trang_thai(ra: str) -> Optional[str]:
    for so, ten in _RE_TRANG_THAI.findall(ra or ""):
        goi_y = TEN_TRANG_THAI.get(int(so))
        if goi_y and goi_y == ten:
            return goi_y
    return None


def trang_thai(ten: str, *, chay: ChayLenh = chay_that) -> Optional[str]:
    """Trạng thái dịch vụ, hoặc `None` = **không biết**.

    ⛔ `None` khác `STOPPED`. Người gọi phải phân biệt "đã dừng" với "không đọc
       được" — cùng luật đã dùng cho `nvidia-smi` ở `busy.py`.
    """
    kq = chay(["query", ten])
    if ma_loi(kq):
        return None
    return _doc_trang_thai(kq.ra)


def _doi(ten: str, muon: str, *, chay: ChayLenh, han_giay: float,
         nhip_giay: float, now: Callable[[], float],
         ngu: Callable[[float], None]) -> Optional[str]:
    t0 = now()
    while True:
        tt = trang_thai(ten, chay=chay)
        if tt == muon:
            return tt
        if now() - t0 >= han_giay:
            return tt
        ngu(nhip_giay)


@dataclass(frozen=True)
class PhanXuDichVu:
    """Kết quả một lượt đổi trạng thái dịch vụ."""
    xong: bool
    trang_thai: Optional[str]
    #: Trạng thái **trước khi** ta chạm vào. Người gọi cần nó để biết có nên đòi
    #: VRAM tụt hay không: dừng một dịch vụ vốn đã dừng thì không có gì để tụt.
    truoc: Optional[str] = None
    ma: int = 0
    ly_do: str = ""

    def as_dict(self) -> dict:
        return {"xong": self.xong, "trang_thai": self.trang_thai,
                "truoc": self.truoc, "ma": self.ma, "ly_do": self.ly_do}


def dich_vu_phu_thuoc_dang_chay(ten: str, *,
                                chay: ChayLenh = chay_that) -> list[str]:
    """Tên những dịch vụ **phụ thuộc** `ten` và **đang chạy**.

    ⭐ Có mặt chỉ để thông điệp lỗi tự giải thích ngay lần hỏng ĐẦU TIÊN. Một dòng
       log nói *"ma 1051"* buộc người đọc đi tra Win32; một dòng nói *"1051, kẻ
       chặn là LTTRenderGateway"* thì xong việc ngay tại đó. `sc enumdepend` chỉ
       **đọc**, không đổi gì.
    """
    kq = chay(["enumdepend", ten])
    if ma_loi(kq):
        return []
    ra: list[str] = []
    ten_hien: Optional[str] = None
    for dong in (kq.ra or "").splitlines():
        d = dong.strip()
        if d.upper().startswith("SERVICE_NAME:"):
            ten_hien = d.split(":", 1)[1].strip()
        elif ten_hien and "STATE" in d.upper():
            if _doc_trang_thai(d) == CHAY:
                ra.append(ten_hien)
            ten_hien = None
    return ra


def _ly_do_ma(ma: int, ten: str, viec: str, *,
              chay: ChayLenh = chay_that) -> str:
    if ma == MA_PHU_THUOC:
        ke_chan = dich_vu_phu_thuoc_dang_chay(ten, chay=chay)
        ai = ", ".join(ke_chan) if ke_chan else "khong doc duoc danh sach"
        return (f"SCM tu choi {viec} {ten}: ma 1051 "
                f"(ERROR_DEPENDENT_SERVICES_RUNNING) — co dich vu PHU THUOC dang "
                f"chay: {ai}. Tren may B do la chinh LTTRenderGateway "
                f"(cai_dat_dich_vu.ps1:205 dat DependOnService {ten}), tuc cong "
                f"render la thu chan chinh lenh cua no. Sua o buoc deploy: "
                f"`nssm reset LTTRenderGateway DependOnService`.")
    if ma == MA_TU_CHOI:
        return (f"SCM tu choi {viec} {ten}: ma 5 (ACCESS_DENIED) — tien trinh cong "
                f"render khong co quyen dieu khien dich vu nay.")
    if ma == MA_KHONG_CO_DICH_VU:
        return (f"khong co dich vu ten {ten!r} (ma 1060). Dat {BIEN_TEN_DICH_VU} "
                f"cho dung ten.")
    return f"sc.exe {viec} {ten} that bai, ma {ma}."


def dung(ten: Optional[str] = None, *, chay: ChayLenh = chay_that,
         han_giay: float = HAN_DOI_GIAY, nhip_giay: float = NHIP_GIAY,
         now: Callable[[], float] = time.monotonic,
         ngu: Callable[[float], None] = time.sleep) -> PhanXuDichVu:
    """Dừng hẳn dịch vụ ComfyUI. **Không** trả `xong=True` nếu chưa chắc đã dừng."""
    ten = ten or ten_dich_vu()
    truoc = trang_thai(ten, chay=chay)
    if truoc is None:
        return PhanXuDichVu(
            False, None, None, 0,
            f"khong doc duoc trang thai dich vu {ten} — KHONG bao la da dung. "
            f"Chay `sc query {ten}` tren may B de xem vi sao.")
    if truoc == DUNG:
        return PhanXuDichVu(True, DUNG, DUNG, 0, "")

    kq = chay(["stop", ten])
    ma = ma_loi(kq)
    # Dừng một dịch vụ đã dừng không phải lỗi — nó là đích ta muốn tới.
    if ma and ma != MA_CHUA_CHAY:
        return PhanXuDichVu(False, trang_thai(ten, chay=chay), truoc, ma,
                            _ly_do_ma(ma, ten, "dung", chay=chay))

    tt = _doi(ten, DUNG, chay=chay, han_giay=han_giay, nhip_giay=nhip_giay,
              now=now, ngu=ngu)
    if tt != DUNG:
        return PhanXuDichVu(
            False, tt, truoc, 0,
            f"da gui lenh dung {ten} nhung sau {han_giay:.0f}s trang thai van la "
            f"{tt!r}.")
    return PhanXuDichVu(True, DUNG, truoc, 0, "")


def chay_lai(ten: Optional[str] = None, *, chay: ChayLenh = chay_that,
             han_giay: float = HAN_DOI_GIAY, nhip_giay: float = NHIP_GIAY,
             now: Callable[[], float] = time.monotonic,
             ngu: Callable[[float], None] = time.sleep) -> PhanXuDichVu:
    """Bật lại ComfyUI — nửa còn lại của lệnh, và nó **bắt buộc phải có**.

    ⭐ Một lệnh chỉ biết tắt sẽ tắt vĩnh viễn tầng sinh ảnh: trọng tài mở cửa sổ
       `ANH` rồi gửi job vẽ tới một ComfyUI không còn chạy, và cổng render sẽ
       báo bận mãi mãi (`BusyWatcher` coi ComfyUI không trả lời là bận). Nên
       chiều bật nằm **cùng một endpoint**, không phải một việc tay.
    """
    ten = ten or ten_dich_vu()
    truoc = trang_thai(ten, chay=chay)
    if truoc == CHAY:
        return PhanXuDichVu(True, CHAY, CHAY, 0, "")

    kq = chay(["start", ten])
    ma = ma_loi(kq)
    if ma and ma != MA_DANG_CHAY:
        return PhanXuDichVu(False, trang_thai(ten, chay=chay), truoc, ma,
                            _ly_do_ma(ma, ten, "chay", chay=chay))

    tt = _doi(ten, CHAY, chay=chay, han_giay=han_giay, nhip_giay=nhip_giay,
              now=now, ngu=ngu)
    if tt != CHAY:
        return PhanXuDichVu(
            False, tt, truoc, 0,
            f"da gui lenh chay {ten} nhung sau {han_giay:.0f}s trang thai van la "
            f"{tt!r}.")
    return PhanXuDichVu(True, CHAY, truoc, 0, "")
