# H32.1 — Findings: AutoSub Video

## Đã đóng trong H32

### H32-AS-001 — Tên sản phẩm không nhất quán — CLOSED

Manifest/page/nav dùng “Khắc phụ đề video”, trong Studio dùng “AUTO SUB VIDEO”.
Đã đổi toàn bộ bề mặt do manifest quản lý thành **AutoSub Video** và browser
verification pass.

## P1

### H32-AS-002 — Chưa có evidence A-Z cho AI transcript/diarize/translate

Fixture trung thực báo WhisperX, Pyannote và Gemini “Chưa cấu hình”. Không có lỗi
UI, nhưng không thể gọi ba capability là production-ready. Cần staging có model/key,
golden corpus VI/EN, WER/timing/DER và test quota/failure/refund.

### H32-AS-003 — Carry-forward security/economics chưa được re-gate

Audit 09-08 nêu upload staging/orphan/purpose token và canonical workload quote.
H32 chứng minh happy path, không chứng minh các đường forged/corrupt/oversize/
abandon đã đóng. Giữ gate G2/G3 có điều kiện cho tới khi negative corpus pass.

## P2

### H32-AS-004 — Locale EN lẫn tiếng Việt

`/en/autosubvideo` có shell EN nhưng phần Studio, status và CTA vẫn VI. Đây là lỗi
journey quốc tế, không chỉ copy đơn lẻ.

### H32-AS-005 — Mobile dùng được nhưng chưa tối ưu tác vụ precision

Không có page overflow, nhưng editor xếp thành cột rất dài; timeline có thanh cuộn
ngang và cue bị cắt theo viewport. Cần mobile mode theo step, sticky preview/CTA,
fit/zoom và cue editor dạng sheet.

### H32-AS-006 — File tải xuống tên chung `output.mp4`

Khách làm nhiều job dễ ghi đè/khó truy vết. Server nên trả
`<project>_<preset>_<resolution>_<job8>.<ext>` qua Content-Disposition; artifact
vẫn giữ support/job ID.

### H32-AS-007 — Tùy biến subtitle còn thiếu các control giá trị cao

Nên thêm caption width/max lines, alignment, line height/letter spacing,
background opacity/radius/padding, safe-area, drag position, custom font/brand
preset và style theo speaker. Không đưa keyframe/NLE phức tạp vào core.

### H32-AS-008 — Animation/preview chưa có golden parity

UI có Fade/Pop/Slide-up và duration nhưng H32 chỉ golden-sampled TikTok word
emphasis. Cần frame-diff cho 9 preset × animation representative × aspect ratio.

### H32-AS-009 — API locale redirect tạo round-trip thừa

Nhiều request `/autosubvideo/api/...` nhận 302 rồi mới 200 ở `/en/...`. Không gây
fail nhưng tăng latency/churn và làm network log khó đọc. Chuẩn hóa base URL API.

### H32-AS-010 — Test pass nhưng có unhandled thread warning

Hai test media progress vẫn phát `PytestUnhandledThreadExceptionWarning` do stderr
double không iterable. Cần sửa test double/join thread và nâng warning này thành
fail để test xanh không che lỗi concurrency.

## P3

### H32-AS-011 — Bề mặt AI còn dev-facing

WhisperX/Pyannote/Gemini nên hiện dưới intent “Tạo transcript/Phân vai/Dịch”; tên
engine và trạng thái chi tiết chuyển vào tooltip/support diagnostic.

### H32-AS-012 — Export phụ đề chưa rõ khả năng tải từng loại

Checkbox cho SRT/VTT/JSON nhưng màn kết quả chỉ đưa video, ASS, ZIP. Bundle có thể
đúng, song khách cần biết từng định dạng nằm trong ZIP hay tải trực tiếp.
