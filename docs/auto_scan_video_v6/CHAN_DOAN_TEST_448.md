# `test_448` — bảy màu đỏ, và ba nguyên nhân KHÁC NHAU

> Đo 2026-09-10, nhánh `phien/asv-v6`. Lượt chạy ghi ra **ngoài kho**
> (`LTT_ASV_E2E_RA=C:\Temp\asv-ui\nghiem_thu_thu.json`) nên bằng chứng đã commit
> không bị hạ cấp — xem §0.
>
> Tệp này **nối tiếp** `docs/auto_scan_video_v4/evidence/20260909_tran_token_ra_chuyen_loi_thoai.md`
> chứ không thay nó. Tệp kia trả lời *"vì sao `chuyen_loi_thoai` hỏng"*; tệp này
> trả lời *"sau khi vá cái đó, còn lại gì"*.

---

## 0. ⛔ Vì sao lượt đo này ghi ra ngoài kho

Bản bằng chứng đang commit khai `giong_that: True`, `model_that: True`,
`thay_the: []` — một lượt **toàn phần**, hỏng ở `content_process`.

Một lượt chạy lại **không có** khoá máy B và token giọng sẽ khai `thay_the: 4`.
Nó có thể làm bảy bài xanh, nhưng bằng chứng khi đó **yếu hơn** bản đang có: nó
chứng minh đường ống chạy được với hàng giả, không chứng minh sản phẩm chạy được.

⇒ Làm gate xanh bằng cách thay một phép đo mạnh bằng một phép đo yếu là đúng
  hình dạng *"phép đo lệch chiều"*. Nên lượt này ghi ra **ngoài kho**: nó chẩn
  đoán, nó không thay bằng chứng.

⭐ Và đọc–ghi dùng **cùng một biến** (`BIEN_RA`, sửa 06/09), nên chuyển hướng
   ghi cũng chuyển hướng đọc — cả tệp `test_448` tự nhất quán trên bản tạm.

---

## 1. Ba nguyên nhân, không phải một

| # | Chặn ở | Nguyên nhân | Trạng thái |
|---|---|---|---|
| **A** | `content_process` | trần token 4.096 < nhu cầu 10.248 | ⚠️ **đường đã thông, TRẦN CHƯA XÁC NHẬN** — §2 và §6 |
| **B** | `giu_hinh / compose` | `sqlite3.OperationalError: database is locked` | ⛔ cần PostgreSQL — §3 |
| **C** | `cat_thong_minh / qc` | T4 loudness `-15,07` ngoài `-14,0 ± 1,0` | 🔴 lệch **0,07 dB** — §4 |

Bản ghi cũ chỉ thấy **A** vì nó dừng ở đó. Vá A xong thì B và C lộ ra — đúng
mệnh đề tệp 09/09 ghim lại: *"một trần nới ra làm lộ trần kế tiếp"*.

---

## 2. A — trần token: vá ở đâu, và vì sao KHÔNG vá ở `ltt_llm`

`ai.goi` đã nhận `max_tokens`/`timeout_s` từ 09/09. `ai.goi_tinh_tien` — **cửa
duy nhất của mọi lần gọi có tính tiền**, và là cửa mà cả bốn giai đoạn đi qua —
**không truyền chúng xuống**. Tham số có sẵn ở một hàm ngay bên dưới và không ai
với tới.

⛔ Không nâng `ltt_llm.ngan_sach.TOKEN_RA_MAC_DINH["job"]`: cửa `job` là mặc
   định cho **mọi** app dùng model nhà. Nâng nó vì một lô 12 đoạn của Auto Scan
   là bắt mọi app khác mang một trần không ai đo cho họ.

⇒ ASV khai ngân sách **của ASV**, theo THAO TÁC (`ai.NGAN_SACH_RA`), nên chỗ gọi
  thứ năm viết ngày mai **tự** nhận đúng ngân sách thay vì phải nhớ.

Con số đặt theo **giá trị lớn nhất quan sát được kèm biên** — không theo công
thức tuyến tính, vì chính báo cáo 09/09 đã tự bác bỏ độ dốc của nó khi vòng đo
thứ ba lật hai phân bố chồng lên nhau.

---

## 3. B — `database is locked`: đây KHÔNG phải chuyện máy B

`docs/BAY_TRONG_CONG_CHAT_LUONG.md` Bẫy 33 đã ghi sẵn: với bộ nghiệm thu ASV,
`LTT_TEST_DATABASE_URL` là **điều kiện CẦN**, vì *"SQLite không sống nổi đường
ống; web + worker cùng ghi ra `database is locked`"*.

⚠️ Nên `BAN_GIAO.md` §2 xếp lỗi này là *"hạ tầng test, nhiều phiên cùng ghi"* —
   **không đúng hẳn**. Lượt đo 10/09 chạy khi **không phiên nào khác chạy bộ
   test** (đo cây tiến trình trước khi bấm) và nó **vẫn** hỏng. Không phải tranh
   chấp giữa các phiên; là một tiến trình web và một tiến trình worker của
   *chính lượt ấy* cùng ghi vào một tệp SQLite.

⇒ Điều kiện để gỡ: một CSDL PostgreSQL vứt đi (tên phải chứa `test` — `pg_scratch`
  từ chối tên khác). Máy có PostgreSQL 17 đang chạy ở 5432, nhưng **thông tin
  đăng nhập nằm trong `C:\LTTPlatform\secrets\app.env`**, và ACL ở đó chặn đọc
  (đo: `UnauthorizedAccessException`; `IsInRole(Administrator)` = `False`).

⛔ ACL đó là **cố ý** (hạng mục W1.5 của audit). Đừng nới nó ra.

---

## 4. C — T4: giả thuyết cũ SAI, và cái sai đáng ghi hơn con số

`BAN_GIAO.md` §2 viết: T4 hỏng *"gần như chắc vì giọng thay thế là SAPI tiếng
Anh trong một bài lồng tiếng **Việt**"*.

**Đọc `qc.py` thì T4 là `am luong tich hop` — LUFS.** Nó không đọc một chữ nào,
không biết ngôn ngữ nào. Ngôn ngữ của giọng không vào được phép đo ấy.

Số thật:

```
T4   lufs = -15,07     đích = -14,0     dung sai = ±1,0     -> lệch 0,07 dB
```

🔑 Và **0,07 dB** mới là phát hiện, không phải chữ "hỏng". Đường ống đang giao
   âm lượng **ngay rìa** lời hứa của chính nó: bất kỳ thay đổi nhỏ nào cũng lật
   nó sang bên kia.

⭐ Chú thích trong `qc.py` đã gọi tên đúng cơ chế từ trước: pha 24 *"nhắm đúng
   trần −1,5 dBTP và giao −1,45 dBTP"*, và khoảng lệch ấy tìm ra được **chỉ vì
   đường ĐO khác đường SẢN XUẤT** — sản xuất chuẩn hoá bản master PCM, còn QC đo
   tệp AAC đầu ra. Đây là **cùng một hình dạng**, lần này ở trục loudness và ở
   đường CẮT (giải mã + mã hoá lại), nơi sai số có thêm một chặng để tích luỹ.

⛔ **Không nới `LUFS_DUNG_SAI`.** Nới một dung sai để một phép kiểm xanh là bỏ
   chính câu hỏi nó đang hỏi. Và `qc.py` đã ghi điều kiện để đổi T4: chỉ khi có
   một **quy cách bàn giao** thật, và khi đó T4 phải đọc tài liệu ấy chứ không
   đọc `tach_tieng`.

⚠️ Chưa đo được: một lượt với **giọng thật** có rơi vào đâu. Nếu bản thay thế
   (SAPI) có phổ khác đủ để đổi loudness sau khi trộn, con số thật có thể khác.
   Nói *"lỗi này cũng có ở đường thật"* lúc này là một suy luận, không phải một
   phép đo.

---

## 5. Việc còn lại, theo đúng thứ tự

1. **Một CSDL PostgreSQL vứt đi** → gỡ **B**. Cần thông tin đăng nhập, tức cần
   nâng quyền — quyết định của chủ dự án.
2. Chạy lại lượt nghiệm thu **trên PostgreSQL**, vẫn ghi ra ngoài kho, để xem
   **C** còn lại một mình hay không.
3. Đo T4 trên một lượt có **giọng thật** trước khi kết luận về nguyên nhân của
   0,07 dB.
4. Chỉ khi cả ba đường đều xanh mới sinh lại bằng chứng **trong kho** — và lượt
   ấy phải bật đủ `LTT_ASV_MODEL_THAT=1` + `LTT_ASV_POOL_URL` +
   `LTT_ASV_GIONG_THAT=1` + `LTT_VOICE_SIDECAR_TOKEN`, nếu không nó hạ cấp bằng
   chứng.

⭐ Và một câu hỏi mở của `BAN_GIAO.md` §2 nay đã có đáp án: cờ bật đường model
   thật là **`LTT_ASV_MODEL_THAT=1`**, kèm **`LTT_ASV_POOL_URL`** trỏ vào pool
   PostgreSQL thật (`tests/fixtures/asv_e2e.py:349-400`). Nó đọc `BIEN_POOL_URL`
   chứ **không** đọc `LTT_DATABASE_URL`, và docstring ở đó nói rõ vì sao.

---

## 6. ⛔ ĐÍNH CHÍNH 10/09 — lượt xanh KHÔNG chứng minh trần token đã đủ

Bản đầu của tệp này xếp **A** là *"đã vá"*. **Phát biểu ấy rộng hơn phép đo.**

Lượt nghiệm thu xanh (26 passed) khai `thay_the: 4`, trong đó có
`platform_core.llm.dieu_phoi.goi`. Nghĩa là `chuyen_loi_thoai` **chưa hề chạm
máy B**: nó gọi một bản thay thế, và một bản thay thế thì không có trần token
nào để chạm.

⇒ Lượt ấy chứng minh **B** (PostgreSQL) và **C** (loudness). Nó **không** nói
  được gì về việc 16.384 token có đủ cho đường thật hay không.

Đúng phải phát biểu tách làm hai:

| | trạng thái |
|---|---|
| đường truyền ngân sách (`goi_tinh_tien` → `goi` → `dieu_phoi.goi`) | ✅ đã thông, có `test_464` chốt |
| **giá trị** 16.384 / 300s có đủ không | ⚠️ **chưa đo trên đường thật** |

### ⚠️ Và một cảnh báo từ phiên khác, đủ nghiêm trọng để đo TRƯỚC

Phiên `workflow 4 bot` chuyển tiếp phép đo của `LLM LTT`: `predicted_n` chạm
**đúng** trần ở **cả** 3.000 lẫn 12.000, `content = 0` ở cả hai — nhân ngân sách
bốn lần mà vẫn ra **0 ký tự**. Nếu điều đó đúng cho prompt thật của
`chuyen_loi_thoai` thì **nâng trần sẽ không gỡ được `test_448`**.

🔑 **Một mảnh có thể còn thiếu trong phép đo ấy, và nó là câu hỏi chứ không phải
   kết luận:** trước thay đổi 10/09, `ai.goi_tinh_tien` — cửa **duy nhất** của
   mọi lần gọi có tính tiền, cửa mà cả bốn giai đoạn ASV đi qua — **không truyền
   `max_tokens`/`timeout_s` xuống**. `ai.goi` nhận hai tham số ấy từ 09/09,
   nhưng `goi_tinh_tien` gọi nó không kèm gì.

⇒ Nếu phép đo kia gọi thẳng `dieu_phoi.goi`/`ai.goi` với `--tran 3.000` rồi
  `12.000`, nó chạy trên một đường **ASV không dùng** — production luôn nhận
  mặc định 4.096 bất kể trần truyền vào. Chưa biết họ đo qua cửa nào.

### Việc phải làm TRƯỚC khi tiêu một lượt nghiệm thu 11 giai đoạn

Đo `nghi_tok / predicted_n` ở **hai** trần khác nhau, qua **`goi_tinh_tien`**
(không qua `dieu_phoi.goi` trực tiếp), trên prompt thật của `chuyen_loi_thoai`:

* nếu `content` > 0 ở trần cao và = 0 ở trần thấp ⇒ trần **là** nguyên nhân,
  16.384 đủ hay không thì con số nói;
* nếu `content` = 0 ở **cả hai** ⇒ trần **không** phải nguyên nhân, và
  `test_448` cần một chẩn đoán khác — nhiều khả năng là khối `<think>` hoặc
  `reasoning_effort`, thứ `20260909_tran_token_ra_chuyen_loi_thoai.md` §"Thứ
  KHÔNG làm" đã khoanh vùng sẵn.

⛔ Không chạy nghiệm thu toàn phần trước khi có hai con số đó: một lượt tiêu một
   suất máy B (`DONG_THOI_MAY_B = 1`) và chặn mọi phiên khác.

---

## 7. Prompt THẬT của `chuyen_loi_thoai` nhỏ hơn fixture 7,6 lần — đo 10/09

Phiên `LLM LTT` đo trên máy B, prompt thường, đầu vào **13.527 token**, 8 lượt,
hai trần (3.000 và 12.000): **4/8 lượt trả `content` rỗng**, hình dạng **lưỡng
cực** — lượt thành công dùng 561–1.197 token rồi tự dừng, lượt hỏng đốt trọn
ngân sách rồi trả rỗng, không lượt nào ở giữa.

Họ ghi rõ một giới hạn, và nó rơi đúng vào địa hạt này: *"chưa đo ở ngữ cảnh
ngắn nên chưa biết nó có phải đặc thù ngữ cảnh dài — prompt `chuyen_loi_thoai`
của ASV có thể ngắn hơn nhiều."*

**Đo được, dựng bằng chính `long_tieng.loi_nhac` trên dữ liệu nguồn thật của bộ
nghiệm thu:**

| cỡ lô | ký tự prompt | ước token |
|---|---|---|
| 4 | 2.389 | ~683 |
| 6 | 3.343 | ~955 |
| **12** (`DOAN_MOI_LO`) | **6.261** | **~1.789** |
| 24 | 12.069 | ~3.448 |

⇒ Lô đầy của ASV vào khoảng **1.800 token đầu vào**, tức **7,6 lần nhỏ hơn**
  fixture 13.527 token. Kết quả 4/8 **chưa được thiết lập** cho ngữ cảnh của
  ASV; muốn biết thì phải đo lại ở ~1.800 token.

⚠️ Và đây là đo **đầu vào**, còn hỏng nằm ở **đầu ra**. Kích thước đầu vào có
   dẫn tới hình dạng lưỡng cực hay không thì chưa ai đo. Đừng đọc bảng này
   thành *"ASV không dính"*.

### 🔴 Một mâu thuẫn giữa hai phép đo, và nó chặn một bản vá đang được đề nghị

| nguồn | prompt | lượt THÀNH CÔNG dùng bao nhiêu token RA |
|---|---|---|
| `3eae396d` (§lô 12) | prompt THẬT của `chuyen_loi_thoai`, lô 12 | **10.248 / 9.642 / 6.948**, `finish_reason=stop` |
| `LLM LTT` (10/09) | prompt thường, đầu vào 13,5K | **561 / 579 / 647 / 1.197**, `stop` |

Hai con số cách nhau một bậc. Chúng **không mô tả cùng một lời gọi**, nên không
được trộn.

⛔ **Hệ quả trực tiếp:** đề nghị *"hạ trần xuống 3.000, phát hiện rỗng, thử lại
   3 lần"* rút từ hàng dưới. Áp nó cho ASV thì trần **3.000 nằm DƯỚI** nhu cầu
   **10.248** mà hàng trên đo được — tức đặt trần dưới sàn nhu cầu, đúng cái
   hình dạng `phanh-luon-an-te-hon-khong-co-phanh` đã có tên trong kho: một
   trần dưới sàn biến thất bại thành **mặc định**, và ba lần thử lại đều cắt ở
   cùng chỗ.

⇒ Phép đo phải làm: chạy `chuyen_loi_thoai` **qua `goi_tinh_tien`**, prompt
  THẬT, lô 12, **nhiều lượt**, ghi `finish_reason` + `token_ra` + `len(content)`
  cho từng lượt. Hai câu hỏi cần tách:

  1. ở ngữ cảnh ~1.800 token, tỉ lệ `content` rỗng là bao nhiêu;
  2. lượt **thành công** thật sự dùng bao nhiêu token ra — 1.200 hay 10.248.

  Câu 2 quyết định trần; câu 1 quyết định có cần thử lại hay không. Đặt trần
  trước khi trả lời câu 2 là đoán.

---

## 8. 10.248 đến từ đường nào — và câu trả lời làm rõ cả tệp bằng chứng

Phiên `LLM LTT` chất vấn đúng chỗ: *"trước `6fcc39ed`, mọi lượt ASV nhận trần
4.096 bất kể truyền gì. Mà lượt thành công trong `3eae396d` dùng tới 10.248. Tức
những lượt ấy **không thể** đã đi qua `goi_tinh_tien`."*

**Kiểm được tại chỗ, không cần máy B:**

```
tools/do_ngan_sach_chuyen_loi_thoai.py:196   ai.goi(db, ai.CHUYEN_LOI_THOAI, msg,
                                                    max_tokens=args.tran, timeout_s=...)
tools/do_on_dinh_chuyen_loi_thoai.py:167     ai.goi(db, thao_tac, messages,
                                                    max_tokens=int(tran or 0))
```

⇒ Đúng: hai bảng ấy **không** đi qua `goi_tinh_tien`.

⭐ **Nhưng chúng đi qua `ai.goi` với prompt THẬT và trần tường minh — đúng đường
   mà `6fcc39ed` vừa làm cho production đi.** Chuỗi đầy đủ là
   `goi_tinh_tien` → `goi` → `dieu_phoi.goi`; mắt duy nhất bị đứt là mắt **đầu
   tiên**, và hai tool đo bắt đầu từ mắt **thứ hai**.

Nên 10.248 **không** phải "số của một đường không còn tồn tại". Nó là số của
đường production **vừa mới bắt đầu đi**. Điều kiện dùng nó, ghi rõ:

> Nó đo *"model muốn bao nhiêu khi được cho chỗ"*, **không** đo *"một lượt
> production thành công đã tiêu bao nhiêu"*. Trước `6fcc39ed` chưa từng có lượt
> production nào được cho chỗ, nên đại lượng thứ hai **không tồn tại** để đo.

### Hệ quả cho tệp bằng chứng đang đỏ

Trước `6fcc39ed`, mọi lượt `chuyen_loi_thoai` của production bị chặn ở **4.096**,
trong khi cùng prompt ấy qua `ai.goi` sinh **6.948–10.248** token khi được cho
chỗ. Lượt hỏng trong `nghiem_thu_hien_hanh.json` **nhất quán với cắt trần**.

⚠️ **Nhất quán, không phải chứng minh.** Bảng lưỡng cực của `LLM LTT` cho một cơ
   chế thứ hai giải thích **cùng một triệu chứng** (`content` rỗng), và không có
   cách phân biệt hai cái cho tới khi đo. Trần `16.384` giữ nhãn **chưa xác
   nhận**.

### Hai cải tiến phép đo, nhận từ `LLM LTT`

**1. Ghi cả `len(reasoning_content)`, không chỉ `len(content)`.** Trong bốn ca
hỏng của họ, `reasoning` đầy cả bốn (9.804–32.334 ký tự) — nhờ đó loại được
"token bị bộ giải mã bỏ" và "bị lọc mất". Nếu ở ~1.800 token vào mà `content`
rỗng **và** `reasoning` cũng rỗng thì đó là một chế độ **KHÁC**, và là một phát
hiện riêng. Gộp hai chế độ ấy thì phép đo nói dối.

**2. `finish_reason` KHÔNG dùng làm dấu hiệu hỏng.** Một ca hỏng của họ có
`finish = stop`, `pred_n = 8.938` trên trần 12.000 — thừa ngân sách, tự dừng
bình thường, vẫn rỗng.

⇒ Mỗi lượt ghi: `len(content)` · `len(reasoning_content)` · `token_ra` ·
  `finish_reason` · giây. **Bốn cột sau là MÔ TẢ; chỉ cột đầu là PHÁN QUYẾT.**
