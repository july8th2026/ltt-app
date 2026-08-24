"""
theo_doi_luot.py — lấy mẫu VRAM **và RAM** TRONG LÚC job chạy, không chỉ chờ kết quả.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — MỘT LỖ THẬT, PHÁT HIỆN 24/08.

   `deploy/chay_baseline.py` (đường **ĐO**) lấy **198 mẫu mỗi job**: VRAM, nhiệt,
   điện, throttle. `runner.py` (đường **KHÁCH DÙNG**) lấy **không mẫu nào**.

   Tức là bộ đo canh rất cẩn thận, còn thứ khách trả tiền để dùng thì chạy mù. Và
   đó đúng là chỗ tệ nhất để mù, vì:

⭐ MÔ HÌNH ĐÚNG: trọng số nằm trên **đĩa**; **page cache của RAM** giữ một bản sau
   lần đọc đầu; nạp là copy **RAM → VRAM** qua PCIe; job chạy **hoàn toàn trong
   VRAM**. Đo được: nạp lại HiDream **0,8 giây** cho 15,6 GB ≈ 20 GB/s — tốc độ
   RAM, không phải tốc độ đĩa.

⛔ NHƯNG CÓ MỘT TRƯỜNG HỢP XẤU TRÔNG GIỐNG HỆT. Khi VRAM không đủ, ComfyUI và
   llama.cpp **không báo lỗi** — chúng giữ một phần trọng số trong RAM và **bơm
   từng lớp qua PCIe suốt job**. Lúc đó:

     · job **vẫn xong**, ảnh **vẫn đúng**;
     · `/health` **vẫn xanh**, ComfyUI **vẫn `alive`**;
     · chỉ chậm đi 3–10 lần.

   Đó là sự cố P6 (18,2 tok/s thay vì 63,3 vì card bẩn) và cùng họ với D-051. Và
   với ảnh nó **khó thấy hơn hẳn bên chữ**: một lượt vẽ vốn đã mất 110 giây, nên
   "chậm gấp ba" trông giống hệt "máy đang bận" — thứ ta đã dạy mọi người coi là
   bình thường.

   ⇒ **Không thể phát hiện bằng cách chờ kết quả.** Phải đo trong lúc chạy.

⭐ HAI ĐẠI LƯỢNG, VÌ MỘT MÌNH VRAM KHÔNG ĐỦ:

     · **VRAM** — nếu job chạy đủ lâu mà VRAM **không lên tới ngưỡng đã biết** thì
       model không thường trú đủ. Đây là bản *một phần* của chốt `tren_gpu.kiem`
       (chốt đó chỉ bắt trường hợp *toàn phần*: VRAM < 5 GB).
     · **RAM còn trống** — nếu nó sụt trong lúc job chạy thì có hộ khác đang ăn bộ
       nhớ chủ, và mọi phép offload sẽ thrash. `BusyWatcher` đã kiểm RAM **trước**
       khi nhận job, nhưng không kiểm **trong lúc** chạy.

⛔ VÀ TỆP NÀY KHÔNG BAO GIỜ TỪ CHỐI GÌ. Nó **quan sát** và **ghi lại**. Một job
   đang chạy chậm thì để nó chạy xong — huỷ giữa đường là biến một sự cố hiệu năng
   thành một sự cố mất việc. Việc của nó là làm sự cố **nhìn thấy được**, và để lại
   bằng chứng trong kết quả job để hôm sau còn truy được.
"""
from __future__ import annotations

import logging
import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)

#: Nhịp lấy mẫu. 2 giây trên một job 110 giây ⇒ ~55 mẫu: đủ để thấy hình dạng,
#: nhẹ đủ để không tự làm chậm việc đang đo.
NHIP_MAU_GIAY = 2.0

#: VRAM tối thiểu phải thấy khi job đã chạy đủ lâu.
#:
#: Đo thật 100 lượt t2i 50 bước 2560×1440: đỉnh **18.287–18.450 MB**, dao động chỉ
#: 163 MB. Nên 15.000 là ngưỡng ĐỦ THẤP để không báo nhầm ở pha nạp/VAE, và ĐỦ CAO
#: để bắt được việc model chỉ thường trú một phần.
#:
#: ⚠️ Chế độ tham chiếu cao hơn (`subject` 2 ảnh @4 MP đo được 20.114 MB), nên
#:    ngưỡng này là **sàn chung**, không phải hình dạng của từng chế độ.
VRAM_TOI_THIEU_KHI_CHAY_MB = 15_000

#: Chỉ kết luận khi job đã chạy đủ lâu để loại trừ pha nạp trọng số và pha VAE.
#: 90 giây: dài hơn toàn bộ phần chuẩn bị đo được, ngắn hơn một lượt vẽ (110 s)
#: nên sự cố bị bắt ngay trong lượt đầu.
CHAY_LAU_TOI_THIEU_S = 90.0

#: RAM còn trống dưới mức này trong lúc chạy là đáng lo: mọi phép offload sẽ thrash.
RAM_TRONG_TOI_THIEU_GB = 8.0


@dataclass(frozen=True)
class MauDo:
    giay: float
    vram_mb: Optional[int]
    ram_trong_gb: Optional[float]


@dataclass(frozen=True)
class TomTatLuot:
    so_mau: int
    giay: float
    vram_dinh_mb: Optional[int] = None
    vram_trung_vi_mb: Optional[int] = None
    vram_thap_nhat_mb: Optional[int] = None
    ram_trong_thap_nhat_gb: Optional[float] = None
    #: `None` = **không biết** (chưa đủ lâu, hoặc không đọc được). Đừng biến
    #: "không biết" thành "không sao".
    thuong_tru_du: Optional[bool] = None
    canh_bao: tuple = ()

    def as_dict(self) -> dict:
        return {"so_mau": self.so_mau, "giay": round(self.giay, 1),
                "vram_dinh_mb": self.vram_dinh_mb,
                "vram_trung_vi_mb": self.vram_trung_vi_mb,
                "vram_thap_nhat_mb": self.vram_thap_nhat_mb,
                "ram_trong_thap_nhat_gb": self.ram_trong_thap_nhat_gb,
                "thuong_tru_du": self.thuong_tru_du,
                "canh_bao": list(self.canh_bao)}


def tom_tat(mau, *, vram_toi_thieu_mb: Optional[int] = None,
            lau_toi_thieu_s: Optional[float] = None,
            ram_toi_thieu_gb: Optional[float] = None) -> TomTatLuot:
    """Dựng tóm tắt từ danh sách mẫu. Hàm **thuần** — test được không cần GPU.

    ⚠️ Đọc hằng số ở đây, không đặt làm tham số mặc định: tham số mặc định tính
       lúc định nghĩa hàm nên `monkeypatch` sẽ không ăn (cùng lớp lỗi với QT-12).
    """
    vram_toi_thieu_mb = (VRAM_TOI_THIEU_KHI_CHAY_MB if vram_toi_thieu_mb is None
                         else vram_toi_thieu_mb)
    lau_toi_thieu_s = (CHAY_LAU_TOI_THIEU_S if lau_toi_thieu_s is None
                       else lau_toi_thieu_s)
    ram_toi_thieu_gb = (RAM_TRONG_TOI_THIEU_GB if ram_toi_thieu_gb is None
                        else ram_toi_thieu_gb)

    mau = list(mau)
    if not mau:
        return TomTatLuot(0, 0.0)

    giay = mau[-1].giay
    vram = [m.vram_mb for m in mau if m.vram_mb is not None]
    ram = [m.ram_trong_gb for m in mau if m.ram_trong_gb is not None]
    canh_bao: list[str] = []

    dinh = max(vram) if vram else None
    ram_min = min(ram) if ram else None

    # ── Chốt "model có thường trú đủ không" ─────────────────────────────────
    thuong_tru: Optional[bool] = None
    if giay < lau_toi_thieu_s:
        # Chưa đủ lâu để loại trừ pha nạp. KHÔNG kết luận.
        pass
    elif dinh is None:
        canh_bao.append("khong doc duoc VRAM lan nao trong ca luot")
    elif dinh < vram_toi_thieu_mb:
        thuong_tru = False
        canh_bao.append(
            f"VRAM dinh chi {dinh} MB sau {giay:.0f}s chay (< {vram_toi_thieu_mb}) "
            f"— model gan nhu chac chan CHI THUONG TRU MOT PHAN, va luot nay cham "
            f"hon binh thuong nhieu lan")
    else:
        thuong_tru = True

    # ── Chốt RAM ────────────────────────────────────────────────────────────
    if ram_min is not None and ram_min < ram_toi_thieu_gb:
        canh_bao.append(
            f"RAM con trong tut xuong {ram_min:.1f} GB (< {ram_toi_thieu_gb}) "
            f"trong luc chay — moi phep offload se thrash")

    return TomTatLuot(
        so_mau=len(mau), giay=giay,
        vram_dinh_mb=dinh,
        vram_trung_vi_mb=int(statistics.median(vram)) if vram else None,
        vram_thap_nhat_mb=min(vram) if vram else None,
        ram_trong_thap_nhat_gb=round(ram_min, 1) if ram_min is not None else None,
        thuong_tru_du=thuong_tru, canh_bao=tuple(canh_bao))


@dataclass
class NguoiTheoDoi:
    """Lấy mẫu trong một luồng riêng suốt thời gian job chạy.

    Dùng như context manager:

        with NguoiTheoDoi(doc_vram=..., doc_ram=...) as td:
            ...chay job...
        tt = td.tom_tat()
    """
    doc_vram: Callable[[], Optional[int]]
    doc_ram_trong_gb: Callable[[], Optional[float]]
    nhip_giay: float = NHIP_MAU_GIAY
    now: Callable[[], float] = time.monotonic
    _mau: list = field(default_factory=list, init=False)
    _dung: threading.Event = field(default_factory=threading.Event, init=False)
    _luong: Optional[threading.Thread] = field(default=None, init=False)
    _t0: float = field(default=0.0, init=False)

    def __enter__(self) -> "NguoiTheoDoi":
        self._t0 = self.now()
        self._luong = threading.Thread(target=self._chay, name="theo-doi-luot",
                                       daemon=True)
        self._luong.start()
        return self

    def __exit__(self, *_exc) -> bool:
        self._dung.set()
        if self._luong is not None:
            # Chờ có hạn: một luồng lấy mẫu không bao giờ được giữ job lại.
            self._luong.join(timeout=self.nhip_giay * 2)
        return False

    def _chay(self) -> None:
        while not self._dung.is_set():
            try:
                self._mau.append(MauDo(self.now() - self._t0,
                                       self.doc_vram(), self.doc_ram_trong_gb()))
            except Exception:                                   # noqa: BLE001
                # ⛔ Một lỗi khi lấy mẫu KHÔNG được làm hỏng job đang chạy. Ghi
                #    một mẫu rỗng để vẫn thấy có khoảng trống, rồi đi tiếp.
                self._mau.append(MauDo(self.now() - self._t0, None, None))
                log.debug("lay mau loi", exc_info=True)
            self._dung.wait(self.nhip_giay)

    def tom_tat(self, **kw) -> TomTatLuot:
        return tom_tat(self._mau, **kw)
