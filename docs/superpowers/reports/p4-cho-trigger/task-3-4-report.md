# P4 Task 3 + 4 — `core.wait` (webhook · event) và `core.human`

## Nguồn đã tra
- `activepieces#3798` *"Create Approval Link ⇒ Wait for Approval doesn't work when there's a step in between"*, `#14388` *"Support multiple pauses within a single step run"* — định danh điểm chờ phải mang đủ ngữ cảnh.
- `activepieces#15626` *"Subflow INTERNAL_ERROR fails the waiting parent instantly… its Return Response is dropped"* ⇒ gửi vào điểm chờ **đã đóng** trả **409**, không phải một 200 nói dối.
- Flowise/Langflow HumanInput: resume bằng **API**, **hết hạn thì định tuyến**. Spec §5.7: mặc định `reject`.
- Spec §8.4: nguồn sự kiện trong phạm vi **chỉ** `workflow.run.finished`.

## Đỏ → xanh
⚠️ **Khai ra**: hai task này tôi viết **mã trước, test sau** (gộp một lượt), nên không có dòng đỏ tự nhiên. Thay bằng **tiêm lỗi** — và tiêm lỗi cắn thật:
```
# bo `vong=vong` khoi khoa diem cho + mac dinh `approve` khi thieu quyet dinh
2 failed, 10 passed   tests/test_1793_wf_core_wait_human.py
# khoi phuc
12 passed             tests/test_1793_wf_core_wait_human.py
```

## Đã làm
- `core.wait mode=webhook`: URL `/hooks/wp/{id}` + token một-lần; CSDL **chỉ** giữ bản băm.
- `core.wait mode=event`: hỏi **lười** trong `tiep_mot` — nó đã cầm sẵn `node` + `vong`, nên không cần một bộ phát riêng phải *tìm lại* ngữ cảnh (chính việc tìm lại là chỗ đẻ ra bộ sinh khoá thứ hai). Không nghe sự kiện của **chính run mình**; bộ lọc hỏng ⇒ `FAILED`, không treo.
- `core.human`: hai nhánh `approve`/`reject`; ⛔ **không có mặc định** (thiếu/sai `quyet_dinh` ⇒ 400); hết hạn mặc định `reject`.

## Chưa làm được
- `core.wait mode=event` quét `workflow_event` từ `wp.created_at` **mỗi tick**, không có con trỏ bền. Với một điểm chờ sống lâu trên một hệ nhiều sự kiện, đó là `O(sự kiện)` mỗi tick. Chưa đo ngưỡng.
- `core.webhook_response` (trả thân tuỳ biến, spec §8.3 chế độ `dong_bo`) **chưa làm**.
