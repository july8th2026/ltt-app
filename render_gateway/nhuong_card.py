"""
nhuong_card.py — xin card trước khi vẽ, và trả card sau khi vẽ. (V1–V4)

🔴 VÌ SAO PHẢI CÓ. Máy B có **một** card 24.576 MB, và mỗi model nhà chiếm 75–78 %
   của nó khi thường trú:

       HiDream đỉnh khi vẽ    18.450 MB   (đo 100 lượt, D-056)
       Qwen3.8-27B thường trú 19.237 MB   (đo 5 lần, 24/08)
       ----------------------------------
       tổng                   37.687 MB   trên 24.576 MB

   Hai model **không bao giờ cùng lúc được**, kể cả khi một bên ngồi im. Nên swap
   không phải một tối ưu hoá — nó là **chế độ vận hành duy nhất**. D-057 đóng
   đường tách chúng ra hai máy, nên việc này thành **bắt buộc**.

⭐ THIẾT KẾ CHO **N HỘ**, KHÔNG PHẢI HAI. Đây là chỗ dễ làm sai nhất, và bản đầu
   trong đầu tôi đã sai đúng như vậy: "cổng render gọi llama-swap nhả" — một cái
   bắt tay hai bên, với tên hộ kia viết cứng.

   D-037 đã ghi máy B có **BA hộ ngay hôm nay**: ① dự án video (dùng chung đúng
   ComfyUI đó), ② LLM, ③ ta. Và chủ sản phẩm chốt 24/08 rằng **dự án video sau này
   sẽ đi theo đúng khuôn của LLM và ảnh** — tức là hộ thứ tư, thứ năm là chuyện
   khi nào chứ không phải có hay không.

   ⇒ Thêm một hộ phải là **một dòng cấu hình**, không phải một lần sửa mã.

⛔ VÀ CÓ HAI LOẠI HỘ, KHÁC NHAU VỀ BẢN CHẤT:

     · hộ **BẢO ĐƯỢC** (`duong_nha` có giá trị) — ta gọi được endpoint nhả của nó.
       Ví dụ `llama-swap GET /unload`.
     · hộ **CHỈ CHỜ ĐƯỢC** (`duong_nha` rỗng) — không có cách nào bảo nó nhả.
       Dự án video hôm nay là loại này: một người đang chạy việc trên đó, và một
       lượt từng chạy **72,5 phút**.

   Trộn hai loại này là lỗi thiết kế. Với loại thứ hai, hành động đúng **không
   bao giờ** là đuổi — mà là **báo bận và lùi lại**.

⛔ BẬN KHÔNG PHẢI HỎNG (D-005). Xin card không được ⇒ **429**, không bao giờ 5xx.
   Máy A coi 5xx là *hỏng* và `disable` khoá sau 5 lần; một tối chạy video sẽ tự
   tắt vĩnh viễn model nhà.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

log = logging.getLogger(__name__)

#: VRAM phải xuống dưới mức này mới coi là "card đã trống cho ta".
#:
#: HiDream cần 18.450 MB. Card có 24.576. Nên trước khi nạp, phần người khác giữ
#: phải dưới ~6.000 MB — cộng thêm biên cho nền desktop (đo trên máy B:
#: 1.263–1.328 MB khi không ai chạy gì).
VRAM_TRONG_TOI_DA_MB = 6_000

#: Chờ tối đa bao lâu cho card trống. Vượt thì **báo bận**, không chạy tiếp.
#:
#: 45 giây: dài hơn thời gian một hộ bảo-được nhả (đo được 0,7 s cho llama-swap,
#: cộng thời gian driver thu hồi), và ngắn hơn nhiều so với để khách treo. Nếu
#: sau 45 giây card vẫn đầy thì gần như chắc chắn có hộ **chỉ-chờ-được** đang
#: chạy, và câu trả lời đúng cho khách là "đang bận", không phải chờ thêm.
HAN_CHO_GIAY = 45.0

#: Nhịp đọc lại VRAM trong khi chờ.
NHIP_DOC_GIAY = 1.0

#: Khoảng cách tối thiểu giữa HAI LẦN ĐUỔI. Trong khoảng này, job ảnh **chờ**
#: thay vì đuổi tiếp.
#:
#: 🔴 VÌ SAO CẦN, VÀ ĐÂY LÀ TRƯỜNG HỢP DUY NHẤT CƠ CHẾ NÀY CÓ THỂ TỆ.
#:
#:    Bình thường không có dao động: Qwen **không** bị nhả sau mỗi request — nó
#:    thường trú (`ttl` 1.800 s) và chỉ bị đuổi khi có job ảnh. Một phiên viết mã
#:    không có job ảnh nào thì Qwen nạp **một lần** (18 s) rồi mọi lượt sau là
#:    0,7–1,2 s.
#:
#:    Nhưng nếu **hai loại việc xen kẽ nhau**:
#:
#:        job ảnh → đuổi Qwen → vẽ 111 s → khách gõ prompt → nạp Qwen 18 s
#:                → job ảnh → đuổi Qwen → ... 
#:
#:    thì **mỗi prompt của khách trả 18 giây**. Đó không phải chậm — đó là không
#:    dùng được.
#:
#: ⇒ Chốt này biến "dao động của LLM" thành "job ảnh xếp hàng", và đó là đánh đổi
#:   ĐÚNG: job ảnh là **bất đồng bộ** (có hàng đợi, khách không ngồi chờ), còn
#:   lượt LLM là **đồng bộ** (khách đang nhìn con trỏ nhấp nháy).
#:
#: ⚠️ Và nó **không** làm chậm trường hợp thường: nếu Qwen không nạp lại thì VRAM
#:    vẫn thấp, `xin_card` đi qua ngay ở nhánh đầu và **không đuổi ai cả**. Một lô
#:    30 ảnh liên tiếp vì thế chạy trọn, không chạm chốt này lần nào.
#:
#: 300 giây: khách LLM trả 18 s **nhiều nhất một lần mỗi 5 phút**, và job ảnh chờ
#: nhiều nhất 5 phút — chấp nhận được cho một việc vốn mất gần 2 phút để chạy.
CACH_NHAU_TOI_THIEU_GIAY = 300.0


@dataclass(frozen=True)
class HoDung:
    """Một hộ dùng chung card.

    `duong_nha` rỗng nghĩa là **chỉ chờ được, không bảo được** — xem docstring đầu
    tệp. Đừng đặt một đường nhả giả để cho đủ trường.
    """
    ten: str
    duong_nha: str = ""
    #: Ước lượng phần nó giữ, **chỉ để ghi log cho người đọc**. Không dùng để
    #: quyết định gì — quyết định luôn dựa trên VRAM đọc thật.
    uoc_giu_mb: int = 0

    @property
    def bao_duoc(self) -> bool:
        return bool(self.duong_nha.strip())


@dataclass
class SoDuoi:
    """Nhớ lần đuổi gần nhất, để không đuổi liên tục. Xem `CACH_NHAU_TOI_THIEU_GIAY`."""
    cach_nhau_giay: Optional[float] = None
    now: Callable[[], float] = time.monotonic
    lan_cuoi: Optional[float] = None

    def _cach(self) -> float:
        return (CACH_NHAU_TOI_THIEU_GIAY if self.cach_nhau_giay is None
                else self.cach_nhau_giay)

    def duoc_duoi(self) -> bool:
        if self.lan_cuoi is None:
            return True
        return (self.now() - self.lan_cuoi) >= self._cach()

    def con_lai_giay(self) -> float:
        if self.lan_cuoi is None:
            return 0.0
        return max(0.0, self._cach() - (self.now() - self.lan_cuoi))

    def ghi(self) -> None:
        self.lan_cuoi = self.now()


@dataclass(frozen=True)
class PhanXuXinCard:
    duoc: bool
    vram_mb: Optional[int]
    giay_da_cho: float
    ly_do: str = ""
    #: Tên những hộ đã được bảo nhả trong lượt này.
    da_bao_nha: tuple = ()

    def as_dict(self) -> dict:
        return {"duoc": self.duoc, "vram_mb": self.vram_mb,
                "giay_da_cho": round(self.giay_da_cho, 1),
                "ly_do": self.ly_do, "da_bao_nha": list(self.da_bao_nha)}


def xin_card(*, ho_khac: Sequence[HoDung],
             doc_vram: Callable[[], Optional[int]],
             goi_nha: Callable[[str], bool],
             nguong_mb: Optional[int] = None,
             han_giay: Optional[float] = None,
             nhip_giay: Optional[float] = None,
             so_duoi: Optional["SoDuoi"] = None,
             now: Callable[[], float] = time.monotonic,
             ngu: Callable[[float], None] = time.sleep) -> PhanXuXinCard:
    """Bảo các hộ bảo-được nhả, rồi **CHỜ VÀ XÁC MINH** VRAM xuống dưới ngưỡng.

    🔴 ĐÂY LÀ HÀM QUAN TRỌNG NHẤT CỦA TỆP, VÀ LÝ DO LÀ BƯỚC "XÁC MINH".

       Gọi endpoint nhả rồi nạp luôn là **giả định**. Nếu model kia chưa thật sự
       rời VRAM, model mới **âm thầm** offload một phần sang RAM chủ — và mọi chốt
       sống/chết vẫn xanh trong khi tốc độ giảm 3–10 lần. Đó là bài học P6 và
       D-051, và ngày 24/08 tôi tự dính đúng nó khi đo: gọi LLM trong lúc ComfyUI
       còn giữ model, card lên **23.860 MB**, và tôi **suýt kết luận sai** rằng
       LLM đang hỏng.

    ⛔ KHÔNG ĐỌC ĐƯỢC VRAM ⇒ **TỪ CHỐI**, không cho qua.

       Đây là chỗ duy nhất trong dự án mà "không biết" phải xử như "không được",
       ngược với `tren_gpu.kiem` (nơi không-biết là im lặng). Lý do khác nhau:
       ở đó ta **quan sát** và một cảnh báo sai làm chết kênh cảnh báo; ở đây ta
       **sắp tiêu GPU và tiêu tiền của khách**, và chạy mù là cách tạo ra đúng
       cái sự cố im lặng vừa nói ở trên.
    """
    # ⚠️ ĐỌC HẰNG SỐ Ở ĐÂY, KHÔNG ĐẶT LÀM THAM SỐ MẶC ĐỊNH.
    #    Tham số mặc định được tính **lúc định nghĩa hàm**, nên
    #    `monkeypatch.setattr(nhuong_card, "HAN_CHO_GIAY", 2)` sẽ **không ăn** —
    #    và test sẽ ngồi chờ 45 giây thật. Đã dính: một test mất 3 phút 45 vì
    #    đúng chuyện này. Cùng lớp lỗi với QT-12.
    nguong_mb = VRAM_TRONG_TOI_DA_MB if nguong_mb is None else nguong_mb
    han_giay = HAN_CHO_GIAY if han_giay is None else han_giay
    nhip_giay = NHIP_DOC_GIAY if nhip_giay is None else nhip_giay

    t0 = now()
    da_bao: list[str] = []

    # ── Card đã trống ⇒ ĐI LUÔN, không đuổi ai ──────────────────────────────
    # Đây là nhánh của trường hợp thường, và nó nằm TRƯỚC mọi thứ khác vì lý do
    # nghiệp vụ: một lô ảnh liên tiếp không được đuổi ai, và không được chạm chốt
    # chống dao động dưới đây.
    vram0 = doc_vram()
    if vram0 is None:
        return PhanXuXinCard(
            False, None, 0.0,
            "khong doc duoc nvidia-smi — TU CHOI, khong chay mu", ())
    if vram0 <= nguong_mb:
        return PhanXuXinCard(True, vram0, 0.0, "", ())

    # ── Có người giữ card. Được đuổi lần nữa chưa? ──────────────────────────
    if so_duoi is not None and not so_duoi.duoc_duoi():
        con = so_duoi.con_lai_giay()
        return PhanXuXinCard(
            False, vram0, 0.0,
            f"vua duoi cach day chua du {so_duoi._cach():.0f}s — cho them "
            f"{con:.0f}s de khong lam khach LLM tra 18s nap lai moi luot. "
            f"VRAM dang {vram0} MB.", ())

    for ho in ho_khac:
        if not ho.bao_duoc:
            # Hộ chỉ-chờ-được: KHÔNG bảo, và cũng không coi là lỗi. Xem docstring
            # đầu tệp — với dự án video, đuổi là phá việc của người khác.
            log.debug("ho %r chi cho duoc, khong bao nha", ho.ten)
            continue
        if goi_nha(ho.duong_nha):
            da_bao.append(ho.ten)
            if so_duoi is not None:
                so_duoi.ghi()
        else:
            # Bảo không được cũng không phải lỗi chí tử: có thể nó đã nhả sẵn.
            # Vòng chờ dưới đây mới là thứ quyết định.
            log.info("bao ho %r nha khong thanh cong — van cho VRAM", ho.ten)

    while True:
        vram = doc_vram()
        if vram is None:
            return PhanXuXinCard(
                False, None, now() - t0,
                "khong doc duoc nvidia-smi — TU CHOI, khong chay mu",
                tuple(da_bao))
        if vram <= nguong_mb:
            return PhanXuXinCard(True, vram, now() - t0, "", tuple(da_bao))
        if now() - t0 >= han_giay:
            con = ", ".join(h.ten for h in ho_khac if not h.bao_duoc) or "khong ro"
            return PhanXuXinCard(
                False, vram, now() - t0,
                f"het {han_giay:.0f}s ma VRAM con {vram} MB (> {nguong_mb}). "
                f"Gan nhu chac chan mot ho chi-cho-duoc dang chay ({con}).",
                tuple(da_bao))
        ngu(nhip_giay)


def doc_ho_tu_env(env: dict) -> tuple:
    """Danh sách hộ dùng chung, đọc từ biến môi trường.

    ⭐ Đây là chỗ "thêm một hộ = một dòng cấu hình" thành thật. Khai bằng
       `LTT_HO_DUNG_CARD`, các mục cách nhau bằng `;`, mỗi mục `ten=duong_nha`
       (bỏ trống `duong_nha` cho hộ chỉ-chờ-được):

           LTT_HO_DUNG_CARD=llm=http://127.0.0.1:8280/unload;video=

    ⚠️ Không khai thì trả về **rỗng**, và `xin_card` khi đó chỉ còn làm một việc:
       **xác minh VRAM**. Đó là hành vi đúng cho một cài đặt dev không có hộ nào —
       và nó vẫn giữ được phần quan trọng nhất của hàm.
    """
    tho = str(env.get("LTT_HO_DUNG_CARD") or "").strip()
    if not tho:
        return ()
    ra = []
    for muc in tho.split(";"):
        muc = muc.strip()
        if not muc:
            continue
        ten, _, duong = muc.partition("=")
        ten = ten.strip()
        if ten:
            ra.append(HoDung(ten=ten, duong_nha=duong.strip()))
    return tuple(ra)


@dataclass
class TraCard:
    """Nhả VRAM của ComfyUI sau khi RẢNH một lúc — không nhả ngay sau mỗi job.

    ⭐ VÌ SAO CHỜ, KHÔNG NHẢ NGAY. Nạp lại HiDream tốn 0,8 giây (đo: 110,5 s lạnh
       so với 109,7 s ấm). Rẻ, nhưng một lô 30 ảnh liên tiếp thì thành 24 giây
       tiêu không vì gì. Chờ một khoảng rồi mới nhả cho lô liên tiếp đi trọn.

    ⭐ VÀ VÌ SAO PHẢI NHẢ. Nếu không, ComfyUI ngồi im mà giữ ~16.600 MB — đo được
       trên máy B lúc GPU 0–1 % tải. Lúc đó LLM cần 19.237 MB và chỉ còn ~7.900:
       nó sẽ nạp đè, card lên 23.860 MB, và **cả hai** cùng chậm.

    ⛔ KHÔNG nhả khi còn job đang chạy. `co_viec()` phải hỏi hàng đợi thật, không
       hỏi một cờ nội bộ.
    """
    #: Rảnh bao lâu thì nhả. 60 giây: dài hơn khoảng nghỉ giữa hai job của một lô
    #: liên tiếp, ngắn hơn mức làm LLM chờ thấy.
    ranh_bao_lau_giay: float = 60.0
    co_viec: Callable[[], bool] = lambda: False
    goi_free: Callable[[], bool] = lambda: False
    now: Callable[[], float] = time.monotonic
    _ranh_tu: Optional[float] = field(default=None, init=False)
    _da_nha: bool = field(default=False, init=False)

    def mot_luot(self) -> bool:
        """Gọi định kỳ. Trả `True` nếu vừa nhả trong lượt này."""
        if self.co_viec():
            self._ranh_tu = None
            self._da_nha = False
            return False
        if self._da_nha:
            return False
        if self._ranh_tu is None:
            self._ranh_tu = self.now()
            return False
        if self.now() - self._ranh_tu < self.ranh_bao_lau_giay:
            return False
        ok = self.goi_free()
        # Đánh dấu đã nhả **dù gọi hỏng**: nếu không thì mỗi nhịp lại gọi lại một
        # endpoint đang lỗi, và log ngập. Có job mới sẽ đặt lại cờ này.
        self._da_nha = True
        if ok:
            log.info("da nha VRAM cua ComfyUI sau %.0fs ranh", self.ranh_bao_lau_giay)
        else:
            log.warning("goi ComfyUI /free khong thanh cong — LLM co the phai nap de")
        return ok
