# H32.5 — Findings: Tạo Video Seedance

## Đã sửa trong vòng này

| ID | Severity | Hiện tượng/root cause | Kết quả |
|---|---|---|---|
| UI-01 | P1 | Quote/Create dưới fold; panel dùng một vùng scroll dài | Tách scroll + dock, PASS desktop/mobile |
| UI-02 | P1 | Composer mobile offscreen vẫn focus; không có close rõ | inert/aria-hidden/close/restore focus, PASS |
| UI-03 | P2 | EN lẫn status VI và title VI | status/title qua gettext, PASS |
| UI-04 | P2 | Saved assets luôn mở làm loãng luồng tạo | details + count + nav open, PASS |
| UI-05 | P2 | Toolbar/header chiếm cao hơn ảnh chuẩn | compact, accessible labels giữ nguyên |
| UI-06 | P1 | Estimate lỗi vẫn trông như CTA sẵn sàng | fail state + disable CTA, negative 500 PASS |
| UI-07 | P2 | Raw worker progress lộ lên card | generic localized status + % |

## Còn mở — không được che bởi visual pass

| ID | Severity | Bằng chứng | Root cause / acceptance |
|---|---|---|---|
| ~~CORE-01~~ | ~~P0~~ | **SOURCE FIXED 2026-08-12** | Q84 cap customer charge; provider variance warning/reconcile. Post-fix paid canary còn ở R1.3 |
| CORE-02 | P1 | Source/audit cũ | ref lưu trước hold, thiếu staging TTL/sweeper |
| ~~CORE-03~~ | ~~P1~~ | **FIXED 2026-08-12** | signed quote intent reuse mọi status; double submit chỉ một job/hold |
| CORE-04 | P1 | Source/audit cũ | audio ref AssetType/MIME sai; fix/canary hoặc ẩn |
| UX-08 | P2 | E3 Remix: refs=0, count=2 | giữ refs/role/count hoặc disclosure rõ |
| UX-09 | P2 | Control registry | thiếu live refresh/cancel/retry/delete/pagination |
| UX-10 | P2 | Reference UI | thiếu remove/replace/reorder từng item |
| UX-11 | P2 | Error card | lỗi lưu tự do có thể không dịch được; cần error code |
| OPS-12 | P1 | Audit cũ | remote asset reconcile/quota/cleanup chưa có |

Không thêm CTA giả để che UX-09/10. App-level release vẫn BLOCKED dù H32.5 visual
gate đã pass.

Phát hiện bổ sung R1: ba file input dùng cùng tên và HTMX encode thành
`[object File]`, làm quote video trả 422. Đã tách `ref_images/ref_videos/ref_audios`,
quote chỉ gửi cờ loại input và queue đối chiếu lại file thật; MP4 6,59 MB pass.
