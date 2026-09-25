"""Bánh cóc quét cả cây ⛔ không được đếm một CÂY KHÁC nằm lồng trong kho.

## Lớp lỗi này đã quay lại BỐN lần

`ruff.toml:46-50` đã ghi nó từ trước, kèm đúng chữ ký: *"`ruff check .` từ gốc sẽ
lún vào nó và đếm LẠI mọi .py → mọi số đếm TĂNG ĐÚNG GẤP 2 (F401 411->821)"*.
Thuốc hồi đó là loại trừ **một cái tên**: `.codex`.

Và nó quay lại, vì cái tên thì vô hạn còn tính chất thì chỉ có một:

| Ngày | Cây lồng trong kho | Ai tạo |
|---|---|---|
| ~06/09 | `.codex/worktrees/<task>/` | Codex CLI |
| 25/09 | `LTTGateBaseline68cde0/` | một phiên dựng mốc gate (chính tôi) |
| 25/09 | `LTTSTUDIOSAPP-n57/` | làn `phien/n57-may-trang-thai` |

Mỗi lần đều **chặn commit của MỌI phiên**, và mỗi lần đều mất thời gian của một
người đi tìm "mình đã thêm 405 lỗi F401 ở đâu".

## ⇒ Nêu TÍNH CHẤT, đừng liệt kê TÊN

Tính chất của thứ phải loại trừ ⛔ không phải *"nó tên là `.codex`"*. Nó là:

> **thư mục đó tự nó là một cây làm việc của git** — tức bên trong có `.git`.

Một cây như vậy ⛔ không thuộc cây này: tệp của nó `git ls-files` ở đây không
thấy, `git status` ở đây không báo, nên một phép đếm nói về "kho này" mà đếm nó
là đang đếm **hai kho**. Điều đó đúng với worktree, với bản `robocopy`, với một
`clone` để so sánh — mọi cách tạo ra, một luật.

⭐ Khuôn nên lặp lại: khi một luật loại trừ phải sửa lần thứ hai để thêm một
   cái tên, đó là dấu hiệu luật đang tả **ví dụ** chứ chưa tả **tính chất**.
"""
from __future__ import annotations

import pathlib

from tools import check_ruff


def _dung_cay(goc: pathlib.Path, ten: str, *, co_git: bool) -> pathlib.Path:
    thu_muc = goc / ten
    (thu_muc / "apps").mkdir(parents=True)
    (thu_muc / "apps" / "x.py").write_text("import os\n", encoding="utf-8")
    if co_git:
        # Worktree của git: `.git` là một TỆP trỏ tới thư mục thật.
        (thu_muc / ".git").write_text("gitdir: ../.git/worktrees/x\n",
                                      encoding="utf-8")
    return thu_muc


def test_tim_ra_worktree_long_nhau_du_ten_la_gi(tmp_path):
    """Tên không quan trọng — chỉ `.git` bên trong mới quan trọng."""
    for ten in ("LTTGateBaseline68cde0", "LTTSTUDIOSAPP-n57", "cay-tam-abc",
                "mot-ten-chua-ai-nghi-ra"):
        _dung_cay(tmp_path, ten, co_git=True)
    loai = set(check_ruff.cay_long_nhau(tmp_path))
    assert loai == {"LTTGateBaseline68cde0", "LTTSTUDIOSAPP-n57", "cay-tam-abc",
                    "mot-ten-chua-ai-nghi-ra"}


def test_thu_muc_thuong_KHONG_bi_loai(tmp_path):
    """⛔ Không được loại oan: `apps/`, `platform_core/` là cây này, phải đếm."""
    _dung_cay(tmp_path, "apps", co_git=False)
    _dung_cay(tmp_path, "platform_core", co_git=False)
    assert check_ruff.cay_long_nhau(tmp_path) == []


def test_git_la_THU_MUC_cung_tinh_la_mot_cay(tmp_path):
    """Bản `robocopy`/`clone` mang `.git` là một THƯ MỤC, không phải tệp."""
    thu_muc = tmp_path / "ban-chep"
    (thu_muc / ".git" / "objects").mkdir(parents=True)
    (thu_muc / "x.py").write_text("import os\n", encoding="utf-8")
    assert check_ruff.cay_long_nhau(tmp_path) == ["ban-chep"]


def test_KHONG_tu_loai_chinh_goc_dang_quet(tmp_path):
    """Gốc cũng có `.git` — loại nó thì bánh cóc không đếm gì cả và XANH VĨNH VIỄN."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "x.py").write_text("import os\n", encoding="utf-8")
    assert check_ruff.cay_long_nhau(tmp_path) == []


def test_quet_TRUYEN_cac_cay_do_cho_ruff(tmp_path, monkeypatch):
    """Tìm ra thì phải dùng — phép kiểm này chốt chỗ nối, không chỉ chỗ tìm.

    🔴 Đúng hình dạng của một lỗi đã gặp thật hôm nay: hàm tìm được câu trả lời
       đúng nhưng người gọi không hỏi nó (`client=None` gặp cửa `if client is
       None: return 0`), nên cả vòng là mã chết mà mọi phép kiểm vẫn xanh.
    """
    _dung_cay(tmp_path, "cay-long", co_git=True)
    lenh_da_chay: list[list[str]] = []

    class _Ra:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def _chay_gia(lenh, **kw):
        lenh_da_chay.append(list(lenh))
        return _Ra()

    monkeypatch.setattr(check_ruff.subprocess, "run", _chay_gia)
    monkeypatch.setattr(check_ruff, "GOC_QUET", tmp_path)
    check_ruff.quet()

    assert lenh_da_chay, "phai goi ruff"
    lenh = lenh_da_chay[0]
    assert "--extend-exclude" in lenh, "khong truyen thi tim de lam gi"
    assert "cay-long" in lenh[lenh.index("--extend-exclude") + 1]


def test_phai_dung_extend_exclude_chu_KHONG_phai_exclude(tmp_path, monkeypatch):
    """⛔ `--exclude` trên dòng lệnh **ghi đè** `exclude` của `ruff.toml`.

    🔴 Đo 25/09/2026, và tôi tự dính: truyền `--exclude <cây lồng>` làm ruff bỏ
       luôn `core/` (15.668 dòng FB/TikTok cũ, **đóng băng** — `ruff.toml:52`),
       `alembic/versions`, `node_modules`, `.codex`. Bánh cóc đỏ với `+90 F401`,
       `+5 F821`, `+2 F601` và mọi con số đó trông **y như một hồi quy thật**.

    ⇒ Đúng cái bẫy hàm này đang đi chữa, ở một tầng khác: một phép đo **mở rộng
      phạm vi** rồi báo cáo như thể mã vừa xấu đi. Phạm vi đổi thì con số không
      còn so sánh được với mốc cũ nữa — mốc và phép đo phải nói về **cùng một
      tập hợp**.
    """
    _dung_cay(tmp_path, "cay-long", co_git=True)
    lenh_da_chay: list[list[str]] = []

    class _Ra:
        returncode = 0
        stdout = "[]"
        stderr = ""

    monkeypatch.setattr(check_ruff.subprocess, "run",
                        lambda lenh, **kw: (lenh_da_chay.append(list(lenh)), _Ra())[1])
    monkeypatch.setattr(check_ruff, "GOC_QUET", tmp_path)
    check_ruff.quet()

    assert "--exclude" not in lenh_da_chay[0], (
        "`--exclude` ghi de cau hinh; phai dung `--extend-exclude`")
