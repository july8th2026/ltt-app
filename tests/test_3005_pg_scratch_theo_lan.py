"""Mỗi làn một CSDL scratch riêng — bỏ khoá `postgres_test` (N-10, Task 0).

## Khoá này bảo vệ MỘT CÁI TÊN, không bảo vệ một tài nguyên độc quyền

Đo 24/09: một làn giữ `postgres_test` **78 phút**, và một làn phiên khác xếp hàng
sau nó — **cho một thứ lẽ ra không chặn ai**. Lý do khoá tồn tại: mọi làn dùng chung
**một** tên CSDL (`lttplatform_test`), và `test_423.moi_truong` gọi `drop_all` trên
nó. Cho mỗi làn một tên riêng thì hết xung đột và không cần khoá nào.

⚠️ **Khác `cpu_nhieu`, và đừng gộp hai thứ:** khoá CPU chia **sức tính** nên không bỏ
   được — nhả ra rồi giành lại chỉ **chậm hơn**. `postgres_test` chia một **cái tên**;
   nhả ra rồi giành lại có thể **sai kết quả**, nhưng cái tên thì **nhân bản được**.

⭐ Nó đóng luôn **M-11**: một `AsvRun` `running` mồ côi của làn khác tự nộp job vô
   hạn (`jobs` phình 1.274 dòng) làm trần 200 job thành trần **dùng chung**, nên trên
   CSDL đó không còn đo được *"vòng sửa có quay không"*. Mỗi làn một CSDL ⇒ không làn
   nào thấy rác của làn khác.

## ⛔ Tên phải suy từ WORKTREE, không từ PID

`test_1720_wf_dong_co_pg` mở **hai tiến trình** worker khác nhau và cả hai phải trở
về **CÙNG MỘT** CSDL scratch. Suy tên từ `os.getpid()` sẽ cho hai tên khác nhau và
làm bài đó hỏng theo một cách rất khó đọc. Nên phép suy phải **tất định theo cây**.
"""
from __future__ import annotations

import pytest
from _pytest.outcomes import Failed

from tests import pg_scratch

#: Tên CSDL PostgreSQL: tối đa 63 byte (`NAMEDATALEN - 1`).
DAI_TOI_DA = 63


@pytest.fixture(autouse=True)
def _co_url(monkeypatch):
    """`scratch_url` trả `""` khi biến chưa đặt — các bài dưới cần một gốc URL.

    ⛔ Dùng một URL GIẢ, không đọc `app.env`: một phép kiểm về cách ĐẶT TÊN không
       được đòi mật khẩu CSDL thật, và không được chạm CSDL nào.
    """
    monkeypatch.setenv(pg_scratch.ENV,
                       "postgresql+psycopg://u:p@127.0.0.1:5432/lttplatform_test")
    # Duong theo lan con OPT-IN (vai `ltt_app` khong co CREATEDB — xem `pg_scratch`).
    # Cac bai duoi kiem CACH DAT TEN, nen chung bat co tuong minh.
    monkeypatch.setenv("LTT_PG_SCRATCH_THEO_LAN", "1")


def test_hai_lan_khac_nhau_cho_hai_CSDL_khac_nhau():
    """Cái làm khoá trở nên không cần thiết: hai làn không còn đụng nhau."""
    a = pg_scratch.scratch_url("asvf-b1")
    b = pg_scratch.scratch_url("asvf-dich")
    assert a != b, (a, b)
    # `scratch_url` đòi tên chứa "test" — rào đó phải còn nguyên sau khi đổi.
    assert "test" in a.rsplit("/", 1)[-1]
    assert "test" in b.rsplit("/", 1)[-1]


def test_ten_CSDL_hop_le_voi_postgres():
    """≤ 63 ký tự, chữ thường, không dấu gạch ngang (PostgreSQL sẽ đòi trích dẫn)."""
    ten = pg_scratch.scratch_url("asvf-nghiem-thu-v2").rsplit("/", 1)[-1]
    assert len(ten) <= DAI_TOI_DA, f"{len(ten)} ky tu: {ten}"
    assert ten == ten.lower(), ten
    assert "-" not in ten, ten
    assert ten.replace("_", "").isalnum(), ten


def test_ten_dai_bi_CAT_chu_khong_lam_hong_tran_63():
    """Một tên làn dài không được sinh ra một tên CSDL PostgreSQL từ chối."""
    ten = pg_scratch.scratch_url("a" * 200).rsplit("/", 1)[-1]
    assert len(ten) <= DAI_TOI_DA, f"{len(ten)} ky tu"
    assert "test" in ten


def test_cung_mot_lan_cho_CUNG_MOT_ten_moi_lan_goi():
    """⛔ TẤT ĐỊNH. `test_1720_wf_dong_co_pg` mở HAI tiến trình worker và cả hai
    phải trở về CÙNG một CSDL.

    Suy tên từ `os.getpid()` sẽ cho hai tên khác nhau, và bài đó hỏng theo một cách
    rất khó đọc (hai worker nhìn hai CSDL rỗng, không ai thấy job của ai).
    """
    assert pg_scratch.scratch_url("x1") == pg_scratch.scratch_url("x1")


def test_khong_truyen_lan_thi_SUY_TU_WORKTREE_chu_khong_tu_PID():
    """`lan=""` phải suy được, và phải suy TẤT ĐỊNH."""
    a = pg_scratch.scratch_url()
    b = pg_scratch.scratch_url()
    assert a == b, (a, b)
    assert "test" in a.rsplit("/", 1)[-1]


def test_ten_suy_ra_MANG_ten_cay_lam_viec():
    """Tên phải nhận ra được là của làn nào — một tên vô danh thì không ai dọn được.

    ⚠️ Chốt lỏng (chỉ đòi một mẩu tên cây có mặt) chứ không chốt cứng cả chuỗi: tên
       cây đổi theo làn, và một phép kiểm ghim cứng tên cây này sẽ đỏ ở mọi làn khác.

    ⛔ Và lấy mẩu ở ĐẦU, không ở cuối. Bản đầu của bài này đòi **8 ký tự cuối** của
       tên cây, và nó đỏ ngay khi `_chuan_ten` cắt tên xuống 28 ký tự để chừa chỗ cho
       vân tay `pg_ten_cay` — **đuôi là phần bị cắt**. Tức bài kiểm đang mô tả một
       lược đồ đặt tên khác với lược đồ thật; sửa bài kiểm, không nới lược đồ.
    """
    import pathlib

    cay = pathlib.Path(__file__).resolve().parents[1].name.lower()
    mau = "".join(c for c in cay if c.isalnum())[:8]
    ten = pg_scratch.scratch_url().rsplit("/", 1)[-1]
    assert mau and mau in ten.replace("_", ""), (mau, ten)


def test_rao_AN_TOAN_van_con_nguyen(monkeypatch):
    """⛔ Bỏ khoá KHÔNG được kéo theo nới rào an toàn.

    `scratch_url` phải vẫn **hard-fail** khi tên CSDL không chứa `test` — rào đó là
    thứ duy nhất đứng giữa `drop_all` và CSDL đang phục vụ khách.
    """
    # ⛔ `monkeypatch`, khong `os.environ[...]` tho: dat thang se RO RI sang cac bai
    #    sau trong cung tep, va mot bai do vi bai truoc lam ban moi truong la mot
    #    gio dong ho bi mat.
    monkeypatch.setenv(pg_scratch.ENV,
                       "postgresql+psycopg://u:p@127.0.0.1:5432/lttplatform")
    # ⛔ `Failed`, khong `BaseException`: ruff B017 dung o day — mot `raises` qua
    #    rong se XANH ca khi ham nem `TypeError` vi mot loi go, tuc no khong con
    #    chung minh rang RAO da ban.
    with pytest.raises(Failed):
        pg_scratch.scratch_url("asvf-b1")


def test_bien_CHUA_DAT_thi_tra_RONG_chu_khong_nem(monkeypatch):
    """Hành vi cũ phải giữ: chưa đặt biến ⇒ `""` ⇒ bộ test dùng SQLite và skip."""
    monkeypatch.delenv(pg_scratch.ENV, raising=False)
    assert pg_scratch.scratch_url("asvf-b1") == ""
    assert pg_scratch.scratch_url() == ""
