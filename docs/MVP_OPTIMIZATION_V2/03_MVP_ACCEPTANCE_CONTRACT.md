# 03 — HỢP ĐỒNG NGHIỆM THU MVP + GOLDEN JOURNEYS

**Ngày:** 2026-08-26 · **Cây:** `db6147e` · **Đầu vào:** 00, 01, 02

> Prompt này tồn tại để 12 prompt sau **không tối ưu một hệ thống mà chưa biết
> "MVP thành công" nghĩa là gì**. Nó là hợp đồng bảo vệ, không phải một vòng
> khảo sát nữa.

---

## 1. Lời hứa sản phẩm

> Cho người sáng tạo nội dung tiếng Việt: biến một ý tưởng thành **ảnh hoặc
> video dùng được**, trả **theo lượt** bằng credit, không cần cài gì.

| | |
|---|---|
| **Persona** | Người làm nội dung tự do / chủ kênh nhỏ, không phải kỹ sư |
| **JTBD lõi** | "Tôi cần một tấm ảnh / một đoạn video dùng được, ngay bây giờ, không muốn học công cụ" |
| **Kết quả lõi** | Một tệp tải về được + một dòng lịch sử giải thích được đã trả bao nhiêu, cho cái gì |
| **Time-to-value** | ⚠️ **CHƯA ĐO** — không được bịa. Đưa vào Prompt 10 |

---

## 2. Bề mặt phát hành

| Bề mặt | Trong MVP? | Trạng thái | Vì sao |
|---|---|---|---|
| Trang công khai + đăng ký + đăng nhập | ✅ | released | Cửa vào duy nhất |
| `taoanh` / `thumbnail` / `anhnoibo` | ✅ core | development | Chuỗi hoàn chỉnh nhất; giá vốn đo kỹ nhất |
| `upscalevideo` · `taovideo` · `prompt_ai_ommi` | ✅ core | released | Đã chạy thật |
| `chataistudio` + `ltt_llm` | ✅ core | development | **Đang bán thật** qua `/api/v1` |
| Nạp credit (PayOS) | ✅ core | released | Không có nó thì không có MVP trả phí |
| `/api/v1` cho khách lập trình | ✅ core | 2 tool mở | `text.chat`, `image.ltt` **đang thu tiền** |
| `autosubvideo` · `taoclipngan` | 🟡 beta | development | Chín tính năng, chưa chín hình dạng |
| `agent` | ⏸️ hoãn | development | Đường đưa tệp vào đã đứt (R-01) |
| `nexus` | ✅ hỗ trợ | released | Đã thu credit thật |
| `vps` | ⏸️ hoãn | tắt bằng cờ | Còn G7b/G9b |
| `qualitylab` | 🔒 nội bộ | internal | Đúng chỗ |
| Trang admin tối thiểu | ✅ hỗ trợ | — | Không có thì không hỗ trợ được khách thật |

---

## 3. Golden Journeys

Sáu hành trình. Không phải "sáu vì pack gợi ý sáu" — mỗi cái đại diện **một lớp
rủi ro khác nhau**, và bỏ cái nào là mù một lớp.

### GJ-1 · Ẩn danh → có tài khoản → vào được sản phẩm

`/` → `/register` → xác thực email → `/login` → catalog → một app

- **Nguồn giá:** không có tiền ở đây
- **Trạng thái:** ẩn danh → chờ xác thực → hoạt động
- **Thành công:** vào được một trang sản phẩm với số dư credit thử
- **Thất bại phải đúng:** email trùng · token hết hạn · Turnstile hỏng · quá hạn mức IP/ngày
- **Bằng chứng có:** E2 (`test_37`, `test_63`) · **cần thêm:** E3 trên URL công khai

### GJ-2 · Tool ảnh: nhập → báo giá → xác nhận → job → kết quả → lịch sử

`/taoanh` (hoặc `/thumbnail`)

- **Nguồn giá có thẩm quyền:** `credit_cost` của manifest, kẹp bởi `gia_von.json`
  + `test_261`. ⛔ **Route không được tự tính giá.**
- **Trạng thái:** `queued → running → done|error`
- **Bất biến tiền:** `giu_cho` cùng transaction với `jobs.submit`; `quyet_toan`
  hoặc `hoan` **đúng một lần** (`_khoa_ket_so_job`)
- **Thất bại phải đúng:** thiếu credit ⇒ **không tạo job, không gọi API**
- **Bằng chứng có:** E2 (`test_67`, `test_68`) · **cần thêm:** E3

### GJ-3 · Nạp credit → webhook → số dư

`/billing` → PayOS → `POST /webhooks/payment/payos`

- **Nguồn giá:** gói + % bonus, `credit.nap` idempotent
- **Bất biến:** webhook trùng **không** cộng hai lần; chữ ký kiểm trên **thân thô**
- **Thất bại phải đúng:** chữ ký sai ⇒ 400, không ghi sổ · đơn quá hạn ⇒ `expired`
- **Bằng chứng có:** E2 · **cần thêm:** E2 phát lại webhook

### GJ-4 · `/api/v1`: khoá dev → `text.chat` dạng luồng → quyết toán

⛔ **Bắt buộc.** Đây là hành trình **duy nhất** đi qua lớp tiền không có đường về.

- **Nguồn giá:** `platform_core/llm/gia_token.py` — một chỗ duy nhất
- **Trạng thái:** `giu_cho_luot` (trần ước CAO) → gọi model → `quyet_toan_hoac_hoan`
- **Bất biến:** **INV-5** (dưới) · `BanError` ⇒ hoàn đủ, khách không trả cho việc máy bận
- **Thất bại phải đúng:** thiếu credit ⇒ 402 · máy B bận ⇒ 503 + hoàn ·
  **tiến trình bị giết giữa luồng ⇒ tiền phải về được**
- **Bằng chứng có:** E2 + **E4** (hai khoản kẹt thật 24/08) · **cần thêm:** E2 tái hiện việc giết tiến trình

### GJ-5 · Job hỏng / provider timeout → tiền đúng

- **Bất biến:** job vào trạng thái cuối ⇔ tiền đã kết sổ
- **Thất bại phải đúng:** worker chết ⇒ `reclaim_orphans` đưa job về trạng thái
  cuối ⇒ hoàn; hết lượt thử ⇒ `error` + hoàn
- **Bằng chứng có:** E2 (`test_193`)

### GJ-6 · Người trực tra một job của khách và **giải thích được tiền**

- **Thành công:** từ một `job_id`/`request_id` đọc ra: dòng thời gian sự kiện,
  lớp lỗi provider, giữ/quyết toán/hoàn, artifact
- ⚠️ **Lỗ đã biết:** một **giữ chỗ treo** hiện lên ở đâu? Trước 26/08: **không
  đâu cả.** Sau `a5274bf`: cảnh báo `HOLD_STRANDED` gửi người trực + có email
- **Bằng chứng có:** E2 (`test_307`)

---

## 4. Bất biến xuyên hành trình

```text
INV-1  Không đọc/ghi chéo chủ sở hữu.
INV-2  Không thu hai lần; không âm số dư ngoài ý muốn.
INV-3  Retry an toàn không tạo tác dụng phụ xa lần thứ hai.
INV-4  Job vào trạng thái cuối  ⇔  tiền đã kết sổ (settle HOẶC refund).
INV-5  ⭐ MỌI giữ chỗ cuối cùng đều kết sổ — KỂ CẢ giữ chỗ không có hàng Job.
INV-6  Artifact thuộc đúng chủ; khoá lưu trữ không đoán được.
INV-7  Giao diện nói thật về trạng thái — không CTA giả, không giá cứng lệch
       nguồn có thẩm quyền.
INV-8  Phục hồi được sau khi tiến trình/trình duyệt chết.
INV-9  ⭐ App nào sinh thẻ catalog/nav thì phải có trang để đáp xuống.
```

**INV-5 và INV-9 là hai bất biến MỚI**, và cả hai sinh từ lỗi thật đo được trong
đợt này, không từ suy luận:

- **INV-5** ← hai khoản giữ chỗ kẹt trên production 24/08. Hệ thống trước 26/08
  **không** bảo đảm nó. Nay đã có máy dò (`a5274bf`) — nhưng **chỉ báo, chưa tự
  hoàn**, nên INV-5 vẫn chưa được *bảo đảm*, chỉ được *quan sát*.
- **INV-9** ← `/ltt-llm` là một link 404 trong header của mọi khách đã đăng nhập.
  Nay được canh ở **hai** chỗ: `lint_app_contract` (chạy cả ở `--quick`) và
  `test_60`.

---

## 5. Chính sách chặn phát hành

```text
P0 mở                    : 0
P1 mở                    : 0, trừ khi chủ sản phẩm chấp nhận rủi ro CÓ LÝ DO VÀ CÓ HẠN
Golden Journeys          : PASS (GJ-1…GJ-6)
Bất biến INV-1…INV-9     : có phép kiểm, không chỉ có lời văn
gate.py ĐẦY ĐỦ           : PASS  (không phải --quick)
Bằng chứng trình duyệt   : E3 trên URL CÔNG KHAI, không chỉ loopback
```

⛔ **Ba cái bẫy đã trả giá, viết vào hợp đồng để không phải nhớ:**

1. `gate --quick` **không** chạy `pytest`. Ngày 25/08 hai phiên đều PASS `--quick`
   và đều bỏ lọt lỗi thật.
2. Loopback `127.0.0.1:8100` bỏ qua Cloudflare. Đã dính: `ltt.css` đúng ở origin,
   CF phục vụ bản cũ 4 giờ, chip hiện thành radio thô.
3. `gate.py` lấy dấu vân tay cây ở **cả hai đầu**. Ghi tệp trong lúc nó chạy làm
   cả lượt vô giá trị — đã xảy ra **ba lần** ngày 25/08.

---

## 6. Trạng thái bằng chứng hôm nay

| Hành trình | E1 | E2 | E3 | E4 |
|---|---|---|---|---|
| GJ-1 đăng ký/đăng nhập | ✅ | ✅ | ❌ | — |
| GJ-2 tool ảnh | ✅ | ✅ | ❌ | — |
| GJ-3 nạp credit | ✅ | ✅ | ❌ | — |
| GJ-4 API luồng | ✅ | ⚠️ một phần | ❌ | ⚠️ **có, và là bằng chứng LỖI** |
| GJ-5 hỏng → hoàn tiền | ✅ | ✅ | — | — |
| GJ-6 đường hỗ trợ | ✅ | ✅ *(mới)* | ❌ | — |

```text
GOLDEN_JOURNEYS_DEFINED:        YES
UNMEASURABLE_CRITICAL_OUTCOMES: 2   (time-to-value; số khách thật theo app)
```
