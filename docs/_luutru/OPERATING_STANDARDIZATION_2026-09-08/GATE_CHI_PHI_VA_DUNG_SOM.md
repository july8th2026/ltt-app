# Chi phí thật của gate, và vì sao có `--dung-som`

> Lập **2026-09-13**. Mọi con số dưới đây **đo được** từ bản ghi máy sinh
> `test-results/gates/20260912T170014Z-5504.json` (hồ sơ `day-du`, 33 bước,
> `cay_da_doi_giua_chung=False`), không phải ước lượng.
>
> Tệp này **không** định nghĩa lại quy trình. Nguồn chân lý vẫn là
> `docs/00_LTT_OPERATING_CONTRACT.md` §4. Đây là **phép đo** để §4 được áp dụng
> đúng, cộng hai khuyết tật công cụ đã sửa.

## 1. "33 bước" không phải chỗ đắt — ba bước mới là

| bước | giây | % |
|---|---|---|
| `bo test (song song)` | 735,5 | **60,3%** |
| `bat bien da tien trinh` | 302,4 | **24,8%** |
| `mypy` | 124,0 | **10,2%** |
| **30 bước còn lại, cộng lại** | **58,1** | **4,7%** |

### ⚠️ ĐÍNH CHÍNH cùng ngày: `mypy` 124,0 s là lượt **cache LẠNH**

Lượt gate tiếp theo trên cùng cây đo `mypy` = **3,1 s** — nhanh hơn **40 lần**.
Khác biệt là `.mypy_cache`.

| | lạnh | ấm |
|---|---:|---:|
| `mypy` | 124,0 s | **3,1 s** |
| `--quick` (suy ra) | ~182 s | **~61 s** |

⇒ Bảng trên đúng cho **lượt đầu sau khi cache bị xoá** (`git clean`, đổi nhánh
lớn, máy mới). Ở nhịp làm việc bình thường, `mypy` **không** nằm trong ba bước
đắt — chỉ còn **hai**: `bo test` và `bat bien` = **85,1 %**.

🔑 Bài học lặp lại đúng thứ tệp này đang nói: **một con số đo một lần chưa phải
một phép đo.** Tôi vừa suýt ghim `124 s` thành hằng số vận hành sau khi thấy nó
đúng một lần — cùng cơ chế đã làm `"~40 giây"` trôi.

⇒ `--dung-som` **không** mất giá trị: khoản tiết kiệm thật của nó là ở hai bước
  `bo test` (735 s) + `bat bien` (302 s), không phải ở `mypy`.

⇒ Cắt bớt bước tĩnh không tiết kiệm gì đáng kể. Mọi khoản tiết kiệm thật đều
nằm ở chỗ **không trả tiền cho ba bước kia khi đã biết phán quyết**.

## 2. 🔴 L1 (`--doi`) có thể ĐẮT HƠN L3

Hợp đồng §4 ghi L3 trung vị **682,8 s**. Lượt `--doi` đo được ở trên:
**734 s đồng hồ / 1220 s CPU, và vẫn là 33 bước**.

Không phải lỗi: `--doi` **tự hạ cấp xuống đầy đủ khi không chắc** — đúng như §4
khai. Thay đổi hôm ấy chạm `platform_core/api_pool.py`, một thành phần lõi có
8+ nơi gọi, nên phạm vi suy ra là *toàn bộ*.

⚠️ ⇒ **Với `platform_core/`, đừng kỳ vọng `--doi` rẻ.** Bậc thang rẻ ở đó là
   `--quick`, không phải `--doi`.

## 3. Gate biết mình FAIL ở giây 159 rồi chạy thêm 575 giây

Thứ tự chạy **đã đúng** (rẻ trước, đắt sau):

```
buoc 12   mypy                  124,0s  FAIL   <- phán quyết đã định TẠI ĐÂY
buoc 26   bat bien da tien...   302,4s  PASS
buoc 33   bo test (song song)   735,5s  FAIL   <- đỏ vì CHÍNH mypy (test_306)
```

Hai bước đỏ, **một** gốc: `test_306::test_mypy_hien_tai_dat_moc` chấm lại đúng
thứ bước `mypy` đã chấm — nhưng đắt gấp 6 và đi sau.

### `--dung-som` — cờ opt-in, không phải mặc định

```
python tools\gate.py --doi --dung-som
```

Chạy nhóm **rẻ** (`cong`, `tinh`, `frontend`) trước; một bước rẻ đỏ ⇒ **dừng**,
không chạy `bo test`/`bat bien`.

⛔ **Vì sao không đổi mặc định.** `_chay_theo_lich` đã viết ra nguyên tắc ngược
lại, có chủ ý: *"KHONG bo qua phan con lai: nguyen tac 'chay het roi moi bao'
van giu"*. Nguyên tắc ấy **đúng cho một lượt phán quyết** — chạy hết mới thấy
**mọi** lỗi trong một lần, thay vì sửa một cái rồi phát hiện cái kế tiếp.

| chế độ | kỳ vọng | muốn biết |
|---|---|---|
| `--dung-som` | **có** lỗi | **sớm** |
| mặc định | xanh | **đủ** |

⚠️ Cái giá khi lượt xanh: nhóm rẻ không còn nấp được trong bóng của `bo test`,
nên một lượt xanh chậm thêm ~180 s. Đó là lý do nó **chỉ** dùng trong vòng lặp.

### Và nó phải TỰ KHAI

Bước chưa chạy giữ `ok is None` — trạng thái **thứ ba**, không gộp vào PASS
cũng không gộp vào FAIL. Dòng `RESULT` thêm
`[DUNG SOM: N BUOC CHUA CHAY, KHONG PHAI BANG CHUNG: …]`, bản ghi JSON ghi
`ket = "CHUA"`.

🔑 Cùng luật đã áp cho `--quick`, `--vong-lap` và cây-đổi: *một lượt chạy ít hơn
thì dòng kết quả của nó phải **trông khác***. Ngày 31/08 hai phiên đọc cùng một
dòng `PASS 25/25` theo hai cách trái ngược, vì một bước đã tự bỏ qua mà dòng
`RESULT` không hề nói.

Ghim: `tests/test_1235_gate_dung_som.py` (7 ca, có đối chứng ngược rằng **mặc
định vẫn chạy hết**).

## 4. 🔴 Gate KHÔNG BAO GIỜ xanh được trong một worktree — đã sửa

Ba phép kiểm đỏ **vĩnh viễn** ở mọi worktree, và chúng **không** phải lỗi của
người đang sửa mã:

```
test_82_upscalevideo::test_vendor_engine_co_mat
test_505_nguon_ban_giao::test_moi_duong_khai_deu_CO_THAT_tren_dia
test_505_nguon_ban_giao::test_DANH_SACH_VAN_CHUYEN_khop_dung_tap_DO_DUOC
```

Nguyên nhân: `apps\*\vendor` và `yolov8n.pt` **gitignored có chủ ý** nhưng
production đọc lúc chạy. Tệp gitignored **không đi theo `git worktree add`** —
chúng không nằm trong lịch sử. Đo 12/09: cây chính `D:\LTTSTUDIOSAPP` có đủ cả
hai; worktree `ltt-llm-dual-model-4dfcf4` không có cái nào.

⇒ Mâu thuẫn ngay trong quy trình: §7 đòi *"trước khi báo xong: gate đầy đủ"*,
  §5 đòi *"mỗi chiến dịch một cây riêng"* — và hai điều đó **loại trừ nhau**.
  Một cổng không thể qua được là một cổng sẽ bị bỏ qua.

### Sửa: hỏi ĐÚNG CÂY, không bỏ phép kiểm

`tests/cay_nguon_deploy.py` trả về cây mà **deploy chép từ** — luôn là cây
chính, kể cả khi lượt chạy xuất phát từ worktree (`git rev-parse
--git-common-dir`).

⛔ Không skip. `tests/pg_scratch.py` đã viết đúng câu cần viết: *"Skipping is how
   a mistake becomes silence"* — và gần như mọi việc đều làm trong worktree, nên
   một phép kiểm skip ở worktree là một phép kiểm **không bao giờ chạy**.

⭐ Câu hỏi thật của ba phép kiểm ấy không phải *"cây này có vendor không"* mà là
   *"cái cây deploy sẽ chép từ đó có vendor không"* — và deploy **chỉ chạy từ
   cây chính** (`docs/16_CAP_NHAT_VA_DEPLOY.md`). Nên phép kiểm nay **mạnh hơn**
   bản cũ: xoá `vendor/` ở cây chính vẫn đỏ, **kể cả khi đang chạy từ worktree**.

### Vì sao nó nghiêm trọng hơn vẻ ngoài

`setup/2-cai-dat.ps1` chép `$VAN_CHUYEN` từ **cây sống** (`Join-Path $src $mau`)
— khác với mã `.py` đi qua `git archive` — và dùng `-ErrorAction SilentlyContinue`:
thiếu tệp thì nó **im lặng bỏ qua**. Một lượt deploy từ cây thiếu vendor sẽ
**âm thầm gỡ vendor khỏi production**. Ba phép kiểm ấy tồn tại để chặn đúng
chuyện đó, và chúng đúng — chỉ là chúng đang hỏi nhầm cây.

## 5. Một con số chép tay đã trôi — đã sửa

Đầu `tools/gate.py` ghi *"`--quick` … ~40 giây"*. Đo thật: **182 s**, riêng
`mypy` đã 124 s. Con số cũ có từ trước khi `mypy` vào gate.

⛔ Đúng cơ chế `CLAUDE.md` cảnh báo năm lần: *một giá trị chép tay không có cách
   nào tự biết nó đã cũ.*

## 6. Còn mở — ghi lại, chưa sửa

**`mypy` chạy 8 lần mỗi lượt gate.** Một lần ở bước `mypy`; bảy lần nữa bên
trong `test_306` (`_mypy_moc_that` gọi `check_mypy.py --accept`, và bốn ca khác
gọi `check_mypy.py`). Chưa đo phần này chiếm bao nhiêu trong 735 s của
`bo test` — cần một lượt `--durations` trên riêng `test_306` mới nói được, và
chưa chạy.

⚠️ **Đừng sửa theo suy luận.** Vài ca trong đó giới hạn `mypy_thu_muc="apps"`
   nên rẻ hơn hẳn một lượt quét cả cây; con số 7 × 124 s là một phép nhân
   **chưa được đo**, không phải một phát hiện.
