# Pha 00–04 — nền, hợp đồng, bản đồ sở hữu, audit Viral, ma trận khoảng trống

Ngày 11/09/2026. Năm pha này là pha **tài liệu và kiểm kê**, không phải pha mã.
Phần lớn sản phẩm của chúng **đã tồn tại** từ V4/V5 — việc ở đây là đối chiếu
từng đề bài với thứ đang có, làm nốt phần thiếu, và **nói thẳng** phần chưa làm.

| pha | đề bài (tóm) | trạng thái | căn cứ |
|---|---|---|---|
| 00 | xác minh HEAD, worktree V6 riêng, audit chỉ đọc, đóng băng baseline | **XONG** | §1 |
| 01 | khoá target, phạm vi, định nghĩa DONE, scorecard, bỏ DEFER sai kiểu V5 | **MỘT PHẦN** | §2 |
| 02 | bản đồ sở hữu năng lực, ma trận REUSE/EXTEND/REIMPLEMENT | **XONG** | §3 |
| 03 | audit Viral lượt hai: menu Render theo tương tác + backend + engine | **CHƯA** | §4 |
| 04 | mỗi tính năng Viral có đích + pha; không tính năng nào biến mất | **XONG** | §5 |

## 1. Pha 00 — nguồn gốc

| câu hỏi | trả lời, đo ngày 11/09 |
|---|---|
| worktree V6 riêng | `D:/LTTSTUDIOSAPP/.claude/worktrees/asv-v6`, nhánh `phien/asv-v6` |
| gốc chung với trunk | `768b1dba` (`admin-mvp-v3`) |
| khoảng cách | đi trước trunk **46** commit, sau trunk **42** commit |
| commit đầu tiên của dòng này | `891d93db` (08/09) |
| bản off-site | `origin/phien/asv-v6` — lần đầu đẩy **11/09**; trước đó 41 commit chỉ nằm trên một ổ đĩa |
| baseline đóng băng | bản ghi gate máy sinh `test-results/gates/*.json` mang `sha` + kết quả từng bước |
| audit chỉ đọc | kho: `REBASE_MAP_V4.md`; Viral: `VIRAL_RENDER_FEATURE_MAP.md` (V5) |

⛔ `D:\BOT GEMINI` là kho tham chiếu chỉ đọc đang phục vụ người dùng thật — không
chạm. `D:\Viral` chỉ đọc.

## 2. Pha 01 — hợp đồng sản phẩm

* **Target + định nghĩa DONE**: `V6_OPERATING_CONTRACT.md` của gói V6 + cổng gate
  đầy đủ (không deploy tới pha 34, `manifest.py` `enabled=False`).
* **Phạm vi tính năng**: `MA_TRAN_TINH_NANG_V6.md` — 59 tính năng, mỗi cái một pha.
* **Bỏ DEFER sai kiểu V5**: 12 dòng `DEFER` của ma trận V5 nay đều có pha V6;
  `test_477` chốt không còn `DEFER` trơ trụi.
* ⚠️ **Chưa làm**: chấm từng pha theo `V6_98_SCORECARD.md`. Việc chấm độc lập là
  đề bài của pha 34, và tự chấm phần mình làm thì không phải bằng chứng.

## 3. Pha 02 — bản đồ sở hữu năng lực

`docs/auto_scan_video_v4/REBASE_MAP_V4.md` chính là ma trận REUSE/EXTEND/ADD theo
từng tệp, và nó được **giữ sống** qua V6: mỗi pha có module mới đều thêm dòng
(`phu_de.py` pha 14/16, `qc.py` pha 27, …). Bề mặt liên-app được **cưỡng chế** ở
`tools/lint_app_contract.py` (`APP_DUOC_DUNG_APP`), không chỉ ghi chép.

`MA_TRAN_KHOANG_TRONG.md` bổ sung chiều thứ hai: với từng pha còn lại, năng lực đã
có chưa (**ĐƯỜNG / CẦU / MÓNG**).

## 4. Pha 03 — CHƯA LÀM, và vì sao

Lượt một đã có ở V5 (`VIRAL_RENDER_FEATURE_MAP.md`). Lượt hai đòi đọc lại menu
Render của `D:\Viral` theo **tương tác + backend + engine**, và ánh xạ từng điều
khiển tới đầu ra thật, cache, CPU/GPU, hành vi khi hỏng. `D:\Viral` là một ứng dụng
Electron đóng gói (`ViralCrawl.exe`) — việc đó là mổ tài nguyên đóng gói, không
phải đọc một thư mục mã. Không làm trong lượt này; ma trận ở §5 đứng trên lượt một.

## 5. Pha 04 — ma trận tính năng

`MA_TRAN_TINH_NANG_V6.md`, dựng bằng máy từ ma trận V5 (tên lấy nguyên văn):

| XONG | MỘT PHẦN | CHƯA | CẦN ADR | LOẠI |
|---|---|---|---|---|
| 28 | 8 | 15 | 3 | 5 |

`test_477` chốt **tập hợp**: tên ở V6 phải bằng đúng tên ở V5. Đối chứng: xoá một
dòng ⇒ **đỏ**; trả một dòng về `DEFER` ⇒ **đỏ**.

Ba mâu thuẫn V5 ↔ V6 được đặt tên, không làm mịn: *nhạc nền*, *lật gương*, *ảnh
bìa* — cả ba cần một quyết định sản phẩm.
