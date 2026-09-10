# DECISIONS — LTT VOICE

Sổ quyết định kỹ thuật của hạng mục LTT VOICE. Cùng khuôn với
`docs/ANH_NOI_BO/DECISIONS.md`:

```
Decision:
Reason:
Alternatives considered:
Trade-off:
Date:
```

**Quan hệ với `docs/QUYET_DINH_NEN_TANG.md`:** file kia giữ quyết định **nền
tảng** (Q117–Q119 là quyết định nền của LTT VOICE). File này giữ quyết định
**kỹ thuật cấp thi hành** — chọn ngưỡng, chọn cách đo, chọn bỏ một pha. Khi một
quyết định ở đây đủ lớn để ràng buộc cả nền tảng, nó phải được nâng thành một
số Q.

**Quy tắc:** một quyết định chưa ghi vào đây thì coi như chưa có. Đổi quyết định
cũ thì **không xoá** — thêm mục mới và ghi `Thay: DV-xxx`.

---

## DV-001 — K0: F5 tinh chỉnh thắng VieNeu zero-shot, nhưng thắng NHỎ

**Decision:** Ghi nhận kết quả so hai hệ. **Chưa quyết K5** — mục DV-002 mới là
quyết định về K5.

**Reason:** Kế hoạch kế thừa khai K0 là pha *"chặn mọi pha sau"*, với điều kiện
qua: ≥ 40 cặp và khoảng tin cậy không chứa 0,5. Đã chạy đúng **40 cặp**
(8 giọng f5tts × 5 câu), cùng người nói, cùng câu.

**Bộ chấm TRUNG LẬP** — không trục nào đi qua bộ mã hoá người nói của bên nào,
vì dùng bộ của VieNeu là hỏi *"VieNeu có nghĩ bản của VieNeu giống người nói
không"* và nó tối ưu đúng thứ ấy:

| trục | công cụ | F5 | VieNeu | hoà | tỉ lệ VieNeu | KTC 95% |
|---|---|---|---|---|---|---|
| dễ hiểu (CER) | Whisper | 11 | 6 | **23** | 0,353 | [0,173; 0,587] |
| chất lượng cảm nhận | DNSMOS P.835 | **31** | 9 | 0 | 0,225 | [0,123; 0,375] |
| trung thành độ sáng | \|lệch\| vs clip gốc | **30** | 10 | 0 | 0,250 | [0,142; 0,402] |
| trung thành cao độ | \|lệch\| vs clip gốc | 19 | 18 | 2 | 0,486 | [0,334; 0,641] |

Hai trục giữa có KTC **không chứa 0,5** ⇒ đã phân thắng bại. Hai trục còn lại
thì không.

🔴 **NHƯNG ĐỘ LỚN MỚI LÀ PHẦN QUAN TRỌNG, VÀ NÓ NGƯỢC VỚI ẤN TƯỢNG TỪ TỈ LỆ
31–9:**

    khoang cach DNSMOS giua hai he                        0,143
    do lech giua HAI LUOT SINH BINH THUONG cua CUNG giong 0,257

Khoảng cách giữa hai **hệ** nhỏ hơn nhiễu giữa hai **lượt** của cùng một hệ —
**0,56σ**. Một người nghe so *một* clip F5 với *một* clip VieNeu sẽ thường
xuyên chọn VieNeu; chỉ qua 40 cặp thì chiều mới rõ.

⭐ Đúng hình dạng đã gặp ở dự án ảnh (`docs/ANH_NOI_BO/DECISIONS.md` D-054):
   *"khác biệt nhỏ hơn khác biệt giữa hai seed — đừng đọc thành '36 bước tệ
   rõ'"*. Cùng bài học, cùng dự án, hai hạng mục khác nhau.

⭐ Và trục **dễ hiểu** — trục quyết định khách có **dùng được** bản đọc hay
   không — thì **23/40 cặp hoà ở CER 0**, tức cả hai đọc đúng hoàn toàn. F5
   không mua thêm gì ở chỗ đó.

**Alternatives considered:**

- *Chấm bằng cosine embedding người nói.* Bỏ: mỗi hệ có bộ mã hoá riêng, và
  dùng bộ nào cũng thiên vị bên ấy. Đây chính là lý do tầng lệch-tham-chiếu của
  K4 đáng dựng — một phép đo **độc lập với embedding** là cách duy nhất chấm
  công bằng hai hệ dùng hai bộ mã hoá khác nhau.
- *Chấm mù bằng người.* Hoãn: D-052 của dự án ảnh đã chuyển sang máy chấm, và
  điều kiện "mỗi phiếu quyết đoán phải viết lý do" khó áp cho 40 cặp tiếng nói
  trong một phiên. Nếu DV-002 bị phản bác thì đây là bước tiếp.
- *Gộp bốn trục thành một điểm tổng.* Bỏ: bốn trục nói bốn điều khác nhau, và
  "F5 bóng bẩy hơn nhưng dễ hiểu ngang nhau" là **chính** thông tin cần để
  quyết K5. Gộp lại là vứt nó đi.

**Trade-off:** Bộ chấm đo được *dễ hiểu · sạch · trung thành âm học*. Nó **không**
đo được **giống người nói tới mức nào theo tai người** — thứ mà một khách nhân
bản giọng quan tâm nhất. Đó là khoảng trống thật của DV-001, và nó chỉ lấp được
bằng nghe mù có người.

⚠️ Một confound đã bị loại **bằng số đo, không bằng lập luận**: hai hệ chạy ở
   hai tần số (F5 24 kHz, VieNeu 48 kHz), nên VieNeu phải qua **một bước hạ tần
   số thừa** trước khi chấm (48→24→16 so với 24→16). Đo lại chính 40 tệp ấy ở
   cả hai đường: chênh lệch DNSMOS **đúng 0,0000** trên cả 40. Bước ấy không ăn
   mất gì. (`tools/k0_kiem_chung_resample.py`)

**Date:** 2026-09-01

---

## DV-002 — KHÔNG mang đường huấn luyện sang. K5 bị gỡ khỏi kế hoạch.

**Decision:** Không port ~7.800 dòng đường huấn luyện của hệ cũ. K5 gỡ khỏi lộ
trình. Nhân bản giọng ở hệ mới **giữ nguyên zero-shot**.

**Reason:** DV-001 đo được khoảng cách, và khoảng cách ấy **không mua nổi cái
giá**:

- Trục **dễ hiểu**: hoà (23/40 cặp hoà ở CER 0). F5 không mua thêm gì.
- Trục **bóng bẩy**: F5 thắng, nhưng **0,143 điểm DNSMOS** — nhỏ hơn nhiễu giữa
  hai lượt sinh của cùng một giọng (0,257).
- Cái giá: F5 cần **một lượt huấn luyện cho MỖI giọng**, một checkpoint
  `model_ft.pt` cho mỗi giọng, và ~7.800 dòng mã.

⭐ Nhưng lý do quyết định **không phải cái giá kỹ thuật, mà là hình dạng sản
   phẩm.** Hệ mới bán *"tải lên 8 giây, có ngay giọng của bạn"*. Với F5 thì mỗi
   giọng khách tạo là một lượt huấn luyện GPU — đó **không phải cùng một sản
   phẩm**, nó là một sản phẩm khác mặc cùng một cái tên.

⭐ Và thiếu sót cụ thể của VieNeu **đã biết**: baseline K4 đo được bản sinh ra
   mất **-3,65 dB** trên 4 kHz so với clip nguồn — một khuyết tật của codec
   neural, có hướng cố định.

🔴 **SỬA 01/09, CÙNG NGÀY:** đoạn trên ban đầu viết tiếp *"một high-shelf ở khâu
   hậu kỳ đóng được một phần"*. **Đã đo, và điều đó SAI** — xem DV-004. Quyết
   định DV-002 vẫn đứng, nhưng nó đứng **mà không có đường vá rẻ nào**, và nói
   đúng như vậy quan trọng: một quyết định kèm một lời hứa chưa kiểm là một
   quyết định người sau sẽ tin nhầm.

**Alternatives considered:**

- *Giữ K5 cho riêng kho giọng dùng chung (25 giọng, không phải giọng khách).*
  Đáng cân nhắc và **chưa loại hẳn** — 25 giọng là một tập đóng, huấn luyện một
  lần. Nhưng nó cần một câu trả lời cho *"giọng của khách và giọng của nền tảng
  nghe khác chất lượng"*, và đó là một quyết định sản phẩm, không phải kỹ thuật.
  Ghi lại ở đây để không mất.
- *Chạy nghe mù có người trước khi quyết.* Đúng về nguyên tắc, nhưng nó chỉ đổi
  được quyết định này nếu tai người thấy một khoảng cách **lớn hơn nhiều** so
  với 0,56σ mà máy đo. Nếu ai đó muốn lật DV-002, đó là phép cần chạy.

**Trade-off:** Ta chấp nhận bản sinh ra **hơi tối và hơi đơn điệu hơn** clip
nguồn một cách hệ thống, đổi lấy nhân bản tức thì. Con số cụ thể đã ghi ở
`voice_sidecar/baseline_lech.json`, nên ngày ai đó muốn cãi lại thì có mốc.

**Date:** 2026-09-01

---

## DV-003 — Kho giọng tách làn theo ngôn ngữ của clip NGUỒN

> ⚠️ **Hàng tiếng Việt của bảng dưới ĐÃ ĐƯỢC KẾT LUẬN — xem DV-005.** Đo lại ở
> n=64 mỗi ô cho t = 3,03 và KTC [+0,0107; +0,0499] không chứa 0. Bảng trong
> mục này giữ nguyên vì nó là số liệu của lượt đo đầu.

**Decision:** `voice_profile.ngon_ngu` là **làn**: clip nguồn tiếng Việt phục vụ
văn bản tiếng Việt, clip nguồn tiếng Anh phục vụ văn bản tiếng Anh. Làn suy từ
`engine` của hệ cũ (`f5tts` → `vi`, `xtts` → `en`), **không** từ tên giọng.

**Reason:** Chủ sản phẩm chốt 01/09. Nó **không** phải ràng buộc kỹ thuật —
VieNeu song ngữ thật (`language: ["vi","en"]`, train from scratch trên ~10.000
giờ EN–VI; đo qua ASR thì nó đọc tiếng Anh đúng từng chữ, `[en 0,996]`). Nó là
một chốt **chất lượng**.

⚠️ **Và số liệu đo được nói nó đúng ở MỘT NỬA:**

| văn bản | nguồn VI | nguồn EN | |
|---|---|---|---|
| tiếng Việt | CER 0,0342 ±0,0407 | CER 0,0725 ±0,0689 | nguồn EN kém 2,1× ở trung bình, **chưa kết luận được** |
| tiếng Anh | CER 0,0208 ±0,0313 | CER 0,0198 ±0,0296 | **trùng khít** — làn chặt hơn cần thiết |

Bất đối xứng ấy đúng chiều vật lý: tiếng Việt có **thanh điệu**, tiếng Anh
không. Mượn âm sắc không-thanh-điệu để đọc tiếng Việt là chiều khó hơn.

**Trade-off:** Với văn bản tiếng Anh, luật đang **chặn một lựa chọn hợp lệ** của
khách mà không có bằng chứng nào đỡ. Chấp nhận vì nó đơn giản và nhất quán;
nếu đo thêm mà hàng tiếng Việt cũng hoà thì nên nới cả hai chiều.

⛔ Cảnh báo cho phiên sau: **đừng đoán làn từ TÊN giọng.** Kho cũ có
`hoathinh_female`, `meoquan_men`, `tamlyhoc_men`, `cg_huong_nam` — tên tiếng
Việt rành mạch, người nói **tiếng Anh**. Đó là tên kênh/nhân vật. Tôi đã đọc tên
như dữ liệu một lần và viết một kết luận sai vào tài liệu.

**Date:** 2026-09-01

---

## DV-004 — EQ sửa độ sáng KHÔNG đóng được khoảng cách. Kết quả âm.

**Decision:** Không đưa EQ sửa độ sáng vào đường sinh. Giữ mã và bộ đo lại như
**bằng chứng**, không như tính năng.

**Reason:** Hệ cũ đã gặp đúng bài này và giải nó —
`audio_postprocess._apply_clarity_eq_xtts` (2026-04-19), với docstring ghi rõ
*"Measured delta vs ref (17 speakers): air (8-16kHz) **-3,7 dB**"*. Ta đo
**-3,65 dB** cho VieNeu. Hai vocoder khác hẳn nhau, hai phép đo độc lập cách
nhau bốn tháng, cùng một cỡ khuyết tật — mọi codec neural đánh đổi dải cao
trước tiên, vì tai người ít nhạy ở đó nên hàm mất mát cũng ít phạt ở đó.

Nên hướng đi rất hợp lý. Đã dựng `voice_sidecar/eq_sua_sang.py` (biquad RBJ,
kẹp ±4 dB như hệ cũ) và quét sáu mức trên 12 bản K0:

| kệ cao @4 kHz | DNSMOS | CER | \|lệch sáng\| |
|---|---|---|---|
| 0,00 dB *(đối chứng)* | 3,0258 ±0,180 | 0,0202 | 7,905 |
| 1,00 dB | 3,0263 ±0,178 | 0,0221 | 7,028 |
| 2,00 dB | 3,0258 ±0,176 | 0,0220 | 6,137 |
| 3,65 dB | 3,0245 ±0,176 | 0,0202 | 4,822 |
| 4,00 dB | 3,0242 ±0,176 | 0,0220 | 4,618 |

⭐ `|lệch sáng|` giảm đẹp 7,9 → 4,6: **EQ làm đúng thứ nó hứa trên chỉ số phổ.**
   DNSMOS thì phẳng lì — dao động ±0,003 trên một độ lệch nội tại **0,180**.
   Không đổi gì cả.

🔴 **Vì sao:** codec neural **không suy giảm** dải cao, nó **không mã hoá** dải
   cao. Bù tuyến tính chỉ nâng phần còn lại — tức nâng cả phần dư nhiễu hình
   thành trong dải ấy — chứ không khôi phục thông tin đã bị vứt. DNSMOS nhìn
   xuyên qua điều đó; chỉ số phổ thì không.

⛔ Đây là đúng kiểu hỏng mà bộ đo sinh ra để bắt: **một con số đẹp lên trong khi
   tiếng không đổi.** Nếu chỉ nhìn `db_dai_cao` thì EQ trông như một thành công
   rõ ràng, và ta đã ship một tính năng không làm gì.

**Alternatives considered:**

- *Mở rộng băng thông bằng model học* (bandwidth extension). Đây mới là công cụ
  đúng cho việc khôi phục thông tin đã mất, và EQ tuyến tính thì không. Nhưng nó
  là một model nữa để nạp, chạy và bảo trì — cho một khoảng cách 0,56σ.
- *EQ theo TỪNG GIỌNG* như hệ cũ (`clarity_eq_gain_hi_db` khác nhau mỗi giọng).
  Không cứu được: bảng trên cho thấy DNSMOS phẳng ở **mọi** mức từ 0 đến 4 dB,
  nên chọn mức riêng cho từng giọng cũng chỉ là chọn giữa những mức đều không
  đổi gì.
- *Chấp nhận.* Đã chọn. Khoảng cách DNSMOS với F5 là 0,143 — **0,56 lần** độ
  lệch giữa hai lượt sinh của cùng một giọng (0,257).

**Trade-off:** Ta giữ một khuyết tật đo được và **không có đường vá rẻ**. Đổi
lại ta không ship một tính năng chỉ làm đẹp báo cáo. `eq_sua_sang.py` ở lại vì
ngày ai đó đề xuất lại ý này, bảng trên trả lời trong ba mươi giây.

**Date:** 2026-09-01

---

## DV-005 — Luật tách làn ĐÚNG cho tiếng Việt. Có bằng chứng. Bổ sung DV-003.

**Decision:** Giữ luật tách làn cho văn bản **tiếng Việt**. Với văn bản **tiếng
Anh** thì luật vẫn chưa có bằng chứng nào đỡ — xem Trade-off.

**Reason:** DV-003 ghi hàng tiếng Việt là *"chưa kết luận được"* ở n=16 mỗi ô.
Đo lại ở **n=64** mỗi ô (8 giọng mỗi làn × 4 câu × 2 lượt):

    nguon VI : CER 0,0342 ±0,0491   n=64
    nguon EN : CER 0,0645 ±0,0631   n=64
    chenh    : +0,0303   sai so chuan 0,0100   t = 3,03
    KTC 95%  : [+0,0107; +0,0499]   KHONG chua 0

⇒ Giọng nguồn tiếng Anh đọc tiếng Việt kém hơn **1,89×**, và khác biệt ấy
  **đã đủ bằng chứng**.

🔴 **Và một khuyết tật của chính bộ đo đã lộ ra ở đây.** Luật phán quyết bản đầu
   so chênh lệch giữa hai **trung bình** với **độ lệch thô** của từng lượt. Đó
   là sai loại: độ lệch thô **không giảm theo n**, nên tăng số phép đo bao
   nhiêu cũng không làm phép thử dễ qua hơn. Nó in "KHONG PHAN BIET" cho một
   khác biệt t=3,03.

   Đã sửa sang **sai số chuẩn của trung bình** — thứ giảm theo √n, tức phép thử
   **thưởng cho việc đo thêm**, đúng như nó nên làm.

**Trade-off:** Với văn bản tiếng Anh, hai làn vẫn trùng khít (0,0208 vs 0,0198,
n=16 mỗi ô). Luật đang **chặn một lựa chọn hợp lệ** ở chiều đó. Chấp nhận vì
tính nhất quán, nhưng nếu muốn nới thì chiều tiếng Anh là chiều nới được — và
nới nó cần đo lại hàng ấy ở n=64 để chắc.

**Date:** 2026-09-01

---

## DV-006 — Bản nhân bản kém biểu cảm 42%, và nguyên nhân nằm ở BỘ CHỌN của ta

**Decision:** Ghi nhận khuyết tật và cơ chế của nó. Quyết định sửa nằm ở
DV-007 (chờ số đo nhánh C).

**Reason:** Baseline K4 đo `delta_f0_tan_tuong_doi_ti_le = **−0,4556**` — bản
nhân bản chỉ giữ ~54% biến thiên cao độ của clip gốc, ở **mọi** bản khoẻ mạnh.
Đây là khuyết tật **lớn hơn độ tối** (−3,65 dB) về mặt tương đối, và nó là thứ
khách nghe ra: *giọng nhân bản đều đều hơn giọng thật*.

**Một confound đã loại bằng số đo, không bằng lập luận.** Clip tham chiếu là
~25 giây ghép từ 3–7 đoạn thu; bản sinh ra là một câu ~4 giây. Một bản ghép
nhiều đoạn đương nhiên có độ tản F0 lớn hơn. Đo riêng:

    A  do tan F0 cua CA clip tham chieu (~25s ghep)  : 0,2515
    B  do tan F0 tung DOAN ngan trong chinh clip ay  : 0,2519
    C  do tan F0 cua ban SINH RA                     : 0,1451

    gia cua DO DAI  (B so voi A)  :  +0,1%   <- gan nhu bang khong
    phan CON LAI    (C so voi B)  : -42,4%   <- chi phan nay noi ve nhan ban

⇒ Độ dài giải thích **0%**. Khuyết tật là thật.

⚠️ Nhưng bảng theo TỪNG GIỌNG cho giá-độ-dài dao động **−6,2% đến −54,4%**, chỉ
   triệt tiêu khi lấy trung bình. Nên một luật chấm **theo từng giọng** sẽ bị
   confound này bóp méo nặng — thêm một lý do R15 phải gỡ (xem `chan_doan.py`).

## 🔴 CƠ CHẾ TÔI VIẾT Ở ĐÂY ĐÃ BỊ BÁC — xem DV-007

> ⛔ Đoạn dưới đây suy ra một cơ chế (*"bộ chọn của ta chọn đoạn phẳng, model
> bám sát cửa sổ"*) từ **một cặp số của một lượt đo**. Phép thử ba nhánh chạy
> ngay sau đó **bác nó**: đổi độ biểu cảm của cửa sổ tham chiếu 1,4 lần thì đầu
> ra gần như không đổi, và còn đổi **sai chiều**.
>
> Giữ nguyên đoạn dưới thay vì xoá, vì nó ghi lại một cái bẫy đáng nhớ: hai con
> số xếp cạnh nhau (cửa sổ 0,1131 → đầu ra 0,1388) trông **y hệt** một quan hệ
> nhân quả, và tôi đã viết nó vào sổ quyết định như một cơ chế. Thứ phân biệt
> tương quan với nhân quả không phải là đọc kỹ hơn — mà là **can thiệp**: đổi
> cửa sổ rồi xem đầu ra có đi theo không.

## Cơ chế đã SUY RA (và đã bị bác)

    do tan F0 cua CA clip goc              0,2515
    do tan F0 cua CUA SO `chon_doan` chon  0,1131   <- phang hon clip 55%
    do tan F0 cua BAN SINH RA              0,1388   <- bam sat cua so, nhinh hon 23%

**Model không làm phẳng gì cả.** Nó tái tạo trung thành cửa sổ nó được đưa,
thậm chí nhỉnh hơn. Cửa sổ ta đưa cho nó **đã phẳng sẵn**.

Và cơ chế giải thích được chứ không phải trùng hợp: `chon_doan.chon()` xếp hạng
theo `cosine(emb(đoạn), emb(**cả clip**))`. Một đoạn đều đều nằm gần cái trung
bình ấy hơn — mọi đoạn có ngữ điệu mạnh đều kéo ra xa tâm. Nên **tối đa hoá độ
đại diện là chọn có hệ thống đoạn ít động nhất**, và không ai nhận ra vì tiêu
chí ấy nghe hiển nhiên đúng.

**Alternatives considered — ba đường đã thử và ĐỀU ÂM, trước khi tìm ra chỗ này:**

- *Tắt khử nhiễu tham chiếu* (đề nghị của chủ sản phẩm). Bộ khử nhiễu chỉ lấy
  đi **−0,095 dB** trên 25 clip — 2,6% của độ tối, và không liên quan biểu cảm.
- *EQ bù độ sáng* (kế thừa hệ cũ). Xem DV-004: `|lệch sáng|` giảm 7,9 → 4,6 mà
  DNSMOS **phẳng lì**.
- *Tăng `temperature`* (README upstream: *"Higher values add expressiveness"*).
  Quét 0,8 → 1,25: biểu cảm **không đi theo** (chênh lớn nhất +0,076 trên sai
  số 0,142, **t = 0,53**), trong khi CER ở 1,10 **tăng hơn gấp đôi** (t = 2,19).
  Lời hứa của upstream **không xác nhận được** trên trục này. Chốt K1 nổ 0% ở
  mọi mức, nên mất ổn định là loại tinh vi, không phải loại thô.

**Trade-off:** Ghi nhận này chưa sửa gì. Nó chỉ chuyển câu hỏi từ *"model có
khuyết tật"* sang *"bộ chọn của ta có khuyết tật"* — và câu thứ hai thì ta sửa
được, còn câu thứ nhất thì không.

⛔ Và một cảnh báo về cách đọc: hai lượt đo đầu của tôi dùng **tỉ lệ có mẫu số
   thay đổi** (đầu ra / cửa sổ), nên nhánh "đại diện" ra +0,227 còn nhánh "biểu
   cảm nhất" ra −0,345 và đọc lướt thì tưởng cái đầu thắng. Nhưng cửa sổ thứ
   hai vốn biểu cảm hơn **1,41×**. Quy về tuyệt đối mới thấy 0,1388 so với
   0,1042. **Câu hỏi luôn là "đầu ra biểu cảm bao nhiêu", và một tỉ lệ có mẫu
   số trôi không trả lời được câu đó.**

**Date:** 2026-09-01

---

## DV-007 — Model KHÔNG chuyển ngữ điệu từ cửa sổ tham chiếu. Giữ `chon_doan`.

**Decision:** Không đổi tiêu chí của `chon_doan.chon()`. Khuyết tật biểu cảm
−42% là **thuộc tính của model**, và không có đường sửa nào từ phía ta.

**Reason:** DV-006 suy ra rằng bộ chọn của ta chọn cửa sổ phẳng và model bám
sát cửa sổ ấy. Phép thử ba nhánh **can thiệp trực tiếp** vào giả thuyết đó —
cùng giọng, cùng câu, ba cửa sổ tham chiếu khác nhau:

    A. dai dien nhat        (tieu chi dang chay)
    B. bieu cam nhat        (trong nguong dai dien)
    C. dien hinh nhat       (do tan F0 gan trung vi cua clip)

| trục | A | B | C |
|---|---|---|---|
| biểu cảm **tuyệt đối** | **0,0995** ±0,0106 | 0,0764 ±0,0090 | 0,0922 ±0,0062 |
| danh tính | **0,7722** ±0,0120 | 0,7681 ±0,0150 | 0,7352 ±0,0164 |
| CER | 0,0399 | 0,0500 | **0,0396** |
| chốt K1 hỏng | 0% | 0% | 0% |

🔴 **Cửa sổ của ba nhánh chênh nhau tới 1,4× về độ tản F0, mà đầu ra chỉ dao
   động 0,076–0,100 — và nhánh có cửa sổ BIỂU CẢM NHẤT cho đầu ra PHẲNG NHẤT.**

⇒ Model **không chuyển tính cách ngữ điệu** từ cửa sổ tham chiếu. Nó trích
  **danh tính người nói** rồi tự sinh ngữ điệu của mình. Đó là hành vi hợp lý
  cho một kiến trúc nhúng speaker embedding, và nó giải thích vì sao ba đường
  trước cũng âm.

⭐ Và tiêu chí đang chạy **thắng cả hai trục**: biểu cảm cao nhất VÀ danh tính
   tốt nhất. Nhánh C đổi được +0,0003 CER nhưng mất **0,037 danh tính** (t≈1,8)
   — đổi thứ khách nghe ra lấy thứ khách không nghe ra.

**Alternatives considered:** bốn đường, tất cả đã đo và đều âm — tắt khử nhiễu
(2,6%) · EQ bù độ sáng (DNSMOS phẳng) · `temperature` (t=0,53) · chọn cửa sổ
(bác ở trên). Còn lại: đổi model, hoặc một bước hậu kỳ học được (không phải
tuyến tính). Cả hai đều lớn hơn nhiều so với một khoảng cách mà DV-001 đã đo là
**0,56σ** của nhiễu giữa hai lượt sinh.

**Trade-off:** Ta chấp nhận **giọng nhân bản đều đều hơn giọng thật ~42%**, và
nay biết chắc rằng không có núm nào ta xoay được. Đó là một câu trả lời kém vui
nhưng **đầy đủ** — bốn giả thuyết, bốn phép đo, bốn lần bác.

⛔ **Bài học phương pháp, đáng hơn kết quả.** DV-006 suy một cơ chế từ hai con
   số xếp cạnh nhau (cửa sổ 0,1131 → đầu ra 0,1388) và viết nó vào sổ quyết
   định như một sự thật. Nó trông y hệt nhân quả. Thứ phân biệt tương quan với
   nhân quả không phải đọc kỹ hơn mà là **CAN THIỆP** — đổi cửa sổ rồi xem đầu
   ra có đi theo không. Mất mười lăm phút, và nó lật ngược một kết luận đã ghi.

**Date:** 2026-09-01

---

## DV-008 — Đợt rà soát giao diện đối chiếu ảnh: bảy tính năng, một module

**Date:** 2026-09-01

**Bối cảnh.** Chủ dự án đối chiếu `LTT_VOICE_UI_PROMPT_PACK_V1` với bản đang
chạy và kết luận *"giao diện thiếu quá nhiều module và tính năng"*. Đúng: một
phép dò 15 điểm trên DOM thật cho **15/15 thiếu**.

**Cách tìm ra chúng, và đây mới là phần đáng giữ.** Không đọc ảnh rồi liệt kê
mong muốn, mà **đối chiếu năng lực backend đã có với thứ giao diện phơi ra**.
Cách ấy tìm được thứ mà đọc ảnh không tìm được:

- `features.chuan_bi_van_ban(tu_dien_rieng=…)` → `text_pipeline.chuan_hoa` →
  `tu_dien.ap_dung(them=…)` — **ba tầng nhận tham số, không ai truyền**. Một
  đường ống dựng xong rồi để không. Đó là ⑤ `PRONUNCIATION` của ảnh 01, và nó
  là một **module** chứ không phải một nút.
- `job_history.list_owned` đã có `start`/`end`/`cursor` — màn Lịch sử không dùng.
- Màn Lịch sử hứa *"nghe lại và **tải về** được"* mà **không có đường tải nào**.

**Đã làm:** tốc độ đọc hậu kỳ · mã giọng trong ô chọn · nhập TXT · tải MP3 ·
lưu vào Dự án · phiên bản khối · ví dụ Python ở màn API · cột dự án · lượt gần
nhất ở Studio · trình phát sóng âm chung cho bốn màn · từ điển phát âm riêng ·
lọc theo ngày · đọc lại một lượt.

**Cố ý KHÔNG làm** (không có backend, dựng ra là nút giả): điểm
Quality/Similarity/Stability % · "Voice Family" · hạn mức Storage ở header ·
nghe thử cho giọng mẫu (chưa sinh tệp mẫu) · tách theo câu ở Studio (đó là mô
hình của màn Dự án; làm ở hai nơi là hai chỗ để chúng lệch nhau).

⛔ **Hai lời hoãn cũ hoá ra là hai lời từ chối vĩnh viễn.** Chú thích trong
   `ltt_voice_studio.html` ghi *"Q119 CẤM phơi ra tốc độ"* — một **trích dẫn
   sai**: Q119 nêu đích danh năm tham số *lấy mẫu* và không có tốc độ. Và
   *"`Save to Project` — chưa có Dự án"* đúng lúc viết, hết đúng khi Dự án ra
   đời, nhưng không ai quay lại kiểm điều kiện.

   ⇒ Khi hoãn một việc, ghi **điều kiện mở lại**, và ghi đủ để người sau kiểm
     được điều kiện ấy mà không phải tin lời ta.

🔴 **Và một trích dẫn sai được CHỐT BẰNG MỘT PHÉP KIỂM sống dai hơn nhiều.**
   `test_347` cấm `name="toc_do"` lên giao diện, viện chính Q119. Chú thích sai
   thì ai cũng dám sửa; một chốt đỏ thì người ta lùi lại — vì gate đỏ trông y
   hệt một lỗi, và bản năng đúng ("đừng làm gate đỏ") quay ra bảo vệ đúng thứ
   sai. Phép kiểm ấy vừa **cấm nhầm** một thứ, vừa **quên cấm** hai thứ thật
   (`repetition_penalty`, `repetition_window`).

**Bài học đo lường.** Chọn tệp test bằng một **mẫu tên tự nghĩ** là tự chọn lấy
bằng chứng cho mình: tôi báo "243 xanh" từ 11 tệp gõ tay, chạy đủ 26 tệp thì hai
tệp đỏ — và cả hai đúng chỗ vừa sửa. Liệt kê bằng `ls | grep` rồi chạy cả danh
sách.

---

## DV-009 — Đường lùi giọng: có, nhưng KHÔNG BAO GIỜ đổi giới và KHÔNG BAO GIỜ im

**Ngày:** 2026-09-07 · **Gate:** `20260907T175803Z-5652.json` (27/29 PASS, 0 bước
đỏ quy về mục này) · **Migration:** `e7b2c94a1d38`

### Vấn đề

Một giọng nhân bản `active` mà không còn `voice_repr` nào `dang_dung` — ca **nâng
engine**, vì biểu diễn gắn với phiên bản engine — làm cả lượt đọc **hỏng**, kèm
một câu sai:

> *"Giọng này chưa ghi danh xong. Hãy thử lại sau ít phút."*

Chờ **không bao giờ** giúp được: không có job ghi danh nào đang chạy. Một lời
khuyên không dẫn tới đâu tệ hơn một lời từ chối.

### Quyết định

`apps/ltt_voice/lui_giong.py` — bậc thang bốn mặt, nới theo thứ tự:

```
1. cung lan + cung gioi + cung phong cach + cung vung
2. noi VUNG        (giu lan + gioi + phong cach)
3. noi PHONG CACH  (giu lan + gioi)
4. DUNG  -> tra None, KHONG ha tieu chuan
```

⛔ **Hai mặt không bao giờ được nới: GIỚI và LÀN.** Hết ứng viên thì trả `None`
và báo lỗi thành thật. Một lỗi *"không đọc được"* tốt hơn một bản đọc bằng giọng
người khác.

⭐ Vùng nới **trước** phong cách: giọng miền Bắc đọc thay miền Nam thì người nghe
nhận ra ngay nhưng vẫn hiểu; một giọng tin tức đọc thay giọng kể chuyện thì đổi
hẳn **nhịp** của cả bài.

### Vì sao luật ấy là luật, không phải sở thích

Hệ `D:\Viral` chạy đúng đường lùi **không** giữ giới, và khách của họ báo ngày
26/08/2026: *"giọng nam bị biến thành giọng nữ"*. Chú thích trong
`giong_piper.py` của họ ghi lại cơ chế:

> *"TRUOC DAY backend KHONG CO bang nay: gioi chi nam trong NHAN hien thi …
> moi duong LUI GIONG o backend khong co cach nao biet khach dang chon nam hay
> nu ⇒ lui ve PIPER_VOICE_MAC_DINH = giong NU, ke ca khi khach chon giong NAM."*

Ta học bài ấy **miễn phí**, bằng cách đọc mã của người khác.

### Cột `VoiceProfile.gioi` — và vì sao migration KHÔNG đoán

`""` = **KHÔNG RÕ**, và đó là một giá trị thật, không phải chỗ trống chờ điền.

⛔ Cám dỗ rõ ràng là suy giới từ tên hiển thị hoặc từ F0 của clip nguồn. Cả hai
sai theo hướng nguy hiểm: chúng sinh ra một cột **trông như dữ liệu**, được
`lui_giong` tin, và khi sai thì hậu quả đúng bằng thứ cột này sinh ra để ngăn.
`toc_do.py` đã ghi một ca thật của phép đo F0 — bộ dò nhầm quãng tám trên một
clip giọng nữ, báo 105,6 Hz.

⇒ Không rõ thì `lui_giong` **từ chối lùi**, và bộ lọc ở bộ chọn giọng **vẫn
hiện** giọng đó. Hai hành vi ấy đều là *"không biết thì đừng làm hộ người ta"*.

### Giới hạn ĐÃ BIẾT của bản này

Ứng viên lùi hiện **chỉ là 20 giọng mẫu**, và cả 20 đều làn `vi`. Nghĩa là:

```
lan vi + gioi ro   ->  lui duoc
lan en             ->  KHONG (chua co giong mau lan en)
gioi = "" khong ro ->  KHONG (khong duoc doan)
```

Đây là giới hạn của **kho giọng**, không phải của thuật toán — `chon()` nhận một
danh sách ứng viên bất kỳ. Ngày kho chung có giọng làn `en` đã khai giới, mở rộng
bằng cách đưa chúng vào `cac`, **không** bằng cách sửa bậc thang.

---

## DV-010 — Ba đường ống có đủ khớp nối mà chưa bao giờ có nước

Nối `lui_giong` vào làm lộ ra rằng **kênh báo cho khách chưa từng chạy**. Cả ba
đều là mã trông hoàn chỉnh:

| Thứ | Trạng thái trước 07/09/2026 |
|---|---|
| `KetQua.canh_bao` | có trường, có khoá trong `as_result()`, **không ai điền** — `jobs.py` viết `ref_b64, preset, _ =` |
| `lan_ngon_ngu.dien_canh_bao` | **0 nơi gọi**; `doi_chieu` trả khuôn còn `{lan_giong}` — khách sẽ đọc đúng chuỗi ấy |
| `/ket-qua/{job_id}` | không trả `canh_bao`; Studio không có ô hiện nó |

⇒ `lan_ngon_ngu.doi_chieu` chạy ở **mọi** lượt kể từ 01/09 và chưa bao giờ nói
được gì. Nay `doi_chieu` trả **câu đã điền**, `jobs.py` giữ nó, route trả nó, và
Studio có `#lv-kq-canh-bao`.

🔴 **Bài học đo lường:** một chỗ trống có sẵn cho một giá trị trông **giống hệt**
một chỗ đã được điền đúng. Cách duy nhất phân biệt là hỏi *"ai ghi vào đây"* —
và câu hỏi ấy trả lời được bằng AST, nên nó thành phép kiểm
(`test_503::test_jobs_KHONG_VUT_canh_bao_di`).

⚠️ Và nó vừa thành thứ **không được phép** chết: một đường lùi im lặng chính là
lỗi DV-009 đi sửa. Mất dòng cảnh báo là mất toàn bộ điểm của nó.

---

## DV-011 — Kiểm tệp model theo NỘI DUNG trước khi nạp

`os.path.isfile()` trả lời *"có tệp không"*, không trả lời *"tệp đó có phải model
không"*. `voice_sidecar/kiem_model.py` hỏi câu thứ hai, và `engine.nap()` gọi nó
**trước** `from vieneu import Vieneu`.

Ba phép kiểm theo định dạng, không một luật chung:

| Định dạng | Phép kiểm |
|---|---|
| `*.safetensors` | đọc `u64` độ dài phần đầu, đòi `8 + n <= cỡ tệp` và `{` ở **offset 8** |
| `*.onnx` | sàn 1 MB + byte đầu không phải `<` hay `{` |
| `*.json` | `json.load` phải chạy được |

⛔ **Vì sao safetensors KHÔNG dùng luật của ONNX.** Phần JSON của safetensors
**thật sự bắt đầu bằng `{`** — chỉ là ở offset 8. Và byte 0 là byte thấp của độ
dài; một phần đầu dài đúng 123 byte cho byte 0 = `0x7B` = `{`. Áp luật ONNX vào
đây là một phép kiểm **đúng gần hết thời gian** — loại tệ nhất: nó sẽ báo oan một
lần, giữa đêm, và không ai tái hiện được.
`test_502::test_safetensors_co_dau_JSON_o_offset_8_van_duoc_coi_la_LANH` dựng
đúng ca tình cờ ấy.

**Fail-open khi không định vị được cache, fail-closed khi định vị được mà hỏng.**
Trộn hai nhánh là hỏng theo cả hai hướng: fail-closed ở nhánh đầu chặn mọi máy
phát triển ⇒ cổng bị gỡ trong một tuần; fail-open ở nhánh sau thì cổng vô nghĩa.

**Nguồn:** `D:\Viral\resources\app-src\giong_piper.py::_onnx_hop_le`, chú thích
07/08/2026 — proxy/captive portal trả **HTTP 200 kèm HTML**, `isfile` xanh
**vĩnh viễn**, khách mất hẳn giọng offline và không lần nào tự sửa được. Ta
không thừa kế mã của họ; ta thừa kế bài học, và làm chặt hơn vì ta biết chính
xác ba định dạng của mình.


---

## DV-012 — Hồ sơ tốc độ theo TỪNG giọng, và ba lỗ tiền lộ ra khi nối nó vào

**Ngày:** 08/09/2026 · **Hạng mục:** U-01 của `VIRAL_VOICE_AUDIT_2026-09-07.md`

`gia.py` ước thời lượng bằng **một** cặp hằng số cho **cả kho giọng**, và chú
thích của chính nó đã nói ra giới hạn: *"Số đo là của MỘT bộ giọng trên MỘT
card."* Kho đối chiếu giữ bảng tương đương cho 61 giọng, và chênh lệch giữa hai
giọng **cùng ngôn ngữ** ở đó lên tới **43 %**.

`apps/ltt_voice/ho_so_giong.py` thay cặp hằng số ấy bằng một **ảnh chụp JSON**
tra theo tên preset — không CSDL, không mạng, vì `manifest._gia()` chạy ở mọi
lượt báo giá và chú thích của nó cấm đúng hai thứ đó.

### 🔴 Nhận hay bác một hồ sơ NGUYÊN KHỐI, không theo từng trường

Bản đầu tra hai trường riêng rẽ, và `tests/test_506` bắt được một lỗi **tiền**:
khi `do_lech_chuan` phồng tới mức không tin được, tốc độ lùi về hằng số chung
(18) nhưng **phí khởi động vẫn lấy số đã đo** (1,0 thay vì 1,5):

```
1,0 + 1000/18 = 56,56   <   1,5 + 1000/18 = 57,06
```

Trộn phần **bị bác** của một hồ sơ với phần lùi cho ra ước **thấp hơn cả đường
lùi thuần** — tức giữ thiếu credit.

⭐ Lý do đúng đắn hơn cả con số: nếu một phép đo không đủ tin để lấy tốc độ, thì
phí khởi động **rút từ chính phép đo ấy** cũng không đủ tin. Hai trường không
độc lập — chúng là hai ẩn của cùng một hệ phương trình.

### ⛔ Lỗ thứ hai: ô báo giá của khách KHÔNG đi cùng đường với phần bị giữ

`POST /xem-truoc` có một chú thích tự nhận: *"con số hiện ra ở đây là con số sẽ
bị tạm giữ, không phải một ước lượng thứ hai."*

Câu ấy đúng **cho tới** lúc `uoc_tran` nhận thêm `giong` — rồi nó thành sai mà
**không ai đụng vào route**. Một mệnh đề chép tay trong chú thích không tự biết
nó vừa hết đúng.

⇒ Route nay nhận `preset` và truyền xuống; `voice.js` gửi nó ở nhánh `"m:"`.
Chỉ `preset`, **không** `voice_id`: giọng nhân bản sinh ra **sau** lượt đo nên
sẽ không bao giờ có hồ sơ, và cả hai đầu phải lùi về **cùng** một hằng số.

### 🔴 Lỗ thứ ba, và là lỗ lớn nhất: bài dài là N lượt phát, không phải một

`gia.giay_uoc` là mô hình hai tham số `khoi_dong + n/toc_do`, trong đó
`khoi_dong` là khoảng lặng model thêm vào **mỗi lượt phát**. `uoc_tran_lo` nói
thẳng điều đó: *"Phần khởi động cộng cho TỪNG đoạn, và đó là đúng: mỗi đoạn là
một lượt phát riêng."*

Nhưng `_gia` gọi `uoc_tran(so_ky_tu=len(cả_bài))` — tính như thể cả bài là
**một** lượt. Hai hàm trong cùng một tệp giá mâu thuẫn nhau, và `uoc_tran_lo`
tồn tại **không người gọi** suốt thời gian ấy.

Đo 08/09/2026, trong trần công khai hiện tại:

| ký tự | số đoạn | giữ (bản cũ) | giá theo từng đoạn | thiếu |
|---|---|---|---|---|
| 5.000 | 4 | 56 | 57 | 1 |
| 100.000 | 67 | 1.112 | 1.132 | **20** |

⛔ Lệch nhỏ, nhưng lệch về **đúng phía chốt 3.3 cấm**. Và hậu quả không phải
"thu thiếu 20 credit" — quyết toán vượt phần giữ thì lượt chạy bị đánh hỏng
**sau khi** đã tiêu hết GPU, tức khách chờ xong rồi nhận một lỗi.

### ⭐ Cái làm ba lỗ này lộ ra là ĐỐI CHỨNG, không phải phép kiểm

Cả ba đều **xanh** dưới một phép kiểm viết theo lối thường:

- lỗ 1: `uoc_tran >= tinh(giây_thật)` xanh, vì cả hai cùng lệch một kiểu
- lỗ 2: "route bằng manifest" xanh, vì **chưa giọng nào có hồ sơ** nên hai đầu
  cùng rơi về hằng số chung — nó sẽ xanh **đúng tới ngày cơ chế bắt đầu có tác
  dụng**
- lỗ 3: "giữ ≥ giá theo từng đoạn" xanh ở văn bản ngắn, vì một đoạn thì hai
  công thức trùng nhau

⇒ Mỗi phép kiểm tiền ở `test_506` đi kèm một **đối chứng độ nhạy**: một vế
chứng minh con số **thật sự đổi** khi thứ đang đo đổi. Và mỗi lượt vá được
nghiệm bằng phép **tiêm bản cũ**, đọc `returncode` chứ không khớp mẫu stdout.

### Ranh giới còn lại

`ho_so_giong.json` hôm nay **rỗng**, và đó là một trạng thái khởi đầu hợp lệ —
mọi giọng lùi về hai hằng số chung, y như trước 08/09. Lấp nó cần
`tools/do_ho_so_giong.py` chạy trên **GPU rảnh**; công cụ ấy tự từ chối khi thấy
`gate`/`pytest` đang chạy (`Win32_Process`, vì `ps` của Git Bash không thấy tiến
trình Windows).

**Chưa đo ⇒ chưa có số.** Không điền tay một giá trị nào vào ảnh chụp.


---

## DV-013 — Ba hạng mục cùng chạm một chỗ: *thứ tự nào, và ai được ở trong danh sách*

**Ngày:** 08/09/2026 · **Hạng mục:** U-11, U-12, U-05, U-04

### U-11 — ETA thật, và ba hằng số giá gõ tay trong JavaScript

`vo.py` cấp `ky_tu_moi_giay` cho template kèm một chú thích đúng nguyên tắc:
*"CÙNG hằng số mà phần giữ credit dùng … Hai chỗ ước thời lượng bằng hai tỉ lệ
khác nhau là hai chỗ nói với khách hai con số khác nhau."*

Nhưng nó cấp **một** trong **ba** số của công thức. `voice.js` gõ nốt hai số
còn lại:

```js
Math.ceil((1.5 + n / 18) * 0.2)
```

Ba con số ấy là bản chép của `GIAY_KHOI_DONG_UOC`, `KY_TU_MOI_GIAY_UOC`, và
`MCREDIT_MOI_GIAY / MCREDIT_MOI_CREDIT`.

⭐ Nên bảng giá thứ hai **vẫn tồn tại** — nó chỉ nấp sau một hằng số đã được cấp
đúng, tức chỗ khó nhìn nhất. Một chú thích nói "dùng chung hằng số" làm người
đọc tin **cả khối** đã dùng chung.

⇒ Cả ba nay đến từ máy chủ; `/xem-truoc` trả thêm `giay_uoc` tính trên phép chia
**thật** (`chia_doan`, `can_bang=True`).

### U-12 — bảng chữ cái không phải một quyết định sản phẩm

`tham_chieu.py` đã xếp giọng theo phong cách, kèm một câu đáng giữ: *"Bên tiêu
thụ lấy phần tử ĐẦU làm mặc định, nên thứ tự ở đây là một QUYẾT ĐỊNH sản phẩm."*

Đúng — nhưng trong một tầng phong cách vẫn còn 6–7 giọng, và giữa chúng thứ tự
là `x.ma`. **Bảng chữ cái không phải một quyết định; nó là sự vắng mặt của một
quyết định** — trong khi phần tử đầu vẫn được dùng làm mặc định.

`apps/ltt_voice/muc_dung.py` đếm từ bảng `jobs` của **chính ta**, ảnh chụp trong
bộ nhớ, làm mới 6 giờ một lần trong `nghe_thu.bao_tri`.

⛔ **Không mượn số của kho đối chiếu**, dù `D:\Viral` có sẵn bảng độ phổ biến cho
61 giọng và nó lấp đúng ô trống này. Hai lý do, và lý do thứ hai nặng hơn: nó đo
khách của *họ*; và ta **không kiểm chứng được** nó, nên ngày nó sai ta không có
cách nào biết.

⚠️ **Vòng phản hồi là có thật** — hiện trước ⇒ dùng nhiều ⇒ càng hiện trước. Ta
nhốt nó **trong** một tầng phong cách và chặn nó **giữa** các tầng: `uu_tien`
phong cách vẫn là khoá thứ nhất. Mức dùng không bao giờ kéo một giọng kể chuyện
lên trên một giọng tự nhiên.

⭐ Ảnh chụp rỗng ⇒ kết quả **đúng bằng** thứ tự cũ. Không có nhánh nào "chờ dữ
liệu", và một kho vừa khởi động lại vẫn đúng.

### U-05 — cổng xuất xứ, và phạm vi của nó hẹp hơn cái tên

Cột `VoiceProfile.license_status` với **bốn** giá trị, ba trong bốn là "không":
`cho_soat` (mặc định) · `thieu_bang_chung` · `tu_choi` · `ok`.

🔴 **Nó gác đúng một thứ: giọng có ra tới KHO CHUNG hay không.** Nó *không* gác
giọng riêng của một khách — xuất xứ của giọng riêng đã có `VoiceConsent` trả
lời, và bắt một cột thứ hai cùng trả lời câu ấy sẽ **làm biến mất giọng của
chính khách** vào ngày migration chạy. Một thiệt hại thật để đổi lấy một phép
kiểm trùng.

⇒ `tests/test_508` chốt ranh giới ấy từ **cả hai phía**. Vế thứ hai (*"cổng
KHÔNG chạm tới giọng riêng"*) là vế bảo vệ khách hiện tại: thiếu nó, một bản vá
"cho chắc, lọc hết" sẽ xanh.

**Danh sách CHO, không phải danh sách CẤM.** `LICENSE_CHO_PHEP = ("ok",)`. Một
bản viết `!= "tu_choi"` trông tương đương và không tương đương: ngày ai đó thêm
một trạng thái mới, danh-sách-cấm để nó **lọt qua** (mở, im lặng),
danh-sách-cho **chặn** nó cho tới khi có người cố ý thêm vào.

**Migration đặt `cho_soat` cho MỌI dòng cũ, kể cả dòng đang `dung_chung=True`.**
Chưa ai soát thật thì ghi `ok` là **bịa một phán quyết** — và cột này sinh ra để
được trích dẫn trong một tranh chấp.

⚠️ Bản đầu của docstring migration viết *"Đo được 08/09: không dòng nào đang
`dung_chung=True`"*. **Tôi chưa đo con số đó.** Đã thay bằng một lời khai thật
kèm câu lệnh đếm để người triển khai tự đo. Một con số bịa trong phần biện minh
làm luận điểm mạnh lên một cách không thật — và nó nằm ngay cạnh một lập luận về
việc đừng bịa phán quyết.

### U-04 — `voice_quality_profile`, và vì sao `diem` được phép RỖNG

`ly_do_loai` là một **cột**, không phải một dòng nhật ký. Nghe như thủ tục, cho
tới lúc có người hỏi *"sao giọng này biến mất?"*.

⭐ Và nó trả lời **mãi mãi**: ngày nâng engine, một giọng bị loại vì *"rè ở âm
/s/"* đáng được thử lại; một giọng bị loại vì *"không có consent"* thì **không**
— cùng trạng thái `rejected`, hai số phận hoàn toàn khác nhau.

⛔ `diem` `nullable`. `None` = **chưa đo**, khác `0.0` = "đo được, và rất tệ".
Một cột `NOT NULL DEFAULT 0` nói rằng mọi giọng đều đã được chấm và đều 0 điểm —
một câu sai về **toàn bộ** kho. Cùng kỷ luật với ba ô "NOT YET BENCHMARKED" của
bản kiểm toán.

---

## DV-014 — U-09: gỡ khả năng quên, thay vì viết một chú thích to hơn

**Ngày:** 08/09/2026

Ở đúng chỗ `nghe_thu.PHIEN_BAN` được gõ tay, chú thích cũ viết ra **cả hai** khớp
nối và **cả** hậu quả:

> *"ĐỔI CÂU TRÊN THÌ PHẢI ĐỔI CHUỖI NÀY … Không đổi phiên bản = khách nghe câu
> **cũ** trong khi mã nói câu mới, và không ai phát hiện ra vì cả hai đều là
> tiếng nói bình thường."*
> *"⚠️ Nó cũng phải đổi khi `PHIEN_BAN_THAM_SO` đổi."*

⭐ **Một chú thích nói "phải nhớ làm X" là một chú thích thừa nhận X sẽ bị
quên.** Và ở đây cái giá của việc quên đã được viết ra bằng chữ: hỏng lặng lẽ,
không triệu chứng nào để lần. Câu trả lời đúng không phải một chú thích to hơn.

⇒ `PHIEN_BAN = "v2-" + sha256(CAU_NGHE_THU + "|" + PHIEN_BAN_THAM_SO)[:12]`.

Đọc được `PHIEN_BAN_THAM_SO` không hiển nhiên — sidecar chạy trong **venv cách
ly**. Nhưng `voice_sidecar/tham_so.py` có đúng **một** dòng import
(`from __future__`); nó là một tệp hằng số thuần, cố ý. Thiếu nó thì trả `"?"` —
một giá trị **ổn định**, nên khoá không nở ra vô hạn trên máy phát triển.

### ⛔ Băm msgid GỐC, và điều đó phơi ra một khớp nối thứ hai

`dung()` gửi `str(_t(CAU_NGHE_THU))` xuống engine, tức **nội dung âm thanh phụ
thuộc ngôn ngữ**, trong khi khoá thì không. Hôm nay vòng bảo trì chạy ngoài mọi
request nên nó luôn rơi về ngôn ngữ mặc định và hai giá trị trùng nhau — **một
sự trùng hợp, không phải một bảo đảm**.

Không vá: thêm ngôn ngữ vào khoá làm **mọi** tệp nghe thử hiện có thành mồ côi,
và đó là thay đổi cần một lượt đo trước. Ghi ra để nó không lặng lẽ.

### Tách *dựng bao nhiêu* khỏi *dựng lúc nào*

`MOI_LUOT_TOI_DA = 3` đúng cho vòng bảo trì, vì vòng ấy chạy **cùng tiến trình**
với worker job — dựng cả 20 tệp là giữ GPU một phút liền trong khi job của khách
chờ mà không ai biết vì sao.

Nhưng hệ quả: sau mỗi lần `PHIEN_BAN` đổi, **bảy tiếng** trôi qua trước khi giọng
cuối có tệp. Trong bảy tiếng đó, cách duy nhất để biết một giọng nghe ra sao là
**trả tiền tạo một lượt**.

⇒ `tools/dung_nghe_thu.py` chạy **ngoài** vòng bảo trì, một lần, sau khi triển
khai. Trần 3/giờ **giữ nguyên** — hai thứ giải hai bài toán khác nhau, và
`test_509` chốt đúng điều đó để không ai gỡ trần "vì nay đã có công cụ".

Công cụ tự từ chối khi `Win32_Process` thấy gate/pytest, không dừng cả lượt khi
một giọng hỏng, và **thoát khác 0** khi có giọng hỏng — in ra rồi thoát 0 là
cách một lỗi đi qua một đường ray tự động mà không ai thấy.

---

## DV-015 — U-13 · U-14 · và vì sao U-07 DỪNG ở phép đo

**Ngày:** 08/09/2026

### U-13 — nghe thử văn bản của khách: bốn trần, và cái thứ ba là cái quan trọng

| trần | chặn |
|---|---|
| `TRAN_KY_TU = 160` | biến cửa này thành một TTS miễn phí |
| `MOI_GIO = 6` | một tài khoản đốt GPU cả ngày |
| **suất `vieneu_gpu`** | một lượt miễn phí làm khách **trả tiền** phải chờ |
| `TRAN_THOI_GIAN_S = 45` | một lượt treo giữ luôn worker web |

⛔ Ba cái đầu là chuyện **lạm dụng**. Cái thứ ba **không phải**: ngay cả một
khách hoàn toàn tử tế, dùng đúng 6 lượt/giờ, vẫn giành card khỏi một job đã trả
tiền nếu ta không xếp sau. `admission.hold_persisted` trả `None` khi hết suất
và **không chờ** — cửa này là công dân hạng hai của cái card, có chủ ý.

**Phơi nhiễm, bằng số:** 6 lượt × 160 ký tự ≈ 8,9 giây tiếng/lượt (18 ký tự/giây)
= ~53 giây tiếng/giờ/tài khoản ≈ **10,7 credit/giờ** nếu tính tiền. Đó là trần
trên, chỉ đạt khi card rảnh suốt.

⛔ Ngày con số ấy thành vấn đề, thứ phải đổi là `MOI_GIO` — **không phải** bỏ
phép xếp sau admission. Bỏ phép ấy đổi một chi phí **đo được** lấy một hàng đợi
khách trả tiền, và **không ai sẽ thấy** sự đánh đổi đó xảy ra.

⚠️ Bộ đếm nằm trong bộ nhớ một tiến trình (ADR-005), nên trần thật là
`MOI_GIO × số tiến trình web`. Nói ra chứ không giấu: một trần "6" mà thật ra là
"18" là một trần **nói dối**. Trần cứng thật nằm ở suất `vieneu_gpu` — nó là
**một** trên toàn cụm và không nhân lên theo tiến trình.

⭐ `xin_luot()` kiểm **và** trừ trong cùng một lần giữ khoá. Tách thành
`con_lai()` rồi `ghi_nhan()` là để hai request đồng thời cùng đọc "còn 1" rồi
cùng đi tiếp — và nó chỉ xảy ra **khi có tải**, tức đúng lúc trần quan trọng nhất.

### U-14 — chỉ số theo giọng, và thứ nó KHÔNG biết

Bản kiểm toán đòi ba chỉ số: RTF · tỉ lệ hỏng · CER trung vị. **Ta có hai.**

🔴 Và ta không có RTF *cho tới hôm nay*: sidecar trả `X-Gen-S`/`X-RTF` ở mọi
lượt, và **không ai lưu chúng**. Hệ quả không phải "thiếu một chỉ số đẹp": mọi
câu hỏi vận hành dạng *"giọng nào tốn GPU nhất"*, *"bản engine mới nhanh hơn
bao nhiêu"* đều không trả lời được bằng dữ liệu ta có — chỉ trả lời được bằng
cách **tiêu thêm GPU để đo lại**.

⇒ `KetQua.gen_s` nay ghi lại, và `ban_doc_dai` **cộng dồn** qua từng lô. Ghi đè
thay vì cộng sẽ cho ra GPU-giây của lô cuối và gọi nó là của cả bài — nhỏ hơn
sự thật nhiều lần, và **trông hoàn toàn hợp lý**.

⛔ `gen_s = 0` nghĩa là **KHÔNG BIẾT**, nên nó không vào `as_result()`. Mọi job
trước 08/09 có `gen_s = 0`, và `0 / giây` là một RTF bằng **0** — tức "nhanh vô
hạn". Trộn chúng vào trung vị làm bảng nói **ngược hẳn** sự thật.

⛔ `cer_trung_vi = None` ở mọi giọng, và `None` là một **câu trả lời**. Không suy
nó từ bất cứ thứ gì đang có: một số bịa trong bảng chỉ số sẽ được so sánh, xếp
hạng, rồi dùng để **loại một giọng**.

⚠️ `gen_s` **không được dùng để tính tiền** (`test_510` chốt điều này bằng cách
soi `gia.py`). Tính tiền theo GPU-giây là tính tiền theo tình trạng máy của
**ta** — khách không điều khiển được nó, nên họ trả nhiều hơn vào ngày ta chạy
nhiều việc khác.

### 🔴 U-07 — DỪNG Ở PHÉP ĐO, và bốn lý do đều đo được

| đo 08/09/2026 | hệ quả |
|---|---|
| `LTT_VOICE_STREAM` **chưa đặt** — `/v1/stream` trả 404 | không xác minh được gì, kể cả bằng tay |
| `co_streaming()` gọi `c.nap()` rồi dò `infer_stream` | muốn biết engine làm được không thì **phải nạp model** ⇒ cần GPU rảnh |
| cửa phát **PCM16**; `lo_ra_tep` cố ý ghi **float32** | streaming **kém trung thực hơn theo thiết kế** — mẫu vượt 1,0 bị kẹp *trước* khi bộ hạ trần đỉnh kịp chạy |
| chốt 3.4: tiền theo thời lượng **ffprobe** trên tệp cuối | một luồng **không có tệp cuối** ⇒ *"tính tiền theo giây đã phát"* là một **mô hình tính tiền MỚI** |

Cái thứ tư là cái chặn thật. Một đường tính tiền mới, không chạy được một phép
kiểm nào, trên một cửa đang tắt — ba điều kiện ấy cộng lại thì lựa chọn đúng là
**không viết**.

⛔ Và **không viết nửa vời**. Thêm `sidecar_client.phat_dan()` mà không ai gọi
là dựng đúng cái "đường ống có đủ khớp nối mà chưa bao giờ có nước" đã ghi ở
DV-010 — và mắc lại đúng lỗi mà cột `license_status` vừa mắc trong chính phiên
này (xem `tools/soat_giong.py`).

**Điều kiện để mở lại U-07**, theo thứ tự:

1. GPU rảnh ⇒ bật `LTT_VOICE_STREAM=1`, gọi `co_streaming()` và **đo** xem
   engine hiện tại có `infer_stream` không. Nếu không thì U-07 chết ở đây.
2. Quyết định thương mại: tính tiền theo **giây đã phát** hay theo **giây đã
   sinh**? Hai câu trả lời khác nhau khi khách ngắt giữa chừng.
3. Đo hành vi Cloudflare với `StreamingResponse` — trần 100 giây áp cho
   **byte đầu** hay cho **cả luồng**? Chưa ai đo, và cả thiết kế phụ thuộc nó.
4. Quyết định chất lượng: chấp nhận PCM16 cho đường nghe-ngay, hay đổi cửa
   sidecar sang float32?

---

## DV-016 — Bảy bánh cóc không phải hai mươi bước, và tôi đã báo cáo như thể chúng là

**Ngày:** 08/09/2026

Suốt phiên này tôi quét **bảy** công cụ tĩnh sau mỗi hạng mục — `check_ruff`,
`check_mypy`, `check_silent_except`, `check_bo_qua`, `check_i18n`,
`check_luat_van_hanh`, `lint_app_contract` — rồi báo cáo *"bánh cóc xanh"*.

Lượt L3 đỏ ở **`check_dich_thieu.py`**, một bước tôi chưa từng chạy. Đếm lại
bằng AST trên `tools/gate.py::_steps`: gate có **20 bước tĩnh** dựa trên một
script trong `tools/`. Tôi chạy **7**.

### 🔴 Cái sai không phải bỏ sót — là dùng một TẬP CON làm ĐẠI DIỆN

Bảy bước ấy không được chọn theo một tiêu chí nào. Chúng là những bước tôi
**tình cờ gặp** trong phiên: ba bước do một phiên khác báo tôi làm đỏ, bốn bước
tôi đọc thấy trong `CLAUDE.md`. Rồi tôi gọi tập ấy là *"bánh cóc"* và báo mức
tin cậy của **toàn bộ cổng** dựa trên nó.

⭐ Cùng hình dạng với sáu ca khác trong ngày (`DV-013`, `§19.0` của bản kiểm
toán, ba vòng chẩn đoán Postgres): **phạm vi phép đo hẹp hơn phạm vi lời tuyên
bố.** Lần này đối tượng bị suy rộng là **chính bằng chứng tôi đưa cho người
khác**.

⚠️ Và nó tốn đúng một lượt L3 — **15 phút**, cộng một cửa sổ mà ba phiên khác
phải đứng yên — để học một thứ mà `check_dich_thieu.py` trả lời trong **2,6
giây**.

### ⇒ Danh sách đến từ MÃ, không từ trí nhớ

```
python -c "import ast,pathlib; s=pathlib.Path('tools/gate.py').read_text(encoding='utf-8');   print([n.args[0].value for n in ast.walk(ast.parse(s))          if isinstance(n,ast.Call) and getattr(n.func,'id','')=='Step'])"
```

Chạy hết 20 bước tĩnh mất **dưới một phút** và **không đụng pytest** — tức nó
nằm ngoài mọi ràng buộc ngân sách lõi. So với 15 phút của một lượt L3 đỏ, tỉ lệ
là 1:15.

⛔ Đây **không** phải một cấp test mới. Hợp đồng vận hành `§4` đã có bốn cấp và
tệp này không thêm cấp thứ năm. Nó chỉ nói: khi bạn định **báo cáo** rằng phần
tĩnh đã sạch, hãy lấy danh sách từ `_steps` chứ đừng lấy từ trí nhớ về những
bước bạn tình cờ chạy.

### Chốt lại bằng một câu dùng được

**Một tập con không tự khai rằng nó là tập con.** Bảy dòng `rc=0` trông y hệt
hai mươi dòng `rc=0` — khác biệt duy nhất nằm ở thứ *không có mặt*, và không có
gì trên màn hình chỉ vào nó.

---

## DV-017 — U-15: đường nối chỉ được phép BỎ QUA, không được phép ĐẢO

**Ngày:** 08/09/2026 · **Hạng mục:** U-15 / T-07

`chuan_hoa()` làm **hai** việc rất khác nhau trong một khối cứng:

```
PHIEN AM   tu dien phat am · ha chu hoa viet tat
DOC SO     so thu tu · ngay · gio · ky hieu · so lon · phan cach nghin
```

Với engine hiện tại cả hai đều cần — nhưng vì **hai lý do khác nhau**:

- `phien_am` bật vì upstream #168 báo engine đọc `ch` thành `tr`, và tên riêng
  thì không bảng nào đoán trước được;
- `doc_so` bật vì engine đọc `1.250.000` theo từng chữ số.

⭐ Nên gộp chúng vào một cờ `chuan_hoa=True/False` sẽ buộc engine thứ hai chọn
**cả hai hoặc không cái nào** — tức nó sẽ chọn "cả hai" và mang theo lỗi. Một
engine đã có bộ chuẩn hoá số riêng mà vẫn bật `doc_so` sẽ **đọc hai lần**:
`"15%"` → `"15 phần trăm"` → `"mười lăm phần trăm phần trăm"`.

### 🔴 KHUÔN CHỈ ĐƯỢC TẮT MỘT NHÓM, KHÔNG ĐƯỢC ĐỔI THỨ TỰ

Thứ tự trong `chuan_hoa()` là **chịu lực**, và ba chú thích trong đó ghi lại ba
lần đã trả giá bằng một lần hỏng thật:

| thứ tự | mất nó thì |
|---|---|
| từ điển **trước** số | phép thay số cắt mất ranh giới từ của tên riêng |
| `_ha_chuoi_viet_hoa` **sau** từ điển | hạ nhầm chữ hoa của viết tắt đã biết |
| `_KY_HIEU` → `_doc_so_lon` → `_NGAN` | `1.250.000đ` ra *"…nghìnđ"* — một chữ `đ` mắc kẹt |

Một khuôn cho phép **đổi thứ tự** mở lại cả ba lỗ cùng lúc, ở một chỗ mà không
chú thích nào nhìn thấy. ⇒ `KhuonChuanHoa` chỉ có ba trường `bool`, và
`test_512` chốt đúng điều đó: *mọi trường phải là `bool`* — không được mang một
danh sách hay một thứ tự.

### ⛔ ĐỔI KHUÔN LÀ ĐỔI TIỀN — nên mặc định phải GIỐNG HỆT TỪNG BYTE

`manifest._gia()` đếm ký tự **sau** chuẩn hoá. Tắt `doc_so` làm hoá đơn nhỏ đi;
bật `doc_so_tran` làm nó to lên.

⇒ Trước khi tách, tôi **chụp đầu ra thật** của tám chuỗi ở hai chế độ và nhúng
vào `test_512::MOC_VANG`. Đó không phải kỳ vọng ai gõ ra — là giá trị của bản
trước. Sau khi tách: **16/16 khớp từng byte**.

⚠️ Và mốc vàng đi kèm một đối chứng (`test_moc_vang_KHONG_rong_va_KHONG_tam_thuong`):
một mốc gồm toàn chuỗi không có gì để chuẩn hoá sẽ xanh với **mọi** bản vá, kể
cả bản xoá sạch `chuan_hoa`.

### ⭐ Lời khai nằm cạnh sự thật về engine, không nằm trong bộ chuẩn hoá

`KHUON_CHUAN_HOA` ở `tham_so_cong_khai.py` — cùng chỗ với `TRAN_MOI_LUOT_SINH`
và `SO_LAN_THU_JOB`. Ngày có engine thứ hai, khuôn của nó nằm cạnh tham số của
nó. `text_pipeline.KHUON_MAC_DINH` **dựng từ** lời khai ấy chứ không gõ lại —
hai bản khai cho cùng một engine là hai bản sẽ lệch.

### Hai lỗi tôi mắc khi làm chính hạng mục này

1. Guard `"from dataclasses import" not in s` — kiểm **module đã import chưa**
   trong khi thứ cần là **tên `replace`**. Import có sẵn nhưng chỉ mang
   `dataclass, field`.
2. `ma.index("phien_am") < ma.index("doc_so")` — chuỗi `"doc_so"` khớp vào
   `doc_so_tran` trong **chữ ký**, nên phép so đang đo thứ tự hai **tham số**
   chứ không phải thứ tự hai **nhánh**.

⭐ Cả hai cùng một hình dạng, và là hình dạng lặp nhiều nhất trong ngày: **đo
một thứ ĐẠI DIỆN cho thứ mình định đo.** Bản vá cho cả hai là đọc **cấu trúc**
(`ast`, `lineno`) thay vì đọc **chuỗi**.

---

## DV-018 — U-17: lần đầu ba màn cần đăng nhập được đo, và bộ đo hỏng ở đúng chỗ đó

**Ngày:** 08/09/2026

### 🔴 Đường `--cookie` của `check_a11y.py` CHƯA BAO GIỜ CHẠY

`tools/a11y_quet.js:39` gọi `new URL(CAU_HINH.goc)`, và `URL` **không tồn tại**
trong ngữ cảnh `playwright-cli run-code`. Nó nằm **trong** nhánh
`if (CAU_HINH.cookie)`, nên:

- lượt chạy **không** cookie không bao giờ chạm tới nó;
- `ROUTE_MAC_DINH` chỉ có bốn route **công khai** (`/`, `/login`, `/dang-ky`,
  `/bang-gia`) — không route nào cần đăng nhập, nên gate không bao giờ truyền
  `--cookie`.

⇒ Một đường được **khai trong docstring** (*"route cần đăng nhập thì phải truyền
`--cookie`"*) mà chưa bao giờ có nước chảy qua. Lại đúng `DV-010`, lần này ở
tầng công cụ đo.

⭐ **Và bản vá đã tồn tại sẵn** ở `tools/mobile_quet.js:189`, kèm nguyên chú
thích giải thích: *"`URL` không tồn tại trong ngữ cảnh `run-code`. Tách tên máy
bằng chuỗi."* Ai đó đã gặp lỗi này, sửa nó ở **một** tệp, ghi lại lý do — và tệp
anh em có **cùng đoạn mã** thì không ai sửa.

> **Chép lại bộ đo mà không chép bài học là cách một lớp lỗi sống sót qua chính
> bản vá của nó.**

### Kết quả đo — 55 nút / 5 mã luật, lần đầu tiên

| mã luật | nút | mức | ở đâu |
|---|---|---|---|
| `nested-interactive` | 18 | **serious** | `article[data-ten=…]` — thẻ giọng |
| `aria-allowed-role` | 18 | minor | cùng phần tử |
| `color-contrast` | 14 | serious | `.lv-chon-noi > small` · `.lv-loc-tao` · `#lv-da-nut-moi` … |
| `landmark-unique` | 3 | moderate | |
| `aria-progressbar-name` | 2 | serious | `.lv-da-thanh` |

**Đã sửa `aria-progressbar-name`** (thêm `aria-label` nói cả hai số: *"3/8 khối"*
trả lời được câu "còn bao nhiêu", "37%" thì không). Đo lại: **55 → 53 nút,
5 → 4 mã**.

### ⛔ CÒN LẠI MỘT QUYẾT ĐỊNH, KHÔNG PHẢI MỘT BẢN VÁ

36 nút (`nested-interactive` + `aria-allowed-role`) đều đến từ **một** dòng:

```html
<article ... tabindex="0" role="button" aria-pressed="…">
    <button class="lv-the-song lv-nghe">…</button>   <- Nghe thu
    <button class="btn sm ghost lv-the-xem">Chi tiết</button>
</article>
```

Một phần tử `role="button"` **chứa** hai `<button>` thật. Trình đọc màn hình
trình bày thẻ như **một** nút, và hai điều khiển bên trong thành không với tới
được một cách tin cậy.

🔴 **Và cấu trúc này đã gây HAI lỗi thật, cả hai đã được vá bằng JS:**

| ngày | lỗi | bản vá |
|---|---|---|
| 04/09 | bấm chuột vào thẻ **không bao giờ** mở được panel — `closest(BEN_TRONG)` khớp vào **chính cái thẻ** | `if (trong && trong !== t) return;` |
| — | Enter trên nút "Nghe thử" bị **nuốt** bởi handler của thẻ | `if (e.target !== t) return;` |

⇒ Hai bản vá ấy chữa **triệu chứng**. `axe` chỉ vào **nguyên nhân**: cái thẻ
không nên là một nút.

**Bản vá đúng** — gỡ `role="button"`/`tabindex`/`aria-pressed` khỏi `<article>`;
chuột vẫn bấm-cả-thẻ (mẫu quen thuộc), bàn phím đi qua nút **"Chi tiết"** vốn
đã có sẵn.

⚠️ **Chưa làm, và cố ý.** Nó đổi điều hướng bàn phím của **mọi** khách trên màn
Giọng, và hai phép kiểm trong `test_500` đang chốt đúng hai bản vá JS ở trên.
Đó là một quyết định sản phẩm, không phải một lượt dọn lint — nên nó được nêu ra
kèm bằng chứng (2 lỗi cũ + 36 nút) chứ không được làm lặng lẽ ở cuối một phiên
dài.

### ⚠️ Bẫy môi trường: Git Bash biến `/ltt-voice` thành `C:/Program Files/Git/ltt-voice`

MSYS tự chuyển đối số trông giống đường dẫn tuyệt đối. Bộ đo báo *"Cannot
navigate to invalid URL"* và URL trong log là `http://127.0.0.1:8123C:/Program
Files/...`. Chạy với `MSYS_NO_PATHCONV=1`.

⭐ Và `check_a11y` **từ chối so mốc khi phạm vi khác** — nó làm đúng: quét ít
route hơn cho ra số nhỏ hơn, và số nhỏ hơn *đọc lên y hệt một cải thiện*. Nên
lượt soát này chạy qua một script chỉ-đọc, **không** `--accept`, để không âm thầm
hạ phạm vi bảo vệ của mốc công khai.
