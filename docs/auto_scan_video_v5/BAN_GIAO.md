# BÀN GIAO — ASV V5, phiên 08/09/2026

> Đọc tệp này trước khi làm tiếp Auto Scan Video. Nó **không** kể lại việc đã
> làm — `V5_IMPLEMENTATION_STATUS.md` và `V5_REAUDIT.md` đã kể. Nó ghi **những
> kết luận SAI mà phiên này đã phát ra**, để phiên sau không đi lại các ngõ cụt
> ấy, và ba việc còn dở.

---

## 0. Trạng thái

| | |
|---|---|
| Nhánh | `phien/asv-v4` — `6bef65c8` |
| §15 | 21/24 bước xanh hoàn toàn; 3 bước còn lại **không chờ lập trình** (xem §3) |
| Gate L3 | `FAIL (1/29)` — đỏ đúng một bước, 19 ERROR đều là `test_448` |
| Test | 8.072 + 96 passed, **0 FAILED** |

---

## 1. 🔴 BA kết luận phiên này phát ra và SAU ĐÓ tự bác bỏ

Ghi ra vì cả ba đều **nghe hợp lý** và cả ba đều **sai**, nên một phiên sau rất
dễ tin lại chúng.

### 1.1 *"Sinh lại `nghiem_thu_hien_hanh.json` cần UAC"* — **SAI**

Tôi lấy chữ *"Cần Administrator"* từ docstring của `setup/nghiem_thu_asv.ps1`
và không đo lại yêu cầu thật.

**Sự thật đo được:** bài ghi báo cáo là
`test_448::test_NGHIEM_THU_ca_hai_preset_ra_video_dung_duoc`, mang
`@rao_chan_nang.NANG` + `@CHI_KHI_BAT`. Nó cần `LTT_TEST_NANG=1` và
`LTT_ASV_E2E_RA`, **không cần quyền nào**.

Script cần Administrator để lấy **token giọng thật**; hai `assert` đòi giọng
thật thì **có điều kiện** (`if not khai:` / `if not bc["thay_the"]:`), nên một
lượt khai rõ đã thay thế cái gì vẫn hợp lệ.

⛔ **Hai rào bị gộp làm một, chỉ một là thật.** Trước đó tôi còn một rào thứ ba
   — *"ghi đè bằng chứng không đảo ngược được"* — cũng sai, vì tệp được git theo
   dõi. Gỡ được rào ấy rồi tôi **giữ nguyên rào UAC mà không kiểm lại nó**.

### 1.2 *"trim bị chặn bởi ràng buộc vật lý"* — **NÓI QUÁ**

Nó **bị hạn chế**, không bị chặn. `giai_doan_ban_dung.py:123` lấy
`khoang = list(ban_do.giu)` ngay tại chỗ `vung` đi vào từ `run.settings` — trim
chỉ cần **giao** với khoảng ấy, một phép toán tại một điểm.

⭐ Và nó **tự được vân tay hoá**: `khoang_giu` đã nằm trong bản dựng, bản dựng đã
   vào vân tay. Không cần thêm trường nào. Thiết kế đầy đủ ở §4.

Hạn chế thật: **chỉ dùng được ở preset cắt**. Preset giữ hình đi `-c:v copy` và
hứa *"video ra dài đúng bằng video vào"* — cắt thì phá lời hứa ấy. Đó là quyết
định **sản phẩm**, và nó cưỡng chế bằng cùng khuôn ba lớp của vùng che.

### 1.3 *"Claude chạy admin"* — **SAI với phiên này**

Đo trực tiếp: `la Admin: False`, và `Test-Path C:\LTTPlatform\secrets\app.env`
ném `UnauthorizedAccessException` — không **nhìn thấy** được tệp, chứ chưa nói
đọc. Nếu một phiên nào đó thật sự chạy nâng quyền thì nó phải được khởi động
khác cách; đừng giả định.

---

## 2. ⛔ Lượt nghiệm thu 21:41 — thứ nó chứng minh và thứ nó KHÔNG

Tôi chạy với `LTT_TEST_NANG=1` và **thiếu cờ bật đường thật**. Kết quả:

```
2 phut 51 -> FAILED
thay_the = 4: dieu_phoi.goi · doc_mot_doan · giai_giong · san_sang
giong_that=False  model_that=False
```

⇒ Lượt ấy **không chạm máy B**. Nó thay cả LLM lẫn ba cửa giọng bằng bản giả,
nên nó không nói gì về sản phẩm. Hai lỗi thu được:

| | |
|---|---|
| `giu_hinh / compose` | `sqlite3.OperationalError: database is locked` — **hạ tầng test**, nhiều phiên cùng ghi |
| `cat_thong_minh / qc` | trượt mục **T4** — gần như chắc vì giọng thay thế là SAPI tiếng Anh trong một bài lồng tiếng **Việt** |

**Đã hoàn nguyên** bằng `git checkout`, đối chiếu băm với một bản sao ngoài kho:
`f01bda6a6ee9ecea`, 20.475 byte, khớp từng byte.

### 🔑 Việc còn thiếu để chạy được lượt THẬT

| Điều kiện | Trạng thái |
|---|---|
| `LTT_TEST_NANG=1` | ✅ đặt được, không cần quyền |
| `LTT_ASV_E2E_RA` | ✅ |
| **Cờ bật đường model thật** | ❌ **chưa tìm ra** — đây là việc đầu tiên của phiên sau |
| Máy B rảnh cho `ltt_llm` | chưa xác minh |
| Token giọng thật (`app.env`) | ❌ cần nâng quyền; **không bắt buộc** — xem §1.1 |

⚠️ Bản đang có trong kho khai `giong_that: True`, `model_that: True`,
`thay_the: 0`. Nó là một lượt **toàn phần** hỏng vì máy B bận. Một lượt sinh lại
mà không bật đủ cờ sẽ **hạ cấp** bằng chứng — hãy chép tệp ra ngoài kho trước
khi bấm, vì `git checkout` chỉ cứu được khi chưa commit đè.

---

## 3. Ba bước §15 chưa xanh — không bước nào chờ lập trình

| Bước | Chặn bởi |
|---|---|
| **14** Subtitle controls | `CAM_TRONG_MVP: subtitle_burn`; `apps/autosubvideo` **đã sở hữu**. Mở ra là chép lại. Cần chữ ký ADR — `ADR_V5_DRAFT.md` §3 |
| **16** Edit controls | phần thiếu (zoom · tỉ lệ · tốc độ · logo) đều bị `CAM_TRONG_MVP`/`HAU_MVP`; **trim thì không** — xem §4 |
| **21** E2E | chính là §2 |

`ADR_V5_DRAFT.md` chia tám mục `DEFER` thành **ba loại** và đó là điểm chính của
nó: một chữ ký mở được loại A và C, nhưng **không mở được loại B** — thứ thiếu ở
đó là bảy phép đo VRAM, không phải một quyết định.

---

## 4. trim — thiết kế đầy đủ, CHƯA áp

Module đã soạn nhưng nằm ngoài kho (scratchpad của phiên, sẽ mất). Chép lại đây
để không phải nghĩ lại.

**Điểm nối:** `giai_doan_ban_dung.py:123`, ngay sau `khoang = list(ban_do.giu)`:

```python
khoang = cat_dau_cuoi.giao(khoang, cua_so, thoi_luong_nguon)
```

**Bốn luật:**

1. **Toạ độ là phân số 0..1**, y hệt `vung_che` — một bộ luật cho cả hai. Đổi
   sang giây xảy ra đúng ở `giai_doan_ban_dung`, nơi biết thời lượng thật.
2. **Sai thì TỪ CHỐI, không đoán.** Cửa sổ ngược không được tự đảo lại.
3. **Chỉ ở preset cắt** — cưỡng chế ba lớp: giao diện ẩn + giải thích, route từ
   chối, giai đoạn không tin giao diện.
4. **Cửa sổ `(0.0, 1.0)` ≡ vắng mặt** — không thu hẹp gì thì không ghi gì, nếu
   không mọi vân tay cũ đổi mà không một khung hình nào đổi.

```python
TOI_THIEU = 0.02          # ngan hon thi moi phep chia thoi gian sau do vo

def chuan_hoa(tho) -> tuple[float, float] | None:
    """[bat_dau, ket_thuc] phan so -> cap da duyet, hoac None neu ca video."""
    if tho in (None, "", (), []):
        return None
    try:
        a, b = tho
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        raise CatLoi(_t('Đoạn cắt không đọc được.')) from None
    # NaN/inf lot qua moi phep so sanh duoi neu khong chan rieng.
    if not (a == a and b == b) or a in (float("inf"), float("-inf")) \
            or b in (float("inf"), float("-inf")):
        raise CatLoi(_t('Đoạn cắt không đọc được.'))
    if not (0.0 <= a < b <= 1.0):
        raise CatLoi(_t('Đoạn cắt phải nằm trong video và điểm đầu phải trước điểm cuối.'))
    if b - a < TOI_THIEU:
        raise CatLoi(_t('Đoạn cắt quá ngắn.'))
    if a == 0.0 and b == 1.0:
        return None                      # luat 4
    return (a, b)


def giao(khoang, cua_so, thoi_luong: float) -> list[tuple[float, float]]:
    if not cua_so or thoi_luong <= 0:
        return [(float(b), float(k)) for b, k in khoang]
    tu, den = cua_so[0] * thoi_luong, cua_so[1] * thoi_luong
    ra = []
    for b, k in khoang:
        b, k = max(float(b), tu), min(float(k), den)
        if k - b > 0:
            ra.append((b, k))
    return ra
```

⚠️ `giao()` trả danh sách **rỗng** nếu cửa sổ không chạm khoảng nào. `ban_dung.dung`
   đã ném cho trường hợp ấy — nhưng thông điệp sẽ nói về "bản dựng không có
   khoảng nào", không nói về trim. Đáng cho một thông điệp riêng.

---

## 5. Hai thứ CỐ Ý không làm — cùng một lý do

Cả hai **đúng ở trunk, sai ở cây này**, vì thay đổi chưa tới nơi người khác đo:

1. **`doc_so_tran` → `None`** (theo khuôn engine). Bản `text_pipeline.chuan_hoa`
   của LTT VOICE chưa hoà tới, nên `chuan_hoa` ở cây này vẫn khai `bool`; truyền
   `None` chỉ chạy đúng nhờ truthiness chứ không nhờ hợp đồng, và mypy nói ra
   (`arg-type` 124 → 125). Lý do đầy đủ ghi trong `giong_noi.py`.
   ⇒ **Làm ở lượt hoà.** Phiên VOICE giữ `tests/test_514` (bất biến: không app
   nào ghim cứng khuôn chuẩn hoá) chờ đúng lúc đó.

2. **Hạ mốc mypy** (`attr-defined` 205 → 204, đã **giảm**). Mốc là tệp dùng
   chung; hạ dựa trên một cây chưa hoà sẽ làm **trunk đỏ cho mọi phiên**.

---

## 6. Ba cái bẫy đã trả giá trong ngày

**Kết dòng.** `tests/test_409_asv_giong_noi.py` là tệp **CRLF** duy nhất trong
nhóm. Chèn một dòng LF vào là trộn kết dòng ⇒ hook `kieu xuong dong` đỏ vì một
lý do chẳng liên quan. `grep` và `cat -A` đều **nuốt `\r`** và báo "LF ok"; chỉ
`read_bytes()` nói thật.

**Neo là chuỗi con.** `"            vt = _van_tay(...)"` (12 dấu cách) là chuỗi
con của dòng 16 dấu cách ⇒ khớp 2 lần. Và `assert d.count("tu_dien=tu_dien")==2`
sai vì `tu_dien=tu_dien or None` chứa nó. **Ghim neo theo đầu dòng, và khẳng
định trên mệnh đề thật chứ đừng đếm chuỗi.**

**Mặc định im lặng.** Bản đầu cho `_van_tay` mặc định `tu_dien=None` rồi quên cả
hai lời gọi ⇒ từ điển lặng lẽ không vào vân tay, mọi test xanh, chỉ khách nhận
nhầm tệp tiếng. **Bỏ mặc định** biến nó thành `TypeError` không bỏ qua được.

---

## 7. Hình dạng lỗi lặp lại nhiều nhất trong ngày

Bốn ca, bốn phiên khác nhau, cùng một hình dạng — **năng lực đúng, đường tới
người dùng không có ai đi**:

```
license_status         cong DOC, khong ai GHI
a11y_quet --cookie     docstring khai, chua bao gio chay
NHAN_LOC[phong_cach]   route loc du BA, template ve HAI
tu_dien_rieng          chu ky NHAN, khong ai TRUYEN
```

Cả bốn đều **có phép kiểm và phép kiểm đều xanh**, vì mỗi tầng làm đúng phần của
nó. Cái sai nằm ở **khoảng giữa** — chỗ không tầng nào sở hữu.

⇒ Câu hỏi bắt được chúng không phải *"nó có đúng không"* mà là hai câu nối nhau:
  **"có đường tới người dùng không"**, rồi **"có ai ĐANG đi trên đường đó không"**.

Và một hình dạng thứ hai, gặp **bốn lần giữa ba phiên**: *phép đo đúng, phạm vi
sai*. Hai phiên cãi nhau về một giá trị mà cả hai đo đúng — trên hai cây khác
nhau, và không ai nói ra giả định ngầm rằng mình đứng cùng chỗ.

⇒ **Con số chuyền giữa hai phiên phải kèm tên cây.** Kết luận *"X gọi Y"* phải
  kèm số hiệu dòng của lời gọi.
