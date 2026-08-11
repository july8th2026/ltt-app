# H32.1 — Journey & control registry

| ID | Journey/control | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|---|
| AS-C01 | Upload video | PASS | Video thật, metadata đúng |
| AS-C02 | Import SRT/VTT/ASS | PASS với SRT | 4 cue, Unicode VI |
| AS-C03 | Transcript search/QA | PASS | 95/100, cảnh báo câu dài |
| AS-C04 | Add/split/merge/delete cue | PRESENT | Control đúng trạng thái enable/disable; cần keyboard matrix |
| AS-C05 | Multi-track/show-hide | PRESENT | Chưa chạy render nhiều track ở H32 |
| AS-C06 | WhisperX | BLOCKED-CONFIG | Fixture báo “Chưa cấu hình”, CTA khóa trung thực |
| AS-C07 | Pyannote | BLOCKED-CONFIG | Như trên |
| AS-C08 | Gemini translate | BLOCKED-CONFIG | Như trên |
| AS-C09 | 9 template presets | PASS chọn TikTok Bold | Chưa golden-test đủ 9 |
| AS-C10 | Font/size/colors/outline/shadow | PASS sampled | Montserrat/64/outline thể hiện trong output |
| AS-C11 | Background/position/karaoke | PASS sampled | Middle + active word vàng |
| AS-C12 | Animation | PARTIAL | Control có 4 mode + duration; chưa đo render parity |
| AS-C13 | Resolution/format/quality | PASS sampled | source/MP4/standard; chưa matrix 12 tổ hợp |
| AS-C14 | Quote before submit | PASS | 2 credit, 0,25 phút |
| AS-C15 | Credit hold/settlement | PASS | 1000 → 998 |
| AS-C16 | Progress/cancel | PASS progress | Cancel chưa kích hoạt vì sẽ phá job golden |
| AS-C17 | Video artifact | PASS | Media probe + visual frame |
| AS-C18 | Subtitle artifact | PASS presence | ASS + ZIP có link; cần content matrix cho từng format |
| AS-C19 | Job history/support ID | PASS | Timeline event và support ID tồn tại |
| AS-C20 | Desktop 1440 | PASS | Không overflow, console 0 |
| AS-C21 | Mobile 390 | PARTIAL | Không page overflow nhưng hành trình rất dài; timeline cuộn ngang |
| AS-C22 | Locale `/en` | FAIL | Shell EN nhưng phần Studio phần lớn vẫn VI |
| AS-C23 | Download filename | FAIL-UX | Browser nhận tên chung `output.mp4` |

## Network/browser

- Console: 0 error, 0 warning.
- Journey không có request 4xx/5xx.
- API chưa locale-prefix thực hiện 302 sang `/en/...` trước 200; đúng chức năng
  nhưng tăng một round-trip cho nhiều request.
