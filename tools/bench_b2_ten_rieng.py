"""bench_b2_ten_rieng.py — tap kiem TEN RIENG, dap an TRA DUOC. ⛔ Khong tu dat.

    python tools/bench_b2_ten_rieng.py --ra <thu muc>

## ⭐ Vi sao tep nay ton tai

Ba luot lien trong mot ngay, luot nao cung **sua mot cho, hong mot cho**:

    v2  sua 光子, hong 李宗盛      (vi du KHONG DAU trong loi nhac)
    v3  sua 李宗盛, van sai 光子
    v4  sua 李宗盛, hong 首尔       (cat theo LOAI THUC THE, sai truc)

⛔ Goc **khong phai** "sua qua nhieu". Goc la **tap kiem 5 ten qua nho de thay
hoi quy TRUOC khi giao**. ⇒ Mo rong tap kiem, ⛔ dung sua them loi nhac.

## ⭐ Va ta KHONG can bo cham cho viec nay

Chi can nhung ten ma **dap an khong ai cai**. Dap an duoi day **tra tu nguon**:
lien ket lien-ngon-ngu `zh.wikipedia -> vi.wikipedia` (doc 24/09 qua API
`prop=langlinks&lllang=vi`) — ⛔ **khong phai ta tu dat**.

⚠️ **Ca nao tra khong ra dap an chac thi BI LOAI khoi tap kiem**, ⛔ khong tu dat
   dap an roi tu cham — dung luat da ap cho Unihan. `光子` bi loai khoi phan cham
   DUONG, chi giu mot tieu chi AM (xem `CAM`).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                               # noqa: BLE001
    pass

#: ⭐ **Dap an tra tu nguon**, ⛔ khong ai trong du an nay dat ra.
#:
#: `zh.wikipedia.org/w/api.php?action=query&prop=langlinks&lllang=vi` — ten bai
#: tuong ung ben vi.wikipedia, doc 24/09/2026.
#:
#: `張伟`/`小美`: ⛔ khong co bai wiki (ten thuong, nhan vat) ⇒ dap an la **chinh
#: cau chu du an ra luat** (`张伟 -> Trương Vĩ`) va suy ra cho `小美` theo dung
#: nhanh 5.2. Nguon duoc ghi ro o cot `nguon`.
CA = [
    # (han, cau mang ten, dap an, nguon, loai)
    ("首尔", "老板在首尔卖了五百份。", "Seoul", "wiki zh->vi", "quen·noi"),
    ("东京", "他昨天去了东京。", "Tokyo", "wiki zh->vi (东京都)", "quen·noi"),
    ("北京", "我们明天到北京。", "Bắc Kinh", "wiki zh->vi", "quen·noi"),
    ("上海", "上海的夏天很热。", "Thượng Hải", "wiki zh->vi", "quen·noi"),
    ("广州", "广州有很多美食。", "Quảng Châu", "wiki zh->vi", "quen·noi"),
    ("重庆", "重庆的火锅最有名。", "Trùng Khánh", "wiki zh->vi", "quen·noi"),
    ("纽约", "他在纽约住了十年。", "New York", "wiki zh->vi (Thành phố New York)",
     "quen·noi"),
    ("李宗盛", "这首歌是李宗盛写的。", "Lý Tông Thịnh", "wiki zh->vi", "quen·nguoi"),
    ("李小龙", "李小龙是一位武术家。", "Lý Tiểu Long", "wiki zh->vi", "quen·nguoi"),
    ("腾讯", "这个游戏是腾讯做的。", "Tencent", "wiki zh->vi", "quen·to_chuc"),
    ("华为", "他买了一部华为手机。", "Huawei", "wiki zh->vi", "quen·to_chuc"),
    ("张伟", "张伟今天没来上班。", "Trương Vĩ",
     "chinh cau chu du an ra luat", "khong_quen·nguoi"),
    ("小美", "小美在山腰搭帐篷。", "Tiểu Mỹ",
     "suy tu nhanh 5.2 (cung luat voi 张伟)", "khong_quen·nguoi"),
]

#: ⛔ Ca **khong tra ra dap an chac** ⇒ ⛔ khong cham DUNG/SAI, chi cham mot tieu
#: chi **AM**: no khong duoc ra mot phien am Han-Viet.
#: `光子` la xuong game (`B2_DICH.md` §4g); vi.wikipedia ⛔ khong co bai
#: `光子工作室群` ⇒ ⛔ khong co dap an duong de cham.
#: ⛔ Lo NHO hon co san pham — xem ghi chu o `_dich_duong_song`.
LO_NHO = 4

#: 🔑 **GHIM nhiet do, va phai noi ra vi sao.** Duong SONG ⛔ khong truyen
#: `temperature` ⇒ cong may B ap `1.0`, va o cau hinh do `ltt-3.5` hong **64 %**
#: so lo (`B2_DICH.md` §7.5). Do ten rieng duoi mot nguon nhieu nhu vay thi
#: chenh lech truoc/sau cua LOI NHAC bi chon mat.
#: ⇒ Ghim de lam loi nhac thanh **bien duy nhat**. ⚠️ Cai gia phai khai: day
#: ⛔ **khong** phai cau hinh khach dang chay.
NHIET_DO = 0.2

#: 🔴 So doan bi model BO trong tung lo — mot KET QUA, ⛔ khong phai tro ngai.
_BO_DOAN: list[dict] = []

CAM = [("光子", "来把枪啊光子!", ["Quang Tử", "Quang Tu"],
        "vi.wikipedia KHONG co bai -> ⛔ khong co dap an duong")]


def _dich_duong_song(cau_list: list[str], *, ghim_model: str = "") -> dict:
    """Qua **LOI NHAC CUA DUONG SONG** (`long_tieng.loi_nhac` + `CHUYEN_LOI_THOAI`).

    🔴 Day moi la thu san pham dung. `dich_thuat` la **duong CHET**
       (`thi_hanh.py:121`; `ai.DICH_THUAT` chi xuat hien trong chinh no).

    ⚠️ `ghim_model`: thao tac song la `chuyen_loi_thoai` -> **qwen38-api**, ma
       `ltt-3.8` dang **NHUONG lan khac** (luat 24/09). ⇒ Ghim `ltt-3.5` de do
       duoc **hom nay**, va **KHAI THANG** rang day la
       *loi nhac DUONG SONG x ltt-3.5*, ⛔ **khong** phai to hop dang chay that.
    """
    import platform_core.db as dbmod
    from platform_core.llm import canonical, dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    doan = [{"ma": f"seg_{i:04d}", "chu": c, "bat": 0.0, "ket": 4.0}
            for i, c in enumerate(cau_list, start=1)]
    mid = canonical.ALIAS_SANG_ID.get(ghim_model or "", "")
    ban_do = ({p: mid for p in ai.THU_TU_PROVIDER} if mid
              else ai.ban_do_model(ai.CHUYEN_LOI_THOAI))
    # ⛔ Chia lo NHU SAN PHAM (`long_tieng.chia_lo`). Gui 14 doan mot lan thi
    #    phan hoi cut va `doc_chuyen` nem "Model khong tra ve bang doan" — mot
    #    trieu chung tro NHAM vao model trong khi loi o ben GOI.
    ra: dict = {}
    db = next(dbmod.get_session())
    try:
        # 🔴 **`moi_lo=LO_NHO` chu khong phai 12 (`long_tieng.DOAN_MOI_LO`).**
        #
        # ⚠️ **Ly do GOC cua dong nay DA BI BAC** (`B2_DICH.md` §7.5). No tung
        #    ghi: *"lo 12 ⇒ 3.5 tra ve 1/12 ⇒ 3.5 khong gánh noi luoc do o co lo
        #    san pham"*. Do lai voi `temperature` GHIM: cung model, cung lo 12,
        #    cung luoc do ⇒ **83/83 doan, 0 lo hong**. Thu phạm la duong song
        #    ⛔ **khong ghim `temperature`** (cong may B ap 1.0) — ⛔ khong phai
        #    co lo, ⛔ khong phai nang luc model.
        #
        # ⭐ Lo 4 GIU LAI, nhung vi mot ly do KHAC va phai noi ra: tep nay do
        #    **ten rieng**, va mot lo hong o day lam mat ca mot cum ca kiem. Lo
        #    nho ha ty le mat mau. ⛔ No ⛔ khong con la bang chung ve nang luc
        #    cua model.
        for lo in L.chia_lo(doan, moi_lo=LO_NHO):
            ra.update(_mot_lo(db, lo, doan, ban_do))
    finally:
        db.close()
    return ra


def _mot_lo(db, lo: list[dict], tat_ca: list[dict], ban_do: dict) -> dict:
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    msg = L.loi_nhac(lo, tat_ca=tat_ca, ngon_ngu_goc="zh",
                     dac_diem_giong={}, ngon_ngu_dich="vi")
    if True:
        # ⛔ PHAI xin tran token ra THEO TEN CUA. Bo qua no ⇒ mac dinh cua
        #    `dieu_phoi` cat phan hoi giua chung, va `doc_chuyen` nem
        #    "Model khong tra ve bang doan" — mot trieu chung tro NHAM vao model
        #    trong khi loi la o ben GOI. Do that: 2 doan chay tot, 14 doan chet.
        # ⛔ Tran/timeout lay tu `ngan_sach_cho` — duong song di qua
        #    `goi_tinh_tien`, va ham do doc bang do (`ai.py:774`) = 16 384,
        #    ⛔ khong phai 32 768 cua `tran_token_ra()`.
        _tran, _cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
        kq = dieu_phoi.goi(db, messages=msg,
                           thu_tu_provider=list(ai.THU_TU_PROVIDER),
                           model_theo_provider=ban_do, temperature=NHIET_DO,
                           max_tokens=_tran, timeout_s=float(_cho or 300.0))
    noi = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    goi = ai.doc_json(str(noi), ai.CHUYEN_LOI_THOAI)
    # 🔴 **GHI so doan BI BO, ⛔ dung nem.** `doc_chuyen` nem `ThieuDoan` — dung
    #    cho SAN PHAM (mot lo thieu doan la mot lo hong). Nhung o day ta dang
    #    **do chinh hien tuong do**, va nem thi mat luon ca phep do.
    # ⚠️ Ti le bo doan la mot KET QUA, khong phai mot tro ngai.
    tho = (goi or {}).get("doan")
    ma_lo = {d["ma"] for d in lo}
    # 🔴 **MOT MANG, khong phai mot bang khoa-theo-ma.** Dung ca ma docstring
    #    cua `long_tieng.loi_nhac` canh bao: *"Yeu cau tra ve JSON co khoa la MA
    #    DOAN, khong phai mot mang"* — vi vi tri ⛔ khong dung lam dinh danh
    #    duoc. Ghi ra la mot **vi pham luoc do**, ⛔ khong lang le ghep theo vi tri.
    vi_pham = ""
    if isinstance(tho, list):
        vi_pham = "doan = MANG (⛔ vi pham luoc do: phai la bang khoa theo ma)"
        tho = {}
    elif not isinstance(tho, dict):
        vi_pham = f"doan = {type(tho).__name__} (⛔ khong doc duoc)"
        tho = {}
    ra = {m: str((v or {}).get("chu") or "")
          for m, v in tho.items() if m in ma_lo and isinstance(v, dict)}
    _BO_DOAN.append({"lo": sorted(ma_lo), "nhan_duoc": sorted(ra),
                     "thieu": sorted(ma_lo - set(ra)),
                     **({"vi_pham_luoc_do": vi_pham} if vi_pham else {})})
    return ra


def _dich(cau_list: list[str]) -> dict:
    """⛔ DUONG CHET (`dich_thuat`). Giu de doi chieu, ⛔ khong phai duong san pham."""
    import platform_core.db as dbmod

    from apps.auto_scan_video import dich_thuat as D

    ban = {"ngon_ngu": "zh",
           "doan": [{"ma": f"seg_{i:04d}", "chu": c}
                    for i, c in enumerate(cau_list, start=1)]}
    db = next(dbmod.get_session())
    try:
        return D.dich_ban_ghi(db, ban)
    finally:
        db.close()


def chay(*, duong: str = "song", ghim_model: str = "ltt-3.5") -> dict:
    from apps.auto_scan_video import ai, van_ban

    cau = [c for _, c, *_ in CA] + [c for _, c, *_ in CAM]
    t0 = time.time()
    ra = (_dich_duong_song(cau, ghim_model=ghim_model) if duong == "song"
          else _dich(cau))

    ket = []
    for i, (han, _c, dap_an, nguon, loai) in enumerate(CA, start=1):
        vi = ra.get(f"seg_{i:04d}", "")
        ket.append({"han": han, "loai": loai, "dap_an": dap_an,
                    "nguon_dap_an": nguon, "ra": vi,
                    "dat": dap_an.lower() in vi.lower()})
    am = []
    for j, (han, _c, cam, vi_sao) in enumerate(CAM, start=len(CA) + 1):
        vi = ra.get(f"seg_{j:04d}", "")
        am.append({"han": han, "⛔ khong_duoc_ra": cam, "ly_do": vi_sao,
                   "ra": vi, "dat": not any(x.lower() in vi.lower() for x in cam)})
    dat = sum(1 for k in ket if k["dat"])
    thieu = sum(len(x["thieu"]) for x in _BO_DOAN)
    return {
        "🔴 bo_doan": {
            "tong_gui": sum(len(x["lo"]) for x in _BO_DOAN), "thieu": thieu,
            "moi_lo": LO_NHO, "co_lo_san_pham": 12,
            "so_lo_vi_pham_luoc_do": sum(1 for x in _BO_DOAN
                                         if x.get("vi_pham_luoc_do")),
            "⚠️": ("Loi nhac DUONG SONG x ltt-3.5 BO DOAN. Do that: lo 12 doan "
                  "-> tra ve 1/12. Tran token ra 32 768 nen ⛔ KHONG phai cut. "
                  "⇒ Con so nay thuoc ve cau hoi 3.5-vs-3.8 (§6.2): neu 3.5 "
                  "khong gánh noi luoc do 4 truong + `ke_ben` o co lo that thi "
                  "\"20x dat hon\" ⛔ khong con la mot lua chon tu do."),
            "chi_tiet": _BO_DOAN},
        "duong_chay": duong,
        "⚠️ duong_la_gi": ("LOI NHAC DUONG SONG (`long_tieng.loi_nhac` + "
                          "CHUYEN_LOI_THOAI)" if duong == "song"
                          else "⛔ DUONG CHET (`dich_thuat`) — khong ai goi"),
        "model_ghim": ghim_model if duong == "song" else "",
        "⚠️ model": ("⛔ GHIM ltt-3.5 vi 3.8 dang NHUONG lan khac; to hop CHAY "
                    "THAT la loi nhac nay x ltt-3.8" if duong == "song"
                    else ""),
        # 🔴 **Hang phai khop DUONG DANG DO.** Ban dau cho nay luon doc
        #    `PHIEN_BAN_LOI_NHAC_DICH` — hang cua duong CHET — ke ca khi
        #    `--duong song`. Ban ghi vi the dan nhan phien ban cua MOT loi nhac
        #    KHAC voi loi nhac vua chay. Dung ho N-21 (mot hang chi phoi nham
        #    loi nhac), lan nay o tang BAN GHI chu khong o tang cache.
        "phien_ban_loi_nhac": (van_ban.PHIEN_BAN_LOI_NHAC_LONG_TIENG
                               if duong == "song"
                               else van_ban.PHIEN_BAN_LOI_NHAC_DICH),
        "hang_phien_ban": ("van_ban.PHIEN_BAN_LOI_NHAC_LONG_TIENG"
                           if duong == "song"
                           else "van_ban.PHIEN_BAN_LOI_NHAC_DICH"),
        "nhiet_do": NHIET_DO,
        "model_thao_tac_song": ai.model_cho(ai.CHUYEN_LOI_THOAI),
        "giay": round(time.time() - t0, 1),
        "duong": {"dat": dat, "tong": len(ket), "chi_tiet": ket},
        "am": {"dat": sum(1 for a in am if a["dat"]), "tong": len(am),
               "chi_tiet": am},
        "⚠️": "Dap an TRA TU NGUON (wiki zh->vi, doc 24/09). Ca khong tra ra "
              "dap an chac ⇒ LOAI khoi phan cham duong, chi giu tieu chi AM.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ra", default="")
    ap.add_argument("--duong", choices=("song", "chet"), default="song")
    ap.add_argument("--ghim", default="ltt-3.5")
    # ⭐ `--lan` — do ten rieng la mot phep do NHIEU LUOT. §7.1 da do 8/13 roi
    #    9/13 tren CUNG cau hinh; mot luot don ⛔ khong tach duoc "loi nhac tot
    #    len" khoi "hom nay gap may". Ban ghi phai mang so lan de khong de len nhau.
    ap.add_argument("--lan", type=int, default=1)
    a = ap.parse_args(argv)
    kq = chay(duong=a.duong, ghim_model=a.ghim)
    if a.ra:
        d = Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"ten_rieng_{kq['duong_chay']}_v{kq['phien_ban_loi_nhac']}"
              f"_lan{a.lan}.json").write_text(
            json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{kq['duong_chay'].upper()}] {kq['⚠️ duong_la_gi']}")
    print(f"  loi nhac v{kq['phien_ban_loi_nhac']} · model ghim "
          f"{kq['model_ghim'] or '(khong)'} · {kq['giay']} s")
    print(f"  DUONG: {kq['duong']['dat']}/{kq['duong']['tong']}")
    for k in kq["duong"]["chi_tiet"]:
        print(f"    {'✅' if k['dat'] else '⛔'} {k['han']:6} [{k['loai']:18}] "
              f"mong {k['dap_an']!r} -> {k['ra'][:56]!r}")
    print(f"  AM (khong duoc ra): {kq['am']['dat']}/{kq['am']['tong']}")
    for k in kq["am"]["chi_tiet"]:
        print(f"    {'✅' if k['dat'] else '⛔'} {k['han']:6} -> {k['ra'][:56]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
