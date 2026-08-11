# Human A/B calibration — giao thức vận hành

## Mục tiêu và ranh giới

Giao thức này biến đánh giá cảm nhận thành evidence có thể kiểm toán. Nó không
tự sinh “phiếu người dùng”, không cho metric tự chấm chính nó và không bật
release gate. `ready_for_threshold_review=true` chỉ có nghĩa dữ liệu đủ để hội
đồng chất lượng xem xét threshold.

## Hợp đồng dữ liệu

Dataset manifest v1 nay giữ thêm:

- `media_kind`: `image` hoặc `video`;
- `split`: `development`, `calibration`, `blind-regression`;
- `slice`, tối đa 12 `tags`;
- SHA-256 reference/degraded nếu artifact đã được materialize;
- license/ownership và consent/retention như contract H31.3a.

Calibration suite tham chiếu `dataset_manifest_sha256`, có version riêng và mỗi
case chỉ chứa candidate/baseline storage key ở backend tin cậy. Assignment gửi
cho rater chỉ có token HMAC trái/phải; không serialize storage key, model,
preset hay vai trò candidate/baseline.

Rater ID đi vào qua biến môi trường và chỉ lưu HMAC-SHA256. Blind secret phải
ở secret store dưới tên `LTT_QUALITYLAB_BLIND_SECRET`, không ghi vào file, log,
command line hay report. Đổi secret tạo calibration version mới; không trộn vote
của hai secret.

## Rubric và lựa chọn

Mỗi case có bốn lựa chọn: trái, phải, hòa, không đủ thông tin. Rubric tùy chọn
chấm 1–5 riêng cho:

1. technical: sharpness, artifact, temporal stability;
2. semantic: giữ đúng nội dung/identity/text;
3. aesthetic: tự nhiên và hữu dụng thực tế.

Một rater chỉ được một vote/case. Mỗi normalized vote có chữ ký HMAC trên case,
rater hash, assignment, preference và rubric; sửa JSON sau khi chấm làm
aggregate từ chối. Mỗi case cần ít nhất ba vote hợp lệ; lựa chọn “không đủ
thông tin” không tính vào ba vote nhưng vẫn được thống kê.

## Điều kiện readiness MVP Upscale

- tối thiểu 30 case ảnh và 12 case video;
- có đủ face, text, nature, animation, low-light, motion;
- có đủ bicubic, blur, noise, compression, mixed;
- mọi case có ít nhất ba rater hợp lệ;
- báo Fleiss kappa và Spearman metric-vs-human; `None` là thiếu bằng chứng,
  không được chuyển thành 0 hoặc PASS;
- output luôn `release_gate_eligible=false` cho tới phase threshold review riêng.

## CLI nội bộ

```powershell
python tools\qualitylab_calibration.py validate --suite <suite.json>

$env:LTT_QUALITYLAB_BLIND_SECRET = '<secret từ secret store>'
$env:LTT_QUALITYLAB_RATER_ID = '<id nội bộ>'
python tools\qualitylab_calibration.py assign --suite <suite.json> --case-id <id>
python tools\qualitylab_calibration.py vote --suite <suite.json> --case-id <id> --selection left

python tools\qualitylab_calibration.py aggregate --suite <suite.json> --votes <normalized-votes.json>
```

Không chép giá trị secret/rater thật vào tài liệu. `assign` trả token artifact;
chỉ backend tin cậy được gọi `resolve_artifact_token()` rồi stream media, và
không được đưa storage key vào HTML/URL/log.

## Việc chưa hoàn thành

- Chưa có 30 ảnh + 12 video đã license/materialize.
- Chưa có ba người thật chấm từng case.
- Chưa có threshold/profile/slice version hay blind-regression holdout.
- Chưa có UI stream artifact qua token; CLI hiện là contract/operator tool.

Vì vậy H31.3d tổng thể vẫn mở và toàn bộ metric cảm nhận tiếp tục `UNKNOWN`.
