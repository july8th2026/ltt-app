"""Chay MOT lan Auto Scan Video tren WORKER THAT cua may chu, va DO no.

    python tools\\asv_chay_worker_that.py tao  --video "<duong>" [--preset ...]
    python tools\\asv_chay_worker_that.py theo-doi <run_id> [--tran-phut 90]
    python tools\\asv_chay_worker_that.py worker [--giay 3600]

## Vi sao tep nay ton tai

Lan `asv-toc-do` do duoc: **0 / 19.979** luot job trong log worker production la
`auto_scan_video`/`asv_*`. Tuc moi nghiem thu cua san pham nay (12/12 giai doan,
QC dat, hai preset) chay trong KHUON TEST — chua bao gio tren tien trinh worker
that, noi PATH, quyen, bien moi truong va thu muc lam viec deu khac.

⛔ Day KHONG phai mot phep kiem: no khong khang dinh gi, no **do** va **ghi
   traceback nguyen van**. Muc tieu la TIM CHO VO, khong phai dat mau xanh.

## Ba dieu ve moi truong that ma khuon test khong tai hien duoc

1. `LTT_WORKER_POOLS = "api:6, gpu+ffmpeg:1, voice:1"` — bon app cua ASV
   (`auto_scan_video`=api, `asv_media`=ffmpeg, `asv_voice`=voice, `asv_gpu`=gpu)
   nam tren BA lan khac nhau. Mot giai doan chuyen lan la mot lan doi tien
   trinh, va do la cho thoi gian chet sinh ra.
2. Worker chay duoi `LocalSystem`: PATH khac phien nguoi dung (da tung thieu
   `ffmpeg`).
3. Co `LTT_AUTO_SCAN_VIDEO` **khong** co trong `secrets\\app.env`. No chi chan
   duong TAO (`dich_vu_tao.da_mo`) — ⛔ no KHONG chan worker thi hanh giai doan.
   Nen worker production **nhat duoc** job ASV du san pham "chua mo".

## Cach do giay CPU moi giai doan

`jobs.worker_id` la `"<host>:<pid>"` (xem `job_worker._chay_mot_worker`), nen
biet dung tien trinh nao chay giai doan nao. Lay `KernelModeTime + UserModeTime`
cua CA CAY tien trinh do luc bat dau va luc ket thuc giai doan; hieu la giay CPU.
Mot worker chay MOT job mot luc, nen nhieu tu job khac la khong dang ke.

⛔ Khong bao cao mot cot. `docs/QUY_TAC_CHAY_LENH_NANG.md` §2b: `giay CPU` tra
   loi "ton bao nhieu suc tinh", `dong ho tuong` tra loi "dieu kien do" — va
   tuong dai + CPU thap la dang CHO, khong phai dang tinh.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

APP_ENV = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")

#: Cac giai doan cua chuoi, lay tu ma nguon chu khong go tay.
def _ten_giai_doan() -> tuple[str, ...]:
    from apps.auto_scan_video import pipeline
    return pipeline.TEN_GIAI_DOAN


def nap_env() -> None:
    """Nap `app.env` vao tien trinh NAY. ⛔ Khong ghi, khong in gia tri."""
    if not APP_ENV.is_file():
        raise SystemExit(f"khong thay {APP_ENV} — tep nay chi chay tren may chu")
    for dong in APP_ENV.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        ten, _, gt = dong.partition("=")
        os.environ.setdefault(ten.strip(), gt.strip())


# ══════════════════════════════════════════════════════════════════════════════
#  Giay CPU cua mot CAY tien trinh
# ══════════════════════════════════════════════════════════════════════════════

def cpu_cay(pid: int) -> tuple[float, int]:
    """`(giay CPU cong don cua CA CAY tien trinh, so tien trinh dem duoc)`.

    ⭐ `psutil`, ⛔ khong `Get-CimInstance Win32_Process`: ban dau ham nay goi
       PowerShell liet ke TOAN BO bang tien trinh moi lan, va mot lan goi mat
       **hon 40 giay** tren may nay — tuc phep do tro thanh mot nghi can, dung
       thu `QUY_TAC_CHAY_LENH_NANG.md` §3.3 cam. `psutil` hoi dung mot cay.

    ⚠️ Tien trinh CHAU (ffmpeg, demucs, whisper do worker de ra) duoc CONG VAO
       — do la ca muc dich. Mot giai doan ASV tieu phan lon suc tinh o tien
       trinh con, va mot con so chi dem tien trinh cha se noi rang `render`
       gan nhu mien phi.

    🔴 **GIOI HAN DA DO, 25/09: con so nay la CAN DUOI, khong phai so that.**
       Tren Windows `psutil` KHONG cong CPU cua tien trinh con da thoat vao cha
       (`children_user`/`children_system` dung yen o 0,0 — do bang mot tien
       trinh con dot 8 trieu phep nhan). Nen mot `ffmpeg` sinh ra va thoat
       **giua hai lan lay mau** bien mat khoi so do.

       ⇒ Dung duoc cho giai doan DAI (demucs, whisper, TTS, render: tien trinh
         con song hang phut, chac chan bi bat). ⛔ Khong dung duoc cho giai
         doan NGAN: `media_prepare` do ra **1,3 giay CPU / 51 giay tuong**, va
         phan lon phan thieu la mot chuoi `ffprobe`/`ffmpeg` chop nhoang.

       ⭐ Cach do dung la Job Object cua Windows (ke ca tien trinh con da thoat),
         nhung no doi quyen tren tien trinh khong phai cua minh. Ghi ra day thay
         vi de mot con so thieu trong nhu mot con so du.
    """
    import psutil

    tong = 0.0
    so = 0
    try:
        goc = psutil.Process(int(pid))
        cac = [goc] + goc.children(recursive=True)
    except Exception as exc:                              # noqa: BLE001
        print(f"[cpu_cay] khong doc duoc tien trinh {pid}: {type(exc).__name__}",
              file=sys.stderr)
        return (0.0, 0)
    for p in cac:
        try:
            t = p.cpu_times()
            tong += float(t.user) + float(t.system)
            so += 1
        except Exception as exc:                          # noqa: BLE001
            print(f"[cpu_cay] bo qua mot tien trinh con (da thoat?): "
                  f"{type(exc).__name__}", file=sys.stderr)
            continue
    return (round(tong, 2), so)


def _pid_cua(worker_id: str) -> int:
    """`"<host>:<pid>"` -> pid. 0 khi khong doc duoc."""
    try:
        return int(str(worker_id or "").rsplit(":", 1)[-1])
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
#  tao
# ══════════════════════════════════════════════════════════════════════════════

def lenh_tao(args) -> int:
    return 0 if _tao(args) else 2


def lenh_chay(args) -> int:
    """`tao` roi `theo-doi` trong MOT luot — mot lan giu khoa may, khong hai."""
    run_id = _tao(args)
    if not run_id:
        return 2
    args.run_id = run_id
    return lenh_theo_doi(args)


def _tao(args) -> str:
    nap_env()
    # 🔑 Co chi bat trong TIEN TRINH NAY. ⛔ Khong ghi vao app.env, khong restart
    #    dich vu nao — `dich_vu_tao.da_mo()` doc `os.environ` luc goi.
    os.environ["LTT_AUTO_SCAN_VIDEO"] = "1"
    os.chdir(GOC)

    from sqlalchemy import text

    from apps.auto_scan_video import dich_vu_tao, features
    from platform_core import credit, db as dbmod

    video = pathlib.Path(args.video)
    if not video.is_file():
        print("KHONG THAY PHIM:", video)
        return ""
    print("PHIM  :", video)
    print("BYTE  :", video.stat().st_size)
    print("PRESET:", args.preset)

    tho = {
        "preset": args.preset,
        "ngon_ngu_nguon": args.nguon,
        "ngon_ngu_dich": args.dich,
        "che_do_giong": args.che_do_giong,
        "giong_id": args.giong,
    }
    for s in dbmod.get_session():
        r = s.execute(text("SELECT id FROM users WHERE email = :e"),
                      {"e": args.email}).first()
        if r is None:
            print("KHONG CO TAI KHOAN:", args.email)
            return ""
        owner = r.id
        print("CHU   :", args.email, owner, "| so_du =", credit.so_du(s, owner))
        try:
            ho_so = dich_vu_tao.dung_cai_dat(s, owner_id=owner, tho=tho)
        except Exception as exc:                          # noqa: BLE001
            s.rollback()
            print("VO O CUA DUYET DAU VAO:", type(exc).__name__, exc)
            raise
        try:
            run = features.tao_run_tu_tai_len(
                s, owner_id=owner, duong_tep=str(video),
                ten_tep=video.name, settings=ho_so)
            s.commit()
        except Exception as exc:                          # noqa: BLE001
            s.rollback()
            print("VO O TAO RUN:", type(exc).__name__, exc)
            raise
        print("RUN_ID:", run.id)
        print("CREDIT GIU:", run.credit_held)
        print("SOURCE_KEY:", run.source_key)
        print("SO_DU SAU KHI GIU:", credit.so_du(s, owner), flush=True)
        return str(run.id)
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  theo-doi
# ══════════════════════════════════════════════════════════════════════════════

def lenh_theo_doi(args) -> int:
    nap_env()
    os.chdir(GOC)

    from sqlalchemy import text

    from platform_core import db as dbmod

    run_id = args.run_id
    het = time.monotonic() + args.tran_phut * 60.0
    t0 = time.time()

    #: stage -> ho so do
    do: dict[str, dict] = {}
    #: so luot job `auto_scan_video.advance` da thay
    advance: dict = {}
    truoc_stage: dict[str, str] = {}
    truoc_run = ""
    nhat_ky: list[dict] = []

    def ghi(ma: str, **kw):
        muc = {"t": round(time.time() - t0, 1),
               "gio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "ma": ma, **kw}
        nhat_ky.append(muc)
        print(f"[{muc['t']:8.1f}s] {ma} " +
              " ".join(f"{k}={v}" for k, v in kw.items()), flush=True)

    # ⛔ MOT phien cho ca vong theo doi. Mo/dong mot phien moi mot nhip (1.200
    #    nhip cho mot gio) la 1.200 lan bat tay voi CSDL PRODUCTION — dung kieu
    #    "phep do tro thanh nghi can" ma QUY_TAC_CHAY_LENH_NANG §3.3 canh bao.
    #    `rollback()` dau moi nhip mo mot giao dich moi ⇒ van doc duoc du lieu moi.
    dbmod.get_engine()
    # `get_engine()` vua goi o tren dat `_session_factory` — cung mot khang
    # dinh voi `platform_core/db.py::get_session()` cho dung bien nay.
    assert dbmod._session_factory is not None      # noqa: SLF001
    phien = dbmod._session_factory()     # noqa: SLF001 - khong co cua cong khai
    xong = False
    # ⭐ DIEU KIEN DO, lay mau moi nhip. `QUY_TAC_CHAY_LENH_NANG.md` §2b: cot
    #    `giay CPU` tra loi *"ton bao nhieu suc tinh"* va mien nhiem voi hang
    #    xom; cot `dong ho tuong` chi co nghia KEM theo tai nen luc do. Khong
    #    ghi tai nen thi mot con so tuong la mot con so khong ai doc lai duoc.
    import psutil
    psutil.cpu_percent(None)             # moc dau cho lan lay mau ke tiep
    nen: list[float] = []
    try:
        while time.monotonic() < het:
            nen.append(psutil.cpu_percent(None))
            s = phien
            s.rollback()
            run = s.execute(text(
                "SELECT id, status, credit_held, credit_actual, error "
                "FROM asv_run WHERE id = :r"), {"r": run_id}).first()
            if run is None:
                print("KHONG CO RUN", run_id)
                return 2
            if run.status != truoc_run:
                ghi("run", trang_thai=run.status, credit_actual=run.credit_actual,
                    loi=(run.error or "")[:200])
                truoc_run = run.status

            # 🔑 Bam theo bang `jobs` chu khong bang `asv_stage`.
            #
            #    `asv_stage.status` di `pending -> queued -> succeeded`; trang
            #    thai `running` cua NO do handler dat va co the khong bao gio
            #    lot vao mot nhip 3 giay — luot dau 25/09 mat sach so do cua
            #    `media_prepare` (12 s) dung vi vay. `jobs` thi luon co
            #    `started_at`/`finished_at`/`worker_id` va nen tang ghi chung
            #    nguyen tu.
            #
            # ⭐ `plan_id = run.id` va `step_id = <ten giai doan>` do chinh
            #    `_nop_giai_doan_san_sang` dat — day la quan he cha-con san co
            #    cua nen tang, khong phai mot phep noi tu bia.
            for j in s.execute(text(
                    "SELECT id, job_type, step_id, status, worker_id, attempts, "
                    "       max_attempts, error, created_at, started_at, "
                    "       finished_at FROM jobs "
                    "WHERE plan_id = :r AND step_id <> '' "
                    "ORDER BY created_at"), {"r": run_id}).all():
                khoa = f"{j.step_id}#{j.id}"
                if truoc_stage.get(khoa) == j.status:
                    continue
                truoc_stage[khoa] = j.status
                wid = j.worker_id or ""
                ho = do.setdefault(j.step_id, {"stage": j.step_id})
                if j.status == "running" and "cpu_dau" not in ho:
                    pid = _pid_cua(wid)
                    cpu, n = cpu_cay(pid) if pid else (0.0, 0)
                    ho.update(worker_id=wid, pid=pid, cpu_dau=cpu,
                              tuong_dau=time.time(), so_tien_trinh_dau=n,
                              nen_tu=len(nen))
                if j.status in ("done", "error", "cancelled"):
                    pid = int(ho.get("pid") or _pid_cua(wid))
                    cpu, n = cpu_cay(pid) if pid else (0.0, 0)
                    ho["cpu_cuoi"] = cpu
                    if "cpu_dau" in ho:
                        ho["cpu_giay"] = round(cpu - float(ho["cpu_dau"]), 1)
                    # ⭐ Dong ho tuong lay tu CSDL, khong tu `time.time()` cua
                    #    tien trinh do: nhip 3 giay lam tron len toi 3 giay moi
                    #    dau, va mot giai doan 12 giay thi do la 25 % sai so.
                    if j.started_at and j.finished_at:
                        ho["tuong_giay"] = round(
                            (j.finished_at - j.started_at).total_seconds(), 1)
                    ho["bat_dau"] = str(j.started_at)
                    ho["ket_thuc"] = str(j.finished_at)
                    ho["job_id"] = j.id
                    ho["worker_id"] = wid
                    ho["trang_thai"] = j.status
                    ho["lan_thu"] = f"{j.attempts}/{j.max_attempts}"
                    ho["loi_job"] = j.error or ""
                    mau = nen[int(ho.get("nen_tu") or 0):] or [0.0]
                    ho["cpu_nen_tb"] = round(sum(mau) / len(mau), 1)
                    ho["cpu_nen_dinh"] = round(max(mau), 1)
                ghi("stage", ten=j.step_id, job=j.status, lan=j.attempts,
                    worker=wid, cpu=ho.get("cpu_giay", ""),
                    tuong=ho.get("tuong_giay", ""), loi=(j.error or "")[:300])

            # ⭐ Dem luot `advance`: cau hoi 3 cua brief (`jobs._advance` co tu
            #    noi vo han khong). So mong doi la 12 + 1 luot mo dau.
            # ⛔ DEM, khong liet ke. Luot 25/09 in tung dong va luot do sinh
            #    1.043 job trong 78 giay — ban ghi tro nen khong doc noi, va
            #    chinh phep do tro thanh mot nghi can.
            d = s.execute(text(
                "SELECT count(*) n, count(*) FILTER "
                "       (WHERE status IN ('queued','running')) song, "
                "       min(created_at) a, max(created_at) b, "
                "       max(error) FILTER (WHERE error <> '') loi "
                # ⚠️ `plan_id` RONG o job dieu phoi: `features._nop_dieu_phoi`
                #    khong dat `plan_id`/`step_id` (khac `_nop_giai_doan_san_sang`).
                #    Nen phai loc qua `params`, va do la mot khoang trong quan
                #    sat that: khong co quan he cha-con nao noi luot `advance`
                #    voi lan chay cua no.
                "FROM jobs WHERE job_type = 'auto_scan_video.advance' "
                "  AND params->>'run_id' = :r"), {"r": run_id}).first()
            advance.update(
                tong=int(d.n or 0), dang_song=int(d.song or 0),
                dau=str(d.a), cuoi=str(d.b), loi=(d.loi or "")[:400])
            if int(d.n or 0) // 250 != int(advance.get("_moc") or -1):
                advance["_moc"] = int(d.n or 0) // 250
                ghi("advance", tong=d.n, dang_song=d.song,
                    loi=(d.loi or "")[:200])

            xong = run.status in ("done", "error", "cancelled")
            if xong:
                break
            time.sleep(args.nhip)
    finally:
        phien.rollback()
        phien.close()
    if not xong:
        ghi("HET TRAN THOI GIAN", tran_phut=args.tran_phut)

    # ── bang ket qua ──────────────────────────────────────────────────────────
    ten = _ten_giai_doan()
    print("\n== GIAI DOAN ==")
    print("⛔ Hai cot, khong trung binh: `CPU s` = suc tinh (mien nhiem hang "
          "xom); `tuong s` + `CPU nen %` = dieu kien do.")
    print(f"{'giai doan':16} {'job':10} {'CPU s':>9} {'tuong s':>9} "
          f"{'loi tb':>7} {'CPU nen %':>10} {'lan thu':>8}  worker")
    for g in ten:
        h = do.get(g, {})
        # `cpu_bc` (bao cao) — ⛔ khong dat lai ten `cpu`: bien do o vong lap
        # lay mau phia tren la `float` (tu `cpu_cay()`), con day la mot gia
        # tri doc tho tu `dict` (`Any | None`) — cung ten trong CUNG mot ham
        # se ep mypy suy mot kieu chung sai cho ca hai.
        cpu_bc = h.get("cpu_giay")
        tuong = h.get("tuong_giay")
        loi_tb = (round(cpu_bc / tuong, 2) if isinstance(cpu_bc, (int, float))
                  and isinstance(tuong, (int, float)) and tuong else "-")
        print(f"{g:16} {str(h.get('trang_thai','(chua chay)')):10} "
              f"{cpu_bc if cpu_bc is not None else '-'!s:>9} "
              f"{tuong if tuong is not None else '-'!s:>9} "
              f"{loi_tb!s:>7} {h.get('cpu_nen_tb','-')!s:>10} "
              f"{h.get('lan_thu','-')!s:>8}  {h.get('worker_id','')}")
        if h.get("loi_job"):
            print(f"    LOI: {h['loi_job'][:500]}")

    # 🔑 Thoi gian chet = khe giua `finished_at` cua job giai doan truoc va
    #    `started_at` cua job giai doan sau — CA HAI lay tu CSDL. Con so
    #    `16-20 s` o `L_TOC_DO_GPU` §3.1 la SUY RA tu kien truc, chua ai do.
    print("\n== THOI GIAN CHET giua cac giai doan (giay, tu CSDL) ==")
    from datetime import datetime as _dt
    def _gio(v):
        try:
            return _dt.fromisoformat(str(v))
        except Exception as exc:                          # noqa: BLE001
            print(f"[thoi gian chet] moc thoi gian khong doc duoc {v!r}: "
                  f"{type(exc).__name__}", file=sys.stderr)
            return None
    moc = sorted(
        ((a, b, g) for g, h in do.items()
         if (a := _gio(h.get("bat_dau"))) and (b := _gio(h.get("ket_thuc")))),
        key=lambda x: x[0])
    chet = []
    for i in range(1, len(moc)):
        d = round((moc[i][0] - moc[i - 1][1]).total_seconds(), 1)
        chet.append((moc[i - 1][2], moc[i][2], d))
        print(f"  {moc[i-1][2]:16} -> {moc[i][2]:16} {d:8.1f} s")
    if chet:
        ds = [d for _a, _b, d in chet]
        print(f"  TONG {round(sum(ds),1)} s | trung binh {round(sum(ds)/len(ds),1)} s "
              f"| min {min(ds)} | max {max(ds)}")

    print("\n== LUOT `advance` ==")
    print(f"  THAT   : {advance.get('tong')}   (chuoi co {len(ten)} giai doan)")
    print(f"  dau    : {advance.get('dau')}")
    print(f"  cuoi   : {advance.get('cuoi')}")
    print(f"  loi    : {advance.get('loi') or '(khong)'}")

    ra = {"run_id": run_id, "giai_doan": do, "advance": advance,
          "thoi_gian_chet": chet, "nhat_ky": nhat_ky}
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(ra, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        print("da ghi:", args.json)
    return 0


# ══════════════════════════════════════════════════════════════════════════════
#  worker rieng
# ══════════════════════════════════════════════════════════════════════════════

def lenh_lay_ket_qua(args) -> int:
    """Chep hien vat ban giao (.mp4 + .srt) ra mot cho ON DINH, va `ffprobe` no.

    🔴 **Chep NGAY khi `render` xong, ⛔ khong doi het luot.** Lan `asv-g17`
       chay 49 phut that roi mat sach: bao cao ghi SAU mot cum `assert`, assert
       no truoc, va thu muc tam bi don khi tien trinh thoat. ⭐ Cat hien vat
       TRUOC khi phan quyet.

    ⛔ Mot tep TON TAI khong chung minh no xem duoc — nen ham nay in ca co tep,
       thoi luong, co luong tieng khong, va bitrate. Da co ca `done` + QC `dat`
       + KHONG tep nao (`N-57`).
    """
    import shutil
    import subprocess

    nap_env()
    os.chdir(GOC)

    from sqlalchemy import text

    from apps.auto_scan_video import features
    from platform_core import db as dbmod
    from platform_core.storage import get_storage

    dich = pathlib.Path(args.dich_thu_muc)
    dich.mkdir(parents=True, exist_ok=True)
    kho = get_storage()
    ra = []
    for s in dbmod.get_session():
        run = s.execute(text(
            "SELECT * FROM asv_run WHERE id = :r"), {"r": args.run_id}).first()
        if run is None:
            print("KHONG CO RUN", args.run_id)
            return 2
        doi_tuong = features.lay_run(s, args.run_id, run.owner_id)
        for nhan, khoa in (("mp4", features.khoa_ket_qua(s, doi_tuong)),
                           ("srt", features.khoa_phu_de(s, doi_tuong))):
            if not khoa:
                print(f"{nhan.upper():4}: (KHONG CO — `render` chua succeeded "
                      f"hoac khong khai khoa)")
                continue
            duoi = pathlib.PurePosixPath(khoa).suffix or f".{nhan}"
            ten = f"{args.nhan}_{args.moc}{duoi}"
            d = dich / ten
            with kho.open(khoa) as f, d.open("wb") as g:
                shutil.copyfileobj(f, g)
            co = d.stat().st_size
            print(f"{nhan.upper():4}: {d}  |  {co} byte")
            ra.append((nhan, d, co))
        break

    for nhan, d, _co in ra:
        if nhan != "mp4":
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(d)],
            capture_output=True, text=True)
        if r.returncode != 0:
            print("FFPROBE HONG:", r.stderr.strip()[:500])
            continue
        tt = json.loads(r.stdout)
        fmt = tt.get("format", {})
        luong = tt.get("streams", [])
        print("  thoi_luong :", fmt.get("duration"))
        print("  bitrate    :", fmt.get("bit_rate"))
        print("  co_tieng   :", any(x.get("codec_type") == "audio" for x in luong))
        for x in luong:
            print(f"    {x.get('codec_type')} {x.get('codec_name')} "
                  f"{x.get('width','')}x{x.get('height','')} "
                  f"bitrate={x.get('bit_rate')}")
    return 0 if ra else 1


def lenh_worker(args) -> int:
    """MOT tien trinh worker RIENG. ⛔ Khong cham dich vu dang chay.

    `maintenance=False`: khong chay vong bao tri — viec nen da co dich vu
    production lam, va hai vong cung quet la hai lan cung mot viec.
    """
    import logging
    import socket

    nap_env()
    os.environ["LTT_AUTO_SCAN_VIDEO"] = "1"
    os.chdir(GOC)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from platform_core.job_runner import run_forever

    het = time.monotonic() + args.giay
    wid = f"{socket.gethostname()}:{os.getpid()}"
    print("WORKER RIENG:", wid, "| python:", sys.executable, flush=True)
    print("PATH co ffmpeg:", _tim_ffmpeg(), flush=True)
    run_forever(wid, stop=lambda: time.monotonic() > het, maintenance=False,
                capabilities=None)
    return 0


def _tim_ffmpeg() -> str:
    import shutil
    return shutil.which("ffmpeg") or "(KHONG THAY TREN PATH)"


# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    # 🔴 MOI `PATH` truoc moi viec (N-59). `ffmpeg` cai theo NGUOI DUNG (WinGet)
    #    nen chi nam tren USER Path; cong cu nay chay duoi quyen nang cao / SYSTEM
    #    thi nhan MACHINE Path va `ffprobe` tran o duoi se nem WinError 2.
    #    ⭐ Goi ham moi cung lam phep do `_tim_ffmpeg()` tra ve dung thu WORKER thay.
    from platform_core import media as _media
    _media.bao_dam_ffmpeg_tren_path()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="lenh", required=True)

    t = sub.add_parser("tao")
    t.add_argument("--video", required=True)
    t.add_argument("--preset", default="localize_preserve_picture")
    t.add_argument("--nguon", default="zh")
    t.add_argument("--dich", default="vi")
    t.add_argument("--che-do-giong", dest="che_do_giong", default="USER_SELECTED")
    t.add_argument("--giong", default="Minh Đức")
    t.add_argument("--email", default="khach1.thu@lttstudios.local")
    t.set_defaults(fn=lenh_tao)

    d = sub.add_parser("theo-doi")
    d.add_argument("run_id")
    d.add_argument("--tran-phut", type=float, default=90.0)
    d.add_argument("--nhip", type=float, default=3.0)
    d.add_argument("--json", default="")
    d.set_defaults(fn=lenh_theo_doi)

    c = sub.add_parser("chay", help="tao roi theo-doi trong MOT luot (mot lan khoa)")
    c.add_argument("--video", required=True)
    c.add_argument("--preset", default="localize_preserve_picture")
    c.add_argument("--nguon", default="zh")
    c.add_argument("--dich", default="vi")
    c.add_argument("--che-do-giong", dest="che_do_giong", default="USER_SELECTED")
    c.add_argument("--giong", default="Minh Đức")
    c.add_argument("--email", default="khach1.thu@lttstudios.local")
    c.add_argument("--tran-phut", type=float, default=90.0)
    c.add_argument("--nhip", type=float, default=3.0)
    c.add_argument("--json", default="")
    c.set_defaults(fn=lenh_chay)

    k = sub.add_parser("lay-ket-qua",
                       help="chep .mp4/.srt ra cho on dinh + ffprobe")
    k.add_argument("run_id")
    k.add_argument("--dich-thu-muc", dest="dich_thu_muc",
                   default=r"D:\LTTSTUDIOSAPP\_ket_qua")
    k.add_argument("--nhan", default="worker-that_v3_giu-hinh")
    k.add_argument("--moc", default=time.strftime("%Y%m%d-%H%M"))
    k.set_defaults(fn=lenh_lay_ket_qua)

    w = sub.add_parser("worker")
    w.add_argument("--giay", type=float, default=3600.0)
    w.set_defaults(fn=lenh_worker)

    args = ap.parse_args()
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
