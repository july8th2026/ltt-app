# Spike P6B — ranh giới egress ở mức hệ điều hành cho mã không tin cậy

**Câu hỏi:** cơ chế nào ở mức Windows thật sự chặn egress của một tiến trình Node.js
chạy mã không tin cậy, **kể cả khi nó `spawn` tiến trình con**?

Nền: `docs/superpowers/reports/p6-egress/spike-chan-egress.md` đã đo và kết luận rằng
vá `net.Socket.prototype.connect` chặn 100 % tổ hợp **trong tiến trình**, nhưng
`child_process.spawnSync(process.execPath, ['-e', …])` đi vòng qua tất cả (`-r <preload>`
là cờ của **tiến trình đó**, không đi theo `spawn`). Spike này đi tìm biên thật.

Máy: Windows 10 Pro 19045, Node v24.17.0, phiên có quyền quản trị.
Bàn thử: `spike/egress-os/`. Đích ngoài: `example.com` (không dữ liệu/tài khoản thật).

---

## 1. Bảng kết quả

`REACHED` = lọt ra Internet. `BLOCKED` = bị chặn. `—` = **chưa đo được** (xem §2).
Tất cả các ô đều là **đo thật**, không suy luận.

| Cơ chế | piece thường (trong tiến trình) | **spawn tiến trình con** | IP trần | IPv6 | UDP | nhị phân native (không qua Node) |
|---|---|---|---|---|---|---|
| **Đối chứng — không chặn gì** | REACHED 200 | REACHED 200 | REACHED 200 | — | REACHED | REACHED 200 |
| **H1a. Tường lửa theo SID người dùng** (`-LocalUser`) | BLOCKED `EACCES` | **BLOCKED** `EACCES` | BLOCKED `EACCES` | — | *chưa đo* (luật đặt `-Protocol TCP`) | **BLOCKED** (curl.exe con, exit 7) |
| **H1b. Tường lửa theo đường dẫn chương trình** (`-Program`) | BLOCKED `EACCES` | BLOCKED `EACCES` (con **cùng** exe) | BLOCKED `EACCES` | — | *chưa đo* | 🔴 **REACHED 200** — curl.exe **thủng** |
| **H2. AppContainer, không capability mạng** | BLOCKED (TIMEOUT) | **BLOCKED — `spawn` trả `ENOENT`, con KHÔNG chạy được** | BLOCKED `EACCES` | — | BLOCKED | **BLOCKED** (`curl.exe` 000, `nslookup` timeout) |
| *H2 đối chứng: AppContainer **có** `internetClient`* | *REACHED 200* | *`ENOENT`* | *REACHED 200* | — | *REACHED* | *REACHED 200* |
| **H3. Namespace mạng WSL2** (`unshare --net`) | BLOCKED | **BLOCKED** (cả con **và cháu**) | BLOCKED | — | BLOCKED | 🔴 **REACHED 200** qua **WSL interop** — xem §3 |
| *H3 đối chứng: cùng distro, không namespace* | *REACHED 200* | *REACHED 200* | *REACHED 200* | — | *REACHED* | *REACHED 200* |

### Dòng đối chứng KHÔNG-chặn (bắt buộc)

Không có dòng này thì "0 request lọt" có thể chỉ là mạng hỏng. Đo được:

- **Ngoài mọi cơ chế:** `probe.js` trực tiếp, `spawn` node con, `spawn` curl.exe con —
  **REACHED 200** cho `tcp_host`, `tcp_rawip`, và **REACHED** cho UDP (DNS 1.1.1.1, 61 byte).
- **Bên trong AppContainer nhưng CÓ `internetClient`** — REACHED 200. Đây là đối chứng
  mạnh nhất: cùng container, cùng ACL, cùng tiến trình, **chỉ khác một capability**.
- **Bên trong WSL nhưng không `unshare`** — REACHED 200 ở cả bốn phép.
- **Luật tường lửa gắn cho SID KHÁC** (`NT AUTHORITY\LOCAL SERVICE`, `S-1-5-19`):
  probe của ta **REACHED 200** ⇒ điều kiện `-LocalUser` **thật sự được đánh giá**, luật
  không âm thầm áp cho cả máy. (Phép đối chứng âm này cần thiết: nếu thiếu nó, ba ô
  `BLOCKED` của H1a không phân biệt được "lọc theo SID chạy đúng" với "luật chặn tất cả".)

---

## 2. Chỗ còn hở — nói thẳng cái chưa đo

- 🔴 **IPv6: chưa đo được, KHÔNG phải "đã chặn".** Máy A **không có** địa chỉ IPv6 toàn cục
  và **không có** route `::/0`; `curl -6 https://example.com/` trả `000` ngay ở **đối chứng**.
  Kênh này không nói được gì về cả ba hướng. Muốn phủ phải đo trên máy có IPv6 thật.
- **UDP ở hướng H1 chưa đo**: luật thử đặt `-Protocol TCP` nên UDP nằm ngoài phạm vi luật,
  không phải "UDP bị chặn". Luật triển khai thật phải là `-Protocol Any`. ⚠️ Đáng lưu ý vì
  **`cloudflared` đi bằng QUIC/UDP** — một luật `Any` đặt sai phạm vi sẽ cắt đúng đường số 4.
- **Native addon biên dịch riêng: chưa dựng.** Vật thay thế là `curl.exe` — mã native thật,
  mở socket bằng syscall, không qua `net`/`dns` của Node. Đã đo cả hai vai: **chạy thẳng
  trong container** (in-process native) và **bị spawn ra**. Với H2 cả hai đều BLOCKED, vì
  chỗ chặn nằm ở tầng WFP chứ không phải trong tiến trình. Một addon N-API trong cùng tiến
  trình đi cùng đường đó, nhưng **chưa có phép đo trực tiếp**.
- **H3 chưa chạy đúng `piece-child-process.js`**: distro Ubuntu **không cài Node**, và distro
  đó **đang chạy dịch vụ `searxng` thật** ⇒ không cài thêm gói. Đo bằng `curl` + `bash`
  (con và cháu). Tính chất namespace không phụ thuộc Node, nhưng đây vẫn là một tập con.
- **H2 chưa chứng minh "con kế thừa token"** — vì **không tạo được con nào cả**. Đó là kết quả
  *mạnh hơn* cho an ninh, nhưng nếu một bản Node/cấu hình tương lai làm `spawn` chạy được thì
  câu hỏi kế thừa **mở lại**. Tài liệu Microsoft **không** phát biểu tường minh rằng token
  AppContainer không thể thoát (xem §5); chỗ này dựa vào đo, không dựa vào hợp đồng.

---

## 3. Hai lỗ thủng đã đo được

**H1b — luật theo đường dẫn chương trình không phải ranh giới.** Chặn `node.exe` thì piece
chỉ cần `spawn('curl.exe')` là ra: đo được **REACHED 200**. Luật gắn vào *một tệp* chỉ chặn
đúng tệp đó.

**H3 — WSL interop thoát khỏi namespace.** Từ **bên trong** `unshare --net` (nơi mọi lệnh
Linux đều `Network is unreachable`), gọi `/mnt/c/Windows/System32/curl.exe` trả **200**.
Lý do cơ học: interop chuyển yêu cầu cho tiến trình init phía Windows, nên nhị phân chạy
**ngoài** namespace. Thử gỡ bằng `unshare --net --mount` rồi `umount /proc/sys/fs/binfmt_misc`
**vẫn REACHED 200** — cách giảm nhẹ đó không đủ. Muốn dùng H3 phải tắt interop ở mức distro
(`wsl.conf` `interop.enabled=false`) và **đo lại**.

⚠️ **Hyper-V firewall (lọc outbound theo từng distro WSL từ phía host) KHÔNG có trên máy này** —
tài liệu Microsoft ghi tính năng bắt đầu từ **Windows 11 22H2**; máy A là Windows 10 19045, và
`New-NetFirewallHyperVRule` / `Set-NetFirewallHyperVVMSetting` **không tồn tại** (đã kiểm).

---

## 4. Khuyến nghị — một hướng chính, một lớp ngoài

### Chính: **H2 — AppContainer không cấp capability mạng**

Lý do chọn, tất cả đều là số đã đo:

1. Chặn **mọi** kênh đo được: `require('https')`, IP trần, UDP, và **mã native chạy thẳng**.
2. Chặn luôn **đường thoát đã làm sập spike P6**: bên trong container `spawn` trả `ENOENT` —
   `cmd.exe`, `curl.exe`, `nslookup.exe`, `node.exe` đều không khởi động được.
3. **Không cần tài khoản Windows mới, không cần một luật tường lửa nào, không cần đổi cài đặt
   hệ thống.** ⇒ **bốn đường ra của máy A không bị đụng tới** — cơ chế này ràng buộc *tiến trình
   được phóng vào container*, chứ không lọc lưu lượng của máy.
4. Có đối chứng chặt: cùng container, chỉ thêm `internetClient` ⇒ REACHED 200.

**Loại trừ nhầm lẫn đã làm:** `ENOENT` **không** phải do thiếu biến môi trường hay thiếu tệp —
trong container `SystemRoot="C:\Windows"`, đủ 90 biến, và `fs.statSync('C:\Windows\System32\cmd.exe')`
**đọc được, 289 792 byte** — vậy mà `spawn` chính tệp đó vẫn `ENOENT`, trong khi ngoài container
nó chạy và in `XIN_CHAO`.

**Giá phải trả — phải chấp nhận trước khi xây:**
- Piece **không** chạy được tiến trình con. Piece nào hợp lệ mà cần `spawn` sẽ hỏng.
- `node` cần `--preserve-symlinks-main`: không có nó, Node `realpath` lên tận gốc và chết
  `EPERM: lstat 'C:\'`.
- `spawnSync` **dùng pipe** bị **treo** trong AppContainer (treo cứng, vượt cả `timeout` của
  chính nó). Runner phải đặt hạn giờ **bên ngoài** và `TerminateProcess`, đừng tin timeout của Node.
- Thư mục runner phải cấp ACL cho `ALL APPLICATION PACKAGES` (hoặc đúng SID container).

### Lớp ngoài: **H1a — tài khoản Windows riêng + luật outbound theo SID**

Đo được: chặn cả piece thường, **cả node con**, **cả curl.exe con** — tức phủ đúng chỗ H1b thủng,
vì tiến trình con kế thừa token người dùng. Đối chứng âm chứng minh phạm vi đúng theo SID.

🔴 **Tài liệu Microsoft ghi `-LocalUser` chỉ khớp gói tin đã *authenticated*** — **đo trên máy này
cho kết quả NGƯỢC LẠI**: lưu lượng TCP thường, không IPsec, vẫn bị lọc theo SID. Nên tin phép đo
cho máy này, và **đo lại** nếu đổi bản Windows.

**Cần chủ dự án** (xem §6) — vì phải tạo tài khoản.

**Vì sao cần cả hai:** H2 mạnh nhưng chỗ dựa là **hành vi đo được**, không phải hợp đồng tài liệu
(§5). H1a nằm ở tầng khác (WFP theo token) nên một lỗ của H2 không kéo theo lỗ của H1a.

---

## 5. Nguồn đã tra

- **`New-NetFirewallRule`** (Microsoft Learn, NetSecurity) — `-LocalUser`/`-Owner`: *"only network
  packets that are authenticated as coming from or going to a principal identified in the list of
  accounts (SID) match this rule"*. `-Program` lọc theo đường dẫn tệp; `-Package` theo SID ứng dụng
  Store; `-Service` theo tên dịch vụ. → **Phép đo §1 mâu thuẫn với mệnh đề "authenticated" cho
  outbound trên build này.**
- **WFP — Permitting and Blocking Applications and Users** (Microsoft Learn) — `FWPM_CONDITION_ALE_USER_ID`
  so khớp security descriptor ở tầng ALE.
- **AppContainer isolation** (Microsoft Learn) — mục *Network isolation*: truy cập mạng bị chặn theo
  capability. Capability SID cố định: `internetClient` = `S-1-15-3-1`.
- **Project Zero, *Understanding Network Access in Windows AppContainers*** (2021-08) — xác nhận bộ lọc
  WFP mặc định chặn AppContainer thiếu `internetClient`; và loopback bị chặn mặc định
  (miễn trừ bằng `CheckNetIsolation.exe LoopbackExempt`).
  ⚠️ Bài này **cũng nói** tiến trình con do AppContainer sinh ra *có thể* chạm tới filter permit sẵn có.
  **Không tìm được trang Microsoft Learn nào phát biểu tường minh rằng token AppContainer không thể
  thoát** ⇒ chỗ này chỉ có đo, không có hợp đồng. Đã ghi vào §2.
- **Hyper-V Firewall** (Microsoft Learn) — *"Starting in Windows 11, version 22H2"* ⇒ không áp dụng
  cho máy A. `microsoft/WSL#11377`: người dùng Windows 10 gặp đúng lỗi thiếu cmdlet.
- **`activepieces/activepieces#11547`** — chính đội activepieces xác nhận sandbox trong-tiến-trình và
  namespace kernel **không đủ** cho mã không tin cậy có quyền mạng; đề xuất microVM QEMU + lọc domain
  ngoài tiến trình. Dẫn **CVE-2025-68668** (n8n, Pyodide sandbox escape, CVSS 9.9).
- **`n8n-io/n8n#26545`** (đã đóng) — đề xuất tương tự cho n8n; dẫn CVE-2025-68668 và **CVE-2025-68613**.
- Không tìm được issue nào bàn riêng về Windows ở cả hai kho.

---

## 6. Việc cần chủ dự án — ⛔ agent không tự làm

Cả hai việc dưới đây **agent bị cấm làm** (tạo tài khoản Windows, đổi cài đặt hệ thống, nhập mật khẩu).

1. **Tạo tài khoản Windows riêng cho runner** (ví dụ `ltt-piece-runner`), quyền tối thiểu, **không**
   thuộc `Administrators`, rồi đặt luật outbound mặc-định-chặn gắn `-LocalUser` theo SID tài khoản đó,
   `-Protocol Any` (⚠️ phải gồm UDP), và mở đúng danh sách đích mà connector cần.
   ⛔ Luật phải gắn **SID của tài khoản runner**, tuyệt đối không dùng luật rộng theo cổng/đích —
   `cloudflared` đi QUIC/UDP và dịch vụ nền tảng chạy dưới danh tính khác.
2. **Nếu chọn H3**: tắt WSL interop ở mức distro (`wsl.conf`, `interop.enabled=false`) rồi **đo lại** —
   lỗ ở §3 chưa được bịt. Distro hiện đang chạy `searxng` thật nên việc này phải do chủ dự án quyết.

Chưa làm hai việc này thì **H2 (AppContainer) vẫn dùng được ngay** — nó không cần gì trong số đó.

---

## 7. Lệnh gỡ sạch

Spike này **không để lại luật tường lửa nào**: script tự gỡ trong khối `finally`, và đã kiểm —
`p6b-spike-*` còn **0**, tổng số luật trở lại đúng **561** như trước khi đo.

```powershell
# 1) Luật tường lửa (đã tự gỡ; lệnh này để đối chứng/gỡ tay nếu một lượt bị ngắt giữa chừng)
Get-NetFirewallRule -DisplayName 'p6b-spike-*' | Remove-NetFirewallRule
(Get-NetFirewallRule -DisplayName 'p6b-spike-*' | Measure-Object).Count   # phải là 0

# 2) Hồ sơ AppContainer do spike tạo
python spike\egress-os\launch_appcontainer.py --xoa ltt-p6b-spike
python spike\egress-os\launch_appcontainer.py --xoa ltt-p6b-net

# 3) Thư mục dàn dựng (bản chép node.exe + ACL đã cấp) nằm trong scratchpad của phiên,
#    xoá cả thư mục là xoá luôn ACL - KHÔNG có ACL nào đặt ngoài thư mục đó.
Remove-Item -Recurse -Force "<scratchpad>\p6b-stage"

# 4) Tiến trình mồ côi (chỉ tiến trình do spike khởi động)
Get-Process node -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "*\p6b-stage\*" } | Stop-Process -Force
```

⛔ **Không** đổi luật tường lửa toàn máy, **không** tắt dịch vụ, **không** đổi cấu hình mạng chung,
**không** đụng `C:\`, `C:\Program Files`, `C:\Windows`. Mọi ACL chỉ nằm trong thư mục dàn dựng.
WSL: chỉ dùng `unshare` tạm thời, **không** sửa distro, **không** cài gói — `searxng` không bị đụng.

## 8. Phép kiểm sản xuất — trước và sau

`python tools/vps_doi_soat_cong.py` (cần `PYTHONPATH=D:\LTTSTUDIOSAPP` và env từ
`C:\LTTPlatform\secrets\app.env`):

| Thời điểm | Kết quả |
|---|---|
| Trước mọi lượt đo | `RESULT: PASS` (69,7 s) |
| Sau lượt đặt/gỡ luật tường lửa | `RESULT: PASS` (68,3 s) |

Bốn đường ra (SSH 22 → `51.79.166.36`, Proxmox 8006, `*.api.ovh.com`, HTTPS của `cloudflared`)
không có luật nào của spike chạm tới: luật duy nhất từng tồn tại hẹp ở **một /32 của `example.com`,
chỉ TCP, chỉ cổng 80/443, chỉ chiều ra**, và đã gỡ.

---

## 9. Cách chạy lại

```powershell
$env:P6B_STAGE = "<thu-muc-dan-dung>"   # chép node.exe + spike\egress-os\*.js vao day
icacls $env:P6B_STAGE /grant "*S-1-15-2-1:(OI)(CI)(M)" /T

# Đối chứng + AppContainer
python spike\egress-os\run_matrix.py --launcher L0_doi_chung
python spike\egress-os\run_matrix.py --launcher L2_appcontainer_net     # đối chứng
python spike\egress-os\run_matrix.py --launcher L2_appcontainer_none

# Phép thử quyết định của H2 (spawn trong container)
python spike\egress-os\launch_appcontainer.py --ten ltt-p6b-spike --caps none --cho-ms 60000 `
  --ra out.txt -- "$env:P6B_STAGE\node.exe" --preserve-symlinks-main `
  "$env:P6B_STAGE\piece-spawn-he-thong-inherit.js"

# H1 (đặt + gỡ luật tường lửa, có đối chứng âm)
powershell -NoProfile -ExecutionPolicy Bypass -File spike\egress-os\fw_localuser.ps1 `
  -Stage $env:P6B_STAGE -Ip4 <ip-cua-example.com>

# H3 (WSL, không sửa distro)
wsl -u root -- bash -c "tr -d '\r' < /mnt/d/LTTSTUDIOSAPP/spike/egress-os/wsl_netns.sh > /tmp/w.sh; bash /tmp/w.sh"
```
