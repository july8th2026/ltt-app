# 04 — IMPLEMENTATION ROADMAP (chờ duyệt — chưa triển khai)

> Mỗi phase: **tệp cụ thể · đổi gì · lệnh kiểm · acceptance**.
> Nhịp làm (CLAUDE.md luật 1): test nhắm mỗi pha (`thanh_phan.py --test <tp>` →
> `python -m pytest <tệp> -q`) · gộp `main` khi test nhắm xanh · **gate
> `gate.py --doi` CHỈ MỘT LẦN cuối plan** · deploy chỉ sau gate xanh trên SHA.
> Nghiệm thu chất lượng: 4 video thật ở `C:\Users\Thang Tuong\Desktop\TEST VIDEO`
> (cooking 79 MB · camp 25 MB · gaming 21 MB · airsoft 88 MB) — không commit vào repo.

---

## PHA 0 — Nền tảng tin cậy (không LLM)

**Mục tiêu:** pipeline hiện tại chạy đúng, chặn clip kém, cache đúng ngữ cảnh.
Làm trước vì mọi phase sau dựa trên nó và vì `evaluation/gate.py` đang chết
(chưa ai gọi).

### 0.1 Nối quality gate vào jobs.py
- **Tệp:** `apps/taoclipngan/jobs.py` (thêm bước giữa editorial → render),
  `cutclipshort/evaluation/gate.py` (đọc, sửa nếu thiếu).
- **Đổi:**
  - Sau `run_editorial`, trước render: gọi `build_evaluators_for_tier`
    (`evaluation/__init__.py`) + gate v3. Clip bị hard reject (hook<0.20,
    intent<0.25, completion<0.20, <5s) → loại khỏi danh sách render.
  - Chế độ: `lifecycle="development"` → **cảnh báo** (ghi vào manifest
    `qa: {rejected: [...], mode: "warn"}`), sau khi đổi `released` → **chặn**.
  - Nếu toàn bộ clip bị reject → fallback top-1 theo ranker (không trả rỗng),
    ghi flag `qa: {fallback: true}`.
- **Test:** `tests/test_tcn_gate.py` (mới) — clip giả hook<0.20 bị loại;
  toàn reject → fallback top-1; mode warn không chặn.
- **Acceptance:** chạy video gaming 21 MB → manifest có `qa` block; clip bị
  reject không xuất hiện trong package.

### 0.2 Cache key đúng ngữ cảnh
- **Tệp:** `cutclipshort/storage/cache.py` (`is_valid`/`mark_done`),
  `cutclipshort/core/pipeline.py` (truyền ngữ cảnh vào key).
- **Đổi:** `config_hash` phải bao hàm `genre + tier + aspect_ratio`;
  thêm `schema_version` vào manifest cache (key cũ → invalid, chạy lại một lần).
- **Test:** cùng source, hai aspect khác nhau → cache miss (bắt buộc chạy lại);
  cùng ngữ cảnh → hit.
- **Acceptance:** log 2 lần chạy 9:16 rồi 1:1 với cùng file — lần 2 chạy engine
  lại, lần 3 (cùng 1:1) dùng cache.

### 0.3 Cancel giết sạch process tree
- **Tệp:** `apps/taoclipngan/jobs.py`, các điểm gọi FFmpeg trong `cutclipshort/`
  (tìm bằng grep `subprocess|ffmpeg`).
- **Đổi:** kill theo **process tree** (CREATE_NO_WINDOW + job object hoặc
  `taskkill /T`); timeout 5s → force; kiểm không để tiến trình mồ côi.
  (H32.4 Phase 0.2 đã ghi nhận nhưng chưa làm.)
- **Test:** hủy job giữa render → `tasklist` không còn ffmpeg con; credit hoàn đúng.
- **Acceptance:** đo 2 lần, log tiến trình trước/sau.

### 0.4 Đo WER tiếng Việt thật + disclosure confidence
- **Tệp:** script đo tạm (không commit kết quả vào code) +
  `apps/taoclipngan/features.py` (hiển thị confidence STT trên UI).
- **Đổi:** trên 4 video test, so transcript Whisper với transcript tay (chủ
  dự án nghe, đánh dấu câu sai) → số WER VI; UI hiển thị "chính xác ~X%"
  hoặc che nếu dưới ngưỡng.
- **Acceptance:** bảng WER 4 video trong `_EVIDENCE/`; UI có confidence line.

**Xong Pha 0 =** pipeline tin cậy, không LLM, chạy 4 video thật không lỗi.

---

## PHA 1 — Video Memory + Intent LLM (lần đầu chạm LLM)

**Mục tiêu:** memory có cấu trúc cho cả tầng LLM; prompt ý định VN được hiểu.

### 1.1 Memory Builder
- **Tệp:** `cutclipshort/editorial/memory_builder.py` (mới),
  `cutclipshort/types.py` (dataclass `VideoMemory`, `Segment`),
  `cutclipshort/core/pipeline.py` (gọi builder sau wave).
- **Đổi:** ghép kết quả 6 engine + transcript word-level → `VideoMemory`:
  `segments[]` = {t_start, t_end, transcript, hook_score, payoff_score,
  motion, audio_energy, persons[], genre_cues}. Nén transcript khi vượt trần
  token (cut theo câu, pattern `auto_scan_video/hieu_canh.py:170-176`).
  Serialize JSON → cache theo `(source_hash, engine_versions, memory_version)`.
- **Test:** build trên fixture transcript 5 segment → JSON đúng schema;
  transcript dài → nén theo câu không cắt giữa từ.
- **Acceptance:** video cooking 79 MB → file memory JSON < 32 KB, mở được,
  đúng số scene của SceneDetect.

### 1.2 Cổng LLM duy nhất + intent analysis
- **Tệp:** `apps/taoclipngan/services/llm.py` (mới — duy nhất nơi gọi
  `dieu_phoi.goi`), `apps/taoclipngan/services/intent.py` (mới).
- **Đổi:**
  - `services/llm.py`: bọc `dieu_phoi.goi(db, messages, thu_tu_provider,
    model_theo_provider={...id thật...}, ma_luot=f"tcng-{job_id}-{bước}")`.
    Xử lý lỗi đúng thứ tự `auto_scan_video/ai.py:740-769`: `BanError` trước
    `AmbiguousProviderError`, mơ hồ → dừng bước LLM (degrade), không phải
    lỗi job. Retry `BanError` ≤ 1 lần theo `retry_after_s`.
  - `intent.py`: prompt VN → JSON {topic, cam_xuc, do_dai_muon, bat_buoc,
    tranh}. Model `ltt-3.5`, `response_format` JSON schema. **Không prompt →
    bỏ bước, memory vẫn đi tiếp.**
- **Test:** `test_tcn_llm_cua.py` — mock `dieu_phoi.goi`: (a) BanError →
  degrade, không raise; (b) JSON sai → retry → degrade; (c) `ma_luot` đúng
  khuôn; (d) test chốt không file nào khác trong app import `dieu_phoi` trực
  tiếp (pattern `test_434` của ASV).
- **Acceptance:** gõ "cắt cho tôi đoạn anh ấy thử món lần đầu, ngắn gọn" →
  intent JSON đúng các trường; tắt máy B → job vẫn xong bằng heuristic,
  manifest `"mode": "heuristic"`.

**Xong Pha 1 =** LLM vào pipeline an toàn, degrade 100%, intent đọc được tiếng Việt.

---

## PHA 2 — Editorial Brain V2 + UI Review (trái tim của "next-gen")

**Mục tiêu:** clip được chọn bởi LLM + người dùng, mỗi clip có lý do.

### 2.1 LLM selection layer
- **Tệp:** `cutclipshort/editorial/brain.py` (mở rộng),
  `cutclipshort/editorial/llm_selector.py` (mới),
  `apps/taoclipngan/jobs.py` (truyền intent + memory).
- **Đổi:**
  - `llm_selector.py`: input = VideoMemory (nén) + intent → output
    JSON [{t_start, t_end, loai (hook/story/shock/insight/payoff/loop),
    ly_do_vi, self_score 0-99, confidence}]. Model `ltt-3.8`, 1 lượt,
    `reasoning_effort` khai theo thao tác.
  - `brain.py`: merge — LLM candidates **gộp vào** pool của 6-pass heuristic
    (dedup semantic có sẵn), ranker chấm tất cả. LLM hỏng → pool heuristic
    nguyên vẹn (Pha 1 đã chứng minh degrade).
  - Score hiển thị: `self_score + confidence` thay vì 4 số heuristic trần.
- **Test:** fixture memory + intent → merge không mất candidate heuristic;
  selector trả rỗng → pipeline vẫn ra 3 clip; duplicate window 90% → dedup.
- **Acceptance:** 4 video thật — mỗi clip trong package có `ly_do_vi` tiếng Việt
  đọc được + score; so với baseline heuristic: số clip bị người dùng (chủ dự án)
  đánh dấu "đúng" tăng (ghi trong `_EVIDENCE/`).

### 2.2 UI Review (human-in-the-loop)
- **Tệp:** `apps/taoclipngan/routes.py` (thêm 2 endpoint),
  `apps/taoclipngan/templates/taoclipngan.html` (mở rộng) hoặc template mới,
  `apps/taoclipngan/jobs.py` (tách render khỏi pipeline — chạy khi khách chọn).
- **Đổi:**
  - Endpoint `POST /review/{job_id}` (ghi lại giữ/bỏ + trim + reframe override)
    và `POST /review/{job_id}/render` (job render chỉ clip được chọn;
    **quote credit trước** — pattern Q47 upscalevideo).
  - Job mới dừng sau quality gate → trạng thái `DANG_CHO_REVIEW`; UI list
    ứng viên: preview ngắn (`/v/{key}` có sẵn), transcript, lý do, score,
    nhãn mode; kéo đầu-cuối trên transcript (word-level timestamps có sẵn).
  - Timeout 24h → auto render top-3.
  - ⚠️ Ngưỡng `routes.py` (`tools/lint_app_contract.py::MAX_ROUTES_*`):
    vượt WARN thì tách `services/review.py` — làm sẵn từ đầu.
- **Test:** test API (không Playwright) — POST review bỏ hết → render trả 0 clip
  + hoàn credit giữ chỗ; timeout fake → top-3; CSRF/permission như endpoint
  hiện có.
- **Kiểm GUI** (CLAUDE.md luật 7): luồng thật trên `127.0.0.1:8100`,
  screenshot vào `_EVIDENCE/`.
- **Acceptance:** chủ dự án chạy 1 video thật, giữ 2/bỏ 1, kéo trim 3s, nhận
  package đúng 2 clip đã sửa — không render clip đã bỏ.

**Xong Pha 2 =** trải nghiệm "next-gen" đầy đủ: chọn bằng ý, xem trước, sửa trước, render đúng ý.

---

## PHA 3 — Reframe V2 + manual override

**Mục tiêu:** crop theo đúng người nói xuyên clip, khách kéo khung được.

### 3.1 Tracking denser
- **Tệp:** `cutclipshort/render/framing.py` (mở rộng `FramingParams` thêm
  `boxes_per_frame`), engine YOLO (mẫu 1 fps trong window clip — cache theo
  source), `cutclipshort/render/segment_renderer.py` (dùng chuỗi boxes).
- **Đổi:**
  - Thay 2 keyframe bằng chuỗi mẫu 1 fps; smooth như hiện tại (smoothstep
    giữa các mẫu gần nhau).
  - Chọn chủ thể: giao diện transcript + audio energy (người đang nói) thay vì
    "người lớn nhất"; nhiều người → heuristic (người có thoại gần nhất,
    audio energy cao nhất). ⛔ Không VLM: `qwen38-vision` đã gỡ D02/L-14
    (`ltt_llm` text-only — xác minh 25/09).
  - Không có người: giữ center + zoom 1.0 + flag QA (không còn crop rủi ro).
- **Test:** fixture boxes 20 khung → crop path mượt không nhảy; không người →
  zoom 1.0; nhiều người có thoại → chọn đúng người đang nói.
- **Acceptance:** video camp (nhiều người, chuyển động) — xem preview: khung
  không rớt người đang nói; không khung nào cắt đầu người.

### 3.2 Manual override UI
- **Tệp:** template review (mở rộng từ 2.2), `jobs.py` (lưu override).
- **Đổi:** kéo khung trong ô preview 9:16 → lưu
  `manual_boxes: [(t_start, t_end, x, y, w, h)]` → render đoạn đó bỏ auto.
- **Test:** override 1 đoạn → crop render đúng khung tay (đo bằng so bbox trong
  frame xuất); không override → auto.
- **Acceptance:** chủ dự án kéo khung 1 đoạn 5s trên video airsoft → output
  đúng khung đã kéo.

**Xong Pha 3 =** reframe ngang ReframeAnything ở điểm cốt lõi (track xuyên clip +
chủ thể đang nói + ghi đè tay).

---

## PHA 4 — Vòng học + phân phối (khác biệt hoá, không ai trong 9 đối thủ có)

### 4.1 Preference store → ranker
- **Tệp:** `apps/taoclipngan/tables.py` (mới: `tcng_preference`, `tcng_pin`),
  `cutclipshort/editorial/clip_ranker.py` (đọc preference), manifest
  (`table_prefix`).
- **Đổi:** UI review ghi mỗi hành vi (giữ/bỏ/pin); ranker: ứng viên có pin
  gần window → +boost (quy tắc cố định, không train); preference theo user.
- **Test:** pin window X → chạy lại job (mock) → ứng viên chứa X rank lên top.
- **Acceptance:** 2 job liên tiếp cùng user, job 2 ưu tiên đúng vùng pin của job 1.

### 4.2 Nối publish_bot
- **Tệp:** `apps/taoclipngan/services/distribution.py` (mới), routes (1
  endpoint "Đăng" từ review/package).
- **Đổi:** typed handoff sang `publish_bot` (kiểm tra cạnh app→app — nếu
  `APP_DUOC_DUNG_APP` chưa có cặp taoclipngan→publish_bot thì **đó là quyết
  định kiến trúc, phải khai + ghi lý do**; AGENTS.md §8.3). Trạng thái publish
  quay lại UI.
- **Test:** mock publish_bot → job publish tạo, trạng thái cập nhật; cạnh app
  khai đúng (`test_308` hai chiều).
- **Acceptance:** 1 clip đăng thật qua publish_bot (tài khoản test
  `akakenly.design@gmail.com` — luật 3b, chủ dự án đăng nhập).

### 4.3 (Tuỳ chọn, sau khi 4.2 chạy) Retention → ranker
- Publish_bot trả stats sau 24–48h → bảng `tcng_feedback_stats` → hiệu chỉnh
  trọng số ranker theo kênh. **Chỉ làm khi có ≥ 20 clip đã đăng có số.**

**Xong Pha 4 =** vòng lặp "càng dùng càng đúng" — điểm không đối thủ nào có
(`_C` §4.2: "trong 9 công cụ, không ai lấy performance thật để sửa model").

---

## RỦI RO & ĐƯỜNG LUI TỪNG PHA

| Pha | Rủi ro chính | Đường lùi |
|---|---|---|
| 0 | Gate chặn nhầm clip tốt (threshold cũ chưa calibrate) | Mode `warn` mặc định; chỉ `block` sau khi đổi lifecycle `released` + đo lại trên 4 video |
| 1 | Máy B bận thường xuyên (7 suất chia mọi app) | Degrade = hành vi hiện tại (đã có từ trước); `BanError` retry 1 lần; không queue LLM trong worker render |
| 2 | LLM chọn clip dở hơn heuristic | Merge (không thay thế); người dùng vẫn chọn tay ở review UI; A/B trên 4 video trước khi tin |
| 2 | UI review vượt ngưỡng routes.py | Tách `services/` từ đầu; lint WARN là báo hiệu, không chặn |
| 3 | YOLO 1 fps chậm trên video dài | Chỉ mẫu **trong window clip đã chọn** (20–40s), không mẫu cả file; cache theo source |
| 4 | publish_bot chưa có contract hợp | Dừng trước, ghi quyết định kiến trúc, không tự sửa app khác |

## QUYẾT ĐỊNH CẦN CHỦ DỰ ÁN TRƯỚC KHI BẮT ĐẦU

1. **Pha nào làm trước?** Roadmap trên là thứ tự đề xuất (0→4). Có thể dừng
   sau Pha 2 ("next-gen" đã đủ) rồi quay lại.
2. **Công thức credit khi có LLM** — phương án A/B/C (`03_TARGET_ARCHITECTURE.md`
   §3.4). Đề xuất A (giữ nguyên).
3. **Số clip mặc định trong review** — hiện render 3. Đề xuất 5 ứng viên,
   khách giữ 1–3.
4. **Vị trí UI review** — mở rộng `taoclipngan.html` (đề xuất) hay trang riêng.
5. **4.2 publish_bot** — có trong phạm vi đợt này không (cần khai cạnh app→app).

## TÀI LIỆU KÈM

- `_A_CURRENT_TRUTH_RAW.md` — audit code chi tiết
- `_B_LLM_INTEGRATION_RAW.md` — audit LTT_LLM (đang hoàn thành, sẽ đối chiếu)
- `_C_COMPETITORS_RAW.md` — 9 đối thủ, 16 chiều, 12 điểm cơ hội
- `01_CURRENT_TRUTH.md` — sự thật đã xác minh kèm dẫn chứng tệp:dòng
- `02_GAP_MATRIX.md` — chênh lệch hiện tại × đối thủ × mục tiêu
- `03_TARGET_ARCHITECTURE.md` — kiến trúc mục tiêu + luật degrade + tiền
