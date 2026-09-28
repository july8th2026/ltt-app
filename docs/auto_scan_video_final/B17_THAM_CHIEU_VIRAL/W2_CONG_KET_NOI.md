# W2 — CỔNG KẾT NỐI: kiểm kê MỌI đường truyền dữ liệu giữa các bước của Viral

**Ngày:** 2026-09-28 · **Làn:** W2 (plan B17) · **Nguồn:** `D:\Viral\resources\app-src`
(chỉ đọc, ⛔ không chạy gì) · **Phía ta:** `apps/auto_scan_video/`

**Câu hỏi của tệp này — một câu:** Viral là **MỘT tiến trình**, nên nó truyền dữ liệu
giữa các bước qua biến. Ta là **8 job, 8 tiến trình**. ⇒ **Mỗi** đường truyền ấy phải
thành một **artifact** hoặc một trường **`outputs`** tường minh. Bỏ sót một cái là một
giai đoạn im lặng ⛔ không nhận được gì — và nó ⛔ **không nổ**, nó cho **kết quả sai**.

Số giai đoạn trong cột `⇒ ở TA` theo **chuỗi 8 giai đoạn của B16**:
`1 media_prepare · 2 audio_prepare · 3 transcribe · 4 vung_che · 5 content_process ·
6 voice_synthesis · 7 timing_align · 8 render`.

---

## 0. ĐỘ PHỦ — bằng SỐ

| đại lượng | số | cách đếm (⛔ không dựa vào trí nhớ) |
|---|---|---|
| **Side-channel toàn cục** `globals()["X"] = …` trong `localize.py` | **12** tên | `grep -o 'globals()\["[A-Za-z0-9_]*"\] *='` → 12 tên riêng biệt |
| — trong đó khối reset đầu `chay()` (`:15039-15318`) liệt kê | **8** | 7 `globals()` + `_VC_SPEED`; 4 tên còn lại reset ở chỗ khác hoặc **cố ý không reset** |
| **Container mutable cấp module** dùng làm kênh | **16** | `grep -n '^_[A-Z][A-Z_0-9]* *= *(\[|{)'` (đã loại hằng bảng-từ/bảng-codec) |
| **Reset xuyên module** ở đầu `chay()` | **6** lời gọi | `chat_luong.dat_lai` `:15044` · `capcut_tts.dat_lai` `:15051` · `phu_de.reset_gpu_moi_job` `:15293` · `xu_ly_video.reset_encoder_moi_job` `:15302` · `_TTS_SOM[0]=None` `:15157` · `_MOC_AUDIO.clear()` `:15325` |
| **Biến môi trường ĐỌC** (tên riêng biệt) | **401** | `grep -o 'os.environ.get("…"'` → `sort -u`. 598 lượt đọc. Nhóm: `CHE_*` 108 · `DUB_*` 68 · `VC_*` 29 · `ASR_*` 21 · `OCR_*` 14 · `EDGE/WHISPER/GEMINI/GEM` 41 · còn lại 120 |
| **Biến môi trường GHI bởi `localize.py`** | **15** | 🔑 **Đây mới là đường TRUYỀN.** 386 tên còn lại là **cấu hình một chiều** (chỉ đọc) |
| **Tệp trung gian trong thư mục làm việc** | **21** | 12 biến thể `.srt` · 7 `.wav` · 2 `.mp4` (§3) |
| **Hậu tố cache liên-lần-chạy** | **7** | `.zh.srt` `.vi.srt` `.band.json` `.boxes.json` `.ocrbox.json` `.dub.wav` `.dubmeta.json` |
| **Holder kết quả luồng nền** (biến cục bộ của `chay()`) | **4 cặp** + 2 | `_xn_kq/_xn_th` · `_tn_kq/_tn_th` · `_cdd_kq/_cdd_th` · `_ct_som_kq/_ct_som_th`; thêm `_cdd_kq2` (trong khối) và `_t_ct` (vỏ chống treo) |

### ⛔ Cái tôi CHƯA soi
1. **Thân `burn_phude` (`:6560-8533`, ~2.000 dòng)** — tôi đọc chữ ký (25 tham số),
   docstring, `return` (`:8528,8530` → **bool**), lời gọi `_kiem_lo_sau_render`
   (`:8529`) và mọi chỗ nó **đọc** `CHE_BLUR_FIT_X`/`CHE_BAND_FIT`. ⛔ Không duyệt hết
   filtergraph ⇒ ⛔ không loại trừ một đường truyền ẩn trong nhánh hiếm.
2. **Thân `_ghep_track_khop` (`:8965-9835`)** — tôi đọc chữ ký, `return` (`:9832` →
   `dub_wav | None`) và **4 chỗ xuất global** (`:9514,9516,9783,9784`). ⛔ Không đọc
   thuật toán tìm onset.
3. **Bốn nhánh `long_tieng_*`**, `capcut_tts`, `ai_dich`, `dai_sub*` — tôi chỉ tra
   **chỗ đọc** các env/global mà `localize` **ghi**; ⛔ không kiểm kê kênh nội bộ **của
   chúng**. Nếu một trong bốn nhánh đó có side-channel riêng, bảng này ⛔ không kể.
4. **`xu_ly_chon.py` (1.754 dòng)** — chỉ tra các tên đã tìm được. Nó là **caller** nên
   ⛔ không phải một bước của chuỗi, nhưng **bước 0** (pre-encode cắt/zoom) sống ở đó.
5. **`_LAST_*` ở module KHÁC.** Bộ dò của chính Viral (`kiem_xung_dot.py:87-96`) ghi:
   *"AST quét thấy **46** biến bị ghi lúc chạy, regex chỉ thấy 9 (20 %)"* — con số đó là
   **cả cây `app-src`**. Tôi đếm **12** cho `localize.py`. ⇒ Bảng này phủ `localize.py`,
   ⛔ **không** phủ 46. Ai muốn phủ hết phải quét AST cả cây (bộ dò của họ có sẵn).

---

## 1. BẢNG CHÍNH — một hàng một đường truyền

### 1a. Side-channel TOÀN CỤC MODULE (12)

| # | tên (nguyên văn) | kiểu | GHI ở đâu | ĐỌC ở đâu | nội dung | ⇒ ở TA phải là gì |
|---|---|---|---|---|---|---|
| 1 | `_LAST_DUB_ONSETS` | toàn cục module | `localize.py:9783` (trong `_ghep_track_khop`) · `:19363` (khôi phục từ `.dubmeta.json`) · reset `:15282` | `localize.py:20264` (căn sub) · `:19783` (ghi vào `.dubmeta.json`) | `[(st_out, en_out)]` **một cặp/câu** — vị-trí THẬT của giọng sau khi nén/trôi | **`artifact`** — 1 cặp × N câu; phim 58′ đo được **1.335 cue** (`:16678`) ⇒ ≈40 KB JSON. ⛔ **KHÔNG** `outputs`: `_gom_dau_vao` từng nhét `outputs` vào vân tay và sinh vòng lặp 56 lần (`thi_hanh.py:281-292`). GĐ6 → GĐ7 |
| 2 | `_LAST_TIME_WARP` | toàn cục module | `localize.py:9514` · `:19364` (khôi phục cache) · reset `:15281` | `localize.py:19944` (`_tw` → `burn_phude(time_warp=…)`) · `:20327` (`_canh_sub_theo_dub`) | warp **per-segment** để video+tiếng gốc khớp dub | **`artifact`** (hoặc `outputs` nếu ≤150 đoạn — trần `VC_WARP_MAX_DOAN=150`). GĐ6 → GĐ7 **và** GĐ8 ⇒ **hai** hạ nguồn, phải khai cả hai trong `sau=` |
| 3 | `_LAST_VIDEO_SLOW` | toàn cục module | `localize.py:9516` (luôn `1.0` ở bản per-segment) · `:19365` · reset `:15280` | `localize.py:19943` (`_vs` → `burn_phude(video_slow=…)`, và cổng `_vs<0.999` ở `:20381`) | **một float** — hệ số chậm video toàn cục (tương thích ngược) | **`outputs["he_so_cham"]`** — một số. GĐ6 → GĐ8 |
| 4 | `_LAST_DUB_APPLIED` | toàn cục module | `localize.py:9784` | `bench_toc_do.py:144,154` — **⛔ không ai trong chuỗi đọc** | tốc-độ CUỐI mỗi câu (>1 = bị nén) | **`artifact`** (đo lường) — ở ta là đầu vào của `qc_do_luong` **gọi tay**. ⛔ Không là `dau_vao` của giai đoạn nào |
| 5 | `_VC_SPEED` | toàn cục module | `localize.py:15318` (đầu `chay()`, từ tham số `speed`) | `localize.py:9317` (trong `_ghep_track_khop`) | `speed` của khách, luồn xuống vì *"luồn qua signature nhiều hàm rủi ro cao hơn lợi ích"* (`:15316`) | **`settings`** — `speed` đã ở `run.settings` từ lúc tạo lần chạy. ⛔ KHÔNG CẦN kênh |
| 6 | `_LAST_DICH_THAT_BAI` | toàn cục module | `localize.py:18043` · `:18080` · reset `:15039` | `xu_ly_chon.py:1230` — **CALLER**, sau khi `chay()` `return None` | phân biệt *"ASR rỗng thật"* ↔ *"dịch fail 100 %"*; hai ca trước đây `return None` giống hệt nhau | **`outputs["ly_do_that_bai"]`** của GĐ5 (chuỗi enum). 🔑 Ở ta nó ⛔ không phải kênh giữa hai giai đoạn mà là **phân loại lỗi của job** — `jobs`/UI đọc |
| 7 | `_KET_ASR_HONG` | toàn cục module | `localize.py:3329` · reset `:15288` | `xu_ly_chon.py:1235,1243` — **CALLER** | *"ASR chết vì máy/thư viện"* + danh sách lý do | **`outputs["ly_do_that_bai"]`** của GĐ3, cùng cơ chế hàng 6 |
| 8 | `_LAST_ASR_PARTIAL` | toàn cục module | `localize.py:595` · reset `:15287` | `localize.py:3371` (nhánh thử lại ASR) | `{video, segs}` — tiến độ ASR **dở**, để chạy tiếp từ mốc thay vì từ 0 | **`artifact` (checkpoint của GĐ3)** — giữ giá trị, đổi chỗ. ⛔ Không phải global: bug gốc *"mất sub từ giây 0 tới mốc của video TRƯỚC"* (`kiem_xung_dot.py:82`) là **đúng** loại lỗi biến mất khi mỗi job một tiến trình |
| 9 | `_OCR_JOB_NAY` | toàn cục module | `localize.py:2971` (khi OCR chạy) · reset `:15311` | `localize.py:17781` (cổng `_chia_nhip`) | cờ *"job này đi đường OCR"* ⇒ **bỏ chia nhịp** (nguồn đã có nhịp) | **`outputs["nguon_ban_ghi"]`** của GĐ3 (`asr` \| `ocr`). GĐ3 → GĐ5. 🔑 Đổi từ **cờ** sang **tên đường** — tránh đúng bẫy `hai-trang-thai-gop-thanh-mot-gia-tri` |
| 10 | `_OCR_DA_CHAY` | toàn cục module | `localize.py:2970` — **CỐ Ý không reset** (`:15308`) | nội bộ `phu_de`/ASR: *"ORT đã nạp DLL CUDA ⇒ Whisper in-process sẽ HỎNG"* | sự thật về **TIẾN TRÌNH**, không về video | ⛔ **KHÔNG CẦN** — hai giai đoạn của ta là hai tiến trình, không bao giờ chung DLL CUDA. Cơ chế thay thế: **ranh giới tiến trình** + `gpu_lease` |
| 11 | `_SO_CAU` | toàn cục module | `localize.py:127` (`_sk_bat_dau`), bồi dần trong chuỗi · mở lại `:15312` | `_sk_xuat` `:18102-18112` (in ở **điểm hội tụ**) | sổ kế toán câu: mỗi phép lọc/gộp/dịch ghi một mốc | **`outputs["so_cau"]`** cộng dồn **theo giai đoạn** (mỗi GĐ ghi mốc của mình). ⛔ Không một sổ chung — sổ chung cần một tiến trình |
| 12 | `_CAT_CHU` | toàn cục module | `localize.py:4750` (reset mỗi lần dựng ASS) | trong `_fit` khi dựng ASS | `[số cue bị cắt chữ, tổng ký tự đã cắt]` | **`outputs["cue_bi_cat", "ky_tu_bi_cat"]`** của GĐ8 |

### 1b. Biến môi trường ĐƯỢC GHI — 15 cái, đây mới là đường truyền

| # | tên (nguyên văn) | kiểu | GHI ở đâu | ĐỌC ở đâu | nội dung | ⇒ ở TA phải là gì |
|---|---|---|---|---|---|---|
| 13 | `OCR_Y_GATE` | biến môi trường | `localize.py:15182` (có dải) · `:15185` (**luôn ghi kể cả rỗng**) | `dai_sub_rapid.py:956,1143` · và vào **khoá cache** `localize.py:15924` | dải `y0,y1` khách tự khoanh ⇒ OCR khỏi quét cả khung | **`settings`** (`che_band_manual` của khách) + **vào vân tay** GĐ3/GĐ4. GĐ1 → GĐ3, GĐ4 |
| 14 | `OCR_LOAI_VUNG` | biến môi trường | `localize.py:15193` (rỗng) · `:15215` (JSON) | `ocr_text.py:1034,1039,1584,1601` · khoá cache `:15924` | vùng banner khách khoanh ⇒ **loại khỏi phụ đề** (nếu không khách nhận chữ HAI lần) | **`settings`** (`banner_boxes`) + vào vân tay. GĐ1 → GĐ3 |
| 15 | `DUB_FIT_LEN` | biến môi trường | `localize.py:15101` | `dich_gemini_web.py:2132` | bật neo `[Ts ≤N từ]` trong prompt dịch | **`settings` dẫn xuất** — xem 🔴 §2.1: đây là **đường NGƯỢC** đã được Viral giải sẵn |
| 16 | `DUB_NEN` | biến môi trường | `localize.py:15102` | `dich_gemini_web.py:2141` | bật **cách viết ngắn** (không phụ thuộc con số) | như trên |
| 17 | `DUB_WPS` | biến môi trường | `localize.py:15136` (ghi) · `:15138,15140` (xoá) | `dich_gemini_web.py:147` (`nhip_tu_dich`) | **từ/giây đo được của CHÍNH giọng sẽ đọc** — `_wps_giong_that(voice, lang)` `:1946` | 🔴 **`settings` dẫn xuất + BẢNG ĐO TRONG MÃ.** Xem §2.1 — hàng đắt nhất |
| 18 | `CHE_BLUR_FIT_X` | biến môi trường | `localize.py:18492` (khối dò dải) · reset `:15226` | `localize.py:7617,7736` (**trong `burn_phude`**) | *"dải đã bám bề ngang chữ thật ⇒ ĐỪNG kéo full-width"* | **`outputs["dai_bam_ngang"]: bool`** của GĐ4 → GĐ8 |
| 19 | `CHE_BAND_FIT` | biến môi trường | `localize.py:18606` · reset `:15227` | `localize.py:7666,7670,7686` (`burn_phude`) · `:18656,18957` (cùng khối) | *"dải đã fit ⇒ đừng nới 2 % nữa"* (đệm 0,004 thay 0,012) | **`outputs["dai_da_fit"]: bool`** của GĐ4 → GĐ8 |
| 20 | `SRC_NGHE` | biến môi trường | `localize.py:2781` · `:3203` · `:3269` | `dich_gemini_web.py:2184` | *"nguồn LÀ NGHE (Whisper/CapCut ASR), ⛔ không phải OCR"* ⇒ prompt dịch khác | **`outputs["nguon_ban_ghi"]`** của GĐ3 — **CÙNG** trường với hàng 9. 🔑 Hai tên env cho một sự thật; ở ta là **một** trường |
| 21 | `VC_SRC_KBPS` | biến môi trường | `localize.py:15729` · xoá `:15731` | `localize.py:4313` (`_enc_video` chọn `cq`) | bitrate nguồn (kbps) ⇒ chọn chất lượng encode | **`outputs["bitrate_nguon_kbps"]`** của GĐ1 → GĐ8 |
| 22 | `CHE_KEO` | biến môi trường | `localize.py:8520,8527` · xoá `:8525` | `localize.py:7782` · **`xu_ly_chon.py:355`** (caller ép 0/1 theo card khách chọn) | kiểu che: kéo mép / làm mờ / vá hình | **`settings`** (`kieu_che`) — khách chọn. ⛔ Không phải kênh |
| 23 | `OCR_MODEL` | biến môi trường | `localize.py:3007,3031,3044,3062` + `ocr_text._ENGINE=None` để ép dựng lại | `ocr_text` | nâng/hạ model OCR **trong** một lượt quét | ⛔ **KHÔNG CẦN** làm kênh — nội bộ GĐ3. Nhưng phải ghi `outputs["ocr_model_da_dung"]` (`son_do` vs `medium`): nếu không, hai lần chạy cùng vân tay ra kết quả khác nhau mà ⛔ không ai biết vì sao |
| 24 | `OCR_THREADS` | biến môi trường | `localize.py:2910` · xoá `:3077` | `ocr_text` | số luồng OCR | **`settings`/hằng số** theo `tai_nguyen_suat`. ⛔ Không phải kênh |
| 25 | `CAPCUT_GIU_UTT` | biến môi trường | `localize.py:11293` | `capcut_tts.py:1517` (bật `need_subtitle_timestamp`) | *"cần mốc TỪ để cắt gộp-câu"* | **`settings` dẫn xuất** trong GĐ6 (nội bộ). ⛔ Không xuyên giai đoạn |
| 26 | `VC_PROFILE_LOG` | biến môi trường | `localize.py:15330` (`setdefault`) | `dich_gemini_web` ghi GEMPROF vào **cùng tệp** | đường dẫn `_render_profile.jsonl` | ⛔ **KHÔNG CẦN** — ở ta mỗi job có `AsvStage.do` + log riêng; gom là việc của `qc_do_luong` |
| 27 | `PATH` | biến môi trường | `localize.py:12530` | tiến trình con (ffmpeg/piper/demucs) | thêm thư mục `vendor` vào `PATH` | ⛔ **KHÔNG CẦN** làm kênh — nhưng 🔴 **PHẢI làm**, và phải làm **cho LocalSystem**: ta đã vấp *worker chạy dưới LocalSystem thiếu `ffmpeg`* |

⭐ **386 tên env còn lại (401 − 15) là CẤU HÌNH MỘT CHIỀU**, ⛔ không phải đường truyền:
chỉ có chỗ **đọc**, ⛔ không chỗ ghi trong cả cây. ⇒ Ở ta mỗi cái là **`settings`** (nếu
khách được đặt) hoặc **một hằng số có tên** trong mã (nếu không). 🔴 **Đừng chép 386 env
sang app của ta** — `CHE_*` một mình đã 108 cái, và Viral tự ghi rằng nhiều cái *"grep
toàn dự án: KHÔNG nơi nào set biến này"* (`:15055`) ⇒ chúng là **mã chết có tên đẹp**.

### 1c. Kênh là TỆP giữa hai bước (artifact bắt buộc)

| # | tên (nguyên văn) | kiểu | GHI ở đâu | ĐỌC ở đâu | nội dung | ⇒ ở TA phải là gì |
|---|---|---|---|---|---|---|
| 28 | `<ten>.zh.srt` | tệp trên đĩa | `localize.py:15506` (đường dẫn) · ghi `:17865` với `_bak_truoc_ghi_de` | GĐ5 (dịch) · cache `:16170,16214,16563` | bản ghi **nguồn** | **`artifact`** khoá `ban_ghi_nguon.srt`. GĐ3 → GĐ5 |
| 29 | `<ten>.vi.srt` | tệp trên đĩa | `:15507` · ghi `:17940-17948` | GĐ8 `burn_phude(vi_srt=…)` · GĐ7 `_canh_sub_theo_dub` | bản **dịch** | **`artifact`** `phu_de_dich.srt`. GĐ5 → GĐ7, GĐ8 |
| 30 | `<ten>.dubsync.vi.srt` | tệp trên đĩa | `:20327` (`_canh_sub_theo_dub`) | `:20357-20360` (`vi_srt_burn`), rồi `burn_phude` `:20382` | phụ đề **đã căn theo onset THẬT** | 🔴 **`artifact` KHOÁ RIÊNG** — xem §2.3. ⛔ Không được ghi đè khoá của hàng 29 |
| 31 | `<ten>.split.vi.srt` `:16338` · `.fix.vi.srt` `:16364` · `.gem.vi.srt` `:17038` · `.sot.srt`/`.sot.vi.srt` `:17452-17453` · `.chinhta_in/out.srt` `:16918-16919` · `.vibatch.srt` (`:16866-16874`) | tệp trên đĩa | trong GĐ5 | trong GĐ5 | 8 biến thể trung gian của **một** bước dịch | ⛔ **KHÔNG CẦN** làm artifact — **nội bộ** GĐ5, sống trong thư mục tạm của job. Chỉ **bản cuối** lên artifact |
| 32 | `<ten><_ptmp>_goc.wav` `:16388,19999` | tệp trên đĩa | GĐ2/GĐ3 (tách tiếng để ASR) | GĐ7 (trộn nền) | tiếng gốc mono | **`artifact`** `tieng_goc.wav`. GĐ2 → GĐ3, GĐ7 |
| 33 | `<ten><_ptmp>_tnhac.wav` `:15697` | tệp trên đĩa | luồng nền tách nhạc | `:20018-20019` (`nhac_da_tach`) | nhạc nền đã tách | **`artifact`** `nhac_nen.wav`. GĐ2 → GĐ7 |
| 34 | `<ten><_ptmp>_dub.wav` `:19200` · cache `.dub.wav` `:19352` | tệp trên đĩa | GĐ6 (`_ghep_track_khop` trả chính nó `:9832`) | GĐ7 (chuẩn âm, trộn) | track lồng tiếng đã ghép | **`artifact`** `long_tieng.wav`. GĐ6 → GĐ7 |
| 35 | `<dub_wav>.ln.wav` `:19850` | tệp trên đĩa | GĐ7 (loudnorm) | GĐ7 (trộn) | dub **đã chuẩn âm** | **`artifact`** `long_tieng_chuan.wav` (hoặc nội bộ GĐ7 nếu GĐ7 không tách) |
| 36 | `<ten><_ptmp>_mix.wav` `:19990,20076,20158,20179` · `_af.wav` `:20197` · `_nhac_warp.wav` `:20041` | tệp trên đĩa | GĐ7 (7 nhánh trộn) | GĐ8 `burn_phude(audio_path=mix_wav)` | **bản phối master** | **`artifact`** `phoi_master.wav`. GĐ7 → GĐ8. 🔑 `mix_wav is None` mang nghĩa *"chốt chống-câm đã bỏ nó"* (`:20366`) ⇒ **phải là `outputs["dub_that"]` riêng**, ⛔ không suy từ artifact vắng mặt |
| 37 | `.ocrbox.json` (cache) | tệp trên đĩa / khoá cache | `:16669` (`_ca.luu_noi_dung`) | `:16380,16616` (`_nap_ocrbox`, `:2199-2214`) | **toạ độ hộp** chữ từng câu — 1.335 đoạn trên phim 58′ | **`artifact`** `hop_ocr.json`. GĐ3 → GĐ4. Xem 🔴 §2.2 |
| 38 | `.band.json` (cache) | tệp trên đĩa / khoá cache | trong khối dò dải | `:15863` (cổng chạy nền) · khối dò dải | dải che tĩnh `(y0,y1,…)` | **`outputs["dai_che"]`** (5 số) — nhỏ, ⛔ không cần artifact. GĐ4 → GĐ8 |
| 39 | `.dubmeta.json` (cache) | tệp trên đĩa / khoá cache | `:19783-19785` | `:19359-19365` (khôi phục **3** global) | `{onsets, warp, slow}` — **chính** ba hàng 1,2,3 gói lại | ⭐ Ở ta đây **chính là** artifact + `outputs` của GĐ6. Viral phải tự gói vì `chi_dub` return sớm; ta có `AsvStage` sẵn |
| 40 | `.boxes.json` (cache) | tệp trên đĩa / khoá cache | `:18796` · `:18890` (`_ca.luu_noi_dung(_bk, …)`) | `:18803` (`_cb` → `_segs`) · cổng chạy-nền `:15772` (`_bk_early`) | **`blur_segs`** — đoạn che ĐỘNG theo thời gian (cùng nội dung hàng 47/51) | **`artifact`** `vung_che_dong.json` — GĐ4 → GĐ8. 🔴 Xem §4.2: **một khoá, HAI bộ sinh khác nghĩa** |
| 41 | `<ten>_longtieng.mp4` `:20257` · `<ten>_phude.mp4` `:20457,20465` | tệp trên đĩa | GĐ8 | khách / `_kiem_lo_sau_render` `:8529` | **bản giao** | **`artifact`** `ban_giao.mp4`. GĐ8 |
| 42 | `_vc_bn_dich_*/bn.zh.srt` · `bn.vi.srt` `:19154` | tệp trên đĩa (tempdir) | GĐ5 (dịch banner) | ngay tại chỗ, rồi `shutil.rmtree` `:19172` | banner đem đi dịch | ⛔ **KHÔNG CẦN** — nội bộ GĐ5 |
| 43 | `_burnpos_%d.ass` `:7163` · `_burnpos_s%d.ass` `:7190` | tệp trên đĩa | trong `burn_phude` | ffmpeg | phụ đề dạng ASS | ⛔ **KHÔNG CẦN** — nội bộ GĐ8 |
| 44 | `_render_profile.jsonl` `:15330-15331` | tệp trên đĩa | `_tg`/`_PROF_STAGES` cuối render | tích luỹ **qua nhiều video** | số đo từng chặng | ⛔ **KHÔNG CẦN** — `AsvStage.do` + `qc_do_luong` gọi tay |

### 1d. Holder luồng nền + biến cục bộ sống suốt `chay()`

| # | tên (nguyên văn) | kiểu | GHI ở đâu | ĐỌC ở đâu | nội dung | ⇒ ở TA phải là gì |
|---|---|---|---|---|---|---|
| 45 | `_xn_kq` / `_xn_th` | biến cục bộ của `chay()` | `:15521-15522` khai · `:15607,15609` (luồng demucs) | `:20471-20502` (`join(timeout=DEMUCS_TIMEOUT)`, `_au_xn`) | đường dẫn wav **chỉ giọng** (demucs) hoặc `None` | **`artifact`** `chi_giong.wav` = **đầu ra của GĐ2**. Nấc lui *"`_xn_kq[0]=None` ⇒ tách tuần tự ở nhánh ghép"* ⇒ ở ta là `job` **thất bại rồi chạy lại**, ⛔ không phải một nhánh trong GĐ7 |
| 46 | `_tn_kq` / `_tn_th` | biến cục bộ của `chay()` | `:15650` khai · `:15700,15703` | `:20018-20019` (`nhac_da_tach`) | nhạc nền đã tách | **`artifact`** (hàng 33) — GĐ2 |
| 47 | `_cdd_kq` / `_cdd_th` (+ `_cdd_kq2` `:18861-18866`) | biến cục bộ của `chay()` | `:15743-15744` khai · `:15780,15782` · `:18866` | `:18814-18844` (`_segs` = vị-trí che ĐỘNG) | `[đoạn che động]` — 1.335 đoạn ca thật | **`artifact`** `vung_che_dong.json` — **đầu ra của GĐ4** |
| 48 | `_ct_som_kq` / `_ct_som_th` | biến cục bộ của `chay()` | `:15858` khai · `:15874,15878` | `:18287-18291` (`join(timeout=CHE_TINH_SOM_JOIN=180)`) | dict dải che TĨNH (`detect_blur_band`) | **`outputs["dai_che"]`** — GĐ4 (hàng 38) |
| 49 | `_t_ct` | biến cục bộ của `chay()` | `:18327,18333` | `join` ngay `:18334` | ⚠ *"KHÔNG phải chồng chặng — chỉ là VỎ CHỐNG TREO"* (`:18331`) | ⛔ **KHÔNG CẦN** — ở ta timeout là việc của `job_runner` |
| 50 | `blur_band` | biến cục bộ của `chay()` | `:18238` (**dummy** `(0,0,0,0,1.0)`) · `:18605` (bám mực) và nhiều nhánh khác | `:20362` (`_can_che`) · `burn_phude(blur_band=…)` `:20383` · `_kiem_lo_sau_render` `:8529` | dải che 5 số | **`outputs["dai_che"]`**. 🔴 **Và phải TÁCH ĐÔI:** `:18238` gộp *"⛔ không cần dò"* với *"đây là một dải"* vào **một giá trị** — đúng bẫy `hai-trang-thai-gop-thanh-mot-gia-tri` của ta. Ở ta: `dai_che: 5 số \| null` **+** `bo_qua_dai_tinh: bool` |
| 51 | `blur_segs` | biến cục bộ của `chay()` | `:18842` (`None` = bỏ che động) · `:18844` | `:20362,20383` · `:8529` | đoạn che ĐỘNG theo thời gian | **`artifact`** (hàng 47) |
| 52 | `_ocr_boxes` | biến cục bộ của `chay()` | `:16379-16380` (nạp cache) · `:16539` khai · `:16630` (`box_sink=`) · `:16664` (ánh xạ zoom) | `:16667-16669` (lưu) · `:18230-18238` (`_ob_som`) · nới dải + net an toàn `:16376` | hộp vị-trí chữ từng câu | **`artifact`** (hàng 37). 🔴 §2.2 |
| 53 | `segs` | biến cục bộ của `chay()` | `:16234,16542,16581,16628,16727` · 4 lượt lọc `:16731-16752` | GĐ5 (dịch) `:16899,16952` | bản ghi nguồn trong bộ nhớ | **`artifact`** (hàng 28) |
| 54 | `segs_vi` | biến cục bộ của `chay()` | `:16250,16311,16337,16350,16370,16899,16952,17706,17764,17807,17891,17904` (**12 chỗ gán**) | ghi `.vi.srt` `:17940` · GĐ6 (TTS) | bản dịch trong bộ nhớ | **`artifact`** (hàng 29). ⚠️ 12 chỗ gán trên một biến = 12 cơ hội để **một nhánh quên gán** |
| 55 | `_r_chac_khong_chu` | biến cục bộ (list) của `chay()` | `:15328` khai · `:18371` | `:20374` (log) · `:20573` (**cờ ra** `che_khong_co_chu`) | *"quét xong, video KHÔNG có chữ cứng"* ≠ *"dò trượt"* | **`outputs["che_khong_co_chu"]: bool`** của GĐ4 → GĐ8 + cổng nghiệm thu. ⭐ Đây là **ví dụ TỐT** về tách hai trạng thái — copy tinh thần này |
| 56 | `ket["da_che"]` `:20363` · `ket["dub_that"]` `:20366` | trả về của hàm | `:20363,20366` | `xu_ly_chon` (cổng nghiệm thu) | *"có che thật"* / *"tiếng Việt thật sự vào video"* | **`outputs`** của GĐ8 — **bắt buộc**, vì `:20366` ghi rõ: `mix_wav=None` ⇒ khách **vẫn nghe có tiếng** nhưng ⛔ **không phải lồng tiếng** |
| 57 | `_trans_key` `_srt_key` `_scan_key` `_obk` `_band_key` `_dub_key` `_vhash` `_vhash_scan` | biến cục bộ của `chay()` | `:15732,15736,15799-15819,15911-15943,15983,16067-16068,16110,18701,19213` | mọi nhánh cache | **bảy khoá cache tính TAY**, mỗi cái khai phiên bản riêng (`s5`,`o1`,`h11`,`x1`,`b3`) | ⛔ **KHÔNG CẦN** — `thi_hanh.van_tay()` (`:249`) làm **một** vân tay/giai đoạn, đã gom `settings`+`contract`+`engine`+`dau_vao` đệ quy |
| 58 | `_gem_stream` (`_GeminiStream` `:3415`) `.buf` `.kq` `.prev_tail` | biến cục bộ + thuộc tính đối tượng | `:16501` dựng · `them_seg` gọi từ hook `on_chot` **trong vòng đọc `ocr_dong`** | `.kq` (dict zh→vi) cuối GĐ5 | dịch **chồng lên** ASR theo block 450 câu, overlap 30 | ⛔ **KHÔNG CẦN** ở dạng này — nó là **luồng trong một tiến trình**. Ở ta: GĐ5 là job riêng; muốn chồng thì đó là **hai job song song** (B16 §1.1) và **hợp đồng phải là artifact theo lô**, ⛔ không phải một callback |
| 59 | `_TTS_SOM[0]` (`_TongHopSom` `:12865`) | container cấp module | `:13252` khai · dựng trong GĐ6 · dọn `:15157` | `_synth1` tra vào đây | đọc tiếng **ngay khi** Gemini xong từng lô | ⛔ **KHÔNG CẦN** — cùng lý do hàng 58. ⭐ Nhưng **giữ ý tưởng khoá cache**: `:12874` ghi *"khoá là NỘI DUNG CHỮ ĐÃ CHUẨN HOÁ, ⛔ không phải chỉ số cue"* — đúng nguyên tắc vân tay của ta |
| 60 | `_BANNER_DICH` | container cấp module | `:8670` khai · `:19169` | `:19146` | bản dịch banner, khoá `(chữ gốc, đích)` — khách *"áp cho tất cả N video"*, đo **6,0 s và 7,5 s** mỗi lượt Gemini | **`artifact` + cache theo vân tay** (`assets.cache_dung_duoc`) khoá `(chữ gốc, ngôn ngữ đích)`. ⭐ Đây là cái **duy nhất** trong nhóm "sống xuyên video" mà ta **PHẢI** có bản thay thế — bỏ là trả tiền N lần cho một chuỗi |
| 61 | `_ASR_WORKER` `:2327` · `_PIPER_CACHE` `:12341` · `_PIPER_GPU_THAT` `:12424` · `_GOP_CAPCUT_TT` `:12602` · `_TL_CACHE` `:8666` · `_DM_DA_CHIA` `:13768` · `_DM_LOI_MT` `:13769` · `_TACH_NAC_HONG` `:13773` · `_TTS_DICH_EP` `:269` · `_LOG_LAST` `:348` · `_MOC_AUDIO` `:6321` · `_CC_TACH_TMP` `:6324` · `_RONG_ASS` `:4703` | container cấp module | rải rác | rải rác | model nóng · probe máy · cờ *"đã thử, vô ích"* · bộ đếm | ⛔ **KHÔNG CẦN** (13 cái) — **chỉ tồn tại vì một tiến trình dài**. §2.4 |
| 62 | `phu_de._MODEL` `:18138` · `ocr_text._ENGINE` `:3008,3032,3045,3063` · `xu_ly_video._NVENC`/`_DA_BAO_ENC` (qua `reset_encoder_moi_job` `:15302`) | toàn cục **module khác** | như neo | như neo | xả VRAM Whisper trước chặng GPU kế · ép dựng lại engine OCR · probe NVENC | ⛔ **KHÔNG CẦN** — tiến trình thoát thì VRAM trả. Cơ chế thay thế: **ranh giới tiến trình** + `gpu_lease` + `tai_nguyen_suat` |

### 1e. Giá trị TRẢ VỀ của hàm (đừng bỏ)

| # | tên (nguyên văn) | kiểu | GHI ở đâu | ĐỌC ở đâu | nội dung | ⇒ ở TA phải là gì |
|---|---|---|---|---|---|---|
| 63 | `asr_segments(...)` → `segs` | trả về của hàm | `:16628` | `:16731-16752` (4 lượt lọc) → GĐ5 | `[(st,en,text)]` | **`artifact`** (hàng 28) |
| 64 | `_ghep_track_khop(...)` → `dub_wav \| None` | trả về của hàm | `:9832` (và `:9821,9830` → `None`) | GĐ7 | **chỉ đường dẫn**; 3 giá trị thật đi qua **global** (hàng 1,2,3) | 🔴 **Ở ta phải là `outputs` + artifact TƯỜNG MINH.** Đây là chỗ dễ sót nhất: hàm *"trả về"* một tệp nhưng **ba** kết quả quan trọng nhất của nó ⛔ không nằm trong `return` |
| 65 | `burn_phude(...)` → `bool` | trả về của hàm | `:8528,8530` | `:20382-20391` (`ok_lt`, và **thử lại** với `vi_srt` gốc) | chỉ **thành/bại** | **`outputs["ok"]` + `outputs["phu_de_da_dung"]`** — phải ghi **dùng bản nào** (căn-giọng hay gốc), nếu không hai lần chạy giống nhau ⛔ không phân biệt được |
| 66 | `_kiem_lo_sau_render(out_mp4, blur_band, blur_segs, che_chu)` `:8533` | trả về của hàm | gọi `:8529` **trong** `burn_phude` | *"báo cáo, ⛔ không chặn"* | OCR lại **bản RA** — tự kiểm sau xuất bản | **`outputs`** của GĐ8 (bước tự kiểm của B16 §1.2). ⚠️ Nó nhận `blur_band`/`blur_segs` ⇒ **phải đọc `outputs` của GĐ4**, ⛔ không tự dò lại |
| 67 | `_wps_giong_that(voice, tgt)` `:1946` → `(voice_type, từ/giây)` | trả về của hàm | `:15126` | `:15130-15136` → env `DUB_WPS` | tốc đọc **đo được** của giọng, tra `capcut_tts.tim_giong` | 🔴 **`settings` dẫn xuất + bảng trong mã** — §2.1 |
| 68 | `_canh_sub_theo_dub(vi_srt, onsets, tw, out)` `:5221-5440`, gọi `:20327` | trả về của hàm | `:20327` | `:20357` (`_srt_co_cue(vi_srt_burn)`) | phụ đề đã căn — hoặc **thiếu/rỗng** ⇒ lùi về `vi_srt` `:20360` | **`artifact`** (hàng 30) **+ `outputs["do_phu_onset"]`**. Cổng độ phủ `≥0,7×số câu` (`DUB_SYNC_MIN_PHU` `:20270`) và **câu lý do** (`:20275,20330`) phải vào `outputs` |

---

## 2. 🔴 BA ĐIỀU PHẢI PHÁT BIỂU RÕ, vì chúng quyết định plan

### 2.0 `artifact` hay `outputs` — **KÍCH THƯỚC quyết định**, ⛔ không phải sở thích

**Ngưỡng ⛔ không phải một con số tôi thích — nó là một ràng buộc đã đo của hệ TA:**
`_gom_dau_vao` (`thi_hanh.py:281-292`) từng nhét `s.outputs` **thô** vào vân tay, và
hậu quả đo được trên worker thật là **`audio_prepare` thử lại 56 lần, `transcribe` 40
lần trong MỘT lần chạy**. ⇒ `outputs` là **hàng của bảng, đi vào chẩn đoán và vào
lineage** — nó phải **nhỏ và ỔN ĐỊNH**. Mọi thứ **dài theo số câu** thuộc về artifact.

| **BẮT BUỘC `artifact`** (dài theo số câu / theo giây video) | **được `outputs`** (hằng số bit) |
|---|---|
| `.srt` cả 4 loại (nguồn · dịch · căn-giọng · nội bộ) — hàng 28,29,30 | `_LAST_VIDEO_SLOW` 1 float · `dai_che` 5 số |
| `.wav`: `tieng_goc` · `chi_giong` · `nhac_nen` · `long_tieng` · `phoi_master` — hàng 32-36 | `da_che` · `dub_that` · `che_khong_co_chu` · `dai_da_fit` · `dai_bam_ngang` (5 bool) |
| `.mp4` bản giao — hàng 41 | `nguon_ban_ghi` ∈ {asr, ocr} · `ly_do_that_bai` (enum) |
| `hop_ocr.json` — **1.335 đoạn** đo thật (`:16678`) ≈ hàng chục KB | `bitrate_nguon_kbps` · `do_phu_onset` (1 tỉ lệ) |
| `vung_che_dong.json` — cùng bậc | `cue_bi_cat` · `ky_tu_bi_cat` · `so_cau` (vài số nguyên) |
| `_LAST_DUB_ONSETS` — **1 cặp/câu**, ≈40 KB ở 1.335 cue | `ocr_model_da_dung` (chuỗi ngắn) |
| `_LAST_DUB_APPLIED` — 1 float/câu | `phu_de_da_dung` ∈ {canh_giong, goc} |
| checkpoint ASR dở (`_LAST_ASR_PARTIAL`) — chứa **cả `segs`** | `encoder` (nvenc/cpu) |

⚠️ **Một ca biên, và nó có TRẦN:** `_LAST_TIME_WARP` là per-segment, nhưng Viral **đã
phải hạ `VC_WARP_MAX_DOAN` 400 → 150** vì filtergraph. 150 cặp float ≈ 3 KB ⇒ `outputs`
**vừa**. ⭐ Nhưng nó ⛔ **không ổn định giữa hai lần thử** của cùng giai đoạn (warp phụ
thuộc dub thật) ⇒ theo đúng lý lẽ `:281-292`, **đặt vào artifact vẫn an toàn hơn**.

### 2.1 🔴🔴 ĐƯỜNG CHẠY NGƯỢC CHUỖI #1 — `DUB_WPS` / `DUB_FIT_LEN` / `DUB_NEN`

**Đây là hàng đắt nhất trong cả bảng.**

```
GHI :15101, :15102, :15136      (DAU chay() = GD1 media_prepare)
DOC dich_gemini_web:147, 2132, 2141   (GD5 content_process)
NOI DUNG THAT = thuoc tinh cua GIONG ma GD6 voice_synthesis se dung
                (_wps_giong_that(voice, lang) :1946 -> capcut_tts.tim_giong)
```

⇒ **Bản dịch (GĐ5) phụ thuộc vào tốc đọc của giọng (GĐ6).** Trong DAG của B16 đó là
một **chu trình**: `5 → 6` theo `sau=`, mà `5` cần một đại lượng của `6`.

⭐ **Viral đã giải sẵn, và cách giải của họ là cách DUY NHẤT đúng cho ta:** họ ⛔
**không** đo giọng lúc chạy. `_wps_giong_that` **tra một bảng đã đo trước**
(`:15109`: `id 1,56× · en 1,51× · es 1,36× · vi 1,35× · pt 1,33× · ko 1,29× · fr 1,25×`),
tức nó là **hàm thuần của `settings.voice` + một hằng số trong mã**. Vì thế họ tính được
nó ở **dòng đầu** `chay()`, trước cả ASR.

🔑 ⇒ **Ở TA: `settings` dẫn xuất, tính trong GĐ1, đi vào vân tay GĐ5.**
⛔ **KHÔNG được** cài bằng *"GĐ6 đo giọng rồi báo lại GĐ5"* — DAG vỡ và ⛔ không ai
thấy nó vỡ, vì `settings.giong_id` vẫn có giá trị nên GĐ5 vẫn chạy, chỉ là **neo sai**.

⚠️ Và có một cái giá phải ghi: `min()` **một chiều** (`:15112-15117` — *"CHỈ SIẾT, KHÔNG
NỚI"*). Nếu ta cài hai chiều, giọng nhanh sẽ **nới** neo ⇒ bản dịch dài hơn ⇒ nén nặng
hơn ⇒ **ngược ý**. Họ đã đo và ghi lý do; copy cả `min()`.

### 2.2 🔴🔴 ĐƯỜNG CHẠY NGƯỢC CHUỖI #2 — `_ocr_boxes` phá tính SONG SONG mà B16 khai

B16 §2 khai `4 vung_che` **🔀 song song với `3 transcribe`**. Bảng này nói: **⛔ không
được, ở nhánh bám-hộp.**

```
GD3 transcribe  --(box_sink=_ocr_boxes :16630)-->  _ocr_boxes / .ocrbox.json :16669
GD4 vung_che    <--DOC--  :18230 (_ob_som), :18235-18238 (bo qua dai TINH),
                          :16376 (noi dai + net an toan chong lo chu)
```

⭐ **Viral sống được vì họ TÁCH ĐÔI bước 20**, và tôi đọc ra sự tách đó từ chính các cổng:
- **luồng nền `_ct_som_th`** (`:15880`) chỉ gọi `detect_blur_band` — **chỉ đọc VIDEO**,
  ⛔ không cần hộp. Và họ **đã gỡ `srt=` khỏi khoá `_band_key`** ngày 29/08 với bằng chứng
  *"phân tích AST `dai_sub.detect_blur_band`"* cho thấy **hàm ⛔ không dùng srt**
  (`:15808-15812`; đo 3 lượt render cùng video 58′: **0/3 HIT**, dò lại 25,7 s · 24,2 s ·
  27,6 s). ⇒ Phần **này** thật sự song song được.
- phần **bám hộp OCR** (`:18230-18238`, `:18492`, `:18596-18606`) **bắt buộc** có
  `_ocr_boxes` ⇒ **sau** GĐ3.

🔑 ⇒ **Ở TA `vung_che` phải là HAI giai đoạn** (hoặc một giai đoạn `sau=(TRANSCRIBE,)`,
tức **mất** tính song song):
```
vung_che_tinh   sau=(MEDIA_PREPARE,)              # doc VIDEO -> outputs["dai_che"]   | 🔀 || GD3
vung_che_bam    sau=(TRANSCRIBE, VUNG_CHE_TINH)   # doc hop_ocr.json
                # -> artifact vung_che_dong.json + outputs[dai_da_fit, dai_bam_ngang]
```
⚠️ Nếu gộp một giai đoạn và khai `🔀 || transcribe` như B16 viết, thì nhánh bám-hộp chạy
với `_ocr_boxes = []`. Và ca ấy **⛔ không nổ**: `:16376` ghi rõ *"`_ocr_boxes` vốn KHÔNG
TỒN TẠI ⇒ khối nới dải + net an toàn chống lộ chữ đều bị **tắt im lặng**"* — tức **chữ
Trung lộ trên bản giao**, log báo `✔ Xong`. Đúng lớp lỗi ta đang chống.

### 2.3 🔴 ĐƯỜNG "NGƯỢC" #3 — GĐ7 tạo một bản MỚI của artifact do GĐ5 sở hữu

```
GD5 content_process  ->  <ten>.vi.srt            :15507, ghi :17940
GD7 timing_align     ->  <ten>.dubsync.vi.srt    :20327
GD8 render           ->  can CA HAI:  vi_srt_burn :20357-20360 (lui ve goc neu 0 cue)
                                      thu lai     :20387-20391 (burn dubsync loi -> burn goc)
```

Đây ⛔ **không** ngược theo thứ tự thực thi, nhưng **ngược theo quyền sở hữu**: GĐ7 sinh
một thứ đóng **cùng vai** với đầu ra của GĐ5, và GĐ8 chọn giữa hai.

🔑 ⇒ **Ở TA:** GĐ7 xuất artifact **khoá riêng** `phu_de_canh_giong.srt`. ⛔ **Tuyệt đối
không** ghi đè khoá của GĐ5 — nếu ghi đè, vân tay GĐ5 vẫn là vân tay cũ nhưng nội dung đã
đổi ⇒ **vân tay nói dối**, và một lượt chạy lại GĐ8 với cache sẽ dùng bản sai. GĐ8 phải
ghi `outputs["phu_de_da_dung"] ∈ {canh_giong, goc}`.

⚠️ Cùng hình dạng, ba chỗ khác: `_ln.wav` (GĐ7 tạo bản chuẩn âm của `long_tieng.wav`),
`_af.wav`, `_nhac_warp.wav`. Mỗi cái một khoá, ⛔ không ghi đè.

### 2.4 🔴 Đường chỉ tồn tại vì họ có MỘT tiến trình dài ⇒ `⛔ KHÔNG CẦN`

Viral nói thẳng cơ chế: *"render_worker là tiến trình **SỐNG DAI** xử lý **~30 video**
tuần tự trong CÙNG process"* (`:15222-15224`, `:15291`, `:15308`). **17 kênh** tồn tại
**chỉ** vì điều đó — hàng 10, 61, 62 và 6 lời gọi reset xuyên module.

| kênh | bệnh họ chữa | cơ chế thay thế Ở TA |
|---|---|---|
| `_OCR_DA_CHAY` (hàng 10) | ORT nạp DLL CUDA ⇒ Whisper in-process **hỏng** | **ranh giới tiến trình** — GĐ3 và GĐ4 là hai job |
| `phu_de._MODEL=None` + `gc.collect()` `:18138-18147` | *"Whisper giữ VRAM tới khi destructor chạy → Demucs/TTS nạp kế → 2 model tranh"* | tiến trình thoát ⇒ VRAM trả; **`gpu_lease`** + `tai_nguyen_suat` |
| `phu_de.reset_gpu_moi_job` `:15293` | 1 sự cố VRAM thoáng qua từng **tắt GPU cho TOÀN BỘ 30 video**, chỉ job đầu báo | không có state sống xuyên job ⇒ bệnh biến mất |
| `xu_ly_video._NVENC` + `_DA_BAO_ENC` `:15302` | một lần probe trượt ⇒ **29 video còn lại encode CPU**, chênh hàng GIỜ, ⛔ không dòng log nào nói vì sao | probe mỗi job; ghi `outputs["encoder"]` để **đo được** |
| `ocr_text._ENGINE=None` `:3008,3032,3045,3063` | ép dựng lại engine khi đổi `OCR_MODEL` | nội bộ GĐ3 |
| `_TTS_SOM[0]` `:13252` + dọn `:15157` | job hỏng ⇒ job SAU trỏ vào bộ đọc-trước **của job trước** (thư mục tạm đã xoá; cache khoá theo **VĂN BẢN** ⇒ *"Cảm ơn các bạn"* dùng lại **giọng video trước**) | ⛔ không cần; nếu muốn chồng thì **hai job**, và khoá cache **phải gồm giọng** |
| `_ASR_WORKER` · `_PIPER_CACHE` · `_PIPER_GPU_THAT` · `_GOP_CAPCUT_TT` · `_TL_CACHE` · `_DM_DA_CHIA` · `_DM_LOI_MT` · `_TACH_NAC_HONG` | model nóng · probe máy · cờ *"đã thử, vô ích"* | **cache theo vân tay** (`assets.cache_dung_duoc`) cho cái đáng giữ; còn lại bỏ |
| `chat_luong.dat_lai()` · `capcut_tts.dat_lai()` · `_SO_CAU` · `_CAT_CHU` · `_RONG_ASS` · `_MOC_AUDIO` | *"số của video A cộng dồn sang video B"*; *"video 1+2 làm đầy bảng, video 3 chạm trần ⇒ **ngừng ghi** ⇒ mất số liệu"* | **`outputs` theo giai đoạn** — mỗi job một sổ, ⛔ không có gì để cộng dồn |
| `_BANNER_DICH` (hàng 60) | 🔴 **NGOẠI LỆ — đáng giữ.** *"áp cho tất cả N video"* ⇒ **6,0 s và 7,5 s** gọi Gemini × N cho **một** chuỗi | **cache theo vân tay**, khoá `(chữ gốc, ngôn ngữ đích)`. Bỏ hẳn là **trả tiền N lần** |
| `_GeminiStream` (58) · `_TongHopSom` (59) | chồng dịch lên ASR / chồng TTS lên dịch — đo thật tiết kiệm **71 s → 136 s** | **hai job song song** (B16 §1.1) với hợp đồng **artifact theo lô**, ⛔ không phải callback in-process |

⭐ **Một câu chốt:** 17 kênh biến mất **⛔ không vì ta bỏ tính năng**, mà vì **mô hình
tiến trình của ta đã giải bệnh mà chúng chữa**. ⇒ Cột `⛔ KHÔNG CẦN` ⛔ **không** là một
khoảng trống cần lấp.

---

## 3. Tệp trung gian — đếm đủ 21, và ai sở hữu cái nào

| tệp (nguyên văn) | neo | GĐ sinh | GĐ đọc | ⇒ ở TA |
|---|---|---|---|---|
| `<ten>.zh.srt` | `:15506` | 3 | 5 | `artifact ban_ghi_nguon.srt` |
| `<ten>.vi.srt` | `:15507` | 5 | 7, 8 | `artifact phu_de_dich.srt` |
| `<ten>.split.vi.srt` | `:16338` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.fix.vi.srt` | `:16364` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.chinhta_in.srt` | `:16918` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.chinhta_out.srt` | `:16919` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.gem.vi.srt` | `:17038` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.sot.srt` | `:17452` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.sot.vi.srt` | `:17453` | 5 | 5 | nội bộ GĐ5 |
| `<ten>.vibatch.srt` (do khách nhập, `vi_co_san`) | `:16866-16874` | — (settings) | 5 | `settings`/artifact khách nộp |
| `<ten>.dubsync.vi.srt` | `:20327` | 7 | 8 | `artifact phu_de_canh_giong.srt` — §2.3 |
| `bn.zh.srt` / `bn.vi.srt` (tempdir) | `:19154` | 5 | 5, xoá `:19172` | nội bộ GĐ5 |
| `<ten><_ptmp>_goc.wav` | `:16388`, `:19999` | 2 | 3, 7 | `artifact tieng_goc.wav` |
| `<ten><_ptmp>_tnhac.wav` | `:15697` | 2 | 7 | `artifact nhac_nen.wav` |
| `<ten><_ptmp>_dub.wav` | `:19200` | 6 | 7 | `artifact long_tieng.wav` |
| `<dub_wav>.ln.wav` | `:19850` | 7 | 7 | `artifact long_tieng_chuan.wav` |
| `<ten><_ptmp>_mix.wav` | `:19990,20076,20158,20179` | 7 | 8 | `artifact phoi_master.wav` |
| `<ten><_ptmp>_nhac_warp.wav` | `:20041` | 7 | 7 | nội bộ GĐ7 |
| `<ten><_ptmp>_af.wav` | `:20197` | 7 | 8 | `artifact` (bản lọc âm) |
| `_burnpos_%d.ass` / `_burnpos_s%d.ass` | `:7163`, `:7190` | 8 | ffmpeg | nội bộ GĐ8 |
| `<ten>_longtieng.mp4` | `:20257` | 8 | khách + `_kiem_lo_sau_render` | `artifact ban_giao.mp4` |
| `<ten>_phude.mp4` | `:20457`, `:20465` | 8 | như trên | `artifact ban_giao.mp4` |
| `_render_profile.jsonl` | `:15330-15331` | mọi GĐ | tích luỹ nhiều video | ⛔ KHÔNG CẦN (`AsvStage.do`) |
| stem demucs / `_dubtmp/fit_%d.wav` | `:8980`, dọn `:20514-20576` | 2, 6 | trong GĐ | nội bộ |

⚠️ **`_ptmp` là một tiền tố chống-đụng-tên, và nó có một bài học ta cần:** `:8976-8980`
ghi *"trước đây `_dubtmp` tên CỐ ĐỊNH — 2 job CÙNG VIDEO khác ngôn ngữ đích chạy song
song sẽ dùng CHUNG thư mục này … → **lệch timing giọng**"*. Và `:20485` đổi sang
`_ptmp + "_l2"` khi luồng nền còn sống, *"file tạm riêng, không giẫm lên luồng nền"*.
⇒ Ở ta `assets.dat_khoa(owner_id, run_id, stage, van_tay, …)` đã có **run_id + owner_id**
trong khoá ⇒ **bệnh này ⛔ không tồn tại**. Nhưng nếu ai cài một thư mục tạm **cố định**
cho worker thì bệnh quay lại — và nó biểu hiện là **lệch timing**, ⛔ không phải một lỗi.

### 3.1 Cache liên-lần-chạy: **7 hậu tố**, và vì sao ở ta là MỘT cơ chế

| hậu tố | khoá (phiên bản khai) | neo |
|---|---|---|
| `.zh.srt` | `_scan_key` `s5`, `_vhash_scan` | `:15911, :15943` |
| `.vi.srt` | `_trans_key` `h11` · `_srt_key` | `:16067, :16068, :16110` |
| `.ocrbox.json` | `_obk` `o1` | `:15983` |
| `.band.json` | `_band_key` `b3` | `:15799-15819` |
| `.boxes.json` | `_bk`/`x1` | `:18701` |
| `.dub.wav` | `_dub_key` | `:19213` |
| `.dubmeta.json` | cùng `_dub_key` | `:19359` |

🔑 ⇒ **BẢY khoá tính tay, mỗi cái một hằng phiên bản (`s5`/`o1`/`h11`/`b3`/`x1`), và mỗi
lần đổi logic phải "bump theo luật"** (`:15806`). Ở ta là **một** `thi_hanh.van_tay()`
(`:249`) đã gom `stage + contract + settings + dau_vao + engine`. ⇒ Nhóm này là
`⛔ KHÔNG CẦN` **về cơ chế**, nhưng ⭐ **hai bài học phải lấy**:
1. `phien_ban_engine(stage_ten)` của ta **chính là** `s5`/`o1`/`h11` của họ. `:253-255`
   của ta đã ghi đúng bệnh: *"thiếu mảnh cuối thì nâng engine lên bản mới sẽ dùng lại kết
   quả cũ, im lặng"*. Họ trả giá bằng **5 hằng số phải nhớ bump tay**.
2. 🔴 **Hạt giống của khoá phải ỔN ĐỊNH.** `:15758-15763`: khoá `boxes` dùng `_vhash`
   (`video_hash` trên **tệp TEMP**, đổi mtime mỗi lần render/mỗi ngôn ngữ) trong khi
   `_scan_key`/`_trans_key` dùng `_vhash_scan` ⇒ **cache boxes ⛔ KHÔNG BAO GIỜ HIT**.
   Ở ta `van_tay` băm `settings` + `dau_vao`; nếu một GĐ đưa **đường dẫn tạm** hay **mtime**
   vào `outputs` rồi cái đó chảy vào `dau_vao` hạ nguồn, ta mắc **đúng** lỗi này. Đó
   chính là thứ `_gom_dau_vao` `:281-292` đã chặn bằng *"CHỈ `fingerprint`, KHÔNG `outputs` thô"*.
3. ⭐ *"NGHI NGỜ → MISS"* (`:15719`) — nguyên tắc của họ khi ⛔ không chắc khoá đúng.
   Cùng tinh thần với `thi_hanh.giai_doan_lech_van_tay` (`:310`).

---

## 4. ❓ CHƯA BIẾT — và cần gì để biết

| # | đường | vì sao chưa biết | cần gì để biết |
|---|---|---|---|
| B | **`_ghep_track_khop` sinh `_dub_onsets` bằng đại lượng gì** | tôi đọc chỗ **xuất** (`:9783`) và chỗ **tiêu thụ** (`:5221`, `:20264`), ⛔ không đọc thân (`:8965-9835`, 870 dòng). ⇒ Tôi khẳng định **có** một kênh onset và **kích thước** của nó; ⛔ **không** khẳng định onset là "đỉnh biên độ đầu tiên" hay "mốc ghép" | đọc `:9600-9790`. **Làn W? nào lo `timing_align` cần cái này** — nó quyết định GĐ6 phải ghi đại lượng gì |
| C | **`burn_phude` có đường truyền ẩn nào khác ⛔ không** | ⛔ chưa duyệt 2.000 dòng filtergraph. Tôi đã bắt hết chỗ nó **đọc** 2 env (`CHE_BLUR_FIT_X`, `CHE_BAND_FIT`) và `_tham_so_goi` `:8522` (tự gọi lại chính nó bằng LÀM MỜ) | `grep -n 'os.environ\|globals()' localize.py` lọc `6560..8533` — **đã làm**, ra **0** chỗ GHI. ⇒ rủi ro còn lại là kênh **qua tệp**. Cần: liệt kê mọi `open(`/`-i ` trong khoảng đó. **30 phút** |
| D | **`_chia_deu_nen_manh(items, …)` `:8974` đổi `items` tại chỗ ⛔ không** | nó chạy **trước** khi `_st_goc_all` được dùng (`:8973` chụp mốc GỐC **trước**) — dấu hiệu nó **có** đổi. Nếu đổi tại chỗ thì mốc "gốc" và mốc "re-slot" là **hai** đại lượng, và cả hai phải ra `outputs` | đọc `_chia_deu_nen_manh`. Đây là ca `hai-trang-thai-gop-thanh-mot-gia-tri` tiềm năng |
| E | **Bốn nhánh `long_tieng_*` + `capcut_tts`/`ai_dich`/`dai_sub*` có side-channel riêng ⛔ không** | ngoài phạm vi tôi soi (§0 mục 3). Bộ dò của chính họ nói **46 biến** trên cả cây, tôi đếm 12 trên `localize.py` ⇒ còn ~34 ở nơi khác | chạy chính `kiem_xung_dot.py` của họ (⛔ **không** trong phiên này — `D:\Viral` chỉ đọc, và tôi ⛔ không chạy gì). Hoặc quét AST bằng công cụ của ta |

### 4.2 🔴 MỘT KHOÁ CACHE, **HAI bộ sinh khác nghĩa** — họ tự ghi là còn nợ

`:18699-18700` (nguyên văn): *"⚠ CÒN NỢ (không sửa ở đây vì cần đổi **CẤU TRÚC**, không
phải đổi key): **hai BỘ SINH khác nhau** (`_ocr_boxes` đã kéo `t_off` vs
`phat_hien_hop_dong` **thô**) vẫn ghi **CHUNG một key** — xem SESSIONS 06/08."*

⇒ `.boxes.json` có thể chứa đoạn **đã dịch mốc** hoặc đoạn **thô**, và khoá `x1` ⛔ không
phân biệt. Ai HIT cache ⛔ không biết mình nhận bản nào.

🔑 **Ở TA điều này ⛔ không được phép tồn tại**, và cơ chế của ta **đã** chặn nếu khai
đúng: hai bộ sinh = **hai giai đoạn** (`vung_che_tinh` vs `vung_che_bam`, §2.2) ⇒ **hai**
`stage` ⇒ **hai** `van_tay` ⇒ **hai** khoá artifact. Lỗi chỉ quay lại nếu ai gộp chúng vào
một giai đoạn và cho nó **hai nhánh** — đúng lớp `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`.

⭐ Và `:18216` là bằng chứng **cơ học** cho §2.2, ⛔ không phải suy luận:
`_ob_som = locals().get("_ocr_boxes") or []` — họ phải dùng `locals().get()` vì biến ấy
**có thể ⛔ không tồn tại** ở đường này. Ở ta `dau_vao` thiếu một artifact thì
`thi_hanh` **nói ra**; một `.get()` thì **im lặng trả rỗng**.

### 4.1 ⚠️ MỘT CHÚ THÍCH CỦA HỌ ĐÃ SAI — đừng thiết kế theo nó

`:15221-15225` viết: *"`CHE_BLUR_FIT_X`/`CHE_BAND_FIT` được **`burn_phude()` SET** có điều
kiện (xem chỗ dùng ~3561/~3509) nhưng KHÔNG bao giờ reset"*.

**Tôi kiểm bằng grep, ⛔ không bằng trí nhớ:** cả tệp chỉ có **4** chỗ ghi hai tên này —
`:15226`, `:15227` (reset) và `:18492`, `:18606` (**trong khối dò dải**, GĐ4). Trong khoảng
`6560-8533` (`burn_phude`) chúng chỉ **được ĐỌC**: `:7617`, `:7670`, `:7686`, `:7736`.

⇒ Đường này là **thuận** (GĐ4 → GĐ8). 🔴 **Nhưng nếu ai đọc chú thích đó mà tin, họ sẽ
thiết kế một đường NGƯỢC không tồn tại** (GĐ8 báo lại GĐ4), và trong mô hình job của ta
đường ngược đó **⛔ không cài được** ⇒ họ sẽ kết luận sai rằng B17 có một chỗ bế tắc.
Neo số cũ (`~3561`/`~3509`) cũng ⛔ không còn khớp tệp hiện tại.

---

## 5. Tóm lại — cái gì đi vào plan

| việc | vì sao | neo |
|---|---|---|
| **1. `vung_che` phải TÁCH HAI** (`vung_che_tinh` ∥ GĐ3 · `vung_che_bam` sau GĐ3) | B16 §2 khai song song, nhưng nhánh bám-hộp cần `_ocr_boxes` của GĐ3; thiếu ⇒ **tắt im lặng** khối chống lộ chữ | §2.2 · `:16376`, `:18230-18238` |
| **2. `DUB_WPS` là `settings` dẫn xuất tính ở GĐ1**, tra bảng đo, `min()` một chiều | GĐ5 cần một đại lượng của GĐ6 ⇒ chu trình nếu cài bằng "GĐ6 báo lại" | §2.1 · `:15101-15140`, `:1946` |
| **3. GĐ7 xuất `phu_de_canh_giong.srt` KHOÁ RIÊNG**; GĐ8 ghi `phu_de_da_dung` | ghi đè khoá GĐ5 làm **vân tay nói dối** | §2.3 · `:20327`, `:20357-20391` |
| **4. `dai_che` phải TÁCH ĐÔI**: `dai_che: 5 số \| null` **+** `bo_qua_dai_tinh: bool` | `:18238` nhét dummy `(0,0,0,0,1.0)` mang **hai** nghĩa vào **một** giá trị | hàng 50 |
| **5. `nguon_ban_ghi` MỘT trường** thay cho `_OCR_JOB_NAY` + `SRC_NGHE` | hai env cho một sự thật, hai chỗ khai ⇒ **không ai bắt khớp** | hàng 9, 20 |
| **6. `dub_that` và `da_che` BẮT BUỘC ra `outputs`** | `mix_wav=None` ⇒ khách **vẫn nghe có tiếng** nhưng **⛔ không phải lồng tiếng**; suy từ "artifact có tồn tại" là **sai** | hàng 56 · `:20364-20366` |
| **7. `_BANNER_DICH` phải có bản thay thế** (cache vân tay theo `(chữ gốc, đích)`) | bỏ = trả **6,0-7,5 s** Gemini × N video cho **một** chuỗi | hàng 60 · `:19141-19169` |
| **8. ⛔ ĐỪNG chép 386 env cấu hình** | `CHE_*` một mình 108 cái; họ tự ghi *"grep toàn dự án: KHÔNG nơi nào set biến này"* (`:15055`) ⇒ **mã chết có tên đẹp** | §1b |
| **9. `_LAST_ASR_PARTIAL` giữ GIÁ TRỊ, đổi CHỖ** → checkpoint GĐ3 | chạy tiếp từ mốc dở là thứ đáng có; **global** thì ⛔ không | hàng 8 |
| **10. `phien_ban_engine` của ta = `s5/o1/h11/b3/x1` của họ** — kiểm nó **có đủ mảnh** | thiếu ⇒ nâng engine mà dùng lại kết quả cũ, **im lặng** | §3.1 · `thi_hanh.py:253-255` |
| **11. `vung_che_dong.json` phải có MỘT bộ sinh** (hệ quả của việc 1) | họ tự ghi *"hai BỘ SINH khác nhau vẫn ghi CHUNG một key — CÒN NỢ, cần đổi CẤU TRÚC"* | §4.2 · `:18699-18700` |
