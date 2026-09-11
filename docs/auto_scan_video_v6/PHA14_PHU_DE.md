# Pha 14 — Phụ đề (subtitle capability integration)

**Trạng thái: XONG.** Ngày 11/09/2026. Nhánh `phien/asv-v6`.

Tài liệu này ghi *cái gì đã dựng và vì sao thế*. Phần khảo sát ban đầu ở
[`PHA14_KHAO_SAT.md`](PHA14_KHAO_SAT.md) — giữ nguyên, kể cả những chỗ nó
đoán sai, vì so hai bản mới thấy được chỗ nào phải đo mới biết.

---

## 0. Chặn phải đo trước — đã đo, và câu trả lời làm đổi thiết kế

Khảo sát ghi một chặn: *`ass=` đọc mốc **tuyệt đối** của bản ra, trong khi
`loc_cat_noi` cắt-rồi-nối, nên phải biết mốc lồng tiếng nằm trên trục nào.*

Đo bằng cách đọc chính người sinh ra dữ liệu — `thoi_gian.lap_ke_hoach`,
dòng 158:

```python
rb = ban_do.ra(float(m["bat"]))
```

⇒ **`ke_hoach["doan"][i]["dat_tai_ms"]` ĐÃ nằm trên trục bản ra.** Nó đi qua
`ban_do.ra()`, chính là phép ánh xạ pha 16 thêm vào.

Hệ quả với thiết kế: cầu nối **không tự ánh xạ gì cả**. Nó chỉ đọc
`dat_tai_ms`/`dai_ms`. Phép ánh xạ đã có chủ sở hữu là `ban_do_thoi_gian`, và
làm lại nó ở đây là mở đường cho hai câu trả lời khác nhau cho cùng một câu hỏi.

⛔ Dựng phụ đề từ `content.json` hay bản ghi gốc sẽ cho phụ đề trôi **đúng như
tiếng đã trôi trước pha 16** — và trôi âm thầm: chữ vẫn chạy, chỉ lệch câu.

---

## 1. Quyết định kiến trúc: mượn tầng TÁC GIẢ, không mượn tầng MÃ HOÁ

`apps/autosubvideo` sở hữu **hai** việc, và ASV chỉ tái dùng **một**:

| tầng | tệp | ASV |
|---|---|---|
| tác giả — preset kiểu chữ, phân đoạn, dựng `.ass`/`.srt` | `style_registry.py`, `ass_builder.py`, `segmenter.py` | **tái dùng** |
| mã hoá — chạy ffmpeg đốt phụ đề vào hình | `burn.py` | **không** |

🔴 Cách đọc tự nhiên nhất của *"đừng viết lại renderer"* là gọi `burn.burn()`, và
đó là cách **sai**: nó chạy một lượt ffmpeg đầy đủ của riêng nó, tức video bị mã
hoá lại **hai lần**. Pha 26 (*Renderer fusion*) tồn tại để gộp mọi biến đổi điểm
ảnh vào MỘT lần encode; gọi `burn()` ở đây là tự tạo ra đúng khoản nợ pha 26
phải trả.

⇒ ASV dựng `.ass` rồi đưa `ass=` vào **chính `-filter_complex` mà `ket_xuat.py`
đã dùng** — đứng cạnh `drawtext` (lớp phủ) và `overlay` (logo).

### Quyết định đó được CƯỠNG CHẾ, không chỉ được ghi chú

Bề mặt liên-app khai ở **cả hai phía** (`apps/autosubvideo/__init__.py` và
`tools/lint_app_contract.py`) gồm sáu tên, tất cả thuộc tầng tác giả:

```
style_registry.list_ids      style_registry.list_presets
style_registry.get_config    segmenter.SegmentMode
ass_builder.build_ass        ass_builder.build_srt
segmenter.SubtitleEvent
```

⭐ **`burn` cố ý vắng mặt.** Sự vắng mặt đó là lớp cưỡng chế duy nhất cho quyết
định trên: một phiên sau muốn "tái dùng cho nhanh" sẽ bị `lint_app_contract`
chặn ngay, thay vì để một khoản nợ GPU chạy im lặng tới pha 26.
`test_471::test_be_mat_lien_app_KHONG_gom_burn` chốt điều này.

---

## 2. HAI TRỤC — chỗ dễ làm sai nhất của cả pha

|  | đổi điểm ảnh? | chạy ở preset giữ hình? |
|---|---|---|
| **đốt** phụ đề vào hình | có | **không thể** — `-c:v copy` không giải mã khung nào |
| **xuất** tệp `.srt` | không | **được**, và đây là lựa chọn phụ đề DUY NHẤT còn lại ở đó |

Bốn tính năng trước (`vung`, `cat`, `lop_phu`, `logo`) có đúng **một** trục, nên
khuôn của chúng là *"preset giữ hình thì bỏ hết"*. Áp khuôn đó cho phụ đề sẽ
khoá mất `.srt` — và khoá **im lặng**: khách không thấy ô nào để hỏi.

Hai trục đó đi xuyên suốt, và mỗi tầng phải nói ra riêng:

| tầng | đốt | `.srt` |
|---|---|---|
| `hop_dong_v4` | `NANG_LUC_DOI_DIEM_ANH` | `NANG_LUC_KHONG_DOI_DIEM_ANH` (bảng **mới**) |
| `cai_dat.co_sua_diem_anh` | `True` | `False` |
| `phu_de.tu_form` (cửa HTTP) | chặn ở preset giữ hình | luôn nhận |
| `giai_doan_ban_dung` | `ha_ve_srt()` hạ trục đốt | giữ nguyên |
| `ban_dung.kiem` | từ chối, câu riêng | nhận |
| giao diện | ô chế độ ẩn theo preset | ô `.srt` **không bao giờ** ẩn |

⛔ Gộp hai bảng năng lực làm một là `hai-rao-bi-gop-lam-mot` ở dạng khác: hai
trục độc lập bị buộc vào một công tắc, và cái bị mất không báo lỗi.

---

## 3. Sự kiện được CHỐT ở COMPOSE, tệp được SINH ở RENDER

COMPOSE và RENDER là **hai job**. RENDER mở đúng MỘT tệp — bản dựng. Nên:

* `giai_doan_ban_dung._ho_so_phu_de` đọc kế hoạch + tài liệu `CONTENT_PROCESS`,
  dựng danh sách sự kiện trên trục ra, và **chốt chúng vào bản dựng**
  (`hinh.phu_de.su_kien`).
* `giai_doan_ket_xuat` chỉ đọc bản dựng, ghi `.ass` vào thư mục tạm của lần chạy
  (xoá cùng nó — đúng khuôn `lop_phu.viet_tep_chu`), và truyền `duong_ass`.

⛔ **Nguồn chữ là tài liệu `CONTENT_PROCESS`, không phải bản kê tiếng.** Bản kê
tiếng là `{ma, khoa, giay}` — nó trỏ tới tệp WAV, nó không mang một chữ nào.
Chính `giai_doan_giong._doc_ban_dich` cũng phải đọc tài liệu này để có chữ.

⚠️ **Hai tài liệu dùng hai khoá khác nhau, và đó không phải lỗi đánh máy.** Kế
hoạch dùng `doan` (`thoi_gian.py:290`), văn bản dùng `muc` (`van_ban.py:107`).
Bản đầu tiên của cầu nối đọc **ngược cả hai** — và nó vẫn xanh, vì phép kiểm khi
đó dùng một dict do chính tôi bịa ra khớp với giả định của chính tôi. Đối chứng
đúng là đọc **người sinh ra tài liệu**;
`test_471::test_doi_hai_tai_lieu_cho_nhau_thi_KHONG_su_kien_nao` giữ chỗ đó.

### `.srt` sinh ở RENDER, không ở COMPOSE — và lý do là hạn

`thi_hanh.py` đặt `la_ban_giao = ten == pipeline.RENDER`, và bản giao là thứ
**không có hạn**. Sinh `.srt` ở COMPOSE thì tệp phụ đề của khách mang
`HAN_TRUNG_GIAN = 30 ngày` trong khi video thì không — tức một nửa bản giao tự
biến mất sau một tháng, im lặng.

---

## 4. Chuỗi lọc

```
[0:v]trim=…[v0];[v0]concat=…[sau_che];[sau_che]ass='…'[ra]
```

`ass=` là mắt xích **cuối**, trên cả logo và lớp phủ: phụ đề là thứ khách đọc để
**hiểu**, còn lớp phủ chữ là thứ khách dán để **trang trí**. Một phụ đề bị che là
một tính năng không tồn tại.

🔑 **Không cần điệu nhảy `cwd` của `autosubvideo/burn.py`.** Bản kia chạy ffmpeg
với `cwd` = thư mục chứa `.ass` rồi truyền tên tệp trần. ASV đã có lời giải tốt
hơn và đã dùng nó cho `textfile=`: `lop_phu.thoat_duong` đổi `\` → `/` và
`:` → `\:`. Escape tốt hơn `cwd` ở một chỗ cụ thể: `cwd` là trạng thái **toàn
tiến trình**, mà lệnh này còn đọc video nguồn, ảnh logo và tệp chữ ở các thư mục
**khác** — một lệnh một `cwd` thì không phục vụ được bốn đường dẫn.

### `PHIEN_BAN_CHE_DO` 5 → 6

Phụ đề đốt vào hình là một biến đổi **điểm ảnh mới** trong chuỗi lọc. Thiếu bước
tăng này thì một lần chạy có phụ đề và một lần không dùng chung vân tay — hai kết
quả khác nhau, một chuỗi băm, và lần thứ hai được phục vụ từ cache.

Hồ sơ phụ đề cũng vào `van_tay_che_do`. ⭐ **Hồ sơ, không phải đường dẫn `.ass`**:
đường dẫn là một tệp tạm đổi tên mỗi lần chạy, nên băm nó sẽ phá huỷ chính cái
cache mà vân tay tồn tại để mở.

---

## 5. Ba cái bẫy đã bịt

**`get_config` rơi về `default` khi id lạ.**
```python
preset = _PRESETS.get(style_id) or _PRESETS["default"]
```
Với `autosubvideo` đó là lựa chọn hợp lý. Với ASV thì không: khách chọn một kiểu,
một id cũ hay gõ sai đi qua, và họ nhận `default` mà không ai nói gì. `phu_de`
**ném** ở cả hai tầng (`chuan_hoa` và `viet_tep_ass`) thay vì rơi về.

**`PhuDeLoi` kế thừa `ValueError`.** Một `except (ValueError, TypeError)` bao
quanh cả đọc lẫn duyệt sẽ nuốt câu trả lời cụ thể rồi bọc lại thành *"không đọc
được"*. Bản đầu của `tu_form` dính đúng thế: gõ sai một id kiểu chữ thì khách đọc
*"Yêu cầu phụ đề không đọc được"*. Đã tách hai bước; bốn lỗi nay có bốn câu.

**Kích thước khung là bắt buộc về nội dung.** `build_ass` tính cỡ chữ và lề theo
`video_width/height`, mặc định 1920×1080. Áp mặc định đó lên video **dọc** cho ra
phụ đề nhỏ bằng một phần ba và đặt sai lề, **không báo một lỗi nào**.

---

## 6. Dấu chân ở `routes.py`

`routes.py` ở **880/900 dòng** khi pha 14 bắt đầu. Toàn bộ tầng đọc + duyệt + đối
chiếu preset nằm ở `phu_de.tu_form`; route chỉ còn một lời gọi. Sau pha:
**899/900**.

---

## 7b. Ba bánh cóc phải VIẾT LẠI, và vì sao không được xoá

Lượt gate đầy đủ đầu tiên đỏ **3 bài / 9.714**. Cả ba là của pha 14, và cả ba
cùng một nguyên nhân: chúng khẳng định `subtitle_burn` **vẫn bị cấm**.

| bài | mệnh đề nó BẢO VỆ | mệnh đề nó VIẾT RA |
|---|---|---|
| `test_466::test_subtitle_burn_VAN_bi_cam` | lớp phủ chữ không được biến thành phụ đề bằng cách đổi tên | *`subtitle_burn` bị cấm* |
| `test_455::test_GUI_khong_mo_duoc_thao_tac_dang_bi_CAM` | giao diện không mở được thao tác đang bị cấm | như trên |
| `test_418::test_moi_lop_ngoai_le_cua_app_deu_duoc_phan_loai` | mọi lớp ngoại lệ đều được phân loại | (thiếu `PhuDeLoi`) |

Hai mệnh đề đó trùng nhau ở pha 11 **chỉ vì lúc ấy ASV chưa làm phụ đề**. Pha 14
làm — đúng đường: đổi hợp đồng, viết mã, viết kiểm, ghi quyết định. Nên mệnh đề
*viết ra* hết hạn, còn mệnh đề *bảo vệ* thì không.

⛔ **Xoá ba bài đi là tháo ba rào.** Bản viết lại phải **khó xanh hơn** bản cũ:

* `test_lop_phu_KHONG_PHAI_phu_de` — ranh giới nay là *"hai thứ khác nhau"*, và
  đòi **cả hai** tên phải có mặt, mỗi tên ở đúng bảng của nó, hai module riêng,
  cộng rào cơ học `SO_LOP_PHU_TOI_DA`. Bản cũ vẫn xanh nếu ai đó **xoá**
  `subtitle_burn` khỏi mọi bảng — nó đo một sự **vắng mặt**. Bản mới thì không.
* `test_mot_nang_luc_da_MO_thi_phai_MO_HAN_o_bang_hop_dong` — mệnh đề **dương**:
  mọi thứ rời khỏi bảng CẤM phải có mặt ở đúng một bảng năng lực. Nó bịt trạng
  thái *"không bị cấm, và cũng không ai khai"* — `nang-luc-co-nhung-khong-ai-di-
  tren-duong`.

⭐ **Đối chứng:** tiêm ba lỗi tương lai có thật, cả ba đều làm bộ kiểm **đỏ** —
gỡ `subtitle_burn` khỏi bảng CẤM mà không khai ở đâu · gộp hai trục làm một ·
nới `SO_LOP_PHU_TOI_DA` lên 500 (biến lớp phủ thành một bản phụ đề). Rồi
`hop_dong_v4.py` và `lop_phu.py` được trả lại nguyên vẹn.

## 7. Bằng chứng

| câu hỏi | trả lời bằng | ở đâu |
|---|---|---|
| mốc phụ đề nằm trên trục nào | đọc `thoi_gian.py:158` | §0 |
| ffmpeg có nhận `ass=` không, đường dẫn Windows thoát đúng không, phụ đề có ra điểm ảnh không | chạy ffmpeg **thật**, đo độ sáng đầu ra so với chính lần chạy không có `ass=` | `bang_chung/phu_de_ass_20260911.json` |
| ba mệnh đề của pha còn đứng không | `tests/test_471_asv_v6_phu_de.py` | 40 bài |

⛔ Không bài test nào chạm ffmpeg: bằng chứng máy thật trả lời một câu hỏi khác
và nó không thuộc về một bộ test chạy hàng trăm lần một ngày.

---

## 8. Còn nợ

* `phan_doan` được duyệt và lưu nhưng **chưa dùng**: sự kiện hiện dựng một-đổi-một
  từ mục kế hoạch. Dùng `segmenter` để chia nhỏ trong một mục là việc của pha sau
  — nó cần mốc **từng từ**, thứ mà kế hoạch chưa mang.
* ~~`highlight_mode` chưa mở ra giao diện~~ — **pha 16 đã trả**, và trong lúc trả đã bắt được một false feature: xem `PHA16_SUBTITLE_STUDIO.md` §1.
* Chưa có kiểm trên trình duyệt thật (`https://app.lttstudios.com`) vì V6 chưa
  deploy — `manifest.py:127 enabled=False`, `/auto-scan-video` trả 404 ở
  production. Việc đó thuộc pha 34.
