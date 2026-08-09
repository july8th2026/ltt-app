# 05 — Findings: Tạo ảnh AI + Thumbnail

## P1

| ID | Finding | Tác động | Direction |
|---|---|---|---|
| F-001 | Thumbnail reserve/settle/UI dùng 5 credit cho mọi model; Gemini 3 Pro đắt hơn Flash và app general đã định 16 | lỗ đơn vị, giá sai giữa hai mode | một cost table/provider pricing snapshot dùng chung; quote server-side theo model/resolution/count |
| F-002 | Edit/style mode không kiểm prerequisite ở client; POST 400 render lại không `form_values`, xóa prompt/mode và dừng tại `/queue` | mất công việc khách hàng | validate trước, preserve draft/file metadata, PRG về canonical URL, focus lỗi |
| F-003 | Upload đọc toàn body trước cap; reference không TTL/delete; Job purge tách artifact làm output inaccessible nhưng blob còn | DOS/storage/privacy/data loss | early body limit/streaming; staging/promote/TTL/delete; artifact+Job retention graph |

## P2

| ID | Finding |
|---|---|
| F-004 | Thumbnail authenticated fragment ở URL không locale nên `/en/` vẫn VI; mode links bỏ `/en/`. |
| F-005 | Thumbnail queued/running card không poll; user phải reload hoặc rời sang Jobs. |
| F-006 | History mỗi mode chỉ 12 job; thiếu search/filter/page/folder/project/delete/download/cancel/retry. |
| F-007 | Một số owner lookup chỉ quét 60 job gần nhất, làm edit/remix output cũ thất bại. |
| F-008 | Partial 1/4 được ghi `done`; UI không nêu partial errors, refund hay actual/requested rõ. |
| F-009 | Preview config bỏ model, giá, reference, Brand Kit và capability/resolution. |
| F-010 | Ratio/resolution không model-aware; Gemini mới hỗ trợ nhiều ratio, 1K/2K/4K và số reference khác nhau. |
| F-011 | General chỉ source+style; không reusable asset library, reference role/weight/strength/multiple character/object. |
| F-012 | Thumbnail 7 nhóm control mở đồng thời; mobile document 2.802px, CTA không sticky/progressive. |
| F-013 | Brand Kit chỉ một latest row, chỉ lưu khi submit paid job; thiếu manage/version/logo/safe-zone/template. |
| F-014 | “82/100 kỹ thuật” không đo text accuracy, semantics, policy, CTR/watch-time; dễ bị hiểu là quality score. |
| F-015 | Compare chỉ đặt hai ảnh cạnh nhau; thiếu zoom, metadata, prompt/settings diff và chọn winner. |
| F-016 | Error history đưa provider/internal copy trực tiếp cho customer; thiếu stable error code/guidance. |
| F-017 | Không có retention/delete disclosure hoặc self-service xóa source/output. |
| F-018 | Hai app slug/job store độc lập trong một product; history/analytics/brand không xuyên mode. |

## P3

| ID | Finding |
|---|---|
| F-019 | Preset “KHANH-Realistic”, “Minecraft (Lâm)” mang tên nội bộ, thiếu customer curation. |
| F-020 | Heading mode Thumbnail vẫn chủ yếu “Tạo ảnh AI”, orientation yếu. |
| F-021 | Copy VI/EN trộn: Model AI, OUTPUT HISTORY, credit, Brand Kit. |
| F-022 | Không có explicit download filename/format/metadata; “Mở” phụ thuộc browser. |
| F-023 | Legacy redirect `/thumbnail` bỏ locale/query state. |
| F-024 | Test chủ yếu HTML/source/API; chưa có Playwright regression money/data/i18n. |

## Root causes

1. Hợp nhất presentation nhưng chưa hợp nhất contract money/history/locale/data.
2. Capability được đưa ra theo provider list, nhưng cost/resolution/reference chưa
   có một model capability registry canonical.
3. Job metadata, reference và artifact được thiết kế tách rời lifecycle.
4. Server-rendered validation chưa có durable form/draft contract.
