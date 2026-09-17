# Nghiệm thu phương án C trên production — 17/09/2026 (23:34–23:49, UTC+7)

> Bản ghi có ngày — đừng sửa số về sau. Kế hoạch: `KE_HOACH_PHUONG_AN_C.md` §5.1; luật: `DECISION_LOG.md` L-23.
> Bản chạy: máy A `575798a7` (deploy 23:29), cổng máy B phương án C bước 3 (23:03, `/health` đọc
> `H:\LTT_LLM\gateway\llama-swap.yaml`: 3.8 `-c 221184 -np 3`, 3.5 `-c 262144 -np 3`, `kvu` bật).
> Đường đo: `https://app.lttstudios.com/api/v1/messages` stream, khoá thử `khach3.thu`,
> `reasoning_effort=low`. Chỉ đọc mã/CSDL/log; không đổi cấu hình, không restart.

## 0. Kết luận

| # | hạng mục | kết quả | số |
|---|---|---|---|
| 1 | lượt nhỏ chạy; `X-LTT-Token-Dat` tới B = lease A | **PASS** | 18/18 lượt: `token_dat` ở B `/health` đúng bằng `llm_waiters.token_dat_truoc` (vd 3.092, 62.560, 104.997, 125.478, 203.072); lượt nhỏ 3.8 TTFT 1,9 s · 60 tok/s; 3.5 TTFT 1,5 s · 77 tok/s |
| 2a | whale xếp hàng, lượt nhỏ được nhận cạnh whale | **PASS** | S nhận sau 3 ms (`dat` 3.084, B `dang_chay` 2 / 65.644) trong khi W2 chờ `whale_nhuong` |
| 2b | **chỉ một whale prefill mỗi lúc** | **FAIL** | cờ whale bị xoá ở nhịp tim 15 s của B, không phải lúc prefill xong ⇒ whale thứ hai được nhận khi whale đầu còn prefill (3.8: chồng 24,9 s) — xem §2 |
| 2c | ngưỡng whale theo model (8.192 / 16.384) | **PASS** | 3.8 ước 7.000 ⇒ `la_whale=f`, 10.002 ⇒ `t`; 3.5 ước 14.000 ⇒ `f`, 18.001 ⇒ `t` |
| 3 | vượt ngân sách (pool = `-c` − 8.192) ⇒ chờ, không 429, vào khi có chỗ | **PASS** | 3.8: 104.997 + 104.996 đang chạy, S3 8.072 (tổng 218.065 > 212.992) ⇒ `cho_ngan_sach` 174,5 s, nhận 0,26 s sau khi B1 nhả. 3.5: 125.478 + 125.476 + 8.072 = 259.026 > 253.952 ⇒ chờ 128 s, nhận 0,41 s sau khi B1 nhả. B `tu_choi` = 0, đỉnh `token_dat` 209.993 / 221.184 và 250.954 / 262.144 |
| 4 | quá trần ⇒ 413 rõ ràng trước 200 | **PASS** | 3.8 ước 190.000 ⇒ 413 sau 0,84 s, `limit_value` 186.368, `retry: never`; 3.5 ước 230.001 ⇒ 413, `limit_value` 227.328. 0 bút toán, B `qua_tran` = 0 (A chặn trước). 3.5 ước 200.000 (thật 99.003) ⇒ 200, xong (O-02 đã đóng) |
| 5 | không luồng nào chết vì tràn KV | **PASS** | 18/18 luồng có `stop_reason` (`end_turn`/`max_tokens`), 0 khối `error`; A log 18 × `STREAM XONG`, 0 `STREAM LOI`; `llamaswap.log` + `llamaswap_err.log` máy B: 0 dòng `failed to find free space` / `context shift` / `KV cache is full` / `decode: failed` |
| 6 | tiền: mỗi lượt đúng một hold + một settle/refund | **PASS** | 18 `request_id` ⇒ 18 × (`hold`, `settle`), 0 lệch khuôn, khớp 18/18 dòng `llm_waiters`; hai lượt 413 không ghi bút toán |
| 7 | A xếp lại khi B 429 (`XEP LAI` / `llm:xep_lai`) | **KHÔNG QUAN SÁT** | B không 429 lần nào (`tu_choi` 0 suốt các phép) ⇒ không có khe để quan sát; không ép bằng cấu hình (theo yêu cầu) |

Tiền đã tiêu: **15 credit** (5.000 → 4.985). Không có khách khác trên LTT LLM trong cửa sổ đo
(`llm_waiters` 3 giờ trước chỉ có tài khoản thử; B `dang_chay` 0 trước mỗi phép).

## 1. Số đo từng lượt

Ước = `features.uoc_token_vao` của máy A (2,5 ký tự/token); vào = `usage.input_tokens` thật. Văn bản
đệm ~5 ký tự/token thật ⇒ ước ≈ 2 × thật (hướng an toàn). TTFT tính từ lúc gửi (gồm cả chờ hàng);
tok/s = token ra / (xong − delta đầu), nên gồm cả khựng do prefill của người khác.

| phép | lượt | model | ước vào | vào thật | ra | chờ hàng (s) | TTFT (s) | tok/s | ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| S1 | nhỏ | 3.8 | 20 | 4 | 171 | 0,00 | 1,92 | 60,3 | |
| S1 | nhỏ | 3.5 | 20 | 26 | 1.024 | 0,00 | 1,52 | 77,1 | |
| S1 | 7K | 3.8 | 7.000 | 3.513 | 256 | 0,00 | 4,78 | 69,9 | không whale |
| S1 | 10K | 3.8 | 10.002 | 5.102 | 215 | 0,00 | 6,34 | 56,4 | whale |
| S1 | 14K | 3.5 | 14.000 | 7.009 | 256 | 0,00 | 4,48 | 74,1 | không whale |
| S1 | 18K | 3.5 | 18.001 | 9.009 | 256 | 0,00 | 5,68 | 69,7 | whale |
| S2 | W1 | 3.8 | 60.000 | 29.832 | 166 | 0,07 | 29,60 | 46,4 | prefill ~1.050 tok/s |
| S2 | W2 (+3 s) | 3.8 | 60.001 | 29.811 | 469 | 29,85 `whale_nhuong` | 58,55 | 48,9 | nhận ở tuổi 30 s (hết `cho_whale_toi_da_s`), 0,27 s sau W1 xong — trùng hợp |
| S2 | S (+6 s) | 3.8 | 12 | 61 | 64 | 0,00 | 8,21 | **3,9** | decode gần như dừng trong prefill 30K của W1 |
| S3 | B1 | 3.8 | 99.949 | 49.567 | 3.000 | 0,00 | 57,52 | 19,8 | |
| S3 | B2 (+2 s) | 3.8 | 99.948 | 49.689 | 3.000 | 30,1 `whale_nhuong` | 121,08 | 30,4 | **nhận khi B1 còn prefill** |
| S3 | S3 | 3.8 | 5.000 | 2.575 | 1.024 | 174,5 `cho_ngan_sach` | 182,54 (7,5 sau khi nhận) | 45,4 | nhận 0,26 s sau B1 nhả |
| S3 | B1 | 3.5 | 120.430 | 59.725 | 3.000 | 0,01 | 34,34 | 23,6 | prefill ~1.740 tok/s |
| S3 | B2 (+2 s) | 3.5 | 120.428 | 59.815 | 3.000 | 30,4 `whale_nhuong` | 80,38 | 37,3 | nhận 1,4 s trước B1 hết prefill |
| S3 | S3 | 3.5 | 5.000 | 2.533 | 1.024 | 128,0 `cho_ngan_sach` | 133,96 (5,6 sau khi nhận) | 71,5 | nhận 0,41 s sau B1 nhả |
| S4 | 190K | 3.8 | 190.000 | — | — | — | 413 sau 0,84 | — | `limit_value` 186.368 |
| S4 | 230K | 3.5 | 230.001 | — | — | — | 413 sau 0,63 | — | `limit_value` 227.328 |
| S4 | 200K | 3.5 | 200.000 | 99.003 | 1.024 | 0,00 | 63,59 | 39,0 | `dat` 203.072 ≤ 253.952 |

## 2. Lỗi: cờ whale bị xoá bởi nhịp tim của máy B, không phải lúc prefill xong

**Triệu chứng.** Luật "≤ 1 whale đang prefill mỗi model" (L-23) không giữ khi prefill > ~30 s.
Phép S3 3.8: B1 (49.567 token thật) nhận 23:39:18,264, **delta nội dung đầu 23:40:15,006**;
B2 (whale) nhận **23:39:50,140** ⇒ hai whale prefill chồng nhau 24,9 s. B `/health` xác nhận:
23:39:52 `dang_chay` 2, `token_dat` 209.993.

**Nguyên nhân (đọc mã, khớp log).** `platform_core/runtime_noi_bo/luong.py::_phat` gọi
`admission.xoa_co_whale(cb.lease_id)` ở **khối byte đầu tiên** từ máy B. Nhưng cổng B
(`llm_gateway/nhip_tim.py`, `LTT_LLM_NHIP_TIM_S` 15 s) chèn dòng chú thích SSE vào khoảng lặng
prefill ⇒ "byte đầu" = nhịp tim 15 s. Bằng chứng log `C:\LTTPlatform\logs\ltt-server.jsonl`: mọi lượt
whale đều ghi `ttfb=15.0s` dù TTFT nội dung thật là 29,6 / 57,5 / 34,3 / 63,6 s:

```
STREAM XONG rid=fc34dacf dur=206.3s ttfb=15.0s khoi=3000 token_ra=3000   (3.8 B1, TTFT thật 57,5 s)
STREAM XONG rid=c08f888d dur=87.5s ttfb=15.0s khoi=1029 token_ra=1024    (3.5 200K, TTFT thật 63,6 s)
```

Header 200 tới client cũng về ở ~15–17 s (`header_s` 17,65 / 15,84), đúng nhịp đầu của B.
Sau khi cờ tắt ở ~15 s, whale sau chỉ còn bị giữ bởi `yc.tuoi_s < cho_whale_toi_da_s` (30 s, env
mặc định) ⇒ được nhận ở tuổi 30 s. Trong S2 (prefill W1 29,6 s) lỗi bị che vì W1 xong đúng lúc W2
tròn 30 s.

**Hệ quả.** Không tràn KV (ngân sách vẫn giữ), nhưng hai prefill lớn cùng chạy làm chậm cả hai và
bỏ đói decode của người khác (B1 3.8 còn 19,8 tok/s; lượt nhỏ trong prefill 30K chỉ 3,9 tok/s).
Mọi whale có prefill > 15 s đều mất cờ sớm — tức gần như mọi whale 3.8 trên ~15K token thật.

**Hướng sửa (chưa làm — phiên này chỉ đọc).** Xoá cờ ở khối **dữ liệu** đầu tiên (bỏ qua dòng bắt
đầu bằng `:`), hoặc để `DemToken.nhin` báo sự kiện nội dung đầu; thêm phép kiểm với B giả phát
nhịp `: ...` trước khối `data:`.

## 3. Ghi chú phụ (không phải lỗi của C)

- **"Đặt chỗ vượt ngân sách ⇒ 413"** chỉ chạm được qua trần vào: `tran_token_ra` kẹp đầu ra theo
  pool nên lượt chữ không ảnh nào qua được trần vào mà đặt chỗ > pool. Đã kiểm trần vào (413 cả hai
  model); nhánh `DatChoVuotPool` (ảnh làm vượt) không đo trên production.
- Lượt nhỏ chen cạnh một prefill 30K trên 3.8: TTFT 8,2 s, decode 3,9 tok/s — đúng lo ngại m3
  (`-b/-ub` mặc định), nằm ngoài phạm vi C.
- Ước vào của A ≈ 2 × token thật với văn bản chữ Latin thường ⇒ pool thực dùng khoảng một nửa số
  đặt chỗ; an toàn nhưng xếp hàng sớm hơn cần (S3 chờ 128–175 s trong khi KV thật còn trống).
- Mục 7 (xếp lại sau B 429) cần một khe nhả thật; lần sau nên quan sát trong giờ có tải.

## 4. Tái lập

Kịch bản trong scratchpad phiên (không commit): `nt_c/kh.py` (client SSE, khoá đọc trong tiến
trình), `kb.py` (dựng prompt theo ước của A), `s1.py`…`s4.py`, `b_health.py` (thăm `/health` B mỗi
0,2–0,25 s qua `chay_voi_may_b.py`), `db_doc.py` (SELECT `llm_waiters`, `credit_entries`).

## 5. Đo lại 2b sau bản sửa — 18/09/2026 00:23–00:29 (máy A `26ed94e5`, deploy 00:22)

Bản sửa: cờ whale chỉ xoá ở khối SSE có dữ liệu thật, không ở dòng `: ping` của B. Kịch bản
`s5.py`: W1 whale, W2 whale gửi sau 3 s, S nhỏ gửi sau 6 s; `max_tokens` 1.500 để W1 còn decode
khi W2 được nhận. Trước phép đo không có khách trên LTT LLM (B `dang_chay` 0).

| model | W1 vào thật | W1 nội dung đầu (client) | W1 `ttfb` log A | W2 nhận (`llm_waiters`) | W2 chờ | S nhận |
|---|---|---|---|---|---|---|
| 3.8 (ước 100.002, đặt 103.550) | 49.757 | 00:24:01,282 (TTFT 53,6 s) | **49,7 s** (trước: 15,0) | 00:24:01,718 (**+0,44 s**) | 50,4 s `whale_nhuong` | sau 9 ms, `dat` 3.084 |
| 3.5 (ước 120.001, đặt 123.549) | 59.606 | 00:27:06,798 (TTFT 47,9 s) | **33,5 s** | 00:27:06,839 (**+0,04 s**) | 44,3 s `whale_nhuong` | sau 6 ms, `dat` 3.084 |

**2b: PASS cả hai model — theo tiêu chí "nhận sau nội dung thật đầu tiên của W1"**, không phải theo
trần chờ 30 s: W2 đã quá 30 s tuổi (50,4 s / 44,3 s) mà vẫn chờ tới khi W1 có dữ liệu thật. B
`/health` xác nhận: 3.8 lên `dang_chay` 3 / 210.183 lúc 00:24:04; 3.5 lên 3 / 250.183 lúc 00:27:08 —
không có lúc nào hai whale cùng prefill. `ttfb` trong `ltt-server.jsonl` nay là thời điểm dữ liệu
thật (3.8: t0 A 00:23:11,56 + 49,7 s = 00:24:01,26 ≈ client 01,282). W2 TTFT: 3.8 122,9 s; 3.5 93,9 s.

Còn lại (ngoài phạm vi C, như §3): lượt nhỏ chen cạnh prefill 50K trên 3.8 decode **1,6 tok/s**
(178 token trong ~112 s), 3.5 **9,1 tok/s** — khựng decode trong prefill lớn (m3, `-b/-ub`).

Tiền: 6 lượt ⇒ 6 × (`hold`, `settle`), tiêu 8 credit (4.985 → 4.977). B `tu_choi` 0, 6/6 luồng kết
thúc `end_turn`/`max_tokens`, 0 khối lỗi.
