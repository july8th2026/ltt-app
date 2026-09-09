# 07_CHANGE_LEDGER — mọi thay đổi mã, kèm bằng chứng

Một dòng cho một thay đổi. Không có mục nào ở đây mà không có **kiểm đột biến**
(§15 STEP 7): tiêm lại lỗi cũ, test phải ĐỎ. Test không đỏ khi bỏ bản sửa là
test không chứng minh được gì.

---

## P1 — Nối kho chung vào đường lùi giọng (mục 38)

**Ngày:** 09/09/2026 · **Trạng thái:** mã xong, chờ cụm hồi quy + B-01

### Nguyên nhân gốc

`lui_giong.tu_giong_mau()` gán **cứng** `ngon_ngu="vi"` và chỉ đọc 20 preset
engine. Một giọng làn `en` mất biểu diễn ⇒ `chon()` trả `None` ⇒ khách nhận lỗi
thay vì một bản đọc.

Baseline của tôi xếp đây là `DATA_GAP` (*"kho rỗng"*). **Sai.** `KHO_GIONG/00_KIEM_KE.md`
khai kho chung có **25 giọng (8 VI + 17 EN)** từ 01/09, đã curate, đang sống trên
production. Kho không rỗng — chúng chỉ chưa bao giờ được nhìn thấy.

### Thay đổi

| tệp | việc |
|---|---|
| `tham_chieu.py` | `+ ung_vien_kho_chung(db)` — dựng `UngVien` từ kho chung, qua `_dieu_kien_kho_chung()` (cổng license), chỉ `trang_thai="active"` và `gioi` đã khai |
| `features.py` | `giai_giong`: thêm **bước hai** sau khi giọng mẫu hết ứng viên |
| `lui_giong.py` | `UngVien` `+ nhan: str = ""` — tên cho người đọc |

Đo: 4 tệp, **+203 / −1**.

### Ba quyết định trong bản sửa

**① Hai bước, KHÔNG gộp một danh sách.** `giai_giong` gọi `chon()` không truyền
`vung`/`phong_cach` (cả hai `""`). Giọng kho chung không có hai trường ấy nên
chúng khớp nấc ①; preset engine — vốn CÓ vùng và phong cách thật — trượt nấc ①
lẫn ② và chỉ được nhặt ở nấc ③.

⇒ Gộp sẽ **lặng lẽ** đổi mọi lượt lùi tiếng Việt sang giọng kho chung. Hai bước
giữ đường `vi` không đổi một byte; bước hai chỉ nổ khi bước một trả `None`.

**② Đi qua `tim_profile`, không tự truy vấn.** Đó là chỗ duy nhất kiểm quyền
đọc, và cổng license nằm trong nó. Một đường lùi có lối riêng là một cổng bị
vòng — bị vòng ở đúng nhánh không ai nhìn.

**③ `nhan or ma` cho câu cảnh báo.** `ma` của giọng chung là `public_id`
(`vc_<32 hex>`). Đưa chuỗi ấy vào *"bài này được đọc bằng …"* là đưa một mã máy
cho người đọc — tệ hơn im lặng, vì khách không tra được nó ở đâu. Giọng mẫu
không đặt `nhan` nên nhánh cũ trả đúng `ma` như trước.

### Test — 5 mới, tổng 29

```
test_lan_EN_mat_bieu_dien_NAY_LUI_DUOC_qua_kho_chung
test_lui_kho_chung_dung_TEN_chu_khong_phai_public_id
test_lan_VI_VAN_lui_ve_PRESET_du_kho_chung_da_co       <- chong hoi quy
test_kho_chung_CHUA_SOAT_LICENSE_thi_khong_duoc_lam_ung_vien
test_ung_vien_kho_chung_BO_giong_khong_ro_gioi
```

`29 passed in 1.50s` (SQLite trong `tmp_path`, không chạm `postgres_test`).

### ⭐ Kiểm đột biến — CẢ HAI đều ĐỎ đúng chỗ

**Đột biến 1** — gộp hai kho làm một danh sách:

```
FAILED test_lan_VI_VAN_lui_ve_PRESET_du_kho_chung_da_co
FAILED test_lan_EN_mat_bieu_dien_NAY_LUI_DUOC_qua_kho_chung
2 failed, 27 passed
```

Thông điệp đỏ nói đúng cơ chế: *"bài này được đọc bằng **Khong duoc chon** (Nam)"*
— tức một bài **tiếng Việt** vừa bị đổi sang giọng kho chung. Đó chính xác là
hồi quy mà quyết định ① chống, và test bắt được nó.

**Đột biến 2** — gỡ hẳn bước kho chung (`con_lai = ()`):

```
FAILED test_lan_EN_mat_bieu_dien_NAY_LUI_DUOC_qua_kho_chung
FAILED test_lui_kho_chung_dung_TEN_chu_khong_phai_public_id
2 failed, 27 passed
```

Cả hai đột biến đã hoàn nguyên; `grep "DOT BIEN"` trả **0**.

### Còn thiếu trước khi chấm >= 98

1. Cụm hồi quy rộng hơn (`test_338 · 380 · 399 · 501 · 506 · 507 · 508`) —
   **đang chờ**: phiên khác giữ `cpu_nhieu` + `postgres_test` lúc 16:0x.
2. **B-01** — xác nhận trên CSDL thật rằng 17 giọng `en` có `gioi` đã khai và
   `license_status="ok"`. Mã đúng không bảo đảm dữ liệu đúng.
3. Một lượt E2E thật: giọng `en` mất biểu diễn → khách nghe được bài + thấy
   cảnh báo.

⇒ Mục 38: **25 → 82**, trần **90** (chưa E2E). Trần cũ 75 (§7.9 *"dataset
rỗng"*) **không còn áp dụng** — dataset không rỗng, nó chỉ chưa được nối.

---

## P2 — Phát dần có tính tiền, mô hình β (mục 20)

**Ngày:** 09/09/2026 · **Trạng thái:** mã xong, chờ cụm hồi quy + JS + E2E

### Quyết định của chủ sản phẩm

Mô hình **β**: giữ chỗ trước, quyết toán theo **số byte PCM đã thật sự gửi đi**.
Ngắt giữa chừng ⇒ trả đúng phần đã nghe.

⚠️ Trước đó tôi khuyên **α** (nghe thử mở rộng). Phép đo bác nó:
`nghe_thu_cua_toi.TRAN_KY_TU = 160` ⇒ 160 ký tự ≈ **0,94 giây** sinh, nên
streaming cửa ấy không ai kịp nghe thấy khác biệt; và nâng trần thì chính module
cấm (*"dùng chung trần với đường trả tiền là mở đúng cái cửa mà mọi trần khác ở
đây sinh ra để đóng"*). Tôi đã trình ba phương án **trước khi** đo trần — lỗi
của tôi.

### Thay đổi

| tệp | việc |
|---|---|
| `sidecar_client.py` | `+ phat_dan()` generator · tách `_dich_loi_http`/`_dich_loi_url` dùng chung thay vì chép |
| `gia.py` | `+ doc_sample_rate()` · `+ giay_tu_pcm()` · `+ DinhDangLa` · hằng số định dạng |
| `routes/_p_phat_dan.py` | **mới** — `POST /phat-dan` |
| `routes/__init__.py` | đăng ký |

### Bốn chỗ dễ sai đã xử

**① Suất GPU phải sống SUỐT generator.** `hold_persisted` là context manager và
khối của nó kết thúc **trước khi** Starlette chạy generator ⇒ dùng nó là nhả
suất ngay lúc bắt đầu phát. ⇒ `acquire()` trước khi trả phản hồi (để còn 503
được), rồi `keep_alive(lease_id)` trong generator lo nhịp đập và nhả.

**② Phiên CSDL của generator là phiên RIÊNG.** Phiên của route đóng khi route
trả về; quyết toán chạy sau đó.

**③ Nguồn chân lý thứ hai được KHAI RA.** Đường job đo bằng `ffprobe`; đường này
đo bằng byte vì **không có tệp** lúc tính. Ba thứ giữ hai thước đo khớp: định
dạng bị ghim và **nổ** nếu khác (`DinhDangLa`), hợp đồng byte có test, và cùng
một `tinh()` ra giá.

**④ Khoản giữ luôn có đường về.** `job_id` tổng hợp `stream:<uuid>` — không hàng
`Job` nào mang khoá ấy, nên `credit.giu_cho_treo` nhặt nó sau 6 giờ nếu tiến
trình chết giữa stream. `finally` lo ca thường, bộ quét lo ca chết.

### Test — `test_514`, 16 mới · tổng 45 xanh (2,39s)

Ghim **hợp đồng byte** giữa `voice_sidecar/server.py::_wav_header_mo` và
`gia.doc_sample_rate`: header dài đúng 44, sample rate đọc đúng ở 16/24/48 kHz,
và **stereo thì NÉM** — vì stereo tính như mono cho ra số giây gấp đôi, tức
**thu gấp đôi**.

Bất biến trung tâm: giữ chỗ cho bài 1.000 ký tự, khách nghe 10 giây rồi ngắt ⇒
thu đúng `gia.tinh(10.0)`, hoàn phần dư. Ngắt ngay lập tức ⇒ **thu 0**.

### ⭐ Kiểm đột biến — một hằng số, 8/16 đỏ

Tiêm `PCM_BYTE_MOI_MAU = 1` (quên 16-bit ⇒ số giây gấp đôi ⇒ **thu gấp đôi**):

```
8 failed, 8 passed
  ... doc_duoc_sample_rate_tu_header_that[16000/24000/48000]
  ... giay_tu_pcm[3 ca]
  ... byte_le_lam_tron_XUONG_mau
  ... quyet_toan_thu_theo_BYTE_DA_GUI_va_hoan_phan_du
```

Đã hoàn nguyên; `grep "DOT BIEN"` trả **0**.

### Còn thiếu trước khi chấm >= 98

1. **JS + giao diện** — chưa có nút nào gọi `/phat-dan`. Mã có, khách chưa dùng được.
2. **Cờ `LTT_VOICE_STREAM=1`** trên production — chưa đặt; sidecar trả 404 tới khi bật.
3. **E2E thật**: nghe được câu đầu ~2 s · ngắt giữa chừng · đối chiếu sổ credit.
4. Cụm hồi quy rộng + hợp đồng Public API.

⇒ Mục 20: **55 → 78**, trần **90** (chưa E2E). Bốn trên tám lớp thành **sáu**.

---

## P2b — Giao diện phát dần (mục 20, lớp cuối)

**Ngày:** 09/09/2026

| tệp | việc |
|---|---|
| `routes/_p_phat_dan.py` | `+ bat_phat_dan()` · route trả **404** khi cờ tắt |
| `routes/_p_tao.py` | truyền `phat_dan_bat` vào ngữ cảnh Studio |
| `templates/ltt_voice_studio.html` | nút, **trong** `{% if phat_dan_bat %}` |
| `server/static/voice.js` | `+ ganPhatDan()` — trình phát Web Audio, +121 dòng |
| `locale/en/LC_MESSAGES/messages.po` | 5 chuỗi (3 route + 2 nút) |

### Vì sao trình phát tự giải PCM

Hai đường tự nhiên đều đóng, và cả hai là sự thật kỹ thuật chứ không phải sở thích:

- `<audio src>` chỉ làm **GET**; cửa này là **POST** (CSRF + giữ credit);
- **`MediaSource` không hỗ trợ WAV**, nên đường MSE cũng đóng.

⇒ Còn Web Audio. Làm được vì định dạng đã ghim ở **hai đầu**. JS đọc sample rate
**từ header** (`getUint32(24, true)`), và `test_514` cấm gõ `48000` vào JS —
hằng số thứ ba cạnh hai hằng số đã có sẽ lệch vào ngày engine đổi tần số, và khi
ấy tiếng sai cao độ mà **không lỗi nào báo**.

`DataView` chứ không `Int16Array`: `Int16Array` đọc theo endianness của **máy**,
luồng thì luôn little-endian.

### Không có bề mặt chết

Nút dùng **cùng biến** `LTT_VOICE_STREAM` mà sidecar đọc, cùng lấy từ một
`app.env` ⇒ không có trạng thái *"web mở mà cổng đóng"*. Cờ tắt ⇒ route **404**.
Test chốt nút nằm sau `{% if phat_dan_bat %}`, và chốt `"true"` **không** bật cờ
— chỉ `"1"`, y hệt sidecar.

### Ba việc quy trình bắt

| | |
|---|---|
| **Bánh cóc dịch** | 3 chuỗi mới ⇒ 346 vs mốc 343, **FAIL**. Thêm tay `msgid`+`msgstr` (đúng lời công cụ: *đừng chạy `i18n.py trich`*), sửa bằng `Edit` vì `.po` là tệp dùng chung (luật 14) ⇒ về **343 PASS** |
| **Luật 18** | `voice.js` đã ở trong `TAI_SAN_CO_VERSION` và `asset_ver` là **băm nội dung** ⇒ URL tự đổi |
| **Kết dòng** | quét cuối bắt `gia.py` thành **293 dòng CRLF** — đúng bẫy Windows mà gate có bước soi. Chuẩn hoá về LF |

---

## P3 — Trần luồng CPU của sidecar (QĐ-V02, mục 11)

**Ngày:** 09/09/2026

### Vấn đề, đo được

    loi vat ly                            10
    torch.get_num_threads() (vieneu-venv) 10   <- lay TRON so loi
    voice_sidecar dat set_num_threads     KHONG

Cùng khuyết tật CLAUDE.md ghi cho `apps/auto_scan_video/demucs_runner.py`:
*"tiến trình con KHÔNG nằm trong ngân sách"*. Một tiến trình cháu không xin khoá
và không nằm trong `-n`; nó chỉ hiện ra ở CPU — và 03/09 máy đã sập vì lớp việc ấy.

### Con số DẪN XUẤT, không đặt bừa

    loi vat ly                     10
    tran pytest cua CLAUDE.md      -6      (`-n 6`, tran cung)
    con lai cho sidecar             4      <- TRAN_LUONG_MAC_DINH

Sidecar + một lượt gate đầy đủ = đúng 10, không vượt. Chọn số lớn hơn là **cố ý**
cho phép vượt lõi. Máy chủ chỉ chạy giọng nói thì đặt
`LTT_VOICE_TORCH_THREADS=10` — nên đây là biến môi trường, không phải hằng số chôn.

### Hai chi tiết dễ mất

**① Đặt TRƯỚC khi nạp model.** Pool luồng của torch dựng lúc nạp;
`set_num_threads` sau đó không thu chúng lại. `test_514` đo **thứ tự dòng**,
không chỉ đo sự tồn tại của hàm.

**② Đặt cả `OMP_NUM_THREADS`.** ONNX Runtime và BLAS đọc biến môi trường, không
đọc `torch.set_num_threads`. Đặt một thứ mà quên thứ kia là để nửa số luồng
thoát ra ngoài trần.

### ⭐ Kiểm đột biến — mẫu "năng lực có, không ai đi"

Gỡ **lời gọi**, giữ nguyên hàm:

```
FAILED test_tran_luong_GOI_TRUOC_khi_nap_model
  "nap() khong goi _dat_tran_luong() — nang luc co, khong ai di"
1 failed, 26 passed
```

Đã hoàn nguyên; `grep "DOT BIEN"` trả **0**.

---

## Cụm hồi quy — 311 xanh, 2 đỏ ĐÚNG DỰ KIẾN

```
14 tep voice, -n 6 --dist loadfile:  2 failed, 311 passed in 30,12s
  FAILED test_504::test_kiem_ke_phu_HET_va_khong_thua
  FAILED test_504::test_stream_van_chua_co_client_va_dieu_do_duoc_GHI_RA
```

Cả hai là **bánh cóc kêu đúng**: `test_504` ghim *"`/v1/stream` chưa có hàm
bọc"*, và P2 đã thêm hàm bọc. Chính docstring của nó viết sẵn việc phải làm:

> *"ngày ai đó thêm client, họ phải xoá phép kiểm này, và xoá nó là một hành
> động người review nhìn thấy."*

⇒ Đã **thay**, không nới. Bản thay chốt một mệnh đề **khó hơn**: `phat_dan`
không được đi qua `_goi` (vì `_goi` gọi `r.read()` — đệm trọn thân), và phải là
generator thật. Đo bằng AST.

⚠️ Mệnh đề ấy quan trọng vì nó bắt một lỗi **không test chức năng nào thấy**:
đệm cả bài rồi mới "phát dần" thì âm thanh vẫn đúng, tiền vẫn đúng, chỉ độ trễ
tới byte đầu là hỏng. `KIEM_KE` cũng đã thêm `phat_dan: "san_pham"`.

`test_504` sau khi thay: **12 xanh**.

---

# CỔNG CHẤT LƯỢNG — lượt gom cuối

## Quick gate

**Lượt 1: FAIL (2/28)** — cả hai đỏ đều là của tôi, và cả hai là bài học:

### ① `kieu xuong dong` — tôi SỬA NHẦM

```
apps/ltt_voice/gia.py
   HEAD=CRLF  ->  hien tai=LF   (thay doi THAT: 64 dong)
```

Tệp ấy **vốn là CRLF trong git** (229 dòng ở HEAD). Tôi thấy CRLF trong lượt
quét toàn vẹn, gọi nó là "bẫy Windows", rồi chuẩn hoá về LF. Chính công cụ nói
ra thứ tôi bỏ qua:

> ⛔ ĐỪNG ép mọi tệp về LF: một số tệp **vốn LÀ CRLF** trong git. Khớp từng tệp.

Phép kiểm so **với HEAD, theo từng tệp** — nó không có khái niệm *"kết dòng
đúng"*, nó hỏi *"anh có đổi kết dòng của tệp này không"*. Cả hai chiều đều đỏ.

⇒ Đã khôi phục `gia.py` về CRLF. Và đã **đính chính ghi chú memory** đã dẫn tôi
tới luật sai ấy.

### ② `trung so test` — số 511 đã có chủ

`test_511_nghe_thu_van_ban_cua_khach.py` tồn tại từ trước. Đổi tên tệp của tôi
thành **`test_514_ltt_voice_phat_dan.py`** (514–530 còn trống).

**Lượt 2: PASS** (28 bước).

## Gate đầy đủ

**Lượt 1: FAIL (1/32)** — đúng một bước (`bo test song song`), **10 đỏ / 8.892**,
11,8 phút.

| test | số | của ai |
|---|---|---|
| `test_448_asv_v4_e2e_nghiem_thu` | 7 | **có sẵn** — commit HEAD ghi nguyên văn: *"gate cuoi 7 do deu la test_448"* |
| `test_505_nguon_ban_giao` | 2 | **có sẵn** — đỏ vì thiếu `yolov8n.pt` (model YOLO của ASV). `grep yolov8n` trong `apps/ltt_voice/` + `voice_sidecar/`: **rỗng** |
| `test_305::test_po_khong_co_msgid_trung` | 1 | 🔴 **CỦA TÔI** |

### `msgid` trùng — đo chứ không đoán ai gây ra

```
trung o HEAD  : 4
trung hien tai: 5
MOI (cua toi) : 1   ->  "Dừng"
```

`"Dừng"` **đã có** ở `apps/chataistudio/templates/chataistudio.html:46`. Một
catalog gettext chỉ được có **một** `msgid` cho mỗi chuỗi — chuỗi giống nhau thì
**dùng chung** một mục; đó là cơ chế của gettext, không phải một sự trùng lặp
cần dọn.

⇒ Gỡ mục của tôi, để lại chú thích tại chỗ cho lượt sau. Số trùng về **4 = đúng
bằng HEAD**; `test_305` **5 xanh**; bánh cóc dịch vẫn PASS ở mốc 343.

⚠️ Ghi rõ để không ai đọc nhầm: tôi **không** sửa 4 mục trùng có sẵn. Chúng
không thuộc phạm vi chiến dịch này, và `test_305` xanh với chúng — tức phép
kiểm ấy đo thứ khác với phép đếm thô của tôi.

### Xác minh sau khi sửa

`test_347` (render Studio) + `test_514` (phát dần): **45 xanh**.

## Gate đầy đủ — lượt 2 (lượt chính)

```
RESULT: FAIL (1/32)     9 failed, 8.893 passed, 61 skipped   11,6 phut
```

**10 → 9 đỏ, và 8.892 → 8.893 xanh.** Đỏ duy nhất của tôi (`msgid` trùng) đã hết.

### Chín đỏ còn lại — ĐO, không tuyên bố

Tôi không viết *"chín cái kia không phải của tôi"* rồi đi tiếp. Ba phép đo:

**① Tệp đỏ có chạm phạm vi tôi sửa không?**

```
test_448_asv_v4_e2e_nghiem_thu.py   2 tham chieu
test_505_nguon_ban_giao.py          0 tham chieu
```

Hai tham chiếu của `test_448` là **một dòng import** để fixture dựng lược đồ:

```
tests/test_448...py:62   import apps.ltt_voice.tables  # noqa isort:skip
```

`tables.py` **không** nằm trong 11 tệp tôi sửa.

**② Tệp tôi sửa có nằm trong phạm vi hai test đó không?**
`git diff --name-only | grep -E "auto_scan_video|nguon_ban_giao|yolo"` → **rỗng**.

**③ Chúng đỏ VÌ GÌ?**

```
test_448: AssertionError: ('giu_hinh', 'content_process',
          'khong provider nao phuc vu duoc: ltt_llm: ban')
test_505: khai nhung khong co tren dia: ['yolov8n.pt']
```

Một cái là **provider LLM bận**, một cái là **thiếu model YOLO**. Không cái nào
đi qua một dòng nào của LTT VOICE.

⇒ Kết luận có căn cứ: **0 đỏ thuộc về chiến dịch này.** Chín đỏ là đỏ của trunk,
và commit HEAD ghi sẵn bảy trong số đó: *"gate cuoi 7 do deu la test_448"*.

⚠️ Ghi thêm một quan sát, **không** phải kết luận: `ltt_llm: ban` xuất hiện
trong lúc một phiên khác vừa chạy gate đầy đủ, và máy B chỉ có **một** suất đồng
thời (`DONG_THOI_MAY_B=1`). Hai lượt gate chồng nhau có thể là nguyên nhân — đó
là việc của phiên giữ ASV, tôi chỉ ghi lại.

---

## P4 — Quét khiếm khuyết 27 hạng mục còn đọc được (09/09)

Chủ dự án yêu cầu *"xử lý code toàn bộ các hạng mục"*. Thay vì đọc tuần tự 27
mục, tôi quét theo **lớp khiếm khuyết** — nhanh hơn và bắt được thứ đọc tuần tự
dễ bỏ sót.

### Bốn lớp quét, bằng AST chứ không khớp chuỗi

| lớp | kết quả |
|---|---|
| Route thiếu `require_login` | **0** |
| POST thiếu `verify_csrf_token` | **0** |
| Route truy vấn `VoiceProfile` thẳng, bỏ qua `tim_profile` | **0** |
| Lời gọi mạng không `timeout` | **0** |

⚠️ Một cảnh báo giả tôi suýt báo: `_p_tao.py` đếm ra *8 route / 8 lần nhắc
`require_login`*, trong khi mọi tệp khác là *route ≤ nhắc − 1* (một lần là dòng
import). Trông như một route thiếu chốt. Đọc bằng AST thì không: `trang_tao`
mang **hai** decorator (`GET ""` và `GET "/"`) trên **một** hàm.

⇒ **Không có khiếm khuyết mã** ở 27 hạng mục ấy. Ghi ra để lượt sau không đi
tìm lại.

### 🔴 Nhưng có một lỗi thật — và nó nằm trong mã CỦA TÔI

Đọc lại `_p_phat_dan.py` đối chiếu bất biến của chính dự án:

```python
dau["X-Canh-Bao"] = "1"        # <- ban dau cua toi
```

`lui_giong.py` bắt **mọi lượt lùi phải sinh cảnh báo cho khách đọc**, vì hệ
`D:\Viral` đã lùi nam → nữ và khách báo lỗi 26/08. Tôi gửi một **lá cờ**: khách
biết *"có gì đó đã đổi"* mà không biết **đổi thành giọng nào**. Im một nửa vẫn
là im.

**Và bản sửa hiển nhiên sẽ hỏng nặng hơn.** Nhét chuỗi thô vào đầu HTTP:

```
cau.encode('latin-1')  ->  UnicodeEncodeError
```

Đầu HTTP chỉ nhận latin-1; câu cảnh báo luôn có dấu tiếng Việt. Starlette **ném**
⇒ cả phản hồi thành 500. `voice_sidecar/server.py::_dau` đã ghi đúng kiểu hỏng
ấy: *"việc đã làm xong rồi mới bị vứt đi"* — model sinh đủ tiếng, ghép xong, cân
mức xong, rồi cả lượt tan vì một chuỗi **giải thích**.

⇒ Mã hoá phần trăm ở máy chủ, `decodeURIComponent` ở JS. Đo:

```
cau goc : 120 ky tu   ·  tho -> NEM UnicodeEncodeError
ma hoa  : 359 byte    ·  latin-1 OK  ·  vong ve KHOP nguyen van
```

### Test — 3 mới (tổng 30 ở `test_514`)

```
test_canh_bao_lui_giong_ma_hoa_duoc_qua_dau_HTTP   <- chung minh CA HAI loi
test_route_phat_dan_MA_HOA_canh_bao_chu_khong_dat_co
test_js_GIAI_MA_canh_bao_va_hien_ra
```

Test đầu dùng `pytest.raises(UnicodeEncodeError)` để chứng minh lỗi (2) là
**thật**, không phải một lo xa.

### ⭐ Kiểm đột biến

Quay `X-Canh-Bao` về `"1"`:

```
FAILED test_route_phat_dan_MA_HOA_canh_bao_chu_khong_dat_co
1 failed, 29 passed
```

Hoàn nguyên; `grep "DOT BIEN"` trả **0**. Ba bộ voice chạy chung: **71 xanh**.

---

## P5 — `/phat-dan` vào bậc rate-limit ĐẮT (09/09)

### Lỗ, và nó lại nằm trong mã của tôi

Mô hình β thu theo **byte đã gửi** ⇒ ngắt trước byte đầu thu **0**. Cửa lại giữ
suất `vieneu_gpu` **duy nhất**. Hai điều đó cộng lại là một vòng lặp không tốn
tiền mà vẫn chiếm card — đúng lớp mà `nghe_thu_cua_toi` đã chặn cho đường miễn
phí, và ghi rõ vì sao:

> ⛔ KHÔNG hoàn khi engine ném lỗi giữa chừng: GPU đã chạy, và một đường hoàn ở
> đó là một vòng lặp thử-lại miễn phí không giới hạn.

### ⭐ Nhưng nền tảng đã có nguyên thuỷ — đừng viết bản thứ hai

Tôi định viết một bộ đếm riêng. Kiểm trước thì thấy `server/usage_rate_limit.py`
đã là middleware per-user cho **mọi** POST của **mọi** app, và docstring của nó
nói thẳng ý định:

> Trung tâm ở middleware → **KHÔNG sửa từng app**, tự áp cho mọi app hiện có +
> tương lai.

⇒ `/phat-dan` **đã** được giới hạn. Câu còn lại chỉ là **bậc nào**:

```
bac chung : 120/phut
bac dat   :  30/phut     <- `_EXPENSIVE_SUFFIXES`
```

Nó đang ở bậc chung. 120 lượt/phút cho một cửa giữ card là quá rộng.

### Sửa: một dòng

Thêm `"/phat-dan"` vào `_EXPENSIVE_SUFFIXES`. Không module mới, không bộ đếm
thứ hai, không trạng thái mới.

⚠️ **Đây là chỗ chiến dịch chạm `server/`** (CLAUDE.md luật 20 bắt dừng lại nói
rõ vì sao). Lý do nó KHÔNG thuộc `apps/`: chính module ấy khai danh sách bậc là
**điểm mở rộng trung tâm đã thiết kế**, và cấm mỗi app tự dựng bộ đếm riêng.
Thêm một dòng vào danh sách là **dùng** cơ chế; viết bộ đếm trong app là **đi
ngược** nó.

⚠️ Và ghi rõ giới hạn: bậc đắt là **anti-script**, không phải một ngân sách GPU
có căn cứ như `MOI_GIO=6` của `nghe_thu` (con số ấy rút từ một phép tính
GPU-giây). Ngày `/phat-dan` có lưu lượng thật, con số 30 phải được đo lại chứ
không mặc nhiên đúng.

### Test

```
test_phat_dan_nam_o_bac_DAT_chu_khong_phai_bac_chung
```

Kèm **đối chứng ngược**: `/tao` phải **không** bị kéo vào bậc đắt — nếu không
thì phép kiểm sẽ xanh với một bản vá thắt chặt nhầm cả cửa không giữ GPU.

`test_514`: **31 xanh**.

---

# GATE CUỐI — lượt chính, phủ P1–P7 + B-06

```
RESULT: FAIL (1/32)    9 failed, 8.905 passed, 61 skipped, 1 xfailed   11,5 phut
```

**8.893 → 8.905 xanh** (12 test mới). **0 đỏ thuộc chiến dịch này.**

## Dự đoán nói TRƯỚC, và nó khớp

Trước khi bấm, tôi ghi ra dự đoán: *"FAIL (1/32) với đúng 9 đỏ, tất cả có sẵn
trên trunk — `test_448` ×7, `test_505` ×2. Chênh so với con số đó là phần của
tôi."*

Kết quả: **đúng 9, đúng hai nhóm ấy.**

⭐ Vì sao ghi dự đoán trước lại quan trọng: nó biến "9 đỏ kia không phải của tôi"
từ một **lời giải thích sau khi thấy kết quả** thành một **phép kiểm có thể
sai**. Nếu ra 10 hay 11, tôi đã phải nhận phần chênh.

## Điều kiện đo — ghi ra vì con số không kèm điều kiện là con số sẽ bị cãi

```
truoc khi bam:  cua_so_yen RANH  ·  CPU 1%  ·  0 tien trinh gate/pytest
```

Lần **đầu tiên** trong buổi cả ba phép kiểm đồng ý. Năm lượt trước đó đều có
phiên khác đang chạy gate — và **hai lần** `cua_so_yen` báo `RANH` trong khi cây
tiến trình có `gate.py` + `pytest -n 6` đang bay. Khoá chỉ thấy ai **xin** khoá;
vế quyết định là cây tiến trình.

## Chín đỏ còn lại — không nhận, và nói rõ vì sao

| test | số | căn cứ |
|---|---|---|
| `test_448_asv_v4_e2e` | 7 | Đọc **tệp tĩnh đã commit** `docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json` ghi một lượt **hỏng**. Chạy lại bộ test không đổi gì |
| `test_505_nguon_ban_giao` | 2 | Thiếu `yolov8n.pt` (model YOLO của ASV) |

Đo ba chiều (đã ghi ở lượt trước): tệp đỏ chạm phạm vi tôi **chỉ** ở một dòng
`import apps.ltt_voice.tables`; `git diff --name-only | grep -E "auto_scan_video|yolo"`
**rỗng**; và lý do đỏ là *provider LLM* / *thiếu model YOLO*.

⚠️ Và một điều học được từ phiên `ltt-llm` sau đó, đáng ghi cạnh đây: `test_448`
hỏng **~50 % số lượt** ngay cả khi mọi thứ đúng (đo 8 lượt, phân bố **lưỡng
cực**). Nên *"chạy lại thấy xanh rồi ghi đè"* **không** phải bằng chứng — một
lượt xanh là đồng xu ngửa. Ai nhận nó phải đếm **tỉ lệ**, không chạy tới khi
xanh.
