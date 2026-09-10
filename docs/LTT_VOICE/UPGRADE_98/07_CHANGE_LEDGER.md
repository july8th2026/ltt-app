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

---

## Commit `a61c7a0d` — Wave A đóng sổ (10/09/2026)

36 tệp · +3.726 / −34. Stage **tường minh từng tệp** (luật 13). Nhánh
`claude/ltt-voice-98-upgrade-9b586f` — **không** commit vào `admin-mvp-v3`, vì
bảy cây dùng chung một `.git` nên commit vào nhánh dùng chung là **đã xuất
bản**. Không push.

Bốn hook pre-commit xanh (~0,6 s): bánh cóc ruff · kiểu xuống dòng · ranh giới
import · cấu hình thuần ASCII. Kiểm trước khi bấm: `do_voice_co_bi_mat.ps1`
thuần ASCII không BOM, `check_xuong_dong` PASS.

⚠️ Lúc commit có phiên khác đang chạy `gate --ho-so day-du` (pid 19656, được
1,6 phút). Vẫn bấm, và đây là lý do — không phải vì vội:

- (a) hook chỉ tốn ~0,6 s kiểm tĩnh, **không** gọi pytest ⇒ không phải lệnh
  nặng. Tôi đọc thân hook (`setup/pre-commit-hook.sh` +
  `.pre-commit-config.yaml`) rồi mới kết luận, chứ không đoán theo tên.
- (b) điều kiện thứ **BA** của giao ước — pre-commit checkout+apply đổi mtime
  **mọi tệp unstaged cùng cây** — không áp, vì lúc ấy `git status` **không còn
  dòng unstaged nào**.

Cả hai vế đo **trước** khi bấm. Đây đúng chỗ mà một lượt trước đã trượt: gộp
kiểm và chạy vào một lệnh thì cảnh báo tới **sau** quyết định.

## `FINAL_SCORECARD.md` — deliverable §33

Số đếm **rút bằng máy** từ chính bảng A (regex trên 77 dòng), không gõ tay:

    cham duoc bang so : 73   trung binh 86,11
    >= 98             :  0        <- muc tieu chuong trinh la >= 98 cho CA 87
    90-97             : 43
    80-89             : 23
    <  80             :  7
    chua co dong      : 10   15, 33-36, 66, 78-81

Phát hiện đáng giá nhất của phép đếm ấy **không** phải điểm trung bình, mà là
phân bố **trần**: 30/77 hạng mục có trần < 98, và 9 hạng mục đã **chạm đúng**
trần của mình (12, 19, 27, 28, 29, 45, 58, 64, 75). Với chín cái ấy, viết thêm
mã chỉ làm điểm **nhỏ đi**.

⇒ Câu trả lời cho *"viết tiếp mã thì có lên 98 không"* là **không**, và nó là
kết quả cơ học của §7 chứ không phải ý kiến của tôi. Thứ còn thiếu là **loại
bằng chứng** (benchmark audio đủ mẫu · E2E trên URL công khai · load test ·
diễn tập khôi phục · người thật nghe mù), và không dòng mã nào sinh ra được
loại bằng chứng ấy.

⛔ Cám dỗ nằm đúng ở chỗ này: hạ trần thì bảng đẹp lên ngay. Trần ở lại.

Đã sửa hai chỗ **lỗi thời** ở `01_SCORECARD_BASELINE.md`: tiêu đề mục B còn ghi
*"66 hạng mục còn lại"* (số của 13:37 ngày 09/09) và mục D còn ghi *"cố ý không
ghi điểm tổng"*. Cả hai **đúng lúc viết và sai lúc đọc** — đúng kiểu bảng chép
tay mà CLAUDE.md luật 5 cảnh báo, và lần này bảng chép tay ấy là của chính tôi.

## ⚠️ Đính chính 10/09 — `cua_so_yen` KHÔNG gánh được quyết định của tôi

Sổ này ghi điều kiện trước lượt gate cuối là ba tín hiệu **đồng thuận**:

    cua_so_yen RANH  ·  CPU 1 %  ·  0 tien trinh gate/pytest

Vế thứ nhất **không đứng được**. Phiên `ltt-4bot-workflow` quan trắc, tôi đọc
lại mã và xác nhận độc lập:

- `tests/test_394_nen_da_phien.py:131`, fixture `khoa_sach`, gọi
  `cua_so_yen.dang_giu()` rồi `nha(ep=True, …)` trên **mọi khoá đang có trên
  máy** — không riêng khoá của bài kiểm.
- Tệp ấy **không** monkeypatch `TEP_KHOA`/`_tep`; dòng 208 còn *assert* đúng
  đường dẫn thật. ⇒ fixture chạm tệp khoá **thật**.
- **6** bài dùng fixture × 2 lần `don()` = **12** lượt tháo khoá mỗi lượt gate.

⇒ **Mỗi lượt gate đầy đủ tự tháo khoá của chính nó giữa chừng**, rồi
`trang-thai` trả `RANH` suốt phần còn lại — đúng cửa sổ mà phiên kế tiếp đọc
rồi bấm.

🔑 Sai số của nó đi về phía **HÀNH ĐỘNG**: nó nói "rảnh" khi đang bận, không
bao giờ ngược lại. Đó là hạng nguy hiểm hơn hẳn sai số ngẫu nhiên.

### Vậy lượt gate của tôi có hỏng không — không, nhưng vì lý do khác lời tôi ghi

Vế thứ **ba** (`0` tiến trình `gate.py`/`pytest` trong cây tiến trình) mới là
thứ gánh quyết định, và nó không đi qua tệp khoá nên không dính lỗi này. Kết
quả cũ đứng nguyên.

Thứ phải sửa là **lời ghi**, không phải kết quả: ba tín hiệu ấy **không độc
lập** như tôi trình bày — một trong ba là âm tính giả có hệ thống. Ghi ba thứ
"cùng đồng ý" trong khi một thứ không có tư cách đồng ý là đúng lỗi mà
`su-that-doc-lap-chan-suy-luan-sai` nói tới.

⚠️ Ngược lại, lúc **commit** `a61c7a0d` thì `cua_so_yen` báo pid 19656 đang giữ
— tức một **dương tính**, và lỗi này không sinh dương tính giả. Nên căn cứ của
lượt commit không đổi.

### Không nhận việc vá

`tests/test_394` do phiên `ltt-4bot-workflow` nhận. Tôi **không** viết chồng.
Đã gửi lại cho họ một chi tiết bản vá dễ trượt: vá `TEP_KHOA` **một mình**
không đủ, vì `dang_giu()` (dòng 233) vừa đọc hằng số `TEP_KHOA` vừa
`glob()` trên `tempfile.gettempdir()` — hai nguồn đường dẫn độc lập. Và lever
cho vế thứ hai phải là `tempfile.tempdir`, **không** phải biến môi trường:

    goi lan 1                     : C:\Users\THANGT~1\AppData\Local\Temp
    sau khi dat tempfile.tempdir  : C:\ABC_GIA_DINH            <- CO hieu luc
    chi dat os.environ['TEMP']    : C:\Users\THANGT~1\...\Temp <- KHONG

Vá thiếu vế ấy thì test vẫn **xanh** (nó chỉ assert khoá của chính nó) mà lỗi
còn nguyên — một bản vá *trông* đúng.

### Đính chính của chính đính chính trên — lý do hết hạn, kết luận thì không

Phiên `ltt-4bot-workflow` vá xong (`56dfc811`, hai đòn bẩy + một bài kiểm ghim
**cơ chế** chứ không ghim tính chất), rồi nói ngược lại đúng cách tôi vừa ghi
mục trên. Họ đúng, và tôi kiểm lại bằng mã trước khi nhận.

Tôi ghi: *"`RANH` không tin được **vì** fixture xoá khoá"*. Câu ấy buộc một
**kết luận không hết hạn** vào một **lý do hết hạn** — sau `56dfc811` sẽ có
người đọc lại rồi tin `trang-thai`. Bản vá đóng **một** đường; còn hai, cả hai
có từ trước và không liên quan gì tới fixture:

| # | Đường | Kiểm |
|---|---|---|
| 2 | `chay_khong_khoa` — hết `--cho` thì gate **chèn và chạy mà không giữ gì**, có chủ đích | ✅ `gate.py:1596` + `cua_so_yen.py:298`, tôi đọc thật |
| 3 | Mọi thứ **không xin khoá**: `pytest` gõ tay, deploy, bốn dịch vụ production | hiển nhiên |

Trong đúng ca 2, `trang-thai` báo `RANH` một cách **hoàn toàn trung thực**
trong khi máy đang chạy một lượt nặng — không con bọ nào cả.

🔑 Câu sống lâu hơn, thay cho câu tôi ghi:

> **`cua_so_yen` trả lời được *"ai XIN khoá"*. Nó không trả lời được *"máy có
> bận không"*.** Cây tiến trình trả lời câu thứ hai, và đó là lý do cây tiến
> trình gánh quyết định — **cả trước lẫn sau** bản vá.

⇒ Kết luận của mục trên (vế thứ ba gánh quyết định) **giữ nguyên**. Thứ sai là
lý do tôi gắn vào nó. Đây đúng hạng lỗi mà
`gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra` nói: một phép đo **đúng** bảo trợ
cho một kết luận nó không trả lời.

### Và một điều cả hai phiên đều chưa nói: bản vá KHÔNG tới cây này

`56dfc811` nằm trên nhánh của họ. **Bảy cây dùng chung một `.git` nhưng mỗi cây
một bản checkout `tests/`.** Đo ngay sau khi commit ấy vào kho:

    git show 56dfc811 --stat        -> co trong .git chung
    grep -n "tempfile.tempdir" tests/test_394_nen_da_phien.py   -> KHONG THAY
    dong 138 van la  nha(ep=True, tai_nguyen=...)

⇒ Ở **cây này** đường 1 vẫn sống, và ở bốn cây kia gần như chắc chắn cũng vậy.
Cùng hình dạng với `ngan-sach-loi-khong-cuong-che-duoc-tu-mot-nhanh` (bốn cây
vẫn `-n 14` trong khi bản sửa đã có ở một nhánh).

⚠️ Nên câu *"đã vá"* đúng với **kho** và sai với **cây**. Ai đọc dòng này phải
tự chạy `grep` ở cây mình đang đứng, không tin bảng.

Tôi **không** cherry-pick `56dfc811` sang nhánh này: nó là hạ tầng dùng chung,
và nhánh này đang chờ hoà vào `admin-mvp-v3` — kéo về sẽ thành hai bản của cùng
một bản vá đi hai đường vào trunk.

Đã ghi lại thành memory `cua-so-yen-tra-loi-ai-xin-khoa-khong-tra-loi-may-co-ban`
(thay memory cũ, vì memory cũ mang đúng cái lý do hết hạn ấy).

### Đồng bộ hai tệp test từ trunk — và vì sao đây KHÔNG phải đảo lời

Trunk `admin-mvp-v3` nay đã có cả hai bản vá (`fedb0eaf` + `44e0e17e`, hoà qua
`5694f90c`). Đã lấy về cây này bằng `git checkout admin-mvp-v3 -- <hai tệp>`.

⚠️ Mục trên tôi viết *"**KHÔNG** cherry-pick `56dfc811` sang nhánh này"*. Lấy về
bây giờ **không** đảo lại lời ấy — hai hành động khác nhau:

| | lúc từ chối | bây giờ |
|---|---|---|
| bản vá ở đâu | chỉ trên **nhánh của phiên kia** | đã ở **trunk** |
| lấy về nghĩa là | tạo **đường thứ hai** cùng một bản vá vào trunk | **đồng bộ** với trunk |
| khi hoà | hai commit khác nhau cho cùng một thay đổi | git thấy hai bên **giống nhau** |

Lý do từ chối là *tránh hai đường vào trunk*, không phải *tránh bản vá*. Khi
trunk đã có, lý do ấy hết áp — và giữ nguyên trạng lúc này mới là sai.

Đo trước khi lấy, để biết mình nhập cái gì:

    git log --oneline 99017910..admin-mvp-v3 -- <hai tep>
      44e0e17e  Ro ri thu HAI: test_361 ...
      fedb0eaf  Mot fixture test dang thao khoa ...
    => DUNG hai commit va, khong thay doi nao khac di ke.

Sau khi lấy, `sha256` hai tệp **khớp từng byte** với bản trunk.

### Đối chứng hai chiều — tự chạy, không nhận theo lời

    TIEN DE  dang_giu() liet ke khoa THAT?              True
    NUA 1    nha(ep=True) tren khoa KHONG phai cua minh -> xoa duoc?  True
             => phep do BAT duoc su pha hoai
    NUA 2    pytest 2 tep -> 60 passed, rc=0
             khoa that TRUOC: True   SAU: True    => DA CACH LY

⛔ **Nửa 1 phải KHOANH vào khoá của chính phép đo.** Tái hiện dạng rộng
(`dang_giu()` rồi `nha(ep=True)` từng cái) chính là hành vi đang được vá — chạy
nó để "chứng minh lỗi có thật" sẽ phá khoá thật của phiên khác. Nên nửa 1 ở đây
chứng minh **cơ chế** trên đúng một khoá do phép đo tự dựng: `ep=True` xoá được
một khoá **không phải của người gọi**. Cộng với tiền đề (`dang_giu()` **có** với
tới khoá thật) là đủ suy ra vòng cũ sẽ xoá nó.

⭐ Con số đáng nhớ của cả vụ này là của phiên `Dọn Dẹp hệ thống API` đo trên
trunk: bản **CHƯA** vá cho **`31 passed`** trong khi đang xoá hàng rào đồng thời
của cả máy. Hình dạng đầy đủ của lỗi không phải *"một bài đỏ khó hiểu"* mà là
**không bài nào đỏ cả** — cùng họ với
`du-lieu-tu-dung-khong-bao-dam-ket-qua`.

⇒ Cây này nay chạy gate lại được. Điều kiện tôi tự đặt ở mục trên (*"không chạy
gate cho tới khi ff"*) đã gỡ, và gỡ bằng **phép đo**, không bằng thông báo của
người khác.

### Đóng nhánh khoá — bốn tầng, và bài học lớn hơn bốn bản vá

| Tầng chạm khoá thật | Ai đóng | Lộ ra sau khi |
|---|---|---|
| lời gọi hàm (`.py`) | quét AST cả kho (phiên `4bot`) | — |
| cờ CLI — `nha --ep` không kèm `--tai-nguyen` gỡ **TẤT CẢ** | tôi đọc `main()` | AST đã "khép" |
| chuỗi gợi ý runtime (dòng 397, in **lúc bị từ chối**) | phiên `4bot` (`3eb68e12`) | CLI đã "khép" |
| **tài liệu `.md`** — khối copy-paste ở `DEVELOPMENT_WORKFLOW.md:85` | tôi (`565ef9a1`) | chuỗi đã "khép" |

🔑 **Ba lần liên tiếp, thứ đóng phạm vi là người đọc một TẦNG KHÁC, không phải
người quét kỹ hơn ở cùng tầng.** Và không phép quét nào tự nói ra rằng nó thiếu
một tầng: AST không biết có một chuỗi gợi ý; chuỗi gợi ý không biết có một tệp
`.md`.

⇒ *"Tôi đã quét kỹ hơn"* không bao giờ là bằng chứng khép phạm vi. Chỉ **liệt kê
các tầng rồi đánh dấu tầng nào CHƯA quét** mới là.

⚠️ Tầng thứ năm tôi **không** tuyên bố sạch: Scheduled Task · lịch sử shell ·
tệp untracked ở cây khác.

⭐ Và một đính chính phiên `4bot` tự nêu, đáng giữ vì nó làm bài học **mạnh
hơn**: `3eb68e12` có sửa docstring mô-đun (dòng 4) **không phải** vì họ nghĩ tới
tầng tài liệu — đó chỉ là hai chỗ trong **cùng một tệp** đang mở và `grep` chỉ
ra cả hai. Tức tầng ấy được đóng do **kề nhau**, không do suy luận về tầng. Nếu
chuỗi gợi ý đã nằm ở một tệp khác thì nó còn nguyên tới giờ.

### Một chi tiết nhỏ mà đúng: dùng lại LỜI, không diễn đạt lại

Bản vá `.md` của tôi chép nguyên câu cảnh báo từ docstring mà phiên kia vừa
sửa, thay vì tự viết. Bốn cách nói khác nhau về cùng một luật là **bốn chỗ để
chúng trôi khỏi nhau**, và không chỗ nào tự biết mình đã trôi — cùng họ với
`⚠️ Đừng gõ lại một con số nào` ở `CLAUDE.md`.

---

## P8 — `test_515`: `enroll` KHÔNG mở qua API, và nay có bằng chứng

**Hạng mục 62 · 85 → 88 (trần 90)** · `tests/test_515_ltt_voice_be_mat_api_cong_khai.py`

### Vì sao đây là việc còn với tới được

§8 xếp sáu bước; bốn bước đầu và bước 6 **chờ chủ dự án**, bước 5 (mục 13/14)
chạm `platform_core/` — ngoài phạm vi tôi tự khai và luật 20 bảo dừng lại nói
rõ. Nên tôi đi tìm thứ bảng §36 bỏ qua vì **ưu tiên thấp hơn**, chứ không phải
vì không làm được. Mục 62 là một trong số đó.

### Phát hiện: sự vắng mặt ĐÚNG, nhưng không ai ghi ra

`manifest.py` khai **hai** job type và **một** `ToolSpec`. `ltt_voice.enroll`
có đủ `_gia` (`CREDIT_GHI_DANH`), `gpu_vram_mb`, `max_runtime_s`,
`cho_tai_nguyen_s`, `SO_LAN_THU_JOB` — nhưng không có `ToolSpec`.

⛔ Trạng thái ấy đúng. Cái sai là nó **không phân biệt được với việc bỏ quên**:
một job type khai đủ tham số vận hành trông y hệt một job type sắp được mở, và
cách sửa cho hai chẩn đoán ấy **ngược nhau**.

### Bằng chứng nó CỐ Ý — đọc mã, không suy

`routes/_p_giong.py:117` ghi `VoiceConsent` **trước khi** `submit_with_credit`,
với bốn trường chỉ tồn tại ở tầng HTTP **của chính người đồng ý**:

    ip=(request.client.host ...)        <- may cua NGUOI DONG Y
    user_agent=(request.headers ...)    <- trinh duyet cua NGUOI DONG Y
    phien_ban_dieu_khoan=PHIEN_BAN_...  <- ban dieu khoan HO da doc
    ref_sha256=sha                      <- rang consent vao DUNG clip do

🔑 Một lượt `jobs:create` từ máy chủ bên tích hợp mang `ip`/`user_agent` **của
bên tích hợp**. ⇒ Mở `enroll` qua API không sinh ra *"consent yếu hơn"* — nó
sinh ra một **bản ghi consent nói SAI về người đã đồng ý**, trong khi trông vẫn
đầy đủ. Hạng lỗi **sở hữu/pháp lý**, §36 xếp trên hiệu năng và UX, và **không**
sửa được bằng cách thêm trường vào `params_schema`.

### Chốt bằng phép kiểm, không bằng chú thích

Một chú thích *"đừng mở enroll"* không ngăn được ai thêm `ToolSpec`; nó chỉ
trách người ấy **sau khi** việc đã xong.

5 test / 5 xanh, và ⭐ bài thứ tư chốt **tiền đề** chứ không chỉ chốt kết luận:
nếu ai dời việc ghi consent xuống `jobs.py` thì tiền đề đổi và mở `enroll` có
thể thành hợp lệ — bài ấy **đỏ** đúng lúc đó, tức nó **không cấm thay đổi**, nó
bắt người thay đổi quay lại đọc phán quyết.

**Đối chứng — bốn đột biến, cả bốn đỏ đúng chỗ:**

    1) them ToolSpec cho enroll   -> khong_mo  = False
    2) them job_type thu ba       -> phan_quyet = False
    3) go `ip=` khoi VoiceConsent -> consent   = False
    4) doi consent khoi route     -> consent   = False

⛔ Đột biến chạy **trong bộ nhớ**, không sửa tệp nào trong cây — một phép kiểm
sửa tạm tệp trong kho sẽ tự phá lượt gate chứa nó, và phá cả lượt phiên khác
([[chot-khong-duoc-ghi-vao-cay]]).

### Điểm tổng

Tính lại **bằng máy** từ chính bảng A: 77 dòng · 73 có số · trung bình
**86,15** (trước P8: 86,11). Số hạng mục **≥ 98 vẫn là 0** — P8 không chạm cái
đó và không được phép trông như đã chạm.

---

## P9 - `test_516`: bang `U-` la ANH CHUP, khong phai danh sach viec

**Hang muc 86 - 80 -> 92 (tran 100)** - `tests/test_516_doi_chieu_u_viral.py`

### Van de THAT rong hon thu so sach ghi

So sach cu ghi ly do tru diem la *"U-06 tu dinh chinh la PHAT HIEN SAI"*. Doc
lai ca 19 muc thi thay U-06 chi la trieu chung. Van de la bang 19 muc ay la
**anh chup 07/09 chua ai doi chieu lai voi thu da ship** - va phan lon DA XONG,
mot so do chinh chuong trinh nay lam (U-03 = P7, U-07 = P2).

=> Nguoi doc theo mat chu se **lam lai viec da xong**. Dung hang loi `CLAUDE.md`
luat 5 goi ten: *mot bang chep tay khong co cach nao tu biet no da cu*.

### Do tung muc, khong doan

    XONG               : 11   U-02,03,04,08,09,12,13,14,15,16,18
    XONG CO CHE, chan  :  3   U-01 (du lieu rong) - U-05 (B-01) - U-07 (co tat)
    MOT PHAN           :  1   U-17
    CHUA               :  3   U-10, U-11, U-19
    PHAT HIEN SAI      :  1   U-06

U-12 va U-16 la hai muc toi khong chac nen di do: `muc_dung.py` CO nguoi goi
that (`nghe_thu.py:300`), va catalog VI dem duoc 28 giong. Ca hai XONG.

### Ba nhom giua quan trong hon hai nhom ngoai

*"Co che xong, du lieu rong"* va *"ma xong, co tat"* doc ra giong **CHUA** voi
nguoi quet nhanh, nhung viec phai lam khac han: khong phai viet ma, ma la **chay
mot phep do** hoac **bat mot co**. Gop chung vao "chua" la cach mot luot soat sau
uoc luong sai cong viec con lai.

### KHONG viet lai bang goc - va do la nua kho hon

Ban kiem toan la mot tai lieu LICH SU. Sua bang cho dung la xoa mat ban ghi ve
viec luot soat ay da ket luan gi. Thu thieu khong phai mot bang dung hon, ma la
mot **moc doi chieu co ngay thang dung TRUOC no**.

`test_516::test_khoi_doi_chieu_dung_TRUOC_bang_U` chot ca **vi tri**: khoi nam
sau bang thi nguoi quet nhanh doc bang truoc, rut ra danh sach viec, roi di lam
- dung kieu hong no sinh ra de chan.

### Mot bang doi chieu cung la mot bang chep tay

Do la ly do co `test_516`. Ban va cho "bang cu noi sai" ma lai la MOT BANG NUA
thi chi doi ngay het han ra xa - va te hon, no **trong moi hon** nen dang tin
hon. Nen moi muc khai XONG phai vien dan mot thu **may kiem duoc**.

14 test / 14 xanh. Bon dot bien, ca bon do dung cho:

    1) sua 11 -> 12 o tong ket   -> tong     = False
    2) bo gach ngang U-06        -> u06      = False
    3) xoa khoi doi chieu        -> tong     = False
    4) go muc_dung.py            -> vien_dan = False

⚠️ Gioi han duoc NOI RA thay vi giau: `test_516` chot duoc chieu *"khai xong ma
da mat"*, KHONG chot duoc chieu *"khai chua ma that ra da co"* - muc CHUA khong
co gi de tro toi.

⭐ Va mot lan phep kiem bat loi cua chinh toi: lan chay dau
`test_con_so_tong_ket_KHOP_voi_bang` **do**, vi regex cua toi khong khop dong
tong ket co chu thich duoi. Bai kiem sai truoc khi bang sai - va no do that,
khong xanh-rong.

### Diem tong

Tinh lai bang may: 77 dong - 73 co so - trung binh **86,32** (P8: 86,15; ban
chot dau: 86,11). So hang muc **>= 98 VAN LA 0**.

---

## DEPLOY 10/09/2026 — và một sự cố 6 phút do CHÍNH TÔI gây ra

### Kết quả cuối

    production  c28a9b5d6cbe  build 2026-09-10T11:12:22  asset_ver 1471b271
    duong lui   3b22503cc590
    nghiem thu  lech 0 · thieu 0 · thua 0  -> DAT
    remote      c28a9b5d = local = production   (ba chieu khop)
    URL cong khai https://app.lttstudios.com/health/version -> 200, dung commit

Đi đủ quy trình `docs/16_CAP_NHAT_VA_DEPLOY.md`: §1 đồng bộ · §2 gate · §2b CVE ·
§2c a11y · §3 ff + kiểm "production thừa gì" (**0**) · §4 deploy · §5 đẩy GitHub
(sau khi `scan_source_secrets.py` ra `Findings: 0`).

### 🔴 SỰ CỐ — production xuống 6 phút, và nguyên nhân là tôi

    11:04:42  chu du an phong deploy (c28a9b5d). CHAY THAT, ADMIN=True.
    11:06:14  TOI phong lop ngoai THU HAI. UAC bat len lan nua.
    11:06:18  luot cua toi bi `deploy.lock` tu choi (dung), EXITCODE=2
    11:07:10  luot cua CHU DU AN chet giua buoc `Copy ma nguon`,
              KHONG co dong EXITCODE -> tuc bi ket thuc, khong tu thoat
    ...       ba dich vu Web/Worker/Voice nam Stopped, khong ai bat len
    11:10:58  toi bat lai bang khuon hai lop -> health 200 tro lai

**Lỗi:** tôi bắn lượt thứ hai mà **không kiểm `deploy.lock`** — nó đã nằm đó từ
11:04:42 và tôi đọc được nó bất cứ lúc nào. Khoá chặn được *lượt* của tôi, nhưng
**không chặn được cái UAC của tôi bật lên đè giữa lúc một cửa sổ deploy đang
chạy**. Tôi không chứng minh được nhân quả; thứ tự thời gian chỉ đúng vào đó, và
tôi là người tạo ra cửa sổ ấy.

⛔ Và đây là chỗ đắng: tôi đã viết *"kiểm RỒI MỚI chạy"* vào sổ này nhiều lần
trong cùng phiên, rồi bỏ qua ở **đúng lệnh nguy hiểm nhất**. Cùng hình dạng với
[[luat-viet-ra-khong-mien-nhiem-cho-nguoi-viet]].

### Vì sao thiệt hại dừng ở 6 phút

Không phải nhờ phản ứng nhanh, mà nhờ **thiết kế của người khác**:

- `deploy.lock` khiến lượt thứ hai **không** chạy song song. Hai robocopy cùng
  ghi `app\` thì mất trắng, không phải mất 6 phút.
- Lượt chết **trước** khi chép, nên `app\` vẫn nguyên bản cũ (`_p_phat_dan.py`
  KHÔNG có ⇒ chưa ghi gì). Không cần `rollback.ps1`.
- `.ket.txt` ghi `BAT DAU=` **ngay lập tức**, nên "không có tệp" phân biệt được
  với "chạy rồi hỏng" — đúng thứ `AGENTS.md` §9.3 dựng nó để làm.

### Chẩn đoán phục hồi — đo, không suy

    app\            4.412 tep, KHONG co _p_phat_dan.py  -> VAN LA BAN CU
    app.previous\   3.778 tep, nguyen
    LTTStudioWeb/Worker/Voice   Stopped
    LTTNexus                    Running

⇒ Không mất mã, không cần rollback. Chỉ thiếu **một lệnh bật dịch vụ**. Gỡ
`deploy.lock` treo sau khi **xác nhận pid 19584 đã chết** (tệp khoá ghi sẵn pid,
nên câu hỏi trả lời được thay vì đoán).

⚠️ Và một dương tính giả tôi tự tạo khi truy: lọc tiến trình bằng
`CommandLine -match 'deploy_nang_quyen|2-cai-dat'` khớp vào **chính lệnh của
tôi** — [[loc-tien-trinh-bang-chuoi-tu-khop-vao-chinh-no]], lần thứ năm.

### Điều không quan sát được từ ngoài — nói ra thay vì suy

`POST https://app.lttstudios.com/ltt-voice/phat-dan` trả **403**, không phải
404. Vì `require_login` là `Depends`, chạy **trước** thân hàm nơi cổng cờ
`LTT_VOICE_STREAM` nằm ([[cong-co-phai-dung-truoc-require-login]]).

⇒ Con số ấy **không** chứng minh cổng cờ hoạt động. Thứ chốt nó là `test_514`.
Cờ vẫn **tắt** trên production, nên `/phat-dan` chưa mở cho khách.

---

## B-04 — 20/20 giọng, và bốn lượt để tới đó

**Mục 39: 30 → 92** (trần 75 → 100) · **Mục 40: `UNKNOWN` → 80** (trần 90) ·
trung bình 74 mục có số: **86,32 → 87,07** · số mục ≥ 98 **vẫn là 0**.

    min 11,31 (Đức Trí)   max 18,49 (Thùy Dung)   chenh 1,63x
    cham hon hang so 18 : 19/20 giong
    do lap lai: hai luot doc lap cach nhau 17 phut
                lech trung binh 0,67%   lon nhat 1,90% (Quang Sơn)

⭐ Chốt tôi viết là `< 1,5 %` và nó trả **False**. Phép kiểm nói thật thay vì tôi
tự khen — con số đúng là 1,90 %.

### Tiền — và vì sao không phải sửa dòng mã nào

    n=  200  lui  12,61s   Đức Trí can  18,06s   thieu 30%   (lui du cho 6/20)
    n= 1000  lui  57,06s   Đức Trí can  90,04s   thieu 37%   (lui du cho 1/20)
    n= 5000  lui 279,28s   Đức Trí can 449,98s   thieu 38%   (lui du cho 0/20)

Chiều nguy hiểm là **giữ THIẾU**: quyết toán thu theo giây **thật** (ffprobe),
nên ước thấp hơn thật là giữ không đủ. Có dữ liệu thì `gia.giay_uoc` tự chuyển
sang đường theo giọng ⇒ lỗ đóng **mà không sửa một dòng mã nào**. Mô hình hai
tham số đặt đúng chỗ từ đầu.

### Bốn lượt, và lượt tệ nhất là lượt THÀNH CÔNG

| lượt | kết cục | nguyên nhân |
|---|---|---|
| 11:23 | chết sau 1 s | `UnicodeEncodeError` — stdout chuyển hướng ⇒ `cp1252` |
| 11:32 | từ chối | rào tự vệ của tool khớp `gate.py|pytest` theo **tên**, không theo tải |
| 11:42 | 1/20 | 19 giọng nhận 429 |
| 11:45 | **20/20** | ⛔ **rồi TÔI tự xoá mất** |
| 12:05 | **20/20** | lượt giữ lại |

⛔ Lượt 11:45 thành công trọn vẹn, rồi tôi viết một kịch bản so sánh giá **ghi
thẳng vào `ho_so_giong.json`** để đổi qua lại hai trạng thái. Nó `TypeError`
**giữa chừng**, để tệp ở trạng thái "trước"; bản thứ hai đọc đúng trạng thái
hỏng ấy làm "sau" rồi ghi đè lại. Kết quả: hai bảng giống hệt nhau, và tôi suýt
kết luận *"dữ liệu mới không đổi gì về tiền"* — **sai hoàn toàn**, rút từ hai
lần đọc cùng một tệp rỗng.

Đúng `chot-khong-duoc-ghi-vao-cay`, luật tôi **có sẵn trong memory**.

⭐ Lượt 12:05 làm khác ba chỗ: phép phân tích viết **chỉ đọc** (số học thuần,
không mutate gì), **thử trên fixture giả** trước khi lượt đo xong, và **sao lưu
ngay** khi có kết quả. Dữ liệu khớp bản sao sau **mọi** thao tác sau đó.

### Ba bản vá gốc rút ra từ các lượt hỏng

1. **`DauPhanHoi`** — `_goi` trả `dict(r.headers)` làm mất tính không-phân-biệt
   hoa/thường của HTTP. Lỗi **sống trên production**: `jobs.py` đọc `X-Gen-S`
   luôn ra `None`, bị `_so()` biến thành `0.0` im lặng ⇒ `gen_s` bằng 0 ở **mọi**
   lượt sinh và phép đối chiếu ffprobe **chưa từng chạy**.
2. **`write_text` thiếu `newline="\n"`** — ghi CRLF vào tệp mà git giữ LF.
   Hỏng ở đây đắt hơn bình thường: tệp bị ghi lại **toàn bộ** nên `git diff`
   không đọc được, và người sau không phân biệt được *"đo ra số khác"* với
   *"chỉ đổi kết dòng"*.
3. **`ra` rỗng vẫn ghi bản ghi "đã đo"** — xem mục trước.

### 🔴 Cơ chế 429 — chẩn lại, và bản sau đúng hơn

Tôi ghi *"lượt của phiên ASV đang giữ suất"*. Phiên ấy đếm `voice-err.log` và
bác lại: **11:40–11:42 gần như rỗng** — nếu họ giữ semaphore thì cổng phải bận,
không phải im.

Thứ thật sự xảy ra: `DangBanTam` mang `retry_after_s`, nên worker đưa job về
`resource_wait` và **lùi** (đo được: 20 s · 20 s · **167 s** · 20 s · 10 s).
Trong quãng lùi cổng **rảnh**, vòng lặp của tôi lấy được; job họ quay lại thì
cổng đầy.

🔑 **Với `_Cong` là semaphore một-suất-không-chờ, kết cục không do ai tham lam
mà do HÌNH DẠNG hai bên: một vòng lặp chặt luôn thắng một job biết lùi.** Càng
lùi lâu càng thua ⇒ bên lịch sự thua **có hệ thống**.

⇒ Căn cứ thiết kế cho `may_tao_tieng`: **semaphore ở tầng runtime không phân xử
được, nó chỉ từ chối.** Nó không biết ai đã chờ bao lâu nên không thể công bằng.
Khoá ở tầng trên — xin trước, không có thì **bỏ cuộc sạch** (mã 75, khuôn
`tools/giu_may_b.py`) — là thứ duy nhất biến *"ai nhanh tay"* thành *"ai tới
trước"*. ⛔ Và chốt phải chép là **hành vi bỏ cuộc**, không phải đoạn mã:
`CuaSoYen` mặc định hết giờ chờ thì **vẫn chạy**, đúng cho `cpu_nhieu` (chen chỉ
làm chậm) và **sai** cho tài nguyên một suất (chen làm hỏng **cả hai** phía).

### ⚠️ Và một đính chính cho chính tôi

Tôi ghi rằng phép đo *"sidecar CPU 0 giây/15 s"* của mình là một **ảnh chụp rơi
vào khe** giữa hai lượt gọi. Không phải: lúc ~11:44 phiên kia đang trong nhịp
lùi **167 giây**, tức họ thật sự không gọi gì. **Phép đo đúng.** Cái sai là câu
tôi rút ra từ nó — nó trả lời *"lúc này không ai gọi"*, còn tôi đọc thành
*"không ai đang cần"*. Hai câu ấy khác nhau khi đối thủ là một job biết lùi.

⇒ Ghi đúng hạng: [[pham-vi-phep-do-hep-hon-loi-tuyen-bo]], **không** phải một
phép đo hỏng. Ghi nhầm hạng thì lần sau tôi sẽ đi cải tiến phép đo — thứ vốn đã
đúng — thay vì thu hẹp lời tuyên bố.

---

## B-01 — cổng license đang chặn TẤT CẢ, và điểm đi xuống

`soat-giong` 10/09, `EXITCODE=0`, 25 dòng trên CSDL production:

    25 giong kho chung   license = cho_soat : 25/25   ok : 0   da curate : 0/25

⭐ Chiều tốt trước: đây là **bằng chứng dương** cho cổng license, không phải một
khoảng trống. `LICENSE_CHO_PHEP=("ok",)` + `_dieu_kien_kho_chung()` đang **thật
sự** chặn cả 25 giọng chưa soát, ở **cả hai** cửa đọc. ⇒ Mục **07:
`BLOCKED_DATA` → 88**, và `BLOCKED_DATA` trong bảng nay còn **0**.

⛔ Rồi chiều còn lại, và nó chạm hạng mục của chính tôi — cổng chặn *tất cả*:

| ID | Trước | Sau | Vì sao |
|---|---|---|---|
| 38 Fallback EN | 82 | **72** | P1 nối bậc hai qua cổng license — **mã đúng, 0 ứng viên chảy qua** |
| 47 VI catalog | 85 | **75** | "28 VI" đếm **có mặt**; dùng được chỉ **20** preset |
| 48 EN catalog | 85 | **60** | 17/17 EN đều `cho_soat` ⇒ **0 dùng được**, không preset nào đỡ |
| 53 Human curation | 90 | **85** | quy trình có, **0/25** đã chạy |

🔑 *"25 giọng đã nằm trong CSDL"* đúng về **CÓ MẶT**, sai về **DÙNG ĐƯỢC**. Tôi
chấm mục 38 lên 82 dựa trên vế thứ nhất; B-04 chỉ đo tốc độ nên không bao giờ lộ
vế thứ hai. Chỉ một phép đếm ở **đúng cột license** trả lời được.

⇒ Trung bình **87,07 → 86,41**. Một chương trình chấm điểm mà **mọi** phép đo
đều đẩy điểm **lên** là một chương trình đang đo sai thứ.

## 🔴 Và một phép đo HỎNG của tôi — báo sai HAI lần cho chủ dự án

Tôi kiểm cờ `LTT_VOICE_STREAM` bằng:

    (& nssm get <svc> AppEnvironmentExtra) -join "`n"  -match 'LTT_VOICE_STREAM'

và báo **hai lần** rằng cờ chưa vào dịch vụ. **Sai cả hai lần.**

`nssm get` xuất **UTF-16LE**; PowerShell đọc theo byte nên chuỗi thật là
`L\0T\0T\0_\0V\0...`. Tìm chuỗi phẳng trong đó **không bao giờ khớp được**.
Đo lại sau khi bỏ NUL:

    LTTStudioWeb / Worker / Voice   so khoa=73   co LTT_VOICE_STREAM=True

⚠️ **Vì sao tôi tin phép đo hỏng ấy:** nó cho ra `73` — một con số **hợp lý**,
khớp với số biến thật. Một phép đo hỏng trả về `0` hay ném lỗi thì tôi đã nghi;
cái này trả về một con số đúng cho **một** câu hỏi (đếm dòng có `=`) rồi tôi
dùng nó cho **câu khác** (có chứa khoá không). Cùng họ với
[[get-content-raw-doc-utf8-bang-ansi]] — bẫy mã hoá **im lặng ở vòng một**.

⛔ **Cái giá là thật:** chủ dự án đã bật cờ đúng từ đầu; tôi báo là chưa, rồi
chạy `nap_lai_env.ps1` — **khởi động lại ba dịch vụ production** — dựa trên phép
đo hỏng ấy. Không mất dữ liệu, nhưng là một lần gián đoạn không cần thiết.

🔑 Luật rút ra: **khi một phép đo trả lời "không có", hãy hỏi nó có đọc được
thứ CÓ không.** Ở đây câu đối chứng rẻ là *"liệt kê tên khoá bắt đầu bằng
`LTT_VOICE`"* — nó ra **rỗng** trong khi chắc chắn phải có `LTT_VOICE_SIDECAR_TOKEN`,
và một dòng ấy đã đủ lật toàn bộ kết luận. Tôi có đối chứng ấy trong tầm tay và
không chạy nó cho tới lượt thứ ba.

⇒ Mục **20 (Streaming) giữ nguyên 78**. Cờ nay đã bật **đo được**, nhưng trần 90
đòi E2E thật — và tôi vừa mới chấm mục 38 xuống vì đúng lỗi *"năng lực có, không
ai đi trên đường"*. Không lặp lại nó ở mục kế bên.
