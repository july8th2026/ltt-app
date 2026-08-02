# UI-RD — Tạo video AI feature matrix

| ID | Feature | Evidence today | Disposition | Required before BUILD |
|---|---|---|---|---|
| TV-01 | Studio shell / responsive composer | form + results exist | RESTYLE | lock desktop/mobile information architecture |
| TV-02 | Model cards/capabilities | registry is model-driven | KEEP/RESTYLE | bind all options to registry |
| TV-03 | Prompt translator | CSRF route + rate limit exists | KEEP | preserve failure feedback/rate limit |
| TV-04 | Prompt history | no data model/UI | BUILD or DEFER | retention, privacy, max size and owner access |
| TV-05 | Reference image/video/audio slots | upload + asset:// pipeline exists | EXTEND | expose roles/handles, validate type/count/size visibly |
| TV-06 | Estimate/credit CTA | estimate and reserve/settle exist | KEEP/RESTYLE | server estimate only; no VND/credit fiction |
| TV-07 | My Videos grid/status filter/sort | 12 owner jobs exist | BUILD | owner query, empty/error/processing states, mobile |
| TV-08 | Card metadata/prompt | job params/result contain partial data | EXTEND | safe DTO; avoid secret/ref URLs |
| TV-09 | Preview/download | owner-only range/presigned output exists | KEEP/RESTYLE | output/auth failure state |
| TV-10 | Retry | no user retry route | DEFER | idempotency, new estimate/hold, user intent and audit |
| TV-11 | Delete/bulk delete | no lifecycle/retention contract | DEFER | soft-delete/storage policy/audit/undo decision |
| TV-12 | Library/asset/templates nav | no corresponding product routes | REJECT/DEFER | do not add fake navigation |
| TV-13 | Grid/list mode | no server persistence | EXTEND | lock local preference vs server profile |
| TV-14 | Reference thumbnails | source image contains illustrative videos | REJECT as fake content | use only real generated output / empty state |
