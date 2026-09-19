# Quy ước kỹ thuật của dự án

Áp dụng cho mọi phiên làm việc trên `D:\LTTSTUDIOSAPP`, cho cả người và Claude.

Tệp này **chỉ** giữ quy ước kỹ thuật. Hai nguồn chân lý, mỗi thứ một nơi:

- **Sản phẩm** (đã chốt gì, vì sao): `docs/QUYET_DINH_NEN_TANG.md`.
- **Quy trình** (mở phiên đọc gì, test/gate khi nào, commit, gộp `main`, deploy,
  khi nào dừng): `docs/00_LTT_OPERATING_CONTRACT.md`.

Chuyện kể và sự cố đứng sau các luật dưới đây: `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
(phụ lục *"chuyện kể chuyển từ AGENTS.md"*). `docs/_luutru/` là lịch sử — đọc để
hiểu *vì sao*, **không làm theo**.

## 0. Mở phiên, vận hành liên tục

→ `docs/00_LTT_OPERATING_CONTRACT.md` §1, §10, §10b. Nâng quyền Administrator:
`python tools\nang_quyen.py` (§9.3).

## 1. Đọc trước khi sửa

→ `docs/00_LTT_OPERATING_CONTRACT.md` §2. Định vị code bằng `grep`/`Glob` trên
chính cây nguồn, rồi đọc chính các tệp sắp sửa.

## 2. Ranh giới không được vượt

1. **`D:\BOT GEMINI` chỉ đọc.** Đang phục vụ người dùng thật. Không sửa, không
   tạo, không xoá, không chạy script ghi file bên đó. Muốn dùng lại thì **copy
   sang** `D:\LTTSTUDIOSAPP` rồi làm trên bản copy.
2. **Không import chéo** giữa hai cây mã nguồn.
3. **Thêm app = thêm một thư mục trong `apps/`.** Không sửa `platform_core/`
   hay `server/`. Nếu thấy buộc phải sửa → **dừng lại và giải thích vì sao**;
   đó là dấu hiệu hợp đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không
   đi vòng.
4. **App socialbot đã bị gỡ hẳn** (Q108 thay Q10), cùng `core/`, `utils/`,
   `server/services/`. Đừng dựng lại — `tests/test_60_app_registry.py` chốt.
   Muốn đưa về thì đó là một quyết định sản phẩm.
5. Cổng của nền tảng là **8100**. Cổng 8000 thuộc về hệ thống khác trên cùng máy.
6. Deploy, đổi DNS: → `docs/16_CAP_NHAT_VA_DEPLOY.md`.

## 3. Bí mật

- Không bao giờ đưa giá trị bí mật (token, khoá, mật khẩu, nội dung file
  service-account) vào code, tài liệu, git, log, ảnh chụp màn hình hay tóm tắt
  hội thoại. Chỉ được ghi **tên** biến, nơi lưu, trạng thái xoay vòng.
- Bí mật sống ngoài mã nguồn, nạp từ biến môi trường hoặc thư mục được bảo vệ.
- Máy quét: `python tools/scan_source_secrets.py` — phải 0 finding (gate chạy nó
  ở bước `secret scan`).
- Nếu phát hiện bí mật lọt vào file được theo dõi: che đi, báo người dùng xoay
  vòng khoá, ghi vào nhật ký — **không chép giá trị đó đi đâu cả**.

### 3b. Tài khoản test vận hành

Kiểm GUI trên production dùng **`akakenly.design@gmail.com`** — tài khoản
**thường**, không phải admin (chủ dự án chỉ định; có thể đổi). Không mượn admin:
admin thấy nhiều hơn khách thật, và lượt kiểm lẫn vào tài khoản quyền cao nhất.
Bốn tài khoản test cũ (`autosub-test@`, `api-load-canary@`, `vps-thu@`,
`reviewer-test@`) là tài khoản **khoá API** — không mở được bề mặt web.

**Mật khẩu không nằm trong kho này.** Nó đi qua biến môi trường lúc chạy
(quy ước của `tests/test_74_smoke_playwright.py`):

```
LTT_SMOKE_USER=...  LTT_SMOKE_PASS=...  node tools/kiem_chatltt_gui.mjs \
    --url https://app.lttstudios.com --anh tmp/kiem_gui_prod
```

⛔ **Claude không gõ mật khẩu vào form đăng nhập**, kể cả khi chủ dự án đưa
trực tiếp trong hội thoại. Chủ dự án khởi động lệnh hoặc tự đăng nhập trong
Chrome thật (§9.1); Claude đọc `bao_cao.json` rồi phân tích.

## 4. Kỷ luật thay đổi

- Làm **thay đổi nhỏ nhất còn trọn nghĩa** cho hạng mục đang mở.
- Mỗi thay đổi hành vi phải có test đi kèm.
- Viết code mới thì đặt đúng chỗ ngay từ đầu — **mục 8 (Bố cục mã nguồn)**.
- Không xoá test đang xanh, trừ khi có quyết định sản phẩm được ghi lại.
- Nhịp test/gate và điều kiện deploy: **`docs/00_LTT_OPERATING_CONTRACT.md` §4, §8**.
  Mục 4b chỉ giữ sự thật kỹ thuật.
- Ghi **đúng lệnh đã chạy và kết quả thật**; phân biệt `đã chạy` / `chưa chạy` /
  `pass` / `fail`. Không tuyên bố hoàn thành dựa trên kế hoạch hay số test thu
  thập được.
- Thay đổi rủi ro: viết trước cách lùi lại, rồi mới làm.

## 4c. Sửa hạ tầng dùng chung — ba câu hỏi trước dòng mã đầu tiên

Áp cho mọi thay đổi trong `tools/`, `platform_core/`, `tests/conftest.py` — mọi
thứ **nhiều cây cùng chạy**. Chuyện kể: BAY, phụ lục §4c.

1. **Nếu chỉ MỘT SỐ cây nhận bản vá, chuyện gì xảy ra?** Mỗi worktree chạy bản
   `tools/` của **riêng nó**. ⛔ Câu trả lời là *"tệ hơn trước khi vá"* (cây đã
   vá chờ, cây chưa vá chạy tự do) ⇒ **thiết kế sai**.
2. **Đường SUY BIẾN của cơ chế này là gì?** Mọi cơ chế điều phối có một nhánh
   "không giữ được gì" (không khoá, cache rỗng, thiếu `psutil`). Trên nhánh ấy
   bản vá còn đúng không? ⭐ **Cố ý** phải phân biệt được với **tai nạn**.
3. **Tôi đang hỏi một NHÃN hay một QUAN HỆ?** Nhãn (tên tệp, chuỗi cmdline, biến
   môi trường, tên nhánh) rẻ và **sai im lặng**; quan hệ (cha-con, `cwd`, ai giữ
   khoá, commit tổ tiên) mới đúng. ⛔ Điều kiện phải là thứ tiến trình đang hỏi
   **không thể tự thoả** — loại `os.getpid()` **và** `parents()`.

**Sau khi vá, bánh cóc phải hỏi HÀNH VI, không hỏi hình dạng.** Câu tự hỏi: *thứ
tôi đang khẳng định có tồn tại được nếu chương trình không chạy không?* Có ⇒ nó
không kiểm hành vi, dù nó **đỏ được** khi bị tiêm. ⚠️ *"Đỏ được"* và *"đo đúng
thứ cần đo"* là **hai** câu hỏi.

## 4d. Sổ lỗi TỰ GÂY — các lớp và cơ chế

Kỷ luật phải áp cả cho **công cụ dùng để đo** (script tạm), không chỉ mã sản
phẩm. Chuyện kể, bảng số và ngày: BAY, phụ lục §4d.

### Lớp A — gọi một API mà không đọc chữ ký trước

⇒ `python tools\do_nhanh.py chu-ky <tep> <ten_ham>` in chữ ký thật từ AST.

### Lớp B — script TẠM lặp lại một cái bẫy đã có ghi chú

(`print` vỡ cp1252 · heredoc Bash nuốt `\` · lọc tiến trình khớp chính mình)
⇒ `tools/do_nhanh.py`: `ra()` thay `print`, `thay()` thay `str.replace`,
`tien_trinh()` thay mọi bộ lọc tiến trình. **Không sinh mã qua heredoc Bash**:
soạn bằng công cụ Write rồi chạy tệp.

### Lớp C — phép kiểm chốt MÔI TRƯỜNG hoặc HÌNH DẠNG thay vì HÀNH VI

⇒ Phép đo **hai chiều**, cả hai bắt buộc: ① chạy dưới điều kiện ngược (có tải /
dưới gate) để chắc nó **không phụ thuộc môi trường**; ② tiêm lại bản cũ để chắc
nó **đỏ được**. Và đối chiếu với **sự thật ĐỘC LẬP**, không với số do chính công
cụ ấy sinh ra (mốc lấy bằng `--accept` của chính nó: hỏng so với hỏng vẫn bằng).

⇒ Nghi một cụm phép kiểm là lớp C thì **chạy đột biến**, đừng suy đoán:

```
py -m cosmic_ray.cli init <cấu-hình>.toml <phiên>.sqlite
py -m cosmic_ray.cli exec <cấu-hình>.toml <phiên>.sqlite
```

⚠️ `cosmic-ray` **sửa tệp tại chỗ** ⇒ chạy trong cây riêng
(`git worktree add --detach`). Lệnh nặng → `docs/QUY_TAC_CHAY_LENH_NANG.md`.
`mutmut` **không chạy được trên Windows**.

### Lớp D — commit vào trunk trước khi có gate xanh

→ `docs/00_LTT_OPERATING_CONTRACT.md` §7.

### Lớp E — phép đo của tôi báo sai, và tôi suýt sửa thứ không hỏng

Ba kiểu báo sai: đọc sai **nguồn** (template thay vì `frontend/*/src`) · mẫu quá
hẹp về **ngôn ngữ** · mẫu quá hẹp về **kỹ thuật**. Cả ba đều báo THIẾU thứ đang
có. ⇒ Trước khi hành động theo một phép đo mới, **mở tay hai mẫu mà nó tố cáo**;
cả hai vô tội ⇒ bộ dò sai. ⚠️ Đừng biến bộ dò như thế thành cổng.

### Dấu hiệu nhận ra mình đang ở trong một lớp

- *"Tôi nhớ hàm này nhận tham số gì"* → **lớp A**
- *"Chỗ này chỉ là script đo, không cần cẩn thận"* → **lớp B**
- *"Chạy tay xanh rồi, chắc ổn"* → **lớp C**
- *"Gate lâu quá, commit trước rồi chạy sau"* → **lớp D**
- *"Phép đo mới toanh cho ra một con số cao đáng ngạc nhiên"* → **lớp E**

## 4b. Chạy test — phần KỸ THUẬT

🔑 **Cấp nào chạy khi nào: `docs/00_LTT_OPERATING_CONTRACT.md` §4.** Mục này chỉ
giữ sự thật kỹ thuật mà hợp đồng trỏ tới. Lệnh gate: `python tools\gate.py`.

⚠️ **`npm run build` phải là việc CUỐI trước gate, sau cả việc sửa test.**
`build_release._frontend_source_sha256` băm **cả** thư mục frontend — gồm cả
`tests/`. Thêm một phép kiểm vitest cũng làm bundle bị coi là **cũ**, và gate đỏ ở
chỗ không liên quan (`test_44_release_build`, `test_95_agent_canvas_build`,
`test_103_autosub_projects`: *"bundle is stale or built with the wrong Node"*).

⛔ **`--tuan-tu` KHÔNG phải `--noi-tiep`.** `--tuan-tu` xếp hàng các **bước**;
bước `bo test` bên trong vẫn tự mở nhiều worker pytest. `--noi-tiep` hạ **cả
hai** mức: một bước một lúc, **và** một tiến trình pytest (không xdist, không
pha 2), frontend `--maxWorkers=1`. Dùng khi — và chỉ khi — "đỏ khi chạy cả bộ,
xanh khi chạy một mình": đó là bằng chứng về lỗi **cách ly** (hoặc máy quá tải),
chưa chỉ ra lỗi ở đâu. Nơi tìm: `tests/test_631_cach_ly_bo_test.py`.

### Thêm test mới thì nhớ ba điều

1. Test **ghi vào tệp thật trong kho** phải khai vào
   `tools/test_nhanh.py::TEP_NOI_TIEP` (chạy nối tiếp ở pha 2; `test_309` chốt),
   và phải khôi phục **đúng từng byte VÀ đúng dấu thời gian** (`write_bytes` +
   `os.utime`). Thiếu một trong hai thì `gate.py` in *"CÂY ĐÃ ĐỔI TRONG LÚC
   CHẠY"* và cả lượt chạy thành vô giá trị.
2. Test **không được đọc trạng thái máy** (tải GPU, tốc độ CPU, số tiến trình).
   Tiêm stub cho mọi thứ nó phụ thuộc. **Một phép kiểm đọc trạng thái máy không
   đo thứ nó nói là đang đo — nó đo cái máy.**
3. **`skip` cho điều kiện của MÔI TRƯỜNG; `assert` cho dữ liệu nằm TRONG KHO.**
   Đúng: `test_74::pytestmark` (thiếu `LTT_SMOKE_URL`), `test_821::pg`,
   `test_826::pg_engine` — thiếu Postgres/cổng/GPU là thứ máy **có thể thật sự
   thiếu**. ⛔ Một `skip` trên dữ liệu trong kho không nổ được và **tệ hơn vô
   dụng**: nó cộng vào bánh cóc `bo qua` và làm bản kiểm kê nói phép kiểm ấy
   **có thể vắng mặt hợp lệ**. Đổi sang `assert` kèm số đo trong thông điệp,
   đừng chạy `check_bo_qua.py --accept`. (Ca thật: BAY, phụ lục §4b.)

### Kiểm tra bằng trình duyệt

Test xanh **không** chứng minh trang hiển thị đúng. Sau mỗi thay đổi giao diện
hoặc luồng người dùng: mở trình duyệt, tái hiện luồng, xem console error, xem
request hỏng, xác minh trên giao diện thật. Lệnh: §9.1.

## 5. Quy tắc bắt buộc trên Windows

Bốn điều dưới đây đều **đã thực sự gây sự cố** trong dự án này:

1. **Ghi file cấu hình phải KHÔNG BOM.**
   ```powershell
   [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
   ```
   `Out-File -Encoding utf8` và `Set-Content -Encoding utf8` của PowerShell 5.1
   chèn BOM → `json.load()` vỡ → `/health/ready` trả 503 trong khi dịch vụ vẫn
   chạy bình thường. Có test chốt (`tests/test_61_setup_scripts.py`).

2. **File `.ps1` phải thuần ASCII.** PowerShell 5.1 đọc `.ps1` không BOM theo
   bảng mã ANSI; một dấu tiếng Việt làm hỏng cả câu lệnh và báo lỗi ở dòng khác.

3. **Không viết Python inline qua PowerShell.** PowerShell nuốt dấu ngoặc kép
   khi truyền cho `.exe`, nên `r"C:\path"` tới Python thành `rC:\path`. Ghi ra
   file `.py` rồi chạy.

4. **Mọi đường dẫn dữ liệu đi qua `platform_core.runtime_paths.data_path()`.**
   Chuỗi `os.path.join("data", ...)` là tương đối theo thư mục làm việc; trên
   máy chủ nó rơi vào `app\data\` — thư mục **bị xoá và thay toàn bộ mỗi lần
   cập nhật**. Có test chốt (`tests/test_62_khoa_logic.py`).

## 6. Quy tắc cập nhật memory

Memory ở đây gồm ba tầng, mỗi tầng một nhiệm vụ. **Đừng trộn lẫn.**

| Tầng | File | Chứa gì | Cập nhật khi nào |
|---|---|---|---|
| **Quyết định** | `docs/QUYET_DINH_NEN_TANG.md` | Điều đã chốt và **vì sao**. Ít thay đổi. | Khi có quyết định kiến trúc/sản phẩm mới, hoặc đổi hướng |
| **Kế hoạch** | `docs/KE_HOACH_TRIEN_KHAI.md` | Việc cần làm, tiêu chí hoàn thành, tiến độ | Khi xong một hạng mục, hoặc khi phát hiện việc mới |
| **Nhật ký** | `docs/NHAT_KY.md` | Đã làm gì, lệnh nào chạy, kết quả thật | Cuối mỗi phiên có thay đổi code |

Memory tự động của Claude (`.claude/projects/.../memory/`) chỉ giữ **sự thật
không suy ra được từ kho** và **phản hồi của chủ dự án** — không bao giờ giữ luật
hay nhật ký phiên.

### Sau khi xong MỘT hạng mục — làm đủ bốn việc

Không được bỏ việc nào. Bỏ một việc là lần sau phải đoán.

1. **Đánh dấu `[x]`** hạng mục đó trong `KE_HOACH_TRIEN_KHAI.md`, ghi kèm ngày
   và kết quả test thật.
2. **Ghi một mục vào `NHAT_KY.md`** theo mẫu ở cuối file đó.
3. **Nếu trong lúc làm phát sinh quyết định mới** → thêm dòng vào bảng quyết
   định (xem giao thức bên dưới).
4. **Commit theo hợp đồng §7**, thông điệp nói rõ *vì sao*, không chỉ *cái gì*.

### Giao thức đổi quyết định — chống chồng chéo quy tắc

1. **Không sửa đè lên dòng quyết định cũ.** Mất lý do là mai sau lặp lại đúng
   cuộc tranh luận đã xong.
2. Đánh dấu dòng cũ là **`~~ĐÃ THAY~~`**, ghi rõ *thay bởi quyết định nào*
   và *ngày nào*.
3. Thêm dòng mới với số thứ tự kế tiếp, ghi **vì sao đổi** — không chỉ ghi
   quyết định mới là gì.
4. **Truy ngược mọi nơi đang nói theo quyết định cũ** và sửa cùng lúc:
   ```powershell
   git grep -n "<gia tri cu>"
   ```
   Sót một chỗ là tạo ra hai quy tắc mâu thuẫn.
5. Nếu quyết định cũ có **test chốt** trong `tests/test_62_khoa_logic.py` thì
   sửa hoặc gỡ test đó **trong cùng một commit**. Một test khoá quy tắc đã chết
   sẽ chặn việc đúng.
6. Ghi vào `NHAT_KY.md`: đổi gì, vì sao, đã dọn những đâu.

**Nguyên tắc gốc:** tại một thời điểm, mỗi câu hỏi chỉ được có **đúng một câu
trả lời đang hiệu lực**. Câu trả lời cũ được phép tồn tại, nhưng phải mang nhãn
"đã chết" rõ ràng để không ai làm theo nhầm.

## 7. Khi không chắc

Nói thẳng là không chắc, kèm cách kiểm chứng. Không đoán rồi trình bày như sự
thật. Nếu phát hiện người dùng hiểu sai điều gì, hoặc cách làm đang có vấn đề,
**nói trước khi làm** chứ đừng lặng lẽ làm theo.

## 8. Bố cục mã nguồn — nơi từng thứ phải nằm

Hợp đồng app quy định `manifest.py` / `routes.py` / `jobs.py`; mục này nói thêm
**logic nghiệp vụ nằm ở đâu**. (Vì sao có mục này: BAY, phụ lục §8.)

### 8.1 Trong một app

```
apps/<slug>/
  manifest.py   bản khai. Nền tảng CHỈ đọc file này.
  routes.py     CHỈ lo HTTP: đọc request, kiểm quyền/CSRF, gọi service, dựng
                phản hồi. KHÔNG chứa quy tắc nghiệp vụ.
  jobs.py       handler chạy trong worker.
  services/     quy tắc nghiệp vụ khi app có NHIỀU miền (mỗi miền một file).
  features.py   quy tắc nghiệp vụ khi app chỉ có MỘT miền.
  cost.py       quy tắc tính giá, nếu tách riêng được.
  tables.py     bảng CSDL riêng của app (kèm `table_prefix` trong manifest).
```

`tables.py` chứ không phải `models.py`: `apps/taovideo/models.py` đã tồn tại và
là **sổ đăng ký model AI**, không phải bảng CSDL. Trùng tên gây hiểu nhầm ngay.

### 8.2 Ngưỡng máy kiểm — `tools/lint_app_contract.py`

Ngưỡng số dòng và số handler của `routes.py` là hằng `MAX_ROUTES_LINES` /
`MAX_ROUTES_HANDLERS` trong `tools/lint_app_contract.py` — nguồn duy nhất, đừng
chép số vào đây. Vượt thì WARN: tách theo miền ra `services/`. Nhiều handler mà
không có tầng nghiệp vụ cũng WARN — logic đang nằm sai chỗ.

Tách `routes.py` thành package thì giữ nguyên bề mặt: `routes/__init__.py` chỉ
export `router` và import các module miền để handler kịp đăng ký.

### 8.2b App được dùng **đúng bốn** module của `server` — không hơn

```
server.deps            get_db, user_hien_tai
server.auth.session    require_login
server.auth.csrf       issue_csrf_token, verify_csrf_token
server.templating      templates
```

Đây là **hợp đồng web của app**. ⛔ **Import bất cứ thứ gì khác từ `server` là
gate ĐỎ** — `tools/lint_app_contract.py` thi hành (bước `app contract lint`).
Cần thêm một module vào danh sách? Đó là **một quyết định kiến trúc** — sửa
`SERVER_APP_CO_THE_DUNG` có chủ ý và ghi lý do, đừng làm cho tiện.

### 8.2c App sinh thẻ catalog/nav thì **phải có trang để đáp xuống**

`surface="customer"` + không `catalog_parent` + không `routes.py` ⇒ gate **ĐỎ**
(`nav_entries()` tự sinh một dòng trỏ vào `route_prefix` khi app không khai `nav`).
Chưa có giao diện thì khai `catalog_parent="<app cha>"`. **Đừng** chữa bằng cách
đổi `surface` — Public API chỉ nhận `"customer"`, đổi là đóng luôn đường bán API.

### 8.3 Việc dùng chung thì ở `platform_core`, không ở app

App gọi vào ruột app khác = gỡ hay đổi tên app đó làm gãy app không liên quan.

**Cạnh app→app: mặc định CẤM, trừ cạnh đã khai** trong `APP_DUOC_DUNG_APP`
(`tools/lint_app_contract.py`) — nguồn duy nhất, đừng chép danh sách vào đây.
⛔ Chốt cả **TÊN được import**, không chỉ tên module, và theo **từng cặp** app —
mỗi cạnh là một quyết định riêng. ⚠️ `test_308` chốt **hai chiều**: thêm cạnh mà
quên khai thì đỏ, *và* khai một cạnh không còn ai dùng cũng đỏ.

| Việc | Dùng | Đừng tự viết lại |
|---|---|---|
| Kiểm ảnh người dùng tải lên | `platform_core.image_input.validate_reference` | |
| Đường dẫn bundle React đã build | `platform_core.frontend_bundle.bundle_assets` | |

**Không neo đường dẫn bằng `Path(__file__).parents[n]`.** Đếm cấp thư mục sai
ngay khi file đổi chỗ, và hỏng **lặng lẽ** (trang vẫn trả 200 với vỏ trống). Neo
bằng tên thư mục (`platform_core/frontend_bundle.py` làm mẫu). `test_148` chặn.

### 8.4 `platform_core` không được biết tên app nào

Kể cả trong chú thích và docstring —
`test_no_app_slug_is_hardcoded_in_the_platform` bắt.

### 8.5 Gate kiểm gì

Danh sách bước: `tools/gate.py::_steps` — nguồn duy nhất. Khi nào chạy:
`docs/00_LTT_OPERATING_CONTRACT.md` §4.

## 9. Trình duyệt và lệnh cần tương tác

### 9.1 Mở trình duyệt

**Production (`https://app.lttstudios.com`): mặc định NỐI VÀO Chrome thật qua
`--cdp`.** Playwright tự khởi chạy Chrome (kể cả với `--profile`) mang cờ
automation và bị Cloudflare trả CAPTCHA xoay vòng ở `/login`. Chủ dự án mở Chrome
thật với `--remote-debugging-port=9222` (vd. `--user-data-dir=C:\LTTBrowserProfiles\ChatLTTKiem2`),
tự qua xác minh và tự đăng nhập; bộ kiểm nối vào:

```bash
node tools/kiem_chatltt_gui.mjs --url https://app.lttstudios.com --cdp http://127.0.0.1:9222
```

⛔ Bộ kiểm **không đóng** trình duyệt khi xong — cửa sổ là của người dùng.

Trang không đi qua Cloudflare (loopback `127.0.0.1:8100`, trang tĩnh): được để
Playwright tự mở, với hồ sơ của dự án — **`--headed`** (không có thì cửa sổ chạy
ẩn), **`--profile=...`** (`--persistent` không kèm đường dẫn tạo hồ sơ TRẮNG),
**`-s=ltt`** (phiên đặt tên, không đụng phiên khác):

```bash
playwright-cli -s=ltt open --browser=chrome --headed \
  --profile="C:\LTTBrowserProfiles\PlenXResearch" <url>
```

### 9.2 Lệnh cần nhập mật khẩu / xác thực

Shell của Claude **không tương tác được**. Mọi lệnh cần nhập (git push lần đầu,
đăng nhập cloud) sẽ chết với `fatal: Cannot prompt because user interactivity has
been disabled.` hoặc `/dev/tty: No such device or address`. Mở cửa sổ mới **thôi
chưa đủ** — nó kế thừa môi trường đã tắt tương tác. Phải kèm
**`-UseNewEnvironment`**, và cho script **ghi log ra file** (`Tee-Object`):

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
  '-File','"<script>.ps1"' -UseNewEnvironment
```

PowerShell coi stderr của `git` là `NativeCommandError` — **không phải lỗi**.
Chỉ tin `EXITCODE`.

### 9.3 Chạy lệnh cần quyền Administrator

Dùng **`python tools\nang_quyen.py <script.py> [tham số]`** (hoặc `--lenh "..."`).
Nó lấy kết quả và mã thoát về.

⚠️ Bẫy nó tránh: `Start-Process -Verb RunAs` **không dùng được cùng**
`-RedirectStandardOutput` — hỏng **im lặng** (không log, thoát sau một giây như
đã chạy xong). Và `EXITCODE` **rỗng** nghĩa là tiến trình không chạy — khác hẳn
`EXITCODE=0`. (Khuôn hai lớp cũ: BAY, phụ lục §9.3.)

## 10. Tệp dùng chung — khi buộc chung một cây

Mặc định mỗi phiên một worktree — tạo, gộp `main`, gỡ: `docs/QUY_TRINH_WORKTREE.md`.
Mục này là quy ước **kỹ thuật** cho lúc nhiều phiên buộc phải chạm cùng tệp.
(Chuyện kể: BAY, phụ lục §10.)

### 10.2 Tệp DÙNG CHUNG: chỉ `Edit` khớp chuỗi chính xác, KHÔNG `Write`/`cat >`

`Write` đè cả tệp **im lặng**; một `git commit` whole-file nuốt phần dở của phiên
kia. Chốt ranh giới tệp với phiên kia (`ListAgents` → `SendMessage`) trước khi sửa.

| Tệp | Cách chia |
|---|---|
| `server/static/ltt.css` | mỗi khu một **khối có nhãn** ở cuối tệp (`LỚP NGỮ NGHĨA CỦA KHU VPS`, `.khu-dev`). Hai vùng tách rời ⇒ không xung đột, miễn không ai ghi đè cả tệp |
| `locale/en/LC_MESSAGES/messages.po` | **chỉ nối thêm cuối**, và **đọc lại tệp ngay trước mỗi lần ghi**. Giữ LF, không BOM. ⛔ Không chạy `i18n.py trich` — nó xếp lại cả tệp. Kiểm 0 msgid trùng sau cùng |
| `server/templates/_kieu_chung.html`, `base.html` | **nhắn trước khi sửa** — luật ở đó chạm mọi trang của mọi app, nên chúng không thuộc khu của ai |
| `CLAUDE.md`, `AGENTS.md`, `tools/gate.py` | chỉ `Edit` |

**Commit chọn lọc:** `git add` từng path của mình, rồi kiểm `git diff --cached`
không dính tệp phiên kia.

### 10.3 Đo baseline: đừng `git stash`

`git stash` cuốn cả phần dở của phiên kia rồi trả lại; một lần ghi xen giữa
`stash` và `pop` là một xung đột. Muốn đo baseline sạch:

```bash
git worktree add --detach <tmp> HEAD   # đo ở đây
git worktree remove --force <tmp>
```

### 10.4 Báo cho nhau thứ mình bắt được ở khu của họ

Lỗi tìm thấy trong khu của phiên khác thì **nhắn cho chủ khu** — đừng tự sửa, đừng
`# noqa` hộ. Ba lớp lỗi hay gặp, chỉ hiện khi render/chạy thật:

1. `button, .btn` trong `_kieu_chung.html` (nội tuyến, đứng sau `ltt.css`) thắng
   mọi luật `.btn-*` một-class ⇒ viết `.btn.<lop>` (0,2,0); kiểm `getComputedStyle`.
2. Rác test lọt vào tệp thật khi lượt chạy bị ngắt giữa `write`↔`finally`.
3. Chỗ-giữ khoá API phải đúng ký tự `…` (U+2026), không phải `...` — `test_272`.

### 10.5 `memory/` cũng là thư mục dùng chung

`.claude/projects/D--LTTSTUDIOSAPP/memory/` dùng chung cho **mọi phiên của dự
án**. Trước khi ghi một memory mới, **đọc `MEMORY.md`**. Trùng thì **gộp vào bản
có sẵn**, chuyển bản trùng vào `memory/_luutru/` và bỏ dòng chỉ mục của nó.

### 10.6 Deploy từ cây riêng bị chặn

`setup\2-cai-dat.ps1` **từ chối** khi `.git` của cây nguồn là một **tệp** (cây
liên kết) thay vì **thư mục** (cây chính); không có `.git` thì cho qua (cài từ bản
chép). `test_362` canh chốt đó, nằm trước mọi thao tác ghi. Quy trình deploy:
`docs/16_CAP_NHAT_VA_DEPLOY.md`.

### 10.7 Tệp dẫn xuất

Sửa `server/static/ltt.css` ⇒ chạy `python tools\dong_goi_gui.py` (bản sao byte
`tools/gui/ltt.css`; `test_284` canh). Tệp sinh ra đụng độ khi gộp: sinh lại trên
cây đã gộp, đừng chọn `--ours/--theirs`.
