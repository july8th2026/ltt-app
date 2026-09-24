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
CAM = [("光子", "来把枪啊光子!", ["Quang Tử", "Quang Tu"],
        "vi.wikipedia KHONG co bai -> ⛔ khong co dap an duong")]


def _dich(cau_list: list[str]) -> dict:
    """Dich qua DUNG duong san pham. ⛔ Khong ghim gi tai cho goi."""
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


def chay() -> dict:
    from apps.auto_scan_video import ai, van_ban

    cau = [c for _, c, *_ in CA] + [c for _, c, *_ in CAM]
    t0 = time.time()
    ra = _dich(cau)

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
    return {
        "phien_ban_loi_nhac": van_ban.PHIEN_BAN_LOI_NHAC,
        "model": ai.model_cho(ai.DICH_THUAT),
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
    a = ap.parse_args(argv)
    kq = chay()
    if a.ra:
        d = Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"ten_rieng_v{kq['phien_ban_loi_nhac']}.json").write_text(
            json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"loi nhac v{kq['phien_ban_loi_nhac']} · {kq['model']} · {kq['giay']} s")
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
