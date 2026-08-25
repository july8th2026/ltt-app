# 09 — GIAO DIỆN / TRẢI NGHIỆM / HỆ THIẾT KẾ

**Ngày:** 2026-08-26 · **Bằng chứng E3 lấy trên `https://app.lttstudios.com`** *(URL công khai, không phải loopback)*

---

## 1. Bằng chứng E3 — trang vào (điểm bắt đầu GJ-1)

Đo thật qua Cloudflare, không qua `127.0.0.1`:

| Phép đo | Desktop 1280 | Mobile 375 |
|---|---|---|
| Lỗi console | **0** | — |
| Tràn ngang | **không** (1265 ≤ 1280) | **không** (375 = 375) |
| Phần tử vượt biên | — | **0** |
| Cache-bust CSS | ✅ `ltt.css?v=828a9c98` | |

⭐ **Đo trên URL công khai là bắt buộc, không phải cẩn thận thừa.** Loopback bỏ
qua Cloudflare (cache, CSP biên, minify). Đã dính một lần: sửa `ltt.css`, origin
đúng, CF vẫn phục vụ bản cũ 4 giờ ⇒ chip hiện thành radio thô với khách thật
trong khi mọi phép kiểm nội bộ đều xanh.

## 2. Danh mục công khai — đối chiếu nguồn ↔ thứ khách thật thấy

9 thẻ: `taoanh` · `autosubvideo` · `taoclipngan` · `taovideo` · `upscalevideo` ·
`agent` · `prompt-ai-ommi` · `chataistudio` · `nexus`.

Khớp **chính xác** với phép đo nguồn (8 app + `nexus` bật bằng `LTT_NEXUS=1` trên
production, tắt ở env local). `visible_on_surface()` đang làm đúng một nguồn chân
lý.

⭐ **Và bốn app đã gỡ KHÔNG hiện trong catalog**, dù mã của chúng vẫn nằm trên
production (`ec6a00c`). ⇒ Residue của Q108/Q109 nằm ở **tầng route**, không ở
mặt tiền khách hàng. Đó là một sự phân biệt quan trọng mà chỉ E3 mới cho được:
suy từ mã sẽ nói "19 app còn đó", suy từ khách sẽ nói "9 sản phẩm" — cả hai đúng,
và câu thứ hai mới là câu khách sống trong đó.

---

## 3. Vấn đề trung thực của giao diện

### U-01 · P2 — thẩm quyền thiết kế bị pha loãng ở tầng template

| Đo trên 81 template | |
|---|---|
| Dùng thuộc tính `style="..."` nội tuyến | **57** |
| Có khối `<style>` riêng | **11** |
| Hệ thiết kế tập trung | **788 dòng** (`ltt.css`) |
| `page_mode` khai rõ | 15 (8 `wide`, 6 `immersive`, 1 `standard`) |
| `.page--catalog` | **định nghĩa trong CSS, 0 template dùng** |

⚠️ **Chưa nâng lên P1, và có lý do.** Câu hỏi đúng của Prompt 09 không phải "bao
nhiêu style nội tuyến" mà là *"cùng một nút bấm có trông khác nhau giữa hai trang
MVP không?"*. Trang vào đo được **0 lỗi, 0 tràn** — nghĩa là style nội tuyến hiện
đang **không** gây trôi dạt nhìn thấy được. Nó là **nợ**, không phải **lỗi**.

⇒ Việc đúng ở Lane 14: dọn style nội tuyến **sau khi** bản thay thế đã chứng minh,
không phải trước. Và `.page--catalog` mồ côi thì xoá — kèm cache-bust.

### R-01 · P2 — Canvas còn một affordance chết

`frontend/agent-canvas/src/CanvasShell.tsx:333` tra `asset.images` /
`asset.${kind}`. Bốn tool `asset.*` đã đi cùng `mediatools` (Q109).

Dòng 334 xử **đúng**:
```ts
if(!assetTool){setRunError(`Canvas chưa có node đầu vào ${uploaded.kind}.`);return}
```

Không sập, thông báo trung thực. **Nhưng affordance vẫn còn**: khách kéo tệp vào
một node và **luôn** nhận lỗi. Đó là ngõ cụt **có biển báo**, không phải ngõ đã
đóng.

`CLAUDE.md` ghi cái giá này đã được đo và chấp nhận (4–7/10 workflow mất node).
Cái **chưa** được quyết: giữ ngõ cụt có biển, hay bỏ hẳn ô kéo-thả?

⇒ Chốt với `02_...md` §4: `agent` đề xuất **DEFER_POST_MVP**. Một sản phẩm mất
đường đưa dữ liệu vào không phải sản phẩm MVP — và câu đó đúng bất kể ta chọn
giữ hay bỏ ô kéo-thả.

### ~~U-02~~ · ✅ đóng `db6147e` — link 404 trong header

`/ltt-llm` từng hiện trong nav của **mọi khách đã đăng nhập** và trả **404**. Vi
phạm INV-7 (giao diện nói thật) ở dạng nặng nhất: không phải hiển thị sai trạng
thái, mà là **mời khách đi vào hư không**.

---

## 4. Hợp đồng giao diện MVP — đề xuất

1. **Một nguồn chân lý cho hiện/ẩn**: `visible_on_surface()`. Đang đúng, giữ.
2. **Bốn kiểu trang**: `standard` (mặc định) · `wide` · `immersive` · ~~`catalog`~~ (mồ côi, xoá).
3. **Ngữ pháp trạng thái cho tool trả phí**:
   `EMPTY → INPUT → VALIDATE → QUOTE → CONFIRM → QUEUED/RUNNING → RESULT/HISTORY`
   ⛔ Không ép cho tool khác bản chất (chat streaming không có QUOTE tách rời).
4. **Mọi asset tĩnh đổi = URL đổi.** `?v={{ asset_ver }}`. Thêm asset mới hoặc
   dựng HTML bằng chuỗi (`server/admin.py`) thì **cũng phải** đính version.
5. **Không CTA cho năng lực không tồn tại** — R-01 là ca mẫu.

---

## 5. Còn nợ bằng chứng

| Trang | E3 |
|---|---|
| `/` catalog ẩn danh | ✅ desktop + mobile |
| `/register` → `/login` | ❌ |
| Một tool trả phí đi hết chuỗi | ❌ |
| `/nap` (nạp credit) | ❌ |
| Trạng thái lỗi/phục hồi | ❌ |

⚠️ **Bằng chứng E3 phải lấy lại SAU deploy.** Production hiện chạy `ec6a00c` —
mọi thay đổi của đợt này (`a5274bf`, `db6147e`, `3d804ee`) **chưa có ở đó**. Cụ
thể: link 404 `/ltt-llm` **vẫn còn trên production** cho tới lần deploy kế tiếp.

```text
NO_RUNTIME_CHANGE: NO
```
