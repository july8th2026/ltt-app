# CHECKPOINT — Mobile Pack V1

Tệp này là **thứ duy nhất** prompt `09_RECOVERY_AFTER_COMPACTION.txt` cần đọc để
nối lại việc sau khi context bị nén. Cập nhật cuối mỗi phase, không cuối mỗi lệnh.

## Bối cảnh phiên

| | |
|---|---|
| cây | `D:\LTTSTUDIOSAPP\.claude\worktrees\mobile-v1` |
| nhánh | `phien/mobile-v1`, fork từ `admin-mvp-v3` @ `911cd142` |
| nguồn quy trình | `G:\My Drive\AI\A LTT AII\LTT_MOBILE_AUTONOMOUS_PROMPT_PACK_V1` |
| kế hoạch | `docs/MOBILE/00_KE_HOACH.md` |
| dải số test | **700–799** |
| máy chủ đo | `python tools\studio_dev.py --cong 8123` |
| trình duyệt | Playwright Chromium + WebKit 26.5 (`playwright-cli`) |

⚠️ Cổng **8100 là production đang chạy thật** (`C:\LTTPlatform`). Không đo trên đó,
không dừng nó. Ma trận tự động luôn chạy ở **8123**.

⚠️ Phiên `LTT Voice autonomous deep audit` làm việc ở cây chính `D:\LTTSTUDIOSAPP`.
Đã báo họ ngày 05/09 rằng Phase C sẽ sửa `apps/ltt_voice/routes/_p_audio.py`.

---

## Trạng thái phase

| phase | trạng thái | bằng chứng |
|---|---|---|
| **A** — kiểm kê + baseline | ✅ **PASS** | `01_MATRIX.md`, `02_BASELINE.md`, `03_BACKLOG.md`, `anh/` |
| B — hợp đồng shared | ⬜ chưa bắt đầu | |
| C — shared media + Voice/Chat P0 | ⬜ | |
| D — media generator | ⬜ | |
| E — editor phức tạp | ⬜ | |
| F — bề mặt chuẩn | ⬜ | |
| G — harness + ma trận | ⬜ | |
| H — cổng phát hành cuối | ⬜ | |

## Gate A — đối chiếu từng điều kiện của pack

| điều kiện | kết quả |
|---|---|
| 100% route khách hàng có dòng trong matrix hoặc lý do loại trừ | ✅ 16/16 app + 7 route chrome; 5 app loại trừ có HTTP 404 làm bằng |
| Có baseline evidence | ✅ 190 ô đo, 2 trình duyệt, 4 ảnh |
| Có matrix P0/P1/P2 | ✅ `03_BACKLOG.md` — 2 P0, 6 P1, 3 P2 |
| Không còn câu "có lẽ app X…" chưa xác minh | ✅ mục "Chưa đo" liệt kê thẳng 6 thứ chưa đo |

## Lệnh test đã chạy

| lệnh | thời điểm | kết quả |
|---|---|---|
| `python tools\gate.py --vong-lap` | 05/09 15:28 | **FAIL (1/21)** — 20 kiểm tĩnh PASS, chỉ `bộ test --lf` đỏ |
| `python tools\gate.py --vong-lap` | 05/09 15:31 | **PASS (21/21)** |

⚠️ **Đừng đọc lượt đầu như một lỗi mã.** Cây worktree mới có cache `--lf` **rỗng**;
đó là trạng thái thứ ba mô tả trong `docs/BAY_TRONG_CONG_CHAT_LUONG.md`. Lượt hai
chạy `--lf` trong **0,1 giây** — và một lượt 0,1 giây cũng **không** phải bằng
chứng, chính dòng `RESULT` của gate nói vậy. Phase A không sửa dòng mã sản phẩm
nào, nên tín hiệu có ý nghĩa ở đây là **20 phép kiểm tĩnh xanh**, không phải `--lf`.
Bằng chứng thật là `python tools\gate.py` đầy đủ ở Phase H.

## P0/P1 còn mở

Toàn bộ: P0-1, P0-2 · P1-1…P1-6 · P2-1…P2-3. Xem `03_BACKLOG.md`.

## Việc tiếp theo

Phase B: chốt Shared vs App-owned cho 7 capability, viết `04_SHARED_CONTRACT.md`.
Bốn quyết định đã có bằng chứng đủ để chốt ngay:
media transport (7 consumer) · safe-area (4) · viewport-fit (toàn nền tảng) ·
luật `pointer:coarse` thiếu `a` (toàn nền tảng).
