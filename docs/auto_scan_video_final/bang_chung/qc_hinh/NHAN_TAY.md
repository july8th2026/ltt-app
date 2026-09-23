# Nhãn tay cho các chỗ nối bị chấm `dat=false` — v1 (廉价的牛肠…, 265 s)

Người đo xem **cả hai khung** của từng chỗ nối rồi trả lời đúng một câu:
*"chỗ nối này có làm đứt mạch nhìn một cách rõ ràng không?"* — đúng câu mà
`qc_ai.loi_nhac_hinh` hỏi model.

⛔ Không chấm theo `ly_do` của model. Đọc lý do trước rồi mới nhìn khung là cách
chắc chắn nhất để gật theo model.

| # | giây (bản ra) | `do_tin` | hai khung là gì | người đo |
|---|---|---|---|---|
| 4 | 20,60 | 1,00 | cận cảnh đĩa đồ ăn đã nướng → toàn cảnh ngoài trời, công nhân dỡ két hàng | **KHÔNG hỏng** — cắt biên tập bình thường (món ăn → nguồn nguyên liệu) |
| 7 | 31,77 | 1,00 | dao cắt lòng bò → công nhân đổ nước vào nồi | **KHÔNG hỏng** — hai bước khác nhau của quy trình |
| 9 | 38,20 | 0,95 | rót soju vào nồi táo/tỏi → chính nồi đó đang sôi | **KHÔNG hỏng** — cùng nồi, nhảy thời gian, chuẩn phim nấu ăn |
| 11 | 46,67 | **0,15** | (dưới `DO_TIN_TOI_THIEU` = 0,70 ⇒ không sinh việc sửa dù bật cổng) | — |
| 16 | 71,37 | 0,95 | tay găng cầm đoạn lòng trong khay → cũng tay đó đang cắt bằng kéo | **KHÔNG hỏng** — cùng người, cùng khay, nhảy một bước quy trình |
| 19 | 79,34 | 0,90 | cận cảnh tay cầm miếng lòng → toàn cảnh chính người thợ bên các khay | **KHÔNG hỏng** — cận → toàn, cùng người cùng chỗ |
| 30 | 124,07 | 0,95 | lòng sống trên vỉ nướng lửa → cùng vỉ đó, đã có kẹp gắp, lòng xếp khác | **KHÔNG hỏng** — nhảy thời gian trong lúc nướng |
| 31 | 126,40 | 0,90 | (cùng cảnh bếp, hai bước nấu liên tiếp) | — chưa soi bằng mắt |
| 37 | 157,17 | 0,90 | (cùng nồi thịt nướng, góc rộng → góc hẹp) | — chưa soi bằng mắt |
| 39 | 167,17 | 0,95 | đũa gắp một miếng trên vỉ → kẹp gắp đảo đồ ăn trên chính vỉ đó | **KHÔNG hỏng** — cùng món cùng vỉ, đổi dụng cụ |

⇒ **8/8 chỗ nối đã soi bằng mắt đều là BÁO ĐỘNG GIẢ.** Hai cái còn lại (#31,
#37) chưa soi; lý do model đưa ra cho chúng cùng một khuôn với tám cái kia
("cùng một cảnh quay… khung trước là…, khung sau là…"), nhưng ⛔ **không đếm
chúng vào số liệu** — một nhãn suy ra từ lý do của chính model thì không phải
một nhãn độc lập.

**9/10** cái bị chấm có `do_tin` ≥ 0,70, tức chúng **vượt** `DO_TIN_TOI_THIEU`
và sẽ sinh việc sửa thật nếu bật cổng.

## Đối chứng phía kia (chỗ nối được chấm `dat=true`)

⛔ Chỉ xem cái bị chấm hỏng thì không đo được recall.

| # | giây | hai khung là gì | người đo | model |
|---|---|---|---|---|
| 1 | 8,97 | lòng nướng trên vỉ → cận hơn cùng vỉ đó | KHÔNG hỏng | `dat=true` ✅ |

## Điều số liệu này nói ra

Lý do model đưa ra ở **cả 6** lượt đều mô tả một **thay đổi nội dung**
("khung 1 là…, khung 2 là…, có sự thay đổi"), chứ không mô tả một chỗ đứt mạch.
Tức model đang trả lời câu *"hai khung này có khác nhau không"* thay vì câu
*"chỗ nối này có gây khó hiểu không"* — trong khi lời nhắc nói thẳng rằng hai
khung khác hẳn nhau (khác bối cảnh, khác góc máy, khác chủ thể) là một cắt
**ĐÚNG**.

⇒ Đây là **hình dạng lời nhắc**, cùng họ với R-05 của làn `fix-toc-do` (8/18
lượt hỏng vì lời nhắc, không phải vì model) — không phải "model kém". Nhưng
chừng nào chưa đo lại sau khi sửa lời nhắc thì con số hiện hành vẫn là con số
hiện hành, và nó không đủ để tiêu tiền.
