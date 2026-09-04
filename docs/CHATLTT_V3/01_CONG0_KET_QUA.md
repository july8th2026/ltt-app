# CỔNG 0 — KẾT QUẢ: 🟢 **THÔNG**

*Chạy 2026-09-04. Ngưỡng chốt ở `01_NGUONG_VA_MA_TRAN.md` §0, commit `ddf7af3`,
**trước** commit này. Dữ liệu thô: `artifacts/01_cong0.json`.*

## Phán quyết

> **🟢 THÔNG — 20/20.** Hợp đồng phục vụ khớp định dạng. Lô chính được phép chạy.
>
> Dự đoán từ phân tích mã (`01_M1_NATIVE_HAY_GENERIC.md`: NATIVE, Qwen3-Coder,
> XML) **khớp với đo thật**. Không có ô nào rơi vào `lech_dinh_dang`.

| Nhóm | Ngưỡng đã chốt | Đo được | |
|---|---|---|---|
| **G0-1** một tool rõ ràng | 5/5 `tool_calls` có cấu trúc | **5/5** | ✅ |
| **G0-2** không cần tool | 5/5 chỉ văn bản, `tool_calls` rỗng | **5/5** | ✅ |
| **G0-3** hai tool, `parallel_tool_calls: true` | ≥ 3/5 ra ≥ 2 lời gọi; **0/5** dạng chữ | **5/5 ra đúng 2**, `finish_reason=tool_calls`, 0 dạng chữ | ✅ vượt |
| **G0-4** nối tiếp sau `tool` result | 5/5 đọc được kết quả và đi tiếp | **5/5** | ✅ |

Độ trễ: nạp model **21,0 s** ở lượt đầu, sau đó **1,4–3,2 s** mỗi lượt
(card sạch 789/24576 MiB trước khi bắt đầu, đúng điều kiện §4).

## Vì sao G0-3 là kết quả đáng chú ý nhất

Cả 5 lượt ra **đúng hai** lời gọi — `calculator` **và** `weather_fake` — trong
một lượt, `finish_reason=tool_calls`. Nghĩa là:

1. gọi song song **hoạt động thật** trên hồ sơ này, không chỉ "được hỗ trợ trên lý thuyết";
2. cờ `parallel_tool_calls: true` **là thứ bật nó** — llama.cpp tắt mặc định
   ([U] `docs/function-calling.md:24`). Nếu bộ kiểm không gửi cờ, nó sẽ đo một
   năng lực đã tắt sẵn rồi kết luận sai rằng model không làm được.

⭐ Đây là một trong hai luật rút ra ở M-1 §6, và nó vừa được xác nhận bằng đo.

## 🔴 Một phát hiện NGOÀI Ý ĐỊNH, và nó quan trọng hơn cả cổng này

Fixture của G0-4 đưa cho model một kết quả tool **SAI**:

```
8123 x 4471 that su  =  36.317.933
so toi nhet vao tool =  36.325.133      <- lech 7.200
```

Đó là lỗi số học của tôi khi dựng fixture. Nhưng nó biến G0-4 thành một **đối
chứng tình cờ** mạnh hơn hẳn bản gốc, và cả **5/5** lượt đều nói cùng một điều:

> Model **lặp lại con số của tool**, không tự tính lại, không nghi ngờ.

Nếu fixture đúng số, kết quả sẽ **mơ hồ**: model có thể tự tính rồi trùng khớp
ngẫu nhiên, và ta không phân biệt được "đọc kết quả tool" với "tự làm ra cùng
đáp án". Số sai đã loại bỏ đúng sự mơ hồ đó.

**Hai kết luận, và cái thứ hai mới nặng:**

1. ✅ Model **thật sự tiêu thụ** `tool` result — G0-4 đạt, không phải đạt nhờ trùng hợp.
2. 🔴 Model **tin tuyệt đối** vào kết quả tool. Nó không có phòng vệ nào của
   riêng nó.

⛔ Hệ quả cho **P02, ranh giới tin cậy** — và nó đổi một giả định: bản kế hoạch
viết *"kết quả tool là dữ liệu không tin được"* như một nguyên tắc kiến trúc.
Đo này cho thấy đó không phải nguyên tắc phòng xa, mà là **mô tả đúng hành vi
đã quan sát được**. Một kết quả tool bị bẻ — từ web, từ tệp người lạ, từ một
máy chủ MCP độc — sẽ đi thẳng vào câu trả lời cho khách, **không gặp một lớp
hoài nghi nào ở model**.

⇒ Phòng vệ injection **phải nằm ở kernel**, trước khi kết quả tới model. Đặt
niềm tin vào việc "model sẽ thấy nó vô lý" là đặt vào một thứ vừa được đo là
không tồn tại. Ghi vào `00_DO_NOT_REWRITE.md` §6 như một mệnh đề **đã đo**,
không phải một lo xa.

⭐ Và đây là lý do giữ nguyên fixture sai thay vì sửa nó: sửa đi là vứt mất đối
chứng duy nhất chứng minh được điều này. Thay vào đó, fixture được **ghi chú rõ
là cố ý sai** trong `p01_cong0.py`, kèm con số đúng.

## G0-2 — bẫy dương tính giả không sập

Năm câu, gồm hai câu **nghe như** cần tool:

| Câu | Model làm gì |
|---|---|
| *"2 + 2 bằng mấy?"* | trả lời thẳng `4` — **không** gọi `calculator` |
| *"Bạn tên gì?"* | tự giới thiệu, có kể ra năng lực tra thời tiết/tính toán mà **không gọi** |

⭐ Câu thứ hai là ca khó hơn: model **nhắc tới** tool trong câu trả lời mà không
**gọi** tool. Phân biệt được "nói về năng lực" với "dùng năng lực" là đúng thứ
chỉ số #2 (dương tính giả) đo, và ở cỡ mẫu này nó sạch 5/5.

⚠️ Năm lượt **không đủ** để công bố tỉ lệ dương tính giả ≤ 3 %. Cổng 0 chỉ
tuyên bố **ống thông**, không tuyên bố chất lượng. Con số đó là việc của lô chính.

## Điều này đổi gì

| Mục | Trạng thái |
|---|---|
| Cổng 0 | 🟢 THÔNG — lô chính được phép chạy |
| M-1 (native/generic) | đóng, **có cả bằng chứng mã lẫn bằng chứng đo** |
| Luật `parallel_tool_calls: true` | ✅ xác nhận bằng đo |
| Luật cấm `tool_call_format=json` | vẫn là suy luận từ mã — **chưa đo**. Nên đo một lượt ở lô chính để biến nó thành sự thật đo được, vì nó là luật đắt nhất trong bộ |
| Ranh giới tin cậy P02 | nâng từ *nguyên tắc* lên *quan sát*: model không hoài nghi kết quả tool |

## Việc kế tiếp

1. Đo **một lượt** với `tool_call_format=json` để xác nhận cái bẫy §5 của M-1 là
   thật — nếu đúng, nó biến một luật suy ra thành một luật đo được, và phép kiểm
   tĩnh chốt nó có căn cứ thay vì có niềm tin.
2. Chạy lô chính (541 lượt bộ lõi) theo `01_NGUONG_VA_MA_TRAN.md` §1-§2.
