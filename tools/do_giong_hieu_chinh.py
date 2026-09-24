"""Hieu chinh + benchmark bo do giong cua ASV (lan asv-final "giong", 22/09/2026).

Hai buoc, hai quyen:

  thu   (NANG QUYEN, qua `setup\\do_on_dinh.ps1 -Do do-giong`) — dung mot kho
        long tieng THAT: video nghiem thu (Desktop\\TEST VIDEO) -> ASR san pham
        (`giai_doan_chep_loi.chep_loi`) -> dich bang model nha that
        (`long_tieng.loi_nhac` + `ai.goi`, pool khoa that, CSDL nhap) -> doc
        TUNG DOAN bang LTT Voice THAT (:8120, `giong_noi.doc_mot_doan`).
        Can `secrets\\app.env` (pool + token giong) — script nap vao TIEN TRINH,
        khong in gia tri nao.
  do    (quyen thuong, chay BANG python cua qc-venv) — chay `bo_do.chay_tat_ca`
        tren kho do, do tai nguyen (nvidia-smi lay mau), dung doi chung am
        (lech cap, cat cut, chen nhieu/khoang lang) va in phan bo WER/CER/SQUIM.

Kho ghi o `--ra` (mac dinh `C:\\lttinf\\asvf_giong` — duong NGAN, MAX_PATH).
⛔ Kho chua tieng tong hop tu giong kho chung: KHONG commit, KHONG chia se.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import subprocess
import sys
import threading
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

RA_MAC_DINH = r"C:\lttinf\asvf_giong"
THU_MUC_VIDEO = pathlib.Path(os.path.expanduser("~")) / "Desktop" / "TEST VIDEO"

#: (ma, tien to ten tep video, ngon ngu dich, giong). v3 = 106,8 s, v2 = 190 s
#: (PLAN.md bang kiem ke) — ca hai trong khoang 1-3 phut cua de bai.
NGUON = [
    ("v3vi", "深度解析", "vi", ["Minh Đức", "Ngọc Huyền"]),
    ("v2vi", "暴雨天", "vi", ["Thái Sơn", "Thùy Dung"]),
    ("v3en", "深度解析", "en", ["@en:vc_b24b1aee8c4d471186b0e1c1d67d860a"]),
    # Them mau hieu chinh (khong phai dau vao benchmark 1-3 phut): ASR san pham
    # gop thanh doan dai 15-25 s, nen hai video 1-3 phut chi cho ~16 doan vi.
    ("v1vi", "廉价", "vi", ["Mai Anh", "Minh Triết"]),
    ("v4vi", "真人", "vi", ["Quang Sơn", "Ngọc Trân"]),
    ("v2en", "暴雨天", "en", ["@en:vc_b24b1aee8c4d471186b0e1c1d67d860a"]),
]
KHO_GIONG_CHUNG = pathlib.Path(r"C:\LTTPlatform\data\voice_goc\kho_chung")


def _ffmpeg() -> str:
    from platform_core import media
    return media.ffmpeg_bin()


def _json(p: pathlib.Path, obj=None):
    if obj is None:
        return json.loads(p.read_text(encoding="utf-8"))
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return obj


# ══════════════════════════════════════════════════════════════════════════
#  thu — can app.env (nang quyen)
# ══════════════════════════════════════════════════════════════════════════

def _mo_db():
    import tempfile

    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_giong_")) / "do.db"
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tam.as_posix()}"
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from tests.fixtures import asv_e2e

    so = asv_e2e.nap_khoa_pool(db)
    db.commit()
    print(f"  [OK] nap {so} dong khoa ltt_llm tu pool that (chi doc)", flush=True)
    return db, so


def _ban_ghi(ra: pathlib.Path, ma_video: str, tien_to: str) -> dict:
    """ASR nguon bang DUONG SAN PHAM, cache theo video."""
    p = ra / f"ban_ghi_{ma_video[:2]}.json"
    if p.is_file():
        return _json(p)
    from apps.auto_scan_video import ban_ghi, giai_doan_chep_loi, nhap_media

    video = next(THU_MUC_VIDEO.glob(f"{tien_to}*"))
    wav = ra / f"nguon_{ma_video[:2]}.wav"
    subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-vn",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
                   check=True)
    t0 = time.monotonic()
    tho = giai_doan_chep_loi.chep_loi(str(wav), ngon_ngu="zh")
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=nhap_media.soi(str(wav))["thoi_luong"])
    ban["_giay_asr"] = round(time.monotonic() - t0, 1)
    ban["_video"] = video.name
    print(f"  [OK] ASR {ma_video[:2]}: {len(ban['doan'])} doan, {ban['_giay_asr']}s",
          flush=True)
    return _json(p, ban)


def _dich(db, ra: pathlib.Path, ma: str, ban: dict, dich: str) -> dict:
    p = ra / f"dich_{ma}.json"
    if p.is_file():
        return _json(p)
    from apps.auto_scan_video import ai, long_tieng

    doan = list(ban["doan"])
    ra_dich: dict = {}
    for i, lo in enumerate(long_tieng.chia_lo(doan)):
        ma_gui = {str(d["ma"]) for d in lo}
        msg = long_tieng.loi_nhac(lo, tat_ca=doan,
                                  ngon_ngu_goc=str(ban.get("ngon_ngu") or "zh"),
                                  dac_diem_giong={"gioi_tinh": "nam", "toc_do": "vua"},
                                  ngon_ngu_dich=dich)
        for thu in range(3):
            try:
                kq = ai.goi(db, ai.CHUYEN_LOI_THOAI, msg, max_tokens=0)
                moi = long_tieng.doc_chuyen(ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI),
                                            ma_gui)
                break
            except Exception as exc:                    # noqa: BLE001
                print(f"  [..] lo {i} lan {thu}: {type(exc).__name__}: "
                      f"{str(exc)[:120]}", flush=True)
                moi = {}
        ra_dich.update({k: v["chu"] for k, v in moi.items()})
        print(f"  [OK] dich {ma} lo {i}: {len(moi)}/{len(lo)}", flush=True)
    return _json(p, ra_dich)


def _ref_en(ma_kho: str) -> str:
    from apps.ltt_voice import sidecar_client
    d = sidecar_client.ghi_danh(str(KHO_GIONG_CHUNG / f"{ma_kho}.wav"))
    return str(d["ref_b64"])


def thu(ra: pathlib.Path) -> int:
    ra.mkdir(parents=True, exist_ok=True)
    if not str(os.environ.get("LTT_ASV_POOL_URL", "")).strip():
        print("BO QUA: chua co LTT_ASV_POOL_URL (chay qua setup\\do_on_dinh.ps1).")
        return 2
    db, so = _mo_db()
    if not so:
        return 1
    from apps.auto_scan_video import giong_noi

    kho_p = ra / "kho.json"
    kho = _json(kho_p) if kho_p.is_file() else []
    da_co = {(d["nguon"], d["ma"]) for d in kho}
    for ma, tien_to, dich, cac_giong in NGUON:
        ban = _ban_ghi(ra, ma, tien_to)
        chu = _dich(db, ra, ma, ban, dich)
        ref = None
        if cac_giong[0].startswith("@en:"):
            ref = _ref_en(cac_giong[0][4:])
        (ra / ma).mkdir(exist_ok=True)
        for i, d in enumerate(ban["doan"]):
            k = str(d["ma"])
            if (ma, k) in da_co or not chu.get(k):
                continue
            giong = cac_giong[i % len(cac_giong)]
            t0 = time.monotonic()
            try:
                wav, _h = giong_noi.doc_mot_doan(
                    chu[k], ref_b64=ref, preset=None if ref else giong)
            except Exception as exc:                    # noqa: BLE001
                print(f"  [!!] TTS {ma}/{k}: {type(exc).__name__}: {exc}", flush=True)
                continue
            tep = ra / ma / f"{k}.wav"
            tep.write_bytes(wav)
            kho.append({"nguon": ma, "ma": k, "ngon_ngu": dich, "giong": giong,
                        "chu": chu[k], "goc": d.get("chu"), "tep": str(tep),
                        "giay_sinh": round(time.monotonic() - t0, 2)})
            _json(kho_p, kho)
        print(f"  [OK] {ma}: {sum(1 for x in kho if x['nguon'] == ma)} doan tieng",
              flush=True)
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  do — quyen thuong, python cua qc-venv
# ══════════════════════════════════════════════════════════════════════════

class LayMauGpu(threading.Thread):
    """Lay mau VRAM (toan card + theo PID) moi 0,25 s bang nvidia-smi."""

    def __init__(self):
        super().__init__(daemon=True)
        self.dung = False
        self.mau: list = []

    def run(self):
        while not self.dung:
            try:
                tong = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5).stdout.strip()
                pid = subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5).stdout.strip()
                m, u = (int(x) for x in tong.split(",")[:2])
                self.mau.append((time.monotonic(), m, u, pid))
            except Exception:                           # noqa: BLE001
                pass
            time.sleep(0.25)


def _dung_16k(vao: str, ra: str, loc: str = "") -> None:
    subprocess.run([_ffmpeg_tho(), "-y", "-loglevel", "error", "-i", vao,
                    *(["-af", loc] if loc else []), "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", ra], check=True)


def _ffmpeg_tho() -> str:
    import shutil
    return os.environ.get("LTT_FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def _phan_vi(xs: list, q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * q
    lo, hi = int(i), min(len(xs) - 1, int(i) + 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def _tom(xs: list) -> dict:
    return {"n": len(xs), "min": round(min(xs), 4) if xs else None,
            "p50": round(_phan_vi(xs, .5), 4), "p90": round(_phan_vi(xs, .9), 4),
            "p95": round(_phan_vi(xs, .95), 4), "max": round(max(xs), 4) if xs else None,
            "tb": round(statistics.fmean(xs), 4) if xs else None}


def _chay_do(dv, nhan: str) -> tuple[dict, dict]:
    from apps.asv_gpu.do_luong import bo_do

    lm = LayMauGpu()
    nen = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                          "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout.strip()
    lm.start()
    t0 = time.monotonic()
    kq = bo_do.chay_tat_ca(dv)
    lm.dung = True
    lm.join(2)
    dinh = max((m for _, m, _, _ in lm.mau), default=0)
    sau = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                          "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout.strip()
    tn = {"nhan": nhan, "giay": round(time.monotonic() - t0, 1),
          "vram_card_truoc_mb": int(nen or 0), "vram_card_dinh_mb": dinh,
          "vram_card_sau_mb": int(sau or 0),
          "gpu_util_dinh": max((u for _, _, u, _ in lm.mau), default=0),
          "theo_bo_do": {t: r.get("tai_nguyen") | {"giay": r.get("giay")}
                         for t, r in kq.items() if r.get("tai_nguyen")}}
    return kq, tn


def do(ra: pathlib.Path) -> int:
    import jiwer  # noqa: F401 - chi chay duoc trong qc-venv
    from apps.asv_gpu.do_luong import bo_do, chuan_hoa_loi

    kho = _json(ra / "kho.json")
    tam = ra / "_do"
    tam.mkdir(exist_ok=True)
    bao: dict = {"kho": {}, "tai_nguyen": [], "doi_chung": {}}

    for nn in ("vi", "en"):
        doan = [d for d in kho if d["ngon_ngu"] == nn]
        if not doan:
            continue
        ds = []
        for d in doan:
            dich = tam / f"{d['nguon']}_{d['ma']}.wav"
            if not dich.is_file():
                _dung_16k(d["tep"], str(dich))
            ds.append({"ma": f"{d['nguon']}/{d['ma']}", "tep": str(dich),
                       "chu": d["chu"]})
        dv = bo_do.DauVao(doan_tieng=ds, ngon_ngu_dich=nn)
        kq, tn = _chay_do(dv, f"that_{nn}_{len(ds)}doan")
        bao["tai_nguyen"].append(tn)
        g = kq["giong"]["ket_qua"]
        s = kq["chat_luong_tieng"]["ket_qua"]
        bao["kho"][nn] = {"giong": g, "squim": s}
        wer = [r["wer"] for r in g.values() if "wer" in r]
        print(f"\n== {nn}: {len(ds)} doan THAT")
        print("  WER ", _tom(wer))
        if nn == "vi":
            print("  CER ", _tom([r["cer"] for r in g.values() if "cer" in r]))
        for k in ("stoi", "pesq", "si_sdr"):
            print(f"  {k:6s}", _tom([r[k] for r in s.values() if k in r]))

        # ── Doi chung A: LECH CAP (tieng doan i, kich ban doan i+1) ─────────
        ma = [x["ma"] for x in ds]
        lech = []
        for i in range(len(ma)):
            a, b = g.get(ma[i]) or {}, g.get(ma[(i + 1) % len(ma)]) or {}
            if a.get("gia_thuyet_chuan") is not None and b.get("tham_chieu_chuan"):
                lech.append(chuan_hoa_loi.cham(b["tham_chieu_chuan"],
                                               a["gia_thuyet_chuan"], nn))
        bao["doi_chung"][f"{nn}_lech_cap"] = {
            "wer": _tom([x["wer"] for x in lech]),
            "cer": _tom([x["cer"] for x in lech if "cer" in x])}

        # ── Doi chung B: THIEU CHU THAT — cat bo 1/3 cuoi tep tieng ─────────
        # ── Doi chung C: nhieu trang SNR 10 dB / khoang lang 0,4 s giua cau ──
        # ⭐ Mot TUPLE ten, khong phai dict {ten: ham|None}: hai trong ba bien
        #    the dung duong ffmpeg rieng ben duoi, nen o duoi la None — va
        #    mot dict tron ham voi None lam moi loi goi thanh "None not
        #    callable" o mypy, cho mot bang ma chi MOT nhanh doc toi.
        bien_the = ("cat_1_3_cuoi", "nhieu_snr10", "lang_giua_0.4s")
        for ten in bien_the:
            ds2 = []
            for x, d in zip(ds, doan, strict=False):
                giay = (g.get(x["ma"]) or {}).get("giay") or 0
                if giay < 1.5:
                    continue
                dich = tam / f"{ten}_{d['nguon']}_{d['ma']}.wav"
                if not dich.is_file():
                    if ten == "cat_1_3_cuoi":
                        _dung_16k(x["tep"], str(dich),
                                  f"atrim=0:{giay * 2 / 3:.3f}")
                    elif ten == "nhieu_snr10":
                        # anoisesrc bien do 0,1 ~ -20 dBFS; tieng ~ -20..-10 LUFS
                        subprocess.run([_ffmpeg_tho(), "-y", "-loglevel", "error",
                                        "-i", x["tep"], "-f", "lavfi", "-i",
                                        f"anoisesrc=d={giay:.3f}:c=white:r=16000:a=0.03",
                                        "-filter_complex", "amix=inputs=2:duration=first:normalize=0",
                                        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                                        str(dich)], check=True)
                    else:
                        nua = giay / 2
                        subprocess.run([_ffmpeg_tho(), "-y", "-loglevel", "error",
                                        "-i", x["tep"], "-filter_complex",
                                        f"[0]atrim=0:{nua:.3f}[a];[0]atrim={nua:.3f},asetpts=PTS-STARTPTS[b];"
                                        f"anullsrc=r=16000:cl=mono,atrim=0:0.4[s];[a][s][b]concat=n=3:v=0:a=1",
                                        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                                        str(dich)], check=True)
                ds2.append({**x, "tep": str(dich)})
            dv2 = bo_do.DauVao(doan_tieng=ds2, ngon_ngu_dich=nn)
            kq2, tn2 = _chay_do(dv2, f"{ten}_{nn}_{len(ds2)}doan")
            bao["tai_nguyen"].append(tn2)
            g2 = kq2["giong"]["ket_qua"]
            s2 = kq2["chat_luong_tieng"]["ket_qua"]
            bao["doi_chung"][f"{nn}_{ten}"] = {
                "wer": _tom([r["wer"] for r in g2.values() if "wer" in r]),
                "cer": _tom([r["cer"] for r in g2.values() if "cer" in r]),
                **{k: _tom([r[k] for r in s2.values() if k in r])
                   for k in ("stoi", "pesq", "si_sdr", "si_sdr_min_cua_so",
                             "pesq_min_cua_so")},
                "chi_tiet_giong": g2, "chi_tiet_squim": s2}
            print(f"  [{ten}] WER", bao["doi_chung"][f"{nn}_{ten}"]["wer"])
    _json(ra / "ket_qua_do.json", bao)
    print("\nghi", ra / "ket_qua_do.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("buoc", nargs="?", default="thu", choices=("thu", "do"))
    ap.add_argument("--ra", default=os.environ.get("LTT_DO_GIONG_RA") or RA_MAC_DINH)
    ap.add_argument("--vong", type=int, default=0, help="(bo qua — tuong thich do_on_dinh.ps1)")
    a = ap.parse_args()
    ra = pathlib.Path(a.ra)
    return thu(ra) if a.buoc == "thu" else do(ra)


if __name__ == "__main__":
    sys.exit(main())
