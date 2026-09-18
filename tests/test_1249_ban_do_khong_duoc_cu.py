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


# ---------------------------------------------------------------------------
# Lo 8 (don tai lieu 18/09): TEN DA GO khong duoc moc lai
#
# Ban do (va cac tai lieu song canh no) tung noi sai vi mot ten da go o L-23
# (`SO_SLOT_MAY_B`, `LTT_LLM_MAX_DONG_THOI`, ...) van nam lai trong mot doan van
# ma khong ai danh dau. `tools/check_ten_da_go.py` giu MOT bang ten da go va
# chot TAP HOP dong vi pham hom nay (banh coc): chi do khi co dong MOI.
# ---------------------------------------------------------------------------
import importlib.util
import subprocess
import sys


def _cong_cu():
    duong = GOC / "tools" / "check_ten_da_go.py"
    spec = importlib.util.spec_from_file_location("check_ten_da_go", duong)
    mod = importlib.util.module_from_spec(spec)
    # `@dataclass` tra lop qua `sys.modules[__module__]` - phai dang ky truoc.
    sys.modules.setdefault("check_ten_da_go", mod)
    spec.loader.exec_module(sys.modules["check_ten_da_go"])
    return sys.modules["check_ten_da_go"]


def test_ten_da_go_kho_hien_tai_xanh():
    """Chay dung nhu gate chay (khong doi so): kho hom nay phai xanh."""
    ra = subprocess.run([sys.executable, "tools/check_ten_da_go.py"], cwd=GOC,
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=120)
    assert ra.returncode == 0, ra.stdout + ra.stderr


def test_ten_da_go_DOI_CHUNG_tiem_mot_dong_cu_thi_DO():
    """🔴 Doi chung: khong co ve nay thi mot bo do luon-xanh cung qua duoc."""
    cc = _cong_cu()
    van = (GOC / "CLAUDE.md").read_text(encoding="utf-8")
    moc = cc.doc_moc()
    assert not cc.so_voi_moc(cc.quet_van_ban("CLAUDE.md", van), moc)

    tiem = van + "\nSo suat doc tu `ngan_sach.SO_SLOT_MAY_B` (mac dinh 3).\n"
    moi = cc.so_voi_moc(cc.quet_van_ban("CLAUDE.md", tiem), moc)
    assert moi and any("SO_SLOT_MAY_B" in k for k in moi), moi


def test_dong_danh_dau_DA_GO_va_ba_dong_sau_duoc_mien():
    cc = _cong_cu()
    van = "\n".join([
        "⛔ **ĐÃ GỠ (L-23)** — tên cũ:",
        "`SO_SLOT_MAY_B`, `POOL_KV_MAY_B`",
        "",
        "env `LTT_LLM_MAX_DONG_THOI`",
        "dong dem",
        "Con dung `LTT_LLM_RPM` o day.",
    ])
    hit = cc.quet_van_ban("docs/x.md", van)
    assert [h.ten for h in hit] == ["LTT_LLM_RPM"], hit


def test_banh_coc_HOAN_DOI_mot_doi_mot_van_do():
    """Chot TAP HOP, khong chot SO LUONG: xoa mot dong cu + them mot dong moi
    thi tong khong doi ma van phai do."""
    cc = _cong_cu()
    # Moc TONG HOP, khong doc moc that: 18/09 moc that da ve 0 dong (don het),
    # ma tinh chat "chot tap hop" khong phu thuoc noi dung moc.
    moc = {cc.Hit("AGENTS.md", "LE", "`LE` cu").khoa(),
           cc.Hit("CLAUDE.md", "POOL_KV", "`POOL_KV_MAY_B` cu").khoa()}
    bo_mot = sorted(moc)[1:]
    hit = [cc.Hit("CLAUDE.md", "SO_SLOT", "`SO_SLOT` moi them")]
    moi = cc.so_voi_moc(hit, set(bo_mot))
    assert moi and len(bo_mot) + len(hit) == len(moc)


def test_moi_ten_trong_bang_deu_bat_duoc():
    """Tu kiem cua bo do: moi ten co mau xau bi bat, mau tot khong bi bat."""
    cc = _cong_cu()
    assert cc.tu_kiem() == 0


def test_buoc_gate_dang_ky_canh_luat_van_hanh():
    """Chay o L1/L2/L3: la mot buoc TINH trong `_steps()` cua gate, ngay sau
    buoc "luat van hanh"."""
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    dau = ma.index("def _steps(")
    het = ma.index("\ndef ", dau + 1)
    than = ma[dau:het]
    a = than.index('"tools/check_luat_van_hanh.py"')
    b = than.index('"tools/check_ten_da_go.py"')
    assert 0 < b - a < 3000, "buoc ten da go phai dang ky canh luat van hanh"
