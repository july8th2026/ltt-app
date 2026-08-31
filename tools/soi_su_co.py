"""soi_su_co.py — doc SO REQUEST that, roi moi hoi may B. (chi doc)

    powershell -ExecutionPolicy Bypass -File .\\setup\\soi_su_co.ps1

## Vi sao tep nay ton tai, va vi sao no doc theo THU TU NAY

Ngay 31/08 mot khach goi 117 luot qua `/api/v1/responses`, **89 luot 503
`service_unavailable`**, keo hon nam gio. Toi da mat nhieu vong doan nguyen nhan
tu `logs\\*.jsonl` — va nhat ky may chu **khong the** tra loi, vi hai trong ba
nhanh sinh ra 503 do **khong ghi mot dong nao**.

⛔ BAI HOC, va no la ly do tep nay doc so request TRUOC: **`public_api_requests`
   la ban ghi co tham quyen; `logs\\*.jsonl` chi la thu ai do nho ghi lai.** Doan
   tu nhat ky khi so cai co san la chon nguon te hon.

## Bon nguyen nhan co the cho cung mot trieu chung 503

Cot `code` va cot `tool` trong so request tach duoc chung ra, va khong gi khac
tach duoc:

    code=service_unavailable, tool RONG   -> chan o tang CHINH SACH
                                             (cong tac ngat: maintenance / tool)
    code=service_unavailable, tool CO      -> may B tu choi (ban) hoac khong phuc vu
    code=capacity_unavailable              -> het nang luc phia sau (pool/GPU)
    code=upstream_error                    -> may B hong that

⭐ Cot `tool` la thu phan biet re nhat: mot yeu cau bi chan o tang chinh sach
   **chua bao gio** biet no goi tool nao, nen o do cot ay RONG. Anh chup man
   hinh cua chu san pham cho thay cot CONG CU trong — day la manh moi dat nhat,
   va no chi doc duoc tu so request.

⛔ CHI DOC. Khong ghi gi, khong doi cau hinh, khong cham so tien.
⛔ KHONG IN CREDENTIAL. Chi in do dai va id rut gon.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tieu(s: str) -> None:
    print("\n" + "=" * 70)
    print("  " + s)
    print("=" * 70)


def _in_json(nhan: str, van: str, toi_da: int = 1200) -> None:
    print(f"  {nhan}:")
    try:
        goc = json.loads(van)
    except (ValueError, TypeError):
        print("    " + (van.strip()[:toi_da] or "(rong)"))
        return
    for d in json.dumps(goc, ensure_ascii=False, indent=2).splitlines()[:40]:
        print("    " + d)


# ── 1. Cong tac ngat ────────────────────────────────────────────────────────

def phan_cong_tac(db) -> None:
    tieu("1. CONG TAC NGAT  (mot cai dang bat se chan MOI yeu cau, 503)")
    from platform_core.public_api import policy

    try:
        dang_bat = policy.active_switches(db)
    except Exception as e:                                      # noqa: BLE001
        print(f"  khong doc duoc: {type(e).__name__}: {e}")
        return
    if not dang_bat:
        print("  KHONG co cong tac nao dang bat.")
        return
    print(f"  >>> CO {len(dang_bat)} CONG TAC DANG BAT — day rat co the LA nguyen nhan:")
    for s in dang_bat:
        print(f"    scope={getattr(s, 'scope', '?')} "
              f"muc_tieu={getattr(s, 'target', '') or '(toan cuc)'}")
        print(f"      ly_do : {getattr(s, 'reason', '')}")
        print(f"      bat_tu: {getattr(s, 'created_at', '?')}  "
              f"het_han: {getattr(s, 'expires_at', None) or '(khong)'}")


# ── 2. So request — ban ghi co tham quyen ──────────────────────────────────

def phan_so_request(db, email: str, gio: int) -> None:
    from sqlalchemy import func, select

    from platform_core.models import User
    from platform_core.public_api.tables import ApiRequestLog as R

    tieu(f"2. SO REQUEST  ({gio} gio gan nhat)")
    tu = datetime.now(timezone.utc) - timedelta(hours=gio)

    print("\n  a) Toan he thong, nhom theo (status, code, route, tool):")
    for st, code, route, tool, n, t0, t1 in db.execute(
            select(R.status, R.code, R.route, R.tool, func.count(),
                   func.min(R.created_at), func.max(R.created_at))
            .where(R.created_at >= tu)
            .group_by(R.status, R.code, R.route, R.tool)
            .order_by(func.count().desc()).limit(25)).all():
        print(f"    {n:5d}x  {st}  {(code or '-'):24s} {route:26s} "
              f"tool={(tool or '(RONG)'):12s}  {t0:%m-%d %H:%M} -> {t1:%m-%d %H:%M}")

    u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if u is None:
        print(f"\n  b) khong tim thay tai khoan {email}")
        return
    print(f"\n  b) Tai khoan {email}  (id={u.id[:8]})")
    tong = db.execute(select(func.count()).select_from(R)
                      .where(R.user_id == u.id)).scalar_one()
    loi = db.execute(select(func.count()).select_from(R)
                     .where(R.user_id == u.id, R.status >= 400)).scalar_one()
    print(f"     tong={tong}  loi(>=400)={loi}")

    print("\n  c) 25 luot gan nhat cua tai khoan do:")
    gan = db.execute(select(R).where(R.user_id == u.id)
                     .order_by(R.created_at.desc()).limit(25)).scalars().all()
    for r in reversed(gan):
        print(f"    {r.created_at:%m-%d %H:%M:%S}  {r.status} "
              f"{(r.code or '-'):22s} {r.route:24s} tool={(r.tool or '(RONG)'):12s} "
              f"{r.latency_ms:6d}ms credit={r.credit_delta:+d}")


# ── 3. May B ───────────────────────────────────────────────────────────────

def phan_may_b(db, goi_thu: bool) -> None:
    import httpx

    from platform_core import api_keys, api_pool, providers
    from platform_core.models import APIKEY_CAT_CHAT

    tieu("3. CONG VLM MAY B")
    try:
        key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                thu_tu_provider=["ltt_llm"])
    except Exception as e:                                      # noqa: BLE001
        print(f"  KHONG cap duoc khoa ltt_llm: {type(e).__name__}: {e}")
        print("  (neu khoa bi disable thi day CHINH LA nguyen nhan)")
        return
    prov = providers.get("ltt_llm")
    base = ((getattr(key, "base_url", "") or "").strip()
            or (getattr(prov, "base_url", "") or "").strip())
    cred = api_keys.lay_credential(db, key)
    print(f"  khoa      : id={key.id[:8]} priority={key.priority} "
          f"trang_thai={getattr(key, 'status', '?')}")
    print(f"  credential: {len(cred)} ky tu (khong in ra)")
    print(f"  base_url  : {base or '(TRONG — day chinh la loi)'}")
    if not base:
        return

    dau = {"Authorization": f"Bearer {cred}"}
    goc = base.rstrip("/")

    def doc_health(nhan: str) -> dict:
        print(f"\n  GET /health  [{nhan}]")
        try:
            r = httpx.get(goc + "/health", headers=dau, timeout=20.0)
            print(f"    HTTP {r.status_code}")
            _in_json("than", r.text)
            return r.json() if r.status_code == 200 else {}
        except (httpx.HTTPError, ValueError) as e:
            print(f"    KHONG NOI DUOC: {type(e).__name__}: {e}")
            return {}

    truoc = doc_health("truoc")
    if not goi_thu:
        return

    # 🔴 PHEP DO QUYET DINH CUA CA TEP NAY.
    #
    #    `/health` co the xanh — GPU ranh, RAM day, trong tai bao "khong ban" —
    #    trong khi MOI yeu cau that van bi tu choi. Do dung la hinh dang su co
    #    31/08, va no chi lo ra khi GOI THAT.
    #
    # ⛔ VA PHAI GOI DUNG TEN MODEL CUA MAY B. Lan chay dau toi gui `ltt_llm` —
    #    do la ALIAS CONG KHAI, khong phai id tren may B. `features.py` anh xa
    #    `ltt_llm` -> `qwen38-api` truoc khi goi. Gui alias thi may B tra 404
    #    "model khong co", va cai 404 do la loi CUA CONG CU, rat de doc nham
    #    thanh mot su co production. Nen lay ten tu chinh `/health`.
    mo = (truoc.get("models_mo") or [])
    ten_model = mo[0] if mo else "qwen38-api"
    print(f"\n  POST /v1/responses  (model={ten_model}, 8 token, dung cua khach)")
    than = {"model": ten_model, "max_output_tokens": 8,
            "input": [{"role": "user",
                       "content": [{"type": "input_text", "text": "1+1?"}]}]}
    try:
        r = httpx.post(goc + "/v1/responses", headers=dau, json=than, timeout=120.0)
        print(f"    HTTP {r.status_code}")
        if r.headers.get("retry-after"):
            print(f"    Retry-After: {r.headers['retry-after']}")
        if r.status_code == 429:
            print("\n    >>> MAY B TU CHOI. LY DO CHINH XAC:")
        _in_json("than", r.text)
    except httpx.HTTPError as e:
        print(f"    KHONG NOI DUOC: {type(e).__name__}: {e}")

    # ⭐ Doc lai `gioi_han` SAU luot goi. Neu `dang_chay` khong tut ve 0 khi da
    #    het viec thi mot SUAT DA BI RO — va voi `max_dong_thoi = 1`, mot suat ro
    #    la cong dong cua vinh vien trong khi GPU hoan toan ranh. Chinh chu thich
    #    trong `llm_gateway/gioi_han.py` canh bao dung hinh dang nay.
    sau = doc_health("sau")
    for nhan, h in (("truoc", truoc), ("sau", sau)):
        gh = (h or {}).get("gioi_han") or {}
        if gh:
            print(f"  gioi_han [{nhan}]: dang_chay={gh.get('dang_chay')} / "
                  f"max={gh.get('max_dong_thoi')}")


def main() -> int:
    p = argparse.ArgumentParser(description="Soi su co API (chi doc).")
    p.add_argument("--email", default="dungnv.forwork@gmail.com")
    p.add_argument("--gio", type=int, default=24)
    p.add_argument("--khong-goi-thu", action="store_true")
    a = p.parse_args()

    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        phan_cong_tac(db)
        phan_so_request(db, a.email, a.gio)
        phan_may_b(db, not a.khong_goi_thu)
        print("\n" + "=" * 70)
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    sys.exit(main())
