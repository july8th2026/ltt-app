# 06 — Options & Decision Gate: Upscale Video

## Ba phương án bắt buộc

| Tiêu chí | REPAIR | PARITY | DIFFERENTIATED |
|---|---:|---:|---:|
| User value | 72 | 96 | 88 |
| Blocker/coverage | 92 | 96 | 82 |
| Time-to-value | 94 | 70 | 38 |
| Reuse nội tại | 96 | 84 | 62 |
| Chi phí/effort | 88 | 62 | 28 |
| Rủi ro/dependency | 88 | 68 | 34 |
| Confidence | 94 | 82 | 56 |
| **Tổng /100** | **86** | **90** | **57** |

- **Phương án khuyến nghị: PARITY có kiểm soát**, triển khai tuần tự: Repair
  blocker trước, sau đó chỉ ba năng lực chất lượng Detail/Denoise/Deblur cùng
  Auto preset. Không biến app thành professional editor.
- Vì sao: Repair đơn thuần làm app an toàn hơn nhưng Market Score vẫn thấp;
  Differentiated toàn phần đòi engine/VRAM/UX quá lớn. Parity chọn lọc tận dụng
  queue/credit/GPU/Seedance có sẵn và cải thiện đúng lời hứa customer.
- Điều không làm: 8K, colorize, object removal, timeline editor, hàng chục model
  kỹ thuật, thông số GPU/VRAM cho customer.

## Câu hỏi khóa logic

| ID | Câu hỏi | Phương án | Khuyến nghị | Hệ quả | Dev chọn/ngày |
|---|---|---|---|---|---|
| D1 | Scope/JTBD ưu tiên? | A Pro editor; B một-click creator; C restoration suite | **B** | Form gọn, advanced theo progressive disclosure | Chưa khóa |
| D2 | Feature nào BUILD? | A tất cả leader; B Detail+Denoise+Deblur; C chỉ repair | **B**, HDR/8K/color DEFER | Cần temporal benchmark/provider nhưng không phình IA | Chưa khóa |
| D3 | Benchmark/parity đích? | A Topaz UI/pro controls; B TensorPix/HitPaw UX + Topaz output bar; C CapCut | **B** | Đơn giản với customer, chất lượng có blind gate | Chưa khóa |
| D4 | Visual target? | A giữ LTT dark; B thay sáng; C theo mockup Pro | **A**, bỏ badge giả/jargon | Đồng nhất portfolio, ít churn | Chưa khóa |
| D5 | Responsive/accessibility? | A desktop first; B WCAG AA + 390/768/1440/1920; C mobile only | **B** | Shared shell cũng phải sửa accessible name | Chưa khóa |
| D6 | Quyền/credit/provider/failure? | A upload thẳng hiện tại; B staging session + server probe/quote + idempotent cleanup; C provider SaaS hết | **B** | Đóng G2/G3/G5, tốn thêm lifecycle/sweeper | Chưa khóa |
| D7 | Rollout/acceptance/rollback? | A deploy ngay; B fixture→targeted→gate→canary→authenticated prod verify; C beta kín | **B** | Không lặp H26 “portfolio PASS” thay app DEEP PASS | Chưa khóa |

Chưa khóa các quyết định làm thay đổi product/model contract thì chưa BUILD.
Các blocker F-001/F-002/F-004/F-006 có thể vào thiết kế kỹ thuật, nhưng vẫn cần
phase implementation riêng và rollback trước khi chạm runtime.

