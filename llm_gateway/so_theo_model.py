"""
so_theo_model.py — **một sổ cho MỖI model**. Tải 3.8 không bao giờ lấy suất 3.5.

🔴 VÌ SAO KHÔNG THỂ DÙNG MỘT `GioiHan` CHUNG. Từ 09/2026 cổng này phục vụ hai
   model chạy trên **hai card khác nhau** của máy B:

     qwen38-api   RTX 3090     `-c`/`-np` của hồ sơ trong `llama-swap.yaml`
     qwen35-api   RTX 5060 Ti  `-c`/`-np` của hồ sơ trong `llama-swap.yaml`

   (⛔ không chép số vào đây — `SoTheoModel.tu_vat_ly` đọc thẳng tệp đó.)

   Một sổ chung nói *"đang chạy 3/3, đầy"* trong khi **cả ba** lượt ấy nằm trên
   3090 và 5060 Ti hoàn toàn rảnh. Tức nó từ chối một lượt mà phần cứng dư sức
   phục vụ — và nó từ chối bằng 429, thứ máy A hiểu là "bận", nên khách đi ra
   đám mây trong khi card thứ hai ngồi không.

   Chiều ngược lại tệ hơn: gộp hai bể KV thành một con số thì bể của 3090
   (nhỏ hơn) được tính bằng bể lớn hơn, và khi KV cạn thì
   `server-context.cpp:3688-3724` **huỷ MỌI slot** chứ không chỉ slot gây ra —
   một khách làm rơi lượt của hai khách khác. Xem `gioi_han.token_pool`.

⭐ NÊN "ĐỘC LẬP" Ở ĐÂY KHÔNG PHẢI MỘT THUỘC TÍNH ĐẸP, NÓ LÀ CẢ MỤC ĐÍCH. Phép
   kiểm `tests/test_1221_gateway_so_theo_model.py` có đối chứng đúng chiều đó:
   tiêm **một** `GioiHan` chung (`SoTheoModel.gop`) thì phép kiểm đầu tiên phải
   ĐỎ.

⛔ KHÔNG GIẾT GÌ ĐỂ LẤY CHỖ. Mọi từ chối ở đây là 429 + `Retry-After`. Sàn VRAM
   của 5060 Ti cũng vậy: dưới sàn thì **không nhận lượt mới**, không ai bị huỷ.
   (L-9, TD-D5: không lượt nào bị giết để đổi residency.)
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from .gioi_han import HAN_GIU_MAC_DINH_S, GioiHan, PhanXuGioiHan, Suat

log = logging.getLogger("llm_gateway.so_theo_model")


class SoTheoModel:
    """Một `GioiHan` cho mỗi model, cộng sàn VRAM theo card.

    `san_vram_mb` = {model: MiB trống tối thiểu trước khi cấp suất}; thiếu tên
    model trong đó (hoặc giá trị 0) = **không có sàn** cho model ấy.
    `doc_vram_trong` = hàm `model -> MiB trống | None`; tiêm được để test không
    cần GPU.
    """

    def __init__(self, models: tuple, *, max_dong_thoi: int, token_pool: int,
                 dong_thoi_rieng: Optional[dict] = None,
                 pool_rieng: Optional[dict] = None,
                 san_vram_mb: Optional[dict] = None,
                 doc_vram_trong: Optional[Callable[[str], Optional[int]]] = None,
                 han_giu_s: float = HAN_GIU_MAC_DINH_S,
                 now: Callable[[], float] = time.monotonic):
        dong_thoi_rieng = dict(dong_thoi_rieng or {})
        pool_rieng = dict(pool_rieng or {})
        self._so: dict = {}
        for m in models:
            self._so[m] = GioiHan(
                max_dong_thoi=int(dong_thoi_rieng.get(m, max_dong_thoi)),
                token_pool=int(pool_rieng.get(m, token_pool)),
                han_giu_s=han_giu_s, now=now)
        self._san = {k: int(v) for k, v in (san_vram_mb or {}).items()}
        self._doc_vram = doc_vram_trong

    # ── Đường phục vụ thật: dựng thẳng từ `llama-swap.yaml` ─────────────────
    @classmethod
    def tu_vat_ly(cls, vat_ly: dict, *,
                  san_vram_mb: Optional[dict] = None,
                  doc_vram_trong: Optional[Callable[[str], Optional[int]]] = None,
                  han_giu_s: float = HAN_GIU_MAC_DINH_S,
                  now: Callable[[], float] = time.monotonic) -> "SoTheoModel":
        """Một sổ mỗi hồ sơ: số chuỗi = `-np`, bể KV = `-c` (phương án C, bước 3).

        ⭐ Bể là `-c`, KHÔNG phải `token_budget` của máy A: cổng là **rào vật
           lý**. Biên chính sách (`bien_pool`) thuộc máy A; lặp lại nó ở đây là
           hai nơi quyết một điều (kế hoạch §3.3 mục 2).
        """
        return cls(tuple(vat_ly), max_dong_thoi=1, token_pool=0,
                   dong_thoi_rieng={m: int(v.np) for m, v in vat_ly.items()},
                   pool_rieng={m: int(v.ctx) for m, v in vat_ly.items()},
                   san_vram_mb=san_vram_mb, doc_vram_trong=doc_vram_trong,
                   han_giu_s=han_giu_s, now=now)

    # ── Dựng từ một sổ CHUNG — chỉ để làm ĐỐI CHỨNG ─────────────────────────
    @classmethod
    def gop(cls, gh: GioiHan, models: tuple) -> "SoTheoModel":
        """Mọi model dùng **cùng một** `GioiHan`.

        🔴 ĐÂY LÀ HÌNH DẠNG SAI, VÀ NÓ CÓ MẶT CÓ CHỦ Ý — hai công dụng:

             1. **đối chứng**: `test_1221` dựng nó và đòi phép kiểm độc lập ĐỎ.
                Không có nó thì "hai sổ độc lập" là một câu không đo được.
             2. **hồi quy**: `test_258`/`test_363` tiêm một `GioiHan` trần vào
                `create_app(gioi_han=...)` để đo hàng rào và lưới thu hồi suất —
                những phép kiểm ấy không nói gì về hai model, nên bắt chúng dựng
                hai sổ là đổi thứ chúng đo.

        ⛔ ĐỪNG DÙNG NÓ Ở ĐƯỜNG PHỤC VỤ THẬT.
        """
        s = cls.__new__(cls)
        s._so = {m: gh for m in models}
        s._san = {}
        s._doc_vram = None
        return s

    # ── Cổng vào ────────────────────────────────────────────────────────────
    def cap_suat(self, model: str,
                 token_dat_truoc: int = 0) -> tuple[PhanXuGioiHan, Optional[Suat]]:
        """Xin suất **trên sổ của đúng model này**.

        Thứ tự: sàn VRAM ⇒ rồi mới tới sổ. Đảo lại là chiếm một suất rồi từ chối,
        tức rò một suất mỗi lần sàn nổ.
        """
        gh = self._so.get(model)
        if gh is None:
            # Không có sổ = model không mở. `api.py` đã chặn bằng 404 trước đó,
            # nên tới được đây là nối dây sai — nói ra, đừng phục vụ.
            log.error("xin suat cho model KHONG co so: %s", model)
            return (PhanXuGioiHan(False, f"model {model} khong co so rieng",
                                  thu_lai_sau_s=30), None)

        px_san = self._kiem_san_vram(model)
        if px_san is not None:
            return (px_san, None)

        return gh.cap_suat(token_dat_truoc)

    def _kiem_san_vram(self, model: str) -> Optional[PhanXuGioiHan]:
        """Sàn VRAM của card chạy `model`. `None` = qua cửa.

        🔴 SÀN VRAM LÀ OPT-IN (spec §22, D06). L-21 đã tắt mặc định cho 5060 Ti
           sau khi số đo production chứng minh nó tự khóa Qwen 3.5 mà không có
           OOM. 3090 cũng không có sàn: cuộc tranh với ComfyUI do trọng tài
           residency ở máy A phân xử (D01 B; `don_dep.py` đã xoá ở 5.4b), và
           chốt VRAM của nó là `Config.vram_sach_mb` tại `/v1/residency/nap`.

           ⛔ Con số nằm ở `config.py` và lý lẽ nằm ở L-18. Đừng chép sang đây.

        ⚠️ KHÔNG ĐỌC ĐƯỢC VRAM ⇒ COI LÀ BẬN, và đó là hành vi **đã có** ở
           `trong_tai.phan_xu()` ("khong hoi duoc nvidia-smi" ⇒ bận). Giữ cùng
           một chiều sai ở hai cửa cạnh nhau quan trọng hơn là tối ưu từng cửa:
           một cửa lạc quan cạnh một cửa bi quan thì người trực không đoán nổi
           cổng sẽ làm gì. Sàn chỉ bật khi được cấu hình (> 0), nên máy không có
           GPU (máy A, test) không bị chạm.
        """
        san = self._san.get(model, 0)
        if san <= 0:
            return None
        trong = self._doc_vram(model) if self._doc_vram is not None else None
        if trong is None:
            return PhanXuGioiHan(
                False, f"khong doc duoc VRAM trong cua card chay {model}",
                thu_lai_sau_s=30)
        if trong < san:
            return PhanXuGioiHan(
                False,
                f"VRAM trong {trong} MiB < san {san} MiB cua card chay {model} — "
                f"khong nhan luot moi (khong giet luot dang chay)",
                thu_lai_sau_s=30)
        return None

    # ── Đọc trạng thái ──────────────────────────────────────────────────────
    def dang_chay(self, model: str) -> int:
        gh = self._so.get(model)
        return 0 if gh is None else int(gh.trang_thai()["dang_chay"])

    def models(self) -> tuple:
        return tuple(sorted(self._so))

    def trang_thai(self) -> dict:
        """`{model: {dang_chay, max_dong_thoi, token_dat, token_pool, …}}`.

        Tên khoá giữ đúng tên của `GioiHan.trang_thai()` — `/health` của cổng đã
        công bố chúng và `tools/soi_su_co.py` cùng `test_334` đang đọc. Thêm một
        tên thứ hai cho cùng một giá trị là mở lại đúng cái bẫy "hai chỗ khai một
        điều" mà chương trình này đi dọn.
        """
        ra = {}
        for m, gh in self._so.items():
            t = dict(gh.trang_thai())
            t["san_vram_mb"] = self._san.get(m, 0)
            ra[m] = t
        return ra

    def trang_thai_chung(self) -> dict:
        """Khối `gioi_han` của `/health`: tổng + khối theo model.

        ⚠️ `max_dong_thoi` là `None` khi các model **không** khai cùng một số
           `-np`. Một con số gộp ở đó sẽ trả lời sai đúng câu mà `test_334` hỏi
           ("máy A có cho nhiều việc song song hơn máy B phục vụ được không"):
           trần là trần **của từng model**, nên khi hai model khác nhau thì không
           tồn tại một con số đúng — và bịa ra một con số thì tệ hơn là nói
           "đọc `theo_model`".
        """
        theo = self.trang_thai()
        maxs = {t["max_dong_thoi"] for t in theo.values()}
        return {
            # Tổng: dùng để bắt SUẤT RÒ (`soi_su_co.py`) — hết việc mà không về 0
            # thì có suất treo, và câu đó đúng với cả hai model cộng lại.
            "dang_chay": sum(t["dang_chay"] for t in theo.values()),
            "max_dong_thoi": maxs.pop() if len(maxs) == 1 else None,
            "giu_lau_nhat_giay": max((t["giu_lau_nhat_giay"] for t in theo.values()),
                                     default=0.0),
            "da_thu_hoi": sum(t["da_thu_hoi"] for t in theo.values()),
            "theo_model": theo,
        }


# ⛔ `token_dat_truoc(vào, ra)` ĐÃ GỠ (phương án C, bước 3). Phép giữ chỗ nay là
#    `vat_ly.token_giu` — CÙNG công thức với `tham_so_da_luot.luat_cho` của máy A
#    (có DEM_UOC, kẹp ra theo chỗ còn), và dùng nguyên số `X-LTT-Token-Dat` khi A
#    khai. Hai hàm cho cùng một câu hỏi là đúng khuôn "hai chỗ khai một điều".
