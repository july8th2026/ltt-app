# Spike P6 — chặn egress cho piece Node.js tuỳ ý

Máy: Node v24.17.0 (`node --version`), npm 11.13.0. Bàn thử: `spike/egress/`
(`catcher-server.js` bắt request cục bộ trên `127.0.0.1:18199` (IPv4) và
`[::1]:18299` (IPv6); `piece-https.js`/`piece-axios.js`/`piece-fetch.js` giả lập
piece gọi ra bằng `require('https')`, `axios`, `fetch()`; `run-all.js` chạy hết
to hợp và in bảng). Chạy: `node run-all.js` trong `spike/egress/`.

## Nguồn tra trước khi đo

- `node --help` (bản thật trên máy, Node 24.17.0): permission model chỉ có
  `--allow-fs-read`, `--allow-fs-write`, `--allow-child-process`, `--allow-worker`,
  `--allow-wasi` — **không có `--allow-net`/permission mạng nào**. Xác nhận thêm
  bằng đo thật: `node --permission --allow-fs-read="*" --allow-child-process
  piece-https.js` vẫn REACHED (status 200) tới đích cục bộ — permission model
  không chặn mạng ở bản Node đang dùng.
- GitHub `nodejs/node` issue #62424 (đóng) — đề xuất thêm `--allow-env`, cho thấy
  permission model vẫn đang mở rộng theo từng tài nguyên riêng lẻ, mạng chưa có.
- GitHub `activepieces/activepieces` issue #11547 (mở, 2026-03-04): chính đội
  activepieces xác nhận sandbox trong-tiến-trình (V8 isolate/`isolated-vm`) và cả
  namespace kernel là **không đủ** cho code không tin cậy có quyền mạng — họ đề
  xuất chuyển sang cô lập phần cứng (QEMU microVM) với "network domain filtering"
  ở ngoài tiến trình. Issue trích cả CVE-2025-68668 (n8n, Pyodide sandbox escape,
  CVSS 9.9) làm minh chứng sandbox trong-tiến-trình từng bị vượt qua trên thực tế.
  `search_code` trên `nodejs/undici`, `activepieces`, `n8n-io/n8n` cho log chặn
  dạng preload cụ thể không ra kết quả — không có mã tham chiếu công khai để trích,
  kết luận dưới đây dựa trên đo thật.

## Bảng kết quả (rút gọn — đủ để trả lời rủi ro chặn)

REACHED = lọt ra ngoài (không bị chặn). CHẶN = bị chặn đúng như preload định làm.
`z_none_doi_chung` = đối chứng không vá gì — REACHED ở mọi hàng (trừ 1 dòng nêu dưới),
chứng minh bàn thử thật sự gọi ra được mạng và có đường tới `example.com` thật.

| Phương án preload | require('https') | axios | fetch() |
|---|---|---|---|
| (a) undici global dispatcher (giả thuyết spec) | **REACHED — không chặn** (mọi target kể cả IP/IPv6) | **REACHED — không chặn** | CHẶN |
| (b1) chỉ vá `dns.lookup` | REACHED khi gọi thẳng bằng IP/IPv6 literal — **lọt** | REACHED khi gọi bằng IP — **lọt** | REACHED khi gọi bằng IP — **lọt** |
| (b2) chỉ vá `net.Socket.prototype.connect` | CHẶN mọi target | CHẶN mọi target | CHẶN mọi target |
| (b3) vá cả hai (khuyến nghị của plan) | CHẶN mọi target | CHẶN mọi target | CHẶN mọi target |
| Đối chứng — không vá gì | REACHED mọi target | REACHED (trừ raw-IP ra ngoài, xem dưới) | REACHED mọi target |

Chi tiết đầy đủ 75 tổ hợp (5 preload × 3 piece × 5 target: IP nội bộ, hostname nội
bộ, IPv6 nội bộ, hostname ngoài `example.com`, IP thật của `example.com`) nằm ở
`spike/egress/results.json`.

**Đối chứng "lọt" chứng minh phép đo có ý nghĩa:** đối chứng không vá REACHED ở
23/25 hàng (2 hàng axios→IP trần lỗi `ERR_BAD_REQUEST` — do server đích không nhận
`GET` thiếu Host header hợp lệ khi gọi thẳng IP, xảy ra **giống hệt** ở cả preload
(a) và đối chứng, tức là lỗi tầng ứng dụng của `example.com`/axios, không liên
quan cơ chế chặn).

## Kết luận

1. **Đúng như rủi ro plan nêu bằng chữ đỏ: undici global dispatcher (giả thuyết
   trong spec §11.2) hoàn toàn KHÔNG chặn `require('http'/'https')`** — tức
   không chặn axios, `@slack/web-api`. Nó chỉ chặn `fetch()`/client undici thật.
   Spec §11.2 sai, phải sửa trước khi mở khách.
2. **Vá riêng `dns.lookup` không đủ** — bất kỳ piece nào gọi thẳng bằng địa chỉ
   IP (v4 hoặc v6, kể cả literal không qua DNS) đều lọt qua, vì Node bỏ qua
   `dns.lookup` khi `net.isIP()` nhận ra chuỗi là IP hợp lệ.
3. **Vá `net.Socket.prototype.connect` một mình đã đủ chặn 100% tổ hợp đo được**
   (kể cả `fetch()`, kể cả IP trần, kể cả IPv6) — vì mọi đường (`http`/`https`/
   `tls`/`net`/undici nội bộ của Node) cuối cùng đều đi qua `net.Socket.connect`.
   Vá thêm `dns.lookup` (phương án b3, đúng như plan viết) không hại gì và cho
   thông điệp lỗi sớm/rõ hơn ở bước phân giải tên, nhưng về mặt CHẶN là dư thừa so
   với b2 — khuyến nghị vẫn giữ cả hai như plan (phòng thủ theo lớp, chi phí thấp)
   với `net.Socket.prototype.connect` là lớp **bắt buộc**, `dns.lookup` là lớp phụ.
4. **Permission model của Node (`--permission`) không phải lựa chọn** ở bản Node
   đang dùng (v24.17.0) — chưa có quyền mạng, đo thật xác nhận request vẫn lọt.

**Khuyến nghị:** preload vá `net.Socket.prototype.connect` (bắt buộc) + `dns.lookup`
(phụ, thông điệp lỗi sớm) trước khi piece bundle chạy, đúng hướng plan §4 P6 đã
ghi — chỉ khác là xác nhận **b2 là lớp chặn thật sự**, b1 chỉ là hàng rào phụ chứ
không phải điều kiện đủ như cách viết "phải vá cả hai" của plan dễ khiến người đọc
tưởng hai lớp ngang hàng.

## Chỗ còn hở (chưa đo, hoặc đo thấy nhưng chưa vá)

- **UDP/DNS-over-HTTPS/QUIC**: bàn thử chỉ đo `net.Socket` (TCP). Một piece dùng
  `dgram` (UDP) hoặc HTTP/3 (QUIC, qua module native không đi qua `net.Socket`)
  sẽ không bị lớp vá này chặn — chưa đo.
- **Native addon / N-API mở socket bằng syscall trực tiếp** (không qua `net`/`dns`
  của Node) sẽ không bị patch trong-tiến-trình nào ở đây chặn — đúng như
  activepieces #11547 cảnh báo, patch trong-tiến-trình không phải biên cô lập an
  toàn cho code hoàn toàn không tin cậy (chỉ hợp cho piece "đáng tin nhưng lỡ gọi
  sai domain", không hợp cho piece cố tình chống lại sandbox).
  Không có `Socket.prototype.connect` gốc để bọc — tăng nguy cơ đóng gói lại từ
  module cache trước khi preload chạy.
- **Chưa đo `worker_threads`/`child_process` con** — nếu piece tự spawn tiến trình
  con hoặc worker mới không nạp lại `-r` preload, egress của tiến trình con không
  bị chặn (cần `--require` áp cho cả worker, hoặc chặn `child_process`/`Worker`
  hẳn bằng permission model — đã có `--allow-child-process`).

---

## 🔴 ĐO BỔ SUNG (điều phối, 24/09): lỗ `child_process` — **đã đo, và nó thủng**

Báo cáo trên xếp `child_process` vào *"chưa vá / chưa đo"*. Nhưng đây là lỗ **quyết định kiến
trúc**, nên không được để ở dạng chưa đo. Kết quả:

```
$ node -r ./preload-socket-only.js -e "require('https').get('https://example.com/'…)"
PARENT_BLOCKED EGRESS_BLOCKED:net.Socket.connect:example.com

$ node -r ./preload-socket-only.js ./piece-child-process.js
CHILD_REACHED 200
```

Cha bị chặn. Con **ra Internet, HTTP 200**. Lý do cơ học: `-r <preload>` là cờ dòng lệnh của
**tiến trình đó**, nó không đi theo `spawn`. Một piece chỉ cần

```js
require('child_process').spawnSync(process.execPath, ['-e', "…require('https')…"])
```

là đi vòng qua **toàn bộ** lớp vá trong tiến trình — kể cả phương án b2/b3 vừa đo là "chặn 100 %".

### Hệ quả: đổi vai của lớp vá, không chỉ đổi phương án

⛔ **Vá trong tiến trình KHÔNG thể là RANH GIỚI an ninh cho mã không tin cậy.** Nó là **lớp phòng
thủ theo chiều sâu** — chặn piece *viết ẩu* gọi nhầm nội mạng, không chặn piece *cố ý*. Đây đúng
điều đội Activepieces nói trong `activepieces#11547` (dẫn CVE-2025-68668 của n8n): sandbox
trong-tiến-trình không đủ cho mã không tin cậy có quyền mạng.

⚠️ Và **Job Object (`win32job`, §11.2) không lấp lỗ này**: nó giới hạn CPU/bộ nhớ/cây tiến trình,
**không** lọc socket. Đưa nó vào chỗ này là nhầm vai.

### Việc phải làm trước khi mở khách — chưa làm, ⛔ chưa được đoán

Ranh giới thật phải ở **mức hệ điều hành**. Ba hướng cần **đo** (⛔ không chọn bằng suy luận):
tài khoản Windows riêng cho runner + luật tường lửa outbound theo **SID** · AppContainer +
network capability · namespace mạng (container/WSL2). Mỗi hướng phải trả lời đúng phép thử
`piece-child-process.js` ở trên, không phải trả lời trên giấy.

**Tái chạy:** `node -r ./preload-socket-only.js ./piece-child-process.js` trong `spike/egress/`.

