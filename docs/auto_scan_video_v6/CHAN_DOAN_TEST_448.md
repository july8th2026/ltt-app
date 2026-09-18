# `test_448` — bảy màu đỏ, và ba nguyên nhân KHÁC NHAU

> ⚠️ **Ảnh chụp 10/09/2026** (tệp này) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

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

## 9. Cả HAI rào cũ đều dưới sàn — và biên an toàn của rào MỚI hẹp hơn tôi tính

Phiên `ltt-llm-api-http-guide` đo bốn lượt ở **1.891 token vào** — đúng cỡ lô 12
của `chuyen_loi_thoai`, prompt thường, trần 12.000:

```
luot  pred_n   finish  content  reasoning   giay
  1    9.831   stop        0     22.016    140,1
  2      499   stop      787      1.199      9,9
  3    9.886   stop    1.022     23.885    142,0
  4   10.508   stop      978     24.810    150,5
```

Đối chiếu với hai rào mà `test_448` chạy dưới:

| rào cũ | số đo được | bị cắt |
|---|---|---|
| `max_tokens` = 4.096 | `pred_n` 9.831 · 9.886 · 10.508 | **3/4** |
| `timeout` = 120 s | 140,1 · 142,0 · 150,5 giây | **3/4** |

⇒ Đây là đối chứng **độc lập** cho §2: hai đường khác nhau (họ gọi thẳng
`POST /v1/chat/completions` ở 8299; ta đi qua `goi_tinh_tien` → `goi` →
`dieu_phoi.goi` với pool + `secretbox`), cùng một kết luận. Và nó xác nhận
`tran-dat-duoi-san-nhu-cau-o-hai-tang` bằng phép đo ở **cả hai** tầng thay vì đo
một tầng rồi suy tầng kia.

### ⛔ ĐÍNH CHÍNH: "dư 56 %" là một con số có PHẠM VI, và tôi đã nói nó không kèm phạm vi

Commit `2ed99b9d` viết *"giá trị tôi đặt (16.384 / 300s) dư 56 % và ~2× so với
nhu cầu đo được"*. **56 % ấy tính so với 10.508 — mức cao nhất ở ngữ cảnh
NGẮN.** Ở ngữ cảnh **dài** (13.527 token vào), cùng bảng đo của họ có:

```
tran 12.000   pred_n = 12.000   finish = length    <- CHAM TRAN
tran  3.000   pred_n =  3.000   finish = length
tran  3.000   pred_n =  3.000   finish = length
```

Model **có** chạm trần khi được cho 12.000 chỗ. Nên nhu cầu thật của lượt ấy là
**≥ 12.000**, và vì nó bị **cắt** nên ta **không biết** nó cần bao nhiêu.

⇒ Biên đúng phải viết là: **≥12.000 so với 16.384, tức dư ≤36 %, và cận dưới ấy
  là một cận KHÔNG ĐO ĐƯỢC** — không phải một con số.

⭐ Đây đúng hạng lỗi `pham-vi-phep-do-hep-hon-loi-tuyen-bo`, và lần này nó nằm
   trong một commit của chính tôi. Câu *"model không chạm trần khi được cho
   chỗ"* đúng cho bốn lượt ngắn và **sai** cho lượt dài; tôi phát biểu nó như
   một tính chất của model.

### 🔑 Hệ quả cho sản phẩm: `finish_reason` phải vào SỔ VẬN HÀNH

Hai triệu chứng khác hẳn nhau, cùng biểu hiện ra ngoài là *"lô hỏng"*:

```
finish = length                    -> TRAN CON THAP        -> nới trần
finish = stop  +  content rỗng     -> CHE DO RONG          -> thử lại
```

`ai.goi` đã trả về `finish_reason` và `suy_nghi` từ 09/09. Nhưng
`goi_tinh_tien` ghi sổ cái chỉ với `token_vao` / `token_ra` / `model` — **hai
trường chẩn đoán ấy không được lưu ở đâu cả**. Tức năng lực có, không ai đi trên
đường: sau này, khi không còn ai ngồi đo, không có cách nào phân biệt hai chế độ
từ dữ liệu vận hành.

⇒ Ghi `finish_reason`, độ dài `content` và độ dài `suy_nghi` vào `ghi_chu` của
  bút toán. Nó rẻ, nó không đổi một quyết định nào, và nó là **báo động duy
  nhất** phân biệt được hai bản sửa.

### ⚠️ Và nới trần là CẦN chứ chưa ĐỦ

Lượt 1 của bảng trên: `finish = stop`, `pred_n` 9.831, `content` **rỗng** — ở
ngữ cảnh ngắn, dưới trần. Tức chế độ rỗng xảy ra **cả khi không rào nào bị
chạm**. 1/4 ở đây, 4/8 ở ngữ cảnh dài; `n` quá nhỏ để nói hai ngữ cảnh khác
nhau, nhưng đủ để nói **nới trần không xoá được chế độ này**.

⇒ Một lượt `test_448` xanh sau khi nới vẫn là một đồng xu — đúng điều §6 đã tự
  đính chính. Không báo "đã vá" dựa trên một lượt xanh.

### ⛔ Và bản THỬ LẠI của ASV không được là một vòng `for`

Đường của họ gọi thẳng cổng nên không có bút toán nào. `goi_tinh_tien` thì ghi
sổ cái ở **cả ba** nhánh (đã giao / từ chối / mơ hồ), có chủ đích — xem
docstring của nó. Một `retry` ngây thơ đặt quanh lời gọi sẽ ghi **hai** bút toán
cho một việc khách nhận **một** lần.

⇒ Phép thử lại phải nằm **trong** một lần ghi sổ, không phải hai lời gọi cạnh
  nhau. Đây là ràng buộc thiết kế, không phải một chi tiết hiện thực.

## 10. 🔴 Rào THỨ BA nằm dưới sàn — và nó rộng gấp 6 lần

§9 nới hai rào của **một lời gọi** (trần token, timeout lời gọi). Câu chưa ai
hỏi: *một lần chạy có bao nhiêu lời gọi, và chúng có kịp trong trần của JOB
không?*

Số học, mọi hằng số lấy **từ mã**, không gõ tay:

```
tran video nhan vao   : 120 phut   (nhap_media.THOI_LUONG_TOI_DA_S)
doan moi lo           : 12         (long_tieng.DOAN_MOI_LO)
tran job content_proc : 60 phut    (manifest.max_runtime_s)
giay/lo do duoc       : p50 142,0  cao nhat 150,5   (do 10/09, LLM LTT)
```

| mật độ đoạn | số đoạn | số lô | giây (p50) | vượt trần job |
|---|---:|---:|---:|---|
| thưa (10/phút) | 1.200 | 100 | 14.200 | **CÓ** |
| vừa (15/phút) | 1.800 | 150 | 21.300 | **CÓ** |
| dày (20/phút) | 2.400 | 200 | 28.400 | **CÓ** |

⇒ Ở p50, chỉ **25 lô** lọt trần job — tức ~300 đoạn, tức **~20 phút video**.

**ASV nhận 120 phút. `content_process` chỉ chạy hết được ~20 phút.** Gấp **6
lần**, và đây là rào rộng nhất trong ba rào đã tìm ra.

### Hai điều kiểm rồi mới nói, vì cả hai đều có thể lật kết luận

**1. Các lô chạy TUẦN TỰ.** `giai_doan_noi_dung.py:147` là một `for` thẳng —
không `gather`, không worker pool. Và ngay cả khi có, máy B chỉ có **một suất
đồng thời** (`DONG_THOI_MAY_B=1`), nên các lời gọi vẫn xếp hàng. Phép nhân ở
trên là đúng phép.

**2. Vượt trần job KHÔNG được thử lại.** `test_217::test_job_vuot_tran_khong_duoc_thu_lai`
chốt `jobq.fail(..., retry=False)` → `JOB_ERROR`, kết thúc.

⇒ Nên đây **không** phải "chậm hơn dự kiến". Đây là *"video dài hơn ~20 phút
  không hoàn thành được"*, và khách nhận một lần chạy hỏng.

### ⚠️ Ba giới hạn của con số này — nói ra để không ai trích nó quá phạm vi

1. **142 giây/lô đo trên đường KHÁC.** Phiên `LLM LTT` gọi thẳng
   `POST /v1/chat/completions` ở 8299; đường của ASV đi qua `goi_tinh_tien` →
   `dieu_phoi` với pool + `secretbox`. Chưa ai đo đường của ASV — đó chính là
   phép đo đang bị chặn.
2. **Mật độ đoạn là ƯỚC, không phải đo.** 10–20 đoạn/phút là khoảng hợp lý cho
   lời thoại, nhưng bản nghiệm thu hiện hành chỉ có **6 đoạn**, quá ít để suy.
3. **Giai đoạn CÓ nối lại.** `su_dung.da_xong` + `_lay_lai_doan_da_xong` bỏ qua
   đoạn đã xong, nên một lần chạy lại **thủ công** tiến thêm được. Khách không
   mất trắng — họ mất một lần chạy và phải tự bấm lại.

### ⛔ Và vì sao KHÔNG nâng trần job ngay

Nâng `max_runtime_s` lên 2 giờ là để **một job giữ một suất worker suốt 2
giờ**. Đó là một quyết định tài nguyên, không phải một dòng cấu hình — và kho
này đã ghi rằng một cái phanh đặt sai chỗ ăn tệ hơn không có phanh, ở **cả hai
chiều**.

Ba đường có thật, và chọn giữa chúng cần số của phép đo đang bị chặn:

| đường | đổi cái gì | rủi ro |
|---|---|---|
| hạ trần video nhận vào | 120 phút → ~20 phút | thu hẹp sản phẩm, nhưng **trung thực** |
| chia `content_process` thành nhiều job | mỗi job vài lô | phức tạp thêm ở tầng hàng đợi |
| nâng `max_runtime_s` | 60 → 120+ phút | một job giữ worker rất lâu |

⇒ Việc đúng lúc này **không** phải chọn. Là ghi nó ra, và đo `giây/lô` trên
  đường thật của ASV — cùng lô đo đang chờ suất máy B.

## 11. ✅ ĐO XONG — trần token LÀ nguyên nhân, và nhu cầu nằm TRÊN trần cũ ở MỌI lượt

Lô đo `do_on_dinh_nang_quyen.ps1` chạy 10:29–10:44 trên đường thật của ASV
(`ai.goi` → `dieu_phoi.goi` → pool + `secretbox` → máy B). **5 vòng × 3 cánh =
15 lượt.**

```
canh                 tran      luot  xong  bi cat   token ra (min/p50/max)   vuot 4.096
THAT/tran-job         4.096      5     1      4      3.844 / 4.096 / 4.096      0/5
THAT/tran-rong(DC)   12.288      5     5      0      4.186 / 6.091 / 6.843      5/5
NGAN/tran-job(DC)     4.096      5     5      0        799 / 1.133 / 1.296      0/5
```

### 🔑 Cánh đối chứng là thứ chứng minh, không phải cánh chính

Ba cánh khác nhau **đúng một biến mỗi lần**:

* `THAT/tran-job` và `THAT/tran-rong` — **cùng lời nhắc, cùng đầu vào**, chỉ
  khác trần. 4.096 hỏng 4/5; 12.288 xong 5/5.
* `THAT/tran-job` và `NGAN/tran-job` — **cùng trần**, chỉ khác cỡ đầu vào.
  Đầu vào ngắn xong 5/5 ở đúng cái trần làm đầu vào dài hỏng.

⇒ Trần không sai *nói chung*. Nó sai **cho cỡ đầu vào của `chuyen_loi_thoai`**.
  Điều này giết giả thuyết *"lời nhắc hỏng"* và giả thuyết *"máy B ốm"* cùng
  lúc — cả hai sẽ làm cánh `NGAN` hỏng theo.

### 🔴 Và con số đắt nhất: nhu cầu thật là **4.186 – 6.843** token

Cánh trần-rộng **không bị cắt lần nào**, nên số của nó là nhu cầu **thật**, không
phải một cận dưới. Và **5/5 lượt đều vượt 4.096**.

⇒ Trần cũ không "hơi chật". Nó nằm **dưới sàn nhu cầu ở mọi lượt**, và lượt duy
  nhất sống sót (3.844) sống vì tình cờ, không vì đủ chỗ. Đúng nghĩa đen của
  `phanh-luon-an-te-hon-khong-co-phanh`: thất bại là **mặc định**, thành công là
  ngoại lệ may mắn.

Giá trị đặt ở `6fcc39ed` — **16.384** — dư **2,4×** so với mức cao nhất đo được.

### ⚠️ Cái KHÔNG thấy, và nó cũng là một kết quả

Trong 15 lượt **không có lượt nào `stop` + `content` rỗng**. "Chế độ rỗng lưỡng
cực" mà phiên `ltt-llm-api-http-guide` đo được ở đường khác (1/4 ở ngữ cảnh
ngắn) **không xuất hiện**.

⛔ n=15 nên đây **không** phải bằng chứng nó không tồn tại. Nó chỉ nói: trên
   đường của ASV, ở cỡ đầu vào này, **mọi** thất bại quan sát được đều là
   `length` — tức có **một** nguyên nhân cần vá, không phải hai.

⭐ Và `finish_reason` là thứ phân biệt được hai chế độ ấy — đúng cột đã nối vào
   sổ cái ở `a0666981`. Nếu chế độ rỗng xuất hiện ở production sau khi nới trần,
   dữ liệu vận hành sẽ nói ra thay vì phải dựng lại một lô đo.

### Ba con số phụ đáng giữ

| | |
|---|---|
| giây/lượt ở trần cũ | 61–72 s (không phải 140–150 s — số đó ở **1.891** token vào, lô này **595**) |
| giây/lượt ở trần rộng | 63–103 s — dài hơn vì nó được phép nghĩ hết |
| khối suy nghĩ | 8.221–15.603 ký tự; lượt bị cắt đều ở ~9.700 |

⇒ Trần timeout 300 s (đặt cùng lúc ở `6fcc39ed`) dư **~3×** so với lượt dài
  nhất đo được.

### ⛔ Lô dừng ở 5/12 vòng, và lý do là lỗi quy trình của tôi

Tiến trình chết khi phiên Claude kết thúc. Memory `lo-do-dai-tren-may-b` đã ghi
đúng điều này — *"phải dùng Scheduled Task; ssh và `Start-Process` đều chết theo
phiên"* — và tôi vẫn dùng `Start-Process -Verb RunAs` cho một lô 32 phút.

⭐ Không đổi kết luận (5/5 ở cánh đối chứng là dứt khoát), nhưng nó mất phần
   **tỉ lệ**: với n=5, "4/5 hỏng ở trần cũ" là một ước lượng thô, không phải một
   tỉ lệ. Ai cần con số ấy thì chạy lại **qua Scheduled Task**.
## 12. ✅ ĐÓNG — `test_448` xanh ở độ trung thực đầy đủ, và bằng một mệnh đề DƯƠNG

```
26 passed, 1 skipped, 0 failed        (22:46, ghi luc 2026-09-10T12:49:22)
giong_that = True   model_that = True   thay_the = []
```

### Mệnh đề dương, đọc từ chính tệp bằng chứng chứ không từ dòng `RESULT`

| cánh | giai đoạn | `tai_ve` | `qc` | `chuyen_loi_thoai` |
|---|---|---|---|---|
| `giu_hinh` / `localize_preserve_picture` | **11/11** | 200, 2.193.981 B | đạt, 13/13 mục | **5.768** token |
| `cat_thong_minh` / `smart_localize` | **11/11** | 200, 1.837.772 B | đạt, 13/13 mục | **4.961** token |

`ma_nguoi_khac = 404` cả hai (ranh giới sở hữu giữ), `doi_soat.khop = True`,
`tu_choi = 0`, mỗi cánh 6 mục lồng tiếng bằng `LTTStudioVoice` thật ở `:8120`.

⭐ Đây là điều mục 11 hứa mà chưa làm được: mục 11 đo **nhu cầu** trên một
   đường riêng; mục này cho thấy **đúng giai đoạn từng hỏng nay chạy qua**, trên
   đường thật, với model thật và PostgreSQL thật.

### 🔑 Hai con số ấy giết luôn cách đọc "trần cũ hơi chật"

Cả **5.768** và **4.961** đều **trên** trần cũ 4.096, và cả hai rơi đúng vào cửa
sổ nhu cầu **4.186–6.843** đo được ở mục 11.

⛔ Nhưng phần đắt nhất là so với lượt **09/09**: chính cánh `cat_thong_minh` khi
   ấy dùng **3.985** token và **lọt** — dưới trần cũ. Hôm nay cùng cánh, cùng
   đầu vào, dùng **4.961** và sẽ **vượt**.

⇒ Với trần 4.096, cánh ấy không hề "an toàn" — nó là một **đồng xu**; cánh kia
  thì hỏng chắc. Đúng nghĩa đen `phanh-luon-an-te-hon-khong-co-phanh`: thất bại
  là **mặc định**, và lượt xanh 09/09 là một **ngoại lệ may mắn**, không phải
  bằng chứng trần đủ dùng. Ai chạy lại hôm ấy và thấy cánh đó xanh sẽ kết luận
  sai — `chay-lai-mot-phep-kiem-do-khong-phai-bang-chung`.

### Vì sao tệp bằng chứng cũ đỏ, nói cho gọn

Tệp cũ ghi lúc **2026-09-09 12:31**, tức **trước** commit `6fcc39ed`
(2026-09-10 03:22) nới trần 4.096 → 16.384. Hai cánh nằm hai phía đúng cái trần
đó. Không có bug nào trong đường ống; có một **rào đặt dưới sàn nhu cầu**.

⚠️ Phạm vi của câu kết luận này, và nó hẹp hơn nó nghe: nguyên nhân của **các
   cánh này**, ở **cỡ đầu vào này**, là trần token — `finish_reason = length`.
   Nó **không** giải thích chế độ `stop` + nội dung rỗng mà phiên
   `ltt-llm-api-http-guide` đo được ở ngữ cảnh 13.487 token, nơi model tự kết
   thúc với **3.062 token ngân sách còn thừa**. Hai cơ chế khác nhau tình cờ in
   ra cùng một chuỗi `chuyen_loi_thoai: model tra ve rong`. Nới trần chữa cái
   thứ nhất và **vô ích** với cái thứ hai.

⇒ Cột `finish_reason` nối vào sổ cái ở `a0666981` là thứ phân biệt hai cơ chế
  ngay trong dữ liệu vận hành, không cần dựng lại một lô đo.

### ⛔ Lượt 11:47 hỏng vì tranh tài nguyên — và nó dạy một bài không về ASV

Lượt trước đó (ghi lúc 11:47) có `giu_hinh` **11/11** nhưng `cat_thong_minh`
chết ở `voice_synthesis` với năm lần `BanError: May tao tieng dang ban`. Cổng
giọng `:8120` là semaphore **một suất, không hàng đợi**
(`voice_sidecar/engine.py:_Cong`), và một phiên khác đang chạy một lô đo trên đó.

🔑 Cơ chế đáng ghi **không** phải "hai phiên tranh nhau" mà là hình dạng của
   chúng. `DangBanTam` mang `retry_after_s`, nên job ASV lùi lại theo nhịp
   **20 / 20 / 167 / 20 / 10** giây; trong quãng lùi cổng rảnh và vòng lặp chặt
   của bên kia lấy được; job ASV quay lại thì cổng đầy.

⇒ **Một semaphore không hàng đợi thì không phân xử — nó chỉ từ chối.** Nó không
  biết ai đã chờ bao lâu, nên thứ nó chọn là *ai nhanh tay hơn*: một vòng lặp
  chặt **luôn** thắng một job biết lùi, và bên lịch sự thua **có hệ thống**.
  Chỉ một khoá ở tầng trên mới biến điều đó thành *ai tới trước*.

Lượt 12:26 xin bốn khoá `cua_so_yen` — `cpu_nhieu`, `may_b`, `may_tao_tieng`,
`postgres_test` — kèm chốt **fail-closed** (hết giờ chờ thì bỏ cuộc với mã 75,
KHÔNG chen). Đối chứng: `voice-err.log` chỉ có **40 dòng trong 17 phút** sau
12:21, so với 6–9 dòng **mỗi phút** khi lô kia chạy. Khác đúng một biến:

```
11:39-11:47  khong khoa  -> mat voice_synthesis mot canh (va ben kia mat 19/20)
12:26-12:49  co khoa     -> 11/11 va 11/11, khong mot 429 nao
```

### ⚠️ Và một đường chết thứ hai, không liên quan gì tới ASV

Lượt 11:19 chạy **dưới Scheduled Task** — đúng thứ memory `lo-do-dai-tren-may-b`
yêu cầu — mà vẫn chết ở phút **6,5** với
`LastTaskResult = 0xC000013A = STATUS_CONTROL_C_EXIT`: một **sự kiện điều khiển
console**. Thủ phạm chưa quy được vì log
`Microsoft-Windows-TaskScheduler/Operational` mặc định **tắt**.

⇒ Scheduled Task là điều kiện **cần, chưa đủ**. Bản chạy được dùng `pythonw.exe`
  (không cấp phát console), con sinh với `CREATE_NO_WINDOW |
  CREATE_NEW_PROCESS_GROUP`, `AllowHardTerminate = $false`, và **nhịp tim 15
  giây** — chính nhịp tim cho ra con số "phút 6,5", thứ làm cả chẩn đoán này khả
  dĩ. Đã cập nhật memory `lo-do-dai-tren-may-b`.

⛔ Và đừng đọc `Get-ScheduledTask … State` thành kết quả: `Ready` là trạng thái
   của một lượt **đã kết thúc**, không phân biệt kết thúc kiểu nào. Câu trả lời
   ở `(Get-ScheduledTaskInfo …).LastTaskResult`.
