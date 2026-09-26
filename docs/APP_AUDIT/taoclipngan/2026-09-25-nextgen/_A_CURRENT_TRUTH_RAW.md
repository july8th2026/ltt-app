# _A — CURRENT TRUTH RAW (Tạo Clip Ngắn) — audit 2026-09-25

> Nguồn: subagent audit code + đọc trực tiếp `apps/taoclipngan/` (manifest/jobs/cost).
> ⚠️ Cây repo đang đổi song song (package engine từng có tên `tclipshort` → `clipshort`).
> Mọi dẫn chứng nên kiểm lại bằng glob trước khi sửa. Trạng thái node theo
> REAL / PARTIAL / MOCK / UNUSED / DUPLICATED / DEAD / BOTTLENECK.

## 1. Sơ đồ pipeline thực tế

```
INPUT (apps/taoclipngan/routes.py)
  → UPLOAD (browser → storage, _DIRECT_VIDEO_MAX = 1 GB)
  → JOB QUEUE (apps/taoclipngan/jobs.py:54-228, handle() trong GPU worker)
  → UNDERSTANDING: probe (cutclipshort/.../core/analysis_runner.py)
  → ANALYSIS (6 engine, song song theo wave):
      ├─ scene_engine (SceneDetect)
      ├─ speech_engine + Whisper (GPU)
      ├─ motion_engine
      ├─ audio_engine + Demucs
      ├─ visual_engine + YOLO (GPU)
      └─ content_engine
  → EDITORIAL (pure Python, KHÔNG LLM):
      ├─ candidate_generator.py (62KB, 6 pass: hook→story→shock→insight→payoff→loop)
      ├─ hook_detector.py / payoff_detector.py
      ├─ clip_ranker.py (4 objectives)
      ├─ coherence.py / semantic_scorer.py (pure Python NLP)
      └─ genre_classifier.py / genre_cues.py (53KB)
  → PLAN (edit_plan_builder.py)
  → EDIT + RENDER (segment_renderer.py + compositor.py, NVENC/libx264)
      └─ framing.py (YOLO-guided crop) · caption_renderer.py (ASS word-chunked)
  → QA (evaluation/composite_scorer.py)
  → OUTPUT (routes: phat media, storage.put)
  → FEEDBACK (manifest JSON + credit_cost)
```

| NODE | TRẠNG THÁI | GHI CHÚ |
|------|-----------|---------|
| INPUT | **REAL** | upload trực tiếp, limit 1 GB |
| UNDERSTANDING | **REAL** | probe + 6 engine |
| ANALYSIS | **REAL** | 6 engine song song; GPU: whisper+yolo |
| EDITORIAL | **REAL (nhưng heuristic)** | 6-pass generator, pure Python, 0 LLM |
| RANK | **REAL** | 4-objective ranker, heuristic |
| PLAN | **REAL** | edit_plan_builder |
| RENDER | **REAL** | NVENC p5, YOLO crop, ASS caption |
| QA | **REAL (không gate chặn)** | composite_scorer tính điểm; chưa chặn output |
| OUTPUT | **REAL** | storage + media |
| FEEDBACK | **PARTIAL** | có manifest, chưa có vòng learning thật |

## 2. Bảng module chính

| MODULE | CHỨC NĂNG | ENGINE THẬT | TRẠNG THÁI | GPU | CACHE |
|--------|-----------|-------------|-----------|-----|-------|
| app surface (routes/manifest) | upload, credit, UI | FastAPI | REAL | — | — |
| job handler (jobs.py:54) | dispatch GPU | 3 hàm lõi | REAL | 6000 MB | — |
| cost.py | credit = phút×tier + clip×5 | heuristic | REAL | — | — |
| pipeline.py | orchestrate wave analysis | engine | REAL | yes | — |
| analysis_runner.py | entry phân tích | engine | REAL | yes | yes |
| cache.py (storage) | key=(source_hash, engine, config) | — | REAL | — | yes |
| whisper adapter | STT | Whisper | REAL | yes | model cache |
| yolo adapter | person detect | YOLOv8s | REAL | 0.1–0.3 GB | model cache |
| ffmpeg_hw | NVENC/QSV detect | ffmpeg | REAL | yes | — |
| candidate_generator | 6-pass proposal | pure Py | REAL | — | — |
| hook/payoff detector | đầu/cuối clip | heuristic | REAL | — | — |
| clip_ranker | multi-objective | heuristic | REAL | — | — |
| coherence / semantic_scorer | khớp hook-payoff, NLP | pure Py | REAL | — | — |
| framing.py | YOLO crop + smooth | YOLO | REAL | yes | — |
| segment_renderer | encode 1 clip | NVENC/x264 | REAL | yes | — |
| caption_renderer | ASS word-chunk | — | REAL | — | — |
| composite_scorer (QA) | điểm tổng hợp | heuristic | REAL | — | — |

## 3. Editorial — công thức thật

**Candidate generator — 6 pass:**
1. HOOK (luôn): opening mạnh, câu hỏi/keyword táo bạo.
2. STORY: narrative arc.
3. SHOCK: emotional spike, tranh cãi.
4. INSIGHT: density thông tin cao.
5. PAYOFF: resolution/kết.
6. LOOP: khoảnh thỏa mãn ngắn 5–20 s.
Post: coverage-gap scan + semantic dedup + scoring.

**Hook score:** `energy×0.25 + text_signal×0.35 + engagement×0.15 + (0.15 if speech) − silence_penalty`.
**Payoff score:** `closure_kw×0.30 + sentence_complete×0.35 + energy_drop×0.15 + trailing_pause×0.20`.
**Ranker:** `W_QUALITY=0.40, W_DIVERSITY=0.20, W_COVERAGE=0.25, W_INTENT=0.15`.
**Coherence:** `direct_overlap×0.6 + full_overlap×0.4 + new_concept_bonus`.

**LLM?** grep `llm|LLM|openai|http` trong `cutclipshort/` → **0 match**. Mọi editorial là pure Python. Đây là điểm trống lớn nhất cho "Editorial Brain V2".

## 4. Rendering

- **Crop:** YOLO-guided (person → cx, cy, zoom); smooth_alpha theo pan speed (0.04–0.15); không có person → fallback center (nguy cơ crop sai chủ thể).
- **Caption:** ASS word-level chunking 2–4 s; responsive scale theo short side; safe margin top 15% / bottom 12% / side 5.5%; highlight số/câu hỏi/superlative.
- **Encode:** NVENC p5 nếu có, else libx264 (priorities: h264_nvenc > h264_qsv > libx264).
- **Preview:** 480w CRF=28 libx264; thumbnail riêng.

## 5. Cache + Cancel + GPU

- **Cache key:** `(source_hash, engine_name, engine_version, config_hash)` — ⚠️ KHÔNG gồm genre/tier/aspect.
- **Cancel:** `request_cancel()` đặt flag + `cancel_check()` ở mọi stage; giết FFmpeg subprocess + model threads; credit refund theo phút thật + clip thật.
- **GPU lease:** manifest `gpu_vram_mb=6000`, `resource={class:gpu, vram_min_mb:6000, slots:1}`; qua `platform_core/job_runner.py`. `health_check.py` check CUDA, fallback CPU.

## 6. Credit / lifecycle (đã đọc trực tiếp)

- `cost.py`: `credit = phút_nguồn × he_so_tier × 5 + số_clip × 5`; tier ×1.0/1.6/2.2.
- `manifest.py`: `lifecycle="development"` — **chưa "Đã phát hành"** (field điều khiển trạng thái release). `enabled=True`, `badge="MỚI"`, `requires=("gpu","ffmpeg")`.
- `jobs.py`: resume idempotent qua `manifest_key` (clips.json); giữ chỗ → đo thật → quyết toán; NÉM khi lỗi → nền hoàn credit.
- App **KHÔNG gọi LLM**, KHÔNG có VLM.

## 7. Top bottleneck / cơ hội

**Bottleneck (cao→thấp):**
1. Cancel cooperative chưa chắc giết hết FFmpeg/model thread (BOTTLENECK).
2. Cache key thiếu genre/tier/aspect → cache stale sai ngữ cảnh.
3. Crop fallback center khi không có person (khó crop sai chủ thể).
4. Semantic scorer pure Python — yếu với tiếng Việt phức tạp.
5. Hook/score hard-threshold, không có confidence range.
6. Không có vòng learning/calibration thật (feedback store có nhưng chưa nối).

**Cơ hội (engine cũ đủ, nối LLM — lợi thế LTT):**
1. **Prompt-directed clipping** — chưa có; LLM đọc "temporal video memory" để chọn theo ý người dùng (P0).
2. **Editorial Brain V2** — LLM reasoning trên structured memory thay heuristic (P0).
3. **Viral score V2** — LLM multi-objective + explainability thay 4 số heuristic (P0/P1).
4. **Human-in-the-loop review** — candidate list + transcript trim/crop/caption edit (P0).
5. **LLM explanation** — lý do chọn clip tiếng Việt tự nhiên (P1).
