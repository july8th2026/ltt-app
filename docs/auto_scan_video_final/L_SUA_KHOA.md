# Làn `sua-khoa` — M-09: mọi vòng sửa chết vì `database is locked`

Nhánh `phien/asv-final-sua-khoa`, từ `eee50f75`. Tệp này là **bảng đo + quyết
định**, không phải quy trình. Luật vận hành ở `docs/00_LTT_OPERATING_CONTRACT.md`.

> `LOI_TONG.md` M-09 (cao, **CHẶN PHÁT HÀNH**): *"Mọi vòng sửa chạy lại
> `voice_synthesis` đều giết lần chạy: `sqlite3.OperationalError: database is
> locked`."* Tức năng lực **"sửa đúng chỗ"** (§8 đề bài) — một dòng trong bảng
> điểm phát hành — **chưa từng chạy trọn một lần nào**.

---

## 1. Tái hiện — một phép kiểm ĐỎ trước, không phải một lời kể

`tests/test_2160_asv_vong_sua_khoa_csdl.py` (dải 2160–2169 của làn này) chạy
**hết chuỗi** bằng hàng đợi thật, worker thật, định tuyến thật; chỉ **máy đo**
(`asv_gpu.do_luong.bo_do.chay_tat_ca` — cần qc-venv + model ASR) và **máy sinh
tiếng** là giả, đúng khuôn `test_402`.

Ba đường sửa của `sua_chua.GIAI_DOAN_SUA` được đi **riêng từng đường**, vì
chúng đặt lại **ba giai đoạn khác nhau** và do đó chạm vào ba trạng thái khác
nhau của `AsvAsset`:

| bài | khiếm khuyết | nguồn | đặt lại | trước bản vá |
|---|---|---|---|---|
| `..._chay_lai_voice_synthesis_KHONG_chet_...` | `doc_sai` | WER 0,95 / CER 0,90 (vượt ngưỡng `vi`) | `voice_synthesis` | **XANH** — không lộ |
| `..._DICH_SAI_dat_lai_content_process_...` | `dich_sai` | `qc_ngu_nghia` chấm `dat=false` | `content_process` | **ĐỎ — `database is locked`** |
| `..._CAT_SAI_dat_lai_edit_plan_...` | `cat_sai` | `qc_hinh` chấm `dat=false` | `edit_plan` | **ĐỎ** (làn `qc-hinh` đã gặp qua `test_2121`) |

⭐ **Đường `doc_sai` XANH cả trước bản vá, và đó là số liệu quan trọng nhất của
mục này.** Nó giải thích vì sao M-09 không lộ ra sớm hơn: đường ấy chỉ
`su_dung.mo_lai_don_vi` cho **một đơn vị**, không gọi
`assets.vo_hieu_theo_day_chuyen`. Hai đường kia đặt lại một giai đoạn **thượng
nguồn**, nên artifact của `voice_synthesis` bị đánh dấu `missing` — và **chỉ
khi ấy** phép kiểm toàn vẹn mới có gì để **GHI** lại. Xem §2.

**Đối chứng** (⛔ không có thì một bài xanh không nói gì):

* `test_DOI_CHUNG_khong_khiem_khuyet_thi_khong_vong_sua_va_run_DONE` — không
  khiếm khuyết ⇒ không vòng sửa ⇒ `done`. Trả lời được câu *"lần chạy hỏng VÌ
  vòng sửa, hay vốn đã hỏng"*.
* `test_HAI_PHIEN_gap_nhau_that_su_thanh_database_is_locked` — chứng minh cái
  bẫy **có thật** trên đúng engine này, trước khi đi đo bản vá.

---

## 2. Nguyên nhân gốc — **cùng hình dạng M-08, khác người gọi**, và nó KHÔNG
   phải một suy luận từ M-08

Đo bằng một hook `before_cursor_execute` ghi lại mọi lệnh DML **theo từng kết
nối** kèm stack. Cặp **giữ / chờ** in ra:

```
GIỮ   (phiên của giai đoạn — thi_hanh.chay_giai_doan)
      UPDATE asv_asset SET integrity=? WHERE asv_asset.id = ?
        thi_hanh.py:345   chay_giai_doan
        giai_doan_giong.py:208  chay
        giai_doan_giong.py:548  _doan_con_dung
        assets.py:467           kiem_toan_ven        <-- db.flush(), KHÔNG commit

CHỜ   (phiên THỨ HAI — job_runner._one_session)
      UPDATE jobs SET progress=?, heartbeat_at=? WHERE jobs.id = ?
        giai_doan_giong.py:175  ctx.progress(...)    <-- vòng lặp KẾ TIẾP
      => sqlite3.OperationalError: database is locked
```

**Cùng hình dạng M-08** (`giai_doan_ban_dung`: `_khoa_con_dung` →
`kiem_toan_ven` → `flush`, rồi `ctx.progress(60)`), **cùng một hàm**, **khác
giai đoạn**. Nhưng M-09 có thêm **hai thành phần mà M-08 không có**, và thiếu
một trong hai thì nó không nổ:

1. **Nhánh `continue` bỏ qua `db.commit()`.** `giai_doan_giong.chay` commit ở
   **cuối** mỗi vòng lặp (dòng 328). Nhưng nhánh *"đoạn cũ còn dùng được"*
   (`if cu is not None: ... continue`, dòng ~236) **nhảy qua** dòng đó. Nên khoá
   ghi mà `kiem_toan_ven` mở sống sang **vòng lặp sau**, và nạn nhân là
   `ctx.progress` ở **đầu** vòng đó — cách chỗ gây ra nó 50 dòng và một vòng lặp.
2. **Chỉ vòng sửa mới làm giá trị ĐỔI.** `kiem_toan_ven` (bản cũ) ghi **vô điều
   kiện**. Ở lượt chạy đầu, `_doan_con_dung` không tìm thấy `AsvAsset` nào nên
   thoát trước khi tới đó. Ở vòng sửa thì có: `vo_hieu_theo_day_chuyen` vừa đặt
   `integrity = missing`, tệp hoá ra vẫn nguyên, phép đo trả `ok` — **một lần ghi
   thật**.

⇒ Đây là lý do M-09 vô hình suốt từ pha 19: nó cần **một vòng sửa thượng nguồn**
để có gì mà ghi, và cần **một đoạn dùng lại được** để bỏ qua commit. Không một
phép kiểm nào của kho dựng đủ cả hai cho tới `test_2121` (23/09).

### 2.1 Vì sao M-08 vá rồi mà M-09 vẫn còn

Bản vá M-08 đặt `db.commit()` **tại chỗ gọi** (`giai_doan_ban_dung.py:286`).
`assets.kiem_toan_ven` có **năm** người gọi:

| người gọi | tình trạng trước 23/09 |
|---|---|
| `giai_doan_ban_dung._khoa_con_dung` | đã vá (M-08) |
| `giai_doan_giong._doan_con_dung` | **M-09** |
| `assets.cache_dung_duoc` | chưa nổ (gọi sớm, phiên còn sạch) |
| `cache_chung._artifact_song` | chưa nổ |
| `giai_doan_ket_xuat` | chưa nổ |

⛔ Vá một chỗ gọi để lại **bốn** cái bẫy y hệt. M-09 là cái thứ hai trong bốn.

### 2.2 Trên PostgreSQL thì hình dạng này là gì

Hai lệnh `UPDATE` ở trên chạm **hai bảng khác nhau** (`asv_asset` / `jobs`).
PostgreSQL khoá ở **mức dòng**, nên phiên thứ hai không đợi ai cả: M-09 **không
biểu hiện** trên production — ⭐ **đã đo trên PostgreSQL thật**, §5.1. Nhưng khiếm khuyết thì vẫn có thật ở đó — giai đoạn
giữ một transaction ghi mở suốt cả vòng lặp sinh tiếng (đo được **937 giây** cho
một phim 107 s, `bang_chung/NEN_V3.md`) thay vì vài mili giây. ⇒ Bản vá phải
đúng theo nghĩa *"không giữ transaction ghi qua một lời gọi mở phiên thứ hai"*,
chứ không phải theo nghĩa *"làm SQLite hết kêu"*. Đo thật: §5.

---

## 3. Đã sửa gì — **hai tầng**, và cả hai đều cần

### 3.1 Tầng gốc — `assets.kiem_toan_ven` không còn để lại transaction ghi

Hàm mang tên một phép **đọc** (*"kiểm"*) nhưng nó **ghi**, và người gọi không có
lý do gì để đoán ra điều đó từ tên hàm. Tách đôi:

| | trước | sau |
|---|---|---|
| đo | lẫn trong hàm | `assets._do_toan_ven(kho, asset)` — **thuần đọc**, không chạm CSDL |
| ghi khi **không đổi** | `db.flush()` vô điều kiện | **không ghi gì** — đường lành để phiên người gọi sạch |
| ghi khi **có đổi** | `db.flush()` (treo khoá) | `db.commit()` |

⭐ `commit` chứ không `flush` vì giá trị này là một **quan sát về thế giới**
(*"tệp này biến mất"*), không phải một mảnh của đơn vị việc người gọi đang làm:
nó đúng kể cả khi giai đoạn sau đó hỏng và bị `rollback`. Đó cũng đúng là luật
`thi_hanh.chay_giai_doan` đã ghi trong nhánh bắt lỗi của nó — *"điểm chốt đã
`commit` … đó là cả lý do chúng `commit` ngay tại chỗ thay vì `flush`"*.

⛔ **Không** dùng một phiên riêng cho lần ghi này. Phiên của người gọi vừa
`SELECT` chính dòng đó nên trên SQLite nó đang giữ khoá **đọc**; một phiên thứ
hai xin khoá ghi sẽ **đợi chính nó** — đúng cái bẫy vừa gỡ, đặt ngược chiều.

### 3.2 Tầng hàng rào — `thi_hanh._CtxChotSo`

Tầng 3.1 sửa **một hàm**. Nó không sửa **luật** *"đừng giữ transaction ghi qua
một lời gọi `ctx`"* — và luật đó đã bị quên **hai lần, ở hai giai đoạn**, bởi
cùng một hàm. Một luật không ai thi hành được thì sẽ bị quên lần thứ ba.

`chay_giai_doan` là **nơi duy nhất** nắm giữ cả phiên của giai đoạn lẫn `ctx`,
nên bất biến được thi hành ở đó: `ctx` được bọc, và trước mỗi lời gọi **mở phiên
thứ hai để GHI** (`progress`, `event`, `stage`, `provider_dispatched`,
`provider_rejected`) phiên thứ nhất được **chốt sổ**.

Hai loại trừ, cả hai đều có lý do đo được:

* ⛔ **`is_cancelled` KHÔNG nằm trong danh sách.** (a) Nó chỉ **đọc**, và một lần
  đọc ở phiên thứ hai không va vào khoá ghi của phiên thứ nhất; (b)
  `cache_chung.GiuCho` gọi nó từ **luồng nhịp** — `commit` một `Session` từ một
  luồng khác là một lỗi **nặng hơn hẳn** cái đang được sửa. Có thêm một chốt
  chặn cơ học: `_chot()` là no-op khi luồng gọi không phải luồng sở hữu phiên.
* ⛔ Đang trong một **SAVEPOINT** (`su_dung.ghi`) thì không chốt — `commit` ở đó
  sẽ đóng cả transaction ngoài, tức quyết định thay cho người đang giữ savepoint.

---

## 4. Bằng chứng trước / sau — và phép **đột biến** để bản vá không tự khen

| phép | trước bản vá | sau |
|---|---|---|
| `test_2160` (8 bài) | 2 ĐỎ (`database is locked`), 6 xanh | **8 xanh** |
| `test_2121` (làn `qc-hinh`, 7 bài) | 7 xanh (bài vòng sửa **cố ý không chốt** `run.status`) | 7 xanh |
| vòng sửa `cat_sai` chạy tới `run.status` | `error` | **`done`** |
| vòng sửa `dich_sai` trên **PostgreSQL** thật (§5.2) | — | **`done`**, 42 job, 1 vòng |
| bộ ASV nhắm (15 tệp, dưới khoá `cpu_nhieu`) | — | **278 passed, 1 skipped** |

**Đột biến** — gỡ từng vế của bản vá rồi chạy lại đúng bài đã đỏ. ⛔ Một bản vá
không đo được vế nào của nó đang gánh việc là một bản vá không ai kiểm lại được:

| gỡ | kết quả |
|---|---|
| gỡ **cả hai** vế (3.1 + 3.2) | **M-09 quay lại** — `database is locked`, y nguyên |
| gỡ vế 3.1, giữ hàng rào 3.2 | xanh |
| gỡ vế 3.2, giữ 3.1 | xanh |

⇒ Hai vế **chồng lấn có chủ đích**: 3.1 là nguyên nhân gốc (và gỡ bẫy cho **bốn**
người gọi còn lại của `kiem_toan_ven`), 3.2 là hàng rào cho giai đoạn **chưa ai
viết**. Bảng trên nói rõ rằng hôm nay mỗi vế đều đủ một mình — giữ cả hai là một
quyết định, không phải một sự trùng lặp vô tình.

### 4.1 Sổ cái sau vòng sửa

Đo trên `test_vong_sua_KHONG_tinh_tien_hai_lan_cho_cung_mot_doan` (3 đoạn tiếng,
đoạn đầu bị chấm WER 0,95):

* `ma_dispatch` của mọi dòng `voice_synthesis` **đôi một khác nhau** — không một
  bút toán nào bị `UNIQUE(run_id, ma_dispatch)` nuốt, và cũng không cái nào trùng;
* số dòng theo đoạn: `[1, 1, 2]` — **đúng một** đoạn có hai lượt đọc thật (vân tay
  có muối vòng sửa, M-07), hai đoạn lành **không bị đọc lại**. Tức vòng sửa tiêu
  tiền cho **đúng** cái nó sửa;
* `VONG_SUA_TOI_DA = 1` được tôn trọng ở cả ba đường: đúng **một** dòng
  `nang_luc=sua_chua` trong sổ, đếm bằng số dòng chứ không bằng một biến;
* khuôn thử có trần 200 job; cả ba đường đều về dưới trần ⇒ **không vòng quay**.

---

## 5. PostgreSQL — **ĐÃ ĐO**

Khoá `cua_so_yen` `postgres_test` rảnh lúc 23/09; làn này **giữ khoá** rồi đo
trên `lttplatform_test`. ⛔ Không `drop_all` (một lượt nghiệm thu vừa xong trên
cùng CSDL đó) — chỉ `create_all` (cộng thêm), dòng sinh ra mang `owner_id`
riêng `uPG-suakhoa`, xoá hết ở cuối (168 job + run).

### 5.1 Hình dạng khoá: M-09 **không biểu hiện** trên PostgreSQL

Đặt đúng cặp giữ/chờ của §2 lên PG: phiên A giữ một `UPDATE` chưa commit, phiên
B (hình dạng `ctx.progress`) ghi một dòng khác.

| | SQLite | PostgreSQL |
|---|---|---|
| phiên B ghi khi phiên A đang giữ | `database is locked` | **đi qua, không đợi** |
| phiên A commit sau đó | — | không xung đột |

⇒ Khoá **mức dòng** của PG: hai lệnh chạm hai bảng khác nhau (`asv_asset` /
`jobs`) nên không có gì để tranh. **Production chưa từng gặp M-09** — nó là một
lỗi chỉ giết lần chạy trên SQLite. ⚠️ Nhưng khiếm khuyết thì có thật ở cả hai:
giai đoạn giữ một transaction ghi mở suốt vòng lặp sinh tiếng (đo được **937
giây** cho một phim 107 s, `bang_chung/NEN_V3.md`) thay vì vài mili giây.

### 5.2 Cả vòng sửa chạy trên PostgreSQL

Bài đã đỏ ở §1 (`dich_sai` → `content_process`) chạy lại với fixture `db` trỏ
`lttplatform_test`, **cùng thân bài**, hàng đợi thật, worker thật:

| phép | số đo |
|---|---|
| `run.status` | **`done`**, `run.error` rỗng |
| job của riêng lần chạy này | **42** |
| vòng sửa trong sổ cái | **1** (`giai_doan_sua = ["content_process"]`) |
| dòng sổ cái `voice_synthesis` | **3**, `ma_dispatch` đôi một khác nhau |

⇒ Bản vá **không** chỉ làm SQLite hết kêu: đường PostgreSQL đi qua nguyên vẹn,
và hai lo ngại đã nêu (một `commit` giữa chừng cắt mất `rollback` của PG; số
lượt ghi tăng) **không xảy ra** ở quy mô đo được.

### 5.3 ⚠️ Phát hiện phụ — `lttplatform_test` có một run MỒ CÔI đang quay

Lượt đo đầu chạm trần 200 job của khuôn thử, và **không phải vì lần chạy này**:

```
RUN LA DANG SONG trong CSDL test: 1
  ('asvr_d29cef8a3e3c4d4392ca08b2ea0f7ee', owner 'cff233e0-4c59-…', 'running')
```

Một `AsvRun` **`running`** của **một phiên khác** nằm lại trong CSDL test; job
`advance` của nó **tự nộp lại vô hạn**, nên mỗi lượt gọi `_chay_het_hang_doi`
đều nhặt job của nó. Bảng `jobs` đã tích tụ **1.274** dòng.

⛔ Làn này **không xoá dữ liệu của phiên khác** (luật 4). Báo điều phối:
(a) run đó cần được đưa về trạng thái kết thúc hoặc xoá; (b) mọi bài PG đếm số
job phải đếm **theo `run_id` của mình**, không đếm tổng — trần 200 của
`_chay_het_hang_doi` là một trần **dùng chung**, và trên một CSDL dùng chung nó
không còn đo được "vòng sửa có quay không".

### 5.4 Còn lại chưa xác minh

* **`test_2160` vẫn ghim SQLite** qua fixture `db` của `test_402`. Lượt PG ở
  §5.2 chạy bằng một bản sao scratch, **không** nằm trong kho — biến nó thành
  một bài thường trực cần một fixture `db` theo tham số, và cần §5.3 được dọn
  trước (nếu không nó đỏ vì rác của người khác). Đây là việc còn lại **duy nhất**
  của vế PostgreSQL.

### 5.5 Những thứ khác chưa đo

* **Chưa đo trên phim thật.** Mọi con số ở đây đến từ khuôn `test_402` (video
  sin 0,4 s, 3 đoạn tiếng). Một vòng sửa trên phim thật (`v1`–`v4`) chạm thêm
  `lat_cat` nhường/nối tiếp giữa vòng sửa — đường đó **có** test
  (`test_2025`, `test_2121`) nhưng chưa lượt thật nào đi qua **sau** bản vá.
* **Ba người gọi còn lại của `kiem_toan_ven`** (`cache_dung_duoc`,
  `cache_chung._artifact_song`, `giai_doan_ket_xuat`) nay **an toàn theo xây
  dựng** (§3.1) nhưng chưa có bài nào chứng minh từng cái một — chúng chưa bao
  giờ nổ, nên không có phép đo đỏ để lấy làm mốc.
* **`giai_doan_ban_dung.py:286`** giữ nguyên `db.commit()` của bản vá M-08. Nay
  nó **thừa** (3.1 + 3.2 đã phủ), nhưng gỡ một dòng vá đang đúng để cho gọn là
  một thay đổi không ai cần — và ghi chú của nó là bằng chứng lịch sử của M-08.
* **`test_2121::test_cho_noi_HONG_sinh_vong_sua_NHAM_DUNG_CHO_va_CO_TRAN`** cố ý
  **không** chốt `run.status == done`, vì lúc nó được viết thì M-09 chặn đường.
  Nay chốt được rồi, nhưng đó là **tệp của làn `qc-hinh`**; làn này chốt mệnh đề
  còn thiếu ở tệp của mình
  (`test_vong_sua_CAT_SAI_dat_lai_edit_plan_va_chay_lai_CA_CHUOI`) thay vì sửa
  tệp của người khác. ⇒ Đề nghị điều phối: sau khi gộp, nới bài đó lên `done`.

---

## 6. Phép kiểm

| Tệp | Bài | Hỏi gì |
|---|---|---|
| `tests/test_2160_asv_vong_sua_khoa_csdl.py` | 8 | **Đối chứng**: không khiếm khuyết ⇒ không vòng sửa, `done` · hai phiên gặp nhau THẬT SỰ thành `database is locked` · **ba đường sửa** (`doc_sai` → `voice_synthesis`, `dich_sai` → `content_process`, `cat_sai` → `edit_plan`) đều chạy trọn tới `done`, đúng một vòng, không vòng quay · sổ cái: không bút toán trùng, đúng một đoạn bị đọc lại · `kiem_toan_ven` không để lại transaction ghi (và đường lành thì không ghi gì) · `_CtxChotSo` chốt sổ trước lời gọi mở phiên thứ hai, và uỷ quyền thuộc tính vẫn chạy |

⛔ Hai bài cuối (`kiem_toan_ven`, `_CtxChotSo`) cố ý **không** đi qua nhau: nếu
bài hàng rào dùng `kiem_toan_ven` thì nó chỉ đo lại vế thứ nhất một lần nữa, và
sẽ xanh cả khi hàng rào bị gỡ hẳn.
