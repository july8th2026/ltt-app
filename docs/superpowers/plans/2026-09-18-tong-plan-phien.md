# Tổng plan phiên 17–18/09/2026 — LTT LLM + LTTCODE (bảng theo dõi tiến độ duy nhất)

> Đây là **một** chỗ để xem tiến độ cả phiên. Plan con giữ chi tiết từng bước; bảng này chỉ giữ trạng thái, bằng chứng (SHA/tệp) và thứ tự. Cập nhật bảng này mỗi khi một hạng mục đổi trạng thái — không ghi % ở chỗ khác.
>
> Ký hiệu: ✅ xong (có bằng chứng) · 🔵 đang chạy · ⬜ chưa làm · ⏸ chờ quyết định · ⛔ chặn ngoài phiên · ✖ bỏ (có lý do)

**Plan con (nguồn chi tiết):**
- LLM v2: `docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md` (bản 2, `88a7910f`)
- Phương án C: `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md`
- LTTCODE: `D:\LTTCODEAPP\docs\LTTCODE\plans\2026-09-17-ke-hoach-tong-phien.md`, `…\2026-09-17-truoc-build-0.1.5.md`, `…\KIEM_CUOI.md` §10

**Production lúc cập nhật bảng (18/09 ~10:30):** máy A chạy `2b3977ad` (`main` = `88a7910f`, khác production chỉ ở tài liệu); máy B cổng Phương án C bước 3 + engine theo nhánh `phien/cache-24g` (**chưa gộp**); LTTCODE 0.1.7 dev 100 %, stable 100 %.

---

## Tiến độ tổng

| Khối | % | Còn lại |
|---|---|---|
| A — Nền tảng LTT LLM (Phương án C) | **100 %** | — |
| B — LTTCODE build + E2E + phát hành | **95 %** | Đăng nhập/đăng xuất trong app (P04 #8 phần giao diện) |
| C — Tối ưu máy B | **85 %** | Gộp cache 24G (Task 1 của LLM v2) |
| E — LLM v2 (làm lại trên Phương án C) | **15 %** | Task 2–13 |
| D — Tổng kết phiên | **0 %** | L3, gộp, push, nhật ký |
| **Cả phiên** | **~70 %** | |

---

## A — Nền tảng LTT LLM (Phương án C)

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| A1 | Đo máy B, khôi phục, ComfyUI Manual | ✅ | `KET_QUA_DO_17_09.md` (nhánh `phien/bench-may-b`, **chưa gộp** → D2) |
| A2 | Chốt tham số: ngân sách `-c − 8.192`, whale 8.192/16.384, LTTCODE `max_tokens` 24.000 | ✅ | DECISION_LOG L-23 |
| A3 | Code bước 1–3 (A xếp lại khi B 429, hồ sơ số một chỗ, B rào vật lý) | ✅ | `dd6f5d55`, `9d48358d` |
| A4 | Gộp + L1 | ✅ | `575798a7` |
| A5 | Deploy B (cổng) → deploy A | ✅ | B 23:03, A 23:29 17/09 |
| A6 | Nghiệm thu production §5.1 | ✅ 7/7 | `NGHIEM_THU_PHUONG_AN_C_17_09.md` (`543e0d50`, `2549161b`) |
| A7 | Sửa cờ whale xoá ở nhịp tim | ✅ | `f54d22db`, deploy `26ed94e5` |
| A8 | Sửa suất `sync` mồ côi khoá 3090 20 phút | ✅ | `a6999888` deploy 04:17 |
| A9 | Dọn cơ chế cũ (13 tên/env, env dịch vụ A/B) | ✅ | rà 18/09: code/env sạch, còn tàn dư tài liệu → E Task 11 |
| A10 | Sửa phát bản LTTCODE lùi về bản đủ điều kiện | ✅ | `2b3977ad` deploy 08:35 |

## B — LTTCODE

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| B1 | Nhóm trước build G1a–G9 + chặn đọc thư mục nhạy cảm | ✅ | LTTCODEAPP `146d479`…`e17a583`, `be278a8` |
| B2 | Build 0.1.5 dev | ✅ | `ccc218f` |
| B3 | Tự cập nhật + sao lưu phiên D17 | ✅ | E2E_0.1.5_gui |
| B4 | Gate bản cài | ✅ 63/0/4 | `7c38e75`, 0.1.7: `fad4a6a` |
| B5 | E2E giao diện (ảnh, code, MCP, skill, terminal, lịch hẹn, hooks, song song, chặn đọc) | ✅ | `E2E_0.1.5_gui.md`, hooks 6/6 `76903c3` |
| B5b | Memory bật mặc định + nhớ qua phiên với model thật | ✅ | `f922386`; `MEM-7Q3K` 18/09 08:29 |
| B6 | Phiên dài ~150k | ✅ (trừ cache qua khởi động lại dịch vụ) | nén 157.144→67.866; cache mất khi restart — đúng thiết kế (`KET_QUA_BAO_TRI_18_09`) |
| B7 | Chấm điểm | ✅ 99/131 | `d9f7c95` |
| B8 | 0.1.6 (hỏng 431 cookie) → 0.1.7 sửa + cổng chặn mới | ✅ | `4ba3ccb`, `2e2a91d`, 0.1.6 rollout 0 |
| B9 | 0.1.7 stable 100 % + trang tải | ✅ | `d9f7c95`; rollout 100 lúc 10:2x 18/09 |
| B10 | CI 4/4 xanh | ✅ | `8681126` |
| B11 | Đăng nhập thật phía máy chủ | ✅ 40/40 | `2e2a06f` |
| B12 | Đăng nhập/đăng xuất **trong app** | ⏸ | cần đăng xuất máy chủ dự án — chủ dự án quyết thời điểm |
| B13 | Chọn mức suy nghĩ theo model trong app (0.1.8) | ⬜ | = E Task 13 |
| B14 | Chứng chỉ EV, máy ảo sạch | ⛔ | ngoài phiên |

## C — Tối ưu máy B

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| C1 | Đo cache prompt hai model (99,6 %) | ✅ | `990ce48a` |
| C2 | Bảo trì: `--ctx-checkpoints 8`, `-b 512` (3.8), `-watch-config` | ✅ | `dac815c5` |
| C3 | Cache 24 GB/model + sàn RAM 24 GB (theo chủ dự án) | 🔵 | nhánh `phien/cache-24g` — **B đang chạy, main chưa có** |
| C4 | Nâng số job song song | ⬜ | sau C3, cần đo lại |

## E — LLM v2 (plan `2026-09-18-ltt-llm-v2-…`, bản 2)

| Task | Hạng mục | Trạng thái | Ghi chú |
|---|---|---|---|
| 0 | Dọn phiên "Serving v2", tag giữ commit, xoá phiên | ✅ | `4074dc02`, tag `luu-tru/serving-v2/*` |
| 1 | Gộp cấu hình B đang chạy vào `main` (hết DRIFT) | 🔵 chờ C3 | chặn mọi deploy B khác |
| 2 | Lỗi tính tiền `/messages` khi trúng cache (R-04) | 🔵 | nhánh `phien/llm-r04` |
| 3 | Catalog mức suy nghĩ theo model | 🔵 | nhánh `phien/suy-nghi-theo-model` |
| 4 | Suy nghĩ do máy chủ quyết, gỡ ghi đè 3 cửa, sàn `max_tokens` 3.5 | 🔵 | cùng nhánh Task 3 — chủ dự án đã duyệt hướng |
| 5 | 3.8 khai đọc ảnh; test bản sao `-c` | 🔵 | nhánh `phien/providers-vision` |
| 6 | B gia hạn suất theo tiến triển (bỏ thu cứng 1.200 s) | ⬜ | sau Task 1 |
| 7 | Ước token cận trên (code ×0,74, emoji ×0,16) + overhead template | ⬜ | sau Task 1; deploy theo chiều |
| 8 | 413 trước 200 đúng câu từng giao thức | ⬜ | sau Task 4 |
| 9 | Tách ngưỡng nén Claude Code/Codex; bộ cài cập nhật khoá LTT | 🔵 | nhánh `phien/nen-claude-codex` |
| 10 | Công cụ kiểm định kỳ (canary cô lập, MTP, `/slots`, bộ chấm A/B) | ⬜ | sau Task 1, giờ vắng |
| 11 | Dọn bản sao gõ tay + tài liệu sai | ⬜ | rải theo task |
| 12 | Chất lượng 3.5: áp thông số lấy mẫu theo model card + A/B | ⬜ | sau Task 4, 10 |
| 13 | LTTCODE chọn mức suy nghĩ theo model (0.1.8) | ⬜ | sau Task 3 |
| — | R-06, 07, 10, 11, 14, 16, 17, 18, 23 của phiên cũ | ⬜ | xác minh từng mục trên tag lưu trữ |

## D — Tổng kết phiên

| # | Hạng mục | Trạng thái |
|---|---|---|
| D1 | Gộp nhánh còn treo: `phien/bench-may-b` (6), `phien/lttcode-skills` (1), `phien/lttcode-updater` (1), các nhánh E | ⬜ |
| D2 | **L3 một lần** trên `main` cuối (sau khi hết pha) → khép nếu đỏ | ⬜ |
| D3 | Deploy nếu có thay đổi sau L1/L2 cuối | ⬜ |
| D4 | Push `origin` cả hai kho | ⬜ |
| D5 | NHAT_KY, memory, xoá luật tạm SSH máy B trong `.claude/settings.local.json` | ⬜ |
| D6 | Dọn worktree tạm của phiên (`-r04`, `-suy-nghi`, `-vision`, `-nen-claude`, `-cache-24`, `-bao-tri-b`, `-phat-hanh`, `-faq-hooks`, `-suat-mo-coi`, `-lttcode-faq`, `-llm-hang-cho`, `-llm-gateway-vatly`, `-bench-b`…) sau khi gộp | ⬜ |

---

## Sự cố trong phiên (đã xử lý)

| Giờ | Sự cố | Xử lý |
|---|---|---|
| 17/09 23:34 | Hai job lớn prefill chồng (cờ whale xoá ở nhịp tim) | `f54d22db` |
| 18/09 ~06:xx | Cache 24 GB làm RAM trống < 48 GB ⇒ B từ chối mọi LLM ~10 phút (không khách bị ảnh hưởng) | hạ 12 GB, rồi chủ dự án yêu cầu 24 GB + sàn 24 GB (C3) |
| 18/09 07:1x | LTTCODE 0.1.6 "Failed to load plugins" (431 do cookie tích tụ) | rollout 0, xoá cookie, 0.1.7 sửa gốc + cổng chặn |
| 18/09 | Hộp cập nhật mở khuất sau cửa sổ chính | `2e2a91d` |
| 18/09 | Suất `sync` mồ côi khoá 3090 20 phút | `a6999888` |

## Chờ chủ dự án

1. Thời điểm đăng xuất app để kiểm đăng nhập/đăng xuất trong giao diện (B12).
2. Kết quả C3 (cache 24G + sàn 24G) trước khi gộp — agent đang đo.
