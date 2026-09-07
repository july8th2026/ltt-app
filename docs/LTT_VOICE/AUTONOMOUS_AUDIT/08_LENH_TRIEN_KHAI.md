# 08 — HAI LỆNH CẦN QUYỀN ADMINISTRATOR (2026-09-05)

Mọi thứ khác đã xong. Hai việc dưới đây cần UAC, và đó là ranh giới của chủ máy
(`lenh-nang-quyen-tren-may-chu`): Claude chuẩn bị hết, người dùng bấm.

⭐ **HAI VIỆC NÀY ĐỘC LẬP VỚI NHAU.** Chạy cái nào trước cũng được:

| | đổi cái gì | ảnh hưởng khi nào |
|---|---|---|
| ① Đổi tên giọng | **dữ liệu** (`voice_profile.ten_hien_thi`) | ngay, không cần deploy |
| ② Deploy | **mã** (`C:\LTTPlatform\app`) | sau khi dịch vụ khởi động lại |

Tên hiển thị đọc từ CSDL, nên ① có tác dụng trên **bản đang chạy hôm nay**.

---

## ① Đổi tên 25 giọng kho chung

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\doi_ten_giong_chung.ps1 -Xem
```

`-Xem` **chỉ in bảng, không ghi gì**. Đọc xong thấy đúng thì:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\doi_ten_giong_chung.ps1 -Ap
```

### Đọc kết quả `-Xem` thế nào

| dòng | nghĩa | phải làm gì |
|---|---|---|
| `-> Tên mới` | khớp `ma_cu`, sẽ đổi | không |
| `KHONG doi (n)` | giọng dùng chung ngoài bảng 25 | xem có đúng không |
| `KHONG CO ma_cu` | `ghi_chu` rỗng/hỏng ⇒ nằm ngoài lượt đổi | báo lại, đừng bỏ qua |
| `[!] TEN DANG CHO LECH` | tên hiện khác bảng — **vẫn đổi** | đọc để biết ai đã đổi tên ngoài công cụ |
| `KHONG AP DUOC` | có lỗi chặn ⇒ **không ghi gì cả** | sửa rồi chạy lại |

⛔ Hoặc cả 25 đổi, hoặc không cái nào — một transaction. Thiếu một `ma_cu` là
   **từ chối cả lượt**, vì "đổi 24/25" là một trạng thái không ai ghi lại được.

⭐ `public_id` (`vc_<32 hex>`) **không đụng tới**, nên khách đang gọi
   `voice_id="vc_…"` không thấy gì khác ngoài cái nhãn.

---

## ② Deploy

⚠️ **Kiểm ngay trước khi bấm** — deploy chép **cả cây**, nên bất cứ thứ gì chưa
commit trong `D:\LTTSTUDIOSAPP` lúc ấy sẽ lên production:

```bash
git status --short
```

Sạch thì chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
```

### Xác minh sau deploy — bằng chính cơ chế lượt này dựng ra

```bash
curl -s https://app.lttstudios.com/health/version
```

Phải thấy ba thứ:

| trường | giá trị đúng |
|---|---|
| `commit` | khớp `git rev-parse --short=12 HEAD` |
| `commit_nguon` | **`marker`** — nếu là `git` thì máy chủ đang chạy từ cây nguồn, **sai chỗ** |
| `hop_dong.ltt_voice.tran_ky_tu_cong_khai` | `100000` |

⛔ Rồi **chốt trên URL công khai**, không dừng ở loopback (quy tắc 5b của
`CLAUDE.md`): loopback bỏ qua Cloudflare, nên trang có thể đẹp ở
`127.0.0.1:8100` mà vỡ với khách thật.

Mở `https://app.lttstudios.com/ltt-voice/` và kiểm **một** thứ: ô đếm phải hiện

    0 / 100.000 ký tự

Trước deploy nó hiện `0 / 1500` — đó là triệu chứng khởi đầu của cả lượt này.

---

## Nếu deploy hỏng

```powershell
# app.previous giu ban truoc do
Move-Item C:\LTTPlatform\app C:\LTTPlatform\app.failed -Force
Move-Item C:\LTTPlatform\app.previous C:\LTTPlatform\app -Force
```

rồi khởi động lại các dịch vụ. ⚠️ Lượt này **không có migration mới**
(`alembic heads` = `7d2c1e9f4a03`, một đầu), nên rollback mã là đủ — không phải
lùi CSDL.
