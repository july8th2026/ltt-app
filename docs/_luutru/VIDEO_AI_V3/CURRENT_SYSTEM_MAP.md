# BẢN ĐỒ HỆ THỐNG THẬT — trước khi làm LTT VIDEO AI V3

> Sản phẩm của **P00**. Mọi câu ở đây đọc từ **mã nguồn đang chạy**, không suy từ
> tên tệp. Chỗ nào là suy luận thì viết rõ "suy luận".
>
> Nếu một câu ở đây sai so với repo thì **repo đúng** — sửa tài liệu này.

Ngày lập: **2026-09-04**.
Cây: `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-api-http-guide-a3e123`
Nhánh: `claude/ltt-video-ai-v3-p00-3f5713` · commit gốc `d225a48`.

---

## 0. Tôi đang đứng ở đâu — và đây là câu hỏi có bẫy

```
Test-Path C:\LTTPlatform   →  ĐÚNG (thư mục tồn tại)
```

⚠️ **Máy này VỪA là máy phát triển VỪA là máy chủ production.** `CLAUDE.md` bảo
kiểm `C:\LTTPlatform` để biết "đang ở máy nào" — câu trả lời ở đây là **cả hai**.
Cây mã nguồn nằm ở `D:\`, bản đang phục vụ khách nằm ở `C:\LTTPlatform\app\`.

Bằng chứng production đang sống (hỏi lúc 2026-09-04 17:50, `tools/api_prod_canary.py`):

| Bề mặt | Mã | Ý nghĩa |
|---|---|---|
| `https://app.lttstudios.com/health/ready` | 200 | dịch vụ sống |
| `/` trang chủ | 200 | mở cho khách ẩn danh |
| `/vps` | 200 | đang bán |
| `/gia-api` | 200 | đang bán |
| `/developers` | 303 | đòi đăng nhập (đúng thiết kế) |

⇒ **Mọi việc của V3 phải làm trên cây `D:\...\worktrees\`, không bao giờ sửa
`C:\LTTPlatform\app\`.** Sửa trực tiếp trong `app\` là mất trắng, âm thầm, ở lần
cập nhật sau (`CLAUDE.md`).

### Nguy cơ đụng phiên khác — đã đo, không phải giả định

`git worktree list` lúc P00:

| Cây | Nhánh | Trạng thái |
|---|---|---|
| `D:\LTTSTUDIOSAPP` | `admin-mvp-v3` | cây chính |
| `...\auto-scan-video-v4-mvp-7173d9` | `phien/asv-v4` | có phiên đang chạy |
| `...\ltt-llm-api-http-guide-a3e123` | `claude/ltt-video-ai-v3-p00-3f5713` | **cây này**, sạch |
| `...\ltt-video-ai-v3-audit-e12665` | `claude/ltt-video-ai-v3-audit-e12665` | **bẩn**, không có phiên nào giữ |
| `D:\LTTSTUDIOSAPP_RELEASE_H42` | `h42-release-clean` | cây phát hành |

🔴 **Có SẴN hai nhánh mang tên `claude/ltt-video-ai-v3-audit-*`** (`-58d581` và
`-e12665`). Tức là đã có ít nhất một lượt khởi động V3 trước lượt này, và nó để
lại một cây bẩn không ai giữ. `ListAgents` lúc P00 cho thấy **ba phiên tương tác
đang sống**, không phiên nào đứng ở cây đó.

⇒ Việc đầu tiên của P01 là **chốt một cây duy nhất cho V3** và nói rõ hai nhánh
kia là rác hay là việc dở dang. Hai cây cùng làm V3 là đúng lớp lỗi mà
`AGENTS.md` §10 sinh ra để chặn.

### Dải số test dành cho cây này

```
Số test cao nhất đang dùng trên MỌI cây: 633   (dải 600–699 là của ChatLTT/H43)
⇒ DẢI CỦA V3: 700–799
```
(thuật toán: `tools/cay_rieng.py:_cap_dai_so_test`, đếm trên mọi worktree.)

---

## 1. Topology — ba máy, và **không được gọi lẫn**

```
                    NGƯỜI DÙNG / TRÌNH DUYỆT
                             │  https://app.lttstudios.com
                             ▼
                  ┌──────────────────────────────┐
                  │  A-CONTROL  (máy này)        │
                  │  C:\LTTPlatform, cổng 8100   │
                  │  Cloudflare Tunnel           │
                  │  PostgreSQL · jobs · credit  │
                  │  provider registry · api_pool│
                  │  storage (R2) · public API   │
                  │  ⚠️ VÀ CŨNG LÀ GPU WORKER    │
                  │     hai RTX 5060 Ti          │
                  └───┬───────────────┬──────────┘
                      │               │
        LAN (bearer)  │               │  HTTPS (chưa tồn tại)
                      ▼               ▼
        ┌─────────────────────┐   ┌───────────────────────┐
        │  B-LAN  192.168.2.66│   │  C-CLOUD              │
        │  RTX 3090 24 GB     │   │  Runpod A100 80GB     │
        │  :8199 render_gw    │   │  ⛔ CHƯA TỒN TẠI      │
        │  :8299 llm_gw       │   │  0 dòng mã trong repo │
        │  + ComfyUI 127.0.0.1│   └───────────────────────┘
        │  + dự án video lạ   │
        │  + VMware/Proxmox   │
        └─────────────────────┘
                      │
                      ▼
              Object storage (R2) — presigned GET/PUT
```

### 1.1 A-CONTROL — và một sự thật pack V3 **không** nói

Pack mô tả A-CONTROL là "control plane": auth, DB, job, credit, provider catalog.
Đúng, nhưng **thiếu một nửa**:

🔴 **A-CONTROL cũng là một GPU worker đang phục vụ khách trả tiền.** Bằng chứng
trong mã, không phải suy đoán:

| Bằng chứng | Ở đâu |
|---|---|
| `platform_core/gpu.py` đọc `nvidia-smi` **trên chính máy A** | `platform_core/gpu.py:53` |
| `gpu_lease.py` giành card bằng `UNIQUE(host, gpu_uuid)`, host = máy A | `platform_core/gpu_lease.py:128` |
| Máy A đã **sập thật** 2026-08-26 (`0x116 VIDEO_TDR_FAILURE`) vì một job 12,6 GB chạy 9 phút trên card đang xuất hình | chú thích `gpu_lease.py:36-52` |
| LTT VOICE chạy engine **trên máy A**, dịch vụ NSSM thứ tư `LTTStudioVoice` | Q117 |
| Hai app khai thẳng `requires=("gpu", "ffmpeg")`: `taoclipngan`, `upscalevideo` | `apps/*/manifest.py` |
| `ltt_voice` khai làn riêng `("voice",)` và chạy **GPU-first** trên máy A | Q118 |
| `autosubvideo`, `qualitylab` khai `("ffmpeg",)` nhưng đường ASR của chúng vẫn đụng card | `apps/*/manifest.py`, `requirements-whisperx.txt` |

**Hệ quả cho V3:** bất kỳ cơ chế nào của Video AI đụng tới GPU cục bộ, hoặc đốt
CPU trên máy A, là đụng vào máy đang phục vụ khách. Luật ngân sách lõi trong
`CLAUDE.md` toàn cục (10 lõi vật lý, trần `-n 6`, `tools/cua_so_yen.py`) **áp
dụng nguyên vẹn** cho mọi phiên làm V3.

Hai card: `platform_core/gpu.py:4` — *"từ 2026-08-06 máy chủ có **hai** RTX 5060 Ti"*.

Dịch vụ khác chạy quanh A-CONTROL: `codex_sidecar/` (ChatGPT Plus), `voice_sidecar/`
(:8120, Q117), Nexus relay (**VPS Vultr `45.76.185.75`**, không phải máy A — Q96).

### 1.2 B-LAN — **bốn hộ**, không phải một worker

Đây là điểm pack V3 nói mơ hồ nhất, và nó quan trọng nhất với D02/D11.

B-LAN không phải "một GPU worker của nền tảng". Nó là **một card 24.576 MB có
nhiều hộ tranh nhau**, và cơ chế tranh chấp là một hợp đồng đang gánh tiền thật:

| # | Hộ | Là gì | Trạng thái thương mại |
|---|---|---|---|
| ① | `render_gateway` :8199 | cổng ảnh, provider `ltt_image`, model HiDream-O1 | **ĐANG BÁN** — 3 credit/ảnh t2i, 9 credit/ảnh có tham chiếu (`/gia-api`, phiên bản giá `ltt-image-2026-08-24b`) |
| ② | `llm_gateway` :8299 | cổng LLM, provider `ltt_llm`, `qwen38-api` + `qwen38-vision` | **ĐANG BÁN** — 50/10/400 credit mỗi triệu token vào/cache/ra |
| ③ | dự án video lạ | ComfyUI **dùng chung**, không thuộc repo này | không bán qua nền tảng; **một lượt từng chạy 72,5 phút, ăn 98,7 % VRAM** |
| ④ | VMware → Proxmox | hạ tầng bán VPS (`apps/vps`), ổ `H:` | **ĐANG BÁN** |

Số đo VRAM (`render_gateway/nhuong_card.py:6-14`):

```
HiDream đỉnh khi vẽ      18.450 MB
Qwen3.8-27B thường trú   19.237 MB
                         ─────────
tổng                     37.687 MB   trên card 24.576 MB
```

⇒ **Hai model không bao giờ cùng lúc được.** Swap không phải tối ưu hoá, nó là
chế độ vận hành duy nhất. `nhuong_card.py` thi hành điều đó bằng hai loại hộ:
hộ **bảo-được** (có `duong_nha`, gọi được endpoint nhả) và hộ **chỉ-chờ-được**
(dự án video hôm nay).

🔴 **Và mã nguồn đã viết sẵn rằng video là "hộ thứ tư"** — `render_gateway/api.py:82-89`:

> *"chủ sản phẩm chốt 24/08 rằng dự án video sau này đi theo đúng khuôn LLM/ảnh,
> nên hộ thứ tư là chuyện *khi nào*, không phải *có hay không*."*

⚠️ Đây là **mâu thuẫn tiềm tàng với D11** ("B-LAN không tham gia Video V1"). Không
phải mâu thuẫn *hôm nay* — D11 chỉ nói V1 không dùng B-LAN, và cái ghi trong mã là
một dự định tương lai. Nhưng nó phải được ghi ra để P01 không "phát hiện" lại nó
rồi tưởng mình tìm thấy một hướng mới.

**Định nghĩa "B-LAN không bị đụng" phải bằng phép kiểm, không bằng lời hứa.**
Bốn tệp test đang là bản mô tả hành vi của B-LAN:

```
tests/test_245_render_gateway.py     cổng ảnh (phía máy B)
tests/test_250_cong_render.py        client phía máy A
tests/test_334_*                     đối chiếu trần token cổng LLM ↔ manifest
tests/test_227_nexus_render.py       đường Nexus tới cổng render
```

### 1.3 C-CLOUD — greenfield tuyệt đối

```
grep -rniI 'runpod|vast.ai|lambdalabs|cloud gpu' --include=*.py --include=*.md .
→ 0 kết quả
```

Không có mã, không có tài liệu, không có tài khoản nào được nhắc trong repo.
Mọi thứ của C-CLOUD là xây mới. **Đây là tin tốt**: không có gì để tương thích
ngược, và cả ranh giới tin cậy được vẽ từ đầu.

---

## 2. Đã có sẵn một sản phẩm video **đang bán** — `apps/taovideo`

🔴 **Đây là phát hiện quan trọng nhất của P00, và pack V3 không hề biết nó tồn tại.**

`apps/taovideo` (1.971 dòng) đang **sống trên production**: mục nav
`🎬 Tạo Video Seedance` hiện trên `https://app.lttstudios.com` cho **khách chưa
đăng nhập** (đọc từ HTML trang `/gia-api` lúc 17:50 ngày 4/9).

| Việc | Đã có ở taovideo | Tệp |
|---|---|---|
| Nhà cung cấp | BytePlus ModelArk (Seedance 2.0 / fast / mini) | `apps/taovideo/modelark.py` |
| Kiểu chạy | async submit → poll → tải → lưu R2 | `apps/taovideo/jobs.py:137` |
| T2V | ✅ | `jobs.handle` |
| I2V | ✅ `image_key` (ảnh ≤8 MB inline, >8 MB → `asset://`) | `apps/taovideo/refs.py`, `assets.py` |
| Character/tham chiếu | ✅ tối đa **4** tài nguyên tham chiếu | `jobs._reference_specs:82` |
| V2V | ✅ `video_key` → `asset://` | `jobs.handle`, `cost.has_video_reference` |
| Giá lai (D09) | ✅ giữ trần ước ×1,25 → quyết toán theo **token thật** | `apps/taovideo/cost.py:91` |
| Chống double-bill khi worker chết | ✅ lưu `_remote_task_id` vào `job.params` ngay sau submit | `jobs._luu_task_id:116` |
| Kiểm duyệt / heal ảnh người thật | ✅ 2 pass `asset://`, 5 lần đổi seed | `jobs.handle` |
| Hợp đồng public API | ✅ `video.generate`, `api_exposed=True`, `params`/`constraints`/`enums` đầy đủ | `apps/taovideo/manifest.py:20,213` |
| Phục vụ video né trần 100 MB | ✅ HTTP Range | `apps/taovideo/routes.py` |
| Giao diện khách | ✅ `apps/taovideo/templates/taovideo.html` + 5 tệp test giao diện | `test_111`, `test_112`, `test_113`, `test_158`, `test_170` |

**Đọc cho đúng ý nghĩa:** bốn mode V1 của D03 **đã có mặt hàng đang bán rồi** —
qua một nhà cung cấp bên ngoài. Nghĩa là câu hỏi thật của V3 **không phải**
*"làm sao có video"*, mà là:

> **Vì sao phải tự chạy GPU khi đã bán được video qua API bên thứ ba?**

Câu trả lời có thể rất chính đáng (biên lợi nhuận, không bị chính sách nội dung
của hãng khác chi phối, kiểm soát chất lượng, mode mà Seedance không làm được).
Nhưng nó **chưa được viết ra ở đâu**, và nó quyết định gần như mọi thứ phía sau:
scope V1, định nghĩa "Quality/Pro", và cả việc có nên tiêu $150 hay không.

⇒ **ADR-0 (xem `EXECUTION_PLAN_REBASED.md`) là câu hỏi cho người dùng.**

Và về mặt kỹ thuật: `taovideo` đã bán các mode này rồi ⇒ P11/P12/P13 của pack
("xây app video / GUI / public API") **là xây trùng**. Chính điều mà
`policies/GLOBAL_RULES.md` mục *No reinvention* cấm.

---

## 3. Kiểm kê abstraction — cái gì tái dùng, cái gì đừng đụng

Cột **Phán quyết** dùng: `DÙNG LẠI` (gọi thẳng) · `MỞ RỘNG` (thêm qua hợp đồng
sẵn có) · `ĐỪNG ĐỤNG` (sửa là vỡ chuyện đang phục vụ khách).

### 3.1 Provider / khoá API

| Thứ | Tệp | Nó là gì | Phán quyết |
|---|---|---|---|
| Provider Registry | `platform_core/providers.py:65` | **MỘT** chỗ khai mọi nhà cung cấp. Docstring: *"Thêm loại API mới = thêm MỘT dòng ở REGISTRY (+ tuỳ 1 adapter HTTP), KHÔNG sửa app"* | **MỞ RỘNG** — thêm `ltt_video` |
| `ModelInfo.capabilities` | `providers.py:42` | schema nghiệp vụ theo model (resolutions/durations/…) — **additive**, đã dùng cho video byteplus | **DÙNG LẠI** |
| `base_url` từ env | `providers.py:164` | `ltt_image`/`ltt_llm` lấy `base_url` từ biến môi trường, **chưa đặt ⇒ rỗng ⇒ adapter từ chối chạy (fail-closed)** | **DÙNG LẠI** khuôn này y nguyên |
| `providers_live.py` | 91 dòng | làm mới danh sách model từ `/v1/models`, parse cả `{"data":[…]}` và Gemini | **DÙNG LẠI** |
| `api_pool.py` | 261 dòng | cấp phát khoá, telemetry rpm/tpm, cooldown, cascade đa-provider, **disable sau 5 lỗi auth** | **DÙNG LẠI** |
| `APIKEY_CAT_VIDEO` | `models.py:650` | hạng mục khoá `video` **đã tồn tại** | ⭐ nghĩa là `ltt_video` **không** phải mở rộng enum — chính lý do Q117 từ chối làm provider cho VOICE thì ở đây **không áp dụng** |

### 3.2 Hàng đợi job — nơi V3 được cho không nhiều nhất

| Cơ chế | Tệp:dòng | Nó giải sẵn bài toán nào của V3 |
|---|---|---|
| `submit()` + `dedupe_key` | `jobs.py:140` | F5 / double-submit / "Tạo lại" không tạo job thứ hai |
| `claim()` `FOR UPDATE SKIP LOCKED` | `jobs.py:185` | nhiều worker không nhặt trùng |
| `claim(capabilities=…)` | `jobs.py:185` | làn worker theo `manifest.requires` (`LTT_WORKER_POOLS`) |
| aging + fair-share theo account | `jobs.py:214` | một khách không đói vì khách khác nộp ồ ạt |
| **`DangBan`** | `jobs.py:86` | *"bận thì thử lại, **đừng tính** lượt"* — chính là 429 của C-CLOUD |
| `defer_resource()` | `jobs.py:300` | về hàng đợi + `retry_after_s`, không tiêu attempt, không chạm sổ tiền |
| **`LoiNguoiGoi`** | `jobs.py:54` | lỗi tham số khách → **không** thử lại 3 lần |
| `mark_provider_dispatched()` | `jobs.py:273` | ghi bền **ngay trước** HTTP ra ngoài |
| `mark_ambiguous()` | `jobs.py:315` | worker chết sau khi đã gửi → terminal, **tuyệt đối không auto-retry** ⇒ chống double-bill GPU |
| `admission_resource` / `admission_slots` | `jobs.py:140`, Q114 | ba cửa (job/sync/stream) giành **cùng một slot** trước provider |
| `reclaim_orphans()` | `jobs.py:420` | worker chết → job về hàng đợi, có tính lượt |
| `job_events` / `job_metrics` / `job_history` | 234/204/113 dòng | tiến độ, sự kiện công khai vs nội bộ, đo độ trễ |

⇒ **P14 (GPU lifecycle) không cần một scheduler mới.** Nó cần một *bộ điều khiển
vòng đời Pod*, và các mảnh khó nhất đã có.

### 3.3 Lease — single-flight đã có sẵn hai bản

| Thứ | Tệp | Dùng cho C-CLOUD thế nào |
|---|---|---|
| `leases.py` (`acquire`/`heartbeat`/`release`) | 146 dòng | **single-flight provisioning**: đúng một tiến trình được phép tạo Pod. Giành bằng `INSERT`, `IntegrityError` = người khác thắng (đường chạy bình thường). Tự lành sau TTL 2 phút |
| `gpu_lease.py` | 254 dòng | khuôn *"thu hồi mồ côi → giành → đập nhịp → trả"*, đã chạy production; **chỉ dành cho GPU CỤC BỘ trên máy A** |
| `manifest.bao_tri` + `bao_tri_moi_giay` | `registry.py:325` | việc nền định kỳ chạy **dưới lease** ⇒ đúng một lần trên toàn cụm. Sinh ra sau lỗi thật: `apps/vps` viết `thu_phi_dinh_ky` mà **không nơi nào gọi nó** |

⇒ Bộ đối soát Pod mồ côi của P14 nên là một `bao_tri` của app, **không** là một
vòng lặp tự dựng — đúng lỗi mà hợp đồng này ra đời để chặn.

### 3.4 Tiền

| Thứ | Tệp | Ghi chú |
|---|---|---|
| Sổ credit chỉ-ghi-thêm | `credit.py` | số dư = `SUM` của sổ; khoá `pg_advisory_xact_lock` theo user chống double-spend |
| `giu_cho` / `quyet_toan` / `hoan` | `credit.py:260/393/439` | **idempotent theo job** |
| `SettlementResult` | `credit.py:35` | tách `provider_credit` khỏi `charged_credit`, có `variance` và `capped` — **chính là D09** |
| `submit_with_credit` | `job_submit.py:40` | job + giữ chỗ trong **một** transaction; `quoted_credit` giữ đúng số đã hứa với khách |
| `gia_von.py` + `gia_von.json` | 248 dòng | giá vốn để tính biên |
| `to_tien.py`, `billing_math.py` | 161/35 | quy đổi credit ↔ VND (Q31: 1 credit = 100đ) |

⚠️ **Nhưng mô hình chi phí của C-CLOUD KHÁC mọi thứ đang có.** Hôm nay giá vốn là
*"mỗi lượt gọi tốn $X"* (token, ảnh, giây). Với GPU thuê, giá vốn là
*giây-GPU × giá/giờ + phần khấu hao storage cố định + thời gian khởi động phân bổ*.
Một Pod bật 20 phút để chạy 3 phút video là 17 phút phải tính vào đâu đó. Đây là
một quyết định giá, không phải một phép nhân → **ADR-2**.

### 3.5 Lưu trữ / media

| Thứ | Tệp | Ghi chú |
|---|---|---|
| `Storage` + `LocalStorage` + **`R2Storage`** | `storage.py:61/205/300` | R2 **đã có**, kèm `url_for`/`put_url` presigned. Pack lo "phải thêm backend R2" — không cần |
| `try_url_for` / `try_put_url` | `storage.py:141/151` | trả `None` với backend cục bộ ⇒ adapter báo lỗi thẳng thay vì gửi job chắc hỏng |
| `CLOUDFLARE_BODY_LIMIT` | `storage.py:34` | 100 MB, kiểm ở tầng app để lỗi nói rõ nguyên nhân |
| `upload_sessions.py` | 400 dòng | staging → promote sau khi job giữ credit; sweeper cho browser bỏ dở; trần 20 phiên / 2 GB / 12 phiên mỗi phút |
| `media.py` | 262 dòng | ffmpeg/ffprobe, `probe`, `duration_seconds`, dò encoder GPU |
| `image_input.validate_reference` | 49 dòng | kiểm ảnh tải lên — **đừng viết lại** (`AGENTS.md` §8.3) |

### 3.6 Public API — **đóng băng theo thiết kế**

| Thứ | Tệp | Ý nghĩa với P13 |
|---|---|---|
| `API_V1_ROUTES` | `server/api/inventory.py:41` | Bề mặt đóng băng. `test_178` chốt **hai chiều**: thêm route không khai ⇒ đỏ; khai mà không dựng ⇒ cũng đỏ. ⚠️ **Đếm thật hôm nay: 27 mục** (26 vào OpenAPI + `openapi.json` `in_schema=False`), trong khi `CLAUDE.md` và ba tệp `docs/PUBLIC_API/*` còn ghi **24** — xem §3.6b |
| `POST /api/v1/jobs` | inventory.py:62 | route **duy nhất** `ASYNC_JOB` — thêm tool video **không cần route mới** |
| `ToolSpec.api_exposed` + `api_contract` | `registry.py:102` | hợp đồng công khai khai trong manifest app |
| `LTT_PUBLIC_API_TOOLS` | `public_api/config.py:170` | **công tắc của operator**, fail-closed. Ba cổng độc lập (Q92) |
| Upload / artifact / webhook / usage / quotes | inventory.py | đã có đủ |
| `tools/check_api_compat.py`, `snapshot()/compare()` | | bộ kiểm tương thích đã có |
| Trang `/developers` | `docs/developer_portal_mvp_ui/` | khoá, scope, usage, webhook — **đã dựng** |

⇒ P13 co lại còn: **khai hợp đồng tool + bật cờ operator + chụp ảnh tương thích**.
Không auth mới, không khoá mới, không trang mới.

### 3.6b ⚠️ Một chỗ tài liệu repo đã trôi khỏi mã — bắt được lúc P00

Đếm bằng mã, không bằng trí nhớ:

```python
body = source[source.index("API_V1_ROUTES"):]
body.count("ApiRoute(")   →  27
```

**27 mục** trong `API_V1_ROUTES` hôm nay (26 vào OpenAPI, cộng
`GET /api/v1/openapi.json` khai `in_schema=False`). Nhưng **bốn** chỗ trong repo
vẫn ghi *"24 route đóng băng"*:

```
CLAUDE.md:228
docs/PUBLIC_API/API_PLATFORM_FULL_RELEASE_READINESS.md:14
docs/PUBLIC_API/AUDIT_API_2026-08-15.md:97
docs/PUBLIC_API/EXTENSION_PROGRESS.md:2124
```

Lệch đúng **ba**, và ba cái đó gần như chắc chắn là ba cửa thêm sau khi con số 24
được viết: `POST /api/v1/chat/completions` (Q106) · `POST /api/v1/messages` và
`POST /api/v1/responses` (Q107).

⭐ Đây **không phải** một lỗi của hệ thống — `test_178` vẫn chốt hai chiều nên mã và
OpenAPI luôn khớp nhau. Nó là một **con số chép tay trong tài liệu đã trôi**, đúng
lớp lỗi mà `CLAUDE.md` tự mô tả ở mục *"HỎI MÁY CHỦ, đừng đọc ở đây"*: một bảng
chép tay **không có cách nào tự biết nó đã cũ**.

⛔ P00 **không sửa** bốn tệp đó: chúng ngoài phạm vi Video AI, và ba trong bốn là
tài liệu lịch sử có ngày tháng (sửa số trong một bản kiểm ngày 15/08 là làm hỏng
một bản ghi). Việc đúng là **P13 xác nhận lại và sửa `CLAUDE.md`** khi nó đụng
Public API — đó là lúc có lý do chính đáng để chạm.

### 3.7 `render_gateway/` — kho báu bị hiểu nhầm là "chỉ của máy B"

Đây là chỗ P01 phải đọc kỹ nhất. Hợp đồng HTTP của nó (đọc từ `api.py`):

| Đường | Khoá | Ghi chú |
|---|---|---|
| `GET /live` | ❌ không | cố ý không nói gì thêm — thăm dò sống/chết không mang bí mật |
| `GET /health` | ✅ | `comfy_alive`, `models`, `gpu`, `busy`, `reason`, `eta_s` |
| `GET /v1/models` | ✅ | khuôn `{"data":[…]}` để `providers_live.parse_models` đọc được |
| `POST /v1/images/generations` | ✅ | **202** + `job_id`; gửi lại cùng `job_id` ⇒ trả job cũ (**idempotency**); **429 = BẬN** kèm `Retry-After` |
| `GET /v1/jobs/{id}` | ✅ | trạng thái |
| `POST /v1/jobs/{id}/cancel` | ✅ | huỷ **đúng** `prompt_id` — `/interrupt` trống sẽ giết lượt 70 phút của hộ khác |
| `POST /v1/exclusive` | ✅ | độc chiếm có TTL |

Phía máy A: `platform_core/image_gen/cong_render.py` (client) +
`dieu_phoi.py` (điều phối trọn job) + `prompt_dich.py` (dịch prompt).

**Ba luật đã trả giá để học** (`cong_render.py:5-20`):
1. **429 là BẬN, không phải hỏng.** Đánh dấu lỗi ⇒ `api_pool` cooldown ⇒ `disable`
   sau 5 lần ⇒ **model nhà tự tắt vĩnh viễn** chỉ vì hàng xóm bận.
2. **Không tự chuyển sang đám mây.** Đổi model sau lưng khách là đánh tráo sản phẩm.
3. **`job_id` là của máy A và phải ổn định** — nó là khoá idempotency. Bản đầu
   thiếu chốt này và đốt ~100 giây GPU mỗi lần gửi lại.

**Máy B không giữ bí mật nào của nền tảng** (Q102): ảnh **vào** bằng presigned GET,
**ra** bằng presigned PUT. Không mật khẩu CSDL, không khoá R2. — Đây chính là mô
hình ranh giới tin cậy mà `policies/TOPOLOGY_AND_BOUNDARIES.md` vẽ cho C-CLOUD.
**Nó đã chạy thật rồi.**

#### Cái gì trong `render_gateway` là chung, cái gì là ảnh

| Mảnh | Tổng quát? | Bằng chứng |
|---|---|---|
| `comfy.py` — client ComfyUI | ⭐ **CHUNG**, và ghim commit ComfyUI `6f7cd7f` | mọi đường đọc từ mã nguồn ComfyUI 0.30.0, kể cả phát hiện *websocket chỉ gửi cho client đã gửi prompt* |
| `workflows.py` — nạp template JSON API-format, thay thẻ `"@ten"` | ⭐ **CHUNG** | *"thêm model mới = thêm một file JSON, không sửa mã"* — đã thử thật khi model đổi từ Klein 9B sang HiDream-O1 |
| `catalog.py` + `workflows/catalog.json` | ⭐ **CHUNG** (dữ liệu) | `ModelSpec` có `modes`/`ref_slots`/`defaults`/`buckets` |
| `jobs.py` — JobStore trạng thái | **CHUNG** | `queued/preparing/generating/saving/completed/failed/cancelled` |
| `busy.py` — trọng tài bận + ETA từ lịch sử | **CHUNG** | không dùng `/system_stats` vì nguồn đó mù với tiến trình khác trên WDDM |
| `nhuong_card.py` — N hộ dùng chung card | **CHUNG** nhưng **chỉ có nghĩa khi nhiều hộ chung một card** | C-CLOUD là card riêng ⇒ **không cần** |
| `storage_io.py` | ⚠️ **ẢNH** | `TRAN_ANH_REF_MB=8`, `_MAGIC` chỉ nhận ảnh, `day_ket_qua(anh: list[bytes])` |
| `runner.py` | ⚠️ **ẢNH** | `comfy.images_of(prompt_id)`, `image_keys[:so]` |
| `api.py` bề mặt | ⚠️ **ẢNH** | chỉ có `POST /v1/images/generations`, `content_type="image/png"` |
| `config.py` mặc định | ⚠️ **WINDOWS** | `E:\AI\ComfyUI\input`, `E:\AI\ltt_render\work` — nhưng **tất cả đều từ env**, không viết cứng |
| `main.py` | ⚠️ **WINDOWS** | `C:\ProgramData\LTTRender\gateway.env`, NSSM |
| `deploy/tai_model.py` | ⭐ **CHUNG** | tải trọng số theo **bản khai JSON**, ghi `BANG_KE.json` (tên/nguồn/sha256/ngày/dung lượng), **tải tiếp được** — đây gần như đúng thứ P05 cần |

⭐ **Kết luận cho ADR:** cái đắt nhất — client ComfyUI đã kiểm chứng, hệ thống
template workflow theo dữ liệu, khuôn presigned-GET/PUT, bộ tải model có bảng kê
— **đã tồn tại và tổng quát**. Cái đặc thù ảnh nằm ở lớp mỏng nhất (bề mặt HTTP,
đọc kết quả, kiểm loại tệp). Đó là bằng chứng mạnh cho phương án **B (lõi chung +
runtime riêng)**, nhưng P01 phải chấm điểm đàng hoàng, không được kết luận ở đây.

### 3.8 Hợp đồng app

| Luật | Nguồn | Hệ quả cho V3 |
|---|---|---|
| Thêm app = thêm **một thư mục** `apps/<slug>/` | `registry.py:1`, Q ràng buộc §2.3 | không sửa `platform_core/`/`server/` |
| App dùng **đúng bốn** module của `server` | `AGENTS.md` §8.2b | import khác ⇒ gate ĐỎ |
| `routes.py` ≤ 900 dòng / 30 handler | `tools/lint_app_contract.py` | |
| Cạnh app→app mặc định **CẤM**, cả kho có đúng **một** (`taovideo→upscalevideo`) | `AGENTS.md` §8.3, `test_308` chốt hai chiều | nếu app video mới cần gọi `taovideo` thì phải **khai** |
| `platform_core` không được biết tên app nào, kể cả trong docstring | §8.4 | |
| `surface="customer"` + không `catalog_parent` + không `routes.py` ⇒ gate ĐỎ | §8.2c | app chỉ-job phải khai `catalog_parent` (mẫu: `anhnoibo`) |
| Job không tra được giá thì **bị từ chối chạy** | Ràng buộc bất biến §4 | |
| Việc dài hơn vài giây **phải** qua hàng đợi job | Ràng buộc bất biến §5 | |

**Tiền lệ vàng: `apps/anhnoibo`** — app *chỉ có job*, bán model nội bộ chạy trên
B-LAN, `catalog_parent`, giá ở `gia.py` riêng, ToolSpec cho `/api/v1`. Đây là
khuôn gần nhất với thứ V3 cần cho C-CLOUD.

---

## 4. Quyết định nền tảng đã chốt mà V3 **phải** tuân

| # | Nội dung | Vì sao dính tới V3 |
|---|---|---|
| **Q102** | Model nhà chạy máy B là **PROVIDER**, không phải app, không phải hệ thống riêng. Máy B không giữ bí mật nào. Không dựng hàng đợi/sổ tiền/kho ảnh thứ hai. **429 ≠ hỏng** | Tiền lệ trực tiếp nhất cho C-CLOUD |
| **Q117** | LTT VOICE **không** làm provider vì engine chạy *cùng máy, sau loopback* — không có khoá để xoay, không có hạn mức để đo | Tiền lệ **ngược**. C-CLOUD là *máy khác, có token, chết độc lập, có hạn mức* ⇒ giống Q102 hơn Q117 |
| **Q114** | Một admission plane chung; **chỉ ASYNC_JOB có hàng đợi bền**; tài nguyên do tool **khai bằng metadata**, không suy từ slug | C-CLOUD phải khai `admission_resource` |
| **Q92** | Public API là adapter/policy layer, **fail-closed** ba cổng | P13 |
| **Q31** | 1 credit = 100đ | mọi phép giá |
| **Q30** | path-based một host, catalog công khai | P12 |
| Ràng buộc §5 | Trần Cloudflare **100 giây** là bắt buộc | mọi việc video **phải** async |
| Ràng buộc §1 | `D:\BOT GEMINI` chỉ đọc | |

---

## 5. Rủi ro đã nhận diện ở P00

| # | Rủi ro | Mức | Ghi ở đâu |
|---|---|---|---|
| R1 | **Xây trùng `apps/taovideo`** — P11/P12/P13 của pack viết như thể chưa có app video nào | 🔴 cao | §2 |
| R2 | **Chưa ai viết ra vì sao cần C-CLOUD** khi Seedance đã bán được 4 mode | 🔴 cao | §2 → ADR-0 |
| R3 | **Ngân sách $150 không được chia theo pha** — P06→P09 tiêu hết thì P10/P14/P15 (đều cần GPU thật) không còn tiền | 🔴 cao | `EXECUTION_PLAN_REBASED.md` §4 |
| R4 | **Hai cây/hai nhánh cùng làm V3** | 🟠 vừa | §0 |
| R5 | Mô hình giá vốn theo **giây-GPU** chưa tồn tại trong `gia_von.py` | 🟠 vừa | §3.4 → ADR-2 |
| R6 | A-CONTROL cũng là GPU worker đang phục vụ khách; máy đã sập thật vì tranh card | 🟠 vừa | §1.1 |
| R7 | Ngân sách CPU 10 lõi dùng chung với 3 phiên khác | 🟠 vừa | `CLAUDE.md` toàn cục |
| R8 | Mã đã ghi "video là hộ thứ tư của máy B" — dễ bị đọc thành cho phép đụng B-LAN | 🟡 thấp | §1.2 |
| R9 | `ho_so_he_thong.txt` là tệp **dẫn xuất**; thêm thư mục `docs/VIDEO_AI/` làm nó cũ | 🟡 thấp | sinh lại ở lượt cuối |

---

## 6. Cái gì **không** kiểm được ở P00, và vì sao

Trung thực về giới hạn của chính bản đồ này:

| Chưa kiểm | Vì sao | Ai kiểm |
|---|---|---|
| B-LAN có đang chạy thật không (`GET /live` của :8199 / :8299) | P00 không có địa chỉ/khoá trong tay và **không xin bí mật**; đường vào máy B đi qua Nexus | P01, chỉ-đọc |
| `/api/v1` đang mở tool nào | canary bỏ qua vì không có `--token-file`; đó là **fail-closed đúng ý muốn**, không phải lỗi | P13 (hoặc chủ dự án đưa token) |
| Giá A100 PCIe 80GB hiện tại | pack cấm dùng snapshot làm hằng số; phải hỏi live | P03 |
| VRAM/thời lượng thật của mọi pipeline video | chưa có gì để đo | P07/P08 |
| Bộ test có xanh trên cây này không | P00 **cố ý không chạy** gate đầy đủ: gate là công cụ ra **phán quyết**, không phải để dò; và 3 phiên khác đang chia 10 lõi | phiên nào chạm mã đầu tiên |
