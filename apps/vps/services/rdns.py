"""rDNS cho IP khach: A record truoc, PTR sau — va khong bao gio chan viec giao may.

## Vi sao co tep nay

Do 25/09/2026 khi so voi Vultr: **khong mot IP nao cua ta co PTR**, trong khi moi
nha cung cap deu dat mac dinh (`*.vultrusercontent.com`, `*.compute.amazonaws.com`,
`*.ovh.net`). Mot dia chi datacenter khong co rDNS la mot diem tru voi cac he thong
chong lam dung.

## Thu tu la mot BAT BIEN, khong phai so thich

OVH **bat buoc forward-confirm**. Do that tren `51.79.202.1`:

    POST /ip/51.79.202.1%2F32/reverse
    400 {"message":"Cannot check if ip-51-79-202-1.vps.lttstudios.com. resolves to 51.79.202.1"}

Nen: tao A record -> cho no resolve -> moi dat PTR. Goi OVH truoc chi de nhan mot
loi kho doc hon.

## ⛔ Khong bao gio nem

Mot may khong co rDNS van la mot may **giao duoc**; mot may khong giao duoc vi DNS
la mot **su co**. Moi loi o day tra `False` va ghi canh bao. `bao_tri` kiem lai va
ghi ban ghi suc khoe, nen mot IP thieu PTR **hien ra** chu khong bien mat.

## Ten suy tu IP, ⛔ khong lay ten khach dat

Khach dat ten may tuy y. Ten do se nam **cong khai trong DNS** va khong xoa duoc
khoi lich su cac dich vu quet DNS. Ten suy tu IP thi khong lo gi ve khach.
"""
from __future__ import annotations

import ipaddress
import logging

log = logging.getLogger(__name__)

#: Vung dat A record cho IP khach. Mot hang so, khong go lai o cho khac.
MIEN_RDNS = "vps.lttstudios.com"


def ten_forward(ip: str) -> str:
    """`51.79.215.194` -> `ip-51-79-215-194.vps.lttstudios.com`.

    ⛔ Tu choi moi thu khong phai IPv4: chuoi nay di vao mot loi goi API va vao
       DNS cong khai.
    """
    dia_chi = ipaddress.IPv4Address(str(ip or "").strip())   # ValueError neu rac
    return "ip-" + str(dia_chi).replace(".", "-") + "." + MIEN_RDNS


def dat_rdns(dns, ovh, ip: str) -> bool:
    """A record truoc, PTR sau. Tra `True` khi ca hai buoc xong.

    `dns` co `dat_a_record(ten, ip)`; `ovh` co `dat_reverse(ip, ten)`.
    """
    try:
        ten = ten_forward(ip)
    except ValueError:
        log.warning("VPS rdns: dia chi khong hop le, bo qua: %r", ip)
        return False
    try:
        dns.dat_a_record(ten, str(ip))
    except Exception as exc:                  # noqa: BLE001 - xem docstring module
        log.warning("VPS rdns: khong tao duoc A record %s -> %s: %s", ten, ip, exc)
        return False
    try:
        ovh.dat_reverse(str(ip), ten)
    except Exception as exc:                  # noqa: BLE001
        log.warning("VPS rdns: A record %s da co nhung OVH tu choi PTR: %s", ten, exc)
        return False
    log.info("VPS rdns: %s -> %s", ip, ten)
    return True


#: Bon trang thai cua mot PTR — ⛔ khong duoc gop lam it hon.
DA_THAY = "da_thay"              # DNS cong khai da tra dung ten
DANG_LAN = "dang_lan"            # OVH luu, DNS chua tra (binh thuong trong vai gio)
CHUA_DAT = "chua_dat"            # OVH tra loi RO RANG la khong co ban ghi (404)
KHONG_DO_DUOC = "khong_do_duoc"  # khong hoi duoc OVH — chua biet gi ca


#: HTTP 404 tu OVH = "khong co ban ghi reverse". Moi ma khac (403 khoa chet, 5xx,
#: het thoi gian) la su VANG MAT cua cau tra loi, khong phai cau tra loi "khong".
MA_KHONG_CO_BAN_GHI = 404


def trang_thai_ptr(ovh, ip: str, *, tra_cuu=None) -> tuple[str, str]:
    """Tra `(trang_thai, chi_tiet)`. Hoi DNS CONG KHAI truoc, OVH sau.

    ## Thu tu nay la mot bat bien, khong phai so thich

    🔴 Do 25/09/2026 (chieu): consumer key OVH bi thu hoi — `403 "This credential
       is not valid"`. Ban cu hoi OVH TRUOC va `except` nuot 403 thanh `CHUA_DAT`
       (chu thich cu con viet han: *"khong doc duoc = chua dat"*). Ket qua: cong
       cu khai **moi IP** la chua co PTR, trong khi `nslookup` tren CA HAI resolver
       cong khai tra dung ten — PTR da dat va da forward-confirm tu truoc.
       Tin cong cu thi ta di dat lai PTR da co, bang chinh cai khoa dang chet.

    ⇒ Thu tu dung: **DNS cong khai la su that**. Khach cua khach nhin thay no, va
      no do duoc ma khong can bat cu khoa API nao. OVH chi con mot viec: phan biet
      *dang lan* voi *chua dat*, khi va chi khi DNS con im.

    ## "Khong do duoc" la trang thai THU TU

    `403` va `404` deu la `HTTPError`, nhung mot cai noi *"ban khong duoc hoi"* va
    cai kia noi *"khong co gi ca"*. Gop chung lai la bien mot dut mach do luong
    thanh mot phat hien ve ha tang. (Cung khuon da can nhieu lan 24-25/09.)
    """
    try:
        mong_doi = ten_forward(ip)
    except ValueError:
        return CHUA_DAT, "dia chi khong hop le"

    tra = tra_cuu or _tra_cuu_cong_khai
    do_duoc_dns = True
    try:
        thay = str(tra(str(ip)) or "").rstrip(".")
    except Exception:                         # noqa: BLE001 - xem docstring module
        # ⛔ "Resolver noi khong co" (chuoi rong) va "toi khong doc duoc dau ra"
        #    (nem) la HAI viec. Gop lai thi mot dut mach do luong bao cao thanh
        #    mot su that ve rDNS — dung cai da xay ra chieu 25/09.
        thay, do_duoc_dns = "", False
    if do_duoc_dns and thay == mong_doi:
        return DA_THAY, thay

    o_ovh, do_duoc, vi_sao = _reverse_o_ovh(ovh, ip)
    if not do_duoc:
        return KHONG_DO_DUOC, f"khong hoi duoc OVH ({vi_sao})"
    if not o_ovh:
        return CHUA_DAT, "OVH khong co ban ghi reverse"
    if not do_duoc_dns:
        return DANG_LAN, f"OVH luu {o_ovh}, chua do duoc DNS cong khai"
    if thay:
        return DANG_LAN, f"OVH luu {o_ovh}, DNS cong khai tra {thay}"
    return DANG_LAN, f"OVH luu {o_ovh}, DNS cong khai chua tra"


def _reverse_o_ovh(ovh, ip: str) -> tuple[str, bool, str]:
    """`(ten_o_ovh, do_duoc, vi_sao)`. `do_duoc=False` ⇒ ⛔ dung ket luan gi ca."""
    from urllib.parse import quote

    khoi = quote(str(ip) + "/32", safe="")
    try:
        ban = ovh.get(f"/ip/{khoi}/reverse/{quote(str(ip), safe='')}")
    except Exception as exc:                  # noqa: BLE001 - xem docstring module
        ma = getattr(exc, "status", None)
        if ma == MA_KHONG_CO_BAN_GHI:
            return "", True, ""
        ma_loi = getattr(exc, "ma_loi", "") or type(exc).__name__
        return "", False, f"{ma or '?'} {ma_loi}".strip()
    return str((ban or {}).get("reverse", "")).rstrip("."), True, ""


#: Resolver cong khai de hoi "the gioi co thay khong". ⛔ KHONG dung resolver he
#: thong: do 25/09/2026, `socket.gethostbyaddr` tra dung ten trong khi CA BA
#: resolver cong khai (8.8.8.8 / 1.1.1.1 / 9.9.9.9) **khong tra gi** — resolver
#: he thong da co ket qua tu dau do (cache/ISP) va no **khong dai dien** cho
#: nguoi ngoai. Hoi no roi ket luan "da thay" la tu lua o dung cho dang do.
RESOLVER_CONG_KHAI = ("1.1.1.1", "8.8.8.8")


class KhongDoDuocDns(OSError):
    """Khong doc duoc cau tra loi cua resolver — ⛔ KHONG co nghia la khong co PTR.

    🔴 Vi sao la mot ngoai le rieng: ban dau `_tra_cuu_cong_khai` tra chuoi rong
       cho ca hai truong hop "resolver noi khong co" va "toi khong hieu dau ra".
       Dau ra `nslookup` tren Windows la `Name:    x` (hai cham), regex lai cho
       `name = x` (dang cua `-type=PTR`) — nen no **chua tung khop**, va nua DNS
       cua phep kiem im lang tra rong suot. Mot dut mach do luong mac ao mot su
       that ve ha tang thi khong ai di sua, vi trong mat nguoi doc no *la* su that.
    """


#: `Name:  x` (nslookup Windows) HOAC `... name = x` (nslookup Unix / -type=PTR).
#: ⚠️ `Server:` va `Address:` cung o dau ra do — mau phai neo vao dung chu "name".
def _ten_trong_dau_ra(dau_ra: str) -> str:
    """Ten PTR trong dau ra `nslookup`, hoac rong neu khong co dong nao la ten."""
    import re

    for mau in (r"(?im)^\s*name\s*:\s*(\S+)\s*$", r"(?im)\bname\s*=\s*(\S+)"):
        khop = re.search(mau, dau_ra or "")
        if khop:
            return khop.group(1).rstrip(".")
    return ""


#: Cach resolver noi "dia chi nay khong co PTR". Do that 25/09 voi `192.0.2.1`:
#: ma thoat **0**, stdout rong, stderr `*** ... can't find 192.0.2.1:
#: Non-existent domain`. Nen ma thoat khong dung duoc lam dau hieu.
_NOI_KHONG_CO = ("non-existent domain", "nxdomain", "can't find",
                 "server failed", "no answer")


def _noi_khong_co_ban_ghi(van_ban: str) -> bool:
    thap = (van_ban or "").lower()
    return any(cau in thap for cau in _NOI_KHONG_CO)


def _tra_cuu_cong_khai(ip: str, *, chay=None) -> str:
    """PTR theo resolver CONG KHAI. Ba ket cuc, ⛔ khong phai hai:

    * mot ten            -> the gioi thay
    * chuoi rong         -> resolver tra loi RO RANG la khong co ban ghi
    * `KhongDoDuocDns`   -> khong doc duoc dau ra / khong goi duoc nslookup
    """
    import subprocess

    chay = chay or (lambda lenh, **kw: subprocess.run(
        lenh, capture_output=True, text=True, timeout=15, **kw))
    noi_khong_co = False
    for dns in RESOLVER_CONG_KHAI:
        try:
            ra = chay(["nslookup", str(ip), dns])
        except (OSError, subprocess.SubprocessError):
            continue
        ten = _ten_trong_dau_ra(getattr(ra, "stdout", "") or "")
        if ten:
            return ten
        if _noi_khong_co_ban_ghi((getattr(ra, "stdout", "") or "")
                                 + (getattr(ra, "stderr", "") or "")):
            noi_khong_co = True
    if noi_khong_co:
        return ""
    raise KhongDoDuocDns("khong resolver cong khai nao tra loi doc duoc")
