# 00_STATUS — bảng điều phối chương trình 4 bot → 4 App

> ⛔ **Đây là bảng điều phối, không phải nguồn chân lý.** Nguồn chân lý là mã
> nguồn và `docs/00_LTT_OPERATING_CONTRACT.md`. Một bảng chép tay không có cách
> nào tự biết nó đã cũ — cơ chế đó đã nói sai năm lần trong kho này.

Cập nhật lần cuối: **2026-09-09 17:35**.
Nguồn: `docs/migration/workflow_apps/01_SOURCE_MANIFEST.md`.

| Phase | Trạng thái | Bằng chứng | Chặn | Kế |
|---|---|---|---|---|
| 00 FAST BUILD governance | **XONG** | hợp đồng §4.10 · `tools/ho_so_cay.py` · `gate.py --tu` · `tests/test_1100` · `FAST_BUILD_WORKTREE_DESIGN.md` · `WORKTREE_ADOPTION_MATRIX.md` · `FAST_BUILD_OPERATOR_GUIDE.md` | — | — |
| 01 LTT runtime baseline | **XONG** | `02_LTT_RUNTIME_BASELINE.md` · vá R1 `foreach.py` + `tests/test_1101` | — | — |
| 02 Audit Transcript | **XONG** | `03_AUDIT_BOT_TRANSCRIPT.md` | S6 | — |
| 03 Audit Pause | **XONG** | `04_AUDIT_BOT_PAUSE.md` | S5 | — |
| 04 Audit GEM | **XONG** | `05_AUDIT_BOT_GEM.md` | **S1·S2·S3** | — |
| 05 Audit Video Assembly | **XONG** | `06_AUDIT_BOT_DUNGVIDEO.md` | S4 | — |
| 06 Cross-bot synthesis | **XONG** | `07_CROSS_BOT_SYNTHESIS.md` | — | — |
| 07 App contracts + Workflow UX | **XONG** | `23_APP_BOUNDARIES.md` · `24_NODE_CONTRACTS.md` · `26_WORKFLOW_UX.md` | — | 08 |
| 08 Build Transcript | CHƯA | | S6 · service STT dùng chung | |
| 09 Build Pause | CHƯA | | S5 | |
| 10 Build GEM | CHƯA | | **S1·S2·S3 — DỪNG** | |
| 11 Build Video Assembly | CHƯA | | S4 | |
| 12 Legacy workflow rebuild | CHƯA | | | |
| 13 Workflow hardening | CHƯA | | | |
| 14 Agent re-evaluation | CHƯA | | | |
| 15 Final cutover | CHƯA | | | |

## Nợ mở — bảng đầy đủ ở `07_CROSS_BOT_SYNTHESIS.md` §5

`S1`–`S3` cần **chủ dự án** quyết (nhánh · provider · tài khoản của `bot_gem`).
`S4`–`S6` là **UNKNOWN trên đường tới hạn**, phải đóng bằng cách đọc mã **trong**
phase build tương ứng, trước khi viết service.
`S9` — đề xuất đổi thứ tự build (pause trước transcript) — **chờ duyệt**; hiện
vẫn giữ thứ tự của pack.

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
