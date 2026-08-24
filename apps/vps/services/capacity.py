"""Xếp chỗ: còn bán được máy nào nữa không.

## Vì sao đây là một module riêng chứ không phải một câu `if` trong routes

Đây là thứ duy nhất đứng giữa "bán thêm một máy" và "kho đầy, **mọi VM cùng hỏng
một lượt**". Ở ảo hoá lồng trên một ổ đĩa không RAID, đó không phải rủi ro lý
thuyết. Nó xứng đáng có tên, có test, và có lý do viết ra.

## RAM và ĐĨA được đối xử KHÁC NHAU — đây là điều quan trọng nhất ở file này

Chốt V14 (2026-08-22) sau khi đo cụm thật:

**RAM là tài nguyên CỨNG.** Máy khách mua 4 GB thì 4 GB đó bị giữ, không ai dùng
chung được. Bán quá RAM là máy không khởi động nổi — hỏng ngay, thấy ngay. Vì thế
RAM kiểm theo **cam kết**, và kiểm nghiêm.

**ĐĨA là tài nguyên CHIA SẺ.** Kho là LVM-thin: một máy khai 80 GB nhưng chỉ chiếm
phần nó ghi thật (node đo được: **640 GB đã hứa, 173,6 GB dùng thật**). Giữ chỗ
cứng 80 GB cho mỗi máy là **lãng phí 3/4 kho** và làm sản phẩm không bán được.
Nên `disk_gb` của một gói là **hạn mức**, không phải chỗ đã giữ.

## Ba cái phanh cho đĩa, vì bán chồng thì phải có phanh

Bán chồng đĩa mà không có phanh nghĩa là bán vô hạn, và kho đầy thì **mọi VM cùng
hỏng một lượt** — không chỉ máy gây đầy.

1. **Thực dùng < 80 %** (`kho_qua_tai`). Bắt trường hợp máy đầy dần theo thời gian
   *mà không ai bán thêm gì cả* — không phanh nào khác thấy được điều đó.
2. **Bán chồng ≤ `TRAN_BAN_CHONG`** (`cho_phep_ban`). Chặn việc bán vô hạn khi kho
   còn rỗng: hôm nay 20 % nhưng đã hứa gấp 10 lần thì ngày mai là thảm hoạ.
3. **Không đọc được dung lượng ⇒ NGỪNG bán** (fail-closed). Bán khi không biết còn
   bao nhiêu chỗ là đúng thứ ta đang phòng.

Bỏ phanh 1 thì một đêm nào đó kho đầy mà không ai được báo. Bỏ phanh 2 thì phanh 1
chỉ kịp bắt khi đã quá muộn để dọn.

## Vì sao ngưỡng là 80 % chứ không phải 95 %

Từ 80 % tới lúc hỏng, mọi thứ vẫn chạy bình thường — không có triệu chứng nào để
ai nhận ra. 20 % còn lại là thời gian để một con người kịp phản ứng: xoá máy hết
hạn, nới đĩa, hoặc dừng bán. Đặt 95 % là bỏ mất khoảng thời gian đó.
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.vps.cost import Plan, dia_tong_gb, lay_plan

#: Kho vượt tỉ lệ này thì ngừng nhận máy mới. Xem docstring.
NGUONG_CHAN_BAN = 0.80

#: Trần bán chồng đĩa: tổng dung lượng ĐÃ HỨA / dung lượng kho thật.
#:
#: V14 chốt đĩa là **tài nguyên chia sẻ**, không giữ chỗ cứng cho từng máy — nên
#: `cho_phep_ban` không còn từ chối chỉ vì "đã hứa vượt kho". Nhưng bỏ hẳn giới
#: hạn thì thành bán vô hạn: mỗi máy mới làm xác suất kho đầy cao hơn, mà kho đầy
#: là **mọi VM cùng hỏng một lượt**.
#:
#: 3.0 chọn theo số đo thật: node đang ở 1,49× với 36,5 % kho thực dùng. Nhân đôi
#: mức đó là còn chỗ để phanh thứ nhất (80 % thực dùng) kịp bắt trước.
TRAN_BAN_CHONG = 3.0

#: RAM chừa cho chính Proxmox (kernel, ZFS ARC, các tiến trình quản trị).
#: 5 GB đo theo cấu hình đích 64 GB; đo lại nếu đổi kiểu kho lưu trữ.
RAM_DU_PHONG_MB = 5 * 1024

#: Đĩa chừa cho template. Catalog toàn Windows: Server 2022 ~20 GB + Win 10/11
#: ~25 GB. Đây là chỗ mà "thêm một bản Windows vào menu" tốn 20 GB thật.
DIA_TEMPLATE_GB = 45


@dataclass(frozen=True)
class SucChua:
    """Sức chứa của node: cái có, cái đã hứa, và cái đang dùng thật.

    Mọi con số là **tuyệt đối** (MB / GB), không phải phần trăm — bài học H38:
    ngưỡng theo phần trăm đổi ý nghĩa mỗi lần nới phần cứng, và không ai để ý.

    `dia_gb_dang_dung` là chỗ **thực sự đã ghi** trên kho, khác hẳn
    `dia_gb_da_hua` (tổng dung lượng khai báo của mọi máy). Với LVM-thin hai con
    số này lệch nhau rất xa — node đo được 640 GB hứa / 173,6 GB dùng thật — và
    chính khoảng lệch đó là thứ V14 cho phép bán.
    """

    ram_mb_tong: int
    dia_gb_tong: int
    ram_mb_da_hua: int = 0
    dia_gb_da_hua: int = 0
    dia_gb_dang_dung: int = 0
    #: Số luồng CPU thật của node, và tổng vCPU đã cam kết cho MỌI máy trên nó.
    #: Trước 24/08 hai con số này không được đo — `cho_phep_ban` gác RAM và đĩa
    #: nhưng **không gác CPU chút nào**, nên mức bán chồng CPU là một hệ quả tình
    #: cờ chứ không phải một lựa chọn.
    cpu_tong: int = 0
    vcpu_da_hua: int = 0

    @property
    def ram_mb_ban_duoc(self) -> int:
        return max(0, self.ram_mb_tong - RAM_DU_PHONG_MB)

    @property
    def dia_gb_ban_duoc(self) -> int:
        return max(0, self.dia_gb_tong - DIA_TEMPLATE_GB)

    @property
    def ram_mb_con(self) -> int:
        """RAM còn bán được. **Cứng** — hết là hết."""
        return max(0, self.ram_mb_ban_duoc - self.ram_mb_da_hua)

    @property
    def dia_gb_con_that(self) -> int:
        """Đĩa còn TRƯỚC khi chạm phanh 80 %. Đây mới là chỗ thật còn trống."""
        tran = int(self.dia_gb_ban_duoc * NGUONG_CHAN_BAN)
        return max(0, tran - self.dia_gb_dang_dung)

    @property
    def ty_le_ban_chong_cpu(self) -> float:
        """Đã cam kết gấp mấy lần số luồng thật. 0 = chưa đo được."""
        if self.cpu_tong <= 0:
            return 0.0
        return self.vcpu_da_hua / self.cpu_tong

    @property
    def ty_le_ban_chong(self) -> float:
        """Đã hứa gấp mấy lần kho. > 1 là bình thường với thin; > 3 là liều."""
        if self.dia_gb_ban_duoc <= 0:
            return 0.0
        return self.dia_gb_da_hua / self.dia_gb_ban_duoc


@dataclass(frozen=True)
class KetQuaKiem:
    """Kết quả một lần kiểm. `ly_do` viết cho NGƯỜI đọc, không phải cho log."""

    cho_phep: bool
    ly_do: str = ""


#: Trần bán chồng vCPU. Bán chồng CPU là **bình thường** với VPS — phần lớn máy
#: nhàn phần lớn thời gian — nhưng "bình thường" khác "vô hạn", và nó phải là một
#: con số đã chọn chứ không phải một hệ quả tình cờ.
#:
#: Node đo được 24/08: **32 luồng**, mà riêng 8 máy của chủ nhà đã cam kết **41
#: vCPU** — node đã ở 1,28× trước khi bán cho ai một máy nào. Bán hết 16 máy Nhỏ
#: đưa nó lên ~1,8×.
#:
#: 3,0× cùng con số với trần bán chồng đĩa (V14), và lý do giống nhau: qua mức đó
#: thì cái mất là **độ trễ** — máy vẫn chạy, chỉ giật, và khách không chứng minh
#: được điều gì.
TRAN_BAN_CHONG_CPU = 3.0


def cho_phep_ban(suc_chua: SucChua, plan_id: str, dia_them_gb: int = 0
                 ) -> KetQuaKiem:
    """Còn bán thêm được một máy theo gói này không?

    Ba câu hỏi, theo đúng thứ tự đắt dần, và **RAM hỏi trước** vì nó là thứ duy
    nhất không thương lượng được: thiếu RAM thì máy không khởi động nổi.
    """
    plan: Plan | None = lay_plan(plan_id)
    if plan is None:
        return KetQuaKiem(False, f"khong co goi {plan_id!r}")

    # 1) RAM — tài nguyên CỨNG, giữ chỗ thật cho từng máy.
    if plan.ram_mb > suc_chua.ram_mb_con:
        return KetQuaKiem(
            False,
            f"het RAM: goi can {plan.ram_mb} MB, con {suc_chua.ram_mb_con} MB")

    # 2) Kho THỰC DÙNG đã chạm phanh 80 % chưa. Không đọc được = coi như đầy.
    if suc_chua.dia_gb_ban_duoc <= 0:
        return KetQuaKiem(False, "khong doc duoc dung luong kho")
    if suc_chua.dia_gb_con_that <= 0:
        return KetQuaKiem(
            False,
            f"kho da dung {suc_chua.dia_gb_dang_dung} GB tren "
            f"{suc_chua.dia_gb_ban_duoc} GB — vuot nguong "
            f"{NGUONG_CHAN_BAN * 100:.0f}%")

    # 3) Bán chồng — đĩa là tài nguyên CHIA SẺ (V14), nhưng không vô hạn.
    can_dia = dia_tong_gb(plan_id, dia_them_gb)
    ty_le_moi = (suc_chua.dia_gb_da_hua + can_dia) / suc_chua.dia_gb_ban_duoc
    if ty_le_moi > TRAN_BAN_CHONG:
        return KetQuaKiem(
            False,
            f"ban chong dia se len {ty_le_moi:.2f}x, tran la "
            f"{TRAN_BAN_CHONG:.1f}x")
    # 4) Bán chồng CPU. Không đo được `cpu_tong` thì **bỏ qua** phép kiểm này,
    #    không chặn: CPU khác RAM và đĩa ở chỗ thiếu nó máy vẫn chạy (chỉ chậm),
    #    nên "không đọc được" ở đây không đáng để dừng bán hàng.
    if suc_chua.cpu_tong > 0:
        ty_le_cpu = (suc_chua.vcpu_da_hua + plan.vcpu) / suc_chua.cpu_tong
        if ty_le_cpu > TRAN_BAN_CHONG_CPU:
            return KetQuaKiem(
                False,
                f"ban chong CPU se len {ty_le_cpu:.2f}x ({suc_chua.vcpu_da_hua}"
                f"+{plan.vcpu} vCPU tren {suc_chua.cpu_tong} luong), tran la "
                f"{TRAN_BAN_CHONG_CPU:.1f}x")
    return KetQuaKiem(True)


def kho_qua_tai(da_dung_bytes: int, tong_bytes: int,
                nguong: float = NGUONG_CHAN_BAN) -> KetQuaKiem:
    """Kho lưu trữ THỰC đã vượt ngưỡng chưa? (phép kiểm 2)

    `cho_phep=False` nghĩa là **quá tải, phải ngừng bán** — đọc ngược với tên hàm
    một chút, nhưng giữ chung một kiểu trả về để người gọi không phải nhớ hai luật.
    """
    tong = int(tong_bytes or 0)
    if tong <= 0:
        # Không đọc được dung lượng kho thì **coi như quá tải**. Fail-closed:
        # bán khi không biết còn bao nhiêu chỗ là đúng thứ ta đang phòng.
        return KetQuaKiem(False, "khong doc duoc dung luong kho")
    ty_le = int(da_dung_bytes or 0) / tong
    if ty_le >= nguong:
        return KetQuaKiem(
            False,
            f"kho da dung {ty_le * 100:.1f}% (nguong {nguong * 100:.0f}%)")
    return KetQuaKiem(True)


def cam_ket_tu_vm(vms: list) -> tuple[int, int, int]:
    """RAM (MB), đĩa (GB) và vCPU đã CAM KẾT cho **mọi** VM trên node.

    Trả `(ram, dia, vcpu)`.

    ## Vì sao phải đếm cả VM không thuộc app này

    Đây là lỗi đã có thật trong bản đầu của module này, và nó chỉ lộ ra khi đo
    cụm thật: bản đầu chỉ cộng phần app tự bán, nên với một node đã có **8 máy
    của chủ nhà chiếm 35,9 GB / 43,2 GB RAM**, nó vẫn báo "còn 38 GB, bán tiếp
    đi". Bán tiếp ở đó là bán chỗ của chính mình.

    Proxmox là **nguồn chân lý duy nhất** về việc node đang cam kết bao nhiêu —
    CSDL của app chỉ biết phần app bán ra. Vì thế con số nền lấy từ Proxmox, và
    CSDL chỉ bù thêm những máy app đã hứa mà **chưa kịp tạo VM** (xem
    `provisioning.suc_chua_hien_tai`).

    Đếm theo **cam kết** (`maxmem`/`maxdisk`) chứ không theo **đang dùng**: khách
    mua 4 GB thì có quyền dùng 4 GB, kể cả lúc máy đang chạy ở 800 MB.

    Template không tính — nó không chạy, và đĩa của nó đã trừ ở `DIA_TEMPLATE_GB`.
    """
    ram = dia = vcpu = 0
    for v in vms or []:
        if int(v.get("template") or 0):
            continue
        ram += int(v.get("maxmem") or 0)
        dia += int(v.get("maxdisk") or 0)
        vcpu += int(v.get("cpus") or 0)
    return ram // (1024 * 1024), dia // (1024 ** 3), vcpu


def suc_chua_tu_proxmox(trang_thai_node: dict, kho: list, *,
                        ten_kho: str = "") -> SucChua:
    """Dựng `SucChua` từ phản hồi thật của Proxmox.

    `ten_kho` rỗng = lấy kho lớn nhất có `content` chứa `images`. Đó gần như luôn
    đúng với một node đơn, và sai thì sai *về phía nhỏ hơn* — an toàn.
    """
    ram_bytes = int((trang_thai_node.get("memory") or {}).get("total") or 0)

    ung_vien = [k for k in (kho or [])
                if "images" in str(k.get("content", ""))
                and int(k.get("total") or 0) > 0]
    if ten_kho:
        ung_vien = [k for k in ung_vien if k.get("storage") == ten_kho]
    chon = max(ung_vien, key=lambda k: int(k.get("total") or 0), default=None)
    dia_bytes = int((chon or {}).get("total") or 0)

    return SucChua(ram_mb_tong=ram_bytes // (1024 * 1024),
                   dia_gb_tong=dia_bytes // (1024 ** 3))


def kho_lon_nhat(kho: list) -> dict:
    """Kho `images` lớn nhất — dùng cho phép kiểm 2. `{}` nếu không có."""
    ung_vien = [k for k in (kho or [])
                if "images" in str(k.get("content", ""))
                and int(k.get("total") or 0) > 0]
    return max(ung_vien, key=lambda k: int(k.get("total") or 0), default={})
