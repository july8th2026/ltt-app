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
# 2. Chạy kịch bản — bench.py, TRÊN MÁY B, chỉ stdlib
python bench.py --kich-ban c1    --ra ket_c1.jsonl     # một lượt đơn, có cho_ranh()
python bench.py --kich-ban c4    --ra ket_c4.jsonl     # bốn lượt đồng thời
python bench.py --kich-ban whale --ra ket_whale.jsonl  # prefill khổng lồ + ba minnow lệch giờ
python bench.py --kich-ban nap   --ra ket_nap.jsonl    # TTFT gồm cả nạp lạnh
```

`bench.py` ở `docs/ltt_llm_dual/artifacts/bench/bench.py`, ghi **từng dòng
JSONL** (không đợi cuối lô) và nhịp tim 15 s ra `<ra>.nhip.txt`.

## 2b. ⛔ BỘ ĐO LÀ THỨ MƯỢN, KHÔNG PHẢI THỨ TỰ XÂY

Chủ dự án chốt **14/09/2026**: *"bộ đo có sẵn trong hệ thống đã sử dụng và pass —
xóa đo tự vẽ trùng lặp."*

Ngày 13–14/09 tôi đã dựng một bộ đo riêng (`tools/nghiem_thu_van_hanh/`, sáu
module, bốn tệp test). **Nó đã bị xoá.** Lý do không phải nó xấu mã — mà là:

| | |
|---|---|
| một lượt chạy của nó sinh **bốn lỗi (V-01…V-04), cả bốn là lỗi của chính nó** | mỗi lỗi bộ đo tốn một lượt chạy production để phát hiện |
| nó **trùng** `bench.py` ở phần cốt lõi | hai bộ đo cùng trả lời một câu là hai bộ đo có thể mâu thuẫn |
| `bench.py` đã **chạy thật, đã pass, có baseline `.jsonl`** | thứ đã chứng minh thắng thứ mới viết |

⇒ **Cần đo thêm một đại lượng thì thêm một kịch bản vào `bench.py`** (§6), không
  mở một bộ đo thứ hai. Luật này áp cho mọi phiên sau.

### Nợ đã ghi, KHÔNG tự ý trả bằng một bộ đo mới

`bench.py` đo **engine máy B** qua llama-swap loopback (`:8280`). Nó **không** đi
qua `API → admission → hàng đợi → credit` của máy A. Tầng ấy hiện đo bằng
**test trong cây** (`tests/test_1240`…`test_1250`) cộng ba lượt nghiệm thu
production đã ghi ở §7. Muốn đo tầng ấy bằng tải thật thì **đề xuất thành một
kịch bản của `bench.py`**, và chỉ làm khi chủ dự án chốt.

## 3. Tài liệu con

| | |
|---|---|
| **Bộ đo** | `docs/ltt_llm_dual/artifacts/bench/bench.py` |
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

Thêm kịch bản là thêm **một nhánh** vào `bench.py` (xem khối `Kich ban da cai`
ở đầu tệp ấy), **không** mở một bộ đo mới — §2b. Ba luật dưới đây giữ cho chương
trình còn nghĩa sau mười lần mở rộng.

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
