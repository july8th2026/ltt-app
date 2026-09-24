# L_NGHIEM_THU — làn nghiệm thu cuối ASV

> Làn `asvf-nghiem-thu-v2`, cây `D:\LTTSTUDIOSAPP-asvf-nghiem-thu-v2`, nhánh
> `phien/asvf-nghiem-thu-v2` (tách từ `main`, đã gộp `phien/asv-final`).
> Dải test: **3000–3099**.

⚠️ Tệp này **chưa từng tồn tại** trước 24/09 — brief của làn trỏ vào nó, và làn
`nghiem-thu` trước đó (`NEN_V3`) ghi bằng chứng vào `bang_chung/NEN_V3.md` mà
không để lại tệp trạng thái. Một brief trỏ vào một tệp không có là một vòng đọc
mất trắng, nên tệp này là **nguồn trạng thái** của làn từ nay.

---

## 1. Khuôn nghiệm thu ĐO SAI SẢN PHẨM — đã sửa (24/09)

Hai khiếm khuyết làm **mọi con số thời gian** của `NEN_V3` (23/09) nói về khuôn
chứ không nói về sản phẩm. Cả hai đều hỏng **im lặng**: lượt chạy vẫn XANH, vẫn
ra tệp dùng được.

| # | hiện trạng | nơi | trạng thái |
|---|---|---|---|
| K-01 | Khuôn **không xin cấp card**: `JobContext(job.id)` không có `gpu_uuid`, còn worker thật lấy card từ `gpu_lease` (`job_runner.py:299`). Thiếu card ⇒ `ctx.has_gpu` False, `ctx.gpu_env()` không ghim `CUDA_VISIBLE_DEVICES` ⇒ demucs + ASR chạy **CPU** (đo 23/09: 72,0 s vs 42,2 s) | `test_448._chay_hang_doi` | **ĐÃ SỬA** `6e2045a1` |
| K-02 | Khoá `cpu_nhieu` bọc **cả lượt chạy**, kể cả lúc CHỜ. `NEN_V3` đo `voice_synthesis` 937/1191 s và gần hết là gọi HTTP ⇒ giữ khoá ~20 phút cho việc **chờ mạng** (sự cố 23/09: 51 phút ở CPU 6–8 %, 6 lượt xếp hàng) | khuôn scratch của làn trước | **ĐÃ SỬA** `6e2045a1` |
| K-05 | 🔧 **TỆP SẢN PHẨM** (`tach_tieng.py`): nền tảng cấp card đúng mà tiến trình con vẫn `ThieuCard` — `tach_nguon` dùng `sys.executable`, trong khuôn là trình thông dịch test (`torch cpu`, `cuda False`) | `tach_tieng.tach_nguon` | **ĐÃ SỬA** `9b8aa1b5` — `LTT_ASV_PYTHON_TACH`, mặc định `sys.executable` ⇒ 🔒 production không đổi gì |
| K-06 | Bài học hai chiều: `torch.cuda` **False** mà `ctranslate2.get_cuda_device_count()` = **1**. Một bool không nói thay chồng CUDA kia theo **cả hai** hướng | `fx.ghim_python_co_card` | **ĐÃ GHI** |

### Cách sửa

* `fx.card_cho_job(job_type, job_id)` — gọi **chính** `job_runner._vram_can` +
  `_giu_gpu` của worker thật, không gõ lại phép chọn. Nhả lease ở `finally`.
* `fx.doi_hoi_card()` — máy không có card thì **dừng**, không âm thầm chạy CPU.
* `fx.ghim_python_co_card(monkeypatch)` — ghim tiến trình con demucs vào
  venv worker, và **khai** rằng đường ASR là câu hỏi khác (K-05, K-06).
* `fx.khai_card(nhat_ky)` — báo cáo khai `pha_doi_card` / `pha_duoc_card` /
  `pha_doi_card_ma_KHONG_duoc`. ⛔ Nó **không** suy ra "ASR chạy trên GPU":
  CTranslate2 mang CUDA/cuDNN riêng, nên `torch.cuda.is_available()` True không
  chứng minh faster-whisper dùng được card.
* `fx.KhoaTheoPha(phien, giu_suot=...)` — ba hành vi, ba lý do:

  | khoá | phạm vi | vì sao |
  |---|---|---|
  | `cpu_nhieu` | quanh **một** job nặng, nhả ngay | chia **sức tính** ⇒ giữ lúc chờ là phí máy |
  | `may_tao_tieng` | từ job giọng đầu tiên đến hết lượt | tài nguyên **độc quyền** ⇒ ai chen vào làm **hỏng phép đo** |
  | `postgres_test` | cả lượt, **trước** `moi_truong` | `moi_truong` gọi `drop_all` trên CSDL scratch dùng chung (sự cố 17/09) |
  | pha chờ | **không khoá gì** | `advance`/`edit_plan`/`content_process`/`qc_ai`/`voice_synthesis` là gọi mạng |

### Chốt bằng phép kiểm, không bằng lời

`tests/test_3000_asv_khuon_nghiem_thu_card_va_khoa.py` — 12 bài, chạy mọi lượt
gate (không cần card thật, không chạm khoá thật).

**Đối chứng đã chạy**: tiêm lại đúng ba hành vi cũ (`card_cho_job` trả rỗng ·
khoá bọc mọi pha · `sleep` trong khối giữ khoá) ⇒ **6/12 bài đỏ**. Một phép đo
không có đối chứng thì số 0 của nó không phải phát hiện.

⚠️ Brief của làn ghi khuôn ở `tests/fixtures/asv_e2e.py` và ghi API là
`ctx.co_gpu`/`ctx.env_for()`. Cả hai **lệch**: `JobContext` được dựng ở
`tests/test_448_asv_v4_e2e_nghiem_thu.py:_chay_hang_doi`, và API thật là
`ctx.has_gpu`/`ctx.gpu_env()`. Phần dùng lại được (`card_cho_job`, `KhoaTheoPha`)
đặt trong fixture; chỗ nối đặt trong `test_448`.

---

## 2. Năm lượt nghiệm thu — định nghĩa

⚠️ `PLAN.md` chỉ nói *"lượt thật cuối A/B/C/D"* mà **không định nghĩa**. A/B/C
suy ra được từ `bang_chung/NEN_V3.md`; **D chưa từng được định nghĩa ở đâu**.
Làn này chốt nó là ô còn lại của bảng `preset × chế_độ_giọng`, và
`tests/test_3001` có một phép đếm tập hợp chốt rằng bốn ô đều được phủ — chứ
không phải một câu trong tài liệu.

| lượt | preset | chế độ giọng | cặp | câu hỏi lượt này trả lời |
|---|---|---|---|---|
| A | giữ hình | AUTO_MATCH | zh→vi | R-01: AUTO_MATCH còn là đường chết? |
| B | giữ hình | USER_SELECTED | zh→vi | đường sản phẩm chính (mốc so với `NEN_V3`) |
| C | cắt thông minh | USER_SELECTED | zh→vi | R-05: `smart_localize` CÓ cắt không? |
| D | cắt thông minh | AUTO_MATCH | zh→vi | giao của R-01 và R-05 — ⚠️ **định nghĩa do làn này tự chốt 24/09** |
| E | giữ hình | USER_SELECTED | **vi→en** | chiều ngược — cặp `→ en` có phải đường sống? |

Phim: `v3` (`深度解析…`, 106,833 s, hardsub Trung) — cùng phim `NEN_V3` đã chạy,
nên hai báo cáo so sánh được với nhau.

`LTT_ASV_QC_AI` **BẬT** (R-07: tắt thì không đo lớp ngữ nghĩa/thị giác; bộ test
tự `assert` lại điều đó).

### Nguồn của từng định nghĩa — cột bắt buộc, không phải chú thích

Mỗi lượt trong `test_3001._bang_luot()` mang một trường `nguon_dinh_nghia`, và
nó **đi theo bản ghi bằng chứng** (`nguon_dinh_nghia_luot` trong JSON từng lượt):

| lượt | đến từ đâu |
|---|---|
| A · B · C | `bang_chung/NEN_V3.md` (23/09) — đã chạy thật |
| **D** | ⛔ **làn `nghiem-thu-v2` TỰ CHỐT 24/09.** `PLAN.md` chỉ ghi *"lượt thật cuối A/B/C/D"*, D không có ở đâu. Điều phối tán thành cùng ngày, kèm đúng điều kiện: bản ghi phải nói rõ đây là lựa chọn của làn |
| E | `PLAN.md` 22/09 (hợp đồng: đích ∈ {vi, en}) + brief làn |

🔑 Vì sao cột này có ở **cả năm** chứ không chỉ ở D: nếu chỉ D có, nó đọc như một
lời biện bạch cho một ô lẻ. Có đủ năm thì nó là một mục truy nguyên, và người đọc
thấy ngay bốn ô kia dựa vào đâu. `test_3001::test_MOI_luot_khai_NGUON_DINH_NGHIA`
chốt cả hai chiều — thiếu nguồn là đỏ, và D mà không nói *"TỰ CHỐT"* cũng đỏ.

### Cổng tác

```
powershell -ExecutionPolicy Bypass -File setup\nghiem_thu_asv.ps1 `
  -NghiemThuCuoi -QcAi -RaLuot <thư mục> -Phim <đường dẫn> [-Luot A,B]
```

⛔ **KHÔNG bọc lệnh này trong `chay_nang.py`.** Đó chính là khiếm khuyết K-02:
`chay_nang.py` giữ `cpu_nhieu` suốt cả lượt, kể cả ~15 phút chờ máy B và sidecar.
Khuôn tự giữ khoá **theo pha** (mục 1), mịn hơn — nên bọc thêm một lớp thô ở
ngoài là xoá đúng cái vừa sửa.

---

## 2b. Quan sát vận hành 24/09 — vòng sửa `dich_sai` CHẠY THẬT, và nó xác nhận luật khoá

Lượt B, phút thứ ~50, đọc từ `asv_stage` của CSDL test trong lúc lượt còn chạy:

```
media_prepare  audio_prepare  transcribe  edit_plan   succeeded  thu=1 rev=3
content_process                                       succeeded  thu=2 rev=6
voice_synthesis                                        RUNNING   thu=2 rev=6
timing_align compose render qc qc_do_luong qc_ai       pending    thu=1 rev=4
qc_ai (lượt đầu)                                       done
```

`qc_ai` chấm một bản dịch là sai ⇒ `sua_chua` (`dich_sai`) ⇒ `content_process`
chạy lại (lần 2) ⇒ `voice_synthesis` **đọc lại** (lần 2) ⇒ mọi giai đoạn sau về
`pending` để chạy lại. **Đây là vòng sửa `dich_sai` chạy đầu-cuối trên phim khách
thật** — đúng cái M-09a ghi là *"chưa ai có phép kiểm đầu-cuối cho nó"*.

⭐ **Và nó biến một lập luận thành một quan sát.** Tôi ghi lý do giữ
`may_tao_tieng` qua các pha QC *trước* khi thấy chuyện này: phán quyết QC có thể
đẩy lần chạy ngược về `voice_synthesis`. Nó **đã** đẩy. Nếu khuôn nhả máy sinh
tiếng lúc `voice_synthesis` báo `succeeded` lần đầu, một phiên khác giành được
máy, và vòng sửa "đọc lại" này đo trên một máy đang mang trạng thái của lượt khác
— đúng bẫy M-07, không còn là giả thuyết.

⛔ Khác biệt thật giữa hai khoá, nói lại vì nó dễ bị gom thành một:

| | nhả rồi giành lại |
|---|---|
| `cpu_nhieu` | chỉ **chậm hơn** |
| `may_tao_tieng` · `postgres_test` | có thể **sai kết quả** |

## 2c. Luật 7 (kiểm giao diện) — đóng tới đâu, còn hở đâu

| lớp | phủ bởi | trạng thái |
|---|---|---|
| dữ liệu tới được màn hình | `test_3002` (`TestClient`, render thật qua HTTP) | ✅ |
| **đọc được trên màn hình** (CSS, khối mở sẵn, không lỗi console, không asset 404) | `test_3003` (**Chromium thật** + uvicorn cục bộ, đăng nhập bằng cookie) | ✅ |
| chốt trên `https://app.lttstudios.com` qua Cloudflare | — | ⛔ **CÒN HỞ** |

⚠️ Lớp cuối **không** chờ P-01: năm bảng `asv_*` đã có trên production; ASV 404 là
do **cờ tính năng** `LTT_AUTO_SCAN_VIDEO`, và bật cờ đó **là mở cho khách** —
§24 của đề bài cấm. ⇒ Việc còn mở đúng là *"chốt trên tên miền thật — **chờ chủ
dự án cho mở khách**"*, không phải *"chờ bảng"*.

## 2d. ⭐ ĐỔI HƯỚNG (chủ dự án, 24/09) — thang ĐO TỪNG BƯỚC thay cho lượt đầy-chuỗi

⛔ **Dừng sau lượt C. KHÔNG chạy D và E.**

### Vì sao đổi — và lý do khớp với chính dữ liệu làn này đo được

Một lượt đầy-chuỗi mất **67 phút** và trả về một mớ lỗi ở **nhiều tầng cùng lúc**;
nó **không** nói được mắt xích nào là gốc:

| lượt | kết quả | nó chứng minh được gì |
|---|---|---|
| A | `error` ở `content_process` | một **tiền đề chưa khai** (N-06) |
| B | `done` | *"chuỗi chạy được"* — kèm **85** khiếm khuyết còn lại (N-01) |

Cả hai đều là *"chuỗi chạy được"* mà **không** là *"từng bước đúng"*. Một phép đo
đầu-cuối trả lời câu *"có ra tệp không"*; nó không trả lời *"bước nào sai"*.

### Hướng mới

Siết **từng mắt xích một**, theo thứ tự, và mỗi bước phải **thật sự đạt** rồi mới
sang bước sau. Trước khi đo mỗi bước: soát mã vận hành của bước đó (tối ưu chưa,
logic kín chưa) và **tra cộng đồng GitHub** xem có phương án tốt hơn (hợp đồng §1b,
`CLAUDE.md` luật 10). Khi mọi bước đã đạt thì chạy thông cả hệ là xong.

### Cái gì của làn này dùng lại — và hai thứ quý nhất

| dùng lại | vì sao nó cần cho thang mới |
|---|---|
| `fx.card_cho_job` + `fx.ghim_python_co_card` | ⭐ mỗi bench đo **SẢN PHẨM**, không đo khuôn (K-01, K-05) |
| `fx.KhoaTheoPha` | ⭐ chạy bench liên tục mà **không chặn cả máy** (K-02) |
| `fx.khai_card`, `fx.bang_vong_sua` | phán quyết thay cho hai danh sách |
| `_ten_an_toan`, khối đo bọc `try` | một lỗi trong mã đo không xoá kết quả |

### Việc phải làm, thứ tự

1. **Tách khuôn thành từng bước gọi riêng được** — chạy **một** giai đoạn trên một
   tệp đầu vào có sẵn. ⛔ Hiện muốn đo `transcribe` phải đi qua `media_prepare` +
   `audio_prepare` trước: **3 phút để đo một bước 20 giây**.
2. **Hợp đồng vào/ra của mỗi bước**, để về sau xen bước mới vào giữa mà không phải
   sửa các bước khác. ⛔ Ghi cái **thấy trong mã**, **không** thiết kế lại — bản đồ
   thật trước, kể cả chỗ nó xấu.
3. **Bước đầu tiên: `transcribe`** (văn bản nguồn). Mọi thứ sau nó đứng trên nó.

### Hoãn CÓ CHỦ Ý — không phải bỏ quên

* **N-06** (AUTO_MATCH đòi nguồn có tiếng nói) → trả lời ở **bước hồ sơ giọng**.
* **N-07** (`so_canh = 1`) → trả lời ở **bước cắt cảnh**.

⛔ Và **giữ nguyên** mọi bằng chứng đã có: `NT_CUOI_A.md`, `NT_CUOI_B.md`, bảng bốn
dòng, N-01…N-07. Lượt B vẫn là **bằng chứng đầu-cuối đầu tiên** của vòng sửa, và
N-01 vẫn là lỗi **chặn mở khách**.

## 3. Kết quả lượt thật

Bằng chứng từng lượt: `bang_chung/NT_CUOI_<lượt>.md`.

| lượt | trạng thái | card được cấp | tệp ra | QC |
|---|---|---|---|---|
| A | (đang chạy) | | | |
| B | (đang chạy) | | | |
| C | (chưa) | | | |
| D | (chưa) | | | |
| E | (chưa) | | | |

---

## 4. Việc còn mở của làn

* `docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json` còn là bản 23/09
  ⇒ `test_448::test_moi_luot_di_HET_chuoi_giai_doan` và
  `::test_phien_ban_ENGINE_trong_bao_cao_van_dung_HOM_NAY` **đỏ** (F-07).
  Phải **sinh lại từ lượt thật**, ⛔ không sửa phép kiểm cho khớp số cũ.
* **Số test trùng, không phải của làn này**: `test_2140_asv_do_gioi_hop_dong.py`
  (asv-final) và `test_2140_loi_job_cho_khach.py` (`main`) cùng số 2140 ⇒
  `tools/check_so_test.py` FAIL. Có sẵn trên `phien/asv-final` trước khi làn này
  tách. Điều phối xử: một trong hai phải đổi tên.
