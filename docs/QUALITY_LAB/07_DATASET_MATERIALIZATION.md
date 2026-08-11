# Dataset materialization — nhập dữ liệu có provenance

## Mục tiêu

`tools/qualitylab_dataset.py` biến một intake nội bộ thành dataset bất biến có
hash. Công cụ chỉ tạo bằng chứng kỹ thuật; nó không tự suy đoán quyền sử dụng,
không tự coi file tìm thấy trên máy là dữ liệu đã được cấp phép và không bật
release gate.

## Intake v1

Mỗi item bắt buộc có:

- `id`, `media_kind`, `split`, `slice`, `degradation` và tags tùy chọn;
- `reference_source` và `degraded_source` là đường dẫn tương đối trong
  `source-root`; absolute path, traversal và symlink thoát root bị từ chối;
- `license`, `owned_or_licensed=true` và `license_evidence_id` có thể kiểm toán;
- nếu là production data: `production_data=true`, `consent_id` và
  `retention_days` dương.

Materializer probe nội dung thật bằng Pillow/ffprobe, không chỉ tin phần mở
rộng. Sau khi toàn bộ item hợp lệ, nó copy qua staging rồi đổi tên atomically.
Output root đã tồn tại luôn bị từ chối để không sửa một benchmark đã dùng.
Manifest chỉ giữ key tương đối, hash và metadata contract; không giữ đường dẫn
nguồn tuyệt đối.

## Lệnh vận hành

Kiểm tra trước, chưa ghi artifact:

```powershell
python tools\qualitylab_dataset.py inspect `
  --intake <intake.json> --source-root <thu-muc-nguon>
```

Materialize vào một thư mục mới ngoài repo:

```powershell
python tools\qualitylab_dataset.py materialize `
  --intake <intake.json> --source-root <thu-muc-nguon> `
  --output-root <dataset-version-moi>
```

Kiểm tra độ phủ của manifest đã tạo:

```powershell
python tools\qualitylab_dataset.py readiness --manifest <manifest.json>
```

Output readiness yêu cầu tối thiểu 30 ảnh, 12 video, đủ ba split, sáu slice,
năm degradation, hash hai artifact và license evidence trên mọi item. Kể cả
khi đủ, `release_gate_eligible` vẫn luôn là `false`.

## Quy tắc thay phiên bản và rollback

- Không dùng lại output root cũ; thay nguồn/recipe/license tạo dataset version
  và calibration version mới.
- Raw source và artifact materialized ở ngoài git; retention thực thi theo hồ
  sơ nguồn. Không chép production media vào fixture.
- Rollback là chọn lại manifest version trước. Không sửa manifest hoặc file đã
  hash tại chỗ.

## Trạng thái hiện tại

Contract/materializer đã có test ảnh synthetic. Dataset thật 30 ảnh + 12 video
chưa được khai báo bằng intake có license evidence, nên H31.3d2 tổng thể vẫn mở.
