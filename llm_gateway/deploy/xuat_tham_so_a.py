"""xuat_tham_so_a.py - in hai tham so CHINH SACH cua may A cho gateway.env may B.

    python llm_gateway\\deploy\\xuat_tham_so_a.py      (CHAY TREN MAY A, trong kho)

In ra dung hai dong `KEY=VALUE`:

    LTT_LLM_MAX_OUTPUT_TOKENS=<apps/ltt_llm/ngan_sach.TOKEN_RA_TRAN>
    LTT_LLM_DEM_UOC=<apps/ltt_llm/ngan_sach.DEM_UOC>

Vi sao (phuong an C buoc 3, `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` §3.2):
tran vao cua may B = `-c(yaml) - max_out - DEM_UOC`, CUNG cong thuc voi may A.
`-c` doc tu `llama-swap.yaml`; hai so con lai la CHINH SACH cua may A. `deploy.ps1`
tung GO TAY `LTT_LLM_MAX_INPUT_TOKENS=186368` - ban sao sai cho 3.5 (O-02). Nay no
goi tep nay va ghi DUNG so ngan_sach dang khai.

Mot tep .py chu khong `python -c` (CLAUDE.md luat 6: khong viet Python inline qua
PowerShell). Tep nay theo goi `llm_gateway` sang may B (scp -r) nhung KHONG chay o
do: may B khong co `apps/`.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _goc_kho() -> Path:
    """Goc kho = cha cua thu muc `llm_gateway`, neo bang TEN (AGENTS.md)."""
    for p in Path(__file__).resolve().parents:
        if p.name == "llm_gateway":
            return p.parent
    raise SystemExit("xuat_tham_so_a.py khong nam trong goi llm_gateway")


def tham_so() -> dict[str, int]:
    goc = _goc_kho()
    if str(goc) not in sys.path:
        sys.path.insert(0, str(goc))
    from apps.ltt_llm import ngan_sach as ns

    # Buoc 2 (may A) gom `LE` + `dem_dat_truoc` thanh `DEM_UOC` (ten cu da go).
    # Khong co la loi - KHONG doan mot so.
    dem = getattr(ns, "DEM_UOC", None)
    if not isinstance(dem, int) or dem <= 0:
        raise SystemExit("ngan_sach khong khai DEM_UOC nguyen duong")
    ra = int(ns.TOKEN_RA_TRAN)
    if ra <= 0:
        raise SystemExit("ngan_sach.TOKEN_RA_TRAN khong nguyen duong")
    return {"LTT_LLM_MAX_OUTPUT_TOKENS": ra, "LTT_LLM_DEM_UOC": int(dem)}


def main() -> int:
    for k, v in tham_so().items():
        print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
