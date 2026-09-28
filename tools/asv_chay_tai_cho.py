"""Chay day chuyen Auto Scan Video TU CAY LAM VIEC, bo hang doi, KHONG deploy.

    python tools\\asv_chay_tai_cho.py chay --video "<duong>" [--preset ...] [--thu-kho]
    python tools\\asv_chay_tai_cho.py chay --run-id <id> --tu voice_synthesis --den compose

## Van de tep nay giai

Hom nay, moi lan muon chay thu day chuyen phai **deploy** len
`C:\\LTTPlatform\\app` roi doi worker cua dich vu production nhat job — vi
worker chay ma DA DEPLOY, ⛔ khong phai ma cay lam viec. Deploy moi vong sua la
rat ton cong (B13 §5, chu du an hoi 28/09).

## Hai manh DA CO — dung lai, khong xay moi

    tools/asv_chay_worker_that.py
        nap_env()   (~dong 77)  -> nap C:\\LTTPlatform\\secrets\\app.env = khoa THAT
        _tao(args)  (~dong 169) -> tao mot lan chay ASV (dung lai NGUYEN VEN o day)

    apps/auto_scan_video/thi_hanh.py
        chay_giai_doan(ten, params, ctx=None)   (dong 436)
        docstring: "mot loi goi TRUC TIEP ngoai hang doi (script, test)"

    platform_core/job_runner.py
        JobContext(job_id, gpu_uuid=...)   (dong 140) — `ctx` THAT nen tang dung
        cho MOI job qua hang doi. Dung lai nguyen chu KHONG tu viet mot lop `ctx`
        rieng: moi giai doan doc `ctx.progress`/`ctx.is_cancelled`/`ctx.gpu_uuid`/
        `ctx.gpu_env()` qua `getattr(ctx, ..., None)`, nen mot `JobContext` that
        voi `job_id=""` la mot doi tuong HOP LE — no chi khong khop dong `Job`
        nao trong CSDL (xem muc "GIOI HAN" o duoi).

    platform_core/gpu_lease.py
        acquire()/heartbeat()/release()   — gianh MOT GPU that, nguyen tu.

⇒ Khoa voice, khoa LLM, GPU, R2, CSDL deu dung duoc tu cay lam viec MA KHONG
  deploy. Thu duy nhat thieu la mot NGUOI LAI — day la no.

## Vi sao KHONG di duong `worker`

`asv_chay_worker_that.py worker` mo mot tien trinh worker THAT, va no se
**TRANH job** voi dich vu production (ca hai cung khai nang luc ASV) — phan
lon giai doan se roi vao worker production, chay ma DA DEPLOY, dung thu ta
muon tranh. Tep nay bo qua CA HAI worker: goi thang `thi_hanh.chay_giai_doan`
trong TIEN TRINH CUA CHINH NO, khong nop job nao vao hang doi.

⛔ KHONG giat lap LLM/TTS/GPU. Khong mot dong gia lap nao trong tep nay — dung
   thu san pham that (torch that, model that, khoa API that). Kho nay da ghi
   hai lan cai gia cua fixture tu dung tien de san pham khong co:
   `fixture-tu-dung-tien-de-ma-san-pham-khong-co.md` (9 test xanh + nghiem thu
   PASS + 404 tren production) va `phep-kiem-xanh-tren-thu-da-hong.md`.

## 🔴 GIOI HAN — day la VONG TRONG nhanh, KHONG phai ban thay nghiem thu

- ⛔ KHONG tai hien PATH cua `LocalSystem`: tien trinh nay chay duoi PHIEN
  NGUOI DUNG hien tai, khong phai LocalSystem worker production chay duoi. Su
  co 23/09: worker thieu `ffmpeg` tren PATH, chi lo khi chay duoi SYSTEM. Mot
  lan `asv_chay_tai_cho` XANH ⛔ KHONG noi gi ve PATH cua LocalSystem.
- ⛔ KHONG tai hien viec NHAY LAN (api / gpu+ffmpeg / voice tren BA lan khac
  nhau qua `LTT_WORKER_POOLS`) — noi thoi gian CHET giua giai doan sinh ra o
  production. Tep nay chay MOT tien trinh, KHONG doi tien trinh nao ca.
- ⚠️ `job_events` (stage_enter/stage_exit, progress_counter) VAN MU, dung nhu
  `thi_hanh.chay_giai_doan` da khai cho `ctx=None` — nhung LY DO khac mot
  chut: o day `ctx` la mot `JobContext` THAT (khong phai `None`), nen
  `ctx.gpu_uuid`/`ctx.gpu_env()`/`ctx.has_gpu` deu DUNG (giai doan GPU van xin
  dung card). Chi `ctx.progress()`/`ctx.event()`/`ctx.is_cancelled()` la MU —
  ba ham do tu mo MOT SESSION RIENG tra `db.get(Job, "")`, va khong co dong
  `jobs` nao mang `id=""` nen chung lang le khong lam gi (`job is None` ->
  no-op / tra `False`). Tuc: **co GPU that, khong co process-log/tien-do**.
- Luat kho *"con so cong phai kem SHA va MOI TRUONG"* ap dung y nguyen: mot
  luot o day noi cho PHIEN NGUOI DUNG, KHONG noi ho cho `LocalSystem`.

⇒ Luot CHOT van phai la `asv_chay_worker_that.py` tren worker THAT sau deploy.
  Nhip moi: sua -> `asv_chay_tai_cho` (phut) -> lap -> mot lan
  `deploy + worker that` o cuoi de chot (B13 §5.3).

## `--thu-kho` (dry-run)

In dung CHUOI loi goi se thuc hien (ten giai doan, `app_slug.job_type`, VRAM
se xin cho CA luot) roi thoat — KHONG cham GPU/DB/LLM/ffmpeg, KHONG goi
`nap_env()`. Day la cai DU de nghiem thu phien nay: chu du an da dan KHONG
chay lenh that (may da treo 2 lan 28/09 vi lenh nang).

## Khoa CPU

Ca luot chay day chuyen la MOT lenh NANG. Khoa `cpu_nhieu` (qua
`tools.cua_so_yen.CuaSoYen`, ⛔ KHONG qua `chay_nang.py` — cong cu do NGOAI
kho) boc QUANH toan bo vong lap 13 giai doan (do la phan TINH lien tuc, khong
co buoc CHO xen giua) va duoc NHA ngay khi vong lap xong, o `finally`.
"""
from __future__ import annotations

import argparse
import importlib
import os
import pathlib
import sys
import threading
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


# ══════════════════════════════════════════════════════════════════════════════
#  Phan THUAN — khong DB, khong GPU, khong I/O. Day la phan co test (dai 4940).
# ══════════════════════════════════════════════════════════════════════════════

def khoang_giai_doan(tu: str, den: str):
    """Mot khoang LIEN TUC cua `pipeline.CHUOI`, ca hai dau bao gom.

    `tu`/`den` rong = lay tu dau / toi cuoi. Nem `SystemExit` voi thong diep ro
    neu ten khong ton tai, hoac `tu` dung SAU `den` trong chuoi — day la hai
    loi go tay de nhat, va thong diep phai tro thang toi cach sua.
    """
    from apps.auto_scan_video import pipeline

    ten_theo_vi_tri = [g.ten for g in pipeline.CHUOI]
    for nhan, ten in (("--tu", tu), ("--den", den)):
        if ten and ten not in ten_theo_vi_tri:
            raise SystemExit(
                f"{nhan}: khong co giai doan '{ten}'. Cac ten hop le: "
                + ", ".join(ten_theo_vi_tri))
    i0 = ten_theo_vi_tri.index(tu) if tu else 0
    i1 = ten_theo_vi_tri.index(den) if den else len(ten_theo_vi_tri) - 1
    if i0 > i1:
        raise SystemExit(
            f"--tu ({tu or ten_theo_vi_tri[0]}) dung SAU --den "
            f"({den or ten_theo_vi_tri[-1]}) trong chuoi — doi lai thu tu.")
    return pipeline.CHUOI[i0:i1 + 1]


#: App -> MANIFEST, nap MOT lan (module manifest thuan khai bao, an toan nap).
_MANIFEST_CACHE: dict = {}


def _manifest(app_slug: str):
    if app_slug not in _MANIFEST_CACHE:
        mod = importlib.import_module(f"apps.{app_slug}.manifest")
        _MANIFEST_CACHE[app_slug] = mod.MANIFEST
    return _MANIFEST_CACHE[app_slug]


def vram_can_cho_khoang(chuoi) -> int:
    """VRAM LON NHAT trong khoang giai doan — dung cho MOT lease chung ca luot.

    ⭐ Doc `AppManifest.vram_for(job_type)` (`platform_core/registry.py:894`),
       ⛔ KHONG go lai con so: do la dung ban khai nen tang dung de xep cho that
       (vd `asv_gpu.transcribe` = 7600 MB, do that 23/09 — xem
       `apps/asv_gpu/manifest.py:108`). 0 = khong giai doan nao trong khoang
       can GPU rieng.
    """
    return max((_manifest(g.app_slug).vram_for(g.job_type) for g in chuoi),
               default=0)


def tham_so_giai_doan(run_id: str, owner_id: str) -> dict:
    """`params` MA `chay_giai_doan` thuc su doc.

    Neo: `apps/auto_scan_video/thi_hanh.py:442-445` — `chay_giai_doan` chi doc
    dung HAI khoa nay tu `params` (`run_id`, `owner_id`); phan con lai cua ho
    so (preset, ngon ngu, giong...) da nam trong `AsvRun.settings` tu luc tao
    run, khong di qua `params` cua tung giai doan.
    """
    return {"run_id": str(run_id), "owner_id": str(owner_id)}


def dong_ke_hoach(chuoi, *, run_id: str, owner_id: str, vram_mb: int) -> str:
    """Chuoi VAN BAN mo ta dung loi goi se thuc hien — dung cho `--thu-kho`."""
    dong = []
    dong.append(f"run_id   : {run_id}")
    dong.append(f"owner_id : {owner_id}")
    if vram_mb > 0:
        dong.append(f"GPU lease: se xin toi {vram_mb} MB, MOT lan cho ca luot "
                     f"({len(chuoi)} giai doan)")
    else:
        dong.append("GPU lease: (khong giai doan nao trong khoang nay can GPU)")
    dong.append("")
    for g in chuoi:
        dong.append(
            f"  thi_hanh.chay_giai_doan({g.ten!r}, "
            f"{{'run_id': {run_id!r}, 'owner_id': {owner_id!r}}}, "
            f"ctx=<JobContext gpu_uuid={'<that>' if vram_mb else ''!r}>)"
            f"   # {g.job_type}")
    return "\n".join(dong)


# ══════════════════════════════════════════════════════════════════════════════
#  Phan CHAY THAT — DB, GPU, tien trinh con. Khong test truc tiep o day.
# ══════════════════════════════════════════════════════════════════════════════

def _owner_cua_run(db, run_id: str) -> str:
    """`owner_id` cua MOT run, doc THANG (khong qua `features.lay_run`).

    `features.lay_run` doi biet san `owner_id` de loc pham vi (I6, dung cho
    duong web) — mot cong cu dia phuong nhu tep nay chua co no khi vua nhan
    `--run-id`. Doc thang khop dung khuon `asv_chay_worker_that.lenh_theo_doi`
    (SQL tho qua `asv_run`, khong qua ORM/ham loc quyen web).
    """
    from sqlalchemy import text
    r = db.execute(text("SELECT owner_id FROM asv_run WHERE id = :r"),
                   {"r": run_id}).first()
    if r is None:
        raise SystemExit(f"khong co run {run_id}")
    return str(r.owner_id)


def lenh_chay(args) -> int:
    from apps.auto_scan_video import pipeline

    chuoi = khoang_giai_doan(args.tu, args.den)

    if args.thu_kho:
        # ⛔ KHONG goi nap_env(), KHONG cham DB/GPU/ffmpeg — dung `--run-id` neu
        #    co (khong tao gi), hoac mot cho giu cho neu se tao run moi.
        run_id = args.run_id or "<se-tao-moi-tu---video>"
        owner_id = "<doc-tu-run-hoac-tu---email-luc-tao>"
        vram_mb = vram_can_cho_khoang(chuoi)
        print("KE HOACH (--thu-kho — khong chay gi that):")
        print(dong_ke_hoach(chuoi, run_id=run_id, owner_id=owner_id,
                            vram_mb=vram_mb))
        return 0

    from tools import asv_chay_worker_that as worker_that
    from tools.cua_so_yen import CuaSoYen

    worker_that.nap_env()
    os.environ["LTT_AUTO_SCAN_VIDEO"] = "1"
    os.chdir(GOC)

    run_id = args.run_id
    if not run_id:
        run_id = worker_that._tao(args)          # noqa: SLF001 - dung lai co y
        if not run_id:
            return 2

    from platform_core import db as dbmod
    from platform_core import gpu_lease as gl
    from platform_core.job_runner import GPU_HEARTBEAT_S, JobContext
    from apps.auto_scan_video import thi_hanh

    gen = dbmod.get_session()
    db = next(gen)
    owner_id = _owner_cua_run(db, run_id)
    try:
        next(gen)
    except StopIteration:
        pass

    can_mb = vram_can_cho_khoang(chuoi)
    print(f"RUN   : {run_id}  (chu {owner_id})")
    print(f"KHOANG: {chuoi[0].ten} .. {chuoi[-1].ten}  ({len(chuoi)} giai doan)")

    lease = None
    db_gpu = None
    dung_nhip = None
    luong_nhip = None
    ket_qua: list[dict] = []
    ma_loi_thoat = 0
    try:
        with CuaSoYen(args.phien, "asv_chay_tai_cho", bat=not args.khong_khoa,
                      cho_toi_da_s=args.cho_khoa_toi_da_s):
            if can_mb > 0:
                dung_duoc, vi_sao = gl.gpu_mod.cuda_dung_duoc()
                if not dung_duoc:
                    print(f"GPU: tien trinh nay KHONG dung duoc CUDA ({vi_sao}) "
                          f"— chay tiep KHONG lease (giai doan GPU se tu choi "
                          f"neu no doi card).")
                else:
                    gen_gpu = dbmod.get_session()
                    db_gpu = next(gen_gpu)
                    try:
                        # ⛔ KHONG truyen `run_id` lam `job_id`: `AsvRun.id` co
                        #    the dai toi 48 ky tu (`asvr_<32 hex>`), con
                        #    `GpuLease.job_id` la `String(36)` — chep vao se
                        #    tran cot. O day KHONG co dong `jobs` that de tro
                        #    toi, nen de rong dung ban chat ("khong qua hang
                        #    doi") thay vi go ep mot gia tri sai kieu.
                        lease = gl.acquire(
                            db_gpu, worker_id=f"tai-cho:{os.getpid()}",
                            need_mb=can_mb)
                    except Exception:                       # noqa: BLE001
                        traceback.print_exc()
                    if lease is None:
                        print(f"GPU: khong gianh duoc lease ({can_mb} MB) — "
                              f"chay tiep KHONG GPU.")
                    else:
                        print(f"GPU   : {lease.gpu_uuid[:20]} "
                              f"(index {lease.gpu_index}), xin {can_mb} MB")
                        dung_nhip = threading.Event()

                        def _nhip():
                            while not dung_nhip.wait(GPU_HEARTBEAT_S):
                                try:
                                    gl.heartbeat(db_gpu, lease)
                                except Exception:            # noqa: BLE001
                                    traceback.print_exc()

                        luong_nhip = threading.Thread(target=_nhip, daemon=True)
                        luong_nhip.start()

            ctx = JobContext(run_id, gpu_uuid=(lease.gpu_uuid if lease else ""))

            for g in chuoi:
                print(f"\n== {g.ten} ==", flush=True)
                t0 = time.monotonic()
                try:
                    ra = thi_hanh.chay_giai_doan(
                        g.ten, tham_so_giai_doan(run_id, owner_id), ctx=ctx)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                    ma_loi_thoat = 2
                    break
                dt = time.monotonic() - t0
                print(f"  -> {ra}  ({dt:.1f}s)")
                ket_qua.append(ra)
    finally:
        if dung_nhip is not None:
            dung_nhip.set()
        if luong_nhip is not None:
            luong_nhip.join(timeout=5.0)
        if lease is not None and db_gpu is not None:
            try:
                gl.release(db_gpu, lease)
                db_gpu.commit()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
        if db_gpu is not None:
            db_gpu.close()

    print(f"\n{len(ket_qua)}/{len(chuoi)} giai doan xong.")
    return ma_loi_thoat


# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="lenh", required=True)

    c = sub.add_parser(
        "chay", help="chay MOT khoang (mac dinh: ca chuoi) TRUC TIEP, bo hang doi")
    c.add_argument("--video", default="",
                   help="bat buoc neu KHONG dung --run-id (tao mot run moi)")
    c.add_argument("--preset", default="localize_preserve_picture")
    c.add_argument("--nguon", default="zh")
    c.add_argument("--dich", default="vi")
    c.add_argument("--che-do-giong", dest="che_do_giong", default="USER_SELECTED")
    c.add_argument("--giong", default="Minh Đức")
    c.add_argument("--email", default="khach1.thu@lttstudios.local")
    c.add_argument("--bien-tap", dest="bien_tap", default="",
                   help='JSON bien tap khung hinh, vd \'{"toc_do": 1.25}\'')
    c.add_argument("--run-id", dest="run_id", default="",
                   help="dung run DA CO thay vi tao moi (vd sua lai MOT giai "
                        "doan bang --tu/--den)")
    c.add_argument("--tu", default="", help="ten giai doan BAT DAU (mac dinh: dau chuoi)")
    c.add_argument("--den", default="", help="ten giai doan KET THUC (mac dinh: cuoi chuoi)")
    c.add_argument("--thu-kho", dest="thu_kho", action="store_true",
                   help="dry-run: chi in ke hoach roi thoat, khong cham gi")
    c.add_argument("--phien", default="asv-tai-cho",
                   help="ten phien cho khoa cpu_nhieu (CuaSoYen)")
    c.add_argument("--khong-khoa", dest="khong_khoa", action="store_true",
                   help="bo qua khoa cpu_nhieu (chi dung khi tu tay biet may ranh)")
    c.add_argument("--cho-khoa-toi-da-s", dest="cho_khoa_toi_da_s", type=float,
                   default=1800.0)
    c.set_defaults(fn=lenh_chay)

    args = ap.parse_args()
    if args.lenh == "chay" and not args.thu_kho and not args.run_id and not args.video:
        ap.error("chay: can --video (tao run moi) hoac --run-id (dung run da co)")
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
