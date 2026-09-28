"""
check_ffmpeg_tran.py — bánh cóc chặn THÊM chỗ gọi `ffmpeg` / `ffprobe` TRẦN.

    py tools/check_ffmpeg_tran.py            # kiem, so voi moc
    py tools/check_ffmpeg_tran.py --list     # liet ke tung cho, kem dong
    py tools/check_ffmpeg_tran.py --accept   # ha moc xuong so hien tai

⭐ VÌ SAO CÓ TỆP NÀY — `N-59`

   `ffmpeg` trên máy này cài **theo người dùng** (WinGet) ⇒ chỉ nằm trên **USER
   Path**. Đo 25/09/2026:

       MACHINE Path có thư mục chứa ffmpeg.exe : False
       USER    Path có thư mục chứa ffmpeg.exe : True

   `LTTStudioWorker` chạy dưới **LocalSystem** ⇒ nhận **MACHINE Path** ⇒ một tiến
   trình con gọi tên **trần** ⛔ không bao giờ tìm thấy nó:
   `FileNotFoundError: [WinError 2]`. Lời gọi đi qua `media.ffmpeg_bin()` miễn
   nhiễm, vì `LTT_FFMPEG` là đường dẫn **tuyệt đối**.

   Đo ngày lập tệp này: **~30 chỗ** gọi tên trần, rải khắp `auto_scan_video`,
   `asv_gpu`, `audio_pause`, `video_assembly`, `qualitylab` và `tools/`. Chúng
   hỏng **cùng một cách**, và ⭐ kiểu hỏng ấy **im lặng**: một tay bắt rộng nuốt
   `WinError 2` thành một dòng log, rồi lượt chạy báo **thành công**. Ca thật:
   sidecar WhisperX chưa bao giờ chạy trên worker production (`N-59`), và trước
   đó là bước VAD của `apps/transcript` (22/09).

⛔ VÌ SAO KHÔNG ĐI SỬA ~30 CHỖ

   Tiến trình con **thừa kế `PATH`**, nên mồi `PATH` **một lần** lúc dịch vụ khởi
   động (`platform_core.media.bao_dam_ffmpeg_tren_path`) là đủ cho **cả ~30**.
   Sửa từng chỗ là làm ~30 lần việc mà **một lần** đã xong — và bỏ sót chỗ thứ
   31, vì người viết chỗ thứ 31 ⛔ không biết luật này tồn tại.

   ⇒ Tệp này **⛔ không dọn quá khứ** — nó **chặn tương lai**. Cùng khuôn
   `check_so_test.py` / `check_ruff.py`: một cái mốc, ⛔ không cho tăng.

🔑 ĐỌC **AST**, ⛔ KHÔNG SO CHUỖI

   Một phép so chuỗi (`grep`) tự khớp vào **docstring của chính nó** — và tệp
   này nói về `ffmpeg` nhiều hơn bất kỳ tệp nào trong kho, nên nó sẽ là "chỗ
   phạm lỗi" nặng nhất. AST ⛔ không nhìn thấy chữ trong chú thích, trong
   docstring, trong tên khoá từ điển (`ho_so["ffmpeg"] = ...`) hay trong một bản
   khai `requires=("ffmpeg",)`. Nó chỉ thấy đúng **hai hình dạng** gây hỏng:

     1. hằng chuỗi `ffmpeg`/`ffprobe` ở **vị trí 0** của một list/tuple **viết
        thẳng** — tức `argv[0]` của một lời gọi tiến trình con;
     2. `shutil.which("ffmpeg")` — dò trên `PATH`, hỏng y hệt.

⭐ MIỄN TRỪ LÀ **CƠ HỌC**, ⛔ KHÔNG PHẢI DANH SÁCH GÕ TAY

   Một mô-đun tự gọi `bao_dam_ffmpeg_tren_path` thì đã có thuốc ⇒ được miễn. Nhờ
   thế, chữa một tệp làm nó **tự rụng** khỏi mốc; ⛔ không ai phải sửa hai chỗ.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
import warnings
from typing import TypeGuard

# 🔴 Cong cu nay IN `⛔`/`⭐`. Console Windows mac dinh cp1252 => `UnicodeEncodeError`
#    va no chet TRUOC khi in ket qua — trong y het mot loi cong cu, khong phai mot
#    phan quyet. Mot phien khac mat mot luot vi dung cho nay (25/09).
#    ⭐ Mot CONG GATE phai in duoc thong bao cua chinh no, o moi console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GOC = pathlib.Path(__file__).resolve().parent.parent
TEP_MOC = pathlib.Path(__file__).with_name("check_ffmpeg_tran.moc")
DAU_HIEU = "# so-cho-goi-ffmpeg-tran theo tep"

#: Mốc RIÊNG cho luật MỚI (B13, 28/09) — ⛔ KHÔNG dùng chung `TEP_MOC`/
#: `DAU_HIEU`: hai luật hỏi hai câu khác nhau ("gọi tên trần" so với "mở
#: filtergraph mà không khai luồng"), và gộp chúng dưới MỘT con số sẽ làm
#: một chỗ dọn ở luật này che một chỗ thêm ở luật kia — đúng bẫy `check_so_
#: test.py` mà `doc_moc` đã ghi lại.
TEP_MOC_LOC = pathlib.Path(__file__).with_name("check_ffmpeg_tran_loc.moc")
DAU_HIEU_LOC = "# so-cho-thieu-luong-loc-theo-tep"

#: Nhãn BƯỚC cho luật MỚI — phơi ra để `gate.py` (phiên sở hữu) nối một bước
#: RIÊNG bằng TÊN nếu muốn một dòng báo cáo tách biệt, ⛔ không phải gõ lại
#: chuỗi. `main()` của CHÍNH tệp này đã tự kiểm CẢ HAI luật trong một lần
#: chạy (Step "ffmpeg tran" hiện có gọi đúng tệp này), nên KHÔNG bắt buộc
#: phải thêm một Step mới — hằng số này chỉ có ích nếu muốn tách dòng.
TEN_BUOC_LOC = "ffmpeg loc luong (thieu filter_threads/filter_complex_threads)"

#: ⚠️ `frozenset({...})` — ⛔ **KHÔNG** một tuple/list. Một tuple `("ffmpeg", …)`
#:    ở đây sẽ khớp **luật 1 của chính nó**, và bánh cóc tố cáo chính mình.
TEN_TRAN = frozenset({"ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"})

#: Hàm mồi PATH. Mô-đun nào gọi nó thì đã có thuốc (xem docstring).
TEN_HAM_MOI = "bao_dam_ffmpeg_tren_path"

#: ⛔ Không quét: sản phẩm build, thư viện vendor, cây của phiên khác, và chính
#:    tệp này (nó giữ `TEN_TRAN`) cùng phép kiểm của nó.
BO_QUA_THU_MUC = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__", "vendor",
    ".claude", ".codex", "test-results", "dist", "build", "_luutru",
})
BO_QUA_TEP = frozenset({"tools/check_ffmpeg_tran.py"})

#: ⛔ `tests/` nằm ngoài phép đếm — và đó là một **quyết định về MÔ HÌNH THIỆT
#: HẠI**, ⛔ không phải một chỗ nới cho dễ xanh.
#:
#: Thứ `N-59` nói là: một tên trần trong **mã sản phẩm** hỏng dưới `LocalSystem`
#: **im lặng** — bị một tay bắt rộng nuốt, và lượt chạy vẫn báo thành công. Một
#: tên trần trong một phép kiểm thì ⛔ không im lặng: nó **đỏ**, ngay, và người
#: chạy đọc được. Ngoài ra phần lớn là hằng để **khẳng định** `argv` của một bản
#: giả (`cmd[0] == "ffmpeg"`), ⛔ không phải một lời gọi tiến trình con nào cả.
#:
#: ⚠️ Đo lúc lập: gộp `tests/` vào thì mốc là **113 chỗ / 45 tệp** thay vì con số
#: sản phẩm — tức bánh cóc sẽ đỏ vì một phép kiểm mới viết, và người ta sẽ **tắt
#: nó**. Một báo động giả làm người ta tắt cổng thì tệ hơn không có cổng.
THU_MUC_GOC_BO_QUA = frozenset({"tests"})


def _la_ten_tran(nut: ast.AST) -> TypeGuard[ast.Constant]:
    """`TypeGuard`, khong chi `bool`: hai cho goi ham nay doc lai `.value` ngay
    sau do — mypy chi thu hep `nut` tu `ast.expr`/`ast.AST` xuong `ast.Constant`
    (co `.value`) khi ham tra dung TypeGuard cua dung nhanh dieu kien."""
    return isinstance(nut, ast.Constant) and nut.value in TEN_TRAN


#: Hàm sinh tiến trình con. Một list/tuple đi **thẳng** vào đây thì là `argv`.
TEN_HAM_SINH = frozenset({"run", "Popen", "call", "check_call", "check_output"})


def _co_co(nut) -> bool:
    """List/tuple này có một **cờ** (`-v`, `-y`, `-i`…) không?

    🔑 Đây là thứ phân biệt một **dòng lệnh** với một **bản khai**. Cả hai đều là
    tuple có `ffmpeg` ở vị trí 0, và ⛔ không đếm được chúng như nhau:

        requires=("ffmpeg",)                      -> BAN KHAI nang luc (manifest)
        "evaluators": ("ffprobe", "pillow", …)    -> BAN KHAI bo do (registry)
        ["ffmpeg", "-nostdin", "-i", duong]       -> DONG LENH  <- thu ta dem

    ⚠️ Bản đầu ⛔ không có phép phân biệt này và đếm cả ba ⇒ mốc mang **3 bản
    khai** trong `apps/*/manifest.py` + `qualitylab/registry.py`. Một bánh cóc
    đếm lẫn hai loại vật thể thì con số của nó ⛔ không nói về điều gì cả, và lần
    đầu ai đó thêm một app khai `requires=("ffmpeg",)` nó sẽ đỏ **sai**.
    """
    return any(isinstance(e, ast.Constant) and isinstance(e.value, str)
               and e.value.startswith("-") for e in nut.elts[1:])


def _cay_hop_le(nguon: str) -> ast.Module | None:
    """`ast.parse` — `None` nếu cú pháp hỏng (đó là việc của bước
    `bien dich duoc`, ⛔ không phải của tệp này), lặng SyntaxWarning của tệp
    ĐANG quét (xem chú thích cũ ở `cho_goi_tran`)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            return ast.parse(nguon)
    except SyntaxError:
        return None


def _cac_dong_lenh_that(cay: ast.AST) -> list[ast.List | ast.Tuple]:
    """Mọi List/Tuple là một DÒNG LỆNH tiến trình con viết thẳng (⛔ không
    phải một bản khai/registry) — dùng chung cho cả HAI luật, và CỐ Ý ⛔
    không đòi vị trí 0 phải là tên `ffmpeg`/`ffprobe`: luật MỚI
    (`cho_thieu_luong_loc`, B13, 28/09) phải bắt được CẢ những dòng lệnh đã
    gọi ĐÚNG `media.ffmpeg_bin()` (miễn với luật 1) mà vẫn thiếu cờ luồng —
    hai bệnh khác nhau, ⛔ không chung một tiêu chí lọc.

    Tiêu chí: `argv` viết thẳng trong một lời gọi sinh tiến trình con
    (`TEN_HAM_SINH`), HOẶC có ít nhất một cờ (`_co_co`) — phân biệt DÒNG LỆNH
    với BẢN KHAI (`requires=("ffmpeg",)`). Cùng một câu hỏi "đây có phải một
    dòng lệnh thật không", ⛔ không được trả lời hai lần theo hai cách có thể
    LỆCH nhau.
    """
    la_argv: set[int] = set()
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Call) or not nut.args:
            continue
        ten_ham = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                   else nut.func.id if isinstance(nut.func, ast.Name) else "")
        if ten_ham in TEN_HAM_SINH and isinstance(nut.args[0], (ast.List, ast.Tuple)):
            la_argv.add(id(nut.args[0]))

    ra: list[ast.List | ast.Tuple] = []
    for nut in ast.walk(cay):
        if not (isinstance(nut, (ast.List, ast.Tuple)) and nut.elts):
            continue
        if id(nut) in la_argv or _co_co(nut):
            ra.append(nut)
    return ra


def cho_goi_tran(nguon: str) -> list[tuple[int, str]]:
    """`[(dong, ten)]` cho mọi chỗ gọi `ffmpeg`/`ffprobe` trần trong một nguồn.

    ⛔ Cú pháp hỏng ⇒ trả rỗng: bước `bien dich duoc` của gate là chủ của câu
       hỏi đó, và một tệp không phân tích được ⛔ không phải phát hiện của tệp này.
    """
    cay = _cay_hop_le(nguon)
    if cay is None:
        return []

    ra: list[tuple[int, str]] = []
    # Luật 1 — hằng chuỗi ở vị trí 0 của một DÒNG LỆNH viết thẳng = argv[0].
    #    ⚠️ Lọc THÊM bằng `_la_ten_tran(dau)` ở đây — CHỈ luật 1 cần vị trí 0
    #    là tên trần; `_cac_dong_lenh_that` cố ý không lọc theo tên.
    for nut in _cac_dong_lenh_that(cay):
        dau = nut.elts[0]
        if _la_ten_tran(dau):
            ra.append((dau.lineno, str(dau.value)))
    # Luật 2 — `shutil.which("ffmpeg")`: dò trên PATH, hỏng y hệt.
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Call) and nut.args and _la_ten_tran(nut.args[0]):
            hang = nut.args[0]                 # TypeGuard chi thu hep BIEN, khong thu hep chi so
            ten_ham = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                       else nut.func.id if isinstance(nut.func, ast.Name) else "")
            if ten_ham == "which":
                ra.append((hang.lineno, str(hang.value)))
    return sorted(ra)


# ══════════════════════════════════════════════════════════════════════════════
#  LUẬT MỚI (B13, 28/09) — lời gọi mở filtergraph phải khai luồng cho NÓ
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Ca thứ TƯ của lớp lỗi "cần gạt mang đúng tên mà ⛔ không nối vào đâu cả"
#    (sau OMP_NUM_THREADS · cv2.setNumThreads · asr_options batched) — và TỆ
#    HƠN ba ca trước: `-threads` CÓ nối, nhưng chỉ nối luồng GIẢI MÃ. Bộ lọc
#    `-vf`/`-filter_complex` mở MỘT POOL LUỒNG RIÊNG mà `-threads` ⛔ không
#    với tới. Làn L4 đo trên video thật: `-threads 2` một mình đỉnh
#    **13,42 lõi**; thêm `-filter_threads 2 -filter_complex_threads 2` hạ
#    xuống **2,27-2,41 lõi**.
#
# ⛔ Một bánh cóc hỏi "đã đặt `-threads` chưa" sẽ XANH trên lời gọi ăn 13 lõi
#    — nó đo CÓ MẶT MỘT CỜ, ⛔ không đo TÍNH CHẤT "luồng đã bị chặn CHƯA".
#    Luật này neo đúng cặp cờ ffmpeg THẬT: `-filter_threads` chặn filtergraph
#    ĐƠN (`-vf`), `-filter_complex_threads` chặn filtergraph PHỨC
#    (`-filter_complex`). Đo trên L4 cho thấy lời gọi vá ĐÚNG mang CẢ HAI cờ
#    dù chỉ dùng `-filter_complex` — nên `-filter_threads` được đòi bất kể
#    dạng filtergraph nào, và `-filter_complex_threads` đòi THÊM khi có
#    `-filter_complex`.
#
# ⚠️ Phạm vi CÓ Ý HẸP: chỉ `-vf`/`-filter_complex` (hai cờ L4 đo được). Cờ lọc
#    khác (`-af`, `-filter:v`…) NGOÀI phạm vi đã đo — thêm khi có bằng chứng,
#    ⛔ đoán trước.
CO_MO_LOC: dict[str, tuple[str, ...]] = {
    "-vf": ("-filter_threads",),
    "-filter_complex": ("-filter_threads", "-filter_complex_threads"),
}


def cho_thieu_luong_loc(nguon: str) -> list[tuple[int, str]]:
    """`[(dong, mo_ta)]` — dòng lệnh ffmpeg có `-vf`/`-filter_complex` mà
    THIẾU cờ luồng bắt buộc theo `CO_MO_LOC` (xem khối trên vì sao)."""
    cay = _cay_hop_le(nguon)
    if cay is None:
        return []

    ra: list[tuple[int, str]] = []
    for nut in _cac_dong_lenh_that(cay):
        co_chuoi = {e.value for e in nut.elts
                   if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        can: set[str] = set()
        for co_loc, doi in CO_MO_LOC.items():
            if co_loc in co_chuoi:
                can.update(doi)
        thieu = sorted(can - co_chuoi)
        if thieu:
            ra.append((nut.elts[0].lineno, f"thieu {','.join(thieu)}"))
    return sorted(ra)


def co_thuoc(nguon: str) -> bool:
    """Mô-đun này tự mồi `PATH` chưa? (miễn trừ cơ học — xem docstring)"""
    return TEN_HAM_MOI in nguon


def _duong_tuong_doi(tep: pathlib.Path) -> str:
    return tep.relative_to(GOC).as_posix()


def quet() -> dict[str, list[tuple[int, str]]]:
    """`{duong/dan.py: [(dong, ten)]}` — chỉ các tệp CÒN chỗ trần và CHƯA có thuốc."""
    ra: dict[str, list[tuple[int, str]]] = {}
    for tep in sorted(GOC.rglob("*.py")):
        if any(p in BO_QUA_THU_MUC for p in tep.relative_to(GOC).parts[:-1]):
            continue
        duong = _duong_tuong_doi(tep)
        if duong in BO_QUA_TEP or duong.split("/")[0] in THU_MUC_GOC_BO_QUA:
            continue
        try:
            nguon = tep.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if co_thuoc(nguon):
            continue
        cho = cho_goi_tran(nguon)
        if cho:
            ra[duong] = cho
    return ra


def quet_loc() -> dict[str, list[tuple[int, str]]]:
    """`{duong/dan.py: [(dong, mo_ta)]}` cho LUẬT MỚI — chỗ mở filtergraph mà
    thiếu cờ khai luồng bắt buộc.

    ⛔ **KHÔNG** áp dụng miễn trừ `co_thuoc()` (mồi PATH) ở đây — đó là thuốc
    cho *"gọi tên trần"* (luật 1), ⛔ không liên quan tới câu hỏi *"filtergraph
    có bị chặn luồng chưa"*: một tệp có thể đã gọi đúng `media.ffmpeg_bin()`
    (miễn với luật 1) mà VẪN thiếu `-filter_complex_threads` (vi phạm luật
    này) — hai bệnh khác nhau, một thuốc chữa một bệnh.
    """
    ra: dict[str, list[tuple[int, str]]] = {}
    for tep in sorted(GOC.rglob("*.py")):
        if any(p in BO_QUA_THU_MUC for p in tep.relative_to(GOC).parts[:-1]):
            continue
        duong = _duong_tuong_doi(tep)
        if duong in BO_QUA_TEP or duong.split("/")[0] in THU_MUC_GOC_BO_QUA:
            continue
        try:
            nguon = tep.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cho = cho_thieu_luong_loc(nguon)
        if cho:
            ra[duong] = cho
    return ra


def doc_moc(tep_moc: pathlib.Path = TEP_MOC) -> dict[str, int]:
    """`{duong/dan.py: so_luong}` được phép còn lại.

    🔴 **THEO TỆP, ⛔ không phải một tổng.** Một tổng im lặng khi ai đó dọn một
    chỗ ở tệp A và thêm một chỗ ở tệp B trong cùng lượt — đúng cái bẫy
    `check_so_test.py` đã trả giá ngày 25/08 và ghi lại.

    `tep_moc` — mặc định `TEP_MOC` (luật 1); luật MỚI (`filter_threads`)
    dùng `TEP_MOC_LOC`, MỘT mốc RIÊNG (⛔ không trộn hai con số dưới một
    tên — yêu cầu người điều phối 28/09).
    """
    try:
        tho = tep_moc.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    ra: dict[str, int] = {}
    for dong in tho.splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue
        duong, _, so = dong.rpartition(" ")
        if duong and so.isdigit():
            ra[duong.strip()] = int(so)
    return ra


def ghi_moc(hien_tai: dict[str, list[tuple[int, str]]],
           tep_moc: pathlib.Path = TEP_MOC, dau_hieu: str = DAU_HIEU) -> None:
    dong = [dau_hieu]
    dong += [f"{d} {len(v)}" for d, v in sorted(hien_tai.items())]
    tep_moc.write_text("\n".join(dong) + "\n", encoding="utf-8", newline="\n")


def so_voi_moc(hien_tai: dict[str, list[tuple[int, str]]],
               moc: dict[str, int]) -> tuple[list[str], list[str]]:
    """`(tang, giam)` — hai danh sách dòng người đọc được.

    ⭐ Tách khỏi `main()` để **chính phép so** kiểm được. Một bánh cóc chưa bao
    giờ thấy ĐỎ là một bánh cóc chưa được chứng minh: `tests/test_4500_*` bơm một
    chỗ thêm và một tệp mới vào đây rồi đòi nó đỏ.
    """
    tang: list[str] = []
    for duong, cho in sorted(hien_tai.items()):
        cu = moc.get(duong)
        if cu is None:
            tang.append(f"  + TEP MOI  {duong}  ({len(cho)} cho): "
                        + ", ".join(f"dong {d}" for d, _ in cho))
        elif len(cho) > cu:
            tang.append(f"  + TANG     {duong}  {cu} -> {len(cho)}: "
                        + ", ".join(f"dong {d}" for d, _ in cho))
    giam = [f"  - GIAM     {d}  {moc[d]} -> {len(hien_tai.get(d, []))}"
            for d in sorted(moc) if len(hien_tai.get(d, [])) < moc[d]]
    return tang, giam


def _kiem_mot_luat(nhan: str, hien_tai: dict[str, list[tuple[int, str]]],
                   tep_moc: pathlib.Path, dau_hieu: str, *,
                   liet_ke: bool, chap_nhan: bool,
                   thong_bao_thuoc: list[str]) -> tuple[bool, bool]:
    """In một khối kết quả cho MỘT luật, trả `(that_bai, moc_thieu)`.

    Tách khỏi `main()` để hai luật in đối xứng và ⛔ không lẫn số của nhau —
    mỗi khối tự mang nhãn `nhan` của nó.
    """
    tong = sum(len(v) for v in hien_tai.values())
    moc = doc_moc(tep_moc)

    if liet_ke:
        for duong, cho in sorted(hien_tai.items()):
            for dong_so, mo_ta in cho:
                print(f"[{nhan}] {duong}:{dong_so}  {mo_ta}")
        print(f"[{nhan}] -- tong {tong} cho / {len(hien_tai)} tep")

    if chap_nhan:
        ghi_moc(hien_tai, tep_moc, dau_hieu)
        print(f"[{nhan}] da ha moc: {tong} cho / {len(hien_tai)} tep")
        return False, False

    if not moc:
        ghi_moc(hien_tai, tep_moc, dau_hieu)
        print(f"[{nhan}] chua co moc -> ghi moc dau tien: {tong} cho / "
             f"{len(hien_tai)} tep")
        return False, False

    tang, giam = so_voi_moc(hien_tai, moc)

    if tang:
        print(f"[{nhan}] RESULT: FAIL - {tong} cho:")
        print("\n".join(tang))
        print()
        for dong in thong_bao_thuoc:
            print(dong)
        return True, False

    if giam:
        print(f"[{nhan}]    da GIAM (dung --accept tuong ung de ha moc):")
        print("\n".join(giam))
    print(f"[{nhan}] dat moc: {tong} cho / {len(hien_tai)} tep — RESULT: PASS")
    return False, False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chan them cho goi ffmpeg tran")
    p.add_argument("--list", action="store_true",
                   help="liet ke tung cho (ca hai luat)")
    p.add_argument("--accept", action="store_true",
                   help="ha moc luat 1 (goi ten tran) xuong so hien tai")
    p.add_argument("--accept-loc", action="store_true",
                   help="ha moc luat MOI (thieu filter_threads) xuong so hien tai")
    p.add_argument("--chi-loc", action="store_true",
                   help="chi kiem luat MOI — dung cho mot Step gate rieng "
                       "(TEN_BUOC_LOC) neu can mot dong bao cao tach biet")
    a = p.parse_args(argv)

    that_bai = False

    if not a.chi_loc:
        loi_1, _ = _kiem_mot_luat(
            "ffmpeg ten tran", quet(), TEP_MOC, DAU_HIEU,
            liet_ke=a.list, chap_nhan=a.accept, thong_bao_thuoc=[
                "⛔ Ten tran hong duoi LocalSystem (MACHINE Path khong co ffmpeg) —",
                "   `FileNotFoundError: [WinError 2]`, va thuong bi nuot im lang.",
                "⭐ THUOC: goi `platform_core.media.bao_dam_ffmpeg_tren_path()` mot lan",
                "   trong mo-dun (hoac o diem khoi dong dich vu) — tien trinh con thua",
                "   ke PATH. Mo-dun nao goi no thi tu duoc mien tru.",
                "⛔ KHONG viet mot duong dan tuyet doi vao ma, va KHONG ghi lai ten",
                "   binary theo kieu `C:\\ffmpeg\\bin\\ffmpeg.exe` — dat may khac thi sai.",
                "   Can chinh mot duong dan thi dung `media.ffmpeg_bin()`.",
            ])
        that_bai = that_bai or loi_1

    loi_2, _ = _kiem_mot_luat(
        "ffmpeg loc luong", quet_loc(), TEP_MOC_LOC, DAU_HIEU_LOC,
        liet_ke=a.list, chap_nhan=a.accept_loc, thong_bao_thuoc=[
            "⛔ `-vf`/`-filter_complex` mo MOT POOL LUONG RIENG ma `-threads`",
            "   (chi cham luong GIAI MA) KHONG voi toi — do that: `-threads 2`",
            "   mot minh dinh 13,42 loi; them `-filter_threads`/",
            "   `-filter_complex_threads` ha xuong 2,27-2,41 loi.",
            "⭐ THUOC: them cac co con thieu (xem CO_MO_LOC) vao CUNG dong lenh.",
            "⛔ KHONG chi dua vao `-threads` — no ⛔ khong cham filtergraph.",
        ])
    that_bai = that_bai or loi_2

    return 1 if that_bai else 0


if __name__ == "__main__":
    sys.exit(main())
