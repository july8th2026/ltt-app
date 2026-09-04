# Phase 07 — Dữ liệu (bảng riêng dạng cây) + sự kiện canonical + reload từ CSDL

## Source
- worktree/branch: như Phase 02 · base: `bdddeae`
- canonical rules read: kế hoạch §4 D4/D6, §5.2/§5.3; AGENTS §8.1 (`tables.py` + `table_prefix`); Q75 (retention); báo cáo Phase 01 §1–§5 + AC-01/02/03/05/06/07/08/09 và ba việc §15

## Evidence — chấm ba phương án dữ liệu (chốt D4)

| | A — sửa `chat_*` (Chat AI Studio) | B — bảng generic thêm cột | **C — bảng riêng `chatltt_*`** |
|---|---|---|---|
| Không phá Chat AI Studio | ✗ bảng đang phục vụ khách, gắn `codex_thread_id`, tuyến tính | ~ | ✓ không chạm |
| Cây + khối typed | ✗ phải thêm `parent_id`, `blocks`, đổi nghĩa `content` | ~ | ✓ thiết kế từ đầu |
| Đúng hợp đồng app (§8.1) | ✗ bảng ở `platform_core/models.py` | ✗ | ✓ `apps/chatltt/tables.py` + `table_prefix` |
| Migration/rollback độc lập | ✗ | ~ | ✓ `7d2c1e9f4a03` lên/xuống sạch |
| **Chọn** | | | **C** |

| Finding | Source/test | Result |
|---|---|---|
| Ba bảng `chatltt_conversation/message/execution`, `load_app_tables` nạp, Alembic **một head** `7d2c1e9f4a03` ← `c7b91e4a2f80`; upgrade tạo đủ, downgrade -1 xoá đúng ba bảng + index | `apps/chatltt/tables.py`, `alembic/versions/20260903_1000_chatltt_cay_hoi_thoai.py`, `test_616` | pass |
| Cây bằng `parent_id`; **sửa-gửi-lại = anh em mới, không xoá con**; **tạo-lại = assistant anh em**; `current_leaf_id` lưu CSDL, `chon_la` đổi nhánh và `duong_toi_la` theo đúng nhánh (AC-05/06/07) | `services/hoi_thoai.py`, `test_617` | pass |
| **Bất biến tầng ghi** `created_at(con) > created_at(cha)` kể cả đồng hồ lùi (việc §15.2 của Phase 01) | `them_thong_diep`, `test_617::test_con_luon_tre_hon_cha…` | pass |
| `dung_cay` dựng đúng từ danh sách **xáo trộn**, hai lượt, cha vắng ⇒ lên gốc (AC-01, đặc tả `convoStructure.spec.ts`) | `test_617::test_dung_cay_tu_danh_sach_xao_tron`, `test_cha_vang_mat…` | pass |
| Sở hữu: người khác đọc/ghi/chọn lá/xoá đều **cùng một** `KhongTimThay`; cha thuộc hội thoại khác không nối được | `test_617::test_nguoi_khac…` | pass |
| Tìm theo tiêu đề **hoặc** nội dung khối; lưu trữ; **xoá mềm** huỷ lượt đang chảy (`cancelled`) | `test_617::test_tim_kiem…` | pass |
| Sự kiện canonical 14 loại; `ap_dung` thuần, `seq` đơn điệu; **một `status`** cho message lẫn execution (việc §15.3: LibreChat có hai quy ước) | `services/su_kien.py`, `test_618` | pass |
| Kết cục: xong (`finish_reason`), thất bại (`error` block), huỷ (`status:cancelled`), **bị cắt** (`status:length`) | `test_618::test_that_bai_huy_va_bi_cat` | pass |
| **Reload giữa chừng**: `su_that()` trả `partial_text`/`seq` từ execution — trình duyệt không giữ gì (AC-02/08/09) | `test_618::test_su_that_giua_chung…` | pass |
| Sự kiện của facade `mo_luong` áp **nguyên xi** lên execution với luồng giả; tiền giữ/thu/hoàn khớp số dư | `test_618::test_su_kien_cua_facade_ap_nguyen_xi` | pass |
| Loại sự kiện lạ ⇒ ném; nhịp ghi 1 s / 200 ký tự / kết thúc; `snapshot` = `resumeState` | `test_618::test_su_kien_la…` | pass |

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| Dữ liệu | A / B / C | **C** | bảng trên | có |
| Lá đang xem | trình duyệt (LibreChat) · **CSDL** | CSDL | reload giữa nhánh cũ phải về đúng nhánh (AC-07) mà không cần suy từ id phản hồi | có |
| Partial khi stream | RAM/Redis · **`chatltt_execution.partial_text` theo nhịp** | CSDL | D6; `parallel=1` không cần pub/sub; đóng mọi tab vẫn còn chữ (AC-09) | có |
| Xoá | cứng · **mềm + retention Q75** | mềm | sổ tiền đối chiếu được; dọn thật là việc bảo trì | có |
| Tìm kiếm | full-text · **ILIKE trên title + cast(blocks)** | ILIKE | đủ V1; PostgreSQL FTS là việc sau khi có số đo | có |
| Khối `tool_call.delta` | ghi · **chỉ tăng seq** | không ghi | V1 không có tool trong chat (MVP scope) | có |

## Changes
- **Mới** `apps/chatltt/tables.py`, `alembic/versions/20260903_1000_chatltt_cay_hoi_thoai.py`, `apps/chatltt/services/hoi_thoai.py`, `apps/chatltt/services/su_kien.py`.
- Tests: `test_616` (3), `test_617` (7), `test_618` (5).

## Tests
| Command | Result |
|---|---|
| `pytest test_616 test_617 test_618 -n 0` | **16 passed** |

## Failures found and repaired
- Không có lỗi ở phase này ngoài hai vòng sửa test nhỏ.

## External unknown/blocker
- Không. Migration chạy trên SQLite tạm; trên PostgreSQL production là việc deploy của chủ sản phẩm (`update.ps1` chạy `alembic upgrade head`).

## Giao cho phase sau
- Phase 08: route SSE chạy `mo_luong` trong thread + hàng đợi để gửi `: ping` khi chờ máy B; commit partial theo `nen_ghi`; `su_that()` cho reload; endpoint `after=seq` để nối lại.
- Phase 12: retention purge cho `deleted_at` (Q75 365 ngày) + orphan artifact.

## Verdict
**PASS**

## Next
Autocontinue to phase: **08** (ChatLTT chỉ-text dùng được) sau khi gộp Phase 04/05 và commit.
