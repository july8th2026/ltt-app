r"""U-05 + U-04 — CỔNG XUẤT XỨ cho kho giọng chung, và LÝ DO LOẠI khi curate.

## Câu mà cả tệp này phục vụ

Bản kiểm toán 07/09/2026 viết ranh giới bằng một câu:

    **"tải được ≠ dùng thương mại được"**

`VoiceProfile.license_status` là chỗ câu ấy thành **dữ liệu**;
`tham_chieu._dieu_kien_kho_chung()` là chỗ nó thành **một phép lọc**.

## ⛔ Phạm vi — và nó hẹp hơn bạn tưởng

Cổng này gác **kho chung** (`dung_chung=True`), tức tập giọng mà **mọi tài
khoản** đọc được. Nó **không** gác giọng riêng của một khách: xuất xứ của giọng
riêng đã có `VoiceConsent` trả lời, và bắt một cột thứ hai cùng trả lời câu ấy
sẽ làm **biến mất giọng của chính khách** vào ngày migration chạy.

⇒ Hai phép kiểm ở mục 3 chốt đúng ranh giới ấy từ **cả hai phía**. Thiếu phía
  thứ hai thì một bản vá "cho chắc, lọc hết" sẽ xanh — và nó là một thiệt hại
  thật cho khách hiện tại.

## 🔴 Vì sao có mục 2 (danh-sách-CHO, không phải danh-sách-CẤM)

`LICENSE_CHO_PHEP = ("ok",)` liệt kê thứ **được** đi qua. Một bản viết theo lối
`!= "tu_choi"` trông tương đương và **không** tương đương: ngày ai đó thêm một
trạng thái mới, danh-sách-cấm để nó **lọt** (mở, im lặng), danh-sách-cho **chặn**
nó cho tới khi có người cố ý thêm vào.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── 1. Cột và bảng tồn tại, với mặc định ĐÓNG ───────────────────────────────

def test_cot_license_status_mac_dinh_la_CHO_SOAT():
    """🔴 Mặc định phải ĐÓNG. `dung_chung=True` nghĩa là **mọi tài khoản** đọc
    được giọng ấy; mặc định `"ok"` biến việc bật một cờ thành việc phát tán một
    giọng chưa ai soát xuất xứ."""
    from apps.ltt_voice.tables import VoiceProfile

    c = VoiceProfile.__table__.c.license_status
    assert c.nullable is False
    assert c.default is not None and c.default.arg == "cho_soat"


def test_bang_curate_co_LY_DO_LOAI_va_DIEM_duoc_phep_RONG():
    """⛔ `diem` phải `nullable`. `None` = **chưa đo**, và nó khác `0.0` = "đo
    được, và rất tệ". Một cột `NOT NULL DEFAULT 0` nói rằng mọi giọng đều đã
    được chấm và đều được 0 điểm — một câu sai về **toàn bộ** kho."""
    from apps.ltt_voice.tables import VoiceQualityProfile

    c = VoiceQualityProfile.__table__.c
    assert "ly_do_loai" in c
    assert c.diem.nullable is True, "`diem` NOT NULL se bia mot diem cho moi giong"
    assert c.trang_thai_curate.default.arg == "cho_soat"


def test_mot_giong_chi_co_MOT_phan_quyet_curate():
    """Hai dòng cho cùng một giọng là hai câu trả lời cho cùng một câu hỏi, và
    không ai biết câu nào đang có hiệu lực."""
    from apps.ltt_voice.tables import VoiceQualityProfile

    rb = {tuple(sorted(c.name for c in r.columns))
          for r in VoiceQualityProfile.__table__.constraints
          if r.__class__.__name__ == "UniqueConstraint"}
    assert ("profile_id",) in rb


# ── 2. Danh sách CHO, không phải danh sách CẤM ──────────────────────────────

def test_LICENSE_CHO_PHEP_la_danh_sach_CHO():
    from apps.ltt_voice import tham_chieu
    assert tham_chieu.LICENSE_CHO_PHEP == ("ok",)


def test_cong_dung_IN_chu_khong_dung_phep_KHAC():
    """⛔ `!= "tu_choi"` trông tương đương và không tương đương — xem docstring
    đầu tệp. Đọc AST, không khớp chuỗi: chú thích quanh đó **nhắc tới** cả hai
    lối viết để giải thích, nên khớp chuỗi sẽ báo động trên chính lời giải
    thích của nó."""
    from apps.ltt_voice import tham_chieu

    cay = ast.parse(pathlib.Path(tham_chieu.__file__).read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef)
               and n.name == "_dieu_kien_kho_chung")
    ma = ast.unparse(ham)
    assert ".in_(" in ma, "cong khong dung phep IN tren danh sach cho"
    assert not any(isinstance(n, ast.Compare)
                   and any(isinstance(o, (ast.NotEq, ast.NotIn)) for o in n.ops)
                   for n in ast.walk(ham)), (
        "cong dung phep KHAC/NOT IN — mot trang thai moi se LOT QUA")


# ── 3. ⛔ Ranh giới: gác kho chung, KHÔNG gác giọng riêng ────────────────────

def test_cong_CO_trong_ca_HAI_cho_doc_kho_chung():
    """⛔ Chép điều kiện ra hai nơi là cách một bản vá sửa `tim_profile` mà
    quên `danh_sach` — và hai cửa khi ấy nói hai câu khác nhau về cùng một
    giọng: bộ chọn không hiện nó, nhưng gửi thẳng `public_id` thì vẫn đọc được.
    """
    from apps.ltt_voice import tham_chieu

    src = pathlib.Path(tham_chieu.__file__).read_text(encoding="utf-8")
    cay = ast.parse(src)
    for ten in ("tim_profile", "danh_sach"):
        ham = next(n for n in ast.walk(cay)
                   if isinstance(n, ast.FunctionDef) and n.name == ten)
        ma = ast.unparse(ham)
        assert "_dieu_kien_kho_chung()" in ma, (
            f"`{ten}` khong goi `_dieu_kien_kho_chung()`")
        assert "dung_chung.is_(True)" not in ma, (
            f"`{ten}` con doc thang `dung_chung` — cong U-05 bi di vong")


def test_cong_KHONG_cham_toi_giong_RIENG_cua_khach():
    """🔴 VẾ ĐỐI XỨNG, và nó là vế bảo vệ khách hiện tại.

    Không có phép kiểm này thì một bản vá "cho chắc, lọc hết" — thêm
    `license_status == 'ok'` vào **mọi** nhánh — sẽ xanh ở mọi phép kiểm trên,
    và nó làm **biến mất giọng của chính khách** ngay sau khi migration đặt
    `"cho_soat"` cho mọi dòng cũ.
    """
    from apps.ltt_voice import tham_chieu

    cay = ast.parse(pathlib.Path(tham_chieu.__file__).read_text(encoding="utf-8"))
    for ten in ("tim_profile", "danh_sach"):
        ham = next(n for n in ast.walk(cay)
                   if isinstance(n, ast.FunctionDef) and n.name == ten)
        # `license_status` chi duoc xuat hien BEN TRONG `_dieu_kien_kho_chung`,
        # khong bao gio o than hai ham nay.
        assert "license_status" not in ast.unparse(ham), (
            f"`{ten}` loc `license_status` o than ham — no se cham ca giong "
            f"RIENG cua khach, khong chi kho chung")


@pytest.mark.parametrize("trang_thai,cho_qua", [
    ("ok", True),
    ("cho_soat", False),
    ("thieu_bang_chung", False),
    ("tu_choi", False),
    ("", False),
    ("OK", False),          # phan biet hoa thuong — co y
    ("mot_trang_thai_moi", False),
])
def test_chi_OK_di_qua_cong(trang_thai, cho_qua):
    """⭐ Bảng này là đối chứng cho mục 2 ở dạng **giá trị**, không ở dạng cú
    pháp. Dòng `"mot_trang_thai_moi"` là dòng quan trọng nhất: nó là cái sẽ tồn
    tại vào ngày có người thêm một trạng thái và quên cổng này."""
    from apps.ltt_voice import tham_chieu
    assert (trang_thai in tham_chieu.LICENSE_CHO_PHEP) is cho_qua


# ── 4. Migration ────────────────────────────────────────────────────────────

MIG = GOC / "alembic/versions/20260908_1600_voice_license_va_curate.py"


def test_migration_dat_CHO_SOAT_cho_moi_dong_cu():
    """⛔ `server_default="ok"` sẽ **bịa một phán quyết** cho mọi dòng đang có.
    Cột này sinh ra để được trích dẫn trong một tranh chấp."""
    ma = MIG.read_text(encoding="utf-8")
    cay = ast.parse(ma)
    up = next(n for n in ast.walk(cay)
              if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
    them = [n for n in ast.walk(up)
            if isinstance(n, ast.Call) and ast.unparse(n.func).endswith("add_column")]
    assert them, "migration khong them cot nao"
    goi = ast.unparse(them[0])
    assert 'server_default=\'cho_soat\'' in goi or \
           'server_default="cho_soat"' in goi, goi
    assert "'ok'" not in goi and '"ok"' not in goi


def test_migration_noi_dung_vao_chuoi_va_KHONG_bo_lo_head():
    """Một migration mồ côi làm `ScriptDirectory` không phân giải được **cả
    chuỗi** — không riêng nó."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    s = ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))
    heads = s.get_heads()
    assert len(heads) == 1, f"chuoi migration bi CHE NHANH: {heads}"


def test_downgrade_go_HET_thu_da_them():
    """Không gỡ hết thì lượt `upgrade` lần sau vấp `column already exists` —
    và nó vấp ở giữa, để lại một CSDL nửa vời."""
    ma = MIG.read_text(encoding="utf-8")
    cay = ast.parse(ma)
    down = next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "downgrade")
    md = ast.unparse(down)
    assert "drop_column" in md and "license_status" in md
    assert "drop_table" in md and "voice_quality_profile" in md
# ── 5. ⛔ ĐƯỜNG GHI PHẢI TỒN TẠI — nếu không, cổng là cửa MỘT CHIỀU không chìa
#
# 🔴 Bản đầu của U-05 mắc **đúng** lớp lỗi mà `DECISIONS.md::DV-010` đã ghi:
#    *"ba đường ống có đủ khớp nối mà chưa bao giờ có nước."* Cột `license_status`
#    được ĐỌC bởi cổng và **không ai GHI**; bảng `voice_quality_profile` thì
#    không ai đọc lẫn ghi.
#
#    Hệ quả không phải "chưa xong": trước bản vá, `dung_chung=True` là **đủ** để
#    một giọng vào kho chung. Sau bản vá nó là **cần nhưng không đủ**, và điều
#    kiện đủ **không đường nào đạt tới được**.
#
# ⭐ Và một bảng đọc được mà không ai ghi trông **y hệt** một bảng đang hoạt
#    động — đó là lý do lớp lỗi này sống lâu.

SOAT = GOC / "tools/soat_giong.py"


def _ham(f, ten):
    cay = ast.parse(f.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


def test_CO_duong_ghi_license_status():
    """⛔ Không có nó thì không giọng nào lên `"ok"` được, mãi mãi."""
    assert SOAT.exists(), "khong co cong cu soat — cong U-05 la cua mot chieu"
    ma = SOAT.read_text(encoding="utf-8")
    assert "license_status" in ma
    assert "commit()" in ma, "cong cu khong ghi gi vao CSDL"


def test_duong_ghi_dat_duoc_DUNG_bon_gia_tri():
    """Và không nhiều hơn — mỗi giá trị lạ là một giá trị cổng sẽ chặn im lặng."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_soat", SOAT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    lic = {v[0] for v in m.ANH_XA.values()}
    assert lic == {"ok", "tu_choi", "thieu_bang_chung"}, lic
    # `cho_soat` la mac dinh cua migration, khong phai mot lenh — nen no KHONG
    # nam trong bang anh xa, va do la dung.


def test_LY_DO_bat_buoc_o_CA_HAI_chieu():
    """🔴 U-04 tồn tại vì một `rejected` không lý do là một quyết định không xem
    lại được. Nhưng một `accepted` không căn cứ cũng vậy — bản ghi license sinh
    ra để được **trích dẫn**, và một ô trống thì không trích được."""
    ma = SOAT.read_text(encoding="utf-8")
    cay = ast.parse(ma)
    them_co = [n for n in ast.walk(cay)
               if isinstance(n, ast.Call)
               and ast.unparse(n.func).endswith("add_argument")
               and any(isinstance(c, ast.Constant) and c.value == "--ly-do"
                       for c in n.args)]
    assert them_co, "khong khai `--ly-do`"
    assert all(any(k.arg == "required" and k.value.value is True
                   for k in n.keywords) for n in them_co), (
        "`--ly-do` khong `required=True` — se co phan quyet khong can cu")


def test_ly_do_RONG_hoac_QUA_NGAN_bi_tu_choi():
    """⭐ `required=True` chỉ chặn **vắng mặt**, không chặn `--ly-do ok`. Một ô
    đã điền mà không phải một câu trả lời **tệ hơn** một ô trống: ô trống thì
    người đọc biết là chưa ai soát."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_soat2", SOAT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.LY_DO_TOI_THIEU >= 8
    assert m.main(["duyet", "khong-ton-tai", "--ly-do", "ok"]) == 2


def test_duyet_KHONG_tu_bat_dung_chung():
    """⛔ *"Xuất xứ có rõ không"* và *"ta có MUỐN mang nó ra kho chung không"* là
    hai câu hỏi khác nhau. Gộp chúng là cách một lệnh **ghi nhận giấy tờ** bỗng
    trở thành một lệnh **xuất bản**."""
    ma = ast.unparse(_ham(SOAT, "_dat"))
    assert "dung_chung = True" not in ma and "dung_chung=True" not in ma, (
        "lenh duyet TU BAT `dung_chung` — mot lenh ghi nhan giay to dang xuat "
        "ban mot giong")


# ── 6. 🔴 HẠ LICENSE khỏi "ok" PHẢI xoá bản nghe thử KHO CHUNG đã dựng
#
# HAI LỚP. Lớp 1 — cửa đọc: từ RC1 (`eb896da7`) `routes/_p_audio.py` chỉ phục
# vụ `voice/chung/*.wav` khi giọng CÒN dung_chung + license ok + active (tra
# CSDL), nên rút license là tệp hết tải được ngay — `test_528` ghim lớp đó.
# Lớp 2 — ở đây: `_dat()` rút license thì xoá TẠI NGUỒN bản nghe thử kho chung,
# vì đó là tiếng nói của một người thật; nó không được nằm lại trong kho sau
# khi giấy tờ bị rút.
#
# Cùng lớp với thu hồi / đổi làn (`giong_vong_doi.khoa_da_biet`,
# `nghe_thu.dung_lai_cho_giong`).

def _nap_soat(ten: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ten, SOAT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def kho_soat(tmp_path, monkeypatch):
    """CSDL sqlite + LocalStorage tạm, và một giọng KHO CHUNG `license="ok"`
    đã có bản nghe thử thật ở `nghe_thu.khoa_chung(public_id)`."""
    import io

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'soat.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, get_storage, set_storage
    set_storage(LocalStorage(str(tmp_path / "store")))

    from apps.ltt_voice import nghe_thu
    from apps.ltt_voice.tables import VoiceProfile

    gen = dbmod.get_session()
    db = next(gen)
    try:
        ho_so = VoiceProfile(
            owner_id="00000000-0000-0000-0000-0000000000ee",
            ten_hien_thi="Kho chung soat", ngon_ngu="vi",
            ngon_ngu_nguon="khai_bao", trang_thai="active",
            dung_chung=True, license_status="ok")
        db.add(ho_so)
        db.commit()
        pid = str(ho_so.public_id)
        khoa = nghe_thu.khoa_chung(pid)
        get_storage().put(khoa, io.BytesIO(b"RIFF-gia"),
                          content_type="audio/wav")
        assert get_storage().exists(khoa), "chua dat duoc tep de kiem xoa"
        yield db, pid, khoa
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        set_storage(None)
        dbmod.reset_engine()


@pytest.mark.parametrize("lenh", ["tu-choi", "thieu-bang-chung"])
def test_ha_license_khoi_OK_XOA_ban_nghe_thu_kho_chung(kho_soat, lenh):
    """🔴 MỆNH ĐỀ TRUNG TÂM (privacy): rút license một giọng kho chung thì bản
    nghe thử kho chung của nó phải biến mất khỏi kho. Cửa đọc `_p_audio` đã
    chặn phục vụ nó (lớp 1, `test_528`); phép này ghim lớp 2 — tệp tiếng của
    một người thật không nằm lại trong kho."""
    from platform_core.storage import get_storage
    db, pid, khoa = kho_soat
    m = _nap_soat("_soat_ha")
    assert m._dat(db, pid, lenh, "giay uy quyen het han", "tester") == 0
    assert not get_storage().exists(khoa), (
        f"`{lenh}` ha license khoi 'ok' ma KHONG xoa ban nghe thu kho chung "
        "— _p_audio van phuc vu no cho moi khach")


def test_duyet_lai_giong_DA_ok_GIU_ban_nghe_thu(kho_soat):
    """Đối chứng: `ok -> ok` không rút gì cả, nên không được xoá. Thiếu phép
    này thì một bản vá "xoá mỗi lần gọi `_dat`" cũng xanh ở phép trên."""
    from platform_core.storage import get_storage
    db, pid, khoa = kho_soat
    m = _nap_soat("_soat_duyet")
    assert m._dat(db, pid, "duyet", "bo sung giay to lan hai", "tester") == 0
    assert get_storage().exists(khoa), "duyet lai giong da ok XOA mat preview"


def test_xoa_that_bai_KHONG_lam_hong_phan_quyet(kho_soat, monkeypatch, capsys):
    """Xoá kho là best-effort (`_p_giong._xoa_khoa`): kho chập không được làm
    `_dat` ném sau khi phán quyết đã ghi vào CSDL — nó phải NÓI RA để người
    soát xoá tay."""
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.storage import get_storage
    db, pid, khoa = kho_soat

    def _hong(_k):
        raise OSError("kho chap")
    monkeypatch.setattr(get_storage(), "delete", _hong)

    m = _nap_soat("_soat_hong")
    assert m._dat(db, pid, "tu-choi", "giay uy quyen het han", "tester") == 0
    assert khoa in capsys.readouterr().out, "xoa that bai ma khong in khoa ra"
    lic = db.execute(select(VoiceProfile.license_status).where(
        VoiceProfile.public_id == pid)).scalar_one()
    assert lic == "tu_choi"
