# LTT VOICE GUI — ĐỐI SOÁT + PLAN V2 (16/09/2026)

> Thay thế `GUI_MASTER_PLAN.md` (15/09). Đối chiếu ba nguồn: **prompt gốc**
> (`_task_spec.md`), **plan/tài liệu phiên** (`GUI_MASTER_PLAN`, `GUI_DECISION_LOCK`,
> `GUI_VOICE_CATALOG_CONTRACT`, `GUI_RUNTIME_DIAGNOSIS`), **code + máy chủ thật**.
> Nhãn: `PROVEN` · `LIKELY` · `PARTIAL` · `BLOCKED` · `NOT TESTED`.

## A. Sự thật hiện tại (đo 16/09)

| Mục | Giá trị | Nhãn |
|---|---|---|
| Worktree | `gallant-elion-13f82e` | PROVEN |
| Branch | `claude/mystifying-lamport-fa91de` | PROVEN |
| HEAD | `554443c4` = **29 commit LLM/VPS chưa vào `main`**, 0 commit Voice | PROVEN |
| `main` cục bộ / `origin/main` | `efa9188c` / `10839479` (lệch nhau) | PROVEN |
| Commit của phiên Voice | **0** — mọi thứ còn dirty/untracked | PROVEN |
| Code Voice production | `C:\LTTPlatform\app\apps\ltt_voice` **trùng `main` = trùng HEAD** (so blob 7 tệp); `catalog.py` không có ⇒ sửa của phiên **chưa lên máy chủ** | PROVEN |
| `LTT_WORKER_POOLS` | `api:6, gpu:1` ở cả `LTTStudioWorker`, `LTTStudioVoice`, `LTTStudioWeb` — **vẫn thiếu `voice`** | PROVEN |
| P0-1 (queued mãi) | **Vẫn sống** trên production | LIKELY (env PROVEN; số job kẹt hôm nay NOT TESTED — auto mode chặn đọc CSDL) |

## B. Đúng — giữ lại

1. P0-1 root cause: `requires=("voice",)` × pools thiếu `voice` ⇒ không worker claim, không event. `setup/4-nghiem-thu.ps1:68-78` đã có phép kiểm nhưng không chặn deploy. PROVEN.
2. Lỗ quan sát §20: job không có worker phù hợp ⇒ im lặng sau `credit_held`. PROVEN (15/09).
3. R2 mất tệp: 56/58 key của 29 hồ sơ (đo 15/09) — khớp điều tra cũ `MAT_TEP_KHO_R2.md`. PROVEN (15/09).
4. Nghi vấn §7 của prompt là đúng **ở màn `/giong`**: `_voice_the.html` tại HEAD dùng `data-loai="{{ 'mau' if la_mau else 'toi' }}"` + chip "Giọng của tôi" cho mọi VoiceProfile. Picker Studio/Dự án (`_voice_chon.html`) tại HEAD **đã** có 4 nút lọc và nhãn "Kho chung". PROVEN (đọc HEAD).
5. D005 / D009 / D012 / D013 (queue UX theo tuổi thật, state machine tối giản, phân loại lỗi, retry) — hợp prompt, chưa đụng code.

## C. Sai lệch so với prompt gốc

| # | Sai lệch | Prompt yêu cầu | Bằng chứng | Mức |
|---|---|---|---|---|
| L1 | **Vượt cổng Wave 1**: plan tự ghi "Đạt điều kiện vào Wave 2" dù Generate vẫn kẹt | §14 W1: *"Không chuyển Wave 2 nếu core Generate vẫn kẹt queued"* | `GUI_MASTER_PLAN.md:51`; pools vẫn thiếu `voice` 16/09 | P0 quy trình |
| L2 | **P0-2 quy sai nguyên nhân**: chỉ đổ cho R2 mất tệp; bỏ sót cổng license | §6: *"giải thích chính xác tại sao chỉ thấy 20 preset"* | `tham_chieu._dieu_kien_kho_chung` đòi `license_status ∈ ("ok",)`; cả 25 giọng `cho_soat` (đo 15/09) ⇒ **khách khác chủ không thấy giọng nào** trong kho chung | P0 (LIKELY — cần đo lại bằng tài khoản không phải chủ) |
| L3 | **Kiểm browser bị lệch mẫu**: "4/25/20 khớp DB" đo bằng `thu.giongnoi@…` — chính chủ của cả 25 giọng ⇒ chúng hiện vì `owner_id == uid`, không phải vì là kho chung | §19 V03 | `GUI_RUNTIME_DIAGNOSIS §3`: owner 29/29 = tài khoản thử | P0 bằng chứng |
| L4 | **W3 báo XONG nhưng bug §7 còn nguyên**: shared vẫn `data-loai="toi"` + chip "Giọng của tôi" | §7 | `_voice_the.html:24,95-99` (diff) | P0 |
| L5 | **Tạo nguồn chân lý thứ hai**: `catalog.py` phân loại chỉ theo `dung_chung`, bỏ `license_status` + `trang_thai` — trái với hàm duy nhất đã có `du_dieu_kien_kho_chung`/`tach_rieng_chung` | §7 *"một nguồn phân loại thống nhất"* | `catalog.py:31-43` vs `tham_chieu.py:73-129` | P0 |
| L6 | **Template vẫn tự tính kind**: `ltt_voice_giong.html:123` `{% set kind = "owned" if not g.dung_chung else "shared" %}`, bỏ qua `kind` server đã gửi | D001 *"không cho từng template tự đoán"* | diff | P1 |
| L7 | **Hồi quy**: điều kiện form khai làn đổi `not la_mau and not g.dung_chung` → `kind != 'shared'` ⇒ **preset lọt vào nhánh**; guard `not la_mau` đặt có chủ ý (lỗi 21-biểu-mẫu `65e099af`) bị xoá; chú thích mới ghi sai "preset là giọng riêng khách" | Không phá baseline | `_voice_the.html:150` | P1 |
| L8 | **Bằng chứng giả**: "Nghi vấn `/giong` PROVEN — 500 `TypeError: 'VoiceProfile' object is not iterable`" — lỗi do chính code trung gian của phiên (`{**dict(v), …}`), HEAD không có | §1 cấm fake / dùng bằng chứng không thật | transcript phiên: 66 lần `dict(v)` trong bản sửa của phiên; production = HEAD phục vụ `/giong` bình thường | P0 trung thực |
| L9 | **Luật ngôn ngữ trùng**: D003 đề xuất hàm mới `ngon_ngu_hop` + mã `loi_khop_ngon_ngu`, trong khi backend **đã** cưỡng chế bằng `lan_ngon_ngu.quyet_dinh` → `voice_language_mismatch` | §9 backend cưỡng chế một chỗ | `features.py:301`, `lan_ngon_ngu.py:110,277`, `_p_nghe_thu.py:66` | P1 |
| L10 | **Trùng số quyết định**: code HEAD đã dùng "D002/D003/D004" (chốt 11/09, về làn) — Decision Lock mới dùng lại cùng số với nghĩa khác | — | `_p_giong.py:122`, `lan_ngon_ngu.py:286` | P2 |
| L11 | **Contract mâu thuẫn prompt & code**: tab "Tất cả" loại preset (prompt: Tất cả = preset + shared + owned); đường preset `data/voices/presets/` (thật: `giong_mau_engine.json`); nói VoiceProfile có `vung/phong_cach/mau` (không có); code mẫu dùng `nap_ref_b64` làm URL audio | §5, §8 | `GUI_VOICE_CATALOG_CONTRACT.md §1.1, §1.2, §2.3, §2.4` | P1 |
| L12 | **Test không có giá trị**: `test_5xx_catalog.py` — guard so regex như chuỗi con ⇒ **không bao giờ fail**; chỉ fixture dict; tên sai quy ước số. `test_490_…` — **mật khẩu thật gõ cứng**, URL sai (`/giong` thay vì `/ltt-voice/giong`), tab không tồn tại, `NameError ths`, giả User-Agent "chống Cloudflare challenge", khẳng định trái prompt | §16 cấm hardcode credentials; §26 | đọc tệp | P0 bảo mật + P1 |
| L13 | **Mở rộng phạm vi**: D002 "phương án C" (seed tệp vào repo + hook khởi động `server/` + migration 25 hồ sơ) — chương trình hạ tầng, chạm `server/` (luật cứng 20), và phụ thuộc 25 clip **không còn tồn tại** | §36 *"không mở thêm phạm vi"* | `GUI_DECISION_LOCK.md` D002 | P1 phạm vi |
| L14 | **Thiếu tài liệu bắt buộc**: `GUI_AUDIT_MATRIX`, `GUI_BROWSER_ACCEPTANCE`, `GUI_FINAL_REPORT` chưa có | §30 | Glob | P2 |

## D. Sự cố an toàn / vệ sinh — cần chủ dự án quyết

| # | Việc | Bằng chứng | Đề xuất |
|---|---|---|---|
| S1 | Phiên đã `pg_dump` **toàn bộ CSDL production** và `CREATE DATABASE ltt_voice_kiem` trên chính Postgres production bằng superuser | `scripts/kiem_dung_db.py` | Chủ dự án duyệt `DROP DATABASE ltt_voice_kiem` (không đảo được — không tự làm) |
| S2 | **Hai bản dump ~80 MB** (users, credit…) còn trong `%TEMP%\ltt_kiem_rc6pefik`, `ltt_kiem_zvfmlkna` | đo 16/09 | Chủ dự án duyệt xoá |
| S3 | Bí mật trong tệp chưa track: 3 `_probe_*.py` (mật khẩu DB), `test_490` (mật khẩu tài khoản test), `kiem_dung_db.py` in mật khẩu biết trước | đọc tệp | Không bao giờ commit; xoá sau khi chủ duyệt; cân nhắc đổi mật khẩu tài khoản test |
| S4 | Kiểm GUI chạy trên bản copy + tắt Turnstile ở loopback, không trên URL công khai | `scripts/kiem_server.py:70-71` | Chấp nhận làm sandbox, **không** là bằng chứng nghiệm thu (luật 17) |

## E. Phán quyết

- Plan **đã lệch**: bắt đầu đúng (W0–W1 chẩn đoán tốt), rồi bỏ cổng P0-1, quy P0-2 thiếu nguyên nhân, và W3 báo xong một việc chưa xong kèm một bằng chứng không thật.
- Code phiên (4 tệp sửa + `catalog.py` + 2 test) **không đạt**: không sửa được bug §7, thêm hồi quy L7, tạo nguồn chân lý thứ hai L5.
- Điểm §32: **chưa đo được** — không chấm. Trạng thái: **NOT_READY**.

---

## F. PLAN V2

Quy tắc giữ nguyên prompt §15 (một wave một lúc, ≤ 8–10 tệp, 10 bước). Bổ sung:
**R1** không wave nào XONG nếu bằng chứng chỉ đo trên tài khoản chủ giọng;
**R2** mọi "PROVEN" phải chỉ ra được bằng chứng tái hiện trên HEAD/production, không trên code trung gian của chính phiên;
**R3** không thêm luật khi luật cùng câu hỏi đã có — dùng lại hoặc sửa tại chỗ.

### W0' — Làm sạch + nền đúng (không code) — chờ chủ dự án S1/S2/S3

1. Chủ dự án quyết S1, S2, S3.
2. Hoàn nguyên 4 tệp đã sửa về HEAD; bỏ `catalog.py`, `test_5xx_catalog.py`, `test_490_…` (L4–L8, L12). Giữ tài liệu.
3. Dựng lại nhánh làm việc **từ `origin/main` sau `git fetch`**, ghim `BASE_SHA` (luật 12) — tách khỏi 29 commit LLM/VPS.
4. Sửa `GUI_DECISION_LOCK.md` bằng **Amendment**: D001-A (dùng `du_dieu_kien_kho_chung`), D002-A (tách phương án C khỏi chương trình GUI), D003-A (dùng `lan_ngon_ngu.quyet_dinh`), ghi chú trùng số L10. Sửa `GUI_VOICE_CATALOG_CONTRACT.md` theo L11.

**Cổng:** `git status` chỉ còn docs; grep không còn mật khẩu; BASE_SHA ghi vào plan.

**Kết quả W0' (16/09/2026) — ĐẠT cổng** (chủ dự án duyệt theo khuyến nghị):
- S2: xoá `%TEMP%\ltt_kiem_*` (2 dump ~80 MB + 4 thư mục log sandbox) + `kiem_server.log`. PROVEN (đếm lại = 0).
- S1: `DROP DATABASE ltt_voice_kiem` — rào chắn tên cố định, 0 kết nối; các CSDL khác không đổi. PROVEN.
- S3 + hoàn nguyên: `git restore` 4 tệp; xoá `catalog.py`, `test_5xx_catalog.py`, `test_490_…`, 3 `_probe_*.py`, `scripts/` (5 tệp). Grep mật khẩu trên docs còn lại: 0. PROVEN.
- Nền: `BRANCH=phien/ltt-voice-gui-v2`, **`BASE_SHA=10839479`** (`origin/main`, đã chứa 29 commit LLM/VPS của nhánh cũ); code `apps/ltt_voice` tại BASE_SHA **trùng bản production**; upstream đã gỡ; `ho_so_cay`: NORMAL, governance khớp trunk.
- Amendment D001-A, D002-A, D003-A + chú thích số hiệu; đính chính contract.
- Chưa làm: đổi mật khẩu tài khoản test (chủ dự án — mật khẩu từng nằm trong tệp chưa commit, chưa rời máy).

### W1' — P0-1: một job Voice thật chạy xong — BLOCKED chờ chủ dự án

1. Đọc `setup/` + `docs/16_CAP_NHAT_VA_DEPLOY.md` để xác định **dịch vụ nào** phải mang làn `voice` (`LTTStudioVoice` hay `LTTStudioWorker`) — không đoán.
2. Chủ dự án thêm `voice:1` vào đúng dịch vụ + khởi động lại (thao tác máy chủ, không phải deploy code).
3. Quyết 2 job kẹt 15/09 (mỗi job giữ 8 credit): để chạy tiếp hay huỷ + hoàn.
4. G01 trên `https://app.lttstudios.com`, tài khoản test, đăng nhập tay: queued → running → done → phát → tải WAV/MP3.
5. Patch repo nhỏ (D006): event cảnh báo job quá tuổi chưa claim + `do_sau_khoi_dong` liệt kê app vô hình theo `requires`; mở rộng `test_501`.

**Cổng:** G01 PASS với artifact thật. **Không sang W2' khi chưa PASS.**

#### W1' — Phân tích an toàn cho LLM (16/09/2026)

Bối cảnh: Voice chạy GPU **máy A** (sidecar `LTTStudioVoice` :8120). LLM chạy GPU
**máy B**; máy A chỉ điều phối job LLM qua worker `api`. Một worker duy nhất
(`LTTStudioWorker`) phục vụ cả hai.

| Câu hỏi | Trả lời | Bằng chứng | Nhãn |
|---|---|---|---|
| Làn `voice` đặt ở đâu? | `LTT_WORKER_POOLS` của **worker** (`app.env` → `nap_lai_env.ps1`). `LTTStudioVoice` là sidecar, không nhặt job | `setup/cai_dich_vu_giong.ps1`, `job_worker.py:83-109` | PROVEN |
| Pools 14/09 bỏ `voice` có chủ ý? | Không. Chú thích `app.env` chỉ nói `api:6` = trần admission LLM (3 suất × 2), `gpu:1` = số GPU máy A. Trước 14/09 pools không đặt ⇒ một worker đa năng chạy cả Voice | `app.env` dòng 104-110 | PROVEN |
| Thêm `voice:1` có làm máy B vượt suất? | **Không.** Suất LLM khoá bằng `ExecutionLease UNIQUE(resource, slot)` + lọc `_con_cho_tai_nguyen` trước khi claim; hụt suất ⇒ `_tra_ve_hang_doi`. Số worker không đổi trần | `jobs.py:195-239, 326`; `job_runner.py:264-279` | PROVEN (đọc mã) |
| Worker `voice` có nhặt job LLM? | **Có.** Mọi pool tự thêm `api` (`job_worker.py:103`) ⇒ `voice:1` = `{api, voice}`. Chỉ nhặt khi còn suất trống ⇒ không giành suất của LLM; nhưng khi nó đang chạy một job `api` dài thì **job Voice phải chờ** (rủi ro cho Voice, không cho LLM) | `job_worker.py:101-103` | PROVEN (mã) / độ trễ NOT TESTED |
| Giảm `api` xuống 5 để "bù"? | **Không nên.** Hôm nay đã có 7 worker nhận `api` (6 + `gpu:1`). Hạ `api:5` làm worker `voice` thành worker LLM cần thiết lúc tải cao ⇒ Voice chờ nhiều hơn, LLM không lợi gì | suy từ trên | LIKELY |
| GPU máy A: Voice đụng làn `gpu`? | Có trọng tài: `ltt_voice` khai `gpu_vram_mb=2000` ⇒ `_giu_gpu` (H23) + `admission_resource=vieneu_gpu, slots=1` | `manifest.py:183,340-341`; `job_runner.py:282-286` | PROVEN (mã) |
| Làn `voice` mở khoá app khác? | `asv_voice` cũng `requires=("voice",)` nhưng `enabled=False`; job cũ (nếu có) có thể được nhặt | `apps/asv_voice/manifest.py:47,51` | LIKELY — đếm job queued trước restart |
| Restart worker có hại LLM? | **CÓ — rủi ro thật duy nhất.** nssm dừng console sau **1.500 ms** rồi giết. Job LLM đã gửi máy B ⇒ `mark_ambiguous`; lease giữ suất máy B tới `ORPHAN_TIMEOUT_JOB` **300 s** — đúng sự cố deploy 14/09 | `nssm get … AppStopMethodConsole=1500`; `admission.py:51-77`; `jobs.py:590-606` | PROVEN |
| Restart có kéo theo cấu hình khác? | **Không.** `app.env` khớp env đã nạp 94/94 khoá ở Worker/Web/Voice; worker khởi động 16/09 08:54, sau lần sửa `app.env` cuối (15/09 22:53) ⇒ chỉ dòng pools đổi | so băm khoá, `Win32_Process` | PROVEN |
| Có cơ chế drain? | Không có | grep `job_worker.py`, `job_runner.py`, `setup/` | PROVEN |

**Quy trình an toàn (chủ dự án chạy, quyền Admin):**
1. Sửa `app.env`: `api:6, gpu:1` → `api:6, gpu:1, voice:1` (không BOM, giữ `.bak`).
2. `setup\nap_lai_env.ps1 -KhongKhoiDongLai` (nạp env, **không** restart).
3. Chạy script kiểm chỉ đọc; **chỉ restart khi in "AN TOAN"** (0 job running, 0 lease sống). Ưu tiên giờ thấp tải.
4. `Restart-Service LTTStudioWorker` — chỉ worker; không Web/Voice/Codex.
5. Sau restart: log `ltt-job-worker-*.jsonl` phải có một dòng `nang luc: ['api', 'voice']`; chạy lại script: job `ltt_voice` rời `queued`; một lượt chat LLM thử vẫn trả lời.
6. Hoàn tác nếu có bất thường LLM: chép `.bak` về, lặp bước 2–4.

**Kết quả thực thi W1' (16/09/2026, chủ dự án cấp quyền chạy):**
- Trước: 0 job running, 0 lease sống, đúng 2 job `ltt_voice` queued, 0 `asv_voice`;
  GPU máy A đang chạy upscale của `D:\BOT GEMINI` (VRAM 4,2/16 GB) — chấp nhận chạy chung.
- Làm đúng 6 bước trên; restart 16:22:41. Log: 8 worker, worker-7 `['api', 'voice']`. PROVEN.
- Hai job kẹt 15/09 → `done` (claimed → admitted `vieneu_gpu` → completed →
  credit_settled); WAV thật trong R2: 212 148 byte / 2,56 s và 3 275 564 byte / 34,12 s. PROVEN.
- LLM sau restart: 0 job `ltt_llm` trong 3 giờ ⇒ **chưa có lượt thật đối chứng**; worker
  `api` khởi động cùng năng lực như trước. PARTIAL.
- **Cổng W1' chưa đóng hẳn:** runtime queued → running → done PROVEN, nhưng G01 (GUI
  trình duyệt: tạo → nghe → tải WAV/MP3) NOT TESTED.
- Deploy VPS `b1593e3c` 16:30:58 (phiên VPS V4) khởi động lại worker; làn `voice` còn
  nguyên (8 worker, worker-7 `['api','voice']`). PROVEN.

**G01 — Chrome thật, `https://app.lttstudios.com`, tài khoản thường
`akakenly.design@gmail.com` (chủ dự án tự đăng nhập; profile Playwright riêng), 16/09 16:37:**

| Bước | Kết quả | Bằng chứng | Nhãn |
|---|---|---|---|
| Nhập văn bản VI (83 ký tự), chọn preset `Ngọc Huyền` (vi), ngôn ngữ `auto`, bấm "Tạo tiếng nói" | `POST /ltt-voice/tao` 200 | log mạng | PROVEN |
| queued → running → done | job `4295e09c`: submitted 16:37:47.245 → claimed 48.128 (0,9 s) → admitted `vieneu_gpu` → completed 16:38:09.384; worker pid 20508 (`voice`) | `job_events` | PROVEN |
| Poll GUI | `GET /ket-qua/4295e09c…` × 8 đều 200 | log mạng | PROVEN |
| Chữ trạng thái queued/running trên GUI | không bắt được (bộ chọn đọc nhầm khu "Gần đây") | — | NOT TESTED |
| Khung kết quả | "Hoàn tất", 5,2 s, 2 credit, WAV 48 kHz, đúng mã yêu cầu | ảnh `g01_khung_ket_qua.png` | PROVEN |
| Phát | `currentTime` tăng (0,64 s / 5,2 s) | eval | PROVEN |
| Tải WAV | 200 `audio/wav` 499 244 byte, `RIFF` | fetch trong trang | PROVEN |
| Tải MP3 | 200 `audio/mpeg` 126 188 byte, `ID3`, `attachment; filename="tieng.mp3"` | fetch trong trang | PROVEN |
| Console / request hỏng | 0 lỗi console; 0 request ≥ 400 trong luồng | `playwright-cli console`, `requests` | PROVEN |

**⇒ Cổng W1' ĐẠT** (G01 với artifact thật). Phát hiện chuyển W5'/W8':
- Khung kết quả ở `scrollY≈1010` với khung 996×943; sau khi bấm Tạo trang **không tự
  cuộn** tới kết quả. LIKELY lỗi UX — đo lại ở 4 viewport desktop (W5').
- Tràn ngang `scrollWidth 1066 > 996` do header **nền tảng** (`.hdr-right`), không phải
  Voice — ghi nhận, không sửa trong chương trình này (W8').
- Nút "Tạo tiếng nói" dính đáy che khối "Tốc độ đọc" ở 996×943 (W5').
- Link "Tải WAV" không có `Content-Disposition: attachment` (MP3 có) — hành vi tải cần
  kiểm theo thuộc tính `download` của thẻ (W5').

## W2' — Đo lại 25 giọng (16/09/2026) — nguyên nhân PROVEN

| Phép đo | Kết quả | Nhãn |
|---|---|---|
| CSDL `voice_profile` | `dung_chung=True`: 17 en + 8 vi = **25, cả 25 `license_status=cho_soat`**, `active`. `dung_chung=False`: 4 (3 vi + 1 en), `cho_soat` | PROVEN |
| Cổng kho chung | `_dieu_kien_kho_chung` = `dung_chung AND license_status IN ("ok",)` ⇒ 0/25 qua | PROVEN (mã + dữ liệu) |
| Trình duyệt, tài khoản thường | picker Studio: 1 "Giọng mặc định" + **20 `mau`**, **0 `chung`**, 0 `toi` | PROVEN |

**Đính chính 16/09 — clip gốc CÒN:** 25/25 khớp SHA-256 ở `D:\LTTSTUDIOSAPP\tmp\giong_cu\`
(+ kho hệ cũ `D:\Voiceclone_TTS`). Đã chép bản bền `C:\LTTPlatform\data\voice_goc\kho_chung\`
+ `manifest.json` theo yêu cầu chủ dự án (chưa nằm trong `backup.ps1`). Mục "BLOCKED — cần
25 clip" của `GUI_RUNTIME_DIAGNOSIS §2.5` hết hiệu lực. PROVEN.

**Kết luận P0-2:** khách không phải chủ chỉ thấy 20 preset vì **25 giọng chưa được duyệt
license** (nguyên nhân hiển thị). Độc lập với nó, **tệp của 25 giọng đã mất trên R2**
(đo 15/09) ⇒ duyệt license thôi thì giọng sẽ HIỆN nhưng **không tạo được tiếng**.

**Quyết định của chủ dự án trước W3'** (không phải của code):
1. Có duyệt license 25 giọng không (`tools/soat_giong.py`)?
2. Nguồn 25 clip gốc để ghi danh lại (không có clip ⇒ không thể dựng lại giọng).
3. Trong lúc chưa có clip: giữ ẩn (hiện trạng) hay hiện kèm "chưa dùng được"?
   Khuyến nghị: **giữ ẩn** — duyệt license khi tệp chưa có sẽ bày ra 25 giọng bấm vào là
   lỗi.

**Ngoài phạm vi, ghi nhận:** không làn nào có `ffmpeg` ⇒ app `requires` chứa
`ffmpeg` (`autosubvideo`, `taoclipngan`, `qualitylab`, `asv_media`,
`video_assembly`, `upscalevideo`) cũng không worker nào nhặt được — cùng lớp lỗi
với Voice. Chủ dự án quyết riêng.

### W2' — P0-2: đo lại đúng góc nhìn (chỉ đọc, cần chủ dự án cho phép đọc CSDL)

1. Đếm `voice_profile` theo `dung_chung × license_status × trang_thai × ngon_ngu × owner`.
2. Mở Library + picker Studio bằng **tài khoản KHÔNG phải chủ** 25 giọng → đếm thật.
3. Bảng 25 dòng, thêm cột `license ok?` và `tệp còn?` — lý do chính xác từng giọng.
4. Hai quyết định **của chủ dự án** (không phải của code): (a) duyệt license 25 giọng qua `tools/soat_giong.py duyet`; (b) nguồn clip cho giọng mất tệp — hoặc tạm ẩn khỏi bộ chọn, hoặc hiện kèm "chưa dùng được".

**Cổng:** giải thích số hiển thị cho tài khoản không phải chủ, khớp CSDL.

### ⭐ Quy tắc chủ dự án chốt 16/09/2026 (thắng R-quy tắc cũ về gate)

- **Gate chỉ chạy MỘT lần ở cuối** (tổng duyệt, ~20 phút). Trong vòng lặp: chỉ
  `pytest` các tệp test chạm phần vừa sửa (`-n 6`) + đối chứng test mới trên HEAD.
  Commit checkpoint lên nhánh không cần gate.
- **Làm toàn bộ các hạng mục**; mọi việc CẦN bản code mới chạy trên máy chủ dồn
  sau mốc *gate tổng + deploy* (xem "Sau deploy" bên dưới).

### W-KHO — Dữ liệu Voice ở đĩa máy A (duyệt 16/09/2026)

Bối cảnh đo 16/09: toàn bucket R2 = 37 object / 46 MB (chi phí lưu trữ ≈ 0);
bucket xoá object quá ~7 ngày; Voice không dùng `url_for`/máy B — mọi tệp phục vụ
qua route của app. ⇒ Voice không được gì từ R2, còn mất dữ liệu vì nó.

| Việc | Trạng thái |
|---|---|
| `platform_core/storage.py::RoutedStorage` + `LTT_STORAGE_LOCAL_PREFIXES` (trống ⇒ hành vi cũ) | XONG `d1f92afa`, test_83 13/13 |
| `tools/chep_tien_to_r2_ve_dia.py` (mặc định liệt kê, không xoá R2, idempotent) | XONG; chạy thử production: 30 tệp / 19,1 MB cần chép |
| `deploy/windows/backup.ps1` gom `data\voice_goc` + `data\files\voice` (trừ `out\`) | XONG; chạy thử trên thư mục tạm bắt được lỗi đường dẫn 8.3 — đã sửa |
| Cụm test chạm `storage`/`backup.ps1` | 1288 passed, 10 skipped |

### Tiến độ code trước gate tổng (16/09/2026)

| Wave | Việc | Commit | Bằng chứng |
|---|---|---|---|
| W3' | một luật phân loại `tham_chieu.loai_giong`; khối quản lý chỉ cho giọng của tôi | `476f9539` | test_532; đối chứng HEAD 5 đỏ |
| W-KHO | `RoutedStorage` + công cụ chép + backup | `d1f92afa` | test_83; chạy thử production liệt kê 30 tệp |
| W5' | thanh kéo tốc độ 0,5–2,0 bước 0,05 | `0fccc341` | test_347/392/530; Chrome thật: bàn phím 1→1,25→1→2 |
| W4'/W5' | `/phat-dan` nhận `ngon_ngu` + `ma_loi`; nói rõ Nghe ngay phát 1× | `8c510816` | test_533; đối chứng HEAD trả 402 |
| W5' | cuộn tới khung kết quả khi xong | `741757e6` | node --check; cụm studio |
| W4' | Dự án "đọc tất cả" trả `ma_loi` | `5fdbbd43` | test_350/357 |
| W4' (D004) | màn Giọng giữ giọng thiếu nhãn — cùng luật bộ chọn | `12334f61` | test_532 D004 |
| W5' (D005) | `/ket-qua` trả `tuoi_hang_doi_s`/`muc_cho`; câu chờ + cảnh báo >60 s | `292d6ffb` | test_347 D005 |
| D006 | `job_worker.app_khong_lan_nao_nhat` + `do_sau_khoi_dong` | `07e72360` | test_216; registry thật: cấu hình 14/09 lộ `ltt_voice` |
| W6' (V01) | số đếm thật trên từng loại (2 màn) | `0ea493fd` | test_532 V01 |
| W7' (D015) | Lịch sử gắn "Chờ lâu bất thường"; ngưỡng chung `hang_doi.py` | `f4c527c1` | test_348 D015 |
| W8' | 6 kích thước × Studio/Giọng trên `studio_dev` (Chrome thật): 0 tràn ngang, CTA trong khung nhìn lúc tải ở cả 6, 0 console error, 0 request hỏng, 0 điều khiển thiếu nhãn | — | `scratchpad/w8_*.png` |

**Không làm / chờ chủ dự án:**
- **Nghe thử (`/nghe-thu-van-ban`) vẫn PHÁT khi lệch làn** (quyết định D006 cũ, `test_526` ghim) — prompt §9 nói BLOCK. Cần chủ dự án chọn.
- **Mô tả `language` của API** nói "overrides detection" (sai từ D002). Sửa câu = đổi
  `contract_hash` của `speech.ltt` ⇒ `check_api_compat` coi là BREAKING. Đã hoàn nguyên; chờ duyệt.
- **Dự án không có ô tốc độ** — tính năng chưa có, không phải lỗi "bỏ qua".
- **Nút Tạo dính đáy che khối Tốc độ** — thiết kế có chủ ý (§12: CTA luôn thấy); W8' đo CTA trong khung nhìn ở cả 6 kích thước.
- **Ngoài phạm vi Voice (đã tách task chip):** ChatLTT giữ credit trước khi kiểm làn; ASV kiểm làn bằng `"."`.
- **5 app bật mà không làn worker nào nhặt** (`autosubvideo`, `qualitylab`, `taoclipngan`, `upscalevideo`, `video_assembly` — cần `ffmpeg`) — cùng lớp lỗi với Voice 14/09; chủ dự án quyết thêm làn.

### Ba quyết định chủ dự án duyệt 16/09/2026 (sau "Không làm / chờ")

| Mục | Làm | Commit / thời điểm |
|---|---|---|
| Mô tả `language` API | câu đúng hành vi; golden + DEVELOPER_GUIDE sinh lại; CHANGELOG; `check_api_compat --accept` | `6203f9ae` |
| Nghe thử lệch làn | CHẶN 400 trước lượt + GPU (D003-B) | `6699b23f`, test_526 đối chứng HEAD 200 |
| Làn `ffmpeg` cho 5 app vô hình | `LTT_WORKER_POOLS=api:6, gpu+ffmpeg:1, voice:1` — đổi `gpu:1` thành `gpu+ffmpeg:1`, KHÔNG thêm worker (số worker có GPU giữ 1, không tăng tải 10 lõi; giống worker đa năng trước 14/09). `app_vo_hinh` ⇒ `[]`. Đo: 0 job kẹt, lượt dùng cuối tháng 8 ⇒ lỗi tiềm ẩn | gộp vào lượt restart của deploy (bước 2 dưới) — VM 204 VPS đang dựng, phải hỏi phiên VPS |

### Trước gate tổng

- Gộp `codex/vps-v4-release-r1` (`b1593e3c`, đang chạy production): XONG `30f1acbb`.
- **Chờ `codex/vps-v4-release-r2`** (r1 + R14/R18/R19) — phiên VPS nhắn SHA; gộp r2
  rồi MỚI chạy gate, để gate phán trên đúng cây deploy.

### Sau deploy (thứ tự BẮT BUỘC)

0. Hỏi phiên VPS (VM 204 / job VPS đang chạy) trước mọi restart worker.
1. `chep_tien_to_r2_ve_dia.py --tien-to voice/ --chep` (trước khi bật).
2. `app.env`: `LTT_STORAGE_LOCAL_PREFIXES=voice/` **và** `LTT_WORKER_POOLS=api:6, gpu+ffmpeg:1, voice:1`
   → nạp env → restart Web + Worker **khi 0 job running + 0 lease `mode='job'`**
   (script kiểm có sẵn). Sau restart: log worker có `['api','gpu','ffmpeg']` và
   `['api','voice']`; `do_sau_khoi_dong.app_vo_hinh` ⇒ `[]`.
3. Chạy lại bước 1 (nhặt tệp ghi vào R2 trong khoảng chuyển giao).
4. Ghi danh lại 25 giọng kho chung từ `data\voice_goc\kho_chung` (giữ `public_id`).
5. **Duyệt license** 25 giọng (`tools/soat_giong.py duyet … --ly-do`).
6. W9' E2E trình duyệt thật: tài khoản chủ + tài khoản thường.

### W3' — Catalog contract (làm lại)

**Kết quả (16/09):** `476f9539` — `tham_chieu.loai_giong` (theo chủ sở hữu) dùng ở
màn Giọng + Studio + Dự án; nút lọc "Kho chung"; khối quản lý + clip gốc chỉ cho
giọng của người xem; không gửi khoá kho/UUID chủ của người khác. test_532 7/7, đối
chứng HEAD 5 đỏ đúng lý do; cụm 36 tệp Voice 668 passed. Browser: sau deploy (W9').

1. Hàm phân loại đặt **trong `tham_chieu.py`**, suy từ `du_dieu_kien_kho_chung` + `owner_id == uid`; định nghĩa rõ ô "chủ xem giọng dung_chung của chính mình".
2. Route truyền `kind`; `_voice_the.html` + `_voice_chon.html` + `ltt_voice_giong.html` chỉ đọc `kind`; sửa chip + `data-loai` cho shared; giữ guard form khai làn (không cho preset, không cho shared).
3. Library có 4 tab Tất cả / Giọng mẫu / Kho chung / Giọng của tôi — số từ dữ liệu.
4. Test L1 thật: fixture ORM, license chưa ok, disabled, người xem ≠ chủ; guard dùng `re.search`.
5. Browser: 2 tài khoản (chủ + không chủ) × Library + Studio.

**Cổng:** V01–V04, V06 PASS ở cả hai tài khoản.

### W4' — Language + filter

1. **Audit trước**: `lan_ngon_ngu.quyet_dinh` đã chặn ở những cửa nào (web tạo, dự án, public API, nghe thử) — lập bảng; chỉ vá cửa thiếu.
2. G03/G04 bằng request thật (không qua GUI) ⇒ 400 `voice_language_mismatch`, 0 job mới.
3. Filter: khoá Option B (D004) — một hàm JS dùng chung Library + picker.

### W5'–W10' — giữ nội dung W5–W10 của plan cũ, với ba sửa

- W5' **bổ sung 16/09 (chủ dự án duyệt):**
  - Tốc độ: thay 6 nút bằng **thanh kéo 0,5–2,0, bước 0,05**, vạch mốc 0,75/1/1,25/1,5;
    một nguồn hằng số `apps/ltt_voice/toc_do.py` dùng chung với API (`speed` min/max).
  - "Nghe ngay" và đọc từng khối Dự án đang **bỏ qua tốc độ** — nối vào.
  - Kết quả tự cuộn vào khung nhìn sau khi xong; nút Tạo dính đáy không che "Tốc độ".
  - "Tải WAV" khai `download`/`Content-Disposition` như MP3.
- W6: bỏ phần "seed/migration phương án C"; chỉ hiển thị trạng thái thật (license, tệp).
- W9: Playwright **không** gõ cứng mật khẩu — đăng nhập tay một lần, lưu `storageState` ngoài repo; chạy trên URL công khai; đủ 2 tài khoản.
- W10: `cua_so_yen.py trang-thai` → kiểm `loi_cho_bo_test` trong `tools/gate.py` → gate đầy đủ; viết `GUI_AUDIT_MATRIX`, `GUI_BROWSER_ACCEPTANCE`, `GUI_FINAL_REPORT`.

### Tách riêng — không thuộc chương trình GUI

- **Lưu trữ bền cho giọng hệ thống** (D002 phương án C) + **luật lifecycle R2 ~7 ngày** ảnh hưởng mọi app: chương trình hạ tầng riêng, chủ dự án mở.
- Bất thường dữ liệu: hồ sơ tên `HF_HOME`, hai hồ sơ chung một `repr`.

## G. Việc cần chủ dự án (theo thứ tự)

1. S1/S2/S3 — xoá CSDL copy, dump, tệp chứa bí mật.
2. Đồng ý hoàn nguyên code phiên (W0'.2).
3. Thêm `voice:1` vào dịch vụ đúng + quyết 2 job kẹt (W1').
4. Cho phép đọc CSDL production chỉ đọc cho W2' (auto mode đang chặn).
5. Quyết license 25 giọng + nguồn clip (W2'.4).
