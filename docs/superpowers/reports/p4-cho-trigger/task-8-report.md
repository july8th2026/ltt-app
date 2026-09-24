# P4 Task 8 — `trigger.event` · dedupe · hạn mức

## Nguồn đã tra
- Spec §8.1 (bảng khoá khử trùng), §8.3, §8.4, §7.3, §11.4.
- `activepieces#14808` ⇒ quá hạn mức cũng phải **nói ra** (429), không im lặng bỏ.

## Đỏ → xanh
```
7 failed, 4 passed    tests/test_1796_wf_trigger_webhook_event.py
11 passed             tests/test_1796_wf_trigger_webhook_event.py
```
(4 phép hạn mức webhook xanh ngay từ lượt đỏ — chúng đo phần task 1 đã làm.)

## Đã làm
- `trigger._SuKien` (`EVENT`): không có lịch; quét theo **con trỏ** `(created_at, id)` lưu ở `workflow_trigger.con_tro`. `kiem()` từ chối bộ lọc hỏng **lúc tạo**, và **chỉ kiểm cú pháp**: thử *tính* nó trên một sự kiện giả sẽ từ chối cả `event.outputs.ten == 'x'`, một bộ lọc **đúng**.
- `ban_su_kien`: chỉ ba dòng kết thúc run (spec §8.4 — sự kiện của job ngoài workflow *"phá luật §3.1-3"*); ⛔ **không nghe sự kiện của chính workflow mình** (một vòng có tiền thật: run → sự kiện → run); con trỏ tiến **kể cả** khi dòng đó lỗi hoặc không khớp (dừng ở một dòng hỏng nghĩa là mọi dòng sau nó không bao giờ tới lượt).
- **HAI** chốt khử trùng và cần cả hai: con trỏ keyset **và** khoá `evt:<tid>:<event_id>`. Phép kiểm **xoá con trỏ đi** và đòi khoá vẫn chặn lần hai.
- Hạn mức webhook đếm trên **CSDL** (không bộ đếm trong tiến trình: web nhiều worker ⇒ 60/phút thành 60×N/phút đúng lúc cần đúng), theo **từng trigger** và trong cửa sổ **một phút**.

## Chưa làm được
- `trigger.poll` (piece, §11.4) **chưa làm** — nó thuộc P6 (connector runner).
- ⭐ **Bắt được trong lúc viết chính báo cáo này**: `ban_su_kien` chưa được `dong_co.mot_vong` gọi — nó chạy khi gọi tay và **không bao giờ** chạy thật, vì `trigger.event` không có `next_fire_at` nên `den_han()` không bao giờ trả về nó. Đã nối, và đã thêm `test_vong_dong_co_CO_goi_bo_quet_su_kien` để nói ra điều đó (⛔ một bộ quét không ai gọi là một bộ quét chết).
- `trigger.poll` (piece) vẫn chưa làm — thuộc P6.
