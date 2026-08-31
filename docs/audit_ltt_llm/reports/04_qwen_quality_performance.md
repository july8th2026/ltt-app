# Prompt 04 — Qwen Quality & Performance

**31/08/2026, 20:45–21:20.** Ownership: D01–D38. Máy B rảnh.

**Kết quả một dòng:** chất lượng **12/12 (100 %)** trên bộ workload của LTT;
hiệu năng có mốc đo được lần đầu; và một **phát hiện P1**: trọng tài GPU
**nhận nhầm tải của chính ta thành tải của người khác**, khiến **75 % yêu cầu bị
từ chối ở lần thử đầu**.

---

## 1. Runtime fingerprint (D01–D06)

```
model      Qwen3.8-27B-UD-Q4_K_M.gguf  15,33 GB   (+ mmproj-F16.gguf 0,86 GB)
llama.cpp  0.3.0-dev build 10689 commit 57291f264  (Clang 20.1.8)
llama-swap v250 (60226b6) 2026-08-14
GPU        RTX 3090 24.576 MiB, driver 610.88
co         --jinja --reasoning-format deepseek -fa 1 -ngl 999 --parallel 1
           --spec-type draft-mtp --spec-draft-n-max 2
           -c 131072  --cache-type-k q8_0 --cache-type-v q8_0
ho so      qwen38-api  -c 131072 ttl 1800 | qwen38-vision -c 65536 ttl 600
```

---

## 2. 🆕 Bộ đánh giá chất lượng — thứ trước đây **không tồn tại**

`tools/danh_gia_llm.py`. Audit baseline chấm G5 **6/15** vì kho không có gì đo
chất lượng model. Nay có, và nó được thiết kế quanh ba ràng buộc thật:

**① Hai pha tách rời.** `--thu-thap` chạy trên máy B (gọi model, ghi đầu ra thô);
`--cham` chạy trên máy A. Vì chấm bài lập trình phải **chạy mã model sinh ra**,
và chạy mã sinh tự động trên máy đang phục vụ khách là rủi ro không cần thiết.
⭐ Được thêm một thứ: **chấm lại được mà không gọi model** — sửa cách chấm rồi
chạy lại là so **cùng một đầu ra**, không phải hai lần sinh khác nhau.

**② Không truyền `temperature`/`top_k`/`top_p`.** Chúng không nằm trong hợp đồng
công khai (cache CUDA graph khoá theo bộ tham số đó). ⛔ Truyền `temperature=0`
để "cho tất định" là đo một cấu hình **khách không bao giờ gặp**.

**③ Chấm bài lập trình bằng CHẠY THẬT**, không khớp chuỗi — khớp chuỗi cho điểm
một hàm *trông* đúng mà chạy sai.

### Kết quả: 12/12

| Bài | Nhóm | Kết quả | Trung vị |
|---|---|---|---:|
| vi-01, vi-02 | tiếng Việt | 2/2 | 2,8–3,1 s |
| en-01 | tiếng Anh | 1/1 | 1,9 s |
| code-01 | lập trình *(chạy 6 phép thử)* | 1/1 | 3,8 s |
| code-02 | sửa lỗi *(chạy 3 phép thử)* | 1/1 | 3,6 s |
| json-01 | JSON có cấu trúc | 1/1 | 2,7 s |
| ctx-10 / ctx-50 / ctx-90 | ngữ cảnh dài ~52K token | **3/3** | 74,9 / 77,0 / 77,9 s |
| dai-01 | sinh dài (40 dòng) | 1/1 | 10,2 s |
| tool-01, tool-02 | chọn tool + tham số | 2/2 | 2,9 s |

⭐ **Không có "lost in the middle".** Kim ở 10 %, 50 % và 90 % đều tìm ra, và ba
độ trễ gần như bằng nhau (74,9 / 77,0 / 77,9 s) ⇒ chi phí là **prefill**, không
phải vị trí.

⛔ `n=1` mỗi bài. Đây là **mốc**, không phải một phép đo có ý nghĩa thống kê.
Đủ để phát hiện hồi quy thô (một chiều tụt từ 100 % xuống 0 %), **không** đủ để
so hai cấu hình gần nhau. A/B thật cần `--lan 5` trở lên.

---

## 3. Hiệu năng (D30–D36)

Ngữ cảnh phép đo — bắt buộc kèm, vì máy B là một máy để bàn đang dùng:

```
truoc: VRAM 22.433 MiB, GPU 0 %, 37 °C, 25 tien trinh tren card
sau  : VRAM 22.433 MiB, GPU 40 %, 60 °C, 25 tien trinh tren card
```

| Loại | n | TTFT tv | Tổng tv | Decode tv |
|---|---:|---:|---:|---:|
| nguội *(chưa có cache tiền tố)* | 1 | 1,44 s | 4,53 s | 65,0 tok/s |
| ấm, 200 token | 5 | **1,26 s** | 4,36 s | **63,3 tok/s** |
| ấm, 900 token | 2 | 1,33 s | 17,20 s | 57,0 tok/s |
| ngữ cảnh 52K token | 3 | — | **~77 s** | — |

⭐ **63,3 tok/s trùng khít con số lịch sử.** Ghi chép P6/D-005 đo *"card sạch
(sau `/free`) → **63,3 tok/s**"* so với *"card bẩn → 18,2 tok/s"*. Hai phép đo
độc lập, cách nhau nhiều ngày, cùng một số ⇒ runtime đang ở trạng thái **sạch**
và ổn định.

⚠️ **`token_ra` là ƯỚC LƯỢNG**, đánh dấu `token_ra_la_uoc: true` trong artifact.

🔴 **SỬA 31/08 sau Prompt 02 — tôi viết sai nguyên nhân.** Bản đầu ghi *"thượng
nguồn **không gửi** `usage` trong luồng SSE"*, như thể đó là một thiếu sót của
nền tảng. **Không phải.** Tôi gọi cửa `/v1/chat/completions` mà **không xin
`stream_options.include_usage`** — kiểu OpenAI chỉ gửi `usage` khi được xin.

Ba cửa thật của nền tảng **có** nhận được, và có bằng chứng sống trong nhật ký
production: `STREAM XONG khoi=64 token_ra=67` — `token_ra ≠ khoi` ⇒ đó là
`usage` thật chứ không phải phép đếm khối.

⇒ `decode_tok_s` ở đây là **ước**, và nó ước vì **bộ đo của tôi thiếu một tham
số**, không vì hệ thống thiếu dữ liệu. Xem `reports/02` §1.

VRAM **không đổi** qua toàn bộ phép đo (22.433 MiB) ⇒ không rò bộ nhớ trong
vòng đời một hồ sơ.

---

## 4. 🔴 Phát hiện P1 — trọng tài nhận nhầm tải của CHÍNH TA

Lý do 429 nguyên văn, lấy từ artifact:

```
"may B dang ban": "co tien trinh python tren card va tai GPU 89% (>= 50%)
                   — dang ve, nap model bay gio se de len nhau"
```

**Cơ chế.** `trong_tai.phan_xu()` có nhánh: *1 python trên card **và** tải GPU
≥ 50 % ⇒ BẬN*. Ý định đúng và được ghi rõ: phân biệt **ComfyUI ngồi im** (0–1 %)
với **ComfyUI đang vẽ**. Nhưng:

* `llama-server.exe` **không phải python** ⇒ không bị đếm;
* tải 89 % lúc đó là của **chính `llama-server` của ta** đang sinh chữ;
* ComfyUI im, và nó là cái python duy nhất được đếm.

⇒ **Tải của ta bị quy cho ComfyUI.**

**Đo được, hai lần độc lập:**

| Lượt chạy | Bị 429 ở lần thử đầu |
|---|---|
| bộ đánh giá chất lượng | **9 / 12** |
| bộ đo hiệu năng | **5 / 8** |
| **cộng** | **14 / 20 = 70 %** |

Mọi lượt đều **thành công khi thử lại**. Tức máy khoẻ, model sẵn sàng, và cổng
vẫn từ chối — vì nó thấy tải do **chính nó** tạo ra.

🔴 **Hệ quả với khách thật:** một client tuần tự (Codex, Claude Code — hỏi, đọc,
hỏi tiếp) sẽ ngẫu nhiên nhận **503 "model is busy"** vì GPU còn nóng từ **lượt
trước của chính họ**. Khách không phân biệt được điều này với "máy B bận thật".

⭐ Và nó nối vào sự cố 31/08: đó là **nguồn thứ hai** sinh ra 503-giả. Nguồn thứ
nhất (suất bị rò) đã vá sáng nay; nguồn này thì chưa ai nhìn thấy.

### Phương án, và vì sao chọn cái nào

| | Phương án | Đánh giá |
|---|---|---|
| a | Bỏ qua nhánh tải khi **model của ta đang chạy** — dùng lại `_co_model_cua_ta_dang_chay()` đã có sẵn | **CHỌN.** Đúng ý định gốc: nhánh này sinh ra để tránh **nạp model** đè lên việc người khác; model đã nạp rồi thì không có gì để đè |
| b | Quy tải theo tiến trình | **BÁC.** `used_memory` là `[N/A]` cho mọi tiến trình trên cấu hình này; per-process utilization cũng không có |
| c | Nâng ngưỡng tải | **BÁC.** Tải của ta là 89–100 %; không có ngưỡng nào tách được |
| d | Bỏ hẳn nhánh tải | **BÁC.** Mất khả năng phát hiện ComfyUI đang vẽ thật — đúng cái nó sinh ra để bắt |

**Rủi ro của (a), nói thẳng:** nếu model của ta đã nạp **và** ComfyUI bắt đầu vẽ,
ta sẽ không còn từ chối. Hai workload cùng card. Nhưng: `--reserve-vram 3` đã
có, VRAM của ta ổn định 22,4 GB, và `don_dep` vẫn giữ nhánh riêng của nó. Đổi
lại là **chấm dứt 70 % lượt từ chối oan**.

⇒ **Quyết định: `CHANGE`, chủ sở hữu Prompt 06.** Không sửa ở đây: phase này sở
hữu D01–D38, còn trọng tài là C16–C21. Gói cấm gom nhiều thay đổi vào một phase,
và đây là một thay đổi trên **đường điều phối GPU của một máy đang phục vụ**.

---

## 5. Song song / backpressure (D29) — **KEEP**

`--parallel 1` ở llama-server, `max_dong_thoi = 1` ở cổng. Đo ở Prompt 03: lượt
thứ hai bị từ chối **0,05 s** kèm `Retry-After: 15`.

⛔ Không đề xuất nâng lên 2. `llama-server` chạy `--parallel 1`; nâng số ở cổng
mà không nâng ở engine chỉ tạo **hàng đợi ẩn** — đúng thứ `gioi_han.py` sinh ra
để tránh. Và nâng ở engine trên một card 24 GB đang ở 22,4 GB là mời OOM.

---

## 6. Ngữ cảnh (D27, D17, D18) — **KEEP**

52K token → ~77 s, và **không lệch theo vị trí kim**. Engine `-c 131072`, cổng
cưỡng chế 96.256, công bố cho khách 88.555 — ba số cho ba việc, đúng phân biệt
mà `OPERATING_CONTRACT §10` đòi.

⛔ **Không** công bố 131.072 cho khách. Một client nhồi 131K sẽ nhận 413.

---

## 7. Upstream (D38) — **DEFER, có lý do cụ thể**

| | Đang dùng | Mới nhất | Chênh |
|---|---|---|---|
| llama.cpp | b10689 | **b10717** | 28 commit |
| llama-swap | v250 | **v251** | 1 bản |

**6/28 commit chạm cấu hình của ta**, đáng chú ý:

* `spec : fuse the DFlash encoder into the KV cache injection (#27310)` — ta dùng
  `--spec-type draft-mtp`
* `kv-cells: stop the sequence scan once all sequences are seen (#28011)`
* `vulkan: top_k radix select for k >= 1024 for Qwen 3.8 Flash Next (#28032)`
  *(Vulkan — ta dùng CUDA, không áp)*

⛔ **Không nâng cấp.** `OPERATING_CONTRACT §5` cấm CHANGE chỉ vì upstream có bản
mới, và §7 đòi *reproducible benchmark + compatibility + rollback + quality
parity*. Ba trong bốn thứ đó **vừa mới tồn tại từ hôm nay**.

⭐ Nhưng nay nâng cấp **đánh giá được**: chạy `danh_gia_llm.py --lan 5` +
`bench_llm_hieu_nang.py` trước và sau, trên cùng bộ đề. Trước hôm nay thì không
có cách nào nói "bản mới có tốt hơn không" ngoài cảm giác.

**Việc còn nợ trước khi cân nhắc nâng cấp:** một mốc `--lan 5` (hiện mới `n=1`),
và một đường rollback đã thử (giữ binary cũ, đổi lại được).

---

## 8. Bảng quyết định

| ID | Ứng viên | Quyết định | Vì sao |
|---|---|---|---|
| D-04-1 | Bộ đánh giá chất lượng | **CHANGE (thêm mới)** | G5 không có chủ sở hữu; nay đo được 8 chiều |
| D-04-2 | Trọng tài quy tải của ta thành của người khác | **CHANGE → 06** | 70 % lượt bị từ chối oan, đo hai lần độc lập |
| D-04-3 | `--parallel 1` / `max_dong_thoi 1` | **KEEP** | Nâng ở cổng mà không ở engine = hàng đợi ẩn; nâng ở engine = OOM |
| D-04-4 | `--spec-type draft-mtp` | **KEEP (chưa A/B)** | 63,3 tok/s khớp mốc lịch sử; chưa có cơ sở đổi |
| D-04-5 | KV cache `q8_0` | **KEEP** | VRAM ổn định 22,4 GB, ngữ cảnh 52K chạy được |
| D-04-6 | Nâng llama.cpp b10689→b10717 | **DEFER** | Thiếu mốc `--lan 5` và đường rollback đã thử |
| D-04-7 | Không phơi `temperature`/`top_k` | **KEEP** | Cache CUDA graph khoá theo chúng |
| D-04-8 | Thượng nguồn không gửi `usage` trong SSE | **DEFER → 05** | Làm decode tok/s thành ước; thuộc hợp đồng giao thức |

---

## 9. Điểm sau Prompt 04

| Chiều | Trước | Sau | Vì sao |
|---|---:|---:|---|
| Model quality & tool/context fidelity | 6 | **12** | 12/12 trên 8 chiều, chấm bằng chạy thật; trừ 3 vì `n=1` và chưa đo vision |
| Performance/resource efficiency | 7 | **11** | có mốc TTFT/decode/e2e/VRAM, khớp số lịch sử; trừ vì `usage` phải ước |
| Tests/evidence/reproducibility | 4 | **5** | bộ đề ổn định, artifact tái chấm được |
| Correctness & invariants | 16 | **15** | −1: trọng tài từ chối oan 70 % là một lỗi đúng đắn, không phải chỉ hiệu năng |
| **TỔNG** | 71 | **78** | |

---

## 10. Còn nợ

* **Vision (D20)** — `qwen38-vision` chưa có bài nào. Nó **đang được bán** trong
  danh mục ⇒ phải đo trước khi tuyên bố G5 đủ.
* **`--lan 5`** cho A/B thật.
* **Nhiều bước tool** (D14) — mới đo chọn tool + tham số, chưa đo vòng lặp
  tool → kết quả → tool tiếp.
