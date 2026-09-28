# B16 — Dựng lại CHUỖI BƯỚC của ASV theo module Render của Viral

**Ngày:** 2026-09-28 · **Nguồn đối chiếu:** `B14_SO_SANH_VIRAL/` (6 tệp, 5 làn +
V6 chuỗi bước) · **Nền:** `main = 0a95d728`

**Chủ dự án chốt (28/09, qua bốn câu hỏi khoá):**
1. **Copy CHUỖI BƯỚC**, giữ hợp đồng nền tảng.
2. **Gộp thành MỘT lần encode.**
3. **Thêm đủ 5–6 luồng nền như họ.**
4. **Bỏ cả năm giai đoạn** ta có mà họ không — khớp đúng Viral.

---

## 1. 🔴 HAI chỗ xung đột giữa bốn quyết định — và cách giải

⚠️ Ghi ra trước mọi thứ khác, vì một plan dựng trên ràng buộc mâu thuẫn sẽ vỡ ở
giữa, và lúc đó ⛔ không ai biết vỡ vì quyết định nào.

### 1.1 Quyết định (1) ⇄ (3): *"giữ checkpoint"* và *"luồng nền"* ⛔ KHÔNG cùng tồn tại

(1) nói **giữ hợp đồng nền tảng** = mỗi bước là một job có **vân tay + lineage +
checkpoint**. (3) nói **thêm luồng nền**. Nhưng một luồng nền **bên trong** một job
làm checkpoint **mất nghĩa**: job chết giữa chừng ⛔ không biết luồng đã làm tới
đâu, nên ⛔ không thể chạy tiếp mà cũng ⛔ không thể chạy lại an toàn.

⭐ **Đường giải, và nó TỐT HƠN cả hai:** Viral dùng **luồng** vì họ có **một tiến
trình**. Ta có **job runner** — nên **đối ứng** của một luồng nền của họ ⛔ không
phải một `threading.Thread`, mà là **một JOB SONG SONG**.

```
Viral:  mot tien trinh  ->  5-6 threading.Thread
Ta:     job runner      ->  5-6 JOB chay dong thoi, moi job co
                            van tay + lineage + checkpoint rieng
```
🔑 Job song song **giết được**, **chạy lại được**, **cache được** — luồng nền thì
⛔ không. ⇒ Ta lấy **đúng tính song song** mà (3) đòi, và ⛔ không mất thứ (1) đòi.

⚠️ **Việc thật phải làm:** `pipeline.CHUOI` hiện là **dây thẳng** vì các khai
`sau=` nối một mắt — ⛔ **không** vì `job_runner` thiếu khả năng.
`pipeline.ke_tiep(da_xong)` đã trả về một **danh sách**. ⇒ Biến `CHUOI` thành một
**DAG thật** là đổi **bản khai**, ⛔ không phải đổi bộ chạy.

⛔ **Còn một cổng phải giữ:** Viral mở luồng nền theo **điều kiện đo được**
(`RAM ≥ 15,0 GB` **và** `VRAM ≥ 8 GB`, `localize.py:15633,15639`), ⛔ không theo một
cờ. Ta có `tai_nguyen_suat` + `gpu_lease` + `cua_so_yen` — ⇒ cổng của ta là **suất
tài nguyên**, và nó **chặt hơn** cổng của họ. Máy này **treo hai lần** ngày 28/09;
song song ⛔ không được vượt cổng ấy.

### 1.2 Quyết định (4): bỏ năm giai đoạn — nhưng ⛔ ĐỪNG bỏ DỤNG CỤ

`image_finish` tan theo (2) ✅ — gộp một lần encode **chính là** bỏ nó.
`edit_plan` nay luôn ra kế hoạch rỗng (`41c11be3`) ⇒ bỏ khỏi `CHUOI` là đúng.

🔴 Nhưng `qc` · `qc_do_luong` · `qc_ai` là **lớp đã phát hiện mọi khiếm khuyết của
phiên này**: 32 giây mất tiếng · hai đoạn nén oan · độ phủ `76,9 %` · bốn ca
cần-gạt-không-nối. Viral ⛔ **không có đại lượng khách quan nào** về tiếng hay hình
(grep 260 tệp: ⛔ không một `pesq`/`squim`/`libvmaf`/`blackdetect`).

⭐ **Và đây là chỗ *"khớp đúng Viral"* có một nghĩa TỐT HƠN nghĩa hiển nhiên:**
Viral **CÓ** tự kiểm — `_kiem_lo_sau_render` (bước 31) OCR lại **bản RA**, và nó
nằm **BÊN TRONG** `burn_phude`, ⛔ không phải một giai đoạn riêng. Cộng
`chat_luong.py` là một **module gọi được**, ⛔ không phải một bước.

⇒ **Khớp đúng hình dạng của họ** nghĩa là:
```
BO khoi CHUOI:  edit_plan · image_finish · qc · qc_do_luong · qc_ai   (5 giai doan)
GIU lam:        · mot BUOC TU KIEM ben trong lan encode cuoi  (nhu buoc 31 cua ho)
                · cac MODULE goi duoc:  qc.kiem() · do_luong · MetricX
                  -> cong cu chan doan + phep kiem goi duoc, KHONG la giai doan
```
🔑 Ta được **chuỗi 8 giai đoạn khớp Viral** (thay 13), **và** ⛔ không mất dụng cụ
đã bắt mọi lỗi hôm nay. Nếu bỏ luôn dụng cụ thì lần sau một bản giao thiếu 32 giây
thoại sẽ **đi thẳng tới khách**, và ta biết điều đó vì hôm nay nó **đã** xảy ra —
chỉ là `qc_do_luong` bắt được.

⚠️ `qc_ai` gọi model ⇒ **tốn tiền mỗi lượt**. Nó ⛔ không nên là một bước tự
chạy; làm **công cụ gọi tay** là đúng hơn cả cho nó.

---

## 2. CHUỖI MỚI — 8 giai đoạn, khớp 33 bước của Viral

| # | giai đoạn ASV mới | gộp bước Viral | song song |
|---|---|---|---|
| 1 | `media_prepare` | 0 (**cắt ĐẦU** *) · 1 · 2 · 3 · 8 · 32 | — |
| 2 | `audio_prepare` | 4 · 5 (demucs · tách nhạc) | 🔀 **song song với 3** |
| 3 | `transcribe` | 9 · 10 · 11 · 12 | 🔀 **song song với 2** |
| 4 | `vung_che` **(MỚI)** | 6 · 7 · 20 (dò dải che, bốn nấc) | 🔀 **song song với 3, 5** |
| 5 | `content_process` | 13 · 14 · 15 · 16 · 17 · 21 (banner) | — |
| 6 | `voice_synthesis` | 19 · 22 · 23 | — |
| 7 | `timing_align` | 24 · 25 · 26 · **27 (căn sub theo onset THẬT)** | — |
| 8 | `render` | 28 · **29 (MỘT encode: + cắt CUỐI *)** · 30 · **31 (tự kiểm)** | — |

⇒ **13 → 8 giai đoạn**, thêm **một** giai đoạn mới (`vung_che` — bước 20 của họ mà
ta ⛔ không có ai chịu trách nhiệm), và **ba** nhánh song song.

\* 🔴 **CẮT ĐẦU/CUỐI — tôi đọc SAI, chủ dự án sửa 28/09.**

Bản đầu của mục này viết *"giữ cách của ta (cắt sau cùng cả hai đầu); họ đã tự lùi
một nửa"*. **Sai**, và lý lẽ sụp ngay khi có quyết định (2):

> ⭐ *"Cắt đầu đuôi họ làm đầu là ĐÚNG nếu chỉ **MỘT lần render** mp4."*

⇒ **Với một lần encode thì ⛔ không tồn tại "lượt sau" để cắt ở cuối.** Cách của ta
(cắt cả hai đầu ở GĐ2 + `ban_do_thoi_gian` đổi mốc) **phụ thuộc vào việc có lượt
thứ hai**. Bỏ lượt thứ hai ⇒ phép đổi mốc **⛔ không còn chỗ nào để sống**.

### 🔑 Và nguyên tắc thật ⛔ không phải "sớm hay muộn" — mà là **có DỊCH TRỤC hay không**

| phép | dịch trục? | ⇒ làm ở đâu |
|---|---|---|
| **cắt ĐẦU** | ✅ **CÓ** — dịch **mọi** mốc hạ nguồn đi `−cat_dau` | **`media_prepare`, TRƯỚC ASR** — để ⛔ không một bước hạ nguồn nào cần biết |
| **cắt CUỐI** | ⛔ **KHÔNG** — chỉ **cắt ngọn** | **trong lần encode DUY NHẤT** (`render`) |

⇒ ⭐ Đó **chính xác** là hình dạng cuối của Viral (`_cat_cuoi_gop`), và nó ⛔ **không
phải** *"lùi một nửa vì nghi ngờ"* — nó là một **phép chia có nguyên tắc theo việc
phép biến đổi có dịch trục hay không**. Cách đọc của chủ dự án đúng; cách đọc của
tôi sai.

### Cái giá, ghi đủ
1. `cat` phải biết **trước ASR**. ✅ Nó nằm trong `run.settings` từ lúc tạo lần
   chạy ⇒ ⛔ không có gì chặn.
2. ⚠️ Khách đổi `cat` **sau** ⇒ phải **chạy lại ASR**. Hôm nay việc ấy rẻ (chỉ
   GĐ2). ⇒ **Mất tính linh hoạt đó**, và mất vì quyết định **một lần encode**, ⛔
   không vì vị trí cắt.
3. ⭐ **Được lại một thứ đáng hơn:** `ban_do_thoi_gian` cho vế **đầu** biến mất —
   mọi mốc hạ nguồn **đã nằm trên trục bản giao**. Bớt **một** phép đổi mốc, và
   phép đổi mốc **chính là chỗ mọi con bọ của B6/B8/B9 đã sống**.

### 2.1 Bốn bước của họ ta PHẢI thêm
| bước | việc | giá trị |
|---|---|---|
| **27** | **căn phụ đề theo ONSET THẬT của giọng** | `5` — ⭐ và ta **đang mắc lỗi này**: `ban_dung.py:127-147` đặt lớp cho `ma` **dẫn**, `phu_de.py:1066` canh **từng** `ma` theo kế hoạch ⇒ khe gộp làm chữ lệch tiếng |
| **29** | MỘT lần encode | bớt một thế hệ nén + nửa CPU |
| **20** | che chữ gốc **là một giai đoạn** | nay ⛔ không ai chịu trách nhiệm |
| **12·17·23** | ba chế độ chạy phần `chi_asr`/`chi_dich`/`chi_dub` | rút ngắn **mọi** vòng sửa |

### 2.2 Giữ nguyên của ta — ⛔ KHÔNG copy
- **TTS** (`ltt_voice`) và **LLM** (`ltt_llm`) — chủ dự án chốt.
- Bậc thang nắn thời lượng vừa dựng (`28b264da`): xén lặng TTS → tăng tốc 1,15 →
  trôi → **nén thêm thay vì bỏ câu**. ⭐ **Tốt hơn Viral**: họ cho video dài ra
  ~10 % (phá `D-ASV-03` của ta); ta ⛔ không bao giờ bỏ câu **và** ⛔ không bao giờ
  dài hơn nguồn. Điểm vỡ `k = 2,8` so với `1,15` trước đó.
- Vân tay · lineage · checkpoint · sổ credit · khoá kho có phạm vi chủ sở hữu.
- `chunk_size = 10` (`d109cb17`) — mượn từ họ, đã đo trên phim của ta.

---

## 3. Thứ tự triển khai

```
P0  §1.2  BO 5 giai doan khoi CHUOI, GIU lam module + mot buoc tu kiem
P0  §2.1  buoc 29: MOT lan encode (hoa tan `image_finish`)
P1  §2.1  buoc 27: can phu de theo onset THAT   <- dang la MOT LOI, khong phai tinh nang
P1  §2.1  buoc 20: giai doan `vung_che` moi
P1  §1.1  CHUOI thanh DAG that: `audio_prepare` ∥ `transcribe` ∥ `vung_che`
P2  §2.1  ba che do chay phan `chi_asr`/`chi_dich`/`chi_dub`
P2        khoa scan CHIA SE giua job (buoc 10)
P3        nghiem thu: mot gate, deploy, T1a-ter tren worker that, soat frame
```

⚠️ **P1 DAG đi SAU hai P0**, vì đổi `CHUOI` khi còn 13 giai đoạn là đổi hai lần.

## 4. ⛔ Chưa biết — ghi ra để ⛔ không ai tưởng đã biết
- Gộp một lần encode có làm `burn` + `che` + `setpts` cùng lô vượt trần
  filtergraph ⛔ không (Viral phải hạ `VC_WARP_MAX_DOAN` 400 → 150 vì đúng chuyện này).
- Ba nhánh song song có vượt cổng `tai_nguyen_suat` trên máy A ⛔ không.
- Khe gộp có thật sự làm phụ đề lệch tiếng ⛔ không, và lệch bao nhiêu ms.
