"""
H1.1 — lớp CSDL: cấu hình, che mật khẩu, vòng di trú.

Trọng tâm của file này là **mật khẩu CSDL không được lọt ra ngoài**. Đó không
phải lo xa: thông báo lỗi của driver PostgreSQL thường nhúng nguyên chuỗi kết
nối, `/health/ready` thì cố ý không yêu cầu đăng nhập (để reverse proxy thăm
dò được), và người ta hay dán nguyên thông báo lỗi vào chat để hỏi. Ba điều đó
cộng lại là một đường rò rất thật.

Phần vòng di trú chạy trên SQLite tạm. Đích thật là PostgreSQL, nhưng migration
đầu tiên chỉ dùng kiểu dữ liệu chạy được ở cả hai, nên vẫn chứng minh được bộ
máy Alembic hoạt động mà không bắt mọi máy chạy test phải có PostgreSQL.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

MAT_KHAU_GIA = "MatKhauSieuBiMat123"
URL_GIA = f"postgresql+psycopg://ltt_user:{MAT_KHAU_GIA}@127.0.0.1:5432/lttdb"


# ── Che mật khẩu ──────────────────────────────────────────────────────────────

def test_che_mat_khau_giu_lai_phan_can_de_chan_doan():
    """Che mật khẩu nhưng vẫn thấy host/cổng/tên CSDL.

    Che sạch cả chuỗi thì thông báo lỗi trở nên vô dụng — người vận hành cần
    biết nó đang cố nối tới đâu.
    """
    from platform_core.db import che_mat_khau

    ket_qua = che_mat_khau(URL_GIA)
    assert MAT_KHAU_GIA not in ket_qua
    assert "***" in ket_qua
    assert "127.0.0.1:5432" in ket_qua
    assert "lttdb" in ket_qua
    assert "ltt_user" in ket_qua


@pytest.mark.parametrize("chuoi", [
    "",
    "postgresql://khong_co_mat_khau@host/db",
    "sqlite:///duong/dan/file.db",
])
def test_che_mat_khau_khong_lam_hong_chuoi_khong_co_mat_khau(chuoi):
    from platform_core.db import che_mat_khau
    assert che_mat_khau(chuoi) == chuoi


def test_loi_ket_noi_khong_bao_gio_lo_mat_khau():
    """Đường lỗi thật: nối tới một cổng không có ai nghe.

    Đây là kịch bản hay gặp nhất (CSDL chưa chạy, sai cổng, tường lửa chặn) và
    cũng là lúc thông báo lỗi của driver nhúng nguyên chuỗi kết nối.
    """
    import time

    from platform_core.db import CONNECT_TIMEOUT_S, kiem_tra_ket_noi, reset_engine

    reset_engine()
    try:
        url = f"postgresql+psycopg://ltt_user:{MAT_KHAU_GIA}@127.0.0.1:1/khong_ton_tai"
        bat_dau = time.monotonic()
        duoc, ly_do = kiem_tra_ket_noi(url)
        mat = time.monotonic() - bat_dau

        assert duoc is False
        assert ly_do, "phai noi ro vi sao khong noi duoc"
        assert MAT_KHAU_GIA not in ly_do

        # Phai BO CUOC nhanh. Khong co gioi han thoi gian thi tren Windows mot
        # dia chi bi tuong lua nuot goi treo hon hai phut — va trong hai phut do
        # worker phuc vu request nam im. Phat hien duoc vi chinh test nay tung
        # mat 130 giay.
        assert mat < CONNECT_TIMEOUT_S * 3, (
            f"cho {mat:.0f}s de biet khong noi duoc — qua lau, "
            f"gioi han dat la {CONNECT_TIMEOUT_S}s"
        )
    finally:
        reset_engine()


# ── Cấu hình ──────────────────────────────────────────────────────────────────

def test_khong_tu_doan_chuoi_ket_noi_mac_dinh():
    """Chưa đặt `LTT_DATABASE_URL` thì phải báo lỗi, không tự đoán localhost.

    Một mặc định thầm lặng trỏ vào `localhost` khiến ứng dụng chạy được trên
    máy phát triển rồi hỏng trên máy chủ theo cách rất khó truy — và tệ hơn là
    có thể nối nhầm vào một CSDL khác đang chạy trên cùng máy.
    """
    from platform_core.db import DatabaseNotConfigured, database_url

    with pytest.raises(DatabaseNotConfigured):
        database_url(env={})

    with pytest.raises(DatabaseNotConfigured):
        database_url(env={"LTT_DATABASE_URL": "   "})


def test_doc_dung_bien_moi_truong():
    from platform_core.db import database_url
    assert database_url(env={"LTT_DATABASE_URL": URL_GIA}) == URL_GIA


def test_alembic_ini_khong_chua_chuoi_ket_noi():
    """`alembic.ini` nằm trong git — chuỗi kết nối tuyệt đối không ở đó.

    Bản mẫu `alembic init` sinh ra có sẵn dòng `sqlalchemy.url = driver://...`.
    Điền mật khẩu thật vào đó là cách phổ biến nhất để lộ mật khẩu CSDL lên kho
    mã nguồn.
    """
    noi_dung = (ROOT / "alembic.ini").read_text(encoding="utf-8")
    for dong in noi_dung.splitlines():
        dong = dong.strip()
        if dong.startswith("#"):
            continue
        assert not dong.startswith("sqlalchemy.url"), (
            "alembic.ini khong duoc chua chuoi ket noi — env.py doc tu "
            "LTT_DATABASE_URL"
        )


# ── Vòng di trú ───────────────────────────────────────────────────────────────

def _chay_alembic(*args: str, db_url: str | None) -> subprocess.CompletedProcess:
    """Chạy alembic trong tiến trình con.

    `encoding="utf-8"` là bắt buộc, không phải trang trí: mặc định Python giải
    mã đầu ra tiến trình con bằng bảng mã hệ thống (cp1252 trên máy Việt Nam),
    và alembic in ra ký tự nằm ngoài bảng đó → `UnicodeDecodeError` làm test đỏ
    vì lý do chẳng liên quan gì tới thứ đang kiểm tra.
    """
    env = dict(os.environ)
    if db_url is None:
        env.pop("LTT_DATABASE_URL", None)
    else:
        env["LTT_DATABASE_URL"] = db_url
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(ROOT), env=env, capture_output=True,
        encoding="utf-8", errors="replace", timeout=180,
    )


def test_vong_di_tru_tien_lui_tien(tmp_path):
    """`upgrade` → `downgrade` → `upgrade` phải sạch cả ba lần.

    Lùi được thì mới dám tiến: một migration không có đường lùi nghĩa là khi
    nó hỏng trên CSDL có dữ liệu thật, lựa chọn duy nhất còn lại là khôi phục
    từ bản sao lưu.
    """
    db = tmp_path / "thu.db"
    url = f"sqlite:///{db.as_posix()}"

    r = _chay_alembic("upgrade", "head", db_url=url)
    assert r.returncode == 0, r.stderr

    import sqlalchemy as sa
    engine = sa.create_engine(url)
    bang = set(sa.inspect(engine).get_table_names())
    engine.dispose()
    assert "platform_info" in bang
    assert "alembic_version" in bang

    r = _chay_alembic("downgrade", "-1", db_url=url)
    assert r.returncode == 0, r.stderr

    engine = sa.create_engine(url)
    bang = set(sa.inspect(engine).get_table_names())
    engine.dispose()
    assert "platform_info" not in bang, "downgrade phai xoa bang no da tao"

    r = _chay_alembic("upgrade", "head", db_url=url)
    assert r.returncode == 0, r.stderr


def test_migration_bao_loi_ro_khi_chua_cau_hinh():
    """Chạy alembic mà chưa đặt `LTT_DATABASE_URL` → báo rõ, không đổ stack."""
    r = _chay_alembic("upgrade", "head", db_url=None)
    assert r.returncode != 0
    assert "LTT_DATABASE_URL" in (r.stdout + r.stderr)


def test_moi_migration_deu_co_duong_lui():
    """Mọi file migration phải có `downgrade()` làm việc thật.

    Không phải vì hay dùng đường lùi, mà vì viết được nó buộc phải nghĩ xem
    thay đổi này có làm mất dữ liệu không.
    """
    thu_muc = ROOT / "alembic" / "versions"
    files = [p for p in thu_muc.glob("*.py") if not p.name.startswith("__")]
    assert files, "chua co migration nao"
    for p in files:
        noi_dung = p.read_text(encoding="utf-8")
        assert "def downgrade()" in noi_dung, f"{p.name} thieu downgrade()"
        than = noi_dung.split("def downgrade()", 1)[1]
        # Chi co "pass" nghia la khong lui duoc that.
        assert than.strip().replace("-> None:", "").strip() not in ("pass", ""), (
            f"{p.name}: downgrade() rong — khong lui duoc"
        )


# ── /health/ready ─────────────────────────────────────────────────────────────

def test_health_ready_bao_ly_do_khi_csdl_chet(monkeypatch):
    """CSDL không nối được → 503 kèm lý do, và **không lộ mật khẩu**.

    `/health/ready` cố ý không yêu cầu đăng nhập để reverse proxy thăm dò được.
    Vì vậy mọi thứ nó in ra đều là công khai.
    """
    from fastapi.testclient import TestClient

    import server.routes.health as health
    from server.app import create_app

    monkeypatch.setattr(
        health, "_kiem_tra_csdl",
        lambda: (False, f"OperationalError: khong noi duoc toi {che_gia()}"),
    )

    app = create_app(env={"LTT_ENV": "development"})
    client = TestClient(app, base_url="https://testserver")
    r = client.get("/health/ready")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert "database" in body["reason"]
    assert MAT_KHAU_GIA not in r.text


def che_gia() -> str:
    """Chuỗi đã che, dùng trong test trên để mô phỏng đường lỗi thật."""
    from platform_core.db import che_mat_khau
    return che_mat_khau(URL_GIA)


# ── Bộ cài và sao lưu ─────────────────────────────────────────────────────────

def test_bo_cai_khong_ghi_de_mat_khau_csdl_da_co():
    """Chạy lại bộ cài không được đổi mật khẩu CSDL đang dùng.

    Bộ cài được thiết kế để chạy lại nhiều lần (mỗi lần cập nhật code đều chạy
    lại). Nếu nó sinh mật khẩu mới mỗi lần thì `app.env` và CSDL lệch nhau, và
    dịch vụ chết ngay sau khi cập nhật — đúng lúc người ta ít ngờ nhất.
    """
    text = (ROOT / "setup" / "2-cai-dat.ps1").read_text(encoding="utf-8")
    assert "LTT_DATABASE_URL=" in text, "bo cai phai ghi LTT_DATABASE_URL"
    assert "GIU NGUYEN" in text
    # Phai co nhanh kiem tra da ton tai truoc khi sinh moi.
    assert "if ($envText -match '(?m)^LTT_DATABASE_URL=')" in text, (
        "phai kiem tra LTT_DATABASE_URL da co truoc khi tao moi"
    )


def test_bo_cai_chay_migration_truoc_khi_khoi_dong_dich_vu():
    """`alembic upgrade head` phải chạy trước khi dịch vụ khởi động.

    Dịch vụ khởi động với lược đồ cũ sẽ không lỗi lúc khởi động — nó lỗi ở
    request đầu tiên chạm vào bảng thiếu cột. Lỗi lúc khởi động dễ truy hơn
    nhiều so với lỗi rải rác trong lúc phục vụ.
    """
    text = (ROOT / "setup" / "2-cai-dat.ps1").read_text(encoding="utf-8")
    vi_tri_migration = text.find("alembic upgrade head")
    vi_tri_khoi_dong = text.find("Head 'Khoi dong'")
    assert vi_tri_migration != -1, "bo cai phai chay alembic upgrade head"
    assert vi_tri_khoi_dong != -1
    assert vi_tri_migration < vi_tri_khoi_dong, (
        "migration phai chay TRUOC khi khoi dong dich vu"
    )


def test_ung_dung_khong_chay_bang_tai_khoan_superuser():
    """Ứng dụng dùng role riêng, không dùng `postgres`.

    Một lỗ hổng SQL injection với quyền superuser đọc được **mọi** database
    trên máy; với role riêng thì chỉ trong phạm vi của nó.
    """
    text = (ROOT / "setup" / "2-cai-dat.ps1").read_text(encoding="utf-8")
    assert "CREATE ROLE ltt_app" in text
    assert "postgresql+psycopg://ltt_app:" in text
    assert "postgresql+psycopg://postgres:" not in text


def test_sao_luu_dung_lai_khi_khong_lay_duoc_csdl():
    """`pg_dump` hỏng thì bản sao lưu phải DỪNG, không được ghi ra êm ru.

    Một bản sao lưu thiếu CSDL trông y hệt một bản đầy đủ — cùng tên file, cùng
    thư mục, cùng thông báo thành công. Nó chỉ lộ ra đúng lúc cần khôi phục,
    tức là lúc muộn nhất có thể.
    """
    text = (ROOT / "deploy" / "windows" / "backup.ps1").read_text(encoding="utf-8")
    assert "pg_dump" in text, "backup.ps1 phai sao luu ca PostgreSQL"

    # Lay nguyen khoi lenh xu ly PostgreSQL, khong phai doan sau lan xuat hien
    # dau tien cua chuoi "pg_dump" — cach do bat trung mot dong chu thich va
    # bao xanh nham.
    bat_dau = text.find("# ---- PostgreSQL")
    ket_thuc = text.find("if ($copied -eq 0)")
    assert bat_dau != -1 and ket_thuc > bat_dau, "khong tim thay khoi PostgreSQL"
    khoi = text[bat_dau:ket_thuc]

    assert khoi.count("throw") >= 2, (
        "ca hai duong hong (pg_dump loi, va khong tim thay pg_dump.exe) deu phai "
        "lam sao luu DUNG LAI, khong bo qua am tham"
    )
    assert "$env:PGPASSWORD = $null" in khoi, (
        "phai xoa PGPASSWORD khoi moi truong sau khi dung"
    )


def test_health_ready_van_xanh_khi_chua_cau_hinh_csdl(monkeypatch):
    """Chưa cấu hình CSDL chưa phải lỗi ở giai đoạn H1.1.

    Chưa phần nào của ứng dụng phụ thuộc CSDL. Bắt `/health/ready` trả 503 ngay
    bây giờ sẽ làm trình quản lý dịch vụ khởi động lại liên tục vì một phụ
    thuộc chưa ai dùng tới.

    **Test này phải được sửa cùng lúc với H1.2** — khi bảng người dùng vào,
    CSDL chết là lỗi thật.
    """
    from fastapi.testclient import TestClient

    from server.app import create_app

    monkeypatch.delenv("LTT_DATABASE_URL", raising=False)
    app = create_app(env={"LTT_ENV": "development"})
    client = TestClient(app, base_url="https://testserver")
    r = client.get("/health/ready")

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ready"
