# H38 — kế hoạch xử lý dứt điểm

**2026-08-24.** Chủ sản phẩm chốt: tập trung đóng H38 cho xong hẳn, không mở
mặt trận mới.

---

## 0. "Dứt điểm" nghĩa là gì — một câu, đo được

> **Một người lạ tìm được giá, đăng ký, lấy khoá, cắm vào công cụ của họ, gọi
> được, bị tính đúng tiền — và ta biết ngay nếu hỏng.**

Bảy vế. Mỗi vế phải **đi thử bằng mắt người lạ**, không phải bằng mắt người đã
biết đường. Hôm nay ta chứng minh được vế 5 và 6; năm vế còn lại **chưa ai đi**.

⛔ Không tính là xong nếu chỉ "có mã và có test". Đó đúng là thứ đã đúng suốt và
vẫn để lọt lỗi `VARCHAR(36)` tới tận lượt gọi thật đầu tiên.

---

## 1. Còn thiếu gì — bảy vế, soi từng cái

| Vế | Trạng thái | Việc |
|---|---|---|
| ① Tìm được **giá** | 🔴 chưa | trang giá công khai cho API, có ví dụ chi phí thật |
| ② **Đăng ký** | 🟡 có, chưa đi thử | đi hết luồng bằng một tài khoản mới toanh |
| ③ Lấy **khoá** | 🟡 có, chưa đi thử | như trên |
| ④ **Cắm vào công cụ** | 🟡 có trang, chưa có công cụ | `/developers/cli` đã có; còn **C15** tự ghi cấu hình |
| ⑤ **Gọi được** | ✅ | Codex CLI qua địa chỉ công khai, 31 giây |
| ⑥ **Tính đúng tiền** | ✅ | 3.042 → 3.037, đối chiếu tay khớp |
| ⑦ **Biết ngay nếu hỏng** | 🔴 chưa | giám sát **khách**, không phải giám sát máy |

Cộng thêm ba món nợ đã ghi: **C13** xoay khoá · **C16** thu tường lửa · `gate`
đầy đủ chưa chạy trọn lần nào.

---

## 2. Bốn đợt, làm dứt điểm

### Đợt A — an toàn vận hành (không cần chủ sản phẩm)

| # | Việc | Đạt khi |
|---|---|---|
| A1 | **C13** xoay bearer token cổng VLM: sinh khoá mới → `gateway.env` → khởi động lại cổng → cập nhật bản ghi `api_keys` | khoá cũ trả `401`, lượt gọi thật vẫn `200` |
| A2 | `gate.py` **đầy đủ** chạy trọn một lần | có dòng tổng kết, không bị cắt |

⚠️ A1 phải làm theo đúng thứ tự đó. Đổi `gateway.env` trước mà quên cập nhật
`api_keys` là **tự cắt đường của chính mình** — mọi lượt gọi trả `401` và triệu
chứng trông y hệt "máy B chết".

### Đợt B — bảy vế còn thiếu, phần viết được bằng mã

| # | Việc | Vì sao |
|---|---|---|
| B1 | **Trang giá công khai** cho API (vế ①) | khách phải biết giá **trước** khi đăng ký. Hôm nay giá chỉ nằm trong `gia_token.py` và trong đầu ta |
| B2 | **Giám sát khách** (vế ⑦): hết credit · tỉ lệ 5xx của `/api/v1` · lượt gọi thất bại liên tiếp của một khoá | hôm nay ta giám sát **máy B sống hay chết**, không giám sát **khách gọi có được không** |
| B3 | **C15** công cụ tự ghi cấu hình ba client (vế ④) | bài học nghimmo: thứ chặn khách là **điền cấu hình**, không phải giao thức |

### Đợt C — đi thử bằng mắt người lạ (vế ② ③)

| # | Việc | Đạt khi |
|---|---|---|
| C1 | Tạo **một tài khoản mới toanh**, đi hết: trang giá → đăng ký → nạp credit → tạo khoá → gọi lần đầu | **không mở tài liệu nội bộ lần nào** |
| C2 | Ghi lại **mọi chỗ vấp**, sửa từng chỗ | mỗi chỗ vấp là một khách sẽ bỏ đi |

⛔ Đợt này **không được làm bằng tài khoản admin**. Admin có sẵn credit, sẵn
quyền, sẵn hiểu biết — đi bằng nó là tự chứng minh cho mình.

### Đợt D — chốt (cần chủ sản phẩm)

| # | Việc | Ai |
|---|---|---|
| D1 | Phiên thật **Claude Code CLI** + **Claude Desktop** có gọi tool | chủ sản phẩm — máy này không có hai công cụ đó |
| D2 | **C16** thu tường lửa máy B về một IP | chủ sản phẩm (thiết lập bảo mật) |
| D3 | **Điều khoản sử dụng** cho API | chủ sản phẩm quyết nội dung; tôi soạn nháp |
| D4 | **Một khách thật** gọi và trả tiền | chủ sản phẩm |

---

## 3. Cái gì KHÔNG làm trong đợt này

| Không làm | Vì sao |
|---|---|
| Mở `qwen38-ops` (200K) | chưa ai chạm trần 64K. Mở là thêm VRAM và thêm một hồ sơ phải bảo trì |
| Streaming cho SDK OpenAI (`/chat/completions` + `stream`) | chưa client nào cần: SDK dùng non-streaming, CLI dùng hai route kia |
| Tool `text.vision` | `ltt_llm_vision` đã khai nhưng chưa ai gọi. Mở khi có người hỏi |
| Sửa cảnh báo metadata của Codex | không chặn gì; nó chỉ làm ước chi phí **của Codex** sai, không làm hoá đơn **của ta** sai |
| Đổi `AUOptions` máy B | thuộc việc vận hành máy B, không thuộc H38 |


---

## 7. Thi hành 24/08 — Đợt A và B

### A1 ✅ Xoay khoá cổng VLM

Bốn bước, đúng thứ tự, mỗi bước có chốt:

```
1. doi gateway.env tren may B   -> 15 dong, khong BOM
2. khoi dong lai cong VLM
3. kiem: khoa CU  -> 401     khoa MOI -> 200
4. cap nhat so khoa nen tang -> kiem toan tuyen qua Cloudflare -> 200, 82 delta
```

⚠️ Có một **khe hở vài giây** giữa bước 2 và 4 mà không cách nào tránh: cổng đã
đổi khoá còn nền tảng chưa. Chấp nhận được vì chưa có khách ngoài; ngày có khách
thì phải cho cổng nhận **hai khoá cùng lúc** trong lúc xoay.

### B1 ✅ Bảng giá công khai — `/gia-api`

🔴 Trang giá cũ (`/developers/pricing`) nằm **sau `require_account`**: muốn biết
giá thì phải đăng ký trước. Thứ tự ngược, và nó chặn đúng người cần nhất — người
đang **cân nhắc**.

Trang mới lấy số từ `gia_token.bang_gia()` — **chính hàm ra hoá đơn**, không gõ
lại vào template — kèm ba ví dụ chi phí thật và ba luật hay gây hiểu nhầm (trả
cho thứ đã sinh · ngắt giữa chừng vẫn tính · không đo được thì không thu).

### B2 ✅ Giám sát KHÁCH, không phải giám sát máy

Thêm `metrics.CREDIT_EXHAUSTED`, ngưỡng **3** trong một vòng bảo trì.

⛔ Cố ý **không** gộp vào `RESPONSES_5XX` hay `AUTH_FAILURE`: một khách hết tiền
không phải một hệ thống hỏng. Trộn hai thứ làm người trực mất khả năng phân biệt
"cần sửa" với "cần gọi điện" — và khi mọi thứ đều là báo động thì không gì là
báo động.

### B3 ✅ `sdk/ltt_cai_dat_cli.py` — công cụ tự ghi cấu hình

Một file, không phụ thuộc, chạy trên cả ba hệ. Cộng thêm chứ không đè · sao lưu
trước khi chạm · **không bao giờ ghi khoá vào file cấu hình** (file cấu hình bị
chia sẻ, bị commit, bị chụp màn hình) · chạy lại không tạo bản sao.

Claude Desktop **in các bước** thay vì giả vờ đã cấu hình — nó không có file nào
để ghi.

### 🔴 Và công cụ đó lập tức bắt được một lỗi ta suýt ship

Lần chạy đầu tiên trả `403`, trong khi `curl` cùng khoá cùng URL trả `200`. Khác
biệt duy nhất là **User-Agent**:

```
urllib mac dinh (`Python-urllib/3.x`)  ->  403
bat ky User-Agent nao khac             ->  200
```

**Cloudflare chặn trước khi request tới máy chủ ta**, nên log của ta trống trơn —
khách thấy 403 còn ta thấy im lặng.

Và ví dụ **"Python — no dependencies"** ta đang ship cho khách dùng đúng
`urllib` không đặt User-Agent. Khách copy–dán là ăn 403.

⚠️ Test cũ `test_vi_du_trong_tai_lieu_la_ma_CHAY_DUOC` chỉ **biên dịch** đoạn mã.
Biên dịch được không có nghĩa là chạy được — đúng QT-14, và lần này QT-14 tự
chứng minh nó cần tồn tại.

⛔ **Cách sửa đúng nằm ở Cloudflare, không ở tài liệu.** Bắt mọi khách tự đặt
User-Agent là một API tồi. Việc cần làm: thêm một quy tắc WAF **bỏ qua kiểm tra
bot cho `/api/v1/*`**. Đó là thao tác trên bảng điều khiển Cloudflare, thuộc chủ
sản phẩm. Trước khi có nó, tài liệu và công cụ đều đã đặt User-Agent.
