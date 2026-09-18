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

_MARKER = re.compile(r"(?:QX|QY|ZT|KP|QN|QD)\d{7,}")


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


# ---- #27148 đúng công thức gốc: nạp pool bằng nhiều hội thoại dài KHÁC nhau (có lượt tool),
#      rồi bắn đồng thời nhiều hội thoại mới ⇒ nhiều slot bị LRU-evict cùng lúc.

def _engine_dem(che_do: str):
    """Như `_engine` nhưng đếm số request đang bay đồng thời và ghi lại thân request."""
    import time as _t
    dem = {"dang": 0, "max": 0, "than": []}
    khoa = threading.Lock()
    trang_thai = {"truoc": ""}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n))
            with khoa:
                dem["dang"] += 1
                dem["max"] = max(dem["max"], dem["dang"])
                dem["than"].append(body)
            _t.sleep(0.15)
            chu = json.dumps(body["messages"])
            thay = _MARKER.findall(chu)
            with khoa:
                if che_do == "ro" and trang_thai["truoc"]:
                    tra_loi = trang_thai["truoc"]
                else:
                    tra_loi = thay[-1] if thay else "NONE"
                if thay:
                    trang_thai["truoc"] = thay[-1]
                dem["dang"] -= 1
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for goi in ({"choices": [{"delta": {"content": tra_loi}}]},
                        {"choices": [{"delta": {}, "finish_reason": "stop"}], "timings": {"cache_n": 0}}):
                self.wfile.write(b"data: " + json.dumps(goi).encode() + b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, dem


@pytest.mark.parametrize("che_do, ma", [("sach", 0), ("ro", 3)])
def test_dong_thoi_lru_27148_bat_ro_va_im_khi_sach(tmp_path, che_do, ma):
    srv, dem = _engine_dem(che_do)
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        kq = K.chay(base, "qwen38-api", 2, ["dong_thoi_lru_27148"], tmp_path / "ra.jsonl", doc_ky_tu=400)
        assert K.ma_thoat(kq) == ma
    finally:
        srv.shutdown()


def test_dong_thoi_lru_27148_that_su_dong_thoi_va_co_luot_tool(tmp_path):
    srv, dem = _engine_dem("sach")
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        K.chay(base, "qwen38-api", 1, ["dong_thoi_lru_27148"], tmp_path / "ra.jsonl", doc_ky_tu=400)
        assert dem["max"] >= 2                      # trigger gốc: nhiều slot evict cùng lúc
        assert len(dem["than"]) >= 4 + 2            # nạp pool > np=3 hội thoại, rồi bắn song song
        vai = [m["role"] for m in dem["than"][0]["messages"]]
        assert vai[:4] == ["system", "user", "assistant", "tool"]
        assert dem["than"][0]["messages"][2].get("tool_calls")
        dong = [json.loads(x) for x in (tmp_path / "ra.jsonl").read_text("utf-8").splitlines()]
        assert {d["pha"] for d in dong} == {"nap", "dong_thoi"}  # cả lượt nạp cũng được chấm
    finally:
        srv.shutdown()


def test_so_marker_voi_moi_marker_cua_ca_luot_chay(tmp_path):
    """Rò từ phiên của KỊCH BẢN KHÁC / VÒNG TRƯỚC cũng phải bị bắt (sổ marker toàn cục)."""
    so = K.SoMarker()
    a, b = so.moi("QX"), so.moi("ZT")
    assert so.cua_nguoi_khac({b}) == {a}
    assert so.cua_nguoi_khac(set()) == {a, b}


def test_engine_sach_tra_dung_ma_cua_chinh_minh_khong_bi_tinh_la_ro(tmp_path):
    """Hồi quy 18/09: sổ marker toàn cục từng tính mã CỦA CHÍNH phiên (câu trả lời đúng) là rò ở `dong_thoi`."""
    srv, _ = _engine_dem("sach")
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        kq = K.chay(base, "qwen38-api", 2, list(K.KICH_BAN), tmp_path / "ra.jsonl", doc_ky_tu=400)
        assert K.ma_thoat(kq) == 0, kq
        dong = [json.loads(x) for x in (tmp_path / "ra.jsonl").read_text("utf-8").splitlines()]
        assert all(d.get("marker_minh") for d in dong if d["kich_ban"] in ("dong_thoi", "dong_thoi_lru_27148"))
    finally:
        srv.shutdown()
