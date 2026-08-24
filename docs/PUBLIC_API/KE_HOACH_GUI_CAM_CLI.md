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
>
> **Đóng gói: Nuitka/PyInstaller ở chế độ THƯ MỤC, rồi bọc bằng một installer.**
> Khách vẫn tải về **đúng một tệp `.exe`** — nhưng đó là **trình cài đặt**, không
> phải một khối tự-giải-nén. Xem §9: `--onefile` là bản *tệ nhất* cho đúng mục
> tiêu "nhìn chuyên nghiệp".

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
| `.exe` kiểu **onefile** (tự giải nén) | §9. Không phải "chưa làm" mà là **làm sai cách**. Chủ sản phẩm đã chốt là **có** đóng gói `.exe` |
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

---

## 9. 🔴 Đóng gói `.exe` — và vì sao "một tệp" **không** nên là `--onefile`

Chủ sản phẩm chốt 24/08: đích là **một `.exe`**, để *"nhìn chuyên nghiệp"*. Tôi
đã nêu lo ngại và chủ sản phẩm đã quyết — nên phần này là **cách làm cho đúng**,
không phải bàn lùi.

Nhưng có một chỗ **phải nói rõ, vì nó quyết định thành bại**: cách hiển nhiên
nhất để có "một tệp" lại là cách **phá hỏng đúng mục tiêu đó**.

### Vì sao `--onefile` tự đánh bại mục tiêu

Cả PyInstaller lẫn Nuitka đều có chế độ onefile, và **cả hai đều tự giải nén**:

> *"A one-file executable contains a massive, heavily compressed binary payload.
> When executed, it extracts dozens of DLLs and files into the user's local
> AppData/Local/Temp directory simultaneously. **Malware does this constantly to
> hide its true payload.**"*

Hệ quả với đúng công cụ này — nó **ghi tệp cấu hình** và **giữ khoá API**, tức
hồ sơ hành vi vốn đã giống thứ đáng nghi:

| | |
|---|---|
| Diệt virus | báo động giả **cao hơn hẳn** onedir |
| Khởi động | chậm mỗi lần chạy vì phải giải nén lại |
| SmartScreen | *"Windows protected your PC"* ngay lần đầu |

⇒ Khách tải về một tệp, bấm vào, và thấy **cảnh báo virus**. Đó là điều ngược
hẳn với *"nhìn chuyên nghiệp"*.

### ⭐ Cách vẫn cho khách **đúng một tệp**, mà không dính

**Bọc thư mục bằng một installer.** Khách tải về **một `.exe`** — và đó là
**trình cài đặt**:

```
LTTStudios-CamCLI-Setup.exe      <- MOT tep khach tai ve
   |
   +-- cai vao Program Files, tao loi tat, tao trinh go cai
   +-- ben trong la mot THU MUC (khong tu giai nen luc chay)
```

Được cả ba thứ mà onefile mất: **AV ít báo hơn**, **khởi động nhanh**, và **có
lối tắt + trình gỡ cài** — thứ mà một `.exe` trần **không** có, và chính là thứ
làm người ta thấy một phần mềm là "thật".

### Chọn bộ dựng: **đo, đừng đoán**

| | PyInstaller | Nuitka |
|---|---|---|
| Cách làm | gói interpreter + mã | **biên dịch sang C** rồi ra máy thật |
| AV | hay bị báo hơn | *"produces actual compiled code that looks much more like a normal application to AV heuristics"* |
| Dựng | nhanh | chậm hơn, cấu hình phức tạp hơn |

Nuitka **có vẻ** tốt hơn. Nhưng dự án này có luật: **chưa đo thì không chạy**.

⇒ **P1 dựng cả hai** ở chế độ thư mục, nộp cả hai lên VirusTotal, so số máy quét
báo. Rẻ, một buổi, và nó thay một cuộc tranh luận bằng một con số.

⛔ Và **đừng chọn Nuitka chỉ vì nó "nghe an toàn hơn"** — nếu số đo cho thấy cả
hai đều sạch thì chọn PyInstaller, vì dựng nhanh hơn là một lợi ích **thật** mỗi
ngày, còn "ít báo giả hơn về lý thuyết" thì không.

### 🔴 Ký số — đây mới là thứ quyết định "chuyên nghiệp"

Một GUI đẹp không cứu được lần chạy đầu tiên. Không ký số thì Windows hiện:

> **Windows protected your PC** — *Microsoft Defender SmartScreen prevented an
> unrecognised app from starting.*

Khách phải bấm *"More info → Run anyway"* — tức bấm qua một cảnh báo bảo mật để
dùng công cụ của một công ty bán hàng cho họ. **Đó là ấn tượng đầu tiên.**

> *"Code signing doesn't make false positives impossible, but it dramatically
> reduces them, especially with Windows Defender and SmartScreen."*

⚠️ **Hai điều phải biết trước khi mua chứng chỉ:**

1. **Chứng chỉ OV thường vẫn phải "tích danh tiếng"** — vài trăm lượt tải đầu
   vẫn có thể bị SmartScreen chặn. Chỉ **EV** mới được tin ngay, và nó đắt hơn.
2. **Từ 2023 khoá riêng bắt buộc nằm trong thiết bị phần cứng (HSM/token)**. Tức
   **không ký được trong CI** theo cách thông thường — phải có dịch vụ ký đám mây
   hoặc một máy cắm token. Đây là **việc vận hành**, không phải một dòng lệnh.

⇒ **Cần chủ sản phẩm quyết**: có mua chứng chỉ không, OV hay EV. Chưa quyết thì
vẫn làm được P1–P4 và phát bản chưa ký kèm hướng dẫn — nhưng **đừng gọi nó là
xong**, vì mục tiêu đặt ra là "nhìn chuyên nghiệp" và đó đúng là phần chưa đạt.

### Bảng việc đóng gói

### ✅ P1 + P2 — số đo thật, 24/08, và nó **lật kỳ vọng**

Dựng cả hai ở chế độ thư mục, quét bằng **Windows Defender cục bộ**
(`MpCmdRun.exe`) — không tải tệp lên đâu cả, và Defender đúng là thứ quyết định
với đa số người dùng Windows.

| | PyInstaller 6.11.1 | Nuitka 4.1.3 |
|---|---|---|
| Kích thước phát hành | **66,9 MB** (116 tệp) | 69,8 MB (43 tệp) |
| Thời gian dựng | **32 s** | **355 s** |
| Windows Defender | **SẠCH** | **SẠCH** |
| `--tu-kiem` sau đóng gói | ✅ | ✅ |

⇒ **P2 chốt: PyInstaller.** Đúng theo luật đã viết ra **trước khi đo**: *"nếu số
đo cho thấy cả hai đều sạch thì chọn PyInstaller, vì dựng nhanh hơn là một lợi
ích thật mỗi ngày, còn 'ít báo giả hơn về lý thuyết' thì không."*

Kích thước gần như bằng nhau (66,9 so với 69,8 MB), nên lợi thế duy nhất còn lại
của Nuitka là giả thuyết về AV — mà phép đo vừa bác bỏ. Đổi lại là **11 lần**
thời gian dựng.

⚠️ **Số đo này là của Defender, không phải của mọi máy quét.** Nó trả lời đúng
câu hỏi quan trọng nhất (đa số khách dùng Defender) và **không** trả lời câu
"mọi diệt virus đều sạch". Nếu sau này có khách báo bị chặn thì đó là lúc dùng P6,
không phải lúc kết luận phép đo này sai.

### 🔴 Một cái bẫy đã dính, ghi lại vì nó **không có log để đọc**

Bản đóng gói đầu tiên dựng xong, Defender sạch, kích thước đúng — và **sẽ mở ra
một cửa sổ trắng**. `THU_MUC_GUI` tính từ `__file__`, thứ **đổi nghĩa** khi đóng
băng: PyInstaller đặt tài sản ở `sys._MEIPASS`, còn Nuitka đặt cạnh `sys.executable`.

Ba dấu hiệu quen thuộc — *dựng OK*, *quét sạch*, *chạy được* — **không cái nào**
chạm tới câu hỏi thật: **tài sản có ở đó không?**

⇒ Đã thêm `--tu-kiem`: bản đóng gói **tự chứng minh** nó tìm được tài sản, in ra
đường dẫn thật rồi trả mã 0/1. Không cần ai ngồi nhìn cửa sổ.

⚠️ Và một phép dò **nói sai mà vẫn ra kết quả đúng** thì còn nguy hơn: bản Nuitka
báo `che do dong bang: False` nhưng vẫn tìm thấy tài sản — **do may**, vì
`__file__` tình cờ trỏ đúng vào `.dist`. Nuitka không đặt `sys.frozen`, nó đặt
`__compiled__`. Đã sửa.

### ✅ P3 — installer, và **gỡ cài mới là chốt thật**

```
LTTStudios-CamCLI-Setup-1.0.0.exe    24,7 MB   (nen tu 66,9 MB)
SHA256 b76b5d7c2a17e47669a5fd2a081f962c98e7eb3ba0fe7857c36686a32dd02224
```

| Bước | Kết quả |
|---|---|
| Defender quét installer | **SẠCH** |
| Cài im lặng | mã 0, vào `%LOCALAPPDATA%\Programs\` — **không cần admin** |
| `--tu-kiem` bản đã cài | ✅ đủ tài sản |
| Lối tắt Start Menu + gỡ cài | ✅ cả hai |
| **Gỡ cài** | thư mục **hết**, lối tắt **hết** |
| `~/.codex`, `~/.claude` sau khi gỡ | ⭐ **KHÔNG bị đụng tới** |

⭐ **`PrivilegesRequired=lowest` là quyết định, không phải mặc định.** Công cụ này
ghi vào `~/.codex`, `~/.claude` và biến môi trường **cấp người dùng**. Cài bằng
quyền admin rồi chạy bằng tài khoản khác là ghi vào **đúng thư mục nhà sai** — và
hỏng lặng lẽ.

⛔ **Gỡ cài KHÔNG được đụng vào cấu hình của khách.** `~/.codex/config.toml` là
thứ **khách đã tạo** qua công cụ, và gỡ một ứng dụng **không được** âm thầm sửa
cấu hình của ứng dụng khác. Muốn gỡ ra thì bấm **"Gỡ ra"** trong công cụ *trước*
khi gỡ cài — đó là đường đã có test chốt trả về **bằng từng byte**.

---

| # | Việc | Đạt khi |
|---|---|---|
| **P1** | Dựng **cả hai** (PyInstaller onedir + Nuitka standalone), nộp VirusTotal | có **số** so sánh, ghi vào tài liệu |
| **P2** | Chốt bộ dựng theo số đo P1 | lý do viết ra, không phải "nghe an toàn hơn" |
| **P3** | Installer Inno Setup: cài, lối tắt, **gỡ cài sạch** | gỡ cài xong không còn tệp nào ngoài cấu hình khách đã tạo |
| **P4** | Thử trên **VM Windows sạch** (Proxmox máy B) | máy không Python/không node ⇒ **vẫn chạy** |
| ~~**P5**~~ | ~~Ký số~~ | ⛔ **KHÔNG LÀM — chủ sản phẩm quyết 24/08.** Chấp nhận SmartScreen hỏi ở lần mở đầu. Xem dưới |
| **P6** | Nộp báo cáo dương-tính-giả cho hãng diệt virus nếu còn | dùng quy trình cộng đồng đã có |

### ⛔ Không mua chứng chỉ — quyết định 24/08, và hệ quả phải làm cho đúng

Chủ sản phẩm chốt: **không mua chứng chỉ ký số, chấp nhận khách bấm xác nhận**
khi mở tệp. Đây là một đánh đổi hợp lý ở giai đoạn này — chứng chỉ EV đắt, và
chứng chỉ OV thì vẫn phải tích danh tiếng nên vài trăm lượt tải đầu **cũng bị**
chặn. Tức tiền bỏ ra chưa chắc mua được thứ định mua.

⚠️ **Nhưng đã chấp nhận thì phải làm cho tử tế**, đừng để khách tự đoán:

1. **Nói trước, ở trang tải về.** Ảnh chụp đúng màn hình SmartScreen sẽ hiện,
   kèm câu *"bấm More info → Run anyway"*. Một cảnh báo **đã được báo trước**
   là một bước cài đặt; một cảnh báo **bất ngờ** là một lý do đóng trình duyệt.
2. **Công bố mã băm SHA-256** của tệp cài đặt cạnh đường tải. Không có chữ ký
   thì băm là thứ **duy nhất** còn lại để khách kiểm tệp đúng là của ta.
3. **P1 và P6 nay QUAN TRỌNG HƠN, không phải kém đi.** Không có chữ ký để
   giảm báo động giả, nên chọn đúng bộ dựng (P1) và nộp báo cáo dương-tính-giả
   (P6) là hàng phòng thủ **duy nhất** còn lại.

⛔ Và **tuyệt đối không** bảo khách *"tắt diệt virus đi rồi cài"*. Đó là dạy
khách một thói quen nguy hiểm để tiện cho ta.

⚠️ **P4 là chốt thật của cả phần đóng gói**, không phải P3. Một installer chạy
được trên máy **đã có Python** không chứng minh gì — cả mục đích của việc đóng
gói là để khách **không cần** Python.
