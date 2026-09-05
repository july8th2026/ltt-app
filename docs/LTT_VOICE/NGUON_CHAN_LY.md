# LTT VOICE — NGUỒN CHÂN LÝ

**Câu hỏi nào đọc ở đâu.** Tệp này chỉ chứa **con trỏ**, không chứa giá trị.

⛔ Một giá trị chép lại là một giá trị sẽ trôi. `CLAUDE.md` đã ghi lớp lỗi này ở
mục *"Hiện giờ cái gì đang sống"*: một bảng chép tay nói sai **năm lần**, và cả
năm đều về phía nguy hiểm. Đừng gõ một con số nào vào đây.

---

## Bảng tra

| Câu hỏi | Nguồn chuẩn | Loại bằng chứng |
|---|---|---|
| Trần ký tự của một **yêu cầu** / một **lượt sinh** | `apps/ltt_voice/tham_so_cong_khai.py` | hằng số + đo 03/09 |
| Bản đang chạy là bản nào | `GET /health/version` | hỏi máy chủ |
| Engine **làm được gì** (có nói tiếng Anh không) | `tools/do_engine_co_noi_tieng_anh.py` | **phép đo** ASR 01/09 |
| Sản phẩm **quyết định** thế nào về làn `vi`/`en` | `apps/ltt_voice/lan_ngon_ngu.py` | chốt của chủ sản phẩm 01/09 |
| Giọng mẫu dựng sẵn: có những gì | `apps/ltt_voice/giong_mau_engine.json` | **sinh ra**, đừng sửa tay |
| Giọng dùng chung: kho đang có gì | `dat_giong_dung_chung.ps1 -Xem` | hỏi CSDL (cần Admin) |
| Bảng tên kho cũ → tên hiển thị | `tools/nhap_kho_giong_cu.py::TEN` | soạn tay, 25 mục |
| Chất lượng từng giọng kho cũ | `tools/soi_kho_giong_cu.py` | DNSMOS + ASR |
| Giá / credit | `apps/ltt_voice/gia.py` | |
| Đường tài liệu dài | `apps/ltt_voice/ban_doc_dai.py` | |
| Cửa tải audio có nhận `Range` không | `apps/ltt_voice/routes/_p_audio.py` | ⚠️ **chưa** — đang sửa ở `phien/mobile-v1` |

---

## Bản đồ tài liệu — cái nào còn sống, cái nào là hồ sơ

⚠️ Sắp theo **ngày viết**, mới nhất trước. Khi hai tệp nói khác nhau, tệp mới
hơn thắng — trừ khi tệp cũ mang một **phép đo** mà tệp mới chỉ mang suy luận.

| Tệp | Ngày | Vai trò |
|---|---|---|
| `NGUON_CHAN_LY.md` | 05/09 | **chỉ mục này** — con trỏ, không giá trị |
| `KHO_GIONG/00_KIEM_KE.md` | 05/09 | kiểm kê 20 preset + 25 giọng dùng chung |
| `AUTONOMOUS_AUDIT/00..07` | 05/09 | lượt soát trần ký tự · dấu vân tay · giao diện |
| `03_TAI_LIEU_DAI.md` | 04/09 | ✅ **hợp đồng** đường tài liệu dài |
| `DECISIONS.md` | 01/09 | các quyết định đã chốt |
| `01_KHOA_UPSTREAM.md` | 30/08 | ✅ **phép đo** engine — vẫn đúng, số đo không cũ |
| `02_QUY_TRINH_TRIEN_KHAI.md` | 30/08 | quy trình |
| `00_PHUONG_AN_VA_LO_TRINH.md` | 31/08 | ⛔ **hồ sơ** — đã gắn biển |
| `VOICE_UI_EXECUTION_PLAN.md` | 31/08 | ⛔ **hồ sơ** — đã gắn biển |
| `AUTONOMOUS_RUN/*` | 31/08 | ⛔ **nhật ký lượt chạy**, không phải hợp đồng |

⭐ Hai tệp `⛔` **không bị sửa bên trong**. Chúng ghi *"lúc ấy ta nghĩ gì"*, và
giá trị ấy mất sạch nếu sửa số cho khớp hiện tại. Chúng chỉ được gắn một biển ở
đầu nói rõ chúng là hồ sơ.

⚠️ `01_KHOA_UPSTREAM.md` cũ nhất bảng nhưng **không** bị gắn biển: nó chứa số
đo (VRAM, RTF, ngưỡng trôi giọng), và một phép đo không cũ đi vì lịch — nó chỉ
cũ đi khi có phép đo mới bác bỏ nó. Chưa có.

---

## 🔴 NĂM KHẲNG ĐỊNH KHÔNG CÒN ĐÚNG — đừng dựng lại chúng

Bốn cái đầu (①–④) **nghe rất thuyết phục** khi mới đọc, và cả bốn đều sai **ngay
từ lúc viết**. Ghi ra vì một phiên sau đọc phải bản cũ sẽ đi "sửa" những thứ vốn
đúng — và sẽ làm vậy một cách tự tin, vì đoạn văn ấy tự xưng là kết quả phân tích.

⚠️ Cái thứ năm (⑤) **khác loại**, và để chung ở đây là có chủ ý: nó **đúng lúc
viết** rồi mới thành sai khi hệ thống đổi. Hai loại này cần hai cách phòng khác
nhau — ①–④ cần *đo trước khi khẳng định*, còn ⑤ cần *quét lại chú thích khi sửa
thứ mà chú thích đang mô tả*. Nhưng hậu quả thì giống hệt: người sau đọc một câu
tự tin và suy tiếp từ nó.

### ① *"Engine không nói được tiếng Anh"* — SAI

**Đã tin hai lần trong cùng một phiên.** Dẫn chứng nghe rất chắc:
`vieneu_utils/phonemize_text.py` ghim `SEAPipeline(lang="vi")` + `G2P(lang="vi")`;
`sea_g2p/g2p.py` khai `SUPPORTED_LANGS = ("vi", "th", "id")` — **không có `en`**.

Bác bỏ trong **năm phút** bằng cách bắt engine đọc thử:

    VAO : The quick brown fox jumps over the lazy dog.
    ASR : The quick brown fox jumps over the lazy dog.       [en 0,996]

`lang` chọn **ngôn ngữ nền Đông Nam Á**, không phải danh sách ngôn ngữ đầu ra;
chuỗi Latin đi qua một engine tiếng Anh dùng chung bên trong cả ba.

⚠️ Câu sai này sống sót **một giờ sau khi bị bác bỏ** — bản bác bỏ commit lúc
12:25, `soi_kho_giong_cu.py` sửa lúc 13:25 mà không ai quét lại. Nó còn được
trích lại lần nữa ngày **05/09**, bởi tôi. Dọn 05/09.

→ `tools/do_engine_co_noi_tieng_anh.py`

### ② *"Nhãn `lang` của kho cũ không đáng tin"* — SAI

`voice_profiles.yaml` ghi `lang: en` cho những cái tên tiếng Việt rành mạch
(`hoathinh_female`, `meoquan_men`, `tamlyhoc_men`) ⇒ kết luận `lang` hẳn có
nghĩa khác.

Bác bỏ: kho cũ xây bằng **F5-TTS cho giọng Việt, XTTS cho giọng Anh**. ASR khớp
**24/24**, độ tin 0,987–1,000. Cái tên tiếng Việt trên một giọng nói tiếng Anh
không phải mâu thuẫn — nó là tên **kênh/nhân vật**, không phải tên người nói.

⭐ Lỗi thật: đọc **tên** như dữ liệu và bỏ qua cột `engine` — cột duy nhất mang
câu trả lời.

→ `tools/soi_kho_giong_cu.py`

### ③ *"Kho cũ có 24 giọng"* — SAI, có **25**

`kyan_nam` có ba clip ở 24000/24000/**22050** Hz, và bộ nối **từ chối cả giọng**
vì hai tần số khác nhau. Nó biến mất sau một dòng `BO:` giữa hai mươi lăm dòng.
Con số 24 đã được báo cho chủ sản phẩm.

⭐ Bài học của `_noi_kho`: *"từ chối là đúng khi việc **không làm được**; ở đây
nó làm được. Một cái chốt đúng đặt sai chỗ vẫn là một cái chốt sai, và nó hỏng
theo kiểu tệ nhất: **im lặng về phía thiếu**."*

⚠️ `tmp/kho_giong_cu.json` vẫn là artefact **trước** bản sửa (24 mục, ghi 07:00
ngày 01/09). Đừng đọc nó thành trạng thái kho.

### ④ *"Chỉ 3 giọng được nhập vào kho chung"* — SAI, **25**

Đọc `tmp/nhap_kho_giong_cu.json` (3 mục) rồi kết luận. Tệp ấy là artefact của
một lượt chạy lúc 07:00; commit thật lúc 13:25 nhập **4 → 25**.

⛔ Một tệp trong `tmp/` không phải trạng thái hệ thống, và nó **không có cách
nào tự nói rằng nó đã cũ**.

→ commit `7de8a461`

### ⑤ *"`/audio` không nhận `Range`"* — ĐÚNG lúc viết, SAI từ **05/09**

Chú thích ở `server/static/voice.js` (trên `veSong`) từng ghi: *"`/audio` trả
`StreamingResponse` nên KHÔNG có `Content-Length`, và nó cũng không nhận
`Range`"*. Cả hai vế đều đúng ở thời điểm viết.

⭐ Nhưng vế thứ hai không chỉ là một chi tiết kỹ thuật — **nó chính là một nửa
của bug P0 mobile**: Safari/WebKit quyết định một nguồn âm thanh có tua được hay
không từ chính lượt 200 đầu tiên; không thấy `Accept-Ranges` thì nó bỏ phát,
trong khi `<a download>` vẫn tải bình thường. Đó đúng là hình dạng lỗi người
dùng báo — *"tải về được nhưng bấm Play trên điện thoại không chạy"*.

Từ 05/09 `/audio` đi qua `platform_core.phat_media`: khai `Accept-Ranges`, trả
`Content-Length` ở lượt 200, `206` cho dải hợp lệ, `416` cho dải vô nghĩa.
Đo trên máy chủ: `bytes=0-99` → `206 bytes 0-99/401324`.

⚠️ Dòng mã dùng `au.duration` **vẫn đúng** — nó chưa bao giờ phụ thuộc vào
`Content-Length`. Một lý do sai vẫn có thể dẫn tới một quyết định đúng, và khi
ấy thứ phải sửa là **lý do**, không phải dòng mã.

→ `docs/MOBILE/02_BASELINE.md` §1a · commit `bec5643d` (phiên `phien/mobile-v1`)

---

## ⭐ MỘT HÌNH DẠNG CHUNG cho ①–④

    mot hang so / mot ten / mot tep doc rat thuyet phuc
      + mot tien de ngam chua ai kiem
      = mot ket luan sai, phat bieu voi giong cua mot phep do

Và cả bốn lần, thứ bác bỏ nó là **bắt hệ thống làm thử** — không phải đọc kỹ hơn.

⇒ **Luật:** một khẳng định về thứ hệ thống *làm được* hay *không làm được* phải
đến từ việc bắt nó làm. Đọc mã cho biết nó được **viết** thế nào, không cho biết
nó **chạy** ra sao.

⚠️ Và luật thứ hai, rút từ ca ①: **bác bỏ một câu chưa đủ — phải đi quét những
chỗ đã chép nó.** Một tài liệu sai đã bị bác bỏ mà không được dọn sẽ được trích
lại, và lần trích sau không mang theo lời bác bỏ.

⚠️ Luật thứ ba, rút từ ca ⑤ và **không suy ra được từ ①–④**: một chú thích mô tả
*hành vi hiện thời của một hệ con khác* là một khẳng định **có hạn dùng**. Nó
không sai lúc viết, nên không phép đo nào lúc viết bắt được nó. Thứ bắt được nó
là **người sửa hệ con ấy đi quét lại các chú thích mô tả nó** — nên việc đó phải
nằm trong cùng commit với bản sửa, không phải trong một lượt dọn dẹp về sau.

---

## ⚠️ MỘT CÂU SẮP THÀNH SAI — dọn khi `phien/mobile-v1` vào

`server/static/voice.js` (~dòng 849) ghi: *"`/audio` trả `StreamingResponse` nên
không có `Content-Length`, và nó cũng **không nhận `Range`**."*

Hôm nay câu ấy **đúng** (`grep -c "Range" _p_audio.py` → 0). Nhánh
`phien/mobile-v1` đang thêm `Range` — vì thiếu nó thì Safari/WebKit **từ chối
phát**, đó là root cause của *"tải về được nhưng bấm Play trên mobile không
chạy"*. Khi bản ấy vào, câu trên hết đúng và phải dọn.

⭐ Ghi ra đây **trước** khi nó sai, vì mục ① dưới đây đã cho thấy hình dạng của
   việc không làm thế: một câu bị bác bỏ mà không ai quét lại sẽ được trích lại,
   và lần trích sau không mang theo lời bác bỏ.

## Quy ước cho tài liệu Voice về sau

1. **Con trỏ, không phải giá trị.** Thấy một con số trong `.md` thì hỏi: nó có
   trong mã không? Nếu có, xoá nó khỏi `.md` và trỏ vào mã.
2. **Ghi lại thứ ĐO ĐƯỢC, đừng ghi cách giải thích nó.** Số liệu 24/24 ở ca ②
   đúng từ đầu; chỉ câu kết luận cạnh nó là sai.
3. **Bác bỏ thì để lại, đừng xoá** — kèm ngày và bằng chứng. Xoá thì người sau
   sẽ suy ra lại đúng kết luận sai ấy, và không có gì chặn họ.
4. **Artefact trong `tmp/` không phải trạng thái.** Ghi ngày khi trích nó.
5. Tệp này là **chỉ mục**. Thêm một tài liệu Voice mới thì thêm một dòng ở đây,
   hoặc nói rõ nó thay thế tài liệu nào.
