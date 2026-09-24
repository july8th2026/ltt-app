"""Hop dong cua `timeout_expr` KHONG DOI khi bo duyet AST tach thanh may + chinh sach.

## Vi sao co tep nay

`platform_core/workflow/bieu_thuc.py` co hop dong HEP CO CHU DICH: chi doc
`params` cua chinh node, khong goi ham, tat dinh. Ba dieu do khong phai gioi
han — chung la dieu kien de con so tran `max_runtime_s` **ton tai truoc** khi
ai do tieu tien (docstring mo-dun do).

Ngon ngu bieu thuc §6 doi nguoc ca ba. Nen bo duyet duoc tach thanh **may**
(`chinh_sach.py`) + **chinh sach** (`bieu_thuc.NGHIEM`): dung lai MA, khong
dung lai HOP DONG.

## ⛔ Vi sao bang duoi day khong duoc go bang tay

"Toi refactor can than nen khong doi gi" khong phai bang chung. Bang `BANG`
duoc **chup co hoc** tu mo-dun TRUOC khi sua (`fb5c93e7`) va in ra bang `repr`:
moi dong la ban ghi that cua ma cu, gom ca **nguyen van cau loi**. Cau loi la
mot phan hop dong — `registry.py` dan no vao `RegistryError` va nguoi khai
tool doc no de sua.

⭐ Bang nay phu CA hanh vi kho chiu ma ta co y KHONG "sua nhan the":
`"  duration_s  "` (khoang trang dau) → `IndentationError`;
`a and b` tra `True`/`False` chu khong tra toan hang;
`min` dung nhu bien thi qua duoc `kiem` nhung chet o `tinh`.
Sua nhung cho do la mot QUYET DINH rieng, khong phai tac dung phu cua don ma.

## ⛔ Phep do nay KHONG phu

- Khong phu ngon ngu §6 (chua ton tai) — chi phu chinh sach NGHIEM.
- Khong phu duong goi tu `registry._validate_hop_dong_v2` (o `test_964`).
- Khong phu `tinh_cay` goi TRUC TIEP voi nut chua qua `kiem_cay`: qua
  `tinh_bieu_thuc` thi moi nut deu da duyet truoc.
"""
import ast
import pathlib

import pytest

from platform_core.workflow.bieu_thuc import (
    kiem_bieu_thuc,
    tham_so_dung,
    tinh_bieu_thuc,
)

#: (bieu_thuc, params, ket_qua_kiem, ket_qua_tinh, ket_qua_tham_so_dung)
#: Moi ket qua la ("OK", gia_tri) hoac ("LOI", ten_lop, nguyen_van_cau_loi).
BANG = [
    ('duration_s * 30 + 120', {'duration_s': 5}, ('OK', None), ('OK', 270), ('OK', ['duration_s'])),
    ('min(duration_s * 30 + 120, 3600)', {'duration_s': 600}, ('OK', None), ('OK', 3600), ('OK', ['duration_s'])),
    ('max(a, b)', {'a': 3, 'b': 9}, ('OK', None), ('OK', 9), ('OK', ['a', 'b'])),
    ('duration_s if duration_s > 10 else 10', {'duration_s': 3}, ('OK', None), ('OK', 10), ('OK', ['duration_s'])),
    ('-duration_s', {'duration_s': 5}, ('OK', None), ('OK', -5), ('OK', ['duration_s'])),
    ('+duration_s', {'duration_s': 5}, ('OK', None), ('OK', 5), ('OK', ['duration_s'])),
    ('duration_s / 2', {'duration_s': 5}, ('OK', None), ('OK', 2.5), ('OK', ['duration_s'])),
    ('duration_s // 2', {'duration_s': 5}, ('OK', None), ('OK', 2), ('OK', ['duration_s'])),
    ('duration_s % 3', {'duration_s': 5}, ('OK', None), ('OK', 2), ('OK', ['duration_s'])),
    ('duration_s - 1', {'duration_s': 5}, ('OK', None), ('OK', 4), ('OK', ['duration_s'])),
    ('1 < a < 10', {'a': 5}, ('OK', None), ('OK', True), ('OK', ['a'])),
    ('1 < a < 3', {'a': 5}, ('OK', None), ('OK', False), ('OK', ['a'])),
    ('a and b', {'a': 1, 'b': 0}, ('OK', None), ('OK', False), ('OK', ['a', 'b'])),
    ('a or b', {'a': 0, 'b': 7}, ('OK', None), ('OK', True), ('OK', ['a', 'b'])),
    ('a == 1', {'a': 1}, ('OK', None), ('OK', True), ('OK', ['a'])),
    ('a != 1', {'a': 1}, ('OK', None), ('OK', False), ('OK', ['a'])),
    ('a >= 1', {'a': 1}, ('OK', None), ('OK', True), ('OK', ['a'])),
    ('a <= 0', {'a': 1}, ('OK', None), ('OK', False), ('OK', ['a'])),
    ('True', {}, ('OK', None), ('OK', True), ('OK', [])),
    ('False', {}, ('OK', None), ('OK', False), ('OK', [])),
    ('1.5', {}, ('OK', None), ('OK', 1.5), ('OK', [])),
    ('min(a, max(b, 3))', {'a': 100, 'b': 1}, ('OK', None), ('OK', 3), ('OK', ['a', 'b'])),
    ('cost if cost else 60', {'cost': 0}, ('OK', None), ('OK', 60), ('OK', ['cost'])),
    ('  duration_s  ', {'duration_s': 7}, ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: unexpected indent'), ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: unexpected indent'), ('LOI', 'IndentationError', 'unexpected indent (<unknown>, line 1)')),
    ("__import__('os').system('x')", {}, ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('OK', ['__import__'])),
    ("open('/etc/passwd')", {}, ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('OK', ['open'])),
    ('len(a)', {'a': 1}, ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('OK', ['a', 'len'])),
    ('abs(a)', {'a': -1}, ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('OK', ['a', 'abs'])),
    ('min(a, key=1)', {'a': 1}, ('LOI', 'LoiBieuThuc', 'khong dung tham so co ten'), ('LOI', 'LoiBieuThuc', 'khong dung tham so co ten'), ('OK', ['a'])),
    ('(lambda: 1)()', {}, ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('LOI', 'LoiBieuThuc', "chi duoc goi ['max', 'min'], khong goi gi khac"), ('OK', [])),
    ('unknown_name', {}, ('LOI', 'LoiBieuThuc', "ten 'unknown_name' khong phai tham so cua tool (co: khong co tham so nao)"), ('LOI', 'LoiBieuThuc', "ten 'unknown_name' khong phai tham so cua tool (co: khong co tham so nao)"), ('OK', ['unknown_name'])),
    ('unknown_name', {'a': 1}, ('LOI', 'LoiBieuThuc', "ten 'unknown_name' khong phai tham so cua tool (co: ['a'])"), ('LOI', 'LoiBieuThuc', "ten 'unknown_name' khong phai tham so cua tool (co: ['a'])"), ('OK', ['unknown_name'])),
    ('nodes', {'a': 1}, ('LOI', 'LoiBieuThuc', "ten 'nodes' khong phai tham so cua tool (co: ['a'])"), ('LOI', 'LoiBieuThuc', "ten 'nodes' khong phai tham so cua tool (co: ['a'])"), ('OK', ['nodes'])),
    ('a + b', {'a': 1}, ('LOI', 'LoiBieuThuc', "ten 'b' khong phai tham so cua tool (co: ['a'])"), ('LOI', 'LoiBieuThuc', "ten 'b' khong phai tham so cua tool (co: ['a'])"), ('OK', ['a', 'b'])),
    ('duration_s.__class__', {'duration_s': 1}, ('LOI', 'LoiBieuThuc', 'cu phap Attribute khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Attribute khong duoc phep'), ('OK', ['duration_s'])),
    ('a.b', {'a': 1}, ('LOI', 'LoiBieuThuc', 'cu phap Attribute khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Attribute khong duoc phep'), ('OK', ['a'])),
    ('[x for x in (1,2)]', {}, ('LOI', 'LoiBieuThuc', 'cu phap ListComp khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap ListComp khong duoc phep'), ('OK', ['x'])),
    ('[1, 2]', {}, ('LOI', 'LoiBieuThuc', 'cu phap List khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap List khong duoc phep'), ('OK', [])),
    ('(1, 2)', {}, ('LOI', 'LoiBieuThuc', 'cu phap Tuple khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Tuple khong duoc phep'), ('OK', [])),
    ('{1: 2}', {}, ('LOI', 'LoiBieuThuc', 'cu phap Dict khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Dict khong duoc phep'), ('OK', [])),
    ('{1, 2}', {}, ('LOI', 'LoiBieuThuc', 'cu phap Set khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Set khong duoc phep'), ('OK', [])),
    ('a[0]', {'a': 1}, ('LOI', 'LoiBieuThuc', 'cu phap Subscript khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Subscript khong duoc phep'), ('OK', ['a'])),
    ('lambda: 1', {}, ('LOI', 'LoiBieuThuc', 'cu phap Lambda khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap Lambda khong duoc phep'), ('OK', [])),
    ("f'{a}'", {'a': 1}, ('LOI', 'LoiBieuThuc', 'cu phap JoinedStr khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap JoinedStr khong duoc phep'), ('OK', ['a'])),
    ("'abc'", {}, ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap str'), ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap str'), ('OK', [])),
    ("b'abc'", {}, ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap bytes'), ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap bytes'), ('OK', [])),
    ('None', {}, ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap NoneType'), ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap NoneType'), ('OK', [])),
    ('...', {}, ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap ellipsis'), ('LOI', 'LoiBieuThuc', 'hang so phai la so, gap ellipsis'), ('OK', [])),
    ('2 ** 999999999', {}, ('LOI', 'LoiBieuThuc', 'toan tu Pow khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu Pow khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', [])),
    ('2 ** 3', {}, ('LOI', 'LoiBieuThuc', 'toan tu Pow khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu Pow khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', [])),
    ('a & b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'toan tu BitAnd khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu BitAnd khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', ['a', 'b'])),
    ('a | b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'toan tu BitOr khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu BitOr khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', ['a', 'b'])),
    ('a ^ b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'toan tu BitXor khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu BitXor khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', ['a', 'b'])),
    ('a << b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'toan tu LShift khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu LShift khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', ['a', 'b'])),
    ('a @ b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'toan tu MatMult khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('LOI', 'LoiBieuThuc', 'toan tu MatMult khong duoc phep (** bi cam: no tinh duoc ma khong bao gio tra loi)'), ('OK', ['a', 'b'])),
    ('~a', {'a': 1}, ('LOI', 'LoiBieuThuc', 'toan tu Invert khong duoc phep'), ('LOI', 'LoiBieuThuc', 'toan tu Invert khong duoc phep'), ('OK', ['a'])),
    ('not a', {'a': 1}, ('LOI', 'LoiBieuThuc', 'toan tu Not khong duoc phep'), ('LOI', 'LoiBieuThuc', 'toan tu Not khong duoc phep'), ('OK', ['a'])),
    ('a in (1, 2)', {'a': 1}, ('LOI', 'LoiBieuThuc', 'phep so sanh In khong duoc phep'), ('LOI', 'LoiBieuThuc', 'phep so sanh In khong duoc phep'), ('OK', ['a'])),
    ('a not in (1, 2)', {'a': 1}, ('LOI', 'LoiBieuThuc', 'phep so sanh NotIn khong duoc phep'), ('LOI', 'LoiBieuThuc', 'phep so sanh NotIn khong duoc phep'), ('OK', ['a'])),
    ('a is b', {'a': 1, 'b': 1}, ('LOI', 'LoiBieuThuc', 'phep so sanh Is khong duoc phep'), ('LOI', 'LoiBieuThuc', 'phep so sanh Is khong duoc phep'), ('OK', ['a', 'b'])),
    ('a is not b', {'a': 1, 'b': 1}, ('LOI', 'LoiBieuThuc', 'phep so sanh IsNot khong duoc phep'), ('LOI', 'LoiBieuThuc', 'phep so sanh IsNot khong duoc phep'), ('OK', ['a', 'b'])),
    ('(a := 1)', {}, ('LOI', 'LoiBieuThuc', 'cu phap NamedExpr khong duoc phep'), ('LOI', 'LoiBieuThuc', 'cu phap NamedExpr khong duoc phep'), ('OK', ['a'])),
    ('1 +', {}, ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: invalid syntax'), ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: invalid syntax'), ('LOI', 'SyntaxError', 'invalid syntax (<unknown>, line 1)')),
    ('(', {}, ('LOI', 'LoiBieuThuc', "khong phan tich duoc: '(' was never closed"), ('LOI', 'LoiBieuThuc', "khong phan tich duoc: '(' was never closed"), ('LOI', 'SyntaxError', "'(' was never closed (<unknown>, line 1)")),
    ('a b', {'a': 1, 'b': 2}, ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: invalid syntax'), ('LOI', 'LoiBieuThuc', 'khong phan tich duoc: invalid syntax'), ('LOI', 'SyntaxError', 'invalid syntax (<unknown>, line 1)')),
    ('', {}, ('OK', None), ('LOI', 'LoiBieuThuc', 'bieu thuc rong'), ('OK', [])),
    ('   ', {}, ('OK', None), ('LOI', 'LoiBieuThuc', 'bieu thuc rong'), ('OK', [])),
    ('120 / d', {'d': 0}, ('OK', None), ('LOI', 'LoiBieuThuc', 'chia cho 0'), ('OK', ['d'])),
    ('120 // d', {'d': 0}, ('OK', None), ('LOI', 'LoiBieuThuc', 'chia cho 0'), ('OK', ['d'])),
    ('120 % d', {'d': 0}, ('OK', None), ('LOI', 'LoiBieuThuc', 'chia cho 0'), ('OK', ['d'])),
    ('a', {'a': 'xau'}, ('OK', None), ('LOI', 'LoiBieuThuc', "tham so 'a' khong co gia tri"), ('OK', ['a'])),
    ('a', {'a': None}, ('OK', None), ('LOI', 'LoiBieuThuc', "tham so 'a' khong co gia tri"), ('OK', ['a'])),
    ('a + 1', {'a': True}, ('OK', None), ('OK', 2), ('OK', ['a'])),
    ('min', {}, ('OK', None), ('LOI', 'LoiBieuThuc', "tham so 'min' khong co gia tri"), ('OK', [])),
    ('min + 1', {}, ('OK', None), ('LOI', 'LoiBieuThuc', "tham so 'min' khong co gia tri"), ('OK', [])),
]

#: ⛔ Banh coc: chup duoc bao nhieu ca thi phai con bay nhieu. Mot bang mong
#:   doi bi xoa bot van xanh — do la cach mot phep do "khong do gi" ma van
#:   bao dat.
SO_CA = 75


def _chay(f, *doi_so):
    try:
        kq = f(*doi_so)
    except Exception as loi:  # noqa: BLE001 — dang doi chieu, phai bat het
        return ("LOI", type(loi).__name__, str(loi))
    return ("OK", sorted(kq) if isinstance(kq, set) else kq)


def test_bang_chup_con_du_ca():
    assert len(BANG) == SO_CA


@pytest.mark.parametrize("i", range(len(BANG)),
                         ids=[b[0][:32] or "<rong>" for b in BANG])
def test_hop_dong_timeout_expr_KHONG_DOI(i):
    bt, params, mong_kiem, mong_tinh, mong_tsd = BANG[i]
    assert _chay(kiem_bieu_thuc, bt, params) == mong_kiem, f"kiem: {bt!r}"
    assert _chay(tinh_bieu_thuc, bt, params) == mong_tinh, f"tinh: {bt!r}"
    assert _chay(tham_so_dung, bt) == mong_tsd, f"tham_so_dung: {bt!r}"


# ── May co THAT SU doc chinh sach khong (tiem loi, khong khang dinh) ───────

def test_may_doc_CHINH_SACH_chu_khong_tu_quyet_dinh():
    """⭐ Noi mot o trong bang ⇒ dung thu bi o do cam phai qua duoc.

    Neu may van tu choi sau khi da noi bang, nghia la lenh cam nam trong MA
    cua may chu khong nam trong bang — luc do bang chi la trang tri, va ban
    khai hop dong o `bieu_thuc.NGHIEM` khong noi len su that nao.
    """
    import dataclasses

    from platform_core.workflow import chinh_sach as CS
    from platform_core.workflow.bieu_thuc import NGHIEM, LoiBieuThuc

    cay_mu = ast.parse("2 ** 3", mode="eval")
    cay_thuoc_tinh = ast.parse("a.b", mode="eval")
    cay_goi = ast.parse("len(a)", mode="eval")
    cay_chuoi = ast.parse("'x'", mode="eval")
    ca = (cay_mu, cay_thuoc_tinh, cay_goi, cay_chuoi)

    # 1. NGHIEM tu choi ca bon
    for cay in ca:
        with pytest.raises(LoiBieuThuc):
            CS.kiem_cay(cay, NGHIEM, {"a"})

    # 2. Noi DUNG mot o ⇒ dung mot thu do di qua duoc
    noi_mu = dataclasses.replace(
        NGHIEM, nhi_phan={**NGHIEM.nhi_phan, ast.Pow: lambda a, b: a ** b})
    CS.kiem_cay(cay_mu, noi_mu, {"a"})
    assert CS.tinh_cay(cay_mu, noi_mu, {}) == 8

    noi_ham = dataclasses.replace(NGHIEM, ham={**NGHIEM.ham, "len": len})
    CS.kiem_cay(cay_goi, noi_ham, {"a"})

    noi_hang = dataclasses.replace(NGHIEM, kieu_hang_so=(bool, int, float, str))
    CS.kiem_cay(cay_chuoi, noi_hang, set())

    # ⭐ Ke ca khi bang cho `Attribute`, may VAN tu choi — vi no chua biet di
    #   vao nut do. Mo mot o trong bang KHONG tu dong mo mot lo hong: hai lop
    #   phai cung dong y thi mot dang nut moi song.
    noi_nut = dataclasses.replace(
        NGHIEM, nut_cho_phep=NGHIEM.nut_cho_phep | {ast.Attribute})
    with pytest.raises(LoiBieuThuc):
        CS.kiem_cay(cay_thuoc_tinh, noi_nut, {"a"})

    # 3. Ban NGHIEM that khong bi cac ban noi kia lam anh huong
    for cay in ca:
        with pytest.raises(LoiBieuThuc):
            CS.kiem_cay(cay, NGHIEM, {"a"})


def test_neu_ai_do_noi_NGHIEM_thi_hop_dong_DO(monkeypatch):
    """🔑 Mot cai rao chi la cai rao neu no DO khi bi go.

    Bai tren chung minh may doc bang. Bai nay chung minh **duong cong khai**
    di qua dung bang do: noi bang thi `len(a)` qua duoc — tuc cac phep cam
    trong `BANG` that su dang canh cai bang nay, khong canh mot ban sao.
    """
    import dataclasses

    from platform_core.workflow import bieu_thuc as BT

    with pytest.raises(BT.LoiBieuThuc):
        BT.kiem_bieu_thuc("len(a)", {"a": {}})

    monkeypatch.setattr(
        BT, "NGHIEM",
        dataclasses.replace(BT.NGHIEM, ham={**BT.NGHIEM.ham, "len": len}))
    BT.kiem_bieu_thuc("len(a)", {"a": {}})  # da noi ⇒ khong con nem


# ── Ruot da chuyen cho — cai canh gac co di theo khong ─────────────────────

def test_ca_hai_mo_dun_deu_KHONG_dung_eval():
    """⭐ `test_964` chi doc AST cua `bieu_thuc.py`.

    Refactor nay **chuyen bo tinh sang tep khac**, nen cai canh gac do khong
    con nhin vao cho co ma — dung hang loi "banh coc ASCII chi quet `print()`
    truc tiep". Bai nay di theo ma: quet CA HAI mo-dun.

    Doc AST chu khong `grep`: `grep "eval"` bao dong tren chinh doan chu thich
    **giai thich vi sao khong dung `eval`** — bo do van ban trung phat viec
    giai thich.
    """
    from platform_core.workflow import bieu_thuc, chinh_sach

    for mo_dun in (bieu_thuc, chinh_sach):
        cay = ast.parse(
            pathlib.Path(mo_dun.__file__).read_text(encoding="utf-8"))
        goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert not ({"eval", "exec", "compile"} & goi), \
            f"{mo_dun.__name__} co loi goi: {goi}"
