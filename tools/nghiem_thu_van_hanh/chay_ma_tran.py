"""chay_ma_tran.py — bo chay MA_TRAN_TEST_JOB_DAI tren production that.

Doc `docs/ltt_llm_dual/MA_TRAN_TEST_JOB_DAI.md` truoc. Tep nay chi la CO CAU
CHAY; ma tran va ly le nam o tai lieu.

## ⛔ Ba dieu bo nay lam khac mot bo do ngay tho

1. **Lay mau bang MOT ket noi ben.** Ban dau toi dinh goi `subprocess` moi giay
   de dem lease — moi lan ~1 s khoi dong Python, tuc chinh phep do thanh nguon
   nhieu lon hon thu no do. Gio mot `engine` duy nhat, poll 1 s.
2. **Ghi moc theo `time.monotonic()` chung mot goc**, de moi job so sanh duoc
   voi nhau va voi chuoi lay mau.
3. **Khong ket luan DAT/TRUOT o day.** Bo nay chi SINH SO. Doc so la viec cua
   nguoi, theo bon ngan o §5 tai lieu — mot bo do tu cham diem la mot bo do se
   tu bao minh dung.
"""
import argparse
import json
import pathlib
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
#: Goc kho — suy tu vi tri tep nay, KHONG ghim cung mot worktree.
GOC_CAY = str(pathlib.Path(__file__).resolve().parents[2])
THU_MUC = pathlib.Path(__file__).resolve().parent
DOI_KHOA = THU_MUC / "doi_khoa"
GOC_API = "http://127.0.0.1:8100"

#: Job DAI chuan — do 13/09: 123,3 s / 7.955 manh tren ltt-3.8 khi chay mot minh.
PROMPT_DAI = ("Count from 1 to 2000. One number per line. "
              "Do not stop early, do not summarise.")
MAX_TOKENS_DAI = 8000

T0 = time.monotonic()


def giay() -> float:
    return round(time.monotonic() - T0, 2)


# ───────────────────────────────────────────────────────────── lay mau
class LayMau(threading.Thread):
    """Chup trang thai he moi giay: lease theo user, va may B dang xu ly."""

    def __init__(self, nhip_s: float = 1.0):
        super().__init__(daemon=True)
        self.nhip_s = nhip_s
        self.mau: list[dict] = []
        self._dung = threading.Event()
        self._engine = None

    def _noi(self):
        if self._engine is None:
            import os
            if not os.environ.get("LTT_DATABASE_URL"):
                t = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")
                for d in t.read_text(encoding="utf-8", errors="replace").splitlines():
                    if d.strip().startswith("LTT_DATABASE_URL="):
                        os.environ["LTT_DATABASE_URL"] = \
                            d.split("=", 1)[1].strip().strip('"')
                        break
            sys.path.insert(0, GOC_CAY)
            from platform_core.db import get_engine
            self._engine = get_engine()
        return self._engine

    def run(self) -> None:
        from sqlalchemy import text
        eng = self._noi()
        while not self._dung.wait(self.nhip_s):
            try:
                with eng.connect() as c:
                    hang = c.execute(text(
                        "SELECT resource, user_id, COUNT(*) FROM execution_leases "
                        "WHERE mode='stream' GROUP BY resource, user_id")).all()
                    cho = c.execute(text(
                        "SELECT COUNT(*) FROM llm_waiters WHERE trang_thai='cho'"
                    )).scalar()
                self.mau.append({
                    "t": giay(),
                    "lease": [{"res": r[0], "user": str(r[1])[:8], "n": int(r[2])}
                              for r in hang],
                    "tong_lease": sum(int(r[2]) for r in hang),
                    "dang_cho": int(cho or 0),
                })
            except Exception as e:  # noqa: BLE001 - lay mau hong khong duoc giet lo do
                self.mau.append({"t": giay(), "loi": str(e)[:120]})

    def dung(self) -> None:
        self._dung.set()


# ───────────────────────────────────────────────────────────── mot job
@dataclass
class KetQua:
    ten: str
    model: str
    khoa: str
    t_gui: float = 0.0
    t_byte_dau: float = 0.0
    t_xong: float = 0.0
    ma: int = 0
    n_manh: int = 0
    n_queued: int = 0
    loi: str = ""
    tre: float = 0.0          #: hoan bao nhieu giay roi moi ban
    cat_sau: int = 0          #: >0 = doc du N manh thi CAT (khach dong tab)
    whale: bool = False       #: prompt prefill LON
    t_cat: float = 0.0
    su_kien_dau: list = field(default_factory=list)

    @property
    def ttfb(self) -> float:
        return round(self.t_byte_dau - t_or(self.t_gui), 2) if self.t_byte_dau else -1.0

    @property
    def dai(self) -> float:
        return round(self.t_xong - self.t_gui, 2) if self.t_xong else -1.0


def t_or(v: float) -> float:
    return v


#: Prompt WHALE — prefill LON. Do dai chon de vuot nguong whale ma van DUOI
#: tran vao that cua ltt-3.8 (171.458 token), nen no PHAI duoc phuc vu chu
#: khong bi 413. Mot phep do whale ma nhan 413 la do nham thu khac.
PROMPT_WHALE = ("Here is a long document." + chr(10)
                + "".join(f"Section {i}: this paragraph exists only to "
                          f"occupy prefill budget for concurrency testing."
                          + chr(10) for i in range(3000))
                + chr(10) + "Count from 1 to 400, one number per line.")


def mot_job(kq: KetQua) -> None:
    import httpx
    if kq.tre:
        time.sleep(kq.tre)
    noi_dung = PROMPT_WHALE if kq.whale else PROMPT_DAI
    than = {"model": kq.model, "stream": True, "max_tokens": MAX_TOKENS_DAI,
            "messages": [{"role": "user", "content": noi_dung}]}
    kq.t_gui = giay()
    try:
        with httpx.Client(timeout=900.0) as kh:
            with kh.stream("POST", f"{GOC_API}/api/v1/messages", json=than,
                           headers={"Authorization": f"Bearer {kq.khoa}",
                                    "Idempotency-Key": uuid.uuid4().hex}) as r:
                kq.ma = r.status_code
                if r.status_code != 200:
                    kq.loi = r.read()[:200].decode("utf-8", "replace")
                    kq.t_xong = giay()
                    return
                for khoi in r.iter_raw():
                    if not kq.t_byte_dau:
                        kq.t_byte_dau = giay()
                    kq.n_manh += 1
                    if b"response.queued" in khoi or b"ltt-cho" in khoi:
                        kq.n_queued += 1
                    if len(kq.su_kien_dau) < 3:
                        kq.su_kien_dau.append(khoi[:90].decode("utf-8", "replace"))
                    if kq.cat_sau and kq.n_manh >= kq.cat_sau:
                        # ⛔ CAT THAT: thoat vong roi roi khoi `with` => httpx
                        #    dong socket. Dung thu khach lam khi dong tab.
                        kq.t_cat = giay()
                        break
    except Exception as e:  # noqa: BLE001
        kq.loi = f"{type(e).__name__}: {e}"[:200]
    kq.t_xong = giay()


# ───────────────────────────────────────────────────────────── kich ban
def J(nhan, khoa, model, **kw) -> dict:
    return {"nhan": nhan, "khoa": khoa, "model": model, **kw}


def doc_khoa(ten: str) -> str:
    return (DOI_KHOA / f"{ten}.key").read_text(encoding="utf-8").strip()


#: (ten kich ban) -> danh sach (nhan, ten_khoa, model)
MA_TRAN: dict[str, list[tuple[str, str, str]]] = {
    "J1": [("A", "vh1-a", "ltt-3.8")],
    "J2": [("A", "vh1-a", "ltt-3.8"), ("B", "vh1-a", "ltt-3.5")],
    "J3": [(f"{m}{i}", "vh1-a", m) for m in ("ltt-3.8", "ltt-3.5") for i in (1, 2)],
    "J4": [(f"{m}{i}", "vh1-a", m) for m in ("ltt-3.8", "ltt-3.5") for i in (1, 2, 3)],
    "J5": [(f"{m}{i}", "vh1-a", m) for m in ("ltt-3.8", "ltt-3.5") for i in (1, 2, 3)]
          + [("THU7", "vh1-a", "ltt-3.8")],
    # J12: MOT tai khoan, HAI khoa — chung minh khoa KHONG cong suat.
    "J12": [(f"a{i}", "vh1-a", "ltt-3.8") for i in (1, 2, 3)]
           + [(f"b{i}", "vh1-b", "ltt-3.8") for i in (1, 2, 3)],
    # J7: hai TAI KHOAN khac nhau — tran tai khoan phai BAT.
    "J7": [(f"vh1_{i}", "vh1-a", "ltt-3.8") for i in (1, 2, 3)]
          + [(f"vh2_{i}", "vh2-a", "ltt-3.8") for i in (1, 2, 3)],
}

#: Kich ban CO THAM SO. Chung khac J1-J7 o cho khong the ban dong loat: J8/J9
#: can khach den LECH GIO (moi do duoc "cho bao lau"), J10 can prefill lon,
#: J11 can mot khach CAT that.
MA_TRAN_MO_RONG: dict[str, list[dict]] = {
    "J8": [J(f"vh1_{i}", "vh1-a", "ltt-3.8") for i in (1, 2, 3)]
          + [J("vh2_den_sau", "vh2-a", "ltt-3.8", tre=20.0)],
    "J9": [J(f"vh1_{i}", "vh1-a", "ltt-3.8") for i in (1, 2, 3)]
          + [J("vh2_den_sau", "vh2-a", "ltt-3.8", tre=20.0),
             J("vh3_den_cuoi", "vh3-a", "ltt-3.8", tre=40.0)],
    "J10": [J("whale", "vh1-a", "ltt-3.8", whale=True),
            J("thuong1", "vh2-a", "ltt-3.8"),
            J("thuong2", "vh3-a", "ltt-3.8")],
    "J11": [J(f"giu_{i}", "vh1-a", "ltt-3.8") for i in (1, 2)]
           + [J("se_cat", "vh2-a", "ltt-3.8", cat_sau=5)],
}


def cho_nen_sach(han_s: float = 180.0) -> bool:
    lm = LayMau()
    eng = lm._noi()
    from sqlalchemy import text
    t0 = time.monotonic()
    while time.monotonic() - t0 < han_s:
        with eng.connect() as c:
            n = c.execute(text("SELECT COUNT(*) FROM execution_leases "
                               "WHERE mode='stream'")).scalar()
        if not n:
            return True
        time.sleep(3)
    return False


def chay(ten_kb: str) -> dict:
    if ten_kb in MA_TRAN:
        dsach = [{"nhan": n, "khoa": k, "model": m} for n, k, m in MA_TRAN[ten_kb]]
    else:
        dsach = MA_TRAN_MO_RONG[ten_kb]
    print(f"== {ten_kb}: {len(dsach)} job ==")
    for j in dsach:
        phu = " ".join(f"{k}={v}" for k, v in j.items()
                       if k not in ("nhan", "khoa", "model"))
        print(f"   {j['nhan']:14s} {j['khoa']:8s} {j['model']}  {phu}")

    print("\n-- nen phai sach --")
    if not cho_nen_sach():
        print("   !! con lease stream khac dang song. DUNG.")
        return {}
    print("   lease mode=stream = 0")

    lm = LayMau()
    lm.start()

    ket: list[KetQua] = [
        KetQua(ten=j["nhan"], model=j["model"], khoa=doc_khoa(j["khoa"]),
               tre=float(j.get("tre", 0.0)), cat_sau=int(j.get("cat_sau", 0)),
               whale=bool(j.get("whale", False)))
        for j in dsach]
    luong = [threading.Thread(target=mot_job, args=(k,)) for k in ket]
    print(f"\n-- ban {len(luong)} job cung luc --")
    for t in luong:
        t.start()
    for t in luong:
        t.join()
    lm.dung()
    time.sleep(1.2)

    dinh = max((m.get("tong_lease", 0) for m in lm.mau), default=0)
    cho_dinh = max((m.get("dang_cho", 0) for m in lm.mau), default=0)

    print("\n-- ket qua tung job --")
    print(f"   {'job':10s} {'ma':>4s} {'ttfb':>7s} {'dai':>8s} {'manh':>7s} {'cho':>4s}")
    for k in ket:
        print(f"   {k.ten:10s} {k.ma:>4d} {k.ttfb:>7.2f} {k.dai:>8.2f} "
              f"{k.n_manh:>7d} {k.n_queued:>4d}"
              + (f"  CAT@{k.t_cat:.1f}s" if k.t_cat else "")
              + (f"  LOI {k.loi[:60]}" if k.loi else ""))

    print("\n-- he thong --")
    print(f"   dinh lease dong thoi : {dinh}")
    print(f"   dinh so nguoi CHO    : {cho_dinh}")
    moc = [m for m in lm.mau if m.get("tong_lease")]
    if moc:
        print("   phan bo luc dinh     : "
              + json.dumps(next(m["lease"] for m in moc
                                if m.get("tong_lease") == dinh)))

    ra = {"kich_ban": ten_kb, "dinh_lease": dinh, "dinh_cho": cho_dinh,
          "job": [{"ten": k.ten, "model": k.model, "ma": k.ma, "ttfb": k.ttfb,
                   "dai": k.dai, "manh": k.n_manh, "queued": k.n_queued,
                   "t_cat": k.t_cat, "tre": k.tre, "loi": k.loi} for k in ket],
          "mau": lm.mau}
    tep = THU_MUC / f"ket_{ten_kb}.json"
    tep.write_text(json.dumps(ra, indent=2), encoding="utf-8")
    print(f"\n   [ban ghi] {tep.name}")
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kich-ban", required=True,
                    help="J1 J2 J3 J4 J5 J7 J12, hoac nhieu cai cach nhau bang dau phay")
    a = ap.parse_args()
    for kb in a.kich_ban.split(","):
        kb = kb.strip()
        if kb not in MA_TRAN and kb not in MA_TRAN_MO_RONG:
            print(f"khong co {kb!r}; co: "
                  f"{sorted(set(MA_TRAN) | set(MA_TRAN_MO_RONG))}")
            return 2
        chay(kb)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
