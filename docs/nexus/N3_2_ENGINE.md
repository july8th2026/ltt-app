# N3.2 — ghép engine RustDesk (nguyên bản, Rổ 1), thiết kế + việc phải xác minh trên VM

> Lập 2026-08-20 sau Q97 (dùng RustDesk **nguyên bản**). Đây là **giả thuyết
> thiết kế + danh sách phải kiểm trên máy thật**, KHÔNG phải sự thật đã xác minh.
> R9 của `EXECUTION_PLAN.md` nói rõ: thứ cấu hình-trên-máy phải có một phép đo
> trên máy thật, không chỉ một khẳng định trên giấy. File này tách hai phần đó ra.

---

## 1. Bài toán, sau Q97

RustDesk **nguyên bản** dùng mô hình xác thực riêng của nó: **ID + mật khẩu**.
Nexus có mô hình riêng: **vé một lần do server cấp** (`cap_ve`/`doi_ve`). Hai mô
hình này phải nối lại mà **không sửa** RustDesk (Rổ 1). Nên câu hỏi trung tâm:

> Vé Nexus (tầng **uỷ quyền**) biến thành credential RustDesk (tầng **truyền**)
> như thế nào, mà không nhúng gì vào binary RustDesk?

## 2. Giả thuyết thiết kế — hai vai, hai credential

```
  Máy ĐÍCH (bị điều khiển)                     Bên ĐIỀU KHIỂN
  ─────────────────────────                    ─────────────────
  Agent LTT:                                   khách đổi vé (web/viewer)
   • cấu hình RustDesk nguyên bản trỏ           → nhận: RustDesk ID của đích
     về server LTT (Q96) — KHÔNG build vào,       + mật khẩu MỘT LẦN (Agent
     nạp config từ ngoài                          vừa đặt cho phiên này)
   • đặt mật khẩu phiên NGẮN HẠN mỗi lần        → chạy RustDesk nguyên bản
     có vé, xoay sau mỗi phiên                    connect tới ID đó với mật
   • bật chỉ báo phiên (ràng buộc 7)              khẩu đó
```

**Vé Nexus là tầng uỷ quyền; mật khẩu RustDesk là tầng truyền.** Agent **xoay
mật khẩu RustDesk theo từng vé**, nên một mật khẩu lộ không cho quyền đứng lâu —
đúng tinh thần vé một lần của Q93 ràng buộc 2, dựng lại bằng cơ chế của RustDesk
thay vì sửa nó.

**Điểm mấu chốt cho Rổ 1:** LTT **không** phát minh giao thức mới trong RustDesk;
LTT chỉ **lái** RustDesk nguyên bản bằng config + mật khẩu từ ngoài. Nếu có bước
nào buộc phải sửa binary thì **dừng lại** — đó là tín hiệu đã trượt sang Rổ 2, và
phải quay lại Q97 trước khi làm.

## 3. Phải xác minh trên VM — chưa cái nào là sự thật

Mỗi dòng dưới đây là một câu hỏi phải trả lời bằng **lệnh chạy trên máy thật**,
không bằng trí nhớ về RustDesk:

| # | Câu hỏi | Vì sao quyết định thiết kế |
|---|---|---|
| V1 | Cấu hình server (rendezvous+relay+key) vào client nguyên bản bằng cách nào **không sửa binary**? (file `.toml`? cờ `--config <chuỗi base64>`? biến môi trường? registry?) | Nếu chỉ có đường "build client riêng" thì đó là Rổ 2 — phải báo lại |
| V2 | Đặt mật khẩu truy cập **không giám sát** qua CLI được không? (`--password`?) Đặt xong có hiệu lực ngay không cần bấm UI? | Agent phải đặt được mật khẩu tự động, không người bấm |
| V3 | **Xoay** mật khẩu giữa hai phiên bằng lệnh được không, sạch không? | Mật khẩu một-lần-mỗi-phiên là cả điểm bảo mật |
| V4 | Bên điều khiển `--connect <id>` cấp mật khẩu **không tương tác** được không? | Nếu nó luôn hỏi tay thì luồng vé tự động gãy |
| V5 | RustDesk ID có **ổn định** theo máy không, hay đổi? Map ID ↔ `nexus_devices` thế nào? | Vé trỏ tới đúng máy phải dựa trên một định danh ổn định |
| V6 | Ép **relay** (`ALWAYS_USE_RELAY`) rồi bắt gói tại hbbr — payload có mã hoá đầu-cuối không? (**T10**) | Nếu relay đọc được màn hình thì phải nói với khách (threat model) |
| V7 | Chỉ báo phiên nguyên bản của RustDesk có đủ mạnh cho ràng buộc 7 không, hay Agent phải chồng thêm một chỉ báo? | Ràng buộc 7 là bắt buộc, không phải tuỳ |

## 4. Việc làm được trên 2 VM cùng gateway (Q2 đã trả lời)

- **V1–V5, V7:** làm được — đây là cấu hình + luồng, không phụ thuộc topo mạng.
- **V6 (T10):** làm được bằng cách **ép relay** dù hai VM cùng LAN.
- **KHÔNG làm được:** tỉ lệ P2P/relay thật (cùng NAT) — để dành 2 mạng khác nhau.

## 5. Ràng buộc mang theo từ Q93 (không được rơi khi tích hợp)

- Luồng điều khiển **không** đi qua control plane (ràng buộc 3): Agent cấu hình
  RustDesk trỏ thẳng relay LTT, control plane chỉ cấp vé.
- Engine phải **kiểm vé**, không chỉ control plane cấp (ràng buộc 2): thể hiện
  qua mật khẩu-một-lần mà Agent chỉ đặt **sau khi** thấy vé hợp lệ.
- Chỉ báo phiên không tắt được + nút ngắt (ràng buộc 7) — V7.
- Không copy/link mã AGPL vào Agent; không "custom client generator" (Q97).

## 6. Trạng thái

**BLOCKED trên phần cứng, KHÔNG trên giấy phép.** Thiết kế xong ở mức giả thuyết;
bảy câu V1–V7 cần 2 VM + binary RustDesk để chuyển từ giả thuyết thành sự thật.
Chủ sản phẩm đã đề nghị cấp 2 VM qua RDP — đó là đầu vào còn thiếu duy nhất.
