# UP-FEAT-001 — enhancement engine benchmark gate

## Kết luận 2026-08-03

**DEFER AI Detail, denoise và deblur; không bật control.** Đây không phải đóng
băng roadmap: gate đã được chạy lại bằng ba model cài thật trên ba loại suy giảm
và đã xác định rõ engine spike tiếp theo. Fast/Quality hiện tại tiếp tục vận hành.

Evidence tái lập: `evidence/ai-detail-benchmark.json` (schema 2). File nguồn chỉ
được đọc từ thư mục test người dùng chỉ định; frame/output tạm đã bị dọn.

## Kết quả đo thật

GPU: NVIDIA GeForce RTX 5060 Ti · driver 596.21 · 12 frame từ `video (10).mp4`.
PSNR/SSIM cao hơn là tốt; temporal error thấp hơn là tốt.

| Model | Case | PSNR dB | SSIM | Temporal | FPS |
|---|---|---:|---:|---:|---:|
| general-x4v3 | bicubic | 29,8962 | 0,981690 | 5,3842 | 1,164 |
| general-x4v3 | noise | **30,9587** | **0,986573** | **5,6477** | 0,969 |
| general-x4v3 | blur | **30,1207** | **0,982857** | **5,8798** | 1,091 |
| general-wdn-x4v3 | bicubic | **31,5096** | **0,987164** | **4,7320** | 1,033 |
| general-wdn-x4v3 | noise | 28,7073 | 0,977182 | 9,4589 | **1,153** |
| general-wdn-x4v3 | blur | 29,7551 | 0,980031 | 6,3061 | 1,053 |
| x4plus | bicubic | 30,9552 | 0,986062 | 5,1100 | 0,665 |
| x4plus | noise | 30,2635 | 0,983868 | 5,9689 | 0,663 |
| x4plus | blur | 27,5247 | 0,966449 | 7,6527 | 0,724 |

### Diễn giải không vượt quá bằng chứng

- WDN thắng tập bicubic này nhưng thua mạnh trên noise và không phải temporal;
  một video không đủ để đổi nó thành “AI Detail”. Có thể nghiên cứu mode
  “preserve detail” sau khi có tập nhiều cảnh, nhưng đó là vé khác và tên khác.
- `general-x4v3` tốt nhất trong noise/blur của tập này, song nó vẫn là spatial
  upscaler x4; không cung cấp denoise/deblur độc lập ở độ phân giải gốc.
- Binary NCNN cài thật không có `-dn`. Upstream hỗ trợ denoise-strength qua DNI
  của pipeline Python; model WDN đơn lẻ không tạo thành thanh strength hợp lệ.
- Không model nào dùng thông tin nhiều frame, nên không model nào đạt điều kiện
  AI Detail temporal bất kể PSNR một case có cao hơn.

## Acceptance để được mở

Engine temporal mới phải đồng thời:

1. cải thiện PSNR ít nhất 0,30 dB so với Quality trên tập degraded giữ lại;
2. temporal error không cao hơn Quality quá 5%;
3. không có artifact nghiêm trọng ở cảnh chuyển động, mặt và chữ;
4. chạy trên GPU production trong giới hạn VRAM, runtime không quá 4 lần Quality,
   có cancel/fallback và cost đo được;
5. license cho phép vận hành thương mại, dependency/model được khóa và rollback.

Denoise/deblur độc lập còn phải giữ kích thước/FPS/audio, có strength thật và
thắng tập noise/blur tương ứng; không được dùng model upscale rồi gắn nhãn khác.

## Engine spike tiếp theo

| Ứng viên | Điểm khả thi /100 | Kết luận |
|---|---:|---|
| BasicVSR++ qua MMagic | **82** | Ưu tiên 1: temporal, có checkpoint SR/denoise/deblur, Apache-2.0 |
| RealBasicVSR | 77 | Ưu tiên 2: phù hợp video real-world, Apache-2.0; stack cũ hơn |
| Real-ESRGAN hiện tại | 54 | Giữ Fast/Quality; không đủ cho feature mới |
| ProPainter | 18 | Loại: video inpainting, sai bài toán và license non-commercial |

Preflight máy hiện tại phát hiện Python 3.11 có PyTorch 2.5.1 CUDA 12.1 nhưng
wheel không chứa kiến trúc `sm_120` của RTX 5060 Ti. Python 3.13 chỉ có torch
CPU. Vì vậy spike temporal phải dùng sidecar/venv cô lập với PyTorch CUDA 13.0
hoặc 12.8 hỗ trợ Blackwell, sau đó mới giải quyết compatibility MMCV/MMagic;
không nâng đè môi trường worker đang chạy.

Nguồn chính thức:

- Real-ESRGAN/DNI: https://github.com/xinntao/Real-ESRGAN
- BasicVSR++: https://github.com/ckkelvinchan/BasicVSR_PlusPlus
- RealBasicVSR: https://github.com/ckkelvinchan/RealBasicVSR
- MMagic: https://github.com/open-mmlab/mmagic
- PyTorch Blackwell/CUDA: https://pytorch.org/blog/pytorch-2-12-release-blog/

## Lệnh tái lập

```powershell
python tools\benchmark_upscale_ai_detail.py `
  "G:\My Drive\AI\Tool AI\Video seedacne\video (10).mp4" `
  --samples 12 `
  --output docs\UI_REDESIGN\upscalevideo\evidence\ai-detail-benchmark.json
```

Chỉ chạy khi không có process GPU production. Script lưu hash engine/model để
phân biệt thay đổi binary, không ghi đường dẫn nguồn vào evidence.
