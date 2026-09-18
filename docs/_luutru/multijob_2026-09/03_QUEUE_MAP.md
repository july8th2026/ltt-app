# 03 — Bản đồ mọi chỗ một request có thể CHỜ

> Mục tiêu (§19): mỗi làn tài nguyên chỉ có **MỘT hàng nghiệp vụ có thẩm quyền**; mọi chỗ chờ khác
> hoặc bị bỏ, hoặc bị chặn trên, hoặc được quan sát.

## Hiện tại

| # | Chỗ chờ | Loại | Có thẩm quyền? | Quan sát được? |
|---|---|---|---|---|
| Q1 | Bảng `jobs` (`queued`, `next_run_at`) | hàng nghiệp vụ bền, fair-share + aging (`jobs.py:185-224`) | **CÓ** (cho việc nền) | `/ops/jobs-metrics` |
| Q2 | Client tự retry sau 429 (`Retry-After` 15) | chờ **ngoài** hệ thống | không — cuộc đua retry, không thứ tự | chỉ đếm 429 |
| Q3 | `GioiHan` gateway | **không chờ** — 429 trong 0,05 s (D-03-2) | — | `/health` |
| Q4 | llama-swap chờ nạp model (`healthCheckTimeout 600`) | chờ khởi động | không | log |
| Q5 | llama-server hàng **deferred** (theo số slot) | hàng **ẩn** của engine | không | `/metrics requests_deferred` (cần `--metrics`, nay đã bật trên máy B) |
| Q6 | Prefill chung trong engine (lô 2.048/bước, theo chỉ số slot) | nghẽn trong engine | không | chỉ thấy qua TTFT |

## Sau thiết kế

| # | Chỗ chờ | Thẩm quyền | Chặn trên |
|---|---|---|---|
| Q1 | `jobs` — việc nền | **CÓ** | trần global/resource/account (giữ) |
| Q1' | `llm_waiters` — phòng chờ cửa tương tác (mới) | **CÓ** — cùng luật nhận với Q1 trong một hàm | `SO_NGUOI_CHO_TOI_DA`, `TOKEN_PREFILL_CHO_TOI_DA`, `CHO_STREAM_TOI_DA` |
| Q2 | Retry của client | thu nhỏ: chỉ khi phòng chờ đầy (429 trước 200) hoặc cửa sync hết ngân sách thời gian | — |
| Q3 | Gateway | vẫn **không chờ** | — |
| Q4 | Nạp model | hiếm hơn: một hồ sơ, `ttl` dài | — |
| Q5 | Deferred của engine | **phải luôn = 0** (máy A + gateway không bao giờ nhận quá N) — báo động nếu > 0 | TD-10 |
| Q6 | Prefill trong engine | điều khiển gián tiếp bằng luật whale (≤1 whale, nhường tương tác) | D-05 |

Q1 và Q1' là **một** mặt phẳng admission: cùng sổ `ExecutionLease`, cùng advisory lock, cùng luật công
bằng — hai "cửa vào" của một hàng, không phải hai hàng. Việc nền không có dòng trong Q1' (hàng bền của
nó là Q1); cửa tương tác không tạo job ngầm (hợp đồng H41.9).
