# R2b — tính tiền một lượt agentic. Đề xuất kèm số, đo 2026-09-05

> Chủ dự án giao: *"cách tính tiền thì nghiên cứu sâu sắc và tính theo token
> input, output, giá tiền bạn nghiên cứu sâu sắc rồi tự đề xuất con số cho tối
> ưu, có thể tính bằng giá bằng cách tính api hiện dùng."*

**Kết luận trước, lý lẽ sau:**

> 🔑 **Bảng giá 50 / 10 / 400 credit/1M là ĐÚNG — đừng đổi.** Thứ hỏng là
> **ranh giới làm tròn**, không phải đơn giá. Đổi đúng một thứ: làm tròn theo
> **người dùng tích luỹ**, thay vì làm tròn lên **mỗi lượt gọi**.

---

## §1 — Giá thị trường hôm nay: neo tháng 8 VẪN ĐÚNG

Lấy trực tiếp từ `openrouter.ai/api/v1/models` (431 model), quy đổi theo đúng tỉ
giá đã neo trong `gia_token.py` — **26.300 đ/USD, 1 credit = 100 đ**:

| Model | ctx | vào (cr/1M) | ra (cr/1M) |
|---|---|---|---|
| **`qwen/qwen3.8-27b`** ← **đúng model nhà** | 1.000.000 | **110,5** | **789,0** |
| `qwen/qwen3.8-flash` | 1.000.000 | 39,5 | 123,6 |
| `openai/gpt-5-mini` | 400.000 | 65,8 | 526,0 |
| `google/gemini-3-flash-preview` | 1.048.576 | 131,5 | 789,0 |
| `anthropic/claude-haiku-4.5` | 200.000 | 263,0 | 1.315,0 |

⭐ `gia_token.py` neo *"105 / 789"* từ 22/08. Hôm nay là **110,5 / 789** — lệch
**+5 % ở vế vào, 0 % ở vế ra**. Neo **không trôi**, và tuyên bố *"ta rẻ hơn
~50 %"* vẫn đúng: ta ở **45 %** giá vào và **51 %** giá ra của thị trường.

⚠️ **Suýt kết luận sai.** Nhìn lướt họ Qwen thấy `qwen3.5-35b` 21/197,
`qwen3-32b` 21/74 — tưởng thị trường sập và ta đang đắt gấp đôi. Đó là các model
**khác**. Đúng model nhà là `qwen3.8-27b`. Một phép so sai dòng đủ để đảo ngược
cả một quyết định giá.

---

## §2 — Hai đại lượng, đo trên mã thật

| Đại lượng | Giá trị | Nguồn |
|---|---|---|
| Khối `tools` (4 tool) | **362 token** | `json.dumps(tool_noi_bo.KHOI + 2 tool có phí)` |
| Trần một kết quả tool | **~2.222 token** | `thi_hanh.TRAN_KY_TU_KET_QUA = 8.000` ký tự |
| Điện biên máy B | **~3 / ~50** cr/1M | 358,65 W đo, 3.000 đ/kWh (`gia_token.py`) |
| Bậc cache có thật không | **có** | `timings.cache_n` → `SuDung.token_vao_cache` |

🔑 **Bậc cache là mấu chốt của cả bài toán.** Vòng lặp agentic gửi lại **toàn bộ**
lịch sử mỗi vòng; `llama-server` trả `cache_n` cho phần không phải prefill lại.
Đo trên mô hình: cache làm một lượt 8 vòng **rẻ đi 56 %** (4,63 → 2,03 credit).

Đây là lợi thế thật của tự vận hành: ta **thực sự không tốn gì** để prefill lại,
còn bán lẻ ngoài kia tính đủ giá cho mọi token lặp.

---

## §3 — Vấn đề 1: C1 làm tròn LÊN mỗi lượt GỌI

Mô hình một lượt (ngữ cảnh đầu 2.000 token, mỗi vòng cộng thêm kết quả tool):

| Kiểu lượt | số gọi | tok vào | tok ra | chi phí thật | **C1 thu** | C2 thu | bội |
|---|---|---|---|---|---|---|---|
| V1 chat thường | 1 | 2.362 | 500 | 0,32 cr | 1 | 1 | 1,0× |
| V3 2 vòng | 2 | 7.036 | 590 | 0,49 cr | **2** | 1 | **2,0×** |
| V3 4 vòng | 4 | 23.320 | 770 | 0,92 cr | **4** | 1 | **4,0×** |
| V3 8 vòng (trần) | 8 | 83.632 | 1.130 | 2,03 cr | **8** | 3 | **2,7×** |

⇒ C1 thu **gấp 2–4 lần** giá niêm yết cho đúng thứ V3 sinh ra. Càng nhiều vòng
càng lệch, và người dùng **không điều khiển được số vòng** — model quyết.

---

## §4 — Vấn đề 2 (tìm ra khi nghiên cứu): SÀN 1 CREDIT LÀ THUẾ LUỸ THOÁI

Không nằm trong câu hỏi, nhưng nó **lớn hơn** vấn đề 1:

| Lượt | ta thu | thị trường | **ta / thị trường** |
|---|---|---|---|
| chat rất ngắn (800 + 150) | 1 | 0,21 | 🔴 **4,84×** |
| chat thường (2.362 + 500) | 1 | 0,66 | 🔴 **1,53×** |
| chat dài (8.000 + 900) | 1 | 1,59 | 0,63× |
| chat rất dài (30.000 + 1.200) | 2 | 4,26 | 0,47× |

🔴 **Mọi lượt dưới ~1 credit làm ta ĐẮT HƠN mua lẻ.** Và lượt ngắn chính là lượt
**thường gặp nhất** của một sản phẩm chat.

Mô phỏng một hội thoại **20 lượt** (phần lớn ngắn, ngữ cảnh lớn dần):

| | chi phí thật | thị trường | thu được |
|---|---|---|---|
| Sàn mỗi lượt (C1 **và** C2) | 3,13 | 17,18 | 🔴 **20 credit** |
| Tích luỹ (C3) | 3,13 | 17,18 | ✅ **3 credit** |

⇒ Sàn biến một hội thoại 20 lượt ngắn thành **20 credit** — **6,4×** giá niêm
yết của chính ta, và **1,16×** giá bán lẻ. C2 **không** sửa được chuyện này: nó
chỉ gộp các vòng *trong một lượt*, không gộp các lượt.

---

## §5 — ĐỀ XUẤT: đổi ĐÚNG MỘT THỨ — ranh giới làm tròn

### Đổi gì

```
C1  (nay):  lam tron LEN moi LUOT GOI                 -> 20 credit / 20 luot
C2  (de xuat cu): lam tron LEN moi LUOT (run)         -> 20 credit / 20 luot
C3  (DE XUAT):    tich luy mcredit theo NGUOI DUNG,
                  thu phan NGUYEN, giu lai phan le    ->  3 credit / 20 luot
```

Một cột `mcredit_du` trên `users` (0 ≤ giá trị < 1.000). Mỗi lần quyết toán:

```
du += chi_phi_mcredit_chinh_xac
thu  = du // 1000          # so credit NGUYEN
du  -= thu * 1000          # giu lai phan le
```

### Vì sao **theo người dùng**, không theo hội thoại hay theo run

| Phạm vi | Vấn đề |
|---|---|
| theo **run** (C2) | không sửa được §4 — mỗi lượt vẫn một sàn |
| theo **hội thoại** | Public API không có hội thoại; và mở hội thoại mới để né sàn |
| theo **người dùng** ✅ | một bộ đếm, dùng chung cho ChatLTT **và** `/api/v1`; rò tối đa **0,99 credit ≈ 99 đ mỗi người, trọn đời** |

⛔ **Không dựng sổ tiền thứ hai.** `credit_entries` vẫn là sự thật duy nhất —
mọi lần thu vẫn là một bút toán. `mcredit_du` là **bộ đếm dẫn xuất**, đúng hạng
với `chatltt_run.mcredit_tich_luy` đã có.

### Vì sao KHÔNG đổi bảng giá

- Neo thị trường **vẫn đúng** (§1): ta ở 45 %/51 % giá bán lẻ.
- Biên gộp trên điện ở đơn giá niêm yết: **6,6×**.
- C3 thu **3 credit** cho hội thoại 20 lượt = **đúng bằng** doanh thu bảng giá
  đã định (3,13). Tức C3 **không giảm giá** — nó **thôi thu thừa**.

🔑 Nếu chủ dự án muốn doanh thu cao hơn thì đòn bẩy là **bảng giá** (quyết định
chính sách, cần `phien_ban_gia` mới), **không phải** cái sàn làm tròn (một lỗi
đúng/sai). Trộn hai thứ là cách chắc chắn để không ai biết giá thật là bao nhiêu.

### Bậc cache 10 → 5: **KHÔNG đổi**

Đã cân: hạ xuống 5 làm lượt 8 vòng rẻ đi đúng **1 credit**, và gần như không đổi
gì ở hội thoại thường (3,68 → 3,13, cùng làm tròn thành 3). Không đáng một
`phien_ban_gia` mới. Bậc 10 (20 % giá vào) cũng đã rộng rãi hơn thông lệ nếu xét
rằng cache là chỗ biên lợi nhuận của hội thoại dài sống.

---

## §6 — Điều còn phải chốt và rủi ro

| Mục | Trạng thái |
|---|---|
| Cột `users.mcredit_du` + khoá hàng khi quyết toán | 🔴 **cần** — `credit.giu_cho` đã khoá theo user, có tiền lệ |
| `dieu_khoan.py` đang công bố `toi_thieu_moi_luot_credit = 1` | 🔴 **phải sửa** — điều khoản đổi theo, đúng luật của chính tệp đó |
| Idempotency: quyết toán hai lần không được cộng `du` hai lần | 🔴 cập nhật `du` phải **cùng giao dịch** với `credit.quyet_toan` |
| Rò tối đa | 0,99 credit/người, trọn đời — chấp nhận được |
| Chưa có khách thật | ⭐ **đây là lúc rẻ nhất để sửa** |

⚠️ **Giới hạn của phân tích này:** mọi con số §3–§4 đến từ **mô hình**, không
phải lượt chạy thật — artefact P01 ghi độ trễ và đạt/trượt, **không ghi token**.
Tham số mô hình lấy từ mã (`TRAN_KY_TU_KET_QUA`, khối `tools` đo thật) nhưng
ngữ cảnh đầu 2.000 token và phân bố độ dài là **giả định**. Việc cần làm trước
khi bật thu tiền thật: ghi `usage` của 20–50 lượt thật rồi chạy lại §3–§4.
