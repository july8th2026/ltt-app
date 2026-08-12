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

1. Staging upload session owner-scoped, TTL, type/signature/actual size/quota/rate.
2. Promote sau hold; cleanup failure/abandon; sweeper dry-run/idempotent.
3. Retention/delete/reconcile có audit event và metric.
4. **PASS:** G2/G5 xanh cho Upscale/Clip/Image/Video.

## R3 — Provider/output matrices

Thực hiện tuần tự AutoSub → Prompt → Image → Clip, mỗi app một release slice:

- cấu hình provider secret ngoài repo;
- chạy canary output thật + probe/Quality Lab phù hợp;
- đối soát quote/hold/settle/refund và ownership/download;
- đóng app đó trước khi sang app kế tiếp.

## R4 — Upscale commercial quality

1. Materialize HR dataset có license/consent; tối thiểu 12 video đủ slice.
2. Blind A/B ≥3 rater/case, review agreement/correlation.
3. Version threshold quality/cost/P95; tách job type Fast/Quality.
4. Rerun qualified dual-GPU khi cả hai card idle.
5. **PASS:** G1/G7/G8 xanh; không dùng diagnostic Lanczos hiện tại làm gate.

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
