# UI-RD Taovideo — kế hoạch BUILD đồng bộ Upscale

1. Hoàn thiện DTO owner-scoped cho history/filter/card; không tạo bảng history mới.
2. Hoàn thiện responsive studio và state empty/queued/running/done/error/cancelled.
3. Đóng cầu Seedance→Upscale theo `upscalevideo` UP1/UP3: quote server-side,
   confirm CSRF, submit service chung, compare nguồn/output thật.
4. Giữ retry/delete/templates/assets DEFER; không bật dead control.
5. Nghiệm thu Playwright 1440/1280/390/360, keyboard, console/network, test app,
   full gate, memory và commit trước release.

Rollback: ẩn nút Upscale và trả template về form/card cũ; job Upscale đã nộp vẫn
được drain/cancel/settle theo Q47, không xóa ledger hay artifact audit.
