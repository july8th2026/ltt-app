"""B9-3 — chữ Hán sót: con số phải LÊN được báo cáo, và có một vòng dịch lại.

🔴 **Ca thật T1a (28/09).** `5/78` đoạn (**6,4 %**) còn chữ Hán sau khi dịch:
   `吃鸡` ×1 và `狙击` ×4 — hai **từ lóng game**. Khách nhìn thấy chúng trên
   phụ đề đã đốt vào hình.

⭐ **Bộ dò thì ⛔ không hỏng.** Đo trên chính lần chạy ấy: `78/78` dòng
   `asv_work_item` mang khoá `han_lot`, `5` dòng khác rỗng, khớp **chính xác**
   5 đoạn thật sự còn chữ Hán, kèm đoạn trích.

🔴 **Thứ hỏng là ĐƯỜNG BÁO CÁO.** `content_process.outputs` ⛔ không có một
   khoá nào nhắc tới chữ Hán. Con số nằm lại trong `asv_work_item` và ⛔ không
   lên tóm tắt, ⛔ không tới QC, ⛔ không tới khách.

⚠️ Và nó làm một **giả định chính sách hết hạn**: chú thích chọn *"ĐÁNH DẤU,
   ⛔ KHÔNG HUỶ"* với lý do *"0,3 % là hiếm"*. T1a đo **6,4 %** — gấp **21 lần**
   tiền đề ấy. Con số lên báo cáo thì lần sau chính sách được chọn trên **số
   đo**, ⛔ không trên một tiền đề ⛔ không ai kiểm lại.
"""
from __future__ import annotations

from apps.auto_scan_video import long_tieng
from apps.auto_scan_video.giai_doan_noi_dung import LY_DO_HAN_LOT

#: Đúng hai cụm sót thật của T1a.
CAU_SOT = "Có người trúng súng狙击, có người không có gì."
CAU_SACH = "Có người trúng súng bắn tỉa, có người không có gì."


def test_bo_do_bat_dung_hai_cum_cua_T1a():
    """⭐ Đối chứng cho mọi bài dưới: ⛔ không có vế này thì một bộ dò luôn trả
    rỗng cũng làm chúng xanh."""
    assert long_tieng.chu_han_lot(CAU_SACH) == []
    assert len(long_tieng.chu_han_lot(CAU_SOT)) == 1
    assert "狙击" in long_tieng.chu_han_lot(CAU_SOT)[0]
    assert len(long_tieng.chu_han_lot("Trận吃鸡 thật, nam sinh không bỏ.")) == 1


def test_ly_do_dich_lai_NEU_DICH_DANH_cum_con_sot():
    """⛔ Một lời nhắc *"đừng để sót chữ Hán"* ⛔ không nói được nó sót ở ĐÂU.

    Hai cụm của T1a là **từ lóng game** — model dịch trọn câu rồi để nguyên
    đúng hai từ ấy. Lời nhắc phải mang chính cụm đó.
    """
    ly_do = LY_DO_HAN_LOT.format(cum="狙击, 吃鸡")
    assert "狙击" in ly_do and "吃鸡" in ly_do
    # ⛔ ⛔ KHÔNG kèm ví dụ dịch sẵn: *"một ví dụ trong lời nhắc là một mệnh
    #    lệnh ngầm"* — bốn ví dụ không dấu từng làm tụt một tên vốn đúng.
    assert "->" not in ly_do and "bắn tỉa" not in ly_do


def test_loi_nhac_MANG_luat_y_canh_khi_co_doan_bi_che():
    """Vòng sửa dùng LẠI `y_canh` sẵn có, ⛔ không viết đường dịch lại thứ hai.

    ⭐ Và một lô **sạch** phải cho lời nhắc **y hệt bản nền** — nếu không, ta
       làm bẩn đường THƯỜNG để phục vụ đường SỬA, và mọi số đo cũ của đường
       thường hết so sánh được.
    """
    lo = [{"ma": "seg_0006", "chu": "有人抽到狙击", "thoi_luong_giay": 2.0,
           "do_dai_toi_da": 40}]
    chung = dict(tat_ca=lo, ngon_ngu_goc="zh", dac_diem_giong={},
                 ngon_ngu_dich="vi")
    nen = long_tieng.loi_nhac(lo, **chung)
    sua = long_tieng.loi_nhac(
        lo, y_canh={"seg_0006": LY_DO_HAN_LOT.format(cum="狙击")}, **chung)
    assert nen != sua, "y_canh ⛔ khong vao duoc loi nhac"
    assert "狙击" in sua[0]["content"] + sua[1]["content"]
    assert long_tieng.loi_nhac(lo, y_canh={}, **chung) == nen, (
        "mot lo SACH phai cho loi nhac y het ban nen")
