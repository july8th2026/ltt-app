r"""
check_ps_bien_trung_tham_so.py — bien cuc bo trong .ps1 KHONG duoc trung ten mot
tham so cua chinh script do.

    python tools\check_ps_bien_trung_tham_so.py

## Vi sao co tep nay

PowerShell khong phan biet hoa thuong o ten bien, va tham so cua script chi la
mot bien binh thuong trong pham vi script. Nen mot vong lap gan `$ten` se **ghi
de** tham so `-Ten` — khong loi, khong canh bao, khong dau vet.

Da xay ra that ngay 31/08/2026 trong `setup/chay_thu_ghi_danh.ps1`: vong lap nap
`app.env` dat `$ten` cho tung ten bien moi truong, nen sau vong lap `$Ten` mang
gia tri `HF_HOME` — bien cuoi cung trong tep. Hai luot ghi danh lien tao ra giong
mang ten "HF_HOME", va luot thu hai chet vi rang buoc duy nhat `(owner_id, ten)`.

⭐ Vi sao mot phep kiem tinh chu khong phai "nho dat ten cho khac": no hong theo
   kieu khong ai nghi den. Nguoi doc thay `$ten` trong mot vong lap 3 dong va
   thay `$Ten` trong khoi `param()` cach do 30 dong, va **khong co gi noi chung
   la mot**. Chinh vi khoang cach do ma mat thuong khong bat duoc.

## Luat chinh xac: KHONG gan tham so BEN TRONG mot vong lap

⛔ Phep kiem nay khong doc duoc y dinh, nen no khong hoi "ban co dinh gan tham
   so khong". No hoi mot cau HEP hon va tra loi duoc: **co gan trong than mot
   vong lap khong.**

   Lan chay dau tien lam ro vi sao phai hep the. No bao do `setup/cai_dich_vu_giong.ps1`:

       if (-not $VenvRoot) { $VenvRoot = $env:LTT_VOICE_VENV_ROOT }

   Do la thanh nguoi ta dien GIA TRI MAC DINH cho mot tham so — dung han, va rat
   pho bien. Mot phep kiem bao dong o do se bi tat di trong mot tuan, va keo theo
   ca truong hop that.

⭐ Vong lap la thu tao ra khac biet. Loi that can SU LAP: `$ten` bi gan lai moi
   vong, nen sau vong lap no mang gia tri cua **luot cuoi**, chang lien quan gi
   toi thu tham so dinh mang. Ngoai vong lap, mot phep gan `$Ten = ...` nam ngay
   truoc mat va doc len dung nhu no lam.

   Nen: gan tham so ngoai vong lap = duoc. Trong vong lap = phai doi ten bien.
   That su muon doi tham so tu mot vong lap thi tinh vao mot bien khac roi gan
   mot lan sau khi vong lap ket thuc.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    # ⛔ `reconfigure`, KHÔNG phải `io.TextIOWrapper(sys.stdout.buffer, ...)`.
    #    Một wrapper mới NHẬN QUYỀN SỞ HỮU buffer bên dưới; khi nó bị thu
    #    gom rác — hoặc khi một module thứ hai bọc đè lên cùng buffer ấy —
    #    nó ĐÓNG buffer thật, và cả tiến trình chết với `ValueError: I/O
    #    operation on closed file` ở dòng `print` tiếp theo, một thông
    #    điệp không nhắc gì tới mã hoá hay tới module nào gây ra.
    #    `reconfigure()` sửa tại chỗ, gọi nhiều lần vô hại.
    #    Bánh cóc: `tests/test_353_voice_sidecar_bo_do.py`.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

GOC = Path(__file__).resolve().parents[1]
THU_MUC = ("setup", "deploy", "tools")

#: `[string]$Ten = '...'` hay `[int]$ChoGiay,` trong khoi param().
_THAM_SO = re.compile(r"^\s*(?:\[[^\]]+\]\s*)*\$([A-Za-z_]\w*)\s*(?:=|,|\)|$)")
#: Mot phep GAN. Khong tinh viec DOC `$ten`.
#:
#: 🔴 PHAI GOM CA `++`, `--`, `+=`, `-=`. Ban dau chi khop `$ten = ...`, va no
#:    bo sot mot lan tai dien cua DUNG con bug no sinh ra de bat:
#:    `setup/nap_credit_tai_khoan_thu.ps1` co tham so `-So` (so credit nap) va
#:    mot bo dem bien env `$so` tang bang `$so++` trong mot vong lap. PowerShell
#:    khong phan biet hoa thuong, nen `-So 100` bi ghi de thanh 70 (so bien da
#:    nap), va CONG CU GHI VAO SO CREDIT MOT BUT TOAN SAI SO — im lang, va so
#:    credit thi append-only.
_GAN = re.compile(r"^\s*\$([A-Za-z_]\w*)\s*(?:=[^=]|\+\+|--|\+=|-=)")

#: Mot lenh `if` co nhac toi bien — dau hieu cua mau DIEN MAC DINH hop le
#: (`if (-not $Repo) { $Repo = ... }`). Chi mau nay duoc mien.
# ⛔ KHONG neo `^`: doan nhin lui la vai dong da NOI LAI thanh mot chuoi, nen
#    `^` chi khop dau chuoi va mau mien tru khong bao gio no. Bang chung: no bao
#    dong nham `setup/cai_dich_vu_giong.ps1:42`, mot mau
#    `if (-not $VenvRoot) { $VenvRoot = ... }` hoan toan hop le.
_IF_NHAC = re.compile(r"(?:^|[\s}])(?:els)?if\s*\(", re.I)
#: Mo dau mot vong lap. `do` co than `{...}` truoc `while`/`until`.
_VONG_LAP = re.compile(r"(^|[^\w-])(foreach|for|while|do)\s*[({]", re.I)


def _tham_so(dong: list[str]) -> tuple[set[str], int]:
    """Ten tham so (thuong hoa) + dong ket thuc khoi `param(`."""
    ten, trong, sau = set(), False, 0
    for i, d in enumerate(dong):
        if not trong:
            if re.match(r"^\s*param\s*\(", d, re.I):
                trong = True
            continue
        if re.match(r"^\s*\)", d):
            return ten, i
        m = _THAM_SO.match(d)
        if m:
            ten.add(m.group(1).lower())
        sau = i
    return ten, sau


def kiem(tep: Path) -> list[str]:
    dong = tep.read_text(encoding="utf-8", errors="replace").splitlines()
    tso, het = _tham_so(dong)
    if not tso:
        return []
    loi, sau, muc_vong = [], 0, []
    for i, d in enumerate(dong[het + 1:], start=het + 2):
        tho = re.sub(r"#.*$", "", d)
        cho_vong = bool(_VONG_LAP.search(tho))

        m = _GAN.match(d)
        if m and m.group(1).lower() in tso:
            ten_b = m.group(1)
            # ⭐ MIEN mau DIEN MAC DINH: `if (-not $Repo) { $Repo = ... }`.
            #    Do la cach hop le de bo trong mot tham so khong duoc truyen.
            #    Nhan ra no bang cach nhin lui vai dong: mot `if` co nhac chinh
            #    bien ay. Moi phep gan KHAC deu la ghi de mot gia tri nguoi
            #    dung vua truyen vao.
            truoc = " ".join(dong[max(0, i - 4):i - 1])
            duoc_mien = (_IF_NHAC.search(truoc or "") is not None
                         and f"${ten_b.lower()}" in truoc.lower())
            if not duoc_mien:
                cho = "than vong lap" if muc_vong else "cap ngoai"
                loi.append(
                    f"{tep.relative_to(GOC)}:{i}: gan ${ten_b} o {cho} — trung "
                    f"ten tham so cua chinh script, va PowerShell KHONG phan "
                    f"biet hoa thuong, nen gia tri nguoi dung truyen vao bi xoa")

        # Dem ngoac SAU khi cham, de mot dong `foreach (...) {` tinh la mo vong.
        for c in tho:
            if c == "{":
                sau += 1
                if cho_vong:
                    muc_vong.append(sau)
                    cho_vong = False
            elif c == "}":
                if muc_vong and muc_vong[-1] == sau:
                    muc_vong.pop()
                sau = max(0, sau - 1)
    return loi


def main() -> int:
    loi = []
    for tm in THU_MUC:
        for tep in sorted((GOC / tm).rglob("*.ps1")):
            loi += kiem(tep)
    if loi:
        print("BIEN CUC BO TRUNG TEN THAM SO:")
        for d in loi:
            print(f"  {d}")
        print("\nDoi ten bien cuc bo. Xem docstring cua tep nay.")
        return 1
    print("[OK] khong tep .ps1 nao ghi de len tham so cua chinh no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
