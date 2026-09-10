# PHA 14 — khảo sát trước khi viết, và một chặn phải trả lời trước

> Đề bài: *"ASV GUI gọi AutoSubVideo `video.subtitle`; OFF/AUTO/CUSTOM, style
> preset, segment mode, export SRT; **không duplicate renderer**."*
>
> ⛔ **Chưa viết mã sản phẩm.** Tệp này ghi lại khảo sát, thiết kế đã chốt, và
> **một câu hỏi chặn** phải đo trước khi viết một dòng nào.

## 0. 🔴 Chặn: phụ đề đi trên TRỤC THỜI GIAN NÀO

`che_do_render.loc_cat_noi` **cắt các khoảng giữ lại rồi nối chúng**. Nghĩa là
mốc thời gian của bản ra **không bằng** mốc của bản gốc: một câu ở giây 180 của
nguồn có thể rơi vào giây 42 của tệp ra.

Bộ lọc `ass=` của ffmpeg đọc mốc **tuyệt đối trong tệp nó đang lọc**. Nên nếu
`.ass` được dựng theo giờ **nguồn** mà đưa vào sau `concat`, phụ đề sẽ hiện
**sai chỗ** — và sai một cách trông vẫn hợp lý (chữ vẫn chạy, chỉ lệch câu).

⭐ Đây **không** phải một vấn đề mới của pha 14. Pha 11 đã gặp đúng nó với lớp
   phủ chữ và đã giải: `che_do_render._anh_xa_cua_so` + `cua_so_ra_lop_phu` ánh
   xạ cửa sổ thời gian từ trục **nguồn** sang trục **ra**, và `drawtext` dùng
   `enable=between(t,a,b)` với `t` là giờ **ra**.

⇒ Phụ đề cần **cùng phép ánh xạ ấy**, hoặc phải được dựng sẵn trên trục ra.

### Dữ kiện đã có, và phần còn thiếu

- `long_tieng.py:116` — *"Các đoạn GIỮ LẠI ngay trước/sau, **theo thứ tự bản ra
  — không phải bản gốc**"*.
- `long_tieng.py:73-74` — *"sau khi cắt, câu đứng trước một câu trong bản ra có
  thể là một câu cách đó ba phút trong bản gốc"*.

⇒ Bản lồng tiếng **đã tư duy theo thứ tự bản ra**. Nhưng *thứ tự* không phải
  *mốc giây*. Câu chưa trả lời được: **`doan[].bat` / `doan[].ket` đang tính theo
  giờ NGUỒN hay giờ RA?**

⛔ **Phải đo, không được đoán.** Hai đường đi hoàn toàn khác nhau tuỳ câu trả
   lời, và chọn nhầm thì phụ đề lệch trên **mọi** lần chạy có cắt — một lỗi
   không làm hỏng tệp, không ném ngoại lệ, chỉ làm sai nội dung.

**Cách đo rẻ:** một lần chạy `smart_localize` có cắt thật, rồi đối chiếu
`doan[].bat` của bản lồng tiếng với mốc thật của câu ấy trong tệp ra
(`ffprobe` + nghe). Hoặc đọc `thoi_gian.lap_ke_hoach` xem nó đặt `bat` từ đâu.

## 1. ✅ Đã chốt: "không duplicate renderer" đọc sai thì hỏng cả pha

Cách đọc tự nhiên nhất — *"gọi `autosubvideo.burn.burn()` cho khỏi viết lại"* —
là cách **sai**.

`burn.burn()` (`apps/autosubvideo/burn.py:104`) chạy **một lượt ffmpeg đầy đủ của
riêng nó**: `Popen`, `-progress pipe:1`, bitrate flags, NVENC/QSV. Gọi nó từ ASV
nghĩa là video bị **mã hoá lại hai lần**.

⛔ Vi phạm thẳng `V6_OPERATING_CONTRACT`: *"Pixel-changing edit bắt buộc re-encode
   **có chủ đích**"*. Hai lượt encode không phải "có chủ đích" — đó là một lượt
   thừa, và nó nhân đôi đúng phần đắt nhất. Pha 26 (*Renderer fusion*) tồn tại
   để **gộp** mọi biến đổi điểm ảnh vào **một** lần encode; gọi `burn()` ở pha 14
   là tự tạo ra đúng khoản nợ mà pha 26 phải trả.

### ⭐ Cách đọc đúng: tái dùng lớp TÁC GIẢ, không tái dùng lớp MÃ HOÁ

| lớp | tệp | ASV dùng? |
|---|---|---|
| **tác giả** — preset, kiểu chữ, highlight, dựng `.ass`/`.srt` | `style_registry.py` · `ass_builder.py` · `segmenter.py` | ✅ |
| **mã hoá** — chạy ffmpeg, bitrate, tiến độ, huỷ | `burn.py` | ⛔ |

⇒ Gọi `ass_builder.build_ass()`, rồi đưa `ass=` vào **chính `-filter_complex` mà
  `ket_xuat.py` đã dựng** — đứng cạnh `drawtext` và `overlay`. Một lệnh, một lần
  encode.

🔑 Bảng đối chiếu ở đầu `ket_xuat.py` **đã** liệt kê `burn.py` làm một trong ba
   bản tham chiếu, kèm ghi chú *"mã hoá lại (bắt buộc, phụ đề đốt vào)"*. Chỗ
   cho việc này đã có trong thiết kế từ V4.

## 2. ✅ Đã chốt: HAI trục, gộp lại là khoá mất một tính năng

|  | đổi điểm ảnh? | chạy ở preset giữ hình? |
|---|---|---|
| **đốt** phụ đề vào hình | có | **không thể** — `-c:v copy` không giải mã khung nào |
| **xuất** tệp `.srt` | không | **được**, và đó là lựa chọn phụ đề **duy nhất** ở đó |

⚠️ Bản nháp đầu của `phu_de.chuan_hoa` trả `None` ngay khi `che_do == tat`,
   **trước khi** đọc `xuat_srt` — nghĩa là tổ hợp *"chỉ xuất SRT, không đốt"*
   **không diễn đạt được**. Cái bị mất không báo lỗi; nó chỉ **không tồn tại**.

⇒ `che_do` điều khiển việc ĐỐT; `xuat_srt` là một trục RIÊNG. Hồ sơ chỉ biến mất
  khi **cả hai** đều tắt.

⇒ Trong hợp đồng: `subtitle_burn` thuộc `NANG_LUC_DOI_DIEM_ANH` (ba tầng cưỡng
  chế của pha 11/12 dùng lại nguyên xi); `subtitle_srt` là một mục **riêng**,
  hợp lệ ở mọi preset.

## 3. ✅ Đã chốt: ba nguồn chân lý phải HỎI, không CHÉP

| thứ | nguồn | ⛔ nếu chép |
|---|---|---|
| danh sách kiểu | `style_registry.list_ids()` (9 id) | trôi ngay lần `autosubvideo` thêm kiểu, và trôi **im lặng** |
| chế độ phân đoạn | `get_args(segmenter.SegmentMode)` (5 mode) | `autosubvideo` **đã có hai bản** (`Literal` + regex ở `schemas.py:105`); bản thứ ba sẽ lệch với cả hai theo hai hướng |
| ngôn ngữ đích | `hop_dong_v4.HAU_MVP::multilingual_target` | xem mục nợ *"`rang_giong` không lọc theo làn"* — cùng hạng lỗi |

### 🔴 Và một bẫy im lặng phải chặn ở biên

`style_registry.get_config(style_id)` **rơi về `default`** khi id không tồn tại:

```python
preset = _PRESETS.get(style_id) or _PRESETS["default"]
```

Với `autosubvideo` đó là lựa chọn hợp lý. Với ASV thì **không**: khách chọn một
kiểu, một id cũ hay gõ sai đi qua, và họ nhận `default` mà **không ai nói gì**.

⇒ ASV **tự kiểm** id và **ném** — đúng hạng lỗi mà `lop_phu` đã từ chối khi nó
  **ném** thay vì lọc bỏ ký tự điều khiển: *"sửa hộ" là sửa một ý định của khách*.

## 4. Bẫy đường dẫn Windows, đã có người trả giá

`burn._ass_filter_arg` ghi nguyên văn: chạy ffmpeg với `cwd` = thư mục chứa
`.ass` rồi truyền **tên tệp trần**, vì ổ đĩa `C:` và `\` **làm vỡ bộ phân tích
filter** — *"đã gặp thật khi test"*.

ASV sẽ đâm vào đúng đó, vì `ket_xuat.dung_lenh` dựng đường tuyệt đối. Đây là một
ràng buộc **đã biết trước**, không phải thứ để phát hiện lại.

## 5. Phạm vi, theo thứ tự, sau khi mục 0 có câu trả lời

1. `apps/auto_scan_video/phu_de.py` — miền: `CHE_DO = (tat · tu_dong · tu_chon)`,
   kiểm style id qua `list_ids()`, segment mode qua `get_args`, `xuat_srt` là
   trục riêng, `PhuDeLoi`. *(Đã viết và chạy thử; gỡ khỏi cây vì chưa có người
   gọi — xem mục 6.)*
2. `loi.py` — `PhuDeLoi` xếp loại `NGUOI_DUNG`, cùng nhóm `LopPhuLoi`/`LogoLoi`.
3. `hop_dong_v4.py` — `subtitle_burn` rời `CAM_TRONG_MVP` + `HAU_MVP` →
   `NANG_LUC_DOI_DIEM_ANH`; `subtitle_srt` khai riêng.
4. `che_do_render.py` — `phu_de` vào `van_tay_che_do`, `PHIEN_BAN_CHE_DO` 5 → 6,
   `ass=` vào chuỗi lọc **sau** `chu`.
5. `ban_dung.py` — nhận `phu_de`, `kiem()` từ chối đốt ở preset sao chép **bằng
   một câu riêng**, không gộp vào `or` với lớp phủ.
6. `ket_xuat.py` — xử bẫy `cwd` của `ass=`.
7. `routes.py` + template + `asv/phu_de.js` — OFF/AUTO/CUSTOM, chọn kiểu, SRT.
8. `test_471` — kèm **bằng chứng engine** (khung có chữ, PSNR ngoài vùng phụ đề)
   và đối chứng tiêm bản cũ.

⚠️ `routes.py` đang ở **880/900 dòng**. Bước 7 gần như chắc chắn chạm trần
   `lint_app_contract`. Logic đọc/kiểm phải vào `phu_de.py`, **không** vào route.
   Trần ấy tồn tại đúng để chặn lần này.

## 6. ⛔ Vì sao KHÔNG commit mã của bước 1–3 lúc này

Đã viết và chạy thử `phu_de.py` (9 kiểu đọc từ `style_registry`, 5 mode đọc từ
`segmenter`, ba đầu vào sai đều ném `PhuDeLoi`), đã xếp loại `PhuDeLoi`, đã
chuyển `subtitle_burn` sang `NANG_LUC_DOI_DIEM_ANH`. **Rồi gỡ hết khỏi cây.**

Lý do: hai bánh cóc bắn, và **cả hai đều đúng**:

```
test_427  REBASE_MAP_V4.md bo sot: ['phu_de']
test_453  nang luc khong co nguoi goi: co_dot_vao_hinh
```

⇒ `test_453` đang nói đúng thứ nó sinh ra để nói: **một module miền không có
  người tiêu thụ là một năng lực không ai đi tới**. Commit nó sẽ khai
  `subtitle_burn` là năng lực đã mở trong khi **không có gì render nó** — đúng
  hạng *"feature chỉ có code nhưng không có UX/API để dùng ⇒ tối đa 60"* của
  `V6_98_SCORECARD`.

⭐ Nên pha 14 phải hạ cánh **nguyên khối**, hoặc không hạ cánh. Thiết kế thì
   chốt được ngay; mã thì đợi mục 0.
