# UI-RD — Tạo video AI (Seedance)

**Trạng thái:** FULL — Decision Gate đã khóa; BUILD đang WIP, chưa deploy
**App/route thật:** `taovideo` / `/taovideo`  
**Ảnh tham khảo:** `g:\My Drive\AI\A\New folder\seedance.png` (1600×990)  
**Nguồn sự thật:** `apps/taovideo/`, `platform_core.jobs`, `jobs` và credit ledger

## Mục tiêu

Đưa giao diện tạo video và thư viện kết quả của app `taovideo` gần bố cục studio
Seedance trong ảnh, nhưng giữ một nguồn sự thật: app/job/credit/storage hiện có.
`Seedance` là tên model/provider-facing; URL, quyền và job type vẫn là `taovideo`.

## Bằng chứng baseline

- `GET /taovideo` production yêu cầu đăng nhập và return-to đúng `/taovideo`;
  Playwright Cloudflare desktop: console 0 error/0 warning, không request động lỗi.
- UI source hiện có form đơn cột + tối đa 12 job của chính chủ, với player/download
  cho video đã xong; chưa có view/grid toggle, filter/sort/status tab, bulk action,
  retry/delete, prompt history hay asset library UI.
- App đã hỗ trợ thật: Seedance Mini/Standard/Fast; resolution/duration/aspect phụ
  thuộc model; audio, quantity 1/2; translation; upload ref ảnh/video/audio; asset://
  và healing ảnh người thật; estimate/reserve/settle credit; worker async/resume.

## Ràng buộc đã khóa

- Không tạo ảnh raster mới. Không dùng thumbnail crop từ ảnh tham khảo để giả video
  của user; thumbnail/video card phải lấy output thật hoặc empty state.
- Không đổi slug/route hay xây app `seedance` thứ hai.
- Mọi history, filter, retry, delete phải owner-scoped, CSRF-protected và có chính
  sách retention/rollback trước khi bật.

## Decision Gate đã khóa

Dev đã trả lời 9 lựa chọn ngày 2026-08-02. Seedance giữ route/job hiện tại, dùng
dữ liệu owner-scoped thật, không giả asset/output và nối Upscale bằng popup báo
giá credit rồi gọi service dùng chung. Phần lifecycle/compare/cancel theo Q47 và
kế hoạch `UI_REDESIGN/upscalevideo/04_IMPLEMENTATION_PLAN.md`; retry/delete vẫn
DEFER đến khi có audit/retention/idempotency đầy đủ.
