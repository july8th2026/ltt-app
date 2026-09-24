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
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

__all__ = [
    # may + chinh sach (dung chung)
    "ChinhSach", "kiem_cay", "tinh_cay", "ten_duoc_doc",
    # ngon ngu §6 — chinh sach DAY DU
    "DAY_DU", "KhongGianNodes", "LoiNgonNgu", "NAMESPACE", "TRAN_CHUOI",
    "TRAN_NUT", "TRAN_SAU", "chinh_sach_day_du", "do_gioi_han",
    "kiem_ngon_ngu", "moi_truong_wf", "tinh_ngon_ngu",
]


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
    #: ⚠️ Kieu la `Callable[..., Exception]` chu khong `type[Exception]`: mot
    #:    so phuong ngu nhan them `vi_tri=` (§6.4 doi loi mang cot). Day la mot
    #:    XUONG LAM LOI, va cac phuong ngu khong cung chu ky.
    lop_loi: Callable[..., Exception]
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

    # ── NANG LUC (mac dinh TAT) ────────────────────────────────────────────
    #
    # ⭐ Moi o duoi day la mot NANG LUC rieng, khong phai mot dang nut. Ly do:
    #    `test_1761` do rang mo `ast.Attribute` trong `nut_cho_phep` cua
    #    `NGHIEM` **van** bi tu choi — luc do vi may chua biet di vao nut do.
    #    Nay may da biet (ngon ngu §6 can), nen cho "lop thu hai" phai chuyen
    #    thanh mot o KHAI BAO DUOC, khong con la mot lo hong trong hieu biet
    #    cua may. Mot phuong ngu muon `a.b` thi phai noi ra rang no muon.

    #: Ham doc `a.b`. `None` ⇒ mo-dun khong co `Attribute`, du bang co mo.
    doc_thuoc_tinh: Callable[[Any, str], Any] | None = None
    #: Ham doc `a[k]`. `None` ⇒ khong co `Subscript`.
    doc_khoa: Callable[[Any, Any], Any] | None = None
    #: Cho hang ghep `[...]` / `{...}` hay khong.
    cho_ghep: bool = False
    #: `and`/`or` cat mach (ve phai khong duoc tinh khi da biet ket qua).
    #: ⛔ `NGHIEM` de `False` CO CHU DICH — doi no la doi gia tri mot tran
    #:    `max_runtime_s` da phat hanh (xem `tinh_cay`).
    cat_mach: bool = False
    #: Chuoi truy cap moc tu ten nay phai TINH hoan toan (`nodes["b-2"]` duoc,
    #: `nodes[vars.k]` khong). `None` ⇒ khong co luat nay.
    goc_phai_tinh: str | None = None
    #: Tran do sau cay / so nut. `None` ⇒ khong do.
    #: ⚠️ Tran DO DAI CHUOI khong o day co chu dich: no la hang so mo-dun
    #:    `TRAN_CHUOI`, vi ca `noi_suy.py` lan `+` cua §6.4 phai dung CUNG mot
    #:    con so. Khai hai cho thi mot ngay nao do hai cho khac nhau.
    tran_sau: int | None = None
    tran_nut: int | None = None
    #: `lop_loi` nhan `vi_tri=` hay khong (§6.4 doi loi mang cot).
    loi_mang_vi_tri: bool = False

    def loi(self, ma: str, *, nut: ast.AST | None = None, **tham) -> Exception:
        cau = self.van_ban[ma].format(**tham)
        if self.loi_mang_vi_tri and nut is not None:
            return self.lop_loi(cau, vi_tri=_cot(nut))
        return self.lop_loi(cau)


def _cot(nut: ast.AST) -> int | None:
    """Cot cua mot nut, hoac `None`.

    ⛔ KHONG `getattr` (banh coc `test_1766::test_module_KHONG_co_cua_thi_hanh`
       cam ca mo-dun nay dung no): `ast.operator`/`ast.cmpop` — `Add`, `Eq`, ...
       — that su KHONG co `col_offset`, nen day la mot cau hoi ve KIEU, tra loi
       bang `isinstance`, chu khong phai mot phep doc thuoc tinh dong.
    """
    return nut.col_offset if isinstance(nut, (ast.expr, ast.stmt)) else None


# ── KIEM: di het cay, khong tinh gi ────────────────────────────────────────

def kiem_cay(nut: ast.AST, cs: ChinhSach, ten_cho_phep: set[str]) -> None:
    """Duyet. Sai thi nem `cs.lop_loi` voi cau noi ro SAI O DAU.

    ⭐ Nut KHONG nam trong `cs.nut_cho_phep` bi tu choi **truoc** khi may xem
       ben trong no. Nen them mot dang nut vao may khong tu dong mo no cho
       phuong ngu nao — phai them vao bang.
    """
    if type(nut) not in cs.nut_cho_phep:
        raise cs.loi("cu_phap", ten=type(nut).__name__, nut=nut)

    if isinstance(nut, ast.Expression):
        return kiem_cay(nut.body, cs, ten_cho_phep)

    if isinstance(nut, ast.Constant):
        if isinstance(nut.value, cs.kieu_hang_so):
            return
        raise cs.loi("hang_so", kieu=type(nut.value).__name__, nut=nut)

    if isinstance(nut, ast.Name):
        if nut.id in cs.ham:
            return
        if nut.id not in ten_cho_phep:
            raise cs.loi("ten", ten=repr(nut.id),
                         co=sorted(ten_cho_phep) or cs.van_ban["khong_co_ten"],
                         nut=nut)
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
            raise cs.loi("tu_khoa", nut=nut)
        for v in nut.args:
            kiem_cay(v, cs, ten_cho_phep)
        return

    if isinstance(nut, ast.Attribute):
        if cs.doc_thuoc_tinh is None:
            raise cs.loi("cu_phap", ten="Attribute", nut=nut)
        if nut.attr.startswith("_"):
            raise cs.loi("thuoc_tinh_rieng", ten=nut.attr, nut=nut)
        return kiem_cay(nut.value, cs, ten_cho_phep)

    if isinstance(nut, ast.Subscript):
        if cs.doc_khoa is None:
            raise cs.loi("cu_phap", ten="Subscript", nut=nut)
        khoa = nut.slice
        tinh_khoa = (isinstance(khoa, ast.Constant)
                     and isinstance(khoa.value, (str, int))
                     and not isinstance(khoa.value, bool))
        if (isinstance(khoa, ast.Constant) and isinstance(khoa.value, str)
                and khoa.value.startswith("_")):
            raise cs.loi("thuoc_tinh_rieng", ten=khoa.value, nut=nut)
        # ⭐ Cung luat hinh dang voi cong publish (`bien_dich.trich_tham_chieu`):
        #    mot tham chieu `nodes[...]` DONG khong kiem duoc to tien luc
        #    publish, nen no cung khong duoc phep TON TAI luc chay. Hai cua
        #    cung mot luat — neu khong, cai nao khong ai di qua la trang tri.
        if (cs.goc_phai_tinh is not None and not tinh_khoa
                and _goc_ten(nut) == cs.goc_phai_tinh):
            raise cs.loi("goc_dong", ten=cs.goc_phai_tinh, nut=nut)
        kiem_cay(nut.value, cs, ten_cho_phep)
        return kiem_cay(khoa, cs, ten_cho_phep)

    if isinstance(nut, ast.List):
        if not cs.cho_ghep:
            raise cs.loi("cu_phap", ten="List", nut=nut)
        for v in nut.elts:
            kiem_cay(v, cs, ten_cho_phep)
        return

    if isinstance(nut, ast.Dict):
        if not cs.cho_ghep:
            raise cs.loi("cu_phap", ten="Dict", nut=nut)
        for k, v in zip(nut.keys, nut.values, strict=True):
            if k is None:                    # `{**x}` — khong co khoa de kiem
                raise cs.loi("cu_phap", ten="Dict(**)", nut=nut)
            kiem_cay(k, cs, ten_cho_phep)
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
        # ⚠️ `NGHIEM` KHONG cat mach (`simpleeval` co cat, Python co cat): moi
        #    ve deu duoc tinh va ket qua la `bool` — `a or b` tra `True`, khong
        #    tra `b`. Doi cho nay la doi gia tri mot tran da phat hanh.
        #
        # ⭐ Ngon ngu §6 thi CO cat mach (`cat_mach=True`), va do la mot luat
        #    ve SU DUNG DUOC chu khong phai ve toc do: `nodes.a.status ==
        #    "SUCCEEDED" and nodes.a.output.x > 1` phai viet duoc. Khong cat
        #    mach thi ve phai no chet trong chinh cai truong hop ma ve trai
        #    sinh ra de chan. Ket qua van la `bool` o ca hai phuong ngu.
        va = isinstance(nut.op, ast.And)
        if cs.cat_mach:
            for v in nut.values:
                if bool(tinh_cay(v, cs, moi_truong)) is not va:
                    return not va
            return va
        gia_tri = [tinh_cay(v, cs, moi_truong) for v in nut.values]
        return all(gia_tri) if va else any(gia_tri)
    if isinstance(nut, ast.IfExp):
        return (tinh_cay(nut.body, cs, moi_truong)
                if tinh_cay(nut.test, cs, moi_truong)
                else tinh_cay(nut.orelse, cs, moi_truong))
    if isinstance(nut, ast.Call):
        if not isinstance(nut.func, ast.Name) or nut.func.id not in cs.ham:
            raise cs.loi("goi_tinh", ds=sorted(cs.ham), nut=nut)
        return cs.ham[nut.func.id](
            *[tinh_cay(v, cs, moi_truong) for v in nut.args])
    if isinstance(nut, ast.Attribute):
        if cs.doc_thuoc_tinh is None:
            raise cs.loi("cu_phap", ten="Attribute", nut=nut)
        goc = tinh_cay(nut.value, cs, moi_truong)
        with _dinh_vi(nut):
            return cs.doc_thuoc_tinh(goc, nut.attr)
    if isinstance(nut, ast.Subscript):
        if cs.doc_khoa is None:
            raise cs.loi("cu_phap", ten="Subscript", nut=nut)
        goc = tinh_cay(nut.value, cs, moi_truong)
        khoa = tinh_cay(nut.slice, cs, moi_truong)
        with _dinh_vi(nut):
            return cs.doc_khoa(goc, khoa)
    if isinstance(nut, ast.List):
        if not cs.cho_ghep:
            raise cs.loi("cu_phap", ten="List", nut=nut)
        return [tinh_cay(v, cs, moi_truong) for v in nut.elts]
    if isinstance(nut, ast.Dict):
        if not cs.cho_ghep:
            raise cs.loi("cu_phap", ten="Dict", nut=nut)
        ra: dict[str, Any] = {}
        for k, v in zip(nut.keys, nut.values, strict=True):
            if k is None:
                raise cs.loi("cu_phap", ten="Dict(**)", nut=nut)
            ten_khoa = tinh_cay(k, cs, moi_truong)
            if not isinstance(ten_khoa, str):
                raise cs.loi("khoa_object", kieu=type(ten_khoa).__name__,
                             nut=nut)
            ra[ten_khoa] = tinh_cay(v, cs, moi_truong)
        return ra
    raise cs.loi("cu_phap", ten=type(nut).__name__, nut=nut)


def _goc_ten(nut: ast.AST) -> str | None:
    """Ten `Name` ma mot chuoi truy cap moc len tu do (`nodes[x].y` → `nodes`)."""
    while isinstance(nut, (ast.Attribute, ast.Subscript)):
        nut = nut.value
    return nut.id if isinstance(nut, ast.Name) else None


@contextmanager
def _dinh_vi(nut: ast.AST):
    """Dan cot cua `nut` vao `LoiNgonNgu` nem tu mot ham doc du lieu.

    Ham doc (`doc_thuoc_tinh`/`doc_khoa`) biet CAI GI hut nhung khong biet no
    nam o cot nao; chi cho nay biet. ⚠️ Chi dan khi loi CHUA co vi tri — mot
    loi tu sau trong chuoi truy cap da mang cot dung hon.
    """
    try:
        yield
    except LoiNgonNgu as loi:
        raise loi.dinh_vi(vi_tri=_cot(nut)) from None


def ten_duoc_doc(cay: ast.AST, cs: ChinhSach) -> set[str]:
    """Tap `Name` ma cay doc toi, tru cac ten nam trong bang ham."""
    return {n.id for n in ast.walk(cay)
            if isinstance(n, ast.Name) and n.id not in cs.ham}


# ═══════════════════════════════════════════════════════════════════════════
#  NGON NGU BIEU THUC §6 — chinh sach DAY DU
# ═══════════════════════════════════════════════════════════════════════════
#
# ⭐ TRA NGUON TRUOC KHI TU SUY — ba quyet dinh duoi day deu co nguon, va mot
#    trong so do LAT NGUOC mot cau trong brief cua task.
#
# 1. `"a" == 1` ⇒ `false`, khong nem (spec §6.4).
#    `google/cel-spec` `doc/langdef.md` §Equality noi RO rang CEL co HAI hanh
#    vi khac nhau: *"Type-checking asserts that arguments to equality operators
#    must be the same type. If the argument types differ, the type-checker will
#    raise an error"* — nhung *"the runtime uses heterogeneous equality"*, va
#    ho viet thang cong thuc: `type(x) == type(y) ? x == y : false`. Ly do ho
#    ghi ngay duoi: **du lieu JSON** — so co the la `double` hay `int` tuy
#    runtime. Ta o dung hoan canh do (params tu JSON), nen ta lay luat RUNTIME
#    cua CEL va bo luat type-checker cua ho.
#    ⇒ Con "CEL nem" trong brief la dung VE TYPE-CHECKER, khong dung ve runtime.
#
# 2. `1 == 1.0` ⇒ `true`, `true == 1` ⇒ `false`.
#    Cung tep tren, muc Numbers: `int`/`uint`/`double` duoc so *"as though they
#    exist on a continuous number line"*. `bool` KHONG nam trong danh sach do,
#    nen `true == 1` roi ve nhanh `type(x) == type(y) ? ... : false`.
#    ⚠️ Python noi NGUOC: `1 == True` la `True` va `True + 1` la `2`, vi `bool`
#       ke thua `int` (do duoc, khong phai tri nho — xem bao cao task). JSON thi
#       co `true`/`false` rieng. Ta theo JSON/CEL, khong theo Python.
#
# 3. `1 + 1.5` ⇒ `2.5`.
#    §6.4 chi cam **mot** phep ep ngam: *"Khong ep ngam giua chuoi va so"*.
#    int/float deu la "so". CEL nem o day (khong co overload `int + double`) va
#    do chinh la mot ly do loai CEL: `json.loads('{"a": 1, "b": 1.5}')` cho ra
#    ca hai kieu trong CUNG mot payload cua khach.
#
# 4. Tran do sau / so nut kiem TRUOC khi tinh.
#    `google/cel-go` `parser/alias.go` co ca `MaxRecursionDepth(limit)` lan
#    `MaxExpressionNodeCount(limit)` — hai tran o tang PARSER chu khong o tang
#    eval. Ta lam cung the va vi mot ly do do duoc tren may nay (§ `do_gioi_han`).
#
# 5. Khong co `safe_mult`.
#    `danthedeckie/simpleeval` phai co `MAX_STRING_LENGTH = 100000` va mot phep
#    kiem `b * len(a) > MAX_STRING_LENGTH` trong `safe_mult`, vi ngon ngu cua ho
#    cho `"x" * n`. §6.4 cua ta khong cho `*` giua chuoi va so, nen phep nhan
#    KHONG con la duong phong to du lieu — mot lenh cam re hon mot cai phanh.

#: §6.4. Do sau cay AST (tinh ca nut `ast.Expression` goc).
TRAN_SAU = 32
#: §6.4. So nut AST toi da.
TRAN_NUT = 10_000
#: §6.4. Chuoi vao, chuoi ra va ket qua: 1 MB. CUNG con so voi `noi_suy.py`.
TRAN_CHUOI = 1024 * 1024

#: §6.2. Bay namespace, va KHONG co gi khac: khong `env`, khong `credentials`,
#: khong `now()` (dung `run.started_at`/`trigger.fired_at` de tinh lai ra cung
#: ket qua).
NAMESPACE = ("loop", "nodes", "params", "run", "trigger", "vars", "workflow")

#: §6.1: `true/false/null` la hang so cua ngon ngu. (`True/False/None` cung
#: chay, vi `ast` doc chung thanh `Constant` chu khong thanh `Name`.)
HANG_SO_TEN = {"true": True, "false": False, "null": None}


class LoiNgonNgu(ValueError):
    """Loi cua ngon ngu §6. Mang `ly_do`, `vi_tri` (cot), `bieu_thuc` (cat 200).

    ⚠️ CO Y khong ke thua `bieu_thuc.LoiBieuThuc` — cung ly do `noi_suy.py` neu:
       hai tang phai test duoc roi nhau, va `LoiBieuThuc` la hop dong cua
       `timeout_expr`, khong phai cua ngon ngu nay.
    """

    def __init__(self, ly_do: str, *, vi_tri: int | None = None,
                 bieu_thuc: str = "") -> None:
        self.ly_do = ly_do
        self.vi_tri = vi_tri
        self.bieu_thuc = (bieu_thuc or "")[:200]
        super().__init__(self._cau())

    def _cau(self) -> str:
        cau = self.ly_do
        if self.vi_tri is not None:
            cau += f" (cot {self.vi_tri})"
        if self.bieu_thuc:
            cau += f": {self.bieu_thuc}"
        return cau

    def dinh_vi(self, *, vi_tri: int | None = None,
                bieu_thuc: str | None = None) -> LoiNgonNgu:
        """Dan cot / nguyen van vao — CHI khi chua co. Tra chinh no, de `raise`."""
        if vi_tri is not None and self.vi_tri is None:
            self.vi_tri = vi_tri
        if bieu_thuc and not self.bieu_thuc:
            self.bieu_thuc = bieu_thuc[:200]
        self.args = (self._cau(),)
        return self


# ── §6.4 GIOI HAN: do bang VONG LAP, truoc khi de quy vao cay ──────────────

def do_gioi_han(cay: ast.AST, cs: ChinhSach) -> None:
    """Tu choi cay qua sau / qua nhieu nut. ⛔ KHONG de quy.

    🔑 Vi sao vong lap chu khong de quy: ham nay ton tai de bao ve bo duyet de
       quy. Neu chinh no de quy theo cay thi no chet dung o cai truong hop no
       sinh ra de chan — do la mot cai phanh lam bang giay.

    ⚠️ Do duoc tren may nay (Python 3.13.12, `sys.getrecursionlimit() == 1000`):
       `"not " * 2000 + "1"` phan tich TOT, cho cay sau 2002; mot bo duyet de
       quy chet voi `RecursionError` o cay do. Tran 32 chan no o nut thu 33.
       ⇒ `test_1766::test_tran_sau_chan_TRUOC_khi_Python_het_ngan_xep` giu
         bang chung do, va tiem loi (bo tran) de thay `RecursionError` that.
    """
    if cs.tran_sau is None and cs.tran_nut is None:
        return
    dem = 0
    ngan_xep: list[tuple[ast.AST, int]] = [(cay, 1)]
    while ngan_xep:
        nut, sau = ngan_xep.pop()
        dem += 1
        if cs.tran_sau is not None and sau > cs.tran_sau:
            raise cs.loi("qua_sau", tran=cs.tran_sau, nut=nut)
        if cs.tran_nut is not None and dem > cs.tran_nut:
            raise cs.loi("qua_nhieu_nut", tran=cs.tran_nut, nut=nut)
        ngan_xep.extend((con, sau + 1) for con in ast.iter_child_nodes(nut))


def _kich_thuoc(gia_tri: Any, tran: int) -> int:
    """Uoc kich thuoc mot gia tri JSON, DUNG NGAY khi vuot `tran`.

    ⚠️ Day la mot UOC LUONG (ky tu + so o), khong phai `sys.getsizeof`. Muc
       dich la chan mot ket qua khong gui di dau duoc, khong phai ke toan bo
       nho. Di bang vong lap vi du lieu tu khach co the long rat sau.
    """
    tong = 0
    ngan_xep: list[Any] = [gia_tri]
    while ngan_xep:
        v = ngan_xep.pop()
        if isinstance(v, str):
            tong += len(v) + 2
        elif isinstance(v, Mapping):
            tong += 2
            for k, x in v.items():
                tong += len(k) + 4 if isinstance(k, str) else 8
                ngan_xep.append(x)
        elif isinstance(v, (list, tuple)):
            tong += 2 + len(v)
            ngan_xep.extend(v)
        else:
            tong += 8
        if tong > tran:
            return tong
    return tong


def _chan_tran_chuoi(gia_tri: Any) -> Any:
    """`+` khong duoc de ket qua vuot 1 MB (§6.4)."""
    if _kich_thuoc(gia_tri, TRAN_CHUOI) > TRAN_CHUOI:
        raise LoiNgonNgu(
            f"ket qua vuot tran {TRAN_CHUOI} ky tu (1 MB)")
    return gia_tri


# ── §6.2 NAMESPACE: doc, va CHI doc ───────────────────────────────────────

def _ten_kieu(v: Any) -> str:
    """Ten kieu theo NGON NGU (JSON), khong theo Python."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "so"
    if isinstance(v, str):
        return "chuoi"
    if isinstance(v, (list, tuple)):
        return "danh sach"
    if isinstance(v, Mapping):
        return "object"
    return type(v).__name__


def _khoa_hien(goc: Mapping) -> list[str]:
    """Khoa de goi y trong cau loi.

    ⛔ Bo khoa bat dau `_`: §6.1 cam DOC chung, nen liet ke chung trong mot cau
       loi la mot duong ro ri ten — ke tan cong khong doc duoc gia tri nhung
       biet duoc co gi o do.
    """
    return sorted(k for k in goc if isinstance(k, str)
                  and not k.startswith("_"))


def _doc_khoa(goc: Any, khoa: Any) -> Any:
    """`a[k]` va (qua `_doc_thuoc_tinh`) `a.k` — mot luat cho ca hai cua."""
    if isinstance(khoa, str) and khoa.startswith("_"):
        raise LoiNgonNgu(f"khoa {khoa!r} bat dau bang `_` — khong doc duoc")
    if goc is None:
        raise LoiNgonNgu(f"gia tri la null, khong doc duoc {khoa!r} cua no")
    if isinstance(goc, Mapping):
        if not isinstance(khoa, str):
            raise LoiNgonNgu(
                f"khoa cua object phai la chuoi, gap {_ten_kieu(khoa)}")
        try:
            return goc[khoa]
        except KeyError:
            raise LoiNgonNgu(
                f"khong co khoa {khoa!r} (co: {_khoa_hien(goc)})") from None
    if isinstance(goc, (list, tuple)):
        if isinstance(khoa, bool) or not isinstance(khoa, int):
            raise LoiNgonNgu(
                f"chi so cua danh sach phai la so nguyen, gap "
                f"{_ten_kieu(khoa)}")
        try:
            return goc[khoa]
        except IndexError:
            raise LoiNgonNgu(
                f"chi so {khoa} ngoai dai — danh sach co {len(goc)} phan tu"
            ) from None
    raise LoiNgonNgu(
        f"kieu {_ten_kieu(goc)} khong doc duoc {khoa!r} — no khong phai object "
        f"hay danh sach (dung ham §6.3)")


def _doc_thuoc_tinh(goc: Any, ten: str) -> Any:
    """`a.b`. ⛔ KHONG `getattr`: mot object Python khong bao gio mo ra o day.

    ⭐ Do la ca diem: `vars.s.upper` khong tra ve phuong thuc `str.upper` ma
       bao loi, vi duong duy nhat toi mot gia tri la **khoa cua du lieu**.
    """
    if ten.startswith("_"):
        raise LoiNgonNgu(f"thuoc tinh {ten!r} bat dau bang `_` — khong doc duoc")
    if not isinstance(goc, Mapping) and not isinstance(goc, (list, tuple)):
        raise LoiNgonNgu(
            f"kieu {_ten_kieu(goc)} khong co thuoc tinh {ten!r} "
            f"(dung ham §6.3)")
    if isinstance(goc, (list, tuple)):
        raise LoiNgonNgu(
            f"kieu danh sach khong co thuoc tinh {ten!r} — dung `[chi so]` "
            f"hoac ham §6.3")
    return _doc_khoa(goc, ten)


class _CongRa(Mapping):
    """`nodes.<id>.output` — tap cong RA cua mot node da chay xong."""

    def __init__(self, nid: str, cong: Mapping[str, Any]) -> None:
        self._nid, self._cong = nid, dict(cong)

    def __getitem__(self, khoa: str) -> Any:
        if khoa not in self._cong:
            raise LoiNgonNgu(
                f"cong {khoa!r} cua node {self._nid!r} chua co gia tri "
                f"(node tra: {_khoa_hien(self._cong)})")
        return self._cong[khoa]

    def __iter__(self):
        return iter(self._cong)

    def __len__(self) -> int:
        return len(self._cong)


class _MatNode(Mapping):
    """Ba mat doc duoc cua mot node (§6.2): `output`, `status`, `error`."""

    MAT = ("output", "status", "error")

    def __init__(self, nid: str, ban_ghi: Mapping[str, Any]) -> None:
        self._nid, self._ban_ghi = nid, ban_ghi

    def __getitem__(self, khoa: str) -> Any:
        if khoa not in self.MAT:
            raise LoiNgonNgu(
                f"nodes.{self._nid}.{khoa} khong doc duoc — chi "
                f"{list(self.MAT)} (spec §6.2)")
        if khoa == "output":
            trang_thai = self._ban_ghi.get("status")
            # ⛔ Node chua chay xong thi output KHONG phai "rong", no la CHUA
            #    TON TAI. Tra `None` o day la noi doi mot cach im lang, va cai
            #    `None` do se di tiep vao mot node co tinh tien.
            if trang_thai != "SUCCEEDED":
                raise LoiNgonNgu(
                    f"node {self._nid!r} chua chay xong (trang thai: "
                    f"{trang_thai!r}) — chua doc duoc output cua no")
            return _CongRa(self._nid, self._ban_ghi.get("output") or {})
        return self._ban_ghi.get(khoa)

    def __iter__(self):
        return iter(self.MAT)

    def __len__(self) -> int:
        return len(self.MAT)


class KhongGianNodes(Mapping):
    """`nodes` cua §6.2 — chi doc, va noi ro khi doc hut.

    Nhan mot anh chup `{id: {"status": ..., "output": {...}, "error": ...}}`.
    ⚠️ Nhan MAP chu khong nhan doi tuong run: tang nay khong duoc biet CSDL, va
       ai nap anh chup do la viec cua tang dong co.
    """

    def __init__(self, anh_chup: Mapping[str, Mapping[str, Any]]) -> None:
        self._anh_chup = anh_chup

    def __getitem__(self, khoa: str) -> _MatNode:
        ban_ghi = self._anh_chup.get(khoa)
        if ban_ghi is None:
            # ⛔ KHONG ke ra danh sach id node: mot do thi co hang tram node, va
            #    cau loi dai khong giup ai. Id node la thu nguoi go tu viet.
            raise LoiNgonNgu(
                f"node {khoa!r} khong co trong run — tham chieu phai la node "
                f"TO TIEN da chay")
        return _MatNode(khoa, ban_ghi)

    def __iter__(self):
        return iter(self._anh_chup)

    def __len__(self) -> int:
        return len(self._anh_chup)


def moi_truong_wf(*, trigger: Any = None, workflow_input: Any = None,
                  vars: Any = None, nodes: Any = None, loop: Any = None,
                  run: Any = None, params: Any = None) -> dict[str, Any]:
    """Moi truong §6.2 cho mot lan tinh. Bay namespace + ba hang so ten.

    ⚠️ Namespace KHONG duoc truyen vao thi VANG MAT han, khong phai rong: doc
       `loop.item` ngoai than ForEach phai bao *"khong co `loop`"*, chu khong
       phai *"`loop` khong co khoa `item`"*. Hai cau do dan nguoi go di hai
       huong khac nhau.
    """
    mt: dict[str, Any] = dict(HANG_SO_TEN)
    if trigger is not None:
        mt["trigger"] = trigger
    if workflow_input is not None:
        mt["workflow"] = {"input": workflow_input}
    if vars is not None:
        mt["vars"] = vars
    if nodes is not None:
        mt["nodes"] = (nodes if isinstance(nodes, KhongGianNodes)
                       else KhongGianNodes(nodes))
    if loop is not None:
        mt["loop"] = loop
    if run is not None:
        mt["run"] = run
    if params is not None:
        mt["params"] = params
    return mt


# ── §6.4 EP KIEU: bang toan tu cua phuong ngu DAY DU ──────────────────────

def _la_so(v: Any) -> bool:
    """`bool` KHONG phai so — xem ghi chu nguon (2) o dau muc nay."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _loi_kieu(toan_tu: str, a: Any, b: Any, them: str = "") -> LoiNgonNgu:
    return LoiNgonNgu(
        f"kieu khong khop: `{toan_tu}` giua {_ten_kieu(a)} va {_ten_kieu(b)}"
        + (f" — {them}" if them else ""))


def _cong(a: Any, b: Any) -> Any:
    if _la_so(a) and _la_so(b):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return _chan_tran_chuoi(a + b)
    if isinstance(a, list) and isinstance(b, list):
        return _chan_tran_chuoi(a + b)
    if (isinstance(a, str) and _la_so(b)) or (_la_so(a) and isinstance(b, str)):
        raise _loi_kieu("+", a, b,
                        "khong ep ngam (§6.4) — dung to_number() hoac "
                        "to_string()")
    raise _loi_kieu("+", a, b, "`+` chi cong hai so, hai chuoi hoac hai "
                               "danh sach")


def _hai_so(toan_tu: str) -> Callable[[Any, Any], Any]:
    def phep(a: Any, b: Any) -> Any:
        if not (_la_so(a) and _la_so(b)):
            them = ("dung to_number()"
                    if isinstance(a, str) or isinstance(b, str) else "")
            raise _loi_kieu(toan_tu, a, b, them or f"`{toan_tu}` can hai so")
        return _PHEP_SO[toan_tu](a, b)
    return phep


_PHEP_SO: dict[str, Callable[[Any, Any], Any]] = {
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "//": lambda a, b: a // b,
    "%": lambda a, b: a % b,
}


def _bang(a: Any, b: Any) -> bool:
    """`==` cua §6.4: **khong bao gio nem**. Khac lop ⇒ `false`.

    Di bang vong lap: du lieu tu khach co the long sau hon ngan xep Python.
    """
    cap: list[tuple[Any, Any]] = [(a, b)]
    while cap:
        x, y = cap.pop()
        lx, ly = _ten_kieu(x), _ten_kieu(y)
        if lx != ly:
            return False
        if lx == "so":
            if x != y:
                return False
        elif lx == "danh sach":
            if len(x) != len(y):
                return False
            cap.extend(zip(x, y, strict=True))
        elif lx == "object":
            if set(x) != set(y):
                return False
            cap.extend((x[k], y[k]) for k in x)
        elif x != y:
            return False
    return True


def _thu_tu(toan_tu: str, phep: Callable[[Any, Any], bool]
            ) -> Callable[[Any, Any], bool]:
    def so_sanh(a: Any, b: Any) -> bool:
        if (_la_so(a) and _la_so(b)) or (isinstance(a, str)
                                         and isinstance(b, str)):
            return phep(a, b)
        # §6.4: *"So sanh khac kieu ⇒ false voi `==`, LOI voi `<`"*. Hai cau
        # khac nhau co chu dich: `==` la mot cau hoi tra loi duoc cho moi cap
        # gia tri; `a < b` giua hai kieu khong co thu tu thi khong co cau tra
        # loi nao dung — im lang chon mot cai la doan y nguoi go.
        raise _loi_kieu(toan_tu, a, b,
                        "so sanh thu tu chi tren hai so hoac hai chuoi")
    return so_sanh


def _trong(a: Any, b: Any) -> bool:
    """`a in b`."""
    if isinstance(b, str):
        if not isinstance(a, str):
            raise _loi_kieu("in", a, b, "`in` tren chuoi can chuoi o ve trai")
        return a in b
    if isinstance(b, (list, tuple)):
        return any(_bang(a, x) for x in b)
    if isinstance(b, Mapping):
        if not isinstance(a, str):
            raise _loi_kieu("in", a, b, "khoa cua object la chuoi")
        return a in b
    raise _loi_kieu("in", a, b,
                    "`in` can chuoi, danh sach hoac object o ve phai")


def _am(a: Any) -> Any:
    if not _la_so(a):
        raise LoiNgonNgu(f"kieu khong khop: `-` can mot so, gap {_ten_kieu(a)}")
    return -a


def _duong(a: Any) -> Any:
    if not _la_so(a):
        raise LoiNgonNgu(f"kieu khong khop: `+` can mot so, gap {_ten_kieu(a)}")
    return +a


VAN_BAN_DAY_DU = {
    "cu_phap": "cu phap {ten} khong duoc phep trong bieu thuc (§6.1)",
    "hang_so": "hang so kieu {kieu} khong duoc phep (chi so, chuoi, "
               "true/false/null)",
    "ten": "ten {ten} khong doc duoc — namespace §6.2 co: {co}",
    "khong_co_ten": "khong co ten nao",
    "nhi_phan": "toan tu {ten} khong duoc phep (§6.1; `**` bi cam)",
    "nhi_phan_tinh": "toan tu {ten} khong duoc phep",
    "mot_ngoi": "toan tu {ten} khong duoc phep",
    "so_sanh": "phep so sanh {ten} khong duoc phep (`is`/`is not` bi cam)",
    "logic": "phep logic khong duoc phep",
    "goi": "chi duoc goi ham trong bang §6.3: {ds}",
    "goi_tinh": "chi duoc goi ham trong bang §6.3: {ds}",
    "tu_khoa": "khong dung tham so co ten khi goi ham (§6.1)",
    "khong_co_gia_tri": "ten {ten} khong co gia tri trong moi truong",
    "chia_0": "chia cho 0",
    "thuoc_tinh_rieng": "{ten} bat dau bang `_` — khong doc duoc (§6.1)",
    "goc_dong": "tham chieu `{ten}` co doan DONG — phai viet tinh "
                '(vi du nodes["b-2"].output.text), vi cong publish kiem quan '
                "he to tien luc publish chu khong luc chay",
    "khoa_object": "khoa cua object phai la chuoi, gap {kieu}",
    "qua_sau": "bieu thuc long qua sau (tran {tran} muc, §6.4)",
    "qua_nhieu_nut": "bieu thuc qua lon (tran {tran} nut AST, §6.4)",
    "nguon_qua_dai": "bieu thuc dai qua {tran} ky tu (1 MB, §6.4)",
    "khong_phan_tich": "khong phan tich duoc: {msg}",
    "ngoac_qua_sau": "ngoac long qua sau: {msg}",
    "ket_qua_qua_lon": "ket qua vuot tran {tran} ky tu (1 MB, §6.4)",
}


def chinh_sach_day_du(*, ham: Mapping[str, Callable[..., Any]] | None = None,
                      ten: str = "ngon_ngu_6") -> ChinhSach:
    """Phuong ngu DAY DU cua §6. Bang ham di VAO qua tham so.

    ⭐ Vi sao bang ham khong nam trong mo-dun nay: `ham_bieu_thuc.py` (§6.3) la
       mot bang 49 ten co vong doi rieng. Nhan no qua tham so thi tang nay test
       duoc voi bang GIA (va `test_1766` lam dung the), va mot ngay bang do doi
       thi mo-dun nay khong phai doi theo.
    """
    return ChinhSach(
        ten=ten,
        lop_loi=LoiNgonNgu,
        nut_cho_phep=frozenset({
            ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
            ast.Compare, ast.BoolOp, ast.IfExp, ast.Call, ast.Attribute,
            ast.Subscript, ast.List, ast.Dict,
        }),
        kieu_hang_so=(bool, int, float, str, type(None)),
        nhi_phan={
            ast.Add: _cong,
            ast.Sub: _hai_so("-"),
            ast.Mult: _hai_so("*"),
            ast.Div: _hai_so("/"),
            ast.FloorDiv: _hai_so("//"),
            ast.Mod: _hai_so("%"),
        },
        mot_ngoi={ast.UAdd: _duong, ast.USub: _am,
                  ast.Not: lambda a: not bool(a)},
        so_sanh={
            ast.Eq: _bang,
            ast.NotEq: lambda a, b: not _bang(a, b),
            ast.Lt: _thu_tu("<", lambda a, b: a < b),
            ast.LtE: _thu_tu("<=", lambda a, b: a <= b),
            ast.Gt: _thu_tu(">", lambda a, b: a > b),
            ast.GtE: _thu_tu(">=", lambda a, b: a >= b),
            ast.In: _trong,
            ast.NotIn: lambda a, b: not _trong(a, b),
        },
        logic=frozenset({ast.And, ast.Or}),
        ham=dict(ham or {}),
        cho_tham_so_ten=False,
        chia_bang_0=frozenset({ast.Div, ast.FloorDiv, ast.Mod}),
        van_ban=VAN_BAN_DAY_DU,
        doc_thuoc_tinh=_doc_thuoc_tinh,
        doc_khoa=_doc_khoa,
        cho_ghep=True,
        cat_mach=True,
        goc_phai_tinh="nodes",
        tran_sau=TRAN_SAU,
        tran_nut=TRAN_NUT,
        loi_mang_vi_tri=True,
    )


#: Phuong ngu DAY DU voi bang ham RONG. Tang lap ngon ngu truyen bang that vao
#: bang `chinh_sach_day_du(ham=BANG_HAM)`.
DAY_DU = chinh_sach_day_du()


# ── Cua vao cua ngon ngu §6 ───────────────────────────────────────────────

def phan_tich(bieu_thuc: str, cs: ChinhSach = DAY_DU) -> ast.Expression:
    """`ast.parse` co bao ve. ⛔ Khong mot loi tho nao ra khoi ham nay.

    ⚠️ Ba duong chet khac nhau, do duoc tren may nay:
       - nguon > 1 MB                    ⇒ chan TRUOC khi parse;
       - `("*300`                        ⇒ `SyntaxError: too many nested
         parentheses` (CPython chan o tokenizer: `Parser/lexer/lexer.c`,
         `if (tok->level >= MAXLEVEL)`; MAXLEVEL = 200 — do: 200 qua, 300 do);
       - `"1" + "+1"*5000`               ⇒ `RecursionError: maximum recursion
         depth exceeded during ast construction` — **chinh `ast.parse` chet**,
         truoc khi ta kip nhin thay cai cay. Nen tran do sau cua ta KHONG chan
         duoc ca nay; ta chi boc no lai cho co cho.
    """
    if len(bieu_thuc) > TRAN_CHUOI:
        raise cs.loi("nguon_qua_dai", tran=TRAN_CHUOI)
    try:
        return ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as loi:
        ma = ("ngoac_qua_sau" if "nested parentheses" in (loi.msg or "")
              else "khong_phan_tich")
        raise cs.loi(ma, msg=loi.msg) from None
    except RecursionError:
        raise cs.loi("qua_sau", tran=cs.tran_sau or TRAN_SAU) from None


def kiem_ngon_ngu(bieu_thuc: str, *, cs: ChinhSach = DAY_DU,
                  ten_cho_phep: set[str] | None = None) -> ast.Expression:
    """Kiem mot bieu thuc §6. Sai thi nem `LoiNgonNgu` mang `vi_tri`.

    ⚠️ Kiem KHONG can moi truong: no tra loi *"bieu thuc nay hop le chua"*,
       khong tra loi *"no doc duoc gi"*. Cong publish (`bien_dich.py`) mo`i la
       cho tra loi cau thu hai.
    """
    if not (bieu_thuc or "").strip():
        raise LoiNgonNgu("bieu thuc rong")
    ten = set(NAMESPACE) | set(HANG_SO_TEN) if ten_cho_phep is None \
        else set(ten_cho_phep) | set(HANG_SO_TEN)
    try:
        cay = phan_tich(bieu_thuc, cs)
        do_gioi_han(cay, cs)
        kiem_cay(cay, cs, ten)
    except LoiNgonNgu as loi:
        raise loi.dinh_vi(bieu_thuc=bieu_thuc) from None
    return cay


def tinh_ngon_ngu(bieu_thuc: str, moi_truong: Mapping[str, Any], *,
                  cs: ChinhSach = DAY_DU) -> Any:
    """Kiem roi tinh. ⛔ Van kiem lai o day chu khong tin tang tren.

    Tra ve gia tri JSON. Vuot 1 MB ⇒ `LoiNgonNgu` chu khong phai mot ket qua
    khong ai gui di dau duoc.
    """
    try:
        cay = kiem_ngon_ngu(bieu_thuc, cs=cs, ten_cho_phep=set(moi_truong))
        ra = tinh_cay(cay, cs, moi_truong)
        if _kich_thuoc(ra, TRAN_CHUOI) > TRAN_CHUOI:
            raise cs.loi("ket_qua_qua_lon", tran=TRAN_CHUOI)
    except LoiNgonNgu as loi:
        raise loi.dinh_vi(bieu_thuc=bieu_thuc) from None
    return ra
