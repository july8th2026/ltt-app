# Phân tích toàn diện — cơ chế vận hành, chi phí, và đường lên MVP thật

**2026-08-23** · phạm vi: chuỗi khoá API · giá vốn · cơ chế nền tảng · hệ model nội bộ
· chấm điểm · phương án MVP

> ## ⛔ ĐỌC MỤC 2 TRƯỚC MỌI THỨ KHÁC
>
> **Nền tảng đang bán ảnh dưới giá vốn, mọi bậc, khoảng 45–57 % giá vốn.** Không
> phải sai một chỗ nhỏ — sai ở cả bốn model đang mở. Bán càng nhiều lỗ càng lớn,
> và khách mua gói lớn (bonus 20 %) làm lỗ nặng thêm.
>
> Đây không phải suy đoán: giá vốn lấy từ bảng giá công bố của nhà cung cấp, giá bán
> đọc từ `apps/taoanh/manifest.py` đang chạy trên production.

---

## 1. Chuỗi khoá API hoạt động như thế nào

### 1.1 Bốn tầng, mỗi tầng một việc

```
app gọi lay_key(db, "gemini", category="image", model="gemini-3-pro-image")
   │
   ├─ ① api_pool.chon_key   CHỌN khoá nào  (lọc → xếp hạng → tăng bộ đếm)
   ├─ ② api_keys.lay_credential   GIẢI MÃ khoá ra chuỗi thật
   ├─ ③  ... app gọi nhà cung cấp ...
   └─ ④ danh_dau_thanh_cong / danh_dau_loi   GHI LẠI kết quả
```

### 1.2 ① Chọn khoá — lọc trước, xếp sau

`_ung_vien()` loại bỏ theo thứ tự:

| Bước | Loại khoá nào |
|---|---|
| `enabled = False` | khoá đã tắt hẳn |
| cooldown chưa hết | *(tự hồi về `active` khi `cooldown_until` đã qua — không cần cron)* |
| `status != active` | khoá đang `error`/`disabled` |
| `category` không khớp | khoá chỉ dành cho `text` không phục vụ `image` |
| `supported_models` không chứa model | khoá không có quyền gọi model đó |
| **chạm `rpm_limit` / `tpm_limit`** | trong cửa sổ 60 giây hiện tại |

Còn lại thì `chon_key()` xếp theo **năm khoá thứ tự**:

```
(thứ tự provider) → −priority → −health_score → window_requests → total_requests
```

Ba tiêu chí đầu là **ý muốn của người vận hành**; hai tiêu chí cuối là **cân tải** —
khoá vừa dùng nhiều thì lùi lại.

### 1.3 ② Bảo mật khoá

Khoá **không bao giờ nằm dạng chữ trong CSDL**: `api_keys.dat_credential()` mã hoá
bằng `LTT_TOKEN_ENCRYPTION_KEY` (ở `secrets/app.env`, không commit). Mất khoá đó là
mất toàn bộ credential đã lưu.

### 1.4 ④ Phân loại lỗi — chỗ này sai là **tự tắt hệ thống**

| Mã trả về | Nền tảng làm gì | Vì sao |
|---|---|---|
| **401 / 403** | `auth_error_count++`, **DISABLE sau 5 lần liên tiếp** | khoá hỏng thật; để nó tiếp tục thì mọi request đều chết |
| **429** | cooldown theo `Retry-After` | hết hạn mức là tạm thời, không phải hỏng |
| **4xx khác** | **KHÔNG phạt khoá** | đó là **lỗi của ta** — prompt sai cú pháp. Thử khoá khác cũng hỏng y hệt |
| **5xx / mạng** | `error_count++`, chuyển `error` sau 5 lần | có thể là nhà cung cấp, có thể là mạng |

⛔ **Đây là chỗ tôi đã phải cẩn thận nhất khi nối model nhà.** `ltt_image` trả **429
khi máy B bận** — mà bận là trạng thái **bình thường** (máy chia GPU với hai dự án
khác). Nếu `429` bị tính là lỗi thì sau 5 lần dự án video chạy buổi tối, khoá model
nhà **tự tắt vĩnh viễn**. `apps/anhnoibo/http_cong.py` vì thế **không gọi
`danh_dau_loi` cho 429**, và có test chốt điều đó.

### 1.5 Cascade đa-provider

`chon_key(category="image", thu_tu_provider=["ltt_image", "gemini"])` gom khoá của
**mọi** provider phục vụ `image`. Một provider cạn khoá **không làm chết cả loại**.

⚠️ **Nhưng hôm nay chưa app nào dùng cascade.** `apps/taoanh` và `apps/thumbnail` gọi
`lay_key(db, "gemini")` — một provider cứng. Đó là lý do §5 xếp "định tuyến" là
hạng mục còn thiếu.

---

## 2. ⛔ Bảng chi phí vận hành — **chưa có cho ảnh, và hậu quả đã hiện ra**

### 2.1 Hiện trạng

| Miền | Bảng giá vốn | Nguồn |
|---|---|---|
| **LLM (H38)** | ✅ **có, chặt chẽ** | `platform_core/llm/gia_token.py` — credit/1M token, neo theo OpenRouter, đo điện thật, đóng dấu phiên bản giá |
| **Ảnh (H37 + Gemini)** | ❌ **không có** | `CREDIT_PER_IMAGE = 5` — một hằng số **không có cơ sở chi phí nào** |
| **Video** | ❌ không có | |

Và bộ đo chi phí `platform_core/public_api/costing.py` **có tồn tại, có nối vào
worker** — nhưng **production chưa đặt một suất giá nào** (`LTT_COST_MICROS_PER_*`
đều vắng). Nên nó **không ghi gì cả**, và bảng biên lợi nhuận trong admin trống.

⛔ Tệ hơn: `RATE_ENV` chỉ có ba loại — **thời lượng, byte, token**. **Không có loại
"chi phí nhà cung cấp mỗi ảnh"**. Nghĩa là khoản chi lớn nhất của mảng ảnh
**không đo được về mặt cấu trúc**, dù có cấu hình đầy đủ. Đó là lý do lỗ này chạy
suốt mà không ai thấy.

### 2.2 Bảng giá thị trường (tra 23/08/2026)

Tỉ giá **26.300đ/USD** — dùng đúng con số `gia_token.py` đã chốt. **1 credit = 100đ**.

| Alias | Model | **Ta bán** | Giá vốn | **Bán/Vốn** | Lỗ mỗi ảnh |
|---|---|---|---|---|---|
| `standard` | gemini-2.5-flash-image | **5 cr** = 500đ | $0,039 = **1.026đ** | **49 %** | **−526đ** |
| `standard-lite` | gemini-3.1-flash-lite-image | **5 cr** = 500đ | $0,0336 = **884đ** | **57 %** | **−384đ** |
| `enhanced` | gemini-3.1-flash-image | **8 cr** = 800đ | $0,067 = **1.762đ** | **45 %** | **−962đ** |
| `pro` | gemini-3-pro-image | **16 cr** = 1.600đ | $0,134 = **3.524đ** | **45 %** | **−1.924đ** |

**Gói nạp có bonus tới 20 %** (gói 1 triệu), nên doanh thu thực chỉ **83,3đ/credit**.
Lỗ thật ở bậc `pro` là **−2.191đ mỗi ảnh**.

### 2.3 Giá hoà vốn

| Alias | Hoà vốn (0 % bonus) | Hoà vốn (20 % bonus) | Đang bán |
|---|---|---|---|
| `standard` | 10,3 cr | **12,3 cr** | 5 |
| `standard-lite` | 8,8 cr | **10,6 cr** | 5 |
| `enhanced` | 17,6 cr | **21,1 cr** | 8 |
| `pro` | 35,2 cr | **42,3 cr** | 16 |

### 2.4 Và đây là chỗ H37 đổi từ "dự án hay" thành "dự án cần thiết"

Đo thật trên máy B, cộng khấu hao (RTX 3090 ~25 triệu, 3 năm × 8 h/ngày):

| Chế độ | Điện | Khấu hao GPU | **Tổng** |
|---|---|---|---|
| t2i 50 bước (96 s) | 28,7đ | 76,1đ | **104,8đ = 1,05 credit** |
| có ảnh tham chiếu (190 s) | 56,8đ | 150,6đ | **207,4đ = 2,07 credit** |

⭐ **Model nhà rẻ hơn Gemini 3 Pro Image 34 lần.**

Nghĩa là H37 không phải một tính năng thêm — nó là **lối thoát của bài toán đơn vị
kinh tế**. Giá 5 credit hiện tại **lỗ** khi chạy qua Gemini, nhưng **lãi ~4,8 lần**
khi chạy qua model nhà.

*(Ghi rõ giới hạn: khấu hao dùng giả định 3 năm × 8 h/ngày và giá điện 3.000đ/kWh —
cùng giả định `gia_token.py` đã dùng. Đổi giả định thì đổi số, nhưng bậc độ lớn
34 lần không đảo được.)*

---

## 3. Cơ chế vận hành LTTSTUDIOSAPP — bản đồ thật

### 3.1 Sáu tầng

```
① Vỏ (server/)        HTTP, phiên, CSRF, template, /api/v1
② Registry            quét apps/*/manifest.py — nền tảng KHÔNG biết tên app nào
③ Hàng đợi job        giữ chỗ credit → worker chạy → quyết toán / hoàn
④ Sổ credit           giu_cho → quyet_toan → hoan, idempotent theo job
⑤ APIKEYS             chọn khoá, telemetry rpm/tpm, phân loại lỗi (§1)
⑥ App (apps/<slug>/)  manifest + jobs + routes — thêm app = thêm MỘT thư mục
```

**Điểm mạnh thật sự của kiến trúc này:** nền tảng không hardcode tên app nào; có
test (`test_60`) quét `platform_core/` để chặn việc đó. Thêm app thứ 19 không phải
sửa nền tảng — điều này **đã được kiểm chứng ba lần trong một tuần** (`anhnoibo`,
`ltt_llm`, `vps` cùng vào mà không đụng lõi).

### 3.2 Ba cổng fail-closed của Public API (Q92)

```
api_exposed=True  ∧  LTT_PUBLIC_API=1  ∧  tên ∈ LTT_PUBLIC_API_TOOLS
```

Thiếu một là tool không ra. Đã **kiểm trên production 22/08**: thêm `image.ltt` với
`api_exposed=True` mà `/api/v1/tools` vẫn trả 401 và catalog rỗng.

### 3.3 Nơi tiền đi qua

```
báo giá (POST /quotes)  →  ký, gắn phiên bản giá, hạn 
   → tạo job (POST /jobs)  →  GIỮ credit  →  worker chạy
      → xong: quyết toán (không bao giờ thu quá phần đã giữ)
      → hỏng: hoàn đủ, idempotent
```

⭐ Thiết kế này **đúng** và là phần chắc nhất của hệ thống. Vấn đề không nằm ở cơ
chế thu tiền — nó nằm ở **con số** được đưa vào cơ chế đó (§2).

---

## 4. Hệ model nội bộ (H37) — phân tích toàn diện

### 4.1 Dây chuyền, từ khách tới GPU

```
khách → /api/v1 → quote → job → worker
  └─ apps/anhnoibo/jobs.py
       ├─ kiểm tham số + kiểm CHỦ SỞ HỮU ảnh tham chiếu
       ├─ platform_core/image_gen/dieu_phoi.py
       │    ├─ prompt_dich   dịch sang tiếng Anh (model chỉ hiểu EN/ZH)
       │    ├─ storage       presigned GET (ảnh vào) + PUT (ảnh ra)
       │    └─ cong_render   gửi máy B, chờ, nhận khoá R2
       └─ apps/anhnoibo/http_cong.py  → bearer token qua APIKEYS
                                          ↓
   máy B: render_gateway (:8199) → ngân sách token → busy → ComfyUI (:8188, chỉ 127.0.0.1)
```

### 4.2 Bảy quyết định nền, và vì sao mỗi cái đúng

| # | Quyết định | Nếu làm ngược |
|---|---|---|
| 1 | Model nhà là **provider**, không phải app | mỗi app ảnh phải chép lại đường gọi |
| 2 | Máy B **không giữ bí mật nào** — ảnh vào/ra bằng presigned URL | một máy để bàn dùng chung trở thành điểm rò khoá R2 |
| 3 | **Dịch prompt trước** | model vẫn vẽ, chỉ là vẽ sai hoàn toàn, **không lỗi nào báo** |
| 4 | **Bận ≠ hỏng** — `BanError` đi thẳng ra ngoài | khách nghe "thất bại" trong khi sự thật là "chờ 10 phút" |
| 5 | **Không cascade ngầm sang đám mây** | đổi model sau lưng khách là đánh tráo sản phẩm |
| 6 | **Chưa đo thì không chạy** (`ngan_sach.py` chặn trước khi chạm GPU) | OOM giữa lô, mất cả lô |
| 7 | ComfyUI **vĩnh viễn chỉ nghe 127.0.0.1** | ComfyUI không có xác thực; lộ ra LAN là mở toang |

### 4.3 Ba lỗ đã tìm và bịt trong 24 h qua

| Lỗ | Phát hiện thế nào | Nếu để lọt |
|---|---|---|
| Chốt dò bận đếm **tiến trình python** | `llama-server.exe` giữ 15,9 GB mà không phải python | nhận job khi card còn 4,6 GB ⇒ OOM im lặng |
| Lô so mù **không mù** (3 dấu vết) | dựng bước chuẩn hoá thì lộ ra | một con số thắng-thua **vô nghĩa nhưng nghe rất thuyết phục** |
| Ghi ảnh Gemini sai định dạng | dòng in có in kích thước | thiên lệch 1,86 lần đi thẳng vào kết luận |

⭐ Cả ba có chung một tính chất: **không cái nào nhìn thấy được từ kết quả**. Hệ vẫn
chạy, ảnh vẫn ra, số vẫn có. Đó là loại lỗi đắt nhất.

---

## 5. Chấm điểm

Thang 10. **Điểm cho thứ đang chạy được và chứng minh được**, không cho ý định.

| # | Hạng mục | Điểm | Căn cứ |
|---|---|---|---|
| 1 | **Kiến trúc app / registry** | **9,5** | 3 app mới vào cùng tuần, 0 dòng sửa lõi; có test chặn hardcode |
| 2 | **Sổ credit (giữ→quyết toán→hoàn)** | **9,0** | idempotent, có khoá theo user, không thu quá phần giữ |
| 3 | **Chuỗi khoá APIKEYS** | **8,5** | phân loại lỗi đúng 4 nhánh, telemetry rpm/tpm, cascade **có nhưng chưa ai dùng** |
| 4 | **Public API `/api/v1`** | **9,0** | 24 route đóng băng, fail-closed đã kiểm trên production, E2E bằng khoá thử |
| 5 | **Hạ tầng H37 (cổng render, điều phối, dịch)** | **8,5** | dây chuyền liền mạch, 300+ test, deploy thật, chốt dò bận đã sửa |
| 6 | **Kỷ luật đo đạc / chống tự lừa** | **8,0** | so mù có cặp bẫy + sàn nhiễu; 3 lỗ mù tự tìm ra và bịt |
| 7 | **Chất lượng model nhà** | **chưa chấm** | G6b chưa chạy — **không được đoán** |
| 8 | **Quan sát vận hành (log, metrics, cảnh báo)** | **5,0** | có log + outbox; **chưa có cảnh báo chủ động**, chưa có bảng sức khoẻ |
| 9 | ⛔ **Giá & giá vốn** | **2,0** | bán dưới giá vốn ở **cả bốn** bậc; không bảng giá vốn cho ảnh |
| 10 | ⛔ **Đo chi phí thực tế** | **1,5** | máy đo có, **không suất giá nào được cấu hình**, và **không có loại "chi phí nhà cung cấp"** |
| 11 | **Phối hợp nhiều phiên làm việc** | **3,0** | 3 phiên trùng số test 250–258; `providers.py` bị hai phiên cùng sửa |
| | **Trung bình có trọng số** | **≈ 6,4** | kỹ thuật rất chắc, **kinh tế đơn vị đang âm** |

**Câu một dòng:** đây là một nền tảng **kỹ thuật tốt hơn mức MVP** đang chạy trên
một **mô hình kinh doanh lỗ ở mọi đơn hàng**.

---

## 6. Phương án lên MVP thật

Xếp theo **thứ tự bắt buộc**, không phải theo độ khó.

### Đợt 0 — CẦM MÁU *(1 buổi, không cần GPU, không cần deploy)*

| # | Việc | Vì sao trước tiên |
|---|---|---|
| 0.1 | **Dựng `platform_core/gia_von.py`** — một bảng giá vốn duy nhất cho **mọi** model ảnh, đơn vị **milli-credit, số nguyên**, có `PHIEN_BAN_GIA` | đúng khuôn `gia_token.py` đã chứng minh dùng được. Một chỗ, không hai |
| 0.2 | **Test chặn bán dưới giá vốn** — quét mọi `credit_cost` và so với `gia_von`; đỏ nếu giá bán < giá vốn | đây là bánh cóc quan trọng nhất của cả tài liệu này. Không có nó thì lỗi này quay lại |
| 0.3 | **Đặt lại giá** theo §2.3 + biên chủ dự án chọn | quyết định kinh doanh — tôi đưa số, chủ dự án chọn bội số |
| 0.4 | Thêm loại chi phí **`COST_PROVIDER_CALL`** vào `costing.RATE_ENV` | không có nó thì chi phí lớn nhất vĩnh viễn không đo được |

⚠️ 0.3 là **quyết định của chủ dự án**. Ba lựa chọn:
- **hoà vốn** (12,3 / 10,6 / 21,1 / 42,3 credit) — không lỗ, không lãi;
- **biên 40 %** (×1,67 giá vốn sau bonus) — 21 / 18 / 36 / 71 credit;
- **giữ giá, đóng bậc `pro`** — chấp nhận lỗ ở bậc rẻ như chi phí thu hút khách,
  nhưng **đóng đúng bậc lỗ nặng nhất**.

### Đợt 1 — MỞ MODEL NHÀ *(cần GPU; **máy chấm** từ D-052, 24/08)*

| # | Việc | Chặn bởi |
|---|---|---|
| 1.1 | Thêm khoá `ltt_image` vào APIKEYS | token ở máy B — **chủ dự án tự làm** |
| 1.2 | Chạy nửa ảnh model nhà cho G6b (~28 ảnh, 1,5 h) | GPU rảnh *(mốc 01:00 đã bỏ — lô đo nay tiếp tục được sau khởi động lại)* |
| 1.3 | Chuẩn hoá + dựng lô + **chấm mù** | 1.2 |
| 1.4 | Cổng quyết định: mở bán / mở hẹp / dừng | 1.3 |
| 1.5 | `is_active=True`, giá theo §2.4 (giá vốn **1,05 credit**) | 1.4 |

⭐ **Vì sao đợt này là lối thoát kinh tế:** ở giá hoà vốn Gemini (12,3 credit),
model nhà có giá vốn **1,05 credit** ⇒ biên **91 %**. Cùng một giá bán, cùng một
khách — khác nhau ở chỗ ảnh được vẽ ở đâu.

### Đợt 2 — ĐỊNH TUYẾN *(sau khi có kết quả G6b)*

| # | Việc |
|---|---|
| 2.1 | Cho `apps/taoanh` khai `providers: ["ltt_image", "gemini"]` và dùng **cascade** `chon_key` đã có sẵn |
| 2.2 | Bảng định tuyến **theo loại yêu cầu** từ G6b: loại nào model nhà thắng thì mặc định đi model nhà |
| 2.3 | ⛔ Khách **luôn thấy** model nào đã vẽ. Không đổi model sau lưng (D-010) |

### Đợt 3 — QUAN SÁT *(việc còn nợ lâu nhất)*

| # | Việc |
|---|---|
| 3.1 | Cấu hình `LTT_COST_MICROS_PER_*` + loại mới ở 0.4 ⇒ bảng biên lợi nhuận trong admin **có số** |
| 3.2 | Cảnh báo chủ động: biên âm, khoá sắp bị disable, máy B mất liên lạc |
| 3.3 | Chạy bền 100 ảnh (G9) |

### Đợt 4 — DỌN NỢ PHỐI HỢP

| # | Việc |
|---|---|
| 4.1 | Đánh số lại test 250–258 (3 phiên trùng nhau) |
| 4.2 | Phân loại `apps/vps` + `apps/ltt_llm` trong hai tài liệu bao phủ ⇒ `test_190`/`test_212` xanh trở lại |
| 4.3 | Quy ước chọn số test + chủ sở hữu tệp dùng chung (`providers.py`) |

---

## 7. Thứ tôi **không** làm trong tài liệu này, và vì sao

- **Không tự đổi giá.** Giá là quyết định kinh doanh. Tôi đưa giá vốn, giá hoà vốn
  và ba phương án; chủ dự án chọn.
- **Không chấm chất lượng model nhà.** G6b chưa chạy. Đoán một điểm số ở đây là
  đúng thứ mà cả bộ so mù sinh ra để chống.
- **Không tự thêm khoá `ltt_image`.** Token là bí mật; nó không đi qua phiên trò
  chuyện.
- **Không đụng vào việc của hai phiên đang chạy song song** (`ltt_llm`, `vps`).

## 8. Nguồn giá thị trường

- [Gemini API pricing — Google](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini 3 Pro Image — $0,134/ảnh 1K–2K](https://www.aifreeapi.com/en/posts/gemini-image-generation-api-pricing)
- [Gemini 2.5 Flash Image — 1.290 token, $0,039/ảnh](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)
- [Gemini 3.1 Flash Image — $0,067/ảnh 1K; Lite $0,0336](https://www.aifreeapi.com/en/posts/gemini-flash-image-generation-pricing)
- [Tự host so với API — điểm hoà vốn 30k–150k ảnh](https://www.wireflow.ai/blog/self-hosted-image-generation-api)
