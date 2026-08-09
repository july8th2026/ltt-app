# 00 — Audit charter: Kịch bản runtime

- **Ngày/mode:** 2026-08-09 · DEEP runtime contract.
- **Trạng thái:** UI Kịch bản YouTube đã retired; `/kichban` phải chuyển Agent.
- **Persona:** customer dùng node Text trong Agent; operator duy trì legacy
  job/project để không mất dữ liệu.
- **JTBD:** generate text từ prompt; phân tích text/image/video; giữ kết quả và
  chi phí đúng modality.
- **Môi trường:** local fixture, source/tests/browser; không gọi Gemini thật.
- **Benchmark:** FLORA/PlenX text node, multimodal LLM node, ComfyUI/n8n AI node.

**G0 PASS.** Không audit UI legacy như một customer app mới.

