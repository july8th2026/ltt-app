# B11 — Plan tổng: dọn ba nợ treo TRƯỚC khi chạy gate

**Ngày:** 2026-09-28 · **Chủ dự án chốt:** *"tổng hợp 3 việc treo để giải quyết
trước khi chạy gate. Giao việc cho agent nếu cần."*

**Trạng thái lúc lập plan:** HEAD `42f39973` · cây sạch · production đang chạy
`8907b4dd` ⇒ **16 commit chưa lên**.

---

## 1. Bức tranh: ta đang ở đâu trong vòng lặp

```
VÒNG 1   gate ─► deploy ─► job test ─► kiểm ─► fix          ✅ trọn vẹn (B9)
VÒNG 2   fix ────────────────────────────────► gate ─► deploy ─► job test
         B10-1 ✅  B10-4 ✅  B10-2/3 ⏳  +  BA NỢ  ← ĐANG Ở ĐÂY
```

⚠️ **Vì sao dọn nợ TRƯỚC gate, ⛔ không phải sau.** Cả ba nợ đều **đổi thứ gate
đo hoặc đổi cách gate chạy**:

| nợ | nếu để sau gate |
|---|---|
| T4 độ to | job test vòng 2 sẽ **lại đỏ T4**, và ta ⛔ không phân biệt được đỏ-cũ với đỏ-mới |
| `\pos` vs `MarginV` | nếu `MarginV` thật sự ⛔ không đáng tin thì **mọi** phép đo vị trí phụ đề của B8/B9/B10 đang đo một thứ **có thể sai** |
| `[WinError 206]` | gate **⛔ không chạy nổi bộ test** ở phạm vi lớn — nó in `PASS` rỗng |

⇒ Chạy gate trước khi dọn là **trả tiền cho một phép đo ⛔ không kết luận được**.

---

## 2. Bốn làn, tệp RỜI NHAU

| làn | việc | tệp sở hữu | ai |
|---|---|---|---|
| **A** | T4 — vòng đo-và-sửa ĐỘ TO | `apps/auto_scan_video/am_master.py` + test riêng | agent (opus) |
| **B** | `[WinError 206]` — `pytest @tệp` | `tools/gate.py`, `tools/test_nhanh.py` + test riêng | agent (sonnet) |
| **C** | ĐO `MarginV` của libass — **⛔ chỉ đo, ⛔ không sửa** | ⛔ không tệp sản phẩm nào | agent (sonnet) |
| **D** | B10-2 + B10-3 — hộp ngang + che ĐỘNG | `do_vung_ocr.py`, `do_vung.py`, `che_do_render.py` | điều phối |

⛔ **⛔ Không hai làn nào chạm cùng một tệp.** Làn C cố ý ⛔ **không** sửa sản
phẩm: nó chạm `phu_de.py`, mà làn D và các bản vá B10 cũng ở gần đó — nên nó
trả về một **phép đo**, và điều phối quyết định sau.

---

## 3. Làn A — T4 độ to

### 3.1 Hiện trạng đo được

```
T1a      master -14,11 LUFS   →  bản giao -14,4   ĐẠT   (sát mép trong)
T1a-bis  master -15,04 LUFS   →  bản giao -15,44  HỎNG  (đích -14,0 ± 1,0)
```

Bản giao **bám sát** master cả hai lần ⇒ lỗi ở chính phép chuẩn hoá master.
Đỉnh thật `-5,75 dBTP` ⇒ **còn thừa ~3 dB biên** — nó *có thể* to hơn mà ⛔
không làm.

### 3.2 ⛔ Đây ⛔ KHÔNG phải hồi quy — là nợ có tên đến hạn

`am_master.py` chỉnh độ to bằng **một hằng số tay** (`BIEN_CHO_CODEC_DB = 0.25`)
hiệu chỉnh trên **hai lần chạy cụ thể** (27/09). Chính chú thích ở đó viết:

> ⚠️ Đây ⛔ **không** phải bản sửa bền vững. Bền vững là một **vòng đo-và-sửa
> cho ĐỘ TO**, đối xứng với `ghim_tran_phoi` của ĐỈNH: `do_ban_giao` này ĐÃ trả
> `lufs` của bản giao thật, nên con số để sửa **đã có sẵn** — chỉ thiếu vòng áp
> nó. ⛔ **Chưa làm** vì hai vòng ấy **TRANH nhau** (tăng gain để lên `-14,0`
> thì đẩy đỉnh lên, vòng ghim lại hạ xuống), và một vòng hội tụ cần **thiết
> kế** chứ ⛔ không cần một hằng số.

⭐ Bài học sản phẩm: **một hằng số hiệu chỉnh trên hai mẫu ⛔ không phải một
vòng điều khiển.** Nó xanh cho tới khi gặp mẫu thứ ba.

### 3.3 Yêu cầu

- Vòng **đo-và-sửa** cho độ to, hội tụ cùng vòng ghim đỉnh. Trần lượt lặp phải
  **hữu hạn** và con số ấy phải **đo ra**, ⛔ không chọn.
- ⛔ **Không** làm hỏng T5 (đỉnh `≤ -1,5 dBTP`).
- ⛔ **Không** thêm một lượt mã hoá nào nếu tránh được; nếu có thì **đo** và ghi.
- Bất biến: hai bản dựng có **nội dung khác nhau** phải cho độ to **trong cùng
  khoảng**. (Chốt một giá trị là chốt cách gõ; chốt *"cả hai đều trong khoảng"*
  mới là chốt tính chất.)

---

## 4. Làn B — `[WinError 206]`

### 4.1 Hiện trạng đo được

```
gate.py --doi   →  bước test CHẾT trong 0,0 giây
                   khong chay duoc: [WinError 206] The filename or extension is too long
```

Gate truyền **từng** đường dẫn test vào một dòng lệnh `pytest`; phạm vi
972–1001 tệp vượt trần **32 767 ký tự** của Windows. Bước test **⛔ không chạy**
mà gate vẫn chạy 32 bước còn lại.

⚠️ Và dòng *"CHẠY LẠI ĐÚNG PHÉP ĐO"* mà chính gate in ra **cũng** liệt kê 1001
tệp ⇒ **chỉ dẫn nó đưa cũng ⛔ không chạy nổi**.

### 4.2 Yêu cầu

- Truyền danh sách qua **tệp đối số** (`pytest @tệp`), sửa **cả** `tools/gate.py`
  **lẫn** `tools/test_nhanh.py`.
- Dòng *"CHẠY LẠI ĐÚNG PHÉP ĐO"* phải in một lệnh **chạy được**.
- Bất biến: một phạm vi **1000 tệp** phải chạy được. ⭐ Chốt bằng cách **dựng
  1000 đường dẫn giả** và kiểm dòng lệnh, ⛔ không chạy 1000 tệp thật.

---

## 5. Làn C — ĐO `MarginV`, ⛔ KHÔNG sửa

### 5.1 Vì sao nghi ngờ

Kho tham chiếu `D:/Viral` ghi, kèm phép đo:

> *"đo thật `force_style` MarginV libass áp **KHÔNG đáng tin**: 72 ≡ 144"*

Họ chuyển hẳn sang `\pos` + `\an5`. **Ta đang dùng đúng cái `MarginV` đó** —
`phu_de.vi_tri_tu_dong` trả `margin_v`, và **toàn bộ B8 + B9-2b + B10-1** dựa
trên nó.

⚠️ Nếu điều đó đúng trên libass của **ta**, thì mọi phép kiểm vị trí phụ đề của
ba đợt ấy đang chốt một con số mà libass **⛔ không thi hành** — tức chúng xanh
mà ⛔ không bảo vệ gì.

### 5.2 Yêu cầu — đây là một PHÉP ĐO, ⛔ không phải một bản vá

Trả lời **đúng một** câu: *"trên libass của máy này, hai `MarginV` khác nhau có
cho hai vị trí chữ khác nhau ⛔ không?"*

- Burn thật bằng ffmpeg, **đếm pixel** vị trí khối chữ — ⛔ không đọc `.ass`,
  ⛔ không tin `force_style`.
- Quét một **dải** giá trị (vd. 20, 40, 72, 100, 144, 200) trên ít nhất **hai**
  chiều cao khung.
- ⛔ **Không sửa một dòng mã sản phẩm nào.** Trả bảng số + kết luận.

---

## 6. Làn D — B10-2 + B10-3 (điều phối tự làm)

- **B10-2** hộp ngang: đã có từ B10-4 (`x 0,09..0,90`); kiểm nó đi hết đường
  tới bộ lọc che, ⛔ không bị chỗ nào ép lại `0..1`.
- **B10-3** che động: `do_dai_chu_ocr` trả **nhiều đoạn** kèm `tu_giay`/
  `den_giay`, kẹp ở **điểm giữa** hai đoạn kề; nối vào `de_xuat` → `vung_che`.
- ⚠️ **Đo lại trên máy A** hai hằng số của kho tham chiếu, ⛔ không chép:
  `crop` có hỗ trợ `enable=` ⛔ không, và ffmpeg vỡ biểu thức `if()` lồng ở N
  bằng bao nhiêu.

---

## 7. Khép lại

```
A · B · C · D xong  ─►  gộp, giải xung đột  ─►  gate phạm vi sửa đổi ở CÂY GATE
                    ─►  đo lại SHA ngay trước khi bấm deploy
                    ─►  `ai_dang_dung_may_chu.py` = RẢNH  ─►  deploy
                    ─►  T1a-ter (9 trục)  ─►  cắt frame + đo TRƯỚC/SAU
```

⚠️ Deploy mang theo cả `core.human` + bundle + 3 bản dịch của phiên agent-ui.

## 8. Câu chưa hỏi chủ dự án, và khi nào hỏi

Sau B10-3, vệt mờ **bám từng câu**; phụ đề mới vẫn đặt theo **một** dải tĩnh.
Nếu chữ gốc đổi chỗ giữa video thì hai thứ **lệch nhau**.

⇒ Thuốc của kho tham chiếu là ASS `\pos` **theo từng cue** — việc lớn hơn
B10-3 và **kéo theo** làn C.

⛔ **Chưa hỏi**, vì câu hỏi ⛔ không đáng đặt khi chưa có số. Sẽ đo *"bao nhiêu
% số đoạn thật sự đổi chỗ"* trên phim mẫu rồi mới hỏi: gần 0 thì ⛔ không đáng
làm; cao thì thành hạng mục bắt buộc.
