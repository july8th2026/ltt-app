# Upscale GPU evidence — checkpoint 2026-08-10

## Phạm vi

Checkpoint này chứng minh bộ đo peak VRAM chạy được trên GPU đích. Nó **không**
là calibration chất lượng hình ảnh, không phải production telemetry và không
đủ dữ liệu để đặt ngưỡng release.

- Media: hai video trong folder test mà chủ sản phẩm đã chỉ định; file nguồn
  chỉ đọc, không copy vào repo. SHA-256 đầu vào được lưu trong raw evidence.
- Input benchmark: cắt 1 giây, chuẩn hóa 480p, 24 frame, giữ audio/FPS.
- GPU: NVIDIA GeForce RTX 5060 Ti, 16.311 MiB, driver 596.21. UUID chỉ lưu dưới
  dạng SHA-256, không lưu định danh thô.
- Sampler: `nvidia-smi` mỗi 200 ms, chọn card bằng UUID; đo `memory.used` toàn
  card rồi trừ baseline. Chỉ qualified khi GPU ban đầu <=512 MiB, <=5% và không
  có lỗi sampling. Đây không phải số per-process.
- Raw evidence nằm trong `tmp/qualitylab-gpu-evidence-v2/` và không được commit;
  bảng dưới chỉ giữ aggregate, hash và contract cần cho audit.

## Kết quả thực tế

Tất cả bốn ca giải mã/encode đúng kích thước, FPS, audio và artifact không rỗng.
Baseline GPU 1 là 4 MiB/0%; sampling error bằng 0 trong cả bốn ca.

| Ca | Model quan sát | Output | Thời gian / 24 frame | Throughput | Peak | Delta từ baseline | Mẫu |
|---|---|---:|---:|---:|---:|---:|---:|
| Fast 1080p | realesr-general-x4v3, tile 384 | 1882×1080 | 4,04 s | 5,94 fps | 852 MiB | 848 MiB | 17 |
| Fast 1440p | realesr-general-x4v3, tile 384 | 2562×1440 | 4,34 s | 5,53 fps | 852 MiB | 848 MiB | 18 |
| Quality 1080p | realesrgan-x4plus, tile 512 | 1882×1080 | 34,12 s | 0,70 fps | 11.180 MiB | 11.176 MiB | 130 |
| Quality 1440p | realesrgan-x4plus, tile 512 | 2562×1440 | 35,20 s | 0,68 fps | 11.181 MiB | 11.177 MiB | 134 |

Hai source artifact có hash bắt đầu bằng `a986c64eacd7` và `6bb793b0fb9d`.
Không dùng tên file trong evidence bền vững.

## Runtime fingerprint

| Artifact | SHA-256 |
|---|---|
| `realesrgan-ncnn-vulkan.exe` | `07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c` |
| `realesr-general-x4v3.bin` | `bfdfaebf0b26be9442faa30b8cec617fe04a808ae2aa3616ece85b92d81ae0ce` |
| `realesr-general-x4v3.param` | `33950f36822fd37786502db9bd6a3638f677c13b23814c8e5a6e8fd9bcea2163` |
| `realesrgan-x4plus.bin` | `713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf` |
| `realesrgan-x4plus.param` | `35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86` |

## Finding bắt buộc xử lý

### GPU-001 — manifest VRAM thấp hơn peak Quality

`apps/upscalevideo/manifest.py` hiện khai 4.000 MB cho
`upscalevideo.render`, trong khi hai ca Quality đo delta khoảng 11.177 MiB.
Scheduler có thể cấp một card còn hơn 4,5 GB nhưng không đủ cho Quality, dẫn đến
OOM hoặc lỗi engine. Đây là stop-line runtime/capacity, không được che bằng cách
đổi verdict Quality Lab.

Không đặt ngay một con số production từ hai clip. Phase runtime riêng phải:

1. benchmark thêm duration/resolution/content slice và cả hai GPU;
2. chọn worst-case + safety margin;
3. quyết định static worst-case hay mở rộng contract VRAM theo preset;
4. test scheduler từ chối GPU thiếu VRAM rồi mới đổi manifest/contract;
5. canary production và có rollback.

### GPU-002 — Quality chậm hơn Fast khoảng tám lần

Quality đạt 0,68–0,70 fps, Fast đạt 5,53–5,94 fps trên cùng input 480p. Giá,
ETA, timeout và SLO không được dùng chung baseline giữa hai preset.

## Giới hạn và bước tiếp theo

- Chỉ hai clip, mỗi ca một giây; chưa có confidence interval hay content slice.
- Whole-device delta chỉ đúng khi card benchmark độc quyền và rảnh; production
  phải ghi peak trong chính lifecycle job hoặc có collector gắn GPU lease.
- Output target 1080p/1440p chưa làm workload neural khác nhiều vì engine vẫn
  upscale x4 rồi encode/downscale; cần benchmark thêm input/duration.
- H31.3c2b vẫn mở. H31.3d cần tối thiểu 30 ảnh + 12 video và human A/B mù trước
  khi đặt threshold chất lượng hay release gate.
