# GĐ1 ASV — Plan triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đảo bậc thang nắn để nấc miễn phí chạy trước nấc 16 giây, dời `edit_plan`
xuống sau `render`, và mở đường cho ASV ra được MP4 trên production.

**Architecture:** GĐ1 giữ nguyên hình, xuất MP4 full độ dài; mọi việc hình (cắt, che,
logo, phụ đề) nằm ở GĐ2 sau `render`. Cửa tiêu tiền (gọi LLM nắn) đọc **ngân sách đã
gồm khoảng lặng mượn được**, ⛔ không đọc `ket - bat`. Bộ ước lượng thời lượng đọc
thay phép "chạy TTS để đo".

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy/PostgreSQL · ffmpeg (`atempo`,
`blackdetect`, `freezedetect`) · PySceneDetect (BSD-3) · OpenCV · `qwen38-api` trên máy B.

**Spec:** `docs/auto_scan_video_final/B1_PLAN_DUONG_ONG_GD1.md` (§1–§10) +
`docs/auto_scan_video_final/B2_PLAN_NGU_CANH_DICH.md` (§1–§6). Executor đọc **cả hai**.

## Global Constraints

- ⛔ **KHÔNG chạy gate trong phiên.** Test NHẮM cụm vừa sửa; gộp `main` xong chạy
  `pre-commit run --all-files`. Gate là việc của CUỐI PLAN, một lần, một cấp.
- ⛔ **Lệnh nặng đi qua** `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n` ≤ 7.
- ⛔ **`git add` tường minh từng tệp.** Dòng `??`/`AM` lạ là phiên khác — ⛔ không
  `stash`, ⛔ không `reset`, ⛔ không `checkout --`. Commit bằng **pathspec**:
  `git commit -F- -- <đường/dẫn>`.
- ⛔ **Đổi lời nhắc PHẢI tăng** `van_ban.PHIEN_BAN_LOI_NHAC_DICH` (nay `5`) — nó nằm
  trong vân tay; thiếu thì lần chạy mới dùng lại kết quả của lời nhắc CŨ.
- ⛔ **Một hằng số một nguồn.** Tuyệt đối ⛔ không gõ lại `0.7`, `1.15`, `3.35`, `0.05` —
  import từ module chủ.
- ⛔ **Không thêm provider dự phòng.** `THU_TU_PROVIDER` giữ **một** tên.
- ⛔ **Không sửa `credit.py`, `jobs.py`, `job_runner.py`, `gpu_lease.py`** — có bút toán thật.
- Ghi tệp cấu hình **KHÔNG BOM**; `.ps1` thuần ASCII.
- Mỗi task kết thúc bằng **một commit**, thông điệp tiếng Việt không dấu, kèm
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## File Structure — và SỞ HỮU theo làn (⛔ không hai làn một tệp)

| làn | tệp SỞ HỮU (chỉ làn này ghi) | task |
|---|---|---|
| **A · bỏ chặn** | `apps/auto_scan_video/giai_doan_media.py` · `tests/test_429_asv_v4_dau_vao_lon.py` | 1 |
| **B · bậc thang** | `apps/auto_scan_video/thoi_gian.py` · `nan_cho_vua.py` · `giai_doan_giong.py` · `giai_doan_thoi_gian.py` · `tests/test_2018_asv_ngan_sach_do_dai.py` | 2, 3, 4, 8 |
| **C · đo & dịch** | `apps/auto_scan_video/nan_thoi_luong.py` · `ngon_ngu.py` · `dich_thuat.py` · `van_ban.py` · `tools/asv_doi_soat.py` · `tests/test_408_asv_dich_thuat.py` | 5, 6, 7 |
| **D · giao diện** | `apps/auto_scan_video/tach_tieng.py` · `tests/test_423_asv_giao_dien.py` | 9 |
| **E · dời giai đoạn** | `apps/auto_scan_video/pipeline.py` · `giai_doan_ban_bien_tap.py` · `giai_doan_noi_dung.py` · `giai_doan_hinh_anh.py` | 10 |

⚠️ **Làn E chạy MỘT MÌNH, sau cùng.** Nó chạm `pipeline.CHUOI` — sổ đăng ký dùng
chung. ⛔ Không làn nào khác được mở khi E đang chạy.

⚠️ **A phải xong trước B/C/E nghiệm thu được** — không có A thì ⛔ không lượt chạy nào
tới `render`, nên ⛔ không đo được gì trên worker thật. B, C, D chạy **song song** với
nhau ngay sau A.

---

## Task 1 · N-58 + N-59: `_duong_doc_duoc` an toàn ở BIÊN  (làn A)

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_media.py:33-56`
- Test: `tests/test_429_asv_v4_dau_vao_lon.py`

**Interfaces:**
- Consumes: `platform_core.storage.Storage` (`open()`, `local_path()`)
- Produces: `_duong_doc_duoc(kho, khoa: str, thu_muc: Path) -> str` — **tên tệp dẫn
  xuất từ `khoa`**, tạo `thu_muc` nếu chưa có. Mọi người gọi khác giữ nguyên cách gọi.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

Thêm vào cuối `tests/test_429_asv_v4_dau_vao_lon.py`:

```python
class _KhoGiaR2:
    """Kho kiểu R2: ⛔ KHÔNG có đĩa, nên `local_path` luôn None."""

    def __init__(self, noi_dung: dict[str, bytes]):
        self._nd = noi_dung

    def local_path(self, key: str):
        return None

    def open(self, key: str):
        import io
        return io.BytesIO(self._nd[key])


def test_duong_doc_duoc_TU_TAO_thu_muc_chua_ton_tai(tmp_path):
    """🔴 N-58: 3/3 lượt production chết `Errno 2` vì thư mục con chưa được tạo."""
    from apps.auto_scan_video.giai_doan_media import _duong_doc_duoc

    kho = _KhoGiaR2({"a/b/seg.wav": b"RIFFxxxx"})
    chua_co = tmp_path / "t0_seg_0001"
    assert not chua_co.exists()

    duong = _duong_doc_duoc(kho, "a/b/seg.wav", chua_co)

    from pathlib import Path as _P
    assert _P(duong).is_file()
    assert _P(duong).read_bytes() == b"RIFFxxxx"


def test_hai_khoa_vao_cung_thu_muc_KHONG_duoc_dung_mot_tep(tmp_path):
    """🔴 N-59: `giai_doan_qc.py:130-131` tải hai khoá vào CÙNG một thư mục.

    Tên tệp cố định ⇒ lượt sau ghi đè lượt trước ⇒ QC so bản ra với CHÍNH NÓ.
    Lỗi IM LẶNG: ⛔ không ném, chỉ làm một phép đo không thể trượt.
    """
    from apps.auto_scan_video.giai_doan_media import _duong_doc_duoc

    kho = _KhoGiaR2({"ra/master.mp4": b"BAN-RA", "nguon/goc.mp4": b"NGUON"})
    d1 = _duong_doc_duoc(kho, "ra/master.mp4", tmp_path)
    d2 = _duong_doc_duoc(kho, "nguon/goc.mp4", tmp_path)

    assert d1 != d2, "hai khoa khac nhau ra cung mot duong"
    from pathlib import Path as _P
    assert _P(d1).read_bytes() == b"BAN-RA"
    assert _P(d2).read_bytes() == b"NGUON"
```

- [ ] **Step 2: Chạy để thấy nó ĐỎ**

Run: `python -m pytest tests/test_429_asv_v4_dau_vao_lon.py -q -k "duong_doc_duoc or hai_khoa"`
Expected: **2 failed** — bài đầu `FileNotFoundError: [Errno 2]`, bài sau `assert d1 != d2`.

- [ ] **Step 3: Sửa tại biên**

Trong `apps/auto_scan_video/giai_doan_media.py`, thêm `import hashlib` vào khối import,
rồi thay thân `_duong_doc_duoc` từ dòng `dich = thu_muc / "nguon.bin"`:

```python
    # 🔴 N-58 (26/09/2026): `thu_muc` CÓ THỂ chưa tồn tại. `giai_doan_thoi_gian.py`
    #    truyền một thư mục CON (`t{lô}_{mã}`) và ⛔ không tạo nó, nên `open(..., "wb")`
    #    ném `Errno 2` ở đoạn ĐẦU TIÊN — 3/3 lượt production chết ở đây.
    #    ⭐ `giai_doan_qc_do_luong.py:161` thì `tm.mkdir()` trước khi gọi ⇒ hợp đồng
    #    "người gọi phải tạo thư mục" chưa bao giờ được gác. Gác ở BIÊN, một lần.
    thu_muc.mkdir(parents=True, exist_ok=True)
    # 🔴 N-59: tên tệp phải DẪN XUẤT TỪ KHOÁ. Với tên cố định `nguon.bin`, hai khoá
    #    khác nhau vào cùng một thư mục ghi đè nhau — và `giai_doan_qc.py:130-131`
    #    làm đúng điều đó, khiến QC so bản ra với CHÍNH NÓ. Lỗi IM LẶNG.
    #    ⛔ Không ai phụ thuộc chuỗi "nguon.bin" (đã grep cả kho).
    dich = thu_muc / (hashlib.sha1(khoa.encode("utf-8")).hexdigest()[:16] + ".bin")
```

- [ ] **Step 4: Chạy lại — phải XANH**

Run: `python -m pytest tests/test_429_asv_v4_dau_vao_lon.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/giai_doan_media.py tests/test_429_asv_v4_dau_vao_lon.py
git commit -F- -- apps/auto_scan_video/giai_doan_media.py tests/test_429_asv_v4_dau_vao_lon.py
```

---

## Task 2 · `thoi_gian.ngan_sach_nan_s()` — MỘT nguồn cho ngân sách nắn  (làn B)

**Files:**
- Modify: `apps/auto_scan_video/thoi_gian.py` (thêm hàm sau `ngan_sach_doan`)
- Test: `tests/test_2018_asv_ngan_sach_do_dai.py`

**Interfaces:**
- Consumes: `thoi_gian.TY_LE_MUON_KHOANG_LANG` (= `0.7`)
- Produces: `ngan_sach_nan_s(khe_s: float, ngan_sach_s: float) -> float`
  — Task 3 gọi hàm này. ⛔ Nó **không** nhận `Khe` (tránh `thoi_gian` phải import
  `nan_thoi_luong`, và tránh vòng import).

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_ngan_sach_nan_khong_co_khoang_lang_thi_BANG_khe():
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 3.0) == 3.0


def test_ngan_sach_nan_muon_DUNG_ty_le_da_khai():
    from apps.auto_scan_video import thoi_gian as tg
    # khe 3,0 s · tới mốc sau 4,0 s ⇒ khoảng lặng 1,0 s
    ra = tg.ngan_sach_nan_s(3.0, 4.0)
    assert abs(ra - (3.0 + 1.0 * tg.TY_LE_MUON_KHOANG_LANG)) < 1e-9


def test_ngan_sach_nan_KHONG_BAO_GIO_nho_hon_khe():
    """Dữ liệu hỏng (`moc_sau` < `ket`) ⛔ không được làm ngân sách teo lại."""
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 1.0) == 3.0
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py -q -k ngan_sach_nan`
Expected: **3 failed** — `ImportError: cannot import name 'ngan_sach_nan_s'`.

- [ ] **Step 3: Thêm hàm**

```python
def ngan_sach_nan_s(khe_s: float, ngan_sach_s: float) -> float:
    """Ngân sách mà **bậc thang nắn** được phép dùng cho một đoạn, tính bằng giây.

    🔴 **Vì sao hàm này tồn tại (26/09/2026).** `giai_doan_giong.py:211` hỏi
       `nan_cho_vua.khe_cua(m)` = `ket - bat`, tức **⛔ không có khoảng lặng**, rồi
       lấy con số đó làm **cửa tiêu tiền** (`nen_viet_lai` → gọi LLM 16 giây).
       Nhưng cửa **thực thi** (`lap_ke_hoach` ở `timing_align`) lại mượn tới
       `TY_LE_MUON_KHOANG_LANG` của khoảng lặng. ⇒ Một đoạn chỉ cần mượn 0,3 giây
       **miễn phí** vẫn phải trả **2 lời gọi LLM + 3 lượt TTS**.

    ⭐ Và chính `nan_thoi_luong.Khe.ngan_sach_s` đã viết ra lời buộc tội:
       *"⛔ Lấy `ket - bat` là vứt hết khoảng lặng, tức vứt phần lớn ngân sách."*

    ⛔ **Không** sửa `khe_cua` để nó tự cộng khoảng lặng: `khe_cua` đang trả lời
       ĐÚNG câu hỏi của nó (*"khe của đoạn này rộng bao nhiêu"*). Sai là **câu được
       hỏi** ở cửa tiêu tiền, ⛔ không phải câu trả lời.

    ⚠️ Tỉ lệ mượn lấy từ `TY_LE_MUON_KHOANG_LANG` — **cùng** hằng số mà
       `lap_ke_hoach` dùng. ⛔ Không gõ lại `0.7`: hai bản sao của một chính sách là
       thứ kho này đã trả giá.
    """
    khe_s = max(0.0, float(khe_s))
    ngan_sach_s = max(khe_s, float(ngan_sach_s))
    return khe_s + (ngan_sach_s - khe_s) * TY_LE_MUON_KHOANG_LANG
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/thoi_gian.py tests/test_2018_asv_ngan_sach_do_dai.py
git commit -F- -- apps/auto_scan_video/thoi_gian.py tests/test_2018_asv_ngan_sach_do_dai.py
```

---

## Task 3 · Cửa tiêu tiền đọc NGÂN SÁCH, và đếm Đ4  (làn B)

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_giong.py` (dòng ~211 và vòng `while` ~313)
- Test: `tests/test_2018_asv_ngan_sach_do_dai.py`

**Interfaces:**
- Consumes: `thoi_gian.ngan_sach_nan_s(khe_s, ngan_sach_s) -> float` (Task 2) ·
  `nan_thoi_luong.Khe` (đã có `bat`, `ket`, `moc_sau`, `khe_s`, `ngan_sach_s`) — danh
  sách `Khe` **đã được dựng** ở `giai_doan_giong.py:149` để gọi `nhom_chi_so`.
- Produces: khoá `"so_doan_nan_oan"` trong `dong_ho` (đi vào `tom_tat` của giai đoạn).

- [ ] **Step 1: Viết phép kiểm ĐỎ — bất biến, ⛔ không phải một lượt chạy**

```python
def test_cua_TIEU_TIEN_phai_doc_NGAN_SACH_khong_doc_khe_cua():
    """🔴 Đ4: đoạn vừa được nếu mượn khoảng lặng thì ⛔ KHÔNG được gọi LLM.

    Chốt bằng AST: `nen_viet_lai` trong `giai_doan_giong` ⛔ không được nhận biến
    tên `khe`. Một phép kiểm hành vi ở đây phải dựng cả máy sinh tiếng; một phép
    kiểm hình dạng thì bắt đúng cái sai và ⛔ không đòi GPU.
    """
    import ast
    import inspect
    from apps.auto_scan_video import giai_doan_giong

    cay = ast.parse(inspect.getsource(giai_doan_giong))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "nen_viet_lai"]
    assert goi, "khong tim thay loi goi nen_viet_lai"
    for n in goi:
        ten = [a.id for a in n.args if isinstance(a, ast.Name)]
        assert "khe" not in ten, (
            "cua tieu tien van doc `khe` (= ket - bat). Phai doc `ngan_sach` "
            "(da gom khoang lang muon duoc) — xem thoi_gian.ngan_sach_nan_s")
        assert "ngan_sach" in ten, "cua tieu tien chua doc ngan_sach"


def test_dong_ho_giai_doan_giong_co_bo_dem_nan_oan():
    """Đ4 phải ĐẾM ĐƯỢC, ⛔ không phải suy ra từ log."""
    import inspect
    from apps.auto_scan_video import giai_doan_giong

    ma = inspect.getsource(giai_doan_giong)
    assert '"so_doan_nan_oan"' in ma, (
        "thieu bo dem D4: so doan `giay > khe` NHUNG `giay <= ngan_sach`")
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py -q -k "TIEU_TIEN or nan_oan"`
Expected: **2 failed** — bài đầu `assert "khe" not in ten`, bài sau thiếu chuỗi.

- [ ] **Step 3: Sửa `giai_doan_giong.py`**

3a. Ngay sau chỗ dựng danh sách `Khe` cho `nhom_chi_so` (khoảng dòng 149), thêm bảng
ngân sách — dùng **cùng** các `Khe` đó, ⛔ không dựng lần hai:

```python
    # ⭐ CÙNG các `Khe` vừa dựng cho `nhom_chi_so` — chúng đã mang `moc_sau`, tức
    #    biên có thật kế tiếp. ⛔ Không dựng lần hai: hai bản sao của cùng một mốc
    #    là chỗ sẽ trôi.
    ngan_sach_theo_ma = {
        k.ma: thoi_gian.ngan_sach_nan_s(k.khe_s, k.ngan_sach_s) for k in khes
    }
```

3b. Tại dòng `khe = nan_cho_vua.khe_cua(m)` (≈211), thêm ngay dưới:

```python
            # 🔴 HAI con số, HAI câu hỏi — ⛔ đừng gộp lại:
            #    `khe`       = khe của chính đoạn (`ket - bat`) → dùng để BÁO CÁO
            #                  (`ket_luan`, `ban_ghi_luot_doc`, `tom_tat`).
            #    `ngan_sach` = khe + phần khoảng lặng mượn được → dùng cho CỬA
            #                  TIÊU TIỀN. Đây là con số mà `timing_align` thật sự
            #                  thực thi, nên nó là con số đúng để quyết có trả
            #                  tiền cho một lượt LLM hay không.
            ngan_sach = ngan_sach_theo_ma.get(str(m["ma"]), khe)
```

3c. Trong vòng `while`, thay điều kiện và thêm bộ đếm Đ4:

```python
                # ⭐ Đ4: đoạn "tràn khe nhưng vừa ngân sách" — mỗi đoạn như vậy
                #    TRƯỚC bản sửa là một lượt LLM tiêu OAN. Đếm để chứng minh.
                if giay > khe and giay <= ngan_sach:
                    dong_ho["so_doan_nan_oan"] += 1
                if not nan_cho_vua.nen_viet_lai(giay, ngan_sach):
                    break
```

3d. Khai bộ đếm trong `dong_ho` (chỗ khởi tạo, ≈ dòng 180):

```python
    dong_ho = {"giay_tts": 0.0, "giay_llm_nan": 0.0, "so_doan_nan_oan": 0}
```

3e. Bảo đảm `from . import thoi_gian` có trong khối import của tệp.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py tests/test_4600_asv_san_dung_sai.py tests/test_4700_asv_gop_khe_that.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/giai_doan_giong.py tests/test_2018_asv_ngan_sach_do_dai.py
git commit -F- -- apps/auto_scan_video/giai_doan_giong.py tests/test_2018_asv_ngan_sach_do_dai.py
```

---

## Task 4 · Trần tăng tốc thành CẢNH BÁO; `VONG_TOI_DA` 2 → 1  (làn B)

**Files:**
- Modify: `apps/auto_scan_video/nan_cho_vua.py:124` · `giai_doan_thoi_gian.py:202-203`
- Test: `tests/test_2018_asv_ngan_sach_do_dai.py`

**Interfaces:**
- Consumes: `nan_cho_vua.tran_co_gian() -> float` (= `TRAN_TANG_TOC` = `1.15`)
- Produces: `VONG_TOI_DA = 1` · hệ số tăng tốc **⛔ không bị kẹp**; hệ số đã áp ghi
  vào hồ sơ giai đoạn dưới khoá `"he_so_toc_da_ap"` (danh sách `float`).

Chủ dự án chốt 26/09: *"vượt trần thoải mái"*, cứu theo thứ tự **(b) nới biên lần hai
→ (c) chấp nhận + ghi báo cáo"*.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_vong_nan_toi_da_la_MOT():
    """VideoLingo (18,5k★) đã bỏ vòng rút gọn thứ hai; chú thích của chính ta
    cũng nói "vòng thứ hai thường không cần đến"."""
    from apps.auto_scan_video import nan_cho_vua
    assert nan_cho_vua.VONG_TOI_DA == 1


def test_he_so_toc_KHONG_bi_kep_ve_tran():
    """Chủ dự án chốt: vượt trần thoải mái. Trần còn là CẢNH BÁO, ⛔ không phải cổng."""
    import ast
    import inspect
    from apps.auto_scan_video import giai_doan_thoi_gian

    ma = inspect.getsource(giai_doan_thoi_gian)
    assert "he_so_toc_da_ap" in ma, "chua ghi lai he so da ap"
    cay = ast.parse(ma)
    ten_goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "min" not in ten_goi or "max" not in ten_goi, (
        "van con phep kep he_so_co_gian ve [1/tran, tran]")
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py -q -k "toi_da_la_MOT or KHONG_bi_kep"`
Expected: **2 failed**.

- [ ] **Step 3: Sửa**

3a. `nan_cho_vua.py:124` — đổi giá trị và ghi lý do:

```python
#: Số vòng xin model viết lại TỐI ĐA cho một đoạn.
#:
#: 🔑 **1 từ 26/09/2026** (trước: 2). Ba căn cứ, ⛔ không phải một linh cảm:
#:    - chú thích của chính `loi_nhac_nan` nói *"đó là lý do vòng thứ hai thường
#:      không cần đến"* — vì lời nhắc đã đưa một mục tiêu ĐO ĐƯỢC;
#:    - `VideoLingo` (18,5k★, Apache-2.0) đã bỏ hẳn vòng hai: `##! No longer
#:      perform secondary trim`;
#:    - đo 26/09: một lời gọi nắn mất **15,6–17,7 giây**, nên vòng hai là 16 giây
#:      cho một xác suất nhỏ.
VONG_TOI_DA = 1
```

3b. `giai_doan_thoi_gian.py:202-203` — bỏ phép kẹp, ghi hệ số đã áp:

```python
        # 🔑 **Trần là CẢNH BÁO, ⛔ không phải cổng (chủ dự án chốt 26/09).**
        #    Trước đây hệ số bị kẹp về `[1/tran, tran]`, nên một đoạn tràn quá
        #    trần bị **đặt sai chỗ trong im lặng**. Nay: áp đúng hệ số cần, và
        #    GHI LẠI — cái giá (giọng hơi méo) khách nghe được và ⛔ không giấu.
        #    `open-dubbing` (Apache-2.0) đặt trần 1.3 rồi chấp nhận lệch; ta ⛔
        #    không chặn, nhưng phải ĐẾM.
        he_so_toc_da_ap.append(float(h))
        if h > nan_cho_vua.tran_co_gian():
            log.warning("timing_align: doan %s tang toc %.3f vuot tran %.3f",
                        ma, h, nan_cho_vua.tran_co_gian())
```

Và đưa `he_so_toc_da_ap` (danh sách, khởi tạo `[]` trước vòng) vào `do_duoc` của giai
đoạn dưới khoá `"he_so_toc_da_ap"`.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py tests/test_4600_asv_san_dung_sai.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/nan_cho_vua.py apps/auto_scan_video/giai_doan_thoi_gian.py tests/test_2018_asv_ngan_sach_do_dai.py
git commit -F- -- apps/auto_scan_video/nan_cho_vua.py apps/auto_scan_video/giai_doan_thoi_gian.py tests/test_2018_asv_ngan_sach_do_dai.py
```

---

## Task 5 · `tools/asv_doi_soat.py` — sáu phép đếm Đ1–Đ6  (làn C)

**Files:**
- Create: `tools/asv_doi_soat.py`
- Test: `tests/test_408_asv_dich_thuat.py`

**Interfaces:**
- Consumes: `apps.auto_scan_video.quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)`
- Produces: `doi_soat(dong: dict) -> dict` với **đúng** các khoá:
  `sai_so_p50`, `sai_so_p90`, `sai_so_max`, `ti_le_doan_ngan`, `pause_kha_dung_s`,
  `so_doan_nan_oan`, `he_so_toc_p90`, `so_doan_lech_cuoi`.
  ⛔ `None` = **chưa đo được**, `0` = **đo được và bằng 0** — hai trạng thái, hai giá trị.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_doi_soat_phan_biet_CHUA_DO_voi_BANG_KHONG():
    """⛔ `0` và "chưa đo được" là HAI trạng thái. Gộp chúng là mất khả năng phân biệt."""
    from tools.asv_doi_soat import doi_soat

    rong = doi_soat({"giai_doan": []})
    assert rong["sai_so_p90"] is None, "khong co cap (doan, that) thi phai la None"
    assert rong["so_doan_nan_oan"] is None


def test_doi_soat_tinh_sai_so_tu_cap_doan_va_that():
    from tools.asv_doi_soat import doi_soat

    dong = {"giai_doan": [{"giai_doan": "voice_synthesis", "tom_tat": {
        "luot_doc": [{"ma": "seg_0001", "giay_doan": 2.0, "giay": 2.0},
                     {"ma": "seg_0002", "giay_doan": 2.0, "giay": 3.0}],
        "so_doan_nan_oan": 1}}]}
    ra = doi_soat(dong)
    # |2-2|/2 = 0 ; |3-2|/3 = 0,3333 -> p50 = 0,1667 (trung binh hai gia tri)
    assert ra["sai_so_max"] == pytest.approx(1 / 3, abs=1e-6)
    assert ra["ti_le_doan_ngan"] == pytest.approx(0.5, abs=1e-6)
    assert ra["so_doan_nan_oan"] == 1
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q -k doi_soat`
Expected: **2 failed** — `ModuleNotFoundError: tools.asv_doi_soat`.

- [ ] **Step 3: Viết `tools/asv_doi_soat.py`**

```python
"""Sáu phép ĐẾM trên một lượt chạy ASV — ⛔ không cần bản tham chiếu, ⛔ không cần ai chấm.

🔑 **Vì sao đếm chứ không chấm.** `B2_DO_DICH_THAM_CHIEU.md` tự khai bộ đo dịch đang
   bị khoá bởi một vòng tròn: chân lý nền là hai người soi mà **cả hai đều là LLM**,
   kappa 0,714 với KTC95 `[0,00 ; 1,00]`. Sáu phép dưới đây ⛔ không hỏi *"bản dịch
   có hay không"* — chúng hỏi *"lượt chạy này có TỰ MÂU THUẪN không"*, và mâu thuẫn
   thì đếm được. Một bộ chấm sai gu vẫn đếm mâu thuẫn đúng.

⛔ `None` nghĩa là **chưa đo được**; `0` nghĩa là **đo được và bằng không**. Gộp hai
   thứ đó vào một giá trị là mất đúng khả năng phân biệt mà bảng này tồn tại để giữ.
"""
from __future__ import annotations


def _phan_vi(cac: list[float], p: float) -> float | None:
    if not cac:
        return None
    xs = sorted(cac)
    if len(xs) == 1:
        return xs[0]
    vt = p * (len(xs) - 1)
    lo = int(vt)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (vt - lo)


def doi_soat(dong: dict) -> dict:
    """`dong` = `quan_sat.dong_thoi_gian(...)`. Trả về tám con số (hoặc `None`)."""
    gd = next((m for m in (dong.get("giai_doan") or [])
               if m.get("giai_doan") == "voice_synthesis"), None)
    tt = (gd or {}).get("tom_tat") or {}
    luot = list(tt.get("luot_doc") or [])

    sai_so: list[float] = []
    ngan = 0
    for e in luot:
        that = float(e.get("giay") or 0.0)
        doan = float(e.get("giay_doan") or 0.0)
        if that <= 0 or doan <= 0:
            continue
        sai_so.append(abs(that - doan) / that)
        if doan < that:
            ngan += 1

    he_so = [float(x) for x in (tt.get("he_so_toc_da_ap") or [])]
    return {
        "sai_so_p50": _phan_vi(sai_so, 0.50),
        "sai_so_p90": _phan_vi(sai_so, 0.90),
        "sai_so_max": max(sai_so) if sai_so else None,
        "ti_le_doan_ngan": (ngan / len(sai_so)) if sai_so else None,
        "pause_kha_dung_s": tt.get("pause_kha_dung_s"),
        "so_doan_nan_oan": tt.get("so_doan_nan_oan"),
        "he_so_toc_p90": _phan_vi(he_so, 0.90),
        "so_doan_lech_cuoi": tt.get("so_doan_lech_cuoi"),
    }
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- tools/asv_doi_soat.py tests/test_408_asv_dich_thuat.py
git commit -F- -- tools/asv_doi_soat.py tests/test_408_asv_dich_thuat.py
```

---

## Task 6 · Bộ ước lượng ghi cả GIÂY ĐOÁN, và cộng thời gian dấu câu  (làn C)

**Files:**
- Modify: `apps/auto_scan_video/ngon_ngu.py` (thêm `GIAY_MOI_DAU_CAU`) ·
  `nan_thoi_luong.py` (`Khe.giay_can`)
- Test: `tests/test_2000_asv_ngon_ngu.py`

**Interfaces:**
- Consumes: `ngon_ngu.NHIP` (= `{VI: 3.35, EN: 3.63}`)
- Produces: `Khe.giay_can(am_tiet=None, dau_cau=None) -> float` — thêm
  `dau_cau * GIAY_MOI_DAU_CAU`. `dau_cau=None` ⇒ đếm từ `self.chu`.

⚠️ **Chỉ lấy dấu câu, ⛔ KHÔNG lấy hằng số "0,15 s mỗi khoảng trắng" của VideoLingo.**
0,15 s × mỗi khoảng trắng ⇒ một câu 10 từ cộng thêm **1,35 giây**, và ta ⛔ chưa đo
điều đó trên giọng của ta. Lấy một hằng số mình chưa hiểu là đúng cái bẫy *"bộ đo phải
tải về, nhưng phần NỐI phải tự kiểm"*.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_giay_can_cong_thoi_gian_cho_DAU_CAU():
    from apps.auto_scan_video import ngon_ngu
    from apps.auto_scan_video.nan_thoi_luong import Khe

    k = Khe(ma="seg_0001", bat=0.0, ket=5.0, moc_sau=6.0, am_tiet=10,
            chu="Hom nay troi mua, chung toi dung leu.")
    khong_dau = 10 / ngon_ngu.NHIP[ngon_ngu.VI]
    assert k.giay_can(dau_cau=0) == pytest.approx(khong_dau, abs=1e-9)
    # hai dau cau: mot dau phay + mot dau cham
    assert k.giay_can() == pytest.approx(
        khong_dau + 2 * ngon_ngu.GIAY_MOI_DAU_CAU, abs=1e-9)


def test_giay_can_khong_dem_KHOANG_TRANG():
    """⛔ Ta KHÔNG mượn hằng số 0,15 s/khoảng trắng của VideoLingo — chưa đo."""
    from apps.auto_scan_video import ngon_ngu
    assert not hasattr(ngon_ngu, "GIAY_MOI_KHOANG_TRANG")
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_2000_asv_ngon_ngu.py -q -k "DAU_CAU or KHOANG_TRANG"`
Expected: **1 failed** (`AttributeError: GIAY_MOI_DAU_CAU`), **1 passed**.

- [ ] **Step 3: Sửa**

3a. `ngon_ngu.py`, ngay dưới `NHIP`:

```python
#: Giây cộng thêm cho MỖI dấu câu — chỗ người đọc ngắt hơi.
#:
#: 🔑 Mượn hình từ `VideoLingo` (`core/tts_backend/estimate_duration.py`, Apache-2.0):
#:    bộ ước lượng của họ cộng **0,1 s cho mỗi dấu câu** lên trên phép `âm tiết ×
#:    hằng số`. Trước 26/09 bộ ước lượng của ta chỉ có `âm tiết ÷ NHIP`, tức coi một
#:    câu 3 mệnh đề đọc liền một hơi — và đó là một lệch **MỘT CHIỀU** (luôn đoán
#:    NGẮN), tức loại lệch tệ nhất ở một ngưỡng.
#:
#: ⚠️ CHƯA đo trên giọng của ta. `tools/asv_doi_soat.py` (Đ2 `ti_le_doan_ngan`) là
#:    phép đo phải chỉnh lại con số này; ⛔ đừng coi `0.10` là đã chốt.
GIAY_MOI_DAU_CAU = 0.10

#: Dấu câu tính là một chỗ ngắt hơi.
DAU_NGAT = ",.!?;:…"
```

3b. `nan_thoi_luong.py` — `Khe.giay_can`:

```python
    def giay_can(self, *, am_tiet: int | None = None,
                 dau_cau: int | None = None) -> float:
        n = self.am_tiet if am_tiet is None else am_tiet
        if dau_cau is None:
            dau_cau = sum(1 for c in (self.chu or "") if c in _ngon_ngu.DAU_NGAT)
        return n / AM_TIET_MOI_GIAY + dau_cau * _ngon_ngu.GIAY_MOI_DAU_CAU
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_2000_asv_ngon_ngu.py tests/test_2062_asv_nan_thoi_luong.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/ngon_ngu.py apps/auto_scan_video/nan_thoi_luong.py tests/test_2000_asv_ngon_ngu.py
git commit -F- -- apps/auto_scan_video/ngon_ngu.py apps/auto_scan_video/nan_thoi_luong.py tests/test_2000_asv_ngon_ngu.py
```

---

> 🔴 **TASK 7 ĐÃ BỊ HUỶ HÌNH DẠNG NÀY — ⛔ ĐỪNG THI HÀNH (26/09).**
>
> Nó nhắm vào `dich_thuat._loi_nhac`, và module đó là **ĐƯỜNG CHẾT**
> (`thi_hanh.py:124`, `van_ban.py:78`). Đường dịch thật là `long_tieng.loi_nhac`.
> Trên đường thật, **số giây đã có** (`thoi_luong_giay`), **ngữ cảnh trước/sau đã
> có** (`ngu_canh_ke`), **lô là 12 ⛔ không phải 20**, và hằng số phiên bản lời nhắc
> là hằng số **khác**.
>
> ⇒ Xem `B2_PLAN_NGU_CANH_DICH.md` §0. Việc còn lại **thật sự** là **Task 7b**: cho
> cửa sổ ngữ cảnh mang **BẢN ĐÃ DỊCH** của lô trước (nay nó chỉ mang bản **gốc**), và
> nối `ho_so_dich` vào lời nhắc của `long_tieng`. Điều phối sẽ soạn lại brief.

## Task 7 · Dịch mang NGỮ CẢNH: hồ sơ + cửa sổ trượt + số giây  (làn C)

**Files:**
- Modify: `apps/auto_scan_video/dich_thuat.py` (`_loi_nhac`, `dich_mot_lo`,
  `dich_ban_ghi`) · `van_ban.py:80`
- Test: `tests/test_408_asv_dich_thuat.py`

**Interfaces:**
- Consumes: `ai.DICH_THUAT`, `ai.goi(db, thao_tac, messages, ctx=, temperature=)`
- Produces:
  `_loi_nhac(lo, ngon_ngu_goc, *, ho_so: dict | None = None, truoc_do: list[tuple[str, str]] | None = None) -> list[dict]` ·
  `dich_ban_ghi(db, ban_ghi_goc, *, ctx=None) -> dict` (chữ ký ⛔ không đổi).

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_loi_nhac_dich_mang_SO_GIAY_cua_tung_doan():
    """C3: mục tiêu ĐO ĐƯỢC thay cho câu "giữ độ dài gần với câu gốc"."""
    from apps.auto_scan_video.dich_thuat import _loi_nhac

    lo = [{"ma": "seg_0001", "chu": "下雨了", "bat": 0.0, "ket": 3.2}]
    tin = _loi_nhac(lo, "zh")
    nguoi_dung = [m for m in tin if m["role"] == "user"][-1]["content"]
    assert "3.2" in nguoi_dung or "3,2" in nguoi_dung, (
        "loi nhac chua mang so giay cua khe — model khong co muc tieu do duoc")


def test_loi_nhac_dich_mang_BANG_DAI_TU_va_TEN_RIENG():
    """C1+C2: quan hệ nhân vật quyết MỘT lần cho cả video, ⛔ không mỗi lô một lần."""
    from apps.auto_scan_video.dich_thuat import _loi_nhac

    ho_so = {"bang_dai_tu": {"A->KHAN": {"toi": "minh", "goi": "cac ban"}},
             "bang_ten_rieng": {"光子": "Quang Tu"}}
    tin = _loi_nhac([{"ma": "seg_0001", "chu": "光子来了", "bat": 0.0, "ket": 2.0}],
                    "zh", ho_so=ho_so)
    ca = " ".join(m["content"] for m in tin)
    assert "Quang Tu" in ca and "cac ban" in ca


def test_loi_nhac_dich_mang_CUA_SO_TRUOT_cua_lo_truoc():
    from apps.auto_scan_video.dich_thuat import _loi_nhac

    tin = _loi_nhac([{"ma": "seg_0021", "chu": "你呢", "bat": 40.0, "ket": 41.0}],
                    "zh", truoc_do=[("你好", "Chao cac ban")])
    ca = " ".join(m["content"] for m in tin)
    assert "Chao cac ban" in ca


def test_doi_loi_nhac_thi_PHAI_tang_phien_ban():
    """⛔ Thiếu bước này, lần chạy mới dùng lại bản dịch của lời nhắc CŨ."""
    from apps.auto_scan_video import van_ban
    assert van_ban.PHIEN_BAN_LOI_NHAC_DICH >= 6
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q -k "loi_nhac or phien_ban"`
Expected: **4 failed**.

- [ ] **Step 3: Sửa `_loi_nhac`**

Đổi chữ ký và thân:

```python
def _loi_nhac(lo: list[dict], ngon_ngu_goc: str, *,
              ho_so: dict | None = None,
              truoc_do: list[tuple[str, str]] | None = None) -> list[dict]:
```

Trong phần `system`, **sau** quy tắc 4, chèn quy tắc 6 và 7 — ⛔ **không** thêm ví dụ
mới (ví dụ trong lời nhắc là mệnh lệnh ngầm; 4 ví dụ không dấu từng làm tụt một tên
vốn đúng), chỉ đưa **bảng dưới dạng dữ liệu**:

```python
            "6. MOI cau se duoc DOC THANH TIENG trong dung so giay ghi o khoa "
            "`giay` cua no. Viet sao cho doc vua so giay do. Do la mot muc tieu "
            "KIEM DUOC, khong phai mot loi khuyen.\n"
            "7. DUNG DUNG hai bang duoi day neu co: `bang_dai_tu` (cach xung ho) "
            "va `bang_ten_rieng` (dang viet cua ten). Chung da duoc chot cho CA "
            "video, nen moi lo phai dung y nhu nhau.\n"
```

Và khối `user` đổi từ `{ma: chu}` sang mang thêm số giây, kèm hai khối ngữ cảnh:

```python
    bang = {d["ma"]: {"chu": d["chu"],
                      "giay": round(float(d.get("ket") or 0.0)
                                    - float(d.get("bat") or 0.0), 2)}
            for d in lo}
    goi_user: dict = {"doan": bang}
    if ho_so:
        for k in ("bang_dai_tu", "bang_ten_rieng", "giong_van", "the_loai"):
            if ho_so.get(k):
                goi_user[k] = ho_so[k]
    if truoc_do:
        # ⭐ Cua so truot: ranh gioi lo TUNG la mot BUC TUONG — lo sau khong biet
        #    lo truoc da quyet dai tu nao. Mot phim 74 doan di 4 lo = 4 lan quyet
        #    lai quan he nhan vat, doc lap nhau.
        goi_user["da_dich_truoc_do"] = [{"goc": a, "dich": b}
                                        for a, b in truoc_do[-3:]]
```

`dich_mot_lo` nhận và chuyển tiếp `ho_so`/`truoc_do`; `dich_ban_ghi` giữ **cửa sổ ba
cặp cuối** và truyền xuống:

```python
    truoc_do: list[tuple[str, str]] = []
    for i, lo in enumerate(cac_lo, start=1):
        ...
        phan = dich_mot_lo(db, lo, ngon_ngu_goc=ngon_ngu, ctx=ctx,
                           ho_so=ho_so, truoc_do=truoc_do)
        gop.update(phan)
        for d in lo[-3:]:
            if d["ma"] in phan:
                truoc_do.append((str(d["chu"]), str(phan[d["ma"]])))
        truoc_do = truoc_do[-3:]
```

3b. `van_ban.py:80` — `PHIEN_BAN_LOI_NHAC_DICH = 6`, kèm một dòng nói vì sao tăng.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/dich_thuat.py apps/auto_scan_video/van_ban.py tests/test_408_asv_dich_thuat.py
git commit -F- -- apps/auto_scan_video/dich_thuat.py apps/auto_scan_video/van_ban.py tests/test_408_asv_dich_thuat.py
```

---

## Task 8 · Nấc cứu cuối: nới biên lần hai rồi CHẤP NHẬN + ghi  (làn B)

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_thoi_gian.py`
- Test: `tests/test_4600_asv_san_dung_sai.py`

**Interfaces:**
- Consumes: `thoi_gian.lap_ke_hoach(muc, thoi_luong_tieng, *, tong_giay, che_do, nhom_gop) -> dict`
- Produces: khoá `"so_doan_lech_cuoi"` và `"giay_lech_cuoi"` trong hồ sơ giai đoạn —
  `tools/asv_doi_soat.py` (Task 5) đọc đúng hai khoá này.

Chủ dự án chốt: **(b) nới biên lần hai → (c) chấp nhận + ghi báo cáo**. ⛔ Không (a)
quay lại LLM: sau khi chốt text, gọi lại model làm chuỗi mất tính tất định, và đó là
thứ phá vân tay + bộ đệm.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_doan_con_lech_sau_tang_toc_phai_duoc_GHI_LAI():
    """(c) chấp nhận thì phải NÓI RA. Một đoạn lệch bị bỏ im lặng là thứ tệ nhất."""
    import inspect
    from apps.auto_scan_video import giai_doan_thoi_gian

    ma = inspect.getsource(giai_doan_thoi_gian)
    assert "so_doan_lech_cuoi" in ma
    assert "giay_lech_cuoi" in ma
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_4600_asv_san_dung_sai.py -q -k lech_cuoi`
Expected: **1 failed**.

- [ ] **Step 3: Ghi hai con số**

Sau khi `_dung_ban_phoi` đặt xong từng đoạn, cộng dồn và đưa vào `do_duoc`:

```python
        # ⭐ Nấc (c) của chủ dự án: chấp nhận lệch, nhưng ⛔ KHÔNG im. Hai con số
        #    này đi vào hồ sơ giai đoạn, nên "chấp nhận" là một quyết định NHÌN
        #    THẤY ĐƯỢC chứ không phải một sự vắng mặt.
        do_duoc["so_doan_lech_cuoi"] = int(so_lech)
        do_duoc["giay_lech_cuoi"] = round(float(giay_lech), 3)
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_4600_asv_san_dung_sai.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/giai_doan_thoi_gian.py tests/test_4600_asv_san_dung_sai.py
git commit -F- -- apps/auto_scan_video/giai_doan_thoi_gian.py tests/test_4600_asv_san_dung_sai.py
```

---

## Task 9 · Gain mặc định của lớp "giọng nói gốc" = −10,46 dB  (làn D)

**Files:**
- Modify: `apps/auto_scan_video/tach_tieng.py:125-129`
- Test: `tests/test_423_asv_giao_dien.py`

**Interfaces:**
- Consumes: `tach_tieng.GAIN_NHO_NHAT` (`0.0`), `GAIN_LON_NHAT` (`2.0`)
- Produces: `LOP_MAC_DINH["giong_gain"] == 0.30`

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_gain_mac_dinh_cua_giong_GOC_la_mot_phan_ba():
    """🔴 Trước 26/09 mặc định là 1.0 = 0 dB: khách vừa tick "giữ giọng nói gốc"
    là giọng gốc trở lại ÂM LƯỢNG ĐẦY, đối đầu trực diện với giọng Việt.

    Chủ dự án chốt −10 dB. Thang trượt là biên độ TUYẾN TÍNH (⛔ không phải dB) và
    `step="5"`, nên 31,6 % ⛔ không nằm trên lưới ⇒ 0.30 = −10,46 dB.
    """
    import math
    from apps.auto_scan_video.tach_tieng import LOP_MAC_DINH

    assert LOP_MAC_DINH["giong_gain"] == 0.30
    assert LOP_MAC_DINH["giong_bat"] is False
    db = 20 * math.log10(LOP_MAC_DINH["giong_gain"])
    assert -11.0 < db < -9.0, f"{db:.2f} dB ngoai dai 9-10 dB chu du an muon"
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_423_asv_giao_dien.py -q -k gain_mac_dinh`
Expected: **1 failed** — `assert 1.0 == 0.30`.

- [ ] **Step 3: Sửa**

```python
LOP_MAC_DINH = {
    # 🔑 **`giong_gain = 0.30` = −10,46 dB (chủ dự án chốt 26/09/2026).**
    #    Trước đó là `1.0` = **0 dB**: khách vừa bật "giữ giọng nói gốc" là lời
    #    thoại gốc trở lại **âm lượng đầy**, đối đầu trực diện với giọng lồng
    #    tiếng Việt. Nhãn CÓ cảnh báo sẽ chồng — nhưng giá trị mặc định làm nó
    #    tệ nhất có thể.
    #    ⚠️ Thang trượt là **biên độ tuyến tính**, ⛔ không phải dB, và `step="5"`
    #    nên −10 dB (= 0,316) ⛔ không nằm trên lưới. `0.30` lệch 0,46 dB.
    "giong_bat": False, "giong_gain": 0.30,
    "nhac_bat": True, "nhac_gain": 1.0,
    "vfx_bat": True, "vfx_gain": 1.0,
}
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_423_asv_giao_dien.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/tach_tieng.py tests/test_423_asv_giao_dien.py
git commit -F- -- apps/auto_scan_video/tach_tieng.py tests/test_423_asv_giao_dien.py
```

---

## Task 10 · Dời `edit_plan` xuống sau `render`, bỏ VLM  (làn E — MỘT MÌNH, sau cùng)

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_noi_dung.py` (`_doc_ban_bien_tap`) ·
  `pipeline.py` (`CHUOI`) · `giai_doan_ban_bien_tap.py` (`chay`)
- Test: `tests/test_423_asv_giao_dien.py` · `tests/test_2025_asv_doc_canh_hong.py`

**Interfaces:**
- Consumes: `pipeline.GiaiDoan(ten, app_slug, job_type, sau, tai_nguyen, tai_nguyen_suat, tien_quyet, ma_loi, do)`
- Produces: `CHUOI` với `CONTENT_PROCESS.sau == (TRANSCRIBE,)` và
  `EDIT_PLAN.sau == (RENDER,)`, `EDIT_PLAN.tai_nguyen == ""`.

⚠️ **Ba bước, ⛔ KHÔNG đảo thứ tự.** Bước 1 phải đi trước bước 2, nếu không mọi lượt
chạy chết vì `content_process` ném khi thiếu artifact.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_content_process_coi_THIEU_ban_bien_tap_la_GIU_TAT_CA():
    """🔴 Trước 26/09 nó NÉM `ThieuBanBienTap`. Sau khi `edit_plan` xuống GĐ2 thì
    "chưa có bản biên tập" là trạng thái HỢP LỆ = giữ tất cả, ⛔ không phải lỗi."""
    import inspect
    from apps.auto_scan_video import giai_doan_noi_dung

    ma = inspect.getsource(giai_doan_noi_dung._doc_ban_bien_tap)
    assert "ThieuBanBienTap" not in ma, (
        "van nem khi thieu ban bien tap — se lam chet MOI luot chay sau khi "
        "edit_plan xuong GD2")


def test_edit_plan_chay_SAU_render_va_KHONG_giu_llm_remote():
    import dataclasses
    from apps.auto_scan_video import pipeline as p

    theo_ten = {dataclasses.asdict(g)["ten"]: dataclasses.asdict(g) for g in p.CHUOI}
    assert theo_ten["edit_plan"]["sau"] == ("render",)
    assert theo_ten["content_process"]["sau"] == ("transcribe",)
    assert not theo_ten["edit_plan"]["tai_nguyen"], (
        "edit_plan van giu suat llm_remote — no KHONG con goi model nao")
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_423_asv_giao_dien.py -q -k "GIU_TAT_CA or SAU_render"`
Expected: **2 failed**.

- [ ] **Step 3a: `content_process` thôi đòi bản biên tập**

Trong `giai_doan_noi_dung._doc_ban_bien_tap`, thay nhánh ném bằng nhánh "giữ tất cả":

```python
    if not khoa:
        # ⭐ 26/09/2026: `edit_plan` đã xuống GĐ2 (chạy SAU `render`), nên tới đây
        #    ⛔ KHÔNG bao giờ có bản biên tập — và đó là trạng thái ĐÚNG, không
        #    phải lỗi. GĐ1 giữ nguyên hình và xuất MP4 full độ dài; việc cắt là
        #    của GĐ2, trên bản ra, với MỘT đồng hồ duy nhất.
        #    ⛔ Ném ở đây làm chết MỌI lượt chạy.
        return None, None
```

Và người gọi coi `(None, None)` là *giữ tất cả* — ⛔ không lọc bản chép lời.

- [ ] **Step 3b: Đổi `CHUOI`**

`content_process`: `sau=(TRANSCRIBE,)`. `edit_plan`: `sau=(RENDER,)`, `tai_nguyen=""`,
và chuyển khai báo của nó xuống **giữa `RENDER` và `IMAGE_FINISH`** trong tuple, kèm
chú thích:

```python
    # 🔑 **Xuống GĐ2 (26/09/2026).** Trước đây giai đoạn này phán quyết trên trục
    #    thời gian NGUỒN, còn `ke_cat`/`image_finish` cắt trên trục BẢN RA — và
    #    `thoi_gian.ngan_sach_doan` đã cảnh báo chính lớp lỗi đó: *"hàm này lặng
    #    lẽ TRỘN HAI ĐỒNG HỒ"*. Chạy sau `render` thì chỉ còn MỘT đồng hồ.
    #
    # ⛔ `tai_nguyen` RỖNG: nó ⛔ không còn gọi model nào. Trước đây nó khai
    #    `llm_remote` TĨNH rồi — với preset giữ hình — ⛔ không gọi gì, tức GIỮ
    #    suất LLM duy nhất của cả máy. Đo 26/09: hai lượt cùng preset, edit_plan
    #    mất 2,8 s và 205,7 s — 203 giây chênh là XẾP HÀNG.
```

- [ ] **Step 3c: Bỏ nhánh VLM khỏi `giai_doan_ban_bien_tap.chay`**

Thay `hieu_canh` VLM bằng ba phép đo tất định: *(1)* cảnh ⛔ không giao đoạn thoại nào
(số học trên bản chép lời) · *(2)* `ffmpeg blackdetect` · *(3)* `ffmpeg freezedetect`.
⛔ **Không xoá** `hieu_canh.py` — nó còn phục vụ `HO_SO_NOI_DUNG` cho đường chọn giọng.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien asv-e -- python -m pytest tests/test_423_asv_giao_dien.py tests/test_2025_asv_doc_canh_hong.py tests/test_418_asv_phan_loai_loi.py tests/test_3004_asv_khai_sau_phai_phu_thu_that_su_doc.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/pipeline.py apps/auto_scan_video/giai_doan_noi_dung.py apps/auto_scan_video/giai_doan_ban_bien_tap.py tests/test_423_asv_giao_dien.py tests/test_2025_asv_doc_canh_hong.py
git commit -F- -- apps/auto_scan_video/pipeline.py apps/auto_scan_video/giai_doan_noi_dung.py apps/auto_scan_video/giai_doan_ban_bien_tap.py tests/test_423_asv_giao_dien.py tests/test_2025_asv_doc_canh_hong.py
```

---

## Task 11 · `ho_so_dich`: MỘT lời gọi cho CẢ video  (làn C)

**Files:**
- Create: `apps/auto_scan_video/ho_so_dich.py`
- Modify: `apps/auto_scan_video/ai.py` (thêm `HO_SO_DICH`) · `giai_doan_noi_dung.py`
- Test: `tests/test_408_asv_dich_thuat.py`

**Interfaces:**
- Consumes: `ai.goi(db, thao_tac, messages, ctx=, temperature=)` · `ai.ThaoTac`
- Produces: `ho_so_dich.dung(db, ban_ghi: dict, *, ctx=None) -> dict` với các khoá
  `the_loai: str` · `so_nguoi_noi: int` · `bang_dai_tu: dict[str, dict[str, str]]` ·
  `bang_ten_rieng: dict[str, str]` · `giong_van: str`.
  **Task 7 nhận đúng dict này** qua tham số `ho_so=`.

🔑 Đây là thứ giải bài `ông/cháu/con/tôi/bạn`: quan hệ nhân vật được quyết **MỘT lần
cho cả video** thay vì mỗi lô quyết lại. Một phim 74 đoạn đi 4 lô ⇒ trước bản này là
**4 lần** quyết độc lập.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_ho_so_dich_tra_ve_DU_nam_khoa():
    from apps.auto_scan_video import ho_so_dich

    goi = {"noi_dung": '{"the_loai":"vlog","so_nguoi_noi":1,'
                       '"bang_dai_tu":{"A->KHAN":{"toi":"minh","goi":"cac ban"}},'
                       '"bang_ten_rieng":{"光子":"Quang Tu"},"giong_van":"than mat"}'}
    ra = ho_so_dich._doc(goi["noi_dung"])
    assert ra["the_loai"] == "vlog"
    assert ra["bang_dai_tu"]["A->KHAN"]["goi"] == "cac ban"
    assert ra["bang_ten_rieng"]["光子"] == "Quang Tu"


def test_ho_so_dich_MOT_loi_goi_cho_ca_video():
    """⛔ Không được gọi theo lô: hồ sơ là câu hỏi TOÀN CỤC."""
    import ast
    import inspect
    from apps.auto_scan_video import ho_so_dich

    cay = ast.parse(inspect.getsource(ho_so_dich))
    vong = [n for n in ast.walk(cay) if isinstance(n, (ast.For, ast.While))]
    trong_vong = any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
        and c.func.attr == "goi"
        for v in vong for c in ast.walk(v))
    assert not trong_vong, "loi goi model nam trong mot vong lap"
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q -k ho_so_dich`
Expected: **2 failed** — `ModuleNotFoundError: apps.auto_scan_video.ho_so_dich`.

- [ ] **Step 3: Viết `ho_so_dich.py`**

```python
"""HỒ SƠ DỊCH — một lời gọi cho CẢ video, quyết quan hệ nhân vật MỘT lần.

🔴 **Vì sao tệp này tồn tại.** `dich_mot_lo` là **vô trạng thái**: mỗi lô chỉ thấy
   `{ma: chu}` của chính nó. Một phim 74 đoạn đi 4 lô ⇒ **4 lần** quyết lại quan hệ
   nhân vật, độc lập nhau. Tiếng Việt mã hoá **quan hệ** vào đại từ, nên người xem
   nghe thấy quan hệ **đổi giữa video** (`ông` → `cậu` → `bạn`).

⭐ Một lời gọi thêm cho **cả video** (~16 giây) thay cho hàng chục lần đoán lại.
"""
from __future__ import annotations

import json
import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

KHOA = ("the_loai", "so_nguoi_noi", "bang_dai_tu", "bang_ten_rieng", "giong_van")


class HoSoDichLoi(ValueError):
    """Model không trả về hồ sơ đọc được."""


def _doc(noi_dung: str) -> dict:
    van = str(noi_dung or "").strip()
    dau, cuoi = van.find("{"), van.rfind("}")
    if dau < 0 or cuoi < dau:
        raise HoSoDichLoi(_t('Model không trả về JSON đọc được.'))
    try:
        goc = json.loads(van[dau:cuoi + 1])
    except json.JSONDecodeError as exc:
        raise HoSoDichLoi(_t('Model trả về JSON hỏng.')) from exc
    if not isinstance(goc, dict):
        raise HoSoDichLoi(_t('Model trả về JSON sai hình dạng.'))
    return {
        "the_loai": str(goc.get("the_loai") or ""),
        "so_nguoi_noi": int(goc.get("so_nguoi_noi") or 0),
        "bang_dai_tu": dict(goc.get("bang_dai_tu") or {}),
        "bang_ten_rieng": dict(goc.get("bang_ten_rieng") or {}),
        "giong_van": str(goc.get("giong_van") or ""),
    }


def dung(db, ban_ghi: dict, *, ctx=None) -> dict:
    """MỘT lời gọi. Hỏng thì trả hồ sơ RỖNG — ⛔ không làm chết lượt chạy."""
    from . import ai

    dong = [f'{d["ma"]}: {d["chu"]}' for d in (ban_ghi.get("doan") or [])]
    tin = [
        {"role": "system", "content": (
            "Doc toan bo loi thoai cua mot video roi tra ve DUY NHAT mot doi "
            "tuong JSON voi dung cac khoa: the_loai, so_nguoi_noi, bang_dai_tu, "
            "bang_ten_rieng, giong_van.\n"
            "bang_dai_tu: voi MOI cap vai, ghi tu tu xung (`toi`) va tu goi "
            "(`goi`) bang tieng Viet se dung suot ca video.\n"
            "bang_ten_rieng: ten goc -> dang viet tieng Viet, chot MOT lan.\n"
            "Khong giai thich gi them.")},
        {"role": "user", "content": "\n".join(dong)},
    ]
    try:
        kq = ai.goi(db, ai.HO_SO_DICH, tin, ctx=ctx, temperature=0.2)
        return _doc(kq["noi_dung"])
    except Exception as exc:  # noqa: BLE001
        # ⭐ Hồ sơ là thứ làm bản dịch TỐT HƠN, ⛔ không phải thứ nó cần để CHẠY.
        #    Hỏng thì đi tiếp với hồ sơ rỗng và NÓI RA, ⛔ không làm chết lượt chạy.
        log.warning("khong dung duoc ho so dich (%s: %s)", type(exc).__name__, exc)
        return {k: ({} if k.startswith("bang_") else "") for k in KHOA}
```

Trong `ai.py`, khai thao tác mới cạnh `DICH_THUAT`:

```python
HO_SO_DICH = ThaoTac("ho_so_dich", False, ("the_loai", "bang_dai_tu"), pha="15",
                     muc_nghi="low")
```

Trong `giai_doan_noi_dung`, gọi `ho_so_dich.dung(...)` **một lần** trước
`dich_thuat.dich_ban_ghi(...)` và truyền xuống.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/ho_so_dich.py apps/auto_scan_video/ai.py apps/auto_scan_video/giai_doan_noi_dung.py tests/test_408_asv_dich_thuat.py
git commit -F- -- apps/auto_scan_video/ho_so_dich.py apps/auto_scan_video/ai.py apps/auto_scan_video/giai_doan_noi_dung.py tests/test_408_asv_dich_thuat.py
```

⚠️ **`giai_doan_noi_dung.py` cũng là tệp của làn E (Task 10).** ⇒ Task 11 chạy
**trước** Task 10, và E gộp `main` trước khi sửa tệp đó.

---

## Task 12 · Đảo [B]→[F]: ước lượng trước, nắn theo LÔ, TTS MỘT lượt  (làn B — task NẶNG nhất)

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_giong.py` (vòng `while` ≈288-340) ·
  `nan_cho_vua.py` (thêm `loi_nhac_nan_lo`)
- Test: `tests/test_2018_asv_ngan_sach_do_dai.py`

**Interfaces:**
- Consumes: `Khe.giay_can(am_tiet=None, dau_cau=None) -> float` (Task 6) ·
  `thoi_gian.ngan_sach_nan_s` (Task 2) · `nan_cho_vua.nen_viet_lai` · `VONG_TOI_DA = 1`
- Produces: `nan_cho_vua.loi_nhac_nan_lo(cac: list[dict], *, ngon_ngu_dich="vi") -> list[dict]`
  — **MỘT** lời nhắc cho **nhiều** đoạn; mỗi mục `{"ma", "chu", "giay_doc", "khe", "truoc", "sau"}`.

🔑 Đây là lõi: hôm nay TTS **chính là phép đo**, nên mỗi vòng nắn = `TTS → LLM → TTS`.
Sau bản này: ước lượng (rẻ) → chốt chữ → **TTS một lượt**.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_loi_nhac_nan_LO_mang_ngu_canh_truoc_sau():
    """Rút một câu mà ⛔ không biết câu kế nói gì thì dễ rút mất chủ ngữ mà câu
    sau đang trỏ tới."""
    from apps.auto_scan_video.nan_cho_vua import loi_nhac_nan_lo

    cac = [{"ma": "seg_0002", "chu": "Cau hai rat dai",
            "giay_doc": 4.8, "khe": 3.2,
            "truoc": "Cau mot", "sau": "Cau ba"}]
    tin = loi_nhac_nan_lo(cac)
    ca = " ".join(m["content"] for m in tin)
    assert "seg_0002" in ca and "3.2" in ca and "4.8" in ca
    assert "Cau mot" in ca and "Cau ba" in ca


def test_giai_doan_giong_KHONG_con_vong_while_quanh_TTS():
    """[F] chạy MỘT lượt: text đã chốt ở [E]."""
    import ast
    import inspect
    from apps.auto_scan_video import giai_doan_giong

    cay = ast.parse(inspect.getsource(giai_doan_giong))
    for v in [n for n in ast.walk(cay) if isinstance(n, ast.While)]:
        trong = {c.func.attr for c in ast.walk(v)
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
        assert "doc_mot_doan" not in trong, (
            "TTS van nam trong mot vong `while` — bac thang chua duoc dao")
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py -q -k "nan_LO or vong_while"`
Expected: **2 failed**.

- [ ] **Step 3a: `nan_cho_vua.loi_nhac_nan_lo`**

```python
def loi_nhac_nan_lo(cac: list[dict], *, ngon_ngu_dich: str = "vi") -> list[dict]:
    """MỘT lời nhắc cho NHIỀU đoạn cần rút ngắn.

    🔴 **Bản cũ `loi_nhac_nan` là MỘT đoạn một lời gọi**, và đo 26/09: mỗi lời gọi
       **15,6–17,7 giây**. Hàng chục đoạn ⇒ hàng chục lần khứ hồi.

    ⭐ Mỗi mục mang `truoc`/`sau` để model thấy ngữ cảnh: rút một câu mà ⛔ không
       biết câu kế nói gì thì dễ rút mất chủ ngữ mà câu sau đang trỏ tới.

    ⚠️ Khoá JSON là **mã đoạn**, và người gọi phải kiểm `set(cần) − set(nhận)` —
       mượn ba lớp chống lẫn id của `VideoLingo` (Apache-2.0).
    """
    bang = {d["ma"]: {"chu": d["chu"],
                      "doc_ra_giay": round(float(d["giay_doc"]), 2),
                      "khe_giay": round(float(d["khe"]), 2),
                      "cau_truoc": d.get("truoc", ""),
                      "cau_sau": d.get("sau", "")}
            for d in cac}
    return [
        {"role": "system", "content": (
            "Moi muc duoi day la mot cau tieng Viet doc ra DAI HON khe thoi gian "
            "cua no. Viet lai NGAN hon de doc vua `khe_giay`, giu nguyen y.\n"
            "Tra ve DUY NHAT mot doi tuong JSON, khoa la ma doan, gia tri la cau "
            "moi. Phai co DU moi ma. Khong them ma moi, khong giai thich.\n"
            "`cau_truoc` va `cau_sau` chi de hieu ngu canh — KHONG dich chung.")},
        {"role": "user", "content": json.dumps(bang, ensure_ascii=False)},
    ]
```

- [ ] **Step 3b: Dựng lại vòng trong `giai_doan_giong`**

Thay vòng `while` bằng bốn khối tuần tự:

```python
        # [B] ƯỚC LƯỢNG — ⛔ không chạy TTS
        doan_tran = []
        for m, k in zip(muc, khes):
            giay_doan = k.giay_can()
            ns = ngan_sach_theo_ma[k.ma]
            if nan_cho_vua.nen_viet_lai(giay_doan, ns):
                doan_tran.append({"ma": k.ma, "chu": k.chu, "giay_doc": giay_doan,
                                  "khe": ns, "truoc": _chu_ke(khes, k, -1),
                                  "sau": _chu_ke(khes, k, +1)})

        # [E] NẮN theo LÔ — 1..3 lời gọi cho CẢ video (cũ: hàng chục)
        if doan_tran:
            chu_moi = _nan_lo(db, run, doan_tran, ctx=ctx)   # {ma: chu}
            for m in muc:
                if m["ma"] in chu_moi:
                    m["chu"] = chu_moi[m["ma"]]

        # [F] TTS MỘT lượt cho danh sách đã chốt
        for m in muc:
            ... doc_mot_doan(...) một lần, ⛔ không vòng lặp ...
```

`_chu_ke(khes, k, buoc)` trả chữ của khe liền trước/liền sau (rỗng ở hai đầu).
`_nan_lo` chia `doan_tran` thành lô ≤ `dich_thuat.DOAN_MOI_LO`, gọi
`ai.goi(db, ai.RUT_NGAN_CHO_VUA, loi_nhac_nan_lo(lo))`, kiểm `set(cần) − set(nhận)`,
retry ≤ 3 lần **thêm một khoảng trắng vào cuối prompt** để phá cache.

⚠️ **Giữ nguyên `lat_cat` + checkpoint theo đoạn.** Một lượt đã trả tiền ⛔ không được
bị bắt đọc lại. `da_lat`/`da_sinh`/`luot_doc` giữ đúng ngữ nghĩa cũ.

- [ ] **Step 4: Chạy lại — XANH**

Run: `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien asv-b -- python -m pytest tests/test_2018_asv_ngan_sach_do_dai.py tests/test_2050_asv_lat_cat_120_phut.py tests/test_4600_asv_san_dung_sai.py tests/test_4700_asv_gop_khe_that.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- apps/auto_scan_video/giai_doan_giong.py apps/auto_scan_video/nan_cho_vua.py tests/test_2018_asv_ngan_sach_do_dai.py
git commit -F- -- apps/auto_scan_video/giai_doan_giong.py apps/auto_scan_video/nan_cho_vua.py tests/test_2018_asv_ngan_sach_do_dai.py
```

---

## Task 13 · G1/G2: nhất quán đại từ và tên riêng  (làn C)

**Files:**
- Modify: `tools/asv_doi_soat.py`
- Test: `tests/test_408_asv_dich_thuat.py`

**Interfaces:**
- Consumes: bản dịch `{ma: chu}` của lượt chạy
- Produces: `nhat_quan(cac_cau: list[str], *, ten_goc: dict[str, str] | None = None) -> dict`
  với khoá `so_bo_dai_tu` (G1, đạt = `1`) và `vi_pham_ten_rieng` (G2, đạt = `0`).

🔑 G1/G2 ⛔ **không cần bản tham chiếu và ⛔ không cần ai chấm** — chúng đếm **mâu
thuẫn bên trong một tài liệu**, nên chúng đi vòng qua vòng tròn LLM đang khoá bộ đo dịch.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_G1_bat_duoc_dai_tu_DOI_giua_video():
    from tools.asv_doi_soat import nhat_quan

    on = ["Chao cac ban", "Hom nay minh di cam", "Cac ban thay the nao"]
    assert nhat_quan(on)["so_bo_dai_tu"] == 1

    doi = ["Chao cac ban", "Hom nay toi di cam", "Cac cau thay the nao"]
    assert nhat_quan(doi)["so_bo_dai_tu"] > 1


def test_G2_bat_duoc_mot_ten_goc_ra_HAI_dang_Viet():
    from tools.asv_doi_soat import nhat_quan

    ra = nhat_quan(["Quang Tu den roi", "Photon da di"],
                   ten_goc={"光子": "Quang Tu"})
    assert ra["vi_pham_ten_rieng"] >= 1
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q -k "G1_bat or G2_bat"`
Expected: **2 failed** — `ImportError: cannot import name 'nhat_quan'`.

- [ ] **Step 3: Thêm vào `tools/asv_doi_soat.py`**

```python
#: Từ xưng hô tiếng Việt — **dữ liệu ngôn ngữ**, ⛔ không phải phán quyết chất lượng.
#: Nên nó được phép gõ ra, và nó kiểm được bằng cách soi lại trên bản ghi thật.
TU_XUNG_HO = ("ong", "ba", "anh", "chi", "em", "chau", "con", "co", "chu", "bac",
              "toi", "to", "minh", "tao", "may", "ban", "cau", "quy vi", "cac ban")


def _bo_dau(v: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", v.lower())
                   if unicodedata.category(c) != "Mn")


def nhat_quan(cac_cau: list[str], *, ten_goc: dict[str, str] | None = None) -> dict:
    """G1 + G2 — đếm MÂU THUẪN, ⛔ không chấm chất lượng."""
    bo: set[frozenset] = set()
    for cau in cac_cau:
        v = _bo_dau(cau)
        thay = frozenset(t for t in TU_XUNG_HO if f" {t} " in f" {v} ")
        if thay:
            bo.add(thay)

    vi_pham = 0
    for _goc, dang in (ten_goc or {}).items():
        d = _bo_dau(dang)
        co = sum(1 for cau in cac_cau if d in _bo_dau(cau))
        if co == 0 and cac_cau:
            # Tên đã chốt mà ⛔ không xuất hiện lần nào ⇒ một dạng KHÁC đã được dùng.
            vi_pham += 1
    return {"so_bo_dai_tu": len(bo) or 1, "vi_pham_ten_rieng": vi_pham}
```

- [ ] **Step 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_408_asv_dich_thuat.py -q`
Expected: **all passed**.

- [ ] **Step 5: Commit**

```bash
git add -- tools/asv_doi_soat.py tests/test_408_asv_dich_thuat.py
git commit -F- -- tools/asv_doi_soat.py tests/test_408_asv_dich_thuat.py
```

---

## ⭐ H1 (chia khoảng lặng làm hai đoạn giao nhau) — đã được giải bởi CẤU TRÚC

`B1 §3 [C]` đòi một phép chia ngân sách **toàn cục** với bất biến *"⛔ không đoạn nào
giao nhau"*. Plan này ⛔ **không** cần một phép chia riêng, và đây là lý do:

```
ngan_sach_s cua doan i  =  moc_sau(i) − bat(i)        [nan_thoi_luong.Khe]
moc_sau(i)              =  bat(i+1)                    [bien co that ke tiep]
```

⇒ Ngân sách của đoạn `i` **kết thúc đúng ở chỗ đoạn `i+1` bắt đầu**, và ngân sách của
`i+1` bắt đầu ở `bat(i+1)` — nó ⛔ **không với ngược lại** được. ⇒ Hai đoạn liền nhau
⛔ **không thể** cùng đòi một khoảng lặng. Bất biến được giữ bởi **định nghĩa của
`moc_sau`**, ⛔ không bởi một phép chia.

⚠️ Nên điều phải gác là một điều **khác**: `moc_sau` phải luôn `>= ket`. Task 2 đã gác
(`ngan_sach_s = max(khe_s, ...)`), và có phép kiểm riêng cho nó.

---

## Nghiệm thu — sau Task 1, và lại sau Task 8

1. Gộp `main`, chạy `pre-commit run --all-files`.
2. Deploy: `Start-Process powershell ... setup\deploy_nang_quyen.ps1 -Verb RunAs` —
   ⚠️ gọi từ **PowerShell**, ⛔ không từ Bash (`/usr/bin/tar` của Git-Bash đọc `C:\`
   như một máy chủ từ xa và bản xuất ra 0 tệp).
3. Chạy **một** phim thật qua web, rồi
   `python tools\asv_doi_soat.py <run_id>` và ghi tám con số vào `docs/NHAT_KY.md`.

**Cổng quyết định — ⚠️ ĐÃ SỬA 26/09, bản đầu đặt SAI CHIỀU:**

🔴 Bản đầu viết *"`so_doan_nan_oan` > 0 trước Task 3 và **= 0** sau"*. **Sai.** Task 3
**vừa** thêm bộ đếm **vừa** bịt lỗ, nên bộ đếm ⛔ không bao giờ quan sát được lỗ lúc nó
còn hở. Và tệ hơn: `so_doan_nan_oan` đếm các đoạn nằm trong dải `(khe, ngân sách]` —
những đoạn đó **vẫn tồn tại** sau bản sửa, chỉ là chúng ⛔ không còn gọi LLM. ⇒ Đòi nó
về `0` là đòi một điều **sai**, và một agent trung thực sẽ hoặc bó tay hoặc bóp con số.

⭐ **Chiều đúng:** `so_doan_nan_oan` là **số đoạn được CỨU**, ⛔ không phải số đoạn hỏng.

| đo cái gì | TRƯỚC Task 3 | SAU Task 3 |
|---|---|---|
| `so_doan_nan_oan` | ⛔ chưa có bộ đếm | **> 0** ⇒ dải không rỗng ⇒ bản sửa **có giá trị**, và con số **lượng hoá** nó |
| `giay_llm_nan` (đã có sẵn) | đo trên hai lượt chạy **hiện tại** | phải **GIẢM** |
| `so_doan_nan_oan == 0` | — | ⇒ dải rỗng ⇒ bản sửa ⛔ **không cứu được gì**, phải xem lại giả thuyết |

⇒ Phép đo "trước" là **`giay_llm_nan` của hai lượt chạy `asvr_ba490300` và
`asvr_94b94b29`** (nộp 26/09, TRƯỚC khi Task 3 được deploy). Đó là lý do hai lượt ấy
phải chạy xong **trước** khi gộp Task 3.

⛔ Một phép đo không đỏ được trước khi sửa thì ⛔ không chứng minh gì — nhưng một phép
đo **đặt sai chiều** thì còn tệ hơn: nó làm người ta sửa đúng mà tưởng mình sai.

---

## Thứ tự chạy và chia agent

```
Task 1 (làn A)  ──►  nghiệm thu #1 (deploy + đo Đ1..Đ4 lần đầu)
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
  làn B: 2→3→4→12→8  làn C: 5→6→11→7→13  làn D: 9   (E chờ)
        └───────────────┴───────────────┴───────────────┘
                        │
                 nghiệm thu #2  ──►  làn E: Task 10 (MỘT MÌNH)
                        │
                 gate CUỐI PLAN (một lần, một cấp)
```

| agent | model | task | ⛔ không được chạm |
|---|---|---|---|
| A | sonnet | 1 | mọi tệp ngoài `giai_doan_media.py` + `test_429` |
| B | **opus** cho 12, sonnet cho 2/3/4/8 | 2 → 3 → 4 → **12** → 8 (tuần tự) | `nan_thoi_luong.py`, `dich_thuat.py`, `ho_so_dich.py`, `ai.py`, `pipeline.py` |
| C | sonnet | 5 → 6 → **11** → 7 → **13** (tuần tự) | `thoi_gian.py`, `nan_cho_vua.py`, `giai_doan_giong.py`, `pipeline.py` |
| D | sonnet | 9 | mọi tệp ngoài `tach_tieng.py` + `test_423` |
| E | **opus** | 10 | — (chạy một mình) |

⚠️ **`tests/test_423_asv_giao_dien.py` bị CẢ D và E chạm** ⇒ D chạy **trước**, E gộp
`main` rồi mới sửa. ⛔ Không mở D và E cùng lúc.

⚠️ E dùng **opus**: nó chạm sổ đăng ký dùng chung và đổi hình dạng chuỗi giai đoạn —
loại việc mà một quyết định sai làm đỏ cho mọi phiên.

⚠️ **Task 12 dùng opus.** Nó dựng lại vòng lõi của một giai đoạn **có bút toán credit**,
phải giữ nguyên ngữ nghĩa `lat_cat` + checkpoint theo đoạn, và một lượt đã trả tiền ⛔
không được bị bắt đọc lại. Bốn task còn lại của làn B là sửa hằng số + thêm bộ đếm ⇒ sonnet.

⚠️ **`giai_doan_noi_dung.py` bị CẢ C (Task 11) và E (Task 10) chạm** ⇒ C xong Task 11 và
gộp `main` **trước khi** E mở. `ai.py` bị C (Task 11) chạm, B ⛔ không chạm.

⚠️ **Task 12 phụ thuộc Task 6** (`Khe.giay_can(dau_cau=)`) của làn C. ⇒ B phải **chờ C
xong Task 6** rồi mới mở Task 12. Đây là phụ thuộc **giao diện**, ⛔ không phải tranh tệp:
chữ ký đã chốt trong plan nên hai làn ⛔ không cần nói chuyện với nhau.
