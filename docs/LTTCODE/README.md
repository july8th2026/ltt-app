# LTTCODE — tài liệu đã chuyển sang kho LTTCODEAPP

Nguồn chân lý duy nhất của sản phẩm LTTCODE (ứng dụng desktop Tauri + DeepSeek Harness)
là kho **LTTCODEAPP** (`D:\LTTCODEAPP`, GitHub `giaitritruyenthongltt-spec/LTTCODEAPP`):

| Cần gì | Ở đâu (trong LTTCODEAPP) |
|---|---|
| Kế hoạch tổng | `docs/LTTCODE/MASTER_IMPLEMENTATION_PLAN.md` |
| Tiến độ đếm theo việc | `docs/LTTCODE/DANH_MUC_CONG_VIEC.md` |
| Trạng thái + nhãn bằng chứng | `docs/LTTCODE/STATE.md` |
| Quyết định D01–D19, kiến trúc, baseline | `docs/LTTCODE/research/` |
| ADR | `docs/LTTCODE/adr/` |
| Bản cũ từng nằm ở đây | `docs/LTTCODE/_superseded/lttstudiosapp-docs-2026-09-16/` |

Phần của LTTCODE **nằm trong kho này** chỉ có:

- `apps/lttcode/` — trang tải + kênh cập nhật (`/lttcode`, `/lttcode/update/...`,
  `/lttcode/dl/...`). Thiết kế: LTTCODEAPP `docs/LTTCODE/specs/2026-09-16-updater-kenh-phat-hanh-design.md`.
- Dữ liệu vận hành trên máy chủ: `data/lttcode_releases.json`, `data/lttcode_dist/`
  (do `tools/release.ps1` của LTTCODEAPP ghi; không commit).

Không thêm tài liệu kế hoạch LTTCODE vào thư mục này — hai nơi khai cùng một điều thì
sớm muộn sẽ lệch nhau (lý do R0.9).