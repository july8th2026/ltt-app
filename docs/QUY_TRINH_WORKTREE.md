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
```

⛔ Không có bước này thì **gate không bao giờ xanh được** trong worktree mới, và
cái đỏ đó không nói lên điều gì về code. `.gitignore` loại `apps/*/vendor/`, nên
48 MB nhị phân + model của `upscalevideo` chỉ nằm ở cây chính, và
`test_82::test_vendor_engine_co_mat` đỏ ở mọi cây liên kết.

⚠️ Một lượt gate đỏ vì thiếu tài sản còn tệ hơn không chạy gate: nó dạy người
đọc bỏ qua màu đỏ.

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

### 4b. Hỏi cây xem nó đang ở hồ sơ nào — trước khi tin một luật nào

```powershell
python tools\ho_so_cay.py trang-thai
```

Một lệnh, không chạy test. Nó trả lời: nhánh · HEAD · thiếu bao nhiêu commit của
trunk · hồ sơ `NORMAL`/`FAST_BUILD` và trạng thái · **tệp governance nào của cây
này đã lệch trunk**.

⭐ Vế cuối là thứ mục 2 ở trên đang làm bằng tay với `findstr`. `findstr` trả lời
đúng một câu hỏi về đúng một hàm; phép so **blob SHA** trả lời cho cả tập tệp
quyết định luật, và nó không cũ đi khi có ai thêm một hàm mới.

Luật của hai hồ sơ ở `docs/00_LTT_OPERATING_CONTRACT.md` §4.10 — **không** ở đây.

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
