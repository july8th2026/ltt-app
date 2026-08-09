# 01 — Current Truth: Prompt AI OMMI

## Bề mặt đang tồn tại

| Miền | Backend hiện có | UI khách hàng hiện có | Sự thật audit |
|---|---|---|---|
| Project | CRUD, clone, archive, snapshot/restore, export | Tạo/sửa brief, scene count, export | Clone/archive/snapshot/restore không lộ ở workspace mới |
| Director | Quote → job → apply kết quả | Quote, chạy toàn project | `applyJob()` gửi revision 0 nên project đã lưu sẽ conflict 409 |
| Resource | upload, generate, variants, usage | CRUD/upload/generate cơ bản | Không gắn resource vào project/scene; lifecycle blob chưa kín |
| Storyboard | scene CRUD/reorder/history/compare/restore, resource/style/meta ids | scene CRUD, quote/run/cancel/retry | Thiếu attach/reorder/camera/continuity/style/meta trên UI |
| Libraries | prompt/style/meta CRUD/version | 3 màn hình thư viện | Có dữ liệu nhưng không có đường dùng vào workflow |
| Handoff | route sang image/video app | Không có ở workspace mới | Lời hứa production chain chưa thực hiện được A–Z |
| Jobs | create/poll/cancel/retry/overview | recent jobs rút gọn | Mất job cross-app; phân loại sai khi thiếu `operation` |
| Settings | preference language/theme/model policy | language/theme/default controls | theme không áp dụng; model selector không tồn tại khi run |
| Legacy | `/classic` wizard 5 bước giàu control | vẫn public | Hai sản phẩm UI song song, test chính đang khóa legacy |

## Evidence registry

| ID | Loại | Nội dung |
|---|---|---|
| EV-BR-001 | Browser | Workspace desktop, 10 mục nav và overview |
| EV-BR-002 | Browser | Tạo project 4 cảnh, quote Director 6 credit, hủy trước provider |
| EV-BR-003 | Browser | Tạo/upload/generate resource; quote 5 credit, hủy |
| EV-BR-004 | Browser | Mobile panel chặn nav; prompt mất khi click sát autosave; generate trả 422 |
| EV-BR-005 | Browser | `/en/` chỉ dịch platform shell, toàn bộ app vẫn tiếng Việt |
| EV-BR-006 | Browser | Chọn nền sáng rồi reload nhưng body vẫn `rgb(8, 9, 10)` |
| EV-BR-007 | Browser | `/classic` có wizard, asset, Director, Board, export và project controls phong phú hơn |
| EV-SRC-001 | Source | manifest/rollout/migrations và contract app |
| EV-SRC-002 | Source | React IA, routes/screens và control coverage |
| EV-SRC-003 | Source | `ommiApi.applyJob` gửi `{}`; backend bắt revision hiện hành |
| EV-SRC-004 | Source | upload/variant/direct-upload và storage lifecycle |
| EV-SRC-005 | Source | storyboard service có capability chưa nối UI |
| EV-SRC-006 | Source | provider/job/credit/result normalization |
| EV-SRC-007 | Source | overview job classification và metrics p95 |
| EV-TEST-001 | Test | 195 backend test liên quan và 22 frontend test pass; coverage hành trình thiếu |
| EV-MKT-001 | Benchmark | Tài liệu chính thức của 6 sản phẩm tham chiếu |

Ảnh browser nằm tại `evidence/`. Không ảnh nào chứa secret hoặc dữ liệu production.

## Sự thật kiến trúc và dữ liệu

- Bảng OMMI có migrations riêng, ownership/CSRF được kiểm tra ở đa số route.
- UI mới không phải một mặt cắt đầy đủ của domain model; nhiều capability chỉ
  tồn tại ở API hoặc legacy.
- Autosave và paid action dùng chung một cờ `busy`, không có outbox/dirty/conflict
  recovery. Click có thể bị vô hiệu im lặng trước khi blur lưu dữ liệu.
- Upload tin declared MIME, đọc toàn file vào RAM; blob được ghi trước DB và xóa
  variant chỉ xóa row. DB failure/delete/abandon có thể để orphan.
- Result provider thiếu scene được đệm placeholder nhưng chưa có UX partial
  outcome/refund rõ ràng.
- Overall `p95_giay` luôn 0 do list latency bị `pop` trước khi tổng hợp.
