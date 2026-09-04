# NGỮ CẢNH DÀI — KẾT QUẢ, VÀ MỘT LƯỢT CẮT NGẮN CÓ CHỦ Ý

*2026-09-05. Thô: `artifacts/01_nc_50k.json`, `artifacts/01_nc_sau.json`.*

## ⛔ Đây KHÔNG phải đi tìm trần token

Trần đã chốt và tài liệu đã có: `apps/ltt_llm/ngan_sach.py` (`CUA_SO_MODEL`
204.800 · `TOKEN_VAO_TRAN` 169.984 · `CONG_BO_CHO_CLIENT` 156.385), quyết định
**D-0** (`docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md`), **Q120**. Lô này **không
đo lại một con số nào** trong đó.

Câu hỏi ở đây khác hẳn, và nó đến từ một cảnh báo chính thức:

> `llama.cpp/docs/function-calling.md:332` `[!CAUTION]` — *"Beware of extreme KV
> quantizations (e.g. `-ctk q4_0`), they can substantially degrade the model's
> **tool calling** performance."*

Trần trả lời *"nhét được bao nhiêu"*. Lô này hỏi *"nhét sâu rồi thì nó còn **gọi
tool đúng** không"*. Production chạy đúng `q4_0`, và D-0 đã khoá nó lại — nên
đây là câu chưa ai trả lời, không phải câu đã trả lời rồi.

## Kết quả: 22/22, không suy giảm

| Độ sâu thật | Vị trí kim | Gọi đúng tool | Kim trong đối số |
|---|---|---|---|
| ~42.000 | đầu | 4/4 | 4/4 |
| ~42.000 | giữa | 4/4 | 4/4 |
| ~42.000 | cuối | 4/4 | 4/4 |
| ~128.000 | đầu | 4/4 | 4/4 |
| ~128.000 | giữa | 4/4 | 4/4 |
| ~128.000 | cuối | 2/2 | 2/2 |
| **Tổng** | | **22/22** | **22/22** |

⭐ Cột thứ hai mới là cột đắt. Chỉ đòi *"có gọi tool"* thì bỏ lọt dạng hỏng đáng
sợ nhất — **gọi đúng tool với đối số bịa**. Ở đây model phải moi một dữ kiện
chôn trong tài liệu 128K rồi đặt nó vào đúng trường đối số, và nó làm đúng 22/22.

Vị trí **giữa** không kém hai vị trí kia. Đó là điểm đáng chú ý: "lost in the
middle" là chỗ KV lượng hoá thường lộ ra trước, và ở đây nó không lộ.

Độ trễ: 43 s ở 42K · **180–188 s ở 128K**. Chính con số thứ hai là thứ vượt trần
120 s của Nexus và buộc phải đi đường Scheduled Task.

## 🔴 Cắt ngắn: 12 lượt còn lại đã DỪNG, và vì sao đó là quyết định đúng

Kế hoạch có thêm một tầng 180K (12 lượt, ~35 phút). **Đã dừng**, sau khi chủ dự
án chỉ ra chi phí — và khi kiểm lại thì họ đúng:

| Lý do | Số |
|---|---|
| Câu hỏi đã được trả lời | 22/22, ba vị trí kim, hai độ sâu cách nhau 3× |
| ChatLTT **không chạm tới** 180K mỗi lượt | `luot.py:44` `TRAN_KY_TU_LUOT = 200.000 ký tự ≈ 80K token` — 128K đã phủ **gấp rưỡi** |
| Chi phí còn lại | ~35 phút GPU cho một điểm dữ liệu biên |

⚠️ **Nhưng phải nói đúng phạm vi, không nói quá.** `TOKEN_VAO_TRAN` của nền tảng
là **169.984**, không phải 80K — cửa `/api/v1` **cho phép** khách gửi tới đó. Nên
kết luận đúng là:

> Vùng **128K trở xuống**: đã đo, không suy giảm.
> Vùng **128K–170K**: **chưa đo**. Nó nằm ngoài đường ChatLTT (trần một lượt
> ~80K) nhưng **trong** đường Public API.

⇒ Nếu sau này có khách API gọi tool ở ngữ cảnh > 128K, câu này phải mở lại. Nó
tốn ~10 phút, và ghi ở đây để lần sau không ai phải đoán nó đã được đo hay chưa.

## Điều này đổi gì

| Trước | Sau |
|---|---|
| [U] cảnh báo `q4_0` làm hỏng tool-calling — **rủi ro chưa đo** | **đã đo tới 128K: không thấy suy giảm** |
| A/B `q8_0` vs `q4_0` là hạng mục bắt buộc | **hạ ưu tiên** — nếu `q4_0` đã đạt 22/22 ở 128K thì cái giá của nó, nếu có, nhỏ hơn sức phân biệt của bộ kiểm này |
| Rủi ro #2 của kế hoạch | **đóng ở vùng ChatLTT**, mở ở vùng API > 128K |

⭐ Hạ ưu tiên A/B KV là thu hoạch lớn nhất của lô này về mặt thời gian: nó lẽ ra
tốn hai lần khởi động lại dịch vụ máy B, hai lần nạp model, và ~25 phút — để trả
lời một câu mà quyết định D-0 **không cho phép hành động theo** dù kết quả thế nào.
