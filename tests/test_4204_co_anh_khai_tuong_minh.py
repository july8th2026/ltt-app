"""test_4204 - tran token ANH cua engine phai duoc KHAI TUONG MINH trong yaml.

## 🔴 Vi sao tep nay ton tai

Truoc 28/09/2026, `llama-swap.yaml` khong truyen `--image-min-tokens` hay
`--image-max-tokens` cho ho so nao. Hai so ay van CO - chung la mac dinh
`set_limit_image_tokens(8, 4096)` ma llama.cpp dat cho ho Qwen2VL/Qwen25VL/
Qwen3VL (`tools/mtmd/clip.cpp:1660`, build b10883 = commit 91f6a6cf3) - nhung
chung NGAM.

Mot con so ngam la mot con so khong ai buoc duoc vao gi. Hau qua do duoc:

  * may A dat cho KV cho MOI anh bang mot hang PHANG 2.048
    (`apps/ltt_llm/ngan_sach.TOKEN_GIU_MOI_ANH`);
  * chi phi THAT la mot ham cua kich thuoc, do 28/09 tren ca hai model:
    320x240 -> 82 · 1024x768 -> 770 · 2048x2048 -> 4.098 · 3840x2160 -> 4.082;
  * tuc o dinh, dat cho THIEU 2x - dung chieu ma `-kvu` mot lan tran giet MOI
    slot (llama.cpp b10689).

⇒ Tep yaml la thu KHOI DONG tien trinh; moi ban sao khac chi la loi ke ve no
  (`llm_gateway/vat_ly.py` docstring). Nen cho duy nhat dung de khai hai so ay
  la yaml, va phep kiem nay la thu giu cho chung khong bien mat lai.

## ⛔ Vi sao khong khai `bat_buoc=True` trong bo doc

Xem chu thich o `VatLy.token_anh_toi_thieu`. Tom tat: `bat_buoc` se bien mot
yaml cu thanh "cong khong khoi dong duoc", tuc mot loi cua duong ANH thanh su
co toan phan cho ca khach chi gui CHU. Fail-closed dung cho la o nguoi tinh
ngan sach anh. Cai gia phai tra: bo doc khong con la luoi, nen LUOI CHINH LA
TEP NAY.

## Phep tiem nghich

`test_bo_doc_thay_duoc_khi_co_VA_khi_khong` chay bo doc tren mot yaml KHONG co
hai co. Thieu no thi `test_yaml_that_khai_hai_co` van xanh ngay ca khi bo doc
bi hong thanh "luon tra ve mot hang so" - tuc xanh vi ly do sai.
"""
from __future__ import annotations

import pytest

from llm_gateway import vat_ly

#: Mac dinh llama.cpp dat cho ho `qwen3vl_merger` (ca hai mmproj cua ta deu la
#: ho nay - doc sieu du lieu GGUF 28/09). Khai tuong minh trong yaml ⇒ hai so
#: nay KHONG doi hanh vi; chung chi lam con so ngam thanh con so doc duoc.
SAN_MONG_DOI = 8
TRAN_MONG_DOI = 4096


@pytest.fixture(scope="module")
def ho_so() -> dict:
    return vat_ly.doc_tep(vat_ly.tim_yaml())


def test_yaml_that_khai_hai_co(ho_so):
    """Moi ho so trong yaml DANG DEPLOY phai khai ca san lan tran token anh."""
    assert ho_so, "khong doc duoc ho so nao tu llama-swap.yaml"
    for ten, v in ho_so.items():
        assert v.token_anh_toi_thieu is not None, (
            f"ho so `{ten}` khong khai `--image-min-tokens` -> chi phi token cua "
            f"mot anh lai thanh con so NGAM, va may A khong the dat cho dung")
        assert v.token_anh_toi_da is not None, (
            f"ho so `{ten}` khong khai `--image-max-tokens`")


def test_hai_so_dung_bang_mac_dinh_engine(ho_so):
    """Khai tuong minh phai khai DUNG thu dang chay - khong tien tay doi hanh vi.

    🔴 Doi mot trong hai so nay la mot DANH DOI SAN PHAM (do chinh xac doi lay KV
       + credit khach tra), khong phai mot viec don dep. San 8 la mot no chat
       luong da biet: clip.cpp:1662-1667 canh bao Qwen-VL can >= 1.024 token anh
       cho tac vu dinh vi (issue #16842). Tra no ay can phep do D-5 va mot quyet
       dinh cua chu du an - xem
       `docs/superpowers/specs/2026-09-28-vision-plan-lock.md` muc C1.
    """
    for ten, v in ho_so.items():
        assert v.token_anh_toi_thieu == SAN_MONG_DOI, (
            f"ho so `{ten}` khai san {v.token_anh_toi_thieu}, mong doi "
            f"{SAN_MONG_DOI}. Doi san la doi CHAT LUONG DOC ANH va gia tien - "
            f"phai qua D-5 va chu du an, khong sua o day cho test xanh")
        assert v.token_anh_toi_da == TRAN_MONG_DOI, (
            f"ho so `{ten}` khai tran {v.token_anh_toi_da}, mong doi "
            f"{TRAN_MONG_DOI}")


def test_bo_doc_thay_duoc_khi_co_VA_khi_khong():
    """⭐ Phep TIEM NGHICH: bo doc phai phan biet duoc co/khong, khong tra hang so."""
    khung = (
        "macros:\n"
        "  CHUNG: >-\n"
        "    -fa 1 -ngl 999 -kvu\n"
        "{them}"
        "models:\n"
        "  thu-api:\n"
        "    cmd: |\n"
        "      llama-server.exe\n"
        "      ${{CHUNG}}\n"
        "      -c 131072\n"
        "      -np 2\n")

    khong = vat_ly.doc_van_ban(khung.format(them=""))["thu-api"]
    assert khong.token_anh_toi_thieu is None, "yaml KHONG khai co ma bo doc van tra so"
    assert khong.token_anh_toi_da is None
    assert khong.ctx == 131_072 and khong.np == 2, "phan con lai phai doc duoc nhu cu"

    co = vat_ly.doc_van_ban(
        khung.format(them="    --image-min-tokens 64 --image-max-tokens 2048\n"))["thu-api"]
    assert co.token_anh_toi_thieu == 64, "bo doc khong lay so tu macro CHUNG"
    assert co.token_anh_toi_da == 2048


def test_co_khai_trong_ho_so_thang_macro():
    """llama.cpp: co khai SAU thang. Bo doc phai theo dung luat ay.

    Quan trong vi `CHUNG` duoc chen TRUOC phan rieng cua tung ho so: mot ho so
    muon khac dan phai de len duoc, neu khong thi "khai tuong minh" tro thanh
    "khai mot lan cho tat ca" va khong ai de y.
    """
    v = vat_ly.doc_van_ban(
        "macros:\n"
        "  CHUNG: >-\n"
        "    --image-min-tokens 8 --image-max-tokens 4096\n"
        "models:\n"
        "  thu-api:\n"
        "    cmd: |\n"
        "      llama-server.exe\n"
        "      ${CHUNG}\n"
        "      --image-min-tokens 1024\n"
        "      -c 131072\n"
        "      -np 2\n")["thu-api"]
    assert v.token_anh_toi_thieu == 1024, "ho so de len macro ma bo doc khong thay"
    assert v.token_anh_toi_da == 4096, "co khong bi de len phai giu nguyen"
