# 05 — Findings: Prompt AI OMMI

## P1 — Release blockers

| ID | Vấn đề | Evidence | Tác động | Fix direction |
|---|---|---|---|---|
| F-001 | `applyJob()` gửi body rỗng, backend nhận revision 0; project thực có revision >0 nên paid Director result conflict 409 | EV-SRC-003 | trả tiền nhưng không nhận storyboard | gửi expected revision canonical, idempotent apply và integration test paid path |
| F-002 | Autosave và action dùng chung `busy`; click sát blur bị vô hiệu im lặng, prompt chưa lưu và mất khi đổi màn hình | EV-BR-004, EV-SRC-002 | mất dữ liệu khách hàng | local draft/outbox, per-action state, flush-before-run, dirty/conflict recovery |
| F-003 | Resource/style/meta/handoff tồn tại rời rạc; workspace mới không hoàn thành được reference→storyboard→image/video | EV-SRC-002/005, EV-BR-007 | core promise không thực hiện A–Z | một canonical project studio, attach `@resource`, per-scene output/handoff |
| F-004 | Upload tin declared MIME, full-buffer; blob ghi trước DB và delete variant không xóa blob | EV-SRC-004 | file giả mạo, RAM pressure, orphan/privacy/cost | signature/decode probe, streaming cap, staging+promote, transactional cleanup/TTL |
| F-005 | Provider trả thiếu scene được đệm placeholder; chưa có partial/refund contract rõ | EV-SRC-006 | charge và kết quả không tương xứng | validate result, explicit partial state, retry missing/refund policy |

## P2 — Phải xử lý trong repair/parity

| ID | Finding |
|---|---|
| F-006 | `/en/` vẫn toàn bộ UI app tiếng Việt; theme “sáng” không áp dụng dù báo đã lưu. |
| F-007 | API validation trả HTML; frontend chỉ parse JSON nên khách chỉ thấy `Lỗi 422`. |
| F-008 | Tạo mới ghi record trống ngay, không setup/name/cancel; tạo rác và khó hiểu. |
| F-009 | Clone/archive/snapshot/restore và library restore/diff có API nhưng thiếu UI. |
| F-010 | Mobile resource panel chặn điều hướng; ribbon ngang khó khám phá; cần keyboard/focus audit đầy đủ. |
| F-011 | Overall `p95_giay` luôn 0 do tổng hợp sau khi đã pop latency list. |
| F-012 | Recent jobs gán sai loại khi thiếu operation và bỏ mất handoff/cross-app jobs. |
| F-013 | Regression hiện nghiêng về legacy; thiếu current Project→Director→Storyboard, mobile, i18n, theme, handoff. |
| F-014 | Project và Brief & Director mở cùng một màn hình; IA trùng nghĩa. |
| F-015 | Reload luôn về Overview; không route/deep-link/screen state. |
| F-016 | Không có model selector khi chạy dù Settings nói model được chọn ở từng lần. |
| F-017 | Director/resource chưa có recovery controls nhất quán cancel/retry; history chỉ recent. |
| F-018 | Search/resource request theo ký tự chưa debounce/pagination budget rõ. |
| F-019 | Internal `storage_key` bị lộ trong resource JSON/export không cần thiết. |

## P3 — Polish/nợ sản phẩm

| ID | Finding |
|---|---|
| F-020 | “Meta Director”, revision và một số copy mang ngôn ngữ dev. |
| F-021 | UI trộn tiếng Việt/Anh, setting default theme mâu thuẫn backend/copy. |
| F-022 | Project export có nguy cơ đưa metadata nội bộ; cần privacy schema riêng. |
| F-023 | Không có empty-state hướng dẫn bằng một workflow mẫu có thể chạy. |
| F-024 | Hai UI `/prompt-ai-ommi` và `/classic` tạo hai nguồn sự thật sản phẩm. |
| F-025 | Shared fixture không import table đã gây overview 500; boot/migration contract cần chốt. |

## Root causes

1. Domain/backend phát triển nhanh hơn canonical customer journey.
2. Autosave, job và storage chưa có state machine xuyên suốt.
3. Capability được tính là “đã có” khi route tồn tại, dù khách hàng không thể dùng.
4. Test kiểm component/legacy và happy API, thiếu browser contract paid A–Z.
