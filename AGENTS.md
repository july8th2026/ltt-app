# Quy tắc làm việc trong dự án này

Áp dụng cho mọi phiên làm việc trên `D:\LTTSTUDIOSAPP`, cho cả người và Claude.

---

## 0. Preflight bắt buộc khi mở hoặc khôi phục phiên

Mỗi phiên mới, và mỗi lần VS Code/máy vừa reset, phải tự kiểm tra trước khi tiếp
tục hạng mục đang dở:

1. Đọc mục mới nhất của `docs/NHAT_KY.md` và hạng mục mở trong
   `docs/KE_HOACH_TRIEN_KHAI.md`; **không khởi động lại từ đầu**.
2. Chạy `git status --short`; không đụng `test-results/`, `tmp/` hoặc thay đổi
   không thuộc hạng mục hiện tại.
3. Kiểm tra công cụ/browser session cần cho hạng mục và các cổng/dịch vụ liên
   quan. Dịch vụ bị tắt do reset thì khởi động lại trong đúng phạm vi đã được
   người dùng giao; không tự mở rộng sang hệ thống khác.
4. Kiểm tra permission profile thực tế. **Không được tuyên bố đã có full quyền
   chỉ vì VS Code chạy Administrator.** Sandbox/approval do host của Codex cấp,
   repo không thể tự sửa hoặc tự bấm hộp thoại `Allow once/always`.
5. Ưu tiên lệnh trong workspace và quyền hiện có. Nếu host bắt escalation, gom
   thành yêu cầu nhỏ, đúng mục tiêu và dùng auto-review/prefix hẹp khi được phép;
   không hỏi lặp cho từng file/lệnh và không tìm cách lách sandbox.
6. Gửi một cập nhật ngắn: checkpoint khôi phục, thứ đang chạy và blocker thật
   (nếu có), rồi tiếp tục tự động. Chỉ dừng hỏi người dùng khi thiếu một lựa chọn
   sản phẩm hoặc quyền ngoài repo mà agent thực sự không thể tự cấp.

**Cấu hình phía người dùng nếu muốn không hiện hộp thoại:** chọn permission
profile không cần approval cho workspace tin cậy hoặc `Allow always` cho prefix
hẹp trong UI Codex. Đây là cấu hình host, không phải file repo và agent không
được giả vờ đã bật nó.

---

## 0b. Vận hành liên tục — không dừng giữa kế hoạch

Khi kế hoạch đang có bước kế tiếp rõ ràng và có thể thực hiện an toàn trong phạm
vi người dùng đã giao, agent phải **tự chuyển sang bước đó** sau mỗi checkpoint,
test hoặc commit; không kết thúc bằng câu “chờ người dùng xác nhận”.

1. Khi một job dài đang chạy hoặc đang chờ GPU, tiếp tục hạng mục CPU/CSDL/mock
   độc lập đã có trong cùng kế hoạch. Khi GPU rảnh, ưu tiên ngay hạng mục GPU kế
   tiếp đã được duyệt; không để tài nguyên rảnh chỉ vì vừa xong một checkpoint.
2. Sau mất điện, reset IDE hoặc compaction, khôi phục từ nhật ký/checkpoint mới
   nhất và đi tiếp; không chạy lại hạng mục đã có bằng chứng hoàn thành.
3. Lỗi ngoài phạm vi hiện tại mà không chặn mục tiêu phải được ghi nhận rồi bỏ
   qua; không tự mở nhánh điều tra làm lệch mục tiêu người dùng giao.
4. “Không dừng” **không** mở rộng quyền, không cho phép bỏ test/gate, không cho
   phép thay đổi phá huỷ và không thay thế tiêu chí hoàn thành. Chỉ dừng khi thật
   sự thiếu lựa chọn sản phẩm, quyền/hành động bên ngoài agent không thể tự cấp,
   có rủi ro an toàn hoặc gặp blocker trực tiếp không còn đường xử lý an toàn.
5. Khi buộc phải dừng, báo đúng checkpoint, bằng chứng đã có, blocker cụ thể và
   bước sẽ tiếp tục ngay sau khi blocker được gỡ; không báo chung chung.

---

## 1. Bắt buộc đọc trước khi thay đổi bất cứ thứ gì

Theo đúng thứ tự, không bỏ bước:

1. `docs/QUYET_DINH_NEN_TANG.md` — **nguồn chân lý**. Tài liệu nào mâu thuẫn
   với nó thì nó đúng.
2. `docs/KE_HOACH_TRIEN_KHAI.md` — hạng mục đang làm và tiêu chí hoàn thành.
3. `docs/NHAT_KY.md` — hai mục gần nhất.
4. Định vị code bằng `grep`/`Glob` trên chính cây nguồn.
   *(`ho_so_he_thong.txt` đã gỡ 2026-09-04: một ảnh chụp toàn cây cũ đi sau
   mỗi lần bất kỳ ai sửa bất kỳ tệp nào.)*
5. Đọc chính các file sắp sửa, **trước khi** sửa.
6. `git status` — biết cây làm việc đang sạch hay bẩn.

`docs/_luutru/` là tài liệu lịch sử. Đọc để hiểu *vì sao*, **không bao giờ làm
theo hướng dẫn trong đó**.

---

## 2. Ranh giới không được vượt

1. **`D:\BOT GEMINI` chỉ đọc.** Đang phục vụ người dùng thật. Không sửa, không
   tạo, không xoá, không chạy script ghi file bên đó. Muốn dùng lại thì **copy
   sang** `D:\LTTSTUDIOSAPP` rồi làm trên bản copy.
2. **Không import chéo** giữa hai cây mã nguồn.
3. **Thêm app = thêm một thư mục trong `apps/`.** Không sửa `platform_core/`
   hay `server/`. Nếu thấy buộc phải sửa → **dừng lại và giải thích vì sao**;
   đó là dấu hiệu hợp đồng app còn thiếu, phải bổ sung vào hợp đồng chứ không
   đi vòng.
4. **Không triển khai lên máy chủ, không đổi DNS** trừ khi được yêu cầu rõ ràng.
5. **App socialbot đã bị gỡ hẳn** (2026-08-25, Q108 thay Q10). Cùng với nó:
   `core/`, `utils/`, `server/services/`, 43 route và 44 tệp test. Đừng dựng
   lại — `tests/test_60_app_registry.py` chốt trạng thái đã gỡ. Muốn đưa về thì
   đó là một quyết định sản phẩm, phải thêm dòng mới vào bảng quyết định trước.
6. Cổng của nền tảng là **8100**. Cổng 8000 thuộc về hệ thống khác trên cùng máy.

---

## 3. Bí mật

- Không bao giờ đưa giá trị bí mật (token, khoá, mật khẩu, nội dung file
  service-account) vào code, tài liệu, git, log, ảnh chụp màn hình hay tóm tắt
  hội thoại. Chỉ được ghi **tên** biến, nơi lưu, trạng thái xoay vòng.
- Bí mật sống ngoài mã nguồn, nạp từ biến môi trường hoặc thư mục được bảo vệ.
- Chạy `python tools/scan_source_secrets.py` trước mỗi lần commit. Phải 0 finding.
- Nếu phát hiện bí mật lọt vào file được theo dõi: che đi, báo người dùng xoay
  vòng khoá, ghi vào nhật ký — **không chép giá trị đó đi đâu cả**.

### 3b. Tài khoản test vận hành

Kiểm GUI trên production dùng **`akakenly.design@gmail.com`** — tài khoản
**thường**, không phải admin. (Chủ dự án chỉ định 2026-09-03; ông ấy nói sẽ đổi
thông tin sau, nên đừng coi nó là vĩnh viễn.)

🔴 **Vì sao không mượn admin nữa.** Mọi lượt kiểm GUI trước đây đều đăng nhập
bằng `admin@lttstudios.com`, và điều đó sai ở hai chỗ khác nhau:

  · Admin **thấy nhiều hơn khách thật** — trang quản trị, cờ nội bộ, đường tắt.
    Một lỗi chỉ xuất hiện với người dùng thường thì không bao giờ lộ ra trong
    một lượt kiểm chạy bằng admin.
  · Hội thoại và credit của lượt kiểm lẫn vào chính tài khoản đang cầm quyền
    cao nhất hệ thống.

⚠️ Bốn tài khoản test cũ (`autosub-test@`, `api-load-canary@`, `vps-thu@`,
`reviewer-test@`) đều là tài khoản **khoá API**. Chúng không có phiên web, nên
**không mở được** một bề mặt web như ChatLTT — đừng mất thời gian thử.

**Mật khẩu không nằm trong kho này** (mục 3 ở trên nói vì sao). Nó đi qua biến
môi trường lúc chạy, theo đúng quy ước sẵn có của
`tests/test_74_smoke_playwright.py`:

```
LTT_SMOKE_USER=...  LTT_SMOKE_PASS=...  node tools/kiem_chatltt_gui.mjs \
    --url https://app.lttstudios.com --anh tmp/kiem_gui_prod
```

⛔ **Claude không gõ mật khẩu vào form đăng nhập**, kể cả khi chủ dự án đưa
trực tiếp trong hội thoại. Chủ dự án khởi động lệnh; Claude đọc
`bao_cao.json` rồi phân tích. Ranh giới này không phải là sự thiếu tin tưởng —
nó là thứ giữ cho một tác nhân tự chủ không bao giờ trở thành đường rò
credential, kể cả khi mọi bước riêng lẻ trông đều hợp lý.

---

## 4. Kỷ luật thay đổi

- Làm **thay đổi nhỏ nhất còn trọn nghĩa** cho hạng mục đang mở.
- Mỗi thay đổi hành vi phải có test đi kèm.
- Viết code mới thì đặt đúng chỗ ngay từ đầu — xem **mục 8 (Bố cục mã nguồn)**.
  Đó là nơi ghi logic nghiệp vụ nằm ở đâu, ngưỡng phình của `routes.py`, và
  những việc dùng chung phải gọi `platform_core` chứ không chép lại.
- Không xoá test đang xanh, trừ khi có quyết định sản phẩm được ghi lại.
- Trước khi báo xong, bắt buộc chạy **một lệnh duy nhất**: `python tools\gate.py`.
  Xem **mục 4b** cho ba lệnh chạy test và lệnh nào dùng khi nào.
- Ghi **đúng lệnh đã chạy và kết quả thật** vào nhật ký. Phân biệt rõ
  `đã chạy` / `chưa chạy` / `pass` / `fail`.
- **Không bao giờ tuyên bố hoàn thành dựa trên kế hoạch hay số test thu thập
  được.** Chỉ dựa trên kết quả chạy thật.
- Thay đổi rủi ro: viết trước cách lùi lại, rồi mới làm.

## 4c. Sửa hạ tầng dùng chung — **ba câu bắt buộc trước dòng mã đầu tiên**

Áp cho mọi thay đổi trong `tools/`, `platform_core/`, `tests/conftest.py` — tức
mọi thứ **nhiều cây cùng chạy**. Ba câu này không phải nghi thức: mỗi câu tương
ứng một bản vá đã hỏng thật trong kho này.

### 1. Nếu chỉ MỘT SỐ cây nhận bản vá, chuyện gì xảy ra?

Mỗi worktree chạy bản `tools/` của **riêng nó**. Một bản vá điều phối chỉ có
hiệu lực khi **mọi** cây đều nhận — và trong khoảng chuyển tiếp nó thường
**phạt người sửa đúng**: cây đã khai thì chờ, cây chưa khai chạy tự do.

```
03/09  tran `-n 6` sua o MOT nhanh   -> bon cay con lai van chay -n 14
06/09  gate khai `postgres_test`     -> cay chua ff van drop_all() vao giua
```

⛔ Nếu câu trả lời là *"tệ hơn trước khi vá"* thì **thiết kế sai**, không phải
"chấp nhận được trong lúc lan". Một bản vá mà chế độ hỏng của nó tệ hơn bệnh nó
chữa thì không phải một bản vá.

### 2. Đường SUY BIẾN của cơ chế này là gì?

Mọi cơ chế điều phối đều có một nhánh "không giữ được gì". Hỏi thẳng: **trên
nhánh ấy, bản vá còn đúng không?**

```
`cua_so_yen.chay_khong_khoa`  -> gate CHEN, giu ZERO tai nguyen
`--lf` cache rong             -> CO Y khong chay gi
thieu `psutil`                -> khong dem duoc, khong phai "may ranh"
```

⭐ Và **cố ý** phải phân biệt được với **tai nạn**: hai trạng thái ấy nhìn từ
ngoài thường giống hệt nhau, nhưng gộp chúng làm một thì hoặc báo động giả liên
tục, hoặc phải nới cổng đến mức nó bỏ lọt chính thứ nó sinh ra để bắt.

### 3. Tôi đang hỏi một NHÃN hay một QUAN HỆ?

```
NHAN    ten tep · chuoi trong cmdline · bien moi truong · ten nhanh
QUAN HE cha-con · cwd · ai dang giu khoa · commit nao la to tien
```

Nhãn thì rẻ và **sai im lặng**. Ba cách đếm tiến trình theo nhãn đều hỏng trong
một đêm — thiếu (`execnet` không mang từ khoá), thừa (`bash -c` mang cả câu
lệnh), và mù với mồ côi (mất gốc thì rơi khỏi cây con).

⛔ Và điều kiện phải là thứ tiến trình đang hỏi **không thể tự thoả**: shell của
chính nó cũng có `cwd` đúng bằng cây ấy. Loại `os.getpid()` **và** `parents()`.

### Sau khi vá: banh cóc phải hỏi HÀNH VI, không hỏi hình dạng

🔴 Ngày 06/09 `tools/test_nhanh.py` thoát sau **0,114 giây**, mã **0**, không
chạy một test nào — và **cả năm** bánh cóc AST vẫn xanh, vì chúng hỏi *"còn khối
`with` không"*, *"còn nhập không"*. Hình dạng mã vẫn đúng khi công cụ đã chết.

⇒ Câu để tự hỏi: **thứ tôi đang khẳng định có tồn tại được nếu chương trình
không chạy không?** Có ⇒ nó không kiểm hành vi, dù nó **đỏ được** khi bị tiêm.

⚠️ *"Đỏ được"* và *"đo đúng thứ cần đo"* là **hai** câu hỏi. Tiêm lại bản cũ
chứng minh phép kiểm **phân biệt được** hai bản; nó không chứng minh phép kiểm
**quan sát thứ ta cần**. Ba lần trong một buổi, cùng một người viết luật này
vẫn tự vi phạm nó — nên nó phải là một **động tác** trong quy trình, không phải
một điều để nhớ.

## 4b. Chạy test — ba lệnh, và **đừng gọi `pytest` trực tiếp**

| Lệnh | Dùng khi | Thời gian |
|---|---|---|
| `python tools\gate.py --vong-lap` | sau **mỗi** lần sửa — **mặc định** | **~15 giây** |
| `python tools\test_nhanh.py` | muốn chạy cả bộ test | ~4 phút |
| `python tools\gate.py` | **trước khi báo xong** | ~5 phút |
| `python tools\gate.py --noi-tiep` | khi nghi kết quả bị **nhiễu** bởi song song hoặc tải máy | ~25–30 phút |

⚠️ **`npm run build` phải là việc CUỐI trước gate, sau cả việc sửa test.**

`build_release._frontend_source_sha256` băm **cả** thư mục frontend — gồm cả
`tests/`. Nên thêm một phép kiểm vitest cũng làm bundle bị coi là **cũ**, và
gate đỏ ở ba chỗ chẳng liên quan gì tới thứ vừa sửa:

```
test_44_release_build · test_95_agent_canvas_build · test_103_autosub_projects
       -> "frontend/<ten> bundle is stale or built with the wrong Node"
```

⭐ Ba lần trong một ngày 03/09. Không phải vì luật khó nhớ, mà vì thứ tự tự
nhiên khi làm việc là *sửa mã → build → viết test* — và bước cuối lại làm hỏng
bước giữa. Chỉ có một cách không quên: **build ngay trước khi gõ `gate.py`**,
không phải "sau khi sửa mã".

⛔ **`--tuan-tu` KHÔNG phải `--noi-tiep`, và nhầm hai cái này rất dễ.**
`--tuan-tu` xếp hàng các **bước**; bước `bo test` bên trong nó vẫn tự mở 10–14
worker pytest. `--noi-tiep` hạ **cả hai** mức: một bước một lúc, **và** một tiến
trình pytest (không xdist, không pha 2), frontend `--maxWorkers=1`.

⭐ Dùng nó khi — và chỉ khi — bạn thấy triệu chứng "đỏ khi chạy cả bộ, xanh khi
chạy một mình". Một lượt `--noi-tiep` XANH trong khi lượt song song ĐỎ là bằng
chứng về một lỗi **cách ly** (hoặc một máy quá tải); nó chưa chỉ ra lỗi ở đâu.
Nơi tìm là `tests/test_631_cach_ly_bo_test.py` — hai luật hay bị phá nhất.

⚠️ Mọi lượt gate nay in `[tai may] N/20 loi dang ban -> RANH/BAN/QUA TAI` trước
khi chạy. `cua_so_yen` chỉ thấy ai **xin khoá**; nó không thấy `pytest` gõ tay,
deploy, hay bốn dịch vụ production. Đo 03/09: khoá báo RẢNH trong khi CPU 65%.

🔑 **Gate là công cụ ra PHÁN QUYẾT, không phải công cụ CHẨN ĐOÁN.**

Ngày 27/08 gate đầy đủ được chạy **sáu lần** chỉ để dò lỗi, ~5 phút mỗi lượt.
Bốn trong sáu lượt đỏ vì một thứ mà một bước con lẻ trả lời trong nửa giây:
baseline của phiên khác · một emoji trong stdout của một công cụ · hồ sơ hệ
thống stale · một phép kiểm đo bất biến qua hình dạng mã nguồn. Đó là 20 phút
trả cho bốn câu trả lời vốn đã có sẵn.

`--vong-lap` giữ **toàn bộ** nhóm kiểm tĩnh — chính là thứ bắt bốn lỗi đó — vì
song song hoá làm chúng chỉ còn 7 giây. Nó chỉ đổi `bộ test` thành `--lf`.

⚠️ Hai điều phải biết trước khi tin nó:

1. **`--lf` một mình chạy TẤT CẢ** khi lượt trước không có gì đỏ (đúng như tài
   liệu pytest). `gate.py` thêm `--lfnf=none`, nên đừng gọi `test_nhanh --lf`
   tay rồi ngạc nhiên vì nó mất 4 phút.
2. **Cache `lastfailed` tích luỹ.** Sau một ngày chạy nhiều lượt lẻ nó phình ra
   (đo 27/08: 123 mục từ 36 tệp, phần lớn đã xanh lại). Lượt `--vong-lap` **đầu
   tiên** sau đó phải rút cạn cache — mất 3 phút 30. Các lượt sau mới là ~15
   giây. Hành vi đúng, nhưng nếu không biết thì trông y hệt một chế độ hỏng.

⛔ `--vong-lap` và `--quick` **không phải bằng chứng**, và dòng `RESULT` của
chúng nói thẳng ra như vậy. Trước khi báo xong vẫn là `python tools\gate.py`.

⛔ **Đừng chạy `python -m pytest` cho toàn bộ kho.** Hai lý do, và lý do thứ hai
mới là lý do thật:

1. Nó **không** chạy 77 test frontend, nên "full regression xanh" sẽ là câu nói
   sai — `gate.py` sinh ra để không ai phải nhớ điều đó.
2. Nó chạy **một luồng và mất 25 phút**, trong khi `test_nhanh.py` cho **cùng
   tập pass/fail** trong 4 phút. Đo 2026-08-26:

   ```
   nối tiếp   4096 passed, 26 skipped   1.534 giây
   song song  4096 passed, 26 skipped     234 giây
   ```

⭐ **Vì sao tốc độ ở đây là vấn đề ĐÚNG ĐẮN, không phải tiện nghi.** Trước
2026-08-26 bộ test mất **2 giờ**, và điều đó đổi cách người ta làm việc: `pytest`
thôi là một vòng lặp và thành một sự kiện. Hệ quả đo được — hạng mục H40 đóng mà
**chưa lượt `pytest` đầy đủ nào chạy xong**, và lượt đầy đủ đầu tiên sau đó tìm
ra **36 lỗi**, trong đó có một phép kiểm **chưa bao giờ xanh** trên máy này.

**Một bộ test quá chậm để chạy là một bộ test không ai chạy.**

Tốc độ đến từ hai chỗ, và chỗ thứ nhất lớn hơn:

- **Bỏ `fsync` cho SQLite tạm** (`platform_core/db.py`). `create_all` 44 bảng:
  **2,16s → 0,05s**. Vì gần như mọi test dựng một CSDL mới, đó là hơn ba giờ.
  ⛔ Có **hai hàng rào** giữ nó khỏi production, và `test_309` chốt cả hai.
- **Chạy song song** (`--dist loadfile`), trừ **ba tệp** ghi vào cây kho —
  chúng chạy nối tiếp ở pha 2. Danh sách ở `tools/test_nhanh.py::TEP_NOI_TIEP`,
  và `test_309` chốt nó.

### Thêm test mới thì nhớ hai điều

1. Test **ghi vào tệp thật trong kho** phải khai vào `TEP_NOI_TIEP`, và phải
   khôi phục **đúng từng byte VÀ đúng dấu thời gian** (`write_bytes` + `os.utime`).
   Thiếu một trong hai thì `gate.py` in *"CÂY ĐÃ ĐỔI TRONG LÚC CHẠY"* và cả lượt
   chạy thành vô giá trị — đã mất **hai lượt gate ≈ 4 giờ** vì đúng chuyện này.
2. Test **không được đọc trạng thái máy** (tải GPU, tốc độ CPU, số tiến trình).
   Tiêm stub cho mọi thứ nó phụ thuộc. Hai phép kiểm đã dính trong một ngày:
   `test_193` (hạn mức nhịp phụ thuộc tốc độ máy) và `test_250` (đọc tải GPU
   thật). **Một phép kiểm đọc trạng thái máy không đo thứ nó nói là đang đo —
   nó đo cái máy.**

---

### Kiểm tra bằng trình duyệt

Test xanh **không** chứng minh trang hiển thị đúng. Sau mỗi thay đổi giao diện
hoặc luồng người dùng: mở trình duyệt, tái hiện luồng, xem console error, xem
request hỏng, xác minh trên giao diện thật. Việc này đã hai lần bắt được lỗi mà
test không thấy.

---

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

   *(Tên module đúng là `platform_core.runtime_paths` từ 2026-08-06; dòng này
   ghi `core.runtime_paths` cho tới 2026-08-25 — tức chỉ vào một module đã
   chuyển nhà từ ba tuần trước, và nay đã bị xoá hẳn.)*

---

## 6. Quy tắc cập nhật memory

Memory ở đây gồm ba tầng, mỗi tầng một nhiệm vụ. **Đừng trộn lẫn.**

| Tầng | File | Chứa gì | Cập nhật khi nào |
|---|---|---|---|
| **Quyết định** | `docs/QUYET_DINH_NEN_TANG.md` | Điều đã chốt và **vì sao**. Ít thay đổi. | Khi có quyết định kiến trúc/sản phẩm mới, hoặc đổi hướng |
| **Kế hoạch** | `docs/KE_HOACH_TRIEN_KHAI.md` | Việc cần làm, tiêu chí hoàn thành, tiến độ | Khi xong một hạng mục, hoặc khi phát hiện việc mới |
| **Nhật ký** | `docs/NHAT_KY.md` | Đã làm gì, lệnh nào chạy, kết quả thật | Cuối mỗi phiên có thay đổi code |

### Sau khi xong MỘT hạng mục — làm đủ bốn việc

Không được bỏ việc nào. Bỏ một việc là lần sau phải đoán.

1. **Đánh dấu `[x]`** hạng mục đó trong `KE_HOACH_TRIEN_KHAI.md`, ghi kèm ngày
   và kết quả test thật.
2. **Ghi một mục vào `NHAT_KY.md`** theo mẫu ở cuối file đó.
3. **Nếu trong lúc làm phát sinh quyết định mới** → thêm dòng vào bảng quyết
   định (xem giao thức bên dưới).
4. **`git commit`** với thông điệp nói rõ *vì sao*, không chỉ *cái gì*.

### Giao thức đổi quyết định — chống chồng chéo quy tắc

Đây là phần dễ sinh nhầm lẫn nhất, nên làm đúng từng bước:

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
   Sót một chỗ là tạo ra hai quy tắc mâu thuẫn — đúng thứ đang phải đi dọn.
5. Nếu quyết định cũ có **test chốt** trong `tests/test_62_khoa_logic.py` thì
   sửa hoặc gỡ test đó **trong cùng một commit**. Một test khoá quy tắc đã chết
   sẽ chặn việc đúng.
6. Ghi vào `NHAT_KY.md`: đổi gì, vì sao, đã dọn những đâu.

**Nguyên tắc gốc:** tại một thời điểm, mỗi câu hỏi chỉ được có **đúng một câu
trả lời đang hiệu lực**. Câu trả lời cũ được phép tồn tại, nhưng phải mang nhãn
"đã chết" rõ ràng để không ai làm theo nhầm.

---

## 7. Khi không chắc

Nói thẳng là không chắc, kèm cách kiểm chứng. Không đoán rồi trình bày như sự
thật. Nếu phát hiện người dùng hiểu sai điều gì, hoặc cách làm đang có vấn đề,
**nói trước khi làm** chứ đừng lặng lẽ làm theo.

---

## 8. Bố cục mã nguồn — nơi từng thứ phải nằm

Chốt 2026-08-06 sau khi rà soát hệ điều hành. **Lý do có mục này:** hợp đồng app
quy định `manifest.py` / `routes.py` / `jobs.py` nhưng chưa từng nói **logic
nghiệp vụ nằm ở đâu**. Không có chỗ mặc định thì route thành chỗ để mọi thứ rơi
vào — kết quả đo được: hai file route vượt 1.300 dòng, một file 1.799 dòng
(lớn nhất repo). Debug một lỗi nhỏ phải cuộn qua sáu miền không liên quan.

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

| Ngưỡng | Giá trị | Vượt thì |
|---|---|---|
| `routes.py` số dòng | 900 | WARN — tách theo miền ra `services/` |
| `routes.py` số handler | 30 | WARN — như trên |
| ≥12 handler mà không có tầng nghiệp vụ | — | WARN — logic đang nằm sai chỗ |

Ngưỡng chọn theo phân bố thật: file route lớn nhất **còn đọc được** trong repo là
~870 dòng / 23 handler. Không phải con số cảm tính.

Tách `routes.py` thành package thì giữ nguyên bề mặt: `routes/__init__.py` chỉ
export `router` và import các module miền để handler kịp đăng ký.

### 8.2b App được dùng **đúng bốn** module của `server` — không hơn

```
server.deps            get_db, user_hien_tai
server.auth.session    require_login
server.auth.csrf       issue_csrf_token, verify_csrf_token
server.templating      templates
```

Đây là **hợp đồng web của app**, và nó được đo trước khi được chốt: phân tích AST
trên 732 tệp cho thấy 12 app chạm đúng bốn module này, **không app nào chạm sâu
hơn**. Nghĩa là biên này đã tồn tại trên thực tế từ lâu — việc duy nhất còn thiếu
là viết nó ra.

⛔ **Import bất cứ thứ gì khác từ `server` là gate ĐỎ.** `tools/lint_app_contract.py`
thi hành, nên nó bị bắt cả ở `gate --quick`.

⭐ **Vì sao khai báo chứ không dời chỗ.** Bốn module này sống ở `server/` (tầng
vận chuyển) trong khi về vai trò chúng là nền tảng. Dời sang `platform_core/web/`
thì tên đúng hơn — nhưng phải sửa **72 chỗ import trong 12 app**, và rủi ro thật
không phải cái tên: nó là *lần sau ai đó với tay sâu hơn*. Luật này chặn đúng
điều đó với giá một vòng lặp. Xem §F của execution rules V2: ưu tiên convention
hiện có trước khi dựng cơ chế mới.

Cần thêm một module vào danh sách? Đó là **một quyết định kiến trúc** — sửa
`SERVER_APP_CO_THE_DUNG` có chủ ý và ghi lý do, đừng làm cho tiện.

### 8.2c App sinh thẻ catalog/nav thì **phải có trang để đáp xuống**

`surface="customer"` + không `catalog_parent` + không `routes.py` ⇒ gate **ĐỎ**.

Sinh ra từ một lỗi thật (2026-08-26): `apps/ltt_llm` khai `nav=()` với ý "chưa có
giao diện" — nhưng `nav_entries()` **tự sinh lại** một dòng trỏ vào `route_prefix`
khi app không khai gì. Kết quả: `/ltt-llm` là link **404 trong header của mọi
khách đã đăng nhập**, nhiều tuần, không phép kiểm nào thấy.

⭐ `apps/anhnoibo` đã tránh đúng bẫy này bằng `catalog_parent`, **và còn viết ra
lý do trong chú thích**. Bài học đã được học và đã được ghi — nó chỉ chưa bao giờ
thành một phép kiểm. Đây là chỗ đóng khoảng cách đó.

Chưa có giao diện thì khai `catalog_parent="<app cha>"`. **Đừng** chữa bằng cách
đổi `surface` — Public API chỉ nhận `"customer"`, đổi là đóng luôn đường bán API.

### 8.3 Việc dùng chung thì ở `platform_core`, không ở app

App gọi vào ruột app khác = gỡ hay đổi tên app đó làm gãy app không liên quan.
Đã dính hai lần, nay có test chặn.

#### Cạnh app→app: mặc định **CẤM**, và cả kho hiện có đúng **một**

Đo bằng AST 2026-08-26: `taovideo → upscalevideo`, hai chỗ import. Đó là cạnh
xuyên-sản-phẩm **duy nhất**.

```python
# tools/lint_app_contract.py
APP_DUOC_DUNG_APP = {
    ("taovideo", "upscalevideo"): {
        ("apps.upscalevideo", "cost"),                        # báo giá nâng cấp
        ("apps.upscalevideo.service", "submit_upscale_job"),  # nộp job nâng cấp
    },
}
```

⭐ **Vì sao khai báo chứ không cắt cạnh.** Đọc kỹ thì đây không phải sai lầm cẩu
thả: hai thứ được gọi đã có tên đúng nghĩa bề mặt công khai. Cắt nó nghĩa là dời
việc điều phối *"nâng cấp một video vừa tạo"* đi đâu đó — và không chỗ nào tốt
hơn chỗ hiện tại: route của `taovideo` là nơi khách bấm nút, và báo giá phải là
báo giá **thật** của `upscalevideo`, không phải một bản sao sẽ trôi.

Cái thiếu không phải cạnh, mà là **lời khai**: bề mặt đó chưa được gọi là công
khai, nên không có gì ngăn lần sau ai đó với tay vào chỗ sâu hơn.

⛔ **Chốt cả TÊN được import, không chỉ tên module.** Chốt mỗi module thì
`from apps.upscalevideo import bất_cứ_gì` vẫn lọt, và hợp đồng chỉ còn là một
lời để ngỏ. Đã chứng minh luật bắn đúng trên 7 ca, gồm cả ca tinh tế: **`taoanh`
dùng cùng bề mặt đó cũng bị chặn** — danh sách theo **từng cặp**, vì mỗi cạnh là
một quyết định riêng chứ không phải một cửa mở chung.

⚠️ Và `test_308` chốt **hai chiều**: thêm cạnh mới mà quên khai thì đỏ, *và* khai
một cạnh mà thực tế không còn ai dùng cũng đỏ — một quyền được cấp rồi bỏ đó là
một cánh cửa không ai canh.

| Việc | Dùng | Đừng tự viết lại |
|---|---|---|
| Kiểm ảnh người dùng tải lên | `platform_core.image_input.validate_reference` | |
| Đường dẫn bundle React đã build | `platform_core.frontend_bundle.bundle_assets` | |

**Không neo đường dẫn bằng `Path(__file__).parents[n]`.** Đếm cấp thư mục sai
ngay khi file đổi chỗ, và hỏng **lặng lẽ**: tách `routes.py` thành package làm
file sâu thêm một cấp, `parents[2]` trỏ nhầm, manifest không đọc được, trang
**vẫn trả 200** với vỏ trống. Neo bằng tên thư mục (`platform_core/frontend_bundle.py`
làm mẫu). `test_148` chặn cả lớp lỗi này.

### 8.4 `platform_core` không được biết tên app nào

Kể cả trong chú thích và docstring. Đã vi phạm hai lần, cả hai đều do
`test_no_app_slug_is_hardcoded_in_the_platform` bắt.

### 8.5 Trước khi báo xong

```powershell
python tools\gate.py
```

Gate gồm: quét bí mật → lint hợp đồng app → **quét tên chưa định nghĩa** → test
3 frontend → pytest. Bước "tên chưa định nghĩa" thêm 2026-08-06 sau khi phát
hiện `POST /upscalevideo/queue` — đường nộp việc **chính** của app đó — gọi
`get_session()` mà không import: mọi lần nộp đều 500, lỗi nằm trong repo từ
2026-08-02, và không test nào chạm route đó. Test không phủ hết mọi nhánh
route; một cái tên chưa định nghĩa thì đọc tĩnh là thấy.

---

## 9. Trình duyệt và lệnh cần tương tác

Chốt 2026-08-06 sau khi mất mấy lượt dò.

### 9.1 Mở trình duyệt

Hồ sơ Chrome của dự án — **giữ đăng nhập giữa các phiên**:

```bash
playwright-cli -s=ltt open --browser=chrome --headed \
  --profile="C:\LTTBrowserProfiles\PlenXResearch" <url>
```

Ba điều bắt buộc:

- **`--headed`** — không có nó thì cửa sổ chạy **ẩn**, chủ sản phẩm không nhìn
  thấy Claude đang làm gì. Mặc định là ẩn.
- **`--profile=...`** — trỏ đúng hồ sơ đó. `--persistent` không kèm đường dẫn sẽ
  tạo hồ sơ TRẮNG, phải đăng nhập lại mọi trang.
- **`-s=ltt`** — phiên đặt tên, để không đụng phiên khác.

Hồ sơ này đang đăng nhập sẵn: Google (`vicentetuber@gmail.com`), GitHub
(`giaitritruyenthongltt-spec`).

`attach --cdp=chrome` chỉ dùng khi chủ sản phẩm đã tự bật "Allow remote
debugging" — không phải đường mặc định.

### 9.2 Lệnh cần nhập mật khẩu / xác thực

Shell của Claude **không tương tác được**. Mọi lệnh cần nhập (git push lần đầu,
đăng nhập cloud) sẽ chết với:

```
fatal: Cannot prompt because user interactivity has been disabled.
bash: line 1: /dev/tty: No such device or address
```

Mở cửa sổ mới **thôi chưa đủ** — nó kế thừa môi trường đã tắt tương tác. Phải
kèm **`-UseNewEnvironment`**:

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
  '-File','"<script>.ps1"' -UseNewEnvironment
```

Và cho script **ghi log ra file** (`Tee-Object`) để Claude đọc được lỗi thật thay
vì đoán. Không có bước này thì mọi chẩn đoán chỉ là phỏng đoán.

Ghi chú: PowerShell coi stderr của `git` là `NativeCommandError` — **không phải
lỗi**. Chỉ tin `EXITCODE`.

### 9.3 Chạy lệnh vừa cần quyền Administrator vừa cần đọc log

`Start-Process` **không cho dùng `-Verb RunAs` cùng với `-RedirectStandardOutput`**.
Hai tham số loại trừ nhau, và nó **hỏng im lặng**: không log, không thông báo
lỗi, tiến trình thoát sau một giây như thể đã chạy xong.

Đúng cách là tách hai lớp:

```powershell
# Lớp NGOÀI — nâng quyền, KHÔNG chuyển hướng
Start-Process powershell -ArgumentList '-File','"<wrapper>.ps1"' -Verb RunAs

# Lớp TRONG (trong wrapper, đã có quyền) — chuyển hướng, KHÔNG -Verb
$p = Start-Process powershell -ArgumentList '-File','"<script>.ps1"' `
       -RedirectStandardOutput $out -RedirectStandardError $err -Wait -PassThru
"EXITCODE=$($p.ExitCode)" | Add-Content $sum
```

Wrapper phải ghi `EXITCODE` ra file. `EXITCODE` **rỗng** nghĩa là tiến trình
không chạy — khác hẳn `EXITCODE=0`. Không phân biệt được hai thứ đó thì sẽ báo
"đã deploy xong" trong khi chưa có gì xảy ra.

---

## 10. Hai phiên Claude cùng một cây làm việc

Chốt 2026-08-27, sau một buổi hai phiên chạy song song (`/developers` và khu VPS)
với **0 lần đè nhau**.

> ⭐ **CẬP NHẬT 2026-09-02 — quy trình đầy đủ nay ở `docs/DEVELOPMENT_WORKFLOW.md`.**
>
> Mục 10 này vẫn đúng và vẫn là luật. Cái đổi là **không còn phải làm bằng tay**:
>
> | Việc | Trước | Nay |
> |---|---|---|
> | tách cây | tự `git worktree add` | `python tools/cay_rieng.py tao <ten>` |
> | chạy ít mà vẫn có nghĩa | không có | `gate.py --doi` (suy phạm vi từ cây) |
> | tránh giành tài nguyên | một khoá cho mọi thứ | khoá theo **tên tài nguyên** |
> | biết ai đang giữ gì | nhắn hỏi nhau | `python tools/cua_so_yen.py trang-thai` |
> | "gate nào chạy trên mã nào" | cuộn lên đọc lại | `test-results/gates/<id>.json` |
>
> 🔴 Ba sự cố thật ngày 02/09 trong **đúng một giờ** là lý do: một phiên đổi
> nhánh của phiên kia, một lượt `--vong-lap` treo quá 5 phút vì tranh CPU, và
> toàn bộ việc chia tệp phải thương lượng bằng tin nhắn.

### 10.1 Vì sao mục này tồn tại

`D:\LTTSTUDIOSAPP` thường có **nhiều phiên Claude chạy cùng lúc trên cùng một
cây** — không phải nhánh riêng, không phải worktree riêng, **cùng đĩa**. Ngày
27/08 `ListAgents` liệt năm phiên interactive.

Hai phiên cùng `Write` một tệp thì bản sau đè bản trước, **im lặng**. Và một
`git commit` whole-file nuốt luôn phần đang dở của phiên kia.

⭐ Cách tránh không phải là khoá file. Là **nói chuyện trước**, một lần, mất hai
phút.

### 10.2 Lập giao ước NGAY khi phát hiện có phiên khác

Không đợi va chạm. `ListAgents` → `SendMessage` tới phiên kia, chốt bốn điều:

**① Ranh giới tệp.** Mỗi bên liệt kê "tệp của tôi" và "tệp của bạn", cam kết
không chạm khu kia. Cụ thể theo khu, không nói chung chung.

**② Tệp DÙNG CHUNG: chỉ `Edit` khớp chuỗi chính xác, KHÔNG `Write`/`cat >`.**

| Tệp | Cách chia |
|---|---|
| `server/static/ltt.css` | mỗi khu một **khối có nhãn** ở cuối tệp (`LỚP NGỮ NGHĨA CỦA KHU VPS`, `.khu-dev`). Hai vùng tách rời ⇒ không xung đột, miễn không ai ghi đè cả tệp |
| `locale/en/LC_MESSAGES/messages.po` | **chỉ nối thêm cuối**, và **đọc lại tệp ngay trước mỗi lần ghi**. Giữ LF, không BOM. ⛔ Không chạy `i18n.py trich` — nó xếp lại cả tệp. Kiểm 0 msgid trùng sau cùng |
| `server/templates/_kieu_chung.html`, `base.html` | **nhắn trước khi sửa** — luật ở đó chạm mọi trang của mọi app, nên chúng không thuộc khu của ai |

**③ Tệp DẪN XUẤT: người commit SAU CÙNG mới sinh.**

`tools/gui/ltt.css` (`tools/dong_goi_gui.py`) chụp **cả cây**. Sinh giữa chừng là commit một
nửa công việc đang dở của phiên kia, **dưới tên đợt của mình**.

Quy tắc: mỗi bên commit **mã nguồn** của mình, không kèm hai tệp đó. Khi mọi
nguồn đã commit thì một bên sinh lại và commit chúng trong **một commit riêng**.
Commit trung gian đỏ `test_284`/`test_177` là chấp nhận được; commit dẫn xuất
cuối vá lại.

**④ Commit chọn lọc.** `git add` từng path của mình, rồi kiểm `git diff --cached`
không dính tệp phiên kia.

### 10.3 Ba cái bẫy của cây dùng chung

🔴 **`git stash` là hành động rủi ro.** Nó cuốn cả phần dở của phiên kia rồi trả
lại, và một lần ghi xen giữa `stash` và `pop` là một xung đột. Muốn đo baseline
sạch thì:

```bash
git worktree add --detach <tmp> HEAD   # đo ở đây
git worktree remove --force <tmp>
```

🔴 **Gate đỏ chưa chắc là lỗi của mình.** Kiểm `git status` và
`git log -1 -- <tệp>` **trước khi đi sửa**. Đã dính: bốn phép kiểm đỏ hoá ra do
`CONTRACT_BASELINE.json` và `developers_base.html` của phiên kia.

🔴 **`CÂY ĐÃ ĐỔI TRONG LÚC CHẠY`** — `tools/gate.py` tự in dòng này khi có ai ghi
vào cây giữa lượt chạy. Khi thấy nó, kết quả nói về cây lúc **bắt đầu**. Đừng
trích nó làm bằng chứng; chạy lại trên một cây đứng yên.

### 10.4 Báo cho nhau thứ mình bắt được ở khu của họ

⭐ **Đây là phần đổi lại được nhiều nhất, và nó không tự xảy ra.** Ba lỗi bắt
được trong một buổi 27/08, không cái nào một phiên tự tìm ra được, và cả ba đều
**chỉ hiện khi render hoặc chạy thật** — không thấy khi đọc HTML hay đọc diff:

1. `_kieu_chung.html` là khối `<style>` nội tuyến trong `<head>` **đứng sau**
   thẻ `<link>` tới `ltt.css`, và nó khai `button, .btn { background:
   var(--accent) }`. Cùng độ đặc hiệu nhưng đến sau ⇒ nó thắng **mọi** luật
   `.btn-*` một-class viết trong `ltt.css`, và nút vận hành ra **màu đỏ** —
   tức màu của hành động không hoàn tác được. Chỉ thấy bằng `getComputedStyle`.
   ⇒ Viết `.btn.<lop>` (0,2,0).
2. Rác test lọt vào tệp thật khi một lượt chạy bị ngắt giữa `write`↔`finally`
   (`image.ghost` trong `CONTRACT_BASELINE.json`).
3. Chỗ-giữ khoá API phải đúng ký tự `…` (U+2026), không phải `...` ASCII —
   `test_272` bóc `ltt_sk_…` để chứng minh trang không lộ khoá thật.

### 10.5 `memory/` cũng là thư mục dùng chung

`.claude/projects/D--LTTSTUDIOSAPP/memory/` dùng chung cho **mọi phiên của dự
án**. Trước khi ghi một memory mới, **đọc `MEMORY.md`** — hai bản gần trùng thì
lần sửa sau chỉ sửa một bản, đúng cái bệnh mục này sinh ra để tránh.

Đã suýt dính ngày 27/08: hai phiên cùng định ghi khuôn phối hợp này. Cách xử lý
đúng là **gộp vào bản có sẵn rồi xoá bản trùng**, kèm dòng chỉ mục của nó.

### 10.6 Cửa sổ yên: máy tự giữ hàng đợi, thay vì ba người nhắn nhau

Chốt 2026-08-31, sau một buổi **ba** phiên cùng cây.

Giao ước ở 10.2 chống được việc **đè tệp** của nhau — và nó đã làm đúng việc,
0 lần đè. Nhưng nó không chống được thứ thứ hai, và thứ này mới đắt: **hai lượt
`gate.py` chạy gần nhau đều cho ĐỎ GIẢ.** Mỗi lượt mất 5–6 phút, và mỗi lượt
thấy tệp của phiên kia đổi giữa chừng nên kết quả nói về một cây không còn tồn
tại. Hôm đó cả hai phiên đều mất một lượt, và cả hai dòng `RESULT` **trông y hệt
một lượt sạch**.

⛔ **Đừng “song song hoá” cổng chất lượng để chữa cái này.** Pha `bo test` đã lấy
trọn phần lõi mà máy cho phép — số worker do **`tools/gate.py:loi_cho_bo_test()`**
quyết, và đó là hàm DUY NHẤT trả lời câu hỏi đó. Hai
lượt cùng lúc chỉ chia đôi cùng một chiếc bánh: tổng thời gian gần y hệt chạy
lần lượt, nhưng trả thêm gấp đôi bộ nhớ, gấp đôi thư mục tạm, và gấp đôi khả
năng đo sai. Song song hoá một thứ **đã bão hoà lõi** không phải tối ưu.

⚠️ **Dòng trên trước 03/09 ghi `-n auto` = “mọi lõi (20 lõi)”. Sai, và sai về
phía nguy hiểm.** `os.cpu_count()` trả **20** vì đó là lõi *logic*; máy này có
**10 lõi vật lý**, và xdist đọc lõi vật lý. Từ 03/09 cổng không còn dùng
`-n auto` nữa. Con số thật ở `tools/gate.py`; luật đầy đủ ở
`docs/QUY_TRINH_WORKTREE.md` và `docs/QUY_TAC_CHAY_LENH_NANG.md`.
⛔ Đừng gõ lại con số đó vào đây — đó chính là cơ chế vừa hỏng.

**Ba thứ đã dựng:**

```powershell
python tools/cua_so_yen.py trang-thai   # ai dang giu, tu bao gio
python tools/cay_rieng.py liet-ke       # cac cay lam viec dang co
python tools/gate.py --khong-khoa       # chay ngay, khong xep hang
```

**① `gate.py` đầy đủ xếp hàng** sau một khoá cấp máy. Đợi quá 15 phút thì nó
**vẫn chạy**, kèm băng báo rằng lượt này có thể bị nhiễu — một cổng chất lượng
từ chối chạy vì bận là một cổng không ai dùng.

⚠️ Trong hầu hết harness, **màn hình im lặng suốt lúc xếp hàng** vì đầu ra chỉ
hiện khi lệnh kết thúc. Biết trước điều đó, đừng tưởng treo.

⛔ `--quick` và `--vong-lap` **không** xếp hàng, và đó là chủ ý: cả hai đã tự
khai chúng không phải bằng chứng, nên nhiễu trên phép đo của chúng ít quan trọng
hơn hẳn — còn chặn một vòng lặp ngắn sau một lượt đầy đủ 6 phút là giết đúng cái
làm nó hữu dụng.

**② Dòng `RESULT` tự khai khi cây đổi:**

```
RESULT: FAIL (4/25)  [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]
```

Cùng luật đã áp cho `--quick` và `--vong-lap`: **một lượt chạy ít tin cậy hơn thì
dòng kết quả của nó phải trông khác.** Trước bản vá, cây-đổi chỉ được nói trong
một đoạn văn phía trên, còn dòng `RESULT` in y hệt — và dòng `RESULT` là thứ duy
nhất được đọc khi người ta vội.

**③ Cây riêng (`git worktree`) — tuỳ chọn, không mặc định.** Nó cho một cây
không ai khác ghi vào, nhưng đòi nhánh riêng (`phien/<tên>`) và phải **gộp lại**.
Mô hình lane-theo-tệp ở 10.2 đang chạy tốt, nên chỉ lấy cây riêng khi bạn thật sự
cần một cửa sổ yên dài.

🔴 **VÀ CƠ CHẾ NÀY TỰ SINH RA MỘT MỐI NGUY LỚN HƠN THỨ NÓ CHỮA.** Máy này **là**
production, và `setup\2-cai-dat.ps1` chép **cả cây** sang `C:\LTTPlatform`.
Nhiều cây riêng nghĩa là nhiều thư mục **trông giống hệt nhau**, và deploy nhầm
một trong số đó là lỗi **im lặng**: script chạy xong, báo thành công, và
production chạy một nhánh không ai định phát hành.

⇒ `2-cai-dat.ps1` có chốt chặn: nó **từ chối** khi `.git` của cây nguồn là một
**tệp** (cây liên kết) thay vì **thư mục** (cây chính). Không có `.git` thì cho
qua — đó là đường cài hợp lệ từ một bản chép. `test_362` canh chốt đó còn nguyên
**và nằm trước mọi thao tác ghi**.

### 10.7 Tệp dẫn xuất: người chạy lượt cuối sinh lại

`tools/gui/ltt.css` chụp **cả cây**, nên nó đổi theo thay đổi của **bất kỳ ai**.
Sinh lại giữa chừng chỉ tạo một phiên bản sẽ cũ trong vài phút — đã đo đúng vậy
ngày 31/08 với `ho_so_he_thong.txt`: sinh lại xong, phiên khác thêm một tệp, nó
cũ lại ngay. *(Hồ sơ đã gỡ 04/09; luật này còn nguyên cho `ltt.css`.)*

⇒ Để **người chạy lượt gate làm bằng chứng cuối cùng** sinh lại, một lần, trên
một cây đứng yên.

🔴 **Và khi nó ĐỤNG ĐỘ lúc gộp: sinh lại trên cây ĐÃ GỘP — không bao giờ
`--ours`/`--theirs`.**

Lý do không hiển nhiên, nên viết ra: đây là một đụng độ **13 MB** trong một tệp
**sinh ra**. Người gặp nó thấy hàng nghìn dòng `<<<<<<<` và phản xạ tự nhiên là
chọn một bên cho xong — phản xạ ấy **đúng** với hầu hết tệp dẫn xuất, và **sai**
với tệp này: chọn một bên cho ra một hồ sơ tả **một cây không tồn tại**, không
phải cây của ai cả, mà là cây của một bên *trước khi* gộp.

`test_177` bắt được, nhưng chỉ khi có người chạy gate **sau** merge. Ai vừa chạy
gate xong ở nhánh mình thì có lý do để không chạy lại — và đó đúng là lúc nó lọt.

