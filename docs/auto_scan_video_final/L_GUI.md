# L_GUI — Studio: mọi điều khiển về đích

> Làn `gui` của phiên `asv-final`. Cây `D:\LTTSTUDIOSAPP-asvf-gui`, nhánh
> `phien/asv-final-gui`, gốc `d8a39091` (15 làn đã gộp).
> Đề bài §12: *"khách dùng được mọi thứ hai ngày qua đã thêm"* — mỗi điều khiển
> phải đi hết **giao diện → cài đặt đã lưu → manifest → engine → khác biệt nhìn
> thấy trong tệp ra hoặc trong báo cáo**. ⛔ Không ô chết.

---

## 1. 🔴 Phát hiện chính: `nguon_loi` là một ô CHẾT từ đầu đến cuối

Làn `ocr` (22/09) đã làm đủ: hằng số, `chuan_che_do`, `dinh_tuyen` bốn chế độ,
phép duyệt ở `dung_cai_dat`, khoá trong `KHOA_NHAN`, trường đọc ở
`cai_dat.tu_ho_so`, và `giai_doan_chep_loi` đọc `cai.nguon_loi`. Chỉ **một
dòng** không có:

```python
# dich_vu_tao.dung_cai_dat — bản cũ
nl = str(tho.get("nguon_loi") or "").strip().lower()
if nl and nl not in nguon_loi_mod.CHE_DO_HOP_LE:
    raise LoiCaiDat(_t('Nguồn lời thoại không hợp lệ.'))
# ... và `nl` KHÔNG BAO GIỜ được dùng lại: hồ sơ trả về không mang khoá này.
```

Hậu quả: khách ép *"chữ trên hình"*, đi qua **cửa không một lỗi nào**, và lần
chạy vẫn chạy `auto`.

⚠️ **Kiểu hỏng này không thể kêu.** Mọi phép kiểm đơn lẻ đều xanh — chúng hỏi
*một mắt xích*. Và `auto` là một kết quả hợp lệ, chỉ không phải cái khách chọn.
Nó chỉ lộ ra khi có người đối soát **giao diện** với **hồ sơ đã lưu**, và đó
đúng là việc của làn này.

⇒ Sửa: một dòng `"nguon_loi": nl` trong hồ sơ. `chuan_hoa` tự bỏ khoá khi nó
bằng `auto` (luật `KHOA_THUA`), nên **vân tay của những lần chạy không ép nguồn
không đổi**.

Chốt lại bằng `test_2100::test_nguon_loi_ep_OCR_di_toi_GIAI_DOAN_chep_loi` —
phép kiểm hỏi **câu hỏi cuối** (*"cái khách bấm có nằm trong hồ sơ không"*),
là câu hỏi duy nhất một ô chết không trả lời được.

---

## 2. Ba ô mới trên màn Studio

| ô | ở đâu | về đích ở đâu |
|---|---|---|
| `ngon_ngu_nguon` (auto/zh/en/vi) | **tầng cơ bản**, cột "Bạn muốn gì" | ASR đọc bằng bảng chữ nào; `kiem_nguon_da_doan` chốt lại sau ASR |
| `ngon_ngu_dich` (vi/en) | **tầng cơ bản**, ngay trên ô Giọng | lọc danh sách giọng **ngay lập tức**; LLM dịch sang đâu |
| `nguon_loi` (auto/embedded/ocr/asr) | nâng cao | `nguon_loi.dinh_tuyen`; nguồn THẬT hiện ở màn một lần chạy |

**Cặp ngôn ngữ ở tầng cơ bản, không ở nâng cao** — chúng không phải tinh chỉnh:
chúng quyết định ASR nghe bằng gì, LLM dịch sang đâu, và **giọng nào còn chọn
được**. `nguon_loi` thì ngược lại: mặc định `auto` đúng cho gần hết khách.

**Miền giá trị đến TỪ module** (`ngon_ngu.cho_giao_dien()`,
`nguon_loi.cho_giao_dien()`), không gõ `zh`/`ocr` vào Jinja — cùng luật với
`preset_can_cho_vung`. `test_2100::test_mien_gia_tri_den_TU_module` chốt.

### 2b. Ô ngôn ngữ đích lọc danh sách giọng — và đó là chỗ nó về đích ở GUI

`rang_giong._rang_khach_chon` **từ chối ở cửa** một giọng lệch làn với
`ngon_ngu_dich`. Không lọc ở giao diện thì khách đổi đích sang tiếng Anh, vẫn
thấy nguyên 20 giọng tiếng Việt, bấm Gửi và ăn một câu từ chối.

⇒ `gia.giong_cho_giao_dien` phát thêm `ngon_ngu`, template phát `data-lan`,
`giong.js` thêm **mặt lọc thứ tư**. Giọng **nhân bản của khách** mang `data-lan`
rỗng và **không bị lọc**: làn của chúng do `ltt_voice` chốt lúc gọi, không phải
một nhãn đọc sẵn.

🔴 **Và phép lọc này đẻ ra một câu SAI mà trình duyệt bắt được, không phải mã.**
Danh sách rỗng trước đây chỉ có một câu: *"hãy bỏ bớt điều kiện"*. Khách vừa đổi
đích sang tiếng Anh mà kho chưa có giọng `en` nào (F-03) thì câu đó bảo họ đi gỡ
một bộ lọc **không tồn tại**. Nay hai câu, tách bằng `hopLan` (số giọng hợp làn,
bỏ qua mọi mặt lọc khác):

| tình huống | câu |
|---|---|
| hết giọng **trong làn** | *"Chưa có giọng nào đọc được ngôn ngữ này — hãy đổi ngôn ngữ đích, hoặc nhân bản một giọng ở LTT VOICE."* |
| hết giọng **sau bộ lọc** | *"Không có giọng nào khớp bộ lọc — hãy bỏ bớt điều kiện."* |

---

## 3. Màn một lần chạy: khối "Bằng chứng chất lượng"

🔴 **Bốn con số đã tồn tại trong `asv_stage.outputs` và không cái nào với tới
được màn hình của người trả tiền.** Đo được ở lượt nền v3: `smart_localize` giao
một video **không cắt một cảnh nào** (VLM hỏng 4/12 lượt) và màn hình của khách
nói đúng một chữ — *"Đã xong."*

`quan_sat.bang_chung_chat_luong(db, run)` gom bốn nhóm, **không mở kho lưu trữ**
(màn này bị htmx hỏi lại 3 giây/lần):

| nhóm | nguồn | hiện ra |
|---|---|---|
| nguồn lời thoại THẬT | `transcribe.outputs.dinh_tuyen.nguon_loi` | "Lời thoại gốc lấy từ: Chữ chạy trên hình" |
| độ phủ bằng chứng | `edit_plan.outputs` (làn `fix-toc-do`) | "Cảnh đã đọc được: 4/6 (67%) · **2 cảnh không đọc được**" |
| QC tất định | `qc.tom_tat` | "2 mục chưa đạt" + từng mục, nhãn tiếng Việt kèm mã (`T13`, `T18`) |
| bộ đo trên card | `qc_do_luong.outputs` | WER/CER · SQUIM · MetricX, mỗi bộ *đã đo* / **chưa đo được trên máy chủ** |

Ba quyết định:

- **Mở sẵn**, không nằm trong `<details>` như khối *Chi phí*. Một bằng chứng phải
  gập ra mới thấy là một bằng chứng không ai đọc — và nếu QC có mục hỏng thì đó
  chính là điều khách cần biết **trước khi tải video về**.
- **Nhãn nói việc gì được kiểm, không nói kiểm bằng cách nào.** `_muc(...)` đã
  mang một `mo_ta`, nhưng đó là chữ của người vận hành (*"đỉnh thật"*, *"trôi
  tích luỹ không vượt ngân sách của 3 đoạn kế tiếp"*). `qc.NHAN_MUC` là bảng cho
  khách; mã nào thiếu nhãn thì tự hiện ra chính nó (`T19`) — một phép kiểm mới
  phải **lộ ra** chứ không được biến mất im lặng.
- **`khong_kha_dung` phải nói ra.** Luật §2 của brief chung. Một bảng bỏ mất
  hàng "chưa đo được" đọc y hệt một bảng đã đo hết và đều đạt.

⛔ `.asv-bc-ds` là lớp **riêng**, không dùng lại `.asv-cai-dat`: lưới 190px của
nó hợp với những sự thật MỘT DÒNG, còn mỗi mục ở đây mang một danh sách con.

Thêm hai dòng vào *Cài đặt đã dùng*: **Ngôn ngữ** (`zh → vi`, nguồn rỗng nói
*"Tự nhận ra"* chứ không bỏ trống) và **Nguồn lời thoại**.

---

## 4. AUTO_MATCH: câu "vì sao chưa ràng được" nay tới được khách

`rang_giong.vi_sao_chua_rang` nói rõ thiếu gì từ 23/09 — nhưng câu đó **dừng lại
ở cột `error`**, một cột màn hình của khách CÓ Ý không đọc (chữ tự do của vận
hành có thể mang đường dẫn hay tên model). Khách đọc một câu chung chung kèm nút
**"Thử lại bước này"** chắc chắn hỏng: AUTO_MATCH trên cùng bản chép lời cho ra
đúng kết quả đó.

⇒ Ba mã ổn định trong `rang_giong.CAU_CHUA_RANG`, `ChuaRangError` mang `ma_loi`
(cùng khuôn `giong_noi.GiongKhongHopLe`), `thi_hanh` đổ vào `stage.outputs`, và
`quan_sat.LOI_CO_MA` **mượn lại chính bảng đó** — một bản của câu, không hai.
`LOI_CO_MA` cũng ẩn nút thử lại, nên câu trả lời đúng (*tự chọn một giọng*) là
việc duy nhất còn lại trên màn hình.

---

## 5. Đã kiểm trong trình duyệt thật (Playwright, `CLAUDE.md` luật 7)

Bản dev cô lập `tools/asv_browser_server.py`, cổng 8199 (⛔ không đụng 8100
production, không deploy).

| phép | 1280 px | 375 px |
|---|---|---|
| console errors | 0 | 0 |
| failed network requests | 0 | 0 |
| tràn ngang (`scrollWidth` vs `clientWidth`) | 1265 = 1265 | 360 = 360 |
| focus ring ô mới | `solid 2px` nhìn thấy | — |

Luồng đã tái hiện trên giao diện thật:

1. chọn video → giá ước hiện (`~5–6 credit`);
2. đổi **Lồng tiếng sang** `vi → en`: danh sách giọng `20 → 0`, câu đổi sang
   *"Chưa có giọng nào đọc được ngôn ngữ này…"*; lọc chặt ở `vi` thì ra câu
   *"…bỏ bớt điều kiện"* — **hai câu, hai tình huống**;
3. nộp thật (`zh → vi`, `nguon_loi=ocr`, `preset=smart_localize`, tốc độ 1,25×)
   → đọc thẳng CSDL: `nguon_loi: "ocr"`, `ngon_ngu_nguon: "zh"`,
   `bien_tap.toc_do: 1.25` **đều nằm trong `run.settings`**;
4. `?run_id=…` (*"Chạy lại với cài đặt này"*) nạp lại đủ ba ô mới;
5. màn một lần chạy với `outputs` gieo đúng hình dạng `tom_tat` của từng giai
   đoạn → khối bằng chứng hiện đủ bốn nhóm.

Ảnh: `bang_chung/gui/gui-studio-{1280,375}.png` ·
`bang_chung/gui/gui-bangchung-{1280,375}.png`.

---

## 6. Trần còn nguyên

| trần | chốt ở | trước | sau |
|---|---|---|---|
| `routes.py` | `test_423` (< 900 dòng / 30 handler) | 722 | **744** / 12 handler |
| module JS | `test_468` (≤ 320 dòng) | `giong.js` 210 | **`giong.js` 259** |

⛔ **Không thêm module JS mới.** Phép lọc theo làn là **mặt lọc thứ tư của cùng
một danh sách**; đặt nó ở một tệp riêng là hai người cùng ghi `option.hidden`
của một `<select>`, và họ sẽ đè nhau.

Phép duyệt vẫn ở **một** đường `dich_vu_tao.dung_cai_dat` — route HTML và cổng
nội bộ dùng chung, `test_2086` chốt cùng đầu vào cho cùng hồ sơ.

---

## 7. Phép kiểm mới (dải 2100–2119)

| tệp | hỏi gì |
|---|---|
| `test_2100_asv_gui_dieu_khien_ve_dich.py` (13) | ô có mặt · miền giá trị đến từ module · **giá trị khách chọn nằm trong hồ sơ đã lưu** · `nguon_loi` mặc định không ghi khoá thừa · bịa ra thì từ chối ở cửa · nạp lại cài đặt cũ · trần `routes.py` + JS · không câu tiếng Việt trong `.js` · `#asv-chu` giải được |
| `test_2101_asv_gui_bang_chung_chat_luong.py` (11) | bốn nhóm bằng chứng lên màn · không hiện khối rỗng · `khong_kha_dung` không bị đọc thành đã đạt · độ phủ là phần trăm · không lộ thứ của vận hành · ba mã `CHUA_RANG` có câu riêng và nằm trong bảng của màn khách · câu hiện ra **không kèm** nút thử lại |

### Hồi quy đã chạy (xanh toàn bộ)

| tệp | kết quả |
|---|---|
| `test_2100` · `test_2101` (mới) | 13 · 11 |
| `test_423` · `test_447` (route + GUI V4) | 35 |
| `test_468` (kiến trúc JS) · `test_2007` (ràng giọng) | 26 |
| `test_2000` (ngôn ngữ) · `test_2041` (nguồn lời) | 44 |
| `test_2025` (cảnh hỏng) · `test_2008` (auto-match hết chuỗi) | 37 |
| `test_420` (QC) | 25 |
| `test_2086` · `test_2087` (cổng nội bộ ngang route) | 23 |

⚠️ Chạy thành **từng mẻ 1–2 tệp** chứ không một mẻ 10 tệp: luật máy 23/09 cho
`chay_nang.py` giữ **cùng khoá `cpu_nhieu`** với `gate.py`, và khoá đang do phiên
`qc-hinh` giữ. Mẻ nhỏ nằm dưới ngưỡng "lệnh nặng" (≥ 3 tệp test) nên chạy được
ngay mà không chen hàng; lượt xếp hàng đã được **rút lại** sau khi đủ độ phủ, để
không giữ chỗ vô ích trong hàng đợi của máy.

⚠️ **Một phép đo đã phải bỏ chứ không sửa.** Bản đầu của
`test_CAU_hien_cho_khach_KHONG_nam_trong_js` hỏi *"có ký tự tiếng Việt không"*
và đánh hỏng `giong.js:khongDau()` — dòng `replace(/đ/g, "d")`, một ký tự tiếng
Việt dùng làm **dữ liệu của thuật toán**, không phải câu cho ai đọc. Phép đo
lệch về phía HÀNH ĐỘNG, nên nó bị thay bằng câu hỏi đúng: *"có CÂU tiếng Việt
không"* (dấu tiếng Việt **và** khoảng trắng trong cùng một chuỗi nguyên vẹn).

---

## 8. Còn lại / bàn giao

- **F-03 chưa đóng và nay NHÌN THẤY được.** Kho giọng chung chưa có giọng `en`
  nào lộ diện với ASV (cột `gioi` trống, chờ chủ dự án duyệt điền), nên chọn
  **Lồng tiếng sang: Tiếng Anh** cho danh sách rỗng kèm đúng câu giải thích.
  Giao diện nay nói ra sự thật đó ở cửa thay vì để khách phát hiện sau khi bấm
  Gửi. Khi 16/17 giọng được điền `gioi`, đường `en` tự sống — không phải sửa GUI.
- **Đường tải lên bền vững** (làn `tai-len`) đã nối sẵn trên trang thật: đủ
  `#asv-upload-id`, `#asv-tai`, `#asv-tai-thanh`, `#asv-tai-tt`, `#asv-tai-lai`,
  `data-tiep-tuc-tu`. Clip nghiệm thu của làn này (68 KB) đi đường multipart
  **theo đúng thiết kế**, nên băng chứng "tiếp tục từ x%" trên trình duyệt thật
  vẫn thuộc `test_2091`/`test_2092` chứ không phải làn `gui`.
- ⛔ **Không chạy `gate.py`** (điều phối chạy L1) và **không deploy**.
