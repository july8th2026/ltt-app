# 01 — Bản đồ UI thực tế (đọc từ live repo, 2026-08-26)

Đo từ mã đang chạy, không từ tài liệu cũ.

## Stack thật

| Tầng | Thực tế |
|---|---|
| Template | Jinja2 — **61** tệp ở `server/templates`, cộng template app-local |
| CSS toàn cục | **`server/static/ltt.css`** — 126 KB, 788 dòng (viết tay dạng nén, dòng dài nhất 8.711 ký tự) |
| React | **3** workspace: `agent-canvas` (70 KB CSS), `autosub-studio` (21 KB), `prompt-ai-ommi` (14 KB) |
| Build CSS | **KHÔNG CÓ.** Không SCSS, không PostCSS, không Tailwind, không `package.json` ở gốc |
| Cache-bust | `server/templating.py:TAI_SAN_CO_VERSION` băm nội dung → `?v=<hash>` |

⭐ **`ltt.css` không được sinh ra — nó được gõ tay ở dạng nén.** Đây là dữ kiện quan
trọng nhất về cách bảo trì: mọi thay đổi là sửa trực tiếp vào tệp phân phối, không
có tầng nguồn nào để đọc cho dễ.

## Ai là authority

**Chỉ có một** CSS authority toàn cục, và đó là tin tốt: không có hai framework
cạnh tranh nhau. Các bundle React đóng gói CSS riêng và **không** rò ra ngoài
(mỗi bundle chỉ nạp ở route của nó).

Phân tán còn lại:

| Nguồn | Số lượng |
|---|---|
| Khối `<style>` trong template | 11 tệp, ~500 dòng CSS |
| Thuộc tính `style=""` nội tuyến | **470** |
| Màu hex viết cứng trong `ltt.css` | **437 lần, 316 màu duy nhất** |

## Design token — nền đã tốt, PHẢI tái dùng

**64 token**, có lớp ngữ nghĩa đầy đủ:

```
--text-primary/secondary/muted      --surface-base/canvas/raised/overlay/interactive
--brand-primary/hover/soft/border   --border-subtle/strong
--status-danger/success/... (9)     --radius/-sm/-md/-lg
--focus-ring, --focus-shadow
```

⛔ **Không được dựng bộ token thứ hai.** Nền này đủ dùng; vấn đề là 316 màu cứng
đi vòng qua nó, không phải token thiếu.

⚠️ Nhưng có **hai thế hệ token sống song song** — đây là nợ thật:

- cũ: `--err/--err-bg/--err-line`, `--ok/…`, `--warn/…`
- mới: `--status-danger/-soft/-border`, `--status-success/…`
- riêng app: `--up-*` (upscalevideo), `--tv-accent` (taovideo)

## File input — 25 chỗ, 2 luật CSS

| Nơi | Số |
|---|---|
| Template Jinja (10 app) | **17** |
| React | **8** |
| **Luật CSS `input[type=file]` trong toàn bộ 126 KB** | **2**, cả hai buộc theo trang (`#content-vault`, `.tv-compose`) |

⇒ ~23 trong 25 file input đang render **hoàn toàn native**.

## Panel điều khiển — trùng lặp nguyên văn

Ba app khác nhau, một luật giống hệt từng ký tự:

```css
.th-controls  {max-height:calc(100vh - 130px); overflow:auto}   /* thumbnail   */
.im-controls  {max-height:calc(100vh - 130px); overflow:auto}   /* taoanh      */
.clip-controls{max-height:calc(100vh - 130px); overflow:auto}   /* taoclipngan */
```

`overflow:auto` đặt **cả hai trục**; ý định chỉ là cuộn dọc. Trong `ltt.css`:
**17** lần `overflow:auto` so với **1** lần `overflow-y:auto`; **11** trong số đó đi
kèm giới hạn chiều cao (tức ý định là dọc).

## Dấu vết 4 app đã gỡ: **KHÔNG CÓ**

Đã quét `socialbot · kichban · demo · mediatools` trong `ltt.css`, mọi template
`server/templates` và `apps/`:

```text
socialbot   2 ket qua  -> deu la CHU THICH ghi lai viec go, khong phai ma sot
kichban     0
mediatools  0
demo        0
```

⭐ Đây là kết quả **tốt hơn dự đoán của đề bài**, và đáng nói ra: Q108/Q109 gỡ app
đã dọn sạch cả tầng giao diện, không để lại CSS mồ côi hay nav chết. Không có việc
gì phải làm ở mục DEAD-CODE.
