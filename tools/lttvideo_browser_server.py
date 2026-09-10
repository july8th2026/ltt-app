"""Bản `lttvideo` cô lập để kiểm giao diện bằng trình duyệt thật.

    python tools/lttvideo_browser_server.py [--port 8137]

In ra địa chỉ + email/mật khẩu để đăng nhập. Ctrl-C để dừng.

⛔ **Máy này LÀ máy chủ production** (`C:\\LTTPlatform` tồn tại) và cổng **8100
   đang phục vụ khách thật**. Nên bản kiểm dựng CSDL sqlite trong thư mục tạm và
   chạy ở cổng riêng — nó **không thể** chạm dữ liệu thật, không phải vì nhớ mà
   vì không có đường nào tới đó.

⭐ Vì sao cần trình duyệt chứ không thêm một phép kiểm: `CLAUDE.md` mục 5 —
   *"Test xanh không chứng minh trang hiển thị đúng"* — và ở kho này việc ấy đã
   **hai lần** bắt được lỗi mà bộ test không thấy.

🔴 `LTT_ENV="development"`, **không** phải `"local-server-test"`. Ở hai hồ sơ kia
   cookie phiên mang cờ `secure`; qua `http://127.0.0.1` trình duyệt bỏ cookie
   ấy, nên mọi trang bật về `/login` và ta soi nhầm cái vỏ. Bài học này đã ghi
   sẵn trong `tools/dev_portal_harness.py`; chép lại lý do chứ không chép mù.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EMAIL = "lttvideo-ui@example.com"
MAT_KHAU = "Browser-test-123"


def main() -> int:
    ap = argparse.ArgumentParser()
    # 8137: KHONG phai 8100 (production dang nghe o day), khong phai 8101
    # (dev_portal_harness), khong phai 8000 (kho BOT GEMINI dang phuc vu that).
    ap.add_argument("--port", type=int, default=8137)
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="lttvideo-ui-"))
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(tmp / 'ui.db').as_posix()}"
    os.environ["LTT_DATA_DIR"] = str(tmp / "data")

    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401,PLC0415
    from platform_core.db import Base, get_engine, get_session  # noqa: PLC0415

    Base.metadata.create_all(get_engine())

    from platform_core import credit  # noqa: PLC0415
    from platform_core.users import tao_nguoi_dung  # noqa: PLC0415

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU)
        user.is_verified = True
        # HAI cong, va ca hai deu doc CUNG mot cot `role`:
        #   - nen tang: `access_middleware.py:71` — `surface="admin"` trong
        #     manifest => 404 tru khi `role == "admin"`;
        #   - app:      `kha_nang.VAI_DUOC_DUNG`.
        # ⭐ Ban dau dong duoi con gan `user.vai`, va `mypy` bat: `"User" has no
        #    attribute "vai"`. Do la bang chung doc lap cho dung thu `A-4` tim
        #    ra — mot tu vung app tu che, khong co that trong CSDL.
        user.role = "admin"
        db.flush()
        credit.cap_tay(db, user.id, 5000, by="ui-harness")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from server.app import create_app  # noqa: PLC0415

    app = create_app(env={
        "LTT_ENV": "development",
        "LTT_SESSION_SECRET": "lttvideo-ui-harness-secret",
        "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp / "config.json"),
    })

    print(f"\n  http://127.0.0.1:{args.port}/lttvideo")
    print(f"  {EMAIL} / {MAT_KHAU}\n  tmp: {tmp}\n", flush=True)

    import uvicorn  # noqa: PLC0415

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
