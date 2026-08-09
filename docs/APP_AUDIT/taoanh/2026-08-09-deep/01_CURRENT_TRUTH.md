# 01 — Current Truth: Tạo ảnh AI + Thumbnail

## Capability thật

| Miền | Tạo ảnh tổng quát | Thumbnail | Sự thật audit |
|---|---|---|---|
| Generate | prompt, 4 model, 5 ratio, 1–4 output | topic/title/style/trend/lang/brand/reference | Có worker/provider/storage/credit thật |
| Edit/reference | edit, semantic inpaint, outpaint, style transfer | remix output hoặc upload 1 reference | Không mask pixel; role/strength/multi-reference hạn chế |
| Quote | theo model × count, 5/8/16 | cố định 5 × count | Thumbnail định giá sai model premium |
| Partial result | settle theo ảnh thật | settle theo ảnh thật | UI không nói partial/error/refund |
| History | 12 job mỗi mode, output/error/progress | 12 job, technical score | không search/page/delete/cancel/retry/download rõ |
| Compare | chọn tối đa 2 output | chọn tối đa 2 output | browser-local, không zoom/metadata/decision |
| Brand | không có | một Brand Kit gần nhất | chỉ lưu khi submit paid job; không quản trị độc lập |
| i18n | phần lớn EN | fragment vẫn VI | mode nav bỏ locale |
| Retention | Job 365 ngày; artifact chưa có policy | như trái | purge Job làm mất ownership link nhưng blob còn |

## Evidence registry

| ID | Evidence |
|---|---|
| EV-BR-001 | Desktop general: model/edit/reference/cost/history |
| EV-BR-002 | Desktop thumbnail: 7 nhóm control và history |
| EV-BR-003 | Mobile 390×844: không overflow nhưng form dài 2.802px, CTA ở cuối |
| EV-BR-004 | `/en/taoanh`: general dịch; mode link mất `/en/` |
| EV-BR-005 | `/en/taoanh/thumbnail`: shell EN nhưng authenticated fragment VI |
| EV-BR-006 | Chọn Gemini 3 Pro ở Thumbnail, CTA vẫn 5 credit |
| EV-BR-007 | Edit không source → POST 400, prompt/mode reset, URL dừng `/queue` |
| EV-SRC-001 | manifest/model/cost: general 5/8/16, thumbnail flat 5 |
| EV-SRC-002 | upload validation/storage reference lifecycle |
| EV-SRC-003 | worker partial output/settlement/provider key |
| EV-SRC-004 | templates/poll/history/compare/i18n composition |
| EV-SRC-005 | Job 365-day retention tách artifact policy chưa có |
| EV-TEST-001 | 48 targeted tests pass; không phủ premium thumbnail price, locale fragment, validation draft loss |
| EV-MKT-001 | nguồn chính thức Firefly/Midjourney/Gemini/YouTube |

## Sự thật dữ liệu và vận hành

- Ownership, CSRF, magic/decode/pixel validation và key sanitization đã có.
- Cả route upload đều `await upload.read()` toàn bộ trước giới hạn 8 MB; middleware
  body limit chỉ áp `/agent/`, không áp hai endpoint này.
- Reference upload được xóa khi validation/submit fail, nhưng sau submit không
  có promote/TTL/delete policy. Output cũng không có delete UI.
- Job retention xóa Job sau 365 ngày nhưng artifact không xóa; general owner
  access phụ thuộc Job/result nên blob trở thành vừa inaccessible vừa orphan.
- General poll progress tự động; Thumbnail sau redirect không có poll tương ứng.
- History giới hạn 12; owner lookup phục vụ edit/remix giới hạn 60 recent jobs.
