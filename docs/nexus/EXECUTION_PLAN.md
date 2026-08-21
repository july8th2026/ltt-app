# LTT NEXUS — Kế hoạch thực thi sống

> Lập 2026-08-17. Đây là **dependency plan thật của repo này**, không phải chuỗi
> 01→42 của pack chạy theo số thứ tự (`README.md` của pack cho phép đổi thứ tự,
> gộp, bỏ task N/A nếu có bằng chứng).
>
> File này là **ledger**: mỗi lần đổi thứ tự hay bỏ một task, ghi lý do vào mục
> 7. Không tạo thêm file quản trị nào khác — pack yêu cầu số artifact tối thiểu.
>
> Đọc `CURRENT_STATE_AUDIT.md` trước. Mọi kết luận dưới đây dựa vào nó.

---

## 1. Việc phải xử lý trước khi Nexus bắt đầu

**Đã chốt 2026-08-17: P1 — đóng nợ trước, rồi mở Nexus.**

Cải chính so với bản đầu của file này: H36.9–12 **đã xong 2026-08-16**
(`CLAUDE.md` lúc đó ghi sai; đã sửa). Nợ thật là **H35.9**, năm điều kiện §11
của `API_PLATFORM_FULL_RELEASE_READINESS.md`.

Tiến độ H35.9 (chi tiết ở `KE_HOACH_TRIEN_KHAI.md`):

| | Điều kiện | Trạng thái |
|---|---|---|
| a | Tách bản sao pepper khỏi CSDL — **phần công cụ + đã áp lên máy chủ** | ✅ 2026-08-17 |
| b | Sinh pepper production + cất một bản ngoài máy | ⬜ việc của người |
| c | Đo lại tải với PostgreSQL thật qua Cloudflare | ⬜ |
| d | Xác nhận trần 100 MB / 100 giây trên tunnel thật | ⬜ |
| e | Nối `metrics` vào cảnh báo + xoay khoá provider | ⬜ |

Nexus (N2) bắt đầu sau khi năm dòng trên xanh và bản `public-api-v2` đã deploy.

---

## 2. Ba quyết định chặn — không suy ra được từ repo

Đây là những thứ mà **đoán sai làm hỏng hàng tháng công việc**, nên chúng chặn
thật chứ không phải chặn cho có. Chi tiết bằng chứng ở `CURRENT_STATE_AUDIT.md`
mục 4.

Chủ sản phẩm đã trả lời ngày **2026-08-17**:

| # | Câu hỏi | Quyết định | Hệ quả phải mang theo |
|---|---|---|---|
| **D1** | Đường giấy phép engine | **Dùng RustDesk AGPL-3.0, giữ ranh giới tiến trình** | Ranh giới phải **thật**, không phải danh nghĩa: engine chạy như tiến trình/dịch vụ riêng, giao tiếp qua IPC/API có hợp đồng rõ, **không** link chung, **không** copy mã AGPL vào module LTT. Bắt buộc kèm `THIRD_PARTY_NOTICES`, ghi exact commit, và track mọi patch (OSS_BOUNDARY_RULES 2/5/6). **Rủi ro R1 vẫn mở** — pack invariant #6 yêu cầu legal review trước phát hành thương mại; đây là quyết định kinh doanh có ý thức, không phải kết luận pháp lý |
| **D2** | Hạ tầng relay | **ĐÃ CHỐT 2026-08-18: VPS trả phí riêng (~5 USD/tháng) → Q94** | Oracle Always Free là $0 thật nhưng trần 50 Mbps và máy để không bị thu hồi; mở cổng tại nhà thì phơi mạng nhà và có thể vướng CGNAT. N1.1 **hết chặn** ngay khi có máy — runbook ở `N1_RELAY_RUNBOOK.md` |
| **D3** | Mô hình tiền | **Thuê bao tháng theo số máy** | Sổ credit hiện tại **không** phủ được: cần gia hạn định kỳ, ân hạn, và auto-charge — đúng thứ **Q53 đã cố ý hoãn** vì thiếu consent/cap/replay protection. Nghĩa là H-thuê-bao là một hạng mục riêng, có quyết định riêng, **không** được nhét vào Nexus như một chi tiết |

Câu hỏi phụ, chưa cần chốt: **v1 có cần app mobile không?** Nếu có thì thêm
23–28 + 38 (chính sách store) và một chu kỳ duyệt App Store.

---

## 3. Việc làm được **ngay**, không phụ thuộc D1/D2/D3

Đây là phần có leverage cao nhất, và là lý do kế hoạch này không đứng im chờ
quyết định.

**Danh tính thiết bị, enrollment, presence và broker uỷ quyền là như nhau dù
engine truyền là RustDesk, MeshCentral hay WebRTC tự viết.** Chúng trả lời câu
hỏi "máy này có phải của tài khoản này không, và ai được phép mở phiên vào nó",
không đụng tới một byte nào của luồng màn hình.

Vì vậy chúng nằm trước mọi lựa chọn engine trong DAG — khác thứ tự của pack, và
đây là thay đổi thứ tự đầu tiên được ghi vào ledger (L1, mục 7).

```
N0  Quyết định D1/D2/D3 + dòng Q93          ← chặn N4 trở đi, KHÔNG chặn N2
        │
N2  Nền tảng thiết bị (làm được ngay)
    N2.1 devices + enrollment khoá công khai
    N2.2 presence
    N2.3 session broker (vé ngắn hạn) + thu hồi
    N2.4 sự kiện kiểm toán
    N2.5 apps/nexus — bề mặt khách hàng
        │
N1  Feasibility engine + mạng (cần D1, D2)
    N1.1 dựng rendezvous/relay trên IP công khai, đo direct vs relay
    N1.2 đo chất lượng phiên tới máy Windows thật
        │
N3  Sản phẩm endpoint Windows
    N3.1 Agent LTT — nửa ĐỘC QUYỀN  ✅ XONG 2026-08-17 (không cần D1/D2)
    N3.2 Ghép engine AGPL           🔓 GỠ CHẶN 2026-08-20 (Q97: RustDesk nguyên bản)
    N3.3a Xác minh cập nhật (ký Ed25519 của LTT)  ✅ XONG 2026-08-18 (Q95)
    N3.3b Dịch vụ Windows + bản cài              ⬜ không còn chặn (Q95)
N4  Mobile (cần quyết định phạm vi)
N5  Sẵn sàng vận hành
N6  Thương mại hoá + phát hành
```

---

## 4. N2 — lát cắt đầu tiên, chi tiết

Đây là phần tôi đề nghị bắt đầu ngay sau khi có câu trả lời cho mục 1.

### N2.0 — Dòng quyết định Q93 ✅ XONG 2026-08-17

Đã thêm vào `docs/QUYET_DINH_NEN_TANG.md` (nối sau Q92, không sửa đè dòng nào),
kèm ba mục mới ở §5 "Còn để mở": D2 (relay), legal review AGPL, và thuê bao
tháng. Mười ràng buộc của Q93 truy ngược về `04_THREAT_MODEL.md` §4.

Nội dung gốc của đề xuất giữ lại dưới đây để đối chiếu:

`AGENTS.md` mục 2.3 cấm sửa `platform_core/`/`server/` khi thêm app, và yêu cầu
**dừng lại giải thích** khi buộc phải sửa. Nexus buộc phải sửa (audit mục 4.2).
Tiền lệ đúng là Q92: bổ sung công khai vào bảng quyết định thay vì đi vòng.

Nội dung Q93 đề xuất:

> Nexus là **platform capability**, không phải một app trong `apps/`. Domain ở
> `platform_core/nexus/`, bề mặt HTTP cho endpoint/relay ở `server/nexus/`,
> `apps/nexus/` chỉ là bề mặt khách hàng. Danh tính thiết bị thuộc về **tài
> khoản**, không thuộc về app. Khoá riêng của thiết bị **không bao giờ** rời
> máy đó. Luồng điều khiển **không bao giờ** đi qua control plane. Mặc định
> fail-closed: `LTT_NEXUS` tắt, không có thiết bị nào được ghép khi cờ tắt.

### N2.1 — `devices` + enrollment ✅ XONG 2026-08-17

`platform_core/nexus/` (`__init__.py` cờ fail-closed, `tables.py`, `devices.py`)
+ migration `b165aa3584e0` + `tests/test_223_nexus_devices.py` (**18 test**).

Ba thứ đáng ghi lại:

- **Khoá riêng không có chỗ để nằm.** Test chốt bằng *cấu trúc*: bảng thiết bị
  không được có cột nào tên `private_key`/`secret`/`token`. Thêm một cột như vậy
  là đỏ ngay, chứ không phải đỏ sau khi CSDL bị đọc trộm.
- **Ba lý do từ chối mã ghép nói cùng một câu.** Mã sai, hết hạn, đã dùng — nếu
  ba thông điệp khác nhau thì việc dò mã biết được mình đang tới gần.
- **`attempts` KHÔNG phải hàng rào chống dò**, và docstring nói thẳng: đổi mã
  tra theo digest nên mã sai không khớp dòng nào. Chống dò thật nằm ở entropy 40
  bit + cửa sổ 5 phút + rate-limit ở tầng HTTP (việc của route).

**Migration đầu tiên dùng `a1b2c3d4e5f6` — trùng với `chat_ai_studio`**, tạo
vòng lặp trong đồ thị revision khiến **mọi** lệnh alembic chết, kể cả `current`.
Bộ test không bắt được vì test dựng schema bằng `Base.metadata.create_all()` chứ
không chạy alembic. Đã thêm hai test tĩnh (id duy nhất, đúng một head), đã kiểm
"có răng". Bài học vào mục 6 làm R10.

Đã kiểm `upgrade → downgrade → upgrade` trên SQLite vứt đi, một head duy nhất.
**Chưa áp lên production** — cờ `LTT_NEXUS` tắt, bảng chưa dùng.

Nội dung thiết kế gốc giữ lại để đối chiếu:

- Bảng `devices`: `id`, `user_id`, tên máy do khách đặt, fingerprint phần cứng,
  **khoá công khai** của thiết bị, thời điểm ghép, trạng thái, ai thu hồi và
  lúc nào.
- Ghép máy bằng **mã ghép dùng một lần, có hạn ngắn**, khách lấy từ web đã đăng
  nhập. Máy sinh cặp khoá **tại chỗ**, chỉ gửi khoá công khai lên. Server không
  bao giờ thấy khoá riêng (invariant #2 của pack).
- Xác thực request từ thiết bị bằng chữ ký, không bằng bearer token dài hạn.
  Đây là chỗ **không** chép `watch_auth.py`: mẹo nhét token vào bảng `sessions`
  đủ cho một agent copy file, không đủ cho danh tính thiết bị (không chống được
  nhân bản token, không thu hồi được theo máy).
- Ownership check theo đúng tư duy `public_api/principal.py`: 404 cho thiết bị
  của người khác, không bao giờ 403 — nếu không, mọi `device_id` thành oracle.

### N2.2 — Presence ✅ XONG 2026-08-17

**Online được SUY RA, không lưu thành cột.** `dang_online()` tính từ
`last_seen_at`; không có cột `is_online` nào để đi dọn. Một cột như vậy sẽ nói
dối đúng lúc tiến trình ghi nó chết — tức là đúng lúc người ta cần nó đúng nhất.

Nên việc dọn duy nhất là **mã ghép hết giá trị**, hai thời hạn khác nhau vì hai
loại dòng có giá trị khác nhau: mã **đã dùng** là mẩu kiểm toán ("máy này ghép
lúc nào, từ IP nào") giữ 365 ngày theo Q75; mã **hết hạn không ai dùng** không
kiểm toán gì, giữ 30 ngày đủ để nhìn ra một chuỗi lần dò.

Nối vào `_quet_canh_bao` trong vòng bảo trì — **sau lease**, không trong vòng
job. Gác sau cờ `LTT_NEXUS`: cờ tắt là **không chạm gì cả**, không phải "thử rồi
bỏ qua lỗi" — khi tắt thì bảng có thể còn chưa migrate, và truy vấn một bảng
chưa tồn tại mỗi lượt sẽ làm log ngập.

### N2.2 — thiết kế gốc

Nhịp tim từ thiết bị, ghi trạng thái online/offline. **Không** dùng bảng `jobs`.
Vòng dọn presence quá hạn phải nằm sau `SingletonLease` (`platform_core/leases.py`)
— worker chạy nhiều tiến trình, đây đúng là lỗi H36 đã sửa một lần rồi.

### N2.3 — Session broker ✅ XONG 2026-08-17

`platform_core/nexus/sessions.py` + bảng `nexus_sessions` + migration
`d649cfad754f` + **19 test** (`test_224`).

Quyết định quan trọng nhất: **ràng buộc nằm trong CHỮ KÝ hàm, không nằm trong kỷ
luật người viết.** `cap_ve` nhận **đối tượng thiết bị** và tự so `device.user_id`
với người xin; không có tham số `device_id`, không có cờ `force`/`as_admin`. Cách
sai là nhận id rồi dặn nhau "nhớ kiểm chủ trước khi gọi" — dặn nhau thì có ngày
quên, và ngày quên đó không ai thấy. Có test chốt **chữ ký** chứ không chỉ hành
vi, vì một test hành vi vẫn xanh được sau khi cửa đã mở.

Bốn thứ khác đáng ghi:

- **Một dòng vừa là vé vừa là bản ghi kiểm toán.** Tách hai chỗ thì có ngày lệch
  nhau, và lúc cần đối chiếu sau sự cố thì không biết tin cái nào.
- **`doi_ve` kiểm LẠI thiết bị**, không tin trạng thái lúc cấp. Nếu tin, nút thu
  hồi thành nút trang trí trong đúng khoảng thời gian nó cần có tác dụng nhất.
  Có test cho đúng kịch bản "thu hồi giữa lúc cấp và lúc dùng".
- **Cấp vé ≠ mở phiên.** `dang_mo` chỉ tính vé đã đổi. Lẫn hai thứ thì chỉ báo
  "đang có người điều khiển" sẽ sáng khi chưa ai vào máy, và người dùng học được
  cách bỏ qua nó — làm hỏng chính ràng buộc 7.
- **Băm vé khác không gian với băm mã ghép.** Cùng cách băm thì một digest lấy ở
  bảng này đem thử được ở bảng kia.

### N2.3 — thiết kế gốc

Server cấp **vé ngắn hạn** cho một phiên cụ thể: ai điều khiển, máy nào, hết hạn
lúc nào, quyền gì (xem-only hay điều khiển). Đây là chỗ duy nhất uỷ quyền được
quyết định, và nó phải ở server (invariant #3). Thu hồi = vé chết ngay, không
chờ hết hạn.

### N2.4 — Kiểm toán

Mỗi phiên ghi một bản ghi bất biến: ai, máy nào, bắt đầu/kết thúc, từ IP nào,
kết thúc vì lý do gì. Đây cũng là cách thoả invariant #4 của pack (không có
backdoor bí mật): **admin không được có đường vào máy khách không để lại dấu**.

### N2.6 — bề mặt cho AGENT ✅ XONG 2026-08-17

`platform_core/nexus/agent_auth.py` + `server/nexus/` + **16 test** (`test_228`).

**Agent không dùng token, agent KÝ.** Ràng buộc 1 nói khoá riêng không rời máy;
hệ quả kỹ thuật là bearer token bị loại — token chép được, và chép được nghĩa là
ai đọc được ổ đĩa hay log của máy đó **trở thành** máy đó.

Ed25519 vì không có tham số nào để chọn sai: RSA đòi chọn độ dài/padding/hàm băm,
ECDSA cần nonce ngẫu nhiên mỗi lần ký mà nonce lặp làm **lộ khoá riêng**. Ed25519
tất định, một cách dùng duy nhất.

Chuỗi ký gồm **bốn** phần, và mỗi phần có test riêng chứng minh nó load-bearing:
`method` + `path` (chữ ký của `heartbeat` không dùng lại được ở `redeem`),
`timestamp` (chữ ký nghe được không dùng được mãi mãi), `sha256(body)` (sửa nội
dung thì chữ ký hỏng). Đây là loại thiết kế mà thiếu phần nào cũng vẫn "chạy"
lúc thử và chỉ sai khi có người tấn công — nên nó được chốt bằng test, không
bằng lời.

Ba việc khác đáng ghi:

- **Rate-limit về đúng chỗ nó thuộc về.** `devices.py` khai rõ nó không tự giới
  hạn nhịp và đó là việc của route; `server/nexus/` trả nợ câu đó, và dùng lại
  `public_api.limits` (thêm cửa công khai `allow()`) chứ **không** dựng bộ đếm
  thứ hai — hai bộ đếm thì không ai trả lời được "khách bị chặn bởi cái nào".
- **Khoá công khai được kiểm dạng NGAY LÚC GHÉP.** Trước đó các test dùng khoá
  giả `"ltt_dev_" + "a"*64`: lưu xuống được nhưng **không bao giờ xác thực
  được** — tức là test xanh trong khi một thiết bị thật sẽ không kết nối nổi.
  Nay `doi_ma` từ chối ở biên, và test dùng khoá Ed25519 thật.
- **Đổi vé cần HAI phép kiểm độc lập**: chữ ký nói *ai đang gọi*,
  `session.device_id` nói *vé này dành cho ai*. Thiếu phép thứ hai thì một thiết
  bị hợp lệ đổi được vé của thiết bị khác — có test cho đúng kịch bản đó.

### N2.5 — `apps/nexus`

Danh sách máy, trạng thái online, nút ghép máy mới, nút thu hồi, lịch sử phiên.
Dùng LTT Carbon Red + hợp đồng bề rộng trang (Q52/Q61). Kiểm bằng trình duyệt
thật trên URL công khai, không chỉ loopback (`CLAUDE.md` mục 5b).

### N3.1 — agent tham chiếu ✅ XONG 2026-08-17

`nexus_agent/` (thư mục gốc, theo tiền lệ `codex_sidecar/`) + **11 test**
(`test_229`).

**Tách được ra làm trước vì endpoint là HAI tiến trình.** Chỉ tiến trình B
(engine) vướng AGPL; tiến trình A — danh tính, enrollment, presence, vé — không
chạm một dòng nào. Nên nó viết được **trong khi** D1 và D2 còn mở, và đó là lý
do ranh giới ở `03_OSS_LICENSE.md` §5 đáng giá hơn một dòng trong tài liệu.

Ba điều đáng ghi:

- **Khoá riêng không được là một file.** Một file 32 byte thô làm ràng buộc 1
  của Q93 thành một câu nói: chép file = nhân bản thiết bị. Dùng **DPAPI** qua
  `ctypes` (không thêm phụ thuộc — mỗi phụ thuộc trên máy khách là một thứ nữa
  phải đóng gói, ký và vá khi có CVE), kèm `entropy` riêng nên một tiến trình
  khác chạy **cùng tài khoản** cũng không mở được. Test đọc file trên đĩa và
  khẳng định nó khác khoá thật.
  **Giới hạn được ghi vào docstring:** DPAPI không cứu một máy đã bị chiếm —
  mục tiêu là chặn **lan sang máy khác**, đúng phạm vi T3.
- **Đường plaintext ngoài Windows mặc định ĐÓNG.** Phải đặt biến môi trường mới
  chạy. Một bản build lỡ tay mang đường đó ra production là loại lỗi không ai
  phát hiện cho tới khi muộn.
- **Test chạy qua HTTP THẬT** (uvicorn, cổng ngẫu nhiên). Một test gọi thẳng hàm
  dùng chung `canonical()` cho cả hai bên, nên **không bao giờ** phát hiện được
  việc agent và server dựng chuỗi ký lệch nhau — mà triệu chứng của lỗi đó phía
  khách trông y hệt "sai khoá".

Sửa luôn một cái tên nói dối: `agent_auth.sign_for_test` → `sign`. Nó ký **mọi
request của mọi máy khách**; chữ `test` trong tên sẽ khiến người đọc sau tưởng
có thể bỏ đi. Có test chốt `nexus_agent/` không gọi hàm nào tên `*_for_test`.

### Tiêu chí hoàn thành N2

- Ghép được một máy giả lập, thấy nó online, mở được vé phiên, thu hồi được;
- test tự động phủ: ghép, chống ghép lại bằng mã đã dùng, hết hạn mã, ký sai bị
  từ chối, thiết bị người khác trả 404, thu hồi làm vé chết ngay;
- `python tools\gate.py` xanh;
- kiểm trình duyệt thật trên `https://app.lttstudios.com`;
- **chưa có luồng điều khiển nào** — đó là N1/N3.

---

## 5. Ánh xạ 42 prompt của pack sang kế hoạch này

| Prompt pack | Xử lý | Lý do |
|---|---|---|
| 01, 02 | ✅ **Xong** → `CURRENT_STATE_AUDIT.md` | Gộp: cùng một lần đọc repo |
| 03 (OSS/license) | ✅ **Xong** → `03_OSS_LICENSE.md`; phần *hướng đi* đã nâng thành **D1** | Kiểm kê + ranh giới là việc riêng, không được coi là xong chỉ vì D1 đã chọn hướng |
| 04 (threat model) | ✅ **Xong** → `04_THREAT_MODEL.md` | Tách riêng chứ không gộp: nó đẻ ra **10 điều khoản** cho Q93, mỗi điều truy ngược được về một mối đe doạ. Gộp vào Q93 sẽ mất phần *vì sao* |
| 05, 06 | Gộp vào N2.0 + N2.1 | Contract freeze sớm là chống chỉ định — Q49/Q85 đã cho thấy contract tốt lên sau khi có lát cắt dọc đầu tiên |
| 07, 08 | → N1.1, **sau** N2 | Đảo thứ tự: cần D2 (tiền thuê VPS) và không chặn N2 |
| 09, 10 | → N1.2, N4 | |
| 11 | → N2.5 | |
| 12 | → phụ thuộc D3 | Entitlement khác nhau hoàn toàn giữa thuê bao và credit |
| 13–17 | → N2.1–N2.4 | Đây là lát cắt đầu tiên, **đưa lên trước** |
| 18–22 | → N3 | Cần D1 trước |
| 21 (updater ký) | ⚠️ cần **mua chứng thư ký mã** | Chi phí + thời gian cấp phát; nêu sớm để không phát hiện lúc sắp phát hành |
| 23–28 | → N4 | Chỉ khi v1 có mobile |
| 29–35 | → N5 | |
| 36 | → phụ thuộc D3 | |
| 37–42 | → N6 | |

Không prompt nào bị bỏ. Bốn prompt bị gộp, hai bị đảo thứ tự, ba bị nâng thành
quyết định chặn.

---

## 6. Sổ rủi ro

| # | Rủi ro | Mức | Giảm bằng |
|---|---|---|---|
| R1 | AGPL lây sang phần độc quyền của LTT | **CAO lại (Q100, Rổ 2)** | Q97 (Rổ 1) đã hạ R1 xuống Thấp, nhưng **Q100 đảo sang Rổ 2 (sửa client)** nên §13 kích và R1 **trở lại CAO**. Giảm bằng: legal review trước phát hành thương mại (bắt buộc lại), ranh giới tiến trình+IPC cứng, **không copy/link mã AGPL vào Agent** (rule 2/3). Việc đã đo (V1-V8) không phí — nền cấu hình vẫn dùng, Rổ 2 chỉ thêm khả năng sửa client |
| R2 | Không có IP công khai → sản phẩm không chạy được ngoài LAN | **Cao** | D2 trước N1 |
| R3 | Chi phí băng thông relay vượt dự tính | Trung bình | N1.1 phải **đo** tỉ lệ direct vs relay và GB/giờ thật, không ước lượng |
| R4 | Một sản phẩm điều khiển máy từ xa bị lạm dụng để chiếm quyền máy nạn nhân | **Cao** | `04_THREAT_MODEL.md` T1. **Không đóng được bằng kỹ thuật** — mọi bước của kẻ lừa đảo đều "hợp lệ", hệ thống làm đúng thứ nó được thiết kế. Giảm bằng: mã ghép sinh **trên máy đích**, hạn rất ngắn, cảnh báo bằng ngôn ngữ hậu quả, chỉ báo phiên không tắt được, và email cho chủ tài khoản **mỗi lần ghép**. Phần còn lại là rủi ro **chấp nhận có ý thức**, phải ghi vào Q93 chứ không để im |
| R5 | Phát hành agent chưa ký mã Windows | **Trung bình, CHẤP NHẬN có ý thức (Q95)** | Chủ sản phẩm chọn phát hành sớm. Rủi ro còn lại là thật và **không giảm hết được**: khách thấy cảnh báo SmartScreen, làm giảm tỉ lệ cài xong và rèn phản xạ bấm-qua-cảnh-báo mà T1 tận dụng. Giảm bằng: nói trước trên trang tải, công bố SHA-256, không đòi quyền admin nếu tránh được. **Phần KHÔNG đánh đổi:** toàn vẹn bản cập nhật vẫn bắt buộc — `nexus_agent/updates.py`, 16 test |
| R6 | App Store từ chối app điều khiển từ xa | Trung bình | Đọc guidelines **trước** khi viết mobile, không phải sau |
| R7 | Nexus kéo chậm Public API đang treo | Trung bình | Mục 1 |
| R8 | Nhánh làm việc: Nexus commit lẫn vào `public-api-v2` | Thấp | Nhánh riêng `nexus-foundation` từ `master` |
| R9 | **Test chốt được *script có lệnh*, không chốt được *lệnh đã chạy trên máy thật*** | **Cao** | Bài học 2026-08-17: `test_scheduled_backup_tightens_acl` xanh suốt nhiều tháng trong khi `D:\LTTBackups` thực tế mở cho `Authenticated Users`. Mọi hạng mục Nexus có phần "cấu hình trên máy" (cổng relay, chứng thư ký, quyền dịch vụ) phải có **một phép đo trên máy thật**, không chỉ một assertion trên mã nguồn |
| R10 | **Bộ test xanh trong khi CSDL không nâng cấp nổi** | Trung bình | Test dựng schema bằng `Base.metadata.create_all()`, **không** chạy alembic — nên một migration hỏng vẫn để bộ test xanh. Đã dính ngay ở N2.1: revision id trùng làm mọi lệnh alembic chết. Giảm bằng hai test tĩnh trong `test_223` (id duy nhất, đúng một head) **và** chạy `upgrade → downgrade → upgrade` thật trên CSDL vứt đi cho mỗi migration mới. Test tĩnh không thay được lần chạy thật |

---

## 7. Ledger — thay đổi so với pack

| # | Thay đổi | Lý do |
|---|---|---|
| L1 | Đưa 13–17 (device/enrollment/presence/broker/audit) lên **trước** 07–10 (POC engine/mạng) | Bốn năng lực này không đổi theo engine, nên chúng là phần duy nhất làm được trước khi có D1/D2. Chờ quyết định mới bắt đầu là lãng phí thời gian không cần thiết |
| L2 | Nâng 03 (license) từ task thành **quyết định chặn D1** | Đã kiểm chứng AGPL-3.0 trực tiếp; đây là rẽ nhánh pháp lý, không phải task kỹ thuật |
| L3 | Gộp 01+02 thành một tài liệu | Cùng một lần đọc repo; hai file sẽ trùng nội dung |
| L4 | Hoãn 05/06 (architecture ADR + contract freeze) tới sau N2.1 | Q49/Q85 trong repo này đều là bằng chứng rằng contract tốt lên sau lát cắt dọc đầu tiên, không phải trước |
| L5 | Thêm N2.0 (Q93) — không có trong pack | `AGENTS.md` bắt buộc: sửa nền tảng thì phải có dòng quyết định công khai. Tiền lệ Q92 |
| L6 | 2026-08-17: D1/D3 đã chốt, D2 hoãn có chủ ý | Xem mục 2. D3 (thuê bao tháng) **đẻ ra một hạng mục mới ngoài phạm vi pack**: cổng gia hạn định kỳ. Pack không có prompt nào cho nó vì pack giả định entitlement đã có sẵn |
| L7 | 2026-08-17: bản đầu của file này ghi sai nợ tồn (H36.9–12 thay vì H35.9) | Nguồn là `CLAUDE.md` đã stale. Đã sửa cả hai. Ghi lại đây vì đây đúng là kiểu lỗi mà `QUYET_DINH_NEN_TANG.md` §4 cảnh báo: phần *tóm tắt trạng thái* không được cập nhật trong khi phần *nhật ký* thì có |
| L8 | **Không** thêm `docs/nexus/` vào `authoritative_docs` của hồ sơ hệ thống | Danh sách đó dành cho nguồn **có thẩm quyền**; `docs/nexus/` hiện là tài liệu lập kế hoạch. Thẩm quyền của Nexus sẽ nằm ở **Q93 trong `QUYET_DINH_NEN_TANG.md`**, file đã có sẵn trong danh sách — nên hồ sơ sẽ tự mang quyết định Nexus ngay khi Q93 được viết, không cần đổi cấu hình |

---

## 8. Trạng thái

**Status: BLOCKED trên D1/D2/D3 cho N1/N3/N4; READY để bắt đầu N2 ngay sau khi
chọn P1/P2 ở mục 1.**

Bước kế tiếp đề nghị: chọn mục 1, trả lời D1/D2/D3, rồi mở nhánh
`nexus-foundation` và bắt đầu N2.0 + N2.1.

---

## 8. N3.3a — xác minh cập nhật (Q95) ✅ XONG 2026-08-18

`nexus_agent/updates.py` + **16 test** (`test_230`).

Q95 bỏ chứng thư ký mã Windows nhưng **không** bỏ thứ này, vì hai cái giải hai
bài toán khác nhau: chứng thư làm *Windows* tin binary lúc cài; chữ ký phát hành
làm *agent* tin bản vá trước khi chạy. Invariant #7 và ràng buộc 10 của Q93 nói
về cái sau, và nó **không tốn tiền** — nền tảng đã dùng Ed25519 cho `agent_auth`.

**Ba tấn công, mỗi cái vượt được hai cái kia** — nên phải có đủ ba lớp:

| Tấn công | Ai bắt |
|---|---|
| Đổi file sau khi ký | `sha256` trong manifest |
| Đổi luôn `sha256` cho khớp | chữ ký phủ cả manifest |
| **Phát lại manifest CŨ** | **chỉ số phiên bản** — chữ ký và `sha256` đều đúng |

Cái thứ ba là cái dễ quên nhất: manifest cũ **từng hợp lệ thật**, nên chữ ký của
nó đúng mãi mãi. Phát lại nó đẩy máy khách về bản có lỗ hổng đã vá — chữ ký
đúng, nội dung đúng, mà vẫn là tấn công.

Ba lựa chọn fail-closed:

- `RELEASE_PUBLIC_KEY` **rỗng trong repo** → agent chưa cấu hình khoá thì **từ
  chối mọi bản cập nhật**. Thà không cập nhật còn hơn cập nhật bừa.
- Khoá **ghim trong mã**, không tải về. Agent tải khoá tin cậy thì kẻ điều khiển
  đường tải đưa khoá của nó, và cả chuỗi tin cậy sụp trong một bước.
- Phiên bản **không parse được** → coi là *không* mới hơn. Ngược lại thì một
  chuỗi lạ thành đường lách qua phép chặn hạ cấp.

Còn nợ, và là **việc của người**: sinh cặp khoá phát hành, ghim phần công khai
vào `RELEASE_PUBLIC_KEY`, và cất phần riêng **ngoài repo, ngoài máy chủ web,
ngoài `secrets/app.env`** — nó ký thủ công cho mỗi bản phát hành.

---

## 9. Vòng lặp sản phẩm — đã chạy thật ✅ 2026-08-18

`tests/test_231_nexus_e2e.py`, **6 test**. Máy chủ HTTP thật; phía web đi bằng
cookie phiên và CSRF thật, phía máy khách đi bằng chính `NexusClient` mà khách
sẽ chạy.

Sáu file test trước kiểm từng mảnh. Cái chưa ai kiểm là **thứ khách thực sự
làm**: mở web → bấm "Ghép một máy mới" → đọc mã trên màn hình → gõ vào phần mềm
trên máy mình → thấy máy hiện ra.

Chỗ nguy hiểm nằm ở chỗ ba mảnh gặp nhau: mã hiện trên HTML dạng `ABCD-EFGH`
(có gạch nối, để đọc cho nhau nghe), còn `doi_ma` chuẩn hoá trước khi băm. Hai
bên đúng riêng **không** có nghĩa là chúng khớp. Nếu lệch, khách gõ đúng thứ họ
nhìn thấy mà vẫn bị từ chối — và không ai đoán ra vì sao.

Bốn tính chất được chốt bằng đường đi thật, không bằng gọi hàm:

- ghép xong **chưa phải** là đang bật — lẫn hai thứ thì danh sách nói máy online
  trong khi nó chưa từng kết nối;
- khách bấm **Thu hồi** → agent dừng hẳn ở nhịp kế tiếp **và tự xoá khoá**;
- **một mã chỉ ghép được một máy** — mã nạn nhân đọc qua điện thoại (T1) phải
  chết ngay sau lần dùng đầu;
- tài khoản khác **không thu hồi được** máy của người ta: `404`, không phải 403.

---

## 10. N1.1 — relay dựng thật ✅ 2026-08-19 (Q96)

Q94 lập kế hoạch VPS Linux trả phí; thực tế dùng lại **VPS Windows đang làm NAT
gateway Proxmox** (`45.76.185.75`) → chi phí thêm **0 đồng**. `rustdesk-server`
1.1.16 nguyên bản, dịch vụ `hbbs`/`hbbr` StartMode Auto, 5 cổng mở đã xác minh
từ ngoài Internet. Chi tiết + hai rủi ro (relay trên chính gateway; Windows Eval
118 ngày) ở `N1_RELAY_RUNBOOK.md` §7, ghi thành **Q96**.

**Còn nợ:** phép đo tỉ lệ P2P/relay + GB/giờ + T10 (relay thấy nội dung không).
Cần **hai máy client thật ở hai mạng** — chưa làm được. Đây là *mục đích* của
N1.1, phần "server có chạy" chỉ là tiền đề.

## 11. N3.3b — đóng gói + phát hành ✅ 2026-08-19 (phần code)

Nửa **vòng đời** (`service.py`) xong 2026-08-18. Nửa **đóng gói + phát hành**
xong 2026-08-19, và nó lấp một lỗ thật: `updates.py` **kiểm** manifest nhưng
không có gì **tạo** ra manifest — tức là không có đường phát hành hợp lệ nào.

Bốn công cụ + một trang, tất cả có test (`test_233`–`test_235`):

- `tools/nexus_release_key.py` — sinh cặp khoá, từ chối ghi khoá riêng vào
  repo/secrets/data (Q95), không in khoá riêng ra màn hình.
- `tools/nexus_sign_release.py` — ký manifest, **dùng lại `canonical_manifest`
  của `updates.py`** nên bên ký và bên kiểm không thể lệch byte; tự kiểm bằng
  `verify_manifest` trước khi ghi ra file.
- `nexus_agent/packaging/nexus_agent.spec` — one-dir, không UPX, loại GUI/thư
  viện máy chủ (giảm Defender gắn cờ — `N3_DONG_GOI_AGENT.md` §4b).
- `tools/build_agent.py` — dựng + nén + in SHA-256; import PyInstaller *chỉ khi
  dựng* nên máy chủ/gate không cần có nó.
- `/nexus/tai` — trang tải công bố SHA-256, nói trước cảnh báo SmartScreen, cảnh
  báo T1; fail-safe khi chưa có bản (`platform_core/nexus/release.py`).

**Còn nợ, là việc trên máy thật không phải code** (`N5_VAN_HANH.md` §3): sinh
khoá thật + ghim, dựng bản đầu trên máy Windows sạch có PyInstaller.

## 12. N5 — sẵn sàng vận hành → `N5_VAN_HANH.md`

Năm điều kiện phải xanh trước khi bật `LTT_NEXUS`, quy trình phát hành từng bản,
giám sát, và ứng phó sự cố (thu hồi thiết bị → tắt cờ → dừng relay → xoay khoá
lộ). Ghi rõ: bật cờ mở phần danh tính/ghép/presence/vé/kiểm toán/trang tải,
**không** mở luồng điều khiển (chưa tồn tại) — nên bật cờ an toàn để chạy thử
nội bộ, chưa phải để mở bán.

---

## Ledger — thay đổi bổ sung

| # | Thay đổi | Lý do |
|---|---|---|
| L9 | 2026-08-19: N1.1 dựng trên gateway Windows có sẵn thay VPS Linux mua mới | Máy đã có, chi phí thêm 0 đồng, đúng mục tiêu "free". Đánh đổi: relay trên chính gateway + Windows Eval — ghi thành Q96 |
| L10 | 2026-08-19: dựng **bên ký** bản phát hành (không có trong pack như một task riêng) | Pack giả định có đường phát hành; repo này thì `updates.py` chỉ kiểm, thiếu bên tạo manifest. Không có nó thì Q95 "phát hành cho khách" không thực thi được |
| L11 | 2026-08-19: nâng N5 thành `N5_VAN_HANH.md` — runbook mở cờ + ứng phó sự cố | Prompt 29–35 của pack là "operational readiness"; gom vào một runbook thay vì bảy file, đúng nguyên tắc số-artifact-tối-thiểu (L3) |

---
## 13. BẢN ĐỒ HẠNG MỤC + TIẾN ĐỘ — 2026-08-20 (sau Q100, Rổ 2)

> ⚠️ **PIVOT Q101 (cuối 2026-08-20) — đọc trước khi tin bảng dưới.** Chủ sản phẩm
> chốt **Model B**: sản phẩm = app native (Windows/iOS/Android) + relay LTT như
> RustDesk, **có unattended**; web `app.lttstudios.com` = **chỉ docs/tài khoản/
> credit**, KHÔNG web-broker. Hệ quả cho bảng dưới: **mảng 7 (Wiring web W1–W5) +
> phần `apps/nexus` web-UI = BẰNG CHỨNG kỹ thuật đã chạy, KHÔNG phải sản phẩm** →
> đóng băng, không tính là tiến độ sản phẩm nữa. **Thêm phạm vi mới chưa có trong
> bảng:** client iOS + Android (fork cũng build được), và **billing chuyển vào
> client** (đăng nhập tài khoản LTT trong client + kiểm credit qua LTT API; cưỡng
> chế ở rendezvous là hardening sau). Bảng % dưới vẫn theo khung Q100 — sẽ tái cân
> theo Model B ở lần cập nhật kế; hiện giữ để không mất lịch sử.

> Cập nhật khi chủ sản phẩm chọn **Rổ 2** (Q100). **Sửa lần 2 cùng ngày:** tách
> riêng mảng **"Cá nhân hóa UI/UX + chức năng theo LTT"** — trước đó bị nén thành
> hai dòng con trong "Fork", mà nó chính là *lý do* chọn Rổ 2 nên phải nổi bật.
> Tách ra làm tổng % nhích xuống (~45% → ~41%) — đúng bản chất: cá nhân hóa mạnh
> là thêm phạm vi, không phải sẵn có.

### Tiến độ theo mảng việc

| # | Workstream | Trọng số | % xong | Trạng thái |
|---|---|---|---|---|
| 1 | Nền tảng & quyết định (audit, threat model, Q93-Q100) | 10% | **100%** | ✅ |
| 2 | Nền tảng thiết bị N2 (devices/enroll/presence/broker/audit/app) | 13% | **100%** | ✅ 9 file test |
| 3 | Hạ tầng relay N1 (dựng + T10) | 7% | **85%** | ✅ dựng+T10; ⬜ tỉ lệ P2P |
| 4 | Khả thi engine + primitives (V1-V8 + `engine.py` + `engine_runner`) | 9% | **95%** | ✅ đo+module+wiring; fork build xác nhận primitives |
| 5 | Fork RustDesk + tuân AGPL (fork/patch/build/công bố mã) | 8% | **82%** | ✅ **fork build CHẠY** (LTTNexus.exe **+ APK Android arm64**) + công bố mã + recipe (Win+Android); còn đổi tên/nhãn Android, macOS/iOS, release build |
| 6 | **Cá nhân hóa UI/UX + chức năng theo LTT** (client Flutter) | 13% | **90%** | 🎨 **P1-P4+P6+P7+P8 XONG**: branding, theme Carbon Red, logo, chỉ báo phiên, việt hoá mặc định, **P7 login+billing enforcement** (target từ chối khi hết credit), **P8 nhật ký truy cập** (ràng buộc 6). Còn: P8-END (ended_at), P5 non-action |
| 7 | Wiring phiên W1-W5 (vé → kết nối thật) | 11% | **100%** | ✅ XONG 2026-08-20 (test 223/227/228/229/236/237) |
| 8 | Đóng gói & phát hành endpoint (tooling + build+sign) | 6% | **72%** | ✅ tooling + build agent + **build fork LTTNexus (Win + APK Android, ký self-signed)** + **endpoint tự phục vụ bản cài** (`/nexus/dl/`, biên-cache immutable, chặn traversal, HEAD+GET, đối chiếu SHA end-to-end); ⬜ ký chính thức, bản gộp fork+agent |
| 9 | Thanh toán Q98 (credit/máy/tháng + nạp qua trình duyệt) | 9% | **85%** | ✅ cơ chế xong (test_238); còn 3 tham số của người (D12) |
| 10 | Sẵn sàng vận hành N5 (runbook + thực thi) | 7% | **70%** | ✅ runbook + E2E LIVE + **ĐÃ DEPLOY PROD 2026-08-21** (LTT_NEXUS=1, billing 50, migration f8a9b0c1d2e3→head, xác minh public URL: tải APK byte-đúng qua CF, `/nexus-agent/*` 401 đòi auth, relay-check secret nạp); ⬜ hbbs trên Vultr relay |
| 11 | Legal review + thương mại N6 | 7% | **0%** | ⬜ (chặn *bán*, không chặn dev) |

**Tổng có trọng số ≈ 90%** (2026-08-21, **ĐÃ DEPLOY LÊN PRODUCTION**: Windows +
Android tải được thật qua `app.lttstudios.com/tai-xuong`, billing 50 bật, Nexus
client API sống. 57 test).

#### Cột mốc 2026-08-21 (d) — DEPLOY PRODUCTION (Windows + Android + billing)

Go-live qua `golive-nexus.ps1` (bấm UAC): thêm `LTT_NEXUS=1`,
`LTT_NEXUS_GIA_MAY_THANG=50`, sinh `LTT_NEXUS_RELAY_SECRET` (ghi
`secrets/nexus_relay_config.txt` cho Vultr), rồi `setup\2-cai-dat.ps1`.

* **Migration prod**: `f8a9b0c1d2e3 → 5a3a13144782` (5 bước nexus) chạy trơn —
  de-risk trước bằng cách sinh đúng SQL PostgreSQL offline (không CREATEDB được
  trên prod nên không test scratch được; SQL review sạch).
* **Xác minh trên URL CÔNG KHAI** (qua Cloudflare, không chỉ loopback):
  `/health/ready` 200; `/tai-xuong` hiện Windows+Android "Tải xuống";
  **tải APK 26.420.220 byte, SHA khớp bit-đúng** qua CF (cf-cache MISS→immutable);
  `/nexus-agent/relay-check` 401 (secret đã nạp), `/status` 401 (đòi chữ ký) ⇒
  `LTT_NEXUS` sống.
* **Còn lại cho răng-thật billing**: deploy hbbs fork lên Vultr relay
  45.76.185.75 + 2 biến (`LTT_NEXUS_RELAY_CHECK_URL`, `LTT_NEXUS_RELAY_SECRET`
  trùng platform). Hiện billing cưỡng chế **client-side** (may_control) — hoạt
  động, nhưng client vá có thể lách; relay-side là lớp không lách được.

#### Cột mốc 2026-08-21 (c) — APK Android + endpoint tự phục vụ bản cài

* **Build APK Android arm64** trong WSL Ubuntu (fork RustDesk chỉ build Android
  trên Linux). Vượt 6 bẫy cross-compile (DNS WSL, rustfmt, openssl-android qua
  vcpkg target-scoped, kcp bindgen `--bindgen` sysroot, license SDK, ký release).
  Ra `app-release.apk` 26.4 MB, đã ký self-signed → cài ngoài Play Store cho nội
  bộ. Cấu hình relay/khoá LTT nằm trong `.so` nên APK trỏ đúng relay. Recipe đầy
  đủ ở fork `BUILD_ANDROID.md`. Nhãn Android còn "RustDesk" (đổi thương hiệu sau).
* **Endpoint `/nexus/dl/{file}`** (`server/nexus_download.py`) phục vụ bản cài
  THẲNG qua Tunnel từ `data/nexus_dist/` (dưới trần 100 MB CF) — không cần R2 cho
  mấy file khiêm tốn. Chặn path-traversal chặt, HEAD+GET, biên-cache immutable
  (ngoại lệ có chủ đích ở middleware: file CÔNG KHAI, version trong tên, không
  dính lớp rò-cache-per-user). Kiểm live: SHA tải về khớp bit-đúng.
* **Manifest live** `data/nexus_versions.json`: Windows + Android `available`,
  macOS/iOS "đang chuẩn bị". Bản cài + manifest là **dữ liệu vận hành** (gitignore,
  triển khai vào `data/` trên server), không nhồi binary vào git.
* Test: `test_244` mở rộng (phục vụ file thật, 404 khi thiếu, chặn traversal).

#### Cột mốc 2026-08-21 (b) — Cưỡng chế billing ở tầng RELAY (răng thật)

Ba phần, xong cả code + build + công bố (chỉ còn deploy lên gateway — việc của
người vận hành, đã ghi ở `LThbbs/LTT_HBBS_FORK.md`):

* **A (platform):** cột `nexus_devices.rustdesk_id` (migration `5a3a13144782`,
  round-trip xác minh) + `GET /nexus-agent/relay-check` (bí mật dùng chung,
  constant-time; chưa cấu hình→404 fail-closed, ID lạ→cho qua, đã đăng ký+chưa
  trả→chặn). 6 test (`test_243`).
* **B (client):** `status()` báo kèm RustDesk ID để platform ánh xạ ID→tài khoản.
* **C (fork hbbs):** fork `rustdesk-server 1.1.16` → `handle_punch_hole_request`
  hỏi platform trước khi môi giới, trả "hết credit" nếu chưa trả. **Off mặc định
  + fail-open** (relay không bao giờ tối vì platform chớp). Build `hbbs.exe` 6.6MB
  (SHA-256 `6621193e…`), công bố nhánh `ltt-hbbs`.

Đây là thứ client bị sửa **không lách được** — quyết định của chủ sản phẩm.

#### Cột mốc 2026-08-20 (b) — fork LTTNexus BUILD trên Windows thật

Rổ 2 đi từ spec sang **binary chạy được**. Fork công khai tại
`github.com/giaitritruyenthongltt-spec/LTTnexus` nhánh `ltt-nexus`: RustDesk
1.4.9 + 5 commit theo dõi được (gộp submodule · config→hạ tầng LTT · APP_NAME→
LTTNexus · fork notice AGPL · recipe build). Build ra
`flutter/build/windows/x64/runner/Release/` (rustdesk.exe + librustdesk.dll 30MB).

Xác minh trên binary: `--version`→`1.4.9`; `--get-id`→ID sinh dưới `%APPDATA%\
LTTNexus`; DLL **nhúng sẵn** server LTT `45.76.185.75` + key LTT + tên `LTTNexus`.
Nghĩa vụ AGPL Corresponding Source: đã công bố.

Toolchain đã dựng+kiểm trên máy này (Rust · VS BuildTools MSVC 14.44 + Win11 SDK
· Flutter 3.24.5 · vcpkg@120deac3 + 6 lib static · **libclang 15.0.6**). Hai bẫy
build đã ghi vào `LTTnexus/BUILD_WINDOWS.md`: libclang phải ~15 (bindgen 0.65 sinh
struct aom rỗng với libclang mới), và pub-get/cargo-fetch phải trước frb codegen.

Còn lại của Rổ 2: **P2–P8** (cá nhân hóa UI Flutter — mảng 6, chưa bắt đầu), đổi
tên exe `rustdesk.exe`→thương hiệu, release build có ký. Chạy fork-service để điều
khiển thật là hành động **chạm production** (biến máy thành điều-khiển-được) — chờ
quyết định, không tự làm.

#### Cột mốc 2026-08-20 — E2E LIVE trên Windows thật

Chạy trọn luồng khách trên chính máy Windows này, bằng **mã agent thật** (keystore
DPAPI, HTTP ký Ed25519) nói với control plane staging (cổng 8140, DB test riêng —
**không chạm prod 8100**). Chỉ **một** mắt xích được stub: subprocess RustDesk —
mà nó đã đo riêng trên VM106 (V1–V8: ghi config, `--get-id`, xoay mật khẩu, relay).

Sáu bước chạy thật, xanh (`scratchpad/e2e_live.py`):
1. Agent ký nhịp tim → server đánh dấu máy **online**.
2. Khách `cap_ve` → cấp vé (qua cổng chủ-sở-hữu + cổng thuê bao).
3. Nhịp kế mang `cho_bao` → agent xoay mật khẩu engine, **báo `engine_id`+secret** (request ký).
4. Server **mã hoá at-rest** secret (Fernet).
5. Khách lấy kết nối → secret + ID **giải mã khớp đúng** thứ agent báo.
6. Khách kết thúc → mật khẩu một-lần **bị xoá** khỏi dòng (giữ cột audit).

Binary đã dựng: `dist/nexus-agent-0.1.0.zip` (SHA-256
`dfa8fe4b533bced1928b3c6749a8acd14aacd9f8bf8cfc5297385ebdee4abd14`); `enroll`/
`status`/keystore DPAPI xác nhận chạy như một exe độc lập trên Windows.

**VM106 chết giữa chừng** (đóng băng dưới tải tải-file — đúng điểm yếu VM 4GB không
GPU đã thấy trước), nên chưa có một *lần chạy VM liên tục* nối cả hai nửa. Nhưng cả
hai nửa đã chứng minh trên Windows thật: nửa danh tính/wiring (máy này, live) +
nửa engine RustDesk (VM106, V1–V8). Nối liên tục chỉ còn chờ một máy đích đủ khoẻ.

### Mảng 6 — Cá nhân hóa theo LTT, chi tiết (đây là phần bạn hỏi)

Đây là *lý do* của Rổ 2. Client RustDesk là **Flutter**, nên hệ thiết kế web của
LTT (`ltt.css`, Carbon Red — Q52/Q61) **không dùng lại trực tiếp được** — phải
tái hiện ngôn ngữ thiết kế (màu/typo/khoảng cách) trong Flutter. Đó là công sức
thật, không phải đổi vài dòng CSS.

| Mã | Hạng mục | Loại |
|---|---|---|
| P1 | Thay thương hiệu: logo, tên "LTT Nexus" thay "RustDesk", màu Carbon Red | giao diện |
| P2 | Tái hiện hệ thiết kế LTT trong Flutter (token màu/typo/spacing) | giao diện |
| P3 | Cửa sổ điều khiển + thanh công cụ restyle theo LTT | giao diện |
| P4 | Chỉ báo phiên tuỳ biến: banner "đang bị điều khiển" + nút ngắt (ràng buộc 7, giải luôn V7) | giao diện + bảo mật |
| P5 | Gỡ/ẩn tính năng không dùng (address book, marketplace, settings nhạy cảm) | chức năng |
| P6 | Việt hoá giao diện client | giao diện |
| P7 | **Tích hợp luồng đăng nhập LTT vào client** — auto-connect qua vé LTT thay vì gõ ID+mật khẩu tay | **chức năng (sâu nhất)** |
| P8 | Móc audit/telemetry về LTT | chức năng |

**Một quyết định về ĐỘ SÂU còn để mở (ảnh hưởng khối lượng P7):**

- **Nhẹ:** rebrand + gỡ UI, nhưng giữ cơ chế ID+mật khẩu của RustDesk (wiring W1-W5
  làm cầu). Khách vẫn thấy "ID/mật khẩu" ở đâu đó.
- **Sâu:** sửa client để **tự kết nối qua vé LTT** — khách chỉ bấm "điều khiển"
  trong LTT, không bao giờ thấy ID/mật khẩu RustDesk. Sản phẩm liền mạch hơn
  nhiều, nhưng P7 nặng hơn hẳn.

Chọn Rổ 2 để cá nhân hóa mạnh thì đường **Sâu** mới xứng, nhưng đó là quyết định
riêng cần chốt trước khi làm P7.

### Danh sách hạng mục CÒN LẠI — theo thứ tự triển khai

**A. Wiring — biến vé thành kết nối — ✅ XONG 2026-08-20:**
1. W1 — cột `engine_id` + `engine_secret` (mã hoá at-rest) vào `NexusSession` + migration
2. W2 — `sessions.py`: agent báo engine, controller lấy kết nối (kiểm chủ, hết hạn)
3. W3 — `server/nexus/routes.py`: agent báo lúc redeem; route khách lấy chi tiết
4. W4 — `client.py`: nhịp tim → `engine.xoay_mat_khau`+`lay_id` → báo (cần Q99 admin)
5. W5 — `apps/nexus`: nút điều khiển + hiện kết nối; kiểm trình duyệt thật

**B. Fork RustDesk + tuân AGPL:**
6. Fork repo tại commit đã ghim; cấu hình server **nhúng sẵn**; mọi sửa là **patch theo dõi được**
7. Pipeline build fork + **công bố mã nguồn** (nghĩa vụ AGPL) + source-offer; `THIRD_PARTY_NOTICES`

**P. Cá nhân hóa UI/UX + chức năng theo LTT (mảng 6 — song song B):**
8. P1-P3 branding + hệ thiết kế LTT trong Flutter + restyle cửa sổ điều khiển
9. P4 chỉ báo phiên tuỳ biến (giải V7); P5 gỡ tính năng thừa; P6 việt hoá
10. **Chốt độ sâu P7 (nhẹ/sâu)**, rồi tích hợp luồng đăng nhập LTT + P8 telemetry

**C. Phát hành endpoint:**
11. Sinh khoá phát hành thật + ghim `RELEASE_PUBLIC_KEY`
12. Bản cài gộp (fork + Agent, một lần nâng quyền — Q99); build+ký trên Windows sạch

**D. Thanh toán (Q98) — ✅ CƠ CHẾ XONG 2026-08-20 (còn 3 tham số D12):**
13. Chốt 3 tham số (giá/máy/tháng, chu kỳ, ân hạn)
14. Cơ chế trừ credit theo máy/tháng; `cap_ve` từ chối khi hết credit; nút nạp mở trình duyệt

**E. Vận hành & thương mại:**
15. Migrate bảng Nexus lên prod; bật `LTT_NEXUS` (sau 5 điều kiện N5)
16. Đo tỉ lệ P2P/relay (cần 2 mạng thật) + **siết relay** (đang mở cho cả Internet)
17. **Legal review** (trước bán) — 6 câu ở `03_OSS_LICENSE.md` §7
18. Giá, điều khoản, mở bán

### Đường tới hai cột mốc

- **"Chạy được nội bộ" (điều khiển thật một máy):** cần A (W1-W5) + C11/C12 + migrate.
  Có thể chạy với client **chưa cá nhân hóa** (còn giao diện RustDesk) — mảng 6
  không chặn cột mốc này, chỉ chặn "sản phẩm mang mặt LTT".
- **"Mở bán":** thêm B (fork công bố mã) + **mảng 6 (cá nhân hóa)** + D (thanh
  toán) + E17 (legal) + E16 (siết relay). Cá nhân hóa là điều kiện của *mở bán*,
  không phải của *chạy thử*.
