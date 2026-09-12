# 06 — Gap analysis: hiện tại → đích (P0 / P1 / P2)

| ID | Khoảng trống | Bằng chứng | Hạng | Thiết kế xử lý |
|---|---|---|---|---|
| **P0-PIN** | Máy B đã có 5060 Ti; llama-swap/dịch vụ không ghim GPU ⇒ lần nạp tới tự chia model sang 2 card, trái D-09a | `--list-devices`: CUDA0=3090, CUDA1=5060 Ti; không `CUDA_VISIBLE_DEVICES`/`-dev` ở `llm_gateway/**`, yaml máy B, env dịch vụ | **P0** | Pha 0: `env` UUID trong yaml đang chạy |
| **P0-KV** | Bật `-kvu` mà không admission ngân sách ⇒ một lần tràn giết mọi slot | `04` §2 (`server-context.cpp:3661-3708`); lab: HTTP 500 | **P0** (điều kiện trước N>1) | sổ ngân sách + chốt gateway (spec §5) |
| G-6 | Engine 1 slot ⇒ throughput tổng ~1 lượt; người thứ 4 chờ 34,6 s | M-1 | **P1** | N=4 `-kvu` (TD-4) |
| G-1 | Không có ưu tiên tương tác/nền | `jobs.py:219-220`; `mode` chỉ live/test | **P1** | D-03 A (chừa slot) |
| G-7 | Prompt dài đang prefill chặn người mới dù còn slot | M-1/M-2 | **P1** | D-05 (≤1 whale, nhường) |
| G-8 | Cửa stream bận ⇒ 429 ngay; không có chờ công bằng | `streaming.py:655` | **P1** | D-06 (phòng chờ + SSE) |
| G-9 | Đổi hồ sơ text↔vision giết lượt đang chạy (186 lần nạp/20 ngày; 100 lượt 502) | `catalog.py:26-29`; log máy B | **P1** | D-08 A (một hồ sơ) |
| G-2 | Hủy job không lan cứng xuống máy B | `job_runner.py:110-174` | **P1** | TD-9 |
| G-10 | Bốn chỗ cùng khai "1" không bắt khớp nhau đủ | C-02; `manifest.py:197` | **P1** | TD một nguồn `SO_SLOT_MAY_B` + `test_334` |
| G-11 | Không quan sát được "vì sao chưa chạy", engine có xếp hàng ẩn không | — | **P1** | TD-10 |
| G-4 | Quota tài khoản thô, không đếm luồng đồng thời | `limits.py:311-366` | **P2** → một phần P1 | TD-8 (trần khi có người chờ) |
| G-3 | Không preemption | llama.cpp không hỗ trợ an toàn | **không làm** | chừa slot thay thế |
| G-5 | `admission_slots` tĩnh | `invocation.py:472-487` | **P2** | tham số một nguồn; co giãn động chỉ khi telemetry đòi |
| G-12 | `--cache-ram` mặc định 8 GiB trong khi cache trúng 54 % | tải thật | **P2** | TD-11 |
| G-13 | Biên VRAM 374 MiB với hồ sơ gộp | M-2 | **P2** (đã chấp nhận) | TD-12 |
| U-1 | Upstream `5fdfa6282` sửa chuẩn hoá L2 lớp GDN của `qwen35.cpp` | `04` §9 | **P2 — ứng viên** | không trong đợt này; cần A/B chất lượng + lui |

Thứ tự bắt buộc: **P0-PIN** (độc lập) → control plane (P0-KV + G-1/7/8/2/10/11, vẫn N=1) → engine N=4
(G-6, G-9). Không làm P2 trước P0 (§44).
