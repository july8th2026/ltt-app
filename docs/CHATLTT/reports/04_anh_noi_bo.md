# Phase 04 — Ảnh nội bộ (`image.ltt`): truy vết, chuẩn hoá kết quả, bận/không sẵn sàng/ref hỏng/nộp trùng

## Source
- worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\lttchat-autonomous-build-plan-1cf29d`
- branch: `claude/lttchat-autonomous-build-plan-1cf29d`
- base SHA: `bdddeae` (HEAD lúc bắt đầu phase; gốc chương trình `dac2406` admin-mvp-v3)
- end SHA: (chưa commit — phiên này **không commit**; commit đóng phase do phiên điều phối)
- canonical rules read: `CLAUDE.md`, `AGENTS.md` §8 (8.3 dùng chung ở `platform_core`, 8.4 `platform_core` không biết tên app), `docs/DEVELOPMENT_WORKFLOW.md`, `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` §3–§7 (dòng H43.4), `docs/CHATLTT/STATE.md` ("Giao cho phase sau"), `docs/CHATLTT/reports/02_runtime_noi_bo.md`, `docs/QUYET_DINH_NEN_TANG.md` Q102/Q114, `docs/ANH_NOI_BO/DECISIONS.md` D-005/D-010/D-012/D-037, `docs/ANH_NOI_BO/CHIA_GPU_VOI_VIDEO.md`, `docs/VLM_NOI_BO/ADMISSION_QUEUE_LTT_LLM.md` §2

## Evidence

### Truy vết đường `image.ltt` (đọc mã, file:line ở cây này)

| Bước | Ở đâu | Ghi nhận |
|---|---|---|
| Báo giá + nộp (client nội bộ) | `platform_core/runtime_noi_bo/job.py:45` `bao_gia` → `validate_tool_params` + `credit_for`; `:77` `nop_job` → `submit_with_credit` ép `owner_id`, `max_attempts=manifest.so_lan_thu_for(lane)` (anhnoibo không khai ⇒ 3), `admission_resource = tool.admission_resource or resource_class(manifest)` = `"api"`, `admission_slots=0` | giữ chỗ = `manifest._gia` = `gia.uoc_tran(so_anh_xin, che_do)` (trần ước CAO, `apps/anhnoibo/manifest.py:45`) |
| Worker nhặt | `platform_core/job_runner.py:194` `_chay_mot_job`: claim → `hold_persisted` chỉ khi `admission_slots>0` (không) → `_vram_can("anhnoibo.generate")=0` ⇒ không giữ GPU máy A → `_chay_handler` | đúng: app chỉ gọi HTTP sang máy B (`requires=("api",)`) |
| Handler | `apps/anhnoibo/jobs.py:handle` → `features.chuan_hoa` (`features.py:98`: prompt, mode, refs ≤ 2, **sở hữu theo đoạn thứ hai của khoá** `:84`) → `_dieu_phoi()` (fail-closed thiếu `LTT_RENDER_BASE_URL`) → `DieuPhoi.chay` | |
| Điều phối | `platform_core/image_gen/dieu_phoi.py:83` `chay`: ① dịch prompt (`prompt_dich`, gọi Gemini) → ② vé GET/PUT presigned (`_ve_vao/_ve_ra`, Q102) → ③ `cong.gui` (429 ⇒ `cong_render.BanError` **không bọc**, `:103`) → `_cho` poll 3 s, trần 900 s, 3 lỗi liên tiếp ⇒ `DieuPhoiError`; thành công mà rỗng ⇒ lỗi (`:127`) | thứ tự **dịch trước, hỏi bận sau** — xem phát hiện F2 |
| Chuẩn hoá kết quả | `features.KetQua.as_result()` `features.py:171`: `image_keys`, `prompt`, `da_dich`, `canh_bao`, `so_anh_xin`, `so_anh_that`, `credit_cost = gia.tinh(so_anh_that)` (`:159`), `phien_ban_gia`, gói provider theo ảnh thật | khuôn đã đủ cho khối ảnh của ChatLTT; không cần đổi |
| Quyết toán | `job_runner.py:652` `_quyet_toan_credit` đọc `result["credit_cost"]`; `credit.quyet_toan` kẹp `≤ held` (Q84), hoàn phần dư; `job.result["credit_cost"]` ghi lại = số THU | |
| Phân loại lỗi | `job_runner.py:573` `_provider_failure_kind`: trước phase này chỉ nhận `LoiNguoiGoi`, `cong_vlm.BanError`, `KhongCoProviderNao.busy_only`, 413/OOM, ambiguous; **mọi thứ khác ⇒ `retry`** | đây là lỗ: `LoiTaoAnh` (bọc `BanError`) và mọi lỗi của `chuan_hoa` đều `retry` |

### Phát hiện

| # | Finding | Source/runtime/test | Result |
|---|---|---|---|
| F1 | **Bận tiêu lượt thử.** `cong_render.BanError` bị `apps/anhnoibo/jobs.py` bọc thành `LoiTaoAnh` (Exception thường) ⇒ `_provider_failure_kind` ⇒ `retry` ⇒ `jobs.fail` tăng `attempts`, sau 3 lần bận job `error` + hoàn tiền cho việc chưa chạy | Phase 02 báo cáo; xác nhận bằng `_provider_failure_kind(LoiTaoAnh) == ("retry", 0)` (`test_608::test_loi_ha_tang_van_la_retry` giữ đúng cho lỗi hạ tầng thật) | **ĐÃ SỬA** — `platform_core.jobs.DangBan` + `_provider_failure_kind` nhận nó; `test_607` 17 test |
| F2 | **Mỗi lần quay lại từ hàng đợi là một lượt dịch prompt Gemini** vì `DieuPhoi.chay` dịch (①) trước khi `cong.gui` (③) biết bận. Với `resource_wait` (F1 sửa) và máy B bận cả giờ (video 72,5 phút — D-005), 20 s/lượt ⇒ ~200 lượt dịch cho một câu | `dieu_phoi.py:93-107`; `cong_render.dang_ban()` `:103` có sẵn *"hỏi trước khi gửi việc"* nhưng không ai gọi | **ĐÃ SỬA ở app**: `jobs.py:52` `_xep_lai_neu_may_ban(cong)` hỏi `/health` trước; bận ⇒ `DangBan` với `eta_s`; **không trả lời ⇒ KHÔNG coi là bận** (đi đường thường, hỏng có đếm lượt). `test_607` §3 |
| F3 | **Lỗi của yêu cầu cũng `retry`**: khoá ảnh của người khác, thiếu prompt, mode lạ, quá 2 ref… đều `LoiTaoAnh` thường ⇒ 3 lượt thử cho việc không bao giờ thành — đúng ca `LoiNguoiGoi` sinh ra để sửa (job `a49ce0d3` 31/08 ở app tiếng) | `features.py:84-131` | **ĐÃ SỬA** — `LoiYeuCauAnh(LoiTaoAnh, LoiNguoiGoi)` cho mọi lỗi của `chuan_hoa`; `LoiTaoAnh` thường giữ cho hạ tầng (retry). `test_608` 10 test |
| F4 | Xin 4 nhận 2 ⇒ thu 2, hoàn 6 (t2i: 3 credit/ảnh, giữ 12) — đường thật qua worker | `test_606::test_xin_4_nhan_2_thu_dung_2_va_hoan_phan_du` | PASS |
| F5 | Nộp trùng `idempotency_key` ⇒ một job, giữ tiền một lần; không khoá ⇒ suy từ `(lane, params)` | `test_606` §3 | PASS |
| F6 | `anhnoibo` **không khai** `admission_resource/_slots`, không `gpu_vram_mb` | `apps/anhnoibo/manifest.py:83-86` (`requires=("api",)`) | xem Quyết định D-04.3 — **không sửa manifest** |
| F7 | `job.result["credit_cost"]` sau quyết toán là số THU (không phải số handler báo) — đúng, ChatLTT đọc trường này | `job_runner.py:557-560`; `test_606` | PASS |

### Bằng chứng cho D-04.3 (admission/VRAM của app ảnh)

- Q102 (`docs/QUYET_DINH_NEN_TANG.md:129`): *"Tranh chấp GPU với việc video trên cùng máy B giải bằng ETA + cascade, KHÔNG bằng hàng đợi FIFO chung"*; *"Luật quyết định là `eta_s ≤ NGƯỠNG_CHỜ` thì chờ, lớn hơn thì cascade"*.
- D-005 (`docs/ANH_NOI_BO/DECISIONS.md:121`): video 72,5 phút, đỉnh VRAM 24.251/24.576 MiB (98,7 %); *"không xếp hàng sau job video"*. **D-010 sửa**: cascade sang Gemini **không còn ngầm** — khách chọn; ngưỡng 45 s vô nghĩa. D-012: ETA việc lạ suy từ trung vị lịch sử của cổng.
- D-037 (`:1747`): máy B có **ba** hộ dùng chung GPU (video `E:\LTT AI`, LLM `H:\LTT_LLM`, ta); cổng render dò bận bằng hiệu VRAM `nvidia-smi − ComfyUI` + đếm tiến trình python, ngưỡng 20.500 MB.
- Q114 (`:141`): tài nguyên khai bằng **metadata của tool**, không suy từ slug; *"Gateway máy B vẫn giữ `max_dong_thoi=1` như hàng rào cuối, không làm queue"*; `resource_wait` không tiêu attempt.
- Tiền lệ: `apps/ltt_llm/manifest.py:192` khai `admission_resource="llm_remote", admission_slots=1` cho một tài nguyên **từ xa** cùng kiểu; `apps/ltt_voice/manifest.py:214` `vieneu_gpu`/1.
- Hệ quả đo được của việc **không** khai: hai job ảnh của ta cùng lúc ⇒ cả hai được dispatch, một cái nhận 429 (nay ⇒ `resource_wait` 20 s, không tốn lượt dịch nhờ F2). Chi phí = một GET `/health` + một vòng hàng đợi. Tranh chấp **lớn** (video/LLM) thì admission plane của ta **không nhìn thấy** — chỉ cổng render thấy (D-037), nên admission không giải được phần đó dù có khai.

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| **D-04.1** Tín hiệu "bận" chung cho mọi app | (a) `_provider_failure_kind` nhận thêm `cong_render.BanError` và `ltt_voice.DangBanTam` theo tên · (b) lớp nền tảng `platform_core.jobs.DangBan(ly_do, retry_after_s)`; app dịch/kế thừa · (c) duck-typing theo thuộc tính `retry_after_s` | **(b)** | (a) bắt `platform_core` import lớp của app (vi phạm §8.4) hoặc kéo `image_gen` vào worker chỉ để so lớp; (c) là hợp đồng ngầm không kiểm được. (b) đối xứng với `LoiNguoiGoi` đã có cùng tệp, app nào cũng ném được không cần biết cổng khác. Giữ nguyên nhánh `cong_vlm.BanError` để đường text không đổi một byte | Có: xoá lớp + 1 dòng `isinstance` |
| **D-04.2** Hỏi `/health` trước khi dịch prompt | (a) sửa `DieuPhoi.chay` gọi `dang_ban()` trước ① · (b) app hỏi `cong.health()` trước `chay` · (c) không làm, ghi nợ | **(b)** | (a) là `platform_core/image_gen/` — ngoài ranh giới tệp của phase; (b) đủ nhỏ, dùng đúng `cong_render.health()` có sẵn, tolerant với bộ điều phối giả (`getattr(dp,"cong",None)`); cổng **không trả lời** thì không coi là bận để cổng chết vẫn hỏng có đếm lượt | Có |
| **D-04.3** Khai `admission_resource/_slots` và `gpu_vram_mb` cho `anhnoibo`? | (a) khai `admission_resource="ltt_render", admission_slots=1` · (b) khai thêm `gpu_vram_mb` · (c) **không khai**, ghi khuyến nghị | **(c)** | `gpu_vram_mb` **sai về bản chất**: nó giữ GPU **máy A** (`_giu_gpu`) trong khi app chỉ gọi HTTP sang máy B — khai là giữ card máy A vô ích. `admission_resource` 1 suất: hợp tiền lệ `llm_remote`/`vieneu_gpu` và Q114, **nhưng** (i) tranh chấp thật là với hai hộ khác trên máy B mà admission của ta không thấy (D-037) — cổng render đã là hàng rào; (ii) khai tên tài nguyên mới chạm `enforce_job_admission`/cap theo tài nguyên của Public API (`limits.py`) mà phase này không được sửa/đo; (iii) chi phí của việc không khai sau F2 chỉ là một GET LAN + một vòng 20 s. Điều kiện của prompt: *"chỉ làm nếu rõ ràng thiếu VÀ không xung đột hợp đồng cascade"* — (i)+(ii) là xung đột đủ để dừng. **Khuyến nghị**: Phase 12 (đồng thời) đo hai job ảnh cùng lúc trên máy B rảnh; nếu 429 xuất hiện đều thì thêm **một dòng** `admission_resource="ltt_render", admission_slots=1` vào `ToolSpec` (không đụng `platform_core`), kèm test ở `test_313` cho tên tài nguyên mới | Có |
| **D-04.4** Lỗi của `chuan_hoa` ⇒ `LoiNguoiGoi` | (a) cho cả `LoiTaoAnh` kế thừa `LoiNguoiGoi` · (b) lớp con `LoiYeuCauAnh(LoiTaoAnh, LoiNguoiGoi)` chỉ cho lỗi yêu cầu | **(b)** | (a) biến "mất liên lạc máy B", "kho không cấp vé", "chưa cấu hình" thành không-thử-lại — đúng hồi quy `LoiHaTang` của app tiếng 31/08. (b) giữ mọi `except LoiTaoAnh` cũ (7 test `test_253` xanh nguyên) | Có |
| **D-04.5** ETA vào `retry_after_s`; không biết ⇒ mặc định 20 s | (a) `max(eta, 60)` · (b) truyền thẳng `eta_s`, rỗng ⇒ mặc định nền tảng | **(b)** | không bịa ngưỡng chưa đo (ghi nhớ "mượn ngưỡng thì phải đo lại"); ETA của cổng đã theo D-012 "không lạc quan"; 20 s là hằng nền tảng đã có | Có |

## Changes

- `platform_core/jobs.py:86` — **mới** `class DangBan(Exception)` (`ly_do`, `retry_after_s`), docstring không nêu tên app (§8.4).
- `platform_core/job_runner.py:588` — `_provider_failure_kind`: `isinstance(exc, (jobq.DangBan, BanError))` ⇒ `("resource_wait", _cho_lai_s(exc))`; `:600` **mới** `_cho_lai_s` (sàn 1, rỗng ⇒ 20 — cùng số cũ). Không đổi nhánh nào khác.
- `apps/anhnoibo/features.py:52` — **mới** `LoiYeuCauAnh(LoiTaoAnh, LoiNguoiGoi)`; 7 chỗ `raise` trong `_kiem_chu_so_huu`/`chuan_hoa` dùng nó. `LoiTaoAnh` giữ cho hạ tầng.
- `apps/anhnoibo/jobs.py:38` `_dang_ban(eta_s)` (câu chữ cũ, ETA theo phút nếu biết); `:52` `_xep_lai_neu_may_ban(cong)`; `handle`: hỏi bận trước `chay` (`:130`), `except BanError ⇒ raise DangBan` (`:143`) thay vì `LoiTaoAnh`.
- **Không** sửa: `apps/anhnoibo/manifest.py`, `gia.py`, `platform_core/image_gen/*`, `registry.py`, `streaming.py`, `runtime_noi_bo/*`.
- Test mới: `tests/test_606_anh_noi_bo_tien_theo_anh_that.py` (5), `tests/test_607_anh_noi_bo_ban_khong_phai_hong.py` (17), `tests/test_608_anh_noi_bo_tham_chieu_va_nop_trung.py` (10).

## Tests

| Command / journey | Result |
|---|---|
| `python -m pytest tests/test_606_*.py tests/test_607_*.py tests/test_608_*.py -q -n 0 -p no:cacheprovider` | **32 passed** (trong lượt 606–612: **58 passed** in 12.62s) |
| Hành trình F4: `bao_gia(image.ltt,count=4)` → `nop_job` (giữ 12) → `_chay_mot_job` → `DieuPhoi` giả trả 2 khoá → `credit_cost=6`, số dư `100−6`, `so_anh_xin=4/so_anh_that=2` | PASS |
| Hành trình F1: `DieuPhoi.chay` ném `BanError(eta_s=150)` → job `queued`, `attempts=0`, `provider_state=rejected`, sự kiện `resource_wait` (không `retry_scheduled`/`failed`/`credit_settled`), `so_da_giu` nguyên, chưa tới `next_run_at` thì worker không nhặt; bận **5 lần > max_attempts 3** vẫn `queued/attempts=0`; hết bận ⇒ `done`, thu đúng | PASS |
| Hành trình F2: `health.busy=True, eta_s=300` ⇒ `DangBan` "còn khoảng 5 phút", `chay` **không** được gọi; `health` ném `CongRenderError` ⇒ đi tiếp và xong; không có `cong` ⇒ bỏ qua | PASS |
| Hành trình F3: `nop_job(mode=edit, image_key=anhnoibo/<người khác>/…)` (bao_gia không kiểm sở hữu — đúng vai) → worker: `error` sau **1** lượt, `_dieu_phoi` không được dựng, `provider_state=""`, hoàn đủ 100, người kia không bị chạm | PASS |
| Hồi quy tệp ghim cùng module: `test_253 test_276 test_313 test_501 test_353 test_340 test_338 test_302` `-n 0` | **185 passed** |
| Hồi quy theo `tools/thanh_phan.py --test core:job` (36 tệp) + `app:anhnoibo` (3) + `app:ltt_voice` (30) + `test_256/60/308/147` + 606–612, `-n 0` | xem dòng cuối mục này |
| `python tools/check_silent_except.py` | `Nuot loi lang le: 62 \| moc: 62 — PASS` |
| `python tools/check_i18n.py` | `774 chuoi chua boc (moc 774) — khong tang` |
| `python tools/lint_app_contract.py` | `Apps quet: 16 \| ERROR: 0 \| WARN: 0 — PASS` |
| Hồi quy đầy đủ theo thành phần | **2 failed, 1184 passed, 7 skipped** in 463 s (`-n 0`, 74 tệp). Hai tệp đỏ **không thuộc phase này**: `test_211::test_every_table_has_a_retention_class` (bảng `chatltt_conversation/_execution/_message` chưa vào `governance.STORES`) và `test_212::test_the_document_classifies_every_app` (`undecided: ['chatltt']`) — cả hai do phiên Phase 07 (`apps/chatltt/`, migration `20260903_1000_chatltt_cay_hoi_thoai.py`) đang mở trên cùng cây; đã báo cho phiên điều phối, không sửa ở đây (ngoài ranh giới tệp). Mọi tệp `core:job`/`app:anhnoibo`/`app:ltt_voice`/`test_256/60/308/147` xanh |

## Failures found and repaired
- Lượt đầu `test_612` (phase 05) chọn số liệu làm giữ = thu = 2 credit nên "hoàn phần dư" không đo được gì — đổi thời lượng giả 6 s → 3 s (giữ 2, thu 1). Cùng bài học Phase 02 ("số liệu test nhỏ làm giữ = thu").
- `JobEvent.id` là UUID chuỗi — sắp theo `sequence`, không theo `id` (sửa trong `test_607` trước khi chạy).
- Không có test cũ nào đỏ vì bản sửa: `test_253` (7 `pytest.raises(LoiTaoAnh)`) xanh nhờ D-04.4(b); `test_276` (`_DP` không có `cong`) xanh nhờ `getattr(dp,"cong",None)`.

## External unknown/blocker
- **LIVE bị chặn ở phiên này** (không được chạm máy B/GPU): *time-to-start* (từ `execution_started` tới `provider_dispatched`/`gui` 202), *render total* (t2i ~58 s / tham chiếu ~190 s ở 30 bước theo `dieu_phoi.py:38` — số cũ, cần đo lại), tỉ lệ 429 khi có video, ETA từ `/health` có khớp thời gian chờ thật không (D-012 trung vị lịch sử). Công cụ có sẵn để đo khi máy rảnh: `tools/nghiem_thu_anh_e2e.py chuan_bi|chay|don` (đi từ ngoài vào qua Cloudflare, tài khoản riêng, khoá chỉ `image.ltt`, tiêu credit thật có chủ đích — *đã có*), đọc `job_events` (`execution_started`, `resource_wait.delay_seconds`, `execution_completed.duration_ms`) để suy time-to-start/render total; `render_gateway/diagnostics` cho phía máy B.
- Chưa đo: có nên khai `admission_resource` cho ảnh (D-04.3) — cần lượt đo hai job đồng thời trên máy B rảnh (Phase 12).

## Verdict
**PASS** — 32/32 test deterministic của phase xanh; bận ⇒ `resource_wait` (không tiêu lượt, không chạm tiền) **đã chứng minh trên worker thật** (`_chay_mot_job`), xin 4 nhận 2 ⇒ thu 2, ref của người khác ⇒ hỏng ngay không chạm máy B, nộp trùng ⇒ một job; không sửa giá/model; ba bánh cóc không tăng. LIVE = chặn ngoài, không ảnh hưởng điều kiện PASS của H43.4.

## Next
Autocontinue to phase: **05** (cùng phiên — xem `05_tieng_noi_bo.md`); giao Phase 06: hook sức khoẻ cho `danh_muc.san_sang` có thể đọc `cong_render.dang_ban()`; giao Phase 09: hiển thị `resource_wait.delay_seconds` (= ETA) trong khối ảnh; giao Phase 12: đo đồng thời để chốt D-04.3.
