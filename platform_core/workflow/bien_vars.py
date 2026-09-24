"""`vars` — trang thai workflow, spec §6.5. Gop luc CHAY, chan xung dot luc PUBLISH.

## Nguyen van spec §6.5

    Khong co trang thai sua duoc dung chung. `vars` = gop output cua moi
    `core.set` la **to tien** cua node dang tinh, theo thu tu `graph.thu_tu`.
    Hai `core.set` ghi cung khoa ma khong co quan he to tien ⇒ validator tu
    choi (`ghi_bien_xung_dot`). ⇒ Tat dinh, khong khoa, khong can cot trang
    thai run.

## ⭐ Vi sao khong co "bang bien cua run"

Mot bang bien sua duoc thi hai nhanh song song ghi vao no, va ket qua phu
thuoc vao **ai chay truoc** — tuc phu thuoc vao lich cua scheduler, khong phu
thuoc vao do thi. Do la thu khong replay duoc, khong giai thich duoc cho khach,
va can mot cai khoa.

§6.5 doi cho no bang mot **phep gop tren do thi**: `vars` cua mot node la mot
ham THUAN cua (anh chup output, quan he to tien, `graph.thu_tu`). Cung ba thu
do ⇒ cung ket qua, hom nay hay khi replay ba thang sau.

Hai nua cua luat ay phai dung CUNG mot quan he to tien, nen ca hai o day:

    `gop_vars`            luc CHAY — gop output cua nguoi ghi la to tien
    `kiem_ghi_xung_dot`   luc PUBLISH — tu choi do thi ma phep gop kia khong
                          tat dinh (hai nguoi ghi cung khoa, khong ai la to
                          tien cua ai ⇒ ket qua tuy thu tu chay)

⚠️ Doi mot trong hai ma khong doi cai kia la mo mot cua: mot do thi publish
   duoc nhung chay ra hai ket qua khac nhau.

## ⛔ Mo-dun nay KHONG cai node `core.set`

`core.set` la node dieu khien cua **P3** (`bien_dich` hom nay tu choi moi loai
ngoai `tool`/`app.*` bang `loai_node_chua_ho_tro`). O day chi co **ngu nghia**
cua `vars` va cho de noi vao:

- P3 goi `kiem_ghi_xung_dot(khoa_ghi, to_tien)` trong `bien_dich` sau khi da
  dung `to_tien` (cung cho cong to tien §6.2 dang dung), voi `khoa_ghi` la tap
  cong RA cua tung node `core.set`;
- dong co goi `gop_vars(...)` khi dung moi truong §6.2
  (`chinh_sach.moi_truong_wf(vars=...)`).

`test_1768` co mot **banh coc** ghim su vang mat do: ngay `core.set` bien dich
duoc ma cong publish chua goi validator, bai ay do.
"""
from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Set
from typing import Any

from platform_core.workflow.bien_dich import LoiBienDich
from platform_core.workflow.chinh_sach import LoiNgonNgu

__all__ = ["KhongGianVars", "LOAI_GHI", "gop_vars", "kiem_ghi_xung_dot"]

#: Loai node ghi `vars` (§6.5). Mot hang so vi ca hai tang deu noi ve no.
LOAI_GHI = "core.set"


def _thay_duoc(khoa: Any) -> bool:
    """Khoa doc duoc tu ngon ngu §6.

    ⛔ Khoa bat dau `_` la VO HINH — cung luat voi `chinh_sach._doc_khoa` va
       voi moi cua doc object cua `ham_bieu_thuc`. Mot luat, khong sau ngoai le:
       neu `vars` giu lai chung thi `keys(vars)` la mot cua hau ke ten.
    """
    return isinstance(khoa, str) and not khoa.startswith("_")


class KhongGianVars(Mapping):
    """`vars` cua §6.2 — chi doc, va noi RO khi doc hut.

    ⚠️ Khong tra `None` cho mot bien chua ai ghi: mot `None` im lang se di
       tiep vao mot node co tinh tien. Cung ly do `_MatNode` tu choi doc output
       cua node chua SUCCEEDED.
    """

    def __init__(self, gia_tri: Mapping[str, Any],
                 nguon: Mapping[str, str] = {},
                 cho_xong: Iterable[str] = ()) -> None:
        self._gia_tri = dict(gia_tri)
        #: khoa -> id node da ghi no (cho cau loi, va de go roi mot phep gop).
        self.nguon = dict(nguon)
        #: Nguoi ghi la to tien nhung CHUA SUCCEEDED — ho co the la ly do mot
        #: bien vang mat, va noi ra dieu do dat hon "khong co khoa".
        self.cho_xong = tuple(sorted(cho_xong))

    def __getitem__(self, khoa: str) -> Any:
        if khoa in self._gia_tri:
            return self._gia_tri[khoa]
        cau = (f"khong co bien {khoa!r} trong `vars` "
               f"(co: {sorted(self._gia_tri)})")
        if self.cho_xong:
            cau += (f"; node ghi bien la to tien nhung CHUA chay xong: "
                    f"{list(self.cho_xong)}")
        raise LoiNgonNgu(cau)

    def __contains__(self, khoa: object) -> bool:
        # ⛔ Khong de `Mapping.__contains__` goi `self[khoa]`: no chi bat
        #    `KeyError`, con day nem `LoiNgonNgu` ⇒ `"k" in vars` se NEM.
        return khoa in self._gia_tri

    def __iter__(self):
        return iter(self._gia_tri)

    def __len__(self) -> int:
        return len(self._gia_tri)

    def __repr__(self) -> str:
        return f"KhongGianVars({self._gia_tri!r})"


def gop_vars(anh_chup: Mapping[str, Mapping[str, Any]], *,
             nguoi_ghi: Iterable[str], to_tien: Set[str],
             thu_tu: Iterable[str]) -> KhongGianVars:
    """`vars` cua MOT node (§6.5). Ham THUAN — khong doc CSDL, khong doc gio.

    - `anh_chup`  `{id: {"status": ..., "output": {...}}}` — cung hinh dang ma
      `chinh_sach.KhongGianNodes` nhan, de dong co chi nap MOT anh chup.
    - `nguoi_ghi` id cac node `core.set` trong do thi.
    - `to_tien`   to tien cua node DANG TINH (khong phai ca bang).
    - `thu_tu`    `graph.thu_tu` — nguoi di SAU ghi de nguoi di truoc.

    ⚠️ Nguoi ghi chua `SUCCEEDED` khong dong gop: output cua ho CHUA TON TAI,
       khong phai "rong". `KhongGianVars.cho_xong` mang ho theo de cau loi noi
       duoc dieu do.
    """
    thu_tu = list(thu_tu)
    nguoi_ghi = set(nguoi_ghi)
    # ⛔ Mot nguoi ghi la to tien ma khong co trong `thu_tu` thi khong xep thu
    #    tu duoc — va bo qua no la ĐOI mot gia tri trong im lang.
    thieu = sorted((nguoi_ghi & set(to_tien)) - set(thu_tu))
    if thieu:
        raise LoiNgonNgu(
            f"node ghi bien {thieu} khong co trong `graph.thu_tu` — khong xep "
            "duoc thu tu ghi, va `vars` phai tat dinh (§6.5)")

    gia_tri: dict[str, Any] = {}
    nguon: dict[str, str] = {}
    cho_xong: list[str] = []
    for nid in thu_tu:
        if nid not in nguoi_ghi or nid not in to_tien:
            continue
        ban_ghi = anh_chup.get(nid) or {}
        if ban_ghi.get("status") != "SUCCEEDED":
            cho_xong.append(nid)
            continue
        for khoa, v in (ban_ghi.get("output") or {}).items():
            if not _thay_duoc(khoa):
                continue
            gia_tri[khoa] = v
            nguon[khoa] = nid
    return KhongGianVars(gia_tri, nguon, cho_xong)


def kiem_ghi_xung_dot(khoa_ghi: Mapping[str, Collection[str]],
                      to_tien: Mapping[str, Set[str]]) -> None:
    """Tu choi do thi ma `gop_vars` khong tat dinh (§6.5, `ghi_bien_xung_dot`).

    `khoa_ghi` la `{id node core.set: cac khoa no ghi}` — tap cong RA cua node
    ay. `to_tien` la `{id: to tien cua id}` — dung cai `bien_dich` da dung cho
    cong to tien §6.2, khong dung mot bang thu hai.

    ⭐ Luat lay NGUYEN VAN spec: *"Hai `core.set` ghi cung khoa ma khong co
       quan he to tien ⇒ tu choi"*. ⛔ Co mot cach doc long hon — chi tu choi
       khi co mot node THUC SU doc `vars` va nhin thay ca hai — va no **khong
       phai cai spec viet**. Cach doc long hon cung lam cau tra loi phu thuoc
       vao viec ai do co doc `vars` hay khong, nen mot lan sua node doc lai
       lam mot do thi da publish tro thanh khong hop le.

    ⚠️ Duyet theo `sorted` de cau loi TAT DINH: hai lan publish cung do thi
       phai ra cung mot cau, neu khong nguoi khai thay "loi lung linh".
    """
    ids = sorted(khoa_ghi)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            chung = sorted(set(khoa_ghi[a]) & set(khoa_ghi[b]))
            if not chung:
                continue
            if b in to_tien.get(a, set()) or a in to_tien.get(b, set()):
                continue        # co quan he to tien ⇒ nguoi di sau thang
            raise LoiBienDich(
                "ghi_bien_xung_dot",
                f"node {a!r} va node {b!r} cung ghi bien {chung} nhung khong "
                f"ai la to tien cua ai — `vars` se phu thuoc thu tu chay "
                f"(spec §6.5). Noi hai nhanh lai, hoac doi ten mot ben.",
                b)
