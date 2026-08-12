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

### R3.1 — AutoSub

- [x] Local WhisperX engine + UI A–Z: upload speech thật, job worker trên GPU1,
  polling queued→done, project reload 9 cue và render NVENC 1080p H.264/AAC.
  Credit 1.000→996 đúng quote 4; output MP4/ASS/SRT/VTT/JSON/ZIP tải được.
- [x] Paid-render preflight: overlap/empty/out-of-source chặn trước quote; tốc
  độ đọc/cue ngắn/line budget cảnh báo trong confirmation. Lỗi API lồng trả
  JSON theo Q88 để frontend hiện đúng hướng xử lý.
- [ ] Corpus VI/EN có ground truth để đo WER/timing; pyannote DER và Gemini
  translation thật. Smoke không ground truth chỉ chứng minh engine chạy, không
  chứng minh độ chính xác thương mại.
- [ ] Đưa source upload của Studio vào draft attachment/UploadSession có
  owner/TTL/recovery. Không gắn file draft chưa có paid Job vào lifecycle Q85
  bằng một đường tắt thiếu hợp đồng.
- **TECHNICAL CONDITIONAL PASS:** bằng chứng chi tiết ở
  `06_R3_AUTOSUB_PROVIDER_EVIDENCE.md`; AutoSub R3 chưa được đóng toàn bộ.

### R3.2–R3.4 — Prompt, Image, Clip

- [ ] Prompt/Image: exact provider key test chưa có trong process hiện tại.
- [ ] Clip: canary Fast cũ đã có nhưng matrix provider/output/ledger trên exact
  release candidate vẫn phải chạy lại tuần tự.

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

- [x] Job Center live progress/backoff/terminal refresh — 2026-08-12, Q87:
  2s khỏe; offline 4→8→16→30s; online reset; terminal reload đúng một lần để
  hiện Retry/Artifact. Retry/cancel/lineage, cursor history đã có và regression.
- [ ] Draft recovery thống nhất cho form chưa có project bền vững; phải chốt
  privacy/user scoping trước khi lưu nội dung nhạy cảm ở browser.
- [ ] Canonical preflight/confirmation cho toàn bộ job giá cao/dài (Seedance,
  Upscale và AutoSub đã có; cần đóng matrix Clip/Image/Prompt).
- [ ] Browser A–Z đủ sáu app desktop/mobile, keyboard/focus/offline/error/refresh
  trên exact staging RC. Lát cắt Job Center source/browser đã PASS.

## R6 — Staging release

1. Backup + migration dry-run + release manifest/checksum.
2. `python tools\gate.py` PASS trên exact commit.
3. Deploy staging; public-like smoke từng app, console/network/SLO/credit ledger.
4. Rollback drill; chỉ sau đó mới đề xuất production deploy riêng.

## Thứ tự vé khuyến nghị

`Seedance P0 money → shared upload/lifecycle P1 → provider matrices → Upscale
calibration/scheduler → UX recovery → staging → production decision`.

H32.7 chỉ lập release plan và nghiệm thu source; không tự cấp quyền deploy.
