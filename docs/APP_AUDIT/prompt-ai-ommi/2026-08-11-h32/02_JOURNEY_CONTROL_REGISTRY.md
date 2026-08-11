# Journey và control registry đã kiểm

| Bước/control | Thiết lập test | Kết quả |
|---|---|---|
| Tạo project | `H32 Prompt AI Catalog Test` | PASS, revision khởi tạo |
| Story | 116 ký tự tiếng Việt | PASS, preflight ≥20 |
| Goal/audience | continuity / khán giả phim ngắn | PASS, vào master prompt |
| Duration/scenes | 30 giây / 6 cảnh | PASS, giới hạn 3–600 / 1–20 |
| Aspect/language | 16:9 / vi | PASS, lưu và preview |
| Style | Hành động điện ảnh | PASS, body + negative resolve thật |
| Meta | Video liên tục có timecode | PASS, meta body resolve thật |
| Snippet | consistency + negative nền | PASS, cả hai vào prompt |
| Lưu | explicit `Lưu brief` | PASS; bỏ blur autosave |
| Preview | checklist + master prompt | PASS, miễn phí, không provider |
| Quote | Director / Gemini 2.5 Flash | PASS, 6 credit, field locked |
| Apply completed job | revision current/stale | PASS 200 / 409 bằng integration |
| Export | JSON/MD/ZIP link | Có, chưa download lại trong H32.2 |
| Mobile | 390×844 | PASS, scrollWidth 375 < 390 |
| Console/network | console 0; journey mới 200 | PASS; không còn GET redirect 302 |

Thiết lập chưa kiểm E4: model switch, provider output quality, token usage,
settlement/refund khi provider lỗi, export file vật lý.
