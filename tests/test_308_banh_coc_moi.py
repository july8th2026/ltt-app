"""test_308 — hai bánh cóc mới của audit 2026-08-26, và bằng chứng chúng KÊU.

Không mạng, không GPU, không CSDL.

## ⭐ VÌ SAO PHẢI CHỨNG MINH BÁNH CÓC KÊU

Cả đợt audit này xoay quanh một phát hiện: **một phép kiểm không được cắm vào đâu
trông y hệt một phép kiểm đang chạy.** Bốn ca đã dính (`usage.reconcile`,
`costing.scan_for_alerts`, `backup.ps1`, bài học `anhnoibo`).

Thêm hai bánh cóc mới rồi tin là chúng hoạt động sẽ là **lặp lại đúng lỗi vừa
tìm ra**. Nên mỗi phép kiểm ở đây chốt hai điều:

  1. nó IM trên cây hiện tại (không báo động giả);
  2. nó KÊU khi dựng lại đúng vi phạm mà nó sinh ra để bắt.

Điều (2) mới là điều đáng chốt. Điều (1) một tệp rỗng cũng làm được.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Bánh cóc 1: chuông đã đúc mà chưa ai treo ─────────────────────────────────

def test_chuong_chua_treo_im_tren_cay_hien_tai():
    from tools import check_chuong_chua_treo as c

    treo = {f"{t['o']}::{t['ham']}" for t in c.quet()}
    moc = set(__import__("json").loads(
        (ROOT / "tools" / "chuong_baseline.json").read_text(encoding="utf-8")))
    assert treo - moc == set(), f"co ham quet/canh bao MOI khong ai goi: {treo - moc}"


def test_chuong_chua_treo_KEU_khi_go_mot_day_cam(tmp_path, monkeypatch):
    """Dựng lại đúng trạng thái trước `a5274bf`: gỡ dòng gọi
    `costing.scan_for_alerts` ra khỏi vòng bảo trì.

    ⭐ Đây là phép kiểm quan trọng nhất tệp này. Nó chứng minh bánh cóc bắt được
       **ca có thật**, chứ không phải một ca giả tưởng dựng cho vừa phép kiểm.
    """
    from tools import check_chuong_chua_treo as c

    goc = (ROOT / "platform_core" / "job_runner.py").read_text(encoding="utf-8")
    dong = "        raised += len(costing.scan_for_alerts(db))\n"
    assert dong in goc, "day cam da bien mat — hoac da doi hinh dang"

    # Dung mot cay GIA trong tmp_path; KHONG dong vao kho that.
    gia = tmp_path / "kho"
    (gia / "platform_core" / "public_api").mkdir(parents=True)
    (gia / "server").mkdir()
    (gia / "apps").mkdir()
    (gia / "platform_core" / "job_runner.py").write_text(
        goc.replace(dong, ""), encoding="utf-8")
    (gia / "platform_core" / "public_api" / "costing.py").write_text(
        (ROOT / "platform_core" / "public_api" / "costing.py").read_text(
            encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(c, "GOC", gia)
    ten = {f"{t['o']}::{t['ham']}" for t in c.quet()}
    assert any("scan_for_alerts" in t for t in ten), (
        f"banh coc KHONG bat duoc ca goc. Tim thay: {ten}")


# ── Bánh cóc 2: kích thước route của `server/` ────────────────────────────────

def test_kich_thuoc_route_server_im_tren_cay_hien_tai():
    from tools import check_server_routes as c

    hien = set(c.quet())
    moc = set(__import__("json").loads(
        (ROOT / "tools" / "server_routes_baseline.json").read_text(encoding="utf-8")))
    assert hien - moc == set(), f"co tep route server MOI vuot nguong: {hien - moc}"


def test_kich_thuoc_route_server_KEU_voi_mot_tep_qua_lon(tmp_path, monkeypatch):
    from tools import check_server_routes as c

    gia = tmp_path / "kho"
    (gia / "server" / "routes").mkdir(parents=True)
    (gia / "server" / "routes" / "phinh_to.py").write_text(
        "\n".join(f"# dong {i}" for i in range(c.MAX_DONG + 50)), encoding="utf-8")

    monkeypatch.setattr(c, "GOC", gia)
    assert "server/routes/phinh_to.py" in c.quet()


def test_hai_noi_thi_hanh_dung_MOT_con_so():
    """Trần 900/30 được thi hành ở hai chỗ. Lệch nhau thì người đọc không biết
    tin bên nào — nên chốt chúng bằng nhau."""
    from tools import check_server_routes, lint_app_contract

    assert check_server_routes.MAX_DONG == lint_app_contract.MAX_ROUTES_LINES
    assert check_server_routes.MAX_HANDLER == lint_app_contract.MAX_ROUTES_HANDLERS


# ── Bánh cóc 3 (đã có từ `db6147e`): app sinh nav phải có trang ──────────────

def test_bien_apps_toi_server_van_duoc_thi_hanh():
    """Hợp đồng bốn module. Nếu ai đó nới nó ra thì phải là hành động CÓ Ý —
    phép kiểm này làm cho việc nới im lặng trở thành việc không thể."""
    from tools.lint_app_contract import SERVER_APP_CO_THE_DUNG

    assert SERVER_APP_CO_THE_DUNG == {
        "server.deps", "server.auth.session",
        "server.auth.csrf", "server.templating",
    }, ("hop dong apps->server da doi. Do la mot QUYET DINH KIEN TRUC — cap nhat "
        "AGENTS.md 8.2b va phep kiem nay cung luc, dung sua mot ben.")
