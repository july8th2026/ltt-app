"""`NodeDefinition` — khung nhìn DẪN XUẤT (spec §4.4), không lưu vào CSDL.

⭐ Ba nguồn (§4.5), không nguồn nào trùng: node lõi khai trong `nut_loi/`, node
   app đọc ToolSpec qua `cong_cu.tat_ca()`, node piece đọc catalog của runner.

⛔ Không sao chép trường nào của ToolSpec ra một bảng thứ hai. Cái giá của bảng
   thứ hai đã đo được: `test_967` đếm 11 hàng CHẾT trong bảng nhãn của Canvas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from platform_core.workflow import luoc_do
from platform_core.workflow.cong_cu import CongCu

KIND = ("trigger", "control", "data", "app", "ai", "connector", "subworkflow")
CATEGORY = ("TRIGGERS", "FLOW", "DATA", "NETWORK", "AI", "LTT_APPS",
            "CONNECTORS", "SUBWORKFLOWS")
QUYEN = frozenset({"network", "credential", "gpu", "filesystem", "subprocess"})

#: Lớp tài nguyên. Danh sách ĐÓNG: `registry.RESOURCE_KEYS` chốt các KHOÁ
#: nhưng không chốt giá trị của `class`, nên một `"GPU"` viết hoa hay `"gpu0"`
#: lọt vào sẽ không bao giờ khớp và scheduler xếp chỗ bằng mặc định — im lặng.
RESOURCE_CLASS = ("cpu", "gpu", "api")

#: Mã lỗi một node app công bố. Lấy TỪ `cau_noi.py` (`nop_job`, `ap_ket_qua`),
#: không khai lại theo trí nhớ.
MA_LOI_APP = ("dau_vao_sai", "vuot_tran_bao_gia", "provider_loi",
              "ket_qua_mo_ho", "bi_huy", "cong_cu_khong_con")


class LoiNut(ValueError):
    """Một định nghĩa node sai. Ném lúc DỰNG (khởi động / gọi palette), không
    đợi lúc chạy — chỗ nó lộ ra lúc chạy là chỗ đang tiêu tiền của khách."""


@dataclass(frozen=True)
class Gia:
    """`mien_phi` | `co_dinh(n)` | `theo_registry(job_type)` (spec §7.1)."""

    kieu: str
    so: int = 0
    job_type: str = ""

    @staticmethod
    def mien_phi() -> "Gia":
        return Gia("mien_phi")

    @staticmethod
    def co_dinh(n: int) -> "Gia":
        return Gia("co_dinh", so=int(n))

    @staticmethod
    def theo_registry(job_type: str) -> "Gia":
        return Gia("theo_registry", job_type=str(job_type))

    def sang_json(self) -> dict:
        return {"kieu": self.kieu, "so": self.so, "job_type": self.job_type}


@dataclass(frozen=True)
class NodeDefinition:
    type: str
    type_version: int
    kind: str
    category: str
    title: str
    description: str
    icon: str
    cong_vao: tuple
    cong_ra: tuple
    tham_so: dict
    thi_hanh: str                       # inline | job | run_con
    job_type: str = ""
    app_name: str = ""
    side_effect: str = "none"
    idempotency_key_fields: tuple = ()
    resource: dict = field(default_factory=dict)
    timeout_expr: str = ""
    retry_mac_dinh: dict = field(
        default_factory=lambda: {"max": 0, "backoff_s": 30})
    gia: Gia = field(default_factory=Gia.mien_phi)
    credential: tuple = ()
    quyen: frozenset = frozenset()
    mock: Optional[Callable[[dict], dict]] = None
    cho: tuple = ()
    ma_loi: tuple = ()
    #: Compiler hôm nay có biên dịch được `type` này không (`bien_dich._node`).
    #: Plan 02 chỉ có `app.*`; node lõi bật cờ này ở plan 04.
    publish_duoc: bool = False

    def __post_init__(self) -> None:
        if self.kind not in KIND:
            raise LoiNut(f"kind la: {self.kind!r} (chi {list(KIND)})")
        if self.category not in CATEGORY:
            raise LoiNut(f"category la: {self.category!r}")
        if self.thi_hanh not in ("inline", "job", "run_con"):
            raise LoiNut(f"thi_hanh la: {self.thi_hanh!r}")
        lop = str(self.resource.get("class", "")) if self.resource else ""
        if lop and lop not in RESOURCE_CLASS:
            raise LoiNut(
                f"resource.class la: {lop!r} (chi {list(RESOURCE_CLASS)})")
        thua = set(self.quyen) - QUYEN
        if thua:
            raise LoiNut(f"quyen la: {sorted(thua)}")


def _tieu_de(mo_ta: str, ten: str) -> str:
    """Câu đầu của mô tả app tự khai. Rỗng ⇒ suy từ tên tool.

    ⛔ KHÔNG dựng một bảng `{tên tool: nhãn}` trong nền tảng — đó chính là thứ
       `test_967` đang đếm hàng chết.
    """
    cau = str(mo_ta or "").split(". ")[0].strip().rstrip(".")
    return cau[:60] if cau else ten.replace(".", " ").replace("_", " ").title()


def tu_toolspec(cc: CongCu) -> NodeDefinition:
    """Node `app.*` từ MỘT `CongCu` (spec §4.5 nguồn 2). Không đọc lại registry."""
    lop = str((cc.resource or {}).get("class", "") or "")
    quyen = {"network"}
    if lop == "gpu":
        quyen.add("gpu")
    return NodeDefinition(
        type=f"app.{cc.ten}", type_version=int(cc.type_version),
        kind="app", category="LTT_APPS",
        title=_tieu_de(cc.mo_ta, cc.ten), description=str(cc.mo_ta or ""),
        icon=str(cc.icon or ""), app_name=str(cc.app_name or cc.app_slug),
        cong_vao=luoc_do.cong_vao(cc.params_schema,
                                  (cc.cong or {}).get("vao") or {}),
        cong_ra=luoc_do.cong_ra(cc.returns, (cc.cong or {}).get("ra") or {}),
        tham_so=luoc_do.sang_json_schema(cc.params_schema),
        thi_hanh="job", job_type=cc.job_type,
        side_effect=cc.side_effect,
        idempotency_key_fields=tuple(cc.idempotency_fields),
        resource=dict(cc.resource or {}),
        timeout_expr=str(cc.timeout_expr or ""),
        retry_mac_dinh={"max": int(cc.so_lan_thu or 0), "backoff_s": 30},
        gia=Gia.theo_registry(cc.job_type),
        # App node chạy như một job của nền tảng: khoá provider nằm ở
        # `api_pool`, không phải credential của khách (§9.1 là chuyện connector).
        credential=(), quyen=frozenset(quyen),
        mock=cc.mock, cho=("JOB",), ma_loi=MA_LOI_APP,
        publish_duoc=True)


__all__ = ["CATEGORY", "Gia", "KIND", "LoiNut", "MA_LOI_APP", "NodeDefinition",
           "QUYEN", "RESOURCE_CLASS", "tu_toolspec"]
