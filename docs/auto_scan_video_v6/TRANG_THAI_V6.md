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
| 00–05 | nền, hợp đồng, kiến trúc | **CHƯA MỞ** | |
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
| 17–34 | — | **CHƯA MỞ** | Ba hạng (ĐƯỜNG / CẦU / MÓNG) + thứ tự phụ thuộc thật: `MA_TRAN_KHOANG_TRONG.md`. ⚠️ Chỉ pha 15 là MÓNG; phần lớn còn lại là **CẦU** — năng lực đã có, chưa có đường gọi từ ASV. Nghiệm thu hạng đó phải hỏi HAI câu: *có đường không* rồi *có xe trên đường không* |

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
