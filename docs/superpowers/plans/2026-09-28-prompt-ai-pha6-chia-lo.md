# PROMPT AI — pha 6: CHIA LÔ sinh cảnh (+ huỷ ở ranh lô)

> **Cho người thi hành:** BẮT BUỘC dùng `superpowers:subagent-driven-development`
> hoặc `superpowers:executing-plans` để làm theo từng task. Các bước dùng `- [ ]`.

**Mục tiêu một câu:** một lượt 20 cảnh hiện sinh trong **một** lượt gọi LLM và chất
lượng suy dần theo thứ tự cảnh; pha này chia thành nhiều lô nhỏ có lịch sử, để cảnh
thứ 20 tốt bằng cảnh thứ 2.

**Kiến trúc:** MỘT job (`prompt_ai_ommi.generate`, không thêm job type), chia lô
**bên trong** worker, báo tiến độ ở ranh lô. Huỷ hợp tác đi qua `ctx.progress_counter`
— thứ nền tảng **đã có**. Quyết toán theo số cảnh đã giao.

**Spec / quyết định:** [`../../PROMPT_AI/QUYET_DINH_26-09.md`](../../PROMPT_AI/QUYET_DINH_26-09.md) — **Q-16** (chia lô, chặn E5), **Q-17** (giữ trần 20), **Q-18** (hình dạng).

---

## 0. ⚠️ ĐÍNH CHÍNH HAI TIỀN ĐỀ CỦA Q-18 — đọc trước khi làm bất cứ gì

Q-18 được chốt dựa trên hai câu tôi nói **sai** về `prompt_canh`. Đo lại trên mã
(28/09) thì:

| Q-18 nói | Mã thật sự |
|---|---|
| *"cờ huỷ là phần DUY NHẤT là mã mới"* | ⛔ Sai — nền tảng **đã có đủ**: `ctx.progress()` và `ctx.progress_counter()` tự **ném `JobCancelled`** khi job bị huỷ (`job_runner.py:189`, `:222`), cộng `ctx.is_cancelled()`, `jobs.cancel()`, và **hai cửa HTTP đã tồn tại** (`server/api/jobs.py:537`, `server/routes/jobs.py:259`) |
| *"tiền đã tính theo lượt gọi nên tự đúng"* | ⛔ Sai cho app NÀY. Đó là `prompt_canh` (`credit_cost -> 0`, thu qua `runtime_noi_bo.luong`). `prompt_ai_ommi` tính tiền ở **tầng job**: `manifest._cost` → `_director_cost = max(4, min(18, 2 + ceil(n/3)*2))`, và `provider.generate_json` gọi LLM **trực tiếp**, ⛔ không qua `runtime_noi_bo` |

⭐ **Tin tốt từ đính chính thứ nhất:** phần việc của pha này nhỏ hơn Q-18 tưởng —
⛔ không phải viết cơ chế huỷ, chỉ phải **gọi đúng chỗ**.

🔴 **Hệ quả của đính chính thứ hai, và đây là chỗ phải cẩn thận nhất cả pha.** Tiền
được **giữ lúc nộp** và quyết toán lúc xong. Nên huỷ giữa đường đặt ra một câu về
tiền mà Q-18 tưởng đã tự giải:

- Nền tảng mặc định **hoàn TOÀN BỘ** khi job bị huỷ (`job_runner._hoan_credit`).
- ⇒ Nếu ta vừa hoàn hết vừa giữ lại cảnh đã sinh, khách **lấy được việc miễn phí**,
  và lặp được: nộp 20 cảnh, huỷ sau lô 1, nhận 10 cảnh, làm lại. Đó là một đường
  lạm dụng thật, ⛔ không phải một ca hiếm.

⭐ **Thuốc, đã đo là chạy được mà ⛔ KHÔNG chạm `credit.py` hay `job_runner.py`:**
handler tự gọi `credit.quyet_toan(db, user_id, job_id, actual=<giá số cảnh đã giao>)`
rồi **ném lại** `JobCancelled`. Runner sau đó gọi `_hoan_credit` → `credit.hoan()` →
gặp `_da_ket_so(job_id)` là `True` → **`return` ngay, không hoàn**.

⚠️ Chốt chịu lực ấy nằm ở `hoan()`, ⛔ **không** ở `so_da_giu()`: `so_da_giu` chỉ
cộng bút toán `CREDIT_HOLD` nên nó **vẫn > 0** sau khi quyết toán. Tôi đã tưởng sai
chỗ này một lần khi đọc. Task 5 có phép kiểm chốt đúng đường đó, vì nếu nó đổi thì
khách **được hoàn cả khoản vừa thu** — mất doanh thu im lặng.

---

## 0b. 🔴 NẮN 28/09 — Task 2/3 nhắm SAI MODULE (phát hiện trước khi viết dòng nào)

Plan gốc bảo chia lô vào `services/breakdown.py` rồi nối vào `jobs.py`. **Sai.** Đo:

```
grep -rn "breakdown(" apps/prompt_ai_ommi/   ->  CHI MOT cho goi:
    routes/storyboard.py:349   (mot ROUTE dong bo, framework nap tu CSDL)
jobs.py::_handle_generate      ->  director_prompt(params) -> provider.generate_json
```

⇒ `breakdown()` ⛔ **không hề** nằm trên đường job. Đường khách đi — và đường Q-16 đo
(`scene_count=20` → 19/20 cảnh) — là **director**:

```
jobs.py::_handle_generate
  -> composer.director_prompt(params)          MOT loi nhac cho CA 20 canh
  -> provider.generate_json(...)               MOT loi goi
  -> _normalize_result(raw, params)            jobs.py:17 cat ve `scene_count`
```

`_director_cost` cũng tính theo `scene_count` của chính đường này. Nên chia lô phải
vào **đây**, ⛔ không vào `breakdown.py`.

### ⭐ Và đường đúng lại RẺ HƠN đường plan gốc

`composer.director_prompt` (dòng 109-118) đã có sẵn **hai** ô cần thiết:

| ô | plan gốc phải tự dựng | thực tế đã có |
|---|---|---|
| cỡ lô | tham số mới cho `breakdown` | `scenes=params["scene_count"]` |
| lịch sử | ghép chuỗi tay vào lời nhắc | `existing=json.dumps(existing[:20])` — dựng cho đúng việc giữ liên mạch |

⇒ Một lô = gọi lại `director_prompt` với `params` đã thay hai khoá ấy:

```python
for dau, cuoi in chia_lo.cac_lo(n):
    p_lo = {**params, "scene_count": cuoi - dau + 1,
            "existing_scenes": chia_lo.cua_so_lich_su(da_sinh)}
    system, prompt = director_prompt(p_lo)
    raw, tokens = provider.generate_json(system, prompt, model=model)
    da_sinh += list(raw.get("scenes") or [])[:cuoi - dau + 1]
    tong_tokens += tokens
    bao_lo(len(da_sinh), n)
```

⛔ `breakdown.py` **KHÔNG đổi**. ⛔ Không tra `framework`. `_normalize_result` **không đổi**.

### Ba giả định khác của plan cũng SAI, đã tra và sửa

| plan gốc giả định | đo được |
|---|---|
| `library.khung_mac_dinh()` tồn tại | ⛔ **không có hàm nào tên vậy** — và nay không cần |
| `tokens_used` trả `0` được | ⛔ `tests/test_130:73` **ghim** `result["tokens_used"] == 123` ⇒ phải **cộng dồn** qua các lô |
| `ctx.user_id` có | ⛔ `JobContext.__init__(job_id, gpu_uuid)` — **không có** `user_id`. Lấy từ `db.get(Job, job_id).user_id` |

⭐ Cả ba đều là chỗ plan **tự đánh dấu** *"người thi hành phải tra trước"*. Chúng lộ ra
trong **một** lượt đo, trước khi viết dòng nào — đó là giá trị của việc ghi ⛔ ra thay vì
viết một lời gọi trông hợp lý.

### Task sau khi nắn

| # | trước | sau |
|---|---|---|
| 1 | `chia_lo.py` số học thuần | **giữ nguyên** |
| 2 | sửa `breakdown.py` | **`jobs.py::_sinh_theo_lo`** dùng `director_prompt` từng lô |
| 3 | nối `bao_lo` ở `jobs.py` | **gộp vào Task 2** (cùng một hàm) |
| 4 | `max_runtime_s` | **giữ nguyên** |
| 5 | huỷ + quyết toán | **giữ nguyên**, `user_id` lấy từ `Job` |
| 6 | đóng pha | **giữ nguyên** |

⇒ 6 task → **5 task**. Các khối mã trong §6 (Task 2 cũ) ⛔ **không dùng nữa**; đọc §0b này.

---
## 1. Global Constraints

Mọi task đều phải thoả, ⛔ không nhắc lại trong từng task:

- ⛔ **KHÔNG thêm job type.** `job_types=("prompt_ai_ommi.generate", ...)` giữ nguyên:
  `tests/test_159_prompt_ai_h26.py` ghim bộ ấy **đúng bằng** và đó là cố ý — đổi tên
  làm job đang xếp hàng thành mồ côi.
- ⛔ **KHÔNG chạm** `platform_core/credit.py`, `platform_core/jobs.py`,
  `platform_core/job_runner.py`. Chủ dự án chọn hình dạng này chính vì nó không đụng
  các tệp có bút toán thật.
- ⛔ **KHÔNG đổi** `manifest._cost` / `_director_cost`. Bảng giá đã chốt ở Q-17
  (19 và 20 cảnh **cùng** 16 credit) và đang sống trên production.
- **Trần cảnh** đọc từ `project_schema.MAX_SCENES`, ⛔ không gõ lại `20`.
- Test mới: số trong dải trống, kiểm bằng `python tools\check_so_test.py`.
- ⛔ Test **không được ghi vào cây**. Cần kho git thì dựng trong `tmp_path`.
- Giữ kết dòng từng tệp theo `git show HEAD:<tệp>`; tệp trộn thì ghép theo **từng dòng**.
- Log viết **không dấu** (bánh cóc `check_i18n` tính chuỗi có dấu là chuỗi hiện cho khách).
- Chuỗi trong `print()` của công cụ phải **ASCII** (`tests/test_309`).
- Trong phiên: ⛔ KHÔNG gate. Chỉ `python tools	hanh_phan.py --test app:prompt_ai_ommi`
  rồi `python -m pytest <tệp> -q`. ⛔ Không bọc `pytest` trong `chay_nang.py`.
- `git commit --only <đường dẫn từng tệp>`, ⛔ không `git add -A`.

---

## 2. Phạm vi: pha 6a làm gì, và cái gì CỐ Ý để ngoài

| | Trong pha 6a | Vì sao |
|---|---|---|
| Chia lô sinh cảnh + lịch sử chống trôi | ✅ | Đây là **mục tiêu** Q-16: chất lượng suy ở cảnh 20 |
| Báo tiến độ theo lô | ✅ | Đồng thời là thứ mở đường huỷ hợp tác |
| Huỷ ở ranh lô + quyết toán theo cảnh đã giao | ✅ | Tiền phải đúng, ⛔ không cho việc miễn phí |
| Trần thời gian khớp trần cảnh + phép kiểm chốt | ✅ | `prompt_ai_ommi` **chưa khai** `max_runtime_s` |
| **Giữ lại cảnh đã sinh sau khi huỷ** | ⛔ **NGOÀI** — pha 6b | Xem §3 |

### 3. Vì sao "giữ lại cảnh đã sinh" bị đẩy sang pha 6b

Job director hiện **hoàn toàn không có CSDL**: `prompt_job_params` (`project_schema.py:190`)
truyền cả project **dưới dạng dict** và `_handle_generate` trả `prompt_package` trong
`result`; `ommi_canh` do **route** ghi, ⛔ không do job ghi. Và runner **bỏ nguyên**
`result` khi job đã `CANCELLED` (`job_runner.py:959` và `:1024` — cả nhánh lỗi lẫn
nhánh thành công).

⇒ Nên "giữ phần đã chạy" đòi một chỗ để ghi, tức phải thêm `brief_id` vào params và
cho job ghi `ommi_canh` từng lô. Đó là **đổi đường đi của một luồng đang sống trên
production** (pha 1–3), và nó ⛔ không cần thiết để đạt mục tiêu Q-16.

⭐ Và pha 6a vẫn **công bằng về tiền** mà không cần nó: khách huỷ thì trả đúng số
cảnh đã giao, ⛔ không phải trả cho cái chưa chạy. Cái mất là **công**, ⛔ không phải
**tiền** — và đó là đánh đổi đúng cho một pha phải hạ rủi ro.

---

## 4. Cấu trúc tệp — quyết định phân rã, chốt ở đây

| Tệp | Trách nhiệm | Task |
|---|---|---|
| **Tạo** `apps/prompt_ai_ommi/services/chia_lo.py` | **Thuần logic, ⛔ không I/O**: chia `n` thành các lô, dựng cửa sổ lịch sử, đếm số lượt gọi, tính giá phần đã giao | 1 |
| **Sửa** `apps/prompt_ai_ommi/services/breakdown.py` | Nhận `goi_llm` và `bao_lo` từ ngoài, lặp theo lô | 2 |
| **Sửa** `apps/prompt_ai_ommi/jobs.py` | Nối `ctx.progress_counter` vào `bao_lo`; bắt `JobCancelled`, quyết toán, ném lại | 3, 5 |
| **Sửa** `apps/prompt_ai_ommi/manifest.py` | Khai `max_runtime_s` suy TỪ `chia_lo`, ⛔ không gõ số | 4 |
| **Tạo** `tests/test_5570…5574` | Năm nhóm phép kiểm | 1–5 |

⭐ **Vì sao `chia_lo.py` tách khỏi `breakdown.py`:** phần **tính** (lô nào gồm cảnh nào,
cần bao nhiêu lượt gọi, giá phần đã giao) phải kiểm được ⛔ **không cần** LLM, ⛔ không
cần CSDL, ⛔ không cần job. `breakdown.py` hiện gọi `provider.generate_json` ngay trong
thân hàm nên mọi phép kiểm của nó phải giả lập provider. Một tệp thuần số học là chỗ
duy nhất các bất biến về **tiền** và về **trần thời gian** kiểm được rẻ — và một bất
biến về tiền chỉ đáng tin khi nó rẻ để chạy.

---

## 5. Task 1 — `chia_lo.py`: số học thuần

**Files:**
- Create: `apps/prompt_ai_ommi/services/chia_lo.py`
- Test: `tests/test_5570_chia_lo_so_hoc.py`

**Interfaces — Produces** (task sau dựa vào đúng các tên này):

```python
LO_CANH: int = 5     # so canh moi lo
LICH_SU: int = 5     # so canh gan nhat cho vao loi nhac lam lich su
def cac_lo(n: int) -> list[tuple[int, int]]: ...   # [(dau, cuoi)] 1-based, cuoi INCLUSIVE
def so_luot_goi(n: int) -> int: ...
def gia_phan_da_giao(so_canh_da_giao: int, params: dict) -> int: ...
def cua_so_lich_su(canh: list[dict]) -> list[dict]: ...
```

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
# tests/test_5570_chia_lo_so_hoc.py
from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo


def test_cac_lo_phu_HET_va_KHONG_chong_nhau():
    """Bat bien manh nhat cua tep nay: moi canh thuoc DUNG MOT lo."""
    for n in range(1, MAX_SCENES + 1):
        lo = chia_lo.cac_lo(n)
        phu = [i for dau, cuoi in lo for i in range(dau, cuoi + 1)]
        assert phu == list(range(1, n + 1)), f"n={n}: {lo}"


def test_so_luot_goi_KHOP_so_lo_thuc_te():
    """⛔ Khong go lai cong thuc: dem chinh cai `cac_lo` tra ve.

    Hai cho khai cung mot dieu la hai cho se lech, va cho lech nay di vao tran
    thoi gian — tuc khach tra tien roi job chet o tran.
    """
    for n in range(1, MAX_SCENES + 1):
        assert chia_lo.so_luot_goi(n) == len(chia_lo.cac_lo(n)), f"n={n}"


def test_gia_phan_da_giao_KHONG_BAO_GIO_vuot_gia_day_du():
    """Khach huy phai tra <= so da giu. ⛔ Khong duoc thu vuot."""
    from apps.prompt_ai_ommi.manifest import _cost
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day_du = _cost(p)
    for da_giao in range(0, MAX_SCENES + 1):
        gia = chia_lo.gia_phan_da_giao(da_giao, p)
        assert 0 <= gia <= day_du, f"da_giao={da_giao}: {gia} > {day_du}"
    assert chia_lo.gia_phan_da_giao(0, p) == 0, "chua giao canh nao thi KHONG thu"
    assert chia_lo.gia_phan_da_giao(MAX_SCENES, p) == day_du, (
        "giao du thi phai bang gia day du — neu khong, mot luot XONG binh thuong "
        "va mot luot huy o canh cuoi se thu hai so khac nhau cho cung mot hang")


def test_gia_phan_da_giao_KHONG_GIAM_khi_giao_them():
    """Don dieu. ⛔ Khong duoc co khe nao giao THEM mot canh lai thu IT hon."""
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day = [chia_lo.gia_phan_da_giao(k, p) for k in range(MAX_SCENES + 1)]
    assert day == sorted(day), day


def test_cua_so_lich_su_lay_DUOI_cung_va_khong_qua_LICH_SU():
    canh = [{"position": i} for i in range(1, 13)]
    ra = chia_lo.cua_so_lich_su(canh)
    assert len(ra) == chia_lo.LICH_SU
    assert [c["position"] for c in ra] == list(range(13 - chia_lo.LICH_SU, 13))
    assert chia_lo.cua_so_lich_su([]) == []
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ**

Chạy: `python -m pytest tests/test_5570_chia_lo_so_hoc.py -q`
Mong đợi: `ModuleNotFoundError: apps.prompt_ai_ommi.services.chia_lo`

- [ ] **Bước 3: viết `chia_lo.py`**

```python
"""Chia mot luot sinh canh thanh nhieu LO — thuan so hoc, KHONG I/O.

🔴 VI SAO CO TEP NAY. Do that 2 lan o `scene_count=20` (lan E, 27/09): ca hai lan
   tra **19/20** canh, va do dai truong `prompt` **co dan theo thu tu canh**
   (159->87 va 165->~90 ky tu) khi chi dung 67%/69% cua `_MAX_TOKENS = 8192`.

⭐ Ket luan quan trong hon con so: **chat luong suy TRUOC khi cham tran cung**, nen
   nang `_MAX_TOKENS` KHONG phai thuoc. `apps/prompt_canh` chia lo va do duoc toi
   250 canh (`LO_BUOC2=10`, `LO_BUOC3=5`, `LICH_SU_CANH=5`).

⛔ Tep nay KHONG import `provider`, KHONG import CSDL, KHONG import `jobs`. Do la
   dieu kien de cac bat bien ve TIEN va ve TRAN THOI GIAN kiem duoc ma khong phai
   gia lap LLM — va mot bat bien ve tien chi dang tin khi no re de chay.
"""
from __future__ import annotations

#: So canh moi lo. Lay 5 theo `prompt_canh.LO_BUOC3` — lo cang nho thi lich su
#: cang dat gia tri tuong doi, nhung so luot goi (va tran thoi gian) cang lon.
LO_CANH = 5

#: So canh gan nhat dua vao loi nhac lam lich su (`prompt_canh.LICH_SU_CANH = 5`).
LICH_SU = 5


def cac_lo(n: int) -> list[tuple[int, int]]:
    """`[(dau, cuoi)]` 1-based, `cuoi` INCLUSIVE. Phu het, khong chong nhau."""
    n = max(0, int(n))
    return [(d + 1, min(d + LO_CANH, n)) for d in range(0, n, LO_CANH)]


def so_luot_goi(n: int) -> int:
    """⭐ Dem chinh `cac_lo`, KHONG viet lai cong thuc.

    Hai cho khai cung mot dieu la hai cho se lech, va cho lech nay di vao
    `max_runtime_s` — tuc khach tra tien roi job chet o tran.
    """
    return len(cac_lo(n))


def gia_phan_da_giao(so_canh_da_giao: int, params: dict) -> int:
    """Gia cho `so_canh_da_giao` canh, dung DUNG bang gia cua `manifest`.

    ⭐ Goi lai `manifest._cost` voi `scene_count` = so canh da giao, chu KHONG
       nhan chia theo ti le: bang gia la mot ham BAC THANG (`2 + ceil(n/3)*2`, kep
       trong `[4, 18]`), nen mot phep nhan ti le se cho mot so **khong nam tren
       bang gia nao** — tuc mot so khach khong the doi soat.

    ⚠️ `0` canh tra `0`, KHONG tra san duoi `4`: san ay la gia cua mot luot CO giao
       hang. Huy truoc khi lo dau xong thi khach KHONG nhan gi.
    """
    from apps.prompt_ai_ommi.manifest import _cost
    if int(so_canh_da_giao) <= 0:
        return 0
    return _cost({**params, "scene_count": int(so_canh_da_giao)})


def cua_so_lich_su(canh: list[dict]) -> list[dict]:
    """`LICH_SU` canh GAN NHAT — chong troi ngu canh giua cac lo.

    ⛔ Khong dua CA danh sach vao loi nhac: lam the thi lo cuoi lai chinh la ca
       van ban dai ma pha nay sinh ra de tranh.
    """
    return list(canh[-LICH_SU:]) if canh else []
```

- [ ] **Bước 4: chạy lại, phải XANH**

Chạy: `python -m pytest tests/test_5570_chia_lo_so_hoc.py -q`

- [ ] **Bước 5: commit**

```bash
git commit --only apps/prompt_ai_ommi/services/chia_lo.py tests/test_5570_chia_lo_so_hoc.py -m "feat(ommi): chia_lo.py - so hoc chia lo, thuan, khong I/O"
```

---

## 6. Task 2 — `breakdown.py`: lặp theo lô, nhận hai hàm từ ngoài

**Files:**
- Modify: `apps/prompt_ai_ommi/services/breakdown.py` — hàm `breakdown()` ở dòng 104
- Test: `tests/test_5571_breakdown_chia_lo.py`

**Interfaces — Consumes:** `chia_lo.cac_lo`, `chia_lo.cua_so_lich_su` (Task 1).

**Interfaces — Produces:** chữ ký mới của `breakdown()`, thêm **hai tham số chỉ
định bằng tên, đều có mặc định** nên ⛔ không phá chỗ gọi cũ:

```python
def breakdown(db, *, framework, story_vi: str, n_scenes: int | None = None,
              model: str = "",
              goi_llm=None,      # (system, prompt, model) -> (raw: dict, tokens: int)
              bao_lo=None,       # (da_xong: int, tong: int) -> None ; duoc phep NEM
              ) -> list[dict]: ...
```

⭐ **Vì sao tiêm `goi_llm` thay vì gọi `provider` trực tiếp như hiện nay:** phép kiểm
của task này phải dựng được tình huống *"lô thứ 3 ném `JobCancelled`"*, và ⛔ không
có cách nào làm điều đó với một lời gọi `provider.generate_json` chôn trong thân hàm
mà không phải vá `provider` toàn cục — thứ làm phép kiểm ảnh hưởng các bài chạy song
song. Mặc định `None` ⇒ dùng `provider.generate_json`, nên mã hiện có ⛔ không đổi.

⚠️ **`bao_lo` được phép NÉM, và điều đó là cố ý.** Nó sẽ là `ctx.progress_counter`,
thứ ném `JobCancelled`. `breakdown()` ⛔ **không được bắt** ngoại lệ ấy — nó phải bay
lên `jobs.py`, chỗ duy nhất biết về tiền.

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
# tests/test_5571_breakdown_chia_lo.py
"""`breakdown()` chia lo, mang lich su, va KHONG bat `JobCancelled`."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import breakdown as bd
from apps.prompt_ai_ommi.services import chia_lo


class _Khung:
    """Khung du de `breakdown` chay — chi cac truong no doc."""
    default_n_scenes = 20
    breakdown_llm_prompt = "Sinh {N} canh tu: {STORY}"
    opening_section = ""
    composition_rules = ""
    negative_footer = ""


def _goi_dem(ghi: list) -> callable:
    """`goi_llm` gia: ghi lai tung loi nhac, tra ve dung so canh duoc yeu cau."""
    def goi(system: str, prompt: str, *, model: str = ""):
        ghi.append(prompt)
        import re
        m = re.search(r"canh (\d+) den (\d+)", prompt)
        dau, cuoi = (int(m.group(1)), int(m.group(2))) if m else (1, 1)
        return ({"scenes": [{"title": f"c{i}", "prompt": f"p{i}"}
                            for i in range(dau, cuoi + 1)]}, 10)
    return goi


def test_20_canh_di_qua_DUNG_so_lo_khong_phai_mot_luot():
    ghi: list[str] = []
    ra = bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=20,
                      goi_llm=_goi_dem(ghi))
    assert len(ghi) == chia_lo.so_luot_goi(20), (
        f"{len(ghi)} luot goi, dung ra {chia_lo.so_luot_goi(20)} — day la CA LY DO "
        f"pha 6 ton tai; mot luot goi duy nhat la trang thai TRUOC khi va")
    assert len(ra) == 20
    assert [c["position"] for c in ra] == list(range(1, 21)), "thu tu canh phai lien tuc"


def test_lo_thu_HAI_tro_di_MANG_lich_su_cua_lo_truoc():
    ghi: list[str] = []
    bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=20,
                 goi_llm=_goi_dem(ghi))
    assert "c1" not in ghi[0], "lo dau KHONG the co lich su"
    assert "c5" in ghi[1], (
        "lo 2 phai thay canh 5 cua lo 1 — thieu lich su thi chia lo lam ngu canh "
        "TROI, tuc doi mot loi (chat luong suy) lay mot loi khac (mat lien mach)")


def test_so_luot_bao_lo_KHOP_so_lo():
    moc: list[tuple[int, int]] = []
    bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=20,
                 goi_llm=_goi_dem([]), bao_lo=lambda da, tong: moc.append((da, tong)))
    assert len(moc) == chia_lo.so_luot_goi(20)
    assert moc[-1] == (20, 20), f"moc cuoi phai la (20, 20), dang la {moc[-1]}"
    assert [d for d, _ in moc] == sorted(d for d, _ in moc), "bo dem phai TANG"


def test_bao_lo_NEM_thi_breakdown_KHONG_bat():
    """⛔ `breakdown` khong duoc bat `JobCancelled` — no phai bay len `jobs.py`.

    Bat o day nghia la job ket thuc BINH THUONG sau khi bi huy, va tien duoc
    quyet toan DAY DU cho mot luot chi giao mot phan.
    """
    class _Huy(Exception):
        pass

    def bao(da: int, tong: int) -> None:
        if da >= 10:
            raise _Huy()

    with pytest.raises(_Huy):
        bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=20,
                     goi_llm=_goi_dem([]), bao_lo=bao)


def test_MOT_canh_thi_van_dung_MOT_lo_khong_phai_khong_lo():
    ghi: list[str] = []
    ra = bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=1,
                      goi_llm=_goi_dem(ghi))
    assert len(ghi) == 1 and len(ra) == 1


def test_lo_tra_THIEU_canh_thi_bu_chu_KHONG_lam_lech_thu_tu():
    """Bat bien cu cua `breakdown` phai song sot qua chia lo.

    Ban truoc bu canh thieu bang `_auto_fill_scene`. Voi nhieu lo, mot lo tra
    thieu KHONG duoc lam cac lo sau lech chi so — day dung la ca `19/20` da do.
    """
    def goi_thieu(system: str, prompt: str, *, model: str = ""):
        import re
        m = re.search(r"canh (\d+) den (\d+)", prompt)
        dau, cuoi = (int(m.group(1)), int(m.group(2))) if m else (1, 1)
        canh = [{"title": f"c{i}", "prompt": f"p{i}"} for i in range(dau, cuoi)]
        return ({"scenes": canh}, 10)

    ra = bd.breakdown(None, framework=_Khung(), story_vi="x" * 50, n_scenes=20,
                      goi_llm=goi_thieu)
    assert len(ra) == 20, "tong so canh phai DUNG bang yeu cau"
    assert [c["position"] for c in ra] == list(range(1, 21))
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ**

Chạy: `python -m pytest tests/test_5571_breakdown_chia_lo.py -q`
Mong đợi: `TypeError: breakdown() got an unexpected keyword argument 'goi_llm'`

- [ ] **Bước 3: sửa `breakdown()`**

Thay thân hàm từ dòng `chosen_model = model or provider.model_mac_dinh()` trở đi:

```python
    chosen_model = model or provider.model_mac_dinh()
    goi = goi_llm or (lambda s, p, *, model="": provider.generate_json(s, p, model=model))

    # ⭐ MOT lo = MOT loi goi. Lich su la `LICH_SU` canh gan nhat, KHONG phai ca
    #    danh sach — dua het vao thi lo cuoi lai la ca van ban dai ma pha nay
    #    sinh ra de tranh.
    scenes: list[dict] = []
    lo = chia_lo.cac_lo(target)
    for dau, cuoi in lo:
        lich_su = chia_lo.cua_so_lich_su(scenes)
        loi_nhac = prompt.replace(
            "{N}", f"{cuoi - dau + 1} (canh {dau} den {cuoi} trong tong {target})")
        if lich_su:
            loi_nhac += "\n\nCanh da sinh (giu lien mach, KHONG lap lai):\n" + \
                "\n---\n".join(f"{c['position']}. {c.get('title') or ''}: "
                               f"{c.get('prompt') or ''}" for c in lich_su)
        raw, _tokens = goi(system, loi_nhac, model=chosen_model)

        # ⚠️ Bu canh thieu NGAY TRONG LO, khong doi den cuoi: mot lo tra thieu ma
        #    khong bu ngay se lam moi lo sau lech chi so — dung ca `19/20` da do.
        tho = list((raw or {}).get("scenes") or [])[:cuoi - dau + 1]
        for k in range(cuoi - dau + 1):
            if k < len(tho):
                scenes.append(_clean_scene(tho[k], dau + k - 1))
            else:
                scenes.append(_auto_fill_scene(dau + k - 1))

        if bao_lo is not None:
            # ⛔ KHONG boc try/except: `bao_lo` la `ctx.progress_counter`, thu NEM
            #    `JobCancelled`. Bat o day nghia la job ket thuc BINH THUONG sau
            #    khi bi huy, va tien duoc quyet toan DAY DU cho mot luot chi giao
            #    mot phan. Ngoai le nay PHAI bay len `jobs.py`.
            bao_lo(len(scenes), target)

    for i, c in enumerate(scenes):
        c["position"] = i + 1
    return scenes
```

Và thêm `from apps.prompt_ai_ommi.services import chia_lo` vào khối import.

- [ ] **Bước 4: chạy lại, phải XANH**

Chạy: `python -m pytest tests/test_5571_breakdown_chia_lo.py tests/test_5543_breakdown_scene_count_matches_default.py tests/test_5544_breakdown_uses_framework_prompt.py tests/test_5545_breakdown_scene_structural_invariants.py -q`

⚠️ Ba tệp `5543`/`5544`/`5545` là các bất biến **đã có** của `breakdown`. Chúng phải
xanh **mà không sửa** — nếu phải sửa một cái, dừng và đọc lại: nghĩa là chia lô vừa
đổi một hành vi ⛔ không ai yêu cầu đổi.

- [ ] **Bước 5: commit**

```bash
git commit --only apps/prompt_ai_ommi/services/breakdown.py tests/test_5571_breakdown_chia_lo.py -m "feat(ommi): breakdown chia lo + lich su, bao_lo duoc phep nem"
```

---

## 7. Task 3 — `jobs.py`: nối tiến độ theo lô

**Files:**
- Modify: `apps/prompt_ai_ommi/jobs.py` — `_handle_generate` (dòng 61–102)
- Test: `tests/test_5572_jobs_bao_lo_va_tien_do.py`

**Interfaces — Consumes:** chữ ký `breakdown(..., goi_llm=, bao_lo=)` (Task 2).

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
# tests/test_5572_jobs_bao_lo_va_tien_do.py
"""`_handle_generate` phai NOI `ctx.progress_counter` vao `bao_lo`.

⭐ Day la cho ca co che huy duoc "mua" mien phi: `progress_counter` tu NEM
   `JobCancelled` khi job bi huy (`job_runner.py:222`). Khong noi vao thi khach
   bam Huy va worker chay tiep den het — va do la mot nut KHONG lam gi, thu te
   hon mot nut khong ton tai.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path


def _than_ham(ten: str) -> str:
    from apps.prompt_ai_ommi import jobs
    return inspect.getsource(getattr(jobs, ten))


def test_handle_generate_TRUYEN_bao_lo_vao_breakdown():
    """Doc AST, KHONG grep chuoi: mot chu thich nhac ten `bao_lo` cung khop grep."""
    than = _than_ham("_handle_generate")
    cay = ast.parse(than.lstrip())
    ten_kw = {kw.arg for n in ast.walk(cay) if isinstance(n, ast.Call)
              for kw in n.keywords if kw.arg}
    assert "bao_lo" in ten_kw, (
        "khong loi goi nao trong `_handle_generate` truyen `bao_lo=` — nghia la "
        "chia lo chay nhung khach KHONG huy duoc va KHONG thay tien do")


def test_bao_lo_di_qua_progress_counter_chu_KHONG_progress():
    """`progress()` cung nem khi huy, nhung no KHONG mang bo dem.

    `progress_counter` ghi `da_xong/tong` that, va `job_events.append_progress_counter`
    NEM neu thieu — mot nhip tim chung minh TIEN TRINH con song, khong chung minh
    VIEC dang tien.
    """
    than = _than_ham("_handle_generate")
    assert "progress_counter" in than, (
        "phai dung `ctx.progress_counter`, khong phai `ctx.progress`: khach can "
        "thay 10/20 canh, khong phai mot con so phan tram tuy y")


def test_ctx_None_thi_van_chay_duoc():
    """Goi tay / test khac goi `_handle_generate` khong co `ctx`.

    ⛔ Khong duoc de `ctx is None` thanh `AttributeError` — bai nay ton tai vi
       mot ban truoc da lam dung the o mot cho khac (`NameError` tren MOI DELETE,
       45 bai xanh khong bat duoc vi tat ca chi doc chuoi nguon).
    """
    than = _than_ham("_handle_generate")
    assert "ctx is not None" in than or "if ctx" in than
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ**

Chạy: `python -m pytest tests/test_5572_jobs_bao_lo_va_tien_do.py -q`
Mong đợi: đỏ ở `test_handle_generate_TRUYEN_bao_lo_vao_breakdown` (chưa có `bao_lo=`).

- [ ] **Bước 3: nối vào `_handle_generate`**

Thay hai dòng `ctx.progress(30, ...)` + `provider.generate_json(...)` bằng:

```python
    def _bao_lo(da_xong: int, tong: int) -> None:
        """Nhip tien do o RANH LO — va la cua huy hop tac.

        ⭐ `progress_counter` tu nem `JobCancelled` khi job da bi huy, nen KHONG
           can viet co huy nao: goi dung cho la duoc ca hai viec.

        ⚠️ Goi o RANH LO, KHONG giua lo: mot lo da goi LLM la da tieu tien, cat
           giua lo lam khach tra ma khong nhan.
        """
        if ctx is None:
            return
        ctx.progress_counter(da_xong, tong, don_vi="canh",
                             event_code="ommi_chia_lo")

    model = str(params.get("model") or provider.model_mac_dinh())
    if ctx is not None:
        ctx.progress(30, "AI Director dang phan canh theo lo")
    raw, tokens = _sinh_theo_lo(params, system, prompt, model, _bao_lo)
```

⚠️ `_sinh_theo_lo` là chỗ nối giữa `jobs.py` và `breakdown.py`. Viết nó **cùng tệp**
`jobs.py`, và nó là nơi duy nhất biết cả hai phía:

```python
def _sinh_theo_lo(params: dict, system: str, prompt: str, model: str, bao_lo):
    """Goi `breakdown` theo lo, tra `(raw, tokens)` giong `generate_json` cu.

    ⭐ Giu DUNG hinh dang tra ve cua duong cu (`raw` dict + `tokens`) de
       `_normalize_result` va moi phep kiem hien co KHONG phai doi. Chia lo la mot
       thay doi ve CACH SINH, khong phai ve HOP DONG dau ra.
    """
    from apps.prompt_ai_ommi.services import breakdown as bd
    from apps.prompt_ai_ommi.services.library import khung_mac_dinh
    n = int(params.get("scene_count") or 6)
    canh = bd.breakdown(None, framework=khung_mac_dinh(params), story_vi=str(
        params.get("story") or ""), n_scenes=n, model=model, bao_lo=bao_lo)
    return {"scenes": canh}, 0
```

⛔ **Chưa biết `khung_mac_dinh` có tồn tại với tên đó không** — người thi hành phải
tra trước bằng `grep -rn "def .*khung\|framework" apps/prompt_ai_ommi/services/library.py`
và dùng đúng tên thật. ⛔ Đừng tạo một hàm mới nếu đã có một hàm trả framework mặc định:
hai chỗ khai cùng một mặc định là hai chỗ sẽ lệch.

⚠️ `tokens` trả `0` vì lời gọi thật nằm trong `breakdown`. Nếu `tokens_used` đang được
ai đọc để tính tiền hay để báo cho khách thì **phải cộng dồn qua từng lô** thay vì trả
`0` — tra bằng `grep -rn "tokens_used" apps/ server/ tests/` trước khi chốt. Một `0` ở
đây có thể là *"không có"* hoặc *"không đo được"*, và gộp hai trạng thái ấy vào một giá
trị là một lỗi đã có tên trong kho này.

- [ ] **Bước 4: chạy lại**

Chạy: `python -m pytest tests/test_5572_jobs_bao_lo_va_tien_do.py tests/test_159_prompt_ai_h26.py -q`

⚠️ `test_159` ghim `job_types` **đúng bằng** — nó phải xanh **mà không sửa**.

- [ ] **Bước 5: commit**

```bash
git commit --only apps/prompt_ai_ommi/jobs.py tests/test_5572_jobs_bao_lo_va_tien_do.py -m "feat(ommi): noi progress_counter vao bao_lo - tien do that + cua huy"
```

---

## 8. Task 4 — `max_runtime_s` khớp trần cảnh, và một phép kiểm chốt bất đẳng thức

**Files:**
- Modify: `apps/prompt_ai_ommi/manifest.py` — thêm `max_runtime_s` vào `AppManifest(...)`
- Modify: `apps/prompt_ai_ommi/services/chia_lo.py` — thêm `NGAN_SACH_MOI_LUOT_S`
- Test: `tests/test_5573_tran_thoi_gian_khop_tran_canh.py`

🔴 **Vì sao task này ⛔ không phải việc phụ.** `prompt_ai_ommi` hiện **không khai**
`max_runtime_s` nên nó ăn mặc định của nền tảng. Chia lô làm **số lượt gọi nhân lên**
(20 cảnh: 1 → 4 lượt), nên một trần vốn vừa đủ có thể thành không đủ. Và `prompt_canh`
đã ghi đúng hậu quả vào manifest của nó: *"chết ở trần nghĩa là khách đã trả mà không
nhận gì"*.

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
# tests/test_5573_tran_thoi_gian_khop_tran_canh.py
"""Tran thoi gian phai DU cho so luot goi o tran so canh.

⭐ Khuon lay tu `tests/test_1105` cua `prompt_canh` — bai da tra tien cho bai hoc
   nay. Hai con so (`max_runtime_s` va `TRAN` cua so canh) song o hai tep khac
   nhau, nen khong ai bat khop chung tru mot phep kiem.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.manifest import MANIFEST
from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo

JOB = "prompt_ai_ommi.generate"


def test_manifest_KHAI_tran_thoi_gian_cho_job_nay():
    assert JOB in (MANIFEST.max_runtime_s or {}), (
        "khong khai `max_runtime_s` thi job an mac dinh nen tang, va chia lo vua "
        "nhan so luot goi len — mot tran von vua du co the thanh khong du")


def test_tran_DU_cho_so_luot_goi_o_tran_so_canh():
    can = chia_lo.so_luot_goi(MAX_SCENES) * chia_lo.NGAN_SACH_MOI_LUOT_S
    co = MANIFEST.max_runtime_s[JOB]
    assert co >= can, (
        f"{MAX_SCENES} canh = {chia_lo.so_luot_goi(MAX_SCENES)} luot goi x "
        f"{chia_lo.NGAN_SACH_MOI_LUOT_S}s = {can}s can, ma tran chi {co}s. "
        f"Chet o tran nghia la khach DA TRA ma khong nhan gi.")


def test_manifest_KHONG_go_lai_so_ma_SUY_tu_chia_lo():
    """⛔ Mot so go tay se troi khoi `LO_CANH` ngay lan dau ai doi `LO_CANH`."""
    import inspect
    from apps.prompt_ai_ommi import manifest
    src = inspect.getsource(manifest)
    assert "chia_lo" in src, (
        "manifest phai NHAP tu `chia_lo` (so_luot_goi / NGAN_SACH_MOI_LUOT_S) chu "
        "khong go lai con so — cung ly le voi `prompt_canh` nhap `TRAN_SO_CANH`")
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ** — `python -m pytest tests/test_5573_tran_thoi_gian_khop_tran_canh.py -q`

- [ ] **Bước 3: thêm hằng số vào `chia_lo.py`**

```python
#: Ngan sach thoi gian cho MOT luot goi LLM, tinh bang giay.
#:
#: ⚠️ Con so nay la mot GIA THIET cho tới khi ai do do lai tren may B. Dat 60s
#:    theo `prompt_canh` (3600 / 76 = 47s) cong bien, vi lo cua ta LON hon lo cua
#:    no (5 canh day du so voi mot buoc chia). Ai do thuc te thi sua o DAY, va
#:    `max_runtime_s` tu di theo.
NGAN_SACH_MOI_LUOT_S = 60
```

- [ ] **Bước 4: khai `max_runtime_s` trong `manifest.py`**

```python
from apps.prompt_ai_ommi.services import chia_lo as _chia_lo

# ... trong AppManifest(...):
    # 🔴 SUY tu `chia_lo`, ⛔ KHONG go so: `20 canh = 4 luot x 60s = 240s`, va con
    #    so ay phai tu doi khi ai doi `LO_CANH`. `tests/test_5573` chot bat dang
    #    thuc de hai so khong troi khoi nhau.
    max_runtime_s={"prompt_ai_ommi.generate":
                   _chia_lo.so_luot_goi(MAX_SCENES) * _chia_lo.NGAN_SACH_MOI_LUOT_S},
```

⛔ **Kiểm vòng import trước khi chốt:** `chia_lo.gia_phan_da_giao` nhập `manifest._cost`
**bên trong hàm** (cố ý), nên `manifest` nhập `chia_lo` ở đầu tệp là an toàn. Chạy
`python -c "import apps.prompt_ai_ommi.manifest"` để chắc.

- [ ] **Bước 5: chạy lại + commit**

```bash
python -m pytest tests/test_5573_tran_thoi_gian_khop_tran_canh.py tests/test_5570_chia_lo_so_hoc.py -q
git commit --only apps/prompt_ai_ommi/manifest.py apps/prompt_ai_ommi/services/chia_lo.py tests/test_5573_tran_thoi_gian_khop_tran_canh.py -m "feat(ommi): max_runtime_s suy tu chia_lo + phep kiem chot bat dang thuc"
```

---

## 9. Task 5 — huỷ giữa đường: quyết toán theo phần đã giao

🔴 **Task nguy hiểm nhất cả pha. Đọc §0 trước khi viết một dòng.** Nó chạm đường
tiền, và nó chạm bằng cách **dựa vào một hành vi của nền tảng** chứ không bằng cách
sửa nền tảng — nên nếu hành vi đó đổi, tiền sai **im lặng**.

**Files:**
- Modify: `apps/prompt_ai_ommi/jobs.py` — bọc `_sinh_theo_lo` trong `try/except JobCancelled`
- Test: `tests/test_5574_huy_giua_duong_quyet_toan_dung.py`

**Chuỗi phải đúng, và đúng theo thứ tự này:**

```
1. khach POST /jobs/{id}/cancel     -> jobs.cancel()  -> status = JOB_CANCELLED
2. worker toi ranh lo ke tiep       -> ctx.progress_counter() -> NEM JobCancelled
3. `jobs.py` BAT, va lam DUNG hai viec:
     credit.quyet_toan(db, user_id, job_id, actual=gia_phan_da_giao(da_giao, params))
     db.commit()
   roi NEM LAI JobCancelled
4. runner bat (`job_runner.py:959`) -> _hoan_credit()
     -> credit.hoan() -> gap `_da_ket_so(job_id)` la True -> `return`, KHONG hoan
```

⚠️ **Chốt chịu lực là bước 4, và nó nằm ở `hoan()`, ⛔ KHÔNG ở `so_da_giu()`.**
`so_da_giu` chỉ cộng bút toán `CREDIT_HOLD` nên nó **vẫn > 0** sau khi quyết toán;
`_hoan_credit` vì thế **vẫn gọi** `hoan()`. Thứ chặn hoàn là `_da_ket_so`. Tôi đã đọc
sai chỗ này một lần. Nếu ai đổi `hoan()` bỏ cái guard ấy, khách sẽ **được hoàn cả khoản
vừa thu** — mất doanh thu, ⛔ không một dòng log nào.

⇒ Vì vậy `test_5574` có một phép kiểm **ghim chính cái guard đó**, và nó cố ý đọc mã
nền tảng chứ không chỉ đọc mã app.

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
# tests/test_5574_huy_giua_duong_quyet_toan_dung.py
"""Huy giua duong: khach tra DUNG phan da giao, KHONG duoc mien phi.

🔴 Neu ta vua hoan HET vua giu lai canh da sinh thi khach lay duoc viec mien phi,
   va lap duoc: nop 20 canh, huy sau lo 1, nhan 10 canh, lam lai. Do la mot duong
   lam dung THAT, khong phai mot ca hiem.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo


def test_jobs_BAT_JobCancelled_va_QUYET_TOAN_truoc_khi_nem_lai():
    """Doc AST: phai co `except` bat `JobCancelled`, trong do goi `quyet_toan`,
    va ket bang mot `raise` TRAN (nem lai)."""
    from apps.prompt_ai_ommi import jobs
    cay = ast.parse(inspect.getsource(jobs))
    thay = False
    for n in ast.walk(cay):
        if not isinstance(n, ast.ExceptHandler):
            continue
        ten = ast.unparse(n.type) if n.type is not None else ""
        if "JobCancelled" not in ten:
            continue
        than = ast.unparse(n)
        assert "quyet_toan" in than, (
            "bat `JobCancelled` ma KHONG quyet toan: nen tang se hoan TOAN BO va "
            "khach lay duoc phan da giao mien phi")
        assert any(isinstance(x, ast.Raise) and x.exc is None
                   for x in ast.walk(n)), (
            "phai `raise` TRAN de nem lai: khong nem lai thi job ket thuc BINH "
            "THUONG sau khi bi huy, va trang thai bao cho khach se sai")
        thay = True
    assert thay, "khong co `except JobCancelled` nao trong jobs.py"


def test_chan_hoan_tien_nam_o_credit_hoan_CHU_KHONG_o_so_da_giu():
    """⭐ GHIM dung co che ma Task 5 dua vao — o MA NEN TANG, khong o ma app.

    `so_da_giu` chi cong but toan HOLD nen no VAN > 0 sau quyet toan; thu chan
    hoan la `_da_ket_so` trong `credit.hoan`. Doi cai guard ay thi khach duoc hoan
    CA KHOAN VUA THU — mat doanh thu, khong mot dong log nao.
    """
    from platform_core import credit
    than = inspect.getsource(credit.hoan)
    assert "_da_ket_so" in than or "da_quyet_toan" in than, (
        "`credit.hoan` KHONG con chan theo 'da ket so'. Toan bo cach huy cua pha 6 "
        "dua vao dieu nay. Doc lai `apps/prompt_ai_ommi/jobs.py` truoc khi tin "
        "bat cu phep kiem nao khac trong tep nay.")


@pytest.mark.parametrize("da_giao,phai_thu_it_hon_day_du", [(0, True), (5, True),
                                                            (10, True), (15, True),
                                                            (MAX_SCENES, False)])
def test_gia_huy_luon_THAP_HON_gia_day_du_tru_khi_giao_du(da_giao,
                                                          phai_thu_it_hon_day_du):
    from apps.prompt_ai_ommi.manifest import _cost
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day_du = _cost(p)
    gia = chia_lo.gia_phan_da_giao(da_giao, p)
    if phai_thu_it_hon_day_du:
        assert gia < day_du, (
            f"giao {da_giao}/{MAX_SCENES} canh ma thu {gia} = gia day du {day_du}: "
            f"khach huy som KHONG duoc tra nhu chay het")
    else:
        assert gia == day_du


def test_DOI_CHUNG_khong_quyet_toan_thi_khach_duoc_mien_phi():
    """Tiem loi: bo loi goi `quyet_toan` khoi nhanh `except` => phep kiem dau PHAI do.

    ⭐ Khong co buoc nay thi `test_jobs_BAT_...` co the dang xanh vi mot ly do
       khong lien quan (vd `ast.unparse` doi dinh dang va chuoi `quyet_toan` khop
       o mot cho khac).
    """
    from apps.prompt_ai_ommi import jobs
    src = inspect.getsource(jobs)
    assert "quyet_toan" in src
    hong = src.replace("quyet_toan", "KHONG_QUYET_TOAN")
    cay = ast.parse(hong)
    for n in ast.walk(cay):
        if isinstance(n, ast.ExceptHandler) and n.type is not None \
                and "JobCancelled" in ast.unparse(n.type):
            assert "quyet_toan" not in ast.unparse(n).replace("KHONG_QUYET_TOAN", ""), \
                "tiem loi khong hieu qua — phep kiem dau khong do duoc dieu gi"
            return
    pytest.fail("khong tim thay nhanh except sau khi tiem loi")
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ** — `python -m pytest tests/test_5574_huy_giua_duong_quyet_toan_dung.py -q`

- [ ] **Bước 3: bọc `_sinh_theo_lo` trong `jobs.py`**

```python
    da_giao = {"n": 0}          # o nho so canh da giao, cho nhanh `except` doc

    def _bao_lo(da_xong: int, tong: int) -> None:
        da_giao["n"] = da_xong
        if ctx is None:
            return
        ctx.progress_counter(da_xong, tong, don_vi="canh",
                             event_code="ommi_chia_lo")

    from platform_core.job_runner import JobCancelled
    try:
        raw, tokens = _sinh_theo_lo(params, system, prompt, model, _bao_lo)
    except JobCancelled:
        # 🔴 QUYET TOAN theo phan DA GIAO roi NEM LAI. Xem plan pha 6 §9.
        #
        #    Nen tang mac dinh hoan TOAN BO khi job bi huy (`_hoan_credit`). Neu ta
        #    de the xay ra, khach lay duoc phan da giao MIEN PHI, va lap duoc.
        #
        # ⭐ `credit.hoan()` tu `return` khi `_da_ket_so(job_id)` la True, nen mot
        #    lan quyet toan o day lam lan hoan cua runner thanh VO TAC DUNG.
        #    ⚠️ Chot ay nam o `hoan()`, KHONG o `so_da_giu()` — `so_da_giu` chi cong
        #       but toan HOLD nen no VAN > 0 sau quyet toan.
        #    `tests/test_5574` ghim chinh cai guard do.
        from platform_core import credit
        from platform_core.db import get_session
        from apps.prompt_ai_ommi.services import chia_lo
        gia = chia_lo.gia_phan_da_giao(da_giao["n"], params)
        job_id = str(getattr(ctx, "job_id", "") or "")
        user_id = str(params.get("owner_id") or getattr(ctx, "user_id", "") or "")
        if job_id and user_id:
            for db in get_session():
                try:
                    credit.quyet_toan(db, user_id, job_id, actual=gia)
                    db.commit()
                finally:
                    db.close()
                break
        else:
            # ⛔ KHONG im lang: thieu `job_id`/`user_id` o day nghia la khach bi
            #    hoan toan bo cho mot luot da giao hang. Ghi ro de co nguoi doi soat.
            _log.warning("ommi huy: thieu job_id/user_id nen KHONG quyet toan duoc "
                         "(da giao %s canh) - khach se duoc hoan toan bo",
                         da_giao["n"])
        raise
```

⛔ **Người thi hành phải tra trước:** `ctx` có thuộc tính `job_id` và `user_id` không, và
`params` có `owner_id` không. Tra bằng `grep -n "self.job_id\|self.user_id" platform_core/job_runner.py`
và `grep -n "owner_id" apps/prompt_ai_ommi/routes/projects.py`. ⛔ Đừng giả định — nếu
`user_id` không có sẵn trên `ctx`, lấy từ `job` trong cùng session (`db.get(Job, job_id).user_id`).

- [ ] **Bước 4: chạy lại**

Chạy: `python -m pytest tests/test_5574_huy_giua_duong_quyet_toan_dung.py -q`

- [ ] **Bước 5: commit**

```bash
git commit --only apps/prompt_ai_ommi/jobs.py tests/test_5574_huy_giua_duong_quyet_toan_dung.py -m "feat(ommi): huy giua duong quyet toan theo phan da giao, khong hoan toan bo"
```

---

## 10. Task 6 — đóng pha: test nhắm cả cụm, rồi mở E5

- [ ] **Bước 1: test nhắm cả cụm**

```bash
python tools\thanh_phan.py --test app:prompt_ai_ommi
```

rồi chạy `python -m pytest <danh sách tệp> -q`. ⛔ Không bọc `chay_nang.py` (≥20 tệp
thì `conftest` tự xin `cpu_nhieu` và sẽ tự khoá chính mình).

Kỳ vọng: **≥ 553 xanh** (mốc đo 28/09 trước pha 6) cộng các bài mới, ⛔ không tệp nào đỏ.

- [ ] **Bước 2: kiểm bằng trình duyệt — pha này ĐỔI thứ khách thấy**

Chia lô làm tiến độ nhảy theo lô thay vì một bước 30 → 85. Phải xem thật:

1. `python tools\api_prod_canary.py trang-thai` để biết bản đang chạy.
2. Mở Studio, nộp một lượt **20 cảnh**, xem thanh tiến độ có đi `5/20 → 10/20 → 15/20 → 20/20`.
3. Bấm **Huỷ** khi đang ở `10/20`; kiểm: job về `cancelled`, và sổ credit thu **đúng
   `gia_phan_da_giao(10, params)`** chứ ⛔ không phải giá đầy đủ, cũng ⛔ không phải 0.
4. Kiểm console 0 lỗi và không request nào đỏ.

⛔ **Không tuyên bố pha 6 xong nếu chưa làm bước 3 trên giao diện thật.** Đó là bước
duy nhất đo được đường tiền từ đầu đến cuối, và đường tiền là thứ phép kiểm đơn vị
⛔ không thể tự chứng minh.

- [ ] **Bước 3: E5 — xoá `apps/prompt_canh`**

Chỉ sau khi bước 2 xanh. Q-16 chặn E5 cho tới khi pha 6 xong, và *"xong"* nghĩa là
**đã nghiệm thu trên giao diện**, ⛔ không phải *"đã viết mã"*.

```bash
grep -rn "prompt_canh" --include=*.py --include=*.html --include=*.md . | grep -v "^./docs/superpowers"
```

⚠️ Xoá một app là xoá một `route_prefix` khỏi sổ dùng chung. Đọc
`tools/thanh_phan.py` xem `prompt_canh` có trong bảng thành phần không, và đọc
`docs/03_THEM_APP_MOI.md` theo chiều ngược lại.

---

## 11. Self-review — đã chạy, và đây là những gì nó tìm ra

**Phủ spec:** Q-16 (chia lô + lịch sử) ⇒ Task 1, 2. Q-17 (giữ trần 20) ⇒ ⛔ không task
nào đổi `MAX_SCENES`; Global Constraints cấm. Q-18 (một job + huỷ ở ranh lô) ⇒ Task 3, 5.

**Ba lỗ hổng self-review tìm ra và plan đã sửa tại chỗ:**

1. **`max_runtime_s` chưa hề được khai** cho app này, mà chia lô nhân số lượt gọi lên 4
   lần ⇒ thêm Task 4. Không có nó thì pha 6 làm job **dễ chết ở trần hơn trước**.
2. **`tokens_used` sẽ thành `0`** khi lời gọi chuyển vào `breakdown` ⇒ Task 3 có một
   bước bắt tra `grep -rn "tokens_used"` trước khi chốt, vì `0` gộp hai trạng thái
   *"không có"* và *"không đo được"*.
3. **Cái guard mà toàn bộ cách huỷ dựa vào nằm ở mã NỀN TẢNG**, không ở mã app ⇒
   `test_5574` có một phép kiểm ghim chính `credit.hoan`'s `_da_ket_so`.

**Ba điều plan này CỐ Ý không làm, ghi ra để không ai tưởng là bỏ sót:**

- ⛔ Không giữ cảnh đã sinh sau khi huỷ (§3 — pha 6b, cần `brief_id` trong params).
- ⛔ Không đổi bảng giá (Q-17 đã chốt, đang sống trên production).
- ⛔ Không thêm job type (`test_159` ghim đúng bằng, và đó là cố ý).

**Một chỗ plan này ⛔ KHÔNG chắc, và nói ra thay vì đoán:** `NGAN_SACH_MOI_LUOT_S = 60`
là một **giả thiết**, suy từ `prompt_canh` (3600/76 ≈ 47 s) cộng biên vì lô của ta lớn
hơn. Chưa ai đo một lượt sinh 5 cảnh trên máy B. Task 4 đặt nó thành **một hằng số ở
một chỗ** để khi có số đo thật thì sửa một dòng và `max_runtime_s` tự đi theo.
