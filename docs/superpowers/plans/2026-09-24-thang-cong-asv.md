# Thang cổng từng bước cho Auto Scan Video — kế hoạch thi hành

> **Cho agent thi hành:** dùng `superpowers:subagent-driven-development` hoặc
> `superpowers:executing-plans`. Bước dùng cú pháp checkbox (`- [ ]`).

**Mục tiêu:** khoá logic vận hành của 12 mắt xích bằng hợp đồng **máy kiểm**, rồi siết
lần lượt hai mắt xích đầu của luồng chính (văn bản nguồn → dịch) cho tới khi **thật sự
đạt** theo ngưỡng đặt trước.

**Kiến trúc:** mỗi giai đoạn khai thêm bốn trường (`tien_quyet`, `ma_loi`, `do`, cộng
bao đóng `sau` đã có) ngay trong `pipeline.py` — một chỗ khai duy nhất. Bốn bất biến
I1–I4 được một phép kiểm quét AST cưỡng chế, nên không ai xen bước mới được mà không
khai đủ. Sau đó mỗi bước có một **bench chạy riêng lẻ** (không phải chạy cả chuỗi) đo
trên video thật của chủ dự án.

**Tech stack:** Python 3.13 · pytest · SQLAlchemy/PostgreSQL · `ai.goi_tinh_tien` →
`dieu_phoi` → máy B (`ltt-3.5` = Qwen3.5-9B GGUF Q6_K) · jiwer (WER/CER) ·
MetricX-24-Hybrid QE · RapidOCR · faster-whisper/whisperx · FLORES-200.

**Spec:** `docs/superpowers/specs/2026-09-24-thang-cong-asv-design.md`

## Global Constraints

- ⛔ **Không deploy, không `public=True`, không bật cờ `LTT_AUTO_SCAN_VIDEO`** (§24 đề bài).
- ⛔ **Không thêm model trên máy B.** Đúng hai model `ltt-3.8`/`ltt-3.5`.
- ⛔ **Không chuyển ASV sang `runtime_noi_bo`.** Đường tiền ASV (`ai.goi_tinh_tien` → `asv_usage`) giữ nguyên.
- ⛔ **Không chạy `gate.py` không tham số (L3).**
- 🔴 **L1 CHỈ chạy MỘT LẦN, ở CUỐI PHIÊN** (chủ dự án chốt 24/09). ⛔ Không L1 sau mỗi
  task, không L1 để "chốt bước". Giữa các task dùng **test NHẮM** cụm vừa sửa:
  `python tools\thanh_phan.py --test <tp>` → `python -m pytest <tệp> -q`.
  Hết mọi task ⇒ `python tools\gate.py --doi --tu $(git merge-base main HEAD)` **một lần**.
  ⚠️ `--doi` **phải** kèm `--tu`: cây sạch thì diff rỗng và gate **từ chối** (đúng vậy).
- 🔴 **Khoá theo KHẢ NĂNG ĐỐT CPU, không theo số tệp** (chủ dự án chốt 24/09). Khoá để
  tuần tự hoá việc **đốt lõi**; xếp hàng một lệnh 3 giây một lõi là phí máy của người khác.

  **KHÔNG cần khoá** — chạy thẳng:
  - pytest **nối tiếp** (⛔ không `-n`) trên 1–2 tệp, dự kiến **< 30 giây**
  - phép kiểm tĩnh / đọc AST / đọc tài liệu / `grep` / `git`
  - gọi **máy B** (chờ mạng, không đốt lõi máy A)

  **PHẢI qua khoá** — `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n` ≤ **7**:
  - pytest có `-n` (song song = nhiều lõi), **hoặc** ≥ 3 tệp test, **hoặc** dự kiến > 30 giây
  - **bất kỳ** ffmpeg · demucs · whisper/ASR · TTS · VMAF · suy luận model trên card máy A
  - build (cargo/npm/tauri) · `gate.py` mọi chế độ

  ⚠️ **Không biết nó đốt bao nhiêu ⇒ ĐO một lần**: chạy thẳng lúc máy rảnh, `tai_may` trước
  và sau. Quá 30 giây hoặc ngốn > 2 lõi ⇒ **từ lần sau nó thuộc nhóm phải qua khoá**, ghi
  con số đó vào báo cáo. ⛔ Đừng đoán rồi giữ nguyên phán đoán.
  ⛔ Và ngược lại cũng sai: một lệnh **thật sự nặng** chạy ngoài khoá vì "tôi nghĩ nó nhẹ" —
  hết cảnh gate + agent cộng dồn 14/20 lõi rồi bị CPU quá tải ngắt (đo 23/09).
- Trước lệnh **thuộc nhóm phải qua khoá**: `python tools\cua_so_yen.py trang-thai` (có người giữ → chờ) + `python tools\tai_may.py` (`QUÁ TẢI` → chờ).
- ⛔ **Nhả khoá ngay khi phép tính xong.** ⛔ Không giữ khoá trong lúc chờ máy B / chờ người / chờ dịch vụ.
- Gọi máy B: ⛔ **không** giữ `cpu_nhieu`. Trần đồng thời **≤ 2** request mỗi model.
- Ghi tệp **không BOM**; `.ps1` thuần ASCII; **giữ nguyên kết dòng** (LF/CRLF) từng tệp.
- ⛔ `ast.parse` **trước** `write_bytes`, không sau.
- Số test mới: tra `python tools\check_so_test.py`, ⛔ đừng đoán số.
- Mọi ngưỡng **viết ra trước khi đo**. Không đạt ⇒ sửa rồi đo lại, ⛔ **không nới ngưỡng**.
- Mỗi phép kiểm mới phải có **đối chứng** (tiêm lỗi, chứng minh nó ĐỎ). ⛔ Một phép kiểm chưa từng đỏ thì chưa biết nó bắt được gì.

---

## Khung 12 mắt xích — bảng cổng (toàn cục, để thấy tổng công việc)

| # | mắt xích | thứ tự | phép đo quyết định ĐẠT | ngưỡng (đặt trước) | trạng thái |
|---|---|---|---|---|---|
| 0 | kiểm kê video | B0 | F0 + LUFS vocals vs nền; % hardsub; số cảnh | — (kiểm kê, không có ngưỡng) | ✅ **XONG** 24/09 |
| — | **hợp đồng 12 bước** | **B-HĐ** | I1–I4 máy kiểm + đối chứng tiêm | 4/4 bất biến đỏ khi tiêm | **Task 1–3** |
| 3 | `transcribe` (nghe chép) | **B1** | WER/CER vs hardsub, ≥ 3 phim | WER ≤ 0,25 · CER ≤ 0,12 | **Task 4–8** |
| 5 | `content_process` (dịch) | **B2** | MetricX QE trên FLORES + tỉ lệ báo động giả của bộ chấm | báo động giả ≤ 15% · QE ≥ mốc 3.8 − 0,3 | **Task 9–13** |
| 2 | `audio_prepare` | B3 | F0 khác 0 trên phim có tiếng; demucs trên card | 3/3 phim có tiếng | chưa viết chi tiết |
| 6 | `voice_synthesis` | B4 | WER lượt cuối + PESQ | WER p50 ≤ 0,12 · PESQ ≥ 2,0 | chưa viết chi tiết |
| 1 | `media_prepare` | B5 | tệp ra giải mã được, thời lượng khớp | 4/4 phim | chưa viết chi tiết |
| 4 | `edit_plan` | B6 | số cảnh khớp đo trực tiếp (N-07) | lệch ≤ 10% | chưa viết chi tiết |
| 7 | `timing_align` | B7 | tỉ lệ câu vừa khe; trôi dồn cuối | ≥ 90% vừa khe | chưa viết chi tiết |
| 8 | `compose` | B8 | LUFS · đỉnh dBTP | −14 ± 1 LUFS · ≤ −1,0 dBTP | chưa viết chi tiết |
| 9 | `render` | B9 | VMAF (nhánh nvenc — **chưa đo bao giờ**) | VMAF ≥ 75 | chưa viết chi tiết |
| 10 | `qc` | B10 | T1–T18 | 0 mục hỏng | chưa viết chi tiết |
| 11 | `qc_do_luong` | B11 | WER/CER giọng, PESQ, SI-SDR | như B4 | chưa viết chi tiết |
| 12 | `qc_ai` | B12 | tỉ lệ báo động giả (đo ở B2) | ≤ 15% | phụ thuộc B2 |

⚠️ Chi tiết thi hành của B3–B12 **viết khi tới**, vì kết quả B1/B2 sẽ đổi cách làm chúng.

---

## Task 0: Bỏ khoá `postgres_test` — mỗi làn một CSDL scratch riêng (N-10)

**Vì sao làm TRƯỚC mọi thứ:** khoá này vừa chặn một làn phiên khác **78 phút**, và nó
tồn tại **không** vì tài nguyên độc quyền thật — mà vì **mọi làn dùng chung MỘT tên CSDL**.
Cho mỗi làn một tên riêng thì hết xung đột và **không cần khoá nào**. ⭐ Nó đóng luôn
**M-11** (một `AsvRun` mồ côi của làn khác tự nộp job vô hạn, `jobs` phình 1.274 dòng):
mỗi làn không còn thấy rác của làn khác.

⚠️ Đây **khác** `cpu_nhieu`: khoá CPU chia **sức tính** nên không bỏ được. `postgres_test`
chỉ chia một **cái tên**.

**Files:**
- Modify: `tests/fixtures/pg_scratch.py` (hàm `scratch_url`)
- Modify: `tests/conftest.py:109` (bỏ `"postgres_test"` khỏi `tai_nguyen=`)
- Test: `tests/test_<N0>_pg_scratch_theo_lan.py` (lấy `<N0>` từ `check_so_test.py`)

**Interfaces:**
- Produces: `pg_scratch.scratch_url(lan: str = "") -> str` — tên CSDL chứa cả `lan`;
  rỗng ⇒ suy từ tên worktree.

- [ ] **Bước 1: Viết phép kiểm ĐỎ trước**

```python
def test_hai_lan_khac_nhau_cho_hai_CSDL_khac_nhau():
    """Khoa `postgres_test` chi bao ve MOT CAI TEN, khong bao ve tai nguyen doc quyen.

    Do 24/09: mot lan giu khoa 78 phut, mot lan phien khac xep hang sau no — cho
    mot thu le ra khong chan ai.
    """
    from tests.fixtures import pg_scratch
    a = pg_scratch.scratch_url("asvf-b1")
    b = pg_scratch.scratch_url("asvf-dich")
    assert a != b
    assert "test" in a and "test" in b   # `scratch_url` doi ten chua "test"


def test_ten_CSDL_hop_le_voi_postgres():
    """Ten PostgreSQL: <= 63 ky tu, chu thuong, khong dau gach ngang."""
    from tests.fixtures import pg_scratch
    ten = pg_scratch.scratch_url("asvf-nghiem-thu-v2").rsplit("/", 1)[-1]
    assert len(ten) <= 63 and ten == ten.lower() and "-" not in ten
```

- [ ] **Bước 2: Chạy để chắc nó ĐỎ**

Run: `python -m pytest tests/test_<N0>_pg_scratch_theo_lan.py -q`
Expected: FAIL — `scratch_url() takes 0 positional arguments`

- [ ] **Bước 3: Sửa `scratch_url` nhận `lan`**

```python
def _chuan_ten(lan: str) -> str:
    """`asvf-nghiem-thu-v2` -> `asvf_nghiem_thu_v2`, cat cho vua 63 ky tu."""
    tho = re.sub(r"[^a-z0-9_]", "_", lan.lower())
    return tho[:40].strip("_")


def scratch_url(lan: str = "") -> str:
    lan = lan or _lan_tu_worktree()
    return f"{_goc_url()}/lttplatform_test_{_chuan_ten(lan)}"
```

- [ ] **Bước 4: Chạy lại — XANH**

Run: `python -m pytest tests/test_<N0>_pg_scratch_theo_lan.py -q`
Expected: PASS

- [ ] **Bước 5: Bỏ `postgres_test` khỏi `tests/conftest.py:109`**, ⛔ giữ `cpu_nhieu`.

- [ ] **Bước 6: ĐỐI CHỨNG cô lập — bước KHÔNG ĐƯỢC BỎ**

Mở **hai** tiến trình cùng dùng CSDL scratch với hai `lan` khác nhau; một bên gọi
`drop_all`, bên kia đang ghi. Bên kia **phải không bị ảnh hưởng**.
⛔ Không có bước này thì ta chỉ chứng minh **tên khác nhau**, chưa chứng minh **cô lập** —
mà cô lập mới là thứ khoá đang bảo vệ.

- [ ] **Bước 7: Dọn M-11**

Sau khi mỗi làn có CSDL riêng, xoá `lttplatform_test` cũ (1.274 dòng rác + một `AsvRun`
mồ côi). ⚠️ Kiểm **không phiên nào đang dùng nó** trước khi xoá (`pg_stat_activity`).

- [ ] **Bước 8: Commit**

```bash
git add tests/fixtures/pg_scratch.py tests/conftest.py tests/test_<N0>_pg_scratch_theo_lan.py
git commit -m "feat(test/pg): moi lan mot CSDL scratch rieng - bo khoa postgres_test, dong M-11"
```

---

## Task 1: Bốn trường hợp đồng trên `GiaiDoan`

**Files:**
- Modify: `apps/auto_scan_video/pipeline.py:68-96` (dataclass), `:98-210` (12 dòng khai)
- Test: `tests/test_<N>_asv_hop_dong_mat_xich.py` (lấy `<N>` từ `check_so_test.py`)

**Interfaces:**
- Produces: `GiaiDoan.tien_quyet: tuple[str, ...]`, `GiaiDoan.ma_loi: tuple[str, ...]`,
  `GiaiDoan.do: tuple[str, ...]`; hàm `pipeline.thieu_khai() -> list[str]` trả danh sách
  `"<ten giai doan>: thieu <truong>"`, rỗng nghĩa là đủ.

- [ ] **Bước 1: viết phép kiểm ĐỎ trước**

```python
def test_moi_giai_doan_khai_du_bon_truong():
    """I2+I4: `tien_quyet` và `do` KHÔNG được rỗng.

    🔴 Vì sao: lượt A 24/09 chết ở `content_process` với `auto_match_thieu_can_cu`,
       và nguyên nhân là một TIỀN ĐỀ CHƯA AI KHAI — tự khớp giọng đòi nguồn có
       tiếng nói. Một tiền đề không khai thì không ai kiểm được, nên nó hiện ra
       như một khiếm khuyết trong khi nó là một điều kiện.
    ⭐ Khai `("",)` là cách khai tường minh "bước này không có tiền đề" — khác
       hẳn `()` là "chưa ai nghĩ tới".
    """
    from apps.auto_scan_video import pipeline
    assert pipeline.thieu_khai() == []
```

- [ ] **Bước 2: chạy để chắc nó ĐỎ**

Run: `python -m pytest tests/test_<N>_asv_hop_dong_mat_xich.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'thieu_khai'`

- [ ] **Bước 3: thêm ba trường + hàm kiểm**

```python
# apps/auto_scan_video/pipeline.py — thêm vào dataclass GiaiDoan
    #: Điều kiện phải đúng để bước này CÓ NGHĨA. ⛔ Không được rỗng.
    #:
    #: 🔴 `("",)` = khai tường minh "không có tiền đề". `()` = CHƯA AI NGHĨ TỚI,
    #:    và `thieu_khai()` đỏ. Khác biệt này là cả mục đích của trường: lượt A
    #:    24/09 chết vì `content_process` đòi nguồn có tiếng nói mà không ai viết.
    tien_quyet: tuple[str, ...] = ()
    #: Mã lỗi ổn định bước này được phép ném. ⛔ Không ném chuỗi tự do — G-04:
    #: câu giải thích dừng ở cột `error`, khách nhận câu chung chung + nút hỏng.
    ma_loi: tuple[str, ...] = ()
    #: Tên phép đo quyết định ĐẠT. ⛔ Rỗng = bước không thể "đạt" ⇒ không vào thang cổng.
    do: tuple[str, ...] = ()


def thieu_khai() -> list[str]:
    """Giai đoạn nào thiếu trường bắt buộc. Rỗng = đủ."""
    ra: list[str] = []
    for g in CHUOI:
        for ten_truong in ("tien_quyet", "ma_loi", "do"):
            if not getattr(g, ten_truong):
                ra.append(f"{g.ten}: thieu {ten_truong}")
    return ra
```

- [ ] **Bước 4: khai đủ cho 12 giai đoạn**

Đọc **từng** module giai đoạn rồi khai theo thứ **có thật trong mã**. ⛔ Đừng bịa.
Ví dụ hai dòng (phần còn lại làm y hệt, đọc mã trước khi khai):

```python
    GiaiDoan(TRANSCRIBE, "asv_gpu", "asv_gpu.transcribe", sau=(AUDIO_PREPARE,),
             tien_quyet=("ban tieng cua CUNG lan chay da co",
                         "nguon loi: tieng noi (asr) — hardsub chi de doi chieu"),
             ma_loi=("chua_co_ban_tieng", "asr_that_bai", "nguon_loi_khong_kha_dung"),
             do=("wer_vs_hardsub", "cer_vs_hardsub")),
    GiaiDoan(CONTENT_PROCESS, "auto_scan_video",
             "auto_scan_video.content_process", sau=(EDIT_PLAN,),
             tien_quyet=("ban ghi loi thoai nguon da co",
                         "cap ngon ngu hop le (nguon {zh,en,vi} -> dich {vi,en})"),
             ma_loi=("auto_match_thieu_can_cu", "dich_that_bai", "vuot_ngan_sach"),
             do=("metricx_qe", "ti_le_bao_dong_gia_bo_cham")),
```

- [ ] **Bước 5: chạy lại — phải XANH**

Run: `python -m pytest tests/test_<N>_asv_hop_dong_mat_xich.py -q`
Expected: PASS

- [ ] **Bước 6: ĐỐI CHỨNG — tiêm, chứng minh nó đỏ**

```bash
python -c "
import pathlib, re
p = pathlib.Path('apps/auto_scan_video/pipeline.py')
s = p.read_bytes().decode('utf-8')
s2 = s.replace('do=(\"wer_vs_hardsub\", \"cer_vs_hardsub\")', 'do=()', 1)
assert s2 != s
p.write_bytes(s2.encode('utf-8'))
"
python -m pytest tests/test_<N>_asv_hop_dong_mat_xich.py -q
```
Expected: **FAIL** với `transcribe: thieu do`. Rồi `git checkout -- apps/auto_scan_video/pipeline.py` và chạy lại: PASS.

- [ ] **Bước 7: commit**

```bash
git add apps/auto_scan_video/pipeline.py tests/test_<N>_asv_hop_dong_mat_xich.py
git commit -m "feat(asv/hop-dong): bon truong khai cho moi mat xich, may kiem I2+I4"
```

---

## Task 2: Sổ mã lỗi chung (I3)

**Files:**
- Create: `apps/auto_scan_video/ma_loi.py`
- Modify: `apps/auto_scan_video/pipeline.py` (import + kiểm)
- Test: cùng tệp Task 1

**Interfaces:**
- Consumes: `pipeline.CHUOI`, `GiaiDoan.ma_loi` (Task 1)
- Produces: `ma_loi.SO_MA: dict[str, str]` (mã → câu khách đọc được);
  `ma_loi.HOAN_CREDIT: frozenset[str]` (mã nào hoàn credit);
  `pipeline.ma_loi_la(ma: str) -> bool`

- [ ] **Bước 1: phép kiểm ĐỎ trước**

```python
def test_moi_ma_loi_khai_o_giai_doan_deu_co_trong_SO_MA():
    """I3: ⛔ không ném chuỗi tự do.

    🔴 G-04 (đo 24/09): câu `vi_sao_chua_rang` dừng ở cột `error`, màn khách đọc
       `outputs.ma_loi` ⇒ khách nhận một câu chung chung KÈM một nút "Thử lại
       bước này" CHẮC CHẮN HỎNG. Một mã lỗi không có câu tương ứng là một cửa
       lỗi nói dối.
    """
    from apps.auto_scan_video import ma_loi, pipeline
    thieu = [(g.ten, m) for g in pipeline.CHUOI for m in g.ma_loi
             if m not in ma_loi.SO_MA]
    assert thieu == [], f"ma khong co cau khach doc duoc: {thieu}"


def test_moi_ma_trong_SO_MA_deu_khai_chinh_sach_credit():
    """Mã lỗi mà không nói credit có hoàn hay không là một lỗ ở sổ tiền."""
    from apps.auto_scan_video import ma_loi
    assert set(ma_loi.HOAN_CREDIT) <= set(ma_loi.SO_MA)
    assert ma_loi.HOAN_CREDIT, "chua ma nao khai hoan credit — kho tin"
```

- [ ] **Bước 2: chạy — ĐỎ** (`ModuleNotFoundError: apps.auto_scan_video.ma_loi`)

- [ ] **Bước 3: dựng sổ mã, lấy mã THẬT từ mã nguồn**

```bash
grep -rn "ma_loi\|error=" apps/auto_scan_video/*.py | grep -oE '"[a-z0-9_]{6,}"' | sort -u
```
Rồi viết `ma_loi.py` với **mọi** mã tìm được, mỗi mã một câu khách đọc được (bọc `_()`),
và `HOAN_CREDIT` cho những mã mà khách **không có lỗi gì**.

⚠️ Kiểm đối chiếu: mã đã dùng ở `quan_sat.LOI_CO_MA` phải khớp — ⛔ đừng tạo bộ thứ hai.

- [ ] **Bước 4: chạy lại — XANH**
- [ ] **Bước 5: ĐỐI CHỨNG** — thêm một mã bịa vào `ma_loi` của một giai đoạn ⇒ phải ĐỎ; hoàn nguyên.
- [ ] **Bước 6: commit** `feat(asv/hop-dong): so ma loi chung, moi ma co cau khach doc duoc`

---

## Task 3: I1 — bao đóng `sau` phủ mọi lần đọc thật (mở rộng `test_3004`)

**Files:**
- Modify: `tests/test_3004_*.py` (đã có, làm một nửa)
- Test: cùng tệp

**Interfaces:**
- Consumes: `pipeline.CHUOI`, hàm `vi_pham(do_thi)` đã tách ở `test_3004`
- Produces: không có giao diện mới — chỉ mở rộng phạm vi phép kiểm

- [ ] **Bước 1: đọc `test_3004` hiện có**, xác nhận nó đã tách phần phán xử thành hàm **thuần nhận đồ thị làm dữ liệu** (`vi_pham`). ⚠️ Nếu chưa, tách trước — nếu không thì không tiêm được, vì `pipeline._kiem_tra_chuoi()` chặn ở lúc **nạp module** và phép tiêm chết trước khi tới phần phán xử (bài học N-08b: *một đối chứng thất bại vì lý do KHÁC thì không phải một đối chứng*).

- [ ] **Bước 2: thêm phép kiểm cho đường CHẠY LẠI**

```python
def test_chay_lai_mot_buoc_giua_chuoi_vo_hieu_dung_cac_buoc_phu_thuoc():
    """⛔ N-08 chưa đo trên đường chạy lại — và đường đó ĐÃ cắn một lần.

    🔴 `features.py:263` ghi một sự cố THẬT: chạy lại `media_prepare` → job
       `audio_prepare` CŨ của lượt trước vẫn chạy → `transcribe` đọc bản tiếng
       thuộc lượt chạy TRƯỚC. Và nó ghi thêm: "một lỗi chỉ hỏng đôi khi thì
       trước đó nó vẫn hỏng, chỉ là chưa ai thấy".
    """
    from apps.auto_scan_video import pipeline
    for g in pipeline.CHUOI:
        ha_nguon = set(pipeline.ha_nguon_cua(g.ten))
        doc_that = set(pipeline.ai_doc(g.ten))   # từ AST
        assert doc_that <= ha_nguon | {g.ten}, (
            f"{g.ten}: bước đọc nó mà KHÔNG bị vô hiệu khi nó chạy lại: "
            f"{sorted(doc_that - ha_nguon - {g.ten})}")
```

- [ ] **Bước 3: chạy — ghi lại kết quả THẬT.** ⚠️ Có thể XANH (bao đóng đang phủ) hoặc ĐỎ. Cả hai đều là kết quả hợp lệ; ⛔ **đừng sửa phép kiểm cho nó xanh**. Đỏ ⇒ đó là N-08 cắn thật, báo điều phối trước khi sửa mã.
- [ ] **Bước 4: ĐỐI CHỨNG trên đồ thị TỔNG HỢP** (không trên `pipeline.py` thật): dựng đúng cảnh *xen một bước mới vào giữa* với một nhánh rẽ ngoài bao đóng ⇒ phải ĐỎ kèm **số dòng**.
- [ ] **Bước 5: commit** `test(asv/hop-dong): I1 phu ca duong chay lai, doi chung tren do thi tong hop`

---

## Task 4: Khuôn chạy MỘT giai đoạn riêng lẻ

**Files:**
- Create: `tests/fixtures/asv_mot_buoc.py`
- Test: `tests/test_<N+1>_asv_khuon_mot_buoc.py`

**Interfaces:**
- Produces:
  ```python
  def chay_mot_buoc(db, kho, *, ten_giai_doan: str, duong_video: str,
                    cai_dat: dict, gieo: dict[str, str] | None = None,
                    xin_card: bool = True) -> dict:
      """Chạy ĐÚNG MỘT giai đoạn. `gieo` = {ten_giai_doan_truoc: khoa_asset}.
      Trả `asv_stage.outputs` của giai đoạn đó + `khai_card` + `khai_python`."""
  ```

- [ ] **Bước 1: phép kiểm ĐỎ trước**

```python
def test_chay_mot_buoc_KHONG_chay_cac_buoc_truoc(db, kho, tmp_path):
    """Cả mục đích của khuôn: đo một bước 20 giây không phải trả 3 phút.

    ⚠️ Gieo theo TẬP ĐỌC THẬT, không theo cột `sau` — bản khai trực tiếp hẹp hơn
       thực tế, và gieo theo `sau` cho một lỗi "thiếu đầu vào" NGHE NHƯ khiếm
       khuyết sản phẩm.
    """
    from tests.fixtures import asv_mot_buoc
    goi = []
    # ... monkeypatch từng `chay` của 12 module để ghi tên khi bị gọi ...
    asv_mot_buoc.chay_mot_buoc(db, kho, ten_giai_doan="transcribe",
                               duong_video=str(tmp_path / "v.mp4"),
                               cai_dat={"nguon_loi": "asr"},
                               gieo={"audio_prepare": "asset:tieng"})
    assert goi == ["transcribe"], f"da chay ca cac buoc khac: {goi}"
```

- [ ] **Bước 2: chạy — ĐỎ** (`ModuleNotFoundError`)
- [ ] **Bước 3: viết khuôn.** Dùng lại **nguyên** hai thứ đã có: `card_cho_job` (xin lease thật) và `ghim_python_co_card` (ghim venv worker). ⛔ Đừng viết đường xin card thứ hai.
- [ ] **Bước 4: chạy — XANH**
- [ ] **Bước 5: ĐỐI CHỨNG** — gọi với `gieo=None` cho một bước không phải bước đầu ⇒ phải **nổ với câu nói rõ thiếu gì**, ⛔ không phải `KeyError` trống.
- [ ] **Bước 6: commit** `feat(test/asv): khuon chay MOT giai doan rieng le, xin card that`

---

## Task 5: Ép `che_do=asr` — luồng chính chạy thật lần đầu

**Files:**
- Modify: `apps/auto_scan_video/nguon_loi.py:43` (`CHE_DO_MAC_DINH`)
- Modify: `apps/auto_scan_video/cai_dat.py:135-136` (chú thích)
- Test: `tests/test_<N+2>_asv_nguon_loi_mac_dinh_asr.py`

**Interfaces:**
- Produces: `nguon_loi.CHE_DO_MAC_DINH == nguon_loi.ASR`

- [ ] **Bước 1: phép kiểm ĐỎ trước**

```python
def test_mac_dinh_la_ASR_vi_san_pham_la_long_tieng_voice_to_voice():
    """🔴 Chủ dự án chốt 24/09: sản phẩm là lồng tiếng voice→voice.

    Đo B0: cả 4 phim mẫu có hardsub Hán 98,8–100% ⇒ với `auto` thì CẢ BỐN đi
    đường `ocr`, và đường `asr` — luồng CHÍNH — chưa từng chạy thật một lần nào.
    """
    from apps.auto_scan_video import nguon_loi
    assert nguon_loi.CHE_DO_MAC_DINH == nguon_loi.ASR


def test_auto_van_con_la_mot_lua_chon_hop_le():
    """Đổi mặc định, ⛔ KHÔNG xoá `auto` — khách vẫn chọn được."""
    from apps.auto_scan_video import nguon_loi
    assert nguon_loi.chuan_che_do("auto") == nguon_loi.AUTO
```

- [ ] **Bước 2: chạy — ĐỎ** (`assert 'auto' == 'asr'`)
- [ ] **Bước 3: đổi mặc định**, và **ghi lý do vào chú thích** (đo B0 + quyết định 24/09).
- [ ] **Bước 4: chạy lại toàn bộ test chạm `nguon_loi`**

Run: `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- python -m pytest tests/ -q -k "nguon_loi or dinh_tuyen or 2040 or 2041 or 2042" -n 7`
⚠️ Đổi một mặc định thì mọi phép kiểm ngầm dựa vào `auto` sẽ đỏ. Đó là **kết quả đúng** — sửa từng phép kiểm cho khai tường minh chế độ nó muốn, ⛔ đừng hoàn nguyên mặc định.

- [ ] **Bước 5: commit** `feat(asv/nguon-loi): mac dinh ASR — san pham la long tieng voice->voice`

---

## Task 6: Bench B1 — WER/CER nghe chép vs hardsub

**Files:**
- Create: `tools/bench_b1_chep_loi.py`
- Create: `docs/auto_scan_video_final/B1_CHEP_LOI.md`
- Test: `tests/test_<N+3>_asv_bench_b1.py`

**Interfaces:**
- Consumes: `tests/fixtures/asv_mot_buoc.chay_mot_buoc` (Task 4)
- Produces: `bench_b1_chep_loi.do_mot_phim(duong: str) -> dict` trả
  `{"wer", "cer", "so_dong_nguon", "so_dong_hardsub", "engine", "co_card", "gioi_han"}`

- [ ] **Bước 1: ngưỡng ĐẠT — viết TRƯỚC khi đo**

Ghi vào `B1_CHEP_LOI.md` trước khi chạy dòng nào:
```
ĐẠT khi: WER ≤ 0,25 VÀ CER ≤ 0,12, trên ≥ 3 phim có tiếng nói (món ăn, cắm trại, PUBG).
Vì sao mức đó: CER đo được trước đây là 0,018 trên 1 clip 33 dòng ở một đường KHÁC
(faster-whisper CPU, văn bản đối chiếu tay). Hardsub có thể RÚT GỌN so với lời nói,
nên ngưỡng phải lỏng hơn số cũ — nhưng 0,25/0,12 vẫn là ngưỡng, không phải mô tả.
⛔ Không đạt ⇒ sửa rồi đo lại. KHÔNG nới ngưỡng.
```

- [ ] **Bước 2: phép kiểm ĐỎ trước cho bộ đo**

```python
def test_do_mot_phim_khai_GIOI_HAN_cua_chan_ly_nen():
    """⛔ Hardsub là đối chiếu TỐT, không hoàn hảo — nó có thể rút gọn lời nói.

    Một con số WER không kèm giới hạn đó sẽ bị đọc như WER thật.
    """
    from tools import bench_b1_chep_loi as b
    kq = b.do_mot_phim.__doc__ or ""
    assert "rut gon" in kq.lower() or "rút gọn" in kq
```

- [ ] **Bước 3: viết bộ đo.** Dùng `jiwer` (đã có trong kho). Chuẩn hoá trước khi so: bỏ dấu câu, thống nhất giản/phồn thể bằng OpenCC nếu có, ⛔ **đừng** bỏ khoảng trắng tiếng Trung theo cách tự chế — ghi rõ cách chuẩn hoá vào báo cáo.
- [ ] **Bước 4: chạy trên 3 phim**, mỗi phim một lượt qua `chay_nang.py`, ⛔ nhả khoá giữa các phim.
- [ ] **Bước 5: ĐỐI CHỨNG** — tiêm một bản chép **đã làm hỏng** (đảo 30% từ) ⇒ WER phải vọt lên rõ. ⛔ Không có bước này thì một WER thấp có thể chỉ là bộ đo hỏng.
- [ ] **Bước 6: ghi kết quả + phán quyết ĐẠT/KHÔNG vào `B1_CHEP_LOI.md`**, kèm: engine nào chạy (`whisperx` hay `faster-whisper`), **card có được cấp không**, và cách chuẩn hoá.
- [ ] **Bước 7: commit**

---

## Task 7: So hai nhánh engine (`whisperx` ↔ `faster-whisper`)

**Files:** Modify `tools/bench_b1_chep_loi.py`; ghi vào `B1_CHEP_LOI.md`

**Interfaces:** Consumes `do_mot_phim` (Task 6); Produces `do_mot_phim(..., engine: str)`

- [ ] **Bước 1:** ⚠️ Hai nhánh có **tham số khác nhau** và **không ai từng so**: `faster-whisper` khai `beam_size=5`, `vad_filter=True`; `whisperx_runner` **không khai** beam lẫn VAD, thêm alignment wav2vec2. Ghi sự khác biệt đó vào báo cáo **trước** khi đo — nó là một biến, không phải một chi tiết.
- [ ] **Bước 2:** đo **cùng** 3 phim bằng **cả hai** nhánh, cùng chuẩn hoá.
- [ ] **Bước 3:** ghi bảng: engine · WER · CER · giây · card. ⛔ Nếu chênh ≤ 0,02 thì kết luận là *"không phân biệt được ở n=3"*, ⛔ **đừng** tuyên bố nhánh nào thắng.
- [ ] **Bước 4: commit**

---

## Task 8: Cổng B1 — phán quyết

- [ ] **Bước 1:** đọc `B1_CHEP_LOI.md`. ĐẠT theo ngưỡng Task 6 ⇒ sang B2. KHÔNG ĐẠT ⇒ **dừng**, báo điều phối kèm số, ⛔ không tự sang bước sau.
- [ ] **Bước 2:** cập nhật `THANG_CONG_TUNG_BUOC.md` (trạng thái B1) và `LOI_TONG.md` (lỗi mới nếu có).
- [ ] **Bước 3:** test **NHẮM** cụm vừa sửa. ⛔ **Không** L1 ở đây — L1 chỉ ở cuối phiên.
- [ ] **Bước 4:** gộp `main` khi test nhắm xanh; commit.

---

## Task 9: Chốt nhiệt độ + seed — điều kiện TIÊN QUYẾT của B2

**Files:**
- Modify: `apps/auto_scan_video/giai_doan_noi_dung.py:216-222`, `apps/auto_scan_video/ai.py:526-529,667-669`
- Test: `tests/test_<N+4>_asv_dich_tai_lap.py`

**Interfaces:**
- Produces: `ai.goi(..., seed: int | None = None)`; `long_tieng.NHIET_DO_DICH: float`

- [ ] **Bước 1: phép kiểm ĐỎ trước**

```python
def test_duong_dich_TRUYEN_nhiet_do_tuong_minh():
    """🔴 Đường sống KHÔNG truyền temperature (đo 24/09) ⇒ lấy mặc định máy chủ,
       không ai chốt. Đường CHẾT `dich_thuat.py:201` thì ghim 0.2.

    ⛔ Không tái lập được thì KHÔNG ĐO ĐƯỢC cải thiện của bất kỳ phương án nào.
       Đây là điều kiện tiên quyết của cả B2, không phải việc làm sau.
    """
    import ast, pathlib
    van = pathlib.Path("apps/auto_scan_video/giai_doan_noi_dung.py").read_text(encoding="utf-8")
    cay = ast.parse(van)
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
           and getattr(n.func, "attr", "") == "goi_tinh_tien"]
    assert goi, "khong tim thay loi goi goi_tinh_tien"
    for g in goi:
        ten = {k.arg for k in g.keywords}
        assert "temperature" in ten, f"dong {g.lineno}: khong truyen temperature"
```

- [ ] **Bước 2: chạy — ĐỎ**
- [ ] **Bước 3: thêm hằng + truyền tường minh**

```python
# apps/auto_scan_video/long_tieng.py
#: Nhiệt độ cho lượt viết lời dịch. 🔴 Ghim vì không ghim thì cổng lấy mặc định
#: máy chủ, và hai lượt cùng đầu vào cho hai bản dịch khác nhau ⇒ không đo được
#: cải thiện. 0.2 lấy theo `dich_thuat.py:201` — cùng kho, cùng việc, đã chọn một lần.
NHIET_DO_DICH = 0.2
```

- [ ] **Bước 4: ⛔ KHÔNG thêm `seed`. Đã ĐO, nó vô hiệu.**

🔴 **Đo 24/09 trên cổng thật, n=5 mỗi cấu hình:**
```
seed=20260924          -> 4/5 ket qua KHAC nhau
khong seed             -> 5/5 khac nhau
temperature=0.0        -> 5/5 VAN khac nhau
```
Cổng **nhận** `seed` nhưng **không có hiệu lực** (`-np 3` + draft-mtp). ⇒ Bản dịch
**không tái lập được bằng bất cứ núm nào**. ⛔ Đừng thêm một tham số chết — nó sẽ
thành lời khai rằng ta có tái lập trong khi không có.

⇒ **Đổi ĐƠN VỊ ĐO thay vì đổi mã:** mọi con số chất lượng dịch từ giờ là **trung vị
của N ≥ 3 lượt**, và báo cáo **phải kèm dải**. Một lượt đơn lẻ ⛔ không được dùng làm
phán quyết. Ghi rõ điều này vào `B2_DICH.md`.

- [ ] **Bước 4b: Nhiệt độ thật ở cổng là `1.0`, KHÔNG phải 0.2 — hạ nó xuống**

🔴 Đo 24/09: đường sống không truyền `temperature` ⇒ cổng áp **`--temp 1.0`** cho **cả
hai** hồ sơ. Đó là mức cao cho việc dịch, và nó là nghi phạm chung cho **hai** triệu
chứng đã đo: 44/95 mục bị chấm dịch sai, và chỉ **1/3** lượt của `ltt-3.5` qua được
bộ đọc lược đồ. ⇒ Ghim `NHIET_DO_DICH = 0.2` và **đo lại cả hai triệu chứng** sau khi
ghim. ⚠️ `temperature=0.0` **không** làm kết quả tái lập (xem bước 4) — hạ nhiệt độ là
để **giảm tản**, ⛔ không phải để có tái lập.
- [ ] **Bước 5: chạy lại — XANH**
- [ ] **Bước 6: ĐỐI CHỨNG tái lập:** cùng một lô, chạy **5 lần**. Có seed hiệu lực ⇒ 5 kết quả giống nhau. Không ⇒ ghi độ tản đo được (bao nhiêu % đoạn khác nhau).
- [ ] **Bước 7: commit**

---

## Task 10: Xác thực bộ chấm bằng bản chuẩn FLORES (Q6)

**Files:**
- Create: `tools/bench_b2_xac_thuc_bo_cham.py`
- Create: `docs/auto_scan_video_final/B2_XAC_THUC_BO_CHAM.md`

**Interfaces:**
- Produces: `bench_b2_xac_thuc_bo_cham.ti_le_bao_dong_gia(n: int) -> dict`

- [ ] **Bước 1: ngưỡng ĐẠT — viết TRƯỚC**
```
Bộ chấm ĐÁNG TIN khi: tỉ lệ báo động giả ≤ 15% trên ≥ 100 cặp FLORES zh→vi.
Vì sao: model CÙNG LOẠI ở lớp kiểm hình cho 9/9 báo động giả (M-10) ⇒ nghi ngờ có
cơ sở. > 15% ⇒ con số 44/95 KHÔNG dùng được để kết luận về bản dịch.
```
- [ ] **Bước 2:** tải FLORES-200 `zho_Hans` + `vie` (kiểm giấy phép: CC-BY-SA-4.0 — ghi vào `THIRD_PARTY_METRICS.md`).
- [ ] **Bước 3:** đưa **cặp nguồn + bản dịch CHUẨN CỦA NGƯỜI** cho bộ chấm `qc_ai` ngữ nghĩa. Mọi phán quyết "dịch sai" = **báo động giả theo định nghĩa**.
- [ ] **Bước 4:** ĐỐI CHỨNG âm: đưa 30 cặp **đã làm hỏng có chủ ý** (đảo nghĩa, sai thực thể) ⇒ bộ chấm phải bắt được. ⛔ Không có bước này thì tỉ lệ báo động giả 0% có thể chỉ là bộ chấm **không bao giờ báo gì**.
- [ ] **Bước 5:** ghi kết quả + phán quyết vào `B2_XAC_THUC_BO_CHAM.md`.
- [ ] **Bước 6: commit**

---

## Task 11: Glossary + luật tên riêng Hán-Việt (Q5)

**Files:**
- Create: `apps/auto_scan_video/thuat_ngu_zh.py`
- Modify: `apps/auto_scan_video/long_tieng.py:135-195` (lời nhắc)
- Test: `tests/test_<N+5>_asv_ten_rieng_han_viet.py`

**Interfaces:**
- Produces: `thuat_ngu_zh.LUAT_TEN_RIENG: str` (câu đưa vào lời nhắc);
  `thuat_ngu_zh.con_chu_han(van: str) -> list[str]`

- [ ] **Bước 1: phép kiểm ĐỎ trước**

```python
def test_loi_nhac_CO_luat_ten_rieng_han_viet():
    """Q5: chủ dự án chốt phiên Hán-Việt (张伟 → Trương Vĩ)."""
    from apps.auto_scan_video import long_tieng, thuat_ngu_zh
    nhac = long_tieng.loi_nhac(...)   # dựng tham số tối thiểu
    assert thuat_ngu_zh.LUAT_TEN_RIENG in nhac


def test_bat_duoc_chu_han_con_sot_trong_loi_viet():
    """🔴 Đã gặp thật: bản cũ còn SÓT CHỮ HÁN trong lời Việt (L_FIX_TOC_DO)."""
    from apps.auto_scan_video import thuat_ngu_zh
    assert thuat_ngu_zh.con_chu_han("ruột bò 烤 nướng") == ["烤"]
    assert thuat_ngu_zh.con_chu_han("ruột bò nướng") == []
```

- [ ] **Bước 2: chạy — ĐỎ**
- [ ] **Bước 3:** viết `thuat_ngu_zh.py`; `LUAT_TEN_RIENG` nói rõ: tên người/địa danh **phiên Hán-Việt**; tên món ăn/đồ vật **dịch nghĩa**; ⛔ không giữ pinyin (TTS tiếng Việt đọc pinyin rất dễ sai — lỗi đó sẽ hiện ở bước giọng, không ở bước dịch).
- [ ] **Bước 4: chạy lại — XANH**
- [ ] **Bước 5:** nối `con_chu_han` thành một phép kiểm **sau mỗi lượt dịch**; sót chữ Hán ⇒ gắn cờ vào `outputs`, ⛔ đừng im lặng.
- [ ] **Bước 6: commit**

---

## Task 11b: Rào của `ltt-3.5` là LƯỢC ĐỒ, không phải chất lượng

🔴 **Đo 24/09 (n=12) đã trả lời trước câu mà Task 12 định hỏi:**

| | `ltt-3.8` | `ltt-3.5` |
|---|---|---|
| MetricX trung vị | 3,06 | **3,06 — BẰNG NHAU** |
| tốc độ | 1× | **3,2× nhanh hơn** |
| chi phí | 1× | **27,6× rẻ hơn** |
| qua bộ đọc `long_tieng.doc_chuyen` | — | ⛔ **1/3 lượt** |

⇒ **3.5 không yếu về chất lượng.** Thứ chặn nó là **bám đúng định dạng đầu ra**. Đó là
tin tốt: sửa định dạng rẻ hơn nhiều so với đổi model — và Q3 đã chốt dùng 3.5.

⚠️ Và nhớ: **cổng đang chạy `--temp 1.0`** (Task 9 bước 4b). Nhiệt độ cao là nghi phạm
số một cho việc lệch lược đồ. ⇒ **Ghim nhiệt độ TRƯỚC, đo lại tỉ lệ qua lược đồ, RỒI**
mới sửa lời nhắc/bộ đọc — nếu không ta sẽ đi sửa bộ đọc cho một vấn đề do nhiệt độ.

**Files:** Modify `apps/auto_scan_video/long_tieng.py` (lời nhắc + `doc_chuyen`);
Test: `tests/test_<N+5b>_asv_luoc_do_3_5.py`

- [ ] **Bước 1: đo lại tỉ lệ qua lược đồ SAU khi ghim nhiệt độ** (n ≥ 12). Ghi con số trước/sau.
- [ ] **Bước 2: ngưỡng ĐẠT — viết TRƯỚC:** ≥ 90% lượt qua `doc_chuyen` ở n ≥ 12.
- [ ] **Bước 3:** còn dưới ngưỡng ⇒ đọc **lượt hỏng thật** xem nó lệch định dạng **thế nào**
  (thiếu khoá? thêm chữ ngoài JSON? xuống dòng?), ⛔ đừng đoán rồi viết lời nhắc dài hơn.
- [ ] **Bước 4:** sửa **một** thứ mỗi lượt (lời nhắc **hoặc** bộ đọc), đo lại sau mỗi lần.
  ⛔ Sửa cả hai cùng lúc thì không biết cái nào có tác dụng.
- [ ] **Bước 5: ĐỐI CHỨNG** — bộ đọc sau khi nới **vẫn phải TỪ CHỐI** một đầu ra thật sự
  sai. ⛔ Nếu không, "90% qua" chỉ nghĩa là bộ đọc đã hết kiểm gì.
- [ ] **Bước 6: commit**

---

## Task 12: Bench B2 — `ltt-3.5` (mốc `ltt-3.8`) trên FLORES + đoạn thật

**Files:** Create `tools/bench_b2_dich.py`; `docs/auto_scan_video_final/B2_DICH.md`

- [ ] **Bước 1: ngưỡng ĐẠT — viết TRƯỚC**
```
ĐẠT khi: MetricX QE trung vị của `ltt-3.5` ≥ (mốc `ltt-3.8`) − 0,3 trên ≥ 100 cặp
FLORES zh→vi, VÀ 0 trường hợp sót chữ Hán trên 3 phim thật.
⚠️ `ltt-3.8` chạy để làm MỐC, không để chọn lại — Q3 đã chốt dùng 3.5. Mốc cho ta
biết CÁI GIÁ của việc dùng 3.5, nếu có.
⛔ MetricX AUC chỉ 0,61 cho lật nghĩa zh→vi ⇒ QE một mình KHÔNG đủ; phải kèm kết quả
Task 10 (tỉ lệ báo động giả) để biết con số nào đáng tin tới đâu.
```
- [ ] **Bước 2:** đo cả hai model, cùng lời nhắc (đã có glossary Task 11), cùng nhiệt độ (Task 9). Trần **≤ 2 request mỗi model**; ⛔ không giữ `cpu_nhieu` khi chờ máy B.
- [ ] **Bước 3:** đo trên **đoạn thật** của 3 phim (từ bản ghi B1) — không chỉ FLORES.
- [ ] **Bước 4:** ghi bảng + phán quyết; nêu rõ cỡ mẫu từng vế.
- [ ] **Bước 5: commit**

---

## Task 13: Cổng B2 — phán quyết + khai rõ số liệu cho khách (Q1)

- [ ] **Bước 1:** phán quyết B2 theo ngưỡng Task 12. KHÔNG ĐẠT ⇒ **dừng**, báo điều phối.
- [ ] **Bước 2:** thi hành Q1 phần còn nợ: số liệu khiếm khuyết phải hiện **TRƯỚC KHI TRỪ CREDIT**, không phải sau. Tìm chỗ trừ credit (`credit.py`, `jobs.py`) và chỗ hiện (`quan_sat.bang_chung_chat_luong`) rồi khai rõ thứ tự. ⛔ Đây là chỗ có bút toán thật — ⛔ **không** đổi sổ sách, chỉ đổi **thứ tự hiển thị/xác nhận**; không chắc thì hỏi điều phối.
- [ ] **Bước 3:** kiểm bằng **trình duyệt thật** (luật 7): hai con số **hiện thật** (`is_visible`), không lỗi console, khối mở sẵn. ⛔ `TestClient` không thay được — nó xanh khi khối bị gập.
- [ ] **Bước 4:** test nhắm xanh ⇒ gộp `main`, cập nhật `THANG_CONG_TUNG_BUOC.md`.
  ⛔ **Không** L1 ở đây. L1 **một lần ở cuối phiên**, sau khi hết mọi task.

---

## Self-review (đã chạy)

**Độ phủ spec:** Q1→Task 13 · Q2→Global Constraints · Q3→Task 9,12 · Q4→Task 10,12 ·
Q5→Task 11 · Q6→Task 10 · Q7→Task 5 · Q8→Task 1,2,3 · Q9→thứ tự Task · I1→Task 3 ·
I2/I4→Task 1 · I3→Task 2. Mục 5 (vật liệu) →Task 6. Mục 7 (nợ) → còn mở, ghi trong bảng khung.

**Chỗ CHƯA có task, khai tường minh:** B3–B12 chi tiết (có ngưỡng trong bảng khung, chi
tiết viết khi tới — quyết định của chủ dự án); `M-11`; N-07.

**Nhất quán tên:** `chay_mot_buoc` (Task 4) dùng ở Task 6; `do_mot_phim` (Task 6) mở rộng
ở Task 7; `thieu_khai` (Task 1) không đổi tên; `SO_MA`/`HOAN_CREDIT` (Task 2) dùng ở Task 1 test.
