# B1 — cổng NGHE CHÉP (`transcribe`)

> Làn `asvf-nghiem-thu-v2`, 24/09/2026. Mắt xích **đầu tiên** của thang cổng —
> mọi bước sau đứng trên văn bản nguồn nó tạo ra.

## ⚠️ ĐỌC TRƯỚC KHI ĐỌC BẤT KỲ CON SỐ NÀO Ở ĐÂY

**Bảng kết quả này BẤT ĐỐI XỨNG.** Chân lý nền là **hardsub**, và mọi sai lệch của
nó đều đẩy số sai **LÊN** (§2). Vì vậy:

| kết quả | kết luận được gì |
|---|---|
| **ĐẠT** | kết luận **ngay** — engine khớp cả một chân lý nền không hoàn hảo |
| **TRƯỢT** | ⛔ **chưa kết luận được gì** cho tới khi **soi tay** |

⛔ Một con số trượt **không** chứng minh engine sai. Người đọc trượt sẽ quy cho
engine — đó là lý do dòng này đứng ở đây chứ không nằm trong mục phương pháp.

## ⚠️ ĐƠN VỊ: `ti_le_don_vi_sai` KHÔNG phải WER

Đo 24/09, trên một dòng phụ đề Hán thật:

```
"深度解析跳伞慢了该怎么打"      -> jiwer thấy 1 "từ",  thật ra 12 KÝ TỰ
hai bản chép lệch ĐÚNG MỘT chữ -> tỉ lệ = 0,50   nhưng CER = 0,0417
```

`jiwer.wer` tách bằng **khoảng trắng**, và văn Hán **không có khoảng trắng** ⇒ mỗi
**dòng** thành một "từ". ⇒ Con số đó là **tỉ lệ DÒNG sai**, không phải WER.

⛔ Gọi nó là "WER" là **đặt tên rộng hơn thứ nó đo**, và người sau sẽ so nó với WER
của bảng xếp hạng thế giới — **hai thứ không cùng đơn vị**. Nên bản ghi luôn mang
`don_vi_ti_le` (`dong` | `tu`) cạnh con số, và đơn vị được xác định bằng **đếm chữ
Hán**, ⛔ không suy gián tiếp từ tỉ lệ ký tự/đơn vị (phép suy đó xếp nhầm cả
`"the quick brown fox jumps"` thành `dong`).

## ⚠️ GIỚI HẠN THỨ HAI: CER không phủ được MỐC THỜI GIAN

Sản phẩm là **lồng tiếng**. Một bản chép đúng **từng chữ** mà **sai mốc** cho CER đẹp
và tiếng **lệch môi** — tức hỏng ở đúng thứ khách mua.

`canh_chinh = "fallback_unaligned"` nghĩa là nhánh **căn chỉnh** không chạy; mốc thời
gian **không căn** đi thẳng vào `timing_align`, nơi quyết định mỗi câu rơi vào khe
nào. ⇒ **CER một mình không phủ được rủi ro này.** Bảng §4 phải đọc kèm cột `engine`
và `canh_chinh`.

⭐ Vì thế `fallback_unaligned` là **hạng A** (chủ dự án thu hẹp phạm vi 24/09), không
phải một ghi chú bên lề.

## 1b. ⛔ CÂU HỎI NGƯỠNG — đang chờ điều phối, KHÔNG tự quyết

`WER ≤ 0,25` ở §1 được viết cho một tỉ lệ **TỪ** sai. Trên văn Hán đơn vị là **DÒNG**
⇒ áp 0,25 cho nó là dùng một ngưỡng **chưa từng được hiệu chỉnh** cho đơn vị ấy: hai
dòng lệch một chữ đã cho 0,50.

⇒ Hiện tại `dat` **chỉ xét CER**; tỉ lệ dòng sai được **báo cáo nhưng không phán
xử**. ⛔ Đây **không phải** nới ngưỡng — ngưỡng CER giữ nguyên 0,12, và câu hỏi được
nêu **trước** khi đo phim nào.

## 1. NGƯỠNG — viết TRƯỚC khi đo, ⛔ không nới

```
ĐẠT khi:  WER ≤ 0,25  VÀ  CER ≤ 0,12
          trên ≥ 3 phim CÓ TIẾNG NÓI (món ăn · cắm trại · PUBG)
```

⛔ **Không đạt ⇒ sửa rồi đo lại. KHÔNG nới ngưỡng.** Nếu ngưỡng sai thì phải nói ra
là ngưỡng sai *trước* khi nhìn số, không phải sau.

**Vì sao mức đó.** CER đo được trước đây là **0,018** trên **1 clip 33 dòng** ở một
đường **KHÁC** (faster-whisper CPU, văn bản đối chiếu **tay**). Hardsub có thể **rút
gọn** so với lời nói, nên ngưỡng phải lỏng hơn số cũ — nhưng 0,25/0,12 vẫn là một
**ngưỡng**, không phải một mô tả.

⛔ **Phim súng hơi (`真人气枪游戏…`) KHÔNG dùng** — B0 ghi *"không chắc có giọng"*.
Một phim không có tiếng nói không đo được đường nghe chép, và đưa nó vào sẽ cho một
con số trông như thất bại của engine.

## 2. ⚠️ GIỚI HẠN CỦA CHÂN LÝ NỀN — đọc cùng lúc với mọi con số ở §4

Hardsub **không phải** bản ghi lời nói. Nó là **bản chữ do người làm phim viết**, và
nó có thể:

| | hệ quả lên WER |
|---|---|
| **rút gọn** lời nói (bỏ từ đệm, gộp câu) | WER **cao giả** — ASR chép đúng thứ người nói, hardsub không có |
| viết lại cho gọn màn hình | WER cao giả |
| bỏ hẳn đoạn không quan trọng | WER cao giả |
| sai chính tả / thiếu dấu | WER cao giả, **không** phải lỗi ASR |

⇒ **Mọi con số WER ở §4 phải đọc kèm dòng này.** Một WER 0,3 ở đây **không** chứng
minh ASR sai 30 % — nó nói *"ASR và hardsub khác nhau 30 %"*, và phần nào thuộc về ai
thì phép đo này **không tách được**.

⭐ Chiều lệch là **một phía**: các nguyên nhân trên đều đẩy WER **lên**. Nên một WER
**thấp** là bằng chứng mạnh (ASR khớp cả một chân lý nền không hoàn hảo); một WER
**cao** là bằng chứng **yếu**, và phải soi tay trước khi quy cho engine.

## 3. Cách chuẩn hoá trước khi so — ghi ra, ⛔ không để trong mã

`tools/bench_b1_chep_loi.chuan_hoa` — **bỏ HÌNH THỨC, giữ NỘI DUNG**:

| bỏ | giữ |
|---|---|
| dấu câu (`[^\w\s]`) | mọi chữ |
| khoảng trắng thừa | khoảng trắng **có nghĩa** (Latin) |
| khác biệt NFC/NFKC | |
| hoa/thường | |

⛔ **Không tự chế phép tách từ tiếng Trung.** Văn bản Hán không có khoảng trắng, nên
**WER theo "từ" trên tiếng Trung ít nghĩa hơn CER**. Cả hai đều được báo cáo, và
**CER mới là số đáng tin** ở đây. Một bộ tách từ tự chế sẽ tạo ra một đơn vị đo
không ai kiểm được — cùng họ với công thức Dice tự chế mà M-01 đã phải xoá.

⛔ **Không dùng OpenCC** (giản↔phồn): máy này **chưa cài** (`ModuleNotFoundError`),
và cài thêm một phép biến đổi **chưa đo** vào giữa chân lý nền là thêm một biến.
Nếu số cuối lệch vì giản/phồn thì việc đó phải hiện ra ở **soi tay**, rồi mới thêm.

### Đối chứng của chính bộ đo — ĐÃ CHẠY

```
giống hệt          WER 0,0000   CER 0,0000
làm hỏng 30 % từ   WER 0,2857   CER 0,2857     RESULT: PASS
```

⭐ Không có bước này thì một WER thấp có thể chỉ là **bộ đo hỏng**, và nó sẽ **im
lặng** cho mọi engine đạt (*"số 0 cần đối chứng"*).

## 4. Kết quả

*(điền sau Bước 4 — mỗi dòng kèm: engine thật, card có được cấp không)*

⚠️ Đọc cùng lúc với §2 (giới hạn chân lý nền) và mục *ĐƠN VỊ* ở đầu tệp.

| phim | CER | tỉ lệ đơn vị sai | đơn vị | số dòng nguồn | số dòng hardsub | engine | card |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 5. Phán quyết

*(điền sau Bước 6)*

## 6. ⚠️ Nếu bench hỏng: ghi TRIỆU CHỨNG trước, quy nguyên nhân sau

Đây là lượt **đầu tiên** đường `asr` chạy thật (Task 5 vừa đổi mặc định), nên xác
suất gặp một **tiền đề chưa khai** là cao.

⛔ **Đừng kết luận *"đường `asr` hỏng"*.** Lượt A ngày 24/09 là tiền lệ: một tiền đề
chưa ai khai (AUTO_MATCH đòi nguồn **có tiếng nói**) bị đọc thành *"AUTO_MATCH là
đường chết"*, và mất ba vòng mới tách ra được. Ghi đúng cái **thấy** — mã lỗi, giai
đoạn, số — rồi mới đi tìm **vì sao**.
