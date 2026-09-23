"""Phiên PostgreSQL phải nói giờ UTC — spec §5 (thời gian) + bài học `ttl()`.

## Vì sao một hằng số cấu hình lại đáng một tệp test

`platform_core/workflow` so sánh thời gian ở **hai** tầng: Python
(`datetime.now(timezone.utc)`) và SQL (`due_at <= now()`, `dong_co.py:196/214`).
Hai tầng chỉ khớp khi phiên CSDL cũng ở UTC. Máy chủ hiện để `timezone` mặc định
của cluster — một giá trị **không nằm trong kho này**, nên không ai đọc mã mà
biết được nó là gì, và đổi nó không để lại diff nào.

Lỗi nó gây ra không phải "sai 7 giờ" cho đều: `danh_thuc.hen()` ghi `due_at`
aware, còn một phiên ở `Asia/Ho_Chi_Minh` đọc `now()` ra một mốc khác — wakeup
đến hạn **sớm 7 giờ hoặc muộn 7 giờ** tuỳ chiều, và vòng động cơ chỉ đơn giản là
không nhặt nó. Không ngoại lệ, không log.
"""
from __future__ import annotations

import platform_core.db as dbmod


def test_phien_postgres_duoc_ghim_utc():
    args = dbmod._connect_args("postgresql+psycopg://u:p@127.0.0.1:5432/d")
    assert args.get("options") == "-c timezone=UTC", (
        "phien PostgreSQL phai ghim UTC — xem docstring tep nay")
    # Không được đánh rơi tham số cũ khi thêm tham số mới.
    assert args["connect_timeout"] == dbmod.CONNECT_TIMEOUT_S


def test_url_postgres_khong_co_duoi_driver_cung_duoc_ghim():
    assert dbmod._connect_args("postgres://u:p@h/d").get(
        "options") == "-c timezone=UTC"


def test_sqlite_KHONG_nhan_tham_so_cua_libpq():
    """🔑 Vế đối chứng. `options` là tham số **libpq**; nhét vào `pysqlite`
    làm `create_engine` ném `TypeError` — và nó sẽ ném ở MỌI test của kho,
    không riêng test này. Không có vế này thì một bản vá "thêm options cho
    mọi url" cũng làm hai bài trên xanh."""
    assert dbmod._connect_args("sqlite:///./x.db") == {}
