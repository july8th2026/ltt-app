# B14 — Tổng hợp 5 làn, và NẮN LẠI plan B13

**Ngày:** 2026-09-28 · **Nguồn:** `V1_DUONG_ONG.md` · `V2_CHEP_LOI_PHU_DE.md` ·
`V3_DICH.md` · `V4_GIONG_AM.md` · `V5_HINH_VAN_HANH.md` · thang chấm
`00_THANG_CHAM.md`

**Yêu cầu chủ dự án:** *"lấy thông số rồi xử lý plan… tránh mất quá nhiều thời
gian xây dựng những thứ vốn đã có."*

---

## 1. 🔴 BA hạng mục B13 nay RẺ HƠN HẲN — đây là phần trả lời trực tiếp

| B13 | tôi đang định xây | Viral đã có | mới |
|---|---|---|---|
| **B5** cứu 32 giây mất tiếng | nấc lui theo độ phủ + tín hiệu ảo giác **thứ tư** + đổi cả bản chép (hạ chất lượng mốc của **toàn bộ** để cứu 13 %) | `chunk_length=10` — **MỘT tham số** (`phu_de.py:713-722`) | `GIÁ 1` |
| **B2** hai cửa `phu_song` | **cảnh báo** rồi thôi | **ĐO rồi HÀNH ĐỘNG** + ngưỡng **TƯƠNG ĐỐI** + 🔴 **⛔ không cache bản sót** | `GIÁ 1–2` |
| **A4/3d** nắn thời lượng | mượn lặng **phía sau** + tăng tốc | **xén lặng TRONG audio TTS trước khi đo** + mượn **phía TRƯỚC** + bậc thang 3 tầng | `GIÁ 2` |

### 1.1 `chunk_size` — hạng mục 1 của chủ dự án, giá bằng một tham số

`whisperx_runner.py:92` gọi `transcribe(audio, batch_size=8, language=…)` — ⛔
**không truyền `chunk_size`** ⇒ nhận mặc định **30**.

🔑 Khối mất là `64,27..94,26` = **29,99 giây** = **đúng một khối ở `chunk_size=30`**.
Một khối giải mã tệ thì mất **trọn 30 giây**, vì đường batched ⛔ không có nấc lui
theo temperature (đã chứng minh: `temperatures`/`no_speech_threshold`/
`compression_ratio_threshold` mỗi tên xuất hiện **đúng 1 lần** trong `asr.py`, ⛔
không ai đọc).

⭐ Và `chunk_size` thì **ĐƯỢC ĐỌC thật**: `asr.py:204` là tham số của `transcribe`,
`:232` đưa thẳng vào `merge_chunks(vad_segments, chunk_size, …)`.

⇒ Đang đo (L2). ⛔ **Không xây nấc lui, ⛔ không bỏ `initial_prompt`, ⛔ không cần
tín hiệu ảo giác thứ tư** nếu phép đo xanh.

### 1.2 🔴 Ta suýt CACHE một bản chép bị cụt

`localize.py:17826-17865`: phát hiện lỗ hổng GIỮA ⇒ đặt cờ `_asr_cut` ⇒ **⛔ KHÔNG
lưu cache bản sót** — *"kẻo lần sau + MỌI ngôn ngữ đều cụt"*.

⚠️ Ta **⛔ không có vế này**. `giai_doan_chep_loi` cache theo `khoa_chung`/vân tay
⇒ một bản chép mất 32 giây **được cache**, và mọi lượt chạy lại của **mọi** ngôn
ngữ đích dùng lại đúng bản cụt ấy. ⇒ Bản vá `chunk_size` sẽ ⛔ **không ăn** trên
các run đã cache nếu ⛔ không tăng `PHIEN_BAN_MA` — và tệ hơn, các bản cụt đã lưu
vẫn nằm đó.

### 1.3 Ngưỡng khe TƯƠNG ĐỐI thay ngưỡng gõ tay

`localize.py:2603-2636`: khe bất thường = `max(15 s, trung_vị_khe_của_CHÍNH_video × 6)`
— *"mỗi video nhịp thoại khác nhau"*.

⚠️ `NGUONG_LO_HONG_S = 15.0` của ta là **hằng số tuyệt đối hiệu chỉnh trên n = 1**
(trung bình nhân giữa hố 7,4 s và hố 32,5 s của **một** phim). Phép của Viral
**bao** con số ấy (`max(15, …)`) và thêm vế thích nghi. ⇒ Nâng cấp `GIÁ 1`.

---

## 2. 🔴 MỘT đánh đổi sản phẩm phải do chủ dự án quyết

**Bậc thang nắn thời lượng của Viral** (`localize.py:9018-9022`, chốt 28/08):
```
① nen <= DUB_MAX_SPEED = 1,2x
② lam CHAM VIDEO toi 20 %
③ troi (dong bo lai phu de theo giong)
   -> KHONG BAO GIO cat bo cau
```
Cộng: mượn lặng **CẢ HAI** đầu (`DUB_LEAD`/`DUB_TAIL = 0,25 s`, đo **giảm 35 %** số
câu vượt trần) · trần đuổi-nợ **tách riêng** (`DUB_CATCHUP_MAX = 1,4×`, kích khi
trễ > 0,3 s) · `DUB_TRIM_SIL` xén lặng **trong audio TTS trước khi đo**.

🔴 **Ta thì CẮT HẲN CÂU**: `thoi_gian.TRAN_TROI_SO_DOAN = 3` — và chú thích của
chính nó khai *"⛔ không dự án tham chiếu nào có trần này"*. Nay ta biết vì sao:
**họ ⛔ không cắt câu, họ làm chậm VIDEO.**

⇒ Hai câu hỏi cho chủ dự án, ⛔ tôi không tự quyết:
1. Có cho phép **làm chậm video tới 20 %** để ⛔ không phải cắt câu? (⚠️ xung đột
   `D-ASV-03`: bản lồng tiếng ⛔ không bao giờ dài hơn video nguồn.)
2. Nếu ⛔ không, giữ `TRAN_TROI_SO_DOAN = 3` (cắt câu) hay chấp nhận trôi nhiều hơn?

⭐ Nhưng **ba** vế còn lại ⛔ không cần hỏi: xén lặng trong audio TTS, mượn lặng
phía trước, tách trần đuổi-nợ — cả ba **giảm** áp lực tăng tốc mà ⛔ không đụng
đánh đổi nào. `LẤY NGAY`.

---

## 3. ⭐ Bảy hạng mục MỚI đáng thêm (⛔ chưa có trong B13)

| # | hạng mục | neo Viral | `GT`/`GIÁ` |
|---|---|---|---|
| **N1** | **Sổ kế toán câu XUYÊN chặng** — số câu còn lại sau **từng** chặng, in `◄── RƠI N CÂU Ở ĐÂY` | `localize.py:114-172` | 5 / 2 |
| **N2** | Lọc dải chữ bằng **hình học nét** (SWT) + lệch tâm ngang | `dai_sub_rapid.py:97-148` | 4 / 3 |
| **N3** | Glossary sửa lỗi **ĐỒNG ÂM ASR** trước khi dịch (đo 8/8) | `ai_dich.py:1290-1336` | 4 +đo / 2 |
| **N4** | Trần phát hiện **dịch PHÌNH/bịa** (>10× đơn vị nguồn **VÀ** >90/60 ký tự) | `ai_dich.py:1062-1077` | 4 / 2 |
| **N5** | Trần độ dài **theo MẬT ĐỘ NGUỒN** (trước TTS, khác pha `nan_cho_vua`) | `dich_gemini_web.py:155-184` | 4 +đo / 2 |
| **N6** | Phát hiện **GỘP CÂU** qua độ dài bất thường trong lô (27.139 cue / 90 video) | `dich_gemini_web.py:1366-1416` | 4 +đo / 2 |
| **N7** | Chuẩn hoá tiếng Việt **trước TTS**: số La Mã, số điện thoại | `tts_chuan_hoa.py:86-100,151-152` | 3 / 1 |

⭐ **N1 là hàng giá trị nhất của cả bảng.** Hôm nay tôi phải truy **bằng tay** qua
CSDL + artifact để biết `78 → 69` đoạn rơi ở đâu. Dữ liệu ta **đã có** trong
`asv_stage.outputs`; thiếu đúng **một hàm đọc ngang**. ⇒ Nó biến mọi lần chẩn đoán
sau này từ một buổi thành một dòng.

---

## 4. 🔴 MỘT cảnh báo nặng hơn mọi hàng `THIẾU`

`dich_gemini_web.py:1522-1546` — **A/B thật, 36 lô, 3 video**: *số đếm-được trong
lời nhắc gần như ⛔ KHÔNG ghìm được độ dài model viết.*

⚠️ Đó **đúng** kỹ thuật `nan_cho_vua.loi_nhac_nan_lo` của ta đang dùng
(`do_dai_toi_da`), và ta **trả tiền thật** cho mỗi lời gọi. ⇒ Đo lại trên
`ltt_llm` bằng **đúng phương pháp so-cặp của họ** trước khi tin thêm. Nếu nó ⛔
không ghìm được thì bậc thang nắn của ta đang **mua một thứ ⛔ không tồn tại** —
và các vế ở §2 (xén lặng, mượn hai đầu) là đường thay thế **⛔ không tốn LLM**.

---

## 5. Ba chỗ Viral ⛔ KHÔNG có gì cho ta

| | |
|---|---|
| **Tín hiệu "cảnh xấu"** (rung / camera bất ổn) | `xu_ly_chon.py` ⛔ không phải mã chọn cảnh (nó là tick hiệu ứng của khách); mã dò cảnh **chỉ dò ranh giới**. ⇒ **E2 phải TỰ XÂY**, ngưỡng là ngưỡng **ta tự đặt** |
| **Ba lớp chống lẫn id** | vá lỗ của giao diện chat tự do; thiết kế JSON-key của ta tránh từ gốc ⇒ `⛔ KHÔNG LẤY` **có lý lẽ** |
| **Cache** | của họ khoá bằng `basename+size+mtime` một-người-dùng; của ta khoá bằng **checksum nội dung + chủ sở hữu** (chống rò rỉ chéo khách). Ta **chặt hơn** |

⭐ Và một vế **ta thiếu** ở tầng vận hành: `_whisper_worker.py` / `_demucs_worker.py`
chạy trong **`subprocess` riêng** để *"KILL được khi cuDNN TREO GIỮA CHỪNG"* và
*"model unload NGAY khi xong"*. Ta có trần lõi (`chan_loi()`) và thuê GPU
(`gpu_lease`) — ⛔ nhưng **⛔ không có vế "giết được"**. Máy treo **hai lần** 28/09
đúng vì một thư viện trong tiến trình **của chính ta**. `GT 4 / GIÁ 4`.

---

## 6. NẮN PLAN — thứ tự mới

```
P0  B5 chunk_size            1 tham so     <- DANG DO, thay ca mot co che
P0  §1.2 KHONG cache ban sot  GIA 1        <- neu khong, moi ban va bi cache che
P0  N1 so ke toan cau         GIA 2        <- bien chan doan tu mot buoi thanh mot dong
P1  §2 xen lang TRONG TTS + muon khe PHIA TRUOC + tach tran duoi-no   GIA 2
P1  §1.3 nguong khe TUONG DOI GIA 1
P1  N3 N4 N5 N6  bon cua o duong DICH      GIA 2 moi cai
P2  N2 SWT cho dai chu        GIA 3
P2  N7 chuan hoa tieng Viet truoc TTS      GIA 1
P2  §5 tien trinh con GIET DUOC            GIA 4
P3  E2 duoi canh xau — TU XAY, khong muon duoc
P3  §4 do lai "tran trong loi nhac co ghim duoc model khong"
HOI CHU DU AN: §2 — lam cham VIDEO 20 % de KHONG cat cau?
```

### ⛔ Rút khỏi B13
- **nấc lui theo độ phủ** + **tín hiệu ảo giác thứ tư** — `chunk_size` thay thế.
- **bỏ `initial_prompt`** — ⛔ không cần nếu `chunk_size` xanh; giữ được dấu câu.

### ✅ Đã làm hôm nay, đúng nguồn
- **D1/D2** tách đoạn theo **chữ đổi** — mượn nguyên `dai_sub_rapid.py:190-213`.
- **A2/A4** mẫu số `ngan_sach` + bỏ chừa chỗ hẹp — ⭐ và §2 nay cho biết ta còn
  **thiếu nấc 0** (xén lặng trong audio TTS) mà Viral có.

---

## 3c. ✅ CHỐT 28/09 — ⛔ KHÔNG lấy nấc "giảm tốc video"

Chủ dự án chốt: **⛔ không lấy** `Video Assist` của Viral. Giữ bậc thang thuần
tiếng:

```
0  XEN LANG trong audio TTS truoc khi DO      (Viral DUB_TRIM_SIL — ta chua co)
1  TRAN sang PAUSE truoc VA sau               (Viral DUB_LEAD/TAIL = 0,25 s)
2  tang toc trong tran THUONG  1,15
3  tran DUOI-NO 1,25, chi kich khi DA tre
4  TROI (don ve cuoi), sub bam giong           (ta DA CO)
—  ⛔ KHONG BAO GIO cat cau
```

### Vì sao ⛔ không lấy — ba cái giá đo được, và hai cái đầu nặng với TA hơn với họ

**Cơ chế của họ là CỤC BỘ từng đoạn** (`localize.py:9255-9263`), ⛔ không phải cả
video:
```
need_i = dur_i / slot_i
need_i <= VOICE_CAP (1,12)  -> khong cham video doan nay (f_i = 1,0)
need_i >  VOICE_CAP         -> cham video DOAN NAY  f_i = max(1-MAXSLOW, VOICE_CAP/need_i)
```

Bảng đo của họ (21/08, 60 cue thật, giọng thật, LEAD/TAIL 0,25):

| MAXSLOW | 0 | 0,08 | 0,10 | 0,15 | 0,40 |
|---|---|---|---|---|---|
| nén TB | 1,194 | 1,151 | ~1,14 | 1,122 | 1,064 |
| cue >1,3× | 35,0 % | 23,3 % | ~21 % | 18,3 % | 6,7 % |
| **video dài thêm** | +0 % | **+4,7 %** | ~+6 % | **+8,4 %** | +17,1 % |

⚠️ Mức `0,20` họ **đang dùng ⛔ KHÔNG nằm trong bảng** — nó là **nội suy** giữa
0,15 và 0,40; chủ dự án của họ đã được báo rõ và vẫn chọn.

| # | cái giá | vì sao nặng với TA |
|---|---|---|
| 1 | **video DÀI RA ~+10 %** ở `0,20` | vi phạm `D-ASV-03` (*bản lồng tiếng ⛔ không bao giờ dài hơn nguồn*) — **chắc chắn**, ⛔ không phải rủi ro |
| 2 | 🔴 **chi phí RENDER nổ** | nguyên văn họ: *"mỗi câu tràn = 1 đoạn trim+concat… video 1h gần như câu nào cũng tràn ⇒ **hàng nghìn đoạn** ⇒ filtergraph khổng lồ ⇒ concat đơn luồng nghẽn, NVENC đói"*. Đo máy khách: **GPU 16 %, ghép 393/1795 s**. Họ phải hạ `VC_WARP_MAX_DOAN` 400→150. ⚠️ Ta vừa tìm **40 chỗ ffmpeg ⛔ không khai `-filter_threads`**, và máy production đã **treo hai lần** 28/09 — đúng lớp này |
| 3 | ⚠️ **từng phá đồng bộ phụ đề** | phim 2296 s: hình **trôi muộn dần** (+1,3 → +2,4 → +9,2 → +12,1 s rồi bão hoà); **phụ đề Việt hiện TRƯỚC phụ đề gốc ~1,05 s** ở một số câu. Họ **tắt 3 tuần** (30/07 → 21/08) vì thế |

⭐ Và một câu của họ **⛔ không làm đổi quyết định nhưng phải ghi lại**, vì nó sẽ
được viện dẫn: *"đã đo và LOẠI mọi hướng chỉnh PROMPT (36 lô A/B, 6/12 = tung đồng
xu) ⇒ **Video Assist là đòn bẩy DUY NHẤT đo được có tác dụng**."*

⇒ 🔑 Với **họ** câu ấy đúng, vì họ **⛔ không có** bậc thang nấc 0/1 của ta (xén
lặng + mượn pause hai đầu) như một cơ chế riêng biệt, và họ **⛔ không** có ngân
sách "tới lúc đoạn sau bắt đầu" của `thoi_gian.ngan_sach_doan`. ⇒ Hai hệ **⛔ không
cùng tập đòn bẩy**, nên *"đòn bẩy duy nhất"* của họ ⛔ **không** chuyển thành
*"đòn bẩy duy nhất"* của ta.

### ⚠️ Nếu bậc thang thuần tiếng VỠ thì mở lại hai đường, ⛔ không phải một
1. lấy ở **`0,08`** (điểm **đã đo**: +4,7 % độ dài, cue gấp 35 % → 23,3 %) và
   **nới `D-ASV-03`** — cần chủ dự án chốt lại vì đó là bất biến có phép kiểm **ném**;
2. **tự xây bản BÙ TRỪ** — chậm chỗ dồn, **nhanh chỗ dư**, giữ **tổng** ⇒ `D-ASV-03`
   còn nguyên. Viral ⛔ không làm thế (họ cho tổng dài ra). Cái giá: việc **tự xây**,
   và phải đo xem mắt có thấy hình nhanh/chậm không đều ⛔ không.

⇒ L1 đang đo **điểm vỡ** của bậc thang thuần tiếng. Có con số rồi mới bàn tiếp.
