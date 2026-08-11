# H32.4 — Findings

## Đã sửa trong phase

| ID | Severity | Hiện tượng → xử lý | Evidence |
|---|---|---|---|
| CLIP-H32-01 | P1 | SRT dùng timeline nguồn 39,780s → rebase/clamp về 0..duration, kể cả draft sửa tay | pytest + ZIP byte inspection |
| CLIP-H32-02 | P1 | progress engine song song lùi và spam hàng trăm event → aggregate có lock, đơn điệu, bước ≥2% | pytest + 2 job E4 |
| CLIP-H32-03 | P1 | probe NVENC 64×64 âm giả trên RTX 50xx → 256×256 yuv420p | ffmpeg 64 fail/256 pass + output NVENC |
| CLIP-H32-04 | P1 | 1:1/4:5 dùng 1080×1920 pixel không vuông → preset giữ cạnh ngắn và đúng aspect | pytest + 1080×1350 SAR 1:1 E4 |
| CLIP-H32-05 | P1 | ticket upload thiếu CSRF/type/size và fallback đọc body vô hạn → hardening + cap+1 | pytest + browser negative/positive |
| CLIP-H32-06 | P1 | video không probe được và min/max sai có thể vào worker → fail rõ trước/đầu pipeline | pytest/source |
| CLIP-H32-07 | P2 | upload error trả HTML trong API JSON → response JSON ổn định | browser E3 |

## Còn mở

| ID | Severity | Finding | Acceptance |
|---|---|---|---|
| CLIP-H32-08 | P1 | Simple presigned PUT chỉ tin `size_bytes` client; chưa kiểm actual object size trước queue | Storage metadata HEAD, max bytes server-side/lifecycle, reject+delete object vượt cap |
| CLIP-H32-09 | P1 | Engine chưa nhận cancel/deadline xuyên analysis/editorial/render | cancel_check từng engine/subprocess, kill tree, refund và E4 cancel |
| CLIP-H32-10 | P1 | Upload/source/output chưa có TTL/delete/quota tự phục vụ | retention policy, quota, delete owner-only, cleanup audit |
| CLIP-H32-11 | P1 | Balanced/Best, multi-clip, auto/EN và phần lớn genre chưa E4 | matrix staging có latency/VRAM/output/credit cho từng capability |
| CLIP-H32-12 | P1 | Transcript Fast VI có lỗi nghe rõ; score 0,659 không chứng minh chất lượng ngôn ngữ | WER sample, confidence cue, correction UX; khuyến nghị Balanced khi VI khó |
| CLIP-H32-13 | P1 | Sửa transcript chỉ đổi SRT/package, caption cháy trong MP4 không đổi | editor preview + rerender revision có quote/credit rõ |
| CLIP-H32-14 | P1 | Không có prompt/topic/exact timeframe để hướng AI chọn đoạn | guided selection với preview quote, deterministic payload/test |
| CLIP-H32-15 | P2 | Không có transcript/timeline trim, manual reframe, caption style preview | Review/Edit workspace tối giản, không biến form Generate thành editor dev |
| CLIP-H32-16 | P2 | History chỉ 8, thiếu search/filter/delete/folder và bulk export | owner pagination, filters, lifecycle actions, ZIP streaming |
| CLIP-H32-17 | P2 | 18,6s output ~35,5 MB/15,25 Mbps; chưa có profile bitrate theo platform | target profile/quality study, VMAF/visual A-B trước hạ bitrate |
| CLIP-H32-18 | P2 | Package nền tảng chỉ metadata, chưa publish/schedule; nhãn dễ hiểu quá mức | đổi copy thành “metadata”; handoff typed sang Publish Bot |
| CLIP-H32-19 | P2 | Job detail chỉ quay về danh sách job, không về app | contextual return link theo app/job |
| CLIP-H32-20 | P3 | Copy còn “1 clips” và VI/EN trộn ở một số fragment | locale/plural regression |

Không có P0 tái hiện. Release rộng bị chặn bởi 08–14.
