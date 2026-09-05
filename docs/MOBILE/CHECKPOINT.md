# CHECKPOINT — Mobile Pack V1

Tệp này là **thứ duy nhất** prompt `09_RECOVERY_AFTER_COMPACTION.txt` cần đọc để
nối lại việc. Cập nhật cuối mỗi phase, không cuối mỗi lệnh.

Cập nhật lần cuối: **2026-09-05, sau Phase E (khảo sát) + F.**

## Bối cảnh phiên

| | |
|---|---|
| cây | `D:\LTTSTUDIOSAPP\.claude\worktrees\mobile-v1` |
| nhánh | `phien/mobile-v1`, đã merge `admin-mvp-v3` @ `b44da56a` |
| commit gần nhất | `8a1bc185` |
| nguồn quy trình | `G:\My Drive\AI\A LTT AII\LTT_MOBILE_AUTONOMOUS_PROMPT_PACK_V1` |
| kế hoạch | `docs/MOBILE/00_KE_HOACH.md` |
| dải số test | **700–799** (đã dùng 700, 701, 702, 703, 704, 705) |
| máy chủ đo | `python tools\studio_dev.py --cong 8123 --giu` |
| dựng dữ liệu đo | `mobile_qa.py bang` · `chat-seed <uid>` · `wav-dai <uid>` |
| trình duyệt | `playwright-cli` — Chromium + WebKit 26.5 |

⚠️ Cổng **8100 là production đang chạy thật**. Không đo trên đó.
⚠️ `frontend/*/node_modules` **đã cài** trong worktree — thiếu nó thì 3 bước
frontend của gate tự bỏ qua và in "KHÔNG PHẢI BẰNG CHỨNG".

---

## Trạng thái phase

| phase | trạng thái | bằng chứng |
|---|---|---|
| **A** kiểm kê + baseline | ✅ PASS | `01_MATRIX.md`, `02_BASELINE.md`, `03_BACKLOG.md` |
| **B** hợp đồng shared | ✅ PASS | `04_SHARED_CONTRACT.md` — 7/7 |
| **C** shared media + P0 | ✅ **PASS** | `phat_media` · voice.js · `05_SONG_AM.md` · vỏ ChatLTT |
| **D** media generator | 🟢 **~70%** | 5 bản chép Range đã gộp · `playsinline` · nhịp job |
| E editor phức tạp | 🟡 ~30% | `06_EDITOR.md` — khảo sát xong; hai giả thuyết của tôi bị bác bỏ |
| F bề mặt chuẩn | 🟢 **~75%** | `07_BE_MAT_CHUAN.md` — bảng/menu/destructive/EN đều sạch; `inputmode` 11→4; zoom 200% **đo được nhưng chưa sửa được** |
| G harness + ma trận | 🟡 ~25% | có bộ đo, chưa thành harness trong kho |
| H cổng phát hành | ⬜ | |

---

## Số đo trước → sau (Chromium; WebKit cho cùng kết quả)

| chỉ số | trước | sau |
|---|---:|---:|
| route tràn ngang @390 | 1 | **0** |
| route tràn ngang @**320** | 2 | **0** |
| ô nhập < 16px (cảm ứng) | 55 | **0** |
| ô nhập < 16px (**desktop**) | 57 | **58** ✅ không đổi có chủ ý |
| vùng chạm < 44px @390 | 468 | **200** |
| vùng chạm < 44px (**desktop**) | 747 | **781** ✅ không đổi (số tăng do seed thêm hội thoại) |
| bản chép bộ Range trong `apps/` | 5 | **0** |
| `<video>` thiếu `playsinline` | 7 | **0** |
| composer ChatLTT dưới màn hình | có | **không** |
| tải thừa khi vẽ sóng | 165 MB | **0** |
| vòng hỏi job không biết tab ẩn | 5 | **3** (còn React) |

## Lệnh test đã chạy

| lệnh | kết quả |
|---|---|
| `python tools\gate.py --vong-lap` | **PASS** (lượt gần nhất) |
| `python tools\test_nhanh.py` | ✅ **6089 passed / 32 skipped / 0 failed** + 67 frontend |

---

## 🔴 Giới hạn phải đọc trước khi tin bất kỳ báo cáo nào

**Playwright WebKit trên Windows không giải mã nổi audio.** Kể cả một WAV `data:`
URI tự sinh, không qua mạng — `MediaError.code = 4`, `networkState = 3` — trong
khi vẫn báo `canPlayType('audio/wav') = "probably"`.

⛔ Nên Gate C của pack (*"Voice play/seek xanh trên Playwright WebKit"*) **không
thể thoả mãn trên máy này**. Đo được trên WebKit: HTTP/Range (chính WebKit gửi
Range và nhận 206), bố cục, tràn, vùng chạm, cỡ chữ. Phát audio trên Safari phải
chuyển sang **thiết bị thật**.

## Năm lần "luật/phép đo tồn tại mà không làm gì"

Cùng một hình dạng lỗi, và **cả năm đều biên dịch được, đúng cú pháp, không lỗi
ở đâu cả**:

1. `:where()` có độ đặc hiệu **0** → luật cỡ chữ 16px thua mọi luật thành phần.
   Đo lại mới thấy 52/55 ô nhập vẫn nhỏ.
2. `env(safe-area-inset-*)` trả **0** khi meta viewport thiếu `viewport-fit=cover`.
3. `Cache-Control` của `chatltt` bị `server/app.py:253` ghi đè — chết từ trước.
4. `overflow-y:auto` trên một hàng grid cao `auto` (vỏ ChatLTT mobile) — không bị
   giới hạn chiều cao thì không có gì để tràn.
5. `<script defer>` cho một tệp mà script nội tuyến gọi **ngay** → `TypeError`.

⇒ **Luật nào thêm cũng phải đo lại sau khi thêm.**

Và hai lần **bộ đo tự nói dối**: `getBoundingClientRect().right` báo cả phần đã
bị `overflow-x:auto` hấp thụ (⇒ hai "thủ phạm" sai ở 320px); và một bộ bóc chú
thích coi `accept="image/*"` là `/*` rồi nuốt 31.605 ký tự.

---

## Việc tiếp theo (thứ tự)

1. **Seed dữ liệu cho ba editor** — không có nó thì mọi phép đo tương tác của
   Phase E rơi vào "không kết luận được" (xem `06_EDITOR.md` §2c). Làm giống
   `mobile_qa.py chat-seed`.
2. **Phase E còn lại** — nút `±0,1s` cho cue Autosub · 3 nút React < 44px ·
   3 vòng `setInterval` trong React cần hook tương đương `LTT.nhipJob`.
3. **Phase G** — biến bộ đo trong scratchpad thành harness trong kho, lái bằng
   registry, **gồm khung 320px** (nó đã bắt được 2 lỗi mà 390px bỏ lọt).
4. **Phase H** — `gate.py` đầy đủ · build 4 frontend đúng thứ tự · cache-bust ·
   deploy một lần rồi chốt trên URL công khai · `NHAT_KY` + rollback.
