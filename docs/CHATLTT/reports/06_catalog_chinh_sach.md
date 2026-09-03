# Phase 06 — Catalog theo chính sách sản phẩm (fail-closed) + sức khoẻ qua hợp đồng

## Source
- worktree/branch: như Phase 02 · base: `bdddeae`
- canonical rules read: kế hoạch §4 D8, §6.1; AGENTS §8.2c (app `surface=customer` phải có trang để đáp xuống); Q92 (ba cổng độc lập); báo cáo Phase 01 §6 (phản đề `visionModels[]` hardcode)

## Evidence

| Finding | Source/runtime/test | Result |
|---|---|---|
| Ba cổng độc lập: `customer_visible` (palette) · `api_exposed`+`LTT_PUBLIC_API_TOOLS` (API) · **allowlist ChatLTT** | `apps/chatltt/services/chinh_sach.py`; `test_613` | tool `api_exposed=True` ngoài allowlist **không hiện**; `customer_visible=False` trong allowlist **vẫn hiện** |
| Fail-closed cho tên lạ và cho **modality lạ** | `chinh_sach.kiem_cho_phep` ném `KhongDuocPhep`; `PHUONG_THUC_HIEN_THI` lọc `video` | `test_613` |
| Catalog suy từ registry, không id nội bộ, không URL máy | `runtime_noi_bo.danh_muc` (mượn `catalog.project_tool`) | `test_613::test_api_danh_muc…` quét body JSON: không `qwen38/hidream/8299/8199/8120/192.168.` |
| **Alias mới chỉ bằng bản khai** | `test_614` — thêm alias thứ ba (experimental, ngữ cảnh 8K) vào fixture ⇒ catalog + enum hợp đồng có nó; cờ `reads_images` đi theo constraints | pass; `apps/chatltt` không có `if` theo tên model (grep chốt) |
| **Sức khoẻ qua hợp đồng** — `AppManifest.suc_khoe: Callable[[], "san_sang"\|"ban"\|"chua_san_sang"]` | `registry.py`; `danh_muc.suc_khoe_cua` (đệm 10 s, ném/giá trị lạ ⇒ `chua_san_sang`) | `test_613::test_suc_khoe_tu_manifest_dem_va_fail_closed` |
| `ltt_voice.suc_khoe` = `sidecar_client.trang_thai()` **ba trạng thái** (không phải `san_sang()` chỉ kiểm env) | `apps/ltt_voice/manifest.py` | khai |
| `ltt_llm.suc_khoe` = `GET /live` cổng máy B (không cần khoá, 1,5 s, không ném) | `apps/ltt_llm/features.py::suc_khoe` | khai |
| `anhnoibo.suc_khoe` | — | **chưa** (Phase 04 đang chạy trên app đó; cổng render có `health()` cần token ⇒ cần đường `/live` không khoá hoặc probe qua provider) → giao Phase 09 |
| App `chatltt` nạp được, có trang đáp xuống, `enabled=False/public=False` (vô hình với khách), `table_prefix="chatltt"` | `apps/chatltt/{manifest,routes}.py`; `lint_app_contract` 16 app / 0 ERROR / 0 WARN; `test_60`, `test_85`, `test_147`, `test_308` xanh | pass |
| Route `/chatltt/api/danh-muc` đòi đăng nhập, `Cache-Control: no-store` | `test_613` | pass |

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| Nơi đặt allowlist | env `LTT_CHATLTT_TOOLS` · **hằng trong `services/chinh_sach.py`** | mã | thay đổi allowlist là quyết định sản phẩm có review, không phải công tắc vận hành (khác `LTT_PUBLIC_API_TOOLS`, vốn là công tắc tắt khẩn) | có |
| Sức khoẻ | catalog tự thăm dò theo tên app · **hook `AppManifest.suc_khoe`** | hook | nền tảng không được biết tên app; app biết dịch vụ của nó ở đâu | có |
| Đệm sức khoẻ | không · **10 s theo slug** | 10 s | một trang vẽ không được thăm dò ba dịch vụ mỗi lần | có |
| Trạng thái `ban` | từ probe · **chỉ từ lượt gọi thật (`DangBan`)** | lượt thật | `/live` không nói bận; đoán bận từ catalog là chip sai chiều ngược | — |

## Changes
- `platform_core/registry.py`: `AppManifest.suc_khoe`.
- `platform_core/runtime_noi_bo/danh_muc.py`: `suc_khoe_cua()` + `san_sang` đọc hook.
- `apps/ltt_voice/manifest.py`, `apps/ltt_llm/{manifest,features}.py`: khai `suc_khoe`.
- **Mới** `apps/chatltt/` (`manifest.py`, `routes.py`, `services/chinh_sach.py`, `templates/chatltt.html`).
- `.po`/`.mo`: 2 chuỗi EN.
- Tests: `test_613` (8), `test_614` (2).

## Tests
| Command | Result |
|---|---|
| `pytest test_613 test_604 test_601 test_60 test_85 test_147 test_308 test_256 -n 0` | 113 passed (sau sửa login fixture) |
| `lint_app_contract` | 16 app · 0 ERROR · 0 WARN |
| `check_silent_except` 62/62 · `check_i18n` 774/774 · `check_dich_thieu` PASS | |

## Failures found and repaired
- Route test: đăng nhập cần `is_verified=True` và trường `username` (khớp form thật).
- `badge="MỚI"` không bọc `N_` làm bánh cóc i18n +1.

## External unknown/blocker
- Không. Probe sức khoẻ thật (máy B `/live`, sidecar voice) chỉ chạy trên máy chủ; test dùng hook giả.

## Giao cho phase sau
- Phase 09: `anhnoibo.suc_khoe` (cần đường thăm dò không khoá của cổng render, hoặc probe qua `providers.get("ltt_image")`).
- Phase 08: `NangLuc.tuy_chon["voice_id"]` là gợi ý; sở hữu vẫn kiểm lúc thi hành.

## Verdict
**PASS**

## Next
Autocontinue to phase: **07** (bảng `chatltt_*` + sự kiện + reload từ CSDL) — sau khi gộp kết quả Phase 04/05 và commit.
