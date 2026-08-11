# Findings H32.2

## Đã sửa

| ID | Mức | Lỗi/gap | Cách đóng |
|---|---|---|---|
| OMMI-H32-01 | P0 | Apply job POST `{}` nên mọi project revision >0 trả 409 | Gửi revision current; integration kiểm 409/200 |
| OMMI-H32-02 | P1 | Style/Meta/Snippet chỉ là menu trang trí | Resolve owner-scoped và đưa body vào preview/job params |
| OMMI-H32-03 | P1 | Autosave onBlur có thể đua với click quote, mất draft | Draft local + nút lưu; mọi preview/quote flush trước |
| OMMI-H32-04 | P1 | Brief React thiếu goal/audience/duration/aspect/language | Bổ sung đầy đủ control customer-facing |
| OMMI-H32-05 | P2 | Mỗi GET API không locale qua 302 | BASE suy ra locale, browser journey mới toàn 200 |
| OMMI-H32-06 | P2 | Quote có thể lệch payload nếu sửa form sau báo giá | Khóa fields tới khi xác nhận/hủy |

## Còn mở

| ID | Mức | Hiện trạng | Tiêu chí đóng |
|---|---|---|---|
| OMMI-H32-07 | P1 | Chưa E4 provider canary/settlement | Worker+provider fixture hoặc staging key; output schema, credit/log pass |
| OMMI-H32-08 | P2 | Model chưa chọn được ở UI | Card tốc độ/giá/chất lượng, quote bind model |
| OMMI-H32-09 | P2 | `/en` vẫn hiện phần lớn nội dung VI | i18n coverage và locale test |
| OMMI-H32-10 | P2 | Chưa activity/support trace theo project | job timeline owner-only, support ID, retry/cancel |
| OMMI-H32-11 | P3 | Chưa bulk/import/export catalog nâng cao | Chỉ làm ở admin sau telemetry nhu cầu |
| OMMI-H32-12 | P3 | Chưa mô tả ngắn selection trong dropdown | Detail/help progressive disclosure |

Không có bug console, 4xx/5xx app request hoặc horizontal overflow trong
journey browser sau sửa.
