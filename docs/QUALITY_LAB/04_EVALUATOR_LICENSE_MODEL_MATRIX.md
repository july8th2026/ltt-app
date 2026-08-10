# Ma trận giấy phép và cấp model cho Quality Lab

> Cập nhật 2026-08-10. Đây là rào vận hành của Q83, không phải tư vấn pháp lý.
> `enabled=false` có nghĩa worker không được import, tải hoặc chạy evaluator đó.

## Quy tắc bật evaluator

Một evaluator học máy chỉ được bật khi đồng thời có đủ: nguồn chính thức,
license phù hợp hoạt động SaaS thương mại, version cố định, toàn bộ weight được
cấp sẵn ngoài runtime, SHA-256 cho từng file và smoke benchmark trên máy đích.
Thiếu một mục thì kết quả là `UNKNOWN`; không fallback sang một model khác.

## Trạng thái đã kiểm chứng

| Evaluator | License ở upstream | Trạng thái LTT | Model/weight | Kết luận |
|---|---|---|---|---|
| LTT PSNR/local-SSIM/bicubic/artifact proxy | LTT internal | **ENABLED diagnostic** | Không có | Chỉ chẩn đoán, chưa human-calibrated và không release gate |
| LPIPS 0.1.4 | BSD-2-Clause | **CANDIDATE, DISABLED** | Linear weights nằm trong package; AlexNet/VGG/SqueezeNet backbone do torchvision nạp | Chỉ bật sau offline provision và checksum cả hai lớp weight |
| pyIQA/IQA-PyTorch current | PolyForm Noncommercial 1.0.0 | **BLOCKED** | Nhiều metric/weight, thường lấy từ model hub | Không dùng cho dịch vụ SaaS thương mại nếu chưa có license riêng |
| DOVER/DOVER-Mobile current | S-Lab License 1.0 | **BLOCKED** | Checkpoint riêng | Upstream chỉ cho mục đích phi thương mại; dùng thương mại phải liên hệ tác giả |

## Bằng chứng nguồn chính

- LPIPS license: <https://github.com/richzhang/PerceptualSimilarity/blob/master/LICENSE>
- LPIPS package/version và bundled linear weights:
  <https://github.com/richzhang/PerceptualSimilarity/blob/master/setup.py>
- LPIPS dùng pretrained torchvision backbone:
  <https://github.com/richzhang/PerceptualSimilarity/blob/master/lpips/pretrained_networks.py>
- pyIQA license hiện tại:
  <https://github.com/chaofengc/IQA-PyTorch/blob/master/LICENSE>
- DOVER license hiện tại:
  <https://github.com/VQAssessment/DOVER/blob/master/LICENSE>

## Quy trình provision LPIPS dự kiến

1. Chốt package `lpips==0.1.4` và một backbone duy nhất (ưu tiên AlexNet sau
   benchmark tài nguyên/chất lượng).
2. Tải package và weight trong tác vụ operator riêng có mạng; runtime worker
   không được tải mạng.
3. Ghi manifest evaluator `{schema_version, evaluator, package_version, source,
   license, artifacts[]}`; mỗi artifact bắt buộc có `{role, filename,
   source_url, license, bytes, sha256}`. Không ghi đường dẫn máy hay credential
   vào report.
4. Khi khởi động evaluator, kiểm tất cả checksum trước khi import/instantiate;
   thiếu hoặc lệch hash thì fail closed và trả `UNKNOWN` có reason code.
5. Benchmark CPU/GPU, peak VRAM, latency và đối chiếu human A/B; chỉ sau đó mới
   đổi `enabled=true`. Việc bật metric không tự động bật release gate.

## Hệ quả cho roadmap

- H31.3 dùng metric nội bộ + paired baseline để xây contract/dataset trước.
- LPIPS là đường mở duy nhất trong ba ứng viên hiện tại nhưng vẫn chưa được cài.
- No-reference video phải nghiên cứu evaluator khác có license thương mại phù
  hợp hoặc mua license; không thay DOVER bằng proxy rồi gọi đó là chất lượng.
