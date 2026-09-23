r"""do_gioi_giong.py — ĐO giới tính của giọng, và CHẤM 17 giọng `en` kho chung.

    (1) sinh    NÂNG QUYỀN  powershell -File .\setup\do_gioi_giong.ps1 -Buoc sinh
    (2) do-gioi thường      python tools\do_gioi_giong.py do-gioi
    (3) cham-en thường      python tools\do_gioi_giong.py cham-en
    (4) bao-cao thường      python tools\do_gioi_giong.py bao-cao

Hai việc mà chủ dự án lẽ ra phải làm bằng TAY, nay làm bằng phép đo:

  F-03 / L_GIONG_EN §5  — `VoiceProfile.gioi` của 25 giọng kho chung đang rỗng,
      và đề xuất cũ là *"chủ dự án duyệt điền 16/17 theo ghi chú xuất xứ"*. Một
      giọng (Robin) đã lệch chính ghi chú của nó, nên điền tay là đoán tập thể.
      ⇒ Đo bằng `apps/asv_gpu/do_luong/gioi.py` (ECAPA gender, MIT), hiệu chỉnh
        trên **20 preset engine** — tập DUY NHẤT có nhãn giới do bên thứ ba
        (engine) khai, không phải do ta suy.
  L_GIONG_EN §3        — Douglas/Clara được chọn bằng nhịp đọc + dư đỉnh, và
      *"chưa có lượt nghe bằng tai"*. ⇒ Chấm cả 17 giọng trên CÙNG kịch bản bằng
      bộ đo đã có (ASR + jiwer, SQUIM_OBJECTIVE) + Distill-MOS (MIT) + DNSMOS
      P.835 (CC BY 4.0) + thống kê nhịp/độ to (Loại A).

⛔ KHÔNG ghi CSDL production. Bước `bao-cao` in một **đề xuất** để chủ dự án
   duyệt — duyệt SỐ, không duyệt phỏng đoán.

Kho tiếng ghi ở `--ra` (mặc định `C:\lttinf\asvf_dogiong`, đường NGẮN).
⛔ Kho chứa tiếng tổng hợp từ giọng kho chung: KHÔNG commit, KHÔNG chia sẻ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

RA_MAC_DINH = r"C:\lttinf\asvf_dogiong"
KHO_GIONG_CHUNG = pathlib.Path(r"C:\LTTPlatform\data\voice_goc\kho_chung")

# ══════════════════════════════════════════════════════════════════════════
#  Kịch bản — GHIM TRONG MÃ, không phải trong một script tạm
# ══════════════════════════════════════════════════════════════════════════
#
# ⭐ L_GIONG_EN đo trên một kịch bản 70 từ nằm trong scratchpad của phiên đó và
#    KHÔNG có trong kho. Nên bảng của nó không lặp lại được, và bảng dưới đây
#    KHÔNG so sánh trực tiếp được với nó. Kịch bản ở đây nằm trong mã, có
#    sha256 in ra cùng kết quả — đó là điều kiện để lần đo sau nói cùng một câu.
#
# ⚠️ Cố ý KHÔNG có số, viết tắt, URL hay ngoặc: `text_pipeline.chuan_hoa` sẽ
#    đọc tràn chúng ("2024" -> "hai nghìn không trăm..."), và một kịch bản mà
#    hai giọng đọc ra hai độ dài khác nhau thì cột "từ/phút" hết nghĩa.

KICH_BAN = {
    "vi_a": ("vi",
             "Buổi sáng hôm ấy sương còn đọng trên mái ngói, người trong xóm "
             "đã kéo nhau ra bến sông. Ông lão chèo đò kể rằng con nước năm nay "
             "lên sớm hơn mọi năm, và ai cũng biết điều đó nghĩa là mùa gặt sẽ "
             "vất vả. Mấy đứa trẻ vẫn chạy lon ton trên bờ đê, cười nói như thể "
             "chẳng có gì đáng lo. Người ta bảo cái làng này đã sống với dòng "
             "sông đủ lâu để hiểu rằng nó cho đi bao nhiêu thì cũng lấy lại "
             "chừng ấy, không hơn không kém."),
    "en_a": ("en",
             "For most of the year the lighthouse stands empty, and the only "
             "sound is the wind working its way around the tower. The keeper "
             "comes twice a month, climbs the stairs, checks the lamp, and "
             "writes a single line in the logbook before going back down. He "
             "says the hardest part is not the climb but the quiet, because a "
             "quiet room gives a person far too much time to think about "
             "everything they have chosen to leave behind on the mainland."),
    "en_b": ("en",
             "Anyone who has tried to repair an old clock will tell you the "
             "same thing: the problem is almost never the part that stopped "
             "moving. You take off the back plate, and what you find is a "
             "small amount of dried oil in a place nobody thought to look. "
             "The gear that failed was simply the first one to give up. Fix "
             "the oil and the clock will run for another thirty years, which "
             "is a lesson worth more than the clock itself."),
}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _json(p: pathlib.Path, obj=None):
    if obj is None:
        return json.loads(p.read_text(encoding="utf-8"))
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return obj


def _manifest_kho_chung() -> list[dict]:
    m = _json(KHO_GIONG_CHUNG / "manifest.json")
    return list(m["giong"])


#: Giới KHAI trong xuất xứ (`ten_tep_cu` của kho cũ). Đây là thứ đề xuất cũ
#: định điền bằng tay — ở đây nó là **đối tượng bị kiểm**, không phải chân lý.
def gioi_khai(ten_tep_cu: str, ten_hien_thi: str) -> str:
    t = ten_tep_cu.lower()
    if "_nu" in t or "female" in t or "girl" in t:
        return "nu"
    if "male" in t or "_men" in t or "_nam" in t:
        return "nam"
    # Không có dấu hiệu trong tên tệp cũ -> lấy từ tên hiển thị đã duyệt.
    if "nữ" in ten_hien_thi:
        return "nu"
    if "nam" in ten_hien_thi:
        return "nam"
    return ""


# ══════════════════════════════════════════════════════════════════════════
#  (1) sinh — cần app.env (LTT_VOICE_SIDECAR_TOKEN), nâng quyền
# ══════════════════════════════════════════════════════════════════════════

def _viec_sinh() -> list[dict]:
    """Danh sách việc đọc. Tất định, sắp xếp được, không phụ thuộc CSDL."""
    from apps.ltt_voice import giong_mau

    viec: list[dict] = []
    # 20 preset engine — tập hiệu chỉnh CÓ NHÃN (nhãn của engine, không của ta).
    for g in giong_mau.DANH_SACH:
        viec.append({"ma": f"preset__{g.ma}__vi_a", "loai": "preset",
                     "giong": g.ma, "public_id": "", "ten": g.ma,
                     "gioi_nhan": g.gioi, "nguon_nhan": "giong_mau_engine.json",
                     "kich_ban": "vi_a", "ngon_ngu": "vi"})
    # 25 giọng kho chung.
    for v in _manifest_kho_chung():
        lan = str(v["ngon_ngu"])
        bans = ["vi_a"] if lan == "vi" else ["en_a", "en_b"]
        for kb in bans:
            viec.append({"ma": f"chung__{v['public_id']}__{kb}", "loai": "chung",
                         "giong": "", "public_id": v["public_id"],
                         "ten": v["ten_hien_thi"],
                         "gioi_nhan": gioi_khai(v["ten_tep_cu"], v["ten_hien_thi"]),
                         "nguon_nhan": f"ghi_chu/{v['ten_tep_cu']}",
                         "kich_ban": kb, "ngon_ngu": lan,
                         "tep_goc": str(KHO_GIONG_CHUNG / v["tep"])})
    return viec


def sinh(ra: pathlib.Path, chi: str = "", so: int = 0) -> int:
    ra.mkdir(parents=True, exist_ok=True)
    (ra / "tieng").mkdir(exist_ok=True)
    from apps.auto_scan_video import giong_noi
    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("BO QUA: chua co LTT_VOICE_SIDECAR_TOKEN "
              "(chay qua setup\\do_gioi_giong.ps1).")
        return 2

    kho_p = ra / "kho.json"
    kho = _json(kho_p) if kho_p.is_file() else []
    da_co = {d["ma"] for d in kho}
    ref_cache: dict[str, str] = {}

    viec = [v for v in _viec_sinh()
            if not chi or v["ngon_ngu"] == chi or v["loai"] == chi]
    con = [v for v in viec if v["ma"] not in da_co]
    # ⭐ `--so 1` de THU DUONG truoc khi giu khoa may hai muoi phut: mot luot
    #    doc bang mot yeu cau cua khach, khong phai mot luot nang.
    if so > 0:
        con = con[:so]
    print(f"  [..] {len(con)}/{len(viec)} luot con phai doc", flush=True)
    for i, v in enumerate(con, 1):
        ngon_ngu, van_ban = KICH_BAN[v["kich_ban"]]
        chu_doc = giong_noi.chuan_hoa_van_ban(van_ban)
        ref = None
        if v["loai"] == "chung":
            pid = v["public_id"]
            if pid not in ref_cache:
                # ⭐ Ghi danh THANG tu clip goc: khong can CSDL production, va
                #    khong dong vao mot dong nao cua khach.
                #
                # ⚠️ Bieu dien khach THUC SU dung la `VoiceRepr` da luu, khong
                #    phai ban ghi danh lai nay. Hai thu bang nhau **chi khi**
                #    `ghi_danh` tat dinh — nen lan dau ta ghi danh HAI luot va
                #    ghi lai ket qua so sanh, thay vi gia dinh.
                r1 = str(sidecar_client.ghi_danh(v["tep_goc"])["ref_b64"])
                if not ref_cache:
                    r2 = str(sidecar_client.ghi_danh(v["tep_goc"])["ref_b64"])
                    _json(ra / "ghi_danh_tat_dinh.json",
                          {"public_id": pid, "giong_nhau": r1 == r2,
                           "sha_1": _sha(r1)[:16], "sha_2": _sha(r2)[:16]})
                    print(f"  [..] ghi_danh tat dinh: {r1 == r2}", flush=True)
                ref_cache[pid] = r1
            ref = ref_cache[pid]
        t0 = time.monotonic()
        try:
            wav, _h = giong_noi.doc_mot_doan(
                van_ban, ref_b64=ref, preset=None if ref else v["giong"])
        except Exception as exc:                    # noqa: BLE001
            print(f"  [!!] {v['ma']}: {type(exc).__name__}: {exc}", flush=True)
            continue
        tep = ra / "tieng" / f"{v['ma']}.wav"
        tep.write_bytes(wav)
        d = dict(v)
        d.update({"tep": str(tep), "chu": van_ban, "chu_doc": chu_doc,
                  "sha_kich_ban": _sha(van_ban)[:16],
                  "giay_sinh": round(time.monotonic() - t0, 2)})
        kho.append(d)
        _json(kho_p, kho)
        print(f"  [OK] {i}/{len(con)} {v['ma']} ({d['giay_sinh']}s)", flush=True)
    print(f"  [OK] kho: {len(kho)} tep tieng -> {kho_p}", flush=True)
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  (2) do-gioi — bo do `gioi` tren CA HAI mat: clip goc + tieng da sinh
# ══════════════════════════════════════════════════════════════════════════

def do_gioi(ra: pathlib.Path) -> int:
    from apps.asv_gpu.do_luong import gioi

    kho = _json(ra / "kho.json")
    clip = [{"ma": d["ma"], "tep": d["tep"]} for d in kho]
    # Clip GOC cua 25 giong kho chung: mot cai nhin doc lap voi engine.
    for v in _manifest_kho_chung():
        clip.append({"ma": f"goc__{v['public_id']}",
                     "tep": str(KHO_GIONG_CHUNG / v["tep"])})

    # ⭐ Cong don theo `ma` + PHIEN BAN bo do. Kho tieng dung dan tung lo, va
    #    cham lai 60 clip de lay them 5 la tieu GPU cua may DANG PHUC VU KHACH.
    #    ⛔ Phien ban bo do doi ⇒ bo het ket qua cu: tron hai phien ban trong
    #       mot bang la cach chac chan nhat de mot bang so noi doi.
    p = ra / "gioi.json"
    cu = _json(p) if p.is_file() else {}
    ket = dict(cu.get("ket_qua") or {}) if cu.get("phien_ban") == gioi.PHIEN_BAN else {}
    moi = [c for c in clip if c["ma"] not in ket]
    print(f"  [..] cham gioi {len(moi)}/{len(clip)} clip (con lai dung lai)",
          flush=True)
    tai = cu.get("tai_nguyen") if not moi else None
    if moi:
        kq = gioi.do_gioi(moi)
        ket.update(kq["ket_qua"])
        tai = kq["tai_nguyen"]
    _json(p, {"ket_qua": ket, "tai_nguyen": tai, "phien_ban": gioi.PHIEN_BAN})
    print(f"  [OK] {p}  ({len(ket)} clip)  tai_nguyen={tai}", flush=True)
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  (3) cham-en — 17 giong `en` tren cung kich ban
# ══════════════════════════════════════════════════════════════════════════

def _do_to(tep: str) -> dict:
    """LUFS-I, LRA, true peak — Loại A, ffmpeg `ebur128=peak=true`."""
    from platform_core import media

    p = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", tep,
                        "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    ra: dict = {}
    dong = [x.strip() for x in (p.stderr or "").splitlines()]
    for i, x in enumerate(dong):
        if x.startswith("I:") and "LUFS" in x:
            ra["lufs_i"] = float(x.split()[1])
        elif x.startswith("LRA:") and "LU" in x and "lra" not in ra:
            ra["lra"] = float(x.split()[1])
        elif x.startswith("Peak:") and i and dong[i - 1].startswith("True peak"):
            ra["true_peak_dbfs"] = float(x.split()[1])
    return ra


#: Doi chung cho bang xep hang. 🔴 KHONG CO DOI CHUNG THI MOT BANG DIEM CHI LA
#: MOT THU TU: doc gia khong biet chenh 0,15 diem Distill-MOS la nhieu hay it.
#: Ba bien doi duoi day lam BAN THAN thang do lo ra tren chinh kho nay.
#: Doan THAT dem di bien dang. ⛔ GHIM MOT MA, khong lay "phan tu dau cua kho":
#: thu tu kho la thu tu tong hop, nen bang doi chung se doi giong giua hai lan
#: chay ma khong ai thay. Day la Douglas — giong L_GIONG_EN da chon.
MA_DOI_CHUNG = "chung__vc_1b65a9e636a54ab59c6a69b8046d3d0a__en_a"

DOI_CHUNG = {
    "nhieu10db": ["-f", "lavfi", "-i", "anoisesrc=c=white:r=16000:a=0.03",
                  "-filter_complex", "amix=inputs=2:duration=first:normalize=0"],
    "meo_clip": ["-af", "volume=6dB,alimiter=limit=0.999"],
    "bang_thong_hep": ["-af", "lowpass=f=3400,highpass=f=300"],
}


def _doi_chung(ra: pathlib.Path, goc: dict) -> list[dict]:
    """Dung ba ban BIEN DANG tu mot doan that. Tra danh sach doan nhu `kho`."""
    from platform_core import media

    d = ra / "doi_chung"
    d.mkdir(parents=True, exist_ok=True)
    ds = []
    for ten, loc in DOI_CHUNG.items():
        p = d / f"doi_chung__{ten}.wav"
        if not p.is_file():
            subprocess.run([media.ffmpeg_bin(), "-y", "-loglevel", "error",
                            "-i", goc["tep"], *loc, "-ac", "1", "-ar", "16000",
                            "-c:a", "pcm_s16le", str(p)], check=True)
        ds.append({"ma": f"doi_chung__{ten}", "tep": str(p), "chu": goc["chu"]})
    return ds


def cham_en(ra: pathlib.Path) -> int:
    from apps.asv_gpu.do_luong import giong, squim, venv

    kho = [d for d in _json(ra / "kho.json") if d["ngon_ngu"] == "en"]
    if not kho:
        print("BO QUA: kho chua co tieng `en`.")
        return 2
    doan = [{"ma": d["ma"], "tep": d["tep"], "chu": d["chu"]} for d in kho]
    goc = next((d for d in kho if d["ma"] == MA_DOI_CHUNG), kho[0])
    doan += _doi_chung(ra, goc)

    print(f"  [..] ASR + jiwer tren {len(doan)} doan", flush=True)
    g = giong.do_giong(doan, ngon_ngu="en")
    print(f"  [..] SQUIM_OBJECTIVE tren {len(doan)} doan", flush=True)
    s = squim.do_squim([{"ma": d["ma"], "tep": d["tep"]} for d in doan])
    print(f"  [..] Distill-MOS + DNSMOS tren {len(doan)} doan", flush=True)
    m = venv.chay(pathlib.Path(__file__).with_name("do_gioi_giong_mos.py"),
                  {"doan": [{"ma": d["ma"], "tep": d["tep"]} for d in doan]},
                  timeout_s=300 + 10 * len(doan))
    print("  [..] do to (ebur128)", flush=True)
    to = {d["ma"]: _do_to(d["tep"]) for d in doan}

    _json(ra / "cham_en.json",
          {"giong": g, "squim": s, "mos": m, "do_to": to,
           "phien_ban": {"giong": giong.PHIEN_BAN, "squim": squim.PHIEN_BAN,
                         "mos": m.get("phien_ban", "")}})
    print(f"  [OK] {ra / 'cham_en.json'}", flush=True)
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  (4) bao-cao
# ══════════════════════════════════════════════════════════════════════════

def _p(v, n=3):
    return "—" if v is None else f"{v:.{n}f}".replace(".", ",")


def bao_cao(ra: pathlib.Path) -> int:
    kho = {d["ma"]: d for d in _json(ra / "kho.json")}
    gi = _json(ra / "gioi.json")["ket_qua"]

    # ── A. Hiệu chỉnh trên 20 preset engine ────────────────────────────────
    print("\n## A. Hieu chinh — 20 preset engine (nhan cua engine)\n")
    print("| preset | nhan | do | do_tin | ti_le_cs_nam | F0 | dung |")
    print("|---|---|---|---|---|---|---|")
    dung = sai = 0
    thap_dung = 1.0
    for ma, d in sorted(kho.items()):
        if d["loai"] != "preset":
            continue
        k = gi.get(ma) or {}
        ok = k.get("nhan") == d["gioi_nhan"]
        dung, sai = dung + ok, sai + (not ok)
        if ok:
            thap_dung = min(thap_dung, k.get("do_tin", 1.0))
        print(f"| {d['ten']} | {d['gioi_nhan']} | {k.get('nhan','—')} | "
              f"{_p(k.get('do_tin'))} | {_p(k.get('ti_le_cua_so_nam'),2)} | "
              f"{_p(k.get('f0_trung_vi'),1)} | {'OK' if ok else 'SAI'} |")
    print(f"\n**Do chinh xac: {dung}/{dung+sai}**  ·  "
          f"do_tin THAP NHAT trong cac lan dung: **{_p(thap_dung)}**\n")

    # ── B. 25 giọng kho chung ──────────────────────────────────────────────
    print("\n## B. De xuat `gioi` — 25 giong kho chung\n")
    print("| giong | lan | khai (xuat xu) | do (tieng sinh) | do_tin | "
          "do (clip goc) | do_tin goc | F0 sinh | khop |")
    print("|---|---|---|---|---|---|---|---|---|")
    de_xuat: dict = {}
    for v in sorted(_manifest_kho_chung(), key=lambda x: (x["ngon_ngu"], x["ten_hien_thi"])):
        pid = v["public_id"]
        lan = v["ngon_ngu"]
        ma = f"chung__{pid}__" + ("vi_a" if lan == "vi" else "en_a")
        k = gi.get(ma) or {}
        kg = gi.get(f"goc__{pid}") or {}
        khai = gioi_khai(v["ten_tep_cu"], v["ten_hien_thi"])
        khop = (k.get("nhan") == kg.get("nhan") == khai)
        de_xuat[pid] = {"ten": v["ten_hien_thi"], "lan": lan, "khai": khai,
                        "do_sinh": k.get("nhan"), "do_tin_sinh": k.get("do_tin"),
                        "do_goc": kg.get("nhan"), "do_tin_goc": kg.get("do_tin"),
                        "f0_sinh": k.get("f0_trung_vi"),
                        "f0_goc": kg.get("f0_trung_vi"),
                        "ti_le_cs_nam_goc": kg.get("ti_le_cua_so_nam"),
                        "khop": khop}
        print(f"| {v['ten_hien_thi']} | {lan} | {khai} | {k.get('nhan','—')} | "
              f"{_p(k.get('do_tin'))} | {kg.get('nhan','—')} | "
              f"{_p(kg.get('do_tin'))} | {_p(k.get('f0_trung_vi'),1)} | "
              f"{'OK' if khop else 'LECH'} |")
    _json(ra / "de_xuat_gioi.json", de_xuat)
    print(f"\n(de xuat co may: {ra / 'de_xuat_gioi.json'})\n")

    # ── C. Xếp hạng 17 giọng `en` ──────────────────────────────────────────
    p_cham = ra / "cham_en.json"
    if not p_cham.is_file():
        print("\n(chua co cham_en.json — bo qua muc C)\n")
        return 0
    c = _json(p_cham)
    g, s, m, to = (c["giong"]["ket_qua"], c["squim"]["ket_qua"],
                   c["mos"]["ket_qua"], c["do_to"])
    theo_giong: dict = {}
    for ma, d in kho.items():
        if d["ngon_ngu"] != "en":
            continue
        theo_giong.setdefault(d["public_id"], {"ten": d["ten"], "ban": []})
        theo_giong[d["public_id"]]["ban"].append(ma)

    print("\n## C. Xep hang 17 giong `en` — cung kich ban, hai ban\n")
    print("| giong | WER | PESQ | PESQ min cs | SI-SDR | Distill-MOS | "
          "DNSMOS OVRL | SIG | tu/phut | LUFS-I | TP dBFS |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    def _tb(bans, lay):
        """Trung binh tren CAC BAN kich ban cua mot giong; `None` khi khong co."""
        xs = [x for x in (lay(b) for b in bans) if x is not None]
        return statistics.fmean(xs) if xs else None

    def _tu_phut(b):
        giay = (s.get(b) or {}).get("giay") or 0.0
        if giay <= 0:
            return None
        return 60.0 * len(KICH_BAN[kho[b]["kich_ban"]][1].split()) / giay

    hang = []
    for pid, v in theo_giong.items():
        bans = v["ban"]
        hang.append({
            "pid": pid, "ten": v["ten"], "so_ban": len(bans),
            "wer": _tb(bans, lambda b: (g.get(b) or {}).get("wer")),
            "pesq": _tb(bans, lambda b: (s.get(b) or {}).get("pesq")),
            "pesq_cs": _tb(bans, lambda b: (s.get(b) or {}).get("pesq_min_cua_so")),
            "si_sdr": _tb(bans, lambda b: (s.get(b) or {}).get("si_sdr")),
            "stoi": _tb(bans, lambda b: (s.get(b) or {}).get("stoi")),
            "distill_mos": _tb(bans, lambda b: (m.get(b) or {}).get("distill_mos")),
            "dnsmos_ovrl": _tb(bans, lambda b: (m.get(b) or {}).get("dnsmos_ovrl")),
            "dnsmos_sig": _tb(bans, lambda b: (m.get(b) or {}).get("dnsmos_sig")),
            "dnsmos_bak": _tb(bans, lambda b: (m.get(b) or {}).get("dnsmos_bak")),
            "tu_phut": _tb(bans, _tu_phut),
            "lufs_i": _tb(bans, lambda b: (to.get(b) or {}).get("lufs_i")),
            "lra": _tb(bans, lambda b: (to.get(b) or {}).get("lra")),
            "true_peak": _tb(bans, lambda b: (to.get(b) or {}).get("true_peak_dbfs")),
        })
    hang.sort(key=lambda h: -(h["distill_mos"] or 0))
    for h in hang:
        print(f"| {h['ten']} | {_p(h['wer'])} | {_p(h['pesq'])} | "
              f"{_p(h['pesq_cs'])} | {_p(h['si_sdr'],2)} | "
              f"**{_p(h['distill_mos'],2)}** | {_p(h['dnsmos_ovrl'],2)} | "
              f"{_p(h['dnsmos_sig'],2)} | {_p(h['tu_phut'],1)} | "
              f"{_p(h['lufs_i'],1)} | {_p(h['true_peak'],1)} |")
    _json(ra / "xep_hang_en.json", hang)

    # ── Đối chứng: thang đo lộ ra trên CHÍNH kho này ───────────────────────
    dc = {k: v for k, v in m.items() if k.startswith("doi_chung__")}
    if dc:
        print("\n### Đối chứng — cùng một đoạn tiếng, ba biến dạng\n")
        print("| bản | WER | PESQ | Distill-MOS | DNSMOS OVRL |")
        print("|---|---|---|---|---|")
        goc_ma = MA_DOI_CHUNG
        for ten, ma in [("gốc (chưa biến dạng)", goc_ma),
                        *[(k.replace("doi_chung__", ""), k) for k in dc]]:
            print(f"| {ten} | {_p((g.get(ma) or {}).get('wer'))} | "
                  f"{_p((s.get(ma) or {}).get('pesq'))} | "
                  f"{_p((m.get(ma) or {}).get('distill_mos'), 2)} | "
                  f"{_p((m.get(ma) or {}).get('dnsmos_ovrl'), 2)} |")
    print(f"\n(xep hang co may: {ra / 'xep_hang_en.json'})\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("buoc", choices=["sinh", "do-gioi", "cham-en", "bao-cao"])
    ap.add_argument("--ra", default=RA_MAC_DINH)
    ap.add_argument("--chi", default="", help="sinh: chi lan nay (vi|en|preset)")
    ap.add_argument("--so", type=int, default=0, help="sinh: chi doc N luot dau (thu duong)")
    a = ap.parse_args()
    ra = pathlib.Path(a.ra)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if a.buoc == "sinh":
        return sinh(ra, a.chi, a.so)
    if a.buoc == "do-gioi":
        return do_gioi(ra)
    if a.buoc == "cham-en":
        return cham_en(ra)
    return bao_cao(ra)


if __name__ == "__main__":
    sys.exit(main())
