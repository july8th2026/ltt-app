"""Tai ban GHIM cua MetricX-24 QE vao HF_HOME va kiem sha256. Chay lai an toan.

    set HF_HOME=C:\\LTTPlatform\\hf-cache
    C:\\LTTPlatform\\qc-venv\\Scripts\\python.exe apps\\asv_gpu\\do_luong\\_metricx\\tai.py

`--in-sha` in sha256 thuc cua moi tep (de chot vao phien_ban.json khi doi ban).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ban_ghim  # noqa: E402


def main() -> int:
    in_sha = "--in-sha" in sys.argv
    for muc in ("mo_hinh", "tokenizer"):
        tep = ban_ghim.tep_cuc_bo(muc, tai_ve=True)
        for ten, p in tep.items():
            if in_sha:
                print(muc, ten, ban_ghim.sha256(p))
            else:
                ban_ghim.kiem(p, ban_ghim.PHIEN_BAN[muc]["tep"][ten])
                print("OK", muc, ten)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
