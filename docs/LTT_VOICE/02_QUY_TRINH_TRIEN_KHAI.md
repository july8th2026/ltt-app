# LTT VOICE — quy trình triển khai

> Viết sau lần deploy **thật** ngày 2026-08-30, gồm cả một sự cố **production nằm
> 19 phút**. Mọi bước dưới đây đã chạy trên máy A; các cảnh báo là chỗ đã trả giá,
> không phải chỗ phòng xa.

---

## 0. Đọc trước: ba thứ khác hẳn deploy thường

| | LTT VOICE khác chỗ nào |
|---|---|
| **Dịch vụ thứ tư** | `LTTStudioVoice`. Nó có `AppDirectory` trỏ `app\` nên **giữ handle** trên thư mục đó — mọi thứ xoay `app\` phải dừng nó **đầu tiên** |
| **Venv thứ hai** | `C:\LTTPlatform\vieneu-venv`, **8 GB**. Sống ngoài `app\`, không bị `update.ps1`/`rollback.ps1` đụng tới |
| **Cache model** | `C:\LTTPlatform\hf-cache`, 305 MB, ghim theo revision |

⛔ **Venv và cache không nằm trong bản sao lưu và cũng không cần.** Chúng dựng lại
được từ `requirements-vieneu.txt`. Nhưng dựng lại mất ~15 phút, nên đừng xoá vì
thấy thư mục to.

---

## 1. Cài lần đầu (máy chưa có LTT VOICE)

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\deploy_nang_quyen.ps1
```

Lớp ngoài xin UAC, lớp trong chạy `2-cai-dat.ps1` và ghi
`C:\LTTPlatform\logs\deploy-<mốc>.ket.txt`.

**Thứ tự các bước, và vì sao nó là thứ tự này:**

```
1  kiem ma nguon bien dich duoc
2  WhisperX sidecar          <- venv rieng, ~3,5 GB
3  Venv giong noi (VIENEU)   <- venv rieng, ~8 GB
   ────────── moi thu tren day chay khi DICH VU VAN DANG CHAY ──────────
4  Copy ma nguon             <- Stop-Service o day. Cua so downtime BAT DAU
5  moi truong Python, cau hinh, PostgreSQL, migration
6  dang ky bon dich vu       <- chi vai giay moi cai
7  Khoi dong + kiem suc khoe <- cua so downtime KET THUC
```

🔴 **Bước 2 và 3 nằm trên vạch có lý do đã trả giá.** Ngày 30/08 bước 3 nằm
**dưới** vạch, giữa lúc dịch vụ đang tắt. Một lần tải 3.461 MB (torch cu128) dài
đúng bằng một khoảng production sập; tiến trình nâng quyền chết trong lúc tải, và
`.ket.txt` có `EXITCODE` **rỗng**.

⭐ Chính `deploy_nang_quyen.ps1` đã ghi sẵn *"EXITCODE rỗng khác hẳn EXITCODE=0 —
rỗng nghĩa là tiến trình không chạy"*. Nhờ dòng đó mà biết ngay là chết giữa
chừng chứ không phải hỏng ở bước cuối.

⛔ **Bài học rộng hơn LTT VOICE: đừng đặt một việc DÀI và CÓ THỂ HỎNG vào giữa
cửa sổ ngừng dịch vụ.** Cài venv không cần dịch vụ nào dừng cả; nó nằm dưới chỉ
vì nó *"thuộc về"* app đó trong đầu người viết. **Sự gần gũi về mặt khái niệm
không phải lý do để xếp thứ tự thi hành.**

`tests/test_45::test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu` giờ chặn việc
này — cho cả hai sidecar.

---

## 2. Cập nhật một máy đã có LTT VOICE

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\update.ps1 -SourceZip <ban>
```

```
DUNG :  LTTStudioVoice -> LTTStudioCodex -> LTTStudioWorker -> LTTStudioWeb
        (nguoc chieu phu thuoc; Voice DAU TIEN vi no giu handle tren app\)
        ↓ backup data -> xoay app\ -> bung ban moi
        ↓ pip install lai venv nen tang
        ↓ alembic upgrade head
BAT  :  Web -> Worker -> Codex -> Voice
        (Voice sau cung: no nap ~320 MB len GPU, mat ~20 giay moi san sang)
        ↓ 4-nghiem-thu.ps1
```

⚠️ `update.ps1` **không** dựng lại `vieneu-venv`. Đó là chủ ý — venv ghim theo
phiên bản và sống ngoài `app\`. Đổi phiên bản trong `requirements-vieneu.txt` thì
phải chạy §3 riêng.

---

## 3. Sửa **một** dịch vụ giọng — không đụng production

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\cai_dich_vu_giong.ps1
```

⭐ **Vì sao có script riêng thay vì chạy lại bộ cài.** Sau sự cố 30/08, đường sửa
*hiển nhiên* cho một dịch vụ chưa đăng ký được là *"chạy lại `2-cai-dat.ps1`"* —
và đó đúng là nước đi sai: script đó dừng Web, Worker và Codex để xoay `app\`.
**Chạy lại cả bộ cài để sửa một dịch vụ là đưa production xuống lần hai, cho một
lỗi không liên quan gì đến ba dịch vụ kia.**

⛔ **Một bản sửa không được tốn hơn chính lỗi nó sửa.**

Script này chỉ làm hai việc của LTT VOICE — dựng venv, đăng ký `LTTStudioVoice` —
và **không dừng gì cả**. Đã chạy thật: bốn dịch vụ đều Running, ba dịch vụ cũ
không gián đoạn một giây.

Nghiệm thu nằm trong chính script: nó **hỏi `/live`**, không tin trạng thái
Windows. *Một dịch vụ `Running` mà không trả lời là đúng thứ Windows gọi là thành
công còn người dùng gọi là hỏng.*

---

## 4. Nghiệm thu

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\4-nghiem-thu.ps1
```

Bốn chốt riêng của LTT VOICE:

| Chốt | Đạt khi |
|---|---|
| Dịch vụ | `LTTStudioVoice` = Running |
| Cổng giọng | `GET 127.0.0.1:8120/live` → `{"ok":true}` (**không cần khoá**) |
| Làn worker | `LTT_WORKER_POOLS` không đặt, **hoặc** có làn `voice` |
| App nạp được | `ltt_voice /ltt-voice ok` trong danh sách 15 app |

🔴 **Chốt làn worker là chốt duy nhất bắt được một lỗi hoàn toàn im lặng.**
`platform_core/jobs.py` lọc bằng `set(manifest.requires).issubset(capabilities)`.
LTT VOICE khai `requires=("voice",)`. Nếu production **đã** đặt `LTT_WORKER_POOLS`
mà thiếu làn `voice` thì job nằm `queued` **mãi mãi** — không lỗi, không cảnh
báo, `/health/ready` vẫn 200, và khách chỉ thấy "đang xử lý" không bao giờ xong.

*(Trên máy A hôm nay `LTT_WORKER_POOLS` **không đặt** ⇒ worker đa năng ⇒ an toàn.
Chốt tồn tại cho ngày ai đó đặt nó.)*

---

## 5. Kiểm giao diện thật (quy tắc 5 / 5b của `CLAUDE.md`)

⛔ **Test xanh không chứng minh trang hiển thị đúng**, và **loopback không chứng
minh khách thấy đúng** — loopback bỏ qua Cloudflare (cache, CSP biên, minify).

### 5.1 Tài khoản thử

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\tai_khoan_thu.ps1 -LietKe
powershell -ExecutionPolicy Bypass -File .\setup\tai_khoan_thu.ps1
```

⚠️ **Đừng chuyển hướng toàn bộ đầu ra (`*> file.log`).** Công cụ in mật khẩu ra
màn hình đúng một lần; ngày 30/08 tôi chuyển hướng cả stdout và mật khẩu nằm
trong `C:\LTTPlatform\logs\` cho tới khi xoá tay. **Một bí mật trong thư mục log
là một bí mật trong mọi bản sao lưu.**

Ba điều công cụ **cố ý không làm**:

- **không nạp credit** — sổ tiền chỉ ghi thêm; một khoản tự cấp sẽ nằm trong mọi
  báo cáo doanh thu về sau như một mục không ai giải thích được;
- **không đặt `role=admin`** — mục đích là kiểm **bề mặt khách hàng**, và admin
  nhìn thấy thứ khách không thấy nên nó chứng minh sai thứ;
- **không nhận email ngoài đuôi `.local`** — tài khoản thử không được nhận thư
  thật, và một địa chỉ không tồn tại làm điều đó chắc chắn.

### 5.2 Bốn màn phải xem

| Màn | Phải thấy |
|---|---|
| `/ltt-voice` | ô văn bản, bộ đếm ký tự + credit tạm tính, chọn giọng, bảng giá mở ra được |
| `/ltt-voice/giong` | bảng giọng, biểu mẫu tạo giọng, **điều khoản + ô cam kết** |
| `/ltt-voice/lich-su` | bảng lịch sử, trình phát cho mỗi lượt đã xong |
| thẻ ở trang chủ | biểu tượng 🎙️, nhãn "Đang phát triển", nút gọi hành động |

Mỗi màn kiểm ba thứ: **console không lỗi**, **không request nào hỏng**, và
`ltt.css?v=<hash>` — thiếu tham số version là CSS cũ tới tay khách trong 4 giờ.

### 5.3 Luồng cần credit

Tạo tiếng và ghi danh giọng đều là job trả phí, nên tài khoản 0 credit **không
chạy được**. Nạp credit là **quyết định của chủ sản phẩm**, không phải của một
lượt kiểm thử.

---

## 6. Lùi bản

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\rollback.ps1
```

Đổi `app.previous` về `app`, dừng/bật bốn dịch vụ đúng thứ tự §2.

⚠️ **`vieneu-venv` và `hf-cache` KHÔNG bị lùi** — chúng ngoài `app\`. Nếu bản mới
đã nâng `vieneu` thì lùi mã mà không lùi venv là lệch, và **cách duy nhất phát
hiện là kiểm phiên bản** — đó là lý do `install-vieneu-sidecar.ps1` idempotent
**theo phiên bản**, không theo *"thư mục đã tồn tại"*.

---

## 7. Sự cố hay gặp

| Triệu chứng | Nguyên nhân thật |
|---|---|
| Job VOICE `queued` mãi, không lỗi | `LTT_WORKER_POOLS` thiếu làn `voice` (§4) |
| Cờ mới không tác dụng sau khi sửa `app.env` | nssm nướng env vào đăng ký dịch vụ **lúc cài** → chạy `setup\nap_lai_env.ps1` |
| Cập nhật ném lỗi ở `Move-Item` | quên dừng `LTTStudioVoice` — nó giữ handle trên `app\` |
| App hiện "cần thiết lập" | `LTT_VOICE_SIDECAR_TOKEN` chưa có, hoặc dịch vụ chưa chạy → §3 |
| Dịch vụ `Running` mà `/live` không trả lời | model đang nạp (~20 giây lần đầu), hoặc xem `logs\voice-err.log` |
| Tiếng ra **không có watermark** | gói `perth` sai quay lại sau một lần cài → chạy lại §3; sidecar phải **từ chối khởi động** khi watermarker rỗng |
| `pip` hỏng `[WinError 32]` giữa chừng | một tiến trình đang giữ `.pyd` trong venv — dừng mọi python của `vieneu-venv` rồi chạy lại |
| `EXITCODE` **rỗng** trong `.ket.txt` | tiến trình **không chạy hết**, khác hẳn `EXITCODE=0`. Kiểm dịch vụ **ngay** — production có thể đang nằm |

---

## 8. Nếu production đang nằm

```powershell
Start-Service LTTStudioWeb; Start-Service LTTStudioWorker
Start-Service LTTStudioCodex; Start-Service LTTStudioVoice
```

Rồi **hỏi nó**, đừng tin trạng thái dịch vụ:

```powershell
Invoke-RestMethod http://127.0.0.1:8100/health/ready
```

⭐ Ngày 30/08 cách này đưa production lên lại trong **13 giây** sau khi phát hiện.
Thời gian mất đi không nằm ở việc sửa — nó nằm ở khoảng **giữa lúc hỏng và lúc
biết là đã hỏng**. Đó mới là chỗ đáng rút ngắn, và cách rút ngắn nó là đọc
`.ket.txt` ngay khi một lượt deploy không kết thúc như mong đợi.
