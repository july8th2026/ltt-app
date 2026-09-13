"""do_cong_q_soak.py — CONG Q: soak TAI HON HOP.

## ⚠️ Spec khong dinh nghia cong nay — toi dinh nghia no, va noi ro la the

`BANG_DOI_SOAT` chi co mot dong: *"Soak hon hop — doi A-P qua truoc"*. Khong co
tep spec nao ta chi tiet. Nen dinh nghia duoi day la cua toi, va no duoc chon
theo mot nguyen tac: **Q chi co nghia neu no them chieu THOI GIAN DUOI TAI TRON
vao nhung bat bien ma F/I/O/P da chot tung cai mot.**

    F  hai model dong thoi          -> nhung do trong MOT lot
    I  residency anh <-> LLM        -> nhung do MOT chu trinh
    O  tien: 7 tinh huong           -> nhung do tung tinh huong ROI NHAU
    P  ro lease 5 diem              -> nhung do sau TUNG kich ban

⇒ Q tron ca bon lai, chay lien tuc, va hoi: sau ngan ay luot, so sach co con
  can khong, suat co con nha khong, tru co con dung khong.

## Nam bat bien do o CUOI

| # | bat bien | vi sao no chi lo ra duoi tai keo dai |
|---|---|---|
| 1 | `execution_leases` ve 0 | mot duong ro hiem chi lo sau nhieu luot |
| 2 | residency ket o `llm` | xen ke anh/LLM nhieu lan moi lo trang thai ket |
| 3 | ca hai model van phuc vu | mot khoa bi phat se tat model o luot thu N |
| 4 | ty le hong <= 2 % | mot con so, khong phai cam giac |
| 5 | khong khoan credit treo | `hold` khong co `settle`/`refund` di kem |

⛔ VA MOT DIEU BO NAY KHONG PHAI: 10 phut khong phai mot gio. Bo nay do duoc
   "khong ro trong 10 phut tai tron", khong do duoc "chay duoc ca ngay". Ghi ro
   de khong ai doc no rong hon thu no noi.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import threading
import time
import uuid

# `hasattr` la loi cua kho (xem tools/bench_llm_hieu_nang.py): goi thang
# `sys.stdout.reconfigure` lam banh coc mypy TANG mot `union-attr`, va gate
# do o buoc 8/33 vi dung mot dong nay.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
GOC_CAY = r"D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-dual-model-4dfcf4"
sys.path.insert(0, GOC_CAY)

from tools.do_tai_hai_model import Khach, _doc_khoa  # noqa: E402

GOC = "https://app.lttstudios.com"
CHUA_XONG = ("queued", "running", "pending", "admitted", "dispatched")
DEM = {"chat": 0, "chat_hong": 0, "stream": 0, "stream_hong": 0,
       "anh": 0, "anh_hong": 0, "huy": 0}
KHOA = threading.Lock()


def _cong(k, n=1):
    with KHOA:
        DEM[k] += n


def _soi_db(cau: str):
    ma = (
        "import json,os,pathlib,sys\n"
        "sys.path.insert(0, r'" + GOC_CAY + "')\n"
        "if not os.environ.get('LTT_DATABASE_URL'):\n"
        "    t = pathlib.Path(r'C:\\LTTPlatform\\secrets\\app.env')\n"
        "    for d in t.read_text(encoding='utf-8', errors='replace').splitlines():\n"
        "        if d.strip().startswith('LTT_DATABASE_URL'):\n"
        "            os.environ['LTT_DATABASE_URL'] = d.split('=',1)[1].strip().strip('\"')\n"
        "            break\n"
        "from sqlalchemy import text\n"
        "from platform_core.db import get_engine\n"
        "with get_engine().connect() as c:\n"
        "    print(json.dumps([list(map(str, r)) for r in c.execute(text(" + repr(cau) + "))]))\n"
    )
    r = subprocess.run([sys.executable, "-c", ma], capture_output=True,
                       text=True, cwd=GOC_CAY, timeout=120)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def _chat(kh, model, dung):
    while not dung.is_set():
        ma, _ = kh.goi("/api/v1/chat/completions",
                       {"model": model, "max_tokens": 128,
                        "reasoning_effort": "none",
                        "messages": [{"role": "user", "content": "Say OK briefly."}]},
                       "POST", idem=str(uuid.uuid4()), timeout=180)
        _cong("chat" if ma == 200 else "chat_hong")
        time.sleep(1)


def _stream(kh, khoa_tho, dung):
    import httpx
    while not dung.is_set():
        try:
            with httpx.Client(timeout=120.0) as c:
                with c.stream("POST", f"{GOC}/api/v1/messages",
                              json={"model": "ltt-3.8", "stream": True,
                                    "max_tokens": 256,
                                    "messages": [{"role": "user",
                                                  "content": "Count to 60."}]},
                              headers={"Authorization": f"Bearer {khoa_tho}",
                                       "Idempotency-Key": str(uuid.uuid4())}) as r:
                    if r.status_code != 200:
                        _cong("stream_hong")
                    else:
                        n = 0
                        for _ in r.iter_raw():
                            n += 1
                            if n >= 4:
                                break          # CAT giua chung — dung duong L-08
                        _cong("stream")
                        _cong("huy")
        except Exception:                       # noqa: BLE001
            _cong("stream_hong")
        time.sleep(2)


def _anh(kh, dung):
    inp = {"prompt": "A quiet mountain lake at dawn", "count": 1}
    while not dung.is_set():
        ma, b = kh.goi("/api/v1/quotes", {"tool": "image.ltt", "input": inp},
                       "POST", idem=str(uuid.uuid4()), timeout=120)
        if ma != 200:
            _cong("anh_hong")
            time.sleep(10)
            continue
        ma, b = kh.goi("/api/v1/jobs",
                       {"tool": "image.ltt", "input": inp,
                        "quote": json.loads(b).get("quote")},
                       "POST", idem=str(uuid.uuid4()), timeout=120)
        if ma not in (200, 201, 202):
            _cong("anh_hong")
            time.sleep(10)
            continue
        jid = json.loads(b).get("id")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 300 and not dung.is_set():
            mj, bj = kh.goi(f"/api/v1/jobs/{jid}", None, "GET", timeout=60)
            if mj == 200:
                st = str(json.loads(bj).get("status") or "")
                if st and st not in CHUA_XONG:
                    _cong("anh" if st in ("done", "succeeded", "completed")
                          else "anh_hong")
                    break
            time.sleep(5)
        else:
            kh.goi(f"/api/v1/jobs/{jid}/cancel", {}, "POST",
                   idem=str(uuid.uuid4()), timeout=60)
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--khoa", required=True)
    ap.add_argument("--phut", type=float, default=10.0)
    a = ap.parse_args()
    tho = _doc_khoa(pathlib.Path(a.khoa))
    kh = Khach(GOC, tho)

    print("== 0. NEN ==")
    lease0 = _soi_db("SELECT COUNT(*) FROM execution_leases")
    print(f"   execution_leases = {lease0}")
    treo0 = _soi_db(
        "SELECT COUNT(*) FROM credit_entries e WHERE e.kind='hold' AND NOT EXISTS "
        "(SELECT 1 FROM credit_entries x WHERE x.ref_id=e.ref_id "
        " AND x.kind IN ('settle','refund'))")
    print(f"   khoan hold khong co settle/refund = {treo0}")

    print()
    print(f"== 1. SOAK {a.phut} phut: chat x2 model + stream-cat + job anh ==")
    dung = threading.Event()
    luong = [
        threading.Thread(target=_chat, args=(Khach(GOC, tho), "ltt-3.8", dung), daemon=True),
        threading.Thread(target=_chat, args=(Khach(GOC, tho), "ltt-3.5", dung), daemon=True),
        threading.Thread(target=_stream, args=(tho, dung), daemon=True),
        threading.Thread(target=_anh, args=(Khach(GOC, tho), dung), daemon=True),
    ]
    for t in luong:
        t.start()
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.phut * 60:
        time.sleep(30)
        with KHOA:
            print(f"   {time.monotonic() - t0:6.0f}s  {dict(DEM)}")
    dung.set()
    for t in luong:
        t.join(timeout=60)

    print()
    print("== 2. Nghi ngoi 30 s roi do BAT BIEN ==")
    time.sleep(30)
    lease1 = _soi_db("SELECT COUNT(*) FROM execution_leases")
    treo1 = _soi_db(
        "SELECT COUNT(*) FROM credit_entries e WHERE e.kind='hold' AND NOT EXISTS "
        "(SELECT 1 FROM credit_entries x WHERE x.ref_id=e.ref_id "
        " AND x.kind IN ('settle','refund'))")
    tt = _soi_db("SELECT trang_thai FROM gpu_residency")
    print(f"   execution_leases = {lease1}  (nen {lease0})")
    print(f"   hold khong doi   = {treo1}  (nen {treo0})")
    print(f"   residency        = {tt}")
    cuoi = {m: kh.goi("/api/v1/chat/completions",
                      {"model": m, "max_tokens": 64, "reasoning_effort": "none",
                       "messages": [{"role": "user", "content": "Say OK."}]},
                      "POST", idem=str(uuid.uuid4()), timeout=180)[0]
            for m in ("ltt-3.8", "ltt-3.5")}
    print(f"   ca hai model     = {cuoi}")

    print()
    print("== PHAN QUYET ==")
    tong = DEM["chat"] + DEM["stream"] + DEM["anh"]
    hong = DEM["chat_hong"] + DEM["stream_hong"] + DEM["anh_hong"]
    ty = hong / (tong + hong) * 100 if (tong + hong) else 100.0
    m1 = lease1 is not None and int(lease1[0][0]) == 0
    m2 = tt is not None and tt and str(tt[0][0]) == "llm"
    m3 = all(v == 200 for v in cuoi.values())
    m4 = ty <= 2.0
    m5 = (treo1 is not None and treo0 is not None
          and int(treo1[0][0]) <= int(treo0[0][0]))
    print(f"  1 execution_leases ve 0        : {'DAT' if m1 else 'TRUOT'}")
    print(f"  2 residency ket o `llm`        : {'DAT' if m2 else 'TRUOT'}")
    print(f"  3 ca hai model van phuc vu     : {'DAT' if m3 else 'TRUOT'} {cuoi}")
    print(f"  4 ty le hong {ty:.1f} % (<= 2 %)   : {'DAT' if m4 else 'TRUOT'} "
          f"({tong} xong / {hong} hong)")
    print(f"  5 khong them khoan credit treo : {'DAT' if m5 else 'TRUOT'}")
    print()
    print("  >> " + ("CONG Q DAT (soak {:.0f} phut). ⚠️ 10 phut KHONG phai mot gio."
                     .format(a.phut) if all([m1, m2, m3, m4, m5]) else
                     "CHUA DAT — doc tung dong tren."))
    return 0 if all([m1, m2, m3, m4, m5]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
