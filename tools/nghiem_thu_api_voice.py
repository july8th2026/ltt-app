r"""nghiem_thu_api_voice.py — §12-14: nghiem thu speech.ltt qua /api/v1 THAT.

Chay qua lop nap app.env (can LTT_DATABASE_URL + pepper de mint/verify key).
Goi may chu DANG CHAY qua loopback 127.0.0.1:8100 (bo qua Cloudflare cho on dinh).

Luong:
  1. §12  mint MOT key tam cho TEST-A (scope jobs:create, allowed_tools speech.ltt)
  2. §13  ma tran /quotes: hop le + bien speed + D03 reject (speed/language ngoai)
  3. §14  MOT job: /quotes -> /jobs -> poll -> done -> tai artifact
  4. §21  check chat luong artifact bang do_chat_luong (DNSMOS + ASR) qua vieneu-venv
  5. revoke key trong `finally` (§12/§31 — key tam PHAI revoke)

⛔ KHONG in token/key ra man hinh hay log.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

BASE = "http://127.0.0.1:8100"
PREFIX = "/api/v1"
CAU = "Xin chào, đây là bản đọc kiểm thử qua API công khai của LTT Studios."


def _preset_vi() -> str:
    from apps.ltt_voice import giong_mau
    for g in giong_mau.DANH_SACH:
        if getattr(g, "ngon_ngu", "") == "vi":
            return g.ma
    return giong_mau.MAC_DINH


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--tai-ve", default="", help="Duong luu artifact job de check chat luong.")
    a = ap.parse_args(argv)

    import requests

    from platform_core import users
    from platform_core.db import get_session
    from platform_core.public_api import keys as devkeys

    preset = _preset_vi()
    gen = get_session()
    db = next(gen)
    key = None
    ket = {"quote_scenarios": [], "job": None, "quality": None}
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            print(f"KHONG THAY tai khoan {a.email}")
            return 2
        key, token = devkeys.issue(
            db, user_id=str(u.id), name="tier2-api-tmp",
            scopes=("jobs:create", "jobs:read"), allowed_tools=("speech.ltt",))
        db.commit()
        H = {"Authorization": f"Bearer {token}"}
        print(f"§12 key tam da mint (khong in token) | preset={preset} | user={u.email}")

        # ── §13 ma tran /quotes ──────────────────────────────────────────────
        scen = [
            ("valid vi 1.0", {"text": CAU, "preset": preset, "speed": 1.0, "language": "vi"}, 200),
            ("speed 2.0 (bien tren)", {"text": CAU, "preset": preset, "speed": 2.0, "language": "vi"}, 200),
            ("speed 0.5 (bien duoi)", {"text": CAU, "preset": preset, "speed": 0.5, "language": "vi"}, 200),
            ("D03 speed 2.5 reject", {"text": CAU, "preset": preset, "speed": 2.5}, 400),
            ("D03 speed 0.1 reject", {"text": CAU, "preset": preset, "speed": 0.1}, 400),
            ("D03 language fr reject", {"text": CAU, "preset": preset, "language": "fr"}, 400),
            ("empty text reject", {"text": "", "preset": preset}, 400),
            ("voice_id+preset reject", {"text": CAU, "preset": preset, "voice_id": "vc_" + "0" * 32}, 400),
        ]
        print("\n§13 QUOTE MATRIX:")
        for ten, inp, want in scen:
            r = requests.post(f"{BASE}{PREFIX}/quotes", headers=H,
                              json={"tool": "speech.ltt", "input": inp}, timeout=30)
            ok = (r.status_code == want)
            reason = ""
            try:
                reason = r.json().get("code") or r.json().get("detail", "")[:50]
            except Exception:  # noqa: BLE001
                reason = r.text[:50]
            ket["quote_scenarios"].append({"ten": ten, "got": r.status_code,
                                           "want": want, "ok": ok, "reason": reason})
            print(f"  [{'OK ' if ok else 'SAI'}] {ten:26} -> {r.status_code} (muon {want}) {reason}")

        # ── §14 MOT job E2E ──────────────────────────────────────────────────
        print("\n§14 JOB E2E (speed 1.5, language vi):")
        inp = {"text": CAU, "preset": preset, "speed": 1.5, "language": "vi"}
        q = requests.post(f"{BASE}{PREFIX}/quotes", headers=H,
                          json={"tool": "speech.ltt", "input": inp}, timeout=30).json()
        print(f"  quote: credit={q.get('credit')} quote_token={'co' if q.get('quote') else 'khong'}")
        # /jobs BAT BUOC header Idempotency-Key (jobs.py:362 require_key), MOT
        # gia tri moi moi call — KHONG dat trong body.
        import uuid
        hj = {**H, "Idempotency-Key": uuid.uuid4().hex}
        jr = requests.post(f"{BASE}{PREFIX}/jobs", headers=hj,
                           json={"tool": "speech.ltt", "quote": q.get("quote"), "input": inp},
                           timeout=30).json()
        jid = jr.get("id")
        if not jid:
            print(f"  /jobs LOI: {json.dumps(jr, ensure_ascii=False)[:300]}")
        print(f"  job id={jid} status={jr.get('status')}")
        st = jr
        for _ in range(150):
            time.sleep(2)
            st = requests.get(f"{BASE}{PREFIX}/jobs/{jid}", headers=H, timeout=30).json()
            if st.get("status") in ("done", "error", "cancelled", "succeeded", "failed"):
                break
        print(f"  ket qua job: {st.get('status')}")
        ket["job"] = {"id": jid, "status": st.get("status"),
                      "result_keys": list((st.get("result") or {}).keys())}
        print(f"  result: {json.dumps(st.get('result'), ensure_ascii=False)[:300]}")

        # ── tai artifact + §21 chat luong ────────────────────────────────────
        if a.tai_ve and st.get("status") in ("done", "succeeded"):
            res = st.get("result") or {}
            audio_key = res.get("audio_key") or res.get("audio") or ""
            if audio_key:
                from platform_core.storage import get_storage
                try:
                    with get_storage().open(audio_key) as f:
                        data = f.read()
                    with open(a.tai_ve, "wb") as f:
                        f.write(data)
                    print(f"  da tai artifact: {a.tai_ve} ({len(data)} byte)")
                    ket["quality"] = _cham_chat_luong(a.tai_ve, CAU)
                except Exception as e:  # noqa: BLE001
                    print(f"  (khong tai/cham duoc artifact: {type(e).__name__}: {e})")

        print("\n__KET_QUA_JSON__" + json.dumps(ket, ensure_ascii=False))
        return 0
    finally:
        if key is not None:
            try:
                devkeys.revoke(db, key)
                db.commit()
                print("\n§12/§31 key tam DA REVOKE.")
            except Exception as e:  # noqa: BLE001
                print(f"\n⛔ REVOKE key that bai: {type(e).__name__}: {e} — REVOKE TAY NGAY.")
        try:
            next(gen)
        except StopIteration:
            pass


def _cham_chat_luong(duong_wav: str, text: str) -> dict | None:
    """Chay do_chat_luong (DNSMOS + ASR) qua vieneu-venv tren artifact."""
    vieneu = r"C:\LTTPlatform\vieneu-venv\Scripts\python.exe"
    if not os.path.isfile(vieneu):
        return None
    out_json = duong_wav + ".chatluong.json"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(
        [vieneu, "-m", "voice_sidecar.do_chat_luong", duong_wav,
         "--text", text, "--json", out_json],
        cwd=root, capture_output=True, text=True, timeout=300)
    if os.path.isfile(out_json):
        with open(out_json, encoding="utf-8") as f:
            d = json.load(f)
        dnsmos = d.get("dnsmos") or {}
        de_hieu = d.get("de_hieu") or {}
        print(f"  §21 CHAT LUONG: DNSMOS ovrl={dnsmos.get('ovrl')} "
              f"| CER={de_hieu.get('cer')} WER={de_hieu.get('wer')}")
        return {"dnsmos": dnsmos, "de_hieu": de_hieu}
    print(f"  (do_chat_luong khong ra json; stderr: {(r.stderr or '')[:150]})")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
