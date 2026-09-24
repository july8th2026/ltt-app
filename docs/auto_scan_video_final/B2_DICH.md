# B2 — cổng DỊCH (zh→vi)

> Làn `b1-cắt-lại` → `b2-dịch`, 24/09/2026. Đứng trên bản chép lời **mới** của
> B1 (`bang_chung/b1_chep_loi_moi/`): có dấu câu, có mốc từng từ, CER 3/3 ĐẠT.

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

### ⇒ Theo bảng quyết định: chạy lượt đầy đủ

Kết quả *"lẫn lộn"* ⇒ **cần con số đường sản phẩm**. Nhãn và SHA đã soạn sẵn ở
§5. ⛔ Chưa chạy — và nó nên chạy **sau** khi `ltt-3.8` rảnh (xem dưới).

### ⚠️ Chặn vận hành: `ltt-3.8` đang bị tranh

Lượt chấm đầu **chết cả 4 lô** với `concurrency_limited` (429) — một làn khác
đang dùng chính model đó cho đường chấm. Sau khi thêm chờ có cấp số nhân, 31
đoạn mất **308 s** (so với 65 s cho cùng số đoạn ở bước dịch trên `ltt-3.5`).
⇒ Chấm `v1`/`v2` **vẫn đang chạy**. ⛔ Không ép thêm request vào `ltt-3.8`.

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

