"""May duyet AST + CHINH SACH — dung lai MA ma khong dung lai HOP DONG.

## Van de no giai

`bieu_thuc.py` co mot bo duyet AST da test ky. Ngon ngu bieu thuc §6 can **cung
bo ruot do**: cung cach di tren cay, cung cach tu choi nut la, cung cach tinh.

Nhung no **doi nguoc ba dieu cam** ma `bieu_thuc.py` coi la tinh nang:

    bieu_thuc.py (timeout_expr)        ngon ngu §6
    CHI doc `params` cua node          doc `nodes.<id>.output.<cong>`
    KHONG goi ham                      co bang ham dong
    tat dinh, tinh duoc luc validate   tinh luc chay

⛔ Mo rong `bieu_thuc.py` tai cho la **pha bao dam ve tien**: con so tran
`max_runtime_s` phai **ton tai truoc** khi ai do tieu tien, va no ton tai duoc
chinh vi ba dieu cam kia.

⇒ Tach doi: **may** o day chi biet DI TREN CAY. **Chinh sach** — nut nao cho
  phep, ten nao giai duoc, co cho goi ham khong, bang ham nao, cau loi noi gi —
  la mot **bang du lieu** truyen vao. Mot may, nhieu hop dong.

## Vi sao chinh sach la DU LIEU chu khong phai lop con

Lop con thi mot hop dong noi long duoc bang cach ghi de mot phuong thuc, va
viec ghi de do **khong hien ra o cho khai bao**. Bang du lieu thi noi long la
mot dong diff trong chinh bang — va mot phep kiem doc duoc bang do.

## Nguon doi chieu (tra truoc khi tu suy)

- `ast` — danh sach nut `ast.expr` va cac cho phai de quy vao:
  https://docs.python.org/3/library/ast.html  (goc `ast.Expression` cho
  `mode="eval"`; `BinOp.left/right`, `Compare.left/comparators`,
  `Call.func/args/keywords`, `IfExp.test/body/orelse`, ...).
- `danthedeckie/simpleeval` (`simpleeval.py`) — bo tinh AST duoc dung rong
  nhat cua Python. Khuon o day lay dung hai y cua ho:
  (1) **bang phan phoi theo dang nut** (`self.nodes = {ast.Name: ..., ...}`),
      dang nut khong co trong bang thi **tu choi** — cho phep theo danh sach
      trang, khong phai cam theo danh sach den;
  (2) **`operators` / `functions` / `names` la tham so cua bo tinh**, khong
      phai hang so trong than ham — dung mot bo ruot cho nhieu cau hinh.
  ⛔ KHONG lay `simpleeval` lam thu vien: no cho `Attribute`, cho `Subscript`,
  cho `**` (chan bang `MAX_POWER`), va bang `DISALLOW_FUNCTIONS` cua no la
  danh sach **den** — ba thu ma `timeout_expr` cam tuyet doi. Ho phai chay theo
  duoi (doc danh sach `Contributors`: nhieu dong la "Reported breakout via ...")
  vi be mat cua ho rong. Be mat cua ta hep, nen ta khong phai chay theo.
"""
from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

__all__ = ["ChinhSach", "kiem_cay", "tinh_cay", "ten_duoc_doc"]


@dataclass(frozen=True, eq=False)
class ChinhSach:
    """Mot PHUONG NGU: may duyet doc bang nay chu khong tu quyet dinh gi.

    ⚠️ `van_ban` giu NGUYEN VAN cau loi cua tung phuong ngu. Cau loi la mot
       phan hop dong — `registry` dan no vao `RegistryError` va nguoi khai tool
       doc no de sua. Doi cau chu la doi hop dong.
    """

    #: Ten phuong ngu — de doc khi go roi, khong hien cho nguoi dung.
    ten: str
    #: Lop ngoai le may nem. Moi tang giu lop loi cua rieng no.
    lop_loi: type[Exception]
    #: Dang nut AST duoc di qua. ⛔ Danh sach TRANG: khong co trong day thi tu
    #: choi, ke ca khi may biet cach xu ly no.
    nut_cho_phep: frozenset[type]
    #: Kieu hang so duoc phep (`isinstance`).
    kieu_hang_so: tuple[type, ...]
    nhi_phan: Mapping[type, Callable[[Any, Any], Any]]
    mot_ngoi: Mapping[type, Callable[[Any], Any]]
    so_sanh: Mapping[type, Callable[[Any, Any], Any]]
    logic: frozenset[type]
    #: Bang ham. Ten trong bang cung duoc dung nhu mot `Name` tran luc KIEM
    #: (simpleeval `_eval_name` cung lui ve `self.functions`).
    ham: Mapping[str, Callable[..., Any]]
    #: Cho `f(x=1)` hay khong.
    cho_tham_so_ten: bool
    #: Toan tu ma ve phai bang 0 la loi NOI RO chu khong phai `ZeroDivisionError`.
    chia_bang_0: frozenset[type]
    van_ban: Mapping[str, str]

    def loi(self, ma: str, **tham) -> Exception:
        return self.lop_loi(self.van_ban[ma].format(**tham))


# ── KIEM: di het cay, khong tinh gi ────────────────────────────────────────

def kiem_cay(nut: ast.AST, cs: ChinhSach, ten_cho_phep: set[str]) -> None:
    """Duyet. Sai thi nem `cs.lop_loi` voi cau noi ro SAI O DAU.

    ⭐ Nut KHONG nam trong `cs.nut_cho_phep` bi tu choi **truoc** khi may xem
       ben trong no. Nen them mot dang nut vao may khong tu dong mo no cho
       phuong ngu nao — phai them vao bang.
    """
    if type(nut) not in cs.nut_cho_phep:
        raise cs.loi("cu_phap", ten=type(nut).__name__)

    if isinstance(nut, ast.Expression):
        return kiem_cay(nut.body, cs, ten_cho_phep)

    if isinstance(nut, ast.Constant):
        if isinstance(nut.value, cs.kieu_hang_so):
            return
        raise cs.loi("hang_so", kieu=type(nut.value).__name__)

    if isinstance(nut, ast.Name):
        if nut.id in cs.ham:
            return
        if nut.id not in ten_cho_phep:
            raise cs.loi("ten", ten=repr(nut.id),
                         co=sorted(ten_cho_phep) or cs.van_ban["khong_co_ten"])
        return

    if isinstance(nut, ast.BinOp):
        if type(nut.op) not in cs.nhi_phan:
            raise cs.loi("nhi_phan", ten=type(nut.op).__name__)
        kiem_cay(nut.left, cs, ten_cho_phep)
        return kiem_cay(nut.right, cs, ten_cho_phep)

    if isinstance(nut, ast.UnaryOp):
        if type(nut.op) not in cs.mot_ngoi:
            raise cs.loi("mot_ngoi", ten=type(nut.op).__name__)
        return kiem_cay(nut.operand, cs, ten_cho_phep)

    if isinstance(nut, ast.Compare):
        for op in nut.ops:
            if type(op) not in cs.so_sanh:
                raise cs.loi("so_sanh", ten=type(op).__name__)
        kiem_cay(nut.left, cs, ten_cho_phep)
        for v in nut.comparators:
            kiem_cay(v, cs, ten_cho_phep)
        return

    if isinstance(nut, ast.BoolOp):
        if type(nut.op) not in cs.logic:
            raise cs.loi("logic")
        for v in nut.values:
            kiem_cay(v, cs, ten_cho_phep)
        return

    if isinstance(nut, ast.IfExp):
        kiem_cay(nut.test, cs, ten_cho_phep)
        kiem_cay(nut.body, cs, ten_cho_phep)
        return kiem_cay(nut.orelse, cs, ten_cho_phep)

    if isinstance(nut, ast.Call):
        # ⚠️ Chi chap `Name` TRAN. `a.b()` di qua `ast.Attribute` — neu phuong
        #    ngu khong mo `Attribute` thi no da chet o cua tren; neu co mo thi
        #    van chet o day. Mot chuoi thuoc tinh la duong ra khoi tap gia tri
        #    da khai.
        if not isinstance(nut.func, ast.Name) or nut.func.id not in cs.ham:
            raise cs.loi("goi", ds=sorted(cs.ham))
        if nut.keywords and not cs.cho_tham_so_ten:
            raise cs.loi("tu_khoa")
        for v in nut.args:
            kiem_cay(v, cs, ten_cho_phep)
        return

    # ⛔ Loi lap trinh cua MAY, khong phai loi cua nguoi khai: mot dang nut da
    #    duoc bang cho phep ma may khong biet di vao. Khong duoc im lang cho
    #    qua — im lang o day nghia la khong duyet phan con lai cua cay.
    raise cs.loi("cu_phap", ten=type(nut).__name__)


# ── TINH: ⛔ KHONG `eval`/`exec`/`compile` ─────────────────────────────────

def tinh_cay(nut: ast.AST, cs: ChinhSach, moi_truong: Mapping[str, Any]) -> Any:
    """Tinh mot nut da duyet.

    Bo tinh de quy nay dai hon mot lenh dung san, va do la cai gia dung. Mot
    lenh dung san "an toan vi da duyet AST truoc" van dua vao viec bo duyet
    KHONG BO SOT mot dang nut nao. Bo tinh nay thi khong co gi de bo sot — thu
    no khong biet tinh, no khong tinh.

    ⚠️ Van kiem lai dang nut o day chu khong tin tang tren.
    """
    if type(nut) not in cs.nut_cho_phep:
        raise cs.loi("cu_phap", ten=type(nut).__name__)

    if isinstance(nut, ast.Expression):
        return tinh_cay(nut.body, cs, moi_truong)
    if isinstance(nut, ast.Constant):
        return nut.value
    if isinstance(nut, ast.Name):
        # ⛔ KHONG lui ve `cs.ham` o day (khac voi `kiem_cay`): mot ten ham
        #    dung tran thi khong co GIA TRI nao de tra.
        if nut.id not in moi_truong:
            raise cs.loi("khong_co_gia_tri", ten=repr(nut.id))
        return moi_truong[nut.id]
    if isinstance(nut, ast.BinOp):
        pt = cs.nhi_phan.get(type(nut.op))
        if pt is None:
            raise cs.loi("nhi_phan_tinh", ten=type(nut.op).__name__)
        phai = tinh_cay(nut.right, cs, moi_truong)
        if type(nut.op) in cs.chia_bang_0 and phai == 0:
            raise cs.loi("chia_0")
        return pt(tinh_cay(nut.left, cs, moi_truong), phai)
    if isinstance(nut, ast.UnaryOp):
        pt_mot = cs.mot_ngoi.get(type(nut.op))
        if pt_mot is None:
            raise cs.loi("mot_ngoi", ten=type(nut.op).__name__)
        return pt_mot(tinh_cay(nut.operand, cs, moi_truong))
    if isinstance(nut, ast.Compare):
        trai = tinh_cay(nut.left, cs, moi_truong)
        # `strict=True` dung nghia o day chu khong chi de qua linter: trong mot
        # `ast.Compare` hop le, `ops` va `comparators` LUON cung do dai. Neu mot
        # ngay nao do chung lech thi im lang cat bot ve ngan hon la bo qua mot
        # phep so sanh — tuc tinh ra mot con so tran KHAC voi thu da khai.
        for op, ve in zip(nut.ops, nut.comparators, strict=True):
            pt_ss = cs.so_sanh.get(type(op))
            if pt_ss is None:
                raise cs.loi("so_sanh", ten=type(op).__name__)
            phai = tinh_cay(ve, cs, moi_truong)
            if not pt_ss(trai, phai):
                return False
            trai = phai
        return True
    if isinstance(nut, ast.BoolOp):
        # ⚠️ KHONG cat mach (`simpleeval` co cat, Python co cat). O day moi ve
        #    deu duoc tinh va ket qua la `bool` — `a or b` tra `True`, khong
        #    tra `b`. Doi cho nay la doi gia tri mot tran da phat hanh.
        gia_tri = [tinh_cay(v, cs, moi_truong) for v in nut.values]
        return all(gia_tri) if isinstance(nut.op, ast.And) else any(gia_tri)
    if isinstance(nut, ast.IfExp):
        return (tinh_cay(nut.body, cs, moi_truong)
                if tinh_cay(nut.test, cs, moi_truong)
                else tinh_cay(nut.orelse, cs, moi_truong))
    if isinstance(nut, ast.Call):
        if not isinstance(nut.func, ast.Name) or nut.func.id not in cs.ham:
            raise cs.loi("goi_tinh", ds=sorted(cs.ham))
        return cs.ham[nut.func.id](
            *[tinh_cay(v, cs, moi_truong) for v in nut.args])
    raise cs.loi("cu_phap", ten=type(nut).__name__)


def ten_duoc_doc(cay: ast.AST, cs: ChinhSach) -> set[str]:
    """Tap `Name` ma cay doc toi, tru cac ten nam trong bang ham."""
    return {n.id for n in ast.walk(cay)
            if isinstance(n, ast.Name) and n.id not in cs.ham}
