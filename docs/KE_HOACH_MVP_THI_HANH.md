# Kế hoạch thi hành MVP — bám tài liệu cộng đồng, từng hạng mục một

**2026-08-23** · đi kèm [`PHAN_TICH_MVP_2026-08-23.md`](PHAN_TICH_MVP_2026-08-23.md)

## Quy tắc của tài liệu này

Chủ dự án chốt: **tìm tài liệu trước, tự nghĩ sau — và chỉ tự nghĩ khi không có
tài liệu.** Nên mỗi hạng mục dưới đây có ba nhãn cố định:

| Nhãn | Nghĩa |
|---|---|
| 📖 **THEO TÀI LIỆU** | có dự án nguồn mở làm đúng việc này; ta chép **cách làm**, ghi rõ chép ở đâu |
| 🔧 **CHỈNH CHO TA** | tài liệu có, nhưng bối cảnh ta khác ⇒ đổi có lý do viết ra |
| 💡 **TỰ NGHĨ** | tìm không ra tài liệu; ghi rõ để người sau biết đây là chỗ yếu nhất |

### Bốn nguồn chính, và giấy phép

| Nguồn | Dùng cho | Giấy phép |
|---|---|---|
| [BerriAI/litellm](https://github.com/BerriAI/litellm) — `model_prices_and_context_window.json` | bảng giá vốn model, định tuyến, cooldown | MIT |
| [getlago/lago](https://github.com/getlago/lago) | ví trả trước, credit hết hạn/chuyển tiếp | AGPL-3.0 *(chỉ đọc kiến trúc, **không** chép mã)* |
| [openmeterio/openmeter](https://github.com/openmeterio/openmeter) | đo lượng dùng → quyền lợi → hoá đơn | Apache-2.0 |
| [lm-sys/FastChat](https://github.com/lm-sys/FastChat) + LMArena | so mù nhiều model, Bradley-Terry | Apache-2.0 |

⛔ **Lago là AGPL.** Ta **đọc kiến trúc** của nó, **không chép một dòng mã nào**.
Cùng nguyên tắc `LICENSE_NOTES.md` đã áp cho Klein 9B.

### Điều đáng nói trước: phần lớn thiết kế của ta **đã khớp tài liệu**

Tra xong mới thấy ba thứ ta làm đúng mà không biết là mình đang theo một khuôn có
tên:

| Ta có | Khớp với |
|---|---|
| `public_api/costing.py` tách **chi phí** khỏi **doanh thu**, đánh dấu `is_estimate` | LiteLLM tách `completion_cost()` khỏi budget enforcement khỏi billing |
| `credit.giu_cho → quyet_toan → hoan` | ví trả trước (prepaid wallet) của Lago |
| `api_pool` chọn theo priority → health → tải cửa sổ | `least-busy` + `usage-based-routing` của LiteLLM Router |

Nên phần lớn công việc dưới đây là **lấp chỗ trống**, không phải làm lại.

---

# ĐỢT 0 — CẦM MÁU

> Không cần GPU. Không cần deploy. Làm được ngay.
> **Ra khỏi đợt này thì hệ thống không còn bán dưới giá vốn nữa.**

---

## 0.1 — Bảng giá vốn model: `platform_core/gia_von.py`

**📖 THEO TÀI LIỆU.** Nguồn: LiteLLM `model_prices_and_context_window.json`.

### Lấy gì từ tài liệu

**① Tên trường.** Dùng đúng tên LiteLLM đặt, không tự đặt tên mới:

| Trường | Nghĩa |
|---|---|
| `input_cost_per_token` | token vào |
| `output_cost_per_token` | token ra |
| `cache_read_input_token_cost` | token vào lấy lại từ cache |
| `output_cost_per_image` | **ảnh sinh ra** ← thứ ta đang thiếu |
| `input_cost_per_image` | ảnh đưa vào (đa phương thức) |
| `mode` | `"image_generation"` / `"chat"` |

*Vì sao chép tên: ngày nào ta muốn nạp thẳng bảng của LiteLLM cho các model mới,
không phải viết lớp dịch tên trường.*

**② Khuôn "bản đồ giá cục bộ".** LiteLLM có `LITELLM_LOCAL_MODEL_COST_MAP=True` để
chạy hoàn toàn ngoại tuyến từ một tệp JSON đóng gói sẵn. Ta lấy đúng ý đó: **một
tệp JSON trong repo là nguồn chân lý**, không gọi mạng lúc chạy.

**③ Phép kiểm số mục.** LiteLLM từ chối bản đồ giá có dưới 50 mục — chống việc một
tệp rỗng/hỏng lặng lẽ làm mọi giá về 0. Ta lấy nguyên ý này.

**④ Mặc định "đắt" khi không biết giá.** LiteLLM gán **$1** cho model không có
trong bảng. Đó là một mặc định **fail-expensive** có chủ ý: không biết giá thì
đừng định tuyến vào đó.

### 🔧 Chỉnh cho ta

| Chỗ chỉnh | Vì sao |
|---|---|
| Đơn vị **milli-credit số nguyên**, không phải USD float | `platform_core/llm/gia_token.py` đã chốt: *"dấu phẩy động trong đường tiền là cách chắc chắn nhất để hai lần cộng ra hai kết quả"* |
| Thêm `PHIEN_BAN_GIA` | LiteLLM không có; nhưng `public_api/pricing.py` của ta đã đòi — đổi giá thì **nhãn mới**, không sửa nhãn cũ |
| Thêm `nguon` + `ngay_tra` mỗi mục | giá thị trường **hết hạn**. Một con số không có ngày là một con số không kiểm lại được |
| Thêm `chi_phi_may_nha` cho `ltt_image` | LiteLLM không mô hình hoá điện + khấu hao GPU |

### Các bước

1. **`platform_core/gia_von.py`** — hằng số + hàm đọc, không I/O lúc import.
2. **`platform_core/gia_von.json`** — dữ liệu. Mỗi mục:
   ```json
   "gemini-3-pro-image": {
     "mode": "image_generation",
     "output_cost_per_image_mcredit": 35240,
     "nguon": "https://ai.google.dev/gemini-api/docs/pricing",
     "ngay_tra": "2026-08-23",
     "ghi_chu": "$0.134/anh 1K-2K @ 26.300d/USD, 1 credit = 100d"
   }
   ```
3. **`gia_von_mcredit(model_id) -> int`** — raise `KhongBietGiaVon` nếu thiếu.
   ⛔ **Không trả 0.** Giá vốn 0 nghĩa là "miễn phí" và nó sẽ đi thẳng vào một
   phép so biên lợi nhuận.
4. **`ltt_image`**: `chi_phi_may_nha` = 1.050 mcredit (t2i) / 2.070 (tham chiếu),
   kèm công thức và giả định trong `ghi_chu`.

### Test chốt (`tests/test_260_gia_von.py`)

| Test | Chốt điều gì |
|---|---|
| mọi model trong `providers.py` đều có mục giá vốn | thêm model mà quên giá là gate đỏ |
| model lạ ⇒ **ném lỗi**, không trả 0 | 0 là một khẳng định, và module này không có quyền khẳng định |
| mỗi mục có `nguon` + `ngay_tra` | số không nguồn không kiểm lại được |
| số mục ≥ ngưỡng | chống tệp rỗng/hỏng *(ý của LiteLLM)* |
| toàn bộ là **int**, không float | quy tắc `gia_token.py` |
| `ngay_tra` cũ hơn 180 ngày ⇒ **cảnh báo** | giá thị trường hết hạn |

**Xong khi:** `python -c "from platform_core import gia_von; print(gia_von.gia_von_mcredit('gemini-3-pro-image'))"` in ra `35240`, và test xanh.

---

## 0.2 — ⛔ Bánh cóc chặn bán dưới giá vốn

**💡 TỰ NGHĨ** — và tôi ghi rõ vì đây là chỗ **không tìm được tài liệu**.

Tra ba nguồn (LiteLLM, Lago, OpenMeter): cả ba đều **đo** chi phí và **hiện** biên
lợi nhuận, nhưng **không nguồn nào chặn việc đặt giá dưới giá vốn**. Lý do hợp lý:
với họ, bán dưới giá vốn là một **lựa chọn kinh doanh hợp lệ** (khuyến mãi, giá
thâm nhập).

Với ta thì khác: giá đang dưới giá vốn **không phải do ai chọn** — nó là một hằng
số không có cơ sở, chạy 22 ngày mà không ai thấy. Nên ta cần thứ họ không cần: một
chốt bắt phải **cố ý** thì mới lỗ được.

### Thiết kế

Một test quét **mọi** `credit_cost` trong registry, dựng đầu vào tối thiểu, so với
`gia_von`:

```python
for app in discover():
    for model_id in cac_model_cua(app):
        gia_ban = app.manifest.credit_cost({...}) * 1000       # mcredit
        gia_von_ = gia_von.gia_von_mcredit(model_id)
        assert gia_ban >= gia_von_ or model_id in LO_CO_CHU_DICH
```

`LO_CO_CHU_DICH` là một **danh sách khai báo** trong repo, mỗi dòng phải có **lý do
và ngày rà lại**. Lỗ thì được — nhưng phải **ký tên**.

### Vì sao test chứ không phải kiểm lúc chạy

Kiểm lúc chạy thì phát hiện **sau khi** đã bán. Test thì phát hiện **trước khi**
merge. Cùng lý lẽ mà `test_190`/`test_212` đã dùng cho việc phơi tool.

**Xong khi:** đổi `CREDIT_PER_IMAGE` về 5 làm test **đỏ** kèm thông điệp nói rõ
thiếu bao nhiêu.

---

## 0.3 — Đặt lại giá bán

**🔧 CHỈNH CHO TA** — con số là quyết định kinh doanh, tôi không tự đặt.

Ba phương án (§2.3 của tài liệu phân tích). Điều tài liệu cộng đồng **có** nói:

📖 **Lago**: ví trả trước có **credit hết hạn và chuyển tiếp theo lịch cấu hình
được**. Ta **chưa có** — credit của ta sống vĩnh viễn. Đó là một khoản nợ tiềm ẩn
trên bảng cân đối, và nó **lớn dần**. Không thuộc đợt 0, nhưng ghi ra ở đây vì nó
là cùng một cuộc trò chuyện về giá.

### Các bước

1. Chủ dự án chọn bội số.
2. Sửa `MODEL_CREDIT_PER_IMAGE` + `CREDIT_PER_IMAGE`.
3. **Đổi `PHIEN_BAN_GIA`** — không sửa nhãn cũ *(quy tắc `public_api/pricing.py`)*.
4. Cập nhật `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` + sinh lại `DEVELOPER_GUIDE`.
5. ⚠️ **Khách đang có credit mua ở giá cũ.** Cần một câu thông báo, không phải một
   lần đổi im lặng.

---

## 0.4 — Thêm loại chi phí "gọi nhà cung cấp" vào `costing.py`

**📖 THEO TÀI LIỆU.** Nguồn: LiteLLM tách **cost calculation** (trong SDK, gắn vào
response) khỏi **budget enforcement** (ở proxy) khỏi **billing**.

### Vấn đề hiện tại, nói chính xác

`costing.RATE_ENV` chỉ có ba loại: `duration_ms`, `bytes`, `tokens`. Với một job
ảnh Gemini, **chi phí lớn nhất là một lần gọi API tính theo ảnh** — không phải
token, không phải giây, không phải byte. Nên khoản đó **không có chỗ để ghi**.

### Các bước

1. Thêm hằng `COST_PROVIDER_CALL` vào `costing.py`.
2. Handler báo về `{"provider_calls": [{"model": ..., "count": n}]}` trong kết quả.
3. `record_job` tra `gia_von` và ghi quan sát — **`source="gia_von"`**, không phải
   `"configured_rate"`, vì nguồn khác thì độ tin khác.
4. Đặt `LTT_COST_MICROS_PER_MS` / `PER_BYTE` trên production *(đang **trống** —
   đó là lý do bảng biên lợi nhuận trong admin không có số nào)*.

**Xong khi:** chạy một job ảnh thật rồi mở `/admin` → biên lợi nhuận, thấy **số âm
đúng bằng** phép tính tay ở §2.2.

---

# ĐỢT 1 — MỞ MODEL NHÀ

## 1.1 — Khoá `ltt_image` trong APIKEYS

**Việc của chủ dự án.** Token ở máy B: `C:\ProgramData\LTTRender\gateway.env`.
Provider `ltt_image`, category `image`.

## 1.2 → 1.4 — Chạy G6b

**📖 THEO TÀI LIỆU** — và ở đây tài liệu chỉ ra **một lỗi thật trong bộ chấm của ta**.

### Điều LMArena dạy ta

LMArena bỏ Elo tuần tự và chuyển sang **Bradley-Terry ước lượng hợp lý cực đại**
từ **toàn bộ** phiếu cùng lúc, khoảng tin cậy bằng **bootstrap** (bách phân vị
2,5–97,5).

Lý do họ đổi: Elo tuần tự **phụ thuộc thứ tự trận**, nên hai lần xáo cùng một bộ
phiếu ra hai bảng xếp hạng khác nhau.

### ⛔ Chỗ bộ chấm của ta sẽ sai

`tools/cham_mu.py` dùng **khoảng Wilson trên tỉ lệ thắng**. Cái đó **đúng cho hai
model**. Nhưng G6b có **ba đối thủ** (Klein 9B · Gemini 3 Pro · GPT Image 2), và
lúc đó tỉ lệ thắng theo cặp **không cộng lại thành một bảng xếp hạng nhất quán** —
A thắng B, B thắng C, C thắng A là chuyện bình thường trong dữ liệu thật.

⇒ **Phải thêm Bradley-Terry trước khi chấm nhiều hơn hai bên.**

### Các bước

1. `tools/cham_mu.py`: thêm `xep_hang_bt()` — Bradley-Terry MLE + bootstrap CI.
2. **Giữ nguyên** đường Wilson cho trường hợp hai model *(đơn giản hơn, đủ dùng,
   và đã có 21 test)*.
3. Giữ nguyên cặp bẫy A-đấu-A đo **sàn nhiễu** — 💡 thứ này **ta tự nghĩ** và
   LMArena không có; nó vẫn đúng, ghi ra để không ai bỏ đi.
4. Chạy: nửa model nhà → `chuan_hoa_anh` → `cham_mu tao` → chấm → `cham_mu tinh`.

**Xong khi:** có bảng định tuyến *"loại yêu cầu → nên đi đâu"*, kèm CI, kèm sàn nhiễu.

## 1.5 — Bật `is_active`, đặt giá model nhà

Giá vốn **1,05 credit**. Ở bất kỳ giá bán nào ≥ giá hoà vốn Gemini, biên **> 90 %**.

---

# ~~ĐỢT 2 — ĐỊNH TUYẾN~~ ⛔ ĐÃ GỠ 2026-08-23

**Chủ dự án bác, và bác đúng.** Xem **D-042**.

Tôi đề xuất định tuyến theo giá vốn sau khi đọc `cost-based-routing` của LiteLLM.
Nó giải một bài toán khác: ở đó nhiều **deployment** phục vụ **cùng một model
logic**, nên chọn cái rẻ nhất là trong suốt với khách.

Ở LTTSTUDIOSAPP thì `gemini-3-pro-image` và `hidream-o1` là **hai mặt hàng khác
nhau**. Khách gọi cái nào thì dùng cái đó. Hệ thống thấy model nhà rẻ hơn 34 lần
rồi lặng lẽ vẽ bằng nó là **đánh tráo sản phẩm** — đúng thứ D-010 cấm, và tôi đã
đề xuất nó **ngay sau khi tự viết ra D-010**.

**Hình dạng đúng đã có sẵn, không phải xây thêm:** mỗi loại tạo ảnh là **một tool
riêng** (`image.ltt`), có **trang tài liệu riêng** (`/developers/tools`), và khách
**tự chọn khoá gọi được tool nào** (`allowed_tools`).

Quy trình thì **vốn đã đồng nhất**: `apps/anhnoibo/http_cong.py` lấy token qua
`api_pool.lay_key(db, "ltt_image", ...)` — cùng bộ máy APIKEYS mà Gemini đi.

### Thứ **giữ lại** từ đợt này, vì nó đúng vì lý do khác

Hai khoảng trống so với LiteLLM Router **không** liên quan tới định tuyến sản phẩm.
Chúng là **độ bền của một tài khoản**, và vẫn đáng làm:

| # | Khoảng trống | Vì sao vẫn đúng |
|---|---|---|
| a | ta **không có chuỗi thử lại nào** | một khoá Gemini cạn hạn mức ⇒ job hỏng, **dù còn khoá Gemini khác**. Đây là dự phòng ở tầng *tài khoản*, không phải tầng *sản phẩm* — khách vẫn nhận đúng model họ gọi |
| b | `401/403` đếm tới 5 mới disable | 4 request đầu vẫn ném vào một khoá đã chết. LiteLLM cooldown ngay |

⛔ Khoảng trống **c** (định tuyến theo giá vốn) **bỏ hẳn**.

⇒ Hai việc trên chuyển thành **Đợt 5 — độ bền chuỗi khoá**, xếp sau quan sát.

# ĐỢT 3 — QUAN SÁT

**📖 THEO TÀI LIỆU.** Nguồn: OpenMeter *(Apache-2.0)*.

Chuỗi của OpenMeter: **sự kiện dùng → gộp → quyền lợi/hạn mức → hoá đơn**. Ta đã
có ba mắt đầu (job events, `costing`, credit) nhưng **chưa nối chúng lại thành một
màn hình**.

| # | Việc | Ghi chú |
|---|---|---|
| 3.1 | Bảng biên lợi nhuận **có số** | phụ thuộc 0.4 |
| 3.2 | Cảnh báo: biên âm · khoá sắp bị disable · máy B mất liên lạc | ⚠️ phải đặt **sau một lease** (`platform_core/leases.py`) — worker chạy nhiều tiến trình, không thì cảnh báo gửi trùng (H36) |
| 3.3 | Chạy bền 100 ảnh (G9) | cần GPU |

---

# ĐỢT 4 — DỌN NỢ PHỐI HỢP

**💡 TỰ NGHĨ.** Không có tài liệu — đây là vấn đề riêng của việc chạy nhiều phiên
Claude song song trên một repo.

| # | Việc | Chi tiết |
|---|---|---|
| 4.1 | Đánh số lại test 250–258 | ba phiên trùng nhau; `test_255_dieu_phoi` và `test_252_dieu_phoi` cùng tên chủ đề |
| 4.2 | Phân loại `apps/vps` + `apps/ltt_llm` | `test_190`/`test_212` mỗi tệp đỏ đúng một test |
| 4.3 | Quy ước: `ls tests/test_2*` trước khi đặt số; ghi chủ sở hữu `providers.py` | |

---

# ĐỢT 5 — ĐỘ BỀN CHUỖI KHOÁ *(tách ra từ Đợt 2 đã gỡ)*

**📖 THEO TÀI LIỆU.** Nguồn: LiteLLM Router — nhưng **chỉ phần độ bền**, không phần
định tuyến sản phẩm.

⭐ Ranh giới phải giữ cho rõ: đây là dự phòng ở tầng **tài khoản**, không phải tầng
**sản phẩm**. Khách gọi `gemini-3-pro-image` thì vẫn nhận `gemini-3-pro-image` —
ta chỉ đổi **khoá nào của Gemini** phục vụ lượt gọi đó. Khách không thấy gì khác.

| # | Việc | Vì sao |
|---|---|---|
| 5.1 | **Chuỗi thử lại có loại trừ tích luỹ** trong `api_pool` | hôm nay một khoá cạn hạn mức ⇒ job hỏng, **dù còn khoá khác của cùng nhà cung cấp**. LiteLLM loại khoá vừa hỏng khỏi các bước sau của cùng một request |
| 5.2 | `401/403` ⇒ **cooldown ngay**, giữ nguyên ngưỡng disable 5 | hôm nay 4 request đầu vẫn ném vào một khoá đã chết |

⛔ **Không** thêm tiêu chí giá vốn vào `chon_key`. Đó là phần đã gỡ, và gỡ vì lý do
sản phẩm chứ không phải vì khó làm.

---

## Thứ tự bắt buộc, và vì sao

```
0.1 gia_von.py ──► 0.2 banh coc ──► 0.3 dat lai gia
      │                                   │
      └────────► 0.4 costing ─────────────┘
                                          │
1.1 khoa ──► 1.2 chay G6b ──► 1.3 cham ──► 1.4 cong quyet dinh ──► 1.5 bat model nha
                                                                        │
                                                          2.x dinh tuyen theo gia von
                                                                        │
                                                                    3.x quan sat
```

- **0.2 phải sau 0.1**: bánh cóc cần bảng giá vốn để so.
- **0.3 phải sau 0.2**: đổi giá mà chưa có bánh cóc thì lần sau lại lệch.
- **Đợt 5 độc lập** với mọi đợt khác: nó chỉ đụng `api_pool`, không đụng giá và
  không đụng model nào.

⛔ **Đợt 2 cũ đã gỡ.** Lý do ghi ở D-042: mỗi model là **một mặt hàng**, và mặt
hàng không thay thế nhau sau lưng khách.

## Ba chỗ yếu nhất của kế hoạch này

Ghi ra vì chúng là 💡 **tự nghĩ**, tức là chưa ai kiểm chứng hộ:

1. **Bánh cóc chặn bán dưới giá vốn (0.2)** — không nguồn mở nào làm. Có thể nó
   sai ở chỗ tôi chưa thấy.
2. **Cặp bẫy A-đấu-A đo sàn nhiễu** — LMArena không có. Tôi vẫn tin nó đúng, nhưng
   nó là của ta.
3. **Quy ước phối hợp nhiều phiên (4.3)** — vấn đề quá mới, chưa có nếp.

## Nguồn

- [BerriAI/litellm](https://github.com/BerriAI/litellm) · [bản đồ giá cục bộ](https://docs.litellm.ai/docs/proxy/custom_model_cost_map) · [định tuyến & cân tải](https://docs.litellm.ai/docs/routing) · [tính chi phí](https://deepwiki.com/BerriAI/litellm/2.6-cost-calculation-and-model-pricing)
- [getlago/lago-api](https://github.com/getlago/lago-api) — ví trả trước, credit hết hạn *(AGPL — chỉ đọc kiến trúc)*
- [openmeterio/openmeter](https://github.com/openmeterio/openmeter) — đo lượng dùng → quyền lợi → hoá đơn
- [lm-sys/FastChat](https://github.com/lm-sys/FastChat) · [Chatbot Arena chuyển sang Bradley-Terry](https://www.lmsys.org/blog/2023-12-07-leaderboard/) · [Elo so với Bradley-Terry](https://hippocampus-garden.com/elo_vs_bt/)
