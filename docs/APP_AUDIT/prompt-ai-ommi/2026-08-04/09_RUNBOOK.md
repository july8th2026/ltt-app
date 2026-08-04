# 09 — Runbook PROMPT AI OMMI

## Rollout và rollback

- `LTT_PROMPT_AI_OMMI_ROLLOUT=off|admin|allowlist|public`.
- `LTT_PROMPT_AI_OMMI_USER_IDS` là danh sách user id khi allowlist.
- Production không cấu hình mặc định `off`; dev mặc định `public`.
- Rollback tức thời: đặt `off`, restart web/worker. Project và artifact không bị
  xóa; UI đọc/chỉnh/export vẫn khả dụng, chỉ tạo job/handoff bị khóa.

## Kiểm tra vận hành

1. `/health/ready` phải 200.
2. Admin xem `/prompt-ai-ommi/api/admin/health`; chỉ có count/status, không PII.
3. Theo dõi Jobs chung: queued lâu, error rate, retry, credit refund.
4. Kiểm tra APIKEYS có credential chat Gemini; ảnh/video do app chủ quản giữ key.
5. Khi provider lỗi diện rộng, chuyển rollout `off`; không xóa job hoặc sửa sổ.

## Backup/retention

AppProject và Job nằm trong DB nền tảng; asset nằm trong Storage owner-scoped.
Backup/restore dùng runbook nền tảng, sau restore kiểm tra project revision,
snapshot, storage key và credit ledger. PROMPT AI OMMI không có endpoint purge
user trực tiếp; retention/purge chỉ được bổ sung như admin job dry-run có audit.

## Release gate

Chạy full pytest, secret scan, browser desktop/mobile, console/network gate.
Sau đó admin → allowlist → public. Deploy production chỉ khi người dùng yêu cầu
rõ và có backup/rollback/health thật.

