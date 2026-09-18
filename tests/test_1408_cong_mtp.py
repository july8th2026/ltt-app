"""test_1408 — phân loại lỗi MTP theo S1 §4.1 và luật cổng §4.3."""
from tools import cong_mtp as C


def test_rong_co_tool_call_la_ok():
    assert C.phan_loai({"text": "", "tool_calls": [{"name": "x"}], "finish": "tool_calls", "reasoning": ""},
                       max_tokens=2000, dap_an=None, schema=None, doi_chung_dung=None) == "ok"


def test_rong_vi_suy_nghi_tieu_het_tran_la_giai_thich_duoc():
    assert C.phan_loai({"text": "", "finish": "length", "reasoning": "x" * 1900, "reasoning_tokens": 1900},
                       max_tokens=2000, dap_an=None, schema=None, doi_chung_dung=None) == "rong_giai_thich"


def test_rong_stop_la_khong_giai_thich():
    assert C.phan_loai({"text": "  ", "finish": "stop", "reasoning": "abc", "reasoning_tokens": 3},
                       max_tokens=2000, dap_an=None, schema=None, doi_chung_dung=None) == "rong_khong_giai_thich"


def test_sai_dap_an_khi_doi_chung_dung_la_hong():
    assert C.phan_loai({"text": "Đáp án là 41", "finish": "stop"}, max_tokens=2000, dap_an="42", schema=None,
                       doi_chung_dung=True) == "hong_noi_dung"


def test_sai_dap_an_khi_doi_chung_cung_sai_khong_tinh_hong():
    assert C.phan_loai({"text": "41", "finish": "stop"}, max_tokens=2000, dap_an="42", schema=None,
                       doi_chung_dung=False) == "ok"


def test_schema_khong_parse_duoc_la_hong():
    assert C.phan_loai({"text": "{\"ten\": 1", "finish": "stop"}, max_tokens=2000, dap_an=None,
                       schema={"type": "object", "required": ["ten"]}, doi_chung_dung=None) == "hong_noi_dung"


def test_ky_tu_thay_the_hoac_lap_la_hong():
    assert C.phan_loai({"text": "ab�cd", "finish": "stop"}, max_tokens=2000, dap_an=None, schema=None,
                       doi_chung_dung=None) == "hong_noi_dung"


def test_cong_dat_chi_khi_moi_bo_dem_bang_0():
    kq = [{"loai": "ok"}] * 10 + [{"loai": "rong_giai_thich"}]
    assert C.cong(kq, deadlock=0, ro_slot=0)["dat"] is True
    assert C.cong(kq + [{"loai": "rong_khong_giai_thich"}], deadlock=0, ro_slot=0)["dat"] is False
    assert C.cong(kq, deadlock=1, ro_slot=0)["dat"] is False


def test_tran_im_lang_khop_admission():
    from platform_core.llm.admission import TRAN_IM_LANG_S
    assert C.TRAN_IM_LANG_S == TRAN_IM_LANG_S


def test_bo_de_du_nam_nhom_va_tat_dinh():
    a, b = C.bo_de(), C.bo_de()
    assert {x["w"] for x in a} == {"W1", "W2", "W3", "W4", "W5"}
    assert [x["than"] for x in a] == [x["than"] for x in b]


def test_doc_doi_chung_hai_phan_ba(tmp_path):
    p = tmp_path / "e3.jsonl"
    rows = [{"ma_bai": "vi-01", "dung": True}, {"ma_bai": "vi-01", "dung": True}, {"ma_bai": "vi-01", "dung": False},
            {"ma_bai": "en-01", "dung": False}, {"ma_bai": "en-01", "dung": True}, {"ma_bai": "w1-0", "dung": None}]
    p.write_text("\n".join(__import__("json").dumps(r) for r in rows), encoding="utf-8")
    assert C.doc_doi_chung(p) == {"vi-01": True, "en-01": False}


def _engine_gia(rong: bool):
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"llamacpp:requests_processing 0\n")

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msg = {"content": "" if rong else "Tokyo Ha Noi 45000 XYLOPHONE-4417"}
            if body.get("tools") and not rong:
                msg = {"content": "", "tool_calls": [{"function": {"name": "tra_thoi_tiet",
                                                                    "arguments": "{\"thanh_pho\": \"Da Nang\"}"}}]}
            du = json.dumps({"choices": [{"message": msg, "finish_reason": "stop"}], "usage": {}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(du)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_chay_engine_tra_rong_thi_truot_cong(tmp_path, monkeypatch):
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    srv = _engine_gia(rong=True)
    try:
        kq = C.chay(f"http://127.0.0.1:{srv.server_address[1]}", "m", 3, 1, tmp_path / "ra.jsonl")
        assert kq["dat"] is False and kq["rong_khong_giai_thich"] == kq["tong"] > 0
    finally:
        srv.shutdown()
