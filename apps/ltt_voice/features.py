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
from platform_core.jobs import DangBan, LoiNguoiGoi

from . import lan_ngon_ngu
from . import gia, sidecar_client, tham_chieu, text_pipeline

log = logging.getLogger(__name__)


class LoiGiongNoi(LoiNguoiGoi):
    """Thông điệp đưa thẳng ra cho khách — phải nói được cách sửa.

    ⭐ MANG THEO MỘT MÃ LỖI (`ma`), tuỳ chọn. Câu chữ đổi theo ngôn ngữ giao
       diện và theo mỗi lần ai đó viết lại cho dễ đọc hơn; mã thì không. Khách
       tích hợp Public API và mã JS ở Studio đều cần bắt lỗi theo **thứ không
       đổi**, và trước 2026-09-10 lớp này không có thứ đó — nên cách duy nhất
       để phân biệt "giọng không phải của bạn" với "văn bản lệch làn" là so
       chuỗi tiếng Việt.

    ⛔ Rỗng là hợp lệ và là mặc định: hàng chục chỗ đang ném lớp này không phải
       sửa theo. Chỗ nào có mã thì khai mã.

    ⛔ Kế thừa `platform_core.jobs.LoiNguoiGoi` để nền tảng **không thử lại**.
       Mọi lỗi ném ra từ đây đều là lỗi của *yêu cầu* (thiếu văn bản, giọng
       không phải của bạn, văn bản quá dài) — chạy lại y hệt sẽ hỏng y hệt.

       Máy bận thì đi đường khác: `DangBanTam`, và nó PHẢI được thử lại.
    """

    def __init__(self, thong_diep="", ma: str = ""):
        super().__init__(thong_diep)
        #: Mã lỗi ổn định cho GUI/API. Rỗng = chưa phân loại.
        self.ma = str(ma or "")


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


class DangBanTam(DangBan, RuntimeError):
    """Máy đang bận. **KHÔNG PHẢI HỎNG** — job phải được xếp lại, không tính tiền.

    ⭐ Kế thừa `platform_core.jobs.DangBan` (H43 Phase 05, 03/09/2026) để worker
       đưa job về hàng đợi bằng `resource_wait` — **không tiêu lượt thử, không
       chạm tiền**. Trước đó lớp này chỉ là `RuntimeError`, và
       `job_runner._provider_failure_kind` không nhận ra nó: mỗi lần cổng giọng
       trả 429, job mất một trong năm lượt thử, và năm lượt bận liên tiếp là một
       job HỎNG kèm hoàn tiền cho một việc chưa từng chạy.

    ⛔ Vẫn KHÔNG kế thừa `LoiNguoiGoi` hay `LoiHaTang` — `test_501` chốt cả hai
       chiều. Giữ `RuntimeError` để chỗ nào đang bắt theo lớp cũ không đổi.
    """

    def __init__(self, retry_after_s: float = 5.0):
        DangBan.__init__(self, "May tao tieng dang ban",
                         retry_after_s=retry_after_s)


# ── yêu cầu ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class YeuCau:
    text: str
    voice_id: str = ""
    preset: str = ""
    owner_id: str = ""
    doc_so_tran: bool = False
    #: Tốc độ HẬU KỲ (time-stretch trên tệp đã sinh), KHÔNG phải tốc độ đọc của
    #: model. Xem `toc_do.py` để biết vì sao hai thứ đó phải tách bạch, và vì
    #: sao nó không thuộc năm tham số mà Q119 khoá.
    toc_do: float = 1.0

    #: Ngôn ngữ khách TỰ KHAI: `"auto"` (mặc định), `"vi"`, `"en"`.
    #:
    #: ⛔ KHÔNG phải tham số của engine. VieNeu song ngữ và tự xử lý cả hai —
    #:    đó là lý do ô này từng bị bỏ với ghi chú *"ba nút giả tệ hơn một câu
    #:    thật"*. Nhận xét ấy đúng **vào lúc viết**, và nó hết đúng khi
    #:    `lan_ngon_ngu.py` ra đời: nay có làn của giọng, có phép đoán ngôn ngữ
    #:    của văn bản, và có phép đối chiếu hai thứ đó.
    #:
    #: ⭐ Nên ô này điều khiển một thứ THẬT: nó thay cho phép ĐOÁN khi đối chiếu
    #:    làn. Xem `lan_ngon_ngu.doi_chieu`.
    ngon_ngu: str = "auto"

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

    # Giá trị lạ -> `auto`. Một tham số hỏng không được làm hỏng job, và
    # `auto` là hành vi cũ nên nó là lối lui đúng.
    ngon_ngu = str(p.get("ngon_ngu") or "auto").strip().lower()
    if ngon_ngu not in ("auto", "vi", "en"):
        ngon_ngu = "auto"

    from . import toc_do as _toc_do
    return YeuCau(text=text, voice_id=voice_id, preset=preset,
                  owner_id=owner_id, ngon_ngu=ngon_ngu,
                  doc_so_tran=bool(p.get("doc_so_tran")),
                  # `hop_le` ép về khoảng và biến giá trị vô nghĩa thành 1.0 —
                  # tức "không đổi". Một tham số hỏng không được làm hỏng job.
                  toc_do=_toc_do.hop_le(p.get("toc_do", 1.0)))


# ── kết quả ──────────────────────────────────────────────────────────────────

@dataclass
class KetQua:
    yeu_cau: YeuCau
    audio_key: str
    giay: float
    text_da_chuan_hoa: str
    so_doan: int = 1
    canh_bao: tuple = field(default_factory=tuple)
    #: 🔴 HAI THỜI LƯỢNG, và trộn chúng là một lỗi TIỀN.
    #:
    #:    `giay`      — thời lượng SINH RA. Cơ sở tính credit, vì đó là lượng
    #:                  việc GPU đã làm.
    #:    `giay_phat` — thời lượng TỆP KHÁCH NHẬN, sau khi đổi tốc độ.
    #:
    #:    Ở 1,5× tệp ngắn đi một phần ba. Tính tiền theo `giay_phat` là để khách
    #:    trả ít hơn cho cùng một lượng việc — một lỗ khai thác được, không phải
    #:    một sự ưu ái. Bằng 0 nghĩa là không đổi tốc độ.
    giay_phat: float = 0.0

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
            # Chỉ công bố khi thật sự khác — thêm hai trường luôn-luôn-có vào
            # mọi bản ghi lịch sử để phục vụ một ca hiếm là làm nặng tất cả.
            **({"toc_do": self.yeu_cau.toc_do,
                "duration_played_s": round(self.giay_phat, 3)}
               if self.giay_phat else {}),
        }


# ── đường đi chính ───────────────────────────────────────────────────────────

def chuan_bi_van_ban(yc: YeuCau, *, tran_moi_doan: int,
                     tu_dien_rieng: dict | None = None):
    """Chuẩn hoá + chia đoạn. Tách ra để test được mà không chạm mạng."""
    return text_pipeline.chuan_bi(
        yc.text, tran_moi_doan=tran_moi_doan,
        doc_so_tran=yc.doc_so_tran, tu_dien_rieng=tu_dien_rieng)


def _chot_lan(lan_giong: str, yc: YeuCau) -> tuple:
    """Áp hợp đồng tương thích làn. Ném `LoiGiongNoi` khi KHÔNG hợp lệ.

    🔴 ĐÂY LÀ CỬA CHẶN, và nó phải ở `features` chứ không ở route — Public API
       đi **thẳng** xuống job và không qua cánh cửa nào của web. Đặt phép chặn
       trong một cửa nghĩa là cửa kia không có nó, tức đúng cái bẫy docstring
       đầu tệp này cảnh báo, ở đúng hạng mục tốn tiền của khách.

    ⭐ Trả về tuple cảnh báo để chữ ký của `giai_giong` không đổi. Từ Q121 tuple
       ấy gần như luôn rỗng — một yêu cầu lệch làn không còn đi qua được đây để
       mà cảnh báo. Giữ chỗ vì làn thứ ba (`bilingual`) sẽ cần đúng chỗ đó.
    """
    pq = lan_ngon_ngu.quyet_dinh(lan_giong, yc.text, yc.ngon_ngu)
    if not pq.cho_phep:
        raise LoiGiongNoi(lan_ngon_ngu.cau_cho_khach(pq), ma=pq.ma_loi)
    return lan_ngon_ngu.doi_chieu(lan_giong, yc.text, yc.ngon_ngu)


def giai_giong(db, yc: YeuCau) -> tuple:
    """`YeuCau` -> `(ref_b64, preset, canh_bao)`.

    Đây là chỗ **quyền sở hữu** được kiểm, và từ Q121 cũng là chỗ **làn ngôn
    ngữ** được chốt. Cả hai là chỗ duy nhất.

    ⛔ THỨ TỰ CÓ NGHĨA: giải giọng trước, chốt làn sau. Ta không nói được một
       yêu cầu lệch làn khi còn chưa biết giọng nào — và "giọng này không phải
       của bạn" là câu phải ra trước, vì nó đúng bất kể văn bản viết bằng gì.
    """
    if not yc.voice_id:
        # ⛔ KHÔNG gõ `"vi"` ở đây nữa. Trước 2026-09-10 chỗ này là một hằng số
        #    chuỗi, và nó là **bản chép thứ nhất** của danh sách VI/EN (bản thứ
        #    hai nằm trong `_voice_chon.html`). Hai bản chép không có phép kiểm
        #    là hai bản sẽ lệch — và bản trong HTML thì không có cách nào tự
        #    biết nó đã cũ.
        from . import giong_mau
        lan = giong_mau.lan_cua(yc.preset) if yc.preset else giong_mau.lan_cua(
            giong_mau.MAC_DINH)
        return None, (yc.preset or None), _chot_lan(lan, yc)

    # `cho_dung_chung=True`: kho giọng chung của nền tảng đọc được cho mọi
    # khách. Đây là cửa DÙNG, nên nó mở; cửa SỬA (`_p_giong`) thì không.
    ho_so = tham_chieu.tim_profile(db, yc.voice_id, owner_id=yc.owner_id,
                                   cho_dung_chung=True)
    if ho_so is None:
        # ⛔ Cùng một thông điệp cho "không tồn tại" và "không phải của bạn".
        #    Phân biệt hai câu đó là cho phép dò xem `voice_id` nào có thật.
        raise LoiGiongNoi(_t("Không tìm thấy giọng này trong tài khoản của bạn."))
    if ho_so.trang_thai != "active":
        raise LoiGiongNoi(_t("Giọng này đang bị tắt. Hãy bật lại hoặc tạo giọng mới."))

    # ⛔ CHỐT LÀN TRƯỚC KHI NẠP BIỂU DIỄN. `nap_ref_b64` là một lượt đọc kho —
    #    trên production đó là một lượt gọi MẠNG tới R2 cho một yêu cầu ta vừa
    #    biết chắc là sẽ bị từ chối. Đặt sau thì vẫn đúng, chỉ là trả tiền cho
    #    một việc không ai cần.
    canh_bao = _chot_lan(ho_so.ngon_ngu, yc)

    bieu_dien = tham_chieu.tim_repr_active(db, ho_so.id)
    if bieu_dien is None:
        raise LoiGiongNoi(_t(
            "Giọng này chưa ghi danh xong. Hãy thử lại sau ít phút."))
    return tham_chieu.nap_ref_b64(bieu_dien), None, canh_bao


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


#: 🔴 `goi_cong_dai` ĐÃ GỠ 03/09/2026, và chỗ này ghi lại vì sao — không phải để
#:    tiếc nó, mà để lần sau ai đó định thêm lại thì đọc được lý do nó đi.
#:
#:    Nó gọi `/v1/speech-dai`: sinh **và** ghép cả bài trong MỘT lượt HTTP. Đúng
#:    cho bài vừa phải, và nó không sai — nhưng nó không ghi lại gì giữa chừng,
#:    nên một đoạn hỏng ở phút thứ 18 làm mất cả lượt, và cả bản đọc phải nằm
#:    trong RAM sidecar cùng lúc.
#:
#: ⭐ Đường bản đọc dài nay đi qua `ban_doc_dai.dung` — từng đoạn có một chỗ
#:    đứng riêng trên đĩa, nên "đọc tiếp" và "chỉ sinh lại đoạn hỏng" là hệ quả
#:    tự nhiên chứ không phải tính năng phải xây thêm.
#:
#: ⚠️ Cửa `/v1/speech-dai` thì VẪN CÒN ở sidecar: `tools/do_troi_tong.py` gọi
#:    thẳng nó, và nó là đường đối chứng của phép đo. Gỡ ở đây là gỡ **người gọi
#:    trong sản phẩm**, không phải gỡ cửa.


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
