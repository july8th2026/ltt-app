# LLM_OPEN_SOURCE_RESEARCH — đối chiếu LTT với thượng nguồn, ở cấp mã

Phase 0 (2026-09-09). Bản sao nghiên cứu nằm **ngoài kho sản phẩm**, tại
`D:/LTT_LLM_RESEARCH_LAB/sources/` — không commit, không chép khối mã lớn.

> ⛔ Quy tắc của chương trình: mỗi kết luận phải chỉ được **đường mã**. Câu
> *"upstream production-grade nên dùng"* không được tính là kết luận.

## Bảng ghim — SHA đã ghi lại

| dự án | commit | ngày commit | giấy phép | vai trò |
|---|---|---|---|---|
| `mostlygeek/llama-swap` | `8fa85899e424d47b81fa60aff08b238a793e2e2b` | 2026-09-07 | `LICENSE.md` | **đang chạy trong sản phẩm** |
| `ggml-org/llama.cpp` | `1945e092030f8668ff93382799502d01490e564d` | 2026-09-09 | `LICENSE` (MIT) | **đang chạy trong sản phẩm** |
| `vllm-project/guidellm` | `f96d26b9e6ed16c80d456adeb697c11451340553` | 2026-09-08 | `LICENSE` | công cụ đo, KHÔNG vào sản phẩm |
| `promptfoo/promptfoo` | `e5767f290f8b57d132fe4dbe4629679552d447e7` | — | `LICENSE` | công cụ eval, KHÔNG vào sản phẩm |
| `BerriAI/litellm` | `e8e3172d7d70558929f32f057ebe4c7471c8c352` | — | `LICENSE` | **chỉ đọc để so sánh** |

⚠️ Hai dòng đầu là bản **thượng nguồn hôm nay**, KHÔNG phải bản đang chạy trên
máy B. Xem G-02 ở baseline: kho không ghi phiên bản nào đang chạy. Mọi kết luận
dựa vào hai dòng ấy đều **có điều kiện**, và điều kiện đó ghi rõ trong từng mục.

---

## O1 · mostlygeek/llama-swap

**UPSTREAM COMMIT** `8fa85899` · **NGÀY** 2026-09-07 · **GIẤY PHÉP** xem `LICENSE.md`

**VÌ SAO LIÊN QUAN** — nó là tầng [2] trong chính đường ống sản phẩm; LTT gọi
`/running` và `/upstream/<model>/tokenize` của nó mỗi ngày.

**CƠ CHẾ ĐÃ ĐỌC** — bảng định tuyến ở `internal/server/*.go`:

```
GET  /metrics                   Prometheus
GET  /api/metrics/activity      kho hoạt động, bền
GET  /api/metrics/stats
GET  /api/hardware              telemetry GPU/hệ thống
GET  /api/performance
GET  /api/events                SSE: nạp / nhả / đổi model
GET  /api/version
GET  /running                   ← LTT ĐANG dùng
GET  /unload  ·  POST /api/models/unload[/{model}]
POST /api/inflight/{id}/cancel  huỷ một lượt đang chạy
GET  /logs  ·  /logs/stream[/{id}]
GET  /api/captures/{id}         (kèm `captures.go` — quyền riêng tư)
```

**LTT ĐANG LÀM GÌ** — `llm_gateway` dùng đúng **một** đường: `/running`, ở hai
chỗ với hai câu hỏi **khác nhau** và tách bạch có chủ ý:

* `_co_model_cua_ta_dang_chay()` (`api.py:113`) — *"llama-swap có giữ **bất kỳ**
  model nào của ta không"*, để trọng tài biết tải cao trên card là của ai.
* `_ho_so_dang_nap()` (`api.py:159`) — *"**đúng hồ sơ này** đã nạp chưa"*, để
  biết `/tokenize` có rẻ không.

Hai câu này từng bị gộp, và việc gộp đã làm hồ sơ vision **gần như không bao giờ
gọi được** (sự cố 22/08, ghi ở `api.py:120-135`).

**LTT MẠNH HƠN Ở** — phân biệt *bận* với *hỏng* (429 vs 502) và ánh xạ nó sang
ngữ nghĩa tính tiền/`api_pool` của nền tảng. llama-swap không có khái niệm ấy;
nó là bộ chuyển vòng đời, không phải bộ trọng tài chia GPU với ComfyUI.

**THƯỢNG NGUỒN MẠNH HƠN Ở** — quan trắc, **rõ rệt và không tranh cãi**:
`/metrics`, `/api/metrics/activity` (bền qua khởi động lại), `/api/hardware`,
`/api/events`. LTT không có gì tương đương, và W2 hiện là hệ con điểm thấp nhất.

**KHOẢNG TRỐNG THẬT** — không phải "LTT thiếu dashboard". Là: **LTT chưa dùng
thứ nó đã trả tiền để có.** llama-swap đã ở trong đường ống, các đường trên là
đọc-thuần và nằm trên loopback.

**MẪU SẼ NHẬN** — (a) `GET /api/version` để **ghi lại** phiên bản đang chạy,
giải G-02; (b) chuyển tiếp/tóm tắt `/api/hardware` + `/metrics` vào `/health`
của cổng thay vì tự thu thập.

**MẪU TỪ CHỐI** — `/api/captures/*` (bắt prompt/response). §27 của chương trình
đặt mặc định TẮT, và ở đây không có yêu cầu nào cần nó.
**VÌ SAO** — bật nó là đem toàn văn prompt của khách vào một kho mới trên máy B.

**GIÁ PHỤ THUỘC** — 0 (đã cài). **GIÁ VẬN HÀNH** — 0 (đọc-thuần, loopback).
**RỦI RO HỒI QUY** — thấp, nhưng **có điều kiện**: nếu bản đang chạy cũ hơn
`8fa85899` thì các đường ấy có thể **không tồn tại**. Phải hỏi máy B trước.

**QUYẾT ĐỊNH** — NHẬN (a) trước, và (b) **chỉ sau khi** (a) trả lời.

---

## O2 · ggml-org/llama.cpp

**UPSTREAM COMMIT** `1945e092` · **NGÀY** 2026-09-09 · **GIẤY PHÉP** MIT

**CƠ CHẾ ĐÃ ĐỌC** — `tools/server/`: `/metrics` (`server.cpp:248`), việc dựng
văn bản Prometheus (`server-task.cpp:1522-1616`), và cổng chặn
(`server-context.cpp:4667-4672`).

**PHÁT HIỆN QUAN TRỌNG NHẤT CỦA CẢ ĐỢT NGHIÊN CỨU:**

```
server-context.cpp:4669
    if (!params.endpoint_metrics) {
        res->error(... "Start it with `--metrics`");
```

`/metrics` **tắt theo mặc định**. Và `llm_gateway/deploy/llama-swap.yaml:112-117`
(macro `CHUNG`) **không có** `--metrics`.

⇒ **Máy B đang thu thập số liệu và vứt đi.**

Vì sao dám nói "đang thu thập": các điểm cộng dồn chạy **vô điều kiện** trong
vòng lặp suy luận, không nằm sau cờ nào —

```
server-context.cpp:4066   metrics.add_prompt(n_prompt_queued, ... t_prompt_start);
server-context.cpp:4072   metrics.n_decode++;
server-context.cpp:4075   metrics.n_busy_slots++;
server-context.cpp:3412   metrics.add_prompt_cached(n_past);
server-context.cpp:4129   metrics_on_prediction(slot)  ->  metrics.predict.add(...)
```

Cờ `--metrics` chỉ mở **cửa đọc**. Nên bật nó tốn **0** trên đường nóng — đây là
kết luận đã kiểm, không phải suy đoán, và nó là lý do mục này được xếp hạng cao.

Thêm một trùng khớp: `CHUNG` đã bật `--spec-type draft-mtp --spec-draft-n-max 2`,
còn thượng nguồn phơi `llamacpp:spec_decode_num_accepted_tokens_per_pos_total`
(`server-task.cpp:1607`). Tức **tỉ lệ chấp nhận suy đoán** — một trong những số
W3 yêu cầu — đang được đếm sẵn và không ai đọc được.

**LTT MẠNH HƠN Ở** — chọn tham số engine. Mỗi cờ trong `CHUNG` mang theo lý do
đã trả giá: `--jinja` bắt buộc, template cộng đồng vá 5 lỗi tool-calling,
`--reasoning-format deepseek` để token suy nghĩ không chen giữa tool call,
`--parallel 1` vì speculative decoding tối ưu một luồng.

**THƯỢNG NGUỒN MẠNH HƠN Ở** — không phải "mạnh hơn". Nó **có sẵn một năng lực
mà LTT chưa bật**.

**MẪU SẼ NHẬN** — thêm `--metrics` vào macro `CHUNG`.
**MẪU TỪ CHỐI** — nâng binary llama.cpp trong đợt này.
**VÌ SAO** — §25 cấm "mới hơn = tốt hơn", và bộ nhớ dự án ghi
`cuBLAS INVALID_VALUE là đặc thù cu130`. Đổi engine phải đi qua đo, không đi qua
đợt này.

**GIÁ PHỤ THUỘC** 0 · **GIÁ VẬN HÀNH** 0 · **RỦI RO HỒI QUY** rất thấp: một cờ,
mở một đường đọc trên `127.0.0.1:8281`, không ai ngoài loopback chạm tới.

⚠️ Điều kiện: binary đang chạy phải đủ mới để có cờ ấy. `--metrics` đã có trong
llama.cpp từ lâu, nhưng vẫn phải **hỏi máy B**, không được suy.

**QUYẾT ĐỊNH** — NHẬN `--metrics`. TỪ CHỐI nâng cấp engine.

---

## O3 · vllm-project/guidellm

**UPSTREAM COMMIT** `f96d26b9` · **NGÀY** 2026-09-08

**VÌ SAO LIÊN QUAN** — W3 cần baseline hiệu năng **chạy lại được**. LTT đã có số
đo thật rất tốt (`catalog.py:38-60`: 50K→999,9 tok/s … 180K→616,7) nhưng chúng
là **kết quả**, không phải **bộ chạy**. Không ai chạy lại được để so.

**CƠ CHẾ ĐÃ ĐỌC** — mô hình tải: `synchronous` / `concurrent` / `constant rate`
/ `sweep` / trace replay; số đo TTFT, ITL, E2E, throughput, error rate; kết xuất
JSON/CSV; scenario có seed để lặp lại.

**LTT MẠNH HƠN Ở** — `tools/bench_llm_hieu_nang.py` và
`tools/bench_llm_admission.py` **đã tồn tại** và đo đúng thứ LTT quan tâm (dọn
card, trọng tài, admission) — thứ GuideLLM không biết gì về.

**THƯỢNG NGUỒN MẠNH HƠN Ở** — kỷ luật *phương pháp*: tách rõ **workload** khỏi
**số đo**, kết xuất máy đọc được, seed cố định.

**KHOẢNG TRỐNG THẬT** — không phải thiếu công cụ đo. Là thiếu **hợp đồng
baseline**: một tệp kết quả có phiên bản, để "candidate so với baseline" thành
một phép trừ chứ không phải một cuộc tranh luận.

**MẪU SẼ NHẬN** — hình dạng kết xuất (JSON có: model, `-c`, quant KV, build
engine, mức ngữ cảnh, TTFT, prefill tok/s, decode tok/s, VRAM đỉnh, seed).
**MẪU TỪ CHỐI** — cài GuideLLM làm phụ thuộc.
**VÌ SAO** — nó là công cụ Linux-trước, máy B là Windows, và §2 xếp "thư viện
mới" dưới "sửa mã hiện có". `bench_llm_hieu_nang.py` đã ở đúng chỗ.

**QUYẾT ĐỊNH** — NHẬN phương pháp, TỪ CHỐI phụ thuộc.

---

## O4 · promptfoo/promptfoo

**UPSTREAM COMMIT** `e5767f29`

**CƠ CHẾ ĐÃ ĐỌC** — eval tất định trên endpoint tương thích OpenAI; assertion có
kiểu; chạy như một cổng cục bộ (CLI), không phải dịch vụ thường trú.

**LTT MẠNH HƠN Ở** — `tools/danh_gia_llm.py` đã có, và bộ test hồi quy của LTT
**dẫn dắt bởi sự cố thật** — đúng thứ §29 nói là đáng giá hơn số lượng.

**THƯỢNG NGUỒN MẠNH HƠN Ở** — tách **corpus** khỏi **bộ chạy**, nên thêm một ca
là thêm dữ liệu chứ không phải thêm mã.

**KHOẢNG TRỐNG THẬT** — hẹp. LTT đã bắt hồi quy giao thức/tool/ngữ cảnh dài bằng
pytest, và pytest **đã** ở trong cổng chất lượng. Thêm một bộ chạy thứ hai là
thêm một chỗ để quên chạy.

**MẪU SẼ NHẬN** — corpus tách khỏi mã (bảng ca dữ liệu).
**MẪU TỪ CHỐI** — cài Promptfoo (Node) lên máy B hoặc vào cổng chất lượng.
**VÌ SAO** — nó kéo một hệ sinh thái Node vào một cổng đang chạy bằng Python,
để đổi lấy thứ pytest đã làm được.

**QUYẾT ĐỊNH** — NHẬN hình dạng, TỪ CHỐI công cụ.

---

## O5 · BerriAI/litellm

**UPSTREAM COMMIT** `e8e3172d` · **CHỈ ĐỌC ĐỂ SO SÁNH**

**ĐỐI CHIẾU TRỰC TIẾP VỚI** `platform_core/llm/dieu_phoi.py` (255 dòng).

| chủ đề | LiteLLM | LTT | ai hơn |
|---|---|---|---|
| router đa provider | có, cấu hình được | có, bên gọi tự khai `thu_tu_provider` | hoà |
| phân loại lỗi | phân loại theo provider | `BanError` / `VuotNganSachError` / `AmbiguousProviderError` / `ProviderOomError` / `CongVlmError` | **LTT** |
| retry | có, và mặc định **bật** | **cố ý không retry** khi mơ hồ | **LTT** |
| cooldown/health key | có | `api_pool.danh_dau_loi` + không đánh dấu khi bận | hoà |
| giữ chỗ ngân sách | có | `credit.giu_cho` → `quyet_toan` → `hoan` | **LTT** |

**LTT MẠNH HƠN Ở — và đây là kết luận đáng giá nhất của mục này:**

```python
# dieu_phoi.py:228-231
except (AmbiguousProviderError, ProviderOomError):
    # Không cascade: timeout sau POST có thể đã tạo side effect; OOM
    # nguyên request sẽ lặp lại y hệt ở sản phẩm không cho fallback.
    raise
```

Rubric của chương trình phạt "retry duplicate-side-effect risk" xuống
Reliability ≤ 90. LTT **không** dính, và không dính vì một quyết định có chú
thích lý do. Một router đa dụng khó làm được điều này, vì nó không biết lượt gọi
của bạn có tác dụng phụ hay không — LTT biết, vì nó không đa dụng.

**THƯỢNG NGUỒN MẠNH HƠN Ở** — bề rộng provider và chuẩn hoá dạng dây cho hàng
chục nhà cung cấp. LTT có **hai** (`ltt_llm`, `gemini`), mỗi cái một hàm.

**KHOẢNG TRỐNG THẬT** — **không có.** Với hai provider, `dieu_phoi.py` **đơn
giản hơn và đúng hơn** cho đúng việc của nó.

**MẪU TỪ CHỐI** — đưa LiteLLM vào đường request.
**VÌ SAO** — nó dựng `LTT → LiteLLM → cổng LTT → llama-swap → llama.cpp`: thêm
một tầng, thêm một điểm hỏng, thêm độ trễ, và **thay một lớp phân loại lỗi đã
đúng bằng một lớp đa dụng**. Không có bằng chứng nào biện minh cho việc đó.

**QUYẾT ĐỊNH** — KHÔNG TÍCH HỢP. Giữ `dieu_phoi.py`.

---

## O6 · langfuse · O7 · prometheus · O8 · grafana — nghiên cứu ở mức khái niệm

**KHÔNG clone.** Lý do ghi rõ chứ không giấu: sau O1+O2, khoảng trống quan trắc
đã có lời giải **không cần** thêm dịch vụ nào — llama.cpp đã đếm sẵn, llama-swap
đã phơi sẵn. Clone thêm ~500 MB để nghiên cứu một giải pháp đã bị loại bởi bằng
chứng là tiêu công vào việc không đổi quyết định.

**KHÁI NIỆM NHẬN** — quy ước đặt tên Prometheus (counter `_total`, gauge, đơn vị
cơ bản trong tên). LTT sẽ **đọc** metric theo tên llama.cpp đã dùng
(`llamacpp:*`), nên quy ước là thứ đọc chứ không phải thứ đặt.

**KHÁI NIỆM TỪ CHỐI** — self-host Langfuse; chạy máy chủ Prometheus; dựng
Grafana.
**VÌ SAO** — §1: tải thấp, ít người dùng, một node. Ba dịch vụ ấy tồn tại để
giải bài toán nhiều node / lưu lâu / nhiều người xem. Ở đây chúng là ba tiến
trình nữa **trên chính cái máy đang tranh GPU với ComfyUI và việc video** — tức
chúng làm tệ đi đúng thứ hệ này nhạy cảm nhất.

⛔ Và §14 chặn trần Operational Simplicity ≤ 80 cho việc over-engineer hệ nội bộ.
Thêm chúng sẽ **hạ** điểm, không nâng.

**QUYẾT ĐỊNH** — KHÔNG TÍCH HỢP. Xem lại nếu, và chỉ nếu, có nhiều node.

---

## Tổng kết quyết định

| # | Mẫu | Quyết định | Giá phụ thuộc |
|---|---|---|---|
| A | `GET /api/version` của llama-swap để **ghi lại** bản đang chạy | **NHẬN** | 0 |
| B | `--metrics` cho llama-server | **NHẬN** | 0 |
| C | Tóm tắt `/metrics` + `/api/hardware` vào `/health` cổng | **NHẬN, có điều kiện** (sau A) | 0 |
| D | Hình dạng kết xuất baseline kiểu GuideLLM | **NHẬN** (phương pháp) | 0 |
| E | Corpus eval tách khỏi bộ chạy | **NHẬN** (hình dạng) | 0 |
| F | LiteLLM vào đường request | **TỪ CHỐI** | — |
| G | Bắt prompt/response (`captures`) | **TỪ CHỐI** | — |
| H | Langfuse / Prometheus / Grafana chạy thường trú | **TỪ CHỐI** | — |
| I | Nâng binary llama.cpp trong đợt này | **TỪ CHỐI** | — |

**Không mẫu nào được nhận kéo theo một phụ thuộc mới hay một dịch vụ mới.** Đó
không phải sự trùng hợp — đó là thứ tự ưu tiên của §2 áp dụng đúng: *dùng lại cơ
chế sẵn có* thắng, ba lần liền.
