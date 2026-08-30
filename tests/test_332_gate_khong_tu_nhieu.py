"""Cong chat luong khong duoc TU NHIEU vao phep do cua chinh no.

🔴 SU VIEC, 2026-08-29. `tools/gate.py::_chay_theo_lich` nop cung luc `bo test`
va toan bo nhom kiem TINH. Ba tep duoi day bi mot test GHI (roi khoi phuc) trong
khi mot buoc gate khac dang DOC chung:

    docs/PUBLIC_API/CONTRACT_BASELINE.json   <- test_209    -> check_api_compat
    locale/en/LC_MESSAGES/messages.po        <- test_306    -> check_dich_thieu
    sdk/typescript/ltt-public-api.ts         <- test_210    -> check_sdk_contract
    server/templates/vps_dieu_khoan.html     <- test_306    -> (khong buoc nao)

Ba tren ba. Do khong phai trung hop.

⛔ Hai phien mat gan tron mot ngay va lan luot do cho: `__pycache__` cu · mot
   tien trinh thu hai · mot tep ghi thu tu chua tim ra · rac fixture ngau nhien.
   KHONG cai nao dung. Cong cu do tu nhieu vao phep do cua no.

⭐ `TEP_NOI_TIEP` cua `test_nhanh.py` bat ba tep test do chay noi tiep VOI NHAU,
   nen chung khong giam len nhau. Hang rao co that — no chan SAI HUONG: no khong
   noi gi ve nhom kiem tinh cua chinh luot gate do.

Phep kiem nay chot huong con lai: mot buoc gate DOC mot tep trong danh sach thi
phai o nhom `sau_test`.
"""
from __future__ import annotations

import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent


def _gate():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gate_mod", GOC / "tools" / "gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cong_cu_cua(step) -> str:
    """Duong tep cong cu ma mot `Step` chay, hoac chuoi rong."""
    for phan in step.argv:
        if isinstance(phan, str) and phan.startswith("tools/"):
            return phan
    return ""


# ── 1. Danh sach tep phai khop THUC TE ──────────────────────────────────────

def test_moi_tep_trong_danh_sach_deu_co_that_va_test_ghi_no_cung_co_that():
    """Mot danh sach tro vao tep khong ton tai la mot hang rao chan khong khi."""
    gate = _gate()
    thieu = []
    for tep, test in gate.TEP_KHONG_DUOC_DOC_SONG_SONG.items():
        if not (GOC / tep).is_file():
            thieu.append(tep)
        if not (GOC / test).is_file():
            thieu.append(test)
    assert thieu == [], f"danh sach tro vao thu khong co that: {thieu}"


def test_test_duoc_khai_THAT_SU_ghi_vao_tep_do():
    """Chot nguon: test duoc khai phai that su nhac toi tep no ghi.

    Neu mot test thoi ghi tep do thi muc nay thanh thua, va mot danh sach thua
    la mot danh sach roi se sai.
    """
    gate = _gate()
    lech = []
    for tep, test in gate.TEP_KHONG_DUOC_DOC_SONG_SONG.items():
        than = (GOC / test).read_text(encoding="utf-8", errors="replace")
        ten = pathlib.PurePosixPath(tep).name
        if ten not in than:
            lech.append(f"{test} khong nhac toi {ten}")
    assert lech == [], lech


# ── 2. Bat bien chinh ───────────────────────────────────────────────────────

def test_buoc_nao_DOC_tep_bi_ghi_thi_phai_chay_SAU_bo_test():
    """Day la phep kiem lam ca tep nay dang ton tai.

    Mot checker moi doc `messages.po` roi de o nhom `tinh` se tai tao dung loi
    da mat mot ngay — va no se tai tao duoi dang "gate do ngau nhien", tuc dang
    kho lan nhat.
    """
    gate = _gate()
    ten_tep = {pathlib.PurePosixPath(t).name
               for t in gate.TEP_KHONG_DUOC_DOC_SONG_SONG}

    xau = []
    for step in gate._steps(quick=False):
        if step.nhom == "nang":
            # `bo test` la BEN GHI, khong phai ben doc xung dot. No nhac ba tep
            # do vi `TEP_NOI_TIEP` liet ke chung — va chinh no lo viec cac test
            # trong no khong giam len nhau. Doi hoi no o `sau_test` la doi no
            # chay sau chinh no.
            continue
        cong_cu = _cong_cu_cua(step)
        if not cong_cu or not (GOC / cong_cu).is_file():
            continue
        than = (GOC / cong_cu).read_text(encoding="utf-8", errors="replace")
        cham = sorted(t for t in ten_tep if t in than)
        if cham and step.nhom != "sau_test":
            xau.append(f"{step.name!r} ({cong_cu}) doc {cham} nhung o nhom "
                       f"{step.nhom!r}, phai la 'sau_test'")
    assert xau == [], "\n".join(xau)


def test_nhom_sau_test_KHONG_chay_song_song_voi_bo_test():
    """Chot o tang lich chay, khong chi o tang nhan.

    Nhan `sau_test` chi co nghia neu bo dieu phoi that su hoan chung lai. Phep
    kiem tren chot cai nhan; phep kiem nay chot cai lich.
    """
    import inspect

    gate = _gate()
    than = inspect.getsource(gate._chay_theo_lich)

    # Khoi song song nop `nang` + `nhe`; `sau` phai nam NGOAI khoi do.
    truoc, _, sau_khoi = than.partition("if sau:")
    assert sau_khoi, "khong con nhanh chay rieng cho nhom `sau_test`"
    assert "sau_test" not in truoc.split("with ThreadPoolExecutor")[-1], (
        "nhom `sau_test` bi nop vao cung khoi song song voi `bo test`")


def test_bon_buoc_da_biet_deu_o_nhom_sau_test():
    """Banh coc cu the: bon buoc nay da tung gay do gia, khong duoc quay lai."""
    gate = _gate()
    nhom = {s.name: s.nhom for s in gate._steps(quick=False)}
    for ten in ("hop dong API", "dich thieu ban EN", "SDK khop hop dong",
                "postman"):
        assert nhom.get(ten) == "sau_test", (
            f"{ten!r} dang o nhom {nhom.get(ten)!r}")


# ── 3. Khong lam hong nhung thu khac ────────────────────────────────────────

@pytest.mark.parametrize("ten", ["bien dich duoc", "bo test (song song)"])
def test_khong_doi_nhom_cua_hai_buoc_neo(ten):
    """`cong` van chay mot minh truoc; `bo test` van la viec nang chay truoc."""
    gate = _gate()
    nhom = {s.name: s.nhom for s in gate._steps(quick=False)}
    assert nhom[ten] in ("cong", "nang"), f"{ten} -> {nhom[ten]}"


# ── Thu hồi xác tiến trình (30/08) ────────────────────────────────────────

def test_gate_DON_XAC_tien_trinh_truoc_khi_do():
    """🔴 Đo 30/08: 282 tiến trình con mồ côi, cũ nhất **55 giờ**.

    Chúng giữ 9,5 GB RAM và **khoá 85 GB temp** — 154/158 thư mục pytest không
    xoá được. Lúc đó ổ C: còn **9,4 GB / 930 GB**, và Postgres của production
    nằm trên C:. Đầy thì Postgres từ chối ghi, và triệu chứng sẽ **không nói
    "hết đĩa"** — nó hiện ra thành job hỏng ngẫu nhiên hoặc `/health/ready` 503.

    ⭐ `test_214` dọn đúng rồi (`join` → `terminate` → `join`). Rò rỉ chỉ xảy ra
       khi tiến trình **cha** bị giết giữa chừng, và không có cách nào bắt một
       tiến trình bị SIGKILL dọn dẹp sau nó.

    ⇒ Nên mục tiêu không phải NGĂN mà là **TỰ LÀNH**: dọn xác cũ trước mỗi lượt.
    """
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "don_tien_trinh_mo_coi.py" in ma, (
        "gate khong con don xac tien trinh truoc khi do — ro ri se tich lai "
        "toi khi day o dia production")
    # Va no phai chay TRUOC danh sach buoc, khong phai sau.
    assert ma.index("don_tien_trinh_mo_coi.py") < ma.index("steps: list[Step]")


def test_cong_cu_don_xac_KHONG_dung_toi_production():
    """Ba thứ nó không bao giờ được chạm, dù mọi điều kiện khác đều khớp."""
    ma = (GOC / "tools" / "don_tien_trinh_mo_coi.py").read_text(encoding="utf-8")
    assert 'CAM = ("c:\\lttplatform\\\\",)' in ma.replace("'", '"') or \
           "lttplatform" in ma.lower(), "khong con chan duong production"
    # Phai doi DU ba dieu kien — thieu mot la co rui ro giet nham.
    for dieu_kien in ("multiprocessing.spawn", "create_time", "python313"):
        assert dieu_kien in ma.lower(), f"thieu dieu kien: {dieu_kien}"
    # Mac dinh la CHI XEM. Mot cong cu giet tien trinh khong duoc mac dinh giet.
    assert '"--giet"' in ma and "action=\"store_true\"" in ma
