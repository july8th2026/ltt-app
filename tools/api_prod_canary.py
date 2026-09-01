"""Canary chỉ-đọc cho khu API, chạy trên máy chủ THẬT qua Cloudflare (H35.9c).

`public_api_load_test.py` cố ý **không bao giờ** trỏ vào production: nó dựng app
trong tiến trình với SQLite tạm. Đó đúng là thứ §6 của
`API_PLATFORM_FULL_RELEASE_READINESS.md` đã đo, và cũng đúng là thứ §11 mục 1
nói **chưa đủ** — vì nó không đi qua Cloudflare và không chạm PostgreSQL thật.
File này là phần còn thiếu, và nó là "một bài tập riêng, được duyệt riêng" mà
docstring của công cụ kia nhắc tới.

Ba việc trong một file thay vì ba file như cặp `*_agent_canary.py`: cả ba dùng
chung cách nạp env, cách tìm user và cách mở phiên CSDL, nên tách ra chỉ nhân
ba đoạn giống nhau. Đổi lại phải đọc `--help` mới biết có ba lệnh con.

    python tools\\api_prod_canary.py prepare --token-file C:\\tmp\\tok.txt
    python tools\\api_prod_canary.py probe   --token-file C:\\tmp\\tok.txt
    python tools\\api_prod_canary.py cleanup

## Vì sao khoá này KHÔNG tiêu được tiền

Khoá cấp bằng `DEFAULT_SCOPES` (`tools:read` + `jobs:read`). `jobs:create` nằm
trong `SPENDING_SCOPES` và **không** được cấp, nên khoá này không nộp được việc
dù có credit trong tài khoản. Đó là rào chắn của thiết kế, không phải của lời
hứa trong tài liệu này.

## Vì sao đo chỉ-đọc

§6 đo "chi phí control-plane"; nên thứ phải đo lại cũng là control-plane. Cho
đường tạo job chạy trên production chỉ để lấy số là tiêu tiền thật và gọi
provider thật cho một phép đo mà điều kiện không đòi. Đường đó đã có bằng chứng
riêng ở H35.8.

## Giới hạn phải đọc kèm số

`LTT_PUBLIC_API_RPM` mặc định 120 request/phút **cho mỗi khoá**. Đẩy mạnh hơn
mức đó bằng một khoá thì thứ đo được là **bộ giới hạn nhịp**, không phải năng
lực máy chủ. Công cụ này giữ tải dưới ngưỡng và đếm riêng 429 để chuyện đó nhìn
thấy được thay vì lẫn vào trung bình.

Token **không bao giờ** in ra màn hình: ghi thẳng vào `--token-file`.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EMAIL = "api-load-canary@lttstudios.com"
BASE_URL = "https://app.lttstudios.com"

#: Đủ để tài khoản trông như một khách thật khi đọc `/usage`, và vô hại: khoá
#: chỉ-đọc không tiêu được đồng nào trong số này.
CREDIT = 100


def nap_env(path: Path) -> None:
    """Nạp app.env vào os.environ. `utf-8-sig` để một BOM lỡ tay không làm hỏng."""
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip()


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
    from sqlalchemy import select

    from platform_core.models import User

    return db.execute(select(User).where(User.email == EMAIL)).scalar_one_or_none()


def prepare(args) -> int:
    from platform_core import credit
    from platform_core.public_api import keys as devkeys
    from platform_core.users import tao_nguoi_dung

    gen, db = _phien()
    try:
        user = _tim(db)
        if user is None:
            user = tao_nguoi_dung(
                db, email=EMAIL, password=secrets.token_urlsafe(32),
                display_name="API load canary", role="user", is_verified=True)
            db.flush()
            print(f"da tao tai khoan {EMAIL}")
        else:
            # Mat khau khong bao gio duoc dung: canary chi goi API bang khoa.
            user.is_active = True
            print(f"dung lai tai khoan co san {EMAIL}")

        so_du = credit.so_du(db, user.id)
        if so_du < CREDIT:
            credit.cap_tay(db, user.id, CREDIT - so_du, by="api-load-canary",
                           note="H35.9c canary")
            print(f"credit: {so_du} -> {credit.so_du(db, user.id)}")
        else:
            print(f"credit da du: {so_du}")

        key, token = devkeys.issue(db, user_id=user.id, name="H35.9c load canary")
        db.commit()

        Path(args.token_file).write_text(token, encoding="utf-8")
        print(f"key_id={key.key_id} scopes={key.scopes}")
        print(f"token da ghi vao {args.token_file} (KHONG in ra man hinh)")
        return 0
    finally:
        _dong(gen)


def probe(args) -> int:
    import httpx

    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    if not token:
        print("LOI: token file rong")
        return 2

    duong = ["/api/v1/tools", "/api/v1/jobs", "/api/v1/usage"]
    do_tre: dict = {d: [] for d in duong}
    trang_thai: dict = {}
    tool_thay: list = []

    # Nhip duoi tran: 120/phut = 2/giay cho moi khoa. Giu 1 request/giay de con
    # cho ca ba duong ma khong cham limiter.
    nhip = max(0.0, float(args.interval))

    with httpx.Client(base_url=args.base_url, timeout=30.0,
                      headers={"Authorization": f"Bearer {token}"}) as client:
        for _vong in range(int(args.rounds)):
            for d in duong:
                t0 = time.perf_counter()
                try:
                    r = client.get(d)
                except Exception as exc:                       # noqa: BLE001
                    trang_thai[f"{d} EXC"] = trang_thai.get(f"{d} EXC", 0) + 1
                    print(f"  loi goi {d}: {type(exc).__name__}")
                    continue
                do_tre[d].append((time.perf_counter() - t0) * 1000.0)
                khoa = f"{d} {r.status_code}"
                trang_thai[khoa] = trang_thai.get(khoa, 0) + 1
                if d == "/api/v1/tools" and r.status_code == 200 and not tool_thay:
                    # Hep va co bao: mot `200` khong phai JSON nghia la co thu
                    # khac dang tra loi thay khu API (trang loi cua bien, proxy
                    # chen vao). Nuot im o day se bien no thanh "danh sach tool
                    # rong" - dung ket luan ma phep do nay sinh ra de kiem.
                    try:
                        body = r.json()
                    except ValueError as exc:
                        print(f"  CANH BAO: {d} tra 200 nhung khong phai JSON "
                              f"({exc}). Khong ket luan gi ve danh sach tool.")
                        body = {}
                    # 🔴 `items` PHẢI CÓ TRONG DANH SÁCH NÀY. Bản cũ đọc
                    #    `data`/`tools` mà khu API trả về **`items`**, nên nó
                    #    luôn ra `[]` — và in ra *"(rỗng — đúng ý muốn khi
                    #    LTT_PUBLIC_API_TOOLS chưa đặt)"* trong khi production
                    #    đang mở **năm** tool. Đo 01/09.
                    #
                    # ⭐ Chú thích ngay trên đã canh đúng cái kết luận sai này,
                    #    chỉ canh **một** đường tới nó (200 không phải JSON). Câu
                    #    trả lời sai đến bằng đường khác: một tên khoá lệch.
                    #
                    # ⇒ Nên chốt không phải "thêm `items`" mà là: **hình dạng lạ
                    #   phải NÓI RA**, đừng bao giờ để nó lặng lẽ thành rỗng.
                    khoa_biet = ("items", "data", "tools")
                    muc = None
                    for k in khoa_biet:
                        if isinstance(body.get(k), list):
                            muc = body[k]
                            break
                    if muc is None:
                        print(f"  CANH BAO: {d} tra 200 nhung khong co khoa nao "
                              f"trong {khoa_biet} (co: {sorted(body)}). "
                              f"KHONG ket luan gi ve danh sach tool.")
                        muc = []
                        tool_thay = ["<khong doc duoc hinh dang>"]
                    else:
                        tool_thay = [t.get("name", "?") if isinstance(t, dict)
                                     else str(t) for t in muc]
                time.sleep(nhip)

    print("\n=== trang thai ===")
    for khoa in sorted(trang_thai):
        print(f"  {khoa}: {trang_thai[khoa]}")

    print("\n=== do tre qua Cloudflare (ms) ===")
    ket = {}
    for d, mau in do_tre.items():
        if not mau:
            print(f"  {d}: khong co mau")
            continue
        thu_tu = sorted(mau)
        p95 = thu_tu[min(len(thu_tu) - 1, int(0.95 * (len(thu_tu) - 1)))]
        ket[d] = {"n": len(thu_tu), "p50": round(statistics.median(thu_tu), 1),
                  "p95": round(p95, 1), "max": round(max(thu_tu), 1)}
        print(f"  {d}: n={ket[d]['n']} p50={ket[d]['p50']} "
              f"p95={ket[d]['p95']} max={ket[d]['max']}")

    print("\n=== tool dang mo cho khach ===")
    print(f"  {tool_thay if tool_thay else '(rong - dung y muon khi '
                                          'LTT_PUBLIC_API_TOOLS chua dat)'}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"latency_ms": ket, "statuses": trang_thai,
                        "tools_exposed": tool_thay}, indent=2), encoding="utf-8")
        print(f"\nket qua ghi vao {args.json_out}")
    return 0


def cleanup(args) -> int:
    from sqlalchemy import select

    from platform_core.public_api import keys as devkeys
    from platform_core.public_api.tables import DeveloperApiKey

    gen, db = _phien()
    try:
        user = _tim(db)
        if user is None:
            print("khong co tai khoan canary - khong co gi de don")
            return 0

        rows = db.execute(select(DeveloperApiKey).where(
            DeveloperApiKey.user_id == user.id,
            DeveloperApiKey.revoked_at.is_(None))).scalars().all()
        for key in rows:
            devkeys.revoke(db, key)
        user.is_active = False
        db.commit()
        # Giu lai hang trong CSDL chu khong xoa: ban ghi kiem toan cua mot lan do
        # tren production la thu can con lai, giong het cach cleanup_agent_canary
        # giu audit row.
        print(f"da thu hoi {len(rows)} khoa va vo hieu {EMAIL}")
        return 0
    finally:
        _dong(gen)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", default=r"C:\LTTPlatform\secrets\app.env")
    sub = parser.add_subparsers(dest="lenh", required=True)

    p = sub.add_parser("prepare", help="tao canary + cap credit + cap khoa chi-doc")
    p.add_argument("--token-file", required=True)
    p.set_defaults(func=prepare)

    p = sub.add_parser("probe", help="do chi-doc qua Cloudflare")
    p.add_argument("--token-file", required=True)
    p.add_argument("--base-url", default=BASE_URL)
    p.add_argument("--rounds", type=int, default=20)
    p.add_argument("--interval", type=float, default=0.35)
    p.add_argument("--json-out", default="")
    p.set_defaults(func=probe)

    p = sub.add_parser("cleanup", help="thu hoi khoa + vo hieu tai khoan canary")
    p.set_defaults(func=cleanup)

    args = parser.parse_args(argv)
    if args.lenh != "probe":
        nap_env(Path(args.env))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
