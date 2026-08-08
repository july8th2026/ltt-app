# UI-RD — Tạo video AI feature matrix

| ID | Feature | Evidence today | Disposition | Required before BUILD |
|---|---|---|---|---|
| TV-01 | Studio shell / responsive composer | 3-zone + mobile drawer browser PASS | DONE | — |
| TV-02 | Model cards/capabilities | registry-driven; browser Mini/Standard/Fast PASS | DONE | — |
| TV-03 | Prompt translator | CSRF route + rate limit exists | KEEP | preserve failure feedback/rate limit |
| TV-04 | Prompt history | 10 prompt gần nhất owner-scoped | DONE | — |
| TV-05 | Reference image/video/audio slots | picker/preview/role/handle, cap 4 thống nhất backend | DONE | — |
| TV-06 | Estimate/credit CTA | báo đúng tổng hold × quantity, ghi rõ settle token thật | DONE | — |
| TV-07 | My Videos grid/status filter/sort | status/model/aspect/sort, grid/list, mobile | DONE | — |
| TV-08 | Card metadata/prompt | DTO an toàn có model/time/params cần hiển thị | DONE | — |
| TV-09 | Preview/download | owner-only Range 206, download thật | DONE | — |
| TV-10 | Retry | no user retry route | DEFER | idempotency, new estimate/hold, user intent and audit |
| TV-11 | Delete/bulk delete | no lifecycle/retention contract | DEFER | soft-delete/storage policy/audit/undo decision |
| TV-12 | Library/asset/templates nav | no corresponding product routes | REJECT/DEFER | do not add fake navigation |
| TV-13 | Grid/list mode | local preference qua reload | DONE | — |
| TV-14 | Reference thumbnails | source image contains illustrative videos | REJECT as fake content | use only real generated output / empty state |
| TV-15 | Nâng cấp video từ card | popup quote 3 credit trên fixture; service owner/CSRF dùng chung | DONE | — |
