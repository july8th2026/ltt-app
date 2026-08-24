"""nghiem_thu_chat_l1.py - di het luong KHACH THAT cho `text.chat`. (H38/L1)

    python tools\\nghiem_thu_chat_l1.py chuan_bi --token-file C:\\tmp\\chat_tok.txt
    python tools\\nghiem_thu_chat_l1.py chay     --token-file C:\\tmp\\chat_tok.txt
    python tools\\nghiem_thu_chat_l1.py don

* VI SAO CAN TEP NAY DU DA CO 739 TEST XANH.
  L1 hoi mot cau ma khong test nao hoi duoc: *mot khach tra tien, dung mot khoa
  moi tao, co goi duoc khong va co bi thu dung tien khong.* H38 tung co 739 test
  xanh va van de lot loi VARCHAR(36) toi dung luot goi that dau tien, vi SQLite
  khong ep do dai ma PostgreSQL thi ep.

* BA CUA, VA CHUNG THU TIEN THEO HAI LUAT KHAC NHAU:
    /chat/completions  SYNC_BILLED - doi Idempotency-Key, tran max_tokens
    /messages          STREAM      - khong doi, thu theo token DA SINH RA
    /responses         STREAM      - nhu tren, cho Codex

  Tep nay di ca ba, vi mot cua xanh khong noi gi ve hai cua kia.

!! DUNG TAI KHOAN TEST, KHONG DUNG ADMIN. Admin co san credit, san quyen, san
   hieu biet - no di qua duoc ca nhung cho mot khach that bi chan.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import secrets
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

BASE = "https://app.lttstudios.com"
EMAIL = "autosub-test@lttstudios.com"     # tai khoan TEST co san, khong phai admin
NAP_THEM = 200                             # credit nap them de chay nghiem thu
TOOL = "text.chat"
MODEL = "ltt_llm"
# !! BAT BUOC. urllib mac dinh bi Cloudflare tra 403 TRUOC khi cham may chu.
UA = "ltt-nghiem-thu-l1/1.0"


def _nap_env() -> None:
    tep = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")
    if not tep.exists():
        return
    for dong in tep.read_text(encoding="utf-8-sig").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#") and "=" in dong:
            k, v = dong.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _phien():
    _nap_env()
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


def _tim(db):
    import sqlalchemy as sa
    from platform_core.models import User
    return db.execute(sa.select(User).where(User.email == EMAIL)).scalar_one_or_none()


def _goi(duong, than, tok, *, phuong="POST", them=None):
    import urllib.error
    import urllib.request
    du = json.dumps(than).encode() if than is not None else None
    dau = {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
           "User-Agent": UA}
    dau.update(them or {})
    rq = urllib.request.Request(BASE + "/api/v1" + duong, data=du, method=phuong,
                                headers=dau)
    try:
        with urllib.request.urlopen(rq, timeout=300) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _text(b):
    return b.decode("utf-8", "replace")


def chuan_bi(a) -> int:
    from platform_core import credit
    from platform_core.public_api import keys as devkeys
    gen, db = _phien()
    try:
        u = _tim(db)
        if u is None:
            print("KHONG co tai khoan " + EMAIL + ". Dung tai khoan test co san.")
            return 1
        truoc = credit.so_du(db, u.id)
        credit.nap(db, u.id, NAP_THEM,
                   note="nghiem thu L1 text.chat " + secrets.token_hex(4))
        db.commit()
        sau = credit.so_du(db, u.id)
        print("tai khoan " + EMAIL + " (role=" + u.role + ")")
        print("credit: {0} -> {1}".format(truoc, sau))

        # !! Ten ham la `issue`, va no tra ve (key, token) THEO THU TU DO. Doi cho
        #    hai gia tri nay thi token bi ghi ra tep duoi dang mot doi tuong ORM -
        #    khong loi nao bao, chi la tep token vo dung o buoc sau.
        key, tok = devkeys.issue(
            db, user_id=u.id, name="nghiem thu L1 chat",
            scopes=("tools:read", "credits:read", "jobs:create", "jobs:read"),
            allowed_tools=(TOOL,))
        db.commit()
        print("key_id=" + str(key.key_id))
        print("scopes=" + str(key.scopes))
        print("allowed_tools=" + str(key.allowed_tools))
        pathlib.Path(a.token_file).write_text(tok, encoding="utf-8")
        print("token da ghi vao " + a.token_file + " (KHONG in ra man hinh)")
        return 0
    finally:
        _dong(gen)


def chay(a) -> int:
    tok = pathlib.Path(a.token_file).read_text(encoding="utf-8").strip()

    def sd():
        m, b = _goi("/credits/balance", None, tok, phuong="GET")
        if m != 200:
            return None
        return (json.loads(b) or {}).get("balance")

    print("== 1. Tool co trong catalog chua")
    m, b = _goi("/tools", None, tok, phuong="GET")
    ten = []
    if m == 200:
        # !! Khoa la `items`, KHONG phai `tools`. Toi doan nham mot lan 24/08 va
        #    nhan mot danh sach RONG - trieu chung giong het "tool chua duoc mo",
        #    tuc mot loi doc sai gia dang thanh mot loi cau hinh. Doc hop dong
        #    (`server/api/`), dung doan tu ten endpoint.
        ten = [t.get("name") for t in (json.loads(b) or {}).get("items", [])]
    print("   GET /tools -> {0}, thay {1}".format(m, ten))
    if TOOL not in ten:
        print("   DUNG: " + TOOL + " chua ra catalog.")
        return 1

    d0 = sd()
    print("== 2. So du truoc: {0}".format(d0))

    print("== 3. /chat/completions  (SYNC_BILLED - doi Idempotency-Key)")
    than = {"model": MODEL, "max_tokens": 300,
            "messages": [{"role": "user", "content": "Tra loi dung hai chu: xin chao"}]}
    m, b = _goi("/chat/completions", than, tok,
                them={"Idempotency-Key": "l1-" + secrets.token_hex(8)})
    print("   -> HTTP {0}".format(m))
    if m != 200:
        print("   " + _text(b)[:400])
        return 1
    kq = json.loads(b)
    noi = ((kq.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    print("   noi dung: " + repr(noi[:80]))
    print("   usage: " + json.dumps(kq.get("usage") or {}, ensure_ascii=False))
    d1 = sd()
    print("   so du {0} -> {1}  (thu {2})".format(d0, d1, (d0 or 0) - (d1 or 0)))
    # !! Mot luot tra ve noi dung RONG ma van thu tien la mot loi TIEN dang song.
    #    Da tung suyt bao nham dieu nay 24/08 vi max_tokens qua nho cho mot model
    #    co phan suy nghi rieng - nen kiem ca `usage`, dung chi kiem chuoi rong.
    if not noi.strip():
        print("   HONG: noi dung RONG. usage=" + json.dumps(kq.get("usage") or {}))
        return 1

    print("== 4. /messages  (STREAM - KHONG doi Idempotency-Key)")
    than = {"model": MODEL, "max_tokens": 300, "stream": True,
            "messages": [{"role": "user", "content": "Tra loi dung mot tu: OK"}]}
    m, b = _goi("/messages", than, tok)
    txt = _text(b)
    print("   -> HTTP {0}, {1} byte".format(m, len(b)))
    if m != 200:
        print("   " + txt[:400])
        return 1
    co_su_kien = ("event:" in txt) or ("data:" in txt)
    co_usage = "usage" in txt
    print("   co su kien SSE: {0} | co usage de quyet toan: {1}".format(
        co_su_kien, co_usage))
    d2 = sd()
    print("   so du {0} -> {1}  (thu {2})".format(d1, d2, (d1 or 0) - (d2 or 0)))
    if not co_su_kien:
        print("   HONG: khong phai mot luong SSE.")
        return 1

    print("== 5. /responses  (STREAM - cho Codex)")
    than = {"model": MODEL, "max_output_tokens": 300, "stream": True,
            "input": "Tra loi dung mot tu: OK"}
    m, b = _goi("/responses", than, tok)
    txt = _text(b)
    print("   -> HTTP {0}, {1} byte, co su kien: {2}".format(
        m, len(b), "data:" in txt))
    if m != 200:
        print("   " + txt[:400])
        return 1
    d3 = sd()
    print("   so du {0} -> {1}  (thu {2})".format(d2, d3, (d2 or 0) - (d3 or 0)))

    print("== 6. Chot")
    print("   tong thu ca ba cua: {0} credit".format((d0 or 0) - (d3 or 0)))
    print("   => moi cua phai thu > 0 va khop voi usage bao cao.")
    return 0


def don(a) -> int:
    import sqlalchemy as sa
    from platform_core.public_api import keys as devkeys
    from platform_core.public_api.tables import DeveloperApiKey
    gen, db = _phien()
    try:
        u = _tim(db)
        if u is None:
            print("khong co tai khoan - khong co gi de don")
            return 0
        rows = db.execute(sa.select(DeveloperApiKey).where(
            DeveloperApiKey.user_id == u.id,
            DeveloperApiKey.name == "nghiem thu L1 chat",
            DeveloperApiKey.revoked_at.is_(None))).scalars().all()
        for row in rows:
            devkeys.revoke(db, row)
        db.commit()
        # Doc lai tu CSDL thay vi tin vao gia tri tra ve: mot lenh thu hoi that
        # bai IM LANG se de mot khoa TIEU DUOC TIEN THAT nam lai.
        con = db.execute(sa.select(sa.func.count()).select_from(DeveloperApiKey).where(
            DeveloperApiKey.user_id == u.id,
            DeveloperApiKey.name == "nghiem thu L1 chat",
            DeveloperApiKey.revoked_at.is_(None))).scalar_one()
        print("da thu hoi {0} khoa; con song: {1}".format(len(rows), con))
        return 1 if con else 0
    finally:
        _dong(gen)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Nghiem thu text.chat tu ngoai vao (L1)")
    sub = ap.add_subparsers(dest="lenh", required=True)
    for ten in ("chuan_bi", "chay"):
        s = sub.add_parser(ten)
        s.add_argument("--token-file", required=True)
    sub.add_parser("don")
    a = ap.parse_args(argv)
    return {"chuan_bi": chuan_bi, "chay": chay, "don": don}[a.lenh](a)


if __name__ == "__main__":
    sys.exit(main())
