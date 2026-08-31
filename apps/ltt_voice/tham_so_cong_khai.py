"""
tham_so_cong_khai.py — vài hằng số mà CẢ HAI phía cùng phải biết.

🔴 VÌ SAO TỆP NÀY TỒN TẠI THAY VÌ IMPORT `voice_sidecar.tham_so`:

   `apps/ltt_voice/` chạy trong **venv nền tảng**; `voice_sidecar/` chạy trong
   **venv cách ly** có torch và vieneu. Một `import voice_sidecar.tham_so` từ
   manifest sẽ kéo theo cả cây phụ thuộc đó vào tiến trình web và worker — tức
   đúng thứ mà venv cách ly sinh ra để tránh.

   Nên hằng số dùng chung sống ở đây, và `tests/test_331_ltt_voice_tham_so.py`
   chốt hai bên khớp nhau. Hai bản sao không có phép kiểm là hai bản sao sẽ lệch;
   hai bản sao **có** phép kiểm là một hợp đồng.
"""
from __future__ import annotations

#: Trần của MỘT LƯỢT SINH. Phải khớp `voice_sidecar.tham_so.TRAN_KY_TU_MOT_LUOT`.
#:
#: Đây là TRẦN CHẤT LƯỢNG (Q119), không phải trần hiệu năng: upstream #168 báo
#: giọng bắt đầu trôi từ khoảng 3.000 ký tự. Đo 30/08 cho thấy 3.000 ký tự vẫn
#: SINH RA ĐƯỢC (17,6 giây, không lỗi) — nên con số này không đến từ giới hạn kỹ
#: thuật, nó đến từ chỗ chất lượng bắt đầu tụt. Nới nó phải qua cổng V10.
TRAN_MOI_LUOT_SINH = 1500

#: Trần của MỘT YÊU CẦU của khách.
#:
#: 🔴 HAI TRẦN NÀY LÀ HAI THỨ KHÁC NHAU, và trước 31/08/2026 chúng là một con số.
#:
#:    Hệ quả của việc gộp: văn bản 3.000 ký tự bị **từ chối**, trong khi chính
#:    thông điệp lỗi của cổng đã nói *"Van ban dai hon phai di duong long-form
#:    nhieu luot sinh"* — con đường ấy chưa bao giờ được xây. `chia_doan()` có
#:    sẵn trong `text_pipeline.py` và **không được gọi ở đâu cả**; `jobs.py` gán
#:    cứng `so_doan=1`.
#:
#: ⭐ Tách hai trần ra thì mỗi con số nói đúng một điều:
#:      · `TRAN_MOI_LUOT_SINH`   — model đọc liền được bao nhiêu trước khi trôi
#:      · `TRAN_KY_TU_CONG_KHAI` — khách gửi được bao nhiêu trong một lần
#:    Yêu cầu dài hơn một lượt thì **chia rồi ghép**, không từ chối.
#:
#: ⚠️ Vẫn giữ 1.500 cho tới khi đo được chất lượng bản GHÉP ở 3.000 và 5.000 ký
#:    tự. Đường đã có, cổng chưa mở — và thứ tự đó là có chủ ý: hạ tầng sẵn sàng
#:    không phải là bằng chứng chất lượng. Nới nó vẫn phải qua V10.
#:
#: ✅ MỘT trong các điều kiện ấy đã xong (01/09/2026): **trôi tông đã đo, và
#:    không có**. Ba lượt độc lập trên bài 12 đoạn, `tools/do_troi_tong.py`:
#:    chênh F0 giữa các đoạn 11–20 Hz so với sàn nhiễu (độ lệch F0 *bên trong*
#:    một đoạn) 19–26 Hz, độ dốc −0,2 đến +1,1 Hz mỗi đoạn. Không vượt sàn, và
#:    phần vượt thì không có hướng.
#:
#: ⛔ ĐỪNG đọc điều đó thành "nới được rồi". Trôi tông là MỘT chiều của chất
#:    lượng; V10 còn CER/WER, tương đồng người nói, clipping, tỉ lệ hỏng. Một
#:    phép đo không thay được một cổng — đó đúng là cách một cảnh báo đúng bị
#:    biến thành một lời cho phép.
#:
#: ✅ Và trần tuyệt đối cũ đã BỎ. Trước 01/09 nó là `TRAN_MOI_LUOT_SINH ×
#:    voice_sidecar.tham_so.TRAN_SO_VAN_BAN_BATCH` (= 8 đoạn), vì cửa văn bản
#:    dài áp kích thước một lượt gộp lô lên chính người gọi — bài 12 đoạn nhận
#:    `413`. Nay cửa tự chia nhóm, nên số đoạn không còn là hợp đồng của khách.
TRAN_KY_TU_CONG_KHAI = 1500
