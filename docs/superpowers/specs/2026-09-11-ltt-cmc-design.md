# LTT-CMC — Thiết kế hợp nhất lịch sử chuẩn

**Ngày khóa thiết kế:** 2026-09-11  
**Trạng thái:** Đã duyệt để triển khai  
**Phạm vi:** Git topology, semantic deduplication, migration/registry/runtime normalization và chính sách worktree  
**Ngoài phạm vi:** triển khai production; thay đổi nội dung trong các worktree phiên đang tạm dừng trước CMC sync barrier

## Mục tiêu và quyết định đã khóa

LTT-CMC tạo một lịch sử chuẩn có thể chứng nhận từ trạng thái repository hiện
tại, bảo toàn năng lực hợp lệ nhưng không phát lại patch trùng, không phục hồi
kiến trúc đã bị loại bỏ và không để nhiều branch/worktree trở thành các nguồn
chân lý cạnh tranh.

Decision Board đã khóa:

| Câu | Quyết định |
|---|---|
| Q1 | Tạo nhánh chuẩn mới, tên `main`. |
| Q2 | Để các phiên Claude hoàn tất phạm vi của chúng, rồi tự reconcile với một `CMC_BASE_SHA` bất biến. |
| Q3 | Chỉ giữ một đường lịch sử chuẩn; không phát lại commit patch-equivalent. |
| Q4 | Chọn implementation chuẩn bằng bằng chứng, migrate caller, rồi mới bỏ bản lỗi thời. |
| Q5 | Reconcile commit local-only có giá trị vào lịch sử chuẩn. |
| Q6 | Backup có kiểm chứng, phân loại rồi reconcile dirty/untracked trạng thái. |
| Q7 | Sau chứng nhận, xóa branch đã merge/bị thay thế; không giữ branch/ref backup. |
| Q8 | Sau tích hợp, xóa mọi linked worktree đã nghỉ; chỉ giữ main worktree. |
| Q9 | Giữ session state cần cho đối chiếu, rồi xóa trạng thái phiên cũ sau Git cleanup. |
| Q10 | Chứng nhận source trước; production deployment là gate riêng. |
| Q11 | Xóa bundle/archive phục hồi tạm ngay sau khi chứng nhận thành công. |
| Q12 | Chỉ `main` tồn tại dài hạn; task branch/worktree là tạm thời. |

Phương án đã chọn là **Conservative Sequential Reconciliation**: xử lý từng
capability/branch, semantic dedup ở mỗi checkpoint và không bulk-merge lịch sử
cũ.

## Bằng chứng nền tại Design Freeze

- Main worktree hiện sạch trên `admin-mvp-v3` tại `34b4626e24e5`; lineage này
  đi trước `master` cũ khoảng 450 commit và chứa commit production hiện hành.
- Có 13 linked worktree; hai detached worktree và nhiều branch không có
  upstream ổn định.
- Topology/ref đã thay đổi trong lúc audit chỉ-đọc. Vì vậy mọi thao tác sau này
  phải bắt đầu bằng một snapshot duy nhất sau khi writer đã yên.
- Voice reconciliation có 20 commit riêng và dirty state được quan sát sau khi
  phiên kết thúc ở giao diện.
- LLM multijob có 9 commit riêng cùng 5 file dirty. Recovery dual-model không
  có commit implementation riêng nhưng có tài liệu chưa track; patch WIP của
  nó trùng chính xác với live dirty diff của multijob.
- `56dfc811` và `598108be` patch-equivalent với lineage nền; `3eb68e12` là ứng
  viên riêng cần semantic review.
- Có 26 commit chỉ còn được reflog giữ. Không được chạy `gc`/`prune` trước khi
  phân loại và hoàn tất chứng nhận.
- Ghép thẳng canonical + Voice + LLM tạo ba Alembic head. Không có collision
  revision ID hay schema-intent duplicate, nhưng ancestry phải được chuẩn hóa.
- Frontend bundles hiện pass freshness verification; không có orphan hashed
  assets trong bốn output đã kiểm.

## 1. Canonical topology

`main` là nhánh chuẩn mới và là branch dài hạn duy nhất sau LTT-CMC. Nó được
tạo từ một SHA đã ghim của lineage `admin-mvp-v3`, không từ `master` cũ và
không dựng lại 450 commit từ đầu.

Trong chiến dịch chỉ dùng main worktree hiện tại tại `D:\LTTSTUDIOSAPP`; không
tạo thêm worktree cho LTT-CMC. Trước khi tạo `main`, phải kiểm tra lại topology,
dirty state, remote state và writer để bảo đảm SHA nền không di chuyển giữa
hai phép đo.

Sau chứng nhận, remote default branch và branch protection chuyển sang `main`.
`master` và `admin-mvp-v3` trở thành lineage bị thay thế và chỉ được xóa sau
khi mọi reference vận hành/tài liệu/CI đã chuyển sang `main`.

## 2. Active-session protection

Ba worktree sau mang nhãn `SESSION_PROTECTED` cho đến CMC sync barrier:

| Workstream | Worktree | Trạng thái thiết kế |
|---|---|---|
| Voice | `.claude/worktrees/ltt-4bot-workflow-app-550cab` | Không commit, switch, rebase, merge, reset, clean hay sửa từ CMC. |
| LLM dual-model recovery | `.claude/worktrees/ltt-video-architecture-recovery-746b24` | Không đụng tài liệu untracked/spec đang dở. |
| LLM multijob predecessor | `.claude/worktrees/ltt-llm-api-http-guide-a3e123` | Không đụng 9 commit và 5 file dirty. |

Hai worktree LLM là một semantic workstream; recovery patch là bằng chứng phục
hồi của dirty multijob diff, không phải implementation thứ hai.

Phiên đã đóng trong UI nhưng tiến trình nền từng còn sống và file/ref từng tiếp tục
thay đổi. Trước backup hoặc reconciliation phải chứng minh quiescence bằng
quan hệ tiến trình/worktree và hai snapshot Git ổn định; không suy từ tên phiên
hay nhãn tiến trình. CMC không tự kill writer.

Trước mọi lệnh nặng phải chạy cả:

```powershell
python tools\tai_may.py
python tools\cua_so_yen.py trang-thai
```

`QUÁ TẢI` thì không chạy; `BẬN` thì hoãn hoặc dùng kiểm tra hẹp. Hai phép đo
trả lời hai câu khác nhau và không thay thế cho nhau.

## 3. Commit và branch reconciliation

Mỗi completed branch/capability ngoài `SESSION_PROTECTED` được xử lý tuần tự:

1. đã tồn tại trong `main` thì bỏ qua;
2. khác SHA nhưng patch-equivalent thì ghi bằng chứng và không replay;
3. capability riêng còn hợp lệ thì port tối thiểu lên code hiện tại;
4. implementation đã bị thay thế hoặc phục hồi kiến trúc cũ thì loại;
5. trường hợp không đủ bằng chứng thì giữ ngoài canonical candidate và ghi
   blocker, không đoán.

Không bulk merge, không chọn nguyên nhánh bằng `ours`/`theirs`, không chép
nguyên file từ lineage cũ. Commit port phải ghi source commit/branch để audit
được nhưng chỉ tạo một canonical path.

Commit reflog-only có giá trị được gắn ref cứu hộ tạm trước khi hết hạn. Ref
này không phải branch vận hành và bị xóa theo Cleanup sau chứng nhận.

## 4. Semantic dedup strategy

Đơn vị quyết định là **capability và authority**, không phải filename hay SHA.
Mỗi ứng viên được phân loại bằng taxonomy:

- `COMMIT_DUPLICATE`: cùng patch/capability; chỉ giữ canonical path.
- `FILE_DUPLICATE`: xác định source và derived/mirror lifecycle.
- `SEMANTIC_DUPLICATE`: chọn một authority, migrate caller, rồi bỏ bản cũ.
- `MIGRATION_DUPLICATE`: chuẩn hóa graph mà không làm mất schema intent.
- `REGISTRY_DUPLICATE`: một slug/route/job/tool/table chỉ có một owner.
- `RULE_DOC_DUPLICATE`: chỉ một tài liệu có quyền quy định; nơi khác trỏ tới nó.
- `ARCHIVE_ONLY`: bằng chứng phục hồi, không được import vào runtime.
- `MERGE_CAPABILITIES`: hai thay đổi bổ sung nhau, phải port có chủ ý.

Các quyết định semantic đã biết:

- Giữ `platform_core/llm/canonical.py` làm authority alias; hợp nhất model
  profile để provider capability, budgeting, manifest và warning cùng dẫn xuất
  từ một nguồn.
- Generalize `admission_token_pool` từ scalar toàn cục thành resource/pool theo
  model; giữ nền multijob nhưng áp dụng quyết định dual-model mới.
- Dirty T9 giữ centralized wait policy và job reservation, nhưng phần “không
  chờ” bị supersede bởi D04: chờ tối đa 60 giây sau idempotency commit.
- Job scheduler và LLM admission queue có boundary khác nhau; tài liệu hóa để
  không một item bị rank bởi cả hai.
- Không phục hồi `chataistudio` hay socialbot đã tombstone/remove.
- Giữ provider tombstone fail-closed; không xem chúng là live duplicate.
- Workflow v3 thay thế legacy workflow theo migrate-callers-then-drop, không
  xóa trước khi có bằng chứng data/route/link migration.

## 5. Backup và rollback

Backup chỉ là hàng rào tạm trong cửa sổ CMC, không phải nguồn làm việc thứ hai.
Trước thao tác làm thay đổi lịch sử hoặc dọn dẹp:

- tạo bundle/ref tạm cho commit reachable/reflog được chọn;
- lưu patch nhị phân/an toàn cho dirty tracked state;
- lưu inventory + hash cho untracked artifacts;
- ghi branch, HEAD, merge-base, status và hash vào manifest không chứa secret;
- verify bundle/patch/hash bằng phép đọc độc lập.

Rollback trước certification là khôi phục từ manifest đã verify về checkpoint
gần nhất. Không overwrite worktree đang dirty để rollback.

Sau full certification thành công và trước khi kết thúc Cleanup, toàn bộ
bundle, ref và archive tạm bị xóa theo Q7/Q11. Sau thời điểm đó rollback là một
commit mới trên `main`, không phải phục hồi branch lịch sử cũ.

## 6. Migration normalization

Canonical candidate phải có đúng một Alembic head, không duplicate revision ID,
không missing parent và không mất schema intent.

Trước khi đổi `down_revision`, phải đọc applied revision ở mọi môi trường liên
quan. Nếu một branch revision từng được apply, không rewrite ancestry; tạo
merge/forward migration rõ ràng. Chỉ reparent migration khi có bằng chứng nó
chưa từng được apply ở bất kỳ môi trường nào.

Voice và LLM migrations được port theo thứ tự trên canonical head. Thay đổi
comment/docstring trong migration lịch sử không được mang sang; giữ canonical
bytes và chuyển giải thích sang tài liệu sống.

Sau mỗi normalization phải kiểm cả graph tĩnh lẫn upgrade/restore path theo
gate phù hợp. Production database không bị mutate trong CMC source phase.

## 7. Registry và runtime normalization

Mỗi app slug, route prefix, ToolSpec name, job type, table prefix và table name
có một owner. Existing registry guards được giữ và bổ sung guard khi thiết kế
hai public model resources có thể gây alias collision.

Các normalization đã xác định:

- thống nhất model profile và derived metadata;
- chọn một giá trị retry cho mỗi job type và khai báo tại manifest thay vì
  hard-code khác nhau theo entry door;
- xác định ranh giới ToolSpec V2 `resource`/`timeout_expr` với AppManifest cũ,
  migrate toàn bộ caller trước khi bỏ field;
- giữ lớp platform GPU lease và machine-wide claim vì chúng khác scope;
- machine A là business/admission authority, machine B chỉ residency/drain
  executor fail-closed, định danh GPU bằng UUID/PCI;
- giữ platform storage, workflow artifact metadata, render transport và cache
  app theo scope riêng; không gộp chỉ vì cùng mang tên storage;
- worker capability vocabulary vẫn mở nhưng phải có kiểm tra deployment pool
  cho mọi lane cần thiết.

Không thay thế toàn bộ registry/model file từ LLM lineage cũ vì nó thiếu nhiều
app và ToolSpec V2/scheduler capability hiện hành.

## 8. Generated/frontend normalization

Bundle hiện đang fresh nên không rebuild chỉ để tạo churn. Khi source/frontend
test thật sự thay đổi, build release phải là bước cuối ngay trước full gate.

`messages.po` là source; `.mo` là output dẫn xuất và phải regenerate, không
binary-merge. `server/static/ltt.css` và `tools/gui/ltt.css` hiện là intentional
mirror: chọn một source lifecycle và sinh/copy deterministic sang consumer,
hoặc nếu chưa đổi contract thì luôn cập nhật/verify cả hai atomically.

`build-meta.json`, source hash, Node version, manifest asset references và
orphan assets phải được verify. Ignored cache/tsbuildinfo không được nhập vào
canonical history. Stale generated asset chỉ bị xóa khi source và consumer
mapping đã chứng minh nó không còn được dùng.

## 9. CMC synchronization barrier

Phase 1 chỉ xử lý governance, completed histories và duplicate độc lập với
`SESSION_PROTECTED`. Khi canonical candidate ổn định, ghi:

```text
CMC_BASE_BRANCH: main
CMC_BASE_SHA: <immutable SHA>
CMC_BASE_WORKTREE: D:\LTTSTUDIOSAPP
```

`CMC_BASE_SHA` không di chuyển trong thời gian hai workstream tự reconcile.
Branch name không được dùng thay SHA. Tại barrier không xóa branch/worktree,
không purge session, không prune và không final-cleanup.

Barrier report phải chứa trạng thái thật của canonical candidate, cả ba
protected worktree, pending reconciliation, proposed deletions và known risks.

## 10. Active-session self-reconciliation protocol

Tại barrier tạo hai handoff prompt đã điền đầy đủ, không placeholder:

- **Prompt A — Voice:** actual worktree, branch, HEAD, dirty state,
  `CMC_BASE_SHA`, canonical path, 20 commit riêng, migration Voice và các shared
  paths (`ltt.css`, locale, lint/gate/governance tools) cần semantic merge.
- **Prompt B — LLM dual-model:** actual Recovery + Multijob worktrees, hai
  branch/HEAD, dirty/untracked state, `CMC_BASE_SHA`, 9 commit nền, WIP patch
  duplicate, model/admission/migration/registry conflicts và quyết định D04.

Mỗi phiên khi được mở lại phải:

1. đọc canonical docs và handoff;
2. kiểm tra status, xác HEAD và hash bằng chứng còn khớp;
3. hoàn tất/commit phạm vi riêng trên branch hiện hữu;
4. tạo integration branch từ đúng `CMC_BASE_SHA` trong chính worktree của nó
   sau khi worktree đã sạch;
5. port capability bằng semantic diff, không merge nguyên lineage cũ;
6. chạy test phạm vi theo Operating Contract;
7. báo integration branch/HEAD, test thật, unresolved conflicts và danh sách
   source commit đã giữ/bỏ.

Phiên không được merge vào `main`, đổi baseline, xóa branch/worktree hay deploy.

## 11. Final integration

Sau khi cả hai handoff hoàn tất, CMC kiểm tra SHA nền và evidence manifests.
Voice được tích hợp trước vì lineage gần canonical hơn; LLM dual-model được
tích hợp sau bằng semantic port trên trạng thái đã có Voice.

Mỗi lần tích hợp phải:

- review commit/capability matrix;
- kiểm migration graph và registry ownership;
- chạy test thay đổi ở L1/L2 theo Operating Contract;
- giữ `main` thành một authority duy nhất;
- không xóa nguồn cho đến final certification.

Checkpoint cuối chạy secret scan, frontend build nếu cần và đúng một full
`python tools\gate.py` sau khi hai phép đo tải/khóa cho phép. Nếu đỏ do cách ly
hoặc tải, dùng bằng chứng và hồ sơ `--noi-tiep` theo Operating Contract; không
đổi tiêu chí hoàn thành.

## 12. Master promotion

Theo Q1-C, **không promote canonical lineage vào `master`**. Mục này trở thành
quy trình chuyển vai trò mặc định sang `main`:

1. chứng nhận `main`;
2. đổi mọi tài liệu, CI, script, protection và integration target sang `main`;
3. đổi remote default branch sang `main`;
4. xác minh clone/checkouts mới dùng `main`;
5. chỉ sau đó đánh dấu `master` và `admin-mvp-v3` là superseded để Cleanup.

Việc chuyển default branch là thay đổi repository host, không phải deployment
production. Production vẫn tuân Q10 và cần gate/ủy quyền riêng.

## 13. Cleanup

Trước Cleanup phải trình bảng cuối và xin phê duyệt destructive action riêng:

```text
WORKTREES: PATH | BRANCH | HEAD | STATUS | INTEGRATED | DELETE
BRANCHES:  NAME | HEAD | CANONICAL/PATCH-EQUIVALENT/SUPERSEDED | DELETE
BACKUPS:   PATH/REF | VERIFIED | PURPOSE | DELETE
SESSIONS:  ID/PATH | GIT HANDOFF COMPLETE | DELETE
```

Chỉ xóa khi `main` đã full-gate xanh, evidence manifest chứng minh capability
đã canonicalize, remote default/protection đã chuyển và production không phụ
thuộc branch/path bị xóa.

Cleanup xóa:

- mọi merged/superseded task branch local và remote;
- `master` và `admin-mvp-v3` sau khi bị thay thế hoàn toàn;
- mọi retired linked worktree;
- Claude session/worktree state cũ đã handoff;
- temporary bundle/ref/archive/patch backup của CMC.

Không giữ bản sao dài hạn. Không dùng filesystem delete thay `git worktree
remove` khi worktree còn được Git quản lý. Không prune object database cho đến
khi bảng cleanup đã xác minh và phê duyệt xong.

## 14. Post-CMC worktree policy

- `main` là branch dài hạn và canonical integration target duy nhất.
- Main worktree là `D:\LTTSTUDIOSAPP`.
- Mỗi task dùng một branch/worktree tạm có owner, scope và thời hạn rõ.
- Một worktree chỉ checkout một task branch; không làm việc trên detached HEAD
  trừ chẩn đoán read-only có chủ ý.
- Task phải tự reconcile với SHA canonical đã ghim trước handoff.
- Sau merge + verification, xóa task worktree và branch trong cùng chu kỳ;
  không biến worktree thành kho lưu trữ.
- Tài liệu quy trình chỉ có một authority cho test cadence và một authority cho
  worktree lifecycle; tài liệu khác liên kết thay vì sao chép quy tắc.
- Mọi thay đổi shared infrastructure tuân ba câu hỏi trong `AGENTS.md` §4c và
  có behavioral/mutation evidence phù hợp.

## Tiêu chí hoàn thành thiết kế

Thiết kế được coi là thực thi xong chỉ khi:

1. `main` là remote default và canonical branch duy nhất;
2. toàn bộ capability hợp lệ đã được reconcile đúng một lần;
3. Alembic có một head và upgrade/restore evidence xanh;
4. registry/runtime có một owner cho mỗi identity/resource;
5. frontend/generated outputs fresh, không orphan;
6. full gate và secret scan xanh trên tree không đổi;
7. production chưa bị deploy bởi CMC;
8. chỉ còn main worktree;
9. old branches/session state và mọi backup tạm đã bị xóa theo quyết định;
10. nhật ký, kế hoạch và quyết định nền tảng phản ánh topology mới.

## Rollback boundary

Trước final certification, rollback dùng checkpoint/bundle/patch tạm đã verify.
Sau Cleanup, lịch sử cũ cố ý không còn là rollback surface; mọi sửa đổi tiếp
theo là forward-fix trên `main`. Nếu bất kỳ điều kiện chứng nhận nào chưa đạt,
Cleanup không được bắt đầu.
