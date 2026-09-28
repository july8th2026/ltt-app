r"""`trigger.schedule` · `trigger.webhook` — node keo duoc len Canvas.

## 🔴 Thu thieu KHONG phai ha tang

Do 28/09/2026 truoc khi viet node: **toan bo duong thuc thi da song va da co
test** — `ban_trigger.ban_den_han` (goi tu `dong_co._ban_trigger` moi vong),
`POST /hooks/wf/{trigger_id}`, `han_muc.vuot_han_webhook`, `khoa_idem`, bo lich
`cronsim`, chinh sach lo lich `BO_LO`, tu tat sau 5 loi.

⇒ Thieu DUY NHAT la **node trong registry** — thu nguoi soan *thay va keo*.

⚠️ Day la lan thu **TU** trong mot ngay gap cung hinh dang:
   `gate.ngan_sach_loi(tru_phien_khac=…)` · `ai_router.chon_nhanh()` · ba node
   `ai.*` · va nay bo lich cron. Moi lan: **da xay, co test, KHONG ai noi**.

🔑 Nen tep nay co mot bai do dung dieu do: **module phai duoc IMPORT**. Mot
   module khong duoc import thi moi phep kiem cua no van xanh va tinh nang van
   khong ton tai — `code_sandbox.py` da song nhu the mot thoi gian, va docstring
   cua no tu ghi *"CHUA dang ky"*.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from platform_core.workflow import nut_loi, trigger  # noqa: E402
from platform_core.workflow.ban_trigger import BO_LO  # noqa: E402

HAI_NODE = ("trigger.schedule", "trigger.webhook")


# ══════════════════════════════════════════════════════════════════════════════
#  1. Publish duoc VA co bo thi hanh — thieu ve hai la te hon khong mo
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("loai", HAI_NODE)
def test_publish_duoc(loai):
    assert nut_loi.tat_ca()[loai].publish_duoc is True


@pytest.mark.parametrize("loai", HAI_NODE)
def test_CO_bo_thi_hanh(loai):
    """🔴 Bai nay quan trong hon bai tren, va `trigger.manual` docstring noi ro
    vi sao: `dong_co._chay_mot_inline` xu ca thieu bo thi hanh bang
    `FAILED "loi_he_thong: … khong co bo thi hanh"`.

    ⇒ Mo `publish_duoc` MOT MINH cho ra mot node **publish sach roi FAILED luc
      chay** — TE HON hien trang, vi hien trang chan TRUOC khi khach bam Chay va
      giu tien. Mot cai co khong kem bo thi hanh la mot loi hua, khong phai mot
      tinh nang.
    """
    assert nut_loi.bo_thi_hanh(loai) is not None, (
        f"{loai} publish duoc ma KHONG co bo thi hanh ⇒ khach bam Chay, bi tru "
        "tien, roi nhan `loi_he_thong`")


@pytest.mark.parametrize("loai", HAI_NODE)
def test_kind_KHOP_mot_loai_trigger_DA_DANG_KY(loai):
    """⛔ Node `trigger.schedule` vo nghia neu tang thuc thi khong biet loai lich
    tuong ung. `trigger.tao` tu choi `kind` chua dang ky **luc tao** — nen mot
    node keo duoc ma `kind` chua dang ky se hong o mot buoc SAU, xa cho nguoi
    dung bam.
    """
    can = {"trigger.schedule": "CRON", "trigger.webhook": "WEBHOOK"}[loai]
    assert can in trigger.SO_DANG_KY, (
        f"{loai} tro toi kind {can!r} ma `trigger.SO_DANG_KY` khong co")


# ══════════════════════════════════════════════════════════════════════════════
#  2. 🔑 Ten tham so phai KHOP `WorkflowTrigger.config`
# ══════════════════════════════════════════════════════════════════════════════

def test_tham_so_lich_dung_DUNG_ten_khoa_cua_config():
    """🔴 `cron` · `tz` · `bo_lo` — doc thang tu `trigger._TheoCron._tz` (khoa
    `tz`) va `ban_trigger` (khoa `bo_lo`).

    ⚠️ Mot tu vung thu hai (`mui_gio`/`khi_lo` cho "de doc") buoc phai co mot lop
       dich, va lop dich la dung noi mot truong bi **vut im lang**: ba lan cung
       mot cho noi trong mot ngay 24/09, moi lan doc sai TEN KHOA roi `continue`.
    """
    ts = nut_loi.tat_ca()["trigger.schedule"].tham_so["properties"]
    assert set(ts) == {"cron", "tz", "bo_lo"}, (
        f"ten tham so lech voi `WorkflowTrigger.config`: {sorted(ts)}")


def test_enum_bo_lo_DOC_hang_so_chu_khong_go_lai():
    """⭐ Cung ly le `TRAN_N_GO_TAY`: lan doi 6→7 sua mot ben, bo ben kia, va gate
    do o dung phep kiem dang le bao ve no. Enum o node phai LA `BO_LO`."""
    ts = nut_loi.tat_ca()["trigger.schedule"].tham_so["properties"]
    assert ts["bo_lo"]["enum"] == list(BO_LO), (
        f"enum {ts['bo_lo']['enum']} khac `ban_trigger.BO_LO` {list(BO_LO)}")


def test_cron_la_BAT_BUOC():
    ts = nut_loi.tat_ca()["trigger.schedule"].tham_so
    assert ts["required"] == ["cron"], ts["required"]


# ══════════════════════════════════════════════════════════════════════════════
#  3. ⛔ BAO MAT — `trigger.webhook` KHONG duoc co tham so bi mat
# ══════════════════════════════════════════════════════════════════════════════

def test_webhook_KHONG_co_tham_so_token():
    """🔴 `params` di vao `workflow_version`, va ban ghi ay **duoc nhan ban khi
    khach "Save as"** roi tra nguyen van cho trinh soan thao
    (`bien_dich._node_chung` da ghi lai cai gia nay cho `core.http`).

    ⇒ Mot token trong `params` la mot bi mat da roi khoi tay chu no. Token song o
      `WorkflowTrigger.config` qua `trigger.bam_token`/`token_khop`.

    ⭐ Bai nay do bang **tap khoa**, khong bang mot danh sach ten cam: mot ten
       moi (`secret`, `khoa_bi_mat`, `api_key`) se di qua mot danh sach cam,
       nhung khong di qua duoc mot lenh doi **RONG**.
    """
    ts = nut_loi.tat_ca()["trigger.webhook"].tham_so
    assert ts["properties"] == {}, (
        "`trigger.webhook` khai tham so: moi tham so o day di vao "
        f"`workflow_version` va bi nhan ban khi khach Save as. Thay: {sorted(ts['properties'])}")
    assert ts.get("additionalProperties") is False


# ══════════════════════════════════════════════════════════════════════════════
#  4. Bo thi hanh chuyen DU payload sang cong `event`
# ══════════════════════════════════════════════════════════════════════════════

class _RunGia:
    def __init__(self, inputs):
        self.inputs = inputs


def test_lich_chuyen_fired_at_va_bu():
    """⭐ `fired_at`/`bu` la dung hai khoa `ban_trigger` dat vao `inputs`. Vut
    `bu` la vut mot thu dong co **da tinh** — va mot workflow co quyen xu khac
    cho luot bu (vd khong gui thong bao lai)."""
    ham = nut_loi.bo_thi_hanh("trigger.schedule")
    kq = ham(None, _RunGia({"fired_at": "2026-09-28T08:00:00+00:00", "bu": True}),
             {"id": "n1", "type": "trigger.schedule"})
    ev = kq.output["event"]
    assert ev["fired_at"] == "2026-09-28T08:00:00+00:00"
    assert ev["bu"] is True
    assert ev["nguon"] == "lich"


def test_webhook_chuyen_than_va_query():
    ham = nut_loi.bo_thi_hanh("trigger.webhook")
    kq = ham(None, _RunGia({"than": {"a": 1}, "query": {"b": "2"}}),
             {"id": "n1", "type": "trigger.webhook"})
    ev = kq.output["event"]
    assert ev["than"] == {"a": 1}
    assert ev["query"] == {"b": "2"}
    assert ev["nguon"] == "webhook"


def test_run_KHONG_co_inputs_thi_van_chay_duoc():
    """⛔ Doi chung: mot run tao tay (`tac_tu.py` truyen `inputs={}`) khong duoc
    lam node nem. Trigger la node DAU — no nem thi ca run chet truoc khi lam gi.
    """
    for loai in HAI_NODE:
        ham = nut_loi.bo_thi_hanh(loai)
        kq = ham(None, _RunGia(None), {"id": "n1", "type": loai})
        assert "event" in kq.output, loai


# ══════════════════════════════════════════════════════════════════════════════
#  5. 🔑 Module phai duoc IMPORT — bai bat dung hinh dang "da xay, chua noi"
# ══════════════════════════════════════════════════════════════════════════════

def test_module_duoc_NOI_vao_nut_loi():
    """🔴 Bai dat nhat tep nay, va no do thu ba bai tren KHONG do duoc.

    Ba bai kia goi `nut_loi.tat_ca()` — va `tat_ca()` chi thay node nao neu
    module khai no **da duoc import**. Nhung chinh tep test nay import
    `platform_core.workflow.nut_loi`, nen neu mot ngay ai xoa dong import trong
    `__init__.py` ma module van ton tai, ba bai kia **van xanh** khi tep test
    nay tinh co import truc tiep... va tinh nang **khong ton tai** tren san pham.

    ⭐ Nen bai nay doc **AST cua `__init__.py`**, ⛔ khong hoi `sys.modules`: mot
       module co the nam trong `sys.modules` vi MOT TEP TEST KHAC vua import no.
       Cung ly le `test_5606` (moi module route phai duoc `__init__` import).
    """
    src = (GOC / "platform_core" / "workflow" / "nut_loi" / "__init__.py"
           ).read_text(encoding="utf-8")
    cay = ast.parse(src)
    da_nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                da_nhap.add(a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                da_nhap.add(a.name.rsplit(".", 1)[-1])
    assert "trigger_lich_hook" in da_nhap, (
        "`nut_loi/__init__.py` KHONG import `trigger_lich_hook` ⇒ hai node bien "
        "mat khoi registry tren san pham, trong khi moi phep kiem cua chung van "
        "xanh vi tep test nay tu import module. Day la hinh dang 'da xay, chua "
        "noi' — lan thu tu trong mot ngay.")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
