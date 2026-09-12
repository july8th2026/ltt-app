# LTT LLM Dual-Model — DECISION LOG

> Mỗi quyết định hỏi MỘT lần; chốt rồi mới sang câu sau. Đã LOCKED thì Claude không tự đổi — muốn đổi
> phải phát hành `DECISION REOPEN REQUEST — Dxx` (bằng chứng mới, lý do, tác động, chi phí di trú) và chờ
> chủ dự án duyệt.
> Quyết định **cũ** của Multi-Job nằm ở `docs/multijob/DECISION_LOG.md` (nhánh
> `claude/ltt-llm-multijob-audit-43efd3`) — **không chép lại**; phân loại của chúng ở
> `01_MULTI_JOB_INHERITANCE.md`. Đổi một quyết định cũ = REOPEN ghi ở đây.
> Bằng chứng: `00`–`06` trong thư mục này.

## Trạng thái
- Gate R0–R5: XONG 2026-09-11.
- Brainstorming: đã invoke (đường **Architectural**).
- Đã khoá: D01 B · D02 C · D03 (đầy đủ, dự phòng C) · D04 B · D05 A · D06 B · D07 A · D08 A-rút-gọn. **DECISION LOCK Spec 1.** Spec 1 đã viết:
  `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` — **DUYỆT 2026-09-11** (chủ dự án: *"thực hiện
  triển khai theo quy trình bạn đã xây dựng, commit tài liệu tránh thất lạc"*; kèm cấp quyền điều khiển máy B qua
  Nexus/OpenSSH). Tiếp theo: implementation plan → chủ dự án duyệt plan → triển khai.
- Kênh máy B: **OpenSSH là kênh chính** (`ssh -i %USERPROFILE%\.ssh\nexus_b lengo@192.168.2.66`; đo 2026-09-11: sshd
  `Running/Automatic`, đăng nhập 0,37–0,47 s) + **Nexus** cho LocalSystem/Scheduled Task/API GPU và làm đường sửa khi
  SSH hỏng. ⚠️ Đính chính: bản đầu dòng này ghi "SSH DISABLED" theo `Ket_noi.md` sinh 30/08 mà không đo — sai; chủ dự
  án chỉ ra. `Ket_noi.md` đã được sinh lại (bộ sinh nay thử đăng nhập thật).

## Ý định chủ dự án đã khoá (không hỏi lại)

| ID | Nội dung | Nguồn |
|---|---|---|
| L-1 | Chỉ hai model: **LTT-3.8** = Qwen3.8-27B trên RTX 3090; **LTT-3.5** = Qwen3.5-9B trên RTX 5060 Ti | prompt chương trình |
| L-2 | Khách/API **chọn** model; không auto-router; **không** âm thầm đổi 3.8 → 3.5 | prompt |
| L-3 | Đích nghiên cứu/đo C4 mỗi model; C8 **không** phải lời hứa 8 lượt ngữ cảnh dài | prompt |
| L-4 | Admission tính cả slot **và** ngân sách ngữ cảnh/KV | prompt |
| L-5 | 262.144 là **đích thử** của LTT-3.8, không phải cam kết production khi chưa có bằng chứng | prompt |
| L-6 | Khách không còn phải chọn text vs vision: một model công khai LTT-3.8 | prompt |
| L-7 | Hai GPU là hai pool độc lập, không gộp 24+16 | prompt |
| L-8 | Danh tính GPU theo UUID + PCI Bus ID, không theo chỉ số | prompt |
| L-9 | Không bao giờ giết lượt đang chạy để đổi residency — drain trước | prompt |
| L-10 | 5060 Ti vừa lắp; **chưa hạng mục nào triển khai** — trạng thái máy B hiện tại là điểm xuất phát | chủ dự án, chat 2026-09-11 |
| L-11 | **Model ảnh vẫn dùng RTX 3090** ⇒ 3090 = LTT-3.8 + model ảnh (chia thời gian); 5060 Ti = LTT-3.5 + màn hình Windows | chủ dự án, chat 2026-09-11 |

| L-12 | **3090 chỉ dành cho model AI** (LTT-3.8 + model ảnh). Mọi VRAM nền (ngữ cảnh đồ hoạ desktop: dwm, explorer, SearchHost, M365Copilot, LGHUB… — `00` §3) và tác vụ không liên quan chuyển hết sang 5060 Ti | chủ dự án, chat 2026-09-11 (trả lời D03) |
| L-13 | **3090 chỉ dùng cho model AI.** LTT-3.8 lấy **trần ngữ cảnh tối đa**: nếu 262.144 vừa trong 24 GB thì **không hạ** số token để đổi lấy biên. Tối ưu theo hướng nhiều token nhất có thể mà vẫn không vượt trần card | chủ dự án, chat 2026-09-11 (sau khi dọn desktop) |

⚠️ L-11 thay thế giả định "3090 chuyên dụng cho LTT-3.8 / ComfyUI chuyển sang 5060" của prompt chương trình.
Hệ quả phải mang vào thiết kế: LTT-3.8 **không** thể "hot liên tục" khi có job ảnh (HiDream đỉnh 18.450 MB +
Qwen thường trú ≥ 19.237 MB > 24.576 MB — `docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md` §1); đích 262.144 phải
tính cả chi phí nạp lại.

## Đã giải bằng kỹ thuật — không hỏi (`TECHNICALLY RESOLVED — NO USER QUESTION`)

| ID | Nội dung | Căn cứ |
|---|---|---|
| TD-D1 | Nền tích hợp = trunk **`admin-mvp-v3`**; Multi-Job được rebase lên đó (đánh số lại test 950–956, nối migration vào head trunk) | `docs/16_CAP_NHAT_VA_DEPLOY.md` ("Nhánh trunk `admin-mvp-v3`"); `00` §2 |
| TD-D2 | Hai model cùng nạp bằng llama-swap v250 `groups` `swap:false` + `env: CUDA_VISIBLE_DEVICES=<UUID>` mỗi model + `hooks.on_startup.preload` | `05` §1 (llama-swap) |
| TD-D3 | Admission theo ngân sách KV ở tầng LTT vẫn **bắt buộc** cho mỗi pool — b10883 và upstream mới nhất vẫn giết mọi slot khi tràn pool, không có PR sửa | `05` §1; `server-context.cpp:3688-3724` @b10883 |
| TD-D4 | Tái dùng lõi Multi-Job T4/T5 (`luat_nhan.xet()` thuần theo `ThamSo`, `xet_va_giu` khoá theo resource) cho **hai** resource độc lập — không viết lại | `01` §2 |
| TD-D5 | Drain do LTT làm: ngừng nhận → chờ in-flight = 0 → mới gỡ model. Không bao giờ gọi unload thủ công llama-swap khi còn lượt chạy (nó không drain) | `05` §1; `fifo.go:222-270` |
| TD-D6 | LTT-3.5 khởi đầu **không** `draft-mtp` (−32 % trên Blackwell CUDA #26750; lợi ích MTP ≈ 0 ở N=4). LTT-3.8 chỉ bật MTP ở `-np 4` sau phép kiểm đúng/sai từng slot (#27572: trả lời rỗng, một xác nhận đúng cấu hình ta) | `05` §1 |
| TD-D7 | Tệp đầu vào: community-first (Docling / markitdown đã có), không tự viết parser | `05` §3 |
| TD-D8 | Kho ấm = standby list Windows (224 GB) + `--cache-ram` cho prompt; `--mlock` vô ích với nạp lại. Chỉ tuyên bố tăng tốc khi có số đo lạnh/ấm | `05` §4 |
| TD-D9 | Ghim ComfyUI và cả hai hồ sơ llama bằng UUID; mọi phép đo VRAM/util trên máy B lọc theo UUID | `03` §1 |
| TD-D10 | Trọng tài residency 3090 (D01 B) có **một** quyền quyết nghiệp vụ: admission plane máy A — nơi duy nhất thấy cùng lúc lease LLM, phòng chờ và hàng job ảnh. Gateway máy B chỉ thực thi đổi residency + chốt fail-closed. ⇒ job ảnh (`apps/anhnoibo`, hôm nay **không** khai `admission_resource`) phải đi qua sổ lease | prompt §5.1 "ONE BUSINESS QUEUE AUTHORITY"; `apps/*/manifest.py` |
| TD-D11 | Hai thang ưu tiên xếp **tầng**, không cạnh tranh: D-03 Multi-Job (tương tác > nền) quyết **lượt tương tác vs job** ở cửa admission; Scheduler V1 (`priority_class internal > external`) quyết **thứ tự giữa các job** trong hàng `jobs`. Không chỗ nào hai thang cùng xếp một cặp | `docs/SCHEDULER_V1/02_SCHEDULER_CONTRACT.md` (trunk); `01` §1 |

## Quyết định cần chủ dự án

### D01 — Chính sách chia RTX 3090 giữa LTT-3.8 và model ảnh — **LOCKED 2026-09-11**
- **Options:** A LLM ưu tiên tuyệt đối (ảnh chờ không trần) · **B luân phiên có trần** · C ảnh ưu tiên (drain, không giết).
- **Selected: B.** LTT-3.8 nóng mặc định. Có job ảnh xếp hàng ⇒ ngừng nhận lượt LLM mới cho 3090, **drain**
  lượt đang chạy (lượt stream mới vào phòng chờ D-06 kèm nhịp tim), vẽ **theo lô** trong một cửa sổ có trần,
  rồi nạp LTT-3.8 lại. Mỗi bên có **thời gian chờ tối đa** cấu hình được.
- **Tham số khởi đầu (cấu hình, chốt lại bằng lưu lượng đo):** ảnh chờ tối đa ~5 phút · cửa sổ ảnh tối đa
  ~4 ảnh hoặc ~8 phút.
- **Evidence:** HiDream đỉnh 18.450 + Qwen ≥ 19.237 MB > 24.576 MB; nạp lại ảnh +0,8 s vs LTT-3.8 18–33,9 s;
  render hôm nay `GET /unload` giết lượt LLM đang chạy; hai trọng tài không có khoá chung (`03` §2, `05` §1).
- **Consequences:** (1) thay HAI trọng tài hiện tại (`render_gateway/nhuong_card.py` đuổi Qwen,
  `llm_gateway/don_dep.py` `/free` ComfyUI) bằng **MỘT** trọng tài residency 3090; (2) trong cửa sổ ảnh, cửa
  đồng bộ LLM trả 429 + Retry-After (không giữ được > ~100 s qua Cloudflare); (3) chi phí nạp lại LTT-3.8
  thành một đầu vào của đích 262.144 (pool lớn ⇒ nạp lâu hơn ⇒ đo); (4) lưu lượng job ảnh phải được đo để chốt
  tham số; (5) không lượt nào bị giết để đổi residency (L-9).
- **Affected:** `render_gateway/{nhuong_card,busy,api}.py`, `llm_gateway/{don_dep,trong_tai,api}.py`,
  `llama-swap.yaml`, admission plane máy A (sổ lease + phòng chờ), `apps/anhnoibo` (đường job ảnh),
  quan sát (trạng thái residency 3090).

### D02 — Tên model công khai + bí danh cũ — **LOCKED 2026-09-11**
- **Options:** A ID mới + bí danh cũ ẩn vĩnh viễn (khuyến nghị) · B ID mới + bí danh cũ có hạn ngừng · **C cắt ngay**.
- **Selected: C.** ID API chấp nhận **đúng hai giá trị** `ltt-3.8` và `ltt-3.5`; tên hiển thị "LTT-3.8", "LTT-3.5".
  `ltt_llm`, `ltt_llm_vision` (và mọi biến thể) ⇒ `model_not_found`. Không bảng bí danh ẩn.
- **Evidence:** bí danh cũ khai ở `apps/ltt_llm/manifest.py:202,235-262`, `features.py:41-46`,
  `public_api/examples.py:236,525`, `server/api/streaming.py:82`; mọi danh mục dẫn xuất từ manifest (`02` §1).
- **Consequences (chủ dự án chấp nhận khi chọn C):** (1) mọi cấu hình Codex/Claude Code của khách đang dùng
  `ltt_llm` gãy khi cắt — cần thông báo khách **trước** ngày cắt; (2) **dữ liệu NỘI BỘ không phải "client"**
  — job đang xếp hàng mang `model=ltt_llm`, lựa chọn model đã lưu của ChatLTT/agent, mẫu/CLI, route
  `ltt-llm-claude-compat`, trang `/developers` và `/gia-api` phải **di trú trong cùng lần deploy** (không
  phải bí danh — là sửa dữ liệu/mã); (3) lịch sử usage/credit giữ nguyên tên cũ (dữ liệu quá khứ, không viết
  lại); (4) cắt tên xảy ra ở **lần bật cuối** (cùng lúc bật Dual-model), không sớm hơn — để đường lùi trước
  nghiệm thu vẫn là đường cũ nguyên vẹn; (5) phép kiểm tĩnh nghiệm thu A: `ltt_llm`/`ltt_llm_vision` không
  còn là tên chấp nhận được ở bất kỳ cửa nào.
- **Affected:** `apps/ltt_llm/{manifest,features,executor,ngan_sach}.py`, `platform_core/providers.py`,
  `platform_core/public_api/{examples,catalog}.py`, `server/api/streaming.py`, ChatLTT (`frontend/chatltt`,
  `runtime_noi_bo/danh_muc.py`), tài liệu developer + giá, test ghim tên cũ.

### D03 — Cấu hình LTT-3.8 trên 3090 — **LOCKED 2026-09-11**
- **Options đưa ra:** A bỏ MTP trước (khuyến nghị) · B giữ MTP, co ngữ cảnh · C giữ 262K + MTP, bớt slot.
- **Selected (lời chủ dự án):** *"khi ta đã giải phóng vram nền tôi tin đủ vram để triển khai full không cần
  hy sinh gì, lựa chọn phương án C để nghiên cứu … 3090 chỉ sử dụng cho model AI; vram nền hay tác vụ không
  liên quan chuyển hết cho 5060"*. Diễn giải khoá:
  1. **Đích = cấu hình ĐẦY ĐỦ, không hy sinh:** `-c 262144` + mmproj (hồ sơ gộp text+vision) + `-np 4 -kvu` +
     `draft-mtp`, trên 3090 đã dọn VRAM nền (L-12).
  2. **Hướng nghiên cứu dự phòng = C:** nếu phép đo chứng minh cấu hình đầy đủ không vừa, hướng dự phòng là
     **giữ 262K + MTP + ảnh, bớt slot** (3 rồi 2) — không bỏ MTP, không co ngữ cảnh.
  3. Rơi xuống dự phòng **không âm thầm**: báo chủ dự án kèm số đo.
- **Evidence:** 3090 hôm nay dùng 182 MiB (màn hình đã sang 5060 Ti; trước đó desktop 1.515–1.612 MiB);
  M-2 (b10689, desktop còn trên 3090): hồ sơ gộp 204.800 đỉnh 24.202 MiB; cộng đồng: 262K + MTP không nạp
  được [M], 262K không MTP 22,2 GB [C] (`05` §2).
- **Giữ nguyên (không phải hy sinh, là phép kiểm):** cổng đúng/sai MTP từng slot ở `-np 4` (#27572 — trả lời
  rỗng/nhận nháp 0; một xác nhận đúng cấu hình Windows CUDA + Qwen3.8-27B MTP + mmproj). Trượt cổng ⇒
  `DECISION REOPEN REQUEST — D03` kèm bằng chứng; Claude không tự đổi cấu hình.
- **Consequences:** (1) việc vận hành L-12 (đưa ngữ cảnh đồ hoạ desktop khỏi 3090) là **điều kiện tiên quyết**
  của phép đo 262K — làm và đo trước; (2) đo VRAM phải kèm bộ đếm Windows `GPU Process Memory … Shared Usage`
  (nvidia-smi không thấy WDDM tràn); (3) thời gian nạp lại hồ sơ 262K là đầu vào của D01 (cửa sổ ảnh);
  (4) tiếp nhận TD-4/D-08 A của Multi-Job theo số mới — REOPEN số, giữ hướng.
- **Affected:** `llm_gateway/deploy/llama-swap.yaml`, `apps/ltt_llm/ngan_sach.py` (`CUA_SO_MODEL`, trần dẫn
  xuất), `test_334`, runbook máy B (dọn VRAM nền), khuôn đo m1/m2.

### D04 — REOPEN TD-7 (Multi-Job): cửa đồng bộ khi hết chỗ — **LOCKED 2026-09-11**
- **Bối cảnh REOPEN:** TD-7 khoá "chờ trước header ≤60 s rồi 429"; WIP Task 9 code "không chờ" mà chưa qua
  REOPEN. Lý do WIP nêu **đúng** (`idempotency.begin` → `pg_advisory_xact_lock`, `idempotency.py:77`;
  `chat.py:188` acquire nằm trước commit `:226`).
- **Options:** A không chờ (công nhận WIP) · **B chờ ≤60 s SAU commit idempotency** · C chờ ≤15 s tại chỗ (giữ khoá).
- **Selected: B.** Trình tự cửa đồng bộ: kiểm tham số/đầu vào (413/402 như cũ) → `idempotency.begin` → commit
  bản ghi "đang xử lý" (**nhả khoá**) → chờ trong phòng chờ (T6) tối đa `min(60 s, ngân sách thời gian còn lại
  của cửa)` → được nhận ⇒ **giữ tiền** ⇒ gọi model ⇒ quyết toán; hết giờ ⇒ 429 + `Retry-After`, đóng bản ghi
  idempotency, **0 khoản giữ tiền**.
- **Consequences:** (1) TD-7 giữ ý (chờ ≤60 s) nhưng **dời điểm chờ ra sau commit** — WIP T9 phần `chat.py` /
  `_mot_cuc` phải sửa lại; (2) bất biến mới cần test: INV-MJ-1 (đang chờ ⇒ không có dòng giữ tiền) áp cả cho
  cửa đồng bộ; hai request trùng khoá idempotency cùng chờ ⇒ chỉ một lượt chạy, lượt kia replay/409; hết giờ
  chờ ⇒ 0 khoản treo; (3) trong cửa sổ ảnh D01 (≫ 60 s) cửa đồng bộ LTT-3.8 trả 429 — `Retry-After` nên ước
  theo thời điểm cửa sổ đóng; (4) áp cho cả hai model.
- **Affected:** `server/api/chat.py`, `server/api/streaming.py` (`_mot_cuc`), `platform_core/public_api/idempotency.py`
  (trạng thái "đang xử lý" + đóng khi hết chờ), `platform_core/llm/phong_cho.py`, test cửa đồng bộ (đánh số mới).
- **ĐÃ HIỆN THỰC — Task 1.5 (2026-09-11).** Trình tự B chạy thật ở cả hai cửa đồng bộ
  (`chat_completions` và `_mot_cuc`): 413 → 402 (`du_so_du`, chỉ đọc) → `idempotency.begin` →
  `db.commit()` → `luong.cho_suat_dong_bo(han_s=luong.han_cho_dong_bo(...))` → giữ tiền → gọi →
  quyết toán. Hết giờ ⇒ 429 + `Retry-After` + `idempotency.mo_lai` (trạng thái mới
  `IDEMPOTENCY_FAILED`, thử lại được) + 0 bút toán. Bằng chứng:
  `tests/test_1208_cua_dong_bo_cho.py` (12 passed, 1 skipped) — trong đó
  `test_ban_ghi_idempotency_DA_COMMIT_khi_dang_cho` là **đối chứng cơ học** của chính D04: tiêm
  bản chờ-trước-commit ⇒ ĐỎ ("database is locked", bản ghi vô hình với phiên khác).
  Chi tiết: `.superpowers/sdd/2026-09-11-ltt-llm-dual-model/task-1.5-report.md`.

### D05 — Phạm vi Input Intelligence + cách chia chương trình — **LOCKED 2026-09-11**
- **Options:** **A hai spec, một nghiệm thu** · B một spec chung · C đợt này chỉ text + ảnh.
- **Selected: A.**
  - **Spec 1 — Runtime hai model:** D01–D04 + mọi TD; đầu vào của Spec 1 = text + nhiều ảnh cho **cả hai** model.
  - **Spec 2 — Input Intelligence MVP:** nâng đường tệp→chữ của ChatLTT (`apps/chatltt/services/trich_van_ban.py`,
    `chia_doan`/`tim_doan`) thành năng lực nền tảng; Docling cho PDF bố cục/bảng, XLSX, PPTX, OCR; markitdown giữ
    làm đường nhanh; đa tệp: ngữ cảnh trực tiếp dưới ngưỡng token, truy hồi trên ngưỡng; ảnh + tệp cùng lượt;
    ghi nguồn từng đoạn (tệp, trang, tiêu đề); cách ly người dùng. **Video/audio ngoài MVP.**
  - Thứ tự: Spec 1 (thiết kế → plan → triển khai + test mục tiêu) → Spec 2 (cùng chu trình) → **nghiệm thu tích
    hợp A–Q chạy MỘT lần** sau cả hai.
- **Consequences:** (1) spec viết ở phiên này là **Spec 1**; Spec 2 có brainstorming/spec/plan riêng; (2) nghiệm
  thu L (đa tệp) thuộc Spec 2 nhưng chạy trong đợt nghiệm thu chung; (3) nơi chạy Docling (máy A 10 lõi dùng chung
  vs máy B 48 luồng) quyết ở Spec 2; (4) video/audio: ghi vào "Remaining work", không làm.
- **Affected:** Spec 2 — `apps/chatltt/services/*`, năng lực mới trong `platform_core` (vị trí quyết ở Spec 2),
  `requirements.txt` (Docling), cửa đầu vào của hai model.

### D06 — Khung cấu hình LTT-3.5 trên 5060 Ti — **LOCKED 2026-09-11**
- **Options:** A 262K + Q4, chừa ≥3 GiB (khuyến nghị) · **B 262K + Q6_K, chừa ~2 GiB** · C 131K + Q4, chừa ~5,8 GiB.
- **Selected: B.** LTT-3.5 = Qwen3.5-9B **Q6_K** + mmproj (hồ sơ gộp text+vision), `-c 262144 -np 4 -kvu`,
  KV q8_0, **không** draft-mtp (TD-D6), ghim UUID 5060 Ti. Ước ~13,7 GiB ⇒ chừa ~2,2 GiB cho desktop + tác vụ nền
  (L-12). Hai model **cùng trần ngữ cảnh 262.144**.
- **Ứng viên tệp (chọn bằng benchmark trong lớp Q6_K):** `unsloth/Qwen3.5-9B-MTP-GGUF` `Q6_K` 7,685 GB (sha
  `8ae8fd04…`; đầu MTP không tốn VRAM khi tắt — tensor MTP chỉ nạp khi dùng, #26296 từ b10212) ·
  `lmstudio-community/Qwen3.5-9B-GGUF` `Q6_K` 7,359 GB (không đầu MTP). mmproj F16 0,918 GB. SHA256 kiểm khi tải.
- **Evidence:** KV Qwen3.5-9B chỉ 8 lớp attention ⇒ 262K q8_0 = 4,25 GiB [INFERRED]; desktop đo 1.515–1.612 MiB
  (`05` §2; `gateway.env` ghi chú).
- **Consequences:** (1) chỗ chừa mỏng ⇒ **chốt bắt buộc**: telemetry VRAM trống 5060 Ti theo UUID + bộ đếm
  `GPU Process Memory … Shared Usage` của llama-server (tràn WDDM không hiện ở nvidia-smi) + cảnh báo khi dưới
  ngưỡng; (2) phép đo phải chạy **khi desktop + tác vụ nền thật đang mở** (L-12), không trên card trống; (3) nếu đo
  cho thấy Q6_K + 262K không chừa được ~2 GiB ⇒ `DECISION REOPEN REQUEST — D06` kèm số đo, Claude không tự hạ
  quant/ngữ cảnh; (4) hai model cùng trần ⇒ `ngan_sach.py` dẫn xuất trần vào/ra theo model từ cùng công thức.
- **Affected:** `llama-swap.yaml` (hồ sơ LTT-3.5), `apps/ltt_llm/ngan_sach.py` (`CUA_SO_THEO_MODEL` thêm id nội
  bộ LTT-3.5), gateway (catalog + sổ theo model), runbook tải model, telemetry/cảnh báo.

### D07 — Nguyên tắc giá LTT-3.5 — **LOCKED 2026-09-11**
- **Options:** **A rẻ hơn OpenRouter ~50 % (như 3.8)** · B ngang OpenRouter + sàn 3× chi phí đo (khuyến nghị) ·
  C 1/4 giá LTT-3.8.
- **Selected: A.** Cùng luật định giá với LTT-3.8. Neo: OpenRouter `qwen/qwen3.5-9b` $0,10 / $0,15 mỗi 1M
  (lấy 2026-09-11) ⇒ ≈ 26 / 39 credit/1M ở tỉ giá của `gia_token.py` (1 credit = 100đ, 26.300đ/USD) ⇒ giá LTT-3.5
  khởi đầu ≈ **13 vào / 3 vào-cache / 20 ra** credit/1M (vào-cache theo tỉ lệ 1/5 như 3.8). Nhãn giá mới
  `ltt-3.5-<ngày chốt>`; LTT-3.8 giữ nguyên `ltt-vlm-2026-08-22`.
- **Rủi ro chủ dự án chấp nhận khi chọn A:** ước chi phí điện biên LTT-3.5 ~31 credit/1M ra ở C1 [INFERRED] > giá
  ra 20 ⇒ có thể **bán dưới giá vốn điện khi vắng khách**; lãi mỏng khi đông.
- **Consequences:** (1) benchmark **phải đo** công suất 5060 Ti (W) theo C1/C4 và ghi chi phí biên/1M token ra
  báo cáo cuối — để chủ dự án xem lại luật giá bằng số thật (không tự đổi; muốn đổi ⇒ REOPEN D07);
  (2) `gia_token.tinh()` nhận model ⇒ hai bảng giá, **một** module (giữ nguyên tắc "một chỗ, không hai");
  (3) trang `/gia-api` + tài liệu developer hiển thị giá theo model; (4) mọi đường tiền (giữ/quyết toán/hoàn)
  tính theo **model thật đã phục vụ** — không bao giờ tính giá 3.8 cho lượt 3.5 hay ngược lại.
- **Affected:** `platform_core/llm/gia_token.py`, `platform_core/llm/thanh_toan.py`, `apps/ltt_llm/features.py`
  (`credit_cost`), trang giá, test tiền (test_68, 292, 390…).

### D08 — Nhịp lên production — **LOCKED 2026-09-11**
- **Options đưa ra:** A một lần cắt sau A–Q có canary nội bộ (khuyến nghị) · B bật sau Spec 1 (mở lại D05) · C bật
  từng model.
- **Selected (lời chủ dự án):** *"lựa chọn phương án tối ưu nhất, quy trình xây dựng toàn bộ plan nhanh nhất, không có
  khách thật đang sử dụng hay cần sử dụng ngay, nên lựa chọn phương án tối ưu thay vì test đi test lại"*. Diễn giải
  khoá = **A rút gọn**:
  1. **Pha 0 an toàn** (ghim UUID 3090 cho LTT-3.8 + ComfyUI, dọn VRAM nền khỏi 3090 — L-12) làm sớm.
  2. Spec 1 → Spec 2 triển khai với **test mục tiêu** từng task; production dùng làm môi trường đo thật (chưa có
     khách) — deploy trung gian tự do theo memory `deploy-thoai-mai-chua-co-khach` (gate xanh + hỏi phiên khác vẫn giữ).
  3. **Bỏ** bước deploy-tối-sau-cờ và canary nội bộ riêng; **không** viết đường mã cờ song song "cho khách cũ".
  4. **Một** nghiệm thu tích hợp A–Q trên đường production → bật + cắt tên (D02) cùng lúc → theo dõi 24 h.
  5. Đường lùi (prompt §14.2) = **cơ học, không phải cờ**: `C:\LTTPlatform\app.previous` (máy A) +
     `H:\LTT_LLM\releases\auto-<ts>` + yaml trước (máy B) + `nang_llamacpp.ps1 -Ban <cũ>`; migration chỉ cộng thêm.
     Kiểm cơ học đường lùi là một mục của nghiệm thu.
- **Evidence:** log worker 28 ngày: 10.663 lượt nhặt `ltt_llm.chat`, 1.075 `anhnoibo.generate` (~38 ảnh/ngày), 0 lượt
  lớp Agent (memory `deploy-thoai-mai-chua-co-khach`); `deploy.ps1` chụp-trước-khi-đè; lùi engine đã diễn tập 18,9 s.
- **Consequences:** (1) bỏ yêu cầu "thông báo khách trước ngày cắt" ở D02 (chưa có khách chính thức); (2) vẫn giữ
  bốn chốt không phải chuyện khách: gate xanh · sổ sách tiền đúng · UAC · hỏi phiên khác trước deploy;
  (3) ~38 ảnh/ngày là đầu vào đầu tiên để chốt tham số cửa sổ ảnh D01.
- **Affected:** plan (thứ tự pha), runbook deploy A+B, mục nghiệm thu "rollback".

### D09 — Model cho việc LLM nội bộ của nền tảng/app — **LOCKED 2026-09-11** (phát hiện khi lập plan)
- **Bối cảnh:** trên trunk, bí danh `ltt_llm` là điểm nối nội bộ `platform_core/llm/canonical.py` (AI CLEAN REBUILD V2
  pha 05–07). Người gọi: `platform_core/image_gen/dich_llm.py` (dịch prompt ảnh, gọi **bên trong** job của
  `apps/{anhnoibo,taoanh,thumbnail}`), `apps/taovideo/translate`, `apps/autosubvideo/ai_workflows.py`,
  `apps/prompt_ai_ommi`, `platform_core/agent/planner.py`; mọi đường giành chung `llm_remote` qua
  `canonical.tai_nguyen_nha()`. D02 cắt bí danh ⇒ mỗi người gọi phải chọn tường minh. D01 B ⇒ trong cửa sổ ảnh LTT-3.8
  không nằm trên GPU ⇒ dịch prompt từ trong job ảnh mà trỏ 3.8 là **vòng chờ** (job ảnh chờ LLM, LLM chờ cửa sổ ảnh đóng).
- **Options:** A tất cả → 3.5 · B chỉ job ảnh → 3.5, còn lại 3.8 · **C mỗi app khai, mặc định 3.5**.
- **Selected: C.** Hợp đồng app thêm trường khai model cho việc LLM nội bộ của app (giá trị `ltt-3.8`|`ltt-3.5`,
  **mặc định `ltt-3.5`** cho mọi app lúc bật); `canonical` đọc khai báo đó thay cho `MODEL_MAC_DINH`. Phép kiểm máy chặn:
  đường gọi LLM từ trong job giữ `anh_3090` (dịch prompt ảnh) **không bao giờ** trỏ `ltt-3.8`.
- **Consequences:** (1) việc nội bộ không bị kẹt residency 3090; 3090 dành cho khách chọn LTT-3.8; (2) chất lượng dịch
  phụ đề/prompt AI trên 9B phải được chấm trong benchmark — nâng app nào lên 3.8 là một dòng khai, không cần REOPEN;
  (3) planner: model nhà của nó là 3.5; **không** có cascade Gemini (gỡ 08/09, `planner.py:18-20`) ⇒ hết chỗ là `PlannerError` — đính chính 11/09 khi làm Task 1.5; (4) giá: việc nội bộ đi
  theo giá model được khai.
- **Affected:** `platform_core/llm/canonical.py`, `platform_core/registry.py` (trường khai), manifest của
  `anhnoibo/taoanh/thumbnail/taovideo/autosubvideo/prompt_ai_ommi`, `platform_core/image_gen/dich_llm.py`,
  `platform_core/agent/planner.py`, test canonical (`test_1001`, `test_1002`).

## ✅ DECISION LOCK — Spec 1 (2026-09-11)
D01 B · D02 C · D03 đầy đủ/dự phòng C · D04 B · D05 A · D06 B · D07 A · D08 A-rút-gọn · D09 C · L-1…L-12 · TD-D1…TD-D11.
Không còn quyết định người dùng mở cho Spec 1. Tiếp theo: viết spec → chủ dự án duyệt.

---

## ✅ L-14 — Cấu hình engine LTT-3.8 (chủ dự án, 2026-09-12)

**Bối cảnh.** L-13 (11/09) nói: *"vram 3090 chỉ sử dụng cho AI model… cho qwen sử dụng
trần tối đa… nếu 262k đạt đủ GB với card không vượt trần 24gb thì không cần hạ số token
xuống."* Điều kiện *"nếu"* đã được đo ở cổng G1 (`10_BENCHMARK_P3.md`) và **không thoả**:
262.144 × 4 slot tràn ~400 MiB sang RAM chủ ngay cả khi bỏ mmproj khỏi GPU.

**Chủ dự án quyết** (hai lượt): giữ **mmproj trên GPU**, **tối đa 3 slot** (bỏ mục tiêu
C4), và **hạ ngữ cảnh xuống cho phù hợp**.

⚠️ Lượt quyết đầu chọn *262.144 + mmproj trên GPU* — hai thứ **không cùng vừa card**
(đo được ~25,2 GB). Đã báo lại kèm số; lượt thứ hai chốt "hạ token, giữ 3 slot".

**Chốt:** `-c 221184 -np 3`, mmproj trên GPU, `-ub` mặc định. VRAM 24.131 MiB,
`Shared` 568 (trong dải sàn ⇒ **không tràn**), biên **445 MiB**.
Đây là mốc cao nhất còn sạch ở `-ub` mặc định; 229.376 đã vượt sàn ~140 MiB.

**Consequences:**
1. **C4 → C3 cho CẢ HAI model.** `SO_SLOT` = 3 (Task 2.6), `-np 3` trong
   `llama-swap.yaml` (Task 3.3). Mọi chỗ spec/plan viết "C4" đọc lại là **C3**.

   ⚠️ Với LTT-3.5 đây là lựa chọn, **không** phải giới hạn phần cứng: cổng G3 (12/09)
   đo được 262.144 × **4** slot vừa thoải mái trên 5060 Ti — VRAM 13.423 MiB, biên
   **2.888 MiB**, không tràn. Chủ dự án chọn 3 **cho nhất quán hai card** (12/09:
   *"cứ để 3 cho nhất quán 2 card"*). Ghi lại vì đây là chỗ dễ hiểu nhầm về sau:
   muốn nâng 3.5 lên 4 slot thì **chỉ cần đổi một con số**, không phải mua thêm gì —
   `admission_theo_model` khai số suất theo từng model nên hai card không buộc bằng nhau.
2. Ngân sách KV `POOL_38` = 221.184 (thay 204.800). Trần vào public là số **dẫn xuất**
   (cửa sổ − token ra tối đa − lề ước), không phải con số chọn tay — `ngan_sach.py` tự tính.
3. **Ràng buộc cứng cho P5:** biên 445 MiB là biên lúc ComfyUI chưa nạp ngữ cảnh CUDA.
   ComfyUI ấm giữ 223,5 MiB và `/free` **không** nhả ⇒ trọng tài residency (Task 5.4)
   phải **dừng hẳn dịch vụ LTTComfyUI** trong cửa sổ LLM, không chỉ gọi `/free`.
4. `qwen38-vision` biến mất: một hồ sơ text+vision duy nhất ⇒ hết nguồn `ConnectionReset`
   do llama-swap đổi hồ sơ giữa chừng.
5. **Còn mở, không chặn:** `-ub 256` cho thêm 16.384 token với biên tương đương, đổi lại
   prefill chậm hơn — chưa đo. Đưa vào G4; đổi chác chưa có giá thì chưa chốt.

---

## ✅ L-15 — Bộ cờ chống "nghĩ mãi không dứt" cho model nhà (đo 2026-09-12)

**Vấn đề đo được.** LTT-3.5 trả `content` **rỗng 6/6 lượt** với đề tiếng Việt, mỗi lượt
đốt đúng `max_tokens` — trên **cả hai** ứng viên Q6_K, tất định. Tiếng Anh cùng lúc 3/3 đạt.
Không phải "model không biết tiếng Việt": lượt thành công trả lời đúng.

**Nguyên nhân** (tài liệu model + cộng đồng, `10_BENCHMARK_P3.md` §G3c): Qwen3.5 ở chế độ
thinking có lỗi *truncated thinking* đã đo công khai (17,4 % đầu ra không phát `</think>`,
84 % số đó lặp > 30 %); `</think>` chỉ là một token và lượng tử hoá làm tụt xác suất của nó;
và **Qwen3.5 luôn nghĩ bằng tiếng Anh** nên đề tiếng Việt bắt nó suy luận bắc cầu.
Cộng thêm tham số lấy mẫu mặc định của `llama-server` lệch khuyến nghị Qwen ở bốn chỗ —
nặng nhất là `presence-penalty 0` (chính là phanh chống lặp).

**Chốt — bộ cờ cho mọi hồ sơ model nhà:**

```
--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5 --reasoning-budget 512
```

**Bằng chứng:** bộ `tools/danh_gia_llm.py` đầy đủ, cùng tệp GGUF, chỉ khác bộ cờ:
**27/36 (75 %) → 36/36 (100 %)**. Không nhóm nào tụt; ba nhóm vốn "mất một phần"
(lập trình · sửa lỗi · sinh dài) lên 100 %. Tiếng Việt 0 % → 100 %. Và nhanh hơn ~3 lần.

**Consequences:**
1. Tham số lấy mẫu đặt ở **server** (`llama-swap.yaml`), không gửi theo request: cache CUDA
   graph khoá theo bộ tham số, và `danh_gia_llm.py` cố ý không truyền chúng.
2. Tham số Qwen **một mình không đủ** (còn 3/6 rỗng) — phải có cả `--reasoning-budget`.
   Khớp ghi chép cũ: `reasoning_effort` dịch xác suất chứ không chặn.
3. **Task 3.3 phải áp cùng bộ cờ cho `qwen38-api` và chạy lại `danh_gia_llm` cho nó.**
   Ghi chép cũ đã đo 3.8 có cùng chế độ hỏng và bỏ ngỏ *"chất lượng của phanh cứng chưa đo"*;
   nay đã đo — nhưng **trên một model khác**, nên là bằng chứng mạnh, chưa phải kết luận.
4. `--reasoning-budget` là cờ **server-global**, không gửi được per-request — nên nó là một
   thuộc tính của hồ sơ, và mọi khách của hồ sơ đó chịu chung.
5. Chưa đo: `--chat-template-kwargs '{"enable_thinking":false}'` (lượt thử hỏng vì lỗi truyền
   tham số qua PowerShell, không phải vì cờ). Không cần cho bản vá này.

---

## ✅ L-16 — Sửa L-15: bỏ `presence-penalty`, giữ phần còn lại (đo 2026-09-12)

**L-15 sai một nửa.** Bộ cờ nó chốt đưa bộ đề lên 36/36, nhưng đo xen kẽ 5 khối cho thấy
nó lấy đi **11 % tốc độ giải mã** và đẩy **LTT-3.8 xuống dưới ngưỡng cổng nghiệm thu B**
(56,61 so với ngưỡng 60,0 — hai dải không chồng nhau, nên là hiệu ứng thật).

Gốc của sai: L-15 gộp **hai thứ khác hẳn nhau về cơ chế** vào một "bộ cờ" rồi đo cả gói.

### Sáu ứng viên, chấm cả bộ đề `--lan 5` (10 lượt tiếng Việt mỗi cái)

| | cấu hình | bộ đề | tiếng Việt | LTT-3.8 tok/s | cổng B |
|---|---|---:|---:|---:|---|
| — | không cờ gì | 45/60 | **0 %** | 63,60 | đạt |
| — | chỉ `--reasoning-budget 512` | 58/60 | 80 % | 65,18 | đạt |
| C | `--reasoning-budget 1024` | 59/60 | 90 % | *(chưa đo)* | — |
| A | budget 512 + tham số Qwen **đủ** | 59/60 | 100 % | **56,61** | **trượt** |
| **B** | **budget 512 + tham số Qwen bỏ `presence-penalty`** | **59/60** | **100 %** | **63,01** | **đạt** |
| E | `--reasoning off` (tắt suy nghĩ) | 48/60 | **10 %** | *(rất nhanh)* | — |

**Chốt: phương án B.**

```
--reasoning-budget 512 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0
```

LTT-3.5 ở cấu hình này: **76,21 tok/s** (dải 74,1–84,8).

### Bốn điều bảng này nói, và không cái nào đoán được trước khi đo

1. **`presence-penalty 1.5` là toàn bộ chi phí, và nó không mua gì.** Bỏ nó: tốc độ
   56,61 → 63,01 (**+11 %**), chất lượng **không đổi** (59/60, tiếng Việt 100 %). Hợp lý
   về cơ chế — nó là phanh chạy **mỗi bước giải mã**, còn `temp/top-p/top-k/min-p` gần
   như miễn phí.
2. **Phanh cứng một mình là chưa đủ, và kiểu hỏng của nó TỆ HƠN.** Chỉ `--reasoning-budget`
   thì 2/10 lượt tiếng Việt trả lời **sai** kèm khối nghĩ rò ra `content`
   (`'Độc lập\n</think>\n\n2/9'`, `'**2 tháng 10**'`) — chứ không phải rỗng. Một câu sai
   nhìn như thật thì khách **không phát hiện được**; một câu rỗng thì phát hiện ngay.
3. **Tắt suy nghĩ là hỏng, không phải đánh đổi.** E nhanh gấp ~20 lần (0,15 s/lượt) nhưng
   tiếng Việt còn **10 %** và sinh dài còn 40 %. Model **cần** khối nghĩ để xử tiếng Việt.
4. **Cả A, B, C đều 59/60 và mỗi cái mất một ô KHÁC nhau** (A mất `sua_loi`, B mất
   `json-01`, C mất `vi-01`) ⇒ ô lẻ đó là **nhiễu**, không phải khác biệt thật. Chỉ cột
   *tiếng Việt* mới tách được chúng, vì đó là chỗ lỗi thật sống.

### Consequences

1. `llama-swap.yaml` (Task 3.3) dùng bộ cờ B cho **cả hai** hồ sơ. `--reasoning-budget`
   là cờ **server-global** nên nó là thuộc tính của hồ sơ, mọi khách chịu chung.
2. Mốc tốc độ mới cho nghiệm thu: **LTT-3.8 63,01** · **LTT-3.5 76,21** (c1, trung vị 5 lượt).
3. ⚠️ Biên của 3.8 mỏng: trung vị 63,01 vượt ngưỡng 60,0 nhưng **2/5 lượt riêng lẻ rơi
   xuống 57,8 và 58,7**. Trung vị là thước của R18 nên nó ĐẠT, nhưng cổng nghiệm thu D
   (C3 thật) phải đo lại — đừng coi 5 % biên này là an toàn.
4. **Chưa đo, để ngỏ có chủ đích:** `--reasoning-budget-message` (chèn một lời kết tử tế
   kèm `</think>` trước chỗ cắt — PR #25961 nói để trống thì hệ thống chỉ ép mỗi thẻ đóng,
   tức cắt cụt trần trụi, và nghiên cứu nó dẫn nói chèn lời kết **tốt hơn hẳn**). B đã đạt
   100 % tiếng Việt nên không cần, nhưng nếu sau này muốn hạ budget xuống cho nhanh hơn
   thì đây là nút phải thử trước.
5. Đính chính một ghi chép sai của tôi: `--chat-template-kwargs '{"enable_thinking":false}'`
   trượt **không phải vì cờ hỏng** mà vì tôi dùng sai công cụ — llama.cpp có
   `-rea / --reasoning [on|off|auto]` đúng nghĩa, và nó nạp được (chính là phương án E).

---

## ✅ L-17 — `llama-swap.yaml` **không** deploy một mình: nó đi cùng Task 5.4 (2026-09-12)

Task 3.3 Step 2 ghi *"deploy máy B ngay sau Step 1"*. Đọc lại sau khi hồ sơ đã viết
xong: **deploy một mình thì mỗi job ảnh sẽ giết luôn LTT-3.5 trên card nó không hề
tranh.** Đây là quyết định hoãn một bước deploy, kèm cơ chế cụ thể.

### Cơ chế, không phải lo xa

Hộ dùng chung card khai đường nhường ở `render_gateway/nhuong_card.py:302`:

```
LTT_HO_DUNG_CARD=llm=http://127.0.0.1:8280/unload;video=
```

`8280` là cổng của **llama-swap**, và đường ấy **không mang tên model**. Một lệnh
không có tham số đối tượng thì không thể nhắm một trong hai model — nên nó nhả thứ
đang chạy, và từ nay "thứ đang chạy" là **hai** tiến trình trên **hai** card.

⚠️ Mức chắc chắn: *"`/unload` không mang tên model"* là **đo được** (chuỗi cấu hình
   ở trên, và dòng log thật `GET http://127.0.0.1:8280/unload 200` trong
   `00_CURRENT_BASELINE.md:85`). *"Nó nhả cả hai"* là **[INFERRED]** từ hình dạng
   URL — hôm nay không phân biệt được vì chỉ có một model để nhả. ⇒ Lần deploy phải
   **đo lại bằng `/running` sau một lượt `/unload`**, chứ không tin dòng này.

Trước hôm nay điều đó vô hại: hồ sơ cũ chỉ có một model, và model ấy ở đúng trên
3090 mà job ảnh đang xin. Từ hồ sơ hai model:

| | trước | sau khi deploy yaml một mình |
|---|---|---|
| job ảnh xin 3090 | `/unload` → nhả LTT-3.8 (đúng thứ cần nhả) | `/unload` → nhả **cả** LTT-3.8 **và** LTT-3.5 |
| LTT-3.5 (5060 Ti) | không liên quan | bị giết, dù card của nó không ai tranh |
| lượt LLM kế tiếp | nạp lại 15,23 s | nạp lại 15,23 s **và** 10,12 s (§G5) |

Lưu lượng thật 28 ngày: **1.075** job `anhnoibo.generate` (~38/ngày). Nên đây không
phải một khả năng lý thuyết — nó là ~38 lần mỗi ngày một model bị giết vô cớ, và
`unload` thủ công **không chờ** lượt đang chạy (`fifo.go:222-270`) nên lượt đang
sinh chữ trên 3.5 cũng chết theo.

### Vì sao KHÔNG sửa bằng cách hoãn `ttl: 0`/`preload`

Đó là phản xạ đầu của tôi và nó sai: `ttl: 0` chỉ **tắt đồng hồ nhả theo nhàn rỗi**.
Nó không phải thứ gây ra chuyện trên — `/unload` toàn cục mới là. Hạ `ttl` về 300 thì
job ảnh **vẫn** giết cả hai model, chỉ thêm việc hai model tự nhả lẫn nhau lúc rảnh.

### Chốt

1. ⛔ **Không** chạy Task 3.3 Step 2 (scp yaml + `Restart-Service LTTLlamaSwap`) cho
   tới khi **Task 5.4** thay `LTT_HO_DUNG_CARD` bằng lệnh residency **theo UUID/model**
   và gỡ hai trọng tài cũ. Hai bước ấy deploy **trong một lần**.
2. **R21 không bị vi phạm** — R21 nói *thứ tự trong một lần deploy* (yaml → gateway →
   máy A), không nói "yaml phải lên ngay hôm nay". Hôm nay **chưa có gì** được deploy,
   nên chưa có lệch nào giữa hai máy; khi deploy, thứ tự R21 vẫn giữ nguyên.
3. Kèm theo, ở lần deploy đó: **gỡ `qwen38-vision` khỏi `LTT_LLM_MODELS` của máy B**
   (báo cáo 3.3 §1). `catalog.py` còn khai `ModelSpec(ten="qwen38-vision")` cho tới
   Task 4.2; sau khi yaml lên, đó là một model gateway quảng cáo mà llama-swap **không
   còn khởi động được**, và lớp chắn duy nhất là `LTT_LLM_MODELS` fail-closed.
4. ⭐ Bài học về hình dạng, đáng ghi vì nó tổng quát: **một lệnh không mang tên đối
   tượng thì nó đúng chỉ khi trên hệ thống có đúng một đối tượng.** `/unload` không
   mang tên model; nó "đúng" suốt một pha vì tình cờ chỉ có một model. Thêm model thứ
   hai không làm nó báo lỗi — nó vẫn thành công, chỉ là làm nhiều hơn thứ ai cũng
   tưởng. Cùng khuôn với `_resource_of` (multijob 2.3) và `model_cho` (2.3 còn sót).
