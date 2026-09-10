"""check_luat_van_hanh.py - chan luat VAN HANH moc lai ngoai hop dong canonical.

    python tools\\check_luat_van_hanh.py
    python tools\\check_luat_van_hanh.py --tu-kiem

================================================================================
CAI NAY CANH GI

Sau 2026-09-08 kho co DUNG MOT nguon luat quy trinh:

    CLAUDE.md  ->  docs/00_LTT_OPERATING_CONTRACT.md  ->  cong cu gate/test

Truoc do, cadence duoc CHEP LAI trong 10 tep ke hoach, va 5 ban chep KHONG
giong nhau: `--vong-lap` sau moi lan sua · `--doi` trong vong lap ·
`test_nhanh --lf` sau moi lan sua · mot tap bat bien rieng sau moi edit ·
`test_nhanh.py` ROI `gate.py` (tra tien hai lan cho cung mot cau tra loi).

Moi phien them mot ban chep. Khong ai co y lam sai; cai sai la **khong co cho
nao de tra loi**, nen ai can mot cadence thi tu viet mot cai.

================================================================================
NO KHONG CANH GI - VA DAY LA PHAN KHO

⛔ Mot tai lieu NHAC TOI `gate.py` khong phai mot luat. Kho nay co hang tram
   dong BANG CHUNG dang "da chay `gate.py`, PASS 23/23". Bat theo chuoi
   `gate.py` la bat ca kho.

⇒ Chi bao dong khi mot dong vua co MENH LENH CADENCE (`sau moi lan sua`,
  `after every edit`, `luon chay`) VUA co mot LENH TEST. Hai thu canh nhau moi
  la mot luat; mot minh thi khong.

⛔ Va bo do nay TU NO la mot tep noi ve cadence. Neu no quet chinh no, hoac quet
   tai lieu giai thich no, no se bao dong tren dung doan van giai thich no -
   loi da xay ra that trong kho nay voi mot bo do khac. Nen `CHO_PHEP` ton tai,
   va `--tu-kiem` chung minh bo do con phan biet duoc dung/sai.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Nguon luat van hanh HOP LE. Chi nhung tep nay duoc dinh nghia cadence.
#:
#: ⛔ Danh sach nay phai NGAN. Moi muc them vao la mot noi thu hai co the dinh
#:    nghia cung mot thu - tuc dung cai benh ma tep nay sinh ra de chua.
CHO_PHEP = (
    "CLAUDE.md",
    "AGENTS.md",
    "docs/00_LTT_OPERATING_CONTRACT.md",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "docs/QUY_TAC_CHAY_LENH_NANG.md",
    "docs/16_CAP_NHAT_VA_DEPLOY.md",
    "docs/BAY_TRONG_CONG_CHAT_LUONG.md",
    "docs/OPERATING_STANDARDIZATION/",
)

#: Menh lenh cadence: "lam viec nay SAU MOI lan/thay doi", "LUON chay".
#: NO CU DA BIET — chot TAP HOP, khong chot SO LUONG.
#:
#: 🔴 Vi sao tap hop chu khong phai mot con so: mot bo dem cho phep "van 1 loi"
#:    se xanh khi mot phien XOA dong cu va THEM mot dong moi te hon. Chot tap
#:    hop thi bat duoc ca hai chieu. Luat cua kho — xem memory *banh coc*.
#:
#: ⚠️ Khoa theo (tep, van ban dong), KHONG theo so dong: so dong troi ngay khi
#:    ai do them mot doan phia tren.
#:
#: Moi muc phai co CHU va LY DO. Khong co muc nao duoc o day "tam thoi" ma
#: khong ai chiu trach nhiem.
#: ⭐ RONG tu 2026-09-08 15:55, va do la trang thai DUNG.
#:
#:    Muc duy nhat tung nam o day (`docs/CHATLTT_V3/00_KE_HOACH_V3.md`) duoc
#:    hoan vi worktree `claude/chatltt-v3-agentic` dang song. Do lai sau do:
#:    phien ay **khong chay**, va tep giong het nhau tren ca ba nhanh
#:    (`git rev-parse <nhanh>:<tep>` cho cung mot bam) — tuc khong ai dang sua
#:    no, nen sua o day khong tao xung dot cho ai. Ly do hoan khong con.
#:
#: ⚠️ Doan nay giu lai **khong phai** vi bang trong can chu thich, ma vi luat
#:    "chot TAP HOP, khong chot SO LUONG" chi doc duoc khi ta con thay mot vi du
#:    ve cach mot muc duoc them va duoc go.
NO_CU: dict[str, str] = {}

CADENCE = re.compile(
    r"sau\s+(moi|moi\s+mot|mot)\s+(lan|lo|cum|buoc)\s*(sua|thay\s*doi|edit)?"
    r"|sau\s+moi\s+thay\s*doi"
    r"|sau\s+moi\s+sua"
    r"|after\s+(every|each)\s+(edit|change|commit)"
    r"|luon\s+chay"
    r"|always\s+run",
    re.I,
)

#: Mot LENH test/gate that su.
#:
#: ⚠️ `\bgate\b` tran chu khong chi `gate\.py`: `--tu-kiem` bat duoc dung cho nay
#:    ngay luot chay dau (mau "Luon chay gate day du truoc khi commit" lot luoi).
#:    An toan vi bao dong doi CA BA mau khop - mot dong noi ve gate ma khong co
#:    menh lenh cadence thi van im.
LENH = re.compile(r"gate\.py|test_nhanh\.py|pytest|\bgate\b", re.I)

#: "Chay ca bo" - de phan biet mot luat TOAN CUC voi mot luat hep.
TOAN_BO = re.compile(
    r"full\s+(gate|pytest|suite)|gate\s+day\s+du|day\s+du|toan\s+bo|--vong-lap"
    r"|--quick|--lf|toan\s+kho",
    re.I,
)


def khong_dau(s: str) -> str:
    """Bo dau tieng Viet de mot mau bat duoc ca hai cach viet."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").replace("đ", "d") \
                                                      .replace("Đ", "D")


#: Dau hieu mot dong la BANG CHUNG (ghi lai mot luot da chay) chu khong phai
#: MENH LENH. Mot phan quyet (`PASS 20`), mot phep chon hep (`-k ...`), hay mot
#: o bang ket qua deu noi "day la thu da xay ra", khong noi "hay lam thu nay".
BANG_CHUNG = re.compile(
    # ⚠️ Mui ten Unicode phai co MAT o day. `khong_dau()` bo dau thanh, no
    #    KHONG doi `→` thanh `->`; thieu chung thi mot dong nhat ky dung
    #    mui ten dep van bi bat (do that 08/09: `docs/NHAT_KY.md:403`).
    r"\bPASS\b|\bFAIL\b|passed|failed|skipped|\bOK\b|RESULT:"
    r"|->|=>|→|⇒|⟶"
    r"|\s-k\s",
    re.I,
)


#: Dau hieu mot dong CAM lam viec gi, hoac KE LAI mot luat da bo. Ca hai deu
#: nhac toi cadence ma khong RA LENH cadence nao.
#:
#: 🔴 Vi sao phai co. Luot chay 08/09 sau khi don xong con 4 bao dong, va **ba
#:    trong bon la chinh cau CAM** vua duoc viet de thay luat cu:
#:        "⛔ Dung chay `test_nhanh.py` truoc no."
#:        "*(Truoc 2026-09-08 dong nay bao goi thang `test_nhanh --lf` ...)*"
#:    Mot bo do trung phat dung doan van giai thich no thi khong ai giu no lau.
CAM_HOAC_LICH_SU = re.compile(
    r"⛔|dung\s+chay|dung\s+goi|khong\s+(chay|goi|duoc|phai|con)"
    r"|do\s+not|don't|never\s+run|no\s+longer"
    r"|truoc\s+20\d\d-\d\d-\d\d|tu(ng)?\s+ghi|von\s+la|da\s+bo|thay\s+luat"
    r"|used\s+to|until\s+20\d\d",
    re.I,
)


def la_bang_chung(dong_khong_dau: str) -> bool:
    """Dong nay MO TA (bang chung / cam doan / lich su) chu khong RA LENH?

    ⚠️ Gioi han da biet: mot luat that phat bieu bang phu dinh kep — vi du
       "Khong duoc bo qua: sau moi lan sua phai chay gate day du" — se LOT.
       Chap nhan co y: bao nham tren moi cau cam se lam bo do bi tat, va mot bo
       do bi tat bat duoc 0 luat. Xem muc "NO KHONG CANH GI" o dau tep.
    """
    return bool(BANG_CHUNG.search(dong_khong_dau)
                or CAM_HOAC_LICH_SU.search(dong_khong_dau))


def duoc_phep(duong: str) -> bool:
    d = duong.replace("\\", "/")
    return any(d == c or d.startswith(c) for c in CHO_PHEP)


def quet_van_ban(text: str) -> list[tuple[int, str, str]]:
    """Tra ve [(so_dong, ly_do, dong)]. Tach rieng de `--tu-kiem` goi duoc."""
    ra: list[tuple[int, str, str]] = []
    dong = text.splitlines()
    for i, raw in enumerate(dong, 1):
        d = khong_dau(raw)
        if (CADENCE.search(d) and LENH.search(d) and TOAN_BO.search(d)
                and not la_bang_chung(d)):
            ra.append((i, "cadence toan cuc", raw.strip()))
            continue
        # `test_nhanh.py` ROI `gate.py` = tra tien hai lan: buoc `bo test` ben
        # trong gate CHINH LA `test_nhanh.py` (tools/gate.py:844).
        #
        # ⛔ CHI khi ca hai dong deu la MENH LENH. Do that 08/09: ban dau mau nay
        #    bao dong 11 lan tren `docs/NHAT_KY.md` - toan la dong BANG CHUNG
        #    ("| test_nhanh.py --noi-tiep -k ... | PASS 20 |"). Mot bang ghi lai
        #    thu da chay khong ra lenh cho ai ca, va bat no la dung cai loi ma
        #    muc "NO KHONG CANH GI" o dau tep noi toi.
        if "test_nhanh.py" in d and not la_bang_chung(d):
            for ke_raw in dong[i:i + 3]:
                ke = khong_dau(ke_raw)
                if re.search(r"gate\.py", ke) and not la_bang_chung(ke):
                    ra.append((i, "chay pytest hai lan", raw.strip()))
                    break
    return ra


def cac_tep_md() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [t for t in out.splitlines()
            if t and not t.startswith("docs/_luutru/")]


MAU_XAU = [
    "Sau moi lan sua chay `python tools\\gate.py` day du.",
    "After every edit, run the full pytest suite.",
    "Luon chay gate day du truoc khi commit.",
]
MAU_TOT = [
    "Da chay `python tools/gate.py` -> RESULT: PASS 23/23.",
    "Buoc nay chay `pytest tests/test_334.py` de chot ngan sach.",
    "`gate.py --doi` la vong lap mac dinh; xem hop dong van hanh.",
    "Gate la cong cu ra phan quyet, khong phai cong cu chan doan.",
    # Bang BANG CHUNG - 11 dong kieu nay o `docs/NHAT_KY.md` da bi bao nham
    # o luot chay dau ngay 08/09.
    "| `python tools\\test_nhanh.py --noi-tiep -k \"test_325\"` | **PASS 20** |",
    "| `python tools\\gate.py --quick` | **PASS 12/12** (sau moi lan sua) |",
    # Cau CAM va cau KE LICH SU - ba dong kieu nay da bi bao nham ngay 08/09,
    # va ca ba deu la van ban vua viet ra de THAY luat cu.
    "Dung chay `test_nhanh.py` truoc no; buoc `bo test` ben trong gate la no.",
    "Do not run `test_nhanh.py` and then `gate.py` - the gate already runs it.",
    "(Truoc 2026-09-08 dong nay bao goi `test_nhanh.py --lf` sau moi lan sua.)",
]


def tu_kiem() -> int:
    """Bo do phai phan biet duoc mot LUAT voi mot BANG CHUNG."""
    loi = 0
    for m in MAU_XAU:
        if not quet_van_ban(m):
            print(f"  [tu-kiem] BO SOT (phai bat): {m}")
            loi += 1
    for m in MAU_TOT:
        if quet_van_ban(m):
            print(f"  [tu-kiem] BAO NHAM (phai bo qua): {m}")
            loi += 1
    print(f"[tu-kiem] {len(MAU_XAU)} mau xau + {len(MAU_TOT)} mau tot"
          f" -> {'OK' if not loi else str(loi) + ' SAI'}")
    return loi


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tu-kiem", action="store_true",
                   help="chi chay tu kiem cua chinh bo do")
    args = p.parse_args()

    if tu_kiem():
        print("RESULT: FAIL - bo do sai, dung tin ket qua quet")
        return 1
    if args.tu_kiem:
        return 0

    moi: list[str] = []
    da_thay: set[str] = set()
    tep_md = cac_tep_md()
    for tep in tep_md:
        if duoc_phep(tep):
            continue
        try:
            text = (ROOT / tep).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for so, ly_do, dong in quet_van_ban(text):
            if tep in NO_CU:
                da_thay.add(tep)
                continue
            moi.append(f"  {tep}:{so}  [{ly_do}]\n      {dong[:120]}")

    # ⛔ Chieu con lai cua banh coc: mot muc NO_CU da duoc don thi phai GO khoi
    #    bang, khong duoc de lai. Mot bang no cu khong bao gio ngan di la mot
    #    bang khong ai doc nua.
    da_don = sorted(set(NO_CU) - da_thay)

    if moi:
        print(f"[luat van hanh] {len(moi)} luat quy trinh MOI nam NGOAI hop dong:")
        for d in moi:
            print(d)
        print()
        print("  Cadence chi duoc dinh nghia o docs/00_LTT_OPERATING_CONTRACT.md.")
        print("  Xoa luat o cac tep tren, hoac tro chung ve hop dong.")
        print("RESULT: FAIL")
        return 1

    if da_don:
        print("[luat van hanh] no cu DA DUOC DON - go chung khoi `NO_CU`:")
        for t in da_don:
            print(f"  {t}")
        print("RESULT: FAIL")
        return 1

    print(f"[luat van hanh] {len(tep_md)} tep .md - khong co cadence canh tranh "
          f"moi ngoai hop dong ({len(NO_CU)} no cu da biet)")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
