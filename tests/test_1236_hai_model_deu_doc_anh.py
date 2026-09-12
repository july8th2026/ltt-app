"""test_1236 — CA HAI model nha deu khai doc duoc anh (L-03).

## Loi no ghim

`apps/ltt_llm/manifest.py` tung khai `ltt-3.8` la **"Text only"** va **khong** co
`constraints.reads_images`, trong khi engine tren may B nap `--mmproj` cho **ca
hai** ho so tu Task 3.3.

Do 13/09/2026, `llama-swap /running` tren may B that:

    qwen38-api  --mmproj H:/LTT_LLM/models/mmproj-F16.gguf
    qwen35-api  --mmproj H:/LTT_LLM/models/mmproj-9B-F16-unsloth.gguf

va chinh llama-swap mo ta ca hai ho so la *"doc anh"*.

## 🔴 Vi sao mot loi khai THIEU nguy hon mot loi khai THUA

Chu thich cu o `manifest.py` lo dung mot chieu: *"hua doc anh ma engine khong
doc duoc"*. Chieu da thuc su xay ra la chieu kia — **hua thieu**:

* `server/api/tools.py:52` doc `constraints.reads_images` de quyet dinh co bat
  nut dinh anh hay khong;
* khai thieu => nut tat => nang luc da tra tien de dung **khong ai dung duoc**;
* va khong co gi bao dong, vi moi thu "chay dung" theo ban khai.

⇒ Mot loi khai THUA gay loi on ao (khach gui anh, model tu choi). Mot loi khai
  THIEU gay im lang — va im lang thi khong ai di tim.

## Pham vi cua phep kiem nay

⛔ No kiem **ban khai**, khong kiem engine. Mot phep kiem goi may B that se phu
   thuoc GPU va khong chay duoc trong gate. Phan "engine that co mmproj khong"
   duoc ghi bang phep do tay o `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` (L-03).

⚠️ Nen neu mot ngay nao do mmproj bi **go** khoi mot ho so, phep kiem nay van
   xanh va ban khai se thanh loi khai THUA. Cach chan that la `catalog.HO_SO`
   phai sinh tu cau hinh engine — chua co, ghi vao so.
"""
from __future__ import annotations

import pytest


def _tool():
    from apps.ltt_llm.manifest import MANIFEST

    return next(t for t in MANIFEST.tools if t.name == "text.chat")


def _models() -> dict:
    """Bản khai model — đọc từ `api_contract`, nguồn mà tầng công bố dùng.

    ⛔ Không đọc từ một bản sao trong test: `server/api/tools.py` đọc đúng chỗ
       này, nên một phép kiểm đọc chỗ khác sẽ xanh trong khi bề mặt thật sai.
    """
    return dict((_tool().api_contract or {})["models"])


HAI_TEN = ("ltt-3.8", "ltt-3.5")


@pytest.mark.parametrize("ten", HAI_TEN)
def test_moi_model_deu_khai_reads_images(ten):
    m = _models()
    assert ten in m, f"thieu model {ten!r} trong ban khai"
    rb = m[ten].get("constraints") or {}
    assert rb.get("reads_images") is True, (
        f"`{ten}` khong khai `reads_images` — engine tren may B nap `--mmproj` "
        f"cho CA HAI ho so, nen ban khai nay lam `server/api/tools.py` tat nut "
        f"dinh anh cho mot model doc duoc anh (L-03).")


@pytest.mark.parametrize("ten", HAI_TEN)
def test_khong_model_nao_con_tu_khai_text_only(ten):
    """⛔ Chuoi 'Text only' la loi khai truc tiep mau thuan voi `reads_images`."""
    mo_ta = (_models()[ten].get("description") or "").lower()
    assert "text only" not in mo_ta, (
        f"`{ten}` van tu mo ta la 'Text only' trong khi khai `reads_images` — "
        f"hai cho noi hai dieu nguoc nhau, va khach doc cho nao thi tin cho do.")


@pytest.mark.parametrize("ten", HAI_TEN)
def test_mo_ta_NOI_RA_viec_doc_anh(ten):
    """Co may khai thoi chua du: mo ta la thu khach DOC.

    `constraints.reads_images` dieu khien giao dien; `description` dieu khien
    ky vong cua nguoi viet ma. Lech nhau thi mot trong hai se sai.
    """
    mo_ta = (_models()[ten].get("description") or "").lower()
    assert "image" in mo_ta, (
        f"`{ten}` khai `reads_images=True` nhung mo ta khong he nhac toi anh")


def test_hai_model_KHONG_cung_mot_mo_ta():
    """⛔ DOI CHUNG cho ba ca tren: chung se van xanh neu ai do chep mo ta cua
    `ltt-3.5` de len `ltt-3.8`. Ca nay chot rang hai model van la HAI san pham
    khac nhau, khong phai mot cau chu duoc nhan doi."""
    m = _models()
    assert m["ltt-3.8"]["description"] != m["ltt-3.5"]["description"]
    assert "deepest" in (m["ltt-3.8"]["description"] or "").lower()
    assert "cheaper" in (m["ltt-3.5"]["description"] or "").lower()


def test_be_mat_cong_khai_cung_thay_co_nay():
    """Cho nao doc `reads_images` thi phai thay no o CA HAI model.

    `server/api/tools.py:52` la noi quyet dinh bat/tat nut dinh anh. Ghim o day
    de mot ban sua chi doi `manifest` ma quen tang cong bo se bi bat.
    """
    co = {ten: bool((spec.get("constraints") or {}).get("reads_images"))
          for ten, spec in _models().items()}
    assert co == {"ltt-3.8": True, "ltt-3.5": True}, co
