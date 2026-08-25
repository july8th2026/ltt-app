# 01 — ĐỐI CHIẾU BỐN APP ĐÃ GỠ

**Ngày:** 2026-08-26 · **Cây:** `db6147e` · **Đầu vào:** `00_LIVE_SYSTEM_MAP.md` I+II

> Mục tiêu của prompt này **không** phải "thư mục còn không". Nó là: chứng minh
> việc xoá đã sạch về **khả năng với tới + hợp đồng + vận hành**.

---

## 0. Kết luận, đặt lên đầu

```text
REMOVED_APPS_ACTIVE_REACHABILITY_SOURCE:     0 / 4
REMOVED_APPS_ACTIVE_REACHABILITY_PRODUCTION: 1 / 4   (socialbot — tới lần deploy kế tiếp)
ORPHANED_CONTRACT_BLOCKERS:                  0
NO_RUNTIME_CHANGE:                           NO  (xem mục 5 — chủ sản phẩm đã bỏ cổng duyệt)
```

⛔ **Hai con số, không phải một.** Báo một số 0 duy nhất là **nói đúng về nguồn
và sai về khách hàng**: production đang chạy `ec6a00c` và vẫn mount 43 route bảng
điều khiển FB/TikTok của `socialbot`.

---

## 1. Quét theo 15 lớp

Pack liệt kê 14 lớp. Lớp thứ 15 được **thêm vào** ở đợt này, và lý do nó tồn tại
đáng ghi hơn bản thân nó — xem mục 3.

Mọi lệnh quét đều mang `| grep -v '\.claude/worktrees/'` (xem mục 4).

| # | Lớp | Kết quả |
|---|---|---|
| 1 | imports / callers | **0** — `grep -rE "^\s*(from\|import)\s+(core\|utils)[\. ]"` trên `apps/platform_core/server/tools/tests` trả rỗng |
| 2 | registry / manifest / discovery | **0** — `discover()` nạp đúng 14 app, không lỗi |
| 3 | route mount / redirect / middleware / cờ | **0** trong nguồn · ⚠️ **43 route còn sống trên production** |
| 4 | Agent / Canvas / ToolSpec / palette | **0 tool**, nhưng còn một affordance chết — xem R-01 |
| 5 | job type / worker / bảo trì | **0** — 19 job_type, tất cả có handler, không mồ côi hai chiều |
| 6 | bảng CSDL / migration / FK / seed | **0** — không migration nào nhắc bốn app |
| 7 | nav / catalog / template / i18n | **0** trong template · 105 mục `.po` — **giữ có chủ ý**, xem mục 2 |
| 8 | tests / fixtures / snapshot | **0 phụ thuộc sống**; 5 tệp test nhắc tên trong docstring lịch sử |
| 9 | docs hiện hành / AGENTS / CLAUDE | **0** chỉ dẫn sống; mọi nhắc đều là ghi chép việc đã gỡ |
| 10 | config / env / setup / service | **0** — `LTT_SOCIALBOT_ROUTES` không còn được đọc trong nguồn |
| 11 | observability / metric / alert | **0** |
| 12 | backup / restore / release | **0** — `robocopy /XD` loại `tmp test-results .claude` (đã kiểm, đọc cả dòng nối) |
| 13 | SDK / public API | **0** — chỉ tài liệu lịch sử trong `docs/PUBLIC_API/` |
| 14 | ví dụ chuẩn / smoke fixture | **0** — `apps/demo` đã được thay bằng `tests/conftest.py::app_thu` |
| **15** | **tài liệu sống trong mã (docstring `.py`)** | **0** sau `09ee8e9` — xem mục 3 |

---

## 2. Phân loại

### `HISTORICAL_ONLY` — giữ, và giữ **có chủ ý**

**105 mục `#:` trong `locale/en/LC_MESSAGES/messages.po`** trỏ tới tệp của
`kichban`/`mediatools` không còn tồn tại.

⛔ **Đây là chỗ bản audit đầu của tôi phán đoán SAI.** Bản đầu xếp nó P2 "nên dọn
nhưng không rẻ". Phép đo lật ngược: trích lại để dọn 105 mục đó khiến `msgmerge`
sinh thêm **25 bản dịch SAI** (`fuzzy` 76 → 101). Việc "dọn" làm nợ dịch **tăng**,
và tăng ở dạng tệ nhất — `msgfmt` bỏ qua mọi mục fuzzy, nên bản dịch hỏng **trông
như đã xong** khi đọc tệp `.po`.

> **Luật rút ra:** hạ mốc dịch bằng cách **DỊCH**, không bao giờ bằng cách
> **TRÍCH LẠI**.

Mọi bình luận `.py`/`.ps1` nhắc tên bốn app đều thuộc lớp này: chúng **ghi lại
việc đã gỡ**, không chỉ dẫn ai làm gì. Giữ.

### `REPLACE_AUTHORITY` — đã xử lý

| Cái gì | Người thay | Trạng thái |
|---|---|---|
| `apps/demo` làm khuôn app tối thiểu | `tests/conftest.py::app_thu` (sống trong bộ nhớ một test) | ✅ |
| `apps/demo` làm khuôn 4 bộ test hạ tầng (`test_67/68/151/173`) | `app_thu` | ✅ |
| docstring `platform_core/registry.py:31` trỏ `apps/demo/` | đã sửa | ✅ `09ee8e9` |

### `KEEP_COMPAT_WITH_EXIT_GATE` — một mục

**43 route legacy trên production.** Cờ `LTT_SOCIALBOT_ROUTES` không còn được đọc
trong nguồn, nhưng **bản đang chạy** (`ec6a00c`) vẫn đọc nó và mặc định **BẬT**.

- **Cổng thoát:** lần deploy kế tiếp xoá chúng khỏi mã. Không cần hành động riêng.
- **Đường tắt nếu muốn sớm hơn:** `LTT_SOCIALBOT_ROUTES=0` + khởi động lại web.
- ⛔ **Đã hoãn có lý do:** khởi động lại `LTTStudioWeb` **chính là cửa sổ M-01**,
  và bản vá M-01 chưa lên production. Tắt route bây giờ có thể làm kẹt thêm một
  khoản tiền nữa **trong khi chuông vẫn chưa treo ở đó**. Xếp sau deploy.

### `UNKNOWN_NEEDS_EVIDENCE` — hết, không còn mục nào

---

## 3. Lớp thứ 15, và vì sao nó đáng thêm vào pack

`platform_core/registry.py:31` — docstring của tệp **quan trọng nhất kho** — vẫn
viết *"Xem `apps/demo/` làm mẫu tối thiểu"* sau khi `apps/demo` đã bị xoá.

Đợt audit của phiên gỡ app quét **route, import, CSDL, và tệp `.md`**. Cả bốn đều
sạch. Nó vẫn trượt dòng này, vì dòng này là **tài liệu sống trong mã**.

⭐ Chỗ đó không phải một chỗ ngẫu nhiên: nó là **câu đầu tiên người viết app mới
đọc**. Một chỉ dẫn trỏ vào thư mục trống là thứ làm hỏng công việc của người tiếp
theo, không phải của người hiện tại — nên nó không có triệu chứng nào cho tới khi
có người mới.

⇒ **Lớp 15 phải nằm trong danh sách quét:** tài liệu không chỉ sống trong `docs/`.

---

## 4. Bản sao bóng — mối nguy chẩn đoán nhầm, và nó có **hai** cái

Đây không phải residue của bốn app, nhưng nó là thứ làm **phép đếm residue sai**.

| Bản sao | Nội dung | Trạng thái |
|---|---|---|
| `.claude/worktrees/wonderful-jepsen-f190f3` | nguyên kho **trước** đợt xoá, có `core/`, `test_152` | ✅ **đã gỡ 26/08** |
| `tmp/h26-canary-20260809-120519/` | nguyên kho từ 09/08, 695 tệp `.py` | còn (1,8 GB, gitignore) |

**Đã thực sự xảy ra:** lần quét `LTT_SOCIALBOT_ROUTES` đầu tiên của đợt này trả
**13 kết quả từ worktree** trước khi tới kết quả thật — đủ để một phiên vội kết
luận *"còn residue socialbot"* trong khi nguồn đã sạch.

⭐ **Một hệ quả phụ đo được khi gỡ worktree:** `tools/check_bien_dich.py` từ
**2.101 → 1.357** tệp. Chênh 744 chính là bản sao bóng. Nghĩa là cổng biên dịch
trước đây **thổi phồng độ phủ ~35 %** bằng cách quét một bản sao cũ — con số PASS
vẫn đúng, nhưng nó nói về một tập hợp khác với tập hợp người đọc tưởng.

**Luật cho mọi prompt sau:** mọi lệnh quét toàn kho phải mang
`| grep -v '\.claude/worktrees/'` và cân nhắc `tmp/`.

---

## 5. `NO_RUNTIME_CHANGE: NO` — nói thẳng

Prompt 01 theo pack là **audit-only**. Đợt này **không** giữ được điều đó, và lý
do là chủ sản phẩm đã **bỏ cổng duyệt** và yêu cầu chạy thẳng chuỗi. Những gì đã
sửa trong lúc chạy prompt này:

| Commit | Sửa gì | Vì sao không đợi |
|---|---|---|
| `a5274bf` | M-01 + M-02 + B-01 | M-01 là P0/E4 — tiền khách **đã mất thật** |
| `db6147e` | link 404 trong nav (`ltt_llm`) | phát hiện **trong lúc** đo bề mặt cho Prompt 02 |

Ghi ra để người đọc sau không tưởng bản báo cáo này được viết trên một cây đứng
yên. Nó không.

---

## 6. Phát hiện mới sinh từ prompt này

### R-01 · P2 · E1 — Canvas còn một affordance chết cho năng lực đã gỡ

`frontend/agent-canvas/src/CanvasShell.tsx:333` vẫn tra `asset.images` /
`asset.${kind}` — bốn tool `asset.*` đã đi cùng `mediatools`.

**Không sập.** Dòng 334 xử đúng:

```ts
if(!assetTool){setRunError(`Canvas chưa có node đầu vào ${uploaded.kind}.`);return}
```

⇒ Xuống cấp êm, thông báo trung thực. **Nhưng affordance vẫn còn**: khách kéo tệp
vào một node và **luôn** nhận lỗi. Đường đưa tệp vào Canvas là một ngõ cụt có
biển báo, không phải một ngõ đã đóng.

`CLAUDE.md` ghi cái giá này đã được đo và chủ sản phẩm chấp nhận (4–7/10 workflow
mất node). Cái chưa được quyết là: **giữ ngõ cụt có biển, hay bỏ hẳn ô kéo-thả?**
⇒ chuyển Prompt 09 (UI trung thực), không tự quyết ở đây.

---

## 7. Bàn giao cho Prompt 02

- Bề mặt sản phẩm sạch residue; mọi quyết định về app còn lại là quyết định
  **sản phẩm**, không phải dọn dẹp.
- `tests/conftest.py::app_thu` là khuôn hạ tầng chuẩn — **đừng** trỏ test mới vào
  một app thật để thay `demo`; đó là đúng cái bẫy đã giữ `core/` sống thêm ba
  tuần dưới Q10.
- Con số production của Prompt 02 **chưa đo được** — xem `02_...md` §0.
