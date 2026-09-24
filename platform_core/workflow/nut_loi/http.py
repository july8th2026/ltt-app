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
from platform_core.workflow.nut_loi import dang_ky

#: ⛔ Danh sách ĐÓNG. `TRACE`/`CONNECT` không bao giờ là thứ một workflow cần,
#: và `TRACE` là một công cụ dò cấu hình proxy.
CACH_CHO_PHEP = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD")

#: 2 MiB. Một đích thù địch không được nhét đầy bộ nhớ worker, và một phản hồi
#: lớn hơn ngần này là một tệp — việc của `core.file`, không phải của node này.
TRAN_PHAN_HOI_BYTE = 2 * 1024 * 1024

THOI_CHO_MAC_DINH_S = 30.0

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


def thuc_thi(tham_so: dict, *, chinh_sach: an_toan_mang.ChinhSach | None = None,
             bo_phan_giai=None, tao_client=None) -> dict:
    """Gọi một API. Trả `{trang_thai, than, headers}` hoặc ném `LoiHttp`.

    Hàm **thuần** theo nghĩa không đụng CSDL và không ghi trạng thái run: cầu
    nối của động cơ dịch `LoiHttp` thành FAILED. `tao_client` để test cắm một
    client giả vào mà không phải vá `httpx`.
    """
    cach = str(tham_so.get("cach") or "GET").upper()
    if cach not in CACH_CHO_PHEP:
        raise LoiHttp("dau_vao_sai",
                      f"Phuong thuc khong duoc phep: {cach!r}.")

    url = str(tham_so.get("url") or "")
    headers = dict(tham_so.get("headers") or {})
    than_byte, kieu = _than_va_kieu(tham_so.get("than"))
    for k, v in kieu.items():
        headers.setdefault(k, v)

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

    than = _dien_giai_than(raw)
    if ma_chap_nhan:
        ok = trang_thai in {int(m) for m in ma_chap_nhan}
    else:
        ok = trang_thai < 400
    if not ok:
        raise LoiHttp("ma_trang_thai_loi", f"HTTP {trang_thai}.",
                      trang_thai=trang_thai, than=than)
    return {"trang_thai": trang_thai, "than": than, "headers": ra_headers}


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
    gia=Gia.mien_phi(), credential=(), quyen=frozenset({"network"}),
    cho=(), ma_loi=MA_LOI_HTTP,
    publish_duoc=False))


__all__ = ["CACH_CHO_PHEP", "CORE_HTTP", "LoiHttp", "MA_LOI_HTTP",
           "THOI_CHO_MAC_DINH_S", "TRAN_PHAN_HOI_BYTE", "thuc_thi"]
