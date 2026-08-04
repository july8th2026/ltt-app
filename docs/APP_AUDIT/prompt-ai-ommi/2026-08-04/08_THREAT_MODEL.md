# 08 — Threat model và security acceptance

| Biên/abuse case | Chốt hiện hành | Bằng chứng |
|---|---|---|
| Đọc/sửa project user khác | mọi lookup gồm `user_id` + `app_slug`; trả 404 | two-user API test |
| Stale tab ghi đè | optimistic `revision`; stale trả 409 | revision test |
| CSRF create/save/job/upload | session CSRF bắt buộc trên mutation | route/API test |
| Path traversal upload | chỉ lấy `PurePath.name`; Storage key do server sinh dưới user id | upload implementation |
| File giả/quá lớn | allow MIME family, byte cap, PIL verify ảnh | route validation |
| Import gài secret/path | schema/cap 900 KiB; forbidden fields do AppProject chặn; storage key bị xóa | round-trip test |
| Cross-app private import | cấm; chỉ ToolSpec public | source inspection + manifest contract |
| Model/param sai | model registry + capability normalization + ToolSpec validation | handoff test |
| Double submit/charge | deterministic dedupe + atomic Job/Credit transaction | platform contract |
| Provider lỗi | worker retry; credit refund/settle chung; không trả raw credential | worker/provider contract |
| Prompt/PII trong health | health chỉ count/status, không trả prompt/media/user | admin endpoint |
| Shared catalog bị user sửa | publish yêu cầu DB role admin; user chỉ đọc | route contract |
| Production mở nhầm | mặc định rollout `off`; modes off/admin/allowlist/public | rollout test |
| BOT GEMINI bị ghi | nguồn chỉ đọc, không import chéo | git diff + thao tác phiên |

Rủi ro còn lại trước public: chưa có canary provider thật; retention/purge async
chưa được mở cho app; PDF native và collaborative edit không thuộc release v1.

