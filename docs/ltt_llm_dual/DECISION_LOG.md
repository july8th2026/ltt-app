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
  (3) planner vẫn được rơi Gemini (việc nội bộ, F-06) nhưng model nhà đầu tiên của nó là 3.5; (4) giá: việc nội bộ đi
  theo giá model được khai.
- **Affected:** `platform_core/llm/canonical.py`, `platform_core/registry.py` (trường khai), manifest của
  `anhnoibo/taoanh/thumbnail/taovideo/autosubvideo/prompt_ai_ommi`, `platform_core/image_gen/dich_llm.py`,
  `platform_core/agent/planner.py`, test canonical (`test_1001`, `test_1002`).

## ✅ DECISION LOCK — Spec 1 (2026-09-11)
D01 B · D02 C · D03 đầy đủ/dự phòng C · D04 B · D05 A · D06 B · D07 A · D08 A-rút-gọn · D09 C · L-1…L-12 · TD-D1…TD-D11.
Không còn quyết định người dùng mở cho Spec 1. Tiếp theo: viết spec → chủ dự án duyệt.
