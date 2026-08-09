# 03 — Competitor Benchmark: Auto Sub Studio

Snapshot 2026-08-09. Chỉ dùng trang/tài liệu chính thức; con số marketing không
được coi là blind evidence về độ chính xác.

## Competitor set

| Sản phẩm | Vai trò | Nguồn chính thức | Giới hạn evidence |
|---|---|---|---|
| CapCut | Social-first direct leader | [Auto captions](https://www.capcut.com/help/how-to-recognise-subtitles), [caption workflow](https://www.capcut.com/resource/video-caption-generator) | E1 docs, khác nhau theo platform/region |
| Descript | Script/timeline leader | [Captions](https://help.descript.com/hc/en-us/articles/37469585005197-Add-and-style-captions), [timeline](https://help.descript.com/hc/en-us/articles/10249275208717-Timeline-overview) | E1 docs, không chạy paid UI |
| VEED | Browser creator suite | [Auto subtitles](https://www.veed.io/tools/auto-subtitle-generator-online) | E1 marketing/docs |
| Adobe Premiere | Professional reference | [Captions overview](https://helpx.adobe.com/au/premiere/desktop/add-text-images/insert-captions/about-captions.html), [Speech to Text](https://helpx.adobe.com/premiere/desktop/add-text-images/insert-captions/auto-transcribe-video-using-speech-to-text.html) | E1 docs, desktop pro không phải MVP parity target |
| Kapwing | Browser/team direct competitor | [Subtitle editor](https://www.kapwing.com/subtitles), [workflow help](https://www.kapwing.com/help/add-captions/) | E1 official; accuracy claim chưa blind verify |

## Capability matrix

Điểm `0` chưa có/chưa chứng minh; `1` tối thiểu; `2` dùng được; `3` mạnh.

| Capability/JTBD | Loại | Trọng số | LTT | CapCut | Descript | VEED | Adobe | Kapwing | Gap/quyết định |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Upload/drag/link/media cloud | TABLE_STAKES | 5 | 1 | 3 | 3 | 3 | 3 | 3 | FIX drop + asset/project |
| Auto transcript/language | TABLE_STAKES | 8 | 2 | 3 | 3 | 3 | 3 | 3 | KEEP fallback; FIX honest capability |
| Editable transcript + exact timing | TABLE_STAKES | 8 | 2 | 3 | 3 | 3 | 3 | 3 | FIX keyboard/zoom/snap |
| Split/merge/drag timeline | TABLE_STAKES | 7 | 2 | 3 | 3 | 2 | 3 | 2 | KEEP; mobile/precision |
| Speaker detection/style | TABLE_STAKES | 6 | 2 | 2 | 3 | 2 | 3 | 3 | FIX conflict/per-speaker style |
| Translation/multilingual tracks | TABLE_STAKES | 7 | 2 | 3 | 3 | 3 | 3 | 3 | FIX lifecycle/quota/EN |
| Dynamic word highlight/animation | TABLE_STAKES | 7 | 2 | 3 | 3 | 3 | 2 | 3 | FIX preview parity |
| Brand preset/custom font reuse | DIFFERENTIATOR | 5 | 2 | 3 | 3 | 2 | 3 | 3 | BUILD brand kit after blockers |
| QA/readability/accessibility | TABLE_STAKES | 6 | 2 | 2 | 2 | 2 | 3 | 3 | QA is strength; block fatal output |
| Export burn + sidecar formats | TABLE_STAKES | 7 | 3 | 3 | 3 | 3 | 3 | 3 | KEEP delivery; fix MIME/name |
| Project/history/collaboration | TABLE_STAKES | 7 | 1 | 3 | 3 | 3 | 3 | 3 | Major gap |
| Autosave/conflict/offline recovery | TABLE_STAKES | 7 | 1 | 2 | 3 | 2 | 3 | 2 | P1 repair |
| Canonical quote/usage limits | TABLE_STAKES | 6 | 1 | 2 | 2 | 2 | 2 | 2 | P1 economics/admission |
| Fast long-media waveform | TABLE_STAKES | 6 | 1 | 3 | 3 | 2 | 3 | 2 | Precompute peaks; no fake data |
| Customer-first VI/EN/mobile | TABLE_STAKES | 8 | 1 | 3 | 3 | 3 | 3 | 3 | Major gap |
| Full pro video editor | ANTI_FEATURE | 0 | 1 | 3 | 3 | 3 | 3 | 3 | REJECT full parity for MVP |

## Kết luận thị trường

- **Market Score: 65/100.** LTT đã có breadth đáng kể: import đa định dạng,
  multi-track, QA, diarize, translate, 9 style, snapshot render và bundle.
- Khoảng cách quyết định không phải thêm nhiều style. Đó là project lifecycle,
  recovery, timeline precision, preview trung thực, media admission và i18n/mobile.
- Descript cho phép zoom/fit, blade/slip/hand/range và captions đồng bộ script;
  LTT nên lấy “progressive precision”, không sao chép toàn bộ editor chuyên nghiệp.
- Adobe tách transcript thành caption track và export burn/sidecar; kiến trúc
  multi-track của LTT đúng hướng nhưng cần validation và style per track.
- CapCut/Kapwing/VEED đều đặt upload/auto/manual/edit/style/export thành luồng
  khách hàng rõ. LTT đang để capability kỹ thuật và trạng thái provider lấn át.
- Differentiator thực tế nên giữ: QA score + artifact bundle + pipeline AI phụ,
  nhưng chỉ sau khi các thao tác này đáng tin và recoverable.

