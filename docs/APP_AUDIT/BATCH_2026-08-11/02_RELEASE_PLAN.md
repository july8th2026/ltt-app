# H32.7 — Release plan tuần tự

## R0 — Không deploy batch ngay

- Giữ production 8100 nguyên trạng.
- Release candidate là chuỗi commit H32.1→H32.6; mỗi app có rollback theo commit.
- Không bundle các blocker P0/P1 thành một lần deploy khó truy nguyên.

## R1 — Seedance money correctness

1. [x] Khóa canonical quote/hold/actual cap/exactly-once/refund/reconcile ở
   source — 2026-08-12, Q84.
2. [x] Chạy negative settle/refund, provider overage, duplicate quote kể cả job
   terminal, insufficient credit kế thừa — 48 targeted pass.
3. [ ] Canary provider nhỏ trên exact release candidate với tài khoản test và
   đối soát ledger. Fixture cô lập không có provider key; không dùng production
   8100 hoặc giả provider thành bằng chứng trả phí.
4. **SOURCE PASS / RELEASE CONDITIONAL:** browser thật MP4 6,59 MB quote 47→29,
   submit lặp chỉ một job/hold, balance 500→424 đúng 47+29, console sạch;
   G3 chỉ xanh sau canary mục 3.

## R2 — Upload và artifact lifecycle dùng chung

1. [x] Staging upload session owner-scoped, TTL, type/signature/actual
   size/quota/rate — 2026-08-12, Q85.
2. [x] Promote sau hold; compensation DB rollback; cleanup failure/abandon;
   sweeper dry-run/idempotent và bỏ qua Job active.
3. [x] Retention/delete/reconcile có audit event, log worker và CLI operator
   không lộ storage key/filename.
4. [x] **SOURCE PASS:** G2/G5 xanh cho Upscale/Clip/Image/Video; 12 core/route
   lifecycle test pass; Playwright Upscale MP4 thật 6,59 MB tạo Job, credit
   1000→992, source route 206, console 0, mobile không overflow.
5. [ ] **RELEASE CONDITIONAL:** Alembic/CORS/object storage phải được dry-run và
   smoke trên exact staging RC ở R6. Browser direct upload vẫn default-off theo
   Q48 cho tới khi bucket CORS pass; production 8100 chưa deploy.

## R3 — Provider/output matrices

Thực hiện tuần tự AutoSub → Prompt → Image → Clip, mỗi app một release slice:

- cấu hình provider secret ngoài repo;
- chạy canary output thật + probe/Quality Lab phù hợp;
- đối soát quote/hold/settle/refund và ownership/download;
- đóng app đó trước khi sang app kế tiếp.

## R4 — Upscale commercial quality

1. Materialize HR dataset có license/consent; tối thiểu 12 video đủ slice.
2. Blind A/B ≥3 rater/case, review agreement/correlation.
3. [x] Tách job type Fast/Quality ở source — 2026-08-12, Q86: submit mới từ
   UI/Seedance dùng lane theo preset; Fast 2 GB, Quality 12 GB; legacy 12 GB
   vẫn resolve cùng handler cho job cũ và ToolSpec tĩnh.
4. [ ] Version threshold quality/cost/P95 sau khi có dataset và human rating.
5. [ ] Rerun qualified dual-GPU khi cả hai card idle. Telemetry 2026-08-12:
   GPU1 idle nhưng GPU0 baseline 1.126 MB vượt guard 512 MB; không dừng workload
   ngoài phạm vi để ép evidence.
6. **SOURCE SCHEDULER PASS / COMMERCIAL BLOCKED:** scheduler regression xanh;
   G1/G7/G8 vẫn chờ dữ liệu có license, ≥3 rater/case và dual-GPU qualified.
   Không dùng diagnostic Lanczos hiện tại làm gate.

## R5 — UX/recovery parity

- Live progress với backoff, retry/cancel/resume, cursor history và draft recovery.
- Canonical preflight/confirmation cho job giá cao/dài.
- Browser A–Z desktop/mobile, keyboard/focus/offline/error/refresh.

## R6 — Staging release

1. Backup + migration dry-run + release manifest/checksum.
2. `python tools\gate.py` PASS trên exact commit.
3. Deploy staging; public-like smoke từng app, console/network/SLO/credit ledger.
4. Rollback drill; chỉ sau đó mới đề xuất production deploy riêng.

## Thứ tự vé khuyến nghị

`Seedance P0 money → shared upload/lifecycle P1 → provider matrices → Upscale
calibration/scheduler → UX recovery → staging → production decision`.

H32.7 chỉ lập release plan và nghiệm thu source; không tự cấp quyền deploy.
