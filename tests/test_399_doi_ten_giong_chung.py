"""Đổi tên hiển thị kho giọng chung — và thứ TUYỆT ĐỐI không được đổi theo.

## Vì sao đổi tên

25 giọng trong kho chung mang tên đặt theo **kênh** (`kinhte`, `lichsu`,
`phatgiao`, `tamlyhoc`, `hoathinh`, `bietdoi`, `lego`) hoặc theo **tên nhân
viên** (`Khánh`, `Lâm`, `Quân`, `Hương KT`, `Nguyệt Nga`). Tên kênh rò danh mục
kinh doanh cho mọi khách đọc; tên nhân viên gắn một con người cụ thể vào **dữ
liệu sinh trắc của chính họ**, bày ra trong một bộ chọn công khai.

## 🔴 ĐIỀU ĐƯỢC CHỐT CHẶT NHẤT Ở ĐÂY

⛔ **`public_id` KHÔNG ĐƯỢC ĐỔI.** Nó là hợp đồng API: khách đang gọi
   `voice_id="vc_…"` trong mã nguồn của họ. Một lượt "dọn dẹp danh mục" mà đụng
   vào nó là một lượt làm hỏng mã của khách — và hỏng ở chỗ họ không sửa được,
   vì họ không biết id mới.

⭐ Cột ấy tách khỏi `ten_hien_thi` từ ngày bảng được dựng, nên đổi tên vốn đã an
   toàn. Phép kiểm này tồn tại để giữ nó **vẫn** an toàn: một bản vá sau này
   "chuẩn hoá id theo tên" sẽ đỏ ở đây.

⚠️ Và điều đó KHÔNG đúng với **giọng mẫu** (`giong_mau.py`), nơi `ma` vừa là
   khoá engine, vừa là `public_id`, vừa là tên hiển thị. Đừng đọc tệp này thành
   "đổi tên giọng nào cũng rẻ".
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap_cong_cu():
    """Nạp công cụ như một module rời.

    ⛔ `tools/` không phải một package, và `import tools.x` kéo theo `sys.path`
       của cả cây. Nạp theo đường dẫn thì phép kiểm không phụ thuộc chỗ nó chạy.
    """
    p = GOC / "tools" / "doi_ten_giong_chung.py"
    spec = importlib.util.spec_from_file_location("_doi_ten", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ten.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _dung_kho(db, mod):
    """Dựng đúng 25 hàng dùng chung: tên CŨ + `ghi_chu` mang `ma_cu`."""
    import json

    from apps.ltt_voice.tables import VoiceProfile
    ra = []
    for i, (ma, (cu, _moi)) in enumerate(mod.DOI_TEN.items()):
        h = VoiceProfile(public_id=f"vc_{i:032x}", owner_id="nen-tang",
                         ten_hien_thi=cu, ngon_ngu="vi",
                         ghi_chu=json.dumps({"nguon": "Voiceclone_TTS",
                                             "ma_cu": ma}),
                         trang_thai="active", dung_chung=True)
        db.add(h)
        ra.append(h)
    db.commit()
    return ra


# ── Bảng đổi tên tự nó phải nhất quán ──────────────────────────────────────

def test_ten_moi_doi_mot_khac_nhau():
    """⛔ `uq_voice_owner_ten` — hai tên mới trùng nhau là một lượt đổi DỪNG
    GIỮA CHỪNG, để lại nửa kho tên cũ nửa kho tên mới và không bút toán nào nói
    cái nào đã xong."""
    mod = _nap_cong_cu()
    moi = [v[1] for v in mod.DOI_TEN.values()]
    trung = sorted({t for t in moi if moi.count(t) > 1})
    assert not trung, f"ten moi trung nhau: {trung}"


def test_ten_moi_khong_trung_giong_mau_engine():
    """20 giọng mẫu đứng CẠNH 25 giọng này trong cùng một bộ chọn.

    ⚠️ Ràng buộc CSDL **không** bắt được ca này — giọng mẫu không có hàng nào
       trong `voice_profile`. Nên nếu không có phép kiểm ở đây thì hai giọng
       cùng tên sẽ hiện ra cạnh nhau và khách chọn nhầm, im lặng.
    """
    from apps.ltt_voice import giong_mau
    mod = _nap_cong_cu()
    cham = sorted({v[1] for v in mod.DOI_TEN.values()}
                  & {g.ma for g in giong_mau.DANH_SACH})
    assert not cham, f"ten moi trung giong mau: {cham}"


def test_ten_moi_khong_con_ten_kenh_hay_nhan_vien():
    """Toàn bộ lý do của lượt đổi này.

    ⛔ Nếu một tên kênh sống sót thì lượt đổi **không đạt mục đích** — và nó sẽ
       trông như đã đạt, vì 24 tên kia đều mới.
    """
    mod = _nap_cong_cu()
    cam = ["Kinh Tế", "Lịch Sử", "Phật Giáo", "Tâm Lý Học", "Hoạt Hình",
           "Biệt Đội", "Lego", "CG Hương", "HT3D", "QTrungg", "Mèo Quàn",
           "Mèo Đang", "Khánh", "Hương KT", "Ninh Đôn", "Nguyệt Nga", "Kỳ An"]
    xau = [v[1] for v in mod.DOI_TEN.values() if any(c in v[1] for c in cam)]
    assert not xau, f"ten moi con mang ten kenh/nhan vien: {xau}"


# ── Hành vi khi áp ─────────────────────────────────────────────────────────

def test_ap_doi_ten_va_GIU_NGUYEN_public_id(db):
    """🔴 Phép kiểm quan trọng nhất tệp này.

    `public_id` là thứ khách đã dán vào mã nguồn của họ. Đổi nó là làm hỏng mã
    của khách ở chỗ họ không sửa được, vì họ không biết id mới.
    """
    mod = _nap_cong_cu()
    hang = _dung_kho(db, mod)
    truoc = {h.public_id: h.ten_hien_thi for h in hang}

    assert mod.main(["--ap"]) == 0

    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    # ⛔ `expire_all` BẮT BUỘC, và thiếu nó là một phép kiểm XANH GIẢ theo chiều
    #    ngược lại. Công cụ mở **phiên riêng** (`get_session()`) và commit ở đó;
    #    phiên của fixture vẫn giữ các đối tượng cũ trong identity map, nên nó
    #    đọc ra tên CŨ dù CSDL đã đổi. Bản đầu của phép kiểm này đỏ vì lý do ấy
    #    — may là nó đỏ; một phép kiểm khẳng định "không đổi" mà quên `expire`
    #    thì sẽ XANH mãi mãi và không bao giờ đo gì.
    db.expire_all()
    sau = {h.public_id: h.ten_hien_thi
           for h in db.execute(select(VoiceProfile)).scalars()}

    assert set(sau) == set(truoc), (
        "public_id DA DOI. No la hop dong API — khach dang goi voice_id='vc_…' "
        "trong ma nguon cua ho.")
    cho_moi = {cu: moi for cu, moi in mod.DOI_TEN.values()}
    for pid, ten_cu in truoc.items():
        assert sau[pid] == cho_moi[ten_cu], f"{pid} doi sai ten"


def test_khong_dong_vao_giong_KHONG_dung_chung(db):
    """Giọng riêng của khách phải nguyên vẹn.

    ⛔ Một lượt đổi tên quét cả bảng sẽ đổi tên giọng **của khách** — dữ liệu
       của họ, đặt tên bởi họ. Bộ lọc `dung_chung` là thứ duy nhất chặn điều đó,
       nên nó phải có phép kiểm riêng chứ không nằm nhờ trong phép kiểm khác.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    mod = _nap_cong_cu()
    _dung_kho(db, mod)
    rieng = VoiceProfile(public_id="vc_" + "f" * 32, owner_id="khach-that",
                         ten_hien_thi="Lily — nữ, tự nhiên", ngon_ngu="vi",
                         trang_thai="active", dung_chung=False)
    db.add(rieng)
    db.commit()

    assert mod.main(["--ap"]) == 0

    db.expire_all()
    lai = db.execute(select(VoiceProfile).where(
        VoiceProfile.public_id == "vc_" + "f" * 32)).scalar_one()
    assert lai.ten_hien_thi == "Lily — nữ, tự nhiên", (
        "da doi ten mot giong RIENG cua khach — bo loc `dung_chung` bi bo qua")


def test_khop_theo_ma_cu_chu_KHONG_theo_ten(db):
    """🔴 Bản đầu của công cụ khoá theo TÊN HIỂN THỊ, và nó sẽ trượt bốn dòng.

    Lượt nhập 01/09 (`nhap_kho_giong_cu.py`) chỉ **vá xuất xứ** cho bốn giọng đã
    có từ trước — nó **KHÔNG đổi tên** chúng. Nên bốn giọng ấy vẫn mang tên do
    đợt nhập đầu đặt, khác với bảng đổi.

    ⭐ Lỗi ấy sẽ **không** trông như lỗi: công cụ báo "khong thay trong kho
       chung" cho đúng bốn dòng, và người đọc rất dễ kết luận "kho thiếu bốn
       giọng" thay vì "bảng của tôi khoá sai thứ".

    ⇒ Khoá theo `ma_cu` — nó là khoá của kho cũ, ghi vào `ghi_chu`, và **không
      trôi theo tên hiển thị**. Phép kiểm này dựng đúng ca ấy: đổi tên một giọng
      ra thứ hoàn toàn khác, rồi đòi công cụ vẫn nhận ra nó.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    mod = _nap_cong_cu()
    hang = _dung_kho(db, mod)

    # Một giọng bị ai đó đổi tên ngoài công cụ này.
    hang[0].ten_hien_thi = "Ten hoan toan khac do dot nhap dau dat"
    db.commit()
    pid = hang[0].public_id
    ma_dau = list(mod.DOI_TEN)[0]

    assert mod.main(["--ap"]) == 0, (
        "cong cu TRUOT vi khoa theo ten — phai khoa theo `ma_cu`")

    db.expire_all()
    lai = db.execute(select(VoiceProfile).where(
        VoiceProfile.public_id == pid)).scalar_one()
    assert lai.ten_hien_thi == mod.DOI_TEN[ma_dau][1]


def test_ghi_chu_rong_thi_NOI_RA_chu_khong_no(db):
    """`ghi_chu` rỗng ⇒ không đọc được `ma_cu` ⇒ giọng ấy nằm ngoài lượt đổi.

    ⛔ Nhưng nó phải **nói ra**, không được biến mất. Bốn giọng nhập đợt đầu
       từng có `ghi_chu` rỗng; nếu một hàng như thế lại xuất hiện thì người chạy
       phải thấy nó, chứ không phải thấy một bảng 24 dòng trông như đủ.
    """
    from apps.ltt_voice.tables import VoiceProfile
    mod = _nap_cong_cu()
    _dung_kho(db, mod)
    db.add(VoiceProfile(public_id="vc_" + "a" * 32, owner_id="nen-tang",
                        ten_hien_thi="Giong khong co xuat xu", ngon_ngu="vi",
                        ghi_chu="", trang_thai="active", dung_chung=True))
    db.commit()

    # Vẫn đổi được 25 giọng có `ma_cu`; giọng thiếu chỉ được BÁO.
    assert mod.main(["--ap"]) == 0
    assert mod._ma_cu("") == ""
    assert mod._ma_cu("{khong phai json") == ""
    assert mod._ma_cu('{"ma_cu": "lily_nu"}') == "lily_nu"


def test_xem_KHONG_ghi_gi(db):
    """`--xem` phải đọc-thuần. Một công cụ "xem" mà ghi là một cái bẫy."""
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    mod = _nap_cong_cu()
    _dung_kho(db, mod)
    assert mod.main(["--xem"]) == 0
    db.expire_all()
    con = {h.ten_hien_thi for h in db.execute(select(VoiceProfile)).scalars()}
    assert con == {v[0] for v in mod.DOI_TEN.values()}, "--xem da GHI vao CSDL"


def test_thieu_mot_giong_thi_TU_CHOI_ca_luot(db):
    """⛔ Thiếu một hàng ⇒ không đổi hàng nào.

    ⭐ Đây là lựa chọn có chủ ý và nó đắt hơn phương án dễ: bỏ qua hàng thiếu
       rồi đổi 24 cái còn lại. Nhưng "đổi 24/25" là một trạng thái **không ai
       ghi lại**, và lượt chạy sau sẽ không biết nó đang ở đâu. Từ chối cả lượt
       thì trạng thái luôn là một trong hai thứ đọc được: cũ hết, hoặc mới hết.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    mod = _nap_cong_cu()
    hang = _dung_kho(db, mod)
    db.delete(hang[0])
    db.commit()

    assert mod.main(["--ap"]) == 2, "thieu mot giong ma van bao thanh cong"
    db.expire_all()
    con = {h.ten_hien_thi for h in db.execute(select(VoiceProfile)).scalars()}
    assert con <= {v[0] for v in mod.DOI_TEN.values()}, (
        "da ghi mot phan du lenh bi tu choi")


def test_giu_lai_ban_do_ten_cu_de_truy_nguoc():
    """Bảng đổi phải giữ được cả hai đầu.

    ⚠️ Sau khi áp, tên cũ **không còn ở đâu trong CSDL**. Nếu bảng này cũng mất
       thì không ai truy được `Adrian` từng là `Tâm Lý Học` — tức mất luôn khả
       năng đối chiếu với kho cũ và với `tmp/kho_giong_cu.json`.

    ⇒ Giữ `DOI_TEN` trong mã, đừng xoá sau khi chạy.
    """
    mod = _nap_cong_cu()
    assert len(mod.DOI_TEN) == 25
    cu, moi = mod.DOI_TEN["tamlyhoc_men"]
    assert cu == "Tâm Lý Học — nam, thuyết minh"
    assert moi.startswith("Adrian")
