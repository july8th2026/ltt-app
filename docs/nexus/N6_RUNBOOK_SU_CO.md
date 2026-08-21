# Runbook sự cố — LTT Nexus

Ba tình huống hay gặp nhất khi Nexus đã có khách. Mỗi mục: **dấu hiệu → kiểm →
xử lý → xác minh**. Viết cho người trực lúc 2 giờ sáng, không phải cho người đã
thuộc hệ thống.

> Nguyên tắc chung: **xác minh bằng URL công khai**, không tin log của script.
> Loopback bỏ qua Cloudflare nên có thể xanh trong khi khách vẫn hỏng.

---

## 0. Kiểm nhanh 30 giây (làm trước mọi thứ)

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://app.lttstudios.com/health/ready
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://app.lttstudios.com/nexus-agent/status
```

| Kết quả | Nghĩa là |
|---|---|
| `200` + `401` | Nền tảng **khoẻ** (401 là đúng: đường đó đòi chữ ký) |
| `502` / `503` | **Dịch vụ chết** → mục 1 |
| `200` + `404` | Nền tảng sống nhưng **Nexus đang TẮT** (`LTT_NEXUS` chưa bật) |

Trang số liệu: `https://app.lttstudios.com/status` (cần đăng nhập quản trị) —
có khối **LTT Nexus**: số máy, đang bật, phiên, chưa trả phí, bộ đếm 24h.

---

## 1. Site trả 502 — dịch vụ không chạy

**Dấu hiệu:** `/health/ready` trả 502; khách báo không đăng nhập được.

**Kiểm** (PowerShell trên máy chủ):
```powershell
Get-Service LTTStudioWeb, LTTStudioWorker, LTTStudioCodex
```

**Xử lý** — trong cửa sổ PowerShell **Administrator**:
```powershell
Start-Service LTTStudioWeb, LTTStudioWorker, LTTStudioCodex
```

**Nguyên nhân đã gặp thật (2026-08-21):** một script deploy đặt
`$ErrorActionPreference='Stop'`; alembic in INFO ra **stderr** nên PowerShell coi
là lỗi và thoát **ngay sau khi đã dừng dịch vụ** → dịch vụ không bao giờ bật lại.
`deploy-self.ps1` nay đã có khối `finally` luôn bật lại dịch vụ; đừng gỡ nó ra.

**Xác minh:** `/health/ready` → 200, rồi `/tai-xuong` → 200.

**Nếu vẫn 502:** xem `C:\LTTPlatform\logs\` (log dịch vụ) và
`C:\LTTPlatform\logs\selfdeploy.log`. Rollback bản trước:
`C:\LTTPlatform\app\deploy\windows\rollback.ps1`.

---

## 2. Relay chết — khách đăng nhập được nhưng không kết nối được máy

**Dấu hiệu:** đăng nhập OK, `/status` OK, nhưng bấm kết nối thì quay mãi. Đây là
sự cố **hay bị chẩn đoán nhầm** thành lỗi nền tảng.

**Kiểm relay còn nghe không** (relay hiện tại: `45.76.185.75`):
```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 https://app.lttstudios.com/nexus-agent/relay-check?id=x
```
→ `401` là đúng (đòi bí mật). Nếu `404`: `LTT_NEXUS_RELAY_SECRET` chưa được đặt.

Cổng relay từ ngoài:
```bash
timeout 6 bash -c 'echo > /dev/tcp/45.76.185.75/21116' && echo "21116 MO" || echo "21116 DONG"
```

**Xử lý** — SSH vào relay (`ssh administrator@45.76.185.75`, xác thực bằng mật
khẩu), rồi trong PowerShell **Administrator** trên máy đó:
```powershell
Get-Service hbbs, hbbr
Start-Service hbbs, hbbr
```

Binary LTT nằm ở `C:\Program Files\RustDeskServer\bin\hbbs.exe`; nssm ở
`...\service\nssm.exe`. Bản gốc được backup cạnh đó (`hbbs.exe.bak-<thời-gian>`)
— nếu nghi bản LTT gây lỗi thì đổi lại bản backup rồi `Start-Service hbbs`.

⚠️ **Không bao giờ xoá `id_ed25519` trong thư mục đó.** Mọi client đã nén sẵn
khoá công khai `A1MZFm2igQwZ29CMGYlhmjP7JI3yXzpc0qV17IqFndI=`; đổi khoá = **toàn
bộ khách mất kết nối** cho tới khi cài lại app.

**Rủi ro đã biết:** relay chạy trên **Windows Server 2016 bản Eval hết hạn
15/12/2026** — hết hạn thì máy **tự tắt mỗi giờ**, kéo sập cả relay lẫn mạng VM.
Phải dời sang Linux trước mốc đó (binary static musl đã build sẵn:
`D:\LThbbs\dist\hbbs`).

---

## 3. Khách nói "tôi đã trả tiền mà vẫn bị chặn"

**Trước hết phân biệt ba trạng thái khác nhau** — chúng trông giống nhau với
khách nhưng cách xử lý hoàn toàn khác:

| Trạng thái | Cách nhận ra |
|---|---|
| Thật sự chưa trả | `/status` (trang quản trị) → **chưa trả phí** > 0; máy đó `paid_until` rỗng hoặc đã qua |
| Đã trả nhưng chưa quét | Vòng thu phí chạy trong worker; nếu worker chết thì không ai gia hạn |
| Relay chặn nhầm | Bộ đếm `nexus:relay_chan` tăng trong khi máy có `paid_until` ở tương lai |

**Kiểm số dư + hạn của khách** (chạy trên máy chủ):
```bash
python - <<'PY'
import re, sqlalchemy as sa
from pathlib import Path
url = next(m.group(1).strip().strip('"') for m in
    (re.match(r"^\s*LTT_DATABASE_URL\s*=\s*(.+?)\s*$", l)
     for l in Path(r"C:\LTTPlatform\secrets\app.env").read_text(encoding="utf-8-sig").splitlines())
    if m)
e = sa.create_engine(url)
with e.connect() as c:
    for r in c.execute(sa.text(
        "SELECT id, display_name, rustdesk_id, paid_until, revoked_at "
        "FROM nexus_devices ORDER BY created_at DESC LIMIT 20")):
        print(r)
PY
```

**Xử lý:**
- **Worker chết** → `Start-Service LTTStudioWorker`. Vòng thu phí nằm trong vòng
  bảo trì của worker (sau lease), không phải trong tiến trình web.
- **Hết credit thật** → khách nạp ở `/nap`; lần quét sau sẽ gia hạn. Cần mở ngay
  thì cộng credit qua trang quản trị rồi đợi vòng quét, **đừng sửa thẳng
  `paid_until` trong CSDL** — làm vậy là ghi tiền không đi qua sổ.
- **Nghi chặn nhầm** → tắt cưỡng chế relay tạm thời bằng cách **bỏ**
  `LTT_NEXUS_RELAY_CHECK_URL` khỏi env của hbbs rồi restart: relay quay về cho
  qua tất cả (mặc định TẮT cưỡng chế). Ghi lại lý do và mốc thời gian.

**Nhớ:** cưỡng chế relay là **fail-open** — control plane không trả lời thì relay
vẫn cho qua. Nên "bị chặn" luôn có nghĩa control plane đã nói **rõ**
`allowed:false`, tức máy đó thật sự chưa trả theo dữ liệu hiện có.

---

## 4. Việc phải làm định kỳ

| Việc | Nhịp | Vì sao |
|---|---|---|
| Xem khối **LTT Nexus** ở `/status` | tuần | Bắt sớm số máy chưa trả phí tăng bất thường |
| Kiểm `21116` từ ngoài | tuần | Relay chết lặng lẽ, khách chịu trận trước khi mình biết |
| Sao lưu `C:\LTTPlatform\secrets\app.env` | sau mỗi lần đổi | Mất `LTT_NEXUS_RELAY_SECRET` = phải cấu hình lại cả relay |
| **Dời relay khỏi Windows Eval** | **trước 15/12/2026** | Hết hạn là tự tắt mỗi giờ |
