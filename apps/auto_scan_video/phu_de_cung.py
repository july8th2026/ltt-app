"""Hardsub (phu de dot vao hinh) -> dong thoi gian — phan LOGIC, khong model.

Dau vao la ket qua THO cua bo OCR (`apps/asv_gpu/do_luong/ocr_khung.py`, chay
RapidOCR trong venv do luong): moi khung mot danh sach dong
`{"hop": [x0, y0, x1, y1], "chu": str, "diem": float}`. Tep nay chi lam hinh
hoc + thoi gian tren danh sach do, nen test duoc khong can model.

    khung_do (full-frame, thua)  --phat_hien_dai-->  dai phu de | None
    khung_dai (cat dai, day)     --dung_dong_thoi_gian-->  segments

## Vi sao nhan dien dai bang ON DINH + DOI CHU, khong bang vi tri co dinh

Bon clip Douyin nghiem thu dat phu de o ba do cao khac nhau (y ~ 0,78-0,95 H) va
co chu KHAC phu de o cung vung: HUD game (`剩余97`, la ban `195 210 西南`, dong
bao ha guc), logo kenh goc tren (`中国 一味`), watermark giua hinh (`千奇百战`),
ma tran dau o day khung. Phu de la cum dong duy nhat thoa CA BA:

  1. can giua ngang (lech tam <= `LECH_TAM_TOI_DA` * W);
  2. xuat hien o nhieu khung (>= `TI_LE_KHUNG_TOI_THIEU`);
  3. chu DOI qua cac khung (so chuoi khac nhau >= `SO_CHU_KHAC_TOI_THIEU`,
     chuoi pho bien nhat chiem < `TI_LE_TINH_TOI_DA`) — logo/watermark/HUD
     tinh bi loai o day.

La ban game cung can giua va cung doi chu — nen them dieu kien 4: chu cao >=
`CAO_CHU_TOI_THIEU` * H (HUD ~15 px, phu de 33-50 px o 576p); giua cac cum dat,
chon cum co `so khung * chieu cao chu` lon nhat. So do cua moi nguong duoi day
ghi trong `docs/auto_scan_video_final/L_OCR.md`.

⛔ Khong phai do "chat luong": day la hinh hoc + dem (loai A). Chat luong doc chu
   la cua PP-OCRv6 (da benchmark), khong phai cua tep nay.
"""
from __future__ import annotations

from collections import Counter
from statistics import median

from rapidfuzz import fuzz

#: Phien ban LOGIC tep nay. Di vao `giai_doan_chep_loi.PHIEN_BAN_MA` qua
#: `nguon_loi.PHIEN_BAN_DINH_TUYEN`.
PHIEN_BAN = 1

#: Diem nhan dang toi thieu cua mot dong (0..1, diem CTC cua PP-OCR). RapidOCR
#: mac dinh `text_score: 0.5`; phu de that tren 4 clip co diem 0,95-1,00.
DIEM_TOI_THIEU = 0.80
LECH_TAM_TOI_DA = 0.15
TI_LE_KHUNG_TOI_THIEU = 0.15
SO_CHU_KHAC_TOI_THIEU = 3
TI_LE_TINH_TOI_DA = 0.5
#: Chu phu de cao >= 4% H. Do tren 4 clip 576p: phu de 33-50 px (5,7-8,7%),
#: HUD/la ban/killfeed 12-18 px (2,1-3,1%). La ban game can giua VA doi chu,
#: nen chi chieu cao tach duoc no khoi phu de khi video khong co phu de.
CAO_CHU_TOI_THIEU = 0.04
#: Hai dong cung cao do neu tam lech nhau <= 4% H.
GOP_CAO_DO = 0.04
#: Trong dai: bo dong thap hon 60% chieu cao chu trung vi cua dai (dong bao
#: ha guc cua game chen vao dai phu de o v3).
TI_LE_CAO_TOI_THIEU = 0.5
#: Hop khac trong khung phai cao >= 80% hang chinh moi la chu phu de.
CO_CHU_CUNG_HANG = 0.8
#: Hai khung lien tiep la CUNG mot dong phu de neu giong nhau >= 80 (rapidfuzz
#: ratio): OCR doc sai 1 chu tren 10 van la cung dong.
GIONG_TOI_THIEU = 80.0
#: Mot dong phai hien >= 2 khung lien tiep: dong 1 khung la khung chuyen canh
#: (chu mo dan) — doc sai nhieu nhat.
SO_KHUNG_TOI_THIEU = 2
#: Chuoi hien trong dai qua 30% thoi luong VA qua 10 s = watermark trong dai.
#: (Mot dong phu de that dai 1-4 s tren 4 clip; clip ngan khong bi xoa oan.)
TI_LE_WATERMARK = 0.30
WATERMARK_TOI_THIEU_S = 10.0


def _tam(hop):
    x0, y0, x1, y1 = hop
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0, max(1.0, y1 - y0)


def _chuan(chu: str) -> str:
    return "".join(str(chu or "").split())


def phat_hien_dai(khung: list[dict], *, rong: int, cao: int) -> dict | None:
    """Tim dai phu de tu cac khung do full-frame. None = khong co hardsub.

    Tra ve `{"y0","y1","cao_chu","ti_le_khung","so_chu_khac","tam_y"}` (pixel
    cua khung goc).
    """
    if not khung or rong <= 0 or cao <= 0:
        return None
    ung_vien = []           # (tam_y, cao_chu, chi_so_khung, chu, y0, y1)
    for i, k in enumerate(khung):
        for d in k.get("dong") or ():
            if float(d.get("diem") or 0) < DIEM_TOI_THIEU:
                continue
            cx, cy, h = _tam(d["hop"])
            if abs(cx - rong / 2.0) > LECH_TAM_TOI_DA * rong:
                continue
            chu = _chuan(str(d.get("chu") or ""))
            if chu:
                ung_vien.append((cy, h, i, chu, d["hop"][1], d["hop"][3]))
    if not ung_vien:
        return None

    # Gom theo cao do: tham lam tren danh sach da sap.
    ung_vien.sort()
    cum: list[list] = []
    for u in ung_vien:
        if cum and u[0] - median(x[0] for x in cum[-1]) <= GOP_CAO_DO * cao:
            cum[-1].append(u)
        else:
            cum.append([u])

    tot, diem_tot = None, 0.0
    n = len(khung)
    for c in cum:
        khung_co = {u[2] for u in c}
        ti_le = len(khung_co) / n
        dem = Counter(u[3] for u in c)
        tinh = dem.most_common(1)[0][1] / len(c)
        if (ti_le < TI_LE_KHUNG_TOI_THIEU or len(dem) < SO_CHU_KHAC_TOI_THIEU
                or tinh >= TI_LE_TINH_TOI_DA):
            continue
        h = median(u[1] for u in c)
        if h < CAO_CHU_TOI_THIEU * cao:
            continue
        diem = len(khung_co) * h
        if diem > diem_tot:
            diem_tot = diem
            y0 = min(u[4] for u in c)
            y1 = max(u[5] for u in c)
            tot = {"y0": max(0, int(y0 - 0.5 * h)),
                   "y1": min(cao, int(y1 + 0.5 * h)),
                   "cao_chu": float(h), "ti_le_khung": round(ti_le, 3),
                   "so_chu_khac": len(dem),
                   "tam_y": round(median(u[0] for u in c) / cao, 3)}
    return tot


def chu_trong_khung(dong: list[dict], *, cao_chu: float,
                    rong: float = 0.0) -> tuple[str, float]:
    """Cac dong OCR trong MOT khung cat dai -> (chu, diem). Rong neu khong co.

    🔑 Chon theo HANG CHINH, khong theo nguong cao tuyet doi: hang chinh = hop
       lon nhat (cao x rong) can giua. Giu hop cung hang (phu de bi OCR tach
       doi) va hang khac CUNG CO CHU (phu de hai hang). Do tren v3: dong bao
       ha guc cua game (cao 21 px) va nut `自动` (19 px) nam TRONG dai phu de
       (34-37 px) — mot nguong tuyet doi 60% cao chu giu ca hai va ghep chung
       vao loi thoai.
    """
    ung = []
    for d in dong or ():
        if float(d.get("diem") or 0) < DIEM_TOI_THIEU:
            continue
        cx, cy, h = _tam(d["hop"])
        chu = _chuan(str(d.get("chu") or ""))
        if chu and h >= TI_LE_CAO_TOI_THIEU * cao_chu:
            ung.append((cx, cy, h, d["hop"], chu, float(d["diem"])))
    if not ung:
        return "", 0.0
    giua = [u for u in ung if not rong or abs(u[0] - rong / 2.0) <= LECH_TAM_TOI_DA * rong]
    if not giua:
        return "", 0.0
    chinh = max(giua, key=lambda u: u[2] * (u[3][2] - u[3][0]))
    hc = chinh[2]
    giu = []
    for u in ung:
        if u[2] < CO_CHU_CUNG_HANG * hc:
            continue                          # chu nho hon han: UI/killfeed
        cung_hang = abs(u[1] - chinh[1]) <= 0.5 * hc
        if cung_hang or (not rong or abs(u[0] - rong / 2.0) <= LECH_TAM_TOI_DA * rong):
            giu.append((round(u[1] / hc), u[3][0], u[4], u[5]))
    giu.sort()
    chu = "".join(g[2] for g in giu)
    diem = sum(g[3] * len(g[2]) for g in giu) / max(1, len(chu))
    return chu, diem


def dung_dong_thoi_gian(khung: list[dict], *, cao_chu: float, fps: float,
                        thoi_luong: float, rong: float = 0.0) -> list[dict]:
    """Khung cat dai (co `t`) -> segments `{start,end,text,words,confidence}`.

    Gop khung lien tiep giong nhau; mot khung trong/khac xen giua (OCR truot
    mot khung) KHONG cat dong neu khung sau lai giong. Chu dai dien cua dong =
    bien the xuat hien nhieu nhat (hoa: diem cao nhat).
    """
    buoc = 1.0 / float(fps)
    doc = []
    for k in sorted(khung, key=lambda x: float(x["t"])):
        chu, diem = chu_trong_khung(k.get("dong") or [], cao_chu=cao_chu, rong=rong)
        doc.append((float(k["t"]), chu, diem))

    dong: list[dict] = []
    hien = None
    lo = 0                                   # so khung lien tiep khong khop
    for t, chu, diem in doc:
        if hien is not None and chu and fuzz.ratio(chu, hien["mau"]) >= GIONG_TOI_THIEU:
            hien["cuoi"] = t
            hien["bien_the"].append((chu, diem))
            lo = 0
            continue
        if hien is not None:
            lo += 1
            if lo <= 1 and not chu:
                continue                     # truot mot khung trong
            dong.append(hien)
            hien = None
            lo = 0
        if chu:
            hien = {"dau": t, "cuoi": t, "mau": chu, "bien_the": [(chu, diem)]}
    if hien is not None:
        dong.append(hien)

    def dai_dien(d):
        dem = Counter(c for c, _ in d["bien_the"])
        return max(dem, key=lambda c: (dem[c], max(s for cc, s in d["bien_the"] if cc == c)))

    # Lop phu chen ngang (dong bao cua game noi DUOI dong phu de o v3): cung dong
    # phu de hien thanh `X` roi `X+lop phu`. Hai nhom LIEN KE ma chu nhom nay
    # CHUA chu nhom kia la MOT dong — giu chu NGAN (lop phu chi them chu).
    gop: list[dict] = []
    for d in dong:
        if gop and d["dau"] - gop[-1]["cuoi"] <= 1.5 * buoc:
            a, b = dai_dien(gop[-1]), dai_dien(d)
            if a in b or b in a:
                ngan = a if len(a) <= len(b) else b
                gop[-1]["cuoi"] = d["cuoi"]
                gop[-1]["bien_the"] = [(ngan, sc) for _, sc in gop[-1]["bien_the"] + d["bien_the"]]
                continue
        gop.append(d)

    ra = []
    for d in gop:
        if len(d["bien_the"]) < SO_KHUNG_TOI_THIEU:
            continue
        chu = dai_dien(d)
        tin = sum(s for _, s in d["bien_the"]) / len(d["bien_the"])
        ra.append({"start": round(d["dau"], 3),
                   "end": round(min(thoi_luong or 1e9, d["cuoi"] + buoc), 3),
                   "text": chu, "words": [],
                   "confidence": round(tin, 4),
                   "so_khung": len(d["bien_the"])})

    # Watermark trong dai: cung mot chuoi phu qua TI_LE_WATERMARK thoi luong.
    if thoi_luong:
        phu = Counter()
        for s in ra:
            phu[s["text"]] += s["end"] - s["start"]
        nguong = max(TI_LE_WATERMARK * thoi_luong, WATERMARK_TOI_THIEU_S)
        bo = {c for c, v in phu.items() if v > nguong}
        ra = [s for s in ra if s["text"] not in bo]

    # Hop dong ban ghi cam chong thoi gian: khung lam tron co the de 1 buoc.
    for a, b in zip(ra, ra[1:]):
        if a["end"] > b["start"]:
            a["end"] = b["start"]
    return [s for s in ra if s["end"] > s["start"]]


def ti_le_chu_han(chu: str) -> float:
    """Ti le ky tu CJK trong chuoi (bo khoang trang, so, dau)."""
    chu_cai = [c for c in chu if c.isalpha()]
    if not chu_cai:
        return 0.0
    han = sum(1 for c in chu_cai if "一" <= c <= "鿿" or "㐀" <= c <= "䶿")
    return han / len(chu_cai)
