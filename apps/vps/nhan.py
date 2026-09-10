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

#: Mã tác vụ (`trang_thai_may.TAC_VU`) → câu người đọc.
#:
#: Đây là thứ trả lời câu *"vì sao trang không đổi gì sau khi tôi bấm"*. Trước
#: VPS V2 không có chỗ nào để hỏi, nên câu trả lời duy nhất là một lời nói dối
#: phát ra ngay lúc bấm ("Đã tắt" cho một máy chưa tắt).
#:
#: ⚠️ Mọi nhãn ở đây đều là thì **đang diễn ra**. Một nhãn quá khứ ("Đã tắt")
#:    trong bảng này sẽ nói dối đúng vào lúc việc chưa xong.
TAC_VU = {
    "dang_bat": N_("Đang bật"),
    "dang_tat": N_("Đang tắt"),
    "dang_kd_lai": N_("Đang khởi động lại"),
    "dang_chup": N_("Đang chụp ảnh"),
    "dang_khoi_phuc": N_("Đang khôi phục"),
    "dang_dung_lai": N_("Đang cài lại"),
    "dang_xoa": N_("Đang xoá"),
    "dang_cap_phat": N_("Đang tạo"),
}

#: Mã bước con của một thao tác → câu người đọc.
#:
#: Mã trong CSDL, câu ở đây — cùng khuôn với `trang_thai`. Ghi thẳng tiếng Việt
#: vào cột `buoc` thì chuỗi đó **không dịch được** sang tiếng Anh và không đếm
#: được, vì nó nằm trong dữ liệu chứ không nằm trong catalog.
BUOC = {
    "gui_lenh_tat": N_("Đang gửi lệnh tắt"),
    "cho_may_tat": N_("Đang chờ máy tắt"),
    "gui_lenh_bat": N_("Đang gửi lệnh bật"),
    "cho_may_bat": N_("Đang chờ máy bật"),
    "tat_truoc_khoi_phuc": N_("Đang tắt máy trước khi khôi phục"),
    "dang_khoi_phuc_anh": N_("Đang khôi phục ảnh chụp"),
    "bat_lai_sau_khoi_phuc": N_("Đang bật lại máy"),
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
    # Bốn dòng `xin_*` (VPS V2/ADR-03) là **yêu cầu**, khác hẳn bốn dòng kết quả
    # bên dưới. Từ khi ba lệnh điện đi qua hàng đợi, một cú bấm sinh HAI dòng:
    # "yêu cầu bật" lúc bấm, rồi "máy được bật" khi đã đo được là nó bật thật.
    # Gộp làm một là quay lại đúng lời nói dối cũ — nói "đã bật" lúc mới bấm.
    "xin_bat": N_("Yêu cầu bật máy"),
    "xin_tat": N_("Yêu cầu tắt máy"),
    "xin_tat_cung": N_("Yêu cầu tắt cứng"),
    "xin_khoi_dong_lai": N_("Yêu cầu khởi động lại"),
    "xin_khoi_phuc": N_("Yêu cầu khôi phục ảnh chụp"),
    "tao_xong": N_("Máy đã sẵn sàng"),
    "thu_phi": N_("Đã thu phí một chu kỳ"),
    "hoan_tien": N_("Đã hoàn credit"),
    "bat": N_("Máy được bật"),
    "tat": N_("Máy được tắt"),
    "tat_cung": N_("Máy bị tắt cứng"),
    "khoi_dong_lai": N_("Máy khởi động lại"),
    "go_dia_cai": N_("Đã gỡ đĩa cài"),
    # Ghi lại vì nó đổi thứ mà ô xác nhận phá huỷ đòi gõ: khách đổi tên rồi ba
    # tháng sau không xoá được máy sẽ cần biết tên cũ là gì.
    "doi_ten": N_("Đổi tên máy"),
    "xin_cai_lai": N_("Yêu cầu cài lại máy"),
    "khoi_phuc": N_("Khôi phục về ảnh chụp"),
    "sao_luu": N_("Đã chụp ảnh máy"),
    "bi_treo": N_("Máy bị tạm dừng"),
    "bi_cach_ly": N_("Máy bị cách ly mạng"),
    "go_cach_ly": N_("Đã gỡ cách ly mạng"),
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
    "bi_cach_ly",
})

#: Mã lỗi (`vps_thao_tac.ma_loi`, `TacVuLoi.ma`) → câu cho **khách** đọc.
#:
#: Đo trên production 09/09/2026: trang máy in ra cho khách nguyên văn
#: `VpsJobError: Proxmox tu choi lenh: <lỗi thô của Proxmox>` — ở **hai** chỗ
#: cùng lúc (`may.ly_do` và cột chi tiết của nhật ký). Cùng một hạng lỗi với
#: lần rò trên trang bán hàng công khai, chỉ khác trang.
#:
#: ⛔ Không mã nào ở đây được nhắc tên `Proxmox`, tên biến môi trường, cổng
#:    `8006`, hay tên class Python. `services/proxmox.py` viết rằng khách
#:    "không bao giờ nhìn thấy" lớp đó — một câu lỗi cũng là một lần nhìn thấy.
#:
#: ⭐ Câu ở đây phải nói được **giờ khách làm gì**, không chỉ nói việc hỏng.
#:    Một câu "Đã xảy ra lỗi" đúng nhưng vô dụng thì khách vẫn phải mở phiếu hỗ
#:    trợ — tức ta không tiết kiệm được gì, chỉ giấu đi.
MA_LOI = {
    "proxmox_tu_choi": N_("Hạ tầng từ chối lệnh này. Đội vận hành đã nhận được "
                          "nhật ký; thử lại sau ít phút."),
    "tac_vu_qua_han": N_("Máy chủ xử lý quá lâu nên chúng tôi dừng chờ. Trạng "
                         "thái máy có thể đã đổi — tải lại trang để xem."),
    "tac_vu_that_bai": N_("Lệnh chạy nhưng không hoàn tất. Đội vận hành đã nhận "
                          "được nhật ký."),
    "dien_khong_dat": N_("Lệnh đã chạy xong nhưng máy không về đúng trạng thái "
                         "mong muốn. Thử lại, hoặc liên hệ hỗ trợ."),
    "khong_doc_duoc": N_("Tạm thời không đọc được trạng thái máy. Tải lại trang "
                         "sau ít phút."),
    "tac_vu_loi": N_("Thao tác không hoàn tất. Đội vận hành đã nhận được nhật ký."),
    "anh_khong_dung": N_("Ảnh chụp này không dùng được để khôi phục. Hãy chọn "
                         "một ảnh khác."),
}

#: Câu dùng khi mã lỗi lạ — xem `ma_loi()` để biết vì sao nó **không** trả về
#: chính mã như mọi bảng khác trong tệp này.
MA_LOI_KHONG_RO = N_("Thao tác không hoàn tất. Đội vận hành đã nhận được nhật ký.")

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


def tac_vu(ma: str) -> str:
    """Nhãn cho một mã tác vụ đang chạy. Mã lạ trả về chính nó."""
    ma = str(ma or "").strip()
    return TAC_VU.get(ma, ma)


def buoc(ma: str) -> str:
    """Nhãn cho một bước con. Mã lạ trả về chính nó, rỗng trả rỗng."""
    ma = str(ma or "").strip()
    return BUOC.get(ma, ma)


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


def ma_loi(ma: str) -> str:
    """Câu cho khách, từ một **mã** lỗi.

    ⚠️ Hàm này **không** theo quy ước "mã lạ trả về chính nó" của `trang_thai()`
       và `su_kien()`, và sự lệch đó là chủ ý.

       Ở những bảng kia, thứ truyền vào luôn là một mã do ta sinh ra, nên echo
       nó lại cùng lắm là xấu. Ở đây thì không: chỗ gọi hàm này từng chứa
       **chuỗi lỗi thô** (`f"{type(exc).__name__}: {exc}"`), nên "trả về chính
       nó" đúng bằng việc in lại cái ta vừa đi vá. Fail-closed về phía im lặng.

    Chi tiết kỹ thuật **không mất**: nó ở `log.warning` và ở
    `vps_thao_tac.chi_tiet_loi` (giữ 180 ngày) — hai nơi người vận hành đọc.
    """
    ma = str(ma or "").strip()
    return MA_LOI.get(ma, MA_LOI_KHONG_RO)
