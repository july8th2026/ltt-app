"""`tools/ai_dang_dung_may_chu.py` — cửa hỏi TRƯỚC KHI DEPLOY.

## Vì sao công cụ này tồn tại

28/09/2026, hai phiên gần như deploy chồng nhau. Phiên kia dừng đúng lúc:
*"deploy khởi động lại `LTTStudioWorker`, và tôi đang có một job ASV chạy dở
(giai đoạn 8/13, 11 phút, 50 credit) — khởi động lại giữa chừng giết nó"*.

⚠️ `git status` sạch, gate xanh, ba bánh cóc toàn cây xanh — **⛔ không cổng nào
trong kho nói gì**. *"Ai đang chạy job"* là trạng thái **⛔ KHÔNG nằm trong git**,
nên ⛔ không bánh cóc nào bắt được; nó chỉ bắt được bằng một cửa hỏi CSDL.

## 🔴 Mệnh đề ĐẮT NHẤT tệp này canh: `KHONG BIET` ≠ `RANH`

Công cụ trả **ba** mã, và việc mã `4` ⛔ không được gộp vào `0` là cả lý do nó
đáng tin:

    0  RANH        ⛔ khong job nao
    3  DANG DUNG   co job — deploy se giet
    4  KHONG BIET  ⛔ khong doc duoc CSDL

Gộp *"⛔ không có job"* với *"⛔ không đo được"* là mất đúng khả năng phân biệt mà
công cụ này tồn tại để cấp — và cái mất ấy **nghiêng về phía nguy hiểm**: một CSDL
⛔ không đọc được sẽ trông y hệt một máy rảnh, rồi ai đó deploy lên nó.

⇒ Đây là cùng một hình dạng với *"`0` là không có, hay không đo được?"*, chỉ khác
  là ở đây hậu quả của việc lẫn hai thứ là **giết job của khách**.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CONG_CU = GOC / "tools" / "ai_dang_dung_may_chu.py"

RANH, DANG_DUNG, KHONG_BIET = 0, 3, 4


def _chay(*co: str, db_url: str | None) -> subprocess.CompletedProcess[str]:
    """Chạy công cụ trong một TIẾN TRÌNH RIÊNG.

    ⭐ Phải là tiến trình riêng, ⛔ không `import main()` rồi gọi: mệnh đề ở đây là
       **mã thoát**, và một `SystemExit` bắt trong tiến trình test ⛔ không chứng
       minh được rằng `2-cai-dat.ps1` sẽ đọc đúng số ấy.
    """
    import os
    moi = dict(os.environ)
    moi.pop("LTT_DATABASE_URL", None)
    if db_url is not None:
        moi["LTT_DATABASE_URL"] = db_url
    return subprocess.run([sys.executable, str(CONG_CU), *co],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(GOC), env=moi, timeout=120)


@pytest.fixture()
def db_rong(tmp_path):
    """Một CSDL có bảng `jobs` nhưng ⛔ không job nào."""
    url = f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}"
    import os
    cu = os.environ.get("LTT_DATABASE_URL")
    os.environ["LTT_DATABASE_URL"] = url
    try:
        import platform_core.db as dbmod
        import platform_core.models  # noqa: F401
        from platform_core import registry as _reg
        _reg.load_app_tables()
        dbmod.reset_engine()
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield url
    finally:
        import platform_core.db as dbmod
        dbmod.reset_engine()
        if cu is None:
            os.environ.pop("LTT_DATABASE_URL", None)
        else:
            os.environ["LTT_DATABASE_URL"] = cu


def _them_job(url: str, status: str) -> str:
    import os
    os.environ["LTT_DATABASE_URL"] = url
    import platform_core.db as dbmod
    from platform_core.models import Job
    dbmod.reset_engine()
    db = next(dbmod.get_session())
    try:
        j = Job(user_id="u1", app_slug="auto_scan_video", job_type="asv.dich",
                status=status, params={})
        db.add(j)
        db.commit()
        return j.id
    finally:
        db.close()
        dbmod.reset_engine()


def test_KHONG_doc_duoc_CSDL_tra_4_chu_KHONG_tra_0():
    """🔴 Bài đắt nhất tệp này. Nếu nó trả `0`, người deploy đọc là *"máy rảnh"*
    và bấm — trong khi thật ra ⛔ không ai biết gì cả."""
    r = _chay(db_url=None)
    assert r.returncode == KHONG_BIET, (
        f"thieu cau hinh CSDL phai tra {KHONG_BIET} (KHONG BIET), "
        f"nhan {r.returncode}\n{r.stdout}\n{r.stderr}")
    assert "KHONG BIET" in r.stdout
    assert "RANH" not in r.stdout.replace("KHONG BIET", "")


def test_khong_job_nao_tra_0_RANH(db_rong):
    r = _chay(db_url=db_rong)
    assert r.returncode == RANH, f"{r.returncode}\n{r.stdout}\n{r.stderr}"
    assert "RESULT: RANH" in r.stdout


@pytest.mark.parametrize("status", ["running", "queued"])
def test_co_job_tra_3_DANG_DUNG(db_rong, status):
    """`queued` cũng tính: một job xếp hàng sẽ được worker nhặt ngay sau khi
    khởi động lại, nhưng ⛔ quan trọng hơn — nó nói rằng **có người đang dùng**."""
    _them_job(db_rong, status)
    r = _chay(db_url=db_rong)
    assert r.returncode == DANG_DUNG, f"{r.returncode}\n{r.stdout}\n{r.stderr}"
    assert "RESULT: DANG DUNG" in r.stdout


def test_chi_tiet_KHONG_in_danh_tinh_khach(db_rong):
    """Một dòng log deploy ⛔ không cần `user_id` để trả lời *"có ai đang dùng"*.

    ⚠️ Log deploy đi vào `logs\\` và được chép đi khi hỗ trợ sự cố — mọi thứ in ra
       ở đây phải giả định là sẽ ra khỏi máy.
    """
    _them_job(db_rong, "running")
    r = _chay("--chi-tiet", db_url=db_rong)
    assert r.returncode == DANG_DUNG
    assert "auto_scan_video/asv.dich" in r.stdout      # du de biet ai can cho
    assert "u1" not in r.stdout.split("RESULT")[0].replace("auto_scan_video", "")


def test_cong_cu_CHI_DOC_khong_ghi_gi(db_rong):
    """⛔ Công cụ chạy ngay trước một lượt deploy — nó ⛔ không được sửa gì.

    Đo bằng `mtime` + kích thước tệp CSDL. ⭐ ⛔ Không đo bằng cách đọc mã tìm
    chữ `commit` — đó là đo VĂN BẢN thay vì đo TÍNH CHẤT, đúng cái bẫy
    `.typed-port` đã dạy hôm nay.
    """
    _them_job(db_rong, "running")
    tep = Path(db_rong.replace("sqlite:///", ""))
    truoc = (tep.stat().st_size, tep.stat().st_mtime_ns)
    assert _chay(db_url=db_rong).returncode == DANG_DUNG
    assert (tep.stat().st_size, tep.stat().st_mtime_ns) == truoc, \
        "cong cu da GHI vao CSDL"
