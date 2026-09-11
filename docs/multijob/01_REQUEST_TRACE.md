# 01 — Request trace: từ cửa vào tới GPU và trở về (HIỆN TẠI, trước đa job)

> Đọc từ mã ở HEAD `9e73bf1f` (3 agent audit + đọc trực tiếp, 2026-09-11). Cột "Thiết kế đổi" trỏ về
> spec `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md`.

## Năm đường tới máy B

| # | Cửa | Điểm admission | Giữ tiền | Mở luồng / gọi | Hết suất ⇒ |
|---|---|---|---|---|---|
| 1 | ChatLTT stream (UI) | `platform_core/runtime_noi_bo/luong.py:202` `admission.acquire(resource="llm_remote", slots=1, mode="stream")` | `luong.py:227` `thanh_toan.giu_cho_luot` | `luong.py:285` `luong_vlm.mo` · giữ lease `luong.py:336` `keep_alive` | `DangBan(nguon="suat")` |
| 2 | Public API stream `/v1/messages`, `/v1/responses` | facade: `server/api/streaming.py:643` → `cua_luong.chuan_bi` (= đường 1) | như 1 | `streaming.py:646` `mo_thuong_nguon` → `StreamingResponse` `:706` + `BackgroundTask(release)` `:704` | `streaming.py:655` **429** `execution_busy` |
| 3 | Public API non-stream trong streaming.py | `server/api/streaming.py:215` | `streaming.py:226` | — | 429 |
| 4 | Public API sync `/v1/chat/completions` | `server/api/chat.py:188` | `chat.py:195` | `chat.py:227` `keep_alive` quanh lời gọi | 429 `execution_busy`, `Retry-After` 15 |
| 5 | Job `/v1/jobs` (text.chat) | `platform_core/job_runner.py:229` `admission.hold_persisted` | lúc submit (`job_submit.py:40-76`, cùng transaction với job) | `apps/ltt_llm/jobs.py:32` `features.chay` | **DEFER** `_tra_ve_hang_doi`, không tính attempt (`test_313:166-195`) |
| 6 | Planner nội bộ | `platform_core/agent/planner.py:144` | — (việc nội bộ) | `platform_core/llm/dieu_phoi.py` `goi()` | rơi sang Gemini (F-06, `test_389`) |

## Chặng chung sau khi được nhận

| Chặng | File:hàm | Hàng/khoá | Timeout | Retry | Hủy | Lỗi |
|---|---|---|---|---|---|---|
| Máy A → máy B | `platform_core/llm/luong_vlm.py:111 mo()` (stream) · `dieu_phoi._goi_openai` / `cong_vlm.chat` | lease `ExecutionLease` (CSDL) | `MO_LUONG_GIAY`; job: ngân sách job | không tự retry sau POST (`AmbiguousProviderError`) | stream: đóng generator ⇒ đóng httpx | 429 B ⇒ `ban=True`, **không** `danh_dau_loi` (`luong_vlm.py:154-172`) |
| Cổng máy B | `llm_gateway/api.py:339-434`: 413 ngân sách → 429 `GioiHan` (`gioi_han.py:219`) → 429 trọng tài (`trong_tai.py`) → 429 dọn card (`don_dep.py`) → chạy | `GioiHan` in-process `max_dong_thoi=1` (`config.py:136`, env `LTT_LLM_MAX_DONG_THOI`) | nhịp tim SSE 15 s (`nhip_tim.py`) | — | `upstream.close()` (`upstream.py:101-170`) ⇒ llama.cpp nhả ≤ 1 s | 5xx/599 ⇒ **502** (`api.py:491-506`) |
| llama-swap | `127.0.0.1:8280`, một model một lúc, không `groups` | — | `healthCheckTimeout 600` | — | — | đổi hồ sơ **giết lượt đang chạy** (đo 03/09) |
| llama-server | `--parallel 1`, `-c 204800` / `131072` (vision) | hàng deferred nội bộ theo số slot | — | — | CANCEL task khi ngắt kết nối | tràn KV ⇒ lỗi |

## Trở về + tiền

- Stream: `DemToken` đọc `usage` thật (INV-010) → `quyet_toan_luot` / `hoan_luot` (`platform_core/llm/thanh_toan.py`), idempotent theo `request_id` (INV-011/012); nhả lease ở `finally` + `BackgroundTask` (sự cố 31/08).
- Bận ở máy A (`nguon="suat"`) ⇒ **429**; bận ở máy B (thượng nguồn) ⇒ **503** + `Retry-After` (`streaming.py:674`), khách không bị thu (INV-003), đếm `CAPACITY_REFUSED`.
- Job: `_quyet_toan_credit` / `_hoan_credit` (`job_runner.py:556-697`); treo 6 h cảnh báo, 24 h tự hoàn.

## Thiết kế đổi gì trên trace này

Đường 1–2: tách `cua_luong.chuan_bi` — tiền kiểm (tham số, số dư) **trước 200**; **chờ + nhận + giữ tiền
sau 200, trong generator** (D-06). Đường 4: chờ trước header trong ngân sách thời gian (TD-7). Đường 5:
thêm hủy cứng (TD-9). Đường 6: không đổi (thử một lần, không chiếm slot chừa). Gateway: `max_dong_thoi = N`
+ sổ token đúng. llama-swap: một hồ sơ, không còn đổi hồ sơ.
