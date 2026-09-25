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

GOC = pathlib.Path(__file__).resolve().parent.parent
TEP_MOC = pathlib.Path(__file__).with_name("check_ffmpeg_tran.moc")
DAU_HIEU = "# so-cho-goi-ffmpeg-tran theo tep"

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


def _la_ten_tran(nut: ast.AST) -> bool:
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


def cho_goi_tran(nguon: str) -> list[tuple[int, str]]:
    """`[(dong, ten)]` cho mọi chỗ gọi `ffmpeg`/`ffprobe` trần trong một nguồn.

    ⛔ Cú pháp hỏng ⇒ trả rỗng: bước `bien dich duoc` của gate là chủ của câu
       hỏi đó, và một tệp không phân tích được ⛔ không phải phát hiện của tệp này.
    """
    try:
        # ⚠️ `ast.parse` phát `SyntaxWarning` cho chuỗi escape hỏng ở tệp ĐANG
        #    QUÉT (vd `"\c"`), in ra dưới tên `<unknown>` và làm đầu ra của bánh
        #    cóc trông như lỗi của chính nó. Đó là việc của bước `ruff`/
        #    `bien dich duoc`, ⛔ không phải của tệp này.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            cay = ast.parse(nguon)
    except SyntaxError:
        return []
    # `argv` viết thẳng trong một lời gọi sinh tiến trình con — kể cả khi ⛔ không
    # có cờ nào (`[bin, vao, ra]`).
    la_argv: set[int] = set()
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Call) or not nut.args:
            continue
        ten_ham = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                   else nut.func.id if isinstance(nut.func, ast.Name) else "")
        if ten_ham in TEN_HAM_SINH and isinstance(nut.args[0], (ast.List, ast.Tuple)):
            la_argv.add(id(nut.args[0]))

    ra: list[tuple[int, str]] = []
    for nut in ast.walk(cay):
        # Luật 1 — hằng chuỗi ở vị trí 0 của một DÒNG LỆNH viết thẳng = argv[0].
        if isinstance(nut, (ast.List, ast.Tuple)) and nut.elts:
            dau = nut.elts[0]
            if _la_ten_tran(dau) and (id(nut) in la_argv or _co_co(nut)):
                ra.append((dau.lineno, str(dau.value)))       # type: ignore[union-attr]
            continue
        # Luật 2 — `shutil.which("ffmpeg")`: dò trên PATH, hỏng y hệt.
        if isinstance(nut, ast.Call) and nut.args and _la_ten_tran(nut.args[0]):
            ten_ham = (nut.func.attr if isinstance(nut.func, ast.Attribute)
                       else nut.func.id if isinstance(nut.func, ast.Name) else "")
            if ten_ham == "which":
                ra.append((nut.args[0].lineno, str(nut.args[0].value)))  # type: ignore[union-attr]
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


def doc_moc() -> dict[str, int]:
    """`{duong/dan.py: so_luong}` được phép còn lại.

    🔴 **THEO TỆP, ⛔ không phải một tổng.** Một tổng im lặng khi ai đó dọn một
    chỗ ở tệp A và thêm một chỗ ở tệp B trong cùng lượt — đúng cái bẫy
    `check_so_test.py` đã trả giá ngày 25/08 và ghi lại.
    """
    try:
        tho = TEP_MOC.read_text(encoding="utf-8").strip()
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


def ghi_moc(hien_tai: dict[str, list[tuple[int, str]]]) -> None:
    dong = [DAU_HIEU]
    dong += [f"{d} {len(v)}" for d, v in sorted(hien_tai.items())]
    TEP_MOC.write_text("\n".join(dong) + "\n", encoding="utf-8", newline="\n")


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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chan them cho goi ffmpeg tran")
    p.add_argument("--list", action="store_true", help="liet ke tung cho")
    p.add_argument("--accept", action="store_true", help="ha moc xuong so hien tai")
    a = p.parse_args(argv)

    hien_tai = quet()
    tong = sum(len(v) for v in hien_tai.values())
    moc = doc_moc()

    if a.list:
        for duong, cho in sorted(hien_tai.items()):
            for dong_so, ten in cho:
                print(f"{duong}:{dong_so}  {ten}")
        print(f"-- tong {tong} cho / {len(hien_tai)} tep")

    if a.accept:
        ghi_moc(hien_tai)
        print(f"[ffmpeg tran] da ha moc: {tong} cho / {len(hien_tai)} tep")
        return 0

    if not moc:
        ghi_moc(hien_tai)
        print(f"[ffmpeg tran] chua co moc -> ghi moc dau tien: {tong} cho / "
              f"{len(hien_tai)} tep")
        return 0

    tang, giam = so_voi_moc(hien_tai, moc)

    if tang:
        print("RESULT: FAIL - them cho goi `ffmpeg`/`ffprobe` TRAN:")
        print("\n".join(tang))
        print()
        print("⛔ Ten tran hong duoi LocalSystem (MACHINE Path khong co ffmpeg) —")
        print("   `FileNotFoundError: [WinError 2]`, va thuong bi nuot im lang.")
        print("⭐ THUOC: goi `platform_core.media.bao_dam_ffmpeg_tren_path()` mot lan")
        print("   trong mo-dun (hoac o diem khoi dong dich vu) — tien trinh con thua")
        print("   ke PATH. Mo-dun nao goi no thi tu duoc mien tru.")
        print("⛔ KHONG viet mot duong dan tuyet doi vao ma, va KHONG ghi lai ten")
        print("   binary theo kieu `C:\\ffmpeg\\bin\\ffmpeg.exe` — dat may khac thi sai.")
        print("   Can chinh mot duong dan thi dung `media.ffmpeg_bin()`.")
        return 1

    if giam:
        print("   da GIAM (nho `--accept` de ha moc, neu khong lan sau se troi lai):")
        print("\n".join(giam))
    print(f"[ffmpeg tran] dat moc: {tong} cho / {len(hien_tai)} tep")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
