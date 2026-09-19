> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: python tools/ho_so_cay.py trang-thai (snapshot một lần, không phải bảng sống). Chỉ đọc để hiểu lịch sử.

# WORKTREE INVENTORY — W0 (LTT AI CLEAN REBUILD V2)

> **Pha:** W0 — ACTIVE SESSION FREEZE + WORKTREE INVENTORY
> **Đo lúc:** 2026-09-08 16:24 (giờ máy, UTC+7)
> **Tính chất:** CHỈ ĐỌC. Không `remove`, không `reset`, không `switch`,
> không `delete`, không `commit`, không sửa business code.
> **Lệnh đã chạy:** `git worktree list --porcelain` · `git branch -vv` ·
> `git status --porcelain` (7 cây) · `git remote -v` · `git fetch --all --prune`
> · `git rev-list --left-right --count` · `git rev-list --count <b> --not --remotes=origin`

## 0. Tóm tắt

| Chỉ số | Giá trị |
|---|---|
| Repo HEAD (cây chính) lúc 16:24 | `21fa7e2b6471de9ef34ef8e84028f43924557944` |
| Repo HEAD (cây chính) lúc 16:27 | `b4a71551` — **đã đổi giữa lúc W0 đang viết** (§2) |
| Branch (cây chính) | `admin-mvp-v3` |
| Số worktree | 7 |
| Số nhánh local | 10 |
| Số nhánh remote (`origin`) | 22 + `HEAD` |
| ACTIVE_WORKTREES | **4** — chủ dự án xác nhận 16:34, xem §2.1 |
| CLEAN_CANDIDATES | **3** |
| DIRTY | **3** |
| UNIQUE_COMMIT_WORKTREES | **0** |
| READY_FOR_W1 | **NO** — xem §5 |

🔑 **Phát hiện quan trọng nhất:** mọi tip nhánh local đều **đã có trên `origin`**
(`git rev-list --count <branch> --not --remotes=origin` = 0 cho cả 10 nhánh).
Rủi ro mất việc **không** nằm ở commit — nó nằm hoàn toàn ở **68 tệp chưa
commit** trong 3 cây (§3).

## 1. Bảng inventory

Cột theo `templates/WORKTREE_INVENTORY.csv` của pack.

| Path | Branch (đo bằng `rev-parse`) | HEAD | Dirty | Ahead/Behind `origin/master` | Unpushed | Upstream | ActiveSession | Classification | Action |
|---|---|---|---|---|---|---|---|---|---|
| `D:/LTTSTUDIOSAPP` | `admin-mvp-v3` | `21fa7e2b` → `b4a71551` | **26 M + 17 ??** | +258 / −0 | **0** | *(chưa đặt)*; ngang bằng `origin/admin-mvp-v3` 0/0 | **CÓ — 2 phiên** | `ACTIVE_PROTECT` + `DIRTY_INVESTIGATE` | KHÔNG ĐỘNG |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/auto-scan-video-v4-mvp-7173d9` | `phien/asv-v4` | `9d7f7044` | **25 M + 8 ??** | +159 / −0 | **0** | `origin/phien/asv-v4` (0/0) | **CÓ** — chủ dự án xác nhận (§2.1) | `ACTIVE_PROTECT` + `DIRTY_INVESTIGATE` | KHÔNG ĐỘNG |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/chatltt-v3-agentic` | `claude/chatltt-v3-agentic` | `139cb1d1` | sạch | +25 / −0 | **0** | *(chưa đặt)*; commit đã ở `origin/claude/chatltt-v3-agentic` | Không | `CLEAN_CANDIDATE` | ứng viên `REMOVE_SAFE` ở W2 |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/ltt-llm-api-http-guide-a3e123` | **detached** `989353c2` | `989353c2` | sạch | +49 / −339 | **0** | — (tip = `origin/claude/ltt-video-ai-v3-p00-3f5713`) | Không | `CLEAN_CANDIDATE` | ứng viên `REMOVE_SAFE` ở W2 |
| `D:/LTTSTUDIOSAPP/.claude/worktrees/video-v2-wangp` | `phien/video-v2-wangp` | `f19b072d` | sạch | +249 / −0 | **0** | *(chưa đặt)*; đã ở `origin/phien/video-v2-wangp` | **CÓ** | `ACTIVE_PROTECT` | KHÔNG ĐỘNG |
| `D:/LTTSTUDIOSAPP-wf2` | `phien/wf2` | `b92839a3` | **2 M** | +255 / −0 | **0** | *(chưa đặt)*; đã ở `origin/phien/wf2` | **CÓ — đang ghi** | `ACTIVE_PROTECT` + `DIRTY_INVESTIGATE` | KHÔNG ĐỘNG |
| `D:/LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | `b4adf873` | sạch | +2 / −672 | **0** | *(chưa đặt)*; đã ở `origin/h42-release-clean` | Không | `CLEAN_CANDIDATE` | ứng viên `ARCHIVE_THEN_REMOVE` ở W2 |

⚠️ **Không có worktree nào đứng ở `master`.** `TRUNK_PROTECT` = 0 cây. Chiến
dịch sẽ cần **tạo mới** một cây (`architecture/ai-clean-rebuild`) ở W2/pha 00 —
nó không thể tái dùng cây nào ở trên.

⚠️ **Tên thư mục worktree KHÔNG phải nhánh nó đang đứng.** Cây
`ltt-llm-api-http-guide-a3e123` đang detached ở tip của
`claude/ltt-video-ai-v3-p00-3f5713`, không liên quan gì tới `ltt-llm-api-http-guide`.
Mọi số ở bảng trên đo bằng `git -C <path> rev-parse`, không đọc theo tên thư mục.

## 2. Bằng chứng phiên đang hoạt động

`ListAgents` báo **3 phiên peer** + phiên này = 4. Nhưng `ListAgents` chỉ thấy
phiên **tồn tại lúc hỏi**, nên bằng chứng quyết định là **nhịp ghi tệp nguồn**
(`find -newermt`, loại trừ `__pycache__`), đo lúc 16:24:

| Cây | Tệp nguồn ghi < 2h | Tệp nguồn mới nhất | Kết luận |
|---|---|---|---|
| `D:/LTTSTUDIOSAPP` | **88** | `apps/ltt_voice/routes/_p_nghe_thu.py` — **16:21** | Phiên LTT VOICE **đang chạy**, cùng cây với phiên này |
| `D:/LTTSTUDIOSAPP-wf2` | **3.370** | `tools/restore_drill_schema.py` — **16:22** | Phiên **đang chạy** (đợt ghi hàng loạt 15:55 = checkout/đồng bộ) |
| `.../video-v2-wangp` | 2 | `tools/wangp/bao_cao_moi_truong.py` — **15:04** | **Đang chạy** (cache import-linter 15:59 ⇒ có lượt gate lúc đó) |
| `.../auto-scan-video-v4-mvp-7173d9` | 0 | `docs/auto_scan_video_v5/V5_IMPLEMENTATION_STATUS.md` — **11:56** | Im 4h39m — nhưng **ĐANG CHẠY**, xem §2.1 |
| 3 cây còn lại | 0 | — | Không có phiên |

## 2.1 🔴 Nhịp ghi tệp đã cho một ÂM TÍNH GIẢ — và đây là ca đo được

Lúc 16:34 chủ dự án xác nhận: phiên LTT VOICE, phiên `wf2`, phiên
`video-v2-wangp` **và** phiên **Auto Scan Video GUI V5** đều **chưa kết thúc**.

Phiên ASV V5 sống trong `.../auto-scan-video-v4-mvp-7173d9`, và tệp nguồn mới
nhất của cây đó là **11:56** — im **4 giờ 39 phút** tại thời điểm hỏi. Phép đo
nhịp ghi ở §2 xếp nó vào *"chưa kết luận"*; sự thật là **đang chạy**.

🔑 **Rút ra:** nhịp ghi tệp chỉ chứng minh được **sự CÓ MẶT**, không bao giờ
chứng minh được **sự VẮNG MẶT**. Một phiên đang đọc mã, đang chờ người dùng,
đang phân tích, hay đang chạy một lượt đo dài đều **không ghi gì cả** — và trông
y hệt một phiên đã chết. Chiều ngược lại thì chắc: HEAD đổi lúc 16:27 **là** bằng
chứng phiên VOICE còn sống.

⇒ Trong toàn chiến dịch này, một cây chỉ được coi là **không có phiên** khi
**chủ dự án nói thế**, không bao giờ vì nó im lặng. Ba cây `CLEAN_CANDIDATE`
ở §1 vì vậy vẫn là **ứng viên**, chưa phải kết luận — W2 phải hỏi lại từng cây.

🔴 **Cây chính có HAI phiên — và có bằng chứng mạnh hơn nhịp ghi tệp.**
Phiên này (`lttstudiosapp-bc`) và một phiên LTT VOICE. Trong khoảng ba phút W0
soạn báo cáo, phiên kia đã:

- sửa **`CLAUDE.md`** và `docs/OPERATING_STANDARDIZATION/FINAL_REPORT.md` — hai
  tệp chưa hề có trong ảnh chụp `git status` lúc phiên này bắt đầu;
- **commit lúc 16:27:21**, đẩy HEAD của cây chính từ `21fa7e2b` sang
  `b4a71551` (*"Khoi phuc doan ma khong-BOM vao `CLAUDE.md`"*).

Đây không phải suy đoán từ mtime: **`HEAD` đổi giữa lượt đo**. Giao ước
`AGENTS.md` §10 áp dụng tuyệt đối ở cây này — tệp dùng chung chỉ sửa bằng
`Edit`, không bao giờ `Write`.

⚠️ Hệ quả cho phép đo: mọi con số của cây chính là **ảnh chụp tại 16:24–16:27**,
không phải một trạng thái đứng yên. Dòng `?? docs/REPO_HYGIENE/` trong
`git status` là **artefact của chính W0 này**, không phải việc của phiên khác.

## 3. Việc chưa commit — đây là toàn bộ rủi ro mất mát

**68 tệp** chưa commit, trên 3 cây. Không tệp nào được đụng tới trong W0.

### 3.1 `D:/LTTSTUDIOSAPP` — `admin-mvp-v3` — 43 tệp (LTT VOICE, đang chạy)

26 sửa đổi (`CLAUDE.md` đã được phiên kia commit lúc 16:27, nên rời khỏi danh
sách bẩn sau phép đo đầu):
`docs/OPERATING_STANDARDIZATION/FINAL_REPORT.md` ·
`docs/architecture/workflow_v2_audit/31_NHAT_KY_TRIEN_KHAI.md` ·
`docs/LTT_VOICE/{DECISIONS,VIRAL_VOICE_AUDIT_2026-09-07,VOICE_UI_EXECUTION_PLAN}.md` ·
`server/static/voice.js` · `tests/test_50{0,1,4}_*` · 15 tệp `apps/ltt_voice/`.

18 tệp mới: `alembic/versions/20260908_1600_voice_license_va_curate.py` ·
`apps/ltt_voice/{chi_so_giong.py,ho_so_giong.py,ho_so_giong.json,muc_dung.py,nghe_thu_cua_toi.py}` ·
`apps/ltt_voice/routes/{_p_chi_so,_p_nghe_thu}.py` · `tests/test_50{6,7,8,9}_*` ·
`tests/test_51{0,1}_*` · `tools/{do_ho_so_giong,dung_nghe_thu,soat_giong}.py`.

⚠️ Trong đó có **một migration chưa commit** (`20260908_1600_voice_license_va_curate.py`).
Bất kỳ bước deploy nào của chiến dịch này phải đối chiếu `alembic` trước.

### 3.2 `.../auto-scan-video-v4-mvp-7173d9` — `phien/asv-v4` — 33 tệp (im 4h28m)

25 sửa đổi (12 tệp `apps/auto_scan_video/`, 2 tệp `apps/ltt_voice/`,
`locale/en/LC_MESSAGES/messages.{po,mo}`, `server/templating.py`,
`server/static/ltt.css`, `tools/gui/ltt.css`, `tools/lint_app_contract.py`,
4 tệp test 4xx, 1 tài liệu) + 8 tệp mới (`apps/auto_scan_video/vung_che.py`,
`server/static/asv.js`, `docs/auto_scan_video_v5/`, `tests/test_45{5,6,7,8,9}_*`).

⚠️ Cây này chạm **`server/templating.py`**, `locale/*` và **`tools/lint_app_contract.py`**
— tức là **hạ tầng dùng chung**, không chỉ `apps/auto_scan_video/`. Đây là
xung đột tiềm tàng với chiến dịch clean rebuild và phải giải ở W1.

### 3.3 `D:/LTTSTUDIOSAPP-wf2` — `phien/wf2` — 2 tệp (đang chạy)

`platform_core/public_api/governance.py` · `tools/restore_drill_schema.py`.

## 4. Nhánh — local và remote

10 nhánh local, **0 unpushed commit**. 22 nhánh remote. Nhánh remote **không có**
cây local nào và **không có** nhánh local tương ứng (9 nhánh):

`chuan/ngan-sach-loi` · `claude/auto-scan-video-v4-mvp-7173d9` ·
`claude/ltt-llm-api-http-guide-a3e123` · `claude/ltt-llm-context-overflow-efe02f` ·
`claude/ltt-voice-autonomous-supervisor-1c3f95` · `claude/ltt-voice-unlimited-tts-743eb0` ·
`claude/lttchat-autonomous-build-plan-1cf29d` · `claude/wonderful-jepsen-f190f3` ·
`phase-minus-1-foundation` · `phien/ltt-llm-context-200k` · `phien/p01` ·
`phien/p08` · `public-api-v2`.

⛔ **Không đụng tới nhánh remote ở pha này.** Theo pack, remote hygiene là **pha 14**,
sau khi master sạch đã merge + deploy + verify. Bảng
`REMOTE_BRANCH_INVENTORY.csv` sẽ lập ở pha 14, không phải bây giờ.

## 5. Vì sao `READY_FOR_W1 = NO`

W1 (`W1_ADMIN_V3_RECONCILE.md`) mở đầu bằng một điều kiện tường minh:

> *"CHỈ chạy sau khi chủ dự án xác nhận các phiên admin-v3 đã kết thúc."*

**Chủ dự án đã trả lời lúc 16:34: các phiên CHƯA kết thúc** — LTT VOICE
(`admin-mvp-v3`), `wf2`, `video-v2-wangp`, và Auto Scan Video GUI V5
(`phien/asv-v4`). Điều kiện mở W1 vì vậy **chưa đạt**, và đây là một câu trả lời
dứt khoát chứ không phải một phép đo còn nghi ngờ.

Ba điều kiện còn thiếu:

1. **Phiên `admin-mvp-v3` chưa kết thúc.** Đo độc lập khớp với lời xác nhận:
   HEAD đi `21fa7e2b` → `b4a71551` (16:27) → `d83fb7f6` (16:34) — **hai commit
   trong mười phút** ngay giữa lượt W0.
2. **43 tệp chưa commit của phiên đó** chưa thể phân loại. W1 đòi
   `UNCOMMITTED_UNKNOWN=0`; không phiên nào ngoài chính phiên VOICE trả lời được
   tệp nào là "xong", tệp nào là "đang dở".
3. **`phien/asv-v4` cũng đang chạy** với 33 tệp bẩn chạm hạ tầng dùng chung
   (`server/templating.py`, `locale/*`, `tools/lint_app_contract.py`). Cây này
   phải được chính phiên ASV V5 chốt trước, không phải W1 đoán hộ.

⛔ **Không có đường vòng.** Nền của chiến dịch (pha 00) phải là một điểm đứng
yên; hiện `admin-mvp-v3` hơn `origin/master` 258 commit **và vẫn đang tăng**.
Chạy 00 lúc này là lấy nền trên một mục tiêu đang di chuyển.

## 6. Gate W0

| Điều kiện W0 | Kết quả |
|---|---|
| Chỉ inventory, không remove/reset/switch/delete/commit | ✅ — 0 lệnh ghi git |
| Không sửa business code | ✅ — chỉ tạo `docs/REPO_HYGIENE/`, `docs/AI_CLEAN_REBUILD/` |
| `admin-v3`/`admin-mvp-v3` phân loại `ACTIVE_PROTECT` | ✅ |
| Tạo `docs/REPO_HYGIENE/WORKTREE_INVENTORY.md` | ✅ — tệp này |
| ACTIVE_WORKTREES / CLEAN_CANDIDATES / DIRTY / UNIQUE_COMMIT_WORKTREES | ✅ — **4** / 3 / 3 / 0 |

**W0 GATE = PASS.** Cấp test áp dụng: **L0 không cần** — W0 không chạm một dòng
mã thực thi nào, bán kính "THẤP" (`00_LTT_OPERATING_CONTRACT.md` §4.5: tài liệu).
Chạy gate ở đây sẽ vừa vô nghĩa vừa vi phạm §4.2 và §4.9 (ba phiên đang ghi tệp —
một lượt gate lúc này chắc chắn ra `CAY DA DOI GIUA CHUNG`).

## 7. Ghi chú ngoài phạm vi (§3 hợp đồng — ghi lại, không sửa)

- **Không có nhánh nào tên `admin-v3`.** Pack nhắc `admin-v3`; kho chỉ có
  `admin-mvp-v3` (local + `origin/admin-mvp-v3`, ngang bằng nhau). Coi hai tên
  là một trong suốt chiến dịch.
- **`master` đi sau rất xa.** `admin-mvp-v3` hơn `origin/master` **258 commit**,
  `phien/wf2` **255**, `phien/video-v2-wangp` **249**. Chiến dịch clean rebuild sẽ
  phải chọn điểm nền — `master` hay `admin-mvp-v3` — ở pha 00. Đây là quyết định
  của pha 00, không phải của W0.
- **6 cây dùng chung một `.git`.** Commit vào nhánh dùng chung là **đã xuất bản**
  (`00_LTT_OPERATING_CONTRACT.md` §6).
