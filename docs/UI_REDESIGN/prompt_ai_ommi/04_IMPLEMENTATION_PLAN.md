# H26.8 — Implementation plan và pass gate

1. **Contract:** test tên public mới nhưng khóa slug/route/job cũ.
2. **Catalog:** package JSON + loader app-owned; merge với catalog DB có phân
   trang; get/clone hoạt động với ID tích hợp; user khác không thấy bản clone.
3. **Dashboard:** API thêm chi tiêu ròng hôm nay/tháng từ ledger cá nhân;
   React dựng strip, tile, resource/project/activity panel.
4. **Responsive:** desktop immersive một viewport; mobile rail một hàng cuộn,
   44px target; không overflow ngang.
5. **Verify:** targeted backend/frontend, quick gate, Playwright desktop/mobile,
   catalog clone/create resource, console/network, full gate.
6. **Release:** cập nhật memory + commit riêng; chưa deploy, H26.12 mới canary.

Rollback: revert commit H26.8. Không có migration; clone/resource/job/ledger đã
tạo vẫn là dữ liệu hợp lệ và không bị xóa khi lùi presentation/catalog tích hợp.
