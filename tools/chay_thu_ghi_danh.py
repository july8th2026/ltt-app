r"""
chay_thu_ghi_danh.py — ghi danh một giọng trên production, đi đúng cửa HTTPS mà
một khách hàng đi: vé SSO → cookie phiên → đọc `csrf_token` khỏi trang → POST
multipart → chờ worker → đọc `result`.

    powershell -ExecutionPolicy Bypass -File .\setup\chay_thu_ghi_danh.ps1 `
        -Clip D:\LTTSTUDIOSAPP\tmp\clip_chuan_b.wav

⭐ VÌ SAO ĐI HTTPS CHỨ KHÔNG GỌI THẲNG `submit_with_credit`

   Gọi thẳng vào `features` hay `submit_with_credit` sẽ **xanh kể cả khi CSRF
   hỏng** — và CSRF hỏng đúng là lỗi vừa làm chết mọi cửa POST của app này
   (31/08: `vo.ngu_canh` không phát token, mọi form render `value=""`, mọi POST
   trả 400). Một phép chạy thử không đi qua cửa thật thì không canh được cửa
   thật. Nên kịch bản này **đọc token khỏi HTML đã render** rồi nộp kèm.

⛔ NÓ CHẠM TIỀN THẬT — job ghi danh giữ chỗ rồi quyết toán trong sổ credit, và
   sổ credit chỉ ghi thêm. Chỉ dùng cho tài khoản đuôi `.local`.

⚠️ PHẢI ĐẶT `User-Agent`. Cloudflare chặn tiền tố `Python-urllib/` (phân biệt
   hoa-thường) và trả 403 trông y hệt khoá sai. Xem `CLAUDE.md`.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

UA = "ltt-chay-thu/1.0"
DUOI_THU = ".local"


def _ve(email: str, goc: str) -> str:
    from platform_core import users
    from platform_core.db import get_session
    from platform_core.nexus import sso

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, email)
        if u is None:
            raise SystemExit(f"KHONG THAY {email}")
        ve = sso.tao_ve(db, u, ip="127.0.0.1")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return f"{goc.rstrip('/')}/nexus-sso?ma={ve}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--goc", default="https://app.lttstudios.com")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--ten", default="Clip 30 giay thu bo chon")
    ap.add_argument("--cho-giay", type=int, default=420)
    a = ap.parse_args(argv)

    if not a.email.endswith(DUOI_THU):
        print(f"TU CHOI: chi chay thu voi tai khoan duoi '{DUOI_THU}'.",
              file=sys.stderr)
        return 2

    import requests

    s = requests.Session()
    s.headers["User-Agent"] = UA

    r = s.get(_ve(a.email, a.goc), timeout=60)
    print(f"[1] SSO  -> {r.status_code}  {r.url}")
    if r.status_code != 200:
        return 2

    r = s.get(f"{a.goc}/ltt-voice/giong", timeout=60)
    tok = re.findall(r'name="csrf_token"\s+value="([^"]*)"', r.text)
    print(f"[2] trang giong -> {r.status_code}, {len(tok)} truong csrf, "
          f"dai = {[len(t) for t in tok]}")
    tot = [t for t in tok if t.strip()]
    if not tot:
        # ⛔ Dung day. Nop tiep chi de nhan 400 va doc no thanh "loi mang".
        print("🔴 TOKEN RONG — moi cua POST cua app dang chet. Xem `vo.ngu_canh`.",
              file=sys.stderr)
        return 2

    with open(a.clip, "rb") as f:
        data = f.read()
    r = s.post(f"{a.goc}/ltt-voice/giong/tao",
               data={"ten": a.ten, "dong_y": "1", "csrf_token": tot[0]},
               files={"tep": (os.path.basename(a.clip), data, "audio/wav")},
               timeout=180)
    print(f"[3] POST ghi danh -> {r.status_code}  {r.text[:300]}")
    if r.status_code != 200:
        return 2
    kq = r.json()
    if not kq.get("ok"):
        return 2
    job_id, voice_id = kq["job_id"], kq["voice_id"]
    print(f"    job {job_id}  voice {voice_id}")

    from platform_core.db import get_session
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job

    t0 = time.time()
    while time.time() - t0 < a.cho_giay:
        gen = get_session()
        db = next(gen)
        try:
            j = db.get(Job, job_id)
            tt, res, err = j.status, j.result, j.error
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
        if tt in (JOB_DONE, JOB_ERROR, JOB_CANCELLED):
            print(f"[4] job {tt} sau {time.time() - t0:.0f}s")
            if err:
                print(f"    loi: {err}")
            print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
            if tt != JOB_DONE:
                return 1
            chon = (res or {}).get("chon_doan")
            if not chon:
                # Bo chon chay im lang thi khong ai biet no co chay khong.
                print("⚠️ result KHONG co `chon_doan` — bo chon khong chay, "
                      "hoac khong bao cao. Xem `engine.ghi_danh`.")
                return 1
            print(f"\n✅ bo chon da chay: {chon.get('bat_dau_s')}s → "
                  f"{chon.get('ket_thuc_s')}s | {chon.get('ly_do')}")
            return 0
        time.sleep(5)
    print(f"HET {a.cho_giay}s ma job van {tt}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
