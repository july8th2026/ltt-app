"""
runtime_noi_bo — cửa gọi năng lực AI **từ bên trong nền tảng**, không cần khoá API.

## Vì sao gói này tồn tại (H43 Phase 02, 2026-09-02)

Một sản phẩm web của chính nền tảng (ChatLTT) cần gọi `text.chat`, `image.ltt`,
`speech.ltt` cho **người dùng đã đăng nhập**. Khảo sát mã cho thấy mọi mảnh đã
có — admission, giữ chỗ, mở luồng, đếm token, quyết toán, nộp job, tính giá —
nhưng chúng chỉ được **lắp ráp** ở hai chỗ, và cả hai đều đòi một `Principal`
sinh từ khoá API bán ra ngoài (`server/api/streaming.py`, `server/api/jobs.py`).

Ba lựa chọn đã cân:

  · Dựng `Principal` giả cho người dùng web — kéo theo policy/rate/idempotency
    của khoá API vào một đường không có khoá nào để đo. **Bác.**
  · Để app tự lắp ráp lại các mảnh — là đường đếm token/quyết toán **thứ hai**,
    đúng thứ PA-7 cấm và đúng thứ đã gây lỗi tiền ở cửa job trước đây. **Bác.**
  · Hạ phần lắp ráp xuống đây thành một **facade mỏng**, rồi cho `server/api`
    gọi lại nó. Một đường, hai cửa. **Chọn.**

## Bốn hàm, và thứ nào KHÔNG ở đây

  `luong.chuan_bi` / `luong.mo_thuong_nguon` / `luong.mo_luong`
      cửa STREAM: admission → giữ chỗ → commit → mở luồng → đếm → quyết toán.
      `mo_luong` sinh **sự kiện canonical**; `mo_luong_tho` giữ byte nguyên xi
      cho `server/api/streaming.py`.
  `danh_muc.danh_muc`
      phép chiếu catalog cho một client nội bộ, lọc bằng allowlist của sản phẩm.
  `job.bao_gia` / `job.nop_job`
      giá + nộp job có giữ chỗ, qua `job_submit.submit_with_credit` — KHÔNG
      phải một đường nộp thứ hai.

⛔ Gói này **không** biết tên app nào (test_60 chốt), **không** import `apps.*`
   hay `server.*` (test_147 chốt), **không** giữ giá, **không** giữ hàng đợi.
   Nó chỉ gọi tiếp những thứ đã có, theo đúng thứ tự đã được đo là đúng.
"""
