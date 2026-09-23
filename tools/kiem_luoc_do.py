"""Đối chiếu `Base.metadata` với lược đồ THẬT trong CSDL.

    python tools\\kiem_luoc_do.py              # đọc LTT_DATABASE_URL
    python tools\\kiem_luoc_do.py --im-lang    # chỉ in khi LỆCH (dùng trong deploy)

## Vì sao tệp này tồn tại

🔴 Sự cố đo được 23/09/2026. Giữa 01/09 23:04 và 06/09 08:51, `alembic_version`
   trên production bị đẩy qua **năm** revision mà không thực thi cái nào — bốn
   của `auto_scan_video`, một của `chatltt`. Cả năm bảng `asv_*` không bao giờ
   được tạo.

   Suốt **21 lượt deploy** sau đó, mỗi lượt đều in `[OK] Luoc do CSDL da o ban
   moi nhat`, vì dòng đó in vô điều kiện khi `alembic upgrade head` trả mã 0 —
   mà *"không có gì để làm"* cũng trả 0. Sự cố nằm im **20 ngày**, và nó lộ ra
   bởi một tai nạn (một vòng quét tài sản ra đời 04/09 được deploy và bắt đầu
   ném `UndefinedTable` vào log worker), chứ không bởi một phép kiểm.

⭐ Đây đúng khuôn **"hai chỗ khai cùng một điều mà không ai bắt khớp"**:
   `alembic_version` nói *"đã chạy tới đây"*, `information_schema` nói *"bảng
   này không tồn tại"*, và không ai đối chiếu hai bên. Cơ học thắng giao ước —
   nên ở đây là cơ học.

## Ba quyết định, và lý do từng cái

1. **Soi cả CỘT, không chỉ bảng.** Bản dò tay ngày 23/09 chỉ gom
   `create_table(...)` trong các revision, nên một revision chỉ `add_column`
   mà bị bỏ qua thì không ai thấy. *Bảng có mặt* không có nghĩa là *bảng đúng
   hình dạng*.

2. **KHÔNG lọc app đang tắt.** `auto_scan_video` khai `enabled=False`, nên
   không luồng nào chạm bảng của nó, nên không có gì kêu — đó chính là lý do
   sự cố sống được 20 ngày. Một phép kiểm bỏ qua app đang tắt sẽ bỏ qua đúng
   ca mà nó sinh ra để bắt.

3. **Thừa không phải lỗi.** CSDL có bảng/cột mà ORM không khai là chuyện bình
   thường (cột cũ chờ một bản gỡ dần, bảng của công cụ ngoài). Báo đỏ vì nó là
   cách biến một phép kiểm thật thành một phép kiểm bị bỏ qua.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
from dataclasses import dataclass, field

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


@dataclass(frozen=True)
class BangThieu:
    ten: str
    app: str = ""


@dataclass(frozen=True)
class CotThieu:
    bang: str
    ten: str
    app: str = ""


@dataclass(frozen=True)
class Lech:
    bang_thieu: list[BangThieu] = field(default_factory=list)
    cot_thieu: list[CotThieu] = field(default_factory=list)

    @property
    def dat(self) -> bool:
        return not self.bang_thieu and not self.cot_thieu

    def gom_theo_app(self) -> dict[str, int]:
        """`{app: số bảng thiếu}` — đọc ra thành một câu có nghĩa.

        "thiếu asv_run, asv_stage, …" đọc như rác của một app đang tắt.
        "app `auto_scan_video`: thiếu 5 bảng" thì không.
        """
        ra: dict[str, int] = {}
        for b in self.bang_thieu:
            ra[b.app or "?"] = ra.get(b.app or "?", 0) + 1
        return ra

    def bao_cao(self) -> str:
        if self.dat:
            return "DAT - luoc do that khop ban khai ORM"
        dong = [f"LECH - {len(self.bang_thieu)} bang thieu, "
                f"{len(self.cot_thieu)} cot thieu"]
        for app, so in sorted(self.gom_theo_app().items()):
            dong.append(f"  app {app}: thieu {so} bang")
        for b in self.bang_thieu:
            dong.append(f"    [bang] {b.ten}")
        for c in self.cot_thieu:
            dong.append(f"    [cot ] {c.bang}.{c.ten}")
        dong.append("")
        dong.append("  `alembic_version` co the van dang noi 'da chay toi head'.")
        dong.append("  !! Dung `alembic downgrade` roi chay lai ca chuoi: chuoi do")
        dong.append("     chua migration cua nhieu lan, chay lai se dung du lieu")
        dong.append("     that cua cac bang khac. Tao MOT revision moi chi tao")
        dong.append("     dung thu con thieu, co `downgrade` that.")
        # ⚠️ Chuỗi trả về phải THUẦN ASCII. Nó được in ra console Windows trong
        #    `setup/2-cai-dat.ps1`, nơi mã trang mặc định là cp1252 — một ký tự
        #    ngoài ASCII ở đây là một `UnicodeEncodeError` làm chết đúng phép
        #    kiểm sinh ra để phát hiện lỗi. `test_2800` chốt điều này.
        return "\n".join(dong)


def doi_chieu(*, khai: dict[str, set[str]], that: dict[str, set[str]],
              chu_bang: dict[str, str] | None = None) -> Lech:
    """So hai bản khai. **Thuần** — không CSDL, không ORM, nên test được rẻ.

    `khai` là thứ ORM nói phải có; `that` là thứ CSDL đang có. `chu_bang` ánh
    xạ bảng sang app để báo cáo gom được theo app.
    """
    chu = chu_bang or {}
    bang_thieu = [BangThieu(t, chu.get(t, "")) for t in sorted(khai)
                  if t not in that]
    cot_thieu = [CotThieu(t, c, chu.get(t, ""))
                 for t in sorted(khai) if t in that
                 for c in sorted(khai[t] - that[t])]
    return Lech(bang_thieu=bang_thieu, cot_thieu=cot_thieu)


def _khai_tu_orm() -> tuple[dict[str, set[str]], dict[str, str]]:
    """`Base.metadata` sau khi nạp MỌI model — kể cả của app đang tắt.

    Nạp theo `apps/*/tables.py` thay vì theo registry: registry lọc theo cờ
    `enabled`, và lọc ở đây là bỏ qua đúng ca cần bắt (xem quyết định 2).
    """
    import importlib

    import platform_core.models  # noqa: F401 - nap model nen tang
    from platform_core.db import Base

    chu: dict[str, str] = {}
    for tep in sorted((GOC / "apps").glob("*/tables.py")):
        app = tep.parent.name
        truoc = set(Base.metadata.tables)
        try:
            importlib.import_module(f"apps.{app}.tables")
        except Exception as exc:  # noqa: BLE001 - mot app hong khong duoc giet ca phep kiem
            print(f"  [!!] khong nap duoc apps.{app}.tables: {type(exc).__name__}")
            continue
        for ten in set(Base.metadata.tables) - truoc:
            chu[ten] = app
    khai = {ten: {c.name for c in b.columns}
            for ten, b in Base.metadata.tables.items()}
    return khai, chu


def _that_tu_csdl(url: str) -> dict[str, set[str]]:
    from sqlalchemy import create_engine, inspect

    may = create_engine(url)
    try:
        soi = inspect(may)
        return {t: {c["name"] for c in soi.get_columns(t)}
                for t in soi.get_table_names()}
    finally:
        may.dispose()


def main() -> int:
    ps = argparse.ArgumentParser(description=__doc__)
    ps.add_argument("--im-lang", action="store_true",
                    help="chi in khi LECH (dung trong duong deploy)")
    ps.add_argument("--url", default="", help="mac dinh doc LTT_DATABASE_URL")
    t = ps.parse_args()

    url = t.url or os.environ.get("LTT_DATABASE_URL", "")
    if not url:
        print("BO QUA - chua co LTT_DATABASE_URL")
        return 0

    khai, chu = _khai_tu_orm()
    lech = doi_chieu(khai=khai, that=_that_tu_csdl(url), chu_bang=chu)
    if lech.dat:
        if not t.im_lang:
            print(f"{lech.bao_cao()} ({len(khai)} bang)")
        return 0
    print(lech.bao_cao())
    # ⚠️ Tra 0 co chu y: lech luoc do KHONG duoc lam hong mot lan deploy dang
    #    chay. Viec cua no la NOI RA — thu ma 21 luot deploy truoc do khong
    #    lam. Dung ma thoat khac 0 la bien mot canh bao thanh mot su co.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
