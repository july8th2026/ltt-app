# Bộ đo chuẩn cho cổng D/E/F — và vì sao bỏ bộ tự viết

> Lập **2026-09-13**. Chủ sản phẩm chốt: *"nên xử lý kỹ bộ đo trước, lấy công cụ
> từ các open source, model"*. Tệp này ghi **cái gì đã chọn, đo được gì để chọn,
> và bốn lỗi khiến phải chọn lại**.

## 1. 🔴 Bốn lần bộ đo tự viết nói dối về production

Không cái nào là lỗi của hệ thống. Cả bốn đều là lỗi của **công cụ đo**, và cả
bốn đều là thứ một bộ đo chuẩn đã giải xong từ lâu.

| # | bộ đo báo | sự thật | cơ chế |
|---|---|---|---|
| 1 | `C1 = 18,98 tok/s`, `scaling 3,93×` cho 3 slot | C1 thật ≈ 58 | lượt đầu phải **nạp model**, và 17 s nạp rơi vào **mẫu số** của C1 |
| 2 | "3 luồng đồng thời" | thật ra 2 + 1 xếp hàng | `.NET DefaultConnectionLimit` = 2 kết nối/host |
| 3 | "6/6 hết giờ", "2/2 hết giờ" | tất cả `done` trong vài giây | API trả `succeeded`, CSDL lưu `done`; bộ đo chờ chữ `done` **trên API** |
| 4 | "62 khoản giữ treo" | 0 | sổ ghi kép giữ **cả** `hold` lẫn `settle`; đếm `hold` là đếm lịch sử |

⛔ Và một lỗi thứ năm, nguy hiểm nhất vì nó làm cổng báo **ĐẠT** cho điều chưa
   từng dựng: *"ngữ cảnh 60K"* thật ra là **24.634** token, vì `KY_TU_MOI_TOKEN`
   = 2,5 là ước **CAO** (đúng cho giữ tiền) bị đem đi **dựng** prompt.

## 2. Công cụ đã chọn

| tầng | công cụ | vì sao |
|---|---|---|
| **serving** (cổng D/E/F) | **GuideLLM** 0.7.3 (`vllm-project`) | đo đúng đại lượng ngành dùng — TTFT, ITL, TPOT, phân vị — và tự quản lý đồng thời bằng bộ lập lịch |
| **engine ngoại tuyến** (cổng H) | `llama-batched-bench` | công cụ **chính chủ** của llama.cpp cho thông lượng ở N chuỗi song song |

⛔ `ray-project/llmperf` **đã archive** — không dùng.

### `llama-batched-bench` chưa dùng được ngay, và lý do phải ghi lại

Nó **tự nạp model**, nên cần card trống. `llama-server` đang giữ 16,5 GB trên
3090 ⇒ không có chỗ cho bản thứ hai. Nó là công cụ đặc tả **engine ngoại tuyến**,
không phải đo **dịch vụ đang sống**. Để dành cho cổng H, khi có cửa sổ bảo trì.

⭐ Cả hai đã có sẵn trên máy B: `H:\LTT_LLM\bin\llamacpp\llama-bench.exe` và
   `llama-batched-bench.exe`.

## 3. Bốn ràng buộc — **đo được**, không đoán

| ràng buộc | đo được | hệ quả |
|---|---|---|
| `uvloop` không hỗ trợ Windows | `pip install guidellm` vỡ khi build `uvloop` | GuideLLM phải chạy trong **WSL** |
| WSL có Python **3.14**, GuideLLM đòi 3.10–3.13 | `python3 --version` | dùng **`uv`** lấy đúng 3.13, không đụng Python hệ thống |
| Cloudflare **không** chặn `httpx` | `/api/v1/models` → **200** | đo được qua đường công khai |
| `validate_backend` mặc định hỏng với API của ta | nó dùng `api_routes` rỗng | `validate_backend=false` — đó là bước chào hỏi, không phải phép đo |

## 4. 🔴 Và một kết luận SAI của chính tôi, giữ lại vì nó là bài học về công cụ

Tôi từng báo: *"`Idempotency-Key` **không** bắt buộc"*, dựa trên một lượt gọi
không kèm header ấy mà nhận **200**.

**Sai.** Lượt ấy đi qua `tools/do_tai_hai_model.Khach`, và dòng 194 của nó:

```python
dau["Idempotency-Key"] = idem or str(uuid.uuid4())
```

**tự chèn** một mã cho mọi POST. Tức tôi đã đo **công cụ của mình**, không đo API.
Gọi thẳng bằng `httpx` cho ra sự thật:

```
400 invalid_request
"This endpoint requires an Idempotency-Key header, one per call"
```

⛔ **Bài học về hình dạng:** một phép thử đi qua một lớp có **hành vi ẩn** không
   trả lời được câu hỏi về lớp **bên dưới** nó. Muốn hỏi API thì phải gõ cửa API,
   không gõ cửa client của mình.

⭐ Và sai lầm ấy có giá cụ thể: nó suýt làm tôi chọn một kiến trúc đo sai (bắn
   thẳng công cụ chuẩn vào cửa ghi), rồi đọc 12 lượt **400** thành "cổng trượt".

## 5. `cau_idem.py` — vì sao cần một cầu nối, và nó thêm gì vào phép đo

Mọi bộ đo LLM chuẩn nói OpenAI **thuần**: chúng gửi một bộ header **cố định**.
Cửa ghi của ta đòi một mã **mới mỗi lượt**. Hai điều đó không gặp nhau.

⇒ Một cầu nối 40 dòng chèn `Idempotency-Key: <uuid4>` vào đường đi. Bộ đo giữ
  **nguyên bản**, không vết vá; phần riêng của ta nằm gọn một chỗ đọc được.

⛔ **Vì sao mã phải MỚI mỗi lượt, không phải một mã cố định:** dùng một mã chung
   thì lượt thứ hai nhận lại **câu trả lời cũ** — không có lượt chạy mới nào —
   và phép đo sẽ báo một thông lượng **không tồn tại**.
   `test_259::test_BAY_khoa_co_dinh_o_default_headers` chốt đúng cái bẫy ấy.

⚠️ Cầu nối thêm **một chặng loopback**. `/_cau/tre` in thời gian chặng **ngược
   dòng** (cầu nối → API); phần phụ trội của chính cầu nối là **hiệu** giữa thời
   gian bộ đo thấy và con số ấy. Đọc sai tên con số này là trừ nhầm một khoản
   gấp hàng trăm lần.

## 6. ⛔ Hai phép đo cùng lúc trên một GPU thì cả hai đều sai

Tôi đã suýt chạy chân **engine** và chân **dịch vụ** song song. Cả hai bắn vào
cùng một 3090 — con số thu được sẽ không trả lời được câu hỏi nào cả. Chạy **nối
tiếp**, và ghi lại thứ tự.

Cùng một luật với `may-tai-nang-lam-gate-SAI-khong-chi-cham`: tải làm phép đo
**sai**, không chỉ làm nó chậm.

## 7. Cái gì bị XOÁ, cái gì GIỮ — và luật phân loại

Chủ sản phẩm chốt: *"nên xoá bộ đo tự viết thay bằng bộ đo tải về, tránh sau sử
dụng nhầm"*. Nhưng không phải mọi script tự viết đều là "bộ đo".

⭐ **Luật phân loại: hỏi nó trả lời câu gì, đừng nhìn tên nó.**

| loại | câu nó trả lời | phán quyết |
|---|---|---|
| **bộ đo thông lượng** | *"nhanh bao nhiêu, ở mấy luồng"* | ⛔ **XOÁ** — GuideLLM làm đúng hơn |
| **đầu dò trạng thái** | *"CSDL/GPU/hàng job đang ở đâu"* | ✅ **GIỮ** — GuideLLM không biết gì về `execution_leases`, `gpu_residency`, `credit_entries` |
| **bộ dựng tình huống** | *"huỷ lúc đang chạy thì sao"* | ✅ **GIỮ** — đó là kịch bản nghiệm thu, không phải phép đo tốc độ |

### Đã xoá (trùng chức năng với GuideLLM)

`do_cong_de.py` · `do_cong_de_v2.py` · `do_thang_may_b.ps1` · `do_thang_may_b.py`
· `do_kho_am.py` · `do_da_san.py`

Cả sáu đo **tok/s ở N luồng**. Cả sáu đã từng cho ra ít nhất một con số sai.

### Giữ lại (đầu dò / dựng tình huống)

`soi_lease_tien.py` · `soi_residency.py` · `hoi_jobs.py` · `dem_lease.py` ·
`do_cong_mop.py` · `do_ngat_sync_tra_slot.py` · `go_ket_nha_llm.py` ·
`kiem_prod_thua_tep.py` · `hoi_alembic.py`

⛔ Chúng **không** đo tốc độ. Xoá chúng là mất khả năng trả lời *"sau khi một
lượt kết thúc bất thường thì còn sót gì"* — câu mà ba cổng M/O/P cùng hỏi và
không bộ benchmark nào trả lời được.

## 8. ⛔ `pkill -f <ten_script>` tự khớp vào chính nó

Khởi động lại cầu nối bằng:

```bash
pkill -9 -f cau_idem.py; setsid python cau_idem.py ...
```

**tự giết chính mình**: chuỗi `cau_idem.py` có mặt trong dòng lệnh của `bash -c`
đang chạy `pkill`, nên `pkill` khớp vào shell của chính nó. Lệnh thoát với mã 9
(SIGKILL) trước khi kịp khởi động lại thứ gì.

⇒ Dừng theo **cổng** (`fuser -k 18099/tcp`) hoặc theo **PID đã ghi**, không theo
  chuỗi tên. Kho đã ghi đúng bài học này ở
  `loc-tien-trinh-bang-chuoi-tu-khop-vao-chinh-no`.

## 9. Ba ràng buộc nữa, chỉ lộ ra khi bắn thật

### 9.1 GuideLLM **cắt đuôi `/v1`** của target rồi tự thêm lại

```
target https://.../api/v1        ->  https://.../api   + /v1/chat/completions
target http://127.0.0.1:18099    ->  (không cắt gì)    + /v1/chat/completions
```

Cầu nối vì thế nhận đường `v1/chat/completions` và **phải bỏ tiền tố ấy** trước
khi nối vào đích `.../api/v1` — không thì thành `.../api/v1/v1/...` → **404**.
Đo được: 12/12 lượt đầu hỏng đúng vì lý do này.

### 9.2 Cửa đồng bộ **từ chối `stream: true`**, và nó chỉ đúng đường

```
400 invalid_request
"This endpoint returns a single JSON answer. For a stream use
 POST /api/v1/messages (Anthropic Messages) or POST /api/v1/responses
 (OpenAI Responses) — those are what Claude Code, Claude Desktop and Codex speak."
```

GuideLLM mặc định `stream=true` ⇒ phải đặt `stream=false` cho cửa này.

⚠️ **Hệ quả với phép đo, phải đọc rõ:** không có stream thì **không đo được
TTFT/ITL** ở cửa đồng bộ — chỉ đo được độ trễ cả lượt và thông lượng. Muốn số
TTFT cho khách **streaming** thì phải đo `/api/v1/responses`, và đó là một cổng
khác với một câu hỏi khác. Ghi hai con số dưới hai cái tên khác nhau, đừng gộp.

### 9.3 Mỗi chân phải chạy NỐI TIẾP

Chân engine và chân dịch vụ cùng bắn vào một 3090. Chạy song song thì cả hai số
đều vô nghĩa. Thứ tự đã dùng: engine trước, dịch vụ sau.

## 10. Số đo bằng GuideLLM — và hai kết luận cũ bị bác bỏ

`ltt-3.8` · prompt 256 tok · output 700 tok · 12 lượt · `stream=false` cả hai chân.

| | C1 (tok ra/s) | C3 (tok ra/s) | scaling |
|---|---:|---:|---:|
| **engine** — thẳng máy B (qua đường hầm SSH) | **67,1** | **132,3** | **1,97×** |
| **dịch vụ** — qua máy A + Cloudflare | **63,4** | **107,5** | **1,70×** |

### 🔴 Bác bỏ 1: *"phí nền tảng RẺ DẦN khi tải tăng"*

Tôi từng ghi (từ bộ tự viết): phí nền tảng ăn vào C1 nặng hơn ăn vào C3, nên
tỉ số scaling qua máy A **cao hơn** đo thẳng máy B. Đo lại bằng công cụ chuẩn,
cùng thiết lập, ngược hẳn:

| | phí nền tảng |
|---|---:|
| ở C1 | 67,1 − 63,4 = **3,7** tok/s (5,5 %) |
| ở C3 | 132,3 − 107,5 = **24,8** tok/s (18,7 %) |

⇒ Nền tảng **đắt dần** theo đồng thời, không rẻ dần: nó nuốt khoảng **một phần
tư** phần lợi mà engine có được khi chạy 3 luồng (1,97× → 1,70×).

⛔ Kết luận cũ sai vì hai chân đo ở hai chế độ khác nhau mà tôi không nhận ra —
   một chân có stream, một chân không. **Hai con số chỉ trừ được cho nhau khi
   mọi thứ khác giống hệt**, và "mọi thứ khác" gồm cả những cờ mình không nhớ
   là mình đã đặt.

### ⭐ Phát hiện phụ: **streaming tốn ~24 % thông lượng**

Cùng engine, cùng đề, chỉ khác một cờ:

| | C3 (tok ra/s) |
|---|---:|
| `stream=true` | 100,5 |
| `stream=false` | **132,3** |

Đây là một con số sản phẩm, không chỉ là một con số đo: khách dùng streaming
trả giá bằng thông lượng, và mức giá ấy nay đo được.

### Cổng D — nửa TTFT

Spec §23 đòi *"TTFT ngắn p95 ≤ 3 s khi còn chỗ"*. Đo ở chân engine có stream:

| | TTFT trung vị | TTFT p95 |
|---|---:|---:|
| C1 | 590 ms | 868 ms |
| C3 | 1151 ms | **1336 ms** |

**ĐẠT**, còn biên hơn 2×.

⚠️ Con số này đo ở **engine**. TTFT mà khách qua máy A thấy phải đo ở
`/api/v1/responses` — cửa đồng bộ không nói stream nên không có TTFT để đo.
Hai câu hỏi khác nhau, hai con số khác nhau, đừng gộp.
