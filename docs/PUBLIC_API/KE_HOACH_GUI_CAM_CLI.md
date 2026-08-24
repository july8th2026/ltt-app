# Kế hoạch: GUI desktop cho công cụ cắm CLI (C15-GUI)

**2026-08-24.** Chủ sản phẩm yêu cầu một GUI desktop thật cho `tools/cam_cli.py`,
theo đúng style của LTTSTUDIOSAPP. Tài liệu này ghi **phương án đã chọn, các
phương án đã loại và vì sao**, rồi mới tới bảng việc.

Nền: `tools/cam_cli.py` (đã xong, 12 test) là **lõi**. GUI là **vỏ**, không được
chứa một dòng nghiệp vụ nào.

---

## 0. Một câu kết luận trước, để không phải đọc hết

> **pywebview (WebView2 native, JS↔Python bridge), dùng lại `ltt.css` nguyên bản.**
> **Không** dựng máy chủ HTTP cục bộ — đó là lớp lỗ hổng đã có CVE thật, và công
> cụ này vừa **giữ khoá API** vừa **ghi tệp cấu hình**, tức đúng hai thứ đáng để
> tấn công.

---

## 1. Tra cộng đồng trước, rồi mới chọn

Theo yêu cầu của chủ sản phẩm ("tìm hiểu từ cộng đồng trước khi tự suy").

| Phương án | Cộng đồng nói gì | Quyết |
|---|---|---|
| **tkinter** | có sẵn trong Python, không cần cài gì. Nhưng *"a pure GUI library, instead of a complete GUI framework"* | ⛔ **loại** |
| **CustomTkinter** | ~11k sao, giao diện hiện đại trên nền tkinter | ⛔ **loại** |
| **PySide6 / Qt** | đầy đủ nhất, nhưng nặng và phải đóng gói | ⛔ **loại** |
| **Electron / Tauri** | quá nặng cho một công cụ ghi hai tệp cấu hình | ⛔ **loại** |
| **máy chủ HTTP cục bộ + trình duyệt** | *"Running HTTP-based servers locally without authentication is not recommended"* | 🔴 **loại — xem §2** |
| **pywebview** | *"lightweight native webview wrapper… does not bundle a heavy GUI toolkit or web renderer"* | ✅ **chọn** |

### Vì sao loại tkinter — và đây **không** phải lý do thẩm mỹ

Yêu cầu là *"theo style của lttstudiosapp"*. Ta **đã có** một hệ thống thiết kế
thật: `server/static/ltt.css`, **583 dòng, 24 biến token** (`--surface-canvas`,
`--brand-primary`, `--status-success`, `--focus-ring`, `--radius-lg`,
`--motion-fast`…).

tkinter **không dùng lại được một dòng nào** trong đó. Chọn tkinter là **vẽ lại
bằng tay** một hệ thống thiết kế đã tồn tại — và bản vẽ lại sẽ trôi khỏi bản gốc
ngay lần đầu ai đó sửa `ltt.css`. Đó là hai nguồn chân lý cho cùng một thứ.

⛔ Và đừng đọc ngược thành *"CustomTkinter đẹp hơn nên chọn nó"*: nó vẫn không
đọc được `ltt.css`, nên nó mắc **đúng** lỗi đó, chỉ là đẹp hơn khi mắc.

---

## 2. 🔴 Vì sao **KHÔNG** dựng máy chủ HTTP cục bộ

Đây là phương án trông hấp dẫn nhất: không phụ thuộc gì, mở trình duyệt mặc định,
dùng thẳng `ltt.css`. **Và nó là phương án nguy hiểm nhất.**

Công cụ này làm đúng hai việc đáng để tấn công:

1. **ghi tệp cấu hình** trong thư mục nhà của khách;
2. **giữ một khoá API tiêu được tiền**.

Một máy chủ HTTP cục bộ làm hai việc đó là **đúng mô tả của một lớp lỗ hổng đã
có CVE**: `CVE-2025-49596` (MCP Inspector) là RCE khai thác **từ trình duyệt** vào
một công cụ dev nghe cổng cục bộ.

Ba đường tấn công, và cái thứ ba là cái giết:

| | |
|---|---|
| **CSRF thường** | một trang bất kỳ khách đang mở `POST` sang `127.0.0.1:PORT` |
| **CORS lỏng** | trang lạ đọc được phản hồi |
| **DNS rebinding** | 🔴 *"Browsers won't notice cross-origin requests under DNS rebinding attacks"* — kẻ tấn công lấy được cả **token CSRF** rồi dùng nó. Tức **token một mình không cứu được** |

Chống được không? Được — chốt `Host`, chốt `Origin`, thêm nonce, chỉ nghe
`127.0.0.1`. Nhưng đó là **bốn lớp phòng thủ phải làm đúng cả bốn**, cho một công
cụ mà giá trị của nó chỉ là *"ghi hộ hai tệp"*.

⭐ **pywebview không có cổng nào cả.** Nó gọi Python qua `window.pywebview.api`
— một cầu nối trong tiến trình, **không phải HTTP**. Không có cổng để quét, không
có `Origin` để giả, không có gì cho DNS rebinding trỏ tới. **Cả lớp lỗ hổng biến
mất theo thiết kế, không phải theo phòng thủ.**

Và một điểm phụ nhưng thật: khoá API gõ trong **cửa sổ native** không đi vào
lịch sử trình duyệt, không bị trình quản lý mật khẩu bắt lưu, không nằm trong
`localStorage` của một origin nào.

---

## 3. Phụ thuộc: đo trên máy thật, không đoán

| | Trạng thái trên máy A (24/08) |
|---|---|
| **WebView2 Runtime** | ✅ **có sẵn, bản 149.0.4022.80** |
| **Microsoft Edge** | ✅ có |
| **Python** | ✅ 3.13.12 |
| **pywebview** | ✅ **đã cài, 5.3** |

WebView2 đi kèm Windows 11 và được Edge cài trên Windows 10 — tức **thực tế là có
sẵn**, không phải một thứ phải đi xin.

⚠️ Còn `pywebview` **là một `pip install`**. Nói thẳng: đây là phụ thuộc duy nhất,
và nó là cái giá phải trả.

Nhưng cái giá đó **rất thấp cho đúng nhóm khách này**: người dùng công cụ này là
người **đã cài Codex hoặc Claude Code** — tức đã có node/npm, đã quen terminal.
Một `pip install pywebview` không phải rào cản với họ.

⛔ **Và phải có đường lùi.** Không cài được `pywebview` thì công cụ **không được
chết**: nó rơi về `cam_cli.py` dạng dòng lệnh, thứ đã chạy được và đã có 12 test.
GUI là **tiện nghi**, không phải điều kiện.

---

## 4. Kiến trúc: vỏ mỏng, lõi đã có

```
tools/cam_cli.py          LÕI - da xong, 12 test. GUI KHONG duoc lap lai gi o day.
tools/cam_cli_gui.py      VO  - dung cua so, noi JS -> ham cua loi
tools/gui/index.html      giao dien
tools/gui/ltt.css         BAN SAO ltt.css, sinh tu ban goc (xem duoi)
cam_cli.bat               tim python -> chay GUI; khong co pywebview -> menu dong lenh
```

### 🔴 `ltt.css` phải **sinh ra**, không được chép tay

Chép tay là tạo bản thứ hai, và bản thứ hai **trôi** ngay lần đầu ai sửa bản gốc —
rồi công cụ trông *gần giống* nền tảng, kiểu sai khó chịu nhất.

⇒ `tools/dong_goi_gui.py` chép `server/static/ltt.css` sang `tools/gui/`, và một
**test chốt hai bản khớp nhau**. Lệch là gate đỏ.

⚠️ Cùng lớp với bài học cache-bust ở quy tắc 6 của `CLAUDE.md`: *một bản sao tĩnh
không có gì nhắc nó cập nhật thì nó sẽ không cập nhật.*

### Cầu nối — mặt tiếp xúc **hẹp có chủ ý**

```python
class Cau:
    def xem(self) -> dict          # dang cam gi
    def cam(self, khoa, toan_cuc) -> dict
    def go(self) -> dict
    def kiem(self) -> dict         # goi that mot luot
```

⛔ **Bốn hàm, không hơn.** Không `doc_tep`, không `chay_lenh`, không
`mo_thu_muc` — mỗi hàm thêm vào cầu nối là một hàm mã JS gọi được, và WebView2
render **HTML của ta hôm nay** thì không có nghĩa nó chỉ render thứ đó mãi.

---

## 5. Giao diện — bốn trạng thái, một màn hình

Không tab, không wizard. Công cụ này làm **một việc**, và người dùng cần thấy
**một câu**: *đang cắm hay chưa*.

```
┌──────────────────────────────────────────────┐
│  LTT Studios · Cắm công cụ viết mã           │
├──────────────────────────────────────────────┤
│  ● Chưa cắm          / ● Đang cắm            │
│                                              │
│  Khoá API   [ ltt_sk_·································· ] │
│             Lấy khoá ↗  (mở /developers/keys)│
│                                              │
│  ☐ Áp cho MỌI phiên Claude Code trên máy này │
│    ⚠ Kể cả gói Anthropic thật của bạn        │
│                                              │
│  [ Cắm vào ]   [ Kiểm thật ]   [ Gỡ ra ]     │
├──────────────────────────────────────────────┤
│  Codex          ~/.codex/config.toml      ✓  │
│  Claude Code    biến môi trường           ✓  │
│  Claude Desktop cấu hình tay  ⓘ chép giá trị │
└──────────────────────────────────────────────┘
```

### Bốn điểm giao diện có lý do, không phải trang trí

**① Ô "áp cho mọi phiên" mặc định TẮT, và có cảnh báo ngay cạnh.**
`ANTHROPIC_BASE_URL` trong `settings.json` là **toàn cục**. Một ô tích lặng lẽ ở
đây chuyển hướng cả gói Anthropic đang trả tiền của khách. Cảnh báo phải nằm
**cạnh ô**, không nằm trong tài liệu.

**② "Kiểm thật" là nút riêng, ngang hàng với "Cắm vào".**
*"Đã ghi tệp"* và *"cắm được rồi"* là hai câu khác nhau — cùng điểm mù với một job
báo `succeeded` mà khách không tải được ảnh. Nút này gọi **thật** một lượt.

**③ Claude Desktop hiện ra, kèm chữ "cấu hình tay".**
Nó **không** tự động hoá được (LevelDB của Electron). Giấu nó đi thì khách tưởng
đã xong; hiện nó ra kèm nút chép bốn giá trị là trung thực.

**④ Sau khi cắm, hiện to: "MỞ LẠI VS CODE".**
`setx` chỉ ăn với tiến trình **mới**. Đây là chỗ hay làm người ta tưởng công cụ
hỏng nhất.

⛔ **Không hiện lại khoá sau khi đã cắm.** `xem` chỉ nói *"đã đặt, N ký tự"*.

---

## 6. Bảng việc

| # | Việc | Đạt khi |
|---|---|---|
| **U1** | `dong_goi_gui.py` + test chốt `ltt.css` khớp bản gốc | sửa `ltt.css` mà quên đồng bộ ⇒ **gate đỏ** |
| **U2** | `cam_cli_gui.py`: cửa sổ + cầu nối 4 hàm | mở ra thấy đúng trạng thái hiện tại |
| **U3** | `index.html` một màn hình, dùng token của `ltt.css` | không có màu nào viết cứng |
| **U4** | Nối `cam` / `go` / `kiem`, hiện kết quả từng bước | mỗi dòng `[OK]`/`[!!]` của lõi lên đúng một dòng UI |
| **U5** | Đường lùi: không có `pywebview` ⇒ menu dòng lệnh | gỡ `pywebview` rồi chạy `.bat` vẫn dùng được |
| **U6** | Khối Claude Desktop + nút chép 4 giá trị | chép xong dán thẳng vào app được |
| **U7** | Test: cầu nối **không** lộ hàm nào ngoài 4 hàm | thêm hàm thứ 5 ⇒ test đỏ |
| **U8** | Thử trên **VM sạch** (Proxmox máy B) | máy không có gì ⇒ vẫn cắm được, hoặc **báo thiếu gì rất rõ** |

### Thứ tự, và vì sao

**U1 trước tất cả.** Nó là chốt chống trôi; làm sau thì đã có một bản sao chép tay
để mà quên.

**U5 trước U6.** Đường lùi phải chạy được **trước** khi thêm tiện nghi — nếu không,
tiện nghi sẽ được xây trên một giả định *"máy nào cũng có pywebview"* chưa ai kiểm.

**U8 cuối, và nó là phép thử THẬT.** Máy A có node, python, git, VS Code, npm.
Khách có thể **không có gì**. Mọi phép thử trước U8 chỉ chứng minh *"chạy trên máy
đã có đồ nghề"*.

---

## 7. ⛔ Cái **không** làm

| Không làm | Vì sao |
|---|---|
| Đóng gói `.exe` | Chủ sản phẩm chốt 24/08: `.bat` trước. Và một `.exe` nhỏ không ký số ghi vào thư mục cấu hình đúng là mô tả hành vi malware |
| Máy chủ HTTP cục bộ | §2. Đã có CVE thật cho đúng hình dạng này |
| Tự động hoá Claude Desktop | LevelDB của Electron. Sửa tay là hỏng lặng lẽ ở lần app cập nhật |
| Thêm hàm vào cầu nối "cho tiện" | Mỗi hàm là một hàm mã JS gọi được |
| Vẽ lại hệ thống thiết kế | `ltt.css` đã có 24 token. Bản thứ hai sẽ trôi |
| Hiện lại khoá sau khi cắm | Khoá chỉ hiện một lần lúc tạo, ở trang khoá |

---

## 8. Rủi ro còn lại, nói thẳng

| Rủi ro | Mức | Xử |
|---|---|---|
| Khách không cài được `pywebview` | trung bình | U5: rơi về dòng lệnh, **không chết** |
| WebView2 vắng trên một máy Win10 cũ | thấp | Edge cài nó; nếu vắng ⇒ cùng đường lùi U5 |
| `ltt.css` đổi mà bản sao không đổi | **cao nếu không có U1** | U1 đưa vào gate |
| Khách bật "toàn cục" rồi quên | trung bình | `go` trả về **đúng nguyên trạng** (đã có test bằng-từng-byte) |
| GUI ngốn thời gian mà khách vẫn dùng dòng lệnh | thật | U8 trả lời — nếu VM sạch cho thấy dòng lệnh là đủ thì **dừng ở đó** |
