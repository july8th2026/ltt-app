# Kế hoạch hoàn tất — 37 hạng mục còn lại

Viết 07/09/2026, sau khi `PLAN_LAP_RAP_2026-09-06.md` đóng 17/19 hạng mục.

⭐ **Kế hoạch này không phải danh sách việc. Nó là danh sách CHẶN.** Phép đo mở
đầu nói rõ vì sao: 37 ô còn lại **không** bị chặn bởi mã.

---

## 0. Đo trước — vì sao "còn 9%" là một con số dễ đọc sai

```
KE_HOACH_TRIEN_KHAI    431 tick / 6 dang do / 37 chua   ->  90,9%
PLAN_LAP_RAP           17/19 hang muc da dong hoac rut  ->  ~89%
```

Nhưng 37 ô còn lại **nặng hơn hẳn** 431 ô đã xong: chúng là phần **thương mại
hoá** (hiệu chuẩn chất lượng, ma trận provider, beta có khách thật), không phải
phần **xây**. Phân theo *thứ chúng cần*:

| chặn bởi | số ô | ví dụ |
|---|---|---|
| người thật chấm | ~4 | `H31.3d3` ≥3 rater/case · `H33.R4` blind A/B · `H21.8` beta 5 user |
| dataset có license | ~4 | ≥30 ảnh + 12 video có consent |
| cửa sổ GPU | ~4 | `H31.3c2` peak VRAM · `H35.10c` trần đồng thời |
| môi trường staging riêng | ~10 | `H33.R1b/R3/R5/R6` trên *exact RC* |
| pack phụ thuộc bốn nhóm trên | ~7 | `H31.3` `H31.4` `H31.5` `H31.6` |
| chủ dự án | 1 | `H35.9` pepper off-site, xoay khoá provider |
| kỹ thuật thuần | ~5 | tắt CSDL báo lỗi · `R8–R10` · `G11` `G12` `G5b` |

⇒ **~30/37 chờ một thứ máy không tự cấp được.** Nên kế hoạch phải tấn công
  **chặn**, không tấn công **việc**. Viết thêm mã không rút ngắn được gì.

---

## 1. 🔴 Đối chiếu cộng đồng — và nó chặn đứng một hạng mục ngay

Tra 07/09/2026 qua GitHub API. `H31.3b` khai *"Evaluator provisioning: LPIPS
offline + checksum; **pyIQA** và **DOVER**"*. Cả hai **cấm dùng thương mại**:

| công cụ | giấy phép thật | dùng thương mại | cập nhật |
|---|---|---|---|
| `pyIQA` (`chaofengc/IQA-PyTorch`) | **PolyForm Noncommercial 1.0.0** | ⛔ **KHÔNG** | 2026-08-31 |
| `DOVER` (`VQAssessment/DOVER`) | **S-Lab 1.0** — *"non-commercial purpose"* | ⛔ **KHÔNG** | **2024-08-12** *(chết 2 năm)* |

🔴 Nền tảng này **bán tool AI theo credit**. Dùng hai công cụ ấy để hiệu chuẩn
   chất lượng sản phẩm thương mại là **vi phạm giấy phép** — và `DOVER` còn
   kèm rủi ro thứ hai: không ai bảo trì suốt hai năm.

⭐ Kế hoạch gốc yêu cầu *"dataset có **license**/consent"* nhưng **không** đặt
   cùng câu hỏi cho chính công cụ chấm. Một lỗ hổng đối xứng.

### Bản thay — đã tra giấy phép thật, không đọc badge

| thay cho | công cụ | giấy phép | trạng thái |
|---|---|---|---|
| LPIPS *(giữ)* | `richzhang/PerceptualSimilarity` | **BSD-2-Clause** | ổn định |
| **DOVER** | **`Netflix/vmaf`** | **BSD-2-Clause-Patent** | 2026-08-14, chuẩn công nghiệp |
| **pyIQA** | `Lightning-AI/torchmetrics` | **Apache-2.0** | 2026-08-31 |
| bổ sung | `andrewekhalel/sewar` · `slhck/ffmpeg-quality-metrics` | **MIT** | active |
| WER | `jitsi/jiwer` | **Apache-2.0** | 2026-09-03 |
| DER | `pyannote/pyannote-audio` | **MIT** | 2026-09-06 |

⭐ `VMAF` là thứ Netflix dùng trong sản xuất, và giấy phép của nó có **cấp phép
   sáng chế minh thị** — đúng thứ một sản phẩm thương mại cần, và là thứ
   `DOVER` không có.

⛔ **Đừng mượn ngưỡng của họ.** Điểm VMAF 93 "tốt" trong ngữ cảnh streaming của
   Netflix không nói gì về ngưỡng chấp nhận của một job upscale bán theo
   credit. Mượn công cụ thì được; mượn **ngưỡng** thì phải đo lại trên chính
   dữ liệu của mình.

---

## 2. Đổi hướng lớn: **tôi chấm thay người**

Chủ dự án chốt 07/09: thay vì thuê rater, **xây để tôi chấm**.

Việc đó gỡ nhóm chặn nặng nhất (~4 ô, và ~7 pack phụ thuộc nó). Nhưng nó chỉ
đứng vững nếu phương pháp chặt — nếu không, ta đổi *"chưa có dữ liệu"* lấy
*"có dữ liệu sai"*, và cái sau tệ hơn.

### ⛔ Ba điều tôi KHÔNG thay được, nói trước

**1. Một tôi không phải ba rater.** Ba người cho **độ đồng thuận** — một phép
   đo về việc phán quyết có ổn định không. Chạy tôi ba lượt **không** phải ba
   rater: các lượt của tôi tương quan với nhau, và một thiên lệch hệ thống sẽ
   xuất hiện đều ở cả ba.

**2. Chất lượng THỜI GIAN là chỗ tôi yếu nhất.** Tôi đọc **khung hình**, không
   đọc **chuyển động**. Nhấp nháy (flicker), giật (judder), trôi màu giữa các
   khung — người thấy ngay, tôi gần như không. `H31.3c` đặt tên đúng ba thứ
   ấy.

**3. Sở thích của tôi có thể lệch hệ thống** — ví dụ thiên về ảnh sắc nét/bão
   hoà hơn, trong khi người dùng thật thấy nó "giả".

⇒ Nên thiết kế dưới đây **chia đôi**: chỗ tôi chấm được, và chỗ chuyển sang
  **máy đo khách quan** thay vì chuyển sang người.

### Thiết kế: bốn lớp, và lớp 1 quyết định ba lớp kia có nghĩa hay không

```
lop 1  DOI CHUNG BIET TRUOC   cap da biet dap an -> toi phai xep DUNG
lop 2  MU + XAO TRON          bo nhan, dao thu tu, khong biet cai nao la ban moi
lop 3  CHAM                   A/B bat buoc chon, kem ly do mot cau
lop 4  DOI CHIEU MAY          so voi VMAF/LPIPS — cho nao LECH la mot phat hien
```

**Lớp 1 là điều kiện tiên quyết.** Dựng các cặp mà đáp án **biết trước một
cách khách quan**: cùng một nguồn, một bản suy giảm có tham số biết trước
(nén nặng hơn, mờ hơn, nhiễu hơn). Nếu tôi không xếp đúng các cặp ấy thì mọi
phán quyết ở lớp 3 **vô giá trị** — và phải nói ra thay vì báo cáo điểm.

⭐ Đây đúng luật đã ghi ở `BAY_TRONG_CONG_CHAT_LUONG.md` **Bẫy 24**: một dụng
   cụ không có đối chứng thì con số nó phát ra không phải phát hiện. Ở đây
   **dụng cụ là tôi**.

**Lớp 4 mới là chỗ giá trị thật.** Không phải để tôi xác nhận VMAF, mà để tìm
**chỗ hai bên lệch nhau** — vì mỗi chỗ lệch là một trong hai điều, và cả hai
đều đáng biết:

- máy đo đúng, tôi sai ⇒ đo được **thiên lệch của tôi**, ghi lại thành giới hạn;
- tôi đúng, máy sai ⇒ tìm ra **một lớp lỗi VMAF/LPIPS mù**, thứ đáng chốt bằng
  một phép kiểm riêng.

⛔ Và tuyệt đối **không** dùng lớp 3 để "chỉnh" ngưỡng cho tới khi nó khớp lớp
   4. Đó là gọt phép đo cho vừa kết luận.

### Hai điều còn lại phải nói thẳng với chủ dự án

- **`H21.8` beta 5 user thật thì tôi KHÔNG thay được.** Nó đo *"người dùng có
  hoàn thành được việc không"*, không đo chất lượng đầu ra. Tôi có thể chạy
  toàn bộ luồng và bắt lỗi chức năng, nhưng *"khách bỏ cuộc ở bước 3 vì không
  hiểu"* là dữ liệu chỉ khách mới có.
- **Chất lượng thời gian của video** chuyển sang **VMAF** (máy đo), không
  chuyển sang tôi. Đó là chỗ đổi người lấy máy, không đổi người lấy tôi.

---

## 3. Tối ưu tốc độ — đo trước, ba đòn bẩy

### 3a. Gate: **2 bước ăn 89%**

Trung bình 6 lượt gần nhất:

```
tong                        794 giay (13,2 phut)
bo test (song song)         568,8s   71,6%
bat bien da tien trinh      138,6s   17,4%   -> cong don 89,1%
27 buoc con lai              86,6s   10,9%
```

⇒ Tối ưu 27 bước nhanh kia là **vô nghĩa**. Đòn bẩy nằm ở đúng hai bước.

### 3b. Va chạm liên phiên — **6 vòng gate mất trắng trong một ngày**

Đo 06–07/09: `--ff-only` bắt **người đến sau** trả toàn bộ chi phí, kể cả khi
hai thay đổi không đụng nhau (3 tệp `docs/` so với mã sau một cờ tắt).

Và hôm nay gate đỏ **ba lần vì môi trường, không vì mã**:

```
1  test_44_release_build   FileNotFoundError tools/tmp*.py   (Bay 29)
2  mypy + test_306         mot dong khai kieu                (that su la loi)
3  test_214                relation "users" does not exist   (va cham postgres_test)
```

Ca 1 và 3 **không phải lỗi mã**. Ca 3 là đúng thứ ghi nhớ
`khoa-khai-thieu-tai-nguyen` mô tả: hai lượt `drop_all()` vào nhau.

⇒ **Đề xuất: thêm tài nguyên `trunk` vào `cua_so_yen`** — ai vào chu trình
  *gate → ff* thì giữ khoá; người kia commit trong cây riêng. Thay một **lời
  hứa** bằng một **cơ chế**.

⛔ Nhưng nó chỉ chạy được nếu **mọi phiên đọc cùng một chỗ**, mà mỗi worktree
   chạy `gate.py` riêng ⇒ chỗ đó là `~/.claude/CLAUDE.md`, **tệp của chủ dự
   án**. Hai phiên đều từ chối tự sửa. **Đây là quyết định của chủ dự án.**

### 3c. `pre-commit` chỉ phủ **3/29 bước**

Bốn dòng `Passed` sau mỗi commit trả lời một câu hẹp hơn nhiều câu người ta
đọc nó thành (~10% cổng). Hôm nay một tệp mới qua sạch cả bốn hook rồi làm đỏ
**hai** bước gate.

⇒ Việc rẻ nhất: một lệnh tiền-kiểm cho **tệp mới** (`mypy` + `check_i18n`),
  vài giây đổi lấy một vòng 12 phút. Đã ghi vào `docs/16` §2.

---

## 4. Lộ trình — xếp theo *thứ chặn thứ khác*

```
GIAI DOAN A — GO CHAN (khong viet tinh nang, chi mo duong)   ~6-8 h
  A1  Thay pyIQA + DOVER bang torchmetrics + VMAF, do lai moc
  A2  Dung bo cham 4 lop, lop 1 (doi chung biet truoc) TRUOC TIEN
  A3  Nguon media co license ro rang cho bo hieu chuan
  A4  [chu du an] khoa `trunk` trong cua_so_yen

GIAI DOAN B — HIEU CHUAN (chay duoc sau A)                   ~10-14 h
  B1  H31.3b/b2  evaluator provisioning + checksum offline
  B2  H31.3c     temporal + performance  -> VMAF, KHONG phai toi
  B3  H31.3d     calibration >= 30 anh + 12 video
  B4  H31.3d3    cham: toi + doi chieu may (thay >= 3 rater)
  B5  H31.3       pack Upscale dong

GIAI DOAN C — NHAN BAN (lap lai khuon B)                     ~12-16 h
  C1  H31.4 AutoSub   (jiwer WER + pyannote DER)
  C2  H31.5 Seedance/Image/Thumbnail/Clip/Text/Agent
  C3  H31.6 release regression + trend + canary

GIAI DOAN D — CAN MOI TRUONG RIENG                           chua uoc duoc
  D1  H33.R1b/R3/R5/R6  — deu doi "exact staging RC"
  D2  H35.10c           — can mot cua so GPU
  D3  R8-R10            — da state + memory

GIAI DOAN E — CHI CHU DU AN                                  ~1 h cua nguoi
  E1  H35.9b  cat pepper ra ngoai may
  E2  H35.9e  xoay khoa provider
  E3  S1      4 phep kiem tren iPhone that
  E4  H21.8   beta 5 user that
```

⭐ **A4 là hạng mục rẻ nhất mà lợi nhất**: nó không đóng ô nào, nhưng nó trả
   lại ~1,5 giờ máy mỗi ngày có hai phiên chạy song song.

⛔ **Giai đoạn D chưa ước được thời gian**, và nói *"chưa ước được"* là câu
   đúng — khác hẳn nói một con số rồi trượt. Nó cần một quyết định hạ tầng
   (staging là một máy? một namespace? một tài khoản Vultr riêng?) mà chưa ai
   chốt.

---

## 5. Điều kiện dừng — viết trước để không tự nới

Mỗi giai đoạn chỉ được coi là xong khi:

1. có một **bản ghi máy sinh ra** (`test-results/`, `.moc`, hoặc JSON) mang
   `sha`, không phải một dòng đánh dấu tay;
2. phép kiểm của nó **đỏ được** khi tiêm bản cũ — và
3. **đối chứng số lượng**: "không tìm thấy gì" không bao giờ được đọc thành
   "mọi thứ đều đúng" (**Bẫy 31**).

⭐ Với bộ chấm, thêm điều kiện thứ tư: **lớp 1 phải đạt trước khi công bố bất
   kỳ điểm nào của lớp 3.** Nếu tôi không xếp đúng các cặp biết-trước-đáp-án
   thì con số của tôi không phải dữ liệu — nó là nhiễu có định dạng đẹp.
