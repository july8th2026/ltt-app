r"""mobile_qa.py — bộ khung đo mobile, lái bằng registry.

    python tools\mobile_qa.py kiem-ke [--ra ho_so.json]   # liet ke surface khach
    python tools\mobile_qa.py bang                        # du bang cho studio_dev

## Vì sao không gõ cứng danh sách app

`docs/MOBILE/01_MATRIX.md` phải nói đúng hiện trạng, mà hiện trạng đổi mỗi lần ai
đó thêm app hay lật `enabled`. Một danh sách chép tay **không có cách nào tự biết
nó đã cũ** — đúng cơ chế đã làm bảng trong `CLAUDE.md` nói sai năm lần. Nên chỗ
câu trả lời đến từ là `registry.discover()`, không phải một hằng số ở đây.

## Vì sao có lệnh `bang`

`tools/studio_dev.py` chỉ nạp bảng của `ltt_voice` — đúng với mục đích của nó.
Nhưng đo mobile thì đi qua **mọi** surface, và một sqlite thiếu `ommi_resource`
làm `/prompt-ai-ommi` trả 500. Ngày 05/09 lượt đo đầu tiên suýt ghi cái 500 ấy
vào báo cáo như một lỗi sản phẩm.

⛔ Đừng chữa bằng cách thêm `import apps.prompt_ai_ommi.tables` — đó là gõ cứng
   slug, và app thứ năm có `tables.py` sẽ lại rơi ra ngoài trong im lặng.
   `registry.load_app_tables()` đã làm đúng việc này cho cả Alembic lẫn server.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: sqlite dùng một lần của `studio_dev.py`. Không phải CSDL thật.
CSDL_DEV = GOC / "tmp" / "studio_dev" / "studio.db"


def kiem_ke() -> list[dict]:
    """Bản khai của mọi app, đọc lúc runtime từ registry."""
    from platform_core import registry

    ra = []
    for la in registry.discover():
        m = la.manifest
        ra.append({
            "slug": m.slug,
            "display": m.display_name,
            "route_prefix": m.route_prefix,
            "surface": m.surface,
            "lifecycle": m.lifecycle,
            "public": m.public,
            "enabled": m.enabled,
            "capabilities": list(m.capabilities),
            "job_types": list(m.job_types),
            "co_credit": m.credit_cost is not None,
        })
    ra.sort(key=lambda d: (d["surface"], d["slug"]))
    return ra


def du_bang() -> tuple[list[str], int]:
    """Dựng bảng của MỌI app vào sqlite của `studio_dev`. Trả (slug đã nạp, số bảng)."""
    os.environ["LTT_DATABASE_URL"] = "sqlite:///" + str(CSDL_DEV).replace("\\", "/")
    os.environ.setdefault("LTT_ENV", "development")
    os.environ.setdefault("LTT_SESSION_SECRET", "studio-dev-khong-bi-mat")

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry

    dbmod.reset_engine()
    da_nap = registry.load_app_tables()
    # `ltt_voice` có một module bảng thứ hai ngoài `tables.py`; registry chỉ
    # nạp `tables.py` theo hợp đồng, nên bảng dự án phải gọi tên ở đây.
    import apps.ltt_voice.tables_du_an  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    return da_nap, len(dbmod.Base.metadata.tables)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = ap.add_subparsers(dest="lenh", required=True)

    k = con.add_parser("kiem-ke", help="liet ke surface khach hang tu registry")
    k.add_argument("--ra", help="ghi JSON ra tep (mac dinh: in bang tom tat)")

    con.add_parser("bang", help="du bang cua moi app vao sqlite cua studio_dev")

    a = ap.parse_args(argv)

    if a.lenh == "kiem-ke":
        d = kiem_ke()
        if a.ra:
            pathlib.Path(a.ra).write_text(
                json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"da ghi {len(d)} app -> {a.ra}")
            return 0
        # In ASCII: stdout Windows la cp1252, mot dau tieng Viet lam vo ca lenh.
        print(f"{'slug':<16}{'surface':<10}{'life':<12}{'pub':<6}{'en':<6}route")
        for x in d:
            print(f"{x['slug']:<16}{x['surface']:<10}{x['lifecycle']:<12}"
                  f"{str(x['public']):<6}{str(x['enabled']):<6}{x['route_prefix']}")
        return 0

    if a.lenh == "bang":
        if not CSDL_DEV.exists():
            print(f"chua co {CSDL_DEV} — chay `python tools\\studio_dev.py` truoc")
            return 1
        da_nap, so = du_bang()
        print(f"app co tables.py: {da_nap}")
        print(f"tong bang: {so}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
