# Pha 11 + 12 — Nghiệm thu egress và rà soát lại từ con số không

**Ngày:** 2026-09-09 · chiến dịch **LTT AI CLEAN REBUILD V2**
**Cây:** `D:\LTTSTUDIOSAPP-aiclean` · nhánh `phien/aiclean`

---

# PHA 11 — E2E / EGRESS ACCEPTANCE

Gói chiến dịch đòi một câu nghiêm khắc, và tôi giữ nó nguyên văn:

> ⛔ *"Không chạy thật ⇒ **NOT_TESTED**, không PASS."*

## 11.1 Cái ĐÃ chạy thật

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| **Đích đến outbound** trên handler job đã di trú | **0 lượt** tới nhà cung cấp đã gỡ | `tests/test_1007_e2e_egress.py`, 6 phép kiểm |
| `runtime_noi_bo` — cửa streaming | PASS | `test_600` + `test_162` (viết lại ở 06.3) |
| `jobs`/`credit`/`storage` | PASS | `test_193` · `test_203` · `test_207` (395 passed ở 06.3) |
| Public API | PASS | `test_181` · `test_187` · `test_190` · `test_195` · `test_212` |
| Cô lập theo người dùng | PASS | `test_71::test_image_route_chan_cross_user` · `test_117` |

### ⭐ Bẫy đặt ở tầng SOCKET, không ở `httpx`

Vá `httpx.post` chỉ bắt được thứ đi qua `httpx`. Một `requests`, một
`urllib.request`, hay một `http.client` sẽ **lọt qua im lặng** — và im lặng ở
đây trông y hệt *"không có lối ra nào"*. Bẫy đặt ở ba cửa: `getaddrinfo`,
`create_connection`, `socket.connect`.

### ⭐ Đối chứng đặt ở ĐẦU RA

`test_BAY_that_su_no` bắt bẫy nổ một lần. Thiếu nó thì mọi `assert == []` xanh
**vì bẫy không được gắn**, chứ không vì không có lượt gọi nào — và hai thứ ấy
trông giống hệt nhau.

## 11.2 🔴 Cái KHÔNG chạy được — khai **NOT_TESTED**, không khai PASS

| Hạng mục | Trạng thái | Vì sao |
|---|---|---|
| LTT_LLM Text sinh thật | **NOT_TESTED** | máy B là **máy khác**; `LTT_LLM_BASE_URL` không đặt trong tiến trình này, cổng 8299 không trả lời từ đây |
| LTT_LLM VLM | **NOT_TESTED** | như trên |
| LTT_IMAGE vẽ thật | **NOT_TESTED** | cổng 8199 không trả lời từ đây |
| Voice regression thật | **NOT_TESTED** | cần sidecar VOICE + GPU |
| Seedance/BytePlus regression | **NOT_TESTED** | cần khoá ModelArk thật + tiền thật |

⛔ **Không suy PASS từ "test xanh".** Bộ test dùng bộ điều phối giả; nó chứng
minh *đường đi đúng*, không chứng minh *máy B trả lời đúng*. Trộn hai câu ấy
lại là cách một nghiệm thu biến thành một lời hứa.

⇒ Năm dòng trên phải chạy **trên máy chủ sau khi deploy** (pha 13), với
`tools/api_prod_canary.py` và một lượt thật cho mỗi đường.

---

# PHA 12 — RÀ SOÁT LẠI TỪ CON SỐ KHÔNG

## 12.1 Phương pháp: **hai bộ dò độc lập**, không dùng chung một dòng mã

| | `tests/test_1006_rao_kien_truc.py` | bộ rà soát pha 12 |
|---|---|---|
| Cách đọc | đi cây **AST** | **token hoá** (`tokenize`), phân loại theo loại token |
| Phân biệt docstring | `ast.get_docstring` | STRING đứng một mình làm cả câu lệnh |
| Chạy ở | bộ test | script rời |

⭐ Cố ý **không** dùng lại hàm nào của `test_1006`: nếu bộ dò ấy sai thì dùng lại
   nó là sai theo. Đây đúng là điều gói chiến dịch đòi — *"không tin report cũ"*.

### 🔴 Và bộ dò thứ hai đã bắt được lỗi — của chính nó

Lượt đầu nó báo **2 EXECUTABLE occurrence**. Đọc ra thì cả hai là **docstring
của hàm**: tôi viết `continue` khi gặp `INDENT`/`NEWLINE` nên biến `truoc` không
bao giờ bằng `INDENT`, và mọi docstring của hàm bị xếp nhầm vào "mã chạy".

⛔ Nếu tôi tin ngay con số ấy, tôi đã báo động hai lỗi P1 không tồn tại. Một bộ
   dò mới **phải được nghi ngờ trước** — nhất là khi nó bất đồng với bộ dò cũ.

## 12.2 Kết quả sau khi sửa bộ dò

```
787 tep ma chay quet lai
EXECUTABLE occurrence (=> FAIL/P1) : 0
ARCHIVE_DOC / HISTORY occurrence   : 100 trong 64 tep   (duoc phep)
```

Hai bộ dò độc lập, hai cách đọc khác nhau, **cùng kết luận 0**.

## 12.3 Chấm điểm 0–100

| Trục | Điểm | Căn cứ |
|---|:--:|---|
| Legacy removal | **10/10** | 0 executable occurrence; 2 bộ dò độc lập |
| Canonicality | **10/10** | một cửa `dieu_phoi.goi`, một bảng giá `image_gen/gia`, một `canonical` |
| App surface cleanliness | **9/10** | 4 lời nói dối với khách đã sửa; −1: `brand_directive` còn có thể khiến model vẽ chữ (chưa đo) |
| Registry / config | **10/10** | `is_active=False` + `chan_neu_da_ngung`; `test_1005` chốt 5 điều kiện |
| Secrets | **8/10** | công cụ nhập khoá đã xoá; −2: `LTT_CODEX_SIDECAR_TOKEN` **còn trong `app.env` của máy chủ** — dọn ở pha 13 |
| Guard | **10/10** | `test_1006`: 18 phép kiểm, **12 là tự kiểm** (mẫu dương + âm) |
| E2E | **6/10** | egress = 0 chứng minh được; 5 đường sinh thật là **NOT_TESTED** |
| Seedance / Voice preservation | **10/10** | không đụng; `MIEN_TRU_HTTP` khai rõ đích đến, `test_45` PASS |
| Worktree hygiene | **9/10** | cây riêng, không đụng phiên khác; −1: đã chồng gate 2 lần trong ngày |

**Tổng: 82/100.**

### ⛔ Ba trục KHÔNG đạt 10, và không trục nào được làm tròn lên

- **E2E 6/10** — trục thấp nhất, và đúng như thế. Không có máy B thì không có
  bằng chứng sinh thật. Nâng nó lên đòi một lượt chạy trên máy chủ, không đòi
  thêm một test nào ở đây.
- **Secrets 8/10** — token của một dịch vụ đã chết vẫn nằm trong `app.env`
  production. Xoá mã không xoá một biến môi trường đã ghi.
- **App surface 9/10** — `brand_directive` chưa đo.

---

## Việc còn lại trước khi đóng chiến dịch

| Pha | Việc | Chặn bởi |
|---|---|---|
| 13 | merge → deploy → **chạy 5 đường E2E thật** → dọn `LTT_CODEX_SIDECAR_TOKEN` → **gỡ dịch vụ `LTTStudioCodex`** | trunk đang có **2 bước gate đỏ** từ `3eae396d` (không phải của chiến dịch này) |
| 14 | dọn 22 nhánh remote | sau 13 |
| 15 | báo cáo nén kho | sau 14 |

⚠️ Hai bước đỏ của trunk là **điều kiện chặn**, và chúng thuộc chiến dịch ASV v4.
Đo lại ngay trước khi hoà — con số hôm nay hết hạn.
