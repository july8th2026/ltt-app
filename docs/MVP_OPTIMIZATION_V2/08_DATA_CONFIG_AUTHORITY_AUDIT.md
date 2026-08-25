# 08 — DỮ LIỆU / CẤU HÌNH / THẨM QUYỀN / MIGRATION / RETENTION

**Ngày:** 2026-08-26 · **Cây:** `3d804ee`

---

## 1. Ma trận thẩm quyền

| Khái niệm | Một nguồn chân lý | Ai đọc | Ai ghi | Thi hành bằng |
|---|---|---|---|---|
| Vòng đời / bề mặt / public của app | `apps/<slug>/manifest.py` | `registry.discover` | chỉ tác giả app | `lint_app_contract`, `test_60` |
| Hiện trong catalog / nav | **`visible_on_surface()`** | header, catalog | — | `test_60` |
| Số dư credit | **tổng của `credit_entries`** | `credit.so_du` | chỉ `credit._ghi` | append-only + khoá hàng |
| Giá bán | `credit_cost` của manifest | `job_submit` | tác giả app | `test_261` |
| **Giá vốn** | **`platform_core/gia_von.json`** | `gia_von.py` | người cập nhật giá | `test_261` — miễn trừ phải có `ly_do` + `chu` + `han_ra_lai` |
| Giá token LLM | `platform_core/llm/gia_token.py` | `thanh_toan` | — | một chỗ duy nhất |
| Giá ảnh nhà | `apps/anhnoibo/gia.py` | `/gia-api` | — | công bố |
| Tool nào ra `/api/v1` | **ba cổng độc lập** | `catalog.py` | `api_exposed` + `api_contract` + `LTT_PUBLIC_API_TOOLS` | fail-closed |
| Schema / migration | `alembic/versions` | alembic | — | **một head** `a4d70e93f158`, 55 revision |
| Retention | `docs/DATA_RETENTION_POLICY.md` + `governance.py` | `_don_du_lieu_het_han` | — | 8 quy tắc chạy thật |
| Hồ sơ môi trường | `platform_core/settings.py` | `LTT_ENV` | — | ⭐ **không đọc tệp nào lúc khởi động** |

---

## 2. Ba thứ đang làm rất đúng, ghi vào danh sách giữ nguyên

### 2.1 `gia_von.json` — và bánh cóc quan trọng nhất kho

Một nguồn giá vốn, đơn vị **milli-credit số nguyên** (lý do viết rõ: dấu phẩy động
trong đường tiền là cách chắc chắn nhất để hai lần cộng ra hai kết quả), tên
trường lấy theo LiteLLM để nạp bảng của họ không cần lớp dịch.

⭐ Và `test_261` biến "bán dưới giá vốn" từ **tai nạn im lặng** thành **hành động
có tên và có hạn**. Nó sinh ra sau khi đo được nền tảng bán ảnh ở **45–57 % giá
vốn suốt 22 ngày** — `CREDIT_PER_IMAGE = 5` không sai lúc đặt, nó chỉ **không bao
giờ được nhìn lại, vì không có gì để so với**.

### 2.2 `/health/ready` không còn đọc tệp cấu hình nào

Trước đây `data/config.json` — cấu hình **của một app** — quyết định cả nền tảng
có "sẵn sàng" không, và trình quản lý dịch vụ khởi động lại theo câu trả lời đó.
Sự cố thật: BOM trong JSON ⇒ `json.load()` vỡ ⇒ 503 trong khi dịch vụ chạy bình
thường. Nay hồ sơ môi trường suy ra từ **một biến môi trường**. Một lớp lỗi bị
xoá, không chỉ một lỗi.

### 2.3 Không có cấu hình chết

106 biến `LTT_*` đọc trong mã · 42 đặt trên production · **0** biến đặt mà mã
không đọc.

---

## 3. Trôi dạt phát hiện được

### D-01 · P2 — `CLAUDE.md` nói cửa API đóng; production đã mở hai tool

`C:\LTTPlatform\secrets\app.env`: `LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`

`CLAUDE.md` mục Public API viết *"`LTT_PUBLIC_API_TOOLS` **rỗng** … còn nợ ba
việc: **mở tool** (bắt đầu bằng `image.thumbnail`)"*.

⛔ **Hai câu trong cùng một tài liệu mâu thuẫn nhau** — hàng H38 nói LLM *"ĐANG
BÁN 2026-08-24"*, hàng Public API vẫn nói cửa đóng. Một phiên sau đọc hàng Public
API sẽ tin `/api/v1` không phục vụ ai, rồi sửa nó **như sửa mã chết**. Nó đang
phục vụ khách trả tiền.

Thêm nữa: tool đã mở **không phải** `image.thumbnail` như kế hoạch ghi, mà là
`text.chat` + `image.ltt` — thứ tự mở cửa đã đổi trên thực tế mà kế hoạch chưa theo.

**Sửa tài liệu, không sửa cờ.** ⇒ Prompt 15 §8.

### D-02 · P3 — hai nguồn nói về cùng một thứ trong `taoanh`

`credit_cost` của manifest là giá bán; `gia_von.json` là giá vốn. Đúng và phải
khác nhau. Nhưng bậc `pro` **đã đóng** với ghi chú trong manifest, trong khi
danh sách miễn trừ của `test_261` là nơi có thẩm quyền cho việc đó. Không sai
hiện tại — chỉ là hai chỗ cùng kể một câu chuyện.

---

## 4. Migration / khôi phục

| Kiểm | Kết quả |
|---|---|
| Số head | **1** (`a4d70e93f158`) — không nhánh mồ côi |
| Số revision | 55 |
| Chạy migration trong deploy | ✅ `2-cai-dat.ps1` |
| Khôi phục giữ ràng buộc/chỉ mục | ✅ có `tools/restore_drill_schema.py` |
| Diễn tập khôi phục | ⚠️ có thư mục `restore_test_*` từ **2026-08-03** và **08-09** — chưa có lần nào gần đây |

⚠️ **Rủi ro chính không nằm ở schema** mà ở chỗ **bản sao lưu mới nhất là
2026-08-17** và **lịch sao lưu không tồn tại** — xem `10_...md` O-01. Một schema
khôi phục được mà không có dữ liệu để khôi phục thì không cứu được gì.

---

## 5. Việc còn nợ

| ID | Mức | Việc |
|---|---|---|
| **D-01** | P2 | Sửa `CLAUDE.md`: `LTT_PUBLIC_API_TOOLS` **không** rỗng — hai tool đang bán |
| **D-03** | P2 | Một diễn tập khôi phục mới, sau khi lịch sao lưu chạy lại |
| **D-02** | P3 | Gộp câu chuyện bậc `pro` của `taoanh` về một chỗ |

```text
NO_RUNTIME_CHANGE: NO
```
