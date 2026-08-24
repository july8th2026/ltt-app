"""Bảng CSDL riêng của app VPS. Tiền tố `vps_` theo `MANIFEST.table_prefix`.

Năm bảng, và ranh giới giữa chúng không phải chuyện gọn gàng:

* `vps_gateway`   — **cổng vào**. Q104/V12 chốt khách tự chọn vùng (VN / Singapore
  / chỉ-cổng), nên đây là **nhiều bản ghi** chứ không phải một dải cổng cứng trong
  code. Thêm một vùng = thêm một dòng, không sửa code.
* `vps_ip`        — IP công khai riêng của một máy, kèm `vultr_id` để trả về được
  cho nhà cung cấp khi máy bị xoá. Tách khỏi `vps_instance` vì IP có vòng đời
  riêng: nó tồn tại ở nhà cung cấp trước khi gắn và sau khi gỡ.
* `vps_instance`  — chính cái máy khách thuê, và **`paid_until`** của nó.
* `vps_console_ve` — vé một-lần để mở console. Bảng chứ không phải bộ nhớ, vì tầng
  web chạy nhiều tiến trình.
* `vps_event`     — nhật ký vòng đời. Không phải log gỡ lỗi: đây là thứ trả lời
  "vì sao máy tôi bị tắt" khi khách hỏi, nên nó phải sống lâu hơn log ứng dụng.

## Vì sao `paid_until` nằm ở đây chứ không ở một bảng hoá đơn

Nền tảng chỉ có **một** sổ tiền: `credit`. Q98 đã giải đúng bài toán này cho Nexus
bằng một cột `paid_until` trên chính đối tượng được thu phí. Dựng thêm bảng
`vps_invoice` là dựng sổ tiền thứ hai, và hai sổ tiền là hai số dư lệch nhau.

## Vì sao cổng và IP có ràng buộc DUY NHẤT ở tầng CSDL

Cấp phát cổng là chỗ hai job chạy song song sẽ đụng nhau. Cách đúng không phải là
"đọc xem cổng nào trống rồi ghi" — giữa hai bước đó có một khoảng trống. Cách đúng
là **cứ INSERT, và coi `IntegrityError` là đường chạy bình thường** nghĩa là người
khác vừa giành trước. Đó là khuôn `platform_core/gpu_lease.py` đã chứng minh trong
production; ràng buộc dưới đây là thứ làm cho khuôn đó chạy được.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (BigInteger, Boolean, DateTime, Index, Integer, JSON,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


#: Trạng thái vòng đời của một máy. Chuỗi chứ không phải Enum của CSDL: thêm một
#: trạng thái không nên là một migration đổi kiểu trên PostgreSQL.
#:
#:   dang_tao   -> job provision đang chạy
#:   dang_chay  -> bình thường
#:   da_tat     -> khách tự tắt (vẫn tính tiền, đĩa vẫn giữ)
#:   bi_treo    -> hết credit hoặc bị treo vì lạm dụng (V8)
#:   dang_xoa   -> job destroy đang chạy
#:   da_xoa     -> đã xoá khỏi Proxmox; giữ bản ghi để trả lời khách và đối soát
#:   loi        -> job provision thất bại; cần người xem
TRANG_THAI = ("dang_tao", "dang_chay", "da_tat", "bi_treo",
              "dang_xoa", "da_xoa", "loi")

#: Vùng của cổng vào. `port` = không có IP riêng, chỉ được một cổng trên IP chung.
VUNG = ("vn", "sgp", "port")


class VpsGateway(Base):
    """Một cổng vào: nơi khách gõ địa chỉ để tới máy của họ.

    Đường về nhà là **WireGuard do phía nhà chủ động gọi ra** — nhờ vậy không cần
    mở cổng nào trên router VNPT, và IP động ở nhà không còn là vấn đề. Cột
    `wg_endpoint` ghi đầu bên kia của đường hầm đó.
    """

    __tablename__ = "vps_gateway"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ten: Mapped[str] = mapped_column(String(80), nullable=False)
    vung: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    #: IP công cộng của chính cổng — thứ khách nối tới khi mua gói chỉ-cổng.
    ip_cong_khai: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Tên miền ổn định trỏ tới cổng. Đổi nhà cung cấp mà khách không phải đổi gì.
    ten_mien: Mapped[str] = mapped_column(String(190), default="", nullable=False)
    wg_endpoint: Mapped[str] = mapped_column(String(190), default="", nullable=False)
    #: Id của chính cổng vào bên nhà cung cấp (Vultr `instances`). Cần nó để gắn
    #: Reserved IP. Tra theo nhãn mỗi lần là một vòng gọi API thừa và một chỗ để
    #: sai: đổi tên trên bảng điều khiển là app không tìm thấy nữa.
    nha_cung_cap_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Dải octet được phép cấp cho máy khách trong `subnet_cidr`. Đóng ở hai
    #: đầu. Thay cho dải cổng của mô hình cũ: từ 2026-08-24 **mỗi máy một IP
    #: công khai riêng**, không chia cổng nữa, nên thứ khan hiếm cần cấp phát
    #: là *địa chỉ trong mạng riêng*, không phải cổng.
    octet_dau: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    octet_cuoi: Mapped[int] = mapped_column(Integer, default=250, nullable=False)

    # ── Mạng riêng mà cổng vào này phục vụ ───────────────────────────────────
    #
    # Sáu cột dưới đây mô tả **trọn** mạng của một cổng vào, để thêm cổng thứ hai
    # là thêm một dòng chứ không phải sửa code (V12).
    #
    # Địa chỉ riêng nay được **cấp phát trực tiếp** (ràng buộc duy nhất trên
    # `vps_instance.ip_noi_bo`), không còn suy ra từ cổng. Mô hình cũ buộc hai
    # thứ vào nhau bằng một phép cộng để khỏi cấp phát hai lần; mô hình mới chỉ
    # có một thứ để cấp, nên phép cộng đó không còn lý do tồn tại.
    #: Bridge của Proxmox mà máy khách cắm vào (mạng cô lập, `bridge-ports none`).
    bridge: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    #: Mạng riêng, dạng CIDR — vd `10.50.0.0/24`.
    subnet_cidr: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    #: Gateway trong mạng đó — chính là host Proxmox, vd `10.50.0.1`.
    subnet_gw: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Resolver cấp cho khách. Cách nhau bằng dấu cách.
    dns: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    #: MTU ghim cho card của khách. 1420 là số ĐO THẬT qua đường hầm WireGuard —
    #: để mặc định 1500 thì gói lớn rơi im lặng, và triệu chứng là "web nào cũng
    #: vào được trừ vài trang", loại lỗi mất hàng giờ mới lần ra.
    mtu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Cổng này có bán được IP riêng không (phụ thuộc nhà cung cấp cho mua thêm IP).
    cho_phep_ip_rieng: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: False = còn tồn tại nhưng không cấp máy mới nữa (đang rút, hoặc dự phòng).
    dang_nhan_may_moi: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ghi_chu: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("ten", name="uq_vps_gateway_ten"),
    )


class VpsIp(Base):
    """Một địa chỉ IP công cộng thuộc một cổng, cấp riêng cho một máy.

    `instance_id` NULL = còn trống. Ràng buộc duy nhất trên `instance_id` là thứ
    ngăn hai job cùng gán một IP cho hai máy khác nhau.
    """

    __tablename__ = "vps_ip"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    gateway_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dia_chi: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Id của IP bên nhà cung cấp (Vultr `reserved-ips`). Thiếu nó thì khi máy
    #: bị xoá ta **không biết phải trả IP nào về**, và mỗi máy chết để lại
    #: $3/tháng chảy mãi.
    vultr_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Nhãn đặt bên nhà cung cấp — để đối chiếu khi cần dọn bằng tay.
    nhan: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: Giá bán thêm mỗi chu kỳ, VNĐ. 0 = IP đi kèm gói, không thu thêm.
    gia_thang_vnd: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("gateway_id", "dia_chi", name="uq_vps_ip_dia_chi"),
        # Một IP chỉ gắn được vào MỘT máy. NULL không tính vào UNIQUE ở cả
        # PostgreSQL lẫn SQLite, nên nhiều IP trống cùng tồn tại là hợp lệ.
        UniqueConstraint("instance_id", name="uq_vps_ip_instance"),
    )


class VpsInstance(Base):
    """Một máy ảo khách đang thuê.

    `vmid` là số hiệu VM trong Proxmox. Khách **không bao giờ** nhìn thấy nó —
    cũng như không thấy tên node hay bất cứ thứ gì của Proxmox. Cấp `vmid` cũng
    đi qua ràng buộc duy nhất vì hai job song song sẽ chọn trùng số.
    """

    __tablename__ = "vps_instance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ten: Mapped[str] = mapped_column(String(80), default="", nullable=False)

    plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    dia_them_gb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    os_id: Mapped[str] = mapped_column(String(32), nullable=False)

    gateway_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    vmid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Địa chỉ trong mạng riêng, vd `10.51.0.50`. NULL = chưa cấp.
    ip_noi_bo: Mapped[str | None] = mapped_column(String(64), nullable=True)

    trang_thai: Mapped[str] = mapped_column(
        String(16), default="dang_tao", nullable=False, index=True)
    #: Lời giải thích cho khách khi trạng thái là `loi` hoặc `bi_treo`.
    ly_do: Mapped[str] = mapped_column(Text, default="", nullable=False)

    #: Thuê bao trả tới lúc nào. NULL = chưa thu chu kỳ nào (khuôn Q98).
    paid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Mốc xoá vĩnh viễn sau khi treo (V8: treo ngay, xoá sau 7 ngày).
    xoa_sau: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        # Hai job song song không được cấp trùng VMID. NULL (chưa cấp) không
        # tính vào UNIQUE nên nhiều máy `dang_tao` cùng lúc là hợp lệ.
        UniqueConstraint("vmid", name="uq_vps_instance_vmid"),
        # Và ĐÂY là trọng tài của việc cấp địa chỉ riêng: cứ INSERT/UPDATE,
        # `IntegrityError` nghĩa là worker khác vừa giành trước. Không có nó thì
        # hai máy cùng nhận `10.51.0.50` và khách gõ đúng địa chỉ lại rơi vào
        # máy người lạ — hỏng im lặng, không lỗi nào được ghi ra.
        UniqueConstraint("gateway_id", "ip_noi_bo", name="uq_vps_instance_ip"),
        # Trang "máy của tôi" luôn lọc theo (chủ) + (chưa xoá).
        Index("ix_vps_instance_user_trangthai", "user_id", "trang_thai"),
        # Vòng thu phí quét theo hạn thanh toán.
        Index("ix_vps_instance_paid_until", "paid_until"),
    )


class VpsConsoleVe(Base):
    """Vé một-lần để mở console của một máy qua proxy WebSocket của mình.

    ## Vì sao phải là BẢNG chứ không phải một dict trong bộ nhớ

    Tầng web chạy **nhiều tiến trình**. Vé cấp ở tiến trình A mà WebSocket rơi
    vào tiến trình B thì console không bao giờ mở được — và triệu chứng là "lúc
    được lúc không", đúng loại lỗi tốn nhiều ngày nhất để lần ra.

    ## Vì sao lưu BĂM chứ không lưu vé

    Cùng lý do `sessions.id` lưu SHA-256 thay vì token thô (P0-5): ai đọc được
    CSDL — bản sao lưu, một truy vấn lỡ tay, một lần dump — thì đọc được vé, và
    vé là quyền xem màn hình máy của khách.

    ## `da_dung_luc` là thứ làm cho nó DÙNG-MỘT-LẦN

    Tiêu vé bằng `UPDATE ... WHERE da_dung_luc IS NULL` rồi đếm số dòng đổi: hai
    request cùng cầm một vé thì đúng **một** thắng. Kiểm rồi mới ghi (đọc, so,
    ghi) là để hở một khe giữa ba bước đó.
    """

    __tablename__ = "vps_console_ve"

    #: SHA-256 hex của vé. KHÔNG phải chính vé.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False, index=True)
    da_dung_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)


class VpsEvent(Base):
    """Nhật ký vòng đời của một máy — thứ trả lời "vì sao máy tôi bị tắt".

    Khác log ứng dụng: log xoay vòng rồi mất, còn cái này phải còn khi khách hỏi
    sau ba tháng. Vì thế nó là bảng, không phải dòng log.
    """

    __tablename__ = "vps_event"

    # `with_variant(Integer, "sqlite")` KHÔNG phải chi tiết vụn: SQLite chỉ tự
    # tăng cho đúng kiểu `INTEGER PRIMARY KEY`, còn `BIGINT` thì không — mọi
    # INSERT sẽ chết vì `NOT NULL constraint failed`. Production chạy PostgreSQL
    # (cần BIGINT vì bảng này chỉ thêm, không bao giờ xoá), nhưng bộ test chạy
    # SQLite; thiếu dòng này thì tầng nhật ký không có test nào đi qua được.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True, autoincrement=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    loai: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Ai gây ra: user id, "he_thong" (vòng thu phí), hoặc "admin:<email>".
    boi: Mapped[str] = mapped_column(String(190), default="", nullable=False)
    chi_tiet: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False, index=True)
