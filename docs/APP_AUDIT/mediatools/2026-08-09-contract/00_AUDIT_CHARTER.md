# 00 — Audit charter: Media Tools runtime

- **Ngày/mode:** 2026-08-09 · DEEP runtime contract.
- **Surface:** không có app UI độc lập; customer dùng tool trong Agent Canvas.
- **Persona/JTBD:** customer đưa asset vào workflow, tạo audio, tách/ghép media,
  nhập video hợp pháp từ URL/social.
- **Môi trường:** local fixture/source/tests/browser; không tải social/provider thật.
- **Benchmark:** FLORA/PlenX content+transformation nodes, ComfyUI media nodes,
  n8n/Make file/HTTP transforms.
- **Trọng số:** giữ chuẩn LTT-AQA vì có AI TTS, credit, upload và network fetch.

**G0 PASS.** `/mediatools` redirect Agent; audit chức năng customer-visible qua
ToolSpec, không audit một màn hình độc lập.

