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

#: Trần ký tự công bố cho MỘT lượt gọi. Phải khớp
#: `voice_sidecar.tham_so.TRAN_KY_TU_MOT_LUOT`.
#:
#: Đây là TRẦN CHẤT LƯỢNG (Q119), không phải trần hiệu năng: upstream #168 báo
#: giọng bắt đầu trôi từ khoảng 3.000 ký tự. Đo 30/08 cho thấy 3.000 ký tự vẫn
#: SINH RA ĐƯỢC (17,6 giây, không lỗi) — nên con số này không đến từ giới hạn kỹ
#: thuật, nó đến từ chỗ chất lượng bắt đầu tụt. Nới nó phải qua cổng V10.
TRAN_KY_TU_CONG_KHAI = 1500
