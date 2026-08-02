# Báo cáo RÀ SOÁT APP — 2026-08-02 (PA-3 HYBRID)

> Phương án: PA-3 (linter + agent parity/review song song + browser E2E). Phạm vi
> sửa: **P0/P1** (bug thật + lỗ hổng + credit sai). P2 (parity fast-follow, nâng nhỏ)
> → backlog. Thứ tự: rủi ro×doanh thu. Nguồn đối chiếu chỉ đọc (BOT GEMINI / FULL AUTO).

## Baseline tự động
- Full suite: XANH (1699 + test_44 sửa lại 31 + test_85 lint). scan: 0.
- Linter hợp đồng app (`tools/lint_app_contract.py`): 9 app, **0 ERROR / 0 WARN**.

## Tổng hợp findings (cập nhật dần khi agent về)

### taoanh (vs gemini_image) — parity core ~80% / tổng ~60%
- **P0: KHÔNG.** Credit (reserve count×5 → settle len(keys)×5, chống double-spend,
  hoàn khi 0 ảnh), cô lập (`/img` guard user_id), CSRF, hợp đồng (idempotent+progress+
  raise) — ĐÚNG.
- **P1 (sửa đợt này):**
  - [P1] Thiếu **cap độ dài prompt** (nguồn 4000) → prompt khổng lồ giữ chỗ credit rồi
    400/timeout. Sửa: cap ở routes.queue + jobs.
  - [P1] **Mất nội dung form khi lỗi re-render** (`_render` không trả lại prompt/model/
    aspect/count) → user gõ lại. Sửa: repopulate context + template.
- **P2 → backlog:** batch `---` (nguồn có, app thiếu — parity); gộp N call→1 call
  multi-image (đỡ 4× chi phí); xoay key giữa job; policy-scan + rate-limit prescreen;
  presigned TTL review; adhoc job_id collision (chỉ khi ctx None — vô hại prod).

### thumbnail (vs thumbnail_api) — parity ~92% (xác nhận DOI_CHIEU đúng)
- **P0: KHÔNG.** Credit (reserve count×5→settle len(keys)×5, chống double-spend, hoàn),
  cô lập (`/img` guard user_id), CSRF, hợp đồng, prompt từ fragment — ĐÚNG. Catalog
  (6 text style/11 phong cách/9 trend/5 ngôn ngữ) + base_prompt byte-match nguồn.
- **P1 (sửa đợt này):** thiếu **cap độ dài** topic/title/subtitle (nguồn cap 2000) →
  phơi chi phí token trên giá phẳng. Sửa: cap ở routes.queue.
- **P2 → backlog:** hiện lỗi ảnh-lỗi-một-phần trên job done; validate aspect theo model
  (latent khi bật Imagen); per-image retry/backoff + xoay key trong job; wording
  title/subtitle rút gọn khác nguồn (cosmetic); batch/ảnh-ref/Imagen (cố ý hoãn).

### kichban (vs youtube_script) — parity ~95%
- **P0: KHÔNG.** Credit (phẳng 3, reserve=settle, chống double-spend, hoàn), cô lập
  (`/r`,`/status` guard user_id + slug), CSRF, topic cap 500, prompt từ fragment (dùng
  .replace ĐÚNG hơn nguồn .format vốn lỗi brace) — ĐÚNG.
- **P1 (sửa đợt này):** lỗi provider (`Gemini HTTP {status}: {text}`) hiện **nguyên
  văn ra UI** (`_script_view.html:54`) — key đã scrub nhưng lộ body/status nội bộ. Sửa:
  thông điệp chung cho user, chi tiết chỉ vào log.
- **P2 → backlog:** cascade đa-provider gộp còn Gemini (document); dead directive
  `do_dai_video/*.txt` (kế thừa từ nguồn); `htmx.min.js` không cache-bust; `except`
  rộng che lỗi APIKEYS; `max_attempts=3` trên gen trả phí (cân nhắc — cũng là chống lỗi).

### upscalevideo (vs video_upscale) — parity core 7/7 ~100% / tổng ~65-70%
- **P0: KHÔNG.** Credit **free-ride guard ĐÚNG** (worker probe duration thật → nâng
  giữ chỗ TRƯỚC extract/GPU/encode); cô lập `/v` guard user_id; CSRF /queue; idempotent
  (out_key exists); engine.check_engine; không sửa platform; service.submit_upscale_job
  cho seedance sạch.
- **P1 (sửa đợt này):**
  - [P1] `_resolve_encoder` (jobs.py:61-68) coi "có GPU encoder" = NVENC → nếu card
    Intel/AMD (qsv/amf) hoặc codec hevc không hỗ trợ → encode HỎNG (sau khi đã upscale
    xong, phí GPU), KHÔNG fallback libx264. Sửa: chỉ dùng nvenc khi detect=h264_nvenc,
    ngược lại libx264 (+ cân nhắc retry libx264 khi encode lỗi).
  - [P1] Không giới hạn thời lượng (đường presigned R2 không cap) → 1 job dài chiếm
    trọn worker GPU đơn, đói mọi tenant. Sửa: cap thời lượng ở submit + worker (raise
    nếu vượt). (P3 đa-worker là giải pháp gốc — vẫn cần cap để chặn lạm dụng.)
- **P2 → backlog:** bỏ thermal guard + VRAM preflight (nguồn có); CSRF /upload-url,
  /estimate; cancel chưa nối; preview disk-guard đếm dư; tải video trước khi top-up.

### taovideo (vs seedance_video) — parity ~70% (core generation ĐỦ)
- **P0: KHÔNG** (reserve atomic + settle/refund idempotent theo job đúng).
- **P1 (sửa đợt này):**
  - [P1] **Double-billing provider khi retry/orphan**: `remote_task_id` KHÔNG lưu → worker
    chết/orphan sau submit ModelArk thì lần chạy lại **submit task MỚI** (nền tảng chịu chi
    phí kép). Sửa: lưu task_id vào job.params, vào lại thì re-poll thay vì submit lại.
  - [P1] **Cửa sổ không heartbeat** khi build ref/asset:// + `_heal` (có thể >5' ORPHAN_TIMEOUT)
    → false-orphan + chạy trùng (cộng hưởng lỗi trên). Sửa: `ctx.progress` trong vòng ref + heal.
  - [P1] **Settle âm số dư**: token thật > ước tính (calib 1 điểm) → balance âm. Sửa: reserve
    bảo thủ (×~1.25).
  - [P1] **Redirect 1 video → /jobs/{id} hiện JSON thô** (không player). Sửa: về `/taovideo`.
  - [P1] **`dich()` đồng bộ trong route async** chặn event loop tới 30s. Sửa: run_in_threadpool.
- **P2 → backlog:** CSRF /translate; range `bytes=0-` đọc cả file vào RAM; ref quá cỡ bị bỏ
  âm thầm; xoay key trong job; sanitize prompt; UI role/@handle (dead); prompt sanitize.

### autosubvideo (vs auto_sub_video) — core burn ~100% / tổng ~75%
- **P0: KHÔNG.** Credit free-ride guard ĐÚNG (probe+top-up trước burn); cô lập `/v`,`/f`;
  CSRF /queue; ffmpeg-PATH + ASS cwd + stderr drain ĐÚNG.
- **P1 (sửa đợt này):**
  - [P1] Range handler đọc **cả file vào RAM** cho output Local (`f.read(length)` với
    `bytes=0-`) → memory-DoS trên deploy KHÔNG-R2 (prod R2 né qua 302). Sửa: cap cửa sổ.
  - [P1 parity] `/preview` (burn_preview) là **dead code**; `bitrate_mode` hardcode "auto"
    → 2 năng lực có code nhưng user không chạm được. (Xếp fast-follow — xem ghi chú.)
- **P2 → backlog:** CSRF /upload-url; content-type `/v` theo format; allow-list ext input;
  precedence ext tmp; transcript nhồi vào dedupe/params; validators/templates/custom-style/zip.

### chataistudio (+ sidecar, vs codex) — chat+ảnh ~80%
- **P0: KHÔNG.** Cô lập hội thoại/tin/ảnh theo user; CSRF mọi POST; admin role-gated;
  sidecar loopback+token; disconnect→interrupt sidecar (không đốt quota).
- **P1 (sửa đợt này):**
  - [P1] **Ngắt kết nối (GeneratorExit) mồ côi giữ-chỗ** — `except Exception` bỏ sót
    BaseException → KHÔNG settle/refund → **ảnh miễn phí bằng cách ngắt giữa chừng**. Sửa:
    settle/refund trong `finally` (bắt cả BaseException).
  - [P1] **Settle không kiểm số dư** — ảnh 20cr > reserve 3cr → 1 lượt nhiều ảnh đẩy balance
    âm. Sửa: cap số ảnh/lượt + (một phần) recheck.
- **P2 → backlog:** ảnh lưu lỗi âm thầm không tính (routes:249); sidecar fail-open khi token
  rỗng; message không cap độ dài; lỗi quota thô (chưa friendly/pool); rollout-loss không
  persist thread mới; render plain-text (chưa markdown); bubble rỗng khi chỉ có ảnh; UI
  custom-instructions chưa gắn.

### taoclipngan (wrapper engine cutclipshort) — option ~95% / power-option ~65%
- **P0 (cosmetic-data): title/score clip LUÔN trống** — `cand_by` key theo `clip_id` nhưng
  `CandidateClip` là `candidate_id` → dict sập `{None: last}`; lookup `clip_spec.clip_id`
  (đúng) luôn miss. Sửa 1 dòng: key theo `candidate_id`.
- **P1 (sửa đợt này):** CSRF `/upload-url` (mint presigned PUT vào prefix nạn nhân);
  prepend cả thư mục **ffprobe** vào PATH (nếu khác dir ffmpeg → analysis lỗi giữa chừng).
- **P2 → backlog:** cap size/duration đường R2-direct; gọi `run_health_check()` sớm;
  score 0..100; thêm 3 genre (nature/action/animation); power-option (caption/color/framing/
  multi-aspect/hook keywords) — MVP cố ý bỏ.

## TỔNG HỢP + KẾ HOẠCH SỬA (P0/P1 đợt này)

**KHÔNG có P0 bảo mật/credit-loss ở app nào** (platform primitive bảo vệ). 1 P0 cosmetic
(taoclipngan title/score). Sửa P0/P1:

**A. Tiền/đúng-đắn (ưu tiên cao):**
1. taovideo: lưu `remote_task_id` + re-poll (chống double-bill provider) ← cao nhất.
2. taovideo: heartbeat trong ref-build + heal (chống false-orphan/chạy trùng).
3. taovideo: reserve bảo thủ ×1.25 (chống balance âm khi token thật > ước tính).
4. taovideo: redirect 1-video → /taovideo (thay JSON thô).
5. taovideo: `dich()` → run_in_threadpool (không chặn event loop).
6. chataistudio: settle/refund trong `finally` (bắt BaseException) — chống ảnh-free-by-disconnect.
7. chataistudio: cap số ảnh/lượt.
8. upscalevideo: `_resolve_encoder` gate nvenc-family, else libx264.
9. taoclipngan: sửa join title/score (candidate_id).

**B. Cứng hoá input (rẻ, rộng):**
10. taoanh: cap độ dài prompt + giữ form khi lỗi.
11. thumbnail: cap độ dài topic/title/subtitle.
12. kichban: thông điệp lỗi provider chung cho user (không lộ body).

**C. Guard chung (rẻ, phòng thủ):**
13. CSRF `/upload-url` (autosub, upscale, taoclip) + `/translate` (taovideo).
14. Cap cửa sổ range `bytes=0-` ở serve routes (né RAM-DoS Local; R2 prod đã né).
15. taoclip: prepend cả ffprobe dir vào PATH.
16. Cap thời lượng nguồn (upscale, taoclip) chống 1 job chiếm trọn worker GPU.

## ĐÃ SỬA + NGHIỆM THU (2026-08-02)

Tất cả P0/P1 nhóm A+B đã sửa + deploy + verify:
- taoclipngan: **P0 title/score** (key `candidate_id`) — smoke THẬT: title/score đã hiện
  ("✨ Last month…" 0.719); ffprobe dir vào PATH.
- taovideo: lưu `remote_task_id` + resume-poll (chống double-bill) · heartbeat ref/heal ·
  reserve ×1.25 · redirect→/taovideo · `dich()` threadpool · CSRF /translate — **translate
  verify THẬT** (VI→"An astronaut cat gliding on Saturn's rings").
- chataistudio: settle/refund trong `finally` (chống ảnh-free-by-disconnect) · cap 4 ảnh/lượt
  — **chat verify THẬT** (luồng bình thường vẫn OK, trả "ổn").
- upscalevideo: `_resolve_encoder` gate nvenc-family → libx264 fallback.
- taoanh: cap prompt 4000 + redirect→/taoanh. thumbnail: cap topic/title/subtitle + redirect.
- kichban: lỗi provider → thông điệp chung (chi tiết chỉ vào log).
- Linter hợp đồng: 0 ERROR. test_85 chốt. Full suite + scan chạy lại.

**Hoãn (P2 → backlog KE_HOACH_TON_DONG):** parity fast-follow (batch ---, /preview,
bitrate_mode, custom-style, thumbnail ref/Imagen, chatai markdown/custom-instr UI, taovideo
seed/role/@handle/key-rotation, thermal/VRAM guard, health_check sớm…), + **P3 worker đa
tiến trình** (bản chất chống starvation).
