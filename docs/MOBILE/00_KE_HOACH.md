# KẾ HOẠCH TRIỂN KHAI — LTT MOBILE AUTONOMOUS PACK V1

Lập 2026-09-05. Nguồn: `G:\My Drive\AI\A LTT AII\LTT_MOBILE_AUTONOMOUS_PROMPT_PACK_V1`
(13 tệp, đọc hết). Tiến độ thực tế ở `CHECKPOINT.md` — **đọc tệp đó trước**, kế
hoạch này chỉ nói *dự định*, checkpoint nói *đã làm được gì và bằng chứng nào*.

---

## 0. PREFLIGHT — số đo, không phải giả định

| Đo | Kết quả | Ý nghĩa |
|---|---|---|
| branch / HEAD | `admin-mvp-v3` @ `72a484c5` | **Trùng khít** baseline pack. Mọi hypothesis trong pack còn hiệu lực nguyên vẹn, không cần hiệu chỉnh. |
| dirty | 36 tệp, toàn bộ là LTT VOICE | Không phải rác cũ — xem dòng dưới. |
| mtime mới nhất | `tools/doi_ten_giong_chung.py` 14:53, đo lúc 15:02 | **Một phiên khác ĐANG GHI vào chính cây này, ngay lúc này, vào đúng vùng P0 của pack.** |
| phiên đang chạy | 5 interactive (`ListAgents`) | Ngân sách 10 lõi chia 5 đường. |
| `cua_so_yen.py trang-thai` | RÀNH | Chưa ai giữ tài nguyên. |
| app dir | 19 | Inventory Phase A là việc một ngày, không phải một tuần. |
| React frontend | 4 (`agent-canvas`, `autosub-studio`, `chatltt`, `prompt-ai-ommi`) | Thứ tự build + cache-bust (CLAUDE.md luật 6) áp dụng cho cả 4. |
| `safe-area-inset` toàn `server/ apps/ frontend/` | **0 lần** | Pack đoán "chưa nhất quán". Thực tế là **chưa tồn tại**. Contract B2 là greenfield, khối lượng lớn hơn pack ước. |
| `100vh` | 10 tệp | Vừa tầm audit thủ công, không cần regex sweep. |
| `dvh` | 5 tệp | Khớp mô tả pack (Agent Canvas / OMMI đã có). |
| `.read()` toàn tệp ở route media | `apps/ltt_voice/routes/_p_audio.py:90` và `:169`; `apps/chatltt/routes/_p_media.py:113` và `:143` | **Hypothesis P0 của pack đã được XÁC NHẬN bằng grep, chưa tốn một lượt browser nào.** |
| `FileResponse` | chỉ `server/nexus_download.py`, `server/routes/tai_lieu_api.py` | Không route media app nào dùng. Range chỉ có ở `apps/taovideo/`. |
| playwright config | **không có** `playwright.config.*` ở đâu cả; chỉ `tests/test_74_smoke_playwright.py` | Harness Phase G gần như greenfield. |
| dải số test trống | **700–799** (600s đã tới 637 do ChatLTT; 397–399 vừa bị phiên Voice chiếm) | Dải cho mobile. |

**Hệ quả lớn nhất của preflight:** hai consumer cho shared media transport
(`ltt_voice` + `chatltt`) đã đủ điều kiện *ngay từ ngày đầu* theo DECISION RULE
của pack ("≥2 consumer thật"). Không cần chờ Phase A kết luận mới được xây
shared layer — phần B4 có thể khởi động song song với phần còn lại của Phase A.

---

## 1. BA ĐIỀU CHỈNH BẮT BUỘC SO VỚI PACK

Pack được viết mà không biết ba điều kiện dưới đây. Chạy nguyên văn `00_MASTER_ONE_SHOT.txt`
trong cây hiện tại sẽ hỏng ở cả ba chỗ.

### A. Cách ly worktree — KHÔNG chạy trong `D:\LTTSTUDIOSAPP`

Pack nói "Mở Claude Code tại repo LTTSTUDIOSAPP". Nhưng cây đó đang có
**36 tệp dirty và một phiên khác đang ghi vào `apps/ltt_voice/` cách đây 9 phút**.
`apps/ltt_voice` chính là P0 số một của pack (Phase C, prompt 03). Hai phiên sửa
cùng bộ tệp = một trong hai mất việc, âm thầm.

Quyết định:
- Tạo nhánh `phien/mobile-v1` từ `72a484c5`, worktree riêng.
- Đọc `docs/QUY_TRINH_WORKTREE.md` **trước** khi tạo (luật của kho, và memory
  ghi rằng `worktree remove` xoá âm thầm thứ bị gitignore).
- Kiểm ngay trong cây mới: `findstr /C:"loi_cho_bo_test" tools\gate.py`.
  Không thấy ⇒ bản gate cũ, tự chọn `-n 14` ⇒ chỉ chạy cụm test hẹp với `-n 6` gõ tay.

Giao ước với phiên Voice (memory *Hai phiên cùng cây — giao ước file*):
- Phase A: **chỉ đọc** `apps/ltt_voice/`, không sửa một byte.
- Phase C: trước khi sửa Voice, `SendMessage` hỏi phiên kia đã commit chưa; nếu
  chưa, làm ChatLTT (consumer thứ hai) trước, quay lại Voice sau.
- Không bao giờ `Write` đè tệp Voice — chỉ `Edit`.

### B. Ma trận tự động chạy trên **loopback `127.0.0.1:8100`**, không chạy trên public URL

Pack (Phase G) yêu cầu ma trận WebKit/Chromium tự động. CLAUDE.md luật 5b yêu cầu
chốt trên `https://app.lttstudios.com`. Hai thứ này **không chồng lên nhau được**:
Playwright tự mở Chrome thì bị Cloudflare chặn bằng CAPTCHA (đã đo, ghi trong memory
*Kiểm GUI: nối vào Chrome thật*).

Quyết định — tách làm hai lớp, không trộn:
- **Lớp regression tự động** (chạy hàng chục lần, mọi phase): loopback 8100.
  Đây là thứ sinh ra bằng chứng cho Gate của từng phase.
- **Lớp chốt public** (chạy đúng vài lần, ở mốc cuối): Chrome thật qua `--cdp`,
  cửa sổ người dùng đã đăng nhập, tài khoản test `akakenly.design@gmail.com`
  (memory *Tài khoản test vận hành* — **không** dùng admin).
- Lớp public chỉ chạy **sau** deploy, tức chỉ một lần ở Phase H. Xem mục 5.

### C. Chạy **Cách A** (master one-shot) nhưng đóng checkpoint sau mỗi phase

Pack khuyến nghị Cách A và có sẵn `09_RECOVERY_AFTER_COMPACTION.txt`. Nhưng
8 phase × 19 app × 4 frontend chắc chắn vượt một context window nhiều lần, và
prompt 09 chỉ rẻ nếu có checkpoint để bám vào.

Quyết định: chạy mạch Cách A, nhưng cuối **mỗi** phase bắt buộc:
1. commit trên `phien/mobile-v1` (kể cả khi phase chưa đẹp);
2. cập nhật `docs/MOBILE/CHECKPOINT.md` — phase nào PASS, **bằng chứng nào**,
   P0/P1 còn mở, lệnh test cuối cùng đã chạy + kết quả nguyên văn.

Checkpoint là tệp duy nhất prompt 09 cần đọc để nối lại. Không tạo "snapshot toàn
cây" (CLAUDE.md đã gỡ `ho_so_he_thong.txt` đúng vì lý do này).

---

## 2. LỘ TRÌNH — 8 PHASE

Ký hiệu gate: `VL` = vòng lặp nhanh · `FULL` = gate đầy đủ. Cấp nào dùng khi nào,
và giá **đo được** của từng cấp: `docs/00_LTT_OPERATING_CONTRACT.md` §4.
*(Chỗ này từng ghi "~15s" và "~5 phút" — cả hai đã trôi; đo thật là 21,4 s và
11,4 phút.)*

### Phase A — Preflight + inventory + baseline (prompt 01)
Việc thật ở kho này:
- Liệt kê app **từ `platform_core/registry.py` lúc runtime**, không từ `ls apps` (19 thư mục
  ≠ 19 surface khách hàng; có `qualitylab`, `ltt_llm`, `agent` có thể là capability-only).
- Với mỗi surface: manifest lifecycle/public/enabled, route, loại frontend, job chính,
  loại media, long-job/streaming/drag/canvas/timeline/composer/upload, CSS responsive
  đang có, rủi ro P0/P1/P2.
- Phân loại theo 9 behavior profile của pack, không theo tên.
- Baseline screenshot + console/network ở 390×844 · 430×932 · 768×1024 · landscape 844×390 · desktop.
- Xác minh 8 hypothesis của pack (4 cái đã confirm bằng grep ở mục 0 — ghi luôn, khỏi đo lại).

Deliverable: `docs/MOBILE/01_MATRIX.md`, `02_BASELINE.md`, `03_BACKLOG_P0P1P2.md`, `CHECKPOINT.md`.
Gate A: 100% customer route có row hoặc có lý do loại trừ; không còn câu "có lẽ app X…".

### Phase B — Thiết kế shared contract (prompt 02, phần thiết kế)
Chốt Shared vs App-owned cho 7 capability: viewport · safe-area · touch/input ·
media transport · media controller · long-job lifecycle · large upload.
Quy tắc: chỉ lên shared khi ≥2 consumer thật hoặc là contract browser/security
mà platform nên sở hữu. Không branching theo slug trong `platform_core/`.

Đã biết trước kết quả cho **B4 (media transport)**: 2 consumer sẵn (`ltt_voice`,
`chatltt`), consumer thứ 3 (`taovideo`) sẽ migrate sau khi có regression test.

Deliverable: `docs/MOBILE/04_SHARED_CONTRACT.md` (quyết định + lý do + tệp đích).
Gate B: mỗi capability có quyết định rõ; không capability nào lên shared với 1 consumer.

### Phase C — Shared layer + P0 Voice/Chat (prompt 02 phần code + prompt 03)
Thứ tự cứng:
1. `platform_core/media_transport.py` (tên tạm) — Range 200/206/416, `Accept-Ranges`,
   `Content-Range`, không đọc toàn tệp vào RAM. **In `starlette.__version__` lúc runtime**
   và xác minh version này có Range trước khi dựa vào `FileResponse` (pack yêu cầu, đúng).
   Ownership vẫn nằm ở app, transport nằm ở shared.
2. Test dải `test_7xx`: no-range · start-end · open-ended · suffix · invalid → 416 ·
   ownership · foreign key · file rỗng/nhỏ · R2 redirect mock. → `VL`.
3. Migrate consumer #1 và #2. **Nếu phiên Voice chưa commit → làm ChatLTT trước.**
4. Voice: root-cause bug "tải được nhưng mobile Play không được" — đo request sequence
   khi bấm Play trên WebKit, ghi Range header/status/headers. Sửa. Chứng minh bằng test tự động.
5. Waveform: profile memory/time short vs long audio. Nếu decode toàn tệp có rủi ro →
   peaks tiền tính hoặc lazy decode dưới ngưỡng **đo được**. Không đổi bytes audio,
   sample rate, billing, quality gate.
6. ChatLTT composer + OSK + streaming + scroll anchoring + lifecycle.

Gate C: Voice play/seek short+long xanh trên WebKit **và** Chromium · Range test tự động ·
composer không bị che · không còn full-file RAM ở route đã migrate · desktop Voice/Chat không regression · `VL` xanh.

### Phase D — Media generators (prompt 04)
Ứng viên từ registry: `taovideo`, `taoanh`, `thumbnail`, `taoclipngan`, `upscalevideo`, `anhnoibo`.
Mỗi app: happy path + validation/error path trên mobile; `playsinline`; Range/seek;
quote/credit trước submit; reload không mất job; card/grid không overflow; download/share fallback.
TaoVideo: migrate Range route riêng sang shared **có regression test**, giữ nguyên
đường R2 direct và đường local.
Cấm: thêm logic tính giá ở frontend; tin duration/filesize do client khai; đổi model/preset để "nhanh mobile".

Gate D: 100% app media có PASS/EXCEPTION · reload không mất job · `VL` xanh.

### Phase E — Complex editors (prompt 05)
- `autosubvideo` (TIMELINE): WCAG 2.5.7 — mọi drag chính phải có đường tap/field.
  Ứng viên: cue inspector/bottom sheet, ô số start/end, nút ±0.1s/±0.5s, prev/next.
- `agent` canvas (React Flow): **đọc version React Flow đã cài trước**, đừng giả định
  có `connectOnClick`. Tăng hit area handle nếu cần. Không hover/right-click-only.
- `prompt_ai_ommi` (STORYBOARD): reorder scene có tap alternative; detail full-width giữ close/back/focus.

Gate E: core workflow của editor làm được **chỉ bằng touch** · drag alternative có test ·
landscape + tablet · desktop editor không regression · `VL` xanh.

### Phase F — Standard/control surfaces (prompt 06)
Header/burger/nav/app tabs · home/catalog · login/register/account · jobs/history ·
pricing/top-up · API docs/developer console · STANDARD_FORM apps · `vps` · `nexus`.
Edge test **320–390px** (bắt overflow mà 390px bỏ lọt). Bảng → card/scroll theo nghĩa,
không `display:none` dữ liệu quan trọng. Copy IP/token touch-friendly và không leak.
Nhãn VI/EN dài không phá layout. Zoom 200%.
Admin/internal: chỉ sanity, không phải release surface.

Gate F: mọi row inventory = PASS/EXCEPTION/BLOCKED · 0 nav 404 · 0 overflow ngoài vùng chủ ý · `VL` xanh.

### Phase G — Harness QA + device matrix (prompt 07)
Một harness **registry-driven**, không 19 script rời. Kho chưa có `playwright.config.*`
nên đây là greenfield — thiết kế cho đúng ngay lần đầu:
- Browser: Chromium + WebKit (bắt buộc), Firefox smoke.
- Viewport: 390×844 · 430×932 · 768×1024 · landscape · desktop · 320 smoke.
- Mode: VI/EN · reduced-motion · coarse pointer.
- Assertion chung: không overflow ngang ngoài ý muốn · CTA chính reachable · sticky
  không che content · focus visible · touch target · không console error · route 2xx/redirect đúng.
- Media: 200/206/416 · seek · play rejection · `playsinline`.
- Long job: submit → hide/reload → quay lại → reconcile.
- Chạy trên **loopback** (mục 1.B).
- **Performance: đo baseline TRƯỚC, đặt ngưỡng SAU.** Không bịa threshold cứng
  (memory *Phép đo lệch chiều phải bỏ*).

Deliverable: harness + `docs/MOBILE/REAL_DEVICE_CHECKLIST.md`.
Gate G: ma trận xanh cho core flow · bằng chứng lưu đúng convention · real-device PASS hoặc PENDING minh thị.

### Phase H — Final Release Gate (prompt 08)
1. `git diff --stat` + đọc diff theo module. Truy: helper mobile/media trùng lặp ·
   slug branching lọt vào platform · `user-scalable=no` · `maximum-scale=1` ·
   silent catch · `.read()` toàn tệp ở route media mới · input <16px · sticky thiếu
   safe-area · `100vh` sót (phân biệt cố ý vs bug) · video thiếu `playsinline` ·
   drag-only · giá/model/credit bị chép vào frontend.
2. Build 4 frontend đúng thứ tự AGENTS.md.
3. **`python tools\gate.py` — bắt buộc, cuối cùng.**
   ⛔ **Đừng chạy `test_nhanh.py` trước nó.** Bước `bo test` **bên trong** gate
   *chính là* `test_nhanh.py` (`tools/gate.py:844`), nên chạy cả hai là trả ~4
   phút hai lần cho cùng một tập pass/fail. *(Hai dòng riêng ở đây trước
   2026-09-08 chính là chỗ dạy ra lỗi đó.)*
4. Chạy lại ma trận browser **sau** build cuối (bundle đã đổi thì bằng chứng trước build vô giá trị).
5. Kiểm cache-bust static (CLAUDE.md luật 6 — `?v={{ asset_ver }}`).
6. Cập nhật `docs/NHAT_KY.md` + `docs/_luutru/PROJECT_MEMORY.md` đúng convention.
7. Ghi rollback.

Verdict chỉ được là `MOBILE RELEASE PASS` khi hội đủ điều kiện mục 11 của master prompt.
Không có thiết bị thật ⇒ **`AUTOMATED MOBILE GATE PASS / REAL-DEVICE GATE PENDING`**,
tuyệt đối không gọi là full PASS.

---

## 3. KỶ LUẬT LỆNH NẶNG (5 phiên đang chạy — 10 lõi vật lý)

Trước **mọi** lệnh nặng (lệnh nào là nặng: `docs/QUY_TAC_CHAY_LENH_NANG.md` §1 —
⛔ đừng kê lại danh sách ở đây):

```
python tools\cua_so_yen.py trang-thai
```

Có phiên khác giữ ⇒ **chờ**. Trần cứng `-n 6`. Test nạp model thật phải nằm sau
`LTT_TEST_NANG`.

⛔ **Gate là công cụ ra phán quyết, không phải công cụ chẩn đoán.** Dò lỗi bằng
cụm test hẹp hoặc bằng `read_bytes()`, không bằng cách chạy gate bốn lần.
Ngày 03/09 máy treo đúng vì việc đó.

---

## 4. HARD BLOCKER DỰ KIẾN — nêu trước, không chờ

Ba cái, nêu ngay để anh biết trước chứ không phải để dừng việc:

1. **Thiết bị vật lý.** iPhone Safari + Android Chrome cần cho OSK, file picker,
   safe-area/PWA và media policy — Playwright không thay thế được.
   → Nếu không có: hoàn tất toàn bộ automation, sinh `REAL_DEVICE_CHECKLIST.md`,
   verdict = `REAL-DEVICE GATE PENDING`. **Không dừng, không hỏi giữa chừng.**

2. **Deploy để chốt public URL.** CLAUDE.md luật 5b buộc chốt trên
   `https://app.lttstudios.com`, mà tới đó phải deploy. Memory *Deploy thoải mái
   khi chưa có khách* cho phép không hỏi từng lần, nhưng deploy chép **cả cây** —
   nên sẽ mang theo việc dở của phiên khác nếu deploy từ cây chính.
   → Quyết định: deploy **một lần duy nhất**, ở Phase H, **từ worktree
   `phien/mobile-v1` đã ff-merge**, sau khi hỏi các phiên đang chạy. Không deploy
   giữa các phase.

3. **Va chạm với phiên LTT VOICE đang chạy.** Đã có giao ước ở mục 1.A. Chỉ thành
   blocker thật nếu phiên kia đang viết lại chính `_p_audio.py` — lúc đó đổi thứ tự,
   làm ChatLTT trước. Không phải lý do để dừng.

Không phải blocker: test đỏ · CSS cũ khó · phải chọn giữa 2 thư viện · cần refactor ·
một lượt automation flaky · context dài.

---

## 5. ROLLBACK

- Toàn bộ việc nằm trên `phien/mobile-v1`, tách khỏi `admin-mvp-v3`. Bỏ nhánh = bỏ hết, không dư chấn.
- Commit theo phase ⇒ revert được từng phase một.
- Shared media transport là **thêm mới**, app cũ chỉ đổi khi migrate ⇒ revert một
  consumer không kéo theo consumer kia.
- Deploy có `app.previous\` để rollback (CLAUDE.md).
- Không đụng `data/`, `secrets/`, `cloudflare/`, không migrate dữ liệu thật.

---

## 6. BẮT ĐẦU NGAY — 6 bước đầu

1. Đọc `docs/QUY_TRINH_WORKTREE.md` + `AGENTS.md` mục 4b, 8.
2. Tạo `phien/mobile-v1` + worktree; kiểm `loi_cho_bo_test` trong `tools\gate.py` của cây mới.
3. `SendMessage` báo phiên Voice: mobile pack sẽ chạm `apps/ltt_voice` ở Phase C, hỏi lịch commit.
4. Enumerate surface từ `platform_core/registry.py` lúc runtime.
5. Dựng `docs/MOBILE/` + `CHECKPOINT.md`, chép 4 kết quả grep đã confirm ở mục 0 vào `02_BASELINE.md`.
6. Chạy Phase A đến Gate A, rồi tự sang Phase B — không chờ duyệt.
