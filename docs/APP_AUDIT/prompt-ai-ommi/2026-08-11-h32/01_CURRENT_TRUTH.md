# Current truth và đối chiếu module nguồn

## Module Prompt Seedance Studio — chỉ đọc

| Miền | Năng lực quan sát được | Quyết định H32.2 |
|---|---|---|
| Prompt Library | meta/sample/template/snippet, tìm/lọc, lịch sử, bulk | KEEP snippet + catalog/version; DEFER bulk/admin |
| Styles V2 | mood/camera/light/motion/color/negative/inheritance | KEEP body + negative; DEFER inheritance sâu |
| Meta prompts | target format, placeholder, default, preview bundle | KEEP meta body + preview; EXTEND validation sau |
| Brief Studio | goal/audience/duration/scenes/style/meta/preflight/preview | KEEP và đưa ra UI khách hàng |
| Team dashboard | team spend, activity feed, team folders | REJECT khỏi app khách hàng; thuộc quản trị |

Không copy database, file người dùng, secret hay runtime code từ `D:\BOT
GEMINI`. App dùng catalog immutable 8 style + 4 meta + 4 snippet đã chắt lọc.

## Trạng thái sau nâng cấp

- Brief đã có title, story, goal, audience, duration, scene count, aspect,
  language, Style, Meta Director và tối đa 8 prompt block.
- Project chỉ lưu ID catalog/private; backend resolve theo ownership tại thời
  điểm preview/quote/run. ID đã mất trả 422 rõ ràng.
- Preview là deterministic, miễn phí, có checklist và hiển thị chính xác style,
  negative, meta, snippet, resource/continuity gửi vào composer.
- Quote chỉ mở sau khi preflight pass; toàn bộ field bị khóa khi modal giá mở.
- Apply job gửi revision thật; thiếu/stale revision trả 409.
- API theo locale hiện tại, không còn 302 cho journey mới.

Chưa chứng minh provider thật: fixture không có provider/worker key. Vì vậy
không tuyên bố chất lượng nội dung AI hoặc settlement credit E4.
