"""noi_phien.py — một phiên khách (hoặc một mã lượt) → mọi lượt, ghép bốn sổ. (CHỈ ĐỌC, T4 P2)

    python tools\\noi_phien.py --phien <id phien client> --email <email khach> [--so-b <gateway_err.log>...]
    python tools\\noi_phien.py --phien <id> --user-id <uuid> [--gio 720]
    python tools\\noi_phien.py --ma st:9f... [--so-b <gateway_err.log>...]

Trả lời: *"lượt X trên máy B thuộc phiên nào của khách nào, tốn bao nhiêu, chờ bao lâu?"*
(thiết kế `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §5).

Nối, cùng MỘT khoá là mã lượt (`ms:`/`st:`/`ch:` + 32 hex):

    public_api_requests.ma_luot   (phiên / nhánh / turn / app client, status, route — P1)
      = llm_waiters.request_id    (chờ, chạy, kết cục, token, TTFB phía A — P2)
      = credit_entries.job_id     (giữ / thu / hoàn)
      = "ma" ở sổ lượt B          (`llm_gateway.so`: TTFT, mã kết thúc, huỷ)

⚠️ Một mã lượt có thể có NHIỀU dòng sổ B: A xếp lại khi B trả 429 với CÙNG mã
   (`luong.py`), nên lấy mọi dòng — dòng cuối là lần được phục vụ.
⛔ `--phien` luôn kèm khách (`--email`/`--user-id`): id phiên do client đặt, hai
   khách trùng chuỗi không được lẫn nhau (chỉ mục `ix_public_api_requests_phien`
   mở đầu bằng `user_id`).
⛔ CHỈ ĐỌC. Không ghi CSDL, không gọi máy B (sổ B đọc từ tệp log đã chép về).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Trần số lượt in ra một lần — phiên dài vẫn đọc được, không nổ màn hình.
TRAN_LUOT = 500


def _aware(t: datetime | None) -> datetime | None:
    """SQLite trả giờ không múi; PostgreSQL có múi. So hai loại là ném."""
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _giay(a: datetime | None, b: datetime | None) -> float | None:
    a, b = _aware(a), _aware(b)
    if a is None or b is None:
        return None
    return round((b - a).total_seconds(), 3)


def gom(db, *, user_id: str = "", phien: str = "", ma: str = "",
        gio: int | None = None) -> list[dict]:
    """Các lượt (dòng `public_api_requests`) của một phiên hoặc một mã, cũ trước,
    mỗi lượt kèm dòng `llm_waiters` và tiền từ `credit_entries`.

    Ném `ValueError` khi `phien` không kèm `user_id`, hoặc không có tiêu chí nào.
    """
    from sqlalchemy import func, select

    from platform_core.models import CreditEntry, LlmWaiter
    from platform_core.public_api.tables import ApiRequestLog as R

    if phien and not user_id:
        raise ValueError("--phien phai kem khach (--email/--user-id): id phien do "
                         "client dat, hai khach trung chuoi khong duoc lan nhau")
    if not phien and not ma:
        raise ValueError("can --phien hoac --ma")
    dk = []
    if phien:
        dk += [R.user_id == user_id, R.phien_khach == phien]
    if ma:
        dk.append(R.ma_luot == ma)
        if user_id:
            dk.append(R.user_id == user_id)
    if gio:
        dk.append(R.created_at >= datetime.now(timezone.utc) - timedelta(hours=gio))
    dong = db.execute(select(R).where(*dk).order_by(R.created_at)
                      .limit(TRAN_LUOT)).scalars().all()

    cac_ma = {r.ma_luot for r in dong if r.ma_luot}
    cho = {}
    tien: dict[str, int] = {}
    if cac_ma:
        cho = {w.request_id: w for w in db.execute(
            select(LlmWaiter).where(LlmWaiter.request_id.in_(cac_ma))).scalars()}
        tien = {j: int(s) for j, s in db.execute(
            select(CreditEntry.job_id, func.sum(CreditEntry.delta))
            .where(CreditEntry.job_id.in_(cac_ma))
            .group_by(CreditEntry.job_id)).all()}

    out = []
    for r in dong:
        w = cho.get(r.ma_luot) if r.ma_luot else None
        out.append({
            "created_at": _aware(r.created_at), "user_id": r.user_id,
            "route": r.route, "status": r.status, "code": r.code or "",
            "phien_khach": r.phien_khach, "nhanh_khach": r.nhanh_khach,
            "luot_khach": r.luot_khach, "ung_dung_khach": r.ung_dung_khach,
            "ma_luot": r.ma_luot,
            "model": w.model if w else None,
            "ket_qua": w.ket_qua if w else None,
            "ly_do_cho": w.ly_do_cho if w else None,
            "cho_s": _giay(w.created_at, w.admitted_at) if w else None,
            "cho_residency_s": w.cho_residency_s if w else None,
            "chay_s": _giay(w.admitted_at, w.finished_at) if w else None,
            "token_vao": w.token_vao if w else None,
            "token_ra": w.token_ra if w else None,
            "token_cache": w.token_cache if w else None,
            "ttfb_s": w.ttfb_s if w else None,
            # giữ âm + hoàn dương ⇒ −Σ = số đã thu. Không bút toán ⇒ None, không 0.
            "credit_thu": -tien[r.ma_luot] if r.ma_luot in tien else None,
            "so_b": [],
        })
    return out


def doc_so_b(duong: list, cac_ma: set[str]) -> dict[str, list[dict]]:
    """Dòng sổ lượt B (`llm_gateway.so`) của đúng các mã trong `cac_ma`, theo thời gian."""
    from tools.tong_hop_ttft_b import doc_so

    ket: dict[str, list[dict]] = {}
    if not cac_ma:
        return ket
    for p in duong:
        with open(p, encoding="utf-8", errors="replace") as f:
            for d in doc_so(f):
                m = d.get("ma")
                if m in cac_ma:
                    ket.setdefault(m, []).append(d)
    for ds in ket.values():
        ds.sort(key=lambda d: d["_luc"])
    return ket


def ghep_so_b(luot: list[dict], so_b: dict[str, list[dict]]) -> None:
    for x in luot:
        x["so_b"] = list(so_b.get(x["ma_luot"], [])) if x["ma_luot"] else []


def _o(gt, dang: str = "{}") -> str:
    return "-" if gt is None else dang.format(gt)


def in_bang(luot: list[dict]) -> None:
    if not luot:
        print("  (khong co luot nao)")
        return
    x0 = luot[0]
    print(f"  khach={x0['user_id'][:8]} phien={x0['phien_khach'] or '-'} "
          f"app={x0['ung_dung_khach'] or '-'}  ({len(luot)} luot)")
    for x in luot:
        print(f"  {x['created_at']:%m-%d %H:%M:%S} {x['status']} "
              f"{(x['code'] or '-'):20s} {x['route']:24s} ma={x['ma_luot'] or '-'} "
              f"nhanh={(x['nhanh_khach'] or '-')[:8]} turn={(x['luot_khach'] or '-')[:8]}")
        if x["model"] is not None:
            print(f"      A: {x['model']} ket_qua={x['ket_qua'] or '-'} "
                  f"cho={_o(x['cho_s'], '{:.1f}s')} "
                  f"(residency {_o(x['cho_residency_s'], '{:.1f}s')}, "
                  f"ly_do={x['ly_do_cho'] or '-'}) chay={_o(x['chay_s'], '{:.1f}s')} "
                  f"ttfb={_o(x['ttfb_s'], '{:.2f}s')} vao={_o(x['token_vao'])} "
                  f"cache={_o(x['token_cache'])} ra={_o(x['token_ra'])} "
                  f"credit={_o(x['credit_thu'])}")
        for d in x["so_b"]:
            print(f"      B: {d['_luc']:%H:%M:%S} http={_o(d.get('ma_http'))} "
                  f"ket_thuc={d.get('ket_thuc') or '-'} ttft={_o(d.get('ttft_s'))} "
                  f"huy={d.get('huy')} vao={_o(d.get('token_vao'))} "
                  f"ra={_o(d.get('token_ra'))}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Noi mot phien/ma luot qua bon so (chi doc).")
    p.add_argument("--phien", default="", help="id phien client (X-Claude-Code-"
                   "Session-Id / session-id) — phai kem --email hoac --user-id")
    p.add_argument("--ma", default="", help="ma luot (vd tu dong so B `\"ma\"`)")
    p.add_argument("--email", default="")
    p.add_argument("--user-id", default="")
    p.add_argument("--gio", type=int, default=0, help="chi N gio gan nhat (0 = het)")
    p.add_argument("--so-b", action="append", default=[],
                   help="tep log cong B (gateway_err.log) da chep ve; lap duoc")
    a = p.parse_args(argv)

    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        user_id = a.user_id
        if a.email and not user_id:
            from sqlalchemy import select

            from platform_core.models import User
            u = db.execute(select(User).where(User.email == a.email)).scalar_one_or_none()
            if u is None:
                print(f"khong tim thay tai khoan {a.email}", file=sys.stderr)
                return 2
            user_id = u.id
        try:
            luot = gom(db, user_id=user_id, phien=a.phien, ma=a.ma, gio=a.gio or None)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if a.so_b:
            ghep_so_b(luot, doc_so_b(a.so_b, {x["ma_luot"] for x in luot
                                              if x["ma_luot"]}))
        in_bang(luot)
        return 0
    finally:
        db.rollback()   # chỉ đọc: không để giao dịch nào treo
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    sys.exit(main())
