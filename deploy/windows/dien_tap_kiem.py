"""dien_tap_kiem.py — phap doi chieu ben trong CSDL TAM cua dien tap khoi phuc.

Duoc goi BOI dien_tap_khoi_phuc.ps1 (KHONG chay thuan tay):

    python dien_tap_kiem.py --env-file <app.env> --db-name <ten CSDL tam>

Doc chuan xuat JSON mot dong vao stdout:
    {"kiem": [...], "du lieu": {...}, "het": true}

Ma xuat: 0 = tat ca kiem XANH, 1 = co kiem DO, 2 = loi mo truong (ket noi,
thieu bang). Chuan nhap co the chua bi mat (noi dung app.env) — chuc nang
nay CHIT in ten bien va ket qua, khong in gia tri.

Vai tro ve alembic: file nay CHIT doc version trong `alembic_version` cua CSDL
da nap va boc phao len (du_lieu["alembic_dump"]). Noi rap ve version va head
DO dien_tap_khoi_phuc.ps1 thuc hien — bang cach CHAY `alembic upgrade head`
len CSDL tam, vi mot ban sao lay truoc deploy hop ly o version cu hon head.
Vi vay khong co "kiem" nao o day so sanh version dump voi head (so sanh hinh
dang khong phai kiem duong khoi phuc).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# Chuoi ket noi doc DUng theo cach restore.ps1 (regex cung mot dang).
_RE_URL = re.compile(
    r"(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@"
    r"([^:/]+):(\d+)/(\S+)\s*$"
)

# Cac bang phai co trong dump (ten that tu platform_core/models.py).
BANG_PHAI_CO = [
    "users", "credit_entries", "jobs", "job_events", "upload_sessions",
    "api_keys", "payment_orders", "credit_packages", "app_access",
    "app_projects", "alembic_version",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env-file", required=True)
    p.add_argument("--db-name", required=True)
    a = p.parse_args()

    try:
        env_text = open(a.env_file, encoding="utf-8").read()
    except OSError as e:
        print(json.dumps({"het": False, "loi": f"khong doc duoc env file: {e!r}"}))
        return 2

    m = _RE_URL.search(env_text)
    if not m:
        print(json.dumps({"het": False, "loi": "khong tim thay LTT_DATABASE_URL"}))
        return 2
    user, pw, host, port, _live_db = m.groups()

    import psycopg
    try:
        conn = psycopg.connect(
            host=host, port=int(port), user=user, password=pw,
            dbname=a.db_name, connect_timeout=10,
        )
    except psycopg.Error as e:
        print(json.dumps({"het": False, "loi": f"ket noi that bai: {str(e)[:200]}"}))
        return 2

    kiem = []

    def them(ten, xanh, thong_tin):
        kiem.append({"ten": ten, "xanh": bool(xanh), "thong_tin": thong_tin})

    try:
        cur = conn.cursor()

        # --- 1. Bang co dat --------------------------------------------------
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        co = {r[0] for r in cur.fetchall()}
        thieu = [b for b in BANG_PHAI_CO if b not in co]
        them("bang_co_dat", not thieu,
             "thieu: " + (", ".join(thieu) if thieu else "khong") +
             f" (tong {len(co)} bang public)")

        du_lieu = {}
        if not thieu:
            # --- 2. So hang ---------------------------------------------------
            for b in ["users", "credit_entries", "jobs", "api_keys",
                      "job_events", "upload_sessions", "payment_orders",
                      "credit_packages"]:
                if b not in co:
                    continue
                cur.execute(f'SELECT count(*) FROM "{b}"')
                du_lieu[b] = cur.fetchone()[0]
            them("so_hang", True,
                 ", ".join(f"{k}={v}" for k, v in sorted(du_lieu.items())))

            # --- 3. Bien tan so sach (cong thuc so_du = SUM(delta)) ----------
            # CSDL KHONG co cot so-du luu: so_du la SUM(moi but toan) theo
            # credit.py:so_du. Nen bien tan kiem duoc la: (a) khong co but toan
            # noi lay den user khong ton tai (FK RESTRICT), (b) khong co user
            # co so du am (tru() khong cho phep so du am, hold chi giu trong
            # transaction).
            cur.execute(
                "SELECT count(*) FROM credit_entries ce "
                "LEFT JOIN users u ON u.id = ce.user_id WHERE u.id IS NULL")
            noi_lay = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM ("
                " SELECT user_id, sum(delta) AS s FROM credit_entries "
                " GROUP BY user_id HAVING sum(delta) < 0) x")
            so_du_am = cur.fetchone()[0]
            cur.execute(
                "SELECT coalesce(sum(delta),0) FROM credit_entries")
            tong_but_toan = cur.fetchone()[0]
            them("so_sach_ton_tai", noi_lay == 0,
                 f"but toan noi lay={noi_lay} (phai = 0)")
            them("so_du_khong_am", so_du_am == 0,
                 f"user co so du am={so_du_am} (phai = 0); "
                 f"tong but toan={tong_but_toan}")
            du_lieu["tong_but_toan"] = tong_but_toan

            # --- 4. Jobs co nguoi chua (FK job.user_id -> users) -------------
            cur.execute(
                "SELECT count(*) FROM jobs j "
                "LEFT JOIN users u ON u.id = j.user_id WHERE u.id IS NULL")
            job_noi_lay = cur.fetchone()[0]
            them("jobs_co_nguoi_chua", job_noi_lay == 0,
                 f"job noi lay={job_noi_lay} (phai = 0)")

            # --- 5. Alembic ----------------------------------------------------
            cur.execute("SELECT version_num FROM alembic_version")
            hang = cur.fetchall()
            du_lieu["alembic_dump"] = [r[0] for r in hang]

        cur.close()
        conn.close()
    except psycopg.Error as e:
        print(json.dumps({"het": False, "loi": f"truy van that bai: {str(e)[:300]}",
                          "du_lieu": du_lieu, "kiem": kiem}))
        return 2

    xanh_tat_ca = all(k["xanh"] for k in kiem)
    print(json.dumps({"het": True, "du_lieu": du_lieu, "kiem": kiem},
                     ensure_ascii=False))
    return 0 if xanh_tat_ca else 1


if __name__ == "__main__":
    sys.exit(main())
