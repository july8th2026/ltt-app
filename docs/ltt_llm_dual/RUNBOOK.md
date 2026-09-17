# RUNBOOK — LTT LLM Dual-Model (máy A + máy B)

Tệp này dành cho **lúc đang trực**: một việc cần làm, hoặc một thứ vừa hỏng. Nó
không giải thích kiến trúc — kiến trúc ở `DECISION_LOG.md` và
`docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md`.

> ⛔ **Không con số nào của hệ thống được gõ lại vào tệp này.** Cửa sổ ngữ cảnh,
> số slot, ngân sách KV, giá, ngưỡng VRAM — mỗi cái có đúng một nguồn chân lý và
> runbook chỉ **trỏ** tới nó. Kho này đã có năm lần một bảng chép tay nói sai, và
> cả năm lần đều sai về phía nguy hiểm (`CLAUDE.md` luật 5).
>
> | cần biết | hỏi ở đâu |
> |---|---|
> | ngữ cảnh · trần token · pool KV · số slot | `apps/ltt_llm/ngan_sach.py` |
> | giá theo model | `platform_core/llm/gia_token.py` |
> | danh tính GPU (UUID) | `llm_gateway/deploy/gpu_may_b.json` |
> | cờ engine đang chạy | `llm_gateway/deploy/llama-swap.yaml` |
> | **cái gì đang sống** | `python tools\api_prod_canary.py trang-thai` |

---

## 0. Ba câu hỏi trước khi gõ bất cứ gì

```powershell
Test-Path C:\LTTPlatform          # True  = bạn đang ở MÁY CHỦ, nó đang phục vụ khách
python tools\cua_so_yen.py trang-thai   # có phiên khác giữ khoá thì CHỜ
git rev-parse --abbrev-ref HEAD   # nhánh, không phải tên worktree
```

Và trước **mỗi** lần deploy: `ListAgents` → hỏi các phiên khác. Deploy chép **cả
cây** nguồn, nên việc của một phiên khác sẽ đi theo (`CLAUDE.md` luật 15).

---

## 1. Đường vào máy B

| | cách | ghi chú |
|---|---|---|
| chính | `ssh -i $env:USERPROFILE\.ssh\nexus_b lengo@192.168.2.66` | đo 11/09/2026 |
| phụ | Nexus (relay) | dùng khi SSH không lên |

⚠️ OpenSSH in một **cảnh báo vô hại ra stderr** mỗi lần kết nối
(`** WARNING: connection is not using a post-quantum key exchange...`). Trong một
`.ps1` có `$ErrorActionPreference = "Stop"` thì dòng đó làm **cả script chết** dù
ssh chạy bình thường. `llm_gateway/deploy/deploy.ps1::ChayTrenB` đã xử — đừng viết
một lối gọi ssh thứ hai không xử.

Dịch vụ trên máy B (tên để gõ lệnh; cổng và dòng lệnh đầy đủ ở
`docs/ltt_llm_dual/00_CURRENT_BASELINE.md` §"Dịch vụ"):

```
LTTLlamaSwap       lò model     (chỉ nghe loopback)
LTTLlmGateway      cổng LLM     (nghe LAN — chỉ máy A vào được, tường lửa)
LTTRenderGateway   cổng ảnh
LTTComfyUI         ComfyUI
```

---

## 2. Deploy

### 2.1 Thứ tự là **ràng buộc cứng**, không phải quy ước — theo HƯỚNG thay đổi

(Phương án C, 17/09 — thay dạng một chiều cũ `yaml → cổng B → A` của R21.)

```
TĂNG sức chứa (-c, -np, max_out/DEM_UOC nới)   :  máy B TRƯỚC  (yaml + cổng)  →  máy A
GIẢM sức chứa                                  :  máy A TRƯỚC  →  máy B
                                                  (A hạ bằng env, KHÔNG cần deploy mã:
                                                   LTT_ADMISSION_SO_SUAT__<resource>,
                                                   LTT_ADMISSION_POOL__<resource>
                                                   + setup\nap_lai_env.ps1)
```

**Vì sao:** máy A là người quyết định nhận; cổng máy B là **rào vật lý** đọc `-c`/`-np`
từ `llama-swap.yaml` (`llm_gateway/vat_ly.py`). Bất biến cần giữ trong mọi khe
chuyển tiếp: *A không bao giờ khai rộng hơn thứ B đang chạy* (A ⊆ B).

- Tăng mà A đi trước ⇒ A nhận lượt B chưa chứa nổi ⇒ B 413/429 **sau 200** (R21,
  đo được: trần input A rộng hơn `-c` đang chạy ⇒ lỗi nổ ở tầng dưới cùng).
- Giảm mà B đi trước ⇒ cùng hậu quả theo chiều ngược: A còn khai số cũ, lớn hơn.
- Rào B vẫn giữ nếu đi sai thứ tự (engine không tràn KV), và từ bước 1 A **xếp
  hàng lại** khi B 429 — nên sai thứ tự thành chậm, không thành mất lượt. Nhưng
  413 sau 200 thì không cứu được: vẫn phải đúng thứ tự.

⚠️ Cổng B đọc yaml **lúc khởi động**. Đổi `-c`/`-np` = restart `LTTLlamaSwap` (nạp
yaml) **rồi** restart `LTTLlmGateway` (đọc lại rào) — đảo lại thì cổng giữ số của
tệp mới trong khi engine còn chạy số cũ.

### 2.1b ⛔ R27 — trên **cùng máy A**, Task 5.3 và 5.5 là MỘT đơn vị deploy

`apps/ltt_llm/manifest.py` **đã khai** `residency_group="rtx3090"`, và luật 0
`CHO_RESIDENCY` **fail-closed** khi không đọc được dòng `gpu_residency` của nhóm đó.
Migration **không gieo dòng nào** — dòng đó do **trọng tài (Task 5.5)** tạo ở bước
đầu tiên của nó.

⇒ Máy A mang 5.3 mà thiếu 5.5 thì **mọi lượt `ltt-3.8` chờ hết ngân sách rồi 429.**
Mô hình chính **chết**, `ltt-3.5` vẫn sống (khác card, không có `residency_group`),
nên triệu chứng nhìn như *"3.8 bị bận mãi"* — một câu trỏ sai hướng hoàn toàn.

⭐ Fail-closed ở đây là **đúng**: mở cửa khi chưa biết ai đang cư trú 3090 là cách
   cấp suất cho cả hai bên cùng lúc. Cái phải sửa là **thứ tự**, không phải hướng
   fail. Và trọng tài phải tạo được dòng đó **ngay cả khi máy B im lặng**, nếu
   không thì một lần máy B không trả lời biến thành một lần LLM ngừng bán.

## 2.0 🔴 BIÊN BẢN DEPLOY 12/09/2026 — MÁY B XONG, MÁY A BỊ CHẶN

Chủ sản phẩm cấp quyền deploy máy A + máy B (12/09, chiều), **đè** lệnh cấm
deploy trong prompt chiến dịch LTT-CMC. Ghi lại để CMC đọc được đây là quyết
định của chủ sản phẩm.

### ✅ Máy B — đã xong, đã nghiệm thu

Mã hai cổng + `llama-swap.yaml` từ commit `54cac32d`; **hash khớp 39 tệp**.
Bốn việc tay ở §2.2 đều đã làm và đã đo lại:

| | Trước | Sau |
|---|---|---|
| `LTT_LLM_MODELS` | `qwen38-api,qwen38-vision` | `qwen38-api,qwen35-api` |
| `LTT_LLM_MAX_DONG_THOI=1` | còn | đã xoá |
| `LTT_HO_DUNG_CARD` / `LTT_TRA_CARD_GIAY` | còn | đã gỡ |
| `DependOnService: LTTComfyUI` | còn | rỗng |
| `gpu_may_b.json` (bản cài render) | **THIẾU** | có |

Nghiệm thu: `/v1/models` → `['qwen35-api','qwen38-api']`; `/health` → `models_la: []`,
trọng tài `bat=true`. **Rollback:** `H:/LTT_LLM/releases/auto-20260912-184817`.

Sổ khoá production: `ltt_llm.supported_models` `['qwen38-api','qwen38-vision']`
→ `['qwen38-api','qwen35-api']` (mục 2 của §2.2 — **đã gỡ chặn**). Bản rollback
ở `%TEMP%\claude\rollback_so_khoa.json`.

### ⛔ Máy A — KHÔNG deploy được từ nhánh này

    CSDL production : d9a1f6c2b3e5
    alembic của ta  : a3f7c214e8b9
    => CommandError: Can't locate revision identified by 'd9a1f6c2b3e5'

Alembic chỉ là triệu chứng. `git rev-list --count 54cac32d..main` = **59 commit**,
**191 tệp mã chạy** khác nhau, trong đó có **ba migration Voice RC1**.
⇒ Deploy nhánh này lên máy A sẽ **gỡ Voice RC1 khỏi production**.

⚠️ Đã thử và đã trả giá: production tắt ~4 phút (19:05–19:09). Bản hỏng giữ ở
   `C:\LTTPlatform\app.that-bai-20260912-190903`; CSDL **không** bị chạm; lăn lại
   bằng `app.previous`.

⇒ Máy A chờ `cmc/llm-dual-reconcile`. Toàn văn: `CMC_SOURCE_STATE.md`.

### ⚠️ Xoay `LTT_RENDER_TOKEN` (12/09)

Token củ **bị in ra một transcript phiên** nên đã xoay. Giá trị mới sống ở
`C:\ProgramData\LTTRender\gateway.env` và sổ khoá `ltt_image` — **không** ghi
vào bất kỳ tệp nào trong kho.

🔴 ĐỔI TỆP THÔI LÀ CHƯA ĐỦ. `nssm` nướng cả bộ env lúc **cài**, và
   `render_gateway/nap_env` **cố ý không ghi đè** biến đã có (khác hẳn cổng LLM:
   ở đó **tệp thắng**). Phải nướng lại rồi restart:

```powershell
$dong = Get-Content C:\ProgramData\LTTRender\gateway.env |
        Where-Object { $_ -notmatch '^\s*#' -and $_ -match '^\s*[A-Za-z_]\w*=' }
& E:\AI\ltt_render\scripts
ssm.exe set LTTRenderGateway AppEnvironmentExtra `
    (@('PYTHONPATH=E:\AI\ltt_render\gateway') + $dong)
Restart-Service LTTRenderGateway -Force
```

Đo lại sau khi đổi: token cũ → **401**, token mới → **200**.

---

### 2.2 ⛔ `llama-swap.yaml` KHÔNG đi một mình (L-17)

Nó đi **cùng Task 5.4** (lệnh residency theo model + gỡ hai trọng tài cũ). Lý do cơ
học: `LTT_HO_DUNG_CARD=llm=http://127.0.0.1:8280/unload` không mang tên model, nên
một job ảnh xin 3090 sẽ nhả **cả LTT-3.5** trên card không ai tranh. Toàn văn +
mức chắc chắn: `DECISION_LOG.md` L-17.

Cùng lần deploy đó, **năm** việc phải làm **tay** (không script nào làm hộ):

1. `C:\ProgramData\LTTLlm\gateway.env`: đặt `LTT_LLM_MODELS` thành **đúng hai hồ
   sơ đang sống** — tức **thêm `qwen35-api`** và **gỡ `qwen38-vision`**. Biến này
   fail-closed nên hai nửa sai theo hai hướng khác nhau:

   | | hậu quả |
   |---|---|
   | thiếu `qwen35-api` | **LTT-3.5 không mở được**: llama-swap chạy hai model, cổng chỉ bán một. Khách không thấy lỗi nào — họ chỉ không thấy model. |
   | còn `qwen38-vision` | cổng quảng cáo một model mà llama-swap **không còn hồ sơ nào khởi động được** (yaml mới chỉ có hai). |

   ⚠️ `LTT_LLM_MAX_DONG_THOI=1` cũ cũng còn trong tệp đó. Task 4.2 đã sửa
      `deploy.ps1` để nó **không ép** giá trị 1 nữa và tự di trú — nhưng hãy
      **đọc lại tệp sau khi chạy** thay vì tin rằng nó đã di trú: một tiến trình
      đang chạy vẫn giữ giá trị cũ tới khi restart (xem §2.3).
2. 🔴 **Sổ khoá: `supported_models` của khoá `ltt_llm` phải có `qwen35-api`.**

   Đo trên CSDL production 12/09 (chỉ đọc) — khoá `ltt_llm` **duy nhất** khai:

   ```
   supported_models = ['qwen38-api', 'qwen38-vision']
   ```

   tức **thiếu `qwen35-api`** và **còn `qwen38-vision`** (hồ sơ đã gỡ). Hậu quả
   không phải một lỗi nhìn thấy được: `api_pool.chon_key(model="qwen35-api")`
   không tìm thấy khoá nào ⇒ `ThieuKeyError` ⇒ `dieu_phoi.goi()` đọc đó thành
   *"provider không phục vụ được, đi tiếp"* ⇒ **mọi lượt LTT-3.5 hỏng trong im
   lặng**, không log, không mã lỗi.

   ⛔ **Không test nào bắt được**, và đó là cả vấn đề: sổ khoá là **dữ liệu vận
      hành**, không phải mã nguồn. Thứ chốt được là *mặc định của công cụ ghi ra
      nó* — nay dẫn từ `canonical.ALIAS_SANG_ID.values()` và có
      `test_1233::test_cong_cu_tao_khoa_cap_cho_du_hai_id_noi_bo` canh.

   Chạy **trên máy chủ**, sau khi đã ghi lại giá trị cũ để lăn lại được:

   ```powershell
   python tools\them_key_ltt_llm.py --token "<bearer cua cong VLM>"
   ```

   Không truyền `--models`: mặc định nay **đúng là** `qwen38-api,qwen35-api`.
   Lệnh idempotent — đã có khoá thì nó **cập nhật** chứ không tạo bản thứ hai.

   ⚠️ Nghiệm thu bằng một lượt gọi thật `model: "ltt-3.5"`, **không** bằng việc
      lệnh trả 0. Lệnh trả 0 chỉ nói "đã ghi", còn thứ ta cần biết là "`chon_key`
      tìm được khoá" — hai câu khác nhau, và chính khoảng cách giữa chúng đã giấu
      lỗi này suốt từ 11/09.

3. `C:\ProgramData\LTTRender\gateway.env`: gỡ `LTT_HO_DUNG_CARD` và
   `LTT_TRA_CARD_GIAY` (Task 5.4).
4. 🔴 **Gỡ `DependOnService` của `LTTRenderGateway`** — nếu không, lệnh trả card
   **không bao giờ chạy được**:

   ```powershell
   ssh ... "nssm reset LTTRenderGateway DependOnService"
   ```

   `render_gateway/deploy/cai_dat_dich_vu.ps1` đặt `LTTRenderGateway` **phụ thuộc**
   `LTTComfyUI`. Nhưng từ Task 5.4a, chính `LTTRenderGateway` là thứ **ra lệnh dừng**
   `LTTComfyUI` — và SCM từ chối dừng một dịch vụ còn dịch vụ khác phụ thuộc vào
   nó đang chạy (**1051 ERROR_DEPENDENT_SERVICES_RUNNING**). Tức cổng render tự
   chặn lệnh của chính nó.

   ⭐ Mã **có** bắt được ca này: nhận 1051, chạy `sc enumdepend` (chỉ đọc), gọi tên
      kẻ chặn và in đúng câu lệnh trên, rồi trả **503**. Nó hỏng **to tiếng**, không
      im lặng — nhưng một lệnh trả card luôn 503 thì trọng tài **treo ở `tra_anh`
      vĩnh viễn**, và LLM không bao giờ lấy lại được 3090.

   ⚠️ Chưa **đo** trên máy B: kết luận 1051 suy từ script cài + tài liệu Win32,
      còn quyền thì suy từ việc nssm không đặt `ObjectName` (⇒ LocalSystem). Đo thật
      ở lần deploy: gọi `POST /v1/nha_comfy {"hanh_dong":"dung"}` và xem nó trả 200
      hay 503-kèm-tên-kẻ-chặn.

5. 🔴 **`gpu_may_b.json` phải có mặt trong cài đặt RENDER** (Task 6.1). Bản gốc
   nằm ở `llm_gateway/deploy/`, nhưng cài đặt render trên máy B **không có** gói
   `llm_gateway` — `render_gateway/deploy/deploy.ps1` chỉ chép gói `render_gateway`.
   ⇒ Trước khi restart `LTTRenderGateway`, xác nhận trên máy B:

   ```powershell
   ssh ... "dir E:\AI\ltt_render\gateway\render_gateway\deploy\gpu_may_b.json"
   ```

   ⛔ **Thiếu tệp này là dừng hẳn việc sinh ảnh, không phải giảm chất lượng.**
   Bộ đọc **fail-closed** có chủ đích: không biết UUID 3090 ⇒ mọi phép đo GPU trả
   `None` ⇒ `xin_card` **từ chối mãi**. Đó là hướng đúng (thà từ chối hơn chạy
   mù trên số của card khác), nhưng nó biến một tệp bỏ sót thành một sự cố
   toàn phần, và log là chỗ duy nhất nói lý do.
   ⭐ Đường thoát không cần deploy lại: đặt `LTT_GPU_DANH_TINH=<đường tệp>` trong
   `C:\ProgramData\LTTRender\gateway.env` (ưu tiên cao nhất trong ba đường dò).

### 2.3 Máy B

```powershell
powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\deploy.ps1
```

**Phương án C — bước 3 (chỉ đổi MÃ cổng, yaml không đổi số):**

```powershell
powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\deploy.ps1 -BoQuaYaml
ssh ... "powershell -c Restart-Service LTTLlmGateway"   # CHỈ cổng — KHÔNG LTTLlamaSwap
curl http://127.0.0.1:8299/health    # vat_ly.nguon = H:\LTT_LLM\gateway\llama-swap.yaml
                                     # vat_ly.theo_model = -c/-np khớp /running
                                     # tran.input_tokens là dict THEO MODEL
```

- Điều kiện trước: **bước 1 đã deploy ở máy A** (A xếp hàng lại khi B 429).
- `-BoQuaYaml`: không chép, không đối chiếu `llama-swap.yaml`; cổng đọc tệp **đang
  có** trên máy B (cạnh gói `llm_gateway`). Log khởi động in `rao vat ly tu ...`.
- `LTTLlamaSwap` **không** restart ở bước này (không unload model).
- Log cảnh báo `BIEN DA GO ... van con dat` là vô hại (nssm nướng env lúc cài);
  muốn sạch: `cai_dat_dich_vu.ps1` trên máy B.
- Cổng không đọc được yaml ⇒ **từ chối khởi động** (mã thoát 4, log nói lý do).
  Lùi: bản chụp `releases/auto-*` của `deploy.ps1` + `Restart-Service LTTLlmGateway`.

🔴 **O-19 — `--no-cache-idle-slots` (còn mở, bước 4).** `/running` máy B 17/09 có cờ
này; `llm_gateway/deploy/llama-swap.yaml` **không có**. Không sửa máy B ở bước 3.
Bước 4 phải hoà giải theo kết quả phép đo **m6** (`--cache-ram` 8192 vs 0): đưa cờ
vào yaml trong kho, hoặc gỡ nó trên máy B. Tới lúc đó `deploy.ps1` (không
`-BoQuaYaml`) **dừng ở bước 1c** khi yaml trên B lệch kho — đừng vượt bằng
`-GhiDeYamlLech` trừ khi đã chủ ý bỏ cờ.

Script **chụp bản đang chạy trước khi ghi** (đó là điểm lùi của bạn) và **không tự
restart** — vì restart `llama-swap` là **unload model**, tức một quyết định vận
hành. Nó phát hiện và **nói**: nếu `llama-swap` khởi động trước lúc bạn chép thì
cấu hình vừa chép **chưa có hiệu lực**.

```powershell
ssh ... "powershell -c Restart-Service LTTLlamaSwap"   # = UNLOAD model
```

🔴 **Đo được 31/08 — vì sao bước xác nhận dưới đây không được bỏ:** tệp trên đĩa
ghi *"input public 65K"*, tiến trình khởi động **trước đó 3 phút**, và `/running`
vẫn trả *"90K"*. Ba con số, hai sự thật, **không một dòng cảnh báo nào**. Cấu hình
là mã (`bat-mot-buoc-dang-tat-cung-la-mot-thay-doi`), và một tệp cấu hình đã chép
mà chưa restart là một lời nói dối đang chờ.

Xác nhận sau restart — **ba chiều, không một chiều**:

```powershell
curl http://127.0.0.1:8280/running                     # đủ HAI model?
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv
                                                       # mỗi llama-server ở ĐÚNG card?
curl http://127.0.0.1:8299/health                      # cổng LLM thấy gì?
```

⚠️ `/running` nói **llama-swap tưởng gì**; `nvidia-smi` nói **card thật có gì**.
Hai câu khác nhau — và chính chỗ lệch giữa chúng là thứ ta đi tìm. Ghi VRAM từng
card vào `NHAT_KY.md`.

### 2.4 Máy A

Theo `docs/16_CAP_NHAT_VA_DEPLOY.md`: đồng bộ trunk → gate xanh → ff →
`setup\2-cai-dat.ps1` (**cần UAC — chủ dự án bấm**).

⛔ Đừng bao giờ sửa tệp trong `C:\LTTPlatform\app\` — lần cập nhật sau xoá sạch
**âm thầm**. Điểm lùi là `app.previous\`.

---

## 3. Residency 3090 — đọc trạng thái

Bảng `gpu_residency` (một dòng mỗi nhóm GPU, ghi đè tại chỗ, khoá lạc quan bằng
`phien_ban`). Máy trạng thái thuần ở `platform_core/llm/residency.py`; bảng chuyển
hợp lệ là `CHUYEN_HOP_LE` và **luật sống ở những chuyển nó KHÔNG chứa**.

```sql
SELECT nhom, trang_thai, tu_luc, cua_so_bat_dau, lan_nap_loi, phien_ban
FROM gpu_residency;
```

⚠️ Đúng **sáu** cột ấy, không hơn — `platform_core/models.py`. Bản nháp của spec
   có tám; hai cột bị bỏ (`thanh_vien_dang_giu`, `so_anh_trong_cua_so`) là hai cột
   **suy ra được** từ `mo_cho()` và từ bảng `jobs`, và một bộ đếm ghi tay sẽ lệch
   đúng lúc một tiến trình chết giữa cửa sổ.

Bảy trạng thái và **câu nó trả lời** (đọc thẳng từ `residency.py`, đừng chép số):

| giá trị trong CSDL | nghĩa | ai được nhận lượt mới |
|---|---|---|
| `llm` | LLM đang cư trú 3090 | lượt LLM |
| `xa_llm` | đang **xả**: ngừng nhận lượt LLM mới, chờ lượt đang chạy xong | không ai trên 3090 |
| `nha_llm` | đã drain, đang phát lệnh nhả | không ai |
| `anh` | model ảnh đang giữ card | job ảnh |
| `tra_anh` | ảnh xong, đang trả card | không ai |
| `nap_llm` | đang nạp lại LLM | không ai |
| `loi_nap` | nạp lại **thất bại** | không ai (có lùi) |

⚠️ Cột đầu là **chuỗi thật trong `gpu_residency.trang_thai`** (chữ thường), không
   phải tên hằng trong Python (`LLM`, `XA_LLM`, …). Đó cũng là chuỗi đi vào
   `/ops/jobs-metrics` và vào log — `residency.py` ghi rõ rằng đổi một giá trị ấy
   là **đổi dữ liệu đang nằm trong CSDL**.

⭐ Bất biến cốt tuỷ, đọc được từ `TRANG_THAI_MO`: **không trạng thái nào mở cửa cho
cả hai vai trò.** Hai model không bao giờ cùng nhận lượt trên một card.

⛔ **Không bao giờ giết việc đang chạy để đổi cư trú.** `XA_LLM` tồn tại chính vì
thế: `unload` thủ công của llama-swap **không drain** — nó `taskkill` và lượt đang
sinh chữ chết theo (`05_COMMUNITY_EVIDENCE.md` §1).

### `LOI_NAP` — việc cần làm khi thấy nó

`LOI_NAP` nghĩa là **lệnh nạp đã phát và máy B báo lỗi**, không phải "chưa nạp".
Máy trạng thái tự lùi và thử lại, và nó **chỉ thử lại khi không còn lượt vẽ nào
đang chạy** (lệnh nạp từ `LOI_NAP` không đi qua nhánh kiểm VRAM của `TRA_ANH`, nên
không có chốt drain thì nó sẽ nạp 16 GB lên một card đang vẽ).

Thứ tự soi, từ rẻ tới đắt:

```powershell
ssh ... "powershell -c Get-Content H:\LTT_LLM\logs\llamaswap_err.log -Tail 40"
curl http://127.0.0.1:8280/running
nvidia-smi --query-gpu=uuid,memory.used,memory.total --format=csv
```

Ba nguyên nhân đã gặp thật, theo thứ tự hay gặp:

1. **VRAM chưa về sạch** — ComfyUI giữ ngữ cảnh CUDA **kể cả khi rảnh**, và `/free`
   **không** nhả nó (L-14 §3). Cách trả card thật là **dừng hẳn dịch vụ
   LTTComfyUI** rồi bật lại (R22).
2. **Tiến trình lạ trên 3090** — `nvidia-smi --query-compute-apps` rồi đối chiếu
   danh sách hợp lệ. Desktop từng nằm trên 3090 qua phiên RDP (L-12).
3. **Cấu hình vừa chép chưa restart** — xem §2.3.

---

## 4. Sổ lượt — truy vấn để phân tích

```sql
-- Phòng chờ: ai đang chờ, chờ vì cái gì, lâu nhất bao nhiêu.
SELECT resource, lop, ly_do_cho, count(*), max(now() - created_at) AS lau_nhat
FROM llm_waiters
WHERE finished_at IS NULL
GROUP BY 1, 2, 3 ORDER BY 4 DESC;

-- Suất đang giữ theo tài nguyên (tên tài nguyên: apps/ltt_llm/ngan_sach.py).
--
-- 🔴 ĐIỀU KIỆN "ĐANG GIỮ" LÀ **NHỬP ĐẬP**, KHÔNG PHẢI MỘT CỘT `nha_luc`.
--    Bảng này không có cột nào ghi "đã nhả": lease của một worker đã chết được
--    nhận ra vì nó **thôi đập nhịp**, và `admission.acquire` thu hồi nó. Đếm mà
--    bỏ điều kiện ấy là đếm cả lease của những tiến trình không còn sống — và số
--    đó **cao hơn** sự thật, tức sai về phía "hệ thống đang đầy".
--    Hạn mồ có một nguyền: `platform_core/llm/admission.py::ORPHAN_TIMEOUT`
--    (đừng gõ lại con số vào đây; `jobs.py:227` cũng đọc chính hằng đó).
SELECT resource, count(*) FROM execution_leases
WHERE heartbeat_at >= now() - interval '20 minutes'   -- = ORPHAN_TIMEOUT
GROUP BY 1;
```

⚠️ `llm_waiters` **chưa có** cột model — Task 6.3 mới thêm. Tới lúc đó thìm `model`
   vào `GROUP BY` ở câu trên; trước đó `resource` là thứ phân biệt hai card
   (`ltt_38_3090` / `ltt_35_5060`), và nó đủ cho câu hỏi "card nào đang tắt".

Và `/ops/jobs-metrics` trên máy A cho hai khối của Task 6.3 (`llm_theo_model`,
`residency_3090`).

⚠️ `0 job` trả lời câu *"có ai chạy không"*, **không** trả lời câu *"có ai dựng
không"*. Hai câu khác nhau, và kho này đã rút sai một lần (`CLAUDE.md`).

---

## 5. Điểm lùi từng pha

| pha | điểm lùi | chi phí |
|---|---|---|
| 3 (yaml) | `xcopy` yaml cũ từ snapshot của `deploy.ps1` + `Restart-Service` | ≈ 20 s (diễn tập 18,9 s) |
| 4 (cổng máy B) | snapshot `.py` + `Restart-Service LTTLlmGateway` | vài giây |
| 5 (residency) | `app.previous\` ở máy A; snapshot máy B (còn `don_dep`/`xin_card` cũ + env cũ) | một lần cài lại |
| migration | `gpu_residency` là **cộng thêm**, vô hại với mã cũ ⇒ không cần lùi | — |

⛔ Lùi máy A mà **không** lùi máy B (hoặc ngược lại) là tự tạo lại đúng mối nguy
R21. Lùi theo **thứ tự ngược**: máy A trước, rồi cổng, rồi yaml.

---

## 6. Sáu điều không được làm

1. ⛔ Sửa tệp trực tiếp trên máy B. Mã viết ở máy A, trong repo, deploy bằng
   script. Lần deploy sau là mất trắng, **âm thầm** (Q102).
2. ⛔ Gọi `unload` thủ công của llama-swap khi còn lượt đang chạy. Drain do LTT
   làm: ngừng nhận → chờ in-flight = 0 → mới nhả (TD-D5).
3. ⛔ Coi `/free` của ComfyUI là "đã trả card" (R22).
4. ⛔ Đổi `-np`/`-c` ở một nơi. **Hai** nơi phải khớp (từ phương án C bước 3 cổng
   không còn env số — nó đọc yaml): `apps/ltt_llm/ngan_sach.py` và
   `llama-swap.yaml` — `tests/test_1201`, `tests/test_334`, `tests/test_1223`
   chốt điều đó. Thứ tự deploy theo §2.1.
5. ⛔ Bật `--load-mode none|dio` (hay `--no-mmap` trên bản cũ): mỗi lần nạp thành
   một lần đọc đĩa, và `dio` phá luôn kho ấm. `tests/test_637` canh.
6. ⛔ Mở `groups` cho hai hồ sơ **cùng một card**. Một group `swap:false` chỉ hợp lệ
   khi mỗi thành viên ghim một UUID riêng (`tests/test_637`).
