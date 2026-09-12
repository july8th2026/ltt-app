"""
so_theo_model.py — **một sổ cho MỖI model**. Tải 3.8 không bao giờ lấy suất 3.5.

🔴 VÌ SAO KHÔNG THỂ DÙNG MỘT `GioiHan` CHUNG. Từ 09/2026 cổng này phục vụ hai
   model chạy trên **hai card khác nhau** của máy B:

     qwen38-api   RTX 3090     -c 221184  -np 3   (mmproj + draft-mtp)
     qwen35-api   RTX 5060 Ti  -c 262144  -np 3   (mmproj + draft-mtp)

   Một sổ chung nói *"đang chạy 3/3, đầy"* trong khi **cả ba** lượt ấy nằm trên
   3090 và 5060 Ti hoàn toàn rảnh. Tức nó từ chối một lượt mà phần cứng dư sức
   phục vụ — và nó từ chối bằng 429, thứ máy A hiểu là "bận", nên khách đi ra
   đám mây trong khi card thứ hai ngồi không.

   Chiều ngược lại tệ hơn: gộp hai bể KV thành một con số thì bể của 3090
   (221.184) được tính bằng bể lớn hơn, và khi KV cạn thì
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
                 rpm: int = 120,
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
                rpm=rpm,
                token_pool=int(pool_rieng.get(m, token_pool)),
                han_giu_s=han_giu_s, now=now)
        self._san = {k: int(v) for k, v in (san_vram_mb or {}).items()}
        self._doc_vram = doc_vram_trong

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
    def cap_suat(self, model: str, token_dat_truoc: int = 0,
                 la_whale: bool = False) -> tuple[PhanXuGioiHan, Optional[Suat]]:
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

        return gh.cap_suat(token_dat_truoc, la_whale)

    def _kiem_san_vram(self, model: str) -> Optional[PhanXuGioiHan]:
        """Sàn VRAM của card chạy `model`. `None` = qua cửa.

        🔴 VÌ SAO CHỈ 5060 Ti CÓ SÀN MẶC ĐỊNH (spec §22, D06). Đo §G3b: LTT-3.5
           Q6_K + MTP giữ 15.309 MiB trên card 16.311 ⇒ **biên còn 1.002 MiB**.
           Chủ dự án chốt ngưỡng cảnh báo **700 MiB** (12/09) vì máy B "chỉ chạy
           hệ thống AI" và card rảnh chỉ giữ 54 MiB. 3090 thì biên 445 MiB nhưng
           nó đã có `don_dep` + trọng tài riêng cho cuộc tranh với ComfyUI.

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
        """`{model: {dang_chay, max_dong_thoi, token_dat, token_pool, whale, …}}`.

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

        ⚠️ `max_dong_thoi`/`rpm` là `None` khi các model **không** khai cùng một
           số. Một con số gộp ở đó sẽ trả lời sai đúng câu mà `test_334` hỏi
           ("máy A có cho nhiều việc song song hơn máy B phục vụ được không"):
           trần là trần **của từng model**, nên khi hai model khác nhau thì không
           tồn tại một con số đúng — và bịa ra một con số thì tệ hơn là nói
           "đọc `theo_model`".
        """
        theo = self.trang_thai()
        maxs = {t["max_dong_thoi"] for t in theo.values()}
        rpms = {t["rpm"] for t in theo.values()}
        return {
            # Tổng: dùng để bắt SUẤT RÒ (`soi_su_co.py`) — hết việc mà không về 0
            # thì có suất treo, và câu đó đúng với cả hai model cộng lại.
            "dang_chay": sum(t["dang_chay"] for t in theo.values()),
            "max_dong_thoi": maxs.pop() if len(maxs) == 1 else None,
            "rpm": rpms.pop() if len(rpms) == 1 else None,
            "giu_lau_nhat_giay": max((t["giu_lau_nhat_giay"] for t in theo.values()),
                                     default=0.0),
            "da_thu_hoi": sum(t["da_thu_hoi"] for t in theo.values()),
            "theo_model": theo,
        }


def token_dat_truoc(token_vao: int, token_ra: int) -> int:
    """Token KV một lượt chiếm ở **ĐỈNH** = vào + ra tối đa.

    🔴 PHẢI LÀ ĐỈNH, KHÔNG PHẢI ĐẦU VÀO. KV lớn dần theo từng token sinh ra, nên
       một lượt "vào 200K, xin ra 32K" chiếm 232K token **trước khi nó xong**.
       Đặt chỗ theo đầu vào thôi là để bể vỡ ở giữa lượt — và lúc bể vỡ thì
       llama.cpp huỷ **mọi** slot, kể cả các lượt đã vào từ trước và đang gần
       xong.

    ⭐ Tối thiểu 1: một yêu cầu rỗng vẫn chiếm một slot thật, và 0 sẽ rơi vào
       nhánh "suất vô hình" của `gioi_han._xin_vao` ⇒ 429 cho một yêu cầu hợp lệ.
       Đường ấy dành cho **nối dây sai**, không dành cho một prompt ngắn.
    """
    return max(1, int(token_vao) + max(0, int(token_ra)))
