# Chuỗi prompt + ảnh/video — WanGP so với BytePlus, và luật cho GUI

**07/09/2026** · đo trên `metadata` thật (SHA `1e1dd275`) và đọc thẳng `wgp.py`.

---

## 0. Kết luận trước, chứng cứ sau

🔴 **Hai engine dùng hai mô hình khác nhau về bản chất. Chép cơ chế tag của
   BytePlus sang WanGP không phải "chưa tối ưu" — nó có hại.**

| | BytePlus / Seedance | WanGP |
|---|---|---|
| Cấu trúc | **mảng `content[]` có thứ tự** | **khe có tên** trong `settings` |
| Chọn vai trò | trường `role` trên từng phần tử | **cờ chữ cái** `image_prompt_type` · `video_prompt_type` |
| Trỏ từ prompt | `@IMG_1`, `@VID_1` — **theo thứ tự** | **không có** |
| Nhiều ảnh | có, tới 4 tài sản | tuỳ model; hai model của ta **không** |

---

## 1. BytePlus: prompt trỏ tới ảnh bằng **vị trí**

Đọc `apps/taovideo/refs.py`:

```python
content = [{"type": "text", "text": normalize_tags(prompt, refs)}]
for ref in refs:
    content.append(_ref_to_part(ref))      # image_url / video_url / audio_url
```

- Mỗi ảnh mang `role` ∈ `{reference_image, first_frame, last_frame, mask}`
- `@handle` người dùng đặt (vd `@swat`) được **viết lại** thành `@IMG_n`
- `n` = thứ tự **trong cùng loại**, theo đúng thứ tự phần tử trong `refs`

⇒ **Thứ tự tải lên chính là địa chỉ.** Đổi thứ tự là đổi nghĩa của prompt.

---

## 2. WanGP: khe có tên, bật bằng cờ chữ cái

Không có mảng. Có các khoá settings rời:

```
image_start · image_end · image_refs · image_guide · image_mask
video_guide · video_guide2 · video_mask · video_source
audio_guide · audio_guide2 · audio_source
```

Khe nào **được đọc** thì do cờ quyết định (`wgp.py`):

| Cờ | Khe | Dòng |
|---|---|---|
| `image_prompt_type` chứa `S` | `image_start` | 1437 |
| `image_prompt_type` chứa `E` | `image_end` | 1460 |
| `video_prompt_type` chứa `I` | `image_refs` — *"You must provide at least one Reference Image"* | 1370 |
| `video_prompt_type` chứa `V` | `video_guide` / `image_guide` | 1381 |
| `video_prompt_type` chứa `A` | `video_mask` / `image_mask` (kèm `U` cho biến thể) | 1390 |
| `video_prompt_type` chứa `G` | bật `denoising_strength` | 1401 |
| `video_prompt_type` chứa `K` | khung nền tham chiếu | `replace("I","KI")` |

### 🔴 Hai cái bẫy trong chính cơ chế cờ

**1. `E` một mình bị gỡ ÂM THẦM.** `wgp.py:1458`:

```python
if not end_frames_always_enabled(model_def) and not any_letters(image_prompt_type, "SVL"):
    image_prompt_type = image_prompt_type.replace("E", "")
```

⇒ "chỉ khung cuối" **không tồn tại**. Muốn khung cuối thì phải có khung đầu ⇒
  cần **hai** ảnh. Ta nhận một tệp, nên ô chọn vai trò đầu/cuối là một nút không
  làm gì.

**2. Cờ đúng mà model không khai thì lỗi.** `"E" in image_prompt_types_allowed`,
   `"I"` đòi `media_inputs.image.reference`. Cờ là **điều kiện cần**, khai báo
   của model là **điều kiện đủ**.

---

## 3. ⛔ WanGP **không có** tag trong prompt — và tag sẽ làm hỏng prompt

Đếm trên toàn bộ `docs/API.md` và `wgp.py` (825 KB):

```
@IMG · @image · "prompt tag" · @ref     →  0 lần
```

Prompt của WanGP đi thẳng vào bộ mã hoá văn bản **T5**
(`models/wan/modules/t5.py`). Một chuỗi `@IMG_1` nằm trong đó **không** được
diễn giải — nó được **mã hoá như chữ thật**, và trở thành nhiễu trong chính câu
mô tả.

⇒ Chép `@tag` sang đây không phải "thừa mà vô hại". Nó **làm xấu kết quả**.

---

## 4. Hai model của ta khai gì — đo, không suy

```
t2v_2_2   image: (khong co khe nao)     video: continue · last · control · mask
i2v_2_2   image: start · end            video: continue · last · control · mask
audio: khong model nao
```

Ba hệ quả:

1. **`t2v_2_2` không nhận ảnh.** Đính ảnh ⇒ phải đổi sang `i2v_2_2`. Đó chính
   là việc `ho_so.MODEL_THEO_DAU_VAO` + `chon_model.kiem_model` đang làm.
2. **Không model nào có khe `reference`.** Trường hợp dùng chính của `@tag`
   Seedance — "gọi tên nhân vật trong prompt" — **không tồn tại** với bộ model
   này. Nó tồn tại ở WanGP (VACE), chỉ là không ở đây.
3. **Cả hai model NHẬN video** ở bốn vai trò. Ta chưa dùng được vì chưa có hồ sơ
   tham số cho đường đó — và hồ sơ phải **rút từ máy thật**, không gõ tay.

---

## 5. 🔴 Lỗi tìm được nhờ chính phép đo này

Ô chọn tệp khai `accept="…,video/mp4"`, trong khi `ho_so.HO_SO_THEO_DAU_VAO`
**không có** mục `"video"`. Đường đi thật của một người dùng tải MP4 lên:

```
chon MP4 → nen tang GIU CREDIT → job chay → `jobs.handle` nem
"Loai tep dinh kem nay chua duoc ho tro" → credit duoc hoan
```

Tiền trả lại, nhưng **thời gian và niềm tin thì không**. Và cái sai **không nằm
ở job** — job từ chối là đúng. Cái sai là **cửa trước** mời người ta vào một
cánh cửa khoá.

⇒ Ô chọn tệp nay chỉ nhận ảnh; `_luu_media` từ chối video **kèm lý do**
  (*"Video làm đầu vào chưa mở"*), để một request gõ tay cũng nhận câu trả lời
  tử tế. `test_729` chốt bất biến: **mọi MIME ô chọn tệp mời phải có một hồ sơ
  nhận được nó** — đã đối chứng bằng cách mở lại MP4 và xác nhận đỏ.

---

## 6. Luật cho GUI — chuỗi đúng cho engine NÀY

| Đầu vào | Model | Khe | Cờ |
|---|---|---|---|
| chỉ chữ | `t2v_2_2` | — | — |
| chữ + **một** ảnh | `i2v_2_2` | `image_start` | `image_prompt_type = "S"` |
| chữ + video | *(chưa mở)* | `video_guide` | `video_prompt_type` chứa `V` |

**Bốn luật rút ra:**

1. **Không tag, không `@handle`.** Không có gì để trỏ tới, và tag làm nhiễu T5.
2. **Một tệp, một khe.** Đính ảnh nghĩa là *khung mở đầu* — nói thẳng câu đó
   trên nhãn, đừng để người dùng đoán.
3. **Ô chọn tệp không được mời thứ đường job từ chối.** Cửa trước phải khớp cửa
   sau; có phép kiểm canh.
4. **Mở thêm khe là rút thêm hồ sơ**, không phải thêm một ô nhập. Hồ sơ rút từ
   máy thật, ghim theo SHA — cùng luật đã áp cho hai hồ sơ hiện có.

## 7. Thứ đáng làm khi pod sống lại

- Rút hồ sơ `video_guide` (`video_prompt_type = "V"` + `denoising_strength`)
  ⇒ mở đường video, và ô chọn tệp nhận lại MP4 **cùng lúc** với hồ sơ ấy.
- Kiểm `image_prompt_types_allowed` của `i2v_2_2` trên máy thật. Nếu có `E` thì
  mở **hai** ô ảnh (đầu + cuối) — không phải một ô có ô chọn vai trò.
- `|start_frame=…,end_frame=…` của WanGP cho phép nhắm một đoạn khung mà không
  cắt clip trước. Đây là thứ đáng đưa lên giao diện khi mở đường video.
