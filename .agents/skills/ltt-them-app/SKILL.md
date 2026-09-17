---
name: ltt-them-app
description: Dùng khi thêm, di trú hoặc tái cấu trúc một app dưới apps/ của LTTSTUDIOSAPP — hợp đồng thư mục app (manifest, routes, jobs, services), giá credit, việc dài qua hàng đợi job, cấm sửa platform_core/server. Trỏ về docs/03_THEM_APP_MOI.md và AGENTS.md §8.
---

# Thêm app — LTTSTUDIOSAPP

Nguồn: `docs/03_THEM_APP_MOI.md` (khuôn manifest/jobs/routes, kiểm tra) ·
`AGENTS.md` §2 (ranh giới), §8 (bố cục mã, ngưỡng lint, bốn module `server`).

## Luật lõi

- **Thêm app = thêm MỘT thư mục `apps/<slug>/`.** Buộc sửa `platform_core/` hoặc
  `server/` ⇒ **dừng và nói rõ vì sao** — hợp đồng app còn thiếu (`AGENTS.md` §2.3).
- Bố cục trong app: `AGENTS.md` §8.1 (nguồn chân lý, đừng chép danh sách).
  `routes.py` chỉ lo HTTP; nghiệp vụ ở `services/` hoặc `features.py`; bảng CSDL ở
  `tables.py` (không phải `models.py`).
- Ngưỡng `routes.py`: hằng trong `tools/lint_app_contract.py` — không chép số.
- App chỉ dùng đúng các module `server` liệt kê ở `AGENTS.md` §8.2b.
- `platform_core` không được biết tên app nào (§8.4).
- Có `job_types` thì phải có `credit_cost` — thiếu giá thì nền tảng từ chối job.
- Việc dài hơn vài giây đi qua **hàng đợi job** (Cloudflare cắt phản hồi 100 s,
  upload 100 MB).
- Route trong app viết đường dẫn **tương đối** (không lặp prefix).
- API key lấy qua pool/credential, **không** đọc biến môi trường — mục 2b.
- Đường dẫn dữ liệu qua `platform_core.runtime_paths.data_path()` (`AGENTS.md` §5.4).
- Template đặt ở `apps/<slug>/templates/`; prompt ghép bằng
  `platform_core.prompt_fragments`, cấm hardcode chuỗi prompt trong `jobs.py`.
- **Di trú** từ `D:\BOT GEMINI` (chỉ đọc): theo `CONG_THUC_DI_TRU_APP.md`, parity
  ≥ 90% — không tự tối giản.

## Kiểm

```powershell
python tools\thanh_phan.py --test app:<slug>
python -m pytest tests\test_60_app_registry.py <các tệp vừa in ra> -q
python tools\lint_app_contract.py
```

Nhịp test/gate: skill `ltt-test-nham`, `ltt-gate`. App có giao diện ⇒ kiểm trình
duyệt (hợp đồng §9).
