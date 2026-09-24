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

## 5. ⛔ Bản BẬT vòng sửa — CHƯA chạy, và lý do là một chặn thật

Để so được, bản BẬT phải khác bản NỀN **đúng một biến**: vòng sửa. Nhưng vòng
sửa chạy **trong đường sản phẩm**, mà đường đó lấy model từ
`manifest.model_llm_noi_bo = "ltt-3.8"` (§2). ⇒ Chạy bây giờ thì hai bản khác
**hai** biến — model **và** vòng sửa — và hiệu số giữa chúng ⛔ **không quy được
cho ai**, đúng cái bệnh bản nền sinh ra để chữa.

⚠️ Thêm nữa: vòng sửa gọi `qc_ai`, đang **trong xưởng** ở làn khác. Đo một vòng
sửa chạy bằng một bộ chấm đang bị sửa là đo một thứ **sẽ đổi**.

⇒ ⛔ Chờ điều phối xếp thứ tự, ⛔ không tự sửa chỗ dùng chung.
