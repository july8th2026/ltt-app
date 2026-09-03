"""nhat_ky_chay.py — ghi nhat ky MOT luot chay nang, chiu duoc mot lan treo may.

    python tools/nhat_ky_chay.py -- python tools/gate.py --phien X
    python tools/nhat_ky_chay.py --xem            # doc lai luot gan nhat
    python tools/nhat_ky_chay.py --xem 3          # ba luot gan nhat

## Vi sao no ton tai

Ngay 03/09 may bi reset **hai lan** vi qua tai. Ca hai lan, cau hoi "cai gi lam
treo" khong tra loi duoc — khong phai vi kho manh moi, ma vi **khong con gi de
doc**. Moi thu nam trong RAM cua mot tien trinh da chet.

Ba ung vien cho lan dau (gate / 45 tien trinh ngoai gate / chinh phep do cua
toi) khong phan biet duoc, va doan la vo ich. Mot lan reset khong co nhat ky la
mot lan hoc duoc **khong gi ca**.

⇒ Tep nay doi lay dieu do bang mot thu re: mot dong JSON moi vai giay, **flush
  ngay**, ngoai cay kho.

## Ba quyet dinh thiet ke, va ly do tung cai

### 1. `flush()` + `os.fsync()` sau MOI dong

Khong co buffer. Mot lan treo may khong cho tien trinh co hoi dong tep, nen bat
cu thu gi con nam trong buffer la thu **khong bao gio** doc lai duoc — dung luc
no dang gia nhat.

⚠️ `fsync` moi dong la cham. Do la lua chon co y: nhip lay mau tinh bang giay,
   nen chi phi khong dang ke, va thu ta mua duoc la ca phep do.

### 2. Ngoai cay kho (`%TEMP%`)

`gate._anh_chup_cay()` quet `tools/`, `tests/`, `apps/`… de phat hien cay doi
giua chung. Mot tep nhat ky ghi lien tuc trong do se lam gate tu bao "CAY DA DOI
TRONG LUC CHAY" va **tu vut bo phep do cua chinh no**. Cung lop loi voi
`cua_so_yen`, va no da duoc ghi ra o do.

### 3. Lay mau THUA va NHE — chi tong may

⛔ Bai hoc dat nhat cua ngay 03/09: **chinh phep do cua toi la mot trong ba nghi
   can.** Ban dau toi quet `process_iter` qua 58 tien trinh, goi `cpu_percent`
   cho tung cai, lap 5 lan — roi khong loai tru duoc chinh no khoi danh sach
   nguyen nhan lam treo may.

⇒ Mac dinh **8 giay/mau**, va moi mau chi doc **ba con so cua toan may**
  (cpu_percent, RAM trong, so tien trinh). Khong duyet tien trinh, khong doc
  cmdline, khong tinh cay con. Chi tiet do de danh cho `--sau` chay MOT LAN o
  dau va cuoi.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

#: Ngoai cay kho — xem muc 2 dau tep.
THU_MUC = Path(tempfile.gettempdir()) / "ltt_nhat_ky_chay"

#: Giay giua hai mau. Thua co y: phep do khong duoc thanh mot nghi can.
NHIP_S = 8.0


def _anh_chup_nhe() -> dict:
    """Ba con so cua TOAN MAY. Khong duyet tien trinh.

    🔴 **Thu tep nay ngay khi viet xong, va no ra HAI loi lien tiep** — ca hai
       deu khien nhat ky ghi `0%` cho mot may dang chay 100%:

         1. `interval=None` lan goi DAU tra 0.0 (khong co moc so sanh)
         2. `interval=None` giu trang thai TOAN CUC, ma ham nay duoc goi tu HAI
            luong — chung giam moc cua nhau, nen mau o GIUA cung ra 0%

    ⇒ `interval=0.2`: tu do trong khoang do, khong phu thuoc lan goi truoc, an
      toan voi nhieu luong. Gia la chan 0,2s moi mau (2,5% cua nhip 8s).

    ⚠️ Mot ham do tra ve 0.0 trong y het mot may dang ranh. Neu khong thu, ca
       hai loi nay chi lo ra **sau mot lan treo** — dung luc khong sua duoc nua.
    """
    try:
        import psutil
    except ImportError:
        return {}
    try:
        m = psutil.virtual_memory()
        # ⛔ `interval=0.2`, KHONG phai `None`.
        #
        # 🔴 Loi thu HAI tim ra khi thu tep nay: `interval=None` giu trang thai
        #    TOAN CUC trong psutil, va ham nay duoc goi tu HAI luong — luong
        #    chinh (`bat_dau`/`ket_thuc`) va luong lay mau. Hai luong giam moc
        #    cua nhau ⇒ mau o giua ra `0%` cho mot may dang chay 100%.
        #
        # ⭐ `interval=0.2` tu do trong khoang do, khong phu thuoc lan goi truoc,
        #    nen an toan voi nhieu luong. Gia: chan 0,2s moi mau — voi nhip 8s
        #    thi la 2,5%, doi lay mot con so dung.
        return {"cpu": psutil.cpu_percent(interval=0.2),
                "ram_trong_gib": round(m.available / 2**30, 2),
                "so_tien_trinh": len(psutil.pids())}
    except Exception as exc:  # noqa: BLE001 - do tai khong duoc lam hong lan chay
        return {"loi_do": f"{type(exc).__name__}: {exc}"}


def _anh_chup_sau() -> dict:
    """Chi tiet, chay DUNG MOT LAN o dau va cuoi. Xem muc 3 dau tep."""
    try:
        import psutil
    except ImportError:
        return {}
    ra = []
    try:
        for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            ten = (p.info["name"] or "").lower()
            if not ten.startswith(("python", "node", "ffmpeg", "pwsh")):
                continue
            cl = " ".join(p.info["cmdline"] or [])[:100]
            ra.append({"pid": p.info["pid"], "ten": ten,
                       "tuoi_phut": round((time.time() - p.info["create_time"]) / 60, 1),
                       "lenh": cl})
    except Exception as exc:  # noqa: BLE001
        return {"loi_do": f"{type(exc).__name__}: {exc}"}
    ra.sort(key=lambda x: -x["tuoi_phut"])
    return {"tien_trinh": ra[:25], "tong": len(ra)}


class NhatKy:
    """Ghi tung dong, flush + fsync ngay. Xem muc 1 dau tep."""

    def __init__(self, ten_luot: str):
        THU_MUC.mkdir(parents=True, exist_ok=True)
        dau = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.tep = THU_MUC / f"{dau}_{ten_luot}.jsonl"
        self._f = open(self.tep, "a", encoding="utf-8", newline="\n")

    def ghi(self, loai: str, **truong) -> None:
        dong = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "loai": loai, **truong}
        self._f.write(json.dumps(dong, ensure_ascii=False) + "\n")
        # ⛔ Ca hai deu can. `flush` day khoi buffer cua Python; `fsync` day khoi
        #    buffer cua HE DIEU HANH. Mot lan treo may khong ton trong cai nao.
        self._f.flush()
        try:
            os.fsync(self._f.fileno())
        except OSError:
            pass

    def dong(self) -> None:
        try:
            self._f.close()
        except OSError:
            pass


def chay_va_ghi(argv: list[str], *, nhip: float = NHIP_S) -> int:
    ten = Path(argv[1]).stem if len(argv) > 1 else "lenh"
    nk = NhatKy(ten)
    nk.ghi("bat_dau", lenh=" ".join(argv), pid_cha=os.getpid(),
           **_anh_chup_nhe())
    nk.ghi("anh_chup_dau", **_anh_chup_sau())

    t0 = time.monotonic()
    # BELOW_NORMAL giong `gate._run`, de nhat ky khong doi hanh vi lan chay.
    them = {"creationflags": 0x00004000} if os.name == "nt" else {}
    p = subprocess.Popen(argv, **them)

    dung = threading.Event()

    def lay_mau() -> None:
        while not dung.wait(nhip):
            nk.ghi("mau", giay=round(time.monotonic() - t0, 1), **_anh_chup_nhe())

    th = threading.Thread(target=lay_mau, daemon=True)
    th.start()
    try:
        ma = p.wait()
    finally:
        dung.set()
        th.join(timeout=2)
        nk.ghi("ket_thuc", ma=p.returncode,
               giay=round(time.monotonic() - t0, 1), **_anh_chup_nhe())
        nk.ghi("anh_chup_cuoi", **_anh_chup_sau())
        nk.dong()
    print(f"\n[nhat ky] {nk.tep}")
    return ma


def xem(so_luot: int = 1) -> int:
    """In lai cac luot gan nhat. Dung sau mot lan treo."""
    if not THU_MUC.is_dir():
        print(f"chua co nhat ky nao o {THU_MUC}")
        return 0
    tep = sorted(THU_MUC.glob("*.jsonl"))[-max(1, so_luot):]
    if not tep:
        print("chua co luot nao")
        return 0
    for t in tep:
        print(f"\n=== {t.name} ===")
        dong = [json.loads(l) for l in t.read_text(encoding="utf-8").splitlines() if l.strip()]
        ket = [d for d in dong if d["loai"] == "ket_thuc"]
        if not ket:
            # 🔴 Day la truong hop tep nay sinh ra de phuc vu: luot chay KHONG
            #    ket thuc — may treo, hoac bi giet. Nhat ky van con.
            print("  ⚠️  KHONG CO DONG `ket_thuc` — luot nay bi cat giua chung")
        mau = [d for d in dong if d["loai"] == "mau" and "cpu" in d]
        if mau:
            dinh = max(mau, key=lambda d: d["cpu"])
            it_ram = min(mau, key=lambda d: d.get("ram_trong_gib", 999))
            print(f"  {len(mau)} mau | CPU dinh {dinh['cpu']:.0f}% luc "
                  f"{dinh.get('giay', 0):.0f}s | RAM trong thap nhat "
                  f"{it_ram.get('ram_trong_gib', '?')} GiB")
        for d in dong:
            if d["loai"] in ("bat_dau", "ket_thuc"):
                print(f"  {d['t']} {d['loai']}: "
                      f"{d.get('lenh') or 'ma=' + str(d.get('ma'))}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Chay mot lenh nang va ghi nhat ky chiu duoc treo may.")
    p.add_argument("--xem", nargs="?", type=int, const=1, default=None,
                   help="doc lai N luot gan nhat thay vi chay gi")
    p.add_argument("--nhip", type=float, default=NHIP_S)
    p.add_argument("lenh", nargs=argparse.REMAINDER,
                   help="dat sau `--`, vi du: -- python tools/gate.py")
    a = p.parse_args()

    if a.xem is not None:
        return xem(a.xem)
    argv = [x for x in a.lenh if x != "--"]
    if not argv:
        p.error("thieu lenh. Vi du: nhat_ky_chay.py -- python tools/gate.py")
    return chay_va_ghi(argv, nhip=a.nhip)


if __name__ == "__main__":
    sys.exit(main())
