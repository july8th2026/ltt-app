# N3.2 Rổ 2 — fork RustDesk mang thương hiệu LTT (spec để thực thi ngoài repo này)

> Lập 2026-08-20 sau Q100 (Rổ 2). File này là **spec**, không phải code: fork
> RustDesk là một **repo riêng** (Flutter + Rust) và build cần một máy có Rust +
> Flutter + Windows — không dựng được từ trong repo nền tảng này. Charter §2/§4:
> chuẩn bị đầy đủ ở đây, đánh dấu phần cần máy/repo.

## 1. Nguồn fork — ghim đúng, không `latest`

- Fork từ `rustdesk/rustdesk` tại commit **`6c578292e8ebbbec708b76986ba8c4bc7c509747`**
  (v1.4.9, đã ghim ở `03_OSS_LICENSE.md` §2 — cùng commit đã đo V1–V8).
- Repo fork **PHẢI công khai** (nghĩa vụ AGPL Q100): người dùng của LTT tương tác
  qua mạng với bản đã sửa, nên Corresponding Source phải công bố.

## 2. Sửa gì — ánh xạ P-item → nguồn (rule 6: mỗi sửa là MỘT commit theo dõi được)

| P | Nội dung | Chạm đâu (định vị, xác minh khi có source) |
|---|---|---|
| P1 | Đổi tên "RustDesk"→"LTT Nexus", logo, màu Carbon Red | `flutter/` assets + `libs/hbb_common` app name; `res/` icon |
| P2 | Hệ thiết kế LTT trong Flutter (token màu/typo/spacing) | `flutter/lib/` theme; **KHÔNG** dùng lại `ltt.css` (web) — tái hiện |
| P3 | Restyle cửa sổ điều khiển + thanh công cụ | `flutter/lib/desktop/` remote toolbar |
| P4 | Chỉ báo phiên tuỳ biến + nút ngắt (ràng buộc 7, giải V7) | phía máy ĐÍCH: overlay "đang bị điều khiển"; RustDesk có sẵn, cần cường hoá không-tắt-được |
| P5 | Gỡ address book / marketplace / settings nhạy cảm | `flutter/lib/` các trang tương ứng |
| P6 | Việt hoá | `flutter/lib/common.dart` i18n + `flutter/lib/models` |
| P7 | **Luồng đăng nhập LTT** (đường Sâu) — client tự kết nối bằng vé LTT, khách không thấy ID/mật khẩu | `flutter/lib/models/*` connection flow + `src/client.rs`; nhận (server, id, mật khẩu) từ Agent LTT qua IPC/tham số dòng lệnh |
| P8 | Móc telemetry/audit về LTT | điểm bắt đầu/kết thúc phiên ở client |

**Nhúng cấu hình server (thay file `.toml` phơi ra):** hai đường —
(a) build-time env `RENDEZVOUS_SERVER` + `RS_PUB_KEY` khi biên dịch (RustDesk hỗ
trợ sẵn, **không** sửa source), hoặc (b) hardcode default trong source (là sửa,
Rổ 2). Chọn (a) nếu chỉ cần nhúng địa chỉ; (b) khi đã sửa branding thì tiện thể.

## 3. Ranh giới AGPL phải giữ khi build fork (Q100 + 03_OSS_LICENSE §5)

- **Không copy/link mã fork (AGPL) vào LTT Nexus Agent.** Agent gọi engine qua
  tiến trình + IPC/tham số dòng lệnh, không chung không gian địa chỉ. Đây là thứ
  giữ Agent (độc quyền) khỏi bị kéo vào nghĩa vụ mở mã.
- **Mọi sửa đổi là commit riêng** trên fork công khai (rule 6) — vì đó chính là
  Corresponding Source phải công bố.
- `THIRD_PARTY_NOTICES` cập nhật: giờ là bản **đã sửa**, phải trỏ tới **fork của
  LTT** (không chỉ upstream) + kèm source-offer.

## 4. Cần máy/repo (charter §4) — không làm được trong repo nền tảng

- [ ] Tạo repo fork công khai tại commit đã ghim.
- [ ] Máy build: Rust + Flutter + Windows (RustDesk build theo `build.py` của họ).
- [ ] Áp P1–P8 thành các commit riêng; build ra `ltt-nexus-<ver>.exe`.
- [ ] Trỏ `LTT_NEXUS_RUSTDESK_EXE` (đã có trong `engine_runner.py`) tới binary fork.
- [ ] Legal review (E16) trước phát hành thương mại.

## 5. Đường Sâu của P7 — hợp đồng với Agent (thiết kế sẵn)

Agent LTT (đã có `engine_runner.py`) xoay mật khẩu + lấy ID rồi báo server (W4).
Đường Sâu thêm: **bên điều khiển** cũng là client fork, nhận (server, id, mật
khẩu) từ LTT — hoặc qua tham số dòng lệnh `--connect <id>` + mật khẩu nhúng, hoặc
qua URI `rustdesk://`. Khách bấm "điều khiển" trên web → web trả một liên kết mở
client fork với sẵn thông tin (từ `lay_ket_noi`, W5) → client tự nối, khách không
gõ gì. Chi tiết cách client fork nhận mật khẩu không-tương-tác là việc **đo trên
source fork** (giống V-series đã làm cho stock), không đoán ở đây.
