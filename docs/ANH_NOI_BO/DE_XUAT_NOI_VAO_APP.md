# Nối model nội bộ vào app — hai đường, chờ duyệt

**22/08/2026 · cần chủ dự án chọn · chưa động vào app nào**

---

## Vấn đề

Bộ máy H37 đã liền mạch tới tận cổng render trên máy B. Nhưng **không app nào gọi
tới nó được**, vì hai lý do:

**① Mọi app ảnh khai cứng provider.**

```python
# apps/taoanh/manifest.py, apps/thumbnail/manifest.py
"model": {"type": "model_ref", "category": "image", "providers": ["gemini"]}
```

Cắm khoá `ltt_image` vào admin cũng không có chỗ nào hiện nó ra.

**② Mỗi app tự gọi thẳng HTTP của Gemini.**

`apps/taoanh/jobs.py` và `apps/thumbnail/jobs.py` **mỗi app có một hàm `_goi_gemini`
riêng**, tự dựng URL `generateContent`, tự lấy key, tự xử lỗi. Không có tầng chung
nào. Đây là **nợ kỹ thuật đã có sẵn**, không phải do H37 sinh ra — nhưng H37 là lúc
nó thành vật cản.

---

## Đường A — sửa từng app

**Làm gì:**

1. `apps/taoanh/manifest.py`: `providers: ["gemini", "ltt_image"]`
2. `apps/taoanh/jobs.py`: thêm một nhánh

```python
if provider_cua(model) == "ltt_image":
    kq = dieu_phoi.DieuPhoi(...).chay(...)
else:
    img = _goi_gemini(...)          # đường cũ, không đụng
```

3. Lặp lại y hệt cho `thumbnail`, và cho mọi app ảnh sau này.

| | |
|---|---|
| **Được** | Đường Gemini đang phục vụ khách **không bị đụng một dòng nào**. Hỏng thì chỉ hỏng đúng app đó. Lùi lại dễ. |
| **Mất** | Nhánh rẽ **nhân bản ở mỗi app**. App thứ ba chép lần thứ ba. Hai hàm `_goi_gemini` trùng nhau vẫn nằm đó. Sửa một lỗi ở đường nội bộ phải sửa ở N chỗ. |
| **Rủi ro** | thấp |
| **Công** | ~1 buổi cho `taoanh`, ~1 buổi cho `thumbnail` |

---

## Đường B — dựng tầng sinh ảnh dùng chung

**Làm gì:**

1. Thêm `platform_core/image_gen/sinh_anh.py` — **một cửa duy nhất**:

```python
def sinh(db, storage, *, model_id, prompt, so_anh, refs=(), ...) -> KetQuaAnh:
    """Định tuyến theo provider của `model_id`. App KHÔNG cần biết provider nào."""
```

2. `taoanh` gọi `sinh_anh.sinh(...)` thay cho `_goi_gemini(...)`.
3. Ít lâu sau, `thumbnail` cũng vậy.
4. Thêm provider ảnh thứ ba sau này = **sửa đúng một tệp**, không sửa app nào.

| | |
|---|---|
| **Được** | Một chỗ duy nhất. Dọn luôn hai bản `_goi_gemini` trùng nhau. Đúng quy tắc *"việc dùng chung thì gọi `platform_core`, đừng chép lại"*. Mọi app sau chỉ khai model là chạy. |
| **Mất** | **Đụng vào app đang ra tiền.** Diff lớn hơn. Cần test kỹ đường Gemini để chắc không đổi hành vi. |
| **Rủi ro** | trung bình — quản được bằng cách làm từng bước |
| **Công** | ~1 buổi dựng tầng chung + ~1 buổi mỗi app |

---

## Khuyến nghị: **đường B, làm bốn bước**

Lý do không phải "B đẹp hơn". Lý do là: **đường A biết chắc sẽ phải làm lại.** Ta đã
có hai bản `_goi_gemini` trùng nhau; đường A thêm hai nhánh rẽ trùng nhau nữa. Đó là
đúng thứ mà `H22` (rà soát hệ điều hành) đã phải đi dọn một lần.

Bốn bước, **không lúc nào app đang chạy bị thay ruột một lần**:

| Bước | Việc | App khách đang dùng |
|---|---|---|
| **B1** | Dựng `sinh_anh.py` + test, **chưa app nào gọi** | không đụng |
| **B2** | `taoanh` gọi tầng chung, **chỉ đường Gemini** — hành vi phải y hệt trước | đổi ruột, giữ nguyên bề ngoài |
| **B3** | Mở `ltt_image` cho `taoanh`, **`is_active` vẫn tắt** | không đổi với khách |
| **B4** | Sau khi `taoanh` chạy ổn định, chuyển `thumbnail` | |

**Chốt an toàn cho B2** — bước rủi ro nhất: trước khi đổi, ghi lại thân yêu cầu mà
`_goi_gemini` hiện gửi đi; sau khi đổi, so **từng trường** phải trùng khớp. Không so
"ảnh có ra không" — so **thứ gửi lên Gemini**, vì đó mới là thứ quyết định.

---

## Ba việc chỉ mở được sau khi anh duyệt

| | Chặn bởi |
|---|---|
| Chạy một job ảnh **thật** từ đầu tới cuối | phải có app gọi |
| Định giá credit cho model nội bộ | phải biết app nào bán nó |
| Cổng chất lượng G6b (so mù với Gemini) | cần đường sinh ảnh chung để so cùng điều kiện |

---

## Nếu anh chọn A

Tôi làm ngay và không bàn thêm — nó **không sai**, chỉ là nợ lại một lần dọn. Với
một sản phẩm cần ra mắt nhanh thì đó có thể là đánh đổi đúng.
