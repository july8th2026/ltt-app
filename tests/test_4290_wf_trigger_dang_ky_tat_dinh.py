"""`trigger.SO_DANG_KY` phải TẤT ĐỊNH — không phụ thuộc ai import cái gì trước
(làn `wft`, 25/09).

## Sự cố đã đo

`tests/test_960_wf_artifact_va_trigger.py::test_moi_loai_trigger_la_MOT_mo_dun`
đỏ khi chạy CHUNG cụm, xanh khi chạy MỘT MÌNH:

    python -m pytest tests/test_1795_wf_trigger_cron.py \
        tests/test_960_wf_artifact_va_trigger.py::test_moi_loai_trigger_la_MOT_mo_dun

Gốc rễ: `platform_core/workflow/poll_connector.py` gọi
`trigger.dang_ky(PiecePoll())` LÚC IMPORT (hiệu ứng phụ), và trước 25/09 không
có nơi nào ép việc import đó xảy ra — `PIECE_POLL` chỉ có mặt trong
`trigger.SO_DANG_KY` nếu một mô-đun KHÁC (`ban_trigger.py`, hoặc test nào gọi
`ban_trigger.ban_den_han`/`ban_su_kien`) đã chạy trước trong cùng tiến trình
pytest. Đúng khuôn "sổ đăng ký dùng chung" mà `nut_loi/__init__.py` đã giải
cho `_SO` — chỉ khác chỗ `trigger.py` chưa có bộ nhận import tương tự.

Vá: `platform_core/workflow/__init__.py` giờ tự `import poll_connector` lúc
gói được chạm tới — bất kỳ `from platform_core.workflow import <bất_kỳ>` nào
cũng chạy `__init__.py` TRƯỚC, nên `PIECE_POLL` luôn được đăng ký. Hai bài
dưới đây khoá lại: (1) sổ giống nhau bất kể thứ tự import, đo bằng tiến trình
Python RIÊNG cho mỗi thứ tự — không phải mô phỏng trong cùng một tiến trình,
vì đó chính là thứ làm sự cố gốc ẩn đi; (2) mỗi loại trigger có ĐÚNG MỘT chỗ
gọi `dang_ky()`, để loại thứ 8 không tái diễn sự cố này.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


def _chay_python(ma: str) -> str:
    """Chạy `ma` trong một tiến trình Python MỚI, trả về dòng in cuối cùng.

    ⚠️ Tiến trình mới, không `importlib.reload` trong tiến trình đang chạy
       pytest: reload không xoá sạch trạng thái mà các mô-đun khác đã import
       (`sys.modules` của các mô-đun phụ thuộc vẫn trỏ tới bản cũ), nên nó
       không tái hiện được đúng thứ tự import "sạch" của một tiến trình pytest
       thật khi CI chọn thứ tự file khác.
    """
    kq = subprocess.run(
        [sys.executable, "-c", ma], cwd=str(GOC),
        capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, f"stdout={kq.stdout!r} stderr={kq.stderr!r}"
    return kq.stdout.strip().splitlines()[-1]


def test_so_dang_ky_giong_nhau_du_import_truoc_hay_sau():
    """Đo bằng HAI tiến trình riêng — không phải giả định."""
    chi_trigger = _chay_python(
        "from platform_core.workflow import trigger\n"
        "print(sorted(trigger.SO_DANG_KY))")

    poll_truoc = _chay_python(
        "from platform_core.workflow import poll_connector\n"
        "from platform_core.workflow import trigger\n"
        "print(sorted(trigger.SO_DANG_KY))")

    # ⭐ Chạm gói qua MỘT mô-đun khác hẳn poll_connector/trigger (ban_trigger
    #    kéo theo poll_connector qua đường riêng của NÓ, nhưng phép này cố ý
    #    đi qua mô-đun không hề nhắc PIECE_POLL, để chứng minh __init__.py
    #    của GÓI mới là thứ ép — không phải một import may mắn nào khác).
    qua_mo_dun_khac = _chay_python(
        "from platform_core.workflow import khoa_idem\n"
        "from platform_core.workflow import trigger\n"
        "print(sorted(trigger.SO_DANG_KY))")

    assert chi_trigger == poll_truoc == qua_mo_dun_khac
    assert "PIECE_POLL" in chi_trigger, (
        "trigger.SO_DANG_KY thieu PIECE_POLL ngay ca khi CHI import trigger "
        "mot minh -- __init__.py cua platform_core.workflow khong con ep "
        "dang ky no nua")


def test_moi_loai_trigger_dang_ky_dung_MOT_cho():
    """Chống loại thứ 8 tái diễn: mỗi `kind` chỉ có ĐÚNG một lời gọi `dang_ky()`
    trong toàn bộ mã nguồn `platform_core/workflow/` — nếu có hai, một trong
    hai là mã chết hoặc một cuộc ghi đè im lặng (`SO_DANG_KY[loai.kind] = loai`
    không cảnh báo khi trùng `kind`, khác `nut_loi._SO` đã có `LoiNut` chặn
    trùng `type`)."""
    from platform_core.workflow import trigger as trigger_mod

    thu_muc = Path(trigger_mod.__file__).resolve().parent
    theo_kind: dict[str, list[str]] = {}

    for tep in sorted(thu_muc.glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"), filename=str(tep))
        for node in ast.walk(cay):
            if not isinstance(node, ast.Call):
                continue
            # Trong CHÍNH `trigger.py`, lời gọi là tên trần `dang_ky(...)`
            # (không tiền tố module). Ở mô-đun khác (`poll_connector.py`), nó
            # qua `_trigger.dang_ky(...)`. Cả hai đều là "đăng ký vào sổ của
            # `trigger`" — ⛔ không đếm `dang_ky()` của sổ KHÁC (vd
            # `nut_loi.dang_ky`, `canh.dang_ky`): những cái đó có `func.value`
            # trỏ tới thứ không phải `trigger`/`_trigger`, loại ở nhánh dưới.
            if isinstance(node.func, ast.Name) and node.func.id == "dang_ky":
                if tep.name != "trigger.py":
                    continue  # tên trần ở tệp khác không phải sổ trigger
            elif (isinstance(node.func, ast.Attribute)
                    and node.func.attr == "dang_ky"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in ("trigger", "_trigger")):
                pass
            else:
                continue
            # `dang_ky(_KhongCoLich(_k))` trong vòng `for _k in (...)`,
            # và `dang_ky(_TheoLich())` / `dang_ky(PiecePoll())` trực tiếp —
            # cả hai đều là MỘT lời gọi nguồn cho một hoặc nhiều `kind`.
            theo_kind.setdefault(str(tep.name), []).append(
                ast.dump(node.args[0]) if node.args else "?")

    # ⭐ Không đếm bằng SO_DANG_KY (đó là KẾT QUẢ, phép này kiểm NGUỒN):
    # `trigger.py` có 4 lời gọi nguồn (`for _k in (...)` là MỘT lời gọi nguồn
    # cho CẢ BA kind `MANUAL`/`API`/`WEBHOOK` của `_KhongCoLich`, cộng
    # `_TheoLich`/`_TheoCron`/`_SuKien` — 3+3 = 6 kind từ 4 lời gọi),
    # `poll_connector.py` có 1 (`PIECE_POLL`) — tổng 6 kind từ 5 lời gọi.
    tong_lenh_goi = sum(len(v) for v in theo_kind.values())
    assert tong_lenh_goi == 5, (
        f"so loi goi dang_ky() nguon thay doi ({tong_lenh_goi}, tung tep: "
        f"{theo_kind}) -- neu them mot loai trigger moi, cap nhat phep nay "
        f"CUNG LUC voi so lieu that, dung de no tu xanh")
    assert set(theo_kind) == {"trigger.py", "poll_connector.py"}, (
        f"mot loai trigger dang dang ky ngoai hai tep da biet: {theo_kind} "
        f"-- kiem no co duoc `platform_core/workflow/__init__.py` import "
        f"khong, neu khong no la mot mo-dun CHET (xem docstring __init__.py)")
