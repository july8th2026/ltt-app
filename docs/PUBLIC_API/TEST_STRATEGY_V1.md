# Public API V1 — Chiến lược test và baseline

## 1. Baseline đo ngày 2026-08-13 (trước mọi thay đổi)

Lệnh đã chạy thật, kết quả thật:

| Phép đo | Lệnh | Kết quả |
|---|---|---|
| Quick gate | `python tools/gate.py --quick` | **PASS 9/9** (secret scan, app contract lint, tên chưa định nghĩa, nuốt lỗi lặng lẽ, chuỗi chưa dịch, system profile, 3 frontend) |
| Targeted core | `python -m pytest -q tests/test_60_app_registry.py tests/test_67_hang_doi_job.py tests/test_68_credit.py tests/test_69_web_jobs.py tests/test_75_api_keys.py tests/test_151_job_events.py tests/test_173_upload_sessions.py tests/test_174_app_upload_lifecycle.py tests/test_176_api_error_contract.py tests/test_80_r2_storage.py` | **139 passed**, 134,5 s |
| Tổng test thu thập | `python -m pytest -q --collect-only --ignore=tmp --ignore=test-results` | **2.696 test** |
| Migration head | `python -m alembic heads` | `b6c7d8e9f0a1` (`20260812_1500_project_upload_attachments`) |
| Registry | `discover()` | 14 app, **0 lỗi**, 17 job_type, 21 ToolSpec |

Latency control-plane (in-process `TestClient`, không qua mạng/Cloudflare/
PostgreSQL — chỉ đo routing + middleware + template; 60 mẫu, 5 lượt warmup):

| Route | Status | p50 | p95 | max |
|---|---|---|---|---|
| `/health/ready` | 200 | 2,47 ms | 2,79 ms | 3,06 ms |
| `/login` | 200 | 3,17 ms | 3,83 ms | 4,36 ms |
| `/` (catalog) | 200 | 6,33 ms | 6,75 ms | 27,11 ms |
| `/health` | 404 | 2,87 ms | 3,24 ms | 46,27 ms |

Ghi chú trung thực về phép đo này:

- Repo **không có** benchmark harness control-plane sẵn (`tools/*benchmark*` là
  của autosub/upscale, đo GPU/ASR). Số trên do script tạm sinh, không commit
  vào repo ở Prompt 01; Prompt 08 quyết có biến nó thành công cụ chuẩn không.
- `/health` trả 404 là **đúng thiết kế**: router health chỉ có `/health/live`,
  `/health/ready`, `/health/version` (`server/routes/health.py`).
- Máy dev này **không** cấu hình `LTT_DATABASE_URL`, nên số trên không bao gồm
  chi phí truy vấn PostgreSQL và không đo được DB pool. Đây là baseline
  *middleware*, không phải baseline production.

## 2. Ràng buộc môi trường test (phải biết trước khi viết test)

- Mặc định test chạy **không có PostgreSQL**. Các bất biến dựa
  `pg_advisory_xact_lock` (`credit.giu_cho`, `credit._khoa_ket_so_job`,
  `taovideo.quotes._lock_intent`) **bị bỏ qua trên SQLite**. Test đồng thời phải
  chạy với `LTT_TEST_DATABASE_URL` (mẫu sẵn có: `tests/test_73_dong_thoi_pg.py`).
- Vì vậy: **mọi test double-charge/double-submit/race của Public API bắt buộc
  có phiên bản PostgreSQL**. Test SQLite xanh không chứng minh gì về race.
- `tools/gate.py` là cổng duy nhất được coi là "regression xanh"; `pytest` một
  mình bỏ qua 3 bộ test frontend và 6 scanner.

## 3. Bốn tầng test cho mỗi prompt

**T1 — targeted (bắt buộc mọi prompt).** Test đúng thứ vừa viết: unit domain +
route contract. Nhanh, chạy được không cần PostgreSQL.

**T2 — security/tenant (bắt buộc khi prompt chạm resource có chủ).** Tối thiểu
cho mỗi endpoint có object:

- BOLA: key của user A đọc/hủy/tải job, upload, artifact, webhook, usage của
  user B → **404/403, không rò tồn tại**.
- Auth: key sai/thu hồi/hết hạn; enumeration (thời gian phản hồi không phân
  biệt "key không tồn tại" và "key sai"); không có header → 401.
- Scope: thiếu scope → 403 **trước** khi chạm credit.
- Mass-assignment: field lạ trong body không được ghi vào job params/DB.
- Charge bypass: không đường nào tạo job mà bỏ qua `submit_with_credit`.
- SSRF: mọi field nhận URL (hiện có `video.social_import`, tương lai webhook
  target) phải có allowlist/deny private range + test.
- Redaction: assert Authorization header, key thô, presigned URL, local path
  **không** xuất hiện trong `job_events`, log JSONL, response lỗi.

**T3 — nhịp test/gate: `docs/00_LTT_OPERATING_CONTRACT.md` §4.** *(Trước
2026-09-16 mục này đòi `gate.py --quick` ở cuối mỗi prompt — một nhịp riêng đã bỏ.)*

**T4 — lượt L3 (một lần, theo hợp đồng §4.2)** đi kèm bộ PostgreSQL chạy với
`LTT_TEST_DATABASE_URL`. *(Bản cũ đặt L3 sau prompt 6, 10, 14, 16, 17 — đã bỏ.)*

## 4. Bất biến phải có test riêng, không được coi là hiển nhiên

| Bất biến | Cách test |
|---|---|
| Scope/validate fail **trước** hold | Gọi với scope thiếu → assert số dòng `credit_entries` không đổi |
| Hold thành công **trước** khi vào hàng đợi | Ép `ThieuCreditError` → assert không có dòng `jobs` |
| Idempotency: cùng key + cùng payload | Gọi 2 lần → **một** job, **một** hold, cùng response |
| Idempotency: cùng key + payload khác | → 409, không tạo job thứ hai |
| Retry sau khi job terminal | Cùng Idempotency-Key → trả job cũ, **không** hold lần hai (đây là chỗ `dedupe_key` hiện tại KHÔNG che) |
| Thu ≤ hold (Q84) | Handler báo `credit_cost` > hold → `charged == held`, có event variance |
| Refund đúng một lần | Gọi `hoan()` hai lần → một dòng `refund` |
| Fail-closed catalog | Tool không allowlist → 404 ở `/api/v1/tools/{name}` và không submit được |
| Không lộ tên provider/model nội bộ | Snapshot response catalog, assert không chứa tên provider/`base_url`/đường dẫn storage |
| Pagination có trần cứng | `limit` vượt trần → clamp, không trả toàn bảng |
| Cookie không phải danh tính API | Gửi cookie phiên hợp lệ, không có Bearer → 401 |

## 5. Quy tắc chống test giả

- Không sửa test cũ để "PASS" nếu hành vi đúng đã đổi — phải ghi rõ trong
  PROGRESS vì sao ngữ nghĩa đổi.
- Không đếm số test thu thập được rồi tuyên bố xanh. Chỉ ghi kết quả chạy thật,
  kèm lệnh.
- Thay đổi giao diện/luồng người dùng (portal ở Prompt 15) phải kiểm bằng
  trình duyệt trên URL công khai, không chỉ loopback (CLAUDE.md 5b).

## 6. Rollback

Mọi prompt phải ghi đường lùi trước khi làm:

- Code: thay đổi additive, mount router sau một cờ môi trường
  (`LTT_PUBLIC_API=0` → không mount, hệ thống trở về đúng trạng thái hôm nay).
- Migration: mỗi migration mới phải có `downgrade()` chạy được và được thử
  `upgrade → downgrade → upgrade` (mẫu: `tools/restore_drill_schema.py`).
- Dữ liệu: bảng mới của Public API không được sửa/di trú bảng cũ; xóa bảng mới
  không làm mất dữ liệu app nào.
