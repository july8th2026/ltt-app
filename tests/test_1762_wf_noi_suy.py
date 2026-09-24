"""Tang noi suy `{{ }}` — spec §6.1 ba luat, va NGU NGHIA quan trong hon cu phap.

## Vi sao tep nay ton tai

Luat 1 cua §6.1 (*"chuoi chi gom mot `{{ expr }}` ⇒ giu KIEU"*) khong phai mot
tien nghi. `{{ workflow.input.n }}` phai tra **so 5**. Neu no tra chuoi `"5"`
thi cong typed §4.7 hoac tu choi, hoac — te hon — nhan roi hong luc chay, o
mot node khac, sau khi da tieu credit.

## ⭐ TRA NGUON — hai engine, va cho chung DONG Y voi nhau

Cau kho nhat khong phai `"{{ a }}"` ma la `" {{ a }} "` (khoang trang BAO
NGOAI). Hai engine doc lap cho cung mot cau tra loi: **tron chu**.

- **Jinja2 `NativeEnvironment`** (`pallets/jinja`, `src/jinja2/nativetypes.py`,
  `native_concat`): `head = list(islice(values, 2))`; chi khi `len(head) == 1`
  moi tra thang gia tri. `" {{ a }} "` bien dich ra BA node (text, expr, text)
  ⇒ di duong `"".join([str(v) for v in values])`.
- **n8n / tournament** (`n8n-io/tournament`, `src/ExpressionBuilder.ts`,
  `getExpressionCode`): duong giu kieu la nhanh `else`, chi vao duoc khi
  `chunks.length <= 2 && chunks[0].text === ''`. `splitExpression`
  (`src/ExpressionSplitter.ts`) LUON phat mot chunk text dau tien, nen
  `" {{ a }} "` ra `['text: " "', 'code', 'text: " "']` ⇒ 3 chunk ⇒ `.join('')`.

⇒ Ta lay luat do: **giu kieu chi khi chuoi KHONG con gi ngoai mot `{{ }}`.**
Ly do doc duoc: mot khoang trang bao ngoai la mot ky tu NGUOI GO CO Y go; neu
ta nuot no de giu kieu thi `" {{ a }} "` va `"{{ a }}"` cho ket qua khac nhau
ma nhin mat khong phan biet duoc — dung hang loi "nhin khong thay" ma cong
typed khong bat duoc.

## ⛔ Ba thu MUON DUOC ma CO Y KHONG muon

1. **Jinja2 native `literal_eval` tren chuoi da noi.** `native_concat` goi
   `literal_eval` ke ca o duong TRON CHU: `"{{a}}{{b}}"` voi a=1, b=2 cho ra
   **so 12**, va hang so `"1"` khong co `{{ }}` nao cung thanh **so 1**. Do la
   suy doan kieu tu hinh dang chu — dung thu ta phai cam, vi no lam kieu cua
   mot tham so phu thuoc vao *gia tri* chu khong vao *cau*.
2. **n8n chap nhan `{{` khong dong.** `ExpressionSplitter` danh dau
   `hasClosingBrackets: false` roi chay tiep — comment trong ma noi ro do la de
   tuong thich `tmpl` doi cu. Ta TU CHOI: mot tham so khong ro ket thuc o dau
   thi kieu cua no khong xac dinh, va §4.7 can kieu truoc khi chay.
3. **GitHub Actions tu choi ep Array/Object thanh chuoi** (docs Expressions,
   bang "casting to string": `Array` / `Object` → *"are not converted to a
   string"*). Ta ep, bang JSON. Vi mapping vao than HTTP la ca ly do tang nay
   ton tai; nhung ta lay phan KHAC cua cung bang do: `Null → ''` va
   `Boolean → 'true'/'false'`, de `None` KHONG BAO GIO ra chuoi `"None"` va
   `True` khong ra `"True"` truoc mat khach.

## Bo tinh la THAM SO, khong phai import

`tinh(expr) -> Any` di vao bang tham so. Tang nay khong biet ngon ngu bieu
thuc, va no test duoc bang stub — nen no khong cho Task 1 (`bieu_thuc.py` +
`chinh_sach.py`, dang bi sua cung luc) va khong chan Task 1.

## ⛔ Phep do nay KHONG phu

- KHONG phu viec tinh bieu thuc: `tinh` o day la stub. Sai o may duyet AST,
  o namespace §6.2, o bang ham §6.3 deu khong hien ra o day.
- KHONG phu duyet de quy dict/list tham so (Task 3/6): chi mot chuoi mot lan.
- KHONG phu `\\}}` trong long bieu thuc — quyet dinh la `}}` DAU TIEN dong,
  nen `{{ "}}" }}` khong viet duoc. Ghi nhan la gioi han, khong phai bug.
- KHONG phu hieu nang: tran 1 MB duoc kiem, thoi gian thi khong do.
"""
from __future__ import annotations

import pytest

from platform_core.workflow.noi_suy import (
    BIEU_THUC,
    CHU,
    LoiNoiSuy,
    TRAN_CHUOI,
    ep_chuoi,
    noi_suy,
    tach,
)


def _stub(bang: dict):
    """Bo tinh gia: tra gia tri theo ten, ghi lai moi bieu thuc da nhan."""
    da_goi: list[str] = []

    def tinh(bt: str):
        da_goi.append(bt)
        if bt not in bang:
            raise KeyError(bt)
        return bang[bt]

    return tinh, da_goi


# ---------------------------------------------------------------- luat 1

@pytest.mark.parametrize("gia_tri", [
    5, 0, 5.5, True, False, None, [1, 2], {"a": 1}, "chuoi",
])
def test_mot_bieu_thuc_mot_minh_GIU_NGUYEN_KIEU(gia_tri):
    tinh, _ = _stub({"a": gia_tri})
    ket = noi_suy("{{ a }}", tinh)
    assert ket == gia_tri
    assert type(ket) is type(gia_tri)


def test_so_KHONG_bi_bien_thanh_chuoi():
    """Ca lam tep nay ton tai: `{{ workflow.input.n }}` phai ra so 5."""
    tinh, _ = _stub({"workflow.input.n": 5})
    assert noi_suy("{{ workflow.input.n }}", tinh) == 5
    assert not isinstance(noi_suy("{{ workflow.input.n }}", tinh), str)


def test_khong_co_khoang_trang_trong_dau_nhon_van_giu_kieu():
    tinh, da_goi = _stub({"a": 7})
    assert noi_suy("{{a}}", tinh) == 7
    assert da_goi == ["a"]


# ---------------------------------------------------------------- luat 2

def test_khoang_trang_BAO_NGOAI_lam_no_thanh_TRON_CHU():
    """Jinja2 `native_concat` (3 node) va tournament `getExpressionCode`
    (`chunks[0].text !== ''`) doc lap cho cung ket qua nay."""
    tinh, _ = _stub({"a": 5})
    assert noi_suy(" {{ a }} ", tinh) == " 5 "
    assert noi_suy("{{ a }} ", tinh) == "5 "
    assert noi_suy(" {{ a }}", tinh) == " 5"


def test_hai_bieu_thuc_lien_nhau_la_TRON_CHU_khong_phai_so():
    """⛔ Jinja2 native cho ra so 12 o day (`literal_eval("12")`). Ta khong."""
    tinh, da_goi = _stub({"a": 1, "b": 2})
    ket = noi_suy("{{ a }}{{ b }}", tinh)
    assert ket == "12"
    assert isinstance(ket, str)
    assert da_goi == ["a", "b"]


def test_tron_chu_thi_moi_manh_deu_qua_ep_chuoi():
    tinh, _ = _stub({"a": None, "b": True, "c": [1, 2]})
    assert noi_suy("x{{ a }}y{{ b }}z{{ c }}", tinh) == "xytruez[1, 2]"


def test_chuoi_khong_co_bieu_thuc_tra_NGUYEN_VAN():
    """⛔ Khong `literal_eval`: `"1"` la chuoi `"1"`, khong phai so 1."""
    tinh, da_goi = _stub({})
    assert noi_suy("1", tinh) == "1"
    assert noi_suy("xin chao", tinh) == "xin chao"
    assert noi_suy("", tinh) == ""
    assert da_goi == []


def test_gia_tri_khong_phai_chuoi_di_qua_nguyen_ven():
    """n8n `resolveSimpleParameterValue`: khong phai bieu thuc thi tra thang."""
    tinh, da_goi = _stub({})
    assert noi_suy(5, tinh) == 5
    assert noi_suy(None, tinh) is None
    assert noi_suy([1], tinh) == [1]
    assert da_goi == []


# ---------------------------------------------------------------- luat 3

def test_backslash_lam_dau_nhon_thanh_CHU_THUONG():
    tinh, da_goi = _stub({"a": 5})
    assert noi_suy("\\{{ a }}", tinh) == "{{ a }}"
    assert da_goi == []


def test_hai_backslash_la_MOT_backslash_roi_bieu_thuc_THAT():
    """tournament: `isEscaped = backslashCount % 2 === 1`, va
    `normalizeBackslashes` thu `\\\\` xuong `\\`."""
    tinh, da_goi = _stub({"a": 5})
    assert noi_suy("\\\\{{ a }}", tinh) == "\\5"
    assert da_goi == ["a"]


def test_backslash_le_loi_van_la_backslash():
    tinh, _ = _stub({})
    assert noi_suy("c:\\tmp\\x", tinh) == "c:\\tmp\\x"


def test_thoat_roi_thi_KHONG_con_giu_kieu():
    """`"\\{{ a }}"` la chu thuan tuy ⇒ ket qua la chuoi, du a la so."""
    tinh, _ = _stub({"a": 5})
    assert noi_suy("\\{{ a }}", tinh) == "{{ a }}"


# ---------------------------------------------------------------- loi CO CHO

def test_khong_dong_thi_LOI_chu_khong_nuot():
    """⛔ n8n nuot (`hasClosingBrackets: false`, tuong thich `tmpl`). Ta tu choi."""
    tinh, _ = _stub({})
    with pytest.raises(LoiNoiSuy) as e:
        noi_suy("{{", tinh)
    assert e.value.vi_tri == 0
    with pytest.raises(LoiNoiSuy) as e2:
        noi_suy("xin chao {{ a", tinh)
    assert e2.value.vi_tri == 9
    assert "dong" in e2.value.ly_do


def test_bieu_thuc_rong_la_LOI():
    tinh, da_goi = _stub({})
    for chuoi in ("{{ }}", "{{}}", "{{\t}}"):
        with pytest.raises(LoiNoiSuy) as e:
            noi_suy(chuoi, tinh)
        assert e.value.vi_tri == 0
        assert "rong" in e.value.ly_do
    assert da_goi == []


def test_dau_dong_mot_minh_chi_la_CHU():
    tinh, _ = _stub({})
    assert noi_suy("}}", tinh) == "}}"
    assert noi_suy("a }} b", tinh) == "a }} b"
    assert noi_suy("{ a }", tinh) == "{ a }"


def test_long_nhau_KHONG_ton_tai_dau_dong_DAU_TIEN_dong():
    """Nhu `ExpressionSplitter`: sau `{{` ta chi tim `}}`, khong dem muc long.
    ⇒ `{{ {{ a }} }}` giao cho bo tinh dung chuoi `"{{ a"`, va bo tinh se
    tu choi no. Xac dinh duoc, in ra duoc, khong co duong nao hai nghia."""
    tinh, da_goi = _stub({"{{ a": "?"})
    assert noi_suy("{{ {{ a }} }}", tinh) == "? }}"
    assert da_goi == ["{{ a"]


def test_loi_cua_bo_tinh_duoc_danh_dau_VI_TRI_trong_chuoi():
    def tinh(bt):
        raise ValueError("bo tinh tu choi")

    with pytest.raises(ValueError) as e:
        noi_suy("aaaa{{ b }}", tinh)
    assert getattr(e.value, "vi_tri_manh", None) == 4


# ---------------------------------------------------------------- ep_chuoi

@pytest.mark.parametrize("gia_tri,mong_doi", [
    (None, ""),            # GHA: Null → ''  ⛔ khong phai "None"
    (True, "true"),        # GHA: Boolean → 'true'/'false'  ⛔ khong phai "True"
    (False, "false"),
    (5, "5"),
    (5.5, "5.5"),
    ("x", "x"),
    ([1, 2], "[1, 2]"),
    ({"a": 1}, '{"a": 1}'),
    ([None, True], "[null, true]"),
    ({"a": "\u0110"}, '{"a": "\u0110"}'),   # khong \\u-escape tieng Viet
])
def test_ep_chuoi(gia_tri, mong_doi):
    assert ep_chuoi(gia_tri) == mong_doi


def test_ep_chuoi_KHONG_dung_repr_cua_python():
    """`str({'a': 1})` cho `{'a': 1}` — nhay don, khong phai JSON, khong dan
    lai duoc vao than HTTP. Do la thu lot ra giao dien nguoi dung."""
    assert "'" not in ep_chuoi({"a": "b"})
    assert ep_chuoi(["a"]) == '["a"]'


def test_ep_chuoi_kieu_la_thi_LOI_chu_khong_repr():
    class La:
        pass

    with pytest.raises(LoiNoiSuy):
        ep_chuoi(La())


def test_None_mot_minh_van_la_None_khong_phai_chuoi_rong():
    """Luat 1 thang luat ep: `{{ a }}` mot minh giu kieu, ke ca kieu None."""
    tinh, _ = _stub({"a": None})
    assert noi_suy("{{ a }}", tinh) is None
    assert noi_suy("[{{ a }}]", tinh) == "[]"


# ---------------------------------------------------------------- gioi han

def test_chuoi_vao_qua_1MB_bi_tu_choi():
    tinh, da_goi = _stub({})
    with pytest.raises(LoiNoiSuy) as e:
        noi_suy("y" * (TRAN_CHUOI + 1), tinh)
    assert "1 MB" in e.value.ly_do or "tran" in e.value.ly_do
    assert da_goi == []


def test_ket_qua_noi_qua_1MB_bi_tu_choi():
    tinh, _ = _stub({"a": "x" * (TRAN_CHUOI - 10)})
    assert len(noi_suy("{{ a }}!", tinh)) == TRAN_CHUOI - 9
    tinh2, _ = _stub({"a": "x" * TRAN_CHUOI})
    with pytest.raises(LoiNoiSuy):
        noi_suy("{{ a }}!", tinh2)


def test_giu_kieu_KHONG_bi_tran_chuoi_chan():
    """Tran la tran CHUOI. Mot `{{ }}` mot minh tra object thi khong ep chuoi,
    nen khong do bang thuoc do do — tran ket qua 1 MB la viec cua §6.4 o tang
    bo tinh, khong phai cua tang nay."""
    tinh, _ = _stub({"a": list(range(100000))})
    assert noi_suy("{{ a }}", tinh) == list(range(100000))


def test_rat_nhieu_bieu_thuc():
    tinh, da_goi = _stub({"a": 1})
    assert noi_suy("{{ a }}" * 2000, tinh) == "1" * 2000
    assert len(da_goi) == 2000


# ---------------------------------------------------------------- tach()

def test_tach_tra_ve_manh_co_vi_tri():
    manh = tach("xin {{ a }} chao {{ b }}")
    assert [(m.loai, m.text, m.vi_tri) for m in manh] == [
        (CHU, "xin ", 0),
        (BIEU_THUC, "a", 4),
        (CHU, " chao ", 11),
        (BIEU_THUC, "b", 17),
    ]


def test_tach_mot_bieu_thuc_cho_DUNG_MOT_manh():
    """Day la co so cua luat 1: khong co manh chu rong nao di kem."""
    assert [m.loai for m in tach("{{ a }}")] == [BIEU_THUC]
    assert [m.loai for m in tach(" {{ a }}")] == [CHU, BIEU_THUC]
