# H32.7 — Release plan tuần tự

## R0 — Không deploy batch ngay

- Giữ production 8100 nguyên trạng.
- Release candidate là chuỗi commit H32.1→H32.6; mỗi app có rollback theo commit.
- Không bundle các blocker P0/P1 thành một lần deploy khó truy nguyên.

## R1 — Seedance money correctness

1. Khóa canonical quote/hold/actual cap/exactly-once/refund/reconcile.
2. Chạy negative race, retry, duplicate submit, insufficient credit.
3. Canary provider nhỏ với tài khoản test và đối soát ledger.
4. **PASS:** không âm/charge vượt hold, G3 xanh; rollback app commit độc lập.

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
