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
| **D2** | Hạ tầng relay | **Chưa quyết — làm phần không cần relay trước** | N2 chạy ngay; N1/N3 vẫn chặn. Phải chốt trước khi có phiên điều khiển thật đầu tiên |
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
N3  Sản phẩm endpoint Windows (cần D1)
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

### N2.1 — `devices` + enrollment

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

### N2.2 — Presence

Nhịp tim từ thiết bị, ghi trạng thái online/offline. **Không** dùng bảng `jobs`.
Vòng dọn presence quá hạn phải nằm sau `SingletonLease` (`platform_core/leases.py`)
— worker chạy nhiều tiến trình, đây đúng là lỗi H36 đã sửa một lần rồi.

### N2.3 — Session broker

Server cấp **vé ngắn hạn** cho một phiên cụ thể: ai điều khiển, máy nào, hết hạn
lúc nào, quyền gì (xem-only hay điều khiển). Đây là chỗ duy nhất uỷ quyền được
quyết định, và nó phải ở server (invariant #3). Thu hồi = vé chết ngay, không
chờ hết hạn.

### N2.4 — Kiểm toán

Mỗi phiên ghi một bản ghi bất biến: ai, máy nào, bắt đầu/kết thúc, từ IP nào,
kết thúc vì lý do gì. Đây cũng là cách thoả invariant #4 của pack (không có
backdoor bí mật): **admin không được có đường vào máy khách không để lại dấu**.

### N2.5 — `apps/nexus`

Danh sách máy, trạng thái online, nút ghép máy mới, nút thu hồi, lịch sử phiên.
Dùng LTT Carbon Red + hợp đồng bề rộng trang (Q52/Q61). Kiểm bằng trình duyệt
thật trên URL công khai, không chỉ loopback (`CLAUDE.md` mục 5b).

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
| R1 | AGPL lây sang phần độc quyền của LTT | **Cao** | D1 + luật sư trước khi viết code tích hợp engine. **Sắc hơn sau prompt 03:** §13 có điều kiện *"if you modify"* — mà build client mang thương hiệu LTT + trỏ về hạ tầng LTT **chính là** modify. Đường "dùng nguyên bản nên không sao" và đường "có sản phẩm riêng" gần như loại trừ nhau. Sáu câu hỏi cho luật sư ở `03_OSS_LICENSE.md` §7 |
| R2 | Không có IP công khai → sản phẩm không chạy được ngoài LAN | **Cao** | D2 trước N1 |
| R3 | Chi phí băng thông relay vượt dự tính | Trung bình | N1.1 phải **đo** tỉ lệ direct vs relay và GB/giờ thật, không ước lượng |
| R4 | Một sản phẩm điều khiển máy từ xa bị lạm dụng để chiếm quyền máy nạn nhân | **Cao** | `04_THREAT_MODEL.md` T1. **Không đóng được bằng kỹ thuật** — mọi bước của kẻ lừa đảo đều "hợp lệ", hệ thống làm đúng thứ nó được thiết kế. Giảm bằng: mã ghép sinh **trên máy đích**, hạn rất ngắn, cảnh báo bằng ngôn ngữ hậu quả, chỉ báo phiên không tắt được, và email cho chủ tài khoản **mỗi lần ghép**. Phần còn lại là rủi ro **chấp nhận có ý thức**, phải ghi vào Q93 chứ không để im |
| R5 | Chứng thư ký mã chưa có lúc cần phát hành | Trung bình | Mua sớm, ngay khi D1 xong |
| R6 | App Store từ chối app điều khiển từ xa | Trung bình | Đọc guidelines **trước** khi viết mobile, không phải sau |
| R7 | Nexus kéo chậm Public API đang treo | Trung bình | Mục 1 |
| R8 | Nhánh làm việc: Nexus commit lẫn vào `public-api-v2` | Thấp | Nhánh riêng `nexus-foundation` từ `master` |
| R9 | **Test chốt được *script có lệnh*, không chốt được *lệnh đã chạy trên máy thật*** | **Cao** | Bài học 2026-08-17: `test_scheduled_backup_tightens_acl` xanh suốt nhiều tháng trong khi `D:\LTTBackups` thực tế mở cho `Authenticated Users`. Mọi hạng mục Nexus có phần "cấu hình trên máy" (cổng relay, chứng thư ký, quyền dịch vụ) phải có **một phép đo trên máy thật**, không chỉ một assertion trên mã nguồn |

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
