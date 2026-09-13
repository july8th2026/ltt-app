# MA TRẬN TEST JOB DÀI — bão hoà, hàng đợi, công bằng

> Thuộc chương trình **VẬN HÀNH THẬT**. Gọi tên là tìm ra tệp này.
>
> ⛔ Đây là test **trên production thật**, bằng tài khoản thật và khoá thật, đi
> xuyên `API → job → admission → hàng đợi → runtime → GPU → stream → credit`.
> Unit test **không** thay được nó: ngày 13/09/2026 ba bản vá L-08 qua sạch mọi
> phép kiểm trong cây rồi hoá ra chưa từng chạm vào lượt thật.

---

## 1. Primitive — ĐO ĐƯỢC, không ước

| | giá trị | đo lúc nào |
|---|---|---|
| **Job dài chuẩn** | `"Count from 1 to 2000. One number per line."` · `max_tokens=8000` | 13/09 |
| Thời lượng trên `ltt-3.8` | **123,3 s** · 7.955 mảnh SSE | 13/09, một mình trên card |
| Credit mỗi lượt | giữ **4**, quyết toán 0–3 | sổ `canary.api` |
| Sàn `max_tokens` | **≥ 64** (L-02) — dưới ngưỡng là 400 | |
| Header bắt buộc | `Idempotency-Key` mỗi lượt, **không** đặt trong body | |

🔑 **Vì sao phải job DÀI.** Hàng đợi chỉ quan sát được khi nó kịp hình thành. Một
lượt 3 giây thì người thứ bảy chưa kịp xếp hàng đã có chỗ, và ta đo ra một hệ
"không bao giờ phải chờ" — sai, và sai về phía yên tâm.

## 2. Đội tài khoản

3 tài khoản × 5.000 credit × **2 khoá live** mỗi tài khoản.

| tài khoản | vai |
|---|---|
| `vh1@lttstudios.local` | khách BÃO HOÀ — chiếm suất |
| `vh2@lttstudios.local` | khách TRANH CHẤP — đến khi đã đầy |
| `vh3@lttstudios.local` | khách ĐẾN SAU — kiểm chờ trắng |

⛔ Hai khoá mỗi tài khoản **không phải để tăng suất** — chúng để **chứng minh
   khoá KHÔNG cộng suất** (J12). Nhầm chỗ này là hiểu sai cả mô hình.

## 3. Ma trận — 12 kịch bản

⚠️ Luật: mỗi kịch bản phải **có khả năng hỏng theo một cách nói lên điều gì đó**.
Cột cuối là điều làm nó ĐỎ; ô trống ở cột ấy nghĩa là kịch bản chưa dùng được.

| # | kịch bản | mong đợi | đỏ khi |
|---|---|---|---|
| **J1** | 1 job, `ltt-3.8` | ~123 s, tok/s nền | lệch > 25 % nền |
| **J2** | 2 job, mỗi card 1 | **song song thật**, ~123 s cả hai | tổng ≈ 2×123 ⇒ hai card đang nối tiếp |
| **J3** | 4 job (2/card) | cả 4 chạy, tok/s giảm nhẹ | có job phải chờ |
| **J4** | 6 job (3/card) | **bão hoà**, cả 6 chạy | có job thứ 6 phải chờ |
| **J5** | **7 job** | job thứ 7 **XẾP HÀNG**, nhận `response.queued` | 429 thay vì chờ, hoặc chờ im lặng |
| **J6** | 12 job, **một** tài khoản | đạt **6 đồng thời** — trần tài khoản KHÔNG bật khi không ai khác chờ | chỉ đạt 4 ⇒ trần bật sai |
| **J7** | vh1 ×3 và vh2 ×3 **cùng lúc** | trần BẬT: vh1 ≤ 2/card | vh1 giữ 3 khi vh2 đang chờ |
| **J8** | vh1 bão hoà trước, vh2 đến sau | vh2 có suất trong **≤ 1 job** (~123 s) | vh2 chờ > 2 job |
| **J9** | vh1 bão hoà, vh3 đến **cuối** | vh3 **không chờ trắng** | vh3 chờ vô hạn |
| **J10** | prefill lớn (whale) + 2 thường | **≤ 1 whale** cùng lúc | 2 whale cùng chạy |
| **J11** | khách **CẮT** giữa lúc bão hoà | lease nhả **< 30 s** (L-08 dưới tải) | ≥ 30 s |
| **J12** | vh1 dùng **cả 2 khoá**, 6 job | vẫn **≤ 3/card** — khoá không cộng suất | vượt 3/card ⇒ lách được trần |

## 4. Tham số đo cho mỗi kịch bản

| nhóm | tham số |
|---|---|
| **Hàng đợi** | thời gian tới suất đầu · số nhịp `response.queued` · lý do chờ cuối |
| **Suất** | số lease `mode=stream` sống theo thời gian · phân bố theo `user_id` |
| **Máy B** | `llamacpp:requests_processing` (cổng **8282** / **8281**) |
| **Thông lượng** | tok/s mỗi job · tổng tok/s · TTFB |
| **Sổ sách** | credit giữ → quyết toán · **0 khoản treo** sau khi xong |
| **Công bằng** | suất tối đa một tài khoản giữ trong lúc có người khác chờ |

## 5. Đọc kết quả — bốn ngăn

Mỗi phát hiện vào **đúng một** ngăn, **trước** khi sửa gì:

| ngăn | xử |
|---|---|
| lỗi hệ thống | vào `SO_LOI_DO_TAI.md`, gom lại sửa một lượt |
| lỗi bộ đo | sửa ngay, chạy lại kịch bản ấy |
| nhiễu | chạy lại, **không diễn giải** |
| hệ đúng, **kỳ vọng sai** | sửa kỳ vọng, ghi rõ |

⭐ Ngăn thứ tư dễ bỏ sót nhất và đã xuất hiện thật: một prompt 195.696 token bị
từ chối, suýt ghi thành *"221K không với tới được"* — trong khi nền tảng khai
**171.458** và từ chối là **đúng**.

## 6. Ba cái bẫy của chính bộ đo

1. **Đối chứng hay thiếu.** J11 đo "nhả nhanh" thì phải kèm một lượt **chạy trọn
   không cắt**; nếu không, "nhả sau 20 s" có thể chỉ là "sinh xong sau 20 s".
   Đúng cái đã làm tôi báo ĐẠT sai một lần.
2. **Trần tài khoản chỉ bật khi có tài khoản KHÁC chờ.** Nên J6 và J7 phải chạy
   **tách nhau**; trộn vào là đo ra một con số không thuộc kịch bản nào.
3. **Chưa tới lượt mà đã nhả.** Khách cắt lúc còn xếp hàng thì **chưa có suất** —
   nhả bừa là nhả suất của người khác.

## 7. Lịch sử chạy

| ngày | commit production | J đạt/tổng | lỗi tìm ra |
|---|---|---|---|
| *(chưa chạy lượt nào)* | | | |
