"""test_1409 — cổng B không có route nào chuyển tiếp /slots hay /upstream/* ra ngoài (S1 §5)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_khong_route_slots_hay_upstream():
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import FakeUpstream, _cfg
    app = create_app(_cfg(), FakeUpstream())
    duong = {getattr(r, "path", "") for r in app.routes}
    assert not any("slots" in d for d in duong)
    assert not any(d.startswith("/upstream") for d in duong)
