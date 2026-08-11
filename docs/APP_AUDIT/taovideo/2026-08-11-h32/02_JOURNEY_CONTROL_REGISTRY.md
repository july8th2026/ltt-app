# H32.5 — Journey & Control Registry

## Journey/state matrix

| State/flow | Kết quả thật | Verdict |
|---|---|---|
| Default + estimate | Mini/4s/16:9/480p; quote 47; CTA mở sau 200 | LIVE |
| Standard capability | 480/720/1080/4K; 4–15s; 6 tỉ lệ | LIVE |
| Reference image | `GiaoDien.png` preview IMG, role/handle render an toàn | LIVE |
| Saved assets | Collapsed mặc định; sidebar mở + scroll đúng | LIVE |
| Grid/list | Đổi view và giữ qua reload bằng localStorage | LIVE |
| Filter done | Còn đúng 1 card; status `Hoàn tất` | LIVE |
| Empty combination | 0 card; giải thích + CTA mở composer | LIVE |
| Running/error/cancelled | Badge/progress/error và count đúng | LIVE |
| Estimate HTTP 500 | `Lỗi · Thử lại`, CTA disabled, aria-busy kết thúc | LIVE |
| Upscale quote | Dialog 1080p báo 3 credit; không confirm/job | LIVE |
| Remix | Khôi phục prompt/model/preset nhưng count=2, refs=0 | PARTIAL |
| Mobile closed | inert/aria-hidden; Tab không vào composer | LIVE |
| Mobile open/close | close button rõ; focus return; không overflow | LIVE |

## Control Registry

| Control | Action/contract | Loading/error | Keyboard/mobile | Verdict |
|---|---|---|---|---|
| Model cards | JS registry + estimate | pending/failed quote khóa submit | radio/label | LIVE |
| Prompt/history | textarea/select | required trước POST | label, keyboard | LIVE |
| EN/ZH/VI | `/translate`, CSRF | server message | button | LIVE |
| Creative options | prompt guidance, không native param | disclosure đúng | details | LIVE |
| 3 reference pickers | multipart + local preview | limit tổng 4 | file chooser | LIVE |
| Role/handle | metadata provider | validation server | label/select/input | LIVE |
| Saved assets | owner-scoped keys | empty state | details/checkbox | LIVE |
| Duration/aspect/resolution | capability dependent | fallback canonical | select | LIVE |
| Count 1/2 | tạo 1–2 job | quote nhân count | select | LIVE |
| Audio | bool provider setting | capability chưa canary audio | checkbox | PARTIAL |
| Quote/Create | `/estimate`, `/queue` | busy/fail/disabled | dock mobile/desktop | LIVE UI |
| Status tabs/filter/sort | GET query | empty state | links/select | LIVE |
| Grid/list | client state | fallback grid | buttons | LIVE |
| Video player/download | owner + Range | artifact error chưa có card recovery | native player/link | PARTIAL |
| Variant | client refill | mất reference, tự count=2 | button | PARTIAL |
| AI Upscale | quote→confirm shared service | dialog error copy | dialog | LIVE quote |
| Nhật ký | `/jobs/{id}` owner scope | job timeline | link | LIVE |
| Cancel/retry/delete | chưa có contract tại app | — | — | MISSING |

## Browser matrix

| Viewport/state | Console | Request | Overflow/focus | PASS |
|---|---:|---:|---|---|
| 1.586×992 EN all/grid/list/model/ref | 0 | 200/206 | không overflow | PASS |
| 1.586×992 VI asset/done/empty/dialog | 0 | 200/206 | không overflow | PASS |
| 390×844 VI library | 0 | 200/206 | không overflow | PASS |
| 390×844 EN composer | 0 | 200/206 | inert/close/return focus | PASS |
| Quote negative 500 chủ ý | HTMX ghi expected error | 500 chủ ý | CTA disabled | PASS |

Ảnh ở `evidence/`; negative probe không tính là failed request của final clean
run.
