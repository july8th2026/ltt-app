# VẬN HÀNH THẬT — chương trình nghiệm thu thường trực

> **Gọi nó thế nào.** Nói *"check plan vận hành thật trong hệ thống LTTSTUDIOSAPP
> và triển khai"* là đủ. Phiên nhận việc đọc tệp này trước, rồi theo §2.
>
> Đây **không** phải một plan dùng một lần. Nó là chương trình chạy lại **sau mỗi
> lần nâng cấp** và **mỗi khi cần audit**.

---

## 1. Nó đo cái gì — và **không** đo cái gì

Giả lập người dùng thật gọi vào **production**, đi xuyên
`API → job → admission → hàng đợi → runtime → GPU → stream → credit → sổ sách`.

⛔ **Nó KHÔNG phải bộ đo hiệu năng.** Đừng chấm nó bằng tok/s. Thứ nó đo là
**hàng đợi, công bằng, và sổ sách** — ba thứ chỉ lộ ra khi hệ **đầy**.

⛔ **Unit test không phải bằng chứng nghiệm thu production.** Ngày 13/09/2026,
**ba** bản vá liên tiếp của sự cố L-08 qua sạch **mọi** phép kiểm trong cây rồi
hoá ra cả ba **chưa từng chạm vào một lượt thật** — chúng gắn vào một cánh cửa
mà lưu lượng không đi qua. Khoảng cách giữa "test xanh" và "chạy đúng" là cả một
lớp lỗi, và chương trình này sinh ra để đứng đúng vào khoảng đó.

⭐ Bằng chứng nó có ích: trong lượt chạy đầu tiên (13/09) nó tìm ra **hai lỗi
   production** mà không unit test nào trong kho bắt được, vì cả hai chỉ hiện khi
   hệ **đang đầy** — xem `ltt_llm_dual/SO_LOI_DO_TAI.md` mục L-11 và L-12.

### Câu hỏi trung tâm

Hệ có **sáu suất** (3 mỗi model, hai card độc lập). Mọi kịch bản xoay quanh ranh
giới ấy: *sáu người đầu chạy — còn người thứ bảy thì sao?*

## 2. Chạy thế nào

```bash
# 0. LUÔN LUÔN trước: có phiên khác đang giữ máy không
py tools\cua_so_yen.py trang-thai

# 1. Nền phải sạch, và production phải RẢNH (xem §5)
# 2. Chạy kịch bản — bộ chạy tự chờ nền sạch trước mỗi cái
py -m tools.nghiem_thu_van_hanh.chay_ma_tran --kich-ban J1,J2,J4,J5
py -m tools.nghiem_thu_van_hanh.chay_ma_tran --kich-ban J7,J12        # công bằng
py -m tools.nghiem_thu_van_hanh.chay_ma_tran --kich-ban J8,J9,J10,J11 # lệch giờ · whale · cắt
```

```bash
# Do rieng do tre NHA SUAT khi khach cat (L-08), co doi chung san
py -m tools.nghiem_thu_van_hanh.do_nha_suat --khoa <tep-khoa> --goc http://127.0.0.1:8100
```

Mỗi kịch bản ghi một `ket_J*.json` gồm từng job (mã, TTFB, thời lượng, số mảnh,
số nhịp báo chờ) và **chuỗi lấy mẫu mỗi giây** (lease theo tài nguyên và theo
tài khoản, số người đang chờ).

⚠️ Bộ chạy **không tự chấm ĐẠT/TRƯỢT**. Nó chỉ sinh số. Đọc số là việc của người,
theo bốn ngăn ở §4 — một bộ đo tự chấm điểm là một bộ đo sẽ tự bảo mình đúng.

## 3. Tài liệu con

| | |
|---|---|
| **Ma trận kịch bản + tham số đo** | `docs/ltt_llm_dual/MA_TRAN_TEST_JOB_DAI.md` |
| **Đường đi một lượt, ai gác chặng nào** | `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` |
| Sổ lỗi của hệ con | `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` |
| Số suất · pool KV · ngưỡng whale | `apps/ltt_llm/ngan_sach.py` |

🔑 **Đừng gõ lại một con số nào vào tệp này.** Đó chính xác là cơ chế đã làm
bảng ở kho này nói sai năm lần, và ngày 13/09 làm ~40 tài liệu khai sai số suất
suốt hai ngày mà không ai biết.

## 4. Đọc kết quả — bốn ngăn

Mỗi phát hiện vào **đúng một** ngăn, **trước** khi sửa bất cứ gì:

| ngăn | xử |
|---|---|
| **lỗi hệ thống** | vào `SO_LOI_DO_TAI.md`, gom lại sửa **một lượt** |
| **lỗi bộ đo** | sửa ngay, chạy lại đúng kịch bản ấy |
| **nhiễu** | chạy lại, **không diễn giải** |
| **hệ đúng, kỳ vọng SAI** | sửa **kỳ vọng**, ghi rõ vì sao |

⭐ Ngăn thứ tư dễ bỏ sót nhất và đã xuất hiện thật: một prompt 195.696 token bị
từ chối, suýt ghi thành *"221K không với tới được"* — trong khi nền tảng khai
**171.458** và từ chối là **đúng**.

## 5. ⛔ Luật phối hợp — đọc trước khi gửi request đầu tiên

**Production là tài nguyên dùng chung, và `cua_so_yen` KHÔNG bảo vệ nó.** Khoá ấy
chỉ khoá lệnh nặng CPU/gate. Hai phiên có thể cùng xanh ở `cua_so_yen` mà vẫn
phá phép đo của nhau.

Đo được ngày 13/09: một lượt đo bão hoà chạy trúng cửa sổ deploy của phiên khác
⇒ cả sáu job chết cùng một khắc, và suýt bị đọc thành *"6 job đồng thời làm sập
hệ"*. Lượt đo ấy phải vứt.

⇒ **Trước khi vào cửa sổ đo: `ListAgents`, nhắn mọi phiên đang sống, chờ họ xác
  nhận.** Báo cả lúc **xong**. Giao ước đi hai chiều — bên đo báo trước, bên
  deploy cũng báo trước.

⚠️ Đề xuất đã ghi cho integrator: thêm tài nguyên khoá thứ ba `production_dang_dung`
   để deploy và đo **loại trừ nhau bằng cơ chế thay vì bằng lời hứa**. Chưa làm.

## 6. Mở rộng — ba luật không được vi phạm

Thêm kịch bản là thêm **một dòng** vào `MA_TRAN` / `MA_TRAN_MO_RONG` trong bộ
chạy. Ba luật dưới đây giữ cho chương trình còn nghĩa sau mười lần mở rộng.

### Luật 1 — kịch bản phải CÓ KHẢ NĂNG HỎNG theo một cách nói lên điều gì đó

Khai rõ **điều gì làm nó đỏ**. Một kịch bản không thể đỏ thì không chứng minh gì
— sổ tay dự án gọi đó là **cửa giả**. Cột "đỏ khi" trong ma trận là bắt buộc; ô
trống nghĩa là kịch bản chưa dùng được.

### Luật 2 — mỗi ngưỡng phải có NGUỒN

Ba nguồn hợp lệ: một **hằng số trong mã**, một **câu trong spec**, hoặc một
**phép đo đã có**. Không có nguồn thì ghi *"chốt sau lượt đầu"* — **đừng bịa một
con số đẹp**.

⚠️ Ngưỡng sai còn tệ hơn không có ngưỡng, vì nó **xanh vĩnh viễn**.

### Luật 3 — mỗi phép đo phải có ĐỐI CHỨNG

Một con số không có đối chứng không phải phát hiện.

🔴 Ngày 13/09 tôi báo *"slot nhả sau 20,8 s — ĐẠT"*. Sai: `max_tokens=2048` sinh
xong trong ~20 s, nên máy B rảnh ở giây 20,8 **dù có cắt hay không**. Phép đo mù
đúng ở chiều nó định đo. Bản sửa: chạy **một lượt trọn vẹn không cắt** trước để
lấy `T_tròn`, rồi mới cắt — kết luận chỉ có nghĩa khi `T_nhả << T_tròn`.

## 7. Lịch sử chạy

Mỗi lượt thêm **một dòng**. Không xoá dòng cũ — so sánh giữa các lượt chính là
thứ một chương trình audit cần.

| ngày | commit production | kết quả | lỗi tìm ra |
|---|---|---|---|
| 2026-09-13 | `3c827ce3` → `08362209` | 9/11 đúng · L-08 đóng (643 s → **0,7 s**) | **L-11**, **L-12** |

## 8. Ngoài phạm vi

- Trộn tải ảnh / voice / Auto Scan Video — chốt **chỉ LLM**. Tranh chấp LLM ↔ ảnh
  đã do cổng I và N đo riêng.
- Cổng M — dư ở biên Cloudflare, **không sửa được ở tầng mã**.
- Cổng L (đa tệp) — thuộc Spec 2, chưa tồn tại.
- Cổng Q (soak) — spec không định nghĩa; chủ sản phẩm chốt bỏ qua 13/09.
