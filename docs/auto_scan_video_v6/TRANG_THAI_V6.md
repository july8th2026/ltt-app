# TRẠNG THÁI CHƯƠNG TRÌNH ASV V6 (98+)

> Nhánh `phien/asv-v6`. Gói yêu cầu gốc:
> `G:\My Drive\AI\A\Auto_Scan_Video_V6_98_Plus` (35 pha, 00–34).
>
> ⛔ **Không deploy cho tới pha 34.** `apps/auto_scan_video/manifest.py` khai
> `enabled=False`, và `/auto-scan-video` trả **404** trên production (cờ
> `LTT_AUTO_SCAN_VIDEO`). Mọi thay đổi ở đây không chạm một khách nào.

## Vì sao tệp này tồn tại

Gói V6 yêu cầu mỗi pha *"đọc STATE/report pha trước"*. Không có tệp ấy thì mỗi
phiên phải suy trạng thái từ `git log` — và `git log` trả lời *"ai đã commit
gì"*, không trả lời *"pha nào đã đóng, pha nào bị chặn và bởi cái gì"*.

⚠️ Bảng dưới là **con trỏ**, không phải bản sao. Số liệu sống ở báo cáo từng
pha; chép lại vào đây là tạo một bản sẽ trôi.

## Bảng pha

| Pha | Tên | Trạng thái | Ghi chú / chặn |
|---|---|---|---|
| 00 | Provenance + worktree + baseline | **XONG** | Cây riêng `asv-v6`, gốc chung `768b1dba`, off-site từ 11/09. Xem `PHA00_04_NEN_TANG.md` §1 |
| 01 | Product contract + 98+ score model | **MỘT PHẦN** | Phạm vi = `MA_TRAN_TINH_NANG_V6.md`; 12 `DEFER` V5 nay đều có pha. ⚠️ Chưa chấm theo `V6_98_SCORECARD.md` — việc chấm độc lập là pha 34 |
| 02 | Capability ownership map | **XONG** | `REBASE_MAP_V4.md` giữ sống qua V6 + `lint_app_contract` cưỡng chế bề mặt liên-app |
| 03 | Viral second-pass audit | **CHƯA** | Lượt một có ở V5; lượt hai phải mổ ứng dụng Electron đóng gói `D:\Viral` — chưa làm |
| 04 | Gap matrix + backlog freeze | **XONG** | `MA_TRAN_TINH_NANG_V6.md`: 59 tính năng → 30 XONG · 6 MỘT PHẦN · 15 CHƯA · 3 CẦN ADR · 5 LOẠI; `test_477` chốt tập hợp bằng đúng V5 |
| 05 | Regression shield + static-analysis | **XONG** | Bốn hạng mục, đã **đo trước khi sửa**: ① bất biến V4/V5 — `tests/bo_bat_bien_v4.py` + `test_428` chốt mỗi bất biến tầng 2 có một tệp chứng minh; ② lint boundary bằng AST — `lint_app_contract.py:266` đã dùng `ast.parse`; ③ rào chắn test nặng — `tests/rao_chan_nang.py` **có sẵn ở nhánh này**, kèm bánh cóc AST và một self-test; ④ nợ mypy ASV **28 → 19**. 🔑 Kết quả có ích của phép đo: trong 24 phát hiện không thuộc pha 14, **không cái nào là lỗi CHẠY** — 6 là khoảng trống kiểu của `require_login`, 3 là stub SQLAlchemy. Tức nợ 616 của cả kho **không** tập trung ở ASV. Đã sửa 3 chỗ *dùng lại một tên cho hai kiểu* (thứ làm mypy mù) và 1 ràng buộc ngầm ở `demucs_runner` |
| 06 | Studio frontend architecture | **XONG** | `asv.js` 1.154 dòng → **tám module** `server/static/asv/`. Một nguồn `ASV_STUDIO_JS` cho ba nơi (thẻ `<script>` · `asset_ver` · bộ kiểm). Trần 320 dòng/module, 4 đối chứng đỏ đúng chỗ. 🔴 Kiểm trình duyệt bắt một nút giả — `[hidden]` bị `.btn{display:inline-flex}` đè. Xem `PHA06_KIEN_TRUC_GUI.md` |
| 07 | ProductSettings + RenderManifest v3 | **XONG** | `cai_dat.py` — schema `asv.cai_dat.v3`, vân tay toàn hồ sơ, **mười nơi đọc → một**. 🔴 Sửa một lần trôi THẬT: `timing_mode` có hai mặc định (`fit_original` vs ``), nên một run thiếu khoá **chạy** một đằng còn **bằng chứng QC ghi** một nẻo. Lưu THƯA / đọc TOÀN PHẦN. 4 đối chứng đỏ đúng chỗ. Xem `PHA07_CAI_DAT_CHUAN_TAC.md` |
| 08 | Durable upload + source preview | **XONG** | `ef7b3425` (08a) + `d78d1804`/`cc9b1e8d` (08b). Xem `PHA08_TAI_LEN.md`. 🔴 Tìm ra đường tải lên 2 GiB **chưa bao giờ chạy được từ giao diện** |
| 09 | Timeline + Scene Browser | **XONG** | `d4066def` — khách XEM được cảnh, và chỉ xem |
| 10 | Core edit controls | **MỘT PHẦN** | `a9cecb42` cắt đầu/cuối. `zoom`/`crop`/`reframe` nằm trong `CAM_TRONG_MVP` — mở chúng cần một ADR, không phải một lượt code |
| 10b | kiểm GUI thật | **XONG** | `395b29dd` — bắt một lỗi bố cục bộ kiểm không thấy |
| 11 | Overlay controls | **XONG** | `efbcfb4a` + `42512fd8` (11a chữ) · `d78d1804` (11b logo, sau khi pha 08 mở đường nhập ảnh). Xem `PHA11_LOP_PHU_CHU.md` |
| 12 | Region editor v2 | **XONG** | `8c4a1d35` (giờ có tác dụng thật) + `8cd5b281` (giao diện đặt giờ) |
| 13 | Watermark/logo intelligence | **XONG — remove ĐỂ TẮT** | `tools/do_watermark.py`. 🔴 Cổng **tài nguyên ĐẠT** (`delogo` 8,9e-5 s/khung → 4,8 s cho video 30 phút / ngân sách 540 s) nhưng cổng **chất lượng KHÔNG ĐẠT**: bộ dò tìm *vùng tĩnh* chứ không tìm *watermark*. Ba trục đã thử, ba phép đo. Xem `PHA13_NHAN_DIEN_WATERMARK.md` |
| 14 | Subtitle capability integration | **XONG** | `apps/auto_scan_video/phu_de.py`. 🔴 Chặn đã đo và câu trả lời làm đổi thiết kế: `thoi_gian.lap_ke_hoach:158` gọi `ban_do.ra()`, nên `ke_hoach.doan[].dat_tai_ms` **đã nằm trên trục bản ra** — cầu nối không tự ánh xạ gì, nó chỉ đọc. ⭐ **HAI trục**: *đốt vào hình* (đổi điểm ảnh, bất khả ở preset giữ hình) và *xuất `.srt`* (không chạm điểm ảnh, chạy ở **cả hai** preset, và là lựa chọn phụ đề duy nhất còn lại ở preset giữ hình) — nên bảng `NANG_LUC_KHONG_DOI_DIEM_ANH` là bảng **mới**, không gộp. ⛔ Mượn tầng **tác giả** của `autosubvideo`, **không** `burn.burn()` (nó chạy một lượt ffmpeg đầy đủ của riêng nó ⇒ mã hoá lại hai lần) — và sự vắng mặt của `burn` trong bề mặt liên-app là lớp cưỡng chế duy nhất cho quyết định đó. `PHIEN_BAN_CHE_DO` 5→6. Xem `PHA14_PHU_DE.md`
| 15 | Hardsub/OCR routing | **CHƯA MỞ — MÓNG** | ⛔ `0` tệp nào trong kho nhắc tới OCR. Cần chọn engine (**một ADR + một phụ thuộc mới**). ⚠️ Pha 13 là tiền lệ: bộ dò watermark **đạt** cổng tài nguyên nhưng **trượt** cổng chất lượng ⇒ để tắt. Xem `MA_TRAN_KHOANG_TRONG.md` |
| 16 | Subtitle Studio UX | **XONG** | 18/27 trường của `SubtitleStyleConfig` mở ra giao diện, duyệt bằng **chính mô hình** của app chủ (`extra="forbid"` bắt cả lỗi gõ sai tên). 🔴 Bắt được một **false feature** thật: `style_registry` giữ chế độ nhấn mạnh ở **hai** chỗ và **7/9** preset khai ở cấp preset trong khi `config.highlight_mode` là `none` ở **cả chín** — đọc chỗ tự nhiên nhất làm kiểu tên `word_emphasis` không nhấn mạnh một từ nào, im lặng. `test_472` 29 bài. Xem `PHA16_SUBTITLE_STUDIO.md` |
| 27 | Technical QC expansion | **XONG** | T1–T13 → **T1–T16**, `PHIEN_BAN_QC` 2→3. Đo trước: 4/8 dung sai đề bài gọi tên **không ai canh**. T14 preset giữ hình có thực sự không mã hoá lại (lưới thứ hai cho T3, thứ rơi về `KHONG_AP_DUNG` ngay khi không băm được) · T15 mỗi dòng phụ đề nằm trong bản ra · T16 luồng hình và luồng tiếng dài bằng nhau (T2 đo **container** — con số vẫn đúng khi hai luồng bên trong lệch). 🔴 Ngưỡng T16 **đo trên `ket_xuat.dung_lenh` thật**, cả hai đường render + nhịp 29,97: lệch tệ nhất 0,0206 s ⇒ chọn 0,50 s (dư địa 24×), vì một mục HONG **chặn** một video đã render xong. Bài kiểm bắt được **hai lỗi trong chính phép kiểm của tôi**: coi `0` là thiếu dữ liệu làm trục `xoay` chết lặng lẽ, và trục xoay một mình không đủ để tuyên bố "không mã hoá lại". `test_473` 23 bài. Xem `PHA27_QC_MO_RONG.md` |
| 26 | Renderer fusion + performance | **XONG** | Không đổi mã — **đo rồi chốt**. Bật cả bốn biến đổi điểm ảnh (vùng · logo · chữ · phụ đề) ⇒ **1** `-filter_complex`, **1** `-c:v`, **1** tệp ra, chạy trên ffmpeg thật. Bốn núm chất lượng khác thang (`-cq 28`/`-global_quality 28`/`-qp_i 28`/`-crf 23`) đo ra **tương đương** (ngưỡng ghi trước, nguồn FFV1). 1080p: NVENC ×0,67 thời gian, ×0,21 CPU ⇒ giữ phần cứng trước. 🔴 libx264 ăn **~11 lõi** ở 1080p — đường lùi CPU chiếm cả máy production. `test_474` 10 bài. Xem `PHA26_RENDERER_FUSION.md` |
| 19 | VoiceBinding + single-speaker | **XONG** | Binding đã chuẩn ở máy chủ; hai lỗ là **thời điểm**: cửa không kiểm quyền sở hữu (chỉ kiểm sau khi giữ credit + tách nguồn + ASR) ⇒ `rang_giong.kiem_o_cua` trước khi giữ credit, bằng chính `_rang_khach_chon`, cùng một câu cho "không có"/"không phải của bạn". Và đường lùi `or cai.giong_id` ở `giai_doan_giong` ⇒ với `AUTO_MATCH` rơi về **giọng mặc định engine** (D-V4-04) — đã đóng. Không nâng `PHIEN_BAN` nào ⇒ nghiệm thu E2E vẫn hiệu lực. `test_475` 10 bài (HTTP thật: 400, không run, không đụng credit). Xem `PHA19_VOICE_BINDING.md` |
| 22 | Dubbing adaptation + fit | **XONG phần làm được — đo ngưỡng chờ nghiệm thu thật kế** | Bậc thang bốn nấc, phục hồi từng đoạn, từ điển phát âm đã có từ V4. Chốt mới: giọng giải **một lần, trước** mọi nấc viết lại. Dữ liệu thật đầu tiên (n=12): 2 đoạn cần sửa mỗi cánh, lệch tới +56% — nhưng không tách được 4 hay 2 đoạn tái dùng, vì tóm tắt chỉ có số **gộp**. Nay `tom_tat` mang **từng đoạn** (không kèm lời thoại) ⇒ lượt nghiệm thu kế đo được ngưỡng `0,08` tự khai *chưa đo*. `test_476` 8 bài. Xem `PHA22_VUA_KHE.md` |
| 25 | Shared artifact cache + leases | **XONG phần tái dùng — MỘT PHẦN** | `cache_chung.py`: khoá **địa chỉ nội dung** cho tách nguồn + chép lời (nghiệm thu thật: cánh 2 tính lại 66 s cho cùng đầu vào). 🔴 Vân tay giai đoạn KHÔNG dùng được làm khoá — nó không mang danh tính nguồn, hai video khác nhau cùng settings sẽ trùng. Chủ sở hữu trong khoá **và** WHERE; chép chứ không trỏ; từ chối khi thử lại / artifact chết / phân vai suy giảm. Tám lần tiêm, tám lần đỏ — và lượt đầu bắt được một **phép kiểm** sai. ⛔ Chưa có một-tính-nhiều-chờ. Xem `PHA25_CACHE_CHUNG.md` |
| 23 | Audio Studio | **XONG ba điều khiển** | Mức nền so với lời · tắt nền · hạ nền theo lời · fade. 🔴 **Đo trước khi dựng**: bản phối kết thúc bằng `loudnorm`, nên (giọng 0, nền −6) và (giọng +3, nền −3) ra CÙNG một tệp (SNR 69,7 dB) ⇒ thanh "mức giọng" riêng là tính năng giả; giao diện có MỘT thanh. Hạ theo lời đo 6,5–7,8 dB dưới lời, −0,33 dB giữa câu. Mặc định ra đúng từng ký tự chuỗi cũ ⇒ không nâng phiên bản. Chín lần tiêm, chín lần đỏ; kiểm trình duyệt thật 1280 + 375 px. ⛔ Mức lời gốc (cần stem lời) và nhạc thay thế (ADR) không làm. Xem `PHA23_AUDIO_STUDIO.md` |
| 17, 18, 20, 21, 24, 28–34 | — | **CHƯA MỞ** | Ba hạng (ĐƯỜNG / CẦU / MÓNG) + thứ tự phụ thuộc thật: `MA_TRAN_KHOANG_TRONG.md`. ⚠️ Chỉ pha 15 là MÓNG; phần lớn còn lại là **CẦU** — năng lực đã có, chưa có đường gọi từ ASV. Nghiệm thu hạng đó phải hỏi HAI câu: *có đường không* rồi *có xe trên đường không* |

## Nợ kỹ thuật mở, không thuộc pha nào

| Mục | Hiện trạng | Vì sao chưa đóng |
|---|---|---|
| `test_448` | ✅ **XANH 10/09 12:49** — 26 passed, 1 skipped, 0 failed | Ba nguyên nhân đều đã vá **có đối chứng**: trần token · `sqlite3 database is locked` · LUFS T4. Trần token nay có mệnh đề **dương** — đúng giai đoạn từng hỏng chạy qua ở cả hai cánh. Xem `CHAN_DOAN_TEST_448.md` §12 |
| Đo `chuyen_loi_thoai` trên đường thật | **XONG 10/09** | 15 lượt. Nhu cầu thật **4.186–6.843** token; trần cũ 4.096 nằm dưới nhu cầu ở **5/5** lượt. Trần mới 16.384 dư 2,4×. Xem `CHAN_DOAN_TEST_448.md` §11 + `bang_chung/do_tran_token_20260910.txt` |
| `nghiem_thu_hien_hanh.json` | ✅ **TÁI SINH XONG 10/09 12:49** | `giong_that=True`, `model_that=True`, `thay_the=[]` — giọng `LTTStudioVoice` thật ở `:8120`, model thật qua pool → máy B, PostgreSQL thật. **Cả hai** cánh 11/11 giai đoạn, `tai_ve` 200, QC 13/13 mục. Không tái sinh từ một lượt xanh: lượt trước đó (11:47) bị loại vì `cat_thong_minh` hỏng do **tranh cổng giọng**, không phải do sản phẩm |
| Xem trước lớp phủ/logo trên khung hình | chưa có | `vung_che` kéo thả được, lớp phủ và logo thì chưa — khách đặt toạ độ bằng số |
| 🔴 **Trần job `content_process` dưới sàn nhu cầu** | ASV nhận video **120 phút**; ở 142 giây/lô (đo được) chỉ **~20 phút video** lọt trần job 60 phút. Các lô chạy **tuần tự** và vượt trần job **không được thử lại** (`test_217`). Xem `CHAN_DOAN_TEST_448.md` §10 — ba đường sửa, và không đường nào chọn được trước khi đo `giây/lô` trên đường thật của ASV |
| **Resume thật** khi tải lên | chưa có | Hiện là *thử lại cả tệp* 3 lần. Resume theo byte cần multipart upload của R2 + một bản ghi tiến độ |
| 🔴 **`rang_giong` không lọc theo LÀN ngôn ngữ** | chặn bởi một phụ thuộc, không phải bởi công sức | Q121 làm `ltt_voice.features.giai_giong` **TỪ CHỐI** cặp văn-bản-`vi` + giọng-làn-`en` (`voice_language_mismatch`), và nó từ chối ở chỗ **mọi** cửa đi qua — gồm đường job của ASV. `rang_giong.py:198` gọi `giong_mau.loc(gioi, vung, phong_cach)` **không có làn**.<br><br>⚠️ Hôm nay chưa nổ được: cả 20 preset engine đều làn `vi`. Nó nổ vào đúng ngày kho giọng mẫu có một giọng `en` — và khách ASV sẽ thấy một câu lỗi về *làn ngôn ngữ* mà họ không có ngữ cảnh để hiểu.<br><br>**Phụ thuộc, kiểm bằng một dòng:** `grep -n "ngon_ngu" apps/ltt_voice/giong_mau.py` — khi `loc()` nhận `ngon_ngu` trên nhánh này thì mở được. (Do phiên `voice-language-compatibility` thêm, hiện ở nhánh riêng.)<br><br>⛔ Và **đừng gõ `ngon_ngu="vi"`**: `vi` không phải hằng số của `rang_giong`, nó là **hệ quả** của việc `HAU_MVP.multilingual_target` chưa mở. Chép nó vào đây tạo bản sao thứ hai, và bản sao ấy sẽ không đổi vào ngày pha 24 mở đa ngôn ngữ — lúc đó ASV lọc giọng `vi` cho bản lồng tiếng Anh, cùng một thất bại im lặng chỉ đổi chiều. Lấy làn từ **đích của lần chạy**. |

## Quy tắc riêng của chương trình này

1. **Không hạ mốc bánh cóc** để một lượt gate xanh. Mốc chốt **tập hợp**, và hạ
   nó là bỏ chính câu hỏi nó đang hỏi.
2. **Bằng chứng engine, không phải HTTP 200.** Mỗi tính năng đổi điểm ảnh phải
   có một phép đo trên tệp ra (PSNR/LUFS), và phép đo phải **không mất mát** —
   xem §4 của `PHA11_LOP_PHU_CHU.md` cho một bản đo sai vì `libx264`.
3. **Đối chứng là tiêm bản cũ xem có ĐỎ không**, và bản thật phải xanh trước.
4. **Kiểm trình duyệt thật** sau mỗi thay đổi giao diện, ở **cả** 1280 và 375.
   Ba lần trong chương trình này, lỗi chỉ trình duyệt thấy — và không lần nào
   tràn ngang, nên chốt `overflow` im lặng cả ba.
