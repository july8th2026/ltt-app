# VIRAL_RENDER_FEATURE_MAP — bản đồ nghiệp vụ menu Render của ViralCrawl

> Artifact 2/5 của chương trình **GUI V5**.
>
> - Nguồn: `D:\Viral` — bản build 04/09/2026, `viralcrawl-desktop` v1.9.5. **READ-ONLY.**
> - Đường UI thật đã lần: `web/index.html` (32.142 dòng) → `web_app.py` (22.935 dòng,
>   `_do_POST` một chuỗi `elif`, 209 endpoint `/api/*`) → `xu_ly_chon.py` (CLI, 60+ cờ)
>   → `xu_ly_video.py` (dựng lệnh ffmpeg) + `localize.py` (20.644 dòng, ASR/OCR/dịch/dub).
> - Ngày đo: 2026-09-07.

---

## ⛔ 0. Ràng buộc pháp lý — đọc trước khi dùng tệp này

`D:\Viral\README.md` ghi nguyên văn về phần mã ngoài MediaCrawler:
**`UNLICENSED` / private**. Và `resources/app-src/MediaCrawler/` là fork của
`NanmiCoder/MediaCrawler`, giữ giấy phép **phi thương mại** của thượng nguồn.

⇒ Với **mọi** mục trong tệp này, quyết định tối đa được phép là
**hiểu hành vi → viết đặc tả → viết lại sạch**. Không sao chép nguyên văn một
dòng nào, kể cả hằng số kèm chú thích. Nơi tệp này chép lại một con số (ví dụ
`n_frames = 20`), con số đó được ghi như **bằng chứng đo được của người khác**,
và §18 của prompt V5 bắt ta **đo lại trên máy mình** trước khi mượn.

Đây không phải một cảnh báo hình thức: LTTSTUDIOSAPP là nền tảng **thương mại**.

---

## 1. Kiến trúc thật (để biết cái gì KHÔNG được bê sang)

| Tầng | Viral làm gì | Phán quyết |
|---|---|---|
| HTTP | `BaseHTTPRequestHandler`, một `_do_POST` khổng lồ với ~209 nhánh `elif` | **REJECT** — nền tảng có FastAPI + router theo app |
| Đồng thời | cờ toàn cục `_proc is not None or _dang_cao` ⇒ **một tác vụ toàn máy**; `_giu_cho_tac_vu()` ngay trước `spawn` | **REJECT** — `platform_core.jobs` + lease |
| Hàng đợi | `_tasks` list trong RAM + `_task_luu()` ghi tệp | **REJECT** — ADR-001 D1 cấm hàng đợi thứ hai |
| Truyền tham số | `os.environ[...]` (`TARGET_LANG`, `DA_GIONG`, `ASR_ENGINE`, `DUB_MAX_SPEED`, `UNIQ_SEED`…) rồi `subprocess` | **REJECT** — trạng thái toàn cục; ASV đã có `ban_dung` là **dữ liệu** |
| Quyền | license/HWID cục bộ (`license_server/`, `hwid.py`) + gói cước `TIER` | **REJECT** — nền tảng có auth + credit |
| Đơn vị công việc | `xu_ly_chon.py` **một tiến trình làm hết**: ASR → dịch → TTS → ffmpeg | **REJECT** — ASV chia 11 giai đoạn có thể thử lại từng bước |

🔑 Điểm mấu chốt: cái Viral gọi là "render" là **một tiến trình chạy tới cùng**.
Cái ASV gọi là "run" là **một máy trạng thái bền vững**. Mọi ý tưởng lấy từ đây
phải được dịch từ ngôn ngữ thứ nhất sang ngôn ngữ thứ hai.

---

## 2. Bảng nghiệp vụ — nhóm CHỈNH HÌNH (Edit)

Cột **Backend entry** là cờ CLI của `xu_ly_chon.py` (dòng dẫn ở `web_app.py:7623
_lenh_xu_ly` dựng lệnh từ `opts` của UI).

| Tên UI | Mục đích người dùng | Control | Backend entry | Engine | Cache/GPU | Bằng chứng production | Hợp ASV? |
|---|---|---|---|---|---|---|---|
| Cắt đầu/cuối | bỏ intro/outro của kênh gốc | 2 ô số (giây) | `--trim-start` `--trim-end` | ffmpeg trim | CPU, vào 1 lần encode | — | ✅ hợp — nhưng xem §5 |
| Tốc độ | 0.8–1.5× né trùng | slider | `--speed` | `setpts`/`atempo` | CPU | — | ⚠️ đổi độ dài ⇒ đụng `DUNG_SAI_DO_DAI_S` |
| Lật gương | né nhận dạng trùng | checkbox | `--mirror` | `hflip` | CPU | nhãn đổi 09/08/2026 ("Lật ngang"→"Lật gương") | ⚠️ mục đích là né bản quyền |
| Phóng to | 105–150%, cắt viền nguồn | slider | `--zoom` | `scale=iw*Z:ih*Z` + crop tâm | CPU | **có** — bug 2026-07 về clamp toạ độ | ⛔ `CAM_TRONG_MVP` |
| Chỉnh màu | né trùng | checkbox | `--color` | `eq` | CPU | — | ⚠️ né bản quyền |
| Tạo bản khác nhau | mỗi tài khoản một vân tay | checkbox | `--uniq` `--uniq-seed` | `eq` lệch rất nhẹ | seed = hash video ⇒ **giữ cache HIT** | **có** — seed cố ý không random để không phá cache đa ngôn ngữ | ⛔ né phát hiện trùng |
| Tỉ lệ khung | 9:16 ↔ 16:9 | select | `--ratio` `--reframe-den` | crop/pad | CPU | — | ⛔ `CAM_TRONG_MVP` (`crop`, `reframe`) |
| Nhạc nền | trộn nhạc trending | file + vol | `--bg-nhac` `--bg-path` `--bg-vol` `--bg-no-loop` | `amix` | CPU | — | ⛔ `music_replace` bị cấm |
| Logo của tôi | đóng dấu kênh | upload ảnh | `--logo` (`/api/upload_logo`) | `overlay` | CPU | — | ✅ hợp lý, hậu MVP |
| Watermark chữ | chữ chạy/đứng | text + kiểu | `--watermark` `--text-wm` `--motion-tu` | `drawtext` | CPU | — | ✅ hợp lý, hậu MVP |
| Ghép video | gộp nhiều clip | nút | `/api/file_ghep` | concat | CPU | — | ⛔ ngoài phạm vi ASV |
| Thư mục lưu | chọn ổ đĩa | picker | `--out-dir` `--dest-dir` | — | — | — | ⛔ khái niệm desktop |
| Ảnh bìa tự động | lấy/chọn frame đẹp | công tắc nhớ | `--tao-thumb` `--cover-url` | trích frame | CPU | KB ghi: video tự tải lên **tự khoá** tính năng này | ⚠️ `apps/thumbnail` đã có |
| Preview 5s | xem thử trước khi render | nút 👁 | `/api/preview5s` | ffmpeg 5 giây | CPU | — | ⭐ **ý tưởng tốt nhất nhóm này** |
| Render song song | 2 video cùng lúc nếu ≥8 nhân | tự động | `/api/lane/set` | 2 lane | CPU | KB §5: nhả CPU cho video kế trong lúc đang xuất | ⚠️ nền tảng đã có lane |

---

## 3. Bảng nghiệp vụ — nhóm CHỌN VÙNG (Region Editor)

Đây là nhóm Viral **mạnh hơn hẳn** ASV, và là nhóm đáng học nhất.

| Chế độ vùng | Việc nó làm | Backend entry |
|---|---|---|
| 🌫 Làm mờ | che kín logo/watermark/chữ nguồn | `--blur-boxes` `--blur-sigma` `--che-blur` |
| 🧹 Xoá logo | **điền nền** — xoá hẳn, không để lại ô mờ | `--che-patch` `--che-keo` (`xoa_text.py`) |
| 📝 Đặt phụ đề | đánh dấu nơi che chữ gốc | `--sub-band` `--sub-khung` |
| 🖼 Logo của tôi | đặt logo khách ở góc | `--logo` |
| 🔤 Chữ | watermark chữ | `--text-wm` `--banner-boxes` |
| 🎯 Tự dò logo | tự đề xuất vùng che | `/api/detect_logo` (`bam_watermark.py`, `dai_watermark.py`) |
| Che dải chữ | dò + che dải phụ đề gốc, **bật sẵn** | `/api/detect_band` → `--che-band` `--che-mau` `--che-dong` |

### 3.1 Ba bài học kỹ thuật cụ thể

**(a) Toạ độ là phân số 0..1, không phải pixel.** Cờ nhận `"y0,y1"` hoặc
`"y0,y1,x0,x1"`. Hàm đọc (`xu_ly_chon.py:~300 _doc_dai`) ghi rõ: *sai định
dạng/ngoài khoảng → `None`, **KHÔNG đoán***. Đó là hành vi đúng và ASV nên chép
lại **nguyên tắc** này.

**(b) Phép biến đổi toạ độ khi zoom phải LOẠI BỎ, không CLAMP.**
`localize.py:675 _anh_xa_zoom_frac` — với center-crop hệ số `Z`, một điểm `p`
ánh xạ thành `p' = 0.5 + Z·(p − 0.5)`. Hộp rơi **hoàn toàn** ra ngoài khung sau
crop trả `None`.

> Chú thích của chính nó ghi lý do, và đây là bài học đắt: *clamp về biên sẽ che
> nhầm vùng trống nơi chữ đã biến mất* (bug zoom 2026-07).

⇒ Với ASV: `zoom` đang bị `CAM_TRONG_MVP` cấm, nhưng **quy tắc "biến đổi hình
làm vùng bị loại chứ không bị kẹp"** vẫn phải nằm trong đặc tả `RenderManifest`
ngay từ V5, vì ngày mở `zoom` ra thì đã quá muộn để phát hiện lại.

**(c) Vùng che và vùng chữ phải tránh nhau.** `localize.py:809 _vung_tranh_y`
tính vùng cấm đặt phụ đề từ `blur_boxes` + `text_wm`. Nếu không, phụ đề dịch bị
vẽ đè lên chính ô đang che chữ gốc.

---

## 4. Bảng nghiệp vụ — PHỤ ĐỀ · OCR · ĐỊNH TUYẾN NGUỒN LỜI

### 4.1 Định tuyến "lấy lời thoại từ đâu" — ý tưởng giá trị nhất của cả Viral

Viral **không** mặc định chạy Whisper. UI có công tắc *"Nhận lời thoại: Đọc từ
sub (mặc định) / Giọng nói"* → `--asr-engine ocr|whisper|whisper_fast`.

Chuỗi suy luận thật (`localize.py`):

```
video
 ├─ _do_ngon_ngu_noi()      nghe AUDIO đoán ngôn ngữ
 └─ nếu audio KHÔNG ra tiếng Trung:
       _han_tren_hinh()      OCR vài frame tìm chữ Hán trên HÌNH
        ├─ có  → video hardsub: đi đường OCR (ocr_text.py)
        └─ không → video thật không phải Trung: đi đường ASR
```

**Bằng chứng production, có ngày tháng và có ca thật** (chú thích
`localize.py:1398`):

> `n_frames` từng là **6**. Ca khách 27/07/2026 — video 143,8 s **có** hardsub mà
> trả `False`. Quét đối chứng 24 khung: chỉ **11/24 (~46%)** khung có chữ, vì phụ
> đề có khoảng nghỉ giữa câu, và một mốc lấy mẫu rơi đúng khe trống. Cần ≥3/6
> khung trúng ⇒ xác suất ~55% = **tung đồng xu**.
> Hậu quả dây chuyền: dò sai nguồn → bỏ qua OCR → ép Whisper → **treo 34 phút
> trên máy khách**.
> Sửa: nâng lên 20, gần như miễn phí vì vòng lặp `break` ngay khi đủ `min_box`.

⭐ Bài học chuyển giao được, độc lập với con số: **một phép dò lấy mẫu thưa trên
nội dung ngắt quãng là một phép tung đồng xu**, và cái giá của nó không phải là
"dò sai" mà là **cả nhánh pipeline sau đó chạy sai suốt 34 phút**.

Còn `_merge_ocr_whisper(ocr_segs, wh_segs, min_gap=1.2)` (`localize.py:1485`) hợp
nhất hai nguồn thay vì chọn một — cũng là ý tưởng tốt.

### 4.2 Làm sạch bản chép — nhóm hàm đáng học

| Hàm | Việc |
|---|---|
| `_la_ao_giac` | loại câu Whisper bịa |
| `_gop_trung` / `_dedup_lap` / `_bo_manh_trung` / `_bo_lap_lien` | 4 tầng khử lặp khác nhau |
| `_chong_de` | chống chồng lấn thời điểm |
| `_an_toan_libass` | thoát ký tự trước khi đưa vào libass |
| `_wps_giong_that` | từ/giây **thật** của từng giọng — dùng để nén thời lượng |

### 4.3 Phụ đề đầu ra

Style: cỡ/font/màu/viền/đậm/nghiêng (`--sub-style`), karaoke (`--karaoke`), chữ
chuyển động (`--motion-tu`), viết lại phong cách. Sửa SRT trong UI rồi render
lại: `/api/srt_duyet`, `/api/srt_export`, `/api/srt_gan`, `/api/srt_render_lai`,
`--srt-co-san`, `--vi-co-san`.

⇒ Với ASV: **`hop_dong_v4.CAM_TRONG_MVP` cấm `subtitle_burn` vì
`apps/autosubvideo` đã làm việc này.** Nhóm 4.3 là REUSE, không phải build.

---

## 5. Bảng nghiệp vụ — DỊCH & ĐA NGÔN NGỮ

| Tính năng | Backend | Ghi chú |
|---|---|---|
| 70+ ngôn ngữ đích | `--target-lang` → `os.environ["TARGET_LANG"]` | ASV hôm nay khoá `vi` (`NGON_NGU_DICH_HOP_LE`) |
| Từ điển tên riêng | `/api/glossary_get`, `/api/glossary_save`, `--quy-tac` | "Cải thiện dịch", chọn chung/riêng |
| Engine dịch | `--engine` (`google` **map về** `gemini`) | Google Dịch đã bỏ khỏi pipeline vì chất lượng kém; giữ trong `choices` để lệnh cũ không lỗi |
| Dịch tiêu đề | `/api/dich_tieu_de`, `/api/kn_dich_tieu_de` | ngoài phạm vi |
| Viết lại phong cách | `--phong-cach` | |

### 5.1 Quét nặng chỉ MỘT lần cho N ngôn ngữ

KB §5 và cơ chế `VC_SCAN_VHASH`/`VC_PREFETCH_SEED`: nghe lời gốc + đọc sub + dò
chữ dùng **chung** cho mọi ngôn ngữ đích của cùng một video.

> *"Càng nhiều ngôn ngữ đầu ra càng lợi — không nhân thời gian theo số ngôn ngữ."*

⭐ Đây là ý tưởng **kiến trúc**, không phải tối ưu vặt, và nó khớp thẳng với cách
ASV đã chia giai đoạn: `MEDIA_PREPARE → AUDIO_PREPARE → TRANSCRIBE` là phần
"phân tích nguồn", còn `CONTENT_PROCESS → VOICE → TIMING → COMPOSE → RENDER` là
phần fan-out theo ngôn ngữ. ASV chỉ cần **cho phép nhiều nhánh sau một thân**.

⚠️ Nhưng `multilingual_target` đang nằm trong `HAU_MVP`.

---

## 6. Bảng nghiệp vụ — GIỌNG & LỒNG TIẾNG

| Tính năng | Backend | Ghi chú |
|---|---|---|
| 4 engine TTS | `--tts edge\|piper\|omnivoice\|capcut` | `edge`/`capcut` online, `piper` offline, `omnivoice` clone |
| Clone giọng | `--ref-audio` (`_whitelist_ref` kiểm) | cần GPU |
| Nghe thử | `/api/dub/preview`, `/api/giong_doc`, `/api/tts_doc_lap` | |
| Âm lượng gốc | `--goc-vol` (0 = chỉ giọng dịch) | |
| Tách lời giữ nhạc | `--tach-nhac` `--xoa-nhac` `--khong-tieng-goc` | demucs |
| Đa giọng nam/nữ | `--da-giong` `--voice-nam` `--voice-nu` `--dao-giong` | `/api/phan_giong` |
| Chỉnh giọng | `--dub-toc` `--dub-pitch` `--dub-khu-on` `--giong-vol` | |
| Trần nén thời lượng | `--max-speed` → `DUB_MAX_SPEED` | giới hạn mức ép nhanh khi khớp thời điểm |

### 6.1 Phân giọng nam/nữ — `diarize_pitch.py`, đọc kỹ

Kiến trúc hai tầng, và **thứ tự ưu tiên là kết quả của một phép so đo thật**:

1. **Ưu tiên 1 — pyannote** (`segmentation-community-1` ONNX, không gate, tự tải
   ~32 MB): segmentation tách **ai đang nói** theo waveform (PowerSet decode) →
   embedding + clustering nối "local speaker" thành người xuyên suốt video → F0
   **chỉ dán nhãn nam/nữ cho CẢ CỤM**, không suy diễn qua ngưỡng F0 từng câu.
2. **Fallback — F0 thuần**: highpass 85 Hz cắt bass nhạc nền → chỉ giữ frame F0
   trong `[70, 450]` → lấy **median** (không mean, để outlier không kéo lệch) →
   k-means 2 cụm thích ứng, không rõ 2 cụm thì ngưỡng cứng 165 Hz → hysteresis
   ±12 Hz gán theo câu liền trước.
3. **Fallback cuối**: ≥90% cùng giới ⇒ trả `None` = video một người, dùng một giọng.

**Hai bằng chứng đo được:**

- Chú thích ghi đã test thật và pyannote **chính xác hơn hẳn** cụm-embedding-đơn
  (ECAPA) hay cụm-theo-F0-tuyệt-đối.
- Bẫy đã vấp: `_F0_HI` từng là 300 kèm bandpass 165 Hz — nó **kẹp** giọng nữ về
  ~150–178 Hz ⇒ hai cụm chồng nhau ⇒ tưởng một giọng. Đo lại trên video 1 nam
  1 nữ: bỏ bandpass thì tách rõ **nam 157 / nữ 207**.

⭐ Và một ràng buộc mà ASV phải chép: **chỉ diarize được khi có audio thật.**
Video hardsub đi đường OCR **không có giọng** ⇒ không phân vai được. ASV đã có
đúng khái niệm này ở `giai_doan_chep_loi.can_phan_vai`.

---

## 7. Bảng nghiệp vụ — HIỆU NĂNG

| Tính năng | Cơ chế | Đáng học? |
|---|---|---|
| **Cache artifact** | `cache_artifact.py` (673 dòng) | ⭐⭐⭐ xem §7.1 |
| **Một lần encode duy nhất** | gộp biến đổi + che + phụ đề + lồng tiếng vào 1 lần | ⭐⭐⭐ |
| Tăng tốc GPU | `/api/cai_gpu`, `cai_gpu.py`, `chan_doan_gpu.py`, `/api/chan_doan_driver` | ⭐ nền tảng đã có `media.detect_gpu_encoder()` |
| Tách audio sớm | `VC_PREFETCH_SEED` | ⭐⭐ |
| Tiến độ render | `/api/render_progress` | ⭐⭐ |
| 2 lane render | `/api/lane/set` | nền tảng đã có |

### 7.1 `cache_artifact.py` — bốn nguyên tắc, và ba trong bốn nên chép

Docstring của nó nêu nguyên tắc thiết kế, và chúng tốt:

1. **NGHI NGỜ → MISS.** Mọi lỗi/không chắc trả MISS (tính lại). *"cache KHÔNG bao
   giờ làm hỏng render."* ⭐ **Chép nguyên tắc này.**
2. **Khoá gồm ĐỦ tham số ảnh hưởng output** + `CACHE_VERSION`. *"Sót tham số =
   serve nhầm"* ⇒ bump version khi đổi logic. ⭐ **Chép.**
3. **Cache LOSSLESS** — tái dùng artifact đã sinh, **không giảm chất lượng, không
   đụng encode**. ⭐ **Chép.**
4. TTL 7 ngày theo *last-access* (`os.utime` touch khi HIT) + LRU theo cap 3 GB.
   ⚠️ Hợp lý cho desktop; ASV đã có chu kỳ **30 ngày** ở `assets.quet_het_han`.

**Và phần KHÔNG được chép:** cơ chế đồng thời. `doi_cache(key, suffix,
wait_giay=1800)` + `touch_lock` / `nha_lock` / `_pid_song` / `chu_lock_da_chet` /
`don_lock_mo_coi` là một **lock theo tệp trên đĩa có dò tiến trình chết**. Nó tồn
tại vì Viral không có bộ điều phối. LTTSTUDIOSAPP **có**: `platform_core.leases`.

⇒ Hành vi mong muốn ("một tiến trình tính, các tiến trình kia chờ rồi dùng lại")
là đúng và đáng có. Cách hiện thực thì phải là lease của nền tảng.

---

## 8. Chẩn đoán FFmpeg & tốc độ

Viral có `bench_toc_do.py`, `chan_doan_gpu.py`, `chan_doan_loi.py`,
`PHAN-TICH-LOG.bat`, `SUA-GPU-CHAM.bat`. Tức: **họ đã học được rằng "bật GPU"
không tự động nghĩa là nhanh hơn** — đủ để phải viết một công cụ chẩn đoán riêng
và một script "sửa GPU chậm".

⇒ Đúng cảnh báo §18 của prompt V5: *hardware decode có thể CHẬM nếu filter kế
tiếp chạy CPU*. **Không chép cờ máy móc — benchmark trước.**

ASV đã có một nửa: `ket_xuat.bo_ma_hoa_thuc_te(ban, co_gpu=)` và
`ket_xuat.ho_so_chan_doan(...)`. Việc còn lại là đưa lên bề mặt operator.

---

## 9. Phần Viral có mà ASV cố ý KHÔNG lấy

| Nhóm | Vì sao loại |
|---|---|
| Cào video (`/api/crawl`, MediaCrawler) | ngoài phạm vi; **giấy phép phi thương mại** |
| Theo dõi kênh, automation, workflow | `social_ingest` trong `HAU_MVP` |
| Đăng bài LohaPage | `social_publish` trong `HAU_MVP` |
| Băm nhỏ | `apps/taoclipngan` đã làm |
| License/HWID/gói cước | nền tảng có auth + credit |
| Trợ lý setup, chọn thư mục, mở link | khái niệm desktop |
| Nhóm "né bản quyền" (`--uniq`, mirror, color) | xem §10 |

---

## 10. Một nhận định sản phẩm phải nói thẳng

Một phần đáng kể nhóm Edit của Viral — `--uniq` (vân tay lệch màu theo tài
khoản), `--mirror`, `--color`, và cả tên tệp `xu_ly_chon.py` với dòng mô tả
**"né bản quyền"** ngay ở đầu — **không phải công cụ biên tập**. Đó là công cụ
làm video reup khó bị hệ thống bản quyền của nền tảng phát hiện là trùng.

LTTSTUDIOSAPP là nền tảng SaaS thương mại có định danh khách hàng thật. Đưa
những control này vào GUI V5 là bán một công cụ né phát hiện bản quyền dưới
thương hiệu LTT.

⇒ Khuyến nghị: **REJECT cả nhóm này** — không phải vì khó, mà vì đó là quyết
định thương hiệu và pháp lý. Ghi vào `VIRAL_HARVEST_DECISIONS.md` như một
quyết định có chủ ý chứ không phải một mục bị bỏ sót.

Các phép biến đổi *cùng tên* nhưng phục vụ mục đích biên tập thật (đổi tỉ lệ cho
Shorts, cắt intro, phóng to để bỏ viền đen) vẫn là ứng viên hợp lệ — khác nhau ở
**ý định và cách bày**, và GUI phải nói rõ ý định đó.
