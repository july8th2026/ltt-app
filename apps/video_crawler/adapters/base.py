"""Hợp đồng adapter nền tảng (spec §11). Chỉ kiểu dữ liệu — không logic nền nào ở đây.

Điều phối khoá tệp này trước khi chia làn: mọi làn adapter dùng chung nó, không làn nào sửa nó.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Protocol

#: Chế độ cào hợp lệ (tên LTT; donor: search/detail/creator/chase).
CHE_DO = frozenset({"tu_khoa", "link", "kenh", "bo"})

#: Id phải an toàn làm khoá storage (`platform_core/storage.py:_safe_key` cấm `..`, `/`, `:`). Mọi đường vào
#: (features cho "xem trước", jobs cho "cào hết") đều lọc theo mẫu này — review lần 2 (Xiaohongshu `note:token`).
ID_AN_TOAN = r"[A-Za-z0-9_-]{1,64}"

#: bao_tien_do(phan_tram_trong_muc_0_100, thong_diep). Nơi DUY NHẤT nối tới ctx.progress + kiểm huỷ.
BaoTienDo = Callable[[int, str], None]


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

    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do: BaoTienDo) -> TepTai:
        """Tải MỘT mục vào `thu_muc`. Ném LoiCao khi hỏng; ném ngoại lệ huỷ khi bao_tien_do báo huỷ."""
        ...
