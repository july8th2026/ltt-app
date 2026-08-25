# 04 — KIẾN TRÚC / PHỤ THUỘC / BIÊN

**Ngày:** 2026-08-26 · **Cây:** `ede373a` · **Phương pháp:** phân tích AST 732 tệp `.py`, không grep

---

## 1. Kết luận trước, vì nó quyết định quy mô mọi thứ còn lại

```
platform_core → apps/*        0 cạnh
```

**Nền tảng thật sự nằm ở đáy đồ thị.** Công của H22 giữ được, và điều đó có một
hệ quả thực tế lớn: **không cần tái kiến trúc gì cả.** Mọi đề xuất dưới đây là
sửa nhỏ tại chỗ, và ba trong bốn cái là *khai báo một biên đã tồn tại* chứ không
phải *dựng một biên mới*.

Theo `01_MVP_REFERENCE_PRINCIPLES.md` §3 và `02_EXECUTION_RULES.md` §F: chỉ thêm
interface khi nó **giảm coupling thật**. Ở đây phần lớn giá trị nằm ở việc **ghi
luật cho thứ đã đúng**, để lần sau không ai đi chệch.

---

## 2. Bốn cạnh đáng soi

| ID | Cạnh | Lần | Phân loại |
|---|---|---|---|
| **A-01** | `apps/taovideo` → `apps/upscalevideo` | 2 | cross-product — **duy nhất của cả kho** |
| **A-02** | `server/api/*` → `apps/ltt_llm` | 5 | adapter biết tên một sản phẩm |
| **A-03** | `server/routes/dashboard` → `apps.anhnoibo.gia`<br>`server/routes/status` → `tools.doctor` | 1+1 | control plane biết giá một app; chu trình `server ↔ tools` |
| **A-04** | `apps/*` → `server.*` | **72** | **biên đã tồn tại nhưng chưa ai khai** |

### A-04 — đọc kỹ trước khi kết tội

72 cạnh nghe như thảm hoạ. Thực tế 12 app chạm **đúng bốn module**:

```
server.deps            22   (get_db, user_hien_tai)
server.auth.session    19   (require_login)
server.templating      17   (templates)
server.auth.csrf       14   (issue/verify_csrf_token)
```

Không app nào chạm sâu hơn. Đây **không phải** coupling lan man — đây là **hợp
đồng web của app**, đã ổn định, đang sống nhầm gói.

**Hai phương án:**

| | Việc | Chi phí | Được gì |
|---|---|---|---|
| **A** ⭐ | Khai vào `AGENTS.md` §8 rằng app **chỉ** được import 4 module này từ `server`, rồi mở rộng `lint_app_contract.py` thi hành | ~1 giờ, 0 rủi ro runtime | Chặn **vi phạm tương lai** — lần sau ai đó với tay sâu hơn thì gate đỏ |
| B | Dời sang `platform_core/web/` | 72 chỗ import trong 12 app | Một cái tên đúng hơn |

**Chọn A.** B trả 72 lần sửa để đổi lấy một cái tên đẹp hơn, mà rủi ro thật (ai
đó với tay sâu hơn) thì A đã chặn. Đây đúng §F: ưu tiên convention hiện có trước
khi dựng cơ chế mới.

### A-02 — và vì sao nó nặng hơn vẻ ngoài

`platform_core/public_api/config.py:20-22` **tự viết ra luật**:

> *"the names apps declare through `ToolSpec` — **this module must not know any
> of them**, see `AGENTS.md` 8.4"*

Trong khi `server/api/` nhắc `apps.ltt_llm` **5 lần** (`chat.py:75,98`;
`streaming.py:177,390,711`). Nền tảng có một luật thành văn, và tầng ngay cạnh
luật đó vi phạm.

Có lý do bào chữa thật: `/messages`, `/responses`, `/chat/completions` là hợp
đồng **tương thích OpenAI/Anthropic**, bản chất gắn với LLM. Nhưng lý do đó biện
minh cho *sự tồn tại của route*, **không** biện minh cho việc hằng số trần token
của một app (`MAX_TOKENS_TRAN`, `tran_theo_ngu_canh`) bị đọc thẳng từ tầng vận
chuyển.

### ⚠️ Đọc kỹ hơn: nó **không phải** chỉ là hằng số

Bản nháp mục này đề xuất *"đưa hai hằng số ra sau một bề mặt không mang tên app"*.
Đọc kỹ 5 chỗ import thì phạm vi rộng hơn thế:

```
chat.py:75        MAX_TOKENS_TRAN                     ← hằng số
chat.py:98        features                            ← HÀM NGHIỆP VỤ
streaming.py:177  features                            ← HÀM NGHIỆP VỤ
streaming.py:390  features                            ← HÀM NGHIỆP VỤ
streaming.py:711  MAX_TOKENS_MAC_DINH, tran_theo_ngu_canh
```

`features` cung cấp `uoc_token_vao()`, `kiem_tham_so()`, `chay()` — tức tầng vận
chuyển **gọi thẳng hàm nghiệp vụ** của một app, không chỉ đọc hằng số của nó.

⛔ **Nên không sửa vội, và đây là lý do.** Ba đường `/messages`, `/responses`,
`/chat/completions` là **streaming đồng bộ** — chúng *không thể* đi qua hàng đợi
job như mọi app khác, nên `registry`/`job_type` (primitive sẵn có) **không giải
được** ca này. Sửa đúng cần một khái niệm mới trong hợp đồng app: *executor đồng
bộ*, phân giải theo **năng lực** thay vì theo **tên**.

Theo §F, cơ chế mới chỉ được thêm khi 1–4 không giải quyết được — ca này **đúng
là** như vậy. Nhưng nó là **P2**, và thêm một khái niệm vào hợp đồng app là việc
đáng làm tỉnh táo, không phải việc đáng làm ở cuối một phiên dài.

**Đề xuất:** giữ nguyên, ghi thành **ngoại lệ có cổng thoát**:

1. Ghi vào `AGENTS.md` §8.4 rằng `server/api/` được biết `apps.ltt_llm` như một
   **ngoại lệ có tên**, kèm lý do (hợp đồng tương thích OpenAI/Anthropic là
   streaming đồng bộ).
2. Bất biến phải giữ: **trần token khách thấy không đổi một con số nào** — đã có
   `tests/golden/public_api_catalog_v1.json` chốt.
3. **Cổng thoát:** khi app thứ hai cần đường streaming đồng bộ, ngoại lệ hết hiệu
   lực và phải làm khái niệm *executor đồng bộ*. Một ngoại lệ cho một app là
   ngoại lệ; cho hai app là một cơ chế đang thiếu.

### A-01 — cạnh cross-product duy nhất

`apps/taovideo/routes.py:548,577` gọi `apps.upscalevideo.cost.uoc_luong_credit`
và `apps.upscalevideo.service.submit_upscale_job`.

⭐ Đọc thêm một tầng thì đây **không phải sai lầm cẩu thả**: hai thứ được gọi có
tên đúng nghĩa bề mặt công khai (`service.submit_*`, `cost.uoc_luong_*`). Vấn đề
là bề mặt đó **chưa được khai là công khai**, nên không có gì ngăn lần sau ai đó
với tay vào chỗ sâu hơn.

**Đề xuất:** khai nó là bề mặt công khai của `upscalevideo` (nhỏ, hướng use-case,
có chủ rõ) và chốt bằng lint rằng chỉ hai thứ đó được gọi từ ngoài. **Không cắt
cạnh** — cắt nó nghĩa là dời việc điều phối đi đâu đó, và không có chỗ nào tốt hơn
chỗ hiện tại.

### A-03 — hai cạnh nhỏ

- `server/routes/status.py:80` → `tools.doctor`: chu trình mức gói `server ↔ tools`.
  Production **không** chạy `tools/`, nên đây là phụ thuộc vào mã chỉ-dành-cho-phát-triển.
- `server/routes/dashboard.py:134` → `apps.anhnoibo.gia`: control plane biết giá
  của một app. Đã có bề mặt chung `/gia-api` — nên dùng nó.

Cả hai P3. Làm khi tiện, không phải blocker.

---

## 3. Chỉ số

| Chỉ số | Giá trị |
|---|---|
| Chu trình mức gói | **1** (`server ↔ tools`) |
| Cạnh cross-product | **1** (A-01) |
| Cạnh `platform_core → apps` | **0** |
| Truy cập dữ liệu chéo chủ | **0** phát hiện |
| Tệp chạm mỗi commit (trung vị, 30 commit gần nhất) | **4** |

Trung vị 4 tệp/commit là **định vị thay đổi lành mạnh**. Với `01_MVP_REFERENCE_PRINCIPLES.md`
§4 (Change Locality > số dòng đẹp), đây là chỉ số quan trọng hơn mọi số LOC trong
báo cáo 05.

---

## 4. DANH SÁCH KHÔNG ĐƯỢC ĐỔI

1. `platform_core` ở đáy đồ thị — 0 cạnh xuống `apps`.
2. `platform_core/leases.py` + `gpu_lease` (đập nhịp, thu hồi mồ côi).
3. `gia_von.json` là **một** nguồn giá vốn + `test_261` miễn trừ có chữ ký/hạn.
4. Ba cổng độc lập của tool `/api/v1` (`api_exposed` + `api_contract` + cờ operator).
5. `_khoa_so_du_user` khoá hàng trước khi đọc số dư.
6. Một alembic head.
7. `visible_on_surface()` là **một** nguồn chân lý cho catalog/header.

---

```text
NO_RUNTIME_CHANGE: NO   (chủ sản phẩm đã bỏ cổng duyệt — xem 01 §5)
```
