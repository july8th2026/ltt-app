# N1.1 — dựng điểm hẹn + relay, và ĐO chứ không đoán

> Chuẩn bị 2026-08-17 theo Q94. **Chưa chạy** — chờ VPS.
>
> File này tồn tại để lúc có máy thì làm theo, không phải dò lại từ đầu. Nó
> cũng ghi sẵn **những con số phải đo**, vì một POC không đo gì thì chỉ chứng
> minh được "có chạy", mà "có chạy" không phải câu hỏi đang cần trả lời.

---

## 0. Vì sao việc này KHÔNG phải chờ legal review

`03_OSS_LICENSE.md` §3: §13 của AGPL-3.0 chỉ kích hoạt **khi bạn sửa chương
trình**. Ở đây ta chạy `rustdesk-server` **nguyên bản**, không sửa một dòng, và
không phân phối binary cho ai. Nghĩa vụ duy nhất còn lại là `THIRD_PARTY_NOTICES`
khi nào có phân phối.

Cái **phải** chờ luật sư là *client mang thương hiệu LTT* — vì build một client
có sẵn địa chỉ server và logo **là** sửa đổi. Nên N1.1 làm được ngay, N3.2 thì
không.

**Ràng buộc bắt buộc:** nếu vì bất kỳ lý do gì phải sửa `rustdesk-server`, dừng
lại và ghi vào Q94 trước khi sửa. Một patch "cho tiện" ở đây kéo §13 vào cuộc mà
không ai nhận ra.

---

## 1. Máy cần gì

| | |
|---|---|
| IP công khai | **bắt buộc** — đây là toàn bộ lý do phải có máy này |
| RAM | 1 GB đủ cho hbbs + hbbr |
| Băng thông | tính theo mục 4, không đoán |
| Hệ điều hành | Linux (Debian/Ubuntu) — bản chính thức có sẵn |

**Cổng phải mở** (đây là chỗ hay sai nhất, và sai thì triệu chứng là "kết nối
được nhưng chậm khủng khiếp" chứ không phải "không kết nối được"):

| Cổng | Giao thức | Dùng cho |
|---|---|---|
| 21115 | TCP | hbbs — NAT type test |
| 21116 | **TCP + UDP** | hbbs — heartbeat/đăng ký (UDP) và kết nối (TCP) |
| 21117 | TCP | hbbr — **relay** |
| 21118 | TCP | hbbs — hỗ trợ web client |
| 21119 | TCP | hbbr — hỗ trợ web client |

Quên **UDP 21116** là lỗi kinh điển: máy vẫn kết nối được qua relay nên trông
như chạy, nhưng **mọi phiên đều đi vòng qua relay** thay vì P2P — tức là hoá đơn
băng thông gấp nhiều lần mà không ai biết vì sao.

---

## 2. Dựng

Phiên bản chốt: **`rustdesk-server` 1.1.16**, commit `73523b31cfd25d77dee862e6fc9f5e1fb5e485ef`
(`03_OSS_LICENSE.md` §2). Ghim đúng bản này, không dùng `latest` — một POC đo
trên bản A rồi chạy production bản B là một phép đo không dùng được.

Sau khi hbbs chạy lần đầu nó sinh cặp khoá; **khoá công khai** là thứ client cần
để xác thực server. Cất nó cùng chỗ với các bí mật khác (Q28), **không** commit.

---

## 3. Sức khoẻ: kiểm bằng đo, không bằng nhìn log

Ba câu hỏi, và cả ba đều phải trả lời bằng số:

1. **Cổng có thật sự mở không** — kiểm **từ ngoài Internet**, không phải từ chính
   máy đó. `ss -lntup` trên máy chỉ nói tiến trình đang nghe, không nói firewall
   của nhà cung cấp có chặn hay không.
2. **UDP 21116 có thông không** — kiểm riêng, vì TCP thông không kéo theo UDP
   thông, và đây đúng là cổng bị quên.
3. **Hai máy có thấy nhau không** — hai thiết bị ở hai mạng khác nhau.

---

## 4. Số phải đo — đây mới là mục đích của N1.1

Đo trên **ít nhất hai cặp mạng thật khác nhau** (ví dụ: hai nhà khác ISP; một
nhà + một 4G). Một cặp không đủ để nói gì về tỉ lệ.

| Số | Vì sao cần | Ghi vào đâu |
|---|---|---|
| **Tỉ lệ P2P trực tiếp / phải qua relay** | Quyết định toàn bộ chi phí băng thông. Đoán sai con số này là đoán sai hoá đơn | `EXECUTION_PLAN.md` R3 |
| **GB/giờ khi đi qua relay** | Nhân với tỉ lệ trên ra chi phí thật/tháng | R3 |
| **Độ trễ khi P2P vs khi relay** | Quyết định trải nghiệm có dùng được không | N1.2 |
| **Mã hoá đầu-cuối: relay thấy được gì** | T10 trong threat model — **phải kiểm chứ không suy đoán** | `04_THREAT_MODEL.md` T10 |

Số cuối quan trọng hơn vẻ ngoài. `04_THREAT_MODEL.md` đã ghi T10 là "cần **xác
minh** RustDesk làm điều này thế nào ở phiên bản đang chốt, chứ không suy đoán".
Nếu relay nhìn thấy nội dung màn hình thì LTT trở thành một bên có thể xem màn
hình của khách, và điều đó phải được nói ra với khách chứ không giấu đi.

Cách đo: bắt gói tại relay trong một phiên thật và xác nhận không đọc được nội
dung. Nếu đọc được — dừng, ghi vào threat model, và đó thành một quyết định sản
phẩm chứ không phải một chi tiết kỹ thuật.

---

## 5. Sau khi đo xong

1. Điền bốn con số vào R3 và T10; **thay** ước lượng bằng số đo, không để cạnh nhau.
2. Nếu tỉ lệ relay cao hơn nhiều so với 10–30% thường thấy thì xem lại cổng UDP
   trước khi kết luận về chi phí — đó là nguyên nhân phổ biến hơn nhiều so với
   "mạng khách xấu".
3. Chỉ khi đó mới bàn tới N1.2 (chất lượng phiên tới máy Windows thật).

---

## 6. Việc KHÔNG làm ở bước này

- **Không** build client mang thương hiệu LTT — đó là N3.2 và nó chờ luật sư.
- **Không** cho khách nào dùng. Q94: agent chưa ký chỉ chạy nội bộ.
- **Không** sửa `rustdesk-server`. Xem mục 0.
