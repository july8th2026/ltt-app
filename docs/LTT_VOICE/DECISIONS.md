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

⭐ Và thiếu sót cụ thể của VieNeu **đã biết và rẻ hơn nhiều để vá**: baseline K4
   đo được bản sinh ra mất **-3,65 dB** trên 4 kHz so với clip nguồn — một
   khuyết tật của codec neural, có hướng cố định. Một high-shelf ở khâu hậu kỳ
   đóng được một phần, và nó không phải một đường huấn luyện.

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
