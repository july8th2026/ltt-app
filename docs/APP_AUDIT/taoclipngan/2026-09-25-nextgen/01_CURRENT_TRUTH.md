# 01 — CURRENT TRUTH (đã xác minh trên code, 2026-09-25)

> Mọi mục có dẫn chứng `tệp:dòng`. Rà soát lại bằng glob/grep trước khi sửa
> (cây repo từng đổi tên `clipngan` → module đặt trực tiếp dưới `apps/taoclipngan/`).

## 1. Bề mặt app

- 7 endpoints, không có UI review/sửa clip — luồng one-shot: upload → queue → package zip.
  - `apps/taoclipngan/routes.py:167` GET "" (trang HTML), `:172` POST /estimate,
    `:193` POST /upload-url, `:245` POST /queue, `:408` POST /package/{job_id}/save,
    `:457` GET /package/{job_id}.zip, `:508` GET /v/{key:path}` (phát media)
- UI template 18,7 KB — `apps/taoclipngan/templates/taoclipngan.html`
- `manifest.py`: `lifecycle="development"`, `enabled=True`, `badge="MỚI"`,
  `gpu_vram_mb=6000`, `requires=("gpu","ffmpeg")`
- `cost.py`: `credit = phút_nguồn × he_so_tier × 5 + số_clip × 5`; tier ×1.0 / ×1.6 / ×2.2
- **App KHÔNG gọi LLM, KHÔNG có VLM** (grep `llm|openai|http` trong app → 0)

## 2. Job pipeline (`jobs.py`, 230 dòng)

`handle()` trong GPU worker:

```
upload object → probe → run_full_analysis (6 engine song song theo wave)
→ run_editorial (brain.py, pure Python) → render 3 clip → storage.put
→ manifest (clips.json, credit_cost)
```

- **Giữa editorial và render KHÔNG có quality gate** — `evaluation/gate.py`
  tồn tại nhưng không được gọi ở đâu trong `jobs.py` (xác minh: không có import
  `gate`/`build_evaluators_for_tier` trong jobs.py).
- Resume idempotent qua `manifest_key`; credit: giữ chỗ → đo thật → quyết toán;
  lỗi → ném → nền hoàn credit.

## 3. Engine `cutclipshort/`

| Module | Chạy thật | Ghi chú |
|---|---|---|
| `core/pipeline.py` (445 dòng) | orchestrator wave | cache theo `AnalysisCache` |
| 6 engine: scene/speech+Whisper/motion/audio+Demucs/visual+YOLO/content | GPU: whisper, yolo | YOLOv8s ~0,1–0,3 GB |
| `editorial/brain.py` (274 dòng) | editorial chính | tier-aware config, semantic context **optional**, degrade graceful khi fail |
| `editorial/candidate_generator.py` (1630 dòng) | 6-pass: hook/story/shock/insight/payoff/loop | `_low_transcript` (<30% chất lượng) → degrade motion-only |
| hook/payoff detector, clip_ranker (W: quality .40 / diversity .20 / coverage .25 / intent .15), coherence, semantic_scorer, genre_classifier (53 KB) | pure Python NLP | 0 LLM |
| `evaluation/gate.py` (340 dòng) | **chưa nối** | hard reject: hook<0.20, intent<0.25, completion<0.20, <5s |
| `evaluation/__init__.py` | expose `build_evaluators_for_tier` | CompositeScorer có, jobs.py không dùng |
| `render/framing.py` (152 dòng) | **chỉ 2 keyframe start/end** | `FramingParams(cx_start→cx_end, zoom_start→zoom_end)` + smoothstep interpolation; adaptive alpha 0.04–0.20 theo pan speed; không người → fallback center; **KHÔNG có tracking per-frame** (khác ReframeAnything của OpusClip) |
| `render/segment_renderer.py`, `compositor.py`, `caption_renderer.py` | NVENC p5 → QSV → libx264 | caption ASS word-chunk 2–4s |
| `storage/cache.py` (117 dòng) | key = `(source_hash, engine_name, engine_version, config_hash)` | **KHÔNG gồm genre/tier/aspect** → có thể stale sai ngữ cảnh |

## 4. Cầu nối LLM (đã đọc trực tiếp — chi tiết trong `_B`)

- `platform_core/llm/dieu_phoi.py:240` — `goi(db, *, messages, thu_tu_provider,
  model, model_theo_provider, tools, max_tokens, temperature, reasoning_effort,
  ma_luot, ...) -> KetQuaChat`. Cascade provider theo thứ tự app khai;
  ⚠️ `model_theo_provider` phải khai id model thật (vd `"ltt_llm": "qwen38-api"`),
  không dùng bí danh app — đã dạy sai 2 chỗ trước đây (docstring line 251–267).
  `ma_luot` = mã lượt, đi lên máy B trong `X-LTT-Request-Id` + cho `huy_luot.huy()`
  hủy theo tên.
- `platform_core/llm/cong_vlm.py:277` — `CongVlm.chat(...)` wrapper HTTP tầng thấp
  (`POST /v1/chat/completions`), lỗi phân loại: `BanError` (bận, có retry_after),
  `HuyError`, `ProviderOomError`, `VuotNganSachError`, `YeuCauSaiError`.
  ⛔ không có tham số fallback — việc lui model là quyết định tầng trên, phải
  tính tiền theo model lui.
- `platform_core/llm/admission.py` — lease chống OOM: `xet_va_giu` (line 429),
  `acquire` (542), `heartbeat` (673), `release` (682), `keep_alive` (717),
  `hold_persisted` (780); có prefill theo tài nguyên + cửa cu-tru nhóm.
- Model: `canonical.MODEL_MAC_DINH="ltt-3.8"` (đường máy B 3090),
  `MODEL_NOI_BO_MAC_DINH="ltt-3.5"` (5060 Ti).
- **Loop learning**: `learned_preferences` / `preference_engine` — grep trong
  `apps/taoclipngan` → **0 match**; manifest có node FEEDBACK nhưng chưa nối
  về ranker (xác nhận từ `_A` + grep độc lập).

## 5. Trạng thái các hạng mục H32 (audit 2026-08-11, chưa làm)

Từ `docs/APP_AUDIT/taoclipngan/2026-08-11-h32/07_IMPLEMENTATION_ROADMAP.md`:
Phase 0 (probe size/type trước queue, cancel qua 6 engine + FFmpeg tree,
matrix tier×count×aspect, WER VI/EN) · Phase 1 (prompt guided, transcript
trim, manual reframe, rerender revision, history) · Phase 2 (handoff
publish_bot, import YouTube, FCPXML, Quality Lab) — **cả 3 phase chưa triển khai**.
Plan next-gen này **gộp** H32 vào một roadmap thống nhất, không chạy song song.

## 6. Video test

`C:\Users\Thang Tuong\Desktop\TEST VIDEO` — 4 file: cooking (79 MB), camp (25 MB),
gaming (21 MB), airsoft (88 MB). Dùng cho nghiệm thu nội bộ, không commit vào repo.
