# Đợt 2 — Báo cáo cuối + đóng băng

**2026-08-27** · nhánh `public-api-v2` · khu `/developers`

## Kết quả: **MVP PASS WITH DEFERRED NON-BLOCKERS**

Nâng cấp giao diện khu API bám ảnh demo, **không bịa dữ liệu, không viết lại,
không dựng hệ thiết kế thứ hai**. Bốn Hành trình Vàng đều đạt.

## Bốn Gate

| Gate | Kết quả |
|---|---|
| A — First Integration (portal → khóa → request an toàn → kết quả rõ) | ✅ overview checklist + cli bậc thang + quickstart |
| B — Understand API (tools → model → quote → docs) | ✅ tools card + pricing 2 cột + docs |
| C — Manage Credentials (project → key → scope/live-test/IP/expiry → rotate/revoke) | ✅ keys: nút tạo đầu trang, tab Live/Test, form gập, danger action rõ |
| D — Debug (request → logs → status/error/id/latency/credit/job) | ✅ logs mã màu + biểu đồ + request_id link |

## Hợp đồng được bảo vệ — không đổi

- **0 dòng thay đổi hành vi**: 32 route (`test_197`), CSRF, bí mật hiện-một-lần
  (`test_191` giữ hình dạng `<code>ltt_sk_…`), lọc theo `user.id`, giá
  server-side, ký webhook, log privacy. (Trang giá giữ `b-err` cho `test_207`.)
- `platform_core` **chỉ thêm** `request_log.daily()` — hàm **chỉ đọc**, có 2 test.
- **`:root` bất biến.** Toàn bộ CSS mới scoped dưới `.khu-dev`/`.dev-topbar` —
  chứng minh máy: 0 selector không scoped ⇒ 14 app khác + khu VPS không bị chạm.
- Điều hướng 3 nhóm, 12 mục trần, đúng một `aria-current="page"` (`test_303`).
- 6 route đã hạ cấp vẫn sống + tìm lại được (`test_300`).

## Bằng chứng

| | |
|---|---|
| QA trình duyệt `dot2_p4` (16 trang × 6 khung 1920→390) | **0 tràn ngang · 0 ô thô · 0 fieldset thô · 0 lỗi console · 0 lỗi mạng** |
| Nội dung @1920 | 1318px |
| Bộ test khu API (14 tệp) | **262 passed · 0 failed** (191·197·199·200·201·202·203·207·208·299·300·301·302·303) |
| `test_299` i18n khu API | PASS · +53 chuỗi EN thêm tay, `.mo` biên dịch |
| `check_silent_except` | PASS (63/63) |
| CSS scoped | 100% (`.khu-dev`/`.dev-topbar`/`@media`) |
| msgid trùng trong `.po` | 0 |

## Đã bám ảnh demo (so ảnh chủ sản phẩm)

Vỏ (thương hiệu sidebar + thanh trên trạng thái + chuông) · carbon trung tính +
accent cyan · 4 thẻ chỉ số có biểu tượng · **biểu đồ Request/Credit 7 & 30 ngày
(SVG server-side, không JS)** · lưới 2 cột · tab gạch chân · bậc thang 4 bước ·
ước tính giá hổ phách + VND · thẻ chỉ số webhook · bảng mã màu trạng thái.

## Năm thứ KHÔNG làm (đúng freeze, không bịa)

Badge Stable/Beta/Alpha (ToolSpec không có trường đó) · bảng bóc giá theo dòng
(`Simulation` trả một số) · menu ẩn hành động nguy hiểm · thẻ user trùng header ·
H1 tô đỏ nửa câu (vỡ khi dịch). Xem `00_FREEZE.md`.

## HOÃN — non-blocker, KHÔNG do mã của đợt này

1. **`python tools/gate.py` đầy đủ trên cây ĐỨNG YÊN.** Không chạy được lúc này
   vì phiên VPS (`lttstudiosapp-d6`) đang ghi song song → sẽ dính "CÂY ĐÃ ĐỔI
   TRONG LÚC CHẠY" (Bẫy 15) và `check_dich_thieu` đỏ 6 chuỗi VPS đang dở của họ.
   ⇒ Người commit sau cùng chạy gate trên cây quiet trước deploy.
2. **Nâng phụ đề/panel cho 9 trang phụ** (docs/settings/privacy/projects/jobs/
   notifications/quickstart/playground/tool_detail/log_detail) — đã đẹp nhờ vỏ
   Đợt 1 và qua QA, chỉ là đồng bộ tuyệt đối. Không phục vụ Golden Outcome nào.

## Việc của chủ sản phẩm trước deploy

1. Chạy `tools\gate.py` trên cây đứng yên (không phiên nào khác ghi).
2. Sinh lại tệp dẫn xuất (`tools/gui/ltt.css`, `ho_so_he_thong.txt`) — người
   commit sau cùng, một commit riêng (giao ước với phiên VPS).
3. Soi trên `https://app.lttstudios.com` (không chỉ loopback — luật 5b).
4. Soi 4 trang tắt-bằng-cờ nếu `_kieu_chung.html` từng đổi (đợt này KHÔNG đổi nó).
