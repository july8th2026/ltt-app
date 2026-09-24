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

#: Job type của node `piece.*`: chúng chạy trên **runner Node**, không qua
#: registry ToolSpec của nền tảng. Một hằng vì hai chỗ nói về nó
#: (`tu_piece` và `__post_init__`), và vì nó là RANH GIỚI giữa hai bộ thi
#: hành chứ không phải một cái tên cho đẹp.
JOB_TYPE_PIECE = "workflow.piece"

#: Job type của node connector **Python native** (`connector.youtube.upload`,
#: spec §11.6). Nó cũng không bọc ToolSpec nào — nhưng vì lý do KHÁC hẳn
#: `piece.*`: piece chạy trên runner Node, còn node này chạy trong worker của
#: ta bằng `httpx`. Hai bộ thi hành khác nhau ⇒ hai hằng, ⛔ không gộp tên.
#:
#: ⚠️ Nó tồn tại vì piece YouTube của Activepieces **không có action upload**
#:    (tra ở tag 0.90.2, kiểm lại 24/09): `download-caption, get-channel,
#:    get-video, list-captions, list-comments, list-playlist-items,
#:    list-playlists, search`. Đây là ca *"dùng lại trước, tự viết sau"* trả
#:    lời **có được tự viết**.
JOB_TYPE_CONNECTOR = "workflow.connector"

#: Job type **được miễn** khai `ten_toolspec`. ⛔ Tập ĐÓNG, và miễn theo **bộ
#: thi hành** chứ không theo tên node. Một bộ thi hành thứ ba xuất hiện mà
#: không khai gì sẽ ném ở `__post_init__` — đúng như mong muốn.
JOB_TYPE_KHONG_TOOLSPEC = frozenset({JOB_TYPE_PIECE, JOB_TYPE_CONNECTOR})

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
    #: Tên ToolSpec trong registry mà node này **bọc** (`CongCu.ten`).
    #:
    #: 🔴 KHAI TƯỜNG MINH, ⛔ KHÔNG SUY RA. Cách "thông minh" là tra ngược
    #:    `job_type → tên tool`. Đo trên registry hôm nay (19 tool): **ba**
    #:    `job_type` bị hai tool dùng chung (`prompt_ai_ommi.generate`,
    #:    `taoanh.generate`, `upscalevideo.render`). Một tra ngược đúng hôm
    #:    nay và sai **im lặng** vào ngày ai đó thêm tool thứ hai trên
    #:    `ltt_llm.chat` — nó chọn tool nào thì tuỳ thứ tự dict.
    #:
    #: Bắt buộc khi `thi_hanh == "job"` (xem `__post_init__`).
    ten_toolspec: str = ""
    #: HẬU KIỂM kết quả job, chạy **trước** khi cầu nối coi là SUCCEEDED:
    #: `(result, params) -> (trang_thai, ma_loi, chi_tiet)`.
    #:
    #: 🔴 Vì sao node tự khai chứ không phải cầu nối tự biết: `job.status`
    #:    SUCCEEDED **không** đảm bảo kết quả dùng được. Ca đã đo trên máy B
    #:    (10–12/09, `nut_loi/ai_loi.py`): HTTP 200, job SUCCEEDED,
    #:    `content` RỖNG. Với `app.image.generate` thì "job xong = có tệp"
    #:    vẫn đúng; với `text.chat` thì không.
    #:
    #: ⛔ Để cầu nối `if type.startswith("ai.")` là hardcode tên không gian
    #:    trong `platform_core/` (Global Constraint), **và** bắt mọi loại
    #:    node mới cần hậu kiểm phải sửa lại chính hàm đang giữ sổ tiền.
    hau_kiem: Optional[Callable[[dict, dict], tuple]] = None
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
        if self.thi_hanh == "job" and not self.ten_toolspec \
                and self.job_type not in JOB_TYPE_KHONG_TOOLSPEC:
            # ⛔ Ném LÚC DỰNG (tức lúc `import`, chỗ người viết node nhìn
            #    thấy ngay), không đợi lúc chạy — "chỗ nó lộ ra lúc chạy là
            #    chỗ đang tiêu tiền của khách" (xem `LoiNut`).
            #
            # ⚠️ NGOẠI LỆ DUY NHẤT là `piece.*`, và nó KHÔNG phải một ngoại
            #    lệ theo TÊN mà theo **bộ thi hành**: node piece chạy trên
            #    runner Node (`JOB_TYPE_PIECE`), không đi qua registry
            #    ToolSpec, nên không có ToolSpec nào để khai. `cau_noi` cũng
            #    từ chối `piece.*` bằng `LoiTienTo` cho tới khi plan 08 mở
            #    đường riêng cho chúng.
            #
            # ⛔ Một bộ thi hành THỨ BA xuất hiện mà không khai gì sẽ rơi
            #    vào nhánh này và chết ở `import` — đúng như mong muốn.
            #    `test_1789::test_banh_coc_moi_node_job_khai_ten_CO_THAT…`
            #    ghim rằng tập ngoại lệ đúng bằng `JOB_TYPE_KHONG_TOOLSPEC`.
            raise LoiNut(
                f"{self.type!r} khai thi_hanh='job' nhung thieu "
                "`ten_toolspec` — cau noi job khong suy duoc ten ToolSpec "
                "tu `type` cho mot khong gian ten khong phai `app.`")


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
        thi_hanh="job", job_type=cc.job_type, ten_toolspec=str(cc.ten),
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


def _nguon_piece_rong() -> list:
    """Khe cắm cho plan 08. ⛔ Không đoán đường dẫn `catalog.json` ở đây: tệp
    đó sinh lúc build và chỉ tồn tại sau khi runner được dựng."""
    return []


#: Plan 08 gán lại bằng hàm đọc `connector_runner/catalog.json`.
NGUON_PIECE: Callable[[], list] = _nguon_piece_rong


def tu_piece(muc: dict) -> NodeDefinition:
    """Node `piece.*` từ một mục catalog (spec §4.5 nguồn 3)."""
    auth = tuple(str(a) for a in (muc.get("auth") or ()))
    quyen = {"network"} | ({"credential"} if auth else set())
    # ⭐ `kind` DO CATALOG KHAI, ⛔ không cứng `"connector"`: một trigger
    #    POLLING của piece là một điểm BẮT ĐẦU đồ thị, và Canvas vẽ nó ở nhóm
    #    TRIGGERS. Một trigger nằm trong nhóm CONNECTORS thì người soạn không
    #    tìm thấy nó ở chỗ họ tìm mọi trigger khác — và họ sẽ kết luận là
    #    "không có trigger Sheets", đúng lúc nó vừa có.
    kind = str(muc.get("kind") or "connector")
    return NodeDefinition(
        type=str(muc["type"]), type_version=int(muc.get("type_version", 1) or 1),
        kind=kind,
        category="TRIGGERS" if kind == "trigger" else "CONNECTORS",
        title=str(muc.get("title") or muc["type"]),
        description=str(muc.get("description") or ""),
        icon=str(muc.get("icon") or ""),
        cong_vao=luoc_do.cong_vao(muc.get("params") or {},
                                  (muc.get("cong") or {}).get("vao") or {}),
        cong_ra=luoc_do.cong_ra(muc.get("returns") or {},
                                (muc.get("cong") or {}).get("ra") or {}),
        tham_so=luoc_do.sang_json_schema(muc.get("params") or {}),
        # ⛔ KHÔNG khai `ten_toolspec`, và đó là ĐÚNG: node piece bọc một
        #    *piece*, không bọc ToolSpec nào. `__post_init__` miễn cho nó
        #    theo `JOB_TYPE_PIECE` — tức theo BỘ THI HÀNH, không theo tên.
        #    Hôm nay `cau_noi.nop_job` vẫn từ chối `piece.*` bằng
        #    `LoiTienTo`; plan 08 phải mở đường riêng cho runner Node.
        thi_hanh="job", job_type=JOB_TYPE_PIECE,
        side_effect=str(muc.get("side_effect") or "external"),
        gia=Gia.co_dinh(int(muc.get("gia", 0) or 0)),
        credential=auth, quyen=frozenset(quyen),
        cho=("JOB",), ma_loi=MA_LOI_APP,
        publish_duoc=False)


def chua_du_hop_dong(cong_cu: dict) -> dict:
    """`{tên tool: [trường còn thiếu]}` — spec §4.5 *"khai đủ side_effect,
    idempotency, resource"*.

    ⚠️ `side_effect` **không đo được ở đây**: nó có mặc định `"external"` trong
       `ToolSpec`, nên một tool khai tường minh `"external"` và một tool quên
       khai trông giống hệt nhau. Phép đếm này chỉ nói về `idempotency` và
       `resource` — xem mục "Spec lệch mã thật" của plan 02.
    """
    ra: dict[str, list] = {}
    for ten, cc in (cong_cu or {}).items():
        thieu = []
        if not cc.idempotency_fields:
            thieu.append("idempotency")
        if not cc.resource:
            thieu.append("resource")
        if thieu:
            ra[ten] = thieu
    return ra


def tat_ca(*, cong_cu: Optional[dict] = None,
           nguon_piece: Optional[Callable[[], list]] = None) -> dict:
    """Hợp ba nguồn. Trùng `type` ⇒ `LoiNut` (spec §4.5)."""
    from platform_core.workflow import cong_cu as _nguon
    from platform_core.workflow import nut_loi

    ra: dict[str, NodeDefinition] = dict(nut_loi.tat_ca())
    cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
    chua_du = chua_du_hop_dong(cc_all)
    for ten, cc in cc_all.items():
        if not cc.workflow or ten in chua_du:
            continue
        nd = tu_toolspec(cc)
        if nd.type in ra:
            raise LoiNut(f"trung type giua hai nguon: {nd.type!r}")
        ra[nd.type] = nd
    for muc in (nguon_piece or NGUON_PIECE)():
        nd = tu_piece(muc)
        if nd.type in ra:
            raise LoiNut(f"trung type giua hai nguon: {nd.type!r}")
        ra[nd.type] = nd
    return ra


def type_version_thieu(db, *, dinh_nghia: Optional[dict] = None) -> list:
    """Node của version ĐÃ PUBLISH trỏ tới `type@version` registry không còn.

    ⭐ Đọc bảng chỉ mục `workflow_version_node` (dẫn xuất của `graph`, sinh ở
       `dinh_nghia._sinh_chi_muc`) chứ không duyệt JSON: một truy vấn SQL cho
       toàn hệ thống, và nó chạy được trên PostgreSQL production.

    🔑 RANH GIỚI LẤY NGUYÊN VĂN TỪ CỔNG THẬT, KHÔNG TỰ ĐẶT LẠI.
       `workflow/tao_run.py::tao_run` chỉ cho tạo run mới khi:

           if not workflow.published_version_id or workflow.archived_at is not None:
               raise KhongCoBanPublish(...)
           ver = db.get(WorkflowVersion, workflow.published_version_id)

       ⇒ tập version còn tạo được run mới = ĐÚNG MỘT version mỗi workflow
       (`published_version_id`) của workflow chưa lưu trữ. Hàm này lọc y hệt.

    ⛔ TRƯỚC 23/09 NÓ CHỈ LỌC `Workflow.archived_at IS NULL` — tức báo cả những
       version CŨ. `WorkflowVersion` là *"một bản đã xuất bản — BẤT BIẾN sau
       khi tạo"* (`platform_core/models.py`, khoá `seq`), nên một version cũ
       trỏ tới tool đã gỡ thì **không bao giờ sửa được**: báo nó là dựng đúng
       cái "báo động không ai tắt được" mà chính đoạn này lấy làm lý do loại
       workflow đã lưu trữ. Lệch về phía báo thừa (ồn, không nguy hiểm) nhưng
       mâu thuẫn nội tại, và ồn dần theo số lần xuất bản.

    ⚠️ CÂY NÀY KHÔNG CÓ CỘT TRẠNG THÁI trên `WorkflowVersion` — spec §18.4 nói
       "chỉ xét version ĐÃ PUBLISH", và ở cây này "đã publish" **không** đọc
       được từ một cột `status` của version: mọi hàng `workflow_version` là
       một bản đã xuất bản (bản đang soạn nằm ở bảng `workflow_draft` riêng,
       spec §4.2, `dinh_nghia.luu_draft`), còn "bản ĐANG publish" là một con
       trỏ trên `Workflow` CHA. Nên luật áp ở `Workflow`, không ở
       `WorkflowVersion`.

    📌 TODO (chưa có người gọi ngoài test — 23/09): hàm này là một máy đo drift
       mà không ai đọc thì không đo gì trên production. Nối vào MỘT trong hai
       chỗ có người nhìn: (a) đường publish `platform_core/workflow/dinh_nghia`
       — từ chối/cảnh báo ngay lúc xuất bản bản trỏ tới `type@version` không
       còn; hoặc (b) một mục trạng thái quản trị ở `server/routes/status.py`.
       Việc nối thuộc plan 02 Task 10 (đường publish + kiểm tra quản trị), không
       làm trong Task 9 vì nó mở thêm bề mặt HTTP ngoài phạm vi bài này.
    """
    from sqlalchemy import select

    from platform_core.models import Workflow, WorkflowVersion, WorkflowVersionNode

    co = dinh_nghia if dinh_nghia is not None else tat_ca()
    ban_do = {t: nd.type_version for t, nd in co.items()}
    hang = db.execute(
        select(WorkflowVersionNode.version_id, WorkflowVersionNode.node_id,
               WorkflowVersionNode.node_type, WorkflowVersionNode.type_version)
        .join(WorkflowVersion,
              WorkflowVersion.id == WorkflowVersionNode.version_id)
        .join(Workflow, Workflow.id == WorkflowVersion.workflow_id)
        .where(Workflow.archived_at.is_(None),
               Workflow.published_version_id == WorkflowVersion.id)
        .order_by(WorkflowVersionNode.version_id,
                  WorkflowVersionNode.node_id)).all()
    return [{"version_id": v, "node_id": n, "node_type": t, "type_version": tv}
            for v, n, t, tv in hang if ban_do.get(t) != tv]


__all__ = ["CATEGORY", "Gia", "JOB_TYPE_CONNECTOR", "JOB_TYPE_KHONG_TOOLSPEC",
           "JOB_TYPE_PIECE", "KIND", "LoiNut", "MA_LOI_APP", "NGUON_PIECE",
           "NodeDefinition", "QUYEN", "RESOURCE_CLASS", "chua_du_hop_dong",
           "tat_ca", "tu_piece", "tu_toolspec", "type_version_thieu"]
