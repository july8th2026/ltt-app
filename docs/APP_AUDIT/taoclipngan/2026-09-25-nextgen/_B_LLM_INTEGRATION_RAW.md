# _B — LLM INTEGRATION (audit, chốt 25/09)

> Nguồn: subagent audit (closing message) + xác minh trực tiếp trên code bởi điều phối.

## Ba câu trả lời chốt

**(a) App mới gọi LLM qua cầu nối nào, tốn bao nhiêu công?**
→ Qua `platform_core/llm/` (`dieu_phoi.goi`, `cong_vlm`, `admission`). App khai
`model_llm_noi_bo` trong manifest (`apps/auto_scan_video/manifest.py:75` =
`"ltt-3.8"` — tiền lệ thật), nền tảng tự route qua `llm_gateway:8299`. Công sức
app: khai manifest 1–3 dòng + viết MỘT cổng gọi (pattern
`apps/auto_scan_video/ai.py:640-770` — xử lý lỗi, dispatch bền, timeout,
reasoning effort).

**(b) Có VLM không?**
→ **KHÔNG qua `ltt_llm`.** `qwen38-vision` đã bị gỡ ở D02/L-14; `ltt_llm` chỉ
còn hồ sơ `qwen38-api` (text-only).
- Xác minh: `apps/ltt_llm/manifest.py:65-66` ("hồ sơ thứ hai của cùng một
  model — `qwen38-vision`, đã gỡ ở D02/2.3. Từ dual-model, đọc ảnh là việc của
  …") và `llm_gateway/deploy/llama-swap.yaml:21-25`
  ("`qwen38-vision` KHÔNG còn tồn tại (D02; L-14 hệ quả 4). MỘT hồ sơ duy
  nhất…").
- VLM vẫn sống qua **render_gateway** (máy B) — app `anhnoibo` dùng
  (`apps/anhnoibo/jobs.py:96`), KHÔNG qua `ltt_llm`. Nối VLM render_gateway
  cho taoclipngan = một **cạnh app→app mới** (quyết định kiến trúc, AGENTS.md
  §8.3) — ngoài scope đợt này; plan dùng text-only enrich.
- ⚠️ Code `apps/auto_scan_video/hieu_canh.py:192-194` với `image_url`+`data:`
  là hợp đồng OpenAI đúng về mặt kỹ thuật (cong_vlm truyền nguyên xi) nhưng
  model VLM không còn phía sau — đọc như lịch sử.

**(c) Concurrency LLM cho thêm tải không?**
→ Có. `llama-swap.yaml`: `ltt-3.8` `-np 3` (RTX 3090), `ltt-3.5` `-np 4`
(RTX 5060 Ti) — **7 suất**, hai khoá advisory độc lập. Nguồn chân lý:
`apps/ltt_llm/ngan_sach.py::HO_SO` → `manifest.py::_khai_admission`.
Máy A quyết định, máy B rào vật lý (`docs/ltt_llm_dual/BAN_DO_DUONG_DI.md`
§1, §3).

## Điều kiện bắt buộc cho app (từ `auto_scan_video` + `dieu_phoi`)

1. **MỘT cổng gọi duy nhất** trong app; test chốt không file nào khác gọi
   `dieu_phoi.goi` trực tiếp (pattern `test_434`).
2. **Thứ tự lỗi** (`ai.py:740-769`): `BanError` (429 — chắc chắn, chưa chạy)
   phân loại TRƯỚC `AmbiguousProviderError` (mơ hồ — dừng bước, cho người
   quyết định). Bao `BanError` thành lỗi thường = hai sự cố đã diễn ra thật.
3. `ma_luot` = `<app>-<job>-<bước>` → hủy được theo tên, nối log hai máy.
4. `model_theo_provider` khai **id model thật** (vd `qwen38-api`), không bí
   danh app.
5. `response_format` JSON schema = grammar llama-server (ràng buộc cứng).
6. `timeout_s` chỉ khai khi thật sự khác mặc định — khai `None` xuống là giá
   trị không hợp lệ.
7. Lý do chọn model theo **tài nguyên, không phải tên** (`cong_vlm.py`
   docstring) — ltt-3.8/ltt-3.5 cùng "họ" ltt nhưng tài nguyên khác nhau.
