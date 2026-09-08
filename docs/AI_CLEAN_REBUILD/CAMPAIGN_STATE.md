# CAMPAIGN STATE — LTT AI CLEAN REBUILD V2

**Pack:** `G:/My Drive/AI/A LTT AII/LTT_AI_CLEAN_REBUILD_CLAUDE_PACK_V2`
**Phiên điều phối:** `lttstudiosapp-bc`
**Cây chiến dịch:** `D:\LTTSTUDIOSAPP-aiclean` · nhánh `phien/aiclean` · nền **`0d1ffe5a`**
**Dải test được cấp cho cây này:** `1000–1099`
**Thứ tự pha:** `W0 → W1 → W2 → 00 → 01 → … → 15` (không gộp, không bỏ pha)

## Bảng pha

| Pha | Tên | Trạng thái | Gate | Artefact |
|---|---|---|---|---|
| **W0** | Freeze + worktree inventory | ✅ XONG 16:27 | PASS | `docs/REPO_HYGIENE/WORKTREE_INVENTORY.{md,csv}` |
| **W1** | Admin-v3 reconcile | ✅ XONG 17:00 | PASS | `ADMIN_V3_RECONCILIATION.md` |
| **W2** | Local worktree cleanup | ✅ XONG 17:00 | PASS | `W2_LOCAL_WORKTREE_CLEANUP.md` |
| **00** | Campaign baseline | ✅ XONG 17:05 | PASS | tệp này, §Baseline |
| **01** | Hard delete contract | ✅ XONG 17:10 | PASS | `FINAL_AI_CONTRACT.md` |
| **02** | Forensic inventory | ✅ XONG 17:25 | **PASS — `INVESTIGATE = 0`** | `LEGACY_SURFACE_MATRIX.csv` · `OUTBOUND_EGRESS_MATRIX.csv` · `PRODUCT_DEPENDENCY_MAP.md` · `DELETE_DEPENDENCY_GRAPH.md` |
| **03** | Target mapping only | ✅ XONG 18:20 | PASS | `MIGRATION_MAP.md` |
| 04 | Block legacy execution (fail-closed) | ⬜ | — | — |
| 05 | Migrate TEXT/VLM → LTT_LLM | ⬜ | — | — |
| 06 | Migrate IMAGE → LTT_IMAGE | ⬜ | — | — |
| 07 | Delete all legacy runtime | ⬜ | — | — |
| 08 | Delete legacy app surfaces | ⬜ | — | — |
| 09 | Provider config / secret clean | ⬜ | — | — |
| 10 | Architecture guard | ⬜ | — | — |
| 11 | Real E2E | ⬜ | — | — |
| 12 | Forensic re-audit | ⬜ | — | — |
| 13 | Commit / merge / deploy | ⬜ | — | — |
| 14 | Remote GitHub hygiene | ⬜ | — | — |
| 15 | Final repo compaction report | ⬜ | — | — |

> ⏸️ **Chưa commit.** Artefact 6 pha đang nằm chưa commit trong cây chiến dịch —
> xem §"Trạng thái commit" cuối tệp.

## Baseline (pha 00)

| | |
|---|---|
| Nhánh | `phien/aiclean` |
| HEAD | `0d1ffe5a1c336d2a492354787757b94d1ad2c608` |
| Upstream | chưa đặt (cây riêng, gộp lại cây chính khi xong) |
| Hơn `origin/master` | 264 commit |
| Nền có chứa admin work đã chốt? | ✅ — cả 6 commit mới nhất của `admin-mvp-v3` đều là **tổ tiên** của HEAD, kể cả merge `phien/wf2` (`d83fb7f6`) |
| Đã đọc | `CLAUDE.md` · `docs/00_LTT_OPERATING_CONTRACT.md` · `AGENTS.md` §4c/§8 · `HARD_DELETE_POLICY.md` · `GIT_WORKTREE_REMOTE_POLICY.md` |

⚠️ **Nền KHÔNG chứa 43 tệp chưa commit của phiên VOICE** — `git worktree` phân
nhánh từ một *commit*. Đã kiểm: chiến dịch không chạm `apps/ltt_voice/**` nên
lượt merge ở pha 13 sẽ không xung đột.

## Kết quả pha 02 — 520 tệp, 11 nhãn, `INVESTIGATE = 0`

| Nhãn | Số tệp | Nghĩa |
|---|---|---|
| `DOC_ARCHIVE` | 242 | tài liệu — lưu trữ, gỡ phần *hướng dẫn sử dụng* còn hiệu lực |
| `TEST_UPDATE` | 97 | phép kiểm — đổi **cùng** changeset xoá |
| `NOT_A_LEGACY_SURFACE` | **54** | khớp mẫu nhưng **không phải** bề mặt legacy |
| `HISTORY_ONLY` | 51 | chỉ chú thích/chuỗi — trơ |
| `UI_DELETE` | 20 | bề mặt giao diện |
| `PRODUCT_MIGRATE` | 19 | giữ sản phẩm, thay động cơ |
| `CONFIG_DELETE` | 17 | cấu hình/bảng giá/mốc bánh cóc |
| `EXECUTION_DELETE` | **8** | đường chạy thật |
| `TOOLING_UPDATE` | 6 | công cụ quét theo tên thư mục |
| `CONTROL_PLANE_DELETE` | 4 | registry · api_pool · planner |
| `MIGRATION_ONLY` | 1 | migration đã chạy production |

### Ba kết luận đắt nhất của pha 02

1. **Chỉ có 8 lối ra mạng, và cả 8 đều là Gemini.** `api.openai.com`: **0**.
   `apiai.vn` và `cheapkeyai`: **0** — chúng chỉ còn trong `REGISTRY`, một
   docstring và một bảng màu admin. Bốn trong năm họ hầu như đã chết sẵn.

2. 🔴 **`openai`/`codex` trong kho này có HAI nghĩa ngược nhau.** Một là nhà
   cung cấp ta gọi ra (`codex_sidecar/runtime.py` — ChatGPT device-code OAuth),
   một là **giao thức ta nói** cho khách cắm vào (`llm_gateway/api.py` — cửa
   trước của **LTT_LLM**, động cơ nằm trong danh sách giữ sống). Một lượt xoá
   theo `grep` sẽ xoá cửa trước của chính động cơ được phép sống.

3. 🔴 **`platform_core/agent/planner.py:20` khai `PLANNER_PROVIDERS =
   ("ltt_llm", "gemini")`** — một fallback legacy **được thiết kế**, kích hoạt
   *khi máy B bận*, tức đi ra Gemini đúng lúc không ai nhìn.

### Hai dương tính giả — xoá theo máy là giết tính năng đang chạy

| Tệp | Máy thấy | Sự thật |
|---|---|---|
| `cutclipshort/adapters/whisper.py` | 12 dòng **mã** khớp `openai` | `openai-whisper` là gói pip **chạy cục bộ**, không có mạng |
| `apps/upscalevideo/**` | khớp `gemini` | *"BOT GEMINI"* là thư mục kho chỉ-đọc `D:\BOT GEMINI` |

## Ràng buộc mang theo suốt chiến dịch

- **Cấp test** (`00_LTT_OPERATING_CONTRACT.md` §4): vòng lặp **L1** (`gate --doi`);
  L2 khi chốt pha; **L3 chỉ ở checkpoint**. ⛔ Không `test_nhanh.py` rồi `gate.py`.
- 🔴 **Trước mọi lệnh nặng: kiểm HAI vế, không phải một.**
  `cua_so_yen trang-thai` là **điều kiện cần, không đủ** — đo 17:13 nó trả
  `RANH` trong khi **5 tiến trình `python -u -c` chạy ~100% CPU mỗi cái**
  (5/10 lõi vật lý, máy 50,5%). Worker `xdist` không mang từ khoá nào để
  `cua_so_yen` nhận ra. ⇒ **luôn đọc cây tiến trình sau khi hỏi khoá.**
  ⚠️ Lọc theo **tên tiến trình**, đừng `grep` chuỗi dòng lệnh — chuỗi đó tự khớp
  vào chính shell đang hỏi (đã giết nhầm shell **bốn lần** trong kho này).
- **§4.9:** nhắn kèm **giờ bắt đầu + thời lượng**, **chờ xác nhận**, rồi mới bấm.
  Luật đi cả hai chiều.
- 🔴 **Điều kiện thứ BA quanh một lượt gate** (phát hiện 08/09, chưa có trong
  hợp đồng): ngoài *"đừng dùng CPU"* và *"đừng ghi tệp"* còn **"đừng chạm tới
  git"**, và mục đầu danh sách đó là **`git commit`**.

  Cơ chế, đọc từ `pre_commit/staged_files_only.py::_unstaged_changes_cleared`
  (**không** phải `git stash` như tôi viết lúc đầu):

  ```
  git diff-index --binary <tree>  ->  ghi patch ra ~/.cache/pre-commit/
  _CHECKOUT_CMD                   ->  XOA sach phan unstaged khoi CAY
  ... chay hook ...
  git apply <patch>               ->  dap lai
  ```

  Vì `_anh_chup_cay()` chụp `(kích thước, mtime)`, một lượt commit làm **mọi**
  tệp unstaged đổi `mtime` dù nội dung y nguyên. **Đo được 08/09:** commit
  `0d1ffe5a` lúc 16:56:48 → 5 tệp unstaged của phiên VOICE đổi mtime lúc
  **16:56:49**. Trong cửa sổ L3, `git commit` không *"có thể"* chạm cây — nó
  **chắc chắn** chạm.

  ⭐ **Nhưng cả ba lệnh trên thao tác trên CÂY HIỆN TẠI.** Ca đo được là một
  commit **cùng cây** (`admin-mvp-v3` đang checkout ở chính `D:\LTTSTUDIOSAPP`,
  và WF2 commit vào đó). Nó **không** chứng minh commit ở cây khác cũng vậy —
  và theo mã nguồn thì không.

  🔑 ⇒ **Đường thoát không phải thêm một cửa sổ, mà là đứng ở cây khác.** Cửa sổ
  phải thương lượng lại mỗi lần và hỏng khi một bên quên; cây riêng thì hỏng
  không được. Đó là lý do chiến dịch này commit ở `phien/aiclean`.

- **Cửa sổ riêng thuộc về lượt MERGE ở pha 13, không phải lượt commit.**
  `codex_sidecar/` nằm **trong** `gate.THU_MUC_CHUP` (`tools/gate.py:1285`).
  Commit xoá nó ở cây riêng thì vô hại với phiên khác; nhưng **`git merge
  phien/aiclean` chạy ở cây chính** và làm cả một thư mục biến mất khỏi ảnh chụp
  của bất kỳ ai đang chạy gate ⇒ **xin cửa sổ cho lượt merge**, kèm giờ + thời
  lượng, chờ xác nhận.
- **`tools/gate.py` là tệp dùng chung** ⇒ `Edit`, không bao giờ `Write`.
- **Không** wipe GitHub, **không** xoá/force-push `master`. Remote hygiene = pha 14.
- **Ngoài phạm vi:** scheduler · priority · GPU fairness · runtime V2 · Public API V2.

## Câu treo từ pha 02 — ĐÃ ĐO Ở PHA 03

**Hỏi:** gỡ fallback Gemini của `planner` có biến thất bại thành **mặc định** không?

**Đáp: KHÔNG** — thất bại đã là mặc định sẵn. Đo 41.622 dòng log worker
production, cửa sổ 28 ngày (11/08 → 08/09): 38 job hỏng vì máy B bận
(38/3.435 lượt `ltt_llm.chat` ≈ **1,1%**), và thông điệp lỗi ghi nguyên văn
`khong provider nao phuc vu duoc: ltt_llm: ban` — **danh sách chỉ có `ltt_llm`**,
Gemini không hề nằm trong cascade của những lượt hỏng ấy.

⛔ **Nhưng số 0 của Gemini KHÔNG phải bằng chứng nó vô dụng.** Đối chứng:
`taoanh` chạy **2** lượt trong 28 ngày; `thumbnail`/`autosubvideo`/`taovideo`/
`prompt_ai_ommi` chạy **0**. Con số ấy đo **sự vắng mặt của người dùng**, không
đo sự vắng mặt của đường gọi. ⇒ **Rủi ro di trú 4 app kia là CHƯA ĐO**, pha 05/06
phải tự dựng phép đo, không được viện dẫn bảng này.

⚠️ Và một bẫy đếm đã tránh: 82 **dòng** log là **38 job** (một job chiếm 12
dòng vì thử lại). Đọc theo dòng thổi phồng tần suất hỏng **2,2 lần**.

🔑 **Thứ tự bắt buộc cho pha 05:** sửa **lỗi bí danh** `model_theo_provider={"ltt_llm":
"ltt_llm"}` **trước**, rồi mới gỡ Gemini — nếu không, mọi lượt đang lặng lẽ đi
Gemini sẽ thành lỗi ồn ào và bị quy sai thành *"LTT_LLM không đủ năng lực"*.

## Trạng thái commit

⏸️ **Chưa commit** tính tới 17:13. Lý do: phiên VOICE đang chạy `gate --doi`
(5 worker ~100% CPU), và một lượt `git commit` ở đây kéo theo `pre-commit` chạy
6 bánh cóc — vừa là **lệnh nặng**, vừa là **thao tác git**. Chờ họ báo xong.

⭐ Đây là lần thứ hai trong phiên mà `cua_so_yen` nói `RANH` còn máy thì không —
nên phép kiểm hai vế ở trên không phải lý thuyết.

## Nhật ký

- **W0** (16:24–16:34) — 8 worktree, 11 nhánh local, 0 commit unpushed lúc đo.
  Chủ dự án xác nhận **4 phiên còn sống** ⇒ `ACTIVE_WORKTREES` 3 → 4.
  Bài học: nhịp ghi tệp chứng minh **sự có mặt**, không chứng minh **sự vắng mặt**.
- **W1** (17:00) — 264 commit ahead; 6 commit chưa push, **cả 6 quy được chủ**;
  43 tệp chưa commit, **cả 43 quy được chủ**; 0 stash. `ADMIN_WORK_PRESERVED=YES`.
  Đọc lại gate W1: nó đòi việc **được bảo toàn và quy chủ**, không đòi **kết thúc**.
- **W2** (17:00) — tạo cây chiến dịch bằng `tools/cay_rieng.py` (quy ước kho
  thắng tên `architecture/ai-clean-rebuild` của pack). 3 cây `ARCHIVE_THEN_REMOVE`
  **chờ chủ dự án xác nhận**, không chờ thêm phép đo.
- **00/01** (17:05–17:10) — nền xác minh; hợp đồng xoá lập, kèm nhãn thứ tư
  `NOT_A_LEGACY_SURFACE` (sửa **phép đo**, không phải nới chính sách).
- **02** (17:25) — quét 3 lớp bằng `tokenize`; 520 tệp phân loại; `INVESTIGATE=0`.
