"""
db.py — kết nối PostgreSQL dùng chung cho cả nền tảng.

Vì sao lớp này tồn tại thay vì mỗi nơi tự tạo engine:

1. **Chuỗi kết nối chứa mật khẩu.** Nếu để nó đi lẫn vào thông báo lỗi hay log
   thì mật khẩu CSDL nằm trong `logs/service-err.log` — một file mà bất kỳ ai
   đọc được đĩa đều xem được. Mọi lỗi kết nối đi qua đây đều được **che mật
   khẩu trước khi ném ra**.
2. **Một engine cho cả tiến trình.** Mỗi engine mang theo một pool kết nối
   riêng; tạo engine trong hàm nghĩa là mỗi lần gọi lại mở một pool mới cho tới
   khi PostgreSQL từ chối vì hết chỗ.
3. **Đổi nơi cấu hình chỉ sửa một chỗ.** Chuỗi kết nối luôn đọc từ biến môi
   trường `LTT_DATABASE_URL`, không bao giờ viết cứng trong mã nguồn.

Ứng dụng **không** tự tạo bảng bằng `create_all()`. Mọi thay đổi lược đồ đi qua
Alembic — xem `alembic/README`. Lý do: `create_all()` chỉ tạo được bảng chưa
tồn tại, nó không biết cách đổi một bảng đã có dữ liệu, nên tới lần đổi lược đồ
thứ hai là bế tắc.
"""
from __future__ import annotations

import os
import re
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Lớp gốc của mọi model. Alembic dò lược đồ qua `Base.metadata`."""


class DatabaseNotConfigured(RuntimeError):
    """Chưa đặt `LTT_DATABASE_URL`."""


# Bắt mật khẩu trong chuỗi kết nối kiểu:  driver://user:MATKHAU@host/db
_MAT_KHAU = re.compile(r"(?P<truoc>://[^:/?#\[\]@]+:)(?P<mk>[^@/?#]+)(?P<sau>@)")


def che_mat_khau(chuoi: str) -> str:
    """Thay mật khẩu trong chuỗi kết nối bằng `***`.

    Dùng cho **mọi** chỗ chuỗi kết nối có thể hiện ra: thông báo lỗi, log,
    trang tình trạng. Giữ lại phần còn lại (host, cổng, tên CSDL) vì đó chính
    là thông tin cần để chẩn đoán.

    >>> che_mat_khau("postgresql+psycopg://ltt:sieubimat@127.0.0.1:5432/lttdb")
    'postgresql+psycopg://ltt:***@127.0.0.1:5432/lttdb'
    """
    if not chuoi:
        return chuoi
    return _MAT_KHAU.sub(lambda m: f"{m.group('truoc')}***{m.group('sau')}", chuoi)


def database_url(env: dict | None = None) -> str:
    """Chuỗi kết nối, đọc từ `LTT_DATABASE_URL`.

    Ném `DatabaseNotConfigured` khi chưa đặt — **không** tự đoán một giá trị
    mặc định. Một mặc định thầm lặng trỏ vào `localhost` sẽ khiến ứng dụng chạy
    được trên máy phát triển rồi hỏng trên máy chủ theo cách rất khó truy.
    """
    e = os.environ if env is None else env
    url = (e.get("LTT_DATABASE_URL") or "").strip()
    if not url:
        raise DatabaseNotConfigured(
            "Chưa đặt LTT_DATABASE_URL. Trên máy chủ nó nằm trong "
            "secrets\\app.env; ở máy phát triển thì đặt vào biến môi trường."
        )
    return url


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


# Giây chờ tối đa khi MỞ một kết nối mới. Không phải thời gian chạy câu lệnh.
#
# Vì sao phải có: không đặt thì driver chờ theo mặc định của hệ điều hành —
# trên Windows một địa chỉ bị tường lửa nuốt gói có thể treo hơn hai phút. Trong
# hai phút đó, worker phục vụ request nằm im. Người dùng chỉ thấy trang treo,
# và trình quản lý dịch vụ không thấy gì bất thường để khởi động lại.
#
# Phát hiện được vì một test kết nối tới cổng chết mất 130 giây.
CONNECT_TIMEOUT_S = 5


def _connect_args(url: str) -> dict:
    """Tham số riêng của driver. Chỉ PostgreSQL hiểu `connect_timeout`."""
    if url.startswith(("postgresql", "postgres")):
        return {"connect_timeout": CONNECT_TIMEOUT_S}
    return {}


def get_engine(url: str | None = None) -> Engine:
    """Engine dùng chung cho cả tiến trình. Tạo một lần rồi tái sử dụng."""
    global _engine, _session_factory
    if _engine is None:
        target = url or database_url()
        _engine = create_engine(
            target,
            connect_args=_connect_args(target),
            # Kết nối nằm không quá lâu sẽ bị tường lửa hoặc chính PostgreSQL
            # cắt âm thầm; pre_ping phát hiện kết nối chết và mở lại thay vì
            # ném lỗi vào mặt người dùng ở request đầu tiên sau khi máy rảnh.
            pool_pre_ping=True,
            pool_recycle=1800,
            # KHÔNG bật echo: nó in cả câu lệnh SQL kèm tham số ra log.
            echo=False,
            future=True,
        )
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False,
                                        class_=Session)
    return _engine


def get_session() -> Iterator[Session]:
    """Phiên làm việc cho một request. Dùng làm dependency của FastAPI.

    Tự đóng phiên khi request kết thúc, kể cả khi có lỗi. Không tự `commit` —
    nơi gọi phải chủ động, vì chỉ nơi gọi mới biết một chuỗi thao tác đã trọn
    vẹn hay chưa (đặc biệt với sổ credit ở H3).
    """
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def kiem_tra_ket_noi(url: str | None = None) -> tuple[bool, str]:
    """Thử kết nối. Trả về (được/không, lý do đã che mật khẩu).

    Dùng cho `/health/ready` và `tools/doctor.py`. Không bao giờ ném ra ngoài:
    người vận hành cần *lý do*, và cần trang tình trạng vẫn mở được để đọc lý
    do đó — đúng lúc mọi thứ đang hỏng.
    """
    try:
        target = url or database_url()
    except DatabaseNotConfigured as exc:
        return False, str(exc)

    try:
        engine = get_engine(target)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as exc:
        # Thông báo lỗi của driver thường nhúng nguyên chuỗi kết nối.
        return False, che_mat_khau(f"{type(exc).__name__}: {exc}")


def reset_engine() -> None:
    """Bỏ engine đang có. Dành cho test và cho việc đổi cấu hình lúc chạy."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
