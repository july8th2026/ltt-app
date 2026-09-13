"""Bảng CSDL riêng của app VPS. Tiền tố `vps_` theo `MANIFEST.table_prefix`.

Sáu bảng, và ranh giới giữa chúng không phải chuyện gọn gàng:

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
* `vps_thao_tac`  — **một mutation dài đang chạy trên một máy** (VPS V2). Khác
  `vps_event` ở chỗ sự kiện là *đã xảy ra rồi*, còn thao tác là *đang xảy ra* —
  nó có hạn chót, có UPID để nối lại, và nó kết thúc. Ép nhật ký làm hàng đợi
  là mất cả hai: nhật ký thì không được xoá, hàng đợi thì phải dọn được.

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

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime,
                        ForeignKey, Index, Integer, JSON, String, Text,
                        UniqueConstraint, text)
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


class VpsInfrastructureProfile(Base):
    """Một tổ hợp compute + public-IP + gateway có vòng đời độc lập.

    Các JSON chỉ chứa cấu hình không bí mật, riêng cho từng backend. Trường dùng
    để chọn/ràng buộc vẫn là cột quan hệ; credential chỉ là tên tham chiếu tới
    canonical secret store.
    """

    __tablename__ = "vps_infrastructure_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(
        String(32), default="production", nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="STANDBY", nullable=False, index=True)
    accept_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    compute_backend_type: Mapped[str] = mapped_column(String(32), nullable=False)
    public_ip_backend_type: Mapped[str] = mapped_column(String(32), nullable=False)
    gateway_backend_type: Mapped[str] = mapped_column(String(32), nullable=False)
    compute_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    network_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provider_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    credential_ref: Mapped[str] = mapped_column(
        String(128), default="", nullable=False)
    config_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    last_health_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE','DRAINING','STANDBY','DISABLED')",
            name="ck_vps_profile_status"),
        CheckConstraint(
            "status = 'ACTIVE' OR accept_new IS FALSE",
            name="ck_vps_profile_accept_only_active"),
        CheckConstraint(
            "is_default IS FALSE OR (status = 'ACTIVE' AND accept_new IS TRUE)",
            name="ck_vps_profile_default_active"),
        Index(
            "uq_vps_profile_one_default", "is_default", unique=True,
            sqlite_where=text("is_default = 1"),
            postgresql_where=text("is_default IS TRUE")),
        Index(
            "ix_vps_profile_selector", "region", "status", "accept_new"),
    )


class VpsProfileHealth(Base):
    """Một quan sát health của đúng một component trên đúng một profile."""

    __tablename__ = "vps_profile_health"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    infrastructure_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vps_infrastructure_profile.id", ondelete="CASCADE"),
        nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('UNKNOWN','STALE','HEALTHY','DEGRADED','CRITICAL')",
            name="ck_vps_profile_health_status"),
        Index(
            "ix_vps_profile_health_latest", "infrastructure_profile_id",
            "component", "observed_at"),
    )


class VpsGateway(Base):
    """Một cổng vào: nơi khách gõ địa chỉ để tới máy của họ.

    Đường về nhà là **WireGuard do phía nhà chủ động gọi ra** — nhờ vậy không cần
    mở cổng nào trên router VNPT, và IP động ở nhà không còn là vấn đề. Cột
    `wg_endpoint` ghi đầu bên kia của đường hầm đó.
    """

    __tablename__ = "vps_gateway"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    infrastructure_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vps_infrastructure_profile.id", ondelete="RESTRICT"),
        nullable=True, index=True)
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
    infrastructure_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vps_infrastructure_profile.id", ondelete="RESTRICT"),
        nullable=True, index=True)
    gateway_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dia_chi: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Id của IP bên nhà cung cấp (Vultr `reserved-ips`). Thiếu nó thì khi máy
    #: bị xoá ta **không biết phải trả IP nào về**, và mỗi máy chết để lại
    #: $3/tháng chảy mãi.
    vultr_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Định danh generic bên backend. `vultr_id` được giữ trong migration V4 đầu
    #: để rollback và để chứng minh legacy ownership, không còn là authority mới.
    backend_resource_id: Mapped[str] = mapped_column(
        String(128), default="", nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), default="QUARANTINED", nullable=False, index=True)
    reservation_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    bound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    billing_mode: Mapped[str] = mapped_column(String(24), default="", nullable=False)
    monthly_cost_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
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
        UniqueConstraint("reservation_token", name="uq_vps_ip_reservation_token"),
        CheckConstraint(
            "state IN ('FREE','RESERVED','BOUND','QUARANTINED')",
            name="ck_vps_ip_state"),
    )


class VpsInstance(Base):
    """Một máy ảo khách đang thuê.

    `vmid` là số hiệu VM trong Proxmox. Khách **không bao giờ** nhìn thấy nó —
    cũng như không thấy tên node hay bất cứ thứ gì của Proxmox. Cấp `vmid` cũng
    đi qua ràng buộc duy nhất vì hai job song song sẽ chọn trùng số.
    """

    __tablename__ = "vps_instance"

    def __init__(self, **kw):
        """Dựng xong là **nhất quán ngay**, không chờ ai nhớ gọi thêm gì.

        `VpsInstance(trang_thai="dang_chay")` phải cho ra `vong_doi="hoat_dong"`,
        không phải giá trị mặc định `"dang_tao"` của cột. Không có bước này thì
        mọi chỗ dựng máy bằng mã cũ — kể cả trong test — đẻ ra một hàng mà hình
        chiếu và mô hình nói hai điều khác nhau, và cái sai đó chỉ lộ ra ở lần
        `dat()` kế tiếp, cách xa chỗ gây ra nó.

        Hàng **đọc từ CSDL** không đi qua đây (SQLAlchemy dựng chúng bằng
        `__new__`), nên lớp tương thích cho hàng cũ nằm ở `chuan_hoa()` bên trong
        `dat()`. Hai chỗ, hai loại đối tượng, cùng một bảng ánh xạ.
        """
        super().__init__(**kw)
        from apps.vps import trang_thai_may
        trang_thai_may.chuan_hoa(self)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ten: Mapped[str] = mapped_column(String(80), default="", nullable=False)

    plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    dia_them_gb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    os_id: Mapped[str] = mapped_column(String(32), nullable=False)

    #: NULL chỉ hợp lệ cho legacy row chưa đủ evidence. Mọi create V4 phải gọi
    #: `profiles.pin_instance()` trước khi enqueue/external mutation.
    infrastructure_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vps_infrastructure_profile.id", ondelete="RESTRICT"),
        nullable=True, index=True)
    profile_resolution_state: Mapped[str] = mapped_column(
        String(16), default="NEEDS_REVIEW", nullable=False, index=True)

    gateway_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    vmid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Địa chỉ trong mạng riêng, vd `10.51.0.50`. NULL = chưa cấp.
    ip_noi_bo: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: ⚠️ **HÌNH CHIẾU, không phải nguồn sự thật.** Từ VPS V2 cột này được tính
    #: ra từ năm cột dưới, ở đúng một chỗ (`trang_thai_may.chieu`), và chỉ được
    #: ghi qua `trang_thai_may.dat()`. Nó ở lại vì 18 tệp test, 7 template và bốn
    #: bảng tra trong `nhan.py` đọc nó — xoá là viết lại cả app mà không giảm rủi
    #: ro nào. Gán thẳng cột này ở nơi khác là dựng nguồn sự thật thứ hai.
    trang_thai: Mapped[str] = mapped_column(
        String(16), default="dang_tao", nullable=False, index=True)

    #: Vòng đời **nghiệp vụ**: máy này còn là khách hàng đang phục vụ không.
    #: `bi_treo` ở đây là khái niệm TIỀN — nó phải sống sót qua mọi thứ xảy ra
    #: với nguồn điện của máy.
    vong_doi: Mapped[str] = mapped_column(
        String(16), default="dang_tao", nullable=False, index=True)
    #: Khách **muốn** máy bật hay tắt. Chỉ `chay`/`tat` — không có "không biết".
    dien_mong_muon: Mapped[str] = mapped_column(
        String(16), default="chay", nullable=False)
    #: Ta **đo được** gì trên hypervisor. `khong_ro` là một giá trị THẬT: nó
    #: nghĩa là đã hỏi và không có câu trả lời, khác hẳn `tat`.
    dien_quan_sat: Mapped[str] = mapped_column(
        String(16), default="khong_ro", nullable=False)
    #: Tác vụ dài đang chạy dở. Rỗng = không có gì. Đây là thứ trả lời câu
    #: "vì sao trang không đổi gì sau khi tôi bấm".
    tac_vu: Mapped[str] = mapped_column(
        String(16), default="", nullable=False)
    #: Sức khoẻ suy ra từ lần đo gần nhất.
    suc_khoe: Mapped[str] = mapped_column(
        String(16), default="khong_ro", nullable=False)
    #: Lần đo gần nhất lúc nào. NULL = chưa đo lần nào — và với việc hiểu hiện
    #: tại thì "chưa đo" ngang bằng "đo từ tuần trước": không biết gì cả.
    quan_sat_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    #: Lời giải thích cho khách khi trạng thái là `loi` hoặc `bi_treo`.
    ly_do: Mapped[str] = mapped_column(Text, default="", nullable=False)

    #: Bị cách ly vì lạm dụng từ lúc nào. NULL = không bị.
    #:
    #: ⚠️ **Khác `bi_treo`**, và khác một cách quan trọng. `bi_treo` là khái niệm
    #: TIỀN: nó đặt luôn mốc `xoa_sau` bảy ngày. Dùng nó cho lạm dụng là ghi vào
    #: sổ rằng khách nợ tiền — sai sự thật — và xoá máy của một khách đang trả
    #: tiền đầy đủ sau một tuần. Cách ly thì cắt mạng, giữ đĩa, và gỡ lại được.
    #: Xem `services/cach_ly.py`.
    cach_ly_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Vì sao. Bắt buộc khi cách ly — đây là thứ người ta đọc lại sau ba tháng.
    cach_ly_ly_do: Mapped[str] = mapped_column(Text, default="", nullable=False)

    #: Thuê bao trả tới lúc nào. NULL = chưa thu chu kỳ nào (khuôn Q98).
    paid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Mốc xoá vĩnh viễn sau khi treo (V8: treo ngay, xoá sau 7 ngày).
    xoa_sau: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # ── Băng thông ───────────────────────────────────────────────────────────
    #
    # `bang_thong_byte` là số đã dùng **trong chu kỳ hiện tại**; nó về 0 mỗi lần
    # thu một chu kỳ mới. Hai cột `moc_*` giữ lần đọc bộ đếm gần nhất trên router
    # để tính phần chênh lệch — bộ đếm của `nft` về 0 khi router khởi động lại,
    # nên lấy hiệu mà không xử lý việc đó sẽ cho ra số ÂM, và số âm cộng vào tổng
    # là **hoàn lại băng thông** cho khách. Xem `apps/vps/bang_thong.py`.
    bang_thong_byte: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False)
    bang_thong_moc_len: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False)
    bang_thong_moc_xuong: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False)
    #: Lần chụp ảnh gần nhất. NULL = chưa chụp lần nào (máy vừa tạo).
    sao_luu_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    #: Đang bị hãm tốc vì vượt hạn mức. Lưu ở đây (không chỉ trên router) để
    #: trang của khách nói được lý do máy chậm, thay vì để họ tự đoán.
    bi_giam_toc: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)

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
        CheckConstraint(
            "profile_resolution_state IN ('NEEDS_REVIEW','PINNED')",
            name="ck_vps_instance_profile_resolution"),
    )


class VpsExternalMutation(Base):
    """Intent/read-back bền cho một mutation ngoài có thể thành công một phần."""

    __tablename__ = "vps_external_mutation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    operation_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vps_infrastructure_profile.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), default="INTENT", nullable=False, index=True)
    request_fingerprint: Mapped[str] = mapped_column(
        String(64), default="", nullable=False)
    external_ref: Mapped[str] = mapped_column(String(190), default="", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str] = mapped_column(
        String(64), default="", nullable=False)
    last_error_detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    compensated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_vps_external_mutation_idem"),
        CheckConstraint(
            "state IN ('INTENT','REQUESTED','OBSERVED','COMPENSATED','FAILED','NEEDS_REVIEW')",
            name="ck_vps_external_mutation_state"),
        Index(
            "ix_vps_external_mutation_instance_step", "instance_id", "step"),
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
    #: Cổng VNC mà Proxmox vừa mở cho phiên này, và vé của chính Proxmox.
    #:
    #: Vé Proxmox phải giữ ở đây vì nó cần cho HAI chỗ: query `vncticket` của
    #: URL WebSocket (phía server dùng), và **mật khẩu VNC** trong bước bắt tay
    #: RFB (phía trình duyệt dùng). `vncproxy` khác `termproxy`: nó KHÔNG nhận
    #: một dòng `user:ticket` mở đầu — chèn dòng đó vào là làm hỏng luồng nhị
    #: phân VNC và Proxmox đóng kết nối ngay, không nói gì.
    #:
    #: Dòng này bị **xoá ngay khi tiêu vé**, nên vé Proxmox nằm trong CSDL nhiều
    #: nhất là %(giay)s giây.
    cong: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Vé `vncproxy` của Proxmox. **`Text`, không phải `String(255)`.**
    #: Vé thật là một chứng chỉ có chữ ký và dài hơn 255 ký tự — đặt trần độ dài
    #: thì Postgres từ chối cả câu INSERT và console trả **500** cho mọi máy.
    #: SQLite không cưỡng chế độ dài `VARCHAR`, nên bộ test đi qua sạch sẽ trong
    #: khi trang thật hỏng hoàn toàn; chỉ mở trình duyệt mới thấy (quy tắc 5).
    pve_ve: Mapped[str] = mapped_column(Text, default="", nullable=False)
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


class VpsThaoTac(Base):
    """Mot mutation dai tren MOT may: ai bao, muon gi, toi dau roi, ket qua sao.

    ## Vi sao khong tai dung `Job`

    Hai vong doi khac nhau, va gop chung lai lam mat ca hai.

    `Job` tra loi *"luot viec nay cua worker da xong chua"*. No co the duoc thu
    lai nhieu lan, va **moi lan la mot dong `Job` khac**. Thao tac tra loi
    *"cai may nay dang bi lam gi, ai bao, toi dau roi"* — no song **xuyen qua**
    nhieu lan thu, va no la thu giao dien hien cho khach.

    Gop lam mot thi hoac la khach thay ba dong "dang khoi dong lai" cho mot lan
    bam nut, hoac la mat dau vet cua nhung lan thu that bai. Ca hai deu te.

    ⚠️ Nhung KHONG dung hang doi thu hai: thao tac **chay bang** job cua nen tang
    va **duoc serialize bang** lease `vps-may:{id}` da co. Xem ADR-02.

    ## `khoa_idem` — chong bam hai lan, va chong hon the

    Khoa idempotency la thu phan biet *"khach bam hai lan"* voi *"khach that su
    muon khoi dong lai hai lan"*. Bam hai lan trong cung mot phut sinh cung mot
    khoa ⇒ lan thu hai tra ve chinh thao tac dang chay, khong tao them gi.

    No cung chong duoc thu ma trong hon nhieu: **worker chet roi chay lai**.
    Lan chay thu hai tim thay thao tac cu qua khoa, doc `upid` da luu, va **noi
    lai vao tac vu dang chay** thay vi ban them mot lenh nua vao Proxmox.
    """

    __tablename__ = "vps_thao_tac"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False,
                                             index=True)
    #: Ma trong `trang_thai_may.TAC_VU` — cung bang tu vung voi cot `tac_vu`
    #: tren `vps_instance`, khong phai mot bang thu hai.
    loai: Mapped[str] = mapped_column(String(16), nullable=False)
    #: user id, "he_thong" (vong bao tri), hoac "admin:<email>".
    boi: Mapped[str] = mapped_column(String(190), default="", nullable=False)
    #: NULL = thao tac nay khong chong trung (vd vong bao tri tu nop).
    #:
    #: ⚠️ **NULL chu khong phai chuoi rong**, va day khong phai chuyen phong
    #: cach. Chuoi rong THAM GIA vao rang buoc duy nhat, nen `''` va vao `''`:
    #: mot may se chi bao gio co duoc **mot** thao tac khong khoa trong ca doi
    #: no. NULL thi khong tinh vao UNIQUE — cung khuon voi `uq_vps_instance_vmid`
    #: (nhieu may `dang_tao` cung luc deu co `vmid` NULL va deu hop le).
    #: `tests/test_552` co mot ca ghim dieu nay.
    khoa_idem: Mapped[str | None] = mapped_column(String(64), nullable=True,
                                                  default=None)

    #: cho | dang_chay | xong | hong | qua_han | huy
    #:
    #: ⚠️ **`tinh_trang` chu khong `trang_thai`**, va do khong phai chuyen phong
    #: cach. `VpsInstance.trang_thai` la mot HINH CHIEU chi duoc ghi qua
    #: `trang_thai_may.dat()` (ADR-01), va co mot phep quet canh dieu do. Hai cot
    #: trung ten thi phep quet ay khong phan biet duoc `op.trang_thai = XONG`
    #: (hop le) voi `may.trang_thai = "dang_chay"` (bug) — no se hoac bao dong
    #: gia, hoac bi noi long roi bo lot ca that.
    #:
    #: Bang nay moi hoan toan (VPS V2) va chua chay o dau, nen doi ten khong ton
    #: gi. Dat ten trung roi day phep quet phai thong minh hon la tra tien mai.
    tinh_trang: Mapped[str] = mapped_column(String(16), default="cho",
                                            nullable=False, index=True)
    #: UPID cua Proxmox, moi dong mot cai. `Text` chu khong `String(n)`: mot
    #: thao tac nhieu buoc (khoi dong lai = tat + bat) sinh nhieu UPID, va cat
    #: bot chuoi nao la mat dung duong noi lai vao tac vu do.
    upid: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lan_thu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Buoc con dang chay, vd "cho may tat". Cho khach doc, nen viet tieng nguoi.
    buoc: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    #: Anh chieu dien: truoc khi lam / muon toi / do duoc sau khi xong.
    #: Ba cot chu khong mot: khong co `dien_truoc` thi khong khoi phuc duoc y
    #: dinh ban dau sau mot lan khoi phuc anh chup.
    dien_truoc: Mapped[str] = mapped_column(String(16), default="",
                                            nullable=False)
    dien_mong_doi: Mapped[str] = mapped_column(String(16), default="",
                                               nullable=False)
    dien_sau: Mapped[str] = mapped_column(String(16), default="",
                                          nullable=False)

    #: Ma loi co CAU TRUC (`tac_vu_qua_han`, `dien_khong_dat`…), khong phai mot
    #: cau tieng Anh. Ma thi dem duoc va canh bao duoc; cau thi khong.
    ma_loi: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    chi_tiet_loi: Mapped[str] = mapped_column(Text, default="", nullable=False)

    tao_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False, index=True)
    bat_dau_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    #: Han chot. Qua moc nay ma van `dang_chay` thi vong bao tri quet no thanh
    #: `qua_han` — day la duong phuc hoi khi mot worker chet giua chung, va no
    #: la ly do cot nay khong duoc phep NULL cho thao tac dang chay.
    han_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    ket_thuc_luc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Hai lan bam sinh cung khoa ⇒ INSERT thu hai chet vi rang buoc nay, va
        # do la **duong chay binh thuong**: nguoi goi bat `IntegrityError` roi
        # tra ve thao tac dang co. Cung khuon voi `uq_vps_instance_ip`.
        UniqueConstraint("instance_id", "khoa_idem",
                         name="uq_vps_thao_tac_idem"),
        # Trang may hoi "co gi dang chay tren may nay khong" moi lan mo.
        Index("ix_vps_thao_tac_may_tinhtrang", "instance_id", "tinh_trang"),
    )
