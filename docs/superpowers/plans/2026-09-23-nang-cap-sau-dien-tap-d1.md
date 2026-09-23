# Nâng cấp sau lượt diễn tập D1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa các lỗi vận hành mà lượt diễn tập thật D1 (23/09) đo được, theo thứ tự "cái đang
chặn chính mình trước", rồi lấp các hạng mục đã nghiên cứu nhưng chưa triển khai.

**Architecture:** Bốn nhóm độc lập nhau, mỗi nhóm một kho: (1) ngữ nghĩa lỗi phía client
(`D:\LTTCODEAPP`, TypeScript), (2) thân lỗi phía nền tảng (`D:\LTTSTUDIOSAPP`, Python),
(3) thông tin tài khoản (nền tảng cấp scope + app hiển thị), (4) giám sát và phát hành.
Không nhóm nào phụ thuộc nhóm khác về mã; chỉ Task 5 phụ thuộc Task 4 về **quyết định của
chủ dự án**.

**Tech Stack:** TypeScript (plugin `llm-ltt`, test `node --test`), Python 3.13 + FastAPI +
SQLAlchemy (nền tảng, test `pytest`), PowerShell 7 (phát hành), Tauri/Rust (vỏ app).

**Spec:** Không có spec riêng. Nguồn yêu cầu là **số đo và sổ lỗi**:
- `D:\LTTCODEAPP\docs\LTTCODE\reports\self-improve\SO_LOI_VAN_HANH.md` — V-19…V-23
- `D:\LTTCODEAPP\docs\LTTCODE\HANG_MUC_BAN_SAU.md` — N-01…N-06
- `D:\LTTCODEAPP\docs\LTTCODE\reports\CHAM_DIEM_VAN_HANH_THAT_23_09.md` — 60 hạng mục chấm điểm
- `docs\VIEC_CAN_LAM_HOP_NHAT.md` — bảng quyết ưu tiên

## Global Constraints

Áp cho **mọi** task, không nhắc lại trong từng task:

- **Gate:** trong phiên chỉ chạy **test nhắm** cụm vừa sửa. Cần gate thì **CHỈ L1**
  (`python tools\gate.py --doi`). ⛔ Không L3 giữa các pha. Hợp đồng `docs/00_LTT_OPERATING_CONTRACT.md` §4.
- **Lệnh nặng:** ≥ 3 tệp test hoặc build ⇒ qua khoá `cpu_nhieu`
  (`python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`), `-n` ≤ 7.
  ⛔ Không giữ khoá trong lúc CHỜ.
- **Git:** `git add` tường minh từng tệp. Dòng `??` lạ trong `git status` là **phiên khác** —
  không `stash`, không `reset`, không `checkout --`.
- **Windows:** cấu hình ghi **KHÔNG BOM**; `.ps1` **thuần ASCII**; ⛔ không viết Python inline
  qua PowerShell. Cả ba đã từng làm sập production (`AGENTS.md` §5).
- **Số tệp test:** lấy trong dải **2300–2319** cho đợt này; chạy `py tools/check_so_test.py`
  sau khi thêm để chắc không tăng trùng lặp.
- **Deploy:** thứ tự bắt buộc **máy B trước, máy A sau**. Deploy cần gate xanh trên đúng SHA.
- **Máy B là máy dùng chung:** trước khi đo hiệu năng, kiểm `http://192.168.2.66:8299/health/ready`
  — 503 `thieu_card` nghĩa là **không đo được gì cả**, dừng và báo.

---

## File Structure

| Tệp | Trách nhiệm | Task |
|---|---|---|
| `D:\LTTCODEAPP\plugins\llm-ltt\src\errors.ts` | Giải mã thân lỗi → mã trung tính cho Harness | 1 |
| `D:\LTTCODEAPP\plugins\llm-ltt\test\error-contract.test.mjs` | Đối chứng cho bộ giải mã | 1 |
| `D:\LTTCODEAPP\desktop\sidecar\presets\standard\agent.cordis.yml` | Số lần thử lại khi nhà cung cấp quá tải | 2 |
| `platform_core\runtime_noi_bo\luong.py` | Dựng thân lỗi cho cửa stream | 3 |
| `tests\test_2300_thieu_credit_kem_so.py` | Đối chứng cho thân lỗi 409 | 3 |
| `apps\lttcode\dang_nhap.py` | Quyền của khoá LTTCODE cấp lúc đăng nhập | 4 |
| `tests\test_2301_scope_khoa_lttcode.py` | Đối chứng scope | 4 |
| `D:\LTTCODEAPP\desktop\src\account.ts` | Cửa sổ Tài khoản hiển thị số dư | 5 |
| `tools\canh_cong_may_b.py` | Canh `/health/ready` máy B, báo khi 503 | 6 |
| `tests\test_2302_canh_cong_may_b.py` | Đối chứng bộ canh | 6 |
| `D:\LTTCODEAPP\tools\release.ps1` | Bắt buộc có ghi chú phát hành | 7 |
| `docs\PUBLIC_API\*` | Ghi rõ yêu cầu `User-Agent` | 8 |

---

## Task 1: Lỗi cổng 5xx phải được thử lại (V-19)

**Vì sao:** 23/09, PostgreSQL bị một phiên khác restart ⇒ origin đứt ⇒ Cloudflare trả **502** kèm
trang HTML của chính nó. Thân đó **không bao giờ** có `ltt_error` (yêu cầu chưa tới máy A), nên
rơi vào `UPSTREAM_UNKNOWN` — mã **không được thử lại** — và lượt của khách chết, dù lỗi mang sẵn
`providerRetryAfterMs: 60000`. Đo: `request/header` …505072 → `assistant/attempt` …505958, **886 ms**.

**Files:**
- Modify: `D:\LTTCODEAPP\plugins\llm-ltt\src\errors.ts` (hàm `lttWireError`, ~dòng 261)
- Test: `D:\LTTCODEAPP\plugins\llm-ltt\test\error-contract.test.mjs`

**Interfaces:**
- Consumes: `decodeLttFailure(value, headers) -> DecodedFailure`, `UPSTREAM_UNKNOWN_CODE`,
  `failureOptions(decoded, status)` — đã có trong tệp.
- Produces: `lttWireError` giữ nguyên chữ ký `(value: unknown, options: { status?: number; headers?: Headers }) => LlmError`.
  Chỉ **mã định tuyến** đổi, message giữ nguyên.

- [ ] **Step 1: Viết phép kiểm đỏ**

Thêm vào cuối `plugins/llm-ltt/test/error-contract.test.mjs`:

```javascript
test('cong 5xx khong co ltt_error thi van duoc thu lai', () => {
  // Than HTML cua Cloudflare khi origin dut - khong the co ltt_error.
  const than = '<!DOCTYPE html><html><body>502 Bad Gateway</body></html>'
  for (const status of [502, 503, 504]) {
    const loi = lttWireError(than, { status })
    assert.notEqual(loi.code, 'UPSTREAM_UNKNOWN',
      `status ${status} phai duoc dinh tuyen la loi tam thoi`)
    assert.equal(loi.code, 'SERVER')
    assert.equal(loi.status, status)
  }
})

test('4xx khong co ltt_error thi VAN fail-closed', () => {
  const loi = lttWireError('{"error":{"message":"la"}}', { status: 400 })
  assert.equal(loi.code, 'UPSTREAM_UNKNOWN')
})

test('than co ltt_error thi status khong dè len mã canonical', () => {
  const than = JSON.stringify({
    error: {
      message: 'qua tai',
      ltt_error: { schema_version: 1, canonical_code: 'provider_overloaded' },
    },
  })
  const loi = lttWireError(than, { status: 503 })
  assert.equal(loi.code, 'RATE_LIMIT') // theo registry, khong phai SERVER
})
```

- [ ] **Step 2: Chạy để chắc nó ĐỎ**

```bash
cd /d/LTTCODEAPP && node --test plugins/llm-ltt/test/error-contract.test.mjs
```

Kỳ vọng: **FAIL** ở phép đầu với `loi.code === 'UPSTREAM_UNKNOWN'`.

- [ ] **Step 3: Sửa tối thiểu**

Trong `plugins/llm-ltt/src/errors.ts`, thay thân `lttWireError`:

```typescript
/**
 * Mã cong 5xx (502/503/504) mà than KHONG giai ma duoc: yeu cau chua toi may A
 * (Cloudflare/reverse proxy tra trang cua chinh no), nen than khong the co
 * `ltt_error`. Fail-closed o day la sai chieu: no bien mot su co ha tang TAM THOI
 * thanh mat luot cua khach. Do 23/09 (V-19): PostgreSQL bi restart -> origin dut
 * -> 502 -> luot chet sau 886 ms du loi mang san retryAfter 60 s.
 *
 * ⛔ CHI ap khi than KHONG phan loai duoc. Than co `ltt_error` thi registry thang:
 *    mot 503 mang canonical_code `provider_overloaded` van phai la RATE_LIMIT.
 */
const RETRYABLE_GATEWAY_STATUS = Object.freeze([502, 503, 504])

/** Build a typed LlmError from a decoded LTT HTTP or SSE envelope. */
export function lttWireError(value: unknown, options: { status?: number; headers?: Headers } = {}): LlmError {
  const decoded = decodeLttFailure(value, options.headers)
  const code = decoded.neutralCode === UPSTREAM_UNKNOWN_CODE
    && options.status !== undefined
    && RETRYABLE_GATEWAY_STATUS.includes(options.status)
    ? 'SERVER'
    : decoded.neutralCode
  return new LlmError(decoded.message, code, failureOptions(decoded, options.status))
}
```

- [ ] **Step 4: Chạy để chắc nó XANH**

```bash
cd /d/LTTCODEAPP && node --test plugins/llm-ltt/test/error-contract.test.mjs
```

Kỳ vọng: **PASS** toàn bộ tệp (trước đợt này là 9 phép, nay 12).

- [ ] **Step 5: Chạy cả cụm llm-ltt để chắc không vỡ chỗ khác**

```bash
cd /d/LTTCODEAPP && node --test plugins/llm-ltt/test/
```

Kỳ vọng: PASS. Bản 0.2.6 có 110 phép ở cụm này.

- [ ] **Step 6: Commit**

```bash
cd /d/LTTCODEAPP
git add plugins/llm-ltt/src/errors.ts plugins/llm-ltt/test/error-contract.test.mjs
git commit -m "fix(llm-ltt): 502/503/504 khong giai ma duoc van phai thu lai (V-19)

Than cua Cloudflare khi origin dut khong the co ltt_error vi yeu cau chua toi may A.
Fail-closed o day bien su co ha tang tam thoi thanh mat luot cua khach.
Do 23/09: luot chet sau 886 ms du loi mang san retryAfter 60 s.

Than co ltt_error van do registry quyet dinh - doi chung am trong test.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Chịu được quá tải kéo dài (V-23)

**Vì sao:** 23/09 máy B mất GPU; mọi lượt nhận `provider_overloaded` → `RATE_LIMIT` (mã **được**
thử lại) nhưng hết số lần thử thì `turn/end kind=error` — lượt chết. Bản đồ đường đi hứa *"người
thứ tám xếp hàng, không bị từ chối"*.

**Files:**
- Modify: `D:\LTTCODEAPP\desktop\sidecar\presets\standard\agent.cordis.yml`

**Interfaces:**
- Consumes: khoá `maxOverflowRetries` đã có trong preset (đặt 2 ở 0.2.3 cho compaction).
- Produces: không đổi API; chỉ đổi số lần thử và cách tôn trọng `retryAfter`.

- [ ] **Step 1: Đọc cấu hình thử lại hiện tại**

```bash
cd /d/LTTCODEAPP && grep -n "maxOverflowRetries\|retry\|maxRetries" desktop/sidecar/presets/standard/agent.cordis.yml
```

Ghi lại giá trị hiện có trước khi đổi — plan này **không** đoán trước con số vì nó phụ thuộc
khoá upstream mà bản 0.1.6-alpha.2 phơi ra.

- [ ] **Step 2: Đặt số lần thử theo `retryAfter`, không theo số cố định**

Nguyên tắc: tổng thời gian chờ phải **đủ để một model nạp xong** (đo 23/09: `llama-server` nạp
mất ~90 s) chứ không phải một số lần cố định. Nếu upstream chỉ cho số lần, đặt sao cho
`số lần × retryAfter trung bình ≥ 180 s`.

- [ ] **Step 3: Kiểm bằng `check_composition`**

```bash
cd /d/LTTCODEAPP && node tools/check_composition.mjs --patch desktop/sidecar/profile-template/lttcode/ltt-lock.patch.yml
```

⚠️ Thiếu cờ `--patch` ⇒ 6 gate lock **đỏ giả** (bẫy đã ghi trong STATE.md).

- [ ] **Step 4: Commit**

```bash
cd /d/LTTCODEAPP
git add desktop/sidecar/presets/standard/agent.cordis.yml
git commit -m "fix(preset): chiu duoc qua tai keo dai thay vi giet luot (V-23)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: `409 insufficient_credit` phải nói cần bao nhiêu, còn bao nhiêu (V-22)

**Vì sao:** `luong.py:1307` viết `except ThieuCredit:` — bắt mà **không giữ ngoại lệ** — rồi dựng
`model_failure(...)` không truyền `limit`/`actual`. Lớp `ThieuCredit` sinh ra chính để mang
`can`/`con` (`luong.py:88-103`), docstring của nó cảnh báo đây là hồi quy đã tìm ra **14/09/2026**
ở cửa job. Hợp đồng v1 có sẵn chỗ chứa (`error_contract.py:125`). Hậu quả đo được 23/09: chính
phiên chẩn đoán quy nhầm sang tài khoản khác, mất ~20 phút.

**Files:**
- Modify: `platform_core\runtime_noi_bo\luong.py:1306-1309`
- Test: `tests\test_2300_thieu_credit_kem_so.py`

**Interfaces:**
- Consumes: `ThieuCredit(can: int | None, con: int | None)`; `model_failure(code, *, http_status, request_id, field, limit, actual, retry_after_s)` — cả hai đã có.
- Produces: thân lỗi 409 có `ltt_error.limit` = cần, `ltt_error.actual` = còn.

- [ ] **Step 1: Viết phép kiểm đỏ**

Tạo `tests/test_2300_thieu_credit_kem_so.py`:

```python
"""409 insufficient_credit phai mang theo can/con - V-22.

Hoi quy nay da tim ra mot lan o cua job ngay 14/09/2026; 23/09 no quay lai o cua
stream va lam mot phien chan doan di sai 20 phut vi khong doc duoc "can bao nhieu,
con bao nhieu".
"""
from __future__ import annotations

from platform_core.llm.model_failure import model_failure


def test_model_failure_mang_can_va_con():
    f = model_failure("insufficient_credit", http_status=409,
                      request_id="r1", limit=17, actual=13)
    than = f.than_v1() if hasattr(f, "than_v1") else f.ltt_error
    assert than["limit"] == 17
    assert than["actual"] == 13


def test_doi_chung_am_khong_truyen_thi_khong_co_hai_truong():
    f = model_failure("insufficient_credit", http_status=409, request_id="r1")
    than = f.than_v1() if hasattr(f, "than_v1") else f.ltt_error
    assert "limit" not in than
    assert "actual" not in than
```

⚠️ Tên hàm dựng thân (`than_v1` hay thuộc tính `ltt_error`) **phải tra lại** trong
`platform_core/llm/model_failure.py` trước khi chạy; hai nhánh `hasattr` ở trên là để test
không chết vì đoán sai tên, nhưng **phải sửa lại cho gọn** sau khi biết tên thật.

- [ ] **Step 2: Chạy để chắc nó xanh (đây là phép kiểm hạ tầng sẵn có)**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2300_thieu_credit_kem_so.py -q
```

Nếu đỏ: `model_failure` chưa đưa `limit`/`actual` vào thân v1 ⇒ **đó là lỗi thứ hai**, sửa trước.

- [ ] **Step 3: Thêm phép kiểm cho đúng chỗ đang hỏng**

```python
def test_cua_stream_khong_duoc_danh_roi_can_con():
    """Doc AST cua luong.py: nhanh bat ThieuCredit phai GIU ngoai le va truyen so."""
    import ast
    import pathlib

    cay = ast.parse(pathlib.Path("platform_core/runtime_noi_bo/luong.py").read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.ExceptHandler):
            continue
        ten = getattr(nut.type, "id", None)
        if ten != "ThieuCredit":
            continue
        assert nut.name is not None, "bat ThieuCredit ma khong giu ngoai le - can/con bi danh roi"
        goi = [n for n in ast.walk(nut) if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "model_failure"]
        assert goi, "nhanh ThieuCredit phai dung model_failure"
        kw = {k.arg for g in goi for k in g.keywords}
        assert {"limit", "actual"} <= kw, f"thieu limit/actual, dang co: {sorted(kw)}"
```

- [ ] **Step 4: Chạy để chắc nó ĐỎ**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2300_thieu_credit_kem_so.py -q
```

Kỳ vọng: **FAIL** với `bat ThieuCredit ma khong giu ngoai le`.

- [ ] **Step 5: Sửa tối thiểu**

`platform_core/runtime_noi_bo/luong.py`, thay đúng bốn dòng:

```python
        except ThieuCredit as e:
            # V-22: lop nay sinh ra de MANG can/con (xem docstring cua no).
            # Danh roi hai so nay tung la hoi quy 14/09 o cua job; 23/09 no quay
            # lai o day. Hop dong v1 co san cho chua: limit = can, actual = con.
            yield _loi_typed(model_failure(
                "insufficient_credit", http_status=409, request_id=tk.request_id,
                limit=e.can, actual=e.con))
            return
```

- [ ] **Step 6: Chạy để chắc nó XANH**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2300_thieu_credit_kem_so.py -q
```

- [ ] **Step 7: Chạy cụm LLM để chắc không vỡ chỗ khác**

```bash
cd /d/LTTSTUDIOSAPP && python tools\thanh_phan.py --test ltt_llm
```

rồi chạy đúng danh sách tệp nó in ra, `-n` ≤ 2 nếu chạy ngoài khoá.

- [ ] **Step 8: Kiểm số tệp test không trùng**

```bash
cd /d/LTTSTUDIOSAPP && py tools/check_so_test.py
```

- [ ] **Step 9: Commit**

```bash
cd /d/LTTSTUDIOSAPP
git add platform_core/runtime_noi_bo/luong.py tests/test_2300_thieu_credit_kem_so.py
git commit -m "fix(llm): 409 insufficient_credit mang lai can/con (V-22)

luong.py:1307 bat ThieuCredit ma khong giu ngoai le nen hai so can/con bi danh roi,
du lop ThieuCredit sinh ra chinh de mang chung va hop dong v1 co san cho chua.
Hoi quy nay da tim ra mot lan o cua job 14/09; 23/09 no quay lai o cua stream va
lam mot phien chan doan di sai 20 phut.

Doi chung: doc AST de chan nhanh bat-ma-khong-giu quay lai.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Khoá LTTCODE có quyền đọc số dư (N-04, phần nền tảng)

**Vì sao:** `/api/v1/credits/balance` đã có, nhưng khoá app tự phát lúc đăng nhập chỉ mang
`(tools:read, jobs:create, jobs:read)`. Đo trên production 23/09: cả ba khoá LTTCODE đang sống
đều vậy ⇒ thêm màn hình số dư sẽ nhận **403**.

**🔴 CHẶN — cần chủ dự án quyết trước khi làm:** đổi `SCOPES_KHOA` chỉ ăn vào khoá **cấp mới**.
Khách đã đăng nhập vẫn mang khoá cũ. Hai lối: (a) bắt đăng nhập lại; (b) nền tảng nâng quyền cho
khoá đang có. **Không tự chọn.**

**Files:**
- Modify: `apps\lttcode\dang_nhap.py:27,32`
- Test: `tests\test_2301_scope_khoa_lttcode.py`

**Interfaces:**
- Consumes: `platform_core.public_api.scopes.SCOPE_CREDITS_READ` (đã có — dùng bởi
  `server/api/usage_routes.py`).
- Produces: `SCOPES_KHOA` có thêm `SCOPE_CREDITS_READ`.

- [ ] **Step 1: Viết phép kiểm đỏ**

```python
"""Khoa LTTCODE phai doc duoc so du - N-04."""
from apps.lttcode.dang_nhap import SCOPES_KHOA
from platform_core.public_api.scopes import (SCOPE_CREDITS_READ, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ)


def test_khoa_lttcode_doc_duoc_so_du():
    assert SCOPE_CREDITS_READ in SCOPES_KHOA


def test_khong_no_them_quyen_ngoai_bon_quyen_da_chot():
    assert set(SCOPES_KHOA) == {SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE,
                                SCOPE_JOBS_READ, SCOPE_CREDITS_READ}
```

- [ ] **Step 2: Chạy để chắc nó ĐỎ**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2301_scope_khoa_lttcode.py -q
```

- [ ] **Step 3: Sửa tối thiểu**

`apps/lttcode/dang_nhap.py`:

```python
from platform_core.public_api.scopes import (SCOPE_CREDITS_READ, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ)

#: N-04: them credits:read de app hien duoc so du. KHONG them usage:read o day -
#: mot quyen chi cap khi co man hinh dung toi no.
SCOPES_KHOA = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ, SCOPE_CREDITS_READ)
```

- [ ] **Step 4: Chạy để chắc nó XANH + cụm lttcode**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2301_scope_khoa_lttcode.py -q
cd /d/LTTSTUDIOSAPP && python tools\thanh_phan.py --test lttcode
```

- [ ] **Step 5: Commit**

```bash
cd /d/LTTSTUDIOSAPP
git add apps/lttcode/dang_nhap.py tests/test_2301_scope_khoa_lttcode.py
git commit -m "feat(lttcode): khoa dang nhap co them credits:read (N-04)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Cửa sổ Tài khoản hiện số dư (N-04, phần app)

**Phụ thuộc:** Task 4 đã deploy, và chủ dự án đã chốt cách xử lý khoá cũ.

**Files:**
- Modify: `D:\LTTCODEAPP\desktop\src\account.ts`

**Interfaces:**
- Consumes: `GET /api/v1/credits/balance` → `{ balance: number, unit: "credit", as_of: string }`.
- Produces: dòng số dư dưới dòng trạng thái đăng nhập; không đổi API nào của app.

- [ ] **Step 1: Đọc cách cửa sổ này gọi mạng hiện tại**

```bash
cd /d/LTTCODEAPP && grep -n "fetch\|invoke\|api" desktop/src/account.ts | head -20
```

Dùng đúng đường đã có (app không gọi thẳng HTTPS từ cửa sổ này nếu host đã có lệnh riêng).

- [ ] **Step 2: Hiện số dư, và hiện cả khi hỏng**

Nguyên tắc bắt buộc: **không có số ⇒ nói là không lấy được**, đừng để trống như thể là 0.

- [ ] **Step 3: Kiểm trên app đã cài**

Mở cửa sổ Tài khoản, xác nhận thấy số dư thật. Đối chiếu bằng truy vấn sổ credit của chính
tài khoản đó.

- [ ] **Step 4: Commit**

---

## Task 6: Canh cửa `/health/ready` của máy B (N-05 — sửa lại so với đề xuất ban đầu)

**🔴 Đính chính quan trọng:** đề xuất ban đầu ("thêm thông tin GPU vào `/live`") là **SAI**.
`llm_gateway/api.py` ghi rõ lệnh cấm: *"⛔ KHÔNG thêm bất cứ thứ gì vào đây. Mỗi trường thêm vào
là một thứ rò ra cho người chưa xác thực"*. Và **`/health/ready` đã làm đúng việc đó rồi**:

```python
if not GPU.thay_du_hai_card():
    return JSONResponse(status_code=503, content={"ok": False, "ly_do": "thieu_card"})
```

Docstring của nó còn ghi: *"`/live` xanh suốt sự cố 23/08 (CUDA hỏng) và suốt cả ca một card
rụng khỏi hệ thống"*. Nghĩa là **tính năng có đủ, chỉ không ai canh cửa đó.** Ngày 23/09 hai card
rụng lúc 16:20 và không có gì báo; phiên chẩn đoán gọi nhầm `/live` (200) rồi kết luận sai.

**Files:**
- Create: `tools\canh_cong_may_b.py`
- Test: `tests\test_2302_canh_cong_may_b.py`

**Interfaces:**
- Consumes: `GET http://192.168.2.66:8299/health/ready` → 200 `{"ok":true}` hoặc 503 `{"ok":false,"ly_do":"thieu_card"}`.
- Produces: `kiem(url, *, doc=...) -> dict` với khoá `ok: bool`, `ly_do: str`, `http: int`;
  mã thoát 0 khi 200, **1 khi khác** — để cắm vào Task Scheduler.

- [ ] **Step 1: Viết phép kiểm đỏ (không gọi mạng thật)**

```python
"""Bo canh /health/ready may B - N-05."""
from tools.canh_cong_may_b import kiem


def test_200_la_san_sang():
    kq = kiem("http://x/health/ready", doc=lambda u: (200, {"ok": True}))
    assert kq["ok"] is True and kq["http"] == 200


def test_503_thieu_card_la_bao_dong():
    kq = kiem("http://x/health/ready", doc=lambda u: (503, {"ok": False, "ly_do": "thieu_card"}))
    assert kq["ok"] is False and kq["ly_do"] == "thieu_card"


def test_khong_noi_duoc_cung_la_bao_dong():
    def hong(_u):
        raise OSError("khong noi duoc")
    kq = kiem("http://x/health/ready", doc=hong)
    assert kq["ok"] is False and "khong_noi_duoc" in kq["ly_do"]
```

- [ ] **Step 2: Chạy để chắc nó ĐỎ** (`ModuleNotFoundError`)

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2302_canh_cong_may_b.py -q
```

- [ ] **Step 3: Viết bộ canh**

```python
"""canh_cong_may_b.py - canh cua /health/ready cong LLM may B.

🔴 VI SAO TON TAI. Ngay 23/09/2026 hai card cua may B rung khoi bus PCIe luc 16:20
   (long day PSU). `/live` van tra 200, be mat van khop cay, ping va cong deu mo -
   moi phep do o tang HTTP deu XANH trong khi khong model nao chay duoc. Phien chan
   doan goi nham `/live` roi ket luan sai la "dong khach tranh suat", mat ~40 phut.

   `/health/ready` DA tra 503 `thieu_card` dung luc ay. Khong ai hoi no.
"""
from __future__ import annotations

import json
import sys
import urllib.request

MAC_DINH = "http://192.168.2.66:8299/health/ready"


def _doc_that(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"user-agent": "ltt-canh-cong/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def kiem(url: str = MAC_DINH, *, doc=_doc_that) -> dict:
    """Hoi mot lan. KHONG bao gio nem: moi loi deu la 'chua san sang'."""
    try:
        http, than = doc(url)
    except Exception as e:  # noqa: BLE001 - loi mang cung la mot cau tra loi
        return {"ok": False, "http": 0, "ly_do": f"khong_noi_duoc: {type(e).__name__}"}
    if http == 200 and than.get("ok") is True:
        return {"ok": True, "http": 200, "ly_do": ""}
    return {"ok": False, "http": http, "ly_do": str(than.get("ly_do") or f"http_{http}")}


def main() -> int:
    kq = kiem(sys.argv[1] if len(sys.argv) > 1 else MAC_DINH)
    print(json.dumps(kq, ensure_ascii=False))
    return 0 if kq["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Chạy để chắc nó XANH**

```bash
cd /d/LTTSTUDIOSAPP && python -m pytest tests/test_2302_canh_cong_may_b.py -q
```

- [ ] **Step 5: Chạy thật một lần**

```bash
cd /d/LTTSTUDIOSAPP && python tools/canh_cong_may_b.py
```

Kỳ vọng hôm nay: `{"ok": true, "http": 200, "ly_do": ""}`.

- [ ] **Step 6: Ghi vào runbook chẩn đoán**

Thêm vào `docs/ltt_llm_dual/LOI_MODEL_RUNBOOK.md` một mục: *"model không chạy — hỏi cửa nào"*,
nêu rõ **`/live` không trả lời được câu đó**, phải hỏi `/health/ready` của **cổng máy B**
(không phải của máy A).

- [ ] **Step 7: Commit**

```bash
cd /d/LTTSTUDIOSAPP
git add tools/canh_cong_may_b.py tests/test_2302_canh_cong_may_b.py docs/ltt_llm_dual/LOI_MODEL_RUNBOOK.md
git commit -m "feat(giam-sat): canh /health/ready may B - 503 thieu_card khong ai hoi (N-05)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Cắm vào lịch (việc của chủ dự án hoặc một task riêng)**

Task Scheduler chạy mỗi 2 phút; mã thoát 1 ⇒ báo. **Không tự tạo task hệ thống trong plan này.**

---

## Task 7: Phát hành bắt buộc có ghi chú (V-20)

**Files:** Modify `D:\LTTCODEAPP\tools\release.ps1`

- [ ] **Step 1:** Đổi `-Notes` thành tham số **bắt buộc** (`[Parameter(Mandatory = $true)]`), và
  thêm chốt từ chối chuỗi rỗng/trắng:

```powershell
if ([string]::IsNullOrWhiteSpace($Notes)) {
  throw "-Notes rong: khach se khong thay dong 'co gi moi' nao (V-20)"
}
```

- [ ] **Step 2:** Kiểm bằng cách chạy `release.ps1` thiếu `-Notes` ⇒ phải dừng ngay, **không build**.
- [ ] **Step 3:** Sửa hai mục `notes` rỗng của 0.2.5/0.2.6 trong manifest kênh dev (sao lưu
  `.bak-<ngày>` trước — `AGENTS.md` §4).
- [ ] **Step 4:** Commit.

---

## Task 8: Nói rõ yêu cầu `User-Agent` cho khách lập trình (N-06)

**Vì sao:** đo 23/09 — `Python-urllib` trần bị Cloudflare trả **403 `error code: 1010`**; `curl`,
`python-requests`, UA trình duyệt đều lọt. Khách dùng thư viện chuẩn của Python mà không đặt UA
sẽ bị chặn ở cửa và **không thấy lỗi nào của ta**.

- [ ] **Step 1:** Quyết (chủ dự án): nới quy tắc Cloudflare cho `/api/v1`, **hay** ghi rõ trong
  tài liệu. Plan này mặc định lối tài liệu vì không đụng hạ tầng.
- [ ] **Step 2:** Thêm vào `docs/PUBLIC_API/` một đoạn: *"đặt `User-Agent` cho mọi yêu cầu"*, kèm
  ví dụ `urllib` có UA.
- [ ] **Step 3:** Commit.

---

## Task 9 (CHẶN — chờ chủ dự án duyệt): cache bộ cài ở biên

**Vì sao:** bộ cài 279 MB phục vụ với `Cache-Control: no-store`, `cf-cache-status: BYPASS` ⇒ mỗi
lượt tải kéo trọn 279 MB từ máy nhà qua tunnel. `/nexus/dl/` **đã** được mở ngoại lệ cache với
đúng lập luận này cho một tệp 26 MB.

⛔ Đụng `server/app.py` — tệp dùng chung của nền tảng (luật 9). **Không làm khi chưa được duyệt.**

- [ ] **Step 1:** Thêm `/lttcode/dl/` vào cùng nhánh với `/nexus/dl/` trong middleware.
- [ ] **Step 2:** Deploy, rồi đo lại `cf-cache-status`: phải chuyển `BYPASS` → `MISS` → `HIT`.
- [ ] **Step 3:** Commit.

---

## Task 10 (CHỜ D1): bổ sung từ sổ lỗi lượt diễn tập

Lượt diễn tập D1 đang chạy khi plan này được viết (lượt 7, bước 168). **Khi nó kết thúc:**

- [ ] **Step 1:** Chạy bộ đo tổng kết trên phiên `session-dd80eaf3` (script đã có:
  `scratchpad/d1/b30_do_toan_dien.js`), lấy số cuối.
- [ ] **Step 2:** Đọc báo cáo agent viết ra (`docs/reports/dien-tap-khoi-phuc-2026-09-23.md`) và
  bốn kết luận bằng số của nó.
- [ ] **Step 3:** Mỗi lỗi mới ⇒ một mục **V-NN** trong `SO_LOI_VAN_HANH.md` với bằng chứng đo.
- [ ] **Step 4:** Mỗi lỗi đủ nặng ⇒ thêm một Task vào **chính plan này**, theo đúng khuôn:
  files / interfaces / test đỏ / sửa tối thiểu / test xanh / commit.
- [ ] **Step 5:** Ba việc đã biết chắc sẽ có từ D1, giữ chỗ sẵn:
  - đường khôi phục thiếu bước `alembic upgrade head` sau khi nạp dump (agent đang kết luận);
  - `restore.ps1` không có chế độ diễn tập thật;
  - bản sao lưu nằm trên chính máy production.

---

## Thứ tự thi hành

| Đợt | Task | Vì sao thứ tự này |
|---|---|---|
| 1 | **1, 3** | Hai lỗi đang **chặn chính LTTCODE** làm việc. Làm trước thì mọi đợt sau đo được tử tế |
| 2 | **6, 7** | Rẻ, không đụng đường chạy của khách, đóng ngay hai lỗ giám sát/phát hành |
| 3 | **2** | Cần đọc khoá upstream trước; làm sau khi 1 đã xanh để phân biệt được nguyên nhân |
| 4 | **4 → 5** | Chỉ chạy sau khi chủ dự án chốt cách xử lý khoá cũ |
| 5 | **8, 9** | 9 chặn tới khi được duyệt |
| 6 | **10** | Sau khi D1 kết thúc |

## Tự rà plan

**Độ phủ:** V-19 → Task 1 · V-20 → Task 7 · V-21 → **chưa có task** (mô tả công cụ
`subagent_doc_nhanh`, để lại cho đợt sau vì cần đo lại hành vi guard trước) · V-22 → Task 3 ·
V-23 → Task 2 · N-04 → Task 4+5 · N-05 → Task 6 · N-06 → Task 8 · N-01/N-02/N-03 → **chưa có
task**, đúng chủ ý: ba mục ấy còn ở trạng thái NGHIÊN CỨU/CHỜ ĐO, chưa đủ chín để viết bước.

**Chỗ còn mơ hồ đã đánh dấu thay vì giấu:** Task 2 không chốt con số vì phụ thuộc khoá upstream
chưa đọc; Task 3 Step 1 ghi rõ phải tra lại tên hàm dựng thân v1; Task 5 phụ thuộc quyết định
của chủ dự án.

**Nhất quán tên:** `SCOPES_KHOA`, `model_failure(limit=, actual=)`, `ThieuCredit.can/.con`,
`kiem(url, *, doc)`, `lttWireError(value, options)` — đã đối chiếu với mã thật khi viết plan.
