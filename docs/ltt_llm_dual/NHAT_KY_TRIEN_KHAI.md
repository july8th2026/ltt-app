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
