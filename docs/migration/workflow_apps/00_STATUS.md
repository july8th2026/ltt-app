# 00_STATUS — bảng điều phối chương trình 4 bot → 4 App

> ⛔ **Đây là bảng điều phối, không phải nguồn chân lý.** Nguồn chân lý là mã
> nguồn và `docs/00_LTT_OPERATING_CONTRACT.md`. Một bảng chép tay không có cách
> nào tự biết nó đã cũ — cơ chế đó đã nói sai năm lần trong kho này.

Cập nhật lần cuối: **2026-09-09 18:20**.
Nguồn: `docs/migration/workflow_apps/01_SOURCE_MANIFEST.md`.

| Phase | Trạng thái | Bằng chứng | Chặn | Kế |
|---|---|---|---|---|
| 00 FAST BUILD governance | **XONG** | hợp đồng §4.10 · `tools/ho_so_cay.py` · `gate.py --tu` · `tests/test_1100` · `FAST_BUILD_WORKTREE_DESIGN.md` · `WORKTREE_ADOPTION_MATRIX.md` · `FAST_BUILD_OPERATOR_GUIDE.md` | — | — |
| 01 LTT runtime baseline | **XONG** | `02_LTT_RUNTIME_BASELINE.md` · vá R1 `foreach.py` + `tests/test_1101` | — | — |
| 02 Audit Transcript | **XONG** | `03_AUDIT_BOT_TRANSCRIPT.md` | S11·S12 | — |
| 03 Audit Pause | **XONG** | `04_AUDIT_BOT_PAUSE.md` | S11·S13 | — |
| 04 Audit GEM | **XONG** | `05_AUDIT_BOT_GEM.md` + `09_QUYET_DINH_GEM_BO_TRINH_DUYET.md` | — | — |
| 05 Audit Video Assembly | **XONG** | `06_AUDIT_BOT_DUNGVIDEO.md` | S10·S11·S14 | — |
| 06 Cross-bot synthesis | **XONG** | `07_CROSS_BOT_SYNTHESIS.md` | — | — |
| 07 App contracts + Workflow UX | **XONG** | `23_APP_BOUNDARIES.md` · `24_NODE_CONTRACTS.md` · `26_WORKFLOW_UX.md` | — | 08 |
| 08 Build Transcript | **KẾ TIẾP** | | service STT dùng chung (changeset riêng) | |
| 09 Build Pause | CHƯA | | | |
| 10 Build GEM | CHƯA | | — (đã gỡ chặn; viết lại theo `09`) | |
| 11 Build Video Assembly | CHƯA | | S10 | |
| 12 Legacy workflow rebuild | CHƯA | | | |
| 13 Workflow hardening | CHƯA | | | |
| 14 Agent re-evaluation | CHƯA | | | |
| 15 Final cutover | CHƯA | | | |

## Bốn quyết định của chủ dự án — 2026-09-09

| | Quyết định |
|---|---|
| S2 | `gem` **bỏ hẳn lái trình duyệt**, chỉ gọi qua `runtime_noi_bo` — `09_...` |
| S1 | nhánh nguồn chân lý của `bot_gem` là **`master`** |
| S9 | giữ **thứ tự của pack**: `transcript` trước |
| S8 | cấu hình thật đọc từ `D:\FULL AUTO VIDEO` (chỉ-đọc) — `08_...` |

⚠️ S2 thay provider giữa lúc migrate. Tôi đã nêu, chủ dự án đã quyết. Hệ quả ghi
ở `09` §1: `gem` **không còn đo được parity** — chuẩn nghiệm thu của nó là **hợp
đồng đầu ra**, không phải so với legacy.

## Nợ mở — bảng đầy đủ ở `07_CROSS_BOT_SYNTHESIS.md` §5

`S1`–`S9` đã đóng hết. Năm nợ **mới** sinh ra từ việc đọc cấu hình thật:
`S10` (`mood.py` không có trong kho git) · `S11` (sửa parity theo `08` §1) ·
`S12` · `S13` · `S14`.

## Hồ sơ vận hành của cây này

`FAST_BUILD` từ sau khi Phase 00 đóng — luật ở hợp đồng §4.10, trạng thái hỏi
bằng `python tools\ho_so_cay.py trang-thai`.

Phase 00 **tự nó** chạy theo `NORMAL`: một prompt không có quyền nới cadence
trước khi hợp đồng canonical được sửa. Đó là chi phí một lần để không tồn tại
hai nguồn luật cùng lúc.

## Chuẩn nghiệm thu đã đóng băng

- Hành vi **P0/P1: giữ 100%**, trừ khi người dùng duyệt cho khai tử một mục cụ thể.
- Parity người dùng nhìn thấy, có trọng số: **≥95%**.
- Không đòi bằng nhau từng byte cho đầu ra LLM — dùng phép đo cấu trúc/ngữ nghĩa
  được đóng băng trong chính bản audit của bot đó.
