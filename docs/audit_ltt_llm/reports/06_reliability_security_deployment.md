# Prompt 06 — Reliability, Security, Deployment (phần đã thi hành)

**31/08/2026, 21:20–22:00.** Ownership: F01–F28.

⚠️ **Phase này CHƯA đóng.** Nó nhận hai `CHANGE` treo từ Prompt 03/04 và thi
hành chúng vì cả hai đang ảnh hưởng khách thật. Phần còn lại của F01–F28 (tiêm
lỗi, mô hình health, bảng quan sát, quét bảo mật, phong bì năng lực) **chưa
làm** — xem §5.

---

## 1. 🔴 CHANGE đã thi hành: trọng tài nhận nhầm tải của chính ta

### A/B, đo trên cùng bộ đề, cùng máy, cách nhau 40 phút

| | Bị 429 ở lần thử đầu | Chất lượng |
|---|---|---|
| **Trước** (bản cũ) | **9 / 12** | 12/12 |
| **Sau** (đã vá) | **0 / 12** | 12/12 |

Cộng cả bộ hiệu năng, con số trước bản vá là **14/20 = 70 %**.

⭐ Đúng thứ `OPERATING_CONTRACT §6` đòi: lợi ích **đo được**, và **không có hồi
quy chất lượng** — 12/12 cả trước lẫn sau.

### Sửa gì

`llm_gateway/trong_tai.py` — nhánh *"1 python trên card + tải ≥ 50 % ⇒ bận"* nay
hỏi thêm **"model của ta có đang chạy không"**. Nếu có, tải cao ấy là **của ta**.

Lý do chọn điều kiện này chứ không phải một ngưỡng khác: **chính thông điệp của
nhánh nói ra mục đích của nó** — *"nạp model bây giờ sẽ đè lên nhau"*. Nó bảo vệ
thao tác **NẠP**, không phải thao tác phục vụ. Model đã nạp rồi thì không có gì
để nạp.

⚠️ Cái giá, nói thẳng: model ta đã nạp **và** ComfyUI bắt đầu vẽ thật ⇒ ta không
còn từ chối. Chấp nhận được vì `--reserve-vram 3` đã có và VRAM của ta ổn định
22,4 GB. Nếu một ngày dự án video đổi cách dùng card thì **đọc lại chỗ này**.

`tests/test_366` — 8 phép kiểm, gồm một bánh cóc chốt rằng `api.py` **có nối
dây** tín hiệu: sửa `trong_tai.py` mà quên nối thì bản vá không chạy, và triệu
chứng là 70 % từ chối oan **vẫn nguyên, không dòng đỏ nào**.

---

## 2. CHANGE đã thi hành: deploy im lặng về cấu hình chưa có hiệu lực

**Bằng chứng gốc (Prompt 03 §5):**

```
llama-swap.yaml TREN DIA        "input public 65K"   ghi 18:37:35
tien trinh llama-swap           khoi dong           18:34:37
cau hinh DANG CHAY (/running)   "input public 90K"
```

Ba con số, hai sự thật khác nhau, không một dòng cảnh báo.

`deploy.ps1` nay **phát hiện và nói**: sau khi chép, nó hỏi thời điểm khởi động
của `llama-swap` trên máy B; nếu tiến trình cũ hơn tệp vừa chép thì in cảnh báo
kèm lệnh cần chạy.

⛔ Nó **không tự restart**. `llama-swap` restart là **unload model** — một quyết
định vận hành, không phải một bước phụ của deploy. Nhưng im lặng thì không chấp
nhận được.

---

## 3. Deploy & rollback — đã đi thật hai lần hôm nay

| | Máy A | Máy B |
|---|---|---|
| Đường | `setup/deploy_nang_quyen.ps1` → `2-cai-dat.ps1` | `llm_gateway/deploy/deploy.ps1` qua SSH |
| Đã chạy | 18:17 (`EXITCODE=0`) | 18:37 và 21:30 |
| Giữ cấu hình vận hành | `app.env` không đụng | `gateway.env` **migrate giữ token/model** |
| Kênh vào khi SSH tắt | — | **Nexus** (bật SSH tạm, đóng lại sau) |
| Rollback | `app.previous/` | `H:\LTT_LLM\releases\` có bản trước |

⭐ **`gateway.env` migrate tại chỗ** (dòng 114–116 của `deploy.ps1`) — kiểm trước
khi deploy, vì nếu nó sinh token mới thì khoá máy A lưu sẽ lệch và toàn bộ dịch
vụ chết. Nó không sinh mới khi tệp đã tồn tại.

---

## 4. Bảo mật — quan sát trong lúc thi hành (chưa phải quét đầy đủ)

* `sshd` trên máy B trở lại `Disabled` sau mỗi lần dùng; đã đối chiếu cổng 22
  đóng **từ máy A** chứ không chỉ tin lệnh `Set-Service`.
* Máy B **không giữ bí mật nào của nền tảng** — `gateway.env` chỉ có bearer của
  chính nó (43 ký tự) + URL loopback + các trần.
* Cầu hẹp `setup/chay_voi_env.ps1` nạp `app.env` vào **riêng tiến trình**, chạy
  đúng bốn việc trong danh sách trắng, **không in giá trị nào**.
* ⚠️ **Chưa làm:** quét bí mật trong release, quét phụ thuộc/advisory, rà soát
  SSRF của hồ sơ vision (F19, F20, F14).

---

## 5. Còn nợ của phase này

| Mục | Trạng thái |
|---|---|
| F01–F10 tiêm lỗi (A restart, DB transient, worker restart, stale lease, hung stream, B unreachable, gateway/llama-swap crash, CUDA hỏng, mất điện) | **CHƯA** |
| F11–F16 mô hình health + bảng quan sát + chất lượng cảnh báo | **CHƯA** |
| F17–F21 quét bảo mật đầy đủ | **CHƯA** |
| F26 thử rollback thật | **CHƯA** — mới có đường, chưa diễn tập |
| F28 phong bì năng lực / SLO | **CHƯA** |

⛔ Không đánh dấu phase này `PASS`. Hai `CHANGE` đã xong và đo được; phần còn
lại là một phase đầy đủ chưa chạy.
