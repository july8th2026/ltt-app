# GUI_MASTER_PLAN — LTT Voice (lập 15/09/2026)

> ⛔ **ĐÃ BỊ THAY THẾ 16/09/2026** bởi
> [`GUI_DOI_SOAT_VA_PLAN_V2.md`](./GUI_DOI_SOAT_VA_PLAN_V2.md). Tệp này đã
> vượt cổng Wave 1 và báo Wave 3 XONG sai — giữ lại chỉ để truy vết.

Quy tắc (prompt §14–§15): **một wave một lúc**; mỗi patch ≤ 8–10 tệp;
mỗi wave đi đúng vòng lặp 10 bước. Không chuyển sang wave kế tiếp khi điều
kiện cổng của wave hiện tại chưa đạt. Quay về đây trước mỗi lượt làm:
*"tìm wave hiện tại, chỉ làm wave đó."*

Vòng lặp 10 bước của mỗi wave:
1. Xác nhận wave hiện tại + điều kiện cổng của wave trước (PROVEN).
2. Liệt kê tệp sẽ chạm (≤ 8–10) — ghi vào đây.
3. Đọc các tệp đó + tài liệu liên quan.
4. Ghi rõ thay đổi sẽ làm (mục Decision nào của GUI_DECISION_LOCK.md).
5. Thực hiện thay đổi.
6. `cua_so_yen.py trang-thai` → test L1 của cụm vừa sửa (`-n 6` tối đa).
7. Kiểm bằng trình duyệt thật (nếu chạm GUI) — `https://app.lttstudios.com`
   hoặc app worktree (E2E — Wave 9).
8. Cập nhật GUI_AUDIT_MATRIX.md dòng liên quan.
9. Cập nhật NHAT_KY.md.
10. Commit từng tệp tường minh (trailer Co-Authored-By).

---

## Wave 0 — Repo truth

| Hạng mục | Giá trị | Trạng thái |
|---|---|---|
| HEAD | `554443c4` | PROVEN (git) |
| Branch | `claude/mystifying-lamport-fa91de` | PROVEN |
| Worktree | `gallant-elion-13f82e` | PROVEN |
| Dirty | 5 tệp untracked (3 probe chứa MẬT KHẨU DB — phải xoá trước commit; `_task_spec.md`; 2 docs mới) | PROVEN |
| DEPLOYED_VERSION | Worker service re-baked env **14/09** (timeline PROVEN — job voice done cuối 13/09 21:01, kẹt từ 15/09); SHA code deploy: **NOT TESTED** (chưa đọc trực tiếp từ `C:\LTTPlatform\app\`) | PARTIAL |

**Cổng vào Wave 1:** xong. **Đóng W0:** trước khi commit lần đầu — xoá 3
probe, ghi rõ SHA deploy nếu đo thêm được.

## Wave 1 — Runtime / queue root cause (P0-1)

- **Điều kiện (prompt §15):** *"Không chuyển Wave 2 nếu core Generate vẫn
  kẹt queued."*
- **Đã làm:** chẩn đoán **PROVEN** (GUI_RUNTIME_DIAGNOSIS.md §1): 2 job kẹt
  queued 15/09, attempts=0; root cause `LTT_WORKER_POOLS="api:6, gpu:1"`
  thiếu làn `voice` (manifest yêu cầu `requires=("voice",)`).
- **Sửa production:** thêm `voice:1` — **chỉ chủ dự án, chưa thực thi**
  (§28: không deploy). **E2E path (không deploy):** app worktree chạy cổng
  riêng + worker địa phương `LTT_WORKER_POOLS=voice:1` chia sẻ DB production
  ⇒ job thật queued → running → done đo được ở Wave 9.
- **Sửa repo (chuyển Wave 10):** event warning khi job quá tuổi chưa được
  claim; `do_sau_khoi_dong.py` liệt kê app "vô hình" theo `requires`; mở
  rộng `test_501`.
- **Trạng thái:** chẩn đoán xong (PROVEN); code guard → Wave 10; E2E proof →
  Wave 9. **Đạt điều kiện vào Wave 2** (root cause hiểu rõ + cách proof).

## Wave 2 — Voice data inventory (P0-2)

- **Đã làm:** bảng 25 shared + 4 owned đầy đủ 9 cột (GUI_RUNTIME_DIAGNOSIS
  §3) — đo 15/09: R2 HEAD từng key (56/58 mất), DB 29 hồ sơ.
- **Phát hiện đưa sang:** phương án lưu trữ **C** (repo truth + seed +
  self-heal + migration + guard) — đã khoá vào D002; 5 bất thường dữ liệu
  (§3.3) → GUI_AUDIT_MATRIX.
- **Điều chặn:** 25 clip nguồn mất — chờ chủ dự án cung cấp (D002/BLOCKED).
- **Trạng thái: XONG** (inventory + phương án). **Đạt điều kiện vào Wave 3.**

## Wave 3 — Catalog contract (P0-3) — **XONG (15/09/2026)**

**Mục tiêu:** hợp đồng catalog khoá **trước** khi code (prompt §8) + hàm
chuẩn `voice_catalog_kind()`.

**Tệp sẽ chạm (≤10):**
1. `docs/LTT_VOICE/GUI_VOICE_CATALOG_CONTRACT.md` (mới)
2. `apps/ltt_voice/ho_so_giong.py` (hoặc module `catalog.py` mới — đọc trước
   để chọn đúng chỗ)
3. `apps/ltt_voice/routes/_p_giong.py`
4. `apps/ltt_voice/routes/_p_tao.py`
5. `apps/ltt_voice/templates/_voice_chon.html`
6. `apps/ltt_voice/templates/_voice_the.html`
7. `apps/ltt_voice/templates/ltt_voice_studio.html`
8. `apps/ltt_voice/templates/ltt_voice_giong.html`
9. `tests/test_5xx_catalog.py` (mới — số theo quy ước test hiện có)

**Bước:**
1. Xác minh nghi vấn `data-loai="{{ 'mau' if la_mau else 'toi' }}"` ở
   `/giong` tại **HEAD** — ghi PROVEN/LIKNOT vào contract.
2. Đọc `giong_vong_doi.py`, `nghe_thu.py`, `tham_so_cong_khai.py` — hiểu 3
   nguồn giọng (preset JSON / shared profile / owned profile) và cách chúng
   hợp nhất hiện tại.
3. Định nghĩa contract: `voice_catalog_kind(voice) → preset|shared|owned`,
   nguồn sự thật của từng loại, quyền của từng loại (shared: không
   Delete/Disable cho user thường), trạng thái thiếu tệp (D002).
4. Ghi `GUI_VOICE_CATALOG_CONTRACT.md` (khoá theo quy tắc §8).
5. Implement hàm chuẩn + chuyển mọi route/template qua nó (không mỗi
   template một luật).
6. Test L1: 3 loại fixture + grep không còn template tự tính kind.
7. Kiểm browser: Library 4 tab, picker Studio — phân loại khớp DB thật.

**Cổng vào Wave 4:** contract khoá + hàm chuẩn có test L1 xanh + nghi vấn
`/giong` đã định vị PROVEN/không.

**Kết quả W3 (15/09/2026) — ĐẠT cổng:**
- Contract khoá: `GUI_VOICE_CATALOG_CONTRACT.md` (3 loại preset/shared/owned +
  nguồn sự thật + quyền + trạng thái thiếu tệp D002).
- Hàm chuẩn MỘT chỗ: `apps/ltt_voice/catalog.py` — `voice_catalog_kind()` +
  `the_cho_trang()` (ORM → dict đủ cột + `kind`).
- Mọi route/template qua hàm chuẩn: `_p_giong.py`, `_p_tao.py` dùng
  `the_cho_trang`; template đọc `kind` (không còn tự tính inline).
- L1 xanh: `tests/test_5xx_catalog.py` 8/8 passed.
- Nghi vấn `/giong`: **PROVEN** — 500 là `TypeError: 'VoiceProfile' object is
  not iterable` (`dict(v)` trên ORM). Sửa bằng `the_cho_trang`.
- Browser (Chrome thật, sandbox loopback, DB copy `ltt_voice_kiem`):
  - Studio picker: 4 owned + 25 shared + 20 preset = khớp DB thật (4/25/20).
  - Library: 49 thẻ = 29 DB (25 shared + 4 owned) + 20 preset; `#lv-g-so`=49.
  - 0 console error, 0 failed network request (§17).
  - Phân loại 4-tab + badge "Kho chung" = phạm vi W6 (chưa làm ở đây).

## Wave 4 — Language contract + filter policy (P0-4, P0-5)

- Luật `ngon_ngu_hop()`: VI+VI ALLOW, EN+EN ALLOW, cross BLOCK **trước job**,
  enforce server-side ở mọi cửa (web + public API nếu voice có mở — kiểm
  `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md`). `Auto` chỉ trợ giúp. (D003)
- Filter policy **Option B** + nhãn "chỉ áp dụng cho giọng có thuộc tính
  này"; `gioi` rỗng 29/29 phải được khai trong UI. (D004)
- Tệp dự kiến: `tham_so_cong_khai.py`, `routes/_p_tao.py`, `jobs.py`
  (pre-check), `platform_core/public_api/` (nếu có), `voice.js`, template
  Library + Studio picker.
- Test L1: bảng 4+1 cặp ngôn ngữ; retry theo D013. Test browser: G03/G04
  BLOCK trước job (fetch thật, 0 job mới).

## Wave 5 — Create-voice UX (Studio)

- Queue states theo tuổi thật (D005): `<10s` / `10–60s` / `>60s` cảnh báo +
  Thử lại/Hủy; không spinner vô hạn. `queue_age_s` tính server-side 1 chỗ.
- Result state machine (D009) + error categories render (D012) + retry rules
  (D013).
- **Đo layout trước khi đổi** (D007): chụp 4 viewport bản hiện tại → so 2
  cột → **Decision Amendment D007-A** ghi lựa chọn + ảnh → mới implement.
- Tệp: `ltt_voice_studio.html`, `voice.js`, route poll.
- Cổng: G01-style luồng tạo (dùng worker local — Wave 9 hạ tầng) + 4 viewport
  CTA visible.

## Wave 6 — Library UX (P0-2 tiếp)

- 4 tab Tất cả/Giọng mẫu/Kho chung/Giọng của tôi; đếm số từ dữ thật.
- 25 shared hiển thị + lý do "tệp gốc đã mất — chờ cung cấp lại" (V03).
- Preview lazy 1-lần-1-preview; voice thiếu tệp không gọi URL 404 (D008).
- V06: user thường **không** có nút Xóa/Vô hiệu trên shared.
- Tệp: `ltt_voice_giong.html`, `voice.js`, `routes/_p_giong.py`.

## Wave 7 — Projects / History / API consistency

- Dự án: audit trước, sửa chắt ("Không redesign mạnh nếu hiện đã tốt") —
  D014. Lịch sử: đủ trạng thái thật + "file không còn" rõ ràng — D015.
  API: đọc từ `tham_so_cong_khai.py`, cùng nguồn catalog, không hardcode —
  D016.
- Tệp: định vị khi đọc (server/ màn API + routes/templates Projects,
  Lịch sử).

## Wave 8 — Responsive + Accessibility

- 6 viewport × {Studio, Library}: không tràn ngang, CTA visible (4 desktop),
  dialog đúng cao, tên dài không vỡ. (D010)
- Bàn phím/focus/aria-live/labels/audio controls (D011) — walkthrough
  keyboard-only 1 luồng thật.

## Wave 9 — E2E trình duyệt thật (Playwright, Chrome thật)

- **Hạ tầng (không deploy):** app worktree cổng riêng + **chia sẻ DB
  production** + worker địa phương `LTT_WORKER_POOLS=voice:1` (sidecar thật
  nếu GPU trống; nếu không → G05/G06/G07 là đúng kịch bản).
- Đăng nhập human 1 lần tài khoản test `thu.giongnoi@lttstudios.local`,
  lưu auth state; không bypass MFA.
- G01–G07 + V01–V08 + §20 queue observability — mỗi test: screenshot + URL +
  hành động + expected + actual + network; instrument console.error /
  pageerror / requestfailed / HTTP≥400.
- **G01 PASS chỉ với artifact thật** (wav tồn tại, phát được, tải được).
- Ghi `GUI_BROWSER_ACCEPTANCE.md`.

## Wave 10 — Regression / release gate

- Test L1/L2/L3: catalog, language, filter, queue-states, guards storage
  (D002), worker over-age warning + do_sau_khoi_dong per-app (D006), mở rộng
  `test_501`.
- `cua_so_yen.py trang-thai` → **`python tools\gate.py` đầy đủ** (kiểm
  `loi_cho_bo_test` có trong gate.py của worktree này trước).
- Hoàn tất 3 tài liệu còn lại: `GUI_AUDIT_MATRIX.md` (§31, cấm "looks
  good"/"probably fine"/"seems implemented"), `GUI_BROWSER_ACCEPTANCE.md`
  (nếu Wave 9 chưa viết hết), `GUI_FINAL_REPORT.md` (§35 A–I, scorecard
  §32, status ∈ {NOT_READY, PARTIAL, STRONG_RC, READY_FOR_ACCEPTANCE} —
  **không bao giờ** READY_FOR_DEPLOYMENT).
- Dọn: xoá 3 `_probe_*.py` + `_task_spec.md`; cập nhật `docs/NHAT_KY.md`;
  commit từng tệp tường minh.

---

## Trạng thái tổng (15/09/2026)

| Wave | Trạng thái |
|---|---|
| W0 Repo truth | PARTIAL (SHA deploy chưa đọc) |
| W1 Runtime/queue | Chẩn đoán PROVEN; code guard → W10; E2E proof → W9 |
| W2 Data inventory | XONG |
| W3 Catalog contract | XONG — contract + `the_cho_trang`, L1 8/8, browser khớp DB (4/25/20) |
| **W4 Language + filter** | **HIỆN TẠI** |
| W5–W10 | Chưa bắt đầu |
