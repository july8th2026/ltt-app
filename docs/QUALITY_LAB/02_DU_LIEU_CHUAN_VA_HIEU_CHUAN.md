# LTT Quality Lab — dữ liệu chuẩn và hiệu chuẩn

## 1. Cấu trúc một benchmark suite

Mỗi sample có manifest không chứa bí mật:

- ID, nguồn/quyền sử dụng, hash, app, task, language, duration/resolution;
- input + expected contract + reference output/annotation nếu tồn tại;
- slice tags: clean/noisy, face/text/motion, speaker count, dialect, aspect...;
- prompt/config/model seed và degradation recipe;
- known limitations và lý do sample thuộc train-calibration hay blind test.

Tách ba tập: `development` để xây evaluator, `calibration` để chọn threshold,
`blind-regression` chỉ dùng cho release. Không tối ưu model app trực tiếp trên
blind set.

## 2. Kích thước MVP

| Pack | MVP đề xuất | Slice tối thiểu |
|---|---:|---|
| Upscale | 30 ảnh + 12 video ngắn × 5 degradation | mặt, chữ, thiên nhiên, animation, low-light, motion |
| AutoSub | 20 audio/video, 60–90 phút | VI/EN, sạch/ồn, 1/2/3 speaker, overlap, nhạc, shot cuts |
| Seedance | 40 prompt/reference case | T2V/I2V/V2V, người/vật/text, camera/motion/style |
| Image/Thumbnail | 60 prompt case | reference, face, text/logo, aspect/crop, brand |
| Clip ngắn | 15 video dài + highlight truth | podcast, review, nhiều speaker, chuyển cảnh |
| Text/Agent | 50 task + 20 adversarial | schema, grounded facts, multi-step, failure/retry |

Con số này đủ dựng MVP và phát hiện regression lớn, chưa đủ tuyên bố chất lượng
thị trường. Sau mỗi release thêm case từ bug thật đã khử dữ liệu riêng tư.

## 3. Human calibration

- Mỗi case cảm nhận được chấm mù A/B bởi ít nhất 3 người; random trái/phải và
  ẩn model/preset.
- Rubric tách technical, semantic, aesthetic/usefulness; có lựa chọn tie và
  “không đủ thông tin”.
- Đo inter-rater agreement và Spearman/Kendall giữa metric với human ranking.
- Metric tương quan kém hoặc lệch theo slice chỉ để chẩn đoán, không làm gate.
- Threshold theo profile/model/resolution/language; version hóa và lưu CI nếu có.

## 4. Báo cáo release

Một release report bắt buộc có baseline, candidate, delta và confidence theo
slice; danh sách hard FAIL; evidence link; evaluator/dataset/hardware version;
runtime/VRAM/cost. Không cho phép chỉ hiện điểm tổng. Verdict cuối:

- `PASS`: mọi hard gate pass và các dimension calibrated không regress quá mức.
- `WARN`: contract pass nhưng có regression/proxy chưa đủ mạnh.
- `FAIL`: hard gate hoặc regression calibrated vượt tolerance.
- `UNKNOWN`: thiếu reference/model/evidence; không được đổi thành PASS.

