# Thêm một model mới vào ChatLTT — sửa đúng những đâu

> Tài liệu này là **lời hứa của kiến trúc**, và `tests/test_626_chatltt_mo_rong_bang_fixture.py`
> giữ nó: nếu một ngày thêm model đòi sửa nhiều hơn danh sách dưới đây, phép
> kiểm ở đó đỏ trước khi ai kịp quen với việc sửa thêm.

## Điều KHÔNG phải sửa

⛔ **`frontend/chatltt/` — không một dòng nào.** Bộ chọn model đọc
`NangLuc.models`; nút đính ảnh bật theo `constraints.reads_images`; nút tạo tắt
theo `san_sang`. Không có `if <tên model>` ở đâu, và `test_626` quét mã để chốt
điều đó.

⛔ **`apps/chatltt/` — cũng không**, trừ đúng **một dòng** trong
`services/chinh_sach.py` khi thêm một **năng lực** mới (không phải khi thêm một
alias vào năng lực đã có).

⛔ **`platform_core/runtime_noi_bo/`** — nó không biết tên app nào, và phải giữ
nguyên như vậy (`test_60` chốt).

---

## 1. Thêm một alias TEXT mới (vd một bản Qwen ngữ cảnh dài)

Sửa **một chỗ**: `apps/ltt_llm/manifest.py`, khối `api_contract["models"]`.

```python
"models": {
    "ltt_llm": {...},
    "ltt_llm_dai": {                       # ← alias CÔNG KHAI, khách ghim vào đây
        "id": "qwen38-dai",                #    id nội bộ, KHÔNG bao giờ rời nền tảng
        "stability": "experimental",       #    stable | experimental | deprecated
        "description": "Cửa sổ rất dài, sinh chậm hơn.",
        "constraints": {
            "context_window": 200_000,     #    lấy từ `ngan_sach.py`, đừng gõ tay
            "max_output_tokens": 8_192,
            "reads_images": True,          #    có ⇒ giao diện bật nút đính ảnh
        },
    },
},
"enums": {"model": [..., "ltt_llm_dai"]},
```

Rồi `apps/ltt_llm/features.py`: thêm `ALIAS_SANG_ID["ltt_llm_dai"] = "qwen38-dai"`,
và `ngan_sach.py` nếu model mới có cửa sổ khác.

**Xong.** Alias xuất hiện trong bộ chọn, trong `/api/v1/models`, và trong trang
tài liệu — cùng lúc, từ cùng một bản khai.

⚠️ `stability="deprecated"` **bắt buộc** kèm `replaced_by`: một alias đang chết mà
không nói đi đâu là báo cho khách rằng tích hợp của họ sắp hỏng và không nói gì thêm
(`registry._validate_model_aliases` từ chối nạp nếu thiếu).

---

## 2. Thêm một model ẢNH mới

Cùng cách, ở `apps/anhnoibo/manifest.py`. Nếu giá đổi theo model thì
`apps/anhnoibo/gia.py` — **và chỉ ở đó**: trang giá công khai, báo giá của
ChatLTT và hoá đơn đều đọc cùng một hàm (`AppManifest.bang_gia`).

---

## 3. Thêm một engine/nhà cung cấp GIỌNG mới

`apps/ltt_voice/`. Ba thứ hợp đồng cần nhớ:

| Thứ | Ở đâu | Vì sao |
|---|---|---|
| `suc_khoe` | `manifest.py` | catalog nói được "chưa sẵn sàng" mà không import app |
| `tuy_chon_dong` | `ToolSpec` | giọng **của chính người dùng** lên được palette mà không import app |
| `so_lan_thu` | `manifest.py` | nạp model lúc deploy lâu hơn cửa sổ thử lại mặc định |

`voice_id` là **danh tính công khai ổn định**: đổi engine thì thêm một dòng
`voice_repr` và đổi cờ `active`, **không** đổi `voice_id`. Đó là toàn bộ lý do
bảng giọng tách làm bốn (`apps/ltt_voice/tables.py`).

---

## 4. Thêm một PHƯƠNG THỨC mới (vd video)

Đây là việc lớn nhất, và cố ý:

1. App sở hữu khai `ToolSpec` với `returns={"video_key": "video"}`.
2. `apps/chatltt/services/chinh_sach.py`:
   - thêm tên vào `CONG_CU_CHO_PHEP` — **một quyết định sản phẩm**, không phải
     một công tắc vận hành;
   - thêm `"video"` vào `PHUONG_THUC_HIEN_THI`.
3. `apps/chatltt/services/tao_media.py`: thêm `"video": "video"` vào
   `KHOI_THEO_PHUONG_THUC`, và `kiem_so_huu_khoa` thêm **một hình khoá** — không
   nới lỏng phép kiểm đang có.
4. `apps/chatltt/tables.py`: thêm `"video"` vào `LOAI_KHOI`.
5. `frontend/chatltt/src/ThongDiepView.tsx`: thêm nhánh vẽ `<video>`.

⭐ Trước bước 2, năng lực ấy **không hiện và không gọi được** — kể cả khi nó đã
nằm trong allowlist. `test_626::test_phuong_thuc_la_khong_hien_va_khong_goi_duoc`
chốt điều đó: một phương thức bộ hiển thị không vẽ được thì **fail-closed**, chứ
không hiện ra một ô trống.

---

## 5. Điều gì xảy ra khi model KHÔNG khả dụng

Không phải một trường hợp riêng — nó là đường chạy bình thường:

- `AppManifest.suc_khoe()` trả `chua_san_sang` ⇒ `NangLuc.san_sang` nói vậy ⇒
  giao diện tắt nút và ghi lý do trên `title`.
- Hook **ném**, trả giá trị lạ, hay app `enabled=False` ⇒ cũng `chua_san_sang`.
  Fail-closed có chủ ý: "không biết" phải hiện ra là "chưa sẵn sàng", không phải
  một chip xanh (bài học `ltt_voice` 02/09 — chip xanh trên một trang mà mọi lượt
  đều hỏng).
- **Bận** (429) thì khác: nó là trạng thái của một **lượt gọi**, không phải của
  cổng. Catalog không đoán trước; cửa gọi báo `DangBan` kèm `retry_after_s`.
