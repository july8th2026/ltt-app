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

- [x] **Hai bước + bảng tóm tắt sống** — nằm trong `vps.html`, không tách tệp
      riêng: một trang, một biểu mẫu. Tóm tắt hiện **số credit sẽ trừ** và **số dư
      còn lại** trước khi bấm; bản trước hiện giá bằng đồng ở một chỗ, số credit ở
      chỗ khác, số dư chỉ trên thanh tiêu đề — ba mảnh của cùng một phép tính.
      *Đo bằng trình duyệt thật:* chọn VPS Lớn (3.290) với số dư 2.000 → "Còn lại
      **−1.290 credit**" màu đỏ + cảnh báo, danh sách OS tự giãn từ 2 lên 5 bản.
      ⚠️ Bản đầu của tôi phá một chốt an toàn: nó hiện biểu mẫu **luôn**, kể cả
      khi không đọc được sức chứa. Hai thứ bị gộp nhầm — *hiện bảng giá* và *cho
      đặt mua*. Nay bảng giá hiện luôn (chỉ đọc), biểu mẫu chỉ khi bán được.
- [x] `vps.html` — bảng máy + thanh băng thông + cảnh báo gia hạn
- [x] `vps_chi_tiet.html` — bốn khối + sao kê + ảnh chụp + khôi phục
- [x] Proxy noVNC + vé dùng-một-lần
- [x] Điều khoản LTT VPS + clickwrap ngay dưới nút
- [x] **Trang bán công khai (chưa đăng nhập)** — ✅ 25/08.

      **Một URL, hai loại người xem.** `/vps` phục vụ cả hai chứ không tách thành
      `/vps` + `/vps/bang-gia`. Lý do cụ thể: thẻ app trong catalog hiện cho cả
      khách chưa đăng nhập, nên `/vps` đòi đăng nhập = người lạ bấm vào rơi thẳng
      vào trang đăng nhập — **ngõ cụt ở đúng bước đầu của phễu bán hàng**. Hai URL
      thì lại có hai trang cùng nói về một sản phẩm, và chúng sẽ lệch nhau.

      Khách ẩn danh thấy: sản phẩm là gì → điều kiện ("Đọc trước khi thuê") →
      bảng giá chỉ đọc → hai nút *Đăng nhập để thuê máy* / *Tạo tài khoản* →
      liên kết điều khoản. Khách đã đăng nhập thấy máy của mình và biểu mẫu.

      **Thứ tự đó là kết quả của việc nhìn trang render thật.** Bản đầu đặt sáu
      dòng cảnh báo TRƯỚC khi nói đây là cái gì — người chưa biết sản phẩm mà đọc
      sáu điều nó không hứa thì đóng tab, không đọc tiếp.

      **Mở cho khách ẩn danh KHÔNG kéo theo ba thứ** (mỗi thứ một chốt trong
      `test_252`): không lộ máy của người khác — `_may_cua_toi(db, "")` sẽ quét
      cả bảng, nên nhánh ẩn danh phải *không gọi* nó chứ không phải gọi rồi lọc;
      không dựng biểu mẫu sẽ POST rồi ăn 401; và **cổng cờ `LTT_VPS` vẫn đứng
      trước** — công khai nghĩa là "không đòi đăng nhập", không phải "bỏ qua cờ".

      ⚠️ **Hai lỗi chỉ nhìn thấy khi render thật, không test nào bắt được:**

      1. Cột thông số hiện là *"Settings"* trong bản tiếng Anh — msgid `"Cấu hình"`
         dùng chung với liên kết admin `⚙ Cấu hình` trỏ tới `/settings`. Đã tách
         `"Cấu hình máy"` → *"Specs"*.
      2. **App đang TẮT vẫn hiện thẻ trên trang chủ của người đã đăng nhập**, mà
         route trả 404 — lại đúng cái ngõ cụt trên. `server/templating.py` (thanh
         bên + header) và nhánh ẩn danh của `dashboard.py` đều lọc
         `manifest.enabled`; nhánh đã-đăng-nhập thì không. Lỗi **có sẵn từ trước**,
         không phải do `public=True`: nhánh đó trả `authenticated or public` nên
         `public=False` cũng lọt y hệt. Đã sửa + chốt test.
- [ ] Kiểm trên **URL công khai** `https://app.lttstudios.com` — chỉ làm được sau
      khi đặt `LTT_VPS=1`; hiện `/vps` trả 404 đúng như fail-closed phải thế
- [x] Asset tĩnh đính `?v={{ asset_ver }}` (dùng chung `ltt.css`, không thêm asset mới)

## Nguồn

- [Vultr — How to Provision Cloud Compute Instances](https://docs.vultr.com/products/compute/instances/cloud-compute/provisioning)
- [Vultr Review 2026 — mô tả luồng hai màn và bảng tóm tắt](https://betterstack.com/community/guides/web-servers/vultr-review/)
