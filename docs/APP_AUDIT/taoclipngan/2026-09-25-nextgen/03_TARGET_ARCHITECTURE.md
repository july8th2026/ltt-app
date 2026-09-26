# 03 — TARGET ARCHITECTURE: pipeline next-gen

> Nguyên tắc: **giữ mọi engine đang chạy thật, thêm lớp LLM bên trên, mỗi lớp LLM
> phải degrade về heuristic khi máy B bận.** Không viết lại 6 engine, không gọi LLM
> trong worker render.

## 1. Pipeline mục tiêu

```
INPUT (routes.py — giữ)
  → PROBE + ANALYSIS (6 engine — GIỮ NGUYÊN, cache mở rộng)
  → ★ MEMORY BUILDER (mới): dựng "video memory" có cấu trúc
       temporal index: segment[] = {t_start, t_end, transcript, scene,
       motion_score, audio_energy, persons[], hooks[], payoffs[]}
  → ★ LLM UNDERSTANDING (mới, degrade được):
       1. Intent analysis: prompt VN → cấu trúc ý định (topic, cảm xúc, độ dài,
          điều bắt buộc/bắt buộc-tránh)
       2. VLM scene enrich: mẫu 8–16 khung/segment ứng viên → mô tả thị giác
          (ai là chủ thể, gì đang xảy ra, có văn bản chữ trên màn hình không)
       3. LLM selection: memory + ý định → danh sách ứng viên kèm lý do
  → EDITORIAL V2 (brain.py nâng cấp):
       - 6-pass heuristic (GIỮ — làm nền + làm đường lui)
       - LLM selection layer (kết quả LLM được merge vào, không thay thế)
       - ★ QUALITY GATE (evaluation/gate.py — CÓ SẴN, lần đầu được NỐI)
  → ★ REVIEW (bề mặt mới): UI khách xem 3–5 ứng viên, giữ/bỏ, trim transcript,
       kéo khung reframe, pin khoảnh khắc → chọn tập render
  → PLAN + RENDER (framing V2: tracking denser + VLM chủ thể + ghi đè tay)
  → QA (composite_scorer — giữ)
  → OUTPUT (giữ) + ★ FEEDBACK (preference store: pin/chọn/bỏ → ranker)
```

## 2. Memory Builder (nền móng của cả tầng LLM)

- **Vị trí:** `cutclipshort/editorial/memory_builder.py` (mới) — nhận kết quả
  6 engine + transcript, ra `VideoMemory` (dataclass) có thể serialize JSON.
- **Nội dung:** segment theo scene cut (SceneDetect đã có), mỗi segment mang:
  transcript word-level (Whisper đã có), hook/payoff score (đã có), motion,
  audio energy, persons bounding box (YOLO đã có), genre cue.
- **Không tính mới** — chỉ ghép những gì 6 engine đã ra. Chi phí: CPU nhẹ.
- **Kích thước trần:** nếu > N token (ước bằng `platform_core/llm/uoc_token.py`),
  nén transcript thành câu chính (cut theo câu — pattern `auto_scan_video/hieu_canh.py:170`).
- **Coi là cache được:** key theo `(source_hash, engine_versions, memory_version)`.

## 3. Tầng LLM — thiết kế gọi

### 3.1 Một cổng gọi duy nhất (pattern `auto_scan_video`)

- `apps/taoclipngan/services/llm.goi_model(...)` — **duy nhất** nơi gọi
  `platform_core.llm.dieu_phoi.goi`. Test chốt không file nào khác gọi trực tiếp
  (như `test_434` của ASV).
- Xử lý lỗi theo thứ tự đã bị cắn 2 lần (`ai.py:740-769`):
  `BanError` (429 — chắc chắn, chưa chạy) → hỏi lại sau; **trước** khi phân loại
  `AmbiguousProviderError` (mơ hồ — dừng, cho người quyết định); mọi lỗi khác
  → degrade.
- `ma_luot` = mã job + tên bước (vd `tcng-{job_id}-select`) → hủy được theo tên
  + nối log hai máy.
- `model_theo_provider` khai id model thật (vd `{"ltt_llm": "qwen38-api"}`) —
  ⛔ không dùng bí danh app (bài học `dieu_phoi.py:251-267`).

### 3.2 Phân bổ model

⚠️ **SỰ THẬT VLM (xác minh 25/09, sửa thiết kế gốc):** `qwen38-vision` đã bị **gỡ ở
D02/L-14** — `ltt_llm` chỉ còn hồ sơ `qwen38-api` (text-only)
(`apps/ltt_llm/manifest.py:65-66`, `llm_gateway/deploy/llama-swap.yaml:21-25`).
Pattern `auto_scan_video/hieu_canh.py` với `image_url`+`data:` là **lịch sử**
(vòng sửa phase 27 của ASV), không còn đường VLM qua `ltt_llm`.

Hệ quả cho plan:
- **Scene enrich bằng text-only:** LLM đọc **transcript + tín hiệu engine**
  (hook/payoff/persons/audio) — không gửi khung hình. Chất lượng enrich giảm
  một bậc so với VLM nhưng **không phụ thuộc VLM nào**; nếu `anhnoibo`
  (render_gateway VLM máy B) có hợp đồng app→app thì nâng cấp sau —
  **không trong scope đợt này**.
- Reframe V2 vẫn chạy bằng **YOLO tracking (số liệu, không LLM)** — chủ thể
  đang nói lấy từ transcript + audio energy; VLM xác nhận người thứ hai **bỏ**,
  thay bằng heuristic đa người (người đang nói > người lớn nhất).

| Bước | Model | Lý do |
|---|---|---|
| Intent analysis | `ltt-3.5` (4 suất, rẻ) | Câu ngắn, 1 lượt |
| LLM selection (editorial) | `ltt-3.8` (3 suất, mạnh) | 1 lượt, memory đã nén |
| Scene enrich (text-only) | `ltt-3.8` | Transcript + tín hiệu engine; KHÔNG khung hình |
| Explanation (lý do chọn clip) | `ltt-3.5` | Câu ngắn |

- **Reasoning effort:** `low`/`medium` cho selection; `None` (mặc định) cho câu
  ngắn — pattern `ai.py:698-710`.
- **Trần token:** `response_format` JSON schema (grammar của llama-server — ràng
  buộc cứng, không phải lời nhắc; `ai.py:712-728`).
- **Budget:** mỗi job ≤ ~4 lượt LLM + ≤ 2 lượt VLM (tránh whale, tránh cháy pool
  KV — `BAN_DO_DUONG_DI.md` §3). Mọi số này là hằng số khai trong app, có test.

### 3.3 Degrade (luật sống còn)

| Tình huống | Hành vi |
|---|---|
| Máy B bận (`BanError`) | Chờ theo retry_after tối đa 1 nhịp; hết → **chạy đường heuristic 6-pass nguyên vẹn** (hành vi hiện tại), gắn nhãn `"mode": "heuristic"` vào manifest |
| LLM trả JSON sai (grammar đã chặn phần lớn; nhánh còn lại) | 1 retry; còn sai → heuristic |
| Scene enrich (text-only) hỏng | Selection chạy trên transcript + số liệu engine thuần (khả năng degrade gốc của 6-pass) |
| Toàn bộ tầng LLM chết | Pipeline chạy đúng như hôm nay — **không bao giờ job lỗi vì LLM** |

⚠️ LLM chỉ làm tốt hơn, không bao giờ là điều kiện để job thành công. Đây là
sự khác biệt với đối thủ SaaS (LLM = dịch vụ).

### 3.4 Tiền — câu hỏi CHO CHỦ DỰ ÁN (chưa chốt trong plan)

Công thức hiện tại `phút×tier×5 + clip×5` không tính lượt LLM. LLM chạy trên
máy B (chi phí biên nội bộ, không phải API trả phí). Ba phương án:

- **A (khuyến nghị):** giữ công thức — LLM là phần "tốt hơn" của cùng gói.
  Đãi khách bằng chất lượng, không thêm biến giá.
- **B:** thêm `+2 credit/lượt selection` — minh bạch hơn nhưng phàn nàn "credit
  khó hiểu" là điểm chết của cả ngành (`_C` §4.4).
- **C:** gói theo số clip nhận được ("99k = 5 clip") — khác biệt hoá giá,
  nhưng đổi công thức = quyết định sản phẩm lớn.

Plan triển khai theo **A**; đổi sang B/C chỉ là sửa `cost.py` + manifest, không
chạm kiến trúc.

## 4. Reframe V2

| Lớp | Hiện tại | Mục tiêu |
|---|---|---|
| Mật độ tracking | 2 keyframe (start/end clip) | Mẫu **1 fps** YOLO trong clip (clip 20–40s = 20–40 lần detect, CPU/GPU nhẹ, cache theo source) |
| Chọn chủ thể | Người lớn nhất (`framing.py:125`) | Người đang nói (đồng bộ audio energy + transcript); nhiều người → heuristic (người có thoại gần nhất), ⛔ không VLM (đã gỡ D02) |
| Ghi đè tay | Không | UI kéo khung trong preview 9:16 → lưu `manual_boxes[t_start..t_end]` → render dùng khung tay, bỏ auto cho đoạn đó |
| Không có người | Fallback center (nguy cơ crop sai) | Giữ center nhưng **giảm zoom về 1.0** + flag trong QA để cảnh báo khách |

`FramingParams` mở rộng thêm `boxes_per_frame: list[(t, cx, cy, zoom)]` —
trước khi render, downsample + smooth như hiện tại (giữ `smoothstep`).

## 5. Review UI (human-in-the-loop)

- **Kỹ thuật:** server-rendered (như `taoclipngan.html` hiện tại + JS thuần),
  preview clip qua endpoint `/v/{key}` đã có. Không dựng React bundle mới
  (nhẹ, đồng nhất với các app khác; bundle React chỉ khi nào UI vượt ngưỡng
  mà `tools/lint_app_contract.py` WARN).
- **Luồng mới:**
  1. Job chạy tới sau quality gate → **không render ngay** → UI hiện 3–5
     ứng viên: video preview ngắn, transcript, lý do chọn (LLM hoặc heuristic),
     score + confidence, nhãn mode (LLM/heuristic).
  2. Khách: giữ/bỏ, trim đầu-cuối (kéo trên transcript — thời gian word-level
     có sẵn), kéo khung reframe, gõ thêm prompt ("cắt gần vào khoảnh khắc X").
  3. "Tạo clip" → job render **chỉ các clip được giữ**, quote credit trước
     (pattern Q47 của upscale: quote/confirm trước khi nộp).
- **Credit:** giữ chỗ khi bắt đầu job (như hiện tại); render sau review chỉ tính
  clip thật sự render; bỏ clip → không tốn.
- **Timeout review:** 24h không chọn → tự render top-3 (không bỏ rơi job).

## 6. Feedback / vòng học (lợi thế không đối thủ nào có)

- `apps/taoclipngan/tables.py` (mới) — 2 bảng:
  - `tcng_preference`: (user_id, job_id, candidate_id, action: kept/discarded/pinned, t_range)
  - `tcng_pin`: (user_id, source_hint, t_range, note)
- Ranker (`clip_ranker.py`) đọc preference của user → điều chỉnh trọng số
  diversity/intent (bắt đầu bằng quy tắc đơn giản: pin trong 5s của ứng viên →
  +boost; KHÔNG train model).
- Publish → stats retention (giai đoạn 4, qua publish_bot) → cùng bảng.

## 7. Những gì KHÔNG làm (phạm vi này)

- Không XML/FCPXML, không team workspace, không scheduler riêng (dùng
  publish_bot), không API/MCP công khai, không import YouTube/Drive,
  không speaker diarization mới (dùng có sẵn), không dubbing.
- Không sửa `platform_core/`, `server/`, `apps/ltt_llm/`.
- Không đổi công thức credit (theo phương án A cho tới khi chủ dự án chốt khác).
