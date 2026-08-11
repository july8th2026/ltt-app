# H32.4 — Benchmark sản phẩm cùng nhóm

Nguồn chính thức được kiểm ngày 2026-08-11:

- OpusClip: <https://help.opus.pro/docs/article/introduction-to-opusclip>
- OpusClip pricing/capability: <https://www.opus.pro/pricing>
- Descript Create clips: <https://help.descript.com/hc/en-us/articles/10119670449293-Create-clips-from-your-content>
- Descript editor: <https://help.descript.com/hc/en-us/articles/37585546799757-The-editor-interface>
- CapCut long-to-short: <https://www.capcut.com/tools/long-video-to-shorts>

| Năng lực khách hàng | LTT hiện tại | Chuẩn thị trường | Quyết định |
|---|---|---|---|
| Local video → highlight | Có, chạy GPU thật | Cốt lõi ở cả ba | KEEP |
| Chọn count/length/layout | Có, 1–10, min/max, 4 ratio | Descript 1–20, 10s–5m; layout | KEEP + model-aware |
| Prompt/goal để tìm đoạn | Chưa có | Opus Co-pilot, Descript criteria | EXTEND P1 |
| Import URL/cloud | Chưa có | Opus nhiều nguồn; CapCut Drive/Dropbox | EXTEND P2 |
| Transcript/timeline editor | Chỉ sửa text package | Descript doc+timeline; Opus editor | EXTEND P1 |
| Reframe/manual crop | Auto crop, chưa chỉnh tay | Opus/CapCut smart + manual | EXTEND P1 |
| Caption style | Preset theo brand, chưa editor | Opus/CapCut chỉnh template | EXTEND P1 |
| B-roll/filler/pause/audio | Engine có một phần, UI chưa có | Opus/Descript công khai rõ | EXTEND có chọn lọc |
| Brand template | 4 preset tĩnh | Opus template/font/logo/intro/outro | EXTEND P2 |
| Publish/schedule | Chỉ metadata ZIP | Opus post/scheduler; CapCut share | HANDOFF trước, không nhồi runtime |
| XML/pro editor export | Chưa có | Opus XML Premiere/Resolve | EXTEND P2 |
| Analytics/team | Chưa có | Opus có ở tier cao | DEFER sau product-market fit |

Không sao chép nguyên editor đa lớp của đối thủ vào form tạo clip. MVP tối ưu là
hai bước rõ: **Generate** nhẹ control → **Review/Edit** theo transcript, crop và
caption; publish là handoff sang app Publish Bot dùng hợp đồng nội bộ.
