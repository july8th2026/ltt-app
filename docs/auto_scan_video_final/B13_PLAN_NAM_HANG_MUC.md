# B13 — Năm hạng mục từ bản `T1a-bis`, đo xong, plan triển khai

**Ngày:** 2026-09-28 · **Lượt đo:** `asvr_47327a869a8f4597960048f09064740`
(`T1a-bis_sau-B9_9truc_20260928-0538.mp4`, 198 s, nguồn 275,0 s)

⛔ **Chưa chạy phép nặng nào.** Mọi con số dưới đây đọc từ CSDL + artifact của
lượt đã chạy, và từ mã nguồn. Chủ dự án đang phân tích video và đã dặn không
chạy thử nghiệm.

---

## 0. Bảng phán quyết — ai thật sự gây ra cái gì

| # | Chủ dự án thấy | Thủ phạm THẬT (đã đo) | Nơi sửa |
|---|---|---|---|
| 1 | 42–66 s không có tiếng | **ASR bỏ trống nguồn 65,17→97,66 s (32,5 s)** | `whisperx_runner` + một CỬA đọc `phu_song` |
| 2 | cắt video quá nhiều | **`settings["cat"]=[0.05,0.95]` của JOB TEST** — máy cắt cảnh cắt **0 giây** | job test + một báo cáo ở `image_finish` |
| 3 | một số câu tăng tốc quá | **`ket_luan()` nhận `khe=ket−bat`**, ⛔ không nhận `ngan_sach` | `giai_doan_giong.py`, 3 chỗ gọi |
| 5 | bật lại OCR đọc chữ tham chiếu | đã có `do_vung_ocr` (B10-4) nhưng **det-only, ⛔ không đọc chữ** | `do_vung_ocr` + khuôn `dai_sub_rapid` |
| — | *(mới 28/09)* clip bị crop time | **cùng thủ phạm hạng mục 2** | đặt `cat=None` cho lượt test |

⭐ **Hai trong năm hạng mục KHÔNG phải lỗi ở nơi nó biểu hiện.** Cắt thì máy
cắt cảnh vô tội; tăng tốc thì bậc thang nắn tính đúng công thức của nó nhưng
được hỏi **sai câu**.

---

## 1. Hạng mục 1 — mất tiếng 42–66 s

### 1.1 Đo: mất ở chặng ĐẦU TIÊN

```
ASR (whisperx 3.8.6, large-v3): 78 đoạn · phu_song 211,56 / 275,04 = 76,9 %

LỖ HỔNG > 2 s trong bản chép:  8 chỗ
   nguồn  65,17 ->  97,66  (32,5 s)   xem 41,1 -> 67,1   ⇐ ĐÚNG khoảng chủ dự án nêu
   nguồn  26,99 ->  34,35  ( 7,4 s)   xem 10,6 -> 16,5
   nguồn 168,47 -> 173,69  ( 5,2 s)   xem 123,8 -> 128,0
   nguồn 130,56 -> 135,62  ( 5,1 s)   xem  93,4 ->  97,5
   (còn 4 chỗ 2,1–4,3 s)
```

⇒ ⛔ Không phải dịch mất, ⛔ không phải TTS mất, ⛔ không phải cắt.
`content_process` giữ đủ **78/78**; `timing_align.so_doan_bi_cat = 0`.

### 1.2 🔴 Đoạn duy nhất ở mép lỗ hổng là LỜI NHẮC CỦA CHÍNH TA

```
initial_prompt ta truyền   : 以下是中文普通话句子。
seg_0024 (64,27..65,17)    : 中文普通话句子          <- 7 ký tự, là KHÚC GIỮA của prompt
so_doan_nghi_ao_giac       : 0
```

`ban_ghi.nghi_ao_giac` đòi **hai** tín hiệu cùng đồng ý: `0 mốc từ` **và**
`cps > 30`. Đoạn này có mốc từ (nhánh `aligned`) và `7 / 0,90 = 7,8 cps`
⇒ **không tín hiệu nào chạm**, ⛔ theo đúng thiết kế.

⭐ Tín hiệu thứ ba **rẻ, cấu trúc, ⛔ không phải danh sách đen**: văn bản đoạn
là **khúc con của `initial_prompt` ta vừa truyền vào**. Đây là kiểu hỏng đã biết
của `initial_prompt` (Whisper nhả lại prompt trên khối ít tiếng) — cùng họ issue
`whisperX #645` mà ta lấy prompt từ đó. Ta **biết chuỗi ấy** vì ta gõ nó ⇒ so
khớp là một phép **đối chiếu đầu vào**, ⛔ không phải đoán nội dung.

### 1.3 ⚠️ Nguyên nhân của hố VAD: CÒN HAI KHẢ NĂNG, chưa tách được

`whisperx_runner.py:88` gọi `load_model(...)` mà ⛔ **không truyền `vad_options`
lẫn `asr_options`**. Mặc định của gói đã cài (`whisperx/asr.py:410,434`):

```
vad_onset = 0,500   vad_offset = 0,363   no_speech_threshold = 0,6
```

| khả năng | ai bỏ đoạn | phân biệt bằng |
|---|---|---|
| (A) pyannote VAD coi 65–98 s là **không tiếng** | tầng VAD | dump khoảng VAD, ⛔ không giải mã whisper |
| (B) VAD cho qua, `no_speech_threshold=0,6` loại khối | tầng whisper | cùng lượt dump đó |

⛔ **Chưa đo được cái nào — và tôi ⛔ không đoán.** Một lượt chạy pyannote VAD
**một mình** (⛔ không decode) trên tệp này là ~10 s GPU và tách hẳn hai khả năng.
Đó là việc **đầu tiên** của hạng mục này, và nó ⛔ không được bỏ qua: hai khả
năng dẫn tới hai cần gạt **khác nhau** (`vad_onset` so với `no_speech_threshold`),
và vặn sai cần gạt thì kết quả ⛔ không đổi một ký tự.

### 1.4 🔑 Và ta ĐÃ ĐO đại lượng đúng rồi — ⛔ không ai đọc nó

`phu_song = 211,56` nằm trong `transcribe.outputs` của **mọi** lượt chạy.
`76,9 %` là một con số **đủ để báo động** và nó ngồi im trong JSON.

⇒ Thuốc ⛔ không phải "đo thêm", mà là **một CỬA đọc con số đã có**:

```
CỬA A (tổng)   phu_song / thoi_luong < NGUONG            ⇒ cảnh báo vận hành
CỬA B (cục bộ) một lỗ hổng ĐƠN LẺ > NGUONG_HO giây
               nằm trong cửa sổ GIỮ                       ⇒ cảnh báo
```

⚠️ **Phải có CẢ HAI.** Một tổng 90 % vẫn có thể chứa một hố 30 giây; và một phim
thật sự ít lời thì tổng thấp mà ⛔ không có hố nào. Đây đúng họ *"mọi cần gạt đo
riêng, tổng chưa ai đo"* — lần này ngược: **tổng CÓ đo, cục bộ chưa ai đo.**

---

## 2. Hạng mục 2 — "cắt quá nhiều" · máy cắt cảnh VÔ TỘI

### 2.1 Đo

```
edit_plan   : so_canh_da_doc 127 · so_canh_hong 0 · so_cat 0 · ti_le_giu 1,0
image_finish: ke_cat.cat = []  · giay_cat 0 · ti_le_cat 0,0
              cua_so_khach = [0.05, 0.95]
              khoang_giu   = [[13,7504 , 261,2579]]
              thoi_luong_vao 275,008  ->  thoi_luong_ra 247,508
```

⇒ 27,5 giây biến mất là **5 % đầu + 5 % cuối**, ⛔ không một giây nào do phân
tích cảnh.

### 2.2 Cái giá, đếm bằng lời thoại

```
🔴 MẤT HẲN 6 đoạn:
   seg_0001   0,11..  2,63  "Đây là game thật, bạn nam không bỏ."
   seg_0002   2,63..  6,40  "Chia làm hai đội, ba bóng trên đầu là máu."
   seg_0003   6,40.. 11,28  "Rơi xuống bản đồ, tìm vũ khí, nổ bóng đối phương."
   seg_0076 262,24..263,04  "Cuối cùng,"
   seg_0077 263,04..273,84  "Đội đỏ y tá quyết tâm đánh đôi,"
   seg_0078 273,84..275,04  "Nhận quà lớn."
⚠️ MẤT MỘT PHẦN 1 đoạn: seg_0004  11,28..15,46
```

⇒ Mất **đúng phần giải thích luật chơi** và **đúng phần kết** — nên bản giao mất
mạch, đúng như chủ dự án nghe thấy. Và vì trục thời gian bị crop hai đầu, nó ⛔
**không còn đối chiếu được với video gốc** (chủ dự án nêu 28/09).

### 2.3 `cua_so_khach` là THIẾT KẾ, ⛔ không phải lỗi

`giai_doan_hinh_anh._cua_so_khach` đọc `cai_dat.doc(run).cat`, tức
`settings["cat"]` — **do người tạo job đặt**. Docstring của nó khai rõ vì sao nó
CỐ Ý nằm ngoài trần 5 %:

> *"Cửa sổ này ⛔ không phải một phán đoán — nó là khách tự kéo hai tay cầm và tự
> thấy kết quả."*

⇒ `[0.05, 0.95]` là **một tham số của job test tôi tạo**, ⛔ không phải mặc định
sản phẩm. ⭐ Máy cắt cảnh **đã có** đúng lá chắn chủ dự án mô tả, và nó là **luật
cứng**: `ke_cat.co_thoai` (*"CHỈ cắt vùng KHÔNG có lời thoại"*), đọc thoại từ
**tiếng Việt ĐÃ SINH** — ⛔ không từ bản chép nguồn, và `ke_cat.py:22` giải thích
vì sao đó mới là trục đúng.

### 2.4 Việc phải làm

| việc | loại |
|---|---|
| **2a** lượt test kế (`T1a-ter`) đặt `cat = None` | tham số, 0 dòng mã |
| **2b** `image_finish` báo *"cửa sổ khách đã xoá N đoạn thoại"* — CẢNH BÁO, ⛔ không chặn | mã, nhỏ |
| **2c** "bỏ đuôi cảnh xấu (rung, chuyển cảnh lỗi)" — **yêu cầu sản phẩm MỚI** | mã, vừa |

⚠️ **2c là việc `ke_cat.py:87` nói phải HỎI chủ dự án** — và chủ dự án **đã yêu
cầu** nó trong tin 28/09, nên nó được phép. Nhưng ghi rõ: trần
`TRAN_CAT_TI_LE = 0,05` chủ dự án **đã chốt GIỮ** ngày 25/09 sau khi biết cái
giá. 2c ⛔ **không được** nới trần đó; nó chỉ làm `diem_kem` **nhắm đúng hơn**
trong cùng ngân sách.

Tín hiệu mượn được từ `C:\Cut_only ver2` (`nerf_engine/stages/`):

```
motion.py     : điểm động = mean(absdiff) hai khung xám 320x180, lấy mẫu 5 fps
scene_detect  : PySceneDetect ContentDetector — TA ĐÃ DÙNG (canh.py, ngưỡng 35)
select.py     : ⭐ chunk CHỒNG NHAU trong cảnh + union_duration
```

⭐ `select.py` ghi sẵn bẫy của chính nó, và nó **áp cho ta**:

> *"Fixes the common bug: counting overlapping chunks twice, which makes the
> selector stop early."*

⇒ Khi 2c sinh nhiều ứng viên trong **cùng một cảnh**, `ke_cat` phải đo `giay_cat`
bằng **hợp** các khoảng, ⛔ không bằng tổng — nếu không trần 5 % sẽ đóng sớm và
báo `dung_o_tran` sai. Đây đúng họ *"sai mẫu số"*.

🔴 **`motion.py` mở một hố CPU mới.** `cv2` mặc định lấy **hết lõi** — đúng lớp
lỗi B12 (RapidOCR) và 03/09 (demucs). Cần gạt là `cv2.setNumThreads(N)`, và nó
phải **đo** chứ ⛔ không tin (B12 §3: `OMP_NUM_THREADS` mang đúng tên mà ⛔ không
nối vào đâu cả).

---

## 3. Hạng mục 3 — tăng tốc quá trong khi khoảng lặng còn trống

### 3.1 Đo — 2 trong 4 đoạn bị nén oan

| đoạn | tiếng TTS | `khe` = `ket−bat` | ngân sách thật | **lặng chưa dùng** | hệ số áp |
|---|---|---|---|---|---|
| `seg_0007` | 2,40 s | 2,10 | 9,46 | **7,36 s** | 1,1418 |
| `seg_0011` | 2,32 | 1,98 | 1,98 | 0,00 | 1,1711 |
| `seg_0024` | 1,20 | 0,90 | 33,39 | **32,49 s** | **1,3333** |
| `seg_0031` | 2,08 | 1,82 | 1,82 | 0,00 | 1,1422 |

`seg_0011` và `seg_0031` tăng tốc là **ĐÚNG** — lặng bằng 0, ⛔ không có chỗ nào
khác. `seg_0007` và `seg_0024` là **oan**.

🔑 Và `32,49 s` "lặng" của `seg_0024` **CHÍNH LÀ hố VAD của hạng mục 1** — nó là
đoạn ảo giác `中文普通话句子` bị ép nhanh **33 %** để vừa một khe 0,90 s, trong khi
32 giây sau nó trống không.

### 3.2 Thủ phạm: một giá trị dán nhãn "BÁO CÁO" lại được THI HÀNH

`giai_doan_giong.py:474-482` dựng **hai** con số và chú thích rất rõ:

```
khe       = ket - bat              -> dùng để BÁO CÁO
ngan_sach = khe + lặng mượn được   -> dùng cho CỬA TIÊU TIỀN
```

Nhưng cả **ba** chỗ gọi `ket_luan(...)` (dòng 495, 558, 727) truyền `khe=khe`,
và `ket_luan` → `co_gian_du_khong(giay, khe)` → `he_so = giay / khe`.
`giai_doan_thoi_gian._dung_ban_phoi` rồi **áp đúng con số đó làm `atempo` thật**.

⇒ Bản vá 26/09 (`thoi_gian.ngan_sach_nan_s`) sửa **cửa tiêu tiền**
(`nen_viet_lai` — có gọi LLM hay không) và ⛔ **KHÔNG** sửa cửa **thi hành**.
Đây họ *"số đúng nhưng gán cho SAI BƯỚC"*: mẫu số `khe` đúng cho câu *"đoạn này
có vừa khe của nó không"*, và sai cho câu *"phải nén bao nhiêu"*.

### 3.3 🔴 Trần 1,15 KHÔNG chặn gì, và báo cáo in hai đại lượng cạnh nhau

```
timing_align.he_so_toc_lon_nhat = 1,15    so_doan_tang_toc = 12          <- KẾ HOẠCH
timing_align.master.he_so_toc_da_ap: n=69, max = 1,3333, khác 1 = 4      <- THỰC ÁP
```

Hai dòng cạnh nhau trong cùng một `outputs`, **hai tập khác nhau**, và
`1,15 < 1,3333`. Ai đọc báo cáo sẽ kết luận trần đã giữ.

`giai_doan_thoi_gian.py:328` khai: trần thiết kế là **CẢNH BÁO**, chủ dự án chốt
26/09; trần duy nhất còn cưỡng chế là `TRAN_KY_THUAT_ATEMPO = 2,0`. ⭐ Quyết định
ấy **đúng** — nhưng nó được chốt khi mẫu số là `khe`. Sửa mẫu số thành
`ngan_sach` thì phần lớn ca vượt trần **tự biến mất**, và câu hỏi "kẹp hay không"
mất phần lớn sức nặng.

### 3.4 ⚠️ Hai máy tăng tốc ĐỘC LẬP — lượt này chúng rời nhau do MAY

```
compose.so_lop_tang_toc = 12      <- ban_ke.he_so_toc,   trần 1,15, kẹp thật
timing_align            =  4      <- he_so_co_gian,      trần 2,0
tập đoạn: {0012,0013,0019,0020,0032,...}  so  {0007,0011,0024,0031}  -> RỜI NHAU
```

⛔ Không gì bảo đảm chúng rời nhau. Một đoạn nằm trong **cả hai** sẽ bị
`1,15 × 1,3333 = 1,53`. Phải có **một bất biến** chặn chuyện đó, ⛔ không phải
một lời hứa.

### 3.5 Việc phải làm

| việc | nội dung |
|---|---|
| **3a** `ket_luan` nhận `ngan_sach` làm mẫu số của `he_so_co_gian`; `khe` **ở lại** cho báo cáo | ⛔ Đừng sửa `khe_cua` — nó trả lời đúng câu của nó, `ngan_sach_nan_s` đã viết ra lời ấy |
| **3b** một bất biến: tổng hệ số áp lên MỘT `ma` (compose × timing) ⛔ không vượt trần | chặn §3.4 |
| **3c** `tom_tat` in **cùng một** đại lượng, hoặc gọi hai tên khác nhau | chặn §3.3 |
| **3d** thứ tự cứu: lặng → dàn trong đoạn → tăng tốc (cuối cùng) | `TY_LE_MUON_KHOANG_LANG = 0,7` đã là bước 1 |

---

## 4. Hạng mục 5 — bật lại OCR đọc chữ tham chiếu

`do_vung_ocr` (B10-4) chạy RapidOCR **det-only** (`use_rec=False`) vì chủ dự án
chốt 27/09 *"không sử dụng text để đối chiếu"*. Tin 28/09 đảo lại: bật đọc chữ,
**theo cách `D:\Viral` làm**.

`D:\Viral\...\dai_sub_rapid.py:1525` chia đoạn bằng **ba** tín hiệu:

```
ngắt khi   gap > HOLD   HOẶC   dy > MOVE_Y   HOẶC   CHỮ ĐỔI
hộp = hợp các hộp trong một đoạn, nới _M nhưng KẸP ở trung điểm hai đoạn kề
```

⇒ Tín hiệu **"chữ đổi"** là thứ `det-only` ⛔ không thể có. Đó chính là lý do
B10-2 (che động theo đoạn) hiện chia đoạn thô hơn bản tham chiếu.

| việc | nội dung |
|---|---|
| **5a** bật `use_rec` ở tầng OCR, dùng chữ **chỉ** để phát hiện ĐỔI ĐOẠN | ⛔ không dùng chữ làm nội dung, ⛔ không dịch từ nó |
| **5b** đo lại giá CPU: `use_rec=True` nạp thêm một model | ⭐ `CPU_TRAN_LOI = 6` phải bọc **cả** rec, ⛔ không chỉ det |
| **5c** đo lại số đoạn che trên chính phim này (B10-2 đo 4 đoạn với det-only) | 🔑 con số phải kèm SHA + môi trường |

---

## 5. ⭐ Hạng mục 6 (mới, chủ dự án hỏi 28/09) — chạy dây chuyền KHÔNG deploy

### 5.1 Hai mảnh ĐÃ CÓ trong kho — ⛔ không phải xây mới

```
tools/asv_chay_worker_that.py  lenh_worker():
    nap_env()                      <- C:\LTTPlatform\secrets\app.env   (khoá THẬT)
    os.chdir(GOC)                  <- GOC = D:\LTTSTUDIOSAPP   ⭐ CÂY LÀM VIỆC
    run_forever(wid, capabilities=NANG_LUC)

apps/auto_scan_video/thi_hanh.py:436   chay_giai_doan(ten, params, ctx=None)
    docstring: "một lời gọi TRỰC TIẾP ngoài hàng đợi (script, test)"
```

⇒ **Khoá voice, khoá LLM, GPU, R2, CSDL đều dùng được từ cây làm việc mà ⛔ không
deploy.** Cái thiếu ⛔ không phải một môi trường giả lập — là một **người lái**.

### 5.2 Vì sao đường `worker` một mình chưa đủ

Dịch vụ production **cũng** khai năng lực ASV (`LTT_WORKER_POOLS = "api:6,
gpu+ffmpeg:1, voice:1"`) ⇒ nó **tranh** job với worker của ta, và phần lớn giai
đoạn sẽ chạy bằng mã **đã deploy** — tức đúng thứ ta muốn tránh. ⛔ Không được
tắt dịch vụ production: máy này phục vụ thật.

### 5.3 Đề xuất: `tools/asv_chay_tai_cho.py` — gọi TRỰC TIẾP, ⛔ không qua hàng đợi

```
nap_env()                                   khoá thật
tạo run   (dùng lại `_tao` của asv_chay_worker_that)
thuê MỘT lease GPU thật (platform_core.gpu_lease)
for g in pipeline.CHUOI:
    thi_hanh.chay_giai_doan(g.ten, {...}, ctx=<ctx tối thiểu>)
```

| được | ⛔ mất |
|---|---|
| mã của **cây làm việc**, ⛔ không deploy | ⛔ không tái hiện PATH của `LocalSystem` |
| ⛔ không tranh job với dịch vụ production | ⛔ không tái hiện nhảy lan (api/gpu/voice) |
| MỘT tiến trình ⇒ bọc `cua_so_yen` đúng một lần | `job_events` mù (`ctx=None` — `thi_hanh` khai rõ) |
| traceback về console, ⛔ không chìm vào log dịch vụ | |

🔴 **Nên nó là VÒNG TRONG nhanh, ⛔ KHÔNG phải bản thay thế nghiệm thu.** Đúng
luật đã ghi sổ: *"con số cổng phải kèm SHA và MÔI TRƯỜNG"* — một phép đo ở phiên
người dùng ⛔ không nói hộ `LocalSystem` (sự cố 23/09: worker thiếu `ffmpeg` trên
PATH, chỉ lộ khi chạy dưới SYSTEM). Lượt **chốt** vẫn phải là
`asv_chay_worker_that` trên worker thật, sau deploy.

⇒ Nhịp mới: **sửa → `asv_chay_tai_cho` (phút) → lặp**; và **một** lượt
`deploy + worker thật` ở cuối để chốt.

⛔ **Không giả lập LLM/TTS.** Chủ dự án muốn *"giữ được code vận hành chuẩn
xác"*, và một bộ giả lập sẽ là đúng cái bẫy đã ghi sổ hai lần: *"fixture tự dựng
tiền đề mà sản phẩm KHÔNG có"* (9 test xanh + nghiệm thu PASS + 404 trên
production) và *"phép kiểm XANH trên thứ ĐÃ HỎNG"*. Ta ⛔ không giả lập thứ gì —
ta chỉ **bỏ hàng đợi**.

---

## 6. Hạng mục 7 — rà nghẽn CPU/GPU cho ĐÚNG các việc trên

B12 đã vá lớp 1 (`CPU_TRAN_LOI = 6` + `chan_loi()`, đã đo 684 % = 6,8 lõi).
Còn nợ, và **plan này thêm hai hộ tiêu thụ mới**:

| # | hộ tiêu thụ | trạng thái |
|---|---|---|
| 1 | RapidOCR **det** | ✅ đã chặn (B12 §7.1) |
| 2 | RapidOCR **rec** (hạng mục 5a) | 🔴 MỚI — phải nằm trong cùng `chan_loi()` |
| 3 | `cv2` điểm động (hạng mục 2c) | 🔴 MỚI — `cv2.setNumThreads`, phải **đo** |
| 4 | fixture giả lập OCR cho test nhẹ | ⏳ B12 lớp 2, chưa làm |
| 5 | **bánh cóc** cho cả lớp "thư viện mặc định lấy hết lõi" | ⏳ B12 lớp 3, chưa làm |
| 6 | tham chiếu chết `dung_video.py:35` | ⏳ chưa sửa |

⭐ **Việc #5 là việc quan trọng nhất trong bảng, và plan này chứng minh điều đó:**
hai hàng 🔴 MỚI xuất hiện **ngay trong plan kế tiếp** sau sự cố. Nếu câu trả lời
cho *"cái gì sẽ NỔ nếu nó xảy ra lần nữa"* là *"tôi sẽ nhớ"*, thì ⛔ chưa có gì.

---

## 7. Danh sách hạng mục triển khai

### 7.0 Năm làn, chia theo CHỦ TỆP — ⛔ không hai làn sửa cùng tệp

| làn | chủ đề | tệp **chỉ** làn này được sửa | dải test |
|---|---|---|---|
| **L1** | thời gian · tốc độ | `nan_cho_vua.py` · `giai_doan_giong.py` · `giai_doan_thoi_gian.py` · `thoi_gian.py` | `4920–4924` |
| **L2** | ASR · ảo giác · độ phủ | `ban_ghi.py` · `giai_doan_chep_loi.py` · `autosubvideo/whisperx_runner.py` | `4925–4929` |
| **L3** | trần CPU · bánh cóc | `do_vung_ocr.py` · `do_vung.py` · `video_assembly/services/dung_video.py` · `tools/` bánh cóc | `4930–4934` |
| **L4** | cắt · cửa sổ khách | `ke_cat.py` · `giai_doan_hinh_anh.py` | `4935–4939` |
| **L5** | người lái không-deploy | `tools/asv_chay_tai_cho.py` (**tệp MỚI**) | `4940` |

🔴 **Dải test chốt TRƯỚC khi làn nào chạy.** `check_so_test` là một **sổ đăng ký
dùng chung**, và bài học 24/09 ghi rõ: các làn ⛔ không va nhau đều khắp — chúng
**tụ ở chỗ một làn khai một điều về CẢ HỆ** (migration · dải test · thành phần ·
route). Chia sẵn dải là cách duy nhất để bốn làn cùng thêm test mà ⛔ không cấn.

⚠️ **`4898–4919` ⛔ KHÔNG dùng được — bản nháp đầu của plan này đã chọn sai.**
Đo lại trên `tests/`: `4900–4908` **đã có chủ** (phiên khác), `4890–4897` là của
B9/B10/B12. `4920–4979` trống hoàn toàn. ⭐ Và `check_so_test` chỉ chặn **trùng**,
⛔ nó **không cấp dải** — nên không có cửa nào bắt hộ lỗi này; phải đếm tay trước
khi chia.

⚠️ `giai_doan_qc.py` / `qc.py` **⛔ chưa gán cho làn nào** — nếu một việc buộc
phải sửa chúng thì việc đó về **L2** (nó là nơi đọc `phu_song`), và L4 phải
nhường.

---

### 7.1 PHA A — P0 · mở lại trục đối chiếu và gỡ nén oan

| id | làn | việc | tệp / neo | xác minh |
|---|---|---|---|---|
| **A1** | — | Lượt test kế đặt `settings["cat"] = None` | tham số job, **0 dòng mã** | `image_finish.cua_so_khach == []` và `thoi_luong_ra == thoi_luong_vao` |
| **A2** | L1 | `ket_luan()` nhận **`ngan_sach`** làm mẫu số của `he_so_co_gian` | `giai_doan_giong.py:495,558,727` → `nan_cho_vua.ket_luan` → `co_gian_du_khong` | `seg_0007`, `seg_0024` ra hệ số **1,0**; `seg_0011`, `seg_0031` **giữ nguyên** |
| **A3** | L2 | Một lượt **pyannote VAD một mình**, ⛔ không decode whisper | script dùng một lần, ~10 s GPU | biết (A) hay (B) — **⛔ chưa vặn gì** |

⭐ **A1 là việc rẻ nhất và giá trị nhất trong cả plan**: nó trả lại khả năng đối
chiếu bản giao với video gốc, thứ mà mọi hạng mục còn lại cần để kiểm.

⛔ **A2 ⛔ KHÔNG sửa `khe_cua`.** `khe_cua` trả lời đúng câu của nó (*"khe của
đoạn này rộng bao nhiêu"*) — `thoi_gian.ngan_sach_nan_s` đã viết ra lời ấy 26/09.
Sai là **câu được hỏi** ở chỗ gọi. `khe` **ở lại** trong `KetQuaNan` cho báo cáo.

⚠️ **A2 phải giữ một bất biến ngược**: một đoạn có `lặng = 0` thì `ngan_sach ==
khe` ⇒ hệ số **⛔ không đổi**. Nếu test chỉ chốt hai đoạn được gỡ mà ⛔ không chốt
hai đoạn giữ nguyên, thì một bản vá "nới hết" cũng xanh — đúng bẫy *"số 0 cần đối
chứng"*.

🔴 **A3 ⛔ không được bỏ qua để nhảy sang vá.** Hai khả năng cho hai cần gạt khác
nhau; vặn sai thì bản chép ra **y hệt**, và một thay đổi "đã áp dụng" mà kết quả
⛔ không đổi một ký tự là dấu hiệu nó **chưa bao giờ chạy**
(`whisperx_runner.py:78`, đo 24/09).

---

### 7.2 PHA B — P1 · làm cái đã đo được NHÌN THẤY

| id | làn | việc | tệp / neo | xác minh | phụ thuộc |
|---|---|---|---|---|---|
| **B1** | L2 | Tín hiệu ảo giác **thứ ba**: văn bản đoạn là khúc con của `initial_prompt` | `ban_ghi.nghi_ao_giac` (:308) · chuỗi từ `MAU_CO_DAU_CAU` | `seg_0024` của lượt T1a-bis bị gắn cờ; **0** đoạn thật bị gắn oan | — |
| **B2** | L2 | **CỬA A** (tổng `phu_song`) + **CỬA B** (một hố đơn lẻ) | `giai_doan_chep_loi.py` sau `chuan_hoa` | lượt T1a-bis kích **cả hai**; một phim ít lời chỉ kích A | — |
| **B3** | L1 | Bất biến: tổng hệ số trên MỘT `ma` (`compose × timing`) ⛔ không vượt trần | `giai_doan_thoi_gian.py:344-362` + `compose` | một `ma` nằm trong cả hai tập ⇒ **nổ**, ⛔ không im | A2 |
| **B4** | L1 | `tom_tat` in **cùng một** đại lượng, hoặc **hai tên khác nhau** | `thoi_gian.tom_tat` (:430) · `giai_doan_thoi_gian.py:448` | ⛔ không còn `1,15` đứng cạnh `1,3333` dưới hai tên nghe như một | A2 |
| **B5** | L2 | Vặn cần gạt VAD **theo kết quả A3** | `whisperx_runner.py:88` `load_model(vad_options=…/asr_options=…)` | hố 32,5 s **co lại**, đo bằng chính phép §1.1 | **A3** |

⭐ **B1 ⛔ không hạ `NGUONG_KY_TU_MOI_GIAY`.** Ngưỡng 30,0 đã hiệu chỉnh trên 188
đoạn thật và nó **đúng** cho tín hiệu của nó. B1 thêm một tín hiệu **thứ ba độc
lập**, ⛔ không nới tín hiệu cũ — nới nó sẽ bắt đầu ăn lời thoại thật.

⚠️ **B5 đổi bản chép ⇒ đổi CER và đổi mọi số đo hạ nguồn.** `whisperx_runner.py`
đã ghi luật ấy cho `initial_prompt`; nó áp y nguyên cho `vad_options`. Và
`giai_doan_chep_loi.PHIEN_BAN_MA` **phải tăng** — nếu không, cache cũ trả về bản
chép của luật cũ và B5 nhìn như ⛔ không ăn.

---

### 7.3 PHA C — P1 · chặn hố CPU **TRƯỚC** khi mở hộ tiêu thụ mới

| id | làn | việc | xác minh |
|---|---|---|---|
| **C1** | L3 | `chan_loi()` bọc **cả** `rec`, ⛔ không chỉ `det` | CPU đỉnh ≤ `CPU_TRAN_LOI + 1` lõi với `use_rec=True` |
| **C2** | L3 | `cv2.setNumThreads(N)` — và **ĐO** nó có ăn | bảng `N → lõi → giây`, đúng khuôn B12 §7.1 |
| **C3** | L3 | Fixture giả lập OCR cho phép kiểm **nhẹ** (B12 lớp 2) | `test_4301` ⛔ không nạp model; chỉ nạp khi `LTT_TEST_NANG` |
| **C4** | L3 | **Bánh cóc** cho cả lớp *"thư viện mặc định lấy hết lõi"* (B12 lớp 3) | thêm một `import onnxruntime`/`torch`/`cv2` ⛔ không khai trần ⇒ **đỏ** |
| **C5** | L3 | Sửa tham chiếu chết `dung_video.py:35` | câu nói `demucs_runner` ⛔ không đặt trần, mà `:324` **đã đặt** |

🔴 **PHA C đứng TRƯỚC PHA D, và đó là ràng buộc cứng.** D1 (`use_rec`) mở một hộ
tiêu thụ CPU **mới**, E2 (`cv2`) mở hộ thứ hai. Máy đã treo **hai lần** vì đúng
hình dạng này, và 03/09 đã treo một lần trước đó.

⭐ **C4 là việc quan trọng nhất của cả plan**, và plan này **tự chứng minh** điều
đó: hai hàng 🔴 MỚI (C1, C2) xuất hiện **ngay trong plan kế tiếp** sau sự cố. Nếu
câu trả lời cho *"cái gì sẽ NỔ nếu nó xảy ra lần nữa"* là *"tôi sẽ nhớ"*, thì ⛔
chưa có gì.

⚠️ **C4 chạm `tools/` — sổ đăng ký dùng chung.** Nó khai một điều về **cả kho**,
nên nó là hàng dễ cấn nhất trong plan. L3 sở hữu nó; làn khác ⛔ không thêm bánh
cóc nào trong phiên này.

---

### 7.4 PHA D — P2 · OCR đọc chữ tham chiếu

| id | làn | việc | xác minh | phụ thuộc |
|---|---|---|---|---|
| **D1** | L3 | Bật `use_rec`, dùng chữ **chỉ** để phát hiện **ĐỔI ĐOẠN** | chữ ⛔ không đi vào nội dung, ⛔ không dịch từ nó | **C1** |
| **D2** | L3 | Chia đoạn ba tín hiệu: `gap > HOLD` **hoặc** `dy > MOVE_Y` **hoặc** **chữ đổi** | số đoạn che > 4 (det-only đo được 4) | D1 |
| **D3** | L3 | Đo lại giá CPU + số đoạn trên **chính phim này** | báo cáo kèm **SHA + môi trường** | D2 |

⚠️ **D3 ⛔ không được so với con số 4 của B10-2 mà bỏ qua môi trường.** Bài học
27/09: tôi đo **nhánh** rồi tuyên bố cho `main`.

---

### 7.5 PHA E — P2 · cắt

| id | làn | việc | xác minh |
|---|---|---|---|
| **E1** | L4 | `image_finish` báo *"cửa sổ khách đã xoá N đoạn thoại"* — **CẢNH BÁO**, ⛔ không chặn | lượt T1a-bis ra `N = 6` (+1 đoạn mất một phần) |
| **E2** | L4 | `diem_kem` nhắm **đuôi cảnh xấu** (rung · chuyển cảnh lỗi), dùng điểm động | cảnh có đuôi rung ⇒ ứng viên ở **đuôi**, ⛔ không ở giữa |
| **E3** | L4 | `giay_cat` đo bằng **HỢP** các khoảng, ⛔ không bằng tổng | hai ứng viên chồng nhau trong một cảnh ⇒ `giay_cat` ⛔ không đếm hai lần |

⛔ **E2 ⛔ KHÔNG nới `TRAN_CAT_TI_LE = 0,05`.** Chủ dự án **đã chốt GIỮ** ngày
25/09 sau khi biết cái giá (video 275 s ⇒ ngân sách cắt 13,8 giây). E2 chỉ làm
`diem_kem` **nhắm đúng hơn** trong cùng ngân sách.

⭐ **E3 là bẫy `select.py` của kho tham chiếu tự tố giác**: *"counting overlapping
chunks twice … makes the selector stop early"*. Nếu ⛔ không có E3 thì E2 sẽ làm
trần đóng sớm và `dung_o_tran` báo **sai**.

⚠️ E1 giữ đúng thiết kế đã ghi: cửa sổ khách là **lựa chọn của khách**, nên E1
**báo** chứ ⛔ **không chặn**. Biến nó thành cửa chặn là từ chối một yêu cầu rõ
ràng của khách vì một ngưỡng hệ thống.

---

### 7.6 PHA F — P3 · vòng trong không deploy

| id | làn | việc | xác minh |
|---|---|---|---|
| **F1** | L5 | `tools/asv_chay_tai_cho.py`: `nap_env` → tạo run → thuê lease GPU → `for g in pipeline.CHUOI: thi_hanh.chay_giai_doan(...)` | chạy hết 13 giai đoạn từ **cây làm việc**, ⛔ không deploy, ⛔ không tranh job |

🔴 **F1 là VÒNG TRONG, ⛔ KHÔNG phải bản thay thế nghiệm thu** — xem §5.3. Nó ⛔
không tái hiện `LocalSystem` PATH lẫn nhảy lan.

⚠️ F1 là **tệp MỚI duy nhất**, nên nó chạy song song với mọi làn khác mà ⛔ không
cấn. ⭐ Nhưng nó **đáng làm SỚM hơn P3 nếu** bốn làn kia cần nhiều vòng sửa —
mỗi vòng nó tiết kiệm một lượt deploy.

---

### 7.7 PHA G — nghiệm thu, **một lần, ở CUỐI PLAN**

| id | việc | luật |
|---|---|---|
| **G1** | Gộp bốn làn về `main` bằng **test nhắm xanh** | ⛔ KHÔNG gate để gộp. Gộp xong → `pre-commit run --all-files` |
| **G2** | Ba bộ kiểm **hình dạng cả cây** (< 45 giây) | `scan_source_secrets` · `check_mypy` · `check_silent_except` — test nhắm ⛔ không bắt được lớp này |
| **G3** | **MỘT** gate, **MỘT** cấp: `gate.py --doi --tu <sha THẬT>` | ⛔ Một gate mỗi nhánh. Còn pha chưa làm ⇒ **chưa bấm** |
| **G4** | Dựng lại **bundle** rồi deploy | Bundle là **ĐẦU RA** — `manifest.json` còn dấu xung đột ⇒ `/agent/canvas` 503 ⇒ mọi test có đăng nhập đỏ (28/09) |
| **G5** | `T1a-ter` trên **worker thật** (`asv_chay_worker_that`), `cat=None` | lượt CHỐT — môi trường `LocalSystem` |
| **G6** | Soát bản ra: cắt frame, **đối chiếu với gốc theo mốc** | A1 đã trả lại khả năng này |

⛔ **G3 ⛔ không chạy trước khi PHA A–F xong hết.** Còn việc chưa làm ⇒ chưa bấm
gate. Và ⛔ không chạy gate **trong** phiên cho từng pha.

🔴 **G3 PHẢI có mốc THẬT (`--tu <sha>`), và PHẢI đọc dòng `RESULT`.** Đo 28/09
(phiên khác, cùng ngày): lượt `--doi` **đầu tiên** của họ bị **TỪ CHỐI** với
`CHUA DO DUOC GI` — trên một **cây sạch**, `--doi` lấy phạm vi bằng diff với
`HEAD`, nên phạm vi luôn **RỖNG**.

⇒ ⭐ `PASS` sau vài giây, `0.0s`, hay `CHUA DO DUOC GI` đều là **KHÔNG CÓ ĐỘ
PHỦ**, ⛔ **không phải xanh**. Đây đúng hai cửa đã ghi sổ: `--doi` hạ cấp thì in
`PASS`, còn `--pham-vi` vượt trần 32 767 ký tự thì in `FAIL 0.0s` đọc **y hệt**
một bộ test đỏ. Tín hiệu phân biệt là `0.0s` và dòng `[BOQUA] N buoc` cạnh
`RESULT`.

⇒ Mốc đúng cho G3 là **SHA đang chạy trên production** (`/health/version` hoặc
`dau_van_tay.json`), ⛔ không phải `HEAD~1`.

---

### 7.8 Bảng phụ thuộc — cái gì chặn cái gì

```
A1 ─────────────────────────────────────────────► G5, G6   (mở lại trục đối chiếu)
A2 ──► B3, B4
A3 ──► B5                                         (⛔ đừng vặn trước khi biết vặn cái nào)
C1 ──► D1 ──► D2 ──► D3                           (⛔ trần TRƯỚC hộ tiêu thụ)
C2 ──► E2 ──► E3                                  (⛔ trần TRƯỚC cv2)
C4 ──────────────────────────────────────────────► chặn cả LỚP lỗi lặp lại
F1 ──► (rút ngắn mọi vòng sửa của A–E)
A–F ─► G1 ─► G2 ─► G3 ─► G4 ─► G5 ─► G6
```

⭐ **Hai ràng buộc cứng duy nhất trong plan**: `A3 → B5` và `C → D/E`. Mọi thứ
khác chạy song song được.

## 8. ⛔ Chưa đo được — ghi ra để ⛔ không ai tưởng đã biết

- (A) VAD so với (B) `no_speech_threshold` — §1.3, cần 1 lượt VAD-only.
- 7 lỗ hổng còn lại (2,1–7,4 s) có cùng nguyên nhân với hố 32,5 s hay không.
- `use_rec=True` tốn thêm bao nhiêu lõi và bao nhiêu giây (hạng mục 5b).
- `cv2.setNumThreads` có thật sự ăn trên bản OpenCV đã cài (hạng mục 6#3).

---

## 9. Sau khi triển khai — plan này SAI ở đâu (28/09, đo bởi năm làn)

### 9.1 🔴 §3.4 SAI CHIỀU — hai máy ⛔ không nhân nhau, một cái bị BỎ RƠI

Tôi viết: một `ma` nằm trong **cả hai** tập sẽ bị `1,15 × 1,3333 = 1,53`. **Sai.**
Đo (L1): `ket_xuat.py:214-216` nạp đúng `duong_video` + `duong_master` và map
`1:a:0`; `duong_lop` **chỉ bị ĐẾM** ở `:173` và ⛔ **không bao giờ vào `cmd`**.

⇒ `ke_hoach.he_so_toc` ⛔ **KHÔNG được áp**. Một `raise` chống nhân đôi là một
**nhánh chết** — đúng thứ sổ kho gọi *"mã phòng thủ cho ca không thể xảy ra"*.

🔑 **Chiều CÓ THẬT thì ngược lại, và nó tệ hơn:** `thoi_gian.lap_ke_hoach` đã đặt
các đoạn theo `dai / he_so_toc`, tức **chừa chỗ hẹp hơn** vì tin rằng tiếng sẽ
được tăng tốc. Tăng tốc ấy ⛔ không xảy ra ⇒ **12 đoạn** của lượt đã đo có tiếng
**DÀI HƠN chỗ kế hoạch chừa**. Và `thoi_gian.kiem:391` ⛔ không bắt được: nó kiểm
chồng lấn trên `dai_ms` **đã chia rồi**, tức nó đo bản đồ chứ ⛔ không đo lãnh thổ.

⭐ Tôi đã dặn L1 *"đọc trước, ⛔ đừng viết mã phòng thủ cho ca không thể xảy
ra"* — và chính lời dặn ấy làm lộ ra rằng **giả thuyết của tôi sai, còn lỗi thật
nằm ngược phía**. Nguồn cho ý định gốc (*"vốn định áp ở render"*):
`docs/auto_scan_video/reports/13_REPORT.md:190`.

Hiện trạng: `thoi_gian.doi_chieu_he_so_toc` (hàm thuần) **đếm và cảnh báo** từng
đoạn lệch + tính tích lớn nhất của hai máy. ⛔ **Không `raise`** — 12 đoạn lệch
hôm nay thì `raise` làm đỏ **mọi** lượt thật.

⇒ **HẠNG MỤC MỚI (P1, làn L1):** quyết `he_so_toc` sẽ được **áp** (ở đâu) hay
**bỏ** (và `lap_ke_hoach` thôi chừa chỗ hẹp). Hai đường đều đúng về kỹ thuật, nên
đây là **đánh đổi sản phẩm** — phải hỏi chủ dự án. ⛔ Đừng để nguyên trạng: hôm
nay 12 đoạn tiếng tràn chỗ chừa mà chỉ có một dòng `log.warning` canh.

### 9.2 ⚠️ B4 ⛔ không làm trọn được trong phạm vi L1 như plan viết

Đổi tên `he_so_toc_lon_nhat` / `so_doan_tang_toc` làm đỏ `test_408` theo **hai**
chiều (khoá mới chưa khai, và khoá đã khai mà ⛔ không ai ghi), và bản vá phải
nằm ở `tools/asv_doi_soat.py` — mà **§7.0 giao `tools/` cho L3**.

L1 đi đường lồng (`KHOA_CAN["timing_align"] = ("master",)` nên khoá con tự do) +
docstring. ⇒ **NỢ:** muốn đổi tên thật thì **L3 phải nhận thêm một hàng**.

⭐ Đây là chi phí thật của luật *một-tệp-một-chủ*: nó ngăn xung đột gộp, nhưng một
việc **đúng** có thể bị chặn vì nó vắt qua hai làn. Ghi ra thay vì để làn tự vượt
ranh.

### 9.3 🔴 NỢ MỚI — một bánh cóc đang đo CÁCH GÕ

`tests/test_2018::test_he_so_toc_KHONG_bi_kep_ve_tran` **đỏ khi
`giai_doan_thoi_gian` gọi cả `min` lẫn `max`**, kể cả khi `max` ⛔ không kẹp gì.
Nó đã **bắt oan** bản vá đầu của L1.

⇒ Đúng họ *"bánh cóc đo CÁCH GÕ thay vì đo tính chất"* đã ghi sổ: `pass` so với
docstring cùng nghĩa mà khác kết quả, và **báo động giả làm người ta TẮT cổng**.
L1 né được bằng cách đẩy số học sang `thoi_gian.py` (thật sự sạch hơn), nhưng
bánh cóc vẫn hỏng. **Giao L3** (nó đã có nghề với đúng lớp lỗi này).

### 9.4 ⚠️ NỢ MỚI — `dem_lech_cuoi` nay là cận TRÊN

Nó so `giay / h_ap` với **`khe`** trong khi ngân sách rộng hơn ⇒ **đếm thừa**
(chỉ với đoạn bị kẹp `> 2,0`, cực hiếm). Sửa đúng cần `ngan_sach` trên **từng
dòng `ban_ke`**, tức một bất biến của `nan_thoi_luong` — ⛔ không phải tệp của L1.
Đã ghi trong docstring. **Giao lượt sau.**

### 9.5 Hai thay đổi làm SỐ BÁO CÁO ⛔ không so được với lượt cũ

| đổi | cái giá | vì sao vẫn đúng |
|---|---|---|
| `he_so == 1,0` nay là `VUA`, ⛔ không còn `CO_GIAN` | `so_vua` phồng, `so_co_gian` teo | một `CO_GIAN` hệ số 1,0 kể về một `atempo` **chưa từng chạy** — đúng con bọ `nan_cho_vua.NGAN` đã ghi 25/09 |
| `ty_le_phu_song` nay đo **HỢP** | ⛔ không so được với lượt cũ nếu có chồng lấn | `outputs["phu_song"]` **giữ TỔNG** nên dữ liệu cũ vẫn so được; hai tên, hai đại lượng |

⭐ Cả hai đều là **sửa phân loại**, ⛔ không phải sửa số. Nhưng ai đọc báo cáo qua
hai mốc thời gian phải biết — nên chúng nằm ở đây chứ ⛔ không chỉ trong commit.

### 9.6 ⛔ HAI bánh cóc bắt được sau khi gộp, và cả hai NGOÀI pre-commit

```
check_silent_except    53 -> 57   (TANG 4)    tools/asv_chay_tai_cho.py
check_mypy union-attr  88 -> 90               cung tep, dong 100-101
```

Từng làn **xanh**, tổng thì **đỏ** — đúng lý do sổ kho gọi ba bộ này là *"hình
dạng CẢ CÂY"*: mã **đúng hành vi, sai bất biến toàn kho**, và test nhắm ⛔ **không
thể** bắt.

🔑 Và `union-attr` là **lỗi của người điều phối**: tôi dặn thêm
`sys.stdout.reconfigure` (tên phim tiếng Trung làm console cp1252 ném) mà ⛔ không
dặn **dùng khuôn nào**. Kho đã có khuôn đúng ở `asv_chay_worker_that.py:59-63`.
⇒ ⭐ *Một lời dặn nêu ĐÍCH mà ⛔ không nêu KHUÔN thì agent sẽ tự dựng khuôn thứ
hai* — và khuôn thứ hai của nó còn **ném thật** khi `stdout` đã bị thay.

⛔ Và ⛔ **không `--accept`** để hạ mốc `mypy` (nó đang mời, `arg-type 108→106`,
`index 32→31`): hạ mốc siết bánh cóc cho **cả kho**, trong khi phiên khác còn
việc dở — một mốc chặt hơn làm việc của họ đỏ vì lý do ⛔ không liên quan. Để
tới cuối plan.

---

## 10. Trạng thái — `main` = `f5c58466`, production = `1e34780f`

| id | việc | trạng thái |
|---|---|---|
| A2 | `ket_luan` nhận `ngan_sach` làm mẫu số | ✅ `8a5696f7` · 4 phép chốt **hai chiều** xanh |
| B1 | tín hiệu ảo giác thứ ba (prompt echo) | ✅ `9cf70bf3` · ngưỡng 4 ký tự, có đối chứng âm |
| B2 | CỬA A (tổng) + CỬA B (hố đơn lẻ) | ✅ `9cf70bf3` · CỬA A đo **HỢP**, `outputs` giữ **TỔNG** |
| B3 | bất biến chồng hệ số | ✅ thay bằng `doi_chieu_he_so_toc` — xem §9.1 |
| B4 | tên đại lượng ⛔ không đọc như một | 🟡 một phần (đường lồng + docstring); đổi tên thật ⇒ **A5** |
| C3 | fixture `gia_lap_ocr` | ✅ `56462bd8` · chặn ở `co_san()`, ⛔ không dựng tiền đề mới |
| C4 | bánh cóc tĩnh trần CPU | ✅ `56462bd8` · `check_khai_tran_cpu.py`, AST 3 tầng, 915 tệp / 24 mốc / 1 miễn |
| C5 | tham chiếu chết `dung_video.py:35` | ✅ `56462bd8` |
| E1 | báo cáo cửa sổ khách xoá thoại | ✅ `ed425898` · chốt **6 mất hẳn + 1 một phần** |
| E3 | ngân sách đo bằng **HỢP** | ✅ `ed425898` · có ca chồng lấn dựng ra |
| F1 | `asv_chay_tai_cho.py` | ✅ `159da8da` + `2c031c63` |
| — | hai bánh cóc hình dạng cả cây | ✅ `2c031c63` — xem §9.6 |
| **A4** | bỏ `he_so_toc`, thôi chừa chỗ hẹp | 🔵 **đang chạy** (L1) — xem §9.1 |
| **A5** | hai khoá `tom_tat`: đổi tên **hay BỎ HẲN** | 🔵 đang chạy (L1 quyết) · bản tham khảo `wip/c7-doi-ten` `81f3bfb9` |
| **C6** | bánh cóc `test_2018` đo CÁCH GÕ | 🔵 đang chạy (L3) — xem §9.3 |
| C7 | sổ khai `asv_doi_soat.py` | ⏸️ **hoãn tới sau A4/A5** |
| A1 | `cat = None` cho lượt test | ⏳ chờ chủ dự án xong phân tích video |
| A3 · B5 | tách (A)/(B) hố VAD rồi mới vặn | ⏳ cần 1 lượt GPU |
| C1 · C2 | trần lõi cho `rec` · `cv2.setNumThreads` | ⏳ cần **đo** |
| D1–D3 · E2 | OCR đọc chữ · đuôi cảnh xấu | ⏳ chặn bởi C1/C2 |
| §9.4 | `dem_lech_cuoi` là cận TRÊN | ⏳ cần `ngan_sach` từng dòng `ban_ke` |
| G1–G6 | nghiệm thu, **một** gate ở cuối | ⏳ cuối plan |

### 10.1 ⛔ Khoảng lệch `main` ↔ production, ghi ra chứ ⛔ không im

Mã sản phẩm lệch: `ban_ghi.py` · `giai_doan_chep_loi.py` · `giai_doan_hinh_anh.py`
· `ke_cat.py` · `nan_cho_vua.py` · `giai_doan_giong.py` · `giai_doan_thoi_gian.py`
· `thoi_gian.py` (+ `dung_video.py` chỉ chú thích, 2 công cụ mới).

⇒ ⛔ **CHƯA tới khách, và đó là CÓ Ý**: plan chưa xong, và luật dự án ghi *deploy
giữa plan phải HỎI chủ dự án*. ⛔ Không gì bị chặn vì chờ — mọi việc còn lại là mã
+ đo cục bộ; chỉ `G5` (`T1a-ter` trên worker thật) mới cần deploy.

### 10.2 ⚠️ NỢ MỚI cho phiên sở hữu `gate.py`/`tai_may.py`

`cpu_nhieu` là **mutex nhị phân** cho một tài nguyên **chia được**. Đo 28/09: một
lượt `gate --pham-vi` (35 phạm vi, `-j 2`) giữ khoá **23,4 phút** trong khi
`tai_may` báo `RANH` với **8,0/10 lõi vật lý rảnh** — hai lượt pytest vài giây
phải xếp hàng sau một tiến trình để trống 8 lõi.

⭐ Đây là dạng **khó thấy nhất** của *"giữ khoá trong lúc không tính"*: nó ⛔ không
đang **CHỜ** (giây CPU vẫn tăng, nên phép phát hiện *"tường dài + CPU thấp"* ⛔
không bắt được) — nó đang **tính CHẬM có chủ ý**. Cái giá của `-j 2` đổ lên
**khoá**, ⛔ không đổ lên máy.

⇒ Câu hỏi thiết kế: khoá nên biết *"tôi xin bao nhiêu lõi"* thay vì *"tôi xin cả
máy"*. ⛔ Không phải việc của plan này; đã báo phiên sở hữu.
