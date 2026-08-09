# Browser route matrix vòng 2

Browser: Chrome headed qua Playwright; test customer; local fixture
`127.0.0.1:8112`; desktop 1440×900 và mobile 390×844. Mỗi route chờ network
idle, ghi status/final URL/console/request failed/overflow và first Tab.

| Manifest | Route yêu cầu | Kết quả desktop/mobile | Console/network | Responsive |
|---|---|---|---|---|
| upscalevideo | `/upscalevideo` | 200 / 200 | sạch | không overflow |
| taovideo | `/taovideo` | 200 / 200 | sạch | không overflow |
| autosubvideo | `/autosubvideo` | 200 / 200 | sạch | không overflow ở shell hiện tại |
| prompt_ai_ommi | `/prompt-ai-ommi` | 200 / 200 | sạch | không overflow |
| taoanh | `/taoanh` | 200 / 200 | sạch | không overflow |
| thumbnail | `/thumbnail` → `/taoanh/thumbnail` | 200 / 200 | sạch | không overflow |
| taoclipngan | `/taoclipngan` | 200 / 200 | sạch | không overflow |
| chataistudio | `/chataistudio` | 200 / 200 | sạch | không overflow |
| agent | `/agent/canvas` | 200 / 200 | sạch | không overflow; first Tab ở canvas section |
| socialbot | `/facebook` | 200 / 200 cho customer thường | sạch | **overflow 392/390** |
| demo | `/demo` | 404 / 404 đúng contract | 404 resource dự kiến | không phải customer UI |
| kichban | `/kichban` → `/agent/canvas` | 200 / 200 | sạch | runtime ẩn đúng |
| mediatools | `/mediatools` → `/agent/canvas` | 200 / 200 | sạch | runtime ẩn đúng |

## Hai finding mới được tái hiện

### RA-UI-001 — Socialbot mobile overflow (P2, E3)

`documentElement.scrollWidth=392` tại viewport 390. `nav.apptabs` có
`scrollWidth=995/clientWidth=375`; callback copy trong card có
`scrollWidth=349/clientWidth=290`. Thanh tab cuộn ngang có thể là chủ ý, nhưng
document-level overflow và callback không wrap là lỗi responsive. Evidence:
`evidence/01-socialbot-mobile-overflow.png`.

### RA-A11Y-001 — Upscale file input không có accessible name (P2, E3)

`#vfile` opacity 0 vẫn hiện trong accessibility/form surface nhưng `labels=[]`,
không `aria-label`/`aria-labelledby`. Nút “Chọn tệp từ máy” không thay nhãn cho
input. Evidence: DOM inspection và
`evidence/02-upscale-upload-control.png`.

Hai finding này không thay đổi Q sau làm tròn; chúng củng cố G6 FAIL hiện có.

