# RÀ SOÁT PROMPT PACK V3 — đối chiếu với hệ thống thật

> Sản phẩm của **P00**, nhiệm vụ 4–6.
> Nguồn: `G:\My Drive\AI\A LTT AII\LTT_VIDEO_AI_CLAUDE_PROMPT_PACK_V3\...`
> (đọc đủ 16 prompt + 4 policy + 4 checklist + 5 template + `MANIFEST.json`).
>
> Thứ tự nguồn chân lý theo chính pack (`policies/GLOBAL_RULES.md`):
> **① code+test đang chạy → ② `AGENTS.md`/`CLAUDE.md`/decisions của repo →
> ③ `USER_DECISIONS.md` → ④ pack V3.** Mọi phán quyết dưới đây theo thứ tự đó.

Ngày: **2026-09-04**. Bằng chứng: `CURRENT_SYSTEM_MAP.md` cùng thư mục.

---

## 0. Đánh giá tổng thể

Pack V3 **tốt hơn hẳn mức trung bình** của loại tài liệu này. Ba điều nó làm đúng
mà repo cũng đã học bằng cách trả giá:

1. **Tách tên máy** (A-CONTROL / B-LAN / C-CLOUD). Repo đã dính đúng lỗi này —
   "máy B" trong repo là một máy vật lý có bốn hộ, gọi C-CLOUD là "máy B" sẽ sinh
   ra chính xác loại nhầm lẫn mà `nhuong_card.py` ra đời để dọn.
2. **Cost guard trước GPU trả tiền** (P04 trước P06), và **preload không GPU** (P05).
3. **Tách upstream baseline (P07) khỏi benchmark sản phẩm (P08).**

Và một điều nó làm rất đúng tinh thần repo: `policies/GLOBAL_RULES.md` mục
*No reinvention* liệt kê gần đúng những abstraction phải audit trước khi tạo cái mới.

**Nhưng pack có một điểm mù lớn, và nó lệch cả nửa cuối kế hoạch:**

> 🔴 **Pack không biết `apps/taovideo` tồn tại.**
> Một app video **đang bán trên production hôm nay**, làm được T2V + ảnh tham
> chiếu + nhiều tham chiếu + video input, có giá lai (giữ trần → quyết toán theo
> token thật), có chống double-bill, có hợp đồng public API viết xong, có giao
> diện và **năm** tệp test giao diện, cộng một tệp chốt **hợp đồng tiền** riêng.

Hệ quả: **P11 (backend), P12 (GUI), P13 (public API) như đang viết là xây trùng** —
đúng thứ mục *No reinvention* của chính pack cấm.

Điểm mù thứ hai, nhỏ hơn nhưng dai hơn:

> 🔴 **Pack không nói vì sao phải có C-CLOUD.**
> `README_START_HERE.md` mở đầu bằng *"Triển khai một App tạo video AI… bằng GPU
> cloud"* — đó là một **giải pháp**, không phải một **vấn đề**. Nếu lý do là biên
> lợi nhuận thì P08 phải so với Seedance chứ không chỉ so các workflow OSS với
> nhau; nếu lý do là kiểm duyệt nội dung thì tiêu chí "Quality/Pro" khác hẳn; nếu
> lý do là một mode Seedance không làm được thì scope V1 nên hẹp hơn D03.

⇒ Hai điểm mù này sinh ra **ADR-0** và **ADR-1** trong `EXECUTION_PLAN_REBASED.md`.

---

## 1. Phán quyết từng prompt

Ký hiệu: **KEEP** giữ nguyên · **MODIFY** sửa nội dung · **SPLIT** tách ·
**MERGE** gộp · **DEFER** hoãn · **DROP** bỏ.

| Prompt | Phán quyết | Vì sao (bằng chứng) |
|---|---|---|
| **P00** | **KEEP** | Đang thực thi. Quyền "được rebase nhưng không xoá hard gate" là đúng. |
| **P01** Current system + ADR | **MODIFY + SPLIT** | Danh sách đọc thiếu **`apps/taovideo`**, `platform_core/registry.py` (hợp đồng app), `leases.py`, `job_events/metrics`, `gia_von.py`, `apps/qualitylab`. Và **điểm quyết ADR đặt sai chỗ**: pack bắt duyệt ADR ở cuối P01, nhưng phương án tốt nhất phụ thuộc chi phí (P03) và runtime (P02) — xem §2.1. |
| **P02** OSS mining | **MODIFY** | Bỏ sót bước 0: **repo đã có hạ tầng ComfyUI**. `render_gateway/comfy.py` ghim ComfyUI `6f7cd7f` (0.30.0); `workflows.py` + `catalog.json` là hệ template theo dữ liệu *"thêm model = thêm một JSON, không sửa mã"*. Candidate nào đòi ComfyUI mới hơn là một **chi phí tương thích**, phải ghi ra. |
| **P03** Cloud BOM + cost | **MODIFY (mạnh)** | Thiếu thứ quan trọng nhất: **chia ngân sách theo pha**. Xem §2.2 — đây là defect nghiêm trọng nhất của pack sau điểm mù `taovideo`. Thêm: phải sinh **mô hình giá vốn theo giây-GPU** làm đầu vào ADR-2. |
| **P04** Runpod account + storage + cost guard | **KEEP + MODIFY nhẹ** | Đúng và đặt đúng chỗ. Thêm: nói rõ khoá Runpod cất ở đâu trong repo (§2.3) — pack chỉ viết *"nếu platform secret store phù hợp"*, mà repo có **hai** cơ chế khác nhau và chọn nhầm là một quyết định kiến trúc. |
| **P05** Preload không GPU | **MODIFY** | `render_gateway/deploy/tai_model.py` **đã làm gần đúng việc này**: tải theo bản khai JSON, ghi `BANG_KE.json` *(tên · nguồn · sha256 · ngày · dung lượng)*, tải tiếp được. `MODEL_BOM_ACTUAL.csv` / `STORAGE_MANIFEST.json` nên **sinh ra từ** nó, không phải định dạng thứ ba. |
| **P06** Tạo C-CLOUD + bootstrap | **KEEP + MODIFY** | Thêm một yêu cầu chốt: **hợp đồng HTTP của cổng C-CLOUD phải trùng khuôn `render_gateway`** (`/live` không khoá · `/health` · `/v1/models` khuôn `{"data":[…]}` · submit trả **202 + job_id idempotent** · **429 = BẬN kèm `Retry-After`** · `/v1/jobs/{id}` · `/cancel`). Không phải để dùng chung mã ngay, mà để `providers_live.parse_models` và client phía A đọc được **không thêm nhánh phân tích mới**. |
| **P07** Upstream 4 mode | **KEEP** | Đúng. Chỉ thêm: *"terminate GPU khi blocker là đọc tài liệu"* phải thành **một dòng trong sổ chi phí**, không phải một lời khuyên. |
| **P08** Benchmark chất lượng + chi phí | **MODIFY (mạnh)** | Hai thiếu sót. **(a)** Không so với **đương kim** (Seedance qua `taovideo`) thì "Quality/Pro" không có mốc nào có nghĩa thương mại. **(b)** Repo **đã có** cả một hệ chấm chất lượng: `apps/qualitylab` (operator-only, `qualitylab.evaluate`), `tools/cham_mu.py` (chấm mù + khoảng Wilson), `tools/bradley_terry.py` (xếp hạng >2 model), `docs/QUALITY_LAB/06_HUMAN_AB_CALIBRATION.md`. Dựng bảng chấm mới là xây trùng. Xem §2.4. |
| **P09** Golden pipelines | **MODIFY** | `PIPELINE_REGISTRY_PROPOSED.json` là một registry **thứ hai**. Repo đã có nơi khai năng lực model: `ModelInfo.capabilities` trong `providers.py` (chính chỗ `hidream-o1` khai `modes`/`buckets`/`steps`/`do_duoc`/`canh_bao`). Nếu C-CLOUD là provider thì golden pipeline **là** một `ModelInfo`. Nếu ADR chọn khác thì phải nói rõ vì sao cần registry riêng. |
| **P10** Kiến trúc remote + E2E | **MODIFY** | Đúng hướng. Thêm: khuôn client đã có thật — `platform_core/image_gen/cong_render.py` + `dieu_phoi.py`. Ba luật của nó (**429≠hỏng · không tự đổi model sau lưng khách · `job_id` là khoá idempotency của máy A**) là **bắt buộc**, không phải gợi ý — vi phạm luật 1 làm `api_pool` tự tắt provider sau 5 lần. |
| **P11** App backend | **MODIFY (mạnh)** | Phụ thuộc **ADR-1**: mở rộng `taovideo` hay app mới? Những việc pack liệt kê mà **đã có**: job async, giữ chỗ/quyết toán/hoàn, tiến độ/huỷ/idempotency, upload lớn qua object storage, telemetry giá vốn. Việc **thật sự mới** chỉ là: adapter gọi C-CLOUD, khai mode theo pipeline đo được, và mô hình giá theo giây-GPU. |
| **P12** Web GUI | **MODIFY (co lại)** | `apps/taovideo/templates/taovideo.html` + `test_111/112/113/158/170` đã có (và `test_172` chốt hợp đồng tiền). Việc mới là **chọn backend/mode** trên giao diện sẵn có, không phải một GUI mới. Giữ nguyên yêu cầu kiểm trên **URL công khai** — và bổ sung cách mở trình duyệt đúng (§2.5). |
| **P13** Public API + developer profile | **MODIFY (co lại mạnh)** | `/api/v1` có bề mặt **đóng băng** (đếm thật **27** mục, tài liệu repo còn ghi 24 — xem `CURRENT_SYSTEM_MAP.md` §3.6b), `test_178` chốt **hai chiều**. `POST /api/v1/jobs` là route `ASYNC_JOB` **duy nhất** ⇒ thêm tool video **không cần route mới**. Khoá/scope/rate-limit/webhook/usage/quota và trang `/developers` **đã dựng**. Việc còn lại: khai `api_contract` trong manifest + bật `LTT_PUBLIC_API_TOOLS` + chạy bộ kiểm tương thích. Mục *"Developer page: key create/revoke…"* của pack là **DROP** — đã tồn tại. |
| **P14** GPU lifecycle | **MODIFY** | Máy trạng thái pack đề xuất là hợp lý, nhưng bốn mảnh khó nhất **đã có**: single-flight (`leases.acquire`, giành bằng `INSERT` + `IntegrityError`), *bận-không-tính-lượt* (`jobs.DangBan` + `defer_resource`), *đã gửi rồi mà worker chết* (`mark_provider_dispatched` → `mark_ambiguous`, **cấm auto-retry**), và đối soát định kỳ chạy đúng một lần toàn cụm (`manifest.bao_tri` dưới lease). Xem §2.6. |
| **P15** Final audit | **KEEP + MODIFY** | Thêm cổng của repo: `python tools\gate.py` **đầy đủ** · `tools/lint_app_contract.py` · `tools/check_api_compat.py` · `tools/scan_source_secrets.py` · `tools/so_deploy.py`. Và **`tools/api_prod_canary.py trang-thai`** thay cho việc chép tay bảng "cái gì đang sống" — `CLAUDE.md` ghi rõ bảng chép tay đã nói sai **năm lần**, cả năm về phía nguy hiểm. |

**Không prompt nào bị DROP hoàn toàn. Không hard gate nào bị bỏ.**

---

## 2. Sáu điểm phải sửa, kèm bằng chứng

### 2.1 Điểm quyết ADR đặt sai chỗ trong `PHASE_GRAPH.json`

Pack hiện tại:

```
P01 → (ADR PROPOSED, user duyệt)  → P03 → P04 → … → P10 (implement ADR)
P02 ─────────────────────────────↗
```

`policies/NON_NEGOTIABLE_GATES.md` viết *"P01 Gate: ADR PROPOSED có evidence và
user approval **trước code tích hợp**"*. Nhưng `P10` mới là chỗ có code tích hợp,
và giữa P01 và P10 có **tám pha** sinh ra đúng những bằng chứng mà ADR cần: runtime
thật (P06), pipeline chạy được (P07), chi phí mỗi video (P08).

⚠️ Bắt duyệt ADR ở cuối P01 là bắt người dùng quyết **trước khi có số**. Và
`P01_CURRENT_SYSTEM_AND_ADR.md` tự biết điều đó — nó viết *"Nếu chưa đủ evidence,
ADR = OPEN và ghi experiment cần thiết thay vì đoán."*

**Sửa:** giữ nguyên P01 (phân tích + scorecard + **đề xuất**), nhưng tách **cổng
duyệt ADR** thành một mốc riêng đặt **sau P03** (có chi phí) và **trước P10** (có
code). Chi tiết ở `EXECUTION_PLAN_REBASED.md` §2.

### 2.2 🔴 Ngân sách $150 chưa được chia theo pha — defect nghiêm trọng nhất

`P03` yêu cầu *"Xác minh worst-case ≤ $150/month"*. Nhưng nó tính **một tổng**, và
tổng đó không nói pha nào được tiêu bao nhiêu.

Đếm các pha **cần GPU trả tiền**: P06 (bootstrap + test recreate), P07 (4 baseline
+ ít nhất một lần chạy lại để kiểm tái lập), P08 (ma trận benchmark 4 mode × nhiều
ca × nhiều candidate), P09 (chốt golden), P10 (E2E A↔C, **và recreate rồi chạy
lại**), P14 (**failure injection**: bật/chạy/drain/terminate lặp nhiều lần), P15
(canary production).

**Bảy pha, một túi tiền, không ai giữ cửa.** Thứ tự chạy thì P08 (tốn nhất) đứng
trước P14/P15 — nghĩa là pha tiêu nhiều nhất tiêu trước, và pha *chứng minh hệ
thống an toàn* tiêu sau cùng bằng phần còn thừa.

⭐ Repo đã có đúng bài học này ở một tầng khác: `render_gateway/ngan_sach.py`,
`llm_gateway/ngan_sach.py`, `apps/ltt_llm/ngan_sach.py` — mỗi nơi có **một** hàm
ngân sách, một đơn vị, và một nguồn duy nhất. Ngân sách tiền cloud phải được đối
xử y như vậy.

**Sửa:** P03 phải sinh **envelope cho từng pha** + luật *"pha sau không mượn trước
được của pha trước"*, và `COST_LEDGER_TEMPLATE.csv` thêm cột `phase_envelope_usd`,
`envelope_remaining_usd`.

### 2.3 Khoá Runpod cất ở đâu — pack để ngỏ, mà repo có hai đường khác hẳn

`P04` viết: *"Nếu platform secret store phù hợp, chuẩn bị chỗ lưu Runpod API
credential ở A-CONTROL."* Repo có **hai** cơ chế:

| Đường | Ở đâu | Hợp khi nào |
|---|---|---|
| **APIKEYS** (`api_keys.py` + `api_pool.py` + bảng `ApiKey`) | có xoay khoá, cooldown, telemetry rpm/tpm, disable sau 5 lỗi auth | khoá **gọi model** — đúng cho token cổng C-CLOUD (tiền lệ: token cổng render cất y như vậy, Q102) |
| **`secrets/app.env`** (`secretbox.py`, `settings.py`) | biến môi trường sinh lúc cài, giữ nguyên khi cài lại | bí mật **hạ tầng** — tiền lệ `LTT_CODEX_SIDECAR_TOKEN` (Q117) |

⚠️ Khoá **vòng đời Runpod** (tạo/xoá Pod, tiêu tiền thật) **không phải** khoá gọi
model. Đặt nó vào `api_pool` là để cơ chế cooldown/disable của nhà cung cấp model
điều khiển thứ tạo ra hoá đơn — sai ngữ nghĩa.

Hạng mục khoá hiện có: `model_control · chat · image · video`
(`platform_core/models.py:647`). Có `model_control`, nhưng nó **chưa từng** được
dùng cho một API vòng đời hạ tầng.

**Sửa:** P04 phải **quyết và ghi lý do**, không để ngỏ. Đề xuất P00 (P04 có quyền
đảo nếu có bằng chứng khác): **khoá vòng đời Runpod đi `secrets/app.env`; token
gọi cổng C-CLOUD đi APIKEYS như `ltt_image`.** Hai thứ khác nhau, hai chỗ khác nhau.

### 2.4 P08 thiếu đương kim, và bỏ qua hệ chấm chất lượng đã có

**(a) Thiếu đương kim.** `templates/BENCHMARK_TEMPLATE.csv` có `accepted`,
`quality_score`, `provider_cost_usd` — đủ để so các candidate OSS **với nhau**,
không đủ để trả lời *"cái này có đáng thay Seedance không"*.

Repo đã làm đúng phép so này một lần và **chấp nhận kết quả bất lợi**: model ảnh
nhà thua Gemini 24–4 trong so mù (D-045), và điều đó **không** làm dự án dừng — nó
làm dự án đổi cách định vị sản phẩm (`providers.py:178`: *"ĐỪNG ĐỊNH VỊ NÓ LÀ ĐẸP
HƠN"*). Đó là một phép so đã tạo ra giá trị thật.

**(b) Bỏ qua hệ đã có:**

| Có sẵn | Là gì |
|---|---|
| `apps/qualitylab/` | app operator-only, `job_types=("qualitylab.evaluate",)`, `surface="admin"`, có dataset/calibration/materializer |
| `tools/cham_mu.py` | chấm **mù** + khoảng Wilson (đúng cho 2 model) |
| `tools/bradley_terry.py` | xếp hạng khi có **>2** đối thủ, vì tỉ lệ thắng theo cặp không cộng thành bảng nhất quán |
| `docs/QUALITY_LAB/06_HUMAN_AB_CALIBRATION.md` | quy trình hiệu chuẩn với người chấm |
| `docs/KHUON_BAN_MODEL_NHA.md` | **31 chốt phải chấm trước khi mở cổng bán một model nhà** |

🔴 `KHUON_BAN_MODEL_NHA.md` là tài liệu quan trọng nhất mà pack không nhắc. Nó là
checklist *"đã có bao giờ mở bán một model nhà"* của chính dự án này — và ghi rằng
H37 đã **mắc lại đúng lỗi tiền của H38**.

**Sửa:** P08 mở rộng thành *"benchmark + so mù với đương kim"*, dùng
`cham_mu`/`bradley_terry`/qualitylab, và P09 phải đối chiếu **31 chốt** của
`KHUON_BAN_MODEL_NHA.md`.

### 2.5 `HUMAN_BROWSER_HANDOFF` mô tả một cách mở trình duyệt **không chạy được ở đây**

Pack viết *"Mở Runpod bằng Chrome/Playwright"*. Trên máy này, Playwright tự mở
Chrome **bị Cloudflare chặn bằng CAPTCHA** — và CAPTCHA nằm đúng trong danh sách
"phải dừng cho người" của chính pack, nên nó biến mọi thao tác tự động thành một
chuỗi bàn giao.

Cách đã chạy được trong repo: nối vào **cửa sổ Chrome thật của người dùng** bằng
`--cdp`, hoặc `--headed --profile=C:\LTTBrowserProfiles\PlenXResearch`
(`AGENTS.md` §9.1).

**Sửa:** P04 ghi rõ cách mở, để không mất một lượt dò.

### 2.6 P14 nên **mô tả bằng cơ chế đã có**, không mô tả bằng khái niệm mới

Đối chiếu từng yêu cầu của P14 với thứ đã tồn tại:

| P14 đòi | Repo đã có | Tệp |
|---|---|---|
| Single-flight provisioning (không tạo 2 Pod vì đua) | `leases.acquire()` — giành bằng `INSERT`, `IntegrityError` = người khác thắng, **tự lành sau TTL** | `leases.py:87` |
| Capacity unavailable → backpressure rõ ràng | `DangBan` + `defer_resource` — về hàng đợi, **không tiêu attempt**, không chạm sổ tiền | `jobs.py:86,300` |
| Never terminate active job | `store.active_prompt_ids()` / `co_viec` của `TraCard`; ở phía A là `job.status` | `render_gateway/api.py:154` |
| Reconcile orphan Pod sau khi app crash | `manifest.bao_tri` chạy **dưới lease** ⇒ đúng một lần toàn cụm | `registry.py:325` |
| Provider API failure sau khi đã gửi | `mark_provider_dispatched` → `mark_ambiguous` (**cấm auto-retry**) | `jobs.py:273,315` |
| Ghi **billed lifetime**, không chỉ GPU kernel time | ❌ **chưa có** | mới |
| Max session runtime + budget remaining | ❌ **chưa có** | mới |

⇒ Việc mới thật sự chỉ có **hai dòng cuối**. `templates/BENCHMARK_TEMPLATE.csv`
cũng thiếu chỗ ghi chúng: có `wall_seconds` và `gpu_active_seconds` nhưng **không có
`pod_billed_seconds`** — mà đó mới là con số ra hoá đơn.

---

## 3. Lỗi nhỏ trong chính pack

| Chỗ | Vấn đề | Sửa |
|---|---|---|
| `GLOBAL_RULES.md` §No reinvention | danh sách audit thiếu: `platform_core/registry.py` (hợp đồng app — **quan trọng nhất**), `leases.py`, `gpu_lease.py`, `job_events/job_metrics/job_history`, `gia_von.py`, `apps/qualitylab`, và **`apps/taovideo`** | bổ sung |
| `BENCHMARK_TEMPLATE.csv` | thiếu `pod_billed_seconds`, `pod_boot_seconds`, `baseline_ref` (so với đương kim), `judge` (ai/mô hình nào chấm) | thêm 4 cột |
| `COST_LEDGER_TEMPLATE.csv` | thiếu `phase_envelope_usd`, `envelope_remaining_usd` | thêm 2 cột |
| `MODEL_BOM_TEMPLATE.csv` | ổn (`checksum` đã có). Nên nói rõ **sha256** và khớp `BANG_KE.json` | ghi chú |
| `PROJECT_STATE_TEMPLATE.md` | thiếu `phase_budget_envelope`, `blan_regression_status` | thêm 2 trường |
| `B_LAN_PROTECTION.md` | toàn văn xuôi ⇒ **không kiểm được**. *"429 busy semantics preserved"* là một lời hứa, không phải một phép kiểm | đổi thành **tên tệp test cụ thể** (§4) |
| `PHASE_GRAPH.json` | P02 chỉ phụ thuộc P00 ⇒ chạy song song P01 được (**tốt**), nhưng đồ thị không có nút "ADR approved" | thêm nút cổng |
| `MANIFEST.json` | `"repo": "giaitritruyenthongltt-spec/LTTSTUDIOSAPP"` — remote thật của cây này là `origin` với các nhánh `phien/*`, `claude/*` | không quan trọng, ghi để khỏi lăn tăn |
| `README_START_HERE.md` | *"Sau mỗi phase cập nhật `docs/VIDEO_AI/PROJECT_STATE.md`"* — đúng, nhưng thiếu: **`docs/_luutru/PROJECT_MEMORY.md` cũng phải cập nhật cuối mỗi phiên** (`CLAUDE.md`) | bổ sung |

---

## 4. Biến `B_LAN_PROTECTION` thành thứ kiểm được

Pack (văn xuôi) → repo (phép kiểm). Đây là thứ P01 phải hoàn thiện, P00 đề xuất
điểm xuất phát:

| Lời hứa của pack | Đo bằng |
|---|---|
| No Video V1 job routed to B-LAN | không app video nào khai `providers: ["ltt_image"]`/`["ltt_llm"]`; không `base_url` nào trỏ `192.168.2.66` |
| No B-LAN deploy script changed | `git diff --stat` **rỗng** trên `render_gateway/**`, `llm_gateway/**` |
| No existing endpoint behavior changed | `tests/test_245_render_gateway.py`, `tests/test_250_cong_render.py` xanh **không sửa một dòng test nào** |
| 429 busy semantics preserved | các ca `BanError`/`ban()` trong hai tệp trên |
| existing auth preserved | ca `auth`/`401` trong `test_245` |
| existing image/LLM workloads unaffected | `tests/test_334*` (trần token cổng LLM ↔ manifest), `tests/test_227_nexus_render.py` |
| rollback path documented | `deploy/windows/rollback.ps1` + `app.previous\` |

⛔ **Và một luật cứng:** nếu để làm Video V1 mà thấy *cần* sửa một tệp trong
`render_gateway/` hay `llm_gateway/`, thì **dừng và trình người dùng** — đó là D02
+ mục "Thứ Claude vẫn phải hỏi user" của `USER_DECISIONS.md`, không phải một lựa
chọn kỹ thuật.

---

## 5. Xung đột với nguồn chân lý của repo — kê đủ, không tự chọn bên

`GLOBAL_RULES.md` bảo: *"Nếu xung đột, báo rõ và không tự âm thầm chọn."*

| # | Pack nói | Repo nói | Trạng thái |
|---|---|---|---|
| X1 | P11/P12/P13: xây app video, GUI, public API | `apps/taovideo` đang bán, `/api/v1` đóng băng bề mặt, `/developers` đã dựng | ⚠️ **Xung đột thật** → ADR-1, người dùng quyết |
| X2 | D03: V1 gồm 4 mode T2V/I2V/Character/V2V | `taovideo` đã bán cả 4 qua Seedance | ⚠️ **Không mâu thuẫn về scope, mâu thuẫn về LÝ DO** → ADR-0 |
| X3 | P13 "developer page: key create/revoke, scopes, usage…" | đã có | ✅ Giải bằng DROP phần đó |
| X4 | P09 `PIPELINE_REGISTRY_PROPOSED.json` | `ModelInfo.capabilities` là nơi khai năng lực model | ⚠️ Registry thứ hai → P09 phải biện minh |
| X5 | D11 "B-LAN không tham gia Video V1" | mã ghi *"dự án video sau này đi theo đúng khuôn LLM/ảnh, hộ thứ tư là chuyện khi nào"* | ✅ **Không xung đột** — mã nói tương lai, D11 nói V1. Ghi ra để không ai "phát hiện lại" |
| X6 | P04 để ngỏ chỗ cất khoá Runpod | repo có hai cơ chế, ngữ nghĩa khác nhau | ⚠️ → §2.3 |
| X7 | `HUMAN_BROWSER_HANDOFF`: "mở bằng Chrome/Playwright" | Playwright tự mở bị Cloudflare CAPTCHA | ✅ Giải bằng `--cdp` (§2.5) |
| X8 | Pack không nói gì về ngân sách CPU | `CLAUDE.md` toàn cục: **10 lõi vật lý dùng chung mọi phiên**, trần `-n 6`, `cua_so_yen.py` trước lệnh nặng | ✅ Bổ sung, không xung đột |
| X9 | Pack coi A-CONTROL là control plane thuần | A-CONTROL **cũng là GPU worker** đang phục vụ khách, đã sập thật 26/08 | ✅ Bổ sung vào topology |

---

## 6. Cái pack làm đúng mà **phải giữ nguyên**, đừng "tối ưu" đi

Ghi ra vì lượt rebase nào cũng có xu hướng cắt phần khó:

1. **P05 trước P06** — không bật A100 để tải model. Đây là tiền thật.
2. **P04 trước mọi GPU trả tiền** — emergency terminate + watchdog phải **dry-run
   xong** trước khi có Pod đầu tiên.
3. **P07 tách khỏi P08** — chạy được upstream nguyên bản trước mọi tối ưu. Repo có
   đúng bài học này ở `nhuong_card.py`: một phép kiểm *"xanh vì lý do sai"* chạy
   0,58 giây trong khi hạn chờ là 45 giây.
4. **Ghim revision** (workflow, custom node, model, commit). `comfy.py` đã ghim
   ComfyUI `6f7cd7f`; `tai_model.py` đã ghi sha256.
5. **Không expose Fast/Standard chỉ vì rẻ hơn** (D10).
6. **Re-check giá live ngay trước khi tạo resource** — snapshot chỉ là tham khảo.
7. **Mọi phase kết thúc bằng STATE/ACTIONS/EVIDENCE/TESTS/COST/RISKS/
   FILES_CHANGED/DECISIONS/ROLLBACK/GO-NO-GO.**
