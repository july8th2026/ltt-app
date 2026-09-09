# Pha 15 — báo cáo nén kho, và những gì KHÔNG được nén vào một con số

**Ngày:** 2026-09-10 · chiến dịch **LTT AI CLEAN REBUILD V2**
**Trunk khi đóng:** `admin-mvp-v3` · **Production:** `84661047c2ae`

---

## 1. Cái đã gỡ — đo có phạm vi

```
21 tep xoa han      2.978 dong
```

⛔ **Con số ấy KHÔNG phải `git diff --shortstat` của cả nhánh.** Nhánh
`phien/aiclean` mang **51 commit** kể từ nền `0d1ffe5a`, trong đó chỉ khoảng
mười lăm là của chiến dịch này — số còn lại là LTT VOICE, WORKFLOW V2, VPS V2.
Lấy `328 files changed, +29.153/−5.524` rồi gán cho chiến dịch là **nhận công
của bốn phiên khác**, và tôi đã suýt làm đúng điều đó ở pha 12 khi một nền so
sánh quá rộng biến `frontend/agent-canvas/src/workflowApi.ts` của WORKFLOW V2
thành "một lỗ hổng của pha 08".

| Đã gỡ | |
|---|---|
| `apps/chataistudio/` | 9 tệp — bản chất là chat gọi ra pool Codex bên ngoài |
| `codex_sidecar/` + `codex_sidecar_main.py` | sidecar Codex |
| `platform_core/image_gen/dich_gemini.py` | lớp dịch prompt qua Gemini |
| `tools/doi_chung_gemini.py` · `tools/import_api_keys_from_botgemini.py` | công cụ đối chứng + nhập khoá |
| 6 tệp test của các đường đã gỡ | `test_83` · `118` · `119` · `162` · `251` · `255_doi_chung` |
| **4 nhà cung cấp** trong `providers.py` | `gemini` · `apiai` · `cheapkeyai` · `plenx` |
| **1 dịch vụ Windows** trên máy chủ | `LTTStudioCodex` |
| **3 khoá chết** trong `secrets\app.env` | `LTT_CODEX_SIDECAR_TOKEN` · `LTT_CODEX_SIDECAR_PORT` · `CODEX_SERVER_HOME` · và `GEMINI_API_KEY` |
| **4 khoá API đang SỐNG** trong CSDL production | `apiai` ×1 · `cheapkeyai` ×2 · `gemini` ×1 |

---

## 2. Thứ CỐ Ý giữ, và lý do là **cơ học** chứ không phải tình cảm

Bốn nhà cung cấp trên còn đúng ba dòng: `id`, `display_name`, `is_active=False`.
Không `base_url`, không `auth_style`, không `list_models_path`, không một
`ModelInfo` nào — tức **không còn mẩu công thức nào để dựng lại một lượt gọi**,
kể cả khi ai đó có sẵn khoá API.

Vì sao không xoá nốt ba dòng ấy:

```python
def da_ngung(provider_id):
    p = REGISTRY.get(provider_id)
    return p is not None and not p.is_active     # VANG MAT => False
```

⇒ Xoá hẳn dòng đăng ký thì `chan_neu_da_ngung("gemini")` **thôi ném**, tức cổng
fail-closed của pha 04 **im lặng mở ra**. Ở đây, xoá nốt dòng cuối không làm hệ
thống sạch hơn — nó gỡ mất **lời từ chối**. Cái còn lại không phải một đường
chạy; nó là một tấm biển *"đường này đã đóng"* mà cổng đọc được.

⚠️ **Cái mất, nói thẳng để đảo lại được bằng một commit:** `kling-3.0` và
`seedance-2.0-pro` rời khỏi catalog video khi PLENX nghỉ. BytePlus vẫn phục vụ
`seedance-2.0`, `-fast`, `-mini`, nên nhóm video không chết.

---

## 3. Cái đã CHỨNG MINH, và cái chỉ mới *tin*

| Mệnh đề | Bằng chứng | Hạng |
|---|---|---|
| Không còn lối ra tới 5 host đã gỡ | `test_1007` — bẫy ở tầng **socket** (3 cửa), kèm `test_BAY_that_su_no` | **đo được** |
| 0 occurrence executable trong 787 tệp mã | **hai bộ dò độc lập** (AST và tokenize), không dùng chung một dòng mã | **đo được** |
| `HISTORY_ONLY` không gọi được | `test_1005` — 150 phép kiểm, 5 điều kiện, đọc thẳng ma trận CSV | **đo được** |
| Rào kiến trúc | `test_1006` — 18 phép kiểm, **12 là tự kiểm** (mẫu dương + mẫu âm) | **đo được** |
| LTT_IMAGE sinh thật | job qua Public API → **ảnh 5.519.918 byte**, `held:3 charged:3`, `mode:"live"` | **đo được** |
| LTT_LLM Text | ba cửa `/chat/completions` · `/messages` · `/responses` đều 200 với token thật | **đo được** |
| Seedance/BytePlus | **lời xác nhận của chủ sản phẩm** rằng nó đang chạy thật | ⚠️ **không phải phép đo của chiến dịch** |
| **VLM** | `danh_gia_vision.py --thu-thap` phải chạy **trên máy B** | 🔴 **NOT_TESTED** |
| **Voice** | cần sidecar VOICE + GPU | 🔴 **NOT_TESTED** |

⛔ Hai dòng cuối **ở lại NOT_TESTED**, và trục E2E **không được cộng điểm** vì
Seedance rời khỏi phạm vi. Bỏ bớt một dòng chưa đo không biến những dòng còn lại
thành đã đo; một nghiệm thu tự nâng điểm bằng cách **thu hẹp mẫu số** là một
nghiệm thu đã hỏng.

---

## 4. 🔴 Một lỗ THẬT mà chiến dịch chỉ tìm ra ở phút cuối

Sau khi mọi phép kiểm đã xanh và báo cáo đã viết, việc dọn **dữ liệu** lôi ra
thứ việc dọn **mã** không thấy:

```
apiai      ...KYJs   455 luot   dung cuoi 09/09 15:05:59
cheapkeyai ...3qUP   456 luot   dung cuoi 09/09 23:35:41   <-- dung giay mot job anh
cheapkeyai ...9Dbf   455 luot   dung cuoi 09/09 15:08:57
gemini     ...B3sk   455 luot   dung cuoi 09/09 15:10:54
```

`public_api/capacity.py::_providers_healthy` gọi `api_pool.chon_key()` **không
truyền `thu_tu_provider`**, nên nó quét mọi nhà cung cấp và chọn trúng một khoá
`cheapkeyai` — hàng khoá tự khai `categories` có `image`, **độc lập với Provider
Registry**.

Hậu quả không phải hiệu năng: `_providers_healthy` trả lời câu *"nền tảng còn
phục vụ nhóm này không"*, và câu ấy đi thẳng ra `/api/v1/capacity`. Nền tảng
**chào bán một năng lực không tồn tại**.

⭐ **Bài học của cả chiến dịch nằm ở đây:** mọi phép kiểm đều soi **mã**. Không
   phép kiểm nào soi **hàng trong bảng `api_keys`**. Một chiến dịch xoá provider
   mà chỉ đọc mã sẽ tuyên bố thành công trong khi bốn khoá của chính những
   provider ấy vẫn đang được cấp phát mỗi ngày.

Đã vá ở mã (`tests/test_1008`, 6 phép kiểm, một là đối chứng chạy lại **nguyên
văn thân hàm cũ** trên cùng dữ liệu), và xoá 4 hàng khỏi CSDL (có sao lưu).

---

## 5. Ba việc NGOÀI PHẠM VI — báo cáo, không tự sửa

Gói chiến dịch dặn: *vấn đề ngoài phạm vi thì viết báo cáo, đừng mở rộng chiến
dịch*. Ba thứ dưới đây đều thật, đều không phải việc của chiến dịch này:

1. **`tools/i18n.py thieu` so `mtime`.** Sau bất kỳ lượt `ff`/`merge` nào nó có
   thể báo *"`.mo` cũ hơn `.po`"* thuần tuý vì **thứ tự git ghi hai tệp** —
   chênh lệch đo được là **2,7 mili giây**, trong khi nội dung khớp tuyệt đối
   (3404 msgid, thiếu 0 / thừa 0 / khác 0). Nó **không** phải bước gate
   `dich thieu ban EN` (bước ấy chạy `check_dich_thieu.py`, không đọc mtime).

2. **`tools/nghiem_thu_chat_l1.py` in một mệnh đề SAI.** Nó kết bằng
   *"mỗi cửa phải thu > 0 và khớp với usage báo cáo"* — nhưng chế độ tính tiền
   **mặc định là C3** (tích luỹ phần lẻ, chỉ thu phần nguyên), nên một lượt 67
   token **đúng ra phải thu 0**. Nó không `assert`, nên không đỏ giả; nó chỉ đẩy
   người đọc tới một kết luận sai. Tôi là người đọc ấy, và suýt báo một P0
   doanh thu không tồn tại.

3. **Hai docstring nói ngược nhau về chế độ mặc định.**
   `gia_token._san_moi_luot()` viết *"C1 là mặc định"*; `thanh_toan._san_moi_luot()`
   viết *"Mặc định KHÔNG"*. Hành vi thì nhất quán (cái trước uỷ quyền cho cái
   sau) — chỉ chú thích mâu thuẫn, và nó nằm trong tệp tự nhận là *"chỗ duy nhất
   được phép đại diện cho giá"*.

### Và một phép đo đóng lại nghi vấn "thu 0"

```
mcredit_du = 61        (>0 => phan le DA vao so)
hold -1 / settle +1  x3  => giu 1 credit, hoan 1, rong 0
```

Không có lỗ doanh thu. Kết luận này đến từ **sổ sách production**, không từ một
lần đọc mã.

---

## 6. Nén kho

| | Trước | Sau |
|---|---|---|
| Nhánh remote | 25 | **10** |
| Nhà cung cấp ngoài còn gọi được | 5 | **1** (BytePlus) |
| Khoá API legacy trong CSDL | 4 | **0** |
| Khoá legacy trong `app.env` | 4 | **0** |
| Dịch vụ Windows của đường đã gỡ | 1 | **0** |

Chi tiết pha 14 và sổ khôi phục từng nhánh: `PHA14_DON_NHANH_REMOTE.md`.
