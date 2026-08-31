"""test_362 — cây riêng cho mỗi phiên, và chốt chặn deploy nhầm cây.

Ba phiên cùng ghi một cây làm mọi lượt `gate.py` cho **đỏ giả**. Cách sửa là cho
mỗi phiên một `git worktree` riêng — nhưng cách sửa ấy **tự sinh ra một mối nguy
lớn hơn thứ nó chữa**:

🔴 Máy này LÀ production, và `setup\\2-cai-dat.ps1` chép **cả cây** sang
   `C:\\LTTPlatform`. Nhiều cây riêng nghĩa là nhiều thư mục trông giống hệt
   nhau, và deploy nhầm một trong số đó là lỗi **im lặng**: script chạy xong,
   báo thành công, và production chạy một nhánh không ai định phát hành.

⇒ Nên phần lớn tệp này canh cái chốt chặn, không canh tiện ích tạo cây.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
CAI_DAT = GOC / "setup" / "2-cai-dat.ps1"
sys.path.insert(0, str(GOC / "tools"))

import cay_rieng  # noqa: E402


def _cay_lien_ket() -> list[Path]:
    """Các worktree liên kết đang có thật trên máy."""
    ra = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=str(GOC),
                        capture_output=True, text=True, encoding="utf-8")
    duong = [Path(d[9:]) for d in ra.stdout.splitlines() if d.startswith("worktree ")]
    return [p for p in duong if p.resolve() != GOC.resolve() and p.exists()]


# ── 1. Tiền đề mà chốt chặn dựa vào ────────────────────────────────────────

def test_cay_chinh_co_dot_git_la_THU_MUC():
    assert (GOC / ".git").is_dir(), (
        "chot chan phan biet cay chinh/cay lien ket bang chinh dieu nay")
    assert cay_rieng.la_cay_chinh() is True


@pytest.mark.parametrize("lien_ket", _cay_lien_ket() or [None])
def test_cay_lien_ket_co_dot_git_la_TEP(lien_ket):
    """⛔ Đây là tiền đề, không phải chi tiết cài đặt.

    Nếu git đổi cách này thì chốt chặn im lặng thôi chặn — và triệu chứng sẽ là
    một lần deploy nhầm, không phải một dòng đỏ. Nên đo trên **cây thật** đang
    có trên máy chứ không dựng cây giả.
    """
    if lien_ket is None:
        pytest.skip("khong co cay lien ket nao tren may de do")
    dot = lien_ket / ".git"
    assert dot.exists() and dot.is_file(), (
        f"{lien_ket}: `.git` phai la TEP thi chot chan moi nhan ra cay lien ket")
    assert cay_rieng.la_cay_chinh(lien_ket) is False


# ── 2. Chốt chặn phải CÓ MẶT trong script cài đặt ─────────────────────────

def test_script_cai_dat_CO_chot_chan_cay_rieng():
    """Bánh cóc: gỡ chốt này ra là mở lại đúng cái bẫy nó sinh ra để chặn."""
    ma = CAI_DAT.read_text(encoding="utf-8")
    assert "CAY RIENG (git worktree)" in ma, "chot chan da bien mat khoi installer"
    assert "PathType Container" in ma, (
        "chot phai phan biet `.git` TEP vs THU MUC — day la ca phep thu")
    dong_chot = [d.strip() for d in ma.splitlines()
                 if "CAY RIENG (git worktree)" in d]
    assert dong_chot and dong_chot[0].startswith("throw"), (
        "phat hien ra ma khong DUNG lai thi khong phai mot chot chan; "
        f"thay: {dong_chot}")


def test_chot_dung_TRUOC_moi_thao_tac_ghi():
    """Chặn sau khi đã chép nửa cây sang production là chặn muộn."""
    ma = CAI_DAT.read_text(encoding="utf-8")
    vi_tri_chot = ma.index("CAY RIENG (git worktree)")
    for ghi in ("Copy-Item", "New-Item", "nssm"):
        if ghi in ma:
            assert vi_tri_chot < ma.index(ghi), (
                f"chot chan nam SAU `{ghi}` — luc do da ghi vao production roi")


def test_khong_co_dot_git_thi_CHO_QUA():
    """Cài từ một bản chép thuần là đường hợp lệ, ghi rõ ở `.DESCRIPTION`.

    ⛔ Một chốt chặn quá tay ở đây sẽ chặn đúng cách cài mà tài liệu hướng dẫn.
    """
    ma = CAI_DAT.read_text(encoding="utf-8")
    dieu_kien = [d for d in ma.splitlines() if "PathType Container" in d][0]
    assert "Test-Path $gitPath) -and" in dieu_kien, (
        "phai co ve `(Test-Path $gitPath) -and ...`, neu khong thi cay khong co "
        "`.git` cung bi chan")


# ── 3. `cay_rieng.py` không được tự bắn vào chân ─────────────────────────

def test_tu_choi_tao_cay_khi_dang_o_trong_mot_cay_rieng():
    ma = (GOC / "tools" / "cay_rieng.py").read_text(encoding="utf-8")
    khuc = ma.split("def _tao(")[1].split("def _go(")[0]
    assert "la_cay_chinh()" in khuc and "SystemExit" in khuc, (
        "tao cay rieng TU trong mot cay rieng se long nhanh chong nhanh")


def test_go_cay_KHONG_dung_force():
    """`git worktree remove` từ chối khi cây còn việc chưa commit.

    Đó chính là thứ cần được từ chối — `--force` biến một lệnh dọn dẹp thành
    một lệnh mất việc, im lặng.
    """
    ma = (GOC / "tools" / "cay_rieng.py").read_text(encoding="utf-8")
    # ⛔ Bo chu thich TRUOC khi do. Ban dau phep kiem nay do ca van ban, nen no
    #    do vi dung cau giai thich VI SAO khong dung `--force` — tuc no phat
    #    hien duoc y dinh dung dan va goi do la vi pham.
    khuc = [d for d in ma.split("def _go(")[1].splitlines()
            if not d.strip().startswith("#")]
    assert not any("--force" in d for d in khuc)


def test_canh_bao_thay_doi_chua_commit_KHONG_di_theo():
    """Cái bẫy dễ mất việc nhất: `worktree add` phân nhánh từ một commit."""
    ma = (GOC / "tools" / "cay_rieng.py").read_text(encoding="utf-8")
    khuc = ma.split("def _tao(")[1].split("def _go(")[0]
    assert "_dang_do()" in khuc and "O LAI cay chinh" in khuc


# ── 4. Cửa sổ yên chỉ chặn thứ đáng chặn ────────────────────────────────

def test_chi_luot_DAY_DU_xep_hang():
    """`--quick`/`--vong-lap` mà phải đợi một lượt đầy đủ là giết vòng lặp ngắn.

    Cả hai chế độ ấy đã TỰ KHAI rằng chúng không phải bằng chứng, nên nhiễu
    trên phép đo của chúng ít quan trọng hơn hẳn.
    """
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "bat=not (args.quick or args.vong_lap or args.khong_khoa)" in ma


def test_gate_van_CHAY_khi_cho_qua_han():
    """Một cổng chất lượng từ chối chạy vì bận là một cổng không ai dùng."""
    import cua_so_yen

    khuc = cua_so_yen.CuaSoYen.__enter__.__doc__ or ""
    ma = (GOC / "tools" / "cua_so_yen.py").read_text(encoding="utf-8")
    than = ma.split("def __enter__")[1].split("def __exit__")[0]
    assert "return self" in than and "raise" not in than, (
        "cho qua han phai TRA VE (chay khong khoa), khong duoc nem loi")
    assert "KHONG CO KHOA" in than, "phai NOI RO rang luot nay co the bi nhieu"


def test_dong_RESULT_tu_khai_khi_cay_doi():
    """🔴 Dòng RESULT là thứ duy nhất được đọc khi người ta vội.

    Trước bản vá này, cây-đổi chỉ được nói trong một đoạn văn phía trên, còn
    dòng RESULT in **y hệt** một lượt sạch.
    """
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "KHONG DUNG LAM BANG CHUNG" in ma
    khoi = _khoi_sua_ket()
    assert any("cay_da_doi" in k for k in khoi), (
        "`cay_da_doi` phai dieu khien chinh bien `ket`, khong phai in roi bo. "
        f"Cac khoi co sua `ket`: {khoi}")


def _khoi_sua_ket() -> list[str]:
    """Mã nguồn của mọi khối `if` trong `main()` có **sửa biến `ket`**.

    🔴 VÌ SAO KHÔNG ĐẾM KÝ TỰ. Bản đầu của phép kiểm này cắt một cửa sổ 600 ký
       tự sau mốc `ket = "PASS" ...` rồi tìm chuỗi trong đó. Nó đỏ ngay khi có
       người **chèn một khối chú thích tử tế** vào giữa — hành vi đúng nguyên,
       chỉ là `cay_da_doi` bị đẩy ra ngoài cửa sổ.

    ⭐ Đó đúng lớp lỗi đã gặp nhiều lần trong ngày 31/08: **neo vào khoảng cách
       vật lý thay vì vào quan hệ.** Ý định thật là *"cờ này phải điều khiển
       chính biến `ket`"* — và đó là một quan hệ, hỏi cây cú pháp được.
    """
    import ast

    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(ma))
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    ra = []
    for n in ast.walk(ham):
        if not isinstance(n, ast.If):
            continue
        sua = any(
            (isinstance(x, ast.AugAssign) and isinstance(x.target, ast.Name)
             and x.target.id == "ket")
            or (isinstance(x, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ket" for t in x.targets))
            for x in ast.walk(n))
        if sua:
            ra.append(ast.unparse(n))
    return ra
