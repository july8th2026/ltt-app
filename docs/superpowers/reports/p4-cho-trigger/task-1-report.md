# P4 Task 1 — Router `/hooks/*` + MỘT nơi sinh khoá khử trùng

## Nguồn đã tra
- `activepieces#14808` *"Rejected webhook auth returns HTTP 200 with no run and no log"* ⇒ token sai trả **401**, không phải 200 im lặng.
- `activepieces#3798`, `#14388`, và quyết định `000015` (activepieces@`17e2ac0b`) — *"Identity is path-keyed… a delay or approval inside a loop used to reuse one waitpoint row across every iteration"*.
- `n8n#17187` *"Scheduled tasks executing multiple times at once"* ⇒ khoá cron mang **mốc lịch**.

## Đỏ → xanh
```
9 failed, 1 passed, 6 errors   tests/test_1790_wf_khoa_cho_va_hook.py
16 passed                      tests/test_1790_wf_khoa_cho_va_hook.py
```
Phép `test_doi_chung_khoa_tran_thi_hai_vong_foreach_TRUNG_NHAU` xanh **cả hai lượt** — nó là đối chứng, nó phải xanh.

## Đã làm
- `khoa_idem.py`: `khoa_cho` gọi **thẳng** `danh_thuc.duong_thi_hanh` (⛔ không bộ sinh khoá thứ hai); vượt `String(120)` thì **băm**, không cắt cụt.
- `noi_lai.py`: một cửa cho mọi tín hiệu từ ngoài (tín hiệu + đóng waitpoint + wakeup, ba bước cùng nhau).
- `han_cho.py` / `han_muc.py`; `server/routes/hooks.py` (401 · 404 · 413 · 429 · 409).
- models + migration `c4a17f9b6d20`.

## Chưa làm được
- Hạn mức §7.3 là **hằng trong mã**, không phải kho settings đổi-được-không-cần-deploy như spec nói. Kho này chưa có bề mặt ấy; một bảng giả vờ đổi được tệ hơn một hằng nói thật.
- `/hooks/wp/{id}` là cửa resume duy nhất; route `POST /agent/api/v3/runs/{id}/human/{wp}` (spec §5.7) **chưa làm** — nó nằm ở `apps/agent`, ngoài quyền của làn này.
