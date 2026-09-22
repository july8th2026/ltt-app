# OPEN SOURCE METRIC AUDIT — Auto Scan Video

> Cổng nghiên cứu (§3 đề bài). Lập 22/09/2026 từ nguồn gốc (LICENSE trong repo,
> model card Hugging Face, docstring nguồn) qua GitHub MCP + web. Cột
> *Decision* là quyết định **trước benchmark**; benchmark của từng làn ghi vào
> tệp làn và cập nhật cột này. Chưa xác minh license ⇒ DO NOT SHIP.

## 1. Kiểm kê bộ đo hiện có (mã gốc `5f936d01`)

| # | Câu hỏi | Hiện thực | Loại | Người đọc | Quyết định |
|---|---|---|---|---|---|
| T1 | tệp ra có luồng hình + tiếng | ffprobe (`qc.py:217`) | A | cổng QC | GIỮ |
| T2 | thời lượng ra vs dự kiến | ffprobe, dung sai 0,5 s (`qc.py:235`) | A | cổng QC | GIỮ |
| T3/T14 | preset giữ hình không mã hoá lại | `-c copy -f md5`, so codec/khung (`qc.py:153,424`) | A | cổng QC | GIỮ |
| T4/T5 | LUFS tích hợp / true peak | `loudnorm` (`qc.py:284`) | A | cổng QC | GIỮ |
| T6 | mỗi đoạn có tệp giọng | tập hợp | A | cổng QC | GIỮ |
| T7/T11 | trôi đoạn / trôi cộng dồn | timestamp, ngưỡng tự đặt | A (đo) | cổng QC | GIỮ đo; ngưỡng ghi nguồn |
| T13 | không phải khung đen | `signalstats` YAVG < 2/255 tự đặt (`qc.py:162`) | **B** | cổng QC | THAY → ffmpeg `blackdetect` + `freezedetect` (tham số chuẩn của ffmpeg) |
| T15/T16 | phụ đề trong khung thời gian / hai luồng dài bằng nhau | timestamp | A | cổng QC | GIỮ |
| C1 | ranh giới cảnh | ffmpeg `select=gt(scene,0.4)`, ngưỡng "CHƯA ĐO" (`canh.py:214`) | **B** (ngưỡng) | hiểu cảnh, bản biên tập | BENCHMARK vs PySceneDetect → thay |
| S1 | đọc khớp kịch bản | Dice tập từ, ngưỡng 0,80 (`sua_chua.khop_van_ban`) — **không nối** | **B** | (không ai) | THAY → ASR lượt cuối + JiWER WER/CER |
| S2 | chất lượng tiếng / tự nhiên | không có | — | — | THÊM (model license sạch) |
| X1 | dịch giữ nghĩa | LLM phán `dat`/`do_tin` (`qc_ai.py:60`) | phán xét ngữ nghĩa | vòng sửa | GIỮ làm lớp ngữ nghĩa + THÊM chỉ số QE số |
| V1 | liên tục hình ở mối cắt | VLM (`qc_ai.py:115`) — **không nối** | phán xét | (không ai) | NỐI vào QC_AI (VLM review) |
| V2 | chất lượng hình sau mã hoá lại | không có | — | — | THÊM VMAF (libvmaf) |
| W1 | vùng watermark | heuristic lưới độ lệch (`tools/do_watermark.py`) — không app nào gọi | **B** | (không ai) | XOÁ (pha 13 đã "để tắt"; OCR vùng chữ thay phần phát hiện chữ) |
| G1 | `DO_TIN_TOI_THIEU = 0.70` lọc phán xét AI | ngưỡng tự đặt | B (ngưỡng) | vòng sửa | GIỮ tạm, ghi là ngưỡng sản phẩm |

## 2. Ứng viên OSS — license đã xác minh

| Need | Candidate | Model/checkpoint | Code license | Weights license | Commercial | Windows | GPU/CPU | Bằng chứng | Decision |
|---|---|---|---|---|---|---|---|---|---|
| Chất lượng hình | Netflix/vmaf v3.2.1 (libvmaf trong ffmpeg 8.0.1 gyan full — đã có trên máy) | `vmaf_v0.6.1` (1080p), `vmaf_4k_v0.6.1`, phone = cờ `phone_model`; `*neg` cho so encoder | BSD-2-Clause-Patent | cùng repo (không có LICENSE riêng cho model/) | Có | Có | CPU | github.com/Netflix/vmaf/blob/master/LICENSE; resource/doc/models_v0.md | **SHIP** — chọn model theo khung (576p/1080p → v0.6.1; ≥ 2160p → 4k); không một ngưỡng chung |
| Cắt cảnh | Breakthrough/PySceneDetect 0.6.7 (đã cài) | — | BSD-3-Clause | — | Có | Có (MSI + pip) | CPU | github.com/Breakthrough/PySceneDetect/blob/main/LICENSE | BENCHMARK (L-B) |
| OCR hardsub | RapidAI/RapidOCR (ONNX) | PP-OCRv5/v6 chuyển ONNX | Apache-2.0 | Apache-2.0 (`python/MODEL_LICENSES.md`, dẫn model card PP-OCR) | Có | Có | CPU/GPU (onnxruntime) | github.com/RapidAI/RapidOCR | **Ứng viên 1** (L-E) |
| OCR hardsub | PaddlePaddle/PaddleOCR 3.x | PP-OCRv5_server_rec (zh), latin (vi) | Apache-2.0 | Apache-2.0 (HF card PP-OCRv5_server_rec) | Có | Có (paddlepaddle-gpu) | GPU/CPU | huggingface.co/PaddlePaddle/PP-OCRv5_server_rec | Ứng viên 2 (nặng hơn: thêm framework Paddle) |
| OCR hardsub | JaidedAI/EasyOCR | — | Apache-2.0 | **CHƯA XÁC MINH** (model hub không ghi license) | ? | Có | GPU/CPU | jaided.ai/easyocr/modelhub | **DO NOT SHIP** |
| WER/CER | jitsi/jiwer | — (không model) | Apache-2.0 | — | Có | Có | CPU | github.com/jitsi/jiwer | **SHIP** (L-C) |
| ASR lượt cuối | faster-whisper `large-v3` (đã dùng ở TRANSCRIBE) | whisper large-v3 | MIT | MIT (openai/whisper) | Có | Có | GPU | model card openai/whisper-large-v3 | **SHIP** — cùng engine sản phẩm, không thêm model |
| Chất lượng tiếng | torchaudio `SQUIM_OBJECTIVE` | `squim_objective_dns2020.pth` (STOI/PESQ/SI-SDR ước lượng, không cần tham chiếu) | BSD-2-Clause | **CC BY 4.0** (docstring `_squim_pipeline.py`) | Có (ghi công) | Có | CPU/GPU | github.com/pytorch/audio/blob/main/src/torchaudio/pipelines/_squim_pipeline.py | **Ứng viên 1** (L-C) — xác minh docstring trong bản torchaudio cài thật |
| Chất lượng tiếng | torchaudio `SQUIM_SUBJECTIVE` | BVCC+DAPS | BSD-2 | **CC BY-NC 4.0** | **Không** | — | — | cùng tệp | **DO NOT SHIP** |
| Chất lượng tiếng | NISQA / NISQA-TTS | nisqa*.tar | MIT | **CC BY-NC-SA 4.0** (`weights/LICENSE_model_weights`) | **Không** | — | — | github.com/gabrielmittag/NISQA | **DO NOT SHIP** |
| Chất lượng tiếng | DNSMOS P.835 (đang dùng OFFLINE ở LTT Voice) | `sig_bak_ovr.onnx` | MIT (code) | **không có tuyên bố riêng** cho .onnx | Chưa rõ | Có | CPU | github.com/microsoft/DNS-Challenge README "Legal Notices" | **DO NOT SHIP** trong runtime; chỉ nghiên cứu nội bộ |
| Chất lượng tiếng | UTMOS22 / UTMOSv2 | — | MIT | không ghi riêng; huấn luyện một phần trên BVCC (mẫu Blizzard cấm phân phối lại) | Mơ hồ | ? | GPU | github.com/sarulab-speech/UTMOSv2 | **DO NOT SHIP** tới khi làm rõ |
| QE dịch (không tham chiếu) | google-research/metricx — MetricX-24-Hybrid ở chế độ QE | `google/metricx-24-hybrid-large-v2p6` (~1,2B, mT5) | Apache-2.0 | Apache-2.0 | Có | ? (transformers) | GPU (bf16 ~2,5 GB) | github.com/google-research/metricx; HF card | **Ứng viên 1** (L-D) |
| QE dịch | Unbabel/COMET `wmt20-comet-qe-da` | XLM-R base | Apache-2.0 | Apache-2.0 (`LICENSE.models.md`) | Có | Có | GPU/CPU | github.com/Unbabel/COMET/blob/master/LICENSE.models.md | Ứng viên 2 (nhẹ, cũ hơn) |
| QE dịch | CometKiwi `wmt22-cometkiwi-da`, `wmt23-cometkiwi-da-xl/xxl`, `XCOMET-XL/XXL` | — | Apache-2.0 | **CC BY-NC-SA 4.0** | **Không** | — | — | HF cards | **DO NOT SHIP** |
| Dịch có tham chiếu | COMET `wmt22-comet-da` | XLM-R large | Apache-2.0 | Apache-2.0 | Có | Có | GPU | HF card | Không dùng ở runtime (sản phẩm không có bản tham chiếu); dùng được cho benchmark nội bộ |
| Khác biệt cảm nhận | LPIPS | alex/vgg/squeeze `v0.1` | BSD-2 | BSD-2 (lớp tuyến tính) + backbone ImageNet của torchvision (điều khoản ImageNet **chưa xác minh**) | Chưa rõ | Có | GPU | github.com/richzhang/PerceptualSimilarity | **DO NOT SHIP** tới khi xác minh backbone; VMAF + SSIM đủ cho câu hỏi hiện có |

## 3. Nguyên tắc chọn (§6 đề bài)

```
SỰ THẬT TẤT ĐỊNH   → công cụ tất định (ffprobe, ffmpeg filter, hình học)
CHẤT LƯỢNG CẢM NHẬN → chỉ số/model đã thành danh (VMAF, SQUIM, MetricX)
PHÁN XÉT NGỮ NGHĨA → LTT LLM/VLM (+ chỉ số số nếu có)
```
