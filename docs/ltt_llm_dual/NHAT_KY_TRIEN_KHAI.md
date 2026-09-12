# Nhật ký triển khai — LTT LLM Dual-Model

> Chỉ ghi **việc đã làm trên máy thật** kèm bằng chứng. Quyết định ở `DECISION_LOG.md`;
> plan ở `docs/superpowers/plans/2026-09-11-ltt-llm-dual-model.md`.

## 2026-09-11 — Task 0.1 + 0.2: ghim GPU trên máy B

**Kênh.** OpenSSH (`ssh -i %USERPROFILE%/.ssh/nexus_b lengo@192.168.2.66`) — đo 11/09: sshd
`Running/Automatic`, đăng nhập khoá 0,37–0,47 s, `lengo` thuộc Administrators. Nexus là kênh dự phòng.
`Ket_noi.md` đã sinh lại (bộ sinh nay **thử đăng nhập thật** rồi mới kết luận).

**`deploy.ps1` — đọc, và vì sao KHÔNG chạy.** Nó chụp thư mục `gateway` sang `releases/auto-<ts>`,
scp **cả cây** gateway + `llama-swap.yaml`, kiểm hash các tệp `.py`, sửa `gateway.env` tại chỗ (ép
`LTT_LLM_MAX_DONG_THOI`), và **không** restart `LTTLlamaSwap`.
⛔ Máy B đang chạy gateway của **nhánh khác** (`claude/ltt-llm-master-upgrade-ddcfc9` @ `de97e8d0`,
một commit ngoài trunk): có `llm_gateway/dem.py` (+182), `api.py` +166, `config.py` +35, `main.py` +54,
`upstream.py` +32. Chạy `deploy.ps1` từ nhánh này sẽ **xoá** việc đó ⇒ Ruling R11: chỉ scp riêng yaml.

**Đã làm.**

| Việc | Bằng chứng |
|---|---|
| Snapshot trước khi đè | thư mục `releases/auto-20260911-194730` (yaml + env ComfyUI trước) |
| Kiểm rảnh trước khi đụng | `/running` = `{"running":[]}`, ComfyUI `/queue` trống, GPU 0 % |
| scp `llama-swap.yaml` | sha256 trên máy B = `209C802F8B25CE7520D3EDB69C7E706414E9D4BC0D599DE317F4DCDF1BC5E628` = đúng bản của nhánh (trước đó `8A9362F6…`) |
| Ghim ComfyUI | `AppEnvironmentExtra REG_MULTI_SZ CUDA_VISIBLE_DEVICES=GPU-26623278-4fa5-82db-4306-237651b03e78` |
| Restart (R13) | Stop phụ thuộc **tường minh** rồi start lại: `LTTRenderGateway` ← `LTTComfyUI`, `LTTLlmGateway` ← `LTTLlamaSwap`; cả bốn `Running` |

**Nghiệm thu (20:23).**

```
ComfyUI   : Device: cuda:0 NVIDIA GeForce RTX 3090   (khong con dong RTX 5060 Ti)
llama-swap: POST /v1/chat/completions model=qwen38-api -> 200, system_fingerprint b10883-91f6a6cf3
nvidia-smi: llama-server.exe CHI o GPU-26623278-...   (5060 Ti: khong co tien trinh tinh toan)
VRAM      : 3090 21.873 MiB (model da nap) | 5060 Ti 54 MiB
Cong      : llm_gateway /live = 200 | render_gateway /health = 401 (co xac thuc, dang phuc vu)
```

**Còn nợ.** Ngữ cảnh đồ hoạ desktop (dwm, explorer, SearchHost, M365Copilot, LGHUB, Taskmgr…) **vẫn**
mở trên 3090 ⇒ L-12 chưa đạt; đo và xử ở Task 0.3.

**Đường lùi.** Chép `llama-swap.yaml` từ `releases/auto-20260911-194730` về thư mục `gateway`,
`nssm reset LTTComfyUI AppEnvironmentExtra`, restart bốn dịch vụ theo đúng thứ tự phụ thuộc ở trên.

## 2026-09-11 — Task 0.3: đo VRAM nền trên 3090 (L-12)

Đo bằng `Get-Counter "\GPU Process Memory(*)\Dedicated Usage"` + `nvidia-smi --query-compute-apps`
(script: `E:/AI/ltt_dual/do_vram_nen.ps1`), lúc `qwen38-api` đang nạp.

| Trên 3090 (UUID `GPU-26623278-…`) | MiB |
|---|---:|
| `llama-server` (model) | 21.493 |
| `python` = ComfyUI thường trú — **hợp lệ** theo L-11 | 224 |
| Ngữ cảnh desktop: explorer 50,8 · dwm 24,8 · LGHUB 30,1 · M365Copilot 26,6 · StartMenu 13,2 · TextInputHost 10,3 · SearchHost 9,6 · Taskmgr 9,5 · ShellHost 9,3 · PhoneExperienceHost 9,2 · System 8,3 · csrss 3,4 | **≈ 205** |

Hai dữ kiện kèm theo:

- Máy B đang truy cập qua **RDP** (`Microsoft Remote Display Adapter 1920×1080`); màn hình vật lý ở
  5060 Ti (1024×768); 3090 **không** xuất hình. Vì vậy vẫn còn một `dwm` trên 3090 (phiên RDP) bên
  cạnh `dwm` của phiên console trên 5060 Ti.
- ⚠️ `llama-server` có **Shared Usage 568 MiB** (tràn WDDM sang RAM) — `nvidia-smi` **không** hiện con
  số này. Mọi phép đo VRAM về sau (Task 3.2) phải đọc thêm bộ đếm này, nếu không sẽ kết luận "vừa card"
  trong khi thực tế đã tràn.

**Ruling R16 — chưa đụng cài đặt đồ hoạ Windows.** 205 MiB nhỏ so với biên cần cho 262.144, và việc
chuyển ưu tiên GPU của ứng dụng desktop là thay đổi cài đặt hệ thống cần chủ dự án. Để **cổng đo G1**
(Task 3.2) phán xử: nạp được cấu hình đầy đủ ⇒ L-12 coi như đạt; thiếu trong khoảng vài trăm MiB ⇒
quay lại dọn desktop rồi đo lại.

## 2026-09-11 — Task 0.4: mốc hồi quy b10883 (cổng nghiệm thu B)

Khuôn đo mới `docs/ltt_llm_dual/artifacts/bench/bench.py` (tổng quát hoá từ `docs/multijob/artifacts/m1/`),
chạy qua llama-swap loopback trên máy B, **không** restart gì, **không** đổi `-np`.

Danh tính đo được: `system_fingerprint b10883-91f6a6cf3` · GGUF sha256 `322E194F…39123482` ·
UUID 3090 `GPU-26623278-…` · hồ sơ production `qwen38-api` (`-np 1`, `-c 204800`, KV q4_0, draft-mtp).

| # | decode tok/s | TTFT (s) | tok vào | tok ra | VRAM (MiB) | Shared (MiB) | W tb |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 65,91 | 2,162 | 1.982 | 600 | 21.893 | 568,0 | 355,3 |
| 2 | 62,50 | 1,959 | 2.039 | 600 | 21.893 | 568,0 | 315,2 |
| 3 | 65,83 | 2,027 | 1.993 | 600 | 21.893 | 568,0 | 360,5 |
| 4 | 66,13 | 1,951 | 2.019 | 600 | 21.893 | 568,0 | 356,9 |
| 5 | 71,80 | 1,948 | 2.014 | 600 | 21.893 | 568,0 | 357,1 |
| **Trung vị** | **65,91** | **1,959** | 2.014 | 600 | 21.893 | 568,0 | 356,9 |

⇒ **Ngưỡng cổng B (C1 ≥ 90 % mốc) = 59,3 tok/s decode.** Con số này thay mốc cũ 54 tok/s của TD-14
(đo trên b10689) — cùng phép đo, build mới.

Hạn chế đã khai (đừng đọc rộng hơn số): `khoi_dong.ps1` (Scheduled Task) **chưa** chạy thử đầu-cuối —
lượt này đi thẳng qua SSH đồng bộ vì chỉ ~1 phút; `bench.py` ước cỡ prompt bằng số từ chứ không qua
`/tokenize` nên token vào dao động 1.982–2.039; `power_w_tb` là trung bình lấy mẫu ~1 s, không phải đỉnh;
sha GGUF là hằng số chép từ `00_CURRENT_BASELINE.md`, phải sửa tay nếu đổi model; máy B **không** có
`cua_so_yen` nên "rảnh" được xác nhận bằng `/running` + `/slots` trước/trong/sau.

## 2026-09-11 — Tối ưu 3090: dọn TOÀN BỘ desktop sang 5060 Ti (L-12 đạt)

**Nguyên nhân thật, đo được.** LUID `0x38cc5f` = 3090, `0x37fdf5` = 5060 Ti. Mọi tiến trình desktop
nằm trên 3090 đều thuộc **session 2 = phiên RDP** (`rdp-tcp#0`, user `lengo`): explorer 50,8 · dwm 24,8 ·
LGHUB 30,1 · M365Copilot 26,6 · StartMenu 13,2 · TextInputHost 10,3 · SearchHost 9,6 · Taskmgr 9,6 ·
ShellHost 9,3 · PhoneExperienceHost 9,2 ≈ **193 MiB**. Phiên console (session 1, màn hình vật lý) **đã**
ở 5060 Ti. ⇒ Không phải "ứng dụng cài lung tung": **phiên Remote Desktop dựng hình trên card mạnh nhất**.

**Đã làm (2 bước, đều lùi được).**

1. Chính sách RDS: `HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services` →
   `fUseHardwareDefaultGraphicsAdapter = 1` (DWORD) — phiên RDS dùng adapter mặc định phần cứng thay vì
   tự chọn card mạnh nhất.
   **Lùi:** `Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name fUseHardwareDefaultGraphicsAdapter`
2. `logoff 2` — đóng phiên RDP để giải phóng ngay. Dịch vụ (session 0: llama-swap, hai gateway, ComfyUI)
   **không** bị ảnh hưởng.

**Sau khi dọn (đo lại).**

| Trên 3090 | MiB |
|---|---:|
| `llama-server` | 21.512,7 |
| `python` = ComfyUI (model ảnh, hợp lệ L-11) | 223,5 |
| `System` | 4,0 |
| **Desktop** | **0** |

`nvidia-smi`: 3090 dùng 21.735 MiB, **trống 2.591 MiB**; 5060 Ti 54 MiB. Toàn bộ desktop (dwm, LogonUI,
csrss) nay ở 5060 Ti.

**Mốc C1 CHÍNH THỨC (đo sau tối ưu, cùng khuôn `bench.py`, hồ sơ production b10883):**

| # | decode tok/s | TTFT (s) | prefill tok/s | tok vào | VRAM (MiB) | W tb |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 66,91 | 2,257 | 1.024,7 | 2.035 | 21.735 | 317,9 |
| 2 | 66,70 | 2,077 | 1.073,0 | 2.020 | 21.735 | 360,0 |
| 3 | 71,45 | 1,953 | 1.150,4 | 2.024 | 21.735 | 355,7 |
| 4 | 60,96 | 1,959 | 1.141,8 | 2.006 | 21.807 | 353,1 |
| 5 | 63,99 | 2,002 | 1.127,1 | 2.012 | 21.826 | 357,5 |
| **Trung vị** | **66,70** | **2,002** | 1.127,1 | 2.019 | 21.735 | 355,7 |

⇒ **Ngưỡng cổng nghiệm thu B = 60,0 tok/s** (90 % của 66,70). Dọn desktop **không** đổi tốc độ (193 MiB
là sức chứa, không phải băng thông) — giá trị của nó nằm ở phép thử 262.144.

**Đầu vào cho thiết kế P5.** ComfyUI vẫn giữ **223,5 MiB** ngữ cảnh CUDA trên 3090 kể cả khi rảnh; `/free`
chỉ nhả **model**, không nhả ngữ cảnh. Muốn 3090 thật sự 100 % cho LLM trong cửa sổ LLM thì trọng tài
residency phải **dừng hẳn dịch vụ `LTTComfyUI`** rồi bật lại cho cửa sổ ảnh, chứ không chỉ gọi `/free`.
Ghi vào Task 5.4/5.5 để cân nhắc (giá phải trả: thời gian khởi động ComfyUI).

### Ba nút đã thử, và nút nào thật sự ăn (đo từng bước)

Mục tiêu chủ dự án: 3090 dành **100 %** cho model. Ba nút, đo sau mỗi nút:

| # | Nút | Kết quả đo |
|---|---|---|
| 1 | `fUseHardwareDefaultGraphicsAdapter = 1` (policy RDS) + `logoff` | **Không ăn** cho phiên RDP mới: session 3 vẫn dựng hình trên 3090 (~107 MiB) |
| 2 | `fEnableWddmDriver = 0` (policy RDS) + đăng nhập phiên MỚI | **Ăn một phần**: `dwm` biến mất khỏi 3090; còn từng app tự chọn card mạnh: explorer, TextInputHost, Taskmgr, SearchHost, ShellHost, CrossDeviceResume, PhoneExperienceHost ≈ **60 MiB** |
| 3 | Ghim 10 app vào 5060 Ti: `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` = `GpuPreference=1;` (Power saving) + đăng xuất | *(đo sau khi chủ dự án đăng nhập lại)* |

⚠️ **Nối lại phiên RDP KHÔNG phải tạo phiên mới.** Chính sách chỉ áp lúc phiên được tạo; bấm Sign out
(hoặc `logoff <id>`) mới có phiên mới. Đã mất một vòng đo vì chuyện này.

**Đường lùi cho cả ba nút.**

```
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name fUseHardwareDefaultGraphicsAdapter
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name fEnableWddmDriver
Remove-Item -Path "HKCU:\Software\Microsoft\DirectX\UserGpuPreferences" -Recurse
```

**Vì sao KHÔNG chuyển ComfyUI sang 5060 Ti** (câu hỏi của chủ dự án 11/09): model ảnh đo đỉnh
**18.450 MiB** (t2i) và **20.000 MiB** khi có ảnh tham chiếu (`docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md` §1),
trong khi 5060 Ti chỉ có **16.311 MiB** — không vừa, kể cả khi card trống; và LTT-3.5 sẽ chiếm ~13,7 GiB
trên chính card đó (D06). Muốn chuyển phải lượng tử hoá model ảnh (fp8/GGUF) — ngoài phạm vi Spec 1.
Đây chính là lý do L-11 giữ model ảnh trên 3090.

**Tại sao 5060 Ti chỉ dùng 54 MiB:** trên đó hiện chưa có gì chạy — LTT-3.5 chưa tải (Task 3.1), và
desktop thì tới nút 3 mới được ghim sang. Con số 54 MiB là đúng, không phải dấu hiệu "chưa chuyển hết".

### Kết quả cuối của việc dọn 3090 (chốt 2026-09-11)

Sau nút 3 (ghim app vào 5060 Ti) + đăng nhập phiên mới: `explorer` và `dwm` **đã rời** 3090.
Còn lại trên 3090: TextInputHost 10,4 · Taskmgr 9,5 · SearchHost 9,3 · PhoneExperienceHost 9,2 ·
ShellHost 9,2 · CrossDeviceResume 9,2 ≈ **47 MiB** (đều là app hệ thống kiểu UWP, không tôn trọng
`UserGpuPreferences`). 

**193 MiB → 47 MiB (−76 %).** Chủ dự án chốt dừng ở đây ("mặc kệ đi"). VRAM 3090: dùng 21.862 MiB,
**trống 2.464 MiB** với model 204.800 đang nạp.

⭐ **L-13 (chủ dự án, cùng lúc):** 3090 chỉ dùng cho model AI, và LTT-3.8 phải lấy **trần ngữ cảnh tối
đa** — nếu 262.144 vừa 24 GB thì **không hạ** số token. Cổng đo G1 (Task 3.2) vì vậy đo theo thứ tự:
262.144 trước, và chỉ báo cáo con số thấp hơn nếu phép đo chứng minh không vừa.

---

## Task 3.1 — Tải Qwen3.5-9B Q6_K + mmproj về máy B (2026-09-11 21:32–21:40)

Chạy sớm hơn thứ tự trong kế hoạch: đây là việc **chờ mạng**, không chạm mã, nên cho nó chạy
song song với Task 2.2 thay vì để nó chặn P3.

### Bước 1 — sha256 lấy từ máy, không chép tay

`lfs.oid` mà HuggingFace API trả về **chính là** sha256 của tệp, nên `Get-FileHash -Algorithm
SHA256` đối chiếu thẳng được. Không có chỗ nào phải tin một con số gõ lại.

| Kho | Tệp | Byte | sha256 |
|---|---|---:|---|
| `unsloth/Qwen3.5-9B-MTP-GGUF` | `Qwen3.5-9B-Q6_K.gguf` | 7.684.551.008 | `8AE8FD04E30C5A4AF3EF72654729FB0D7F33615CAC1BA335DD88084A56287934` |
| `unsloth/Qwen3.5-9B-MTP-GGUF` | `mmproj-F16.gguf` | 918.165.984 | `5A40D1F771686432172A4981018A0D30D03A5AAF5793A5BADD5416573362A232` |
| `lmstudio-community/Qwen3.5-9B-GGUF` | `Qwen3.5-9B-Q6_K.gguf` | 7.359.259.040 | `B2CCC477F0A2449DE299BEF560B63E498CAE94A2F3A3BAE13DF01168D77773E6` |
| `lmstudio-community/Qwen3.5-9B-GGUF` | `mmproj-Qwen3.5-9B-BF16.gguf` | 921.704.480 | `330D17547BFDBCD0E7A0CB3F4B06B4CEEAC0AAA1E449122D9D66EF957AEB74B3` |

Tải **cả hai** ứng viên Q6_K vì cổng G3 (Task 3.2) phải chọn một bằng **đo** VRAM đỉnh trên
5060 Ti + chấm chất lượng, không chọn trước bằng suy luận. Hai tệp lệch nhau 325 MB.

⚠️ `mmproj-F16.gguf` của unsloth **trùng tên** với mmproj của bản 27B đang nằm trên
`H:\LTT_LLM\models` (927.607.488 B, `CBB841A9…`). Ghi đè là mất mmproj của LTT-3.8 mà không ai
biết cho tới lần nạp sau. Script lưu dưới tên `mmproj-9B-F16-unsloth.gguf`.

### Bước 2 — chạy bằng Scheduled Task SYSTEM

`E:\AI\ltt_dual\tai_model.ps1` (bản trong kho: `docs/ltt_llm_dual/artifacts/bench/tai_model.ps1`),
đăng ký `schtasks /tn LTT_Tai_Model_35 /ru SYSTEM`. **Không** chạy thẳng qua ssh: phiên ssh đứt
thì tiến trình con bị giết giữa chừng ~17 GB. Script chạy lại được — tệp nào đúng hash thì bỏ qua.

Task để lại trên máy B (kiểu `ONCE` giờ đã qua nên không tự chạy lại) để lần sau tải bổ sung chỉ
cần `schtasks /run`.

### Bước 3 — kết quả

```
21:36:01  XONG  Qwen3.5-9B-Q6_K-unsloth.gguf   7684551008 byte / 235 s
21:36:45  XONG  mmproj-9B-F16-unsloth.gguf      918165984 byte / 10,7 s
21:38:48  XONG  Qwen3.5-9B-Q6_K-lmstudio.gguf  7359259040 byte / 119,3 s
21:40:44  XONG  mmproj-9B-BF16-lmstudio.gguf    921704480 byte / 84,1 s
=== KET THUC === 0 loi
```

Cả 4 tệp: số byte khớp, sha256 khớp oid. 16,9 GB trong 8,7 phút (~32 MB/s). `H:` còn 507 GB trống.

⇒ Task 3.1 xong. Cổng đo Task 3.2 đã có đủ tệp để chạy G3 (hai ứng viên) và G1 (bản 27B sẵn có).
