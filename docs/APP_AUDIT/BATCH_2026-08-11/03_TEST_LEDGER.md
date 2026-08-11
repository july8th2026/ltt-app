# H32.7 — Test và evidence ledger cuối batch

## Full gate

Lệnh duy nhất theo AGENTS:

```powershell
python tools\gate.py
```

Kết quả ngày 2026-08-11: **PASS 9/9**, tổng **1.777 giây**.

| Bước | Kết quả | Thời gian |
|---|---|---:|
| Secret scan | PASS | 5,2s |
| App contract lint | PASS | 0,1s |
| Undefined names | PASS | 1,2s |
| Silent exception guard | PASS | 0,6s |
| i18n guard | PASS | 0,9s |
| agent-canvas Vitest | PASS | 21,5s |
| autosub-studio Vitest | PASS | 6,0s |
| prompt-ai-ommi Vitest | PASS | 6,8s |
| Full pytest | PASS | 1.734,2s |

Gate runner không in số lượng test khi PASS vì chỉ giữ tail output; không suy
đoán count từ lần trước. Bằng chứng có thẩm quyền là exit code 0 và bảng 9/9.

## Browser ledger

| App | Viewport/state cuối | Console | Network app | Evidence |
|---|---|---:|---:|---|
| AutoSub | desktop + 390px, upload→render→download | 0 | 0 failed | hồ sơ autosub H32 |
| Prompt AI | desktop + 390px, brief→preview→quote | 0 | 0 failed | hồ sơ OMMI H32 |
| Tạo ảnh | desktop + 390px, General/Thumbnail/edit/remix | 0 | 0 failed | hồ sơ taoanh H32 |
| Tạo Clip | desktop + 390px, source→job→output/package | 0 | 0 failed | hồ sơ clip H32 |
| Seedance | 1586×992 + 390×844, multi-state/quote negative | 0 | 0 failed | hồ sơ taovideo H32 |
| Upscale | 1586×992 + 390×844, actual upload/batch/history | 0 | 0 failed | hồ sơ upscale H32 |

Mỗi browser pass được chạy sau thay đổi cuối của app tương ứng. Thay đổi dùng
chung cuối batch chỉ thêm CSS `.up-*` scoped cho Upscale, nên không làm thay đổi
bề mặt năm app trước. Production 8100 không được dùng làm bằng chứng cho source
chưa deploy.

## Kết luận nghiệm thu source

- Source gate: **PASS**.
- Browser gate phạm vi H32: **PASS**.
- Product/commercial gate: **BLOCKED** theo `01_RELEASE_AUDIT.md`.
- Deployment: **chưa chạy, không được H32 tự động thực hiện**.
