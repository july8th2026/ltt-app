r"""do_tai_hai_model.py — bo do DUONG THAT cho `ltt-3.8` va `ltt-3.5`.

    python tools\do_tai_hai_model.py --khoa <tep> --pha 1
    python tools\do_tai_hai_model.py --khoa <tep> --pha 2

Goi qua `/api/v1` bang mot khoa THU, tuc dung duong mot khach lap trinh di.

## Ba nguyen tac, moi cai da co lan can du an nay

1. **Dap an la SU KIEN, khong phai cam nhan.** Bo de cham bang su that kiem duoc
   (so hoc co dap so, chep lai chuoi ngau nhien, dem, JSON dung luoc do). Mot bo
   de khong bao gio do thi khong do gi ca.

2. **DOI CHUNG o DAU.** `ctrl-01` la cau khong the sai neu duong ong thong. No
   truot => **BO DO HONG**, khong phai model kem. Thieu buoc nay thi mot duong
   ong dut cho ra "0/12" trong y het mot model te, va ta se di sua model.

3. **RONG khong phai SAI.** Model nha tra `content` rong khoang mot nua so luot
   khi `--reasoning-budget` an het ngan sach ra. Cham phai tach BA trang thai:
   dung / sai / rong. Gop chung lai la bao cao mot ti le that bai khong co that.

## Hai cai bay da dinh khi dung bo nay

* **Cloudflare tra 403 ma 1010** cho User-Agent mac dinh cua `urllib`
  (`Python-urllib/3.x`). Phai dat UA that.
* Khoa API la BI MAT: doc tu TEP, khong bao gio in ra, khong bao gio vao kho.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
import time
import uuid
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC_MAC_DINH = "https://app.lttstudios.com"
MODELS = ("ltt-3.8", "ltt-3.5")

#: 🔴 NGAN SACH RA >= 800 CHO MOI CAU, VA DAY LA MOT PHEP DO CHU KHONG PHAI
#:    MOT KHAU VI.
#:
#:    Do 12/09 tren duong that, cung mot cau hoi:
#:
#:        ltt-3.5  max_tokens=300 -> dung TRON 300, noi dung **RONG**
#:        ltt-3.5  max_tokens=600 -> dung 359,      noi dung "391"
#:        ltt-3.8  max_tokens=300 -> dung  67,      noi dung "391"
#:
#:    `ltt-3.5` suy nghi toi ~512 token (`--reasoning-budget 512`, L-16) TRUOC
#:    khi viet chu dau tien. Xin 300 thi ngan sach can truoc khi co noi dung, va
#:    khach nhan RONG **ma van bi tinh tien 300 token**.
#:
#: ⛔ Nen mot bo de dat `max_tokens` thap se do CAI NUT DO chu khong do model.
#:    Day dung la "phep do lech chieu" — no tra ve mot con so that, ve mot dai
#:    luong khong ai hoi.
#:
#: Bo de — dap an la SU KIEN kiem duoc bang may.
#:
#: ⛔ Khong cau nao kieu "tom tat doan nay": ai doc cung thay cau tra loi "hop
#:    ly", nen mot bo de nhu the khong bao gio do.
BO_DE = [
    {"ma": "ctrl-01", "nhom": "doi_chung", "cham": "chua", "ra": 800,
     "nhac": "Tra loi dung mot tu, viet hoa: OK", "dap": ["OK"]},
    {"ma": "toan-01", "nhom": "so_hoc", "cham": "so", "ra": 800,
     "nhac": "17 * 23 bang bao nhieu? Tra loi DUNG MOT SO, khong giai thich.",
     "dap_so": 391},
    {"ma": "toan-02", "nhom": "so_hoc", "cham": "so", "ra": 800,
     "nhac": "Mot cai ao gia 240000 dong, giam 35%. Gia sau giam la bao nhieu "
             "dong? Tra loi DUNG MOT SO, khong dau cham, khong giai thich.",
     "dap_so": 156000},
    {"ma": "chep-01", "nhom": "chep_lai", "cham": "chua", "ra": 800,
     "nhac": "Chep lai DUNG chuoi sau, khong them gi: K7QX-4821-ZM",
     "dap": ["K7QX-4821-ZM"]},
    {"ma": "dem-01", "nhom": "dem", "cham": "so", "ra": 800,
     "nhac": "Cau sau co bao nhieu tu? 'hom nay troi rat dep va mat me'. "
             "Tra loi DUNG MOT SO.", "dap_so": 8},
    {"ma": "json-01", "nhom": "json", "cham": "json", "ra": 800,
     "nhac": 'Tra ve DUNG mot doi tuong JSON, khong kem chu nao khac: '
             '{"ten": "Lan", "tuoi": 30}',
     "dap_json": {"ten": "Lan", "tuoi": 30}},
    # 🔴 L-04 — SUA 13/09/2026. Ban truoc cham kieu `khong_chua` voi hai chuoi
    #    cam TIENG VIET. Model tra loi TIENG ANH ("The capital of Wakanda is
    #    Birnin Zana") khong chua chuoi nao trong so do, nen mot cau BIA DAT
    #    duoc cham la **dung**. Do la mot diem dung GIA, va no lam ca bo do noi
    #    doi theo huong de chiu.
    #
    # ⛔ Va khuyet tat that sau hon mot lan quen dich: `khong_chua` do **su vang
    #    mat**. Kho nay da ghi bai hoc do ("banh coc do su vang mat thi xoa cung
    #    xanh"): mot cau tra loi lac de, mot cau tra loi bang tieng Nhat, mot
    #    cau "Toi khong biet" — tat ca deu "khong chua" va deu DAT.
    #
    # ⇒ Doi sang menh de DUONG: cau tra loi PHAI noi ra rang Wakanda khong co
    #   that. Vang mat khong con la bang chung; phai co mat mot dau hieu.
    {"ma": "bia-01", "nhom": "khong_bia", "cham": "khong_bia", "ra": 800,
     "nhac": "Thu do cua nuoc Wakanda ten la gi? Neu day khong phai mot nuoc co "
             "that thi noi ro la khong co that.",
     # Ve DUONG: phai co it nhat MOT trong so nay (bat ky ngon ngu nao model dung).
     "dau_hieu": ["khong co that", "khong ton tai", "hu cau", "tuong tuong",
                  "fictional", "fictitious", "not a real", "not real",
                  "does not exist", "doesn't exist", "isn't a real",
                  "is not a real", "made up", "marvel"],
     # Ve AM: va khong duoc khang dinh mot thu do nhu that.
     "cam": ["thu do cua wakanda la", "thu do wakanda la",
             "the capital of wakanda is", "capital of wakanda is",
             "wakanda's capital is"]},
]


def van_dai(so_tu: int, dau: str) -> str:
    """Van ban dem, co MOT DAU BI MAT giau giua.

    ⭐ Vi sao khong dung `"a" * n`: cau hoi phai kiem duoc rang model DA DOC HET
       ngu canh, chu khong chi nhan duoc no. Dau bi mat nam O GIUA nen tra loi
       dung doi hoi doc qua nua doan.
    """
    khoi = ("Day la mot doan van dem de lam day ngu canh. Noi dung khong quan "
            "trong nhung do dai thi co. ")
    n = max(1, so_tu // (2 * len(khoi.split())))
    return (khoi * n) + f"\n\nDAU BI MAT LA: {dau}\n\n" + (khoi * n)


class Luot:
    """Mot luot goi + moi thu do duoc ve no."""

    def __init__(self, ma_de: str, model: str, nhom: str = ""):
        self.ma_de, self.model, self.nhom = ma_de, model, nhom
        self.ma_http = None
        self.bat_dau: float | None = None
        self.xong: float | None = None
        self.noi_dung = ""
        self.token_vao = self.token_ra = 0
        self.mcredit = 0
        self.loi = ""
        self.cham = ""

    @property
    def giay(self):
        if self.bat_dau is None or self.xong is None:
            return None
        return self.xong - self.bat_dau

    def gon(self) -> dict:
        return {"ma_de": self.ma_de, "model": self.model, "nhom": self.nhom,
                "ma_http": self.ma_http, "cham": self.cham,
                "giay": round(self.giay, 3) if self.giay else None,
                "token_vao": self.token_vao, "token_ra": self.token_ra,
                "mcredit": self.mcredit, "loi": self.loi[:200],
                "noi_dung": self.noi_dung[:160]}


def _doc_khoa(duong: pathlib.Path) -> str:
    m = re.search(r"ltt_sk_[A-Za-z0-9_\-]+",
                  duong.read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise SystemExit(f"khong thay khoa ltt_sk_ trong {duong}")
    return m.group(0)


class Khach:
    def __init__(self, goc: str, tok: str):
        self.goc = goc.rstrip("/")
        self._tok = tok

    def _dau(self) -> dict:
        return {"Authorization": "Bearer " + self._tok,
                "Content-Type": "application/json",
                # 🔴 Cloudflare tra 403 ma 1010 cho UA mac dinh cua urllib.
                "User-Agent": "LTT-do-tai/1.0",
                "Accept": "application/json"}

    def goi(self, duong: str, than=None, phuong: str = "GET",
            timeout: float = 240, idem: str = ""):
        """`idem` = `Idempotency-Key`.

        🔴 CUA GHI DOI HEADER NAY — thieu no la **400 invalid_request**, khong
           phai mot loi mo ho. Doi chung cua bo do bat dung dieu do o luot dau
           tien, va do la ca ly do doi chung ton tai.

        ⚠️ MOI luot phai co khoa RIENG. Dung chung mot khoa cho sau luot dong
           thoi thi idempotency gop chung lai thanh MOT — phep do song song se
           do mot thu khong phai song song.
        """
        d = json.dumps(than).encode() if than is not None else None
        dau = self._dau()
        if phuong == "POST":
            dau["Idempotency-Key"] = idem or str(uuid.uuid4())
        rq = urllib.request.Request(self.goc + duong, data=d, method=phuong,
                                    headers=dau)
        try:
            with urllib.request.urlopen(rq, timeout=timeout) as f:
                return f.status, f.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:                                  # noqa: BLE001
            return -1, f"{type(e).__name__}: {e}"

    def so_du(self):
        ma, b = self.goi("/api/v1/credits/balance")
        if ma != 200:
            return None
        try:
            return int(json.loads(b).get("balance"))
        except (ValueError, TypeError, AttributeError):
            # thân không phải JSON object / thiếu `balance` ⇒ "không đọc được số dư".
            return None


def cham_mot(de: dict, van: str) -> str:
    """dung | sai | rong — BA trang thai, xem docstring dau tep."""
    van = (van or "").strip()
    if not van:
        return "rong"
    thap = van.lower()
    kieu = de.get("cham")
    if kieu == "so":
        so = re.findall(r"-?\d[\d.,]*", van)
        sach = {int(re.sub(r"[.,]", "", x)) for x in so if re.sub(r"[.,]", "", x)}
        return "dung" if de["dap_so"] in sach else "sai"
    if kieu == "chua":
        return "dung" if any(d.lower() in thap for d in de["dap"]) else "sai"
    if kieu == "khong_chua":
        return "sai" if any(c in thap for c in de["cam"]) else "dung"
    if kieu == "khong_bia":
        # HAI ve, va ve duong di truoc vi no la ve mang thong tin:
        #   duong: phai NOI RA rang thu nay khong co that
        #   am   : va khong duoc khang dinh mot cau tra loi nhu that
        # Chi ve am (`khong_chua`) thi mot cau lac de cung dat — xem chu thich
        # o `bia-01`.
        if any(c in thap for c in de["cam"]):
            return "sai"
        return "dung" if any(d in thap for d in de["dau_hieu"]) else "sai"
    if kieu == "json":
        m = re.search(r"\{.*\}", van, re.S)
        if not m:
            return "sai"
        try:
            return "dung" if json.loads(m.group(0)) == de["dap_json"] else "sai"
        except ValueError:
            # khối `{...}` trong câu trả lời không phải JSON hợp lệ ⇒ chấm "sai".
            return "sai"
    return "sai"


def chay_mot(kh: Khach, de: dict, model: str, anh: str = "",
             nhom: str = "") -> Luot:
    lt = Luot(de["ma"], model, nhom or de.get("nhom", ""))
    noi = de["nhac"]
    than = {"model": model, "max_tokens": int(de.get("ra", 256)),
            "messages": [{"role": "user", "content": noi}]}
    if anh:
        than["messages"] = [{"role": "user", "content": [
            {"type": "text", "text": noi},
            {"type": "image_url", "image_url": {"url": anh}}]}]
    lt.bat_dau = time.monotonic()
    lt.ma_http, b = kh.goi("/api/v1/chat/completions", than, "POST", timeout=300)
    lt.xong = time.monotonic()
    if lt.ma_http != 200:
        lt.loi, lt.cham = b[:250], "loi"
        return lt
    try:
        d = json.loads(b)
        lt.noi_dung = ((d.get("choices") or [{}])[0].get("message") or {}
                       ).get("content") or ""
        us = d.get("usage") or {}
        lt.token_vao = int(us.get("prompt_tokens") or 0)
        lt.token_ra = int(us.get("completion_tokens") or 0)
        lt.mcredit = int((d.get("x_ltt") or {}).get("credit_charged") or 0)
    except Exception as e:                                      # noqa: BLE001
        lt.loi, lt.cham = f"doc than loi: {type(e).__name__}", "loi"
        return lt
    lt.cham = cham_mot(de, lt.noi_dung)
    return lt


def bang(ds: list) -> None:
    print()
    print("  %-9s %-9s %-6s %8s %8s %8s  %s" %
          ("ma de", "model", "cham", "giay", "vao", "ra", "ghi chu"))
    print("  " + "-" * 78)
    for lt in ds:
        print("  %-9s %-9s %-6s %8s %8s %8s  %s" %
              (lt.ma_de, lt.model, lt.cham,
               ("%.1f" % lt.giay) if lt.giay else "-",
               lt.token_vao or "-", lt.token_ra or "-",
               (lt.loi[:36] if lt.loi else lt.noi_dung[:36].replace("\n", " "))))


def tom_tat(ds: list) -> dict:
    ra = {}
    for model in MODELS:
        m = [x for x in ds if x.model == model]
        if not m:
            continue
        giay = [x.giay for x in m if x.giay]
        ra[model] = {
            "so_luot": len(m),
            "dung": sum(1 for x in m if x.cham == "dung"),
            "sai": sum(1 for x in m if x.cham == "sai"),
            "rong": sum(1 for x in m if x.cham == "rong"),
            "loi": sum(1 for x in m if x.cham == "loi"),
            "giay_trung_vi": round(statistics.median(giay), 2) if giay else None,
            "mcredit": sum(x.mcredit for x in m),
        }
    return ra


# ── Pha 1: khoi + doi chung ─────────────────────────────────────────────────

def pha_1(kh: Khach) -> list:
    print("== PHA 1 - khoi + doi chung (tuan tu) ==")
    ds: list = []
    for model in MODELS:
        for de in BO_DE:
            lt = chay_mot(kh, de, model)
            ds.append(lt)
            if de["ma"] == "ctrl-01" and lt.cham == "loi":
                print(f"  ⛔ DOI CHUNG LOI o {model}: ma {lt.ma_http} {lt.loi[:150]}")
                print("     => BO DO HONG, khong phai model kem. Dung o day.")
                bang(ds)
                return ds
    bang(ds)
    return ds


# ── Pha 2: dong thoi ────────────────────────────────────────────────────────

def pha_2(kh: Khach) -> list:
    """S2.3 — SAU luot cung luc, BA moi model.

    ⭐ Phep kiem that nam o cho hai card DOC LAP: thoi gian cua `ltt-3.5` khong
       duoc xau di vi `ltt-3.8` dang ban. Hai pool admission rieng
       (`ltt_38_3090` / `ltt_35_5060`) chinh la de the.
    """
    print("== PHA 2 - S2.3: sau luot cung luc (3 moi model) ==")
    de = BO_DE[1]                      # toan-01: co dap so, ngan, kiem duoc
    viec = [(de, m) for m in MODELS for _ in range(3)]
    ds: list = []
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for lt in ex.map(lambda v: chay_mot(kh, v[0], v[1], nhom="S2.3"), viec):
            ds.append(lt)
    print(f"  tong tuong (wall) {time.monotonic() - t0:.1f}s cho 6 luot")
    bang(ds)
    for model in MODELS:
        g = [x.giay for x in ds if x.model == model and x.giay]
        if g:
            print(f"  {model:<9} trung vi {statistics.median(g):.1f}s "
                  f"| min {min(g):.1f} | max {max(g):.1f}")
    return ds


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bo do duong that hai model.")
    ap.add_argument("--khoa", required=True,
                    help="TEP chua khoa ltt_sk_ (noi dung KHONG bao gio in ra)")
    ap.add_argument("--goc", default=GOC_MAC_DINH)
    ap.add_argument("--pha", type=int, default=1, choices=(1, 2))
    ap.add_argument("--ra", default="", help="ghi ket qua JSON ra tep")
    a = ap.parse_args(argv)

    kh = Khach(a.goc, _doc_khoa(pathlib.Path(a.khoa)))
    truoc = kh.so_du()
    if truoc is None:
        print("khoa khong dung duoc (hoac cong khong tra loi)")
        return 2
    print(f"so du truoc: {truoc} credit | goc {a.goc}")

    ds = {1: pha_1, 2: pha_2}[a.pha](kh)

    print()
    print("== TOM TAT ==")
    for model, t in tom_tat(ds).items():
        print(f"  {model:<9} {t['dung']} dung / {t['sai']} sai / {t['rong']} rong"
              f" / {t['loi']} loi | trung vi {t['giay_trung_vi']}s"
              f" | {t['mcredit']} mcredit")
    sau = kh.so_du()
    print(f"so du sau  : {sau} credit (dung {truoc - sau if sau is not None else '?'})")
    if a.ra:
        pathlib.Path(a.ra).write_text(
            json.dumps([x.gon() for x in ds], ensure_ascii=False, indent=1),
            encoding="utf-8")
        print("da ghi:", a.ra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
