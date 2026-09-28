# `Model trả lời rỗng` khi dịch prompt ảnh — nguyên nhân và thuốc

**Đo 28/09/2026 trên production, máy A gọi máy B.** Chủ dự án chốt **tạm bỏ qua**
(tính năng tạo ảnh từ VLM sẽ hoàn thiện sau) — tệp này giữ lại số đo để lượt ấy
⛔ không phải đo lại.

## Triệu chứng

Một run workflow thật (`0990ef96`, mẫu `ai-viet-mo-ta-roi-sinh-anh`):

```
y_tuong (ai.llm)          SUCCEEDED
anh (app.image.generate)  FAILED
  provider_loi: RuntimeError: Không dịch được prompt sang tiếng Anh
    (GoiLLMThatBai: Model trả lời rỗng — thử lại hoặc đổi mô tả.)
```

## 🔴 Nguyên nhân: `ltt-3.5` tiêu HẾT `max_tokens` vào phần SUY NGHĨ

`platform_core/image_gen/dich_llm.py` đặt `MAX_TOKENS = 1024` và `taoanh` khai
model nội bộ `ltt-3.5`. Đo `dieu_phoi.goi` trực tiếp:

| model | `max_tokens` | `reasoning_effort` | `finish_reason` | `content` | suy nghĩ | thời gian |
|---|---|---|---|---|---|---|
| `ltt-3.5` | 1024 | *(không đặt)* | **`length`** | **0** | 3 131 | 14,4 s |
| `ltt-3.5` | 2048 | *(không đặt)* | **`length`** | **0** | 6 348 | 27,5 s |
| `ltt-3.5` | 4096 | *(không đặt)* | `stop` | 17 | 6 330 | 27,4 s |
| `ltt-3.5` | 1024 | `minimal` | **`length`** | **0** | 3 236 | 15,2 s |
| **`ltt-3.5`** | **1024** | **`low`** | **`stop`** | **31** | 1 106 | **4,3 s** |
| `ltt-3.8` | 256 | *(không đặt)* | `stop` | 38 | — | 3,9 s |

⇒ `content` rỗng **⛔ không phải lỗi ngẫu nhiên** — nó là hệ quả **tất định** của
`finish_reason='length'`: model dùng hết ngân sách token cho `reasoning_content`
rồi ⛔ không còn chỗ viết câu trả lời.

## ⭐ Thuốc: `reasoning_effort='low'`

**4,3 s** (nhanh gấp ~3), `content` đủ, và **giữ chi tiết**. Ba lựa chọn khác đều
tệ hơn:

- **tăng `MAX_TOKENS` lên 4096** — 27 s, và bản dịch **mất chi tiết**:
  `'A kitten sleeping'` (mất *"tam thể"* và *"bậu cửa sổ"*). Đó đúng thứ
  `prompt_dich.py` tồn tại để bảo vệ — bảng D-027 trong docstring của nó cho thấy
  mất chi tiết ⇒ **ảnh sai**. `low` cho `'Cat sleeping on the window sill'` (giữ
  được bậu cửa sổ).
- **đổi sang `ltt-3.8`** — nhanh và chính xác nhất (`'The cat is sleeping on the
  windowsill.'`), nhưng 3.8 là model 27B và nó **tranh card với model ảnh**. Chính
  docstring `dich_llm.goi_llm` nói `MODEL_NOI_BO_MAC_DINH = ltt-3.5` được chọn vì
  *"model không tranh card với ảnh"*. ⇒ Đổi model là một **đánh đổi sản phẩm**
  (chất lượng dịch vs thông lượng ảnh), ⛔ không phải một bản vá.
- **`reasoning_effort='minimal'`** — ⚠️ **tệ hơn `low`**: vẫn `length`, vẫn rỗng.
  ⛔ Đừng suy rằng "minimal ít suy nghĩ hơn low". Với `ltt-3.8` máy chủ **nâng**
  `minimal → low` (L-33); với `ltt-3.5` thì ⛔ không, và `minimal` ⛔ không cắt được
  phần suy nghĩ.

## ⚠️ Vế thứ hai, độc lập với mọi lựa chọn trên: THÔNG ĐIỆP SAI LẠC

`dich_llm.py:109` ném `"Model trả lời rỗng — thử lại hoặc đổi mô tả."` cho ca
`finish_reason='length'`. Cả hai lời khuyên đều **sai**:

- *thử lại* → hỏng y hệt (tất định, ⛔ không ngẫu nhiên);
- *đổi mô tả* → prompt **ngắn hơn** cũng hỏng (đo: `"con meo tam the ngu tren bau
  cua so"` cũng rỗng).

⇒ Người đọc đi đúng hướng mà thông điệp chỉ, và cả hai hướng đều là đường chết.
Cùng hạng *"một thông điệp sai tiêu thời gian theo hướng NGƯỢC"*.

⭐ Thông điệp đúng phải phân biệt hai ca:

```
finish_reason == 'length'  ->  "model dung het ngan sach token cho phan suy nghi;
                                dat reasoning_effort='low' hoac tang max_tokens"
finish_reason == 'stop' + content rong  ->  "model tra loi rong that"
```

## Phạm vi ảnh hưởng

`dich_llm.tao_ham_dich` được dùng bởi **ba** app: `taoanh` · `anhnoibo` ·
`thumbnail` (`apps/*/jobs.py`). Cả ba khai model nội bộ mặc định `ltt-3.5`, nên
**cả ba** đi qua cùng hố này với mọi prompt.

## Cách tái hiện

`dieu_phoi.goi(db, messages=…, model_theo_provider=canonical.ban_do_model("ltt-3.5"),
max_tokens=1024)` rồi đọc `kq.finish_reason` và `len(kq.noi_dung)`.

⚠️ ⛔ Đừng đo qua `dich_llm.goi_llm`: nó đọc **đúng một** trường (`kq.noi_dung`)
rồi ném — nên nó ⛔ không cho biết `finish_reason`, tức ⛔ không cho biết **vì sao**
rỗng. Tôi mất một lượt đo vì đứng ở tầng đó.

---

## 🔴 SỬA HÌNH DẠNG BẢN VÁ — lớp lỗi có **hai** nạn nhân, và cần gạt cơ học ĐÃ CÓ

Phiên *"Phân tích lỗi hiển thị máy B"* đối chiếu tài liệu này và đưa mảnh tôi
thiếu (28/09). Tôi đã **kiểm lại từng lời khai bằng mã**, cả ba đúng khít.

⚠️ **Nên mục khuyến nghị `reasoning_effort='low'` ở trên là chưa đủ**: nó chữa
**một nơi gọi**, còn lớp lỗi có hai nạn nhân đã biết và ⛔ không có gì chặn nạn
nhân thứ ba.

### Sàn đã tồn tại, và chỉ được cưỡng chế ở CỬA CÔNG KHAI

```
apps/ltt_llm/ngan_sach.san_token_ra("ltt-3.5")          = 2560   (= 2048 budget + 512 chỗ trả lời)
apps/ltt_llm/ngan_sach.san_token_ra_dong_bo("ltt-3.5")  = 1024
```

Cưỡng chế ở `apps/ltt_llm/executor.py:62` → `features.kiem_san_token_ra`. Ba nơi
gọi **nội bộ** đi cửa khác nên ⛔ không qua sàn:

| Nơi gọi | `max_tokens` | model | vs sàn 2560 |
|---|---|---|---|
| `platform_core/image_gen/dich_llm.py:39` | 1024 | `ltt-3.5` | 🔴 dưới sàn — ca đo ở trên |
| `apps/taovideo/translate.py:29` | **2048** | `ltt-3.5` | 🔴 **dưới sàn — nơi thứ hai, chưa ai báo** |
| `apps/prompt_ai_ommi/provider.py:67` | 8192 | `ltt-3.5` | ✅ trên sàn |

`taovideo/translate.py` cũng ⛔ không đặt `reasoning_effort` (`grep`: chỉ
`max_tokens=_MAX_TOKENS` ở dòng 88) ⇒ trùng khít hình dạng đã đo.

⇒ **Thuốc đúng: mọi nơi gọi nội bộ đọc `san_token_ra(model, muc_nghi)` thay vì gõ
một hằng số.** `budget_suy_nghi_dong_bo` đã ghi sẵn lý do từ trước: *"để suy nghĩ
tiêu hết `max_tokens` là trả `content` rỗng"*. Giữ `reasoning_effort='low'` **thêm**
(số đo ở trên: nhanh gấp 3 và giữ chi tiết), ⛔ không thay.

### ⚠️ Nhưng một phép kiểm cơ học lấy `san_token_ra` làm sàn sẽ ⛔ KHÔNG chặn được `ltt-3.8`

```
san_token_ra("ltt-3.8") = 64     (mọi mức — SAN_TOKEN_RA_THEO_NGHI dùng _SAN_NHE)
```

`64` là **cố ý**, có số đo kèm tại chỗ: *"Đo 13/09: 63 token ở MỌI mức, đúng ngay
ở max_tokens=100 — chưa từng thấy trả rỗng, nên lấy sàn đo được, không nhân biên."*

🔴 **Nhưng số đo ấy có ngày 13/09, còn thứ nó làm sàn cho đã đổi ngày 19/09.**
L-32/L-33 thêm **trần suy nghĩ theo mức** cho riêng 3.8
(`BUDGET_SUY_NGHI_THEO_MUC["ltt-3.8"] = {low: 1024, medium: 2048, xhigh: 4096}`),
và mức mặc định là `medium` = **2048**. Một sàn `64` đứng trước một budget suy nghĩ
`2048` thì ⛔ không chặn được gì: đúng cơ chế đã làm `ltt-3.5` trả rỗng.

⛔ **Tôi CHƯA đo `ltt-3.8` trả rỗng** — đây là một **lệch ngày giữa số đo và thứ
nó đo**, ⛔ không phải một lỗi đã tái hiện. Phép đo khép lại nó: gọi `ltt-3.8`,
`reasoning_effort` để trống, `max_tokens` = 64…256, xem `finish_reason` và độ dài
`content`. Nếu rỗng thì sàn 3.8 phải tính lại theo `BUDGET_SUY_NGHI_THEO_MUC` +
`TOKEN_CHO_TRA_LOI`, đúng cách `_SAN_35` đã tính.

⭐ Cùng họ với `memory/con-so-cong-phai-kem-sha-va-moi-truong.md`: một con số cổng
**đúng lúc đo** có thể sai sau khi thứ nó đo đổi hình dạng — nên một sàn cần ghi
**ngày đo** và **cái nó giả định**, không chỉ giá trị.
