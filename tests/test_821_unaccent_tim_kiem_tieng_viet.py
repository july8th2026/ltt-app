"""
test_821 — tìm kiếm tiếng Việt KHÔNG DẤU phải tìm được văn bản CÓ DẤU. (H44 P06)

🔴 Phép đo 06/09 trên PostgreSQL thật (`lttplatform_test`):

    cau hoi                     khong unaccent   co unaccent
    "phần lẻ credit"   (co dau)        KHOP          KHOP
    "phan le credit"   (khong dau)      -            KHOP
    "cong don luot sau"              -            KHOP
    "so token that su dung"          -            KHOP
    "tinh theo token"                -            KHOP

Bốn dòng dưới là ca **thường gặp nhất** — người Việt gõ nhanh thì gõ không dấu.
Một tìm kiếm không tìm được `"phan le credit"` là một tính năng phần lớn người
dùng thấy là hỏng, không phải một góc hiếm.

⛔ **Ví dụ đầu tiên tôi chọn là một ví dụ BẨN**, và chính phép kiểm này bác nó:
`"tinh tien theo token"` trượt ở **cả hai** chế độ, vì từ `"tiền"` **không có**
trong văn bản. `plainto_tsquery` nối các từ bằng **AND**, nên một từ vắng mặt
làm cả câu trượt — **giống hệt** triệu chứng thiếu dấu. Xem
`test_MOT_TU_VANG_MAT_truot_GIONG_HET_thieu_dau`.

⭐ Postgres **không có** cấu hình `vietnamese`, nhưng `simple` tách từ tiếng Việt
   **đúng** (theo khoảng trắng, hạ chữ thường, giữ dấu). Thứ còn thiếu chỉ là
   **bỏ dấu** — và đó đúng là việc của `unaccent`.

⛔ Tệp này **cần PostgreSQL thật**. Không giả lập được: `unaccent` là một phần mở
   rộng của máy chủ, và một bản giả sẽ chứng minh bản giả chạy đúng chứ không
   chứng minh máy chủ chạy đúng — cùng luật Bẫy 24 (*phép kiểm tự dựng đầu vào
   chỉ đo phía tiêu thụ*).
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from tests import pg_scratch

VAN_BAN = ("Giá mỗi lượt gọi được tính theo số token thật sự dùng. "
           "Phần lẻ dưới một credit được cộng dồn sang lượt sau.")


@pytest.fixture(scope="module")
def pg():
    url = pg_scratch.scratch_url()
    if not url:
        pytest.skip(f"can {pg_scratch.ENV} tro toi mot CSDL vut di")
    eng = create_engine(url, pool_pre_ping=True)
    with eng.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    yield eng
    eng.dispose()


def _khop(eng, hoi: str, *, bo_dau: bool) -> bool:
    """Câu hỏi `hoi` có khớp `VAN_BAN` không, với/không `unaccent`."""
    if bo_dau:
        sql = ("SELECT to_tsvector('simple', unaccent(:x)) "
               "@@ plainto_tsquery('simple', unaccent(:q))")
    else:
        sql = ("SELECT to_tsvector('simple', :x) "
               "@@ plainto_tsquery('simple', :q)")
    with eng.connect() as c:
        return bool(c.execute(text(sql), {"x": VAN_BAN, "q": hoi}).scalar())


# ── 1. Cái lỗ, và nó có thật ───────────────────────────────────────────────

@pytest.mark.parametrize("hoi", ["phần lẻ credit", "cộng dồn lượt sau"])
def test_hoi_CO_DAU_van_khop_khi_khong_bo_dau(pg, hoi):
    """Đối chứng dương: có dấu thì `simple` đã đủ, không cần `unaccent`."""
    assert _khop(pg, hoi, bo_dau=False)


@pytest.mark.parametrize("hoi", ["tinh theo token", "phan le credit",
                                 "cong don luot sau", "so token that su dung"])
def test_hoi_KHONG_DAU_KHONG_khop_neu_thieu_unaccent(pg, hoi):
    """🔴 Cái lỗ. Phép kiểm này ghim rằng nó **có thật** — nếu ngày nào đó nó
    đỏ, nghĩa là Postgres đã tự xử lý dấu và `unaccent` thành thừa."""
    assert not _khop(pg, hoi, bo_dau=False), (
        "khong dau da khop san => `unaccent` co the khong con can")


# ── 2. `unaccent` đóng cái lỗ ấy ───────────────────────────────────────────

@pytest.mark.parametrize("hoi", ["tinh theo token", "phan le credit",
                                 "cong don luot sau", "PHAN LE CREDIT"])
def test_unaccent_lam_hoi_KHONG_DAU_tim_duoc_van_ban_CO_DAU(pg, hoi):
    """🟢 Mệnh đề trung tâm của bước 1 P06."""
    assert _khop(pg, hoi, bo_dau=True), hoi


@pytest.mark.parametrize("hoi", ["phần lẻ credit", "cộng dồn lượt sau"])
def test_bo_dau_KHONG_lam_hong_cau_hoi_CO_DAU(pg, hoi):
    """⛔ Đối chứng bắt buộc: một bản vá cho ca A mà làm hỏng ca B là một bản vá
    tệ hơn cái nó chữa. Bỏ dấu **cả hai vế** nên có dấu vẫn phải khớp."""
    assert _khop(pg, hoi, bo_dau=True), hoi


def test_tu_KHONG_lien_quan_van_KHONG_khop(pg):
    """⭐ Đối chứng âm — không có nó thì một hàm luôn trả `True` cũng qua được
    mọi phép kiểm trên. Đây đúng luật Bẫy 24."""
    assert not _khop(pg, "cá heo bay trên sao Hoả", bo_dau=True)
    assert not _khop(pg, "ca heo bay tren sao hoa", bo_dau=True)


# ── 3. Extension thật sự nằm trong CSDL ────────────────────────────────────

def test_unaccent_da_duoc_cai(pg):
    with pg.connect() as c:
        assert c.execute(text(
            "SELECT count(*) FROM pg_extension WHERE extname = 'unaccent'"
        )).scalar() == 1


def test_migration_dung_ten_extension_trusted(pg):
    """`unaccent` phải là **trusted** — đó là lý do migration cài được mà không
    cần superuser. Ngày nó thôi trusted, bước này thành việc cần người."""
    with pg.connect() as c:
        assert c.execute(text(
            "SELECT bool_or(trusted) FROM pg_available_extension_versions "
            "WHERE name = 'unaccent'")).scalar() is True


def test_MOT_TU_VANG_MAT_truot_GIONG_HET_thieu_dau(pg):
    """🔴 Bẫy đã dính khi viết chính tệp này, và nó phải nằm lại bằng một phép
    kiểm chứ không bằng một dòng ghi chú.

    Ví dụ đầu tiên tôi chọn là `"tinh tien theo token"`, và tôi ghi vào kế hoạch
    P06 rằng nó trượt **vì không dấu**. Sai: từ `"tiền"` **không có** trong văn
    bản. `plainto_tsquery` nối các từ bằng **AND**, nên chỉ một từ vắng mặt là
    cả câu trượt — **giống hệt** triệu chứng thiếu dấu.

    ⇒ Hai nguyên nhân, một triệu chứng. Phép kiểm này chốt rằng chúng **thật sự
    khác nhau**, để lần sau không ai lại đọc nhầm cái này thành cái kia.
    """
    # THIEU TU: truot o CA HAI che do — bo dau khong cuu duoc
    assert not _khop(pg, "tinh tien theo token", bo_dau=False)
    assert not _khop(pg, "tinh tien theo token", bo_dau=True)
    assert not _khop(pg, "tính tiền theo token", bo_dau=True), (
        "co dau day du van truot => chung minh nguyen nhan la THIEU TU")

    # THIEU DAU: truot khi khong bo dau, KHOP khi bo dau
    assert not _khop(pg, "tinh theo token", bo_dau=False)
    assert _khop(pg, "tinh theo token", bo_dau=True)
