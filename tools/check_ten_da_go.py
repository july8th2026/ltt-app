"""check_ten_da_go.py - chan TEN DA GO moc lai trong tai lieu song va chu thich LLM.

    python tools\\check_ten_da_go.py            # kiem, so voi moc (gate chay the nay)
    python tools\\check_ten_da_go.py --tu-kiem  # chi tu kiem bo do
    python tools\\check_ten_da_go.py --accept   # ghi lai moc (khi da DON bot dong cu)

================================================================================
CAI NAY CANH GI

Ngay 17/09 (L-23, Phuong an C) mot loat ten bi go: `ngan_sach.LE`,
`SO_SLOT_MAY_B`, `DONG_THOI_MAY_B`, `POOL_KV*`, `SO_SLOT`, `LE_NGU_CANH`, header
`X-LTT-Whale`, env `LTT_LLM_{NGUONG_WHALE,DEM_DAT_TRUOC,TOKEN_MOI_ANH,
MAX_INPUT_TOKENS,MAX_DONG_THOI,TOKEN_POOL,RPM}`, `luat_cho(pool, ...)`,
`dem_dat_truoc`, `token_moi_anh`. Sau do (L-24/L-25, O-19, hop dong 16/09):
`--no-cache-idle-slots`, `--cache-ram 8192/12288`, san RAM 48 cua cong LLM,
"canonical integrator", "vong lap la `gate.py --doi`".

Ban ra 18/09 tim thay cac ten nay CON SONG trong tai lieu ma nguoi sau doc DE
LAM (ban do, runbook, hop dong, chu thich ma) - khong danh dau gi. Mot ten da go
ma van nam trong ban do thi nguoi doc se di tim no, hoac te hon, dat lai no.

================================================================================
NO KHONG CANH GI

⛔ Lich su. Nhat ky, luu tru, artifacts va anh chup co ngay DUOC nhac ten cu -
   do la su that da xay ra. Pham vi quet la mot danh sach NGAN cac tep song
   (`PHAM_VI_TEP`, `PHAM_VI_MA`), khong phai ca kho.
⛔ Dong da danh dau. Dong chua `ĐÃ GỠ` / `ĐÃ THAY` / `~~` / `Gỡ:` (va 3 dong
   sau no) la dong DANG NOI rang ten ay da go - bat no la phat dung cau dinh
   chinh.
⛔ "Muc effort cua 3.5" (L-26: 3.5 khong co muc) khong co dang chuoi co dinh de
   bat - khong o trong bang. Van xuoi thi test_1249 khong doc (xem dau tep ay).

================================================================================
BANH COC

Kho hom nay con nhieu dong cu hop ly (vd `llm_gateway/` canh bao luc khoi dong
khi env da go van con dat). Nen bo do chot TAP HOP dong vi pham (tep, ten, van
ban dong - KHONG theo so dong, so dong troi) vao `check_ten_da_go.moc`, va chi
DO khi co dong MOI ngoai moc. Chot tap hop chu khong chot so luong: xoa mot dong
cu roi them mot dong moi thi tong khong doi ma van phai do.
Dong cu duoc don thi moc khong tu co lai - bo do nhac chay `--accept`.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOC = Path(__file__).with_name("check_ten_da_go.moc")

#: MOT bang ten da go duy nhat: (ten hien thi, mau regex tren van ban DA BO DAU,
#: co khong phan biet hoa thuong, mau xau de tu kiem).
#:
#: ⚠️ Mau chay tren `khong_dau(dong)`: bo dau tieng Viet khong doi dinh danh ma,
#:    nhung cho mau "vong lap la ..." viet mot lan cho ca hai cach go.
TEN_DA_GO: tuple[tuple[str, str, bool, str], ...] = (
    ("LE", r"`LE`|\bngan_sach\.LE\b|^\s*LE\s*[:=]", False,
     "Tran vao = cua so - ra - `LE`."),
    ("SO_SLOT_MAY_B", r"\bSO_SLOT_MAY_B\b", False, "doc `SO_SLOT_MAY_B`"),
    ("DONG_THOI_MAY_B", r"\bDONG_THOI_MAY_B\b", False, "bi danh DONG_THOI_MAY_B"),
    ("POOL_KV", r"\bPOOL_KV\w*", False, "`POOL_KV_MAY_B` = -c"),
    ("SO_SLOT", r"\bSO_SLOT\b", False, "`SO_SLOT` = -np"),
    ("LE_NGU_CANH", r"\bLE_NGU_CANH\b", False, "manifest.LE_NGU_CANH"),
    ("X-LTT-Whale", r"\bX-LTT-Whale\b", True, "header x-ltt-whale phia A"),
    ("LTT_LLM_NGUONG_WHALE", r"\bLTT_LLM_NGUONG_WHALE(?![A-Z0-9])", False,
     "env LTT_LLM_NGUONG_WHALE=8192"),
    ("LTT_LLM_DEM_DAT_TRUOC", r"\bLTT_LLM_DEM_DAT_TRUOC(?![A-Z0-9])", False,
     "LTT_LLM_DEM_DAT_TRUOC"),
    ("LTT_LLM_TOKEN_MOI_ANH", r"\bLTT_LLM_TOKEN_MOI_ANH(?![A-Z0-9])", False,
     "LTT_LLM_TOKEN_MOI_ANH"),
    ("LTT_LLM_MAX_INPUT_TOKENS", r"\bLTT_LLM_MAX_INPUT_TOKENS(?![A-Z0-9])", False,
     "LTT_LLM_MAX_INPUT_TOKENS=90000"),
    ("LTT_LLM_MAX_DONG_THOI", r"\bLTT_LLM_MAX_DONG_THOI(?![A-Z0-9])", False,
     "LTT_LLM_MAX_DONG_THOI__qwen35-api=3"),
    ("LTT_LLM_TOKEN_POOL", r"\bLTT_LLM_TOKEN_POOL(?![A-Z0-9])", False,
     "LTT_LLM_TOKEN_POOL"),
    ("LTT_LLM_RPM", r"\bLTT_LLM_RPM(?![A-Z0-9])", False, "LTT_LLM_RPM=120"),
    ("luat_cho(pool", r"\bluat_cho\(\s*pool\b", False, "luat_cho(pool, vao, ra)"),
    ("dem_dat_truoc", r"\bdem_dat_truoc\b", False, "so_theo_model.dem_dat_truoc"),
    ("token_moi_anh", r"\btoken_moi_anh\b", False, "tham so token_moi_anh"),
    ("--no-cache-idle-slots", r"--no-cache-idle-slots", False,
     "them --no-cache-idle-slots vao yaml"),
    ("cache-ram 8192/12288", r"cache-ram\s+(8192|12288)\b", False,
     "--cache-ram 12288 moi model"),
    ("san RAM LLM 48", r"\bLTT_LLM_RAM_TRONG_GB\s*=\s*48\b", False,
     "LTT_LLM_RAM_TRONG_GB=48"),
    ("canonical integrator", r"canonical\s+integrator", True,
     "cho canonical integrator gop main"),
    ("vong lap la gate --doi", r"vong\s+lap\s+la\W*(python\s+tools[\\/])?gate(\.py)?\s+--doi",
     True, "Cong: vòng lặp là `gate.py --doi`."),
)

#: Mau TOT: dong phai KHONG bi bat (ten hien hanh giong ten da go).
MAU_TOT = (
    # 28/09: `token_giu_moi_anh` NAY LA TEN DA GO (xem TEN_DA_GO duoi). Dong nay
    # giu lai LAM MAU TOT vi no la mot cau TAI LIEU ve lich su, khong phai mot
    # noi goi - va phep kiem phai phan biet duoc hai thu do.
    "`HO_SO[m].token_giu_moi_anh` = 2048",
    "`LTT_ADMISSION_POOL__ltt_35_5060` chi HA duoi ban khai",
    "`LTT_LLM_SO_LAN_XEP_LAI` (3)",
    "`--cache-ram 24576` moi model, san `LTT_LLM_RAM_TRONG_GB=24`",
    "LE THI HOA (ten nguoi, khong phai hang so)",
    "`DEM_UOC` thay cho hang cu",
    "Phien tu gop `main` (hop dong §7).",
    "⛔ **ĐÃ GỠ (L-23)** `SO_SLOT_MAY_B`",
    "~~`LTT_LLM_MAX_DONG_THOI=1`~~",
)

#: Pham vi: tai lieu SONG ma nguoi sau doc de lam. Danh sach NGAN co chu y.
PHAM_VI_TEP = (
    "CLAUDE.md",
    "AGENTS.md",
    "docs/00_BAT_DAU_TU_DAY.md",
    "docs/00_LTT_OPERATING_CONTRACT.md",
    "docs/ltt_llm_dual/BAN_DO_DUONG_DI.md",
    "docs/ltt_llm_dual/RUNBOOK.md",
    "docs/ltt_llm_dual/README.md",
    # Plan hien hanh cua duong LLM (18/09). Doi plan thi doi dong nay.
    "docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md",
    "docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md",
    "docs/VLM_NOI_BO/CAM_CLI.md",
)
#: Chu thich (va ma) trong ba thu muc cua duong LLM.
PHAM_VI_MA = ("apps/ltt_llm/", "platform_core/llm/", "llm_gateway/")

#: Duong dan mien (lich su) - ap ca khi mot tep lot vao pham vi.
MIEN_DUONG = ("_luutru/", "NHAT_KY", "artifacts/")

#: Dau danh dau "dong nay dang noi ten ay DA GO" (tren van ban da bo dau).
DANH_DAU = re.compile(r"DA GO\b|DA THAY\b|~~|\bGo:")
SO_DONG_SAU_DANH_DAU = 3

#: Anh chup co ngay o dau tep ("Ảnh chụp 13/09") => ca tep la lich su.
ANH_CHUP = re.compile(r"anh chup\W*\d{1,2}/\d{1,2}", re.I)

_MAU = [(ten, re.compile(m, re.I if khong_hoa else 0))
        for ten, m, khong_hoa, _x in TEN_DA_GO]


@dataclass(frozen=True)
class Hit:
    tep: str
    ten: str
    dong: str

    def khoa(self) -> str:
        # Khoa theo van ban dong, KHONG theo so dong (so dong troi moi lan sua).
        return f"{self.tep}::{self.ten}::{' '.join(self.dong.split())[:160]}"


def khong_dau(s: str) -> str:
    """Bo dau tieng Viet de mot mau bat duoc ca hai cach viet."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").replace("đ", "d") \
                                                      .replace("Đ", "D")


def la_anh_chup(text: str) -> bool:
    return bool(ANH_CHUP.search(khong_dau("\n".join(text.splitlines()[:15]))))


def quet_van_ban(tep: str, text: str) -> list[Hit]:
    """Tra ve cac dong nhac ten da go ma KHONG duoc danh dau."""
    ra: list[Hit] = []
    mien_toi = -1
    for i, raw in enumerate(text.splitlines()):
        d = khong_dau(raw)
        if DANH_DAU.search(d):
            mien_toi = i + SO_DONG_SAU_DANH_DAU
            continue
        if i <= mien_toi:
            continue
        for ten, mau in _MAU:
            if mau.search(d):
                ra.append(Hit(tep, ten, raw.strip()))
    return ra


def cac_tep() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    ra = []
    for t in out.splitlines():
        if any(m in t for m in MIEN_DUONG):
            continue
        if t in PHAM_VI_TEP or (t.endswith(".py")
                                and t.startswith(PHAM_VI_MA)):
            ra.append(t)
    return sorted(ra)


def quet_kho() -> list[Hit]:
    ra: list[Hit] = []
    for tep in cac_tep():
        try:
            text = (ROOT / tep).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if tep.endswith(".md") and la_anh_chup(text):
            continue
        ra += quet_van_ban(tep, text)
    return ra


def doc_moc() -> set[str]:
    if not MOC.is_file():
        return set()
    return {d for d in MOC.read_text(encoding="utf-8").splitlines()
            if d and not d.startswith("#")}


def so_voi_moc(hits: list[Hit], moc: set[str]) -> list[str]:
    """Khoa MOI (ngoai moc). Chot tap hop: hoan doi mot-doi-mot van ra khac rong."""
    return sorted({h.khoa() for h in hits} - moc)


def ghi_moc(hits: list[Hit]) -> None:
    dong = ["# check_ten_da_go - tap dong nhac ten da go (banh coc).",
            "# Sinh boi `python tools\\check_ten_da_go.py --accept`. Khoa: tep::ten::dong.",
            *sorted({h.khoa() for h in hits})]
    # newline="\n": tren Windows write_text doi \n thanh \r\n (bay da gap).
    with open(MOC, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")


def tu_kiem() -> int:
    """Moi ten co mau xau bi bat; mau tot khong bi bat; danh dau mien dung."""
    loi = 0
    for ten, _m, _k, xau in TEN_DA_GO:
        if ten not in {h.ten for h in quet_van_ban("x.md", xau)}:
            print(f"  [tu-kiem] BO SOT {ten!r}: {xau}")
            loi += 1
    for tot in MAU_TOT:
        if quet_van_ban("x.md", tot):
            print(f"  [tu-kiem] BAO NHAM: {tot}")
            loi += 1
    print(f"[tu-kiem] {len(TEN_DA_GO)} ten + {len(MAU_TOT)} mau tot"
          f" -> {'OK' if not loi else str(loi) + ' SAI'}")
    return loi


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tu-kiem", action="store_true")
    p.add_argument("--accept", action="store_true",
                   help="ghi lai moc = tap hien tai (chi khi da DON bot)")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        # Duoi gate stdout la ong dan -> cp1252 tren Windows; dong trich co dau.
        sys.stdout.reconfigure(errors="backslashreplace")

    if tu_kiem():
        print("RESULT: FAIL - bo do sai, dung tin ket qua quet")
        return 1
    if a.tu_kiem:
        return 0

    hits = quet_kho()
    if a.accept:
        ghi_moc(hits)
        print(f"Da ghi moc: {len({h.khoa() for h in hits})} dong")
        return 0

    moc = doc_moc()
    moi = so_voi_moc(hits, moc)
    da_don = sorted(moc - {h.khoa() for h in hits})
    print(f"[ten da go] {len(cac_tep())} tep trong pham vi | "
          f"{len({h.khoa() for h in hits})} dong cu | moc {len(moc)}")
    if moi:
        print(f"[ten da go] {len(moi)} dong MOI nhac ten da go (L-23/L-25/hop dong):")
        for k in moi:
            print(f"  {k}")
        print()
        print("  Doi sang ten hien hanh (`ngan_sach.HO_SO[m]`, DECISION_LOG L-23..L-28),")
        print("  hoac danh dau dong la lich su (`ĐÃ GỠ`/`ĐÃ THAY`/`~~`).")
        print("RESULT: FAIL")
        return 1
    if da_don:
        print(f"[ten da go] {len(da_don)} dong cu da duoc don - chay `--accept` de thu moc.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
