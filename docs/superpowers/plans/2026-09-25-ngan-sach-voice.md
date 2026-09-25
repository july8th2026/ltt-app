# Ngân sách voice tính cả khoảng lặng — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.

**Goal:** `nan_cho_vua` phán quyết "vừa / không vừa" trên **cùng một ngân sách** mà bộ
lập kế hoạch dùng, thay vì trên `ket - bat`.

**Architecture:** Tách `dung_duoc` (thoại + 70 % khoảng lặng) khỏi thân `lap_ke_hoach`
thành hàm riêng trong `thoi_gian.py`; `khe_cua` gọi **chính** hàm ấy. Một phép tính,
hai người gọi.

**Tech Stack:** Python 3.13 · pytest · ⛔ không gói mới.

**Spec:** `docs/superpowers/specs/2026-09-25-ngan-sach-voice-va-moc-thoi-gian-design.md`

## Global Constraints

- ⛔ **KHÔNG gate** (L1/L2/L3). Chốt 25/09: gate **một lần, một cấp, CUỐI PLAN**.
- ⛔ Không đổi `TY_LE_MUON_KHOANG_LANG` (0.7) · `TRAN_TANG_TOC` (1.15) · `DUNG_SAI_DAI`
  (0.08). ⚠️ Hai cái sau **khoá lẫn nhau** ở `nan_cho_vua.py:108` — khẳng định **cấp
  module**, sai thì **app ⛔ không nạp được**, ⛔ không phải một test đỏ.
- ⛔ Không `python -c` cho việc tính · ⛔ không `| tail` (xoá mã lỗi) · `-n ≤ 4`.
- Gộp `main` xong: `pre-commit run --all-files` (`N-56`: merge ⛔ không chạy bánh cóc).
- Commit kết thúc bằng `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Số test: đọc `tools/cay_rieng.py` trước khi chọn. ⛔ Dải `4100-4199` của phiên khác.

---

### Task 1: Tách `ngan_sach_dung_duoc` — refactor THUẦN, hành vi ⛔ KHÔNG đổi

**Files:**
- Modify: `apps/auto_scan_video/thoi_gian.py` — thêm hàm; `lap_ke_hoach:186-193` gọi nó
- Test: tệp mới trong dải số của bạn

**Interfaces:**
- Produces: `ngan_sach_dung_duoc(bat_ra: list[int], ket_ra: list[int], i: int, tong_ms: int) -> int`

- [ ] **Step 1: Viết phép kiểm ĐỎ — hàm chưa tồn tại**

```python
def test_dung_duoc_bang_cong_thuc_cu():
    from apps.auto_scan_video import thoi_gian as tg
    bat = [0, 10_000]
    ket = [3_000, 13_000]
    # ngan sach doan 0 = 10.000 ms; noi thoai = 3.000; lang = 7.000
    # dung duoc = 3.000 + int(7.000 * 0,7) = 7.900
    assert tg.ngan_sach_dung_duoc(bat, ket, 0, 20_000) == 7_900


def test_doan_CUOI_lay_toi_het_nguon():
    from apps.auto_scan_video import thoi_gian as tg
    bat = [0]
    ket = [3_000]
    # ngan sach = 20.000; lang = 17.000; dung duoc = 3.000 + 11.900 = 14.900
    assert tg.ngan_sach_dung_duoc(bat, ket, 0, 20_000) == 14_900
```

- [ ] **Step 2: Chạy — phải ĐỎ**

`python -m pytest <tệp> -q` — kỳ vọng `AttributeError: ... ngan_sach_dung_duoc`

- [ ] **Step 3: Viết hàm, rồi cho `lap_ke_hoach` gọi nó**

```python
def ngan_sach_dung_duoc(bat_ra: list[int], ket_ra: list[int], i: int,
                        tong_ms: int) -> int:
    """Ngan sach THAT cua doan `i`: thoai + phan khoang lang duoc muon.

    MOT cho khai. `lap_ke_hoach` va `nan_cho_vua.khe_cua` cung goi ham nay.
    Hai ban khai cua mot luat la cach chung lech nhau - xem N-24, N-55, N-58.
    """
    bat_goc = int(bat_ra[i])
    ngan_sach = ngan_sach_doan(bat_ra, i, tong_ms)
    noi_thoai = max(0, int(ket_ra[i]) - bat_goc)
    khoang_lang = max(0, ngan_sach - noi_thoai)
    return noi_thoai + int(khoang_lang * TY_LE_MUON_KHOANG_LANG)
```

Rồi ở `thoi_gian.py:186-193` thay bốn dòng tính tay bằng một lời gọi:

```python
        bat_goc = bat_ra[i]
        dung_duoc = ngan_sach_dung_duoc(bat_ra, ket_ra, i, tong_ms)
```

⚠️ Kiểm xem `ngan_sach` / `noi_thoai` / `khoang_lang` còn được dùng ở **dưới** trong
cùng vòng lặp không. Còn thì **giữ nguyên chúng**, chỉ thay dòng `dung_duoc`.

- [ ] **Step 4: Chạy lại — XANH, và bộ test `thoi_gian` cũ vẫn XANH**

Tìm tệp test bằng `python tools\thanh_phan.py --test auto_scan_video`.
⭐ Đây là **refactor thuần** — một phép cũ đỏ nghĩa là bạn **đã đổi hành vi**, ⛔ không
phải phép kiểm sai.

- [ ] **Step 5: Commit**

```bash
git add apps/auto_scan_video/thoi_gian.py tests/<tệp mới>
git commit -m "thoi_gian: tach ngan_sach_dung_duoc - mot cho khai cho luat 70%"
```

---

### Task 2: `khe_cua` dùng ngân sách thật

**Files:**
- Modify: `apps/auto_scan_video/nan_cho_vua.py:136-147`
- Modify: `apps/auto_scan_video/giai_doan_giong.py:178`
- Test: cùng tệp Task 1

**Interfaces:**
- Consumes: `thoi_gian.ngan_sach_dung_duoc`
- Produces: `khe_cua(muc: list[dict], i: int, tong_giay: float) -> float`

⭐ **Chỉ MỘT chỗ gọi `khe_cua`** (`giai_doan_giong.py:178`). Mọi hàm phía sau
(`can_nan`, `ket_luan`, `co_gian_du_khong`) nhận `khe` là **một số float** ⇒ ⛔ không lan.

- [ ] **Step 1: Viết phép kiểm ĐỎ**

```python
def test_doan_VUA_neu_tinh_ca_khoang_lang():
    from apps.auto_scan_video import nan_cho_vua as ncv
    muc = [{"ma": "s1", "bat": 0.0, "ket": 3.0},
           {"ma": "s2", "bat": 10.0, "ket": 13.0}]
    khe = ncv.khe_cua(muc, 0, 20.0)
    assert khe == 7.9, f"ky vong 7,9 s (3 + 70% cua 7), nhan {khe}"
    assert not ncv.can_nan(3.5, khe), "3,5 s VUA trong 7,9 s ma van doi nan"


def test_doan_CUOI_co_ngan_sach_duong():
    from apps.auto_scan_video import nan_cho_vua as ncv
    muc = [{"ma": "s1", "bat": 0.0, "ket": 3.0}]
    assert ncv.khe_cua(muc, 0, 20.0) > 0, "doan cuoi ngan sach 0 => LUON goi LLM"
```

- [ ] **Step 2: Chạy — phải ĐỎ** (`TypeError`: `khe_cua` nhận một tham số)

- [ ] **Step 3: Viết hàm mới**

```python
def khe_cua(muc: list[dict], i: int, tong_giay: float) -> float:
    """Ngan sach cua doan `i`: thoai + 70 % khoang lang phia sau.

    Goi CHINH `thoi_gian.ngan_sach_dung_duoc` - mot phep tinh, hai nguoi goi.

    Ban cu tra `ket - bat` (chi phan dang noi), voi ly do "cau thoai phai khop
    cai mieng dang nhep". Do la ly le LONG TIENG KHOP MOI. Hop dong san pham
    chot 22/09 la MOT GIONG THUYET MINH (`ban_ghi.py:47`) => ly do ay da chet.
    Hau qua do duoc 25/09: 49 luot goi LLM moi phim, 27 phut cho.
    """
    from .thoi_gian import _ms, ngan_sach_dung_duoc
    bat = [_ms(m.get("bat") or 0.0) for m in muc]
    ket = [_ms(m.get("ket") or 0.0) for m in muc]
    return ngan_sach_dung_duoc(bat, ket, i, _ms(tong_giay)) / 1000.0
```

- [ ] **Step 4: Sửa chỗ gọi `giai_doan_giong.py:178`**

Đổi `khe = nan_cho_vua.khe_cua(m)` sang dạng truyền `(muc, i, tong_giay)`.

⚠️ **Đọc vòng lặp quanh dòng 178 TRƯỚC** — cần biết tên biến danh sách, biến chỉ số,
và `tong_giay` lấy từ đâu. ⛔ Đừng đoán tên biến.

- [ ] **Step 5: Chạy — XANH, và bộ test `nan_cho_vua` + `giai_doan_giong` vẫn XANH**

⚠️ Phép kiểm nào đỏ vì **kỳ vọng con số cũ** thì sửa kỳ vọng **và nói rõ trong commit**
rằng hành vi **cố ý đổi**. ⛔ Đừng sửa mã cho khớp phép kiểm cũ.

- [ ] **Step 6: Commit**

```bash
git add apps/auto_scan_video/nan_cho_vua.py apps/auto_scan_video/giai_doan_giong.py tests/<tệp>
git commit -m "nan_cho_vua: khe_cua tinh ca khoang lang - het goi LLM cho doan VON DA VUA"
```

---

### Task 3: `voice_synthesis` khai `llm_remote`

**Files:** Modify `apps/auto_scan_video/pipeline.py` — mục `VOICE_SYNTHESIS`

- [ ] **Step 1: Phép kiểm ĐỎ**

```python
def test_voice_synthesis_khai_llm_remote():
    from apps.auto_scan_video import pipeline
    g = pipeline.THEO_TEN["voice_synthesis"]
    assert g.tai_nguyen == "llm_remote", (
        "voice_synthesis goi may B 49 lan moi phim (do 25/09) nhung khong khai "
        "=> 49 luot chay NGOAI co che dem suat cua nen tang")
```

- [ ] **Step 2: Chạy — ĐỎ**

- [ ] **Step 3: Thêm `tai_nguyen="llm_remote", tai_nguyen_suat=1`** vào mục
  `VOICE_SYNTHESIS`, theo đúng khuôn `CONTENT_PROCESS` (`pipeline.py:282`)

- [ ] **Step 4: Chạy — XANH**

⚠️ Chạy **cả bộ test hàng đợi job**: đổi khai báo tài nguyên là **đổi cách nạp job**.
Phép nào đỏ ⇒ **báo điều phối**, ⛔ đừng tự nới.

- [ ] **Step 5: Commit**

```bash
git add apps/auto_scan_video/pipeline.py tests/<tệp>
git commit -m "pipeline: voice_synthesis khai llm_remote - 49 luot khong con ngoai so"
```

---

### Task 4: ĐO trước / sau

- [ ] **Step 1** Đếm lượt gọi máy B trong nhật ký lượt chạy **đã có** (25/09) = **49**
- [ ] **Step 2** Chạy lại đúng phim ấy sau Task 1-3, đếm lại
- [ ] **Step 3** Báo bảng `trước → sau`, kèm số đoạn vào nấc 2 và số sửa thành công

🔴 **⛔ KHÔNG hứa con số.** Nếu chỉ giảm `49 → 40` thì gốc nằm **chỗ khác** và phải
**tìm tiếp** — ⛔ không được coi là xong.

⚠️ **Cần điều phối duyệt trước khi chạy**: chủ dự án đã dừng mọi lượt ASV trên worker
thật cho tới khi lắp xong hai giai đoạn.

---

### Task 5: ĐO mốc thời gian ba đường ASR

- [ ] **Step 1** Trên **một** phim thật, xuất mốc từng từ của ba đường:
  `faster-whisper` thô (thứ production đang chạy) · `WhisperX` đã căn (sau bản vá
  `N-59`) · `CapCut ASR` (`D:\Viral\resources\app-src\capcut_asr.py` — kho của chủ dự
  án, ⛔ **CHỈ ĐỌC**, ⛔ không chạy `.exe`/`.bat` trong đó)

- [ ] **Step 2** So lệch mốc từng từ giữa ba đường, trên cùng phim

- [ ] **Step 3** Báo bảng + đề nghị. ⛔ **Không tự đổi engine** — quyết định của chủ dự án.

⭐ Lý do task này tồn tại: ngân sách **đứng trên** mốc. Sửa công thức ngân sách mà mốc
vào sai thì chỉ là **đổi một loại sai này lấy một loại sai khác**.
