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
- **Số tệp test:** số cao nhất đang dùng trên MỌI cây là **2504** (đo 23/09 khi dựng cây
  `sua-d1`). Dùng số **≥ 2505** chưa ai dùng; chạy `py tools/check_so_test.py` sau khi thêm
  để chắc không tăng trùng lặp. ⚠️ Dải 2300–2319 ghi ở bản đầu của plan là **SAI** — số đó
  đã có phiên khác dùng.
- **Deploy:** thứ tự bắt buộc **máy B trước, máy A sau**. Deploy cần gate xanh trên đúng SHA.
- **Máy B là máy dùng chung:** trước khi đo hiệu năng, kiểm `http://192.168.2.66:8299/health/ready`
  — 503 `thieu_card` nghĩa là **không đo được gì cả**, dừng và báo.


## Tiến độ (cập nhật 23/09 ~21:35)

> Cách tính: mỗi task 1 đơn vị · **xong = 1** · **xong một phần = 0,5** · đang chạy chưa xong = 0.
> Không ước lượng theo cảm giác. "Đang chạy" KHÔNG được tính điểm — hôm nay đã có bốn lần một
> việc trông sắp xong rồi chết giữa chừng.

### Phần A — sửa lỗi: **10 / 10 = 100 %** (xong 23/09 ~21:30)

| Task | Việc | Trạng thái |
|---|---|---|
| 1 | V-19 cổng 5xx phải thử lại | ✅ `87f752a` · 116/116 |
| 2 | V-23 chịu quá tải kéo dài | ✅ `977653f` · 28/28 · lộ thêm V-24 |
| 3 | V-22 `409` kèm cần/còn | ✅ `94d4edaa` · 3 phép + 2823 cụm provider |
| 4 | Khoá có `credits:read` | ✅ `c622589c` · chỉ ăn vào khoá **cấp mới**, khách cũ không bị bắt làm gì |
| 5 | Cửa sổ Tài khoản hiện số dư | ✅ `0c6df5a` · 6 phép · lấy không được thì hiện `—`, **không bao giờ `0`** |
| 6 | Canh `/health/ready` máy B | ✅ `5cdba614` + `dbe3fc71` · 4 phép |
| 7 | `-Notes` bắt buộc | ✅ `8ed9ecb` · manifest dev đã vá |
| 8 | Tài liệu `User-Agent` | ✅ `c23c7cce` · đã gộp `main` |
| 9 | Cho Cloudflare cache bộ cài | ✅ `e17f1bc3` · **đã deploy + đo**: `no-store` → `immutable`, BYPASS → MISS → **HIT** (Age tăng 29→37) |
| 10 | Bổ sung từ sổ lỗi D1 | ✅ `67f412f6` — số đo cuối đã ghi, V-19…V-24 đã lập, **`restore.ps1` đã vá** (7 phép, có đối chứng âm). Off-site đã dựng + cắm lịch. Sổ đăng ký đã vào mẫu backup (`8a46784c`) — **hết việc mở** |

### Phần B — nâng năng lực: **2,5 / 10 = 25 %** (không đổi)

| Task | Việc | Trạng thái |
|---|---|---|
| 11 | A1 nút "Chạy tiếp" | 🟡 **0,5** — hàm `coTheNoiLai` + test xong (`670770b`); **nút giao diện CHẶN**: slot không có hàm resend, cần thiết kế mới |
| 12 | C2 nén bằng 3.5 | 🟡 **0,5** — mã xong (`3326d7f`), **chờ đo** tốc độ + chất lượng tóm tắt trên phiên dài |
| 13 | MCP dùng thật (nay 0/166) | ⬜ chưa |
| 14 | Gỡ trần 50 của kế hoạch/mục tiêu | ⬜ chưa |
| 15 | Agent do người dùng định nghĩa | 🟡 **0,5** — **đã có sẵn và đã chạy thật**: `~/.agents/agents/*.md` (hai tầng), ghim model cần **cả `provider` lẫn `model`**. Lộ lỗi **V-25**: khoá `tools:` bị **bỏ qua âm thầm** — người dùng tưởng khoá được agent con, thực tế nó có đủ công cụ host. Còn: tài liệu + vá cảnh báo + bằng chứng trong app |
| 16 | Credit mỗi lượt cạnh token | ⚫ **ĐÓNG — chặn ở tầng engine.** Tra ba vòng, mỗi vòng bác một phương án: (1) cổng không có trường credit, quyết toán chạy sau byte cuối; (2) `client.js` là **loopback remote page ⇒ không có Tauri IPC**; (3) từ sidecar thì `TokenUsage` là interface đóng và projection **khoá cứng đồng bộ, cấm I/O**. Cần hạ tầng engine mới ⇒ chuyển `HANG_MUC_BAN_SAU.md`. **Không chỗ nào hiện số tiền sai** |
| 17 | Giảm độ trễ mỗi bước | ⬜ chưa |
| 18 | Chạy tiếp khi đóng app | 🟡 **0,5** — tra xong: **phần lớn đã có** (khay giữ sidecar sống, autostart, `lttcode-cli.exe` chạy thật 60,7 s). H18 chấm lại 45 → 78. Còn: chủ dự án quyết có làm scheduler mức hệ điều hành không |
| 19 | Git/PR thành công cụ gốc | 🟡 **0,5** — đã chấm `lxj808624/dsh-tool-git` (≈ 51/100). **Quyết định: bundle nhưng CHỈ lấy nhóm chỉ-đọc** (`git_status/diff/log/show`) — nhóm ghi có `add -A` không chặn, không quét bí mật, và `stash -u` ngoài hàng rào (cuốn mất tệp `??` của phiên khác). Còn: xác minh Cordis tắt được công cụ lẻ, rồi bundle |
| 20 | Khởi động app (17→49→107 s) | ⬜ chưa |

### Ngoài plan — việc sinh ra từ lượt diễn tập D1

| Việc | Trạng thái |
|---|---|
| Đồng bộ off-site ra Google Drive | ✅ `a70512f4` — chạy thật 7 bản/1,11 GB/0,9 phút/0 lỗi; đã cắm lịch `LTTStudioBackupOffSite` 03:00 hằng ngày, chạy thử dưới trình lập lịch **kết quả 0** |
| Ba tệp sổ đăng ký ngoài mẫu backup | ✅ `8a46784c` (đã gộp `main`) — tra ra **chỉ hai** tệp cần sao lưu, không phải ba: `lttcode_releases.json` + `nexus_versions.json` (chứa chữ ký minisign + SHA từng bản đã phát ⇒ **không dựng lại được**). `translations/` **sinh lại được**: `setup\2-cai-dat.ps1:683-694` robocopy nó từ kho mã mỗi lần deploy ⇒ cố ý để ngoài. 7 phép, đỏ trước (kiểm trên `HEAD` cũ) xanh sau |
| `app.env` cất ở ổ D | ✅ ghi thành **quyết định có chủ ý** của chủ dự án 23/09 trong `RUNBOOK_KHOI_PHUC.md` §8 (D là ổ vật lý khác C ⇒ chịu được hỏng một ổ), kèm phần nó **KHÔNG** che: cháy máy · mất trộm · ransomware mã hoá cả hai ổ |
| Đường diễn tập khôi phục + đối chứng âm | ✅ `3f5b8a8d` (gộp `main`, 1 286 dòng) |

### Đọc con số này thế nào

**65 % và 25 % không so sánh được với nhau.** Phần A là mười lỗi đã biết, mỗi cái vài chục dòng.
Phần B là mười năng lực, trong đó ba cái là dự án riêng. Cộng hai phần thành một con số là vô nghĩa.

**Bốn task Phần B ở mức 0,5 đều dừng ở đúng chỗ đáng dừng**, không phải bỏ dở: Task 11 chặn vì
slot giao diện không có sẵn đường nối; Task 12 chờ phép đo mà một lượt text không tạo ra được;
Task 15/18/19 dừng sau khi tra ra **năng lực đã có sẵn** — và đó là kết quả có giá trị hơn việc
viết thêm mã.


## Bản đồ làn — chạy song song thế nào cho nhanh mà không hỏng

> Phần này **không phải lý thuyết**: mọi ràng buộc dưới đây đều là thứ đã va phải trong ngày
> 23/09. Thiếu nó thì người sau hoặc chạy tuần tự (mất hết tốc độ), hoặc cho hai làn cùng ghi
> một kho rồi hỏng việc của nhau.

### Năm ràng buộc cứng

| # | Ràng buộc | Vì sao — bằng chứng 23/09 |
|---|---|---|
| R1 | **Một kho = MỘT làn được ghi.** Không phải "không sửa trùng tệp" mà là **chỉ số git dùng chung** | Chính phiên điều phối đã phá luật này: commit `4b56a79` vào `D:\LTTCODEAPP` trong lúc làn `lttcode-ma` đang làm ở đó. Làn kia phát hiện và báo lại. Lần đó không đụng tệp nên thoát, lần sau thì không chắc |
| R2 | **Làn cần mở app LTTCODE: chỉ một, và phải độc quyền** | App single-instance; bộ lái từ chối mở khi app đang chạy. Hai làn cùng lái là chồng phím lên nhau |
| R3 | **Làn tra nguồn KHÔNG commit gì cả**, kể cả tài liệu — báo về, điều phối ghi | Để nó không tranh chỉ số git với làn đang ghi cùng kho (R1) |
| R4 | **Lệnh nặng đi qua MỘT khoá `cpu_nhieu` cho cả máy**, `-n` ≤ 7, **không giữ khoá lúc chờ** | Luật chốt 23/09 sau sự cố gate + agent cộng dồn 14/20 lõi; và một làn giữ khoá 22 phút cho lệnh nâng quyền chờ 90 phút trong khi GPU rảnh 9 % |
| R5 | **Làn dùng model LTT: đếm suất máy B (3.8 ba · 3.5 bốn)** | 23/09: ba máy LTTCODE cùng chạy ⇒ `provider_overloaded` 48 sự kiện/90 phút. Nhiều làn gọi model cùng lúc sẽ tự làm nghẽn mình |

### Ba loại làn

| Loại | Ghi gì | Chạy song song được với |
|---|---|---|
| **Làn mã** | commit vào **một** kho | Làn mã của kho KHÁC · làn tra nguồn · (không với làn app cùng kho) |
| **Làn app** | thường không commit; lái app đã cài để đo | Mọi làn mã — nhưng **chỉ một làn app tại một thời điểm** |
| **Làn tra nguồn** | **không gì cả** | Tất cả |

### Xếp làn cho các task còn lại

| Làn | Kho / cây | Task | Song song được với |
|---|---|---|---|
| `nen-tang` | worktree `D:\LTTSTUDIOSAPP-*` | 10 (vá `restore.ps1` thêm `alembic upgrade head`) | mọi làn khác |
| `lttcode-ma` | `D:\LTTCODEAPP` cây chính | 11 Step 5 (nút "Chạy tiếp" — **cần thiết kế trước**), 16 (chờ chủ dự án chọn nguồn số) | `nen-tang`, `tra-nguon` |
| `do-app` | không commit · **độc quyền app** | 13 (MCP dùng thật), 14 (gỡ trần kế hoạch), 20 (khởi động app), và **phép đo còn nợ của 12** | mọi làn mã |
| `tra-nguon` | **không commit** | 17 Step 1 (tách độ trễ ba phần), đánh giá `dsh-tool-git` cho 19 | tất cả |

⚠️ **Task 12 và 13/14/20 đều cần `do-app`** ⇒ chúng **không** song song với nhau, phải xếp hàng
trong cùng một làn. Đó là nút thắt thật của đợt sau, không phải số lượng agent.

### Đo được gì về tốc độ hôm nay

| Đợt | Làn chạy cùng lúc | Kết quả |
|---|---|---|
| 1 | 2 (lttcode + nền tảng) | 4 task xong |
| 2 | 3 (mã + tài liệu + tra nguồn) | 3 task xong + 3 câu năng lực được trả lời |
| 3 | 2 (credit nền tảng + credit app) | 3 task xong, 1 dừng đúng luật |

**Trần thật không phải số agent.** Ba đợt trên đều dừng ở 2–3 làn, và lý do luôn là R1 (số kho
có thể ghi song song) chứ không phải thiếu CPU — máy chạy 5–48 % suốt. Muốn nhanh hơn thì phải
**tăng số worktree**, không phải tăng số agent trên cùng một cây.

### Ba thứ phải viết vào MỌI brief agent

Thiếu một trong ba, agent sẽ làm sai theo đúng cách đã thấy hôm nay:

1. **"KHÔNG chạy gate ở bất kỳ mức nào"** — nếu không nó sẽ tự chạy và hoặc tốn 16 phút, hoặc
   vô tình nâng thành L3.
2. **"Không dừng lượt để chờ — chờ ở tiền cảnh"** — làn `credit-scope` đã dừng lượt giữa chừng
   để "đợi thông báo việc nền", bỏ dở 4 tệp chưa commit.
3. **"Chỗ nào plan sai so với mã thật thì nói thẳng, đừng lặng lẽ sửa"** — nhờ câu này mà ba lỗi
   trong plan lộ ra: `maxOverflowRetries` sai chỗ, `than_v1()` sai tên, `node --test <thư mục>`
   sai lệnh.

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

## Task 1 ✅ XONG (`87f752ae`): Lỗi cổng 5xx phải được thử lại (V-19)

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

// ⚠️ BAN VA NAY CHUA DU - xem ghi chu ben duoi.

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

🔴 **BẢN VÁ TRÊN LÀM VỠ MỘT PHÉP KIỂM SẴN CÓ — đã sửa khi thi hành (23/09).** Chỉ xét
`neutralCode === UPSTREAM_UNKNOWN_CODE` là chưa đủ: một thân **có** `ltt_error` với
`canonical_code: upstream_unknown` đi qua HTTP 502 thì **registry đã quyết**, phải giữ
`UPSTREAM_UNKNOWN`. Nó khác hẳn "thân không đọc được gì". Cách sửa đúng: thêm cờ
`structured: boolean` vào `DecodedFailure` (`errors.ts:106`, gán ở dòng 254) và **chỉ đè
khi `!structured`**.

- [ ] **Step 4: Chạy để chắc nó XANH**

```bash
cd /d/LTTCODEAPP && node --test plugins/llm-ltt/test/error-contract.test.mjs
```

Kỳ vọng: **PASS** toàn bộ tệp — 18 phép (bản đầu của plan ghi 9→12 là **sai**, tệp này
vốn đã có 15 phép).

- [ ] **Step 5: Chạy cả cụm llm-ltt để chắc không vỡ chỗ khác**

```bash
cd /d/LTTCODEAPP && node --test plugins/llm-ltt/test/*.test.mjs
```

⚠️ **Phải có `*.test.mjs`** — Node 24 không nhận thư mục làm đối số `--test`, đưa thư mục
vào sẽ ném `Cannot find module`, trông hệt như test đỏ. Kỳ vọng: PASS **116** phép (không
phải 110 như bản đầu của plan ghi).

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

## Task 2 ✅ XONG (`977653f`): Chịu được quá tải kéo dài (V-23)

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

## Task 3 ✅ XONG (`94d4edaa`): `409 insufficient_credit` phải nói cần bao nhiêu, còn bao nhiêu (V-22)

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

✅ **ĐÃ TRA (23/09) — plan đoán SAI, đây là tên thật:** `ModelFailure` là dataclass có
thuộc tính trực tiếp `.limit` / `.actual`, và phương thức dựng dict thân v1 tên là
**`as_detail()`** — không phải `than_v1()` và không phải thuộc tính `ltt_error`. Viết thẳng
`f.as_detail()`, bỏ hẳn nhánh `hasattr` phỏng đoán ở trên.

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

## Task 6 ✅ XONG (`5cdba614`): Canh cửa `/health/ready` của máy B (N-05 — sửa lại so với đề xuất ban đầu)

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

## Task 7 ✅ XONG (`8ed9ecb0`): Phát hành bắt buộc có ghi chú (V-20)

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

- [x] **Step 1: XONG 23/09 ~18:40** — số đo cuối của cả lượt D1:

| Chỉ số | Giá trị |
|---|---|
| Thời lượng | **347 phút** (5 h 47) · 1 355 dòng bản ghi |
| Lượt / bước | 7 / **231** |
| Gọi công cụ | **246** — `pwsh` 91 · `read` 49 · `edit` 40 · `write` 19 · `grep` 18 · `job_output` 13 · `todo_write` 6 · `glob` 6 · `subagent_doc_nhanh` 2 · `list_subagent_models` 1 · `tool_search` 1 |
| Lỗi công cụ | **13 = 5,3 %** (`pwsh` 12, `edit` 1) |
| Nén ngữ cảnh | **4 lần**: 188,6 · 243,7 · 173,5 · 115,8 s ⇒ **721,6 s = 12 phút**, bằng **3,5 %** thời lượng phiên |
| Thử lại | 12 |
| Thẻ xin duyệt | 1 |
| Độ trễ mỗi bước | p50 **23,7 s** · p90 70,9 s · max 328,9 s |
| Kết thúc 7 lượt | 1 `aborted` (phiên chính dừng) · **4 `error`** · 1 `interrupted` (khởi động lại máy) · **1 `completed`** |

⚠️ **Hai con số này làm xấu bảng chấm điểm so với lúc chấm giữa chừng, và phải cập nhật:**
- C2 (chi phí một lần nén): lúc chấm mới có 2 lần nén; thực tế **4 lần, tổng 12 phút**.
  Điểm 45 là **rộng lượng quá** — số đúng gần 40.
- A2 (tỉ lệ gọi công cụ hỏng): 4,8 % → **5,3 %** khi đủ 246 lần gọi.
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

## Thứ tự thi hành — Phần A

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
---

# PHẦN B — Nâng năng lực, không phải vá lỗi

> Phần A (Task 1–10) chỉ **dừng chảy máu**: làm hết vẫn đúng **69,7** điểm, vì không hạng mục nào
> trong `CHAM_DIEM_VAN_HANH_THAT_23_09.md` được nâng. Phần B nhắm vào chính các hạng mục điểm thấp.
>
> **Luật chung của Phần B — không có ngoại lệ:** mỗi task phải **đo trước, đo sau bằng CÙNG bộ đo**
> đã dùng ngày 23/09 (`scratchpad/d1/b30_do_toan_dien.js` cho phiên LTTCODE,
> `scratchpad/do_phien_claude.py` cho phiên Claude Code). Không có số trước/sau ⇒ **không được
> tick task**, dù mã đã chạy. Lý do: cả ngày 23/09 chứng minh rằng thứ trông xanh ở tầng trên vẫn
> có thể chết ở tầng dưới.

## Bảng nhắm

| Task | Hạng mục | Nay | Nhắm | Cách đo lại |
|---|---|---:|---:|---|
| 11 | A1 Lượt dài không đứt | 55 | 85 | Tỉ lệ lượt lỗi trong phiên ≥ 5 h — **hàm + test xong `670770b`, nút giao diện CHẶN: xem dưới** |
| 12 | C2 Chi phí một lần nén | 45 | 80 | Giây/lần nén, đo trên phiên thật — **mã xong `3326d7f`, CHỜ ĐO** |
| 13 | G1+G2 MCP dùng được thật | 45 | 85 | Số lần gọi MCP / tổng số lần gọi công cụ trong một phiên thật |
| 14 | E2+E3 Kế hoạch và mục tiêu | 50 | 85 | Có bằng chứng E2E; gỡ trần 50 |
| 15 | D3 Agent do người dùng định nghĩa | 40 | 85 | Định nghĩa được một agent bằng tệp và nó chạy |
| 16 | J1+J2 Chi phí hiện cho người dùng | 25 | 85 | Số dư + credit mỗi lượt hiện trên giao diện |
| 17 | A5 Độ trễ mỗi bước | 60 | 75 | p50/p90 giây mỗi bước |
| 18 | H18 Chạy nền / không cần mở app | 45 | 80 | Một việc chạy tới cùng khi app đã đóng |
| 19 | G4 Git/PR gốc | 45 | 80 | Tạo được nhánh + PR từ trong app, có đối chứng |
| 20 | L2 Khởi động app | 45 | 80 | Giây khởi động lạnh, đo 3 lần |

---

## Task 11 ⏳ HÀM XONG (`670770b`), NÚT GIAO DIỆN CHẶN: Lượt không chết vì lỗi nền tảng (A1: 55 → 85)

**Số đo hiện tại:** **4/7 lượt** của phiên D1 kết thúc bằng lỗi nền tảng. Phiên Claude Code cùng
máy cùng ngày: **0/nhiều lượt**. Đây là con số tệ nhất trong cả bảng 60 mục.

Task 1 và 2 (Phần A) chỉ sửa *phân loại* và *số lần thử*. Chúng không trả lời câu hỏi thật của
khách: **"lượt của tôi chết rồi, giờ sao?"** Hiện khách phải tự gõ lại từ đầu.

**Files:**
- Modify: `D:\LTTCODEAPP\plugins\ui-lttcode\src\client.js` (tin lỗi turn-error)
- Create: `D:\LTTCODEAPP\plugins\ui-lttcode\test\noi-lai.test.mjs`

**Interfaces:**
- Consumes: `lttErrorParts(message)` và `LTT_CANONICAL_KEYS` đã có trong `client.js`.
- Produces: nút "Chạy tiếp" trên tin lỗi khi mã lỗi thuộc nhóm tạm thời; bấm là gửi lại **đúng
  lượt vừa hỏng**, không phải một tin mới.

- [ ] **Step 1: Viết phép kiểm đỏ** — tin lỗi mã tạm thời phải có đường nối lại

```javascript
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { coTheNoiLai } from '../src/client.js'

test('loi tam thoi thi cho noi lai', () => {
  for (const ma of ['provider_overloaded', 'upstream_timeout', 'upstream_unreachable',
                    'internal_error', 'stream_idle_timeout']) {
    assert.equal(coTheNoiLai(ma), true, ma)
  }
})

test('loi cua chinh yeu cau thi KHONG cho noi lai', () => {
  // Noi lai mot yeu cau sai van sai - chi lam khach mat them tien.
  for (const ma of ['invalid_request', 'context_window_exceeded', 'insufficient_credit',
                    'unauthorized', 'model_not_found']) {
    assert.equal(coTheNoiLai(ma), false, ma)
  }
})

test('ma la thi KHONG cho noi lai', () => {
  assert.equal(coTheNoiLai('upstream_unknown'), false)
  assert.equal(coTheNoiLai('mot_ma_chua_tung_thay'), false)
})
```

- [ ] **Step 2: Chạy để chắc nó ĐỎ**

```bash
cd /d/LTTCODEAPP && node --test plugins/ui-lttcode/test/noi-lai.test.mjs
```

- [ ] **Step 3: Viết `coTheNoiLai` trong `client.js`**

```javascript
/**
 * Loi nao dang noi lai. Danh sach DONG, doi chieu voi registry cua may A
 * (llm_gateway/error_contract.py: cot `recovery` = `wait`).
 *
 * ⛔ KHONG noi lai `upstream_unknown`: khong biet chuyen gi da xay ra thi khong
 *    biet noi lai co an toan khong. Va KHONG noi lai loi cua chinh yeu cau -
 *    gui lai mot yeu cau sai van sai, chi ton them tien cua khach.
 */
const MA_NOI_LAI_DUOC = Object.freeze(new Set([
  'provider_overloaded', 'concurrency_limited', 'rate_limited', 'model_loading',
  'upstream_timeout', 'upstream_unreachable', 'internal_error',
  'stream_idle_timeout', 'empty_response',
]))

export function coTheNoiLai(maCanonical) {
  return MA_NOI_LAI_DUOC.has(String(maCanonical ?? ''))
}
```

- [ ] **Step 4: Chạy để chắc nó XANH**

🔴 **CHẶN (đo 23/09):** `ChatNodeOwnerProps` — props thật mà slot `conversation.chat.node`
nhận (`dsh-client-ui-chat/lib/types/client/contract/slots.d.ts:60-78`) — **không có** hàm
resend/retry/continue nào. Chỉ có `cwd, openSkill, openFile, inspectCall, forkAt, loadImage,
renderMessageImages, fileMentions, turnProcess`. `forkAt(seq)` tạo **nhánh mới**, khác nghĩa
"gửi lại đúng lượt hỏng". Muốn có nút này phải luồn prop qua nhiều tầng — là thiết kế mới,
không phải chỗ nối sẵn. **Đã dừng đúng chỗ, không đoán cấu trúc giao diện.**

- [ ] **Step 5 (CHẶN — cần thiết kế): Nối nút vào tin lỗi** — khi `coTheNoiLai(ma)`, tin lỗi hiện nút **"Chạy tiếp"**;
  bấm là gửi lại đúng lượt hỏng. Nếu lỗi kèm `retryAfter`, nút hiện đếm ngược thay vì bấm được ngay.

- [ ] **Step 6: Đo lại trên phiên thật**

Chạy một phiên ≥ 3 giờ có việc thật, đếm lại tỉ lệ `turn/end kind=error`. **Đạt khi: khách không
phải gõ lại lần nào** cho nhóm lỗi tạm thời.

- [ ] **Step 7: Commit**

---

## Task 12 ⏳ MÃ XONG (`3326d7f`), CHỜ ĐO: Nén ngữ cảnh bằng model nhỏ (C2: 45 → 80)

**Số đo hiện tại:** **188,6 s** và **243,7 s** cho hai lần nén trong cùng một phiên — hơn **7 phút**
khách ngồi nhìn màn hình không có gì xảy ra. Đây là thứ không hiện trong bất kỳ bảng tính năng nào
nhưng quyết định người ta có dùng tiếp hay không.

**Ý tưởng:** tóm tắt lịch sử **không cần** model 27B. `ltt-3.5` (9B) đo được **0,96 s TTFT** so với
1,35 s của 3.8, và chạy trên **card khác** (5060 Ti) nên không tranh suất với lượt chính.

**Files:**
- Modify: `D:\LTTCODEAPP\desktop\sidecar\presets\standard\agent.cordis.yml` (khối compaction)

**Interfaces:**
- Consumes: khối `compaction-basic` đã có `maxOverflowRetries: 2` và `thresholdRatio: 0.79`.
- Produces: compaction chạy trên `provider: ltt-official, model: ltt-3.5`; lượt chính không đổi.

- [ ] **Step 1: Đo mốc trước** — lấy hai số 188,6 s / 243,7 s từ phiên D1 làm mốc, ghi vào báo cáo.

- [ ] **Step 2: Đọc khối compaction để biết nó có nhận `agentOptions` không**

```bash
cd /d/LTTCODEAPP && grep -n "compaction" -A 15 desktop/sidecar/presets/standard/agent.cordis.yml | head -40
```

Nếu upstream **không** cho chọn model cho compaction ⇒ dừng, ghi thành mục nghiên cứu N-NN và
soạn issue upstream, **không vá `node_modules`** (luật "dùng lại trước, tự viết sau").

- [ ] **Step 3: Đặt model nén = `ltt-3.5`**, giữ nguyên ngưỡng 0,79.

- [ ] **Step 4: Kiểm chất lượng tóm tắt, không chỉ kiểm tốc độ**

⚠️ Đây là chỗ dễ sai nhất: nén nhanh mà mất thông tin thì phiên sau lạc đề, và **lỗi đó không
hiện ra ngay**. Phép kiểm: chạy một phiên dài tới khi nén, rồi hỏi agent ba câu về việc đã làm ở
phần bị nén; ba câu phải trả lời đúng.

- [ ] **Step 5: Đo lại** — giây mỗi lần nén. **Đạt khi ≤ 90 s** và ba câu kiểm trên đều đúng.

- [ ] **Step 6: Commit**

---

## Task 13: MCP phải thật sự dùng được (G1+G2: 45 → 85)

**Số đo hiện tại:** LTTCODE có 4 MCP mặc định (memory, context7, chrome-devtools, playwright)
nhưng **0/166 lần gọi công cụ** trong phiên D1 là MCP. Phiên Claude Code cùng ngày gọi playwright
thật để kiểm trang phát hành. Một tính năng không ai gọi thì bằng không.

**Files:**
- Create: `D:\LTTCODEAPP\tests\live\mcp\kiem_tung_mcp.mjs`
- Modify: `D:\LTTCODEAPP\plugins\profile-lttcode\cordis.patch.yml` (nếu phát hiện cấu hình chặn)

**Interfaces:**
- Produces: `kiemMcp(ten) -> { ten, noiDuoc: boolean, soCongCu: number, loi?: string }` cho từng
  MCP; và một báo cáo JSON gom bốn kết quả.

- [ ] **Step 1: Đo hiện trạng bằng một phép kiểm thật, không đọc cấu hình**

Với mỗi MCP: khởi động, liệt kê công cụ, gọi **một** công cụ vô hại, ghi kết quả.
- `memory` → ghi rồi đọc lại một khoá
- `context7` → tra một thư viện
- `playwright` → mở `about:blank`, đọc tiêu đề
- `chrome-devtools` → liệt kê công cụ (không mở trang)

- [ ] **Step 2: Phân loại từng cái** — chạy được / hỏng / không ai gọi vì model không biết nó có.
  Cái thứ ba là lỗi **mô tả công cụ**, không phải lỗi MCP.

- [ ] **Step 3: Sửa đúng nhóm vừa phân loại.** Với nhóm "model không biết": viết lại mô tả để nói
  rõ **khi nào nên dùng**, không chỉ nói nó là gì.

- [ ] **Step 4: Đo lại trên phiên thật** — chạy một việc **bắt buộc phải dùng MCP** (ví dụ: kiểm
  một trang web thật). **Đạt khi: MCP được gọi ≥ 1 lần mà không phải nhắc trong prompt.**

- [ ] **Step 5: Commit**

---

## Task 14: Gỡ trần 50 của kế hoạch và mục tiêu (E2+E3: 50 → 85)

**Vì sao đang 50:** `exit_plan_mode`, `get_goal`, `create_goal`, `update_goal` **có trong 43 công
cụ** nhưng **không dùng lần nào** trong 155 bước. Theo thang chấm, không bằng chứng ⇒ trần 50.
Đây là **điểm rẻ nhất cả bảng**: tính năng đã có, chỉ thiếu phép đo và một cú hích.

**Files:**
- Create: `D:\LTTCODEAPP\tests\live\ke-hoach\kiem_plan_mode.mjs`

- [ ] **Step 1: Chạy một việc thật đủ lớn để phải lập kế hoạch**, quan sát agent có vào chế độ
  kế hoạch không. Ghi lại: có / không.
- [ ] **Step 2:** Nếu không — tra vì sao: prompt hệ thống không nhắc, hay mô tả công cụ mờ, hay
  điều kiện kích hoạt quá hẹp.
- [ ] **Step 3:** Sửa đúng nguyên nhân tìm được.
- [ ] **Step 4:** Chạy lại, thu bằng chứng: bản ghi có `exit_plan_mode`, và kế hoạch hiện trên giao diện.
- [ ] **Step 5: Commit**

---

## Task 15: Agent do người dùng tự định nghĩa (D3: 40 → 85)

**Vì sao:** Claude Code cho định nghĩa agent bằng tệp (vai trò, model, bộ công cụ riêng). LTTCODE
chỉ có bốn agent con **cố định trong preset**. Chênh **−52**, một trong ba chênh lớn nhất.

**Nghiên cứu trước, viết mã sau** — gói `dsh-agent-plugins-market` đã có mục **"Agent personas"**
(`runtime/agent-role-names.js`, `agent-role-router.js`, `subagent-catalog.js`). Rất có thể năng lực
này **đã có sẵn** và chỉ cần mở đường cho người dùng, giống chuyện `/health/ready` ở Task 6.

- [x] **Step 1 ✅ XONG (làn `b-agent`, 23/09) — năng lực CÓ SẴN, đã chạy thật:**

  | Câu | Trả lời | Bằng chứng |
  |---|---|---|
  | Đọc ở đâu | `$DSH_AGENTS_HOME`, mặc định `homedir()/.agents`, rồi nối thêm `/agents` | `lib/catalog/paths.js:51-54` (`resolveAgentsRoot`) + `lib/runtime/user-store.js:19-21` |
  | Đường thật trên máy này | `C:\Users\<user>\.agents\agents\*.md` — **hai tầng `agents`**, không phải `~/.agents/*.md` như plan viết | như trên |
  | Gắn model riêng | **ĐƯỢC** — nhưng phải khai **CẢ `provider` LẪN `model`**; thiếu một khoá thì route bị bỏ qua | `lib/runtime/agent-role-router.js:28-60` (`parseAgentRole`), `resolveAgentOptions` ~78-106 |
  | Khoá được nhận | `name`, `description`, `disabled`, `provider`, `model`, `reasoning_effort` | như trên |
  | Giới hạn bộ công cụ | **KHÔNG** — xem mục 🔴 dưới | `parseAgentRole` không đọc khoá `tools` |
  | Người dùng thấy được không | **CÓ**, hai đường: catalog tự chèn `<available_subagents>` khi có tool `subagent_run` (`lib/runtime/subagent-catalog.js`); và API CRUD HTTP cho panel `agents` (`lib/routes.js:337-370`) |

  **Bằng chứng chạy** (gọi thẳng `node` vào `agent-role-router.js`, không mở app): frontmatter mẫu
  → `agentRoleCatalog` sinh `{name, provider:"ltt-official", model:"ltt-3.5"}` không suy biến →
  `resolveAgentOptions` trả đúng cặp đó, diagnostics rỗng.
  Tệp mẫu đang sống: `C:\Users\Thang Tuong\.agents\agents\ra-bao-mat-thu.md` (thư mục trước đó
  **rỗng** — không đụng tệp nào của người dùng). **Giữ lại** làm ví dụ chạy được cho tài liệu.

  🔴 **Lỗi V-25 — khoá `tools:` bị bỏ qua ÂM THẦM.** Làn đã chạy đối chứng: frontmatter có
  `tools: [Read, Grep]` ⇒ `'tools' in policy` → **`false`**, **không lỗi, không cảnh báo**.
  Đây là dạng nguy hiểm nhất: người dùng tưởng đã khoá agent con thành chỉ-đọc, thực tế nó
  **có toàn bộ công cụ của host**. Tệ hơn, `lib/runtime/user-panels.js:12-14` mô tả khuôn lưu
  trữ là "Claude Code agents frontmatter" — tức **mời người ta viết `tools:`** rồi lặng lẽ vứt đi.
  ⇒ Ít nhất phải **cảnh báo** khi thấy khoá không được hỗ trợ. Đã lập thành mục lỗi riêng.

  **Muốn khoá công cụ thật** thì có đường khác, nhưng **không phải đường của người dùng**: khai
  một tool subagent trong `presets/standard/agent.cordis.yml:374-420` qua
  `@deepseek-ai/dsh-tool-subagent` với `toolFilter.allow` — ví dụ `tool-subagent-doc-nhanh` đang
  chạy `ltt-3.5` với `allow:[read, glob, grep, skill]`. Đó là YAML của dev, không phải tệp `.md`.

- [ ] **Step 2 — chỉ còn tài liệu + cảnh báo, KHÔNG viết hệ agent thứ hai.**
  - [ ] Viết mục "Tự định nghĩa subagent" vào tài liệu LTTCODE: đường đặt tệp **hai tầng**,
        khuôn frontmatter, ví dụ `ra-bao-mat-thu.md`, và **giới hạn thật** (`tools:` không ăn).
  - [ ] Vá V-25: `parseAgentRole` gặp khoá lạ ⇒ đẩy một dòng cảnh báo, đừng im.
- [ ] **Step 3 — bằng chứng cuối:** giao một việc thật cho `ra-bao-mat-thu`, xác nhận bản ghi
  cho thấy nó chạy **đúng vai và đúng `ltt-3.5`** (bước này cần mở app ⇒ gộp vào lượt mở app chung).
- [ ] **Step 4: Commit**

> **Việc ghi vào `D:\LTTCODEAPP` đang xếp sau làn `credit-uoc` (R1).**

---

## Task 16: Tiền hiện ngay chỗ khách nhìn (J1+J2: 25 → 85)

Task 4 + 5 (Phần A) mới làm cửa sổ Tài khoản. Task này đi xa hơn: **credit mỗi lượt, cạnh token**.

**Vì sao:** thanh chân phiên đã hiện `288K tok · trúng cache 84 % · 47 % ngữ cảnh` — token thì
thấy, **tiền thì không**, dù tiền mới là thứ khách trả. Và đo được: mỗi lượt giữ 17–18 credit rồi
hoàn 16–17, tiêu thật 1–2.

**Files:**
- Modify: `D:\LTTCODEAPP\plugins\ui-lttcode\src\client.js` (thanh chân phiên)

### 🔴 CHẶN Ở TẦNG ENGINE — đóng task ở plan này, chuyển thành mục thiết kế riêng

Đã tra **ba vòng**, mỗi vòng bác một phương án. Không vòng nào là đoán — đều có tệp:dòng.

**Vòng 1 — không có nguồn chính xác.** `/api/v1/messages` (cửa LTTCODE dùng) chỉ mang `WireUsage`:
token vào/ra/cache, **không có trường credit**. Quyết toán credit chạy trong `finally` **SAU khi
byte cuối đã gửi** ⇒ không nhét được vào SSE đang chạy. `/api/v1/usage` join theo `Job.id`, còn
lượt chat mang mã `stream:<hex>` ⇒ **không liệt kê lượt chat**.

**Vòng 2 — phương án (b) "hiệu số số dư, gọi từ giao diện": BẤT KHẢ.**
`client.js` chạy trong **DSH web UI, là một loopback remote page** ⇒ **không có Tauri IPC**, nên
không gọi được `credits_balance` (đường gọi số dư duy nhất, do Task 5 dựng).
> `desktop/src-tauri/src/lib.rs`, docstring `open_account_window`: *"…the DSH web UI, **which as a
> loopback remote page gets no Tauri IPC**"* · `desktop/src-tauri/capabilities/default.json`:
> *"**The DSH web UI is a loopback remote page and gets no capability.**"*

Cửa sổ Tài khoản (`account.html`, `WebviewUrl::App`) là **cửa sổ khác hẳn** — nó có IPC, nhưng
không phải nơi cần hiện credit.

**Vòng 3 — gọi từ phía sidecar (đúng lớp): vẫn chặn, ở BA lớp liên tiếp.**

| Lớp | Tình trạng | Bằng chứng |
|---|---|---|
| Gọi mạng | ✅ **dùng lại được** — `plugins/llm-ltt/src/adapter.ts` `stream()` đã có `resolveApiKey()` + `doFetch` + `attributionHeaders()` gọi `baseUrl` bằng Bearer `ltt_sk_` | — |
| Chở số đi tiếp | ❌ `TokenUsage` là **interface đóng**, chỉ có `inputTokens, outputTokens, totalTokens?, cacheRead/Write?, reasoningTokens?` — **không có trường tự do** | `plugins/llm-ltt/src/translate.ts:47-59` (`mergeUsage`) · `dsh-llm/lib/types/types.d.ts:149-163` |
| Nuôi thanh chân phiên | ❌ projection **khoá cứng đồng bộ**: *"All functions MUST be synchronous… an async unit would tear the carriers' consistency cut"* ⇒ **không `fetch` được trong projection**, và nó chỉ fold lại sự kiện **đã có** trong log, không tự đi lấy | `dsh-token-meter/lib/types/usage-projection.d.ts` · `dsh-session-projection/lib/types/index.d.ts:34-36` |

**Vì sao đây là "không có kênh" chứ không phải "kênh khó dùng":** muốn số credit tới được thanh
chân phiên thì phải có **cả ba**: (a) một actor mới ngoài projection, gọi `credits/balance` bất
đồng bộ quanh ranh giới lượt; (b) **một loại sự kiện MỚI** ghi vào log phiên; (c) một unit
projection MỚI fold trên sự kiện đó. Cả ba đều là **hạ tầng engine mới**.

**Quyết định:** ⛔ **không dựng hạ tầng engine mới trong plan này.** Chuyển sang
`HANG_MUC_BAN_SAU.md`. Hai đường đi tiếp, chủ dự án chọn sau:
1. Bàn với người giữ `dsh-token-meter` / `dsh-session-projection` để mở một kênh sự kiện phụ;
2. Chấp nhận **credit không đồng bộ theo đúng lượt** — hiện số dư ví cập nhật rời rạc (đã có ở
   cửa sổ Tài khoản, Task 5), không gắn vào từng lượt.

> **Điều đã giữ được:** không có chỗ nào trong app hiện một con số tiền **sai**. Ba vòng tra đều
> dừng trước khi viết mã. Thà không nói còn hơn nói sai về tiền — đó là ràng buộc đặt ra từ đầu
> và nó đã làm đúng việc của nó.

---

## Task 17: Giảm độ trễ mỗi bước (A5: 60 → 75)

**Số đo hiện tại:** p50 **26,8 s** · p90 **72,7 s** · max 273 s cho một bước. Claude Code cùng
máy: khoảng bản ghi p50 1,5 s.

⚠️ **Đây là hạng mục dễ hứa hão nhất.** Phần lớn độ trễ đến từ model 27B chạy trên một card, không
từ phần mềm. Vì vậy task này **chỉ nhắm phần phần mềm thật sự kiểm soát được**, và nhắm khiêm tốn
(60 → 75), không nhắm bằng Claude Code.

- [ ] **Step 1: Tách độ trễ thành ba phần** trên một phiên thật: chờ suất · sinh token · chạy công
  cụ. Chưa biết ba phần này bao nhiêu thì **mọi tối ưu đều là đoán**.
- [ ] **Step 2:** Chỉ tối ưu phần lớn nhất mà phần mềm kiểm soát được. Nếu phần lớn nhất là sinh
  token ⇒ kết luận thẳng: **đây là giới hạn phần cứng**, ghi vào báo cáo và **đóng task**, không
  vờ tối ưu.
- [ ] **Step 3:** Đo lại p50/p90 bằng đúng bộ đo cũ.
- [ ] **Step 4: Commit**

---

## Task 18: Việc chạy tới cùng khi app đã đóng (H18: 45 → 80)

**Vì sao:** chênh **−42,7**, lớn nhất trong cả hai bảng. LTTCODE có `schedule_create/list/delete`
nhưng **lịch hẹn mất khi đóng app**. Nghĩa là mọi kịch bản "giao việc rồi đi ngủ" đều không dùng được.

**Đây là task lớn nhất Phần B** — nên tách thành plan riêng sau khi có thiết kế. Ở plan này chỉ
làm bước nghiên cứu để biết nó lớn cỡ nào.

- [ ] **Step 1:** Trả lời ba câu bằng mã, không bằng phỏng đoán: sidecar sống được khi cửa sổ đóng
  không · lịch hẹn lưu ở đâu · DSH có chế độ headless không.
- [ ] **Step 2:** Viết một mục thiết kế ngắn vào `HANG_MUC_BAN_SAU.md`, kèm ước lượng khối lượng.
- [ ] **Step 3:** Chủ dự án quyết có mở plan riêng không.

---

## Task 19: Git và PR thành công cụ gốc (G4: 45 → 80)

**Vì sao:** chênh **−45**. Hiện LTTCODE chỉ có `pwsh` + skill; mọi thao tác git là gõ lệnh, không
có bước xem lại thay đổi trước khi commit.

- [x] **Step 1 ✅ XONG (làn `b-git`, 23/09):** đã chấm `lxj808624/dsh-tool-git` theo `TIEU_CHI.md`.

  **≈ 51/100.** MIT · TypeScript · v0.1.3 · `execFile` không qua shell · cài bằng
  `dsh plugin add` — **kiến trúc khớp** (4,5/5): đây là plugin Cordis, mà LTTCODE **chạy trên
  DSH/Cordis**, nên nó cắm thẳng vào được.

  > ⚠️ Làn chấm mục 5 **1/5 vì "không cắm được vào runtime Claude Code"** — **chấm sai**. Tiêu chí
  > đó hỏi *giá trị cho nền tảng của ta*, mà nền tảng của ta là DSH. Trừ điểm này đi thì điểm
  > thật cao hơn 51. Ghi lại để lần sau đọc `TIEU_CHI.md` đúng chủ ngữ.

  **Ba thứ làm nó KHÔNG dùng nguyên trạng được** (bằng chứng tệp:dòng do làn đọc mã):

  | # | Vấn đề | Bằng chứng |
  |---|---|---|
  | a | **`git add -A` là tính năng chính thức, không bị chặn** | `src/tools/stage.ts`: `all: true` → `ctx.run(['add','-A'])`. Hàng rào `findDestructiveGit` (`src/safety.ts`) **chỉ kiểm `git_commit --amend`**, không hề kiểm `git_stage` |
  | b | **Không quét bí mật, một dòng nào cũng không** | `search_code` "secret" → 0 kết quả; đọc `stage.ts`/`commit.ts`/`safety.ts` không có logic nào cho `.env`, `*.pem`, `secrets/**` |
  | c | **`git_stash push --includeUntracked` KHÔNG nằm trong hàng rào** | `PATTERNS` chặn `reset --hard`, `clean -f`, `checkout -- .`, `push --force`… nhưng bỏ sót `stash`. Đây đúng là **luật chết người số 4** của kho này: dòng `??` là của phiên khác — một lượt `stash -u` sẽ **cuốn mất việc của phiên đang chạy** |

  Thêm: upstream im > 5 tuần, issue #4 đã xác nhận lỗi mà chưa vá (trưởng thành 2/5).

- [ ] **Step 2 — QUYẾT ĐỊNH: bundle NHƯNG CHỈ LẤY PHẦN ĐỌC.**

  **Vì sao không bọc cả gói, cũng không tự viết từ đầu:** chênh −45 sinh ra từ *"không có bước
  xem lại thay đổi trước khi commit"* — tức là thiếu **`git_status` / `git_diff` / `git_log` /
  `git_show` có cấu trúc**. Bốn công cụ đó là **chỉ đọc, không rủi ro**, và gói này đã có sẵn,
  làm tốt, trả JSON. Lấy chúng là **đóng đúng cái chênh** mà không nhận một rủi ro nào.

  Ba thứ ở bảng trên **đều nằm ở nhóm công cụ GHI** (`git_stage`, `git_commit`, `git_stash`).
  Nhóm đó ta **không cần**: ghi git vẫn đi qua `pwsh`, nơi luật của kho đã áp sẵn. Bỏ chúng thì
  ba vấn đề a/b/c biến mất mà **không phải fork, không phải vá mã người khác, không phải nuôi
  một bản rẽ nhánh**.

  - [ ] Xác minh **tắt được từng công cụ** trong lớp vá Cordis (`plugins/profile-lttcode/cordis.patch.yml`).
        ⚠️ **Chưa xác minh — đừng coi là đã biết.** Nếu Cordis **không** cho tắt lẻ từng công cụ
        ⇒ quay lại tự viết ba công cụ mỏng, đừng nhận cả nhóm ghi.
  - [ ] Ghim đúng `#v0.1.3`, không để trôi theo `main` của upstream đang im.

- [ ] **Step 3 — đối chứng âm, chạy THẬT sau khi bundle:** gọi `git_stage`, `git_commit`,
  `git_stash` từ trong phiên ⇒ cả ba **phải không tồn tại**. Nếu còn gọi được thì việc tắt
  không ăn, và task này **chưa xong** — dù `git_status` đã chạy đẹp.
- [ ] **Step 4 — bằng chứng:** trong một phiên thật, model tự gọi `git_diff` để xem lại trước
  khi đề nghị commit (chứ không phải ta nhắc nó trong prompt).
- [ ] **Step 5: Commit**

> **Việc ghi vào `D:\LTTCODEAPP` đang xếp sau làn `credit-uoc` (R1: một kho một làn ghi).**

---

## Task 20: Khởi động app (L2: 45 → 80)

**Số đo hiện tại, đo 3 lần trong ngày 23/09:** **17 s** (máy ấm) · **49 s** (lạnh) ·
**107,7 s** (sau khi khởi động lại máy). Xu hướng xấu dần và chưa ai truy.

- [ ] **Step 1:** Đo lại 3 lần lạnh, lấy mốc ổn định.
- [ ] **Step 2:** Tách thời gian khởi động thành: khởi tạo vỏ Tauri · dựng `DSH_HOME` · nạp
  composition · mở WebView2. Bản ghi `==== sidecar ready in <N> ms` đã có sẵn số cho một chặng.
- [ ] **Step 3:** Chỉ tối ưu chặng lớn nhất.
- [ ] **Step 4:** Đo lại 3 lần lạnh. **Đạt khi p50 ≤ 30 s.**
- [ ] **Step 5: Commit**

---

## Thứ tự Phần B

| Đợt | Task | Lý do |
|---|---|---|
| B1 | **14, 13** | Rẻ nhất: tính năng đã có, chỉ thiếu bằng chứng và một cú hích. Gỡ được hai trần 50 |
| B2 | **11, 12** | Hai thứ khách cảm thấy ngay: không mất lượt, không chờ 4 phút để nén |
| B3 | **16** | Tiền hiện ra — nối tiếp Task 4+5 |
| B4 | **15, 19** | Cần tra upstream trước; rất có thể phần lớn đã có sẵn |
| B5 | **17, 20** | Đo trước, và **được phép kết luận "giới hạn phần cứng" rồi đóng task** |
| B6 | **18** | Lớn nhất, tách plan riêng sau khi nghiên cứu |

## Nếu làm hết Phần B

Cộng theo bảng nhắm: **69,7 → khoảng 78**. Chưa bằng Claude Code (85,0), và điều đó **đúng với
thực tế** — hai chênh còn lại lớn nhất là nền tảng chạy trên (chỉ desktop Windows) và tự động hoá,
cả hai đều là dự án riêng chứ không phải một task.

⚠️ **Một điều phải nói thẳng:** đích "mạnh bằng hoặc hơn Claude Code" **không đạt được bằng cách
đuổi theo từng hạng mục**. Claude Code chạy model trên hạ tầng đám mây; LTTCODE chạy hai model nhà
trên một máy hai card dùng chung. Chỗ LTTCODE có thể **vượt** không nằm ở danh sách tính năng mà ở
bốn thứ nó đang vượt thật: tiếng Việt đầu-cuối (+55), bản ghi lỗi theo hợp đồng (+22), sandbox trên
Windows gốc (+18), và hiện tốc độ/token ngay cho người dùng (+15). Nâng bốn thứ đó lên **95+** là
con đường khác biệt hoá; đuổi theo H18 và H14 là con đường tốn nhất và về sau cùng.
