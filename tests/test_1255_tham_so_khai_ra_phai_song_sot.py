"""test_1255 — moi tham so KHAI trong hop dong phai SONG SOT qua bo kiem.

## 🔴 Loi that, do duoc tren production 14/09/2026

`apps/ltt_llm/features.kiem_tham_so` la mot **danh sach trang**: no dung mot
`sach = {...}` moi va chi chep sang nhung khoa no biet. Thu gi khong duoc chep
thi **bien mat khong mot tieng dong**, va khach van nhan **200**.

Cung mot request `response_format: json_schema` bat buoc `ten/tuoi/thanh_pho`:

    qua may A    ->  {"id":10,"name":"...","age":34,"city":"Ha Noi"}  boc ```json
    thang may B  ->  {"ten":"...","tuoi":34,"thanh_pho":"Ha Noi"}       DUNG khuon

Engine lam duoc hoan hao. Tang nen tang nem tham so di roi bao thanh cong.

⛔ Do la hinh dang **cua gia** te nhat trong so tay du an: khong phai mot loi
   bao sai, ma mot lo**i IM LANG**. Khach dat mot tham so, tin rang no chay, va
   bo phan tich JSON cua ho vo **luc duoc luc khong** — thu rat kho truy.

## Vi sao phep kiem nay kiem HAM, khong kiem DU LIEU

Mot phep kiem liet ke "response_format phai chay, tool_choice phai chay" se
xanh mai cho toi khi ai do them khoa thu bay va quen viet dong thu bay. No do
dung thu no da biet.

⭐ Phep kiem nay lay danh sach tu **chinh hop dong cong khai**
   (`ToolSpec.params_schema`) roi doi TUNG khoa phai di xuyen. Them mot khoa
   vao hop dong ma quen day no qua `kiem_tham_so` ⇒ **do ngay**, khong can ai
   nho viet them test.
"""
from __future__ import annotations

import pytest

from apps.ltt_llm.features import kiem_tham_so

#: Gia tri HOP LE cho tung kieu khai trong `params_schema`. Khoa nao khong co
#: khuon o day thi phep kiem NEM — de mot kieu moi khong lang le duoc bo qua.
MAU_THEO_KHOA = {
    "messages": [{"role": "user", "content": "xin chao"}],
    "model": "ltt-3.8",
    "max_tokens": 128,
    "temperature": 0.7,
    "tools": [{"type": "function",
               "function": {"name": "f", "parameters": {"type": "object"}}}],
    # `none` da bi BO khoi hop dong 14/09 (do duoc: 2 token thay vi ~1.180).
    "reasoning_effort": "low",
    "response_format": {"type": "json_schema",
                        "json_schema": {"name": "n",
                                        "schema": {"type": "object"}}},
    "tool_choice": "auto",
    "parallel_tool_calls": True,
    "top_p": 0.9,
    "seed": 42,
    "stop": ["\n\n"],
}


def _hop_dong() -> dict:
    from apps.ltt_llm.manifest import MANIFEST

    for tool in MANIFEST.tools:
        if tool.name == "text.chat":
            return dict(tool.params_schema)
    raise AssertionError("khong thay tool `text.chat` trong manifest")


def test_moi_khoa_trong_hop_dong_deu_co_mau_de_thu():
    """Mot kieu tham so moi khong duoc lang le thoat khoi phep kiem nay."""
    thieu = sorted(set(_hop_dong()) - set(MAU_THEO_KHOA))
    assert not thieu, (
        f"hop dong khai {thieu} ma phep kiem chua co mau hop le de thu — "
        "them mau vao MAU_THEO_KHOA, dung noi rong phep kiem")


@pytest.mark.parametrize("khoa", sorted(_hop_dong()))
def test_khoa_khai_trong_hop_dong_phai_song_sot(khoa):
    """🔴 Day la phep kiem chinh. Khai ma bi vut = cua gia."""
    vao = {"messages": MAU_THEO_KHOA["messages"], "model": "ltt-3.8"}
    vao[khoa] = MAU_THEO_KHOA[khoa]

    ra = kiem_tham_so(vao)

    assert khoa in ra, (
        f"`{khoa}` duoc KHAI trong params_schema nhung `kiem_tham_so` khong "
        f"chep no sang — khach gui no, nhan 200, va no bi vut im lang. "
        f"Do dung la loi da xay ra voi `response_format` (14/09/2026).")


def test_DOI_CHUNG_phep_kiem_nay_do_duoc():
    """⛔ Mot phep kiem khong the do khong chung minh gi (Luat 3 cua chuong trinh).

    Day la doi chung: mot khoa KHONG duoc `kiem_tham_so` biet toi thi phai
    vang mat o dau ra. Neu menh de nay sai thi phep kiem tren cung vo nghia,
    vi no se xanh voi bat cu thu gi.
    """
    ra = kiem_tham_so({"messages": MAU_THEO_KHOA["messages"],
                       "model": "ltt-3.8",
                       "mot_khoa_khong_ai_khai": 123})
    assert "mot_khoa_khong_ai_khai" not in ra, (
        "bo kiem dang cho MOI thu di xuyen — phep kiem tren khong con y nghia")


# ── Tung tham so moi: hop le thi qua, sai thi TU CHOI (khong im lang) ────────

@pytest.mark.parametrize("xau", [
    {"response_format": "json"},                       # phai la doi tuong
    {"response_format": {"type": "khong_ton_tai"}},
    {"response_format": {"type": "json_schema"}},       # thieu json_schema
    {"tool_choice": "bat_buoc"},                        # ngoai none|auto|required
    {"tool_choice": 5},
    # Dang DOI TUONG bi tu choi CO CHU Y: he kieu Public API khong co kieu HOP
    # nen no khong cong bo duoc; nhan ma khong khai la mot cua giau.
    {"tool_choice": {"type": "function", "function": {"name": "f"}}},
    {"parallel_tool_calls": "yes"},                     # phai la bool
    {"top_p": 0.0},                                     # (0..1], 0 khong hop le
    {"top_p": 1.5},
    {"seed": "42"},
    {"seed": True},                                     # bool KHONG phai so nguyen
    {"stop": []},
    {"stop": ["a", "b", "c", "d", "e"]},                # tran 4 cua OpenAI
    {"stop": [1, 2]},
])
def test_gia_tri_sai_bi_TU_CHOI_chu_khong_bi_bo_qua(xau):
    """Tu choi to rang con hon bo qua im lang — cung bai hoc, chieu nguoc lai."""
    from apps.ltt_llm.features import ThamSoSai

    vao = {"messages": MAU_THEO_KHOA["messages"], "model": "ltt-3.8", **xau}
    with pytest.raises(ThamSoSai):
        kiem_tham_so(vao)


# ── Tang thu hai: song sot qua bo kiem VAN CHUA phai la gui di ───────────────

#: Nhung khoa co DOI SO CO TEN rieng trong `dieu_phoi.goi`, nen khong di qua
#: duong `them`. Chung co lop dich rieng (vd alias model -> id noi bo).
CO_DUONG_RIENG = {"messages", "model", "max_tokens", "temperature",
                  "reasoning_effort", "tools"}


def test_moi_khoa_khong_co_duong_rieng_phai_nam_trong_bang_CHUYEN_THANG():
    """🔴 Song sot qua `kiem_tham_so` moi la mot NUA duong.

    Truoc 14/09, mot tham so phai duoc moc tay o BON tang:
    `kiem_tham_so` -> `dieu_phoi.goi(...)` -> `than` -> may B. Dung o tang mot
    roi im lang bien mat la dung nhung gi da xay ra voi `response_format`.

    Phep kiem nay chot rang khong con khoang trong ay: khoa nao khai trong hop
    dong ma khong co doi so rieng thi PHAI nam trong `THAM_SO_CHUYEN_THANG`.
    """
    from apps.ltt_llm.features import THAM_SO_CHUYEN_THANG

    can_chuyen = set(_hop_dong()) - CO_DUONG_RIENG
    thieu = sorted(can_chuyen - set(THAM_SO_CHUYEN_THANG))
    assert not thieu, (
        f"{thieu} duoc khai trong hop dong va qua duoc `kiem_tham_so`, nhung "
        "KHONG nam trong `THAM_SO_CHUYEN_THANG` — chung se dung lai o nen tang "
        "va khong bao gio toi may B, trong khi khach van nhan 200")

    thua = sorted(set(THAM_SO_CHUYEN_THANG) - set(_hop_dong()))
    assert not thua, (
        f"{thua} duoc chuyen thang len may B nhung KHONG khai trong hop dong "
        "cong khai — mot tham so khong ai cong bo ma van co tac dung")


def test_bang_chuyen_thang_thuc_su_toi_dieu_phoi(monkeypatch):
    """Doi chung cua phep kiem tren: bat lay than request that.

    Khong goi may B — thay `dieu_phoi.goi` bang mot ban ghi lai doi so.
    """
    from apps.ltt_llm import features

    bat = {}

    def gia(db, **kw):
        bat.update(kw)
        raise RuntimeError("dung o day — chi can doi so")

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)
    with pytest.raises(RuntimeError):
        features.chay(None, {"messages": MAU_THEO_KHOA["messages"],
                             "model": "ltt-3.8",
                             "response_format": MAU_THEO_KHOA["response_format"],
                             "top_p": 0.9, "seed": 7, "stop": ["HET"]})

    them = bat.get("them") or {}
    assert them.get("top_p") == 0.9 and them.get("seed") == 7
    assert them.get("stop") == ["HET"]
    assert them.get("response_format") == MAU_THEO_KHOA["response_format"], (
        "`response_format` khong toi duoc dieu phoi — dung cho no bien mat "
        "truoc 14/09")


def test_stop_dang_chuoi_don_duoc_chuan_hoa_thanh_danh_sach():
    """OpenAI nhan ca chuoi lan mang; ta chuan hoa ve mang o mot cho."""
    ra = kiem_tham_so({"messages": MAU_THEO_KHOA["messages"],
                       "model": "ltt-3.8", "stop": "HET"})
    assert ra["stop"] == ["HET"]


# ── Tang thu BA: `dieu_phoi` va `CongVlm.chat` phai KHOP CHU KY ──────────────

def test_moi_khoa_dieu_phoi_dat_vao_THAN_phai_la_doi_so_CongVlm_chat_nhan():
    """🔴 Loi nay DA LEN PRODUCTION 14/09/2026, va hai tang kiem tren khong thay.

    `dieu_phoi._goi_openai` goi `CongVlm(...).chat(**than)` — no RAI ca `than`
    thanh doi so co ten. Ban dau toi viet `than.update(them)`, nen sau tham so
    moi thanh kwargs ma `CongVlm.chat` khong co:

        CongVlm.chat() got an unexpected keyword argument 'seed'

    Moi luot mang bat ky tham so moi nao deu **503**; mot luot khong mang gi van
    **200**. Hai tang kiem tren deu xanh vi chung dung lai o `dieu_phoi.goi` —
    chung chot rang tham so ROI KHOI app, khong chot rang no VAO DUOC may B.

    ⛔ Bai hoc lap lai cua kho: mot phep kiem thay `dieu_phoi.goi` bang ban gia
       khong bao gio cham toi chu ky that o tang duoi. Phep kiem nay soi CHU KY,
       nen no khong can goi may B ma van bat duoc dung lop loi ay.
    """
    import inspect
    import textwrap

    from platform_core.llm.cong_vlm import CongVlm

    nhan = set(inspect.signature(CongVlm.chat).parameters) - {"self"}

    # ⛔ DOC BANG AST, KHONG QUET VAN BAN.
    #
    #    Ban dau phep kiem nay viet `assert 'than["them"]' in nguon` — va no
    #    XANH voi ma DA HONG, vi khoi CHU THICH ngay tren doan ma cung chua
    #    nguyen van chuoi ay. Mot bo do quet van ban khong phan biet duoc loi
    #    giai thich voi dieu duoc lam; kho nay da ghi dung cai bay do.
    import ast

    from platform_core.llm import dieu_phoi

    cay = ast.parse(textwrap.dedent(inspect.getsource(dieu_phoi.goi)))
    gan_them, update_them = False, False
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Assign):
            for dich in nut.targets:
                if (isinstance(dich, ast.Subscript)
                        and isinstance(dich.value, ast.Name)
                        and dich.value.id == "than"
                        and isinstance(dich.slice, ast.Constant)
                        and dich.slice.value == "them"):
                    gan_them = True
        if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                and nut.func.attr == "update"
                and isinstance(nut.func.value, ast.Name)
                and nut.func.value.id == "than"):
            update_them = True

    assert not update_them, (
        "`dieu_phoi` dang goi `than.update(...)` — no rai tham so phu thanh "
        "kwargs cua `CongVlm.chat`, va moi luot mang tham so moi se 503")
    assert gan_them, (
        "`dieu_phoi` phai dat tham so phu vao `than[\"them\"]` de chung di "
        "qua doi so `them` cua `CongVlm.chat`")

    for khoa in ("model", "messages", "tools", "max_tokens", "temperature",
                 "reasoning_effort", "them"):
        assert khoa in nhan, (
            f"`dieu_phoi` dat `{khoa}` vao `than`, nhung `CongVlm.chat` khong "
            f"nhan doi so ay — `chat(**than)` se nem TypeError va cua tra 503")
