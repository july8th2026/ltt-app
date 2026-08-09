# A6 — Findings và root cause

## P1 — blocker lớn (4)

| ID | Hiện tượng / bằng chứng | Root cause và ảnh hưởng | Acceptance |
|---|---|---|---|
| CLIP-P1-01 | ZIP SRT clip 1 bắt đầu 4s, clip 2 bắt đầu 27s | caption segment giữ timestamp nguồn, exporter không rebase; phụ đề standalone lệch/hỏng khi publish | mọi SRT bắt đầu theo timeline clip, clamp 0..duration; golden ZIP test |
| CLIP-P1-02 | Direct ticket không CSRF/size binding; queue tin object owner-prefix, MIME/duration client; fallback đọc trước cap | admission không có một validator canonical; có thể upload orphan/không phải video/underquote và gây storage/worker DoS | ticket ký size/type/expiry, stream cap, ffprobe trước hold, cleanup orphan, abuse tests |
| CLIP-P1-03 | Worker dài không check cancel, không deadline theo stage | JobContext có cooperative cancel nhưng handler không dùng; khách hủy vẫn có thể đốt GPU/tạo artifact, state/credit race | cancel checkpoint từng stage/clip, subprocess timeout/kill, ledger/artifact race tests |
| CLIP-P1-04 | Source/output không delete/TTL khép kín; job purge có thể làm artifact mất đường truy cập | lifecycle owner/job/artifact chưa có policy và collector chung | policy retention, delete/export, reference count/GC, audit log và restore evidence |

## P2 — material (15)

1. Quote dùng duration browser trước khi server probe; có thể tăng hold/fail muộn.
2. `min_duration`/`max_duration` không clamp/đảm bảo thứ tự; giới hạn manifest và HTML không đồng nhất.
3. Render lỗi từng clip bị bỏ qua, DONE nếu còn một output; UI không nói “hoàn tất một phần” hay quyết toán.
4. Resume chỉ dựa manifest cuối; crash giữa clip lặp phân tích/render và tốn GPU.
5. Card running không polling, trạng thái đứng yên tới khi reload.
6. Error card hiển thị chuỗi kỹ thuật, không hướng dẫn sửa/retry.
7. History chỉ 8 job; không pagination/search/filter/project/delete.
8. Source library chỉ 8 asset trong 60 job gần nhất; không quản lý orphan/version.
9. Brand preset cố định; không quản lý logo/font/safe zone/template version.
10. Metadata ba nền tảng gần như cùng mẫu; không editor/preview riêng từng nền tảng.
11. Compare thiếu sync playback, frame/zoom và quyết định chọn winner.
12. `/en/taoclipngan` còn chuỗi VI “Chọn video để tính chi phí.”
13. ZIP được spool qua web process; bundle lớn gây temp disk/bandwidth pressure, không direct bundle/range.
14. Chưa có golden/blind evaluation cho highlight, reframe, caption WER/burn và score calibration.
15. Chưa có URL/cloud import hoặc handoff trực tiếp từ Asset/Seedance/AutoSub; time-to-value kém benchmark.

## P3 — polish (5)

1. Score/rationale còn tên metric gần nội bộ, chưa diễn đạt hoàn toàn theo creator.
2. Mobile không overflow nhưng output/transcript kéo trang rất dài và dày.
3. Tier/brand/platform copy chưa có trợ giúp theo ngữ cảnh hoặc mẫu trước/sau.
4. Không có notification khi job dài hoàn tất ngoài trang hiện tại.
5. CTA package chưa làm nổi bật khác biệt “sửa metadata/SRT” và “không render lại caption cháy”.

Không có P0 được chứng minh trong fixture. Tổng: **0 P0 · 4 P1 · 15 P2 · 5 P3**.
