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
