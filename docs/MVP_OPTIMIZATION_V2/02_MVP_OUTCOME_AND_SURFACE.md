# 02 — LỜI HỨA MVP, BỀ MẶT SẢN PHẨM, VÀ NHỮNG THỨ KHÔNG LÀM

**Ngày:** 2026-08-26 · **Cây:** `db6147e` · **Đầu vào:** 00, 01

---

## 0. ⛔ Một phép đo còn thiếu, và nó ảnh hưởng độ chắc của cả báo cáo

Báo cáo này cần biết: **app nào có khách thật, bao nhiêu job, thu bao nhiêu
credit.** Không có nó thì mọi phân loại dưới đây dựa trên *mã và ý định*, không
dựa trên *hành vi khách*.

Phép đo đã soạn (chỉ `COUNT`/`SUM`, không đọc nội dung) **bị cổng quyền của phiên
chặn** khi nối CSDL production. Tôi **không** đi vòng, và **không** nhờ phiên khác
chạy hộ — đó là lách quyền.

```text
CO_KHACH_THAT_KHONG:  UNMEASURABLE
```

Ảnh hưởng: mọi ô "đề xuất" ở mục 4 là **giả thuyết có cơ sở kỹ thuật**, chưa phải
kết luận sản phẩm. Ba nhãn `RETIRE_REMOVE_CANDIDATE` **không được thi hành** cho
tới khi có số.

⭐ Tiền lệ trong chính kho này cho thấy phép đo đó quyết định điều gì: đợt gỡ
`socialbot` an toàn **vì đã đo trước** — 0 job, 0 `app_access`, 0 `app_projects`,
không có `tokens.enc`. Không đo mà gỡ là đoán.

**Script đã sẵn** — chủ sản phẩm chạy được ngay:

```sql
SELECT app_slug, count(*) jobs, count(DISTINCT user_id) khach,
       min(created_at)::date dau, max(created_at)::date cuoi
FROM jobs GROUP BY app_slug ORDER BY jobs DESC;
```

---

## 1. Bề mặt thật — đo bằng chính hàm quyết định, không đọc mắt

Đọc bình luận manifest **không đủ**: `anhnoibo` có `public=True` trong lời gọi,
mà tài liệu nói nó không lên catalog. Cả hai đều đúng — vì `visible_on_surface()`
trả `False` khi có `catalog_parent`, và cột `public` một mình gây hiểu lầm.

Bảng dưới đây đọc từ `discover()` + `visible_on_surface()`:

| App | bật | cha catalog | khách ẩn danh thấy | khách đã đăng nhập thấy | lifecycle | tool API |
|---|---|---|---|---|---|---|
| `agent` | ✅ | — | ✅ | ✅ | development | 0 |
| `autosubvideo` | ✅ | — | ✅ | ✅ | development | 1 |
| `chataistudio` | ✅ | — | ✅ | ✅ | development | 0 |
| `prompt_ai_ommi` | ✅ | — | ✅ | ✅ | **released** | 2 |
| `taoanh` | ✅ | — | ✅ | ✅ | development | 2 |
| `taoclipngan` | ✅ | — | ✅ | ✅ | development | 1 |
| `taovideo` | ✅ | — | ✅ | ✅ | **released** | 1 |
| `upscalevideo` | ✅ | — | ✅ | ✅ | **released** | 2 |
| `ltt_llm` | ✅ | `chataistudio` | ❌ | ❌ | development | 1 |
| `anhnoibo` | ✅ | `taoanh` | ❌ | ❌ | development | 1 |
| `thumbnail` | ✅ | `taoanh` | ❌ | ❌ | development | 1 |
| `qualitylab` | ✅ | — | ❌ | ❌ (admin) | internal | 0 |
| `nexus` | ❌ cờ | — | *(bật thì ✅)* | *(bật thì ✅)* | **released** | 0 |
| `vps` | ❌ cờ | — | *(bật thì ✅)* | *(bật thì ✅)* | development | 0 |

**Con số thật:**

```
Khách ẩn danh thấy   : 8 app
Khách đã đăng nhập   : 8 app  (sau khi sửa ltt_llm)
Trong đó released    : 3      (prompt_ai_ommi, taovideo, upscalevideo)
Trong đó development : 5
App con (catalog_parent): 3   (anhnoibo, thumbnail, ltt_llm)
Tắt bằng cờ          : 2      (nexus, vps)
```

⚠️ **`ltt_llm` từng là 9, và cái thứ 9 là một link 404.** Đã sửa ở `db6147e` —
xem `01_...md` §6 và commit đó.

---

## 2. Phát hiện quan trọng nhất của prompt này

> **5 trên 8 sản phẩm khách nhìn thấy vẫn mang nhãn `lifecycle="development"`.**

Đây không phải một con số xấu. Nó là dấu hiệu của một điều khác:

⛔ **Bề mặt MVP hôm nay không do ai chọn.** Nó là **mặc định manifest cộng lại**:
`AppManifest.enabled` mặc định `True`, `public` mặc định `True`, `surface` mặc
định `"customer"`, `lifecycle` mặc định `"development"`. Viết một app mới mà
không khai gì thì nó **tự lên catalog công khai**.

Hệ quả với khách: một khách ẩn danh vào `app.lttstudios.com` thấy **8 sản phẩm**,
trong đó **5 cái chính nền tảng đang tự gọi là "đang phát triển"**. Đó là một
lời hứa mà không ai cố ý hứa.

**Đây là quyết định sản phẩm cần chốt, không phải lỗi kỹ thuật cần sửa.**

---

## 3. Lời hứa MVP — bản đề cử

Dựng từ thứ **đã thu được tiền thật**, không từ thứ đã tốn công xây:

> **Cho người sáng tạo nội dung tiếng Việt: biến một ý tưởng thành ảnh hoặc
> video dùng được, trả theo lượt bằng credit, không cần cài gì và không cần
> biết nhà cung cấp nào đứng sau.**

Ba mệnh đề phụ, mỗi cái có bằng chứng:

1. **Trả theo lượt, minh bạch** — sổ credit chỉ-ghi-thêm, `gia_von.json` là một
   nguồn giá vốn duy nhất, và `test_261` chặn bán dưới giá vốn bằng miễn trừ
   **có chữ ký và có hạn**.
2. **Không cần biết nhà cung cấp** — `api_contract` chiếu `params_schema` nội bộ
   thành hợp đồng công khai không lộ tên model thật.
3. **Có đường cho khách lập trình** — `/api/v1`, ba cổng độc lập, fail-closed.

---

## 4. Phân loại bề mặt — **đề xuất**, chưa thi hành

| App | Đề xuất | Vì sao |
|---|---|---|
| `taoanh` (+`thumbnail`, `anhnoibo`) | **MVP_CORE_SURFACE** | Đường ảnh là chuỗi hoàn chỉnh nhất: input → báo giá → job → kết quả → lịch sử, và là nơi giá vốn đã được đo kỹ nhất |
| `upscalevideo` | **MVP_CORE_SURFACE** | `released`, có đường GPU thật và đường Watch Agent bằng bearer token |
| `taovideo` | **MVP_CORE_SURFACE** | `released`, đường video async đã chạy |
| `prompt_ai_ommi` | **MVP_CORE_SURFACE** | `released`, 2 tool API |
| `chataistudio` (+`ltt_llm`) | **MVP_CORE_SURFACE** | Đang bán thật qua `/api/v1` (`text.chat`) |
| `autosubvideo` | **MVP_BETA_OPTIONAL** | 4 job type, route sát trần 899/900 — chín về tính năng, chưa chín về hình dạng |
| `taoclipngan` | **MVP_BETA_OPTIONAL** | engine vendor, phụ thuộc GPU nặng |
| `agent` | **DEFER_POST_MVP** | Q109 đã lấy mất 4 tool `asset.*` — node **đầu vào** của workflow. Đường đưa tệp vào Canvas hiện là ngõ cụt (R-01). Một sản phẩm mất đường vào không phải sản phẩm MVP |
| `qualitylab` | **INTERNAL_CAPABILITY** | `surface="admin"`, `internal` — đúng chỗ rồi |
| `nexus` | **MVP_SUPPORT_SURFACE** | `released`, đã thu credit thật; web chỉ là cửa giới thiệu + tài khoản |
| `vps` | **DEFER_POST_MVP** | ~95 % xong nhưng còn G7b/G9b, và khách **tự cài Windows** — gánh hỗ trợ khác hẳn phần còn lại của danh mục |

⛔ **Không nhãn `RETIRE_REMOVE_CANDIDATE` nào được đề xuất.** Lý do trung thực:
không có số dùng thật (§0) thì đề xuất gỡ là đoán — và kho này vừa trả giá cho
một lần đoán (Q109 lấy mất node đầu vào của Agent).

---

## 5. Non-goals — nói rõ những thứ MVP **không** hứa

1. **Không hứa model nhà đẹp hơn Gemini.** So mù G6b: phần có ý nghĩa **14–4
   nghiêng về Gemini**. Ảnh có chữ tiếng Việt thì trả lời Gemini, và đó là câu
   cuối.
2. **Không hứa video dài / tệp lớn qua web.** Cloudflare chặn ở 100 MB/request và
   100 giây chờ.
3. **Không hứa Agent Canvas là sản phẩm MVP.** Xem §4.
4. **Không hứa VPS trong MVP.** Cờ `LTT_VPS` chưa đặt, và đó là quyết định đúng.
5. **Không hứa SLA.** Chưa có baseline hiệu năng nào được đo trên lưu lượng thật.

---

## 6. Quyết định sản phẩm cần chốt

| ID | Câu hỏi | Vì sao không tự quyết được |
|---|---|---|
| **S-A** | 5 app `development` có được ở lại catalog **công khai** không? | Đây là lời hứa với khách, không phải cấu hình |
| **S-B** | `agent` giữ hay hoãn khi đường đưa tệp vào đã đứt? | Cần số dùng thật (§0) |
| **S-C** | Mặc định `AppManifest` có nên đổi thành `public=False`? | 1 chiều với app đang sống; nhưng nó là gốc của §2 |

⭐ **S-C là câu hỏi có giá trị lâu nhất.** Sửa 5 nhãn `lifecycle` chỉ chữa hôm
nay. Đổi mặc định — hoặc bắt manifest **khai tường minh** `public` — chữa cả
ngày mai: app tiếp theo sẽ không tự lên catalog công khai vì tác giả quên một
dòng. Cùng họ với luật vừa thêm vào `lint_app_contract` ở `db6147e`.

---

```text
NO_RUNTIME_CHANGE: NO   (xem 01_...md §5 — chủ sản phẩm đã bỏ cổng duyệt)
```
