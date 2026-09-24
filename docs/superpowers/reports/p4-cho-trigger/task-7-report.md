# P4 Task 7 — `trigger.cron` bằng `cronsim`

## Nguồn đã tra — và một ĐỔI Ý so với spec
Spec §8.2 chỉ định `croniter`. Tôi dùng **`cronsim`**, tra được:
- `pallets-eco/croniter#258` (**MỞ**, 02/08/2026) — *"get_next skips a fire time when the DST shift is not a whole hour; get_prev and match disagree"*; `#259` — *"croniter_range stop test ignores the UTC offset: silently drops results and returns out-of-interval values"*. Hai lỗi **còn mở**, đúng vào **hai** phép ta cần: tiến (lần bắn kế) và **lùi** (mốc lỡ gần nhất).
- `cuu508/cronsim` (BSD-3-Clause, dùng trong Healthchecks): *"Correctness… match Debian's cron as closely as possible, including its quirky behaviour during DST transitions"*, và có `reverse=True`.
- `n8n#34628` / `#23906` *"Missed schedule trigger can cause unexpectedly long delays"*; `n8n#17187` *"Scheduled tasks executing multiple times at once"*; `activepieces#15114` *"Schedule trigger silently freezes: non-atomic enable pipeline strands flows"*.

## Đỏ → xanh
```
12 failed, 4 passed   tests/test_1795_wf_trigger_cron.py
16 passed             tests/test_1795_wf_trigger_cron.py
```

## Đã làm
- `trigger._TheoCron`: `lan_ke_tiep` / `moc_gan_nhat`, đổi múi giờ → naive-UTC. `kiem()` từ chối **lúc tạo**: cron hỏng, tz hỏng, chu kỳ < 5 phút — đo bằng **hai mốc liên tiếp thật**, không đọc chuỗi (`*/5 * * * *` và `0,5,10,… * * * *` là một lịch viết hai kiểu).
- `tao()` gọi `kiem()` qua `getattr` ⇒ lõi **không biết tên loại nào** (`G42`).
- `ban_trigger.ban_den_han`: đi qua **đúng** cửa `tao_run`; khoá mang **mốc lịch**; `chay_mot_lan` ⇒ **một** run cho mốc **gần nhất** (⛔ không bù 3 ngày = 3 run); `bo_qua` ⇒ không run **nhưng `next_fire_at` vẫn tiến**; 5 lỗi liên tiếp ⇒ tự tắt; một trigger hỏng không chặn trigger lành.

## Một lỗi THẬT bắt được lúc chạy test
`den_han()` tự hỏi đồng hồ trong khi bên gọi đã chốt một mốc `luc` cho cả lượt ⇒ "chọn theo mốc này, tính mốc lịch theo mốc kia". Nay nó nhận `bay_gio` từ bên gọi.

## Chưa làm được
- `SCHEDULE` (theo giây) **chưa bị thay** như spec §8.2 nói; các hàng cũ vẫn mang loại ấy, chưa có di trú.
- `version_mode = "pinned"` có cột nhưng `ban_trigger` vẫn bắn bản **publish**; chưa nối.
