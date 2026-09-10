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
| LTT_LLM Text sinh thật | ✅ **09/09 23:35** — `nghiem_thu_chat_l1`, **cả ba cửa** đều 200 với token thật | máy B là **máy khác**; `LTT_LLM_BASE_URL` không đặt trong tiến trình này, cổng 8299 không trả lời từ đây |
| LTT_LLM VLM | ✅ **10/09 03:33** — `model=ltt_llm_vision`→`qwen38-vision`; ảnh sinh bằng mã, model trả `{"so_hinh_tron": 3, "chu": "K7QX"}`, **khớp đáp án** | như trên |
| LTT_IMAGE vẽ thật | ✅ **09/09 23:38** — job qua Public API → **ảnh 5.519.918 byte**, `held:3 charged:3`, `mode:"live"` | cổng 8199 không trả lời từ đây |
| Voice regression thật | ✅ **10/09 03:36** — job `7a0ea335` qua hàng đợi production → **8,48 giây tiếng, 814.124 byte RIFF/WAVE**; báo giá 2 = thu 2, số dư 37→35 | cần sidecar VOICE + GPU |
| Seedance/BytePlus regression | **NGOÀI PHẠM VI — 09/09** | chủ sản phẩm xác nhận *“đã chạy được thật”*; xem §11.3 |

⛔ **Không suy PASS từ "test xanh".** Bộ test dùng bộ điều phối giả; nó chứng
minh *đường đi đúng*, không chứng minh *máy B trả lời đúng*. Trộn hai câu ấy
lại là cách một nghiệm thu biến thành một lời hứa.

⇒ **Bốn** dòng còn lại phải chạy **trên máy chủ sau khi deploy** (pha 13).

## 11.3 🔴 Hai đính chính về chính kế hoạch này

### (a) Công cụ tôi ghi ở trên là **SAI công cụ**

Bản đầu mục này viết năm đường sẽ chạy bằng `tools/api_prod_canary.py`. Mở
chính công cụ ấy ra thì nó nói ngược lại:

> *Khoá cấp bằng `DEFAULT_SCOPES` (`tools:read` + `jobs:read`). `jobs:create`
> nằm trong `SPENDING_SCOPES` và **không** được cấp, nên khoá này **không nộp
> được việc** dù có credit.*

Nó là canary **chỉ-đọc** cho control-plane — cố ý, để một phép đo không đòi
tiêu tiền thì không tiêu tiền thật.

Công cụ đúng — và chúng **cố ý tiêu được tiền**, kèm ba hàng rào (tài khoản
riêng không phải admin · nạp đúng số credit vừa đủ vài lượt · không quyền admin):

| Đường | Công cụ |
|---|---|
| LTT_LLM Text | `tools/nghiem_thu_chat_l1.py` — đi **cả ba cửa** `/chat/completions` · `/messages` · `/responses` |
| LTT_IMAGE | `tools/nghiem_thu_anh_e2e.py` — từ ngoài vào qua Cloudflare |
| VLM | `tools/danh_gia_vision.py` — **phải đọc trước khi tin**, đúng bài học ở trên |
| Voice | `tools/chay_thu_ltt_voice.py` — cần sidecar VOICE + GPU |

⛔ **Bài học:** tôi viết tên một công cụ vào kế hoạch **mà không mở nó ra đọc**.
   Nó có tên đúng chủ đề nên nó **trông như** câu trả lời. Đọc `docstring` mất
   20 giây và nó nói thẳng ngược lại.

⭐ Và chính docstring của hai công cụ đúng phát biểu hộ lý do `NOT_TESTED` không
   thay được bằng test xanh: *739 test xanh vẫn để lọt lỗi `VARCHAR(36)` tới
   đúng lượt gọi thật đầu tiên, vì SQLite không ép độ dài mà PostgreSQL thì ép.*

### (b) Seedance/BytePlus — **bỏ khỏi phạm vi**, 09/09/2026

Chủ sản phẩm quyết: *“API seedance bỏ qua vì nó đã chạy được thật. Ta bỏ qua
hạng mục này.”*

⚠️ **Ghi cho đúng loại bằng chứng.** Đây là **lời xác nhận của chủ sản phẩm**
   rằng đường ấy đang chạy thật trên production — **không phải** một lượt đo do
   chiến dịch này thực hiện. Hai loại bằng chứng ấy **không thay nhau được**, và
   trộn chúng là cách một nghiệm thu tự nâng điểm cho mình.

⇒ Nên trục **E2E không được cộng điểm** cho dòng này; nó chỉ **rời khỏi danh
  sách việc phải làm**. Lý do bỏ cũng hợp lý độc lập với điểm số: chạy lại nó là
  tiêu **tiền thật với nhà cung cấp ngoài** cho một đường **không nằm trong phạm
  vi xóa của chiến dịch** — Seedance/BytePlus thuộc nhóm được phép giữ chạy.

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
| Legacy removal | **9/10** | 0 executable occurrence; 2 bộ dò độc lập. −1 vì **4 khoá legacy đang SỐNG trong CSDL sống sót qua MỌI phép kiểm** — `PHA15` §4 |
| Canonicality | **10/10** | một cửa `dieu_phoi.goi`, một bảng giá `image_gen/gia`, một `canonical` |
| App surface cleanliness | **9/10** | 4 lời nói dối với khách đã sửa; −1: `brand_directive` còn có thể khiến model vẽ chữ (chưa đo) |
| Registry / config | **10/10** | `is_active=False` + `chan_neu_da_ngung`; `test_1005` chốt 5 điều kiện |
| Secrets | **10/10** | `app.env` 4 khoá legacy → **0** · CSDL 4 khoá **đang sống** → **0** (có sao lưu) · dịch vụ `LTTStudioCodex` đã gỡ |
| Guard | **10/10** | `test_1006`: 18 phép kiểm, **12 là tự kiểm** (mẫu dương + âm) |
| E2E | **9/10** | egress = 0 · **4/4 đường sinh thật đã chứng minh** (Text · VLM · IMAGE · Voice); −1 vì Seedance dựa trên **lời xác nhận**, không phải phép đo |
| Seedance / Voice preservation | **10/10** | không đụng; `MIEN_TRU_HTTP` khai rõ đích đến, `test_45` PASS |
| Worktree hygiene | **9/10** | cây riêng, không đụng phiên khác; −1: đã chồng gate 2 lần trong ngày |

**Tổng: 86/100** — cập nhật 10/09 (E2E +3 · Secrets +2 · Legacy removal −1).

⚠️ Điểm **tăng 4 nhưng một trục bị HẠ**, và vế bị hạ mới đáng đọc: bốn khoá API của chính các nhà cung cấp đã gỡ **vẫn đang được cấp phát mỗi ngày** sau khi chiến dịch tuyên bố xong. Mọi phép kiểm đều soi **mã**; không phép kiểm nào soi **hàng trong bảng**.

### ⛔ Ba trục KHÔNG đạt 10, và không trục nào được làm tròn lên

- **E2E 6/10** — trục thấp nhất, và đúng như thế. ⚠️ **Việc Seedance rời khỏi phạm vi KHÔNG nâng điểm trục này**: bỏ bớt một dòng chưa đo không biến những dòng còn lại thành đã đo. Một nghiệm thu tự nâng điểm bằng cách thu hẹp mẫu số là một nghiệm thu đã hỏng. Không có máy B thì không có
  bằng chứng sinh thật. Nâng nó lên đòi một lượt chạy trên máy chủ, không đòi
  thêm một test nào ở đây.
- **Secrets 8/10** — token của một dịch vụ đã chết vẫn nằm trong `app.env`
  production. Xoá mã không xoá một biến môi trường đã ghi.
- **App surface 9/10** — `brand_directive` chưa đo.

---

## Việc còn lại trước khi đóng chiến dịch

| Pha | Việc | Chặn bởi |
|---|---|---|
| 13 | merge → deploy → **chạy 4 đường E2E thật** → dọn `LTT_CODEX_SIDECAR_TOKEN` → **gỡ dịch vụ `LTTStudioCodex`** | trunk đang có **2 bước gate đỏ** từ `3eae396d` (không phải của chiến dịch này) |
| 14 | dọn 22 nhánh remote | sau 13 |
| 15 | báo cáo nén kho | sau 14 |

⚠️ Hai bước đỏ của trunk là **điều kiện chặn**, và chúng thuộc chiến dịch ASV v4.
Đo lại ngay trước khi hoà — con số hôm nay hết hạn.
