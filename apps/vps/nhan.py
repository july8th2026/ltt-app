"""Nhãn người đọc cho các mã trạng thái của máy.

## Vì sao có file riêng thay vì viết thẳng trong template

`trang_thai` là **mã trong CSDL** — `dang_chay`, `bi_treo`, `da_xoa`. Hiện nguyên
mã đó ra trang là bắt khách đọc thứ được viết cho máy đọc; và một khách nhìn thấy
`bi_treo` không biết máy còn dữ liệu hay đã mất, không biết phải làm gì tiếp.

Đặt ở đây, không trong template, vì **hai trang cùng hiện trạng thái này**
(`vps.html` và `vps_chi_tiet.html`). Hai bản sao của cùng một bảng nhãn thì lần
sửa sau chỉ sửa một bản, và trang còn lại nói một câu khác về cùng một máy.

Nhãn khai bằng `N_()` — **đánh dấu để trích, không dịch ngay**. Gọi `_()` ở đây
sẽ đóng băng ngôn ngữ theo lần nạp module đầu tiên, tức mọi người dùng đều thấy
ngôn ngữ của người vào trước nhất. Dịch thật xảy ra lúc hiển thị, trong template.
"""
from __future__ import annotations

from platform_core.i18n import N_

#: Mã trong CSDL → câu người đọc.
TRANG_THAI = {
    "dang_tao": N_("Đang tạo"),
    "dang_chay": N_("Đang chạy"),
    "da_tat": N_("Đã tắt"),
    "bi_treo": N_("Bị tạm dừng"),
    "loi": N_("Lỗi"),
    "da_xoa": N_("Đã xoá"),
}


#: Mã trong CSDL → **class badge** của `ltt.css`.
#:
#: Ở đây chứ không trong template vì từ 26/08 có **bốn** trang cùng hiện trạng
#: thái (`vps.html`, `vps_chi_tiet.html`, `vps_cai_dat.html`, `vps_console.html`).
#: Bốn bản sao của cùng một bảng màu thì lần sửa sau chỉ sửa một bản, và ba trang
#: còn lại nói một câu khác về cùng một máy.
#:
#: ⚠️ Màu **không bao giờ đứng một mình**: `.badge` của `ltt.css` luôn kèm một
#:    chấm VÀ chữ nhãn. Một ô đỏ không có chữ là một ô vô nghĩa với người không
#:    phân biệt được màu.
BADGE = {
    "dang_tao": "b-warn",
    "dang_chay": "b-ok",
    "da_tat": "b-grey",
    "bi_treo": "b-warn",
    "loi": "b-err",
    "da_xoa": "b-grey",
}

#: Mã trong CSDL → câu **"giờ phải làm gì"**.
#:
#: Một nhãn trạng thái nói máy đang ở đâu; nó không nói người đọc phải làm gì
#: tiếp. `bi_treo` là ví dụ rõ nhất: khách nhìn thấy "Bị tạm dừng" không biết máy
#: còn dữ liệu hay đã mất, và không biết nạp credit thì có lấy lại được không.
#:
#: Rỗng (`""`) là **có chủ ý** cho những trạng thái không cần ai làm gì.
BUOC_TIEP = {
    "dang_tao": N_("Máy đang được tạo. Tải lại trang sau vài phút."),
    "dang_chay": "",
    "da_tat": N_("Máy đã tắt. Bấm “Bật” để chạy lại. Máy đã tắt vẫn tính phí "
                 "vì nó vẫn giữ chỗ và giữ dữ liệu."),
    "bi_treo": N_("Máy bị tạm dừng do hết hạn thanh toán. Dữ liệu vẫn còn. "
                  "Nạp credit để dùng lại."),
    "loi": N_("Máy gặp lỗi. Xem lý do bên dưới, hoặc cài lại máy."),
    "da_xoa": N_("Máy đã bị xoá. Không khôi phục được."),
}

#: Loại sự kiện → câu người đọc, cho nhật ký ở trang máy.
#:
#: Trước 26/08 nhật ký hiện **nguyên mã** (`xin_cai_lai`, `treo_khong_tat_duoc`)
#: cạnh một cột JSON thô. Đó là thứ viết cho người vận hành đọc, không phải cho
#: khách — mà nhật ký này tồn tại chính là để trả lời khách câu *"vì sao máy tôi
#: bị tắt"* sau ba tháng.
#:
#: ⚠️ Chỉ đổi **cách gọi**, không đổi **ngữ nghĩa**. Không gộp hai mã thành một
#:    câu, kể cả khi hai câu nghe gần giống nhau: `tat` là khách bấm, còn
#:    `treo_khong_tat_duoc` là hệ thống thử tắt và thất bại.
SU_KIEN = {
    "tao_moi": N_("Yêu cầu tạo máy"),
    "tao_xong": N_("Máy đã sẵn sàng"),
    "thu_phi": N_("Đã thu phí một chu kỳ"),
    "hoan_tien": N_("Đã hoàn credit"),
    "bat": N_("Máy được bật"),
    "tat": N_("Máy được tắt"),
    "tat_cung": N_("Máy bị tắt cứng"),
    "khoi_dong_lai": N_("Máy khởi động lại"),
    "go_dia_cai": N_("Đã gỡ đĩa cài"),
    "xin_cai_lai": N_("Yêu cầu cài lại máy"),
    "khoi_phuc": N_("Khôi phục về ảnh chụp"),
    "sao_luu": N_("Đã chụp ảnh máy"),
    "bi_treo": N_("Máy bị tạm dừng"),
    "treo_khong_tat_duoc": N_("Tạm dừng nhưng chưa tắt được máy"),
    "dung_lai": N_("Máy dừng lại"),
    "xin_xoa": N_("Yêu cầu xoá máy"),
    "da_xoa": N_("Máy đã bị xoá"),
    # Máy đã xoá nhưng địa chỉ IP chưa trả về được cho nhà cung cấp. Khách cần
    # thấy nó: nó giải thích vì sao một địa chỉ họ từng dùng chưa biến mất.
    "ip_chua_tra_duoc": N_("Chưa trả được địa chỉ IP"),
    "loi": N_("Có lỗi xảy ra"),
}

#: Sự kiện nào là **tin xấu** — dùng để chọn màu chấm trên dòng thời gian.
SU_KIEN_XAU = frozenset({
    "loi", "bi_treo", "treo_khong_tat_duoc", "da_xoa", "dung_lai",
})

#: Hậu tố mà `dieu_khien._lam` gắn vào khi một thao tác thất bại.
_HAU_TO_LOI = "_that_bai"


def trang_thai(ma: str) -> str:
    """Nhãn cho một mã trạng thái.

    Mã lạ thì **trả về chính nó**, không trả chuỗi rỗng: một ô trống trên trang
    làm khách tưởng máy không có trạng thái, còn một mã lạ hiện ra ít nhất cho
    ta thứ để tra khi họ chụp màn hình gửi tới.
    """
    ma = str(ma or "").strip()
    return TRANG_THAI.get(ma, ma)


def badge(ma: str) -> str:
    """Class badge cho một mã trạng thái. Mã lạ → xám, **không** → xanh.

    Fail-closed về phía thận trọng: một trạng thái ta chưa biết mà hiện màu
    "khoẻ" là nói một điều ta không kiểm được.
    """
    return BADGE.get(str(ma or "").strip(), "b-grey")


def buoc_tiep(ma: str) -> str:
    """Câu "giờ làm gì" cho một mã trạng thái, hoặc chuỗi rỗng."""
    return BUOC_TIEP.get(str(ma or "").strip(), "")


def su_kien(loai: str) -> str:
    """Nhãn người đọc cho một loại sự kiện.

    Xử lý cả hậu tố `_that_bai` mà `dieu_khien._lam` sinh động
    (`bat_that_bai`, `khoi_dong_lai_that_bai`…) — nếu không thì mỗi thao tác cần
    **hai** dòng trong bảng trên, và một trong hai sẽ bị quên.

    Mã lạ trả về chính nó, cùng lý do với `trang_thai()`.
    """
    loai = str(loai or "").strip()
    if loai.endswith(_HAU_TO_LOI):
        goc = SU_KIEN.get(loai[: -len(_HAU_TO_LOI)])
        if goc:
            # Không dịch ở đây — `N_()` chỉ đánh dấu, template mới tra. Trả về
            # msgid ghép sẽ tạo một chuỗi KHÔNG có trong catalog và luôn ra
            # tiếng Việt trên bản EN. Nên trả cặp và để template ghép.
            return goc
    return SU_KIEN.get(loai, loai)


def su_kien_that_bai(loai: str) -> bool:
    """Loại sự kiện này có phải một lần **thất bại** không."""
    return str(loai or "").strip().endswith(_HAU_TO_LOI)


def su_kien_xau(loai: str) -> bool:
    """Sự kiện này có phải tin xấu không — quyết định màu chấm trên nhật ký."""
    loai = str(loai or "").strip()
    return loai in SU_KIEN_XAU or su_kien_that_bai(loai)
