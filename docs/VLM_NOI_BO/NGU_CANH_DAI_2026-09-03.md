# Ngữ cảnh dài của `ltt_llm` — đo, quyết, và cái bẫy đã suýt lừa tôi

> **Nhánh:** `phien/ltt-llm-context-200k` · **gốc:** `admin-mvp-v3` `dac2406`,
> được phiên khác fast-forward lên `d225a48` giữa chừng (kiểm: `dac2406` vẫn là
> tổ tiên của `d225a48`, không mất gì).
>
> Nguồn chân lý vẫn là `apps/ltt_llm/ngan_sach.py`. Tệp này **không** giữ một
> con số nào để tra cứu — nó giữ **bằng chứng** và **lý do**.

---

## 0. Triệu chứng phải giải thích

```
POST /api/v1/responses  ->  413
input_tokens   101.938
hard limit      96.256
```

Máy B: `Dau vao vuot tran token · tran=96256 · thay=101938`.

⚠️ `thay` là **token ƯỚC**, không phải token thật: `llm_gateway/ngan_sach.py`
chặn bằng `len(text) / 2.5` để **không phải đánh thức GPU** chỉ để đếm. Ước cao
là chiều sai an toàn, nhưng nó có nghĩa là *client không thể tự dự đoán chính
xác chỗ ta từ chối*. Đó là lý do `CONG_BO_CHO_CLIENT` phải thấp hơn trần thật.

---

## 1. Vì sao client không nén kịp — và vì sao "0,8" là câu trả lời sai

Hai bộ cài đều tính ngưỡng nén bằng `cửa_sổ × 0,8`.

```
cửa sổ công bố   88.555
ngưỡng nén 0,8   70.844
khoảng trống     25.412      <-- nhỏ hơn MỘT lượt sinh dài nhất (32.768)
```

Client chỉ kiểm ngưỡng **giữa hai lượt**. Nên sau khi nó quyết định "chưa cần
nén" ở 70.844, lượt kế tiếp vẫn được phép lớn thêm trọn một lượt nữa. Cấu hình
ấy **không thể** giữ lời hứa "nén trước khi chạm trần" — nó chỉ đúng chừng nào
không ai trả lời dài.

⭐ Điều đáng nhớ: `0,8` không sai vì bịa. Nó sai vì **được chọn ở một cửa sổ
rộng rồi mang sang một cửa sổ hẹp** mà không ai tính lại. Ở hồ sơ ngữ cảnh rộng,
quy tắc đúng (`công bố − một lượt sinh`) rơi gần đúng vào 0,79.

⇒ `ngan_sach.nen_cua()` nay **dẫn xuất** khoảng trống đó thay vì gõ một tỉ lệ.

---

## 2. Ba khuyết tật cùng họ, tìm ra trên đường

| # | Khuyết tật | Vì sao nó sống được |
|---|---|---|
| D-01 | Hai bộ cài khai `ltt_llm_vision` với cửa sổ của model **text** (88.555) trong khi cửa sổ thật của nó là **28.262** — hứa gấp **3,1 lần** | Đây đúng là F-02 ("một con số cho hai model") mà `cong_bo_cua()` sinh ra để giết. Nó chết ở `/api/v1/models` và **sống sót ở bộ cài** |
| D-02 | **Hai phép kiểm đang cưỡng chế D-01**: `test_283` và `test_334` cùng viết `assert m["context_window"] == CUA_SO_NGU_CANH` trong một vòng lặp trên **nhiều** model | Phép kiểm không bắt khuyết tật; nó **đòi** khuyết tật. Sửa mã cho đúng thì gate đỏ — nên không ai sửa |
| D-03 | `sdk/ltt_cai_dat_cli.py` (bản một-tệp cho macOS/Linux) không đặt `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | Bản Windows đặt từ 30/08, kèm cả khối chú thích nói "thiếu chúng là một lỗi tiền". `test_275` so **catalog** giữa hai bộ cài và xanh suốt — vì khoảng trống nằm ở *chỗ nó không nhìn* |

⭐ Bài học chung của cả ba: **một bản vá sửa *con số* mà không sửa *hình dạng*
thì khuyết tật quay lại ở bản sao kế tiếp.** Chừng nào còn MỘT hằng số cho HAI
model, hoặc MỘT tỉ lệ gõ tay ở HAI tệp, nó còn quay lại.

---

## 3. Đo thật, 2026-09-03, trên đúng card đang phục vụ

RTX 3090 24.576 MiB · `llama-server` build 10689 · `--parallel 1` ·
MTP `--spec-draft-n-max 2` · flash-attention.

Mỗi lượt: prompt **ngẫu nhiên** (không tái dùng prompt cache), đếm token bằng
`/tokenize` của chính model đang nạp, cắm một mốc ở **đầu** và một ở **cuối**
prompt rồi bắt model đọc lại cả hai.

| token vào | `qwen38-api` 131K/q8_0 | `qwen38-ops` 200K/q4_0 |
|---:|---|---|
| 50.000 | 1.004,7 tok/s · TTFT 49,7 s | 999,9 tok/s · TTFT 49,9 s |
| 100.000 | 802,0 · 124,8 s | 805,3 · 124,3 s |
| 130.000 | 712,8 · 182,4 s | 726,5 · 178,6 s |
| 150.000 | — (quá cửa sổ) | 672,4 · 223,0 s |
| 165.000 | — | 639,1 · 257,8 s |
| 180.000 | — | 616,7 · 291,7 s |
| **VRAM đỉnh** | **22.017 MiB** | **21.979 MiB** |

**Mốc đầu và mốc cuối đọc lại đúng ở mọi lượt hoàn tất** ⇒ không có cắt ngữ cảnh
im lặng ở hồ sơ nào.

Hồ sơ 200K **không** tốn thêm VRAM (thực ra ít hơn 38 MiB) và **không** chậm hơn
ở mọi mốc chung.

---

## 4. 🔴 HAI CÁI BẪY, CÙNG MỘT CÁI XÁC

Hồ sơ 200K "chết" **hai lần**, ở hai mốc khác nhau, trong hai lô đo khác nhau.
Cả hai lần đều để lại **đúng cùng một dấu vết**:

```
ConnectionResetError [WinError 10054]      <- luot dang chay
URLError [WinError 10061] refused          <- moi luot sau do
```

Và cả hai lần, giải thích hiển nhiên — *"hồ sơ 200K chỉ còn 2,6 GiB biên, prefill
ở ngữ cảnh lớn cần buffer lớn hơn, nên OOM"* — **khớp hoàn hảo**. Nó khớp với
cảnh báo của mọi bảng cộng đồng, khớp với lý do `llm_gateway/ngan_sach.py` tồn
tại, và khớp với việc mốc chết cao dần khi ngữ cảnh cao dần.

**Cả hai lần nó đều sai.**

### Lần 1 — 130K: bị ĐUỔI

```
task 160 | prompt processing, n_tokens = 12288, progress = 0.09
...
srv load_model: initializing, n_slots = 1, n_ctx_slot = 131072   <-- 131K!
[INFO] <qwen38-api> Health check passed on http://127.0.0.1:8281/health
```

Một tiến trình `llama-server` **mới** khởi động với `-c 131072` ngay giữa lượt
prefill. llama-swap **đuổi model đang chạy** để nạp hồ sơ mà một request khác
gọi. Nguồn: `LTTStudioWeb` trên máy A (pid 25060 → nssm → `LTTStudioWeb`) — một
phiên khác đang chạy bộ kiểm giao diện ChatLTT trên production, mỗi lượt là một
`POST` thật qua `text.chat` → `ltt_llm`.

Đo lại trong cửa sổ yên: **130K chạy 178,6 s, mốc đầu-cuối đúng.**

### Lần 2 — 180K: bị HẾT HẠN

```
[INFO] <qwen38-ops> Unloading model, TTL of 900s reached
```

Model nạp xong lúc 19:04:12; `ttl: 900` ⇒ 19:19:12; lượt chết lúc 19:19:16.

Lý do sâu hơn nằm ở **công cụ đo của tôi**: nó gửi thẳng tới cổng của
`llama-server` (8282) thay vì đi qua llama-swap, vì tôi nghĩ bỏ một lớp proxy
thì phép đo "sạch hơn". Nhưng `ttl` của llama-swap đếm hoạt động **đi qua nó**.
Đi vòng qua llama-swap là **tự tay tắt đồng hồ giữ model sống**, rồi quy cái
chết cho model.

### ⭐ Điều rút ra, và nó không phải "cẩn thận hơn"

Một lần OOM, một lần bị đuổi, và một lần hết hạn TTL **để lại cùng một cái xác**.
Không phép đo nào ở tầng client phân biệt được ba thứ đó — phải đọc log của
tầng dưới. Nên chuẩn "tái hiện được" là chưa đủ ở đây; chuẩn phải là **giải
thích được cái xác bằng một nguồn độc lập**.

Và cả hai lần, thứ suýt làm tôi kết luận sai là **một giả thuyết khớp quá vừa**.

### ⭐ Phát hiện kiến trúc — lần 1 không chỉ là tai nạn đo đạc

**llama-swap giết một lượt đang chạy để nhường chỗ cho hồ sơ khác, và lượt bị
giết chỉ nhận `ConnectionReset` — không lỗi nào nói vì sao.**

⇒ Nếu ta từng mở **hai** hồ sơ text ra cho khách cùng lúc, một request hồ sơ B
sẽ **giết một lượt đang chạy của hồ sơ A**, ngẫu nhiên, không giải thích được.
Nên kết luận là **một hồ sơ text công khai duy nhất** — tức nếu nâng ngữ cảnh
thì nâng chính `qwen38-api`, **không** trỏ bí danh `ltt_llm` sang `qwen38-ops`.

*(Hồ sơ vision vẫn swap với text — điều đó không tránh được và đã là hiện trạng;
khác biệt là nó do **khách chọn model** chứ không phải do ta chia đôi một model.)*

## 4c. Codex thật, bản thật — A/B trên `codex-cli 0.145.0`

Không suy từ cấu hình. Chạy **hai** `CODEX_HOME` khác nhau, khác **đúng một
dòng** (`model_catalog_json`), rồi đọc thứ Codex tự in ra:

| | Không có catalog | Có catalog ta sinh |
|---|---|---|
| Cảnh báo | `warning: Model metadata for` `` `ltt_llm` `` `not found. Defaulting to fallback metadata; this can degrade performance and cause issues.` | **không có** |
| `model` / `provider` | `ltt_llm` / `ltt` | `ltt_llm` / `ltt` |
| Tệp cấu hình | nhận | **nhận** |

⭐ Hai điều đọc được từ đây, và cả hai đều cần:

1. **`model_context_window = 88555` một mình KHÔNG đủ.** Hồ sơ "không catalog"
   vẫn khai đúng con số đó, và Codex vẫn rơi về metadata dự phòng. Thứ giết được
   cảnh báo là **tệp catalog** — và `auto_compact_token_limit` chỉ tồn tại ở đó.
2. **Catalog mới (mỗi model một cửa sổ) không làm Codex từ chối tệp.** Đó là rủi
   ro thật của thay đổi này: ngày 30/08 hai trường sai khuôn đã làm Codex **từ
   chối khởi động**, và một lần nữa làm vỡ tiện ích VS Code. Nên "Codex vẫn chạy"
   là một kết quả phải đo, không phải một giả định.

Cả hai lượt đều đi hết đường tới `https://app.lttstudios.com/api/v1/responses`
và nhận `401` có cấu trúc (`retry: never`) — tức đường mạng, Cloudflare và cổng
fail-closed đều đúng. Lượt phiên dài với khoá thật vẫn còn nợ (xem §8).

**Chạy lại sau khi đổi số** (catalog mới: `ltt_llm` 156.385 / nén 123.617;
`ltt_llm_vision` 28.262 / **không có** trường ngưỡng nén): Codex 0.145.0 vẫn
nhận tệp, vẫn **không** cảnh báo. Đây là phép đo bắt buộc chứ không phải cho
yên tâm — bỏ hẳn một trường là đúng thứ đã từng làm Codex từ chối khởi động
(30/08, `web_search_tool_type: null`), và một trường khác thì làm vỡ tiện ích
VS Code trong khi CLI vẫn xanh.

---

## 5. Trần nào bị chạm trước

| Trần | Giá trị | Ở ngữ cảnh 200K |
|---|---|---|
| VRAM | 24.576 MiB | 21.979 đo được — **không phải trần bị chạm** |
| Body request của nền tảng | `DEFAULT_MAX_BODY_BYTES` = 1 MiB | cần ~765 KB — vừa, nhưng **phải kiểm giá trị THẬT trên production** (`LTT_PUBLIC_API_MAX_BODY_BYTES` có thể bị đặt khác) |
| Cloudflare (cửa **đồng bộ**) | ~100 s | TTFT ở 165K là 257,8 s ⇒ vượt xa. **Nhưng đây không phải vấn đề mới, và nâng trần token không làm nó tệ hơn** — xem đo ngay dưới |
| Cloudflare (cửa **stream**) | đồng hồ **im lặng**, không phải tổng thời gian | `llm_gateway/nhip_tim.py` chèn chú thích SSE mỗi 15 s trong lúc prefill ⇒ đồng hồ không bao giờ chạm |

### Cửa đồng bộ tự co, và nó co bằng **thời gian** chứ không bằng token

`features.tran_token_ra_dong_bo(token_vao, 90 s)` — số token ra còn vừa ngân
sách 90 giây của cửa đồng bộ, sau khi trừ thời gian prefill:

| token vào | token ra còn cho phép |
|---:|---:|
| 20.000 | 1.306 |
| 60.000 | **0** |
| 96.256 (trần hiện tại) | **0** |
| 169.984 (trần nếu nâng) | **0** |

⇒ Cửa đồng bộ **đã** từ chối mọi thứ trên ~43K từ trước, bằng một `400` nói rõ
lý do và chỉ sang cửa stream / cửa job. Nâng trần token **không** đổi gì ở đây,
vì trần thật của cửa này chưa bao giờ là trần token.

⭐ Đây là lý do §31 của chương trình (*"đừng để mỗi cửa một trần"*) **không** bị
vi phạm: ba cửa dùng **chung một** trần token, và cửa đồng bộ hẹp hơn vì một
ràng buộc **khác loại** — đồng hồ của Cloudflare — được cưỡng chế ở một chốt
riêng, có thông điệp riêng.

⭐ Nên chú thích cũ ở `llm_gateway/catalog.py` — *"mở `qwen38-ops` ra Internet là
bán một cửa sổ khách không dùng nổi"* — **đúng cho cửa đồng bộ và sai cho cửa
stream**, vì nó được viết trước khi `nhip_tim.py` tồn tại và chưa ai đọc lại nó
sau đó. Cửa mà Codex và Claude Code dùng là cửa stream.

---

## 5b. Chất lượng: KV `q8_0` so với `q4_0`

Nâng lên 200K **bắt buộc** đổi KV cache sang `q4_0` — `q8_0` ở 200K không vừa
card 24 GB. Nên "chạy được" chưa đủ; phải hỏi *"trả lời có tệ đi không"*.

`tools/danh_gia_llm.py --lan 3`, 12 bài, cùng bộ đề, cùng ngày, cùng build,
thu thập cách nhau 5 phút:

| | `qwen38-api` (q8_0) | `qwen38-ops` (q4_0) |
|---|---|---|
| tiếng Việt · tiếng Anh · lập trình · sửa lỗi · cấu trúc · ngữ cảnh dài · sinh dài · chọn tool | tất cả 100 % | tất cả 100 % |
| **tổng** | **36/36** | **36/36** |

⛔ **KHÔNG được đọc bảng này là "chất lượng như nhau".** Cả hai đạt kịch trần
nghĩa là bộ đo ấy **không phân biệt được hai hồ sơ**. Nó chứng minh *không có
suy giảm thô trên workload của LTT* — đúng mục đích nó được viết ra, và là một
kết quả thật — nhưng một phép đo mà mọi ứng viên đều đạt 100 % thì **không còn
là phép đo** cho câu hỏi này.

⭐ Nên phải đo thêm đúng chỗ KV lượng hoá làm hỏng **trước tiên**: KV lượng hoá
làm nhoè attention, và thứ lộ ra đầu tiên là những token **không ở hai đầu** —
đầu prompt được attention neo mạnh, cuối prompt thì vừa mới đọc.

🔴 Và điều đó có nghĩa bộ kiểm sentinel đầu-cuối ở §3 **bỏ qua đúng vùng rủi ro
nhất**. Nó chốt "không cắt ngữ cảnh im lặng" rất tốt và chốt "không nhoè giữa
cửa sổ" **không chút nào** — hai mệnh đề khác nhau mà một phép kiểm dễ bị đọc
thành cả hai.

### Kim trong đống cỏ, 130K, năm độ sâu

Cùng `seed` ⇒ hai hồ sơ nhận **đúng cùng một prompt và cùng những cái kim**.
Hai lượt mỗi hồ sơ.

| | q8_0 (`qwen38-api` 131K) | q4_0 (`qwen38-ops` 200K) |
|---|---|---|
| kim đọc đúng (10 %, 30 %, 50 %, 70 %, 90 %) | **10/10** | **10/10** |
| giây mỗi lượt | 184,7 · 184,8 | 182,6 · 184,4 |

⚠️ Hoà, và hoà **ở kịch trần** — nên nói đúng mức: phép đo này **không tìm thấy**
suy giảm nào ở đúng vùng KV lượng hoá làm hỏng trước tiên. Nó **không** chứng
minh "hai hồ sơ như nhau"; một bộ đo mà mọi ứng viên đạt 100 % thì vẫn không
phân biệt được. Thứ nó loại trừ là *một suy giảm đủ lớn để đo thấy*, và đó đúng
là thứ đáng lo khi đổi KV.

⭐ Hiện vật thô + chính hai công cụ đo: `do_ngu_canh_2026-09-03/`.

---

## 6. Cái giá phải nói ra

Prefill chậm dần theo ngữ cảnh (1.005 → 639 tok/s từ 50K lên 165K). Ở 165K,
**byte đầu tiên tới sau 258 giây**.

Nhưng đó là giá của một prefix **lạnh**. Trong một phiên agent thật, prefix ổn
định và llama.cpp tái dùng KV — chỉ phần mới phải prefill. Lượt đắt là lượt
**ngay sau khi nén**, vì nén viết lại toàn bộ lịch sử.

⇒ Nâng cửa sổ **giảm số lần** phải trả cái giá đó (nén thưa hơn), đồng thời làm
**mỗi lần** đắt hơn. Đây là một đánh đổi thật, không phải một chiều thắng.

---

## 7. Quyết định

### D-1 — Ngưỡng nén của client: **dẫn xuất, không phải tỉ lệ** ✅ ĐÃ LÀM

| | |
|---|---|
| **Câu hỏi** | Client phải nén ở đâu để không bao giờ chạm trần? |
| **Bằng chứng** | Sự cố 413 ở 101.938 / 96.256. Với `× 0,8` khoảng trống là 25.412 < 32.768 = một lượt sinh dài nhất |
| **Chọn** | `nen_cua(m) = cong_bo_cua(m) − TOKEN_RA_TRAN` |
| **Vì sao** | Client chỉ kiểm ngưỡng **giữa hai lượt**; khoảng trống phải chứa trọn một lượt nữa |
| **Đảo lại được** | Có — một hàm, một dòng, có phép kiểm hai chiều |

### D-2 — Cửa sổ vision: **riêng, không dùng chung** ✅ ĐÃ LÀM

`ltt_llm_vision` khai 28.262 chứ không phải 88.555. Và khi quy tắc D-1 không cho
ngưỡng nào dương (28.262 < 32.768), bộ cài **bỏ hẳn** trường ngưỡng nén thay vì
ghi một con số bịa.

⭐ Đây là một sự thật khó chịu mà D-1 làm lộ ra, không phải một lỗi D-1 tạo ra:
**`qwen38-vision` dành hơn một nửa cửa sổ của nó cho `TOKEN_RA_TRAN`.** Nó là
model để đọc một tấm ảnh, không phải để chạy một phiên agent dài — và nay hợp
đồng nói đúng điều đó thay vì hứa ngược lại. *(Nợ mở: xem §8.)*

### D-0 — 🟢 CHỐT: engine lên **204.800**, KV `q4_0`

```
cua so engine   131.072  ->  204.800      (llama-swap.yaml, KV q8_0 -> q4_0)
tran vao         96.256  ->  169.984      (gateway.env + config.py + deploy.ps1)
cong bo client   88.555  ->  156.385      (hai bo cai + examples.py)
nguong nen       55.787  ->  123.617
```

**Vì sao dám chốt** — bốn phép đo độc lập, tất cả trên đúng card đang phục vụ:

| Câu hỏi | Trả lời | Bằng chứng |
|---|---|---|
| Có vừa VRAM không? | Vừa, và **tốn ít hơn** hồ sơ cũ | 21.979 vs 22.017 MiB |
| Có chậm hơn không? | Không, ở mọi mốc chung | §3 |
| Có cắt ngữ cảnh im lặng không? | Không | mốc đầu-cuối đúng ở mọi lượt |
| KV `q4_0` có làm dốt đi không? | Không đo thấy | 36/36 và 10/10 kim, §5b |

⭐ Và điểm quan trọng nhất: **trần 169.984 nằm BÊN TRONG vùng đã chạy thật**
(179.902 token), không ở mép nó. Ta không bán tới giới hạn đã đo — ta bán thấp
hơn nó 10 nghìn token.

⛔ **Cái này KHÔNG phải "đạt mục tiêu 200K"**. 204.800 là cửa sổ *engine*; thứ
khách nhét vào được là **156.385**. Gọi sản phẩm này là "200K context" đúng theo
cách mọi hãng khác gọi, và sai theo cách dự án này đã bốn lần trả giá.

### D-3 — Engine `204800` hay `200000`?

**`204800`.** Không phải vì tròn hơn mà vì **đó là con số đã được đo**: hồ sơ
`qwen38-ops` chạy `-c 204800` từ trước, và mọi số ở §3 đo trên đúng nó. `200000`
là một cấu hình **chưa ai chạy lần nào** — chọn nó là đổi một con số có bằng
chứng lấy một con số nghe cho tròn.

### D-4 — Nếu nâng, thì nâng **`qwen38-api`**, không trỏ bí danh sang `qwen38-ops`

Vì §4: llama-swap **giết một lượt đang chạy** để nạp hồ sơ khác. Hai hồ sơ text
cùng mở ra cho khách = một nguồn `ConnectionReset` ngẫu nhiên không giải thích
được. Một hồ sơ text công khai, một tệp `-c`, một sự thật.

### D-5 — 🔴 THỨ TỰ DEPLOY, và vì sao đảo thứ tự là hỏng im lặng

Ba thứ phải đổi, và **thứ tự của chúng không hoán vị được**:

```
1. llama-swap.yaml  -c 204800  +  RESTART LTTLlamaSwap   (may B)
2. gateway.env      LTT_LLM_MAX_INPUT_TOKENS             (may B)
3. ngan_sach.py     CUA_SO_MODEL                          (may A)
```

⛔ **Bước 1 trước bước 2.** Nếu trần của cổng B lên 169.984 trong khi
`llama-server` vẫn chạy `-c 131072`, thì cổng **nhận** một yêu cầu 150K rồi
llama-server **cắt bớt ngữ cảnh** — đúng thứ tệ nhất: không lỗi, không 413, chỉ
là một câu trả lời thiếu mất phần đầu prompt.

⛔ **Bước 2 trước bước 3.** Máy B phải luôn **rộng hơn hoặc bằng** máy A. Ngược
lại thì máy A cho qua thứ máy B từ chối, và khách nhận 413 từ một tầng sâu hơn
tầng có thông điệp tốt.

⚠️ **`deploy.ps1` chép `llama-swap.yaml` mà KHÔNG restart `LTTLlamaSwap`** —
khuyết tật D-03-5 của audit 31/08, vẫn mở. Nên bước 1 phải restart **bằng tay**,
và phải xác minh bằng `/running` chứ không bằng tệp trên đĩa.

⚠️ Và `deploy.ps1` **ghi đè** `LTT_LLM_MAX_INPUT_TOKENS` ở ba chỗ bằng số gõ
tay. `test_334::test_deploy_ps1_KHONG_lui_tran_cua_may_B` nay chốt điều đó —
trước 03/09 không có gì chốt, nên một lần deploy không liên quan sẽ lặng lẽ lùi
trần về cũ.

---

## 8. Còn nợ — nói ra, không giấu

| # | Nợ | Vì sao chưa đóng |
|---|---|---|
| N-1 | **Chưa deploy.** Máy B vẫn `-c 131072` | Cần cửa sổ deploy; một phiên khác đang dùng production. Thứ tự ở §7 D-5 |
| N-2 | **Canary phiên dài với khoá thật** — Codex/Claude chạy tới ngưỡng nén rồi nén, quan sát bằng log | Cần một khoá API sống. Bộ kiểm đọc tệp khoá bị chặn ở phiên này ⇒ chỉ chạy được canary **cấu hình** (§4c), không chạy được canary **hành vi** |
| N-3 | **Lượt sinh dài ở cuối cửa sổ chưa đo sạch.** Lượt 160K/8192 trả `finish_reason: stop` sau 122 token vì đề bài chỉ đòi một dòng | Nó chứng minh request được NHẬN, không chứng minh decode còn khoẻ ở cuối cửa sổ. Đã sửa đề bài trong `bench_ctx.py` nhưng chưa chạy lại |
| N-4 | **`qwen38-vision` chưa đo lại**, và cửa sổ công bố của nó (28.262) **hẹp hơn** một lượt sinh dài nhất (32.768) | Nó dành hơn nửa cửa sổ cho `TOKEN_RA_TRAN`. Không ngưỡng nén nào giữ được lời hứa ⇒ bộ cài bỏ hẳn trường đó. Sửa thật là đo lại vision hoặc cho nó trần ra riêng |
| N-5 | **`deploy.ps1` không restart `LTTLlamaSwap`** (D-03-5, audit 31/08) | Chưa chạm tới `deploy.ps1` ngoài ba con số. Cho tới khi sửa, bước 1 của §7 D-5 phải làm tay |
| N-6 | **Hai bộ đo chất lượng đều hoà ở kịch trần** | Chúng loại trừ một suy giảm đủ lớn để đo thấy. Muốn nhạy hơn thì cần bộ đề khó hơn, và đó là một việc riêng |
| ~~N-7~~ | ~~`LTT_PUBLIC_API_MAX_BODY_BYTES` thật trên production~~ | ✅ **ĐÓNG 03/09.** Biến **không** được đặt ở đâu cả: `AppEnvironmentExtra` của dịch vụ `LTTStudioWeb` liệt kê 71 biến và không có nó, và service env chính là thứ `2-cai-dat.ps1` nạp từ `app.env`. ⇒ production dùng mặc định **1 MiB**, đủ cho 747 KB cần thiết. *(Đọc TÊN biến từ registry, không đọc giá trị — không có bí mật nào bị in ra.)* |
| **N-8** | 🔴 **Chốt "cây đứng yên" của gate KHÔNG soi `llm_gateway/` và `sdk/`** | Tìm ra 03/09. `gate._anh_chup_cay()` chỉ chụp `apps, platform_core, server, tools, tests, alembic, locale`. Chương trình này sửa **10** thư mục, và **năm** trong số đó (`docs`, `frontend`, `llm_gateway`, `sdk`, `ho_so_he_thong.txt`) nằm ngoài ảnh chụp.<br><br>⛔ Nghĩa là sửa mã **cổng máy B** hoặc **bộ cài khách** ngay giữa một lượt gate thì `CAY DA DOI TRONG LUC CHAY` **không kêu**, và dòng `RESULT: PASS` nói về một cây đã không còn tồn tại. Cùng một họ với `banh-coc-chi-bao-ve-thu-no-nhin-thay`.<br><br>⭐ Và tôi phát hiện nó theo đường ngược: tôi sửa một tệp `docs/` giữa lượt gate, **tưởng** mình vừa làm mất lượt đó, rồi đọc `_anh_chup_cay()` để xác nhận — và thấy điều tệ hơn là thứ tôi lo. |
