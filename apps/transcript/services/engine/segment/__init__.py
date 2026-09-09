"""Dựng dòng thời gian — chuyển nguyên vẹn từ bot legacy.

⚠️ Phần tái xuất dưới đây **có trong bản gốc** và bản chuyển đầu tiên của tôi đã
   đánh rơi nó, chỉ giữ lại dòng docstring. Mã của App không vỡ vì nó nhập thẳng
   `from .engine.segment.core import make_timeline_v2` — nên khiếm khuyết này
   **không phép kiểm nào chạm tới**, và nó chỉ lộ ra khi bộ đối chiếu parity
   nhập đúng theo lối tài liệu của bot gốc.

   Bốn tên này là bề mặt công khai của gói ở bản gốc; giữ chúng thì mọi đoạn mã
   viết theo bot cũ chạy nguyên xi.

Cả `core` lẫn `timeline` đều thuần Python — nhập ở đây **không** kéo theo torch,
nên vòng quét registry vẫn nhẹ.
"""
from __future__ import annotations

from .core import make_segments, make_timeline, make_timeline_v2
from .timeline import analyze_segment_quality, get_timeline_statistics

__all__ = [
    "make_segments",
    "make_timeline",
    "make_timeline_v2",
    "analyze_segment_quality",
    "get_timeline_statistics",
]
