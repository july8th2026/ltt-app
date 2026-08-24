# ComfyUI có tự khởi động cùng Windows được không?

> ## 📌 VIỆC CÒN NỢ — chủ dự án tự chạy trên máy B
>
> **Đã duyệt 22/08/2026. Script đã sửa xong, đã đẩy sang máy B, đã kiểm parse.**
> Chỉ còn bước cần quyền Administrator mà phiên SSH không nâng được.
>
> **Bước 1** — máy B, PowerShell **Run as administrator**:
> ```
> powershell -ExecutionPolicy Bypass -File E:\AI\ltt_render\gateway\render_gateway\deploy\cai_dat_dich_vu.ps1
> ```
>
> **Bước 2** — ⚠️ ComfyUI **mồ côi** hiện tại vẫn giữ cổng 8188 nên dịch vụ chưa lên
> được. Phải dừng **đúng nó** rồi khởi động dịch vụ:
> ```
> Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
>   Where-Object { $_.CommandLine -like '*ComfyUI*' } |
>   ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
> Start-Service LTTComfyUI
> ```
> 🔴 **SỬA 23/08 — bản cũ ở đây SAI VÀ NGUY HIỂM.** Nó viết
> `Stop-Process -Name python -Force`, mà **cổng VLM và cổng render cũng là
> `python.exe`** (`LTTLlmGateway`, `LTTRenderGateway`). Lệnh đó giết luôn cả hai
> dịch vụ đang phục vụ. Bản trên lọc theo **dòng lệnh**, nên chỉ chạm ComfyUI.
>
> ⏱️ **Chờ hàng đợi ComfyUI rỗng** (`curl http://127.0.0.1:8188/queue`) rồi hãy
> chạy — nếu không sẽ cắt ngang một lượt ảnh hoặc một lượt video.
>
> ✅ **Sau một lần khởi động lại máy thì bước 2 là thừa**: ComfyUI mồ côi đã chết
> theo, cổng 8188 rỗng, chỉ cần `Start-Service LTTComfyUI`.
>
> **Bước 3** — kiểm:
> ```
> Get-Service LTTComfyUI          # phai Running / Automatic
> curl http://127.0.0.1:8188/queue
> ```
>
> **Ba thay đổi đã làm trong script** (§4 giải thích vì sao):
> `+--reserve-vram 3` · `−--cache-ram 24 64` · `+AppKillProcessTree 1`

**2026-08-22.** Nghiên cứu, **chưa làm gì**. ComfyUI trên máy B là thành phần **dùng
chung** của dự án ảnh (H37) và dự án video (`E:\LTT AI`) — đổi cách khởi động nó là
đụng vào cả hai.


## 🔴 Chạy thật 23/08 — ba điều lộ ra

### 1. `AppKillProcessTree` KHÔNG tồn tại trong nssm 2.24

nssm trên máy B là **2.24 (2014-08-31)**. Tham số đó được thêm ở các bản sau, và
ở đó nó dùng để **tắt** hành vi mặc định chứ không phải để bật. Bản 2.24 **vốn đã**
giết cả cây tiến trình khi dừng dịch vụ.

Hậu quả của việc tôi đặt nó: nssm in **một trang lỗi "Invalid parameter"** giữa
chừng script, và người chạy tưởng việc cài hỏng. Đã gỡ khỏi
`render_gateway/deploy/cai_dat_dich_vu.ps1`.

⛔ **Đừng tin, hãy đo:** sau `nssm stop LTTComfyUI`, chạy
`nvidia-smi --query-gpu=memory.used --format=csv`. Còn vài GB nghĩa là ComfyUI
thật còn sống, và lúc đó mới phải tìm cách khác.

### 2. `AppThrottle` trên máy B vẫn là 90000 — bản deploy đã cũ

Bản vá xuống 5000 nằm trong repo ở máy A, nhưng script ComfyUI chạy từ
`E:\AI\ltt_render\gateway\...`, mà đường đó **không** được `llm_gateway/deploy/deploy.ps1`
đồng bộ. Hệ quả: dịch vụ rơi vào `STATE: 7 PAUSED` (nssm đang giãn thời gian chờ)
trong khi SCM đã bỏ cuộc. Đã chép tay script mới sang và đặt `AppThrottle 5000`
cho dịch vụ đang chạy.

### 3. ⚠️ `LTTRenderGateway` NAY PHỤ THUỘC `LTTComfyUI` — và đó là một rủi ro mới

Script đặt `DependOnService = LTTComfyUI`. Nghĩa là **ComfyUI không lên thì cổng
render cũng không lên**. Trước hôm nay cổng render chạy độc lập.

Nếu sau khi khởi động lại mà ComfyUI vẫn hỏng, gỡ ràng buộc để cứu cổng render:

```
E:\AI\ltt_render\scripts
ssm.exe reset LTTRenderGateway DependOnService
sc config LTTComfyUI start= demand
net start LTTRenderGateway
```

### 4. Nguyên nhân gốc hôm 23/08 KHÔNG phải cấu hình dịch vụ

ComfyUI chết vì **CUDA hỏng cả máy**:

```
Windows fatal exception: access violation
  torch/cuda/__init__.py line 529 in _lazy_init
```

Cùng lỗi đã giết `llama-server` (`ggml_cuda_init: failed to initialize CUDA`).
Hai stack độc lập, một nguyên nhân: máy B **tắt không sạch lúc 13:16–13:19**
(sự kiện `1074` → `41` + `6008`). **Phải khởi động lại sạch trước**, mọi thứ khác
là vô nghĩa cho tới lúc đó.

---

## 1. Trả lời ngắn

**Được, và phần kỹ thuật khó nhất đã tự chứng minh rồi.** Nhưng đây **không phải câu
hỏi kỹ thuật** — ba trở ngại thật đều nằm ở chỗ khác.

---

## 2. Hiện trạng đo được

### 2.1. ⭐ CUDA trong session 0 CHẠY ĐƯỢC — đã đo, không phải suy đoán

Tiến trình ComfyUI đang sống ngay lúc này:

```
PID 8564   E:\ai\venv\Scripts\python.exe  main.py --port 8188
           --disable-auto-launch --listen 127.0.0.1 --reserve-vram 3
USER       NT AUTHORITY\SYSTEM
SESSION    0
```

**Nó đang chạy dưới SYSTEM, trong session 0** — đúng môi trường mà một dịch vụ
Windows sẽ chạy. Và nó vừa render ảnh thật trong bài nghiệm thu cổng VLM
(mục 8, `nghiem_thu.py`). Nên câu hỏi "CUDA có hoạt động trong session 0 không" —
thứ mà cộng đồng hay vướng — **đã được trả lời bằng đo đạc trên chính máy này**.

### 2.2. Nhưng nó KHÔNG tự khởi động

| Nơi kiểm | Kết quả |
|---|---|
| Dịch vụ Windows | ❌ không có `LTTComfyUI` |
| Task Scheduler | ❌ chỉ có 2 tác vụ GPU power-limit, **đều Disabled** |
| Thư mục Startup | ❌ chỉ AnyDesk |
| Registry `Run` | ❌ không có |
| **Cha của tiến trình** | **PID 10220 — ĐÃ THOÁT** |

Tiến trình **mồ côi**, sinh lúc **14:11:19 hôm nay**. Cha đã thoát và chạy dưới
SYSTEM ⇒ gần như chắc chắn do **một phiên SSH khởi động rồi đóng phiên** (`sshd`
chạy dưới SYSTEM nên con nó thừa hưởng session 0).

⇒ **Máy khởi động lại là ComfyUI biến mất.** Cả việc ảnh của H37 lẫn việc video đều
chết cho tới khi có người bật tay.

---

## 3. Ba trở ngại thật

### 3.1. 🔴 Phiên H37 đã cân nhắc và **cố ý không làm**

Ghi thẳng trong `render_gateway/deploy/cai_dat_dich_vu.ps1`:

> *ComfyUI trên máy B do **DỰ ÁN VIDEO** dùng chung và **HỌ tự khởi động nó** bằng
> `E:/AI/tools/start_comfy.ps1`. Biến nó thành dịch vụ tự khởi động sẽ:*
> 1. *tranh cổng 8188 với cách khởi động của họ → **một bên chết**;*
> 2. ***XOÁ MẤT cờ `--reserve-vram 3`** mà H37 đặt sau sự cố D-024.*

Script đó có sẵn cờ `-BoQuaComfy` và **mặc định là bỏ qua**. Đây là một quyết định
đã cân nhắc, không phải một thiếu sót.

### 3.2. 🔴 Ba nơi khai cờ, không nơi nào khớp nơi nào

Đây mới là vấn đề cốt lõi, và nó có sẵn từ trước:

| Nguồn | `--reserve-vram` | `--cache-ram` |
|---|---|---|
| `E:\AI\tools\start_comfy.ps1` (dự án video) | ❌ **không có** | ❌ |
| `render_gateway/deploy/cai_dat_dich_vu.ps1` (H37) | ❌ **không có** | `24 64` |
| **Tiến trình đang chạy thật** | ✅ **3** | ❌ |

Dựng dịch vụ nghĩa là **chọn một trong ba**. Chọn nhầm thì mất `--reserve-vram 3` —
đúng thứ D-024 kê ra **sau lần máy B khởi động lại đột ngột 22/08**, và nó biến mất
**trong im lặng**: ComfyUI vẫn chạy, vẫn render, chỉ là biên VRAM mỏng lại.

### 3.3. ⚠️ `venv\Scripts\python.exe` là **stub**, phải giết cả cây tiến trình

`pyvenv.cfg` cho thấy đây là venv chuẩn (`python -m venv`), và trên Windows
`Scripts\python.exe` (274 KB) là **launcher** — nó sinh ra
`C:\Users\lengo\...\Python312\python.exe` mới là ComfyUI thật:

```
PID 8564  (stub, 3,8 MB RAM)
  └─ PID 13912  (ComfyUI that, 2.265 MB RAM, giu model + VRAM)
```

Dịch vụ dừng mà chỉ giết tiến trình cha ⇒ **ComfyUI thật còn sống và vẫn ôm VRAM**,
trong khi dịch vụ báo "Stopped". Phải đặt `AppKillProcessTree 1` cho nssm.

---

## 4. Đề xuất: **đừng dựng định nghĩa thứ tư**

Cách sai: viết một `LTTComfyUI` mới với bộ cờ riêng ⇒ thành nguồn thứ tư, và lần
sau ai đó sửa `start_comfy.ps1` sẽ tưởng mình đang sửa cái đang chạy.

Cách đúng, theo thứ tự ưu tiên:

| | Cách | Được | Mất |
|---|---|---|---|
| **C1** ⭐ | Thêm `--reserve-vram 3` vào `E:\AI\tools\start_comfy.ps1`, rồi dựng dịch vụ **gọi chính script đó** | **Một nguồn chân lý cho cờ.** Dự án video vẫn sửa được mà không phải đụng nssm | Phải sửa tệp của dự án khác |
| **C2** | Task Scheduler "At startup" chạy `start_comfy.ps1` | Không đụng nssm; dự án video quen với script này | Không có tự khởi động lại khi ComfyUI chết; khó theo dõi |
| **C3** | Dịch vụ nssm với bộ cờ riêng | Có auto-restart, có log xoay vòng | ⛔ **Nguồn thứ tư.** Đúng thứ H37 đã từ chối |

**Với C1 hoặc C3, ba thứ bắt buộc:**

1. `--listen 127.0.0.1` — **không bao giờ đổi**. ComfyUI không có xác thực; ai gọi
   được cổng 8188 là chạy được mã tuỳ ý trên máy B.
2. `--reserve-vram 3` — D-024. Mất nó là mất trong im lặng.
3. `AppKillProcessTree 1` — vì cái stub ở §3.3.

**Không** đặt `LTTRenderGateway` hay `LTTLlmGateway` phụ thuộc `LTTComfyUI`: hiện
cả hai **không có phụ thuộc nào** và vẫn lên đúng. Thêm phụ thuộc vào một dịch vụ
mới là mời một cách hỏng mới sau reboot. Cổng VLM **không cần** ComfyUI sống —
`don_dep.py` đọc VRAM bằng `nvidia-smi`, ComfyUI chết thì card sạch, cổng vẫn chạy.

---

## 5. Việc này thuộc về ai

ComfyUI là thành phần của **dự án ảnh H37 + dự án video**, không phải của H38 (VLM).
Hạng mục VLM **không cần** ComfyUI tự khởi động — nó chỉ cần biết VRAM có sạch không,
và `nvidia-smi` trả lời được điều đó dù ComfyUI sống hay chết.

⇒ **Đây là việc nên để chủ dự án quyết**, và nếu làm thì nên làm cùng lúc với việc
thống nhất bộ cờ ở §3.2 — vì đó mới là thứ đang thật sự lệch.

---

## 6. Nguồn

- Đo trên máy B 22/08: `nvidia-smi`, `Win32_Process`, `Get-ScheduledTask`, registry `Run`
- Quyết định của H37: `render_gateway/deploy/cai_dat_dich_vu.ps1` §1 (cờ `-BoQuaComfy`)
- Trình khởi động của dự án video: `E:\AI\tools\start_comfy.ps1`
- D-024 (`--reserve-vram 3`): `docs/ANH_NOI_BO/DECISIONS.md`
- ComfyUI-Watchdog (quản dịch vụ bằng nssm): https://github.com/MushroomFleet/ComfyUI-Watchdog
- Lỗi CUDA khi ComfyUI chạy nền: https://github.com/Comfy-Org/ComfyUI/issues/6843
