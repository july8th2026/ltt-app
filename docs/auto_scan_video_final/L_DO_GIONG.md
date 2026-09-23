# L-ĐO-GIỌNG — đo giới tính của giọng, và chấm 17 giọng `en` bằng số

> Làn `do-giong` của phiên `asv-final`, 23/09/2026. Nhánh `phien/asv-final-do-giong`.
> Mọi con số dưới đây **đo thật** trên máy A, tiếng thật của LTT Voice (`:8120`),
> clip gốc thật của kho giọng chung.

## Kết luận trước

1. **Hai việc chờ tay chủ dự án nay là hai phép đo.** `L_GIONG_EN.md` §5 đề nghị
   *"chủ dự án duyệt điền 16/17 cột `gioi` theo ghi chú xuất xứ"*, và §3 chọn
   Douglas/Clara bằng nhịp đọc + dư đỉnh với lời thú nhận *"chưa có lượt nghe
   bằng tai"*. Cả hai nay có số.
2. *(điền sau khi đo)*

## 0. Chạy lại

```
setup\do_gioi_giong.ps1                 # NÂNG QUYỀN — dựng kho tiếng (62 lượt đọc)
python tools\do_gioi_giong.py do-gioi   # chấm giới: 62 tệp sinh + 25 clip gốc
python tools\do_gioi_giong.py cham-en   # ASR+jiwer, SQUIM, Distill-MOS, DNSMOS, ebur128
python tools\do_gioi_giong.py bao-cao   # in ba bảng markdown dưới đây
python -m pytest tests/test_2140 -q     # hợp đồng (nhẹ)
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

*(bảng số: mục A/B/C bên dưới, sinh bằng `do_gioi_giong.py bao-cao`)*

## 3. *(A — hiệu chỉnh)*

## 4. *(B — đề xuất `gioi` cho 25 giọng)*

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

## 6. Hai bộ dò F0 đặt CÙNG một clip ở hai bên ranh giới

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

## 7. Giới hạn phải nói ra

*(điền)*
