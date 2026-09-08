# FEATURE_PARITY_MATRIX — Viral ↔ Auto Scan Video ↔ năng lực nền tảng

> Artifact 3/5. Đọc sau `CURRENT_UI_AUDIT.md` và `VIRAL_RENDER_FEATURE_MAP.md`.
> Cột "LTT capability" **không suy đoán** — lấy từ
> `docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` (đo tại `706faca`) và từ
> `BE_MAT_CONG_KHAI` của từng app.

Từ vựng quyết định (đúng §5 của prompt V5, không thêm không bớt):
`KEEP_ASV` · `REUSE_LTT` · `ADAPT_VIRAL_IDEA` · `REIMPLEMENT_CLEAN` ·
`EXTEND_LTT_CAPABILITY` · `DEFER` · `REJECT`

---

## 🔴 0. Va chạm phải giải quyết TRƯỚC khi đọc bảng

Prompt V5 §6 xếp vào **P0** các mục: *Zoom · Tỉ lệ khung · Logo · Text overlay ·
subtitle controls · đa ngôn ngữ · đa giọng*.

`apps/auto_scan_video/hop_dong_v4.py` — hợp đồng sản phẩm đã đóng băng, được
`ADR-V4-001` chốt — nói ngược lại:

```python
CAM_TRONG_MVP = ("reorder", "reframe", "crop", "zoom", "broll",
                 "subtitle_burn", "upscale", "music_replace", "transition")

HAU_MVP = ("reframe", "zoom", "subtitle_burn", "upscale", "broll",
           "multi_speaker_voice", "multilingual_target",
           "social_ingest", "social_publish")
```

Và chú thích của chính nó ghi rõ điều kiện để gỡ:

> *"một mục rời khỏi đây là một quyết định sản phẩm, và nó cần một ADR."*

Nó còn ghi vì sao `reorder` nằm ở `CAM_TRONG_MVP` chứ không chỉ vắng mặt khỏi
bảng `THAO_TAC_CHO_PHEP`: nếu chỉ vắng mặt thì *"chưa khai"* và *"bị cấm"* trông
giống nhau, và một pha sau **chỉ cần thêm một dòng là đủ** để mở. Đặt ở đây thì
thêm dòng đó làm một phép kiểm đỏ.

### Cách xử lý — và vì sao không phải là "bỏ qua hợp đồng"

Prompt V5 §14 nói *"KHÔNG PHÁ FEATURE HIỆN TẠI"* và §1 nói giữ nguyên kiến trúc.
Từ vựng quyết định của chính §5 có sẵn `DEFER` cho đúng tình huống này.

⇒ Mọi mục trong `CAM_TRONG_MVP`/`HAU_MVP` nhận **`DEFER`**, kèm con đường mở
(một ADR-V5). Chúng **không** biến mất khỏi thiết kế: `V5_UI_INFORMATION_
ARCHITECTURE.md` dành sẵn chỗ và `RenderManifest` dành sẵn trường, để ngày ADR
được ký thì việc còn lại là bật cờ chứ không phải thiết kế lại.

⚠️ Đây là chỗ **duy nhất** trong cả chương trình mà tôi không thi hành nguyên văn
prompt, và lý do là một quyết định đã ghi thành văn bản của chính dự án. Nếu chủ
dự án muốn mở, việc cần làm là **ký một ADR-V5**, không phải sửa bảng này.

---

## 1. Nhóm: đường vào & khung sản phẩm

| Feature | Viral | ASV | LTT capability hiện có | Gap | Decision |
|---|---|---|---|---|---|
| Tải video lớn, bền vững | chọn tệp trên đĩa | route có, **UI không gọi** | `platform_core.upload_sessions` — presigned PUT, sniff magic-byte, cap 20 phiên / 2 GiB. Đã có caller thật (`autosubvideo/services/source_drafts.py:33`) | **chỉ thiếu client JS** | `REUSE_LTT` |
| Kiểm định dạng trước khi gửi | — | server-side | `upload_sessions` sniff | thiếu kiểm phía client | `REIMPLEMENT_CLEAN` (UI) |
| Preview nguồn | Preview 5s (`/api/preview5s`) | ❌ | `storage.url_for` presigned | ⭐ thiếu hoàn toàn | `ADAPT_VIRAL_IDEA` |
| Ước giá trước khi chạy | gói cước/hạn mức | `gia.py` có bảng, **không hiện** | `credit`, `gia.py` | thiếu route + UI | `KEEP_ASV` + `REIMPLEMENT_CLEAN` (UI) |
| Ước thời gian | ETA render | ❌ | `media.probe` (thời lượng) | thiếu | `ADAPT_VIRAL_IDEA` |
| Preset cấp sản phẩm | 20+ checkbox rời | 2 preset | `hop_dong_v4.PRESET` | ✅ ASV **đúng hơn** | `KEEP_ASV` |
| Hàng đợi / trạng thái bền | list RAM + tệp | máy trạng thái 11 giai đoạn | `platform_core.jobs` + `leases` | — | `KEEP_ASV` |

---

## 2. Nhóm: chỉnh hình (Edit)

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| Cắt đầu/cuối | `--trim-start/-end` | ❌ | `ban_dung` có `khoang_giu` | trường đã có, GUI chưa | `ADAPT_VIRAL_IDEA` |
| Tỉ lệ khung 9:16/16:9 | `--ratio` | ❌ | — | `CAM_TRONG_MVP: crop, reframe` | **`DEFER`** → ADR-V5 |
| Phóng to | `--zoom` | ❌ | — | `CAM_TRONG_MVP: zoom` | **`DEFER`** → ADR-V5 |
| Quy tắc biến đổi toạ độ khi zoom | `_anh_xa_zoom_frac` | ❌ | — | ⭐ **đặc tả phải viết NGAY** dù zoom hoãn | `REIMPLEMENT_CLEAN` (chỉ đặc tả + test) |
| Tốc độ | `--speed` | ❌ | `DUNG_SAI_DO_DAI_S = 0.50` | đổi độ dài, đụng lời hứa sản phẩm | **`DEFER`** |
| Logo của tôi | `--logo` | ❌ | `image_input.validate_reference` | không bị cấm; hậu MVP | **`DEFER`** (đã có chỗ trong IA) |
| Watermark chữ | `--text-wm` | ❌ | — | như trên | **`DEFER`** |
| Nhạc nền | `--bg-nhac` | ❌ | — | `CAM_TRONG_MVP: music_replace` | **`REJECT`** trong ASV |
| Ghép video | `/api/file_ghep` | ❌ | — | ngoài phạm vi | `REJECT` |
| Ảnh bìa | `--tao-thumb` | ❌ | `apps/thumbnail` (`image.thumbnail`) | app khác đã sở hữu | `REUSE_LTT`, hậu MVP |
| Lật gương · chỉnh màu · vân tay `--uniq` | có | ❌ | — | mục đích là **né phát hiện bản quyền** | **`REJECT`** — xem `VIRAL_RENDER_FEATURE_MAP.md` §10 |
| Chọn thư mục lưu | `--out-dir` | ❌ | `storage` | khái niệm desktop | `REJECT` |

---

## 3. Nhóm: vùng che (Region Editor)

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| Trình sửa vùng kéo-thả trên khung hình | ⭐ có, 6 chế độ | ❌ | — | **ABSENT** | `REIMPLEMENT_CLEAN` — thuộc **GUI của ASV** |
| Toạ độ chuẩn hoá 0..1 | có | ❌ | `ban_dung` chưa có trường `regions` | cần mở rộng schema | `EXTEND_LTT_CAPABILITY`? **Không** — `ban_dung` là của ASV ⇒ `KEEP_ASV` + mở rộng |
| Làm mờ vùng | `--blur-boxes` | ❌ | ffmpeg qua `asv_media` | cần trường + filter | `ADAPT_VIRAL_IDEA` |
| Xoá logo bằng điền nền | `--che-patch/--che-keo` | ❌ | — | inpaint, chi phí GPU chưa đo | **`DEFER`** — cần đo VRAM trước khi khai |
| Tự dò logo | `/api/detect_logo` | ❌ | — | **ABSENT** | **`DEFER`** (phụ thuộc job GPU mới) |
| Tự dò dải phụ đề gốc | `/api/detect_band` | ❌ | — | **ABSENT** | `ADAPT_VIRAL_IDEA`, hậu MVP |
| Vùng che ↔ vùng chữ tránh nhau | `_vung_tranh_y` | ❌ | — | quy tắc, không phải mã | `REIMPLEMENT_CLEAN` (đặc tả) |

> 🔑 Trình sửa vùng là **GUI của ASV**, không phải năng lực nền tảng: nó chỉ sinh
> ra **dữ liệu toạ độ**. Việc *thi hành* toạ độ đó là ffmpeg trong `asv_media`.
> Tách đúng như vậy thì phần khó (vẽ, kéo, zoom, undo) không đụng gì tới nền tảng.

---

## 4. Nhóm: nguồn lời thoại & phụ đề

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| **Định tuyến nguồn lời** (sub nhúng → hardsub OCR → ASR) | ⭐⭐⭐ có | ❌ luôn ASR | `autosubvideo.transcription.transcribe_file` (**declared**) | thiếu **nhánh quyết định**, không thiếu ASR | `ADAPT_VIRAL_IDEA` → đặt ở `asv_media`/`asv_gpu`, **không** ở orchestrator |
| Đọc phụ đề nhúng | có | ❌ | ffprobe qua `media.probe` | rẻ, chưa làm | `REIMPLEMENT_CLEAN` |
| OCR hardsub | `ocr_text.py` (2.521 dòng) | ❌ | **ABSENT** trong `apps/` | cần app/job mới có khai VRAM | **`DEFER`** — nhưng nhánh định tuyến làm trước |
| ASR | Whisper/CapCut | ✅ | `autosubvideo.transcribe_file`, gpu 6.000 MB | — | `REUSE_LTT` |
| Hợp nhất OCR + ASR | `_merge_ocr_whisper` | ❌ | — | phụ thuộc OCR | `DEFER` |
| Làm sạch bản chép (ảo giác, lặp, chồng đè) | 6 hàm | một phần | — | ⭐ đáng học | `ADAPT_VIRAL_IDEA` |
| Đốt phụ đề vào hình | `--phude` | ❌ | `autosubvideo` → `ToolSpec("video.subtitle")` | `CAM_TRONG_MVP: subtitle_burn` **vì app kia đã làm** | `REUSE_LTT`, hậu MVP |
| Style phụ đề (font/cỡ/màu/viền) | `--sub-style` | ❌ | `autosubvideo` | như trên | `REUSE_LTT` |
| Karaoke / chữ chuyển động | `--karaoke`, `--motion-tu` | ❌ | — | — | `DEFER` |
| Sửa SRT rồi render lại | `/api/srt_*` | ❌ | — | ⭐ giá trị cao | `ADAPT_VIRAL_IDEA`, hậu MVP |

---

## 5. Nhóm: dịch & đa ngôn ngữ

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| Gọi model dịch | Gemini web + AI key | ✅ `dich_thuat.py` | `ltt_llm` `ToolSpec("text.chat")`, dispatch qua `platform_core/llm/dieu_phoi.goi`, `llm_remote`×1 | — | `KEEP_ASV` / `REUSE_LTT` |
| Từ điển tên riêng | `/api/glossary_*` | ❌ | — | ⭐ chất lượng dịch | `ADAPT_VIRAL_IDEA` (thuộc ASV: `ContentProfile`) |
| Nhiều ngôn ngữ đích | 70+ | khoá `vi` | — | `HAU_MVP: multilingual_target` | **`DEFER`** — IA phải chừa chỗ |
| **Phân tích nguồn một lần, fan-out N ngôn ngữ** | ⭐⭐⭐ có | chuỗi tuyến tính | `jobs` cho phép nhiều job con | ý tưởng kiến trúc, không phải tính năng | `ADAPT_VIRAL_IDEA` — thiết kế `RenderPlan` **ngay từ V5** để không phải mổ lại |

---

## 6. Nhóm: giọng nói

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| Danh mục giọng của khách | — | ✅ | `ltt_voice.doc_man_api.ma_giong_cua_toi` (**declared**) | — | `REUSE_LTT` |
| Lọc giọng theo giới/vùng/phong cách | 16 giọng phân nam/nữ | ❌ trong GUI | `ltt_voice/giong_mau.py`: `loc`, `tim`, `hop_le`, `DANH_SACH`, `NHAN_GIOI`, `NHAN_VUNG`, `NHAN_PHONG_CACH` — **đã** trong `BE_MAT_CONG_KHAI` (`apps/ltt_voice/__init__.py:59-65`), và `gia.giong_chon_duoc` **đã gọi `loc()`** | chỉ thiếu GUI | **`REUSE_LTT`** |
| Nghe thử giọng | `/api/dub/preview` | ❌ | `ltt_voice.features.goi_cong` (**declared**) | thiếu route + UI | `REUSE_LTT` + `REIMPLEMENT_CLEAN` (UI) |
| Phân vai người nói | `diarize_pitch.py` | ✅ `can_phan_vai` | `autosubvideo.ai_workflows.diarize_file` + `assign_speakers` (**declared**, pha 07) | — | `REUSE_LTT` |
| Nhãn nam/nữ cho cụm nói | ⭐ pyannote→cụm→F0 **cho cả cụm** | một phần | — | ⭐ xem `VIRAL_RENDER_FEATURE_MAP.md` §6.1 | `ADAPT_VIRAL_IDEA` |
| Nhiều giọng cho nhiều người | `--da-giong` | ❌ | — | `HAU_MVP: multi_speaker_voice` | **`DEFER`** |
| Ràng buộc "OCR không có giọng ⇒ không diarize" | có | ✅ đã có khái niệm | — | — | `KEEP_ASV` |
| Âm lượng gốc / giữ nhạc nền | `--goc-vol`, `--tach-nhac` | ✅ `tach_tieng.py`, demucs | `asv_gpu.audio_prepare` | ✅ ngang bằng | `KEEP_ASV` |
| Trần nén thời lượng khi khớp | `--max-speed` | ✅ `nan_cho_vua.py` | — | ✅ | `KEEP_ASV` |
| Clone giọng | `--ref-audio` | ✅ qua `ltt_voice` enroll | `ltt_voice.enroll` | — | `REUSE_LTT` |

---

## 7. Nhóm: hiệu năng & vận hành

| Feature | Viral | ASV | LTT capability | Gap | Decision |
|---|---|---|---|---|---|
| Cache artifact theo khoá nội dung | ⭐⭐⭐ `cache_artifact.py` | ❌ | `storage` + `assets.quet_het_han` (30 ngày) | **gap thật** | `ADAPT_VIRAL_IDEA` → **`EXTEND_LTT_CAPABILITY`** (thuộc `platform_core`, không thuộc ASV) |
| "Một tính, các bên kia chờ rồi dùng lại" | lock tệp + dò pid chết | ❌ | `platform_core.leases` | hành vi đúng, hiện thực sai | `EXTEND_LTT_CAPABILITY` dùng lease |
| Nguyên tắc NGHI NGỜ → MISS | có | — | — | quy tắc | `ADAPT_VIRAL_IDEA` |
| Khoá cache gồm đủ tham số + `CACHE_VERSION` | có | `ban_dung` đã băm | `ban_dung` có `hashlib` | ✅ nửa đường | `KEEP_ASV` + mở rộng |
| Một lần encode duy nhất | ⭐ có | ✅ `-c:v copy` (D-ASV-03) | — | ✅ ASV **mạnh hơn**: không encode lại hình *lần nào* ở preset giữ hình | `KEEP_ASV` |
| Chọn encoder GPU | `cai_gpu.py` | ✅ | `media.detect_gpu_encoder()` (nvenc>qsv>amf), đã xử lý bẫy kích thước tối thiểu NVENC | — | `REUSE_LTT` |
| Tiến độ render % + ETA | `/api/render_progress` | `_chay_co_tien_do` có, **UI không hiện** | — | thiếu đường lên UI | `KEEP_ASV` + `REIMPLEMENT_CLEAN` (UI) |
| Chẩn đoán chậm (encoder, ×realtime, filter) | `bench_toc_do.py`, `SUA-GPU-CHAM.bat` | `ket_xuat.ho_so_chan_doan` có | — | thiếu đường lên UI operator | `KEEP_ASV` + `REIMPLEMENT_CLEAN` (UI) |
| 2 lane render | `/api/lane/set` | — | `jobs` + lane nền tảng | — | `REUSE_LTT` |

---

## 8. Nhóm: REJECT dứt khoát

| Feature | Vì sao |
|---|---|
| Monolith `web_app.py` / `localize.py` | §2 prompt V5 |
| Hàng đợi bằng tệp | ADR-001 D1 — không bao giờ có hàng đợi thứ hai |
| Trạng thái qua biến môi trường toàn cục | `ban_dung` là dữ liệu, đó là cả điểm của nó |
| Khoá tiến trình kiểu desktop | nền tảng có lease |
| Định tuyến provider trực tiếp | `api_pool` + `dieu_phoi.goi` |
| License/HWID | auth + credit |
| Crawler (MediaCrawler) | ngoài phạm vi + **phi thương mại** |
| Đăng bài | `HAU_MVP: social_publish` |
| Nhóm né phát hiện bản quyền | quyết định thương hiệu — `VIRAL_RENDER_FEATURE_MAP.md` §10 |

---

## 9. Tổng kết

| Decision | Số mục |
|---|---|
| `KEEP_ASV` | 11 |
| `REUSE_LTT` | 11 |
| `ADAPT_VIRAL_IDEA` | 11 |
| `REIMPLEMENT_CLEAN` | 6 |
| `EXTEND_LTT_CAPABILITY` | 2 |
| `DEFER` | 14 |
| `REJECT` | 12 |
| **`BUILD NEW`** | **0** |

⭐ Con số cuối là kết luận quan trọng nhất của tệp này: **không một mục nào cần
một năng lực nền tảng mới.** Hai mục `EXTEND_LTT_CAPABILITY` còn lại đều là *mở
rộng additive* của một chủ sở hữu đã có (cache artifact trong `platform_core`,
lease cho cache).

### 🔴 Một đính chính, và bài học của nó

Bản đầu của bảng này xếp *"lọc giọng theo giới/vùng/phong cách"* là
`EXTEND_LTT_CAPABILITY` với lý do *"chưa trong `BE_MAT_CONG_KHAI`"*. **Sai.**
Nó đã được khai đủ bảy tên ở `apps/ltt_voice/__init__.py:59-65`, và
`gia.giong_chon_duoc` **đã gọi `loc()`** từ trước.

Nguồn của cái sai: tôi đọc `CAPABILITY_INVENTORY_V4.md` — nơi ghi
`EXTEND_OWNER_CONTRACT` — thay vì đọc mã. Bản kiểm kê đó đúng **tại thời điểm
nó được đo** (`706faca`); một pha sau đã đóng mục này, đúng như nó đã đóng mục
`diarize_file`, và bản kiểm kê không tự biết điều đó.

⭐ Bài học đã có tên trong kho này: **đọc thứ đại diện thay vì đọc thứ thật.**
Một bảng kiểm kê là ảnh chụp; mã là hiện tại. Với các mục còn lại của chương
trình V5, cột "LTT capability" phải được đối chiếu **lại với mã** ngay trước khi
mục đó được implement, không phải một lần lúc lập bảng.

Nói cách khác: **khoảng cách giữa ASV hôm nay và một studio xử lý video hoàn
chỉnh phần lớn là khoảng cách GUI, không phải khoảng cách năng lực.** Đó là lý do
chương trình này tên là GUI V5.
