"""
nghiem_thu_anh_e2e.py — nghiệm thu `image.ltt` **từ ngoài vào**, qua Cloudflare. (H37/G10, C4)

    python tools\\nghiem_thu_anh_e2e.py chuan_bi --token-file C:\\tmp\\anh_tok.txt
    python tools\\nghiem_thu_anh_e2e.py chay     --token-file C:\\tmp\\anh_tok.txt
    python tools\\nghiem_thu_anh_e2e.py don

⭐ VÌ SAO KHÔNG DÙNG `api_prod_canary.py`. Khoá của canary cố ý **không** có
   `jobs:create` — nó là canary chỉ-đọc, và docstring của nó nói rõ rằng cho
   đường tạo job chạy trên production "chỉ để lấy số" là tiêu tiền thật cho một
   phép đo không đòi.

   Việc này thì **đòi đúng điều đó**. Đường ảnh **chưa từng** chạy thật từ ngoài
   vào bao giờ, và H38 đã dạy vì sao điều đó không thay được bằng test: 739 test
   xanh vẫn để lọt lỗi `VARCHAR(36)` tới đúng lượt gọi thật đầu tiên, vì SQLite
   không ép độ dài mà PostgreSQL thì ép.

⛔ NÊN KHOÁ NÀY TIÊU ĐƯỢC TIỀN, và đó là chủ ý. Ba hàng rào bù lại:

     ① tài khoản RIÊNG (`EMAIL` dưới đây), không phải admin;
     ② nạp đúng `CREDIT` credit — đủ vài lượt, không đủ để một vòng lặp hỏng
        tiêu hết tiền thật;
     ③ `allowed_tools` chỉ có `image.ltt`. Khoá này không gọi được gì khác.

   Và `don` thu hồi khoá. Chạy nó khi xong.

⚠️ ĐI QUA ĐỊA CHỈ CÔNG KHAI, không loopback. Loopback bỏ qua Cloudflare, mà
   Cloudflare là nơi lỗi 403-vì-User-Agent và 524-vì-timeout xuất hiện — hai thứ
   đã dính thật ở H38.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import sys
import time

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

BASE = "https://app.lttstudios.com"
EMAIL = "nghiemthu-anh@lttstudios.local"
CREDIT = 30                       # ~10 lượt t2i mot anh o gia 3 credit
TOOL = "image.ltt"
UA = "ltt-nghiem-thu-anh/1.0"     # KHONG de urllib/httpx mac dinh: CF tra 403


def _nap_env() -> None:
    """Đọc `secrets\\app.env` vào `os.environ`. Bản chạy đọc env, không đọc tệp."""
    import os

    tep = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")
    if not tep.exists():
        raise SystemExit(f"khong thay {tep} — day khong phai may chu?")
    for dong in tep.read_text(encoding="utf-8-sig").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#") and "=" in dong:
            k, _, v = dong.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _phien():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


def _tim(db):
    from platform_core.models import User
    import sqlalchemy as sa
    return db.execute(sa.select(User).where(User.email == EMAIL)).scalars().first()


def chuan_bi(a) -> int:
    from platform_core import credit
    from platform_core.public_api import keys as devkeys
    from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                                 SCOPE_CREDITS_READ,
                                                 SCOPE_JOBS_CREATE,
                                                 SCOPE_JOBS_READ,
                                                 SCOPE_TOOLS_READ)
    from platform_core.users import tao_nguoi_dung

    gen, db = _phien()
    try:
        user = _tim(db)
        if user is None:
            user = tao_nguoi_dung(
                db, email=EMAIL, password=secrets.token_urlsafe(32),
                display_name="Nghiem thu anh E2E", role="user", is_verified=True)
            db.flush()
            print(f"da tao tai khoan {EMAIL}")
        else:
            user.is_active = True
            print(f"dung lai tai khoan co san {EMAIL}")

        so_du = credit.so_du(db, user.id)
        if so_du < CREDIT:
            credit.cap_tay(db, user.id, CREDIT - so_du, by="nghiem-thu-anh",
                           note="H37/G10 C4")
            print(f"credit: {so_du} -> {credit.so_du(db, user.id)}")
        else:
            print(f"credit da du: {so_du}")

        key, token = devkeys.issue(
            db, user_id=user.id, name="H37/G10 nghiem thu anh",
            scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                    SCOPE_ARTIFACTS_READ, SCOPE_CREDITS_READ),
            allowed_tools=(TOOL,))
        db.commit()

        pathlib.Path(a.token_file).write_text(token, encoding="utf-8")
        print(f"key_id={key.key_id}")
        print(f"scopes={key.scopes}")
        print(f"allowed_tools={key.allowed_tools}")
        print(f"token da ghi vao {a.token_file} (KHONG in ra man hinh)")
        return 0
    finally:
        _dong(gen)


def chay(a) -> int:
    """Nộp MỘT job ảnh thật và đối soát credit từng bước."""
    import httpx

    token = pathlib.Path(a.token_file).read_text(encoding="utf-8").strip()
    h = {"Authorization": f"Bearer {token}", "User-Agent": UA}
    kh = httpx.Client(base_url=f"{BASE}/api/v1", headers=h, timeout=60.0)

    def ra(ten, r):
        print(f"  {ten:26s} HTTP {r.status_code}")
        return r

    print("== 1. Tool co trong catalog chua")
    r = ra("GET /tools", kh.get("/tools"))
    if r.status_code != 200:
        print(f"     {r.text[:300]}")
        return 1
    ten = [t.get("name") for t in (r.json().get("items") or [])]
    print(f"     tool thay duoc: {ten}")
    if TOOL not in ten:
        print(f"     DUNG: {TOOL} chua ra catalog. Da nap lai env chua?")
        return 1

    print("== 2. So du truoc")
    r = ra("GET /credits/balance", kh.get("/credits/balance"))
    truoc = (r.json() or {}).get("balance")
    print(f"     balance = {truoc}")

    than = {"tool": TOOL, "params": {"prompt": a.prompt, "count": 1, "mode": "t2i"}}

    print("== 3. Bao gia")
    r = ra("POST /quotes", kh.post("/quotes", json=than))
    if r.status_code != 200:
        print(f"     {r.text[:400]}")
        return 1
    quote = r.json()
    print(f"     credit bao gia = {quote.get('credit')}  quote_id = {quote.get('id')}")

    print("== 4. Nop job")
    idem = "nt-anh-" + secrets.token_hex(8)
    r = ra("POST /jobs", kh.post("/jobs", json={**than, "quote_id": quote.get("id")},
                                 headers={"Idempotency-Key": idem}))
    if r.status_code not in (200, 201, 202):
        print(f"     {r.text[:400]}")
        return 1
    job = r.json()
    job_id = job.get("id")
    print(f"     job_id = {job_id}  status = {job.get('status')}")

    print("== 5. Cho job xong (may B ve ~110 giay/anh)")
    het = time.time() + a.cho
    cuoi = None
    while time.time() < het:
        r = kh.get(f"/jobs/{job_id}")
        if r.status_code != 200:
            print(f"     GET /jobs/{job_id} -> HTTP {r.status_code}: {r.text[:200]}")
            return 1
        cuoi = r.json()
        tt = cuoi.get("status")
        if tt in ("succeeded", "failed", "cancelled"):
            break
        print(f"     ... {tt}")
        time.sleep(10)
    print(f"     status cuoi = {(cuoi or {}).get('status')}")
    print(json.dumps(cuoi, ensure_ascii=False, indent=2)[:1400])

    print("== 6. So du sau, va doi soat")
    r = ra("GET /credits/balance", kh.get("/credits/balance"))
    sau = (r.json() or {}).get("balance")
    print(f"     balance {truoc} -> {sau}  (da tru {(truoc or 0) - (sau or 0)})")
    print(f"     bao gia luc dau: {quote.get('credit')}")
    tinh = ((cuoi or {}).get("credit") or {})
    print(f"     job.credit: {json.dumps(tinh, ensure_ascii=False)}")
    print("     ⇒ 'charged' phai bang so credit THAT SU tru, va <= bao gia.")
    return 0 if (cuoi or {}).get("status") == "succeeded" else 1


def don(a) -> int:
    """Thu hồi mọi khoá của tài khoản nghiệm thu. Không xoá tài khoản."""
    from platform_core.public_api import keys as devkeys
    from platform_core.public_api.tables import DeveloperApiKey
    import sqlalchemy as sa

    gen, db = _phien()
    try:
        user = _tim(db)
        if user is None:
            print("khong co tai khoan nghiem thu — khong co gi de don")
            return 0
        rows = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.user_id == user.id,
            DeveloperApiKey.revoked_at.is_(None))).scalars().all()
        for row in rows:
            devkeys.revoke(db, row.key_id)
        db.commit()
        print(f"da thu hoi {len(rows)} khoa")
        return 0
    finally:
        _dong(gen)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Nghiem thu image.ltt tu ngoai vao")
    sub = ap.add_subparsers(dest="lenh", required=True)

    p1 = sub.add_parser("chuan_bi")
    p1.add_argument("--token-file", required=True)

    p2 = sub.add_parser("chay")
    p2.add_argument("--token-file", required=True)
    p2.add_argument("--prompt", default="A calico cat asleep on a wooden table, "
                                        "morning light through a window")
    p2.add_argument("--cho", type=float, default=600.0, help="giay cho toi da")

    sub.add_parser("don")

    a = ap.parse_args(argv)
    if a.lenh != "chay":
        _nap_env()
    return {"chuan_bi": chuan_bi, "chay": chay, "don": don}[a.lenh](a)


if __name__ == "__main__":
    sys.exit(main())
