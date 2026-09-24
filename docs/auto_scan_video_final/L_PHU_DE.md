# L-H phu-de — năm chế độ phụ đề, dùng lại AutoSub (asv-final, 22/09/2026)

Nhánh `phien/asv-final-phu-de`. Test mới: `test_2070` (35 bài), `test_2071` (15 bài).
Bằng chứng máy thật: `bang_chung/phu_de/` (script + JSON, chạy lại được).

## 1. Năm chế độ — định nghĩa và lý do

| `che_do` | chữ trên hình | vị trí | kiểu chữ |
|---|---|---|---|
| `tat` (OFF) | — (vẫn xuất `.srt` được, `chu` chọn được) | — | — |
| `tu_dong` (AUTO) | **bản dịch** | **tự tránh dải phụ đề gốc** | preset (`default`) |
| `nguon` (SOURCE) | **lời gốc** = `goc` của tài liệu `CONTENT_PROCESS` | của preset | preset |
| `dich` (TRANSLATED) | bản dịch (`chu`, đích `vi`/`en`) | của preset | preset |
| `tu_chon` (CUSTOM STYLE) | `chu` = `dich` \| `nguon` | preset + tinh chỉnh | preset + 18 trường tinh chỉnh |

- **Một chỗ trả lời "chữ nào":** `phu_de.chu_cua(ho_so)`.
- **SOURCE dùng bản ghi chuẩn, không dùng ASR trực tiếp.** `van_ban.dung` giữ cả `goc` (lời của
  bản ghi) và `chu` (bản dịch) trong CÙNG mục, cùng `ma`. Khi lane OCR (L-E) đổi nguồn lời và ghi
  `nguon_loi` vào bản ghi, `goc` vẫn là lời chuẩn — SOURCE không cần sửa. Phụ đề lời gốc dùng
  đúng mốc trục RA của bản dịch (`ke_hoach.dat_tai_ms`), không có trục thời gian thứ hai.
- **AUTO = bản dịch, vì Auto Scan luôn lồng tiếng**: phụ đề khớp lời khách đang nghe; lời gốc
  thường đã nằm trên hình (hardsub) nên khắc lại là che thêm hình mà không thêm ý.
- **AUTO tự quyết vị trí** — đây là thứ phân biệt nó với TRANSLATED:
  - dải phụ đề gốc **đã che** (khách đánh dấu `danh_dau_phu_de`; `_loc_lam_mo` làm mờ mọi vùng)
    ⇒ đáy chữ mới trùng đáy dải: `alignment=2`, `margin_v=(1−y1)·H`, `safe_area_percent=0`;
  - dải **chưa che** (đường cho hộp OCR của L-E, `da_che=False`) ⇒ đặt trên đỉnh dải + 2 % H;
  - chưa biết dải ⇒ vị trí preset + giao diện hiện gợi ý đánh dấu dải.
  - Thứ tự: preset < vị trí tự động < tinh chỉnh của khách. Vị trí tự động áp bằng
    `model_copy` (không duyệt): `margin_v` của mô hình chặn ở 200, dải 0,76 trên khung 1080 cần 281.

### Đo dải hardsub trên 4 clip thật (`do_dai_hardsub.py`, 60 khung/clip, chỉ đọc)

| clip | khung | dải hardsub (phần chiều cao) | đỉnh/nền |
|---|---|---|---|
| v1 牛肠 | 1024×576 | 0,927–0,983 | 92× |
| v2 露营 | 864×576 | 0,909–0,971 | 59× |
| v3 跳伞 (game) | 836×576 | 0,761–0,795 | 32× |
| v4 气枪 | 1024×576 | 0,899–0,958 | 24× |

Kiểu `default` vẽ ở 0,778–0,941 (đo bằng diff điểm ảnh trên v1) ⇒ **chồng hardsub ở cả 4 clip**.
⚠️ `PLAN.md` ghi v1 "không thấy hardsub ở 40 s": đo 60 khung cho dải rõ nhất trong bốn (92×) —
v1 CÓ hardsub (vd. 想要牛肠好吃 ở giây 20–30).

⛔ Phát hiện dải tự động lúc chạy là một heuristic (loại B) ⇒ KHÔNG ship; phép đo trên chỉ dùng
làm bằng chứng. Nguồn dải lúc chạy là vùng khách đánh dấu, và sau này hộp OCR của L-E.

## 2. False feature đã bịt: `danh_dau_phu_de`

`vung_che.LOAI_DANH_DAU_PHU_DE` khai nghĩa *"đừng đặt phụ đề dịch chồng lên đây"*, giao diện cho
vẽ, bản dựng lưu — **không một dòng nào đọc `loai` đó** (và `_loc_lam_mo` làm mờ nó như `lam_mo`).
`phu_de.dai_phu_de_goc` là người đọc đầu tiên; `test_2070::test_dai_phu_de_goc_chi_doc_vung_DANH_DAU`.
Bẫy PHA16 (nhấn mạnh ở hai cấp) giữ nguyên lời giải `nhan_manh()`; `test_472` vẫn xanh.

## 3. Mở rộng AutoSub (không engine mới trong ASV)

Khai CẢ HAI phía (`apps/autosubvideo/__init__.py` + `tools/lint_app_contract.py`):
- `segmenter.wrap_lines` — ngắt dòng biết chữ Hán (rộng 2 cột, không mở dòng bằng `，。`).
  `_wrap_text` cũ chỉ ngắt theo dấu cách ⇒ câu tiếng Trung ra MỘT dòng dài vô hạn. Chữ có dấu
  cách đi nguyên `_wrap_text` (byte-identical, có test). `segment()` của AutoSub hưởng luôn.
  ASV bỏ bộ ngắt tự viết `_ngat_dong` → gọi `wrap_lines`.
- `ass_builder`: karaoke `word` trên chữ Hán ⇒ một `\kf` mỗi chữ (trước: 0 thẻ — `word` im lặng
  không làm gì trên phụ đề tiếng Trung).
- `font_checker.missing_glyphs(font, text)` — glyph THẬT qua `fontTools` cmap (`is_font_available`
  chỉ trả lời "có font tên đó"). Arial: đủ tiếng Việt, thiếu toàn bộ chữ Hán; YaHei: đủ Hán.
  ASV `glyph_thieu()` hỏi font kiểu → fallback của kiểu → `Arial, Microsoft YaHei, SimSun`; ký tự
  không font nào vẽ được ghi vào `ho_so["glyph_thieu"]` + log (không chặn: libass còn lùi qua
  DirectWrite rộng hơn). Render thật 9 preset với câu Việt + Hán trên khung v1; xem bằng mắt 6 preset
  (default, ltt_brand, tiktok_bold, cinematic, meme_punch, kids_color): đủ dấu tiếng Việt và chữ Hán,
  dù Montserrat/Anton/Oswald/Helvetica Neue không cài trên máy A (libass tự lùi).

## 4. Xem trước = render, từng điểm ảnh

Một hồ sơ → một `.ass` → một chuỗi lọc: `xem_truoc_tu_form` = `tu_form` (cửa nộp thật) →
`viet_tep_ass` (hàm RENDER gọi) → `che_do_render.loc_cat_noi` (chuỗi `ket_xuat` dùng, cả vùng che).
Route `POST /auto-scan-video/phu-de/xem-truoc` chỉ đọc form + gọi (routes.py 873/900).

`do_xem_truoc_vs_render.py` (v2, giây 30, dải v2 đánh dấu, khoảng giữ `[0,1]+[2,4]` — có CẮT):

| chế độ | điểm lệch (không mất, png/rgb24) | PSNR vs render thật libx264 |
|---|---|---|
| tat / tu_dong / nguon / dich / tu_chon | **0 / 0 / 0 / 0 / 0** | 35,0 / 33,5 / 33,6 / 33,5 / 33,3 dB |

Từng cặp chế độ khác nhau 6,2–14,6 % điểm ảnh (mỗi chế độ đổi bản ra).
🔴 Lần đo đầu: **1.488 điểm lệch** (≤ 3 mức) chỉ ở vùng làm mờ — cùng chuỗi lọc, cùng điểm ảnh,
nhưng đầu vào PNG vs MOV làm ffmpeg thương lượng định dạng khác (một bên sang `yuva420p` ngay đầu,
bên kia sau `crop`). Sửa: xem trước đổi khung sang video `yuv420p` (định dạng h264 nguồn) TRƯỚC
chuỗi lọc (`DINH_DANG_VAO`) ⇒ 0 lệch. `-ss` đặt sau `-i` để `ass=` thấy mốc thật (giây 1,0 trong
sự kiện, qua hiệu ứng vào).

## 5. Giao diện + kiểm trình duyệt thật

`phu_de.js` (256/320 dòng): kiểu / nguồn chữ / tinh chỉnh chỉ hiện ở `tu_chon`; gợi ý đánh dấu dải
khi `tu_dong` chưa có dải; nút xem trước chụp khung đang dừng của `<video>` (canvas → PNG) và
hiện PNG máy chủ trả. Kiểm bằng Playwright + Chrome thật trên `tools/asv_browser_server.py`
(`kiem_trinh_duyet.py`, cookie phiên sinh từ CSDL test, không gõ mật khẩu): 5 chế độ → **5 PNG
khác nhau**, HTTP 200, 0 lỗi console, gợi ý hiện→ẩn khi đánh dấu dải. Hai lỗi chỉ lộ trên trình
duyệt, đã sửa: JS gửi `che_do` (khớp thời gian) thay cho `preset`; hai yêu cầu song song về không
theo thứ tự làm khung chế độ trước đè chế độ vừa chọn (nay chỉ hiện yêu cầu mới nhất).
Một request `blob:` hỏng còn lại (URL khung cũ bị thu hồi) — vô hại.

## 6. Còn lại / điều phối cần biết

- Hồi quy (89 tệp: mọi `test_4*asv*`, 81, 85, 103, 1110, 306, 147, 148, 2070, 2071; qua
  `chay_nang.py`, `-n 6`): 1728 đạt, 5 đỏ. 1 đỏ của lane này (`check_bo_qua`: 3 `skipif` mới ở
  `test_2071`) — đã gỡ, test glyph nay chạy cứng. 4 đỏ **có sẵn từ gốc nhánh, không thuộc lane**:
  `test_427` (REBASE_MAP thiếu `ngon_ngu`), `test_418` (`NgonNguError` chưa phân loại),
  `test_448` (`chep_loi/1` vs `/2`), `test_453` (`la_tien_trinh_con` trong `apps/asv_gpu`).

- `routes.py` sửa (thêm 1 route) — L-A cũng có thể sửa tệp này; `messages.po/.mo` thêm 17 mục.
- `glyph_thieu` chưa vào QC (`qc.py` thuộc L-B): ho_so mang khoá, QC đọc được khi cần.
- Dải `danh_dau_phu_de` áp cả video (bỏ `tu_giay/den_giay` khi tính vị trí).
- Độ mờ `_loc_lam_mo` trên dải hardsub 40 px (bán kính 5 px) vẫn đọc lờ mờ được chữ Hán — thuộc
  lane render/vùng che (L-G), không sửa ở đây.
- Cỡ chữ: `build_ass` dùng PlayRes = khung thật (y như AutoSub `jobs.py`), nên 48 px trên 576 p là
  8 % chiều cao — quyết định của AutoSub, giữ nguyên.
- Mốc từng từ (karaoke thật theo lời đọc) vẫn nợ: kế hoạch chưa mang mốc từ; `\kf` chia đều.
