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
