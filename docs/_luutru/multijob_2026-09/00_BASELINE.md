# 00 — Baseline + phép đo M-1 trên máy B (2026-09-11)

> Đo thật trên máy B, RTX 3090 **một mình** (ghim bằng `CUDA_VISIBLE_DEVICES=<UUID 3090>`
> + `-dev CUDA0`; 5060 Ti đỉnh 54 MiB = không bị chạm). `llama-server` **b10689**
> (`57291f264`, đúng binary production `H:\LTT_LLM\bin\llamacpp`), cờ production
> (`--jinja`, template froggeric, `--reasoning-format deepseek`, `-fa 1 -ngl 999`,
> `draft-mtp n-max 2`, `-c 204800`, KV `q4_0`, `--metrics`) — **chỉ đổi `-np` / `-kvu`**.
> Server thí nghiệm cổng 8290, **không** đụng llama-swap/production.
>
> Dụng cụ + dữ liệu thô: `artifacts/m1/` (`m1_bench.py` throwaway, `ketqua.jsonl`,
> `tong_hop.py` để in lại bảng). Chạy dưới Scheduled Task SYSTEM + `pythonw`, 10:35–10:41
> giờ máy, không bị dừng giữa chừng (tiền kiểm: llama-swap `/running` rỗng, 3090 132 MiB).
> Ba phiên khác xác nhận không dùng máy B trong khung này.

## 1. Kết quả

| | **p1** (production hiện tại) | **p2 + `-kvu`** | **p4 + `-kvu`** |
|---|---:|---:|---:|
| Slot × ngữ cảnh mỗi slot | 1 × 204.800 | 2 × **204.800 (pool chung)** | 4 × **204.800 (pool chung)** |
| VRAM 3090 sau nạp | 21.619 MiB | 22.067 (+448) | **22.965 (+1.346)** |
| VRAM đỉnh cả lượt | 21.652 | 22.091 | 22.993 — còn ~1,6 GiB |
| **C1** decode | 59,9 tok/s | 60,1 | **62,7** |
| C1 spec-decode chấp nhận | 62 % | 64 % | 68 % |
| **C4 tổng** | 59,2 tok/s | 79,2 (**+34 %**) | **121,4 (+105 %)** |
| C4 mỗi luồng | 59–67 | 38–45 | 32 |
| C4 người xong cuối | **34,6 s** (9,0/17,8/25,8/34,6) | 25,9 s | **16,9 s** (cả 4 cùng xong) |
| Whale 60.017 token prefill | 60,2 s (998 tok/s) | 60,6 s | 62,2 s (966 tok/s) |
| **Minnow** TTFT khi whale đang prefill | **55,8 s** (chờ hết) | **54,9 s** (chờ hết!) | **5,2 s** |
| Minnow tốc độ **trong lúc** whale prefill | 0 token | 0 token | **1,4 tok/s** (75 token) |
| Minnow tốc độ sau whale | 66,6 | 46,6 | 46,3 |

## 2. Đọc kết quả — năm điều

1. **C4 VỪA trên 3090 một mình, với nguyên pool 200K.** Mỗi slot thêm tốn **~448 MiB**
   cố định (trạng thái recurrent GDN × 3 hàng do MTP — `04` §4), KV thì dùng chung pool
   đã cấp sẵn. ⇒ **đảo ngược** suy luận "C4 gần như chắc chắn không vừa" rút từ lab (lab
   dùng drafter DFlash2 là **một model riêng** ăn VRAM; `draft-mtp` dùng lớp nextn có sẵn).
2. **Bật slot KHÔNG làm chậm người dùng đơn lẻ.** C1 60–63 tok/s ở cả ba cấu hình;
   spec-decode vẫn chấp nhận 62–68 %. Chú thích "`--parallel 2` −20 %" trong
   `llama-swap.yaml:89-91` **không đúng trên máy này** (nguồn gốc là RTX 5090 / 2×5060 Ti — `05`).
3. **Throughput tổng gấp đôi ở C4**, và quan trọng hơn với người dùng: người thứ 4 xong
   ở **16,9 s thay vì 34,6 s**. Đổi lại mỗi luồng chậm còn ~32 tok/s khi đủ 4 người.
4. 🔴 **Prefill dài là nghẽn thật, và nhiều slot KHÔNG tự chữa được.** Khi một prompt
   60K đang prefill:
   - p1: người mới đợi **hết** prefill (~56 s);
   - p2: người mới **vẫn đợi hết** (~55 s) dù còn slot trống — engine lấp prompt theo
     **chỉ số slot**, whale ở slot thấp ăn trọn ngân sách prefill 2.048 token mỗi bước (`04` §6);
   - p4: người mới vào nhanh (5 s — tùy may rủi slot nào) nhưng **bò 1,4 tok/s** suốt ~53 s.
   ⇒ Với llama.cpp, "có slot trống" ≠ "được phục vụ". Chính sách cho prompt dài phải
   nằm ở tầng admission (quyết định D-05).
5. **Sau khi whale prefill xong, decode của nó rẻ**: minnow chạy lại ~46 tok/s bên cạnh.
   Chỗ đắt là **prefill**, không phải việc một phiên dài "nằm" trong pool.
   ⇒ "Whale" phải định nghĩa bằng **token cần prefill mới** (prompt − phần cache trúng),
   không bằng tổng ngữ cảnh — phiên agent 150K mà cache trúng 148K là một lượt **nhẹ**.

## 3. Tải THẬT 22/08 → 11/09 (log máy B, §34)

Nguồn: `H:\LTT_LLM\logs\llamaswap.log` (output `print_timing`/`release` của llama-server) và
`gateway.log` (access log uvicorn), phân tích **ngay trên máy B**, chỉ in số tổng hợp
(`artifacts/m1/phan_tich_log.py` → `phan_bo_tai.json`). 3.668 request hoàn tất.

| Đại lượng | p50 | p90 | p99 | max |
|---|---:|---:|---:|---:|
| Token prefill **mới** (sau cache) | 2.031 | 12.855 | 67.926 | 164.840 |
| Tổng ngữ cảnh lúc nhả | 16.627 | 51.921 | 113.155 | 164.988 |
| Token cache trúng | 1.054 | 41.247 | 79.941 | 152.464 |
| Token sinh ra | 1.910 | 13.715 | 19.880 | 26.842 |
| Prefill (s) | 2,35 | 11,0 | 73,1 | 740,8 |
| **Tổng mỗi lượt (s)** | **39,0** | **226,5** | 340,1 | 746,1 |

- Lượt có prefill mới vượt ngưỡng: >8K **816** (22 %), >16K **279** (7,6 %), >32K **155** (4,2 %),
  >64K **64** (1,7 %), >128K **10**. ⇒ ngưỡng whale khởi đầu đề xuất **16K** (7,6 % lượt).
- Ngữ cảnh >64K: **231** lượt (6,3 %) — những lượt tạo áp lực ngân sách KV.
- **54,1 %** tổng token ngữ cảnh là cache trúng ⇒ giữ cache phiên có giá trị lớn.
- Không lượt nào `truncated`. 186 lần llama-server khởi động; 21 lần nạp `mmproj` (vision).
- Cổng `/v1/*`: 200 = 3.228 · **429 = 453** (chat 372 · responses 78 · messages 3) · 502 = 109
  (responses 100) · 413 = 124. ⚠️ Chưa tách được lượt của khách với lượt đo đạc của các phiên
  trước — đọc 429 là **dấu hiệu** tranh chấp, không phải tỉ lệ khách bị từ chối.

Hệ quả thiết kế: **decode chiếm phần lớn thời gian** (p50 39 s/lượt, p90 ~4 phút) — đúng loại tải
mà nhiều slot gộp tốt (M-1: C4 ×2). Và `--cache-ram` mặc định 8.192 MiB là nút rẻ để giữ cache
phiên khi pool KV bị dồn (máy B có 128 GB RAM) — cần đo trong M-2.

## 4. Phép đo M-2 (13:38–13:45, cùng khuôn an toàn M-1)

Dụng cụ `artifacts/m1/m2_bench.py` (bản sao m1, giữ m1 nguyên trạng) → `ketqua_m2.jsonl`,
in lại bằng `tong_hop2.py`. Mọi cấu hình `-np 4 -kvu -c 204800`, ghim 3090.

### 4.1 Cỡ lô prefill (D-05) — whale 60K + 3 người mới đến lúc +6/+14/+22 s

| `-b` | Whale prefill | TTFT 3 người mới | Tốc độ họ **trong lúc** whale prefill | Sau whale (4 luồng) |
|---|---:|---|---|---:|
| 2048 (mặc định) | 63,1 s | 4,1 / 5,7 / 6,0 s | 1,5 / 1,5 / 1,6 tok/s | 29–30 |
| 1024 | 65,8 s (+4 %) | 2,6 / 2,4 / 2,8 s | 2,2 / 2,3 / 2,3 tok/s | 28–31 |
| 512 | 61,8 s | **56,6 / 49,0 / 41,0 s** (chờ hết!) | — | 31–32 |

Đọc đúng: **cỡ lô KHÔNG phải biến quyết định.** Hiệu ứng "người mới chờ hết prefill hay được vào
rồi bò" thay đổi **giữa các lượt cùng cấu hình** (M-1: p2 chờ hết, p4 được vào; M-2: b512 chờ hết,
b2048/b1024 được vào) — tức nó phụ thuộc **thứ tự slot** mà engine chọn, không phải `-b`. Và khi được
vào thì tốc độ trong lúc whale prefill **luôn** ở 1,5–2,3 tok/s. n = 1 mỗi ô.
⇒ Không nút engine nào cứu được trải nghiệm trong lúc whale prefill; **vế admission của D-05**
(≤1 whale, whale nhường lượt đang sinh chữ) mới là thứ chịu tải. Giữ `-b` mặc định; `-b 1024` là
ứng viên tinh chỉnh khi có telemetry nhiều lượt.

### 4.2 Hồ sơ GỘP text + vision (D-08) — thêm `--mmproj` vào hồ sơ 4 slot, pool 204.800

| | Số đo |
|---|---|
| Nạp | OK, 33,9 s · **VRAM 24.106 / 24.576 MiB** (hơn bản chỉ-text 22.988: +1.118) |
| VRAM đỉnh (1 ảnh + 3 luồng text đồng thời) | **24.202 MiB — còn 374 MiB** |
| C1 / C4 | 59,9 tok/s / 123,0 tok/s — không suy giảm |
| 1 ảnh 1024×768 (798 token prompt) | 200 trong 3,8 s; trả lời **đúng** ("hình tròn màu đỏ, bên trái") |
| 1 ảnh + 3 luồng text cùng lúc | ảnh 200 trong 5,8 s; text 33,6–36,1 tok/s |

⇒ Hồ sơ gộp **chạy được và đúng**, không bao giờ phải đổi hồ sơ (loại bỏ đường "llama-swap giết
lượt đang chạy" — 186 lần nạp/20 ngày). **Nhưng biên 374 MiB là mỏng** trên một máy để bàn đang
dùng (audit: 23 tiến trình trên card — Edge, Zalo, Riot Vanguard…). Pool nhỏ hơn (vd 163.840) sẽ
lấy lại biên — **chưa đo** (cấu hình dự phòng không chạy vì bản 204.800 đã nạp được).

## 5. Giới hạn của phép đo (đọc đúng phạm vi)

- n = 1 mỗi ô; không `--lan 5`. Đủ để chọn hướng, **không** đủ để đặt SLA.
- Prompt tổng hợp (từ vựng lặp) + `ignore_eos`; spec-decode trên văn bản thật có thể khác.
- Chưa đo: p3/p5/p6; hồ sơ **vision** (mmproj + ảnh) ở nhiều slot; pool gần đầy
  (lab thấy exception spec-decode khi KV gần đầy); `-b`/`-ub` nhỏ hơn để giảm đói prefill.
- `common_fit_params: failed to fit params … n_gpu_layers already set by user` là cảnh
  báo của tính năng tự khớp (bị bỏ qua vì đặt `-ngl 999`), không phải lỗi — cả ba đều nạp OK.
