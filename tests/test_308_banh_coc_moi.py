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


def test_banh_coc_route_server_CUONG_CHE_con_so_chu_khong_chi_ghi_ra(tmp_path):
    """⛔ Một chốt ghi lại thứ nó không cưỡng chế là một chốt nói dối về phạm vi.

    Trước 2026-09-02 chốt này chỉ so **tập hợp** tệp. `dong`/`handler` được ghi
    vào mốc và được IN RA mỗi lần chạy — nhưng không bao giờ được so. Một tệp đã
    nằm trong mốc có thể phình vô hạn mà dòng RESULT vẫn là PASS.

    Và nó đã xảy ra: `server/admin.py` đi từ **1.388 → 1.622** dòng (+234) trong
    khi chốt báo PASS suốt đoạn đường đó.

    ⚠️ Đây không phải luật mới: luật cũ vẫn là "nợ chỉ được giảm". Phần còn
       thiếu là một nửa phép so.

    ⛔ CHỐT NÀY KHÔNG ĐƯỢC GHI VÀO CÂY, và bản đầu của nó đã phạm đúng điều đó.

       Bản đầu sửa tạm `tools/server_routes_baseline.json` rồi khôi phục. Hai
       hậu quả, cả hai đều đã xảy ra thật:

         · `gate._anh_chup_cay()` quét `tools/` để phát hiện cây đổi giữa chừng
           ⇒ mỗi lượt chạy làm gate in "CÂY ĐÃ ĐỔI TRONG LÚC CHẠY", tức chốt
           **tự phá lượt đo chứa nó**;
         · bước tĩnh `kich thuoc route server` chạy **song song** với bộ test và
           đọc đúng tệp ấy ⇒ nó đọc trúng bản đã bị sửa và ĐỎ.

       Điều thứ hai chính là `gate.TEP_KHONG_DUOC_DOC_SONG_SONG` — danh sách đã
       tồn tại vì ba tệp khác từng gây `OSError [Errno 22]` và làm hai phiên mất
       gần trọn một ngày. Thêm tệp thứ tư vào danh sách ấy là cách sai: cách
       đúng là **đừng ghi vào cây**.

    ⭐ Nên chốt này vá `MOC` sang `tmp_path` và gọi thẳng `main()`. Không tiến
       trình con, không chạm cây, không đua với ai.
    """
    import io
    import json
    import sys
    from contextlib import redirect_stdout
    from unittest.mock import patch

    from tools import check_server_routes as csr

    that = json.loads(csr.MOC.read_text(encoding="utf-8"))
    assert that, "moc rong — khong kiem duoc gi"
    ten = sorted(that)[0]
    that[ten]["dong"] = int(that[ten]["dong"]) - 10     # giả vờ tệp vừa phình

    gia = tmp_path / "moc_gia.json"
    gia.write_text(json.dumps(that, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    dau_ra = io.StringIO()
    cu = csr.MOC
    try:
        csr.MOC = gia
        # `main()` gọi `parse_args()` không tham số ⇒ nó đọc `sys.argv`, mà dưới
        # pytest `sys.argv` là dòng lệnh của pytest. Không vá thì argparse thoát
        # với mã 2 và chốt đỏ vì một lý do chẳng liên quan gì tới điều nó đo.
        with patch.object(sys, "argv", ["check_server_routes.py"]), \
                redirect_stdout(dau_ra):
            ma = csr.main()
    finally:
        csr.MOC = cu

    assert ma == 1, ("tep da vuot nguong phinh them 10 dong ma chot van PASS — "
                     "con so trong moc lai chi de trang tri")
    assert "PHINH" in dau_ra.getvalue().upper()


def test_guard_doi_dang_nhap_khong_chi_la_MOT_ten_ham():
    """⛔ Một cảnh báo sai lâu ngày dạy người ta bỏ qua chính công cụ phát ra nó.

    Trước 2026-09-02 chốt này khớp đúng chuỗi `require_login`, nên nó cảnh báo
    `apps/qualitylab` — một app `public=False`, `surface="admin"`, mọi route đều
    `Depends(require_operator)`. Đó là **cảnh báo duy nhất** linter phát ra trên
    cả 15 app, và nó là **dương tính giả**.

    ⭐ `server/deps.py:99` `require_operator` gọi chính `require_login` rồi thêm
       chốt 403 nếu không phải quản trị viên — tức nó MẠNH HƠN, không yếu hơn.

    ⚠️ Sửa bằng cách dạy chốt biết thêm một guard, KHÔNG bằng cách thêm ngoại lệ
       cho `qualitylab`: một ngoại lệ sống lâu hơn hoàn cảnh sinh ra nó.
    """
    import inspect

    from server import deps
    from tools.lint_app_contract import GUARD_DOI_DANG_NHAP

    assert "require_login" in GUARD_DOI_DANG_NHAP
    assert "require_operator" in GUARD_DOI_DANG_NHAP

    # Và điều làm `require_operator` hợp lệ phải được ĐO, không phải tin lời:
    # nó phải thật sự gọi `require_login`.
    than = inspect.getsource(deps.require_operator)
    assert "require_login(request)" in than, (
        "require_operator khong con goi require_login - no khong con du tu cach "
        "lam guard dang nhap, va GUARD_DOI_DANG_NHAP phai bo no ra")


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


# ── Bánh cóc 4: biên `apps/` → `apps/` (A-01) ────────────────────────────────

def test_chi_MOT_canh_xuyen_san_pham_va_no_da_duoc_khai():
    """Đo bằng AST, không tin danh sách: kho có đúng một cạnh app→app.

    Nếu ai đó thêm cạnh thứ hai mà quên khai vào `APP_DUOC_DUNG_APP`, phép kiểm
    ở dưới đã đỏ. Phép kiểm **này** bắt trường hợp ngược lại: khai một cạnh
    trong hợp đồng mà thực tế không còn ai dùng — một quyền được cấp rồi bỏ đó
    là một cánh cửa không ai canh.
    """
    import ast
    import pathlib

    from tools.lint_app_contract import APP_DUOC_DUNG_APP

    that = set()
    for f in sorted(pathlib.Path("apps").rglob("*.py")):
        phan = str(f).replace("\\", "/").split("/")
        if "__pycache__" in phan:
            continue
        nguon = phan[1]
        try:
            cay = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and not n.level and n.module:
                mods = [n.module]
            for m in mods:
                p = m.split(".")
                if p[0] == "apps" and len(p) > 1 and p[1] != nguon:
                    that.add((nguon, p[1]))

    assert that == set(APP_DUOC_DUNG_APP), (
        f"canh thuc te {sorted(that)} khac hop dong "
        f"{sorted(APP_DUOC_DUNG_APP)}")


def test_be_mat_cong_khai_cua_upscalevideo_chot_CA_TEN_khong_chi_module():
    """⛔ Chốt tên, không chốt module.

    Chốt mỗi module thì `from apps.upscalevideo import bat_cu_gi` vẫn lọt, và
    hợp đồng chỉ còn là một lời để ngỏ. Đã chứng minh luật bắn đúng:

        im   from apps.upscalevideo import cost
        im   from apps.upscalevideo.service import submit_upscale_job
        BAN  from apps.upscalevideo import jobs
        BAN  from apps.upscalevideo.service import _noi_bo
        BAN  from apps.upscalevideo import cost, jobs
        BAN  taoanh: from apps.upscalevideo import cost   (khac cap)
    """
    from tools.lint_app_contract import APP_DUOC_DUNG_APP

    assert APP_DUOC_DUNG_APP[("taovideo", "upscalevideo")] == {
        ("apps.upscalevideo", "cost"),
        ("apps.upscalevideo.service", "submit_upscale_job"),
    }, ("be mat cong khai cua `upscalevideo` da doi. Do la mot QUYET DINH KIEN "
        "TRUC — cap nhat AGENTS.md muc 8.3 cung luc, dung sua mot ben.")
