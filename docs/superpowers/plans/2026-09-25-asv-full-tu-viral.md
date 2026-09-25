# ASV — hoàn thiện dây truyền, mỗi hạng mục ÁNH XẠ sang `D:\Viral`

> Lập 25/09/2026 · làn `asv-plan` · nhánh `phien/asv-plan` · `main` lúc lập: `cd8a5a60`.
>
> **Tệp này là plan HÀNH ĐỘNG.** Sổ trạng thái + sổ cái `N-xx` vẫn là
> `2026-09-24-thang-cong-asv.md`. Thứ tự "hoàn thiện dây truyền trước" của
> `2026-09-25-asv-xay-tiep.md` **vẫn thắng** — tệp này mô tả việc **sau** khi
> dây truyền chạy liền mạch, ⛔ không chen ngang nó.

**Lý do tồn tại.** Chủ dự án chốt 25/09:

> *"lấy code từ Viral để xử lý các hạng mục trong plan để chuẩn hoá dây truyền
> và hoàn thiện plan thay vì tự suy"*

và, kèm ảnh chụp GUI Viral: *"tất cả những công cụ, tính năng trong ảnh, tôi đều
cần khai thác cho hệ thống của ta."*

---

## 0. ⭐ BỐN LUẬT — con trỏ, ⛔ không chép lại toàn văn

| Luật | Chủ — chỉ nơi này định nghĩa |
|---|---|
| **L1 · Cổng** (test nhắm → L1/L2 giữa phiên → L3 một lần cuối phiên) | `docs/00_LTT_OPERATING_CONTRACT.md` §4 · `CLAUDE.md` luật 1 |
| **L2 · Agent** (một làn = một worktree + một nhánh, việc cơ học ⇒ `sonnet`, nhả `cpu_nhieu` ngay khi lệnh **tính** xong) | `CLAUDE.md` toàn cục mục ⭐ *Chạy agent* · `docs/QUY_TAC_CHAY_LENH_NANG.md` |
| **L3 · ⛔ KHÔNG dừng giữa các pha** | hợp đồng §10b · `CLAUDE.md` luật 2 |
| **L4 · Điều phối (một LLM) là NGƯỜI CHẤM khi bộ đo bị nghi ngờ** | `2026-09-25-asv-xay-tiep.md` §L4 (giao thức mù 5 bước) |

⛔ Không tệp nào trong plan này được định nghĩa lại bốn luật ấy.

---

## 1. 🔴 ĐỌC MỤC NÀY TRƯỚC — bảng `DEFER` cũ ĐÃ LẠC HẬU

`docs/auto_scan_video_v5/V5_IMPLEMENTATION_STATUS.md` §3 (ảnh chụp **08/09**) kê
tám mục `DEFER`. Kiểm lại trên mã `main` **hôm nay**: **sáu trong tám đã LÀM RỒI.**

### ⛔ ĐỪNG GIAO — đã có trên `main` `cd8a5a60`

| Mục `DEFER` 08/09 | Sự thật 25/09 | Bằng chứng trên `main` |
|---|---|---|
| zoom · tỉ lệ khung · crop — *"`CAM_TRONG_MVP`"* | **ĐÃ CÓ** | `hop_dong_v4.py:164` `NANG_LUC_DOI_DIEM_ANH` chứa `crop`, `zoom`, `reframe` · `bien_tap.py:50` `_TRUONG` · `hinh_hoc.khung_bien_tap` · `che_do_render._loc_khung:494` · `server/static/asv/bien_tap.js` |
| tốc độ — *"`DUNG_SAI_DO_DAI_S`"* | **ĐÃ CÓ** | `speed` trong `NANG_LUC_DOI_DIEM_ANH` · `bien_tap.TOC_DO_TOI_DA = 1.5` · `che_do_render.loc_toc_do_tieng:480` · `nan_cho_vua.py` bậc thang 4 nấc |
| logo · watermark chữ — *"`HAU_MVP`"* | **ĐÃ CÓ, kể cả vị trí x/y** | `logo.py:77` `chuan_hoa_mot` trả `{x, y, rong, do_mo}` · `lop_phu.py` · `che_do_render._loc_logo:314`, `_loc_chu:249` · `asv/logo.js:115-117` **đã có ô nhập x, y, rộng** |
| đốt phụ đề + style — *"`CAM_TRONG_MVP`"* | **ĐÃ CÓ ở pha 14** | `subtitle_burn` đã **gia nhập** `NANG_LUC_DOI_DIEM_ANH:168` · `phu_de.py`, `phu_de_cung.py` · `ass=` trong `filter_complex` · `asv/phu_de.js`. Đường `.srt` không đốt: `NANG_LUC_KHONG_DOI_DIEM_ANH` |
| cache artifact — *"thuộc `platform_core`, cần lease"* | **ĐÃ CÓ** | `cache_chung.py` + `platform_core.leases` (bảng `singleton_leases`) · `tests/test_2080_asv_cache_lease.py` · `docs/auto_scan_video_final/L_CACHE_LEASE.md` |
| OCR hardsub (nguồn lời) — *"chưa đo VRAM"* | **ĐÃ CÓ, đã đo, đã chốt** | `docs/auto_scan_video_final/L_OCR.md`: RapidOCR 3.9.2 + PP-OCRv6 small ONNX, Apache-2.0, **CPU 4 luồng 66 ms/khung**, CER 0,30 % vs ASR 1,81 % |

Thêm hai mục chủ dự án nhắc trong ảnh mà cũng **đã có**:

| Mục trong ảnh | Bằng chứng |
|---|---|
| âm lượng gốc · fade | `am_thanh.py:46-51` `NEN_DB_MAC_DINH`, `FADE_TOI_DA` · `am_master.fade_ap_dung:482` · `asv/am_thanh.js` |
| **"giữ âm gốc, bỏ giọng người"** — và nó là **MẶC ĐỊNH** | `tach_tieng.py:65-66` `STEM_GIU = ("drums","bass","other")` · `STEM_BO = ("vocals",)` · `MODEL_TACH = "htdemucs"` · demucs chạy mọi lượt (`demucs_runner.py`) |
| cắt đầu/cuối | `cat_dau_cuoi.py` · `asv/cat.js` |
| vùng che (làm mờ) | `vung_che.py` · `che_do_render._loc_lam_mo:188` · `asv/vung.js` |

### ⭐ Bài học của chính plan này

**Một bảng `DEFER` là ảnh chụp của MỘT NGÀY.** Mọi dòng phải kiểm lại **trên mã
hôm nay** trước khi lên plan. Đúng cái sai mà `V5_IMPLEMENTATION_STATUS.md` §6 đã
tự thú một lần: *"nguồn của cái sai: đọc **bản kiểm kê** thay vì đọc **mã**."*
Lần này bản kiểm kê **là** tệp đó, và nó đã cũ 17 ngày.

⇒ **Luật vào plan:** mỗi hạng mục ở §3 dưới mang một **ô bằng chứng `file:dòng`
trên `main`**. Không có ô đó ⇒ hạng mục **chưa được giao**.

---

## 2. ⛔ CỐ Ý KHÔNG LẤY — ghi rõ để người đọc sau ⛔ đừng tưởng ta bỏ sót

| Viral có | ⛔ Ta không lấy, vì |
|---|---|
| **Công tắc tổng mỗi khối** (bật/tắt cả nhóm Edit) | Viral cần vì cài đặt **sống qua cả lô video**. Ở ta **mỗi lượt là một video** và mọi khối đã **mặc định tắt** (hồ sơ THƯA — `bien_tap.chuan_hoa` chỉ ghi trường khác mặc định) ⇒ công tắc ấy là một control **gần như không làm gì**. |
| **Mẹo "khoanh vùng phụ đề tay cho khỏi mất công dò"** | `vung_che` loại `danh_dau_phu_de` của ta mang nghĩa **ÂM**: *⛔ đừng vẽ gì ở đây*. ⛔ **Không** phải che dải sub gốc. Và ta ⛔ **không có** bước tự dò để mà "khỏi mất công dò". ⇒ Chép câu đó là **một lời hứa sai với khách**. |
| **Nhóm né phát hiện trùng**: `--uniq`/`--uniq-seed` (`xu_ly_chon.py:54 _fingerprint_eq`, `xu_ly_video.py:1133`) | Lệch màu `±2 %` theo seed = hash video, để *"10 bản GIỐNG nhau vẫn bị flag"* không bị flag. LTT là nền tảng **thương mại có định danh khách thật** ⇒ bán công cụ né bản quyền dưới thương hiệu LTT. Quyết định **thương hiệu + pháp lý**, ⛔ không phải quyết định kỹ thuật. (`VIRAL_RENDER_FEATURE_MAP.md` §10 đã khuyến nghị; tệp này **giữ**.) |
| `MediaCrawler/` | fork `NanmiCoder/MediaCrawler`, giấy phép **phi thương mại**, quyền ⛔ không thuộc chủ dự án. Ta đã có `apps/video_crawler`. |
| Ghép nhiều video · băm nhỏ · thư mục lưu · license/HWID · trợ lý setup | ngoài phạm vi ASV, hoặc `apps/taoclipngan` / nền tảng đã có (`VIRAL_RENDER_FEATURE_MAP.md` §9). |
| Hàng đợi `_tasks` trong RAM · `os.environ` truyền tham số · một `_do_POST` 209 nhánh | ADR-001 D1 cấm hàng đợi thứ hai. ASV có `platform_core.jobs` + `ban_dung` là **dữ liệu** (`VIRAL_RENDER_FEATURE_MAP.md` §1). |

### Ba mục GIỮ `DEFER` — ⛔ đừng tự mở

| Mục | Chặn bởi | Vì sao ⛔ không mở trong plan này |
|---|---|---|
| `multilingual_target` (ngôn ngữ đích ngoài `{vi, en}`) | `hop_dong_v4.HAU_MVP:127` | chủ dự án ⛔ **không** nhắc trong ảnh |
| `multi_speaker_voice` (nhiều giọng) | `hop_dong_v4.HAU_MVP:126` | chủ dự án ⛔ **không** nhắc trong ảnh |
| `reorder` · `broll` · `upscale` · `transition` | `hop_dong_v4.CAM_TRONG_MVP:113` | `upscale`: `apps/upscalevideo` đã làm |

---

## 3. 🔑 BẢNG ÁNH XẠ — việc CÒN THẬT

Ba loại:

- **A — LẤY MÃ**: thuần tính, ⛔ không trạng thái ⇒ copy công thức/bảng tham số/phép ffmpeg + sửa import.
- **B — LẤY ĐẶC TẢ**: ý đúng, ⛔ phải viết lại cho SaaS (hàng đợi job, sổ credit, R2, Cloudflare cắt 100 MB / 100 s, nhiều người dùng).
- **C — ⛔ KHÔNG LẤY**: ta đã có bản tốt hơn, hoặc giấy phép chặn.

| # | Hạng mục | Tệp VIRAL giải bài này (đã `grep` xác minh) | Loại | Đặt vào đâu trong cây ta | Cờ/ADR cần ký | Phụ thuộc | Công |
|---|---|---|---|---|---|---|---|
| **V1** | **Lật gương** (`hflip`) | `xu_ly_video.py:1125-1126` (`if cfg["mirror"]: vf.append("hflip")`) · `preview_5s.py:61` · ⭐ bẫy: `localize.py:6581-6582` + `:7285-7286` (phải lật `x` của vùng/logo: `(x0',x1')=(1-x1,1-x0)`, `y` giữ nguyên; coi chừng **lật kép**) · `xu_ly_chon.py:812` (⛔ **không** lật trước OCR — OCR đọc chữ Trung ngược ra rác) | **A** | `bien_tap._TRUONG` + `chuan_hoa` · `che_do_render._loc_khung:494` (chặng KHUNG) · `ban_dung._kiem_bien_tap:399` · `hinh_hoc.khung_bien_tap` | ADR-V5 §V1 (ký cùng V2) | — | nhỏ |
| **V2** | **Dịch màu** | 🔑 Giá trị THẬT Viral dùng cho nút "chỉnh màu": `xu_ly_config.json:13` → **`eq=contrast=1.06:brightness=0.03:saturation=1.12`** (⛔ **ba** trục, ⛔ không phải một) · áp ở `xu_ly_video.py:1127-1128`, `xu_ly_chon.py:1041-1042`, `:1418` · ⛔ **không** lấy `_fingerprint_eq` (`xu_ly_chon.py:54`) — xem §2 | **A** | y hệt V1 | ADR-V5 §V2 | — | nhỏ |
| **V3** | **Nhạc nền** (tải lên + âm lượng + loop) | `xu_ly_video.py:51` (`bg_volume = 0.25`) · `:1091-1093` (**loop = `-stream_loop -1` đặt TRƯỚC `-i` của nhạc**) · `:1182-1196` (`[bg]volume=…` → `amix=inputs=2:duration=first:normalize=0` → **`alimiter=limit=0.95:level=false`** — `normalize=0` **SUM** ⇒ vượt 0 dBFS ⇒ méo) · `:1197-1212` (⭐ nhánh video **câm** ⛔ không qua `amix` ⇒ **`apad` BẮT BUỘC** — thiếu nó thì `-shortest` bám vào nhạc hữu hạn, **mất 15–20 phút đuôi**) · `:1170-1181` (`--goc-vol` kẹp `0..2`; ⭐ `≤0.001` ⇒ **coi như video CÂM**, dùng lại đúng nhánh đã có thay vì mở ca thứ ba) | **B** | `am_master.bieu_thuc_tron:497` + `tron_cuoi:543` (⛔ **KHÔNG** thêm `-i` thứ ba ở `ket_xuat.dung_lenh:219` — xem §3.2) · hồ sơ mới trong `am_thanh.chuan_hoa` · artifact nhạc qua `assets.py` | 🔴 **ADR-V5 §V3 — gỡ `music_replace` khỏi `CAM_TRONG_MVP:117`** | V1/V2 độc lập; cần `assets` đường tải lên (đã có, `logo.py:192 gan_vao_run`) | vừa |
| **V4a** | **Tự dò logo/watermark TĨNH** | 🔑 `/api/detect_logo` gọi **`dai_watermark.py:26` + `:44`** `phat_hien_watermark(video, n_frames=16, ngan_sach_giay=10.0)` → `_phat_hien`. Thuật toán: 16 khung → xám → `scale` bề rộng **360** → `stack.std(axis=0)` (**phương sai theo THỜI GIAN**: logo đục thì gần như ⛔ không đổi) → mặt nạ `std < 8.0` **giao** cổng biên `abs(Laplacian(mean, ksize=3)) > 26` → chỉ trong **vùng góc/mép** (⛔ không tâm — tránh thẻ tiêu đề) → `MORPH_CLOSE (9,9)` → `connectedComponentsWithStats` lọc theo diện tích `0.0009..0.06`, `w > 0.55·gw` loại, độ đặc `< 0.35` loại. ⭐ **0 model, 0 GPU — chỉ cv2/numpy** | **B** | mô-đun mới `apps/auto_scan_video/do_vung.py` (⛔ **không** sửa `vung_che.py` — nó là **lớp KIỂM**, ⛔ không phải lớp **ĐO**) | ADR-V5 §V4 **sau** Đ1 | 🔴 **Đ1** | vừa |
| **V4b** | **Tự dò DẢI CHỮ gốc** | `dai_sub.py:255 detect_blur_band` — thứ tự **tay → RapidOCR (`dai_sub_rapid.py:1914`) → OpenCV (`dai_sub.py:69 phat_hien_dai`) → không có**. Tầng OpenCV: 18 khung trong 10–90 % độ dài → bề rộng 480 → `sum(abs(Laplacian))` theo HÀNG → `score = nrm(mean) × nrm(std)` (**mạnh VÀ biến động theo thời gian** = chữ chạy) → mọc vùng đỉnh khi `score ≥ max(0.18, peak·0.45)`, chỉ 45–100 % dưới. Rồi `dai_sub.py:188 _om_sat_vien` bó Y về đúng nét chữ: `white = g>190`, `dark = dilate(g<70, (1,9))`, `stroke = white & dark`, hợp trên 12 khung, `pad 0.0075·H`. ⭐ **0 model, 0 GPU** ở tầng OpenCV; tầng RapidOCR dùng lại bộ ta đã có (`L_OCR.md`, **CPU**) | **B** | y hệt V4a | ADR-V5 §V4 | 🔴 **Đ1** | vừa |
| **V4c** | Logo **DI CHUYỂN** | `/api/bam_watermark` → `bam_watermark.py:542 bam(...)`: `cv2.matchTemplate(..., TM_CCOEFF_NORMED)` trên ảnh gradient đã CLAHE (`_net:66`) → gom cụm (`_gom_cum:91`, `o_luoi=24`) → `duong_bieu_thuc:180` sinh biểu thức `if(gte(t,t0), v0+slope·(t-t0), …)` lồng nhau. Hằng: `nguong_khop=0.55`, `MAX_CHANG=60`, `DUNG_SAI_DUONG=55 px`, `DI_TOI_THIEU=165 px`. Nạp **RapidOCR CPU** (`_lay_ocr:227`, đo thật trong docstring `:230-238`: **106 MB RAM, 0,8 s/lần**, khoá toàn cục `_OCR_KHOA`) | **B** nếu Đ1 nói đáng · **C** nếu không | y hệt V4a | ADR-V5 §V4 | 🔴 **Đ1** | vừa–lớn |
| **V5** | **Điền nền** (xoá hẳn thay vì để ô mờ) | 🔑 **Đường VIDEO của Viral ⛔ KHÔNG dùng model nào — HAI kỹ thuật, ⛔ đừng lẫn:** ① **`--che-patch`** (`localize.py:7944`): sao một dải **sạch lân cận** (khe `0.5·bh`, ưu tiên trên rồi dưới), pha trộn cặp trên+dưới, dốc alpha hình thang qua `geq`+`alphamerge`, rồi `overlay`. Hằng: `CHE_PATCH_GAP=0.10`, `CHE_PATCH_FEATHER=0.30`, `CHE_PATCH_FEATHER_X=0.04`. ② **`--che-keo`** (`localize.py:7782`, `:7830-7860`): `crop` dải **≤ `CHE_KEO_HS_MAX = 4 px`** (`localize.py:6106`) ngay trên và dưới → `vflip` + `scale` giãn phủ dải chữ → hoà chéo theo chiều dọc. Hằng: `CHE_KEO_HOA=1`, `CHE_KEO_FEATHER=0.30`, `CHE_KEO_FEATHER_X=0.04`, mọi độ dày qua `_chan2` (`:6110`). Lùi mặc định: `boxblur=h/12:2`. ⛔ `xoa_text.py` (LaMa ONNX) **chỉ cho ẢNH thumbnail** — `thumb_tool.py:17,195,212` là người gọi **DUY NHẤT**, và phiên được tạo với **`providers=["CPUExecutionProvider"]`** (`xoa_text.py:133`) ⇒ **0 VRAM**, nhưng ~200 MB tải về | **A** cho `che_patch`/`che_keo` (thuần ffmpeg) · **C** cho LaMa — xem §3.3 | `che_do_render`: **loại vùng thứ hai** cạnh `_loc_lam_mo:188` · `vung_che` thêm `loai="dien_nen"` · 🔴 **TĂNG `PHIEN_BAN_CHE_DO`** | ADR-V5 §V5 | 🔴 **Đ1** (xác nhận CPU, ⛔ không phải VRAM) | vừa |
| **V6** | Kéo-thả **vị trí** logo/watermark trên khung | — (Viral: `web/index.html` trình sửa vùng) | **C** | 🔴 **⛔ KHÔNG PHẢI VIỆC CỦA LÀN ENGINE.** Backend **đã nhận x/y** (`logo.py:107-108`), `asv/logo.js:115-116` **đã có ô nhập x/y**. Còn lại thuần UX: tái dùng bộ kéo SVG `viewBox="0 0 1 1"` của `asv/vung.js:165` | ⛔ không cần ADR | — | ⇒ giao làn **`asv-gui`** |
| **Đ1** | 🔴 **HẠNG MỤC ĐO** — dò vùng + điền nền: chi phí thật | `L_OCR.md` §5 (khuôn đo đã có) · `GPU_MAY_A.md` §2 (bảng "chuyển được? / VRAM / đáng?") · bộ đo `tools/bench_gpu_may_a.py` | — | `docs/auto_scan_video_final/L_DO_VUNG.md` (mới) | ⛔ **KHÔNG tự gỡ `DEFER`** — số trước, ADR sau | — | vừa |

### 3.1 ⭐ Chi tiết SỐNG CÒN của V1/V2 — đưa vào plan nguyên văn

> ⛔ Không tăng `PHIEN_BAN_CHE_DO` (`che_do_render.py:80`, đang **7**) thì **vân
> tay ⛔ không đổi** ⇒ lượt chạy lại **trả về tệp CŨ**, và khách sẽ thấy "đã bật
> lật gương" mà video **y như cũ** — một lỗi **IM LẶNG**.

Và `van_tay_che_do:601` **phải bắm** hồ sơ `bien_tap` mới. Hôm nay nó bắm
`che_do`, `bo`, `khoang`, `vung`, `lop_phu`, `logo`, `phu_de`, `phien_ban` — ⛔
**không** bắm `bien_tap`. Chính docstring của nó đã ghi tên cái bẫy này hai lần
(*"sót tham số = serve nhầm"*, L4 của `vung_che`), và V5 đã sót đúng một chiều
của chính nó (`tu_giay`/`den_giay`).

⇒ **V1/V2 là một changeset nguyên tử**: trường mới + `kiem` + chặng lọc + vân tay
+ `PHIEN_BAN_CHE_DO` lên một bậc. ⛔ Tách ra là mở một lỗi im lặng.

🔑 **Và một quà của kiến trúc ta**: bẫy `localize.py:6581` (phải lật `x` của vùng
che/logo) **⛔ không xảy ra ở ta**, vì thứ tự chặng của `loc_cat_noi:354` là

```
noi -> che (toa do NGUON) -> KHUNG -> logo -> chu -> phu de -> TOC DO
```

`hflip` nằm trong chặng **KHUNG** ⇒ **sau** `che` (nên vùng vẫn là toạ độ nguồn,
⛔ không cần lật) và **trước** `logo`/`chu` (nên logo của khách ⛔ không bị lật
ngược — Viral phải vá đúng chuyện này). ⛔ **Đừng đặt `hflip` ở chỗ khác.**
Và OCR của ta chạy ở `giai_doan_chep_loi` trên video **nguồn**, xong hẳn trước
render ⇒ bẫy `xu_ly_chon.py:812` cũng ⛔ không với tới được.

⚠️ **Và nếu ai vẫn định lật toạ độ**: bản Viral làm việc đó ở
`xu_ly_video.py:1729-1730` bằng `x = max(0, src_w - x - w)` — **`max(0, …)` là một
phép KẸP.** Đó đúng cái mà `localize.py:675 _anh_xa_zoom_frac` của chính họ **đã
học là sai** (hộp rơi hẳn ra ngoài phải **bị LOẠI**, ⛔ không kẹp về biên, vì
*"kẹp về biên sẽ che nhầm vùng trống nơi chữ đã biến mất"* — bug zoom 2026-07).
Hai chỗ trong cùng một kho, hai luật ngược nhau. Luật của ta là luật L2/L3 của
`vung_che`: **sai thì TỪ CHỐI, hộp ra ngoài thì LOẠI, ⛔ không kẹp.**

### 3.2 ⭐ Vì sao V3 ⛔ KHÔNG được là một `-i` thứ ba

`ket_xuat.dung_lenh:219` nhận đúng hai đầu vào: `-i <video> -i <master>`. Bản
master **đã** được `am_master` chuẩn âm về `LUFS_DICH` và ghim trần đỉnh
(`han_dinh:237`, `ghim_tran_phoi:285`). Trộn nhạc nền **sau** đó là:

- đúng cái `loc_cat_noi:354` cấm — *"trộn hai quyết định âm thanh ở hai chỗ, và
  cái thứ hai sẽ thắng một cách im lặng"*;
- và đúng cái `asv/am_thanh.js` giải thích: `loudnorm` đưa cả bản về `-14 LUFS`
  ⇒ một thanh "âm lượng nhạc nền" đặt **sau** `loudnorm` là **một thanh không làm
  gì** — khách kéo, bản ra ⛔ không đổi.

⇒ Nhạc nền vào **`am_master.bieu_thuc_tron:497`** như một nguồn nữa, **trước**
`loudnorm`, và **`PHIEN_BAN_MASTER` (`am_master.py:55`, đang 3) lên một bậc** —
cùng lý do vân tay như §3.1. `alimiter` của Viral (`xu_ly_video.py:1189`) ta đã
có sẵn ở `am_master.loc_han_dinh:224`.

### 3.3 ⭐ V5 — cái đã chặn `điền nền` là một GIẢ THIẾT SAI

Bảng `DEFER` 08/09 ghi *"OCR hardsub · tự dò logo · xoá bằng điền nền — **chưa
đo VRAM**"*. Đọc mã tham chiếu thì:

| Mảnh | Kỹ thuật thật | VRAM |
|---|---|---|
| tự dò logo tĩnh (`dai_watermark.py:44`) | OpenCV thuần: phương sai theo thời gian + Laplacian + gom thành phần liên thông | **0** — ⛔ không nạp model nào |
| tự dò dải chữ, tầng OpenCV (`dai_sub.py:69`, `:188`) | OpenCV thuần: Laplacian theo hàng + `mean×std` + bó về nét chữ | **0** |
| tự dò dải chữ, tầng OCR (`dai_sub_rapid.py:1914`) | RapidOCR — ta **đã có, đã chốt CPU** (`L_OCR.md` §5) | **0** |
| bám logo di chuyển (`bam_watermark.py:542`) | `cv2.matchTemplate` + RapidOCR **CPU** | **0** — nhưng **106 MB RAM, 0,8 s/lần** (đo trong docstring `:230-238`) |
| điền nền cho **VIDEO** (`che_patch`, `che_keo`) | **ffmpeg thuần**: sao dải sạch lân cận / `crop`+`vflip`+`scale` giãn phủ + hoà mép | **0** |
| điền nền cho **ẢNH** (`xoa_text.py`, LaMa ONNX 512×512) | onnxruntime, và phiên tạo với **`providers=["CPUExecutionProvider"]`** (`:133`) ⇒ cũng **0 VRAM**; ⛔ **chỉ `thumb_tool.py` gọi** | **0** |

🔴 ⇒ **⛔ KHÔNG mảnh nào trong họ này dùng VRAM.** Cái chặn `DEFER` 17 ngày qua
là một **giả thiết ⛔ chưa ai kiểm**. Nên **Đ1 đo CPU + RAM**, ⛔ **không** đo VRAM.

⚠️ Nhưng ⛔ **vẫn ĐO trước, ADR sau** — bốn con số còn chưa biết: ms/khung dò, số
khung phải dò để đạt tỉ lệ dò, **RAM cộng dồn khi nhiều lượt chạy song song** (ta
có nhiều làn worker, Viral chỉ có 3 và đã phải đặt một khoá toàn cục `_OCR_KHOA`),
và **chi phí một lần giải mã thêm** nếu chặng dò ⛔ không dùng lại được khung mà
`canh.py` đã trích.

⭐ Đây đúng họ lỗi `hai-trang-thai-gop-thanh-mot-gia-tri`: *"chưa đo VRAM"* và
*"VRAM bằng 0"* đã bị gộp thành một chữ `DEFER`, và ⛔ không ai phân biệt được
chúng cho tới khi có người **đọc mã tham chiếu**.

🔴 **Và LaMa là loại C — vì giấy phép.** Model card `Carve/LaMa-ONNX` tự khai
`license: apache-2.0`, nhưng đó là **bản port**; trọng số thượng nguồn là
`big-lama` của `saic-mdal/lama`. Một bản port **⛔ không rửa được** giấy phép
trọng số thượng nguồn. Đây đúng ca `OPEN_SOURCE_METRIC_AUDIT.md` đã phán quyết
một lần (EasyOCR bị loại vì *"weights chưa xác minh"*).
⇒ **Đ1 phải trả lời giấy phép `big-lama` trước khi ai chạm vào LaMa.** ⛔ Không
trả lời được ⇒ dùng `che_keo` (ffmpeg, 0 trọng số) và `cv2.inpaint` (Telea,
OpenCV Apache-2.0, 0 trọng số) — và **thế là đủ cho video**.

### 3.4 ⭐ Ba BẤT BIẾN của `che_keo` — Viral đã trả giá, ta ⛔ đừng trả lại

| Bất biến | Nguồn | Hậu quả nếu bỏ |
|---|---|---|
| Dải nguồn dày **SỐ CHẴN ≥ 2 px** | `localize.py:6110 _chan2` — chuỗi chạy sau `format=yuv420p`, chroma lấy mẫu **2:1 theo DỌC** ⇒ dải 1 px cho **0 hàng** chroma | `[Parsed_crop] Invalid too big or non positive size … height '0'` ⇒ ffmpeg chết `-22` ở **cả** `h264_nvenc` **lẫn** `libx264`. Đo thật 5 tổ hợp: `hs=1` LỖI · `hs=2` OK · `hs=8` OK |
| **Chừa chỗ** cho dải nguồn, và **chỉ ở bên thật sự lấy nguồn** | `localize.py:7842-7846` + `:7856-7860` | Nới hết chỗ ⇒ crop nguồn rơi ra ngoài khung ⇒ ffmpeg chết. Mà chừa **cả hai bên vô điều kiện** cũng sai: dải sát đáy ⛔ không có nguồn dưới mà vẫn bị trừ ⇒ lõi đục **hụt 3 px ở đáy — đúng chỗ chữ nằm** |
| Vùng hoà mép nằm **HẲN NGOÀI** dải chữ | `localize.py:7840-7841` | *"Tan ăn vào trong = LỘ CHỮ"* |
| 🔴 ⛔ **KHÔNG có đường lùi im lặng** | `_da_che_keo` (`localize.py:6588, 7800, 8517`) của Viral lùi về **làm mờ** khi ffmpeg chết ⇒ *"khách chọn Kéo mép nhận về Làm mờ, tốn 2 lượt ffmpeg vô ích, và KHÔNG có gì báo cho khách"* | Ở ta: **⛔ không lùi**. Hình học không dựng được ⇒ `BanDungError` **trước khi** gọi ffmpeg, câu bốn dòng cho khách (`loi.py`). Đây là đúng họ lỗi im lặng §3.1 |

### 3.5 ⭐ Hai bất biến nữa cho V4 — Viral làm ĐÚNG, ta chép

| Bất biến | Nguồn | Vì sao quan trọng với ta |
|---|---|---|
| 🔴 **"⛔ không có gì ở đó" ≠ "⛔ không đo được"** | `dai_sub_rapid` **ném `LoiKyThuat`** khi hỏng về kỹ thuật, nhưng **trả `None` + `chac=True`** khi đã quét thật và kết luận *video ⛔ không có hardsub* | Đúng bài học `hai-trang-thai-gop-thanh-mot-gia-tri` trong sổ ta. ⛔ Một bộ dò trả `[]` cho **cả hai** ca là một bộ dò **mất khả năng phân biệt** — và cái mất ⛔ không báo lỗi, nó chỉ ⛔ không tồn tại |
| **Vùng khách tự vẽ THẮNG vùng tự dò** | `localize.py:809 _vung_tranh_y` → trả cặp phân số `(y/H, (y+h)/H)`, ⛔ không bao giờ ném (`[]` khi hỏng) · `dai_sub.py:175 _trung_vung_tay` **loại** dải tự dò nào chồng lên vùng khách đã vẽ | 🔑 Đây là chỗ `danh_dau_phu_de` **nghĩa ÂM** của ta (§2) gặp V4: khi V4 sống, một dải tự dò chồng lên `danh_dau_phu_de` phải **bị LOẠI**, ⛔ không phải "nhường một nửa". ⚠️ Và ⛔ **đừng** vì có V4 mà đổi nghĩa `danh_dau_phu_de` thành "che dải sub gốc" — hai khái niệm, hai trường |

⛔ Một thứ Viral làm mà ta **⛔ không chép**: `xu_ly_chon.py:299 _doc_dai` — toạ độ
`x` sai định dạng **âm thầm tụt** về dạng 2 số `(y0,y1)` thay vì từ chối. Cố ý ở
họ (giữ được mặt nạ tay của khách), nhưng nó phá luật L2 của `vung_che` ta: *"sai
thì TỪ CHỐI, ⛔ không kẹp về biên — một cửa sổ bị sửa hộ là một cửa sổ khách ⛔
không vẽ"*.

---

## 4. LÀN — mỗi làn một worktree + một nhánh, ⛔ không hai làn một tệp

🔴 **Hai làn ĐANG SỐNG, ⛔ chừa tệp của họ ra:**

| Làn đang sống | Sở hữu | ⛔ Làn mới ⛔ không chạm |
|---|---|---|
| `asv-gui` | **toàn bộ lớp giao diện** ASV: `apps/auto_scan_video/templates/*.html`, `server/static/asv/*.js`, `server/static/ltt.css`, handler UI trong `routes.py` | mọi tệp trên |
| `asv-g17` | `tests/test_448_asv_v4_e2e_nghiem_thu.py` + đường nghiệm thu | tệp trên |

### Bảng làn đề xuất

| Làn | Nhánh | Hạng mục | 🔑 Tệp làn này SỞ HỮU (⛔ không ai khác ghi) | Song song được ngay? |
|---|---|---|---|---|
| **`asv-hinh`** | `phien/asv-hinh` | **V1 + V2** (lật gương · dịch màu) | `apps/auto_scan_video/bien_tap.py` · `hinh_hoc.py` · `che_do_render.py` · `ban_dung.py` · ⭐ **`tests/test_2062_asv_bien_tap_engine.py`** (đã có — **mở rộng**, ⛔ đừng tạo tệp thứ hai cho cùng cụm) | ✅ **ĐỘC LẬP** — bắt đầu ngay |
| **`asv-nhac`** | `phien/asv-nhac` | **V3** (nhạc nền) | `apps/auto_scan_video/am_master.py` · `am_thanh.py` · `assets.py` · `ket_xuat.py` · tệp test mới trong **dải của cây** (`cay_rieng.py tao` in ra dải; ⛔ đừng gõ số tay) | ✅ **ĐỘC LẬP** — bắt đầu ngay (⛔ không giao nhau tệp nào với `asv-hinh`) |
| **`asv-do-vung`** | `phien/asv-do-vung` | **Đ1** (hạng mục ĐO) | `tools/bench_do_vung.py` (mới) · `docs/auto_scan_video_final/L_DO_VUNG.md` (mới) | ✅ **ĐỘC LẬP** — bắt đầu ngay; ⛔ **không sửa `apps/`** |
| **`asv-vung2`** | `phien/asv-vung2` | **V4a + V4b + V5** (tự dò tĩnh · dò dải chữ · điền nền) | `apps/auto_scan_video/do_vung.py` (mới) · `vung_che.py` · và **`che_do_render.py` — SAU khi `asv-hinh` gộp `main`** | ⛔ **KHÔNG** — xem dưới |
| *(chưa cấp)* | — | **V4c** (logo di chuyển) | — | ⛔ **CHƯA GIAO** — chỉ mở nếu Đ1-③ nói RAM/khoá chịu được. Ghi ở đây để ⛔ không ai tưởng đã bỏ |
| `asv-gui` *(đang sống)* | — | **V6** (kéo-thả logo) + phơi V1/V2/V3 ra UI | lớp giao diện (bảng trên) | ✅ V6 ngay; UI của V1/V2/V3 **sau** khi làn engine gộp |
| `asv-gia` *(mới, 25/09)* | — | giá phẳng **10 credit/phút video** | `apps/auto_scan_video/gia.py` | ✅ **ĐỘC LẬP về tệp** — nhưng xem §4.1 (xung đột **ngữ nghĩa**) |
| `asv-toc-do` *(mới, 25/09)* | — | `job_runner` · `edit_plan` song song · `N-46` jitter | `platform_core/job_runner.py` · `leases.py` · `apps/auto_scan_video/canh.py` · `thi_hanh.py` · `pipeline.py` | ✅ **ĐỘC LẬP** — `canh.py` ⛔ không import `che_do_render`/`ban_dung`/`ket_xuat` (đã `grep`) |

### 4.1 🔴 `asv-gia` — ĐỘC LẬP về TỆP, ⛔ KHÔNG độc lập về NGHĨA

`gia.py` import **đúng một** thứ: `platform_core.i18n` (⛔ không `bien_tap`, ⛔ không
`che_do_render`, ⛔ không `ban_dung`) ⇒ ⛔ **không** xung đột merge với làn nào.

⚠️ **Nhưng bốn làn engine đều THÊM năng lực tính tiền được**, và cả bốn, theo bản
năng, sẽ mở `gia.py` để đặt giá cho việc mới. ⇒ Đúng ca
`lan-song-song-xanh-rieng-do-khi-gop`: *luật một-tệp-một-chủ ngăn xung đột
**merge**, ⛔ không ngăn xung đột **ngữ nghĩa***.

🔑 **Và giá phẳng 10 credit/phút thực ra GỠ nút thắt ấy** — đó là tin tốt, nhưng
chỉ nếu nói to: giá ⛔ **không** còn là hàm của *tập thao tác*, nó là hàm của **độ
dài video**. ⇒ Ba hệ quả **bắt buộc**:

1. ⛔ **`asv-hinh` · `asv-nhac` · `asv-vung2` ⛔ KHÔNG mở `gia.py`.** Thêm
   `lat_guong`/`dich_mau`/`nhac_nen`/`dien_nen` **⛔ không đổi giá**. `gia.py` thuộc
   **một chủ duy nhất: `asv-gia`**.
2. **`asv-gia` đi TRƯỚC** trong hàng đợi gộp `main` — vì nếu nó gộp **sau**, nó sẽ
   phải xoá các nhánh giá mà ba làn kia vừa thêm, và mỗi lần xoá là một cơ hội
   **bỏ sót một nhánh** (sổ credit, luật 9 `CLAUDE.md`).
3. ⚠️ Nhưng V1/V2/V5 đổi preset từ `sao_chep` sang `cat_ma_hoa_lai` cho những lượt
   trước đây ⛔ không cần mã hoá lại ⇒ **chi phí máy thật tăng** trong khi **giá
   phẳng ⛔ không tăng**. Đó ⛔ **không** phải việc của plan này, nhưng nó là một
   **câu hỏi cho `asv-gia`**, và nó phải được ghi ở đó thay vì phát hiện lúc xem
   hoá đơn điện.

### ⭐ Thứ tự phụ thuộc — chỗ nào THẬT SỰ độc lập

```
KHOI DONG ngay, NAM lan song song (khong lan nao doi lan nao):
   ⇢ asv-gia     (gia phang)   <-- GOP `main` TRUOC ba lan engine (§4.1 muc 2)
   ⇢ asv-hinh    (V1+V2)
   ⇢ asv-nhac    (V3)
   ⇢ asv-do-vung (D1 - do, KHONG sua apps/)
   ⇢ asv-toc-do  (job_runner · edit_plan · N-46)

   asv-hinh gop `main`  ─────────────────┐   (nha `che_do_render.py`)
   D1 tra SO + phan quyet giay phep ─────┤
                                         ▼
                               asv-vung2 (V4a+V4b+V5)
                                         │
                                asv-gui phoi ra UI
```

**Hai lý do `asv-vung2` phải chờ, và ⛔ chỉ hai:**

1. **Xung đột tệp**: V5 sửa `che_do_render.py` (thêm loại vùng thứ hai) — cùng tệp
   `asv-hinh` sửa cho V1/V2. Luật một-tệp-một-chủ ⇒ **tuần tự**. ⛔ Đừng "chia
   theo hàm" — đây đúng ca `so-dang-ky-dung-chung-la-cho-cac-lan-va-nhau`: cả hai
   khai một điều về **`PHIEN_BAN_CHE_DO`**, tức về **cả hệ**.
2. **Chưa có số**: gỡ `DEFER` cho V4/V5 mà chưa có Đ1 là đúng cái §3.3 vừa bắt
   được — một `DEFER` dựa trên giả thiết ⛔ không đo.

⚠️ `asv-hinh` và `asv-nhac` **⛔ không** giao nhau tệp nào (`che_do_render.py` vs
`am_master.py`), nhưng **cả hai tăng một số phiên bản vân tay** (`PHIEN_BAN_CHE_DO`
vs `PHIEN_BAN_MASTER`) — **hai số khác nhau, hai tệp khác nhau** ⇒ thật sự song
song. ⛔ Nếu một làn phải sửa số của làn kia thì **dừng và báo điều phối**.

⚠️ **`asv-nhac` ↔ `asv-toc-do`**: `asv-nhac` sở hữu `ket_xuat.py`, `asv-toc-do` sở
hữu `thi_hanh.py`/`pipeline.py`. Hai tệp khác nhau, nhưng `thi_hanh.chay_giai_doan`
là **người gọi** `giai_doan_ket_xuat` ⇒ nếu `asv-toc-do` đổi **chữ ký** hay **thứ
tự giai đoạn**, `asv-nhac` đỏ khi gộp. ⇒ `asv-toc-do` đổi song song **bên trong**
một giai đoạn thì an toàn; đổi **ranh giới giữa các giai đoạn** thì **báo trước**.

---

## 5. NGHIỆM THU — mỗi hạng mục một PHÉP KIỂM. ⛔ "làm xong" ⛔ không phải tiêu chí

⛔ **Không mốc thời gian. Điều kiện.**

| # | ⛔ Chưa xong khi chưa có |
|---|---|
| **V1** | ① `bien_tap.chuan_hoa` **từ chối** `lat_guong` ⛔ không phải bool, và hồ sơ THƯA ⛔ không ghi `lat_guong=False`. ② 🔴 **Phép kiểm vân tay**: `van_tay_che_do(bien_tap={"lat_guong":True})` ≠ `van_tay_che_do(bien_tap={})` — và cùng phép kiểm đó **đỏ** nếu ai gỡ `bien_tap` khỏi vân tay. ③ `PHIEN_BAN_CHE_DO` **đã tăng**, có phép kiểm chốt nó ≠ 7. ④ `ban_dung.kiem` **ném** cho bản dựng vừa `sao_chep` vừa có `lat_guong` (cùng luật vật lý với `mask_region`). ⑤ Chuỗi lọc sinh ra có `hflip` **trong chặng KHUNG**, ⛔ **không** trước `che`, ⛔ **không** sau `logo` — chốt bằng **thứ tự chuỗi**, ⛔ không chỉ "có mặt". ⑥ **Một lượt ffmpeg THẬT** trên clip ngắn: khung ra là ảnh lật của khung vào (so pixel ở hai mép), và **logo ⛔ KHÔNG bị lật** |
| **V2** | ①–④ y hệt V1 cho `dich_mau`. ⑤ Chuỗi có `eq=saturation=1.12` và ⛔ **không** có `contrast`/`brightness`/`gamma` — chốt bằng phép kiểm **vắng mặt**, vì giá trị Viral (`xu_ly_config.json:13`) có **ba** trục và cái dễ xảy ra nhất là chép cả ba. ⑥ **Một lượt ffmpeg THẬT**: bão hoà trung bình khung ra **cao hơn** khung vào, và **độ sáng trung bình ⛔ KHÔNG đổi** ngoài nhiễu lượng tử — đây là phép kiểm phân biệt "mở một trục" với "chép cả ba" |
| **V3** | ① Hồ sơ nhạc nền **vắng mặt** khi khách ⛔ không tải nhạc. ② `PHIEN_BAN_MASTER` **đã tăng**, có phép kiểm chốt. ③ Vân tay master **đổi** khi đổi `khoa` nhạc hoặc `am_luong_nen`. ④ 🔴 **Phép kiểm chống "thanh kéo không làm gì"**: hai lượt cùng nhạc, khác `am_luong_nen` ⇒ **hai tệp ra KHÁC BYTE** (đúng cái `asv/am_thanh.js` cảnh báo). ⑤ **Ca video CÂM**: bản ra dài **đúng** bằng video (bẫy `apad`, `xu_ly_video.py:1199`). ⑥ **Ca nhạc NGẮN hơn video** và **DÀI hơn video** — cả hai ra đúng độ dài, trong `DUNG_SAI_DO_DAI_S`. ⑦ Bản ra ⛔ **không clip**: `han_dinh` đo đỉnh thật ≤ `DINH_THAT_DB`. ⑧ Tệp nhạc đi qua **đường `assets`** có kiểm quyền sở hữu + trần kích thước (Cloudflare 100 MB) |
| **V4a/b** | ① Trên bộ **≥ 4 clip thật** của chủ dự án (`Desktop\TEST VIDEO`, cùng bộ `L_OCR.md` dùng): **tỉ lệ dò đúng** + **tỉ lệ báo động giả**, ⛔ không một con số. ② 🔴 **SÀN MAY RỦI**: so với "đoán một hộp ở góc phải trên" (V4a) và "đoán dải 12 % dưới cùng" (V4b) — ⛔ không hơn sàn ⇒ ⛔ **không phát hành**. ③ Ca **⛔ KHÔNG có logo / ⛔ KHÔNG có hardsub** ⇒ 🔴 phân biệt được **"đã quét, ⛔ không có"** với **"⛔ chưa quét được"** (§3.5) — hai giá trị trả về **KHÁC NHAU**, có phép kiểm cho từng ca. ④ Dải tự dò chồng `danh_dau_phu_de` ⇒ **bị LOẠI** (§3.5). ⑤ Đề xuất ra là **phân số 0..1**, đi qua `vung_che.chuan_hoa` ⛔ không bị từ chối |
| **V4c** | Hoặc dò đúng logo **di chuyển** theo thời gian, hoặc 🔴 **khai thẳng là ⛔ KHÔNG hỗ trợ** — ⛔ tuyệt đối không im lặng trả một hộp **tĩnh** cho một logo động (khách trả tiền cho một lượt render che nhầm chỗ). Có phép kiểm cho chính ca này |
| **V5** | ① `_chan2`: dải nguồn dày **1 px** hoặc **3 px** ⇒ **từ chối ở `kiem`**, ⛔ không tới ffmpeg (⭐ **3 px** là ca chia-lẻ Viral dặn *"đừng để lọt"*). ② Dải **sát đáy** / **sát đỉnh** khung ⇒ dựng được hoặc từ chối rõ ràng, ⛔ **không** ffmpeg `-22`. ③ 🔴 **⛔ KHÔNG đường lùi**: phép kiểm chốt rằng ⛔ **không** nhánh nào đổi `dien_nen` thành `lam_mo` — **đây là phép kiểm quan trọng nhất của V5**. ④ **Một lượt ffmpeg THẬT**: vùng điền nền ⛔ **không còn** chữ gốc (OCR trên khung ra trả rỗng ở vùng đó) và ⛔ **không** là một ô mờ (phương sai cục bộ **cao hơn** ca `lam_mo`). ⑤ `PHIEN_BAN_CHE_DO` tăng + vân tay phân biệt `lam_mo` vs `dien_nen` |
| **Đ1** | ① **ms/khung** của V4a (`dai_watermark`) và V4b (`dai_sub`) trên **CPU**, cùng khuôn `L_OCR.md` §5 (4 luồng, venv đo lường), 3 lượt mỗi bên, kèm **phương sai**. ② Số **khung phải dò** để đạt tỉ lệ dò ở V4-① — ⭐ và trả lời câu `VIRAL_RENDER_FEATURE_MAP.md` §4.1 đã trả giá: *"một phép dò lấy mẫu THƯA trên nội dung NGẮT QUÃNG là một phép tung đồng xu"* (`_han_tren_hinh` nâng `n_frames` **6 → 20**, `min_box=3`, sau ca khách treo 34 phút). ③ 🔴 **RAM cộng dồn** khi N lượt chạy song song (Viral chỉ 3 làn mà đã phải đặt khoá toàn cục `_OCR_KHOA`; đo của họ: 1 instance = 106 MB / 66 luồng, 5 instance = 246 MB / **198 luồng**) — trả lời *ta cần một khoá hay không*. ④ **Chi phí giải mã/encode thêm**, hoặc chứng minh dùng lại được khung `canh.py` đã trích. ⑤ 🔴 **Phán quyết giấy phép `big-lama`**, trích **nguồn thượng nguồn** (⛔ không trích model card bản port `Carve/LaMa-ONNX`) — theo thang `OPEN_SOURCE_METRIC_AUDIT.md`. ⑥ Kết luận viết dạng bảng `GPU_MAY_A.md` §2: *chuyển được? · chi phí · đáng?* — và ⛔ **cột VRAM ghi `0` kèm lý do**, ⛔ không để trống (§3.3) |
| **V6** | thuộc `asv-gui` — nghiệm thu bằng **trình duyệt thật trên `https://app.lttstudios.com`** (`CLAUDE.md` luật 7): kéo logo, thả, `POST` mang `x`/`y` **phân số**, console ⛔ không lỗi, 375×812 ⛔ không tràn ngang |

### ⭐ Hai luật nghiệm thu áp cho MỌI hàng trên

1. **Một lượt ffmpeg THẬT là bắt buộc** cho V1, V2, V3, V5. `test_457` đã chốt
   *chuỗi lọc*; ⛔ một chuỗi lọc đúng ⛔ không chứng minh tệp ra đúng
   (`V5_IMPLEMENTATION_STATUS.md` §5: *"hai lỗi mà bộ test ⛔ KHÔNG thấy, và trình
   duyệt thấy"*). Lượt ffmpeg là **lệnh nặng** ⇒ qua `chay_nang.py`, và **nhả
   khoá ngay khi lệnh tính xong**.
2. **Mọi mục gỡ một cờ phải có phép kiểm ĐỐI CHỨNG**: cờ còn nguyên ⇒ phép kiểm
   **đỏ**. ⛔ Không có nó thì `hop_dong_v4._kiem_tra_hop_dong:237` là *"đo vắng
   mặt — xoá cũng xanh"* (`banh-coc-cong-chat-luong`).

---

## 6. ADR-V5 — MỘT tệp, năm mục, ⛔ không năm tệp

`docs/auto_scan_video_v5/ADR_V5.md` (nâng `ADR_V5_DRAFT.md`). `V5_IMPLEMENTATION_STATUS.md`
§3 đã nói cách mở: *"ký một ADR-V5 + bật cờ, ⛔ không phải thiết kế lại."*

| Mục | Quyết định | 🔑 Cái GIÁ phải ghi ra (⛔ đừng ghi ADR một chiều) |
|---|---|---|
| §V1 | mở `lat_guong` | Mục đích Viral dùng nó là **né nhận dạng trùng**. Ta bán nó là **biên tập** ⇒ ⛔ giao diện phải nói ý định đó, ⛔ không đặt cạnh một chữ "né trùng" nào |
| §V2 | mở `dich_mau`, **chỉ trục `saturation`** (`1.12` — đúng giá trị Viral dùng) | Giá trị Viral (`xu_ly_config.json:13`) có **ba** trục: `contrast=1.06`, `brightness=0.03`, `saturation=1.12`. ⛔ Mở cả ba (hay bốn, như `_fingerprint_eq`) là dựng lại công cụ né vân tay **bằng tay khách** — chỉ khác là ta ⛔ không gọi nó bằng tên đó nữa. ⇒ ADR phải ghi **vì sao hẹp lại**, và §5 V2-⑤ là phép kiểm thi hành |
| §V3 | **gỡ `music_replace` khỏi `CAM_TRONG_MVP`** | 🔴 **Bản quyền nhạc.** Khách tải nhạc lên và ta xuất bản nó ⇒ ta thành đường phân phối. Cần: điều khoản khách xác nhận quyền + `assets` giữ **ai tải, lúc nào**. ⛔ ADR ⛔ không được ký mà bỏ dòng này |
| §V4 | mở tự dò **sau Đ1** | Một đề xuất **sai** tệ hơn ⛔ không đề xuất: khách tin nó, che nhầm, và trả tiền cho một lượt render sai. ⇒ Phải có **sàn may rủi** (§5 V4-②) |
| §V5 | mở `dien_nen` bằng **`che_keo` (ffmpeg)**; LaMa **loại C** cho tới khi giấy phép `big-lama` được xác minh | ⛔ Không đường lùi im lặng (§3.4) |

⛔ **Chưa ký ADR ⇒ ⛔ chưa gỡ cờ.** `hop_dong_v4._kiem_tra_hop_dong:237` là cơ
học thi hành điều đó, và §2 của `hop_dong_v4` đã ghi luật *"một mục rời khỏi bảng
là một quyết định sản phẩm, và nó cần một ADR."*

---

## 7. Sổ cái — tiếp `N-55`

| N | Mục | Làn |
|---|---|---|
| 🔴 `N-56` | **Bánh cóc gác ở `commit` ⛔ không gác được `merge`** — xem §9 | điều phối |
| `N-57` | V1 lật gương + vân tay + `PHIEN_BAN_CHE_DO` | `asv-hinh` |
| `N-58` | V2 dịch màu (chỉ `saturation`) | `asv-hinh` |
| `N-59` | V3 nhạc nền vào `bieu_thuc_tron` + `PHIEN_BAN_MASTER` | `asv-nhac` |
| `N-60` | Đ1 đo dò vùng (**CPU + RAM**, ⛔ không phải VRAM) + phán quyết giấy phép `big-lama` | `asv-do-vung` |
| `N-61` | V4a tự dò logo TĨNH (`dai_watermark`) | `asv-vung2` |
| `N-62` | V4b tự dò DẢI CHỮ (`dai_sub`) + phân biệt *⛔ không có* / *⛔ chưa đo được* | `asv-vung2` |
| `N-63` | V5 điền nền (`che_patch`/`che_keo`) + ⛔ KHÔNG đường lùi | `asv-vung2` |
| `N-64` | V6 kéo-thả vị trí logo (UI) | `asv-gui` |
| `N-65` | ADR-V5 năm mục | làn nào ký mục nào thì ghi ở đó |
| `N-66` | V4c logo di chuyển — ⛔ **chưa giao**, chờ Đ1-③ | — |

---

## 8. ⚠️ Ghi chú pháp lý — một đính chính với tệp cũ

`VIRAL_RENDER_FEATURE_MAP.md` §0 (08/09) ghi: *"quyết định tối đa được phép là
hiểu hành vi → viết đặc tả → viết lại sạch. ⛔ Không sao chép nguyên văn một dòng
nào"*, dựa trên `D:\Viral\README.md` khai `UNLICENSED`.

🔑 **Chủ dự án chốt 25/09: `D:\Viral` THUỘC chủ dự án** ⇒ ràng buộc ấy **⛔ không
còn áp** cho mã Viral. Lấy mã thoải mái.

⛔ **Ngoại lệ DUY NHẤT, vẫn nguyên:** `resources/app-src/MediaCrawler/` là fork
`NanmiCoder/MediaCrawler`, giấy phép **phi thương mại**, quyền ⛔ **không** thuộc
chủ dự án ⇒ ⛔ không lấy gì từ đó. Ta đã có `apps/video_crawler`.

⚠️ Và điều §0 nói về **trọng số model** thì **vẫn đúng** và ⛔ không liên quan tới
ai sở hữu Viral: quyền của `big-lama` (§3.3) thuộc thượng nguồn, ⛔ không thuộc
chủ dự án, ⛔ không thuộc bản port.

⛔ `D:\Viral` là **CHỈ ĐỌC**: ⛔ không sửa, ⛔ không chạy `.exe`/`.bat` trong đó.

---

## 9. 🔴 CHẶN NGAY BÂY GIỜ — bánh cóc `ruff` trên `main` lệch 1, mọi làn ⛔ không commit được

Tìm ra khi làn này commit **một tệp `.md` duy nhất** và vẫn bị chặn:

```
banh coc ruff (chi do khi TANG) ... Failed
[ruff] TANG so voi moc:  F401  408 -> 409
```

| | |
|---|---|
| **Thủ phạm** | `tests/test_3800_asv_gui_ban_giao_va_thanh_hanh_dong.py:28` — `import pytest` ⛔ không dùng |
| **Vào `main` lúc nào** | `9d6d8d31` (25/09, làn `asv-gui`), gộp ở `cd8a5a60` |
| **Mốc** | `tools/check_ruff.moc:13` → `F401 = 408`, đặt `d82d120e` (16/09). Cây `main` hôm nay: **409** |
| **Sửa** | xoá đúng dòng 28. ⇒ **Việc của `asv-gui`** (chủ tệp), ⛔ không phải của làn này |

### ⭐ Vì sao một lỗi lint lọt được lên `main` — và đây là phần đáng ghi

`banh-coc-ruff` là hook **`pre-commit`**. `git merge --ff-only` ⛔ **không tạo
commit** ⇒ ⛔ **không chạy hook nào**. Nên đường gộp `main` mà hợp đồng §7 quy
định (`merge --ff-only`) là một đường **⛔ không có cổng lint**: một lượt commit
trên nhánh phiên có thể xanh ở cây đó rồi lên `main` làm bánh cóc lệch.

🔴 **Và hậu quả đắt hơn chính lỗi:** bánh cóc đo **TOÀN KHO**, ⛔ không đo tệp
đang commit (`.pre-commit-config.yaml:54-57` nói rõ, có chủ đích). ⇒ **một** dòng
`import` thừa ở một tệp chặn **mọi commit của mọi làn** — kể cả commit chỉ sửa
tài liệu. Bốn làn của plan này đều bị chặn cho tới khi dòng đó được xoá.

⛔ **⛔ ĐỪNG `--accept`.** `--accept` ghi mốc lên **409**, tức **vĩnh viễn cấp
phép thêm một import thừa** cho cả kho. Đó là bánh cóc **trôi ngược**, và nó im
lặng — đúng cái `banh-coc-cong-chat-luong` cảnh báo. Sửa một dòng, ⛔ đừng hạ cổng.

⇒ **Đề xuất cho điều phối:** giao `asv-gui` xoá dòng 28 (tệp của họ, một token,
⛔ không đổi nghĩa phép kiểm nào — `pytest` ⛔ không được dùng trong tệp), rồi mọi
làn commit lại được. Và cân nhắc một việc riêng: **cổng lint cho đường gộp
`main`** (hook `post-merge` hoặc một bước trong `gate.py`), vì lỗ này sẽ lặp.

### 9.1 🔴 `N-56` — bánh cóc gác ở `commit` ⛔ KHÔNG gác được `merge`

⭐ **Đã gỡ chặn**: `875131f2` xoá dòng đó. Nhưng cái **lỗ** thì vẫn còn, nên nó
vào sổ cái.

```
Banh coc `ruff` gac o:   pre-commit   (hook cua GIT COMMIT)
Duong viec vao `main`:   merge --ff-only   (KHONG tao commit)
                         ⇒ LO dung ngay cho viec that su HA CANH
```

Ba tính chất cộng lại mới thành sự cố, và ⛔ đừng nhớ thiếu một cái:

| | |
|---|---|
| Cổng gác ở **commit** | `merge --ff-only` ⛔ không tạo commit ⇒ ⛔ không chạy hook nào |
| Cổng đo **TOÀN KHO**, ⛔ không đo tệp đang commit | `.pre-commit-config.yaml:54-57` — **có chủ đích** (một commit chỉ sửa `ruff.toml` cũng phải bị đo) |
| ⇒ **một** vi phạm lọt qua chặn **MỌI làn** | làn `asv-plan` bị chặn khi commit **một tệp `.md` duy nhất** |

**Thuốc** (chọn một, ⛔ không phải cả hai): `pre-commit run --all-files` **sau mỗi
lần gộp `main`**, hoặc một móc `post-merge`. ⇒ **Việc riêng, ⛔ không nhét vào làn
nào ở §4.**

⭐ **Và hai điều ⛔ KHÔNG được làm khi bị chặn kiểu này:**

1. ⛔ **Đừng sửa tệp của làn khác** — dù chỉ một token. Luật một-tệp-một-chủ tồn
   tại **đúng cho lúc bất tiện**; nó ⛔ không có ngoại lệ "vì tôi đang gấp".
2. 🔴 ⛔ **Đừng `--accept`.** `--accept` ghi mốc `408 → 409`, tức **cấp phép vĩnh
   viễn** thêm một import thừa **cho cả kho** để đổi lấy việc đi tiếp **năm phút**.
   **Một bánh cóc được nới mỗi lần nó vướng thì ⛔ không còn là bánh cóc** — nó là
   một con số đi theo hiện trạng. Báo lên, chờ chủ tệp sửa. Ta chờ đúng một lượt.

### 9.2 🔴 Bài học lớn hơn — *"chặn bởi X"* phải ghi **AI đo X** và **KHI NÀO**

Dòng `| OCR hardsub · tự dò logo · điền nền | chưa đo VRAM |` sống trong
`V5_IMPLEMENTATION_STATUS.md` §3 từ **08/09**, được chép lại vào brief của **hai**
làn trong phiên 25/09, và **cả hai lần đều được dùng để từ chối mở hạng mục**.

Nhưng §3.3 tệp này cho thấy: **⛔ không mảnh nào chạm VRAM.** OpenCV thuần, ffmpeg
thuần, và LaMa còn **tự ghim `providers=["CPUExecutionProvider"]`**.

🔑 ⇒ **⛔ Chưa ai đọc mã để xem nó có chạm VRAM hay ⛔ không.** Một lý do hoãn được
chép đi chép lại suốt **17 ngày**, qua **ba tệp**, mà ⛔ không ai kiểm.

> ⭐ **Luật:** một dòng *"chặn bởi X"* phải ghi **ai đo X** và **ngày đo**.
> ⛔ Không có hai thứ đó thì nó ⛔ **không phải một phép đo** — nó là **một tin đồn
> có định dạng bảng**, và định dạng bảng làm nó trông như đã được kiểm.

⚠️ Và nó **ăn khớp** với §1: cả hai lỗi cùng một họ — **đọc một BẢN KIỂM KÊ thay
vì đọc MÃ**. §1 mất 6 hạng mục *tưởng còn thiếu*; §9.2 mất 17 ngày của *một hạng
mục tưởng bị chặn*. ⇒ Đó là lý do §1 đặt luật: **mỗi hạng mục mang một ô bằng
chứng `file:dòng` trên `main`.** Luật này áp cho **cả cột "chặn bởi"**, ⛔ không
chỉ cột "đã có".
