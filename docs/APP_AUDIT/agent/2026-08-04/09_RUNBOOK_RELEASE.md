# 09 — Agent Canvas release/operations runbook

## Ranh giới phát hành

- UI/editor có thể public nhưng tạo run chịu `LTT_AGENT_CANVAS_RUN_ROLLOUT`:
  `off → admin → allowlist → public`. Giá trị sai tự fail-closed về `off`.
- Kill switch toàn Agent: đặt rollout `off`, restart web; run mới trả 503, editor
  và dữ liệu workflow vẫn đọc/sửa được. Run đang chạy được admin cancel.
- Kill switch provider: disable các API key của provider/category trong admin.
  Tool mất provider phải disabled/giải thích thật; không fallback sang key ngoài pool.
- Kill switch tool/app: disable quyền app/capability; ToolSpec biến khỏi catalog
  người không có quyền. Không xoá snapshot hay artifact để rollback UI.

## Canary tuần tự

1. Backup DB + data; build release; migration additive.
2. `off`: health, catalog, login, Canvas read/save/restore/share ACL.
3. `admin`: một run text và một media fixture; quote=hold=settlement mong đợi.
4. `allowlist`: một user thường; node scope + full scope; cancel/refund.
5. `public`: chỉ mở khi browser console/network sạch và metrics trong ngưỡng.

## SLO và cảnh báo

| Tín hiệu | Đích | Cảnh báo/ứng xử |
|---|---:|---|
| Run success loại trừ provider policy | ≥98% | <95%/15 phút: về allowlist; điều tra theo app/provider |
| Quote/actual mismatch | <0,1% | bất kỳ over-hold: rollout off ngay |
| Save API P95 | ≤800 ms | >1,5 s/15 phút: giữ editor, khóa run mới |
| Worker wait | theo capability | max tăng liên tục: giảm canary/cancel backlog |
| Unexpected browser console/network | 0 | không promote phase |
| Secret scan | 0 | không build/deploy |

Endpoint admin `/agent/api/admin/metrics` chỉ trả số liệu vận hành tổng hợp; run
audit dùng user hash, không trả goal/params/PII. Log provider không được chứa key.

## Rollback

1. Đặt rollout `off` và restart web.
2. Cancel run bị ảnh hưởng qua admin, để ledger settle/refund theo đường chuẩn.
3. Khôi phục release trước; migrations H16 là additive nên code cũ bỏ qua bảng/cột mới.
4. Chỉ downgrade migration sau backup và khi code cũ đã chạy ổn.
5. Health loopback → Cloudflare → login → Canvas read-only; ghi kết quả thật vào nhật ký.

## Drill đã chốt

- 10 user chạy đồng thời không trùng child job.
- Cache chỉ same-owner + exact params và kiểm artifact còn tồn tại.
- Social import chặn private/reserved DNS, redirect mù và file không phải video.
- Canvas/Plan chặn trên 512 KiB/100 bước trước provider/credit.
- Share token chỉ lưu hash, có expiry/revoke và clone permission riêng.
