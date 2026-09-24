# L-ĐO-GIỌNG — đo giới tính của giọng, và chấm 17 giọng `en` bằng số

> Làn `do-giong` của phiên `asv-final`, 23/09/2026. Nhánh `phien/asv-final-do-giong`.
> Mọi con số dưới đây **đo thật** trên máy A, tiếng thật của LTT Voice (`:8120`),
> clip gốc thật của kho giọng chung.

## Kết luận trước

1. **Hai việc chờ tay chủ dự án nay là hai phép đo.** `L_GIONG_EN.md` §5 đề nghị
   *"chủ dự án duyệt điền 16/17 cột `gioi` theo ghi chú xuất xứ"*, và §3 chọn
   Douglas/Clara bằng nhịp đọc + dư đỉnh với lời thú nhận *"chưa có lượt nghe
   bằng tai"*. Cả hai nay có số.
2. **Giới: đo được 21/25, để trống 4 — và hai giọng LỆCH ghi chú xuất xứ.** Model
   ECAPA (MIT, weights MIT) đạt **19/20** trên tập nhãn của engine, và lần sai duy
   nhất tự khai `do_tin` 0,615 trong khi lần đúng thấp nhất là 0,953 — hai đám
   tách rời, nên ngưỡng **0,95** cho 19 đúng · 1 bỏ trống · **0 sai**.
   ⇒ `Robin` là **nữ** (hai mặt, `do_tin` 0,982, 0/15 cửa sổ nghiêng nam) chứ
   không phải *"giọng biến hoá qua hai dải"* như kết luận 01/09; giọng thật sự
   biến hoá là **`Aaron`** (`p_nam` 0,07→0,87 trong cùng một clip) và nó **để
   trống**.
3. **Xếp hạng: Clara giữ, Douglas thay bằng Owen — và tiêu chí cũ hỏng ở gốc.**
   `L_GIONG_EN` xếp theo *"nhịp gần 156 từ/phút"*, nhưng giọng **chậm nhất** kho
   đọc 181,9 từ/phút và trung vị 217,7 — **không giọng nào tới gần cái đích ấy**,
   nên tiêu chí đó chỉ đang xếp theo *ai đọc chậm nhất*. Chấm lại bằng bảy phép
   đo: Owen dẫn với hạng trung bình 2,9 và **hạng tệ nhất chỉ là 5**, trong khi
   Douglas đứng **16/17** ở SQUIM PESQ. Clara là giọng `nu` tốt nhất, giữ nguyên.
4. ⛔ **Không ghi một dòng CSDL nào.** Đề xuất nằm ở `de_xuat_gioi.json`; đường
   ghi là `soat_giong.py dat-gioi` (mục 4.3), chủ dự án bấm.
5. ⚠️ **Việc cho làn khác**: `ngon_ngu.NHIP[EN] = 2,6` từ/giây chưa từng đo trên
   giọng thật; 34 lượt đọc thật cho **3,63** từ/giây (mục 6.1).

## 0. Chạy lại

```
setup\do_gioi_giong.ps1                 # NÂNG QUYỀN — dựng kho tiếng (62 lượt đọc)
python tools\do_gioi_giong.py do-gioi   # chấm giới: 62 tệp sinh + 25 clip gốc
python tools\do_gioi_giong.py cham-en   # ASR+jiwer, SQUIM, Distill-MOS, DNSMOS, ebur128
python tools\do_gioi_giong.py bao-cao   # in ba bảng markdown dưới đây
python -m pytest tests/test_2145 -q     # hợp đồng (nhẹ)
set LTT_TEST_NANG=1 && python -m pytest tests/test_2141 tests/test_2142 -q
```

Kho tiếng ở `C:\lttinf\asvf_dogiong` — **không commit** (tiếng tổng hợp từ giọng
kho chung là dữ liệu sinh trắc, cùng luật với `data/voice_goc/`).

## 1. Model đã chọn, và vì sao không phải một luật F0

### 1.1 Ứng viên và giấy phép — đọc từ nguồn gốc 23/09/2026

| Ứng viên | License mã | License **weights** | Quyết định |
|---|---|---|---|
| **JaesungHuh/voice-gender-classifier** (ECAPA-TDNN + 1 lớp, tinh chỉnh VoxCeleb2) | **MIT** — `LICENSE` repo GitHub, *"Copyright (c) 2024 jaesunghuh"* | **MIT** — `license: mit` ở YAML front-matter model card HF | **SHIP** |
| griko/gender_cls_svm_ecapa_voxceleb | Apache-2.0 | Apache-2.0 (YAML model card) | Sạch, nhưng kéo theo SpeechBrain + Silero VAD lúc chạy ⇒ để dự phòng |
| alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech | Apache-2.0 | Apache-2.0 | Sạch, nhưng 1,2 GB và chỉ đo trên LibriSpeech sạch |
| `audeering/wav2vec2-*-age-gender` | giấy phép nghiên cứu audEERING | **CC BY-NC-SA 4.0** | **DO NOT SHIP** |
| openSMILE | audEERING Research License | cùng — và nó cấm cả **đặc trưng trích bằng nó** trong sản phẩm | **DO NOT SHIP** |
| praat-parselmouth (F0/formant kiểu Praat) | **GPL-3.0** | — | **DO NOT SHIP** (copyleft) |

⭐ Điều đáng nói: *"phân loại giới tính toàn là NC"* là một điều **sai** mà
   audEERING (ứng viên được trích dẫn nhiều nhất) làm cho có vẻ đúng. Có ít nhất
   ba bản MIT/Apache-2.0 xác minh được.

### 1.2 Vì sao không dùng F0 một mình

Kho này đã có sẵn câu trả lời, ở hai chỗ và cùng một giọng:

* `apps/ltt_voice/tables.py` (chú thích cột `gioi`): *"đoán bằng F0 nghe thì hợp
  lý, nhưng chính `toc_do.py` đã ghi lại một ca bộ dò cao độ nhầm quãng tám trên
  một clip giọng nữ (báo 105,6 Hz). Một cột 'giới' sai còn tệ hơn một cột trống,
  vì nó **được tin**."*
* `docs/LTT_VOICE/KHO_GIONG/00_KIEM_KE.md` (05/09): ranh giới F0 tự nhiên ≈ 168 Hz
  cho 23/25 giọng, nhưng `phatgiao_nu` nằm ở 171,4 Hz — **sát ranh 3 Hz**.

⇒ F0 vẫn được ghi (`f0_trung_vi`, torchaudio `detect_pitch_frequency`, BSD-2) để
  **đối chiếu**, không để phán xử. Nó là cột kiểm tra chéo, không phải quan toà.

### 1.3 Cửa sổ trượt — thứ tách được "giọng trầm" khỏi "giọng biến hoá"

Một nhãn cho cả đoạn không phân biệt được hai thứ dẫn tới hai hành động khác nhau:
giọng nam trầm (model chắc 0,99 ở **mọi** cửa sổ) và giọng **diễn** đổi dải giữa
chừng (0,9 bên này ở cửa sổ này, 0,9 bên kia ở cửa sổ khác). Trung bình của cả
hai đều ra *"0,9 một bên"*.

⇒ Bộ đo trả `ti_le_cua_so_nam` (3 s / bước 1,5 s), và **`do_tin` lấy MIN** của
  xác suất trung bình và tỉ lệ cửa sổ đồng ý. Một giọng đổi dải không thể có
  `do_tin` cao, dù xác suất trung bình của nó cao.

## 2. Kho đo

| tập | n | nhãn đến từ đâu | dùng để |
|---|---|---|---|
| 20 preset engine, kịch bản `vi_a` | 20 | `giong_mau_engine.json` — **engine khai**, không phải ta suy | **hiệu chỉnh** |
| SAPI David / Zira (`tests/test_2141`) | 2 | hệ điều hành khai | chốt chiều, chạy lại được mọi lúc |
| 25 clip **gốc** của kho chung | 25 | không có nhãn độc lập | cái nhìn thứ hai |
| 25 giọng kho chung, tiếng **đã sinh** | 33 lượt | không có nhãn độc lập | **đề xuất** |

Kịch bản ghim trong mã (`tools/do_gioi_giong.py::KICH_BAN`) — cố ý không có
chữ số, viết tắt hay ngoặc, vì `text_pipeline.chuan_hoa` đọc tràn chúng và một
kịch bản mà hai giọng đọc ra hai độ dài khác nhau thì cột "từ/phút" hết nghĩa.

⚠️ **Không so trực tiếp được với bảng của `L_GIONG_EN` §3**: kịch bản của phiên
đó nằm trong scratchpad và không có trong kho, nên nó không lặp lại được. Kịch
bản ở đây nằm trong mã và có phép kiểm (`tests/test_2145`).

## 3. A — hiệu chỉnh trên 20 preset engine

Nhãn giới của 20 preset do **engine** khai (`giong_mau_engine.json`, sinh ra bởi
`tools/sinh_giong_mau_engine.py`) — đây là tập duy nhất trong tay ta có nhãn
không phải do ta suy ra. Mỗi preset đọc cùng một kịch bản `vi_a`.

| preset | nhan | do | do_tin | ti_le_cs_nam | F0 | dung |
|---|---|---|---|---|---|---|
| Adam | nam | nam | 0,996 | 1,00 | 93,0 | OK |
| Kim Thanh | nu | nu | 0,988 | 0,00 | 202,5 | OK |
| Mai Anh | nu | nu | 0,986 | 0,00 | 205,1 | OK |
| Minh Triết | nam | nu | 0,615 | 0,38 | 142,9 | SAI |
| Minh Đức | nam | nam | 0,995 | 1,00 | 149,5 | OK |
| Mỹ Duyên | nu | nu | 0,989 | 0,00 | 225,4 | OK |
| Ngọc Huyền | nu | nu | 0,986 | 0,00 | 200,0 | OK |
| Ngọc Linh | nu | nu | 0,984 | 0,00 | 192,8 | OK |
| Ngọc Trân | nu | nu | 0,976 | 0,00 | 181,8 | OK |
| Phạm Tuyên | nam | nam | 0,953 | 1,00 | 112,7 | OK |
| Quang Sơn | nam | nam | 0,993 | 1,00 | 148,1 | OK |
| Quỳnh Anh | nu | nu | 0,991 | 0,00 | 202,5 | OK |
| Thanh Bình | nam | nam | 0,995 | 1,00 | 149,5 | OK |
| Thái Sơn | nam | nam | 0,973 | 1,00 | 125,0 | OK |
| Thùy Dung | nu | nu | 0,981 | 0,00 | 202,5 | OK |
| Thục Đoan | nu | nu | 0,983 | 0,00 | 222,2 | OK |
| Trúc Ly | nu | nu | 0,995 | 0,00 | 207,8 | OK |
| Xuân Vĩnh | nam | nam | 0,994 | 1,00 | 131,1 | OK |
| Đoan Trang | nu | nu | 0,993 | 0,00 | 213,3 | OK |
| Đức Trí | nam | nam | 0,993 | 1,00 | 108,1 | OK |

**Do chinh xac: 19/20**  ·  do_tin THAP NHAT trong cac lan dung: **0,953**

🔴 **Một lần sai, và nó tự khai ra.** `Minh Triết` (engine khai `nam`) đo ra
`nu` — nhưng với `do_tin` **0,615** và `ti_le_cua_so_nam` 0,38, tức model nói
thẳng rằng nó không chắc. Đặt cạnh nhau:

```
do_tin THẤP NHẤT trong 19 lần ĐÚNG :  0,953
do_tin của lần SAI duy nhất        :  0,615
```

⇒ Hai đám **không chồng nhau**, và khoảng trống giữa chúng rộng 0,34. Một ngưỡng
đặt ở bất cứ đâu trong `(0,615 ; 0,953]` cho **19 đúng · 1 bỏ trống · 0 SAI** trên
tập hiệu chỉnh. Chốt **`do_tin ≥ 0,95`** — sát dưới mốc 0,953 để không bỏ mất một
lần đúng nào, và cao hơn hẳn lần sai duy nhất.

⚠️ Đây là *độ chính xác trên tập hiệu chỉnh*, không phải một lời hứa. 20 điểm
là ít: 19/20 có khoảng tin cậy 95% khoảng **75–99,9%**. Và tập này toàn giọng
**tiếng Việt do engine dựng** — xem mục 7.

⭐ Hai điểm nhãn thứ ba, chạy lại được bất cứ lúc nào không cần máy chủ:
`tests/test_2141` đọc cùng một câu bằng SAPI **David** (nam) và **Zira** (nữ)
rồi chốt cả nhãn lẫn `do_tin > 0,90`. Hai giọng ấy nằm trong Windows, nên phép
kiểm không phụ thuộc kho giọng nào cả.

## 4. B — đề xuất `gioi` cho 25 giọng kho chung

Mỗi giọng đo **hai mặt độc lập**: clip **gốc** của người nói thật (thứ đã dùng
để nhân bản) và **tiếng do engine sinh ra** từ giọng nhân bản ấy (thứ khách
thực sự nghe). Hai mặt phải nói cùng một câu.

| giong | lan | khai (xuat xu) | do (tieng sinh) | do_tin | do (clip goc) | do_tin goc | F0 sinh | khop |
|---|---|---|---|---|---|---|---|---|
| Aaron — nam, phiêu lưu | en | nam | nu | 0,865 | nu | 0,601 | 160,0 | LECH |
| Adrian — nam, thuyết minh | en | nam | nam | 0,995 | nam | 0,996 | 89,9 | OK |
| Clara — nữ, thuyết minh | en | nu | nu | 0,996 | nu | 0,998 | 213,3 | OK |
| Douglas — nam, thuyết minh | en | nam | nam | 0,996 | nam | 0,997 | 98,8 | OK |
| Ethan — nam, giảng bài | en | nam | nam | 0,993 | nam | 0,995 | 134,5 | OK |
| Ivy — nữ, thuyết minh | en | nu | nu | 0,991 | nu | 0,997 | 250,0 | OK |
| Julian — nam, thuyết minh | en | nam | nam | 0,991 | nam | 0,995 | 148,1 | OK |
| Lulu — nữ, hoạt hình | en | nu | nu | 0,996 | nu | 0,997 | 197,5 | OK |
| Marcus — nam, thuyết minh | en | nam | nam | 0,794 | nam | 0,908 | 99,4 | OK |
| Miles — nam, mạng xã hội | en | nam | nam | 0,992 | nam | 0,990 | 92,5 | OK |
| Nathan — nam, hội thoại | en | nam | nam | 0,998 | nam | 0,997 | 114,3 | OK |
| Nova — nữ, hoạt hình | en | nu | nu | 0,997 | nu | 0,998 | 210,5 | OK |
| Owen — nam, kể chuyện | en | nam | nam | 0,996 | nam | 0,995 | 134,5 | OK |
| Peter — nam, hội thoại | en | nam | nam | 0,967 | nam | 0,996 | 108,8 | OK |
| Robin — giải trí, biến hoá giọng | en | nam | nu | 0,982 | nu | 0,982 | 161,6 | LECH |
| Simon — nam, trang nghiêm | en | nam | nam | 0,993 | nam | 0,996 | 105,3 | OK |
| Victor — nam, kể chuyện | en | nam | nam | 0,994 | nam | 0,997 | 100,6 | OK |
| An Nhiên — nữ, kể chuyện thiền | vi | nu | nu | 0,993 | nu | 0,992 | 166,7 | OK |
| Bảo Lâm — nam, kể chuyện | vi | nam | nam | 0,987 | nam | 0,625 | 98,2 | OK |
| Diễm Chi — nữ, kể chuyện ngôn tình | vi | nu | nu | 0,992 | nu | 0,987 | 195,1 | OK |
| Duy Khang — nam, tự nhiên | vi | nam | nam | 0,992 | nam | 0,996 | 149,5 | OK |
| Gia Huy — nam, bản tin kinh tế | vi | nam | nam | 0,994 | nam | 0,997 | 120,3 | OK |
| Hạ Vy — nữ, tự nhiên | vi | nu | nu | 0,993 | nu | 0,993 | 177,8 | OK |
| Thanh Nhã — nữ, tự nhiên | vi | nu | nu | 0,980 | nu | 0,884 | 186,0 | OK |
| Trọng Nghĩa — nam, kể chuyện lịch sử | vi | nam | nam | 0,987 | nam | 0,991 | 103,2 | OK |

### 4.1 Đề xuất chốt — 21 ghi, 4 để trống

Luật áp: **hai mặt cùng nhãn** VÀ **`do_tin` của cả hai ≥ 0,95** (ngưỡng từ mục 3).

| giọng | vì sao **ĐỂ TRỐNG** |
|---|---|
| Aaron — nam, phiêu lưu | `do_tin` 0,601 (clip gốc) — và hai mặt đều nói `nu`, ngược ghi chú |
| Bảo Lâm — nam, kể chuyện | `do_tin` 0,625 (clip gốc); tiếng sinh thì 0,987 `nam` |
| Marcus — nam, thuyết minh | `do_tin` 0,794 (tiếng sinh) |
| Thanh Nhã — nữ, tự nhiên | `do_tin` 0,884 (clip gốc) |

21 giọng còn lại đủ điều kiện. Kết quả **không đổi** khi hạ ngưỡng xuống 0,90 —
bốn ca bỏ trống đều dưới 0,89, nên đề xuất này không nằm trên lưỡi dao ngưỡng.

### 4.2 🔴 HAI giọng lệch ghi chú xuất xứ — và chỉ MỘT được ghi

**① `Robin` (`khanh_male_entertainment`) — ghi chú khai `male`, đo ra `nu`.**

Hai mặt độc lập cùng nói `nu`, cùng `do_tin` **0,982**, và **0/15 cửa sổ** nghiêng
về `nam`. Soi từng cửa sổ 3 giây của clip gốc:

```
p_nam :  0,029  0,016  0,014  0,021  0,030  0,023  0,015  0,014
         0,016  0,014  0,009  0,011  0,017  0,019  0,027
F0 Hz :   205    216    210    267    229    170    216    216
          200    188    198    210    198    168    162
```

⛔ Điều này **bác bỏ** cách đọc của 01/09 (`tools/doi_ten_giong_chung.py`), vốn
kết luận *"giọng diễn, biến hoá qua cả hai dải"* từ việc 24,1% số khung nằm dưới
170 Hz. Phép đo hôm nay nói khác: giọng này **không** đi qua hai dải — nó nữ ở
**mọi** cửa sổ, và 24,1% khung dưới 170 Hz chỉ là phần thấp bình thường của một
giọng nữ. Cái tên `entertainment` gợi ra một câu chuyện hợp lý, và câu chuyện ấy
được tin vì nó hợp lý.

**② `Aaron` (`harry_male_adventure`) — ghi chú khai `male`, đo ra `nu` nhưng KHÔNG chắc.**

Đây mới đúng là giọng *"biến hoá qua hai dải"* mà 01/09 đi tìm — chỉ là nó tìm
nhầm giọng:

```
p_nam :  0,128  0,433  0,354  0,114  0,204  0,537  0,447  0,326
         0,210  0,521  0,871  0,860  0,709  0,074  0,201
F0 Hz :   162    130    148    174    174    140    178    170
          147    160    182    151    143    165    158
```

`p_nam` chạy từ 0,07 đến 0,87 **trong cùng một clip**. ⇒ `ti_le_cua_so_nam` 0,33,
`do_tin` 0,601 ⇒ **ĐỂ TRỐNG**. Và đó là hành vi đúng: cột này không có ô cho
*"ở giữa"*, nên ô trống là câu trả lời trung thực duy nhất.

⭐ Chính vì `Aaron` mà `do_tin` phải lấy **MIN(xác suất trung bình, tỉ lệ cửa sổ
đồng ý)**: xác suất trung bình của cả clip là 0,865 về phía `nu` — đủ cao để lọt
mọi ngưỡng hợp lý. Chỉ tỉ lệ cửa sổ mới nói ra rằng một phần ba clip nghiêng về
phía kia.

### 4.3 Ghi đề xuất vào CSDL — lệnh đã có, chủ dự án bấm

⛔ Làn này **không ghi một dòng CSDL nào**. Đường ghi:

```
python tools\soat_giong.py dat-gioi ^
    --tu-do-luong C:\lttinf\asvf_dogiong\de_xuat_gioi.json ^
    --nguong 0.95 ^
    --ly-do "do bang ECAPA gender (MIT), L_DO_GIONG.md muc 3-4, 23/09/2026"
```

Không có `--that` thì lệnh **chỉ in kế hoạch**. Căn cứ được ghi vào
`VoiceProfile.ghi_chu` (`gioi_nguon` / `gioi_can_cu` / `gioi_nguoi`), nên sáu
tháng sau vẫn tra được con số này đến từ đâu. `tests/test_2143` chốt phần quyết
định (6 phép, không mở CSDL nào).

⭐ Hệ quả: `rang_giong._rang_kho_chung` có **21 ứng viên** thay vì 0 ⇒ `en` +
`AUTO_MATCH` thôi trả `CHUA_RANG`. F-03 đóng được về phía dữ liệu.

## 5. Chấm 17 giọng `en` — bộ đo, và vì sao MOS không phải một cột mới

### 5.1 Năm cột, ba loại

| cột | đến từ đâu | loại |
|---|---|---|
| WER / CER | `do_luong/giong.py` — faster-whisper `large-v3` ghim + jiwer 4.0.0 | **đã ship** |
| STOI · PESQ · SI-SDR (+ thấp nhất cửa sổ) | `do_luong/squim.py` — SQUIM_OBJECTIVE, CC BY 4.0 | **đã ship** |
| Distill-MOS (1–5) | `microsoft/Distill-MOS` 0.9.1 — **MIT cả mã lẫn weights** | **mới** |
| DNSMOS P.835 SIG/BAK/OVRL | `voice_sidecar/dnsmos.py` — đã có trong kho từ 31/08, CC BY 4.0 | **đã có, nay hợp lệ** |
| từ/phút · LUFS-I · LRA · true peak · F0 | ffmpeg `ebur128` + torchaudio | **Loại A** |

### 5.2 UTMOS / DNSMOS — điều đã đổi so với 22/09

Brief hỏi thẳng: *"kiểm lại giấy phép weights từ nguồn gốc, và nói cái gì đã đổi."*
Hai thứ đổi, và **một trong hai lật hẳn một kết luận cũ**:

* 🔴 **DNSMOS: DO-NOT-SHIP → SHIP.** Lý do cũ (*"không có tuyên bố giấy phép cho
  tệp `.onnx`"*) **sai**. `microsoft/DNS-Challenge` tách đôi giấy phép —
  `LICENSE-CODE` (MIT) cho *code*, `LICENSE` gốc (**CC BY 4.0**) cho *"the
  Microsoft documentation and **other content** in this repository"*. Tệp
  `.onnx` là *other content*.
  ⭐ Và bản khai đã **tự mâu thuẫn** trước khi bị bắt: nó chấp nhận weights của
  `SQUIM_OBJECTIVE` là CC BY 4.0 **vì chúng đến từ chính repo ấy**. Kho này
  cũng đã có câu trả lời đúng từ 31/08, trong docstring `voice_sidecar/dnsmos.py`.
  Chi tiết: `THIRD_PARTY_METRICS.md` §2b.
* ⚠️ **UTMOS: lý do loại thay đổi, kết luận giữ nguyên.** Lý do cũ (*"weights
  không khai giấy phép"*) cũng sai — UTMOSv2 khai `license: mit` trên HF, và
  UTMOS22 đã đổi AFL → MIT. Nhưng lý do **đúng** thì mạnh hơn: `docs/datasets.md`
  của chính UTMOSv2 khai dữ liệu huấn luyện **SOMOS là CC BY-NC-SA 4.0** (và
  Blizzard không khai gì). Một nhãn MIT dán lên bản dẫn xuất không gỡ được điều
  khoản NonCommercial của thượng nguồn. ⇒ vẫn **DO NOT SHIP**.
* ⭐ **Thứ mới tìm được: `microsoft/Distill-MOS`** — repo MIT, weights nằm
  **ngay trong cây MIT ấy** (`distillmos/weights/distill_mos_v7.pt`), model card
  ghi `| License | MIT |` kèm câu *"Nothing contained in this Model Card should
  be interpreted as or deemed a restriction or modification to the license the
  model is released under."* Đây là bản chấm MOS thương mại sạch mà bản kiểm kê
  22/09 bỏ sót.
  ⚠️ **Nhưng nó không phải UTMOS thay thế 1:1**: model card khai nó huấn luyện
  cho **tiếng Anh** và cho cảnh **tăng cường / suy hao tín hiệu**, không phải
  cho "giọng đọc nào nghe hay hơn". Nên nó vào bảng như **một cột có đối chứng**,
  không phải như một quan toà — và nó chỉ chạy **ngoài đường chạy của khách**.

### 5.3 Đối chứng — thang đo lộ ra trên chính kho này

Không có đối chứng thì một bảng điểm chỉ là một **thứ tự**: người đọc không biết
chênh 0,15 điểm là nhiều hay ít. Nên cùng lượt chấm còn ba bản **biến dạng** dựng
từ một đoạn thật bằng ffmpeg: nhiễu trắng, méo/clip (+6 dB rồi limiter), và băng
thông hẹp (300–3400 Hz, kiểu điện thoại).

### 5.4 Bảng — 17 giọng `en`, hai kịch bản mỗi giọng

Cột `gioi (do)` lấy từ mục 4; số trong ngoặc là hạng **trong giới ấy**, vì
`rang_giong._rang_kho_chung` lọc theo giới trước rồi mới xét `UU_TIEN_KHO_CHUNG`.

| # | giong | gioi (do) | WER | PESQ | PESQ min cs | SI-SDR | Distill-MOS | DNSMOS OVRL | SIG | tu/phut | LUFS-I | TP dBFS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Miles — nam, mạng xã hội | nam (1) | 0,000 | 3,268 | 2,377 | 22,23 | **4,78** | 3,50 | 3,70 | 200,4 | -20,9 | -3,6 |
| 2 | Douglas — nam, thuyết minh | nam (2) | 0,000 | 3,179 | 2,490 | 21,73 | **4,72** | 3,46 | 3,67 | 187,9 | -20,1 | -3,3 |
| 3 | Marcus — nam, thuyết minh | nam (3) | 0,000 | 3,249 | 2,229 | 17,16 | **4,70** | 3,43 | 3,64 | 184,1 | -21,2 | -1,2 |
| 4 | Simon — nam, trang nghiêm | nam (4) | 0,000 | 3,305 | 2,752 | 23,30 | **4,70** | 3,55 | 3,74 | 226,5 | -21,1 | -1,0 |
| 5 | Owen — nam, kể chuyện | nam (5) | 0,000 | 3,678 | 3,535 | 23,18 | **4,68** | 3,49 | 3,73 | 205,4 | -20,0 | -2,8 |
| 6 | Peter — nam, hội thoại | nam (6) | 0,000 | 3,328 | 2,476 | 22,04 | **4,67** | 3,41 | 3,62 | 196,0 | -19,6 | -2,1 |
| 7 | Robin — giải trí, biến hoá giọng | nu (1) | 0,000 | 3,300 | 2,433 | 22,30 | **4,67** | 3,35 | 3,58 | 228,6 | -20,2 | -4,0 |
| 8 | Ethan — nam, giảng bài | nam (7) | 0,000 | 3,740 | 3,280 | 21,82 | **4,65** | 3,28 | 3,53 | 233,7 | -19,9 | -1,1 |
| 9 | Ivy — nữ, thuyết minh | nu (2) | 0,000 | 3,558 | 3,097 | 23,27 | **4,64** | 3,16 | 3,43 | 234,0 | -19,6 | -2,5 |
| 10 | Lulu — nữ, hoạt hình | nu (3) | 0,000 | 3,584 | 2,792 | 21,48 | **4,64** | 3,26 | 3,51 | 237,8 | -20,6 | -3,5 |
| 11 | Clara — nữ, thuyết minh | nu (4) | 0,006 | 3,583 | 2,909 | 23,30 | **4,62** | 3,16 | 3,41 | 220,8 | -19,9 | -2,5 |
| 12 | Aaron — nam, phiêu lưu | nu (5) | 0,000 | 3,393 | 2,883 | 17,70 | **4,60** | 3,29 | 3,53 | 221,2 | -19,5 | -1,7 |
| 13 | Victor — nam, kể chuyện | nam (8) | 0,000 | 3,200 | 2,431 | 15,07 | **4,60** | 3,41 | 3,64 | 233,3 | -20,0 | -2,5 |
| 14 | Julian — nam, thuyết minh | nam (9) | 0,000 | 3,569 | 2,776 | 24,81 | **4,60** | 3,40 | 3,62 | 203,7 | -19,1 | -1,9 |
| 15 | Nova — nữ, hoạt hình | nu (6) | 0,000 | 3,425 | 2,643 | 22,43 | **4,55** | 3,13 | 3,38 | 256,7 | -20,0 | -2,9 |
| 16 | Nathan — nam, hội thoại | nam (10) | 0,000 | 2,982 | 2,256 | 14,79 | **4,52** | 3,38 | 3,61 | 214,7 | -20,0 | -3,2 |
| 17 | Adrian — nam, thuyết minh | nam (11) | 0,006 | 3,591 | 2,689 | 19,00 | **4,39** | 3,40 | 3,61 | 204,8 | -20,6 | -3,2 |

**Dan dau theo gioi (Distill-MOS):**
- `nam`: Miles 4,78 · Douglas 4,72 · Marcus 4,70
- `nu`: Robin 4,67 · Ivy 4,64 · Lulu 4,64

### Đối chứng — cùng một đoạn tiếng, ba biến dạng

| bản | WER | PESQ | Distill-MOS | DNSMOS OVRL |
|---|---|---|---|---|
| gốc (chưa biến dạng) | 0,000 | 3,149 | 4,75 | 3,48 |
| nhieu10db | 0,000 | 1,166 | 2,61 | 2,42 |
| meo_clip | 0,000 | 3,402 | 4,74 | 3,38 |
| bang_thong_hep | 0,000 | 3,320 | 4,59 | 3,43 |

### 5.5 Đối chứng nói ra thang đo — và nói ra cả chỗ bộ đo MÙ

| bản (cùng một đoạn tiếng) | WER | PESQ | Distill-MOS | DNSMOS OVRL |
|---|---|---|---|---|
| gốc | 0,000 | 3,149 | 4,75 | 3,48 |
| + nhiễu trắng ~10 dB | 0,000 | **1,166** | **2,61** | **2,42** |
| +6 dB rồi limiter (méo/clip) | 0,000 | 3,402 | **4,74** | 3,38 |
| băng thông 300–3400 Hz | 0,000 | 3,320 | 4,59 | 3,43 |

Đọc bảng này **trước** khi đọc bảng xếp hạng:

* **Nhiễu**: Distill-MOS rơi **2,14** điểm. Cả 17 giọng trải trong **0,39** điểm
  (4,39–4,78) ⇒ toàn bộ khoảng cách giữa giọng tốt nhất và giọng kém nhất chỉ
  bằng **18%** của một cú nhiễu 10 dB.
* 🔴 **Méo/clip**: Distill-MOS **4,74** — gần như không nhúc nhích (gốc 4,75), và
  PESQ còn **tăng**. Bộ đo này **mù với méo biên độ**.
* **Băng thông hẹp**: chỉ −0,16.
* **WER = 0 ở cả ba biến dạng**, kể cả bản nhiễu.

⇒ Kết luận về chính bộ đo: nó phát hiện **nhiễu cộng**, và gần như chỉ nhiễu.
Gọi nó là thước đo *"giọng nào nghe hay hơn"* sẽ là đúng thứ mục 5.2 đã cảnh báo.

### 5.6 Bảy phép đo, SÁU người thắng khác nhau

| phép đo | nhất | bét |
|---|---|---|
| Distill-MOS | Miles 4,78 | Adrian 4,39 |
| DNSMOS OVRL | Simon 3,55 | Nova 3,13 |
| DNSMOS SIG | Simon 3,74 | Nova 3,39 |
| SQUIM PESQ | Ethan 3,74 | Nathan 2,98 |
| SQUIM PESQ (cửa sổ tệ nhất) | **Owen 3,54** | Marcus 2,23 |
| SQUIM SI-SDR | Julian 24,8 dB | Nathan 14,8 dB |
| WER | **15/17 hoà ở 0,000** | Clara / Adrian 0,006 |

⇒ **Không có "giọng tốt nhất"** mà bộ đo này bầu ra được. Nên câu hỏi phải đổi
thành câu trả lời được: *giọng nào không có điểm yếu ở phép đo nào?*

| giọng | hạng TB (7 phép) | hạng **tệ nhất** |
|---|---|---|
| **Owen — nam, kể chuyện** | **2,9** | **5** |
| Simon — nam, trang nghiêm | 4,3 | 11 |
| Miles · Ethan · Julian | 6,9 | 15 · 13 · 14 |
| **Douglas — nam, thuyết minh** | 8,3 | **16** |
| **Clara — nữ, thuyết minh** | 8,4 | 16 |
| Nathan — nam, hội thoại | 14,7 | 17 |

⚠️ *Hạng trung bình là một phép gộp hạng (Borda), tức một công thức của TA — nó
ở đây để đọc, không để phán.* Thứ phán là cột **hạng tệ nhất** và cột PESQ cửa
sổ tệ nhất, vì đó là hai thứ nói về một tính chất NGHE ĐƯỢC: khoảnh khắc tệ nhất
trong một câu.

## 6. Douglas và Clara có thật là hai giọng tốt nhất không

**Trả lời: Clara thì có cơ sở. Douglas thì không — và cả hai đều được chọn bằng
một tiêu chí hỏng.**

### 6.1 🔴 Tiêu chí cũ đo khoảng cách tới một cái đích KHÔNG GIỌNG NÀO VỚI TỚI

`L_GIONG_EN` §3 chọn *"nhịp gần mốc ~156 từ/phút mà `ngon_ngu.CUM["en"]` hứa với
LLM"*. Mốc ấy là `ngon_ngu.NHIP[EN] = 2,6` từ/giây. Đo 34 lượt đọc thật (17 giọng
× 2 kịch bản):

```
tu/phut :  min 181,9   p50 217,7   max 265,7
tu/giay :  min 3,03    p50 3,63    max 4,43
NHIP[EN] hien tai        2,60      (= 156 tu/phut)
```

**Giọng CHẬM NHẤT trong kho vẫn nhanh hơn mốc 17%; trung vị nhanh hơn 40%.** Xếp
hạng theo *"gần 156 nhất"* vì thế không xếp theo độ phù hợp — nó xếp theo *giọng
nào đọc chậm nhất*, và trao giải cho giọng chậm nhất trong một kho mà không ai
chậm. (Douglas 187,9 là giọng chậm thứ hai sau Marcus 181,9.)

⚠️ **Việc cho làn khác**: `NHIP[EN] = 2,6` chưa từng được đo trên giọng thật. Nó
lệch về phía **an toàn** (ngân sách chữ ngắn hơn khe ⇒ tiếng ngắn hơn khe, nằm
trong dung sai −35% của `nan_cho_vua`), nên đây **không** phải lỗi đang chảy máu
— nhưng nó đang bỏ phí ~40% ngân sách chữ mỗi câu tiếng Anh. Con số đo được:
**3,63 từ/giây**. ⛔ Làn này không sửa `ngon_ngu.py` (ngoài phạm vi, và nó là
tệp của làn khác).

### 6.2 Clara — giữ

Trong 6 giọng đo ra `nu`, Clara có **hạng trung bình tốt nhất** (8,4 so với Lulu
9,6 · Ivy 10,0 · Robin 10,0 · Nova 12,0) và đứng **thứ nhì** ở cột phán
(PESQ cửa sổ tệ nhất: Ivy 3,10 → Clara 2,91 → Aaron 2,88).

⚠️ Nhưng hai chỗ phải nói ra: Clara **đội sổ** ở DNSMOS OVRL (3,16, chỉ trên Nova
3,13), và đó **khớp** với cảnh báo của kiểm kê 05/09 (`bella_nu`, DNSMOS 3,184 —
"thấp so với kho này"). Hai lần đo cách nhau 18 ngày, hai kho tiếng khác nhau,
cùng một kết luận. Và Ivy cũng 3,16 — nên con số ấy **không** tách được Clara
khỏi ứng viên thay thế duy nhất của cô.

⇒ **Không có bằng chứng để đổi.** Giữ Clara.

### 6.3 Douglas — thay bằng Owen

| | Owen | Douglas |
|---|---|---|
| hạng trung bình (7 phép) | **2,9** | 8,3 |
| hạng tệ nhất | **5** | **16**/17 (SQUIM PESQ) |
| PESQ cửa sổ tệ nhất | **3,535** (nhất kho) | 2,490 (hạng 11) |
| DNSMOS OVRL | 3,49 (hạng 3) | 3,46 (hạng 4) |
| Distill-MOS | 4,68 (hạng 5) | 4,72 (hạng 2) |
| WER | 0,000 | 0,000 |
| từ/phút | 205,4 | 187,9 |

Cách biệt 1,05 PESQ giữa Owen và Douglas ở **cửa sổ tệ nhất** là thật: đối chứng
ở mục 5.5 cho thấy một cú nhiễu 10 dB làm PESQ rơi khoảng 2 điểm, nên 1,05 bằng
**một nửa** một cú nhiễu 10 dB — không phải nhiễu số liệu. Douglas đứng thứ 16/17
ở SQUIM PESQ cả đoạn; không giọng nào khác trong nhóm dẫn đầu có một ô tệ như thế.

⇒ **Đổi thứ tự `UU_TIEN_KHO_CHUNG` thành `(Owen, Clara)`**, ghim bằng
`tests/test_2144`. Đây là một thứ tự phá hoà tất định giữa các ứng viên **đã**
qua bộ lọc giới — đổi nó không mở thêm giọng nào cho ai, không đổi catalog, và
đảo lại được bằng một dòng.

## 7. Hai bộ dò F0 đặt CÙNG một clip ở hai bên ranh giới

Bảng kiểm kê 05/09 (`docs/LTT_VOICE/KHO_GIONG/00_KIEM_KE.md`) dựng một ranh giới
F0 ≈ **168 Hz** và ghi hai ca đáng ngờ. Đo lại hôm nay bằng torchaudio:

| giọng | F0 — kiểm kê 05/09 | F0 — đo 23/09 | ranh 168 Hz | model nói |
|---|---|---|---|---|
| `phatgiao_nu` → An Nhiên | 171,4 Hz (**trên** ranh, "sát ranh ⚠️") | **155,3 Hz** (**dưới** ranh) | **đổi bên** | `nu`, `do_tin` 0,992 |
| `khanh_male_entertainment` → Robin | 220,2 Hz | 202,5 Hz | cùng bên | `nu`, `do_tin` 0,982 |

🔴 Đây chính là lý do một luật F0 **không đủ trung thực** để điền một cột mà hệ
thống sẽ tin: hai bộ dò cùng đo một tệp và đặt nó ở **hai phía** của cái ngưỡng
quyết định. Khác biệt ấy không phải lỗi của bên nào — nó là dải sai số bình
thường của ước lượng cao độ, và nó lớn hơn khoảng cách từ clip đó tới ngưỡng.

## 8. Giới hạn phải nói ra

**Về phép đo giới (mục 3–4)**

1. **Tập hiệu chỉnh 20 điểm, một ngôn ngữ, một nguồn.** 20 preset đều là giọng
   *tiếng Việt do chính engine VieNeu dựng*. 25 giọng kho chung thì 17 là giọng
   *nhân bản từ người nói tiếng Anh*. 19/20 không hứa gì cho miền thứ hai; khoảng
   tin cậy 95% của nó là **75–99,9%**.
2. **Hai mặt đo KHÔNG độc lập hoàn toàn.** Clip gốc và tiếng engine sinh ra đi
   qua cùng một bộ nhân bản, nên "hai mặt cùng nói `nu`" không mạnh bằng hai bộ
   đo khác nhau cùng nói `nu`. Nó loại được lỗi của *bước nhân bản*, không loại
   được lỗi của *model chấm*.
3. **Ghi danh lại, không đọc `VoiceRepr` đã lưu.** Công cụ ghi danh thẳng từ
   clip gốc để khỏi động vào CSDL production. Đã kiểm: ghi danh hai lượt cùng
   một clip cho `ref_b64` **giống hệt** (`ghi_danh_tat_dinh.json`), nên đường này
   tất định — nhưng nó *bằng* biểu diễn đã lưu thì chưa chứng minh, chỉ hợp lý.
4. **"Giới của một giọng" là tính chất của TÍN HIỆU.** Một diễn viên đọc giọng
   khác sẽ được chấm theo thứ họ đọc. Với sản phẩm thì đó lại là câu đúng (khách
   chọn theo thứ họ NGHE), nhưng nó không phải một phát biểu về con người.

**Về bảng xếp hạng (mục 5–6)**

5. **WER bão hoà — nó không xếp hạng được gì.** 15/17 đúng 0,000, và cả ba bản
   đối chứng biến dạng cũng 0,000. Cột ấy chỉ chứng minh *cả 17 giọng đều nghe
   ra chữ*, không hơn.
6. **Distill-MOS mù với méo biên độ** (mục 5.5) và model card của nó khai là
   huấn luyện cho **tiếng Anh**, cảnh **tăng cường/suy hao tín hiệu**. Nó không
   phải máy đo "tự nhiên".
7. **Chưa ai nghe.** ⛔ Bảng này **không thay thế** một lượt nghe bằng tai — nó
   thay một lượt *chọn bằng nhịp đọc*. Bốn giọng dẫn đầu (Owen, Simon, Miles,
   Ethan) đều đáng nghe thử trước khi khoá lâu dài; tệp wav còn ở
   `C:\lttinf\asvf_dogiong\tieng` và sinh lại được bằng mục 0.
8. **n = 2 kịch bản mỗi giọng.** Không có phép kiểm ý nghĩa thống kê nào ở đây,
   và không nên có — với n = 2 thì con số duy nhất đáng tin là con số lớn hơn
   dải đối chứng (mục 5.5), tức PESQ cửa sổ tệ nhất.
9. **Kho tiếng không commit.** Nó là tiếng tổng hợp từ giọng nhân bản của người
   thật; `bang_chung/` của phiên chỉ giữ các tệp JSON số liệu.
