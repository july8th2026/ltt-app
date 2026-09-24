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
