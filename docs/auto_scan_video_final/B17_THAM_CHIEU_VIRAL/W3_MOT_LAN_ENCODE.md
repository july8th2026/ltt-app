# W3 — Hợp đồng đầy đủ của `burn_phude` (Viral, MỘT lần encode)

## Độ phủ — bằng SỐ

- Biên hàm thật: `def burn_phude` bắt đầu **`localize.py:6560`**, kết thúc **trước
  `:8533`** (`def _kiem_lo_sau_render` — hàm KHÁC, cấp module, không lồng bên
  trong). Tổng **1.973 dòng** (8532 − 6560 + 1). V6 ghi `:6560-8533` là lấy mốc
  "dòng `def` kế tiếp" làm biên trên — số dòng thật là 1.973, không phải "~2.000"
  tròn nhưng cùng bậc.
- Đọc **nguyên văn** trong phiên này: **~340 dòng thật** trải trên khoảng
  `:6560-8533` (đọc theo khối, không tuyến tính) — chữ ký + docstring
  (`:6560-6600`), toàn bộ khối tính `cat_cuoi`/`_burn_giay` (`:6591-6668`),
  khối quyết định `co_blur`/`co_khung`/`co_reframe`/gop (`:6962-7000`), dựng
  filtergraph video (`:7264-7320`, `:7360-7392` chunk N=99/60, `:8175-8277`
  reframe + `_emit_speed`), khối audio (`:8376-8425`), và toàn bộ đuôi hàm —
  chạy lệnh, dọn file tạm, đường lùi, gọi `_kiem_lo_sau_render`, `return`
  (`:8465-8532`).
- **CHƯA soi**: phần lớn khối dựng dải che ĐỘNG/che TĨNH chi tiết
  (`:6670-7263`, ~590 dòng — logic gom track, BLUR_GOM, bo góc, "vá bằng hình
  sạch", kéo mép) và khối `khung_filter_parts`/`text_wm_parts` gọi ra
  `xu_ly_video.py` (thân KHÔNG đọc, chỉ đọc điểm gọi trong `burn_phude`).
  Không đọc thân `_srt_to_ass_pos` (nơi `karaoke`/`motion_tu` thực sự dùng) —
  chỉ thấy điểm gọi (`:7164`, `:7192`). Không đọc thân `xu_ly_video.khung_filter_parts`,
  `text_wm_parts`, `_bieu_thuc_warp`.
- ⭐ Sửa lại một con số của brief: **`_tham_so_goi` chụp 32 tham số ở dòng đầu
  (`:6560-6566`), không phải 25.** Đếm trực tiếp trên chữ ký thật (7 dòng tham
  số): `video, vi_srt, out_mp4, che_chu, audio_path, log_fn, zoom_ap, extra_vf,
  speed, wm_path, wm_pos, wm_scale, bg_path, bg_vol, bg_loop, blur_band,
  blur_segs, logo, text_wm, blur_boxes, banner_boxes, video_slow, time_warp,
  ratio, karaoke, motion_tu, blur_band_manual, mirror, sub_band, goc_vol,
  sub_khung, cat_cuoi` = 32. Bản thân comment ở `:6588-6589` chỉ nói *"chép tay
  thì ai thêm tham số mới sau này, đường lùi sẽ âm thầm đánh rơi nó (lỗi im
  lặng, chỉ lộ ra ở ca hiếm)"* — tức số tham số **đã tăng theo thời gian** kể
  từ khi V6 đếm; 25 là một bản đếm cũ, không phải trạng thái hiện tại.

---

## Phần 1 — Chữ ký đầy đủ (32 tham số)

Cột "nghĩa" chỉ ghi những gì có DẪN CHỨNG (docstring `:6572-6584` hoặc comment
tại điểm dùng); không tự đoán — thiếu dẫn chứng thì ghi ❓.

| # | tham số | kiểu/mặc định | nghĩa (dẫn chứng) | ở TA lấy từ đâu |
|---|---|---|---|---|
| 1 | `video` | str, bắt buộc | đường dẫn file video nguồn | `RENDER`: artifact video nguồn/GD1; `IMAGE_FINISH`: MP4 do `render` xuất (`giai_doan_hinh_anh.py:_ke_cat` đọc trực tiếp file) |
| 2 | `vi_srt` | str/None | đường dẫn `.srt` tiếng Việt để burn phụ đề | `RENDER` đọc `duong_ass` dựng từ `ban_dung.json` (khoá `tieng.master`) — dạng khác (ASS thay vì SRT) |
| 3 | `out_mp4` | str, bắt buộc | đường dẫn file MP4 xuất ra | artifact `mp4` của `render` (và, nếu gộp, của `image_finish`) |
| 4 | `che_chu` | bool=True | "*Mặc định (chỉ che chữ + burn phụ đề): đường ĐƠN GIẢN như cũ*" (`:6567`) — bật/tắt che chữ gốc | ⛔ **KHÔNG CÓ giai đoạn nào che chữ gốc** trong `CHUOI` (V6 đã ghi: mã đo vùng có ở `de_xuat_vung.py`/`do_vung_ocr.py` nhưng không phải giai đoạn) |
| 5 | `audio_path` | str/None | track audio thay thế (dẫn: comment `:8390-8394` — mang HAI nghĩa: lồng tiếng MỚI, hoặc giọng gốc đã tách nhạc `_au_xn`, caller phải tự phân biệt) | `COMPOSE`: `tieng.master.khoa` (ban phối master.wav) |
| 6 | `log_fn` | callable=`log` | hàm ghi log | hạ tầng `thi_hanh`/logging của job, không phải setting sản phẩm |
| 7 | `zoom_ap` | float=1.0 | hệ số zoom crop; `>1.0` mới kích hoạt (comment `:6985-6990`: thiếu điều kiện này từng làm zoom "rơi im lặng", bắt bằng test md5 khung) | ❓ CHƯA BIẾT — không thấy setting zoom tương đương trong `RENDER`/`IMAGE_FINISH` đã đọc |
| 8 | `extra_vf` | list/None | "*list filter video chèn TRƯỚC che/sub*" (`:6573`) | `IMAGE_FINISH`/GD2 "điểm ảnh" (`hflip`+`eq`) theo comment `che_do_render.py:80-81,783-787` |
| 9 | `speed` | float=1.0 | "*tăng tốc — setpts (video) + atempo (audio), áp ở CUỐI*" (`:6574`); bị CLAMP `[0.5, 2.0]` (`:6591-6592`, giá trị ngoài dải làm `atempo` fail) | `bien_tap["toc_do"]` — B6 chốt áp **CUỐI `image_finish`** (khớp Viral, V6 đã xác nhận) |
| 10 | `wm_path` | str/None | file ảnh watermark, gộp cùng lần encode (`:6575`) | ❓ CHƯA BIẾT (có `logo` qua `_loc_logo` ở `che_do_render.py`, nhưng chưa đối chiếu là cùng khái niệm) |
| 11 | `wm_pos` | str="20:20" | toạ độ `overlay=` của watermark (đọc thẳng từ code dùng, không có trong docstring) | ❓ CHƯA BIẾT |
| 12 | `wm_scale` | str="" | tham số `scale=` áp lên watermark trước khi overlay (đọc từ code `:8371` khu vực `co_wm`) | ❓ CHƯA BIẾT |
| 13 | `bg_path` | str/None | file nhạc nền | ❓ CHƯA BIẾT trong `RENDER`/`COMPOSE` đã đọc (chưa grep sâu — không loại trừ tồn tại dưới tên khác) |
| 14 | `bg_vol` | float=0.25 | âm lượng nhạc nền 0-1 (`:6576`) | ❓ CHƯA BIẾT |
| 15 | `bg_loop` | bool=True | "*True = nhạc NGẮN hơn video → LẶP LẠI; False = phát 1 lần rồi im lặng*"; nhạc DÀI hơn LUÔN tự cắt vừa khít bất kể cờ này (`:6577-6580`) | ❓ CHƯA BIẾT |
| 16 | `blur_band` | tuple `(y0,y1,H[,x0,x1])`/None | "*làm mờ ĐÚNG dải sub gốc (dò bằng `dai_sub`) thay hộp đen cố định*" (`:6670`); có quy ước "dummy khác None nghĩa là không cần dò" (`:6698-6707`, chính là bẫy [hai-trạng-thái-gộp-thành-một-giá-trị] mà MEMORY đã ghi) | ⛔ không giai đoạn — cùng nhóm với `che_chu` |
| 17 | `blur_segs` | list `(t_on,t_off,y0,y1,x0,x1)`/None | "*blur ĐỘNG bám sub DI CHUYỂN (mỗi đoạn 1 vị-trí, bật theo thời gian)*" (`:6671`); ⚠ chủ dự án Viral **đã CHỐT BỎ che động** 06/08/2026, chỉ còn che tĩnh (`:6674`) — tham số còn tồn tại trong chữ ký nhưng nhánh dùng nó đang bị khoá ở tầng gọi | ⛔ không giai đoạn |
| 18 | `logo` | dict `{"path":...}` | ảnh logo dán đè (dùng ở `co_khung`, `:6964`) | `che_do_render.py:_loc_logo` (RENDER dùng khái niệm logo riêng, thứ tự `logo -> chu -> phu de` — xem Phần 2) |
| 19 | `text_wm` | ? | watermark dạng CHỮ, kiểm qua `xu_ly_video.co_text_wm(text_wm)`; áp SAU reframe để "*chữ đúng góc khung + đúng cỡ*" (`:8257`) | `che_do_render.py:_loc_chu` (lớp chữ phủ — chưa đối chiếu 1-1) |
| 20 | `blur_boxes` | list hộp | ô XOÁ (vá bằng hình sạch/copy dải liền kề) — PHẢI chạy TRƯỚC mọi node che, xem "XOÁ TRƯỚC — CHE SAU" Phần 2 | ❓ CHƯA BIẾT — chưa thấy khái niệm "ô xoá logo gốc" tương đương trong RENDER đã đọc |
| 21 | `banner_boxes` | list hộp | dịch banner "SAU CÙNG, bằng CHÍNH phiên Gemini đã dịch phụ đề" (theo V6 `:19130-19184`, ngoài phạm vi `burn_phude` — trong hàm chỉ thấy nó góp phần bật `co_khung`, `:6964`) | ❓ CHƯA BIẾT |
| 22 | `video_slow` | float=1.0 | hệ số làm chậm ĐỀU cả video (Video Assist uniform); nhân với `speed` thành `_vspd` (`:8206-8210`) | ❓ CHƯA BIẾT tên setting tương đương ở TA |
| 23 | `time_warp` | list `(o0,o1,f)`/None | warp tốc độ THEO TỪNG ĐOẠN (per-segment), dùng để giãn/nén khớp lồng tiếng; "*mỗi đoạn warp (o0,o1,f) → trim đoạn + setpts=PTS/(spd×f) + concat*" (`:8208`) | `TIMING_ALIGN` (ta doi truc — B6 chốt "KHÔNG được đổi trục", khác cơ chế piecewise này) |
| 24 | `ratio` | str="" | khoá tỉ lệ khung đích, tra `xu_ly_video.KHUNG_RATIO.get(ratio)`; rỗng/không khớp ⇒ không reframe (`:6972`) | `khung ra` — RENDER (`giai_doan_ket_xuat.py`: *"khung ra phải đúng: sai khung thì phụ đề .ass bị đặt sai chỗ mà KHÔNG lỗi nào báo"*) |
| 25 | `karaoke` | bool=False | truyền xuống `_srt_to_ass_pos(..., karaoke=karaoke, ...)` (`:7164`, `:7192`) — **thân hàm đó chưa đọc**, chỉ xác nhận tham số được CHUYỂN TIẾP, chưa xác nhận cơ chế | ❓ CHƯA BIẾT |
| 26 | `motion_tu` | int=0 | cùng nhóm, truyền xuống `_srt_to_ass_pos(..., motion_tu=motion_tu)` — chưa đọc thân | ❓ CHƯA BIẾT |
| 27 | `blur_band_manual` | bool=False | đánh dấu `blur_band` do NGƯỜI DÙNG tự đặt (không phải dò tự động) — tắt các guard tự động (ép min-width `:6717`, canh giữa `:6729`, ép `_ymin` `:6950`) khi cờ này bật | ❓ CHƯA BIẾT — có thể ứng với "khách kéo tay dải che" trong editor ta, chưa đối chiếu |
| 28 | `mirror` | bool=False | "*video ĐẦU VÀO (`video`) đã bị lật ngang THẬT ở 1 pass encode TRƯỚC đó... lần gọi NÀY không tự lật nữa... toạ độ blur_segs/blur_band/blur_boxes/logo vẫn tính theo video GỐC (trước lật) → phải lật toạ độ x cho khớp*" (`:6578-6584`) | GD2 "điểm ảnh" (`hflip`) — `che_do_render.py:80-81` liệt `hflip` cùng nhóm mirror |
| 29 | `sub_band` | tuple/None | "DẢI ĐẶT PHỤ ĐỀ nếu người dùng TÁCH RIÊNG trong editor; không có → dùng chính `blur_band`... CHỈ đổi CHỖ ĐẶT CHỮ, KHÔNG đụng vùng che" (`:6996-6998`) | ❓ CHƯA BIẾT |
| 30 | `goc_vol` | float/None | "ÂM LƯỢNG TIẾNG GỐC: `0.0` = tắt hẳn, `1.0` = giữ nguyên, `None` = không đụng" (`:8387`); CLAMP `[0.0, 2.0]` (`:8398`) | `COMPOSE`/`TIMING_ALIGN` — mảng "trộn nền bảy nhánh" của V6 (`#25`, `:19957-20187`) |
| 31 | `sub_khung` | bool=False | "khách kéo dải TRONG lúc đang xem theo khung MỚI (sau reframe) ⇒ toạ độ `sub_band` hiểu theo khung xuất" (`:7128`) — hoãn vẽ subtitle tới SAU reframe khi bật | ❓ CHƯA BIẾT |
| 32 | `cat_cuoi` | float=0.0 | cắt ĐUÔI video, tính bằng **giây NGUỒN**; thực hiện bằng cách hạ trần `-t` của lệnh ffmpeg (không phải filter `trim`) — xem Phần 4 câu 1 | `IMAGE_FINISH`/`ke_cat.py` — nhưng ta cắt bằng RE-ENCODE riêng (GD2), Viral cắt bằng hạ `-t` trong CHÍNH lần encode chính |

---

## Phần 2 — Thứ tự filter, nguyên văn + lý do

### 2.1 — Dòng tóm tắt 4 bước (đúng như brief trích)

Nguyên văn comment `:7264`:

```
# --- video: [biến đổi hình] -> [watermark] -> [che chữ + burn sub] -> [setpts tăng tốc] ---
```

Và docstring `:6572`:

```
speed    : tăng tốc — setpts (video) + atempo (audio), áp ở CUỐI (whisper đã nghe tốc độ gốc).
```

### 2.2 — Thứ tự THẬT, đọc trực tiếp từ mã (rộng hơn 4 bước tóm tắt ở trên)

⚠️ Dòng tóm tắt `:7264` chỉ đúng cho nhánh KHÔNG có `co_khung`/`co_reframe`.
Đọc hết khối dựng `fc` (`:7264-8277`), thứ tự node THẬT là:

| thứ tự | filter/khối | neo dòng | điều kiện bật | ta có tương đương? |
|---|---|---|---|---|
| 0 | `format=yuv420p` (ép chuẩn hoá màu khi hwaccel GPU bật) | `:7271-7275` | `_hw_vf` (hwaccel đang bật) | ❓ chưa biết |
| 1 | `extra_vf` (biến đổi hình: hflip/eq/...) | `:7276-7277` | `extra_vf` khác rỗng | GD2 "điểm ảnh" |
| 2 | watermark ẢNH: `scale=` (tuỳ chọn) + `overlay={wm_pos}` | `:7278-7282` | `co_wm` | ❓ chưa biết |
| 3 | lật toạ độ `blur_segs`/`blur_band` theo x (KHÔNG chèn filter, chỉ tính lại số) | `:7284-7292` | `mirror` hoặc `extra_vf` có `hflip` | tương đương "đảo toạ độ khi mirror" |
| 4 | **`blur_boxes` (ô XOÁ) — chạy TRƯỚC mọi node che** | `:7304-7315` | `blur_boxes` khác rỗng | ❓ chưa biết |
| 5 | che chữ (`blur_band`/`blur_segs`, dựng `post`/node `vmsk` riêng — chunk hoá, xem 2.4) + `subtitles=` burn phụ đề vào `post` | `:7320-8202` (khối lớn, chưa soi hết) | `co_blur`; `vi_srt and not _sub_sau_khung` | ⛔ không giai đoạn |
| 6 | (nếu `co_khung`) `khung_filter_parts`: logo / ô xoá còn lại / banner | `:8244-8262` | `co_khung` | `che_do_render.py` (thứ tự nội bộ CỦA TA cũng là `logo -> chữ -> phụ đề`, xem 2.5) |
| 7 | `setpts` tốc độ — đơn (`_spd_node`) hoặc piecewise (`time_warp`, hàm `_emit_speed`) | `:8210-8267` | `co_speed` hoặc `_has_warp` | B6: `toc_do` áp CUỐI `image_finish` |
| 8 | reframe tỉ lệ (`_kr`): nền mờ (downscale-upscale) + `overlay=(W-w)/2:(H-h)/2` giữa khung | `:8276-8360` | `co_reframe` | `khung ra` của RENDER |
| 9 | `text_wm` (watermark CHỮ) — cố ý áp SAU reframe "để chữ đúng góc khung + đúng cỡ" | `:8257 (comment)`, `:8370-8375` | `co_text_wm(text_wm)` | `che_do_render.py:_loc_chu` |
| — | (song song, không cùng chuỗi) audio: nguồn → `atempo` → trộn `amix` nhạc nền → `alimiter` | `:8376-8425` | — | `COMPOSE`/`TIMING_ALIGN` |

⇒ Dòng `:7264` là đúng **hình dạng chung** nhưng bỏ sót: bước 0 (format fix),
bước 3-4 (lật toạ độ + xoá logo), và quan trọng nhất — **bước 8-9 (reframe +
text-watermark) chạy SAU CẢ setpts**, không nằm trong 4 mắt xích được tóm tắt.

### 2.3 — Lý do thứ tự (nguyên văn, đây là phần MEMORY nhấn mạnh — "ngăn người sau đổi cho tiện")

1. **Speed áp CUỐI** — docstring `:6572`: *"áp ở CUỐI (whisper đã nghe tốc độ
   gốc)"*. Time_warp piecewise nhắc lại lý do ở `:8208-8209`: *"Sub/blur/khung
   đã áp lên `cur` TRƯỚC bằng `enable=between(t,...)` trên mốc GỐC → tự bám
   tốc độ đoạn (đúng)"* — nghĩa là mọi filter `enable=` phía trên đọc `t` theo
   TIMELINE GỐC; nếu setpts chạy trước, `t` sẽ bị nén/giãn và các mốc
   `between(t,a,b)` lệch khỏi ý định.

2. **`blur_boxes` (xoá) PHẢI trước mọi node che — "XOÁ TRƯỚC — CHE SAU"**
   (comment đầy đủ `:7293-7303`, chốt 04/09/2026, *"chủ dự án thấy trên video
   thật"*):
   > *"Dải che chữ gốc hoạt động bằng cách LẤY MỘT DẢI HÌNH NGAY TRÊN nó rồi
   > dán xuống (`crop=1280:110:0:490` → `overlay=0:610`). Watermark/logo đang
   > nằm trong dải NGUỒN đó thì bị CHÉP XUỐNG thành BẢN SAO; ô xoá chạy SAU
   > chỉ xoá bản GỐC, còn bản sao thì KHÔNG AI che ⇒ video ra có watermark ở
   > chỗ video gốc KHÔNG HỀ CÓ (đo thật: y≈500 hiện lại ở y≈620)."*
   Và hệ luận ngược — thứ THÊM VÀO (logo/banner/chữ) phải chạy SAU che, không
   được gộp làm một lượt gọi: *"đặt trước thì đến lượt CHÚNG bị chép xuống, mà
   để dải che đè lên logo khách vừa đặt cũng sai."*

3. **Reframe áp SAU CÙNG (sau che+sub+khung+speed)** — comment `:8276-8277`:
   *"GỘP REFRAME 9:16/16:9 vào CÙNG encode... Áp CUỐI (sau che+sub+khung+speed):
   scale nền mờ + video vừa khung → overlay giữa. KHỚP `bien_doi_khung`."* Và
   dẫn chuẩn ngành ở `:8175-8176`: *"overlay/mask first at native resolution,
   scale after compositing, perform scaling ONCE."*

4. **`text_wm` áp SAU reframe, không phải trước** — comment `:8257`: *"KHÔNG
   áp watermark chữ ở đây (trước reframe/zoom) — áp SAU reframe (lên `vmap`)
   để chữ đúng góc khung + đúng cỡ."*

### 2.4 — Giới hạn `crop` + `enable=` (Phần 3, nhưng gắn liền lý do thứ tự ở 2.2 bước 5)

`crop` KHÔNG có timeline `enable=` — xác nhận bằng lời họ tự ghi (`:7362`,
verify bằng `ffmpeg -filters`), nên N dải che rời rạc từng có N chuỗi
`crop` chạy trên MỌI khung hình bất kể dải có "bật" hay không (chi phí
O(N×độ dài video)). Cách giải: gộp N dải cùng nhóm thành 1 `crop` kích thước
cố định, x/y là biểu thức `if(between(t,...))` per-frame lồng nhau, rồi 1
`gblur`+1 `overlay` với `enable=` OR của cả nhóm.

### 2.5 — Đối chiếu với thứ tự CỦA TA (`che_do_render.py`)

Ta có một comment thứ tự riêng, độc lập, tại `:719-751` của
`che_do_render.py`:

```
noi -> che -> logo -> chu
```
và cho GD1 hiện tại (chỉ nhận `vung`/`bien_tap={"toc_do":...}`):
```
logo -> chu -> phu de (toa do BAN RA) -> TOC DO (cuoi cung)
```
với `diem_anh` (hflip/eq) chen "sau hình học, trước logo/chữ/phụ đề". Đây là
CÙNG NGUYÊN TẮC "xoá/nội dung nguồn trước, phủ nhận diện sau, tốc độ cuối
cùng" mà Viral áp dụng — hai hệ tới độc lập cùng kết luận cho trục tốc độ
(V6 đã ghi "KHỚP"), và ⭐ cùng kết luận cho trục "phủ SAU hình học" — nhưng
ta CHƯA có bước "che chữ gốc" trong chuỗi này (V6 đã ghi ⛔ không có giai đoạn),
nên so sánh vị trí "che" chỉ có nghĩa từ phía Viral.

---

## Phần 3 — Giới hạn kỹ thuật đã đụng

1. **`crop` không nhận `enable=`** — xác nhận (`:7362`, dẫn nguồn
   `ffmpeg -filters` + ffmpeg-user mailing list "blur moving objects"). Giải
   bằng gộp N dải → 1 `crop` cố định + biểu thức `if(between(t,...))` cho x/y
   (§2.4).

2. **ffmpeg eval parser vỡ ở N=99 `if()` lồng nhau** — đo nhị phân trên máy
   thật (`:7372-7373`): *"N=98 OK, N=99 FAIL (\"Missing ')' or too many
   args\")"*. Phim thật (63 phút) ra đúng 100 dải sau gom — "ngay sát ngưỡng
   vỡ". Fix: `_CHUNK_MAX = 60` (`:7376`), chia nhóm theo KÍCH THƯỚC gần nhau
   (greedy) chứ không theo vị trí cố định (tránh 1 dải lỗi kéo méo cả nhóm,
   comment `:7377-7384`).

3. **`VC_WARP_MAX_DOAN` — ⚠️ KHÔNG thuộc `burn_phude`.** Đây là phát hiện
   quan trọng cần sửa lại so với brief: hằng số này sống trong
   **`_ghep_track_khop`** (`localize.py:8965-9835`, hàm ghép track lồng tiếng
   khớp thời lượng — audio, KHÔNG PHẢI video filtergraph của `burn_phude`) và
   trong khối build tham số warp phía trên nó (`:9280-9460`, `:10030-10140`,
   `:19252-19257`). Con số hiện tại trong mã **không phải 150** — mặc định đọc
   qua env là **`1200`** (`:9451`: `int(os.environ.get("VC_WARP_MAX_DOAN",
   "1200") or 1200)`, lặp lại ở `:10040`, `:19257`). Comment `:9430` tự ghi
   nhận: *"Con số 'GPU 16%, ghép 393/1795s' ở comment trên là từ thời **3671
   đoạn**, TRƯỚC..."* — tức lý do "400→150" trong brief là một mốc LỊCH SỬ đã
   bị nâng lại nhiều lần (hướng dẫn còn lại tại chỗ: *"muốn chính xác tối đa
   (chậm hơn): `VC_WARP_MAX_DOAN=400`"* — `:9407`; *"đặt `VC_WARP_MAX_DOAN=600`
   (miễn phí, phủ 27%)"* — `:9446`; *"về mức cũ: `VC_WARP_MAX_DOAN=150`"* —
   `:9449`, đọc như MỘT LỰA CHỌN LÙI cho ai gặp máy yếu/phim chậm bất thường,
   không phải giá trị đang chạy). Số liệu đo gốc (*"GPU 16%, ghép
   393/1795s"*) vẫn đúng như một PHÉP ĐO lịch sử, chỉ sai nếu đọc thành "cấu
   hình hiện hành". **Vì hằng số này nằm ngoài `burn_phude`, nó KHÔNG phải
   giới hạn của "một lần encode" — nó là giới hạn của bước ghép audio TRƯỚC
   khi vào `burn_phude`** (đầu vào `time_warp` mà `burn_phude` nhận đã bị cap
   sẵn ở tầng gọi).

4. **`_tham_so_goi` — nấc lui KÉO→LÀM MỜ** (`:6587-6590`, dùng ở
   `:8511-8524`): chụp TOÀN BỘ 32 tham số lời gọi bằng `locals()` ngay dòng
   đầu hàm (trước khi có biến cục bộ nào khác) — lý do ghi rõ: *"chép tay thì
   ai thêm tham số mới sau này, đường lùi sẽ âm thầm đánh rơi nó (lỗi im
   lặng, chỉ lộ ra ở ca hiếm)"*. Khi ffmpeg chết (`kq.returncode != 0`) VÀ
   nhánh "che kiểu KÉO MÉP" (warp hình học phức tạp hơn blur: crop+vflip+
   scale+geq+alphamerge+overlay) đã THỰC SỰ chạy (`_da_che_keo[0]`), hàm gọi
   LẠI CHÍNH NÓ (`return burn_phude(**_tham_so_goi)`) sau khi ép
   `os.environ["CHE_KEO"] = "0"` (buộc nhánh làm mờ thay vì kéo méo), rồi khôi
   phục biến môi trường trong `finally`. Comment tự nhận giới hạn: guard
   `_keo_dung_duoc` chỉ chặn được ca hình học ĐÃ BIẾT; ca lạ mà không có
   fallback này thì *"khách MẤT TRẮNG video — vì hàm này chỉ `return False`,
   KHÔNG có đường lui"*. Chỉ lùi ĐÚNG MỘT LẦN (retry không đệ quy tiếp vì lần
   gọi lại đã set `CHE_KEO=0`, `_da_che_keo` không thể True lần hai theo cùng
   nhánh).

5. **Reframe dùng downscale→upscale thay `boxblur` cho nền mờ 9:16** — lý do
   là HIỆU NĂNG, đo thật (`:8298`): *"boxblur=20:3 CPU CỰC NẶNG — ĐO THẬT 60s
   video: boxblur 46s vs downscale-upscale 12s = NHANH 3.8×; video 1.7h
   boxblur ~3 GIỜ"*. Có thử GPU (`scale_cuda`/`overlay_cuda`) và bỏ vì chậm
   hơn: *"ĐO THẬT 30s@1080p: pipeline GPU 16.7s (2.0×) CHẬM HƠN pipeline CPU
   hiện tại 5.7s (7.2×) vì overhead hwdownload/hwupload"* (`:8296-8299`).

6. **`speed` bị CLAMP cứng `[0.5, 2.0]`** (`:6591-6595`): giá trị `<0.5` cho
   `atempo` ngoài dải hợp lệ → filter `atempo` FAIL → render FAIL thẳng.
   Chuỗi `atempo=2.0,atempo=spd/2.0` xử lý `speed>2.0` (audio, `:8413-8414`)
   nhưng dải dưới `0.5` KHÔNG có xử lý tương đương, comment tự ghi *"<0.5 thì
   chưa"*.

7. **Piecewise `time_warp` cũng có trần riêng, TÁCH biệt `VC_WARP_MAX_DOAN`**:
   trong `_emit_speed`, nếu số đoạn `_n > 200` VÀ không dựng được MỘT biểu
   thức gộp (`_bieu_thuc_warp` trả rỗng), hàm lùi về `split`+`trim`+`concat` N
   nhánh và cảnh báo *"lùi split/concat (ghép chậm hơn ~2×)"* (`:8231-8235`);
   comment ghi ngưỡng này đo được *"N=1199 chậm 49% so với N=600"* — tức
   `burn_phude` tự có MỘT giới hạn piecewise-video độc lập với trần audio ở
   mục 3.

---

## Phần 4 — Ba câu trả lời trực tiếp

**1. Cắt CUỐI có nằm trong hàm này không, và ở vị trí nào trong chuỗi filter?**

Có — NHƯNG không phải một node filter, mà là hạ trần `-t` của lệnh ffmpeg.
Khối tính (`:6628-6659`) chạy TRƯỚC khi filtergraph `fc` được dựng (`fc = []`
ở `:7263`): nó tính lại `_burn_giay` (độ dài OUTPUT sau khi trừ `cat_cuoi`
quy đổi theo `speed`/`video_slow`/`time_warp`) rồi đặt `_cat_ap = True`.
`_burn_giay` này sau đó quyết định `cmd += ["-t", "%.3f" % _burn_giay]`
(`:8474`). Vậy về mặt CHUỖI FILTER, cắt cuối KHÔNG có vị trí — nó là một trần
thời lượng đầu ra áp dụng cho TOÀN BỘ encode, độc lập với thứ tự các node
video/audio. (Đây khác `_cat_cuoi_gop` ở `xu_ly_chon.py:803` mà brief nhắc
tới — đó là công tắc RÀNG BUỘC ROUTING ở tầng gọi, quyết định CÓ đẩy
`cat_cuoi` vào lời gọi `burn_phude` hay không; bản thân `burn_phude` không
biết và không cần biết về công tắc đó, nó chỉ nhận `cat_cuoi` như một số.)

**2. `_kiem_lo_sau_render` được gọi BÊN TRONG hàm này không, và ở đâu — trước
hay sau khi ghi tệp ra?**

Có, gọi ở `:8529` — dòng ÁP CHÓT, SAU khi: (a) `_burn_run` đã chạy ffmpeg và
`kq.returncode == 0` (encode thành công, file `out_mp4` đã ghi xong ra đĩa),
(b) mọi file tạm đã được dọn (`_fc_script`, `sub_tmp`, `sub_ass_tmp`,
`_khung_tw`, `_mask_tmp_files`). Ngay sau lời gọi này là `return True`
(`:8530`). ⚠️ Giá trị TRẢ VỀ của `_kiem_lo_sau_render` (số box chữ Hán còn
sót) **KHÔNG được `burn_phude` đọc/dùng** — lời gọi không gán biến, không
kiểm tra kết quả. Bản thân `_kiem_lo_sau_render` mặc định TẮT
(`CHE_RESIDUAL_CHECK` mặc định `"0"`, trả `0` ngay dòng đầu nếu tắt — docstring
của nó tự đánh giá *"MẶC ĐỊNH TẮT từ 13/08/2026... ĐO THẬT cho thấy nó KHÔNG
đáng giá: giá 10,2s/video 600s, độ phủ 8 khung/18.003 khung = 0,04%"*) — nên
trong đường chạy thông thường, đây là một lệnh gọi gần như KHÔNG LÀM GÌ.

**3. Hàm trả về gì, và ai đọc giá trị ấy?**

Trả `bool`: `True` khi encode thành công (`:8530`); `False` khi ffmpeg lỗi và
KHÔNG có nấc lui khả dụng (`:8528`); hoặc — trong ca lùi KÉO→LÀM MỜ — trả
NGUYÊN kết quả của lệnh gọi đệ quy `burn_phude(**_tham_so_goi)` (`:8522`,
tức vẫn là `bool`, chỉ là của lượt render lại). Người đọc: các điểm gọi ở
CUỐI `chay()` dùng trực tiếp làm điều kiện rẽ nhánh —
`if burn_phude(video, vi_srt, out_mp4, ...):` (`:20460`, `:20505`) và biến
`ok_lt = burn_phude(...)` (`:20382`, `:20389`, `:20403`) để quyết định bước
kế tiếp (ghi log thành công/thất bại, có tiếp tục xử lý audio tuần tự hay
không). Không có nơi nào đọc chi tiết LỖI qua giá trị trả về — lỗi cụ thể chỉ
đi qua `log_fn`.

---

## Phần 5 — Giới hạn kỹ thuật chắc chắn sẽ đụng khi gộp `render`+`image_finish`

(trả lời phần (d) của báo cáo, rút từ Phần 3+4)

- **Thứ tự "xoá trước — che sau" (§2.3.2)**: nếu gộp thành một encode, TA
  cũng phải quyết định thứ tự giữa "ô xoá logo gốc" (nếu có khái niệm tương
  đương) và "che chữ" TRƯỚC khi cộng logo/watermark/banner của khách — sai
  thứ tự sẽ tái hiện đúng bug "watermark chép xuống bản sao" mà Viral đã
  từng gặp thật trên video khách.
- **Trần N=99 `if()` lồng / chunk ≤60** (§3.2): nếu TA có bất kỳ cơ chế che
  ĐỘNG nhiều dải nào dùng `crop`+biểu thức per-frame, sẽ đụng ĐÚNG giới hạn
  eval parser của ffmpeg này — không phải giả thuyết, đo nhị phân thật
  (N=98 OK / N=99 FAIL).
- **`speed` phải áp SAU CÙNG các filter có `enable=between(t,...)`** (§2.3.1):
  gộp `toc_do` (hiện áp cuối `image_finish`, tức cuối TOÀN BỘ pipeline hình)
  vào CÙNG lần encode với `render` bắt buộc `setpts` phải là node GẦN CUỐI
  filtergraph mới, sau mọi node đọc mốc thời gian gốc (che, sub, khung, logo).
  Đây chính là bất biến B6 "KHÔNG được đổi trục" đã chốt — Viral đi tới cùng
  kết luận độc lập, là bằng chứng ngoài củng cố B6, không phải điều mới.
- **`speed` CLAMP `[0.5, 2.0]` cứng** (§3.6): nếu gộp mà audio pipeline của
  TA cho phép `toc_do` ngoài dải này, sẽ cần tự thêm guard tương đương —
  Viral clamp vì `atempo` fail cứng ngoài dải, không phải lựa chọn sản phẩm.
- **Không có nấc lui nếu ffmpeg chết giữa filtergraph phức tạp** (§3.4): gộp
  hai encode thành một làm filtergraph DÀI HƠN (nhiều node hơn trong MỘT lần
  gọi ffmpeg) — rủi ro "một lỗi làm mất trắng cả hai giai đoạn" tăng theo,
  trong khi kiến trúc hiện tại (`render` rồi `image_finish`) cô lập lỗi theo
  giai đoạn (mỗi giai đoạn của TA vốn có `van_tay`/checkpoint riêng — mạnh
  hơn nấc lui LÀM MỜ một lần của Viral, theo V6 đã ghi). Gộp encode có thể
  MẤT tính chất cô lập lỗi đó nếu không thiết kế lại điểm checkpoint.
- **`cat_cuoi` là trần `-t`, không phải node filter** (Phần 4.1): nếu TA gộp
  cắt-cảnh của `image_finish` (`ke_cat.py`, hiện cắt bằng RE-ENCODE độc lập
  trên trục NGUỒN — B6) vào cùng lần encode với `render`, sẽ cần quyết định
  cắt bằng cơ chế nào (trim filter theo từng đoạn còn giữ, hay hạ `-t`/`-ss`
  toàn cục như Viral) — hai cơ chế cho kết quả khác nhau khi có nhiều đoạn bị
  cắt rời rạc (không chỉ cắt đầu/cuối liên tục), và `ke_cat.py` của TA cắt
  NHIỀU đoạn rời (không chỉ đầu/cuối) nên KHÔNG thể áp thẳng công thức `-t`
  đơn giản của Viral.

---

## SHA

Sẽ ghi SHA của commit chứa đúng tệp này ngay sau khi commit (báo cáo cuối).
