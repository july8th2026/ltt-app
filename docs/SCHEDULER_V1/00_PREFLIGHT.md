# Scheduler V1 — Phase 0 preflight

Ngày: 2026-09-10

## Phạm vi

Nâng cấp hàng đợi PostgreSQL hiện hữu bằng hai lớp ưu tiên, ranking canonical,
queue snapshot, ETA và phản hồi client. Không rewrite queue, không thêm broker,
không đổi pricing/provider/GPU manager và không deploy production trong campaign.

## Cây làm việc

- Worktree: `D:\LTTSTUDIOSAPP-scheduler-v1`
- Branch: `architecture/scheduler-priority-v1`
- Base/HEAD lúc tách cây: `9d7118284aea4818178e857c787ac285f40ab57c`
- Trunk nguồn: `admin-mvp-v3`
- Trạng thái lúc tách: sạch; vendor bị ignore của Upscale đã được copy theo
  `docs/QUY_TRINH_WORKTREE.md`.

Một worktree LTT Voice đang sửa `platform_core/public_api/invocation.py`. Tệp đó
được coi là vùng đã có chủ và campaign này không sửa. Các vùng Scheduler chính
(`jobs.py`, `models.py`, `job_runner.py`, `runtime_noi_bo/job.py`, API status)
không có thay đổi dở trong worktree khác tại thời điểm kiểm.

## Máy và dịch vụ

- Đây là máy chủ (`C:\LTTPlatform` tồn tại), nên không sửa bản cài hoặc chạy
  production migration trực tiếp.
- PostgreSQL nghe cổng 5432; ứng dụng hiện hữu nghe đúng cổng 8100.
- Permission filesystem của phiên: unrestricted. Điều này không được hiểu là
  quyền deploy hoặc quyền thay đổi hệ thống ngoài phạm vi.
- `python tools\cua_so_yen.py trang-thai`: `RANH` lúc kết thúc preflight.

## Trạng thái gate

`FULL_GATE: NOT_RUN` tại baseline. Không mượn kết quả lịch sử hay một HEAD khác
làm bằng chứng cho cây này. Theo Operating Contract, L1/L2 chạy sau từng
changeset; L3 chỉ chạy ở checkpoint cuối của thay đổi `jobs`/migration.

## Rủi ro chuyển tiếp

Migration phải additive. Job cũ và binary không biết metadata mới vẫn có hành
vi an toàn tương đương cũ; mọi giá trị thiếu/lạ được hiểu là `EXTERNAL`. Lúc
phát hành phải đưa web và worker lên trong cùng release vì chỉ worker mới hiểu
priority. Không chạy migration production trong campaign này.

