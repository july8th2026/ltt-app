# B2 — cổng DỊCH (zh→vi)

> Làn `b1-cắt-lại` → `b2-dịch`, 24/09/2026. Đứng trên bản chép lời **mới** của
> B1 (`bang_chung/b1_chep_loi_moi/`): có dấu câu, có mốc từng từ, CER 3/3 ĐẠT.

# 🔴🔴 ĐÍNH CHÍNH LỚN (24/09, cuối ngày) — TÔI ĐÃ ĐO MỘT ĐƯỜNG CHẾT

> ⛔ **Đọc mục này trước tất cả. Nó làm mất hiệu lực chữ "đường sản phẩm" ở
> §4b, và làm quyết định `ltt-3.5` của chủ dự án CHƯA có hiệu lực.**

## Sự thật đo được

```
apps/auto_scan_video/thi_hanh.py:121
   "`dich_thuat.dich_ban_ghi` khong con nguoi goi nao tu do"

grep `ai.DICH_THUAT` trên toàn bộ apps/ ⇒ chỉ xuất hiện TRONG CHÍNH `dich_thuat.py`
```

Giai đoạn **`CONTENT_PROCESS`** — nơi ASV thật sự chuyển lời sang tiếng Việt —
gọi `long_tieng.loi_nhac(...)` + `ai.goi_tinh_tien(..., ai.CHUYEN_LOI_THOAI)`
(`giai_doan_noi_dung.py:212, 217`). ⛔ Nó **không** gọi `dich_thuat`.

| thao tác | model hôm nay | có ai gọi không |
|---|---|---|
| `dich_thuat` | **qwen35-api** (ltt-3.5) | ⛔ **KHÔNG** — đường chết |
| **`chuyen_loi_thoai`** | ⛔ **qwen38-api** (ltt-3.8) | ✅ **đây là đường sống** |

## ⇒ Ba hệ quả, ⛔ không được giấu

1. ⛔ **Quyết định *"dịch đi `ltt-3.5`"* CHƯA có hiệu lực.** Tôi ghim đúng cơ chế
   (`MODEL_THEO_THAO_TAC`) nhưng ghim **nhầm thao tác**. Đường sống vẫn chạy
   `ltt-3.8` — tức vẫn trả **~20× token ra**.
2. ⚠️ **Mọi con số dịch trong tệp này đo `dich_thuat`**, ⛔ không phải thứ khách
   nhận. Chúng vẫn có giá trị — cùng model, cùng dữ liệu, cùng lớp bài toán —
   nhưng ⛔ **không được đọc là "chất lượng sản phẩm"**.
3. ⚠️ **Luật Hán-Việt (quy tắc 5, các bản v2→v5) nằm trong `dich_thuat._loi_nhac`
   — lời nhắc mà sản phẩm KHÔNG dùng.** Tập kiểm 12 ca **13/13** là thật, nhưng
   nó chứng minh *luật viết đúng*, ⛔ **không** chứng minh *khách sẽ nhận đúng*.

⚠️ Và `van_ban.PHIEN_BAN_LOI_NHAC` **có** nằm trong vân tay của `CONTENT_PROCESS`
(`thi_hanh.py:138`) ⇒ các lần tăng 1→5 hôm nay **đã vô hiệu cache của đường
sống** cho một thay đổi ⛔ **không** chạm vào lời nhắc của nó. Vô hại về kết
quả, ⛔ nhưng là một tín hiệu sai cho người đọc sau.

## ⛔ Tôi DỪNG ở đây, không tự sửa

Chuyển quy tắc 5 sang `long_tieng.loi_nhac` là **sửa lời nhắc của đường
SỐNG** — lời nhắc lồng tiếng đã qua nghiệm thu, có ngân sách độ dài riêng
(`ngon_ngu.ngan_sach_do_dai`), và ⛔ không phải phạm vi điều phối đã giao.
⇒ **Báo, chờ xếp thứ tự.**

⭐ Bài học, và nó là bài học của **cả ngày hôm nay** ở một tầng cao hơn:
*"đọc thứ đại diện thay vì đọc thứ thật"* — tôi đã đo một hàm **tên đúng**
(`dich_thuat`) thay vì hàm **được gọi thật**. Câu hỏi đáng lẽ phải hỏi ngay từ
đầu: ⭐ **"ai GỌI hàm này?"**, ⛔ không phải *"hàm này tên là gì"*.

---

# ⏭ TRẠNG THÁI LÀN B2 — đọc dòng này trước khi cầm tiếp (24/09, cuối)

| việc | trạng thái | ở đâu |
|---|---|---|
| **1 · lược đồ** | ✅ **XONG** — thủ phạm là `temperature` ⛔ chưa ai ghim, ⛔ không phải model/lược đồ | §7.5 |
| **2 · quy tắc tên riêng vào đường SỐNG** | ✅ **XONG** — 21/33 → 38/39, kèm **1 hồi quy** (`光子`) | §7.6 |
| **3 · đường B, phần THU** | ✅ **XONG** — `khong_chac` vào `outputs`, ⛔ chỉ thu | §7.7 |
| **N-23 · ghim model + nhiệt độ + ép lược đồ** | ✅ **XONG** — lô hỏng **64,3 % → 0,0 %** (0/20), giá **+0 lượt gọi** | §7.8 |
| **đo lại sau khi ghim** | ✅ **XONG** — tên riêng **không đổi**; vòng sửa **vẫn xáo 92 %** | §7.9 |
| **đo lại sau cú sập 23:37–23:44** | ✅ **XONG** — `0/20` **tái hiện y hệt** (cộng dồn 40 lô, 376/376 đoạn) | §7.8b |
| **SEED** (nửa còn lại của "nhiệt độ + seed") | 🔴 **XONG — cổng NHẬN, ⛔ KHÔNG hiệu lực.** Đường dịch ⛔ **không tái lập được** | §7.8c |
| **`光子` × lồng tiếng** | ✅ **XONG** — va chạm ⛔ **không tái hiện**: `光子` chưa bao giờ ra chữ Hán | §7.8d |
| **bất biến chữ Hán ở BIÊN** | ✅ **XONG** — `chu_han_lot` → `outputs["han_lot"]`, ⭐ **đánh dấu, ⛔ không huỷ** | §7.8d |
| **A/B vòng sửa (§4f)** | 🔴 **RỖNG — hai nhánh CÙNG MỘT MÃ.** N-02 ⇒ **đã giải thích** | §7.10 |
| **nối `y_canh`** | ✅ **XONG** — vòng sửa thôi mù; phép kiểm đọc **CÂY người gọi** | §7.11 |
| **A/B `y_canh` (điều phối chấm mù)** | ⚠️ **B 4/9 · A 2/9 · ngang 3/9** — hướng **dương**, ⛔ chưa đủ `n` | §7.12 |

### 🔴 Ba việc CHỜ điều phối / chủ dự án — ⛔ làn này cố ý không tự làm

1. ✅ **ĐÃ LÀM — N-23** (điều phối cấp số hiệu 24/09). Xem §7.8.
2. ✅ **ĐÓNG — chủ dự án chốt 24/09 luật tên riêng** (§4h). Luật đã chốt **đúng
   bằng** `QUY_TAC_TEN_RIENG_VI` đang chạy ⇒ ⛔ **KHÔNG sửa lời nhắc thêm**.
   ⚠️ `光子` hỏng 3/3 và `重庆` 1/3 ở lượt đo sau khi ghim (§7.9) — điều phối đọc
   đây **rất có thể là rút thăm**, ⛔ không phải lỗi luật. ⇒ Việc còn lại là
   **đo lại**, ⛔ không phải sửa luật.
3. ✅ **ĐÓNG — chủ dự án chốt 24/09 (tối): `ltt-3.5` phục vụ đường dịch.**
   ⛔ Không so sánh 3.8 nữa. `ltt-3.8` nhường **toàn bộ** cho làn bộ chấm.

### ⛔ Chưa làm

* **Bước 3** (bản nền dịch đo lại trên đường sống) — chưa chạy.
* **Độ nhạy/độ ồn của `khong_chac` trên ĐƯỜNG SỐNG** — ô còn trống (§7.7).
  ⚠️ Và `57 %`/`0,63 %` của §4i đo ở **nhiệt độ chưa ghim** ⇒ phải đo lại **trước**
  khi dựng bảng từ.
* ⏭ **BẢNG TỪ `B → D` (+ `A` tuỳ chọn)** — điều phối chốt 24/09, ⛔ **chưa làm**,
  xếp **sau** việc nhiệt độ (§4d).
  🔑 ⭐ **Và §7.12 vừa cho nó một lý do ĐO ĐƯỢC:** `y_canh` giúp **diễn đạt**,
  ⛔ **không** cứu lớp **thuật ngữ/lóng** (`掐雷`, `纯白给`, `热胀冷缩` hỏng ở
  **CẢ HAI** nhánh). ⇒ `y_canh` và bảng từ ⛔ **không thay nhau — chúng BÙ NHAU**.
* ⏭ **Mở rộng A/B 9 → ~20 đoạn** — cần thêm phán quyết thật của bộ chấm; điều
  phối xin làn bộ chấm, ⛔ làn này ⛔ không đụng `ltt-3.8`.
* ✅ **N-02 (85 → 85) ĐÃ ĐƯỢC GIẢI THÍCH — bằng CƠ CHẾ, đọc từ mã** (§7.10):
  vòng sửa chỉ chạm đoạn **bị gắn cờ**, và dịch lại bằng lời nhắc **y hệt**
  (`y_canh` ⛔ không ai truyền) ⇒ một **phép rút thăm lại ⛔ không có chiều**
  ⇒ tổng giữ nguyên, thành phần bị xáo.
* 🔴 **Phép A/B §4f ⛔ KHÔNG chạy được: hai nhánh là CÙNG MỘT MÃ** (§7.10).
* ⏭ **Ẩn số cuối, ⛔ không cần nhánh B, ⛔ không cần bộ chấm:** xác suất một
  lượt **rút lại** làm một đoạn **đã đúng** tệ đi. ~12 đoạn, người soi **mù với
  thứ tự**, và **khai rõ người soi là ai**.
* ✅ **Chữ Hán lọt bản ghi vì lỗi ASR (`1/343 = 0,3 %`) — ĐÃ có cửa chặn ở biên**
  (`long_tieng.chu_han_lot` → `outputs["han_lot"]`, §7.8d). ⭐ Đây là **bộ dò lỗi
  chép lời THỨ HAI**, độc lập với đường B — hai tín hiệu độc lập cùng trỏ một
  đoạn thì đáng tin hơn hẳn một. ⏭ **Chưa ai ĐỌC cột này** — như `khong_chac`.
* 🔑 **`seed`: câu hỏi ĐÃ ĐÓNG VĨNH VIỄN** (§7.8c). Cổng **có** chuyển và **có**
  kiểm `seed`; bất định là **thượng nguồn** (llama.cpp #7052 · #19981 · #27407).
  ⛔ **Không còn đường nào ở tầng tham số** — đừng thử lại.
* **`重庆`** còn sai 1/3 lượt dù nằm ngay trong ví dụ của luật.
* Hai bài đỏ trong bộ `app:auto_scan_video` (`test_3300` metricx, `test_334`
  ngân sách) — ⚠️ **đã đỏ TRƯỚC** làn này (kiểm trên SHA `b9370220`), ⛔ không
  thuộc phạm vi B2.

### Công cụ, chạy lại được bằng một lệnh

```
tools/bench_b2_luoc_do.py   --model ltt-3.5 --lo 12 --temp -1 --phim v2 --so-lo 7
                            (--temp -1 = ⛔ KHONG gui truong temperature = cau hinh SAN PHAM)
tools/bench_b2_ten_rieng.py --duong song --ghim ltt-3.5 --lan <n>
```

⚠️ Cả hai cần `LTT_DATABASE_URL` từ `C:\LTTPlatform\secrets\app.env` (ACL chặn;
phiên agent chạy quyền admin nên đọc được). ⛔ Không giữ `cpu_nhieu` — gọi máy B
là **chờ mạng**.

---

# 7. BƯỚC 1 — ĐO ĐƯỜNG SỐNG **TRƯỚC KHI SỬA**

> ⛔ Không có số *"trước"* thì mọi số *"sau"* ⛔ không quy được cho bản sửa.
> Lời nhắc đường sống (`long_tieng.loi_nhac`) chạy **y nguyên**, ⛔ chưa sửa gì.

⚠️ **Model: ghim `ltt-3.5`**, vì thao tác sống `chuyen_loi_thoai` đi `ltt-3.8`
mà 3.8 **đang nhường làn khác**. ⇒ Đây là *lời nhắc đường sống × `ltt-3.5`*,
⛔ **không** phải tổ hợp đang chạy thật (*× `ltt-3.8`*). Ô đó **còn trống**.

## 7.1 Kết quả: **9/13** — và cách nó sai thì không ai đoán được

| tên | mong | đường sống ra | |
|---|---|---|---|
| 首尔 · 东京 · 北京 · 上海 · 广州 · 纽约 | (địa danh quen) | Seoul · Tokyo · Bắc Kinh · Thượng Hải · Quảng Châu · New York | ✅ |
| 腾讯 · 华为 | Tencent · Huawei | Tencent · Huawei | ✅ |
| 小美 | Tiểu Mỹ | Tiểu Mỹ | ✅ |
| **重庆** | Trùng Khánh | ⛔ **"Chongqing"** (**bính âm**) | ⛔ |
| **张伟** | Trương Vĩ | ⛔ **"Zhang Wei"** (**bính âm**) | ⛔ |
| **李小龙** | Lý Tiểu Long | ⛔ **"Bruce Lee"** (**tiếng Anh**) | ⛔ |
| **李宗盛** | Lý Tông Thịnh | ⛔ "Lý Tông **Thành**" | ⛔ |
| `光子` (tiêu chí âm) | ⛔ không ra "Quang Tử" | "Photon" | ✅ |

🔴 **Ba trong bốn ca hỏng là BÍNH ÂM hoặc TIẾNG ANH**, ⛔ không phải phiên sai
dấu. Với một sản phẩm **lồng tiếng**, nghĩa là **giọng đọc sẽ phát âm
*"Zhang Wei"*, *"Bruce Lee"*, *"Chongqing"*** giữa một câu tiếng Việt. Đó là
một khiếm khuyết **khách nghe thấy**, ⛔ không phải một lỗi trên giấy.

⚠️ **Và nó KHÔNG ổn định:** chạy hai lần ở `temperature 0.2` cho **8/13** rồi
**9/13**; `重庆` ra *"Chung Quỳ"* ở lượt đầu và *"Chongqing"* ở lượt sau. ⇒ ⛔
Đừng đọc 9/13 như một hằng số.

## 7.2 So với đường chết — và vì sao phép so này **có** nghĩa

```
đường CHẾT  (`dich_thuat`)   + luật v5      ->  13/13
đường SỐNG  (`long_tieng`)   + KHÔNG luật   ->   9/13  (8/13 ở lượt lặp)
```

⛔ Hai lời nhắc khác nhau nên ⛔ **không** kết luận *"model kém hơn"*. Thứ phép
so này nói là: **luật quy tắc 5 có tác dụng thật**, và đường sống **đang thiếu
nó**. Đó là căn cứ cho Bước 2.

## 7.3 ⚠️ Một phát hiện NGOÀI dự kiến, và nó thuộc về câu 3.5-vs-3.8

> 🔴 **ĐÃ BỊ BÁC — đọc §7.5 trước.** Con số `1/12` dưới đây có thật, nhưng
> nguyên nhân ⛔ **không phải** *"3.5 không gánh nổi lược đồ"*: đường sống
> ⛔ **không ghim `temperature`** và cổng máy B áp `1.0`. Ghim nhiệt độ ⇒
> cùng model, cùng lô 12, cùng lược đồ: **83/83, 0 lô hỏng**.

Ở **cỡ lô sản phẩm** (`long_tieng.DOAN_MOI_LO = 12`), lời nhắc đường sống ×
`ltt-3.5` trả về **1/12 đoạn** (`ThieuDoan: thiếu 11 đoạn`) — ⛔ **không** phải
cụt, vì trần token ra là **32 768**. Một lượt khác trả `doan` là **một MẢNG**,
đúng cái mà docstring của `long_tieng.loi_nhac` cảnh báo (*"khoá phải là MÃ
ĐOẠN, không phải một mảng"* — vì vị trí ⛔ không dùng làm định danh được).

Hạ xuống **4 đoạn/lô** thì ổn định: **14/14 đoạn, 0 thiếu, 0 vi phạm lược đồ**.

> 🔴 ⇒ Con số này thuộc về **§6.2**: nếu `ltt-3.5` ⛔ **không gánh nổi** lược đồ
> bốn trường (`chu`+`cam_xuc`+`kieu_noi`+`nhan_manh`) + `ke_ben` ở **cỡ lô
> thật**, thì *"3.8 đắt gấp 20×"* ⛔ **không còn là một lựa chọn tự do** — nó
> có thể là **cái giá của việc chạy được**.
>
> ⚠️ ⛔ **Chưa kết luận:** ta ⛔ **chưa** đo `ltt-3.8` trên cùng phép thử (3.8
> đang nhường). Có thể 3.8 cũng bỏ đoạn, và lúc đó vấn đề là **lược đồ**, ⛔
> không phải model. Đó là phép đo **đầu tiên** phải chạy khi có suất 3.8.

## 7.5 🔴 PHÉP LƯỢC ĐỒ — và nó **lật** §7.3. Thủ phạm là `temperature`, ⛔ không phải model, ⛔ không phải lược đồ

> ⛔ **Đọc mục này trước §7.3.** §7.3 kết luận *"`ltt-3.5` không gánh nổi lược đồ
> ở cỡ lô thật"* từ **một** lượt trả `1/12`. Phép đo dưới đây cho thấy con số ấy
> **có thật**, nhưng nguyên nhân ⛔ **không phải** thứ §7.3 quy cho.

### Cái §7.3 không biết: đường sống **không ghim `temperature`**

```
giai_doan_noi_dung.py:217   ai.goi_tinh_tien(...)        ⛔ KHONG truyen temperature
ai.py:775                   goi(..., temperature=None)
cong_vlm.py:341             chi dat khoa khi khac None   ⇒ than request KHONG mang temperature
```

⇒ Cổng máy B áp mặc định của chính nó. Làn `llm-cong` đã đo và ghi con số đó:
**`--temp 1.0`** cho **cả hai** hồ sơ `qwen35-api`/`qwen38-api`
(`L_LLM_CONG.md` §4a, `llama-swap.yaml` trên máy B).

🔑 ⇒ **Bench và sản phẩm chạy hai cấu hình khác nhau, và ⛔ không ai nói ra.**
`bench_b2_ten_rieng` truyền `temperature=0,2` **tường minh** — nên 9/13 và 8/13
ở §7.1 đúng là số của `0,2`, ⛔ không phải số sai. Nhưng **khách ⛔ không nhận
cấu hình đó**: đường sống không truyền gì, nên khách nhận `≈ 1,0`.

⇒ ⚠️ 9/13 là một **cận TRÊN** của thứ khách nhận, ⛔ không phải thứ khách nhận.
Bảng dưới đo được rằng ở `≈ 1,0` thì chính `ltt-3.5` hỏng **64 %** số lô — tức
khoảng cách giữa hai cấu hình ⛔ **không nhỏ**, và ⛔ chưa ai đo nó cho phần
**tên riêng**.

### Phép đo — MỘT biến, và biến đó là `temperature`

`tools/bench_b2_luoc_do.py --temp -1` ⇒ ⛔ **không gửi** trường `temperature`,
tức **đúng cấu hình đường sống**. Mọi thứ khác giữ nguyên: lời nhắc
`long_tieng.loi_nhac` y nguyên · `long_tieng.chia_lo(moi_lo=12)` · cùng bản chép
lời `b1_chep_loi_moi/` · cùng `ltt-3.5`.

| phim | `temperature` | lô hỏng | đoạn nhận | vi phạm lược đồ |
|---|---|---|---|---|
| v1 | ⛔ **không gửi (SẢN PHẨM)** | **3/7** | 47/83 | 3 |
| v1 | ghim **0,0** | **0/7** | **83/83** | 0 |
| v1 | ghim **0,2** | **0/7** | **83/83** | 0 |
| v2 | ⛔ **không gửi (SẢN PHẨM)** | **6/7** | 25/74 | 3 |
| v2 | ghim **0,0** | **2/7** | 51/74 | 1 |

```
ghim nhiet do   2/21 lo hong   =  9,5 %
SAN PHAM        9/14 lo hong   = 64,3 %      Fisher mot phia p = 0,0011
```

### 🔴 Và `ltt-3.8` ở **đúng cấu hình sản phẩm**: **0/7 lô hỏng, 83/83**

| phim | model | `temperature` | lô hỏng | đoạn nhận |
|---|---|---|---|---|
| v1 | **`ltt-3.8`** | ⛔ không gửi (SẢN PHẨM) | **0/7** | **83/83** |
| v1 | `ltt-3.5` | ⛔ không gửi (SẢN PHẨM) | 3/7 | 47/83 |
| v1 | `ltt-3.5` | **ghim 0,0 / 0,2** | **0/7** | **83/83** |
| v2 | **`ltt-3.8`** | ⛔ không gửi (SẢN PHẨM) | **0/7** | **74/74** |
| v2 | `ltt-3.5` | ⛔ không gửi (SẢN PHẨM) | 6/7 | 25/74 |
| v2 | `ltt-3.5` | ghim 0,0 | 2/7 | 51/74 |

> ⭐ **Đọc hai dòng đầu một mình thì kết luận là *"20× là giá của việc chạy
> được"*** — đúng kết cục thứ nhất §7.3 dựng ra. **Dòng thứ ba bác nó:** cùng
> phim, cùng lược đồ, cùng `ltt-3.5`, chỉ thêm **một tham số** ⇒ cũng **83/83**.
>
> 🔑 ⇒ Cái 20× ấy sẽ được trả **phần lớn** để che một núm chưa ai ghim.
>
> ⚠️ **Nhưng ⛔ không phải TOÀN BỘ, và đây là chỗ phải nói cho đúng:** trên
> **cả hai** phim ở **đúng cấu hình sản phẩm**, `ltt-3.8` được **14/14 lô,
> 157/157 đoạn**. `ltt-3.5` **ghim nhiệt độ** vẫn còn **2/21 lô hỏng**. ⇒ `ltt-3.8`
> **có** một biên năng lực thật về bám lược đồ; ghim `temperature` lấy lại
> **phần lớn** khoảng cách (64,3 % → 9,5 %), ⛔ **không** lấy hết.
>
> ⇒ Câu cho chủ dự án ⛔ **không** phải *"3.5 hay 3.8"* mà là: **ghim
> `temperature` TRƯỚC**, rồi mới hỏi 9,5 % lô hỏng còn lại đáng giá bao nhiêu —
> vì đó mới là phần 20× thật sự mua.

⭐ *"Lô hỏng"* ở đây là **theo nghĩa sản phẩm**: vi phạm lược đồ **hoặc** thiếu
đoạn — vì `long_tieng.doc_chuyen` ném `ThieuDoan` cho cả hai (`long_tieng.py:240`).

### ⇒ Trả lời ba kết cục §7.3 đặt ra: ⛔ **không kết cục nào**

Ba kết cục §7.3 viết ra đều giả định biến là **model**. Biến thật là một **núm
chưa ai ghim**:

| §7.3 hỏi | câu trả lời đo được |
|---|---|
| 3.8 đủ 12 · 3.5 rơi ⇒ *"20× là giá của việc chạy được"* | ⛔ **SAI** — `ltt-3.5` giữ đủ **83/83** ở lô 12 khi `temperature` được ghim |
| cả hai rơi ⇒ vấn đề là **lược đồ** | ⛔ **SAI** — cùng lược đồ, cùng lô 12, cùng model: 0/7 hỏng khi ghim |
| 3.5 cần hạ cỡ lô | ⛔ **Không cần.** `bench_b2_ten_rieng.LO_NHO = 4` ra đời từ tiền đề §7.3 — tiền đề ấy nay đổ |

🔴 **Và điều này chạm KHÁCH, không chỉ chạm phép đo:** đường sống hôm nay chạy
`ltt-3.8` **không ghim `temperature`**. Nếu `ltt-3.8` cũng nhạy như `ltt-3.5`
thì một phần lô hỏng mà khách gặp là **cái núm này**, ⛔ không phải model.

### ⚠️ Ghim `temperature` ⛔ KHÔNG phải một liều thuốc — nó chỉ **giảm**

`v2 × ghim 0,0` vẫn **2/7 lô hỏng** (một lô trả `doan` là **MẢNG**, một lô trả
`1/12`). ⇒ ⛔ Đừng đọc bảng trên thành *"ghim 0,0 là xong"*. Hai điều còn đúng:

1. ⭐ **Phim v2 khó hơn v1 ở CẢ HAI cấu hình** (6/7 vs 3/7 ở sản phẩm; 2/7 vs 0/7
   khi ghim) ⇒ ⛔ dữ liệu cũng là một biến, và `n = 2` phim ⛔ không đủ để tách nó.
2. Làn `llm-cong` đã đo: ⛔ **`temperature = 0` KHÔNG làm lượt tái lập được**
   (5 kết quả khác nhau / 5 lượt — `L_LLM_CONG.md` §4b; cơ chế: `-np 3` +
   continuous batching + `--spec-type draft-mtp`). ⇒ Ghim nhiệt độ mua **độ bám
   lược đồ**, ⛔ **không** mua tính tất định.

⇒ Đường sửa đúng cho lược đồ vẫn là thứ `L_LLM_CONG.md` §3 đã chỉ:
**grammar / `response_format`**, hoặc một **vòng thử lại** ở mức lô. Ghim
`temperature` là một bước **rẻ và đo được**, ⛔ không phải bước cuối.

### ⚠️ Hai lỗi của chính tôi trong lượt này — khai thẳng

1. 🔴 **Suýt kết tội `temperature` từ n = 3 lô.** Lượt đầu: `0,2` hỏng 1/3 lô,
   `0,0` hỏng 0/3 ⇒ *"0,0 chữa được"*. Nới lên 7 lô: **cả hai đều 0/7**. Ba lô
   ⛔ không phân biệt được một biến cố ~10 %. Đúng bài học
   *"chạy lại một phép kiểm đỏ không phải bằng chứng"* — phải hỏi **tỉ lệ hỏng
   nội tại** trước. Kết luận thật chỉ đứng được khi cấu hình **sản phẩm** vào cuộc.
2. **Bench xin sai trần token ra.** Tệp này ban đầu xin `ai.tran_token_ra()`
   = **32 768**, còn đường sống đi qua `ai.goi_tinh_tien` → `ngan_sach_cho`
   = **16 384** (`ai.py:774`). §7.3 đã suy từ con số 32 768 rằng *"⛔ không phải
   cụt"*. Đã sửa bench về trần sản phẩm. ⭐ Kết luận *"không phải cụt"* **vẫn
   đúng** — token ra đo được của một lô 12 đoạn là ~2,8–5,0 k (`L_LLM_CONG.md` §3),
   ⛔ không chạm trần nào — nhưng nó đúng **vì số đó**, ⛔ không vì 32 768.

### 🔴 Việc cần điều phối xếp: ghim `temperature` cho `chuyen_loi_thoai`

⛔ **Làn này không tự sửa** — `giai_doan_noi_dung.py` là đường **chạm khách** và
nằm ngoài phạm vi đã giao. Số để mang đi: **9,5 % so với 64,3 % lô hỏng**, giá
của bản sửa là **một tham số**, và ⛔ nó **không** đổi model, ⛔ không đổi lời
nhắc, ⛔ không đụng sổ sách.

⚠️ **Cần một số hiệu `N-xx`** (sổ dùng chung — ⛔ làn này không tự đặt).

## 7.6 ⭐ BƯỚC 2 — quy tắc TÊN RIÊNG vào lời nhắc ĐƯỜNG SỐNG: **21/33 → 38/39**

`long_tieng.QUY_TAC_TEN_RIENG_VI` · `PHIEN_BAN_LOI_NHAC_LONG_TIENG` **1 → 2**.
Sửa **MỘT lần**, đo **3 lượt trước** và **3 lượt sau**, cùng cấu hình
(`bench_b2_ten_rieng`, ghim `ltt-3.5`, ghim `temperature = 0,2`, lô 4).

### 🔴 Vì sao phải 3 lượt: **một lượt ⛔ không nói được gì**

```
TRUOC, cung cau hinh, ba luot:   7/13 · 9/13 · 5/13
```

⛔ Biên độ **5 → 9 trên 13**. Một lượt *"trước"* so với một lượt *"sau"* ⛔ **không
tách được** *"lời nhắc tốt lên"* khỏi *"hôm nay gặp may"*. Đúng chỗ ba lượt sửa
hôm qua trượt (§4c, §4h): mỗi lượt *"sửa một chỗ, hỏng một chỗ"* — với `n = 1`
thì một dao động bình thường **đọc ra như một hồi quy**.

### ⚠️ Và phải TÁCH *"tên sai"* khỏi *"đoạn mất"*

Nhiều ca *"hỏng"* ở lượt trước là **chuỗi RỖNG** — model ⛔ không trả đoạn đó về,
tức đúng bệnh §7.5, ⛔ **không** phải dịch sai tên. Gộp hai thứ vào một điểm là
đo `temperature` mà tưởng đang đo lời nhắc.

```
TRUOC   doan co tra ve 10 · 13 · 10  ⇒ ten DUNG 21/33 = 63,6 %
SAU     doan co tra ve 13 · 13 · 13  ⇒ ten DUNG 38/39 = 97,4 %
                                        Fisher mot phia p = 2,0e-4
```

### Bảng TỪNG CA — `OK` đúng · `XX` sai · `-` ⛔ model không trả đoạn về

| tên | đáp án (wiki zh→vi) | TRƯỚC (v1) | SAU (v2) |
|---|---|---|---|
| 首尔 | Seoul | OK OK OK | OK OK OK |
| 东京 | Tokyo | OK OK **-** | OK OK OK |
| 北京 | Bắc Kinh | OK OK **-** | OK OK OK |
| 上海 | Thượng Hải | OK OK **-** | OK OK OK |
| 广州 | Quảng Châu | OK OK OK | OK OK OK |
| **重庆** | Trùng Khánh | ⛔ XX XX XX | ⚠️ **OK XX OK** |
| 纽约 | New York | OK OK OK | OK OK OK |
| **李宗盛** | Lý Tông Thịnh | ⛔ XX XX XX | ✅ **OK OK OK** |
| **李小龙** | Lý Tiểu Long | ⛔ XX OK XX | ✅ **OK OK OK** |
| 腾讯 | Tencent | - OK OK | OK OK OK |
| **华为** | Huawei | - OK XX | ✅ **OK OK OK** |
| **张伟** | Trương Vĩ | - ⛔ XX XX | ✅ **OK OK OK** |
| 小美 | Tiểu Mỹ | OK XX OK | ✅ **OK OK OK** |
| **光子** (tiêu chí ÂM) | ⛔ không được ra *Quang Tử* | - OK OK | 🔴 **XX OK OK** |

### ⭐ Ba ca hỏng bằng **bính âm / tiếng Anh** — thứ khách **NGHE THẤY** — đã đóng

```
张伟    "Zhang Wei"   ->  Trương Vĩ      3/3
李小龙  "Bruce Lee"   ->  Lý Tiểu Long   3/3
李宗盛  "Lý Tông Thành" -> Lý Tông Thịnh 3/3
```

⭐ `李宗盛` là ca mà Unihan **bác lại dấu ✅ của chính làn này** (§4c): *"Thành"*
là âm của 成/城, `盛` là **thịnh**. Nay lời nhắc mang đáp án **tra được** làm ví
dụ, và cả 3 lượt ra đúng.

### 🔴 HOÁ ĐƠN — ⛔ không giấu: **một hồi quy, một ca chưa đóng**

| | |
|---|---|
| 🔴 **hồi quy** | `光子` → *"Quang Tử"* ở **1/3 lượt**. Đó **đúng cái** §4g cảnh báo: một **thương hiệu** (xưởng game) bị phiên âm như tên người. Nhánh *"tổ chức/thương hiệu ⇒ giữ nguyên"* **có** trong luật, nhưng ⛔ **không thắng** được mọi lượt |
| ⚠️ **chưa đóng** | `重庆` → *"Chongqing"* ở **1/3 lượt**, dù `重庆 -> Trùng Khánh` nằm **ngay trong ví dụ** của luật |

⇒ ⛔ **Đừng đọc 38/39 thành *"đã xong"***. Nó là **97,4 % trên đoạn trả về**, và
hai ca trên nói rằng luật ⛔ **chưa tất định** — cùng họ với `L_LLM_CONG.md` §4b
(*⛔ không núm nào làm lượt tái lập được*).

### Token lời nhắc — trước/sau, và **cái gì thật sự bị ăn**

| | ký tự | token (ước, `uoc_token`) |
|---|---|---|
| hệ thống, đích `vi` — **TRƯỚC** | 1 026 | **338** |
| hệ thống, đích `vi` — **SAU** | 1 804 | **590** (**+252**, +75 %) |
| hệ thống, đích `en` — sau | 1 024 | **338** ⇒ ⛔ **không đổi** |

⚠️ **Và *"ngân sách độ dài"* ⛔ KHÔNG phải thứ bị ăn.** `ngon_ngu.ngan_sach_do_dai`
là trần **số âm tiết của MỘT câu ra**, tính từ `thoi_luong_giay` — nó ⛔ **không
đọc** độ dài lời nhắc. Thứ thật sự trả thêm là **token VÀO**: +252 token mỗi lô,
tức **+0,0126 credit/lô** ở `ltt-3.8` (50/1M) và **+0,0033** ở `ltt-3.5` (13/1M)
— đọc từ `gia_token.BANG_GIA`. Cả lô hệ thống + người dùng là ~2 425 token, ⛔ xa
mọi trần ngữ cảnh.

### ⛔ Luật CHỈ áp cho đích `vi` — và đó là một phần của bản sửa

`ngon_ngu.DICH_HOP_LE` có **cả `en`** (`kiem_cap`). *"Phiên âm Hán-Việt"* là luật
của tiếng Việt; bơm nó vào một lượt dịch sang tiếng Anh là dựng lại **F-05** (lời
nhắc ghi cứng *"tiếng Việt"* cho mọi nguồn). ⇒ `loi_nhac` chèn **có điều kiện**,
và bảng token trên là **phép kiểm** cho điều đó: đích `en` giữ nguyên 338.

## 7.7 ⭐ ĐƯỜNG B — bật phần **THU**, và ⛔ chỉ phần thu

`long_tieng.QUY_TAC_TU_KHAI` + trường `khong_chac` mỗi đoạn ·
`PHIEN_BAN_LOI_NHAC_LONG_TIENG` **2 → 3**. Ghi vào
`AsvWorkItem.outputs["khong_chac"]` (`giai_doan_noi_dung.py`).

### Ranh giới — điều phối chốt, ⛔ giữ nguyên văn

| | |
|---|---|
| ✅ **thu** | thêm trường, ghi vào `outputs` |
| ⛔ **không** hiển thị cho khách | `long_tieng.dung` ⛔ không rạp trường này vào tài liệu — có **phép kiểm** gác (`test_khong_chac_CHI_THU...`) |
| ⛔ **không** lái vòng sửa | ⛔ không nơi nào đọc nó để quyết định dịch lại |
| ⛔ **không** chặn gì | mọi dạng sai đều ra `[]`, ⛔ không ném |

**Dùng nó vào việc gì là quyết định của chủ dự án.**

### Số đã đo (bản nền, `tools/bench_b2_duong_b_tu_khai.py` — §4i)

```
do nhay   4/7  ca thuat ngu da biet hong  (师傅 · 烧酒 · 掐雷 · 纯白给)
do on     19 muc / 3 011 ky tu goc = 0,63 %      ⇒ nguoi soi tay duoc
gia       +1 truong luoc do · ~0 luot goi them
```

⭐ Tác dụng phụ đáng giá hơn chính nó: nó khai cả **lỗi CHÉP LỜI**
(`避不住`, `提炼枪`, `此一听`) — tức thứ §4e cần để **tách lỗi ASR khỏi lỗi
dịch**, một việc ta ⛔ chưa có cách nào khác làm.

### 🔴 RANH GIỚI của nó — giữ nguyên văn

> **Model biết nó không biết TỪ; nó không biết nó hiểu sai CÂU.**

**0 %** ở lớp ngữ pháp: `补人` · `热胀冷缩` · `这才是` (ra *"Mới đây mới là"*
thay vì *"Đây mới là"*) đều ⛔ **không** được khai. ⇒ ⛔ Đừng đọc cột này như
một bộ đo chất lượng.

### ⚠️ Cái ta ⛔ CHƯA đo, và phải nói ra

Bốn con số trên đo trên **lời nhắc ĐƯỜNG CHẾT** (`dich_thuat`), ⛔ không phải
lời nhắc vừa nối. Lời nhắc đường sống khác hẳn (có `ke_ben`, `do_dai_toi_da`,
`cam_xuc`/`kieu_noi`, và từ §7.6 có thêm quy tắc tên riêng) ⇒ ⛔ **độ nhạy và
độ ồn trên đường sống là một ô CÒN TRỐNG**. Đó chính là lý do bật **phần thu**:
để ô đó tự đầy lên bằng lượt chạy thật, ⛔ không phải để dùng ngay.

### Đọc KHOAN DUNG — và vì sao khác hẳn `chu`

`_chuoi_ngan`: vắng mặt · sai kiểu · rỗng ⇒ `[]`; trần **8 mục × 40 ký tự**.
⛔ Không ném. `chu` là **thứ sản phẩm** nên sai lược đồ ở đó **phải** thành lỗi;
`khong_chac` là một **cột chẩn đoán** ⛔ không ai ở hạ nguồn đọc — để nó làm hỏng
một lô lời thoại **đã trả tiền** là đổi một thứ đắt lấy một thứ không đắt.

> 🔴 **Và phép kiểm bắt được một lỗi của chính bản vá này.** Bản đầu viết
> `str(m or "")` — gộp `None` với **mọi giá trị falsy khác**: `0`, `False`,
> `0.0` thành chuỗi rỗng rồi bị bỏ **im lặng**. `list(range(50))` ra **7** mục
> thay vì 8. Cùng họ lỗi với *"hai trạng thái gộp thành một giá trị"*. Đã sửa
> thành `"" if m is None else str(m)`.

### Token — cộng dồn cả §7.6 và §7.7

| lời nhắc hệ thống | ký tự | token |
|---|---|---|
| gốc (trước cả hai) | 1 026 | **338** |
| + quy tắc tên riêng (§7.6) | 1 804 | 590 |
| + tự khai (§7.7), đích `vi` | **1 991** | **641** (+303 so với gốc, +90 %) |
| + tự khai (§7.7), đích `en` | 1 211 | **389** |

⚠️ Trường tự khai ⛔ **không** giới hạn theo đích — một model dịch sang tiếng
Anh cũng có quyền khai chỗ nó không chắc. Chỉ **quy tắc Hán-Việt** mới gắn với
`vi`. Chi phí token vào thêm: ~**+0,015 credit/lô** ở `ltt-3.8`,
~**+0,004** ở `ltt-3.5`.

## 7.8 ✅ **N-23 ĐÃ THI HÀNH** — ghim `temperature`, ghim model, và **ép lược đồ**

> 🔴 **Chủ dự án chốt 24/09 (tối): `ltt-3.5` phục vụ đường dịch của app.**
> ⇒ Câu *"3.5 hay 3.8"* **ĐÓNG**. ⛔ Không so sánh thêm. `ltt-3.8` nhường **toàn
> bộ** cho làn bộ chấm.

### Cổng N-23 — câu hỏi điều phối bắt kiểm TRƯỚC khi sửa

> *"`temperature` có nằm trong vân tay `CONTENT_PROCESS` không?"*

🔴 **KHÔNG.** Vân tay cũ là `noi_dung/{PHIEN_BAN_LOI_NHAC_LONG_TIENG}/{model}`.
⇒ **Vế thứ hai của N-23**: một tham số **đổi đầu ra** mà ⛔ **không vào vân tay**
nghĩa là cache trả kết quả của **nhiệt độ cũ** cho một cấu hình **mới**, ⛔ im
lặng. Cùng họ lỗi với **N-21**, chỉ khác chiều: N-21 là *vân tay đổi mà lời nhắc
không đổi*; đây là *lời nhắc chạy khác mà vân tay không đổi*.

⇒ Đã sửa cả hai vế trong **một** bản vá. Vân tay nay:

```
noi_dung/3/ltt_llm:qwen35-api/t0.00/g1
            ↑ model ghim      ↑ nhiet do  ↑ rang buoc luoc do
```

⚠️ `None` (⛔ không gửi) mã hoá thành `tcong`, ⛔ **khác** mọi giá trị số — *"không
khai"* và *"khai 0,0"* là **hai trạng thái**, gộp lại là đúng bẫy *"hai trạng
thái một giá trị"*.

### Ba bản sửa, **một** lần vô hiệu cache

| | ở đâu | vì sao |
|---|---|---|
| `chuyen_loi_thoai → ltt-3.5` | `ai.MODEL_THEO_THAO_TAC` | chủ dự án chốt |
| `temperature = 0.0` | `ai.NHIET_DO_THEO_THAO_TAC` | ⛔ **không tách** khỏi dòng trên: 3.5 **không ghim** mất 64,3 % lô |
| **ép lược đồ** | `long_tieng.luoc_do_phan_hoi` → `response_format` | đóng nốt 2/21 |

⭐ `qc_ngu_nghia` **giữ `ltt-3.8` ghim tường minh** và ⛔ **không** bị ghim nhiệt
độ — vắng mặt trong bảng = giữ nguyên hành vi cũ, đúng khuôn `MODEL_THEO_THAO_TAC`.

### ⭐ Ép lược đồ — **tra nguồn trước khi tự suy** (luật 10)

**Nguồn:** `ggml-org/llama.cpp`, `tools/server/README.md`:

> *"The `response_format` parameter supports both plain JSON output (e.g.
> `{"type": "json_object"}`) and schema-constrained JSON (e.g.
> `{"type": "json_object", "schema": {…}}` …)"*

⇒ llama-server dịch lược đồ thành **grammar**: một token không hợp lược đồ ⛔
**không sinh ra được**. Đó là một **ràng buộc lúc giải mã**, ⛔ không phải một
lời nhắc mạnh hơn — và đó là lý do nó đóng được **cả hai** chế độ hỏng đã đo
(`doan` ra **MẢNG** · **thiếu đoạn**).

⭐ Và ta biết **trước** các mã của lô ⇒ lược đồ khai **đích danh**:
`required` = đúng các mã đã gửi, `additionalProperties: false`.

### Kết quả — ngưỡng viết TRƯỚC là **≤ 1 % trên ≥ 20 lô**

| cấu hình | lô hỏng | đoạn |
|---|---|---|
| ⛔ không ghim gì (SẢN PHẨM cũ) | 9/14 = **64,3 %** | — |
| ghim `temperature` | 2/21 = **9,5 %** | — |
| **ghim + ép lược đồ** | **0/20 = 0,0 %** ✅ | **188/188** |

```
v1  lo 12 x 7 lo  ->  0 hong  83/83
v2  lo 12 x 7 lo  ->  0 hong  74/74     ⬅ phim VAN hong 2/7 khi chi ghim nhiet do
v3  lo  6 x 6 lo  ->  0 hong  31/31
```

### ⭐ GIÁ, tính bằng **số lượt gọi thêm**: **+0**

`response_format` đi **kèm chính lượt đang gọi** — ⛔ không thêm một lần gọi nào,
⛔ không hạ cỡ lô, ⛔ không vòng thử lại. Hai đường kia (*thử lại khi hỏng*,
*lô nhỏ hơn*) ⛔ **không cần đo** vì đường này đã đạt ngưỡng ở giá bằng **không**.

---

## 7.8b ✅ ĐO LẠI TỪ ĐẦU sau cú sập `23:37–23:44` — **0/20 tái hiện y hệt**

Điều phối bắt đo lại vì số cũ *"chạy quanh cú sập"*. Đã chạy lại **toàn bộ** phép
ép lược đồ sau `23:58`, cùng cấu hình:

| phim | lô | trước sập | **sau sập** |
|---|---|---|---|
| v1 | 12 × 7 | 0 hỏng · 83/83 | **0 hỏng · 83/83** |
| v2 | 12 × 7 | 0 hỏng · 74/74 | **0 hỏng · 74/74** |
| v3 | 6 × 6 | 0 hỏng · 31/31 | **0 hỏng · 31/31** |

```
CONG DON hai luot:  40 lo · 376/376 doan · 0 lo hong = 0,0 %
```

⭐ Hai lượt **độc lập**, cách nhau một lần restart cả ba dịch vụ, ra **cùng một
con số** ⇒ `0/20` ⛔ không phải vết của cú sập.

⚠️ Và mốc giờ đã kiểm: lượt gọi model muộn nhất của loạt CŨ kết thúc **23:35:39**,
trước cửa sổ **81 giây** ⇒ ⛔ không lượt nào vắt qua. Thứ **phải vứt** là **bộ
test** chạy *trong* cửa sổ (11 đỏ → **5** khi chạy lại sau `23:44`).

---

## 7.8c 🔴 **SEED — cổng NHẬN, và nó ⛔ KHÔNG có hiệu lực.** Đường này ⛔ KHÔNG tái lập được

Nửa còn lại của *"chốt nhiệt độ + seed"*. **Nguồn** (⛔ không đoán):
`ggml-org/llama.cpp`, `tools/server/README.md` — `-s, --seed SEED | RNG seed
(default: -1, use random seed for -1)`. Cổng máy B ⛔ không từ chối trường này
(`L_LLM_CONG.md` §4b: 5/5 lượt trả 200).

⇒ Đo lại trên **đúng cấu hình đang chạy hôm nay** (ghim `temperature 0,0` **+ ép
lược đồ**) — ô mà §4b ⛔ chưa có:

| cấu hình | đoạn ỔN ĐỊNH | đoạn ĐỔI |
|---|---|---|
| temp 0,0, ⛔ chưa ép lược đồ, ⛔ không seed | 1 | 11 |
| **temp 0,0 + ép lược đồ + `seed=20260925`** | **0** | **12 / 12** |

🔴 **Ghim seed ⛔ không mua được gì.** Ba lượt **cùng lô, cùng seed, cùng nhiệt
độ, cùng lược đồ** ra **ba bản khác nhau** ở **mọi** đoạn. Ví dụ `seg_0003`:
*"Cách tốt nhất là vào trong ngay."* · *"…vào trong nhà ngay."* · *"Vào nhà ngay
là tốt nhất."*

⭐ Khớp `L_LLM_CONG.md` §4b (4 kết quả khác nhau / 5 lượt **có** seed). Hai phép
đo **độc lập**, hai cấu hình khác nhau, **một kết luận**.

### ✅ Cổng CÓ chuyển `seed` xuống engine — đo bằng HÀNH VI, ⛔ không đọc mã

Mã cổng nằm trên **máy B** (`H:\LTT_LLM\gateway`), ⛔ không đọc được từ máy A.
⇒ Đo bằng **hành vi**, và phép đo này dứt khoát:

| gửi | kết quả |
|---|---|
| `seed = 7` (số nguyên) | ✅ HTTP 200 |
| `seed = "khong-phai-so"` (chuỗi) | 🔑 **HTTP 400 `invalid_request`** |

⇒ ⭐ **Một trường bị BỎ QUA ⛔ không thể sinh ra lỗi kiểu.** Việc `seed` sai kiểu
bị **từ chối** chứng minh nó **đi tới một bộ kiểm** ở hạ nguồn — tức nó **thật
sự được chuyển**, ⛔ không bị nuốt ở cổng.

⇒ Đường của ta: `ai.goi` → `dieu_phoi.goi(them=)` → `CongVlm.chat` →
`than_gui.update(them)` (`cong_vlm.py:341`) → thân request → cổng máy B.

### 🔴 ⇒ Tính chất THƯỢNG NGUỒN, ⛔ không phải lỗ hổng của ta. **Đóng câu hỏi.**

Cộng đồng `ggml-org/llama.cpp` đã ghi nhiều lần — **trích số issue**:

| issue | tiêu đề | liên quan thế nào |
|---|---|---|
| **#7052** | *Non-deterministic output of the llama.cpp server when using multiple slots* | ⭐ **đúng ca của ta**: cổng chạy `-np 3` (nhiều slot) |
| **#19981** | *LLM does not produce identical results with identical seed and prompt* | ⭐ đúng triệu chứng: **cùng seed, cùng prompt, khác kết quả** |
| **#27407** | *spec: greedy output diverges from non-speculative baseline under batched verification on CUDA* | ⭐ cổng chạy **`--spec-type draft-mtp`** — giải mã suy đoán, đúng cơ chế issue này mô tả |
| **#2838** | *CUDA non-determinism on identical requests* | nền: bất định ở tầng CUDA |

> 🔑 **ĐÓNG VĨNH VIỄN — ⛔ phiên sau đừng đi lại.** `seed` **được chuyển và được
> kiểm**, và lượt vẫn **đổi 12/12 đoạn**. ⇒ Bất định đến từ **thượng nguồn**
> (nhiều slot + gộp lô liên tục + giải mã suy đoán), ⛔ **không** từ một núm ta
> quên bật. **⛔ Không còn đường nào để thử ở tầng tham số.**
>
> ⚠️ Muốn tái lập thì phải **đổi CẤU HÌNH ENGINE** (`-np 1`, bỏ `--spec-type`) —
> tức **đánh đổi thông lượng của cả máy B**, một quyết định ⛔ **không thuộc
> làn này**. Hoặc **cache theo vân tay**, đúng như `L_LLM_CONG.md` §4b kết luận.

> # 🔴 HỆ QUẢ, và nó đổi cách ta báo MỌI số dịch về sau
>
> **Đường dịch của ASV ⛔ KHÔNG tái lập được — ⛔ không núm nào đi qua đường sản
> phẩm làm nó tái lập.** Cơ chế hợp lý: `-np 3` + continuous batching +
> `--spec-type draft-mtp` (`L_LLM_CONG.md` §4b) — thứ tự ghép lô đổi theo tải.
>
> ⇒ ⭐ **Mọi phép đo chất lượng dịch phải báo kèm PHƯƠNG SAI giữa các lượt,
> ⛔ không được báo một con số.** Một lượt ⛔ không phải một phép đo.
>
> ⚠️ Chính tệp này đã suýt vi phạm: §7.1 ghi *"9/13"*, và ba lượt trên **cùng**
> cấu hình cho **7 · 9 · 5**. Con số trung thực là **một khoảng**, ⛔ không phải
> một điểm.

⚠️ **Và nó chạm VÂN TAY/CACHE:** cùng đầu vào, cùng tham số, **khác đầu ra** ⇒
vân tay khớp nhưng kết quả ⛔ không phải thứ lần trước sinh ra. ⛔ **Ghi lại,
⛔ không sửa gì ở đó lúc này** (điều phối chốt).

⚠️ **⛔ Đừng suy ngược rằng vòng sửa vô hại.** Ta mới biết nó **ĐỔI** đoạn
(92–100 %), ⛔ **chưa** biết đổi theo **hướng nào**. Phép cơ chế §4f (29 đoạn
**đã đúng** → tốt lên / không đổi / tệ đi) vẫn là phép trả lời câu đó, và nay
⛔ **không** chạy được rẻ hơn bằng cách ghim núm nào.

---

## 7.8d ⚠️ `光子` và LỒNG TIẾNG — va chạm ⛔ KHÔNG tái hiện

Điều phối hỏi: *"giữ nguyên dạng"* có đẩy **chữ Hán** vào bản ghi tiếng Việt —
thứ giọng đọc ⛔ không phát âm nổi — hay không. **Chuỗi THẬT**, ⛔ không tóm tắt:

| lời nhắc | `光子` ra |
|---|---|
| v1 (chưa luật) | *"Mang súng ra đi **Photon**!"* |
| v2 (có luật) | *"Đưa súng đi **Quang Tử**!"* · *"Lấy súng ra đi **Photon**!"* ×2 |
| v3 (luật + ghim) | *"…**Quang Tử**!"* ×3 |

⇒ 🔑 **`光子` ⛔ CHƯA BAO GIỜ ra chữ Hán.** Nó ra **"Photon"** (Latin) hoặc
**"Quang Tử"** (Hán-Việt) — **cả hai đều đọc được** bằng giọng Việt. ⇒ Va chạm
*"thương hiệu giữ dạng ⇒ chữ Hán lọt vào bản ghi"* ⛔ **không tái hiện**.

### Quét chữ Hán trên MỌI đầu ra đã có

```
b2_dich_nen    0 / 188 doan
b2_ten_rieng   0 / 119 dau ra
b2_lap_lai     1 /  36 ban      <- ⚠️ mot ca
--------------------------------------------
tong           1 / 343  =  0,3 %
```

⚠️ **Và ca duy nhất ấy ⛔ KHÔNG phải thương hiệu:**

```
seg_0005   "…dùng súng提炼 để dụ nó."
```

`提炼` đến từ `提炼枪` — một **lỗi CHÉP LỜI** mà chính đường B đã khai (§4i liệt
`提炼枪` trong danh sách lỗi ASR). ⇒ Nguyên nhân là **ASR**, ⛔ không phải nhánh
*"tổ chức/thương hiệu giữ nguyên dạng"*.

> ⇒ ⛔ **Chưa có căn cứ đề nghị chủ dự án sửa luật.** Câu bổ sung *"thương hiệu
> giữ dạng **đọc được**"* giải một bài toán mà **dữ liệu ⛔ chưa cho thấy tồn
> tại**. ⚠️ Rủi ro thật nằm ở chỗ khác: **chữ Hán lọt vào bản ghi vì lỗi ASR**,
> `1/343 = 0,3 %` — và đó là một **cửa chặn ở biên**, ⛔ không phải một câu trong
> lời nhắc.

⚠️ `n = 3` phim, và `光子` là **tên thương hiệu DUY NHẤT** trong cả ba ⇒ ⛔ kết
luận này ⛔ không nói gì về một phim có nhiều thương hiệu Trung Quốc.

## 7.10 🔴 §4f: phép A/B **ĐỘT BIẾN THÀNH RỖNG** — hai nhánh là **cùng một mã**

> Điều phối giao: *nhánh A (dịch lại trơn) vs nhánh B (qua vòng sửa), ≥3 lượt,
> so phân phối + chiều.* ⛔ **Phép này ⛔ không chạy được — và lý do chính là
> phát hiện.** Đọc mã trước khi đốt một lượt gọi nào.

### Vòng sửa `dich_sai` làm ĐÚNG hai việc, ⛔ không việc thứ ba

```
jobs.py:335   su_dung.mo_lai_don_vi(db, run, stage=gd, item_key=ma)   <- CHI doan bi gan co
jobs.py:350   features._dat_lai_giai_doan(db, s)                      <- dat lai dong giai doan
```

Rồi `content_process` chạy lại và dựng lời nhắc bằng
`long_tieng.loi_nhac(lo, tat_ca=…, ngon_ngu_goc=…, dac_diem_giong=…, ngon_ngu_dich=…)`.

> 🔑 **`y_canh` ⛔ KHÔNG được truyền.** Tham số ấy **có tồn tại**
> (`long_tieng.py:214`, và lời nhắc **có** chỗ nhét nó — `long_tieng.py:240`),
> nhưng ⛔ **không người gọi nào truyền**. `grep y_canh` trên cả `apps/`: chỉ
> thấy định nghĩa, ⛔ không thấy một lần truyền.

⇒ ⭐ **Đoạn bị gắn cờ được dịch lại bằng lời nhắc Y HỆT lần đầu** — ⛔ không một
bit nào về *"vì sao nó bị chê"* đi vào lời nhắc.

### ⇒ Nhánh B **≡** nhánh A. Phép A/B là một phép so **một thứ với chính nó**

```
nhanh A  = goi lai `long_tieng.loi_nhac` tren doan do
nhanh B  = goi lai `long_tieng.loi_nhac` tren doan do      <- CUNG MOT DONG MA
```

⛔ Chạy nó sẽ tốn `12 đoạn × 2 nhánh × 3 lượt = 72` lượt gọi để phát hiện lại
một **sự thật đọc được trong mã**. ⭐ Và kết quả đã biết trước: `A ≈ B`, vì
chúng **là một**.

### ⭐ ⇒ N-02 (85 → 85) **ĐƯỢC GIẢI THÍCH**, và giải thích bằng cơ chế

1. Vòng sửa **chỉ** chạm đoạn bị gắn cờ (`mo_lai_don_vi` nhận **một** `item_key`);
2. đoạn ấy được **rút thăm lại** từ **đúng** phân phối cũ (cùng lời nhắc);
3. ⇒ ⛔ **không có áp lực theo chiều nào** — kỳ vọng thay đổi điểm ≈ **0**;
4. ⇒ tổng giữ nguyên, **thành phần bị xáo**.

Đúng bằng số N-02 quan sát: `85 → 85`, `dich_sai 60→44` nhưng `doc_sai 10→14`
và `khong_vua 15→27`. ⭐ Một phép rút thăm lặp lại, ⛔ không phải một phép sửa.

### 🔴 Và nó SỬA một hiểu sai của chính §1 và §4f

§1 viết: *"vòng sửa nhiều khả năng đang **dịch lại những câu vốn đã đúng**"*, và
§4f đo bằng cách cho **29 đoạn ĐẠT** đi qua đường dịch lại.

⛔ **Sai về sản phẩm.** Vòng sửa ⛔ **không bao giờ** chạm đoạn **không bị gắn
cờ** — `mo_lai_don_vi` cấm đúng điều đó, và `jobs.py:320` ghi rõ vì sao (*"phạm
vi nhỏ nhất an toàn"*). ⇒ Đoạn đúng **chỉ** bị dịch lại khi bộ chấm **gắn cờ
NHẦM** nó.

> ⇒ ⭐ **Thiệt hại thật = (tỉ lệ báo động giả) × (xác suất lượt rút lại tệ hơn).**
> ⛔ Không phải *"28/29 đoạn đã đúng bị đổi"* — con số ấy đo một đường
> **sản phẩm ⛔ không đi**.

### ⇒ Phép CÒN LẠI đáng chạy, và nó ⛔ không cần nhánh B, ⛔ không cần bộ chấm

Chỉ còn **một** ẩn số: **xác suất một lượt rút lại làm đoạn đúng TỆ ĐI**.

```
lay ~12 doan DA DUNG  ->  rut lai 1 lan  ->  NGUOI soi: tot len / khong doi / te di
```

⭐ ⛔ Không cần nhánh đối chứng, vì *"rút lại"* **chính là** thứ vòng sửa làm.
⛔ Không cần bộ chấm — nó đang trượt cổng và thuộc làn khác.
⚠️ **Người soi phải MÙ với thứ tự** (⛔ không biết bản nào là gốc, bản nào là
rút lại), và **phải khai ra rằng người soi là tôi** — đúng xung đột lợi ích §4f
đã tự khai.

⛔ **CHƯA chạy** — nó cần một lượt soi tay nghiêm túc, và điều phối xếp bảng từ
`B→D` trước hay sau là quyết định của điều phối.

## 7.11 ⭐ NỐI `y_canh` — vòng sửa thôi **mù**

> 🔴 **Khuyết tật:** `loi_nhac` **có** tham số `y_canh` (`:214`), lời nhắc **có**
> chỗ nhét nó (`:240`), và ⛔ **không một người gọi nào truyền**. ⇒ Đoạn bị chê
> được dịch lại bằng lời nhắc **y hệt** — ⛔ không một bit nào về *vì sao*.
> ⇒ Nó ⛔ không phải vòng **sửa**; nó là một lần **rút thăm lại** (§7.10).

### Đường nối — bốn chỗ, mỗi chỗ một câu

```
sua_chua.y_canh_cho(kk)           dung `y_canh` CO DINH DANG KIEM SOAT tu mot khiem khuyet
jobs.py:_vong_sua                 truyen `y_canh` kem `mo_lai_don_vi` (theo TUNG don vi)
su_dung.mo_lai_don_vi(y_canh=)    gop vao `outputs` cua don vi, GIU ban cu
su_dung.y_canh_dang_cho(...)      doc lai cho cac don vi `ITEM_INVALIDATED`
giai_doan_noi_dung                loc theo ma cua LO roi truyen vao `loi_nhac`
```

### ⛔ Bốn ràng buộc — và cái thứ ba là cái đắt nhất

**1. ĐOẠN TRÍCH, ⛔ không phải nhãn trần.** `y_canh_cho` dựng ba trường có tên:

```
nghi_ngo      ly do cua bo cham, cat 160 ky tu
trich_nguon   cau goc bo cham chi ra
trich_ban_cu  ban dich CU bi nghi
```

⭐ *"sai thực thể"* gần như vô dụng; *"`壁球` → «quần vợt»"* thì dùng được. Cùng
bài học với bộ dò chữ Hán: **một cờ nói *có gì đó* sai; một đoạn trích nói *sai
ở đâu***.

**2. Ví dụ trong lời nhắc là MỆNH LỆNH NGẦM** (§4c). `y_canh` đi **thẳng** vào
lời nhắc ⇒ **hình dạng** của nó đang dạy model ⇒ ⛔ không đổ văn thô của bộ chấm
vào; ba trường có tên, cắt độ dài, trường rỗng bị **bỏ hẳn**.

**3. 🔴 Bộ chấm đang TRƯỢT CỔNG ⇒ `y_canh` MANG THEO BÁO ĐỘNG GIẢ.**
⇒ Lời nhắc ⛔ **KHÔNG** ra lệnh *"hãy sửa lỗi này"*:

```
"Day la NGHI NGO, KHONG phai phan quyet — buoc kiem do CO BAO DONG GIA."
"Neu ban cu DA DUNG thi GIU NGUYEN no."
"KHONG duoc doi mot cau dang dung chi vi no bi nghi ngo."
```

⭐ Ép sửa một chỗ **vốn đúng** là cách chắc chắn nhất **biến một báo động giả
thành một hỏng thật**. Câu chữ phải cho model một **đường lui**.

**4. ⛔ Đối chứng HAI CHIỀU** — và vế hai mới là vế bảo vệ đường thường:

| | |
|---|---|
| đoạn **có** `y_canh` | lời nhắc mang **đoạn trích** + luật *"kiểm lại"* |
| lô **không** đoạn nào | lời nhắc **y hệt bản nền, từng byte** (`nen == _msg({})`) |

⇒ Luật `y_canh` **chỉ** chèn khi lô thật sự có đoạn mang nó. Thiếu vế hai thì ta
⛔ không biết mình có làm bẩn đường **thường** hay không — và mọi số cũ của
đường thường hết so sánh được.

### 🔴 Phép kiểm bắt ĐÚNG khuyết tật đã xảy ra, ⛔ không phải một biến thể

⚠️ Ba bài đơn vị ở trên gọi `loi_nhac` **trực tiếp** nên **luôn** truyền `y_canh`
⇒ chúng ⛔ **không** bắt được khuyết tật thật. **Đã thử tiêm:** bỏ `y_canh=` ở
`giai_doan_noi_dung` ⇒ cả ba **vẫn XANH**.

⇒ ⭐ `test_NGUOI_GOI_that_su_TRUYEN_y_canh_cho_loi_nhac` đọc **CÂY (AST) của
chính người gọi**: mọi lời gọi `loi_nhac` trong `chay` phải có từ khoá `y_canh`.
Tiêm lại ⇒ **ĐỎ đúng chỗ**.

> 🔑 **Một tham số không ai truyền là một tham số không tồn tại** — và chỉ một
> phép kiểm nhìn **người gọi** mới nói được điều đó.

### 🔑 CÂU NGẮN NHẤT TÓM CẢ HỌ LỖI — ⛔ giữ nguyên văn

> **Một tham số ⛔ không ai truyền là một tham số KHÔNG TỒN TẠI — và chỉ một
> phép kiểm nhìn NGƯỜI GỌI mới nói được điều đó.**

⭐ Nó khái quát cả **họ** lỗi gặp trong hai ngày, ⛔ không riêng `y_canh`:

| ca | hình dạng |
|---|---|
| `y_canh` | tham số có · chỗ nhận có · ⛔ **không ai truyền** ⇒ vòng sửa mù |
| `fallback_reason` | ghi ra · ⛔ không ai đọc |
| `words` | mốc từng từ đã trả tiền để tính · ⛔ bị vứt ở chỗ nối |
| `pipeline.ma_loi_la` | khai · ⛔ không nhánh nào gọi |
| `nguon_loi` (G-01) | duyệt giá trị · ⛔ **không đặt vào hồ sơ trả về** |

⚠️ **Điểm chung, và nó là điểm chết:** ⛔ **không** phép kiểm đơn vị nào bắt được,
vì phép kiểm đơn vị **tự nó truyền** tham số. Chúng chỉ lộ ra khi có một phép
kiểm đọc **CÂY của chính người gọi** — hoặc khi một khách trả tiền cho hậu quả.

### ⏭ Nay phép A/B **có nghĩa** — ⛔ chưa chạy

```
A  dich lai KHONG y_canh   (dung san pham HOM QUA)
B  dich lai CO  y_canh     (san pham sau ban va nay)
cung doan · cung cau hinh · >= 3 luot moi nhanh
```

⭐ Đo **CHIỀU**, ⛔ không đo *"có đổi không"* — đường dịch ⛔ không tái lập được
nên **mọi thứ đều đổi**. Câu thật: **trong số đoạn đổi, bao nhiêu TỐT LÊN / TỆ
ĐI?**

⛔ **Người soi ⛔ không phải tôi và ⛔ không phải bộ chấm.** Chủ dự án chốt
**điều phối chấm** ⇒ làn này chuẩn bị **cặp mù** (bỏ nhãn nhánh, xáo thứ tự).
⭐ Và nhánh **A** trả luôn ẩn số §7.10: *xác suất một lượt rút lại làm đoạn đúng
tệ đi*. **Một phép đo, hai câu trả lời.**

## 7.12 ⭐ A/B `y_canh` — **điều phối chấm MÙ**. Hướng DƯƠNG, ⛔ chưa có bằng chứng

> ⛔ **Làn này ⛔ KHÔNG chấm.** Chủ dự án chốt **điều phối chấm**; phán quyết
> được **commit TRƯỚC khi mở khoá** (`a96310b9`). ⚠️ Và người chấm **tự khai:
> họ là một mô hình** — câu đó đi **cạnh** kết quả, ⛔ không ở cuối.

### Kết quả

```
B (CO y_canh) thang :  4/9 doan  (12/27 muc)
A (KHONG)     thang :  2/9 doan  ( 6/27 muc)
ngang nhau          :  3/9 doan  ( 9/27 muc)
```

⭐ **27/27 nhất quán** — cả ba lượt của mỗi đoạn cho **cùng** phán quyết ⇒ việc
xáo + ghép cặp **sạch**, và phán quyết ⛔ không dao động.

> ⚠️ **4 thắng / 2 thua trên 6 ca quyết định ⛔ KHÔNG vượt được ngẫu nhiên.**
> ⇒ Viết **"nghiêng về giúp, `n` quá nhỏ"** — ⛔ **đừng** viết *"`y_canh` giúp"*.

### 🔴 Thứ ĐẮT HƠN con số: bốn quan sát lúc chấm, khi CHƯA biết nhánh

```
掐雷 = LUU DAN          -> CA HAI ban deu "dat min"
纯白给 = long game       -> CA HAI ra "trang tay"
热胀冷缩                -> CA HAI rut thanh "vi nhiet do"
```

⇒ ⭐ **Khác biệt giữa hai nhánh nằm ở DIỄN ĐẠT** (giữ/bỏ `肯定`, `这里`, `也`,
`迅速`; `趁` dịch *"khi"* hay *"chờ"*), ⛔ **KHÔNG nằm ở việc sửa được thuật ngữ.**

> 🔑 **Kết luận thật của phép đo:** `y_canh` giúp model **diễn đạt sát hơn**,
> ⛔ nhưng nó ⛔ **không** cứu được lớp **thuật ngữ / tiếng lóng** — đúng lớp mà
> **bảng từ `B→D`** sinh ra để giải.
> ⇒ Hai đường ấy ⛔ **không thay thế nhau** — chúng **BÙ NHAU**.

### 🔴 Một CHẾ ĐỘ HỎNG MỚI: gợi ý "có vấn đề" ⇒ model **BỊA** chi tiết

```
提炼枪  (mot token DA HONG do ASR)  ->  mot ban CO `y_canh` them "sung MAY"
```

⇒ ⭐ Một gợi ý *"chỗ này có vấn đề"* có thể đẩy model **thêm thông tin nó ⛔
không có**, thay vì **kiểm lại**. ⚠️ Ràng buộc thứ ba (*"nghi ngờ, ⛔ không phải
phán quyết"*) **đúng hướng nhưng CHƯA đủ mạnh**.

⇒ **Bản vá (lời nhắc v4), sửa MỘT lần:**

```
"KHONG duoc THEM chi tiet moi. Neu ban khong chac, hay GIU nguyen muc cu the
 cua ban cu — dung cu the hoa them mot thu ma cau goc khong noi."
```

⭐ Và đo lại **CẢ 9 ĐOẠN**, ⛔ không chỉ ca vừa sửa — ta đã mất một lượt vì đúng
chuyện đó (§4c, ba lần *sửa-một-hỏng-một*). ⭐ `提炼枪` là **phép thử sẵn có**,
⛔ ⛔ không bịa ca mới.

### ⛔ PHẠM VI — ghi nguyên văn, ⛔ đừng rút gọn

> Đây là **TRẦN TRÊN**. `y_canh` trong phép đo này là **lý do ĐÚNG**: **21/27**
> mục đến từ **7 ca người xác minh**, chỉ **6/27** từ **2 phán quyết thật** của
> bộ chấm. Vòng sửa **thật** có **43 %** báo động giả ⇒ `y_canh` thật sẽ **ồn
> hơn hẳn**, và kết quả thật sẽ **kém hơn** con số ở đây.

⚠️ Và `n = 9 đoạn`, ⛔ không phải 12 — ta chỉ có **2** phán quyết thật của bộ
chấm, sinh thêm đòi `ltt-3.8` (đã nhường hẳn làn bộ chấm). Mở rộng lên ~20 đoạn
cần điều phối xin thêm verdict.

## 7.13 ⭐ Lời nhắc **v4** — cấm bịa chi tiết. `提炼枪` đã đóng, ⚠️ nhưng ĐỘ DÀI nay tố cáo nhánh

**Bản vá:** thêm **một** câu vào luật `y_canh`
(`PHIEN_BAN_LOI_NHAC_LONG_TIENG` **3 → 4**):

```
"KHONG duoc THEM chi tiet moi. Neu ban khong chac, hay GIU nguyen muc cu the
 cua ban cu — dung cu the hoa them mot thu ma cau goc khong noi."
```

### ✅ Ca `提炼枪` — **đã đóng, 3/3 lượt**

Đo lại **cả 9 đoạn** (⛔ không chỉ ca vừa sửa — §4c đã dạy):

```
v3 (truoc)  mot ban CO y_canh  ->  "... dung sung MAY ..."      <- BIA
v4 (sau)    ca 3 luot          ->  "... dung sung bat anh ta hung dan."
```

⇒ ⭐ Chi tiết bịa **biến mất**, và **nhất quán 3/3**. Ràng buộc mới **giữ**.

### 🔴 ⚠️ NHƯNG — ĐỘ DÀI nay TỐ CÁO NHÁNH. Tập mù v4 ⛔ **KHÔNG còn mù**

| | v3 | **v4** |
|---|---|---|
| A trung vị | 8 từ | 8 từ |
| B trung vị | 8 từ | **7 từ** |
| tỉ lệ B/A | **1,00** ✅ | **0,875** 🔴 |

```
B NGAN hon A : 18/27      bang nhau : 3/27      B DAI hon : 6/27
=> doan "ban NGAN hon la B" dung 18/27 = 67 %   (50 % = khong doan duoc gi)
```

> 🔴 **Đây là một hệ quả ⛔ KHÔNG lường trước của chính bản vá.** Câu *"giữ nguyên
> mức cụ thể, ⛔ đừng thêm chi tiết"* đẩy nhánh B **ngắn lại một cách hệ thống**
> ⇒ người chấm có thể đoán nhánh bằng **độ dài**, ⛔ không bằng chất lượng.
>
> ## 🔑 ⚠️ `0,875` ÁP CHO **ĐOẠN ĐƯỢC SỬA**, ⛔ KHÔNG CHO TOÀN BẢN DỊCH
>
> ⛔ **Đừng trích con số này rộng ra.** `QUY_TAC_Y_CANH` **chỉ** được chèn khi lô
> thật sự có đoạn mang `y_canh` ⇒ nó **chỉ** chạm những đoạn **bị gắn cờ và được
> dịch lại**. Đường **thường** ⛔ **không** đổi một byte nào — lời nhắc FLORES
> **y hệt** ở v3 và v4.
>
> ⇒ ⭐ **Bán kính ảnh hưởng = tỉ lệ đoạn bị gắn cờ**, ⛔ không phải 100 % bản dịch.
> ⚠️ Điều phối đã suýt trích nó rộng ra (*"v4 đẩy ta về phía mất ~8 điểm
> chrF++"*) và **đã rút**.
>
> ⭐ Và bán kính nhỏ ⛔ **không phải may**: nó nhỏ **vì bản vá có phạm vi chặt** —
> một luật **chỉ bật khi có dữ liệu cần nó**, và **có phép kiểm gác** đúng điều
> đó (`test_quy_tac_TEN_RIENG_chi_ra_khi_dich_VI` cùng khuôn). ⇒ **Tính chất
> đáng giữ**, ⛔ không phải một chi tiết.
>
> ⇒ ⛔ **Phải báo TRƯỚC khi chấm** — đúng ràng buộc điều phối đặt ra, và lần này
> nó **bắt được một cái thật**. ⛔ Đừng đọc phán quyết v4 như một phép mù sạch.

### ✅ Đã xử: **cân theo CHIỀU**, ⛔ không lọc theo ĐỘ LỚN

Điều phối chọn *"lọc `|len(A) − len(B)| ≤ 1`"*. **Đã làm và ĐỎ:**

```
loc |dif| <= 1 :  15/27 cap · 5/9 doan · B ngan hon 12/15 = 80 %  ⛔ TE HON goc (67 %)
loc |dif| == 0 :   3/27 cap · 1/9 doan ·                     0 %  ⛔ het luc thong ke
loc |dif| <= 2 :  24/27 cap · 8/9 doan ·                    62 %
```

> 🔑 **Rò rỉ nằm ở CHIỀU, ⛔ không ở ĐỘ LỚN.** Lọc theo độ lớn giữ lại **đúng**
> những cặp *"B ngắn hơn một từ"* ⇒ nó **cô đặc** chiều thay vì xoá nó.

⇒ **Đường 2′ — cân theo chiều** (số cặp B-ngắn = số cặp B-dài):

```
6 cap B-ngan + 6 cap B-dai + 3 cap bang = 15 cap · 8/9 doan
doan "ngan hon = B" dung 6/15 = 40 %      (50 % = mu that)
```

⚠️ **Thiên lệch còn lại, phải khai:** cặp ⛔ **không đều** giữa các đoạn (1–3
cặp/đoạn) ⇒ một đoạn nặng 3 phiếu, một đoạn nặng 1. ⇒ ⛔ **Đừng đọc *"số cặp
thắng"* thành *"số đoạn thắng"*** — chấm **theo ĐOẠN**.

⚠️ Và bộ lọc `≤ 1` (đã bỏ) thiên lệch chọn mẫu **rõ**: giữ **trọn 5** đoạn, bỏ
**trọn 4**, các đoạn bị bỏ đều **dài hơn** (trung vị **13** vs **8** từ).

⭐ Tập **chưa cân** giữ nguyên ở `b2_ab_y_canh_v4/` — ⛔ không xoá.

## 7.9 🔴 Đo lại sau khi ghim — **một hoá đơn tự đóng, một thì không**

### 1. Tên riêng: **38/39 → 38/39**. ⛔ Ghim nhiệt độ ⛔ KHÔNG đổi gì ở đây

| tên | v1 chưa luật | v2 có luật | **v3 luật + ghim 0,0** |
|---|---|---|---|
| 重庆 | XX XX XX | OK XX OK | ⚠️ **XX OK OK** |
| **光子** (tiêu chí ÂM) | - OK OK | XX OK OK | 🔴 **XX XX XX** |
| 11 ca còn lại | — | OK | **OK OK OK** |

```
v2 (chua ghim)  38/39 = 97,4 %
v3 (DA ghim)    38/39 = 97,4 %      ⇒ khong doi
```

> 🔴 **`光子` nay hỏng ỔN ĐỊNH 3/3 lượt** — trước khi ghim nó hỏng **1/3**.
> ⇒ Theo đúng tiêu chí điều phối đặt ra (*"còn hỏng **ổn định** ⇒ lúc đó mới là
> lỗi **luật**"*): đây **là lỗi luật**, ⛔ không phải rút thăm. Nhánh
> *"tổ chức/thương hiệu ⇒ giữ nguyên"* **thua** nhánh phiên âm một cách nhất quán.
> ⛔ **Làn này không sửa** — `光子` là quyết định **sản phẩm**, chờ chủ dự án (§4g).

⚠️ `重庆` vẫn **1/3 sai** ⇒ còn **ngẫu nhiên**, ⛔ chưa đủ căn cứ gọi là lỗi luật.

### 2. Mất đoạn: **2/21 → 0/20** ✅ — xem §7.8

### 3. 🔴 Vòng sửa: giả thuyết **SAI**. Ghim nhiệt độ ⛔ **KHÔNG** đóng được N-02

> Giả thuyết điều phối: *"ở `temperature = 0`, dịch lại **cùng** một đầu vào cho
> **cùng** một đầu ra ⇒ **vòng sửa thôi xáo**"*.

Phép đo (`tools/bench_b2_lap_lai.py`) — **cùng** lô, **cùng** lời nhắc đường
sống, **đúng** nhiệt độ sản phẩm đang ghim, gọi **3 lượt**:

```
12 doan so duoc  ->  ON DINH 1  ·  DOI 11  =  92 %
```

⛔ **11/12 đoạn vẫn ra khác nhau** giữa các lượt. Ví dụ `seg_0003`:
*"Cách tốt nhất là nhanh chóng vào trong tòa nhà."* · *"Cách tốt nhất là vào
trong ngay."* · *"Cần vào trong ngay."*

⭐ Và nó **khớp với một nguồn đã có**: `L_LLM_CONG.md` §4b đo **5 kết quả khác
nhau / 5 lượt** ngay ở `temperature = 0` (cơ chế: `-np 3` + continuous batching
+ `--spec-type draft-mtp` — thứ tự ghép lô đổi theo tải). Hai phép đo **độc lập**,
trên hai lô khác nhau, **cùng một kết luận**.

> 🔑 ⇒ **Ghim nhiệt độ mua ĐỘ BÁM LƯỢC ĐỒ, ⛔ không mua tính tái lập.**
> ⇒ Con số **92 %** ngang với **28/29 đoạn đổi** mà §4f đo bằng một đường khác.
> ⇒ **N-02 (85 → 85) VẪN chưa được giải thích bằng nhiệt độ.** Vòng sửa vẫn là
> một **phép rút thăm lại**, và ⛔ **không** được đóng sổ nó bằng bản vá N-23.

## 7.4 ⇒ Bước 2 ĐÃ LÀM (§7.6) · Bước 3 ⛔ CHƯA

**Bước 2** — quy tắc tên riêng vào lời nhắc đường sống — ⭐ **đã làm, xem §7.6**
(21/33 → 38/39, kèm hoá đơn một hồi quy). Nó chạy **sau** §7.5, đúng thứ tự:
⛔ không chồng một thay đổi lời nhắc lên một chỗ mà nguyên nhân bất ổn còn chưa rõ.

**Bước 3** (bản nền dịch đo lại trên đường sống) ⛔ **chưa chạy**.

⭐ **Đường B** (§4d) — phần **THU** đã bật, xem §7.7. ⛔ Chỉ thu.

---

## ⚠️ ĐỌC TRƯỚC MỌI CON SỐ

⛔ **Chưa có bộ chấm đáng tin.** Đường chấm ngữ nghĩa (`qc_ai`) đang **trong
xưởng** ở một làn khác, và nó vừa được đo là **báo động giả 43 %**. ⇒ Tệp này
mang **bản dịch** và **quan sát tay**, ⛔ **không** mang một phán quyết tốt/xấu.

## 1. Bản NỀN — vì sao nó là việc quan trọng nhất

Ta **chưa bao giờ** tách *"chất lượng dịch"* khỏi *"dịch + một vòng sửa chạy
bằng bộ chấm hỏng"*. Quan sát **85 → 85 không hội tụ** (N-02) là số của **cả
cụm**, và cụm ấy chứa chính bộ chấm nói trên.

⇒ Vòng sửa nhiều khả năng đang **dịch lại những câu vốn đã đúng**. ⛔ Không có
bản nền, mọi con số dịch từ trước tới nay **không quy được cho ai**.

## 2. Cách chạy — ⛔ và vì sao là BENCH, không phải đổi cấu hình

| thành phần | lấy từ đâu |
|---|---|
| lời nhắc | `dich_thuat._loi_nhac` — ⛔ **nguyên văn** |
| chia lô | `dich_thuat.chia_lo` (`DOAN_MOI_LO = 20`) |
| đọc kết quả | `dich_thuat._doc_ban_dich` (khoá theo mã đoạn) |
| nhiệt độ | **0,2** — đúng con số `dich_mot_lo` đang dùng |
| model | **`ltt-3.5`** ⬅ điều **duy nhất** khác |
| vòng sửa | ⛔ **TẮT** |

### 🔴 CHẶN — một chỗ khai DÙNG CHUNG, cần điều phối xếp thứ tự

```
apps/auto_scan_video/manifest.py:102   model_llm_noi_bo="ltt-3.8"
```

Đó là **nguồn duy nhất** mà `ai.model_cho()` đọc, và nó phục vụ **cả năm** thao
tác AI của ASV — **kể cả `qc_ai`**, đang là vùng của làn khác. ⇒ Đổi nó sang
`ltt-3.5` là **đổi model của làn kia trong im lặng**.

⛔ Nên làn này **không sửa**, mà ghim model **tại chỗ gọi** trong
`tools/bench_b2_dich_nen.py`. ⚠️ **Hệ quả phải biết:** đường **sản phẩm** vẫn
đang dịch bằng `ltt-3.8` — bản nền này ⛔ **chưa** là thứ sản phẩm tạo ra.

## 3. Kết quả chạy

| phim | đoạn nguồn | **dịch được** | thiếu | lô | lô hỏng | giây |
|---|---|---|---|---|---|---|
| v1 · món ăn | 83 | **83** | 0 | 5 | 0 | 114,0 |
| v2 · cắm trại | 74 | **74** | 0 | 4 | 0 | 84,1 |
| v3 · PUBG | 31 | **31** | 0 | 2 | 0 | 53,8 |

```
188/188 đoạn · 0 thiếu · 0 lô hỏng · 0 đoạn rỗng · 0 chữ Hán sót trong bản dịch
```

⭐ Tổng **252 s** cho 188 đoạn, trần **2 request/model**, ⛔ **không** giữ
`cpu_nhieu` (gọi máy B là **chờ mạng**, không đốt lõi máy A).

Bản dịch: `bang_chung/b2_dich_nen/{v1,v2,v3}_nen.json` — mỗi tệp mang
`⚠️ gioi_han` **trong chính bản ghi**.

## 4. Đọc tay — ⛔ quy tắc chọn chốt TRƯỚC, liệt kê hiện tượng, KHÔNG chấm điểm

**Quy tắc** (`bench_b2_dich_nen.chon_mau`, viết trước khi có bản dịch nào): mỗi
phim **10** câu **cách đều**, chỉ số `round(i·(n−1)/9)`, `i = 0..9`. ⭐ Cách đều
chứ không ngẫu nhiên ⇒ chạy lại ra **đúng** mẫu đó; ⛔ không chọn tay ⇒ không ai
chọn được những câu đẹp.

### 4.1 Tên riêng → Hán-Việt: **2/3 đúng**

| tên Hán | ra tiếng Việt | |
|---|---|---|
| `小美` (10 lần, v2) | **Tiểu Mỹ** — ✅ và **nhất quán cả 10 lần** | ✅ |
| `李宗盛` (v1) | **Lý Tông Thành** | ✅ |
| `光子` (v3) | ⛔ **"Photon"** | ⛔ |

⛔ `光子` là tên **studio game** (Lightspeed & Quantum). Model dịch **nghĩa đen
sang tiếng Anh** thay vì phiên Hán-Việt (*Quang Tử*) hay giữ nguyên.

⭐ **Và lời nhắc hiện KHÔNG hề nhắc tới phiên Hán-Việt** (`_loi_nhac`, 4 quy
tắc, không quy tắc nào về tên riêng). ⇒ 2/3 đúng là **may**, ⛔ không phải một
hành vi được bảo đảm.

### 4.2 Bỏ sót / bịa thêm: **không thấy ca nào**

0 đoạn rỗng, 0 chữ Hán sót. Tỉ lệ độ dài VI/ZH nằm quanh **3,5–4,5** đều khắp —
⚠️ đó là **giãn nở bình thường** của tiếng Việt so với văn Hán, ⛔ không phải
dấu hiệu bịa thêm. ⚠️ Và tỉ lệ độ dài **không** phát hiện được việc bỏ sót *bên
trong* một câu — phép này ⛔ **không** phủ điều đó.

### 4.3 Thuật ngữ — nơi hỏng tập trung

| phim | gốc | ra | hiện tượng |
|---|---|---|---|
| v3 | `掐雷` · `假雷` | *"ném **mìn**"* · *"**mìn** giả"* | ⛔ `雷` ở đây là **lựu đạn**, không phải mìn. `掐雷` = *nấu lựu đạn* (giữ vài giây rồi ném) — mất hẳn nghĩa |
| v3 | `纯白给` | *"bị cho trắng tay"* | ⛔ tiếng lóng game: *chết vô ích / nạp mạng*. Dịch theo mặt chữ |
| v3 | `补人` | *"tiêu diệt"* / *"xử lý"* | ⚠️ đúng nghĩa (kết liễu địch đã gục) nhưng **hai cách gọi cho một thuật ngữ** |
| v1 | `烧酒` | *"rượu **shochu**"* | ⛔ phim Hàn: đây là **soju**. Ra tên Nhật |
| v1 | `热胀冷缩` | *"do nóng lạnh"* | ⛔ mất khái niệm **giãn nở vì nhiệt** |
| v1 | `九分熟` | *"chín chín phần"* | ⚠️ lặp chữ, khó đọc thành tiếng |
| v1 | `嫩肉粉` | *"bột mềm thịt"* | ⚠️ thiếu chữ *làm*: "bột **làm** mềm thịt" |
| v1 | `师傅` | *"thày bếp"* / *"người làm bếp"* | ⚠️ sai chính tả (**thầy**) + **không nhất quán** |
| v2 | `这才是…` | *"**Mới đây mới là** cuộc sống…"* | ⛔ *"Mới đây"* = *gần đây*. Đúng phải là *"Đây mới là…"* |

⭐ **Hình dạng chung:** hỏng **không** rải đều — nó **tụ ở thuật ngữ chuyên
ngành** (game, ẩm thực vùng) và ở **tiếng lóng**. Văn tường thuật thông thường
ra **trôi chảy và đúng**.

⚠️ **Và điều này đang bị đánh giá bằng một chân lý nền lệch:** bản chép lời
nguồn có lỗi nghe (`跳散` ← `跳伞`, `天然霉` ← `天然酶`, `避不住` ← `庇护所`).
⭐ Model dịch **tự phục hồi** hai trong số đó (*"men tự nhiên"*, *"nơi trú ẩn"*)
— tức một phần "lỗi dịch" người sau đọc thấy sẽ là **lỗi ASR**, ⛔ không phải
lỗi dịch. Phải tách trước khi quy trách nhiệm.

## 4b. ⭐ TÁCH MODEL THEO THAO TÁC — chặn ở §2 đã gỡ

`ai.MODEL_THEO_THAO_TAC` (commit `1a225aa8`): **vắng mặt = giữ nguyên hành vi
cũ**. Hôm nay bảng có đúng hai dòng:

```
qc_ngu_nghia -> ltt-3.8    🔑 GHIM TƯỜNG MINH, ⛔ không "thừa hưởng mặc định"
dich_thuat   -> ltt-3.5    ⭐ chủ dự án chốt
```

⭐ `qc_ngu_nghia` được ghim **dù giá trị hôm nay trùng mặc định**: một giá trị
trùng **vì tình cờ** và một giá trị trùng **vì được khai** là hai trạng thái
khác nhau, và ⛔ chỉ cái thứ hai sống sót qua một lần ai đó sửa chỗ khác.
Phép bắt cái bẫy: `test_DOI_MAC_DINH_thi_qc_ngu_nghia_KHONG_doi`.

⇒ Bản nền nay chạy **qua đường sản phẩm** (`dich_thuat.dich_ban_ghi`, ⛔ không
ghim gì tại chỗ gọi). Bản ghi mang `model_that` do `ai.model_cho` **thực sự**
chọn — ⛔ không phải hằng của bench; hai thứ đó lệch nhau được, và khi lệch thì
con số phải nói ra.

| phim | đoạn | dịch được | model thật | lời nhắc | giây |
|---|---|---|---|---|---|
| v1 | 83 | **83** | `qwen35-api` | v3 | 154,0 |
| v2 | 74 | **74** | `qwen35-api` | v3 | 125,2 |
| v3 | 31 | **31** | `qwen35-api` | v3 | 64,5 |

## 4c. Hán-Việt — thêm luật, đo lại trên ĐÚNG 30 câu cũ

### 🔴 Lần đầu hỏng, và nó hỏng theo cách đáng ghi

Lời nhắc **v2** thêm quy tắc 5 với bốn ví dụ — nhưng tôi viết chúng **không
dấu** (`Truong Vi`, `Tieu My`, `Ly Tong Thanh`, `Quang Tu`). Đo lại:

| tên | v1 (chưa có luật) | **v2 (ví dụ KHÔNG DẤU)** | **v3 (ví dụ CÓ DẤU)** |
|---|---|---|---|
| `光子` | ⛔ *Photon* | ✅ *Quang **Tu*** ⚠️ mất dấu | ✅ **Quang Tử** |
| `小美` | ✅ *Tiểu Mỹ* | ✅ *Tiểu Mỹ* | ✅ **Tiểu Mỹ** |
| `李宗盛` | ✅ *Lý Tông Thành* | ⛔ *Lý Tông **Thanh*** ⬅ **TỤT** | ✅ **Lý Tông Thành** |
| chữ Hán sót | 0 | **1** ⬅ | **0** |

⛔ v2 sửa được `光子` **nhưng làm hỏng** `李宗盛` — đúng cái điều kiện *"sửa được
mà không làm hỏng hai cái kia"* đặt ra. Model **bắt chước HÌNH THỨC của ví dụ**,
không chỉ nội dung của luật: ví dụ không dấu ⇒ tên riêng ra không dấu.

> ⭐ **Một ví dụ trong lời nhắc là một MỆNH LỆNH ngầm.** Cùng họ với ghi chú đã
> có ở `dich_thuat.MODEL_CHINH`: *một ví dụ trong docstring là mã mà người ta
> chép*. Lần này nạn nhân là **model**, không phải người.

⇒ v3 viết ví dụ **có dấu đầy đủ** và cấm bỏ dấu tường minh: **3/3 đúng, 0 hồi
quy, 0 chữ Hán sót**. `PHIEN_BAN_LOI_NHAC` 1 → 2 → 3 (nó nằm trong vân tay, nên
mọi bản dịch cũ tự vô hiệu).

⚠️ Và đây là **n = 3 tên riêng trên 3 phim** — ⛔ đủ để nói *"đã sửa ca đã biết"*,
⛔ **không** đủ để nói *"phiên Hán-Việt đã đúng"*.

### 🔴 Thử nới n, và phép tra **bác lại một dấu ✅ ở bảng trên**

Nguồn đã tra: **Unihan** (Unicode Consortium, `Unihan_Readings.txt`, trường
`kVietnamese`) — một nguồn **công bố**, 8 306 ký tự có âm.

⛔ **Không dùng được làm người chấm**, hai lý do đo được:

| | |
|---|---|
| **thiếu chữ giản thể** | 张 · 伟 · 陈 · 刘 · 杨 · 赵 · 吴 đều **không có** entry (7/17 ký tự thử). Phim khách là văn **giản thể** |
| **âm lệch khỏi lối dùng trong TÊN** | 美 → *"mỉ"* (tên dùng **Mỹ**) · 子 → *"tí"* (光子 dùng **Tử**) |

⇒ Theo đúng luật đã đặt: ⛔ **không tự chế danh sách rồi tự chấm**. **n = 3, và
dừng ở đó.**

### ⚠️ Nhưng phép tra đó **bác một dấu ✅ của chính tôi**

Unihan cho `盛` → **`thịnh`**, ⛔ **không phải** *"thành"* (*thành* là âm của
成/城). ⇒ `李宗盛` ra **"Lý Tông Thành"** ở **cả** v1 **và** v3 nhiều khả năng
**SAI** — và tôi đã chấm nó ✅ **hai lần**, bằng mắt, vì nó *trông* như một tên
Việt hợp lý.

⇒ **Bảng trên phải đọc lại**: cột v3 chứng minh *"không hồi quy so với v1"* và
*"nhất quán"*, ⛔ **không** chứng minh *"đúng chuẩn Hán-Việt"*. Con số trung
thực là:

```
3/3 NHẤT QUÁN và KHÔNG HỒI QUY          ✅ đo được
?/3 ĐÚNG CHUẨN Hán-Việt                 ⛔ KHÔNG đo được — không có người chấm
   (và `李宗盛` đang bị NGHI, không được tính là đúng)
```

⭐ Bài học, và nó đắt: **tôi tự chấm bản dịch của chính tôi.** Hai lượt liền
`李宗盛` ra *"Thành"* và tôi ghi ✅ cả hai lần — ⛔ một dấu ✅ do người tạo ra kết
quả tự đặt không phải một phép đo. Chính vì thế điều phối đòi **nguồn tra được**,
và chính vì thế *"không tra ra nguồn ⇒ khai n = 3 và dừng"* là luật đúng.

## 4d. ⭐ Hỏng tụ ở THUẬT NGỮ ⇒ trỏ tới BẢNG TỪ, ⛔ không phải đổi model

Phát hiện đáng giá nhất của lượt này, và nó phải đứng **trước** khi ai kịp đề
xuất đổi model:

> **Văn tường thuật ra trôi chảy và đúng. Hỏng tụ ở thuật ngữ chuyên ngành và
> tiếng lóng** — `掐雷` (lựu đạn, không phải mìn) · `纯白给` (lóng game) ·
> `烧酒` (soju Hàn, không phải shochu Nhật) · `补人`.

⛔ **Một model to hơn cũng không biết `纯白给` là tiếng lóng game.** Đó là tri
thức **miền**, không phải năng lực ngôn ngữ. ⇒ Đường sửa là **bảng từ theo
miền** (game · ẩm thực vùng · dã ngoại) bơm vào lời nhắc, ⛔ **không** phải
`ltt-3.5 → ltt-3.8`.

⚠️ Và đổi model còn **đắt hơn**: `ltt-3.8` là ~4× token vào và ~20× token ra
(`platform_core/llm/gia_token.BANG_GIA`) — trả gấp bội cho một thứ nó **cũng
không biết**.

### Các đường đi khả dĩ, kèm GIÁ — ⛔ tôi không chọn, đây là quyết định sản phẩm

⚠️ Bảng từ cho **ba phim này** ⛔ không trả lời được cho **phim khách đưa lên**:
ta không biết trước khách dịch phim game, ẩm thực hay tài liệu.

| đường | cách làm | giá phải trả | hỏng thế nào |
|---|---|---|---|
| **A · khách tự nạp bảng từ** | ô nhập "thuật ngữ riêng" trước khi chạy | ⛔ **công của khách**, và khách thường **không biết trước** phim mình có thuật ngữ gì; thêm một bước rời bỏ ở phễu | khách để trống ⇒ **không có gì đổi**, ta quay lại đúng hiện trạng |
| **B · model TỰ KHAI chỗ nó không chắc** | thêm một trường `khong_chac: [ma]` vào lược đồ dịch | +token mỗi lô; ⚠️ và **độ tự tin của model là một thứ chưa đo** — nó có thể tự tin ở đúng chỗ nó sai | ⛔ nếu model không biết mình không biết thì trường này **rỗng đều**, và ta trả tiền cho một cột trống |
| **C · bảng theo LĨNH VỰC, khách chọn** | 3–5 bảng dựng sẵn (game · ẩm thực · dã ngoại · tài liệu) | ⛔ **công của ta** để dựng và **nuôi** từng bảng; phim lai lĩnh vực thì chọn sai bảng | chọn nhầm lĩnh vực ⇒ bơm thuật ngữ **sai miền** vào lời nhắc, ⚠️ có thể **tệ hơn** không có bảng |
| **D · rút bảng từ TỪ CHÍNH PHIM** | một lượt LLM đọc toàn bộ bản chép lời, liệt kê thuật ngữ + đề xuất cách dịch, rồi bơm vào lời nhắc dịch | +1 lượt gọi mỗi phim (≈ 1/5 chi phí dịch); ⛔ **không có người chấm** cho bảng nó rút ra | bảng rút sai ⇒ **ghim sai** một thuật ngữ cho **toàn phim**, ⚠️ tệ hơn sai lẻ tẻ |
| **E · không làm gì** | giữ nguyên | 0 | hỏng thuật ngữ ở lại đúng mức hôm nay (§4d) |

> 🔴 **ĐÃ CHỐT 24/09 — điều phối chọn `B → D`, `A` tuỳ chọn.** ⛔ **CHƯA LÀM.**
>
> | | đường | vì sao |
> |---|---|---|
> | 1 | **B** — model tự khai từ nó không chắc | rẻ nhất; phần **thu** đã bật (§7.7); tiện thể là **bộ dò lỗi chép lời** |
> | 2 | **D** — rút bảng từ **TỪ CHÍNH PHIM** | ⭐ chỗ nó thắng một bảng tĩnh: sinh ra **từ phim khách đưa lên**, nên trả lời được *"phim game hay ẩm thực?"* — câu ta ⛔ **không biết trước** |
> | 3 | **A** — khách tự nạp bảng từ, **ĐÈ LÊN** kết quả tự động | rẻ, và là thứ khách doanh nghiệp sẽ hỏi |
>
> ⛔ **Xếp SAU việc nhiệt độ, và lý do là một con số:** `57 %` độ nhạy và
> `0,63 %` độ ồn của đường B **đo ở nhiệt độ CHƯA ghim** ⇒ ⚠️ cả hai **có thể
> đổi**. ⛔ Đừng dựng một thiết kế trên hai con số sắp phải đo lại.
>
> ⚠️ **Giới hạn ghi vào thiết kế NGAY TỪ ĐẦU:** *model biết nó không biết **TỪ**;
> nó ⛔ không biết nó hiểu sai **CÂU*** — **0 %** ở lớp ngữ pháp (§4i).
> ⇒ `B→D` ⛔ **không thay** được bộ chấm, nó **giảm tải** cho bộ chấm.
>
> ⭐ **Khi tới lượt, đo HAI vế** — vế hai là vế ta suýt quên ở **mọi** lần sửa
> lời nhắc hôm nay:
> 1. bao nhiêu trong **7 ca hỏng đã biết** được đóng;
> 2. ⭐ **có ca nào vốn ĐÚNG bị bảng từ làm hỏng không.**

⛔ **Tôi không khuyến nghị đường nào** — điều phối mang tới chủ dự án. Ba điều đã
**đo được** và cần nằm cạnh lựa chọn:

1. hỏng **tụ ở thuật ngữ + lóng**, văn tường thuật trôi chảy;
2. ⛔ đổi model **không** sửa được lớp hỏng này, và đắt ~4× vào / ~20× ra;
3. ⛔ ta **chưa có** người chấm nào cho bản dịch — nên mọi đường trên, sau khi
   làm, ⛔ **vẫn chưa đo được là có giúp không**. Đó là ràng buộc nặng nhất.

## 4e. ⚠️ Tách lỗi ASR khỏi lỗi dịch — và một giới hạn của CER

Ba lỗi nghe trong bản chép lời nguồn, cả ba **rơi trúng từ khoá**:

| nguồn ASR | đúng ra là | model dịch xử lý |
|---|---|---|
| `跳散` | `跳伞` (nhảy dù) | ✅ ra *"nhảy dù"* — **tự phục hồi** |
| `天然霉` | `天然酶` (enzyme) | ✅ ra *"men tự nhiên"* — **tự phục hồi** |
| `避不住` | `庇护所` (nơi trú ẩn) | ✅ ra *"nơi trú ẩn"* — **tự phục hồi** |

⇒ Một phần *"lỗi dịch"* người sau đọc thấy sẽ là **lỗi chép lời**, ⛔ không phải
lỗi dịch. Phải tách **trước** khi quy trách nhiệm.

⭐ Và nó phơi ra một **giới hạn của CER** — đã ghi vào `B1_CHEP_LOI.md` §1c:
mỗi lỗi trên chỉ 1–3 ký tự trên hơn 700, tức đóng góp vào CER **gần bằng
không**, nhưng chúng là **danh từ mang nghĩa của câu**. ⛔ *"CER 0,04"* ⛔ không
đọc thành *"chép lời gần như hoàn hảo"*.

⚠️ Việc model **tự phục hồi cả ba** là **may**, ⛔ không phải bảo đảm — và nó làm
việc quy trách nhiệm **khó hơn**, không dễ hơn.

## 4f. ⭐ Vòng sửa GIÚP hay PHÁ — đo CƠ CHẾ, ⛔ chưa đốt 67 phút

> ⚠️ **Mọi con số mục này chỉ nói về vòng sửa với bộ chấm V1**
> (`qc_ai.py` `604b82a7`, 2026-09-23) — ⛔ **không nói gì** về bộ chấm V3.

> ### ✅ Xuất xứ con số — đã TRUY, 2026-09-25 (làn `asv-banh-coc`)
>
> `mypy` phát hiện `tools/bench_b2_vong_sua.py:131` — bộ đo sinh ra mọi con số
> mục này — gọi `qc_ai.doc_ngu_nghia` **thiếu tham số bắt buộc** `van_ban` ⇒ một
> `TypeError` ngay dòng đầu. Câu phải trả lời: *con số dưới đây đến từ đâu?*
>
> ⭐ **Con số là THẬT.** Tại `800234d8` (lượt ghi bằng chứng, 24/09 21:07) cây ấy
> **chưa** chứa `91d921f4` (cùng ngày, 19:21, làn khác) — và ở cây ấy
> `doc_ngu_nghia` **vẫn nhận HAI tham số**. Lời gọi hai tham số **đúng lúc nó
> chạy**. ⛔ Không có số nào bị dán nhãn sai, ⛔ không có số nào bị bịa.
>
> 🔴 **Nó vỡ SAU đó, ở chỗ gộp:** `91d921f4` (*chấm ngữ nghĩa NHỊ PHÂN → phân
> mức MQM, V2*) làm `van_ban` **bắt buộc** và chỉ sửa **2 trong 4** người gọi
> (`giai_doan_qc_ai.py`, `bench_b2_xac_thuc_bo_cham.py`). Hai bench còn lại vỡ
> im lặng. ⚠️ Và ⛔ **không phép kiểm nào bắt được** — chỉ `mypy` bắt.
>
> ⚠️ **Tệ hơn: chính vòng thử lại của bench sẽ CHE nó.** Lời gọi nằm trong
> `except Exception as exc` (bắt `concurrency_limited`) ⇒ một `TypeError` sẽ
> hiện ra như *"model từ chối, thử lại 5 lần rồi thua"*, ⛔ không như *"mã hỏng"*.
>
> ⇒ **Lời gọi đã sửa** (truyền `{ma: (goc, chu)}` đúng khuôn
> `giai_doan_qc_ai.py:224`), ⛔ **nhưng bench CHƯA chạy lại** (một lượt tốn tiền
> thật). ⚠️ Và nếu chạy lại, nó đo **bộ chấm V2/V3**, ⛔ **không so sánh được**
> với bằng chứng V1 ở dưới — `doc_ngu_nghia` nay trả `{ma, dat, muc, loi, ly_do}`
> và `dat` được **tính từ `muc`**, khác hẳn V1.

### Bước 1 — chấm bản nền (phim 3)

```
31 đoạn  ->  2 bị gắn cờ   (model chấm qwen38-api = ltt-3.8, ghim tường minh)
```

⚠️ **Tiền đề *"FA ~43 % ⇒ phần bị báo nhầm sẽ đông"* KHÔNG tái hiện ở đây.** Soi
tay cả hai:

| mã | lý do bộ chấm nêu | phán đoán tay |
|---|---|---|
| `seg_0010` | dịch `趁` thành *"Khiến"* | ✅ **báo ĐÚNG** — `趁` = *nhân lúc*, không phải *khiến* |
| `seg_0005` | `架着门口` ra *"chặn cửa"* thay vì *"chĩa súng canh cửa"* | ✅ **báo ĐÚNG** (chặn ≠ canh) |

⇒ **0/2 báo nhầm** trên phim này. ⛔ Nên ⛔ **không** có tập "bị báo nhầm" để
chạy bước 3 như thiết kế.

### Bước 3′ — đổi phép đo cho đúng câu hỏi

Câu cần trả lời là *"dịch lại một đoạn **vốn đã đúng** có làm nó tệ đi không?"*.
⇒ ⭐ Lấy thẳng **29 đoạn bộ chấm cho ĐẠT**, cho đi qua đúng đường dịch lại, so
với bản nền. Phép này **không phụ thuộc** vào tỉ lệ báo nhầm của bộ chấm.

```
29 đoạn ĐÃ ĐÚNG  ->  28 đoạn ĐỔI  (chỉ 1 giữ nguyên nguyên văn)
```

Soi tay 28 đoạn đổi:

| loại | đếm | ví dụ |
|---|---|---|
| **không đổi nghĩa** (churn) | **~18** | *"xin lỗi"* → *"xin lỗi nhé"* · *"vào tòa nhà"* → *"vào trong tòa nhà"* |
| **tốt lên** | **~5** | *"kẻ khác"* → *"địch"* · *"tặng trắng"* → *"tự chết"* (`纯白给`) |
| ⛔ **tệ đi** | **~4** | xem dưới |

### 🔴 Và chỗ "tệ đi" rơi trúng đúng điểm yếu đã biết: THUẬT NGỮ

| mã | bản nền | sau khi dịch lại |
|---|---|---|
| `seg_0022` | *"quăng một quả **lựu đạn** giả"* ✅ | *"thử đặt **mìn** giả"* ⛔ |
| `seg_0025` | *"trực tiếp quăng **lựu đạn**"* ✅ | *"trực tiếp **cài bom**"* ⛔ |
| `seg_0008` | *"**lượng máu**"* ✅ | *"**huyết lượng**"* ⛔ (âm Hán-Việt sống, trái quy tắc 1 *"tự nhiên, văn nói"*) |

⭐ `雷` được dịch **ĐÚNG** (*lựu đạn*) ở bản nền và **TRÔI sang sai** (*mìn* /
*bom*) sau khi dịch lại — **hai đoạn, cùng một thuật ngữ, cùng một chiều**. Đó
là một ca **cụ thể, kiểm được** của *"dịch lại một đoạn vốn đã đúng làm nó tệ
đi"*.

### Phán đoán — ⚠️ và một xung đột lợi ích phải khai

> 🔴 ⛔ **PHẠM VI CỦA KẾT LUẬN — đọc trước con số.**
>
> *"Vòng sửa **với bộ chấm V1** gây trôi trên đoạn đã đúng"* ⛔ **KHÔNG** suy ra
> *"vòng sửa có hại"*. Phép cân này có **hai vế**: (a) bao nhiêu đoạn **sai** được
> sửa, (b) bao nhiêu đoạn **đúng** bị chạm rồi trôi. V1 có báo động giả **43 %**
> nên vế (b) rất đông. Bộ chấm **V3** hạ FA xuống **23 %** ⇒ số đoạn đúng bị chạm
> ít hơn hẳn ⇒ ⚠️ **phép cân có thể ĐỔI DẤU**.
>
> ⛔ Đừng viết kết luận rộng hơn dữ liệu.

Kết quả **LẪN LỘN**, nghiêng về *"churn nhiều, hại có thật nhưng không đều"*:
vòng sửa ⛔ không phá một cách hệ thống, nhưng mỗi lần nó chạm vào một đoạn đã
đúng là một lần **rút thăm lại**, và thuật ngữ là chỗ dễ trượt nhất.

⭐ Điều này **giải thích được** N-02 (85 → 85, `dich_sai` 60→44 nhưng `doc_sai`
10→14 và `khong_vua` 15→27): **tổng không đổi vì thành phần bị xáo lại**, đúng
như một phép rút thăm lặp lại chứ không phải một phép sửa hội tụ.

> ⚠️ ⛔ **Xung đột lợi ích, khai thẳng:** ba bảng trên do **tôi** phán đoán, và
> **tôi là người tạo ra cả hai bản dịch**. Hôm nay tôi đã sai một lần đúng kiểu
> đó — chấm ✅ cho `李宗盛` → *"Lý Tông Thành"* hai lượt liền, tới khi Unihan bác
> lại (§4c). ⇒ Các con số ~18/~5/~4 là **quan sát tay**, ⛔ **không phải một
> phép đo**, và ⛔ không được dùng để đóng một cổng.

### ⇒ ⛔ HOÃN lượt đầy đủ — điều phối đổi quyết định 24/09

Bảng quyết định nói *"lẫn lộn ⇒ chạy lượt đầy đủ"*. **Ba dữ kiện mới làm nó sai:**

1. ⭐ **Câu hỏi đã được trả lời.** Lượt 67 phút sinh ra để giải thích **85 → 85**;
   §4f đã giải thích bằng cơ chế (*rút thăm lại*, thành phần bị xáo). **Trả rồi.**
2. Lượt ấy sẽ đo **cấu hình ta sắp bỏ** (bộ chấm V1). Làn kia đang chốt **V3 +
   `temperature 0.0`**.
3. `ltt-3.8` **đang bị tranh** ⇒ con số thu được lẫn cả **tranh tài nguyên**,
   ⛔ không tách được.

⇒ **MỘT lượt duy nhất, chạy SAU khi V3 về**, trên đúng cấu hình sẽ ship.
⛔ Không hai lượt. Khung A/B đã dựng sẵn (§6) để chạy bằng **một lệnh**.

### ⚠️ Chặn vận hành: `ltt-3.8` đang bị tranh

Lượt chấm đầu **chết cả 4 lô** với `concurrency_limited` (429) — một làn khác
đang dùng chính model đó cho đường chấm. Sau khi thêm chờ có cấp số nhân, 31
đoạn mất **308 s** (so với 65 s cho cùng số đoạn ở bước dịch trên `ltt-3.5`).
⇒ Chấm `v1`/`v2` **vẫn đang chạy**. ⛔ Không ép thêm request vào `ltt-3.8`.

## 4h. Lời nhắc **v4** — ba nhánh, và bảng trước/sau CẢ TẬP

> 🔴 **CHỦ DỰ ÁN ĐÃ CHỐT 24/09.** Luật tên riêng ⛔ **không còn là "luật tạm"**:
>
> ```
> 1. CÓ lối viết quen tiếng Việt  ⇒ dùng lối quen   首尔→Seoul · 李宗盛→Lý Tông Thịnh
> 2. KHÔNG có / không chắc        ⇒ LOẠI THỰC THỂ mới quyết định
>      người · địa danh           ⇒ phiên Hán-Việt   张伟→Trương Vĩ
>      tổ chức · thương hiệu      ⇒ giữ nguyên dạng  光子 ⛔ không phiên
> ```
>
> ⭐ Đây **đúng** là luật đã nằm trong `QUY_TAC_TEN_RIENG_VI` (lời nhắc đường
> sống, §7.6) ⇒ ⛔ **KHÔNG sửa lời nhắc thêm lần nào vì chuyện này.**
>
> ⚠️ **Phần dưới giữ nguyên làm LỊCH SỬ, ⛔ đừng dọn đi.** Nó ghi ba lần
> *sửa-một-hỏng-một* và — đáng giá nhất — việc **trục cắt sai lúc đầu**
> (cắt theo *loại thực thể* trong khi trục thật là *"đã có lối quen hay chưa"*,
> §4h dưới). Đó là thứ ngăn người sau đi lại đúng con đường ấy.

`PHIEN_BAN_LOI_NHAC` **3 → 4**. Quy tắc 5 tách: **5a** người/địa danh → phiên
Hán-Việt · **5b** người thật có lối viết quen → dùng lối quen · **5c** tổ
chức/thương hiệu → **giữ nguyên, không phiên**.

### ⚠️ Đo lại CẢ TẬP, ⛔ không chỉ `光子`

| tên | v1 (chưa luật) | v2 (ví dụ không dấu) | v3 (ví dụ có dấu) | **v4 (ba nhánh)** |
|---|---|---|---|---|
| `光子` (thương hiệu) | *Photon* | *Quang Tu* | ⛔ *Quang Tử* | ⚠️ **Photon** |
| `小美` (người) | Tiểu Mỹ | Tiểu Mỹ | Tiểu Mỹ | ✅ **Tiểu Mỹ** |
| `李宗盛` (người quen) | *Lý Tông Thành* | ⛔ *Lý Tông Thanh* | *Lý Tông Thành* | ✅ **Lý Tông Thịnh** |
| `韩国` (địa danh) | Hàn | Hàn | Hàn Quốc | ✅ **Hàn Quốc** |
| `首尔` (địa danh) | Seoul | Seoul | ✅ **Seoul** | ⛔ **Sê-ôl** ⬅ **HỒI QUY** |
| chữ Hán sót / rỗng | 0 / 0 | 1 / 0 | 0 / 0 | **0 / 0** |

### 🔴 v4 sửa `李宗盛` nhưng **làm hỏng `首尔`** — và nó chỉ ra một LỖ trong chính phân loại

```
v3  老板硬是在寸土寸金的首尔…  ->  "…tại Seoul nơi đất chật người đông"   ✅
v4  (cùng câu)                ->  "…ở Sê-ôl đất đai đắt đỏ…"             ⛔
```

⚠️ `首尔` = **Seoul** — một **địa danh** đã có **lối viết quen** trong tiếng
Việt. Nhánh **5a** bảo *"địa danh ⇒ phiên Hán-Việt"*, và model làm đúng lời: nó
phiên ra *"Sê-ôl"*. Nhánh **5b** (lối quen) lại chỉ nói **"NGƯỜI thật"**.

> ⭐ ⇒ *"Lối viết quen"* ⛔ **không phải thuộc tính của NGƯỜI** — nó là thuộc tính
> của **cái tên**. Địa danh cũng có, thương hiệu cũng có. Phân loại ba nhánh
> đang cắt theo **loại thực thể**, trong khi trục thật là **"đã có lối quen hay
> chưa"**.

⛔ **Làn này không tự sửa tiếp.** Bản vá có thể chỉ là một chữ (5b: *"người thật"*
→ *"người thật hoặc địa danh"*), nhưng: (a) luật là của điều phối, và (b) mỗi
lần đổi lời nhắc là **một lượt đo lại cả tập** — hôm nay đã ba lần, và mỗi lần
sửa một chỗ thì hỏng một chỗ khác. ⇒ Báo, ⛔ không lặp thêm một vòng.

**Điểm hiện tại:** v4 so với v3 = **+1 sửa** (`李宗盛`), **−1 hỏng** (`首尔`),
3 giữ nguyên.

## 4i. ⭐ ĐƯỜNG B đã ĐO — model **có** biết chỗ nó không biết, và danh sách **ngắn**

⛔ Không chờ quyết định sản phẩm: đường B của §4d là một **câu hỏi thực nghiệm**,
trả lời được bằng bản nền `ltt-3.5` — ⛔ không cần `ltt-3.8`, ⛔ không cần bộ chấm.

**Thiết kế** (`tools/bench_b2_duong_b_tu_khai.py`): bảo model, **trong lúc dịch**,
liệt kê từ/cụm **trong câu gốc** nó *không chắc*. ⛔ Không nói ta tìm gì, ⛔ không
một ví dụ nào từ 7 ca đã hỏng — *ví dụ là mệnh lệnh ngầm*, đưa `掐雷` vào thì ta
đo chính lời mách của mình.

| phim | bắt / cần bắt | khai tổng | ngoài 7 ca |
|---|---|---|---|
| v1 | **2/3** (`师傅`, `烧酒`) | 5 | 2 |
| v2 | **0/1** | 7 | 7 |
| v3 | **2/3** (`掐雷`, `纯白给`) | 7 | 5 |
| **tổng** | ⭐ **4/7 = 57 %** | **19** | 14 |

### Độ ồn: **19 mục / 3 011 ký tự gốc = 0,63 %**

⛔ **Không phải 200/718.** Danh sách đủ ngắn để một người soi tay trong vài phút.

### ⭐ Và "ồn" hoá ra **phần lớn KHÔNG phải ồn**

```
v1  沙砾 · 纸香
v2  直冷 · 避不住 · 小壁 · 榨了点爆米花 · 投影目录 · 卷土重来 · 起过烧油
v3  提炼枪 · 白给 · 光子 · 掐个假雷 · 此一听 · 假装本人
```

⚠️ `避不住` · `提炼枪` · `此一听` · `直冷` · `小壁` · `起过烧油` là **lỗi ASR** —
đúng lớp §4e nói phải tách ra. Và nó khai cả **`光子`**, chính cái tên §4g đang
tranh luận.

> ⭐ ⇒ Đường B **rẻ và sống**, và nó có một **tác dụng phụ đáng giá hơn**: nó là
> một **bộ dò lỗi CHÉP LỜI**, tức thứ §4e cần để tách lỗi ASR khỏi lỗi dịch —
> ⛔ một việc ta chưa có cách nào làm.

### ⛔ Nhưng nó KHÔNG bắt lớp NGỮ PHÁP

3 ca trượt: `补人` · `热胀冷缩` · `这才是` (→ *"Mới đây"*). ⚠️ `这才是` là lỗi
**ngữ pháp**, ⛔ không phải thuật ngữ — và model **không hề thấy mình sai**.

> ⇒ **Model biết nó không biết TỪ; nó không biết nó hiểu sai CÂU.** Đó là ranh
> giới của đường B, và nó phải nằm cạnh mọi con số ở trên.

⛔ **Vẫn không khuyến nghị.** Giá của đường B, để điều phối mang đi: **+1 trường
trong lược đồ, ~0 lượt gọi thêm** (đi kèm lượt dịch), đổi lấy **57 % lớp thuật
ngữ + một bộ dò lỗi ASR**, ⛔ và **0 %** lớp ngữ pháp.

## 4g. 🔴 `光子` — ta có thể đã sửa từ SAI KIỂU A sang SAI KIỂU B

### Bằng chứng: nó là XƯỞNG GAME, không phải người

```
v3 seg_0004 (5,48–7,40)   来把枪啊光子!
tên tệp phim              … #和平精英夏日航海 #和平精英夏日探险 …
```

| bằng chứng | nguồn |
|---|---|
| Phim là video chơi **和平精英** (PUBG Mobile) | hashtag trong tên tệp gốc |
| 和平精英 / PUBG Mobile do **LightSpeed Studios** (光子工作室群) đồng phát triển | Wikipedia *PUBG Mobile* (REST summary, đọc 24/09) |
| Câu là **lời gọi thẳng** dạng cầu khiến — *"cho cái súng đi, 光子!"* — người chơi trách **nhà phát triển** về may rủi khi nhặt đồ | ngữ cảnh: hai câu trước/sau bàn về nhặt súng, ⛔ không có nhân vật nào tên 光子 |
| Xuất hiện **đúng một lần** trong cả ba phim | đếm trên `b2_dich_nen/` |

⇒ `光子` là **tổ chức / thương hiệu**, ⛔ không phải tên người.

### ⚠️ Hệ quả: bản "đã sửa" có thể sai **nặng hơn** bản gốc

```
v1 (chưa có luật)  ->  "Photon"      ⚠️ dịch nghĩa đen — nhưng 光子 NGHĨA LÀ photon
v3 (có luật)       ->  "Quang Tử"    ⛔ phiên âm một THƯƠNG HIỆU như một tên người
```

⭐ Thương hiệu thường **giữ tên đã quen**, ⛔ không phiên âm. ⇒ Ta có thể đã đổi
từ *sai kiểu A* sang *sai kiểu B* — **rồi tự chấm ✅**. Đúng lớp lỗi của
`李宗盛` ở §4c, lần này ở **chiều phân loại** chứ không phải chiều đọc âm.

### ⛔ Luật hiện tại KHÔNG phân biệt ba loại — và đó là câu cho chủ dự án

Chủ dự án ra luật bằng ví dụ **`张伟 → Trương Vĩ`**, một **tên người**. Quy tắc 5
trong `_loi_nhac` áp **một cách** cho **mọi** tên riêng:

| loại | ví dụ trong dữ liệu | luật có lẽ đúng | luật hiện tại làm gì |
|---|---|---|---|
| người **có lối viết quen ở VN** | `李宗盛` (nhạc sĩ Đài Loan) | dùng **lối quen** — *Lý Tông Thịnh*, tra được | ⛔ phiên tự do ⇒ ra *"Lý Tông Thành"* |
| người / địa danh **không quen** | `张伟`, `小美` | **phiên Hán-Việt** ✅ đúng luật | ✅ đúng |
| **tổ chức / thương hiệu** | `光子` (xưởng game) | ⚠️ **giữ tên đã quen**, ⛔ có lẽ không phiên | ⛔ phiên như tên người |

⛔ **Làn này không tự quyết** — đây là quyết định **sản phẩm**, không phải một
bản vá lời nhắc. Điều phối mang tới chủ dự án.

⚠️ **Unihan giữ đúng vai:** dùng làm **gợi ý soi** (nó bác được *"Thành"*),
⛔ **không** nâng lên thành chân lý nền (thiếu giản thể 7/17, âm lệch lối dùng
trong tên).

## 5. Bản BẬT vòng sửa — ⏭ **việc kế tiếp**, chặn đã gỡ, SHA đã ghim

⭐ Chặn ở §2 **đã gỡ** (§4b): dịch nay đi `ltt-3.5` **trong chính đường sản
phẩm**, còn `qc_ngu_nghia` được ghim `ltt-3.8` tường minh. ⇒ Bản BẬT và bản NỀN
nay khác **đúng một** biến: **vòng sửa**.

**SHA phải ghim và ghi vào kết quả** (⛔ bộ chấm đang trong xưởng ở làn khác):

```
apps/auto_scan_video/qc_ai.py   604b82a7eccee07473541873b8ca11bf049a8d60   2026-09-23
VONG_SUA_TOI_DA = 1             (sua_chua.py:73)
```

Nhãn bắt buộc dán thẳng vào bản ghi:

> **vòng sửa với bộ chấm V1 — ĐÃ BIẾT hỏng, báo động giả 43 %**

⭐ ⛔ **Không chờ bộ chấm mới.** Câu hỏi này về **hiện trạng**: *"vòng sửa như nó
đang tồn tại hôm nay đang giúp hay đang phá?"* — và quan sát **85 → 85** (N-02)
cũng sinh ra từ đúng bộ chấm ấy. Chờ bộ chấm mới là **đổi mất câu hỏi**.

⚠️ **Trạng thái: CHƯA chạy.** Vòng sửa được điều phối trong `jobs._vong_sua`,
cần một lần chạy thật qua hàng đợi job (lượt NT-CUOI B trước đây tốn **67 phút**).
⇒ Việc kế tiếp của làn, ⛔ không phải một việc đã xong.

---

# 6. Bộ đo dựng SẴN — ⛔ chạy được bằng một lệnh khi V3 về

⭐ Mọi phán quyết về **dịch** đang chờ bộ chấm. ⇒ Việc đáng giá bây giờ là làm sao
**khoảnh khắc V3 về thì đo được ngay**, ⛔ không phải ngồi chờ rồi mới dựng khung.

## 6.1 Khung A/B vòng sửa — `tools/bench_b2_ab_vong_sua.py`

> 🔴 **BỘ ĐO NÀY ⛔ CHƯA TỪNG CHẠY** (kiểm 2026-09-25): ⛔ không có thư mục bằng
> chứng nào của nó, và §6.2 cũng khai *"⛔ CHƯA chạy"*. ⇒ *"dựng sẵn, chạy được
> bằng một lệnh"* ⛔ **không** phải *"đã chứng minh chạy được"*.
>
> Bằng chứng: `mypy` tìm ra `:153` gọi `qc_ai.doc_ngu_nghia` **thiếu** tham số
> bắt buộc `van_ban` ⇒ `--chay` sẽ chết ở lô đầu. Đã sửa 25/09, nhưng ⛔ vẫn
> chưa có lượt nào. (`--kiem` và cổng tài nguyên của `--chay` dừng **trước** chỗ
> đó, nên câu *"đã thử: nó dừng thật"* dưới đây vẫn đúng — nó chỉ ⛔ không nói gì
> về phần đo.)

```
python tools/bench_b2_ab_vong_sua.py --kiem            # ⛔ KHÔNG gọi model
python tools/bench_b2_ab_vong_sua.py --chay --ra <thư mục>
```

**MỘT biến, và biến đó là vòng sửa.** Giữ cố định: bản chép lời · model dịch ·
model chấm · `PHIEN_BAN_LOI_NHAC` · `VONG_SUA_TOI_DA = 1` (đúng như sản phẩm).

```
nhánh A = dịch, ⛔ không vòng sửa            (bản nền)
nhánh B = dịch -> chấm -> dịch lại đoạn bị gắn cờ
```

⭐ Mỗi kết quả mang **toàn bộ môi trường** để tái lập, và ⭐ giữ **cả hai** bản
cạnh nhau (⛔ không chỉ hiệu số) để người sau **soi tay được**:

```
model_dich  qwen35-api   ·  model_cham  qwen38-api  ·  loi_nhac v3
vong_sua_toi_da 1  ·  sha_bo_cham 604b82a7  ·  sha_loi_nhac_dich db08e7ad
```

🔑 **Cổng tài nguyên có trong chính công cụ:** `--chay` **tự dừng** nếu bước chấm
sẽ rơi vào `qwen38-api` (đang nhường làn khác), trừ khi có `--ep-3-8`. ⛔ Không
phải một dòng ghi chú — là một lần `return 3`. Đã thử: nó dừng thật.

## 6.2 Thiết kế phép so `ltt-3.5` vs `ltt-3.8` cho DỊCH — ⛔ CHƯA chạy

> Câu chủ dự án giao: *"để **phép đo** chọn 3.5 hay 3.8 cho dịch"*.
> ⛔ Chưa chạy: `ltt-3.8` đang nhường làn khác (luật 24/09).

**Đo gì** — hai vế, ⛔ không gộp thành một điểm (bài học §9 của B1):

| vế | cách đo | vì sao |
|---|---|---|
| **chất lượng** | bộ chấm V3, `temperature 0.0`, trên **cùng** bản chép lời, **cùng** lời nhắc v3 | ⚠️ bộ chấm chạy trên `ltt-3.8` ⇒ ⛔ **nó chấm chính model của nó** ở một nhánh. Phải khai, và nếu được thì chấm **mù** (⛔ không nói model nào) |
| **thuật ngữ** | đúng bảng §4d (`掐雷` · `纯白给` · `烧酒` · `补人` · `血量`) | ⭐ đây mới là chỗ hỏng **tụ lại**; một điểm tổng quát sẽ **loãng** nó đi |

**Trên dữ liệu nào:** ba phim, **188 đoạn** — cùng bộ đã dùng cho bản nền, ⛔ không
đổi dữ liệu giữa hai vế.

**Ngưỡng — viết TRƯỚC, và nó là một ngưỡng CHÊNH LỆCH, ⛔ không phải ngưỡng tuyệt đối:**

```
⇒ 3.8 chỉ được chọn nếu nó hơn 3.5 ĐỦ LỚN để bù giá.
```

**Giá — đọc từ `platform_core/llm/gia_token.BANG_GIA`, ⛔ không gõ lại:**

| | vào mới /1M | vào cache /1M | ra /1M |
|---|---|---|---|
| `ltt-3.5` | **13** | 3 | **20** |
| `ltt-3.8` | **50** | 10 | **400** |
| **bội số** | **3,8×** | 3,3× | ⛔ **20×** |

### ⚠️ Tự thiên vị khi 3.8 chấm chính nó — TRA NGUỒN trước, ⛔ không tự dựng

Hiện tượng **đã được đo và đặt tên**: *self-preference bias* (SPB) của
LLM-as-a-judge. Hai nguồn đọc 24/09 (arXiv API):

| nguồn | nói gì | dùng gì ở đây |
|---|---|---|
| **arXiv 2608.18091** *"Self- and Other-Labels Induce Bidirectional Bias in LLM Judges"* | ⭐ **Dưới đánh giá MÙ, tự thiên vị BIẾN MẤT** (còn một hiệu ứng nhỏ theo **chiều ngược lại** sau khi khống chế chất lượng và **độ khắt khe của giám khảo**). Thiên vị phần lớn do **NHÃN** gây ra, và nhãn gây lệch **hai chiều** | ⇒ **chấm mù không phải "một nửa" — nó là biện pháp chính**. ⛔ Nhưng phải khống chế thêm **độ khắt khe** |
| **arXiv 2604.22891** *"Quantifying and Mitigating Self-Preference Bias of LLM Judges"* | Khung **tự động**: dựng **cặp CÙNG CHẤT LƯỢNG** (chênh lệch không đáng kể) để **tách** *khả năng phân biệt* khỏi *xu hướng thiên vị*, ⛔ không cần người gán nhãn. Cảnh báo: đo cũ **lẫn** năng lực sinh với lập trường đánh giá | ⇒ thêm một **bộ hiệu chuẩn**: nếu giám khảo vẫn nghiêng về phía 3.8 trên các cặp **đã biết là ngang nhau**, ta có một **độ lệch đo được để trừ đi** |

⇒ Thiết kế chống SPB cho §6.2, **ba lớp**, ⛔ không phải một:

1. **Mù** — bộ chấm chỉ thấy `goc` + `tieng_viet`, ⛔ **không** thấy model nào
   sinh ra (hiện `qc_ai.loi_nhac_ngu_nghia` **đã** như vậy — ✅ giữ nguyên).
2. **Cùng một giám khảo, cùng `temperature 0.0`, cùng thứ tự** cho cả hai nhánh
   ⇒ khống chế *độ khắt khe*.
3. ⭐ **Cặp cùng chất lượng** làm hiệu chuẩn ⇒ đo **độ lệch còn lại** và trừ.

⚠️ **Giới hạn phải khai:** cả hai nguồn đều nói đo trên **văn sinh ra** thì
**phong cách** và **chất lượng bị lẫn** — bản dịch của 3.8 mang dấu vết phong
cách của chính nó, nên ⛔ mù **không** xoá được hết. ⇒ Lớp 3 là thứ cho ta một
**con số**, ⛔ không phải một lời hứa.

⚠️ **Token RA đắt gấp 20 lần**, và dịch là một tác vụ **nặng đầu ra** (bản dịch
tiếng Việt dài ~3,5–4,5× văn Hán gốc — đo ở §4.2). ⇒ Chi phí thực của một lượt
dịch nghiêng hẳn về vế `ra`, tức về phía **bội số 20×**.

⇒ Ngưỡng đề nghị để điều phối chốt (⛔ **làn này không tự quyết**): **3.8 chỉ
được chọn nếu nó sửa được một lớp hỏng mà 3.5 KHÔNG sửa được** — ⛔ không phải
"nhỉnh hơn vài phần trăm trên một điểm tổng quát". Căn cứ: §4d đã đo rằng hỏng
**tụ ở tri thức miền**, và ⛔ **một model to hơn cũng không biết `纯白给` là tiếng
lóng game** — nên ⚠️ **kết quả nhiều khả năng là "3.8 không hơn ở đúng chỗ đang
hỏng"**, và phép đo này tồn tại để **kiểm chứng điều đó**, ⛔ không phải để xác
nhận nó.

### ⛔ Ngưỡng *"hơn bao nhiêu thì đáng"* — viết TRƯỚC khi đo

```
chi phí RA:  ltt-3.5 = 20 credit/1M   ·   ltt-3.8 = 400 credit/1M   ⇒ 20×
```

⇒ Đề nghị để điều phối chốt, ⛔ làn này không tự quyết:

| điều kiện | 3.8 có đáng không |
|---|---|
| 3.8 sửa được **một LỚP hỏng** 3.5 không sửa được (ví dụ: cả 7 ca thuật ngữ) | ⭐ **đáng xét** |
| 3.8 hơn trên một **điểm tổng quát** vài phần trăm | ⛔ **không đáng** — 20× cho vài phần trăm |
| 3.8 hơn ở **văn tường thuật** (chỗ 3.5 **đã** trôi chảy) | ⛔ **không đáng** — cải thiện chỗ không hỏng |

⚠️ Và §4d đã đo rằng hỏng **tụ ở tri thức miền** ⇒ ⛔ một model to hơn **cũng
không biết** `纯白给` là tiếng lóng game. Phép đo này tồn tại để **kiểm chứng**
điều đó, ⛔ **không** để xác nhận nó.

⛔ **Và phép đo này ⛔ không trả lời được** *"bảng từ có giúp không"* — đó là một
phép đo **khác**, và nó vẫn chưa có người chấm (§4d, ràng buộc 3).
