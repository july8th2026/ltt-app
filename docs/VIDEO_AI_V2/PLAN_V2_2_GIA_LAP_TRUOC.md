# V2.2 — Xây trọn bộ trên máy giả lập, pod để cuối

> **Cho phiên thực thi:** đọc hết mục 0–2 trước khi chạm tệp đầu tiên. Các bước
> dùng ô đánh dấu `- [ ]`.

**Mục tiêu:** dựng đủ bộ mã vận hành cho LTT VIDEO trên WanGP — sổ đăng ký model,
danh mục tác vụ, đường ống, GUI — **nghiệm thu toàn bộ mà không cần pod**. Pod và
GPU là hạng mục **cuối cùng**, chỉ để soi lỗi thật.

**Kiến trúc:** một **mối nối** (`apps/lttvideo/cong/`) với hai hiện thực —
`MayThat` (HTTP tới pod) và `MayGiaLap` (phát lại bản ghi). Mọi tầng trên mối nối
không biết mình đang nói chuyện với cái nào.

**Nền tảng:** Python 3.13 · FastAPI · htmx · pytest + xdist · WanGP `1e1dd275`

**Tài liệu gốc:** `docs/VIDEO_AI_V2/CHAM_DIEM_WANGP_VS_SEEDANCE.md` (bảng năng
lực) · `scratchpad/wangp_src/docs_API.md` (hợp đồng API WanGP)

---

## 0. Ràng buộc toàn cục

Áp cho **mọi** hạng mục dưới đây, không nhắc lại.

| | Luật | Vì sao |
|---|---|---|
| **G1** | ⛔ **Không gõ tay một giá trị nào của WanGP.** Mọi năng lực/tham số phải truy được về `get_model_schema()` hoặc `get_default_settings()` | chính lỗi đã làm hỏng V2.1: một phép đo hẹp thành khung sản phẩm |
| **G2** | ⛔ **Không viết phép kiểm nào kiểm lại hành vi của WanGP.** Chỉ kiểm **mối nối** | WanGP đã có bộ test của nó; kiểm lại là nhân đôi công và nhân đôi chỗ sai |
| **G3** | Mọi bản ghi mang `nguon`: `"khuon"` (fixture) hoặc `"ghi_tu_may"` + `sha_wangp` | để không bao giờ nhầm dữ liệu tạm với dữ liệu thật |
| **G4** | Dải test **738–759**. Không đụng 720–737 (đã dùng) | `docs/dai test cấp cho từng chương trình` |
| **G5** | Ghi tệp bằng `write_bytes`, kết dòng **LF** | `pathlib.write_text` đổi `\n` → `\r\n` trên Windows |
| **G6** | `python tools/gate.py --vong-lap` sau **mỗi** hạng mục; `tools/gate.py` đầy đủ trước khi báo xong | |
| **G7** | Kiểm CPU + `cua_so_yen trang-thai` **trước** mọi lệnh nặng; `-n 6` là trần cứng | |

**Hoãn có chủ đích — không phải bỏ sót:**

> **Giá vốn.** Chủ dự án chốt: dùng nội bộ, chưa tính. `apps/lttvideo/cost.py`
> giữ nguyên. ⚠️ Điều đổi khi thương mại hoá: 46 model = 46 mức tiêu GPU, và
> `cost.py` hiện chỉ biết 2. Ghi ở đây để lần sau không ai tưởng nó đã xong.

---

## 1. Bố cục tệp

```
apps/lttvideo/
  cong/                    ◄── MỐI NỐI (mới)
    __init__.py
    giao_uoc.py            Protocol — DUY NHẤT tầng trên được nhìn thấy
    may_that.py            HTTP -> dich_vu_ccloud trên pod
    may_gia_lap.py         phát lại ban_ghi/, không mạng, không GPU
  ban_ghi/                 ◄── BẢN GHI WanGP (mới)
    _README.md
    liet_ke_model.json     đầu ra list_model_metadata()
    so_do__<model>.json    đầu ra get_model_schema(<model>)
    mac_dinh__<model>.json đầu ra get_default_settings(<model>)
  so_dang_ky.py            ◄── SINH sổ hồ sơ từ bản ghi (mới) — THAY ho_so.py
  tac_vu.py                ◄── danh mục tác vụ người dùng (mới)
  ho_so.py                 ⛔ GỠ ở HM-3
  chon_model.py            ⛔ GỠ ở HM-3 (thay bằng tac_vu.chon)
  wangp_client.py          ⛔ GỠ ở HM-2 (thay bằng cong/may_that.py)
  jobs.py                  viết lại trên mối nối
  routes.py                thêm route gallery có thứ tự
  features.py              giữ
  templates/               thêm _tv_ref.html
tools/wangp/
  ghi_ban_ghi.py           ◄── MÁY GHI (mới) — tool DUY NHẤT nói với pod thật
server/static/lttvideo.js  gallery kéo-thả
tests/test_738..746        dải mới
```

---

## 2. Hợp đồng mối nối — đọc kỹ, mọi hạng mục sau đều dựa vào đây

Lấy **nguyên văn** hình dạng từ `docs_API.md:240-310`. Không thêm trường nào.

```python
# apps/lttvideo/cong/giao_uoc.py
from typing import Protocol, Any, Iterator

class May(Protocol):
    """Mọi thứ LTT cần ở WanGP. Tầng trên KHÔNG được import gì khác."""

    def liet_ke_model(self, **loc: Any) -> list[dict]:
        """`list_model_metadata(**loc)`. Bộ lọc hợp lệ (docs_API.md:252):
        family · base_model_type · finetune · model_type · main_output ·
        inputs · name · query · limit · offset."""

    def so_do(self, model_type: str) -> dict | None:
        """`get_model_schema(model_type)`."""

    def mac_dinh(self, model_type: str) -> dict:
        """`get_default_settings(model_type)`."""

    def kha_dung(self, model_type: str) -> dict:
        """`get_model_availability(model_type)` — trọng số đã có trên đĩa chưa."""

    def gui_viec(self, settings: dict) -> str:
        """`submit_task(settings)`. Trả mã việc."""

    def tien_do(self, ma_viec: str) -> dict:
        """Một nhịp tiến độ: {'pha','phan_tram','xong','loi'}."""

    def ket_qua(self, ma_viec: str) -> dict:
        """`result()`: {'tep': [...], 'loi': [...], 'huy': bool}."""

    def huy(self, ma_viec: str) -> None: ...
```

🔑 **Vì sao mối nối nằm đúng ở đây:** bảy phương thức trên là **toàn bộ** bề mặt
WanGP mà sản phẩm cần. Thứ gì WanGP làm mà không lọt qua bảy cửa này thì tầng
trên không dùng được — và đó là điều tốt: nó ngăn đúng kiểu rò rỉ đã sinh ra
`wangp_client` cũ.

---

## HM-1 · Mối nối + máy giả lập

**Tệp**
- Tạo `apps/lttvideo/cong/__init__.py`, `giao_uoc.py`, `may_gia_lap.py`
- Tạo `apps/lttvideo/ban_ghi/_README.md`
- Test `tests/test_738_cong_giao_uoc.py`

**Giao diện**
- Sản ra: `May` (Protocol), `MayGiaLap`, `LoiMay`
- Dùng ở: mọi hạng mục sau

- [ ] **B1. Viết phép kiểm đỏ trước**

```python
# tests/test_738_cong_giao_uoc.py
def test_may_gia_lap_thuc_hien_DU_giao_uoc():
    """Thiếu một phương thức thì tầng trên vỡ ở runtime, không vỡ ở test."""
    from apps.lttvideo.cong.giao_uoc import May
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap
    thieu = [t for t in May.__protocol_attrs__
             if not callable(getattr(MayGiaLap, t, None))]
    assert not thieu, f"MayGiaLap thieu: {thieu}"
```

- [ ] **B2. Chạy, xác nhận ĐỎ** — `pytest tests/test_738_cong_giao_uoc.py -q`
      Kỳ vọng: `ModuleNotFoundError: apps.lttvideo.cong`

- [ ] **B3. Viết `giao_uoc.py`** — nguyên văn khối ở mục 2, thêm
      `class LoiMay(RuntimeError)` và `runtime_checkable`.

- [ ] **B4. Viết `may_gia_lap.py`**

```python
class MayGiaLap:
    """Phát lại `ban_ghi/`. Không mạng, không GPU, không phụ thuộc thời gian.

    ⛔ KHÔNG bịa dữ liệu. Thiếu bản ghi thì NÉM, không trả rỗng — một máy giả
       lập trả rỗng biến 'chưa ghi' thành 'model không có năng lực đó', và cái
       nhầm ấy đi thẳng vào GUI.
    """
    def __init__(self, goc: Path | None = None): ...
    def _doc(self, ten: str) -> Any:
        tep = self.goc / f"{ten}.json"
        if not tep.is_file():
            raise LoiMay(f"chua co ban ghi {ten!r} — chay tools/wangp/ghi_ban_ghi.py")
        return json.loads(tep.read_text(encoding="utf-8"))
```

`gui_viec` đẩy việc vào hàng đợi trong bộ nhớ; `tien_do` trả các nhịp đã kịch
bản hoá; `ket_qua` trả đường dẫn tới một MP4 mẫu nhỏ trong `ban_ghi/`.

- [ ] **B5. Chạy lại, xác nhận XANH**

- [ ] **B6. Phép kiểm đối chứng — máy giả lập phải KÊU khi thiếu bản ghi**

```python
def test_thieu_ban_ghi_thi_NEM_chu_khong_tra_rong(tmp_path):
    m = MayGiaLap(goc=tmp_path)
    with pytest.raises(LoiMay, match="chua co ban ghi"):
        m.so_do("t2v_2_2")
```

- [ ] **B7. `gate.py --vong-lap`, rồi commit**

---

## HM-2 · Máy thật + gỡ `wangp_client`

**Tệp**
- Tạo `apps/lttvideo/cong/may_that.py`
- Gỡ `apps/lttvideo/wangp_client.py`
- Sửa `tools/wangp/dich_vu_ccloud.py` — thêm 4 đường tra cứu
- Test `tests/test_739_may_that.py`

**Giao diện**
- Tiêu thụ: `May` (HM-1)
- Sản ra: `MayThat(goc_url, token)`

- [ ] **B1. Thêm 4 đường vào cầu nối** — `dich_vu_ccloud.py`, mỗi đường là một
      dòng chuyển tiếp thẳng, **không có logic**:

```python
@app.get("/model")            # -> session.list_model_metadata(**query)
@app.get("/model/{mt}/so-do") # -> session.get_model_schema(mt)
@app.get("/model/{mt}/mac-dinh")  # -> session.get_default_settings(mt)
@app.get("/model/{mt}/kha-dung")  # -> session.get_model_availability(mt)
```

- [ ] **B2. Phép kiểm: cầu nối KHÔNG được chứa nghiệp vụ**

```python
def test_cau_noi_chi_CHUYEN_TIEP_khong_bien_doi():
    """🔑 Đây là phép kiểm quan trọng nhất của HM này. Một phép biến đổi ở cầu
    nối là một chỗ suy diễn nằm NGOÀI tầm với của gate — nó chạy trên pod."""
    ma = inspect.getsource(dich_vu_ccloud)
    for ten in ("list_model_metadata", "get_model_schema",
                "get_default_settings", "get_model_availability"):
        than = _than_ham_goi(ma, ten)      # AST, không khớp chuỗi
        assert "if " not in than and "for " not in than, (
            f"{ten}: cau noi dang BIEN DOI ket qua, phai chuyen tiep tho")
```

- [ ] **B3. Viết `may_that.py`** — HTTP thuần, `LoiMay` khi mã lỗi ≠ 2xx.

- [ ] **B4. Gỡ `wangp_client.py`; sửa mọi nơi import nó** (đo bằng
      `grep -rn "wangp_client" apps/ tests/`, sửa hết, **không để lại lớp bọc
      tương thích** — lớp bọc là cách một tầng đã gỡ sống lại).

- [ ] **B5. Phép kiểm chốt: không còn ai import `wangp_client`** (AST, không grep)

- [ ] **B6. `--vong-lap`, commit**

---

## HM-3 · Sổ đăng ký **SINH RA** — gỡ `ho_so.py` và `chon_model.py`

Đây là hạng mục sửa đúng nguyên nhân gốc của độ phủ 2/46.

**Tệp**
- Tạo `apps/lttvideo/so_dang_ky.py`
- Gỡ `apps/lttvideo/ho_so.py`, `apps/lttvideo/chon_model.py`
- Test `tests/test_740_so_dang_ky.py`

**Giao diện**
- Tiêu thụ: `May.liet_ke_model`, `May.so_do`, `May.mac_dinh`
- Sản ra: `nap(may) -> SoDangKy`; `SoDangKy.model_cho(dau_vao) -> list[str]`;
  `SoDangKy.settings(model_type, dau_vao) -> dict`

- [ ] **B1. Phép kiểm đỏ — sổ phải SINH, không được gõ**

```python
def test_khong_co_TEN_MODEL_nao_go_tay_trong_so_dang_ky():
    """⛔ Một tên model hằng số trong mã là một giá trị sẽ trôi khi WanGP đổi
    bản. Sổ phải nhận model từ máy, không từ hằng."""
    cay = ast.parse(inspect.getsource(so_dang_ky))
    hang = [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for h in hang:
        assert not re.match(r"^(t2v|i2v|vace|ltx2|ti2v)_", h), (
            f"ten model {h!r} go tay — phai den tu may.liet_ke_model()")
```

- [ ] **B2. Chạy, xác nhận ĐỎ** (`ho_so.py` hiện có đúng những tên ấy)

- [ ] **B3. Viết `so_dang_ky.py`**

```python
def nap(may: May) -> SoDangKy:
    """Đọc năng lực CỦA MỌI model video, một lần, rồi dựng chỉ mục ngược:
    {hình dạng đầu vào} -> [model làm được].

    Hình dạng đầu vào lấy từ chính `metadata.media_inputs` mà WanGP khai
    (docs_API.md:284), KHÔNG từ một bảng của ta.
    """
    ds = may.liet_ke_model(main_output="video")
    chi_muc: dict[tuple, list[str]] = {}
    for m in ds:
        mi = m["metadata"]["media_inputs"]
        for khoa in _hinh_dang(mi):        # ('image','start'), ('image','reference')…
            chi_muc.setdefault(khoa, []).append(m["model_type"])
    return SoDangKy(ds, chi_muc)
```

- [ ] **B4. `settings()` KHÔNG tự dựng cờ chữ cái**

```python
def settings(self, model_type, dau_vao) -> dict:
    """⭐ Chỉ lấy `get_default_settings` rồi gắn media vào đúng khe.
    KHÔNG đặt image_prompt_type / video_prompt_type bằng tay.

    docs_API.md:330 — WanGP TỰ điền: 'start images add S, end images add E
    without removing S, source-video continuation adds V, reference images
    use the first declared reference mode containing I'.
    Tầng dịch cờ ở phía ta vừa thừa, vừa là chỗ suy diễn lọt vào.
    """
```

- [ ] **B5. Phép kiểm: KHÔNG có chữ cái cờ nào gán tay**

```python
def test_khong_gan_co_chu_cai_bang_tay():
    ma = inspect.getsource(so_dang_ky)
    for xau in ('"S"', '"E"', '"KI"', '"FI"', 'image_prompt_type ='):
        assert xau not in ma, f"con gan co tay: {xau} — WanGP tu dien"
```

- [ ] **B6. Gỡ `ho_so.py` + `chon_model.py`, sửa mọi nơi dùng**

- [ ] **B7. Chạy `tests/test_729`** (nó chốt "ô chọn tệp không mời thứ job từ
      chối"). Mệnh đề **không đổi**, chỗ chứa nó đổi ⇒ viết lại tại vị trí mới,
      **không xoá**.

- [ ] **B8. `--vong-lap`, commit**

---

## HM-4 · Danh mục tác vụ

Biến "46 model" thành một danh sách việc người dùng hiểu được.

**Tệp** — tạo `apps/lttvideo/tac_vu.py`, test `tests/test_741_tac_vu.py`

**Giao diện**
- Tiêu thụ: `SoDangKy`
- Sản ra: `TAC_VU: dict[str, TacVu]`; `TacVu(ma, nhan, dau_vao, loc)`;
  `chon(so, ma_tac_vu, dau_vao) -> tuple[str, dict]`

- [ ] **B1. Định nghĩa tác vụ bằng **bộ lọc**, không bằng tên model**

```python
TAC_VU = {
  "chu_thanh_video": TacVu("chu_thanh_video", _t("Tạo video từ mô tả"),
                           dau_vao=(), loc={"main_output": "video"}),
  "anh_thanh_video": TacVu(..., dau_vao=("image.start",),
                           loc={"main_output": "video", "inputs": "image"}),
  "nhieu_anh_tham_chieu": TacVu(..., dau_vao=("image.reference",), ...),
  "boi_canh_va_nhan_vat": TacVu(..., dau_vao=("image.background",
                                              "image.reference"), ...),
  "theo_video_dieu_khien": TacVu(..., dau_vao=("video.control",), ...),
  "noi_dai_video":        TacVu(..., dau_vao=("video.continue",), ...),
}
```

⭐ Mỗi tác vụ hỏi **năng lực**, và sổ trả về model nào có năng lực ấy. Thêm model
mới vào WanGP ⇒ tác vụ tự có thêm lựa chọn, **không sửa một dòng nào**.

- [ ] **B2. Phép kiểm: mọi `dau_vao` phải là vai trò WanGP THẬT khai**

```python
def test_moi_vai_tro_deu_co_trong_ban_ghi():
    """⛔ Đối chứng chống bịa. Một vai trò gõ sai ('image.first') sẽ khớp 0
    model và tác vụ ấy im lặng biến mất khỏi GUI."""
    hop_le = _vai_tro_co_that(MayGiaLap())    # đọc từ ban_ghi/
    for tv in TAC_VU.values():
        for v in tv.dau_vao:
            assert v in hop_le, f"{tv.ma}: vai tro {v!r} khong model nao khai"
```

- [ ] **B3. Phép kiểm: mỗi tác vụ khớp ≥ 1 model** (nếu 0 thì hoặc bản ghi
      thiếu, hoặc bộ lọc sai — cả hai đều phải đỏ)

- [ ] **B4. `--vong-lap`, commit**

---

## HM-5 · Đường ống trên mối nối

**Tệp** — viết lại `apps/lttvideo/jobs.py`, `dieu_phoi.py`; test `tests/test_742_duong_ong.py`

- [ ] **B1. `jobs.handle` nhận `may` qua tham số**, mặc định `MayThat`:

```python
def handle(job, *, may: May | None = None):
    may = may or _may_mac_dinh()      # MayThat khi có LTTV_POD_ID, MayGiaLap khi không
```

⇒ Toàn bộ đường ống chạy được trong test **không cần pod**.

- [ ] **B2. Giữ nguyên vòng chờ HAI LỐI RA** (`xong` **và** `ket_qua()` trả về
      được). Một lối ra đã treo vô hạn một lần rồi.

- [ ] **B3. Phép kiểm mối nối — không phải kiểm WanGP:**
  - job xong ⇒ `Job.result["video_keys"]` có khoá tận cùng `_keys`
  - job lỗi ⇒ credit **được hoàn**
  - huỷ ⇒ `POST /jobs/{id}/cancel` kiểm sở hữu
  - `MayGiaLap` ném ⇒ job **FAILED có lý do**, không treo

- [ ] **B4. ⛔ KHÔNG viết phép kiểm nào về chất lượng video** (G2)

- [ ] **B5. `--vong-lap`, commit**

---

## HM-6 · GUI — gallery có thứ tự

**Tệp** — `routes.py`, `templates/_tv_ref.html`, `server/static/lttvideo.js`;
test `tests/test_743_gui_gallery.py`

- [ ] **B1. Ô chọn tác vụ** đọc từ `TAC_VU`, không gõ cứng trong template

- [ ] **B2. Gallery kéo-thả** — **thứ tự là nghĩa**, nên phải hiện số thứ tự
      trên từng ảnh, và số ấy phải đổi ngay khi kéo

- [ ] **B3. Ô chọn vai trò = đúng 4 lựa chọn WanGP khai**, lấy từ
      `so_do()["setting_values"]["video_prompt_type"]["image_ref_choices"]` —
      **không gõ nhãn tiếng Anh của WanGP vào template**, dịch qua `_t()`

- [ ] **B4. Xem trước: ảnh dùng `FileReader`, video dùng `createObjectURL`**
      (CSP `img-src` **không** cho `blob:`; `media-src` có). Bẫy 28.

- [ ] **B5. Thêm mọi tệp static mới vào `server/templating.TAI_SAN_CO_VERSION`**
      — `test_737` quét ngược sẽ đỏ nếu quên

- [ ] **B6. Kiểm bằng trình duyệt thật** (`tools/lttvideo_browser_server.py`):
      console sạch · không request hỏng · kéo-thả đổi số thật ·
      `img.complete && img.naturalWidth > 0`

- [ ] **B7. Dừng harness trước khi chạy gate** (PID còn sống làm đỏ
      `test_361_cua_so_yen`)

- [ ] **B8. `gate.py` đầy đủ, commit**

---

## HM-7 · Máy ghi — bản ghi thật thay khuôn

🔴 **Hạng mục ĐẦU TIÊN cần pod.** Mọi thứ trên đã xanh trước khi tới đây.

**Tệp** — tạo `tools/wangp/ghi_ban_ghi.py`; test `tests/test_744_ban_ghi.py`

- [ ] **B1. Viết máy ghi** — gọi 4 đường tra cứu, ghi `ban_ghi/*.json` kèm
      `nguon: "ghi_tu_may"` + `sha_wangp` + `luc`

- [ ] **B2. Khởi động pod hiện tại, chạy máy ghi**
      ⭐ Tra cứu **không nhân ma trận** ⇒ **không phụ thuộc cuBLAS**. Bước này
      chạy được trên stack đang hỏng.

- [ ] **B3. Đối chiếu khuôn ↔ bản ghi thật.** Mọi chỗ lệch là một chỗ ta đã
      đoán sai — **ghi lại từng chỗ**, đó là dữ liệu quý nhất của cả kế hoạch.

- [ ] **B4. Phép kiểm: không bản ghi nào còn `nguon: "khuon"`**

- [ ] **B5. Hỏi `kha_dung()` cho mọi model** ⇒ biết cái nào đã có trên
      `lttv-models-v1` (**300 GB**, US-KS-2), cái nào phải tải

- [ ] **B6. Tắt pod**

---

## HM-8 · Tải chuỗi model

- [ ] **B1. Chọn tập model từ HM-4 + HM-7/B5**, xếp theo *số tác vụ mở ra / GB*
- [ ] **B2. Đo dung lượng trống trước khi tải** — ghi vào
      `bao_cao_moi_truong.py` (hiện **không** đo đĩa; 300 GB gồm cả conda + torch)
- [ ] **B3. Tải, ghi lại từng model chiếm bao nhiêu**
- [ ] **B4. Chạy lại máy ghi** ⇒ `kha_dung` đổi trạng thái

---

## HM-9 · Pod + GPU — soi lỗi cuối cùng

- [ ] **B1. Dựng lại stack `cu128/py310`** (`cu130` chết ở cuBLAS
      bf16/fp16/fp32, **ngoài** WanGP — đã đo)
- [ ] **B2. Đối chứng: `torch.einsum` bf16 chạy được ngoài WanGP**
- [ ] **B3. Một lượt sinh video thật, mỗi tác vụ một lượt**
- [ ] **B4. Đổi `MayGiaLap` → `MayThat`, chạy lại HM-5 + HM-6**
- [ ] **B5. `gate.py` đầy đủ → `ff` → deploy → nghiệm thu URL công khai**

---

## 3. Vì sao thứ tự này đúng

| Hạng mục | Cần pod? | Cần GPU lành? |
|---|---|---|
| HM-1 … HM-6 | ❌ | ❌ |
| HM-7 (máy ghi) | ✅ | ❌ *(tra cứu không nhân ma trận)* |
| HM-8 (tải model) | ✅ | ❌ |
| HM-9 (sinh thật) | ✅ | ✅ |

**Sáu trên chín hạng mục làm được ngay hôm nay.** Và khi pod sống lại, việc còn
lại là *đối chiếu*, không phải *xây* — mà đối chiếu thì nhanh, còn xây trên một
máy hay chết thì mỗi lỗi tốn một vòng khởi động pod.

## 4. Tự soát

- **Phủ hết yêu cầu?** trọn bộ mã vận hành ✅ · giả lập trước ✅ · pod/GPU cuối ✅
  · không test lại WanGP ✅ (G2) · giá vốn giữ nguyên ✅ (mục 0)
- **Còn chỗ trống nào?** không — mọi bước có tệp cụ thể và mã cụ thể
- **Tên hàm nhất quán?** `May` · `MayThat` · `MayGiaLap` · `LoiMay` ·
  `nap()` · `SoDangKy` · `TAC_VU` · `chon()` dùng y hệt từ HM-1 tới HM-9

---

## 5. Sổ xoá — chồng chéo và vi phạm, xử ở đâu

Chủ dự án chốt 07/09: **xoá thật dữ liệu/mã cũ nếu chồng chéo hoặc phạm luật ta
đang xây.** Sổ này tồn tại để không thứ nào biến mất âm thầm, và để không thứ
nào lẽ ra phải mất mà vẫn sống.

⛔ **Không để lại lớp bọc tương thích.** Một lớp bọc là cách một tầng đã gỡ sống
   lại: nó giữ nguyên đường import cũ, nên không ai bị buộc phải sửa, nên tầng
   cũ tồn tại mãi dưới một cái tên mới.

| Thứ | Phán quyết | Vì sao | Ở đâu |
|---|---|---|---|
| `apps/lttvideo/wangp_client.py` | 🔴 **XOÁ** | trộn *cách nói chuyện* với *biết gì về model* — chính chỗ sinh ra chi phí mỗi-model | HM-2 |
| `apps/lttvideo/ho_so.py` | 🔴 **XOÁ** | bảng model **gõ tay** — phạm G1 | HM-3 |
| `apps/lttvideo/chon_model.py` | 🔴 **XOÁ** | chọn model bằng bảng gõ tay — phạm G1 | HM-3 |
| `apps/lttvideo/ho_so_data/*.json` | 🔴 **XOÁ** | hai hồ sơ rút tay, thay bằng `ban_ghi/` ghi từ máy | HM-7 |
| `CHO_TOI_DA_S` (**hai** chỗ) | 🟠 **ĐỔI TÊN** | `dieu_phoi.py:25`=900,0 (chờ **máy** khởi động) vs `jobs.py:56`=3600,0 (chờ **việc** xong). Một tên, hai nghĩa, hai giá trị — và `routes.py:260` nói với người dùng con số của cái kia. ⇒ `CHO_MAY_SAN_SANG_S` / `CHO_VIEC_XONG_S` | HM-5 |
| `apps/lttvideo/dieu_phoi.py` | 🟡 **GIỮ, ĐỔI CHỖ** | nó là mối nối **RunPod** (bật/tắt/chờ card), không phải mối nối WanGP. Không chồng `cong/`. Nhưng nó thuộc HM-9, đừng để đường ống lệ thuộc nó | HM-9 |
| `apps/lttvideo/kha_nang.py` | 🟡 **GIỮ, SINH RA** | `VAI_DUOC_DUNG` là **quyền**, không chồng gì. Nhưng `NANG_LUC_MO = ("tao_video",)` gõ tay ⇒ phải **sinh từ `TAC_VU`**, nếu không mở tác vụ mới sẽ quên mở cổng và tính năng câm lặng | HM-4 |
| `apps/lttvideo/cost.py` | 🟢 **GIỮ NGUYÊN** | chủ dự án hoãn giá vốn. ⚠️ Ghi để không ai tưởng đã xong: `USD_MOI_GIO_GPU = 1.59` là giá **gõ tay sẽ trôi**, và `CREDIT_MOI_GIAY_VIDEO` chỉ đúng cho 2 model | — |

### Luật khi xoá

1. **Xoá sau khi bản thay đã xanh**, không xoá trước — nếu không thì cây đỏ vì
   một lý do khác lý do đang sửa.
2. **Phép kiểm thì VIẾT LẠI, không xoá theo.** Mệnh đề mà `test_729` (ô chọn
   tệp không mời thứ job từ chối) hay `test_730` (đọc đúng khoá `video_keys`)
   canh **không đổi một chữ** khi mã đổi chỗ. Xoá một phép kiểm vì mã đổi chỗ
   là bỏ một đảm bảo, không phải dọn dẹp.
3. **Đo bằng AST, không bằng `grep`,** khi chốt "không ai còn import thứ đã gỡ"
   — `grep` khớp cả chú thích nhắc tới nó, và đã báo động sai bốn lần ở kho này.

---

## 6. Nhật ký thực thi — thứ kế hoạch đoán sai

Mục này ghi chỗ **bản kế hoạch sai**, vì đó mới là dữ liệu. Chỗ nó đúng thì các
ô đánh dấu đã nói rồi.

### HM-1 · giao ước đáng lẽ là 8, thật ra là 11

Mục 2 của chính tài liệu này khai **tám** phương thức — viết **trước khi** đọc
xem `wangp_client` cũ thật sự dùng gì. Đọc rồi mới thấy ba cửa nữa đang chạy
thật:

| Cửa thiếu | Đường cầu nối | Thiếu nó thì |
|---|---|---|
| `nap_media` | `POST /nap_media` | WanGP chỉ nhận **đường dẫn tệp trên máy nó**; ảnh người dùng nằm ở R2 ⇒ không có đầu vào ảnh nào chạy được |
| `tai_ve` | `GET /tai/{job}/{i}` | video sinh xong **nằm lại trên pod** ⇒ job XONG mà không tải được gì |
| `don_dep` | `POST /cleanup/{job}` | volume 300 GB đầy dần, và nó **dùng chung với trọng số model** |

⭐ Chính `test_738` (*"chốt con số"*) bắt được điều này — nó sinh ra để buộc
  người sửa dừng một nhịp, và người đầu tiên nó chặn là người viết ra nó.

### HM-1 · máy giả lập ghi vào cây kho

`ket_qua()` bản đầu ghi `gia_lap_<ma>.mp4` vào `apps/lttvideo/ban_ghi/`. Một tệp
lạ sinh ra trong cây **giữa lượt gate** làm chính lượt ấy mất giá trị
(`cay_da_doi_giua_chung`) — mất 10 phút mới biết. Nay ghi ra thư mục tạm, có
phép kiểm canh.

### 🔴 HM-2 · một lỗi đã khiến MỌI lượt chạy thật đều chết

`jobs.py` kéo tệp về bằng:

```python
with_tai = getattr(client, "tai_ve", None)
if with_tai is None:
    raise LoiJob(_t("Không tải được kết quả về."))
```

Nhưng `WanGPClient` **không bao giờ có** `tai_ve` — đếm được: 0 định nghĩa.

⇒ Mọi lượt sinh video thật đều dừng ở *"Không tải được kết quả về"*, **sau khi**
  GPU đã chạy xong và tính tiền thời gian thuê.

⭐ Bài học không nằm ở phương thức thiếu, mà ở **cái vỏ**: `getattr(x, "ten",
  None)` cộng một thông điệp lỗi tử tế biến một **lỗ hổng** thành một **trường
  hợp biên đã xử lý**. Không có dấu vết nào để lần: không `AttributeError`,
  không traceback, chỉ một câu tiếng Việt lịch sự nói rằng việc đã hỏng.

⇒ Nay gọi thẳng `client.tai_ve(job_id, i)` theo giao ước. Thiếu là
  `AttributeError` nổ ngay trong test.

### HM-2 · phân biệt huỷ/hỏng từng đặt trên một chuỗi của thượng nguồn

`KetQua.da_huy` cũ dò chuỗi `"cancelled"` trong thông điệp lỗi. Đó là một phép
phân biệt **về tiền** (huỷ ⇒ hoàn phần chưa dùng; hỏng ⇒ không trừ) đặt trên
cách diễn đạt của WanGP.

Hai đường hỏng, cả hai đều im lặng:

1. WanGP đổi chữ ⇒ mọi lần huỷ bị tính như hỏng
2. một lỗi thật chứa chữ ấy (*"upstream connection cancelled by peer"*) ⇒ một
   lần hỏng được tính như huỷ

⇒ Cầu nối nay phơi thẳng `GenerationResult.cancelled` thành trường `huy`.
  `test_722` có phép kiểm đối chứng cho **đúng** ca số 2.

### HM-5 · hai trần chờ trùng tên đã tách

`CHO_TOI_DA_S` tồn tại ở **hai** tệp, **hai** giá trị, **hai** nghĩa —
`dieu_phoi` 900,0 (chờ **máy** khởi động) và `jobs` 3600,0 (chờ **việc** xong) —
và `routes.py` nói với người dùng con số của cái kia. Nay là
`CHO_MAY_SAN_SANG_S` / `CHO_VIEC_XONG_S`, có phép kiểm chốt cả hai tên lẫn quan
hệ thứ tự giữa chúng.

⛔ Và `_client_that()` **không** lui về máy giả lập khi thiếu cấu hình. Một job
   thật chạy trên máy giả lập sẽ "thành công" và trả về một tệp **không phải
   video**: job XONG, credit đã trừ, người dùng tải về một tệp hỏng — thất bại
   im lặng **về phía có lợi**, kiểu tệ nhất.

### HM-6 · gallery kéo-thả **hoãn có chủ đích**

Kế hoạch dự tính một gallery nhiều ảnh có thứ tự. Nhưng mọi tác vụ cần nhiều
ảnh (`nhieu_anh_tham_chieu`, `boi_canh_va_nhan_vat`) đang `mo=False` — chúng
thiếu `mac_dinh__vace_14B.json`, mà bản ghi ấy phải rút từ máy thật (HM-7).

⛔ Dựng ô chọn nhiều ảnh trong khi mọi tác vụ nhiều ảnh đều đóng là **mở một
   cánh cửa vào căn phòng khoá** — đúng bất biến app này đã trả giá để học.

⭐ `test_743` canh điều đó theo cách **tự tắt**: nó `skip` ngay khi có một tác vụ
  nhiều ảnh mở ra. Nó canh sự **khớp** giữa hai cửa, không canh sự vắng mặt của
  một tính năng.

### 🔴 HM-6 · test xanh, DOM đúng, nhìn thì vỡ

Ô chọn tác vụ ban đầu render thành **chữ thô xếp dọc**, không phải chip — y hệt
sự cố `ltt.css` mà `CLAUDE.md` mục 5b ghi lại. Cả `test_743` lẫn `test_734` đều
xanh, vì chúng đo **cấu trúc**, và cấu trúc thì đúng.

⇒ Sửa bằng cách **dùng lại `.tv-models`**, khuôn đã có của chính app này (lưới 2
  cột, viền, `:has(input:checked)`). Không lớp CSS mới, không tệp static mới,
  nên không phải cache-bust gì.

Đo bằng CSS **tính toán** chứ không bằng DOM: bấm ô thứ hai thì viền đổi
`rgb(59,48,49)` → `rgb(239,61,53)` và nền `rgb(19,20,22)` → `rgb(50,19,21)`.

Và bố cục ban đầu đặt ô chọn tác vụ **trong mục "Đính kèm"** — ngược với thứ tự
thật của quyết định, vì tác vụ chọn model, chọn có được đính kèm không, chọn tối
đa mấy tệp. Nay nó là mục **01**, các mục sau đánh số lại.

### HM-7 · bốn điều đo được khi pod thật lên

**1. Không pod nào bật lại được.** Cả bốn đều trả *"not enough free GPUs on the
host machine"*. RunPod `stop` **nhả card**, và card ấy có thể không bao giờ về.
⇒ HM-7 và HM-9 **gộp làm một**: tạo pod mới, và chọn ảnh cho nó chính là quyết
định HM-9.

**2. Bảng tồn kho không phải giá thật.** Tiền kiểm báo `H100 NVL $2,59/h`;
pod tạo ra tính **$3,19/h**. `lowestPrice` là *chỉ dấu*, không phải hoá đơn.

**3. ⛔ Pod này KHÔNG có SSH — và đó là hệ quả của chính cấu hình ta đặt.**
`dockerEntrypoint: ["bash","-lc","bash /data/lttv/khoi_dong.sh"]` **ghi đè**
entrypoint mặc định của RunPod, mà chính entrypoint ấy mới khởi động `sshd`.
Cổng 22 vẫn được ánh xạ (38427) nên nhìn bảng thì tưởng có SSH — nhưng không ai
nghe ở đó. ⇒ Mọi đường vào pod phải đi qua **cầu nối**. Muốn chạy một lệnh chẩn
đoán thì phải có một đường trên cầu nối, không có đường tắt.

**4. Lượt tra cứu ĐẦU TIÊN trả giá khởi tạo phiên.** Hợp đồng `May` nói đúng
rằng bốn đường tra cứu *"không nhân ma trận"* — nhưng chúng gọi `_lay_phien()`,
và lượt đầu tiên `init()` cả runtime WanGP. `MayThat.CHO_MAC_DINH_S = 30,0` nên
lượt ấy **hết giờ**. Sau khi phiên ấm (`runtime_san_sang: true`) thì tra cứu trả
về trong **1 giây**.

⇒ Đây là một chỗ hợp đồng nói **chưa đủ**, không phải nói sai. Cần một trần chờ
  riêng cho lượt đầu, hoặc một đường hâm nóng tường minh.

### 🟢 HM-7/HM-9 · cuBLAS CHẠY ĐƯỢC trên cu128

Đo 08/09 trên pod `rappv9risxm802` (image `cuda:12.8.1`, H100 NVL, $3,19/h):

```
30/30 bước inference -> decoding -> xong
3.291.112 byte · header \x00\x00\x00 ftypisom   (MP4 thật)
710 giây cho 5 giây video @ 480p / 30 bước
```

⇒ Lỗi `CUBLAS_STATUS_INVALID_VALUE` là **đặc thù của stack cu130**, không phải
của WanGP, không phải của model, không phải của mã ta. Đây là lần đầu chuỗi
`settings() → gui_viec → tien_do → ket_qua → tai_ve → don_dep` chạy trọn vẹn
với **máy thật**.

⚠️ Số giá vốn đo được, ghi để dùng khi thương mại hoá (đang hoãn theo quyết định
   của chủ dự án): **~$0,63 cho một video 5 giây** ở 480p/30 bước.

### 🔴 HM-7 · hai lỗi mà mọi phép kiểm trước đó đều bỏ lọt

**1. Đọc nhầm tài liệu, và dữ liệu tự dựng che mất.** WanGP có **hai** hàm liệt
kê trả **hai khuôn**: `list_model_defs()` lồng dưới `metadata`, còn
`list_model_metadata()` trả **phẳng**. Ví dụ ở `docs_API.md:262` là của hàm thứ
nhất; ta áp khuôn ấy cho hàm thứ hai ⇒ 225 model mà **không model nào khai một
vai trò nào**.

⭐ Vì sao nó lọt qua tất cả: bản ghi cũ do **chính ta** dựng từ ảnh chụp, nên nó
  mang đúng khuôn ta tưởng. **Phép kiểm và dữ liệu cùng sai một kiểu thì khớp
  nhau hoàn hảo.** Chỉ dữ liệu từ máy thật mới phá được sự khớp giả ấy — đó
  chính xác là việc HM-7 sinh ra để làm.

Sau khi sửa, hai nguồn độc lập cách nhau một ngày cho **cùng** con số
(83/70/51/82/113). Đã chốt cả hai khuôn lẫn phép đối chứng chéo.

**2. Cửa THỨ BA.** `kha_dung` thật: **1/225 available**, 4 partial, 220 missing
— trong đó `i2v_2_2`. Hai cửa ta canh trước đó đều **xanh** cho tác vụ ảnh:

    o chon tep moi gi    ↔  tac vu nhan gi          ✓
    tac vu can vai tro   ↔  model khai vai tro      ✓
    ban khai co          ↔  TRONG SO co             ✗  ← chua ai dem

⇒ `dang_mo()` nay đòi **ba** điều kiện. Tác vụ ảnh tự đóng, ô chọn tệp biến
  theo, và phép kiểm đo **HTML đã dựng** chứ không đo mã nguồn — một phép kiểm
  về *thứ người dùng thấy* mà đọc mã nguồn thì nó đỏ đúng lúc mã đã đúng.

**Bài học rộng hơn một lỗi:** bất biến *"cửa trước khớp cửa sau"* chỉ đúng khi
**đếm đủ số cửa**. Hai cửa đầu là hai cửa ta *nghĩ ra*; cửa thứ ba chỉ lộ ra khi
hỏi máy thật.

### Bốn pod chết đã xoá — và `204` không phải lỗi

Cả bốn xoá **thành công** (HTTP 204) nhưng `may_cloud.rest()` in ra `"loi xoa"`:
nó chỉ nhận `200`/`201`. Báo thành công thành thất bại nguy hiểm theo hướng
riêng: nó đẩy người ta đi **thử lại một việc đã xong**, và với một thao tác
destructive thì lần thử lại ấy nhắm vào thứ khác. Đã vá, có phép kiểm.

### 🟢 HM-8 · ba model có trọng số — và tải RẺ hơn dự tính nhiều

```
t2v_2_2    available (co san)
i2v_2_2    missing -> available   681s tong (~186s tai, roi 30 buoc)   2.564.549 byte
vace_14B   missing -> available   711s tong (~126s tai, roi 30 buoc)   3.924.224 byte
```

⭐ **Tải chỉ mất 2–3 phút mỗi model**, không phải hàng chục phút như kế hoạch lo.
Phần đắt là **sinh video** (~11 phút cho 5 giây), không phải tải. Kế hoạch đã đặt
HM-8 như một hạng mục nặng; đo ra thì nó là hạng mục nhẹ nhất trong ba hạng mục
cần pod.

**Tổng chi phí HM-7 + HM-8 + HM-9: 56 phút × $3,19/h ≈ $3,01.**

### 🔴 HM-8 · một sai thứ tự của chính phiên này

Ta ghi `kha_dung` **rồi mới** tải trọng số. Nên bản ghi nói `i2v_2_2` và
`vace_14B` *thiếu*, trong khi đĩa đã *có*.

⭐ Sai số đi **đúng chiều an toàn**: nó giữ tác vụ **đóng**. Ẩn mất một tác vụ
  chạy được thì nhìn thấy ngay; mời người ta vào một tác vụ hỏng thì họ mất
  credit trước khi ai biết. Đây là lần đầu trong phiên một sai sót của ta rơi về
  phía an toàn thay vì phía yên tâm.

⛔ **Cách sửa KHÔNG phải bật lại pod để làm mới một bản ghi.** Ứng dụng không
   phục vụ được job nào khi pod tắt, nên một tác vụ "đang mở" lúc pod tắt cũng
   vô nghĩa. `available` là **trạng thái sống**, không phải dữ liệu ghim — chỗ
   đúng để làm mới là **lúc pod khởi động**.

### Ba tác vụ VACE: lý do đóng ĐÃ ĐỔI

| | Trước 08/09 | Nay |
|---|---|---|
| `nhieu_anh_tham_chieu` | thiếu `mac_dinh__vace_14B` | thiếu **gallery kéo-thả** |
| `boi_canh_va_nhan_vat` | thiếu bản ghi | thiếu **giao diện** |
| `theo_video_dieu_khien` | thiếu trọng số | thiếu **giao diện** + hồ sơ `video_prompt_type` |

⛔ Đã ghi lại `can_cu` cho cả ba. **Một lý do cũ để nguyên là một lý do sẽ bị đọc
   nhầm** — người sau đọc "chưa có bản ghi" sẽ đi rút bản ghi, và thấy nó đã có
   thì kết luận sai rằng tác vụ sẵn sàng.
