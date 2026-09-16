# RULE INVENTORY — mọi nguồn luật vận hành trong HEAD

> ⚠️ **Ảnh chụp lịch sử.** Nhịp hiện hành (16/09: test nhắm trong phiên, L3 một
> lần cuối phiên) ở `docs/00_LTT_OPERATING_CONTRACT.md` §4 và
> `SESSION_MIGRATION_NOTE.md`. Cột *"khớp canonical"* dưới đây so với luật 08/09.
>
> Chụp **2026-09-08**. Phạm vi quét: **822 tệp `.md` được git theo dõi**
> (`git ls-files '*.md'`, trừ `docs/_luutru/`), cộng `tools/gate.py`,
> `tools/test_nhanh.py`, `tools/thanh_phan.py`, `pytest.ini`, `tests/conftest.py`.
>
> ⛔ **`.claude/worktrees/**` KHÔNG nằm trong phạm vi.** Đó là cây của phiên khác,
> không phải HEAD. Lượt grep đầu tiên của chiến dịch này quét trúng chúng và trả
> về hàng trăm tệp — con số đó sai. `git ls-files` mới là định nghĩa của HEAD.

## Cách phân loại

| Loại | Nghĩa |
|---|---|
| **POLICY** | Ra lệnh cho công việc **tương lai**, phạm vi **toàn cục** |
| **FACT** | Sự thật kỹ thuật / bất biến. Không phải cadence |
| **EVIDENCE** | Ghi lại một lượt chạy **đã xảy ra**. Không ra lệnh gì |
| **PLAN-LOCAL** | Cadence viết lại bên trong một kế hoạch chiến dịch |

Chỉ **POLICY** và **PLAN-LOCAL** mới có thể chồng chéo. **EVIDENCE** không bao giờ
là luật — `docs/` có hàng trăm dòng dạng "đã chạy `gate.py`, PASS 23/23", và đếm
chúng như luật là lý do lượt quét đầu tiên ra con số vô nghĩa.

---

## A. Nguồn luật toàn cục

| ID | Nguồn | Luật hiện tại | Loại | Còn đúng? | Trùng? | Mâu thuẫn? | Final action |
|---|---|---|---|---|---|---|---|
| A1 | `CLAUDE.md` §4 | `gate.py --vong-lap` sau **MỖI** lần sửa; `test_nhanh.py` cả bộ; `gate.py` trước khi báo xong | POLICY | ⚠️ một phần | ✅ A2 | ✅ A3 | **MERGE_INTO_CANONICAL** |
| A2 | `AGENTS.md` §4b | Y hệt A1, bảng 4 lệnh, cộng `--noi-tiep` | POLICY | ⚠️ một phần | ✅ A1 | ✅ A3 | **MERGE_INTO_CANONICAL** |
| A3 | `docs/DEVELOPMENT_WORKFLOW.md` §2 | Vòng lặp là `gate --doi`, **không** phải `--vong-lap` | POLICY | ✅ | — | ✅ A1/A2 | **KEEP_AND_CONSOLIDATE** (đây là bản **đúng hơn**) |
| A4 | `CLAUDE.md` §4 + `AGENTS.md` §4b | "⛔ đừng chạy `python -m pytest` cho toàn kho" | POLICY | ✅ | ✅ nhau | — | **MERGE_INTO_CANONICAL** |
| A5 | `CLAUDE.md` §4 + `AGENTS.md` §4b | "Gate là công cụ **phán quyết**, không phải **chẩn đoán**" | POLICY | ✅ | ✅ nhau + `KE_HOACH_NOI_TIEP:334` | — | **MERGE_INTO_CANONICAL** |
| A6 | `CLAUDE.md` §Quy tắc 5/5b | Kiểm trình duyệt sau đổi giao diện; chốt trên **URL công khai** | POLICY | ✅ | ✅ `AGENTS.md` §4b cuối | — | **MERGE_INTO_CANONICAL** |
| A7 | `CLAUDE.md` §Quy tắc 6 | Đổi static ⇒ cache-bust | FACT | ✅ | — | — | **TECHNICAL_FACT_NOT_POLICY** — giữ tại chỗ |
| A8 | `CLAUDE.md` §Quy tắc 1/2/3 | Không BOM · `.ps1` thuần ASCII · không Python inline qua PowerShell | FACT | ✅ | ✅ `AGENTS.md` §5 | — | **TECHNICAL_FACT_NOT_POLICY** — gom về `AGENTS.md` §5 |
| A9 | `AGENTS.md` §0 | Preflight khi mở/khôi phục phiên | POLICY | ✅ | ⚠️ `DEVELOPMENT_WORKFLOW` §1 | — | **MERGE_INTO_CANONICAL** |
| A10 | `AGENTS.md` §10 | Hai phiên cùng cây — giao ước tệp, `Edit` không `Write` | POLICY | ✅ | ⚠️ `DEVELOPMENT_WORKFLOW` §5 | — | **MERGE_INTO_CANONICAL** |
| A11 | `AGENTS.md` §4c/§4d | Sửa hạ tầng dùng chung — ba câu hỏi; sổ lỗi tự gây 5 lớp | FACT | ✅ | — | — | **KEEP_AND_CONSOLIDATE** (giữ ở `AGENTS.md`) |
| A12 | `AGENTS.md` §8 | Bố cục mã nguồn app; trần 900 dòng/30 handler | FACT | ✅ | ⚠️ `CLAUDE.md` §Thêm app | — | **TECHNICAL_FACT_NOT_POLICY** |
| A13 | `docs/QUY_TAC_CHAY_LENH_NANG.md` | 4 bước trước lệnh nặng; `cua_so_yen` | POLICY | ✅ | ⚠️ CLAUDE.md global | — | **KEEP_AND_CONSOLIDATE** (trỏ tới từ canonical) |
| A14 | `docs/16_CAP_NHAT_VA_DEPLOY.md` | Đồng bộ → gate → ff → deploy → push | POLICY | ✅ | — | — | **KEEP_AND_CONSOLIDATE** (deploy có cổng riêng — đúng) |
| A15 | `docs/QUY_TRINH_WORKTREE.md` | Luật tạo/gỡ worktree | POLICY | ✅ | ⚠️ `DEVELOPMENT_WORKFLOW` §1 | — | **KEEP_AND_CONSOLIDATE** |
| A16 | `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | 17 cái bẫy của chính gate | FACT | ✅ | — | — | **TECHNICAL_FACT_NOT_POLICY** |
| A17 | `CLAUDE.md` §CHƯA CÓ KHÁCH | Đừng rà soát tương thích ngược; 4 ngoại lệ | POLICY | ✅ | — | — | **KEEP_AND_CONSOLIDATE** |
| A18 | `CLAUDE.md` §Hiện giờ cái gì đang sống | Hỏi máy chủ, đừng đọc bảng chép tay | POLICY | ✅ | — | — | **KEEP_AND_CONSOLIDATE** |

## B. Cadence viết lại trong kế hoạch chiến dịch — nguồn chồng chéo thật

Đây là chỗ luật sinh sôi. **Mỗi kế hoạch chép lại cadence**, và bốn bản chép
**không giống nhau**.

| ID | Nguồn | Cadence nó khai | Khác canonical thế nào | Chủ | Final action |
|---|---|---|---|---|---|
| B1 | `docs/CHATLTT_V3/00_KE_HOACH_V3.md:253` | `--vong-lap` sau mỗi sửa · đầy đủ trước mỗi phase | dùng `--vong-lap`, không `--doi` | ⛔ phiên sống | **MERGE_INTO_CANONICAL** *(qua migration note)* |
| B2 | `docs/KE_HOACH_NOI_TIEP_2026-08-29.md:67` | chép nguyên khối lệnh của `CLAUDE.md` §4 | trùng hoàn toàn | — | **DELETE_OBSOLETE** |
| B3 | `docs/VPS/UI_MVP_V2/00_KE_HOACH_GIAO_DIEN.md:572` | `test_nhanh.py --lf` sau mỗi lần sửa | **gọi thẳng test runner**, bỏ qua gate | — | **DELETE_OBSOLETE** |
| B4 | `docs/MOBILE/00_KE_HOACH.md:93,194` | `VL` sau mỗi bước; rồi `test_nhanh.py` **rồi** `gate.py` | ⛔ **chạy pytest hai lần** | — | **DELETE_OBSOLETE** |
| B5 | `docs/admin_mvp_v3/00_KE_HOACH_TRIEN_KHAI.md:210` | `--vong-lap` sau mỗi lô · đầy đủ trước mỗi bước | dùng `--vong-lap` | — | **DELETE_OBSOLETE** |
| B6 | `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md:463` | `--vong-lap` sau **mỗi** lần sửa | dùng `--vong-lap` | ⛔ phiên sống | **MERGE_INTO_CANONICAL** *(qua migration note)* |
| B7 | `docs/auto_scan_video/BASELINE_COMMANDS.md:12,15` | `test_nhanh.py` (4 phút) **rồi** `gate.py` (5 phút) | ⛔ **chạy pytest hai lần** | — | **DELETE_OBSOLETE** |
| B8 | `docs/auto_scan_video/STATE.md:52` | "invariant subset — run after every edit" | cadence thứ tư | — | **DELETE_OBSOLETE** |
| B9 | `docs/auto_scan_video_v4/STATE_V4.md:400` | `VONG_NHANH` 9 tệp sau mỗi edit | cadence thứ năm | ⛔ phiên sống | **MERGE_INTO_CANONICAL** *(qua migration note)* |
| B10 | `docs/system_purification/KE_HOACH_THI_HANH.md:73,329` | commit checkpoint khi `--vong-lap` xanh; `test_214` chạy tay sau mọi thay đổi | dùng `--vong-lap` | — | **DELETE_OBSOLETE** |
| B11 | `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md:58,204,278` | `gate --doi` vòng lặp; đầy đủ 1 lần cuối phase | ✅ **khớp canonical** | — | **KEEP_AND_CONSOLIDATE** |
| B12 | `docs/PUBLIC_API/TEST_STRATEGY_V1.md:44` | "`gate.py` là cổng duy nhất được coi là regression xanh" | ✅ khớp | — | **KEEP_AND_CONSOLIDATE** |

⭐ **B4 và B7 là bằng chứng cho nghi ngờ "chạy pytest hai lần".** Cả hai bảo chạy
`test_nhanh.py` (4 phút) rồi `gate.py` (5 phút) — mà bước `bo test` **bên trong**
`gate.py` chính là `test_nhanh.py` (`tools/gate.py:838`). Đó là ~4 phút trả hai
lần cho cùng một tập pass/fail.

## C. Sự thật kỹ thuật phải GIỮ (đừng xoá nhầm cùng cadence)

| ID | Bất biến | Nguồn | Đưa về đâu |
|---|---|---|---|
| C1 | Test ghi vào tệp thật trong kho phải khai `TEP_NOI_TIEP` + khôi phục đúng byte **và** đúng mtime | `AGENTS.md` §4b | giữ `AGENTS.md`; canonical trỏ tới |
| C2 | Test không được đọc trạng thái máy (tải GPU, tốc độ CPU) | `AGENTS.md` §4b | giữ `AGENTS.md` |
| C3 | `npm run build` là việc **cuối** trước gate | `AGENTS.md` §4b | giữ `AGENTS.md` |
| C4 | `--tuan-tu` ≠ `--noi-tiep` | `AGENTS.md` §4b | giữ `AGENTS.md` |
| C5 | Cache `lastfailed` toàn id chết ⇒ `--lf` chạy **toàn bộ** | `tools/gate.py:1084`, `CLAUDE.md` §4 | canonical (lý do bỏ `--vong-lap` làm mặc định) |
| C6 | Test nạp model thật phải sau rào `LTT_TEST_NANG` / marker `nang` | `pytest.ini`, `tests/rao_chan_nang.py` | canonical §test levels |
| C7 | Trần `-n 6`; ngân sách lõi; `cua_so_yen` trước lệnh nặng | `~/.claude/CLAUDE.md`, `QUY_TAC_CHAY_LENH_NANG.md` | canonical trỏ tới |
| C8 | Ánh xạ test suy từ **import**, không từ tên tệp | `DEVELOPMENT_WORKFLOW.md` §3 | canonical §L1 |
| C9 | Deploy chép **cả cây** ⇒ hỏi phiên khác trước | `docs/16_...`, `CLAUDE.md` | canonical §deploy |
| C10 | Kiểm URL công khai, không chỉ loopback | `CLAUDE.md` §5b | canonical §live acceptance |

## D. Tham chiếu treo — tài liệu trỏ vào một hợp đồng HEAD không có

`OPERATING_CONTRACT §5/§6/§10/§13` và `V4_OPERATING_CONTRACT A.1–A.6` được **11
tệp** trích dẫn như luật (`docs/audit_ltt_llm/reports/*`, `docs/auto_scan_video_v4/*`,
`docs/system_purification/KE_HOACH_THI_HANH.md:73`).

```
$ git ls-files | grep -iE "operating_contract"
(khong co gi)
```

⇒ Các tệp ấy trích một hợp đồng **chỉ tồn tại trong prompt của một phiên đã đóng**.
Không ai kiểm chứng lại được một trích dẫn như thế. Đây là lập luận mạnh nhất cho
việc `docs/00_LTT_OPERATING_CONTRACT.md` phải **nằm trong kho**.

Final action: **INVESTIGATE** → giải quyết bằng cách tạo hợp đồng canonical thật.
Không sửa 11 tệp trích dẫn (phần lớn là EVIDENCE của phiên đã đóng).

## E. Cấu hình test

| ID | Hiện trạng | Đánh giá | Final action |
|---|---|---|---|
| E1 | `pytest.ini` chỉ khai marker `nang`, **cố ý không có `addopts`** | ✅ đúng — `addopts` ẩn sẽ đổi hành vi của cả gate lẫn `test_nhanh` mà không ai thấy trong lệnh | **KEEP_AND_CONSOLIDATE** |
| E2 | `@pytest.mark.slow` dùng 1 lần nhưng **không khai** trong `pytest.ini` | ⚠️ nhỏ; chưa bật `--strict-markers` nên chưa gãy | **INVESTIGATE** → follow-up P1 |
| E3 | `pytest-xdist` **đã có và đã dùng** (`test_nhanh.py --dist loadfile`) | ✅ đã tối ưu xong từ 26/08 (2 giờ → 4 phút) | **TECHNICAL_FACT_NOT_POLICY** |
| E4 | `STATE_V4.md:756` khẳng định "no `pytest.ini` in the repo at all" | ❌ **SAI** — `pytest.ini` có trong HEAD | ghi vào FINAL_REPORT; tệp thuộc phiên sống, không sửa hộ |

---

## Tổng kết số

| | |
|---|---|
| Tệp `.md` được git theo dõi đã quét | **822** |
| Nguồn có mệnh lệnh cadence toàn cục/kế hoạch | **30** |
| Rule ghi vào bảng | **44** (A1–A18, B1–B12, C1–C10, D, E1–E4) |
| `DELETE_OBSOLETE` | **7** (B2, B3, B4, B5, B7, B8, B10) |
| `MERGE_INTO_CANONICAL` | **11** |
| `KEEP_AND_CONSOLIDATE` | **11** |
| `TECHNICAL_FACT_NOT_POLICY` | **6** |
| `INVESTIGATE` | **2** (D, E2) |
| Cadence **mâu thuẫn** cùng tồn tại trong HEAD | **5 bản khác nhau** |
| Nơi bảo chạy pytest **hai lần** | **2** (B4, B7) |
