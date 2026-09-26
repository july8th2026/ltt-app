# 02 — GPU SCHEDULER TRUTH

> Nguồn: `platform_core/models.py`, `platform_core/gpu_lease.py`,
> `platform_core/job_runner.py`. Mọi số liệu hiệu năng dưới đây là **CHƯA ĐO**
> (GPU đang bận việc production thật lúc lập tài liệu này, 2026-09-26).

## Cơ chế lease, đầu-đến-cuối

1. **Job cần GPU** → `job_runner.py:_giu_gpu(worker_id, job_id, job_type, need_mb)`
   (context manager). `need_mb` đến từ `manifest.vram_for(job_type)`
   (`platform_core/registry.py:881`) — đọc `gpu_vram_mb` của app (`manifest.py`).
2. `_giu_gpu` gọi `gpu_lease.acquire(db, worker_id=..., job_id=..., need_mb=...)`
   (`gpu_lease.py:137`):
   - `busy_uuids(db)` (`gpu_lease.py:128-133`) — UUID mọi GPU **đã có lease** trên
     máy này (`WHERE host = host_name()`).
   - `_con_cho(g)` (`gpu_lease.py:163-178`): `free_mb - đã_giữ(g) >= need_mb + HEADROOM_MB`
     (`HEADROOM_MB = 1024`, `gpu_lease.py:100`) + chính sách máy (`cm.gpu_allows`,
     ví dụ chặn GPU đang xuất hình để tránh TDR).
   - `ung_vien = [g for g in gpus if g.uuid not in taken and _con_cho(g)]`
     (`gpu_lease.py:179`) — **GPU đã có lease bị loại khỏi ứng viên NGAY LẬP TỨC**,
     trước khi xét `need_mb`. Đây là chỗ quyết định: dù `need_mb` bé tới đâu,
     một GPU đang bận thì **không bao giờ** được chọn.
   - Ghi `GpuLease` mới, `db.commit()`. `IntegrityError` (đụng
     `UniqueConstraint("host","gpu_uuid")`, `models.py:1037`) nghĩa là worker
     khác vừa giành đúng card này giữa lúc đọc-ghi → rollback, thử card tiếp
     theo (đường chạy BÌNH THƯỜNG, không phải lỗi).
   - Công bố lên `gpu_claims` với `exclusive=True` (`gpu_lease.py:196-203`) —
     **luôn độc quyền cả card**, bất kể `need_mb` khai bao nhiêu.
3. **Không giành được GPU nào** → `acquire` trả `None` → `_giu_gpu` yield
   `(None, het_gpu=True)` → job xếp lại hàng, thử lại sau (không lỗi).
4. **Trong lúc chạy**: `heartbeat(db, lease)` (`gpu_lease.py:213`) đập nhịp bằng
   luồng riêng (không phụ thuộc `ctx.progress()`, vì một job nạp model lâu mà
   không gọi progress sẽ bị coi mồ côi). `reclaim_orphans` (`gpu_lease.py:111`)
   xoá lease của worker chết (`heartbeat_at` quá `ORPHAN_TIMEOUT = 10 phút`).
5. **Xong job**: `release(db, lease)` (`gpu_lease.py:226`) xoá row `GpuLease` —
   GPU quay lại `ung_vien` cho job kế tiếp.

## Vì sao đồng thời = 1, không phụ thuộc VRAM

`GpuLease.__table_args__` chỉ có một ràng buộc:

```python
UniqueConstraint("host", "gpu_uuid", name="uq_gpu_lease_host_uuid")  # models.py:1037
```

Đây là **cơ chế**, không phải chính sách có thể chỉnh bằng tham số app. Một GPU
trên một máy có **tối đa một** hàng `GpuLease` sống tại một thời điểm — bất kể
GPU đó còn 15 GB trống hay 15 MB trống. `need_mb`/`gpu_vram_mb` chỉ tham gia ở
bước 2 (`_con_cho`) để quyết định **có nhận job ĐẦU TIÊN hay không** khi GPU
**chưa** có lease nào — nó không bao giờ được đọc để cho phép một lease **thứ
hai** cùng tồn tại, vì bước lọc `ung_vien` (`gpu_lease.py:179`) đã loại GPU đã
có lease trước khi `need_mb` kịp có ý nghĩa. Đây chính là điều docstring của
`GpuLease` (`models.py:1028-1031`) đã nói trước:

> *"Quy ước v1: một job một GPU, không chia sẻ. Cố ý chọn vậy — việc nặng của
> nền tảng (whisper, YOLO, upscale) đều ngốn VRAM, và kế toán VRAM theo hứa hẹn
> sẽ lệch so với thực tế rồi OOM."*

## `gpu_vram_mb` / `HEADROOM_MB` thực sự gate cái gì

Chỉ MỘT điều: **sàn nhận công việc khi GPU đang RẢNH**. Hạ `gpu_vram_mb.fast`
2000→1000 làm sàn `_con_cho` giảm từ "cần 3024 MB trống" xuống "cần 2024 MB
trống" cho **một** job Fast đang xin GPU rảnh — không liên quan gì đến việc có
job Fast thứ hai chạy cùng lúc hay không, vì bước 2 (`ung_vien`) đã loại toàn
bộ GPU bận trước khi con số này được dùng. Nói cách khác: `gpu_vram_mb` quyết
định **ai được vào hàng đầu tiên**, không quyết định **hàng có mấy chỗ**.

## Cần đổi gì để có shared-GPU scheduling THẬT (và tại sao KHÔNG làm bây giờ)

Phải thay `UniqueConstraint("host","gpu_uuid")` bằng kế toán tổng `vram_mb` đã
cấp trên mỗi GPU (mỗi lease giữ một phần VRAM thay vì độc chiếm), tức:

1. Bỏ `UniqueConstraint`, cho phép nhiều `GpuLease` cùng `gpu_uuid`.
2. `_con_cho` phải cộng dồn `vram_mb` của MỌI lease đang sống trên GPU đó rồi
   so với `free_mb` thật — hiện `_con_cho` chỉ trừ `da_giu` (VRAM công bố qua
   `gpu_claims`, không phải VRAM thật NCNN/CUDA đã cấp).
3. `gpu_claims.publish(..., exclusive=True)` (`gpu_lease.py:201-203`) phải đổi
   thành công bố **phần** VRAM, không phải cả card — mọi consumer khác đọc
   `gpu_claims` (các app khác dùng GPU) phải được kiểm tra không giả định
   độc quyền.
4. Cần đo THẬT VRAM một tiến trình NCNN/CUDA chiếm (không chỉ `tile`/`threads`
   suy luận từ `autotune.py`) — kế toán theo hứa hẹn mà không đo thật là đúng
   con đường docstring `models.py:1028-1031` đã cảnh báo sẽ OOM.

⛔ **Không làm bây giờ** vì ba lý do trong chính docstring và trong audit:
(a) chưa có phép đo VRAM thật per-process để kế toán chính xác — làm mà không
đo là lặp lại đúng lỗi ISSUE A/B đã tìm thấy; (b) máy này là **production**,
một GPU, đang chạy job khách thật — OOM do kế toán sai ảnh hưởng trực tiếp
khách hàng; (c) chưa có bằng chứng đo được rằng tải hiện tại cần nhiều hơn 1
job GPU đồng thời (không có hàng đợi dài quan sát được). Xem
`07_CORRECTION_PLAN.md` phase liên quan — đây là hạng mục DEFERRED, có
evidence-gate rõ ràng, không phải "quên làm".
