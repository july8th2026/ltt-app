# B2 — Plan: dịch có NGỮ CẢNH, và đo bằng thứ ⛔ không cần ai chấm

> Chủ dự án nêu 26/09/2026: *"sử lý từng câu 1, hay gom danh sách các câu lại rồi
> gửi cho llm… tránh dịch từng câu 1 sẽ gặp lỗi về ngữ cảnh. ví dụ dịch
> ông/cháu/con/tôi/bạn."*
>
> Tệp này trả lời **hiện trạng đo được**, rồi đề ra plan. ⛔ Không chép lại
> `B2_DO_DICH_THAM_CHIEU.md` — hai giới hạn của bộ đo ở đó vẫn nguyên hiệu lực.

---

## 🔴 §0 ĐỊNH CHÍNH LỚN (26/09, sau khi agent Task 11 soi ra) — §1 ĐỌC SAI MODULE

⛔ **Toàn bộ §1 dưới đây phân tích `dich_thuat.py`, và module đó là ĐƯỜNG CHẾT.**
Chính kho nói ra bằng chữ:

```
thi_hanh.py:124   "dich_thuat.dich_ban_ghi khong con nguoi goi nao tu do."
van_ban.py:78     "Phien ban loi nhac cua dich_thuat._loi_nhac (⛔ duong CHET ...)"
```

Đường dịch **THẬT** của `content_process` là `long_tieng.loi_nhac` +
`ai.goi_tinh_tien(ai.CHUYEN_LOI_THOAI, ...)`. Và nó **đã có gần hết** những thứ §1
báo là thiếu:

| §1 nói "thiếu" | sự thật ở `long_tieng.py` |
|---|---|
| lô 20 đoạn | **`DOAN_MOI_LO = 12`** — nhỏ hơn *có ý*, vì mỗi đoạn ở đây **mang theo ngữ cảnh** (`long_tieng.py:79-85`) |
| ⛔ không có số giây | 🔴 **ĐÃ CÓ**: mỗi mục mang `thoi_luong_giay` (`long_tieng.py:233`). **C3 của plan này ĐÃ ĐƯỢC LÀM RỒI** |
| ⛔ không có ngữ cảnh trước/sau | **ĐÃ CÓ**: `ngu_canh_ke(tat_ca, vi_tri, ke=NGU_CANH_KE)` đưa các đoạn **giữ lại** liền trước/sau, *theo thứ tự bản ra* (`long_tieng.py:197-206`) |
| ⛔ không có ngân sách độ dài | **ĐÃ CÓ**: tính từ `ngon_ngu.ngan_sach_do_dai` với nhịp **đã đo** 3,35 âm tiết/giây (`long_tieng.py:52`) |
| ⛔ không chống lẫn id | **ĐÃ CÓ**: ghép theo **mã**, ⛔ không theo vị trí, và xử ca *"gửi 12 nhận 11"* (`long_tieng.py:29`) |
| ⛔ không nhất quán thuật ngữ | **ĐÃ CÓ** một luật riêng cho ca *"hơi buồn / buồn man mác / sad / u sầu"* (`long_tieng.py:38`) |
| tăng `PHIEN_BAN_LOI_NHAC_DICH` | ⛔ **SAI HẰNG SỐ** — đó là phiên bản của lời nhắc **CHẾT**. Đường sống có hằng số riêng (`long_tieng.py:49`) |

### 🔑 Điều gì trong §1 vẫn ĐÚNG

**Cửa sổ ngữ cảnh là bản GỐC, ⛔ không phải bản ĐÃ DỊCH.** `ngu_canh_ke` trả
`d["chu"]` — chữ **nguồn** của các đoạn kề. ⇒ Lô 2 thấy *câu tiếng Trung* của lô 1,
nhưng ⛔ **không thấy lô 1 đã dịch `你` thành "cháu"**. Nên **chẩn đoán cốt lõi vẫn
sống**: ranh giới lô là một bức tường **cho QUYẾT ĐỊNH dịch**, dù ⛔ không phải cho
ngữ cảnh nội dung.

Và **hồ sơ dịch toàn cục** thật sự thiếu: `y_canh` là ghi chú **theo từng đoạn**
(`QUY_TAC_Y_CANH`), ⛔ không phải một bảng đại từ chốt **một lần cho cả video**. ⇒
`ho_so_dich` (Task 11) ⛔ **không** trùng `y_canh`.

### ⚠️ Vì sao tôi sai, và bài học

Tôi `grep dich_thuat`, đọc kỹ module đó, **nhưng ⛔ không bao giờ kiểm AI GỌI nó**.
Đúng cái bẫy đã ghi trong sổ dự án: *"đọc thứ đại diện thay vì đọc thứ thật — thứ
tôi đang hỏi có SẴN ở chỗ tôi đang đứng không?"* Một module đọc rất thuyết phục vẫn
có thể ⛔ không nằm trên đường nào.

⇒ **Luật thêm vào cho mọi phân tích sau:** trước khi kết luận về một module, chạy
`grep -rn "<ten_module>\." --include=*.py apps/` và **đếm người gọi**. ⛔ Không có
người gọi thì ⛔ không có kết luận.

---

## 1. Hiện trạng — đã gom lô, nhưng ⛔ KHÔNG mang ngữ cảnh qua ranh giới lô

Đọc `apps/auto_scan_video/dich_thuat.py`, ⛔ không suy diễn:

| câu hỏi | sự thật trong mã |
|---|---|
| Từng câu hay theo lô? | **Theo lô**, `DOAN_MOI_LO = 20`, giữ nguyên thứ tự |
| Vì sao 20? | chú thích tự khai: *"một con số **CHƯA ĐO** trên dữ liệu thật"* |
| Gộp kết quả thế nào? | tất định, khoá theo `ma` đoạn ⇒ ⛔ không có phép đối chiếu theo thứ tự |
| Thiếu đoạn thì sao? | `_doc_ban_dich` **ném** kèm `n/tổng` ⇒ bắt được |
| Lô sau có biết lô trước đã dịch gì? | 🔴 **KHÔNG.** `dich_mot_lo` **vô trạng thái** — mỗi lời gọi chỉ có `{ma: chữ}` của đúng lô đó |
| Có nhãn người nói? | 🔴 **KHÔNG** — `ban_ghi.py:45` rút `phan_vai`/`nguoi_noi` ngày 22/09 |
| Lời nhắc nói gì về độ dài? | *"Giữ độ dài **gần** với câu gốc"* — ⛔ **không một con số nào** |
| Có bảng tên riêng / bảng đại từ? | quy tắc 5 đòi *nhất quán*, nhưng **phạm vi chỉ trong một lô** |
| `tu_dien` của khách có vào lời nhắc dịch? | **KHÔNG** — đó là từ điển **cách ĐỌC** tên riêng, dùng ở giai đoạn khác |

### 🔑 Chẩn đoán đúng ⛔ không phải "dịch từng câu"

Ta **đã** gom lô — nên phần chủ dự án lo đã được giải **một nửa**. Nửa còn lại
hỏng nặng hơn và khó thấy hơn: **ranh giới lô là một bức tường**.

```
lô 1 (đoạn 1–20)   : model quyết 你 -> "cháu"          <- ⛔ không ai ghi lại
lô 2 (đoạn 21–40)  : model KHÔNG BIẾT lô 1 quyết gì  -> "cậu"
lô 3 (đoạn 41–60)  :                                 -> "bạn"
```

⇒ Một video 74 đoạn đi **4 lô** ⇒ **4 lần** quyết lại quan hệ nhân vật, độc lập
nhau. Tiếng Việt mã hoá **quan hệ** vào đại từ, nên đây ⛔ không phải lỗi phong
cách: người xem nghe thấy quan hệ **đổi giữa video**.

Cùng cơ chế với ca đã đo: `光子 -> "Photon"` (`B2_DICH.md §4.1`) — nhất quán tên
riêng chỉ được bảo đảm **trong** một lô.

### 🔴 Mắt xích làm nó vô hình: nhãn người nói bị rút vì "không ai đọc"

`ban_ghi.py:45`:

> *"Bằng chứng người nói (`phan_vai`/`nguoi_noi`) ĐÃ RÚT 22/09 — sản phẩm là MỘT
> giọng thuyết minh, **không bộ phận nào đọc nhãn người nói**, phân vai chỉ tốn
> GPU."*

Lý do đó **đúng cho việc chọn giọng**. Nhưng bộ phận *cần* nhãn ấy là **bản dịch**,
và nó ⛔ không đọc vì nó **chưa từng được xây để đọc**. ⇒ Một trường bị bỏ vì
"không ai dùng", trong khi người cần dùng là người **chưa được xây**. Cùng hình
dạng với con bọ làn giọng (26/09) và với `cho-noi-hai-module-vut-truong-im-lang`.

---

## 2. Đo trước — và cố ý ⛔ KHÔNG dùng sân đấu LLM

`B2_DO_DICH_THAM_CHIEU.md` tự khai: chân lý nền là **hai người soi đều là LLM**,
kappa 0,714 với KTC95 `[0,00 ; 1,00]` ⇒ *"chân lý nền chưa bao giờ được ghim"*.
⛔ Nên plan này **không** treo phán quyết của mình vào sân đấu đó.

⭐ **Và nó không cần.** Khuyết điểm chủ dự án nêu ⛔ không phải câu hỏi về **gu** —
nó là **mâu thuẫn bên trong một tài liệu**, và mâu thuẫn **đếm được**:

| cổng | đếm cái gì | cần bản tham chiếu? | cần ai chấm? |
|---|---|---|---|
| **G1 — nhất quán đại từ** | số **bộ đại từ khác nhau** dùng cho cùng một cặp vai trong một video. Đạt = **1** | ⛔ không | ⛔ không |
| **G2 — nhất quán tên riêng** | một token tên gốc ra **đúng một** dạng tiếng Việt; vi phạm đếm được | ⛔ không | ⛔ không |
| **G3 — vừa khe** | số đoạn đọc ra **dài hơn** khe của nó | ⛔ không | ⛔ không |

🔑 Ba cổng này **tự do khỏi vòng tròn LLM**, vì chúng ⛔ không hỏi *"bản dịch có hay
không"* — chúng hỏi *"bản dịch có **tự mâu thuẫn** không"*. Một bộ chấm sai gu vẫn
đếm mâu thuẫn đúng.

⚠️ G1 đòi một **danh sách đóng** các từ xưng hô tiếng Việt (ông/bà/anh/chị/em/cháu/
con/cô/chú/bác/tôi/tớ/mình/tao/mày/bạn/cậu/quý vị/các bạn…). Danh sách đó là **dữ
liệu ngôn ngữ**, ⛔ không phải phán quyết chất lượng — nên nó được phép gõ ra, và nó
**kiểm được** bằng cách soi lại trên bản ghi thật.

⭐ G3 có thêm một tính chất quý: nó **dự báo THỜI GIAN**. Mỗi đoạn tràn khe = một
lượt nắn = **15,6–17,7 giây** (đo 26/09, `qwen38-api`, mức nghĩ `low`). ⇒ G3 là
cổng duy nhất vừa đo **chất lượng** vừa đo **giá**.

---

## 3. Plan — ba thay đổi, **cùng hoặc ít hơn** số lời gọi LLM

### C1 — một lượt "HỒ SƠ DỊCH" cho CẢ video (**+1** lời gọi, ~16 giây)

Gửi **toàn bộ** dòng chữ gốc (74 đoạn ≈ vài nghìn token, thừa sức một lời gọi) và
xin về một JSON nhỏ:

```json
{"the_loai": "vlog", "so_nguoi_noi": 1,
 "vai": {"A": "nguoi dan (chu kenh)", "KHAN": "nguoi xem"},
 "bang_dai_tu": {"A->KHAN": {"toi": "minh", "goi": "cac ban"}},
 "bang_ten_rieng": {"光子": "Quang Tu", "李宗盛": "Ly Tong Thinh"},
 "giong_van": "than mat"}
```

⇒ Quan hệ được quyết **MỘT lần cho cả video**, thay vì mỗi lô quyết lại.

### C2 — mỗi lô mang HỒ SƠ + cửa sổ trượt (**+0** lời gọi)

`_loi_nhac(lo, ngon_ngu_goc, ho_so, da_dich_truoc_do)`:

- `bang_dai_tu` và `bang_ten_rieng` vào lời nhắc **dưới dạng DỮ LIỆU** kèm câu
  *"dùng ĐÚNG bảng này"*.
  ⛔ **Không** thêm ví dụ mới. Bài học đã ghi: *ví dụ trong lời nhắc là mệnh lệnh
  ngầm* — 4 ví dụ không dấu từng làm tụt một tên vốn đúng.
- **2–3 cặp (gốc, dịch) cuối của lô trước**, nhãn rõ *"đã dịch — giữ nhất quán"*.

Chi phí: **+~300 token mỗi lô**, ⛔ không thêm một lời gọi nào.

### C3 — mỗi đoạn mang SỐ GIÂY của khe (**+0** lời gọi, và **giảm** lượt nắn)

`{ma: {"chu": "…", "giay": 3.2}}` + một quy tắc **có số**.

🔑 Chính `nan_cho_vua.loi_nhac_nan` đã viết ra nguyên tắc này: *"khác biệt giữa
'hãy viết ngắn hơn' và 'câu này đọc ra 4,8 giây, khe có 3,2 giây…': cái sau cho
model một **mục tiêu kiểm được**, và nó là lý do **vòng thứ hai thường không cần
đến**."* ⇒ Nguyên tắc **đã có**, chỉ đang được áp ở chỗ **ĐẮT** (sửa từng đoạn,
16 s/lượt) mà ⛔ không áp ở chỗ **RẺ** (dịch theo lô, cùng số lời gọi).

### Đo lại `DOAN_MOI_LO` (nay 20, tự khai CHƯA ĐO)

Có hồ sơ + cửa sổ rồi thì lô **to hơn** đỡ mất nhất quán hơn, nhưng lô to thì một
phản hồi hỏng mất nhiều hơn. Đo 10 / 20 / 40 trên **hai phim thật** theo G1–G3 +
số lần `_doc_ban_dich` ném.

---

## 4. Ràng buộc bắt buộc khi thi hành

1. ⛔ Đổi lời nhắc **PHẢI** tăng `van_ban.PHIEN_BAN_LOI_NHAC_DICH` (nay `5`) — nó
   nằm trong vân tay; thiếu thì lần chạy mới **dùng lại kết quả của lời nhắc CŨ**.
2. ⛔ Sửa lời nhắc thì **đo lại CẢ tập**, không chỉ ca vừa sửa.
3. Lớp **TÍNH** của bộ đo dùng thư viện tải về; ta chỉ viết phần **NỐI**. G1/G2/G3
   là phép **đếm**, nên chúng là phần nối — ⛔ không phải một bộ chấm mới.
4. `THU_TU_PROVIDER` vẫn **một** tên. ⛔ Không thêm dự phòng im lặng.

---

## 5. Thứ tự, và vì sao chất lượng đi TRƯỚC tốc độ

Vòng nắn 16 giây/đoạn là **triệu chứng** của việc bản dịch ⛔ không biết ngân sách
thời gian. ⇒ C3 sửa **cả hai**: ít mâu thuẫn hơn **và** ít lượt nắn hơn.

```
1. G1/G2/G3 (cổng, ⛔ không cần ai chấm)   <- thiếu nó thì mọi câu sau là cảm giác
2. C1 hồ sơ dịch        (+1 lời gọi/video)
3. C2 hồ sơ + cửa sổ    (+0)
4. C3 số giây mỗi đoạn  (+0, giảm lượt nắn)
5. Đo lại DOAN_MOI_LO
6. CHỈ SAU ĐÓ: nắn song song (≤2 request) · tách "quyết chữ" khỏi "đọc tiếng"
```

---

## 6. Câu phải hỏi chủ dự án — ⛔ dữ liệu không trả lời hộ

Với phim **nhiều nhân vật** mà sản phẩm chỉ có **MỘT giọng thuyết minh**: bản dịch
có phải giữ đại từ **giữa các nhân vật** (*"con thưa bố…"*), hay chuyển hết sang
lời **kể lại** của một người dẫn?

- Giữ đại từ nhân vật ⇒ người xem hiểu quan hệ, nhưng một giọng đọc hai vai nghe
  **lẫn**.
- Chuyển sang lời kể ⇒ mạch rõ, nhưng **mất** sắc thái quan hệ.

⇒ Đánh đổi **sản phẩm** (khách nhận gì), ⛔ không phải một con số. Và nó quyết định
luôn việc có bật lại `diarize` hay không: **chỉ hướng thứ nhất** mới cần nhãn người
nói, tức mới đáng tốn GPU.
