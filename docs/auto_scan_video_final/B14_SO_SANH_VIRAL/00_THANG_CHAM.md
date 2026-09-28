# B14 — Đối chiếu `D:\Viral` với ASV: thang chấm DÙNG CHUNG

**Ngày:** 2026-09-28 · **Yêu cầu chủ dự án:** *"lập bảng so sánh các hạng mục,
logic vận hành từng bước của dây chuyền; tính năng nào ta còn thiếu mà Viral đã
xây; chấm điểm rõ ràng để nghiên cứu nên bổ sung hay không."*

🔴 **Tệp này là NGUỒN CHÂN LÝ của thang chấm.** Năm làn cùng điền, và nếu mỗi làn
tự đặt thang thì bảng ⛔ không so được với nhau — đúng bẫy *"hai chỗ khai cùng một
điều, ⛔ không ai bắt khớp"*. ⛔ Đừng sửa thang; nếu thang thiếu một ô, **báo điều
phối**, ⛔ đừng tự thêm cột.

---

## 1. Quy mô và PHẠM VI

```
D:\Viral\resources\app-src   118.491 dong · 260 tep .py
   localize.py   20.644   <- dieu phoi ca day chuyen
   web_app.py    22.935   <- UI + server cua ho
```

### 🔴 Phạm vi CHỐT LẠI 28/09 (chủ dự án): **CHỈ** `auto_scan_video` ↔ **module Render** của Viral

⚠️ Bản đầu của mục này khoanh *"dây chuyền lồng tiếng"* — **rộng hơn yêu cầu**. Chủ
dự án chốt: chỉ so ASV với **module Render**. ⇒ Biên ⛔ không còn là một danh sách
tôi chọn, mà là một **sự thật đo được**: *mọi thứ với tới được từ `xu_ly_chon.main()`*.

**Xương sống, đo bằng chuỗi import thật:**
```
render_worker.py  346    worker SONG, doc JSON-line stdin, giu NONG model qua nhieu render
  -> xu_ly_chon.main()          1.754   DIEM VAO that (argparse) — noi LUONG va TUY CHON song
       -> localize.py          20.644   than day chuyen
       -> xu_ly_video.py        2.716   tang ffmpeg
       -> phu_de.py             1.153   WhisperModel + _transcribe
```

**Với tới được (đã kiểm từng tệp):** `ocr_text.py` · `dai_sub.py` ·
`dai_sub_rapid.py` · `cache_artifact.py` · `chat_luong.py` · `capcut_asr.py` ·
`capcut_tts.py` · `dich_gemini_web.py` · `zhconv/` · `ngon_ngu` ·
`chan_doan_loi.py` · `tts_chuan_hoa` · `vietnormalizer` · `thong_tin_may` ·
`thumb_tool` · `diarize_pitch.py` · `bam_watermark.py` · `cat_giong_clone.py`

### ⛔ NGOÀI module Render — đo được, ⛔ không phải ý kiến

```
grep "import <m>" render_worker.py xu_ly_chon.py localize.py xu_ly_video.py phu_de.py
```
⇒ ⛔ **KHÔNG ai trong module Render gọi:** `long_tieng/` · `_demucs_worker.py` ·
`_whisper_worker.py` · `_phan_tich_srt.py` · `cai_gpu.py` · `cai_omnivoice.py` ·
`kiem_thu_vien.py` · `bench_toc_do.py` · `chan_doan_gpu.py`

⚠️ ⭐ **Hai cái đầu là bất ngờ đáng ghi:** `long_tieng/` và `_demucs_worker.py`
nghe **đúng như** việc lồng tiếng và tách nhạc của ta, mà **module Render ⛔ không
gọi chúng**. ⇒ Một tệp mang đúng tên việc ta làm vẫn có thể **⛔ không nằm trong
đường họ chạy** — đúng họ lỗi *"đọc thứ đại diện thay vì đọc thứ thật"*. ⛔ Đừng
xếp hàng theo **tên tệp**; xếp theo **đường gọi**.

Và loại từ trước, vì lý do khác (⛔ không phải cùng sản phẩm):
| bị loại | lý do |
|---|---|
| `MediaCrawler/` (~8k) | thuộc **app khác** của ta (`video_crawler`) |
| `license_server/` · `bao_mat_key.py` | ta có `credit.py`/`billing.py` — mô hình tiền **khác hẳn** |
| `web_app.py` · `_do_render_ui*.py` | UI desktop một người; ta là SaaS có server riêng |
| `tai_ytdlp.py` · `chup_bai.py` · `xhs_browser.py` | tải/đăng bài — thuộc `video_crawler` |

⚠️ Loại ⛔ **không** nghĩa "⛔ không bao giờ xem". Muốn soát `video_crawler` so với
`MediaCrawler`, hay lớp lồng tiếng của họ ngoài Render, thì đó là **bảng B15 riêng**.

---

## 2. 🔴 Khác biệt NỀN TẢNG — đọc TRƯỚC khi chấm bất cứ hàng nào

| | `D:\Viral` | ASV của ta |
|---|---|---|
| hình thái | app **desktop MỘT người dùng** | **SaaS đa người dùng** |
| cấu hình | **biến môi trường** (`WHISPER_NOSPEECH`, `WHISPER_VAD_THR`…) | `settings` theo từng lần chạy, có sổ khai |
| trạng thái | biến **toàn cục**, `globals()[...]` | `AsvRun`/`AsvStage` trong CSDL, có vân tay |
| tiền | giấy phép | **sổ credit có bút toán thật** |
| lỗi | log ra màn hình cho người đang ngồi đó | `loi.phan_loai`, thử lại được / ⛔ không |
| tệp | đường dẫn cục bộ | `Storage` (R2 hoặc đĩa), khoá có phạm vi chủ sở hữu |

⇒ 🔑 **Một tính năng của họ có thể ĐÚNG mà vẫn ⛔ KHÔNG mượn được**, vì nó dựa
trên "có một người đang ngồi xem log". ⭐ Thứ mượn được là **LỚP TÍNH** (thuật
toán, ngưỡng đã đo, thứ tự bước); thứ ⛔ không mượn được là **LỚP NỐI** (cấu hình,
trạng thái, báo lỗi).

⛔ **Tuyệt đối ⛔ không đề nghị đổi `credit.py` · `jobs.py` · `job_runner.py` ·
`gpu_lease.py`** — chúng có lưu lượng và bút toán **thật**.

---

## 3. Cột của bảng — ĐÚNG tám cột, ⛔ không thêm bớt

| cột | nội dung |
|---|---|
| `HẠNG MỤC` | tên việc, theo **nghiệp vụ** chứ ⛔ không theo tên hàm |
| `BƯỚC ASV` | giai đoạn nào của `pipeline.CHUOI` (13 giai đoạn), hoặc `—` |
| `VIRAL CÓ GÌ` | mô tả + **neo `tệp:dòng`**. ⛔ Không neo = ⛔ không tính |
| `TA CÓ GÌ` | module/hàm của ta + neo, hoặc `⛔ KHÔNG` |
| `TRẠNG THÁI` | một trong năm nhãn ở §4 |
| `GIÁ TRỊ` | 1–5, §5 |
| `GIÁ` | 1–5, §6 |
| `ĐỀ NGHỊ` | `LẤY NGAY` / `LẤY SAU` / `⛔ KHÔNG LẤY` + **một câu** lý do |

⚠️ Mỗi hàng phải có **neo tệp:dòng cho CẢ HAI bên** (hoặc `⛔ KHÔNG` tường minh ở
bên ta). Một hàng ⛔ không neo được là một hàng **⛔ chưa kiểm**, và nó tệ hơn một
hàng thiếu — vì bảng sẽ nói một điều ⛔ không ai xác nhận được.

---

## 4. `TRẠNG THÁI` — đúng năm nhãn

| nhãn | nghĩa |
|---|---|
| `ĐÃ MƯỢN` | ta **đã** lấy, nêu neo cả hai bên |
| `THIẾU` | Viral có, ta ⛔ không, và nó **áp dụng được** cho sản phẩm ta |
| `CỐ Ý KHÔNG` | ta **cố ý** ⛔ không làm — **PHẢI nêu nguồn quyết định** (tài liệu/commit/ngày) |
| `KHÁC THIẾT KẾ` | cùng nhu cầu, ta giải **khác** — nêu cách của ta |
| `KHÔNG ÁP DỤNG` | nhu cầu ấy ⛔ không tồn tại trong sản phẩm ta (nêu vì sao) |

🔴 **`CỐ Ý KHÔNG` mà ⛔ không có nguồn thì ⛔ KHÔNG được dùng** — hãy ghi `THIẾU`.
Bịa một quyết định để lấp một ô là cách chắc chắn nhất để bảng này nói dối. Vài
quyết định **đã có** nguồn, dùng được ngay:
- đọc chữ để **DỊCH** — bỏ 26/09 (Task 21), `phu_de_cung.py` đã xoá
- **phân vai** (diarization) — rút 22/09, sản phẩm là MỘT giọng thuyết minh
- lớp **Agent/Canvas/Workflow** — tự do thiết kế lại, chủ sản phẩm chốt 07/09
- `TRAN_CAT_TI_LE = 0,05` — chủ dự án chốt **GIỮ** 25/09 sau khi biết cái giá
- WanGP — **giấy phép cấm bán**

---

## 5. `GIÁ TRỊ` 1–5 — *"khách nhận được gì thêm"*

| điểm | nghĩa |
|---|---|
| **5** | sửa một **khiếm khuyết chủ dự án ĐÃ BÁO** (mất tiếng · cắt hỏng · tăng tốc quá · chữ che sai) |
| **4** | sửa một khiếm khuyết **ta đã ĐO được** mà khách chưa báo |
| **3** | tính năng khách **thấy được** nhưng chưa ai đòi |
| **2** | cải thiện vận hành (nhanh hơn, rẻ hơn) — khách ⛔ không thấy |
| **1** | chỉ gọn mã |

⭐ **Cột `BẰNG CHỨNG` ẩn trong `GIÁ TRỊ`:** nếu chú thích của Viral **có một con
số đã đo** (*"video rap 65 s ra 2 câu với VAD, 24 câu khi tắt VAD"*) thì ghi
`+đo` cạnh điểm (ví dụ `4 +đo`). ⭐ Một ngưỡng **đã chạy thật ở nơi khác** đáng
hơn hẳn một đoạn mã trông hợp lý — và nó là thứ luật kho gọi là *"dùng lại trước,
tự viết sau"*. ⛔ Mã ⛔ không kèm số đo thì ⛔ không được `+đo`.

---

## 6. `GIÁ` 1–5 — *"mượn nó tốn gì"*

| điểm | nghĩa |
|---|---|
| **1** | một hằng số / một ngưỡng / vài dòng thuần |
| **2** | một hàm thuần mới, ⛔ không phụ thuộc mới |
| **3** | **gói mới**, hoặc chạm 2–3 module |
| **4** | **đốt CPU/GPU thêm** (⚠️ xem dưới), hoặc đổi một bất biến đang có |
| **5** | chạm **sổ sách** (credit/jobs/lease), hoặc đổi hợp đồng giai đoạn, hoặc đổi luồng tiền |

🔴 **Bất cứ hàng nào thêm một HỘ TIÊU THỤ CPU/GPU thì GIÁ ≥ 4 và phải ghi rõ.**
Máy này là **production** và đã **treo hai lần ngày 28/09** vì một thư viện mặc
định lấy hết lõi. Kho nay có bánh cóc `tools/check_khai_tran_cpu.py` — một hàng
mang thư viện mới vào **phải** khai trần (`chan_loi()`/`cpu_affinity`).

⚠️ Và ⛔ **đừng tin tên cần gạt**: đo 28/09, `cv2.setNumThreads(N)` **đọc lại
đúng N** mà CPU ⛔ không hề theo N; `OMP_NUM_THREADS` cho `onnxruntime` cũng ⛔
không nối. Nếu một hàng nói *"chặn được bằng tham số X"* thì phải **đếm số lần X
được đọc trong mã gói**, ⛔ không suy từ tên.

---

## 7. `ĐỀ NGHỊ` — suy từ hai trục, ⛔ không từ cảm giác

```
GIA TRI >= 4  va  GIA <= 3      ->  LAY NGAY
GIA TRI >= 3  va  GIA <= 4      ->  LAY SAU
GIA TRI <= 2                    ->  ⛔ KHONG LAY  (tru khi GIA = 1)
GIA = 5                         ->  ⛔ KHONG LAY  (tru khi GIA TRI = 5, va khi do PHAI HOI chu du an)
```

⚠️ Công thức là **điểm khởi đầu, ⛔ không phải phán quyết**. Nếu bạn lệch khỏi nó
thì **nói rõ vì sao** trong cột `ĐỀ NGHỊ` — một hàng lệch có lý lẽ đáng hơn một
bảng nhất quán mà sai.

---

## 8. ⛔ Ba điều ⛔ KHÔNG được làm khi điền bảng

1. ⛔ **Không chạy gì cả.** Vòng này là **ĐỌC**. ⛔ Không pytest, ⛔ không nạp
   model, ⛔ không ffmpeg. Ba làn khác đang giữ khoá CPU cho việc đo thật.
2. ⛔ **Không sửa một dòng mã sản phẩm nào.** Ra **một tệp Markdown** của làn bạn.
   Thấy một khiếm khuyết đáng sửa ⇒ **ghi thành hàng**, ⛔ đừng tự sửa.
3. ⛔ **`D:\Viral` là kho CHỈ ĐỌC.** ⛔ Không ghi, ⛔ không tạo tệp, ⛔ không chạy
   script của họ.

## 9. Và một cái bẫy của chính bảng này

⚠️ **Một hàng `THIẾU` ⛔ không tự động là một việc phải làm.** Viral là app một
người dùng đã chạy nhiều năm; nó có những tính năng sinh ra từ **thói quen của
đúng một người**. ⭐ Câu hỏi đúng ⛔ không phải *"họ có mà ta ⛔ không, sao vậy?"*
mà là *"khách của TA có cần nó ⛔ không?"* — và ⛔ nếu bạn ⛔ không trả lời được
câu ấy thì cho `GIÁ TRỊ = 3` rồi để chủ dự án quyết, ⛔ đừng cho 5.
