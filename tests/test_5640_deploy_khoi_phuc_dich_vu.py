r"""Deploy bo do PHAI dua dich vu tro lai — va `Move-Item` phai THU LAI.

## 🔴 Su co 2026-09-28 17:38 — production 502 cho toi khi CO NGUOI DE Y

```
EXITCODE=1                    17:38:06 -> 17:39:14  (68 giay)
Move-Item C:\LTTPlatform\app  ->  'Access to the path is denied'  (2-cai-dat.ps1:674)
/health/ready                 502   <- ba dich vu deu Stopped
```

Script da **dung dich vu** o buoc truoc, roi `Move-Item` nem, roi script **thoat**
— va ⛔ khong ai dua dich vu tro lai. Ban cu chua bi cham (Move that bai TRUOC khi
chep gi), nen that bai ay **sach** ve du lieu; cai gia la downtime.

## 🔑 HAI khiem khuyet, va cai thu hai moi la cai dat

**1. Cuoc dua trong chinh script.** `Stop-Service -Force` tra ve khi **SCM danh
dau** la Stopped — ⛔ KHONG khi tien trinh da thoat va nha handle. Va script co
`Start-Sleep -Seconds 2` sau `Stop-Service` o **ba** cho khac (:1098, :1134,
:1164), nhung o cho **duy nhat** ma ngay sau `Stop-Service` la mot phep **doi ten
thu muc** thi lai ⛔ khong cho gi. Mot bat nhat trong cung mot tep.

⭐ Va no giai thich vi sao luot **15:12 cung ngay THANH CONG**: mot cuoc dua thang
   hay thua theo thoi diem, ⛔ khong hong deu. Defender quet thi lau hon 2 giay.

**2. ⛔ KHONG co duong khoi phuc.** Giua "dung dich vu" (~:665) va "khoi dong lai"
(~:1290) co **~620 dong**. Truoc ban va nay, MOI loi trong khoang do de production
xuong **vo han dinh**.

## ⚠️ Bai hoc 21/08 da duoc ap ĐÚNG MỘT NỬA — day la cho dat nhat

Phien `Auto Scan Video` chi ra: so cua ho ghi ca **21/08 site sap** vi
`$ErrorActionPreference='Stop'` quanh mot lenh native (alembic in INFO ra stderr)
lam script thoat **sau khi da dung dich vu**. Bai hoc ghi lai gom **hai** ve:
*"⛔ khong `Stop` quanh lenh native"* **va** *"`finally` luon bat lai dich vu"*.

Doc mã thi: ve MOT thanh `Invoke-Ngoai` (:49-55) — chan **NGUYEN NHAN** cu the.
Ve HAI **chua bao gio duoc viet**: `finally` duy nhat trong tep la o :53 va no chi
khoi phuc `$ErrorActionPreference`.

🔑 ⇒ Ho va **nguyen nhan** (stderr cua exe) roi ghi bai hoc nhu the ca **lop** da
   duoc xu. Hom nay mot nguyen nhan KHAC (`Move-Item` / handle chua nha) di qua
   dung cai lo ve hai de lai. Cung ho `luat-thieu-ve-ngoai-le-nhan-theo-so-nguoi-doc`
   va `ma-phong-thu-cho-ca-khong-the-xay-ra` doc nguoc.

⭐ Nen `trap` ma bai kiem nay ghim ⛔ **khong** nham vao `Move-Item`. No nham vao
   **moi** loi giua stop va start, bat ke nguyen nhan — vi danh sach nguyen nhan
   ⛔ khong bao gio day du, con "dich vu phai song" thi luon dung.

## ⚠️ Va `trap` ay DA DUOC CHAY THAT, ⛔ khong chi doc qua

Do 28/09 bang mot `.ps1` thu: `Stop` gia lap -> `Move-Item` that bai -> `catch`
noi bo `throw` -> **`TRAP CHAY`** in ra, va **ma thoat van la 1**. Hai ve deu can:
trap phai chay, va no ⛔ khong duoc che loi.

🔴 Lan do dau toi dung `tail -8` va ⛔ khong thay dong `TRAP CHAY` — toi suyt ket
   luan *"trap khong chay"*. Dung ho `doc-thu-dai-dien-thay-vi-doc-thu-that`: mot
   cua so doc CAT MAT bang chung doc y het bang chung VANG MAT.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
PS1 = GOC / "setup" / "2-cai-dat.ps1"


@pytest.fixture(scope="module")
def src() -> str:
    return PS1.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  1. Duong KHOI PHUC — ve thu hai cua bai hoc 21/08
# ══════════════════════════════════════════════════════════════════════════════

def test_co_trap_khoi_phuc_dich_vu(src):
    """⛔ Thieu cai nay thi moi loi giua stop va start = production xuong vo han."""
    assert re.search(r"^trap\s*\{", src, re.M), (
        "`2-cai-dat.ps1` KHONG co `trap` — mot loi bat ky giua 'dung dich vu' va "
        "'khoi dong lai' (~620 dong) se de production o trang thai Stopped cho "
        "toi khi co nguoi de y. Ca that 28/09 va 21/08.")


def test_trap_KHOI_DONG_LAI_dich_vu_chu_khong_chi_in_ra(src):
    """⚠️ Mot `trap` chi `Write-Host` la mot lop phong thu GIA: no bao dong roi
    de production nam duoi. Doi loi goi `Start-Service` NGAY TRONG than trap."""
    mo = re.search(r"^trap\s*\{(.*?)^\}", src, re.M | re.S)
    assert mo, "khong doc duoc than `trap`"
    than = mo.group(1)
    assert "Start-Service" in than, (
        "than `trap` khong goi `Start-Service` — no bao dong ma khong khoi phuc")
    for svc in ("LTTStudioWeb", "LTTStudioWorker", "LTTStudioVoice"):
        assert svc in than, f"`trap` bo sot dich vu {svc}"


def test_trap_KHONG_che_loi(src):
    """⛔ `trap` phai `break` (hoac `throw`), ⛔ KHONG `continue`.

    🔴 `continue` trong trap lam script **di tiep** sau loi va thoat 0 — tuc mot
       deploy that bai bao THANH CONG. Do te hon ca su co goc: hom nay ta thay
       `EXITCODE=1` nen biet co chuyen; voi `continue` thi ⛔ khong ai biet.
    """
    mo = re.search(r"^trap\s*\{(.*?)^\}", src, re.M | re.S)
    than = mo.group(1)
    assert re.search(r"\b(break|throw)\b", than), (
        "`trap` khong `break`/`throw` ⇒ script di tiep sau loi va co the thoat 0: "
        "mot deploy that bai se bao THANH CONG")
    assert not re.search(r"^\s*continue\s*$", than, re.M), (
        "`trap` dung `continue` — no CHE loi")


def test_co_co_de_trap_biet_da_khoi_dong_lai_chua(src):
    """⭐ Thieu co nay thi `trap` se khoi dong lai o **moi** loi, ke ca loi xay ra
    SAU khi dich vu da chay — vo hai nhung gay nhieu, va mot canh bao gay nhieu
    thi nguoi ta hoc cach bo qua."""
    assert "DaDungDichVu" in src and "DaKhoiDongLai" in src, (
        "thieu co trang thai: `trap` khong phan biet duoc 'chua kip khoi dong "
        "lai' voi 'da chay roi'")


# ══════════════════════════════════════════════════════════════════════════════
#  2. Cuoc dua `Stop-Service` -> `Move-Item`
# ══════════════════════════════════════════════════════════════════════════════

def test_move_item_app_co_THU_LAI(src):
    """🔴 `Stop-Service -Force` tra ve khi SCM danh dau Stopped, ⛔ KHONG khi tien
    trinh da nha handle. Nen phep doi ten NGAY SAU no phai thu lai.

    ⭐ Thu lai co backoff, ⛔ khong `Start-Sleep` co dinh: Defender quet lau hon
       hai giay, va mot hang so o day la mot cuoc dua khac cho doi so.
    """
    mo = re.search(r"Move-Item \$appDir \$prev", src)
    assert mo, "khong tim thay `Move-Item $appDir $prev`"
    # Vung ~40 dong quanh loi goi phai co mot vong lap thu lai.
    dau = max(0, mo.start() - 2000)
    vung = src[dau:mo.end() + 2000]
    assert re.search(r"foreach\s*\(\s*\$lan\s+in\s+1\.\.", vung), (
        "`Move-Item $appDir $prev` KHONG nam trong vong thu lai ⇒ mot handle chua "
        "nha (binh thuong tren Windows) lam ca luot deploy chet, va no chet SAU "
        "khi dich vu da bi dung")


def test_co_CHO_dich_vu_that_su_Stopped(src):
    """⛔ `Start-Sleep -Seconds 2` la mot con so DOAN. Doi mot phep DO."""
    assert re.search(r"\$s\.Status\s+-eq\s+'Stopped'", src) or \
        re.search(r"Status\s+-ne\s+'Stopped'", src), (
        "khong thay phep DO trang thai dich vu truoc khi doi ten thu muc — "
        "script chi `Start-Sleep` mot hang so")


def test_that_bai_phai_NOI_AI_dang_giu(src):
    """⚠️ Mot `'Access denied'` tran ⛔ khong the chan doan duoc. Lan 28/09 toi mat
    mot luot deploy (va may phut production) de tim ra rang ⛔ khong tien trinh nao
    con song — tuc thu pham la mot handle, ⛔ khong phai mot chuong trinh."""
    mo = re.search(r"Move-Item \$appDir \$prev", src)
    vung = src[max(0, mo.start() - 2000):mo.end() + 2500]
    assert "Win32_Process" in vung, (
        "vong thu lai khong in ra tien trinh dang mo tep duoi `app\\` khi that "
        "bai — nguoi doc se lai thay mot 'Access denied' tran")


# ══════════════════════════════════════════════════════════════════════════════
#  3. Luat 6: `.ps1` thuan ASCII, khong BOM (da lam sap production)
# ══════════════════════════════════════════════════════════════════════════════

#: Moi `.ps1` trong `setup/`. ⛔ KHONG go ten tung tep: mot tep moi them vao thu
#: muc nay phai duoc kiem **mac dinh**, khong phai khi ai do nho them ten.
PS1_SETUP = sorted((GOC / "setup").glob("*.ps1"))


def test_co_it_nhat_mot_ps1_de_kiem():
    """⛔ Doi chung cho bai duoi: `glob` tra tap RONG thi bai kia xanh ma ⛔ khong
    kiem gi. Mot phep kiem tren tap rong la mot phep kiem **vang mat**."""
    assert PS1_SETUP, "khong thay `.ps1` nao trong `setup/` - glob sai duong?"
    assert any(p.name == "2-cai-dat.ps1" for p in PS1_SETUP), (
        "`2-cai-dat.ps1` khong nam trong tap quet - dung cai lo ma bai duoi mo ta")


@pytest.mark.parametrize("tep", PS1_SETUP, ids=lambda p: p.name)
def test_moi_ps1_trong_setup_thuan_ASCII_va_khong_BOM(tep):
    """🔴 **BAI NAY BAT DUOC MOT LO THAT, va no bat duoc vi TOI VUA VI PHAM.**

    `tests/test_45_deploy_scripts.py::test_scripts_are_pure_ascii` co **dung** phep
    kiem nay - nhung `DEPLOY_DIR` cua no tro toi **`deploy/windows/`**, va
    `EXPECTED_SCRIPTS` ⛔ **khong** chua `2-cai-dat.ps1`. Do duoc 28/09:

        DEPLOY_DIR                          -> <kho>/deploy/windows
        '2-cai-dat.ps1' in EXPECTED_SCRIPTS -> False

    ⇒ **Script deploy CHINH - cai da lam sap production hai lan - ⛔ khong nam
      trong mot banh coc ASCII nao.** `CLAUDE.md` luat 6 viet *"`.ps1` thuan
      ASCII"*; luat co, con co che chi bao mot nua thu muc.

    ⚠️ Toi phat hien vi ban va `trap` cua toi mang mot em dash (3 byte UTF-8 tai
       offset 1661) va `test_45` **van XANH**. Neu toi ⛔ khong vi pham, lo nay con
       nam do - va lan sau se la mot phien khac, tren mot dong ma **khong phai chu
       thich**. Cung ho `pham-vi-phep-do-hep-hon-loi-tuyen-bo`: mot phep kiem dung
       ap tren mot TAP CON, va ten cua no ⛔ khong noi ra tap con ay.

    ⭐ Nen bai nay `glob("*.ps1")` chu ⛔ khong go ten: mot tep `.ps1` moi trong
       `setup/` duoc kiem **mac dinh**.
    """
    tho = tep.read_bytes()
    assert not tho.startswith(b"\xef\xbb\xbf"), f"{tep.name} co BOM"
    xau = [(i, b) for i, b in enumerate(tho) if b > 127]
    canh = ""
    if xau:
        i = xau[0][0]
        canh = tho[max(0, i - 50):i + 20].decode("utf-8", "replace")
    assert not xau, (
        f"{tep.name}: {len(xau)} byte ngoai ASCII, dau tien o offset "
        f"{xau[0][0] if xau else '-'}. PowerShell 5.1 se doc sai mot tep khong "
        f"BOM. Ngu canh: {canh!r}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
