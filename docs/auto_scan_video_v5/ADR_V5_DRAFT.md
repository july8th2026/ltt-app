# ADR-V5 (BẢN THẢO) — mở hay giữ đóng tám mục `DEFER` của Auto Scan Video

> ✅ **ĐÃ KÝ 26/09/2026 — xem §6.** Tệp này ⛔ không còn là bản thảo.
>
> Soạn 08/09/2026, phiên ASV V5. ⚠️ Dòng *"chặn bước 14 và 16"* ở bản thảo nay
> **⛔ KHÔNG còn đúng**: xem §6b — thực tế đã vượt qua nó.

---

## 1. Vì sao cần một ADR chứ không phải một lần sửa mã

`apps/auto_scan_video/hop_dong_v4.py` giữ hai danh sách, và chúng **được cưỡng
chế bằng mã**: `_kiem_tra_hop_dong()` chạy ở cấp module, nên mọi preset vừa cho
phép vừa cấm một mục sẽ làm `import` **vỡ ngay lúc nạp**, không phải lúc chạy.

⇒ Không ai "lỡ tay" mở được một mục. Mở nó là một hành vi có chủ đích, và hợp
đồng đòi hành vi ấy phải có địa chỉ. Đó là điều tệp này phục vụ.

---

## 2. 🔴 Tám mục ấy KHÔNG cùng một loại — và đây là phần hay bị gộp

Cả tám đang mang cùng một nhãn `DEFER`, nên chúng trông như một danh sách việc
chưa làm. Đo lại thì chúng thuộc **ba** loại, và ba loại ấy cần ba câu trả lời
khác nhau:

| Loại | Câu hỏi thật | Ai trả lời được |
|---|---|---|
| **A — app khác đã sở hữu** | *"ASV có nên làm lại việc app kia đang làm không?"* | kiến trúc, không phải sản phẩm |
| **B — chưa đo được** | *"tốn bao nhiêu VRAM, và có vừa máy không?"* | một phép đo, không phải một chữ ký |
| **C — phạm vi sản phẩm** | *"ta có bán thứ này không?"* | **chủ dự án** |

⭐ Phân biệt này quan trọng vì nó đổi việc phải làm: ký một chữ ký cho loại **B**
   không mở được gì — thứ thiếu là một phép đo. Còn loại **A** thì một chữ ký
   *mở được*, nhưng mở ra một bản sao chép.

---

## 3. Loại A — `subtitle_burn` · `upscale`

**Đo được 08/09:** `apps/autosubvideo/` và `apps/upscalevideo/` đều **đang tồn
tại** trong kho, không phải kế hoạch.

Chú thích ngay trong hợp đồng đã nói thẳng lý do:

```python
"subtitle_burn",    # `apps/autosubvideo` da lam viec nay
"upscale",          # `apps/upscalevideo` da lam viec nay
```

⛔ Mở hai mục này trong ASV **không phải** thêm tính năng — nó là chép một năng
lực đã có sang một app thứ hai. Nền tảng này có đúng một luật chống điều đó
(`CLAUDE.md` luật 20: thêm app = thêm **một** thư mục; việc dùng chung thì gọi
`platform_core`, đừng chép lại), và hai bản sao của một tính năng nghĩa là hai
chỗ phải sửa mỗi lần đổi, hai bảng giá phải khớp nhau, hai chỗ để lệch.

**Đề xuất: GIỮ ĐÓNG.** Và thay vì mở, làm thứ khách thật sự cần —

⇒ **một đường bàn giao**: màn kết quả của ASV có nút *"Thêm phụ đề cho video
này"* dẫn sang `autosubvideo` với `storage_key` của kết quả điền sẵn. Khách
được việc mình muốn, nền tảng không có bản sao nào, và ASV không cần một dòng
`ffmpeg` mới.

⚠️ Đường bàn giao ấy **chưa được thiết kế** và không thuộc phạm vi V5. Nó cần
một chỗ trong `platform_core` để một app truyền artifact sang app khác mà không
qua máy khách — thứ hiện chưa có.

---

## 4. Loại B — `zoom` · `reframe` · `crop` · `broll` · OCR hardsub · tự dò logo · xoá logo bằng điền nền

Bốn mục đầu nằm trong `CAM_TRONG_MVP`; ba mục sau nằm trong ghi chú
`VIRAL_HARVEST_DECISIONS.md` với lý do **"chưa đo VRAM"**.

🔑 **Một chữ ký không mở được nhóm này**, và đó là điều quan trọng nhất trong
tệp này. Thứ chặn chúng không phải một quyết định — là một con số chưa ai đo:
mỗi mục cần một model chạy trên GPU, và `apps/asv_media/` khai VRAM cho render
theo một ngân sách cố định.

**Điều kiện để mở, viết thành việc làm được:**

| Mục | Cần đo gì trước |
|---|---|
| `reframe` (YOLO đổi khung) | VRAM đỉnh của YOLO cùng lúc với bộ mã hoá đang chạy |
| `zoom` (đường đi camera) | không cần model, nhưng đổi **mọi** vùng che đã lưu — toạ độ 0..1 không còn cố định theo khung |
| `crop` | như `zoom` |
| OCR hardsub | VRAM của OCR + một tập mẫu có hardsub để đo độ chính xác |
| tự dò logo · điền nền | VRAM của inpaint; và nó **đổi giá** một lần chạy |

⚠️ **`zoom` có một hệ quả mà chữ ký không gỡ được.** `vung_che.py` chốt rằng toạ
độ là phân số 0..1 **của khung hình**. Nếu khung hình tự dịch chuyển theo thời
gian thì một vùng che đã lưu không còn trỏ vào đúng chỗ nó từng trỏ. Mở `zoom`
đòi vùng che thành **hàm theo thời gian**, không còn là một hình chữ nhật —
tức đổi `SCHEMA_BAN_DUNG`, không phải bật một cờ.

**Đề xuất: GIỮ ĐÓNG**, và chuyển thành **bảy hạng mục đo** có thể giao cho một
phiên khác, độc lập với chữ ký của chủ dự án.

---

## 5. Loại C — `multilingual_target` · `multi_speaker_voice` · `music_replace` · `transition` · `reorder` · tốc độ

Đây là nhóm **duy nhất** mà một chữ ký thật sự quyết định được điều gì.

| Mục | Nếu MỞ thì đổi gì | Nếu GIỮ ĐÓNG |
|---|---|---|
| `multilingual_target` | `NGON_NGU_DICH` thành một lựa chọn của khách; giá đổi theo ngôn ngữ; `ltt_voice` phải có giọng cho ngôn ngữ ấy | sản phẩm là **lồng tiếng Việt**, và tên nó nói đúng thế |
| `multi_speaker_voice` | cần tách người nói (`diarize` đã có) + gán giọng theo người; giá nhân theo số giọng | một giọng cho cả video |
| `music_replace` | phải có kho nhạc có bản quyền — **chưa có**, và đó là chi phí pháp lý chứ không phải kỹ thuật | giữ nhạc gốc |
| `transition` · `reorder` | phá lời hứa *"thứ tự cảnh là thứ tự gốc"* | giữ |
| **tốc độ** | ⛔ **va chạm trực tiếp với `DUNG_SAI_DO_DAI_S = 0.50`** | giữ |

🔴 Mục **tốc độ** đáng đọc kỹ, vì nó không phải một cấm đoán tuỳ tiện. Chú thích
trong hợp đồng viết:

> *Không preset nào được làm video DÀI RA. Đó không phải một ngưỡng chất lượng,
> đó là một lời hứa: khách đưa vào một video, không đưa vào một khoảng thời gian
> để điền vào.*

Đổi tốc độ **luôn** đổi độ dài. Mở nó không phải nới một dung sai từ 0,5 giây
lên vài giây — nó là **bỏ** lời hứa ấy. Nếu chủ dự án muốn mở, việc đúng là viết
lại lời hứa cho khách trước, rồi mới đổi hằng số.

**Đề xuất:**

- `multilingual_target`, `multi_speaker_voice` → **quyết định thương mại thật**,
  tôi không có cơ sở để khuyến nghị. Cả hai đã có chỗ dành sẵn trong IA §4.
- `music_replace`, `transition`, `reorder`, tốc độ → **giữ đóng**; cả bốn phá
  một lời hứa đã nói với khách, không chỉ thêm một tính năng.

---

## 6. Chữ ký

Điền vào đây thì §3–§5 có hiệu lực; để trống thì hợp đồng giữ nguyên.

```
Ngay      : 26/09/2026
Nguoi ky  : chu du an (qua phien dieu phoi ASV)

Loai A (subtitle_burn, upscale)         : [x] mo        (da lam, xem §6b)
Loai B (zoom, reframe, crop, broll, ...): [x] giao DO   (da do va da lam, §6b)
Loai C — multilingual_target            : [x] giu dong
Loai C — multi_speaker_voice            : [x] giu dong
Loai C — con lai (nhac, chuyen canh,
         thu tu canh, toc do)            : [x] giu dong
```

⭐ **Chu du an chot bang mot cau luat, khong bang nam o tich:** *"ADR V5 neu di theo
   logic van hanh cua ta thi trien khai, neu lech thi bo."* ⇒ Phien dieu phoi doc lai
   §3-§5 va **phan la KHOP**, roi ky theo. Ly do phan KHOP, tung muc cua Loai C:

   | muc | ly do ADR viet | con dung 26/09? |
   |---|---|---|
   | `multilingual_target` | san pham la **long tieng Viet**, ten no noi dung the | ✅ dung — `ban_ghi.py:47` chot 22/09 |
   | `multi_speaker_voice` | mot giong cho ca video | ✅ dung — hop dong MOT GIONG thuyet minh |
   | `music_replace` | doi **kho nhac co ban quyen** — chua co; chi phi **PHAP LY** | ✅ dung, xem canh bao duoi |
   | `transition` · `reorder` | pha loi hua *"thu tu canh la thu tu goc"* | ✅ dung |
   | **toc do** | va cham truc tiep voi `DUNG_SAI_DO_DAI_S = 0.50` | ✅ dung — mot rang buoc DO DUOC |

⚠️ 🔴 **`music_replace` ⛔ KHONG phai `nhac_nen` cua V3 — dung doc lan, va day la cho
   de lan nhat trong ca tep.**
   - `music_replace` (van GIU DONG) = **nen tang cap nhac**, doi mot kho co ban quyen.
     Cai gia la **phap ly**, khong phai ky thuat.
   - `nhac_nen` (V3, DA LAM 25/09) = **khach tu tai len MOT tep cua ho**, khach giu
     quyen. `am_thanh.py:36` tu khai no la mot NGUON KHAC voi lop `nhac` cua
     `tach_tieng`.
   ⇒ `CAM_TRONG_MVP` van liet `music_replace` (`hop_dong_v4.py:117`) va dieu do **DUNG**,
     ⛔ khong mau thuan voi V3. Ai thay hai dong ay va tuong ta tu mau thuan thi doc lai
     o day.

---

## 6b. ⚠️ Phan da bi THUC TE vuot qua — doc truoc khi tin bat ky cau nao o §3-§4

Ban thao soan **08/09**. Toi **25-26/09**, Loai A va Loai B ⛔ khong con la "dang cho
mot quyet dinh" — chung **da duoc lam va da gop `main`**:

| muc | trang thai that |
|---|---|
| `subtitle_burn` · phu de | ✅ chay o `image_finish` (GD2) sau khi doi thu tu, `8a02df43` |
| `zoom` / chang KHUNG | ✅ o GD2; lan gd2 khai ro zoom **khong tach duoc** khoi crop |
| tu do logo (V4a) · tu do dai chu (V4b) | ✅ `do_vung.py` viet du, **Đ1 da do va chot** (`L_DO_VUNG.md`) |
| xoa logo bang **dien nen** (V5) | ✅ `che_keo` da noi vao chuoi, `PHIEN_BAN_CHE_DO=10`, co phep kiem "⛔ KHONG duong lui ve `lam_mo`" |
| logo **di chuyen** (V4c) | ⛔ **C — KHONG lay**, hai ly do doc lap: gia 5-10x VA no doi khach khoanh o (tuc khong phai bo TU DO). Viral tu thu va tu loai. |
| `upscale` | ✅ `apps/upscalevideo` lam viec nay, ⛔ khong thuoc ASV |

🔑 ⇒ Cau *"chan buoc 14 va 16"* o dau tep la mot **CUA HOI BANG CHUNG MA HE DA THOI
   SAN XUAT**: no doi mot chu ky cho viec da xong. De no o day nguyen van se lam nguoi
   sau di tim mot quyet dinh chua co, trong khi ma da co. Vi vay §6 duoc ky VA §6b
   duoc viet — giu lap luan, bo cai cua da het hieu luc.

⚠️ VA mot lo THAT con lai, ⛔ khong bi §6 dong: `do_vung.de_xuat()` **chua co nguoi
   goi nao** ngoai chinh no va test (grep 26/09). Tuc V4a/V4b **da dung xong ma chua ai
   dung**. Cai con thieu ⛔ khong phai thuat toan — no la mot **be mat UI**: hien khung
   de xuat, khach bam nhan hoac keo sua, roi moi thanh `vung_che` that. `do_vung.py` CO
   Y khong tu dong che, vi nghiem thu 25/09 cho thay V4b ⛔ khong phan biet duoc dai phu
   de voi mot thanh HUD cua game.

⚠️ Ký "mở" cho loại **B** không làm mã đổi. Ô ấy chỉ nói *bắt đầu đo*, và bảy
hạng mục đo ở §4 là thứ ra việc.

---

## 7. Nếu KHÔNG ký thì sao

Không có gì hỏng. Hợp đồng giữ nguyên, hai bước 14 và 16 của §15 ở lại trạng
thái `DEFER`, và **cả hai đều đã có chỗ dành sẵn** trong `V5_UI_INFORMATION_
ARCHITECTURE.md` §4 — tức ngày mở chúng là một lần bật cờ, không phải một lần
thiết kế lại giao diện.

⭐ Đó chính là điều `VIRAL_HARVEST_DECISIONS.md` luật L3 đòi: *`DEFER` không phải
   "quên"*. Tệp này là bằng chứng luật ấy được giữ.
