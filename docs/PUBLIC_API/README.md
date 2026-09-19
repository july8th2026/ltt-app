# PUBLIC_API — chỉ mục

**Loại:** TRA CỨU, đang sống (code_refs cao nhất trong cụm L-B — 47 tệp mã/test
còn đọc thư mục này).

**Tệp chủ:** `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` (bảng chốt: app/tool/
model/chế độ chạy nào được publish qua `/api/v1`, coverage cuối) — trỏ từ
`CLAUDE.md` gốc dự án (dòng "Public API `/api/v1`"). Người tích hợp đọc
`DEVELOPER_GUIDE.md`; hợp đồng dây đọc `PROTOCOL_V1.md`.

**Sinh tự động — KHÔNG sửa tay:** `DEVELOPER_GUIDE.md` và `PROTOCOL_V1.md` có
một khối giữa marker do `tools/build_public_api_docs.py` ghi từ catalog thật
(`--check` chống trôi) — sửa nguồn sinh (mã), không sửa khối đó trực tiếp.

**Trạng thái:** nhiều tệp còn lại (`AUDIT_*`, `*_PROGRESS.md`, `*_READINESS_V1.md`,
`FULL_PLATFORM_*`, `KERNEL_V1.md`…) là log tiến độ/audit tự mang mốc ngày — đọc
như biên bản tại thời điểm đó, không phải quy chuẩn hiện hành trừ khi tệp tự
nói "chốt"/"quy chuẩn" (ví dụ `QUY_CHUAN_TRANG_TAI_LIEU_API.md`).
