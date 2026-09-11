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
