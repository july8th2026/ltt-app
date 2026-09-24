"""Chinh sach DAY DU cua ngon ngu bieu thuc §6.2 (namespace) + §6.4 (kieu, tran).

## Vi sao co tep nay

`chinh_sach.py` co MAY duyet AST; `bieu_thuc.NGHIEM` la phuong ngu HEP (tran
`timeout_expr`). Tep nay do phuong ngu RONG — thu ma workflow that chay: doc
`nodes.<id>.output.<cong>`, goi ham, tra moi kieu JSON.

⭐ Dieu kien ra cua ca phase (plan §7): **phep thoat sandbox DO DUNG**. Nen moi
   duong thoat o day la MOT ca param rieng: mot dong do = mot cau noi ro.

## ⛔ Phep do nay KHONG phu

- Khong phu bang ham §6.3 (`ham_bieu_thuc.py`, Task 4): `DAY_DU` o day mang
  bang ham RONG, va cac ca goi ham dung bang GIA. Ngay hai manh lap lai, ai do
  phai do lai rang bang that khong mo them dang nut nao.
- Khong phu tang `{{ }}` (`noi_suy.py`, Task 2) — ta do bieu thuc TRAN.
- Khong phu cong publish (`bien_dich.py`, Task 7) tru dung mot phep bat khop
  hinh dang `nodes` giua hai cua.
- Khong do hieu nang, khong do bo nho that: tran 1 MB do bang **do dai chuoi /
  so phan tu uoc luong**, khong bang `sys.getsizeof`.
- Khong phu dieu gi ve `RecursionError` cua mot Python khac 3.13: nguong do
  duoc o day la nguong cua CHINH may nay (xem `test_tran_sau_chan_TRUOC...`).
"""
from __future__ import annotations

import ast
import dataclasses

import pytest

from platform_core.workflow import chinh_sach as CS
from platform_core.workflow.chinh_sach import (
    DAY_DU,
    TRAN_CHUOI,
    TRAN_NUT,
    TRAN_SAU,
    LoiNgonNgu,
    kiem_ngon_ngu,
    moi_truong_wf,
    tinh_ngon_ngu,
)

# ── Bo do dung chung ───────────────────────────────────────────────────────

NODES = {
    "b2": {"status": "SUCCEEDED", "output": {"text": "xin chao", "n": 3}},
    "b-2": {"status": "SUCCEEDED", "output": {"text": "co dau gach"}},
    "dang_chay": {"status": "RUNNING", "output": {}},
    "hong": {"status": "FAILED", "output": {}, "error": "het credit"},
}


def moi_truong(**them):
    goc = dict(
        trigger={"body": {"a": 1}, "fired_at": "2026-09-24T10:00:00+07:00"},
        workflow_input={"ten": "Lan", "so": 5},
        vars={"x": 10, "s": "abc", "ds": [1, 2, 3], "obj": {"k": "v"},
              "_bi_mat": "khong duoc doc", "rong": None},
        nodes=NODES,
        loop={"item": "a", "index": 0, "total": 3},
        run={"id": "r1", "started_at": "2026-09-24T09:00:00+07:00",
             "owner": "u1"},
        params={"duration_s": 12},
    )
    goc.update(them)
    return moi_truong_wf(**goc)


def tinh(bt, **them):
    return tinh_ngon_ngu(bt, moi_truong(**them))


def sau_cay(src: str) -> int:
    """Do sau cay — CUNG cach `chinh_sach` dem, va dem bang VONG LAP."""
    cay = ast.parse(src, mode="eval")
    sau, ngan = 0, [(cay, 1)]
    while ngan:
        n, d = ngan.pop()
        sau = max(sau, d)
        ngan.extend((c, d + 1) for c in ast.iter_child_nodes(n))
    return sau


# ── §6.2 NAMESPACE: doc duoc dung sau thu ──────────────────────────────────

@pytest.mark.parametrize("bt,mong", [
    ("trigger.body.a", 1),
    ("trigger.fired_at", "2026-09-24T10:00:00+07:00"),
    ("workflow.input.ten", "Lan"),
    ("workflow.input.so", 5),
    ("vars.x", 10),
    ("vars.obj.k", "v"),
    ("vars.ds[1]", 2),
    ("vars.ds[-1]", 3),
    ("vars.obj['k']", "v"),
    ("nodes.b2.output.text", "xin chao"),
    ("nodes.b2.output['text']", "xin chao"),
    ("nodes.b2.status", "SUCCEEDED"),
    ("nodes.hong.status", "FAILED"),
    ("nodes.hong.error", "het credit"),
    ("loop.item", "a"),
    ("loop.index", 0),
    ("loop.total", 3),
    ("run.id", "r1"),
    ("run.owner", "u1"),
    ("params.duration_s", 12),
])
def test_namespace_doc_duoc(bt, mong):
    assert tinh(bt) == mong


def test_id_node_co_dau_gach_viet_bang_NGOAC_VUONG():
    """⭐ `nodes.b-2` la PHEP TRU. Duong duy nhat la `nodes["b-2"]`."""
    assert tinh('nodes["b-2"].output.text') == "co dau gach"

    # `nodes.b-2` khong he la mot ten: `ast` doc no thanh `nodes.b - 2`.
    cay = ast.parse("nodes.b-2", mode="eval")
    assert isinstance(cay.body, ast.BinOp) and isinstance(cay.body.op, ast.Sub)

    # ... nen no phai do, va do VI mot ly do NOI DUNG SU THAT: khong co node
    #     ten `b`. ⛔ Khong duoc im lang tra `None` hay doan y nguoi go.
    with pytest.raises(LoiNgonNgu) as e:
        tinh("nodes.b-2")
    # ⚠️ Doc `ly_do` chu khong `str(e.value)`: cau day du co dan NGUYEN VAN
    #    bieu thuc vao cuoi (§6.4), nen chuoi "b-2" luon co mat o do.
    assert "b-2" not in e.value.ly_do
    assert "'b'" in e.value.ly_do


def test_tham_chieu_nodes_DONG_bi_tu_choi_CUNG_CHO_voi_cong_publish():
    """Hai cua phai tu choi CUNG mot chuoi — neu khong, mot cua la trang tri."""
    from platform_core.workflow.bien_dich import LoiBienDich, trich_tham_chieu

    bt = 'nodes[vars.s].output.text'
    with pytest.raises(LoiBienDich):        # cua publish (Task 7)
        trich_tham_chieu(bt)
    with pytest.raises(LoiNgonNgu):         # cua ngon ngu (tep nay)
        kiem_ngon_ngu(bt)


@pytest.mark.parametrize("bt,tu_khoa", [
    # node khong co trong run
    ("nodes.khongco.output.x", "khongco"),
    # node CHUA chay xong ⇒ output khong ton tai, phai NOI RO
    ("nodes.dang_chay.output.x", "RUNNING"),
    ("nodes.hong.output.x", "FAILED"),
    # cong chua co gia tri
    ("nodes.b2.output.khongco", "khongco"),
    # khoa khong co trong mot object thuong
    ("vars.khongco", "khongco"),
    ("vars.obj.khongco", "khongco"),
    # chi so ngoai dai
    ("vars.ds[9]", "9"),
    # doc thuoc tinh cua thu khong phai object
    ("vars.s.length", "chuoi"),
    ("vars.rong.x", "null"),
])
def test_doc_hut_thi_NOI_RO_chu_khong_tra_None(bt, tu_khoa):
    with pytest.raises(LoiNgonNgu) as e:
        tinh(bt)
    assert tu_khoa in str(e.value)


def test_khong_co_namespace_la_bien_tran():
    with pytest.raises(LoiNgonNgu) as e:
        tinh("env.SECRET")
    assert "env" in str(e.value)
    # cau loi phai KE RA cai co that, de nguoi go sua duoc
    assert "vars" in str(e.value) and "nodes" in str(e.value)


def test_loi_mang_VI_TRI_va_NGUYEN_VAN_theo_khuon_6_4():
    with pytest.raises(LoiNgonNgu) as e:
        tinh("1 + vars.khongco")
    assert e.value.vi_tri == 4          # cot cua `vars.khongco`
    assert e.value.bieu_thuc == "1 + vars.khongco"
    assert e.value.ly_do


def test_bieu_thuc_dai_bi_CAT_200_trong_loi():
    with pytest.raises(LoiNgonNgu) as e:
        tinh("vars.khongco" + " + 1" * 100)
    assert len(e.value.bieu_thuc) == 200


# ── §6.2 CHI DOC: gan, goi phuong thuc, thuoc tinh `_` ─────────────────────

@pytest.mark.parametrize("bt,tu_khoa", [
    ("vars._bi_mat", "_"),                      # thuoc tinh bat dau `_`
    ("vars['_bi_mat']", "_"),                   # ... ke ca qua ngoac vuong
    ("vars.s.upper()", "goi"),                  # goi phuong thuc cua doi tuong
    ("vars.s.upper", "chuoi"),                  # ... ke ca chi LAY ham do
    ("(x := 1)", "cu phap"),                    # gan (walrus)
    ("vars.x := 1", "phan tich"),               # ... ke ca dang khong parse
    ("vars.obj.__class__", "_"),
    ("vars.s.__class__.__mro__", "_"),
    ("().__class__", "_"),
    ("[].append", "danh sach"),
])
def test_chi_doc_thi_CHI_DOC(bt, tu_khoa):
    with pytest.raises(LoiNgonNgu) as e:
        tinh(bt)
    assert tu_khoa in str(e.value).lower()


def test_khoa_DONG_van_khong_doc_duoc_khoa_bat_dau_gach_duoi():
    """⭐ Phat hien bang TIEM LOI: luat `_` phai o CA HAI tang.

    Bo duyet tinh chi thay `vars["_bi_mat"]` viet TRAN. Voi mot khoa DONG —
    `vars[trigger.body.ten]` — no khong thay gi ca, va chi tang DOC du lieu
    con canh. Lan tiem dau tien (go luat `_` khoi tang doc) cho **157 passed**:
    cai rao do luc ay khong duoc phep kiem nao do toi. Bai nay la cho do.
    """
    with pytest.raises(LoiNgonNgu) as e:
        tinh("vars[vars.ten_khoa]",
             vars={"ten_khoa": "_bi_mat", "_bi_mat": "khong duoc doc"})
    assert "_bi_mat" in e.value.ly_do

    # ... va cung the khi ten khoa den tu trigger (du lieu NGOAI vao)
    with pytest.raises(LoiNgonNgu):
        tinh("vars[trigger.body.ten]",
             trigger={"body": {"ten": "_bi_mat"}},
             vars={"_bi_mat": "khong duoc doc"})


def test_gan_khong_phai_bieu_thuc():
    with pytest.raises(LoiNgonNgu):
        kiem_ngon_ngu("vars.x = 1")


# ── §6.4 EP KIEU: `==` khac kieu tra FALSE, khong nem ──────────────────────

@pytest.mark.parametrize("bt,mong", [
    # 🔑 diem spec chot: CEL lam nguoc (type-checker cua no NEM)
    ('"a" == 1', False),
    ('"a" != 1', True),
    ('vars.s == vars.x', False),
    ('null == 0', False),
    ('null == null', True),
    ('null != "x"', True),
    ('[1] == "1"', False),
    ('{} == []', False),
    # cung LOP thi so that
    ('1 == 1.0', True),         # int/float cung mot lop "so" (CEL: number line)
    ('2 == 2', True),
    ('"a" == "a"', True),
    ('[1, 2] == [1, 2]', True),
    ('{"a": 1} == {"a": 1}', True),
    ('{"a": 1} == {"a": 2}', False),
    # bool la LOP RIENG (JSON co true/false rieng; Python thi bool la int)
    ('true == 1', False),
    ('false == 0', False),
    ('true == true', True),
    ('[1] == [true]', False),
])
def test_bang_khac_kieu_tra_false_chu_khong_nem(bt, mong):
    assert tinh(bt) is mong


def test_bang_khong_bao_gio_nem_du_hai_ben_la_gi():
    """⛔ Khong mot cap gia tri JSON nao lam `==` nem. Do la ca diem cua luat."""
    gia_tri = ["null", "true", "1", "1.5", '"a"', "[1]", '{"a": 1}', "[]", "{}"]
    for a in gia_tri:
        for b in gia_tri:
            assert isinstance(tinh(f"{a} == {b}"), bool)


# ── §6.4 EP KIEU: so hoc va so sanh thu tu ─────────────────────────────────

@pytest.mark.parametrize("bt,mong", [
    ("1 + 1.5", 2.5),       # 🔑 CEL NEM o day (int/double khong tron)
    ("1 + 1", 2),
    ("1.5 * 2", 3.0),
    ("7 / 2", 3.5),
    ("7 // 2", 3),
    ("7 % 2", 1),
    ("-vars.x", -10),
    ('"a" + "b"', "ab"),
    ("[1] + [2]", [1, 2]),
    ("1 < 2", True),
    ('"a" < "b"', True),
    ("1 <= 1.0", True),
    ("not 0", True),
    ('not ""', True),
    ("not []", True),
    ("not {}", True),
    ("not null", True),
    ("not 1", False),
    ('"b" in "abc"', True),
    ("2 in vars.ds", True),
    ('"k" in vars.obj', True),
    ('"z" not in vars.obj', True),
    ("1 if true else vars.khongco", 1),      # nhanh khong chon: KHONG tinh
])
def test_so_hoc_va_so_sanh(bt, mong):
    assert tinh(bt) == mong


@pytest.mark.parametrize("bt,tu_khoa", [
    ('"1" + 1', "to_number"),       # spec §6.4 goi thang ten loi ra
    ('1 + "1"', "to_number"),
    ('"a" < 1', "kieu"),            # spec: so sanh thu tu khac kieu ⇒ LOI
    ('1 > "a"', "kieu"),
    ('[1] < [2]', "kieu"),
    ('"a" * 3', "kieu"),            # ⛔ khong nhan chuoi (simpleeval phai co
    ('3 * "a"', "kieu"),            #    `safe_mult`; ta khong co phep do)
    ("true + 1", "kieu"),           # bool khong phai so
    ("null + 1", "kieu"),
    ("[1] + 1", "kieu"),
    ("1 in 1", "kieu"),
    ('1 in "abc"', "kieu"),
])
def test_khong_ep_ngam_thi_NOI_RO_kieu_khong_khop(bt, tu_khoa):
    with pytest.raises(LoiNgonNgu) as e:
        tinh(bt)
    assert tu_khoa in str(e.value)


@pytest.mark.parametrize("bt", ["1 / 0", "1 // 0", "1 % 0", "vars.x / 0"])
def test_chia_0_noi_ro(bt):
    with pytest.raises(LoiNgonNgu) as e:
        tinh(bt)
    assert "0" in str(e.value)


def test_and_or_CAT_MACH_va_tra_bool():
    # ve phai KHONG duoc tinh — neu tinh thi no da nem "khong co node"
    assert tinh("false and nodes.khongco.output.x") is False
    assert tinh("true or nodes.khongco.output.x") is True
    # tra `bool`, khong tra toan hang (giong `NGHIEM`, khac Python)
    assert tinh("vars.x and vars.s") is True
    assert tinh("0 or vars.s") is True


# ── §6.4 GIOI HAN ──────────────────────────────────────────────────────────

def test_tran_sau_dung_bang_32():
    assert TRAN_SAU == 32 and TRAN_NUT == 10_000 and TRAN_CHUOI == 1024 * 1024


def test_sau_ngay_duoi_tran_thi_qua_duoc():
    src = "not " * (TRAN_SAU - 2) + "1"
    assert sau_cay(src) == TRAN_SAU
    assert tinh(src) in (True, False)


def test_sau_qua_tran_thi_do():
    src = "not " * (TRAN_SAU - 1) + "1"
    assert sau_cay(src) == TRAN_SAU + 1
    with pytest.raises(LoiNgonNgu) as e:
        tinh(src)
    assert "sau" in str(e.value)


def test_tran_sau_chan_TRUOC_khi_Python_het_ngan_xep():
    """🔑 Bang chung: tran 32 chan o mot cay ma bo duyet DE QUY se chet.

    ⛔ Khong dung `sys.setrecursionlimit` de "chung minh" — do la doi luat
       choi. Ta lay mot cay CO THAT sau hon ngan xep Python that.
    """
    import sys
    src = "not " * 2000 + "1"
    assert sau_cay(src) > sys.getrecursionlimit()      # cay that su qua sau

    with pytest.raises(LoiNgonNgu):                    # sach se
        kiem_ngon_ngu(src)

    # ⭐ TIEM LOI: bo tran sau ⇒ chinh cay nay lam bo duyet de quy vo ngan xep.
    khong_tran = dataclasses.replace(DAY_DU, tran_sau=None)
    with pytest.raises(RecursionError):
        CS.kiem_cay(ast.parse(src, mode="eval"), khong_tran,
                    set(CS.NAMESPACE))


def test_RecursionError_cua_chinh_ast_parse_duoc_BOC():
    """`ast.parse` tu no chet TRUOC khi ta thay cai cay — do la mot loi tho.

    Do tren may nay (Python 3.13.12): `"1" + "+1"*5000` ⇒ `RecursionError:
    maximum recursion depth exceeded during ast construction`.
    """
    src = "1" + "+1" * 5000
    with pytest.raises(RecursionError):
        ast.parse(src, mode="eval")          # nguon tho, do duoc
    with pytest.raises(LoiNgonNgu) as e:     # ... da boc
        kiem_ngon_ngu(src)
    assert "sau" in str(e.value)


def test_ngoac_long_qua_sau_ra_loi_co_cho():
    """CPython chan o tokenizer (`MAXLEVEL`), khong phai `RecursionError`."""
    src = "(" * 300 + "1" + ")" * 300
    with pytest.raises(SyntaxError):
        ast.parse(src, mode="eval")
    with pytest.raises(LoiNgonNgu) as e:
        kiem_ngon_ngu(src)
    assert "ngoac" in str(e.value) or "phan tich" in str(e.value)


def test_qua_nhieu_nut_thi_do():
    du = "[" + ",".join(["1"] * (TRAN_NUT - 3)) + "]"
    assert tinh(du) == [1] * (TRAN_NUT - 3)
    qua = "[" + ",".join(["1"] * (TRAN_NUT + 1)) + "]"
    with pytest.raises(LoiNgonNgu) as e:
        kiem_ngon_ngu(qua)
    assert "nut" in str(e.value)


def test_nguon_qua_1MB_bi_chan_TRUOC_khi_phan_tich():
    with pytest.raises(LoiNgonNgu) as e:
        kiem_ngon_ngu("1 " + "+ 1 " * (TRAN_CHUOI // 4))
    assert "1 MB" in str(e.value) or "ky tu" in str(e.value)


def test_chuoi_ket_qua_qua_1MB_thi_do():
    to = "x" * (TRAN_CHUOI // 2 + 10)
    assert len(tinh("vars.to + vars.to", vars={"to": "y" * 10})) == 20
    with pytest.raises(LoiNgonNgu) as e:
        tinh("vars.to + vars.to", vars={"to": to})
    assert "1 MB" in str(e.value) or "tran" in str(e.value)


def test_danh_sach_ket_qua_qua_tran_thi_do():
    ds = list(range(TRAN_CHUOI // 2))
    with pytest.raises(LoiNgonNgu):
        tinh("vars.ds + vars.ds", vars={"ds": ds})


# ── DIEU KIEN RA: moi duong thoat sandbox = MOT ca ────────────────────────

@pytest.mark.parametrize("bt", [
    "__import__('os')",
    "__import__",
    "open('x')",
    "eval('1')",
    "compile('1', 'x', 'eval')",
    "globals()",
    "vars()",                       # `vars` la namespace, khong phai ham
    "().__class__.__bases__",
    "(1).__class__",
    "[x for x in [1]]",
    "{k: 1 for k in [1]}",
    "(x for x in [1])",
    "lambda: 1",
    "(lambda: 1)()",
    "2 ** 10",
    "10 ** 10 ** 10",
    "1 if true else (lambda: 1)()",
    "f'{vars.x}'",
    "b'xx'",
    "...",
    "vars.x is None",
    "vars.x is not None",
    "vars.ds[0:2]",                 # slice — spec co ham `slice`, khong co cu phap
    "[*vars.ds]",
    "{**vars.obj}",
    "vars.obj.get('k')",
    "trigger.body.pop()",
    "~1",
    "vars.x @ vars.x",
    "vars.x & 1",
    "vars.x | 1",
    "vars.x ^ 1",
    "vars.x << 1",
    "vars.x >> 1",
])
def test_duong_thoat_sandbox_DO_DUNG(bt):
    """⭐ Dieu kien ra cua phase P2. Mot dong = mot duong da bi dong."""
    with pytest.raises((LoiNgonNgu, SyntaxError)) as e:
        kiem_ngon_ngu(bt)
    if isinstance(e.value, SyntaxError):
        pytest.fail(f"{bt!r}: SyntaxError tho, chua duoc boc")


def test_goi_ham_ngoai_bang_bi_tu_choi_va_bang_la_THAM_SO():
    """Bang ham la DU LIEU: `DAY_DU` mang bang RONG, ai lap thi truyen vao."""
    assert DAY_DU.ham == {}
    with pytest.raises(LoiNgonNgu):
        kiem_ngon_ngu("len(vars.s)")

    co_ham = CS.chinh_sach_day_du(ham={"len": len})
    assert tinh_ngon_ngu("len(vars.s)", moi_truong(), cs=co_ham) == 3
    # ... nhung ngay ca khi co bang, van khong duoc goi bang tham so co TEN
    with pytest.raises(LoiNgonNgu) as e:
        tinh_ngon_ngu("len(x=vars.s)", moi_truong(), cs=co_ham)
    assert "ten" in str(e.value)
    # ... va khong duoc goi mot gia tri lay tu du lieu
    with pytest.raises(LoiNgonNgu):
        tinh_ngon_ngu("vars.f()", moi_truong(vars={"f": len}), cs=co_ham)


# ── BANH COC: bang chinh sach la thu duy nhat quyet dinh ──────────────────

def test_bang_nut_cho_phep_dung_bang_ban_khai():
    """Them mot dang nut vao `DAY_DU` phai la mot dong diff O DAY."""
    assert DAY_DU.nut_cho_phep == frozenset({
        ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
        ast.Compare, ast.BoolOp, ast.IfExp, ast.Call, ast.Attribute,
        ast.Subscript, ast.List, ast.Dict,
    })


def test_NGHIEM_KHONG_duoc_mo_ra_boi_viec_may_hoc_them_nut_moi():
    """🔑 May gio biet di vao `Attribute`/`Subscript`/`List`/`Dict`.

    Neu chi can them dang nut vao bang la `NGHIEM` doc duoc `a.b`, thi viec
    tach may/chinh sach da bien thanh mot lo hong cho hop dong ve tien.
    """
    from platform_core.workflow.bieu_thuc import NGHIEM, LoiBieuThuc

    for src, nut in (("a.b", ast.Attribute), ("a[0]", ast.Subscript),
                     ("[a]", ast.List), ("{'k': a}", ast.Dict)):
        cay = ast.parse(src, mode="eval")
        with pytest.raises(LoiBieuThuc):
            CS.kiem_cay(cay, NGHIEM, {"a"})
        noi = dataclasses.replace(
            NGHIEM, nut_cho_phep=NGHIEM.nut_cho_phep | {nut})
        with pytest.raises(LoiBieuThuc):      # van do: thieu NANG LUC trong bang
            CS.kiem_cay(cay, noi, {"a"})


@pytest.mark.parametrize("o,src", [
    ("tran_sau", "not " * 40 + "1"),
    ("tran_nut", "[" + ",".join(["1"] * (TRAN_NUT + 1)) + "]"),
    ("doc_thuoc_tinh", "vars.x"),
    ("doc_khoa", "vars['x']"),
    ("cho_ghep", "[1, 2]"),
])
def test_TIEM_LOI_go_mot_o_trong_bang_thi_cai_rao_bien_mat(o, src):
    """⭐ Mot cai rao chi la cai rao neu no DO khi bi go.

    Go o `o` khoi `DAY_DU` ⇒ hanh vi PHAI doi. Neu khong doi, o do la trang
    tri va bai kiem tren no do mot thu khac voi thu no noi.
    """
    that = {"tran_sau": None, "tran_nut": None, "doc_thuoc_tinh": None,
            "doc_khoa": None, "cho_ghep": False}[o]
    bi_go = dataclasses.replace(DAY_DU, **{o: that})
    cay = ast.parse(src, mode="eval")
    ten = set(CS.NAMESPACE)

    if o in ("tran_sau", "tran_nut"):
        # co tran ⇒ tu choi; go tran ⇒ KHONG con tu choi vi ly do do nua
        with pytest.raises(LoiNgonNgu):
            CS.do_gioi_han(cay, DAY_DU)
        CS.do_gioi_han(cay, bi_go)
    else:
        CS.kiem_cay(cay, DAY_DU, ten)          # co nang luc ⇒ qua
        with pytest.raises(LoiNgonNgu):        # go nang luc ⇒ do
            CS.kiem_cay(cay, bi_go, ten)


def test_module_KHONG_co_cua_thi_hanh():
    """Co hoc, khong phai giao uoc: doc AST cua chinh mo-dun."""
    import pathlib
    nguon = pathlib.Path(CS.__file__).read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    cam = {"eval", "exec", "compile", "getattr", "setattr", "__import__",
           "globals", "locals", "vars"}
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not (goi & cam), f"mo-dun goi {goi & cam}"
