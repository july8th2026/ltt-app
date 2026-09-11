# Pha 16 — Subtitle Studio (tinh chỉnh kiểu chữ)

**Trạng thái: XONG.** Ngày 11/09/2026. Đứng thẳng trên pha 14
([`PHA14_PHU_DE.md`](PHA14_PHU_DE.md)).

---

## 1. Một false feature có thật, đo được — và đây là lý do chính pha này đáng giá

`style_registry` giữ chế độ nhấn mạnh ở **hai** chỗ, và chúng không bằng nhau:

| | `FullStylePreset.highlight_mode` | `SubtitleStyleConfig.highlight_mode` |
|---|---|---|
| `ltt_brand` | `word` | `none` |
| `tiktok_bold` | `word` | `none` |
| `reels_clean` | `bg_flash` | `none` |
| `meme_punch` | `word` | `none` |
| `kids_color` | `word` | `none` |
| `punchline` | `all_text` | `none` |
| `word_emphasis` | `word` | `none` |
| `cinematic`, `default` | `none` | `none` |

**7 trên 9** preset khai ở cấp preset. **Cả chín** có `config.highlight_mode ==
"none"`.

🔴 Đọc `config.highlight_mode` là cách tự nhiên nhất — mọi thuộc tính khác (font,
màu, viền, lề) đều ở đó, và `cau_hinh_kieu()` trả về đúng đối tượng ấy. Bản đầu
của tôi làm đúng thế. Hệ quả: **mọi preset render không nhấn mạnh gì.** Kiểu tên
`word_emphasis` không nhấn mạnh một từ nào. Không lỗi nào báo, tệp `.ass` vẫn
hợp lệ, và cách duy nhất phát hiện là mở tệp ra nhìn.

⇒ `phu_de.nhan_manh(ho_so)` là chỗ **duy nhất** quyết định, theo thứ tự:
tinh chỉnh của khách → cấp preset → cấp cấu hình.

⭐ Và `test_472` chốt nó bằng **hai** bài, không phải một: một bài khẳng định 5
preset có nhấn mạnh thật sự phát thẻ ASS, một bài khẳng định `default`/`cinematic`
**không** phát thẻ nào. Thiếu bài thứ hai thì bài thứ nhất vẫn xanh khi ai đó
dán thẻ vào mọi dòng.

Thêm một bài canh cho chính bài kiểm: `test_preset_khai_nhan_manh_o_CAP_PRESET_
chu_khong_o_config` sẽ **đỏ** nếu `style_registry` chuyển nhấn mạnh xuống
`config` — lúc đó `nhan_manh()` trở nên thừa và phải bỏ đi, chứ không phải để lại
một lớp không còn giải quyết gì.

---

## 2. Duyệt bằng chính mô hình của app chủ

`SubtitleStyleConfig` là một mô hình Pydantic với `extra="forbid"` và ràng buộc
miền cho từng trường (`font_size` 12..120, `bg_opacity` 0..1, `alignment` 1..9).
`chuan_hoa_tinh_chinh` **dựng thử cả cấu hình cuối cùng** thay vì kiểm từng
trường:

```python
_mo_hinh_kieu()(**{**goc.model_dump(), **tho})
```

⭐ `extra="forbid"` bắt cả lỗi gõ sai **tên** — thứ một vòng `for` tự viết không
bao giờ bắt được, vì nó chỉ nhìn những tên nó biết.

Bốn câu trả lời riêng biệt, không một câu chung chung:

| khách nhập | câu trả lời |
|---|---|
| `font_size: 500` | *font_size — Input should be less than or equal to 120* |
| `font_sizee: 60` | *Không chỉnh được thuộc tính: font_sizee* |
| `italic: true` | *Không chỉnh được thuộc tính: italic* (cố ý không mở) |
| `font_color: "do"` | *font_color — String should match pattern…* |

Bề mặt liên-app xin thêm **một** tên: `schemas.SubtitleStyleConfig`. Xin **mô
hình**, không xin một hàm duyệt — mô hình mang cả hình dạng lẫn miền giá trị.

---

## 3. Mười tám trường mở, chín trường không

Mô hình có 27 trường. Đổ hết ra màn hình là đòi khách **thiết kế** một kiểu chữ
thay vì **chọn** một kiểu — trong khi 9 preset đã làm đúng việc đó.

Mười tám trường mở trả lời đúng những trục pha 16 gọi tên: font · cỡ · màu ·
viền · vị trí · nền · karaoke/nhấn mạnh · chuyển động.

Chín trường còn lại không mở, mỗi trường một lý do ghi tại chỗ trong
`phu_de.TRUONG_MO` — `font_fallback` là quyết định hạ tầng, `shadow_*` chồng
lên viền (hai nút cho cùng một hiệu ứng thì khách chỉnh mãi không ra),
`keyword_highlights` cần một trình soạn danh sách từ (pha riêng)…

⭐ Chúng **không bị cấm** — mở thêm chỉ là thêm một tên vào `TRUONG_MO`; không
tầng nào khác phải đổi, vì tầng duyệt đọc mô hình chứ không đọc danh sách này.

---

## 4. Giao diện: giá trị khởi điểm là của PRESET, không phải của MÔ HÌNH

Hai thứ này khác nhau: mô hình mặc định `font_size=48`, còn `tiktok_bold` khởi
điểm ở 64. Hiện mặc định của mô hình sẽ làm **mọi ô khách chạm vào** trở thành
một "tinh chỉnh" dù họ không đổi ý gì.

⇒ `cho_giao_dien()["kieu_cau_hinh"]` phát giá trị khởi điểm của cả 9 preset.
JS so với bảng đó để chỉ gửi những ô khách **thật sự** đổi, và đổi kiểu thì kéo
mọi ô về khởi điểm của kiểu mới.

⚠️ So sánh bằng **chuỗi thường hoá**: `<input type=color>` trả `#ffffff` cho giá
trị khởi điểm `#FFFFFF`, và `<input type=number>` trả `48` cho `48`. So sánh
thẳng `!==` sẽ báo "đã đổi" cho cả hai — tức gửi thừa ở mọi lần chạy, đúng điều
cả khối này tồn tại để tránh.

⛔ Miền giá trị trong HTML đến từ `luoc_do_tinh_chinh()`, không gõ tay.
`test_472::test_template_KHONG_go_mien_gia_tri_bang_tay` chốt bằng **cơ học**:
nó tìm mọi `min="<số>"` trong khối và đỏ nếu thấy.

---

## 5. Bằng chứng

* `tests/test_472_asv_v6_tinh_chinh_phu_de.py` — **29 bài**.
* Đối chứng: tiêm lại hai lỗi cũ, cả hai làm bộ kiểm **đỏ**
  (đọc `config.highlight_mode` → 5 bài đỏ; bỏ `TRUONG_MO` → 1 bài đỏ), rồi
  `phu_de.py` được trả lại nguyên vẹn 30.755 byte.
* Đo trên tệp **đã ghi**, không dừng ở đối tượng Python: cỡ 48→96, màu
  `&H00FFFFFF`→`&H000000FF` (ASS dùng **BGR**), viền 2→6, canh 2→8, thẻ `\kf`
  của karaoke và `\fscx70` của `pop`.

## 6. Còn nợ

* Xem trước phụ đề **trên khung hình thật** trong studio (hiện chỉ xem được sau
  khi render). Cần một đường dựng khung xem trước — thuộc pha 32.
* `keyword_highlights` cần một trình soạn danh sách từ.
* Chưa kiểm trên trình duyệt thật: V6 chưa deploy (`manifest.py:127
  enabled=False`, `/auto-scan-video` trả 404 ở production). Thuộc pha 34.
