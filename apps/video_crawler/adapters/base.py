"""Hợp đồng adapter nền tảng (spec §11). Chỉ kiểu dữ liệu + làm sạch — không logic nền nào ở đây.

Điều phối khoá tệp này trước khi chia làn: mọi làn adapter dùng chung nó, không làn nào sửa nó
(ngoại lệ có điều phối: làn W4-L10 thêm `KenhItem`/`tim_kenh`, 23/09).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from platform_core.i18n import N_

#: Chế độ cào hợp lệ (tên LTT; donor: search/detail/creator/chase).
CHE_DO = frozenset({"tu_khoa", "link", "kenh", "bo"})

#: Id phải an toàn làm khoá storage (`platform_core/storage.py:_safe_key` cấm `..`, `/`, `:`). Mọi đường vào
#: (features cho "xem trước", jobs cho "cào hết") đều lọc theo mẫu này — review lần 2 (Xiaohongshu `note:token`).
ID_AN_TOAN = r"[A-Za-z0-9_-]{1,64}"

#: Id KÊNH: cùng bộ ký tự `ID_AN_TOAN` (an toàn làm phần đường dẫn URL + khoá storage) nhưng dài hơn —
#: `sec_user_id` của Douyin tới ~200 ký tự (`douyin_web._SEC_UID`), id kênh YouTube 24, user_id XHS 24,
#: `mid` Bilibili là số.
ID_KENH_AN_TOAN = r"[A-Za-z0-9_-]{1,200}"

#: bao_tien_do(phan_tram_trong_muc_0_100, thong_diep). Nơi DUY NHẤT nối tới ctx.progress + kiểm huỷ.
BaoTienDo = Callable[[int, str], None]

_RE_ID_KENH = re.compile(ID_KENH_AN_TOAN)
#: URL tuyệt đối http(s) — chặn `data:`, `javascript:`, đường dẫn tương đối. Không kiểm tên miền ở đây:
#: allowlist CDN ảnh nằm ở `anh_bia.CDN_ANH` (tầng phục vụ lại ảnh), không nhân đôi luật.
_RE_URL = re.compile(r"https?://[^\s\"'<>\\]{1,2000}")
#: Số theo dõi / số video lớn hơn mức này là dữ liệu rác ⇒ bỏ (hiện trống) thay vì hiện số vô nghĩa.
_SO_TOI_DA = 10 ** 12
#: Mô tả kênh chỉ để xem lướt trên thẻ — cắt ngắn ngay ở adapter, không để nền tảng quyết định độ dài.
MO_TA_TOI_DA = 200
TEN_KENH_TOI_DA = 120


@dataclass(frozen=True)
class YeuCauCao:
    """Một yêu cầu khám phá đã qua validate theo registry."""
    nen_tang: str
    che_do: str
    dau_vao: str
    so_luong: int


@dataclass(frozen=True)
class CrawlItem:
    """Một video tìm thấy. ⚠ Không trường nào được kết thúc bằng `_key` (spec §14)."""
    nen_tang: str
    id: str
    url: str
    tieu_de: str = ""
    tac_gia: str = ""
    thoi_luong_s: int | None = None
    anh_bia: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CrawlItem":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass(frozen=True)
class YeuCauTimKenh:
    """Khách gõ TÊN kênh (không có link) — `tu_khoa` là văn bản tự do, chưa tin được."""
    nen_tang: str
    tu_khoa: str
    so_luong: int


@dataclass(frozen=True)
class KenhItem:
    """Một thẻ kênh để khách chọn. ⚠ Không trường nào được kết thúc bằng `_key` (spec §14).

    `url` do ADAPTER dựng lại từ `id` (không lấy chuỗi của nền) — chống URL giả mạo, cùng nguyên tắc
    `url_chuan` của video. `anh_dai_dien` chỉ là URL: tầng trên phục vụ lại qua proxy `anh_bia`,
    KHÔNG tải trong lúc tìm.
    """
    nen_tang: str
    id: str
    ten: str
    url: str
    anh_dai_dien: str = ""
    so_theo_doi: int | None = None
    so_video: int | None = None
    mo_ta: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "KenhItem":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


def id_kenh_an_toan(id: Any) -> bool:
    return isinstance(id, str) and _RE_ID_KENH.fullmatch(id) is not None


def so_kenh(v: Any) -> int | None:
    """Số theo dõi / số video của nền ⇒ int ≥ 0, hoặc None (thiếu, âm, không phải số, lớn vô lý)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v < 0 or v > _SO_TOI_DA:            # v != v ⇒ NaN
        return None
    return int(v)


def chu_kenh(v: Any, toi_da: int) -> str:
    """Chuỗi hiển thị của nền ⇒ một dòng, gộp khoảng trắng, cắt `toi_da` ký tự. Không phải chuỗi ⇒ ""."""
    return re.sub(r"\s+", " ", v).strip()[:toi_da] if isinstance(v, str) else ""


def url_anh_kenh(v: Any) -> str:
    """URL ảnh đại diện đã chuẩn hoá; `//host/x` (Bilibili `upic`) ⇒ https. Không phải http(s) ⇒ ""."""
    s = v.strip() if isinstance(v, str) else ""
    if s.startswith("//"):
        s = "https:" + s
    return s if _RE_URL.fullmatch(s) else ""


def tao_kenh(nen_tang: str, id: Any, url: str, *, ten: Any = "", anh_dai_dien: Any = "",
             so_theo_doi: Any = None, so_video: Any = None, mo_ta: Any = "") -> KenhItem | None:
    """Dữ liệu thô của nền ⇒ KenhItem đã làm sạch; id không an toàn hoặc URL không phải http(s) ⇒ None.

    Dữ liệu lạ (thiếu trường, sai kiểu) KHÔNG làm vỡ: mọi trường phụ rơi về mặc định.
    """
    if not id_kenh_an_toan(id) or not _RE_URL.fullmatch(url or ""):
        return None
    return KenhItem(
        nen_tang=nen_tang, id=str(id), url=url,
        ten=chu_kenh(ten, TEN_KENH_TOI_DA) or str(id),
        anh_dai_dien=url_anh_kenh(anh_dai_dien),
        so_theo_doi=so_kenh(so_theo_doi), so_video=so_kenh(so_video),
        mo_ta=chu_kenh(mo_ta, MO_TA_TOI_DA),
    )


#: Mã lỗi riêng cho "nền này chưa tìm kênh theo tên được" — tầng trên phân biệt với lỗi mạng/đăng nhập.
MA_CHUA_HO_TRO_TIM_KENH = "chua_ho_tro_tim_kenh"
_CHUA_HO_TRO_TIM_KENH = N_("Nền tảng này chưa tìm kênh theo tên được. Hãy dán link kênh.")


def loi_chua_ho_tro_tim_kenh() -> "LoiCao":
    return LoiCao(MA_CHUA_HO_TRO_TIM_KENH, _CHUA_HO_TRO_TIM_KENH, tam_thoi=False)


@dataclass(frozen=True)
class TepTai:
    """Một tệp đã tải xong vào thư mục tạm của worker."""
    duong_dan: Path
    kich_thuoc: int
    ten_hien_thi: str


class LoiCao(Exception):
    """Lỗi đã phân loại. `tam_thoi=True` ⇒ nên thử lại; False ⇒ lỗi phía khách (không thử lại, hoàn tiền)."""

    def __init__(self, ma: str, thong_diep: str, *, tam_thoi: bool):
        super().__init__(thong_diep)
        self.ma = ma
        self.thong_diep = thong_diep
        self.tam_thoi = tam_thoi


class PlatformAdapter(Protocol):
    nen_tang: str

    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        """search/link/kênh/bộ → danh sách mục, KHÔNG tải. Ném LoiCao khi hỏng."""
        ...

    def tim_kenh(self, yeu_cau: YeuCauTimKenh, *, bao_tien_do: BaoTienDo) -> list[KenhItem]:
        """TÊN kênh → thẻ kênh để khách chọn (không tải ảnh). Nền chưa làm được ⇒
        LoiCao(MA_CHUA_HO_TRO_TIM_KENH). Không tìm thấy ai ⇒ danh sách rỗng, KHÔNG phải lỗi."""
        raise loi_chua_ho_tro_tim_kenh()

    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do: BaoTienDo) -> TepTai:
        """Tải MỘT mục vào `thu_muc`. Ném LoiCao khi hỏng; ném ngoại lệ huỷ khi bao_tien_do báo huỷ."""
        ...
