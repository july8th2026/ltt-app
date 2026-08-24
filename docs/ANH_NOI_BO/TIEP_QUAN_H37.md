# H37 — tiếp quản, sửa logic, và kế hoạch trọn vẹn

**2026-08-24.** Chủ sản phẩm giao: *"tiếp quản công việc xây dựng `ltt_image`,
phân tích logic vận hành hiện tại, lấy hệ thống ta xây dựng làm gốc … để
`ltt_image` cũng được gọi từ API và tạo ra sản phẩm trả cho khách."*

"Hệ thống ta xây dựng" ở đây là **H38** (model ngôn ngữ nhà), vừa đi hết một
vòng có khách trả tiền thật. Khuôn rút ra từ nó nằm ở
[`docs/KHUON_BAN_MODEL_NHA.md`](../KHUON_BAN_MODEL_NHA.md) — 6 tầng, 31 chốt.

---

## 0. Kết luận trước, để không phải đọc hết

**H37 không "đi lệch hướng" như tôi tưởng lúc nhận việc.** Tầng khoá và tầng
cổng của nó **đã đúng** từ trước: `http_cong.py` dùng `api_pool` đúng cách và
**không** đánh dấu lỗi khi 429 (D-005); cổng render đã có `max_concurrent=1`,
429-khi-bận, và `busy.py` đọc VRAM thật qua `nvidia-smi`.

Chỗ lệch nằm ở **ba tầng ngoài cùng**: giá, quyết toán, và quan sát. Chấm theo
khuôn được **18/31**.

Trong đó có **một lỗi tiền đang sống**, cùng gốc với lỗi H38 đã mắc và đã sửa
hôm 23/08. Nó đã được sửa hôm nay, cùng sáu chỗ còn lại.

---

## 1. Bảy chỗ lệch, và trạng thái sau hôm nay

| | Chỗ lệch | Trước | Nay |
|---|---|---|---|
| 🔴 **L1** | Quyết toán theo phần **đã giữ**, không theo ảnh thật | xin 4 nhận 2 vẫn thu tiền 4 | ✅ sửa |
| 🔴 **L2** | Máy A **không có phép thăm dò nào** cho cổng render | cổng ảnh chết ⇒ chờ khách báo | ✅ sửa |
| 🔴 **L3** | Không phát hiện được "model ảnh rơi về CPU" | mọi chốt xanh, ảnh chậm gấp chục lần | ✅ sửa |
| 🟠 **L4** | Giá không công bố, không phiên bản | `CREDIT_MOI_ANH = 5` chôn trong manifest | ✅ sửa |
| 🟠 **L5** | Chưa mở trên API công khai | fail-closed đang làm đúng việc | ✅ **MỞ 24/08** — cả bốn cổng |
| 🟡 **L6** | Nghiệp vụ nằm trong `jobs.py` | cửa thứ hai sẽ phải chép | ✅ sửa |
| 🟡 **L7** | Không nói cho khách luật tính tiền ảnh | | ✅ sửa |

### 🔴 L1 — lỗi tiền, chi tiết

`render_gateway/runner.py` trả về **đúng số ảnh nó tải lên được**
(`image_keys[:so]`) và chỉ ghi một dòng log khi thiếu. Nên *"xin 4, nhận 2"* là
một kết cục **có thật**, không phải giả thuyết.

`apps/anhnoibo/jobs.py` không báo `credit_cost`. Mà `job_runner._quyet_toan_credit`
không thấy khoá đó thì **thu trọn phần đã giữ**. Khách trả tiền 4 ảnh cho 2 ảnh.
Im lặng, không log, không sự kiện.

Và có một biến thể tệ hơn ở `platform_core/image_gen/dieu_phoi.py`:

```python
return KetQuaAnh(job_id, tuple(t.image_keys or khoa), …)   # ← trước
```

`khoa` là danh sách khoá lưu trữ **cấp phát trước khi vẽ** — nó tồn tại kể cả
khi không ảnh nào được tải lên. Nên cổng trả về rỗng thì ta vẫn khai đủ `so_anh`
ảnh, tính tiền đủ `so_anh` ảnh, và khách bấm vào thì **404 từng cái một**.

Đã sửa cả hai: giá thật tính từ ảnh thật (`apps/anhnoibo/gia.py`), và
"thành công mà rỗng" nay là một **mâu thuẫn được báo lỗi**, không phải một
trường hợp chữa cháy im lặng.

### 🔴 L2/L3 — quan sát

Máy B chạy **hai dịch vụ khác nhau**: cổng VLM (:8299) và cổng render (:8199).
Chúng khởi động riêng, chết riêng, deploy riêng. H38 đã có `_tham_cong_vlm` +
`_tham_gpu_may_b`; phía ảnh **không có gì cả**, dù chạy trên cùng cái máy.

Nay có `_tham_cong_render` (sống/chết, qua `/live` mới thêm — không cần khoá) và
`_tham_gpu_anh` (GPU-hay-CPU, qua `/health`). Hai metric riêng, hai ngưỡng riêng.

⚠️ Triệu chứng CPU-fallback bên ảnh **khó thấy hơn hẳn bên chữ**: một lượt vẽ
vốn đã mất 96 giây, nên "chậm gấp hàng chục lần" trông giống hệt "máy đang bận"
— đúng thứ ta đã dạy mọi người coi là bình thường. Chốt chỉ bật khi **chắc
chắn**: đang vẽ > 90 giây mà VRAM < 5 GB.

### Bằng chứng

| Test | Chốt gì |
|---|---|
| `tests/test_276_gia_anh_that.py` (13) | giá theo ảnh thật · trần ≥ giá thật ở **mọi** cặp · `job_runner` đọc được · cổng rỗng ⇒ lỗi |
| `tests/test_277_tham_cong_anh.py` (16) | `/live` không cần khoá và không lộ vận hành · 429 **không** đếm · hai metric riêng |
| `tests/test_274_gia_cong_khai.py` (+3) | giá ảnh lên trang công khai, không lộ `hidream` |

---

## 2. H37 đang ở đâu trên 14 phase

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| G0 khung · G2 giấy phép | ✅ | |
| G1 đo phần cứng | ✅ | `bench/G1_phan_cung.json` |
| G3 baseline | ✅ | `bench/G3_*` |
| G4 quét cấu hình | ✅ **ĐÓNG 24/08** | D-054: gộp B2b+B2c = **60 cặp**, 50 bước 33–18, KTC [0,507; 0,744]. **Giữ 50 bước, câu cuối.** |
| G5 edit + reference | ✅ **MỞ 24/08** | bậc cuối đã đo (D-053): `subject` 2 ảnh @4 MP = **20,1 GB · 239 s**. Trần token 7.506 → **11.412** |
| G5b chuỗi nâng chất | ⏸️ chưa | |
| G6b đối chứng trần | ✅ **đã chấm** | D-045: Gemini 24 – nhà 4 – hoà 2 |
| G6 cổng render | ✅ | thêm `/live` + chốt GPU hôm nay |
| G7 deploy sang B | ✅ | dịch vụ chạy thật trên B |
| G8 nối nền tảng | ✅ | provider `ltt_image` + `image_gen` + app `anhnoibo` |
| **L1–L7** | ✅ hôm nay | **không có trong kế hoạch gốc** |
| G9 độ bền | ✅ **ĐÓNG 24/08** | D-056: **100/100, 0 hỏng**. VRAM 18.287–18.450 MB (dao động 0,9 %), nhiệt 69–74 °C, thời gian 108,0–110,9 s. **Không trôi**: 20 lượt cuối *thấp hơn* 20 lượt đầu ở cả ba đại lượng. Lô đầu chết ở 87 vì SSH đứt — chạy trọn nhờ Scheduled Task (D-055) |
| G10 mở cho khách | 🔨 **đang 24/08** | 4 cổng đã mở; còn nghiệm thu một job thật từ ngoài vào |
| G11 giám sát chất lượng | ⏸️ chưa | |

**Đường găng còn lại: chỉ còn nghiệm thu G10** — một job ảnh đi thật từ ngoài vào qua `/api/v1`, và nó chờ **hai lệnh của chủ sản phẩm** (§4 Đợt C).

⚠️ **Đã đảo thứ tự so với bản đầu của tài liệu này.** Bản đầu xếp *không mở tool trước khi xong Đợt A + B*. Tôi đổi, và ghi ra để không ai tưởng là quên:

① Bốn cổng fail-closed vẫn nguyên vẹn — mở là một hành động **có chủ ý**, và đảo lại được bằng một dòng trong `app.env`.
② Nền tảng **chưa có khách ngoài**, nên cái giá của việc mở sớm gần bằng 0. Trong khi đó thứ **chưa ai làm bao giờ** — một job ảnh đi thật từ ngoài vào qua `/api/v1` — là thứ dễ lòi ra vấn đề nhất. H38 có 739 test xanh và vẫn để lọt lỗi `VARCHAR(36)` tới đúng lượt gọi thật đầu tiên.

---

## 3. Câu hỏi kinh doanh — đã trả lời 24/08

G6b đã chấm và **model nhà thua rõ**: 0 thắng / 16 ở photoreal + chân dung +
đông người + thumbnail + chữ. Chỉ ngang ở anime/fantasy/kiến trúc, mà mỗi loại
vỏn vẹn 2 cặp.

Kế hoạch gốc đặt G6b làm **cổng chặn** với luật *"thua quá xa thì không mở bán"*.
Theo đúng luật đó, cổng này **đã trượt**.

Nhưng D-042 + D-046 đã đổi bài toán: không còn định tuyến, mỗi model là **một
mặt hàng có cổng gọi riêng**. Khách gọi `image.ltt` là nhận HiDream, biết trước
mình mua gì. Nên câu hỏi không còn là *"nhà có đẹp hơn Gemini không"* mà là:

> **Có ai muốn mua một model vẽ kém hơn nhưng rẻ hơn và không bị chính sách nội
> dung của một hãng khác chi phối không?**

✅ **Chủ sản phẩm đã trả lời 24/08: bán, và hạ giá một phần ba.** Ba hệ quả, cả
ba đã thi hành:

1. **Đừng định vị là "đẹp hơn".** Ghi thẳng vào `providers.py` cạnh chỗ mở cổng,
   để người sau đọc mã là thấy — không phải đi tìm trong tài liệu.
2. **Đừng đưa việc có chữ sang nó.** D-048 xếp chữ tiếng Việt là **ngoài phạm
   vi**; `image.thumbnail` (Gemini) vẫn là hàng cho việc có chữ.
3. **Giá phản ánh đúng lý do tồn tại của nó.** `CREDIT_MOI_ANH` **5 → 3**
   (tham chiếu 15 → 9). Trước đó nó đặt **bằng đúng giá `thumbnail` chạy Gemini**
   — tức là bán một sản phẩm kém hơn với cùng giá.

   Lấy 3 chứ không lấy 4 (5 × 2/3 = 3,33): làm tròn về phía khách, và như vậy
   *mọi* lượt gọi rẻ hơn ít nhất một phần ba, kể cả lượt một ảnh — lượt phổ biến
   nhất. Vẫn trên giá vốn xa: `gia_von.json` ghi 1,05 credit/ảnh, biên **2,9 lần**.

---

## 4. Kế hoạch còn lại — bốn đợt

### Đợt A — chốt cấu hình *(cần GPU)*

| # | Việc | Đạt khi |
|---|---|---|
| A1 | ✅ **XONG 24/08 (D-054).** Lô B2c nâng lên 60 cặp; khoảng tin tách khỏi 0,5; **giữ 50 bước** | có một dòng trong `DECISIONS.md` nói số bước cuối cùng ✅ |
| A2 | ✅ **XONG 24/08 (D-053).** Bậc cuối chưa ai đo — `subject` 2 ảnh @4 MP — đã đo có người canh: **20.114 MB VRAM · 239,0 s · 73 °C**, dưới xa ngưỡng dừng 21.000. Trần 7.506 → **11.412** | trần mới có **số đo** đứng sau ✅ |

⛔ **Đừng hạ `ref_mp` cho lọt chốt.** Đó chỉ là chọn một con số khác cũng chưa ai
đo, và nó biến một chốt an toàn thành một nghi thức.

⛔ **Luật một-lô-một-biến vẫn giữ** (D-046). Đổi hai biến cùng lúc thì khi thua
sẽ không biết vì thứ nào.

### Đợt B — độ bền *(G9, cần GPU)*

| # | Việc | Vì sao |
|---|---|---|
| B1 | ✅ **XONG 24/08 (D-056)** — 100/100, không rò VRAM, không trôi nhiệt. Và số đo làm cảnh báo "VRAM 97,5 %" thành **lỗi thời**: nặng nhất từng đo nay là 20,1 GB, biên còn ~4,5 GB | ~~VRAM 23,9 / 24,6 GB = 97,5 %, biên quá mỏng~~ — **đó là câu hỏi lúc đặt B1, và câu trả lời là con số đó đã lỗi thời**: nó đo trước `--reserve-vram 3`. Giữ lại vế này để thấy B1 sinh ra vì lo cái gì |
| B2 | ⏸️ **chưa** — cần dự án video chạy cùng lúc, tức cần chủ sản phẩm | ba hộ dùng chung card, không phải hai (D-037). Cần biết cổng render **báo bận đúng**, không phải báo hỏng. ⚠️ Đây là chốt duy nhất của Đợt B chưa đóng, và nó **không** đóng được bằng một lô đo của riêng ta |
| B3 | ✅ **XONG** — ComfyUI trên máy B **đã** chạy với `--reserve-vram 3` (kiểm bằng `nssm get LTTComfyUI AppParameters` 24/08), và `test_245` nay chốt cờ đó khớp `VRAM_CHUA_LAI_GB` | mất cờ lặng lẽ là sập giữa một lô dài ✅ |
| B4 | ✅ **XONG** — chốt cả ba mắt xích: cổng đặt `dang_lo` → thăm dò đếm metric → `ops_alerts` bắn ở ngưỡng 1 (`test_277`) | lệch tên metric ở bất kỳ đâu thì cả dây im lặng, và im lặng trông y hệt bình thường ✅ |

### Đợt C — mở cho khách *(G10, cần quyết định §3)*

| # | Việc | Ai |
|---|---|---|
| C1 | ✅ **XONG 24/08** — chốt định vị và giá theo §3 | chủ sản phẩm |
| C2 | ✅ **XONG** — `gia.py` 5 → 3, `PHIEN_BAN_GIA` → `ltt-image-2026-08-24b`, `/gia-api` tự đổi theo | tôi |
| C3 | ✅ **XONG** — `is_active=True` + `LTT_PUBLIC_API_TOOLS` thêm `image.ltt` | tôi |
| C4 | Một job thật đi từ ngoài vào qua `https://app.lttstudios.com/api/v1`, đối soát credit bằng tay | tôi |
| C5 | Điền một dòng vào mục 4 của `APP_API_COVERAGE_FINAL.md` | tôi |

⛔ **C4 không thay được bằng test.** H38 có 739 test xanh và vẫn để lọt lỗi
`VARCHAR(36)` tới tận lượt gọi thật đầu tiên — SQLite không ép độ dài, PostgreSQL
có. Đường ảnh chưa từng chạy thật từ ngoài vào bao giờ.

### Đợt D — sau khi mở

| # | Việc |
|---|---|
| D1 | **G11** giám sát chất lượng thường trực |
| D2 | **G5b** chuỗi nâng chất (upscale/restore + VLM tự loại) — chỉ khi có khách và có phàn nàn cụ thể |
| D3 | Cửa thứ hai (đồng bộ) nếu có ai hỏi. `features.py` đã sẵn sàng cho việc đó |

---

## 5. Cái gì KHÔNG làm

| Không làm | Vì sao |
|---|---|
| Chạy thêm lô đấu Gemini | D-046 đã bỏ hẳn. Không còn lựa chọn nào để đổi ⇒ điểm số không mua được gì |
| Cascade sang đám mây khi máy B bận | D-010: khách trả tiền cho `image.ltt` mà nhận Gemini là **bán sai hàng** |
| `danh_dau_loi` cho khoá `ltt_image` khi 429 | D-005: cooldown rồi `disable` sau 5 lần — một tối chạy video sẽ tự tắt vĩnh viễn model nhà |
| Đưa việc có chữ tiếng Việt sang `image.ltt` | D-048: ngoài phạm vi, đã chấp nhận |
| Mở tool trước khi xong Đợt A + B | fail-closed đang làm đúng việc; mở sớm là bỏ đúng thứ đang bảo vệ mình |
