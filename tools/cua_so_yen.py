"""cua_so_yen.py — mot khoa cap may cho cac luot do dat tien.

    python tools/cua_so_yen.py trang-thai     # ai dang giu, tu bao gio
    python tools/cua_so_yen.py nha --ep --tai-nguyen cpu_nhieu
                                              # go MOT khoa treo
    # ⛔ `nha --ep` khong kem `--tai-nguyen` go TAT CA khoa tren may,
    #    ke ca cua mot luot gate dang chay.

## Vi sao no ton tai

Kho nay thuong xuyen co **ba phien Claude cung ghi mot cay**. Mot luot
`gate.py` day du mat 5-6 phut va pha `bo test` lay `-n auto` = **moi loi**.
Hai luot cung luc tren 20 loi thi moi luot duoc ~7 loi: tong thoi gian gan y
het chay lan luot, nhung tra them gap doi bo nho, gap doi thu muc tam, va gap
doi kha nang do sai.

⇒ Song song hoa mot thu **da bao hoa loi** khong phai toi uu, chi la chia nho
  cung mot chiec banh. Nen cho xep hang, dung cho tranh.

⭐ Va cai xep hang mua duoc thu quan trong hon toc do: mot **cua so yen**. Phien
   dang cho biet chinh xac ai dang do va tu bao gio, nen no biet nen doi hay nen
   di lam viec khac — thay vi nhan tin hoi nhau roi doan.

## Vi sao KHONG dat khoa trong cay kho

`gate._anh_chup_cay()` quet `tools/` de phat hien cay doi giua chung. Mot tep
khoa nam trong do se **tu lam ban phep do cua chinh no**: gate ghi khoa luc bat
dau, thay `tools/...` doi luc ket thuc, roi bao "cay da doi". Cung lop loi voi
"gate tu nhieu vao phep do" da ghi trong CLAUDE.md.

⛔ KHONG dung `os.kill(pid, 0)` de do tien trinh con song tren Windows. Python
   tren Windows dich moi tin hieu khac `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` thanh
   `TerminateProcess` — tuc phep "do xem con song khong" se **giet** dung cai
   tien trinh no dang hoi. Dung `OpenProcess` qua ctypes.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

#: Ngoai cay kho — xem ghi chu dau tep.
TEP_KHOA = Path(tempfile.gettempdir()) / "ltt_cua_so_yen.json"

#: Tai nguyen mac dinh. Giu DUNG ten tep cu, co ly do: mot luot `gate.py` ban
#: cu dang chay van phai thay khoa cua ban moi va nguoc lai. Doi ten o day la
#: mo mot cua so trong do hai ban cung tuong minh dang doc quyen.
MAC_DINH = "cpu_nhieu"

#: Tai nguyen ma chen qua han se cho KET QUA SAI (khong chi cham): mot CSDL test dung
#: chung. Qua `cho_toi_da_s` thi CHO TIEP thay vi chen — khoa treo van tu doat.
KHONG_DUOC_CHEN = frozenset({"postgres_test"})


def _tep(tai_nguyen: str) -> Path:
    """Moi tai nguyen MOT tep khoa rieng.

    🔴 Mot tep cho moi tai nguyen chu khong mot tep chung chua nhieu muc — vi
       `O_EXCL` moi la thu lam phep chiem khoa dung. Mot tep chung bat buoc
       phai doc-sua-ghi, va cua so giua doc va ghi chinh la luc hai tien trinh
       cung tuong minh thang.
    """
    if tai_nguyen == MAC_DINH:
        return TEP_KHOA
    an_toan = "".join(c if c.isalnum() or c in "_-" else "_" for c in tai_nguyen)
    return Path(tempfile.gettempdir()) / f"ltt_khoa_{an_toan}.json"

#: Khoa gia hon nguong nay coi nhu treo, du tien trinh con song. Mot luot gate
#: day du mat ~6 phut; 2 gio la rong rai gap 20 lan, nen cham nguong nay nghia
#: la co gi do that su hong chu khong phai "dang chay lau".
TUOI_TOI_DA_S = 7200

#: Nhip in lai dong "dang doi" khi xep hang. Im lang qua thi nguoi dung tuong treo.
NHIP_IN_S = 15

#: Giu lau BAT THUONG — canh bao, KHONG doat. Luat 23/09 (CLAUDE.md muc ⭐ Chay
#: agent): khoa bao DUNG lenh tinh, nha ngay khi tinh xong.
#:
#: ⛔ Khac han `TUOI_TOI_DA_S`: cai kia tra loi "co coi nhu treo de DOAT khong"
#:    (2 gio). Mot luot giu 40 phut thi CHUA treo — no van dung luat cu ma van
#:    lam ca may dung. Khong co nguong nay thi viec giu thua khong loi ra o dau
#:    ca, va luat chi la giao uoc: phai co thu DEM no.
#:
#: 30 phut: mot luot gate day du ~6 phut, mot bo test app ~5-10 phut; qua 30
#: phut thi hoac lenh dang CHO (sai luat), hoac no qua lon va phai chia nho.
GIU_LAU_S = 1800


def _con_song(pid: int) -> bool:
    """PID con song khong. Khong bao gio dung `os.kill` — xem dau tep."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        # ⚠️ Mo duoc handle KHONG du de ket luan con song: mot tien trinh da
        #    thoat van mo duoc handle chung nao con ai giu tham chieu toi no.
        #    Phai hoi ma thoat — `STILL_ACTIVE` moi la dang chay.
        ma = ctypes.c_ulong()
        if k32.GetExitCodeProcess(h, ctypes.byref(ma)):
            return ma.value == STILL_ACTIVE
        return True
    finally:
        k32.CloseHandle(h)


def _doc(tai_nguyen: str = MAC_DINH) -> dict | None:
    try:
        return json.loads(_tep(tai_nguyen).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _treo(ban_ghi: dict) -> str:
    """Khoa co dang treo khong. Tra LY DO, hoac chuoi rong neu con hieu luc."""
    pid = int(ban_ghi.get("pid") or 0)
    tuoi = time.time() - float(ban_ghi.get("bat_dau_epoch") or 0)
    if not _con_song(pid):
        return f"tien trinh {pid} khong con chay"
    if tuoi > TUOI_TOI_DA_S:
        return f"giu qua lau ({tuoi / 3600:.1f} gio)"
    return ""


def _canh_bao_giu_lau(ban_ghi: dict) -> str:
    """Khoa dang bi giu qua lau khong. Tra CAU CANH BAO, hoac chuoi rong.

    In o CA HAI phia co chu dich: phia nguoi CHO (de biet nen doi hay di lam
    viec khac) va phia nguoi GIU (de chinh ho thay minh vua giu bao lau). Mot
    con so chi nguoi ngoai thay thi khong sua duoc hanh vi cua ai.
    """
    giay = time.time() - float(ban_ghi.get("bat_dau_epoch") or 0)
    if giay <= GIU_LAU_S:
        return ""
    return (f"GIU LAU: {giay / 60:.0f} phut (nguong {GIU_LAU_S / 60:.0f}). "
            f"Khoa bao DUNG lenh tinh — doc ket qua, sua ma, commit, viet bao "
            f"cao, cho nguoi/dich vu deu lam NGOAI khoa.")


def _mo_ta(ban_ghi: dict) -> str:
    giay = time.time() - float(ban_ghi.get("bat_dau_epoch") or 0)
    ten = ban_ghi.get("phien") or "?"
    return (f"{ten} (pid {ban_ghi.get('pid')}) chay "
            f"`{ban_ghi.get('lenh') or '?'}` duoc {giay / 60:.1f} phut")


#: Doc ra khi mot ban ghi khoa KHONG khai `so_loi`.
#:
#: ⛔ **KHONG phai 0, va day la phan de sai nhat cua ca co che.** Mot ban ghi cu
#:    (ghi truoc 03/09) khong co khoa nay. Doc no thanh 0 nghia la "luot do
#:    khong dung loi nao" — tuc ngan sach khong bi tru — tuc dung cai qua tai ma
#:    co che nay sinh ra de chan, chi khac la **im lang**.
#:
#: ⭐ "Khong khai" va "khong dung" la hai dieu khac nhau. Khi khong biet, doan ve
#:    phia DE DAT (fail-closed): mot luot gate dang giu `cpu_nhieu` thi chac chan
#:    dang dung mot phan dang ke cua may.
SO_LOI_KHI_KHONG_KHAI = 8


def thu_giu(phien: str, lenh: str, tai_nguyen: str = MAC_DINH, *,
            so_loi: int = 0) -> bool:
    """Thu chiem khoa MOT lan cho MOT tai nguyen. True neu duoc.

    `so_loi` la so loi luot nay se dung. Ghi vao ban ghi de mot luot KHAC tinh
    duoc ngan sach con lai cua **may**, thay vi cua rieng no.
    """
    tep = _tep(tai_nguyen)
    ban_ghi = {
        "phien": phien,
        "pid": os.getpid(),
        "may": socket.gethostname(),
        "lenh": lenh,
        "tai_nguyen": tai_nguyen,
        "so_loi": max(0, int(so_loi)),
        "bat_dau_epoch": time.time(),
        "bat_dau": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        # O_EXCL: hai tien trinh cung goi thi dung MOT thang thang. Doc-roi-ghi
        # khong lam duoc dieu do, va cua so dua chinh la luc dong nhat.
        fd = os.open(tep, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        cu = _doc(tai_nguyen)
        if cu is None:
            # Tep co that nhung khong doc duoc: rac tu mot lan ngat giua chung.
            tep.unlink(missing_ok=True)
            return thu_giu(phien, lenh, tai_nguyen)
        ly_do = _treo(cu)
        if not ly_do:
            return False
        print(f"  [cua so yen] doat khoa treo ({tai_nguyen}): "
              f"{_mo_ta(cu)} - {ly_do}")
        tep.unlink(missing_ok=True)
        return thu_giu(phien, lenh, tai_nguyen)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(ban_ghi, ensure_ascii=False))
    return True


def nha(phien: str = "", *, ep: bool = False,
        tai_nguyen: str = MAC_DINH) -> bool:
    """Tra khoa. Chi tra khoa CUA MINH tru khi `ep`."""
    tep = _tep(tai_nguyen)
    cu = _doc(tai_nguyen)
    if cu is None:
        tep.unlink(missing_ok=True)
        return True
    if not ep and int(cu.get("pid") or 0) != os.getpid():
        return False
    tep.unlink(missing_ok=True)
    return True


def loi_da_hua(ban_ghi: dict, *, tai_nguyen_can_tru: str = MAC_DINH) -> int:
    """So loi mot ban ghi khoa dang giu. Fail-CLOSED khi khong khai.

    🔴 Ham nay ton tai vi mot mac dinh 0 se lam ca co che vo dung mot cach im
       lang. Xem `SO_LOI_KHI_KHONG_KHAI`.
    """
    if ban_ghi.get("hong") or ban_ghi.get("treo"):
        return 0                      # khoa chet khong giu loi nao
    if str(ban_ghi.get("tai_nguyen") or MAC_DINH) != tai_nguyen_can_tru:
        return 0                      # tai nguyen khac, khong phai CPU
    khai = ban_ghi.get("so_loi")
    if khai is None:
        return SO_LOI_KHI_KHONG_KHAI
    try:
        return max(0, int(khai))
    except (TypeError, ValueError):
        return SO_LOI_KHI_KHONG_KHAI


def loi_phien_khac_dang_giu(phien_minh: str = "",
                            tai_nguyen: str = MAC_DINH) -> int:
    """Tong loi cac luot KHAC dang giu. Dung de bien ngan sach thanh per-MAY."""
    return sum(loi_da_hua(r, tai_nguyen_can_tru=tai_nguyen)
               for r in dang_giu()
               if not (phien_minh and r.get("phien") == phien_minh))


def dang_giu() -> list[dict]:
    """Moi khoa dang ton tai tren may, kem ly do treo neu co.

    Dung cho `trang-thai`: mot phien thay "ban" phai biet **tai nguyen nao** va
    **ai** dang giu, neu khong no chi biet doi ma khong biet doi cai gi.
    """
    ra: list[dict] = []
    thu_muc = Path(tempfile.gettempdir())
    ung_vien = [TEP_KHOA, *sorted(thu_muc.glob("ltt_khoa_*.json"))]
    for tep in ung_vien:
        if not tep.exists():
            continue
        try:
            ban_ghi = json.loads(tep.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra.append({"tai_nguyen": tep.stem, "hong": True})
            continue
        ban_ghi.setdefault("tai_nguyen", MAC_DINH)
        ban_ghi["treo"] = _treo(ban_ghi)
        ra.append(ban_ghi)
    return ra


class CuaSoYen:
    """Context manager: giu khoa suot mot luot do.

    ⛔ `bat=False` van dung duoc nhu mot khoi `with` — de ben goi khong phai
       viet hai nhanh chi vi co mot co `--khong-khoa`.

    ⚠️ Cho qua han thi **van chay**, khong bo cuoc. Mot cong chat luong tu choi
       chay vi ban la mot cong khong ai dung; no chi phai NOI RO rang ket qua
       lan nay co the bi nhieu.
    """

    def __init__(self, phien: str, lenh: str, *, bat: bool = True,
                 cho_toi_da_s: float = 1800.0,
                 tai_nguyen: tuple[str, ...] = (MAC_DINH,),
                 so_loi: int = 0):
        self.so_loi = max(0, int(so_loi))
        self.phien = phien
        self.lenh = lenh
        self.bat = bat
        self.cho_toi_da_s = cho_toi_da_s
        # 🔴 SAP XEP la mot yeu cau dung dan, khong phai de cho gon.
        #
        #    Hai luot cung xin {postgres_test, cpu_nhieu} theo hai thu tu khac
        #    nhau thi moi ben giu mot cai va doi cai kia — khoa chet, va no chi
        #    xay ra khi hai phien tinh co bat dau gan nhau, tuc rat kho tai
        #    hien. Xin theo cung mot thu tu tuyet doi thi truong hop do khong
        #    ton tai duoc.
        self.tai_nguyen = tuple(sorted(set(tai_nguyen)))
        self.da_giu: list[str] = []
        #: Da nha roi, nhung GIU LAI de bao cao sau khoi `with`.
        self.da_giu_xong: list[str] = []
        self.da_cho_s = 0.0
        #: Luc giu duoc khoa (epoch). 0 = chua tung giu (tat khoa, hoac chay
        #: khong khoa sau khi cho qua han) ⇒ khong co gi de khai luc thoat.
        self.bat_dau_giu = 0.0

    def _thu_giu_het(self) -> bool:
        """Xin TAT CA, hoac khong xin gi.

        ⛔ Giu mot phan roi doi phan con lai la cong thuc khoa chet thu hai:
           ta giu A va doi B trong khi luot kia giu B va doi A. Nen that bai o
           bat cu cai nao la nha het roi thu lai tu dau.
        """
        for tn in self.tai_nguyen:
            if not thu_giu(self.phien, self.lenh, tn, so_loi=self.so_loi):
                for da in self.da_giu:
                    nha(self.phien, tai_nguyen=da)
                self.da_giu = []
                return False
            self.da_giu.append(tn)
        return True

    @property
    def chay_khong_khoa(self) -> bool:
        """Luot nay dang CHEN: da het gio cho ma khoa van bi giu.

        ⭐ **B3 khong can mot nhanh ngan sach rieng, va do la ket qua chu khong
           phai su tinh co.** Khi chen, luot kia VAN dang giu khoa, nen ban ghi
           cua no van nam do — va `ngan_sach_loi(tru_phien_khac=True)` (goi SAU
           khoi `with`) tu dong tru phan cua no. Do that: mot luot kia giu 10 loi
           thi ngan sach cua ta tu 14 tut xuong 4.

        ⇒ "Chen thi chay nho" roi ra tu chinh phep tru per-MAY. Viet them mot
          nhanh `neu dang chen thi giam` se la mot duong thu hai toi cung mot
          ket qua — va hai duong toi cung mot so la hai cho de chung lech nhau.

        Thuoc tinh nay chi de **noi ra** dieu do o dong ket qua. No khong tham
        gia phep tinh nao.
        """
        return self.bat and bool(self.tai_nguyen) and not self.da_giu

    def _ai_giu(self) -> str:
        for tn in self.tai_nguyen:
            cu = _doc(tn)
            if cu is not None and not _treo(cu):
                return f"{tn}: {_mo_ta(cu)}"
        return "(khong ro)"

    def __enter__(self) -> "CuaSoYen":
        if not self.bat or not self.tai_nguyen:
            return self
        bat_dau = time.time()
        in_lan_cuoi = 0.0
        khong_chen = sorted(set(self.tai_nguyen) & KHONG_DUOC_CHEN)
        da_bao_khong_chen = False
        while True:
            if self._thu_giu_het():
                self.bat_dau_giu = time.time()
                self.da_cho_s = time.time() - bat_dau
                if self.da_cho_s > 2:
                    print(f"  [cua so yen] den luot - da doi "
                          f"{self.da_cho_s / 60:.1f} phut\n")
                return self
            doi = time.time() - bat_dau
            if doi > self.cho_toi_da_s and khong_chen:
                # 🔴 SU CO 17/09 (tests/test_1500): chen vao `postgres_test` khi luot
                #    kia dang `drop_all` tren CUNG CSDL test ⇒ `relation "jobs" does not
                #    exist` — mot ket qua SAI, khong chi cham. Khoa treo (tien trinh
                #    chet / qua gia) van bi doat trong `thu_giu`, nen cho tiep khong ket.
                if not da_bao_khong_chen:
                    print(f"  [cua so yen] cho qua {self.cho_toi_da_s / 60:.0f} phut "
                          f"nhung KHONG chen {', '.join(khong_chen)} (ket qua se sai) "
                          f"- cho tiep: {self._ai_giu()}")
                    da_bao_khong_chen = True
            elif doi > self.cho_toi_da_s:
                print(f"  [cua so yen] cho qua {self.cho_toi_da_s / 60:.0f} "
                      f"phut ma khoa van bi giu: {self._ai_giu()}")
                print("  [cua so yen] CHAY MA KHONG CO KHOA - ket qua co the "
                      "bi nhieu boi luot kia.\n")
                self.da_cho_s = doi
                return self
            if time.time() - in_lan_cuoi > NHIP_IN_S:
                print(f"  [cua so yen] xep hang {doi / 60:.1f} phut - "
                      f"{self._ai_giu()}")
                for tn in self.tai_nguyen:
                    cu = _doc(tn)
                    if cu and (cb := _canh_bao_giu_lau(cu)):
                        print(f"  [cua so yen] [{tn}] {cb}")
                in_lan_cuoi = time.time()
            time.sleep(1.0)

    def __exit__(self, *_exc) -> None:
        # 🔴 GIU LAI DANH SACH DA NHA truoc khi xoa no.
        #
        #    `da_giu` phai rong sau khi thoat (neu khong, mot lan goi `__exit__`
        #    thu hai se nha khoa cua nguoi khac). Nhung nguoi goi thuong doc
        #    "luot nay da giu gi" **sau** khoi `with` — do dung la luc ghi bao
        #    cao. Do 2026-09-02: kho ket qua cua gate ghi `tai_nguyen_da_giu: []`
        #    cho mot luot **co** giu `cpu_nhieu`. Khong sai mot cach on ao; chi
        #    lang le ghi sai vao dung cho nguoi sau se tin.
        self.da_giu_xong = list(self.da_giu)
        for tn in self.da_giu:
            nha(self.phien, tai_nguyen=tn)
        self.da_giu = []
        # Khai ra chinh minh vua giu bao lau. Nguoi giu la nguoi duy nhat sua
        # duoc cach bon lenh; nguoi cho chi biet than.
        if self.bat_dau_giu and self.da_giu_xong:
            giu = time.time() - self.bat_dau_giu
            ten = ", ".join(self.da_giu_xong)
            print(f"  [cua so yen] da nha {ten} - giu khoa {giu / 60:.1f} phut")
            if giu > GIU_LAU_S:
                print(f"  [cua so yen] CANH BAO: GIU LAU hon nguong "
                      f"{GIU_LAU_S / 60:.0f} phut. Lenh nay co buoc KHONG phai "
                      f"tinh (cho, doc, sua, commit) khong? Tach ra, hoac chia "
                      f"nho lenh tinh.")


def main() -> int:
    p = argparse.ArgumentParser(description="Khoa cua so yen cho cac luot do.")
    p.add_argument("lenh", choices=["trang-thai", "nha"])
    p.add_argument("--ep", action="store_true",
                   help="voi `nha`: go ca khoa cua phien khac")
    p.add_argument("--tai-nguyen", default="",
                   help="voi `nha`: chi nha mot tai nguyen (mac dinh: TAT CA)")
    a = p.parse_args()

    if a.lenh == "trang-thai":
        ds = dang_giu()
        if not ds:
            print("RANH - khong tai nguyen nao dang bi giu.")
            return 0
        for bg in ds:
            if bg.get("hong"):
                print(f"[{bg['tai_nguyen']}] TEP KHOA HONG - luot sau se don.")
                continue
            print(f"[{bg['tai_nguyen']}] {_mo_ta(bg)}")
            if cb := _canh_bao_giu_lau(bg):
                print(f"    CANH BAO: {cb}")
            if bg.get("treo"):
                print(f"    CANH BAO: TREO ({bg['treo']}) - luot sau tu doat.")
        return 0

    can_nha = ([a.tai_nguyen] if a.tai_nguyen
               else [bg.get("tai_nguyen", MAC_DINH) for bg in dang_giu()])
    if not can_nha:
        print("Khong co khoa nao de nha.")
        return 0
    that_bai = [tn for tn in can_nha if not nha(ep=a.ep, tai_nguyen=tn)]
    if not that_bai:
        print(f"Da nha: {', '.join(can_nha)}")
        return 0
    # 🔴 Cau goi y phai NEU TEN tai nguyen, va day la cho no NGUY HIEM nhat.
    #
    #    Dong nay in ra **dung luc mot phien khac dang giu khoa** (`that_bai` la
    #    nhung khoa ta vua KHONG nha duoc vi khong phai cua ta). Ban cu goi y
    #    `nha --ep` tran — ma `--ep` khong kem `--tai-nguyen` thi go **TAT CA**
    #    khoa tren may (xem `can_nha` o tren). Ai lam theo nguyen van la go ca
    #    khoa cua mot luot gate dang song, dung o cho nguoi ta de tin nhat.
    #
    # ⚠️ Do la duong thu TU cham toi khoa that, va no **khong** hien ra o phep
    #    quet ma: ba duong kia (`nha(ep=True)`, `dang_giu()`, `_tep("<ten>")`)
    #    deu doc duoc bang AST, con duong nay di qua **mot chuoi goi y** ma con
    #    nguoi go tay theo.
    goi_y = " ".join(f"--tai-nguyen {tn}" for tn in that_bai[:1])
    them = "  (lam TUNG cai, dung go tran)" if len(that_bai) > 1 else ""
    print(f"Phien khac dang giu: {', '.join(that_bai)}. "
          f"Neu chac chung treo: `nha --ep {goi_y}`{them}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
