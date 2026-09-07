"""`MayGiaLap` — phát lại bản ghi WanGP. Không mạng, không GPU, không đồng hồ.

## Nó dùng để làm gì

Sáu trên chín hạng mục của V2.2 (sổ đăng ký · danh mục tác vụ · đường ống · GUI)
không cần một GPU nào để đúng. Chúng chỉ cần **năng lực model có hình dạng
đúng**. `MayGiaLap` cung cấp đúng thứ đó, nên chúng xây và nghiệm thu được
trong khi pod đang hỏng.

## 🔴 Nguyên tắc: thiếu dữ liệu thì KÊU, không đoán

Cám dỗ tự nhiên của một máy giả lập là trả `[]` hay `{}` khi chưa có bản ghi.
Đừng. Một máy giả lập trả rỗng biến:

    "ta chưa ghi năng lực của model này"   (một khoảng trống ĐÃ BIẾT)

thành:

    "model này không có năng lực ấy"       (một câu trả lời SAI, tự tin)

Câu sai ấy đi thẳng vào sổ đăng ký, rồi vào danh mục tác vụ, rồi vào GUI — và
tới lúc ấy nó trông y hệt một sự thật. Đây đúng là cơ chế đã buộc `CLAUDE.md`
phải gỡ bảng trạng thái chép tay: một bảng cũ **không có cách nào tự biết** nó
đã cũ.

⇒ Mọi đường đọc đều đi qua `_doc()`, và `_doc()` ném `LoiMay`.

## Trường `nguon` không phải trang trí

Mỗi bản ghi khai `nguon`: `"khuon"` (ta dựng tạm cho đúng hình dạng) hoặc
`"ghi_tu_may"` (chạy `tools/wangp/ghi_ban_ghi.py` trên pod thật). Thiếu trường
ấy thì bản ghi **bị từ chối** — vì tới HM-7 không ai còn phân biệt được khuôn
sót lại với dữ liệu thật, mà một khuôn sót lại thì trông hệt dữ liệu thật, chỉ
khác là nó sai.
"""
from __future__ import annotations

import fnmatch
import json
import tempfile
from pathlib import Path
from typing import Any

from apps.lttvideo.cong.giao_uoc import LoiMay

#: Thư mục bản ghi mặc định — cạnh gói app, không neo bằng `parents[n]`.
GOC_BAN_GHI = Path(__file__).resolve().parent.parent / "ban_ghi"

#: Nhịp tiến độ mặc định khi lời gọi không đưa kịch bản riêng.
KICH_BAN_MAC_DINH: tuple[dict[str, Any], ...] = (
    {"pha": "nap_model", "phan_tram": 5.0, "xong": False},
    {"pha": "khu_nhieu", "phan_tram": 60.0, "xong": False},
    {"pha": "giai_ma", "phan_tram": 95.0, "xong": False},
    {"pha": "xong", "phan_tram": 100.0, "xong": True},
)

_NGUON_HOP_LE = frozenset({"khuon", "ghi_tu_may"})


def _khop(gia_tri: Any, mau: Any) -> bool:
    """Một ô có khớp bộ lọc không.

    Theo `docs_API.md:252`: lọc chuỗi nhận mẫu `*`/`?` không phân biệt hoa
    thường; nhiều giá trị là phép HOẶC; ô là danh sách thì khớp nếu **bất kỳ**
    phần tử nào khớp.
    """
    maus = mau if isinstance(mau, (list, tuple, set)) else [mau]
    oo = gia_tri if isinstance(gia_tri, (list, tuple, set)) else [gia_tri]
    for m in maus:
        if isinstance(m, str):
            for o in oo:
                if isinstance(o, str) and fnmatch.fnmatch(o.lower(), m.lower()):
                    return True
        else:
            if m in oo:
                return True
    return False


class MayGiaLap:
    """Hiện thực `May` đọc từ đĩa.

    ⚠️ **Tệp nó sinh ra KHÔNG phải video giải mã được.** `ket_qua()` ghi một tệp
       đánh dấu để tầng trên có thứ thật để cầm, tải lên, ghi khoá. Nếu có mã
       nào cần *giải mã* tệp ấy thì phép kiểm phải đỏ ầm ĩ — chứ không được
       xanh nhờ một MP4 bịa cho vừa.

    🔴 Và nó ghi vào **thư mục tạm**, không vào `ban_ghi/`. `ban_ghi/` nằm
       trong kho; một tệp lạ sinh ra ở đó giữa lượt gate làm chính lượt gate ấy
       mất giá trị (`cay_da_doi_giua_chung`), và mất 10 phút để biết. `ban_ghi/`
       là **chỉ đọc lúc chạy**.
    """

    def __init__(self, goc: Path | None = None,
                 kich_ban: list[dict[str, Any]] | None = None) -> None:
        self.goc = Path(goc) if goc is not None else GOC_BAN_GHI
        self._kich_ban = list(kich_ban) if kich_ban else list(KICH_BAN_MAC_DINH)
        self._viec: dict[str, dict[str, Any]] = {}
        self._dem = 0
        self._noi_ra: Path | None = None
        self._dem_media = 0

    # ── đọc bản ghi ────────────────────────────────────────────────────────

    def _tep(self, ten: str) -> Path:
        return self.goc / f"{ten}.json"

    def _phong_bi(self, ten: str) -> dict[str, Any]:
        tep = self._tep(ten)
        if not tep.is_file():
            raise LoiMay(
                f"chua co ban ghi {ten!r} trong {self.goc} — chay "
                "`python tools/wangp/ghi_ban_ghi.py` tren pod that")
        try:
            pb = json.loads(tep.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise LoiMay(f"ban ghi {ten!r} hong: {e}") from e
        if not isinstance(pb, dict) or pb.get("nguon") not in _NGUON_HOP_LE:
            raise LoiMay(
                f"ban ghi {ten!r} thieu truong `nguon` hop le "
                f"({'/'.join(sorted(_NGUON_HOP_LE))}) — khong biet no la khuon "
                "tam hay du lieu that")
        return pb

    def _doc(self, ten: str) -> Any:
        return self._phong_bi(ten)["du_lieu"]

    def nguon_cua(self, ten: str) -> str:
        """`"khuon"` hay `"ghi_tu_may"`. HM-7/B4 chốt không còn khuôn nào."""
        return str(self._phong_bi(ten)["nguon"])

    # ── tra cứu ────────────────────────────────────────────────────────────

    def liet_ke_model(self, **loc: Any) -> list[dict]:
        ds = list(self._doc("liet_ke_model"))
        gioi_han = loc.pop("limit", None)
        bo_qua = int(loc.pop("offset", 0) or 0)
        truy_van = loc.pop("query", None)

        ra = []
        for m in ds:
            sieu = m.get("metadata") or {}
            if all(_khop(sieu.get(k, m.get(k)), v)
                   for k, v in loc.items() if v is not None):
                ra.append(m)

        if truy_van:
            mau = f"*{str(truy_van).lower()}*"
            ra = [m for m in ra
                  if any(_khop(m.get(k) or (m.get("metadata") or {}).get(k), mau)
                         for k in ("name", "model_type", "architecture",
                                   "family", "description"))]

        ra = ra[bo_qua:]
        return ra[:int(gioi_han)] if gioi_han is not None else ra

    def _tu_ban_do(self, ten: str, model_type: str) -> dict:
        """Đọc một ô trong bản ghi **dạng bản đồ** (`{model_type: …}`).

        ⭐ Một tệp cho cả 225 model, không phải 225 tệp: cùng dữ liệu, nhưng 225
          tệp nhỏ trong git biến mỗi lần ghi lại thành một diff không đọc nổi.

        ⛔ Thiếu khoá thì NÉM. `May.so_do` được phép trả `None` khi **WanGP**
           không biết model — nhưng "bản ghi của ta chưa có" là chuyện khác hẳn,
           và trả `None` cho nó là biến một khoảng trống đã biết thành một câu
           trả lời sai.
        """
        ban_do = self._doc(ten)
        if model_type not in ban_do:
            raise LoiMay(
                f"ban ghi {ten!r} khong co model {model_type!r} "
                f"({len(ban_do)} model da ghi) — chay `ghi_ban_ghi.py --pod`")
        return ban_do[model_type]

    def so_do(self, model_type: str) -> dict | None:
        return self._tu_ban_do("so_do", model_type)

    def mac_dinh(self, model_type: str) -> dict:
        return self._doc(f"mac_dinh__{model_type}")

    def kha_dung(self, model_type: str) -> dict:
        return self._tu_ban_do("kha_dung", model_type)

    # ── chạy việc ──────────────────────────────────────────────────────────

    def gui_viec(self, settings: dict) -> str:
        if not settings.get("model_type"):
            raise LoiMay("settings thieu `model_type`")
        self._dem += 1
        ma = f"gialap-{self._dem}"
        self._viec[ma] = {"nhip": list(self._kich_ban), "huy": False,
                          "settings": dict(settings)}
        return ma

    def _lay(self, ma_viec: str) -> dict[str, Any]:
        v = self._viec.get(ma_viec)
        if v is None:
            raise LoiMay(f"khong co viec {ma_viec!r}")
        return v

    def tien_do(self, ma_viec: str) -> dict:
        v = self._lay(ma_viec)
        if v["huy"]:
            return {"pha": "da_huy", "phan_tram": 100.0, "xong": True}
        if not v["nhip"]:
            return {"pha": "xong", "phan_tram": 100.0, "xong": True}
        return dict(v["nhip"].pop(0))

    def ket_qua(self, ma_viec: str) -> dict:
        v = self._lay(ma_viec)
        if v["huy"]:
            # ⛔ huy KHONG kem loi — xem docstring `May.ket_qua`.
            return {"tep": [], "loi": [], "huy": True}
        if self._noi_ra is None:
            self._noi_ra = Path(tempfile.mkdtemp(prefix="lttv_gialap_"))
        tep = self._noi_ra / f"gia_lap_{ma_viec}.mp4"
        if not tep.exists():
            tep.write_bytes(
                b"KHONG PHAI VIDEO THAT - do MayGiaLap sinh ra de tang tren co "
                b"mot tep that de cam. Khong giai ma duoc, va do la CO Y.\n")
        return {"tep": [str(tep)], "loi": [], "huy": False}

    def huy(self, ma_viec: str) -> None:
        self._lay(ma_viec)["huy"] = True

    # ── dua vao / lay ra / don ─────────────────────────────────────────────

    def nap_media(self, du_lieu: bytes, *, duoi: str = "png") -> str:
        """Ghi byte ra thư mục tạm, trả đường dẫn — y như pod thật làm.

        ⛔ Từ chối byte rỗng. Trên máy thật, một tệp 0 byte đi trót lọt qua đây
           rồi làm WanGP hỏng ở tận khâu giải mã, và thông điệp lỗi lúc đó nói
           về VAE chứ không nói về tệp đầu vào.
        """
        if not du_lieu:
            raise LoiMay("nap_media: du lieu rong")
        if self._noi_ra is None:
            self._noi_ra = Path(tempfile.mkdtemp(prefix="lttv_gialap_"))
        self._dem_media += 1
        tep = self._noi_ra / f"vao_{self._dem_media}.{duoi.lstrip('.')}"
        tep.write_bytes(du_lieu)
        return str(tep)

    def tai_ve(self, ma_viec: str, chi_so: int = 0) -> bytes:
        kq = self.ket_qua(ma_viec)
        try:
            return Path(kq["tep"][chi_so]).read_bytes()
        except IndexError as e:
            raise LoiMay(
                f"viec {ma_viec!r} khong co tep thu {chi_so}") from e

    def don_dep(self, ma_viec: str) -> None:
        v = self._lay(ma_viec)
        v["da_don"] = True
