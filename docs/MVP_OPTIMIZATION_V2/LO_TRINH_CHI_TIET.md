# LỘ TRÌNH TRIỂN KHAI CHI TIẾT — MVP Optimization V2

**Lập:** 2026-08-26 · **Cây:** `9848efa` (sạch) · **Thay thế:** `KE_HOACH_THI_HANH_V2.md`
**Dựa trên:** bộ prompt pack V2 (16 prompt) + [`00_LIVE_SYSTEM_MAP.md`](00_LIVE_SYSTEM_MAP.md) Phần I & II

> Tài liệu này chia việc tới mức **một người/một phiên làm được và nghiệm thu
> được**. Mỗi mục có: mục tiêu · việc cụ thể · lệnh · tiêu chí nghiệm thu ·
> mức bằng chứng · đường lùi · phụ thuộc.

---

## 0. Ba nguyên tắc chi phối toàn lộ trình

**① Đúng trước, gọn sau, đẹp sau cùng.** Lane 12 (đúng) → Lane 13 (cấu trúc) →
Lane 14 (giao diện). Không trộn. Lý do không phải thẩm mỹ quy trình: trộn thì mất
khả năng quy trách nhiệm gốc rễ, và đường lùi từ một batch trộn là đường lùi của
cả ba thứ cùng lúc.

**② Không rewrite.** Đo được `platform_core → apps = 0 cạnh` nghĩa là nền móng
**đang đúng**. Mọi việc dưới đây là sửa nhỏ tại chỗ. Không microservices, không
đổi framework/ORM/CSDL, không viết lại frontend, không đổi tên hàng loạt.

**③ Không nâng bằng chứng bằng suy luận.** E1 (đọc mã) ≠ E2 (test chạy) ≠ E3
(trình duyệt/runtime) ≠ E4 (production). Bốn khoảng trống bằng chứng của H40
(**O-02**) phải được lấp bằng cách **chạy**, không bằng cách viết rằng đã chạy.

---

## 1. Trạng thái xuất phát — chốt lại cho khỏi lệch

| Hạng mục | Trạng thái |
|---|---|
| Cây làm việc | `9848efa`, sạch (chỉ `docs/MVP_OPTIMIZATION_V2/` chưa commit) |
| Production `C:\LTTPlatform\app` | `ec6a00c` — **19 app**, còn 43 route legacy. 4 dịch vụ Running |
| Danh mục app | 19 → **14** trong nguồn |
| Bộ test | 4.727 → **4.093** |
| `gate.py` đầy đủ | ❌ **chưa lượt nào hoàn tất** — chủ sản phẩm quyết bỏ 25/08 |
| Gói phát hành | ❌ **không dựng được** (B-01) |
| Sao lưu | ❌ không lịch, bản mới nhất 2026-08-17 (O-01) |
| **P0 mở** | **1** — M-01: **2 credit của khách đã kẹt thật** trên production (24/08) |
| P1 mở | **3** — B-01, O-01, O-02 |

⚠️ **Hai chỗ dễ chẩn đoán nhầm, dán lên tường:**

1. `.claude/worktrees/wonderful-jepsen-f190f3` giữ trạng thái **trước** đợt xoá.
   Mọi `grep -r` toàn kho đếm hai lần. **Luôn** thêm `| grep -v '\.claude/worktrees/'`.
2. `test_44_release_build` đỏ **từ trước** đợt xoá. Đừng quy cho việc gỡ 4 app.

---

# PHA A — AUDIT (không sửa runtime)

Sinh báo cáo dưới `docs/MVP_OPTIMIZATION_V2/`. Không đụng mã, config, migration,
asset, bundle.

---

## S1 · Prompt 01 + 02 — Đối chiếu app đã gỡ & bề mặt MVP

**Đầu vào:** `00_LIVE_SYSTEM_MAP.md` Phần I+II · **Đầu ra:**
`01_REMOVED_APPS_RECONCILIATION.md`, `02_MVP_OUTCOME_AND_SURFACE.md`

### T-01.1 · Quét residue theo 14 lớp, trên **hai** trạng thái

Prompt 01 mặc định đếm một con số. Ở đây phải đếm hai — nguồn đã sạch, production
thì chưa.

```bash
# LUÔN loại worktree thứ hai
grep -rniE "socialbot|kichban|mediatools" --include="*.py" --include="*.html" \
  --include="*.json" --include="*.ps1" --include="*.po" \
  apps platform_core server tools setup locale alembic sdk \
  | grep -v __pycache__ | grep -v '\.claude/worktrees/'
```

Lớp **thứ 15** phải thêm vào danh sách của pack, và lý do nó tồn tại đáng ghi:
**tài liệu sống trong mã** (docstring `.py`), không chỉ trong `docs/`. Phiên
trước quét route + import + CSDL + `.md` và **trượt** `platform_core/registry.py:31`
— dòng nằm ở docstring của tệp quan trọng nhất kho, đúng chỗ người viết app mới
đọc trước tiên.

**Nghiệm thu:**
```text
REMOVED_APPS_ACTIVE_REACHABILITY_SOURCE:     0 / n
REMOVED_APPS_ACTIVE_REACHABILITY_PRODUCTION: n / n   (tới lần deploy kế tiếp)
```
Báo một con số 0 duy nhất là **nói đúng về nguồn và sai về khách hàng**.

**Bằng chứng:** E1 cho nguồn; E3 cho production (gõ thật vào URL, như phiên trước
đã làm 21/21 → 404).

### T-01.2 · Phân loại `.po` — và **không** dọn

105 mục `#:` trỏ tệp đã xoá. Phân loại `HISTORICAL_ONLY`, **không**
`REMOVE_RESIDUE_SAFE`. Đã đo: trích lại sinh thêm 25 bản dịch sai (fuzzy 76→101).
Luật: **hạ mốc dịch bằng cách DỊCH, không bằng cách TRÍCH LẠI.**

### T-02.1 · Nạp registry thật, dựng bảng bề mặt

Đọc bình luận manifest là chưa đủ — `anhnoibo` có bình luận nói `public=False`
nhưng lời gọi `AppManifest(...)` không truyền tham số đó.

```bash
PYTHONIOENCODING=utf-8 python -c "
from platform_core.registry import discover
for m in sorted(discover(), key=lambda x: x.slug):
    print(f'{m.slug:16s} enabled={m.enabled!s:6s} public={m.public!s:6s} surface={m.surface:10s} lifecycle={m.lifecycle}')
"
```

**Nghiệm thu:** bảng 14 app với giá trị **sau khi nạp**, không phải giá trị đọc mắt.

### T-02.2 · Đo lượng dùng thật — **chặn bởi D-02**

**S-01:** 8/11 app khách vẫn `lifecycle="development"`. Bề mặt MVP hôm nay là
**mặc định manifest cộng lại**, không ai chọn. Phân loại đúng cần biết: app nào
có khách thật, bao nhiêu job, thu bao nhiêu credit.

Chỉ `COUNT`/`SUM`, không đọc nội dung:

```sql
SELECT app_slug, count(*) AS jobs, count(DISTINCT user_id) AS users,
       min(created_at) AS lan_dau, max(created_at) AS lan_cuoi
FROM jobs GROUP BY app_slug ORDER BY jobs DESC;
```

Tiền lệ: đợt gỡ socialbot an toàn **vì đã đo trước** (0 job, 0 `app_access`,
0 `app_projects`, không có `tokens.enc`).

**Nếu D-02 không duyệt:** ghi `UNMEASURABLE` cho cột "có khách thật chưa" và
**không đoán**. Prompt 02 vẫn chạy, độ chắc thấp hơn — và phải nói ra.

### T-02.3 · Phân loại từng bề mặt

Nhãn: `MVP_CORE_SURFACE` · `MVP_SUPPORT_SURFACE` · `MVP_BETA_OPTIONAL` ·
`INTERNAL_CAPABILITY` · `ADMIN_MINIMUM` · `MERGE_PRESENTATION_ONLY` ·
`DEFER_POST_MVP` · `RETIRE_REMOVE_CANDIDATE`.

**Không sửa manifest ở bước này.** Chỉ đề xuất.

---

## S2 · Prompt 03 — Hợp đồng nghiệm thu & Golden Journeys

⛔ **Chạy riêng một phiên.** Đây là hợp đồng bảo vệ 12 prompt sau khỏi việc tối ưu
một hệ thống mà chưa biết "MVP thành công" nghĩa là gì.

**Đầu ra:** `03_MVP_ACCEPTANCE_CONTRACT.md`, `03_GOLDEN_JOURNEY_MATRIX.md`

### T-03.1 · Chọn Golden Journey tối thiểu

Đề cử dựa trên đo thật (điều chỉnh theo kết quả S1):

| GJ | Hành trình | Vì sao vào danh sách |
|---|---|---|
| **GJ-1** | ẩn danh → đăng ký → xác thực email → đăng nhập → vào catalog | cửa vào duy nhất; 7 route `register.py` không có `Depends` |
| **GJ-2** | tool ảnh: nhập → báo giá → xác nhận → job → kết quả → lịch sử | đại diện **toàn bộ** lớp tiền-qua-worker |
| **GJ-3** | nạp credit PayOS → webhook → số dư | đường tiền vào; webhook ký trên thân thô |
| **GJ-4** | `/api/v1` khoá dev → `text.chat` luồng → quyết toán | **đường tiền trong-request** — nơi M-01 sống |
| **GJ-5** | job hỏng / provider timeout → hoàn tiền đúng | đường phục hồi |
| **GJ-6** | operator: tra một job của khách, giải thích được tiền | không có thì không vận hành khách thật được |

**GJ-4 là bắt buộc**, không phải tuỳ chọn: đó là hành trình duy nhất đi qua lớp
tiền không có đường về.

### T-03.2 · Bất biến xuyên hành trình

```text
INV-1  không đọc/ghi chéo chủ sở hữu
INV-2  không thu hai lần; không âm số dư ngoài ý muốn
INV-3  retry an toàn không tạo tác dụng phụ xa lần hai
INV-4  job vào trạng thái cuối ⇔ tiền đã kết sổ (settle HOẶC refund)
INV-5  ⭐ MỌI giữ chỗ cuối cùng đều kết sổ — kể cả giữ chỗ không có hàng Job
INV-6  artifact thuộc đúng chủ
INV-7  giao diện nói thật về trạng thái
INV-8  phục hồi được sau khi tiến trình/trình duyệt chết
```

**INV-5 là bất biến mới**, sinh trực tiếp từ M-01. Nó là thứ hệ thống hiện
**không** bảo đảm.

**Nghiệm thu:** `GOLDEN_JOURNEYS_DEFINED: YES`, mỗi GJ ghi rõ E-hiện-có và
E-cần-có; `UNMEASURABLE_CRITICAL_OUTCOMES: n` có tên từng cái.

---

## S3 · Prompt 04 + 05 — Kiến trúc & định vị thay đổi

**Đầu ra:** `04_ARCHITECTURE_DEPENDENCY_AUDIT.md`, `05_MODULE_FILE_CHANGE_LOCALITY.md`

Phần lớn phép đo **đã có** ở Phần II — S3 không đo lại, chỉ quyết định.

### T-04.1 · Chốt bốn cạnh đã đo, đề xuất 2 phương án mỗi cạnh

A-01, A-02, A-03, A-04 — xem II.1. Mỗi cạnh cần: 2 phương án + ROI + rủi ro +
"KHÔNG được đổi".

### T-04.2 · Kiểm chu trình còn sót

```bash
PYTHONIOENCODING=utf-8 python - <<'PY'
# dựng lại đồ thị AST rồi tìm chu trình (script mẫu ở scratchpad phiên 2026-08-26)
PY
```
Đã biết một chu trình mức gói: `server ↔ tools`.

### T-05.1 · Chấm điểm điểm nóng theo **Change Locality**, không theo LOC

| Tệp | Dòng | Handler | Câu hỏi |
|---|---|---:|---|
| `server/admin_api.py` | 1.897 | — | mấy use case độc lập? |
| `server/routes/developer.py` | 1.521 | **32** | **vượt cả hai trần app-contract nhưng ngoài tầm lint** (G-01) |
| `server/admin.py` | 1.388 | — | |
| `platform_core/job_runner.py` | 1.236 | — | đây là **trái tim**; tách là rủi ro cao |
| `apps/autosubvideo/routes.py` | **899** | 25 | **sát trần 900/30 đúng một dòng** |

Với mỗi tệp trả lời 7 câu của Prompt 05, đặc biệt câu 3 (*"fix gần đây chạm những
vùng nào"*) — dùng `git log --follow --stat`.

**Nhãn:** `KEEP` · `SPLIT_BY_USE_CASE` · `MOVE_TO_EXISTING_OWNER` ·
`RENAME_FOR_OWNERSHIP` · `EXTRACT_SHARED_ONLY_AFTER_RULE_OF_THREE` · `LEAVE_UNTIL_CHURN`

⚠️ `autosubvideo/routes.py` ở 899/900 nghĩa là **dòng tiếp theo ai đó thêm sẽ làm
gate đỏ**. Đó là việc phải xử, nhưng xử vì lý do đó chứ không phải vì "899 là số
xấu".

---

## S4 · Prompt 06 + 07 + 08 — Tiền, quyền, dữ liệu

**Đầu ra:** `06_RUNTIME_RELIABILITY_AUDIT.md`, `07_SECURITY_TENANT_PRIVACY_AUDIT.md`,
`08_DATA_CONFIG_AUTHORITY_AUDIT.md`

### T-06.1 · ⭐ M-01 — **đã là E4, không còn phải chứng minh nó có thật**

Đo trên production 26/08: **2 credit kẹt thật**, cả hai không có hàng `Job`, cả
hai ngày 24/08. Máy dò hiện tại bắt **0/2**. Tỉ lệ phát hiện thủ công **1/2**.

Việc còn lại **không** phải chứng minh lỗi tồn tại — mà là tách **hai** lỗi ra,
vì chúng sửa khác nhau:

**T-06.1a · Lỗi "bắt hụt" — lấy E2 mà không phá gì** *(cần D-02)*

```bash
python tools/reconcile_public_api_usage.py --days 3
```

Hai dòng mồ côi đã nằm sẵn đó. Dự đoán: in `ok: True`, `holds_without_job: 0`.
Nếu đúng ⇒ đã chứng minh máy dò **mù** trên dữ liệu thật, không cần giết dịch vụ
nào.

**T-06.1b · Lỗi "cửa sổ khi giết tiến trình" — cần phép thử phá hoại**

Gọi `/api/v1/messages` dạng luồng rồi `Stop-Service -Force LTTStudioWeb`.
**Trên CSDL test, không production**, và cần chủ sản phẩm đồng ý.

⚠️ Đừng gộp hai phép thử. Chúng chứng minh hai thứ khác nhau, ở hai mức rủi ro
khác nhau, và T-06.1a làm được ngay hôm nay.

**T-06.1c · Câu hỏi mở phải trả lời**

`platform_core/agent/budget.py:86` giữ chỗ rồi để lại hàng `AgentRun` **bền vững**
ở `AGENT_RUNNING`. Khác chất với ba đường kia: nó **thu hồi được** nếu có gì đó
quét run treo. **Có gì quét không?** Chưa xác minh. Nếu không thì đó là đường thứ
tư, và là đường duy nhất sửa được rẻ bằng một vòng quét sẵn có.

**Nghiệm thu:** một test tái hiện được cho mỗi lỗi, đặt số theo
`tools/check_so_test.py`. **Chưa sửa** — sửa là T-12.1.

### T-06.2 · Ma trận cửa sổ hỏng cho cả 24 điểm đổi tiền

Sáu cột theo pack: state chưa commit / state commit + side effect chưa xảy ra /
side effect xảy ra + state rollback / chết trước ACK / timeout không rõ kết quả /
retry trùng.

Riêng `credit.tru()` (2 chỗ: `vps/services/billing.py:106`,
`nexus/billing.py:103`) là **trừ thẳng, không giữ chỗ** — mô hình thuê bao. Kiểm
riêng: chạy hai lần trong một chu kỳ có trừ hai lần không? (`AppManifest.bao_tri`
chạy dưới lease nên **về lý thuyết** là không — cần test chứng minh.)

### T-07.1 · Test âm tính chủ-A/chủ-B

Bề mặt xác thực sạch ở **E1** (II.2). Nâng lên E2: với mỗi route trả artifact/job/
project, dựng hai chủ và thử thay ID. Ưu tiên theo GJ.

### T-07.2 · Bốn chốt không-`Depends` cần test riêng

HMAC thiết bị (phát lại + lệch giờ) · bearer `/watch/*` (cookie trình duyệt phải
bị từ chối) · chữ ký PayOS (thân sửa đổi) · `relay_check` fail-closed (biến rỗng
⇒ tắt).

### T-08.1 · Ma trận thẩm quyền + xử D-01

Mỗi khái niệm → SSoT → readers → writers → cơ chế thi hành. **D-01:** `CLAUDE.md`
nói `LTT_PUBLIC_API_TOOLS` rỗng; production đặt `text.chat,image.ltt`. Sửa **tài
liệu**, không sửa cờ.

**Đã sạch, ghi vào danh sách giữ nguyên:** 106 biến đọc / 42 đặt / **0** biến
production mà mã không đọc.

---

## S5 · Prompt 09 + 10 — Giao diện & vận hành

**Đầu ra:** `09_UI_UX_MVP_AUDIT.md`, `10_OPERABILITY_PERFORMANCE_COST_AUDIT.md`

### T-09.1 · Bằng chứng E3 cho từng trang GJ

⛔ **Hai đường, và đường thứ hai mới là đường chốt:**
1. `127.0.0.1:8100` — soi nhanh;
2. `https://app.lttstudios.com` — **chốt**. Loopback bỏ qua Cloudflare (cache,
   CSP biên, minify). Đã dính một lần: sửa `ltt.css`, origin đúng, CF phục vụ bản
   cũ 4 giờ, chip hiện thành radio thô.

Mỗi trang: desktop + mobile · rỗng/nhập/chạy/kết quả · console · request hỏng ·
tràn ngang · đường focus bàn phím.

### T-09.2 · Kiểm U-01 bằng mắt, không bằng grep

57/81 template dùng `style=` nội tuyến là **tín hiệu**, chưa phải phán quyết.
Câu hỏi đúng: *cùng một nút bấm có trông khác nhau giữa hai trang MVP không?*
Không khác ⇒ P3, không phải P2. `.page--catalog` mồ côi trong CSS: xác nhận rồi
xoá ở Lane 14 (nhớ cache-bust, xem T-14.3).

### T-10.1 · Đường support: một job của khách truy được tới đâu

Từ `request_id`/`job_id` → sự kiện → lớp lỗi provider → giữ/quyết toán/hoàn →
artifact → retry/cancel. Đây cũng là chỗ M-01 lộ ra dưới góc nhìn vận hành:
**một giữ chỗ kẹt hiện lên ở đâu?** (đáp án hiện tại: không đâu cả).

### T-10.2 · O-01 — sao lưu (không đợi tới đây, xem T-12.3)

Đo cần quyền nâng cao:
```powershell
Get-ChildItem D:\LTTBackups -Recurse -File | Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 FullName, Length, LastWriteTime
```

### T-10.3 · Baseline hiệu năng — và một cái bẫy

⚠️ **Thời gian chạy test trước/sau KHÔNG so được với nhau.** `tests/conftest.py`
từng có ba fixture `autouse` chạy trước **mọi** test; chúng đi cùng đợt xoá. Bộ
test nhanh hơn vì **bớt việc mỗi test**, không phải vì mã tốt lên. Ghi số nào thì
ghi kèm câu này, nếu không nó sẽ được đọc thành một cải thiện không có thật.

---

## S6 · Prompt 11 — Tổng hợp & cổng quyết định

**Đầu ra:** `11_MASTER_PLAN.md`, `11_DECISION_GATE.md`, `11_MVP_ACCEPTANCE_CANDIDATE.md`

### T-11.1 · Gộp nguyên nhân gốc — một gốc, một chủ, một batch

Ví dụ đã thấy: B-01 sinh ra **hai** test đỏ, nhưng chỉ **một** gốc (bundle cũ).
Sửa gốc, không sửa hai triệu chứng.

### T-11.2 · Sơ đồ hiện tại → đích

Đích phải là **tiến hoá** của cây thật. Vùng đủ tốt ghi `KEEP AS-IS` — và ở kho
này danh sách `KEEP AS-IS` **dài hơn** danh sách sửa (14 mục ở II.10 + Phần I).

**Nghiệm thu:**
```text
READY_FOR_CORRECTNESS_LANE / STRUCTURAL_LANE / UI_LANE: YES/NO
OPEN_OWNER_DECISIONS: n
```

---

# ⛔ CỔNG CHỦ SẢN PHẨM

Điền `templates/HUMAN_DECISIONS.md`. **Trống = CHƯA DUYỆT.**

| ID | Câu hỏi | A | B | Khuyến nghị | Cửa |
|---|---|---|---|---|---|
| **D-01** | Bật lại lịch sao lưu production ngay? | Đăng ký `LTTStudioBackup` + chạy một lần có `-IncludeSecrets` | Đợi S5 | **A** | 2 chiều |
| **D-02** | Cho phép đếm chỉ-đọc CSDL production để chốt bề mặt MVP? | Cho phép `COUNT`/`SUM` | Không — ghi `UNMEASURABLE` | **A** | 2 chiều |
| **D-03** | 43 route legacy đang chạy trên production? | `LTT_SOCIALBOT_ROUTES=0` + khởi động lại web | Đợi lần deploy đợt xoá | **A** | 2 chiều (vài giây) |
| **D-04** | M-01 sửa tới đâu? | A: máy dò + báo (rẻ, không đụng tiền) | B: `hold_expires_at` + tự hoàn (đúng gốc, đụng schema) | **A trước, B sau khi có số** | A 2 chiều · B 1 chiều |
| **D-07** | Bù 2 credit đã kẹt cho khách, theo đường nào? | Ghi bút toán bù cho **cả hai** dòng | Chỉ bù dòng đã có người ghi (`23:58:10`) | **A** — sổ append-only nên bù là bút toán MỚI, không sửa lịch sử | 2 chiều |
| **D-05** | Bề mặt MVP: app nào `RETIRE`/`DEFER`? | *(chờ S1/S2)* | | — | **1 chiều** |
| **D-06** | Deploy đợt xoá lên production khi nào? | Sau khi Lane 12 xong + gate đầy đủ xanh | Sớm hơn | **A** | **1 chiều** |

⚠️ **D-05 và D-06 là hai cửa một chiều duy nhất.** Mọi thứ khác lùi được.

---

# PHA B — THI HÀNH

Chỉ chạy sau cổng quyết định. Trước **mỗi** batch: đọc lại finding, `git status`,
chạy tái hiện, ghi behavior kỳ vọng + đường lùi. **Nếu tái hiện không còn đúng thì
KHÔNG sửa** — cập nhật finding.

---

## S7 · Prompt 12 — Lane đúng đắn (correctness + residue)

### T-12.1 · M-01 phương án A — máy dò biết đếm và biết kêu

Ba việc nhỏ, thứ tự này:

1. **Sửa vị ngữ.** `usage.reconcile` đang đếm `job_id == ""`. Đổi thành "có `hold`
   mà không có `settle`/`refund` **và** không ứng với hàng `Job` nào" — bắt được
   cả bốn đường ở II.4(1).
2. **Cắm vào `_mot_luot_bao_tri`** dưới lease `bao_tri`, nhịp riêng. **Chỉ báo,
   không tự hoàn.** Tự hoàn là quyết định tiền — thuộc phương án B.
3. **Nối vào `ops_alerts`** để người trực biết, thay vì chờ ai đó gõ CLI.

**Không đụng:** `_khoa_so_du_user`, tính append-only của sổ, `quyet_toan_hoac_hoan`.

**Nghiệm thu:** test T-06.1 chuyển xanh · một test âm tính chứng minh máy dò **bắt
được** giữ chỗ có `request_id` khác rỗng · `check_multiproc` chứng minh việc nền
chạy **một lần trên cả cụm**, không N lần.

**Đường lùi:** `git revert`; máy dò chỉ đọc nên không có dữ liệu để hoàn tác.

### T-12.2 · B-01 — dựng lại ba bundle

```bash
cd frontend/agent-canvas && npm ci && npm run build
cd ../autosub-studio && npm ci && npm run build
cd ../prompt-ai-ommi && npm ci && npm run build
```
rồi:
```bash
python tools/build_system_profile.py
python tools/dong_goi_gui.py
```

**Nghiệm thu:** `pytest tests/test_44_release_build.py -q` ⇒ **35 passed**. Đặc
biệt xác nhận `test_secret_abort_path_reports_location_and_exits` **thật sự chạy**
— nó đang bị chốt bundle-cũ che.

⚠️ **Đổi bundle = đổi tài sản tĩnh ⇒ phải cache-bust.** Xem T-14.3.

### T-12.3 · O-01 — sao lưu *(cần D-01)*

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\5-lich-backup.ps1
powershell -ExecutionPolicy Bypass -File .\deploy\windows\backup.ps1 -IncludeSecrets
```

**Nghiệm thu:** `Get-ScheduledTaskInfo -TaskName 'LTTStudioBackup'` trả về task
với `LastTaskResult = 0` · có tệp mới trong `C:\LTTPlatform\backups` · có thư mục
`backups-secrets` với `ltt_secrets_*.zip` · và **một lần diễn tập khôi phục**
(`tools/restore_drill_schema.py`) chứng minh bản sao dùng được — bản sao chưa
khôi phục thử là một lời hứa, không phải một bản sao.

### T-12.4 · F-07 — worktree thứ hai

Hỏi phiên đang giữ nó. Nếu đã xong: `git worktree remove`. Nếu chưa: để nguyên và
giữ luật `grep -v '\.claude/worktrees/'`. **Không tự xoá** — cửa một chiều với
công việc chưa commit ở đó.

### T-12.5 · D-03 — tắt 43 route legacy trên production *(cần D-03)*

Thêm `LTT_SOCIALBOT_ROUTES=0` vào `C:\LTTPlatform\secrets\app.env`, khởi động lại
`LTTStudioWeb`. Đảo được trong vài giây bằng cách xoá dòng đó.

**Nghiệm thu:** gõ thật vào ≥5 trong 43 URL ⇒ 404. Log ghi
`LTT_SOCIALBOT_ROUTES=0 — khong gan 43 route...`.

### Cổng thoát Lane 12

```text
OPEN_P0_FROM_AUDIT: 0
OPEN_P1_CORRECTNESS_BLOCKERS: 0 (hoặc chủ sản phẩm hoãn CÓ lý do VÀ có hạn)
REMOVED_APP_ACTIVE_RESIDUE: 0 ở nguồn; production ghi rõ trạng thái
GOLDEN_JOURNEY_BEHAVIOR_REGRESSION: 0
python tools\gate.py   (ĐẦY ĐỦ, không --quick)   PASS
```

⛔ Không đạt thì **không chạy Prompt 13**.

---

## S8 · Prompt 13 — Lane cấu trúc (giữ nguyên behavior)

### T-13.1 · A-02 — cắt `server/api` khỏi tên app

Đưa `MAX_TOKENS_TRAN`, `MAX_TOKENS_MAC_DINH`, `tran_theo_ngu_canh` ra sau một bề
mặt **không mang tên app** — hoặc để app tự khai qua `ToolSpec`/`api_contract`
như luật đã viết. 5 chỗ import.

**Bất biến:** trần token của khách **không đổi một con số nào**. Chốt bằng
`tests/golden/public_api_catalog_v1.json` (đã có sẵn — đây chính là việc nó sinh
ra để làm).

### T-13.2 · A-04 — khai báo biên `apps → server`

Hai phương án, chọn theo §F (abstraction tối thiểu):

- **A. Khai báo, không di chuyển** *(khuyến nghị)*: ghi vào `AGENTS.md` mục 8
  rằng app **chỉ** được import 4 module này từ `server`, rồi mở rộng
  `tools/lint_app_contract.py` để thi hành. Chi phí ~1 ngày, 0 rủi ro runtime,
  bắt được vi phạm **tương lai**.
- **B. Di chuyển sang `platform_core/web/`**: đúng chỗ hơn về mặt tên gọi, nhưng
  chạm 72 chỗ import trong 12 app để đổi lấy một cái tên đẹp hơn.

Phương án A thắng vì nó giải quyết **rủi ro thật** (lần sau ai đó với tay sâu
hơn) mà không trả giá 72 lần sửa.

### T-13.3 · A-01 — khai bề mặt công khai của `upscalevideo`

`taovideo` đã gọi đúng hai thứ (`cost.uoc_luong_credit`, `service.submit_upscale_job`).
Việc cần làm **không** phải cắt cạnh — mà là **khai nó là công khai** và chốt
bằng lint rằng chỉ những thứ đó được gọi từ ngoài. Nhỏ, use-case-oriented, có chủ
rõ ràng — đúng "boundary rule" của Prompt 13.

### T-13.4 · A-03 + G-01

`server/routes/status.py` → `tools.doctor`: gỡ chu trình. `dashboard.py` →
`apps.anhnoibo.gia`: đưa giá về bề mặt chung `/gia-api`. G-01: mở rộng lint sang
`server/` **chỉ khi** T-05.1 chứng minh `developer.py` có nhiều use case độc lập
— không tách vì con số 1.521.

**Đường lùi mỗi batch:** một commit một mục tiêu, `git revert` được từng cái.

---

## S9 · Prompt 14 — Lane giao diện

Chỉ trang MVP. Thứ tự: IA/nav → shell + token → ngữ pháp trạng thái GJ →
primitive trùng lặp thật → bề rộng/layout → mobile/a11y → dọn style nội tuyến
**sau khi** bản thay thế đã chứng minh.

### T-14.3 · ⛔ Cache-bust — luật cứng cho mọi thay đổi tĩnh

`ltt.css` đính `?v={{ asset_ver }}` (hash nội dung,
`server/templating.py:ASSET_VER`). Thêm asset tĩnh **mới**, hoặc dựng HTML bằng
chuỗi (vd `server/admin.py`), thì **cũng phải** đính version. Trang HTML đã
`Cache-Control: no-store` nên link version tới người dùng ngay sau deploy.

Không làm bước này thì người dùng nhận bản cũ tới khi hết TTL 4 giờ — và trang sẽ
**đẹp ở loopback, vỡ với khách thật**.

**Browser gate mỗi trang đã chạm:** desktop + mobile · rỗng · nhập/hành động ·
báo giá/xác nhận nếu có tiền · chờ/chạy/kết quả · lỗi/phục hồi · console · request
hỏng · tràn ngang · đường focus · ảnh chụp.

---

## S10 · Prompt 15 — Nghiệm thu & đóng băng

Không phải vòng refactor mới.

### T-15.1 · Lấp bốn khoảng trống bằng chứng của O-02

Đây là việc **bắt buộc**, không phải tuỳ chọn — H40 đã đóng mà thiếu cả bốn:

1. `python -m pytest -q --ignore=tmp --ignore=test-results` — **toàn bộ 4.093**;
2. ba bộ frontend trên cây cuối;
3. `python tools/check_multiproc.py`;
4. kiểm trình duyệt thật trên URL công khai.

⚠️ **Chạy `gate.py` đầy đủ một mình.** Gate lấy dấu vân tay cây ở cả hai đầu; ghi
tệp trong `apps/ platform_core/ server/ tools/ tests/ alembic/ locale/` lúc nó
chạy làm cả lượt vô giá trị. Ngày 25/08 chuyện này xảy ra **ba lần**, một trong
đó do chính phiên audit này chạy `pytest` song song. Hỏi `ListAgents` trước.

### T-15.2 · Đối chiếu tài liệu

D-01 · 4 app đã gỡ không còn tham chiếu sống · quyết định supersede đúng ·
`ho_so_he_thong.txt` sinh lại · **không có tuyên bố PASS nào vượt bằng chứng**.

### T-15.3 · Bảng nghiệm thu

```text
MVP_SCOPE / GOLDEN_JOURNEYS / ARCHITECTURE_GATE / SECURITY_TENANT_GATE
RUNTIME_GATE / MONEY_GATE / DATA_RECOVERY_GATE / UI_UX_GATE
ACCESSIBILITY_GATE / OPERABILITY_GATE / PERFORMANCE_COST_GATE / FULL_REPO_GATE
OPEN_P0 / OPEN_P1 / OWNER_RISK_ACCEPTANCES / MVP_OPTIMIZED: YES|NO
```

Được **đề xuất** tag `MVP_OPTIMIZED_V2`. **Không tự tag/deploy/push.**

---

## 2. Sổ rủi ro

| # | Rủi ro | Đã thấy? | Giảm nhẹ |
|---|---|---|---|
| R1 | Chạy gate song song với phiên khác ⇒ kết quả vô giá trị | ✅ **3 lần ngày 25/08** | `ListAgents` trước; một lượt gate một lúc |
| R2 | Loopback xanh, khách thật vỡ | ✅ đã dính (`ltt.css`, TTL 4h) | Chốt trên URL công khai |
| R3 | Deploy giữa lúc có luồng LLM ⇒ tiền kẹt | ✅ **ĐÃ XẢY RA 2 LẦN, 2 credit** (24/08) | Khuyến nghị T-12.1 trước D-06 (mục 3) — **điều kiện kỹ thuật, không phải cấm**; deploy là quyền chủ sản phẩm |
| R8 | Tiền kẹt không ai đếm ⇒ con số thật ≥ con số biết | ✅ tỉ lệ phát hiện thủ công **1/2** | Treo chuông (T-12.1) trước khi bàn bồi hoàn |
| R9 | Đọc ngược mẫu nhỏ: "0 sự cố" thành "an toàn" | ✅ `agent_runs` **n=4**, 0 rò | Ghi cỡ mẫu cạnh mọi con số 0; R8 theo chiều ngược |
| R10 | Việc "đã biết" không bao giờ được xếp lịch | ✅ **M-01 chính là ca mẫu** | Xem P-01 — mục "Còn tồn đọng" phải có đường vào `KE_HOACH_TRIEN_KHAI.md` |
| R4 | Máy tự khởi động lại (Windows Update) | ✅ đã xảy ra | Việc dài phải ghi tiến độ từng bước |
| R5 | Quét toàn kho đếm worktree hai lần ⇒ chẩn đoán nhầm | ✅ suýt xảy ra trong chính đợt này | `grep -v '\.claude/worktrees/'` |
| R6 | `--quick` PASS bị đọc thành "đã kiểm đủ" | ✅ 25/08 hai phiên | Lane 12–15 dùng gate đầy đủ |
| R7 | Deploy đợt xoá 96.734 dòng lên hệ thống đang thu tiền | chưa | D-06, sau Lane 12 + gate xanh; có `app.previous` để lùi |

---

## 3. Thứ tự nếu chỉ làm được ba việc

Cập nhật 26/08 sau khi M-01 lên **P0/E4** (2 credit đã mất thật):

1. **T-12.1 — M-01.** Không còn là rủi ro; là **thiệt hại đang diễn ra**, và
   không ai đang đếm. Tỉ lệ phát hiện thủ công 1/2 nghĩa là con số thật **lớn
   hơn hoặc bằng** con số đo được, không bao giờ nhỏ hơn. Bước đầu tiên
   (`reconcile` chạy được và đếm đúng) rẻ và không đụng đường tiền.
2. **T-12.3 — sao lưu** *(D-01)*. Không chặn prompt nào; nó chặn **mất dữ liệu**,
   thứ duy nhất trong danh sách **không sửa lại được**.
3. **T-12.2 — dựng lại bundle.** Rẻ nhất, và đang chặn **cả gói phát hành lẫn một
   phép kiểm chặn rò rỉ bí mật**.

### Về thứ tự deploy — **khuyến nghị, không phải cấm**

Bản đầu của tài liệu này viết *"luật thứ tự cứng: không deploy trước khi T-12.1
xong"*. **Sửa lại cách nói đó.** Deploy là quyết định của chủ sản phẩm; hai phiên
Claude không đặt ra được một điều cấm, và chủ sản phẩm có thể có lý do thương mại
mà phép đo kỹ thuật không thấy.

Điều đúng đắn để nói là **điều kiện kỹ thuật đi kèm**, và chủ sản phẩm cân nó với
những thứ khác:

> **Deploy là hành động mở cửa sổ M-01.** `setup/2-cai-dat.ps1:107`
> `Stop-Service -Force` giết đúng tiến trình đang giữ lưới hoàn tiền. Deploy khi
> chưa treo chuông (T-12.1) = mở cửa sổ đó **mà vẫn không ai đếm** — nên nếu tiền
> lại kẹt, ta sẽ biết với xác suất khoảng 1/2, như hai lần trước.
>
> T-12.1 bước đầu (máy dò đếm đúng + báo) **rẻ, chỉ đọc, không đụng đường tiền**.
> Khuyến nghị: xong nó trước, rồi deploy tuỳ chủ sản phẩm.

Nếu chủ sản phẩm chọn deploy trước: đó là một lựa chọn hợp lệ, và việc cần làm
kèm theo là **ghi lại mốc thời gian deploy** để sau này đối soát được khoảng nào
có nguy cơ.

Ba việc còn lại của pha A đều **quan trọng**; ba việc trên là **khẩn cấp**. Hai
tính từ đó không cùng nghĩa.
