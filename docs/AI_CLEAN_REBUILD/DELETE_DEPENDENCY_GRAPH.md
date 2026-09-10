# DELETE DEPENDENCY GRAPH — pha 02

> Thứ tự xoá. Đây **không** phải một danh sách việc — nó là câu trả lời cho
> `AGENTS.md` §4c câu 1: *"nếu chỉ MỘT SỐ chỗ nhận bản vá, chuyện gì xảy ra?"*

## 1. Vì sao thứ tự là bắt buộc

Xoá động cơ trước khi chuyển người gọi ⇒ **mọi caller nổ**. Chế độ hỏng đó *tệ
hơn bệnh nó chữa*, và §4c gọi thẳng đó là **thiết kế sai**, không phải "chấp
nhận được trong lúc lan".

```
                     ┌─────────────────────────────┐
   pha 03  MAP       │ chot san pham -> dong co LTT │   khong sua ma
                     └──────────────┬──────────────┘
                                    v
                     ┌─────────────────────────────┐
   pha 04  BLOCK     │ fail-closed: chan REQUEST    │   legacy khong tao
                     │ MOI toi 5 ho. Doc lich su    │   duoc luot goi moi,
                     │ VAN chay.                    │   nhung ma van con
                     └──────────────┬──────────────┘
                                    v
        ┌───────────────────────────┴───────────────────────────┐
        v                                                       v
  pha 05 TEXT/VLM -> LTT_LLM                        pha 06 IMAGE -> LTT_IMAGE
  autosubvideo · taovideo · prompt_ai_ommi          taoanh · thumbnail · anhnoibo
  chataistudio · planner                            (E03, E05, dich_gemini)
  (E01, E02, E04, E07)
        └───────────────────────────┬───────────────────────────┘
                                    v
                     ┌─────────────────────────────┐
   pha 07  DELETE    │ dong co: dich_gemini ·       │  luc nay KHONG con
        RUNTIME      │ dieu_phoi nhanh gemini ·     │  caller nao
                     │ codex_sidecar/ · doi_chung   │
                     └──────────────┬──────────────┘
                                    v
                     ┌─────────────────────────────┐
   pha 08  DELETE    │ be mat app: manifest · route │
        SURFACES     │ · UI selector · JS/template  │
                     └──────────────┬──────────────┘
                                    v
                     ┌─────────────────────────────┐
   pha 09  CONFIG    │ REGISTRY 3 muc · api_pool    │
        + SECRET     │ rows · env · khoa            │
                     └─────────────────────────────┘
```

## 2. Cạnh phụ thuộc — ai phải chết SAU ai

| Phải xoá | …chỉ sau khi | Vì |
|---|---|---|
| `platform_core/image_gen/dich_gemini.py` | `taoanh`, `thumbnail`, **`anhnoibo`** đã chuyển | `anhnoibo/jobs.py:110` gọi `dich_gemini.goi_gemini` |
| nhánh `gemini` trong `platform_core/llm/dieu_phoi.py` | `autosubvideo`, `taovideo`, `prompt_ai_ommi`, **`planner`** đã chuyển | `planner.py:20` khai `("ltt_llm","gemini")` |
| `codex_sidecar/` | `apps/chataistudio` đã chuyển sang LTT_LLM | `sidecar_client.py` gọi loopback vào sidecar |
| 3 mục `REGISTRY` trong `providers.py` | mọi caller ở trên đã chết | `providers.get("gemini")` còn 25 nơi import |
| hàng `api_pool` + khoá | `REGISTRY` đã xoá | khoá mồ côi thì vô hại, khoá **có** provider sống thì không |
| **6 công cụ** `TOOLING_UPDATE` | **cùng lúc** với `codex_sidecar/` | `gate.py:1285`, `check_mypy.py:58` quét **theo danh sách thư mục** — thư mục biến mất thì chúng hỏng |
| **97 tệp** `TEST_UPDATE` | **cùng changeset** với thứ chúng chốt | Không trước (đỏ giả), không sau (cửa mở trống) |

### ⛔ Hai cạnh dễ quên nhất

1. **`tools/gate.py` nằm trong đồ thị này.** `THU_MUC_CHUP` và danh sách quét
   `mypy` đều liệt kê `codex_sidecar` **theo tên**. Xoá thư mục mà không sửa hai
   danh sách ⇒ chính cổng chất lượng đỏ, và nó sẽ trông như một lỗi của người
   khác. `gate.py` là **tệp dùng chung** ⇒ `Edit`, **không bao giờ `Write`**.

2. **`codex_sidecar/` NẰM TRONG `THU_MUC_CHUP`** (`gate.py:1285`). Một thư mục
   biến mất giữa lượt gate của phiên khác = `CAY DA DOI GIUA CHUNG`. ⇒ Pha 07
   phải **xin cửa sổ riêng**, thông báo giờ + thời lượng, chờ xác nhận.

## 3. Điều gì chứng minh mỗi pha đã xong

| Pha | Bằng chứng phải có |
|---|---|
| 04 | Phép kiểm chứng minh một request legacy **không tạo lối ra mạng nào** — đo **egress**, không đo tên gói |
| 05/06 | Sản phẩm chạy trên LTT, và `OUTBOUND_EGRESS_MATRIX` giảm từ 8 xuống 0 |
| 07 | `git grep` 5 họ trên `*.py` không còn dòng lớp `MA` nào ngoài 54 tệp `NOT_A_LEGACY_SURFACE` |
| 09 | Năm điều kiện `HISTORY_ONLY`, mỗi điều kiện **một phép kiểm** ở dải `1000–1099` |

⚠️ Và phép kiểm phải hỏi **HÀNH VI**: *thứ tôi khẳng định có tồn tại được nếu
chương trình không chạy không?* Một bánh cóc AST hỏi *"còn `import
google.generativeai` không"* vẫn xanh khi ai đó gọi cùng endpoint bằng
`httpx.post`. Điều kiện "không network egress" phải đo **lối ra**, không đo tên gói.

## 4. Thứ KHÔNG nằm trong đồ thị

`NOT_A_LEGACY_SURFACE` (54 tệp) không có cạnh nào, không có pha nào, không có
việc gì. Chúng ở trong `LEGACY_SURFACE_MATRIX.csv` **chỉ để nói rằng chúng đã
được xét và bị loại** — nếu không, lượt rà soát sau sẽ tìm lại đúng 54 tệp ấy và
hỏi lại đúng câu hỏi ấy.
