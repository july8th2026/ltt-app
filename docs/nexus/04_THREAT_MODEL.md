# LTT NEXUS — Threat model và ranh giới tin cậy

> Prompt 04 của pack. Lập 2026-08-17, sau `03_OSS_LICENSE.md`.
>
> File này là **đầu vào trực tiếp của Q93**. Mọi điều khoản trong Q93 phải truy
> ngược được về một mối đe doạ ở đây; ngược lại, mỗi mối đe doạ nghiêm trọng
> phải có một điều khoản đối ứng, hoặc một dòng ghi rõ **vì sao chấp nhận**.

---

## 0. Vì sao sản phẩm này khác mọi app đã có

15 app hiện tại đều cùng một hình dạng: khách bấm nút → job chạy **trên máy
LTT** → trả file. Thiệt hại tối đa khi một app hỏng là mất tiền của một khách và
mất uy tín.

Nexus khác về **loại**: sản phẩm thành công nghĩa là **có người đang gõ phím và
di chuột trên máy tính của người khác**. Một lỗi uỷ quyền ở đây không làm mất một
job — nó giao toàn bộ máy của khách, kèm mọi thứ họ đã đăng nhập, cho người
khác.

Hệ quả cho cách đọc file này: những mối đe doạ dưới đây **không** được xếp hạng
theo xác suất kỹ thuật, mà theo **thiệt hại không thể hoàn tác**.

---

## 1. Tài sản cần bảo vệ

| # | Tài sản | Mất nó nghĩa là gì |
|---|---|---|
| A1 | **Quyền điều khiển một máy Windows của khách** | Kẻ tấn công có mọi thứ trên máy đó: mail đang đăng nhập, ngân hàng, tài liệu, và cả bàn đạp vào mạng nội bộ của khách |
| A2 | Khoá riêng của thiết bị | Giả mạo thiết bị đó vĩnh viễn cho tới khi bị thu hồi |
| A3 | Vé phiên (session ticket) | Một phiên trái phép trong thời hạn vé |
| A4 | Tài khoản LTT của khách | Ghép thêm thiết bị, thu hồi thiết bị thật, xem lịch sử |
| A5 | Tính toàn vẹn của nhật ký kiểm toán | Mất khả năng trả lời "ai đã vào máy tôi, lúc nào" — câu hỏi duy nhất quan trọng sau sự cố |
| A6 | Băng thông relay | Bị dùng làm đường hầm miễn phí cho kẻ khác |
| A7 | Nội dung màn hình đang truyền | Rò rỉ dữ liệu khách ngay cả khi phiên là hợp pháp |

---

## 2. Ranh giới tin cậy

```
 [1] trình duyệt / mobile ──HTTPS/Cloudflare──> control plane (app.lttstudios.com)
                                                     │
 [2] control plane ──request có chữ ký──> LTT Nexus Agent (máy khách)
                                                     │
 [3] Agent ──IPC cục bộ──> engine RustDesk (AGPL, tiến trình riêng)
                                                     │
 [4] endpoint ──trực tiếp hoặc qua relay──> endpoint     ◄── DATA PLANE
                                                     │
 [5] nhân viên LTT ──> mọi thứ ở trên                    ◄── nội gián
```

Bốn điều rút ra, và cả bốn đều thành điều khoản Q93:

- **[4] không bao giờ được đi qua [1].** Ràng buộc bất biến #5 của pack, và
  `CURRENT_STATE_AUDIT.md` §4.1 đã chứng minh nó **cũng bất khả thi về kỹ thuật**
  (trần 100 giây + ToS của Cloudflare). Hai lý do độc lập cùng chỉ một hướng.
- **[3] là ranh giới giấy phép lẫn ranh giới bảo mật.** Agent không chạm luồng
  màn hình; engine không quyết định uỷ quyền. Xem `03_OSS_LICENSE.md` §5.
- **[2] không được tin client.** Ràng buộc bất biến #3.
- **[5] phải để lại dấu.** Ràng buộc bất biến #4.

---

## 3. Mối đe doạ

Xếp theo thiệt hại không thể hoàn tác, không theo xác suất.

### T1 — Kẻ tấn công ghép máy NẠN NHÂN vào tài khoản của CHÍNH NÓ ⚠️ nghiêm trọng nhất

**Kịch bản thật, không giả định:** gọi điện cho nạn nhân xưng là hỗ trợ kỹ thuật,
hướng dẫn cài "phần mềm hỗ trợ", rồi bảo họ **đọc mã ghép** qua điện thoại. Kẻ
tấn công nhập mã ở phía nó. Xong. Đây là kiểu lừa đảo **phổ biến nhất** với mọi
sản phẩm điều khiển từ xa đang tồn tại, và RustDesk cũng dính.

Điều nguy hiểm: **mọi bước đều "hợp lệ"**. Không có chữ ký sai, không có khoá bị
lộ, không có lỗ hổng nào bị khai thác. Hệ thống làm đúng điều nó được thiết kế.

Vì vậy **không có biện pháp kỹ thuật nào đóng hẳn được T1**. Chỉ giảm được:

- mã ghép **sinh trên máy được điều khiển** và có hạn **rất ngắn**;
- màn hình ghép nói bằng ngôn ngữ hậu quả, không phải ngôn ngữ kỹ thuật: *"Người
  có mã này sẽ điều khiển được máy tính của bạn và thấy mọi thứ trên màn hình.
  Chỉ đưa mã cho người bạn tự tìm đến, không bao giờ cho người gọi đến bạn."*;
- **chỉ báo phiên không tắt được** trong suốt phiên, kèm nút ngắt luôn ở đó;
- thời gian chờ trước phiên đầu tiên của một thiết bị mới ghép;
- email cho chủ tài khoản **mỗi lần** một thiết bị được ghép.

Chấp nhận rủi ro còn lại: **có**, và phải ghi rõ trong Q93 rằng đây là rủi ro
được chấp nhận có ý thức chứ không phải chỗ bị bỏ quên.

### T2 — Vé phiên bị đánh cắp hoặc dùng lại

Giảm: vé **dùng một lần**, hạn tính bằng phút, buộc chặt vào (người điều khiển,
thiết bị đích, quyền, thời điểm), thu hồi được **ngay** ở phía server, và vé phải
được engine kiểm chứ không chỉ được control plane cấp.

### T3 — Khoá riêng thiết bị bị lấy khỏi máy đã bị chiếm

Giảm: khoá sinh **trên máy** và không bao giờ rời máy (invariant #2), cất bằng cơ
chế của hệ điều hành (DPAPI/TPM), thu hồi theo **từng thiết bị**.

Nói thẳng: **một máy đã bị chiếm hoàn toàn thì đã mất rồi.** Mục tiêu ở đây chỉ
là hạn chế thiệt hại lan sang thiết bị khác của cùng tài khoản.

### T4 — Nội gián / admin LTT vào máy khách ⚠️

Ràng buộc bất biến #4: **không tạo backdoor bí mật.**

Giảm: admin **thu hồi và vô hiệu** được, nhưng **không cấp được vé phiên** cho
thiết bị mình không sở hữu mà không để lại bản ghi bất biến **chủ thiết bị đọc
được**. Nếu sau này cần đường hỗ trợ có phép, nó phải là *khách bật, có hạn, ghi
nhật ký* — không phải một quyền âm thầm.

Đây là chỗ dễ nhất để "tiện tay" phá vỡ, và cũng là chỗ mất niềm tin nhanh nhất.

### T5 — Relay bị lạm dụng làm đường hầm miễn phí

Giảm: relay **chỉ nhận** phiên có vé hợp lệ do broker cấp; hạn ngạch theo tài
khoản; đo lưu lượng theo phiên.

### T6 — Luồng dữ liệu trôi dạt vào control plane

Không phải tấn công mà là **trôi dạt kiến trúc**: một hôm ai đó thêm "proxy tạm
qua web cho tiện". Giảm bằng test chốt ở tầng nền tảng, không bằng lời nhắc.

### T7 — Cập nhật độc hại

Ràng buộc bất biến #7. Agent chạy quyền cao trên máy khách → đường cập nhật là
đường leo thang đặc quyền hoàn hảo. Giảm: **ký mã**, xác minh chữ ký **trước** khi
thực thi, không tự tải từ nguồn không xác thực. Cần mua chứng thư ký mã (rủi ro
R5 trong `EXECUTION_PLAN.md`).

### T8 — Dò danh sách thiết bị của người khác

Giảm: dùng lại nguyên tư duy `platform_core/public_api/principal.py` — thiết bị
của người khác trả **404**, không bao giờ 403. Ngược lại thì mỗi `device_id`
thành một máy tra cứu.

### T9 — Kẻ tấn công thu hồi thiết bị của nạn nhân (từ chối dịch vụ)

Giảm: thu hồi cũng là hành động **có xác thực và có ghi nhật ký**, và chủ tài
khoản được báo.

### T10 — LTT nhìn thấy nội dung màn hình khách

Giảm: mã hoá đầu-cuối giữa hai endpoint; relay chỉ thấy dữ liệu đã mã hoá. Cần
**xác minh** RustDesk làm điều này thế nào ở phiên bản đang chốt, chứ không suy
đoán — ghi là việc phải làm ở N1.

---

## 4. Điều khoản bắt buộc cho Q93

Rút thẳng từ mục 3. Mỗi dòng truy ngược được về một mối đe doạ:

1. Khoá riêng của thiết bị **không bao giờ rời máy đó**. *(T3, invariant #2)*
2. Uỷ quyền phiên do **server** quyết, bằng vé dùng một lần, hạn ngắn, thu hồi
   được ngay. *(T2, invariant #3)*
3. Luồng điều khiển **không bao giờ** đi qua control plane. *(T6, invariant #5)*
4. Admin **không** cấp được vé cho thiết bị mình không sở hữu; mọi hành động của
   admin để lại bản ghi **chủ thiết bị đọc được**. *(T4, invariant #4)*
5. Mỗi phiên ghi một bản ghi **bất biến**: ai, máy nào, từ đâu, bắt đầu/kết thúc,
   vì sao kết thúc. *(A5)*
6. Máy được điều khiển **luôn** hiện chỉ báo không tắt được, kèm nút ngắt. *(T1)*
7. Ghép thiết bị: mã sinh **trên máy đích**, hạn rất ngắn, cảnh báo bằng ngôn ngữ
   hậu quả, và **email cho chủ tài khoản mỗi lần ghép**. *(T1)*
8. Thiết bị của người khác trả **404**, không bao giờ 403. *(T8)*
9. Cập nhật phải **xác minh chữ ký trước khi thực thi**. *(T7)*
10. Relay chỉ nhận phiên có vé hợp lệ. *(T5)*

---

## 5. Điều được chấp nhận có ý thức

Ghi ra để sau này không ai tưởng là bỏ sót:

- **T1 không đóng được bằng kỹ thuật.** Mọi sản phẩm cùng loại đều sống chung với
  nó. Ta giảm bằng ma sát và bằng chữ, và chấp nhận phần còn lại.
- **Máy đã bị chiếm hoàn toàn thì đã mất.** Không thiết kế để chống lại kẻ đã có
  quyền cao trên chính máy đó.
- **Trần 100 giây chưa đo trên tunnel thật** — nhưng nó không liên quan Nexus, vì
  data plane cố ý không đi qua tunnel.

---

## 6. Trạng thái

**Status: PASS.**

Threat model đã đủ để viết Q93: mười điều khoản ở mục 4 đều truy ngược được về
một mối đe doạ cụ thể, và ba điều chấp nhận ở mục 5 được ghi rõ thay vì để im.

Việc còn phải **kiểm chứng chứ không suy đoán**, chuyển sang N1: RustDesk mã hoá
đầu-cuối như thế nào ở phiên bản `1.4.9`, và relay thực sự thấy được gì.

Bước kế tiếp theo DAG: **N2.0 — viết Q93** (gộp prompt 05/06 của pack).
