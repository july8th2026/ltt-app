r"""`ai.llm` · `ai.extract` · `ai.router` publish duoc — va phep DICH dau ra.

## 🔴 Vi sao ba node nay bi chan toi 28/09/2026, va vi sao ly do ghi trong kho SAI

`ai_llm.py` giai thich `publish_duoc=False` bang hai co:

  1. *"compiler chua biet dich `tham_so` thanh `params`"*
  2. *"cau noi suy ten ToolSpec bang `node["type"][4:]`, ap cho `ai.llm` ra `lm`"*

Do truc tiep 28/09: **ca hai da het dung**. Bat co trong bo nho thi
`bien_dich.bien_dich()` chay thang, va `cau_noi.py:103` doc `nd.ten_toolspec` tu lau.

⇒ Neu tin docstring, ta bat co va tuong da xong. Thu that su hong nam o **TU VUNG
  DAU RA**:

      ToolSpec `text.chat`  returns  content · tool_calls · usage
      `ai.llm`              cong_ra  text · json
      `ai.extract`          cong_ra  json
      `ai.router`           cong_ra  nhanh

  va `ap_ket_qua` ghi `output_ref = result` **nguyen van**. Nen
  `{{ nodes.n2.output.text }}` doc ra **RONG** — ⛔ khong loi, ⛔ khong canh bao,
  sau khi credit da bi tru.

⚠️ Mot loi giai thich SAI cho mot cai co nguy hiem hon ⛔ khong co loi giai thich
   nao: no **moi nguoi doc bat co**. Cung ho tham chieu chet ma B12 ghi
   (`dung_video.py:35` noi `demucs_runner` ⛔ khong dat `set_num_threads`, trong khi
   dong 324 da dat).

## ⭐ Va `chon_nhanh()` la mot ham DUNG, CO TEST, ⛔ KHONG AI GOI

Viet o plan P7 Task 2, kiem boi `test_2903`, nam ngoai moi duong chay cho toi hom
nay. Cung ho `gate.ngan_sach_loi(tru_phien_khac=...)`: co tai lieu, co phep kiem
rieng, ⛔ khong noi nao dung ⇒ ⛔ khong phep kiem nao that bai khi no vang mat.

🔑 *"Co ham + co test"* ⛔ **khong** tra loi *"tinh nang co chay khong"*. Cau tra
   loi nam o **AI GOI NO** — va ⛔ khong bang do phu nao hoi cau do, vi dong ma ay
   **co** chay: trong test.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from platform_core.workflow import bien_dich, cau_noi, cong_cu, nut_loi  # noqa: E402
from platform_core.workflow.nut_loi import ai_llm, ai_router  # noqa: E402

BA_NODE = ("ai.llm", "ai.extract", "ai.router")


# ══════════════════════════════════════════════════════════════════════════════
#  1. Ba node publish duoc, va bien dich THAT SU chay
# ══════════════════════════════════════════════════════════════════════════════

def _tai_lieu(loai: str, tham_so: dict) -> dict:
    return {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "n1", "type": "trigger.manual", "position": {"x": 0, "y": 0}},
        {"id": "n2", "type": loai, "position": {"x": 200, "y": 0},
         "params": dict(tham_so)},
    ], "edges": []}]}


THAM_SO = {
    "ai.llm": {"prompt": "xin chao", "model": "ltt-3.8"},
    "ai.extract": {"prompt": "trich", "model": "ltt-3.8",
                   "luoc_do": {"type": "object"}},
    "ai.router": {"prompt": "phan loai", "ai_choice": ["spam", "that"]},
}


@pytest.mark.parametrize("loai", BA_NODE)
def test_bien_dich_duoc(loai):
    """⛔ Do HANH VI, ⛔ khong do cai co. Mot `publish_duoc=True` ma bo bien dich
    van tu choi thi cai co la mot loi hua, ⛔ khong phai mot tinh nang."""
    ke = bien_dich.bien_dich(_tai_lieu(loai, THAM_SO[loai]))
    assert "nodes" in ke and "thu_tu" in ke, sorted(ke)


@pytest.mark.parametrize("loai", BA_NODE)
def test_co_publish_duoc_BAT(loai):
    assert nut_loi.tat_ca()[loai].publish_duoc is True


@pytest.mark.parametrize("loai", BA_NODE)
def test_ten_toolspec_tra_ra_that_va_job_type_KHOP(loai):
    """🔴 Day la ve ma docstring cu noi con hong. Do lai de khoi ai phai tin
    mot cau van: `text.chat` co that trong `cong_cu.tat_ca()`, va `job_type`
    hai ben khop nhau."""
    nd = nut_loi.tat_ca()[loai]
    cc = cong_cu.tat_ca().get(nd.ten_toolspec)
    assert cc is not None, f"{loai}: `{nd.ten_toolspec}` khong co trong ToolSpec"
    assert cc.job_type == nd.job_type, (loai, cc.job_type, nd.job_type)


# ══════════════════════════════════════════════════════════════════════════════
#  2. Phep DICH — moi cong ra phai duoc dien
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("loai", BA_NODE)
def test_moi_CONG_RA_deu_duoc_phep_dich_dien(loai):
    """🔴 Bai dat nhat muc nay, va no do dung con bo goc: mot cong ra KHONG duoc
    dien thi bieu thuc doc no ra **rong**, ⛔ khong loi, sau khi da tru credit.

    ⭐ Do bang cach so **tap khoa** hàm dịch trả với **tap cong ra** đã khai —
       ⛔ khong bang cach doc tung ten trong ma. Neu mai ai them mot cong ra thu
       ba cho `ai.llm` ma quen dien no, bai nay do.
    """
    nd = nut_loi.tat_ca()[loai]
    ra = nd.doi_dau_ra({"content": '{"a": 1}'}, THAM_SO[loai])
    cong = {c[0] for c in nd.cong_ra}
    thieu = cong - set(ra)
    assert not thieu, (
        f"{loai}: phep dich KHONG dien cong ra {sorted(thieu)} ⇒ mot bieu thuc "
        f"`{{{{ nodes.x.output.{sorted(thieu)[0]} }}}}` se doc ra RONG. "
        f"Ham dich tra: {sorted(ra)}")


def test_ai_llm_dich_content_sang_text():
    ra = ai_llm.doi_dau_ra_llm({"content": "xin chao"}, {})
    assert ra["text"] == "xin chao"
    assert ra["json"] is None, "van xuoi ⇒ cong `json` phai la None, khong phai loi"


def test_ai_llm_van_xuoi_KHONG_bi_coi_la_loi():
    """⛔ Doi chung: `ai.llm` ⛔ khong bat buoc JSON (chi `ai.extract` moi bat).
    Mot ban va "chat che hon" bat loi o day se pha node `ai.llm`."""
    assert ai_llm.doi_dau_ra_llm({"content": "khong-phai-json"}, {})["text"]


def test_ai_extract_tra_gia_tri_DA_PARSE():
    ra = ai_llm.doi_dau_ra_extract({"content": '{"ten": "an", "tuoi": 3}'},
                                   {"luoc_do": {"type": "object"}})
    assert ra["json"] == {"ten": "an", "tuoi": 3}


def test_ai_router_chon_dung_nhanh():
    ra = ai_router.doi_dau_ra_router({"content": " spam "},
                                     {"ai_choice": ["spam", "that"]})
    assert ra["nhanh"] == "spam", "khong `strip` hoac khong goi `chon_nhanh`"


def test_ai_router_khong_khop_thi_ve_MAC_DINH():
    ra = ai_router.doi_dau_ra_router({"content": "spam vi co link la"},
                                     {"ai_choice": ["spam", "that"]})
    assert ra["nhanh"] == ai_router.NHANH_MAC_DINH, (
        "khop LONG: mot cau giai thich co chua ten nhanh da di qua nhu the model "
        "da CHON — xem docstring `chon_nhanh`")


def test_ai_router_mac_dinh_RONG_roi_ve_hang_chu_khong_thanh_ten_rong():
    """⚠️ `default` cua JSON Schema ⛔ KHONG tu dien vao `params` da luu. Nen mot
    `params` cu (soan truoc khi them `mac_dinh`) se cho chuoi rong."""
    ra = ai_router.doi_dau_ra_router({"content": "khong khop gi"},
                                     {"ai_choice": ["a"], "mac_dinh": ""})
    assert ra["nhanh"] == ai_router.NHANH_MAC_DINH


# ══════════════════════════════════════════════════════════════════════════════
#  3. 🔴 BUT TOAN — `credit_cost` phai SONG SOT qua phep dich
# ══════════════════════════════════════════════════════════════════════════════
#
# `credit_cost` la handler bao gia THAT (vd theo token). `ap_ket_qua` doc no de
# ghi `cost_credit`. Mot ham dich tra `{"text": ...}` sach se **xoa** no, va luot
# ay am tham bi tinh theo `gia_that` uoc luong.
#
# ⚠️ Day ⛔ khong phai mot loi hien thi — la **ghi sai so**. Nen no duoc chot o
#    HAI muc: hang so (`KHOA_HE_THONG_GIU_QUA_PHEP_DICH`) va **thu tu goi** trong
#    `ap_ket_qua` (phep dich phai o TRUOC dong doc `credit_cost`).

def test_khoa_he_thong_co_credit_cost():
    assert "credit_cost" in cau_noi.KHOA_HE_THONG_GIU_QUA_PHEP_DICH


def test_phep_dich_dat_TRUOC_dong_doc_credit_cost():
    """⭐ Chot **THU TU** bang AST, vi day la mot quan he vi tri — va no la thu
    mot ban refactor "don dep" de doi nhat ma ⛔ khong ai thay gi khac la.

    🔴 Neu phep dich chay SAU dong `bao = du_lieu.get("credit_cost")` thi hang so
       giu khoa o tren thanh **vo dung**: `bao` da doc xong tu dict CU, va viec
       giu khoa trong dict MOI ⛔ khong con anh huong gi. Mot bai chi kiem hang so
       se **XANH** trong ca do — day la ve phan biet duoc.
    """
    src = (GOC / "platform_core" / "workflow" / "cau_noi.py").read_text(
        encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)
           and n.name == "ap_ket_qua"]
    assert ham, "mat moc `ap_ket_qua`"

    dong_dich = dong_credit = None
    for n in ast.walk(ham[0]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "doi":
            dong_dich = min(dong_dich or n.lineno, n.lineno)
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "bao" for t in n.targets):
            dong_credit = n.lineno
    assert dong_dich is not None, "khong thay loi goi `doi(...)` - phep dich dau?"
    assert dong_credit is not None, "khong thay dong gan `bao = ...`"
    assert dong_dich < dong_credit, (
        f"phep dich o dong {dong_dich}, doc `credit_cost` o dong {dong_credit}: "
        "phep dich phai chay TRUOC, neu khong hang so giu khoa thanh vo dung")


def test_ham_dich_khong_tu_giu_credit_cost_MA_cau_noi_giu():
    """⛔ Doi chung: cac ham dich CO Y ⛔ khong mang `credit_cost` sang.

    ⭐ Vi sao de vay thay vi bat moi ham dich tu nho: mot nghia vu phai nho o N
       cho se bi bo o cho thu N+1. Dat no MOT lan o cau noi thi mot ham dich moi
       ⛔ khong the quen — no **khong duoc phep** biet ve `credit_cost`.
    """
    ra = ai_llm.doi_dau_ra_llm({"content": "a", "credit_cost": 7}, {})
    assert "credit_cost" not in ra, (
        "ham dich tu mang `credit_cost` sang ⇒ nghia vu bi chia hai cho, va cho "
        "thu hai se trôi khoi cho thu nhat")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ══════════════════════════════════════════════════════════════════════════════
#  4. 🔴 Duong VAO — `doi_tham_so`. Toi da va MOT NUA roi dung.
# ══════════════════════════════════════════════════════════════════════════════
#
# Mot run THAT tren production 28/09/2026 (`c50eb822`, mau 4, 31 giay):
#
#     node y_tuong (ai.llm)  FAILED
#     provider_loi: ThamSoSai: `messages` phai la mot danh sach khong rong
#
# `ai.llm` khai `{prompt, model}`; `apps/ltt_llm/features.py:352` doi
# `messages=[{role, content}]`. ⛔ Khong ai dich giua hai hinh dang.
#
# ⚠️ Toi thay hai tu vung khac nhau o duong **RA** (`content` -> `text`), va duoc.
#    Toi ⛔ **khong hoi** duong **VAO** co cung van de khong. Va docstring cua
#    `ai_llm.py` **da noi thang**: *"mot `prompt`, khong phai mang `messages` day
#    du vai tro"*. Toi doc cau ay, rut ket luan dung ve mot chieu, roi dung.
#
# ⭐ ⇒ Khi phat hien hai module dung hai tu vung, cau hoi ⛔ khong phai *"cho nao
#   lech?"* ma la ***"CA HAI chieu da duoc dich chua?"***. Mot cho noi co hai dau,
#   va va mot dau lam cai con lai **KHO THAY HON** — vi nay node publish duoc,
#   bien dich duoc, chay duoc, va chi hong o tan provider.

def test_ba_node_ai_deu_co_doi_tham_so():
    for loai in BA_NODE:
        nd = nut_loi.tat_ca()[loai]
        assert nd.doi_tham_so is not None, (
            f"{loai} ⛔ khong co `doi_tham_so` ⇒ `params` cua node di thang sang "
            "job, va handler `ltt_llm.chat` se tu choi vi thieu `messages`")


def test_dich_prompt_thanh_messages_dung_hinh_dang_handler():
    """⭐ Hinh dang lay tu `features.py:352-355`: danh sach KHONG RONG, moi phan
    tu co `role`. ⛔ Khong doan tu tai lieu OpenAI."""
    ra = ai_llm.doi_tham_so_ai({"prompt": "xin chao", "model": "ltt-3.8"})
    assert isinstance(ra.get("messages"), list) and ra["messages"], ra
    for tin in ra["messages"]:
        assert isinstance(tin, dict) and "role" in tin, tin
    assert ra["messages"][0]["content"] == "xin chao"
    assert ra["model"] == "ltt-3.8"


def test_KHONG_gui_tham_so_cua_NODE_sang_job():
    """⛔ `luoc_do` (ai.extract) va `ai_choice`/`mac_dinh` (ai.router) la tham so
    cua **node** — dung o `hau_kiem`/`doi_dau_ra`. Gui sang handler la gui rac.

    ⭐ Do bang tap khoa, ⛔ khong bang mot danh sach ten cam: mot tham so node MOI
       se di qua danh sach cam, nhung ⛔ khong di qua duoc mot lenh doi *"chi
       nhung khoa handler nhan"*.
    """
    ra = ai_llm.doi_tham_so_ai({
        "prompt": "p", "model": "ltt-3.8", "luoc_do": {"type": "object"},
        "ai_choice": ["a", "b"], "mac_dinh": "a"})
    la = set(ra) - {"messages", "model", "max_tokens"}
    assert not la, f"gui khoa cua NODE sang job: {sorted(la)}"


def test_prompt_RONG_van_ra_messages_khong_rong():
    """⚠️ Handler tu choi `messages` RONG. Mot `prompt` rong (nguoi soan chua dien)
    phai ra mot `messages` co **mot** phan tu voi `content` rong — de loi bao la
    *"model tra ve rong"* hay *"prompt rong"* chu ⛔ khong phai
    `ThamSoSai: messages phai la danh sach khong rong`, mot cau ⛔ khong lien quan
    gi den thu nguoi dung lam sai."""
    ra = ai_llm.doi_tham_so_ai({"prompt": "", "model": "ltt-3.8"})
    assert ra["messages"] and ra["messages"][0]["role"] == "user"


def test_dich_VAO_dat_TRUOC_tinh_gia_va_khoa_idem():
    """🔴 Ve phan biet duoc, va no do THU TU — thu mot ban refactor "don dep" de
    doi nhat.

    Dat sai cho ⛔ **khong bao loi**: no chi lam `tinh_gia` va `_khoa_idem` noi ve
    mot thu KHAC thu duoc gui. `text.chat` tinh gia theo token cua `messages`, nen
    tinh tren `prompt` tho ra mot so khac; va khoa khu trung mo ta mot luot gui
    ⛔ khong ton tai. Ca hai im lang.
    """
    src = (GOC / "platform_core" / "workflow" / "cau_noi.py").read_text(
        encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)
           and n.name == "nop_job"]
    assert ham, "mat moc `nop_job`"
    d_dich = d_gia = d_khoa = None
    for n in ast.walk(ham[0]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "_doi":
            d_dich = n.lineno if d_dich is None else min(d_dich, n.lineno)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "tinh_gia":
            d_gia = n.lineno if d_gia is None else min(d_gia, n.lineno)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "_khoa_idem":
            d_khoa = n.lineno if d_khoa is None else min(d_khoa, n.lineno)
    assert d_dich is not None, "`nop_job` khong goi ham dich (`_doi`)"
    assert d_gia is not None and d_dich < d_gia, (
        f"dich o dong {d_dich}, `tinh_gia` o {d_gia}: gia phai tinh tren params "
        "DA DICH — tuc thu that su gui di")
    assert d_khoa is not None and d_dich < d_khoa, (
        f"dich o dong {d_dich}, `_khoa_idem` o {d_khoa}: khoa khu trung phai mo "
        "ta dung luot gui ay")
