"""Proxmox giả **có trạng thái** — để kiểm hành vi bất đồng bộ, không kiểm thứ tự gọi.

## Vì sao cần cái này thay vì một mock ghi lại lời gọi

`CORE/OPERATING_CONTRACT.md` §M nói thẳng ra điều mà cả chương trình VPS V2 xoay
quanh:

> SAI: assert chuỗi `tat_cung` xuất hiện trước `khoi_phuc_anh`.
> ĐÚNG: fake Proxmox chuyển RUNNING → STOPPING → STOPPED; assert rollback không
> được gọi trước STOPPED.

Một mock chỉ ghi lại lời gọi **luôn xanh** cho cả bản đúng lẫn bản sai: cả hai đều
gọi `tat_cung` rồi `khoi_phuc_anh`. Khác biệt duy nhất là bản đúng **chờ giữa hai
lệnh** — và chờ thì không để lại dấu vết nào trong một danh sách lời gọi.

## Mô hình: đếm ngược theo LƯỢT HỎI, không theo đồng hồ

Mỗi tác vụ nền mang một bộ đếm `con_lai`. Mỗi lần ai đó hỏi `trang_thai_tac_vu`,
bộ đếm giảm một; về 0 thì tác vụ kết thúc **và** trạng thái điện của máy mới đổi.

Nhờ vậy bộ test chứng minh được đúng thứ cần chứng minh — *"mã có chờ không"* —
mà không tốn một giây đồng hồ nào. Một bộ test async tốn 5 giây mỗi ca là bộ test
người ta sẽ bỏ chạy, và nó lại đúng là bộ duy nhất bắt được lớp lỗi này.
"""
from __future__ import annotations

from apps.vps.services.proxmox import ProxmoxError


class TacVuGia:
    """Mot tac vu nen dang chay. `khi_xong` chay khi va chi khi no ket thuc TOT.

    Callback chu khong mot co: hai loai tac vu doi hai thu khac nhau khi xong
    (bat/tat doi dien, chup anh doi mot dong trong danh sach anh), va nhet ca hai
    vao mot truong la buoc moi cho doc phai doan xem truong do dang noi ve cai gi.
    """

    def __init__(self, ten: str, con_lai: int, exitstatus: str, khi_xong=None):
        self.ten = ten
        # `max(1, ...)`: mot tac vu phai duoc HOI it nhat mot lan moi ket thuc.
        # Cho phep 0 thi `khi_xong` khong bao gio chay, va the gioi that khong
        # bao gio doi — mot fake im lang noi doi ca hai phia.
        self.con_lai = max(1, int(con_lai))
        self.exitstatus = exitstatus
        self.khi_xong = khi_xong


class ProxmoxGia:
    """Một node Proxmox giả với đúng một máy.

    `buoc` = phai hoi bao nhieu lan thi tac vu moi xong; toi thieu 1. Mac dinh 2
    de giong the gioi that: cham. Dat 1 cho ca "nhanh".
    """

    def __init__(self, *, vmid: int = 200, dien: str = "running",
                 buoc: int = 2):
        self.vmid = int(vmid)
        self.dien = dien
        self.buoc = int(buoc)
        self.tac_vu: dict[str, TacVuGia] = {}
        self.da_goi: list[str] = []
        self.anh: list[dict] = []
        #: Đặt để mọi lần đọc trạng thái tác vụ ném lỗi — mô phỏng mạng chớp.
        self.doc_hong_con: int = 0
        #: Đặt để mọi lệnh ghi bị từ chối.
        self.tu_choi_ghi: bool = False
        self._dem = 0

    # ── nội bộ ──────────────────────────────────────────────────────────────

    def _upid(self, ten: str) -> str:
        self._dem += 1
        return f"UPID:pve:{ten}:{self._dem:04d}"

    def _nhan_viec(self, ten: str, *, exitstatus: str = "OK",
                   khi_xong=None, buoc: int | None = None) -> str:
        if self.tu_choi_ghi:
            raise ProxmoxError("Proxmox tra 500", status=500)
        self.da_goi.append(ten)
        upid = self._upid(ten)
        self.tac_vu[upid] = TacVuGia(
            ten, self.buoc if buoc is None else buoc, exitstatus, khi_xong)
        return upid

    def _dat_dien(self, dien: str):
        def _lam():
            self.dien = dien
        return _lam

    # ── đọc ─────────────────────────────────────────────────────────────────

    def trang_thai_tac_vu(self, upid: str) -> dict:
        if self.doc_hong_con > 0:
            self.doc_hong_con -= 1
            raise ProxmoxError("mang chop", status=502)
        tv = self.tac_vu.get(str(upid))
        if tv is None:
            raise ProxmoxError("khong co tac vu do", status=404)
        if tv.con_lai > 0:
            tv.con_lai -= 1
            if tv.con_lai > 0:
                return {"status": "running", "upid": upid}
            # Vua ve 0: tac vu ket thuc, va **chi toi luc nay** the gioi that moi
            # doi. Truoc do, moi thu van y nguyen.
            if tv.khi_xong is not None and tv.exitstatus == "OK":
                tv.khi_xong()
        return {"status": "stopped", "exitstatus": tv.exitstatus, "upid": upid}

    def trang_thai_vm(self, vmid: int) -> dict:
        if int(vmid) != self.vmid:
            raise ProxmoxError("khong co VM do", status=404)
        return {"status": self.dien, "vmid": self.vmid}

    def danh_sach_vm(self) -> list:
        return [{"vmid": self.vmid, "name": f"vps-{self.vmid}",
                 "status": self.dien}]

    def danh_sach_anh(self, vmid: int) -> list:
        return [dict(x) for x in self.anh]

    # ── ghi ─────────────────────────────────────────────────────────────────

    def bat(self, vmid: int) -> str:
        return self._nhan_viec("bat", khi_xong=self._dat_dien("running"))

    def tat_mem(self, vmid: int) -> str:
        return self._nhan_viec("tat_mem", khi_xong=self._dat_dien("stopped"))

    def tat_cung(self, vmid: int) -> str:
        return self._nhan_viec("tat_cung", khi_xong=self._dat_dien("stopped"))

    def chup_anh(self, vmid: int, ten: str, *, mo_ta: str = "") -> str:
        # Anh chi HIEN RA khi tac vu ket thuc tot — dung nhu that. Day la thu lam
        # cho phep kiem "don anh cu truoc khi anh moi xuat hien" co nghia: bo cai
        # nay di thi ban sai van xanh.
        def _hien():
            self.anh.append({"name": ten, "description": mo_ta})
        return self._nhan_viec("chup_anh", khi_xong=_hien)

    def xoa_anh(self, vmid: int, ten: str) -> str:
        if self.tu_choi_ghi:
            raise ProxmoxError("Proxmox tra 500", status=500)
        self.da_goi.append(f"xoa_anh:{ten}")
        self.anh = [x for x in self.anh if x.get("name") != ten]
        return self._upid("xoa_anh")

    def khoi_phuc_anh(self, vmid: int, ten: str) -> str:
        # Proxmox từ chối rollback một máy đang chạy khi ảnh không kèm RAM.
        # Đây LÀ luật mà bản cũ vi phạm, nên fake phải cưỡng chế nó — không thì
        # test "khôi phục khi máy chưa tắt" vẫn xanh.
        if self.dien != "stopped":
            raise ProxmoxError("VM is running", status=500)
        return self._nhan_viec("khoi_phuc_anh")

    def xoa(self, vmid: int, *, xoa_luon_dia: bool = True) -> str:
        return self._nhan_viec("xoa")

    def dat_cau_hinh(self, vmid: int, **cau_hinh):
        self.da_goi.append("dat_cau_hinh")
        return None

    # ── tiện ích cho test ───────────────────────────────────────────────────

    def hoan_tat_moi_tac_vu(self) -> None:
        """Ép mọi tác vụ đang chạy kết thúc ngay ở lần hỏi kế tiếp."""
        for tv in self.tac_vu.values():
            if tv.con_lai > 1:
                tv.con_lai = 1

    def them_anh(self, ten: str) -> None:
        self.anh.append({"name": ten})


def nhip_gia():
    """Nhịp giả: giấc ngủ **đẩy đồng hồ** thay vì chờ thật.

    ⚠️ Tiêm mỗi `ngu` là chưa đủ, và đó là một lỗi đã đo được: hàm thôi ngủ nhưng
       hạn chót vẫn tính theo `time.monotonic()`, nên mọi ca quá hạn quay tít một
       lõi CPU cho đủ 300 giây thật. Bộ test vẫn **xanh** — nó chỉ mất 301 giây.

    ⇒ Giấc ngủ và đồng hồ phải đi cùng nhau. Xem `tac_vu.Nhip`.
    """
    from apps.vps.services.tac_vu import Nhip

    dong_ho = [0.0]

    def ngu(giay: float) -> None:
        dong_ho[0] += float(giay)

    return Nhip(ngu=ngu, dong_ho=lambda: dong_ho[0])
