# Bàn giao P11 — red team độc lập

**07/09/2026.** Viết bởi chính người đã xây B4/B5/B6 và cả bốn bản vá P10.

## ⛔ Đọc tệp này như một BẢN KHAI, không như một bản đồ

Kế hoạch đòi P11 chạy ở **phiên mới, cây mới**, và lý do nằm ngay ở dòng trên:
tôi là người viết thứ sắp bị thẩm định. Một người viết biết rõ mình **định** làm
gì, nên rất khó thấy chỗ mình **thực sự** làm gì.

⇒ Tệp này có ích ở chỗ nói ra **tôi đã đo gì** và **tôi chỉ suy luận gì**. Nó
  **không** phải danh sách việc phải làm, và đặc biệt **không** phải ranh giới
  của việc phải làm. Một red team chỉ kiểm những gì tệp này liệt kê là một red
  team đang đọc bản đồ của bị cáo.

⭐ Mục **"Chỗ tôi nghi mình sai"** là phần đáng đọc nhất. Nếu chỉ có thời gian
  cho một mục, đọc mục đó.

---

## 1. Đã đo, có đối chứng

Mỗi dòng dưới đây có một phép đo **và** một đối chứng — tức đã tiêm bản cũ và
thấy nó đỏ. Đây là mức tin cậy cao nhất tôi tạo ra được.

| Mệnh đề | Đối chứng |
|---|---|
| Dừng ở biên chờ chặn được lần chạy tiếp | bản cũ ⇒ 4/10 đỏ |
| Chạy tiếp bị chặn khi đã có người chạy | gỡ lease ⇒ `returncode 1`, rồi trả nguyên trạng, sha256 khớp |
| Lease **được nhả**, không khoá chết | phép kiểm ngược riêng |
| Phiếu của run đã huỷ không còn hiện | bản cũ ⇒ 2 đỏ |
| Lọc phiếu **không** quá tay | phép kiểm hai run, một huỷ một không |
| CLS trên Chrome thật = 0,0003 | ép dịch chuyển ⇒ 0,2043 (bộ đo chạy thật) |
| Cờ V3 tắt ⇒ prompt **không đổi một byte** | vế TẮT đo ra 0 ký tự, 0,00 ms |

---

## 2. 🔴 Chỗ tôi nghi mình sai

Xếp theo mức tôi nghi, cao xuống thấp.

### 2.1 Lease 10 phút KHÔNG che được một bước chạy lâu

Đây là chỗ tôi nghi nhất, và nó nằm trong bản vá của chính tôi.

Nhịp đập của lease đi nhờ callback `ghi=` của `DP.tiep_tuc`, tức **mỗi bước một
nhịp**. Nếu **một bước** kéo dài hơn `TTL_CHAY_TIEP = 10 phút` — một tool chậm,
một job nặng, một model kẹt — thì:

```
lease het han  ->  reclaim_expired() thu hoi  ->  nguoi thu hai ACQUIRE DUOC
                -> hai luot model cho mot lan duyet, dung cai lo vua va
```

⛔ Tức bản vá **thu hẹp** cửa sổ đua từ *"luôn luôn"* xuống *"chỉ khi một bước
   vượt 10 phút"*, chứ **không đóng** nó.

### Nhưng phải nói cho chính xác: CƠ CHẾ có thật, NGƯỜI KÍCH HOẠT thì khó dựng

Nói quá một rủi ro làm red team tốn công; nói thiếu thì giấu lỗi. Nên đây là
phần tôi nghĩ tiếp sau khi viết đoạn trên:

Lease hết hạn mới chỉ là **điều kiện cần**. Còn phải có một người thứ hai **thật
sự gọi** vào lúc ấy. Có đúng hai nguồn gọi, và cả hai đều đi qua
`nen_chay_tiep`:

```
1. route duyet          -> chi chay sau mot `_quyet` THANH CONG (CAS)
2. _danh_thuc_run       -> chi chay khi mot JOB vua xong
```

Và `nen_chay_tiep` đòi **không còn phiếu chưa quyết** *và* **không còn job treo**.
Ghép lại:

- Bước chậm là một **job** ⇒ `con_cho_job` là `True` ⇒ **cả hai nguồn bị chặn**,
  lease chưa bao giờ là thứ đang gánh.
- Bước chậm là một **lời gọi model** hoặc một **tool đồng bộ** ⇒ không có job
  treo. Nhưng lúc ấy nguồn 2 không có gì để kích hoạt nó (không job nào xong),
  còn nguồn 1 cần một phiếu **khác** được duyệt — mà nếu còn phiếu khác chưa
  quyết thì `nen_chay_tiep` đã trả `False` cho người thứ nhất từ đầu.

⇒ Tôi **chưa dựng được** một kịch bản chạm tới lỗ này. Nghĩa là nó có thể là một
  lỗ **không tới được** — hoặc tôi chưa nghĩ ra đường, đúng như ba lần tôi sai
  trong ngày ở §4.

**Đề nghị cho P11 — hỏi đúng câu này:** *có đường nào khiến hai lời gọi
`tiep_sau_duyet` cùng vượt `nen_chay_tiep` không?* Nếu **có**, thì lease là thứ
duy nhất đang chặn, và câu hỏi 10 phút thành thật sự cấp bách. Nếu **không**,
thì lease là lớp phòng thủ thứ hai và TTL không phải chuyện gấp.

⭐ Cách tái hiện nhanh: hạ `TTL_CHAY_TIEP` xuống vài giây thay vì dựng một tool
  ngủ 11 phút. Nhưng **hạ TTL không tự chứng minh lỗ tới được** — nó chỉ bỏ qua
  vế thời gian. Vế khó là vế người kích hoạt.

⭐ Nếu tái hiện được thì bản sửa đúng có lẽ là **đập nhịp bằng một luồng riêng**
  chứ không đi nhờ nhịp bước — vì nhịp bước đúng **trừ khi** bước chậm, mà bước
  chậm mới là lúc cần nó. ⚠️ Luồng ấy phải mở **phiên CSDL của riêng nó**: một
  `Session` SQLAlchemy không an toàn đa luồng, và chính `chay_tiep_nen` đã ghi
  lại bài học đó trong docstring của nó.

### 2.2 Phụ phí V3 đo trên một CSDL RỖNG

`tools/do_phu_phi_v3.py` chạy với SQLite tạm và `user_id` bịa. Nó ra **3 tool /
1.213 ký tự**. Một người dùng thật có thể bật nhiều tool hơn, và
`chieu_tool.chieu()` đọc theo người dùng.

⇒ Con số 1.213 là **sàn**, không phải trần. Đo lại trên một tài khoản thật ở
  P12, và nếu số ấy lớn hơn nhiều thì phần prefill đáng lo hơn tôi ước.

### 2.3 `_danh_thuc_run` chạy ở tiến trình web — tôi ĐỌC ra, không CHẠY ra

Tôi kết luận đường chạy tiếp luôn nằm trong tiến trình web (nên cờ `so.dung`
dùng chung) bằng cách đọc mã: `_danh_thuc_run` nằm trong `dong_bo`, mà `dong_bo`
chạy khi client hỏi qua HTTP.

⛔ Nhưng có dịch vụ `LTTStudioWorker` **riêng tiến trình**. Nếu có bất kỳ đường
   nào khiến `dong_bo` chạy trong worker, kết luận của tôi sai và lỗ huỷ rộng
   hơn tôi mô tả. Tôi đã sai đúng một giả thuyết kiểu này sáng nay (xem §4).

### 2.4 `dang_cho` chỉ lọc `CANCELLED`, không lọc `FAILED`

Có chủ đích: đường `FAILED` chưa được đo, và nới bộ lọc theo suy đoán là cách
một bộ lọc bắt đầu giấu thứ nó không nên giấu. Nhưng một phiếu của run `FAILED`
có lẽ cũng chết. **Chưa kiểm.**

### 2.5 `ten_lease` được miễn trừ khỏi bánh cóc IDOR

Tôi lập luận nó an toàn (chuỗi thuần, một người gọi đã kiểm chủ sở hữu, id là
uuid). Lập luận, không phải phép đo. Nếu có đường nào để người ngoài chọn được
`run_id` đưa vào đó, miễn trừ này sai.

### 2.6 Đo giao diện làm trên loopback, KHÔNG trên URL công khai

CLS và ma trận 5 mốc đều đo ở `127.0.0.1:8198` với cờ V3 bật. Giao diện V3
**chưa có trên production** (kiểm được: `grep ltc-duyet` ra 0 trong bundle đang
chạy), nên vế công khai chưa ai đo. Xem CK1/CK2 ở `STATE.md`.

---

## 3. Phép kiểm đột biến bắt buộc — và một cái bẫy cụ thể

Kế hoạch đòi: *cố ý phá từng thứ và test phải **đỏ*** — sở hữu · duyệt ·
idempotency · tiền · trần vòng lặp · registry động.

⚠️ **Đừng khớp mẫu stdout để kết luận "đã đỏ".** Đọc `returncode`. Một lỗi thu
   thập (import sai, fixture vỡ) cũng in chữ `failed` và sẽ bị đọc thành *"đối
   chứng đạt"* trong khi phép kiểm chưa chạy lần nào.

⭐ Khuôn tự phục hồi tôi đã dùng, dùng lại được: lưu `sha256` bản gốc → tiêm →
  chạy → khôi phục trong `finally` → **khẳng định sha256 khớp lại**. Không có
  bước khẳng định cuối thì một lượt tiêm hỏng để lại cây bẩn, và lượt gate sau
  đó đo một thứ không ai định đo.

---

## 4. Ba lần tôi sai TRONG NGÀY — hình dạng đáng để nghi tiếp

Ghi ra vì mỗi lần đều là một giả thuyết **khớp rất vừa** rồi hoá ra sai.

| Tôi tưởng | Thật ra | Bắt được nhờ |
|---|---|---|
| Huỷ hỏng vì **đa tiến trình** | `_danh_thuc_run` chạy ở tiến trình web | đọc tiếp thay vì dừng ở giả thuyết khớp |
| URL công khai không đo được vì **Cloudflare chặn** | **V3 chưa có trên production** | `grep` bundle đang chạy |
| Phụ phí V3 là **204 ms** | 987 ms lượt đầu (nạp module) rồi **2,7 ms** | nhìn **phân bố** thay vì trung bình |

⇒ Cả ba đều là *một lời giải thích đúng-vừa-đủ làm điều tra dừng sớm*. Nếu P11
  thấy tôi khẳng định điều gì mà chỉ có một đường bằng chứng, hãy nghi đúng chỗ
  đó.

---

## 5. Bốn thứ P11 **không** gỡ được, đừng mất thời gian

| Việc | Vì sao |
|---|---|
| Bước gate `bat bien da tien trinh` | cần **UAC** — phiên nối tiếp mất token nâng quyền; chỉ chủ dự án bấm được |
| Ba bước `frontend *` | thiếu `node_modules` ở cây riêng; `npm ci` là việc chạy được nhưng nặng |
| Đo trên URL công khai | V3 chưa phát hành; đây là việc của **nghiệm thu P12** |
| Xoay khoá production đã lộ | chủ dự án đã hoãn có chủ đích tới khi hệ thống xong |

---

## 6. Nơi tra cứu

| Cần gì | Ở đâu |
|---|---|
| Trạng thái thật từng pha | `docs/CHATLTT_V3/STATE.md` |
| Tiêu chí gốc từng pha | `docs/CHATLTT_V3/00_KE_HOACH_V3.md` |
| Bốn bản vá P10 | `git log claude/chatltt-v3-agentic` — `b9aaa766`, `ebe18104` |
| Phép kiểm biên huỷ | `tests/test_849_*` |
| Phép kiểm đua chạy tiếp | `tests/test_817_*` (hai phép kiểm cuối) |
| Bẫy trong chính cổng chất lượng | `docs/BAY_TRONG_CONG_CHAT_LUONG.md` |
