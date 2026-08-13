# FULL PLATFORM DEPENDENCY GRAPH — EXT-01

Mục đích: chứng minh thứ tự EXT-02…EXT-21 **không tuỳ tiện** — mỗi bước tiêu thụ
đầu ra của bước trước, và đảo thứ tự thì phải làm lại việc.

---

## 1. Đồ thị

```
                     ┌─────────────────────────────────┐
                     │ V2 (Q92) — kernel, keys, scopes │
                     │ catalog, quote/job/credit,      │
                     │ upload/artifact, limits,        │
                     │ webhook, usage, portal tối thiểu│
                     └───────────────┬─────────────────┘
                                     │
                            EXT-01 (bản này)
                    gap matrix · dependency · target
                                     │
        ┌────────────────────────────┴────────────────────────────┐
        │                                                         │
  EXT-02 PROTOCOL                                          EXT-04 IDENTITY
  execution mode, error/retry,                             project, service
  correlation header, retry-after                          account, IP/expiry,
        │                                                  OAuth decision
        │                                                         │
  EXT-03 CATALOG                                                  │
  models/capabilities,                                            │
  execution mode trong contract                                   │
        │                                                         │
        └────────────────────────┬────────────────────────────────┘
                                 │
                        EXT-05 DEVELOPER TAB (IA)
                                 │
        ┌──────────┬─────────────┼─────────────┬──────────┐
        │          │             │             │          │
   EXT-06      EXT-07        EXT-08        EXT-09     EXT-10
   variable    quickstart    playground     logs/      webhook
   reference   /recipes                     trace      console
        │          │             │             │          │
        └──────────┴─────────────┼─────────────┴──────────┘
                                 │
                        EXT-11 USAGE/BUDGET/ALERT
                                 │
                        EXT-12 SANDBOX
                                 │
                        EXT-13 ADMIN CORE
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        EXT-14 POLICY      EXT-15 PRICING     EXT-16 OPS/SUPPORT
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                        EXT-17 LIFECYCLE/STATUS
                                 │
                        EXT-18 SDK/CLI/POSTMAN
                                 │
                        EXT-19 PRIVACY/RETENTION
                                 │
                        EXT-20 CERTIFICATION 100%
                                 │
                        EXT-21 FINAL GATE
```

---

## 2. Vì sao đúng thứ tự này — từng cạnh một

| Cạnh | Bắt buộc vì |
|---|---|
| 01 → 02 | Không khoá được chuẩn giao thức khi chưa biết cái gì đang thiếu. Bằng chứng: EXT-01 mới phát hiện `X-Correlation-ID` chỉ có trên nhánh lỗi và `Retry-After` không phải header. |
| 02 → 03 | Contract của tool phải **khai** execution mode; khai một giá trị chưa có định nghĩa là tạo nợ. Ngược lại, sửa 5 contract sau khi đã publish là breaking change. |
| 02 → 05 | Playground/logs hiển thị lỗi và retry; UI dựng trước khi mã lỗi ổn định thì phải sửa lại UI. |
| 01 → 04 | Ownership hierarchy (user → project → key) quyết định **khoá chính** của mọi bảng sau đó. Đây chính là bài học V1 mà `AUDIT_V1_TO_V2.md` ghi lại: xây UI trước identity thì phải làm lại. |
| 04 → 05 | IA của portal phụ thuộc việc có Project/Service account hay không: có thì cây điều hướng là `Project → Keys`, không thì phẳng. |
| 03,04 → 05 | Tab "Apps, Models & Tools" cần catalog model (03) và phạm vi hiển thị theo project (04). |
| 05 → 06…10 | Sáu tính năng developer đều là **trang con** của tab; không có khung IA thì mỗi trang tự đặt chỗ, và đó là cách route rác sinh ra. |
| 03 → 06 | Variable reference **sinh từ** contract; viết tay là drift ngay lần đổi schema đầu tiên. |
| 03 → 08 | Playground dựng form từ JSON Schema thật; nếu không, nó là form thứ hai phải bảo trì. |
| 02 → 09 | Trace cần correlation id có mặt trên **mọi** phản hồi (thiếu này là X5 trong gap matrix). |
| 09 → 16 | Support trace của admin đọc cùng nguồn với log của khách; xây admin trước thì phải viết lại khi nguồn đổi. |
| 10 → 11 | Cảnh báo "webhook chết" là một loại alert; event catalog phải có trước. |
| 11 → 12 | Sandbox phải **không** sinh chi phí provider và **không** đụng ngân sách thật → cần biết ngân sách được đo thế nào. |
| 05…12 → 13 | Admin quản trị **những thực thể đã tồn tại**. Xây admin cho thứ chưa có là xây giao diện cho bảng trống. |
| 13 → 14,15,16 | Policy/pricing/ops đều là màn hình trong admin console; cần khung admin trước. |
| 04 → 14 | Tier gắn vào project/tài khoản; không có project thì tier chỉ gắn được vào khoá lẻ — mô hình sai, sửa sau rất đắt. |
| 15 → 20 | Chứng nhận phải khẳng định **giá đúng theo phiên bản bảng giá**; chứng nhận trước khi có pricing version là chứng nhận thứ sẽ đổi. |
| 02,03,04 → 17 | Changelog/deprecation nói về *cái gì* thay đổi: route, mã lỗi, contract, scope, auth. Cả bốn phải ổn định trước. |
| 17 → 18 | SDK/CLI/Postman **sinh** từ contract + version. Sinh trước lifecycle là đóng băng nhầm phiên bản. |
| 19 sau 09,10,12 | Retention/export/delete phải biết hết dữ liệu tồn tại: request log, webhook delivery, sandbox run. Viết chính sách trước khi biết dữ liệu là viết chính sách sai. |
| 20 trước 21 | Không kết luận release khi chưa chứng nhận từng tool/model/execution mode. |

---

## 3. Cạnh **không** tồn tại (được phép làm song song)

- EXT-06 / EXT-07 / EXT-09 / EXT-10 độc lập nhau (khác dữ liệu, khác trang).
- EXT-14 / EXT-15 độc lập nhau; chỉ gặp lại ở EXT-16 (ops đọc cả hai).
- EXT-18 không phụ thuộc EXT-19.

Pack chạy tuần tự nên đây chỉ là ghi chú: nếu một prompt bị chặn vì quyết định
sản phẩm, có thể chạy prompt song song thay vì đứng chờ — **trừ** các cạnh ở §2.

---

## 4. Điểm chặn cần quyết định của chủ sản phẩm (không phải việc của code)

| Quyết định | Chặn | Vì sao không tự quyết được |
|---|---|---|
| Có mở **delegated OAuth** không | EXT-04, và gián tiếp EXT-05/13/20/21 | Phụ thuộc có bên thứ ba thật muốn hành động thay mặt người dùng LTT hay không. `RESEARCH_AND_DESIGN_BASIS.md` nói rõ: không thêm OAuth theo trào lưu. Nếu không, ghi `DEFERRED_WITH_ADR`. |
| Sửa gốc giá-theo-thời-lượng bằng **cách nào** (đo phía server lúc báo giá, hay cấm top-up và fail-refund) | mở `video.upscale`, `video.subtitle`, `video.short_clips` | Cách một tốn thêm một lần đọc metadata; cách hai làm một số job dài bị từ chối giữa chừng. Là đánh đổi sản phẩm. |
| Con số **trần credit ngày** mặc định | EXT-11, EXT-14 | Là chính sách thương mại. |
| Có làm **sandbox tốn tiền thật với model rẻ** hay **mock hoàn toàn** | EXT-12 | Mock rẻ nhưng không chứng minh tích hợp thật. |
| Có mở **STREAM** cho chat không | EXT-02, EXT-20 | Kéo theo quyết định ToS về sidecar ChatGPT (đã ghi ở `APP_DISPOSITION_V1.md`). |

Bốn trong năm quyết định trên **chặn ở EXT-02/EXT-04**, tức là rất sớm. Đó là
lý do EXT-01 nêu chúng ngay bây giờ thay vì để va phải giữa chừng.
