"""test_1452 — gộp TTFT + nạp nguội từ sổ lượt cổng B (R-16). Thuần, không mạng."""
from __future__ import annotations

import json

from tools import tong_hop_ttft_b as T


def _d(luc, model="qwen38-api", stream=True, ttft=1.0, ma=200):
    return (f"{luc},123 INFO llm_gateway.so " + json.dumps(
        {"model": model, "stream": stream, "ttft_s": ttft, "ma_http": ma, "huy": False}) + "\n")


def test_ttl_doc_tu_yaml_that():
    assert T.ttl_yaml() > 0


def test_doc_so_bo_dong_la_va_loc_theo_gio():
    dong = [_d("2026-09-18 10:00:00"), "2026-09-18 10:00:01,000 INFO llm_gateway.api khac\n",
            "rac\n", _d("2026-09-18 11:00:00")]
    assert len(T.doc_so(dong)) == 2
    import datetime as dt
    assert len(T.doc_so(dong, dt.datetime(2026, 9, 18, 10, 30))) == 1


def test_phan_vi_nearest_rank():
    xs = list(range(1, 101))
    assert T.phan_vi(xs, 95) == 95
    assert T.phan_vi(xs, 50) == 50
    assert T.phan_vi([7.0], 95) == 7.0
    assert T.phan_vi([], 95) is None


def test_stream_va_dong_bo_khong_gop():
    """TTFT đồng bộ = cả lượt (api.py) ⇒ gộp với stream là trộn hai đại lượng."""
    luot = T.doc_so([_d("2026-09-18 10:00:00", stream=True, ttft=1.0),
                     _d("2026-09-18 10:00:05", stream=False, ttft=40.0)])
    kq = T.tong_hop(luot, 1800)
    assert kq["qwen38-api/stream"]["ttft_max"] == 1.0
    assert kq["qwen38-api/dong_bo"]["ttft_max"] == 40.0


def test_nguoi_suy_tu_khoang_lang_theo_tung_model():
    luot = T.doc_so([
        _d("2026-09-18 10:00:00", ttft=30.0),                       # đầu sổ: không biết
        _d("2026-09-18 10:10:00", ttft=1.0),                        # ấm
        _d("2026-09-18 10:20:00", model="qwen35-api", ttft=0.5),    # model khác không làm 3.8 ấm/nguội
        _d("2026-09-18 11:00:01", ttft=25.0),                       # lặng 50 phút > 1800 s ⇒ nguội
    ])
    kq = T.tong_hop(luot, 1800)["qwen38-api/stream"]
    assert kq["nguoi_suy_tu_so"] == 1
    assert kq["ttft_nguoi"] == [25.0]
    assert kq["ttft_am_p95"] == 1.0
    assert kq["ttft_p95"] == 30.0


def test_loi_khong_vao_phan_vi():
    luot = T.doc_so([_d("2026-09-18 10:00:00", ttft=99.0, ma=503), _d("2026-09-18 10:00:01", ttft=2.0)])
    kq = T.tong_hop(luot, 1800)["qwen38-api/stream"]
    assert kq["ttft_max"] == 2.0 and kq["ma_http"] == {200: 1, 503: 1}


def test_dem_unload_llamaswap():
    dong = ["[INFO] <qwen38-api> Unloading model, TTL of 1800s reached\n",
            "[INFO] <qwen35-api> Unloading model, TTL of 1800s reached\n",
            "[INFO] <qwen38-api> Unloading model, TTL of 1800s reached\n",
            "[INFO] <qwen38-api> Health check passed on http://127.0.0.1:8282/health\n"]
    assert T.dem_unload(dong) == {"qwen38-api": 2, "qwen35-api": 1}
