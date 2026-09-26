r"""Cây RIÊNG để chạy gate — ghim ở `main`, đặt NGOÀI kho.

    python tools/cay_gate.py chuan-bi          # dung/lam moi cay gate
    python tools/cay_gate.py chay              # chuan bi roi chay gate trong do
    python tools/cay_gate.py chay --pham-vi core:wf_dong_co
    python tools/cay_gate.py duong-dan         # in duong dan roi thoat

## Vì sao tồn tại — sáu lần va chạm cây chính trong hai ngày

Cây chính là **một tài nguyên chia sẻ có NHIỀU CHIỀU độc lập**, và mỗi chiều vỡ
một cách khác (đo 25–26/09/2026, ba phiên):

| chiều | đã vỡ thế nào |
|---|---|
| nội dung cây | gate bị vô hiệu vì có người `merge` giữa lượt (**×2**) |
| sổ ref | `git commit` chết: `cannot lock ref 'HEAD'` |
| HEAD/nhánh | một lượt gộp **mang theo** commit của phiên thứ ba |
| HEAD/nhánh | một commit **đi lạc nhánh** — đúng nội dung, sai nhánh, **⛔ không ai thấy** |
| index | một lượt gộp bị chặn bởi tệp **đang staged** của phiên khác |

## ⭐ Vì sao KHÔNG dùng một khoá `cay_chinh`

Một khoá chỉ **xếp hàng** sự tranh chấp; cây riêng **xoá** nó:

1. Gộp và gate **chạy song song** — ⛔ không ai chờ ai. Với khoá, một lượt gate
   22 phút chặn một `git merge` 3 giây.
2. 🔑 Nó đo **`main` ĐÃ COMMIT** ⇒ miễn nhiễm với **cả hai** thứ từng làm bẩn
   phán quyết: người khác gộp giữa lượt, **và** tệp chưa commit của người khác
   nằm trong cây. Lượt gate 25/09 đo `main` **cộng 8 tệp chưa commit** của một
   phiên khác — và nếu nó XANH thì còn tệ hơn, vì ⛔ không ai đi điều tra một
   lượt xanh.
3. ⛔ Không cơ chế mới: chỉ `git worktree` + `checkout --detach`.

⚠️ Phản biện đã xét và bỏ: *"một bản sao không phải `main`"*. Một cây **sạch** ở
   **đúng commit** của `main` là **byte-identical** cho mọi tệp đã commit; khác
   biệt duy nhất là tệp **chưa** commit — thứ ta **muốn** loại.

## Ba ràng buộc, mỗi cái từ một lần va thật

- **NGOÀI kho.** Đặt trong kho thì nó vào tập quét của công cụ ⛔ không tôn
  trọng gitignore (`scan_source_secrets`) — và nếu ⛔ không gitignored thì cả
  ruff cũng đếm hai lần (`LTTGateBaseline68cde0`, 25/09: `F401 408→813`).
  `tools/check_worktree_trong_kho.py` canh đúng điều này.
- **`--detach`**, ⛔ không checkout nhánh `main`: git ⛔ không cho hai worktree
  giữ cùng một nhánh, và ta ⛔ không muốn cây này *sở hữu* `main`.
- **Đọc lại tip của `main` ở MỖI lượt.** ⛔ Không tin một ảnh chụp: một phiên
  khác vừa chứng minh rằng tin nhắn của họ về trạng thái cây đã **tự làm cũ**
  trên đường truyền.

## ⚠️ Cái giá đã ĐO được: cây mới ⛔ không có `node_modules`

Đo 26/09 ngay sau khi dựng: `connector_runner` thiếu **18** gói,
`frontend/agent-canvas` thiếu **30** — vì `node_modules` là **untracked**, nên
`git worktree add` ⛔ không mang nó theo. Bước gate `phu thuoc npm da cai`
FAIL, **và nó FAIL đúng**.

⭐ Đây hoá ra là **lãi**, ⛔ không phải lỗ: cây gate `npm ci` từ **đúng
`package-lock.json` đã commit** ⇒ nó đo được cả câu *"lock này có cài được
không"* — đúng hình dạng ca `isolated-vm` và `jsondiffpatch` đã cắn 25/09, nơi
cây phát triển chạy được vì `node_modules` của nó **cũ hơn** khai báo.

⚠️ Phương án đã xét và **bỏ**: junction `node_modules` từ cây chính sang. Nó
   phá đúng tính chất tệp này tồn tại để có — cây gate sẽ đo `node_modules`
   **của cây chính**, tức lại *"dựng từ một nguồn khác"*. Và nếu một phiên đang
   `npm ci` ở cây chính thì cây gate đọc một trạng thái nửa vời.

⛔ `npm ci` ⛔ KHÔNG chạy trong `chuan-bi` mặc định: nó là **lệnh nặng**, và
`chuan-bi` phải chạy được cả khi phiên khác đang giữ `cpu_nhieu`. Phải xin
tường minh: `chuan-bi --cai-npm`, và nó tự đi qua `chay_nang.py`.

## Python thì ⛔ không cần cài gì cả

Đo 26/09: `gate.py` ⛔ không tham chiếu `venv` ở đâu, và ta gọi nó bằng
`sys.executable` — interpreter **đang chạy** mang theo site-packages của chính
nó, ⛔ không phụ thuộc cây. Nên phần Python của gate chạy trong cây gate mà
⛔ không cần cài gì. (Đo, ⛔ không đoán: câu này đáng đúng một lệnh `grep`.)

## ⛔ Thứ tệp này KHÔNG làm

⛔ Không deploy. Luật kho: *"Deploy chỉ chạy từ cây chính"* — dấu vân tay bản
phát hành phải sinh từ đó, ⛔ không từ một cây đo.
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

TEN_HAU_TO = "-cay-gate"


def _stdout_utf8() -> None:
    """Console Windows là cp1252 và ⛔ không mã hoá được `⭐`/`⛔`.

    ⚠️ Gọi ở khối `__main__`, ⛔ KHÔNG trong `main()` và ⛔ KHÔNG ở mức module:
       cả hai chỗ kia đều đã cắn thật 26/09 (`ValueError: I/O operation on
       closed file` khi một bài test gọi `main()`, và khi một bài test import).
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def goc_cay_chinh() -> Path:
    """Gốc cây chính — từ `.git` CHUNG, nên đúng dù ta đứng ở worktree nào."""
    ra = _git("rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(ra.stdout.strip()).resolve().parent


def duong_dan_cay_gate() -> Path:
    goc = goc_cay_chinh()
    return goc.parent / (goc.name + TEN_HAU_TO)


def _sha_main() -> str:
    """SHA hiện tại của `main`. ⛔ Đọc lại mỗi lượt, ⛔ không nhớ."""
    ra = _git("rev-parse", "main", cwd=goc_cay_chinh())
    sha = ra.stdout.strip()
    if not sha:
        raise SystemExit(f"khong doc duoc `main`: {ra.stderr.strip()[:200]}")
    return sha


def _la_worktree_dang_ky(p: Path) -> bool:
    ra = _git("worktree", "list", "--porcelain", cwd=goc_cay_chinh())
    for dong in ra.stdout.splitlines():
        if dong.startswith("worktree "):
            if Path(dong[len("worktree "):].strip()).resolve() == p.resolve():
                return True
    return False


def chuan_bi() -> Path:
    """Dựng hoặc làm mới cây gate ở tip của `main`. Trả về đường dẫn."""
    goc = goc_cay_chinh()
    cay = duong_dan_cay_gate()

    # ⛔ Chan truoc: cay gate NAM TRONG kho la dung cai bay `check_worktree_trong_kho`
    #    sinh ra de bat. Kiem o day de loi hien luc TAO, khong doi tan luot gate.
    try:
        cay.resolve().relative_to(goc)
    except ValueError:
        pass
    else:
        raise SystemExit(f"⛔ cay gate {cay} nam TRONG kho {goc} — tu choi")

    sha = _sha_main()
    if not _la_worktree_dang_ky(cay):
        print(f"  [..] dung cay gate: {cay}")
        ra = _git("worktree", "add", "--detach", str(cay), sha, cwd=goc)
        if ra.returncode != 0:
            raise SystemExit(f"⛔ khong dung duoc: {ra.stderr.strip()[:400]}")
        print(f"  [OK] da dung, ghim {sha[:12]}")
        return cay

    ban = _git("status", "--porcelain", cwd=cay).stdout.strip()
    if ban:
        so = len(ban.splitlines())
        raise SystemExit(
            f"⛔ cay gate {cay} co {so} tep chua commit — TU CHOI lam moi.\n"
            "   Mot cay do phai SACH: neu khong, phan quyet lai noi ve `main`\n"
            "   CONG mot thu gi do, dung cai benh no sinh ra de chua.\n"
            f"   Xem: git -C {cay} status")
    ra = _git("checkout", "--detach", sha, cwd=cay)
    if ra.returncode != 0:
        raise SystemExit(f"⛔ khong ghim duoc {sha[:12]}: {ra.stderr.strip()[:400]}")
    print(f"  [OK] cay gate {cay} ghim {sha[:12]}")
    return cay


def _nap_bo_do_npm():
    """Nạp `tools/check_phu_thuoc_npm.py` — ⛔ KHÔNG chép lại luật của nó.

    ⭐ Thư mục nào có lock, gói nào coi là thiếu, thư mục nào đang được miễn
       (`CHUA_CAI`) — tất cả đã định nghĩa ở đó. Một bản sao thứ hai của luật
       sẽ trôi khỏi bản gốc, và kho này đã mất nhiều buổi cho đúng khuôn ấy.
    """
    import importlib.util
    duong = Path(__file__).resolve().parent / "check_phu_thuoc_npm.py"
    spec = importlib.util.spec_from_file_location("_bo_do_npm", duong)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def thu_muc_npm_thieu(cay: Path) -> list[str]:
    """Thư mục npm còn thiếu gói **trong cây `cay`**, bỏ các mục đã miễn trừ."""
    import shutil
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        print("  [!] npm khong co tren PATH - bo qua buoc dong bo npm.")
        print("      ⚠️ Day KHONG phai mot lan PASS: la mot cau hoi chua hoi.")
        return []
    m = _nap_bo_do_npm()
    goc_cu = m.ROOT
    try:
        m.ROOT = cay          # hoi ve CAY GATE, khong phai cay chua bo do
        return [d for d in m._thu_muc_co_lock()
                if d not in m.CHUA_CAI and m._thieu(d, npm)]
    finally:
        m.ROOT = goc_cu


def dong_bo_npm(cay: Path, *, cai: bool) -> int:
    """Kiểm (và nếu `cai` thì cài) `node_modules` trong cây gate."""
    thieu = thu_muc_npm_thieu(cay)
    if not thieu:
        print("  [OK] node_modules du o moi thu muc co lock")
        return 0
    if not cai:
        print(f"  [!] {len(thieu)} thu muc thieu node_modules: {', '.join(thieu)}")
        print("      => buoc gate `phu thuoc npm da cai` se FAIL, va FAIL DUNG.")
        print("      SUA: python tools/cay_gate.py chuan-bi --cai-npm")
        return 1

    # ⭐ `npm ci` la LENH NANG => di qua `chay_nang.py` de giu dung MOT luot
    #    nang moi luc tren ca may. ⛔ Dung goi `npm` truc tiep o day.
    chay_nang = Path(__file__).resolve().parent / "chay_nang.py"
    for d in thieu:
        print(f"\n  [..] npm ci trong {cay / d}")
        ra = subprocess.run([sys.executable, str(chay_nang), "--phien", "cay-gate",
                             "--", "npm", "ci"], cwd=cay / d)
        if ra.returncode != 0:
            print(f"  ⛔ `npm ci` that bai o {d} - ma thoat {ra.returncode}")
            return 1
    con = thu_muc_npm_thieu(cay)
    if con:
        print(f"  ⛔ van con thieu sau `npm ci`: {', '.join(con)}")
        return 1
    print("  [OK] da cai xong")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("lenh", choices=["chuan-bi", "chay", "duong-dan"])
    ap.add_argument("--cai-npm", action="store_true",
                    help="chay `npm ci` cho thu muc con thieu (LENH NANG)")
    a, con_lai = ap.parse_known_args(argv)

    if a.lenh == "duong-dan":
        print(duong_dan_cay_gate())
        return 0

    cay = chuan_bi()
    ma_npm = dong_bo_npm(cay, cai=a.cai_npm)
    if ma_npm != 0 and a.lenh == "chay":
        # ⛔ Khong chay gate khi da BIET no se FAIL vi thieu cai dat: mot luot
        #    gate 20+ phut de bao lai dieu ta vua biet trong 3 giay la lang phi,
        #    VA no ghi mot phan quyet vao so "mot L3 moi nhanh".
        print("\n⛔ Dung truoc khi chay gate: cay gate chua du node_modules.")
        return ma_npm
    if a.lenh == "chuan-bi":
        print(f"\n⭐ Chay gate trong do:  cd {cay} && python tools/gate.py")
        return ma_npm

    # ⭐ `gate.py` dung `ROOT = Path(__file__).parent.parent`, tuc no TU do cay
    #    no nam trong. Nen chay no o day la do cay gate — KHONG phai sua gate.py.
    print(f"\n=== chay gate trong {cay} ===")
    return subprocess.run([sys.executable, "tools/gate.py", *con_lai],
                          cwd=cay).returncode


if __name__ == "__main__":
    _stdout_utf8()
    raise SystemExit(main())
