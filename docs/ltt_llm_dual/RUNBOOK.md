# RUNBOOK — LTT LLM Dual-Model (máy A + máy B)

Tệp này dành cho **lúc đang trực**: một việc cần làm, hoặc một thứ vừa hỏng. Nó
không giải thích kiến trúc — một lượt đi qua đâu ở `BAN_DO_DUONG_DI.md` (đọc TRƯỚC khi
sửa), quyết định ở `DECISION_LOG.md`.

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

### 2.1a Đổi PHÉP ƯỚC token (L-27) — một commit đổi CẢ HAI chiều ⇒ B trước, A NGAY sau

`uoc_token.py` (A và B) làm ước **tăng** cho code/CJK/hex/emoji và **giảm** cho văn
xuôi Anh. B giữ `max(X-LTT-Token-Dat, vào_đo_B)`; A khai `vào_A + max_tokens + DEM_UOC`.
Không thứ tự nào sạch trong khe giữa hai máy — chọn khe hẹp hơn:

- **B trước (chọn):** B mới đo code dày cao hơn A cũ khai ⇒ B giữ nhiều hơn A tưởng ⇒
  429 ⇒ A xếp lại (chậm, không mất lượt). Chỉ xảy ra khi code dày > ~83K token thật
  (chênh 0,41× thật > `max_tokens` + 2.048). Ước B vượt trần vào ⇒ B đếm thật nếu
  model đã nạp; chưa nạp ⇒ 413 sau 200 (chỉ ca ~160K+ code dày).
- **A trước (không chọn):** A mới ước văn xuôi thấp hơn B cũ (1,37× vs 2,25×) ⇒ cùng
  hậu quả từ ~39K token văn xuôi — khe rộng hơn.

⇒ deploy cổng B (`llm_gateway/deploy/deploy.ps1`), rồi deploy A **ngay** sau; khe càng
ngắn càng tốt, không để qua giờ cao điểm.

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

## 2.0 Biên bản deploy 12/09/2026 — đã chuyển

Biên bản (máy B xong, máy A bị chặn vì alembic) là **lịch sử**, đã chuyển sang
`NHAT_KY_TRIEN_KHAI.md` mục *"2026-09-12 — Biên bản deploy"*. Còn ở đây phần là **thao tác**:

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

   ⚠️ Env ĐÃ GỠ (L-23, phương án C bước 3) — `LTT_LLM_MAX_DONG_THOI`,
      `LTT_LLM_TOKEN_POOL`, `LTT_LLM_RPM`, `LTT_LLM_MAX_INPUT_TOKENS` (cả dạng
      `__<model>`) — có thể còn trong tệp đó. `deploy.ps1` tự xoá theo tiền tố
      (`$tienToDaGo`) — nhưng hãy **đọc lại tệp sau khi chạy** thay vì tin rằng nó
      đã sạch: một tiến trình đang chạy vẫn giữ env cũ tới khi restart (xem §2.3);
      cổng còn thấy chúng thì chỉ log `BIEN DA GO ... van con dat` (vô hại).
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

✅ **O-19 — đóng 17/09.** Cờ `--no-cache-idle-slots` (không thuộc cấu hình — ĐÃ GỠ khỏi B) từng thấy trên `/running` máy B là
phép đo ma trận cache C1 **tạm thời** của phiên Serving V2, không phải cấu hình
production; phiên đó đã hoàn nguyên yaml trên B về bản gốc (cờ trùng kho). Còn đúng
luật chung: `deploy.ps1` (không `-BoQuaYaml`) **dừng ở bước 1c** khi yaml trên B lệch
kho — đổi yaml trên B để đo thì báo trước và hoàn nguyên ngay sau đo.

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

### 2.3b Cửa sổ bảo trì 18/09 — cái gì đã đổi trên máy B (L-24)

- `llama-swap.yaml`: `--cache-ram 24576` (L-25, thay 12288 của L-24) + `--ctx-checkpoints 8`
  cả hai model; `-b 512 -ub 512` chỉ 3.8. `-c`/`-np` không đổi. Số:
  `artifacts/bench_hang_cho/KET_QUA_BAO_TRI_18_09.md` (§2 + phụ lục L-25).
- 🔴 **`--cache-ram` ăn RAM hệ thống, và cổng B có sàn RAM.** Trọng tài từ chối **mọi**
  lượt khi RAM trống < `LTT_LLM_RAM_TRONG_GB` (**24** từ L-25; `deploy.ps1` ghi đè mỗi lần
  deploy — đừng sửa tay `gateway.env`). Dấu hiệu: `/health` → `trong_tai.ban=true`,
  `ly_do "RAM trong ... duoi nguong"`, `dem.ban_trong_tai` tăng, trong khi `/slots` cả hai
  engine rảnh. Chữa ngay: `Restart-Service LTTLlamaSwap` (xả cache RAM). Sàn chỉ **chặn lượt
  mới**, không xả cache.
- Mức bình thường sau L-25 (đo 18/09): cache rỗng ~85 GiB trống; hai cache đầy **33–35 GiB**;
  cửa sổ ảnh (3.8 nhả, cache 3.5 đầy, ComfyUI + HiDream) đáy **~58 GiB** (sàn render 48).
  Thấp hơn các mức này mà không có tải mới ⇒ có thứ khác ăn RAM trên B (VM VMware, việc AI
  khác) — tìm nó trước khi đụng cache.
- Đổi `--cache-ram`, sàn, model, hay bật thứ gì thường trú trên B ⇒ làm lại phép tính trong
  chú thích yaml; `tests/test_1293_ngan_sach_ram_may_b.py` đỏ khi ba chỗ lệch nhau.
- Đổi sàn: sửa `llm_gateway/deploy/deploy.ps1` (`$thamSoA['LTT_LLM_RAM_TRONG_GB']`) +
  `config.py` → deploy → `Restart-Service LTTLlmGateway` (cổng đọc `gateway.env` lúc khởi động).
- `LTTLlamaSwap` chạy `-watch-config`: lưu yaml ⇒ llama-swap tự nạp lại, **không** restart
  dịch vụ — nhưng v250 **nạp lại cả hai model** (cache mất) ở mọi lần lưu. Vẫn đọc
  `/running` sau khi lưu. Đổi `-c`/`-np` vẫn phải restart `LTTLlmGateway` (§2.1).
- Nhả **một** model: `curl -X POST http://127.0.0.1:8280/api/models/unload/<model>`
  (không dùng `GET /unload` — nhả tất cả). Nạp lại: một lượt gọi model đó (~16 s cho 3.5).
- `deploy.ps1` bước 1c sẽ dừng khi yaml B lệch kho — kể cả lệch chỉ ở chú thích (18/09
  trước cửa sổ: B thiếu các chú thích Phương án C/O-19, cờ trùng khít). So cờ trước khi
  dùng `-GhiDeYamlLech`.

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

## 4b. Kiểm định kỳ — chạy lại sau MỖI lần nâng llama.cpp (plan v2 Task 10)

**Khi nào:** ngay sau mỗi lần đổi bản ghim `llm_gateway/deploy/phien_ban_ghim.json` (`nang_llamacpp.ps1`) —
trước khi mở lại cho khách hoặc trong cửa sổ vắng đầu tiên; và sau mỗi lần đổi `-np`/`-kvu`/`--cache-ram`/
`--spec-type` trong `llama-swap.yaml`. Ngoài ra `tong_hop_ttft_b.py` mỗi tuần.

Đường vào chung: `ssh -N -L <cổng>:127.0.0.1:8280 lengo@192.168.2.66` (gọi thẳng llama-swap, **không** qua
8299, không tốn credit). Trước mỗi khúc đếm kết nối khách vào 8299 (ngoài loopback) — > 0 thì chờ. Không đổi cờ.

| # | công cụ | lỗi thượng nguồn nó canh | đạt | lần gốc |
|---|---|---|---|---|
| 1 | `tools/kiem_co_lap_llm.py` (≥ 200 lượt/model, cả `dong_thoi_lru_27148`) | #27148 rò nội dung giữa phiên (pool RAM + LRU), #28286/#26425 MTP × np | 0 rò | `artifacts/KIEM_CO_LAP_18_09.md` |
| 2 | `tools/kim_ngu_canh_dai.py --model qwen38-api` ở **đúng các độ sâu phục vụ** (100K → trần vào `tran_vao_cua`) | #27756 EOS im lặng / quên sự kiện ở ngữ cảnh dài (GDN 48 lớp); lỗ **không đơn điệu** ⇒ đo nhiều độ sâu | 4/4 sự kiện mọi độ sâu | `artifacts/bench_hang_cho/KET_QUA_NEEDLE_MTP_18_09.md` |
| 3 | `tools/cong_mtp.py` mỗi model, `--song-song 2` | MTP × np trả rỗng/hỏng nội dung, rò slot, deadlock | cổng `dat` | như trên |
| 4 | `tools/ab_lay_mau_35.py chay` (chỉ biến thể A đủ làm mốc) | tụt chất lượng 3.5 do engine đổi | A không tụt so với mốc | `artifacts/bench_hang_cho/SAMPLING_35_MODEL_CARD_18_09.md` |
| 5 | `tools/tong_hop_ttft_b.py` trên `H:\LTT_LLM\logs\gateway_err*.log` + `llamaswap*.log` | TTFT p95 trôi, nạp nguội (TTL `llama-swap.yaml`) | so với lần trước (chưa có ngưỡng) | R-16, cùng tệp needle |

Một mục đỏ ⇒ không mở bản llama.cpp mới cho khách; lùi bản ghim (`nang_llamacpp.ps1 -Ban <bản cũ>`, tường minh).

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

---

## 7. Cảnh báo R-16 — TTFT stream và nạp nguội theo ngày (`tools/canh_bao_ttft_b.py`)

Chạy trên **máy A**, đọc sổ lượt cổng B (`H:\LTT_LLM\logs\gateway_err*.log`) **chỉ đọc** qua đường vào
§1, dùng lại bộ đọc/phân vị/TTL của `tools/tong_hop_ttft_b.py`. Ngưỡng = đề xuất R-16 (giữ nguyên):
TTFT stream **ấm** p95/ngày > 45 s (cần ≥ 20 lượt ấm), hoặc > 5 lượt nạp nguội/ngày/model có TTFT > 20 s
(chỉ cửa stream — cửa đồng bộ ghi cả lượt). Kênh: thư người trực của `ops_alerts` (`platform_core.mailer`
→ `LTT_OPS_ALERT_EMAIL`; vắng ⇒ tắt mềm). Mỗi (ngày, model, điều kiện) gửi **một** lần — trạng thái ở
`data_path("canh_bao", "ttft_b.json")`.

```powershell
python tools\canh_bao_ttft_b.py                     # hôm qua, CHẠY THỬ: in số, không gửi, không ghi trạng thái
python tools\canh_bao_ttft_b.py --ngay 2026-09-18   # một ngày (giờ máy B)
python tools\canh_bao_ttft_b.py --gui               # gửi nếu vượt (bản chạy theo lịch)
# Đặt lịch (chủ máy làm, công cụ không tự đặt):
schtasks /Create /TN "LTT canh bao TTFT B" /SC DAILY /ST 07:15 /TR "C:\LTTPlatform\venv\Scripts\python.exe C:\LTTPlatform\app\tools\canh_bao_ttft_b.py --gui"
```

Mã thoát: 0 không vượt · 1 có vượt (đã gửi / chạy thử / đã gửi trước đó) · 2 không đọc được sổ hoặc gửi thư
hỏng (chưa ghi trạng thái ⇒ lần sau gửi lại). Tài khoản chạy lịch phải đọc được `secrets\app.env` và có
`~\.ssh\nexus_b`.

Đọc số đúng: `ttft_s` đo từ lúc **cổng B** nhận lượt ⇒ **không** gồm thời gian chờ ở máy A
(`llm_waiters`, `whale_cho_prefill` của L-29). Nạp nguội suy từ sổ (khoảng lặng > TTL); `llamaswap.log`
không đếm theo ngày được vì llama-swap v250 chỉ in giờ khi đặt `logTimeFormat` (mặc định rỗng) — yaml
của ta không đặt. Số thật 16–18/09 (chạy thử): p95 ấm 31,6/32,9 s → 11,0/11,3 s (18/09); nạp nguội > 20 s
tối đa 4/ngày (3.8) ⇒ không ngày nào vượt.
