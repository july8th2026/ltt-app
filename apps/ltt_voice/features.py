"""
features.py — NGHIỆP VỤ của LTT VOICE. Mọi cửa gọi vào đây.

Khuôn tầng 4 chốt 4.1 (`docs/KHUON_BAN_MODEL_NHA.md`): *"Nghiệp vụ ở `features.py`,
dùng chung mọi cửa — hai cửa tự xử lý riêng ⇒ ngày chúng lệch nhau là ngày một
yêu cầu bị tính hai giá."*

Ba cửa sẽ gọi vào đây: web (`routes.py`), job worker (`jobs.py`), và Public API
(qua ToolSpec → cùng job). Không cửa nào được tự kiểm quyền, tự chia đoạn, hay tự
tính tiền.

⛔ QUYỀN SỞ HỮU KIỂM Ở ĐÂY, KHÔNG Ở ROUTE. `voice_id` là chuỗi khách gửi lên;
   không kiểm thì khách A đọc được giọng của khách B chỉ bằng cách đoán. Đặt phép
   kiểm trong route nghĩa là cửa thứ hai phải chép lại, và bản chép sẽ lệch.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from platform_core.i18n import _ as _t
from platform_core.jobs import LoiNguoiGoi

from . import gia, sidecar_client, tham_chieu, text_pipeline

log = logging.getLogger(__name__)


class LoiGiongNoi(LoiNguoiGoi):
    """Thông điệp đưa thẳng ra cho khách — phải nói được cách sửa.

    ⛔ Kế thừa `platform_core.jobs.LoiNguoiGoi` để nền tảng **không thử lại**.
       Mọi lỗi ném ra từ đây đều là lỗi của *yêu cầu* (thiếu văn bản, giọng
       không phải của bạn, văn bản quá dài) — chạy lại y hệt sẽ hỏng y hệt.

       Máy bận thì đi đường khác: `DangBanTam`, và nó PHẢI được thử lại.
    """


class LoiHaTang(RuntimeError):
    """Cổng giọng trục trặc. **PHẢI được thử lại** — không phải lỗi của khách.

    🔴 LỚP NÀY SINH RA TỪ MỘT HỒI QUY, ghi lại để không ai gộp nó vào
       `LoiGiongNoi` lần nữa.

       31/08/2026, commit `c8634b8` cho `LoiGiongNoi` kế thừa
       `platform_core.jobs.LoiNguoiGoi` để nền tảng thôi thử lại ba lần một lỗi
       vĩnh viễn. Đúng cho "giọng này không phải của bạn". **Sai** cho nhánh
       `LoiSidecar`, vốn cũng ném `LoiGiongNoi` — và nhánh đó gồm: mạng chập
       chờn, cổng trả 5xx, cổng đang khởi động lại sau deploy, cổng trả thứ
       không phải JSON.

       Hệ quả: thông điệp nói *"Vui lòng thử lại sau"* trong khi nền tảng đã
       quyết **không bao giờ thử lại**. Và ca thường gặp nhất chính là ca tệ
       nhất — deploy khởi động lại `LTTStudioVoice`, mọi job đang bay đều hỏng
       vĩnh viễn thay vì được xếp lại vài giây sau.

       ⭐ Chính docstring của `LoiNguoiGoi` đã cảnh báo đúng điều này: *"Đừng
          dùng nó cho lỗi hạ tầng… đánh dấu chúng là lỗi người gọi biến một
          trục trặc thoáng qua thành một thất bại vĩnh viễn trong mắt khách."*
          Tôi viết câu đó rồi vi phạm nó trong cùng một commit.

    ⛔ KHÔNG kế thừa `LoiNguoiGoi`. Đó là toàn bộ lý do lớp này tồn tại.
    """


class DangBanTam(RuntimeError):
    """Máy đang bận. **KHÔNG PHẢI HỎNG** — job phải được xếp lại, không tính tiền."""

    def __init__(self, retry_after_s: float = 5.0):
        super().__init__("May tao tieng dang ban")
        self.retry_after_s = retry_after_s


# ── yêu cầu ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class YeuCau:
    text: str
    voice_id: str = ""
    preset: str = ""
    owner_id: str = ""
    doc_so_tran: bool = False

    @property
    def so_ky_tu(self) -> int:
        return len(self.text)


def chuan_hoa(params: dict) -> YeuCau:
    """Đọc tham số của một cửa bất kỳ thành một `YeuCau` đã kiểm.

    ⛔ KHÔNG kiểm trần ký tự ở đây bằng một con số gõ tay. Trần thuộc về
       `voice_sidecar/tham_so.py` và cổng tự từ chối bằng 413 trước khi chạm GPU.
       Ta chỉ kiểm những thứ mà **chỉ tầng này biết**: có text không, có giọng
       không, và giọng đó có phải của người này không.
    """
    p = params or {}
    text = str(p.get("text") or "").strip()
    if not text:
        raise LoiGiongNoi(_t("Chưa có văn bản để đọc."))

    voice_id = str(p.get("voice_id") or "").strip()
    preset = str(p.get("preset") or "").strip()
    if voice_id and preset:
        # Hai nguồn giọng cùng lúc là một yêu cầu không có câu trả lời đúng.
        # Từ chối rõ ràng, đừng lặng lẽ chọn một cái.
        raise LoiGiongNoi(_t("Chỉ chọn một: giọng của bạn hoặc giọng có sẵn."))

    # 🔴 KIỂM `preset` Ở ĐÂY, KHÔNG Ở ROUTE — và không kiểm là mất tiền của khách.
    #
    #    Một tên giọng bịa đi lọt hết đường xuống worker, rồi SDK mới ném
    #    `ValueError: Voice 'X' not found`. Mà `ValueError` **không phải**
    #    `LoiNguoiGoi`, nên nền tảng coi đó là lỗi hạ tầng và **thử lại ba lần**.
    #    Khách chờ khoảng ba mươi giây cho một câu trả lời mà cửa vào đã biết
    #    ngay từ đầu — đúng lớp lỗi mà `voice_id` đã mắc và đã sửa (xem chú thích
    #    ở `routes.py::tao`).
    #
    # ⛔ Và nó phải ở `features`, không ở `routes`: Public API đi **thẳng** xuống
    #    job, không qua route nào cả. Đặt phép kiểm trong một cánh cửa thì cánh
    #    cửa thứ hai không có nó — đúng cái bẫy docstring đầu tệp này cảnh báo.
    if preset:
        from . import giong_mau
        if not giong_mau.hop_le(preset):
            raise LoiGiongNoi(_t("Không có giọng dựng sẵn tên này."))

    # ⛔ Giữ NGUYÊN dạng chuỗi. `User.id` là UUID chuỗi; ép `int()` ở đây
    #    từng ném rồi bị nuốt, cho ra `owner_id = 0` cho mọi người dùng.
    owner_id = str(p.get("owner_id") or p.get("user_id") or "").strip()

    return YeuCau(text=text, voice_id=voice_id, preset=preset,
                  owner_id=owner_id,
                  doc_so_tran=bool(p.get("doc_so_tran")))


# ── kết quả ──────────────────────────────────────────────────────────────────

@dataclass
class KetQua:
    yeu_cau: YeuCau
    audio_key: str
    giay: float
    text_da_chuan_hoa: str
    so_doan: int = 1
    canh_bao: tuple = field(default_factory=tuple)

    @property
    def credit_that(self) -> int:
        """🔴 GIÁ THẬT theo **giây đo được**, không theo phần đã giữ (khuôn 3.4).

        Không đo được ⇒ **0** (khuôn 3.5): thu tiền không bằng chứng tệ hơn mất
        một ít tiền.
        """
        if not self.giay or self.giay <= 0:
            return 0
        return gia.tinh(self.giay)

    def as_result(self) -> dict:
        """Thứ handler trả về cho `job_runner`.

        ⛔ `credit_cost` BẮT BUỘC có. Thiếu nó thì `job_runner._quyet_toan_credit`
           thu **trọn phần đã giữ**, im lặng — đúng lỗi H37 mắc và đã sửa 24/08.
        """
        return {
            "audio_key": self.audio_key,
            "duration_s": round(self.giay, 3),
            "text": self.text_da_chuan_hoa,
            "so_doan": self.so_doan,
            "credit_cost": self.credit_that,
            "phien_ban_gia": gia.PHIEN_BAN_GIA,
            "canh_bao": list(self.canh_bao),
        }


# ── đường đi chính ───────────────────────────────────────────────────────────

def chuan_bi_van_ban(yc: YeuCau, *, tran_moi_doan: int,
                     tu_dien_rieng: dict | None = None):
    """Chuẩn hoá + chia đoạn. Tách ra để test được mà không chạm mạng."""
    return text_pipeline.chuan_bi(
        yc.text, tran_moi_doan=tran_moi_doan,
        doc_so_tran=yc.doc_so_tran, tu_dien_rieng=tu_dien_rieng)


def giai_giong(db, yc: YeuCau) -> tuple:
    """`YeuCau` -> `(ref_b64, preset, canh_bao)`.

    Đây là chỗ **quyền sở hữu** được kiểm, và nó là chỗ duy nhất.
    """
    if not yc.voice_id:
        return None, (yc.preset or None), ()

    ho_so = tham_chieu.tim_profile(db, yc.voice_id, owner_id=yc.owner_id)
    if ho_so is None:
        # ⛔ Cùng một thông điệp cho "không tồn tại" và "không phải của bạn".
        #    Phân biệt hai câu đó là cho phép dò xem `voice_id` nào có thật.
        raise LoiGiongNoi(_t("Không tìm thấy giọng này trong tài khoản của bạn."))
    if ho_so.trang_thai != "active":
        raise LoiGiongNoi(_t("Giọng này đang bị tắt. Hãy bật lại hoặc tạo giọng mới."))

    bieu_dien = tham_chieu.tim_repr_active(db, ho_so.id)
    if bieu_dien is None:
        raise LoiGiongNoi(_t(
            "Giọng này chưa ghi danh xong. Hãy thử lại sau ít phút."))
    return tham_chieu.nap_ref_b64(bieu_dien), None, ()


def _goi_va_dich_loi(ham, *doi_so, **tham_so):
    """Chạy một lời gọi cổng và **dịch lỗi hạ tầng thành câu khách đọc được**.

    ⛔ BẬN KHÔNG PHẢI HỎNG. `SidecarBan` -> `DangBanTam`, và tầng job phải xếp
       lại chứ không đánh dấu job hỏng. Một job bị coi là hỏng sẽ **trừ credit**
       cho một việc chưa từng chạy.

    ⭐ Tách ra dùng chung cho cả hai cửa (một lượt và văn bản dài) chứ không
       chép đôi: hai bản chép của một bảng dịch lỗi sẽ lệch, và cái lệch đầu
       tiên gần như chắc chắn là nhánh `SidecarBan` — tức đúng nhánh mà lệch
       một chút là mất tiền của khách.
    """
    try:
        return ham(*doi_so, **tham_so)
    except sidecar_client.SidecarBan as e:
        raise DangBanTam(retry_after_s=e.retry_after_s) from e
    except sidecar_client.VanBanQuaDai as e:
        raise LoiGiongNoi(_t(
            "Đoạn văn bản quá dài cho một lượt đọc. Hãy chia thành nhiều đoạn "
            "ngắn hơn.")) from e
    except sidecar_client.LoiSidecar as e:
        # ⛔ `LoiHaTang`, KHÔNG phải `LoiGiongNoi`. Nhánh này là trục trặc của
        #    HẠ TẦNG, và thông điệp của nó hứa với khách là sẽ thử lại.
        log.warning("cong giong loi: %s", e)
        raise LoiHaTang(_t(
            "Máy tạo tiếng nói chưa sẵn sàng. Vui lòng thử lại sau.")) from e


def goi_cong(text: str, *, ref_b64=None, preset=None) -> tuple:
    """Một lượt sinh. Trả `(wav_bytes, headers)`."""
    return _goi_va_dich_loi(sidecar_client.noi, text,
                            ref_b64=ref_b64, preset=preset)


def goi_cong_dai(doan: list, *, ref_b64=None, preset=None) -> tuple:
    """Nhiều đoạn -> MỘT tệp liền mạch. Cùng hình dạng trả về với `goi_cong`."""
    return _goi_va_dich_loi(sidecar_client.noi_dai, list(doan),
                            ref_b64=ref_b64, preset=preset)


def hash_noi_dung(data: bytes) -> str:
    """SHA-256 của tệp nguồn. Là khoá idempotent của việc ghi danh."""
    return hashlib.sha256(data).hexdigest()


def kiem_ghi_danh(data: bytes, content_type: str = "") -> dict:
    """Cửa vào của luồng ghi danh. Ném `LoiGiongNoi` với câu sửa được."""
    from . import audio_input
    try:
        return audio_input.kiem(data, content_type)
    except audio_input.LoiAudio as e:
        raise LoiGiongNoi(str(e)) from e
