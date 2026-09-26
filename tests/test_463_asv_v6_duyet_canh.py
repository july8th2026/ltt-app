"""V6 pha 09 — khach XEM duoc cac canh, va khong sua duoc chung.

## Vi sao pha nay ton tai

Chuoi ASV tach canh bang ffmpeg, roi goi model doc **tung canh** — mot buoc co
tinh tien — roi quyet dinh bo canh nao. Truoc pha 09, `quan_sat.py` khong co mot
dong nao ve canh va `asv_chi_tiet.html` khong hien mot chu nao: khach **tra tien
cho mot quyet dinh ho khong duoc xem**.

## Hai cau hoi tach nhau, va cau thu hai moi kho

  §1  bang ke co DUNG khong          — so canh, giu/cat, %% tren dai
  §2  no co RO RI thu khong duoc ro ri khong

§2 la phan de sai nhat. `ban_bien_tap` ghi `ly_do` cho **nguoi van hanh**:

    "VLM de xuat bo (tin 0.91 >= nguong 0.85, canh co loi thoai)"

Mot cau mang ten mot he con, mot con so nguong va mot tu viet tat. Dua thang no
ra man khach la vi pham `routes.py` muc 2 va nhom D cua `test_447`.

## ⛔ Du lieu o day dung TU MA SAN PHAM, khong go tay

`ChiMucCanh`, `lap_ban`, `sang_dict` deu la ban that. Mot artefact go tay se
kiem chinh tri tuong tuong cua toi ve dinh dang, chu khong kiem dinh dang.
"""
from __future__ import annotations

import io
import json

import pytest

from apps.auto_scan_video import ban_bien_tap as bbt
from apps.auto_scan_video import canh as canh_mod
from apps.auto_scan_video import hieu_canh as hc
from apps.auto_scan_video import hop_dong_v4, pipeline, quan_sat

from tests import test_423_asv_giao_dien as _gd

moi_truong = _gd.moi_truong


CANH = (
    canh_mod.Canh("canh_0001", 0.0, 10.0),
    canh_mod.Canh("canh_0002", 10.0, 20.0),
    canh_mod.Canh("canh_0003", 20.0, 30.0),
    canh_mod.Canh("canh_0004", 30.0, 40.0),
)


def _goi(*, preset=hop_dong_v4.PRESET_CAT_THONG_MINH, bo=("canh_0003",)) -> bytes:
    """Artefact `edit_plan` THAT — dung chinh cac ham san pham dung."""
    ci = canh_mod.ChiMucCanh(CANH, 40.0)
    hieu = tuple(
        hc.HieuCanh(ma_canh=c.ma,
                    de_xuat="bo" if c.ma in bo else "giu",
                    do_tin=0.95 if c.ma in bo else 0.9)
        for c in CANH)
    ban = bbt.lap_ban(preset=preset, chi_muc=ci, hieu_canh=hieu, ban_ghi={})
    from apps.auto_scan_video.giai_doan_ban_bien_tap import _chi_muc_dict

    return json.dumps({"ban": ban.sang_dict(), "chi_muc": _chi_muc_dict(ci)},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")


def _dung_run(db, kho, *, owner: str, goi: bytes):
    """Mot run co giai doan `edit_plan` da xong va mot artefact that trong kho."""
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import AsvRun, AsvStage

    run = AsvRun(id=f"run-{owner}-canh", owner_id=owner, status="done",
                 source_key="v/nguon.mp4",
                 settings={"preset": hop_dong_v4.PRESET_CAT_THONG_MINH})
    db.add(run)
    db.flush()
    khoa = f"staging/{owner}/{run.id}/edit_plan.json"
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")
    # ⭐ `owner_id` cung o TANG GIAI DOAN, khong chi o run: bang chot NOT NULL,
    #    va do la I6 duoc cuong che them mot lop nua o CSDL.
    db.add(AsvStage(run_id=run.id, owner_id=owner, stage=pipeline.EDIT_PLAN,
                    status="succeeded", outputs={"khoa_asset": [khoa]}))
    db.commit()
    assert features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN) is not None
    return run


@pytest.fixture()
def moi_truong_canh(moi_truong):
    """`moi_truong` cua `test_423`, kem mot run co ban bien tap that."""
    import platform_core.db as dbmod
    from platform_core.storage import get_storage

    app, a, csrf_a, b, csrf_b = moi_truong
    db = next(dbmod.get_session())
    try:
        from platform_core.models import User
        from sqlalchemy import select
        uid = db.scalar(select(User.id).where(User.email == "asv-a@example.com"))
        run = _dung_run(db, get_storage(), owner=uid, goi=_goi())
        yield app, a, csrf_a, b, csrf_b, run.id, uid
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Bang ke co dung khong
# ══════════════════════════════════════════════════════════════════════════════

def test_dong_canh_dem_dung_giu_va_cat(moi_truong_canh):
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun

    *_, run_id, _uid = moi_truong_canh
    db = next(dbmod.get_session())
    try:
        d = quan_sat.dong_canh(db, get_storage(), db.get(AsvRun, run_id))
    finally:
        db.close()
    assert d is not None
    assert (d["so_canh"], d["so_giu"], d["so_cat"]) == (4, 3, 1)
    assert d["thoi_luong"] == 40.0
    assert d["giu_giay"] == 30.0


def test_moc_phan_tram_KHOP_moc_giay(moi_truong_canh):
    """⭐ Phan tram tinh o MAY CHU, khong o template: mot phep chia trong Jinja
    la mot ban thu hai cua mot quy tac hinh hoc."""
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun

    *_, run_id, _uid = moi_truong_canh
    db = next(dbmod.get_session())
    try:
        d = quan_sat.dong_canh(db, get_storage(), db.get(AsvRun, run_id))
    finally:
        db.close()
    for c in d["canh"]:
        assert abs(c["bat_pt"] - 100.0 * c["bat"] / 40.0) < 1e-6
    assert [c["bat_pt"] for c in d["canh"]] == [0.0, 25.0, 50.0, 75.0]


def test_canh_QUA_NGAN_van_co_be_rong_ve_duoc():
    """🔴 Mot canh 0,4 giay trong mot video 30 phut ra 0,02% — tuc KHONG mot
    diem anh nao. Khach dem duoc muoi canh trong danh sach ma chi thay chin
    vach, va khong co cach nao doan la vi sao."""
    assert quan_sat.SAN_BE_RONG_PT > 0


def test_chua_xong_edit_plan_thi_tra_None(moi_truong):
    """Man hinh khi do khong hien khoi nay, chu khong hien mot khoi RONG."""
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun

    db = next(dbmod.get_session())
    try:
        run = AsvRun(id="run-chua-xong", owner_id="uX", status="running",
                     source_key="v/x.mp4", settings={})
        db.add(run)
        db.commit()
        assert quan_sat.dong_canh(db, get_storage(), run) is None
    finally:
        db.close()


def test_artefact_hong_KHONG_lam_vo_trang(moi_truong):
    """⛔ Nuot loi CO CHU DICH, va chi o day: mot artefact khong doc duoc khong
    duoc lam vo trang ket qua cua mot lan chay DA XONG. Khach van tai duoc
    video; ho chi khong thay bang ke canh."""
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun, AsvStage

    db = next(dbmod.get_session())
    kho = get_storage()
    try:
        run = AsvRun(id="run-hong", owner_id="uY", status="done",
                     source_key="v/y.mp4", settings={})
        db.add(run)
        db.flush()
        khoa = "staging/uY/run-hong/edit_plan.json"
        kho.put(khoa, io.BytesIO(b"{khong phai json"), content_type="application/json")
        db.add(AsvStage(run_id=run.id, owner_id="uY", stage=pipeline.EDIT_PLAN,
                        status="succeeded", outputs={"khoa_asset": [khoa]}))
        db.commit()
        assert quan_sat.dong_canh(db, kho, run) is None
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Khong ro ri — phan de sai nhat
# ══════════════════════════════════════════════════════════════════════════════

def test_dong_canh_KHONG_tra_ly_do_ky_thuat(moi_truong_canh):
    """🔑 `ly_do` cua mot canh bi cat co dang:

        "VLM de xuat bo (tin 0.95 >= nguong 0.65)"

    Ba thu bi cam cung mot luc: ten mot he con, mot con so nguong, mot tu viet
    tat. Bai nay chot rang **khong truong nao** cua ban tra ve mang chuoi do —
    khong phai chot rang template khong in no ra.
    """
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun

    *_, run_id, _uid = moi_truong_canh
    db = next(dbmod.get_session())
    try:
        d = quan_sat.dong_canh(db, get_storage(), db.get(AsvRun, run_id))
    finally:
        db.close()
    # ⛔ Chan XANH-RONG truoc da. Doi chung 10/09 cho thay bai nay VAN XANH
    #    khi `dong_canh` tra `None` — `json.dumps(None)` khong ro ri gi ca,
    #    va mot bai "khong tim thay tu cam" tren mot tap rong thi luon xanh.
    assert d is not None and d["so_canh"] == 4, "khong co gi de soi ro ri"
    van = json.dumps(d, ensure_ascii=False)
    for cam in ("VLM", "nguong", "de_xuat", "ly_do", "bang_chung", "do_tin"):
        assert cam not in van, f"bang ke ro ri {cam!r}"


def test_ban_bien_tap_THAT_SU_co_ly_do_ky_thuat():
    """⛔ Doi chung cho bai tren. Neu `ly_do` von da rong thi bai kia xanh ma
    khong chung minh gi — dung cai bay "khong doi chung thi so 0 khong phai mot
    phat hien"."""
    ci = canh_mod.ChiMucCanh(CANH, 40.0)
    hieu = (hc.HieuCanh(ma_canh="canh_0003", de_xuat="bo", do_tin=0.95),)
    ban = bbt.lap_ban(preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
                      chi_muc=ci, hieu_canh=hieu, ban_ghi={})
    ly_do = " ".join(q.ly_do for q in ban.quyet_dinh)
    assert "VLM" in ly_do and "nguong" in ly_do


def test_TRANG_hien_bang_ke_va_KHONG_ro_ri(moi_truong_canh):
    """Cau hoi thu hai: co ai DANG di tren duong khong. HTTP that, HTML that."""
    _app, a, _csrf, _b, _cb, run_id, _uid = moi_truong_canh
    r = a.get(f"/auto-scan-video/run/{run_id}")
    assert r.status_code == 200, r.text[:400]
    van = r.text
    assert "asv-canh-thanh" in van, "khong thay dai canh"
    assert van.count("asv-canh-vach") == 4, "so vach khong bang so canh"
    for cam in ("VLM", "nguong", "canh_0003", "de_xuat"):
        assert cam not in van, f"trang ro ri {cam!r}"


def test_TRANG_khong_co_o_chon_nao_cho_canh(moi_truong_canh):
    """⛔ CHI XEM. Mot `<input>` trong khoi canh la buoc dau tien cua cai do thi
    ma `MVP_CONTRACT` muc 5 cam — va mot khi no co mat, viec go no ra la mot lan
    lay di thu khach da thay."""
    _app, a, _csrf, _b, _cb, run_id, _uid = moi_truong_canh
    van = a.get(f"/auto-scan-video/run/{run_id}").text
    khoi = van.split('class="asv-canh"', 1)[1].split("</section>", 1)[0]
    for cam in ("<input", "<select", "<button", "draggable"):
        assert cam not in khoi, f"khoi canh co {cam!r} — no phai la CHI XEM"


def test_nguoi_KHAC_khong_xem_duoc_bang_ke(moi_truong_canh):
    """I6: loc theo chu so huu o TANG DICH VU. Bang ke canh khong duoc mo mot
    duong vong quanh no."""
    _app, _a, _csrf, b, _cb, run_id, _uid = moi_truong_canh
    r = b.get(f"/auto-scan-video/run/{run_id}")
    assert r.status_code in (403, 404), r.status_code


def test_HOAN_CAT_duoc_noi_ra_o_cap_ban(moi_truong):
    """⭐ `_ap_chinh_sach_an_toan` hoan bot lenh cat de dat san giu lai 50%%. No
    lat `thao_tac` ve GIU nhung giu nguyen `do_tin` va `bang_chung`, nen mot canh
    duoc hoan **khong phan biet duoc** voi mot canh duoc giu ngay tu dau.

    ⛔ Cach "sua" hien nhien — do chuoi `ly_do` xem co chua "hoan cat" — chinh la
       thu §2 vua cam. Nen hom nay su that duoc noi o CAP BAN, va bai nay chot
       rang no CO duoc noi ra chu khong bien mat.
    """
    import platform_core.db as dbmod
    from platform_core.storage import get_storage
    from apps.auto_scan_video.tables import AsvRun

    # Bo GAN HET -> chinh sach an toan phai hoan lai mot so.
    goi = _goi(bo=tuple(c.ma for c in CANH[:3]))
    db = next(dbmod.get_session())
    try:
        run = _dung_run(db, get_storage(), owner="uZ", goi=goi)
        d = quan_sat.dong_canh(db, get_storage(), db.get(AsvRun, run.id))
    finally:
        db.close()
    assert d["da_hoan_cat"] >= 1, (
        "bo 3/4 canh ma khong hoan lai lenh cat nao — doi chung hong, "
        "bai nay khong con do duoc gi")
    assert d["so_giu"] >= 2


def test_463_ly_do_KHAI_DUNG_xuat_xu_cua_con_so(monkeypatch):
    """🔴 **Lý do đi vào artifact của KHÁCH, nên nó ⛔ không được khai sai xuất xứ.**

    `do_tin` là một **hợp đồng duck-type** dùng chung bởi hai đại lượng **khác bản
    chất**: tỉ lệ đo bằng **ffmpeg** (`BangChungCanh`, từ Task 10) và **độ tin của
    VLM** (`hieu_canh.HieuCanh`). Bản trước ghi cứng *"VLM đề xuất bỏ"* cho **mọi**
    quyết định.

    🔴 Và từ Task 22 thì `hieu_canh.doc_hieu_canh` đã bị xoá, ⛔ **không** mã sản
       phẩm nào còn dựng `HieuCanh` ⇒ câu *"VLM"* ấy **luôn sai** trên mọi lượt chạy
       thật, suốt từ đó tới 27/09.

    ⚠️ Và bài kiểm cũ `..._co_ly_do_ky_thuat` chốt `"VLM" in ly_do` — một bánh cóc đo
       **CÁCH GÕ** thay vì tính chất, và ở đây nó **bảo vệ một lời khai sai**. Nó vẫn
       đúng cho `HieuCanh`; bài này chốt **chiều còn lại**, chiều mà đường sống đi qua.
    """
    from apps.auto_scan_video import ban_bien_tap as bb
    from apps.auto_scan_video.giai_doan_ban_bien_tap import BangChungCanh

    class _Canh:
        ma = "canh_0001"

    bc = BangChungCanh(ma_canh="canh_0001", de_xuat="bo", do_tin=0.95,
                       **{})
    qd = bb._quyet_dinh_mot_canh(_Canh(), bc, co_thoai=False)

    assert qd.thao_tac == bb.THAO_TAC_CAT, qd
    assert "ffmpeg" in qd.ly_do, (
        f"ly do ⛔ khong goi ten phep do THAT: {qd.ly_do!r}")
    assert "VLM" not in qd.ly_do, (
        f"bang chung la phep do ffmpeg ma ly do khai la VLM: {qd.ly_do!r}")


def test_463_nguon_LA_cua_doi_tuong_chu_khong_phai_mac_dinh_VLM():
    """⭐ Một nguồn **thứ ba** (hay một bản giả trong test) ⛔ không được bị khai là
       VLM chỉ vì nó **im lặng** về xuất xứ.

    Đây là vế đối chứng: nếu `_nguon_cua` có mặc định là `"VLM"` thì bài trên vẫn
    xanh cho `BangChungCanh` (lớp đó khai ffmpeg) mà lỗi vẫn còn cho mọi thứ khác.
    """
    from apps.auto_scan_video import ban_bien_tap as bb

    class _Canh:
        ma = "canh_0002"

    class _La:            # ⛔ khong khai NGUON_BANG_CHUNG
        ma_canh = "canh_0002"
        de_xuat = "bo"
        do_tin = 0.99

    qd = bb._quyet_dinh_mot_canh(_Canh(), _La(), co_thoai=False)
    assert "VLM" not in qd.ly_do, (
        f"nguon im lang bi khai la VLM: {qd.ly_do!r}")
