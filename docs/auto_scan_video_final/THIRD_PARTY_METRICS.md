# THIRD_PARTY_METRICS — bản khai giấy phép bên thứ ba (§18 đề bài)

> Mỗi phụ thuộc/model ĐANG CHẠY trong đường sản phẩm phải có một dòng đầy đủ ở
> bảng §1. Chưa xác minh được giấy phép ⇒ **DO NOT SHIP** (§18), và nó phải nằm
> ở bảng §2 kèm lý do — không được im lặng bỏ qua.
>
> Nghiên cứu gốc + các ứng viên đã loại: `OPEN_SOURCE_METRIC_AUDIT.md`.
> Cột *checksum* là của **tệp weights thật đã tải về máy này**, không phải của
> trang model card; làn nào tải model thì làn đó điền.

## §1. Đang dùng trong runtime

| # | Dùng để | Repo / gói | Phiên bản (tag/commit) | Model / checkpoint | License mã | License weights | Thương mại | Phân phối lại | Nguồn tải | Checksum | Làn |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Đo chất lượng hình sau mã hoá lại (VMAF) | Netflix/vmaf qua `libvmaf` trong ffmpeg | ffmpeg 8.0.1-full (gyan.dev), libvmaf v3.x | `vmaf_v0.6.1` (≤1080p) · `vmaf_4k_v0.6.1` (≥2160p) | BSD-2-Clause-Patent | cùng repo, không có LICENSE riêng cho `model/` | ✅ | ✅ | đi kèm bản dựng ffmpeg đã cài | — (không tải rời) | ky-thuat |
| 2 | Cắt cảnh | Breakthrough/PySceneDetect | 0.6.7.1 (đã cài) | — (thuật toán, không weights) | BSD-3-Clause | — | ✅ | ✅ | PyPI | — | ky-thuat |
| 3 | WER / CER | jitsi/jiwer | 4.0.0 (`setup/qc_models_requirements.txt`) | — | Apache-2.0 | — | ✅ | ✅ | PyPI | — | giong |
| 4 | ASR lượt cuối (đọc lại bản đã lồng tiếng) | faster-whisper (đã là engine của TRANSCRIBE) | `large-v3` | openai/whisper-large-v3 | MIT | MIT | ✅ | ✅ | HF, đã có trong `C:\LTTPlatform\hf-cache` | *(làn giong điền)* | giong |
| 5 | Chất lượng tiếng không cần tham chiếu | pytorch/audio `SQUIM_OBJECTIVE` | torchaudio 2.8.0+cu128 | `squim_objective_dns2020.pth` | BSD-2-Clause | **CC BY 4.0** (ghi công) | ✅ | ✅ kèm ghi công | torch hub → `TORCH_HOME` | *(làn giong điền)* | giong |
| 6 | Đo chất lượng dịch, không cần bản tham chiếu | google-research/metricx | *(làn dich điền)* | `google/metricx-24-hybrid-large-v2p6` | Apache-2.0 | Apache-2.0 | ✅ | ✅ | HF → `HF_HOME` | *(làn dich điền)* | dich |
| 7 | OCR phụ đề đốt vào hình | *(làn ocr chốt: RapidOCR hoặc PaddleOCR)* | *(điền)* | *(điền)* | Apache-2.0 | Apache-2.0 *(xác minh lại)* | ✅ | ✅ | *(điền)* | *(điền)* | ocr |
| 8 | **Giới tính của một giọng, đo từ tiếng** (`apps/asv_gpu/do_luong/gioi.py`) | JaesungHuh/voice-gender-classifier (mã nhúng ở `do_luong/_ecapa_gioi/`, dẫn xuất từ TaoRuijie/ECAPA-TDNN) | GitHub `49bcbecfd929…` · HF rev `db1222153bd6…` | `model.safetensors` (ECAPA-TDNN + 1 lớp tuyến tính, 61.907.512 B) | **MIT** (`LICENSE` của repo GitHub) | **MIT** (`license: mit` ở YAML front-matter model card HF) | ✅ | ✅ kèm LICENSE + NOTICE | HF → `HF_HOME` | `2d8e0be1fdf159d60d5087416e6f6277c5e30ce9e33a61c767a9a409e6c503c5` | do-giong |
| 9 | Chấm MOS để **xếp hạng giọng** (ngoài đường chạy của khách — `tools/do_gioi_giong.py`) | microsoft/Distill-MOS (+ `xls-r-sqa` 0.1.0, lcn-kul) | `distillmos` 0.9.1 (PyPI) | `distillmos/weights/distill_mos_v7.pt` (16.907.522 B) | **MIT** (`LICENSE`: "Copyright (c) Microsoft Corporation") | **MIT** — weights nằm NGAY TRONG cây MIT, model card ghi `\| License \| MIT \|` | ✅ | ✅ | PyPI (weights đi kèm gói) | `b18b3ac60227267cfb91e5d00ce22cc7b73716fd92f269484da1446e27031a40` | do-giong |
| 10 | DNSMOS P.835 (SIG/BAK/OVRL) — dùng ở LTT Voice và ở bảng xếp hạng giọng | microsoft/DNS-Challenge qua `voice_sidecar/dnsmos.py` (đã có trong kho từ 31/08) | commit `82f1b17e7776a43eee395d0f45bae8abb700ad00` | `sig_bak_ovr.onnx` (1.157.965 B) | **MIT** (`LICENSE-CODE`) | **CC BY 4.0** (`LICENSE` gốc — xem §2b) | ✅ | ✅ kèm ghi công | GitHub → `HF_HOME\dnsmos` | `269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd` | do-giong |

### Nghĩa vụ ghi công phải thực hiện

- **CC BY 4.0 (SQUIM_OBJECTIVE)**: bản ra thương mại phải ghi công tác giả. Chỗ
  ghi: trang *Giới thiệu / Giấy phép* của nền tảng — ⚠️ **chưa làm**, việc còn mở.
- **CC BY 4.0 (DNSMOS P.835)**: cùng trang, cùng nghĩa vụ. Văn bản đề nghị nằm ở
  docstring `voice_sidecar/dnsmos.py` (Reddy, Gopal, Cutler — ICASSP 2022).
- **Apache-2.0 (MetricX, jiwer, PaddleOCR/RapidOCR)**: giữ NOTICE + bản quyền khi
  nhúng mã. Làn `dich` nhúng lớp `MT5ForRegression` ⇒ phải kèm NOTICE.
- **MIT (ECAPA gender, Distill-MOS)**: giữ nguyên văn giấy phép + dòng bản quyền
  khi phân phối lại. Làn `do-giong` nhúng mã ⇒ `do_luong/_ecapa_gioi/LICENSE` +
  `NOTICE` (`tests/test_2140` chốt cả hai tệp còn đó và còn dẫn đúng commit).

## §2. ĐÃ LOẠI — không được đưa vào runtime

| Ứng viên | Lý do loại | Nguồn |
|---|---|---|
| NISQA / NISQA-TTS | weights **CC BY-NC-SA 4.0** (mã MIT nhưng weights NC) | `weights/LICENSE_model_weights` |
| torchaudio `SQUIM_SUBJECTIVE` | weights **CC BY-NC 4.0** (BVCC/DAPS) | docstring `_squim_pipeline.py` |
| UTMOSv2 | repo khai weights `license: mit`, **nhưng** `docs/datasets.md` của chính nó khai dữ liệu huấn luyện SOMOS là **CC BY-NC-SA 4.0** (+ Blizzard không khai gì). Một nhãn MIT trên bản dẫn xuất không gỡ được điều khoản NC của thượng nguồn | `sarulab-speech/UTMOSv2/docs/datasets.md` |
| UTMOS22 / `tarepan/SpeechMOS` | weights ghim cùng checkpoint BVCC/Blizzard, và bản demo kèm `wav2vec_small.pt` của Meta ⇒ **chưa xác minh** được cả chuỗi | Space `sarulab-speech/UTMOS-demo` |
| CometKiwi (`wmt22`, `wmt23-xl/xxl`), XCOMET-XL/XXL | weights **CC BY-NC-SA 4.0** | model card HF |
| EasyOCR | weights **chưa xác minh** giấy phép | Jaided AI model hub |
| LPIPS | backbone ImageNet của torchvision — điều khoản **chưa xác minh** | tài liệu torchvision `models.md` |
| `audeering/wav2vec2-*-age-gender` | weights **CC BY-NC-SA 4.0** (YAML model card) | HF model card |
| openSMILE | "audEERING Research License" — cấm cả **đặc trưng trích bằng nó** trong sản phẩm | `audeering/opensmile/LICENSE` |
| praat-parselmouth | **GPL-3.0** — copyleft, không đưa vào nền tảng đóng | `Parselmouth/LICENSE` |

## §2b. MỘT KẾT LUẬN CỦA BẢN KHAI NÀY ĐÃ BỊ BÁC BỎ — DNSMOS

Bảng §2 trước 23/09/2026 ghi *"DNSMOS P.835 — **không có tuyên bố giấy phép** cho
tệp `.onnx`"*. **Câu đó sai**, và câu trả lời đã nằm sẵn trong chính kho này từ
31/08: docstring `voice_sidecar/dnsmos.py` ghi *"giấy phép **CC-BY-4.0**"* kèm
commit ghim và sha256.

`microsoft/DNS-Challenge` **tách đôi** giấy phép — đọc thẳng từ README mục *Legal
Notices* (23/09/2026):

> *"Microsoft and any contributors grant you a license to the Microsoft
> documentation and other content in this repository under the Creative Commons
> Attribution 4.0 International Public License, see the LICENSE file, and grant
> you a license to any code in the repository under the MIT License, see the
> LICENSE-CODE file."*

Tệp `LICENSE` ở gốc repo mở đầu bằng đúng dòng `Attribution 4.0 International`.
Tệp `.onnx` không phải *code* — nó là *other content*, tức **CC BY 4.0**: dùng
thương mại được, bắt buộc ghi công.

⭐ Và bản khai này đã **tự mâu thuẫn** trước khi bị bắt: dòng §1 #5 chấp nhận
weights của `SQUIM_OBJECTIVE` là CC BY 4.0 *vì chúng đến từ `microsoft/DNS-Challenge`* —
cùng một repo, cùng một tệp `LICENSE`, kết luận ngược nhau ở hai dòng cách nhau
mười lăm dòng. Bài học không phải "đọc kỹ hơn" mà là: **khi một repo đã xuất
hiện hai lần trong bảng, hai dòng ấy phải chỉ về cùng một nguồn**.

⇒ DNSMOS chuyển sang §1 (#10). LTT Voice vốn đã dùng nó, nay dùng **đúng luật**
thay vì dùng trong vùng xám.
