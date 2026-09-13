"""test_1249 — `BAN_DO_DUONG_DI.md` khong duoc phep noi sai.

## Vi sao mot BAN DO can phep kiem

`CLAUDE.md` ghi ro: bang chep tay o kho nay **da noi sai NAM lan, ca nam deu ve
phia nguy hiem**. Mot tep tai lieu khong co cach nao tu biet no da cu.

⇒ Ban do chi duoc phep song neu moi dieu no khai deu doi chieu duoc voi MA. Ba
  ve duoi day doi chieu ba loai khai: **duong dan**, **con so**, **cau truc**.

⛔ Ve nay KHONG doc van xuoi. No chi doc nhung thu co the SAI mot cach nguy
   hiem. Bat mot tai lieu phai khop tung chu la bien no thanh tep khong ai dam
   sua — va mot tai lieu khong ai dam sua cung la mot tai lieu cu.
"""
import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[1]
BAN_DO = GOC / "docs" / "ltt_llm_dual" / "BAN_DO_DUONG_DI.md"


def test_ban_do_ton_tai():
    assert BAN_DO.is_file(), (
        f"khong thay {BAN_DO.relative_to(GOC)} — ban do la diem vao de TRA duong "
        "LLM; mat no thi nguoi sau lai doc ma tu cho co loi tro ra, dung cach da "
        "de ra ba ban va hong cua L-08.")


def test_moi_DUONG_DAN_trong_ban_do_deu_co_that():
    """Mot con tro chet con te hon khong co con tro: no dan di va dan sai."""
    van = BAN_DO.read_text(encoding="utf-8")
    # Chi lay nhung chuoi TRONG dau nhay nguoc trong ro rang la duong dan tep.
    ung_vien = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|md))`", van))
    thieu = []
    for d in sorted(ung_vien):
        if "/" not in d:          # ten tep tran (vd `manifest.py`) — bo qua
            continue
        if d.startswith("starlette/"):   # thu vien ben ngoai, khong o kho nay
            continue
        if not (GOC / d).exists():
            thieu.append(d)
    assert not thieu, f"ban do tro toi tep KHONG TON TAI: {thieu}"


def test_bon_con_so_khop_BAN_KHAI_chu_khong_phai_chep_tay():
    """🔴 Ve quan trong nhat.

    Ban do in bang suat/pool. Neu `ngan_sach.py` doi ma bang khong doi, ban do
    thanh cai bang thu sau noi sai. Ve nay doc ban khai THAT roi doi chieu.
    """
    from platform_core.runtime_noi_bo.luong import tim_tool

    _m, tool = tim_tool("text.chat")
    van = BAN_DO.read_text(encoding="utf-8")

    for model in ("ltt-3.8", "ltt-3.5"):
        suc = tool.admission_cho(model)
        assert suc is not None, (
            f"{model} khong con khai admission ⇒ no se roi vao nhanh khong duoc "
            "bao ve. Cua stream nay TU CHOI phuc vu model nhu the (co y).")
        dong = next((d for d in van.splitlines()
                     if d.lstrip().startswith(f"| `{model}`")), None)
        assert dong is not None, f"ban do khong con dong cho {model}"
        assert str(suc.resource) in dong, (
            f"ban do ghi tai nguyen sai cho {model}: ban khai noi "
            f"{suc.resource!r}, ban do ghi: {dong.strip()}")
        # So co dau cham phan nghin trong tai lieu ("221.184") — bo dau roi so.
        so_trong_dong = {s.replace(".", "") for s in re.findall(r"[\d.]+", dong)}
        assert str(suc.slots) in so_trong_dong, (
            f"ban do ghi so suat sai cho {model}: ban khai noi {suc.slots}")
        assert str(suc.token_pool) in so_trong_dong, (
            f"ban do ghi pool KV sai cho {model}: ban khai noi {suc.token_pool}")


def test_ban_do_khai_dung_SO_CUA_stream():
    """Cau truc: ban do noi "dung hai" — ma phai dong y."""
    from tests.test_1248_mot_cua_stream_duy_nhat import (_cac_lenh_tra_stream,
                                                         _la_cua_sandbox)

    tat_ca = _cac_lenh_tra_stream()
    that = [g for g in tat_ca if not _la_cua_sandbox(g)]

    assert len(tat_ca) == 2 and len(that) == 1, (
        f"ma co {len(tat_ca)} `return StreamingResponse` ({len(that)} cua that), "
        "nhung ban do §2 khai dung HAI (mot sandbox + mot that). Doi ma thi phai "
        "doi ban do — do la ca diem cua ve nay.")
    # ⛔ DA GO mot ve o day: `assert "hai" in van`. Chu "hai" xuat hien khap
    #    tai lieu (`hai card`, `hai duong`, `hai lop`...) nen no XANH vinh vien
    #    va cho cam giac an toan gia. Ve co nghia la ve `len(tat_ca) == 2` ben
    #    tren — no doc MA, khong doc van xuoi.
