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
| **A** | `content_process` | trần token 4.096 < nhu cầu 10.248 | ✅ **đã vá** — xem §2 |
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
