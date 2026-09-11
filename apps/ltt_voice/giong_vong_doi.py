"""
giong_vong_doi.py — VÒNG ĐỜI và XUẤT XỨ NGÔN NGỮ của một Voice Profile.

Tách khỏi `tables.py` (chỉ khai bảng) và `tham_chieu.py` (chạm CSDL/kho) vì đây
là **luật của trạng thái**: một giọng được đi từ đâu tới đâu, và một giá trị
`ngon_ngu` hiện có được sửa khi nào. Cả hai đều là quy tắc thuần, test được mà
không cần CSDL — nên chúng ở một tệp thuần.

⭐ VÌ SAO XUẤT XỨ NGÔN NGỮ LÀ MỘT GIÁ TRỊ, KHÔNG PHẢI MỘT PHÉP ĐOÁN (D003).

   Cột `voice_profile.ngon_ngu` có từ đầu, nhưng cửa ghi danh **chưa bao giờ đặt
   nó** — nên mọi giọng nhân bản, kể cả giọng mà tên hiển thị là tiếng Anh, đều
   mang `ngon_ngu = "vi"` do mặc định của cột (đo 01/09/2026, `test_384`). Đó
   chính là điều một kho giọng production KHÔNG được làm: **khẳng định một ngôn
   ngữ mà nó chưa từng thu thập, rồi coi đó là sự thật.**

   D003 (2026-09-11) chốt ba nguồn, và **chỉ ba**:
     ① `khai_bao`     — khách TỰ NÓI lúc ghi danh. Nguồn đáng tin nhất.
     ② `do_asr`       — máy ĐO bằng ASR sau khi có bản ghi (WS khác). Vì là một
                        PHÉP ĐO, sửa nó đòi bằng chứng cùng cấp — xem
                        `khai_lan_hop_le`.
     ③ `mac_dinh_cu`  — dòng có TRƯỚC tính năng này; `ngon_ngu` của chúng là một
                        MẶC ĐỊNH cột, không phải một khoản khai hay một phép đo.
                        Migration `20260911_1000_voice_ngon_ngu_nguon` đặt giá
                        trị này cho mọi dòng đang có.

⛔ D003 BỎ nhánh "chưa biết" của bản nháp cũ (`chua_biet`, `ngon_ngu=""`). Ghi
   danh RC1 luôn khai một làn — không còn đường nào để lại một giọng không rõ
   làn lúc ghi danh xong; xem `khai_lan_hop_le` bên dưới cho ràng buộc sửa sau.

⛔ KHÔNG SAO CHÉP THUẬT TOÁN ĐỐI CHIẾU CỦA WS01 (`lan_ngon_ngu.py`). Tệp này chỉ
   **lưu** làn nguồn cho đúng, và dùng `lan_ngon_ngu.LAN_HOP_LE` làm thẩm quyền
   cho danh sách làn — việc đối chiếu văn bản với làn vẫn là của WS01.
"""
from __future__ import annotations

from . import lan_ngon_ngu

# ── Trạng thái vòng đời ──────────────────────────────────────────────────────
#
# `dang_ghi_danh` → `active`               (job ghi danh xong, có biểu diễn)
#                 → `loi`                  (job ghi danh hỏng vĩnh viễn)
# `active`        → `disabled`             (khách tắt, ĐẢO NGƯỢC được)
# `disabled`      → `active`               (bật lại)
# `active`/`disabled`/`loi` → `revoked`    (THU HỒI: xoá dữ liệu sinh trắc,
#                                           KHÔNG đảo ngược; giữ lịch sử + bút
#                                           toán)
#
# ⛔ T-07: `dang_ghi_danh` KHÔNG chuyển thẳng sang `revoked`. Đang ghi danh
#    nghĩa là chưa có biểu diễn engine để thu hồi — cửa thu hồi phải chờ job
#    xong (`active`/`loi`) rồi mới thu hồi, không được nhảy cóc qua một trạng
#    thái chưa từng tồn tại đủ để xoá.
#
# ⛔ `revoked` khác `disabled` ở CHIỀU KHÔNG QUAY LẠI ĐƯỢC và ở HỆ QUẢ với dữ
#    liệu: `disabled` chỉ tắt đường dùng, mọi tệp còn nguyên (điều khoản hứa giữ
#    clip gốc để dựng lại giọng khi nâng engine). `revoked` là quyền được xoá của
#    khách — nó **xoá clip nguồn, biểu diễn và tệp nghe thử**, và cố ý phá lời
#    hứa "dựng lại được" đó, vì dữ liệu sinh trắc thuộc về người, không thuộc về
#    ta. Lịch sử lượt tạo và bút toán credit thì GIỮ, để không làm mồ côi tiền đã
#    thu — đúng lý do `tables.py` không có trạng thái `deleted` (xoá cả hàng).
TT_DANG_GHI_DANH = "dang_ghi_danh"
TT_ACTIVE = "active"
TT_DISABLED = "disabled"
TT_REVOKED = "revoked"
#: 🔴 Hỏng ghi danh có một trạng thái RIÊNG. Trước đó một job ghi danh hỏng để lại
#:    giọng ở `dang_ghi_danh` **vĩnh viễn**, và `features.giai_giong` nói mãi câu
#:    *"chưa ghi danh xong, thử lại sau"* — một lời hứa không bao giờ thành. `loi`
#:    là một trạng thái CUỐI hiện được ra giao diện: khách biết cần ghi danh lại.
#:
#: ⚠️ CHUYỂN VÀO `loi` LÀ VIỆC CỦA WORKER — tệp này chỉ **định nghĩa** trạng
#:    thái và luật chuyển; nó không tự đặt được vì nó không chạy trong worker.
TT_LOI = "loi"

TRANG_THAI_HOP_LE = frozenset(
    {TT_DANG_GHI_DANH, TT_ACTIVE, TT_DISABLED, TT_REVOKED, TT_LOI})

#: Chuyển trạng thái CHO PHÉP (spec §6.3). Khai tường minh để một cửa mới không
#: lặng lẽ đưa một giọng đi một đường vô nghĩa (vd `revoked` → `active`: dữ liệu
#: đã xoá, bật lại là bật một cái vỏ rỗng).
_CHUYEN = {
    TT_DANG_GHI_DANH: {TT_ACTIVE, TT_LOI},
    TT_ACTIVE: {TT_DISABLED, TT_REVOKED},
    TT_DISABLED: {TT_ACTIVE, TT_REVOKED},
    TT_LOI: {TT_REVOKED},
    TT_REVOKED: set(),  # cuối đường — không quay lại (INV-THU-HOI-1)
}


def co_the_chuyen(tu: str, den: str) -> bool:
    """Có được chuyển từ trạng thái `tu` sang `den` không.

    Dùng ở cửa thu hồi/tắt để không phụ thuộc vào việc mỗi cửa tự nhớ luật.
    """
    return den in _CHUYEN.get(tu, set())


# ── Làn ngôn ngữ nguồn + xuất xứ (D003) ──────────────────────────────────────

#: Xuất xứ của giá trị `ngon_ngu` — trả lời "vì sao ta tin làn này", và ba giá
#: trị này là **thẩm quyền duy nhất** cho cột `voice_profile.ngon_ngu_nguon`.
NGUON_KHAI_BAO = "khai_bao"        # khách tự khai lúc ghi danh
NGUON_DO_ASR = "do_asr"            # máy ĐO bằng ASR sau khi có bản ghi
NGUON_MAC_DINH_CU = "mac_dinh_cu"  # dòng có trước tính năng này (migration)

NGUON_HOP_LE = (NGUON_KHAI_BAO, NGUON_DO_ASR, NGUON_MAC_DINH_CU)


def khai_lan_hop_le(lan_moi: str, *, lan_hien: str, nguon_hien: str) -> str:
    """Khách xin sửa làn hiện có sang `lan_moi` — có được không?

    Trả `""` khi được, hoặc một mã lỗi ỔN ĐỊNH (Public API + GUI đọc mã, không
    đọc câu chữ — câu chữ đổi theo ngôn ngữ giao diện):

      `"voice_language_required"`  `lan_moi` không thuộc `lan_ngon_ngu.LAN_HOP_LE`
                                    — không có làn thứ ba, và không có "tự đoán".
      `"voice_language_measured"`  làn hiện tại đến từ một PHÉP ĐO ASR
                                    (`nguon_hien == NGUON_DO_ASR`) và khách xin
                                    đổi sang một làn KHÁC làn đã đo.

    ⭐ VÌ SAO `do_asr` CHẶN CÒN `khai_bao`/`mac_dinh_cu` THÌ KHÔNG.

       `do_asr` là bằng chứng đo được từ chính bản ghi âm — một khoản khai tay
       muốn ghi đè nó phải trả lời được "vì sao phép đo sai", và cửa này không
       phải chỗ trả lời câu đó (đó là việc đo lại, T-04 không mở đường tắt).
       `khai_bao` (khách tự nói) và `mac_dinh_cu` (chưa ai đo, chưa ai khai) thì
       không có bằng chứng nào bị ghi đè — sửa tự do là đúng.

    ⚠️ Khách xin đổi SANG ĐÚNG làn đã đo (`lan_moi == lan_hien` khi `do_asr`) là
       một no-op hợp lệ, không phải một xung đột — trả `""`.
    """
    lan = lan_ngon_ngu.chuan_lan(lan_moi)
    if lan not in lan_ngon_ngu.LAN_HOP_LE:
        return "voice_language_required"
    if nguon_hien == NGUON_DO_ASR and lan != lan_ngon_ngu.chuan_lan(lan_hien):
        return "voice_language_measured"
    return ""


# ── Thu hồi: những khoá kho phải xoá ─────────────────────────────────────────

def khoa_can_xoa(owner_id: str, public_id: str) -> str:
    """TIỀN TỐ kho phải coi là bị xoá khi THU HỒI một giọng (T-07).

    🔴 Task 4 (`db, ho_so -> list[str]`, xem `khoa_da_biet` — hàm CHỊ EM ngay
       dưới đây) chỉ tính được từng khoá NÓ BIẾT (từ `VoiceRef`/`VoiceRepr` +
       một khoá nghe thử suy được). Đó không phải "mọi khoá dưới tiền tố":
       `platform_core.storage` (`Storage`/`LocalStorage`,
       `platform_core/storage.py`) KHÔNG có API liệt-kê-theo-tiền-tố, nên
       không hàm nào ở tầng app này biết chắc CÓ hay KHÔNG một tệp lạ nằm
       cùng thư mục mà không hàng CSDL nào trỏ tới (vd một `preview-*` phiên
       bản engine CŨ, còn sống từ trước một lần nâng cấp).

    ⭐ HÀM NÀY VẪN CÓ ÍCH dù không tự xoá được gì bằng nó một mình:
         ① căn cứ để LOG một cảnh báo vận hành ("dọn tay mọi thứ còn sót dưới
           tiền tố này nếu có"), cho `_thu_hoi_mot` (`routes/_p_giong.py`);
         ② chỗ một backend liệt-kê-được-theo-tiền-tố sau này (R2 có
           `list_objects_v2`, hay `LocalStorage` được thêm một hàm xoá cả thư
           mục) cắm vào mà không đổi chữ ký gọi từ route — xem README của
           Task 6 (task-6-report.md) cho lý do KHÔNG thêm hàm đó vào
           `platform_core/storage.py` ở lượt này (thay đổi tầng nền tảng, cần
           một quyết định riêng, không phải việc âm thầm chèn vào một task app).

    ⛔ THUẦN — không chạm CSDL, không chạm kho. Chỉ nối chuỗi, nên không bao
       giờ ném và không cần `db`.
    """
    return f"voice/{owner_id}/{public_id}/"


def khoa_da_biet(db, ho_so) -> list[str]:
    """Mọi khoá `platform_core.storage` mà TA BIẾT CHẮC phải xoá khi THU HỒI
    `ho_so` — không phải "mọi khoá dưới tiền tố" (đó là `khoa_can_xoa`, hàm
    chị em ngay trên; đọc docstring của nó để biết vì sao hai hàm tách nhau).

    Gom TỪ DỮ LIỆU chứ không đoán tên tệp:
      · clip nguồn      — `storage_key` của mọi `VoiceRef` của giọng này;
      · biểu diễn engine — `storage_key` của mọi `VoiceRepr` (chứa `speaker_emb`,
                          thứ `tables.py` nói thẳng là "KHÔNG BAO GIỜ ra ngoài");
      · tệp nghe thử     — khoá HIỆN HÀNH suy được từ `(owner_id, public_id)`
                          (`nghe_thu.khoa_rieng`). Chỉ MỘT phiên bản — một
                          bản nghe thử của một `PHIEN_BAN` engine cũ hơn (nếu
                          còn sót từ trước một lần nâng cấp) sẽ KHÔNG bị liệt
                          ở đây, vì không có cách liệt kê nó (xem `khoa_can_xoa`).

    ⛔ Tệp KẾT QUẢ (`voice/out/{uid}/{job_id}/…`) KHÔNG nằm ở đây: nó thuộc về
       một LƯỢT TẠO, có `job_id`, và đã được `job_content.py` dọn theo hạn 30
       ngày. Thu hồi một giọng không được xoá các bản thu âm khách đã tải về là
       sản phẩm của họ.

    Trả về danh sách khoá (có thể có trùng nếu hai ref cùng khoá — người gọi tự
    khử trùng khi xoá).
    """
    from . import nghe_thu  # lazy: tránh vòng import ở tầng module
    from .tables import VoiceRef, VoiceRepr
    from sqlalchemy import select

    khoa: list[str] = []
    try:
        for r in db.execute(
                select(VoiceRef.storage_key)
                .where(VoiceRef.profile_id == int(ho_so.id))).scalars():
            if r:
                khoa.append(str(r))
        for r in db.execute(
                select(VoiceRepr.storage_key)
                .where(VoiceRepr.profile_id == int(ho_so.id))).scalars():
            if r:
                khoa.append(str(r))
    except Exception:  # noqa: BLE001 - đọc khoá để xoá; hỏng thì vẫn xoá được
        import logging                                 # phần đã gom, đừng dừng
        logging.getLogger(__name__).warning(
            "khong doc het duoc khoa kho de thu hoi %s", ho_so.public_id,
            exc_info=True)
    # Tệp nghe thử riêng — cùng thư mục giọng, tên `preview-*`.
    khoa.append(nghe_thu.khoa_rieng(str(ho_so.owner_id), str(ho_so.public_id)))
    return khoa
