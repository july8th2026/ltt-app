# 00 — KIỂM KÊ KHO GIỌNG (2026-09-05)

## ⛔ KẾT LUẬN TRƯỚC: việc được yêu cầu **phần lớn đã làm xong** ngày 01/09

Yêu cầu giả định có 20–100 giọng tên không chuẩn cần một hệ thống tự phân loại
và đặt tên lại. Đo thật thì hệ thống ấy **đã được xây và đã chạy** — commit
`7de8a461` (01/09/2026), ngay trên nhánh này:

    Kho chung: 4 -> 25 giong (8 VI + 17 EN).
    Cong bo chon giong nay co 45 lua chon:
      20 preset cua model + 25 giong nhan ban.

Và nó **đang sống trên production**: bản deploy khớp `master` từng byte ở cả bốn
tệp đối chứng, `master` chứa cột `dung_chung` + migration `20260901_0200`, nên
25 giọng dùng chung hiện ra với khách thật ngay hôm nay.

| kho | số | tên | metadata | trạng thái |
|---|---|---|---|---|
| Preset engine | **20** | *Mai Anh, Minh Đức, Ngọc Huyền…* | giới/vùng/phong cách, **sinh ra** từ engine | ✅ không cần curate |
| Giọng dùng chung (từ kho cũ) | **25** | *"Lily — nữ, tự nhiên"* … | giới, làn, xuất xứ sha256 | ✅ đã curate 01/09 |
| **Tổng bộ chọn giọng** | **45** | | | ✅ **đang sống** |

⇒ Xây một bộ sinh tên tự động bây giờ là làm lại một việc đã xong — và làm tệ
hơn, vì bảng tay (`tools/nhap_kho_giong_cu.py::TEN`) giữ được tên kênh/nhân vật
mà chủ sản phẩm đã quen (`hoathinh_female` → *"Hoạt Hình — nữ, hoạt hình"*).

## 🔴 HAI KẾT LUẬN CỦA CHÍNH TÔI ĐÃ BỊ BÁC BỎ TRONG LƯỢT NÀY

Ghi lại vì cả hai đều **nghe rất hợp lý** và cả hai đều sai — và một phiên sau
đọc bản nháp cũ sẽ đi sửa những thứ vốn đúng.

### ① *"Chỉ 3 giọng được nhập"* — SAI

Tôi đọc `tmp/nhap_kho_giong_cu.json` (3 mục) và kết luận kho chỉ có 3 giọng. Tệp
ấy là artefact của **một lượt chạy**, ghi lúc 07:00 ngày 01/09; commit thật lúc
13:25 cùng ngày nhập **25**.

⛔ Bài học: một tệp trong `tmp/` không phải trạng thái hệ thống. Nó là ảnh chụp
   của một lượt chạy, và nó **không có cách nào tự nói rằng nó đã cũ**.

### ② *"Engine mới không nói được tiếng Anh"* — SAI

Tôi trích docstring của `tools/soi_kho_giong_cu.py`: `phonemize_text.py` ghim
`SEAPipeline(lang="vi")` + `G2P(lang="vi")` ⇒ suy ra 17 giọng XTTS chỉ dùng được
làm nguồn âm sắc. Tôi đã kiểm: **mã đúng là ghim `vi`** (cả hai bản venv).

Nhưng `apps/ltt_voice/lan_ngon_ngu.py` có một **phép đo** ngày 01/09:

    VAO : The quick brown fox jumps over the lazy dog.
    ASR : The quick brown fox jumps over the lazy dog.       [en 0,996]

⭐ Quan sát đúng, **suy luận từ nó thì sai**. G2P cấu hình tiếng Việt không có
   nghĩa là model không đọc được tiếng Anh — model được train song ngữ (~10.000
   giờ En–Vi, có code-switching trong cùng một câu). Phép đo thắng phép đọc mã.

⇒ Làn `en` **không phải một lời hứa hão**. Nó là một **chốt chất lượng** do chủ
  sản phẩm đặt (clip nguồn Việt phục vụ văn bản Việt), và nó **cảnh báo chứ
  không chặn** — vì tiếng Việt viết không dấu không phân biệt được với tiếng Anh
  bằng bảng mã, nên một cổng chặn sẽ từ chối việc hợp lệ của khách.

## Kiểm kê 25 giọng kho cũ — ĐO THẬT

Hai nguồn: `tmp/kho_giong_cu.json` (DNSMOS + ASR, lượt có GPU) và một lượt đo
mới trong phiên này cho F0 / nhịp / im lặng / clipping (numpy thuần, không GPU,
chạy được trong lúc cổng chất lượng chiếm máy).

⚠️ `tmp/kho_giong_cu.json` có **24** mục, không phải 25 — nó ghi lúc 07:00, tức
**trước** bản sửa `_noi_kho` cùng ngày. Trước bản sửa, `kyan_nam` (ba clip ở
24000/24000/**22050** Hz) bị bộ nối **từ chối cả giọng** vì hai tần số khác
nhau, và nó biến mất sau một dòng `BO:` giữa hai mươi lăm dòng khác.

⭐ Chú thích của `_noi_kho` nay ghi lại đúng bài học ấy, và nó đáng chép ra đây:
   *"từ chối là đúng khi việc **không làm được**; ở đây nó làm được — chuyển tần
   số là một phép chuẩn. Một cái chốt đúng đặt sai chỗ vẫn là một cái chốt sai,
   và nó hỏng theo kiểu tệ nhất: **im lặng về phía thiếu**."*

### Phân bố

    engine   f5tts 8 (lan vi)      xtts 17 (lan en)
    ASR      khop 25/25 voi engine — khong mot ngoai le
    gioi     nam 16                nu 8   (+1 dang tranh cai, xem duoi)
    clipping 0,000 o CA 25         muc thu -17,8 .. -23,2 dBFS

⭐ Kho cũ đã chuẩn hoá tử tế. Không giọng nào clipping, mức thu rất đều — phần
tín hiệu dùng lại được nguyên.

### ⚠️ VIỆC CÒN LẠI 1 — một nhãn giới tính lệch hẳn số đo, và nó ĐANG SỐNG

F0 trung vị tách hai nhóm rất sạch (nam 88–166 Hz, nữ 171–276 Hz, ranh giới tự
nhiên ≈ **168 Hz**). 23/25 nhãn khớp. Hai ca không:

| giọng | nhãn | F0 trung vị | dải F0 | DNSMOS | |
|---|---|---|---|---|---|
| `khanh_male_entertainment` | **nam** | **220,2 Hz** | 173,8 *(rộng nhất kho)* | **2,971** *(thấp nhất kho)* | 🔴 |
| `phatgiao_nu` | nữ | 171,4 Hz | 92,3 | 3,215 | ⚠️ sát ranh |

⛔ KHÔNG kết luận "nhãn sai". Ba giải thích đều vừa khít với dữ liệu, và chúng
dẫn tới ba hành động khác nhau:

  · giọng nhân vật / giả thanh — tên có `entertainment`, rất hợp lý;
  · nhãn kho cũ sai;
  · **F0 đo sai** — bộ đo dùng tự tương quan, nó nhảy quãng tám ở giọng dải
    rộng, mà đây đúng là giọng dải rộng nhất kho.

⚠️ Và giả thuyết thứ ba tự nghi ngờ chính phép đo của tôi. Ba giả thuyết + điểm
   chất lượng thấp nhất kho ⇒ **nghe bằng tai**, không tự sửa nhãn. Đây đúng là
   ca mà mục 16 của yêu cầu gọi là *confidence thấp → người duyệt*.

### ⚠️ VIỆC CÒN LẠI 2 — chưa có tầng chất lượng, và giọng yếu đang bày ra

Mục 10 của yêu cầu đòi phân `RECOMMENDED / GOOD / REVIEW / HIDE`. Hôm nay
**không có cơ chế nào**: `dung_chung` là một cột `bool`, bật là hiện.

Năm giọng đáng xem lại, và cả năm **đang hiện cho khách**:

| giọng | vấn đề | số đo |
|---|---|---|
| `khanh_male_entertainment` | DNSMOS thấp nhất kho | 2,971 |
| `bella_nu` | DNSMOS thấp | 3,184 |
| `lego_nu` | DNSMOS thấp | 3,188 |
| `nguyetnga_nu` | **hơn nửa clip là im lặng** | im 0,562 |
| `kinhte_nam` | im lặng cao | im 0,458 |

⚠️ "DNSMOS thấp" ở đây là **thấp so với chính kho này** (2,97–3,55 — dải rất
   hẹp), không phải thấp tuyệt đối. Đừng đọc 3,184 thành "giọng hỏng".

### ⚠️ VIỆC CÒN LẠI 3 — chưa dò trùng lặp

Mục 11 (ma trận tương đồng bằng speaker embedding) **chưa chạy**. Hạ tầng có sẵn
— `ghi_danh` của sidecar trả embedding, và `chon_doan` đã dùng nó — nhưng nó cần
GPU, và `cua_so_yen.py` báo `[cpu_nhieu]` suốt phiên này vì cổng chất lượng đang
chạy. `CLAUDE.md` cấm chồng lệnh nặng.

⚠️ Có một lý do nghi ngờ trùng lặp là **có thật**, không phải phòng xa: kho cũ
   phục vụ nhiều kênh, và bốn cái tên `meoquan_men` / `meodang_men` / `ht3d_men`
   / `hoathinh_female` cùng thuộc nhóm hoạt hình. Hai giọng đầu chênh F0 63 Hz
   (91,3 vs 154,2) nên **không** phải một người — nhưng đó là suy luận từ một
   chỉ số, không phải một phép đo tương đồng.

## Kiến trúc danh tính — một ràng buộc TIỀM ẨN, chưa đau

`giong_mau.py` gộp bốn khái niệm vào một chuỗi:

    GiongMau.ma  ==  engine preset key   (di thang vao `infer(voice=...)`)
                 ==  public_id           (hop dong API: preset="Adam")
                 ==  ten_hien_thi        (thu khach nhin thay)

Đây đúng là coupling mục 1 của yêu cầu cảnh báo. Nhưng nó **chưa gây đau**: 20
cái tên ấy vốn đã đẹp, chưa ai muốn đổi cái nào.

⛔ Nên **không tách bây giờ** — mục 22 của chính yêu cầu nói thế: *"KHÔNG
   migration chỉ vì architecture đẹp."*

⭐ Ghi bản sửa lại để ngày cần không phải nghĩ lại: thêm `giong_mau_catalog.json`
   (người soạn) và cho `ten_hien_thi` đọc nó; `ma` giữ nguyên ⇒ `public_id` giữ
   nguyên ⇒ **API không đổi một chữ**. Đó là phương án A của mục 2, và nó **cộng
   thêm** chứ không migrate.

⚠️ Ngược lại, `VoiceProfile` (giọng nhân bản + dùng chung) **đã có kiến trúc
   đúng** từ đầu: `public_id` (`vc_<32 hex>`) tách hẳn `ten_hien_thi`. Đổi tên
   hiển thị một giọng dùng chung hôm nay đã an toàn sẵn — không cần xây gì.

## Cái KHÔNG xây, và điều kiện để nó đáng xây

| yêu cầu | không xây vì | đáng xây khi |
|---|---|---|
| bộ sinh tên tự động (§12–13) | bảng tay đã có, đủ 25, đã áp | kho vượt ~100 giọng |
| classifier vùng miền (§8) | 20 preset đã có `vung` sinh từ engine; 25 giọng kho cũ không có dữ liệu vùng | nhận giọng từ khách ngoài |
| tách `catalog_id` / alias (§1) | chưa có tên nào cần đổi | lần đầu phải đổi một tên preset |
| màn duyệt admin (§17) | 25 dòng thì một bảng markdown rẻ hơn một màn hình | kho vượt ~50 giọng |
| chống ghi đè curated (§20) | snapshot engine hôm nay **không có** trường curated nào | thêm trường curated đầu tiên |

⭐ Không thứ nào bị loại vì khó. Chúng bị loại vì hôm nay chưa có vấn đề mà
chúng giải — và mỗi dòng kèm điều kiện để người sau biết khi nào thì có.

## Đề nghị

Ba việc, nhỏ, theo thứ tự giá trị:

1. **Nghe `khanh_male_entertainment`** rồi chốt nhãn giới tính. Một câu trả lời
   của tai người đóng lại ba giả thuyết mà không phép đo nào của tôi đóng được.
2. **Quyết có cần tầng chất lượng không.** Nếu có, nó là một cột `xep_hang` trên
   `VoiceProfile` + một bộ lọc — nhỏ. Nếu không, ghi ra rằng "bật `dung_chung`
   tức là đã duyệt", để lần sau không ai đi tìm cơ chế không tồn tại.
3. **Chạy dò trùng lặp** khi GPU rảnh — nó là lượt đo duy nhất còn thiếu.
