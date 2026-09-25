"""P-A task A4 — hiện trường quan sát ĐÃ CÓ dữ liệu, chưa vẽ (25/09/2026).

Bối cảnh: `RunV3Node.attempt` và `RunV3.created_at`/`RunV3Event.created_at`
(`workflowApi.ts:518` trở xuống) đã có từ P9b, nhưng `RunV3Panel` chỉ vẽ
node_id/trạng thái/credit/lỗi — bỏ `attempt`, và không hề hiện thời điểm bắt
đầu/kết thúc/thời lượng của run. Đây KHÔNG phải trường mới: dữ liệu đã nằm
trong payload máy chủ trả về mỗi nhịp SSE, chỉ chưa được vẽ ra.

Hành vi đầy đủ (bấm chạy → thấy "Bắt đầu"/"Kết thúc"/"Lần N") do
`tests/RunV3Panel.test.tsx` (describe "task A4") kiểm qua React Testing
Library — tệp này chỉ là kiểm TĨNH nhanh, đối chứng rằng các trường đó THẬT
SỰ được đọc trong `RunV3Panel.tsx`.
"""
from __future__ import annotations

import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "agent-canvas" / "src"


def _nguon() -> str:
    return (SRC / "RunV3Panel.tsx").read_text(encoding="utf-8")


def test_cot_attempt_duoc_doc():
    assert "n.attempt" in _nguon()


def test_bat_dau_ket_thuc_doc_tu_created_at():
    nguon = _nguon()
    assert "run.created_at" in nguon
    # Kết thúc lấy từ sự kiện `seq` lớn nhất (`RunV3Event.created_at`), ⛔
    # không phải phần tử cuối mảng — xem chú thích `suKienCuoi` trong nguồn.
    assert "e.seq > max.seq" in nguon or "max.seq" in nguon


def test_thoi_luong_tinh_tu_hieu_hai_moc():
    nguon = _nguon()
    assert "function thoiLuong" in nguon
    assert "getTime()" in nguon


def test_khong_dung_toLocaleTimeString_de_khoi_troi_theo_mui_gio_test():
    """🔑 Đối chứng: định dạng giờ phải TẤT ĐỊNH (cắt chuỗi ISO), không qua
    `toLocaleTimeString`/`Intl` — máy chạy test và máy người dùng khác múi
    giờ sẽ làm một bài kiểm giờ-phút trở nên giả-ngẫu-nhiên."""
    nguon = _nguon()
    # Chuỗi "toLocaleTimeString" có thể còn trong CHÚ THÍCH giải thích vì sao
    # tránh nó — bài này chỉ cấm một LỜI GỌI thật (dấu `(` ngay sau tên hàm).
    assert ".toLocaleTimeString(" not in nguon
    assert "iso.slice(11, 19)" in nguon
