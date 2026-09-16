"""hook_khong_dung_giua_pha.py — Stop hook: chan viec DUNG khi ke hoach con viec.

## Vi sao no ton tai

Hop dong §10b ("khong dung giua cac pha") la mot cau VAN BAN. Van ban khong
cuong che duoc gi: chinh kho nay da ghi bai hoc *"luat viet ra khong mien nhiem
cho nguoi viet - co hoc thang loi van"*. Tep nay la phan CO HOC cua luat do:
harness chay no, khong phai Claude, nen no khong quen duoc.

## Co che

Stop hook duoc goi khi Claude dinh ket thuc luot. Neu no in ra

    {"decision": "block", "reason": "..."}

thi luot KHONG ket thuc, va `reason` duoc dua lai cho Claude nhu mot chi dan.

## ⛔ DIEU KIEN DUNG - phan quan trong nhat cua tep nay

Mot Stop hook chan vo dieu kien la mot vong lap vo han dot token. Nen o day co
BA cua thoat doc lap, va chi can MOT cua mo la luot duoc ket thuc:

  1. **Khong co tep ke hoach** (`.claude/pha_dang_chay.json`) -> cho dung.
     Day la mac dinh: khong khai ke hoach thi hook khong lam gi ca.
  2. **Het viec** (`con_lai` rong) -> cho dung, va xoa tep.
  3. **Cham tran** (`so_lan_chan >= tran`, mac dinh 12) -> cho dung kem canh bao.
     Tran nay bao ve khi Claude ket lai ma khong tick duoc viec nao - tuc khi
     chinh co che nay khong con giup duoc gi nua.

⭐ Va mot cua thu tu do harness giu: `stop_hook_active`. Claude Code dat co nay
   khi luot hien tai DA bi mot Stop hook chan roi; ta ton trong no de hai lop
   chong lap khong nhan nhau.

## Nguoi dung tat bang cach nao

Xoa `.claude/pha_dang_chay.json`. Mot co che khong tat duoc bang mot hanh dong
don gian la mot co che se bi tat bang cach go ca hook.

## Dinh dang tep ke hoach

    {
      "muc_tieu": "L-01 -> L-05 + cong D..Q",
      "con_lai": ["do nguong max_tokens (L-02)", "L-04", "cong G"],
      "so_lan_chan": 0,
      "tran": 12
    }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEN_TEP = "pha_dang_chay.json"
TRAN_MAC_DINH = 12


def _tep_ke_hoach() -> Path:
    """`.claude/pha_dang_chay.json` canh tep nay (goc kho / goc worktree)."""
    return Path(__file__).resolve().parents[1] / ".claude" / TEN_TEP


def _cho_dung() -> int:
    """Khong in gi -> harness hieu la 'khong can thiep'."""
    return 0


def main() -> int:
    try:
        vao = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return _cho_dung()          # doc khong duoc thi KHONG chan

    # Cua 4: harness da bao luot nay bi chan roi.
    if vao.get("stop_hook_active"):
        return _cho_dung()

    tep = _tep_ke_hoach()
    if not tep.is_file():
        return _cho_dung()          # Cua 1

    try:
        kh = json.loads(tep.read_text(encoding="utf-8"))
    except Exception as e:                                      # noqa: BLE001
        print(json.dumps({"systemMessage":
                          f"[khong-dung-giua-pha] {TEN_TEP} khong doc duoc "
                          f"({type(e).__name__}) - bo qua hook"}))
        return _cho_dung()

    con_lai = [str(x) for x in (kh.get("con_lai") or []) if str(x).strip()]
    if not con_lai:                                             # Cua 2
        try:
            tep.unlink()
        except OSError:
            pass
        print(json.dumps({"systemMessage":
                          "[khong-dung-giua-pha] ke hoach da het viec - "
                          "go tep, cho dung."}))
        return _cho_dung()

    so_lan = int(kh.get("so_lan_chan") or 0)
    tran = int(kh.get("tran") or TRAN_MAC_DINH)
    if so_lan >= tran:                                          # Cua 3
        print(json.dumps({"systemMessage":
                          f"[khong-dung-giua-pha] da chan {so_lan} lan (tran "
                          f"{tran}) ma ke hoach van con {len(con_lai)} viec. "
                          f"Cho dung de tranh vong lap - xem {TEN_TEP}."}))
        return _cho_dung()

    kh["so_lan_chan"] = so_lan + 1
    try:
        tep.write_text(json.dumps(kh, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    except OSError:
        return _cho_dung()          # khong ghi duoc bo dem thi KHONG chan

    ke = con_lai[0]
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"Ke hoach con {len(con_lai)} viec chua xong; hop dong "
            f"`docs/00_LTT_OPERATING_CONTRACT.md` §10b noi mot pha xong khong "
            f"phai mot diem xin phep.\n\n"
            f"VIEC KE TIEP: {ke}\n"
            f"Con lai: {', '.join(con_lai)}\n\n"
            f"Lam tiep viec do. Khi xong MOT viec, bo no khoi `con_lai` trong "
            f"`.claude/{TEN_TEP}` va dat lai `so_lan_chan` ve 0.\n"
            f"Neu that su phai dung (gate do, thao tac khong dao duoc, thay doi "
            f"khong ro cua ai, rui ro bao mat - bon dieu kien dung cua §10b), "
            f"hay XOA `.claude/{TEN_TEP}` roi ket luot va noi ro vi sao."
        ),
        "systemMessage": (f"[khong-dung-giua-pha] chan lan {so_lan + 1}/{tran} "
                          f"- con {len(con_lai)} viec, ke tiep: {ke}"),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
