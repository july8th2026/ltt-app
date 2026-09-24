# Task 4 — `jsonschema` kiểm đầu ra

**Nguồn tra:** `pip show jsonschema` → 4.26.0, đã có sẵn trong môi trường
(phụ thuộc bắc cầu của `chromadb`) — dùng lại đúng luật "dùng lại trước, tự
viết sau", KHÔNG tự viết bộ kiểm. Khai tường minh vào
`requirements-server.txt` (phụ thuộc trực tiếp, không còn ẩn theo
`chromadb`). PyPI `jsonschema` hỗ trợ Draft 2020-12
(`jsonschema.validate`/`ValidationError`/`SchemaError`).

**Đỏ + Xanh:** cùng cặp với Task 3 (`ai_loi.py`/`test_2901`) —
`kiem_luoc_do(gia_tri, luoc_do)` gọi thẳng `jsonschema.validate`, bắt cả
`ValidationError` (dữ liệu sai) và `SchemaError` (chính lược đồ sai cú
pháp, `test_luoc_do_sai_cu_phap_bi_bao_loi_ro...`) — không để ngoại lệ thoát
ra ngoài. `dien_giai()` còn tự parse `content` bằng `json.loads` trước khi
kiểm (`test_content_khong_phai_json_voi_luoc_do_la_FAILED`: model bọc JSON
trong ```` ```json ```` — ca đã ghi ở `apps/ltt_llm/manifest.py:318`, "may B
tra dung khuon con qua may A thi khuon bi bo qua va JSON bi boc trong
```json"). `ai.extract` khai `ma_loi` chứa `dau_ra_sai_luoc_do`
(`test_2902::test_ai_extract_ma_loi_khai_dau_ra_sai_luoc_do`).

**Chưa làm được:** kiểm ở đây là lược đồ đầu RA (JSON Schema thật, Draft
2020-12) — KHÔNG liên quan `platform_core/workflow/luoc_do.py` (từ vựng
`params_schema` LTT cho THAM SỐ VÀO của node app, khác hệ). Không đụng tệp
đó, đúng phạm vi. GBNF/`response_format` gửi lên máy B (để ép model theo
đúng lược đồ ngay từ lúc sinh, giảm tỉ lệ rơi vào FAILED) là việc của bộ
dịch `tham_so ai.* -> params text.chat` — cùng khoảng trống compiler đã ghi
ở Task 1, chưa làm.
