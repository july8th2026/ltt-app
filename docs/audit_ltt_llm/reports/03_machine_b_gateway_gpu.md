# Prompt 03 — Machine B Gateway, GPU Control & Runtime Lifecycle

**31/08/2026, 20:14–20:30.** Ownership: C01–C28.
Máy B **rảnh hoàn toàn** trong suốt phép đo (chủ sản phẩm xác nhận) ⇒ đo được
thật, không phải suy từ mã.

Mọi số dưới đây là `OBSERVED` trên runtime thật qua Nexus, trừ chỗ ghi rõ khác.

---

## 1. Ranh giới cổng (C01–C05, C11–C13) — **VERIFIED-KEEP**

| Phép thử | Kết quả đo | Verdict |
|---|---|---|
| `GET /live` không khoá | `200` 0,05 s — chỉ `{ok, version}` | KEEP |
| `GET /health` không khoá | **401** 0,02 s | KEEP |
| `GET /health` khoá **sai** | **401** 0 s | KEEP |
| `POST /v1/responses` khoá sai | **401** 0 s — **không chạm GPU** | KEEP |
| model `gpt-4o` / `llama-3` / `qwen38-api-x` / rỗng | **404** cả bốn, ≤0,01 s | KEEP — fail-closed |
| Input vượt trần | **413 trong 0,02 giây** | KEEP |
| Output vượt trần | **413** 0 s | KEEP |

Thân lỗi nói đủ ba con số, không thừa:

```json
{"ly_do":"Dau vao vuot tran token.","truong":"input_tokens","tran":96256,"thay":120001}
{"ly_do":"Xin sinh ra qua nhieu token.","truong":"max_tokens","tran":32768,"thay":999999}
```

⭐ **C05 đạt theo nghĩa mạnh nhất.** 300.000 ký tự bị từ chối trong **0,02 giây** —
tức nó bị chặn **trước khi chạm GPU**, không phải sau. Đây là thứ chỉ đo được
bằng đồng hồ; đọc mã không phân biệt được "chặn sớm" với "chặn muộn".

⛔ `/live` không rò gì: không model, không trạng thái bận, không trần. Đúng như
chú thích của nó tự đặt ra cho mình.

### C04 — một quan sát **KHÔNG tái hiện được**, ghi lại đúng như vậy

| Lượt | Thân | Kết quả |
|---|---|---|
| 1 | `{"model":"qwen38-api"}` | 400 sau **14,08 s** |
| 2 | y hệt, 2 phút sau | 400 sau **0,71 s** |

Giả thuyết (`INFERRED`, chưa chứng minh): lượt 1 rơi vào lúc model **chưa nạp**,
và một thân sai-nhưng-model-đúng vẫn kích `llama-swap` nạp model trước khi
`llama-server` từ chối. Lượt 2 chạy khi model đã ấm.

⛔ **Không ghi đây thành lỗi.** Một quan sát không tái hiện được mà bị báo thành
defect sẽ khiến phiên sau đi sửa một thứ không hỏng — và tệ hơn, làm mờ những
cảnh báo đúng nằm cạnh nó. Cần một phép đo có kiểm soát (ép unload rồi gửi thân
sai) mới kết luận được. **DEFER → Prompt 06.**

Hai thân sai khác: `{}` → 404 (thiếu `model` ⇒ rơi vào danh sách trắng, đúng),
`khong phai json` → 422 0 s.

---

## 2. Đồng thời (C06, C07) — **VERIFIED-KEEP**

Hai yêu cầu hợp lệ, cách nhau 0,4 s:

```
A  ma=200  1,59 s
B  ma=429  0,05 giay   retry_after=15
```

⭐ Đúng cả ba tính chất quan trọng: người thứ hai bị **từ chối nhanh** (0,05 s)
chứ không **xếp hàng vô hình**; có `Retry-After`; và thang gợi ý (15 s) cùng cỡ
với một lượt LLM thật, không phải 1 giây mời khách tạo vòng lặp bận.

`dang_chay` về **0** sau cả ba phép thử ⇒ **không rò suất** — bản vá 31/08 giữ
đúng lời hứa của nó dưới tải thật, không chỉ trong test.

---

## 3. Máy trạng thái GPU (C16–C21) — **một phát hiện về ĐO LƯỜNG**

Bốn nguồn tín hiệu, đọc gần như đồng thời:

| Nguồn | Giá trị | Thẩm quyền |
|---|---|---|
| `nvidia-smi` tổng | 22.350 MiB / 24.576 · 0 % · 41 °C | **authoritative** cho tổng |
| `--query-compute-apps` | **23 tiến trình**, `used_memory` = **`[N/A]` cho TẤT CẢ** | **ambiguous** — xem dưới |
| `/health trong_tai` | `ban=False so_python_gpu=1 ram_trong=118,2 GB` | advisory |
| `/health gpu` | `tren_gpu=True vram=22.350 co_model_nap=True` | authoritative |
| llama-swap `/running` | `qwen38-api state=ready` | **authoritative** cho "model nào" |

🔴 **`used_memory` là `[N/A]` cho MỌI tiến trình trên cấu hình này.** Không quy
được VRAM về chủ. Đó chính là lý do trọng tài **đếm tiến trình python** thay vì
đặt ngưỡng VRAM (D-022) — quyết định cũ ấy hoá ra không chỉ đúng vì ComfyUI giữ
model thường trú, mà còn vì **phép quy chủ VRAM không tồn tại ở đây**.

⇒ **VERIFIED-KEEP.** Nhưng đổi lý do trong tài liệu: nó không phải một lựa chọn
ưa thích, nó là **lựa chọn duy nhất khả thi**.

### 🔴 Máy B là một MÁY TÍNH ĐỂ BÀN ĐANG DÙNG, không phải một appliance

23 tiến trình trên card gồm `dwm.exe`, `explorer.exe`, `msedgewebview2.exe` (×2),
`Zalo.exe`, **`Riot Vanguard\vgtray.exe`**, `Adobe Creative Cloud`,
`Taskmgr.exe`, `WindowsTerminal.exe`, `PhoneExperienceHost`,
`Python312\python.exe` (ComfyUI), và `llama-server.exe`.

Hai hệ quả, cả hai đều thật:

* **Benchmark (Prompt 04) sẽ nhiễu** nếu ai đó đang dùng máy. Mọi số đo D30–D36
  **bắt buộc** kèm ảnh chụp `trong_tai` + danh sách tiến trình tại thời điểm đo,
  nếu không nó không có provenance.
* `so_python_gpu` đếm **python**, nên một trình duyệt hay một game **không** làm
  trọng tài báo bận. Với một máy để bàn đang dùng thật, đó là một lỗ đo — nhưng
  **không mở rộng phạm vi ở đây**; ghi thành rủi ro cho Prompt 04.

---

## 4. Vòng đời model (C22–C25) — **VERIFIED-KEEP**, có số

| Chuyển | Thời gian | Kết quả |
|---|---:|---|
| text → vision | **28,4 s** | 200 |
| vision → text | **20,6 s** | 200 |

VRAM: text 22.350 MiB · vision **20.670 MiB**.

Hai hồ sơ khác nhau ở nhiều hơn `mmproj`:

```
qwen38-api      -c 131072   ttl 1800   port 8281
qwen38-vision   -c  65536   ttl  600   port 8283   --mmproj mmproj-F16.gguf
```

⭐ `ttl` khác nhau (1800 vs 600) là một quyết định vận hành **chưa được ghi ở
đâu** ngoài chính tệp cấu hình: hồ sơ vision tự nhả sau 10 phút, hồ sơ text giữ
30 phút. Hợp lý (vision dùng thưa hơn) nhưng nên nói ra.

⛔ **Không có "dọn nhầm"**: `don_dep` chỉ chạy khi **không** có model của ta đang
chạy (`_co_model_cua_ta_dang_chay`), và cả hai lượt chuyển đều thành công mà
`da_thu_hoi` giữ nguyên 0.

---

## 5. 🔴 C26/C27 — CẤU HÌNH TRÊN ĐĨA KHÔNG PHẢI CẤU HÌNH ĐANG CHẠY

Phát hiện nặng nhất của phase này, và **tôi là người tạo ra một nửa của nó**.

```
llama-swap.yaml TREN DIA       "... input public 65K"    ghi luc 18:37:35
tien trinh llama-swap          khoi dong luc             18:34:37
cau hinh DANG CHAY (/running)  "... input public 90K"
```

`llm_gateway/deploy/deploy.ps1` **chép `llama-swap.yaml` sang máy B nhưng không
khởi động lại `LTTLlamaSwap`.** Cấu hình mới nằm trên đĩa **bất động** cho tới
khi có thứ khác restart dịch vụ — có thể vài ngày sau, và khi đó nó có hiệu lực
**âm thầm, không ai chờ đợi**.

⛔ **Và tôi đã lùi một con số hôm nay mà không biết.** Bản deploy của tôi lúc
18:37 ghi đè mô tả `90K` (đúng hơn) bằng `65K` (cũ) từ kho. Nó chưa có hiệu lực
vì llama-swap chưa restart — nhưng nó **sẽ** có, ở lần restart tiếp theo, và lúc
đó không ai liên hệ nó với một lần deploy của ngày 31/08.

⭐ Đây **cùng một lớp** với bài học đã ghi ở `setup/nap_lai_env.ps1`: *"sửa
app.env rồi restart dịch vụ là KHÔNG đủ"* — dịch vụ nướng biến môi trường vào
đăng ký lúc **cài**. Ở đây là bản đối xứng: **deploy tệp cấu hình mà không
restart thì tệp ấy không phải cấu hình.**

**Đề nghị (CHANGE, nhưng để Prompt 06 quyết vì nó chạm deploy):** `deploy.ps1`
phải hoặc (a) restart `LTTLlamaSwap` sau khi chép, hoặc (b) **in ra rõ** rằng
cấu hình chưa có hiệu lực và cần một lần restart. Im lặng là lựa chọn duy nhất
không chấp nhận được.

---

## 6. 🔴 Sửa hai chỗ trong `00_baseline.md` — cả hai là lỗi của tôi

### 6.1 C-01 sai về **cơ chế**

Tôi viết: *"trần `65K` chết… **tới tay khách** qua trường `description` của
`/v1/models`"*. **Sai.** `/v1/models` lấy dữ liệu từ `llm_gateway/catalog.py`
(`m.max_context`, `m.mo_ta`), **không** từ `llama-swap.yaml`. Đo thật:

```json
{"id":"qwen38-api","context_window":131072,"description":"... Ngu canh 131K."}
{"id":"qwen38-vision","context_window":65536,"description":"... ngu canh 64K"}
```

Chuỗi `65K` nằm trong `llama-swap.yaml` — tệp đó là **cấu hình nội bộ của
llama-swap**, không phơi ra client. Tôi thấy chuỗi đó ở một tệp, thấy `/v1/models`
có trường `description`, và **nối hai thứ lại mà không kiểm** — đúng lớp lỗi
"gán một con số có thật cho một tập hợp khác".

### 6.2 `65536` của vision **không** phải số chết

Nó là **cấu hình đang chạy** (`-c 65536`, xác nhận qua `/running`) và được công
bố nhất quán (`context_window: 65536`). Không có gì để sửa.

### 6.3 Mâu thuẫn THẬT, hẹp hơn và đúng hơn

`/v1/models` công bố `context_window: 131072` (ngữ cảnh **engine**) trong khi
cổng **cưỡng chế** `input_tokens ≤ 96.256`. Một client đọc `context_window` rồi
nhồi 131K sẽ nhận 413.

⚠️ Nhưng **mức độ thấp hơn tôi viết**: cổng máy B chỉ nghe LAN, tường lửa mở cho
đúng 192.168.2.17 ⇒ `/v1/models` này **không tới khách**. Khách đọc `/api/v1` của
máy A, và máy A công bố `88.555` — đúng. `OPERATING_CONTRACT §10` gọi tên chính
sự phân biệt này: *engine context* ≠ *hard server input cap* ≠ *advertised client
context*. Ở đây ba số là 131.072 / 96.256 / 88.555 và **cả ba đều đúng việc của
chúng**.

⇒ **KEEP**, hạ từ P2 xuống **P3**, ghi chú lại cho Prompt 01.

---

## 7. Bảng A↔B (C15)

| | Máy A | Máy B | Khớp? |
|---|---|---|---|
| id model nội bộ | `ALIAS_SANG_ID: ltt_llm→qwen38-api, ltt_llm_vision→qwen38-vision` | `LTT_LLM_MODELS=qwen38-api,qwen38-vision` | ✅ |
| trần input | `TOKEN_VAO_TRAN = 96.256` | `LTT_LLM_MAX_INPUT_TOKENS` = 96.256 | ✅ đo qua 413 |
| trần output | `TOKEN_RA_TRAN = 32.768` | 32.768 | ✅ đo qua 413 |
| đồng thời | `DONG_THOI_MAY_B = 1` | `max_dong_thoi = 1` | ✅ **nhưng hai nguồn** |
| bận | 429 + `Retry-After` | 429 + `Retry-After: 15` | ✅ |
| công bố client | 88.555 | *(không phơi ra khách)* | ✅ |

`test_334` có ba lớp đối chiếu (`TestDoiChieuMayB`, `TestDoiChieuNenTang`,
`TestDoiChieuKhoMayB`) ⇒ cơ chế chống trôi **đã có** và không cần dựng thêm.
Prompt 01 xác minh nó phủ đúng `DONG_THOI_MAY_B`.

---

## 8. Quyết định của phase

| ID | Ứng viên | Quyết định | Vì sao |
|---|---|---|---|
| D-03-1 | Ranh giới cổng (auth/allow-list/413-trước-GPU) | **KEEP** | Đo thật, đạt theo nghĩa mạnh |
| D-03-2 | Đồng thời 429 + Retry-After | **KEEP** | 0,05 s từ chối, không xếp hàng ẩn |
| D-03-3 | Đếm tiến trình python thay vì ngưỡng VRAM | **KEEP** | `used_memory` là `[N/A]` ⇒ quy chủ VRAM **không khả thi** |
| D-03-4 | 14 s ở thân sai | **DEFER → 06** | Không tái hiện được; cần phép đo có kiểm soát |
| D-03-5 | `deploy.ps1` không restart llama-swap | **CHANGE → 06** | Cấu hình trên đĩa ≠ cấu hình đang chạy, và im lặng |
| D-03-6 | `context_window` 131K vs trần 96K | **KEEP (P3)** | Ba số khác nhau cho ba việc khác nhau; không tới khách |
| D-03-7 | `max_dong_thoi = 1` | **KEEP** | `--parallel 1` của llama-server; đổi là mời OOM |

**Không sửa một dòng mã nào ở phase này.** Hai `CHANGE` đều chạm deploy ⇒ thuộc
Prompt 06, và gói cấm gom nhiều thay đổi vào một phase.

---

## 9. Điểm sau Prompt 03

| Chiều | Trước | Sau | Vì sao đổi |
|---|---:|---:|---|
| Reliability/recovery | 7 | **8** | vòng đời model đo được, không rò suất dưới tải |
| Security boundaries | 8 | **9** | fail-closed đo thật ở 7 đường, không chạm GPU |
| Observability/operations | 4 | **4** | `/health` tốt, nhưng cấu hình-trên-đĩa ≠ đang-chạy là lỗ quan sát |
| **TOTAL** | 69 | **71** | |

Confidence chiều máy B: **HIGH** (đo trên runtime thật, máy rảnh).

---

## 10. Còn nợ

* **C21 CPU/CUDA degraded** — chưa tái hiện được. `tren_gpu=True` khi khoẻ; chưa
  ép được trạng thái hỏng để xem chốt có bắt không. Cần `Prompt 06` (tiêm lỗi).
* **C28 reboot/crash recovery** — chưa thử; máy B vừa mất điện/tắt lúc 18:19 và
  lên lại sạch, nhưng đó là **quan sát**, không phải phép thử có kiểm soát.
* **C14 SSRF/media policy** — chưa chạm; hồ sơ vision nhận ảnh, cần Prompt 05.
