r"""Phụ thuộc npm đã KHAI có thật sự ĐƯỢC CÀI ở cây này chưa.

## Vì sao tệp này tồn tại — sáu lần trong một ngày

25/09/2026, cùng một câu hỏi cắn sáu lần:

    pywin32  ->  connector node_modules  ->  isolated-vm  ->  lược đồ CSDL
             ->  jsondiffpatch  ->  phân loại lưu trữ + bản dịch

Mỗi lần: **thứ này chạy được ở đây vì ở đây nó dựng từ một NGUỒN KHÁC với
production.** Lần đầu làm **production sập 7 phút** (`pywin32` chưa khai). Lần
sau nhẹ hơn, nhưng vẫn mất một lượt gate 21,8 phút.

Phần *Python* đã có người canh: `requirements*.txt` + `test_62` (cận trên) +
venv sạch của trình cài. Phần *lược đồ CSDL* cũng có: `do_migration_tren_postgres.py`.
⛔ Phần **npm** thì chưa ai canh — và nó là ba trong sáu ca.

## Câu hỏi ĐÚNG là gì

🔴 ⛔ **KHÔNG phải** *"thư mục `node_modules` có tồn tại không"*. Đo 25/09:
`frontend/chatltt` **CÓ** `node_modules` mà vẫn thiếu **34** phụ thuộc — đúng
hình dạng ca `jsondiffpatch` (gói mới thêm vào `package.json`, `node_modules`
cũ hơn khai báo).

⭐ Câu đúng là *"`npm ls` nói bản cài đã đủ chưa"*, và ta **hỏi chính npm**
thay vì tự viết bộ giải phụ thuộc thứ hai.

## Phạm vi — và vì sao hẹp đúng chừng này

Chỉ xét thư mục có **`package-lock.json` được git theo dõi**: không lock thì
⛔ không có "bản cài đúng" để đối chiếu (`spike/egress` là ví dụ — một spike,
⛔ không phải đích tái lập). Danh sách tệp lấy từ `git ls-files`, ⛔ không từ
`glob`: `glob` sẽ quét cả `node_modules` của chính nó và cả cây tạm của phiên
khác nằm trong kho.
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stdout_utf8() -> None:
    """Console Windows mặc định là cp1252 và ⛔ không mã hoá được `⭐`/`⛔`.

    🔴 Không có hàm này thì đúng **nhánh FAIL** sẽ sập lúc in — tức phép kiểm
       phát hiện được lỗi rồi chết trước khi nói ra. Đo 25/09: phép tiêm lỗi
       đầu tiên của chính tệp này chết đúng như vậy, và cùng tối đó một lượt
       xác minh model cũng mất bằng chứng vì cùng lý do.

    ⚠️ Gọi trong `main()`, ⛔ **KHÔNG ở mức module**. Bản đầu của tệp này bọc
       `sys.stdout` ngay khi import ⇒ mọi tệp test import nó đều bị đổi stdout,
       và pytest đóng buffer ⇒ `ValueError: I/O operation on closed file`.
       ⭐ Cùng họ với tác dụng phụ lúc import mà `poll_connector` vừa bị sửa
       (`test_4290`): thứ gì đổi trạng thái toàn cục thì thuộc về **điểm vào**,
       ⛔ không thuộc về câu lệnh `import`.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)

#: Thư mục ĐÃ KHAI mà hôm nay **chưa** được cài ở cây này.
#:
#: ⛔ **Tập này chỉ được phép CO LẠI.** Cùng khuôn `MIEN_TRU_SLUG` của
#:    `test_60` và `MOC_DUONG_CHET` của `test_3521`: ai cài được một thư mục
#:    thì xoá nó khỏi đây, và lần xoá ấy hiện ra trong diff cho người review.
#:
#: ⚠️ Ba thư mục dưới đây **đúng là ba bước mà `gate.py` đang `BOQUA`**
#:    (*"3 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: frontend autosub-studio,
#:    frontend prompt-ai-ommi, frontend chatltt"*). Nên chúng ⛔ không phải một
#:    phát hiện mới — tệp này chỉ làm điều đang ngầm thành điều **khai ra**.
CHUA_CAI = frozenset({
    "frontend/autosub-studio",
    "frontend/chatltt",
    # ⭐ 28/09: `frontend/prompt-ai-ommi` DA RA khoi tap nay. Pha 3 cua PROMPT
    #    AI dung frontend that o do (`StudioShell`/`BriefPane`), nen no da duoc
    #    `npm ci` + `npm run build` chay that va bo kiem tu bao "co lai duoc".
    #    Do la dung luat mot chieu cua tap nay, va no bo bot MOT buoc gate dang
    #    bi `BOQUA` => do phu tang, khong giam.
    # ⚠️ Cay nao chua cai thi bo kiem se DO va in san `cd frontend/prompt-ai-ommi
    #    && npm ci`. Do la y muon: mot buoc bi bo qua im lang te hon mot buoc do
    #    kem lenh sua.
})


def _thu_muc_co_lock() -> list[str]:
    """Thư mục có CẢ `package.json` và `package-lock.json` **được git theo dõi**."""
    ra = subprocess.run(["git", "ls-files", "*package-lock.json"],
                        cwd=ROOT, capture_output=True, text=True)
    thu_muc = []
    for dong in ra.stdout.splitlines():
        d = str(Path(dong).parent).replace("\\", "/")
        if d == ".":
            d = ""
        if (ROOT / d / "package.json").exists():
            thu_muc.append(d)
    return sorted(set(thu_muc))


def _thieu(d: str, npm: str) -> list[str]:
    """Danh sách gói `npm ls` báo thiếu/sai ở thư mục `d`.

    ⭐ Hỏi npm bằng `--json` rồi đọc `problems`, ⛔ không grep văn bản: văn bản
       của npm đổi theo phiên bản và theo ngôn ngữ, `problems` thì không.
    """
    ra = subprocess.run([npm, "ls", "--depth=0", "--json"],
                        cwd=ROOT / d, capture_output=True, text=True)
    try:
        d_json = json.loads(ra.stdout or "{}")
    except json.JSONDecodeError:
        # ⛔ Không nuốt: npm không trả JSON đọc được là một câu trả lời ta
        #    KHÔNG có, khác hẳn "không thiếu gì".
        return [f"<khong doc duoc dau ra npm ls: {(ra.stderr or '')[:200]}>"]
    van_de = list(d_json.get("problems") or [])
    for ten, chi_tiet in (d_json.get("dependencies") or {}).items():
        if isinstance(chi_tiet, dict) and chi_tiet.get("missing"):
            van_de.append(f"missing: {ten}")
    return van_de


def main() -> int:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        print("npm khong co tren PATH — bo qua phep kiem nay.")
        print("⚠️ Day KHONG phai mot lan PASS: no la mot cau hoi chua duoc hoi.")
        return 0

    thu_muc = _thu_muc_co_lock()
    if not thu_muc:
        print("RESULT: FAIL")
        print("Khong tim thay thu muc nao co `package-lock.json` duoc git theo "
              "doi — phep kiem nay dang do mot tap RONG, tuc no khong canh gi.")
        return 1

    do, da_cai_roi = [], []
    for d in thu_muc:
        van_de = _thieu(d, npm)
        nhan = d or "<goc kho>"
        if van_de:
            if d in CHUA_CAI:
                print(f"  [MOC]  {nhan}: thieu {len(van_de)} goi (da khai o `CHUA_CAI`)")
            else:
                do.append((d, van_de))
        else:
            print(f"  [OK]   {nhan}")
            if d in CHUA_CAI:
                da_cai_roi.append(d)

    if do:
        print("\nRESULT: FAIL")
        print("Phu thuoc npm DA KHAI ma CHUA duoc cai o cay nay:")
        for d, van_de in do:
            print(f"\n  {d or '<goc kho>'} — {len(van_de)} van de:")
            for v in van_de[:6]:
                print(f"      {v}")
            if len(van_de) > 6:
                print(f"      ... va {len(van_de) - 6} nua")
            print(f"    SUA: cd {d} && npm ci")
        print("\n⭐ `node_modules` TON TAI khong co nghia la du: mot goi vua")
        print("   duoc them vao `package.json` thi ban cai cu van thieu no.")
        return 1

    if da_cai_roi:
        print("\nRESULT: FAIL")
        print("`CHUA_CAI` con giu thu DA cai duoc — banh coc phai CO LAI:")
        for d in da_cai_roi:
            print(f"    xoa {d!r} khoi CHUA_CAI trong tools/check_phu_thuoc_npm.py")
        return 1

    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    # ⭐ Tac dung phu thuoc ve DIEM VAO, khong ve `main()`: mot bai test
    #    goi `main()` truc tiep se bi doi `sys.stdout`, va pytest dong
    #    buffer => `ValueError: I/O operation on closed file`. Da can
    #    that o CA HAI tep nay, o hai tang khac nhau (import, roi main).
    _stdout_utf8()
    raise SystemExit(main())
