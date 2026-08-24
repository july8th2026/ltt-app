"""kiem_import.py - chay TREN MAY B sau khi deploy, kiem moi thu import duoc.

    H:\\LTT_LLM\\venv\\Scripts\\python.exe H:\\LTT_LLM\\gateway\\llm_gateway\\deploy\\kiem_import.py

Vi sao la mot tep .py chu khong phai `python -c "..."` qua ssh: quy tac 3 cua
CLAUDE.md - PowerShell nuot dau ngoac kep khi truyen cho .exe, va qua mot lop ssh
nua thi hong chac chan. Da dinh mot lan trong phien nay.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Cho phep chay tu bat ky dau: neo vao thu muc `gateway` (cha cua `llm_gateway`).
GOC = Path(__file__).resolve().parent.parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def main() -> int:
    loi = []

    for ten in ("fastapi", "uvicorn", "httpx", "psutil"):
        try:
            __import__(ten)
        except ImportError as e:
            loi.append(f"thu vien thieu: {ten} ({e})")

    try:
        import llm_gateway
        import llm_gateway.api          # noqa: F401
        import llm_gateway.don_dep      # noqa: F401
        import llm_gateway.gia_token_khong_co_o_day  # noqa: F401
    except ImportError as e:
        # `gia_token` nam o platform_core tren MAY A, KHONG deploy sang may B:
        # may B khong biet gia, khong biet credit, khong biet nguoi dung (Q102).
        if "gia_token_khong_co_o_day" not in str(e):
            loi.append(f"llm_gateway khong import duoc: {e}")

    try:
        from render_gateway.busy import so_python_tinh_tren_gpu  # noqa: F401
    except ImportError as e:
        loi.append(f"render_gateway.busy khong import duoc: {e}")

    try:
        from llm_gateway.config import Config
        cfg = Config.from_env()
        print(f"  cau hinh: port={cfg.port} upstream={cfg.upstream_url} "
              f"models_mo={list(cfg.models_mo) or 'RONG (fail-closed)'}")
    except Exception as e:                                   # pragma: no cover
        loi.append(f"Config.from_env() hong: {type(e).__name__}: {e}")

    if loi:
        for d in loi:
            print(f"  [LOI] {d}")
        return 1

    print(f"  import OK - llm_gateway {llm_gateway.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
