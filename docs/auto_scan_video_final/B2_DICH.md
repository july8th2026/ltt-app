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

## 5. ⛔ Bản BẬT vòng sửa — CHƯA chạy, và lý do là một chặn thật

Để so được, bản BẬT phải khác bản NỀN **đúng một biến**: vòng sửa. Nhưng vòng
sửa chạy **trong đường sản phẩm**, mà đường đó lấy model từ
`manifest.model_llm_noi_bo = "ltt-3.8"` (§2). ⇒ Chạy bây giờ thì hai bản khác
**hai** biến — model **và** vòng sửa — và hiệu số giữa chúng ⛔ **không quy được
cho ai**, đúng cái bệnh bản nền sinh ra để chữa.

⚠️ Thêm nữa: vòng sửa gọi `qc_ai`, đang **trong xưởng** ở làn khác. Đo một vòng
sửa chạy bằng một bộ chấm đang bị sửa là đo một thứ **sẽ đổi**.

⇒ ⛔ Chờ điều phối xếp thứ tự, ⛔ không tự sửa chỗ dùng chung.
