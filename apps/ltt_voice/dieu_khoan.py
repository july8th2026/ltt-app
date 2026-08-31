"""
dieu_khoan.py — điều khoản dùng giọng nói, và bản cam kết sở hữu.

⭐ VÌ SAO LÀ MÃ CHỨ KHÔNG PHẢI MỘT ĐOẠN HTML:

   `apps/vps/dieu_khoan.py` + `test_298` đã chứng minh khuôn này: điều khoản nào
   nhắc tới một con số thì con số đó phải **lấy từ hằng số thật**, không gõ lại.
   Đổi giới hạn mà quên sửa điều khoản là gate đỏ, không phải là một trang web
   nói sai trong im lặng.

⛔ NHÂN BẢN GIỌNG CHẠM QUYỀN NHÂN THÂN. Đây không phải một ô tick cho đẹp: giọng
   nói là đặc điểm nhận dạng của một con người. Sản phẩm này chỉ nhận **giọng của
   chính người dùng hoặc giọng họ được uỷ quyền**, và cam kết đó phải lưu được
   thành dữ liệu đối chiếu được — ai, lúc nào, bản điều khoản nào, tệp nào.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from platform_core.job_content import RETENTION_DAYS

from .audio_input import GIAY_TOI_DA, GIAY_TOI_THIEU, MAX_BYTES
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

#: Đổi bất cứ câu nào bên dưới thì phải đổi chuỗi này. Bản cam kết đã lưu trỏ tới
#: đúng phiên bản, nên không có phiên bản thì không biết khách đã đồng ý với gì.
#: 31/08/2026 — thêm điều "Giữ tệp bao lâu". Bản cam kết cũ vẫn trỏ tới
#: `…-2026-08-30a`, và đó là đúng việc: khách đã đồng ý với bản KHÔNG có
#: điều đó, nên bản ghi phải nói vậy.
PHIEN_BAN_DIEU_KHOAN = "ltt-voice-dk-2026-08-31a"


def cac_dieu() -> list:
    """Điều khoản, với mọi con số LẤY TỪ HẰNG SỐ THẬT."""
    return [
        {
            "tieu_de": _t("Giọng bạn được phép tải lên"),
            "noi_dung": _t(
                "Chỉ tải lên giọng của chính bạn, hoặc giọng bạn có văn bản uỷ "
                "quyền của người nói. Không tải lên giọng người nổi tiếng, giọng "
                "lấy từ phim, video hay bản ghi mà bạn không có quyền."),
        },
        {
            "tieu_de": _t("Clip mẫu"),
            "noi_dung": _t(
                "Từ {min:.0f} đến {max:.0f} giây, tối đa {mb} MB, định dạng WAV, "
                "MP3 hoặc M4A. Chúng tôi giữ nguyên bản clip để có thể dựng lại "
                "giọng khi nâng cấp model."
            ).format(min=GIAY_TOI_THIEU, max=GIAY_TOI_DA,
                     mb=MAX_BYTES // (1024 * 1024)),
        },
        {
            "tieu_de": _t("Độ dài mỗi lượt đọc"),
            "noi_dung": _t(
                "Tối đa {n} ký tự cho một lượt. Văn bản dài hơn nên chia thành "
                "nhiều lượt: giọng đọc giữ được sự đồng nhất tốt hơn khi mỗi "
                "lượt ngắn."
            ).format(n=TRAN_KY_TU_CONG_KHAI),
        },
        {
            "tieu_de": _t("Tiền"),
            "noi_dung": _t(
                "Tính theo số giây tiếng nói thật sự tạo ra, không theo số ký tự "
                "gửi lên. Chúng tôi giữ tạm một khoản theo độ dài văn bản và hoàn "
                "lại phần dư ngay khi xong. Nếu không đo được kết quả, bạn không "
                "bị trừ gì."),
        },
        {
            "tieu_de": _t("Giữ tệp bao lâu"),
            "noi_dung": _t(
                "Tệp tiếng tạo ra được giữ {n} ngày kể từ khi xong, rồi xoá. "
                "Hãy tải về trong khoảng đó. Lịch sử lượt tạo và bút toán credit "
                "vẫn giữ lại để đối chiếu, chỉ tệp là hết hạn."
            ).format(n=RETENTION_DAYS),
        },
        {
            "tieu_de": _t("Đóng dấu"),
            "noi_dung": _t(
                "Mọi tệp tiếng tạo ra đều được đóng một dấu chìm không nghe thấy "
                "để nhận diện nội dung do máy tạo."),
        },
    ]


#: 🔴 `N_()` CHỨ KHÔNG PHẢI `_()`.
#:
#:    Đây là hằng số **cấp module**, tức nó được tính đúng một lần lúc nạp. Gọi
#:    `_()` ở đây sẽ đóng băng ngôn ngữ theo **lần nạp đầu tiên** — nghĩa là mọi
#:    người dùng đều thấy ngôn ngữ của người vào đầu tiên sau khi khởi động lại.
#:
#:    `N_()` chỉ đánh dấu chuỗi cho người dịch; phép dịch thật xảy ra khi
#:    template render, tức đúng lúc đã biết ngôn ngữ của người đang xem.
#:
#: (Gate bắt được: `test_161_i18n_lop_python::test_khong_goi_dich_o_cap_module`.)
CAM_KET = N_(
    "Tôi xác nhận đây là giọng của chính tôi, hoặc tôi được người nói uỷ quyền "
    "sử dụng giọng này.")
