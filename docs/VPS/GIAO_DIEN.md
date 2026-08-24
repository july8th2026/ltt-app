# Giao diện bán và quản lý VPS (H39/G8)

> Tham chiếu: luồng tạo máy của Vultr, đọc 2026-08-24. Không sao chép giao diện —
> lấy **thứ tự quyết định** của họ, vì thứ tự đó đã được hàng triệu lượt dùng mài giũa.

## Điều Vultr làm đúng, và ta lấy lại

Vultr **tách luồng tạo máy làm hai màn**, cố ý: màn một chọn **phần cứng**
(vùng → gói), màn hai chọn **phần mềm** (hệ điều hành → xác thực → tên máy). Bên phải
luôn có **bảng tóm tắt cập nhật trực tiếp**: cấu hình đang chọn và giá, hiện *trước*
khi bấm nút cuối.

Hai điều đó giải quyết đúng hai nỗi sợ của người mua: *"tôi đang mua cái gì"* và
*"nó tốn bao nhiêu"*. Tách hai màn còn giúp không ai phải nhìn 30 lựa chọn cùng lúc.

Ta lấy nguyên nguyên tắc đó, nhưng **rút gọn mạnh** — Vultr có 32 vùng và 6 họ gói,
ta có **1 vùng và 3 gói**. Bê nguyên giao diện của họ vào một cửa hàng 3 gói là làm
khó khách một cách vô cớ.

## Luồng tạo máy của ta — hai bước, một trang

```
┌─ Bước 1 · Chọn máy ───────────────────┐   ┌─ Tóm tắt ──────────────┐
│  Khu vực:  [Singapore ▾]              │   │  VPS Vừa               │
│                                       │   │  2 vCPU · 4 GB · 60 GB │
│  ○ Nhỏ    1 vCPU · 2 GB · 40 GB       │   │  Băng thông 200 GB/th  │
│  ● Vừa    2 vCPU · 4 GB · 60 GB       │   │  IP riêng Singapore    │
│  ○ Lớn    4 vCPU · 8 GB · 80 GB       │   │  ──────────────────    │
│                                       │   │  179.000 đ / 30 ngày   │
├─ Bước 2 · Chọn hệ điều hành ──────────┤   │  = 1.790 credit        │
│  ● Windows Server 2022 (có giao diện) │   │                        │
│  ○ Windows Server 2022 (Core)         │   │  Số dư: 4.200 credit   │
│  ○ Windows 10                         │   │  Sau khi mua: 2.410    │
│                                       │   │                        │
│  Tên máy: [may-cua-toi____________]   │   │  [ Tạo máy ]           │
└───────────────────────────────────────┘   └────────────────────────┘
```

**Vì sao một trang chứ không hai:** Vultr cần hai trang vì họ có 32 vùng × 6 họ gói.
Ta có 3 gói. Bắt khách bấm "Tiếp theo" giữa hai màn chỉ để chọn 3 thứ là thêm ma sát
mà không đổi lại được gì.

**Bảng tóm tắt là phần bắt buộc.** Nó phải hiện **số credit sẽ trừ ngay** và **số dư
còn lại sau khi mua** — nền tảng bán theo credit, và người mua cần thấy hai con số đó
trước khi bấm, không phải sau.

## Ba dòng cảnh báo bắt buộc (V14 + đo thật 2026-08-24)

Đặt **ngay dưới bảng tóm tắt**, không giấu trong điều khoản:

1. **Dung lượng đĩa là hạn mức trên kho lưu trữ dùng chung**, không phải ổ cứng cấp
   riêng. Kho đầy thì mọi máy đều không ghi thêm được, dù máy anh chưa chạm trần.
2. **Băng thông có hạn mức** (100/200/400 GB tuỳ gói). Vượt thì bị **giảm tốc**, không
   bị tính thêm tiền. — *Đây là con số thật: gateway có 2.048 GB/tháng chia cho mọi khách.*
3. **Dịch vụ chạy trên hạ tầng riêng, không có cam kết SLA.** Máy chủ đặt tại Việt Nam,
   đường vào qua Singapore.

Dòng 2 quan trọng hơn nó trông: **không công bố hạn mức thì một khách tải phim cả
tháng ăn hết quota của 15 người còn lại**, và ta không có cơ sở nào để giảm tốc họ.

## Sau khi bấm "Tạo máy"

Đi qua **hàng đợi job** như mọi app khác của nền tảng (Cloudflare cắt ở 100 giây; tạo
máy Windows mất vài phút). Trang tiến trình dùng lại thành phần sẵn có:

```
[  5%] đang xin chỗ trên máy chủ
[ 15%] đang nhân bản hệ điều hành
[ 45%] đang cấp địa chỉ IP
[ 60%] đang đặt cấu hình
[ 85%] đang khởi động
[100%] xong — máy của bạn đã sẵn sàng
```

Xong thì hiện **thông tin đăng nhập, đúng một lần**:

```
Địa chỉ   45.77.45.29          [sao chép]
Tài khoản Administrator
Mật khẩu  ••••••••••  [hiện] [sao chép]

⚠ Mật khẩu này chỉ hiện MỘT LẦN. Lưu lại ngay.
   Mất thì phải đặt lại từ trang quản lý máy.
```

Cùng khuôn với việc `setup\2-cai-dat.ps1` in mật khẩu admin đúng một lần — nền tảng
này đã có tiền lệ, giữ cho nhất quán.

## Danh sách máy của khách

| Tên | Địa chỉ IP | Gói | Trạng thái | Băng thông | Gia hạn |
|---|---|---|---|---|---|
| may-cua-toi | 45.77.45.29 | Vừa | ● đang chạy | ▓▓▓▓░░ 62 % | còn 18 ngày |
| thu-nghiem | 45.77.45.31 | Nhỏ | ○ đã tắt | ▓░░░░░ 8 % | còn 3 ngày ⚠ |

Bốn cột đầu là chuẩn chung của mọi trang VPS. **Hai cột cuối là của riêng ta** và
quan trọng hơn ở đây so với Vultr:

- **Băng thông** phải hiện ngay ở danh sách, không giấu trong trang chi tiết — vì nó
  là tài nguyên khan hiếm nhất của mô hình này.
- **Gia hạn** phải cảnh báo sớm: máy bị **treo ngay khi hết hạn và xoá sau 7 ngày**
  (V8). Khách mất máy vì không biết sắp hết hạn là lỗi của giao diện, không phải của họ.

## Trang chi tiết một máy

Bốn khối, theo thứ tự người ta thực sự cần:

1. **Tổng quan** — IP, tài khoản, cấu hình, ngày gia hạn, nút *Đặt lại mật khẩu*.
2. **Đồ thị băng thông** — đã dùng / hạn mức, theo ngày trong chu kỳ hiện tại.
3. **Console** — noVNC nhúng, cho lúc khách tự chặn mất đường RDP của mình. Vé
   `vncproxy` **dùng-một-lần**, proxy qua server ta; khách **không bao giờ** chạm
   cổng 8006 của Proxmox.
4. **Nguy hiểm** — Cài lại (mất sạch dữ liệu) · Xoá máy. Cả hai đòi gõ đúng tên máy
   để xác nhận, khuôn của GitHub — vì hai nút này không hoàn tác được.

## Trang bán (chưa đăng nhập)

Bảng ba gói, giá theo tháng, và **một câu giải thích vì sao địa chỉ ở Singapore**:
máy chủ đặt tại Việt Nam, đường vào đi qua Singapore để có IP tĩnh ổn định. Nói thẳng
tốt hơn để khách tự phát hiện rồi nghĩ ta giấu.

Không dùng chữ "cloud", "không giới hạn", "99,9 % uptime" — ta không có SLA, và một
câu quảng cáo sai là một vụ tranh chấp về sau.

## Việc phải làm (G8)

- [ ] `server/templates/vps_tao.html` — hai bước + bảng tóm tắt cập nhật trực tiếp
- [ ] `server/templates/vps_danh_sach.html` — bảng + thanh băng thông + cảnh báo gia hạn
- [ ] `server/templates/vps_chi_tiet.html` — bốn khối ở trên
- [ ] Proxy noVNC + vé dùng-một-lần (chung với G3)
- [ ] Trang bán công khai + điều khoản (chung với G10)
- [ ] Kiểm trên **URL công khai** `https://app.lttstudios.com`, không chỉ loopback
      (quy tắc 5b của `CLAUDE.md` — Cloudflare từng phục vụ CSS cũ 4 tiếng)
- [ ] Đính `?v={{ asset_ver }}` cho mọi asset tĩnh mới (quy tắc 6)

## Nguồn

- [Vultr — How to Provision Cloud Compute Instances](https://docs.vultr.com/products/compute/instances/cloud-compute/provisioning)
- [Vultr Review 2026 — mô tả luồng hai màn và bảng tóm tắt](https://betterstack.com/community/guides/web-servers/vultr-review/)
