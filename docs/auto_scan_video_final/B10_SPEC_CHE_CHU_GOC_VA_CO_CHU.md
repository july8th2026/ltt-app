# B10 — Che chữ gốc phải BÁM CHỮ THẬT, và chữ mới phải VỪA DẢI

**Ngày:** 2026-09-28 · **Nguồn:** chủ dự án quan sát trên bản giao T1a-bis, rồi
đối chiếu kho tham chiếu `D:\Viral\resources\app-src` (CHỈ ĐỌC).
**Chủ dự án chốt 3 hướng** (§6).

---

## 1. Bốn quan sát, bốn nguyên nhân cơ học

Chủ dự án nêu: *"che mờ có vẻ có vấn đề — nó nhận diện text hay mặc định khu
vực? che đoạn có text thôi hay full timeline? trên video mẫu nó che 2 dòng từ
đầu đến cuối trong khi có cảnh text 1 dòng. Trong khi text mới thì bé tí."*

**Cả bốn đều đúng.** Mỗi cái một nguyên nhân riêng.

### 1.1 🔴 Ta ⛔ KHÔNG đọc chữ — ta đoán theo biến thiên điểm ảnh

`do_vung.do_dai_chu`:

```python
diem = chuan(M.mean(axis=0)) * chuan(M.std(axis=0))   # "mạnh VÀ đổi"
```

⛔ Không OCR. Suy từ **năng lượng cạnh theo hàng × biến thiên theo thời gian**.

⭐ **Viral hạ đúng cách này xuống hạng CHÓT**, và nêu lý do:

> `manual → RapidOCR(clustering) → OpenCV(phat_hien_dai) → none`
>
> *"OpenCV (đoán qua biến thiên pixel, ⛔ không đọc chữ thật → nhầm animation /
> đồ hoạ động thành 'dải sub', user báo video Whisper ⛔ không hardsub vẫn bị
> che to)"*

Và OpenCV **chỉ** chạy khi cả hai tầng OCR **lỗi KỸ THUẬT** — ⛔ không phải khi
OCR chạy xong mà ⛔ không thấy chữ. Hai trạng thái ấy ⛔ không được gộp.

⚠️ **Chính ta đã đo được giới hạn đó** (25/09, `do_vung.de_xuat` docstring):
*"V4b ⛔ không phân biệt được dải phụ đề với bảng tên HUD của game… đó là GIỚI
HẠN CỦA PHƯƠNG PHÁP, ⛔ không phải chuyện tinh chỉnh ngưỡng."* Ta **biết** nó
yếu và chốt nó chỉ là *đề xuất* — nhưng ⛔ **không thêm tầng mạnh hơn**, nên
khách hoặc tự khoanh, hoặc nhận một dải đoán.

### 1.2 🔴 Che CẢ VIDEO, vì bộ dò ⛔ không trả trường thời gian

```python
return KetQua(vung=({"x0": 0.0, "y0": y0f, "x1": 1.0, "y1": y1f},), ...)
```

⭐ **Cơ học thì ta ĐÃ CÓ đủ:** `vung_che.chuan_hoa` nhận `tu_giay`/`den_giay`
(`hinh_hoc.khoang_thoi_gian`), `che_do_render._bat_khi` sinh
`enable=between(t,…)`, giao diện có sẵn ô *"Từ giây"/"Đến giây"*.

⇒ **⛔ Không ai điền tự động.** Một năng lực có mã mà ⛔ không có đường vào —
cùng họ với `danh_dau_phu_de` (B9-2b) và `chu_han_lot` (B9-3): **phép tính
đúng, đường dẫn tới nó thì thiếu**.

Viral có **blur ĐỘNG**: `blur_segs = (t_on, t_off, y0, y1, x0, x1)` — mỗi đoạn
một khoảng **và** một hộp riêng.

### 1.3 🔴 Dải cao gấp đôi vì nó là HỢP TRÊN THỜI GIAN

Hồ sơ hàng cộng dồn **mọi khung mẫu**: hàng nào có chữ ở *một số* khung đều góp
điểm. ⇒ dải = **bao của mọi khung** ⇒ một cảnh 2 dòng kéo dải cao gấp đôi cho
**cả video**, đúng như chủ dự án thấy.

Viral gặp đúng: *"hộp clustering bin-kề phòng 2 dòng → 1 dòng bị cao ~2× ('che
quá to')"* — chữa bằng `_om_sat_vien` (ta **đã chép** hàm này) **cộng** hộp
theo từng đoạn. Ta có nửa đầu, thiếu nửa sau.

### 1.4 🔴 Ta che FULL chiều ngang

`x0 = 0.0, x1 = 1.0` luôn luôn. Viral vá đúng chỗ này 31/08/2026:
*"khách kéo hẹp dải trong editor mà render vẫn che hết chiều ngang"*.

### 1.5 🔴 Cỡ chữ mới ⛔ không liên quan gì tới dải che

Ta đặt `margin_v` theo **đáy dải** (B8/B9-2b) nhưng cỡ chữ thì chọn riêng: sau
B9-1 nó là *lớn nhất sao cho 2 dòng vừa **bề rộng***. Câu dài ⇒ chữ nhỏ.

Viral có **hai** luật ta thiếu cả hai:

```python
s  = min(W, H) / 288.0                  # quy chiếu CẠNH NGẮN, ⛔ không phải chiều cao
fz = max(8, round(fz_base * s))
_fz_dai = int((_dh * H * 0.85) / 1.15)  # KẸP theo chiều cao DẢI che
```

Và họ đặt bằng `\pos` + `\an5` (neo **tâm**), ⛔ không dùng `MarginV`, vì đo
được: *"force_style MarginV libass áp ⛔ KHÔNG đáng tin: 72 ≡ 144"*.
**Ta đang dùng đúng cái `margin_v` đó.**

---

## 2. Vì sao luật `min(W,H)` chứ ⛔ không phải `H`

Viral đo thật (burn ffmpeg + đếm pixel chữ), khung `1080×1920`, `size = 15`:

| công thức | cỡ chữ | khối chữ | bề ngang |
|---|---|---|---|
| cũ `H/288` | **100 px** | cao 165 px | **73,2 %** — câu 30 ký tự đã vỡ 2 dòng |
| mới `min(W,H)/288` | **56 px** | cao 43 px | 57,2 % |

⭐ Và khung ngang `1920×1080` cho `min = 1080 = H` ⇒ **y hệt công thức cũ**, nên
⛔ không hồi quy cho khách 16:9. Một biểu thức, ⛔ không cần nhánh `if H > W`.

⚠️ **Bài học họ ghi kèm đáng giá hơn công thức.** Bản cũ CÓ một cái kẹp cho
khung dọc, gác sau `if not _co_env_fz`. Nhưng giao diện **luôn luôn** gửi `size`
⇒ biến môi trường **luôn** có ⇒ **cái kẹp chưa bao giờ chạy từ giao diện**:

> *"cửa thoát hiểm cho power-user trở thành ĐƯỜNG ĐI MẶC ĐỊNH, mà comment giải
> thích vẫn nằm đó nên đọc qua thấy rất hợp lý."*

⇒ Cùng họ *"luật hẹp ru ngủ"* và *"tham chiếu chết"*: cả ba tạo **niềm tin rằng
có lưới**.

---

## 3. Hai bẫy hiệu năng Viral đã trả tiền — ⛔ đừng trả lại

### 3.1 `crop` ⛔ KHÔNG hỗ trợ `enable=`

Đo thật: 18 dải / 10 phút ⇒ blur động chiếm **75 %** thời gian render, dù
`gblur`/`overlay` đã có `enable=`. Vì N chuỗi `crop` riêng vẫn chạy trên **mọi
khung × N dải**.

⇒ Thuốc: **gộp** nhiều dải thành **một** chuỗi — một `crop` kích thước cố định
(= khung lớn nhất trong nhóm) với `x`/`y` là **biểu thức lồng
`if(between(t,…))`**, một `gblur` + một `overlay` với `enable` = tổng OR.

### 3.2 ffmpeg vỡ biểu thức `if()` lồng ở N = 99

Đo nhị phân trên máy thật: **N = 98 OK, N = 99 FAIL** (*"Missing ')' or too many
args"*). Phim 63 phút ra đúng 100 dải — **sát ngưỡng**.

⇒ Thuốc: chia nhóm **≤ 60 dải/chuỗi**.

⚠️ **Hai con số này đo trên máy KHÁC và ffmpeg KHÁC.** Phải **đo lại** trên máy
A trước khi ghim — đúng luật *"một con số cổng phải kèm SHA · MÔI TRƯỜNG · TẬP
ĐO"*. ⛔ Chép thẳng `60`/`98` là mượn một phép đo ⛔ không phải của mình.

---

## 4. Trạng thái phải phân biệt, ⛔ đừng gộp

Viral tách ba, và **cả ba đều cần**:

| trạng thái | nghĩa | hành động |
|---|---|---|
| `LoiKyThuat` (**ném**) | chưa cài / crash / ⛔ không mở được tệp | **lùi** tầng sau |
| `None` (**trả**) | quét thật, ⛔ không thấy chữ | **TIN**, ⛔ không che, ⛔ không lùi |
| có dải | thấy | che |

🔴 Gộp hai cái đầu là đúng lỗi họ ghi 31/07: nuốt lỗi kỹ thuật thành *"video ⛔
không có sub cứng"* ⇒ **⛔ không che ⇒ lộ chữ Hán**.

⭐ Ta đã có hình dạng này ở `de_xuat` (`khong_do_duoc` + `ly_do` vs `khong_co`) —
giữ nguyên và mở rộng cho tầng mới.

---

## 5. Cổng an toàn của Viral, đáng lấy

> *"Dải RapidOCR quá RỘNG (> 22 %) — video có thể ⛔ KHÔNG có phụ đề cứng → ⛔
> KHÔNG blur"*

⭐ Một dải chiếm hơn 22 % chiều cao **⛔ không phải phụ đề** — đó là giao diện,
đồ hoạ, hay một cảnh nhiều chữ. Che nó là **làm hỏng video của khách**, và
*"đo sai nguy hơn ⛔ không đo"* (chính docstring `de_xuat` của ta).

---

## 6. Ba chốt của chủ dự án (28/09)

| câu | chốt |
|---|---|
| tầng dò | **Thêm RapidOCR làm tầng CHÍNH**; cách hiện tại tụt xuống tầng lùi |
| phạm vi thời gian | **ĐỘNG theo từng đoạn** |
| cỡ chữ | **Cạnh NGẮN + kẹp theo chiều cao dải** |

## 7. Bất biến để kiểm

> **BB-1** — Video có phụ đề gốc **1 dòng ở đoạn A, 2 dòng ở đoạn B** phải cho
> **hai** hộp che chiều cao **khác nhau**. (Một phép kiểm chỉ chốt một đoạn sẽ
> xanh cả khi dải vẫn là hợp-trên-thời-gian.)
>
> **BB-2** — Đoạn ⛔ **không có** chữ gốc phải **⛔ không** có ô mờ nào bật.
>
> **BB-3** — Hộp che phải có `x1 − x0 < 1.0` khi chữ gốc ⛔ không trải hết bề
> ngang.
>
> **BB-4** — `LoiKyThuat` phải **lùi tầng**; `None` phải **⛔ không che**. Hai ca
> cho hai hành động khác nhau, và phải có phép kiểm cho **cả hai**.
>
> **BB-5** — Khung `1920×1080` phải cho cỡ chữ **y hệt trước B10** (vì
> `min(W,H) = H`). ⛔ Không hồi quy cho khách 16:9.
>
> **BB-6** — Dải hẹp đi ⇒ cỡ chữ **nhỏ đi**; dải rộng ra ⇒ cỡ chữ **to lên**,
> tới trần `fz`. (Chốt rằng kẹp theo dải **thật sự** nối vào.)
>
> **BB-7** — Dải > 22 % chiều cao ⇒ **⛔ không che**.

## 8. Thứ tự thi công

1. **B10-1 cỡ chữ** — gọn trong `phu_de.py`, ⛔ không phụ thuộc mới, thấy ngay.
2. **B10-2 hộp ngang + ôm sát Y theo đoạn** — sửa `do_vung`, còn dùng bộ dò cũ.
3. **B10-3 che ĐỘNG** — nối `tu_giay`/`den_giay` vào đường đề xuất + gộp nhóm.
4. **B10-4 RapidOCR** — tầng chính; cần gói mới trên **cả hai** venv.

⭐ Xếp vậy vì mỗi bước **tự nó đã cải thiện** và đo được riêng. ⛔ Không gộp
bốn thứ vào một lượt rồi ⛔ không biết cái nào tạo ra khác biệt.

## 9. ⛔ Ngoài phạm vi

- **`\pos` + `\an5` thay `MarginV`**: Viral đo được `MarginV` của libass ⛔ không
  đáng tin (`72 ≡ 144`). Ta **chưa đo lại** trên libass của ta — và B8 đang dựa
  hoàn toàn vào `margin_v`. ⇒ **Đo trước, đổi sau.** Đổi mà ⛔ không đo là thay
  một cơ chế đang chạy bằng một cơ chế mượn niềm tin.
- **T4 độ to** — nợ riêng, xem `am_master.py` (`BIEN_CHO_CODEC_DB`).
