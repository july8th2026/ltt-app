# bench/ — bằng chứng đo của H37

Nơi giữ **số đo** của hạng mục H37 (model tạo ảnh nội bộ trên máy B).
Kế hoạch: [`docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md`](../docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md).

## Vì sao số đo nằm ở máy A chứ không ở máy B

Máy B là **máy chạy**, không phải nơi lưu trữ chân lý. Nó có thể bị cài lại, bị dọn
dẹp, bị đổi (đã xảy ra một lần: node `MAY-B` cũ ở `192.168.2.2` nay `REVOKED`, máy
hiện tại là bản cài lại ở `192.168.2.66`). Số đo mất theo máy thì phase phải đo lại
từ đầu.

Vì vậy: **đo trên B, ghi về A, commit vào git.**

## Cái gì commit, cái gì không

| Commit | Không commit |
|---|---|
| `*.json` — số đo, tham số, kết quả | `*.png` / `*.jpg` — ảnh sinh ra |
| `*.md` — biên bản, kết luận | `*.safetensors` / `*.gguf` — trọng số |
| `prompts_*.json` — bộ prompt chuẩn | `gallery/` — ảnh so sánh |

Ảnh và trọng số là **dữ liệu**, không phải mã. Chúng nằm ở
`E:\AI\ltt_render\bench\` trên máy B và trên R2 nếu cần giữ lâu.
`.gitignore` đã chặn sẵn.

## Bố cục

```
bench/
├── README.md                 tệp này
├── G1_phan_cung.json         PCIe link · tốc độ đĩa E: · mốc metrics hai máy
├── G1_gpu_check.txt          kết quả gpu_check.py (có phép tensor thật)
├── G3_baseline.json          5 ca baseline: seed · thời gian · VRAM đỉnh · nhiệt
├── prompts_30.json           bộ 30 prompt cố định của G4
├── G4_benchmark.json         5 chiến lược × 30 prompt × ≥3 lần đo
├── G5_edit_reference.json    6 loại × 10 ca
├── G9_stress.json            100 lượt · memory drift · P95 · kịch bản tranh chấp
└── G11_doi_chung.json        vote mù với Gemini, mở khoá tên model sau khi vote
```

## Quy tắc bắt buộc với mọi tệp số đo

1. **Mỗi số phải kèm điều kiện đo**: ngày, phiên bản model, phiên bản ComfyUI
   (commit ghim `6f7cd7f`), profile, seed, và **máy có đang độc chiếm không**.
2. **Đo một lần không phải đo.** G4 tối thiểu 3 lần, lấy trung vị — luật ở
   `KE_HOACH_THI_HANH.md` §1.3 (trần điểm cứng).
3. **Số bẩn phải bị vứt, không phải chú thích.** Nếu có lượt video chen vào giữa
   thì đo lại; đừng giữ số kèm dòng "lúc này máy hơi bận".
