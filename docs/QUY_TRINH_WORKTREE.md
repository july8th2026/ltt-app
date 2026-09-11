# Quy trình worktree — vì sao máy treo, và luật để nó không lặp lại

Viết 2026-09-03, sau chín lần máy production khởi động lại đột ngột trong hai ngày.

## Chuyện đã xảy ra

`D:\LTTSTUDIOSAPP` có 5–9 worktree. **Mỗi worktree checkout bản `tools/gate.py`
của nhánh nó** — không chép từ cây gốc, không ai viết mới. Nhưng vì nhiều phiên
cùng sửa một tệp trên các nhánh khác nhau và không ai gộp lại, cùng lúc tồn tại
**ba bản `gate.py` khác nhau**, mỗi bản chỉ biết một nửa bài toán:

| Nhánh | `03845cb`<br>đếm lõi | `4420b56`<br>đo tải | `de0a77d`<br>11→10 | `3b5e257`<br>trần 6 | `-n` thực |
|---|:--:|:--:|:--:|:--:|:--:|
| `phien/asv-v4` | ✅ | — | ✅ | ✅ | 6 |
| `admin-mvp-v3` | ✅ | ✅ | — | — | 14 |
| `claude/lttchat-…` | ✅ | ✅ | — | — | 14 |
| `phien/ltt-llm-…` | ✅ | — | — | — | 14 |
| `claude/ltt-voice-…` | ✅ | — | — | — | 14 |
| `master` | — | — | — | — | 14 |

Trong khi `pytest -n auto` trên máy này tự chọn **10** (xdist đọc lõi **vật lý**).
Bốn phiên chạy song song = tới **56 worker trên 10 lõi**.

🔴 **`master` đi sau `admin-mvp-v3` 505 commit.** Đó là gốc rễ: worktree mới tạo
từ `master` **ra đời đã cũ**, và lỗi tự tái sinh mà không ai làm gì sai.

## Luật

### 1. Worktree mới tạo từ nhánh trunk, không từ `master` cũ

```powershell
git -C D:\LTTSTUDIOSAPP worktree add <đường-dẫn> -b <nhánh-mới> admin-mvp-v3
```

Sau khi `master` được ff tới trunk thì tạo từ `master` cũng đúng — nhưng **kiểm
trước khi tin**:

```powershell
git -C D:\LTTSTUDIOSAPP rev-list --count master..admin-mvp-v3
```

Khác 0 nghĩa là `master` lại tụt lại. Đừng tạo worktree từ nó.

### 1b. Chép tài sản bị gitignore từ cây chính

```powershell
robocopy D:\LTTSTUDIOSAPP\apps\upscalevideo\vendor <cây-mới>\apps\upscalevideo\vendor /E
Copy-Item D:\LTTSTUDIOSAPP\yolov8n.pt <cây-mới>\yolov8n.pt
```

⛔ Không có bước này thì **gate không bao giờ xanh được** trong worktree mới, và
cái đỏ đó không nói lên điều gì về code. `.gitignore` loại `apps/*/vendor/`, nên
48 MB nhị phân + model của `upscalevideo` chỉ nằm ở cây chính, và
`test_82::test_vendor_engine_co_mat` đỏ ở mọi cây liên kết.

⚠️ Một lượt gate đỏ vì thiếu tài sản còn tệ hơn không chạy gate: nó dạy người
đọc bỏ qua màu đỏ.

🔴 **`yolov8n.pt` thêm 09/09, sau khi mục này đã tồn tại và vẫn bỏ sót nó.**
Nó nằm ở **gốc kho**, untracked, không nằm dưới `apps/*/vendor/` — nên đọc câu
`.gitignore` ở trên rồi suy ra "chỉ có `vendor/`" là suy sai. Thiếu nó thì
`test_505::test_moi_duong_khai_deu_CO_THAT_tren_dia` đỏ, và câu nó nói —
*"khai nhưng không có trên đĩa: ['yolov8n.pt']"* — **không nhắc một chữ nào tới
worktree**, nên người đọc đi tìm lỗi trong mã.

⇒ Cách đúng để lấy danh sách này là **hỏi cây chính**, không phải chép lại một
bảng trong tài liệu (bảng chép tay không có cách nào tự biết nó đã cũ):

```powershell
git -C D:\LTTSTUDIOSAPP status --ignored --porcelain |
  Where-Object { $_ -like '!!*' -and $_ -notlike '*__pycache__*' }
```

Đo 09/09 nó trả về đúng hai mục thật: `apps/upscalevideo/vendor/` và
`yolov8n.pt` (cộng `desktop.ini` của Windows, bỏ qua được).

### 1c. Sau khi hoà trunk có XOÁ app: dọn thư mục ma

🔴 `git` theo dõi **tệp**, không theo dõi **thư mục**. Một commit xoá cả một app
sẽ xoá hết tệp của nó, nhưng thư mục vẫn nằm lại trên đĩa nếu trong đó còn thứ
`.gitignore` bỏ qua — và `__pycache__` thì luôn còn. `git status` **sạch**, còn
`apps/<app đã xoá>/` thì vẫn **tồn tại**.

Đo 09/09 sau khi hoà 47 commit trunk vào một nhánh V6:

```
apps/chataistudio/     chỉ còn 6 tệp .pyc   -> test_60, test_85, `app contract lint` ĐỎ
codex_sidecar/         thư mục RỖNG hoàn toàn -> test_1004 ĐỎ
```

⚠️ Ba bước đỏ đó **không nói gì về worktree**: chúng nói "một thư mục trong
`apps/` không có manifest" và "pha 07 khai đã xoá nhưng vẫn còn". Người đọc đi
tìm lỗi trong mã.

```powershell
git clean -ndX apps/          # xem truoc, chua xoa gi
git clean -fdX apps/          # xoa that
Get-ChildItem . -Recurse -Directory | Where-Object {
  (Get-ChildItem $_.FullName -Recurse -File -Force).Count -eq 0 }   # thu muc rong
```

🔴 **`git clean -fdX apps/` XOÁ LUÔN `apps/upscalevideo/vendor/` — tức nó phá
đúng thứ §1b ngay trên kia bắt phải có.** `-X` xoá *mọi* thứ bị gitignore dưới
`apps/`, và 48 MB nhị phân của `upscalevideo` nằm đúng trong tập đó.

Đo 12/09/2026: dọn thư mục ma làm 5 test đỏ thành xanh, rồi lượt cổng kế tiếp
đỏ **3 test khác** — `test_82::test_vendor_engine_co_mat` và hai test
`test_505_nguon_ban_giao`. Không dòng đỏ nào nhắc tới worktree hay tới lệnh
`clean` vừa chạy.

⇒ Chạy `clean` xong thì **chép lại ngay**, đừng đợi cổng nhắc:

```powershell
robocopy D:\LTTSTUDIOSAPP\apps\upscalevideo\vendor <cây>\apps\upscalevideo\vendor /E
```

⚠️ Cái bẫy ở đây không phải tài liệu thiếu: §1b và §1c đều **đúng**, nhưng
không mục nào biết mục kia, nên làm đúng mục sau là phá mục trước.

⛔ **Và đừng hạ mốc `ruff`/`mypy` sau lần dọn này.** Dọn xong thì số phát hiện
**giảm** (đo 09/09: `attr-defined` 204 → 188, `F401` 415 → 414) vì mã của app đã
xoá không còn được quét. Hạ mốc theo con số ấy sẽ làm **đỏ mọi cây chưa dọn** —
mà cây chưa dọn là trạng thái **mặc định**, vì git để thư mục ma lại. Hạ mốc là
việc làm sau, một lần, khi mọi cây đã sạch.

### 2. Mỗi phiên tự kiểm cây mình đang đứng

```powershell
findstr /C:"loi_cho_bo_test" tools\gate.py
```

Không thấy ⇒ **bản cũ**, nó sẽ tự chọn 14 worker. Gộp trunk vào trước khi chạy
gate đầy đủ:

```powershell
git merge admin-mvp-v3
```

### 3. Trước mọi lệnh nặng

```powershell
python tools\cua_so_yen.py trang-thai
```

Có phiên khác đang giữ ⇒ **chờ**. Khoá chỉ cảnh báo, nó không tự chặn được bạn.

Lệnh nặng = `gate.py` (mọi chế độ, kể cả `--quick`), `test_nhanh.py`, từ 3 tệp
test trở lên, `build_system_profile.py`.

### 4. Đừng ghi tệp vào một cây đang chạy gate

`gate._anh_chup_cay()` chụp `apps/ platform_core/ server/ tools/ tests/ alembic/
locale/` lúc bắt đầu và đối chiếu lúc kết thúc. Một tệp đổi giữa chừng làm nó
báo "CÂY ĐÃ ĐỔI" và **tự vứt bỏ phép đo của chính nó** — mất 5 phút không thu
được gì.

### 5. Xong việc thì gộp trunk lại ngay

Nhánh sống lâu mà không gộp là cách sinh ra chính tình huống này. Sau mỗi hạng
mục xong: `git merge admin-mvp-v3` rồi để nhánh của bạn được gộp về.

## Cơ chế ngân sách lõi — một hàm, một đơn vị

`tools/gate.py::loi_cho_bo_test()` là **hàm duy nhất** trả lời "bộ test được bao
nhiêu worker". Bốn vế, tất cả trên **lõi vật lý**:

```
vat_ly - LOI_DE_DANH_VAT_LY - chiem      máy còn bao nhiêu cho ta
chiem = max(KHAI BÁO, ĐO ĐƯỢC)           ai đang giữ chỗ — hai nguồn, một số
TRAN_WORKER_BO_TEST                      trần an toàn cứng (6)
max(1, ...)                              không bao giờ từ chối chạy
```

### `max`, không phải `+`

Hai nguồn **chồng lên nhau**: một phiên vừa khai 6 lõi vừa dùng 6 lõi xuất hiện
ở cả hai. Cộng lại là trừ 12 cho một việc chiếm 6 — cơ chế giảm tải tự làm mình
vô dụng. `max` đếm mỗi kẻ chiếm chỗ đúng một lần.

- chỉ **khai báo**: phiên khác vừa giữ khoá, chưa kịp chạy
- chỉ **đo được**: `pytest` gõ tay ngoài gate, bot, **tiến trình cháu**
- **cả hai**: cùng một phiên → đếm một lần

### ⚠️ Tiến trình cháu không nằm trong `-n`

`-n 6` đếm worker pytest, không đếm thứ mỗi worker sinh ra. Ngày 03/09 đo được
**12 tiến trình `demucs`, mỗi cái 460–984% CPU**, không cái nào xin khoá và
không cái nào nằm trong `-n` — vì `demucs_runner.py` không đặt
`torch.set_num_threads`. Vế **ĐO ĐƯỢC** là thứ duy nhất nhìn thấy chúng.

⇒ Test nạp model thật phải nằm sau rào chắn `LTT_TEST_NANG`
(`tests/rao_chan_nang.py`).

🔴 **Rào chắn đó CHƯA có trên trunk.** Đo 04/09: `tests/rao_chan_nang.py` chỉ
tồn tại ở nhánh `phien/asv-v4`, không có ở `admin-mvp-v3`, `phien/asv` hay
`h42-release-clean`. Nên trên trunk, câu trên mô tả một lớp bảo vệ **chưa tồn
tại** — đừng đọc nó như một bảo đảm. Cho tới khi `phien/asv-v4` gộp về:
kiểm bằng `ls tests/rao_chan_nang.py` trước khi tin, và test nào nạp model
thật thì tự chặn bằng `LTT_TEST_NANG` gõ tay.

## Sau một lần treo

`C:\Users\Thang Tuong\Desktop\HOP DEN\KHAM.bat` — hộp đen ghi liên tục
CPU/RAM/swap/đĩa + GPU/VRAM/nhiệt/điện + 10 tiến trình nặng nhất, tự dày lên
1 giây/mẫu khi máy căng, `fsync` từng dòng.

⚠️ Nó ghi giờ **UTC**; máy ở **UTC+7**. `09:51Z` = **16:51 giờ máy**.
