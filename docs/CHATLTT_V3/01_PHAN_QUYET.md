# P01 — PHÁN QUYẾT: 🟢 **PASS**

*2026-09-05. Ngưỡng chốt ở `01_NGUONG_VA_MA_TRAN.md`, commit `ddf7af3`, **trước**
mọi dữ liệu — kiểm được bằng `git log`.*

> **Hợp đồng phục vụ Qwen3.8 đủ điều kiện làm nền cho điều phối tool của V3.
> P02 được phép khoá Qwen làm planner.**

## Môi trường đã ghim

| Mục | Giá trị | Cách biết |
|---|---|---|
| llama.cpp | `0.3.0-dev` **build 10689**, commit `57291f264`, Clang 20.1.8 | `--version` trên máy B |
| GGUF | `Qwen3.8-27B-UD-Q4_K_M.gguf` | yaml |
| Template | `qwen3.8-froggeric-v22.3`, SHA256 `6e1439c9…03629b`, 421 dòng | `files/read`, `truncated=False`, byte khớp |
| Handler | **Qwen3-Coder** (`COMMON_CHAT_FORMAT_PEG_NATIVE`) | `chat.cpp@57291f264:3597-3601` |
| Hồ sơ | `qwen38-api` `-c 204800`, KV **`q4_0`**, `--parallel 1`, MTP n-max 2 | yaml — **khớp hoàn toàn** bản đang chạy trên máy B |

## Bốn cổng, tất cả đều thông

| Cổng | Quy mô | Kết quả |
|---|---|---|
| **0** khớp định dạng | 20 lượt | 🟢 20/20 — không lượt nào lệch định dạng |
| **Lô chính** 9 chỉ số | 532 lượt (2 nhánh) | 🟢 **9/9 PASS** |
| **Ngữ cảnh sâu** | 22 lượt, tới 128K | 🟢 22/22 gọi đúng **và** 22/22 kim trong đối số |
| **Đường ống LTT** | 7 phép kiểm | 🟢 7/7 (`tests/test_800_*`) |

Tổng: **581 lượt gọi model · 0 lượt hỏng · 0 credit · ~40 phút GPU.**

### Chín chỉ số, nhánh tiếng Việt có dấu

| # | Chỉ số | Ngưỡng | Đo | |
|---|---|---|---|---|
| 1 | Chọn đúng tool | ≥ 92 % | 98,8 % | ✅ |
| 2 | Dương tính giả | ≤ 3 % | **0 %** | ✅ |
| 3 | Schema hợp lệ | ≥ 98 % | **100 %** | ✅ |
| 4 | Đối số đúng nghĩa | ≥ 90 % | 98,5 % | ✅ |
| 5 | Chuỗi 2 bước | ≥ 85 % | **100 %** | ✅ |
| 6 | Gọi trùng / lặp | ≤ 2 % | **0 %** | ✅ |
| 7 | Bịa tool | **0 %** | **0 %** | ✅ |
| 8 | **Vượt rào injection** | **0 %** | **0/30** | ✅ |
| 9 | Trả lời cuối đúng | ≥ 88 % | 97,9 % | ✅ |

Ngoài bảng: gọi song song **18/18 ra đúng 2 lời gọi** · mơ hồ **18/18 hỏi lại,
0 gọi bừa**.

## Ba câu M-1/M-2/M-3 đã đóng

| | Câu | Trả lời |
|---|---|---|
| **M-1** | Handler Native hay Generic? | **NATIVE** (Qwen3-Coder). Chứng minh bằng **mã** (ba chuỗi phát hiện có đủ trong template, không nhánh nào bắt trước) **và** bằng **đo** (Cổng 0 không lượt nào lệch định dạng) |
| **M-2** | `q4_0` hỏng tool-call bao nhiêu? | **Không đo thấy suy giảm** tới 128K, cả ba vị trí kim. A/B `q8_0` **hạ ưu tiên** — xem §giới hạn |
| **M-3** | Năm lời hứa của template v22.3? | **Không tái hiện** được lỗi nào trong 581 lượt: không stalling giữa vòng tool, không crash JSON đối số, không "empty think poisoning" |

## Bốn phát hiện đổi kế hoạch

| ID | Phát hiện | Ảnh hưởng |
|---|---|---|
| **M-6** | Khi có `tools`, llama.cpp **cưỡng chế sinh** bằng văn phạm GBNF (lazy, kích hoạt bởi `<tool_call>`) — không chỉ phân tích | Định dạng được bảo đảm ở tầng **sinh**, mạnh hơn giả định ban đầu. Cũng là lý do bẫy `tool_call_format=json` **không nổ** |
| **M-5** | Model tin **dữ liệu** tool nhưng không nghe **mệnh lệnh** tool | Bề mặt lộ lớn hơn không phải injection (0/30) mà là **dữ liệu sai** — model không có phòng vệ nào trước nó. ⇒ P02: kernel phải kiểm **tính đúng** của dữ liệu, không chỉ lọc lệnh |
| **U-2** | `parallel_tool_calls` tắt mặc định | Phải gửi cờ; đã ghim bằng `test_800` |
| **VI** | Tiếng Việt **không dấu** ăn mất ~10 điểm độ chính xác đối số, nhưng **không** làm hỏng ý định | ⇒ P05/P09: hiện đối số ra trước khi chạy tool **có phí** |

## ⛔ Giới hạn — phần PASS này KHÔNG bao gồm

| Chưa đo | Vì sao chấp nhận được | Khi nào phải mở lại |
|---|---|---|
| Ngữ cảnh **128K–170K** | ngoài đường ChatLTT (trần một lượt ~80K token) | có khách API gọi tool ở ngữ cảnh sâu hơn |
| A/B `q8_0` vs `q4_0` | `q4_0` đã 22/22 ở 128K; và **D-0 không cho phép hành động theo kết quả** dù nó thế nào — 200K đã chốt | nếu chất lượng tool-call sa sút trong vận hành |
| MTP bật/tắt · `reasoning_effort` low/xhigh | biến số production chưa cô lập; không cái nào gây triệu chứng trong 581 lượt | nếu có triệu chứng |
| Vòng lặp **thật** nhiều bước | lô này nạp sẵn kết quả tool; chưa lượt nào chạy N vòng model liên tiếp | **P03** — đó chính là việc của P03 |
| Sổ tiền của một lượt agentic thật | `test_800` chỉ chứng minh `tools` làm tăng giữ chỗ | **P04** |

⭐ **Và một giới hạn về chính bộ kiểm:** model đạt ~100 % trên gần hết chỉ số,
nên ngưỡng **không hề ràng buộc** và bộ kiểm **gần như không có sức phân biệt**.
Nó chứng minh *"không có khiếm khuyết thô"* — đủ cho cổng hôm nay. Nó **chưa**
đủ làm lưới đỡ hồi quy cho P03–P12; P03 phải làm nó khó lên trước khi dựa vào nó.

## Ba lần bộ đo tự hỏng — và cả ba đều hỏng ÊM

Ghi lại vì đây là thu hoạch phương pháp lớn nhất của P01, không phải phần phụ:

| # | Triệu chứng | Sự thật |
|---|---|---|
| 1 | `doi_so_dung` **FAIL 77,9 %** | **Cả 8 lượt trượt là lỗi của tôi.** Tôi viết kịch bản bằng tiếng Việt không dấu; `"dong dat"` model đọc thành `"đồng yên"` — cách đọc **hợp lệ**. Chỉ đọc bảng tổng hợp là đã kết luận *"Qwen đối số kém"* và dựng cả một vòng chỉnh prompt để sửa một lỗi không tồn tại |
| 2 | Ngữ cảnh dài **hỏng 12/12** | Hỏng trong **0,6 giây** — quá nhanh cho prefill 50K. Base64 vượt trần dòng lệnh Windows; lệnh bị cắt rồi **vẫn chạy**. Nếu không nhìn con số 0,6 s thì đã kết luận *"model hỏng ở ngữ cảnh dài"* — **đúng cái kết luận lô đó sinh ra để kiểm chứng** |
| 3 | 156K **trượt ở 120,2 s** | Không phải model (GPU 100 % lúc đó) mà là trần Nexus. Ba đường chạy tách rời đều chết êm trước khi tới Scheduled Task |

⭐ Mẫu số chung: **phép đo hỏng theo đúng chiều nó đang đi tìm.** Cả ba lần, cách
phát hiện không phải là bảng tổng hợp mà là **một con số trông vô lý** — 0,6 giây,
120,2 giây, và tám lượt trượt tập trung vào ba câu hỏi cụ thể. Bảng tổng hợp
không bao giờ tự nói nó sai.

⇒ Luật cho các pha sau: **soi từng lượt trượt trước khi tin một tỉ lệ.** Một chỉ
số FAIL mà không mở ra xem từng ca là một chỉ số chưa đọc.
