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
| FFmpeg/libvmaf + `vmaf_v0.6.1` | BSD-2-Clause-Patent; FFmpeg build license riêng | **ENABLED diagnostic** | Model đi kèm libvmaf build | Pin model rõ và hash toàn bộ FFmpeg binary trong evaluator snapshot; vẫn UNKNOWN trước calibration |
| pyIQA/IQA-PyTorch current | PolyForm Noncommercial 1.0.0 | **BLOCKED** | Nhiều metric/weight, thường lấy từ model hub | Không dùng cho dịch vụ SaaS thương mại nếu chưa có license riêng |
| DOVER/DOVER-Mobile current | S-Lab License 1.0 | **BLOCKED** | Checkpoint riêng | Upstream chỉ cho mục đích phi thương mại; dùng thương mại phải liên hệ tác giả |
| **UVQ (`google/uvq`)** — no-reference | **Apache-2.0** | **CANDIDATE, DISABLED** | 169 MB checkpoint PyTorch **nằm trong kho** | Ứng viên cho ô NR-video mà mục "Hệ quả cho roadmap" để ngỏ. Đạt điều kiện 1–4; còn thiếu SHA-256 và smoke benchmark — xem dưới |

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
- VMAF license và model guidance:
  <https://github.com/Netflix/vmaf/blob/master/LICENSE>,
  <https://github.com/Netflix/vmaf/blob/master/resource/doc/models_v0.md>

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

## Thẩm định UVQ — 07/09/2026, đo qua GitHub API

Mục "Hệ quả cho roadmap" bên dưới để ngỏ một ô từ 10/08: *"No-reference video
phải nghiên cứu evaluator khác có license thương mại phù hợp hoặc mua license."*
Đây là lượt tra đầu tiên cho ô đó.

### Bốn ứng viên NR-VQA, tra giấy phép thật chứ không đọc badge

| kho | giấy phép | push cuối | kết luận |
|---|---|---|---|
| **`google/uvq`** | **Apache-2.0** | 2026-01-29 | ✅ ứng viên |
| `VQAssessment/FAST-VQA` | NOASSERTION | 2024-08-12 | ⛔ cùng nhóm S-Lab với DOVER |
| `vztu/RAPIQUE` | MIT | 2022-09-18 | ⚠️ không bảo trì 4 năm |
| `utlive/VIDEVAL` | MIT | 2021-04-22 | ⚠️ không bảo trì 5 năm |

### UVQ đối chiếu **sáu điều kiện bật evaluator** ở đầu tệp này

| # | điều kiện | trạng thái |
|---|---|---|
| 1 | nguồn chính thức | ✅ `github.com/google/uvq` (Google) |
| 2 | license hợp SaaS thương mại | ✅ Apache-2.0; **không** có `LICENSE` con trong `models/` hay `uvq_pytorch/checkpoint/` ⇒ phủ bởi `LICENSE` gốc |
| 3 | version cố định | ✅ ghim theo commit SHA |
| 4 | **toàn bộ weight cấp sẵn ngoài runtime** | ✅ checkpoint **nằm trong kho**, không tải mạng lúc chạy |
| 5 | SHA-256 từng file | ⛔ **chưa** — cần tác vụ operator có mạng |
| 6 | smoke benchmark trên máy đích | ⛔ **chưa** — cần một cửa sổ GPU |

⭐ **Điều kiện 4 là chỗ UVQ hơn hẳn hai ứng viên đang cân nhắc.** LPIPS nạp
   backbone qua `torchvision` lúc chạy, và `torchmetrics` cũng vậy — cả hai
   vướng đúng điều kiện này. UVQ thì checkpoint nằm sẵn trong kho.

### Kích thước và phụ thuộc — đo 07/09

```
uvq_pytorch/checkpoint/
  compressionnet_pytorch_statedict.pt    62,76 MB
  distortionnet_pytorch_statedict.pt     55,84 MB
  contentnet_pytorch.pt                  46,73 MB
  contentnet_labels.csv                   3,43 MB
  TONG                                  168,76 MB

requirements.txt: torch==2.8.0  torchvision==0.23.0  tqdm  numpy  pandas
```

⭐ **Không kéo theo TensorFlow.** Kho có cả bản SavedModel (`models/*.pb`) lẫn
   bản PyTorch; bản PyTorch chỉ cần `torch`. Đó là khác biệt lớn về chi phí —
   máy này đã có `torch 2.11.0+cu128`.

⚠️ Nhưng **lệch version là rủi ro thật**: UVQ ghim `torch==2.8.0`, máy chạy
   `2.11.0`. Nạp một `state_dict` qua hai bản torch thường không sao, nhưng
   *"thường không sao"* không phải một phép đo. Đó chính là việc của điều
   kiện 6, và nó phải chạy **trước** khi đổi `enabled`.

### ⛔ Điều KHÔNG được suy ra từ mục này

1. UVQ **chưa** được bật. Nó ở `CANDIDATE, DISABLED`, cùng bậc với LPIPS.
2. Giấy phép sạch **không** thay được calibration. Một evaluator chưa hiệu
   chuẩn vẫn trả `UNKNOWN` — đúng luật ở đầu tệp này.
3. UVQ **không** thay `DOVER` theo nghĩa "cùng điểm số". Nó là một model khác,
   thang khác, phải hiệu chuẩn lại từ đầu. Luật *"không thay DOVER bằng proxy
   rồi gọi đó là chất lượng"* vẫn nguyên hiệu lực và áp cho cả UVQ.

## Hệ quả cho roadmap

- H31.3 dùng metric nội bộ + paired baseline để xây contract/dataset trước.
- LPIPS là đường mở duy nhất trong ba ứng viên hiện tại nhưng vẫn chưa được cài.
- No-reference video phải nghiên cứu evaluator khác có license thương mại phù
  hợp hoặc mua license; không thay DOVER bằng proxy rồi gọi đó là chất lượng.
- VMAF là full-reference và có thể phản ánh enhancement gain; không dùng một
  mình để quyết định Upscale tốt/xấu, không thay temporal/artifact/human A/B.
