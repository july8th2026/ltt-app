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

### Nghĩa vụ ghi công phải thực hiện

- **CC BY 4.0 (SQUIM_OBJECTIVE)**: bản ra thương mại phải ghi công tác giả. Chỗ
  ghi: trang *Giới thiệu / Giấy phép* của nền tảng — ⚠️ **chưa làm**, việc còn mở.
- **Apache-2.0 (MetricX, jiwer, PaddleOCR/RapidOCR)**: giữ NOTICE + bản quyền khi
  nhúng mã. Làn `dich` nhúng lớp `MT5ForRegression` ⇒ phải kèm NOTICE.

## §2. ĐÃ LOẠI — không được đưa vào runtime

| Ứng viên | Lý do loại | Nguồn |
|---|---|---|
| NISQA / NISQA-TTS | weights **CC BY-NC-SA 4.0** (mã MIT nhưng weights NC) | `weights/LICENSE_model_weights` |
| torchaudio `SQUIM_SUBJECTIVE` | weights **CC BY-NC 4.0** (BVCC/DAPS) | docstring `_squim_pipeline.py` |
| DNSMOS P.835 | **không có tuyên bố giấy phép** cho tệp `.onnx` | README "Legal Notices" của microsoft/DNS-Challenge |
| UTMOS22 / UTMOSv2 | weights không khai riêng; dữ liệu huấn luyện BVCC cấm phân phối lại | repo sarulab-speech |
| CometKiwi (`wmt22`, `wmt23-xl/xxl`), XCOMET-XL/XXL | weights **CC BY-NC-SA 4.0** | model card HF |
| EasyOCR | weights **chưa xác minh** giấy phép | Jaided AI model hub |
| LPIPS | backbone ImageNet của torchvision — điều khoản **chưa xác minh** | tài liệu torchvision `models.md` |

⚠️ DNSMOS vẫn được LTT Voice dùng **ngoài runtime** (đánh giá nội bộ, `docs/LTT_VOICE/`).
Việc đó không thuộc bản khai này; bản khai này chỉ nói về đường sản phẩm ASV.
