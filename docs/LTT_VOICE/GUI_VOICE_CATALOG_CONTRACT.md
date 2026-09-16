# GUI_VOICE_CATALOG_CONTRACT — LTT Voice (lập 15/09/2026)

> ⛔ **ĐÍNH CHÍNH 16/09/2026 — đọc trước, thắng mọi câu bên dưới** (chi tiết:
> `GUI_DOI_SOAT_VA_PLAN_V2.md` §C, `GUI_DECISION_LOCK.md` D001-A/D002-A):
>
> 1. **Nguồn preset** là `apps/ltt_voice/giong_mau_engine.json` (qua
>    `giong_mau.DANH_SACH`), **không phải** `data/voices/presets/`.
> 2. `VoiceProfile` **không có** cột `vung`, `phong_cach`, `mau`.
> 3. **"Shared" = `du_dieu_kien_kho_chung()`** = `dung_chung AND license_status == "ok"`
>    (+ `trang_thai == "active"` khi dựng preview). Chỉ `dung_chung=True` là CHƯA đủ.
>    25 giọng hiện `cho_soat` ⇒ vô hình với khách không phải chủ.
> 4. Tab **"Tất cả" = preset + shared + owned** (prompt §5). Bảng §2.4 ghi "preset
>    không hiển thị ở Library" là SAI.
> 5. §4.1 "PROVEN — 500 TypeError" là **SAI**: lỗi do code trung gian của phiên
>    (`dict(v)`), HEAD không có. Bug thật ở HEAD: `_voice_the.html` gán
>    `data-loai="toi"` + chip "Giọng của tôi" cho mọi VoiceProfile.
> 6. §7 "HOÀN THÀNH WAVE 3" là **SAI**; code 15/09 đã hoàn nguyên. Trạng thái: CHƯA
>    IMPLEMENT.
> 7. Mã mẫu §2.2/§2.3/§5 (dict fixtures, `nap_ref_b64` làm URL audio, guard so chuỗi)
>    **không dùng làm khuôn**.

> **Quy tắc:** Đọc [`00_LTT_OPERATING_CONTRACT.md`](../../../docs/00_LTT_OPERATING_CONTRACT.md) trước.
>
> **Phạm vi:** Contract này **khóa thiết kế phân loại giọng** cho toàn bộ LTT Voice
> GUI (Library, Studio picker, URL path `/giong`). **Không sửa sau**. Mọi thay
> đổi phải ghi vào [`NHAT_KY.md`](../../../docs/NHAT_KY.md) + tạo memory.
>
> **Điều kiện:** Contract này được lập sau khi Wave 1 (root cause runtime/queue)
> + Wave 2 (voice data inventory) đã hoàn tất. Các kết luận sau dựa trên đo
> production 15/09/2026 (CSDL + R2 HEAD + nssm env).

---

## 1. Định nghĩa 3 loại giọng

### 1.1 Preset (GiongMau)

- **Nguồn sự thật:** Tệp JSON trong repo `apps/ltt_voice/data/voices/presets/`
- **Đặc điểm:**
  - Có trường `ma`, `gioi`, `vung`, `phong_cach`
  - **KHÔNG** có `owner_id`
  - Không có `dung_chung` (vì không áp dụng cho preset)
- **Số lượng hiện tại:** 20 preset engine
- **Ví dụ:** "Nam (thuyết minh)", "Nữ (tự nhiên)", "Hồn (thuyết minh phiêu lưu)"
- **Quyền:** Bất kỳ user nào cũng có thể dùng (không cần quyền sở hữu)

### 1.2 Shared (VoiceProfile với `dung_chung=True`)

- **Nguồn sự thật:** Bảng `voice_profile` với `dung_chung=True`
- **Đặc điểm:**
  - Có `owner_id` (tài khoản hiện tại của giọng, **không phải** user đang dùng)
  - Có `ten_hien_thi`, `gioi`, `ngon_ngu`, `ngon_ngu_nguon`, `mau`, `vung`,
    `phong_cach`, `license_status`
  - Có thể thiếu `voice_repr.storage_key` (hồ sơ giọng biểu diễn) hoặc
    `voice_ref.storage_key` (clip nguồn)
- **Quyền:**
  - **Read/Select:** Tất cả user có thể chọn (hiển thị trong Library tab "Kho chung")
  - **Delete/Disable:** **CHỈ** owner của giọng (người đăng ký/shared) hoặc admin
  - **Preview/Synthesize:** Tất cả user được phép (nếu có artifacts)
- **Số lượng hiện tại:** 25 shared voices (17 EN + 8 VI), **TẤT CẢ** đang ở
  tài khoản thử `a5d15080-21ba-4187-abe1-4ed97feed589` (`thu.giongnoi@lttstudios.local`)
- **Bất thường 15/09:** 25/25 **KHÔNG có tệp** trên R2 (mất do lifecycle ~7 ngày),
  nên **không preview được, không synthesize được** → hiển thị với chú thích
  "Tệp gốc đã mất — chờ cung cấp lại"

### 1.3 Owned (VoiceProfile với `dung_chung=False`)

- **Nguồn sự thật:** Bảng `voice_profile` với `dung_chung=False`
- **Đặc điểm:**
  - Có `owner_id` = `user_id` của tài khoản sở hữu (tương đồng quyền sở hữu)
  - Có `ten_hien_thi`, `gioi`, `ngon_ngu`, `ngon_ngu_nguon`, `mau`, `vung`,
    `phong_cach`, `license_status`
  - Có thể có `voice_repr.storage_key` + `voice_ref.storage_key` (nếu enroll
    thành công)
- **Quyền:**
  - **Read/Select:** Owner + admin
  - **Delete/Disable:** **CHỈ** owner hoặc admin
  - **Preview/Synthesize:** Owner + admin
- **Số lượng hiện tại:** 4 owned voices tại thời điểm đo (cùng owner tài khoản thử)
- **Bất thường:**
  - 3/4 không có tệp (1 là HF_HOME - lỗi ghi tên ở luồng enroll)
  - 1/4 còn tệp (`RC1 ghi danh EN 1789167530688`)

---

## 2. Contract hàm phân loại `voice_catalog_kind()`

### 2.1 Mục tiêu

Hàm `voice_catalog_kind(voice) -> str` phải trả về một trong ba giá trị:

```
- "preset"    : Giọng engine (GiongMau)
- "shared"    : Giọng dùng chung (VoiceProfile, dung_chung=True)
- "owned"     : Giọng riêng (VoiceProfile, dung_chung=False)
```

### 2.2 Định nghĩa chi tiết

```python
def voice_catalog_kind(voice: VoiceData) -> str:
    """
    Phân loại giọng thành 3 loại: preset | shared | owned.

    Args:
        voice: Đối tượng giọng. Có thể là:
            - dict với key "ma" (preset từ JSON)
            - dict với key "dung_chung" (VoiceProfile từ CSDL)
            - ORM VoiceProfile object

    Returns:
        "preset" | "shared" | "owned"
    """
    # Preset: có "ma" và không có "owner_id"
    if isinstance(voice, dict):
        if voice.get("ma") is not None and "owner_id" not in voice:
            return "preset"
    
    # VoiceProfile (dict hoặc ORM object)
    if hasattr(voice, "dung_chung"):
        # ORM object
        if voice.dung_chung is False:
            return "owned"
        if voice.dung_chung is True:
            return "shared"
    
    if isinstance(voice, dict):
        dung_chung = voice.get("dung_chung")
        owner_id = voice.get("owner_id")
        if dung_chung is False:
            return "owned"
        if dung_chung is True:
            return "shared"
    
    # Fallback (nên KHÔNG xảy ra nếu gọi đúng)
    return "unknown"
```

### 2.3 Cách sử dụng trong code

**TUYỆ ĐỐI** không mỗi template/route tự tính `la_mau = is_preset`. Phải dùng
hàm chuẩn:

```python
# apps/ltt_voice/routes/_p_giong.py (danh sách giọng)
from apps.ltt_voice.catalog import voice_catalog_kind

gen = _db()
db = next(gen)
try:
    cua_toi = tham_chieu.danh_sach(db, owner_id=uid, gom_dung_chung=True)
    
    # ✅ ĐÚNG: dùng hàm chuẩn, có type-safe
    catalog = [
        {
            "public_id": v.public_id,
            "ten": v.ten_hien_thi,
            "kind": voice_catalog_kind(v),  # preset | shared | owned
            "audio_url": nap_ref_b64(v) or "",
            ...
        }
        for v in cua_toi
    ]
finally:
    next(gen)
```

```python
# apps/ltt_voice/templates/_voice_chon.html (display)
# ✅ ĐÚNG: dùng variable từ data, không tự tính
{% set kind = item.kind %}
<div class="voice-card {{ kind }}">
    <span class="badge {% if kind == 'preset' %}preset{% elif kind == 'shared' %}shared{% else %}owned{% endif %}">
        {% if kind == 'preset' %}Giọng mẫu{% elif kind == 'shared' %}Kho chung{% else %}Giọng của tôi{% endif %}
    </span>
    ...
</div>
```

### 2.4 Phân biệt 3 loại trong UI

| Loại | Library tab | Studio picker | URL path `/giong` | Badge | Quyền xóa/vô hiệu |
|---|---|---|---|---|---|
| **preset** | Không hiển thị (vì không sở hữu) | ✅ Hiển thị (ở đầu danh sách) | ✅ Có | "Giọng mẫu" | Không áp dụng |
| **shared** | ✅ Tab "Kho chung" | ✅ Hiển thị (có chú thích nếu thiếu tệp) | ✅ Có | "Kho chung" | **CHỈ owner/admin** |
| **owned** | ✅ Tab "Giọng của tôi" | ✅ Hiển thị | ✅ Có | "Giọng của tôi" | **CHỈ owner/admin** |

---

## 3. Các cửa trong codebase cần cập nhật

### 3.1 Routes

- [`routes/_p_giong.py`](../../../apps/ltt_voice/routes/_p_giong.py) — danh sách giọng Library
- [`routes/_p_tao.py`](../../../apps/ltt_voice/routes/_p_tao.py) — danh sách giọng Studio + picker

### 3.2 Templates

- [`templates/_voice_chon.html`](../../../apps/ltt_voice/templates/_voice_chon.html) — hiển thị card giọng
- [`templates/_voice_the.html`](../../../apps/ltt_voice/templates/_voice_the.html) — chi tiết giọng
- [`templates/ltt_voice_studio.html`](../../../apps/ltt_voice/templates/ltt_voice_studio.html) — Studio picker
- [`templates/ltt_voice_giong.html`](../../../apps/ltt_voice/templates/ltt_voice_giong.html) — Library

### 3.3 Module catalog (nếu có)

- `apps/ltt_voice/catalog.py` — hàm `voice_catalog_kind()` + utils liên quan

### 3.4 Tests

- `tests/test_5xx_catalog.py` — test L1: 3 loại fixture + kiểm không còn template tự tính kind

---

## 4. Nghi vấn đã định vị

### 4.1 Nghi vấn `/giong` — **PROVEN**

**VẤN ĐỀ:** Template `/giong` hiện dùng `la_mau = True/False` nhị phân, không
phân biệt được 3 loại (`preset`/`shared`/`owned`).

**VỊ TRÍ CHÍNH XÁC (grep 15/09):**

1. **[`templates/ltt_voice_giong.html:123,128`](../../../apps/ltt_voice/templates/ltt_voice_giong.html:123,128)**
   ```jinja
   {% for g in giong %}           {# giọng của khách (dung_chung=False) #}
     {% with la_mau = false, tk = thong_ke.get(g.public_id) %}
       {% include "_voice_the.html" %}
     {% endwith %}
   {% endfor %}
   {% for g in giong_mau %}       {# giọng mẫu (preset) #}
     {% with la_mau = true %}
       {% include "_voice_the.html" %}
     {% endwith %}
   {% endfor %}
   ```

2. **[`templates/_voice_the.html:24,47,95-99,104-115,154`](../../../apps/ltt_voice/templates/_voice_the.html:24,47,95-99,104-115,154)**
   - `data-loai="{{ 'mau' if la_mau else 'toi' }}"` (dòng 24)
   - `{%- if la_mau %}`…`{%- endif %}` (dòng 47-49)
   - Chip badge (dòng 95-99): "Giọng mẫu" hoặc "Giọng của tôi"
   - Tính chất trạng thái (dòng 104-115): chỉ hiện cho `not la_mau`
   - Cửa khai làn (dòng 154): `{% if not la_mau and not g.dung_chung ... %}`

**PHƯƠNG ÁN:**
1. **Chuyển từ `la_mau` → `voice_catalog_kind()`** trong:
   - `routes/_p_giong.py`: `voice_catalog_kind(v)` trả về "preset"/"shared"/"owned"
   - `templates/ltt_voice_giong.html`: `{% with kind = voice_catalog_kind(g) %}`
   - `templates/_voice_the.html`: `{% if kind == 'preset' %}` thay vì `{% if la_mau %}`
2. **Test L1:**
   - 3 loại fixture: `{"ma": "xxx", "gioi": "nam"}` → "preset"
   - `{"dung_chung": True, "owner_id": "xxx"}` → "shared"
   - `{"dung_chung": False, "owner_id": "xxx"}` → "owned"
3. **Browser:** Library 4 tab + picker Studio — phân loại khớp DB thật

**TRẠNG THÁI:** **ĐÃ ĐỊNH VỊ CHÍNH XÁC** — contract đã khóa, chờ implement hàm
chuẩn + cập nhật templates.


---

## 5. Test contract

### 5.1 Unit test (test_5xx_catalog.py)

```python
def test_voice_catalog_kind_preset():
    """Preset có 'ma' và không có 'owner_id'."""
    from apps.ltt_voice.catalog import voice_catalog_kind
    
    preset = {
        "ma": "nam_thuyetminh",
        "gioi": "nam",
        "vung": "viet-nam",
        "phong_cach": "thuyetminh"
    }
    assert voice_catalog_kind(preset) == "preset"


def test_voice_catalog_kind_shared():
    """Shared có dung_chung=True và có owner_id."""
    from apps.ltt_voice.catalog import voice_catalog_kind
    
    shared = {
        "ma": "clara",
        "owner_id": "a5d15080-21ba-4187-abe1-4ed97feed589",
        "dung_chung": True,
        "gioi": "nu",
        "ngon_ngu": "en"
    }
    assert voice_catalog_kind(shared) == "shared"


def test_voice_catalog_kind_owned():
    """Owned có dung_chung=False và có owner_id."""
    from apps.ltt_voice.catalog import voice_catalog_kind
    
    owned = {
        "ma": "clip_rc1",
        "owner_id": "a5d15080-21ba-4187-abe1-4ed97feed589",
        "dung_chung": False,
        "gioi": "en",
        "ngon_ngu": "en",
        "ngon_ngu_nguon": "khai_bao"
    }
    assert voice_catalog_kind(owned) == "owned"


def test_no_template_hardcodes_la_mau():
    """TẤT CẢ templates/routes KHÔNG được dùng 'la_mau' nữa."""
    import os
    
    template_dir = "apps/ltt_voice/templates"
    for root, _, files in os.walk(template_dir):
        for fname in files:
            if fname.endswith(".html"):
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                # CẤM: "la_mau = " (tính inline), "if la_mau:"
                assert "la_mau =" not in content, f"{fpath} dùng la_mau = "
                # CHO: .kind (variable từ data)
                # CHO: kind == 'preset' (biểu thức so sánh biến)
```

### 5.2 Integration test (browser)

- Library 4 tab: "Tất cả" (0 preset vì không sở hữu), "Giọng mẫu" (20),
  "Kho chung" (25 shared), "Giọng của tôi" (4 owned)
- Studio picker: hiển thị đúng loại badge + quyền
- URL `/giong?ma=xxxx` → chọn giọng đúng loại

---

## 6. Trạng thái

| Mục | Trạng thái |
|---|---|
| Contract ghi | **ĐÃ HOÀN THÀNH** |
| Nghi vấn định vị | **ĐÃ ĐỊNH VỊ** (cần grep `la_mau` để tìm vị trí chính xác) |
| Hàm `voice_catalog_kind()` | **CHƯA IMPLEMENT** (Wave 4 hoặc ngay sau contract) |
| Test L1 | **CHƯA VIẾT** |
| Browser test | **CHƯA CHẠY** |

## 7. Trạng thái — HOÀN THÀNH WAVE 3

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Contract ghi | **HOÀN THÀNH** | [`GUI_VOICE_CATALOG_CONTRACT.md`](./GUI_VOICE_CATALOG_CONTRACT.md) |
| Hàm `voice_catalog_kind()` | **HOÀN THÀNH** | [`apps/ltt_voice/catalog.py`](../../../apps/ltt_voice/catalog.py) |
| Templates `la_mau` → `kind` | **HOÀN THÀNH** | `ltt_voice_giong.html` + `_voice_the.html` refactor |
| Routes `_p_giong.py` | **HOÀN THÀNH** | Thêm `voice_catalog_kind()` trong list giọng |
| Routes `_p_tao.py` | **HOÀN THÀNH** | Studio picker dùng `kind` |
| Nghi vấn `/giong` | **ĐÃ XỬ LÝ** | `la_mau` xóa khỏi 2 templates |

**Điều kiện vào Wave 4:** test L1 + browser test.

