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
