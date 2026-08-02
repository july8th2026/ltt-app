# Auto Sub ANALYZE evidence — 2026-08-02

- Reference inspected at original 1680×935; no generated image and no crop created.
- Browser fixture: `tools.upscale_browser_server` on isolated SQLite/storage; test
  user only. `/autosubvideo` desktop 1440×900 and mobile 390×844: overflow X=false,
  CTA visible, console 0, dynamic request `/estimate` 200.
- Current app inventory: 15 source/template files; `tests/test_81_autosubvideo.py`;
  route requires pre-existing transcript.
- Read-only `D:\BOT GEMINI` inventory: Auto Sub v3 API/UI/editor/template/preview/
  cancel/retry; no writes/imports. Normalizer/segmenter are equivalent aside from
  port/import/newline adjustments.
- Machine capability: RTX 5060 Ti 16311 MiB; FFmpeg 8.0.1 with libass/drawtext/
  NVENC; faster-whisper 1.2.1 + CTranslate2 4.7.1; cached tiny/base/small/medium/
  large-v3/turbo and PhoWhisper model families.
- Read-only video inventory under `G:\My Drive\AI\Tool AI\Video seedacne` found
  short H.264/AAC candidates (8–10 s, 864×496, 24 fps, stereo 44.1 kHz). Originals
  were not modified. Multi-speaker/long-form corpus remains required at AS0.
- External research used official/origin docs listed in `04_IMPLEMENTATION_PLAN.md`.

