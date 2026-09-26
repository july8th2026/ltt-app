"""Bánh cóc cho `tools/cay_gate.py` — cây gate phải nằm NGOÀI kho và SẠCH.

## Vì sao tồn tại

Cây chính bị va **sáu lần trong hai ngày** (25–26/09/2026), trên **bốn chiều
độc lập**: nội dung cây · sổ ref · HEAD/nhánh · index. `cay_gate.py` chọn cách
**xoá** tranh chấp (đo một bản sao `main` đã commit) thay vì **xếp hàng** nó.

⭐ Nhưng một công cụ *"đặt worktree ra ngoài kho"* mà tự đặt vào trong kho thì
   nó **sinh ra đúng cái bệnh nó chữa** — và đó là ca thật: `LTTGateBaseline68cde0`
   (25/09) thổi mọi mốc ruff gấp đôi và chặn commit của **mọi** phiên.

## Ba chỗ tiêm lỗi, mỗi chỗ từ một lần cắn thật

1. **đường dẫn nằm TRONG kho** ⇒ ca `LTTGateBaseline` ở trên.
2. **cây gate BẨN** ⇒ lượt gate 25/09 đo `main` **cộng 8 tệp chưa commit** của
   phiên khác. Nếu lượt ấy XANH thì còn tệ hơn: ⛔ không ai đi điều tra một
   lượt xanh.
3. **`chay` vẫn chạy gate khi biết trước sẽ FAIL** ⇒ đốt 20+ phút để nói lại
   điều đã biết trong 3 giây, **và** ghi một phán quyết vào sổ *"một L3 mỗi
   nhánh"*.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONG_CU = ROOT / "tools" / "cay_gate.py"


def _nap():
    spec = importlib.util.spec_from_file_location("_cay_gate", CONG_CU)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_cong_cu_nap_duoc():
    assert CONG_CU.exists()
    _nap()


def test_hoi_goc_CAY_CHINH_khong_phai_cay_dang_chay():
    """Cùng tính chất `test_4108` chốt: gốc phải là gốc `.git` **CHUNG**.

    🔴 Bản đầu của `check_worktree_trong_kho.py` dùng `ROOT` và **PASS sai** khi
       gọi từ worktree riêng. Tệp này chạy **chính từ một worktree riêng**, nên
       phép dưới đây là phép thật, ⛔ không phải phép trên giấy.
    """
    m = _nap()
    goc = m.goc_cay_chinh()
    assert (goc / ".git").is_dir(), (
        f"{goc} khong phai goc cay chinh (.git phai la THU MUC o cay chinh)")


def test_duong_dan_cay_gate_nam_NGOAI_kho():
    """⭐ Chốt **tính chất** (ngoài kho), ⛔ không chốt chuỗi đường dẫn.

    Chốt `"D:/LTTSTUDIOSAPP-cay-gate"` sẽ đỏ oan ngày kho được clone chỗ khác,
    mà vẫn ⛔ không bắt được ca một hậu tố mới vô tình trỏ vào trong kho.
    """
    m = _nap()
    goc, cay = m.goc_cay_chinh(), m.duong_dan_cay_gate()
    with pytest.raises(ValueError):
        cay.resolve().relative_to(goc)


def test_TIEM_LOI_duong_dan_TRONG_kho_thi_TU_CHOI(monkeypatch):
    """🔴 Ca `LTTGateBaseline68cde0`: worktree trong kho làm `find . -name "*.py"`
    nhảy 4778 → 7241 và **mọi** mốc ruff đúng gấp đôi.

    Nếu ô này xanh thì `cay_gate.py` là **cái máy sản xuất** ca ấy.

    ⛔ Mọi lệnh git **GHI** bị chặn: tiêm vào **quyết định**, ⛔ KHÔNG vào hệ
       tệp. (Lệnh **đọc** vẫn đi qua — `goc_cay_chinh()` cần `rev-parse`, nên
       bịt sạch `_git` sẽ hỏng chính phép đo: nó `SystemExit` vì lý do khác.)
       🔴 Bản đầu của phép này ⛔ không chặn, và khi tôi tháo lớp bảo vệ để chứng
       minh bánh cóc cắn được thì nó **dựng một worktree thật trong cây chính** —
       đúng cái bệnh đang đo. `check_worktree_trong_kho.py` bắt được nó, nên hai
       công cụ có che nhau; nhưng một phép kiểm ⛔ không được trả giá bằng cây
       mà phiên khác đang dùng. (Bài học này `test_4108` đã viết ra; tôi vi phạm
       nó ở đúng tệp số kế tiếp.)
    """
    m = _nap()
    trong = m.goc_cay_chinh() / "cay_gate_gia_de_tiem_loi"
    monkeypatch.setattr(m, "duong_dan_cay_gate", lambda: trong)

    that, ghi = m._git, []

    def _git_chan_lenh_GHI(*args, cwd=None):
        if args and args[0] in {"worktree", "checkout"}:
            ghi.append(args)
            raise AssertionError(f"lenh GHI trong phep tiem loi: {args}")
        return that(*args, cwd=cwd)

    monkeypatch.setattr(m, "_git", _git_chan_lenh_GHI)
    with pytest.raises(SystemExit) as e:
        m.chuan_bi()
    assert "TRONG kho" in str(e.value)
    assert ghi == [], "phai tu choi TRUOC khi git GHI bat cu gi"
    assert not trong.exists(), "tu choi roi ma van tao thu muc"


def test_TIEM_LOI_cay_gate_BAN_thi_TU_CHOI_lam_moi(monkeypatch, tmp_path):
    """🔴 Lượt gate 25/09 đo `main` **cộng** tệp chưa commit của phiên khác.

    ⭐ Một cây **đo** phải SẠCH: nếu không, phán quyết lại nói về *"`main` cộng
       một thứ gì đó"* — đúng cái bệnh cây gate sinh ra để chữa.
    """
    m = _nap()
    gia = tmp_path / "cay-gate"
    gia.mkdir()
    monkeypatch.setattr(m, "duong_dan_cay_gate", lambda: gia)
    monkeypatch.setattr(m, "_la_worktree_dang_ky", lambda p: True)
    monkeypatch.setattr(m, "_sha_main", lambda: "0" * 40)

    goi = []

    def _git_gia(*args, cwd=None):
        goi.append(args)
        ra = subprocess.CompletedProcess(args, 0, " M mot/tep/cua/phien/khac.py\n", "")
        return ra

    monkeypatch.setattr(m, "_git", _git_gia)
    with pytest.raises(SystemExit) as e:
        m.chuan_bi()
    assert "chua commit" in str(e.value)
    assert not any("checkout" in a for g in goi for a in g), (
        "cay ban ma van `checkout --detach` — mat thay doi cua phien khac")


def test_TIEM_LOI_chay_KHONG_goi_gate_khi_thieu_node_modules(monkeypatch, tmp_path):
    """⛔ Biết trước sẽ FAIL thì ⛔ đừng đốt 20+ phút để nói lại.

    ⭐ Và chốt **hành vi** (gate ⛔ không được gọi), ⛔ không chốt thông điệp:
       thông điệp là chữ hiển thị, còn *"có gọi gate hay không"* là thứ tốn tiền.
    """
    m = _nap()
    monkeypatch.setattr(m, "chuan_bi", lambda: tmp_path)
    monkeypatch.setattr(m, "dong_bo_npm", lambda cay, *, cai: 1)

    da_goi = []
    monkeypatch.setattr(m.subprocess, "run",
                        lambda *a, **k: da_goi.append(a) or
                        subprocess.CompletedProcess(a, 0))
    assert m.main(["chay"]) == 1
    assert da_goi == [], f"van goi gate du biet se FAIL: {da_goi}"


def test_npm_ci_phai_GIU_KHOA_may_khong_goi_npm_tran(monkeypatch, tmp_path):
    """`npm ci` là **lệnh nặng**: luật máy đòi đúng MỘT lượt nặng mỗi lúc.

    🔴 Bản đầu của phép này chốt `"chay_nang.py" in van` — **chốt cách gõ, ⛔ không
       chốt tính chất**, đúng cái bẫy `banh-coc-do-cach-go` đã ghi. Và nó **xanh**
       trong khi mã **hỏng thật**: `chay_nang.py` ⛔ không nằm trong kho (nó ở
       `~/.claude/ltt/`), nên lần chạy thật đầu tiên chết `[Errno 2]`. Một phép
       kiểm chốt sự có mặt của một **chuỗi** ⛔ không biết gì về việc tệp ấy có
       tồn tại hay không.

    ⭐ Tính chất thật: `npm` ⛔ không được gọi khi ⛔ chưa giữ khoá máy.
    """
    m = _nap()
    (tmp_path / "goi").mkdir()

    thu_tu: list[str] = []
    giu = False
    lan = []

    def _thieu_gia(cay):
        # lan 1 = truoc khi cai (con thieu) · lan 2 = kiem lai sau khi cai (du)
        lan.append(1)
        return ["goi"] if len(lan) == 1 else []

    monkeypatch.setattr(m, "thu_muc_npm_thieu", _thieu_gia)

    class _KhoaGia:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            nonlocal giu
            giu = True
            thu_tu.append("giu-khoa")
            return self

        def __exit__(self, *a):
            nonlocal giu
            giu = False
            thu_tu.append("nha-khoa")
            return False

    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    import cua_so_yen  # type: ignore[import-not-found]
    monkeypatch.setattr(cua_so_yen, "CuaSoYen", _KhoaGia)

    def _run_gia(cmd, **k):
        assert giu, f"⛔ goi {cmd} khi CHUA giu khoa may"
        thu_tu.append("npm")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(m.subprocess, "run", _run_gia)
    assert m.dong_bo_npm(tmp_path, cai=True) == 0
    assert thu_tu == ["giu-khoa", "npm", "nha-khoa"], thu_tu


def test_cua_so_yen_la_nguon_TRONG_kho():
    """⭐ Công cụ **trong** kho ⛔ không được phụ thuộc đường dẫn **ngoài** kho.

    🔴 Ca thật ở trên: `chay_nang.py` sống ở `~/.claude/ltt/` — cấu hình **cá
       nhân** của một máy. Nó sẽ hỏng ở mọi máy khác, và hỏng **im lặng** nếu
       nơi đó tình cờ có một tệp cùng tên.
    """
    assert (ROOT / "tools" / "cua_so_yen.py").exists()
    van = CONG_CU.read_text(encoding="utf-8")
    assert "from cua_so_yen import CuaSoYen" in van

    # 🔴 Ban dau chia van ban theo `\"\"\"` de bo docstring — va no dem ca CHU
    #    THICH, nen do oan vi mot dong ke lai lich su. Doc AST thi chu thich
    #    khong ton tai, con chuoi va ten thi co: dung kenh tra loi duoc cau
    #    *"ma CO CHAY dung toi no khong"*.
    import ast
    cay = ast.parse(van)
    goi_toi = [n for n in ast.walk(cay)
               if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and "chay_nang" in n.value)
               or (isinstance(n, ast.Name) and "chay_nang" in n.id)
               or (isinstance(n, ast.Attribute) and "chay_nang" in n.attr)]
    # Docstring cua module duoc ke lich su => loai dung no, khong loai ca ho.
    ds = ast.get_docstring(cay) or ""
    goi_toi = [n for n in goi_toi
               if not (isinstance(n, ast.Constant) and n.value == ds)]
    assert goi_toi == [], (
        f"ma con dung toi `chay_nang` o dong {[n.lineno for n in goi_toi]} — "
        "no khong co trong kho, no o `~/.claude/ltt/`")


def test_dong_bo_npm_TON_TRONG_mien_tru_CHUA_CAI_cua_bo_do_goc(monkeypatch):
    """⭐ Một luật, một nguồn: `CHUA_CAI` sống ở `check_phu_thuoc_npm.py`.

    🔴 Nếu `cay_gate.py` chép lại danh sách ấy thì hai bản sẽ trôi khỏi nhau —
       và kho này đã mất nhiều buổi cho đúng khuôn *"hai chỗ khai cùng một điều,
       ⛔ không ai bắt khớp"*.
    """
    m = _nap()
    goc = m._nap_bo_do_npm()
    assert goc.CHUA_CAI, "bo do goc khong con mien tru nao — phep nay do tap RONG"
    # ⭐ Hỏi tính chất: mọi mục được miễn ở bộ đo gốc ⛔ không bao giờ bị
    #    `cay_gate` báo thiếu — kể cả khi `_thieu` nói CÓ thiếu.
    monkeypatch.setattr(m, "_nap_bo_do_npm", lambda: goc)
    monkeypatch.setattr(goc, "_thu_muc_co_lock", lambda: sorted(goc.CHUA_CAI))
    monkeypatch.setattr(goc, "_thieu", lambda d, npm: ["missing: bat-ky-goi-nao"])
    assert m.thu_muc_npm_thieu(Path(".")) == []


def test_HAI_cong_cu_KHOP_nhau_cay_gate_khong_bi_4108_bao_do():
    """⭐ Bất biến ở BIÊN giữa hai công cụ cùng nói về worktree.

    `check_worktree_trong_kho.py` FAIL mọi worktree trong kho chưa đủ hai vế;
    `cay_gate.py` dựng một worktree. Nếu chỗ nó dựng bị công cụ kia bắt thì ta
    có hai luật đánh nhau — và người đọc gate sẽ tắt một trong hai.
    """
    m = _nap()
    spec = importlib.util.spec_from_file_location(
        "_kiem_wt", ROOT / "tools" / "check_worktree_trong_kho.py")
    k = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(k)
    assert m.duong_dan_cay_gate().resolve() not in [
        p.resolve() for p in k.worktree_trong_kho()]


def test_cay_gate_THAT_neu_da_dung_thi_phai_DETACH():
    """Nếu cây gate đã tồn tại trên máy này thì nó ⛔ không được giữ nhánh `main`.

    ⭐ Vì sao `--detach`: git ⛔ không cho hai worktree giữ cùng một nhánh, nên
       một cây gate *sở hữu* `main` sẽ chặn cây chính checkout `main` — biến
       công cụ giảm tranh chấp thành công cụ tạo tranh chấp.
    """
    m = _nap()
    cay = m.duong_dan_cay_gate()
    if not cay.exists():
        pytest.skip("cay gate chua dung tren may nay")
    ra = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=cay,
                        capture_output=True, text=True)
    assert ra.returncode != 0, f"cay gate dang giu nhanh {ra.stdout.strip()}"
