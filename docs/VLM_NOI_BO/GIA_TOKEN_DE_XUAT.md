# Giá token cho API model nhà — nghiên cứu và giá đã chốt

**2026-08-22.** ✅ **ĐÃ CHỐT** — chủ dự án duyệt đúng mức đề xuất ở §4.

```
Token vao (phai prefill that)   ....   50 credit / 1.000.000 token
Token vao lay lai tu cache      ....   10 credit / 1.000.000 token
Token ra (ke ca reasoning)      ....  400 credit / 1.000.000 token
```

Đã vào mã: **`platform_core/llm/gia_token.py`**, nhãn phiên bản giá
`ltt-vlm-2026-08-22`, test **`tests/test_252_gia_token.py` 18/18 xanh**.

Ba điều về cách cài đặt, đáng đọc trước khi sửa gì:

- **Tính bằng milli-credit (1/1.000 credit = 0,1đ), toàn số nguyên, không float.**
  Một lượt gọi điển hình tốn 0,3 credit — không biểu diễn nổi bằng credit nguyên.
  Dấu phẩy động trong đường tiền là cách chắc nhất để hai lần cộng ra hai kết quả.
- **Làm tròn về credit nguyên là việc của tầng quyết toán, không phải của bảng giá.**
  Ranh giới có chủ ý: đổi cách làm tròn không được đụng vào giá.
- **Không đo được thì ném lỗi, không trả 0.** `KhongDoDuocError`. Một hoá đơn 0đ
  âm thầm là một lỗ hổng doanh thu im lặng.

✅ **C1 ĐÃ CHỐT** (§3) — làm tròn **LÊN** credit nguyên mỗi lượt gọi, tối thiểu
1 credit. Đã vào `platform_core/llm/thanh_toan.py`, test
`tests/test_253_thanh_toan_llm.py` **14/14 xanh**.

⚠️ **Cái giá của C1, và ta công bố nó chứ không giấu:** lượt gọi nhỏ trả nhiều hơn
giá niêm yết — lượt 0,3 credit bị thu 1 credit, tức **3,3 lần**. `bang_gia()` khai
thẳng `toi_thieu_moi_luot_credit = 1` và giải thích trong `ghi_chu`, có test neo.
Một khách gọi nhiều sẽ tự tính ra trong vòng một ngày; thà họ đọc được từ trước.

*(C2 — sổ tích luỹ phần lẻ — vẫn để ngỏ. Nó chỉ đụng `thanh_toan.py`, **không**
đụng `gia_token.py`. Ranh giới đó là có chủ ý.)*

---

*(Phần dưới giữ nguyên như lúc nghiên cứu, để về sau còn đọc được **vì sao** ra
những con số này.)*

Mọi giá thị trường dưới đây lấy từ bảng giá công khai đang chạy. Chi phí biên tính
từ **số điện đo thật trên máy B**, không phải ước lượng.

---

## 1. Ba mốc neo

### 1.1. Tỉ giá của nhà

`1 credit = 100đ` (Q31, `billing_math.VND_PER_CREDIT`). Gói mặc định hiện có:

| Gói | Giá | Credit gốc | Bonus | **Tổng** |
|---|---:|---:|---:|---:|
| 50K | 50.000đ | 500 | 0 % | 500 |
| 100K | 100.000đ | 1.000 | 5 % | 1.050 |
| 200K | 200.000đ | 2.000 | 10 % | 2.200 |
| **500K** | 500.000đ | 5.000 | 15 % | **5.750** |
| 1 triệu | 1.000.000đ | 10.000 | 20 % | 12.000 |

Tỉ giá USD ngày 21/08/2026: **1 USD ≈ 26.300đ ⇒ 1 USD ≈ 263 credit.**

### 1.2. Giá thị trường của **đúng model này**

Đây là mốc neo quan trọng nhất — không phải so với model khác, mà so với **cùng
Qwen3.8-27B** ở nơi khác:

| Nơi bán | Model | Vào $/M | Ra $/M | **Vào credit/M** | **Ra credit/M** |
|---|---|---:|---:|---:|---:|
| **OpenRouter** | **Qwen3.8-27B** | **0,40** | **3,00** | **105** | **789** |
| OpenRouter | Qwen3.6-27B | 0,30 | 2,00 | 79 | 526 |
| Morph (rẻ nhất nhóm 27B) | Qwen3.6-27B | 0,289 | — | 76 | — |
| DeepInfra | Qwen3-32B (đời cũ) | 0,08 | 0,28 | 21 | 74 |

### 1.3. Giá của thứ khách có thể dùng thay

| Model | Vào $/M | Ra $/M | Vào credit/M | Ra credit/M |
|---|---:|---:|---:|---:|
| Gemini 3 Flash | 0,25 | 1,50 | 66 | 395 |
| Gemini 3.7 Flash | 0,38 | 1,88 | 100 | 494 |
| Gemini 3.5 Flash-Lite | 0,15 | 1,25 | 39 | 329 |

---

## 2. Chi phí biên thật của ta — tính từ số đo

**Số đo:** máy B lúc chạy tiêu **358,65 W** (`nvidia-smi`, P0).
**Giả định phải xác minh:** điện **3.000đ/kWh**. *(Bậc thang EVN — chủ dự án đối
chiếu hoá đơn thật rồi sửa lại con số này.)*

```
0,359 kW x 3.000 d/kWh = 1.077 d moi gio GPU chay
```

| Loại token | Tốc độ (đo cộng đồng, đúng card) | Token/giờ | **Chi phí điện/1M token** |
|---|---:|---:|---:|
| **Ra** (decode, MTP n=2, 64K) | ~60 tok/s | 216.000 | **~4.985đ = ~50 credit** |
| **Vào** (prefill) | ~1.000 tok/s | 3.600.000 | **~299đ = ~3 credit** |

Hai điều phải nói rõ:

- ⚠️ **Chưa tính khấu hao card.** 3090 đã mua rồi (chi phí chìm), nhưng nếu tính
  thay thế thì phải cộng thêm.
- ⚠️ **Token ra đắt hơn token vào ~17 lần.** Đó không phải chính sách giá — đó là
  vật lý: decode đọc toàn bộ trọng số cho **mỗi** token, prefill xử lý cả lô một lượt.
  Mọi bảng giá LLM trên thị trường đều phản ánh đúng tỉ lệ này.

---

## 3. 🔴 Vấn đề kỹ thuật phải giải TRƯỚC khi chốt giá

**Credit là số nguyên, còn một lời gọi LLM tốn một phần nhỏ của credit.**

Ví dụ một lượt bot điển hình — 2.000 token vào, 500 token ra — ở mức giá đề xuất ở
§4 tốn **0,3 credit = 30đ**. Nhưng `credit.tru()` và `credit.giu_cho()` nhận **số
nguyên**. Ảnh và video không gặp chuyện này vì một job tốn vài credit trở lên.

Ba đường ra:

| | Cách | Được | Mất |
|---|---|---|---|
| **C1** | **Ngưỡng tối thiểu 1 credit/lời gọi** | Không đụng sổ cái. Làm được ngay | Thu vượt tới **3 lần** với lời gọi nhỏ. Khách gọi nhiều sẽ tự tính ra và thấy |
| **C2** ⭐ | **Sổ tích luỹ phân số** — cộng dồn chi phí lẻ theo tài khoản, trừ credit nguyên khi vượt 1 | **Đúng giá**, chuẩn ngành. Thêm một cột, không đổi đơn vị | Phải viết và test |
| **C3** | Đổi đơn vị credit (1 credit = 10đ) | Hết vấn đề | Đụng Q31, trang nạp, PayOS, mọi gói đã bán. **Không nên** |

**Đề xuất: C2.** C1 dùng tạm cho lần mở đầu nếu cần ra mắt sớm, và nói rõ trong tài
liệu API là có ngưỡng tối thiểu — đừng để khách tự phát hiện.

---

## 4. ĐỀ XUẤT GIÁ

Neo vào **giá cùng model trên OpenRouter**, cắt khoảng một nửa, và vẫn cao hơn chi
phí điện nhiều lần:

| | **Đề xuất** | ≈ USD/1M | So OpenRouter | So chi phí điện |
|---|---:|---:|---:|---:|
| **Token vào** | **50 credit / 1M** | $0,19 | **−52 %** | **16×** |
| **Token vào lấy từ cache** | **10 credit / 1M** | $0,038 | — | — |
| **Token ra** | **400 credit / 1M** | $1,52 | **−49 %** | **8×** |

### Vì sao ba con số này

- **Rẻ hơn OpenRouter một nửa** cho **cùng một model** — đó là lý do khách chọn ta.
- **Vẫn lãi gộp 8× trên token ra**, phần đắt nhất. Biên đủ dày để chịu được việc
  card dùng chung và có lúc không chạy.
- **Token cache tính 20 %** vì nó gần như miễn phí thật: llama-server báo
  `timings.cache_n`, và phần đó **không chạy prefill lại**. Bot gọi lặp cùng system
  prompt — tính đủ giá cho phần đó là **tính tiền khách hai lần cho cùng một thứ**.
  20 % là mức thị trường đang dùng cho cached input.

### Khách nhận được gì với 500.000đ

500.000đ → **5.750 credit**.

| Kiểu dùng | Giả định | Được bao nhiêu |
|---|---|---|
| Chỉ tính token ra | — | **~14,4 triệu token ra** |
| Bot hội thoại | 2.000 vào + 500 ra mỗi lượt | **~19.000 lượt gọi** |
| Trợ lý code | 8.000 vào + 1.500 ra mỗi lượt | **~5.700 lượt gọi** |
| Trợ lý code có cache | 8.000 vào (80 % cache) + 1.500 ra | **~8.600 lượt gọi** |

---

## 5. ⚠️ Một cái bẫy giá mà cascade tạo ra

Nếu máy B bận và ta **âm thầm chuyển sang Gemini**, ta trả giá Gemini nhưng thu giá
của mình:

| | Ta thu | Gemini 3 Flash lấy của ta | Lãi |
|---|---:|---:|---:|
| Token vào | 50 | **66** | 🔴 **−16 (lỗ)** |
| Token ra | 400 | 395 | +5 (≈ hoà) |

⇒ **Ở mức giá này, mỗi lượt cascade sang Gemini Flash là một lượt LỖ.**

Nhưng đừng sửa bằng cách nâng giá hay đổi sang model rẻ hơn — **`D-010` đã cấm**:
*đổi model sau lưng khách là đánh tráo sản phẩm.* Với một API bán ra ngoài thì điều
đó còn nặng hơn: khách trả tiền cho **Qwen3.8-27B**, nhận về Gemini mà không biết.

**Cách đúng, và nó cũng xoá luôn vấn đề lãi lỗ:**

> Máy B bận ⇒ trả **429 + `Retry-After`**. Không cascade âm thầm.
> Khách muốn có đường lui thì **tự khai** (`fallback_model`), và khi đó **tính theo
> giá của model lui**.

Đây đúng thứ `llm_gateway/api.py` đã làm sẵn, và đúng thứ `test_250` đang neo.

---

## 6. Bốn câu chốt lại

| # | Câu | Đề xuất của tôi |
|---|---|---|
| 1 | Giá token vào / ra | **50 / 400 credit mỗi 1M** |
| 2 | Token cache tính bao nhiêu | **20 % giá vào = 10 credit/1M** |
| 3 | Token reasoning có tính không | **CÓ, tính như token ra** — nó tiêu GPU y hệt. Template đã vá mặc định `medium` nên phần này không phình. Phải **nói rõ trong tài liệu API**, đừng để khách phát hiện sau |
| 4 | Khách ngắt giữa stream | **Tính phần đã sinh, hoàn phần còn lại.** `credit.giu_cho → quyet_toan → hoan` làm sẵn việc này |

Và một câu kỹ thuật: **chọn C1 hay C2 ở §3.**

---

## 7. Số cần xác minh trước khi chốt

| # | Số | Hiện là | Cách xác minh |
|---|---|---|---|
| 1 | Giá điện đ/kWh | **giả định 3.000** | hoá đơn EVN thật |
| 2 | Tốc độ decode thật của máy B | mượn cộng đồng ~60 tok/s | **P5** |
| 3 | Tốc độ prefill thật | mượn ~1.000 tok/s | **P5** — và nó cũng quyết trần Cloudflare |
| 4 | Tỉ lệ cache thật của lưu lượng | chưa biết | đo sau khi có khách thật |

⚠️ Nếu P5 đo ra decode **thấp hơn nhiều** so với 60 tok/s thì chi phí điện trên mỗi
token ra tăng tỉ lệ nghịch, và biên 8× hẹp lại. **Chốt giá sau P5 thì an toàn hơn**;
chốt trước cũng được vì biên đang rất dày.

---

## 8. Nguồn

- Qwen3.8-27B trên OpenRouter: https://openrouter.ai/qwen/qwen3.8-27b
- Qwen3.6-27B trên OpenRouter: https://openrouter.ai/qwen/qwen3.6-27b
- So giá theo model/nhà cung cấp: https://pricepertoken.com/pricing-page/model/qwen-qwen3.6-27b
- Qwen3-32B (đời cũ, DeepInfra): https://pricepertoken.com/pricing-page/model/qwen-qwen3-32b
- Giá Gemini: https://pricepertoken.com/pricing-page/model/google-gemini-3-flash-preview
- Tỉ giá USD/VND 21/08/2026: https://cafef.vn/du-lieu/ty-gia-ngoai-te.chn
