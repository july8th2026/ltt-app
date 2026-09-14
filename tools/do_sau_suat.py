"""do_sau_suat.py — chứng minh "3 suất/card · 6 suất/2 card · hàng chờ vào đúng".

    py tools/do_sau_suat.py --so-job 9 --ra 12000

Luật đo: `docs/ltt_llm_dual/LUAT_DO_SAU_SUAT.md`. Đọc nó trước khi đọc số.

## ⛔ Vì sao tệp này đo CẢ HAI MÁY

Ngày 14/09 tôi kết luận sai **hai lần** vì chỉ nhìn máy A: đầu tiên đổ cho hồ
worker, sau đó bảo `worker-1` chết (nó là tiến trình cha). Nguyên nhân thật —
`reasoning_effort=none` làm model trả 2 token — chỉ lộ ra khi hỏi máy B.

    máy A  ->  ta CẤP PHÁT thế nào      (execution_leases, jobs.status)
    máy B  ->  nó THẬT SỰ LÀM gì        (requests_processing/deferred, GPU)

`requests_deferred` là **đối chứng**: máy B không hoãn mà máy A vẫn xếp hàng ⇒
hàng đợi là của máy A, đúng thiết kế.

## ⛔ Mệnh đề khó nhất: BÀN GIAO

"Có job chạy sau đó" không chứng minh gì — chúng có thể chạy vì lô trước đã
xong sạch. Bằng chứng thật là **mốc thời gian**: giây lease tụt, và giây một job
`queued` thành `running`. Tệp này ghi cả hai và ghép cặp.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
import uuid

GOC_API = "https://app.lttstudios.com/api/v1"
KHOA = pathlib.Path("C:/LTTPlatform/secrets/van_hanh_khoa/vh1-a.key")
MAY_B = "192.168.2.66"
CONG_METRIC = {"ltt_38_3090": 8282, "ltt_35_5060": 8281}

#: Job DÀI — xem luật §2. Ngắn thì các lượt kết thúc lệch nhau và hàng đợi
#: không bao giờ kịp hình thành (đo 14/09: `max_tokens=1500` cho đỉnh 3, không
#: phải 6).
DE_BAI = ("Viet mot bai phan tich chi tiet ve kien truc he thong phan tan: "
          "dat van de, cac thanh phan, danh doi, va vi du cu the. Viet dai va "
          "day du, khong tom tat.")


def _dbs():
    env = pathlib.Path("C:/LTTPlatform/secrets/app.env").read_text(
        encoding="utf-8", errors="replace")
    for dong in env.splitlines():
        k, sep, v = dong.partition("=")
        if sep and k.strip() == "LTT_DATABASE_URL":
            return v.strip().strip('"').strip("'")
    raise SystemExit("khong thay LTT_DATABASE_URL")


def _may_b(cong: int) -> dict:
    """`{processing, deferred}` của một cổng máy B, hoặc `{}` khi không hỏi được."""
    import subprocess
    khoa_ssh = pathlib.Path.home() / ".ssh" / "nexus_b"
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
             "-i", str(khoa_ssh), f"lengo@{MAY_B}",
             f"curl -s -m 8 http://127.0.0.1:{cong}/metrics"],
            capture_output=True, timeout=20)
        ra: dict = {}
        for d in r.stdout.decode("utf-8", "replace").splitlines():
            if d.startswith("llamacpp:requests_processing "):
                ra["processing"] = int(float(d.rsplit(" ", 1)[1]))
            elif d.startswith("llamacpp:requests_deferred "):
                ra["deferred"] = int(float(d.rsplit(" ", 1)[1]))
        return ra
    except Exception:                       # noqa: BLE001
        return {}


class BoGpu(threading.Thread):
    """Duty cycle THAT cua hai card, 500 ms/mau, qua MOT phien SSH thuong truc.

    ⛔ Vi sao khong dung Task Manager cua Windows: no ve engine **3D**, con
       llama.cpp chay tren engine **Compute_0/CUDA**. Card dang sinh token o
       1787 MHz / 316 W van hien "0 %" o do — do la ly do bao cao "3090 chay
       nho giot" ngay 14/09, va `nvidia-smi` bac bo no (do duoc: 76 % so mau
       >= 50 %, mot mach 36 giay lien).
    """

    def __init__(self, nhip_ms: int = 500):
        super().__init__(daemon=True)
        self.nhip_ms = nhip_ms
        self.mau: list[tuple] = []
        self._p = None

    def run(self) -> None:
        import subprocess
        khoa_ssh = pathlib.Path.home() / ".ssh" / "nexus_b"
        try:
            self._p = subprocess.Popen(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                 "-i", str(khoa_ssh), f"lengo@{MAY_B}",
                 "nvidia-smi --query-gpu=index,utilization.gpu,clocks.sm,"
                 f"power.draw --format=csv,noheader,nounits --loop-ms={self.nhip_ms}"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except Exception:                   # noqa: BLE001
            return
        t0 = time.monotonic()
        for dong in self._p.stdout:         # type: ignore[union-attr]
            try:
                c = dong.decode("utf-8", "replace").strip().split(", ")
                self.mau.append((round(time.monotonic() - t0, 2), int(c[0]),
                                 int(c[1]), int(c[2]), float(c[3])))
            except Exception:               # noqa: BLE001
                pass

    def dung(self) -> None:
        if self._p is not None:
            self._p.kill()

    def duty(self, gpu: int) -> dict:
        """Ti le mau card `gpu` that su dang tinh, va mach lien tuc dai nhat."""
        v = [m for m in self.mau if m[1] == gpu]
        if not v:
            return {}
        ban = [m[2] >= 50 for m in v]
        dai = cur = 0
        for b in ban:
            cur = cur + 1 if b else 0
            dai = max(dai, cur)
        return {"mau": len(v), "ban_pc": round(100 * sum(ban) / len(v)),
                "util_tb": round(sum(m[2] for m in v) / len(v)),
                "w_tb": round(sum(m[4] for m in v) / len(v)),
                "mach_dai_s": round(dai * self.nhip_ms / 1000, 1),
                "chuoi": "".join("#" if m[2] >= 50 else ("+" if m[2] > 5 else ".")
                                 for m in v)}


class BoLayMau(threading.Thread):
    """Chụp CẢ HAI máy mỗi `nhip_s` giây."""

    def __init__(self, url: str, nhip_s: float = 2.0, nhip_may_b: int = 3):
        super().__init__(daemon=True)
        self.url, self.nhip_s, self.nhip_may_b = url, nhip_s, nhip_may_b
        self.mau: list[dict] = []
        self._dung = threading.Event()

    def run(self) -> None:
        from sqlalchemy import create_engine, text

        eng = create_engine(self.url)
        t0 = time.monotonic()
        dem = 0
        while not self._dung.wait(self.nhip_s):
            dem += 1
            m: dict = {"t": round(time.monotonic() - t0, 1)}
            try:
                with eng.connect() as c:
                    hang = c.execute(text(
                        "SELECT resource, count(*) FROM execution_leases "
                        "GROUP BY resource")).all()
                    tt = c.execute(text(
                        "SELECT status, count(*) FROM jobs WHERE app_slug='ltt_llm' "
                        "AND created_at > now() - interval '1 hour' "
                        "GROUP BY status")).all()
                m["lease"] = {r[0]: int(r[1]) for r in hang}
                m["tong"] = sum(int(r[1]) for r in hang)
                m["job"] = {r[0]: int(r[1]) for r in tt}
            except Exception as e:          # noqa: BLE001
                m["loi_A"] = str(e)[:90]
            # Máy B chậm hơn (đi qua SSH) nên thưa hơn; nhưng KHÔNG bỏ hẳn.
            if dem % self.nhip_may_b == 0:
                m["mayB"] = {ten: _may_b(c) for ten, c in CONG_METRIC.items()}
            self.mau.append(m)

    def dung(self) -> None:
        self._dung.set()


def _mot_job(i: int, model: str, ra_token: int, ket: list) -> None:
    import httpx

    k = KHOA.read_text().strip()
    H = {"Authorization": "Bearer " + k, "Content-Type": "application/json"}
    vao = {"model": model, "max_tokens": ra_token,
           "messages": [{"role": "user", "content": DE_BAI}]}
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=1800) as c:
            q = c.post(GOC_API + "/quotes",
                       headers={**H, "Idempotency-Key": uuid.uuid4().hex},
                       json={"tool": "text.chat", "input": vao})
            if q.status_code >= 300:
                ket.append({"i": i, "model": model, "pha": "quote",
                            "ma": q.status_code, "chi": q.text[:120]})
                return
            j = c.post(GOC_API + "/jobs",
                       headers={**H, "Idempotency-Key": uuid.uuid4().hex},
                       json={"tool": "text.chat", "quote": q.json()["quote"],
                             "input": vao})
            if j.status_code >= 300:
                ket.append({"i": i, "model": model, "pha": "jobs",
                            "ma": j.status_code, "chi": j.text[:120]})
                return
            jid = j.json()["id"]
            while time.monotonic() - t0 < 1700:
                time.sleep(5)
                r = c.get(f"{GOC_API}/jobs/{jid}", headers=H)
                d = r.json()
                if d.get("status") in ("succeeded", "failed", "cancelled"):
                    r = d.get("result") or {}
                    u = r.get("usage") or {}
                    # ⭐ GIU NGUYEN VAN, khong chi dem token: "check ket qua tra
                    #    ve" la mot menh de rieng — mot lo job co the dung gio,
                    #    dung suat, dung GPU va van tra ve rong (memory "model
                    #    nha tra ve rong khoang mot nua luot").
                    van = r.get("content") or r.get("text") or ""
                    if not van and isinstance(r.get("choices"), list) and r["choices"]:
                        van = (r["choices"][0].get("message") or {}).get("content") or ""
                    giay = round(time.monotonic() - t0, 1)
                    ra = u.get("output_tokens") or u.get("completion_tokens") or 0
                    ket.append({"i": i, "model": model, "pha": d["status"],
                                "ma": 200, "giay": giay, "token_ra": ra,
                                "ky_tu": len(van), "van": van,
                                "toc": round(ra / max(giay, 0.1), 1)})
                    return
            ket.append({"i": i, "model": model, "pha": "HET GIO", "ma": 0})
    except Exception as e:                  # noqa: BLE001
        ket.append({"i": i, "model": model, "pha": "LOI",
                    "chi": f"{type(e).__name__}: {e}"[:120]})


def _cap_ban_giao(mau: list[dict], trong_giay: float = 15.0) -> list[dict]:
    """Cặp (lease TỤT, job queued VÀO CHẠY) cách nhau ≤ `trong_giay`.

    ⛔ Đây là bằng chứng của M3. "Có job chạy sau đó" KHÔNG phải bằng chứng —
       chúng có thể chạy vì lô trước đã xong sạch.
    """
    co = [m for m in mau if "tong" in m]
    cap = []
    # `strict=False` co chu y: `co[1:]` ngan hon `co` dung mot phan tu.
    for a, b in zip(co, co[1:], strict=False):
        if b["tong"] < a["tong"]:           # mot suat vua nha
            cho_truoc = (a.get("job") or {}).get("queued", 0)
            for c in co:
                if c["t"] <= b["t"] or c["t"] - b["t"] > trong_giay:
                    continue
                if (c.get("job") or {}).get("queued", 0) < cho_truoc \
                        and c["tong"] >= b["tong"]:
                    cap.append({"nha_luc": b["t"], "vao_luc": c["t"],
                                "tre_s": round(c["t"] - b["t"], 1)})
                    break
    return cap


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-job", type=int, default=9,
                    help="6 de lap day + phan du de tao hang cho")
    ap.add_argument("--ra", type=int, default=12000, help="max_tokens moi job")
    ap.add_argument("--model", default="",
                    help="chi mot model (vd ltt-3.8) — bai do RIENG mot card; "
                         "bo trong = tron hai model nhu cu")
    ap.add_argument("--ban-ghi", default="ket_sau_suat.json")
    a = ap.parse_args()

    url = _dbs()
    from sqlalchemy import create_engine, text
    with create_engine(url).connect() as c:
        nen = c.execute(text("SELECT count(*) FROM execution_leases")).scalar()
    b0 = {t: _may_b(p) for t, p in CONG_METRIC.items()}
    dang_chay = sum(int((v or {}).get("processing", 0)) for v in b0.values())
    print(f"== NEN: {nen} lease tren may A · {dang_chay} request dang chay tren may B ==")
    if nen or dang_chay:
        print("   ⛔ NEN KHONG SACH — dung lai. Moi so sau day se thuoc mot kich ban KHAC")
        print("      va no se khong tu khai dieu do (luat §4).")
        return 2

    bo = BoLayMau(url)
    bo.start()
    gpu = BoGpu()
    gpu.start()
    ket: list = []

    def _model(i: int) -> str:
        return a.model or ("ltt-3.8" if i % 2 == 0 else "ltt-3.5")

    luong = [threading.Thread(target=_mot_job, args=(i, _model(i), a.ra, ket))
             for i in range(a.so_job)]
    print(f"== nop {a.so_job} job, max_tokens={a.ra} ==")
    for t in luong:
        t.start()
        time.sleep(0.4)          # rai deu, khong dam mot phat
    for t in luong:
        t.join()
    bo.dung(); bo.join(timeout=8)
    gpu.dung(); gpu.join(timeout=5)

    co = [m for m in bo.mau if "tong" in m]
    dinh = max((m["tong"] for m in co), default=0)
    dinh_res: dict = {}
    for m in co:
        for k, v in (m.get("lease") or {}).items():
            dinh_res[k] = max(dinh_res.get(k, 0), v)
    song_song = any(len(m.get("lease") or {}) >= 2 for m in co)
    dinh_cho = max(((m.get("job") or {}).get("queued", 0) for m in co), default=0)
    hoan = max((sum((v or {}).get("deferred", 0) for v in (m.get("mayB") or {}).values())
                for m in co if "mayB" in m), default=0)
    cap = _cap_ban_giao(bo.mau)
    hong = [k for k in ket if k.get("pha") not in ("succeeded",)]

    print("\n== KET QUA ==")
    for k in sorted(ket, key=lambda x: x["i"]):
        print(f"   job {k['i']} {k['model']:9s} {k['pha']:10s} "
              f"{k.get('giay', '-')!s:>7}s  token_ra={k.get('token_ra')}"
              f"  ky_tu={k.get('ky_tu')}  {k.get('toc')} tok/s")

    print("\n== BA MENH DE ==")
    # 🔴 KY VONG DOI LAI 3/CARD NGAY 14/09/2026 — sua HE, khong sua phep do.
    #
    #    Luot dau truot: do duoc dung 2 suat moi card, on dinh, tren ca hai card.
    #    Toi da tam xep no vao ngan "he dung, ky vong sai" va ha ky vong xuong 2.
    #    Chu san pham bac bo 14/09: *"khong tro slot ve 2, vi ta da co hang cho
    #    job roi"*. Nguyen nhan la mot hang so nam CHET trong `luat_nhan.tran_nen`
    #    (`so_slot - 1`): no tru mot suat cho lop TUONG_TAC, trong khi ca lo job
    #    deu mang `lop=NEN` (`job_runner.py:373`). Nay no la tham so
    #    `ThamSo.chua_slot_tuong_tac`, mac dinh 0 ⇒ nen dung HET slot.
    #
    # ⭐ Nguoi tuong tac KHONG mat bao ve: `NEN_NHUONG` van chan moi luot nen MOI
    #    khi co nguoi tuong tac dang CHO, nen suat vua nha van ve tay ho truoc.
    mot_card = bool(a.model)
    so_slot_ky_vong = 3
    if mot_card:
        ten_res = "ltt_38_3090" if "3.8" in a.model else "ltt_35_5060"
        m1 = dinh_res.get(ten_res, 0) == so_slot_ky_vong and len(dinh_res) == 1
        chi1 = f"card {ten_res} phai dat {so_slot_ky_vong} · dinh do: {dinh_res}"
    else:
        m1 = all(v == so_slot_ky_vong for v in dinh_res.values()) and len(dinh_res) == 2
        chi1 = f"dinh theo tai nguyen: {dinh_res}"
    tong_ky_vong = so_slot_ky_vong * (1 if mot_card else 2)
    m2 = dinh >= tong_ky_vong and (mot_card or song_song)
    m3 = bool(cap)
    for ten, dat, chi in (
            (f"M1  moi card dat {so_slot_ky_vong} suat", m1, chi1),
            (f"M2  tong dat {tong_ky_vong} suat", m2,
             f"dinh tong={dinh} · thay ca hai cung luc={song_song}"),
            ("M3  hang cho vao dung khi mot suat nha", m3,
             f"{len(cap)} cap ban giao: {cap[:3]}")):
        print(f"   [{'DAT ' if dat else 'TRUOT'}] {ten}  — {chi}")

    # ── M4: KET QUA TRA VE, va no la mot menh de RIENG ───────────────────────
    # ⛔ Ba menh de tren deu XANH duoc voi mot lo job tra ve RONG: chung chi do
    #    suat, gio va hang doi. Model nha tung tra rong khoang mot nua luot, nen
    #    "co ket qua" phai duoc doi rieng chu khong suy ra tu "job succeeded".
    #
    # ⭐ Nguong 20 tok/s KHONG phai so dep: do 14/09, mot lo 3 job tren card 2
    #    suat cho 13,7 va 18,8 tok/s (vi job thu ba xep hang), con 3 job tren 3
    #    suat cho 33-40. Nguong nam GIUA hai cum ay nen no phan biet duoc chung.
    xong = [k for k in ket if k.get("pha") == "succeeded"]
    rong = [k["i"] for k in xong if not k.get("ky_tu")]
    cut = [k["i"] for k in xong if 0 < (k.get("ky_tu") or 0) < 200]
    cham = [k["i"] for k in xong if (k.get("toc") or 0) < 20]
    m4 = bool(xong) and not rong and not cut and not cham
    print(f"   [{'DAT ' if m4 else 'TRUOT'}] M4  ket qua tra ve co that va day du"
          f"  — rong={rong} cut={cut} cham(<20 tok/s)={cham}")

    # ── M5: GPU LIEN MACH ────────────────────────────────────────────────────
    # ⛔ Task Manager cua Windows ve bon engine **3D/Copy/Video Encode/Decode**,
    #    KHONG ve **Compute_0 (CUDA)** — card dang sinh token o 343 W / 1665 MHz
    #    / 76 °C van hien "Utilization 0 %" o do. Bao cao "3090 chay nho giot"
    #    ngay 14/09 den tu o ay. `nvidia-smi` bac bo: mot job 11.000 token cho
    #    MOT mach lien tuc 178,0 giay, 95 % so mau >= 50 %. Menh de nay ghim lai.
    duty = {g: gpu.duty(g) for g in (0, 1)}
    card_gpu = 0 if (not mot_card or "3.8" in a.model) else 1
    d = duty.get(card_gpu) or {}
    m5 = (d.get("ban_pc", 0) >= 60) if d else False
    print(f"   [{'DAT ' if m5 else 'TRUOT'}] M5  GPU{card_gpu} lien mach (>=60% mau ban)"
          f"  — ban={d.get('ban_pc')}% util_tb={d.get('util_tb')}%"
          f" {d.get('w_tb')}W mach dai nhat={d.get('mach_dai_s')}s")
    if d.get("chuoi"):
        print("       " + d["chuoi"][:200])

    print("\n== DOI CHUNG ==")
    print(f"   may B hoan (deferred) : {hoan}   (phai la 0)")
    print(f"   dinh job xep hang     : {dinh_cho}")
    print(f"   job hong              : {len(hong)}  {hong[:2] if hong else ''}")

    pass_het = m1 and m2 and m3 and m4 and m5 and hoan == 0 and not hong
    print(f"\n== {'PASS' if pass_het else 'CHUA PASS'} ==")
    pathlib.Path(a.ban_ghi).write_text(
        json.dumps({"ket": ket, "mau": bo.mau, "dinh": dinh,
                    "dinh_res": dinh_res, "cap_ban_giao": cap,
                    "deferred": hoan, "gpu_duty": duty, "gpu_mau": gpu.mau,
                    "menh_de": {"m1": m1, "m2": m2, "m3": m3, "m4": m4,
                                "m5": m5},
                    "pass": pass_het},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   [ban ghi] {a.ban_ghi}")
    return 0 if pass_het else 1


if __name__ == "__main__":
    raise SystemExit(main())
