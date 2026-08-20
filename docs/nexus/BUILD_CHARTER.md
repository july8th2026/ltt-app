# Hợp đồng vận hành tự động — LTT Nexus

> Lập 2026-08-20. Chủ sản phẩm cấp **full quyền** và yêu cầu **tự triển khai
> liên tục, không xác nhận từng bước**. File này ghi rõ tôi tự quyết gì, và cái
> gì vẫn dừng lại báo — vì "full quyền" nghĩa là tự quyết mọi thứ *an toàn để tự
> quyết*, không phải bỏ mọi lằn ranh.

## 1. Tự quyết + tự làm, KHÔNG hỏi

- Mọi code/config/test/docs trong repo, trên nhánh dev.
- Sửa lỗi, sửa gate/test đỏ, refactor, đổi thiết kế kỹ thuật.
- Theo **khuyến nghị của chính tôi** ở các ngã rẽ kỹ thuật (vd đường "Sâu" của
  P7 — tôi đã khuyến nghị, nên tôi đi luôn, đánh dấu đảo được).
- Tham số chưa chốt (giá, chu kỳ…): xây **config-driven**, đặt mặc định hợp lý +
  TODO, **tắt mặc định** để không tự bật thứ chưa duyệt. Không chặn build.
- Chạy test, gate, commit sau mỗi lát cắt xanh.

## 2. Làm-tới-nơi rồi ĐÁNH DẤU (không chặn, làm song song việc khác)

Những việc chỉ người làm được — tôi chuẩn bị sẵn hết (script/khoá giả/checklist)
rồi ghi vào "§4 Cần bạn", tiếp tục việc khác:

- **Sinh khoá phát hành THẬT** — khoá riêng phải do bạn giữ, ngoài máy.
- **Build/ký trên máy Windows sạch** có PyInstaller.
- **Legal review** (người ngoài).
- **Con số giá** cuối cùng.

## 3. DỪNG LẠI BÁO — lằn ranh cứng, giữ kể cả khi full quyền

- **Không gõ mật khẩu vào ô đăng nhập** (lằn ranh cũ; chỉ có giá trị khi không
  ngoại lệ — nhất là với sản phẩm điều khiển máy từ xa).
- **Không lách cơ chế an toàn** (đã bị chặn tscon/restart-hbbs; đó là gác đúng).
- **Không tự tay đụng PRODUCTION đang phục vụ khách**: migrate CSDL prod, bật
  `LTT_NEXUS` trên máy live, deploy. Máy chủ này **đang chạy thật**
  (`LTTStudioWeb`/`Worker`/`cloudflared` Running). Build hết trên dev, chuẩn bị
  sẵn, **báo trước khi áp lên prod**. Đây là "hard to reverse + outward-facing".
- **Không xoá/ghi đè không đảo được** mà không có checkpoint.

## 4. Cần bạn (danh sách sống — tôi cập nhật khi phát sinh)

- [ ] Chốt độ sâu P7: **Sâu** (khuyến nghị, tôi đang đi) hay Nhẹ.
- [ ] Con số giá/máy/tháng + chu kỳ + ân hạn (D12).
- [ ] Sinh khoá phát hành thật (C10) + build trên Windows sạch (C11).
- [ ] Legal review trước bán (E16).
- [ ] Cho phép migrate + bật cờ trên PRODUCTION (E14).
- [ ] Hạ tầng: đổi mật khẩu VPS đã lộ; siết relay đang mở ra Internet (E15).

## 5. Thứ tự Phase

| Phase | Nội dung | Tự làm được? |
|---|---|---|
| **1** | Wiring W1–W5 (vé → kết nối thật) | ✅ toàn bộ |
| **2** | Fork + tuân AGPL B6–B7 (fork, config nhúng, build+công bố mã) | ✅ phần lớn |
| **3** | Cá nhân hóa P1–P8 (branding + design Flutter + luồng đăng nhập LTT) | ✅ phần lớn; build cần máy |
| **4** | Đóng gói & phát hành C11–C12 | ⚠️ build cần Windows sạch |
| **5** | Thanh toán D13–D14 (config-driven, tắt mặc định) | ✅ cơ chế; số giá của người |
| **6** | Vận hành & thương mại E15–E18 | ⚠️ prod + legal của người |

Chạy tuần tự; trong mỗi Phase, mỗi lát cắt: viết → test → gate → commit. Không
dừng giữa các Phase; chỉ dừng ở §3 hoặc khi cạn việc tự-làm-được rồi báo §4.
