"""Nghiem thu SONG: giet worker giua chung -> job co duoc nhat lai khong.

    python tools\\nghiem_thu_mo_coi.py            # ~7 phut, gan nhu toan ngu

⭐ Vi sao cong cu nay ton tai du DA CO ba test cho `reclaim_orphans`.

`test_67`, `test_150` va `test_313` deu lam MOT viec: dat `heartbeat_at` lui
ve qua khu roi goi `reclaim_orphans()` va xem no tra ve 1. Tuc chung kiem
**phia doc** — "cho mot nhip cu, ham nay co nhat khong".

Hai phia con lai khong test nao cham toi:

  1. **Phia GHI** — worker that co that su cap nhat `heartbeat_at` khi dang
     chay khong? Do 07/09: `platform_core/jobs.py:248 heartbeat()` **khong
     duoc goi o dau ca**. Nhip cua job chi nhich khi app goi `ctx.progress`
     (`jobs.py:336 set_progress`). Do la mot hop dong THAT nhung KHONG duoc
     cuong che — `apps/taovideo/jobs.py:5` ghi ro no.
  2. **Phia LICH** — co vong nao TU goi nhat lai khong, hay phai goi tay?
     (`job_runner.py:1640`, moi luot cua vong worker.)

Mot bo test xanh o phia doc van tuong thich hoan toan voi mot he thong
khong bao gio nhat lai gi — vi khong ai ghi nhip, hoac khong ai goi vong.

⛔ Dung bien cai nay thanh mot buoc gate. No ngu ~7 phut theo dung
   `ORPHAN_TIMEOUT` that; rut ngan thoi gian ay bang cach vi nhip ve qua khu
   la quay lai dung phep do ma ba test kia da lam roi.

## Hai lop doi chung — vi mot ket qua khong doi chung thi khong phai phat hien

Neu chi do "sau khi giet, worker B nhan job", ket qua ay con khop voi hai
gia thuyet KHAC va deu tam thuong:

  A. worker A chua bao gio thuc su chay  -> phai chung minh nhip TIEN truoc khi giet
  B. lenh giet khong an, A van song      -> phai chung minh nhip DUNG IM sau khi giet

Ca hai deu phai dat thi ket luan moi co nghia. Script thoat 1 va noi ro khi
mot trong hai do.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

CHO_CHAY = 90       # giay cho worker A nhan job + ghi >= 2 nhip
CHO_IM = 45         # giay quan sat sau khi giet (doi chung B)
CHO_NHAT = 480      # giay cho worker B nhat lai (ORPHAN_TIMEOUT = 5')


# --------------------------------------------------------------- worker con
def _lam_worker(worker_id: str) -> None:
    """Worker THAT — chi thay handler bang mot ham chay lau.

    Moi thu khac la ma kho that: `run_forever` that, vong `reclaim_orphans`
    that, duong ghi nhip that (`ctx.progress` -> `jobs.set_progress`).
    """
    from platform_core import jobs as jobq
    from platform_core.job_runner import run_forever

    def _cham(params, ctx):
        n = int(params.get("buoc", 30))
        for i in range(n):
            ctx.progress(int(100 * i / n), f"buoc {i}")
            time.sleep(20)
        return {"xong": True}

    jobq.resolve_handler = lambda job_type: _cham
    run_forever(worker_id, maintenance=False)


# ------------------------------------------------------------- dieu phoi
def _chay(thu_muc: Path) -> int:
    thu_muc.mkdir(parents=True, exist_ok=True)
    db_tep = thu_muc / "mocoi.sqlite"
    if db_tep.exists():
        db_tep.unlink()
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{db_tep.as_posix()}"

    from platform_core import db as dbmod
    from platform_core import jobs as jobq
    from platform_core import registry
    from platform_core.models import Job

    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    buoc: list[dict] = []

    def ghi(nhan: str, **kw) -> None:
        buoc.append({"buoc": nhan, **kw})
        print("  " + nhan + ": "
              + "  ".join(f"{k}={v}" for k, v in kw.items()), flush=True)

    def doc(jid):
        d = next(dbmod.get_session())
        try:
            j = d.get(Job, jid)
            return j.status, j.heartbeat_at, j.worker_id, int(j.attempts or 0)
        finally:
            d.close()

    def sinh(wid: str):
        return subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker", wid],
            env=dict(os.environ, PYTHONPATH=str(GOC)), cwd=str(GOC),
            stdout=open(thu_muc / f"{wid}.log", "wb"),
            stderr=subprocess.STDOUT)

    d = next(dbmod.get_session())
    job = jobq.submit(d, user_id="u-nghiem-thu", app_slug="nghiem-thu",
                      job_type="nghiemthu.cham", params={"buoc": 30},
                      max_attempts=3)
    d.commit()
    jid = job.id
    d.close()
    ghi("nop job", id=jid[:8], trang_thai="queued")

    # ---- worker A + doi chung A: nhip phai TIEN -----------------------
    wa = sinh("worker-A")
    ghi("khoi dong worker A", pid=wa.pid)

    nhip: list = []
    het = time.time() + CHO_CHAY
    while time.time() < het:
        st, hb, _wid, _att = doc(jid)
        if st == "running" and hb is not None and (not nhip or hb != nhip[-1]):
            nhip.append(hb)
            if len(nhip) >= 2:
                break
        time.sleep(2)

    st, hb, wid, att = doc(jid)
    ghi("worker A da nhan job", trang_thai=st, worker=wid, luot=att,
        so_nhip_khac_nhau=len(nhip))
    if st != "running" or len(nhip) < 2:
        wa.kill()
        print("\nDOI CHUNG A DO: worker A khong chay hoac khong ghi nhip.\n"
              "   => 'worker chet duoc nhat lai' khong chung minh duoc gi,\n"
              "      vi no chua bao gio song. Dung.")
        return 1
    ghi("DOI CHUNG A dat", y_nghia="worker that CO ghi nhip khi chay")

    # ---- giet + doi chung B: nhip phai DUNG IM ------------------------
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(wa.pid)],
                   capture_output=True)
    time.sleep(2)
    hb_giet = doc(jid)[1]
    ghi("da giet worker A", nhip_luc_giet=str(hb_giet)[:19])

    time.sleep(CHO_IM)
    hb_sau = doc(jid)[1]
    ghi(f"{CHO_IM}s sau khi giet", nhip=str(hb_sau)[:19],
        dung_im=(hb_sau == hb_giet))
    if hb_sau != hb_giet:
        print("\nDOI CHUNG B DO: nhip van tien sau khi giet -> tien trinh con\n"
              "   song. Moi ket luan sau day la ve mot worker chua chet.")
        return 1
    ghi("DOI CHUNG B dat", y_nghia="lenh giet an that, khong con ai dap nhip")

    # ---- worker B nhat lai --------------------------------------------
    wb = sinh("worker-B")
    ghi("khoi dong worker B", pid=wb.pid, cho="ORPHAN_TIMEOUT ke tu nhip cuoi")

    t0 = time.time()
    cho = None
    het = time.time() + CHO_NHAT
    while time.time() < het:
        _st, _hb, wid, _att = doc(jid)
        if wid == "worker-B":
            cho = round(time.time() - t0)
            break
        time.sleep(5)

    st, hb, wid, att = doc(jid)
    ghi("ket qua", trang_thai=st, worker=wid, luot=att, giay_cho=cho)
    wb.kill()

    dat = wid == "worker-B" and st in ("running", "queued")
    ghi("KET LUAN", dat=dat)
    (thu_muc / "ket_qua.json").write_text(
        json.dumps({"dat": dat, "job": jid, "buoc": buoc},
                   ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print("\n" + ("DAT" if dat else "KHONG DAT"))
    return 0 if dat else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--worker", default="",
                   help="noi bo: chay lam tien trinh worker con")
    p.add_argument("--thu-muc", default="",
                   help="noi ghi CSDL tam + log (mac dinh test-results/mocoi)")
    a = p.parse_args()
    if a.worker:
        _lam_worker(a.worker)
        return 0
    return _chay(Path(a.thu_muc) if a.thu_muc else GOC / "test-results" / "mocoi")


if __name__ == "__main__":
    raise SystemExit(main())
