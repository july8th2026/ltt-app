# Giao thức đo trạng thái thật của code

> Chạy TRƯỚC khi tin tài liệu hoặc thiết kế thêm hạ tầng. Tất cả lệnh dưới đây
> dành cho PowerShell tại `D:\LTTSTUDIOSAPP`; không dùng Bash và không dùng
> Python inline qua PowerShell.

## A. Bảy phép đo cốt lõi

### A1 — Inventory app và hợp đồng khai báo

```powershell
Get-ChildItem apps -Directory | ForEach-Object {
  $m = Join-Path $_.FullName "manifest.py"
  if (Test-Path $m) {
    Write-Host "`n=== $($_.Name) ==="
    rg -n "slug=|route_prefix=|job_types=|requires=|credit_cost=|tools=" $m
  }
}
```

Kiểm số app, job type, capability và `tools`. `tools` chưa có nghĩa là thiếu
metadata agent; không có nghĩa handler/job/runtime chưa tồn tại.

### A2 — Các mảnh ghép agent và storage

```powershell
rg -n "class ToolSpec|tools:" platform_core/registry.py
rg -n "parent_id|plan_id|step_id|agent_runs" platform_core/models.py alembic/versions
rg -n "def url_for|def put_url|class R2Storage" platform_core/storage.py
Test-Path platform_core/agent
```

| Kết quả | Nghĩa |
|---|---|
| không có `ToolSpec` | chưa có metadata tool cho planner |
| không có cột cha/plan/step | chưa có checkpoint/fan-out cấp agent |
| có `url_for` + `put_url` + `R2Storage` | file lớn đã có đường tải xuống/tải lên trực tiếp |
| chưa có `platform_core/agent` | chưa có planner/validator/executor agent |

### A3 — Quy mô và tài nguyên từng app

```powershell
Get-ChildItem apps -Directory | ForEach-Object {
  $py = Get-ChildItem $_.FullName -Recurse -Filter *.py
  $prompts = Get-ChildItem $_.FullName -Recurse -Filter *.txt
  $ui = Test-Path (Join-Path $_.FullName "templates")
  "{0}: {1} file Python, {2} prompt, UI={3}" -f $_.Name,$py.Count,$prompts.Count,$ui
}
```

Không suy ra parity chỉ từ số dòng. Đọc manifest, route, handler và test của app.

### A4 — Lược đồ CSDL và migration

```powershell
Get-ChildItem alembic/versions/*.py | Sort-Object Name | Select-Object -Last 5 -ExpandProperty Name
rg -n "^class (Job|CreditEntry|ApiKey|PaymentOrder|ChatConversation|ChatMessage)" platform_core/models.py
```

### A5 — Cổng chất lượng

```powershell
python -m pytest -q --collect-only
python -m pytest -q
python tools\scan_source_secrets.py
python tools\lint_app_contract.py --strict
```

Chưa xanh thì không mở hạng mục mới. Ghi đúng kết quả thật, không suy từ số test
collect được. Linter chỉ bắt lỗi cơ học, không thay review nghiệp vụ/browser.

### A6 — Việc vừa xảy ra

```powershell
git log --oneline -12
git status --short
Get-Content docs/NHAT_KY.md -TotalCount 140
```

Nhật ký ghi mục mới ở đầu file. Không dùng `tail` để tìm việc gần nhất.

### A7 — Kiểm kê primitive dùng lại trước khi thiết kế

```powershell
rg -n "^(def|class) " platform_core
rg -n "submit_with_credit|get_storage|put_url|url_for|api_pool|prompt_fragments|platform_core.media" apps
rg -n "submit_upscale_job|sidecar_client|run_with_progress" apps codex_sidecar
```

Lập bảng trước khi đề xuất:

| Nhu cầu | Implementation đã có | Khoảng trống thật | Quyết định |
|---|---|---|---|
| ví dụ: upload video lớn | `Storage.put_url()` + R2 | CORS bucket nếu chưa bật | cấu hình, không xây uploader |

Không được ghi “xây mới” nếu chưa điền cột “Implementation đã có”.

## B. Từ kết quả đo đến bước kế tiếp

Đọc theo thứ tự:

1. Test đỏ hoặc scan/linter lỗi → xử lý lỗi trong đúng phạm vi được giao.
2. Lập inventory primitive nội tại và app hiện có.
3. ToolSpec chưa có → đề xuất T0 **additive**, chỉ thêm metadata/validation;
   không tạo runtime tool, queue hay billing thứ hai.
4. ToolSpec có nhưng app thiếu khai báo → T0b, bọc handler hiện hữu.
5. Chưa đủ năng lực nghiệp vụ → ưu tiên app LTT đã có; chỉ tham chiếu nguồn ngoài
   để bù L1/L2 thật sự thiếu.
6. Đủ tool nhưng chưa có checkpoint/fan-out → D1.
7. Có D1 nhưng chưa planner/validator/cổng duyệt → D2.
8. Có planner nhưng chưa verifier → D3.
9. Agent backend xong → triển khai các phase Canvas bắt buộc theo Q49/Q39.

## C. Câu hỏi bắt buộc trước dòng code đầu tiên

1. Đã đo code và đọc hai mục nhật ký mới nhất chưa?
2. Nhu cầu này đã có primitive hoặc app mẫu nào trong LTT?
3. Đây là reuse, mở rộng additive, logic app-local hay khoảng trống L1/L2?
4. Có đụng `platform_core/`/`server/` không; lý do hợp đồng chung là gì?
5. Có migration không; rollback và tương thích app cũ thế nào?
6. Test nào chốt hành vi, browser flow nào phải nghiệm thu?
7. Có nguy cơ lộ bí mật, sai credit, chạy trùng hoặc mất cô lập user không?

## D. Tuyệt đối không làm

1. Ghi vào `D:\BOT GEMINI`; chỉ đọc và chỉ copy L1/L2 khi thật sự thiếu.
2. Copy L6 từ BOT GEMINI: queue, auth, JSON store, quota, key pool, storage.
3. Sửa trực tiếp `C:\LTTPlatform\app\`; phải sửa nguồn rồi deploy đúng quy trình.
4. Viết Python inline qua PowerShell hoặc dùng lệnh Bash trong tài liệu Windows.
5. Tuyên bố hoàn thành dựa trên kế hoạch thay vì test/scan/browser thật.
