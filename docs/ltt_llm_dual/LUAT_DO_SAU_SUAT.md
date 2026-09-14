# Luật đo "sáu suất + hàng chờ" — 14/09/2026

> Chương trình mẹ: `docs/VAN_HANH_THAT.md`. Bộ đo chuẩn: `BO_DO_CHUAN.md`.
>
> Tệp này **chỉ** đặt luật cho một câu hỏi: *ba suất mỗi card, sáu suất hai
> card, và job thứ bảy có vào đúng chỗ khi một suất nhả ra không.*

---

## 1. Ba mệnh đề phải chứng minh, và mỗi cái phải CÓ THỂ SAI

| # | Mệnh đề | Đỏ khi |
|---|---|---|
| **M1** | Một lô **job thuần** đạt trần nền = **2** suất/card | đỉnh một tài nguyên ≠ 2 |
| **M2** | Hai card chạy **song song**, tổng **4** | đỉnh tổng < 4, hoặc chỉ một `resource` xuất hiện |
| **M3** | Job thứ N **chờ**, và khi một suất nhả thì nó **vào ngay** | có job `queued` trong khi còn chỗ dưới trần |

### 🔴 M1/M2 ĐÃ SỬA 14/09 — hệ ĐÚNG, kỳ vọng SAI

Bản đầu đòi **3 suất/card, tổng 6**. Đo được: **đúng 2 mỗi card, 4 tổng, 5 job
xếp hàng**, ổn định suốt lượt, trên **cả hai** card.

Nguyên nhân là một luật **cố ý** — `luat_nhan.py:170`:

```
if sum(1 for g in giu if g.lop != TUONG_TAC) >= tran_nen(so_slot)
tran_nen(3) = 3 − 1 = 2
```

Cửa **job** gán `lop=NEN` (`job_runner.py:373`); cửa **sync/stream** gán
`lop=TUONG_TAC` (`luong.py:368`). Luật **chừa một suất mỗi card** cho người
đang ngồi đợi, để một lô job nền không bao giờ làm nghẹt cả card.

⇒ Trần đúng của một lô job thuần là **2/card = 4**. **Sáu suất chỉ đạt được khi
  có CẢ HAI loại lưu lượng**: 2 nền + 1 tương tác mỗi card.

⛔ Đòi 3/card ở cửa job là đòi hệ **phá chính luật nó đang thi hành** — và
   "sửa" cho nó đạt là gỡ mất lớp bảo vệ người dùng tương tác.

⛔ **M3 là mệnh đề khó nhất và dễ giả nhất.** "Có job chạy sau đó" **không**
chứng minh gì — chúng có thể chạy vì lô trước đã xong sạch, chứ không phải vì
bàn giao. Bằng chứng thật là **mốc thời gian**: giây lease tụt 6→5, và giây một
job `queued` chuyển sang `running`. Hai mốc ấy phải **gần nhau**.

---

## 2. Job phải DÀI — và đây là ràng buộc, không phải sở thích

Đo 14/09: sáu job `max_tokens=1500` cho đỉnh **3**, không phải 6 — vì chúng kết
thúc **lệch nhau**, không bao giờ chồng đủ. Hàng đợi chỉ quan sát được khi nó
**kịp hình thành**.

⇒ Mỗi job phải dài hơn **tổng thời gian nộp cả lô** ít nhất vài lần. Primitive
đã đo: `ltt-3.8` sinh 8.000 token trong **106 giây**.

---

## 3. Đo CẢ HAI MÁY, cùng lúc, và chúng trả lời hai câu khác nhau

| máy | nguồn | trả lời câu |
|---|---|---|
| **A** | `execution_leases`, `jobs.status` | ta **cấp phát** thế nào |
| **B** | `llamacpp:requests_processing`, `requests_deferred`, `nvidia-smi` | máy B **thật sự làm** gì |

🔑 **Chỉ đo một bên là đo một nửa.** Ngày 14/09 tôi đã kết luận sai hai lần vì
chỉ nhìn máy A: lần đầu đổ cho hồ worker, lần sau bảo `worker-1` chết (nó là
tiến trình cha). Nguyên nhân thật — `reasoning_effort=none` — chỉ lộ ra khi hỏi
máy B.

⭐ **`requests_deferred` là đối chứng.** Nếu máy B **không** hoãn lượt nào mà
máy A vẫn xếp hàng ⇒ hàng đợi là của **máy A**, đúng thiết kế. Nếu máy B hoãn
⇒ ta đang gửi quá sức nó, và con số của máy A vô nghĩa.

---

## 4. Nền phải SẠCH, và phải chứng minh là sạch

Bắt đầu khi `execution_leases` **rỗng** và cả hai `requests_processing` = **0**.

⛔ Nền bẩn thì mọi số sau đó thuộc về một kịch bản **khác**, và nó **không tự
khai** điều đó. Đo được 13/09: một lượt đo bão hoà chạy trúng cửa sổ deploy của
phiên khác, cả sáu job chết cùng một khắc, và kết quả trông **y hệt** một phát
hiện lớn.

---

## 5. Bốn ngăn — phân loại TRƯỚC khi sửa

| ngăn | xử |
|---|---|
| lỗi hệ thống | ghi sổ, gom sửa một lượt |
| lỗi bộ đo | sửa ngay, chạy lại đúng kịch bản ấy |
| nhiễu | chạy lại, **không diễn giải** |
| hệ đúng, kỳ vọng sai | sửa **kỳ vọng**, ghi rõ vì sao |

---

## 6. Điều kiện để nói "PASS"

Cả ba mệnh đề đạt, **trên một lượt nền sạch**, với:

- đỉnh mỗi `resource` = **3**;
- đỉnh tổng = **6**, và có ít nhất một mẫu thấy **cả hai** `resource` cùng lúc;
- tồn tại ít nhất một **cặp bàn giao**: lease tụt rồi một job `queued` vào chạy
  trong vòng **15 giây**;
- `requests_deferred` = **0** suốt lượt ở cả hai cổng;
- **0** job `failed`, **0** mã `429`.

⛔ Thiếu **một** dòng ⇒ **chưa pass**. Không có "pass một phần".

⚠️ Và một lượt pass **không** chứng minh hệ luôn đúng — nó chứng minh hệ đúng
**ở lượt ấy, ở tải ấy**. Ghi lại tải đã dùng, đừng ghi "hệ ổn".
