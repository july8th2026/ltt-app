"""`core.http` — gọi một HTTP API mà **người soạn workflow** chọn địa chỉ.

Plan wf-v2 P5 Task 3. Mọi request đi qua bộ gác `platform_core.an_toan_mang`
(P5/T1) và client ghim IP `platform_core.http_an_toan` (P5/T2).
⛔ **Không** viết lại bộ kiểm URL ở đây — có đúng một bản, và nó ở T1.

⭐ **Người soạn workflow là một bên ngoài.** Họ không phải kẻ tấn công, nhưng
   URL họ gõ vào có thể do một node trước đó sinh ra từ dữ liệu của người
   khác. Nên node này áp **đúng** chính sách mà webhook áp cho URL khách
   nhập: chỉ https, chỉ địa chỉ định tuyến được công cộng.

⛔ **Mặc định KHÔNG theo chuyển hướng.** Header người soạn khai (rất hay là
   một `Authorization`) sẽ được gửi LẠI tới host mà **đích kia** chọn trong
   `Location`. Đó là một đường rò khoá không cần ai tấn công tinh vi: chỉ cần
   API đối tác bị chiếm quyền trả một `302`. Bật `theo_chuyen_huong` thì mỗi
   hop vẫn qua bộ gác (T2), nhưng việc gửi lại header là quyết định của người
   soạn, không phải mặc định của nền tảng.

⛔ **Chưa nối vào `nut_loi/__init__.py`.** Làn p3 đang sửa tệp đó. Cơ chế
   đăng ký vẫn đúng: `dang_ky()` chạy khi mô-đun được import, và
   `tests/test_2912_nut_core_http.py::test_import_mo_dun_LA_DU_de_node_co_mat_trong_so`
   chứng minh điều đó thay vì để nó thành một lời hứa.

⛔ **Chưa nối vào `dong_co`/`cau_noi`.** `thuc_thi()` là một hàm thuần: nhận
   tham số, trả kết quả hoặc ném `LoiHttp`. Việc dịch `LoiHttp` thành trạng
   thái FAILED của một node nằm ở cầu nối, ngoài phạm vi tệp của làn p5.
"""
from __future__ import annotations

import json as _json
from typing import Any

import httpx

import platform_core.an_toan_mang as an_toan_mang
import platform_core.http_an_toan as http_an_toan
from platform_core.i18n import N_
from platform_core.workflow import he_kieu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow import ngon_ngu, noi_suy
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.nut_loi import dang_ky
from platform_core.workflow.nut_loi.chay import KetQua
from platform_core import credential as kho_credential

#: ⛔ Danh sách ĐÓNG. `TRACE`/`CONNECT` không bao giờ là thứ một workflow cần,
#: và `TRACE` là một công cụ dò cấu hình proxy.
CACH_CHO_PHEP = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD")

#: 2 MiB. Một đích thù địch không được nhét đầy bộ nhớ worker, và một phản hồi
#: lớn hơn ngần này là một tệp — việc của `core.file`, không phải của node này.
TRAN_PHAN_HOI_BYTE = 2 * 1024 * 1024

THOI_CHO_MAC_DINH_S = 30.0

#: Chính sách bộ gác mà node dùng. `None` = mặc định của `an_toan_mang`
#: (chỉ https, chỉ địa chỉ công cộng). ⭐ Là một hằng ở mức mô-đun để phép kiểm
#: đổi **câu hỏi** đặt cho bộ gác (máy chủ giả sống ở 127.0.0.1) mà không phải
#: **vô hiệu hoá** bộ gác — vô hiệu hoá thì phép kiểm không còn đo gì.
CHINH_SACH_NODE = None

#: Kiểu credential node này biết tiêm. ⛔ Không `oauth2`: một access token của
#: Google đi vào một URL người soạn tự gõ là đúng hình dạng của một lần rò
#: token sang bên thứ ba. `oauth2` là việc của connector, nơi ĐÍCH đã cố định.
KIEU_CREDENTIAL = ("api_key", "bearer", "basic")

#: Header không bao giờ được trả ra `output` (spec §9.4). Một đích thù địch
#: **dội lại** header uỷ quyền trong phản hồi là một đường rò không cần ai
#: tấn công tinh vi — nên che theo TÊN, cả hai chiều.
HEADER_PHAI_CHE = ("authorization", "cookie", "set-cookie", "x-api-key",
                   "proxy-authorization", "x-auth-token", "x-csrf-token")

DA_CHE = "«da che»"

#: Mã lỗi node công bố (spec §5.6 `NodeError.ma`). Khai riêng, không dùng lại
#: `nut.MA_LOI_APP`: lỗi ở đây không phải lỗi của một job app.
MA_LOI_HTTP: tuple[str, ...] = (
    "dau_vao_sai",          # URL/phương thức sai hình dạng — chưa gửi gì
    "bi_chan_ssrf",         # bộ gác từ chối đích
    "het_thoi_gian",
    "khong_ket_noi_duoc",
    "ma_trang_thai_loi",    # 4xx/5xx và người soạn không khai là chấp nhận
    "phan_hoi_qua_lon",
)


class LoiHttp(Exception):
    """Một lần gọi không thành. `ma` nằm trong `MA_LOI_HTTP`."""

    def __init__(self, ma: str, thong_bao: str = "", *,
                 trang_thai: int = 0, than: Any = None) -> None:
        self.ma = ma
        self.trang_thai = int(trang_thai)
        # Thân lỗi PHẢI tới được tay người soạn: không có nó thì họ không
        # cách nào biết API kia phàn nàn chuyện gì.
        self.than = than
        super().__init__(thong_bao or ma)


def _than_va_kieu(than: Any) -> tuple[bytes | None, dict]:
    """Thân gửi đi + header `Content-Type` tương ứng.

    `dict`/`list` → JSON. Chuỗi → nguyên văn, **không** đoán kiểu hộ: người
    soạn khai `Content-Type` của họ thì header đó thắng.
    """
    if than is None:
        return None, {}
    if isinstance(than, (dict, list)):
        return (_json.dumps(than, ensure_ascii=False).encode("utf-8"),
                {"Content-Type": "application/json; charset=utf-8"})
    if isinstance(than, bytes):
        return than, {}
    return str(than).encode("utf-8"), {}


def _doc_co_tran(phan_hoi: httpx.Response) -> bytes:
    """Đọc thân với trần cứng. Vượt trần ⇒ dừng, không đọc nốt."""
    ra = bytearray()
    for khuc in phan_hoi.iter_bytes():
        ra += khuc
        if len(ra) > TRAN_PHAN_HOI_BYTE:
            raise LoiHttp("phan_hoi_qua_lon",
                          f"Phan hoi vuot {TRAN_PHAN_HOI_BYTE} byte.",
                          trang_thai=phan_hoi.status_code)
    return bytes(ra)


def _dien_giai_than(raw: bytes) -> Any:
    """JSON nếu phân tích được, ngược lại là chuỗi.

    ⭐ Một API trả HTML **không phải** lỗi của người soạn workflow — biến nó
       thành FAILED là bắt họ trả giá cho quyết định của bên kia.
    """
    if not raw:
        return ""
    try:
        return _json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")


def che_header(headers: dict, *, bi_mat: str = "") -> dict:
    """Header đã che, an toàn để trả ra `output` và vào `node_run_snapshot`.

    Hai lớp, và cả hai đều cần:

    1. **Theo TÊN** (`HEADER_PHAI_CHE`) — bắt được cả thứ ta không gửi, ví dụ
       một `Set-Cookie` phiên của đích.
    2. **Theo GIÁ TRỊ** — bắt được bí mật xuất hiện ở một header mang tên khác,
       vì một đích thù địch chọn được tên header nó dội lại.
    """
    ra = {}
    for k, v in (headers or {}).items():
        gt = str(v)
        if str(k).lower() in HEADER_PHAI_CHE:
            ra[k] = DA_CHE
        elif bi_mat and bi_mat in gt:
            ra[k] = gt.replace(bi_mat, DA_CHE)
        else:
            ra[k] = gt
    return ra


def header_credential(kieu: str, bi_mat, meta: dict | None = None) -> dict:
    """`{tên header: giá trị}` cho một credential. ⛔ Không log giá trị trả về.

    `meta` là ô **công khai**, nên nó chỉ mang được những thứ không bí mật —
    tên header và tiền tố. Chính giá trị thì nằm trong `bi_mat`.
    """
    meta = dict(meta or {})
    if kieu == "bearer":
        return {"Authorization": f"Bearer {bi_mat}"}
    if kieu == "basic":
        import base64

        if isinstance(bi_mat, dict):
            tai_khoan = str(bi_mat.get("tai_khoan") or bi_mat.get("user") or "")
            mat_khau = str(bi_mat.get("mat_khau") or bi_mat.get("password") or "")
            tho = f"{tai_khoan}:{mat_khau}"
        else:
            # Đã là "user:pass" — `basic` với một chuỗi duy nhất chỉ có nghĩa đó.
            tho = str(bi_mat)
        goi = base64.b64encode(tho.encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {goi}"}
    # `api_key`: đích quyết định tên header, nên người tạo credential khai nó.
    ten = str(meta.get("ten_header") or "Authorization")
    tien_to = str(meta.get("tien_to") or "")
    gia_tri = f"{tien_to}{bi_mat}" if tien_to else str(bi_mat)
    return {ten: gia_tri}


def thuc_thi(tham_so: dict, *, chinh_sach: an_toan_mang.ChinhSach | None = None,
             bo_phan_giai=None, tao_client=None, header_them=None,
             che_gia_tri: str = "") -> dict:
    """Gọi một API. Trả `{trang_thai, than, headers}` hoặc ném `LoiHttp`.

    Hàm **thuần** theo nghĩa không đụng CSDL và không ghi trạng thái run: cầu
    nối của động cơ dịch `LoiHttp` thành FAILED. `tao_client` để test cắm một
    client giả vào mà không phải vá `httpx`.
    """
    header_them = dict(header_them or {})
    cach = str(tham_so.get("cach") or "GET").upper()
    if cach not in CACH_CHO_PHEP:
        raise LoiHttp("dau_vao_sai",
                      f"Phuong thuc khong duoc phep: {cach!r}.")

    url = str(tham_so.get("url") or "")
    headers = dict(tham_so.get("headers") or {})
    than_byte, kieu = _than_va_kieu(tham_so.get("than"))
    for k, v in kieu.items():
        headers.setdefault(k, v)
    # ⭐ Credential GHI ĐÈ header người soạn tự gõ, không `setdefault`: nếu hai
    #    thứ cùng khai `Authorization` thì thứ đi ra phải là thứ nền tảng quản
    #    lý được và thu hồi được — không phải một chuỗi nằm trong `params`.
    headers.update(header_them)

    thoi_cho = float(tham_so.get("thoi_cho_s") or THOI_CHO_MAC_DINH_S)
    theo_chuyen_huong = bool(tham_so.get("theo_chuyen_huong") or False)
    ma_chap_nhan = tham_so.get("ma_chap_nhan")

    xuong = tao_client or http_an_toan.tao_client
    try:
        with xuong(chinh_sach=chinh_sach, bo_phan_giai=bo_phan_giai,
                   timeout=thoi_cho,
                   follow_redirects=theo_chuyen_huong) as client:
            with client.stream(cach, url, headers=headers,
                               content=than_byte) as phan_hoi:
                raw = _doc_co_tran(phan_hoi)
                ra_headers = dict(phan_hoi.headers)
                trang_thai = int(phan_hoi.status_code)
    except an_toan_mang.LoiChanSSRF as exc:
        # Hình dạng URL sai là **lỗi của người soạn**; địa chỉ bị chặn là một
        # chuyện khác hẳn. Gộp hai thứ vào một mã là bắt họ đi dò xem mình gõ
        # sai hay nền tảng từ chối.
        if exc.ma == an_toan_mang.MA_KHONG_CHO_PHEP:
            raise LoiHttp("bi_chan_ssrf",
                          "Dia chi nay khong duoc phep.") from exc
        raise LoiHttp("dau_vao_sai", f"URL khong hop le ({exc.ma}).") from exc
    except httpx.TimeoutException as exc:
        raise LoiHttp("het_thoi_gian",
                      f"Khong tra loi trong {thoi_cho} giay.") from exc
    except httpx.HTTPError as exc:
        raise LoiHttp("khong_ket_noi_duoc", str(exc)) from exc

    ra_headers = che_header(ra_headers, bi_mat=che_gia_tri)
    than = _dien_giai_than(raw)
    if ma_chap_nhan:
        ok = trang_thai in {int(m) for m in ma_chap_nhan}
    else:
        ok = trang_thai < 400
    if not ok:
        raise LoiHttp("ma_trang_thai_loi", f"HTTP {trang_thai}.",
                      trang_thai=trang_thai, than=than)
    return {"trang_thai": trang_thai, "than": than, "headers": ra_headers}


def chay_http(db, run, node: dict, *, moi_truong: dict, **_) -> KetQua:
    """Bộ thi hành inline của `core.http` — nối `thuc_thi` vào động cơ.

    🔴 THIẾU BỘ NÀY, `main` ĐỎ NGAY LÚC COLLECT (24/09). Node khai
       `thi_hanh="inline"` nhưng `dang_ky` không nhận hàm chạy, và luật của
       `nut_loi.dang_ky` **ném lúc dựng** — đúng như nó phải làm: một node
       inline không có bộ thi hành sẽ đứng `READY` tới khi hết TTL 20 giờ.

    ⛔ Đây là vết của việc **hai làn song song**: làn viết `core.http` và làn
       thêm luật `dang_ky` đều XANH một mình, và chỉ vỡ khi gộp. Xanh-khi-tách
       không chứng minh được gì về xanh-khi-gộp.

    Tham số đi qua ngôn ngữ §6 trước khi gọi, cùng đường `du_lieu.chay_*`.
    `LoiHttp` thành `FAILED` có **mã**, không thành ngoại lệ trần — động cơ bắt
    ngoại lệ trần thành `loi_he_thong`, và một URL người dùng gõ sai không phải
    lỗi hệ thống.
    """
    tham_so = dict(node.get("params") or {})
    try:
        # 🔴 `ngon_ngu.tinh` (bản trước) coi CẢ chuỗi là một biểu thức, nên một
        #    URL viết thẳng — `"https://vi.du/api"` — ném `invalid syntax`.
        #    Tức node chỉ chạy được khi mọi tham số là biểu thức, và đó là
        #    ngược với §6: `{{ }}` là thứ **đánh dấu** phần biểu thức trong một
        #    chuỗi thường. `noi_suy` là lớp đúng, và nó trả nguyên văn khi
        #    không có `{{`.
        for ten, gia_tri in list(tham_so.items()):
            tham_so[ten] = noi_suy.noi_suy(
                gia_tri, lambda bt: ngon_ngu.tinh(bt, moi_truong))
    except (LoiNgonNgu, noi_suy.LoiNoiSuy) as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])

    try:
        header_them, bi_mat_tho = _credential(db, run, node)
    except kho_credential.LoiCredential as loi:
        # ⭐ Mã của kho đi thẳng ra: `credential_bi_thu_hoi` là câu spec §9.1
        #    yêu cầu, và nó nói đúng việc khách phải làm (nối lại/tạo khoá mới).
        return KetQua(sang="FAILED", error=f"{loi.ma}: {loi}"[:2000])

    try:
        ra = thuc_thi(tham_so, chinh_sach=CHINH_SACH_NODE,
                      header_them=header_them, che_gia_tri=bi_mat_tho)
    except LoiHttp as loi:
        # ⛔ `loi.than` mang **thân phản hồi của đích**, và một 401 hay dội lại
        #    chính token vừa gửi. Che trước khi nó thành `error` của node —
        #    `error` đi vào `node_run_snapshot`, một bảng CHỈ THÊM.
        return KetQua(sang="FAILED",
                      error=_che_chuoi(f"{loi.ma}: {loi}", bi_mat_tho)[:2000])
    return KetQua(output=ra)


def _che_chuoi(chuoi: str, bi_mat: str) -> str:
    return chuoi.replace(bi_mat, DA_CHE) if bi_mat else chuoi


def _credential(db, run, node: dict) -> tuple[dict, str]:
    """`(header tiêm vào, bí mật thô để che)`. Rỗng khi node không gán ref.

    ⭐ **Chỉ chỗ này giải mã**, và nó nằm trong tiến trình job (spec §9.4).
       Động cơ gọi `chay_http` từ vòng scheduler của worker — cùng tiến trình,
       không phải tiến trình web.
    """
    ref = str(node.get("credential_ref") or "")
    if not ref or db is None:
        return {}, ""
    c = kho_credential.kiem_ref(db, ref,
                                owner_id=str(getattr(run, "owner_id", "") or ""),
                                kieu_cho_phep=KIEU_CREDENTIAL)
    bi_mat = kho_credential.lay_de_dung(
        db, ref, owner_id=str(getattr(run, "owner_id", "") or ""),
        run_id=str(getattr(run, "id", "") or ""),
        node_id=str(node.get("id") or ""))
    header = header_credential(c.kieu, bi_mat, c.meta)
    # Bí mật thô dùng để CHE, nên nó phải là chuỗi thật sự đi ra dây — với
    # `basic` thì đó là chuỗi đã base64, không phải mật khẩu gốc.
    tho = bi_mat if isinstance(bi_mat, str) else ""
    if c.kieu == "basic":
        tho = next(iter(header.values())).split(" ", 1)[-1]
    return header, tho


CORE_HTTP = dang_ky(NodeDefinition(
    type="core.http", type_version=1, kind="data", category="NETWORK",
    title=N_("Gọi HTTP"),
    description=N_("Gọi một HTTP API. Mọi địa chỉ đi qua bộ gác SSRF: chỉ "
                   "https và chỉ địa chỉ công cộng."),
    icon="🌐",
    cong_vao=(
        ("url", he_kieu.Cong(type="text", required=True, nhan="url")),
        ("than", he_kieu.Cong(type="any", required=False, nhan="than")),
        ("headers", he_kieu.Cong(type="json", required=False, nhan="headers")),
    ),
    cong_ra=(
        ("trang_thai", he_kieu.Cong(type="integer", required=True,
                                    nhan="trang_thai")),
        ("than", he_kieu.Cong(type="any", required=False, nhan="than")),
        ("headers", he_kieu.Cong(type="json", required=False, nhan="headers")),
    ),
    tham_so={
        "type": "object",
        "properties": {
            "cach": {"type": "string", "enum": list(CACH_CHO_PHEP),
                     "default": "GET", "description": N_("Phương thức HTTP.")},
            "url": {"type": "string", "description": N_("Địa chỉ https.")},
            "headers": {"type": "object", "x-ltt-control": "code-json",
                        "description": N_("Header gửi kèm.")},
            "than": {"description": N_(
                "Thân gửi đi. Object/mảng -> JSON; chuỗi -> nguyên văn.")},
            "thoi_cho_s": {"type": "number", "minimum": 0.1, "maximum": 300,
                           "default": THOI_CHO_MAC_DINH_S},
            "theo_chuyen_huong": {"type": "boolean", "default": False,
                                  "description": N_(
                                      "Theo 3xx. Tắt mặc định: header của "
                                      "bạn sẽ đi tới host do đích kia chọn.")},
            "ma_chap_nhan": {"type": "array", "items": {"type": "integer"},
                             "description": N_(
                                 "Mã coi là thành công. Trống -> mọi mã < 400.")},
        },
        "required": ["url"], "additionalProperties": False,
    },
    thi_hanh="inline", side_effect="external", idempotency_key_fields=(),
    resource={"class": "api"},
    # Không tính credit: node này không chạy model và không giữ GPU. Cái nó
    # tiêu là thời gian worker, và trần `thoi_cho_s` là thứ chặn điều đó.
    gia=Gia.mien_phi(), credential=KIEU_CREDENTIAL,
    quyen=frozenset({"network", "credential"}),
    cho=(), ma_loi=MA_LOI_HTTP + ("credential_bi_thu_hoi", "khong_thay"),
    # ⭐ MỞ KHOÁ 24/09/2026. Lý do khoá (`tests/test_1789`: *"thiếu KHO
    #    CREDENTIAL cho header Authorization — bật sớm là mời khách dán token
    #    vào `WorkflowVersion`"*) đã hết: kho có ở `platform_core/credential.py`,
    #    ref được kiểm lúc publish (`dinh_nghia._kiem_credential`), và bí mật
    #    bị che ở cả `output` lẫn `error`.
    publish_duoc=True), chay_http)


__all__ = ["CACH_CHO_PHEP", "CHINH_SACH_NODE", "CORE_HTTP", "DA_CHE",
           "HEADER_PHAI_CHE", "KIEU_CREDENTIAL", "LoiHttp", "MA_LOI_HTTP",
           "THOI_CHO_MAC_DINH_S", "TRAN_PHAN_HOI_BYTE", "chay_http",
           "che_header", "header_credential", "thuc_thi"]
