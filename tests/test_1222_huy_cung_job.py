"""Task 4.3 (LTT LLM Dual-Model) — hủy CỨNG một lượt + một dòng sổ mỗi lượt.

Đây là nửa còn dở của chương trình Multi-Job: **nửa hủy của T10** và **toàn bộ
T11**. Đo được trước khi bắt đầu: `grep` không tìm thấy `/v1/huy`, `499`, hay
`HuyError` ở bất cứ đâu trong `llm_gateway/` hay `platform_core/` — tức **hôm nay
không có gì hủy được một lượt LLM đang bay**.

🔴 BA MỆNH ĐỀ PHẢI CHỨNG MINH, và mỗi cái có một đối chứng ngược chiều:

  1. **Kết nối tới nhà cung cấp ĐÓNG ≤ 2 giây** sau khi job bị hủy — đo bằng một
     máy chủ HTTP **thật** giữ kết nối, và chính máy chủ ấy nói ra nó thấy khách
     đi lúc nào. Đối chứng: tắt luồng canh ⇒ kết nối sống tới hết ⇒ phép đo ĐỎ.
  2. **499 ⇒ `HuyError`**, một lớp **không** phải `CongVlmError` và **không** phải
     `BanError`. Đối chứng: cùng đường ấy với 500 ⇒ `CongVlmError` **và**
     `danh_dau_loi` được gọi — chứng minh con mắt do thám hoạt động, nên việc nó
     im lặng ở ca 499 là một sự thật chứ không phải một phép kiểm hỏng.
  3. **Một dòng sổ mỗi lượt**, và lượt bị hủy có đúng **một** dòng `huy=true`.

⛔ HỦY KHÔNG ĐƯỢC LÀ MỘT CÁI CHẾT. Không `taskkill`, không `/unload` của
   llama-swap (đường ấy không mang tên model nên nó nhả cả hai card — L-17),
   không chạm slot của ai khác. Đóng kết nối **là** cơ chế: llama.cpp nhả slot
   ≤1 s sau khi client rời (`server-context.cpp:39`, `server-queue.cpp:607-617`).

⚠️ VÌ SAO CÓ MÁY CHỦ SOCKET THẬT TRONG TỆP NÀY. Thứ phải chứng minh là *"cái
   socket kia đóng"*, và một bản giả Python không có socket nào — nó chỉ có thể
   **kể lại** rằng nó đã được gọi. Đúng lớp sai mà kho này đã ghi thành luật
   ("đọc thứ đại diện thay vì đọc thứ thật"). Ba phép kiểm dưới đây dùng
   `http.server` trên cổng 0, loopback, tuổi thọ vài giây.
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

M38 = "qwen38-api"

#: Trần của mệnh đề 1. Luồng canh thăm mỗi 1 giây (`jobs.NHIP_CANH_S`), nên 2
#: giây là "một nhịp cộng một khoảng dư rộng rãi", không phải một con số đẹp.
TRAN_DONG_S = 2.0


# ── Máy chủ giả: giữ kết nối, và BIẾT khách đi lúc nào ───────────────────────

class _SoHieu:
    """Thứ máy chủ giả quan sát được. Đây là **phép đo**, không phải lời kể."""

    def __init__(self) -> None:
        self.bat_dau = threading.Event()
        self.khach_di = False
        self.giay_toi_luc_khach_di: float | None = None
        self.header_nhan: dict = {}
        self.duong_huy: list[dict] = []
        self.khoa = threading.Lock()


def _handler(so: _SoHieu, giu_s: float, than_tra: bytes):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):       # im lặng: bộ test không cần access log
            pass

        def do_POST(self):               # noqa: N802 - ten cua BaseHTTPRequestHandler
            n = int(self.headers.get("Content-Length") or 0)
            tho = self.rfile.read(n) if n else b""
            # ⭐ `/v1/huy` KHÔNG được giữ. Đây chính là đường mà máy A dùng để
            #    bảo máy B thôi sinh chữ; giữ nó lại là tự chặn đường hủy của
            #    mình, và phép kiểm sẽ đo một sự cố do chính nó dựng ra.
            if self.path.endswith("/v1/huy"):
                with so.khoa:
                    so.duong_huy.append(json.loads(tho or b"{}"))
                self._tra(200, b'{"huy":true}')
                return

            with so.khoa:
                so.header_nhan = {k.lower(): v for k, v in self.headers.items()}
            t0 = time.monotonic()
            so.bat_dau.set()

            # Giữ kết nối, vừa giữ vừa **nghe** xem khách còn đó không.
            self.connection.settimeout(0.05)
            het = t0 + giu_s
            while time.monotonic() < het:
                try:
                    if self.connection.recv(1, socket.MSG_PEEK) == b"":
                        so.khach_di = True
                        break
                except (TimeoutError, socket.timeout):
                    continue
                except OSError:
                    so.khach_di = True
                    break
            if so.khach_di:
                so.giay_toi_luc_khach_di = time.monotonic() - t0
                return                       # khách đi rồi thì không trả lời ai
            self.connection.settimeout(None)
            self._tra(200, than_tra)

        def _tra(self, ma: int, than: bytes) -> None:
            try:
                self.send_response(ma)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(than)))
                self.end_headers()
                self.wfile.write(than)
            except OSError:
                pass                          # khách đã đi giữa chừng: bình thường

    return H


#: Thân trả về đủ `usage` + `timings` — dòng sổ phải bóc được **cả hai**.
THAN_DU_SO = json.dumps({
    "model": M38,
    "choices": [{"message": {"content": "xin chao"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1200, "completion_tokens": 34},
    "timings": {"cache_n": 900, "prompt_per_second": 850.5,
                "predicted_per_second": 59.9},
}).encode()


@contextmanager
def may_chu_giu(giu_s: float = 30.0, than: bytes = THAN_DU_SO):
    """Một nhà cung cấp giả **có socket thật**, giữ kết nối `giu_s` giây."""
    so = _SoHieu()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _handler(so, giu_s, than))
    luong = threading.Thread(target=srv.serve_forever, daemon=True)
    luong.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}", so
    finally:
        srv.shutdown()
        srv.server_close()
        luong.join(timeout=5.0)


# ══ 1. Lớp vận chuyển của CỔNG: `upstream.json` hủy được giữa chừng ═════════

def test_upstream_json_dong_duoc_giua_chung_va_bao_MA_DA_HUY():
    """🔴 MỆNH ĐỀ 1 ở tầng thấp nhất: cái socket kia **thật sự** đóng.

    Trước bản này `HttpxUpstream.json` gọi `httpx.request`, thứ dựng một client
    bên trong rồi vứt đi — không ai cầm được tay nắm nào, nên khoảng thời gian
    một lượt đồng bộ đang chạy là một vùng **không hủy được**.
    """
    from llm_gateway import so_luot as SL
    from llm_gateway.upstream import MA_DA_HUY, HttpxUpstream

    with may_chu_giu(giu_s=30.0) as (url, so):
        luot = SL.Luot(ma="r-1")
        moc = SL.SO_LUOT.set(luot)
        try:
            def _cat():
                so.bat_dau.wait(5.0)
                time.sleep(0.2)
                luot.huy()

            threading.Thread(target=_cat, daemon=True).start()
            t0 = time.monotonic()
            ma, _than = HttpxUpstream(url).json(
                "POST", "/v1/chat/completions", body={"a": 1}, timeout=30.0)
            mat = time.monotonic() - t0
        finally:
            SL.SO_LUOT.reset(moc)

    assert ma == MA_DA_HUY, (
        f"ma {ma} — mot luot HUY bi phan loai thanh loi mang/het gio; may A doc "
        f"502 la `CongVlmError` va nam lan la khoa chet (D-005)")
    assert mat < TRAN_DONG_S, f"mat {mat:.2f}s de dong ket noi"
    assert so.khach_di, "may chu gia KHONG thay khach di — socket van con mo"
    assert so.giay_toi_luc_khach_di is not None
    assert so.giay_toi_luc_khach_di < TRAN_DONG_S


def test_doi_chung_KHONG_huy_thi_ket_noi_song_toi_HET():
    """⭐ Đối chứng của phép trên: cùng máy chủ, cùng đường, **không** hủy.

    Không có nó thì "đóng ≤2 giây" là một câu không đo được — một máy chủ trả lời
    ngay lập tức cũng cho ra đúng con số ấy.
    """
    from llm_gateway.upstream import HttpxUpstream

    with may_chu_giu(giu_s=1.2, than=THAN_DU_SO) as (url, so):
        t0 = time.monotonic()
        ma, than = HttpxUpstream(url).json("POST", "/v1/chat/completions",
                                           body={"a": 1}, timeout=30.0)
        mat = time.monotonic() - t0

    assert ma == 200 and b"xin chao" in than
    assert not so.khach_di, "khach di ma khong ai bao di — doi chung vo nghia"
    assert mat >= 1.0, (
        f"chi mat {mat:.2f}s — may chu gia khong he giu ket noi, nen phep kiem "
        f"o tren xanh vi mot ly do khac")


# ══ 2. Cửa `/v1/huy` của cổng ═══════════════════════════════════════════════

def _app_cong(up):
    from llm_gateway.api import create_app
    from tests.test_250_llm_gateway import _cfg, _tt_ranh

    return create_app(_cfg(models_mo=(M38,), np=4),
                      up, trong_tai=_tt_ranh())


class UpstreamGiuTrongTien:
    """Thượng nguồn giả **có ghi tay nắm vào sổ lượt** — như bản thật.

    ⚠️ Nó không có socket, và tệp này không giả vờ rằng nó có: phép đo socket
       nằm ở mục 1 với máy chủ thật. Bản này chỉ để đo **cửa HTTP** của cổng —
       mã trả về, bộ đếm, dòng sổ — mà không phải dựng cả llama-swap.
    """

    def __init__(self, than: bytes = THAN_DU_SO):
        self.than = than
        self.bat_dau = threading.Event()
        self.rieng: dict[str, bytes] = {}

    def json(self, method, path, *, body=None, timeout=60.0):
        from llm_gateway import so_luot as SL
        from llm_gateway.upstream import MA_DA_HUY

        if path in self.rieng:
            return 200, self.rieng[path]
        if not path.startswith("/v1/"):
            return 200, b"{}"
        mo = threading.Event()
        SL.ghi_nhan(mo.set)              # "dong ket noi" ~ danh thuc
        self.bat_dau.set()
        da_dong = mo.wait(timeout=5.0)
        if da_dong and SL.da_huy():
            return MA_DA_HUY, b"huy theo yeu cau"
        return 200, self.than

    def stream(self, method, path, *, body=None, timeout=900.0):
        return 200, "text/event-stream", iter([b"data: x\n\n"])


def test_POST_v1_huy_cat_luot_dang_bay_va_luot_ay_tra_499(caplog):
    """🔴 Cửa T10: `/v1/huy` ⇒ đóng thượng nguồn ⇒ lượt đang bay trả **499**.

    ⛔ 499 chứ không 502: máy A đọc 502 thành `CongVlmError` ⇒ `danh_dau_loi` ⇒
       năm lần là `APIKEY_ERROR`, thứ **không tự hồi**. Và không 429: với model
       nội bộ `THU_TU_PROVIDER` chỉ có MỘT phần tử, nên "bận ⇒ đi tiếp" là cạn
       danh sách ⇒ `KhongCoProviderNao`, che mất nguyên nhân thật.
    """
    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO, logger="llm_gateway.so")
    up = UpstreamGiuTrongTien()
    app = _app_cong(up)
    c_chay, c_huy = TestClient(app), TestClient(app)
    ket: dict = {}

    def _goi():
        r = c_chay.post("/v1/chat/completions",
                        headers={"X-LTT-Request-Id": "r-huy-1"},
                        json={"model": M38,
                              "messages": [{"role": "user", "content": "hi"}]})
        ket["ma"] = r.status_code
        ket["than"] = r.json()

    t = threading.Thread(target=_goi, daemon=True)
    t.start()
    assert up.bat_dau.wait(5.0), "luot gia khong bao gio bat dau"

    r = c_huy.post("/v1/huy", json={"request_id": "r-huy-1"})
    assert r.status_code == 200, r.text
    assert r.json()["huy"] is True and r.json()["so_cua_dong"] >= 1

    t.join(timeout=5.0)
    assert ket.get("ma") == 499, f"luot bi huy tra {ket.get('ma')}"
    assert ket["than"]["ly_do"] == "huy theo yeu cau"

    dong = _dong_so(caplog)
    assert len(dong) == 1, f"{len(dong)} dong so cho MOT luot: {dong}"
    assert dong[0]["huy"] is True
    assert dong[0]["ma"] == "r-huy-1"
    assert dong[0]["ma_http"] == 499
    # ⛔ `None`, khong phai 0: thuong nguon chet TRUOC khi `usage` ve.
    assert dong[0]["token_vao"] is None and dong[0]["so_dang_tin"] is False


def test_doi_chung_khong_goi_v1_huy_thi_luot_di_toi_het_va_huy_false(caplog):
    """⭐ Đối chứng: cùng lượt, cùng cổng, **không** gọi `/v1/huy`."""
    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO, logger="llm_gateway.so")
    up = UpstreamGiuTrongTien()
    c = TestClient(_app_cong(up))

    # Không ai đóng ⇒ `mo.wait(5.0)` hết giờ ⇒ thượng nguồn trả 200 bình thường.
    r = c.post("/v1/chat/completions",
               headers={"X-LTT-Request-Id": "r-ok-1"},
               json={"model": M38, "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200, r.text

    dong = _dong_so(caplog)
    assert len(dong) == 1 and dong[0]["huy"] is False, dong


def test_v1_huy_ma_khong_co_luot_nao_thi_404_khong_phai_200():
    """⛔ 404, không 200. Một bên hủy nhận 200 sẽ tin là đã cắt được — và "tưởng
    đã cắt" là đúng trạng thái làm người ta thôi kiểm lại."""
    from fastapi.testclient import TestClient

    c = TestClient(_app_cong(UpstreamGiuTrongTien()))
    assert c.post("/v1/huy", json={"request_id": "khong-co"}).status_code == 404
    assert c.post("/v1/huy", json={}).status_code == 400


# ══ 3. Dòng sổ: một lượt một dòng, và nó mang đủ số ═════════════════════════

def _dong_so(caplog) -> list[dict]:
    return [json.loads(r.getMessage()) for r in caplog.records
            if r.name == "llm_gateway.so"]


def test_dong_so_mang_du_so_cua_mot_luot_that(caplog):
    """🔴 MỘT DÒNG, VÀ NÓ LÀ MỘT SỔ SÁCH.

    Trường bắt buộc: mã lượt · model · UUID card · token vào/cache/ra · prefill &
    decode tok/s · TTFT · mã kết thúc · có bị hủy không.

    ⚠️ `gpu` được phép `None` khi `gpu_may_b.json` không giải được vai của model —
       một tệp danh tính thiếu không được làm sập một lượt đang tính tiền. Nhưng
       **chỉ** trường ấy: mọi trường còn lại phải có mặt, vì một dòng thiếu số
       còn tệ hơn không có dòng nào.
    """
    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO, logger="llm_gateway.so")
    up = UpstreamGiuTrongTien()
    up.rieng["/v1/chat/completions"] = THAN_DU_SO   # tra ngay, khong giu
    c = TestClient(_app_cong(up))
    r = c.post("/v1/chat/completions",
               headers={"X-LTT-Request-Id": "r-so-1"},
               json={"model": M38, "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200, r.text

    dong = _dong_so(caplog)
    assert len(dong) == 1, dong
    d = dong[0]
    assert set(d) >= {"ma", "model", "gpu", "giao_thuc", "stream", "ma_http",
                      "ket_thuc", "huy", "ttft_s", "token_vao", "token_cache",
                      "token_ra", "prefill_tps", "decode_tps", "so_dang_tin"}
    assert d["ma"] == "r-so-1" and d["model"] == M38
    assert d["token_vao"] == 1200 and d["token_cache"] == 900 and d["token_ra"] == 34
    assert d["prefill_tps"] == 850.5 and d["decode_tps"] == 59.9
    assert d["ket_thuc"] == "stop" and d["huy"] is False
    assert d["so_dang_tin"] is True
    assert isinstance(d["ttft_s"], float)


def test_dong_so_van_ra_khi_luot_bi_TU_CHOI_truoc_thuong_nguon(caplog):
    """Một lượt 404/413/429 vẫn có dòng — nếu không, sổ thiếu hẳn một cửa.

    ⛔ Và các số của nó là `null` chứ không phải 0: không có lượt model nào chạy,
       nên "0 token" sẽ là một khẳng định sai chứ không phải một chỗ trống.
    """
    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO, logger="llm_gateway.so")
    c = TestClient(_app_cong(UpstreamGiuTrongTien()))
    r = c.post("/v1/chat/completions",
               headers={"X-LTT-Request-Id": "r-404"},
               json={"model": "khong-ton-tai",
                     "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 404

    dong = _dong_so(caplog)
    assert len(dong) == 1 and dong[0]["ma_http"] == 404
    assert dong[0]["ket_thuc"] == "tu_choi"
    assert dong[0]["token_vao"] is None and dong[0]["so_dang_tin"] is False


def test_dong_so_cua_luot_STREAM_khong_bia_ra_token(caplog):
    """SSE đi qua cổng **nguyên xi**, nên cổng không có `usage` để mà ghi.

    ⛔ Ghi `0` ở đây là bịa. Dòng vẫn ra (TTFT + mã kết thúc là thứ cổng **tự đo
       được**), nhưng `so_dang_tin=False` nói thẳng rằng token phải hỏi nơi khác.
    """
    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO, logger="llm_gateway.so")
    c = TestClient(_app_cong(UpstreamGiuTrongTien()))
    r = c.post("/v1/chat/completions",
               headers={"X-LTT-Request-Id": "r-sse"},
               json={"model": M38, "stream": True,
                     "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200 and b"data: x" in r.content

    dong = _dong_so(caplog)
    assert len(dong) == 1, dong
    assert dong[0]["stream"] is True and dong[0]["so_dang_tin"] is False
    assert dong[0]["token_ra"] is None


# ══ 4. Máy A: 499 ⇒ `HuyError`, và nó KHÔNG phải lỗi của khoá ═══════════════

def test_499_thanh_HuyError_va_HuyError_khong_phai_CongVlmError():
    """🔴 MỆNH ĐỀ 2. Quan hệ **kiểu** là thứ quyết định tiền ở đây.

    `dieu_phoi` bắt `CongVlmError` rồi gọi `api_pool.danh_dau_loi()`. Nếu
    `HuyError` là con của nó thì mọi lượt hủy đi thẳng vào đường ấy — và năm lần
    là `APIKEY_ERROR`, thứ không tự hồi.
    """
    from platform_core.llm.cong_vlm import (BanError, CongVlm, CongVlmError,
                                            HuyError, VuotNganSachError)

    assert not issubclass(HuyError, CongVlmError)
    assert not issubclass(HuyError, BanError)
    assert not issubclass(HuyError, VuotNganSachError)

    cong = CongVlm(goi=lambda *a, **k: (499, {"ly_do": "huy theo yeu cau"}))
    with pytest.raises(HuyError):
        cong.chat(model=M38, messages=[{"role": "user", "content": "hi"}])


class _KeyGia:
    id = "k-1"
    base_url = ""
    provider = "ltt_llm"


def _do_tham_dieu_phoi(monkeypatch, ma_cong: int, than_cong):
    """Dựng `dieu_phoi.goi` với một provider duy nhất trả `ma_cong`.

    Trả `(loi, so_lan_danh_dau_loi, so_lan_chon_key)` — hai con số cuối là con
    mắt do thám: chúng phân biệt "không cascade" với "không có gì để cascade".
    """
    from platform_core import api_keys, api_pool, providers
    from platform_core.llm import dieu_phoi

    dem = {"loi": 0, "chon": 0, "thanh_cong": 0}

    def _chon_key(db, **kw):
        dem["chon"] += 1
        return _KeyGia()

    monkeypatch.setattr(api_pool, "chon_key", _chon_key)
    # ⚠️ `**kw` CHỨ KHÔNG LIỆT KÊ THAM SỐ. Bản giả ở đây đóng vai *"có một lần
    #    đánh dấu lỗi xảy ra"*, không phải vai *"chữ ký của `danh_dau_loi` hôm
    #    nay". Bản cũ khai `lambda db, key` và nó ĐỎ ngay khi L-09 thêm
    #    `http_status=` — không phải vì mã sai mà vì bản giả chặt hơn thứ nó
    #    thay thế. Đây là lần THỨ HAI trong cùng một phiên (lần đầu:
    #    `executor.run(..., ma_luot=)` làm đỏ 19 phép kiểm).
    monkeypatch.setattr(api_pool, "danh_dau_loi",
                        lambda db, key, **kw: dem.__setitem__(
                            "loi", dem["loi"] + 1))
    monkeypatch.setattr(api_pool, "danh_dau_thanh_cong",
                        lambda db, key, **kw: dem.__setitem__(
                            "thanh_cong", dem["thanh_cong"] + 1))
    monkeypatch.setattr(api_keys, "lay_credential", lambda db, key: "tok")
    # Hai provider CÙNG họ giao thức, để "cascade" ở đối chứng thật sự đi tới
    # lời gọi thứ hai chứ không dừng ở nhánh "chưa biết giao thức".
    monkeypatch.setattr(dieu_phoi, "PROVIDER_OPENAI", ("ltt_llm", "ltt_llm_2"))
    monkeypatch.setattr(providers, "da_ngung", lambda pid: False)
    monkeypatch.setattr(
        providers, "get",
        lambda pid: type("P", (), {"base_url": "http://127.0.0.1:1"})())
    monkeypatch.setattr(
        dieu_phoi, "_goi_openai",
        lambda base, cred, than, t, *, ma_luot="": _tra_cong(ma_cong, than_cong))

    loi = None
    try:
        dieu_phoi.goi(None, messages=[{"role": "user", "content": "hi"}],
                      thu_tu_provider=["ltt_llm", "ltt_llm_2"],
                      model_theo_provider={"ltt_llm": M38, "ltt_llm_2": M38},
                      ma_luot="r-x")
    except Exception as e:                                      # noqa: BLE001
        loi = e
    return loi, dem


def _tra_cong(ma: int, than):
    """Chạy đúng `CongVlm.chat` trên một mã cổng cho trước — không giả kết quả.

    ⭐ Đi qua `CongVlm` thật chứ không `raise` thẳng: thứ đang được kiểm là
       **cách cổng phân loại một mã HTTP**, nên tự ném ra lớp mong muốn sẽ là
       phép kiểm tự trả lời câu hỏi của chính nó.
    """
    from platform_core.llm.cong_vlm import CongVlm

    return CongVlm(goi=lambda *a, **k: (ma, than)).chat(
        model=M38, messages=[{"role": "user", "content": "hi"}])


def test_dieu_phoi_gap_499_thi_KHONG_cascade_va_KHONG_danh_dau_loi_khoa(
        monkeypatch):
    """🔴 MỆNH ĐỀ 2 ở tầng điều phối: ba cái "không" cùng lúc."""
    from platform_core.llm.cong_vlm import HuyError

    loi, dem = _do_tham_dieu_phoi(monkeypatch, 499, {"ly_do": "huy theo yeu cau"})

    assert isinstance(loi, HuyError), f"499 ra {type(loi).__name__}"
    assert dem["loi"] == 0, "mot luot HUY da danh dau loi cho khoa (D-005)"
    assert dem["chon"] == 1, (
        f"da thu {dem['chon']} provider — mot luot bi huy khong duoc thu lai o "
        f"noi khac: no se chay mot luot khong ai cho, va tinh tien cho no")


def test_doi_chung_500_VAN_danh_dau_loi_khoa_va_VAN_cascade(monkeypatch):
    """⭐ Đối chứng của phép trên, và nó chứng minh **con mắt do thám còn sống**.

    Không có nó thì `dem["loi"] == 0` ở phép trên cũng đúng khi `danh_dau_loi`
    chưa bao giờ nằm trên đường đi — tức một số 0 không có đối chứng, thứ mà kho
    này đã ghi thành luật là "không phải một phát hiện".
    """
    loi, dem = _do_tham_dieu_phoi(monkeypatch, 500, {"loi": "vo"})

    assert dem["loi"] == 2, f"danh_dau_loi goi {dem['loi']} lan"
    assert dem["chon"] == 2, "500 phai cascade sang provider sau"
    assert type(loi).__name__ == "KhongCoProviderNao"


# ══ 5. Cửa job: luồng canh `is_cancelled()` ⇒ đóng kết nối ⇒ `JobCancelled` ══

class _CtxGia:
    """`JobContext` tối thiểu: chỉ những gì `jobs.handle` thật sự chạm tới."""

    def __init__(self, job_id: str, huy_sau_s: float | None):
        self.job_id = job_id
        self._huy_luc = (time.monotonic() + huy_sau_s) if huy_sau_s else None
        self.so_lan_hoi = 0

    def progress(self, *a, **k):
        pass

    def provider_dispatched(self, *a, **k):
        pass

    def provider_rejected(self, *a, **k):
        pass

    def is_cancelled(self) -> bool:
        self.so_lan_hoi += 1
        return self._huy_luc is not None and time.monotonic() >= self._huy_luc


def _phien_csdl_rong(monkeypatch) -> None:
    """Cho `jobs.handle` một phiên CSDL rỗng — KHÔNG đầu độc module nạp sau.

    🔴 BẪY ĐÃ DÍNH (17/09/2026, gộp phương án C): `platform_core.job_runner` và
       `platform_core.llm.admission` viết `from platform_core.db import get_session`
       ở ĐẦU MODULE, tức chép tên hàm vào module của chúng LÚC NẠP. `jobs.handle`
       nạp `job_runner` bên TRONG thân hàm. Nếu lần nạp đầu tiên của tiến trình
       rơi vào lúc `platform_core.db.get_session` đang bị vá thành `iter([None])`,
       `job_runner.get_session` giữ bản giả MÃI MÃI — monkeypatch hoàn lại
       `platform_core.db` nhưng không biết bản chép kia. Phép kiểm sau trong cùng
       worker gọi `_chay_mot_job` ⇒ `claim(db=None)` ⇒ `AttributeError`.
       Chỉ lộ dưới `-n 6` khi xdist xếp test này làm người nạp `job_runner` đầu
       tiên của worker (chạy riêng thì `test_job_bi_huy_thi_ket_noi...` đã nạp
       trước) — nên trông như "xung đột với test_272".
    ⭐ Nạp mọi module có bản chép TRƯỚC khi vá, rồi mới vá.
    """
    import platform_core.job_runner  # noqa: F401  (chép get_session lúc nạp)
    import platform_core.llm.admission  # noqa: F401  (như trên)

    monkeypatch.setattr("platform_core.db.get_session",
                        lambda: iter([None]), raising=False)


def _vao_ltt_llm(monkeypatch, url: str):
    """Cho `features.chay` gọi **`dieu_phoi._goi_openai` thật** tới `url`.

    ⭐ Không giả `_goi_openai`: nó là nơi hàm đóng được ghi vào hai sổ và là nơi
       `X-LTT-Request-Id` được gắn. Giả nó đi thì phép kiểm dưới đây không còn đo
       đường hủy nữa — nó đo bản giả của chính mình.
    """
    from types import SimpleNamespace

    from apps.ltt_llm import features
    from platform_core.db import get_session
    from platform_core.llm import dieu_phoi

    def _chay(db, params, *, timeout_s=300.0, on_dispatch=None, on_rejected=None,
              ma_luot=""):
        kq = dieu_phoi._goi_openai(
            url, "", {"model": M38,
                      "messages": [{"role": "user", "content": "hi"}]},
            30.0, ma_luot=ma_luot)
        return SimpleNamespace(as_result=lambda: {"noi_dung": kq.noi_dung})

    monkeypatch.setattr(features, "chay", _chay)
    # `jobs.handle` mở một phiên CSDL rồi đưa xuống `features.chay`; bản giả ở
    # trên không dùng tới `db`, nên một phiên rỗng là đủ và ta không kéo cả CSDL
    # vào một phép kiểm đo **socket**.
    _phien_csdl_rong(monkeypatch)
    return get_session


def test_job_bi_huy_thi_ket_noi_toi_nha_cung_cap_dong_trong_2s(monkeypatch):
    """🔴 MỆNH ĐỀ 1, ở đúng cửa mà chương trình nói tới: luồng canh của job.

    Và nó kiểm luôn nửa còn lại của đường hủy: máy A **nói với máy B** bằng
    `POST /v1/huy`. Đóng socket A→B là chưa đủ — thân của một endpoint `def` ở
    cổng chạy trong threadpool và không nhận tin khách đã đi.
    """
    from apps.ltt_llm import jobs as ltt_jobs
    from platform_core.job_runner import JobCancelled

    with may_chu_giu(giu_s=30.0) as (url, so):
        _vao_ltt_llm(monkeypatch, url)
        ctx = _CtxGia("j-1", huy_sau_s=0.3)
        t0 = time.monotonic()
        with pytest.raises(JobCancelled):
            ltt_jobs.handle({"model": M38,
                             "messages": [{"role": "user", "content": "hi"}]}, ctx)
        mat = time.monotonic() - t0

    assert mat < TRAN_DONG_S + 1.5, f"mat {mat:.2f}s moi bo cuoc"
    assert so.khach_di, "nha cung cap gia KHONG thay khach di — socket con mo"
    assert so.giay_toi_luc_khach_di < TRAN_DONG_S, (
        f"dong sau {so.giay_toi_luc_khach_di:.2f}s")
    # Máy A đã nói với máy B, và nói đúng tên lượt.
    assert so.duong_huy == [{"request_id": "job-j-1"}], so.duong_huy
    # ⛔ Va KHONG gui `X-Conversation-Id` len thuong nguon (bang chung cong dong §1).
    assert so.header_nhan.get("x-ltt-request-id") == "job-j-1"
    assert "x-conversation-id" not in so.header_nhan


def test_doi_chung_tat_luong_canh_thi_ket_noi_SONG_toi_het(monkeypatch):
    """⭐ ĐỐI CHỨNG mà plan đòi: không có luồng canh ⇒ kết nối sống tới hết.

    `ngat.chay_canh_ngat` tắt hẳn luồng canh khi `ngat_chua is None` — tức đây
    đúng là hành vi **trước** Task 4.3, không phải một bản dựng lại.
    """
    from apps.ltt_llm import jobs as ltt_jobs

    with may_chu_giu(giu_s=1.2) as (url, so):
        _vao_ltt_llm(monkeypatch, url)
        ctx = _CtxGia("j-2", huy_sau_s=0.3)
        ctx.is_cancelled = None                      # tat luong canh
        t0 = time.monotonic()
        kq = ltt_jobs.handle({"model": M38,
                              "messages": [{"role": "user", "content": "hi"}]}, ctx)
        mat = time.monotonic() - t0

    assert kq == {"noi_dung": "xin chao"}
    assert not so.khach_di, "khong co luong canh ma ket noi van dong — vo ly"
    assert mat >= 1.0, f"chi mat {mat:.2f}s — may chu gia khong he giu"
    assert so.duong_huy == []


def test_499_tu_cong_cung_thanh_JobCancelled_chu_khong_phai_job_ERROR(monkeypatch):
    """Cổng đã cắt trước khi luồng canh kịp thấy ⇒ vẫn là "đã hủy", không "lỗi".

    ⛔ Nếu `HuyError` thoát ra khỏi handler thì `_chay_handler` rơi vào nhánh
       `except Exception` ⇒ `jobq.fail()` ⇒ job mang trạng thái `error` **và** ba
       lượt thử lại — tức GPU chạy thêm ba lượt cho một người đã bỏ đi.
    """
    from types import SimpleNamespace

    from apps.ltt_llm import features, jobs as ltt_jobs
    from platform_core.job_runner import JobCancelled
    from platform_core.llm.cong_vlm import CongVlm

    def _chay(db, params, *, timeout_s=300.0, on_dispatch=None, on_rejected=None,
              ma_luot=""):
        kq = CongVlm(goi=lambda *a, **k: (499, {"ly_do": "huy"})).chat(
            model=M38, messages=[{"role": "user", "content": "hi"}])
        return SimpleNamespace(as_result=lambda: {"noi_dung": kq.noi_dung})

    monkeypatch.setattr(features, "chay", _chay)
    _phien_csdl_rong(monkeypatch)
    with pytest.raises(JobCancelled):
        ltt_jobs.handle({"model": M38}, _CtxGia("j-3", huy_sau_s=None))


# ══ 6. Sổ sách: hoàn trọn, nhả lease, và hủy SAU KHI XONG là vô hại ═════════

@pytest.fixture()
def db_huy(tmp_path, monkeypatch):
    """SQLite sạch + phiên, cùng khuôn `test_1209.db_job`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "huy.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    # Canh bẫy `_phien_csdl_rong`: bản chép `get_session` phải là hàm thật.
    import platform_core.job_runner as jr
    import platform_core.llm.admission as adm
    for mod in (jr, adm):
        assert mod.get_session is dbmod.get_session, (
            f"{mod.__name__}.get_session bi dau doc boi mot ban va luc nap — "
            f"xem _phien_csdl_rong")
    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090()
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _tool_co_lease(job_type: str):
    from platform_core.registry import AdmissionModel, ToolSpec

    return ToolSpec(
        name="thu.huy", job_type=job_type,
        description="tool vut di, chi de job nay gianh mot lease",
        params_schema={"text": {"type": "string"}}, returns={"output": "text"},
        admission_theo_model={"*": AdmissionModel("tn_huy_thu", 1, 0)})


def test_job_bi_huy_giua_chung_HOAN_TRON_va_NHA_LEASE(db_huy, monkeypatch,
                                                      app_thu):
    """🔴 Sổ sách của một lượt hủy: credit về đủ, lease biến mất, job `cancelled`.

    ⚠️ Người hủy ở đây là **đúng cái seam của endpoint**: `server/api/jobs.py:524`
       làm `jobq.cancel(db, job)` rồi `credit.hoan(...)` trong **cùng một
       transaction** (một hoàn tiền commit mà không kèm việc hủy — hoặc ngược lại
       — là một sổ không khớp với thực tế). Tệp này gọi đúng hai hàm ấy từ một
       luồng khác thay vì dựng cả lớp HTTP + scope + CSRF, thứ đã có bộ test riêng.
    """
    import platform_core.job_runner as jr
    from platform_core import credit
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import (JOB_CANCELLED, CreditEntry,
                                      ExecutionLease, Job)
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG, bao_dam_user

    bao_dam_user(db_huy, "u-huy")
    credit.cap_tay(db_huy, "u-huy", 100, by="test")
    db_huy.commit()
    so_du_dau = credit.so_du(db_huy, "u-huy")

    monkeypatch.setattr(jr, "_tool_cua_job", _tool_co_lease)

    bat_dau = threading.Event()
    thay_lease: dict = {}

    def _handler(params, ctx):
        import platform_core.db as dbmod
        g = dbmod.get_session()
        s = next(g)
        try:
            thay_lease["n"] = s.query(ExecutionLease).count()
        finally:
            s.close()
        bat_dau.set()
        # Luồng canh thật của `jobs.handle`: `ngat.chay_canh_ngat` thăm
        # `is_cancelled()` mỗi 1 giây rồi ném `KhachNgat`. Ở đây không có máy B
        # nào để đóng, nên lời gọi "model" chỉ là một khoảng chờ dài.
        from platform_core.job_runner import JobCancelled
        from platform_core.llm import ngat
        try:
            return ngat.chay_canh_ngat(lambda: time.sleep(20.0),
                                       ngat_chua=ctx.is_cancelled, nhip_s=0.2)
        except ngat.KhachNgat:
            raise JobCancelled() from None

    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _handler)

    job = submit_with_credit(db_huy, user_id="u-huy", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "x" * 250})
    db_huy.commit()
    ma_job = job.id
    da_giu = credit.so_da_giu(db_huy, ma_job)
    assert da_giu > 0, "khong giu credit nao — phep kiem hoan tien se vo nghia"

    def _huy():
        import platform_core.db as dbmod
        bat_dau.wait(10.0)
        time.sleep(0.3)
        g = dbmod.get_session()
        s = next(g)
        try:
            j = s.get(Job, ma_job)
            if jr.jobq.cancel(s, j):
                credit.hoan(s, j.user_id, j.id)
            s.commit()
        finally:
            s.close()

    t = threading.Thread(target=_huy, daemon=True)
    t.start()
    assert jr._chay_mot_job("w-huy") is True
    t.join(timeout=10.0)

    db_huy.expire_all()
    j = db_huy.get(Job, ma_job)
    assert j.status == JOB_CANCELLED, f"job o trang thai {j.status}"
    # Hoàn TRỌN: số dư về đúng chỗ cũ, không hơn không kém.
    assert credit.so_du(db_huy, "u-huy") == so_du_dau
    # ⚠️ KHÔNG đo bằng `so_da_giu() == 0`: hàm ấy chỉ cộng bút toán `hold`, nên
    #    sau một lần hoàn nó VẪN trả `held` — sổ này là **chỉ ghi thêm**, không
    #    ai xoá dòng giữ đi cả. Thứ nói lên "đã hoàn" là số dư và dòng hoàn.
    assert credit._da_ket_so(db_huy, ma_job), "job huy ma chua ket so"
    # ⛔ VÀ CHỈ MỘT LẦN. `_chay_handler` gọi `_hoan_credit` trên đường
    #    `JobCancelled`; nếu nó không idempotent thì đây là hai bút toán hoàn cho
    #    một khoản giữ — một sai lệch sổ, trên một sổ đang chạy thật.
    hoan = db_huy.query(CreditEntry).filter(
        CreditEntry.job_id == ma_job, CreditEntry.delta > 0).count()
    assert hoan == 1, f"{hoan} but toan hoan cho MOT lan giu"
    assert thay_lease.get("n") == 1, "handler chay ma khong giu lease nao"
    assert db_huy.query(ExecutionLease).count() == 0, "lease chua duoc nha"


def test_huy_SAU_KHI_job_da_xong_la_vo_hai_khong_hoan_lan_hai(db_huy, app_thu):
    """Một lệnh hủy đến muộn không được biến thành một khoản hoàn thứ hai.

    ⛔ Hai cửa cùng phải đóng, và phép kiểm đòi cả hai: `jobs.cancel` từ chối một
       job đã kết thúc (`status not in (queued, running)`), **và** `credit.hoan`
       không tạo bút toán mới khi không còn gì đang giữ. Chỉ có cửa thứ nhất thì
       một đường khác gọi thẳng `hoan()` vẫn ghi được.
    """
    import platform_core.job_runner as jr
    from platform_core import credit
    from platform_core import jobs as jobq
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import JOB_DONE, CreditEntry, Job
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG, bao_dam_user

    bao_dam_user(db_huy, "u-muon")
    credit.cap_tay(db_huy, "u-muon", 100, by="test")
    db_huy.commit()

    job = submit_with_credit(db_huy, user_id="u-muon", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "x" * 250})
    db_huy.commit()
    ma_job = job.id
    assert jr._chay_mot_job("w-muon") is True
    db_huy.expire_all()
    j = db_huy.get(Job, ma_job)
    assert j.status == JOB_DONE, f"job o trang thai {j.status}"

    truoc = credit.so_du(db_huy, "u-muon")
    so_but_toan = db_huy.query(CreditEntry).filter(
        CreditEntry.job_id == ma_job).count()

    assert jobq.cancel(db_huy, j) is False, (
        "huy duoc mot job da xong — cua thu nhat khong dong")
    credit.hoan(db_huy, j.user_id, j.id)          # cua thu hai, goi thang
    db_huy.commit()

    assert credit.so_du(db_huy, "u-muon") == truoc
    assert db_huy.query(CreditEntry).filter(
        CreditEntry.job_id == ma_job).count() == so_but_toan


# ══ 7. Chốt tĩnh: không có đường giết nào len vào đường hủy ═════════════════

def test_duong_huy_khong_chua_taskkill_hay_unload():
    """⛔ Mệnh đề **dương** về hình dạng đường hủy, không phải một lời hứa.

    Hủy đúng là đóng một kết nối. `taskkill` giết cả tiến trình `llama-server`
    (mọi slot, mọi khách); `/unload` của llama-swap **không mang tên model** nên
    nó nhả cả hai card (L-17) — tức hủy lượt của mình bằng cách giết lượt của
    người khác. Cả hai đều không được có mặt trên đường này.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent
    for ten in ("llm_gateway/so_luot.py", "platform_core/llm/huy_luot.py",
                "apps/ltt_llm/jobs.py"):
        van = (goc / ten).read_text(encoding="utf-8")
        # Bỏ chú thích: cả hai chữ được nhắc tới trong lời giải thích *vì sao
        # không dùng*, và một bộ dò quét văn bản thô sẽ trừng phạt đúng việc ấy.
        ma = "\n".join(d for d in van.splitlines()
                       if not d.lstrip().startswith("#"))
        ma = ma.split('"""')[0] + '"""'.join(ma.split('"""')[2:] or [""])
        assert "taskkill" not in ma.lower(), ten
        assert "/unload" not in ma, ten
