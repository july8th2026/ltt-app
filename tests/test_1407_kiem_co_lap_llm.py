"""test_1407 — canary cô lập chéo phiên phải BẮT được rò cài sẵn và im với engine sạch."""
from __future__ import annotations

import json
import pathlib
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kiem_co_lap_llm as K  # noqa: E402

_MARKER = re.compile(r"(?:QX|QY|ZT|KP)\d{7,}")


def _engine(che_do: str):
    """Engine giả nói SSE chat-completions. `ro` = trả marker của REQUEST TRƯỚC."""
    trang_thai = {"truoc": ""}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            than = json.dumps([{"id": 0, "is_processing": False}]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(than)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n))
            chu = json.dumps(body["messages"])
            thay = _MARKER.findall(chu)
            if che_do == "ro":
                tra_loi = f"Earlier I saw {trang_thai['truoc']}" if trang_thai["truoc"] else "NONE"
            else:
                tra_loi = thay[-1] if thay and "What is the secret" in chu else "NONE"
            if thay:
                trang_thai["truoc"] = thay[-1]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for goi in (
                {"choices": [{"delta": {"content": tra_loi}}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}],
                 "timings": {"prompt_n": 10, "cache_n": 0}},
            ):
                self.wfile.write(b"data: " + json.dumps(goi).encode() + b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.mark.parametrize("che_do, ma", [("sach", 0), ("ro", 3)])
def test_canary_phan_biet_sach_va_ro(tmp_path, che_do, ma):
    srv = _engine(che_do)
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        kq = K.chay(base, "qwen38-api", 4, ["tuan_tu_khong_lien_quan", "xoay_vuot_slot"],
                    tmp_path / "ra.jsonl", doc_ky_tu=400)
        assert K.ma_thoat(kq) == ma
        dong = [json.loads(x) for x in (tmp_path / "ra.jsonl").read_text("utf-8").splitlines()]
        assert dong and all("finish_reason" in d and "reasoning_ky_tu" in d for d in dong)
    finally:
        srv.shutdown()


def test_engine_chet_la_khong_do_duoc(tmp_path):
    kq = K.chay("http://127.0.0.1:9", "qwen38-api", 1, ["tuan_tu_khong_lien_quan"],
                tmp_path / "ra.jsonl", doc_ky_tu=200)
    assert K.ma_thoat(kq) == 2


def test_tim_ro_khong_duong_tinh_gia_voi_so_ngan():
    assert K.tim_ro("QX12345678", "code QX12345678 here")
    assert not K.tim_ro("QX12345678", "QX1234567 and 12345678")
