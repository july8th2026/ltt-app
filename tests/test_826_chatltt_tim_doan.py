"""
test_826 — truy hồi đoạn: QUYỀN ở mọi nền tảng, CHẤT LƯỢNG chỉ ở Postgres.
(H44 P06 bước 4)

## Tệp này cố ý chia làm hai, và ranh giới ấy là mệnh đề

* **Mục 1–2** chạy ở **mọi** nền tảng. Chúng đo quyền và phạm vi — hai thứ
  *không phụ thuộc* vào bộ xếp hạng, nên đường phụ (so khớp chuỗi con) trả lời
  được. Đó đúng ranh giới của một **cửa giả hợp lệ**: nó chỉ trả lời được
  những câu **không phụ thuộc thứ nó thay**.

* **Mục 3** đòi **PostgreSQL thật**. Bỏ dấu, xếp hạng, và `f_unaccent` là hành
  vi của máy chủ; một bản giả sẽ chứng minh bản giả chạy đúng (Bẫy 24).

⛔ Và có một phép kiểm chốt chính **ranh giới** ấy: không ai được đọc kết quả
   SQLite như bằng chứng cho chất lượng tìm kiếm.
"""
from __future__ import annotations

import pytest

CHU = "u-chu-826"
LA = "u-la-826"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _doan(db, *, user_id, conv_id, tep_id, cac_doan, trang_dau=1):
    from apps.chatltt.services import chia_doan
    from apps.chatltt.tables import ChatlttDoan
    for i, noi in enumerate(cac_doan):
        db.add(ChatlttDoan(user_id=user_id, conversation_id=conv_id,
                           tep_id=tep_id, thu_tu=i, trang=trang_dau + i,
                           noi_dung=noi, so_ky_tu=len(noi),
                           bam=chia_doan.bam(noi)))
    db.flush()


# ── 1. Quyền và phạm vi — chạy ở MỌI nền tảng ─────────────────────────────

def test_nguoi_LA_khong_tim_thay_doan_cua_chu(db):
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=["Phan le duoi mot credit duoc cong don sang luot sau."])

    assert tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                        cau_hoi="phan le credit"), "chu phai TIM THAY"
    assert tim_doan.tim(db, user_id=LA, conversation_id="c1",
                        cau_hoi="phan le credit") == []


def test_KHONG_ro_ri_sang_hoi_thoai_KHAC_cua_CHINH_minh(db):
    """⛔ Chiều thứ hai, và nó khác chiều trên: cùng một chủ, hai hội thoại.

    Tài liệu đính vào hội thoại A không được rò sang hội thoại B — nếu không
    thì "phạm vi hội thoại" chỉ là một nhãn, và người dùng sẽ thấy tài liệu
    công việc trả lời trong một cuộc trò chuyện riêng tư.
    """
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=["Bao cao noi bo ve doanh thu quy bon."])

    assert tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                        cau_hoi="doanh thu")
    assert tim_doan.tim(db, user_id=CHU, conversation_id="c2",
                        cau_hoi="doanh thu") == []


def test_cau_hoi_RONG_cho_danh_sach_rong_chu_khong_cho_TAT_CA(db):
    """🔴 Một câu hỏi rỗng trả về **mọi** đoạn là một rò rỉ trông như tính năng."""
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1", cac_doan=["a b c", "d e f"])
    for hoi in ("", "   ", "\n"):
        assert tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                            cau_hoi=hoi) == []


def test_tra_ve_KHONG_QUA_so_doan_da_xin(db):
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=[f"credit doan so {i}" for i in range(20)])
    ra = tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                      cau_hoi="credit", so_doan=3)
    assert len(ra) == 3


def test_tu_KHONG_lien_quan_thi_khong_khop(db):
    """⭐ Đối chứng âm — không có nó thì một hàm trả về mọi thứ cũng qua sạch."""
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=["Phan le duoi mot credit duoc cong don."])
    assert tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                        cau_hoi="ca heo bay tren sao Hoa") == []


# ── 2. Trích dẫn ──────────────────────────────────────────────────────────

def test_trich_dan_mang_du_BA_thu_buoc_5_doi(db):
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=["Noi dung ve credit va token."], trang_dau=7)
    doan, _diem = tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                               cau_hoi="credit")[0]
    td = tim_doan.trich_dan(doan)
    assert td["tep_id"] == "t1"
    assert td["trang"] == 7
    assert td["doan_id"]


def test_trang_0_giu_nguyen_la_0_chu_khong_thanh_1(db):
    """⭐ `trang = 0` nghĩa là **không biết** (`.txt` không có trang). Đổi nó
    thành 1 là bịa ra một trích dẫn trỏ vào "trang đầu" của một thứ không có
    trang nào."""
    from apps.chatltt.services import tim_doan

    _doan(db, user_id=CHU, conv_id="c1", tep_id="t1",
          cac_doan=["ghi chu ve credit"], trang_dau=0)
    doan, _ = tim_doan.tim(db, user_id=CHU, conversation_id="c1",
                           cau_hoi="credit")[0]
    assert tim_doan.trich_dan(doan)["trang"] == 0


# ── 3. Ranh giới cửa giả ──────────────────────────────────────────────────

def test_nen_tang_phai_NOI_RA_no_dang_chay_duong_nao(db):
    """🔴 Phép kiểm chốt chính **ranh giới**, không chốt một hành vi.

    Đường không-phải-Postgres là một **cửa giả hợp lệ**: nó trả lời được câu
    hỏi về quyền và phạm vi, vì hai thứ ấy không phụ thuộc bộ xếp hạng. Nhưng
    nó **không** trả lời được câu hỏi về chất lượng tìm kiếm — và cách duy nhất
    giữ được ranh giới ấy là bắt nó **tự khai**.

    ⛔ Nếu ngày nào `nen_tang()` biến mất, mọi phép kiểm ở mục 1–2 vẫn xanh, và
       ai đó sẽ đọc chúng như bằng chứng rằng tìm kiếm chạy đúng.
    """
    from apps.chatltt.services import tim_doan

    assert tim_doan.nen_tang(db) == "sqlite", (
        "canh nay phai la SQLite; neu doi thi phep kiem duoi day noi sai")
    assert tim_doan.nen_tang(db) != "postgresql"


def test_bo_dau_python_TU_KHAI_la_KHAC_unaccent_that():
    """🔴 Đo 06/09: Postgres ánh xạ `đ → d`, `NFD` thì không.

    Phép kiểm này ghim rằng khác biệt ấy **có thật**, để không ai thay đường
    thật bằng đường Python vì thấy nó "cũng bỏ dấu được".
    """
    import unicodedata

    from apps.chatltt.services import tim_doan

    tho = unicodedata.normalize("NFD", "đồng")
    chi_nfd = "".join(c for c in tho if not unicodedata.combining(c))
    assert chi_nfd == "đong", (
        "NFD da tu xu ly duoc `đ` — neu that thi phep do 06/09 het dung")
    # Ham cua ta VA rieng ca nay, nhung do la mot ban va theo danh sach.
    assert tim_doan._bo_dau_python("đồng") == "dong"


# ── 4. PostgreSQL THẬT ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pg_engine():
    from sqlalchemy import create_engine

    from tests import pg_scratch
    url = pg_scratch.scratch_url()
    if not url:
        pytest.skip(f"can {pg_scratch.ENV} tro toi mot CSDL vut di")
    eng = create_engine(url, pool_pre_ping=True)
    yield eng
    eng.dispose()


def test_f_unaccent_la_IMMUTABLE_chu_khong_phai_STABLE(pg_engine):
    """🔴 Đây là toàn bộ lý do hàm bọc tồn tại.

    `unaccent` là **STABLE** (`provolatile='s'`), và Postgres từ chối biểu thức
    chỉ số không IMMUTABLE. Ngày `f_unaccent` thôi IMMUTABLE, chỉ số không tạo
    được nữa — và nó sẽ hỏng lúc migrate, xa chỗ ai đó vừa sửa.
    """
    from sqlalchemy import text

    with pg_engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        c.execute(text(
            "CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text "
            "AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$ "
            "LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT"))
    with pg_engine.connect() as c:
        assert c.execute(text(
            "SELECT provolatile FROM pg_proc WHERE proname='unaccent' LIMIT 1"
        )).scalar() == "s", "unaccent da thanh IMMUTABLE => ham boc thanh thua"
        assert c.execute(text(
            "SELECT provolatile FROM pg_proc WHERE proname='f_unaccent' LIMIT 1"
        )).scalar() == "i"


def test_postgres_anh_xa_D_GACH_thanh_d_con_NFD_thi_khong(pg_engine):
    """⭐ Chính phép đo đã loại bỏ phương án "bỏ dấu ở Python"."""
    from sqlalchemy import text

    with pg_engine.connect() as c:
        for goc, mong in (("Đầu tư", "Dau tu"), ("đồng", "dong"),
                          ("Số điện thoại", "So dien thoai")):
            assert c.execute(text("SELECT unaccent(:x)"), {"x": goc}).scalar() == mong


def test_CHI_SO_GIN_tao_duoc_tren_bieu_thuc_da_boc(pg_engine):
    """🟢 Mệnh đề trung tâm của bước 4: chỉ số **tạo được**.

    Không có phép kiểm này thì migration chỉ là một ý định — và nó sẽ đỏ lần
    đầu tiên trên máy chủ thật, giữa một lượt deploy.
    """
    from sqlalchemy import text

    with pg_engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS thu_doan_fts"))
        c.execute(text("CREATE TABLE thu_doan_fts (id serial primary key, "
                       "noi_dung text not null)"))
        c.execute(text("CREATE INDEX ix_thu_fts ON thu_doan_fts "
                       "USING GIN (to_tsvector('simple', f_unaccent(noi_dung)))"))
        c.execute(text("INSERT INTO thu_doan_fts (noi_dung) VALUES (:x)"),
                  {"x": "Phần lẻ dưới một credit được cộng dồn sang lượt sau."})

    with pg_engine.connect() as c:
        khop = c.execute(text(
            "SELECT count(*) FROM thu_doan_fts WHERE "
            "to_tsvector('simple', f_unaccent(noi_dung)) "
            "@@ plainto_tsquery('simple', f_unaccent(:q))"),
            {"q": "phan le credit"}).scalar()
    assert khop == 1, "cau hoi KHONG DAU khong tim ra van ban CO DAU"

    with pg_engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS thu_doan_fts"))


def test_KHONG_index_thi_van_dung_KET_QUA_chi_khac_TOC_DO(pg_engine):
    """⛔ Đối chứng bắt buộc: chỉ số là chuyện **tốc độ**, không phải chuyện
    **đúng sai**. Nếu bỏ chỉ số mà kết quả đổi, nghĩa là ta đang đọc một thứ
    khác chứ không phải cùng một phép so."""
    from sqlalchemy import text

    with pg_engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS thu_khong_index"))
        c.execute(text("CREATE TABLE thu_khong_index (id serial primary key, "
                       "noi_dung text not null)"))
        c.execute(text("INSERT INTO thu_khong_index (noi_dung) VALUES (:x)"),
                  {"x": "Phần lẻ dưới một credit được cộng dồn sang lượt sau."})
    with pg_engine.connect() as c:
        n = c.execute(text(
            "SELECT count(*) FROM thu_khong_index WHERE "
            "to_tsvector('simple', f_unaccent(noi_dung)) "
            "@@ plainto_tsquery('simple', f_unaccent(:q))"),
            {"q": "phan le credit"}).scalar()
    assert n == 1
    with pg_engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS thu_khong_index"))
