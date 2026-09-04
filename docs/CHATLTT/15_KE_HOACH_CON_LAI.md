# Kế hoạch phần còn lại — sau 04/09/2026

Viết sau khi ba bản vá GPU lên máy B và đợt 5–7 của bộ kiểm giao diện xanh.
Mỗi hạng mục ghi **đạt khi nào**, không chỉ ghi làm gì — một hạng mục không có
tiêu chí dừng là một hạng mục sẽ trôi.

---

## H1 — Deploy máy A  ⏱ ~15 phút  🔴 chặn mọi thứ khác

Production đang **lệch** ở `render_gateway/busy.py` (prod `5a8ff416`, kho
`bba8ca47`). Máy A cũng chạy mã `render_gateway`, nên bản vá nhường card mới chỉ
sống ở máy B — hai máy đang chạy hai bản khác nhau của cùng một tệp.

⛔ **Đây là trạng thái nguy hiểm nhất trong danh sách này**, và nguy theo kiểu
   im lặng: không có gì hỏng ngay, chỉ là hai bên suy luận về card theo hai bộ
   luật khác nhau.

| Bước | Việc |
|---|---|
| 1 | `git merge` cây chính (phiên kia vừa thêm `ad77f04`) |
| 2 | `gate.py` đầy đủ trên cây đã hợp |
| 3 | `--ff-only` cây chính → deploy nâng quyền (chủ dự án bấm UAC) |
| 4 | đối chiếu băm production vs kho cho **cả ba** gói: `apps/`, `render_gateway/`, `llm_gateway/` |

**Đạt khi:** ba gói khớp băm, `/health/ready` 200, và `tools/api_prod_canary.py
trang-thai` xanh.

---

## H2 — Nghiệm thu ba bản vá GPU trong điều kiện THẬT  ⏱ ~30 phút  🔴

Hiện mới chứng minh bằng phép kiểm đơn vị và hai lần quan sát rời rạc. Chưa có
một lượt đo **có chủ đích** nào dựng đúng tình huống.

🔴 **Và đây là chỗ dễ tự lừa nhất**: cả ba bản vá đều nói về những tình huống
   *hiếm*, nên "chạy thử thấy không sao" **không phải bằng chứng**. Phải dựng
   đúng điều kiện rồi mới đo.

| # | Dựng điều kiện | Đạt khi |
|---|---|---|
| 2.1 | qwen **đang trả lời** (tải ≥ 50 %) → gửi job ảnh | job **chờ** rồi chạy; **không** có `ConnectionReset` ở lượt chat |
| 2.2 | qwen **chỉ thường trú** (rảnh) → gửi job ảnh | `/unload` được gọi, VRAM tụt, ảnh ra |
| 2.3 | ComfyUI **đang vẽ** → gửi lượt chat | cổng LLM trả **429**, không nạp đè |
| 2.4 | card trống → job ảnh | đi thẳng, **không đuổi ai** (log không có dòng nhả) |

**Đạt khi:** cả bốn quan sát được, và VRAM **không lần nào** chạm 24 GB với hai
model cùng `state=ready`/`queue_running`.

⚠️ 2.3 tiêu credit thật (một lượt ảnh + một lượt chữ). Chấp nhận: đây là bốn
   tình huống đắt nhất của cả hệ.

---

## H3 — Chốt "nhả về RAM"  ⏱ ~20 phút  🟢

Hôm nay nó **đúng nhờ tình cờ**: `mmap` + 82 GB page cache trống, GGUF 15,33 GiB.
Không ai canh. Thêm `--no-mmap`, hoặc RAM tụt vì một dịch vụ khác, và nạp lại sẽ
chậm đi vài lần **mà không có gì kêu** — đúng họ với "tràn sang RAM chủ" đã đo
22/08.

**Việc:** một chốt đọc `llama-swap.yaml` và khẳng định:
- không có cờ `--no-mmap` trong `cmd` của bất kỳ hồ sơ nào;
- `healthCheckTimeout` đủ cho một lần nạp **từ đĩa lạnh** (trường hợp xấu nhất).

**Đạt khi:** chốt đỏ nếu ai đó thêm `--no-mmap`. Phải **thử phá** để xác nhận.

---

## H4 — `6.2` giọng nhân bản  ⏱ ~10 phút  🟡 cần chủ dự án

Bỏ qua **mọi lượt** vì tài khoản kiểm chưa nhân bản giọng nào. Mệnh đề *"giọng
riêng đi đúng vào tham số"* chưa từng được kiểm.

**Hai đường, chủ dự án chọn:**
- (a) tạo một giọng nhân bản trên `akakenly.design@gmail.com` → hạng mục chạy được;
- (b) chấp nhận không kiểm được → đổi `bo_qua` thành một dòng ghi rõ trong báo cáo
  nghiệm thu, thay vì lặng lẽ bỏ qua mỗi lượt.

⛔ Không chọn thì nó sẽ **bỏ qua mãi mãi** và trông như đã kiểm.

---

## H5 — Đợt 8: di động và bàn phím ảo  ⏱ ~1 giờ  🟡

Đã có trong kế hoạch gốc, chưa dựng. Cỡ M vì cần giả lập thiết bị.

| # | Hạng mục | Đạt khi |
|---|---|---|
| 8.1 | 390 px: ô soạn không bị bàn phím ảo che | ô soạn còn thấy được khi focus |
| 8.2 | cuộn tới đáy khi bàn phím mở | tin nhắn cuối vẫn trong khung nhìn |
| 8.3 | chip ảnh đính kèm không tràn ngang | `scrollWidth <= clientWidth` |
| 8.4 | nút media chạm được (≥ 44 px) | đo `getBoundingClientRect` |

---

## H6 — Đợt 9: đổi model giữa hội thoại  ⏱ ~40 phút  🟡

| # | Hạng mục | Đạt khi |
|---|---|---|
| 9.1 | đổi `ltt_llm` → `ltt_llm_vision` giữa chừng | lượt sau dùng đúng model mới |
| 9.2 | model đã chọn sống qua F5 | `conversation.model_alias` giữ nguyên |
| 9.3 | đổi sang model không đọc ảnh khi đang có ảnh đính kèm | giao diện gỡ ảnh và **nói ra** |

---

## H7 — Nợ nhỏ  🟢

- `5.2/5.3` xanh nhưng **phập phù** theo card rảnh. Cân nhắc cho chúng chờ card
  lâu hơn thay vì bỏ qua sớm — nhưng **đừng** biến bỏ-qua thành ép-chạy: máy bận
  là một kết quả thật.
- Commit `2c9fc88` mang thông điệp `wip` cho một bản vá thực chất. Nội dung đầy
  đủ nằm ở chú thích mã và `docs/ANH_NOI_BO/DECISIONS.md`; không viết lại lịch
  sử vì cây chính đã có nó.

---

## Thứ tự thi hành

    H1  ->  H2  ->  H3  ->  (H4 chờ chủ dự án)  ->  H5  ->  H6  ->  H7

🔑 **H1 trước H2** vì đo trên hai máy chạy hai bản mã khác nhau là đo một hệ
   không tồn tại. Và **H2 trước mọi thứ còn lại** vì nếu ba bản vá GPU sai thì
   mọi phép đo sau đó đều đứng trên một nền không chắc.
