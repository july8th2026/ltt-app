# Plan vận hành — Workflow Platform V2, vòng hoàn thiện (25/09/2026)

> Nối tiếp `2026-09-24-wf-v2-MASTER.md` (13/14 phase, đã gộp `main`, deploy `2adecdb8`).
> Tệp này là **nguồn chân lý duy nhất** cho vòng hoàn thiện. ⛔ Tệp khác ghi khác là sai.

## 0. Quyết định đã khoá (chủ dự án, 25/09)

| # | Câu hỏi | Chốt |
|---|---|---|
| D1 | Phạm vi | **Mở lại toàn bộ prompt gốc** — không giữ bốn hoãn của 22/09 |
| D2 | Điều kiện XONG | **8 luồng A–H chạy thật trên PostgreSQL + diễn tập sự cố** (§57 + §53 prompt gốc) |
| D3 | Bộ node DATA | **YAGNI** — đo expression engine trước, chỉ thêm node khi đo thấy thiếu |
| D4 | ⭐ Tự xây | **KHÔNG tính năng nào được tự xây.** Không có nguồn cộng đồng ⇒ **loại khỏi plan**, ghi sổ nháp |
| D5 | Giấy phép | Chủ dự án xác nhận **dùng cá nhân/nội bộ**, **tự chịu trách nhiệm** |

### D4 áp thế nào — ranh giới, để sau khỏi cãi nhau

- **Tính năng** (node, trigger, sandbox, connector, cơ chế điều phối) ⇒ phải có nguồn ADOPT/ADAPT/PORT. Không có ⇒ loại.
- **Dây nối** (gọi route ta đã có từ UI ta đã có, dọn mã chết, render trường đã có dữ liệu) ⇒ **không phải tính năng**, vẫn làm.
- **Sửa lỗi theo tài liệu chính thức** (ví dụ `5xx` của Google) ⇒ không phải tự xây; tài liệu **là** nguồn.

### D5 — hệ quả giấy phép, viết ra để sau còn tìm lại

- Mã **Sustainable Use License** (n8n, phần **không** `.ee.`) được dùng và sửa cho mục đích cá nhân–nội bộ.
- ⛔ **Vẫn loại dù cá nhân**: `.ee.` của n8n và `packages/ee/` của Activepieces — đòi giấy phép Enterprise **trả tiền**, không có miễn trừ cá nhân.
- ⛔ **Loại**: Pipedream (Source Available, cấm SaaS), Inngest (SSPL), Windmill (AGPLv3 + cấm managed service).
- ⚠️ **Nếu sau này bán cho khách trả tiền**: mọi mã gốc SUL phải gỡ hoặc thay. Chỗ dùng ghi ở §2, cột "SUL".

## 1. Luật vận hành của riêng plan này

1. **Gate**: trong plan chỉ chạy **L1** (`gate.py --doi --tu <sha>`) hoặc **L2** (`gate.py --pham-vi <tp>`).
   ⛔ **Không L3** cho tới khi **hết plan**. ⛔ Không gate để đóng một phase.
2. **CPU** (luật 3 `CLAUDE.md`): trước mọi lệnh nặng chạy `python tools/cua_so_yen.py trang-thai` (có người giữ ⇒ **chờ**) và `python tools/tai_may.py` (`QUÁ TẢI` ⇒ **chờ**).
   Agent đi qua `chay_nang.py --phien <làn> <lệnh>`, `-n` ≤ `gate.TRAN_N_GO_TAY` (đọc hằng số, ⛔ đừng gõ lại số).
   ⭐ **Nhả khoá ngay khi tính xong** — đọc kết quả, sửa mã, `git commit`, viết báo cáo đều làm **ngoài** khoá.
3. **Làn** = một worktree + một nhánh `phien/wfv2-<làn>`. ⛔ Hai làn không sửa cùng một tệp.
4. **Dải số test của plan: `4100`–`4199`.** Khai ở đây vì kho **chưa có sổ dải** — `check_so_test.py` suy từ số đã dùng, ⛔ không giữ chỗ (đã va nhau 2 lần trong 2 ngày). Cao nhất hiện tại `3801`; `4000`–`4003` thuộc làn VPS.
5. ⛔ **Không agent nào chạy `tools/gate.py`.** Chỉ điều phối chạy.
6. ⛔ **Không hạ mốc bánh cóc bằng `--update`** để cho xanh.

## 2. Ma trận nguồn — lấy từ đâu, giấy phép gì

| Hạng mục | Nguồn | Đường dẫn | Giấy phép | SUL? |
|---|---|---|---|---|
| Trigger POLLING + chống trùng | Activepieces | `packages/pieces/common/src/lib/polling/` (`pollingHelper`, `DedupeStrategy{TIMEBASED,LAST_ITEM}`) | MIT | — |
| Trigger Drive / Notion / Gmail | Activepieces | `packages/pieces/community/{google-drive,notion,gmail}` — đều POLLING | MIT | — |
| Trigger GitHub / Sheets | Activepieces | WEBHOOK tự đăng ký qua `context.webhookUrl` | MIT | — |
| Thuộc tính động (`values:DYNAMIC`) | Activepieces | `packages/pieces/framework` | MIT | — |
| Waitpoint chờ sự kiện cấp node | Kestra · Trigger.dev | `plugin/core/flow/Pause.java` · `packages/trigger-sdk/src/v3/wait.ts` | Apache-2.0 | — |
| Luật chờ (thay cho node Merge) | Airflow | `airflow/task/trigger_rule.py` — `TriggerRule` | Apache-2.0 | — |
| Gộp nhánh ba chế độ | Node-RED | node `join` | Apache-2.0 | — |
| Error handler trong cùng đồ thị | Kestra · Node-RED | khối `errors:` · node `catch` | Apache-2.0 | — |
| Dry-run | Dagster | `ResourceDefinition.mock_resource()` | Apache-2.0 | — |
| Marketplace / cài node lúc chạy | Node-RED · Activepieces | Palette Manager + Admin API · `piece-install-service.ts` | Apache-2.0 / MIT | — |
| Code Node | Activepieces | `packages/server/sandbox/src/lib/sandbox.ts` (fork tiến trình + `isolated-vm`) | MIT | — |
| Kiểu cổng `table` | Langflow | `src/lfx/src/lfx/schema/dataframe.py` | MIT | — |
| Playwright cho canvas | xyflow | `tests/playwright/e2e/{nodes,pane}.spec.ts` | MIT | — |
| Backoff · diff · xem JSON | `tenacity` · `deepdiff` + `jsondiffpatch` · `@uiw/react-json-view` | PyPI / npm | Apache-2.0 / MIT | — |
| Action bổ sung (⛔ không phải trigger) | MCP | SDK Python `mcp` · `github/github-mcp-server` | MIT | — |
| Sửa `5xx` upload | Google | tài liệu resumable upload chính thức | — | — |
| Webhook Response · Vision (dạng resource) | n8n | `nodes/RespondToWebhook/` · `nodes/OpenAi/ImageDescription.ts` | Sustainable Use | ⚠️ **CÓ** |

⚠️ **Dòng cuối là chỗ DUY NHẤT dùng mã SUL.** Đổi sang bán thương mại thì đúng chỗ đó phải gỡ hoặc thay.

### ⛔ MCP không thay được lớp trigger

MCP là **client-initiated/pull**; `resources/subscribe` chỉ chạy khi client giữ một phiên kết nối sống. Nó làm **đầu RA** (gọi tool khi workflow đã chạy), ⛔ không làm **đầu VÀO** (không đánh thức một run đang chờ). Lớp trigger vẫn là piece Activepieces + `cronsim`.

Độ phủ MCP không đều, ghi ra để khỏi kỳ vọng sai: **GitHub** chính chủ MIT đang bảo trì tốt · **Notion** chính chủ nhưng đã ngừng bảo trì tích cực · **Slack/Drive/GitLab đã archive** · **Google Workspace** không có bản chính chủ.

## 3. LOẠI khỏi plan — và vì sao

| Việc | Lý do loại |
|---|---|
| Connector Pipedream | *"Source Available License v1.0"* cấm dùng thương mại / làm SaaS |
| Mã Inngest | SSPL — buộc mở toàn bộ mã dịch vụ nếu chạy as-a-service |
| Mã Windmill | AGPLv3 + Community Edition cấm resell/managed service |
| Evaluator của n8n | `.ee.` — đòi Enterprise trả tiền, ⛔ không có miễn trừ cá nhân |
| Slack trigger thời gian thực | APP_WEBHOOK cần app Slack cấp nền tảng; thượng nguồn ghi *"not supported"* cho bên ngoài |

### Sổ nháp — nghiên cứu sau, ⛔ không làm trong plan này

- **StackStorm-Exchange** (Apache-2.0, ~160 pack, 6000+ action) — nguồn thoáng nhất đã tra, nhưng lấy nó là dựng **runtime connector thứ hai** (Python). Đụng luật "⛔ không engine thứ hai".
- **nsjail** (Windmill) — dùng namespace Linux, ⛔ không map sang AppContainer của Windows.
- **Node Start · node Retry** — không tồn tại ở nền tảng nào. Khởi động là ngầm định; retry là **tham số per-node** — đúng thứ ta đang làm.
- **`while` / `break` / `continue`** — cả ba nền tảng đều không có; đều dùng ngữ nghĩa for-each, thứ ta **đã có**.
- **4 trạng thái Draft/Validated/Published/Archived** — thượng nguồn chỉ có `{DRAFT, LOCKED}` + `publishedVersionId`; mô hình ta **đã cùng hình dạng**. ⇒ ⛔ Không phải lỗ hổng, không làm.

## 3b. ✅ KẾT QUẢ — 4/4 plan đóng (25/09 tối)

| Plan | Làn | Kết quả |
|---|---|---|
| **P-A** | `wfa` `wfb3` | Nối `chay-lai-tu`/`so-sanh`/`soan` lên UI; **Playwright bấm thật** trên cổng 8199, `pageErrors == 0` |
| **P-B** | `wfb1` `wfb2` `wfb4` `wfb5` | `5xx` YouTube theo tài liệu Google · FLOW D trigger POLLING thật · FLOW G **gọi model thật** · cổng biểu thức §6 |
| **P-C** | `wfc` | Catalog **4→7 piece, 17→32 node**, hết `bo_qua` |
| **P-D** | `wfd` `wfd2` `wfm` | Sandbox hai lớp + **7 diễn tập thoát vỏ** · node `core.code` · marketplace + cổng duyệt fail-closed |
| *(phát sinh)* | `wfn` `wfk` `wft` `wfp` `wfg` | Bước cài `connector_runner` · `/soan` sập trình soạn · sổ trigger tất định · publish `piece.*` · báo giá `ai.*` |

**17 làn đã gộp `main`. 30+ phép kiểm mới** (dải 4100–4299). Alembic một head.

⚠️ **Ba mục LOẠI, đã ghi ở §3** — không phải quên: Pipedream (giấy phép) · Inngest (SSPL) ·
Windmill (AGPLv3) · Evaluator n8n (`.ee.`) · Slack APP_WEBHOOK.

⚠️ **Còn nợ, ⛔ không thuộc plan này:** nghiệm thu upload YouTube thật (chặn vì không
đăng nhập được) · xoay client secret Google + mật khẩu superuser PostgreSQL · hai
khiếm khuyết deploy còn lại · khoá cây chính · sổ dải số test · ~~phát hiện `node_modules` cũ hơn khai báo~~ ✅ **ĐÃ TRẢ** (`abc27c2e`): bước gate `phu thuoc npm da cai` + `tools/check_phu_thuoc_npm.py` + `test_4107`. Hỏi chính `npm ls --json` (đọc `problems`), phạm vi từ `git ls-files`, tập miễn trừ `CHUA_CAI` **chỉ được co lại**, và in thẳng `cd <thư mục> && npm ci`. ⭐ Tiêm lỗi dựng lại đúng ca `jsondiffpatch` ⇒ đỏ đúng chỗ. ⚠️ Lược đồ CSDL thì đã có `do_migration_tren_postgres.py` canh từ trước.

---

## 4. Bốn plan — thứ tự và điều kiện ra

| Plan | Nội dung | Điều kiện ra |
|---|---|---|
| **P-A** Nối dây | `chay-lai-tu` · `so-sanh` · `/soan` lên UI; bổ sung trường quan sát; dọn mã chết | Bấm được thật trên `https://app.lttstudios.com`; Playwright xanh |
| **P-B** Đóng điều kiện XONG | Sửa `5xx`; FLOW D thật bằng trigger POLLING; FLOW G thật; Playwright canvas; test đua callback-trước-WAITING | A–H **thật trên PostgreSQL** + diễn tập sự cố (§53) |
| **P-C** Mở connector | Port `pollingHelper` + ánh xạ thuộc tính động; mở Drive/Notion/Gmail/GitHub | ≥ 1 trigger poll thật chạy end-to-end |
| **P-D** Code Node + Marketplace | Port sandbox hai lớp đặt trong AppContainer sẵn có; cài piece lúc chạy | Diễn tập thoát sandbox **thất bại có đối chứng** |

⛔ **P-D không mở trước khi P-B xanh** — prompt gốc §33 cấm đưa Code Node vào sớm khi sandbox chưa hoàn thành.

## 5. Mức task — chỉ mở cho P-A

Cây `D:/LTTSTUDIOSAPP-wfa` · nhánh `phien/wfv2-a` · dải test `4100`–`4119`.

| # | Task | Tệp sửa | Test |
|---|---|---|---|
| A1 | Gọi `POST /api/v3/runs/{id}/chay-lai-tu/{node_id}` từ panel lượt chạy | `frontend/agent-canvas/src/workflowApi.ts`, `RunV3Panel.tsx` | `test_4100` |
| A2 | Gọi `GET /api/v3/runs/{id}/so-sanh`, hiện diff bằng `jsondiffpatch` | `workflowApi.ts`, `RunDiff.tsx` (mới) | `test_4101` |
| A3 | Gọi `POST /api/v3/workflows/{id}/soan` (Agent Designer) từ CanvasShell | `CanvasShell.tsx`, `workflowApi.ts` | `test_4102` |
| A4 | Render trường quan sát **đã có dữ liệu**: bắt đầu/kết thúc, thời lượng, `attempt` | `RunV3Panel.tsx` | `test_4103` |
| A5 | Inspector cho lượt chạy: input/output/log qua `@uiw/react-json-view` | panel mới | `test_4104` |
| A6 | Dọn mã chết v2 trong `workflowApi.ts` (`runAgain`, `restoreRunAsWorkflow`, `createRun`, `approveRun`…) | `workflowApi.ts` | bánh cóc `test_4105` |

⭐ A6 chốt theo **tập hợp** hàm còn sống, ⛔ không theo **số lượng** — đếm thì xoá cũng xanh.

⚠️ A1–A5 là **dây nối**, ⛔ không phải tính năng mới: route + test phía máy chủ đã có từ P9b/P10, frontend chưa từng gọi (grep rỗng). Đây là lý do P-A đứng đầu — nó biến việc **đã trả tiền** thành việc **dùng được**.

## 6. Nợ vận hành ngoài plan (⛔ không trộn vào P-A..P-D)

1. **Ba bánh cóc đỏ trên `main`** — `check_silent_except` 73/mốc 51, `check_mypy` (index, operator, union-attr), `check_bo_qua`.
   ⭐ Đo bằng **tập HIỆU** so với SHA xanh cuối (`84daefd8`), ⛔ không bằng tập hiện tại: cả 22 chỗ tăng thuộc vùng ASV (`tools/bench_b2_*` 18 · `bench_gpu_may_a` 1 · `whisperx_runner` 2 · `quan_sat` 1). `server/templating.py` (13 chỗ) **không** thuộc phần tăng — nó đã nằm trong mốc cũ.
2. **Sổ dải số test** — `cay_rieng.py` suy dải từ ảnh chụp, ⛔ không giữ chỗ. Va 2 lần trong 2 ngày (2920–2923, 3500–3503). Thuốc: **ghi dải đã cấp vào một tệp trong kho** — biến một **suy diễn** thành một **bản khai**.
3. ~~**Khoá cây chính**~~ ✅ **ĐÃ TRẢ** (bước D `fe4a70d8`+`e337a712`, bước A phiên này) — và trả **khác** cách đặt vấn đề ban đầu.
   ⭐ Đo lại trước khi làm: ⛔ **không phải một** tranh chấp mà **bốn chiều độc lập** — nội dung cây (×2: người khác gộp giữa lượt) · sổ ref (`cannot lock ref 'HEAD'`) · HEAD/nhánh (×2: một lượt gộp *mang theo* commit phiên thứ ba; một commit **đi lạc nhánh** mà ⛔ không ai thấy) · index (tệp đang staged của phiên khác chặn gộp). **Sáu** lần va, ⛔ không phải hai.
   ⇒ Một khoá `cay_chinh` là hình dạng **sai**: khoá tuần tự hoá việc **TÍNH**, còn đây là tranh chấp về **CHỖ ĐỨNG**. Đổi chỗ đứng thì tranh chấp **mất hẳn**, ⛔ không phải xếp hàng — `git merge` 3 giây của phiên khác ⛔ không còn phải chờ một lượt gate 20 phút.
   - **A. `tools/cay_gate.py`** — dựng/làm mới worktree gate **NGOÀI kho**, `--detach` ở tip `main`, rồi chạy `gate.py` ở đó. `gate.py` đã dùng `ROOT = Path(__file__).parent.parent` ⇒ ⛔ **không cần sửa `gate.py`**. Nó đo **`main` ĐÃ COMMIT** ⇒ miễn nhiễm **cả hai** thứ từng làm bẩn phán quyết, kể cả ca *"`main` cộng 8 tệp chưa commit của phiên khác"* — mà nếu ca ấy XANH thì còn tệ hơn, vì ⛔ không ai đi điều tra một lượt xanh. `test_4109` tiêm lỗi 3 chỗ.
   - **D. `tools/check_worktree_trong_kho.py`** + bước gate — worktree **trong** kho thổi mọi bánh cóc gấp đôi (`LTTGateBaseline68cde0`). ⭐ Luật thật cần **CẢ HAI** vế (gitignored **và** máy quét đã loại), vì công cụ tôn trọng gitignore và công cụ quét hệ tệp mù theo hai kiểu khác nhau. `test_4108` dùng bảng chân lý 4 ô, 3 ô phải đỏ.
   - **B** hoá ra ⛔ không cần sửa gì (`gate.py` tự đo cây nó nằm trong). **C** bỏ — chỉ là tài liệu, đã nằm ở `docs/QUY_TRINH_WORKTREE.md §3`.
   - ⚠️ **Nợ con còn lại**: chiều **commit đi lạc nhánh** vẫn chưa có ai canh. Nó ⛔ không thuộc cây gate (cây gate `--detach`, ⛔ không commit) và một lớp canh sẽ đổi hành vi `git commit` của **mọi** phiên ⇒ chờ chủ dự án chốt.
   - ⚠️ **Cái giá đã đo**: cây gate mới thiếu `node_modules` (untracked) — `connector_runner` 18 gói, `frontend/agent-canvas` 30. ⭐ Hoá ra là **lãi**: `npm ci` từ đúng lock đã commit đo được cả câu *"lock này có cài được không"* — đúng hình dạng ca `isolated-vm`/`jsondiffpatch`. `npm ci` là **lệnh nặng** ⇒ đi qua `chay_nang.py`, và phải xin tường minh `--cai-npm`.
4. **Hai khiếm khuyết đường deploy** — phép kiểm đặt **sau** điểm không quay lại; `pip install` chạy khi dịch vụ đã dừng.
5. **Xoay bí mật** — client secret Google và mật khẩu superuser PostgreSQL.
