"""
test_801 — `apps/chatltt/services/gop_manh.py`. (H44 P03)

`test_800` đã ghim: runtime **không** gộp mảnh, mỗi chunk một sự kiện. Tệp này
kiểm phần ChatLTT phải làm — và kiểm bằng **đúng hình dạng máy B đã phát thật**,
lấy từ `artifacts/01_cong0.json`, không phải hình dạng tôi tưởng tượng.
"""
from __future__ import annotations

import json

import pytest

from apps.chatltt.services import gop_manh as G


def _sk(*manh):
    return {"type": "tool_call.delta", "tool_calls": list(manh)}


def _dau(index, ten, ds=""):
    return {"index": index, "id": f"call_{index+1}", "type": "function",
            "function": {"name": ten, "arguments": ds}}


def _noi(index, ds):
    return {"index": index, "function": {"arguments": ds}}


# ── Ca thường: một lời gọi, đối số cắt ba mảnh ─────────────────────────────

def test_gop_ba_manh_thanh_mot_loi_goi():
    ds = G.gop([
        _sk(_dau(0, "calculator")),
        _sk(_noi(0, '{"expres')),
        _sk(_noi(0, 'sion": "8123')),
        _sk(_noi(0, ' * 4471"}')),
    ])
    assert len(ds) == 1
    assert ds[0].ten == "calculator"
    assert ds[0].id == "call_1"
    assert ds[0].doi_so() == {"expression": "8123 * 4471"}


def test_khong_cat_manh_van_dung():
    ds = G.gop([_sk(_dau(0, "calculator", '{"expression": "1+1"}'))])
    assert ds[0].doi_so() == {"expression": "1+1"}


def test_tool_khong_tham_so_ra_dict_rong_KHONG_phai_loi():
    """⭐ `arguments` rỗng là hợp lệ — tool không tham số vẫn gọi được."""
    ds = G.gop([_sk(_dau(0, "trang_thai"))])
    assert ds[0].doi_so() == {}


# ── Gọi song song: `index` là khoá, không phải `id` ────────────────────────

def test_hai_loi_goi_song_song_khong_tron_nhau():
    """🔴 Chỉ chunk ĐẦU mang `id`. Gom theo `id` thì mọi mảnh sau rơi vào nhóm
    `None` và trộn lẫn — P01 đo gọi song song 18/18 nên đây là đường thường ngày.
    """
    ds = G.gop([
        _sk(_dau(0, "calculator"), _dau(1, "weather_fake")),
        _sk(_noi(0, '{"expression":'), _noi(1, '{"city":')),
        _sk(_noi(0, ' "12*12"}'), _noi(1, ' "Ha Noi"}')),
    ])
    assert len(ds) == 2
    assert [x.ten for x in ds] == ["calculator", "weather_fake"]
    assert ds[0].doi_so() == {"expression": "12*12"}
    assert ds[1].doi_so() == {"city": "Ha Noi"}


def test_giu_THU_TU_XUAT_HIEN_chu_khong_thu_tu_index():
    ds = G.gop([
        _sk(_dau(3, "search_fake", "{}")),
        _sk(_dau(1, "calculator", "{}")),
    ])
    assert [x.index for x in ds] == [3, 1]


def test_thieu_index_thi_coi_la_loi_goi_thu_nhat():
    ds = G.gop([
        _sk({"id": "call_1", "function": {"name": "calculator", "arguments": '{"a":'}}),
        _sk({"function": {"arguments": ' 1}'}}),
    ])
    assert len(ds) == 1, "thieu `index` khong duoc de ra hai loi goi vo danh"
    assert ds[0].doi_so() == {"a": 1}


def test_ten_duoc_GAN_khong_duoc_NOI():
    """⛔ Runtime lặp chunk đầu ⇒ nối `name` sẽ ra `calculatorcalculator`."""
    ds = G.gop([_sk(_dau(0, "calculator")), _sk(_dau(0, "calculator", "{}"))])
    assert ds[0].ten == "calculator"


# ── Đối số hỏng là dữ liệu để model sửa, không phải lý do giết run ─────────

def test_doi_so_khong_phai_JSON_thi_nem_DoiSoHong():
    ds = G.gop([_sk(_dau(0, "calculator", '{"expression": "1+1"'))])   # thieu }
    with pytest.raises(G.DoiSoHong):
        ds[0].doi_so()


def test_doi_so_la_mang_thi_cung_nem():
    ds = G.gop([_sk(_dau(0, "calculator", '[1, 2]'))])
    with pytest.raises(G.DoiSoHong):
        ds[0].doi_so()


def test_su_kien_loai_khac_bi_bo_qua():
    bo = G.BoGop()
    for sk in ({"type": "response.delta", "text": "xin chao"},
               {"type": "usage.updated", "token_ra": 5}):
        bo.nhin(sk)
    assert not bo.co_gi_khong()


# ── Băm chặn trùng ─────────────────────────────────────────────────────────

def test_bam_trung_KHONG_doi_theo_thu_tu_khoa():
    """⛔ Không chuẩn hoá thì bộ chặn trùng chỉ chặn khi model tình cờ sinh khoá
    đúng thứ tự cũ — tức chặn ngẫu nhiên, và một cái rào chặn ngẫu nhiên tệ hơn
    không có rào: nó tạo cảm giác đã được bảo vệ."""
    a = G.bam_trung("calculator", {"a": 1, "b": 2})
    b = G.bam_trung("calculator", {"b": 2, "a": 1})
    assert a == b


def test_bam_trung_doi_khi_doi_so_doi():
    assert G.bam_trung("calculator", {"a": 1}) != G.bam_trung("calculator", {"a": 2})


def test_bam_trung_doi_khi_TEN_doi():
    assert G.bam_trung("calculator", {"a": 1}) != G.bam_trung("weather_fake", {"a": 1})


# ── Đúng hình dạng máy B đã phát THẬT ──────────────────────────────────────

def test_khop_hinh_dang_may_B_da_phat_that():
    """Dựng lại từ `artifacts/01_cong0.json`: chunk đầu mang `id`+`name`+
    `arguments` rỗng, các chunk sau chỉ nối `arguments`."""
    ds = G.gop([
        _sk({"index": 0, "id": "call_1", "type": "function",
             "function": {"name": "calculator", "arguments": ""}}),
        _sk({"index": 0, "function": {"arguments": '{"expression"'}}),
        _sk({"index": 0, "function": {"arguments": ': "8123 * 4471"}'}}),
    ])
    assert len(ds) == 1
    lg = ds[0]
    assert (lg.id, lg.ten, lg.loai) == ("call_1", "calculator", "function")
    assert lg.doi_so() == {"expression": "8123 * 4471"}
    assert json.loads(lg.doi_so_tho) == lg.doi_so()


def test_tom_tat_cat_ngan_va_khong_xuong_dong():
    lg = G.LoiGoi(index=0, ten="search_fake", doi_so_tho='{"q": "' + "x" * 300 + '"}')
    t = G.tom_tat(lg)
    assert t.startswith("search_fake(")
    assert len(t) < 160 and "\n" not in t
