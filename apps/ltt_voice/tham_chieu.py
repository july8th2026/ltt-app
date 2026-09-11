"""
tham_chieu.py — tra cứu và lưu Voice Profile / biểu diễn engine.

Tách khỏi `features.py` vì hai lý do khác nhau, và cả hai đều đáng:

  · `features.py` là **quy tắc**; tệp này là **cách chạm CSDL và kho**. Trộn hai
    thứ đó thì không test được quy tắc mà không dựng một CSDL.
  · Phiên truy vấn phải **ngắn**. Một lượt sinh tiếng có thể mất hàng chục giây;
    giữ một transaction mở suốt thời gian đó là giữ khoá CSDL trong lúc chờ mạng.
    Cùng bài học đã ghi ở `apps/anhnoibo/jobs.py`.
"""
from __future__ import annotations

import hashlib
import io
import logging

from . import lan_ngon_ngu

log = logging.getLogger(__name__)

#: Tiền tố khoá trong `platform_core.storage`. Có `owner_id` trong đường dẫn để
#: một lần nhìn vào kho là biết tệp thuộc về ai.
def khoa_nguon(owner_id: str, public_id: str) -> str:
    return f"voice/{owner_id}/{public_id}/source"


def khoa_bieu_dien(owner_id: str, public_id: str, van_tay: str) -> str:
    #: Có vân tay trong khoá để hai biểu diễn của hai revision **không đè nhau**.
    #: Đè nhau thì lùi model về bản cũ sẽ đọc phải biểu diễn của bản mới.
    return f"voice/{owner_id}/{public_id}/repr-{van_tay}.npz"


def van_tay(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


# ── tra cứu ──────────────────────────────────────────────────────────────────

#: 🔴 CỔNG XUẤT XỨ (U-05) — giá trị DUY NHẤT cho phép một giọng ra kho chung.
#:
#:    Bản kiểm toán 07/09/2026 ghi ranh giới bằng một câu: *"tải được ≠ dùng
#:    thương mại được"*. Cột `VoiceProfile.license_status` là chỗ câu ấy thành
#:    dữ liệu, và hằng số này là chỗ nó thành một phép lọc.
#:
#: ⛔ MỘT giá trị, không phải một danh sách "những giá trị không bị cấm". Khác
#:    biệt ấy quyết định điều gì xảy ra khi ai đó thêm một trạng thái mới:
#:    danh-sách-cấm thì trạng thái mới **lọt qua** (mở, im lặng); danh-sách-cho
#:    thì nó **bị chặn** cho tới khi có người cố ý thêm vào đây.
LICENSE_CHO_PHEP = ("ok",)


def _dieu_kien_kho_chung():
    """Điều kiện SQL cho "giọng này được ở kho chung".

    ⛔ MỘT hàm, dùng ở CẢ HAI chỗ đọc kho chung. Chép điều kiện ra hai nơi là
       cách một bản vá sau này sửa `tim_profile` mà quên `danh_sach` — và hai
       cửa khi ấy nói hai câu khác nhau về cùng một giọng: bộ chọn không hiện
       nó, nhưng gửi thẳng `public_id` thì vẫn đọc được.

    ⚠️ Đây là điều kiện của **kho chung**, không phải của mọi giọng. Giọng
       riêng của một khách không đi qua cổng này: xuất xứ của nó đã có
       `VoiceConsent` trả lời, và bắt một cột thứ hai cùng trả lời câu ấy sẽ
       làm biến mất giọng của chính khách vào ngày migration chạy.
    """
    from sqlalchemy import and_

    from .tables import VoiceProfile
    return and_(VoiceProfile.dung_chung.is_(True),
                VoiceProfile.license_status.in_(LICENSE_CHO_PHEP))


def du_dieu_kien_kho_chung(ho_so) -> bool:
    """Bản THUẦN PYTHON của `_dieu_kien_kho_chung()` — cho MỘT đối tượng
    `VoiceProfile` đã nạp sẵn (không phải một biểu thức SQL), dùng ở nơi ĐÃ CÓ
    SẴN danh sách trong tay và chỉ cần hỏi "hồ sơ NÀY có đủ điều kiện không",
    không đáng một truy vấn CSDL thứ hai.

    ⛔ PHẢI SUY TỪ ĐÚNG HAI CỘT VỚI `_dieu_kien_kho_chung()` (`dung_chung` +
       `license_status`) — hai bản của CÙNG một câu hỏi lệch nhau là đúng lớp
       lỗi mà docstring `_dieu_kien_kho_chung` đã cảnh báo: một cửa nói "kho
       chung", cửa kia nói "không", về CÙNG một giọng. Xem `tach_rieng_chung`
       cho nơi dùng thật.
    """
    return (bool(ho_so.dung_chung)
            and str(ho_so.license_status or "") in LICENSE_CHO_PHEP)


def tach_rieng_chung(ds) -> tuple:
    """Tách một danh sách `VoiceProfile` thành `(rieng_ids, chung_ids)` —
    hình dạng đúng cho `nghe_thu.duong_cho_trang(rieng=, chung=)`.

    🔴 FIX ROUND 1/5 (Task 10, PULLED IN item 5, 2026-09-11) — MỘT HÀM DÙNG Ở
       CẢ BA NƠI (`routes/_p_tao.py`, `_p_giong.py`, `_p_du_an.py`), thay ba
       bản `if g.dung_chung else ...` tự viết. Ba bản cũ bỏ sót ĐÚNG MỘT ô:

       một giọng ĐÃ được đánh `dung_chung=True` (curation) nhưng
       `license_status` CHƯA `"ok"` (`tools/soat_giong.py` đợi soát xuất xứ
       riêng — hai bước, hai câu hỏi khác nhau, xem docstring lệnh `duyet`).
       Với `if g.dung_chung`, giọng đó bị xếp vào `chung` — nhưng
       `nghe_thu._dung_kho_chung` (qua `danh_sach_kho_chung`, đi qua
       `_dieu_kien_kho_chung`) KHÔNG BAO GIỜ dựng preview kho chung cho nó
       (license chưa "ok"), nên `khoa_chung` không bao giờ trúng. Nó cũng bị
       ĐẨY RA KHỎI `rieng` — nơi bản nghe thử dựng LÚC GHI DANH (`khoa_rieng`,
       từ trước khi `dung_chung` được bật) vẫn còn sống. Kết quả: nút nghe
       thử biến mất im lặng cho đúng CHỦ giọng đó, ngay trên trang của họ.

    ⭐ Điều kiện "là chung" PHẢI khớp `_dieu_kien_kho_chung()` — dùng lại
       `du_dieu_kien_kho_chung`, không viết lại một bản thứ ba.

    🔴 FIX ROUND 2/5 (Task 11, carried item (a)) — CÒN THIẾU `trang_thai ==
       "active"`. `du_dieu_kien_kho_chung` chỉ hỏi `dung_chung` + `license_
       status`, không hỏi giọng có đang PHỤC VỤ được không. Một giọng đã
       `dung_chung=True` + `license_status="ok"` nhưng chủ vừa TẮT nó
       (`trang_thai="disabled"`, hoặc `"revoked"`) vẫn lọt vào `chung` — và
       `nghe_thu.danh_sach_kho_chung`/`_giong_chung_dang_hop_le` (cổng đọc
       thật) đều đòi `trang_thai == "active"`, nên nút nghe thử trên chính
       trang của chủ giọng trỏ tới một khoá SẼ 404. Đo được: một khách tắt
       giọng kho chung của mình rồi mở lại `/ltt-voice/giong` thấy nút nghe
       thử vẫn còn — bấm vào là lỗi.

    ⭐ Ép thêm `trang_thai == "active"` cho nhánh `chung`: một giọng dung_chung
       nhưng KHÔNG active rơi về `rieng` — nếu đó là giọng của chính khách
       đang xem trang (trường hợp DUY NHẤT `rieng` từng chứa một giọng
       dung_chung=True, xem `nghe_thu._dung_giong_rieng_con_thieu`), họ vẫn có
       thể còn một bản nghe thử RIÊNG (`khoa_rieng`, dựng lúc ghi danh); nếu
       không, `duong_cho_trang` đơn giản không tìm thấy khoá nào và không
       dựng nút — im lặng đúng cách, không phải một 404.
    """
    rieng: list[str] = []
    chung: list[str] = []
    for g in ds:
        la_chung = (du_dieu_kien_kho_chung(g)
                   and str(getattr(g, "trang_thai", "") or "") == "active")
        (chung if la_chung else rieng).append(g.public_id)
    return rieng, chung


def tim_profile(db, public_id: str, *, owner_id: str, cho_dung_chung: bool = False):
    """Tìm theo `public_id` **và** chủ sở hữu, trong MỘT truy vấn.

    ⛔ Đừng tách thành "tìm theo id rồi so owner": hai bước thì có một khoảng
       trống ở giữa mà một bản vá sau này rất dễ quên bước hai. Một truy vấn thì
       không quên được.

    `cho_dung_chung=True` mở thêm các giọng **kho chung của nền tảng**
    (`dung_chung=True`) — chúng không thuộc ai nhưng ai cũng ĐỌC được.

    🔴 THAM SỐ NÀY MẶC ĐỊNH `False`, VÀ THỨ TỰ ĐÓ QUAN TRỌNG.

       Hàm này là chỗ **duy nhất** kiểm quyền sở hữu giọng, nên nó cũng là chỗ
       một lỗi ở đây trở thành một lỗ rò dữ liệu sinh trắc. Mặc định đóng nghĩa
       là mọi lời gọi CŨ giữ nguyên hành vi cũ, và chỉ những cửa **cố ý** mở
       mới thấy kho chung.

    ⛔ Và nó chỉ mở đường ĐỌC. Sửa, tắt, xoá một giọng dùng chung vẫn đòi đúng
       chủ — xem `_chi_chu_so_huu`. Gộp "ai dùng được" với "ai sửa được" vào một
       phép kiểm là cách một khách tắt mất giọng của cả nền tảng.
    """
    from sqlalchemy import or_, select

    from .tables import VoiceProfile
    if not public_id:
        return None
    dk = [VoiceProfile.public_id == str(public_id)]
    if cho_dung_chung:
        # ⛔ `_dieu_kien_kho_chung()`, KHÔNG phải `dung_chung.is_(True)`. Cổng
        #    U-05 nằm ở đây vì đây là chỗ DUY NHẤT kiểm quyền đọc một giọng.
        if owner_id:
            dk.append(or_(VoiceProfile.owner_id == str(owner_id),
                          _dieu_kien_kho_chung()))
        else:
            dk.append(_dieu_kien_kho_chung())
    elif owner_id:
        dk.append(VoiceProfile.owner_id == str(owner_id))
    else:
        return None
    return db.execute(select(VoiceProfile).where(*dk)).scalar_one_or_none()


def chi_chu_so_huu(ho_so, owner_id: str) -> bool:
    """Người này có được **SỬA** hồ sơ đó không (tắt, đổi tên, xoá).

    ⛔ Tách hẳn khỏi "có được DÙNG không". Một giọng dùng chung thì mọi khách
       đọc được, nhưng chỉ chủ sở hữu — nền tảng — mới đổi được. Không tách thì
       khách đầu tiên bấm "Tắt giọng này" sẽ tắt nó cho tất cả mọi người.
    """
    return bool(ho_so is not None and owner_id
                and str(ho_so.owner_id) == str(owner_id))


def danh_sach(db, *, owner_id: str, gom_tat: bool = False,
              gom_dung_chung: bool = False, ngon_ngu: str = "") -> list:
    """Giọng của một người. `gom_dung_chung` thêm kho chung của nền tảng.

    ⛔ Mặc định KHÔNG gồm kho chung, cùng lý do với `tim_profile`: màn nào muốn
       thấy nó phải nói ra. Một danh sách âm thầm dài thêm là cách một cửa
       "quản lý giọng của tôi" bỗng liệt kê cả giọng nó không được sửa.
    """
    from sqlalchemy import or_, select

    from .tables import VoiceProfile
    dk = VoiceProfile.owner_id == str(owner_id)
    if gom_dung_chung:
        # Cùng một điều kiện với `tim_profile` — xem `_dieu_kien_kho_chung`.
        dk = or_(dk, _dieu_kien_kho_chung())
    q = select(VoiceProfile).where(dk)
    # LÀN. Chốt 01/09/2026: kho giọng tách làn theo ngôn ngữ của clip NGUỒN.
    #
    # ⭐ Đây mới là chỗ làn thật sự làm việc — không phải cảnh báo lúc nộp bài.
    #    Khách lọc đúng làn từ đầu thì không bao giờ chạm tới cảnh báo, và một
    #    cảnh báo không bao giờ nổ là dấu hiệu bộ lọc đang làm đúng việc.
    #
    # ⛔ Mặc định RỖNG = không lọc. Một bộ lọc bật sẵn sẽ giấu mất giọng của
    #    chính khách nếu làn của nó chưa được đặt — và `ngon_ngu` từng là một
    #    cột không ai đọc nên dữ liệu cũ hoàn toàn có thể trống hoặc sai.
    if ngon_ngu in lan_ngon_ngu.LAN_HOP_LE:
        q = q.where(VoiceProfile.ngon_ngu == ngon_ngu)
    if not gom_tat:
        q = q.where(VoiceProfile.trang_thai != "revoked")
    # Kho chung xuống dưới giọng của chính khách: thứ họ tự tạo là thứ họ đi tìm.
    return list(db.execute(
        q.order_by(VoiceProfile.dung_chung.asc(),
                   VoiceProfile.tao_luc.desc())).scalars())


def ung_vien_kho_chung(db) -> tuple:
    """Ứng viên lùi giọng dựng từ **KHO CHUNG**, cho làn mà giọng mẫu không phủ.

    🔴 VÌ SAO HÀM NÀY TỒN TẠI. `lui_giong.tu_giong_mau()` gán cứng
       `ngon_ngu="vi"` vì cả 20 preset của engine đều là giọng Việt. Hệ quả:
       một giọng làn `en` mất biểu diễn thì **không lùi được**, và khách nhận
       một lỗi thay vì một bản đọc.

       Chính `lui_giong.py` đã viết sẵn cách sửa: *"Ngày kho chung có giọng làn
       `en` với giới đã khai, mở rộng bằng cách đưa chúng vào `cac`, không phải
       bằng cách sửa bậc thang."* Kiểm kê 01/09 nói ngày đó đã tới — kho chung
       có 25 giọng, trong đó 17 làn `en`.

    ⛔ `ma` là `public_id`, KHÔNG phải tên preset. Nơi gọi phải nạp biểu diễn
       cho nó qua `tim_profile` + `tim_repr_active` — và đi đúng cửa ấy là cố ý:
       `tim_profile` là chỗ **duy nhất** kiểm quyền đọc, nên đường lùi không
       được có một lối riêng bỏ qua cổng license (`_dieu_kien_kho_chung`).

    ⚠️ CHỈ trả giọng có `gioi` đã khai. `lui_giong.chon()` cũng từ chối `""`,
       nên lọc ở đây là thừa về mặt kết quả — nhưng nó làm **ý định** hiện ra ở
       chỗ dữ liệu được dựng, thay vì để một bộ lọc ở xa gánh hộ.

    ⚠️ KHÔNG lọc theo biểu diễn còn sống ở đây. Nơi gọi thử nạp và bỏ qua ứng
       viên nạp không được — vì một giọng chung mất biểu diễn là đúng cùng ca
       hỏng đã kéo ta tới đường lùi, và nó có thể xảy ra giữa hai truy vấn.
    """
    from sqlalchemy import select

    from . import lui_giong
    from .tables import VoiceProfile

    q = (select(VoiceProfile)
         .where(_dieu_kien_kho_chung(),
                VoiceProfile.trang_thai == "active",
                VoiceProfile.gioi.in_(("nam", "nu")))
         # Tất định: cùng đầu vào phải cho cùng giọng thay. `lui_giong.chon`
         # cũng sắp lại theo `ma`, nhưng sắp ở đây làm phép đo lặp lại được.
         .order_by(VoiceProfile.public_id.asc()))
    return tuple(
        lui_giong.UngVien(ma=str(p.public_id), gioi=str(p.gioi or ""),
                          ngon_ngu=str(p.ngon_ngu or ""),
                          nhan=str(p.ten_hien_thi or ""))
        for p in db.execute(q).scalars())


def tim_repr_active(db, profile_id: int):
    from sqlalchemy import select

    from .tables import VoiceRepr
    return db.execute(
        select(VoiceRepr).where(
            VoiceRepr.profile_id == int(profile_id),
            VoiceRepr.trang_thai == "dang_dung")
        .order_by(VoiceRepr.tao_luc.desc())
    ).scalars().first()


def danh_sach_kho_chung(db):
    """`[(VoiceProfile, VoiceRepr)]` cho mọi giọng KHO CHUNG đang `active` và
    có biểu diễn còn dùng được.

    ⭐ Dựng cho vòng bảo trì nghe thử (`nghe_thu._dung_kho_chung`): nó cần cả
       hồ sơ (để biết LÀN — đọc câu tiếng Việt hay tiếng Anh, xem
       `nghe_thu.cau_cho_lan`) lẫn biểu diễn (để nạp `ref_b64` khi cần dựng).

    ⛔ ĐI QUA `_dieu_kien_kho_chung()`, không tự viết `dung_chung.is_(True)`.
       Cổng license U-05 nằm trong đó, và một giọng chưa soát xuất xứ thì không
       được dựng bản demo — dựng nghĩa là mang nó ra chào bán.

    ⛔ TRẢ `VoiceRepr` THÔ, KHÔNG GIẢI MÃ Ở ĐÂY. Giải mã (`nap_ref_b64`) là một
       lượt đọc kho + decode base64 — không rẻ, và ở một lượt bảo trì bình
       thường phần lớn giọng kho chung ĐÃ có tệp nghe thử rồi. Trả thẳng biểu
       diễn để người gọi chỉ giải mã cho giọng THẬT SỰ còn thiếu — kiểm
       `co_san` TRƯỚC `nap_ref_b64`, xem `nghe_thu._dung_kho_chung`.

    ⚠️ Bỏ qua giọng KHÔNG có biểu diễn active (`tim_repr_active` trả `None`):
       không có gì để nạp, cùng lý do với `_dung_giong_rieng_con_thieu` của
       `nghe_thu.py`.
    """
    from sqlalchemy import select

    from .tables import VoiceProfile

    ra = []
    q = select(VoiceProfile).where(
        _dieu_kien_kho_chung(), VoiceProfile.trang_thai == "active"
    ).order_by(VoiceProfile.tao_luc.asc())
    for ho_so in db.execute(q).scalars():
        bd = tim_repr_active(db, ho_so.id)
        if bd is not None:
            ra.append((ho_so, bd))
    return ra


def tim_ref_theo_hash(db, profile_id: int, sha256: str):
    from sqlalchemy import select

    from .tables import VoiceRef
    return db.execute(
        select(VoiceRef).where(VoiceRef.profile_id == int(profile_id),
                               VoiceRef.sha256 == str(sha256))
    ).scalar_one_or_none()


# ── kho ──────────────────────────────────────────────────────────────────────

def nap_ref_b64(bieu_dien) -> str:
    """Đọc `.npz` biểu diễn từ kho, trả base64 để gửi sang sidecar."""
    import base64

    from platform_core.storage import get_storage
    st = get_storage()
    with st.open(bieu_dien.storage_key) as f:
        return base64.b64encode(f.read()).decode("ascii")


def luu_bieu_dien(*, owner_id: str, public_id: str, ref_b64: str) -> tuple:
    """Ghi `.npz` biểu diễn vào kho. Trả `(storage_key, van_tay)`."""
    import base64

    from platform_core.storage import get_storage
    raw = base64.b64decode(ref_b64)
    vt = van_tay(raw)
    khoa = khoa_bieu_dien(owner_id, public_id, vt)
    get_storage().put(khoa, io.BytesIO(raw), content_type="application/octet-stream")
    return khoa, vt


def luu_nguon(*, owner_id: str, public_id: str, data: bytes, mime: str) -> str:
    """Ghi tệp GỐC bất biến. Không nén, không chuyển đổi, không cắt.

    ⛔ Bản gốc là thứ duy nhất cho phép **dựng lại** biểu diễn khi lên engine mới
       (QĐ-3). Xử lý nó trước khi lưu là vứt đi khả năng đó, và không ai phát
       hiện ra cho tới ngày cần dùng.
    """
    from platform_core.storage import get_storage
    duoi = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
            "audio/mp4": "m4a", "audio/x-m4a": "m4a"}.get(mime, "bin")
    khoa = f"{khoa_nguon(owner_id, public_id)}.{duoi}"
    get_storage().put(khoa, io.BytesIO(data), content_type=mime)
    return khoa


def tuy_chon_preset(db, user_id: str) -> list:
    """Kho giọng **DÙNG CHUNG** của nền tảng, cho `ToolSpec.tuy_chon_dong`.

    🔴 VÌ SAO CẦN, TÁCH HẲN KHỎI `tuy_chon_voice_id`. Hàm kia chỉ trả giọng
       **nhân bản của chính người dùng** — một tài khoản chưa nhân bản giọng nào
       thì nhận về danh sách rỗng. Đo 04/09 trên tài khoản kiểm: ô chọn giọng
       của ChatLTT **không hiện ra**, nên con đường "chọn giọng" chưa từng tồn
       tại với phần lớn khách; họ chỉ có đúng một giọng mặc định.

    ⭐ Nhưng nền tảng đã có sẵn **20 giọng mẫu** gắn nhãn giới/vùng/phong cách
       (`giong_mau.py`), và `speech.ltt` đã nhận `preset` từ lâu. Thứ thiếu chưa
       bao giờ là năng lực — chỉ là không ai mời chúng ra màn hình.

    ⛔ Nhãn KHÔNG dịch ở đây. `NHAN_*` là chuỗi đã đánh dấu `N_()`; dịch sớm
       trong một hàm chạy ở tầng danh mục là ghim ngôn ngữ của tiến trình vào
       một danh sách nhiều phiên cùng đọc. Bên hiển thị dịch, như `_p_giong.py`.

    ⚠️ `db` và `user_id` không dùng tới — kho chung không thuộc về ai. Chữ ký
       vẫn giữ nguyên vì đó là hợp đồng của `tuy_chon_dong`.
    """
    from . import giong_mau

    # ⭐ XEP THEO PHONG CACH, khong theo thu tu khai bao. Ben tieu thu lay
    #    phan tu DAU LAM MAC DINH, nen thu tu o day la mot QUYET DINH san pham
    #    chu khong phai mot chi tiet: de `tin_tuc` dung dau nghia la moi khach
    #    chua chon gi deu duoc doc bang giong ban tin trang trong.
    #
    # ⛔ Va xep bang DU LIEU chu khong de ben kia do chu tren nhan: nhan da
    #    qua `_()`, nen mot ban dich sang tieng Anh se lam moi phep so chuoi
    #    truot — hong lang le, va hong theo ngon ngu giao dien.
    # ⛔ HANG SO O `giong_mau`, KHONG go lai o day. Ban truoc go tai cho, va
    #    mot bang thu tu thu hai cho cung mot kho giong la hai man hinh moi
    #    cung mot khach hai giong mac dinh khac nhau.
    #
    # ⭐ Va xep bang `muc_dung.xep` chu khong bang `sorted` tai cho: ben trong
    #    mot tang phong cach, thu tu nay den tu muc dung THAT cua ta (U-12),
    #    khong den tu bang chu cai. Anh chup rong thi ket qua bang het thu tu
    #    (phong cach, ma) — dung thu tu truoc 08/09/2026.
    from . import muc_dung
    ra = []
    for g in muc_dung.xep(giong_mau.DANH_SACH):
        nhan = " · ".join(x for x in (
            giong_mau.NHAN_GIOI.get(g.gioi, ""),
            giong_mau.NHAN_VUNG.get(g.vung, ""),
            giong_mau.NHAN_PHONG_CACH.get(g.phong_cach, ""),
        ) if x)
        ra.append({"value": g.public_id,
                   "label": f"{g.ten_hien_thi} ({nhan})" if nhan else g.ten_hien_thi,
                   "gioi": g.gioi, "vung": g.vung, "phong_cach": g.phong_cach,
                   # 🔴 LÀN PHẢI ĐI THEO DANH MỤC. Đây là danh sách mà một sản
                   #    phẩm KHÁC (ChatLTT, palette Agent) dựng ô chọn giọng từ
                   #    đó, và nó không import app này. Danh mục nào đánh rơi
                   #    làn thì bên kia chỉ còn hai đường: mời khách chọn một
                   #    giọng mà cửa nộp sẽ từ chối, hoặc **chép tay** một danh
                   #    sách VI/EN của riêng nó — tức đúng bản chép thứ ba mà
                   #    Q121 vừa dọn đi hai bản.
                   "ngon_ngu": g.ngon_ngu})
    return ra


def tuy_chon_voice_id(db, user_id: str) -> list:
    """Giọng nhân bản của **chính** người dùng, cho `ToolSpec.tuy_chon_dong`.

    Nền tảng gọi hàm này qua tham chiếu trong manifest (H43 Phase 02) để một
    sản phẩm web khác (ChatLTT) hay palette Agent mời đúng giọng của họ mà
    không import app này. Danh sách là **gợi ý cho giao diện**; sở hữu vẫn do
    `features.giai_giong` kiểm lúc thi hành.

    Không gồm kho chung và không gồm giọng đã thu hồi — cùng mặc định với
    `danh_sach`: màn nào muốn thấy kho chung phải nói ra.
    """
    ra = []
    for ho_so in danh_sach(db, owner_id=str(user_id)):
        if getattr(ho_so, "trang_thai", "") != "active":
            continue
        ra.append({"value": str(ho_so.public_id),
                   "label": str(getattr(ho_so, "ten_hien_thi", "") or ho_so.public_id),
                   # Cùng lý do với `tuy_chon_preset`: bên tiêu thụ cần lọc
                   # được theo làn, và nó chỉ lọc được thứ danh mục nói ra.
                   # `chuan_lan` ép về đúng ba giá trị — cột này là `String(16)`
                   # tự do nên `"VI"` hay `"xx"` đều có thể có thật.
                   "ngon_ngu": lan_ngon_ngu.chuan_lan(
                       getattr(ho_so, "ngon_ngu", ""))})
    return ra
