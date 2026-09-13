"""Lớp tương thích cho engine chuyển từ `bot_dungvideo`.

Engine vào đây **nguyên vẹn** — mọi ngưỡng, mọi hằng số, mọi nhánh rẽ giữ y bản
đã chạy một năm. Thứ duy nhất phải đổi là bốn module hạ tầng của bot
(`utils/log.py`, `utils/paths.py`, `utils/ffmpeg.py`, `dll_fix.py`) vì chúng
không đi theo. Bốn tệp ở đây thay chúng, **giữ nguyên chữ ký**.

⛔ Đừng "chuẩn hoá" chữ ký cho giống phần còn lại của kho: 29 tệp engine gọi
   chúng, và một chữ ký khác sẽ làm 29 tệp ấy hỏng **lúc chạy**, không phải lúc
   nạp.
"""
