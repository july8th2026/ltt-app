# A2–A3 — Journey và Control Registry

## State matrix

| State | Kết quả quan sát | Verdict |
|---|---|---|
| Empty | CTA upload, cấu hình, quote rỗng và output empty rõ | LIVE |
| File selected | Hiện tên/duration/size; quote đổi theo tier và số clip | PARTIAL — duration/quote từ browser |
| Validation | Có giới hạn UI nhưng server admission chưa probe/khóa object | BROKEN |
| Insufficient credit | Contract worker/ledger có tăng hold và fail/refund | PARTIAL — có thể fail muộn sau upload/probe |
| Queued/running | Card có progress/stage và link nhật ký | PARTIAL — không polling trong trang app |
| Done | Preview, score, rationale, compare, transcript, download/package | PARTIAL — SRT sai timeline |
| Partial render | Worker có thể DONE với ít output hơn | MISLEADING — không công bố partial/refund |
| Error | Card lỗi và link log | PARTIAL — lỗi thô, không CTA sửa/retry |
| Cancel/retry | Job platform có contract nhưng worker không cooperative cancel | BROKEN |
| Resume/crash | Chỉ resume khi manifest hoàn chỉnh đã tồn tại | PARTIAL |
| Mobile | Không overflow ở 390×844 | LIVE có điều kiện; hành trình dài/dày |
| EN | Route và phần lớn nội dung dịch | PARTIAL — còn chuỗi VI ở estimate |

## Control Registry

| Screen/control | Action/API/credit | State | Gap chính | Evidence |
|---|---|---|---|---|
| Upload zone | file picker; direct ticket hoặc multipart queue | PARTIAL | ticket không CSRF/size binding; fallback đọc trước cap | E1 source, E3 browser |
| Source library | chọn object từ job gần đây | PARTIAL | 8 mục, không delete/search, nguồn orphan không thấy | E1/E3 |
| Aspect ratio | 9:16, 1:1, 16:9, 4:5 | LIVE | chưa preview safe-area | E1/E3 |
| Number of clips | 1/2/3/5/8/10; ảnh hưởng quote | LIVE | partial output không nói rõ | E2/E3 |
| Advanced disclosure | tier/brand/genre/language/duration/platform | PARTIAL | min/max contract lệch và không đảm bảo min≤max | E1/E3 |
| Estimate | POST `/estimate`; không giữ tiền | PARTIAL | tin duration browser, không canonical probe | E1/E3 |
| Tạo clip | POST `/queue`; hold estimate | PARTIAL | input object/MIME/duration chưa đủ tin cậy | E1/E2 |
| Job log | `/jobs/{id}` | LIVE | thông điệp lỗi còn kỹ thuật | E3 |
| Progress | card progress/stage | PARTIAL | không tự refresh/poll | E1/E3 |
| Cancel/retry | qua control plane | BROKEN | handler dài không check cancel/deadline | E1 |
| Score/rationale | giải thích hook/flow/value… | PARTIAL | nhãn metric nội bộ; không calibration/output QA | E1/E3 |
| Compare | chọn tối đa hai video | LIVE cơ bản | không sync playback/zoom/frame | E3 |
| Download MP4 | owner-checked stream Range | LIVE | retention chưa rõ | E2/E3, HTTP 206 |
| Edit title/transcript | lưu draft vào package revision | PARTIAL | không đổi caption cháy; UI có nói rõ | E2/E3 |
| Platform checkboxes | chọn metadata TikTok/Shorts/Reels | PARTIAL | copy gần như cùng mẫu; không edit theo platform | E1/E3 |
| Lưu package | POST revision owner-only | LIVE | conflict/version UX còn tối thiểu | E2/E3 |
| Tải ZIP | server spool MP4/SRT/JSON | BROKEN cho publish | SRT tuyệt đối; bundle lớn đi qua web process | E1/E3/E4 artifact |

## Browser verification

- Desktop empty/source/advanced và ba job state; mobile 390×844; VI/EN.
- Quote file thật: 52 giây, High quality/3 clip = 25 credit; Fast/10 clip = 55 credit.
- Compare hai clip, mở transcript, tải ZIP; MP4 trả `206 Partial Content`; ZIP `200`.
- Console: 0 error, 0 warning. Failed network liên quan luồng: 0.
- ZIP đọc trực tiếp: `captions/clip_01.srt` bắt đầu `00:00:04,000 --> 00:00:08,000` dù clip độc lập bắt đầu tại 0.
- Ảnh ở `evidence/`; không chạy provider/GPU render production.
