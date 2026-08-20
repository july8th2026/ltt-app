# N3.2 — ghép engine RustDesk (nguyên bản, Rổ 1), thiết kế + việc phải xác minh trên VM

> Lập 2026-08-20 sau Q97 (dùng RustDesk **nguyên bản**).
>
> §2 là **giả thuyết thiết kế**; §3 là **danh sách phải kiểm**; **§3b là sự thật
> đã đo được trên máy thật** (V1/V2/V3/V5 xong 2026-08-20). Ba phần cố ý để riêng
> — R9 của `EXECUTION_PLAN.md` đòi thứ cấu-hình-trên-máy phải có một phép đo thật,
> và trộn giả thuyết với kết quả là cách chắc chắn để sau này không ai biết dòng
> nào đã được chứng minh.

---

## 1. Bài toán, sau Q97

RustDesk **nguyên bản** dùng mô hình xác thực riêng của nó: **ID + mật khẩu**.
Nexus có mô hình riêng: **vé một lần do server cấp** (`cap_ve`/`doi_ve`). Hai mô
hình này phải nối lại mà **không sửa** RustDesk (Rổ 1). Nên câu hỏi trung tâm:

> Vé Nexus (tầng **uỷ quyền**) biến thành credential RustDesk (tầng **truyền**)
> như thế nào, mà không nhúng gì vào binary RustDesk?

## 2. Giả thuyết thiết kế — hai vai, hai credential

```
  Máy ĐÍCH (bị điều khiển)                     Bên ĐIỀU KHIỂN
  ─────────────────────────                    ─────────────────
  Agent LTT:                                   khách đổi vé (web/viewer)
   • cấu hình RustDesk nguyên bản trỏ           → nhận: RustDesk ID của đích
     về server LTT (Q96) — KHÔNG build vào,       + mật khẩu MỘT LẦN (Agent
     nạp config từ ngoài                          vừa đặt cho phiên này)
   • đặt mật khẩu phiên NGẮN HẠN mỗi lần        → chạy RustDesk nguyên bản
     có vé, xoay sau mỗi phiên                    connect tới ID đó với mật
   • bật chỉ báo phiên (ràng buộc 7)              khẩu đó
```

**Vé Nexus là tầng uỷ quyền; mật khẩu RustDesk là tầng truyền.** Agent **xoay
mật khẩu RustDesk theo từng vé**, nên một mật khẩu lộ không cho quyền đứng lâu —
đúng tinh thần vé một lần của Q93 ràng buộc 2, dựng lại bằng cơ chế của RustDesk
thay vì sửa nó.

**Điểm mấu chốt cho Rổ 1:** LTT **không** phát minh giao thức mới trong RustDesk;
LTT chỉ **lái** RustDesk nguyên bản bằng config + mật khẩu từ ngoài. Nếu có bước
nào buộc phải sửa binary thì **dừng lại** — đó là tín hiệu đã trượt sang Rổ 2, và
phải quay lại Q97 trước khi làm.

## 3. Phải xác minh trên VM — chưa cái nào là sự thật

Mỗi dòng dưới đây là một câu hỏi phải trả lời bằng **lệnh chạy trên máy thật**,
không bằng trí nhớ về RustDesk:

| # | Câu hỏi | Vì sao quyết định thiết kế |
|---|---|---|
| V1 | Cấu hình server (rendezvous+relay+key) vào client nguyên bản bằng cách nào **không sửa binary**? (file `.toml`? cờ `--config <chuỗi base64>`? biến môi trường? registry?) | Nếu chỉ có đường "build client riêng" thì đó là Rổ 2 — phải báo lại |
| V2 | Đặt mật khẩu truy cập **không giám sát** qua CLI được không? (`--password`?) Đặt xong có hiệu lực ngay không cần bấm UI? | Agent phải đặt được mật khẩu tự động, không người bấm |
| V3 | **Xoay** mật khẩu giữa hai phiên bằng lệnh được không, sạch không? | Mật khẩu một-lần-mỗi-phiên là cả điểm bảo mật |
| V4 | Bên điều khiển `--connect <id>` cấp mật khẩu **không tương tác** được không? | Nếu nó luôn hỏi tay thì luồng vé tự động gãy |
| V5 | RustDesk ID có **ổn định** theo máy không, hay đổi? Map ID ↔ `nexus_devices` thế nào? | Vé trỏ tới đúng máy phải dựa trên một định danh ổn định |
| V6 | Ép **relay** (`ALWAYS_USE_RELAY`) rồi bắt gói tại hbbr — payload có mã hoá đầu-cuối không? (**T10**) | Nếu relay đọc được màn hình thì phải nói với khách (threat model) |
| V7 | Chỉ báo phiên nguyên bản của RustDesk có đủ mạnh cho ràng buộc 7 không, hay Agent phải chồng thêm một chỉ báo? | Ràng buộc 7 là bắt buộc, không phải tuỳ |

## 3b. KẾT QUẢ ĐO THẬT — 2026-08-20, trên VM106

Máy đo: **VM106**, Windows 10 Enterprise LTSC build 19044, 4 GB RAM, IP nội bộ
`10.50.0.17`, ra Internet bằng `45.76.185.75` (qua gateway — đúng như đã ghi ở
`N3_2_TEST_SETUP.md` §3). Điều khiển hoàn toàn bằng **SSH** qua gateway; không
dùng RDP một lần nào.

Bản dùng: `rustdesk-1.4.9-x86_64.exe`, **nguyên bản**, tải từ release chính thức.
SHA-256 `EAEDEB0088E687BF46F7C46A9C6EA5493CE51F3134DFD6ACBEDB47B5B9136274`,
24.472.432 byte. Cài bằng `--silent-install` → dịch vụ `RustDesk` Running/Automatic.

| # | Câu hỏi | Kết quả |
|---|---|---|
| **V1** | Nạp cấu hình server **không sửa binary**? | ✅ **ĐƯỢC** — xem dưới |
| **V2** | Đặt mật khẩu không giám sát bằng lệnh? | ✅ `rustdesk.exe --password <pw>` → `Done!` |
| **V3** | **Xoay** mật khẩu giữa hai phiên? | ✅ gọi lại `--password` — 3 lần ra 3 ciphertext khác nhau |
| **V5** | ID có ổn định không? | ✅ `--get-id` → `288780716`, **không đổi** sau khi restart dịch vụ |
| V4 | Bên điều khiển kết nối không tương tác? | ⬜ **cần máy thứ hai** |
| V6/T10 | Relay có đọc được nội dung màn hình? | ⬜ **cần máy thứ hai** |
| V7 | Chỉ báo phiên đủ mạnh cho ràng buộc 7? | ⬜ **cần máy thứ hai** (phải có phiên thật mới thấy) |

### V1 — cách nạp cấu hình, và hai cái bẫy

Sửa `RustDesk2.toml`, mục `[options]`:

```toml
[options]
custom-rendezvous-server = '45.76.185.75'
relay-server = '45.76.185.75'
key = 'A1MZFm2igQwZ29CMGYlhmjP7JI3yXzpc0qV17IqFndI='
```

**Bẫy 1 — có HAI bộ config, và bộ quan trọng không nằm ở chỗ ai cũng nghĩ.**
Bộ của người dùng ở `%APPDATA%\RustDesk\config\`, nhưng bộ **dịch vụ** —
thứ phục vụ truy cập không giám sát — nằm ở
`C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config\`.
Chỉ sửa bộ người dùng thì dịch vụ vẫn trỏ về `rs-ny.rustdesk.com`.

**Bẫy 2 — phải DỪNG dịch vụ trước khi sửa**, vì nó ghi đè config lúc thoát.

**Xác minh hai chiều, không tin lời client:** phía máy đích thấy kết nối
`Established` tới `45.76.185.75:21116`; phía **máy chủ** hbbs cũng thấy kết nối
vào cổng 21116. Cả hai đầu cùng xác nhận thì mới tính là đo được.

### Ý nghĩa cho Q97 — điều kiện sống còn đã đứng vững

Rổ 1 đòi: RustDesk **nguyên bản** phải trỏ được về hạ tầng LTT mà **không sửa
binary**. V1 chứng minh điều đó bằng file cấu hình. Không phải build lại, không
phải dùng "custom client generator". **Không có bước nào buộc trượt sang Rổ 2**,
nên điều kiện dừng ghi ở §2 không kích hoạt.

### Ghi chú cho thiết kế Agent (đổi giả thuyết §2 thành việc làm được)

Thiết kế "vé Nexus → mật khẩu RustDesk một lần" **thực thi được** bằng đúng hai
lệnh mà V2/V3 đã chứng minh, cộng ID lấy từ V5:

```
doi_ve hop le  ->  rustdesk.exe --password <chuoi ngau nhien moi>
                   rustdesk.exe --get-id        (map vao nexus_devices)
het phien      ->  rustdesk.exe --password <chuoi ngau nhien khac>
```

Lưu ý cho người viết code: ID cất trong config dạng **mã hoá** (`enc_id`), nên
**đừng parse file config** để lấy ID — dùng `--get-id`. Parse `enc_id` là viết
một thứ sẽ hỏng ở bản RustDesk kế tiếp.

### V4 — ĐÃ TRẢ LỜI, và câu trả lời đổi thiết kế

**Bên điều khiển của RustDesk là ứng dụng GUI (Flutter), KHÔNG có chế độ headless.**
Bằng chứng: `--help` và `-h` không in trợ giúp mà **mở cửa sổ GUI**; chạy trong
phiên không có desktop thì nó chết với `Could not create platform view rendering
surface`. Chỉ `--version` (và `--get-id`, `--password`) chạy được không cần màn hình.

Hệ quả cho Nexus, và nó **không xấu**: bên điều khiển trong sản phẩm là **khách
ngồi trước màn hình**, nên GUI là đúng chỗ. Cái KHÔNG làm được là để một tiến
trình tự động đóng vai người điều khiển — nghĩa là mọi kịch bản "server tự mở
phiên vào máy khách" đều bất khả thi với client nguyên bản. Xét theo Q93 ràng
buộc 5 (admin không được có đường vào máy khách không để lại dấu) thì đây là
**giới hạn có lợi**, không phải thiếu sót.

### Hai phát hiện khi dựng phép đo T10

**1. Hai máy cùng LAN nối THẲNG, `force-always-relay` không ngăn được.** Đặt
`force-always-relay = 'Y'` cả ở peer config lẫn options toàn cục, phiên vẫn đi
`10.50.0.17:50251 ↔ 10.50.0.16:50265` — trực tiếp qua LAN, không chạm relay.

Cách ép được thật: **chặn đường LAN ở tầng firewall** giữa hai máy. Sau khi chặn,
kết nối chuyển sang `45.76.185.75:21117` (hbbr = relay) đúng như mong đợi.

Ý nghĩa cho R3 (chi phí băng thông): **máy cùng mạng nội bộ sẽ không tốn băng
thông relay** — tốt cho chi phí. Nhưng nó cũng nói rằng một phép đo tỉ lệ làm
trên hai máy cùng LAN sẽ ra "100% direct" **vì lý do sai**, không liên quan gì
tới chất lượng xuyên NAT.

**2. Khởi động lại dịch vụ RustDesk cắt phiên đang chạy.** Hiển nhiên khi nói ra,
nhưng nó làm hỏng lần đo đầu: đã nhờ người dùng kết nối rồi mới đi chặn LAN và
restart, nên lúc bắt gói thì phiên đã chết (lưu lượng 0 KB/6s). Thứ tự đúng:
**chuẩn bị xong hết → mới nhờ kết nối → bắt gói, không đụng gì thêm.**

### V6 / T10 — relay CÓ đọc được nội dung màn hình không? TRẢ LỜI: KHÔNG (thụ động)

Định làm bằng bắt gói một phiên video thật, nhưng VM 4GB không GPU cứ treo khi
RustDesk encode phần mềm (lỗi `SwapChain11 Device lost`), và tiến trình chạy qua
SSH nằm ở session 0 nên không chụp được phiên. **Môi trường không hợp để bắt gói
video.** Nhưng T10 có câu trả lời **chặt hơn** — đọc từ **mã nguồn tại đúng
commit đã ghim** (Q96/`03_OSS_LICENSE`), vì "relay đọc được nội dung không" là
một tính chất **thiết kế**, không phải kết quả một phiên cụ thể.

**Bằng chứng 1 — relay là bộ chuyển byte MÙ, không có khoá.**
`rustdesk-server@73523b3` `src/relay_server.rs`, hàm `relay()`:

```rust
res = peer.recv() => { ... limiter.consume(nb); total += nb;
                       stream.send_raw(bytes.into()).await?; }   // chuyen RAW
```

Relay chỉ `recv → đếm → send_raw`. Không có nhánh nào giải mã, không giữ khoá
phiên. `sodiumoxide` duy nhất trong file là để **ký danh tính máy chủ** (khoá
`A1MZ…`), không phải giải mã.

**Bằng chứng 2 — client mã hoá đầu-cuối mỗi khung.**
`hbb_common@master` `src/tcp.rs`: `struct Encrypt(pub Key, ...)` dùng
`secretbox::seal`/`open` (NaCl XSalsa20-Poly1305), nonce theo seqnum. Mỗi khung
màn hình là ciphertext trên dây.

**Bằng chứng 3 — khoá đối xứng KHÔNG lọt về máy chủ.**
`rustdesk@6c57829` `src/client.rs:799-805`: controller sinh khoá đối xứng ngẫu
nhiên rồi **niêm phong bằng khoá CÔNG KHAI của máy đích** (`create_symmetric_key_msg(their_pk_b)`).
Chỉ khoá riêng của máy đích — *không bao giờ rời máy* (Q93 ràng buộc 1) — mở được.

**Kết luận T10:** một relay **thụ động** (LTT vận hành đúng đắn) **không đọc được
nội dung màn hình** — nó chỉ thấy ciphertext + số byte + thời điểm. Đây là chứng
minh từ mã nguồn, mạnh hơn một lần bắt gói (vốn chỉ chứng minh "phiên này, chuỗi
này không thấy").

### V8 — RANH GIỚI QUYỀN (phát hiện khi xây Agent, 2026-08-20)

Đo trên VM106 với một user **thường** (không admin), qua scheduled task:

| Lệnh | User thường | Bằng chứng |
|---|---|---|
| `--get-id` | ✅ chạy được | trả `288780716` |
| `--password` | ❌ **từ chối** | *"Installation and administrative privileges required!"* |

Ghi config service profile (`ServiceProfiles\LocalService`) và dừng dịch vụ
RustDesk cũng đòi admin. Nên **đọc ID** thì Agent thường làm được, nhưng **đặt/
xoay mật khẩu và cấu hình** là **thao tác có đặc quyền**.

**Đây xung đột với N3.3b.** N3.3b chọn Scheduled Task **không admin** để tránh
đúng màn hình UAC mà kịch bản lừa đảo T1 cần khách bấm qua. Nhưng điều khiển
**không giám sát** (unattended) — cài RustDesk như dịch vụ *và* xoay mật khẩu
phiên — **bản chất cần admin**. Không có đường vòng: RustDesk đặt mật khẩu không
giám sát vào hồ sơ dịch vụ, và chỉ tiến trình admin ghi được vào đó.

**N3.3b đã lường trước điều này** — nó viết: "Khi nào cần vào máy trước lúc đăng
nhập thì đổi sang service, và **đổi kèm quyền admin**, không phải một cờ nhỏ."
Điều khiển không giám sát đúng là trường hợp đó. Nên câu hỏi không phải "tránh
admin thế nào" mà "**đặt phần admin ở đâu cho gọn nhất**". Ba đường:

| Đường | Được | Mất |
|---|---|---|
| **A. Agent chạy admin** | đơn giản nhất | mọi thứ Agent làm đều đặc quyền; một lỗi trong Agent là lỗi đặc quyền |
| **B. Trợ lý đặc quyền nhỏ** (service/task SYSTEM) chỉ để xoay mật khẩu; Agent thường gọi tới | Agent giữ bề mặt nhỏ, không admin; chỉ trợ lý ~50 dòng là đặc quyền | thêm một thành phần, thêm một IPC |
| **C. Mật khẩu cố định đặt một lần lúc cài** | không cần xoay lúc chạy | **mất tính vé-một-lần** — mật khẩu lộ = quyền đứng mãi. Vi phạm tinh thần Q93 ràng buộc 2 |

Đường **C loại** vì nó vứt chính tính chất bảo mật của thiết kế. Giữa **A** và
**B**: B đúng hơn về nguyên tắc bề-mặt-nhỏ, nhưng A đơn giản hơn cho v1. Đây là
**quyết định của chủ sản phẩm**, và nó phải công khai vì nó động tới đánh đổi
UAC/T1 của Q95 — dù đường nào thì cài Nexus-điều-khiển-không-giám-sát cũng sẽ có
**một** lần nâng quyền admin lúc cài (RustDesk là dịch vụ). Điều N3.3b tránh được
là admin **mỗi lần chạy**, không phải admin lúc cài.

`nexus_agent/engine.py` xây trung lập với quyết định này: mỗi hàm khai rõ quyền
nó cần (`lay_id` thường; `dat_mat_khau`/`xoay_mat_khau`/`ghi_cau_hinh` đặc
quyền), còn "ai chạy nó với quyền gì" để tầng gọi quyết sau khi chốt A/B.

### Sắc thái phải nói với khách, KHÔNG được giấu (threat model)

LTT vận hành **cả** điểm hẹn (ký, bảo chứng khoá công khai của máy đích) **và**
relay. Chứng minh trên chặn relay **thụ động**. Nó **không** tự chặn một
**MITM chủ động** do chính người vận hành máy chủ: vì controller tin khoá công
khai của máy đích *do máy chủ bảo chứng* (`sign_pk`, `client.rs:777`), một máy chủ
độc hại có thể tráo khoá của nó vào giữa rồi giải mã.

Nói thẳng: **LTT không thể lén đọc màn hình khách**, nhưng về lý thuyết **có thể
dựng MITM chủ động** nếu tự tay tráo khoá — và việc đó để lại dấu (khoá đổi) và
là một hành vi cố ý, khác hẳn "relay tình cờ thấy". Theo cam kết minh bạch của
threat model, điều này phải **nói với khách**, không giấu. Giảm nhẹ thật sự cần
**ghim/đối chiếu khoá máy đích ngoài băng** — ghi vào việc còn để mở.

### Một phát hiện ngoài kế hoạch — relay đang mở cho cả Internet

Lúc kiểm kết nối trên máy chủ, cổng **21118 và 21119** (hỗ trợ web client) có
kết nối `Established` từ **`194.88.98.84`** và **`69.5.169.96`** — không phải máy
nào của chúng ta. `hbbs`/`hbbr` mặc định **không giới hạn ai được dùng**, nên
bất kỳ ai biết địa chỉ đều nối vào được.

Hệ quả phải xử lý trước khi có khách trả tiền: đây vừa là **chi phí băng thông
người khác xài** (R3), vừa là bề mặt tấn công trên chính máy làm NAT gateway cho
mạng VM (rủi ro #1 của Q96). Chưa xử lý; ghi lại ở đây để không rơi.

---

## 4. Việc làm được trên 2 VM cùng gateway (Q2 đã trả lời)

- **V1–V5, V7:** làm được — đây là cấu hình + luồng, không phụ thuộc topo mạng.
- **V6 (T10):** làm được bằng cách **ép relay** dù hai VM cùng LAN.
- **KHÔNG làm được:** tỉ lệ P2P/relay thật (cùng NAT) — để dành 2 mạng khác nhau.

## 5. Ràng buộc mang theo từ Q93 (không được rơi khi tích hợp)

- Luồng điều khiển **không** đi qua control plane (ràng buộc 3): Agent cấu hình
  RustDesk trỏ thẳng relay LTT, control plane chỉ cấp vé.
- Engine phải **kiểm vé**, không chỉ control plane cấp (ràng buộc 2): thể hiện
  qua mật khẩu-một-lần mà Agent chỉ đặt **sau khi** thấy vé hợp lệ.
- Chỉ báo phiên không tắt được + nút ngắt (ràng buộc 7) — V7.
- Không copy/link mã AGPL vào Agent; không "custom client generator" (Q97).

## 6. Trạng thái — 2026-08-20

**4/7 câu đã trả lời bằng đo thật** (V1, V2, V3, V5 — xem §3b). Quan trọng nhất:
**V1 đứng vững**, nên điều kiện sống còn của Rổ 1 (Q97) được chứng minh chứ không
còn là giả định, và **không có gì buộc trượt sang Rổ 2**.

**Ba câu còn lại — V4, V6/T10, V7 — chặn bởi đúng MỘT thứ: cần máy thứ hai.**
Cả ba đều đòi một **phiên điều khiển thật giữa hai máy**: V4 cần bên điều khiển,
V6/T10 cần lưu lượng thật đi qua relay để bắt gói, V7 cần phiên đang chạy mới
thấy chỉ báo. Một máy không dựng được phiên với chính nó.

**Không** cài client lên gateway để làm bên điều khiển: gateway đang chạy relay,
nên nó vừa là bên đo vừa là bên bị đo — phép đo T10 sẽ không dùng được. Cần một
VM thứ hai, và nó cũng là máy vứt đi.
