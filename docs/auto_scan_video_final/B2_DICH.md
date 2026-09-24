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

## 4h. Lời nhắc **v4** — luật TẠM ba nhánh, và bảng trước/sau CẢ TẬP

> ⛔ **Đây là luật TẠM do ĐIỀU PHỐI thu hẹp, chưa phải chủ dự án chốt ba nhánh.**
> Chủ dự án ra luật bằng ví dụ `张伟 → Trương Vĩ` — một **tên người**; đem nó áp
> lên một **thương hiệu** là **ta** nới rộng, nên thu về là **trả lại** lời họ
> nói. ⛔ Đừng đọc bảng này như thể ba nhánh đã được chốt.

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
