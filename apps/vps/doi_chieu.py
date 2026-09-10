"""Đối chiếu CSDL với bốn nguồn sự thật nằm ngoài nó.

## Vì sao cần một phép đối chiếu riêng

App giữ trạng thái ở **năm** chỗ, và bốn trong số đó không phải CSDL của nó:

| Nguồn | Giữ gì | Mất đồng bộ thì sao |
|---|---|---|
| Proxmox | VM | VM mồ côi ăn RAM và đĩa thật, không ai trả tiền |
| router (dnsmasq) | đặt chỗ DHCP | giữ một địa chỉ trong mạng riêng, máy mới nhận địa chỉ đó bị kẹt |
| router (nftables) | bộ đếm băng thông, cờ hãm | bộ đếm cũ dính sang khách mới = hoá đơn sai |
| cổng vào (nftables) | đường NAT 1:1 | gói từ Internet vẫn được dẫn vào mạng riêng |
| Vultr | Reserved IP | **$3/tháng chảy mãi**, và không ai nhìn thấy |

Trước 2026-08-25 **không có gì đối chiếu chúng**. Mọi lần đọc chỉ xảy ra *bên
trong một job, cho đúng một máy đó*. Nghĩa là mọi thứ mồ côi đều sống mãi và
không lộ ra ở đâu cả — không log, không cảnh báo, không một dòng trên trang admin.

## Chỉ NÓI RA, không tự **xoá**

Hàm ở đây không xoá gì. Tự xoá là đặt cược rằng phép đối chiếu không bao giờ
sai — và một phép đối chiếu sai mà tự xoá thì **xoá đúng thứ nó hiểu nhầm**. Ví
dụ: một VM đang được job khác dựng dở sẽ trông y hệt một VM mồ côi.

Người đọc quyết định, và `tools/vps_treo_khan.py` hay job xoá là công cụ để làm.

## Nhưng có MỘT thứ nó được phép tự làm: ghi lại phép đo

Từ VPS V2, vòng này còn **đọc trạng thái điện thật** của từng máy và ghi vào
`dien_quan_sat` + `quan_sat_luc`. Đó không phải "tự sửa": ghi lại một quan sát
không phá gì cả, và nó là thứ duy nhất làm cho `qua_cu()` có nghĩa. Không có nó,
mọi máy đều mang một phép đo từ lần thao tác gần nhất — có thể từ tháng trước.

## Năm mức của một phát hiện, và vì sao phải phân biệt

Bản đầu chỉ có một danh sách "mồ côi". Nhưng ba câu dưới đây đòi ba hành động
khác hẳn nhau, và gộp chúng vào một danh sách là mời người đọc xử lý sai:

| Mức | Nghĩa | Ai xử |
|---|---|---|
| `TU_CHUA_DUOC` | ghi lại một quan sát là đủ | vòng này, ngay |
| `THU_LAI_DUOC` | lệch giữa ý muốn và thực tế | một thao tác, tự động được |
| `CAN_NGUOI` | cần một quyết định | người vận hành |
| `NGHI_MO_COI` | trông như rác, **có thể không phải** | người vận hành, cẩn thận |
| `VO_BAT_BIEN` | một bất biến đã vỡ | người vận hành, ngay |

⛔ `NGHI_MO_COI` **không bao giờ** được tự xử. Tên của nó là một lời nhắc.
"""
from __future__ import annotations

from dataclasses import dataclass, field


#: Năm mức của một phát hiện. Xem docstring đầu tệp.
TU_CHUA_DUOC = "tu_chua_duoc"
THU_LAI_DUOC = "thu_lai_duoc"
CAN_NGUOI = "can_nguoi"
NGHI_MO_COI = "nghi_mo_coi"
VO_BAT_BIEN = "vo_bat_bien"

MUC_DO = (TU_CHUA_DUOC, THU_LAI_DUOC, CAN_NGUOI, NGHI_MO_COI, VO_BAT_BIEN)

#: Mức nào **cấm** mọi hành động tự động phá huỷ.
#:
#: Viết ra thành một tập hợp có tên thay vì để mỗi chỗ tự nhớ: một danh sách
#: chép tay ở ba nơi là ba nơi sẽ lệch nhau, và chỗ lệch đầu tiên xoá một VM
#: của khách.
CAM_TU_XU = frozenset({NGHI_MO_COI, CAN_NGUOI, VO_BAT_BIEN})


@dataclass(frozen=True)
class LechLac:
    """Một nhóm thứ lệch cùng loại, kèm **mức** để người đọc biết phải làm gì."""

    nhan: str
    muc: tuple
    hau_qua: str
    #: Mặc định `NGHI_MO_COI` — phía an toàn. Một phát hiện quên khai mức mà rơi
    #: vào `TU_CHUA_DUOC` là một phát hiện được tự xử mà không ai định thế.
    muc_do: str = NGHI_MO_COI

    def __str__(self) -> str:
        return f"[{self.muc_do}] {self.nhan}: {list(self.muc)} -> {self.hau_qua}"


@dataclass
class KetQua:
    lech: list = field(default_factory=list)
    so_may: int = 0
    so_ip: int = 0
    khong_doc_duoc: list = field(default_factory=list)
    #: Số máy vừa được ghi lại một phép đo điện thật trong lượt này.
    da_do_dien: int = 0

    @property
    def tong_mo_coi(self) -> int:
        return sum(len(x.muc) for x in self.lech)

    def theo_muc(self, muc_do: str) -> list:
        """Những phát hiện ở một mức. Dùng để quyết định nên báo động hay không."""
        return [x for x in self.lech if x.muc_do == muc_do]

    @property
    def can_nguoi_xu(self) -> int:
        """Số thứ **không** tự xử được. Đây mới là con số đáng báo động."""
        return sum(len(x.muc) for x in self.lech if x.muc_do in CAM_TU_XU)

    def __bool__(self) -> bool:
        return bool(self.lech)


def _an_toan(ten: str, ham, mac_dinh, ket_qua: KetQua):
    """Gọi một nguồn ngoài; nguồn không trả lời thì ghi lại và đi tiếp.

    Một nguồn im lặng **không** được làm mất kết quả của các nguồn khác: người
    chạy phép này thường đang tìm một sự cố, và mất nửa báo cáo là mất đúng nửa
    họ cần.
    """
    try:
        return ham()
    except Exception as exc:                     # noqa: BLE001
        ket_qua.khong_doc_duoc.append(f"{ten}: {type(exc).__name__}: "
                                      f"{str(exc)[:80]}")
        return mac_dinh


def quet(db, client) -> KetQua:
    """Đối chiếu tất cả. `client` là ProxmoxClient đã nối được."""
    from sqlalchemy import select

    from apps.vps.services import dinh_danh, gateway, router, vultr
    from apps.vps.tables import VpsInstance, VpsIp

    kq = KetQua()

    may = list(db.execute(select(VpsInstance).where(
        VpsInstance.trang_thai != "da_xoa")).scalars())
    ip_db = list(db.execute(select(VpsIp)).scalars())
    kq.so_may, kq.so_ip = len(may), len(ip_db)

    vmid_db = {m.vmid for m in may if m.vmid}
    mac_db = {dinh_danh.mac(m.id).lower() for m in may}
    priv_db = {str(m.ip_noi_bo) for m in may if m.ip_noi_bo}
    pub_db = {x.dia_chi for x in ip_db}

    # Chỉ xét VM mang tên `vps-*`: 8 máy của chủ nhà trên cùng node KHÔNG phải
    # việc của app, và báo chúng là mồ côi mỗi ngày sẽ dạy người đọc bỏ qua báo
    # cáo này.
    vm_app = _an_toan("proxmox", lambda: {
        int(v["vmid"]) for v in client.danh_sach_vm()
        if str(v.get("name") or "").startswith("vps-")}, None, kq)

    rt = _an_toan("router", router.client_tu_moi_truong, None, kq)
    dat_cho = _an_toan("router/dhcp", rt.danh_sach_dat_cho, {}, kq) if rt else {}
    dang_do = _an_toan("router/bw", rt.doc_bang_thong, {}, kq) if rt else {}
    dang_ham = _an_toan("router/ham", rt.danh_sach_giam_toc, set(), kq) if rt else set()

    gw = _an_toan("gateway", gateway.client_tu_moi_truong, None, kq)
    duong = _an_toan("gateway/nat", gw.danh_sach_duong, {}, kq) if gw else {}

    vt = _an_toan("vultr", vultr.client_tu_moi_truong, None, kq)
    ip_vt = _an_toan("vultr/ip",
                     lambda: {r["subnet"] for r in vt.danh_sach_ip()},
                     None, kq) if vt else None

    def them(nhan, tap, hau_qua, muc_do=NGHI_MO_COI):
        if tap:
            kq.lech.append(LechLac(nhan, tuple(sorted(tap)), hau_qua, muc_do))

    if vm_app is not None:
        them("VM tren Proxmox khong co trong CSDL", vm_app - vmid_db,
             "chiem RAM va dia that, khong ai tra tien", NGHI_MO_COI)
        # VO_BAT_BIEN chu khong NGHI_MO_COI: day la mot may **dang thu tien** ma
        # khong co thuc the nao dang sau. Khong co gi de "nghi" ca — so sach dang
        # sai, va no sai ve phia thu tien cua khach.
        them("May trong CSDL khong co VM",
             {m.vmid for m in may if m.vmid and m.vmid not in vm_app},
             "khach tra tien cho mot may khong ton tai", VO_BAT_BIEN)
    them("Dat cho DHCP khong ung may nao",
         {k for k in dat_cho if k.lower() not in mac_db},
         "giu mot dia chi trong mang rieng", NGHI_MO_COI)
    them("Dang do bang thong ma khong con may",
         {ip for ip in dang_do if ip not in priv_db},
         "bo dem cu dinh sang khach moi nhan cung dia chi = hoa don sai",
         NGHI_MO_COI)
    them("Dang bi ham toc ma khong con may",
         {ip for ip in dang_ham if ip not in priv_db},
         "khach moi nhan dia chi do bi ham, khong ai hieu vi sao", CAN_NGUOI)
    # Mot duong NAT khong co trong so sach dan goi tu Internet vao mang rieng —
    # do la mot lo hong BAO MAT, khong phai mot manh rac.
    them("Duong NAT khong co trong CSDL", set(duong) - pub_db,
         "goi tu Internet van duoc dan vao mang rieng", VO_BAT_BIEN)
    if ip_vt is not None:
        them("Reserved IP ben Vultr khong co trong CSDL", ip_vt - pub_db,
             "$3/thang chay mai, va khong ai nhin thay", NGHI_MO_COI)
        them("Dong vps_ip khong co IP that ben Vultr", pub_db - ip_vt,
             "so sach noi ta co mot dia chi ma thuc te khong con", VO_BAT_BIEN)

    # -- Dien: do that, ghi lai, va bao lech ---------------------------------
    kq.da_do_dien, lech_dien = _dong_bo_dien(db, client, may)
    them("May co y muon va thuc te khac nhau", lech_dien,
         "khach bam bat/tat ma may khong theo - mot thao tac se sua duoc",
         THU_LAI_DUOC)
    return kq


def _dong_bo_dien(db, client, may) -> tuple:
    """Doc dien THAT cua tung may, ghi lai, va tra ve nhung may bi lech.

    ## Vi sao day khong phai "tu sua"

    Ghi lai mot quan sat khong pha gi ca - no chi lam so sach noi dung hon thuc
    te. Thu bi cam la **hanh dong** dua tren quan sat do (xoa, tao lai, tat), va
    ham nay khong lam gi trong so ay.

    ## Vi sao no can thiet

    Khong co no, `dien_quan_sat` chi duoc cap nhat khi co ai do bam mot nut. Mot
    may khong ai dung toi trong ba thang mang mot phep do tu ba thang truoc, va
    `qua_cu()` khong the phan biet "may khoe" voi "may chet tu lau".

    ## Vi sao chi bao lech khi DO DUOC that

    `khong_ro` nghia la khong hoi duoc. Bao "lech" cho mot cau hoi that bai la
    bien mot su co MANG thanh mot su co CAU HINH, va nguoi doc se di sua nham cho.
    """
    from apps.vps import trang_thai_may as tt
    from apps.vps.services import tac_vu

    da_do, lech = 0, set()
    tam = KetQua()
    for m in may:
        if not m.vmid:
            continue
        dien = _an_toan(f"dien/{m.vmid}",
                        lambda m=m: tac_vu.doc_dien(client, m.vmid),
                        tt.KHONG_RO, tam)
        tt.ghi_quan_sat(m, dien)
        da_do += 1
        if (dien in (tt.CHAY, tt.TAT)
                and str(m.dien_mong_muon or "") in (tt.CHAY, tt.TAT)
                and dien != m.dien_mong_muon
                and not tt.dang_ban(m)):
            lech.add(f"{m.vmid}:muon={m.dien_mong_muon},thuc_te={dien}")
    return da_do, lech
