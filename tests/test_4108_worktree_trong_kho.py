"""Bánh cóc cho `tools/check_worktree_trong_kho.py`.

## Vì sao nó tồn tại

25/09: một worktree `LTTGateBaseline68cde0` đặt **trong** kho làm `find . -name
"*.py"` nhảy **4778 → 7241**, mọi mốc ruff **đúng gấp đôi**, và **chặn commit
của mọi phiên**. Hai lần trong hai ngày (`.codex/worktrees` là lần trước).

## ⛔ Vì sao tệp này KHÔNG dựng worktree thật để tiêm lỗi

Dựng một worktree trong cây chính — dù chỉ vài giây — là làm bẩn đúng cái cây
mà phiên khác có thể đang chạy gate trên đó. ⇒ Tiêm vào **quyết định**
(`_quyet_dinh`) thay vì vào **hệ tệp**: cùng chứng minh được điều cần chứng
minh, ⛔ không trả giá bằng một lượt gate của người khác.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONG_CU = ROOT / "tools" / "check_worktree_trong_kho.py"


def _nap():
    spec = importlib.util.spec_from_file_location("_kiem_wt", CONG_CU)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_cong_cu_nap_duoc():
    assert CONG_CU.exists()
    _nap()


def test_gate_CO_goi_cong_cu_nay():
    """⛔ Một bộ đo không ai gọi thì không canh gì cả. Chốt bằng ĐƯỜNG DẪN tệp,
    ⛔ không bằng tên bước (tên bước là chữ hiển thị, đổi được tự do)."""
    van = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "tools/check_worktree_trong_kho.py" in van


def test_hoi_goc_CAY_CHINH_khong_phai_cay_dang_chay():
    """🔴 Bản đầu dùng `ROOT` (cây đang chạy lệnh) ⇒ **PASS sai** khi gọi từ một
    worktree riêng: worktree của cây chính nằm ngoài `ROOT` nên bị bỏ qua.

    ⭐ Chốt **tính chất**: gốc mà công cụ hỏi phải là gốc của `.git` CHUNG, tức
       nó ⛔ không phụ thuộc cây nào đang chạy — kể cả khi bài này chạy từ một
       worktree riêng.
    """
    m = _nap()
    goc = m.goc_cay_chinh()
    assert (goc / ".git").is_dir(), (
        f"{goc} khong phai goc cay chinh (.git phai la THU MUC o cay chinh, "
        "la TEP o worktree rieng)")


@pytest.mark.parametrize("gitignored,may_quet_loai,mong_doi_do", [
    (True, True, False),     # đủ hai vế  -> chấp nhận
    (True, False, True),     # gitignored nhưng máy quét vẫn quét -> ĐỎ
    (False, True, True),     # máy quét loại nhưng ruff vẫn đếm  -> ĐỎ
    (False, False, True),    # ca `LTTGateBaseline` 25/09        -> ĐỎ
])
def test_TIEM_LOI_can_CA_HAI_ve(gitignored, may_quet_loai, mong_doi_do, monkeypatch):
    """⭐ Bốn ô của bảng chân lý, và ba trong bốn phải ĐỎ.

    Đây là chỗ tệp này kiếm được tiền: luật *"cứ gitignore là xong"* sẽ làm ô
    thứ hai **xanh** — và ô ấy đúng là ca `.codex`/máy quét bí mật, nơi một
    công cụ **quét hệ tệp** vẫn nhìn thấy cây chép.
    """
    m = _nap()
    gia = m.goc_cay_chinh() / "cay_gia_de_tiem_loi"
    monkeypatch.setattr(m, "worktree_trong_kho", lambda: [gia])
    monkeypatch.setattr(m, "_bi_gitignore", lambda p: gitignored)
    monkeypatch.setattr(m, "_may_quet_co_loai", lambda p: may_quet_loai)
    ma = m.main()
    assert (ma != 0) is mong_doi_do, (
        f"gitignored={gitignored} may_quet={may_quet_loai} => ma thoat {ma}")


def test_khong_co_worktree_trong_kho_thi_PASS(monkeypatch):
    """Đối chứng chiều ngược: tập rỗng phải PASS, ⛔ không FAIL oan."""
    m = _nap()
    monkeypatch.setattr(m, "worktree_trong_kho", lambda: [])
    assert m.main() == 0


def test_chay_that_tren_kho_nay_PASS_hoac_noi_ro_cach_sua(capsys):
    """Chạy thật. ⛔ Không đòi PASS mù: nếu ĐỎ thì thông điệp **phải** kèm lệnh
    `git worktree move`/`remove` — vì cái đã tốn của mọi phiên hôm qua ⛔ không
    phải việc không phát hiện, mà là ⛔ không ai biết phải làm gì."""
    m = _nap()
    ma = m.main()
    ra = capsys.readouterr().out
    assert "RESULT:" in ra
    if ma != 0:
        assert "git worktree move" in ra and "git worktree remove" in ra
