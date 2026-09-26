r"""Worktree nằm TRONG kho — và luật thật, ⛔ không phải luật ta tưởng.

## Ca thật, 25–26/09/2026

Một phiên dựng `git worktree add LTTGateBaseline68cde0 <sha>` **ngay trong**
`D:\LTTSTUDIOSAPP` để trả lời câu *"ta làm hỏng hay vốn hỏng"* — kỹ thuật đúng,
**chỗ đặt sai**. Hậu quả đo được:

    find . -name "*.py"  ->  7241      sau khi go  ->  4778
    F401 408->813 · F811 379->758 · B905 41->82 · B904 21->42 ...

Nó **chặn commit của MỌI phiên**, không riêng người tạo.

## 🔑 Luật thật — và vì sao "cứ gitignore là xong" là SAI

Đo 26/09, ba thư mục, ba kết quả khác nhau:

| thư mục | gitignored? | ruff thấy? | vì sao |
|---|---|---|---|
| `.claude/worktrees/` (2096 tệp `.py`) | ✅ (`.gitignore:138`) | ⛔ **không** | ruff mặc định `respect-gitignore = true` |
| `.codex/worktrees/` | ⛔ không | ✅ **có** | nên `ruff.toml` phải loại **tay** (chú thích ghi F401 411→821) |
| `LTTGateBaseline68cde0/` | ⛔ không | ✅ **có** | ⇒ **nó** mới là cái đã thổi |

⇒ Worktree trong kho chỉ thổi bánh cóc **nếu nó ⛔ không gitignored** — với công
cụ **tôn trọng gitignore**. ⚠️ Nhưng công cụ **quét hệ tệp** (`scan_source_secrets.py`)
thì thổi kiểu gì cũng được, **trừ khi** loại tường minh — và đó là lý do
`.claude`/`.codex` nằm trong `EXCLUDED_DIRS` của máy quét ấy.

⭐ Nên điều kiện để một worktree trong kho là **chấp nhận được** gồm **CẢ HAI**:
gitignored **và** có trong danh sách loại của máy quét bí mật. Thiếu một vế là
một bánh cóc nào đó đang đếm hai lần mà ⛔ chưa ai biết.

## ⛔ Thứ tệp này KHÔNG làm

Nó ⛔ không xoá gì. Một worktree có thể đang mang việc chưa commit của phiên
khác (luật 4 `CLAUDE.md`). Nó chỉ **nói ra**, kèm đúng lệnh để tự xử — và
`git worktree remove` **từ chối** khi cây còn thay đổi, còn `rm -rf` thì
**mất**. Đó là khác biệt đáng nói ra chứ không đáng giả định người đọc biết.
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def goc_cay_chinh() -> Path:
    """Gốc của **cây chính** dùng chung, ⛔ không phải cây đang chạy lệnh này.

    🔴 Bản đầu dùng `ROOT` (cây chứa tệp này) và vì thế **PASS sai**: chạy từ
       một worktree riêng thì `.claude/worktrees/...` của cây chính nằm NGOÀI
       `ROOT`, nên nó báo *"không worktree nào trong kho"* trong khi cây chính
       đang có một cái.

    ⭐ Câu phải hỏi là *"có worktree nào nằm trong **cây chính** không"* — vì cây
       chính là thứ mọi phiên dùng chung và là nơi bánh cóc bị đếm hai lần.
       `--git-common-dir` trả `.git` **chung** (⛔ không phải `.git` của worktree),
       nên cha của nó là gốc cây chính, dù ta đang đứng ở đâu.
    """
    ra = subprocess.run(["git", "rev-parse", "--path-format=absolute",
                         "--git-common-dir"],
                        cwd=ROOT, capture_output=True, text=True)
    return Path(ra.stdout.strip()).resolve().parent


def _stdout_utf8() -> None:
    """Console Windows là cp1252 và ⛔ không mã hoá được `⭐`/`⛔`.

    ⚠️ Gọi trong `main()`, ⛔ KHÔNG ở mức module: bọc `sys.stdout` lúc import
       làm mọi tệp test import mô-đun này bị đổi stdout, và pytest đóng buffer ⇒
       `ValueError: I/O operation on closed file`. Đã cắn thật ở
       `tools/check_phu_thuoc_npm.py` bản đầu.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)


def worktree_trong_kho() -> list[Path]:
    """Đường dẫn các worktree nằm DƯỚI gốc kho (⛔ không tính chính gốc kho)."""
    ra = subprocess.run(["git", "worktree", "list", "--porcelain"],
                        cwd=ROOT, capture_output=True, text=True)
    goc = goc_cay_chinh()
    trong = []
    for dong in ra.stdout.splitlines():
        if not dong.startswith("worktree "):
            continue
        p = Path(dong[len("worktree "):].strip()).resolve()
        if p == goc:
            continue
        try:
            p.relative_to(goc)
        except ValueError:
            continue          # ngoài kho — đúng chỗ, không phải vấn đề
        trong.append(p)
    return trong


def _bi_gitignore(p: Path) -> bool:
    """`p` co bi gitignore khong — hoi TU CAY CHINH.

    🔴 Ban dau chay voi `cwd=ROOT` (cay dang chay lenh). Khi `p` nam o cay
       CHINH ma ta dung o mot worktree rieng, `git check-ignore` giai `p` theo
       cay rieng va tra ve "KHONG bi ignore" — mot cau tra loi SAI, ⛔ khong
       phai mot loi. `.claude/` co trong `.gitignore:138`, va no van bao KHONG.

    ⭐ Cung ho voi bay da ghi trong so: mot kenh khong the tra loi cau ta dang
       hoi thi no van tra ve mot gia tri trong nhu cau tra loi.
    """
    ra = subprocess.run(["git", "check-ignore", "-q", str(p)],
                        cwd=goc_cay_chinh(), capture_output=True, text=True)
    return ra.returncode == 0


def _may_quet_co_loai(p: Path) -> bool:
    """Máy quét bí mật có loại đường dẫn này không.

    ⭐ Hỏi **chính máy quét** (`_is_excluded_file`), ⛔ không đọc lại danh sách
       `EXCLUDED_DIRS` — một bản sao thứ hai của luật sẽ trôi khỏi bản gốc, và
       kho này đã mất nhiều buổi cho đúng khuôn ấy.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import scan_source_secrets as mq          # type: ignore[import-not-found]
    except Exception as loi:                      # noqa: BLE001
        print(f"  [!] khong nap duoc scan_source_secrets: {loi}")
        return False
    # Một tệp bất kỳ BÊN TRONG worktree đó — nếu máy quét loại nó thì loại cả cây.
    thu = p / "x.py"
    try:
        return bool(mq._is_excluded_file(goc_cay_chinh(), thu))
    except Exception:                             # noqa: BLE001
        return False


def main() -> int:
    trong = worktree_trong_kho()
    if not trong:
        print("RESULT: PASS  (khong worktree nao nam trong kho)")
        return 0

    do = []
    for p in trong:
        tuong_doi = p.relative_to(goc_cay_chinh()).as_posix()
        gi = _bi_gitignore(p)
        mq = _may_quet_co_loai(p)
        if gi and mq:
            print(f"  [OK]   {tuong_doi}  (gitignored + may quet da loai)")
        else:
            do.append((tuong_doi, gi, mq))

    if not do:
        print("\nRESULT: PASS")
        return 0

    print("\nRESULT: FAIL")
    print("Worktree nam TRONG kho ma chua du HAI dieu kien:")
    for tuong_doi, gi, mq in do:
        print(f"\n  {tuong_doi}")
        print(f"      gitignored        : {'CO' if gi else 'KHONG'}")
        print(f"      may quet da loai  : {'CO' if mq else 'KHONG'}")
        print("    SUA (chon mot):")
        print(f"      1. chuyen ra NGOAI kho:  git worktree move {tuong_doi} "
              f"D:/LTTSTUDIOSAPP-{Path(tuong_doi).name}")
        print(f"      2. go han (cay phai SACH): git worktree remove {tuong_doi}")
        if not gi:
            print("      3. hoac them vao .gitignore VA vao EXCLUDED_DIRS cua "
                  "tools/scan_source_secrets.py — CA HAI, khong mot ve")
    print("\n⭐ Vi sao can CA HAI ve: cong cu ton trong gitignore (ruff) tu bo")
    print("   thu muc gitignored; cong cu quet he tep (may quet bi mat) thi")
    print("   KHONG — no chi bo thu duoc liet ke tuong minh.")
    print("⛔ Tep nay khong xoa gi: mot worktree co the dang mang viec chua")
    print("   commit cua phien khac. `git worktree remove` tu choi khi cay con")
    print("   thay doi; `rm -rf` thi MAT.")
    return 1


if __name__ == "__main__":
    # ⭐ Tac dung phu thuoc ve DIEM VAO, khong ve `main()`: mot bai test
    #    goi `main()` truc tiep se bi doi `sys.stdout`, va pytest dong
    #    buffer => `ValueError: I/O operation on closed file`. Da can
    #    that o CA HAI tep nay, o hai tang khac nhau (import, roi main).
    _stdout_utf8()
    raise SystemExit(main())
