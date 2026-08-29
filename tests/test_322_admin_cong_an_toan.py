"""Cong an toan cua khu quan tri (`docs/admin_mvp_v3/18_SAFETY_GATE.md`).

Tep nay khong kiem mot trang nao. No kiem BAT BIEN — nhung thu phai dung o MOI
trang, va phai con dung sau moi lan doi giao dien.

Khac voi cac tep test lo (312-315) o cho: cac tep do chung minh mot trang lam
dung viec cua no; tep nay chung minh khong trang nao lam hong viec chung.
"""
from __future__ import annotations

import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[1]
ADMIN = (GOC / "server/admin.py").read_text(encoding="utf-8")
ADMIN_API = (GOC / "server/admin_api.py").read_text(encoding="utf-8")


def _handler_post(src: str) -> dict[str, str]:
    """`route -> than handler` cho moi `@expose(..., methods=[... "POST" ...])`."""
    dong = src.splitlines()
    ra = {}
    for i, l in enumerate(dong):
        if "@expose(" not in l or "POST" not in l:
            continue
        route = re.search(r'"([^"]+)"', l).group(1)
        than = []
        for j in range(i + 1, len(dong)):
            if "@expose" in dong[j] or dong[j].startswith("class "):
                break
            than.append(dong[j])
        ra[route] = "\n".join(than)
    return ra


POST = {**_handler_post(ADMIN), **_handler_post(ADMIN_API)}


def test_bo_test_nay_thay_du_bat_mat_mutation():
    """Neu con so nay tut xuong, mot mutation vua bien mat khoi tam quet."""
    assert len(POST) >= 12, sorted(POST)


def test_moi_thao_tac_ghi_deu_kiem_csrf():
    thieu = [r for r, t in POST.items() if "verify_csrf_token" not in t]
    assert not thieu, thieu


def test_moi_thao_tac_ghi_deu_de_lai_dau_vet():
    """⭐ Truoc dot `admin_mvp_v3` con so nay la 5/11.

    Sau khong ghi nhat ky: them/sua provider credential, bat-tat-reset provider
    key, tao/sua goi nap, bat-tat-xoa goi nap, va **xac nhan don da tra** — tuc
    mot thao tac TIEN. Dau vet cua no chi nam trong `order.note` va but toan
    credit, nen cau "ai xac nhan don nay" khong tra duoc o noi nguoi ta se tim.
    """
    thieu = [r for r, t in POST.items()
             if "ghi_nhat_ky" not in t and "nhat_ky" not in t.lower()]
    assert not thieu, thieu


def test_khong_route_admin_nao_bi_xoa():
    """Ma tran tuong thich (`03_IA_FREEZE.md` §4) chot: 0 URL bi xoa, 0 bi doi.

    Ha mot trang khoi thanh ben la hop le; xoa route cua no thi khong — mot URL
    da vao dau trang va tin nhan ho tro thi 404 la thiet hai that.
    """
    phai_con = {
        # tu viet
        "/nguoi-dung", "/apikeys", "/grant-credit", "/api-key-them",
        "/api-key-sua", "/api-key-test", "/api-key-action", "/api-models",
        "/api-models-refresh", "/doanh-thu", "/goi", "/goi/action", "/don",
        "/don/action",
        # khu API
        "/api-tong-quan", "/api-tai-khoan", "/api-khoa", "/api-khoa-action",
        "/api-cong-cu", "/api-chinh-sach", "/api-chinh-sach-action",
        "/api-kill-switch", "/api-kill-switch-action", "/api-gia",
        "/api-gia-action", "/api-margin", "/api-request", "/api-job",
        "/api-bao-mat", "/api-trace", "/api-trace-export",
    }
    co = set(re.findall(r'@expose\("([^"]+)"', ADMIN + ADMIN_API))
    thieu = sorted(phai_con - co)
    assert not thieu, thieu


def test_kill_switch_van_doi_ly_do_o_tang_service():
    """Anh mockup ve kill switch la mot TOGGLE, kem ba dong meta rong.

    Doc nguoc lai: ba dong do la ba TRUONG BAT BUOC ma backend doi. Neu ai do
    lam theo anh — mot cong tac khong co o ly do — thi hanh dong se LUON that
    bai o `_require_reason`. Phep kiem nay chot rang rang buoc do van o tang
    service, khong bi day len UI.
    """
    policy = (GOC / "platform_core/public_api/policy.py").read_text(encoding="utf-8")
    assert "def _require_reason" in policy or "reason" in policy
    tables = (GOC / "platform_core/public_api/tables.py").read_text(encoding="utf-8")
    assert "reason" in tables
    # Va form o admin phai co o ly do bat buoc.
    than = POST["/api-kill-switch-action"]
    assert "reason" in than

    # ⚠️ Tu 29/08 markup nam o TEMPLATE, khong con o `admin_api.py` — thanh 12
    #    trang API da chuyen sang Jinja. Phep kiem theo markup ve dung cho no
    #    o, va chat hon ban cu: khong chi doi o ton tai ma doi no BAT BUOC.
    vo = (GOC / "server/templates/admin/api_kill_switch.html").read_text(
        encoding="utf-8")
    assert 'name="reason"' in vo
    assert "required" in vo and "minlength" in vo
    # 🔴 Va no phai la mot FORM co o xac nhan, khong phai mot toggle. Anh mockup
    #    ve toggle; lam theo anh thi thao tac LUON that bai o tang service.
    assert 'name="confirm"' in vo
    assert "<input type=\"checkbox\"" in vo


def test_khong_secret_nao_bi_render():
    """Bat bien tu `01_LIVE_EVIDENCE.md` §2 — bon thu khong bao gio duoc ra HTML."""
    # Token phien CHINH LA khoa chinh cua `Session`. Khong duoc dua vao cot nao.
    assert "DbSession.id" not in ADMIN or "column_list" not in ADMIN.split("DbSession.id")[0][-400:]
    for cam in ("credential_enc", "password_hash"):
        # Duoc phep nhac trong chu thich; khong duoc phep noi vao chuoi HTML.
        for dong in (ADMIN + ADMIN_API).splitlines():
            d = dong.strip()
            if cam in d and not d.startswith("#"):
                assert "f'" not in d and 'f"' not in d, d


def test_so_credit_van_append_only_o_tang_model_view():
    khoi = ADMIN[ADMIN.index("class CreditEntryAdmin"):]
    khoi = khoi[:khoi.index("class ")] if "class " in khoi[10:] else khoi
    khoi = ADMIN[ADMIN.index("class CreditEntryAdmin"):
                 ADMIN.index("class AppAccessAdmin")]
    assert "can_create = False" in khoi
    assert "can_edit = False" in khoi
    assert "can_delete = False" in khoi


def test_mark_paid_van_di_qua_duong_idempotent():
    """Khong duoc thay `billing.ghi_nhan_tra` bang mot duong cong credit khac."""
    than = POST["/don/action"]
    assert "billing.ghi_nhan_tra" in than
    assert "credit.nap" not in than
    assert "cap_tay" not in than
